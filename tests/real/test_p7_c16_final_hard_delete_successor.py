"""P7.C16 delete-chain authority successor preparation.

This module is preparation-only.  It composes the consumed P7.C15 child
engine, but owns a new gate, ledger, boot/result authorities and run paths.
The only runtime seam used by the offline handoff is the fake protocol/runtime
boundary; the application delete service and storage cleanup coordinator stay
real.
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

from codex_control.adapters.codex.isolation import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex.runtime import RuntimeQuiescenceProof
from codex_control.application.delete_storage_cleanup import DeleteStorageCleanupCoordinator
from codex_control.storage import SqliteStorage
from tests.real import test_p7_c12_strict_approval_matcher as p7c12
from tests.real import test_p7_c13_final_hard_delete_acceptance as p7c13
from tests.real import test_p7_c15_final_hard_delete_successor as p7c15


P7C16_FUTURE_REAL_GATE = "P7C16_FUTURE_REAL_GATE"
P7C16_EXPECTED_HEAD = "P7C16_EXPECTED_HEAD"
P7C16_EXPECTED_TREE = "P7C16_EXPECTED_TREE"
P7C16_EXPECTED_LAUNCHER_BLOB = "P7C16_EXPECTED_LAUNCHER_BLOB"
P7C16_EXPECTED_P7C15_LAUNCHER_BLOB = "P7C16_EXPECTED_P7C15_LAUNCHER_BLOB"
P7C16_EXPECTED_P7C14_LAUNCHER_BLOB = "P7C16_EXPECTED_P7C14_LAUNCHER_BLOB"
P7C16_EXPECTED_P7C13_HARNESS_BLOB = "P7C16_EXPECTED_P7C13_HARNESS_BLOB"
P7C16_EXPECTED_P7C12_MATCHER_BLOB = "P7C16_EXPECTED_P7C12_MATCHER_BLOB"
P7C16_EXPECTED_TESTS_INIT_BLOB = "P7C16_EXPECTED_TESTS_INIT_BLOB"
P7C16_EXPECTED_TESTS_REAL_INIT_BLOB = "P7C16_EXPECTED_TESTS_REAL_INIT_BLOB"
P7C16_LEDGER_PATH = Path("/root/.codexcontrol/p7c16-one-shot.json")
P7C16_IMPORT_ROOTS = ("/root/CodexControl/src", "/root/CodexControl")
P7C16_PYTHONPATH = os.pathsep.join(P7C16_IMPORT_ROOTS)
P7C16_PROFILE_ID = "p7c16-successor-profile"  # unique P7.C16 namespace only
P7C16_ENGINE_PROFILE_ID = p7c15.P7C15_PROFILE_ID
P7C16_AUTHENTICATED_HOME = "/root/.codex_second"
P7C16_LEDGER_SCHEMA = "p7c16-one-shot-v1"
P7C16_BOOT_SCHEMA = "p7c16-boot-v1"
P7C16_CHILD_RESULT_SCHEMA = "p7c16-child-result-v1"
P7C16_STATES = frozenset(("RESERVED", "COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"))
P7C16_REPAIR1_BASE_HEAD = "4f477e313192350414b1c157b6e1789135d11600"
P7C16_REPAIR1_BASE_TREE = "67a5276b34481ae3d118cbcb09dd73d2a6224973"
P7C16_CONSUMED_P7C15_SOURCE = "17f8907068aa58de85d92800b9d87621e59ad1a3"
P7C16_CONSUMED_P7C15_LAUNCHER = "ebe4ffab2d08494452c1b132fe2fed50f4830a6b"
P7C16_P7C15_EVIDENCE = "b0f1f2014e23c60cb611c3176ad5f880b50dfc35"
P7C16_P7C14_LAUNCHER = "fcce1352d581522b4c4ab0e5235d0b927d2eceb8"
P7C16_P7C13_HARNESS = "5a1fe8e32cd985b1e1845d73266211632e33950c"
P7C16_P7C12_MATCHER = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"
P7C16_TESTS_INIT = "080243830be797f87d23b459dbfd12c142a9d49a"
P7C16_TESTS_REAL_INIT = "23d73d7648ed14ef6857ee665784b87f57fde9f3"

# The positive P7.C15 invocation plan is frozen.  P7.C16 adds only bounded
# final convergence and a margin; offline tests may inject smaller values.
P7C16_REAL_CONVERGENCE_ALLOWANCE = 60.0
P7C16_REAL_WATCHDOG_MARGIN = 60.0
P7C16_REAL_CONVERGENCE_TIMEOUT = 30.0
P7C16_REAL_WATCHDOG_HARD_DEADLINE = (
    p7c15.P7C15_REAL_WATCHDOG_HARD_DEADLINE
    + P7C16_REAL_CONVERGENCE_ALLOWANCE
    + P7C16_REAL_WATCHDOG_MARGIN
)


class P7C16PreparationError(RuntimeError):
    """Finite, path-free preparation failure."""


class P7C16ControllerStorageMismatch(P7C16PreparationError):
    """Safe successor category for a known controller-authority mismatch."""

    category = "controller_storage_mismatch"


class P7C16LateFailure(P7C16PreparationError):
    """Synthetic late failure used only after delete-generation acquire."""


def _p7c16_error_category(error: BaseException) -> str | None:
    category = getattr(error, "category", None)
    value = getattr(category, "value", category)
    return value if isinstance(value, str) and value else None


P7C16_TEST_ONLY_PRODUCTION_FACTORY: Callable[["P7C16ArchitectContract"], "P7C16PreparedFutureExecutor"] | None = None


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _repository() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.run(("git", *args), cwd=_repository(), check=True, capture_output=True, text=True).stdout.strip()


def _blob(path: Path) -> str:
    return _git("hash-object", str(path))


def p7c16_fresh_run_paths(fragment: str, *, root: Path, authority: Path) -> dict[str, str]:
    safe = "".join(c for c in fragment if c in "0123456789abcdef")[:32]
    if not safe:
        raise P7C16PreparationError("safe run hash fragment required")
    return {
        "isolated_root": str(root / f"p7c16-isolated-{safe}"),
        "controller_db": str(authority / f"p7c16-controller-{safe}.sqlite3"),
        "workdir": str(root / f"p7c16-work-{safe}"),
        "approval_target": str(root / f"p7c16-approval-{safe}"),
        "boot": str(authority / f"p7c16-boot-{safe}.json"),
        "child_result": str(authority / f"p7c16-child-result-{safe}.json"),
        "wire": str(authority / f"p7c16-wire-{safe}.json"),
        "approval_journal": str(authority / f"p7c16-approval-journal-{safe}.json"),
        "stage": str(authority / f"p7c16-stage-{safe}.jsonl"),
    }


@dataclass(frozen=True)
class P7C16SourceAuthority:
    head: str
    tree: str
    launcher_blob: str
    p7c15_launcher_blob: str
    p7c14_launcher_blob: str
    p7c13_harness_blob: str
    p7c12_matcher_blob: str
    tests_init_blob: str
    tests_real_init_blob: str
    import_root_authority: bool
    tracked_clean: bool
    tracked_worktree_clean: bool = True
    tracked_index_clean: bool = True


@dataclass(frozen=True)
class P7C16ArchitectContract:
    authorization_token: str
    expected_head: str
    expected_tree: str
    expected_launcher_blob: str
    expected_p7c15_launcher_blob: str
    expected_p7c14_launcher_blob: str
    expected_p7c13_harness_blob: str
    expected_p7c12_matcher_blob: str
    expected_tests_init_blob: str
    expected_tests_real_init_blob: str
    expected_import_roots: tuple[str, str] = P7C16_IMPORT_ROOTS
    expected_tracked_worktree_clean: bool = True
    expected_tracked_index_clean: bool = True


def current_p7c16_source_authority() -> P7C16SourceAuthority:
    repo = _repository()
    clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    return P7C16SourceAuthority(
        _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}"), _blob(Path(__file__).resolve()),
        _blob(repo / "tests/real/test_p7_c15_final_hard_delete_successor.py"),
        _blob(repo / "tests/real/test_p7_c14_final_hard_delete_recovery.py"),
        _blob(repo / "tests/real/test_p7_c13_final_hard_delete_acceptance.py"),
        _blob(repo / "tests/real/test_p7_c12_strict_approval_matcher.py"),
        _blob(repo / "tests/__init__.py"), _blob(repo / "tests/real/__init__.py"),
        p7c15.validate_p7c15_import_root_authority(), clean and index_clean, clean, index_clean,
    )


def p7c16_source_bundle_gate(environ: Mapping[str, str], contract: P7C16ArchitectContract | None,
                             authority: P7C16SourceAuthority) -> bool:
    if (contract is None or contract.expected_import_roots != P7C16_IMPORT_ROOTS
            or contract.expected_tracked_worktree_clean is not True or contract.expected_tracked_index_clean is not True):
        return False
    expected = (contract.authorization_token, contract.expected_head, contract.expected_tree,
                contract.expected_launcher_blob, contract.expected_p7c15_launcher_blob,
                contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob,
                contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob,
                contract.expected_tests_real_init_blob)
    if not all(expected) or environ.get(P7C16_FUTURE_REAL_GATE) != contract.authorization_token:
        return False
    names = ((P7C16_EXPECTED_HEAD, contract.expected_head), (P7C16_EXPECTED_TREE, contract.expected_tree),
             (P7C16_EXPECTED_LAUNCHER_BLOB, contract.expected_launcher_blob),
             (P7C16_EXPECTED_P7C15_LAUNCHER_BLOB, contract.expected_p7c15_launcher_blob),
             (P7C16_EXPECTED_P7C14_LAUNCHER_BLOB, contract.expected_p7c14_launcher_blob),
             (P7C16_EXPECTED_P7C13_HARNESS_BLOB, contract.expected_p7c13_harness_blob),
             (P7C16_EXPECTED_P7C12_MATCHER_BLOB, contract.expected_p7c12_matcher_blob),
             (P7C16_EXPECTED_TESTS_INIT_BLOB, contract.expected_tests_init_blob),
             (P7C16_EXPECTED_TESTS_REAL_INIT_BLOB, contract.expected_tests_real_init_blob))
    try:
        repo = _repository()
        actual_protected = (
            _blob(Path(__file__)), _blob(repo / "tests/real/test_p7_c15_final_hard_delete_successor.py"),
            _blob(repo / "tests/real/test_p7_c14_final_hard_delete_recovery.py"),
            _blob(repo / "tests/real/test_p7_c13_final_hard_delete_acceptance.py"),
            _blob(repo / "tests/real/test_p7_c12_strict_approval_matcher.py"),
            _blob(repo / "tests/__init__.py"), _blob(repo / "tests/real/__init__.py"),
        )
        actual_head = _git("rev-parse", "HEAD")
        actual_tree = _git("rev-parse", "HEAD^{tree}")
        clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
        index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    actual_authority_hashes = (authority.launcher_blob, authority.p7c15_launcher_blob,
                               authority.p7c14_launcher_blob, authority.p7c13_harness_blob,
                               authority.p7c12_matcher_blob, authority.tests_init_blob,
                               authority.tests_real_init_blob)
    return (all(environ.get(name) == value for name, value in names)
            and actual_authority_hashes == actual_protected
            and authority.head == actual_head and authority.tree == actual_tree and clean and index_clean
            and authority == P7C16SourceAuthority(contract.expected_head, contract.expected_tree,
                contract.expected_launcher_blob, contract.expected_p7c15_launcher_blob,
                contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob,
                contract.expected_p7c12_matcher_blob, contract.expected_tests_init_blob,
                contract.expected_tests_real_init_blob, True, True, True, True))


def _contract_from_environment(environ: Mapping[str, str]) -> P7C16ArchitectContract:
    return P7C16ArchitectContract(
        environ.get(P7C16_FUTURE_REAL_GATE, ""), environ.get(P7C16_EXPECTED_HEAD, ""),
        environ.get(P7C16_EXPECTED_TREE, ""), environ.get(P7C16_EXPECTED_LAUNCHER_BLOB, ""),
        environ.get(P7C16_EXPECTED_P7C15_LAUNCHER_BLOB, ""), environ.get(P7C16_EXPECTED_P7C14_LAUNCHER_BLOB, ""),
        environ.get(P7C16_EXPECTED_P7C13_HARNESS_BLOB, ""), environ.get(P7C16_EXPECTED_P7C12_MATCHER_BLOB, ""),
        environ.get(P7C16_EXPECTED_TESTS_INIT_BLOB, ""), environ.get(P7C16_EXPECTED_TESTS_REAL_INIT_BLOB, ""),
    )


class P7C16StageJournal(p7c15.P7C15StageJournal):
    """Independent bounded successor journal with safe late-chain stages."""

    def append(self, stage: str, state: str, *, effect_class: str = "none", error: BaseException | None = None) -> None:
        if stage not in {"CONTROLLER_BINDING", "DELETE_CLEANUP_AUTHORITY_CONFIRMED", "DELETE_CHAIN_READY",
                         "THREAD_DELETE_DISPATCH", "THREAD_DELETE_RESULT", "APPLICATION_DELETE_RESULT",
                         "TERMINAL_EXCEPTION"} and len(stage) > 96:
            raise P7C16PreparationError("stage authority invalid")
        if self.sequence >= self.MAX_RECORDS or not stage or not state or len(stage) > 96 or len(state) > 32:
            raise P7C16PreparationError("stage journal bound exceeded")
        self.sequence += 1
        record: dict[str, Any] = {"schema": "p7c16-stage-v1", "sequence": self.sequence,
                                  "stage": stage, "state": state, "effect_class": effect_class}
        if error is not None:
            record["error_class"] = type(error).__name__[:96]
            category = getattr(error, "category", None)
            value = getattr(category, "value", category)
            if isinstance(value, str) and len(value) <= 96:
                record["error_category"] = value
        raw = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(self.path.read_bytes()) + len(raw) > self.MAX_BYTES:
            raise P7C16PreparationError("stage journal too large")
        with self.path.open("ab") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())


class P7C16LateBoundControllerRuntimeView:
    """Immutable early root authority, upgraded only after the DB exists."""

    def __init__(self, underlying: Any, profile: Any, repository: Path, controller_db: str) -> None:
        self.underlying, self.profile_id, self.profile = underlying, profile.profile_id, profile
        self.repository, self.controller_db_path = repository, controller_db
        self._root_authority = IsolationPathAuthority((profile,), controller_db_root=str(Path(controller_db).parent),
                                                       repository_root=str(repository), protected_roots=())
        self._exact_authority: IsolationPathAuthority | None = None

    @property
    def authority(self) -> IsolationPathAuthority:
        if self._exact_authority is not None:
            return self._exact_authority
        return self._root_authority

    def bind_exact_path(self) -> IsolationPathAuthority:
        path = Path(self.controller_db_path)
        if (not path.is_absolute() or not path.name.startswith("p7c16-controller-")
                or path.is_symlink() or not path.is_file()):
            raise ValueError("controller_storage_mismatch")
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_nlink != 1 or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("controller_storage_mismatch")
        exact = IsolationPathAuthority((self.profile,), controller_db_path=str(path), repository_root=str(self.repository), protected_roots=())
        exact.validate_runtime_authority()
        self._exact_authority = exact
        return exact

    def bind_exact(self, storage: SqliteStorage) -> IsolationPathAuthority:
        exact = self.bind_exact_path()
        if not storage.matches_database_path(exact.controller_db_path):
            raise ValueError("controller_storage_mismatch")
        return exact

    def validate_runtime_authority(self, **kwargs: Any) -> None:
        self.authority.validate_runtime_authority(**kwargs)


class P7C16RuntimeManagerView(p7c15.GenerationTrackingRuntimeManager):
    """Delegating facade; the underlying manager owns every reservation."""

    def __init__(self, underlying: Any, boot: Mapping[str, Any]) -> None:
        super().__init__(underlying)
        self.underlying = underlying
        self.engine_profile_id = P7C16_ENGINE_PROFILE_ID
        # The composed P7.C15 engine supplies its frozen profile identity to
        # lifecycle adapters.  P7.C16 owns only the successor authorities.
        profile = underlying.profile(P7C16_ENGINE_PROFILE_ID)
        self._authority_view = P7C16LateBoundControllerRuntimeView(
            underlying, profile, _repository(), boot["controller_db"])
        self.acquire_count = 0

    @property
    def isolation_authority(self) -> IsolationPathAuthority:
        if self._authority_view._exact_authority is None and Path(self._authority_view.controller_db_path).exists():
            self._authority_view.bind_exact_path()
        return self._authority_view.authority

    async def acquire(self, profile_id: str) -> Any:
        self.acquire_count += 1
        runtime = await super().acquire(profile_id)
        if getattr(self.underlying, "generation", 0) >= 3 and getattr(self.underlying, "p7c16_failure_scenario", "") in {
            "late_failure", "late_failure_shutdown_failure",
        }:
            raise P7C16LateFailure("P7.C16 synthetic late failure")
        return runtime

    def configure(self, boot: Mapping[str, Any]) -> None:
        configure = getattr(self.underlying, "configure", None)
        if callable(configure):
            configure(boot)

    async def shutdown_profile(self, profile_id: str) -> None:
        if profile_id != self.engine_profile_id:
            raise P7C16PreparationError("effective engine profile mismatch")
        await self.underlying.shutdown_profile(profile_id)

    async def reserve(self, profile_id: str) -> Any:
        if profile_id != self.engine_profile_id:
            raise P7C16PreparationError("effective engine profile mismatch")
        return await self.underlying.reserve(profile_id)

    async def recreate_isolated_state_root(self, reservation: Any) -> None:
        # Do not inspect, wrap, or replace the token.  The underlying manager
        # validates its own reservation identity and owns recreation.
        await self.underlying.recreate_isolated_state_root(reservation)

    def profile(self, profile_id: str) -> Any:
        return self.underlying.profile(profile_id)

    def bind_controller(self, storage: SqliteStorage) -> IsolationPathAuthority:
        return self._authority_view.bind_exact(storage)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.underlying, name)


class P7C16ProductionChildOrchestrator(p7c15.P7C15ProductionChildOrchestrator):
    """Consumed child graph with only the controller-authority correction."""

    def __init__(self, boot: Mapping[str, Any], journal: P7C16StageJournal, *, runtime_factory: Callable[[], Any] | None = None,
                 force_failure: bool = False, stage_timeouts: Mapping[str, float] | None = None) -> None:
        self.p7c16_manager: P7C16RuntimeManagerView | None = None
        self._raw_runtime_factory = runtime_factory
        self._delete_generation_acquired = False
        self._convergence_failed = False

        def factory() -> P7C16RuntimeManagerView:
            raw = runtime_factory() if runtime_factory is not None else p7c15._build_p7c15_runtime_manager(boot)
            configure_raw = getattr(raw, "configure", None)
            if callable(configure_raw):
                configure_raw(boot)
            self.p7c16_manager = P7C16RuntimeManagerView(raw, boot)
            return self.p7c16_manager

        super().__init__(boot, journal, runtime_factory=factory, force_failure=force_failure, stage_timeouts=stage_timeouts)

    async def run_async(self) -> dict[str, Any]:
        coordinator_init = DeleteStorageCleanupCoordinator.__init__
        service_init = p7c13.DialogueDeleteService.__init__

        def successor_coordinator_init(instance: Any, storage: Any, runtime_manager: Any, *args: Any, **kwargs: Any) -> None:
            if isinstance(runtime_manager, P7C16RuntimeManagerView):
                try:
                    # This is the exact path/storage agreement boundary. The
                    # real coordinator constructor remains authoritative for
                    # cleanup reservation and scanner behavior.
                    runtime_manager.bind_controller(storage)
                except ValueError as error:
                    if str(error) == "controller_storage_mismatch":
                        raise P7C16ControllerStorageMismatch() from None
                    raise
            coordinator_init(instance, storage, runtime_manager, *args, **kwargs)
            if isinstance(runtime_manager, P7C16RuntimeManagerView):
                self._mark("DELETE_CLEANUP_AUTHORITY_CONFIRMED", effect_class="controller")

        def successor_service_init(instance: Any, *args: Any, **kwargs: Any) -> None:
            service_init(instance, *args, **kwargs)
            self._mark("DELETE_CHAIN_READY", effect_class="delete-chain")

        try:
            # Patch only constructor methods for this child lifetime. The
            # concrete production classes and implementations remain intact.
            with patch.object(DeleteStorageCleanupCoordinator, "__init__", successor_coordinator_init), \
                 patch.object(p7c13.DialogueDeleteService, "__init__", successor_service_init):
                return await super().run_async()
        except BaseException as error:
            manager = self.p7c16_manager
            if manager is not None and (self._delete_generation_acquired or manager.acquire_count >= 3) and not self._runtime_quiescent(manager):
                try:
                    await p7c13._await_owned(
                        manager.shutdown_profile(P7C16_ENGINE_PROFILE_ID),
                        timeout=self.stage_timeouts.get("final_runtime_local_convergence", P7C16_REAL_CONVERGENCE_TIMEOUT),
                        convergence=self.stage_timeouts.get("final_runtime_local_convergence", P7C16_REAL_CONVERGENCE_TIMEOUT),
                        stage="P7.C16 late failure convergence",
                    )
                except BaseException:
                    self._convergence_failed = True
            if str(error) in {"durable controller binding mismatch", "controller_storage_mismatch"}:
                raise P7C16ControllerStorageMismatch() from None
            raise

    @staticmethod
    def _runtime_quiescent(manager: Any) -> bool:
        underlying = getattr(manager, "underlying", manager)
        return not any(bool(getattr(underlying, name, {})) for name in ("_runtimes", "_starting", "_unresolved"))


async def reproduce_p7c15_controller_authority_root_cause() -> dict[str, Any]:
    """Execute the consumed defect against the real storage/coordinator classes."""
    with tempfile.TemporaryDirectory(prefix="p7c16-root-cause-") as directory:
        root = Path(directory); repository = root / "repository"; repository.mkdir(mode=0o700)
        controller_root = root / "controller"; controller_root.mkdir(mode=0o700)
        home = root / "home"; home.mkdir(mode=0o700)
        profile = p7c13.CodexProfile("p7c15-root-cause", str(home), "P7.C15", str(root / "isolated"))
        isolated = IsolationPathAuthority((profile,), controller_db_root=str(controller_root), repository_root=str(repository), protected_roots=())
        db = controller_root / "root-cause.sqlite3"
        storage = await SqliteStorage.open(str(db))
        calls: list[str] = []

        class EarlyManager:
            isolation_authority = isolated
            async def reserve(self, _profile: str) -> None: calls.append("reserve")
            async def shutdown_profile(self, _profile: str) -> None: calls.append("shutdown")
            async def recreate_isolated_state_root(self, _token: object) -> None: calls.append("recreate")

        try:
            try:
                DeleteStorageCleanupCoordinator(storage, EarlyManager())
            except ValueError as error:
                reproduced = str(error) == "controller_storage_mismatch"
            else:
                reproduced = False
        finally:
            await storage.close()
        return {"reproduced": reproduced, "coordinator_delete_calls": 0, "thread_delete_dispatches": 0, "calls": tuple(calls)}


def _p7c16_boot(root: Path, contract: P7C16ArchitectContract) -> dict[str, Any]:
    authority = root / "authority"; authority.mkdir(mode=0o700, exist_ok=True)
    run_root = root / "run"; run_root.mkdir(mode=0o700, exist_ok=True)
    paths = p7c16_fresh_run_paths("a" * 24, root=run_root, authority=authority)
    paths["workdir"] = str(run_root / "p7c16-work-aaaaaaaa")
    paths.update({"ledger": str(authority / "p7c16-one-shot.json"), "codex_home": str(root / "fake-home")})
    Path(paths["codex_home"]).mkdir(mode=0o700, exist_ok=True)
    return {"schema": P7C16_BOOT_SCHEMA, "profile_id": P7C16_ENGINE_PROFILE_ID,
            "engine_profile_id": P7C16_ENGINE_PROFILE_ID, "source_head": contract.expected_head,
            "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
            "run_id_hash": _sha256("p7c16-synthetic"), "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET),
            "codex_home": paths["codex_home"], "isolated_root": paths["isolated_root"],
            "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"),
            "isolated_logs": str(Path(paths["isolated_root"]) / "logs"), "controller_db": paths["controller_db"],
            "workdir": paths["workdir"], "approval_target": paths["approval_target"], "ledger_path": paths["ledger"],
            "boot_authority_path": paths["boot"], "child_result_path": paths["child_result"],
            "wire_path": paths["wire"], "approval_journal_path": paths["approval_journal"],
            "stage_journal_path": paths["stage"], "import_roots": list(P7C16_IMPORT_ROOTS),
            "deterministic_import_root": P7C16_PYTHONPATH, "runtime_authority": "/usr/local/bin/codex"}


class P7C16RootOnlyBootAuthority:
    MAX_BYTES = 16384
    KEYS = frozenset(("schema", "profile_id", "engine_profile_id", "source_head", "source_tree", "launcher_blob", "run_id_hash", "effect_ceiling",
                      "codex_home", "isolated_root", "isolated_sqlite", "isolated_logs", "controller_db", "workdir", "approval_target",
                      "ledger_path", "boot_authority_path", "child_result_path", "wire_path", "approval_journal_path", "stage_journal_path",
                      "import_roots", "deterministic_import_root", "runtime_authority"))
    PATH_KEYS = ("ledger_path", "boot_authority_path", "child_result_path", "isolated_root", "isolated_sqlite",
                 "isolated_logs", "controller_db", "workdir", "approval_target", "wire_path", "approval_journal_path",
                 "stage_journal_path")

    def __init__(self, path: str | Path) -> None: self.path = Path(path)

    @classmethod
    def validate(cls, value: Mapping[str, Any], *, authority_path: Path | None = None, allow_test_home: bool = False) -> dict[str, Any]:
        if set(value) != cls.KEYS or value.get("schema") != P7C16_BOOT_SCHEMA:
            raise P7C16PreparationError("P7.C16 boot schema invalid")
        if value.get("profile_id") != P7C16_ENGINE_PROFILE_ID or value.get("engine_profile_id") != P7C16_ENGINE_PROFILE_ID:
            raise P7C16PreparationError("P7.C16 engine profile invalid")
        if value.get("codex_home") != P7C16_AUTHENTICATED_HOME and not allow_test_home:
            raise P7C16PreparationError("P7.C16 authenticated home invalid")
        for key in ("source_head", "source_tree", "launcher_blob", "run_id_hash", "codex_home", "runtime_authority"):
            if not isinstance(value.get(key), str) or not value[key] or "\0" in value[key] or len(value[key]) > 4096:
                raise P7C16PreparationError("P7.C16 boot scalar invalid")
        if len(value["run_id_hash"]) != 64 or any(c not in "0123456789abcdef" for c in value["run_id_hash"]):
            raise P7C16PreparationError("P7.C16 run hash invalid")
        if value["import_roots"] != list(P7C16_IMPORT_ROOTS) or value["deterministic_import_root"] != P7C16_PYTHONPATH:
            raise P7C16PreparationError("P7.C16 import authority invalid")
        if not isinstance(value["effect_ceiling"], dict) or set(value["effect_ceiling"]) != set(p7c13.FROZEN_EFFECT_BUDGET):
            raise P7C16PreparationError("P7.C16 effect ceiling invalid")
        if any(type(value["effect_ceiling"][key]) is not int or value["effect_ceiling"][key] != p7c13.FROZEN_EFFECT_BUDGET[key]
               for key in value["effect_ceiling"]):
            raise P7C16PreparationError("P7.C16 effect ceiling invalid")
        for key in cls.PATH_KEYS:
            path = value.get(key)
            if not isinstance(path, str) or not os.path.isabs(path) or len(path) > 4096 or "\0" in path:
                raise P7C16PreparationError("P7.C16 boot path invalid")
            if Path(path).is_symlink():
                raise P7C16PreparationError("P7.C16 boot path symlink")
        if len({value[key] for key in cls.PATH_KEYS}) != len(cls.PATH_KEYS):
            raise P7C16PreparationError("P7.C16 boot paths alias")
        if not Path(value["ledger_path"]).name.endswith("one-shot.json") or not Path(value["controller_db"]).name.startswith("p7c16-controller-"):
            raise P7C16PreparationError("P7.C16 current-run path invalid")
        if authority_path is not None and Path(value["boot_authority_path"]) != authority_path:
            raise P7C16PreparationError("P7.C16 boot authority path drift")
        return dict(value)

    def create(self, value: Mapping[str, Any], *, allow_test_home: bool = False) -> dict[str, Any]:
        value = self.validate(value, authority_path=self.path, allow_test_home=allow_test_home)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            payload = (json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
            if len(payload) > self.MAX_BYTES:
                raise P7C16PreparationError("P7.C16 boot too large")
            stream.buffer.write(payload); stream.flush(); os.fsync(stream.fileno())
        st = self.path.lstat()
        if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
            raise P7C16PreparationError("P7.C16 boot identity invalid")
        return self.read(allow_test_home=allow_test_home)

    def read(self, *, allow_test_home: bool = False) -> dict[str, Any]:
        identity = self.path.lstat()
        if identity.st_uid != 0 or stat.S_IMODE(identity.st_mode) != 0o600 or identity.st_nlink != 1 or not stat.S_ISREG(identity.st_mode) or identity.st_size > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 boot identity invalid")
        fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            data = os.read(fd, self.MAX_BYTES + 1); current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_nlink != 1 or stat.S_IMODE(current.st_mode) != 0o600:
                raise P7C16PreparationError("P7.C16 boot identity drift")
        finally:
            os.close(fd)
        if len(data) > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 boot too large")
        return self.validate(json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys), authority_path=self.path, allow_test_home=allow_test_home)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in pairs:
        if key in result:
            raise P7C16PreparationError("duplicate JSON key")
        result[key] = item
    return result


class P7C16ChildResultAuthority:
    MAX_BYTES = 16384
    KEYS = frozenset(("schema", "status", "verdict", "source_head", "source_tree", "launcher_blob", "run_id_hash",
                      "boot_authority_path", "effect_counts", "outcomes", "classes", "terminal_exception_class",
                      "terminal_error_category", "last_confirmed_stage", "stage_journal_sha256",
                      "runtime_child_quiescent", "parent_process_group_quiescent"))
    STATUSES = frozenset(("PASS", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"))

    @staticmethod
    def _validate(payload: Mapping[str, Any], boot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if set(payload) != P7C16ChildResultAuthority.KEYS or payload.get("schema") != P7C16_CHILD_RESULT_SCHEMA:
            raise P7C16PreparationError("P7.C16 child result schema invalid")
        if payload.get("status") not in P7C16ChildResultAuthority.STATUSES or type(payload.get("verdict")) is not bool:
            raise P7C16PreparationError("P7.C16 child result status invalid")
        if boot is not None and any(payload.get(key) != boot.get(key) for key in ("source_head", "source_tree", "launcher_blob", "run_id_hash", "boot_authority_path")):
            raise P7C16PreparationError("P7.C16 child result boot binding invalid")
        if not isinstance(payload.get("effect_counts"), dict) or set(payload["effect_counts"]) != set(p7c13.FROZEN_EFFECT_BUDGET):
            raise P7C16PreparationError("P7.C16 child result effects invalid")
        if any(type(payload["effect_counts"][key]) is not int or not 0 <= payload["effect_counts"][key] <= p7c13.FROZEN_EFFECT_BUDGET[key] for key in payload["effect_counts"]):
            raise P7C16PreparationError("P7.C16 child result effect ceiling invalid")
        for key in ("outcomes", "classes"):
            if not isinstance(payload.get(key), dict) or len(payload[key]) > 64 or any(not isinstance(k, str) or not isinstance(v, (str, int, bool, type(None))) for k, v in payload[key].items()):
                raise P7C16PreparationError("P7.C16 child result map invalid")
        for key in ("terminal_exception_class", "terminal_error_category", "last_confirmed_stage", "stage_journal_sha256"):
            if payload[key] is not None and (not isinstance(payload[key], str) or not payload[key] or len(payload[key]) > 128):
                raise P7C16PreparationError("P7.C16 child result string invalid")
        if type(payload["runtime_child_quiescent"]) is not bool or payload["parent_process_group_quiescent"] is not None and type(payload["parent_process_group_quiescent"]) is not bool:
            raise P7C16PreparationError("P7.C16 child result quiescence invalid")
        return dict(payload)

    @classmethod
    def write(cls, path: str | Path, payload: Mapping[str, Any], boot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        path = Path(path); checked = cls._validate(payload, boot); path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            payload_bytes = (json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
            if len(payload_bytes) > cls.MAX_BYTES:
                raise P7C16PreparationError("P7.C16 child result too large")
            stream.buffer.write(payload_bytes); stream.flush(); os.fsync(stream.fileno())
        return cls.read(path, boot)

    @classmethod
    def read(cls, path: str | Path, boot: Mapping[str, Any] | None = None) -> dict[str, Any]:
        target = Path(path); identity = target.lstat()
        if identity.st_uid != 0 or stat.S_IMODE(identity.st_mode) != 0o600 or identity.st_nlink != 1 or not stat.S_ISREG(identity.st_mode) or identity.st_size > cls.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 child result identity invalid")
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            data = os.read(fd, cls.MAX_BYTES + 1); current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_nlink != 1 or stat.S_IMODE(current.st_mode) != 0o600:
                raise P7C16PreparationError("P7.C16 child result identity drift")
        finally:
            os.close(fd)
        if len(data) > cls.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 child result too large")
        return cls._validate(json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys), boot)


class P7C16DurableOneShotLedger:
    KEYS = frozenset(("schema", "state", "source_head", "source_tree", "launcher_blob", "run_id_hash",
                      "engine_profile_id", "effect_counts", "recovery"))
    MAX_BYTES = 8192

    def __init__(self, path: str | Path) -> None:
        self.path, self._identity = Path(path), None

    @classmethod
    def _valid(cls, record: Any) -> dict[str, Any]:
        if not isinstance(record, dict) or set(record) != cls.KEYS or record.get("schema") != P7C16_LEDGER_SCHEMA or record.get("state") not in P7C16_STATES:
            raise P7C16PreparationError("P7.C16 ledger schema invalid")
        if any(not isinstance(record.get(key), str) or not record[key] for key in ("source_head", "source_tree", "launcher_blob", "run_id_hash", "engine_profile_id")):
            raise P7C16PreparationError("P7.C16 ledger authority invalid")
        if not isinstance(record["effect_counts"], dict) or not isinstance(record["recovery"], dict):
            raise P7C16PreparationError("P7.C16 ledger maps invalid")
        return dict(record)

    def _check_identity(self) -> os.stat_result:
        st = self.path.lstat()
        if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode) or st.st_size > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 ledger identity invalid")
        if self._identity is not None and (st.st_dev, st.st_ino) != self._identity:
            raise P7C16PreparationError("P7.C16 ledger replaced")
        if self._identity is None:
            self._identity = (st.st_dev, st.st_ino)
        return st

    def reserve(self, record: Mapping[str, Any]) -> bool:
        checked = self._valid(dict(record))
        if checked.get("state") != "RESERVED":
            raise P7C16PreparationError("P7.C16 ledger schema invalid")
        payload = (json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        if len(payload) > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 ledger too large")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            self._check_identity()
            return False
        try:
            os.fchmod(fd, 0o600); os.write(fd, payload); os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != 0 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise P7C16PreparationError("P7.C16 ledger identity invalid")
            self._identity = (st.st_dev, st.st_ino)
        finally:
            os.close(fd)
        return True

    def update(self, **changes: Any) -> None:
        value = self.read(); state = changes.get("state", value.get("state"))
        if set(changes) - {"state", "recovery"}:
            raise P7C16PreparationError("P7.C16 ledger authority mutation invalid")
        if state not in P7C16_STATES - {"RESERVED"} or value.get("state") != "RESERVED":
            raise P7C16PreparationError("P7.C16 terminal transition invalid")
        value.update(changes)
        payload = (json.dumps(self._valid(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        if len(payload) > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 ledger too large")
        fd = os.open(self.path, os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            current = os.fstat(fd)
            if self._identity is not None and (current.st_dev, current.st_ino) != self._identity:
                raise P7C16PreparationError("P7.C16 ledger replaced")
            if current.st_uid != 0 or current.st_nlink != 1 or stat.S_IMODE(current.st_mode) != 0o600:
                raise P7C16PreparationError("P7.C16 ledger identity invalid")
            os.ftruncate(fd, 0); os.write(fd, payload); os.fsync(fd)
        finally:
            os.close(fd)
        self._check_identity()
        return self.read()

    def read(self) -> dict[str, Any]:
        identity = self._check_identity()
        fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            data = os.read(fd, self.MAX_BYTES + 1); current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino) or current.st_nlink != 1:
                raise P7C16PreparationError("P7.C16 ledger identity drift")
        finally:
            os.close(fd)
        if len(data) > self.MAX_BYTES:
            raise P7C16PreparationError("P7.C16 ledger too large")
        return self._valid(json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys))


def p7c16_exact_effect_pass_gate(counts: Mapping[str, int]) -> bool:
    required = ("new_threads", "model/list", "thread/start", "thread/resume", "turn/start",
                "approval_responses", "allow_responses", "turn/interrupt", "thread/delete")
    forbidden = ("thread/read", "thread/list", "second_child", "real_retry", "telegram")
    return all(type(counts.get(key)) is int and counts[key] == p7c13.FROZEN_EFFECT_BUDGET[key] for key in required) and all(
        type(counts.get(key)) is int and counts[key] == 0 for key in forbidden)


def _p7c16_child_result_file_is_valid(path: Path, boot: Mapping[str, Any]) -> bool:
    try:
        P7C16ChildResultAuthority.read(path, boot)
        return True
    except (OSError, UnicodeError, json.JSONDecodeError, P7C16PreparationError):
        return False


class _P7C16UnderlyingFakeReservation:
    """Test-only reservation owned by the fake underlying manager."""

    def __init__(self, manager: "_P7C16UnderlyingFakeRuntimeManager", profile_id: str) -> None:
        self.manager, self.profile_id, self.released = manager, profile_id, False

    def quiescence_proof(self) -> RuntimeQuiescenceProof:
        return RuntimeQuiescenceProof(
            self.profile_id, not self.released, False,
            not P7C16ProductionChildOrchestrator._runtime_quiescent(self.manager), False,
        )

    async def release(self) -> None:
        await self.manager.release(self)


class _P7C16UnderlyingFakeRuntimeManager(p7c15._FakeRuntimeManager):
    """Fake external process boundary with real manager ownership semantics."""

    def __init__(self, scenario: str = "positive") -> None:
        self.p7c16_failure_scenario = scenario if scenario.startswith("late_failure") else ""
        super().__init__(
            profile_id=P7C16_ENGINE_PROFILE_ID,
            scenario="positive" if self.p7c16_failure_scenario else scenario,
        )
        self._profile: Any | None = None
        self._authority: IsolationPathAuthority | None = None
        self._reservations: list[_P7C16UnderlyingFakeReservation] = []
        # Deliberately mirror the real manager's ownership maps. The
        # successor quiescence authority never reads the inherited fake-only
        # runtime_quiescent boolean.
        self._runtimes: dict[str, Any] = {}
        self._starting: dict[str, Any] = {}
        self._unresolved: dict[str, Any] = {}
        self.reserve_count = self.release_count = self.recreate_count = 0

    def configure(self, boot: Mapping[str, Any]) -> None:
        super().configure(boot)
        self._profile = p7c13.CodexProfile(P7C16_ENGINE_PROFILE_ID, boot["codex_home"], "P7.C15", boot["isolated_root"])
        self._authority = IsolationPathAuthority(
            (self._profile,), controller_db_root=str(Path(boot["controller_db"]).parent),
            repository_root=str(_repository()), protected_roots=(),
        )

    @property
    def isolation_authority(self) -> IsolationPathAuthority:
        if self._authority is None:
            raise P7C16PreparationError("underlying authority unavailable")
        return self._authority

    def profile(self, profile_id: str) -> Any:
        if profile_id != P7C16_ENGINE_PROFILE_ID or self._profile is None:
            raise P7C16PreparationError("effective engine profile mismatch")
        return self._profile

    async def reserve(self, profile_id: str) -> _P7C16UnderlyingFakeReservation:
        if profile_id != P7C16_ENGINE_PROFILE_ID or self._reservations:
            raise P7C16PreparationError("reservation profile mismatch")
        self.reserve_count += 1
        token = _P7C16UnderlyingFakeReservation(self, profile_id)
        self._reservations.append(token)
        return token

    async def acquire(self, profile_id: str) -> Any:
        runtime = await super().acquire(profile_id)
        self._runtimes[profile_id] = runtime
        return runtime

    async def shutdown_profile(self, profile_id: str) -> None:
        if self.p7c16_failure_scenario == "late_failure_shutdown_failure" and self.generation >= 3:
            raise P7C16PreparationError("synthetic shutdown nonconvergence")
        await super().shutdown_profile(profile_id)
        self._runtimes.clear(); self._starting.clear(); self._unresolved.clear()

    async def release(self, token: _P7C16UnderlyingFakeReservation) -> None:
        if token not in self._reservations or token.released:
            raise P7C16PreparationError("underlying reservation token invalid")
        token.released = True; self._reservations.remove(token); self.release_count += 1

    async def recreate_isolated_state_root(self, token: _P7C16UnderlyingFakeReservation) -> None:
        if token not in self._reservations or not token.quiescence_proof().is_quiescent:
            raise P7C16PreparationError("underlying reservation invalid")
        self.recreate_count += 1
        if self.scenario == "confirmed_pending":
            raise P7C16PreparationError("synthetic recreate pending")
        IsolatedStateRoot(self.isolation_authority)._recreate_bound(self.profile(token.profile_id))


class P7C16PreparedFutureExecutor:
    def __init__(self, ledger: P7C16DurableOneShotLedger, child: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None, *,
                 watchdog: Any | None = None, child_command_factory: Callable[[Path], Sequence[str]] | None = None,
                 run_paths: Mapping[str, str] | None = None, boot_path: Path | None = None,
                 test_only_watchdog_bounds: tuple[float, float, float] | None = None,
                 test_only_codex_home: Path | None = None) -> None:
        self.ledger, self.child, self.calls = ledger, child, 0
        self.watchdog, self.child_command_factory = watchdog, child_command_factory
        self.run_paths, self.boot_path = dict(run_paths or {}), boot_path
        self.test_only_watchdog_bounds = test_only_watchdog_bounds
        self.test_only_codex_home = test_only_codex_home

    @classmethod
    def production(cls, contract: P7C16ArchitectContract) -> "P7C16PreparedFutureExecutor":
        return cls._production_with_authority(contract, ledger_path=P7C16_LEDGER_PATH)

    @classmethod
    def _production_with_authority(
        cls, contract: P7C16ArchitectContract, *, ledger_path: Path,
        process_factory: Callable[..., Any] = subprocess.Popen,
        active_group_probe: Callable[[int], int] | None = None,
        zombie_group_probe: Callable[[int], int] | None = None,
        group_scan_error_probe: Callable[[int], int] | None = None,
        child_dispatch: Callable[[Path], int] | None = None,
        test_only_watchdog_bounds: tuple[float, float, float] | None = None,
        test_only_codex_home: Path | None = None,
        mutation_events: list[str] | None = None,
        run_parent_mkdir: Callable[[Path], None] | None = None,
    ) -> "P7C16PreparedFutureExecutor":
        run_hash = _sha256(os.urandom(32))
        state_parent = ledger_path.parent.parent / f"p7c16-state-parent-{run_hash[:12]}"
        work_parent = ledger_path.parent.parent / f"p7c16-work-parent-{run_hash[:12]}"
        paths = p7c16_fresh_run_paths(run_hash, root=state_parent, authority=ledger_path.parent)
        paths["workdir"] = str(work_parent / f"p7c16-work-{run_hash[:32]}")
        boot_path = Path(paths["boot"])
        record = {"schema": P7C16_LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head,
                  "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
                  "run_id_hash": run_hash, "engine_profile_id": P7C16_ENGINE_PROFILE_ID,
                  "effect_counts": {}, "recovery": {}}
        watchdog = p7c13.OwnedParentChildWatchdog(
            process_factory=process_factory, active_group_probe=active_group_probe,
            zombie_group_probe=zombie_group_probe, group_scan_error_probe=group_scan_error_probe,
        )

        def command_factory(actual_boot: Path) -> Sequence[str]:
            return ("/usr/bin/env", f"PYTHONPATH={P7C16_PYTHONPATH}", "/usr/bin/python", "-m",
                    "tests.real.test_p7_c16_final_hard_delete_successor", "--p7c16-future-child",
                    "--boot-authority", str(actual_boot))

        executor = cls(P7C16DurableOneShotLedger(ledger_path), child=None, watchdog=watchdog,
                       child_command_factory=command_factory, run_paths=paths, boot_path=boot_path,
                       test_only_watchdog_bounds=test_only_watchdog_bounds,
                       test_only_codex_home=test_only_codex_home)
        executor._mutation_events = mutation_events if mutation_events is not None else []
        executor._run_parent_mkdir = run_parent_mkdir or (lambda path: path.mkdir(mode=0o700, exist_ok=False))
        executor._offline_child_dispatch = child_dispatch
        executor._explicit_group_probes = any(probe is not None for probe in (active_group_probe, zombie_group_probe, group_scan_error_probe))
        executor._record = record
        return executor

    def _event(self, name: str) -> None:
        getattr(self, "_mutation_events", []).append(name)

    def _production_boot(self, contract: P7C16ArchitectContract, record: Mapping[str, Any]) -> dict[str, Any]:
        if not self.run_paths or self.boot_path is None:
            raise P7C16PreparationError("P7.C16 fresh authority missing")
        paths = dict(self.run_paths); paths["boot"] = str(self.boot_path); paths["ledger_path"] = str(self.ledger.path)
        authority = self.ledger.path.parent
        st = authority.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or stat.S_IMODE(st.st_mode) & 0o022:
            raise P7C16PreparationError("P7.C16 authority root unsafe")
        expected = {"isolated_root", "controller_db", "workdir", "approval_target", "boot", "child_result", "wire", "approval_journal", "stage"}
        if set(self.run_paths) != expected or any(not os.path.isabs(value) for value in self.run_paths.values()):
            raise P7C16PreparationError("P7.C16 fresh path set invalid")
        for key, value in self.run_paths.items():
            if not Path(value).name.startswith("p7c16-") or Path(value).exists() or Path(value).is_symlink():
                raise P7C16PreparationError("P7.C16 fresh namespace invalid")
        if len({os.path.realpath(value) for value in self.run_paths.values()}) != len(self.run_paths):
            raise P7C16PreparationError("P7.C16 physical path alias")
        boot = {"schema": P7C16_BOOT_SCHEMA, "profile_id": P7C16_ENGINE_PROFILE_ID,
                "engine_profile_id": P7C16_ENGINE_PROFILE_ID, "source_head": contract.expected_head,
                "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
                "run_id_hash": record["run_id_hash"], "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET),
                "codex_home": str(self.test_only_codex_home or Path(P7C16_AUTHENTICATED_HOME)), "isolated_root": paths["isolated_root"],
                "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"),
                "isolated_logs": str(Path(paths["isolated_root"]) / "logs"), "controller_db": paths["controller_db"],
                "workdir": paths["workdir"], "approval_target": paths["approval_target"],
                "ledger_path": str(self.ledger.path), "boot_authority_path": paths["boot"],
                "child_result_path": paths["child_result"], "wire_path": paths["wire"],
                "approval_journal_path": paths["approval_journal"], "stage_journal_path": paths["stage"],
                "import_roots": list(P7C16_IMPORT_ROOTS), "deterministic_import_root": P7C16_PYTHONPATH,
                "runtime_authority": "/usr/local/bin/codex"}
        if self.test_only_codex_home is not None:
            Path(self.test_only_codex_home).mkdir(mode=0o700, parents=True, exist_ok=True)
        return P7C16RootOnlyBootAuthority(self.boot_path).validate(
            boot, authority_path=self.boot_path, allow_test_home=self.test_only_codex_home is not None)

    def _run_production(self, contract: P7C16ArchitectContract) -> p7c13.WatchdogResult:
        record = dict(getattr(self, "_record", {}))
        if not record or not self.ledger.reserve(record):
            raise P7C16PreparationError("P7.C16 reservation consumed")
        self._event("LEDGER_RESERVED")
        paths = dict(self.run_paths or {})
        self._run_parent_mkdir(Path(paths["isolated_root"]).parent); self._event("RUN_STATE_PARENT_CREATED")
        self._run_parent_mkdir(Path(paths["workdir"]).parent); self._event("RUN_WORK_PARENT_CREATED")
        boot = self._production_boot(contract, record)
        P7C16RootOnlyBootAuthority(self.boot_path).create(
            boot, allow_test_home=self.test_only_codex_home is not None); self._event("BOOT_CREATED")
        P7C16RootOnlyBootAuthority(self.boot_path).read(allow_test_home=self.test_only_codex_home is not None)
        command = tuple(self.child_command_factory(self.boot_path))
        child_dispatch = getattr(self, "_offline_child_dispatch", None)
        if child_dispatch is not None:
            if not getattr(self, "_explicit_group_probes", False):
                self.watchdog.active_group_probe = lambda _pgid: 0
                self.watchdog.zombie_group_probe = lambda _pgid: 0
                self.watchdog.group_scan_error_probe = lambda _pgid: 0
            class OfflineProcess:
                pid = os.getpid(); returncode: int | None = None
                def wait(self, timeout: float | None = None) -> int:
                    del timeout
                    self.returncode = child_dispatch(Path(command[-1]))
                    return self.returncode
            self.watchdog.process_factory = lambda *_args, **_kwargs: OfflineProcess()
        hard_deadline, term_grace, kill_grace = self.test_only_watchdog_bounds or (
            P7C16_REAL_WATCHDOG_HARD_DEADLINE, p7c13.REAL_WATCHDOG_TERM_GRACE, p7c13.REAL_WATCHDOG_KILL_GRACE)
        self._event("CHILD_DISPATCHED")
        observed = self.watchdog.run(command, result_path=boot["child_result_path"], timeout_seconds=hard_deadline,
                                     term_grace_seconds=term_grace, kill_grace_seconds=kill_grace,
                                     result_validator=lambda path: _p7c16_child_result_file_is_valid(path, boot))
        child_result: dict[str, Any] | None = None
        try:
            child_result = P7C16ChildResultAuthority.read(boot["child_result_path"], boot)
        except (OSError, UnicodeError, json.JSONDecodeError, P7C16PreparationError):
            pass
        child_valid = child_result is not None and observed.child_result_valid
        child_status = child_result.get("status") if child_result else None
        exact_effect = bool(child_result and p7c16_exact_effect_pass_gate(child_result["effect_counts"]))
        if observed.status == "TIMEOUT": state = "TIMEOUT"
        elif child_status in {"UNKNOWN", "CONFIRMED_PENDING"}: state = child_status
        elif (observed.status == "COMPLETED" and child_valid and child_status == "PASS"
              and child_result["verdict"] is True and child_result["runtime_child_quiescent"] is True
              and exact_effect and observed.child_count == 1 and not observed.retry
              and observed.owned_group_active == observed.owned_group_zombies == observed.group_scan_errors == 0):
            state = "COMPLETED"
        else: state = "FAILED"
        recovery = {"watchdog_status": observed.status, "child_result_valid": child_valid,
                    "child_status": child_status, "child_verdict": child_result.get("verdict") if child_result else None,
                    "runtime_child_quiescent": child_result.get("runtime_child_quiescent") if child_result else None,
                    "exact_effect_gate": exact_effect, "owned_group_active": observed.owned_group_active,
                    "owned_group_zombies": observed.owned_group_zombies, "group_scan_errors": observed.group_scan_errors,
                    "child_count": observed.child_count, "retry_count": getattr(self.watchdog, "retry_count", 0),
                    "signals_sent_count": len(observed.signals_sent), "last_confirmed_stage": child_result.get("last_confirmed_stage") if child_result else "PARENT_VALIDATION",
                    "child_result_authority_hash": _sha256(Path(boot["child_result_path"]).read_bytes()) if child_valid else None}
        self.ledger.update(state=state, recovery=recovery)
        return observed

    def run(self, contract: P7C16ArchitectContract) -> Any:
        if self.calls:
            raise P7C16PreparationError("second child/retry forbidden")
        self.calls += 1
        if self.watchdog is not None:
            return self._run_production(contract)
        if self.child is None:
            raise P7C16PreparationError("P7.C16 production child missing")
        raise P7C16PreparationError("offline executor requires explicit child/watchdog seam")


def _p7c16_parse_child_boot(arguments: Sequence[str]) -> Path:
    if len(arguments) != 3 or arguments.count("--p7c16-future-child") != 1 or arguments.count("--boot-authority") != 1:
        raise P7C16PreparationError("P7.C16 child arguments invalid")
    index = arguments.index("--boot-authority")
    if index + 1 >= len(arguments) or not os.path.isabs(arguments[index + 1]):
        raise P7C16PreparationError("P7.C16 boot authority missing")
    return Path(arguments[index + 1]).absolute()


def p7c16_future_child_main(boot_path: str | Path, *, runtime_factory: Callable[[], Any] | None = None,
                            force_failure: bool = False, verify_installed_authority: bool | None = None) -> int:
    """Run one owned successor child against a supplied external boundary."""
    boot = P7C16RootOnlyBootAuthority(boot_path).read(allow_test_home=runtime_factory is not None)
    journal = P7C16StageJournal(boot["stage_journal_path"])
    child: P7C16ProductionChildOrchestrator | None = None
    should_verify = runtime_factory is None if verify_installed_authority is None else verify_installed_authority
    old_umask = os.umask(0o077)
    try:
        # This check is deliberately before construction of the real runtime
        # factory.  A supplied factory is an explicit offline-only seam.
        if should_verify:
            p7c13.InstalledRuntimeAuthority().verify()
        child = P7C16ProductionChildOrchestrator(boot, journal, runtime_factory=runtime_factory, force_failure=force_failure)
        result = asyncio.run(child.run_async())
        payload = _p7c16_child_payload(boot, result, child, journal)
        P7C16ChildResultAuthority.write(boot["child_result_path"], payload, boot)
        return 0 if payload.get("status") == "PASS" and payload.get("verdict") is True else 1
    except BaseException as error:
        payload = _p7c16_child_payload(
            boot, {"status": "FAILED", "verdict": False, "last_confirmed_stage": child.last_confirmed_stage if child else "PRE_CHILD",
                   "terminal_exception_class": type(error).__name__,
                   "terminal_error_category": _p7c16_error_category(error),
                   "runtime_child_quiescent": bool(child and child.p7c16_manager and
                                                    P7C16ProductionChildOrchestrator._runtime_quiescent(child.p7c16_manager))},
            child, journal,
        )
        try:
            journal.append("TERMINAL_EXCEPTION", "FAILED", effect_class="terminal", error=error)
            payload["stage_journal_sha256"] = journal.digest()
            P7C16ChildResultAuthority.write(boot["child_result_path"], payload, boot)
        except (OSError, P7C16PreparationError):
            pass
        return 1
    finally:
        os.umask(old_umask)


def _p7c16_child_payload(boot: Mapping[str, Any], result: Mapping[str, Any], child: P7C16ProductionChildOrchestrator | None,
                         journal: P7C16StageJournal) -> dict[str, Any]:
    budget = child.budget if child is not None else None
    return {
        "schema": P7C16_CHILD_RESULT_SCHEMA, "status": result.get("status", "FAILED"),
        "verdict": bool(result.get("verdict", False)), "source_head": boot["source_head"],
        "source_tree": boot["source_tree"], "launcher_blob": boot["launcher_blob"],
        "run_id_hash": boot["run_id_hash"], "boot_authority_path": boot["boot_authority_path"],
        "effect_counts": {key: budget.count(key) if budget is not None else 0 for key in p7c13.FROZEN_EFFECT_BUDGET},
        "outcomes": dict(result.get("outcomes", {})), "classes": dict(result.get("classes", {})),
        "terminal_exception_class": result.get("terminal_exception_class"),
        "terminal_error_category": result.get("terminal_error_category"),
        "last_confirmed_stage": result.get("last_confirmed_stage", "PRE_CHILD"),
        "stage_journal_sha256": result.get("stage_journal_sha256") or journal.digest(),
        "runtime_child_quiescent": bool(result.get("runtime_child_quiescent", False)),
        "parent_process_group_quiescent": None,
    }


def p7c16_real_entrypoint(*, environ: Mapping[str, str], authority: P7C16SourceAuthority | None = None,
                          executor: P7C16PreparedFutureExecutor | None = None) -> dict[str, Any]:
    current = authority or current_p7c16_source_authority(); contract = _contract_from_environment(environ)
    if not p7c16_source_bundle_gate(environ, contract, current):
        raise P7C16PreparationError("P7C16_FUTURE_REAL_GATE=DISABLED_OR_SOURCE_MISMATCH")
    if executor is not None:
        selected = executor
    elif P7C16_TEST_ONLY_PRODUCTION_FACTORY is not None:
        selected = P7C16_TEST_ONLY_PRODUCTION_FACTORY(contract)
    else:
        selected = P7C16PreparedFutureExecutor.production(contract)
    return selected.run(contract)


class P7C16OfflineAuthorityTests(unittest.TestCase):
    def test_gate_disabled_before_ledger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c16-gate-") as directory:
            path = Path(directory) / "p7c16-one-shot.json"
            with self.assertRaises(P7C16PreparationError):
                p7c16_real_entrypoint(environ={}, executor=P7C16PreparedFutureExecutor(P7C16DurableOneShotLedger(path)))
            self.assertFalse(path.exists())

    def test_root_cause_is_reproduced_with_real_coordinator(self) -> None:
        result = asyncio.run(reproduce_p7c15_controller_authority_root_cause())
        self.assertTrue(result["reproduced"]); self.assertEqual((), result["calls"])

    def test_late_bound_exact_path_validates_only_after_open(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c16-authority-") as directory:
            root = Path(directory); repo = root / "repo"; repo.mkdir(mode=0o700); home = root / "home"; home.mkdir(mode=0o700)
            controller_parent = root / "controller"; controller_parent.mkdir(mode=0o700)
            state = root / "state"; controller = controller_parent / "p7c16-controller-current.sqlite3"
            profile = p7c13.CodexProfile(P7C16_PROFILE_ID, str(home), "P7.C16", str(state))
            raw = type("Raw", (), {})(); view = P7C16LateBoundControllerRuntimeView(raw, profile, repo, str(controller))
            self.assertIsNotNone(view.authority.controller_db_root); self.assertIsNone(view.authority.controller_db_path)
            async def check() -> None:
                IsolatedStateRoot(view.authority).provision(profile)
                storage = await SqliteStorage.open(str(controller))
                try:
                    exact = view.bind_exact(storage)
                    self.assertEqual(str(controller), exact.controller_db_path)
                    self.assertTrue(storage.matches_database_path(exact.controller_db_path or ""))
                finally:
                    await storage.close()
            asyncio.run(check())

    def test_wrong_path_symlink_and_private_authority_fail_before_delete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c16-negative-") as directory:
            root = Path(directory); repo = root / "repo"; repo.mkdir(mode=0o700); home = root / "home"; home.mkdir(mode=0o700)
            controller_parent = root / "controller"; controller_parent.mkdir(mode=0o700)
            controller = controller_parent / "p7c16-controller-current.sqlite3"; foreign = controller_parent / "p7c16-controller-foreign.sqlite3"
            profile = p7c13.CodexProfile(P7C16_PROFILE_ID, str(home), "P7.C16", str(root / "state"))
            fixture_view = P7C16LateBoundControllerRuntimeView(object(), profile, repo, str(controller))
            IsolatedStateRoot(fixture_view.authority).provision(profile)
            async def check() -> None:
                storage = await SqliteStorage.open(str(controller))
                try:
                    view = P7C16LateBoundControllerRuntimeView(object(), profile, repo, str(foreign))
                    with self.assertRaises(ValueError): view.bind_exact(storage)
                    foreign.touch()
                    view = P7C16LateBoundControllerRuntimeView(object(), profile, repo, str(foreign))
                    with self.assertRaises(ValueError): view.bind_exact(storage)
                    link = controller_parent / "p7c16-controller-link.sqlite3"; link.symlink_to(foreign)
                    view = P7C16LateBoundControllerRuntimeView(object(), profile, repo, str(link))
                    with self.assertRaises(ValueError): view.bind_exact(storage)
                finally:
                    await storage.close()
            asyncio.run(check())

    def test_real_shaped_runtime_quiescence_matrix_uses_ownership_maps(self) -> None:
        class RealShapedRuntimeManager:
            def __init__(self) -> None:
                self._runtimes: dict[str, object] = {}
                self._starting: dict[str, object] = {}
                self._unresolved: dict[str, object] = {}

        manager = RealShapedRuntimeManager()
        self.assertFalse(hasattr(manager, "runtime_quiescent"))
        self.assertTrue(P7C16ProductionChildOrchestrator._runtime_quiescent(manager))
        for name in ("_runtimes", "_starting", "_unresolved"):
            setattr(manager, name, {"p7c15-successor-profile": object()})
            self.assertFalse(P7C16ProductionChildOrchestrator._runtime_quiescent(manager))
            setattr(manager, name, {})
        self.assertTrue(P7C16ProductionChildOrchestrator._runtime_quiescent(manager))

    def test_controller_storage_mismatch_is_finite_and_predelete(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        with tempfile.TemporaryDirectory(prefix="p7c16-controller-mismatch-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
            holder: dict[str, Any] = {}

            def factory() -> Any:
                manager = _P7C16UnderlyingFakeRuntimeManager(scenario="controller_mismatch")
                holder["manager"] = manager
                return manager

            self.assertEqual(1, p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=factory))
            result = P7C16ChildResultAuthority.read(boot["child_result_path"])
            self.assertEqual("FAILED", result["status"])
            self.assertEqual("P7C16ControllerStorageMismatch", result["terminal_exception_class"])
            self.assertEqual("controller_storage_mismatch", result["terminal_error_category"])
            self.assertEqual(0, result["effect_counts"]["thread/delete"])
            self.assertEqual(0, holder["manager"].client.calls.count("thread/delete"))

    def test_late_failure_convergence_matrix_is_owned_and_one_shot(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        for scenario, expected_quiescent in (("late_failure", True), ("late_failure_shutdown_failure", False)):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory(prefix="p7c16-late-failure-") as directory:
                root = Path(directory); boot = _p7c16_boot(root, contract)
                P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
                holder: dict[str, Any] = {}

                def factory() -> Any:
                    manager = _P7C16UnderlyingFakeRuntimeManager(scenario=scenario)
                    holder["manager"] = manager
                    return manager

                self.assertEqual(1, p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=factory))
                result = P7C16ChildResultAuthority.read(boot["child_result_path"])
                self.assertEqual("FAILED", result["status"])
                self.assertFalse(result["verdict"])
                self.assertEqual(expected_quiescent, result["runtime_child_quiescent"])
                self.assertEqual(0, result["effect_counts"]["thread/delete"])
                self.assertEqual(0, result["effect_counts"]["real_retry"])
                self.assertEqual(0, holder["manager"].client.calls.count("thread/delete"))

    def test_default_entrypoint_selects_production_and_completes_offline_handoff(self) -> None:
        actual = current_p7c16_source_authority()
        authority = P7C16SourceAuthority(
            actual.head, actual.tree, actual.launcher_blob, actual.p7c15_launcher_blob,
            actual.p7c14_launcher_blob, actual.p7c13_harness_blob, actual.p7c12_matcher_blob,
            actual.tests_init_blob, actual.tests_real_init_blob, actual.import_root_authority,
            True, True, True,
        )
        environment = {
            P7C16_FUTURE_REAL_GATE: "synthetic-token",
            P7C16_EXPECTED_HEAD: authority.head, P7C16_EXPECTED_TREE: authority.tree,
            P7C16_EXPECTED_LAUNCHER_BLOB: authority.launcher_blob,
            P7C16_EXPECTED_P7C15_LAUNCHER_BLOB: authority.p7c15_launcher_blob,
            P7C16_EXPECTED_P7C14_LAUNCHER_BLOB: authority.p7c14_launcher_blob,
            P7C16_EXPECTED_P7C13_HARNESS_BLOB: authority.p7c13_harness_blob,
            P7C16_EXPECTED_P7C12_MATCHER_BLOB: authority.p7c12_matcher_blob,
            P7C16_EXPECTED_TESTS_INIT_BLOB: authority.tests_init_blob,
            P7C16_EXPECTED_TESTS_REAL_INIT_BLOB: authority.tests_real_init_blob,
        }
        with tempfile.TemporaryDirectory(prefix="p7c16-default-entrypoint-") as directory:
            root = Path(directory); ledger_path = root / "authority" / "p7c16-one-shot.json"
            events: list[str] = []; selection_count = 0; coordinator_count = 0; delete_count = 0
            manager_holder: dict[str, Any] = {}
            real_run = subprocess.run

            def clean_git_run(*args: Any, **kwargs: Any) -> Any:
                command = args[0] if args else kwargs.get("args", ())
                if isinstance(command, (tuple, list)) and len(command) >= 2 and command[0] == "git" and command[1] == "diff":
                    return subprocess.CompletedProcess(command, 0)
                return real_run(*args, **kwargs)

            def dispatch(boot_path: Path) -> int:
                manager = _P7C16UnderlyingFakeRuntimeManager(); manager_holder["manager"] = manager
                return p7c16_future_child_main(boot_path, runtime_factory=lambda: manager)

            def factory(contract: P7C16ArchitectContract) -> P7C16PreparedFutureExecutor:
                nonlocal selection_count
                selection_count += 1
                return P7C16PreparedFutureExecutor._production_with_authority(
                    contract, ledger_path=ledger_path, child_dispatch=dispatch,
                    test_only_codex_home=root / "fake-home", test_only_watchdog_bounds=(10.0, 1.0, 1.0),
                    mutation_events=events,
                )

            original_coordinator = DeleteStorageCleanupCoordinator.__init__
            original_delete = p7c13.DialogueDeleteService.delete

            def counted_coordinator(instance: Any, *args: Any, **kwargs: Any) -> None:
                nonlocal coordinator_count
                coordinator_count += 1; original_coordinator(instance, *args, **kwargs)

            async def counted_delete(instance: Any, request: Any) -> Any:
                nonlocal delete_count
                delete_count += 1; return await original_delete(instance, request)

            with patch.object(subprocess, "run", side_effect=clean_git_run), \
                 patch.object(DeleteStorageCleanupCoordinator, "__init__", counted_coordinator), \
                 patch.object(p7c13.DialogueDeleteService, "delete", counted_delete), \
                 patch(__name__ + ".P7C16_TEST_ONLY_PRODUCTION_FACTORY", factory):
                observed = p7c16_real_entrypoint(environ=environment, authority=authority, executor=None)

            self.assertEqual("COMPLETED", observed.status)
            self.assertEqual(1, observed.child_count)
            self.assertEqual(1, selection_count)
            self.assertEqual(1, events.count("LEDGER_RESERVED"))
            self.assertEqual(1, events.count("CHILD_DISPATCHED"))
            self.assertEqual(1, coordinator_count); self.assertEqual(1, delete_count)
            self.assertEqual(1, manager_holder["manager"].client.calls.count("model/list"))
            self.assertEqual(1, manager_holder["manager"].client.calls.count("thread/delete"))
            self.assertEqual("COMPLETED", P7C16DurableOneShotLedger(ledger_path).read()["state"])

    def test_stage_authority_order_is_successor_owned(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        with tempfile.TemporaryDirectory(prefix="p7c16-stage-order-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
            self.assertEqual(0, p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=_P7C16UnderlyingFakeRuntimeManager))
            stages = [json.loads(line)["stage"] for line in Path(boot["stage_journal_path"]).read_text().splitlines()]
            required = ["CONTROLLER_BINDING", "DELETE_CLEANUP_AUTHORITY_CONFIRMED", "DELETE_CHAIN_READY",
                        "THREAD_DELETE_DISPATCH", "THREAD_DELETE_RESULT", "APPLICATION_DELETE_RESULT"]
            positions = [stages.index(stage) for stage in required]
            self.assertEqual(positions, sorted(positions))

    def test_gate_disabled_cli_projection_is_two_without_executor_injection(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(2, _module_main(["--p7c16-real-run"]))

    def test_default_entrypoint_cli_projects_every_terminal_state(self) -> None:
        actual = current_p7c16_source_authority()
        authority = P7C16SourceAuthority(
            actual.head, actual.tree, actual.launcher_blob, actual.p7c15_launcher_blob,
            actual.p7c14_launcher_blob, actual.p7c13_harness_blob, actual.p7c12_matcher_blob,
            actual.tests_init_blob, actual.tests_real_init_blob, actual.import_root_authority,
            True, True, True,
        )
        environment = {
            P7C16_FUTURE_REAL_GATE: "synthetic-token",
            P7C16_EXPECTED_HEAD: authority.head, P7C16_EXPECTED_TREE: authority.tree,
            P7C16_EXPECTED_LAUNCHER_BLOB: authority.launcher_blob,
            P7C16_EXPECTED_P7C15_LAUNCHER_BLOB: authority.p7c15_launcher_blob,
            P7C16_EXPECTED_P7C14_LAUNCHER_BLOB: authority.p7c14_launcher_blob,
            P7C16_EXPECTED_P7C13_HARNESS_BLOB: authority.p7c13_harness_blob,
            P7C16_EXPECTED_P7C12_MATCHER_BLOB: authority.p7c12_matcher_blob,
            P7C16_EXPECTED_TESTS_INIT_BLOB: authority.tests_init_blob,
            P7C16_EXPECTED_TESTS_REAL_INIT_BLOB: authority.tests_real_init_blob,
        }
        real_run = subprocess.run

        def clean_git_run(*args: Any, **kwargs: Any) -> Any:
            command = args[0] if args else kwargs.get("args", ())
            if isinstance(command, (tuple, list)) and len(command) >= 2 and command[0] == "git" and command[1] == "diff":
                return subprocess.CompletedProcess(command, 0)
            return real_run(*args, **kwargs)

        class ProjectionExecutor:
            def __init__(self, state: str) -> None:
                self.state = state

            def run(self, _contract: P7C16ArchitectContract) -> dict[str, str]:
                return {"state": self.state}

        for state, expected_exit in (("COMPLETED", 0), ("FAILED", 1), ("UNKNOWN", 1),
                                     ("CONFIRMED_PENDING", 1), ("TIMEOUT", 1)):
            with self.subTest(state=state):
                with patch.dict(os.environ, environment, clear=True), \
                     patch.object(subprocess, "run", side_effect=clean_git_run), \
                     patch(__name__ + ".current_p7c16_source_authority", return_value=authority), \
                     patch(__name__ + ".P7C16_TEST_ONLY_PRODUCTION_FACTORY", lambda _contract, selected=state: ProjectionExecutor(selected)):
                    self.assertEqual(expected_exit, _module_main(["--p7c16-real-run"]))

    def test_full_production_shaped_handoff_uses_real_cleanup_chain(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        with tempfile.TemporaryDirectory(prefix="p7c16-handoff-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
            holder: dict[str, Any] = {}
            def factory() -> Any:
                manager = _P7C16UnderlyingFakeRuntimeManager(); holder["manager"] = manager; return manager
            coordinator_count = 0
            delete_count = 0
            view_holder: dict[str, P7C16RuntimeManagerView] = {}
            original_coordinator = DeleteStorageCleanupCoordinator.__init__
            original_delete = p7c13.DialogueDeleteService.delete
            original_view_init = P7C16RuntimeManagerView.__init__
            def counted_coordinator(self: Any, *args: Any, **kwargs: Any) -> None:
                nonlocal coordinator_count
                coordinator_count += 1; original_coordinator(self, *args, **kwargs)
            async def counted_delete(self: Any, request: Any) -> Any:
                nonlocal delete_count
                delete_count += 1; return await original_delete(self, request)
            def counted_view(self: P7C16RuntimeManagerView, underlying: Any, selected_boot: Mapping[str, Any]) -> None:
                original_view_init(self, underlying, selected_boot); view_holder["view"] = self
            with patch.object(DeleteStorageCleanupCoordinator, "__init__", counted_coordinator), patch.object(p7c13.DialogueDeleteService, "delete", counted_delete), patch.object(P7C16RuntimeManagerView, "__init__", counted_view):
                code = p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=factory)
            result = P7C16ChildResultAuthority.read(boot["child_result_path"])
            self.assertEqual(0, code); self.assertEqual("PASS", result["status"]); self.assertTrue(result["verdict"])
            self.assertEqual(1, coordinator_count); self.assertEqual(1, delete_count)
            self.assertIs(view_holder["view"].underlying, holder["manager"])
            self.assertEqual(1, holder["manager"].reserve_count); self.assertEqual(1, holder["manager"].recreate_count)
            self.assertEqual(1, holder["manager"].release_count)
            self.assertEqual(boot["controller_db"], view_holder["view"].isolation_authority.controller_db_path)
            self.assertEqual(1, holder["manager"].client.calls.count("model/list"))
            self.assertEqual(1, holder["manager"].client.calls.count("thread/delete"))
            self.assertEqual({"new_threads": 1, "model/list": 1, "thread/start": 1, "thread/resume": 1,
                              "turn/start": 4, "approval_responses": 1, "allow_responses": 1,
                              "turn/interrupt": 1, "thread/delete": 1, "thread/read": 0, "thread/list": 0,
                              "second_child": 0, "real_retry": 0, "telegram": 0}, result["effect_counts"])

    def test_late_failure_converges_without_retry_or_duplicate_delete(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        with tempfile.TemporaryDirectory(prefix="p7c16-failure-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot, allow_test_home=True)
            holder: dict[str, Any] = {}
            def factory() -> Any:
                manager = _P7C16UnderlyingFakeRuntimeManager(scenario="delete_failure"); holder["manager"] = manager; return manager
            code = p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=factory)
            result = P7C16ChildResultAuthority.read(boot["child_result_path"])
            self.assertEqual(1, code); self.assertEqual("UNKNOWN", result["status"])
            self.assertTrue(result["runtime_child_quiescent"])
            self.assertEqual(1, holder["manager"].client.calls.count("thread/delete"))
            self.assertEqual(0, result["effect_counts"]["real_retry"])

    def test_production_executor_launches_one_owned_child_and_projects_completed(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12", "tests", "real-tests")
        with tempfile.TemporaryDirectory(prefix="p7c16-parent-") as directory:
            root = Path(directory); ledger_path = root / "authority" / "p7c16-one-shot.json"; fake_home = root / "fake-home"
            holder: dict[str, Any] = {}; manager_holder: dict[str, Any] = {}
            def dispatch(boot_path: Path) -> int:
                manager = _P7C16UnderlyingFakeRuntimeManager(); manager_holder["manager"] = manager
                holder["boot"] = boot_path
                return p7c16_future_child_main(boot_path, runtime_factory=lambda: manager)
            executor = P7C16PreparedFutureExecutor._production_with_authority(
                contract, ledger_path=ledger_path, child_dispatch=dispatch,
                test_only_codex_home=fake_home, test_only_watchdog_bounds=(10.0, 1.0, 1.0),
            )
            observed = executor.run(contract)
            self.assertEqual("COMPLETED", observed.status); self.assertEqual(1, observed.child_count)
            self.assertEqual("COMPLETED", P7C16DurableOneShotLedger(ledger_path).read()["state"])
            self.assertTrue(holder["boot"].name.startswith("p7c16-boot-"))
            self.assertEqual(1, manager_holder["manager"].client.calls.count("thread/delete"))
            with self.assertRaises(P7C16PreparationError):
                executor.run(contract)


def _module_main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c16-real-run" in arguments:
        try:
            result = p7c16_real_entrypoint(environ=dict(os.environ))
        except P7C16PreparationError: return 2
        if isinstance(result, p7c13.WatchdogResult):
            return 0 if result.status == "COMPLETED" else 1
        return 0 if result.get("state") == "COMPLETED" else 1
    if "--p7c16-future-child" in arguments:
        try:
            return p7c16_future_child_main(_p7c16_parse_child_boot(arguments))
        except (ValueError, IndexError, OSError, P7C16PreparationError):
            return 1
    unittest.main(argv=[sys.argv[0], *arguments]); return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
