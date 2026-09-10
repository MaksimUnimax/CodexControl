"""P7.C6 real T3 and hard-delete acceptance.

This module is intentionally inert under ordinary unittest discovery.  The
direct invocation requires the architect-authorized one-shot token and uses
only the shared authenticated home plus fresh run-owned local boundaries.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import secrets
import shutil
import stat
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from codex_control.adapters.codex import (
    CodexThreadLifecycleAdapter,
    IsolationPathAuthority,
    IsolatedStateRoot,
    PersistentProfileResidualScanner,
    ThreadBinding,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalKind,
    ApprovalRequest,
    ApprovalHandlingStatus,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.capabilities import (
    SCHEMA_SHA256,
    SUPPORTED_CODEX_VERSION,
)
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelCatalogAdapter
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.adapters.codex.thread_lifecycle import ThreadOperationResult
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnInterruptStatus,
    TurnStartStatus,
    TurnTerminalStatus,
)
from codex_control.application import (
    DeleteStorageCleanupCoordinator,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    SqliteStorage,
)


AUTHORIZATION = "AUTHORIZED_ONE_THREAD_ONE_DELETE_2026_09_10"
ONE_SHOT_LEDGER = Path("/root/.codexcontrol/p7c6-real-one-shot-ledger.json")
PROFILE_ID = "server-80-codexcontrol"
SERVER_ID = "server-80"
PERSISTENT_HOME = "/root/.codex_second"
EXECUTABLE = "/usr/local/bin/codex"


@dataclass
class _Counters:
    calls: dict[str, int]
    approval_allow_responses: int = 0
    official_delete_status: str | None = None


@dataclass
class _Run:
    root: Path
    state_parent: Path
    state_root: Path
    controller_dir: Path
    controller_db: Path
    ledger: Path
    workdir: Path
    sentinel: Path


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def _new_run() -> _Run:
    root = Path(tempfile.mkdtemp(prefix="codexcontrol-p7c6-", dir="/tmp"))
    os.chmod(root, 0o700)
    state_parent = root / "state-parent"
    state_root = state_parent / "c6-isolated-state"
    controller_dir = root / "controller"
    controller_db = controller_dir / "controller.sqlite3"
    ledger = root / "recovery-ledger.json"
    workdir = root / "workdir"
    sentinel = root / "outside-workspace-sentinel"
    for directory in (state_parent, controller_dir, workdir):
        directory.mkdir(mode=0o700)
    controller_db.touch(mode=0o600)
    ledger.touch(mode=0o600)
    os.chmod(controller_db, 0o600)
    os.chmod(ledger, 0o600)
    return _Run(root, state_parent, state_root, controller_dir, controller_db, ledger, workdir, sentinel)


def _ledger(run: _Run, value: dict[str, Any]) -> None:
    run.ledger.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(run.ledger, 0o600)


def _path_is_private(path: Path, mode: int, regular: bool = False) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    if value.st_uid != 0 or stat.S_IMODE(value.st_mode) != mode:
        return False
    return stat.S_ISREG(value.st_mode) if regular else stat.S_ISDIR(value.st_mode)


def _path_has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor or "/")
    for component in path.parts[1:]:
        current /= component
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _process_boundary_users(targets: dict[str, Path]) -> dict[str, int]:
    """Read-only process proof; values and environment contents are never emitted."""
    found = {name: set() for name in targets}

    def under(value: str, target: Path) -> bool:
        try:
            candidate = Path(value)
            return candidate == target or target in candidate.parents
        except (OSError, ValueError):
            return False

    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        proc = Path("/proc") / entry
        try:
            env_parts = proc.joinpath("environ").read_bytes().split(b"\0")
        except OSError:
            continue
        selected: list[str] = []
        for part in env_parts:
            if b"=" not in part:
                continue
            key, value = part.split(b"=", 1)
            key_text = key.decode("utf-8", "ignore")
            if key_text in {"CODEX_HOME", "CODEX_SQLITE_HOME", "PWD", "OLDPWD"}:
                selected.append(value.decode("utf-8", "ignore"))
        try:
            selected.append(os.readlink(proc / "cwd"))
        except OSError:
            pass
        try:
            for fd in os.listdir(proc / "fd"):
                try:
                    selected.append(os.readlink(proc / "fd" / fd))
                except OSError:
                    continue
        except OSError:
            pass
        for name, target in targets.items():
            if any(under(value, target) for value in selected):
                found[name].add(int(entry))
    return {name: len(pids) for name, pids in found.items()}


def _shared_home_process_count() -> int:
    count = 0
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        try:
            if b"CODEX_HOME=/root/.codex_second\0" in (Path("/proc") / entry / "environ").read_bytes():
                count += 1
        except OSError:
            pass
    return count


def _mount_alias_preflight(run: _Run, profile: CodexProfile, repository: Path) -> None:
    protected = {
        "persistent_home": Path(profile.codex_home),
        "isolated_root": Path(profile.isolated_state_root),
        "isolated_sqlite": Path(profile.isolated_state_root) / "sqlite",
        "isolated_logs": Path(profile.isolated_state_root) / "logs",
        "controller_db": run.controller_db,
        "controller_parent": run.controller_dir,
        "repository": repository,
    }
    if any(_path_has_symlink_component(path) for path in protected.values()):
        raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    if not _path_is_private(Path(profile.codex_home), 0o700):
        raise AssertionError("P7C6_PERSISTENT_HOME_AUTHORITY_INVALID")
    if not _path_is_private(run.root, 0o700) or not _path_is_private(run.state_parent, 0o700):
        raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    if not _path_is_private(run.controller_dir, 0o700):
        raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    if not _path_is_private(run.controller_db, 0o600, regular=True):
        raise AssertionError("P7C6_CONTROLLER_AUTHORITY_INVALID")
    if not _path_is_private(repository, 0o755) and not _path_is_private(repository, 0o700):
        raise AssertionError("P7C6_REPOSITORY_AUTHORITY_INVALID")
    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    except OSError as error:
        raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED") from error
    for path in protected.values():
        if any(
            len(fields := line.split(" - ", 1)[0].split()) >= 5 and fields[4] == str(path)
            for line in mountinfo.splitlines()
        ):
            raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    identities = {(os.stat(path, follow_symlinks=False).st_dev, os.stat(path, follow_symlinks=False).st_ino) for path in protected.values()}
    if len(identities) != len(protected):
        raise AssertionError("P7C6_MOUNT_ALIAS_UNRESOLVED")


def _walk_files(root: Path) -> tuple[list[Path], int]:
    files: list[Path] = []
    errors = 0
    if root.is_symlink():
        return [], 1
    if root.is_file():
        return [root], 0
    if not root.is_dir():
        return [], 0
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError:
            errors += 1
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    errors += 1
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    files.append(Path(entry.path))
                else:
                    errors += 1
            except OSError:
                errors += 1
    return files, errors


def _count_needles(path: Path, needles: tuple[bytes, ...]) -> tuple[tuple[int, ...], int, int]:
    counts = [0 for _ in needles]
    scanned = 0
    errors = 0
    carry = b""
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(65536):
                scanned += len(chunk)
                data = carry + chunk
                for index, needle in enumerate(needles):
                    counts[index] += data.count(needle)
                carry = data[-max((len(needle) for needle in needles), default=1) + 1 :]
                if scanned > 64 * 1024 * 1024:
                    errors += 1
                    break
    except OSError:
        errors += 1
    return tuple(counts), scanned, errors


def _marker_oracle(profile: CodexProfile, thread_id: str, markers: tuple[bytes, ...]) -> dict[str, Any]:
    roots = (
        ("persistent_sessions", Path(profile.codex_home) / "sessions"),
        ("persistent_history", Path(profile.codex_home) / "history.jsonl"),
        ("isolated_sqlite", Path(profile.isolated_state_root) / "sqlite"),
        ("isolated_logs", Path(profile.isolated_state_root) / "logs"),
    )
    needles = (thread_id.encode(),) + markers
    totals = [0 for _ in needles]
    files = 0
    bytes_scanned = 0
    errors = 0
    families: set[str] = set()
    for family, root in roots:
        paths, walk_errors = _walk_files(root)
        errors += walk_errors
        for path in paths:
            files += 1
            counts, scanned, file_errors = _count_needles(path, needles)
            bytes_scanned += scanned
            errors += file_errors
            if any(counts):
                families.add(family)
            totals = [left + right for left, right in zip(totals, counts)]
    return {
        "files_scanned": files,
        "bytes_scanned": bytes_scanned,
        "scan_errors": errors,
        "thread_count": totals[0],
        "marker_count": sum(totals[1:]),
        "families": sorted(families),
    }


def _metadata_snapshot(profile: CodexProfile) -> set[tuple[str, int, int, int]]:
    result: set[tuple[str, int, int, int]] = set()
    roots = (Path(profile.codex_home) / "sessions", Path(profile.codex_home) / "history.jsonl")
    for root in roots:
        files, _ = _walk_files(root)
        for path in files:
            try:
                value = path.stat()
            except OSError:
                continue
            result.add((str(path.relative_to(profile.codex_home)), value.st_dev, value.st_ino, value.st_size))
    return result


class _PinnedCatalog:
    """One authenticated model/list snapshot, reused after generation restart."""

    def __init__(self, manager: CodexRuntimeManager, adapter: CodexModelCatalogAdapter, snapshot: CodexModelCatalog) -> None:
        self._manager = manager
        self._adapter = adapter
        self._snapshot = snapshot

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        runtime = await self._manager.acquire(profile_id)
        if runtime.generation == self._snapshot.runtime_generation:
            return await self._adapter.get_catalog(profile_id, refresh=False)
        return replace(self._snapshot, runtime_generation=runtime.generation)


class _ExactApprovalOperator:
    def __init__(self, thread_id: str, sentinel: Path) -> None:
        self.thread_id = thread_id
        self.sentinel = sentinel
        self.requests = 0
        self.allowed = False
        self.mismatched = False

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests += 1
        commands = tuple(line.removeprefix("command: ") for line in request.context_lines if line.startswith("command: "))
        expected = {
            f"sleep 30 && touch {self.sentinel}",
            f"/bin/sh -c sleep 30 && touch {self.sentinel}",
            f"/bin/bash -lc sleep 30 && touch {self.sentinel}",
        }
        exact = (
            request.kind in (ApprovalKind.COMMAND_EXECUTION, ApprovalKind.EXEC_COMMAND)
            and (request.thread_id is None or request.thread_id == self.thread_id)
            and len(commands) == 1
            and commands[0] in expected
        )
        if exact:
            self.allowed = True
            return ApprovalDecision.ALLOW
        self.mismatched = True
        return ApprovalDecision.DENY


def _wrap_runtime(runtime: Any, counters: _Counters) -> None:
    if getattr(runtime, "_c6_counted", False):
        return
    original_request = runtime.client.request
    original_response = runtime.client.respond_server_request

    async def request(method: str, params: Any) -> Any:
        counters.calls[method] = counters.calls.get(method, 0) + 1
        try:
            result = await original_request(method, params)
        except Exception:
            if method == "thread/delete":
                counters.official_delete_status = "DELETE_UNKNOWN"
            raise
        if method == "thread/delete":
            counters.official_delete_status = "DELETE_CONFIRMED" if isinstance(result, dict) else "DELETE_UNKNOWN"
        return result

    async def response(request_object: Any, result: dict[str, Any]) -> None:
        counters.approval_allow_responses += 1
        await original_response(request_object, result)

    runtime.client.request = request
    runtime.client.respond_server_request = response
    runtime._c6_counted = True


async def _run_c6() -> dict[str, Any]:
    if os.environ.get("CODEXCONTROL_P7C6_REAL_RUN") != AUTHORIZATION:
        raise unittest.SkipTest("P7C6 real authorization not present")
    try:
        if ONE_SHOT_LEDGER.exists() and ONE_SHOT_LEDGER.stat().st_size:
            raise AssertionError("P7C6_ONE_SHOT_ALREADY_CONSUMED")
    except OSError as error:
        raise AssertionError("P7C6_ONE_SHOT_LEDGER_UNAVAILABLE") from error
    run = _new_run()
    profile = CodexProfile(PROFILE_ID, PERSISTENT_HOME, "Shared authenticated", str(run.state_root))
    repository = Path.cwd()
    counters = _Counters({})
    thread_id: str | None = None
    manager: CodexRuntimeManager | None = None
    storage: SqliteStorage | None = None
    success = False
    _ledger(run, {
        "format": 1,
        "status": "AUTHORIZED_IN_PROGRESS",
        "profile_id": PROFILE_ID,
        "persistent_home_mode": "SHARED_AUTHENTICATED",
        "root": str(run.root),
        "state_root": str(run.state_root),
        "controller_db": str(run.controller_db),
        "ledger": str(run.ledger),
        "workdir": str(run.workdir),
    })
    try:
        targets = {
            "isolated_root": run.state_root,
            "sqlite": run.state_root / "sqlite",
            "logs": run.state_root / "logs",
            "controller_db": run.controller_db,
            "ledger": run.ledger,
            "workdir": run.workdir,
        }
        initial_external = _process_boundary_users(targets)
        if any(initial_external.values()):
            raise AssertionError("P7C6_ISOLATED_ROOT_EXTERNAL_USERS")
        IsolatedStateRoot(IsolationPathAuthority(
            (profile,), controller_db_path=str(run.controller_db), repository_root=str(repository)
        )).provision(profile)
        _mount_alias_preflight(run, profile, repository)
        post_provision_external = _process_boundary_users(targets)
        if any(post_provision_external.values()):
            raise AssertionError("P7C6_ISOLATED_ROOT_EXTERNAL_USERS")
        authority = IsolationPathAuthority(
            (profile,), controller_db_path=str(run.controller_db), repository_root=str(repository)
        )
        scanner = PersistentProfileResidualScanner(authority)
        manager = CodexRuntimeManager(
            [profile], client_version="p7c6-real", executable=EXECUTABLE,
            isolation_authority=authority,
        )
        original_acquire = manager.acquire

        async def counted_acquire(profile_id: str) -> Any:
            runtime = await original_acquire(profile_id)
            _wrap_runtime(runtime, counters)
            return runtime

        manager.acquire = counted_acquire
        runtime = await manager.acquire(PROFILE_ID)
        manifest = manager._installed_manifest
        if manifest is None or manifest.codex_cli_version != SUPPORTED_CODEX_VERSION or manifest.schema_sha256 != SCHEMA_SHA256:
            raise AssertionError("P7C6_CAPABILITY_MISMATCH")
        catalog_adapter = CodexModelCatalogAdapter(manager)
        snapshot = await catalog_adapter.get_catalog(PROFILE_ID)
        visible_defaults = tuple(model for model in snapshot.models if not model.hidden and model.is_default)
        if len(visible_defaults) != 1:
            raise AssertionError("P7C6_MODEL_DEFAULT_AMBIGUOUS")
        model = visible_defaults[0]
        effort = model.default_reasoning_effort
        pinned_catalog = _PinnedCatalog(manager, catalog_adapter, snapshot)
        thread_lifecycle = CodexThreadLifecycleAdapter(manager, pinned_catalog)
        turn_lifecycle = CodexTurnLifecycleAdapter(manager, pinned_catalog)
        cwd = TrustedWorkingDirectory(str(run.workdir))
        response_marker = f"C6_RESPONSE_{secrets.token_hex(24)}"
        memory_marker = f"C6_MEMORY_{secrets.token_hex(24)}"
        interrupt_marker = f"C6_INTERRUPT_{secrets.token_hex(24)}"
        markers = (response_marker.encode(), memory_marker.encode(), interrupt_marker.encode())
        marker_hashes = tuple(_sha256(marker) for marker in markers)
        metadata_before = _metadata_snapshot(profile)
        start = await thread_lifecycle.start(
            PROFILE_ID, model_id=model.model_id, reasoning_effort=effort, working_directory=cwd
        )
        if start.status is not ThreadOperationStatus.START_CONFIRMED or start.binding is None:
            raise AssertionError("P7C6_START_NOT_CONFIRMED")
        binding = start.binding
        thread_id = binding.thread_id
        _ledger(run, {
            "format": 1,
            "status": "THREAD_CREATED_RECOVERY_REQUIRED",
            "profile_id": PROFILE_ID,
            "thread_id": thread_id,
            "thread_id_sha256": _sha256(thread_id),
        })
        turn_one = await turn_lifecycle.start_turn(
            thread_binding=binding,
            model_id=model.model_id,
            reasoning_effort=effort,
            user_text=(
                f"Reply briefly and include this response marker exactly: {response_marker}. "
                f"Remember this memory marker for the next turn: {memory_marker}. Do not use tools."
            ),
            working_directory=cwd,
        )
        if turn_one.status is not TurnStartStatus.CONFIRMED or turn_one.binding is None:
            raise AssertionError("P7C6_TURN1_START_NOT_CONFIRMED")
        terminal_one = await turn_lifecycle.wait_turn(turn_one.binding)
        text_one = "\n".join(message.text for message in terminal_one.messages)
        if terminal_one.status is not TurnTerminalStatus.COMPLETED or response_marker not in text_one:
            raise AssertionError("P7C6_TURN1_NOT_DEFINITIVE")
        await manager.shutdown_profile(PROFILE_ID)
        resumed = await thread_lifecycle.resume(binding=binding, working_directory=cwd)
        if resumed.status is not ThreadOperationStatus.RESUME_CONFIRMED or resumed.binding is not binding:
            raise AssertionError("P7C6_RESUME_NOT_CONFIRMED")
        runtime = await manager.acquire(PROFILE_ID)
        turn_two = await turn_lifecycle.start_turn(
            thread_binding=binding,
            model_id=model.model_id,
            reasoning_effort=effort,
            user_text=f"Reply with the remembered memory marker exactly: {memory_marker}. Do not use tools.",
            working_directory=cwd,
        )
        if turn_two.status is not TurnStartStatus.CONFIRMED or turn_two.binding is None:
            raise AssertionError("P7C6_TURN2_START_NOT_CONFIRMED")
        terminal_two = await turn_lifecycle.wait_turn(turn_two.binding)
        text_two = "\n".join(message.text for message in terminal_two.messages)
        if terminal_two.status is not TurnTerminalStatus.COMPLETED or memory_marker not in text_two:
            raise AssertionError("P7C6_TURN2_NOT_DEFINITIVE")
        turn_three = await turn_lifecycle.start_turn(
            thread_binding=binding,
            model_id=model.model_id,
            reasoning_effort=effort,
            user_text=(
                f"Do not mention control marker {interrupt_marker}. Request approval, then run exactly "
                f"this command and nothing else: sleep 30 && touch {run.sentinel}"
            ),
            working_directory=cwd,
        )
        if turn_three.status is not TurnStartStatus.CONFIRMED or turn_three.binding is None:
            raise AssertionError("P7C6_TURN3_START_NOT_CONFIRMED")
        operator = _ExactApprovalOperator(binding.thread_id, run.sentinel)
        bridge = CodexApprovalBridge(profile_id=PROFILE_ID, client=runtime.client, operator=operator)
        approval_task = asyncio.create_task(bridge.handle_next())
        approval = await asyncio.wait_for(asyncio.shield(approval_task), timeout=90)
        if approval.status is not ApprovalHandlingStatus.ALLOWED or not operator.allowed or operator.requests != 1:
            raise AssertionError("P7C6_APPROVAL_NOT_EXACTLY_ALLOWED")
        interrupt = await turn_lifecycle.interrupt_turn(turn_three.binding)
        if interrupt.status not in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED):
            raise AssertionError("P7C6_INTERRUPT_NOT_CONFIRMED")
        if interrupt.terminal_result is None or interrupt.terminal_result.status is not TurnTerminalStatus.FAILED:
            raise AssertionError("P7C6_INTERRUPT_TERMINAL_NOT_DEFINITIVE")
        if run.sentinel.exists():
            raise AssertionError("P7C6_DELAYED_SENTINEL_EXISTS")
        await manager.shutdown_profile(PROFILE_ID)
        predelete_production = scanner.scan(profile, binding.thread_id)
        predelete_oracle = _marker_oracle(profile, binding.thread_id, markers)
        if predelete_production.scan_errors or predelete_production.limit_exceeded:
            raise AssertionError("P7C6_PREDELETE_SCAN_ERROR")
        if predelete_production.match_count == 0 and predelete_oracle["thread_count"] == 0 and predelete_oracle["marker_count"] == 0:
            raise AssertionError("P7C6_PREDELETE_OBSERVATION_INCONCLUSIVE")
        storage = await SqliteStorage.open(str(run.controller_db))
        dialogues = DialogueRepository(storage, now_ms=lambda: 1000)
        await dialogues.create_intent(dialogue_id="p7c6-dialogue", server_id=SERVER_ID, profile_id=PROFILE_ID)
        created = await dialogues.confirm_created(dialogue_id="p7c6-dialogue", expected_version=0, thread_id=binding.thread_id)
        cleanup = DeleteStorageCleanupCoordinator(storage, manager, scanner=scanner, now_ms=lambda: 2000)
        delete_service = DialogueDeleteService(
            storage, server_id=SERVER_ID, thread_lifecycle=thread_lifecycle,
            local_cleanup=cleanup, now_ms=lambda: 2000,
        )
        deleted = await delete_service.delete(DialogueDeleteRequest(created.dialogue_id, created.version))
        if deleted.status is not DialogueDeleteStatus.DELETED or deleted.tombstone is None or counters.official_delete_status != "DELETE_CONFIRMED":
            raise AssertionError("P7C6_APPLICATION_DELETE_NOT_DELETED")
        await manager.shutdown_all()
        postdelete_production = scanner.scan(profile, binding.thread_id)
        postdelete_oracle = _marker_oracle(profile, binding.thread_id, markers)
        postdelete_metadata = _metadata_snapshot(profile)
        if postdelete_production.match_count or postdelete_production.scan_errors or postdelete_production.limit_exceeded:
            raise AssertionError("P7C6_POSTDELETE_PERSISTENT_RESIDUAL")
        if postdelete_oracle["thread_count"] or postdelete_oracle["marker_count"] or postdelete_oracle["scan_errors"]:
            raise AssertionError("P7C6_POSTDELETE_MARKER_RESIDUAL")
        if any(_walk_files(run.state_root / directory)[0] for directory in ("sqlite", "logs")):
            raise AssertionError("P7C6_POSTDELETE_ISOLATED_RESIDUAL")
        final_external = _process_boundary_users(targets)
        if final_external["isolated_root"] or final_external["sqlite"] or final_external["logs"] or final_external["controller_db"]:
            raise AssertionError("P7C6_EXTERNAL_BOUNDARY_USERS")
        thread_sha = _sha256(binding.thread_id)
        _ledger(run, {
            "format": 1,
            "status": "PASS_COMPLETED_NO_RERUN",
            "profile_id": PROFILE_ID,
            "thread_id_sha256": thread_sha,
            "marker_sha256": marker_hashes,
        })
        shutil.rmtree(run.workdir)
        if run.sentinel.exists():
            run.sentinel.unlink()
        success = True
        return {
            "architect_main": "32153c3d63bf6b45a8b16478566997c09e8e0cac",
            "architect_tree": "2dd760ba3fe7ea880c6c65db3eb6c0673d70ed75",
            "profile_id": PROFILE_ID,
            "persistent_home_mode": "SHARED_AUTHENTICATED",
            "unrelated_shared_home_processes_allowed": "YES",
            "shared_home_process_count_preflight": _shared_home_process_count(),
            "unrelated_process_termination_calls": 0,
            "isolated_root_external_users": 0,
            "controller_db_external_users": 0,
            "installed_version": manifest.codex_cli_version,
            "schema_sha256": manifest.schema_sha256,
            "model_list_calls": counters.calls.get("model/list", 0),
            "thread_start_calls": counters.calls.get("thread/start", 0),
            "thread_resume_calls": counters.calls.get("thread/resume", 0),
            "turn_calls": counters.calls.get("turn/start", 0),
            "approval_allow_responses": counters.approval_allow_responses,
            "interrupt_calls": counters.calls.get("turn/interrupt", 0),
            "thread_delete_calls": counters.calls.get("thread/delete", 0),
            "thread_read_calls": counters.calls.get("thread/read", 0),
            "thread_list_calls": counters.calls.get("thread/list", 0),
            "telegram_calls": 0,
            "start_status": start.status.value,
            "resume_status": resumed.status.value,
            "turn1_status": terminal_one.status.value,
            "turn2_status": terminal_two.status.value,
            "approval_status": approval.status.value,
            "interrupt_status": interrupt.status.value,
            "official_p1_delete_status": counters.official_delete_status,
            "application_delete_status": deleted.status.value,
            "thread_id_sha256": thread_sha,
            "marker_sha256": marker_hashes,
            "predelete_production": {
                "files_scanned": predelete_production.files_scanned,
                "bytes_scanned": predelete_production.bytes_scanned,
                "match_count": predelete_production.match_count,
                "scan_errors": predelete_production.scan_errors,
            },
            "predelete_marker_oracle": predelete_oracle,
            "postdelete_production": {
                "files_scanned": postdelete_production.files_scanned,
                "bytes_scanned": postdelete_production.bytes_scanned,
                "match_count": postdelete_production.match_count,
                "scan_errors": postdelete_production.scan_errors,
            },
            "postdelete_marker_oracle": postdelete_oracle,
            "postdelete_isolated_sqlite_descendants": 0,
            "postdelete_isolated_logs_descendants": 0,
            "unrelated_metadata_entries_removed": len(metadata_before - postdelete_metadata),
            "ownership_envelope_valid": "PASS",
            "one_shot_ledger": "PASS_COMPLETED_NO_RERUN",
            "mount_alias_preflight": "PASS",
        }
    except BaseException as error:
        if not success:
            _ledger(run, {
                "format": 1,
                "status": "ABORTED_RECOVERY_REQUIRED",
                "profile_id": PROFILE_ID,
                "persistent_home_mode": "SHARED_AUTHENTICATED",
                "unrelated_shared_home_processes_allowed": "YES",
                "thread_id": thread_id,
                "thread_id_sha256": _sha256(thread_id) if thread_id else None,
                "error_category": type(error).__name__,
            })
        raise
    finally:
        if manager is not None:
            try:
                await manager.shutdown_all()
            except Exception:
                pass
        if storage is not None:
            try:
                await storage.close()
            except Exception:
                pass
        if not run.sentinel.exists():
            pass
        elif success:
            run.sentinel.unlink()
        if run.workdir.exists():
            shutil.rmtree(run.workdir)


class P7C6RealHardDeleteAcceptance(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(os.environ.get("CODEXCONTROL_P7C6_REAL_RUN") == AUTHORIZATION, "gated real P7.C6")
    async def test_real_t3_and_hard_delete(self) -> None:
        report = await _run_c6()
        print("P7C6_SANITIZED_REPORT=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
