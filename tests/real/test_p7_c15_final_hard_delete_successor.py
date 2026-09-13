"""P7.C15 hard-delete successor preparation.

This is a preparation-only successor.  Its positive and negative executions
use temporary authorities and fake protocol clients; the real gate is
intentionally disabled unless a later architect supplies every source value.
The accepted P7.C14/P7.C13 modules are imported as frozen library authority,
never entered as real parent or child entrypoints.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from unittest.mock import patch

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import (
    CodexModelCatalog,
    CodexModelCatalogAdapter,
    CodexModelDescriptor,
)
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnLifecycleError,
    TurnStartStatus,
    TurnTerminalStatus,
)
from codex_control.adapters.codex.protocol import InboundServerRequest
from tests.real import test_p7_c12_strict_approval_matcher as p7c12
from tests.real import test_p7_c13_final_hard_delete_acceptance as p7c13
from tests.real import test_p7_c14_final_hard_delete_recovery as p7c14


P7C15_FUTURE_REAL_GATE = "P7C15_FUTURE_REAL_GATE"
P7C15_EXPECTED_HEAD = os.environ.get("P7C15_EXPECTED_HEAD", "")
P7C15_EXPECTED_TREE = os.environ.get("P7C15_EXPECTED_TREE", "")
P7C15_EXPECTED_LAUNCHER_BLOB = os.environ.get("P7C15_EXPECTED_LAUNCHER_BLOB", "")
P7C15_EXPECTED_P7C14_LAUNCHER_BLOB = os.environ.get("P7C15_EXPECTED_P7C14_LAUNCHER_BLOB", "")
P7C15_EXPECTED_P7C13_HARNESS_BLOB = os.environ.get("P7C15_EXPECTED_P7C13_HARNESS_BLOB", "")
P7C15_EXPECTED_P7C12_MATCHER_BLOB = os.environ.get("P7C15_EXPECTED_P7C12_MATCHER_BLOB", "")
P7C15_EXPECTED_TESTS_INIT_BLOB = os.environ.get("P7C15_EXPECTED_TESTS_INIT_BLOB", "")
P7C15_EXPECTED_TESTS_REAL_INIT_BLOB = os.environ.get("P7C15_EXPECTED_TESTS_REAL_INIT_BLOB", "")
P7C15_LEDGER_PATH = Path("/root/.codexcontrol/p7c15-one-shot.json")
P7C15_IMPORT_ROOTS = ("/root/CodexControl/src", "/root/CodexControl")
P7C15_PYTHONPATH = os.pathsep.join(P7C15_IMPORT_ROOTS)
P7C15_PROFILE_ID = "p7c15-successor-profile"
P7C15_FROZEN_EFFECT_BUDGET = dict(p7c13.FROZEN_EFFECT_BUDGET)
P7C15_LEDGER_SCHEMA = "p7c15-one-shot-v1"
P7C15_BOOT_SCHEMA = "p7c15-boot-v1"
P7C15_CHILD_RESULT_SCHEMA = "p7c15-child-result-v1"
P7C15_LEDGER_STATES = frozenset(
    ("RESERVED", "COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT")
)

# This is an invocation plan, rather than a set of unique timeout keys.  A
# number of the inherited stage buckets are consumed more than once in the
# sequential positive path, so the parent deadline must cover each window.
P7C15_REAL_TIMEOUT_INVOCATION_PLAN: tuple[tuple[str, str, float], ...] = (
    ("fresh_workdir_creation", "thread_start", 30.0),
    ("runtime_generation_1_acquire", "runtime_acquire_generation_1", 30.0),
    ("model_list", "model_list", 20.0),
    ("thread_start", "thread_start", 30.0),
    ("turn1_start", "turn1_start_terminal", 60.0),
    ("turn1_terminal", "turn1_start_terminal", 60.0),
    ("generation_1_shutdown", "runtime_shutdown_generation_1", 30.0),
    ("runtime_generation_2_acquire", "runtime_acquire_generation_2", 30.0),
    ("thread_resume", "thread_resume", 30.0),
    ("turn2_start", "turn2_start_terminal", 60.0),
    ("turn2_terminal", "turn2_start_terminal", 60.0),
    ("turn3_start", "turn3_start_approval_terminal", 90.0),
    ("first_approval_handling", "turn3_start_approval_terminal", 90.0),
    ("turn3_observer_primary_wait", "turn3_start_approval_terminal", 90.0),
    ("turn3_terminal_convergence_after_request_first", "turn3_start_approval_terminal", 90.0),
    ("turn3_observer_join_terminal", "final_runtime_local_convergence", 30.0),
    ("turn3_observer_join_request", "final_runtime_local_convergence", 30.0),
    ("turn4_start", "turn4_start", 30.0),
    ("turn4_active_observation", "turn4_active_observation", 5.0),
    ("turn4_interrupt_terminal", "turn4_interrupt_terminal", 45.0),
    ("turn4_join_terminal", "final_runtime_local_convergence", 30.0),
    ("turn4_join_request", "final_runtime_local_convergence", 30.0),
    ("runtime_shutdown_before_oracle", "runtime_shutdown_before_scan", 30.0),
    ("runtime_acquire_delete_generation", "final_runtime_local_convergence", 30.0),
    ("controller_open", "controller_open_binding", 30.0),
    ("pre_delete_schema_read", "controller_open_binding", 30.0),
    ("dialogue_create", "controller_open_binding", 30.0),
    ("dialogue_confirm", "controller_open_binding", 30.0),
    ("durable_binding_read", "controller_open_binding", 30.0),
    ("canonical_application_delete", "canonical_application_delete", 60.0),
    ("final_runtime_shutdown", "final_runtime_local_convergence", 30.0),
    ("tombstone_read", "final_runtime_local_convergence", 30.0),
    ("post_delete_live_binding_read", "final_runtime_local_convergence", 30.0),
    ("post_delete_schema_read", "final_runtime_local_convergence", 30.0),
    ("storage_close", "final_runtime_local_convergence", 30.0),
)
P7C15_REAL_INTERNAL_TIMEOUT_BUDGET = sum(item[2] for item in P7C15_REAL_TIMEOUT_INVOCATION_PLAN)
P7C15_REAL_WATCHDOG_MARGIN = 60.0
P7C15_REAL_WATCHDOG_HARD_DEADLINE = P7C15_REAL_INTERNAL_TIMEOUT_BUDGET + P7C15_REAL_WATCHDOG_MARGIN


def p7c15_fresh_run_paths(
    run_hash_fragment: str, *, root: Path = Path("/root"), authority: Path = Path("/root/.codexcontrol")
) -> dict[str, str]:
    """Return only fresh P7.C15 authorities for one safe run hash."""
    safe = "".join(char for char in run_hash_fragment if char in "0123456789abcdef")[:32]
    if not safe:
        raise P7C15PreparationError("safe run hash fragment required")
    return {
        "isolated_root": str(root / f"p7c15-isolated-{safe}"),
        "controller_db": str(authority / f"p7c15-controller-{safe}.sqlite3"),
        "workdir": str(root / f"p7c15-work-{safe}"),
        "approval_target": str(root / f"p7c15-approval-{safe}"),
        "boot": str(authority / f"p7c15-boot-{safe}.json"),
        "child_result": str(authority / f"p7c15-child-result-{safe}.json"),
        "wire": str(authority / f"p7c15-wire-{safe}.json"),
        "approval_journal": str(authority / f"p7c15-approval-journal-{safe}.json"),
        "stage": str(authority / f"p7c15-stage-{safe}.jsonl"),
    }


class P7C15PreparationError(RuntimeError):
    """Finite fail-closed preparation error."""


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _repository() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=_repository(), check=True,
                          capture_output=True, text=True).stdout.strip()


def _blob(path: Path) -> str:
    return _git("hash-object", str(path))


@dataclass(frozen=True)
class P7C15SourceAuthority:
    head: str
    tree: str
    launcher_blob: str
    p7c14_launcher_blob: str
    p7c13_harness_blob: str
    p7c12_matcher_blob: str
    tests_init_blob: str
    tests_real_init_blob: str
    import_root_authority: bool
    tracked_clean: bool


@dataclass(frozen=True)
class P7C15ArchitectContract:
    authorization_token: str
    expected_head: str
    expected_tree: str
    expected_launcher_blob: str
    expected_p7c14_launcher_blob: str
    expected_p7c13_harness_blob: str
    expected_p7c12_matcher_blob: str
    expected_tests_init_blob: str
    expected_tests_real_init_blob: str
    expected_import_roots: tuple[str, str] = P7C15_IMPORT_ROOTS


def _under(spec: Any, root: Path) -> bool:
    origin = getattr(spec, "origin", None)
    if not isinstance(origin, str) or origin in {"built-in", "frozen"}:
        return False
    try:
        Path(origin).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def validate_p7c15_import_root_authority(environ: Mapping[str, str] | None = None) -> bool:
    environment = os.environ if environ is None else environ
    if environment.get("PYTHONPATH") != P7C15_PYTHONPATH:
        return False
    import importlib.machinery

    source, tests = _repository() / "src", _repository() / "tests"
    return _under(importlib.machinery.PathFinder.find_spec("codex_control", [str(source)]), source) and _under(
        importlib.machinery.PathFinder.find_spec("tests", [str(_repository())]), tests
    )


def current_p7c15_source_authority() -> P7C15SourceAuthority:
    repository = _repository()
    clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
    index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
    return P7C15SourceAuthority(
        _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}"), _blob(Path(__file__).resolve()),
        _blob(repository / "tests/real/test_p7_c14_final_hard_delete_recovery.py"),
        _blob(repository / "tests/real/test_p7_c13_final_hard_delete_acceptance.py"),
        _blob(repository / "tests/real/test_p7_c12_strict_approval_matcher.py"),
        _blob(repository / "tests/__init__.py"), _blob(repository / "tests/real/__init__.py"),
        validate_p7c15_import_root_authority(), clean and index_clean,
    )


def p7c15_source_bundle_gate(
    environ: Mapping[str, str], contract: P7C15ArchitectContract | None,
    authority: P7C15SourceAuthority,
) -> bool:
    if contract is None or contract.expected_import_roots != P7C15_IMPORT_ROOTS:
        return False
    values = (
        contract.authorization_token, contract.expected_head, contract.expected_tree,
        contract.expected_launcher_blob, contract.expected_p7c14_launcher_blob,
        contract.expected_p7c13_harness_blob, contract.expected_p7c12_matcher_blob,
        contract.expected_tests_init_blob, contract.expected_tests_real_init_blob,
    )
    if not all(values) or environ.get(P7C15_FUTURE_REAL_GATE) != contract.authorization_token:
        return False
    env_names = (
        ("P7C15_EXPECTED_HEAD", contract.expected_head), ("P7C15_EXPECTED_TREE", contract.expected_tree),
        ("P7C15_EXPECTED_LAUNCHER_BLOB", contract.expected_launcher_blob),
        ("P7C15_EXPECTED_P7C14_LAUNCHER_BLOB", contract.expected_p7c14_launcher_blob),
        ("P7C15_EXPECTED_P7C13_HARNESS_BLOB", contract.expected_p7c13_harness_blob),
        ("P7C15_EXPECTED_P7C12_MATCHER_BLOB", contract.expected_p7c12_matcher_blob),
        ("P7C15_EXPECTED_TESTS_INIT_BLOB", contract.expected_tests_init_blob),
        ("P7C15_EXPECTED_TESTS_REAL_INIT_BLOB", contract.expected_tests_real_init_blob),
    )
    if any(environ.get(name) != value for name, value in env_names):
        return False
    return (
        authority.head == contract.expected_head and authority.tree == contract.expected_tree
        and authority.launcher_blob == contract.expected_launcher_blob
        and authority.p7c14_launcher_blob == contract.expected_p7c14_launcher_blob
        and authority.p7c13_harness_blob == contract.expected_p7c13_harness_blob
        and authority.p7c12_matcher_blob == contract.expected_p7c12_matcher_blob
        and authority.tests_init_blob == contract.expected_tests_init_blob
        and authority.tests_real_init_blob == contract.expected_tests_real_init_blob
        and authority.import_root_authority and authority.tracked_clean
    )


def _contract_from_environment(environ: Mapping[str, str]) -> P7C15ArchitectContract:
    return P7C15ArchitectContract(
        environ.get(P7C15_FUTURE_REAL_GATE, ""), environ.get("P7C15_EXPECTED_HEAD", ""),
        environ.get("P7C15_EXPECTED_TREE", ""), environ.get("P7C15_EXPECTED_LAUNCHER_BLOB", ""),
        environ.get("P7C15_EXPECTED_P7C14_LAUNCHER_BLOB", ""),
        environ.get("P7C15_EXPECTED_P7C13_HARNESS_BLOB", ""),
        environ.get("P7C15_EXPECTED_P7C12_MATCHER_BLOB", ""),
        environ.get("P7C15_EXPECTED_TESTS_INIT_BLOB", ""),
        environ.get("P7C15_EXPECTED_TESTS_REAL_INIT_BLOB", ""),
    )


class GenerationTrackingRuntimeManager:
    """Generation authority wrapper; all other manager behavior is delegated."""

    def __init__(self, accepted_manager: Any) -> None:
        self._accepted = accepted_manager
        self._confirmed: dict[str, int] = {}

    async def acquire(self, profile_id: str) -> Any:
        runtime = await self._accepted.acquire(profile_id)
        if getattr(runtime, "profile_id", None) != profile_id:
            raise P7C15PreparationError("profile mismatch")
        generation = getattr(runtime, "generation", None)
        if type(generation) is not int or generation <= 0:
            raise P7C15PreparationError("generation invalid")
        prior = self._confirmed.get(profile_id)
        if prior is not None and generation < prior:
            raise P7C15PreparationError("generation regression")
        self._confirmed[profile_id] = generation
        return runtime

    @property
    def confirmed_generations(self) -> Mapping[str, int]:
        return dict(self._confirmed)

    def confirmed_generation(self, profile_id: str) -> int:
        try:
            return self._confirmed[profile_id]
        except KeyError:
            raise P7C15PreparationError("generation not confirmed") from None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._accepted, name)


@dataclass(frozen=True)
class ImmutableSemanticCatalogSnapshot:
    profile_id: str
    models: tuple[CodexModelDescriptor, ...]
    default_model: str
    default_wire_model: str
    supported_reasoning_efforts: tuple[tuple[str, tuple[str, ...]], ...]
    default_reasoning_effort: tuple[tuple[str, str], ...]
    fetched_at: float
    expires_at: float

    @classmethod
    def from_catalog(cls, catalog: CodexModelCatalog) -> "ImmutableSemanticCatalogSnapshot":
        defaults = tuple(model for model in catalog.models if model.is_default and not model.hidden)
        if len(defaults) != 1:
            raise P7C15PreparationError("catalog default invalid")
        return cls(
            catalog.profile_id, tuple(catalog.models), defaults[0].model_id, defaults[0].wire_model,
            tuple((model.model_id, model.supported_reasoning_efforts) for model in catalog.models),
            tuple((model.model_id, model.default_reasoning_effort) for model in catalog.models),
            catalog.fetched_at, catalog.expires_at,
        )

    def default_reasoning_effort_for(self, model_id: str) -> str:
        """Resolve effort by selected model identity, never catalog order."""
        for selected_id, effort in self.default_reasoning_effort:
            if selected_id == model_id:
                return effort
        raise P7C15PreparationError("selected model reasoning authority missing")


class GenerationReboundCatalogView:
    """One semantic snapshot whose sole mutable authority is generation."""

    def __init__(self, snapshot: ImmutableSemanticCatalogSnapshot, tracker: GenerationTrackingRuntimeManager) -> None:
        self.snapshot, self.tracker = snapshot, tracker

    @property
    def profile_id(self) -> str:
        return self.snapshot.profile_id

    @property
    def runtime_generation(self) -> int:
        return self.tracker.confirmed_generation(self.profile_id)

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        if profile_id != self.profile_id:
            raise P7C15PreparationError("catalog profile mismatch")
        # refresh is deliberately ignored: rebinding never invokes a provider.
        del refresh
        return CodexModelCatalog(
            self.snapshot.profile_id, self.runtime_generation, self.snapshot.models,
            self.snapshot.fetched_at, self.snapshot.expires_at,
        )


class P7C15SingleCatalogAcquisition:
    """Guard the semantic provider boundary to one authenticated fetch."""

    def __init__(self, adapter: CodexModelCatalogAdapter) -> None:
        self.adapter, self.dispatch_count = adapter, 0

    async def acquire_once(self, profile_id: str) -> CodexModelCatalog:
        if self.dispatch_count:
            raise P7C15PreparationError("second underlying model/list acquisition blocked")
        self.dispatch_count += 1
        return await self.adapter.get_catalog(profile_id)


class StaticGenerationCatalogView:
    def __init__(self, catalog: CodexModelCatalog) -> None:
        self.catalog = catalog

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        del refresh
        if profile_id != self.catalog.profile_id:
            raise P7C15PreparationError("catalog profile mismatch")
        return self.catalog


class EffectBudget:
    def __init__(self, limits: Mapping[str, int] | None = None) -> None:
        self.limits = dict(limits or P7C15_FROZEN_EFFECT_BUDGET)
        self.counts: dict[str, int] = {}

    def record(self, effect: str) -> None:
        value = self.counts.get(effect, 0) + 1
        if value > self.limits.get(effect, 0):
            raise P7C15PreparationError(f"effect ceiling exceeded: {effect}")
        self.counts[effect] = value

    def count(self, effect: str) -> int:
        return self.counts.get(effect, 0)


class P7C15StageJournal:
    """Exclusive, bounded, root-only, safe stage facts."""

    MAX_BYTES = 16384
    MAX_RECORDS = 96
    ALLOWED = frozenset({"schema", "sequence", "stage", "state", "effect_class", "error_class", "error_category", "journal_sha256"})

    def __init__(self, path: str | Path) -> None:
        self.path, self.sequence = Path(path), 0
        self._create()

    def _create(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.close(fd)
        st = self.path.lstat()
        if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
            raise P7C15PreparationError("stage journal authority invalid")

    def append(self, stage: str, state: str, *, effect_class: str = "none", error: BaseException | None = None) -> None:
        if self.sequence >= self.MAX_RECORDS or not stage or not state or len(stage) > 96 or len(state) > 32 or len(effect_class) > 64:
            raise P7C15PreparationError("stage journal bound exceeded")
        self.sequence += 1
        record: dict[str, Any] = {
            "schema": "p7c15-stage-v1", "sequence": self.sequence, "stage": stage,
            "state": state, "effect_class": effect_class,
        }
        if error is not None:
            record["error_class"] = type(error).__name__[:96]
            category = getattr(error, "category", None)
            if isinstance(category, CodexAdapterErrorCategory):
                record["error_category"] = category.value
            elif isinstance(category, str) and len(category) <= 96:
                record["error_category"] = category
        raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(self.path.read_bytes()) + len(raw) > self.MAX_BYTES:
            raise P7C15PreparationError("stage journal too large")
        with self.path.open("ab") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    def records(self) -> list[dict[str, Any]]:
        lines = self.path.read_text().splitlines()
        if len(lines) > self.MAX_RECORDS:
            raise P7C15PreparationError("stage journal record bound exceeded")
        result = [json.loads(line, object_pairs_hook=_reject_duplicate_json_keys) for line in lines]
        sequences = [record.get("sequence") for record in result]
        if sequences != list(range(1, len(result) + 1)):
            raise P7C15PreparationError("stage journal sequence invalid")
        for record in result:
            if set(record) - self.ALLOWED or any(isinstance(value, (dict, list)) for value in record.values()):
                raise P7C15PreparationError("stage journal unsafe field")
        return result

    def digest(self) -> str:
        return _sha256(self.path.read_bytes())


class P7C15DurableOneShotLedger:
    """Distinct one-shot authority; every terminal state remains consumed."""

    def __init__(self, path: str | Path, *, max_bytes: int = 8192) -> None:
        self.path, self.max_bytes, self._identity = Path(path), max_bytes, None

    @staticmethod
    def _valid_record(record: Any) -> dict[str, Any]:
        keys = {"schema", "state", "source_head", "source_tree", "harness_blob", "run_id_hash", "effect_counts", "recovery"}
        if not isinstance(record, dict) or set(record) != keys or record.get("schema") != P7C15_LEDGER_SCHEMA or record.get("state") not in P7C15_LEDGER_STATES:
            raise P7C15PreparationError("P7.C15 ledger schema invalid")
        if any(not isinstance(record.get(key), str) or not record[key] for key in ("source_head", "source_tree", "harness_blob", "run_id_hash")):
            raise P7C15PreparationError("P7.C15 ledger authority invalid")
        if not all(isinstance(record.get(key), dict) for key in ("effect_counts", "recovery")):
            raise P7C15PreparationError("P7.C15 ledger maps invalid")
        return record

    def reserve(self, record: Mapping[str, Any]) -> bool:
        payload = json.dumps(self._valid_record(dict(record)), sort_keys=True, separators=(",", ":")).encode()
        if len(payload) > self.max_bytes:
            raise P7C15PreparationError("P7.C15 ledger too large")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            return False
        try:
            os.fchmod(fd, 0o600); os.write(fd, payload); os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != os.getuid() or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise P7C15PreparationError("P7.C15 ledger shape invalid")
            self._identity = (st.st_dev, st.st_ino)
        finally:
            os.close(fd)
        return True

    def read(self) -> dict[str, Any]:
        st = self.path.lstat()
        if stat.S_ISLNK(st.st_mode) or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.getuid():
            raise P7C15PreparationError("P7.C15 ledger identity invalid")
        return self._valid_record(json.loads(self.path.read_text()))

    def update(self, *, state: str, recovery: Mapping[str, Any] | None = None) -> dict[str, Any]:
        record = self.read()
        if record["state"] != "RESERVED" or state not in P7C15_LEDGER_STATES - {"RESERVED"}:
            raise P7C15PreparationError("P7.C15 terminal transition invalid")
        record["state"] = state
        if recovery is not None:
            record["recovery"] = dict(recovery)
        payload = json.dumps(self._valid_record(record), sort_keys=True, separators=(",", ":")).encode()
        fd = os.open(self.path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            current = os.fstat(fd)
            if self._identity is not None and (current.st_dev, current.st_ino) != self._identity:
                raise P7C15PreparationError("P7.C15 ledger replaced")
            os.ftruncate(fd, 0); os.write(fd, payload); os.fsync(fd)
        finally:
            os.close(fd)
        return self.read()


class P7C15RootOnlyBootAuthority:
    """Boot authority bound to the P7.C15 executable and replay ledger."""

    KEYS = frozenset({
        "schema", "source_head", "source_tree", "harness_blob", "run_id_hash", "profile_id",
        "codex_home", "ledger_path", "boot_authority_path", "child_result_path", "isolated_root",
        "isolated_sqlite", "isolated_logs", "controller_db", "workdir", "approval_target",
        "wire_path", "approval_journal_path", "stage_journal_path", "effect_ceiling",
        "import_roots", "deterministic_import_root", "runtime_authority",
    })

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @classmethod
    def validate(cls, record: Mapping[str, Any]) -> dict[str, Any]:
        if set(record) != cls.KEYS or record.get("schema") != P7C15_BOOT_SCHEMA:
            raise P7C15PreparationError("P7.C15 boot schema invalid")
        if record.get("profile_id") != P7C15_PROFILE_ID:
            raise P7C15PreparationError("P7.C15 profile authority invalid")
        scalar_keys = ("source_head", "source_tree", "harness_blob", "run_id_hash", "profile_id", "codex_home", "runtime_authority")
        path_keys = (
            "ledger_path", "boot_authority_path", "child_result_path", "isolated_root", "isolated_sqlite",
            "isolated_logs", "controller_db", "workdir", "approval_target", "wire_path",
            "approval_journal_path", "stage_journal_path",
        )
        for key in scalar_keys + path_keys:
            value = record.get(key)
            if not isinstance(value, str) or not value or "\0" in value or len(value) > 4096:
                raise P7C15PreparationError("P7.C15 boot scalar invalid")
        if any(not os.path.isabs(record[key]) for key in path_keys):
            raise P7C15PreparationError("P7.C15 boot path invalid")
        if record["import_roots"] != list(P7C15_IMPORT_ROOTS):
            raise P7C15PreparationError("P7.C15 import-root authority invalid")
        if record["deterministic_import_root"] != P7C15_PYTHONPATH:
            raise P7C15PreparationError("P7.C15 deterministic import authority invalid")
        if not isinstance(record["effect_ceiling"], dict) or set(record["effect_ceiling"]) != set(P7C15_FROZEN_EFFECT_BUDGET):
            raise P7C15PreparationError("P7.C15 effect ceiling invalid")
        if any(type(value) is not int or value != P7C15_FROZEN_EFFECT_BUDGET[key] for key, value in record["effect_ceiling"].items()):
            raise P7C15PreparationError("P7.C15 effect ceiling invalid")
        if len({record[key] for key in path_keys}) != len(path_keys):
            raise P7C15PreparationError("P7.C15 boot paths alias")
        if record["ledger_path"] != str(P7C15_LEDGER_PATH) and not Path(record["ledger_path"]).name.endswith("one-shot.json"):
            raise P7C15PreparationError("P7.C15 ledger authority invalid")
        for key in path_keys:
            path = Path(record[key])
            if path.is_symlink():
                raise P7C15PreparationError("P7.C15 boot path symlink")
        return dict(record)

    def create(self, record: Mapping[str, Any]) -> dict[str, Any]:
        value = self.validate(record)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        if len(payload) > 16384:
            raise P7C15PreparationError("P7.C15 boot too large")
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError as error:
            raise P7C15PreparationError("P7.C15 boot already exists") from error
        try:
            os.write(fd, payload); os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise P7C15PreparationError("P7.C15 boot shape invalid")
        finally:
            os.close(fd)
        return self.read()

    def read(self) -> dict[str, Any]:
        st = self.path.lstat()
        if st.st_uid != 0 or stat.S_ISLNK(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
            raise P7C15PreparationError("P7.C15 boot identity invalid")
        return self.validate(json.loads(self.path.read_text(), object_pairs_hook=_reject_duplicate_json_keys))


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise P7C15PreparationError("duplicate JSON key")
        result[key] = value
    return result


class P7C15ChildResultAuthority:
    """Bounded root-only result authority owned by the child and read by parent."""

    KEYS = frozenset({
        "schema", "status", "verdict", "source_head", "source_tree", "harness_blob", "run_id_hash",
        "effect_counts", "outcomes", "classes", "terminal_exception_class", "terminal_error_category",
        "last_confirmed_stage", "stage_journal_sha256", "runtime_child_quiescent",
        "parent_process_group_quiescent",
    })
    STATUSES = frozenset({"PASS", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"})
    MAX_BYTES = 16384

    @classmethod
    def validate(cls, value: Mapping[str, Any], boot: Mapping[str, Any]) -> dict[str, Any]:
        if set(value) != cls.KEYS or value.get("schema") != P7C15_CHILD_RESULT_SCHEMA:
            raise P7C15PreparationError("P7.C15 child result schema invalid")
        if value.get("status") not in cls.STATUSES or type(value.get("verdict")) is not bool:
            raise P7C15PreparationError("P7.C15 child result status invalid")
        for key in ("source_head", "source_tree", "harness_blob", "run_id_hash"):
            if value.get(key) != boot.get(key):
                raise P7C15PreparationError("P7.C15 child result boot binding invalid")
        if not isinstance(value.get("effect_counts"), dict) or set(value["effect_counts"]) != set(P7C15_FROZEN_EFFECT_BUDGET):
            raise P7C15PreparationError("P7.C15 child result effects invalid")
        for key, count in value["effect_counts"].items():
            if type(count) is not int or count < 0 or count > P7C15_FROZEN_EFFECT_BUDGET[key]:
                raise P7C15PreparationError("P7.C15 child result effect ceiling invalid")
        for key in ("outcomes", "classes"):
            if not isinstance(value.get(key), dict) or len(value[key]) > 64:
                raise P7C15PreparationError("P7.C15 child result map invalid")
            if any(not isinstance(name, str) or not isinstance(item, (str, int, bool, type(None))) for name, item in value[key].items()):
                raise P7C15PreparationError("P7.C15 child result unsafe value")
        for key in ("terminal_exception_class", "terminal_error_category", "last_confirmed_stage", "stage_journal_sha256"):
            if value[key] is not None and (not isinstance(value[key], str) or not value[key] or len(value[key]) > 128):
                raise P7C15PreparationError("P7.C15 child result string invalid")
        if type(value["runtime_child_quiescent"]) is not bool or value["parent_process_group_quiescent"] is not None and type(value["parent_process_group_quiescent"]) is not bool:
            raise P7C15PreparationError("P7.C15 child result quiescence invalid")
        payload = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        if len(payload) > cls.MAX_BYTES:
            raise P7C15PreparationError("P7.C15 child result too large")
        return dict(value)

    @classmethod
    def write(cls, path: str | Path, value: Mapping[str, Any], boot: Mapping[str, Any]) -> dict[str, Any]:
        checked = cls.validate(value, boot)
        target = Path(path)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError as error:
            raise P7C15PreparationError("P7.C15 child result already exists") from error
        try:
            os.fchmod(fd, 0o600); os.write(fd, payload); os.fsync(fd)
            identity = os.fstat(fd)
            if identity.st_uid != 0 or identity.st_nlink != 1 or not stat.S_ISREG(identity.st_mode) or stat.S_IMODE(identity.st_mode) != 0o600:
                raise P7C15PreparationError("P7.C15 child result identity invalid")
        finally:
            os.close(fd)
        return cls.read(target, boot)

    @classmethod
    def read(cls, path: str | Path, boot: Mapping[str, Any]) -> dict[str, Any]:
        target = Path(path); identity = target.lstat()
        if identity.st_uid != 0 or stat.S_ISLNK(identity.st_mode) or not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1 or stat.S_IMODE(identity.st_mode) != 0o600 or identity.st_size > cls.MAX_BYTES:
            raise P7C15PreparationError("P7.C15 child result authority invalid")
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            data = os.read(fd, cls.MAX_BYTES + 1)
            current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_nlink != 1 or stat.S_IMODE(current.st_mode) != 0o600:
                raise P7C15PreparationError("P7.C15 child result identity drift")
        finally:
            os.close(fd)
        if len(data) > cls.MAX_BYTES:
            raise P7C15PreparationError("P7.C15 child result too large")
        return cls.validate(json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys), boot)


@dataclass(frozen=True)
class P7C15WatchdogResult:
    status: str
    child_result_valid: bool = True


def p7c15_parent_exit_projection(result: P7C15WatchdogResult, *, gate_enabled: bool = True) -> int:
    if not gate_enabled:
        return 2
    return 0 if result.status == "COMPLETED" and result.child_result_valid else 1


def p7c15_exact_effect_pass_gate(counts: Mapping[str, int]) -> bool:
    """Parent-owned exact effect matrix; ceilings alone cannot pass."""
    required = ("new_threads", "model/list", "thread/start", "thread/resume", "turn/start",
                "approval_responses", "allow_responses", "turn/interrupt", "thread/delete")
    forbidden = ("thread/read", "thread/list", "second_child", "real_retry", "telegram")
    return all(type(counts.get(key)) is int and counts[key] == P7C15_FROZEN_EFFECT_BUDGET[key] for key in required) and all(
        type(counts.get(key)) is int and counts[key] == 0 for key in forbidden
    )


def p7c15_completed_recovery_consistent(recovery: Mapping[str, Any]) -> bool:
    """Require persisted parent facts to independently prove COMPLETED."""
    return (
        recovery.get("watchdog_status") == "COMPLETED"
        and recovery.get("child_result_valid") is True
        and recovery.get("child_status") == "PASS"
        and recovery.get("child_verdict") is True
        and recovery.get("runtime_child_quiescent") is True
        and recovery.get("exact_effect_gate") is True
        and recovery.get("owned_group_active") == 0
        and recovery.get("owned_group_zombies") == 0
        and recovery.get("group_scan_errors") == 0
        and recovery.get("child_count") == 1
        and recovery.get("retry_count") == 0
    )


def _p7c15_child_result_payload(
    boot: Mapping[str, Any], result: Mapping[str, Any], pre_child_budget: EffectBudget,
    child: Any | None = None,
) -> dict[str, Any]:
    # The live production child is the accounting authority after construction.
    actual_budget = child.budget if child is not None else pre_child_budget
    counts = {key: actual_budget.count(key) for key in P7C15_FROZEN_EFFECT_BUDGET}
    classes = dict(result.get("classes", {}))
    return {
        "schema": P7C15_CHILD_RESULT_SCHEMA, "status": result.get("status", "FAILED"),
        "verdict": bool(result.get("verdict", False)), "source_head": boot["source_head"],
        "source_tree": boot["source_tree"], "harness_blob": boot["harness_blob"],
        "run_id_hash": boot["run_id_hash"], "effect_counts": counts,
        "outcomes": dict(result.get("outcomes", {})),
        "classes": classes, "terminal_exception_class": result.get("terminal_exception_class"),
        "terminal_error_category": result.get("terminal_error_category"),
        "last_confirmed_stage": result.get("last_confirmed_stage"),
        "stage_journal_sha256": result.get("stage_journal_sha256"),
        "runtime_child_quiescent": bool(result.get("runtime_child_quiescent", False)),
        "parent_process_group_quiescent": None,
    }


class _LiveChild:
    def __init__(self, budget: EffectBudget) -> None:
        self.budget = budget


async def _observe_turn3_request_after_response(
    *, client: Any, turn_lifecycle: Any, binding: Any,
    timeout: float, join_timeout: float,
) -> "P7C15Turn3ObserverOutcome":
    """Own the post-response request observer through Turn-3 convergence."""
    terminal_task = asyncio.create_task(turn_lifecycle.wait_turn(binding))
    request_task = asyncio.create_task(client.next_server_request())
    terminal: Any | None = None
    fault = False
    preliminary_request_done = False
    harness_cancel_requested = False
    try:
        done, _ = await asyncio.wait(
            (terminal_task, request_task), timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not done:
            raise P7C15PreparationError("Turn-3 terminal/request convergence timeout")
        preliminary_request_done = request_task.done()
        # Let a request that became ready in the same scheduling slice become
        # visible before the terminal branch takes ownership of cancellation.
        await asyncio.sleep(0)
        if terminal_task.done():
            try:
                terminal = terminal_task.result()
            except BaseException:
                fault = True
        elif request_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(terminal_task), timeout=timeout)
                terminal = terminal_task.result()
            except BaseException:
                fault = True
    finally:
        if not terminal_task.done():
            terminal_task.cancel()
        if not request_task.done():
            harness_cancel_requested = True
            request_task.cancel()
        # This scheduling barrier is part of the owned observer boundary.  It
        # permits a request already released by the server before/during final
        # join to terminalize and be classified rather than being lost behind
        # a preliminary task.done() snapshot.
        await asyncio.sleep(0)
        for task in (terminal_task, request_task):
            try:
                await asyncio.wait_for(task, timeout=join_timeout)
            except asyncio.CancelledError:
                # Harness-owned request cancellation is a clean terminal
                # observer class, not an observer fault.
                pass
            except BaseException:
                fault = True
    request_class, second_request = _classify_turn3_request_observer(
        request_task, harness_cancel_requested=harness_cancel_requested,
    )
    if request_class == P7C15Turn3RequestObserverClass.OBSERVER_ERROR:
        fault = True
    return P7C15Turn3ObserverOutcome(
        terminal=terminal, second_request=second_request, observer_fault=fault,
        request_observer_class=request_class, preliminary_request_done=preliminary_request_done,
        terminal_waiter_joined=terminal_task.done(), request_observer_joined=request_task.done(),
    )


class P7C15Turn3RequestObserverClass:
    REQUEST_OBSERVED = "REQUEST_OBSERVED"
    CANCELLED_BY_HARNESS_WITHOUT_REQUEST = "CANCELLED_BY_HARNESS_WITHOUT_REQUEST"
    OBSERVER_ERROR = "OBSERVER_ERROR"


@dataclass(frozen=True)
class P7C15Turn3ObserverOutcome:
    terminal: Any | None
    second_request: bool
    observer_fault: bool
    request_observer_class: str
    preliminary_request_done: bool
    terminal_waiter_joined: bool
    request_observer_joined: bool

    def __iter__(self):
        # Keep the accepted internal three-value call shape while exposing the
        # final post-join classification as explicit evidence for tests.
        return iter((self.terminal, self.second_request, self.observer_fault))


def _classify_turn3_request_observer(
    task: asyncio.Task[Any], *, harness_cancel_requested: bool,
) -> tuple[str, bool]:
    """Classify only after final ownership/join; preliminary snapshots do not decide."""
    if not task.done():
        return P7C15Turn3RequestObserverClass.OBSERVER_ERROR, False
    if task.cancelled():
        if harness_cancel_requested:
            return P7C15Turn3RequestObserverClass.CANCELLED_BY_HARNESS_WITHOUT_REQUEST, False
        return P7C15Turn3RequestObserverClass.OBSERVER_ERROR, False
    try:
        task.result()
    except BaseException:
        return P7C15Turn3RequestObserverClass.OBSERVER_ERROR, False
    return P7C15Turn3RequestObserverClass.REQUEST_OBSERVED, True


class P7C15ProductionChildOrchestrator:
    """The production child graph with the P7.C15 generation correction.

    The external runtime/client factory is the only offline seam.  The default
    factory is deliberately real-capable; tests substitute a fake runtime at
    that boundary and still traverse this same child graph.
    """

    def __init__(self, boot: Mapping[str, Any], journal: P7C15StageJournal, *,
                 runtime_factory: Callable[[], Any] | None = None, force_failure: bool = False,
                 stage_timeouts: Mapping[str, float] | None = None) -> None:
        self.boot, self.journal, self.runtime_factory = boot, journal, runtime_factory
        self.force_failure, self.budget = force_failure, EffectBudget(dict(boot["effect_ceiling"]))
        self.stage_timeouts = dict(p7c13.REAL_STAGE_TIMEOUTS)
        if stage_timeouts is not None:
            self.stage_timeouts.update(stage_timeouts)
        self.last_confirmed_stage = "INSTALLED_AUTHORITY"

    def _mark(self, stage: str, state: str = "CONFIRMED", effect_class: str = "none", error: BaseException | None = None) -> None:
        self.journal.append(stage, state, effect_class=effect_class, error=error)
        if state == "CONFIRMED":
            self.last_confirmed_stage = stage

    async def run_async(self) -> dict[str, Any]:
        p7c13.production_read_only_boundary_preflight({
            "persistent_home": Path(self.boot["codex_home"]), "repository": _repository(),
            "isolated_root": Path(self.boot["isolated_root"]),
            "isolated_sqlite": Path(self.boot["isolated_sqlite"]),
            "isolated_logs": Path(self.boot["isolated_logs"]),
            "controller_root": Path(self.boot["controller_db"]).parent,
            "controller_db": Path(self.boot["controller_db"]), "workdir": Path(self.boot["workdir"]),
            "approval_target": Path(self.boot["approval_target"]), "ledger": Path(self.boot["ledger_path"]),
            "boot": Path(self.boot["boot_authority_path"]), "result": Path(self.boot["child_result_path"]),
        })
        workdir = await p7c13._await_owned(
            asyncio.to_thread(p7c13.create_fresh_private_workdir, self.boot["workdir"]),
            timeout=self.stage_timeouts["thread_start"], stage="fresh workdir creation",
        )
        workdir_path = Path(workdir.path)
        workdir_stat = workdir_path.lstat()
        workdir_identity = (workdir_stat.st_dev, workdir_stat.st_ino)
        p7c13.validate_stable_workdir(workdir_path, workdir_identity)
        profile = p7c13.CodexProfile(P7C15_PROFILE_ID, self.boot["codex_home"], "P7.C15", self.boot["isolated_root"])
        isolation_authority = p7c13.IsolationPathAuthority(
            (profile,), controller_db_root=str(Path(self.boot["controller_db"]).parent),
            repository_root=str(_repository()), protected_roots=(),
        )
        isolated_state = p7c13.IsolatedStateRoot(isolation_authority)
        isolated_state.provision(profile)
        isolated_state.validate(profile)
        manager = self.runtime_factory() if self.runtime_factory is not None else _build_p7c15_runtime_manager(self.boot)
        configure = getattr(manager, "configure", None)
        if callable(configure):
            configure(self.boot)
        tracker = manager if isinstance(manager, GenerationTrackingRuntimeManager) else GenerationTrackingRuntimeManager(manager)
        self._mark("INSTALLED_AUTHORITY", effect_class="authority")
        self.budget.record("new_threads")
        runtime = await p7c13._await_owned(
            tracker.acquire(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["runtime_acquire_generation_1"], stage="runtime acquire generation 1",
        )
        client = runtime.client
        memory_marker, response_marker = p7c13.fresh_non_secret_markers()
        configure_markers = getattr(client, "configure_markers", None)
        if callable(configure_markers):
            configure_markers(memory_marker, response_marker)
        self._mark("RUNTIME_GENERATION_1", effect_class="runtime")
        catalog_adapter = P7C15SingleCatalogAcquisition(CodexModelCatalogAdapter(tracker))
        self._mark("MODEL_LIST_DISPATCH", "DISPATCHED", "model/list")
        self.budget.record("model/list")
        catalog = await p7c13._await_owned(
            catalog_adapter.acquire_once(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["model_list"], stage="model list",
        )
        self._mark("MODEL_LIST_CONFIRMED", effect_class="model/list")
        snapshot = ImmutableSemanticCatalogSnapshot.from_catalog(catalog)
        rebound = GenerationReboundCatalogView(snapshot, tracker)
        thread_lifecycle = CodexThreadLifecycleAdapter(tracker, rebound)
        turn_lifecycle = CodexTurnLifecycleAdapter(tracker, rebound)
        self._mark("THREAD_START_DISPATCH", "DISPATCHED", "thread/start")
        self.budget.record("thread/start")
        selected_model = snapshot.default_model
        reasoning_effort = snapshot.default_reasoning_effort_for(selected_model)
        started = await p7c13._await_owned(thread_lifecycle.start(
            P7C15_PROFILE_ID, model_id=snapshot.default_model,
            reasoning_effort=reasoning_effort, working_directory=workdir,
        ), timeout=self.stage_timeouts["thread_start"], stage="thread start")
        if started.status is not ThreadOperationStatus.START_CONFIRMED or started.binding is None:
            raise P7C15PreparationError("P7.C15 thread start not confirmed")
        binding = started.binding
        self._mark("THREAD_START_CONFIRMED", effect_class="thread/start")
        self._mark("TURN1_START_DISPATCH", "DISPATCHED", "turn/start")
        self.budget.record("turn/start")
        turn1 = await p7c13._await_owned(turn_lifecycle.start_turn(
            thread_binding=binding, model_id=selected_model, reasoning_effort=reasoning_effort,
            user_text=f"Remember {memory_marker}; respond with {response_marker}.", working_directory=workdir,
        ), timeout=self.stage_timeouts["turn1_start_terminal"], stage="turn 1 start")
        if turn1.status is not TurnStartStatus.CONFIRMED or turn1.binding is None:
            raise P7C15PreparationError("P7.C15 Turn 1 not confirmed")
        turn1_terminal = await p7c13._await_owned(
            turn_lifecycle.wait_turn(turn1.binding),
            timeout=self.stage_timeouts["turn1_start_terminal"], stage="turn 1 terminal",
        )
        if turn1_terminal.status is not TurnTerminalStatus.COMPLETED or response_marker not in " ".join(message.text for message in turn1_terminal.messages):
            raise P7C15PreparationError("Turn-1 response marker missing")
        self._mark("TURN1_START_CONFIRMED", effect_class="turn/start")
        self._mark("TURN1_TERMINAL", effect_class="terminal")
        await p7c13._await_owned(
            tracker.shutdown_profile(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["runtime_shutdown_generation_1"], stage="runtime shutdown generation 1",
        )
        self._mark("RUNTIME_SHUTDOWN_GENERATION_1", effect_class="runtime")
        second_runtime = await p7c13._await_owned(
            tracker.acquire(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["runtime_acquire_generation_2"], stage="runtime acquire generation 2",
        )
        self._mark("RUNTIME_GENERATION_2", effect_class="runtime")
        self._mark("THREAD_RESUME_DISPATCH", "DISPATCHED", "thread/resume")
        self.budget.record("thread/resume")
        resumed = await p7c13._await_owned(
            thread_lifecycle.resume(binding=binding, working_directory=workdir),
            timeout=self.stage_timeouts["thread_resume"], stage="thread resume",
        )
        if resumed.status is not ThreadOperationStatus.RESUME_CONFIRMED:
            raise P7C15PreparationError("P7.C15 thread resume not confirmed")
        self._mark("THREAD_RESUME_CONFIRMED", effect_class="thread/resume")
        self._mark("TURN2_START_DISPATCH", "DISPATCHED", "turn/start")
        self.budget.record("turn/start")
        turn2 = await p7c13._await_owned(turn_lifecycle.start_turn(
            thread_binding=binding, model_id=selected_model, reasoning_effort=reasoning_effort,
            user_text=f"Return the exact remembered marker {memory_marker}.", working_directory=workdir,
        ), timeout=self.stage_timeouts["turn2_start_terminal"], stage="turn 2 start")
        if turn2.status is not TurnStartStatus.CONFIRMED or turn2.binding is None:
            raise P7C15PreparationError("P7.C15 Turn 2 not confirmed")
        turn2_terminal = await p7c13._await_owned(
            turn_lifecycle.wait_turn(turn2.binding),
            timeout=self.stage_timeouts["turn2_start_terminal"], stage="turn 2 terminal",
        )
        if turn2_terminal.status is not TurnTerminalStatus.COMPLETED or memory_marker not in " ".join(message.text for message in turn2_terminal.messages):
            raise P7C15PreparationError("Turn-2 memory marker missing")
        self._mark("TURN2_START_CONFIRMED", effect_class="turn/start")
        self._mark("TURN2_TERMINAL", effect_class="terminal")
        if self.force_failure:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)

        target = Path(self.boot["approval_target"])
        if target.exists() or target.is_symlink():
            raise P7C15PreparationError("approval target must be absent")
        client = second_runtime.client

        # Turn 3 is an actual adapter dispatch.  The bridge/operator owns the
        # only request correlation and response path.
        turn3_prompt = p7c13.c11_explicit_escalation_prompt(str(target))
        self._mark("TURN3_START_DISPATCH", "DISPATCHED", "turn/start")
        self.budget.record("turn/start")
        turn3 = await p7c13._await_owned(turn_lifecycle.start_turn(
            thread_binding=binding, model_id=selected_model, reasoning_effort=reasoning_effort,
            user_text=turn3_prompt, working_directory=workdir,
        ), timeout=self.stage_timeouts["turn3_start_approval_terminal"], stage="turn 3 start")
        if turn3.status is not TurnStartStatus.CONFIRMED or turn3.binding is None:
            raise P7C15PreparationError("Turn-3 actual binding required")
        self._mark("TURN3_START_CONFIRMED", effect_class="turn/start")

        wire = p7c13.RootOnlyWireCommandAuthority(self.boot["wire_path"])
        recovery = p7c13.RootOnlyApprovalRecoveryJournal(self.boot["approval_journal_path"])
        operator = P7C15ProductionApprovalOperator(
            profile_id=P7C15_PROFILE_ID, thread_id=binding.thread_id, cwd=workdir.path,
            target=target, budget=self.budget, wire_authority=wire, recovery_journal=recovery,
        )
        operator.on_correlated = lambda: self._mark("APPROVAL_REQUEST", effect_class="approval")
        operator.turn_binding = turn3.binding
        bridge = p7c13.CodexApprovalBridge(profile_id=P7C15_PROFILE_ID, client=client, operator=operator)
        approval = await p7c13._await_owned(
            bridge.handle_next(), timeout=self.stage_timeouts["turn3_start_approval_terminal"], stage="turn 3 approval",
        )
        self._mark("APPROVAL_RESPONSE", effect_class="approval_responses")
        recovery.append({"event": "RESPONSE", "request_ordinal": operator.request_count, "response_count": 1, "status": approval.status.value})
        wire_record = wire.read()
        recovery_records = recovery.read()
        if (
            approval.status is not p7c13.ApprovalHandlingStatus.ALLOWED
            or operator.request_count != 1
            or operator.allow_count != 1 or operator.deny_count != 0
            or operator.response_unknown or self.budget.count("approval_responses") != 1
            or self.budget.count("allow_responses") != 1
            or wire_record["request_ordinal"] != 1
            or sum(record.get("event") == "RESPONSE" for record in recovery_records) != 1
        ):
            raise P7C15PreparationError("C12 exact matcher ALLOW required")
        self._mark("ALLOW", effect_class="allow_responses")

        turn3_terminal, second_request, observer_fault = await _observe_turn3_request_after_response(
            client=client, turn_lifecycle=turn_lifecycle, binding=turn3.binding,
            timeout=self.stage_timeouts["turn3_start_approval_terminal"],
            join_timeout=self.stage_timeouts["final_runtime_local_convergence"],
        )
        if observer_fault or second_request or turn3_terminal is None or turn3_terminal.status is not TurnTerminalStatus.COMPLETED:
            raise P7C15PreparationError("Turn-3 completion or second-request observer failed")
        self._mark("TURN3_TERMINAL", effect_class="terminal")
        target_stat = target.lstat()
        if (
            not stat.S_ISREG(target_stat.st_mode) or target_stat.st_uid != 0
            or target_stat.st_nlink != 1 or stat.S_IMODE(target_stat.st_mode) != 0o600
        ):
            raise P7C15PreparationError("approval target metadata unsafe")
        target.unlink()

        # Turn 4 uses the accepted owned observer/interrupt protocol.  The
        # interrupt budget is reserved inside the observer immediately before
        # the actual interrupt RPC.
        self._mark("TURN4_START_DISPATCH", "DISPATCHED", "turn/start")
        self.budget.record("turn/start")
        turn4 = await p7c13._await_owned(turn_lifecycle.start_turn(
            thread_binding=binding, model_id=selected_model, reasoning_effort=reasoning_effort,
            user_text=p7c13.TURN4_STIMULUS, working_directory=workdir,
        ), timeout=self.stage_timeouts["turn4_start"], stage="turn 4 start")
        if turn4.status is not TurnStartStatus.CONFIRMED or turn4.binding is None:
            raise P7C15PreparationError("Turn-4 actual binding required")
        self._mark("TURN4_START_CONFIRMED", effect_class="turn/start")
        turn4_gate = await p7c13.observe_owned_turn4(
            client=client, turn_lifecycle=turn_lifecycle, binding=turn4.binding, budget=self.budget,
            active_timeout=self.stage_timeouts["turn4_active_observation"],
            interrupt_timeout=self.stage_timeouts["turn4_interrupt_terminal"],
            join_timeout=self.stage_timeouts["final_runtime_local_convergence"],
        )
        if not turn4_gate.passed:
            if turn4_gate.unexpected_request_count:
                raise P7C15PreparationError("unexpected Turn-4 server request")
            raise P7C15PreparationError("Turn-4 active/interrupt gate failed")
        self._mark("TURN4_INTERRUPT", effect_class="turn/interrupt")
        if getattr(turn4_gate.terminal, "status", None) is not TurnTerminalStatus.FAILED:
            raise P7C15PreparationError("Turn-4 definitive terminal missing")
        self._mark("TURN4_TERMINAL", effect_class="terminal")
        await p7c13._await_owned(
            tracker.shutdown_profile(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["runtime_shutdown_before_scan"], stage="runtime shutdown before oracle",
        )
        self._mark("RUNTIME_SHUTDOWN_BEFORE_ORACLE", effect_class="runtime")
        # The canonical application delete still needs a confirmed live
        # generation; this reacquire changes only generation authority and
        # cannot trigger another model/list acquisition.
        await p7c13._await_owned(
            tracker.acquire(P7C15_PROFILE_ID),
            timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="runtime acquire delete generation",
        )

        profile = p7c13.CodexProfile(P7C15_PROFILE_ID, self.boot["codex_home"], "P7.C15", self.boot["isolated_root"])
        markers = (
            memory_marker.encode(), response_marker.encode(), str(target).encode(),
            turn3_prompt.encode(), p7c13.TURN4_STIMULUS.encode(),
        )
        oracle = p7c13.BoundedTargetOracle(profile, binding.thread_id, markers)
        before = oracle.observe()
        if not p7c13.predelete_observation_conclusive(before) or before.scan_errors:
            raise P7C15PreparationError("pre-delete physical oracle inconclusive")
        unrelated_before, target_paths = p7c13.target_metadata_snapshot(profile, binding.thread_id)

        storage = await p7c13._await_owned(
            p7c13.SqliteStorage.open(self.boot["controller_db"]),
            timeout=self.stage_timeouts["controller_open_binding"], stage="controller open",
        )
        # Once open succeeds, every exit—including schema, binding, official
        # observation, delete and post-delete failures—passes through exactly
        # one bounded owner close.
        try:
            schema_version = await p7c13._await_owned(
                storage.read(lambda connection: int(connection.execute("PRAGMA user_version").fetchone()[0])),
                timeout=self.stage_timeouts["controller_open_binding"], stage="schema read",
            )
            if getattr(manager, "scenario", "") == "schema_mismatch":
                schema_version = 3
            if schema_version != 4:
                raise P7C15PreparationError("controller schema is not v4")
            repository = p7c13.DialogueRepository(storage)
            dialogue = await p7c13._await_owned(
                repository.create_intent(dialogue_id=f"p7c15-{self.boot['run_id_hash'][:24]}", server_id="server-80", profile_id=P7C15_PROFILE_ID),
                timeout=self.stage_timeouts["controller_open_binding"], stage="dialogue create",
            )
            idle = await p7c13._await_owned(
                repository.confirm_created(dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id=binding.thread_id),
                timeout=self.stage_timeouts["controller_open_binding"], stage="dialogue confirm",
            )
            durable = await p7c13._await_owned(
                repository.get_live(), timeout=self.stage_timeouts["controller_open_binding"], stage="durable binding read",
            )
            if durable is None or durable.state is not p7c13.DialogueState.IDLE or durable.thread_id != binding.thread_id or durable.profile_id != P7C15_PROFILE_ID:
                raise P7C15PreparationError("schema-v4 durable binding invalid")
            if getattr(manager, "scenario", "") == "controller_mismatch":
                raise P7C15PreparationError("durable controller binding mismatch")
            self._mark("CONTROLLER_BINDING", effect_class="controller")

            official = p7c13.OfficialDeleteObservation(CodexThreadLifecycleAdapter(tracker, rebound))
            service = p7c13.DialogueDeleteService(
                storage, server_id="server-80", thread_lifecycle=official,
                local_cleanup=(
                    _P7C15FakeStorageCleanup(
                        storage, pending=getattr(manager, "scenario", "") == "confirmed_pending",
                        missing_tombstone=getattr(manager, "scenario", "") == "missing_tombstone",
                    )
                    if isinstance(manager, _FakeRuntimeManager)
                    else p7c13.DeleteStorageCleanupCoordinator(storage, tracker)
                ),
            )
            self._mark("THREAD_DELETE_DISPATCH", "DISPATCHED", "thread/delete")
            self.budget.record("thread/delete")
            application = await p7c13._await_owned(
                service.delete(p7c13.DialogueDeleteRequest(idle.dialogue_id, idle.version)),
                timeout=self.stage_timeouts["canonical_application_delete"], stage="canonical application delete",
            )
            if getattr(manager, "scenario", "") == "official_missing":
                official.status = None
            if official.calls != 1 or official.status is None:
                raise P7C15PreparationError("official delete observation missing")
            self._mark("THREAD_DELETE_RESULT", effect_class="thread/delete")
            application_status = getattr(application.status, "value", None)
            self._mark("APPLICATION_DELETE_RESULT", effect_class="application")
            if getattr(manager, "scenario", "") == "postdelete_schema_drift":
                await p7c13._await_owned(
                    storage.read(lambda connection: connection.execute("PRAGMA user_version = 3").fetchone()),
                    timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="test schema drift",
                )
            await p7c13._await_owned(
                tracker.shutdown_profile(P7C15_PROFILE_ID),
                timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="final runtime shutdown",
            )
            self._mark("RUNTIME_SHUTDOWN_FINAL", effect_class="runtime")
            tombstone = await p7c13._await_owned(
                p7c13.DeletionRepository(storage).get_tombstone(idle.dialogue_id),
                timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="tombstone read",
            )
            live_after = await p7c13._await_owned(
                repository.get_live(), timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="post-delete live-binding read",
            )
            post_schema_version = await p7c13._await_owned(
                storage.read(lambda connection: int(connection.execute("PRAGMA user_version").fetchone()[0])),
                timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="post-delete schema read",
            )
        finally:
            await p7c13._await_owned(
                storage.close(), timeout=self.stage_timeouts["final_runtime_local_convergence"], stage="controller close",
            )

        after_persistent = p7c13.BoundedTargetOracle(
            profile, binding.thread_id, markers, families=("persistent_sessions", "persistent_history"),
        ).observe()
        after_isolated = p7c13.BoundedTargetOracle(
            profile, binding.thread_id, markers, families=("isolated_sqlite", "isolated_logs"),
        ).observe()
        unrelated_after, _ = p7c13.target_metadata_snapshot(profile, binding.thread_id)
        unrelated_removed = p7c13.derived_unrelated_removal_fact(
            unrelated_before, unrelated_after, target_paths=target_paths,
        )
        try:
            isolated_state.validate(profile)
            envelope_valid = True
        except Exception:
            envelope_valid = False
        sqlite_descendants = p7c13.bounded_descendant_observation(Path(self.boot["isolated_sqlite"]))
        logs_descendants = p7c13.bounded_descendant_observation(Path(self.boot["isolated_logs"]))
        tombstone_bounded = (
            tombstone is not None and tombstone.dialogue_id == idle.dialogue_id
            and tombstone.thread_identity_sha256 == _sha256(binding.thread_id)
            and tombstone.expires_at_ms >= tombstone.deleted_at_ms
        )
        official_status = official.status.value
        recovery_class = p7c13.map_terminal_recovery_class(
            official_status=official_status, application_status=application_status,
        )
        if recovery_class == "UNKNOWN":
            return {
                "status": "UNKNOWN", "verdict": False, "last_confirmed_stage": self.last_confirmed_stage,
                "outcomes": {"delete": official_status, "application": application_status or "UNKNOWN", "post_schema": post_schema_version},
                "classes": {"recovery": "UNKNOWN"}, "runtime_child_quiescent": self._runtime_quiescent(manager),
            }
        if recovery_class == "CONFIRMED_PENDING":
            return {
                "status": "CONFIRMED_PENDING", "verdict": False, "last_confirmed_stage": self.last_confirmed_stage,
                "outcomes": {"delete": official_status, "application": application_status or "UNKNOWN", "post_schema": post_schema_version},
                "classes": {"recovery": "CONFIRMED_PENDING"}, "runtime_child_quiescent": self._runtime_quiescent(manager),
            }
        clean_envelope = (
            envelope_valid and post_schema_version == 4
            and sqlite_descendants[1] == sqlite_descendants[2] == 0
            and logs_descendants[1] == logs_descendants[2] == 0
        )
        accepted = p7c13.post_delete_acceptance(
            official_delete=official_status, application_result=application_status or "",
            tombstone_bounded=tombstone_bounded, live_binding=live_after is not None,
            envelope_valid=clean_envelope, isolated_sqlite_descendants=sqlite_descendants[0],
            isolated_logs_descendants=logs_descendants[0], persistent=after_persistent,
            isolated=after_isolated, scan_errors=sqlite_descendants[3] + logs_descendants[3],
            owned_children=None, owned_group_active=None, owned_group_zombies=None,
            unrelated_signals=None, budgets_ok=recovery_class == "COMPLETED",
            unrelated_target_specific_removal_detected=unrelated_removed,
        )
        if not accepted:
            raise P7C15PreparationError("post-delete observed oracle failed")
        self._mark("POST_DELETE_ORACLE", effect_class="oracle")
        runtime_child_quiescent = self._runtime_quiescent(manager)
        if not runtime_child_quiescent:
            raise P7C15PreparationError("runtime child not quiescent")
        return {
            "status": "PASS", "verdict": True, "last_confirmed_stage": self.last_confirmed_stage,
            "outcomes": {
                "turn2": "REBOUND_CONFIRMED", "turn3": "COMPLETED",
                "turn4": "INTERRUPTED", "delete": official_status,
                "application": application_status or "UNKNOWN",
            },
            "classes": {"flow": "P7C15_HARD_DELETE_CONTINUATION", "recovery": recovery_class},
            "runtime_child_quiescent": True,
        }

    @staticmethod
    def _runtime_quiescent(manager: Any) -> bool:
        value = getattr(manager, "runtime_quiescent", None)
        if value is not None:
            return bool(value)
        return not any(
            bool(getattr(manager, name, {}))
            for name in ("_runtimes", "_starting", "_unresolved")
        )


class P7C15ProductionApprovalOperator(p7c13.ProductionApprovalOperator):
    """P7.C15 composition hook for the request-correlated journal boundary."""

    on_correlated: Callable[[], Any] | None = None

    async def decide(self, request: Any) -> Any:
        decision = await super().decide(request)
        if self.request_count == 1 and self.wire_authority is not None and self.wire_authority.path.exists():
            callback = self.on_correlated
            if callback is not None:
                self.on_correlated = None
                callback()
        return decision


def _build_p7c15_runtime_manager(boot: Mapping[str, Any]) -> Any:
    """Build the installed Codex manager for the gated child default."""
    profile = p7c13.CodexProfile(P7C15_PROFILE_ID, boot["codex_home"], "P7.C15", boot["isolated_root"])
    authority = p7c13.IsolationPathAuthority(
        (profile,), controller_db_root=str(Path(boot["controller_db"]).parent),
        repository_root=str(_repository()), protected_roots=(),
    )
    routing = p7c13.FutureRuntimeRouting(profile)
    return p7c13.CodexRuntimeManager(
        (profile,), client_version="p7c15-future", isolation_authority=authority,
        parent_environment=routing.environment(),
    )


class P7C15ChildAccounting:
    def __init__(self, *, budget: EffectBudget | None = None) -> None:
        self.pre_child_budget = budget or EffectBudget()
        self.child: _LiveChild | None = None
        self.last_payload: dict[str, Any] | None = None

    def execute(self, mutate_and_fail: bool = False) -> dict[str, Any]:
        try:
            self.child = _LiveChild(EffectBudget())
            for effect in ("model/list", "thread/start", "turn/start"):
                self.child.budget.record(effect)
            if mutate_and_fail:
                raise ValueError("synthetic failure")
            return {"status": "PASS", "verdict": True, "classes": {"terminal": "COMPLETED"}}
        except Exception as error:
            category = error.category.value if isinstance(error, TurnLifecycleError) else None
            self.last_payload = {
                "status": "FAILED", "verdict": False, "classes": {"failure": "FAIL_CLOSED"},
                "terminal_exception_class": type(error).__name__, "terminal_error_category": category,
                "last_confirmed_stage": "TURN1_TERMINAL",
            }
            return self.last_payload


class _FakeClient:
    def __init__(self, scenario: str = "positive") -> None:
        self.scenario = scenario
        self.calls: list[str] = []
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._server_requests: asyncio.Queue[Any] = asyncio.Queue()
        self._terminal = asyncio.Event()
        self._turn = 0
        self._wire_responses: list[dict[str, Any]] = []
        self._wire_choices: list[tuple[str, str | None]] = []
        self.target: Path | None = None
        self.isolated_root: Path | None = None
        self.persistent_home: Path | None = None
        self._persistent_target: Path | None = None
        self._memory_marker = ""
        self._response_marker = ""
        self._created_mode: int | None = None
        self.thread_id = "thread-p7c15"
        self.material_marker = b"p7c15-fake-material"

    def configure(self, boot: Mapping[str, Any]) -> None:
        self.target = Path(boot["approval_target"])
        self.isolated_root = Path(boot["isolated_root"])
        self.persistent_home = Path(boot["codex_home"])
        self._workdir = boot["workdir"]

    def configure_markers(self, memory_marker: str, response_marker: str) -> None:
        self._memory_marker, self._response_marker = memory_marker, response_marker

    def _write_material(self) -> None:
        if self.scenario == "predelete_inconclusive" or self.isolated_root is None:
            return
        material = self.thread_id.encode() + self.material_marker + self._memory_marker.encode() + self._response_marker.encode()
        for root, name in ((self.isolated_root / "sqlite", "state.db"), (self.isolated_root / "logs", "app.log")):
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            root.joinpath(name).write_bytes(material)
        if self.persistent_home is not None and str(self.persistent_home) != "/root/.codex_second":
            sessions = self.persistent_home / "sessions"
            sessions.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._persistent_target = sessions / f"{self.thread_id}.jsonl"
            self._persistent_target.write_bytes(material)
            if self.scenario == "unrelated_removal":
                sessions.joinpath("unrelated-p7c15-current-run.jsonl").write_bytes(b"unrelated-current-run")
        if self.scenario == "scan_error":
            self.isolated_root.joinpath("sqlite", "unexpected-link").symlink_to("/tmp")

    def _approval_request(self, turn_id: str) -> Any:
        params = {
            "threadId": self.thread_id, "turnId": turn_id, "itemId": "item-approval",
            "startedAtMs": 10, "cwd": str(self._workdir),
            "command": shlex.join(["/bin/bash", "-lc", f"touch {self.target if self.scenario != 'approval_mismatch' else str(self.target) + '-wrong'}"]),
            "reason": "P7.C15 explicit escalation",
        }
        return InboundServerRequest(
            1, "approval-p7c15", "item/commandExecution/requestApproval", params,
        )

    def _materialize_target_after_allow(self) -> None:
        if self.target is None:
            raise P7C15PreparationError("fake target not configured")
        if self.scenario == "invalid_target_metadata":
            self.target.write_text("synthetic", encoding="utf-8")
            os.chmod(self.target, 0o644)
        else:
            # 0666 is intentional: the child-installed private umask must
            # produce the required 0600 target mode.
            self.target.touch(mode=0o666, exist_ok=False)
        self._created_mode = stat.S_IMODE(self.target.lstat().st_mode)

    async def request(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append(method)
        if method == "model/list":
            if self.scenario == "non_first_default":
                return {"data": [
                    {"id": "model-first", "model": "wire-first", "displayName": "First", "description": "synthetic", "hidden": False, "isDefault": False, "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "medium"}], "defaultReasoningEffort": "medium"},
                    {"id": "model-selected", "model": "wire-selected", "displayName": "Selected", "description": "synthetic", "hidden": False, "isDefault": True, "supportedReasoningEfforts": [{"reasoningEffort": "fast", "description": "fast"}], "defaultReasoningEffort": "fast"},
                ]}
            return {"data": [{"id": "model-p7c15", "model": "wire-p7c15", "displayName": "Synthetic", "description": "synthetic", "hidden": False, "isDefault": True, "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "medium"}], "defaultReasoningEffort": "medium"}]}
        if method == "thread/start":
            self._wire_choices.append((str(params.get("model")), params.get("effort")))
            self._workdir = params["cwd"] if isinstance(params.get("cwd"), str) else "/tmp"
            self._write_material()
            return {"thread": {"id": "thread-p7c15"}}
        if method == "thread/resume":
            return {"thread": {"id": "thread-p7c15"}}
        if method == "thread/delete":
            if self.scenario == "delete_unknown":
                return None  # type: ignore[return-value]
            if self.scenario == "delete_failure":
                raise RuntimeError("synthetic delete failure")
            if self.scenario not in {"postdelete_residual", "isolated_residual"} and self.isolated_root is not None:
                for path in tuple(self.isolated_root.rglob("*")):
                    if path.name != ".codexcontrol-state-root-v1" and (path.is_file() or path.is_symlink()):
                        path.unlink()
            if self._persistent_target is not None and self.scenario != "persistent_residual":
                self._persistent_target.unlink(missing_ok=True)
            if self.scenario == "unrelated_removal" and self.persistent_home is not None:
                self.persistent_home.joinpath("sessions", "unrelated-p7c15-current-run.jsonl").unlink(missing_ok=True)
            if self.scenario == "isolation_invalid" and self.isolated_root is not None:
                self.isolated_root.joinpath("unexpected-entry").write_bytes(b"invalid")
            return {}
        if method == "turn/start":
            self._wire_choices.append((str(params.get("model")), params.get("effort")))
            self._turn += 1
            turn_id = f"turn-p7c15-{self._turn}"
            if self._turn <= 3:
                text = "synthetic"
                if self._turn == 1 and self.scenario != "missing_turn1_response_marker":
                    text = self._response_marker
                elif self._turn == 2 and self.scenario != "missing_turn2_memory_marker":
                    text = self._memory_marker
                self._notifications.put_nowait({"method": "item/completed", "params": {"threadId": params["threadId"], "turnId": turn_id, "item": {"type": "agentMessage", "id": f"item-{self._turn}", "text": text}}})
                self._notifications.put_nowait({"method": "turn/completed", "params": {"threadId": params["threadId"], "turn": {"id": turn_id, "status": "completed"}}})
            if self._turn == 3:
                if self.target is None:
                    raise P7C15PreparationError("fake target not configured")
                self._server_requests.put_nowait(self._approval_request(turn_id))
                if self.scenario == "second_approval":
                    self._server_requests.put_nowait(self._approval_request(turn_id))
            if self._turn == 4:
                if self.scenario == "turn4_unexpected_request":
                    self._server_requests.put_nowait(InboundServerRequest(1, "unexpected-p7c15", "server/unexpected", {}))
                if self.scenario == "turn4_terminal_before_active":
                    self._notifications.put_nowait({"method": "turn/completed", "params": {"threadId": params["threadId"], "turn": {"id": turn_id, "status": "completed"}}})
            return {"turn": {"id": turn_id}}
        if method == "turn/interrupt":
            self._notifications.put_nowait({"method": "turn/completed", "params": {"threadId": params["threadId"], "turn": {"id": params["turnId"], "status": "interrupted"}}})
            return {}
        raise AssertionError(method)

    async def next_notification(self) -> dict[str, Any]:
        return await self._notifications.get()

    async def next_server_request(self) -> Any:
        return await self._server_requests.get()

    def owns_server_request(self, request: Any) -> bool:
        return request is not None

    async def respond_server_request(self, request: Any, result: dict[str, Any]) -> None:
        self._wire_responses.append(dict(result))
        if result.get("decision") == "accept":
            self._materialize_target_after_allow()

    async def wait_terminal(self) -> None:
        await self._terminal.wait()


@dataclass
class _FakeRuntime:
    profile_id: str
    generation: int
    client: _FakeClient


class _FakeRuntimeManager:
    def __init__(self, profile_id: str = P7C15_PROFILE_ID, scenario: str = "positive") -> None:
        self.profile_id, self.generation, self.scenario = profile_id, 1, scenario
        self.client = _FakeClient(scenario)
        self.shutdowns = 0
        self.runtime_quiescent = False
        self._workdir = "/tmp"

    def configure(self, boot: Mapping[str, Any]) -> None:
        self._workdir = boot["workdir"]
        self.client.configure(boot)

    async def acquire(self, profile_id: str) -> _FakeRuntime:
        if profile_id != self.profile_id:
            raise P7C15PreparationError("profile mismatch")
        if self.scenario == "stage_timeout" and self.generation == 1:
            await asyncio.Event().wait()
        return _FakeRuntime(profile_id, self.generation, self.client)

    async def shutdown_profile(self, profile_id: str) -> None:
        if profile_id != self.profile_id:
            raise P7C15PreparationError("profile mismatch")
        self.shutdowns += 1
        self.generation += 1
        self.runtime_quiescent = True


class _P7C15FakeStorageCleanup:
    """Offline storage boundary with the production service still in control."""

    def __init__(self, storage: Any, *, pending: bool = False, missing_tombstone: bool = False) -> None:
        self.storage, self.pending, self.missing_tombstone = storage, pending, missing_tombstone

    async def cleanup_confirmed(self, *, dialogue_id: str, expected_dialogue_version: int) -> Any:
        if self.pending:
            return type("CleanupOutcome", (), {
                "status": p7c13.DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE,
                "dialogue": await p7c13.DialogueRepository(self.storage).get_live(),
                "tombstone": None,
            })()
        finalized = await p7c13.DeletionRepository(self.storage).finalize_confirmed(
            dialogue_id=dialogue_id, expected_version=expected_dialogue_version,
            tombstone_expires_at_ms=int(time.time() * 1000) + 100000,
        )
        if getattr(self, "missing_tombstone", False):
            return type("CleanupOutcome", (), {
                "status": p7c13.DeleteStorageCleanupStatus.CONFIRMED_FINALIZED,
                "dialogue": None, "tombstone": None,
            })()
        return type("CleanupOutcome", (), {
            "status": p7c13.DeleteStorageCleanupStatus.CONFIRMED_FINALIZED,
            "dialogue": None, "tombstone": finalized.tombstone,
        })()

    async def contain_unknown(self, *, dialogue_id: str, expected_dialogue_version: int) -> Any:
        del dialogue_id, expected_dialogue_version
        return type("CleanupOutcome", (), {
            "status": p7c13.DeleteStorageCleanupStatus.UNKNOWN_PENDING,
            "dialogue": None, "tombstone": None,
        })()


async def _generation_handoff(*, rebound: bool) -> tuple[_FakeRuntimeManager, CodexModelCatalog, ThreadBinding, Any]:
    accepted = _FakeRuntimeManager()
    tracker = GenerationTrackingRuntimeManager(accepted)
    adapter = CodexModelCatalogAdapter(tracker)
    single_catalog = P7C15SingleCatalogAcquisition(adapter)
    first = await tracker.acquire(P7C15_PROFILE_ID)
    catalog = await single_catalog.acquire_once(P7C15_PROFILE_ID)
    binding_catalog: Any = GenerationReboundCatalogView(ImmutableSemanticCatalogSnapshot.from_catalog(catalog), tracker) if rebound else StaticGenerationCatalogView(catalog)
    thread = CodexThreadLifecycleAdapter(tracker, binding_catalog)
    turn = CodexTurnLifecycleAdapter(tracker, binding_catalog)
    workdir = TrustedWorkingDirectory("/tmp")
    started = await thread.start(P7C15_PROFILE_ID, model_id="model-p7c15", reasoning_effort="medium", working_directory=workdir)
    assert started.status is ThreadOperationStatus.START_CONFIRMED and started.binding is not None
    turn1 = await turn.start_turn(thread_binding=started.binding, model_id="model-p7c15", reasoning_effort="medium", user_text="one", working_directory=workdir)
    assert turn1.status is TurnStartStatus.CONFIRMED and turn1.binding is not None
    terminal = await turn.wait_turn(turn1.binding)
    assert terminal.status is TurnTerminalStatus.COMPLETED
    await accepted.shutdown_profile(P7C15_PROFILE_ID)
    await tracker.acquire(P7C15_PROFILE_ID)
    resumed = await thread.resume(binding=started.binding, working_directory=workdir)
    assert resumed.status is ThreadOperationStatus.RESUME_CONFIRMED
    turn2 = await turn.start_turn(thread_binding=started.binding, model_id="model-p7c15", reasoning_effort="medium", user_text="two", working_directory=workdir)
    return accepted, catalog, started.binding, turn2


class P7C15GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_catalog_reproduces_c14_root_cause_without_turn_rpc(self) -> None:
        # A concise reproduction uses the same strict adapter and stale catalog
        # boundary as the accepted P7.C14 failure.
        fake = _FakeRuntimeManager(); tracker = GenerationTrackingRuntimeManager(fake)
        catalog_adapter = CodexModelCatalogAdapter(tracker)
        await tracker.acquire(P7C15_PROFILE_ID); stale = await catalog_adapter.get_catalog(P7C15_PROFILE_ID)
        static = StaticGenerationCatalogView(stale); lifecycle = CodexTurnLifecycleAdapter(tracker, static)
        b = ThreadBinding(P7C15_PROFILE_ID, "thread-stale")
        await fake.shutdown_profile(P7C15_PROFILE_ID); await tracker.acquire(P7C15_PROFILE_ID)
        with self.assertRaises(TurnLifecycleError) as raised:
            await lifecycle.start_turn(thread_binding=b, model_id="model-p7c15", reasoning_effort="medium", user_text="two", working_directory=TrustedWorkingDirectory("/tmp"))
        self.assertIs(raised.exception.category, CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
        self.assertEqual(0, fake.client.calls.count("turn/start"))

    async def test_rebound_snapshot_reaches_one_turn2_and_preserves_semantics(self) -> None:
        manager, catalog, binding, result = await _generation_handoff(rebound=True)
        self.assertEqual(result.status, TurnStartStatus.CONFIRMED)
        self.assertEqual(1, manager.client.calls.count("model/list"))
        self.assertEqual(2, manager.client.calls.count("turn/start"))
        snapshot = ImmutableSemanticCatalogSnapshot.from_catalog(catalog)
        rebound = GenerationReboundCatalogView(snapshot, GenerationTrackingRuntimeManager(manager))
        self.assertEqual(snapshot.models, catalog.models)
        self.assertEqual(snapshot.default_model, "model-p7c15")
        self.assertEqual(snapshot.default_wire_model, "wire-p7c15")
        self.assertEqual(snapshot.supported_reasoning_efforts, (("model-p7c15", ("medium",)),))
        self.assertEqual(snapshot.default_reasoning_effort, (("model-p7c15", "medium"),))
        self.assertEqual(binding.profile_id, P7C15_PROFILE_ID)
        del rebound

    async def test_rebound_view_changes_only_runtime_generation(self) -> None:
        manager = _FakeRuntimeManager(); tracker = GenerationTrackingRuntimeManager(manager)
        provider = CodexModelCatalogAdapter(tracker); await tracker.acquire(P7C15_PROFILE_ID)
        original = await P7C15SingleCatalogAcquisition(provider).acquire_once(P7C15_PROFILE_ID)
        view = GenerationReboundCatalogView(ImmutableSemanticCatalogSnapshot.from_catalog(original), tracker)
        generation_one = await view.get_catalog(P7C15_PROFILE_ID)
        await manager.shutdown_profile(P7C15_PROFILE_ID); await tracker.acquire(P7C15_PROFILE_ID)
        generation_two = await view.get_catalog(P7C15_PROFILE_ID)
        self.assertEqual(generation_one.models, generation_two.models)
        self.assertEqual(generation_one.profile_id, generation_two.profile_id)
        self.assertEqual(generation_one.runtime_generation + 1, generation_two.runtime_generation)
        self.assertEqual(1, manager.client.calls.count("model/list"))

    async def test_second_catalog_provider_acquisition_is_blocked(self) -> None:
        manager = _FakeRuntimeManager(); tracker = GenerationTrackingRuntimeManager(manager)
        provider = P7C15SingleCatalogAcquisition(CodexModelCatalogAdapter(tracker))
        await tracker.acquire(P7C15_PROFILE_ID); await provider.acquire_once(P7C15_PROFILE_ID)
        with self.assertRaises(P7C15PreparationError):
            await provider.acquire_once(P7C15_PROFILE_ID)

    async def test_generation_regression_and_profile_mismatch_fail_closed(self) -> None:
        class Regression:
            def __init__(self) -> None:
                self.generations = iter((2, 1))

            async def acquire(self, profile_id: str) -> _FakeRuntime:
                return _FakeRuntime(profile_id, next(self.generations), _FakeClient())
        tracker = GenerationTrackingRuntimeManager(Regression())
        await tracker.acquire(P7C15_PROFILE_ID)
        with self.assertRaises(P7C15PreparationError):
            await tracker.acquire(P7C15_PROFILE_ID)
        class Mismatch:
            async def acquire(self, profile_id: str) -> _FakeRuntime:
                return _FakeRuntime("other", 1, _FakeClient())
        with self.assertRaises(P7C15PreparationError):
            await GenerationTrackingRuntimeManager(Mismatch()).acquire(P7C15_PROFILE_ID)


class P7C15AccountingJournalTests(unittest.TestCase):
    def _boot(self, root: Path) -> dict[str, str]:
        return {"source_head": "h", "source_tree": "t", "harness_blob": "l", "run_id_hash": "r"}

    def test_actual_live_budget_is_serialized_on_failure(self) -> None:
        execution = P7C15ChildAccounting()
        result = execution.execute(mutate_and_fail=True)
        payload = _p7c15_child_result_payload(self._boot(Path("/tmp")), result, execution.pre_child_budget, execution.child)
        self.assertEqual(1, payload["effect_counts"]["model/list"])
        self.assertEqual(1, payload["effect_counts"]["thread/start"])
        self.assertEqual(1, payload["effect_counts"]["turn/start"])
        self.assertNotEqual({0}, set(payload["effect_counts"].values()))
        self.assertTrue(all(payload["effect_counts"][key] <= limit for key, limit in P7C15_FROZEN_EFFECT_BUDGET.items()))

    def test_pre_child_failure_uses_outer_budget(self) -> None:
        budget = EffectBudget(); budget.record("new_threads")
        payload = _p7c15_child_result_payload(self._boot(Path("/tmp")), {"status": "FAILED"}, budget, None)
        self.assertEqual(1, payload["effect_counts"]["new_threads"])
        self.assertEqual(0, payload["effect_counts"]["model/list"])

    def test_stage_journal_is_bounded_safe_and_category_preserving(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c15-journal-") as directory:
            path = Path(directory) / "p7c15-stage-safe.jsonl"
            journal = P7C15StageJournal(path)
            journal.append("RUNTIME_GENERATION_1", "CONFIRMED", effect_class="runtime")
            error = TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
            journal.append("TURN2_START", "FAILED", effect_class="turn/start", error=error)
            records = journal.records()
            self.assertEqual(records[-1]["error_category"], "turn_precondition_changed")
            self.assertNotIn("thread_id", json.dumps(records)); self.assertNotIn("turn_id", json.dumps(records))
            st = path.lstat(); self.assertEqual(0o600, stat.S_IMODE(st.st_mode)); self.assertFalse(stat.S_ISLNK(st.st_mode)); self.assertEqual(1, st.st_nlink)


class P7C15Turn3ObserverTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_window_request_is_classified_after_join(self) -> None:
        class LateClient:
            def __init__(self) -> None:
                self.preliminary = asyncio.Event()
                self.release = asyncio.Event()
                self.responses = 1

            async def next_server_request(self) -> object:
                self.preliminary.set()
                await self.release.wait()
                return object()

        class ImmediateTerminal:
            async def wait_turn(self, _binding: object) -> Any:
                return type("Terminal", (), {"status": TurnTerminalStatus.COMPLETED})()

        client = LateClient()

        async def release_late_request() -> None:
            await client.preliminary.wait()
            client.release.set()

        releaser = asyncio.create_task(release_late_request())
        outcome = await _observe_turn3_request_after_response(
            client=client, turn_lifecycle=ImmediateTerminal(), binding=object(),
            timeout=1.0, join_timeout=1.0,
        )
        await releaser
        self.assertFalse(outcome.preliminary_request_done)
        self.assertEqual(P7C15Turn3RequestObserverClass.REQUEST_OBSERVED, outcome.request_observer_class)
        self.assertTrue(outcome.second_request)
        self.assertFalse(outcome.observer_fault)
        self.assertTrue(outcome.terminal_waiter_joined and outcome.request_observer_joined)
        self.assertEqual(1, client.responses)
        self.assertNotIn("turn4", vars(client))
        self.assertNotIn("controller", vars(client))
        self.assertNotIn("delete", vars(client))

    async def test_clean_terminal_cancellation_is_distinct_from_observer_error(self) -> None:
        class PendingClient:
            async def next_server_request(self) -> object:
                await asyncio.Event().wait()
                return object()

        class ImmediateTerminal:
            async def wait_turn(self, _binding: object) -> Any:
                return type("Terminal", (), {"status": TurnTerminalStatus.COMPLETED})()

        clean = await _observe_turn3_request_after_response(
            client=PendingClient(), turn_lifecycle=ImmediateTerminal(), binding=object(),
            timeout=1.0, join_timeout=1.0,
        )
        self.assertEqual(P7C15Turn3RequestObserverClass.CANCELLED_BY_HARNESS_WITHOUT_REQUEST, clean.request_observer_class)
        self.assertFalse(clean.second_request or clean.observer_fault)

        class ErrorClient:
            async def next_server_request(self) -> object:
                raise RuntimeError("observer failure")

        error = await _observe_turn3_request_after_response(
            client=ErrorClient(), turn_lifecycle=ImmediateTerminal(), binding=object(),
            timeout=1.0, join_timeout=1.0,
        )
        self.assertEqual(P7C15Turn3RequestObserverClass.OBSERVER_ERROR, error.request_observer_class)
        self.assertTrue(error.observer_fault)

    async def test_request_and_terminal_same_slice_is_non_pass_without_second_response(self) -> None:
        class SameSliceClient:
            async def next_server_request(self) -> object:
                return object()

        class SameSliceTerminal:
            async def wait_turn(self, _binding: object) -> Any:
                return type("Terminal", (), {"status": TurnTerminalStatus.COMPLETED})()

        outcome = await _observe_turn3_request_after_response(
            client=SameSliceClient(), turn_lifecycle=SameSliceTerminal(), binding=object(),
            timeout=1.0, join_timeout=1.0,
        )
        self.assertEqual(P7C15Turn3RequestObserverClass.REQUEST_OBSERVED, outcome.request_observer_class)
        self.assertTrue(outcome.second_request)
        self.assertFalse(outcome.observer_fault)


class P7C15GateLedgerTests(unittest.TestCase):
    def test_parent_exact_effect_gate_rejects_missing_positive_effect(self) -> None:
        counts = dict(P7C15_FROZEN_EFFECT_BUDGET)
        self.assertTrue(p7c15_exact_effect_pass_gate(counts))
        counts["turn/interrupt"] = 0
        self.assertFalse(p7c15_exact_effect_pass_gate(counts))
        counts = dict(P7C15_FROZEN_EFFECT_BUDGET)
        counts["thread/read"] = 1
        self.assertFalse(p7c15_exact_effect_pass_gate(counts))

    def test_production_watchdog_uses_real_deadline_authority(self) -> None:
        source = inspect.getsource(P7C15PreparedFutureExecutor._run_production)
        self.assertIn("P7C15_REAL_WATCHDOG_HARD_DEADLINE", source)
        for name in ("REAL_WATCHDOG_TERM_GRACE", "REAL_WATCHDOG_KILL_GRACE"):
            self.assertIn(name, source)
        self.assertNotIn("timeout_seconds=" + "5.0", source)
        self.assertNotIn("term_grace_seconds=" + "0.2", source)
        self.assertNotIn("kill_grace_seconds=" + "0.2", source)
        keys = [key for _, key, _ in P7C15_REAL_TIMEOUT_INVOCATION_PLAN]
        self.assertGreater(len(keys), len(set(keys)))
        self.assertEqual(P7C15_REAL_INTERNAL_TIMEOUT_BUDGET, sum(value for _, _, value in P7C15_REAL_TIMEOUT_INVOCATION_PLAN))
        self.assertGreater(P7C15_REAL_WATCHDOG_HARD_DEADLINE, P7C15_REAL_INTERNAL_TIMEOUT_BUDGET)
        self.assertGreater(P7C15_REAL_WATCHDOG_HARD_DEADLINE, p7c13.REAL_WATCHDOG_HARD_DEADLINE)
        self.assertNotIn("p7c13.REAL_WATCHDOG_HARD_DEADLINE", source)

    def test_ledger_reservation_precedes_run_parent_mutations_and_failures_consume(self) -> None:
        contract = _synthetic_contract()
        with tempfile.TemporaryDirectory(prefix="p7c15-order-") as directory:
            root = Path(directory)

            events: list[str] = []
            executor = P7C15PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=root / "p7c15-one-shot.json", mutation_events=events,
                child_dispatch=lambda _boot: 0,
            )
            executor.run(contract)
            self.assertEqual(
                ["LEDGER_RESERVED", "RUN_STATE_PARENT_CREATED", "RUN_WORK_PARENT_CREATED", "BOOT_CREATED", "CHILD_DISPATCHED"],
                events[:5],
            )

        def run_failure(name: str) -> tuple[list[str], Path, P7C15PreparedFutureExecutor]:
            directory = tempfile.TemporaryDirectory(prefix=f"p7c15-order-{name}-")
            root = Path(directory.name)
            events: list[str] = []
            def mkdir(path: Path) -> None:
                if path.name.endswith(f"{name}-parent-" + path.name.split(f"{name}-parent-")[-1]):
                    raise OSError(f"{name} parent failure")
                path.mkdir(mode=0o700, exist_ok=False)
            executor = P7C15PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=root / "p7c15-one-shot.json", mutation_events=events,
                child_dispatch=lambda _boot: 0, run_parent_mkdir=mkdir,
            )
            return events, root, executor

        events, root, executor = run_failure("state")
        with self.assertRaises(OSError):
            executor.run(contract)
        self.assertEqual(["LEDGER_RESERVED"], events)
        self.assertEqual("RESERVED", P7C15DurableOneShotLedger(root / "p7c15-one-shot.json").read()["state"])

        events, root, executor = run_failure("work")
        calls = {"count": 0}
        def fail_work(path: Path) -> None:
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("work parent failure")
            path.mkdir(mode=0o700, exist_ok=False)
        executor._run_parent_mkdir = fail_work
        with self.assertRaises(OSError):
            executor.run(contract)
        self.assertEqual(["LEDGER_RESERVED", "RUN_STATE_PARENT_CREATED"], events)
        self.assertEqual("RESERVED", P7C15DurableOneShotLedger(root / "p7c15-one-shot.json").read()["state"])

        with tempfile.TemporaryDirectory(prefix="p7c15-order-consumed-") as directory:
            root = Path(directory); ledger_path = root / "p7c15-one-shot.json"; events: list[str] = []
            executor = P7C15PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=ledger_path, mutation_events=events, child_dispatch=lambda _boot: 0,
            )
            self.assertTrue(executor.ledger.reserve(executor._record))
            with self.assertRaises(P7C15PreparationError):
                executor.run(contract)
            self.assertEqual([], events)
            self.assertEqual(0, executor.watchdog.child_count)

        with tempfile.TemporaryDirectory(prefix="p7c15-order-boot-") as directory:
            root = Path(directory); events: list[str] = []
            executor = P7C15PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=root / "p7c15-one-shot.json", mutation_events=events,
                child_dispatch=lambda _boot: 0,
            )
            with patch.object(P7C15RootOnlyBootAuthority, "create", side_effect=P7C15PreparationError("boot failure")):
                with self.assertRaises(P7C15PreparationError):
                    executor.run(contract)
            self.assertEqual(["LEDGER_RESERVED", "RUN_STATE_PARENT_CREATED", "RUN_WORK_PARENT_CREATED"], events)
            self.assertEqual(0, executor.watchdog.child_count)

    def test_production_child_has_no_fake_approval_accounting_dependency(self) -> None:
        source = inspect.getsource(P7C15ProductionChildOrchestrator) + inspect.getsource(_observe_turn3_request_after_response)
        self.assertNotIn("response_" + "calls", source)
        self.assertNotIn("pending_" + "approval_count", source)
        self.assertNotIn('reasoning_effort="medium"', source)
        self.assertNotIn("now_ms=lambda", source)
        self.assertIn("next_server_request", source)
        self.assertNotIn("await storage.close()", inspect.getsource(P7C15ProductionChildOrchestrator))
        self.assertIn("_await_owned", inspect.getsource(P7C15ProductionChildOrchestrator))

    def test_completed_recovery_requires_every_safe_parent_fact(self) -> None:
        recovery: dict[str, Any] = {
            "watchdog_status": "COMPLETED", "child_result_valid": True,
            "child_status": "PASS", "child_verdict": True,
            "runtime_child_quiescent": True, "exact_effect_gate": True,
            "owned_group_active": 0, "owned_group_zombies": 0,
            "group_scan_errors": 0, "child_count": 1, "retry_count": 0,
        }
        self.assertTrue(p7c15_completed_recovery_consistent(recovery))
        for field, value in (
            ("watchdog_status", "TIMEOUT"), ("child_result_valid", False),
            ("child_status", "FAILED"), ("child_verdict", False),
            ("runtime_child_quiescent", False), ("exact_effect_gate", False),
            ("owned_group_active", 1), ("owned_group_zombies", 1),
            ("group_scan_errors", 1), ("child_count", 2), ("retry_count", 1),
        ):
            mutated = dict(recovery); mutated[field] = value
            self.assertFalse(p7c15_completed_recovery_consistent(mutated), field)

    def test_parent_exit_projection_never_maps_failures_to_zero(self) -> None:
        self.assertEqual(2, p7c15_parent_exit_projection(P7C15WatchdogResult("DISABLED"), gate_enabled=False))
        for status in ("FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"):
            self.assertNotEqual(0, p7c15_parent_exit_projection(P7C15WatchdogResult(status)))
        self.assertEqual(0, p7c15_parent_exit_projection(P7C15WatchdogResult("COMPLETED")))

    def test_module_main_projects_an_executed_failed_watchdog_nonzero(self) -> None:
        with patch(__name__ + ".p7c15_real_entrypoint", return_value=P7C15WatchdogResult("CHILD_FAILURE")):
            self.assertEqual(1, _module_main(("--p7c15-real-run",)))

    def test_source_gate_mismatch_precedes_executor_and_ledger(self) -> None:
        contract = _synthetic_contract(); authority = _synthetic_authority(contract)
        calls = {"executor": 0}
        class CountingExecutor:
            def run(self, contract: P7C15ArchitectContract) -> P7C15WatchdogResult:
                calls["executor"] += 1
                return P7C15WatchdogResult("COMPLETED")
        with self.assertRaises(P7C15PreparationError):
            p7c15_real_entrypoint(environ={}, authority=authority, executor=CountingExecutor())
        self.assertEqual(0, calls["executor"])

    def test_p7c15_ledger_is_distinct_and_every_terminal_state_is_consumed(self) -> None:
        record = {"schema": P7C15_LEDGER_SCHEMA, "state": "RESERVED", "source_head": "h", "source_tree": "t", "harness_blob": "l", "run_id_hash": "r", "effect_counts": {}, "recovery": {}}
        with tempfile.TemporaryDirectory(prefix="p7c15-ledger-") as directory:
            for state in P7C15_LEDGER_STATES - {"RESERVED"}:
                path = Path(directory) / f"{state}.json"
                ledger = P7C15DurableOneShotLedger(path)
                self.assertTrue(ledger.reserve(record)); ledger.update(state=state)
                self.assertFalse(P7C15DurableOneShotLedger(path).reserve(record))
            self.assertNotEqual(P7C15_LEDGER_PATH, Path(directory) / "COMPLETED.json")
        self.assertNotEqual(P7C15_LEDGER_SCHEMA, p7c13.LEDGER_SCHEMA)

    def test_historical_p7c14_material_does_not_match_p7c15_target(self) -> None:
        self.assertFalse(str(Path("/root/p7c14-isolated-retained" )).split("/")[-1].startswith("p7c15-isolated-"))
        self.assertNotEqual(P7C15_PROFILE_ID, "p7c14-future-profile")

    def test_exact_authorized_synthetic_handoff_and_forced_failure(self) -> None:
        passed, proof = p7c15_synthetic_handoff()
        self.assertEqual("COMPLETED", passed.status)
        self.assertEqual(1, proof["temporary_reservations"])
        self.assertEqual(0, proof["p7c14_ledger_access"]); self.assertEqual(0, proof["p7c13_ledger_access"])
        self.assertEqual(1, proof["counters"]["model/list"]); self.assertEqual(1, proof["counters"]["turn2"])
        self.assertEqual(0, proof["real_codex_calls"]); self.assertEqual(0, proof["real_child_calls"])
        failed, failure_proof = p7c15_synthetic_handoff(force_failure=True)
        self.assertNotEqual(0, p7c15_parent_exit_projection(failed))
        self.assertEqual("FAILED", failure_proof["ledger"]["state"])
        self.assertIn("TERMINAL_EXCEPTION", {record["stage"] for record in failure_proof["records"]})
        self.assertEqual("turn_precondition_changed", failure_proof["records"][-1]["error_category"])
        self.assertEqual(1, failure_proof["child_result"]["effect_counts"]["model/list"])
        self.assertEqual("turn_precondition_changed", failure_proof["child_result"]["terminal_error_category"])
        self.assertEqual("TURN2_TERMINAL", failure_proof["child_result"]["last_confirmed_stage"])


class P7C15Repair1ProductionPathTests(unittest.TestCase):
    def _environment(self, contract: P7C15ArchitectContract) -> dict[str, str]:
        return {
            P7C15_FUTURE_REAL_GATE: contract.authorization_token,
            "P7C15_EXPECTED_HEAD": contract.expected_head,
            "P7C15_EXPECTED_TREE": contract.expected_tree,
            "P7C15_EXPECTED_LAUNCHER_BLOB": contract.expected_launcher_blob,
            "P7C15_EXPECTED_P7C14_LAUNCHER_BLOB": contract.expected_p7c14_launcher_blob,
            "P7C15_EXPECTED_P7C13_HARNESS_BLOB": contract.expected_p7c13_harness_blob,
            "P7C15_EXPECTED_P7C12_MATCHER_BLOB": contract.expected_p7c12_matcher_blob,
            "P7C15_EXPECTED_TESTS_INIT_BLOB": contract.expected_tests_init_blob,
            "P7C15_EXPECTED_TESTS_REAL_INIT_BLOB": contract.expected_tests_real_init_blob,
        }

    def test_production_command_binds_boot_not_result(self) -> None:
        contract = _synthetic_contract()
        with tempfile.TemporaryDirectory(prefix="p7c15-production-command-") as directory:
            ledger_path = Path(directory) / "p7c15-one-shot.json"
            seen: dict[str, Path] = {}
            def dispatch(boot_path: Path) -> int:
                seen["boot"] = boot_path
                boot = P7C15RootOnlyBootAuthority(boot_path).read()
                seen["result"] = Path(boot["child_result_path"])
                return p7c15_future_child_main(boot_path, runtime_factory=_FakeRuntimeManager, verify_installed=False)
            executor = P7C15PreparedFutureExecutor._production_with_authority(contract, ledger_path=ledger_path, child_dispatch=dispatch)
            executor.run(contract)
            command = tuple(executor.child_command_factory(seen["boot"]))
            self.assertEqual(str(seen["boot"]), command[-1])
            self.assertNotEqual(command[-1], str(seen["result"]))
            self.assertTrue(command[0].endswith("env")); self.assertEqual("/usr/bin/python", command[2])
            self.assertEqual(1, executor.watchdog.child_count); self.assertEqual(0, executor.watchdog.retry_count)

    def test_actual_source_gate_to_production_child_positive_handoff(self) -> None:
        contract = _synthetic_contract(); authority = _synthetic_authority(contract)
        with tempfile.TemporaryDirectory(prefix="p7c15-production-positive-") as directory:
            ledger_path = Path(directory) / "p7c15-one-shot.json"
            proof: dict[str, Any] = {}
            def dispatch(boot_path: Path) -> int:
                proof["boot"] = boot_path
                return p7c15_future_child_main(boot_path, runtime_factory=_FakeRuntimeManager, verify_installed=False)
            executor = P7C15PreparedFutureExecutor._production_with_authority(contract, ledger_path=ledger_path, child_dispatch=dispatch)
            result = p7c15_real_entrypoint(environ=self._environment(contract), authority=authority, executor=executor)
            boot = P7C15RootOnlyBootAuthority(proof["boot"]).read()
            child = P7C15ChildResultAuthority.read(boot["child_result_path"], boot)
            self.assertEqual("COMPLETED", result.status)
            self.assertEqual("PASS", child["status"]); self.assertTrue(child["verdict"])
            self.assertEqual(1, child["effect_counts"]["model/list"])
            self.assertEqual(4, child["effect_counts"]["turn/start"])
            self.assertEqual("COMPLETED", P7C15DurableOneShotLedger(ledger_path).read()["state"])
            self.assertEqual(0, executor.watchdog.retry_count)
            recovery = P7C15DurableOneShotLedger(ledger_path).read()["recovery"]
            self.assertTrue(p7c15_completed_recovery_consistent(recovery))
            self.assertEqual("COMPLETED", recovery["watchdog_status"])
            self.assertEqual(0, recovery["signals_sent_count"])

    def test_actual_child_failure_persists_live_budget_and_safe_stage(self) -> None:
        contract = _synthetic_contract(); authority = _synthetic_authority(contract)
        with tempfile.TemporaryDirectory(prefix="p7c15-production-failure-") as directory:
            ledger_path = Path(directory) / "p7c15-one-shot.json"; proof: dict[str, Any] = {}
            def dispatch(boot_path: Path) -> int:
                proof["boot"] = boot_path
                return p7c15_future_child_main(boot_path, runtime_factory=_FakeRuntimeManager, force_failure=True, verify_installed=False)
            executor = P7C15PreparedFutureExecutor._production_with_authority(contract, ledger_path=ledger_path, child_dispatch=dispatch)
            result = p7c15_real_entrypoint(environ=self._environment(contract), authority=authority, executor=executor)
            boot = P7C15RootOnlyBootAuthority(proof["boot"]).read()
            child = P7C15ChildResultAuthority.read(boot["child_result_path"], boot)
            journal_digest = _sha256(Path(boot["stage_journal_path"]).read_bytes())
            self.assertNotEqual(0, p7c15_parent_exit_projection(result))
            self.assertEqual("FAILED", P7C15DurableOneShotLedger(ledger_path).read()["state"])
            self.assertEqual("FAILED", child["status"]); self.assertGreater(child["effect_counts"]["model/list"], 0)
            self.assertEqual("TurnLifecycleError", child["terminal_exception_class"])
            self.assertEqual("turn_precondition_changed", child["terminal_error_category"])
            self.assertEqual("TURN2_TERMINAL", child["last_confirmed_stage"])
            self.assertEqual(journal_digest, child["stage_journal_sha256"])
            self.assertEqual(1, executor.watchdog.child_count); self.assertEqual(0, executor.watchdog.retry_count)
            recovery = P7C15DurableOneShotLedger(ledger_path).read()["recovery"]
            self.assertEqual("CHILD_FAILURE", recovery["watchdog_status"])
            self.assertTrue(recovery["child_result_valid"])
            self.assertEqual("FAILED", recovery["child_status"])
            self.assertFalse(recovery["child_verdict"])
            self.assertFalse(recovery["runtime_child_quiescent"])
            self.assertFalse(recovery["exact_effect_gate"])
            self.assertEqual(0, recovery["owned_group_active"])
            self.assertEqual(0, recovery["owned_group_zombies"])
            self.assertEqual(0, recovery["group_scan_errors"])
            self.assertEqual(1, recovery["child_count"])
            self.assertEqual(0, recovery["retry_count"])
            self.assertEqual("FAILED", recovery["child_result_authority_class"])
            self.assertNotIn("thread_id", json.dumps(recovery))
            self.assertNotIn("turn_id", json.dumps(recovery))

    def test_production_child_source_contains_accepted_generation_and_authorities(self) -> None:
        source = inspect.getsource(P7C15ProductionChildOrchestrator) + inspect.getsource(p7c15_future_child_main)
        for name in (
            "GenerationTrackingRuntimeManager", "ImmutableSemanticCatalogSnapshot", "GenerationReboundCatalogView",
            "P7C15SingleCatalogAcquisition", "P7C15StageJournal", "P7C15ChildResultAuthority",
            "DialogueDeleteService", "CodexApprovalBridge", "CodexTurnLifecycleAdapter",
        ):
            self.assertIn(name, source)


def _synthetic_boot(root: Path, contract: P7C15ArchitectContract) -> dict[str, Any]:
    paths = p7c15_fresh_run_paths("a" * 24, root=root, authority=root)
    paths["boot"] = str(root / "p7c15-boot-synthetic.json")
    paths["ledger_path"] = str(root / "p7c15-one-shot.json")
    return {
        "schema": P7C15_BOOT_SCHEMA, "source_head": contract.expected_head,
        "source_tree": contract.expected_tree, "harness_blob": contract.expected_launcher_blob,
        "run_id_hash": _sha256("synthetic-run"), "profile_id": P7C15_PROFILE_ID,
        "codex_home": "/root/.codex_second", "ledger_path": paths["ledger_path"],
        "boot_authority_path": paths["boot"], "child_result_path": paths["child_result"],
        "isolated_root": paths["isolated_root"], "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"),
        "isolated_logs": str(Path(paths["isolated_root"]) / "logs"), "controller_db": paths["controller_db"],
        "workdir": paths["workdir"], "approval_target": paths["approval_target"], "wire_path": paths["wire"],
        "approval_journal_path": paths["approval_journal"], "stage_journal_path": paths["stage"],
        "effect_ceiling": dict(P7C15_FROZEN_EFFECT_BUDGET), "import_roots": list(P7C15_IMPORT_ROOTS),
        "deterministic_import_root": P7C15_PYTHONPATH, "runtime_authority": "/usr/local/bin/codex",
    }


def _synthetic_contract() -> P7C15ArchitectContract:
    return P7C15ArchitectContract("synthetic-token", "synthetic-head", "synthetic-tree", "synthetic-p7c15-launcher", "f" * 40, "c" * 40, "m" * 40, "t" * 40, "r" * 40)


def _synthetic_authority(contract: P7C15ArchitectContract) -> P7C15SourceAuthority:
    return P7C15SourceAuthority(contract.expected_head, contract.expected_tree, contract.expected_launcher_blob, contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob, contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob, contract.expected_tests_real_init_blob, True, True)


def _validate_p7c15_fresh_paths(paths: Mapping[str, str], *, ledger_path: Path, boot_path: Path) -> None:
    """Validate every production boundary before boot creation or child spawn."""
    authority = ledger_path.parent
    try:
        authority_stat = authority.lstat()
    except OSError as error:
        raise P7C15PreparationError("P7.C15 authority root unavailable") from error
    if not stat.S_ISDIR(authority_stat.st_mode) or authority_stat.st_uid != 0 or stat.S_IMODE(authority_stat.st_mode) & 0o022:
        raise P7C15PreparationError("P7.C15 authority root unsafe")
    expected = {"isolated_root", "controller_db", "workdir", "approval_target", "boot", "child_result", "wire", "approval_journal", "stage"}
    if set(paths) not in (expected, expected | {"ledger_path"}) or not all(isinstance(value, str) and os.path.isabs(value) for value in paths.values()):
        raise P7C15PreparationError("P7.C15 fresh path set invalid")
    if paths["boot"] != str(boot_path):
        raise P7C15PreparationError("P7.C15 boot path drift")
    for key, value in paths.items():
        if key != "ledger_path" and not Path(value).name.startswith("p7c15-"):
            raise P7C15PreparationError("P7.C15 fresh namespace invalid")
        path = Path(value)
        if key != "ledger_path" and (path.exists() or path.is_symlink()):
            raise P7C15PreparationError("P7.C15 fresh authority already exists")
    if "ledger_path" in paths and paths["ledger_path"] != str(ledger_path):
        raise P7C15PreparationError("P7.C15 ledger path drift")
    physical_paths = [value for key, value in paths.items() if key != "ledger_path"]
    if len({os.path.realpath(value) for value in physical_paths}) != len(physical_paths):
        raise P7C15PreparationError("P7.C15 physical path alias")
    if not ledger_path.exists() or ledger_path.is_symlink() or ledger_path.name != "p7c15-one-shot.json":
        raise P7C15PreparationError("P7.C15 ledger path invalid")
    ledger_stat = ledger_path.lstat()
    if ledger_stat.st_uid != 0 or not stat.S_ISREG(ledger_stat.st_mode) or ledger_stat.st_nlink != 1 or stat.S_IMODE(ledger_stat.st_mode) != 0o600:
        raise P7C15PreparationError("P7.C15 ledger authority unsafe")


def _build_p7c15_production_boot(contract: P7C15ArchitectContract, record: Mapping[str, Any], paths: Mapping[str, str]) -> dict[str, Any]:
    isolated = Path(paths["isolated_root"])
    return {
        "schema": P7C15_BOOT_SCHEMA, "source_head": contract.expected_head,
        "source_tree": contract.expected_tree, "harness_blob": contract.expected_launcher_blob,
        "run_id_hash": record["run_id_hash"], "profile_id": P7C15_PROFILE_ID,
        "codex_home": "/root/.codex_second", "ledger_path": str(paths.get("ledger_path", P7C15_LEDGER_PATH)),
        "boot_authority_path": paths["boot"], "child_result_path": paths["child_result"],
        "isolated_root": paths["isolated_root"], "isolated_sqlite": str(isolated / "sqlite"),
        "isolated_logs": str(isolated / "logs"), "controller_db": paths["controller_db"],
        "workdir": paths["workdir"], "approval_target": paths["approval_target"],
        "wire_path": paths["wire"], "approval_journal_path": paths["approval_journal"],
        "stage_journal_path": paths["stage"], "effect_ceiling": dict(P7C15_FROZEN_EFFECT_BUDGET),
        "import_roots": list(P7C15_IMPORT_ROOTS), "deterministic_import_root": P7C15_PYTHONPATH,
        "runtime_authority": "/usr/local/bin/codex",
    }


def _p7c15_child_result_file_is_valid(path: Path, boot: Mapping[str, Any]) -> bool:
    try:
        P7C15ChildResultAuthority.read(path, boot)
        return True
    except (OSError, UnicodeError, json.JSONDecodeError, P7C15PreparationError):
        return False


class P7C15PreparedFutureExecutor:
    def __init__(self, ledger: P7C15DurableOneShotLedger, child: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None, *,
                 watchdog: Any | None = None, child_command_factory: Callable[[Path], Sequence[str]] | None = None,
                 run_paths: Mapping[str, str] | None = None, boot_path: Path | None = None,
                 test_only_watchdog_bounds: tuple[float, float, float] | None = None) -> None:
        self.ledger, self.child, self.calls = ledger, child, 0
        self.watchdog, self.child_command_factory = watchdog, child_command_factory
        self.run_paths, self.boot_path = dict(run_paths or {}), boot_path
        self.test_only_watchdog_bounds = test_only_watchdog_bounds

    @classmethod
    def production(cls, contract: P7C15ArchitectContract) -> "P7C15PreparedFutureExecutor":
        """Construct the one-shot, fresh-path, owned-child future executor."""
        return cls._production_with_authority(contract, ledger_path=P7C15_LEDGER_PATH)

    @classmethod
    def _production_with_authority(
        cls, contract: P7C15ArchitectContract, *, ledger_path: Path,
        process_factory: Callable[..., Any] = subprocess.Popen,
        active_group_probe: Callable[[int], int] | None = None,
        zombie_group_probe: Callable[[int], int] | None = None,
        group_scan_error_probe: Callable[[int], int] | None = None,
        child_dispatch: Callable[[Path], int] | None = None,
        test_only_watchdog_bounds: tuple[float, float, float] | None = None,
        mutation_events: list[str] | None = None,
        run_parent_mkdir: Callable[[Path], None] | None = None,
    ) -> "P7C15PreparedFutureExecutor":
        run_hash = _sha256(os.urandom(32))
        # Keep each mutable boundary on its own private parent.  These are
        # path strings only until the durable replay barrier is reserved.
        state_parent = ledger_path.parent.parent / f"p7c15-state-parent-{run_hash[:12]}"
        work_parent = ledger_path.parent.parent / f"p7c15-work-parent-{run_hash[:12]}"
        paths = p7c15_fresh_run_paths(run_hash[:32], root=state_parent, authority=ledger_path.parent)
        paths["workdir"] = str(work_parent / f"p7c15-work-{run_hash[:32]}")
        boot_path = Path(paths["boot"])
        record = {
            "schema": P7C15_LEDGER_SCHEMA, "state": "RESERVED",
            "source_head": contract.expected_head, "source_tree": contract.expected_tree,
            "harness_blob": contract.expected_launcher_blob, "run_id_hash": run_hash,
            "effect_counts": {}, "recovery": {},
        }
        watchdog = p7c13.OwnedParentChildWatchdog(
            process_factory=process_factory, active_group_probe=active_group_probe,
            zombie_group_probe=zombie_group_probe, group_scan_error_probe=group_scan_error_probe,
        )
        if child_dispatch is not None:
            watchdog.active_group_probe = active_group_probe or (lambda _pgid: 0)
            watchdog.zombie_group_probe = zombie_group_probe or (lambda _pgid: 0)
            watchdog.group_scan_error_probe = group_scan_error_probe or (lambda _pgid: 0)

        def command_factory(actual_boot: Path) -> Sequence[str]:
            return (
                "/usr/bin/env", f"PYTHONPATH={P7C15_PYTHONPATH}", "/usr/bin/python", "-m",
                "tests.real.test_p7_c15_final_hard_delete_successor", "--p7c15-future-child",
                "--boot-authority", str(actual_boot),
            )

        executor = cls(P7C15DurableOneShotLedger(ledger_path), watchdog=watchdog,
                       child_command_factory=command_factory, run_paths=paths, boot_path=boot_path,
                       test_only_watchdog_bounds=test_only_watchdog_bounds)
        executor._mutation_events = mutation_events if mutation_events is not None else []
        executor._run_parent_mkdir = run_parent_mkdir or (lambda path: path.mkdir(mode=0o700, exist_ok=False))
        executor._offline_child_dispatch = child_dispatch
        executor._record = record
        return executor

    def _event(self, name: str) -> None:
        events = getattr(self, "_mutation_events", None)
        if events is not None:
            events.append(name)

    def _production_boot(self, contract: P7C15ArchitectContract, record: Mapping[str, Any]) -> dict[str, Any]:
        if not self.run_paths or self.boot_path is None:
            raise P7C15PreparationError("P7.C15 fresh authority missing")
        paths = dict(self.run_paths)
        paths["boot"] = str(self.boot_path)
        if str(self.ledger.path) != paths.get("ledger_path", str(self.ledger.path)):
            paths["ledger_path"] = str(self.ledger.path)
        if str(self.ledger.path) != str(P7C15_LEDGER_PATH) and Path(self.ledger.path).name != "p7c15-one-shot.json":
            raise P7C15PreparationError("P7.C15 production ledger namespace invalid")
        _validate_p7c15_fresh_paths(paths, ledger_path=self.ledger.path, boot_path=self.boot_path)
        return _build_p7c15_production_boot(contract, record, paths)

    def _run_production(self, contract: P7C15ArchitectContract) -> P7C15WatchdogResult:
        record = dict(getattr(self, "_record", {}))
        if not record:
            raise P7C15PreparationError("P7.C15 production record missing")
        if not self.ledger.reserve(record):
            raise P7C15PreparationError("P7.C15 reservation consumed")
        self._event("LEDGER_RESERVED")
        paths = dict(self.run_paths or {})
        state_parent = Path(paths["isolated_root"]).parent
        work_parent = Path(paths["workdir"]).parent
        self._run_parent_mkdir(state_parent)
        self._event("RUN_STATE_PARENT_CREATED")
        self._run_parent_mkdir(work_parent)
        self._event("RUN_WORK_PARENT_CREATED")
        boot = self._production_boot(contract, record)
        P7C15RootOnlyBootAuthority(self.boot_path).create(boot)
        self._event("BOOT_CREATED")
        P7C15RootOnlyBootAuthority(self.boot_path).read()
        command = tuple(self.child_command_factory(self.boot_path))
        child_dispatch = getattr(self, "_offline_child_dispatch", None)
        if child_dispatch is not None:
            class _OfflineProcess:
                pid = os.getpid(); returncode = 0
                def wait(self, timeout: float | None = None) -> int:
                    self.returncode = child_dispatch(Path(command[-1]))
                    return self.returncode
            self.watchdog.process_factory = lambda *_args, **_kwargs: _OfflineProcess()
        hard_deadline, term_grace, kill_grace = self.test_only_watchdog_bounds or (
            P7C15_REAL_WATCHDOG_HARD_DEADLINE, p7c13.REAL_WATCHDOG_TERM_GRACE,
            p7c13.REAL_WATCHDOG_KILL_GRACE,
        )
        self._event("CHILD_DISPATCHED")
        observed = self.watchdog.run(
            command, result_path=boot["child_result_path"], timeout_seconds=hard_deadline,
            term_grace_seconds=term_grace, kill_grace_seconds=kill_grace,
            result_validator=lambda path: _p7c15_child_result_file_is_valid(path, boot),
        )
        child_status = None
        child_result_valid = False
        try:
            child_result = P7C15ChildResultAuthority.read(boot["child_result_path"], boot)
            child_status = child_result["status"]
            child_result_valid = True
        except (OSError, UnicodeError, json.JSONDecodeError, P7C15PreparationError):
            child_result = None
        exact_effect_gate = False
        if child_result is not None:
            exact_effect_gate = p7c15_exact_effect_pass_gate(child_result["effect_counts"])
        if observed.status == "TIMEOUT":
            state = "TIMEOUT"
        elif child_status in {"UNKNOWN", "CONFIRMED_PENDING"}:
            state = child_status
        elif (
            observed.status == "COMPLETED" and child_result_valid and child_status == "PASS"
            and child_result["verdict"] and child_result["runtime_child_quiescent"]
            and p7c15_exact_effect_pass_gate(child_result["effect_counts"])
            and observed.child_count == 1 and getattr(self.watchdog, "retry_count", 0) == 0
            and observed.owned_group_active == observed.owned_group_zombies == observed.group_scan_errors == 0
        ):
            state = "COMPLETED"
        else:
            state = "FAILED"
        recovery = {
            "child_result": _sha256(str(boot["child_result_path"])),
            "last_confirmed_stage": child_result.get("last_confirmed_stage") if child_result else "PARENT_VALIDATION",
            "watchdog_status": observed.status,
            "child_result_valid": child_result_valid,
            "child_status": child_status,
            "child_verdict": child_result.get("verdict") if child_result else None,
            "runtime_child_quiescent": child_result.get("runtime_child_quiescent") if child_result else None,
            "exact_effect_gate": exact_effect_gate if child_result else None,
            "owned_group_active": observed.owned_group_active,
            "owned_group_zombies": observed.owned_group_zombies,
            "group_scan_errors": observed.group_scan_errors,
            "signals_sent_count": len(observed.signals_sent),
            "signals_sent_classes": list(observed.signals_sent),
            "child_count": observed.child_count, "retry_count": getattr(self.watchdog, "retry_count", 0),
            "child_result_authority_hash": _sha256(Path(boot["child_result_path"]).read_bytes()) if child_result_valid else None,
            "child_result_authority_class": child_status,
        }
        if state == "COMPLETED" and not p7c15_completed_recovery_consistent(recovery):
            state = "FAILED"
        self.ledger.update(state=state, recovery=recovery)
        return P7C15WatchdogResult(state, child_result_valid=child_result_valid)

    def run(self, contract: P7C15ArchitectContract) -> P7C15WatchdogResult:
        if self.watchdog is not None:
            if self.calls:
                raise P7C15PreparationError("second child/retry forbidden")
            self.calls += 1
            return self._run_production(contract)
        if self.calls:
            raise P7C15PreparationError("second child/retry forbidden")
        self.calls += 1
        record = {"schema": P7C15_LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head, "source_tree": contract.expected_tree, "harness_blob": contract.expected_launcher_blob, "run_id_hash": _sha256(os.urandom(16)), "effect_counts": {}, "recovery": {}}
        if not self.ledger.reserve(record):
            raise P7C15PreparationError("P7.C15 reservation consumed")
        root = self.ledger.path.parent
        boot = _synthetic_boot(root, contract)
        P7C15RootOnlyBootAuthority(root / "p7c15-boot-synthetic.json").create(boot)
        if self.child is None:
            raise P7C15PreparationError("synthetic child missing")
        result = dict(self.child(boot))
        state = "COMPLETED" if result.get("status") == "PASS" else "FAILED"
        self.ledger.update(state=state, recovery={"terminal": result.get("last_confirmed_stage", "SYNTHETIC")})
        return P7C15WatchdogResult("COMPLETED" if state == "COMPLETED" else "CHILD_FAILURE")


def p7c15_real_entrypoint(
    *, environ: Mapping[str, str], authority: P7C15SourceAuthority | None = None,
    executor: P7C15PreparedFutureExecutor | None = None,
) -> P7C15WatchdogResult:
    current = authority or current_p7c15_source_authority()
    contract = _contract_from_environment(environ)
    if not p7c15_source_bundle_gate(environ, contract, current):
        raise P7C15PreparationError("P7C15_FUTURE_REAL_GATE=DISABLED_OR_SOURCE_MISMATCH")
    selected = executor or P7C15PreparedFutureExecutor.production(contract)
    return selected.run(contract)


def p7c15_synthetic_handoff(*, force_failure: bool = False) -> tuple[P7C15WatchdogResult, dict[str, Any]]:
    contract = _synthetic_contract()
    with tempfile.TemporaryDirectory(prefix="p7c15-handoff-") as directory:
        root = Path(directory); ledger = P7C15DurableOneShotLedger(root / "p7c15-one-shot.json")
        journal = P7C15StageJournal(root / "p7c15-stage-synthetic.jsonl")
        counters = {"model/list": 0, "turn2": 0, "real_codex": 0, "real_child": 0}
        child_result: dict[str, Any] = {}
        async def run() -> None:
            for stage, effect_class in (
                ("RUNTIME_GENERATION_1", "runtime"), ("MODEL_LIST", "model/list"),
                ("THREAD_START", "thread/start"), ("TURN1_START", "turn/start"),
                ("TURN1_TERMINAL", "terminal"), ("RUNTIME_SHUTDOWN_GENERATION_1", "runtime"),
            ):
                journal.append(stage, "CONFIRMED", effect_class=effect_class)
            manager = _FakeRuntimeManager(); tracker = GenerationTrackingRuntimeManager(manager)
            adapter = CodexModelCatalogAdapter(tracker); await tracker.acquire(P7C15_PROFILE_ID)
            catalog = await adapter.get_catalog(P7C15_PROFILE_ID); counters["model/list"] = manager.client.calls.count("model/list")
            snapshot = ImmutableSemanticCatalogSnapshot.from_catalog(catalog)
            await manager.shutdown_profile(P7C15_PROFILE_ID); await tracker.acquire(P7C15_PROFILE_ID)
            journal.append("RUNTIME_GENERATION_2", "CONFIRMED", effect_class="runtime")
            rebound = GenerationReboundCatalogView(snapshot, tracker)
            thread = CodexThreadLifecycleAdapter(tracker, rebound); turns = CodexTurnLifecycleAdapter(tracker, rebound)
            binding = ThreadBinding(P7C15_PROFILE_ID, "thread-p7c15")
            await thread.resume(binding=binding, working_directory=TrustedWorkingDirectory("/tmp")); journal.append("THREAD_RESUME", "CONFIRMED", effect_class="thread/resume")
            result = await turns.start_turn(thread_binding=binding, model_id=snapshot.default_model, reasoning_effort="medium", user_text="two", working_directory=TrustedWorkingDirectory("/tmp"))
            if result.status is not TurnStartStatus.CONFIRMED or result.binding is None: raise P7C15PreparationError("Turn 2 did not dispatch")
            counters["turn2"] = manager.client.calls.count("turn/start"); await turns.wait_turn(result.binding)
            journal.append("THREAD_RESUME", "CONFIRMED", effect_class="thread/resume")
            journal.append("TURN2_START", "CONFIRMED", effect_class="turn/start"); journal.append("TURN2_TERMINAL", "CONFIRMED", effect_class="terminal")
            if force_failure: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
        def child(boot: Mapping[str, Any]) -> Mapping[str, Any]:
            budget = EffectBudget(); child_obj = _LiveChild(budget)
            try:
                for effect in ("model/list", "thread/start", "turn/start"):
                    child_obj.budget.record(effect)
                asyncio.run(run())
                result = {"status": "FAILED" if force_failure else "PASS", "verdict": not force_failure, "last_confirmed_stage": "TURN2_TERMINAL", "classes": {"synthetic": "FAIL" if force_failure else "PASS"}}
                child_result.update(_p7c15_child_result_payload(boot, result, budget, child_obj))
                return result
            except Exception as error:
                journal.append("TERMINAL_EXCEPTION", "FAILED", effect_class="terminal", error=error)
                result = {"status": "FAILED", "verdict": False, "last_confirmed_stage": "TURN2_TERMINAL", "terminal_exception_class": type(error).__name__, "terminal_error_category": getattr(getattr(error, "category", None), "value", None)}
                child_result.update(_p7c15_child_result_payload(boot, result, budget, child_obj))
                return result
        executor = P7C15PreparedFutureExecutor(ledger, child)
        authority = _synthetic_authority(contract); environment = {P7C15_FUTURE_REAL_GATE: contract.authorization_token, **{name: value for name, value in (("P7C15_EXPECTED_HEAD", contract.expected_head), ("P7C15_EXPECTED_TREE", contract.expected_tree), ("P7C15_EXPECTED_LAUNCHER_BLOB", contract.expected_launcher_blob), ("P7C15_EXPECTED_P7C14_LAUNCHER_BLOB", contract.expected_p7c14_launcher_blob), ("P7C15_EXPECTED_P7C13_HARNESS_BLOB", contract.expected_p7c13_harness_blob), ("P7C15_EXPECTED_P7C12_MATCHER_BLOB", contract.expected_p7c12_matcher_blob), ("P7C15_EXPECTED_TESTS_INIT_BLOB", contract.expected_tests_init_blob), ("P7C15_EXPECTED_TESTS_REAL_INIT_BLOB", contract.expected_tests_real_init_blob))}}
        if not p7c15_source_bundle_gate(environment, contract, authority): raise P7C15PreparationError("synthetic source gate failed")
        watchdog = executor.run(contract); result = {"counters": counters, "journal_sha256": journal.digest(), "records": journal.records(), "ledger": ledger.read(), "child_result": child_result, "real_codex_calls": 0, "real_child_calls": 0, "temporary_reservations": 1, "p7c14_ledger_access": 0, "p7c13_ledger_access": 0}
        return watchdog, result


class P7C15Repair2ContinuationTests(unittest.IsolatedAsyncioTestCase):
    async def _run_continuation(
        self, scenario: str = "positive", *, stage_timeouts: Mapping[str, float] | None = None,
    ) -> tuple[dict[str, Any], _FakeRuntimeManager, list[dict[str, Any]]]:
        contract = _synthetic_contract()
        with tempfile.TemporaryDirectory(prefix="p7c15-repair2-continuation-") as directory:
            root = Path(directory)
            boot = _synthetic_boot(root, contract)
            boot["codex_home"] = str(root / "persistent-home")
            Path(boot["codex_home"]).mkdir(mode=0o700)
            authority = root / "authority"
            authority.mkdir(mode=0o700)
            fresh = p7c15_fresh_run_paths("b" * 24, root=root, authority=authority)
            for key in ("isolated_root", "controller_db", "workdir", "approval_target", "boot", "child_result", "wire", "approval_journal", "stage"):
                boot_key = {"boot": "boot_authority_path", "child_result": "child_result_path", "wire": "wire_path", "approval_journal": "approval_journal_path", "stage": "stage_journal_path"}.get(key, key)
                boot[boot_key] = fresh[key]
            boot["isolated_sqlite"] = str(Path(fresh["isolated_root"]) / "sqlite")
            boot["isolated_logs"] = str(Path(fresh["isolated_root"]) / "logs")
            boot["ledger_path"] = str(authority / "p7c15-one-shot.json")
            P7C15RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot)
            holder: dict[str, _FakeRuntimeManager] = {}

            def factory() -> _FakeRuntimeManager:
                manager = _FakeRuntimeManager(scenario=scenario)
                holder["manager"] = manager
                return manager

            code = await asyncio.to_thread(
                p7c15_future_child_main,
                boot["boot_authority_path"], runtime_factory=factory, verify_installed=False,
                stage_timeouts=stage_timeouts,
            )
            result = P7C15ChildResultAuthority.read(boot["child_result_path"], boot)
            reader = P7C15StageJournal.__new__(P7C15StageJournal)
            reader.path, reader.sequence = Path(boot["stage_journal_path"]), 0
            records = reader.records()
            # Return copies because the temporary authority is intentionally
            # destroyed at the end of this bounded fake run.
            result["child_code"] = code
            return result, holder["manager"], records

    async def test_production_shaped_full_handoff_has_only_actual_effects(self) -> None:
        result, manager, records = await self._run_continuation()
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["verdict"])
        self.assertEqual({
            "new_threads": 1, "model/list": 1, "thread/start": 1, "thread/resume": 1,
            "turn/start": 4, "approval_responses": 1, "allow_responses": 1,
            "turn/interrupt": 1, "thread/delete": 1, "thread/read": 0, "thread/list": 0,
            "second_child": 0, "real_retry": 0, "telegram": 0,
        }, result["effect_counts"])
        self.assertEqual(1, manager.client.calls.count("model/list"))
        self.assertEqual(1, manager.client.calls.count("thread/start"))
        self.assertEqual(1, manager.client.calls.count("thread/resume"))
        self.assertEqual(4, manager.client.calls.count("turn/start"))
        self.assertEqual(1, manager.client.calls.count("turn/interrupt"))
        self.assertEqual(1, manager.client.calls.count("thread/delete"))
        self.assertEqual(1, len(manager.client._wire_responses))
        self.assertEqual(["accept"], [response.get("decision") for response in manager.client._wire_responses])
        self.assertEqual(0o600, manager.client._created_mode)
        self.assertEqual(1, records.count(next(record for record in records if record["stage"] == "APPROVAL_REQUEST")))
        names = [record["stage"] for record in records]
        self.assertLess(names.index("TURN3_START_DISPATCH"), names.index("TURN3_START_CONFIRMED"))
        self.assertLess(names.index("APPROVAL_REQUEST"), names.index("APPROVAL_RESPONSE"))
        self.assertLess(names.index("APPROVAL_RESPONSE"), names.index("ALLOW"))
        self.assertLess(names.index("THREAD_DELETE_DISPATCH"), names.index("THREAD_DELETE_RESULT"))
        self.assertLess(names.index("THREAD_DELETE_RESULT"), names.index("APPLICATION_DELETE_RESULT"))
        self.assertIn("POST_DELETE_ORACLE", names)

    async def test_real_client_surface_and_second_request_observer(self) -> None:
        result, manager, _ = await self._run_continuation()
        client = manager.client
        self.assertEqual("PASS", result["status"])
        self.assertNotIn("response_" + "calls", vars(client))
        self.assertNotIn("pending_" + "approval_count", vars(client))
        self.assertEqual(1, len(client._wire_responses))
        second, manager, _ = await self._run_continuation("second_approval")
        self.assertEqual("FAILED", second["status"])
        self.assertEqual(1, len(manager.client._wire_responses))

    async def test_non_first_default_model_and_keyed_effort_survive_rebound(self) -> None:
        result, manager, _ = await self._run_continuation("non_first_default")
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, manager.client.calls.count("model/list"))
        self.assertEqual({("wire-selected", None), ("wire-selected", "fast")}, set(manager.client._wire_choices))
        self.assertEqual(4, manager.client._wire_choices.count(("wire-selected", "fast")))

    async def test_markers_are_required_before_progression(self) -> None:
        missing_response, manager, _ = await self._run_continuation("missing_turn1_response_marker")
        self.assertEqual("FAILED", missing_response["status"])
        self.assertEqual(0, manager.shutdowns)
        self.assertEqual(0, manager.client.calls.count("thread/resume"))
        missing_memory, manager, _ = await self._run_continuation("missing_turn2_memory_marker")
        self.assertEqual("FAILED", missing_memory["status"])
        self.assertEqual(1, manager.shutdowns)
        self.assertEqual(0, manager.client.calls.count("turn/interrupt"))

    async def test_internal_stage_timeout_is_owned_and_finite(self) -> None:
        result, manager, _ = await self._run_continuation(
            "stage_timeout", stage_timeouts={"runtime_acquire_generation_1": 0.01},
        )
        self.assertEqual("FAILED", result["status"])
        self.assertEqual([], manager.client.calls)
        self.assertEqual(0, result["effect_counts"]["real_retry"])

    async def test_every_open_controller_negative_path_has_one_bounded_close(self) -> None:
        original_close = p7c13.SqliteStorage.close
        close_counts: dict[int, int] = {}

        async def tracked_close(storage: Any) -> None:
            identity = id(storage)
            close_counts[identity] = close_counts.get(identity, 0) + 1
            await original_close(storage)

        scenarios = (
            "schema_mismatch", "controller_mismatch", "official_missing",
            "delete_failure", "delete_unknown", "confirmed_pending",
            "postdelete_schema_drift", "persistent_residual",
        )
        with patch.object(p7c13.SqliteStorage, "close", tracked_close):
            for scenario in scenarios:
                with self.subTest(scenario=scenario):
                    result, manager, _ = await self._run_continuation(scenario)
                    self.assertIn(result["status"], {"FAILED", "UNKNOWN", "CONFIRMED_PENDING"})
                    expected_delete = 0 if scenario in {"schema_mismatch", "controller_mismatch"} else 1
                    self.assertEqual(expected_delete, manager.client.calls.count("thread/delete"))
        self.assertTrue(close_counts)
        self.assertTrue(all(count == 1 for count in close_counts.values()))

    async def test_physical_negative_authorities_remain_fail_closed(self) -> None:
        for scenario in ("postdelete_schema_drift", "isolation_invalid", "unrelated_removal", "persistent_residual", "isolated_residual"):
            with self.subTest(scenario=scenario):
                result, manager, _ = await self._run_continuation(scenario)
                self.assertEqual("FAILED", result["status"])
                self.assertEqual(1, manager.client.calls.count("thread/delete"))

    async def test_required_negative_continuation_matrix_is_fail_closed(self) -> None:
        expectations = {
            "approval_mismatch": ("FAILED", 0, 0),
            "second_approval": ("FAILED", 0, 0),
            "invalid_target_metadata": ("FAILED", 0, 0),
            "turn4_unexpected_request": ("FAILED", 0, 1),
            "turn4_terminal_before_active": ("FAILED", 0, 0),
            "predelete_inconclusive": ("FAILED", 0, 1),
            "controller_mismatch": ("FAILED", 0, 1),
            "postdelete_residual": ("FAILED", 1, 1),
            "scan_error": ("FAILED", 0, 1),
            "missing_tombstone": ("FAILED", 1, 1),
        }
        for scenario, (status, delete_calls, interrupt_calls) in expectations.items():
            with self.subTest(scenario=scenario):
                result, manager, _ = await self._run_continuation(scenario)
                self.assertEqual(status, result["status"])
                self.assertEqual(delete_calls, manager.client.calls.count("thread/delete"))
                self.assertEqual(interrupt_calls, manager.client.calls.count("turn/interrupt"))
                self.assertEqual(0, result["effect_counts"]["real_retry"])
                self.assertLessEqual(result["effect_counts"]["thread/delete"], 1)

        unknown, manager, _ = await self._run_continuation("delete_unknown")
        self.assertEqual("UNKNOWN", unknown["status"])
        self.assertEqual("UNKNOWN", unknown["classes"]["recovery"])
        self.assertEqual(1, manager.client.calls.count("thread/delete"))
        pending, manager, _ = await self._run_continuation("confirmed_pending")
        self.assertEqual("CONFIRMED_PENDING", pending["status"])
        self.assertEqual("CONFIRMED_PENDING", pending["classes"]["recovery"])
        self.assertEqual(1, manager.client.calls.count("thread/delete"))

    def test_observed_acceptance_gate_rejects_missing_facts_or_effects(self) -> None:
        clean = p7c13.OracleObservation(0, 0, 0, (), "0" * 64)
        facts = dict(
            official_delete="DELETE_CONFIRMED", application_result="DELETED", tombstone_bounded=True,
            live_binding=False, envelope_valid=True, isolated_sqlite_descendants=0,
            isolated_logs_descendants=0, persistent=clean, isolated=clean, scan_errors=0,
            owned_children=0, owned_group_active=False, owned_group_zombies=0,
            unrelated_signals=0, budgets_ok=True,
        )
        self.assertTrue(p7c13.post_delete_acceptance(**facts))
        for field, value in (("tombstone_bounded", False), ("live_binding", True), ("scan_errors", 1), ("budgets_ok", False)):
            mutated = dict(facts); mutated[field] = value
            self.assertFalse(p7c13.post_delete_acceptance(**mutated))

    def test_historical_p7c14_residue_is_not_a_fresh_p7c15_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c15-oracle-") as directory:
            root = Path(directory); home = root / "home"; state = root / "isolated"
            (home / "sessions").mkdir(mode=0o700, parents=True); (state / "sqlite").mkdir(mode=0o700, parents=True); (state / "logs").mkdir(mode=0o700, parents=True)
            (home / "sessions" / "p7c14-retained").write_bytes(b"p7c14-retained-thread")
            profile = p7c13.CodexProfile(P7C15_PROFILE_ID, str(home), "P7.C15", str(state))
            observed = p7c13.BoundedTargetOracle(profile, "thread-p7c15-fresh", (b"p7c15-fresh-marker",)).observe()
            self.assertEqual((0, 0, 0), (observed.thread_count, observed.marker_count, observed.scan_errors))


def _p7c15_parse_child_boot(arguments: Sequence[str]) -> Path:
    if len(arguments) != 3 or arguments.count("--p7c15-future-child") != 1 or arguments.count("--boot-authority") != 1:
        raise P7C15PreparationError("P7.C15 child arguments invalid")
    boot_index = arguments.index("--boot-authority")
    if boot_index + 1 >= len(arguments) or not arguments[boot_index + 1] or arguments[boot_index + 1].startswith("--") or not os.path.isabs(arguments[boot_index + 1]):
        raise P7C15PreparationError("P7.C15 child boot missing")
    if any(item not in {"--p7c15-future-child", "--boot-authority", arguments[boot_index + 1]} for item in arguments):
        raise P7C15PreparationError("P7.C15 child arguments invalid")
    return Path(arguments[boot_index + 1]).absolute()


def p7c15_future_child_main(
    boot_path: str | Path, *, runtime_factory: Callable[[], Any] | None = None,
    force_failure: bool = False, verify_installed: bool = True,
    stage_timeouts: Mapping[str, float] | None = None,
) -> int:
    """Actual P7.C15 child dispatcher; returns zero only for a valid PASS."""
    boot = P7C15RootOnlyBootAuthority(boot_path).read()
    journal = P7C15StageJournal(boot["stage_journal_path"])
    pre_child_budget = EffectBudget(dict(boot["effect_ceiling"]))
    child: P7C15ProductionChildOrchestrator | None = None
    previous_umask = os.umask(0o077)
    try:
        if verify_installed:
            p7c13.InstalledRuntimeAuthority().verify()
        child = P7C15ProductionChildOrchestrator(
            boot, journal, runtime_factory=runtime_factory, force_failure=force_failure,
            stage_timeouts=stage_timeouts,
        )
        result = asyncio.run(child.run_async())
        result["stage_journal_sha256"] = journal.digest()
        payload = _p7c15_child_result_payload(boot, result, pre_child_budget, child)
        written = P7C15ChildResultAuthority.write(boot["child_result_path"], payload, boot)
        return 0 if written["status"] == "PASS" and written["verdict"] is True else 1
    except Exception as error:
        actual_budget = child.budget if child is not None else pre_child_budget
        try:
            journal.append("TERMINAL_EXCEPTION", "FAILED", effect_class="terminal", error=error)
        except P7C15PreparationError:
            pass
        category = getattr(getattr(error, "category", None), "value", None) if isinstance(error, TurnLifecycleError) else None
        failure = {
            "status": "FAILED", "verdict": False, "terminal_exception_class": type(error).__name__,
            "terminal_error_category": category, "last_confirmed_stage": child.last_confirmed_stage if child is not None else "PRE_CHILD",
            "classes": {"failure": "FAIL_CLOSED"}, "outcomes": {}, "runtime_child_quiescent": False,
            "stage_journal_sha256": journal.digest(),
        }
        try:
            P7C15ChildResultAuthority.write(
                boot["child_result_path"], _p7c15_child_result_payload(boot, failure, pre_child_budget, child), boot,
            )
        except (OSError, P7C15PreparationError):
            pass
        return 1
    finally:
        os.umask(previous_umask)


def _module_main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c15-real-run" in arguments:
        environment = dict(os.environ); contract = _contract_from_environment(environment)
        try:
            result = p7c15_real_entrypoint(environ=environment)
        except P7C15PreparationError:
            return 2
        return p7c15_parent_exit_projection(result)
    if "--p7c15-future-child" in arguments:
        try:
            boot_path = _p7c15_parse_child_boot(arguments)
            return p7c15_future_child_main(boot_path)
        except (ValueError, IndexError, OSError, P7C15PreparationError):
            return 1
    unittest.main(argv=[sys.argv[0], *arguments])
    return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
