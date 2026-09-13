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
from codex_control.adapters.codex.runtime import ProfileReservation, RuntimeQuiescenceProof
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
P7C16_LEDGER_PATH = Path("/root/.codexcontrol/p7c16-one-shot.json")
P7C16_IMPORT_ROOTS = ("/root/CodexControl/src", "/root/CodexControl")
P7C16_PYTHONPATH = os.pathsep.join(P7C16_IMPORT_ROOTS)
P7C16_PROFILE_ID = "p7c16-successor-profile"
P7C16_LEDGER_SCHEMA = "p7c16-one-shot-v1"
P7C16_BOOT_SCHEMA = "p7c16-boot-v1"
P7C16_CHILD_RESULT_SCHEMA = "p7c16-child-result-v1"
P7C16_STATES = frozenset(("RESERVED", "COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"))
P7C16_BASE_HEAD = "3744cb19fba8ecba53d163b9e77f7adc9a213e6c"
P7C16_BASE_TREE = "2fd391fb6fff9c3e84bda7d3640155677a42f070"
P7C16_CONSUMED_P7C15_SOURCE = "17f8907068aa58de85d92800b9d87621e59ad1a3"
P7C16_CONSUMED_P7C15_LAUNCHER = "ebe4ffab2d08494452c1b132fe2fed50f4830a6b"
P7C16_P7C15_EVIDENCE = "b0f1f2014e23c60cb611c3176ad5f880b50dfc35"
P7C16_P7C14_LAUNCHER = "fcce1352d581522b4c4ab0e5235d0b927d2eceb8"
P7C16_P7C13_HARNESS = "5a1fe8e32d18600fcf7ace6b9aa24067238d6dec7"
P7C16_P7C12_MATCHER = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"


class P7C16PreparationError(RuntimeError):
    """Finite, path-free preparation failure."""


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
    import_root_authority: bool
    tracked_clean: bool


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
    expected_import_roots: tuple[str, str] = P7C16_IMPORT_ROOTS


def current_p7c16_source_authority() -> P7C16SourceAuthority:
    repo = _repository()
    clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repo).returncode == 0
    return P7C16SourceAuthority(
        _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}"), _blob(Path(__file__).resolve()),
        _blob(repo / "tests/real/test_p7_c15_final_hard_delete_successor.py"),
        P7C16_P7C14_LAUNCHER, P7C16_P7C13_HARNESS, P7C16_P7C12_MATCHER,
        os.environ.get("PYTHONPATH") == P7C16_PYTHONPATH, clean and index_clean,
    )


def p7c16_source_bundle_gate(environ: Mapping[str, str], contract: P7C16ArchitectContract | None,
                             authority: P7C16SourceAuthority) -> bool:
    if contract is None or contract.expected_import_roots != P7C16_IMPORT_ROOTS:
        return False
    expected = (contract.authorization_token, contract.expected_head, contract.expected_tree,
                contract.expected_launcher_blob, contract.expected_p7c15_launcher_blob,
                contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob,
                contract.expected_p7c12_matcher_blob)
    if not all(expected) or environ.get(P7C16_FUTURE_REAL_GATE) != contract.authorization_token:
        return False
    names = ((P7C16_EXPECTED_HEAD, contract.expected_head), (P7C16_EXPECTED_TREE, contract.expected_tree),
             (P7C16_EXPECTED_LAUNCHER_BLOB, contract.expected_launcher_blob),
             (P7C16_EXPECTED_P7C15_LAUNCHER_BLOB, contract.expected_p7c15_launcher_blob),
             (P7C16_EXPECTED_P7C14_LAUNCHER_BLOB, contract.expected_p7c14_launcher_blob),
             (P7C16_EXPECTED_P7C13_HARNESS_BLOB, contract.expected_p7c13_harness_blob),
             (P7C16_EXPECTED_P7C12_MATCHER_BLOB, contract.expected_p7c12_matcher_blob))
    return (all(environ.get(name) == value for name, value in names)
            and authority == P7C16SourceAuthority(contract.expected_head, contract.expected_tree,
                contract.expected_launcher_blob, contract.expected_p7c15_launcher_blob,
                contract.expected_p7c14_launcher_blob, contract.expected_p7c13_harness_blob,
                contract.expected_p7c12_matcher_blob, True, True))


def _contract_from_environment(environ: Mapping[str, str]) -> P7C16ArchitectContract:
    return P7C16ArchitectContract(
        environ.get(P7C16_FUTURE_REAL_GATE, ""), environ.get(P7C16_EXPECTED_HEAD, ""),
        environ.get(P7C16_EXPECTED_TREE, ""), environ.get(P7C16_EXPECTED_LAUNCHER_BLOB, ""),
        environ.get(P7C16_EXPECTED_P7C15_LAUNCHER_BLOB, ""), environ.get(P7C16_EXPECTED_P7C14_LAUNCHER_BLOB, ""),
        environ.get(P7C16_EXPECTED_P7C13_HARNESS_BLOB, ""), environ.get(P7C16_EXPECTED_P7C12_MATCHER_BLOB, ""),
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


class _P7C16Reservation:
    def __init__(self, manager: "P7C16RuntimeManagerView", profile_id: str) -> None:
        self.manager, self.profile_id, self.released = manager, profile_id, False

    def quiescence_proof(self) -> RuntimeQuiescenceProof:
        return RuntimeQuiescenceProof(self.profile_id, not self.released, False, False, not self.manager.runtime_quiescent)

    async def release(self) -> None:
        await self.manager.release(self)


class P7C16RuntimeManagerView(p7c15.GenerationTrackingRuntimeManager):
    """Delegating facade; cleanup reservations return to this same manager."""

    def __init__(self, underlying: Any, boot: Mapping[str, Any]) -> None:
        super().__init__(underlying)
        self.underlying = underlying
        self.profile = lambda profile_id: p7c13.CodexProfile(profile_id, boot["codex_home"], "P7.C16", boot["isolated_root"])
        # The composed P7.C15 engine still supplies its frozen profile identity
        # to the lifecycle adapters.  P7.C16 owns the executable, ledger and
        # filesystem authorities around that engine; no P7.C15 path is reused.
        self._authority_view = P7C16LateBoundControllerRuntimeView(
            underlying, self.profile(p7c15.P7C15_PROFILE_ID), _repository(), boot["controller_db"])
        self.reservations: list[_P7C16Reservation] = []
        self.reserve_count = 0
        self.cleanup_shutdowns = 0
        self.recreate_count = 0

    @property
    def isolation_authority(self) -> IsolationPathAuthority:
        if self._authority_view._exact_authority is None and Path(self._authority_view.controller_db_path).exists():
            self._authority_view.bind_exact_path()
        return self._authority_view.authority

    @property
    def runtime_quiescent(self) -> bool:
        return bool(getattr(self.underlying, "runtime_quiescent", False))

    def configure(self, boot: Mapping[str, Any]) -> None:
        configure = getattr(self.underlying, "configure", None)
        if callable(configure):
            configure(boot)

    async def shutdown_profile(self, profile_id: str) -> None:
        self.cleanup_shutdowns += 1
        await self.underlying.shutdown_profile(profile_id)

    async def reserve(self, profile_id: str) -> _P7C16Reservation:
        self.reserve_count += 1
        token = _P7C16Reservation(self, profile_id)
        self.reservations.append(token)
        return token

    async def release(self, token: _P7C16Reservation) -> None:
        if token not in self.reservations or token.released:
            raise ValueError("reservation_token_invalid")
        token.released = True
        self.reservations.remove(token)

    async def recreate_isolated_state_root(self, token: _P7C16Reservation) -> None:
        if token not in self.reservations or not token.quiescence_proof().is_quiescent:
            raise ValueError("reservation_invalid")
        self.recreate_count += 1
        IsolatedStateRoot(self.isolation_authority)._recreate_bound(self.profile(token.profile_id))

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

        def factory() -> P7C16RuntimeManagerView:
            raw = runtime_factory() if runtime_factory is not None else p7c15._build_p7c15_runtime_manager(boot)
            self.p7c16_manager = P7C16RuntimeManagerView(raw, boot)
            return self.p7c16_manager

        super().__init__(boot, journal, runtime_factory=factory, force_failure=force_failure, stage_timeouts=stage_timeouts)

    async def run_async(self) -> dict[str, Any]:
        try:
            result = await super().run_async()
            return result
        except BaseException:
            manager = self.p7c16_manager
            if manager is not None and not manager.runtime_quiescent:
                try:
                    await asyncio.wait_for(manager.shutdown_profile(P7C16_PROFILE_ID), timeout=2.0)
                except BaseException:
                    self._convergence_failed = True
            raise


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
    paths.update({"ledger": str(authority / "p7c16-one-shot.json"), "codex_home": str(root / "home")})
    Path(paths["codex_home"]).mkdir(mode=0o700, exist_ok=True)
    return {"schema": P7C16_BOOT_SCHEMA, "profile_id": P7C16_PROFILE_ID, "source_head": contract.expected_head,
            "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
            "run_id_hash": _sha256("p7c16-synthetic"), "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET),
            "codex_home": paths["codex_home"], "isolated_root": paths["isolated_root"],
            "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"),
            "isolated_logs": str(Path(paths["isolated_root"]) / "logs"), "controller_db": paths["controller_db"],
            "workdir": paths["workdir"], "approval_target": paths["approval_target"], "ledger_path": paths["ledger"],
            "boot_authority_path": paths["boot"], "child_result_path": paths["child_result"],
            "wire_path": paths["wire"], "approval_journal_path": paths["approval_journal"],
            "stage_journal_path": paths["stage"]}


class P7C16RootOnlyBootAuthority:
    KEYS = frozenset(("schema", "profile_id", "source_head", "source_tree", "launcher_blob", "run_id_hash", "effect_ceiling",
                      "codex_home", "isolated_root", "isolated_sqlite", "isolated_logs", "controller_db", "workdir", "approval_target",
                      "ledger_path", "boot_authority_path", "child_result_path", "wire_path", "approval_journal_path", "stage_journal_path"))

    def __init__(self, path: str | Path) -> None: self.path = Path(path)

    def create(self, value: Mapping[str, Any]) -> dict[str, Any]:
        if set(value) != self.KEYS or value["schema"] != P7C16_BOOT_SCHEMA:
            raise P7C16PreparationError("P7.C16 boot schema invalid")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(dict(value), stream, sort_keys=True, separators=(",", ":")); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        return dict(value)

    def read(self) -> dict[str, Any]:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if set(value) != self.KEYS or value["schema"] != P7C16_BOOT_SCHEMA:
            raise P7C16PreparationError("P7.C16 boot schema invalid")
        return value


class P7C16ChildResultAuthority:
    @staticmethod
    def write(path: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
        path = Path(path); path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(dict(payload), stream, sort_keys=True, separators=(",", ":")); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        return dict(payload)

    @staticmethod
    def read(path: str | Path) -> dict[str, Any]:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if value.get("schema") != P7C16_CHILD_RESULT_SCHEMA or value.get("status") not in {"PASS", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"}:
            raise P7C16PreparationError("P7.C16 child result invalid")
        return value


class P7C16DurableOneShotLedger:
    def __init__(self, path: str | Path) -> None: self.path = Path(path)

    def reserve(self, record: Mapping[str, Any]) -> bool:
        if record.get("schema") != P7C16_LEDGER_SCHEMA or record.get("state") != "RESERVED":
            raise P7C16PreparationError("P7.C16 ledger schema invalid")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(dict(record), stream, sort_keys=True, separators=(",", ":")); stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        return True

    def update(self, **changes: Any) -> None:
        value = json.loads(self.path.read_text(encoding="utf-8")); state = changes.get("state", value.get("state"))
        if state not in P7C16_STATES - {"RESERVED"} or value.get("state") != "RESERVED":
            raise P7C16PreparationError("P7.C16 terminal transition invalid")
        value.update(changes); self.path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def read(self) -> dict[str, Any]: return json.loads(self.path.read_text(encoding="utf-8"))


class P7C16PreparedFutureExecutor:
    def __init__(self, ledger: P7C16DurableOneShotLedger, child: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None) -> None:
        self.ledger, self.child, self.calls = ledger, child, 0

    def run(self, contract: P7C16ArchitectContract) -> dict[str, Any]:
        if self.calls: raise P7C16PreparationError("second child/retry forbidden")
        self.calls += 1; run_hash = _sha256(os.urandom(16)); root = self.ledger.path.parent
        paths = p7c16_fresh_run_paths(run_hash, root=root / f"p7c16-state-{run_hash[:12]}", authority=root)
        record = {"schema": P7C16_LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head,
                  "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
                  "run_id_hash": run_hash, "effect_counts": {}, "recovery": {}}
        if not self.ledger.reserve(record): raise P7C16PreparationError("P7.C16 reservation consumed")
        boot = {"schema": P7C16_BOOT_SCHEMA, "profile_id": P7C16_PROFILE_ID, "source_head": contract.expected_head,
                "source_tree": contract.expected_tree, "launcher_blob": contract.expected_launcher_blob,
                "run_id_hash": run_hash, "effect_ceiling": dict(p7c13.FROZEN_EFFECT_BUDGET), **paths,
                "ledger_path": str(self.ledger.path), "codex_home": str(root / "p7c16-home"),
                "isolated_sqlite": str(Path(paths["isolated_root"]) / "sqlite"), "isolated_logs": str(Path(paths["isolated_root"]) / "logs"),
                "boot_authority_path": paths["boot"], "child_result_path": paths["child_result"],
                "wire_path": paths["wire"], "approval_journal_path": paths["approval_journal"], "stage_journal_path": paths["stage"]}
        Path(boot["codex_home"]).mkdir(mode=0o700, parents=True, exist_ok=True)
        P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot)
        result = dict(self.child(boot)) if self.child is not None else {"status": "FAILED", "verdict": False, "runtime_child_quiescent": False}
        result.setdefault("schema", P7C16_CHILD_RESULT_SCHEMA); result.setdefault("effect_counts", {}); result.setdefault("last_confirmed_stage", "PRE_CHILD")
        P7C16ChildResultAuthority.write(boot["child_result_path"], result)
        self.ledger.update(state=result.get("status", "FAILED"), recovery={"child_status": result.get("status"), "child_result": _sha256(boot["child_result_path"])})
        return result


def _p7c16_parse_child_boot(arguments: Sequence[str]) -> Path:
    if len(arguments) != 3 or arguments.count("--p7c16-future-child") != 1 or arguments.count("--boot-authority") != 1:
        raise P7C16PreparationError("P7.C16 child arguments invalid")
    index = arguments.index("--boot-authority")
    if index + 1 >= len(arguments) or not os.path.isabs(arguments[index + 1]):
        raise P7C16PreparationError("P7.C16 boot authority missing")
    return Path(arguments[index + 1]).absolute()


def p7c16_future_child_main(boot_path: str | Path, *, runtime_factory: Callable[[], Any] | None = None,
                            force_failure: bool = False) -> int:
    """Run one owned successor child against a supplied external boundary."""
    boot = P7C16RootOnlyBootAuthority(boot_path).read()
    journal = P7C16StageJournal(boot["stage_journal_path"])
    child: P7C16ProductionChildOrchestrator | None = None
    old_umask = os.umask(0o077)
    try:
        child = P7C16ProductionChildOrchestrator(boot, journal, runtime_factory=runtime_factory, force_failure=force_failure)
        result = asyncio.run(child.run_async())
        payload = dict(result)
        payload.update({"schema": P7C16_CHILD_RESULT_SCHEMA, "effect_counts": {
            key: child.budget.count(key) for key in p7c13.FROZEN_EFFECT_BUDGET},
            "stage_journal_sha256": journal.digest()})
        P7C16ChildResultAuthority.write(boot["child_result_path"], payload)
        return 0 if payload.get("status") == "PASS" and payload.get("verdict") is True else 1
    except Exception as error:
        payload = {"schema": P7C16_CHILD_RESULT_SCHEMA, "status": "FAILED", "verdict": False,
                   "last_confirmed_stage": child.last_confirmed_stage if child is not None else "PRE_CHILD",
                   "terminal_exception_class": type(error).__name__, "terminal_error_category": getattr(getattr(error, "category", None), "value", None),
                   "runtime_child_quiescent": bool(child and child.p7c16_manager and child.p7c16_manager.runtime_quiescent),
                   "effect_counts": {key: child.budget.count(key) if child is not None else 0 for key in p7c13.FROZEN_EFFECT_BUDGET}}
        try:
            journal.append("TERMINAL_EXCEPTION", "FAILED", effect_class="terminal", error=error)
            payload["stage_journal_sha256"] = journal.digest()
            P7C16ChildResultAuthority.write(boot["child_result_path"], payload)
        except (OSError, P7C16PreparationError):
            pass
        return 1
    finally:
        os.umask(old_umask)


def p7c16_real_entrypoint(*, environ: Mapping[str, str], authority: P7C16SourceAuthority | None = None,
                          executor: P7C16PreparedFutureExecutor | None = None) -> dict[str, Any]:
    current = authority or current_p7c16_source_authority(); contract = _contract_from_environment(environ)
    if not p7c16_source_bundle_gate(environ, contract, current):
        raise P7C16PreparationError("P7C16_FUTURE_REAL_GATE=DISABLED_OR_SOURCE_MISMATCH")
    return (executor or P7C16PreparedFutureExecutor(P7C16DurableOneShotLedger(P7C16_LEDGER_PATH))).run(contract)


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

    def test_full_production_shaped_handoff_uses_real_cleanup_chain(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12")
        with tempfile.TemporaryDirectory(prefix="p7c16-handoff-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot)
            holder: dict[str, Any] = {}
            def factory() -> Any:
                manager = p7c15._FakeRuntimeManager(); holder["manager"] = manager; return manager
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
            self.assertEqual(1, view_holder["view"].reserve_count); self.assertEqual(1, view_holder["view"].recreate_count)
            self.assertEqual(boot["controller_db"], view_holder["view"].isolation_authority.controller_db_path)
            self.assertEqual(1, holder["manager"].client.calls.count("model/list"))
            self.assertEqual(1, holder["manager"].client.calls.count("thread/delete"))
            self.assertEqual({"new_threads": 1, "model/list": 1, "thread/start": 1, "thread/resume": 1,
                              "turn/start": 4, "approval_responses": 1, "allow_responses": 1,
                              "turn/interrupt": 1, "thread/delete": 1, "thread/read": 0, "thread/list": 0,
                              "second_child": 0, "real_retry": 0, "telegram": 0}, result["effect_counts"])

    def test_late_failure_converges_without_retry_or_duplicate_delete(self) -> None:
        contract = P7C16ArchitectContract("synthetic-token", "head", "tree", "launcher", "p15", "p14", "p13", "p12")
        with tempfile.TemporaryDirectory(prefix="p7c16-failure-") as directory:
            root = Path(directory); boot = _p7c16_boot(root, contract)
            P7C16RootOnlyBootAuthority(boot["boot_authority_path"]).create(boot)
            holder: dict[str, Any] = {}
            def factory() -> Any:
                manager = p7c15._FakeRuntimeManager(scenario="delete_failure"); holder["manager"] = manager; return manager
            code = p7c16_future_child_main(boot["boot_authority_path"], runtime_factory=factory)
            result = P7C16ChildResultAuthority.read(boot["child_result_path"])
            self.assertEqual(1, code); self.assertEqual("UNKNOWN", result["status"])
            self.assertTrue(result["runtime_child_quiescent"])
            self.assertEqual(1, holder["manager"].client.calls.count("thread/delete"))
            self.assertEqual(0, result["effect_counts"]["real_retry"])


def _module_main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c16-real-run" in arguments:
        try: p7c16_real_entrypoint(environ=dict(os.environ))
        except P7C16PreparationError: return 2
        return 1
    if "--p7c16-future-child" in arguments:
        try:
            return p7c16_future_child_main(_p7c16_parse_child_boot(arguments))
        except (ValueError, IndexError, OSError, P7C16PreparationError):
            return 1
    unittest.main(argv=[sys.argv[0], *arguments]); return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
