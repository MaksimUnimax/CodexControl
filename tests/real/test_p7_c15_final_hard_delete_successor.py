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
import json
import os
import stat
import subprocess
import sys
import tempfile
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


def p7c15_fresh_run_paths(run_hash_fragment: str) -> dict[str, str]:
    """Return only fresh P7.C15 authorities for one safe run hash."""
    safe = "".join(char for char in run_hash_fragment if char in "0123456789abcdef")[:32]
    if not safe:
        raise P7C15PreparationError("safe run hash fragment required")
    root = Path("/root")
    authority = Path("/root/.codexcontrol")
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
        if self.sequence >= self.MAX_RECORDS or not stage or not state:
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
        result = [json.loads(line) for line in lines]
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
        "ledger_path", "child_result_path", "isolated_root", "controller_db", "workdir",
        "approval_target", "wire_path", "approval_journal_path", "stage_journal_path",
    })

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @classmethod
    def validate(cls, record: Mapping[str, Any]) -> dict[str, Any]:
        if set(record) != cls.KEYS or record.get("schema") != P7C15_BOOT_SCHEMA:
            raise P7C15PreparationError("P7.C15 boot schema invalid")
        if record.get("profile_id") != P7C15_PROFILE_ID:
            raise P7C15PreparationError("P7.C15 profile authority invalid")
        for key in ("source_head", "source_tree", "harness_blob", "run_id_hash", "ledger_path", "child_result_path"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise P7C15PreparationError("P7.C15 boot scalar invalid")
        return dict(record)

    def create(self, record: Mapping[str, Any]) -> dict[str, Any]:
        value = self.validate(record)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
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
        return self.validate(json.loads(self.path.read_text()))


@dataclass(frozen=True)
class P7C15WatchdogResult:
    status: str
    child_result_valid: bool = True


def p7c15_parent_exit_projection(result: P7C15WatchdogResult, *, gate_enabled: bool = True) -> int:
    if not gate_enabled:
        return 2
    return 0 if result.status == "COMPLETED" and result.child_result_valid else 1


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
    }


class _LiveChild:
    def __init__(self, budget: EffectBudget) -> None:
        self.budget = budget


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
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._turn = 0

    async def request(self, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
        self.calls.append(method)
        if method == "model/list":
            return {"data": [{"id": "model-p7c15", "model": "wire-p7c15", "displayName": "Synthetic", "description": "synthetic", "hidden": False, "isDefault": True, "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "medium"}], "defaultReasoningEffort": "medium"}]}
        if method == "thread/start":
            return {"thread": {"id": "thread-p7c15"}}
        if method == "thread/resume":
            return {"thread": {"id": "thread-p7c15"}}
        if method == "thread/delete":
            return {}
        if method == "turn/start":
            self._turn += 1
            turn_id = f"turn-p7c15-{self._turn}"
            self._notifications.put_nowait({"method": "item/completed", "params": {"threadId": params["threadId"], "turnId": turn_id, "item": {"type": "agentMessage", "id": f"item-{self._turn}", "text": "synthetic"}}})
            self._notifications.put_nowait({"method": "turn/completed", "params": {"threadId": params["threadId"], "turn": {"id": turn_id, "status": "completed"}}})
            return {"turn": {"id": turn_id}}
        if method == "turn/interrupt":
            return {}
        raise AssertionError(method)

    async def next_notification(self) -> dict[str, Any]:
        return await self._notifications.get()

    async def wait_terminal(self) -> None:
        await asyncio.Future()


@dataclass
class _FakeRuntime:
    profile_id: str
    generation: int
    client: _FakeClient


class _FakeRuntimeManager:
    def __init__(self, profile_id: str = P7C15_PROFILE_ID) -> None:
        self.profile_id, self.generation, self.client = profile_id, 1, _FakeClient()
        self.shutdowns = 0

    async def acquire(self, profile_id: str) -> _FakeRuntime:
        return _FakeRuntime(profile_id, self.generation, self.client)

    async def shutdown_profile(self, profile_id: str) -> None:
        if profile_id != self.profile_id:
            raise P7C15PreparationError("profile mismatch")
        self.shutdowns += 1
        self.generation += 1


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


class P7C15GateLedgerTests(unittest.TestCase):
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


def _synthetic_boot(root: Path, contract: P7C15ArchitectContract) -> dict[str, Any]:
    return {
        "schema": P7C15_BOOT_SCHEMA, "source_head": contract.expected_head,
        "source_tree": contract.expected_tree, "harness_blob": contract.expected_launcher_blob,
        "run_id_hash": _sha256("synthetic-run"), "profile_id": P7C15_PROFILE_ID,
        "ledger_path": str(root / "ledger.json"), "child_result_path": str(root / "result.json"),
        "isolated_root": str(root / "p7c15-isolated-synthetic"),
        "controller_db": str(root / "p7c15-controller-synthetic.sqlite3"),
        "workdir": str(root / "p7c15-work-synthetic"),
        "approval_target": str(root / "p7c15-approval-synthetic"),
        "wire_path": str(root / "p7c15-wire-synthetic.json"),
        "approval_journal_path": str(root / "p7c15-approval-journal-synthetic.json"),
        "stage_journal_path": str(root / "p7c15-stage-synthetic.jsonl"),
    }


def _synthetic_contract() -> P7C15ArchitectContract:
    return P7C15ArchitectContract("synthetic-token", "synthetic-head", "synthetic-tree", "synthetic-p7c15-launcher", "f" * 40, "c" * 40, "m" * 40, "t" * 40, "r" * 40)


def _synthetic_authority(contract: P7C15ArchitectContract) -> P7C15SourceAuthority:
    return P7C15SourceAuthority(contract.expected_head, contract.expected_tree, contract.expected_launcher_blob, contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob, contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob, contract.expected_tests_real_init_blob, True, True)


class P7C15PreparedFutureExecutor:
    def __init__(self, ledger: P7C15DurableOneShotLedger, child: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self.ledger, self.child, self.calls = ledger, child, 0

    def run(self, contract: P7C15ArchitectContract) -> P7C15WatchdogResult:
        if self.calls:
            raise P7C15PreparationError("second child/retry forbidden")
        self.calls += 1
        record = {"schema": P7C15_LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head, "source_tree": contract.expected_tree, "harness_blob": contract.expected_launcher_blob, "run_id_hash": _sha256(os.urandom(16)), "effect_counts": {}, "recovery": {}}
        if not self.ledger.reserve(record):
            raise P7C15PreparationError("P7.C15 reservation consumed")
        root = self.ledger.path.parent
        boot = _synthetic_boot(root, contract)
        P7C15RootOnlyBootAuthority(root / "p7c15-boot-synthetic.json").create(boot)
        result = dict(self.child(boot))
        state = "COMPLETED" if result.get("status") == "PASS" else "FAILED"
        self.ledger.update(state=state, recovery={"terminal": result.get("last_confirmed_stage", "SYNTHETIC")})
        return P7C15WatchdogResult("COMPLETED" if state == "COMPLETED" else "CHILD_FAILURE")

    @classmethod
    def production(cls, contract: P7C15ArchitectContract) -> "P7C15PreparedFutureExecutor":
        """Construct the future real path only after the source gate passes."""
        root = P7C15_LEDGER_PATH.parent
        run_hash_fragment = _sha256(os.urandom(16))[:24]
        fresh_paths = p7c15_fresh_run_paths(run_hash_fragment)

        def future_child(boot: Mapping[str, Any]) -> Mapping[str, Any]:
            command = (
                sys.executable, "-m", "tests.real.test_p7_c15_final_hard_delete_successor",
                "--p7c15-future-child", "--boot-authority", str(boot["child_result_path"]),
            )
            # The command is authority metadata here; real execution is never
            # entered by preparation because no P7.C15 token is supplied.
            del command, fresh_paths
            return {"status": "FAILED", "verdict": False, "last_confirmed_stage": "SOURCE_GATE", "classes": {"future": "NOT_RUN"}}

        return cls(P7C15DurableOneShotLedger(P7C15_LEDGER_PATH), future_child)


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
            for stage, effect_class in (
                ("TURN3_DISPATCH", "turn/start"), ("APPROVAL_RESPONSE", "approval"),
                ("TURN3_TERMINAL", "terminal"), ("TURN4_DISPATCH", "turn/start"),
                ("TURN4_INTERRUPT", "turn/interrupt"), ("TURN4_TERMINAL", "terminal"),
                ("CONTROLLER_BINDING", "controller"), ("THREAD_DELETE", "thread/delete"),
                ("APPLICATION_DELETE", "application"),
            ):
                journal.append(stage, "CONFIRMED", effect_class=effect_class)
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
            boot_index = arguments.index("--boot-authority") + 1
            Path(arguments[boot_index]).lstat()
        except (ValueError, IndexError, OSError):
            return 1
        return 1
    unittest.main(argv=[sys.argv[0], *arguments])
    return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
