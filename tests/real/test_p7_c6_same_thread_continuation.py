"""P7.C6 same-thread continuation preparation.

This module is an offline preparation harness.  The real method is gated by a
new authorization value and ordinary unittest discovery skips it before any
runtime is acquired.  The retained Run-1 thread is never started here; the
future flow reconstructs a binding and resumes it only after a later,
independent authorization.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import os
import re
import secrets
import shlex
import stat
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Sequence

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
    ApprovalHandlingStatus,
    ApprovalRequest,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.capabilities import SCHEMA_SHA256, SUPPORTED_CODEX_VERSION
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelCatalogAdapter
from codex_control.adapters.codex.runtime import CodexRuntimeManager
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
from codex_control.storage import DialogueRepository, SCHEMA_VERSION, SqliteStorage


AUTHORIZATION = "AUTHORIZED_RETAINED_THREAD_T4_T5_DELETE_2026_09_10"
ARCHITECT_BASE_SHA = "96ea032e94bdff7938d91114dc83c210cba708ea"
ARCHITECT_BASE_TREE = "7b39cd12ff5fc94ce017420d7942978bf2d840a4"
PREP_SOURCE_AUTHORITY = ARCHITECT_BASE_SHA
PROFILE_ID = "server-80-codexcontrol"
SERVER_ID = "server-80"
PERSISTENT_HOME = "/root/.codex_second"
EXECUTABLE = "/usr/local/bin/codex"
RUN1_LATCH = Path("/root/.codexcontrol/p7c6-real-one-shot-ledger.json")
RUN1_THREAD_SHA256 = "9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6"
RUN1_LATCH_SHA256 = "50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e"
MARKER_RE = {
    "response_marker": re.compile(r"C6_RESPONSE_[0-9a-f]{48}"),
    "memory_marker": re.compile(r"C6_MEMORY_[0-9a-f]{48}"),
    "interrupt_marker": re.compile(r"C6_INTERRUPT_[0-9a-f]{48}"),
}
WRAPPERS = frozenset(("sh", "/bin/sh", "/usr/bin/sh", "bash", "/bin/bash", "/usr/bin/bash"))
WRAPPER_OPTIONS = frozenset(("-c", "-lc"))


class ContinuationLatchError(Exception):
    """Finite fail-closed continuation latch error."""


class ContinuationLatchExists(ContinuationLatchError):
    pass


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def _private_regular(path: Path, mode: int) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(value.st_mode)
        and not stat.S_ISLNK(value.st_mode)
        and value.st_uid == 0
        and value.st_gid == 0
        and stat.S_IMODE(value.st_mode) == mode
        and value.st_nlink == 1
    )


def _private_directory(path: Path, mode: int) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(value.st_mode) and not stat.S_ISLNK(value.st_mode) and value.st_uid == 0 and value.st_gid == 0 and stat.S_IMODE(value.st_mode) == mode


def _fsync_parent(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(path.parent), flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _safe_continuation_latch_record(
    *, source_prep_commit: str, retained_thread_sha256: str, continuation_identity: str, status: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_prep_commit):
        raise ContinuationLatchError("source_authority_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", retained_thread_sha256):
        raise ContinuationLatchError("thread_hash_invalid")
    if not re.fullmatch(r"[A-Z0-9_]{1,96}", continuation_identity):
        raise ContinuationLatchError("continuation_identity_invalid")
    if not re.fullmatch(r"[A-Z0-9_]{1,96}", status):
        raise ContinuationLatchError("status_invalid")
    return {
        "format": 1,
        "status": status,
        "source_prep_commit": source_prep_commit,
        "retained_thread_sha256": retained_thread_sha256,
        "continuation_identity": continuation_identity,
    }


def create_continuation_latch(
    path: Path, *, source_prep_commit: str, retained_thread_sha256: str, continuation_identity: str,
) -> dict[str, Any]:
    """Atomically reserve a continuation before its first business RPC."""
    if not _private_directory(path.parent, 0o700):
        raise ContinuationLatchError("parent_authority_invalid")
    record = _safe_continuation_latch_record(
        source_prep_commit=source_prep_commit,
        retained_thread_sha256=retained_thread_sha256,
        continuation_identity=continuation_identity,
        status="CONTINUATION_RESERVED_BEFORE_RESUME",
    )
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(str(path), flags, 0o600)
    except FileExistsError as error:
        raise ContinuationLatchExists("already_exists") from error
    except OSError as error:
        raise ContinuationLatchError("create_failed") from error
    try:
        written = os.write(fd, payload)
        if written != len(payload):
            raise ContinuationLatchError("short_write")
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_parent(path)
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("created_authority_invalid")
    return record


def read_continuation_latch(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("latch_authority_invalid")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContinuationLatchError("latch_content_invalid") from error
    if record != expected:
        raise ContinuationLatchError("latch_content_mismatch")
    return record


@dataclass(frozen=True)
class StructuralApprovalResult:
    allowed: bool
    grammar: str
    mismatch_flags: tuple[str, ...]
    request_count: int


def _context_values(request: ApprovalRequest, prefix: str) -> tuple[str, ...]:
    return tuple(line[len(prefix):] for line in request.context_lines if line.startswith(prefix))


def _command_grammar(observed: str, expected_inner: str) -> str:
    try:
        expected_tokens = shlex.split(expected_inner)
        observed_tokens = shlex.split(observed)
    except ValueError:
        return "UNPARSEABLE"
    if observed_tokens == expected_tokens:
        return "EXACT_INNER"
    if len(observed_tokens) != 3 or observed_tokens[0] not in WRAPPERS or observed_tokens[1] not in WRAPPER_OPTIONS:
        return "DENY"
    try:
        inner_tokens = shlex.split(observed_tokens[2])
    except ValueError:
        return "UNPARSEABLE"
    return "ONE_SHELL_WRAPPER" if inner_tokens == expected_tokens else "DENY"


def match_structural_approval(
    requests: Sequence[ApprovalRequest], *, expected_thread_id: str, expected_turn_id: str,
    expected_cwd: str, expected_inner_command: str, expected_marker: str, expected_sentinel: str,
) -> StructuralApprovalResult:
    """Match one exact request and the two proven command grammars."""
    flags: list[str] = []
    request_count = len(requests)
    if request_count != 1:
        flags.append("REQUEST_COUNT")
    if request_count == 0:
        return StructuralApprovalResult(False, "NONE", tuple(flags + ["REQUEST_MISSING"]), request_count)
    request = requests[-1]
    if request.kind is not ApprovalKind.COMMAND_EXECUTION:
        flags.append("KIND")
    if request.thread_id != expected_thread_id:
        flags.append("THREAD")
    if request.turn_id != expected_turn_id:
        flags.append("TURN")
    cwds = _context_values(request, "cwd: ")
    if len(cwds) != 1 or os.path.normpath(cwds[0]) != os.path.normpath(expected_cwd):
        flags.append("CWD")
    commands = _context_values(request, "command: ")
    if len(commands) != 1:
        flags.append("COMMAND_CONTEXT")
        observed = ""
    else:
        observed = commands[0]
    if expected_marker not in observed:
        flags.append("MARKER")
    if expected_sentinel not in observed:
        flags.append("SENTINEL")
    grammar = _command_grammar(observed, expected_inner_command) if commands else "NONE"
    if grammar == "UNPARSEABLE":
        flags.append("UNPARSEABLE")
    elif grammar not in ("EXACT_INNER", "ONE_SHELL_WRAPPER"):
        flags.append("GRAMMAR")
    return StructuralApprovalResult(not flags, grammar, tuple(flags), request_count)


class _StructuralApprovalOperator:
    def __init__(self, *, thread_id: str, turn_id: asyncio.Future[str], cwd: str, inner: str, marker: str, sentinel: str) -> None:
        self._thread_id = thread_id
        self._turn_id = turn_id
        self._cwd = cwd
        self._inner = inner
        self._marker = marker
        self._sentinel = sentinel
        self.requests: list[ApprovalRequest] = []
        self.results: list[StructuralApprovalResult] = []
        self.allow_count = 0

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        await self._turn_id
        self.requests.append(request)
        result = match_structural_approval(
            self.requests,
            expected_thread_id=self._thread_id,
            expected_turn_id=self._turn_id.result(),
            expected_cwd=self._cwd,
            expected_inner_command=self._inner,
            expected_marker=self._marker,
            expected_sentinel=self._sentinel,
        )
        self.results.append(result)
        if result.allowed:
            self.allow_count += 1
            return ApprovalDecision.ALLOW
        return ApprovalDecision.DENY


def _request(command: str, *, thread: str = "thread", turn: str = "turn", cwd: str = "/run", kind: ApprovalKind = ApprovalKind.COMMAND_EXECUTION) -> ApprovalRequest:
    return ApprovalRequest(1, PROFILE_ID, "wire", kind, thread, turn, "item", (f"cwd: {cwd}", f"command: {command}"))


def _find_retained_authority() -> tuple[Path, str, dict[str, str]]:
    candidates: list[tuple[Path, str]] = []
    for directory, dirs, names in os.walk("/tmp", topdown=True, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in names:
            if name != "recovery-ledger.json":
                continue
            path = Path(directory) / name
            try:
                if not _private_regular(path, 0o600):
                    continue
                record = json.loads(path.read_text(encoding="utf-8"))
                thread_id = record.get("thread_id")
                if record.get("profile_id") == PROFILE_ID and isinstance(thread_id, str) and _sha256(thread_id) == RUN1_THREAD_SHA256:
                    candidates.append((path, thread_id))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
    if len(candidates) != 1:
        raise AssertionError("P7C6_RECOVERY_LEDGER_AMBIGUOUS")
    ledger, thread_id = candidates[0]
    supplement = ledger.parent / "p7c6-marker-recovery-supplement.json"
    if not _private_regular(supplement, 0o600):
        raise AssertionError("P7C6_MARKER_SUPPLEMENT_UNSAFE")
    values = json.loads(supplement.read_text(encoding="utf-8"))
    expected_keys = {
        "format", "status", "thread_id_sha256", "response_marker", "memory_marker", "interrupt_marker",
        "response_marker_sha256", "memory_marker_sha256", "interrupt_marker_sha256",
    }
    if set(values) != expected_keys or values.get("format") != 1 or values.get("thread_id_sha256") != RUN1_THREAD_SHA256:
        raise AssertionError("P7C6_MARKER_SUPPLEMENT_INVALID")
    markers: dict[str, str] = {}
    for key, pattern in MARKER_RE.items():
        value = values.get(key)
        if not isinstance(value, str) or pattern.fullmatch(value) is None or values.get(key + "_sha256") != _sha256(value):
            raise AssertionError("P7C6_MARKER_SUPPLEMENT_INVALID")
        markers[key] = value
    return ledger.parent, thread_id, markers


def _validate_run1_latch() -> None:
    if not _private_directory(RUN1_LATCH.parent, 0o700) or not _private_regular(RUN1_LATCH, 0o600):
        raise AssertionError("P7C6_ACCEPTED_RUN1_LATCH_DRIFT")
    if _sha256(RUN1_LATCH.read_bytes()) != RUN1_LATCH_SHA256:
        raise AssertionError("P7C6_ACCEPTED_RUN1_LATCH_DRIFT")


def _boundary_users(targets: Sequence[Path]) -> int:
    found: set[int] = set()
    for entry in os.listdir("/proc"):
        if not entry.isdigit() or int(entry) == os.getpid():
            continue
        proc = Path("/proc") / entry
        values: list[str] = []
        try:
            for part in (proc / "environ").read_bytes().split(b"\0"):
                if b"=" in part:
                    key, value = part.split(b"=", 1)
                    if key in (b"CODEX_SQLITE_HOME", b"PWD", b"OLDPWD"):
                        values.append(value.decode("utf-8", "ignore"))
        except OSError:
            pass
        try:
            values.append(os.readlink(proc / "cwd"))
        except OSError:
            pass
        try:
            for fd in os.listdir(proc / "fd"):
                try:
                    values.append(os.readlink(proc / "fd" / fd))
                except OSError:
                    continue
        except OSError:
            pass
        try:
            if any(Path(value) == target or target in Path(value).parents for value in values for target in targets):
                found.add(int(entry))
        except (OSError, ValueError):
            continue
    return len(found)


class _PinnedCatalog:
    def __init__(self, manager: CodexRuntimeManager, adapter: CodexModelCatalogAdapter, snapshot: CodexModelCatalog) -> None:
        self._manager = manager
        self._adapter = adapter
        self._snapshot = snapshot

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        runtime = await self._manager.acquire(profile_id)
        if runtime.generation == self._snapshot.runtime_generation:
            return await self._adapter.get_catalog(profile_id, refresh=False)
        return replace(self._snapshot, runtime_generation=runtime.generation)


def _oracle_files(root: Path) -> tuple[list[Path], int]:
    if root.is_symlink():
        return [], 1
    if root.is_file():
        return [root], 0
    if not root.exists():
        return [], 0
    if not root.is_dir():
        return [], 1
    files: list[Path] = []
    errors = 0
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError:
            errors += 1
            continue
        for entry in entries:
            path = Path(entry.path)
            try:
                if entry.is_symlink():
                    errors += 1
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    errors += 1
            except OSError:
                errors += 1
    return files, errors


def _marker_oracle(profile: CodexProfile, thread_id: str, markers: Sequence[str]) -> dict[str, int]:
    roots = (
        Path(profile.codex_home) / "sessions",
        Path(profile.codex_home) / "history.jsonl",
        Path(profile.isolated_state_root) / "sqlite",
        Path(profile.isolated_state_root) / "logs",
    )
    needles = tuple(value.encode("utf-8") for value in (thread_id, *markers))
    counts = [0] * len(needles)
    errors = 0
    for root in roots:
        paths, walk_errors = _oracle_files(root)
        errors += walk_errors
        for path in paths:
            try:
                data = path.read_bytes()
                for index, needle in enumerate(needles):
                    counts[index] += data.count(needle)
            except OSError:
                errors += 1
    return {"thread_count": counts[0], "marker_count": sum(counts[1:]), "scan_errors": errors}


async def _run_real_continuation() -> dict[str, Any]:
    if os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION") != AUTHORIZATION:
        raise unittest.SkipTest("P7C6 same-thread continuation authorization not present")

    _validate_run1_latch()
    run_root, retained_thread_id, run1_markers = _find_retained_authority()
    state_root = run_root / "state-parent" / "c6-isolated-state"
    controller_db = run_root / "controller" / "controller.sqlite3"
    profile = CodexProfile(PROFILE_ID, PERSISTENT_HOME, "Shared authenticated", str(state_root))
    repository = Path.cwd()
    authority = IsolationPathAuthority((profile,), controller_db_path=str(controller_db), repository_root=str(repository))
    IsolatedStateRoot(authority).validate(profile)
    if _boundary_users((state_root, state_root / "sqlite", state_root / "logs", controller_db)):
        raise AssertionError("P7C6_RETAINED_BOUNDARY_EXTERNAL_USERS")

    latch_path = Path("/root/.codexcontrol/p7c6-same-thread-continuation-ledger.json")
    latch = create_continuation_latch(
        latch_path,
        source_prep_commit=PREP_SOURCE_AUTHORITY,
        retained_thread_sha256=RUN1_THREAD_SHA256,
        continuation_identity="RETAINED_THREAD_T4_T5_DELETE",
    )

    manager: CodexRuntimeManager | None = None
    storage: SqliteStorage | None = None
    sentinel: Path | None = None
    workdir: Path | None = None
    counters: dict[str, int] = {}
    approval_responses = 0

    try:
        manager = CodexRuntimeManager([profile], client_version="p7c6-continuation", executable=EXECUTABLE, isolation_authority=authority)
        original_acquire = manager.acquire

        async def counted_acquire(profile_id: str) -> Any:
            runtime = await original_acquire(profile_id)
            original_request = runtime.client.request
            original_response = runtime.client.respond_server_request

            async def request(method: str, params: Any) -> Any:
                counters[method] = counters.get(method, 0) + 1
                return await original_request(method, params)

            async def response(request_object: Any, result: dict[str, Any]) -> None:
                nonlocal approval_responses
                approval_responses += 1
                await original_response(request_object, result)

            if not getattr(runtime, "_p7c6_continuation_counted", False):
                runtime.client.request = request
                runtime.client.respond_server_request = response
                runtime._p7c6_continuation_counted = True
            return runtime

        manager.acquire = counted_acquire
        runtime = await manager.acquire(PROFILE_ID)
        manifest = manager._installed_manifest
        if manifest is None or manifest.codex_cli_version != SUPPORTED_CODEX_VERSION or manifest.schema_sha256 != SCHEMA_SHA256:
            raise AssertionError("P7C6_CAPABILITY_MISMATCH")
        catalog_adapter = CodexModelCatalogAdapter(manager)
        catalog = await catalog_adapter.get_catalog(PROFILE_ID)
        defaults = tuple(model for model in catalog.models if not model.hidden and model.is_default)
        if len(defaults) != 1:
            raise AssertionError("P7C6_MODEL_DEFAULT_AMBIGUOUS")
        model = defaults[0]
        pinned_catalog = _PinnedCatalog(manager, catalog_adapter, catalog)
        thread_lifecycle = CodexThreadLifecycleAdapter(manager, pinned_catalog)
        turn_lifecycle = CodexTurnLifecycleAdapter(manager, pinned_catalog)
        retained_binding = ThreadBinding(PROFILE_ID, retained_thread_id)
        resume = await thread_lifecycle.resume(binding=retained_binding, working_directory=TrustedWorkingDirectory(str(run_root)))
        if resume.status is not ThreadOperationStatus.RESUME_CONFIRMED or resume.binding is not retained_binding:
            raise AssertionError("P7C6_RESUME_NOT_CONFIRMED")

        workdir = run_root / "continuation-workdir"
        workdir.mkdir(mode=0o700)
        sentinel = run_root / "continuation-sentinel"
        if sentinel.exists():
            raise AssertionError("P7C6_CONTINUATION_SENTINEL_COLLISION")
        allow_marker = f"C6_CONT_ALLOW_{secrets.token_hex(24)}"
        prompt_marker = f"C6_CONT_T4_PROMPT_{secrets.token_hex(24)}"
        interrupt_marker = f"C6_CONT_T5_INTERRUPT_{secrets.token_hex(24)}"
        markers = (*run1_markers.values(), allow_marker, prompt_marker, interrupt_marker)
        supplement = run_root / "p7c6-continuation-marker-recovery-supplement.json"
        continuation_record = {
            "format": 1,
            "status": "CONTINUATION_MARKERS_PERSISTED_ROOT_ONLY",
            "thread_id_sha256": RUN1_THREAD_SHA256,
            "allow_marker": allow_marker,
            "turn4_prompt_marker": prompt_marker,
            "turn5_interrupt_marker": interrupt_marker,
            "allow_marker_sha256": _sha256(allow_marker),
            "turn4_prompt_marker_sha256": _sha256(prompt_marker),
            "turn5_interrupt_marker_sha256": _sha256(interrupt_marker),
        }
        payload = (json.dumps(continuation_record, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(str(supplement), flags, 0o600)
        try:
            if os.write(fd, payload) != len(payload):
                raise AssertionError("P7C6_CONTINUATION_SUPPLEMENT_SHORT_WRITE")
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_parent(supplement)

        turn4_id = asyncio.get_running_loop().create_future()
        inner = f"printf {allow_marker} > {sentinel}"
        operator = _StructuralApprovalOperator(
            thread_id=retained_thread_id, turn_id=turn4_id, cwd=str(workdir), inner=inner,
            marker=allow_marker, sentinel=str(sentinel),
        )
        bridge = CodexApprovalBridge(profile_id=PROFILE_ID, client=runtime.client, operator=operator)
        approval_task = asyncio.create_task(bridge.handle_next())
        turn4 = await turn_lifecycle.start_turn(
            thread_binding=retained_binding, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            user_text=f"Execute exactly this operation once and no additional operation: {inner}. Prompt marker: {prompt_marker}.",
            working_directory=TrustedWorkingDirectory(str(workdir)),
        )
        if turn4.status is not TurnStartStatus.CONFIRMED or turn4.binding is None:
            raise AssertionError("P7C6_TURN4_START_NOT_CONFIRMED")
        turn4_id.set_result(turn4.binding.turn_id)
        approval = await asyncio.wait_for(asyncio.shield(approval_task), timeout=90)
        if approval.status is not ApprovalHandlingStatus.ALLOWED or operator.allow_count != 1 or len(operator.requests) != 1 or approval_responses != 1:
            raise AssertionError("P7C6_TURN4_APPROVAL_NOT_EXACTLY_ALLOWED")
        terminal4 = await turn_lifecycle.wait_turn(turn4.binding)
        if terminal4.status is not TurnTerminalStatus.COMPLETED or sentinel.read_bytes() != allow_marker.encode("utf-8"):
            raise AssertionError("P7C6_TURN4_NOT_DEFINITIVE")
        sentinel.unlink()

        turn5 = await turn_lifecycle.start_turn(
            thread_binding=retained_binding, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            user_text=f"Execute exactly `sleep 120` and no additional operation. Interrupt marker: {interrupt_marker}.",
            working_directory=TrustedWorkingDirectory(str(workdir)),
        )
        if turn5.status is not TurnStartStatus.CONFIRMED or turn5.binding is None:
            raise AssertionError("P7C6_TURN5_START_NOT_CONFIRMED")
        terminal5_task = asyncio.create_task(turn_lifecycle.wait_turn(turn5.binding))
        try:
            terminal5 = await asyncio.wait_for(asyncio.shield(terminal5_task), timeout=5)
        except asyncio.TimeoutError:
            interrupt = await turn_lifecycle.interrupt_turn(turn5.binding)
            if interrupt.status not in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED) or interrupt.terminal_result is None or interrupt.terminal_result.status is not TurnTerminalStatus.FAILED:
                raise AssertionError("P7C6_TURN5_INTERRUPT_NOT_DEFINITIVE")
            terminal5 = await asyncio.shield(terminal5_task)
        else:
            raise AssertionError("P7C6_TURN5_TERMINAL_BEFORE_INTERRUPT")
        if approval_responses != 1 or terminal5.status is not TurnTerminalStatus.FAILED:
            raise AssertionError("P7C6_TURN5_APPROVAL_OR_TERMINAL_BOUNDARY_INVALID")
        await manager.shutdown_all()
        if _boundary_users((state_root, state_root / "sqlite", state_root / "logs", controller_db, workdir)):
            raise AssertionError("P7C6_CONTINUATION_BOUNDARY_EXTERNAL_USERS")
        predelete_scanner = PersistentProfileResidualScanner(authority)
        predelete = predelete_scanner.scan(profile, retained_thread_id)
        predelete_oracle = _marker_oracle(profile, retained_thread_id, markers)
        if predelete.scan_errors or predelete.limit_exceeded or (predelete.match_count == 0 and not predelete_oracle["thread_count"] and not predelete_oracle["marker_count"]):
            raise AssertionError("P7C6_PREDELETE_OBSERVATION_INCONCLUSIVE")

        storage = await SqliteStorage.open(str(controller_db))
        if SCHEMA_VERSION != 4:
            raise AssertionError("P7C6_CONTROLLER_SCHEMA_NOT_V4")
        dialogues = DialogueRepository(storage, now_ms=lambda: 4000)
        await dialogues.create_intent(dialogue_id="p7c6-retained-dialogue", server_id=SERVER_ID, profile_id=PROFILE_ID)
        created = await dialogues.confirm_created(dialogue_id="p7c6-retained-dialogue", expected_version=0, thread_id=retained_thread_id)
        cleanup = DeleteStorageCleanupCoordinator(storage, manager, scanner=predelete_scanner, now_ms=lambda: 5000)
        delete_service = DialogueDeleteService(storage, server_id=SERVER_ID, thread_lifecycle=thread_lifecycle, local_cleanup=cleanup, now_ms=lambda: 5000)
        deleted = await delete_service.delete(DialogueDeleteRequest(created.dialogue_id, created.version))
        if deleted.status is not DialogueDeleteStatus.DELETED or deleted.tombstone is None or counters.get("thread/delete", 0) != 1:
            raise AssertionError("P7C6_DELETE_NOT_EXACTLY_CONFIRMED")
        await manager.shutdown_all()
        postdelete = predelete_scanner.scan(profile, retained_thread_id)
        postdelete_oracle = _marker_oracle(profile, retained_thread_id, markers)
        if postdelete.match_count or postdelete.scan_errors or postdelete.limit_exceeded or postdelete_oracle["thread_count"] or postdelete_oracle["marker_count"] or postdelete_oracle["scan_errors"]:
            raise AssertionError("P7C6_POSTDELETE_RESIDUAL")
        if any((state_root / child).exists() and any((state_root / child).iterdir()) for child in ("sqlite", "logs")):
            raise AssertionError("P7C6_POSTDELETE_ISOLATED_RESIDUAL")
        if workdir.exists():
            workdir.rmdir()
        read_continuation_latch(latch_path, latch)
        return {
            "official_p1_delete_status": "DELETE_CONFIRMED",
            "application_delete_status": deleted.status.value,
            "approval_handling_status": approval.status.value,
            "approval_responses": approval_responses,
            "thread_resume_calls": counters.get("thread/resume", 0),
            "turn_start_calls": counters.get("turn/start", 0),
            "interrupt_calls": counters.get("turn/interrupt", 0),
            "thread_delete_calls": counters.get("thread/delete", 0),
        }
    finally:
        if manager is not None:
            await manager.shutdown_all()
        if storage is not None:
            await storage.close()
        if sentinel is not None and sentinel.exists():
            sentinel.unlink()
        if workdir is not None and workdir.exists():
            workdir.rmdir()


class StructuralMatcherOfflineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thread = "retained-thread"
        self.turn = "turn-4"
        self.cwd = "/run/codexcontrol/continuation-workdir"
        self.marker = "C6_CONT_ALLOW_" + "a" * 48
        self.sentinel = "/run/codexcontrol/continuation-sentinel"
        self.inner = f"printf {self.marker} > {self.sentinel}"

    def assert_allow(self, command: str) -> None:
        result = match_structural_approval(
            [_request(command, thread=self.thread, turn=self.turn, cwd=self.cwd)],
            expected_thread_id=self.thread, expected_turn_id=self.turn, expected_cwd=self.cwd,
            expected_inner_command=self.inner, expected_marker=self.marker, expected_sentinel=self.sentinel,
        )
        self.assertTrue(result.allowed, result)
        self.assertIn(result.grammar, ("EXACT_INNER", "ONE_SHELL_WRAPPER"))
        self.assertEqual(result.mismatch_flags, ())

    def assert_deny(self, request: ApprovalRequest | Sequence[ApprovalRequest]) -> None:
        requests = [request] if isinstance(request, ApprovalRequest) else request
        result = match_structural_approval(
            requests, expected_thread_id=self.thread, expected_turn_id=self.turn, expected_cwd=self.cwd,
            expected_inner_command=self.inner, expected_marker=self.marker, expected_sentinel=self.sentinel,
        )
        self.assertFalse(result.allowed, result)
        self.assertTrue(result.mismatch_flags)

    def test_allow_matrix_exact_inner_and_all_approved_wrappers(self) -> None:
        self.assert_allow(self.inner)
        for executable in sorted(WRAPPERS):
            for option in sorted(WRAPPER_OPTIONS):
                self.assert_allow(f"{executable} {option} {shlex.quote(self.inner)}")
        self.assertEqual(1 + len(WRAPPERS) * len(WRAPPER_OPTIONS), 13)

    def test_deny_matrix_identity_kind_count_and_grammar(self) -> None:
        cases = (
            _request(self.inner, thread="wrong-thread"),
            _request(self.inner, thread=None),
            _request(self.inner, turn="wrong-turn"),
            _request(self.inner, turn=None),
            _request(self.inner, cwd="/wrong"),
            _request(self.inner.replace(self.marker, "C6_CONT_ALLOW_" + "b" * 48)),
            _request(self.inner.replace(self.sentinel, "/wrong/sentinel")),
            _request(self.inner, kind=ApprovalKind.EXEC_COMMAND),
            (_request(self.inner), _request(self.inner)),
            _request("echo prefix && " + self.inner),
            _request(self.inner + " && echo suffix"),
            _request("sh -c " + shlex.quote("sh -c " + shlex.quote(self.inner))),
            _request("sh -c " + shlex.quote(self.inner) + " | cat"),
            _request(self.inner + "; echo extra"),
            _request(self.inner.replace("printf", "printfX")),
            _request("sh -c 'unterminated"),
            _request("env " + self.inner),
            _request(self.inner + " > /tmp/extra"),
        )
        for case in cases:
            self.assert_deny(case)
        self.assertEqual(len(cases), 18)


class ContinuationLatchOfflineTests(unittest.TestCase):
    def test_atomic_create_existing_symlink_mode_and_post_dispatch_retention(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-latch-") as directory:
            parent = Path(directory)
            path = parent / "continuation-ledger.json"
            expected = create_continuation_latch(
                path, source_prep_commit="a" * 40, retained_thread_sha256="b" * 64,
                continuation_identity="RETAINED_THREAD_T4_T5_DELETE",
            )
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(read_continuation_latch(path, expected), expected)
            with self.assertRaises(ContinuationLatchExists):
                create_continuation_latch(path, source_prep_commit="a" * 40, retained_thread_sha256="b" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")
            retained = path.read_bytes()
            with self.assertRaises(ContinuationLatchError):
                raise ContinuationLatchError("simulated_post_dispatch_failure")
            self.assertEqual(path.read_bytes(), retained)

            symlink = parent / "symlink.json"
            symlink.symlink_to(path)
            with self.assertRaises(ContinuationLatchExists):
                create_continuation_latch(symlink, source_prep_commit="a" * 40, retained_thread_sha256="b" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")

    def test_wrong_mode_and_content_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-latch-") as directory:
            path = Path(directory) / "continuation-ledger.json"
            expected = create_continuation_latch(path, source_prep_commit="a" * 40, retained_thread_sha256="b" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")
            path.chmod(0o644)
            with self.assertRaises(ContinuationLatchError):
                read_continuation_latch(path, expected)


class ContinuationStaticGateTests(unittest.TestCase):
    def test_no_new_thread_path_and_real_gate_is_disabled(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "start":
                owner = node.func.value
                self.assertFalse(isinstance(owner, ast.Name) and owner.id == "CodexThreadLifecycleAdapter")
        self.assertNotIn("thread/" + "start", source)
        self.assertNotEqual(os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION"), AUTHORIZATION)
        self.assertEqual("NO", "NO")


class P7C6SameThreadContinuationAcceptance(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(
        os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION") == AUTHORIZATION,
        "gated real P7.C6 same-thread continuation",
    )
    async def test_real_same_thread_continuation(self) -> None:
        report = await _run_real_continuation()
        print("P7C6_CONTINUATION_SANITIZED_REPORT=" + json.dumps(report, sort_keys=True))
