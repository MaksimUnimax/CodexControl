"""P7.C6 same-thread continuation prep-v2 repair.

The real test is deliberately gated by a distinct, future operator token.  No
ordinary test command can acquire a runtime, and this module contains no
thread creation path.  All helpers below are acceptance-only harness code;
production scanners and lifecycle code are not changed by this repair.
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
import signal
import stat
import subprocess
import sys
import time
import tempfile
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from unittest import mock

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
    ApprovalHandlingStatus,
    ApprovalKind,
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
from codex_control.storage import DeletionRepository, DialogueRepository, SqliteStorage


AUTHORIZATION = "AUTHORIZED_RETAINED_THREAD_T4_T5_DELETE_2026_09_10"
EXPECTED_HEAD_ENV = "CODEXCONTROL_P7C6_CONTINUATION_EXPECTED_HEAD"
EXPECTED_TREE_ENV = "CODEXCONTROL_P7C6_CONTINUATION_EXPECTED_TREE"
EXPECTED_REPOSITORY = "/opt/codex-control"
ARCHITECT_BASE_SHA = "e7368c68c37ac9499440f3d9d5856496414d0638"
ARCHITECT_BASE_TREE = "07548cf44840b7892198d8d149b7c42a178f2920"
REVIEWED_CANDIDATE = "2b38969c1c9a8232cb1c68efc953dae125e0e18c"
PROFILE_ID = "server-80-codexcontrol"
SERVER_ID = "server-80"
PERSISTENT_HOME = "/root/.codex_second"
EXECUTABLE = "/usr/local/bin/codex"
RUN1_LATCH = Path("/root/.codexcontrol/p7c6-real-one-shot-ledger.json")
RUN1_THREAD_SHA256 = "9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6"
RUN1_LATCH_SHA256 = "50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e"
CONTINUATION_LATCH = Path("/root/.codexcontrol/p7c6-same-thread-continuation-ledger.json")
MARKER_RE = {
    "response_marker": re.compile(r"C6_RESPONSE_[0-9a-f]{48}"),
    "memory_marker": re.compile(r"C6_MEMORY_[0-9a-f]{48}"),
    "interrupt_marker": re.compile(r"C6_INTERRUPT_[0-9a-f]{48}"),
}
WRAPPERS = frozenset(("sh", "/bin/sh", "/usr/bin/sh", "bash", "/bin/bash", "/usr/bin/bash"))
WRAPPER_OPTIONS = frozenset(("-c", "-lc"))
ORACLE_MAX_FILES = 10_000
ORACLE_MAX_FILE_BYTES = 16 * 1024 * 1024
ORACLE_MAX_BYTES = 64 * 1024 * 1024
ORACLE_CHUNK_BYTES = 64 * 1024
WATCHDOG_HARD_DEADLINE = 5.0
WATCHDOG_TERMINATE_GRACE = 1.0
WATCHDOG_KILL_GRACE = 1.0


class ContinuationLatchError(Exception):
    """Finite fail-closed latch/journal error."""


class ContinuationLatchExists(ContinuationLatchError):
    pass


class SourceAuthorityError(AssertionError):
    pass


class BoundaryPreflightError(AssertionError):
    pass


class OracleError(AssertionError):
    pass


class BudgetError(AssertionError):
    pass


class SanitizationError(AssertionError):
    pass


class TaskNonconvergedError(TimeoutError):
    """A finite owner stopped observing a task without a terminal state."""

    def __init__(self, owner: "OwnedTask") -> None:
        self.owner = owner
        super().__init__(f"{owner.name}: FINAL_NONCONVERGENCE")


@dataclass
class OwnedTask:
    task: asyncio.Task[Any]
    name: str
    phase: str = "PRIMARY_WAIT"
    terminalized: bool = False
    nonconverged: bool = False

    def done(self) -> bool:
        return self.task.done()


def _create_owned_task(awaitable: Any, name: str) -> OwnedTask:
    return OwnedTask(asyncio.create_task(awaitable), name)


def _as_owned_task(value: OwnedTask | asyncio.Task[Any], name: str = "owned-task") -> OwnedTask:
    return value if isinstance(value, OwnedTask) else OwnedTask(value, name)


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def _private_regular(path: Path, mode: int) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(value.st_mode)
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
    return (
        stat.S_ISDIR(value.st_mode)
        and value.st_uid == 0
        and value.st_gid == 0
        and stat.S_IMODE(value.st_mode) == mode
    )


def _fsync_parent(path: Path) -> None:
    fd = os.open(str(path.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_all(fd: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(fd, payload[offset:])
        if written <= 0:
            raise ContinuationLatchError("short_write")
        offset += written


def _read_private_json(path: Path, *, max_bytes: int = 256 * 1024) -> dict[str, Any]:
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("private_record_authority_invalid")
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    try:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, min(64 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ContinuationLatchError("record_limit_exceeded")
            chunks.append(chunk)
    finally:
        os.close(fd)
    try:
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContinuationLatchError("record_content_invalid") from error
    if not isinstance(value, dict):
        raise ContinuationLatchError("record_content_invalid")
    return value


def _hash_bounded_private_file(path: Path, *, max_bytes: int = 256 * 1024) -> str:
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("private_record_authority_invalid")
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    digest = hashlib.sha256()
    total = 0
    try:
        before = os.fstat(fd)
        while True:
            chunk = os.read(fd, min(64 * 1024, max_bytes - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ContinuationLatchError("record_limit_exceeded")
            digest.update(chunk)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise ContinuationLatchError("record_identity_changed")
    finally:
        os.close(fd)
    return digest.hexdigest()


def _safe_record(*, source_sha: str, source_tree: str, thread_sha: str, identity: str, status: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or not re.fullmatch(r"[0-9a-f]{40}", source_tree):
        raise ContinuationLatchError("source_authority_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", thread_sha):
        raise ContinuationLatchError("thread_hash_invalid")
    if not re.fullmatch(r"[A-Z0-9_]{1,96}", identity) or not re.fullmatch(r"[A-Z0-9_]{1,96}", status):
        raise ContinuationLatchError("record_enum_invalid")
    return {
        "format": 2,
        "status": status,
        "accepted_harness_sha": source_sha,
        "accepted_harness_tree": source_tree,
        "retained_thread_sha256": thread_sha,
        "continuation_identity": identity,
    }


def create_continuation_latch(
    path: Path, *, accepted_harness_sha: str, accepted_harness_tree: str,
    retained_thread_sha256: str, continuation_identity: str,
) -> dict[str, Any]:
    """Create the exclusive replay barrier before the first continuation RPC."""
    if not _private_directory(path.parent, 0o700):
        raise ContinuationLatchError("parent_authority_invalid")
    record = _safe_record(
        source_sha=accepted_harness_sha, source_tree=accepted_harness_tree,
        thread_sha=retained_thread_sha256, identity=continuation_identity,
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
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_parent(path)
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("created_authority_invalid")
    return record


def read_continuation_latch(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    record = _read_private_json(path)
    if record != expected:
        raise ContinuationLatchError("latch_content_mismatch")
    return record


def _atomic_replace_json(path: Path, record: Mapping[str, Any]) -> None:
    if not _private_directory(path.parent, 0o700):
        raise ContinuationLatchError("record_parent_invalid")
    if path.exists() and not _private_regular(path, 0o600):
        raise ContinuationLatchError("record_authority_invalid")
    payload = (json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    temporary = path.parent / (f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(temporary), flags, 0o600)
    try:
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(str(temporary), str(path))
        _fsync_parent(path)
    except Exception:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise
    if not _private_regular(path, 0o600):
        raise ContinuationLatchError("record_authority_invalid")


class ContinuationRecoveryJournal:
    """Root-only crash-safe finite progress record."""

    def __init__(self, path: Path, record: dict[str, Any]) -> None:
        self.path = path
        self.record = dict(record)

    @classmethod
    def create(cls, path: Path, record: Mapping[str, Any]) -> "ContinuationRecoveryJournal":
        if not _private_directory(path.parent, 0o700):
            raise ContinuationLatchError("journal_parent_invalid")
        payload = (json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(str(path), flags, 0o600)
        except FileExistsError as error:
            raise ContinuationLatchExists("journal_already_exists") from error
        try:
            _write_all(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        _fsync_parent(path)
        if not _private_regular(path, 0o600):
            raise ContinuationLatchError("journal_authority_invalid")
        return cls(path, dict(record))

    def update(self, **fields: Any) -> None:
        self.record.update(fields)
        _atomic_replace_json(self.path, self.record)


def sanitize_success_records(records: Mapping[Path, Mapping[str, Any]]) -> None:
    """Sanitize all retained recovery records only after the final PASS gate."""
    try:
        for path, record in records.items():
            _atomic_replace_json(path, record)
    except Exception as error:
        raise SanitizationError("LOCAL_RECOVERY_SANITIZATION_FAILED") from error


def sanitize_only_after_final_gates(gates_pass: bool, records: Mapping[Path, Mapping[str, Any]]) -> None:
    if gates_pass is not True:
        raise SanitizationError("SANITIZATION_GATES_NOT_CONFIRMED")
    sanitize_success_records(records)


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
    """Allow only the exact inner command or one exact shell wrapper."""
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
        self._thread_id, self._turn_id, self._cwd = thread_id, turn_id, cwd
        self._inner, self._marker, self._sentinel = inner, marker, sentinel
        self.requests: list[ApprovalRequest] = []
        self.results: list[StructuralApprovalResult] = []
        self.allow_count = 0

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        await self._turn_id
        self.requests.append(request)
        result = match_structural_approval(
            self.requests, expected_thread_id=self._thread_id, expected_turn_id=self._turn_id.result(),
            expected_cwd=self._cwd, expected_inner_command=self._inner,
            expected_marker=self._marker, expected_sentinel=self._sentinel,
        )
        self.results.append(result)
        if result.allowed:
            self.allow_count += 1
            return ApprovalDecision.ALLOW
        return ApprovalDecision.DENY


def _request(command: str, *, thread: str = "thread", turn: str = "turn", cwd: str = "/run", kind: ApprovalKind = ApprovalKind.COMMAND_EXECUTION) -> ApprovalRequest:
    return ApprovalRequest(1, PROFILE_ID, "wire", kind, thread, turn, "item", (f"cwd: {cwd}", f"command: {command}"))


def _validate_run1_latch() -> None:
    if not _private_directory(RUN1_LATCH.parent, 0o700) or not _private_regular(RUN1_LATCH, 0o600):
        raise AssertionError("P7C6_ACCEPTED_RUN1_LATCH_DRIFT")
    if _hash_bounded_private_file(RUN1_LATCH) != RUN1_LATCH_SHA256:
        raise AssertionError("P7C6_ACCEPTED_RUN1_LATCH_DRIFT")


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
                record = _read_private_json(path)
                thread_id = record.get("thread_id")
                if record.get("profile_id") == PROFILE_ID and isinstance(thread_id, str) and _sha256(thread_id) == RUN1_THREAD_SHA256:
                    candidates.append((path, thread_id))
            except (OSError, ContinuationLatchError):
                continue
    if len(candidates) != 1:
        raise AssertionError("P7C6_RECOVERY_LEDGER_AMBIGUOUS")
    ledger, thread_id = candidates[0]
    supplement = ledger.parent / "p7c6-marker-recovery-supplement.json"
    values = _read_private_json(supplement)
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


def _git_value(repository: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(repository), check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH") from None
    return result.stdout.strip()


def validate_source_authority(
    *, repository: Path = Path(EXPECTED_REPOSITORY), expected_head: str | None = None,
    expected_tree: str | None = None,
) -> dict[str, str]:
    """Prove accepted HEAD/tree/clean path before latch or runtime acquire."""
    head = expected_head if expected_head is not None else os.environ.get(EXPECTED_HEAD_ENV)
    tree = expected_tree if expected_tree is not None else os.environ.get(EXPECTED_TREE_ENV)
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH")
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH")
    try:
        if repository.resolve(strict=True) != Path(EXPECTED_REPOSITORY).resolve(strict=True):
            raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH")
    except OSError:
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH") from None
    if _git_value(repository, "rev-parse", "HEAD") != head or _git_value(repository, "rev-parse", "HEAD^{tree}") != tree:
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH")
    if _git_value(repository, "status", "--porcelain", "--untracked-files=all"):
        raise SourceAuthorityError("P7C6_CONTINUATION_SOURCE_AUTHORITY_MISMATCH")
    return {"accepted_harness_sha": head, "accepted_harness_tree": tree}


def _decode_mount_field(value: str) -> str:
    return value.replace("\\040", " ").replace("\\011", "\t").replace("\\012", "\n").replace("\\134", "\\")


def _mount_points(mountinfo: str) -> set[str]:
    points: set[str] = set()
    for line in mountinfo.splitlines():
        fields = line.split(" - ", 1)[0].split()
        if len(fields) >= 5:
            points.add(os.path.normpath(_decode_mount_field(fields[4])))
    return points


def _path_metadata(path: Path, *, must_exist: bool = True) -> tuple[int, int] | None:
    current = path if path.is_absolute() else Path(os.path.abspath(path))
    missing = False
    parts = current.parts
    cursor = Path(parts[0])
    for part in parts[1:]:
        cursor /= part
        try:
            value = cursor.lstat()
        except FileNotFoundError:
            missing = True
            if must_exist and cursor == current:
                raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
            continue
        except OSError:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED") from None
        if missing:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
        if stat.S_ISLNK(value.st_mode) or value.st_uid != 0 or value.st_gid != 0:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
        if stat.S_ISDIR(value.st_mode):
            if cursor == current and stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
        elif cursor == current:
            if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1 or stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
            return value.st_dev, value.st_ino
        else:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    if missing:
        if must_exist:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
        return None
    try:
        value = current.lstat()
    except OSError:
        raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED") from None
    if stat.S_ISLNK(value.st_mode) or value.st_uid != 0 or value.st_gid != 0:
        raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    if stat.S_ISDIR(value.st_mode) and stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    return value.st_dev, value.st_ino


def _path_under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _preflight_absent_path(path: Path) -> None:
    """Prove a future local path has a safe, non-symlink parent and is absent."""
    absolute = Path(os.path.abspath(os.fspath(path)))
    cursor = Path(absolute.parts[0])
    for component in absolute.parts[1:]:
        cursor /= component
        try:
            value = cursor.lstat()
        except FileNotFoundError:
            if cursor != absolute:
                raise BoundaryPreflightError("P7C6_LOCAL_PARENT_ABSENT")
            return
        except OSError as error:
            raise BoundaryPreflightError("P7C6_LOCAL_PATH_UNREADABLE") from error
        if stat.S_ISLNK(value.st_mode) or value.st_uid != 0 or value.st_gid != 0:
            raise BoundaryPreflightError("P7C6_LOCAL_PATH_UNSAFE")
        if cursor == absolute:
            raise BoundaryPreflightError("P7C6_LOCAL_PATH_COLLISION")
        if not stat.S_ISDIR(value.st_mode):
            raise BoundaryPreflightError("P7C6_LOCAL_PARENT_UNSAFE")
        if cursor == absolute.parent and stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
            raise BoundaryPreflightError("P7C6_LOCAL_PARENT_UNSAFE")


def preflight_local_continuation_paths(paths: Mapping[str, Path]) -> dict[str, Any]:
    """Preflight every local continuation artifact before latch/RPC authority."""
    normalized = {name: Path(os.path.abspath(os.fspath(path))) for name, path in paths.items()}
    for path in normalized.values():
        _preflight_absent_path(path)
    names = tuple(normalized)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            left, right = normalized[left_name], normalized[right_name]
            if _path_under(left, right) or _path_under(right, left):
                raise BoundaryPreflightError("P7C6_LOCAL_PATH_OVERLAP")
    return {"paths": tuple(sorted(normalized)), "status": "PASS"}


def _process_users(targets: Mapping[str, Path]) -> dict[str, int]:
    users = {name: set() for name in targets}
    for pid_name in os.listdir("/proc"):
        if not pid_name.isdigit() or int(pid_name) == os.getpid():
            continue
        proc = Path("/proc") / pid_name
        values: list[Path] = []
        try:
            values.append(Path(os.readlink(proc / "cwd")))
        except OSError:
            pass
        try:
            environ_fd = os.open(str(proc / "environ"), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                environ_bytes = os.read(environ_fd, 256 * 1024)
            finally:
                os.close(environ_fd)
            for variable in environ_bytes.split(b"\0"):
                if variable.startswith(b"CODEX_SQLITE_HOME="):
                    values.append(Path(variable.split(b"=", 1)[1].decode("utf-8", "strict")))
        except (OSError, UnicodeError):
            pass
        try:
            for fd_name in os.listdir(proc / "fd"):
                try:
                    values.append(Path(os.readlink(proc / "fd" / fd_name)))
                except OSError:
                    pass
        except OSError:
            pass
        for name, target in targets.items():
            if any(value == target or _path_under(value, target) for value in values):
                users[name].add(int(pid_name))
    return {name: len(pids) for name, pids in users.items()}


def _continuation_owned_processes(workdir: Path) -> int:
    """Read-only bounded forensic for a delayed command owned by this run."""
    found = 0
    for pid_name in os.listdir("/proc"):
        if not pid_name.isdigit() or int(pid_name) == os.getpid():
            continue
        proc = Path("/proc") / pid_name
        try:
            cwd = Path(os.readlink(proc / "cwd"))
            if not (cwd == workdir or _path_under(cwd, workdir)):
                continue
            fd = os.open(str(proc / "cmdline"), os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                command_line = os.read(fd, 4096)
            finally:
                os.close(fd)
            if b"sleep\x00120" in command_line or b"sleep 120" in command_line:
                found += 1
        except (OSError, UnicodeError):
            continue
    return found


def preflight_protected_boundaries(
    boundaries: Mapping[str, Path], *, allowed_nested: Iterable[tuple[str, str]] = (),
    mountinfo: str | None = None, external_users: Mapping[str, int] | None = None,
    externally_owned: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Fresh read-only mount, component, identity and external-user proof."""
    # Keep the lexical path so lstat can see a symlink component; resolving
    # here would turn an alias fixture into its target before it is checked.
    normalized = {name: Path(os.path.abspath(os.fspath(path))) for name, path in boundaries.items()}
    allowed = set(allowed_nested)
    identities: dict[str, tuple[int, int] | None] = {}
    for name, path in normalized.items():
        identities[name] = _path_metadata(path, must_exist=path.exists())
    names = tuple(normalized)
    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            left, right = normalized[left_name], normalized[right_name]
            if _path_under(left, right) or _path_under(right, left):
                if (left_name, right_name) not in allowed and (right_name, left_name) not in allowed:
                    raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
            elif identities[left_name] is not None and identities[left_name] == identities[right_name]:
                raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    points = _mount_points(mountinfo if mountinfo is not None else Path("/proc/self/mountinfo").read_text(encoding="utf-8"))
    if any(str(path) in points for path in normalized.values()):
        raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    users = dict(external_users) if external_users is not None else _process_users(normalized)
    shared = {"persistent_home_shared", "repository"}
    owned = set(externally_owned) if externally_owned is not None else set(normalized) - shared
    for name, count in users.items():
        if name in owned and count:
            raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    return {"mount_alias": "PASS", "external_users": users}


def _walk_regular_files(root: Path, *, max_files: int) -> tuple[list[Path], int, bool]:
    files: list[Path] = []
    errors = 0
    limited = False
    try:
        root_stat = root.lstat()
    except FileNotFoundError:
        return files, errors, limited
    except OSError:
        return files, 1, limited
    if stat.S_ISLNK(root_stat.st_mode):
        return files, 1, limited
    if stat.S_ISREG(root_stat.st_mode):
        return [root], 0, limited
    if not stat.S_ISDIR(root_stat.st_mode):
        return files, 1, limited
    if root_stat.st_uid != 0 or root_stat.st_gid != 0 or stat.S_IMODE(root_stat.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
        return files, 1, limited
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
                value = entry.stat(follow_symlinks=False)
                path = Path(entry.path)
                if stat.S_ISLNK(value.st_mode):
                    errors += 1
                elif stat.S_ISDIR(value.st_mode):
                    if value.st_uid != 0 or value.st_gid != 0 or stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                        errors += 1
                    else:
                        pending.append(path)
                elif stat.S_ISREG(value.st_mode):
                    if len(files) >= max_files:
                        return files, errors, True
                    files.append(path)
                else:
                    errors += 1
            except OSError:
                errors += 1
    return files, errors, limited


def _count_chunked(chunks: Iterable[bytes], needles: Sequence[bytes]) -> tuple[int, ...]:
    counts = [0] * len(needles)
    carry = b""
    width = max((len(needle) for needle in needles), default=1)
    for chunk in chunks:
        combined = carry + chunk
        boundary = len(carry)
        for index, needle in enumerate(needles):
            start = 0
            while True:
                position = combined.find(needle, start)
                if position < 0:
                    break
                if position + len(needle) > boundary:
                    counts[index] += 1
                start = position + 1
        carry = combined[-(width - 1):] if width > 1 else b""
    return tuple(counts)


@dataclass(frozen=True)
class DescriptorScan:
    counts: tuple[int, ...]
    scan_errors: int
    limited: bool
    bytes_read: int
    identity: tuple[int, int] | None


def _safe_regular_metadata(value: os.stat_result) -> bool:
    return (
        stat.S_ISREG(value.st_mode)
        and value.st_uid == 0
        and value.st_gid == 0
        and value.st_nlink == 1
        and not stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _safe_path_components(root: Path, path: Path) -> bool:
    """Require every existing pathname component up to the file to be safe."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    cursor = root
    try:
        root_value = cursor.lstat()
        if not stat.S_ISDIR(root_value.st_mode) or root_value.st_uid != 0 or root_value.st_gid != 0 or stat.S_IMODE(root_value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
            return False
        for component in relative.parts[:-1]:
            cursor /= component
            value = cursor.lstat()
            if not stat.S_ISDIR(value.st_mode) or value.st_uid != 0 or value.st_gid != 0 or stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                return False
    except OSError:
        return False
    return True


def _scan_descriptor(
    path: Path, needles: Sequence[bytes], *, max_file_bytes: int, chunk_bytes: int,
    max_bytes: int | None = None,
) -> DescriptorScan:
    """Read one safe regular file and return the identity verified by that read."""
    empty = DescriptorScan((0,) * len(needles), 0, False, 0, None)
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
        return replace(empty, scan_errors=1)
    try:
        before = path.lstat()
        if not _safe_regular_metadata(before):
            return replace(empty, scan_errors=1)
        if before.st_size > max_file_bytes:
            return replace(empty, limited=True)
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        return replace(empty, scan_errors=1)
    chunks: list[bytes] = []
    total = 0
    error = False
    limited = False
    post_path = None
    try:
        opened = os.fstat(fd)
        identity = (before.st_dev, before.st_ino)
        metadata = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if metadata(opened) != metadata(before) or not _safe_regular_metadata(opened):
            return replace(empty, scan_errors=1)
        while True:
            try:
                remaining_file = max_file_bytes - total
                remaining_total = max_bytes - total if max_bytes is not None else remaining_file
                read_size = min(chunk_bytes, remaining_file, remaining_total)
                if read_size <= 0:
                    limited = True
                    break
                chunk = os.read(fd, read_size)
            except OSError:
                error = True
                break
            if not chunk:
                break
            total += len(chunk)
            chunks.append(chunk)
        after = os.fstat(fd)
        try:
            post_path = path.lstat()
        except OSError:
            error = True
        if metadata(after) != metadata(before) or post_path is None or metadata(post_path) != metadata(before) or (post_path.st_dev, post_path.st_ino) != identity:
            error = True
    except OSError:
        error = True
    finally:
        try:
            os.close(fd)
        except OSError:
            error = True
    return DescriptorScan(
        (0,) * len(needles) if error else _count_chunked(chunks, needles),
        1 if error else 0,
        limited,
        total,
        None if error else identity,
    )


def _marker_oracle(
    profile: CodexProfile, thread_id: str, markers: Sequence[str], *, max_files: int = ORACLE_MAX_FILES,
    max_file_bytes: int = ORACLE_MAX_FILE_BYTES, max_bytes: int = ORACLE_MAX_BYTES,
    chunk_bytes: int = ORACLE_CHUNK_BYTES,
) -> dict[str, int | bool]:
    """Bounded target-only oracle; all reads are descriptor/no-follow and chunked."""
    if any(type(value) is not int or value <= 0 for value in (max_files, max_file_bytes, max_bytes, chunk_bytes)):
        raise OracleError("LIMITS_INVALID")
    roots = (
        Path(profile.codex_home) / "sessions", Path(profile.codex_home) / "history.jsonl",
        Path(profile.isolated_state_root) / "sqlite", Path(profile.isolated_state_root) / "logs",
    )
    needles = tuple(value.encode("utf-8") for value in (thread_id, *markers))
    counts = [0] * len(needles)
    errors = 0
    files_scanned = 0
    bytes_scanned = 0
    limit_exceeded = False
    for root in roots:
        paths, walk_errors, walk_limit = _walk_regular_files(root, max_files=max_files - files_scanned)
        errors += walk_errors
        limit_exceeded = limit_exceeded or walk_limit
        for path in paths:
            if files_scanned >= max_files:
                limit_exceeded = True
                break
            try:
                size = path.lstat().st_size
            except OSError:
                errors += 1
                continue
            if bytes_scanned >= max_bytes:
                limit_exceeded = True
                break
            scan = _scan_descriptor(
                path, needles, max_file_bytes=max_file_bytes, chunk_bytes=chunk_bytes,
                max_bytes=max_bytes - bytes_scanned,
            )
            files_scanned += 1
            if scan.limited:
                limit_exceeded = True
            if scan.scan_errors:
                errors += scan.scan_errors
            bytes_scanned += scan.bytes_read
            for index, value in enumerate(scan.counts):
                counts[index] += value
        if limit_exceeded:
            break
    return {
        "thread_count": counts[0], "marker_count": sum(counts[1:]), "scan_errors": errors,
        "limit_exceeded": limit_exceeded, "files_scanned": files_scanned, "bytes_scanned": bytes_scanned,
    }


@dataclass(frozen=True)
class PersistentIdentity:
    relative_path: str
    category: str
    st_dev: int
    st_ino: int


@dataclass(frozen=True)
class UnrelatedBaseline:
    identities: tuple[PersistentIdentity, ...]
    scan_errors: int
    limit_exceeded: bool
    files_scanned: int = 0
    bytes_scanned: int = 0


def capture_unrelated_baseline(
    home: Path, retained_thread_id: str, *, max_files: int = ORACLE_MAX_FILES,
    max_file_bytes: int = ORACLE_MAX_FILE_BYTES, max_bytes: int = ORACLE_MAX_BYTES,
    chunk_bytes: int = ORACLE_CHUNK_BYTES,
) -> UnrelatedBaseline:
    """Capture only path category and device/inode, excluding target artifacts."""
    identities: list[PersistentIdentity] = []
    errors = 0
    limited = False
    bytes_scanned = 0
    files_scanned = 0
    roots = ((home / "sessions", "sessions"), (home / "history.jsonl", "history.jsonl"))
    target = (retained_thread_id.encode("utf-8"),)
    for root, category in roots:
        paths, walk_errors, walk_limit = _walk_regular_files(root, max_files=max_files - files_scanned)
        errors += walk_errors
        limited = limited or walk_limit
        for path in paths:
            if files_scanned >= max_files:
                limited = True
                break
            if bytes_scanned >= max_bytes:
                limited = True
                break
            scan = _scan_descriptor(
                path, target, max_file_bytes=max_file_bytes, chunk_bytes=chunk_bytes,
                max_bytes=max_bytes - bytes_scanned,
            )
            errors += scan.scan_errors
            limited = limited or scan.limited
            bytes_scanned += scan.bytes_read
            files_scanned += 1
            if scan.limited:
                break
            if scan.counts[0]:
                continue
            if scan.scan_errors or scan.identity is None:
                continue
            try:
                relative = path.relative_to(home).as_posix()
            except ValueError:
                errors += 1
                continue
            # The descriptor scanner's post-read pathname check already
            # proved that this is the same identity whose bytes were scanned.
            identities.append(PersistentIdentity(relative, category, *scan.identity))
        if limited:
            break
    return UnrelatedBaseline(tuple(identities), errors, limited, files_scanned, bytes_scanned)


def reconcile_unrelated_baseline(baseline: UnrelatedBaseline, home: Path) -> dict[str, Any]:
    current: set[tuple[str, str, int, int]] = set()
    paths, errors_a, limit_a = _walk_regular_files(home / "sessions", max_files=ORACLE_MAX_FILES)
    paths_b, errors_b, limit_b = _walk_regular_files(home / "history.jsonl", max_files=ORACLE_MAX_FILES - len(paths))
    for category, category_paths in (("sessions", paths), ("history.jsonl", paths_b)):
        for path in category_paths:
            try:
                value = path.lstat()
                if not _safe_path_components(home, path) or not _safe_regular_metadata(value):
                    continue
                current.add((path.relative_to(home).as_posix(), category, value.st_dev, value.st_ino))
            except (OSError, ValueError):
                errors_a += 1
    missing = tuple(
        identity for identity in baseline.identities
        if (identity.relative_path, identity.category, identity.st_dev, identity.st_ino) not in current
    )
    return {
        "preserved": not baseline.scan_errors and not baseline.limit_exceeded and not missing and not (errors_a + errors_b) and not (limit_a or limit_b),
        "missing": missing, "scan_errors": baseline.scan_errors + errors_a + errors_b,
        "limit_exceeded": baseline.limit_exceeded or limit_a or limit_b,
    }


async def validate_controller_state(storage: SqliteStorage, dialogue_id: str, controller_db: Path | None = None) -> dict[str, Any]:
    """Prove actual opened DB state through the storage read boundary."""
    actual_user_version = await storage.read(lambda connection: connection.execute("PRAGMA user_version").fetchone()[0])
    live = await DialogueRepository(storage).get_live()
    tombstone = await DeletionRepository(storage).get_tombstone(dialogue_id)
    conflicting_idempotency = await storage.read(
        lambda connection: connection.execute(
            "SELECT (SELECT COUNT(*) FROM callback_actions WHERE subject_id = ?) + "
            "(SELECT COUNT(*) FROM turn_jobs WHERE dialogue_id = ?) + "
            "(SELECT COUNT(*) FROM errors WHERE dialogue_id = ?)",
            (dialogue_id, dialogue_id, dialogue_id),
        ).fetchone()[0] > 0
    )
    path_authority = controller_db is None or bool(getattr(storage, "matches_database_path", lambda _path: False)(controller_db))
    return {
        "actual_user_version": actual_user_version,
        "preexisting_live_dialogue": live,
        "conflicting_tombstone": tombstone,
        "conflicting_idempotency": bool(conflicting_idempotency),
        "controller_path_authority": path_authority,
        "passed": actual_user_version == 4 and live is None and tombstone is None and not conflicting_idempotency and path_authority,
    }


REAL_BUDGET = {
    "model/list": 1, "thread/resume": 1, "turn/start": 2, "turn/interrupt": 1, "thread/delete": 1,
    "thread/start": 0, "thread/read": 0, "thread/list": 0,
}
ALLOWED_REQUEST_METHODS = frozenset(REAL_BUDGET)


def assert_dynamic_budget(counters: Mapping[str, int], approval_responses: int, *, model_list_reason: str | None = None) -> None:
    if set(counters) - ALLOWED_REQUEST_METHODS:
        raise BudgetError("UNEXPECTED_REQUEST_METHOD")
    for method, expected in REAL_BUDGET.items():
        if counters.get(method, 0) != expected:
            raise BudgetError(f"{method.upper().replace('/', '_')}_BUDGET")
    if approval_responses != 1:
        raise BudgetError("APPROVAL_RESPONSE_BUDGET")


def assert_no_reacquire(before: int, after: int) -> None:
    if type(before) is not int or type(after) is not int or after != before:
        raise BudgetError("RUNTIME_REACQUIRE_DURING_INTERRUPT")


class ObservingDeleteLifecycle:
    """Narrow observer preserving the exact lifecycle result and binding."""

    def __init__(self, underlying: Any) -> None:
        self.underlying = underlying
        self.call_count = 0
        self.status: ThreadOperationStatus | None = None
        self.result: Any = None

    async def delete(self, *, binding: ThreadBinding) -> Any:
        if self.call_count:
            raise AssertionError("P7C6_OFFICIAL_DELETE_RETRY")
        self.call_count += 1
        result = await self.underlying.delete(binding=binding)
        self.result = result
        self.status = result.status if type(getattr(result, "status", None)) is ThreadOperationStatus else None
        return result


def _isolated_payload_proof(state_root: Path) -> dict[str, int]:
    counts = {"sqlite": 0, "logs": 0, "errors": 0}
    for child in ("sqlite", "logs"):
        root = state_root / child
        try:
            root_value = root.lstat()
            if not stat.S_ISDIR(root_value.st_mode) or root_value.st_uid != 0 or stat.S_IMODE(root_value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                counts["errors"] += 1
                continue
        except OSError:
            counts["errors"] += 1
            continue
        pending = [root]
        descendants = 0
        while pending:
            directory = pending.pop()
            try:
                entries = list(os.scandir(directory))
            except OSError:
                counts["errors"] += 1
                continue
            for entry in entries:
                try:
                    value = entry.stat(follow_symlinks=False)
                    descendants += 1
                    if descendants > ORACLE_MAX_FILES:
                        counts["errors"] += 1
                        pending.clear()
                        break
                    if stat.S_ISLNK(value.st_mode) or value.st_uid != 0 or stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                        counts["errors"] += 1
                    elif stat.S_ISDIR(value.st_mode):
                        pending.append(Path(entry.path))
                    elif not stat.S_ISREG(value.st_mode):
                        counts["errors"] += 1
                except OSError:
                    counts["errors"] += 1
        counts[child] = descendants
    return {
        "POSTDELETE_SQLITE_PAYLOAD_DESCENDANTS": counts["sqlite"],
        "POSTDELETE_LOG_PAYLOAD_DESCENDANTS": counts["logs"],
        "POSTDELETE_ISOLATED_TRAVERSAL_ERRORS": counts["errors"],
    }


def _safe_exact_file(path: Path, expected: bytes) -> bool:
    """Prove exact sentinel bytes through one stable, no-follow descriptor read."""
    if len(expected) > ORACLE_MAX_FILE_BYTES:
        return False
    try:
        before = path.lstat()
        if not _safe_regular_metadata(before) or before.st_size != len(expected):
            return False
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
    except OSError:
        return False
    actual = bytearray()
    stable = True
    try:
        opened = os.fstat(fd)
        metadata = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid, value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if metadata(opened) != metadata(before) or not _safe_regular_metadata(opened):
            return False
        while len(actual) <= len(expected):
            chunk = os.read(fd, min(ORACLE_CHUNK_BYTES, len(expected) + 1 - len(actual)))
            if not chunk:
                break
            actual.extend(chunk)
        after = os.fstat(fd)
        try:
            post_path = path.lstat()
        except OSError:
            return False
        stable = (
            metadata(after) == metadata(before)
            and metadata(post_path) == metadata(before)
            and _safe_regular_metadata(post_path)
        )
    except OSError:
        return False
    finally:
        try:
            os.close(fd)
        except OSError:
            stable = False
    return (
        stable
        and before.st_size == len(expected)
        and len(actual) == len(expected)
        and bytes(actual) == expected
    )


class _PinnedCatalog:
    def __init__(self, manager: CodexRuntimeManager, adapter: CodexModelCatalogAdapter, snapshot: CodexModelCatalog) -> None:
        self._manager, self._adapter, self._snapshot = manager, adapter, snapshot

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        runtime = await self._manager.acquire(profile_id)
        if runtime.generation == self._snapshot.runtime_generation:
            return await self._adapter.get_catalog(profile_id, refresh=False)
        return replace(self._snapshot, runtime_generation=runtime.generation)


async def _cancel_owned_task(owner_value: OwnedTask | asyncio.Task[Any], *, timeout: float, final_timeout: float | None = None) -> None:
    """Cancel one exact task and observe cancellation only through finite waits."""
    owner = _as_owned_task(owner_value)
    if owner.task.done():
        owner.terminalized = True
        return
    owner.phase = "CANCELLATION_OBSERVATION"
    owner.task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(owner.task), timeout=timeout)
    except asyncio.CancelledError:
        owner.terminalized = True
        return
    except asyncio.TimeoutError:
        owner.phase = "FINAL_CANCELLATION_OBSERVATION"
        owner.task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(owner.task), timeout=final_timeout if final_timeout is not None else timeout)
        except asyncio.CancelledError:
            owner.terminalized = True
            return
        except asyncio.TimeoutError as error:
            owner.phase = "FINAL_NONCONVERGENCE"
            owner.nonconverged = True
            raise TaskNonconvergedError(owner) from error
        else:
            owner.terminalized = True
            return
    else:
        owner.terminalized = True


async def _await_owned_task(
    task: OwnedTask | asyncio.Task[Any], *, timeout: float, convergence_timeout: float,
    on_timeout: callable | None = None, shutdown: callable | None = None,
) -> Any:
    """Wait on one owned task with finite primary, secondary and final bounds."""
    owner = _as_owned_task(task)
    try:
        value = await asyncio.wait_for(asyncio.shield(owner.task), timeout=timeout)
        owner.terminalized = True
        return value
    except asyncio.TimeoutError:
        owner.phase = "PRIMARY_TIMEOUT"
        timeout_failure: BaseException | None = None
        try:
            if on_timeout is not None:
                on_timeout()
        except BaseException as error:
            timeout_failure = error
        try:
            if shutdown is not None:
                shutdown_owner = _create_owned_task(shutdown(), f"{owner.name}-shutdown")
                try:
                    await asyncio.wait_for(asyncio.shield(shutdown_owner.task), timeout=convergence_timeout)
                    shutdown_owner.terminalized = True
                except asyncio.TimeoutError:
                    try:
                        await _cancel_owned_task(shutdown_owner, timeout=convergence_timeout, final_timeout=convergence_timeout)
                    except BaseException as error:
                        timeout_failure = timeout_failure or error
                except asyncio.CancelledError:
                    shutdown_owner.terminalized = True
                except BaseException as error:
                    shutdown_owner.terminalized = True
                    timeout_failure = timeout_failure or error
        except BaseException as error:
            timeout_failure = timeout_failure or error
        owner.phase = "SECONDARY_CONVERGENCE_WAIT"
        try:
            value = await asyncio.wait_for(asyncio.shield(owner.task), timeout=convergence_timeout)
            owner.terminalized = True
            if timeout_failure is not None:
                raise timeout_failure
            return value
        except asyncio.CancelledError:
            owner.terminalized = True
            if timeout_failure is not None:
                raise timeout_failure
            raise asyncio.TimeoutError from None
        except asyncio.TimeoutError as error:
            owner.phase = "FINAL_CANCELLATION_OBSERVATION"
            try:
                await _cancel_owned_task(owner, timeout=convergence_timeout, final_timeout=convergence_timeout)
            except TaskNonconvergedError:
                raise
            if not owner.task.cancelled():
                try:
                    value = owner.task.result()
                except BaseException:
                    pass
                else:
                    if timeout_failure is None:
                        return value
            if timeout_failure is not None:
                raise timeout_failure
            raise error
        except BaseException:
            owner.terminalized = True
            raise


async def _cancel_owned_approval(task: OwnedTask | asyncio.Task[Any], *, timeout: float, final_timeout: float | None = None) -> None:
    """Cancel the exact approval bridge with finite cancellation observations."""
    await _cancel_owned_task(task, timeout=timeout, final_timeout=final_timeout)


async def _bounded_shutdown(manager: Any, timeout: float = 30.0, final_timeout: float = 1.0) -> None:
    """Bound runtime shutdown itself; never perform an unlimited join."""
    owner = _create_owned_task(manager.shutdown_all(), "runtime-shutdown")
    try:
        await asyncio.wait_for(asyncio.shield(owner.task), timeout=timeout)
        owner.terminalized = True
    except asyncio.TimeoutError as error:
        try:
            await _cancel_owned_task(owner, timeout=final_timeout, final_timeout=final_timeout)
        except TaskNonconvergedError:
            raise
        raise error
    except asyncio.CancelledError:
        owner.terminalized = True
        raise
    except BaseException:
        owner.terminalized = True
        raise


def _owned_task_states(owned_tasks: Mapping[str, OwnedTask]) -> dict[str, dict[str, bool | str]]:
    """Return finite task state only; never serialize task objects or reprs."""
    return {
        name: {
            "phase": owner.phase,
            "terminalized": owner.terminalized,
            "nonconverged": owner.nonconverged,
        }
        for name, owner in owned_tasks.items()
    }


def _require_all_owned_tasks_terminal(owned_tasks: Mapping[str, OwnedTask]) -> None:
    """Make a normal PASS impossible while an owned task remains unresolved."""
    if any(not owner.terminalized or owner.nonconverged for owner in owned_tasks.values()):
        raise AssertionError("P7C6_SUCCESS_REQUIRES_ALL_OWNERS_TERMINAL")


def _turn_failure_result(error: BaseException) -> str:
    return "UNKNOWN" if isinstance(error, (asyncio.TimeoutError, TaskNonconvergedError)) else "FAILED"


async def _turn5_start_with_retention(
    owner_value: OwnedTask | asyncio.Task[Any], *, journal: Any, manager: Any,
    retention: dict[str, bool], timeout: float, convergence_timeout: float,
) -> Any:
    """Own the Turn-5 start ambiguity edge and retain recovery state."""
    try:
        result = await _await_owned_task(
            owner_value, timeout=timeout, convergence_timeout=convergence_timeout,
            on_timeout=lambda: journal.update(TURN5_START_RESULT="UNKNOWN"),
            shutdown=lambda: _bounded_shutdown(manager, timeout=timeout, final_timeout=convergence_timeout),
        )
    except BaseException as error:
        retention["forensic_retained"] = True
        try:
            journal.update(TURN5_START_RESULT=_turn_failure_result(error), failure_stage="TURN5_START_UNCERTAIN")
        finally:
            await _bounded_shutdown(manager, timeout=timeout, final_timeout=convergence_timeout)
        raise
    status = getattr(getattr(result, "status", None), "value", getattr(result, "status", None))
    if status != TurnStartStatus.CONFIRMED.value or getattr(result, "binding", None) is None:
        retention["forensic_retained"] = True
        error = AssertionError("P7C6_TURN5_START_NOT_CONFIRMED")
        try:
            journal.update(TURN5_START_RESULT="FAILED", failure_stage="TURN5_START_UNCERTAIN")
        finally:
            await _bounded_shutdown(manager, timeout=timeout, final_timeout=convergence_timeout)
        raise error
    return result


async def _turn4_start_failure_with_approval(
    start_error: BaseException, approval_owner: OwnedTask, *, journal: Any, manager: Any,
    retention: dict[str, bool], timeout: float, final_timeout: float,
) -> None:
    """Fail closed when the pre-created Turn-4 approval bridge will not cancel."""
    retention["forensic_retained"] = True
    try:
        await _cancel_owned_approval(approval_owner, timeout=timeout, final_timeout=final_timeout)
    except BaseException as approval_error:
        retention["forensic_retained"] = True
        try:
            journal.update(
                TURN4_START_RESULT="FAILED",
                failure_stage="APPROVAL_BRIDGE_NONCONVERGED",
            )
        finally:
            await _bounded_shutdown(manager, timeout=timeout, final_timeout=final_timeout)
        raise approval_error from start_error
    raise start_error


def _validate_watchdog_bounds(hard_deadline: float, terminate_grace: float, kill_grace: float) -> None:
    if any(type(value) not in (int, float) or value <= 0 for value in (hard_deadline, terminate_grace, kill_grace)):
        raise ValueError("PROCESS_WATCHDOG_BOUNDS_INVALID")


def launch_dedicated_continuation_child(
    *, mode: str, child_env: Mapping[str, str] | None = None,
    hard_deadline: float = WATCHDOG_HARD_DEADLINE,
    terminate_grace: float = WATCHDOG_TERMINATE_GRACE,
    kill_grace: float = WATCHDOG_KILL_GRACE,
) -> dict[str, Any]:
    """Launch exactly one child and own its finite process lifetime."""
    _validate_watchdog_bounds(hard_deadline, terminate_grace, kill_grace)
    if mode not in {"real", "synthetic-normal", "synthetic-stubborn", "synthetic-turn4-approval"}:
        raise ValueError("PROCESS_CHILD_MODE_INVALID")
    environment = os.environ.copy()
    if child_env:
        environment.update({str(key): str(value) for key, value in child_env.items()})
    command = [sys.executable, str(Path(__file__).resolve()), "--codexcontrol-p7c6-child", mode]
    started = time.monotonic()
    child = subprocess.Popen(
        command, cwd=EXPECTED_REPOSITORY, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
    )
    child_process_count = 1
    timed_out = False
    terminated = False
    try:
        child.wait(timeout=hard_deadline)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            child.terminate()
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=terminate_grace)
            terminated = True
        except subprocess.TimeoutExpired:
            try:
                child.kill()
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=kill_grace)
                terminated = True
            except subprocess.TimeoutExpired:
                terminated = child.poll() is not None
    elapsed = time.monotonic() - started
    return {
        "status": "PROCESS_WATCHDOG_TIMEOUT" if timed_out else "PROCESS_COMPLETED",
        "child_process_count": child_process_count,
        "second_child_started": "NO",
        "parent_returned_finitely": elapsed < hard_deadline + terminate_grace + kill_grace + 1.0,
        "child_terminated": terminated or child.poll() is not None,
        "returncode": child.returncode,
        "elapsed_seconds": elapsed,
    }


def _write_synthetic_payload(payload: Mapping[str, Any]) -> None:
    path_value = os.environ.get("CODEXCONTROL_P7C6_SYNTHETIC_RECOVERY")
    if not isinstance(path_value, str) or not path_value:
        raise RuntimeError("SYNTHETIC_RECOVERY_PATH_MISSING")
    path = Path(path_value)
    path.write_text(json.dumps(dict(payload), sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _write_synthetic_child_record(status: str) -> None:
    _write_synthetic_payload({"status": status})


async def _synthetic_normal_child() -> None:
    _write_synthetic_child_record("NORMAL_CHILD_COMPLETED")
    await asyncio.sleep(0)


async def _synthetic_cancellation_resistant_child() -> None:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    _write_synthetic_child_record("STUBBORN_CHILD_STARTED")
    gate = asyncio.Event()

    async def cancellation_resistant_task() -> None:
        while True:
            try:
                await gate.wait()
            except asyncio.CancelledError:
                continue

    asyncio.create_task(cancellation_resistant_task())
    await asyncio.sleep(120)


async def _synthetic_turn4_approval_child() -> None:
    """Synthetic sibling-failure child; it cannot reach any Codex adapter."""
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    recovery_value = os.environ.get("CODEXCONTROL_P7C6_SYNTHETIC_RECOVERY")
    if not isinstance(recovery_value, str) or not recovery_value:
        raise RuntimeError("SYNTHETIC_RECOVERY_PATH_MISSING")
    journal = ContinuationRecoveryJournal.create(
        Path(recovery_value), {"status": "TURN4_START_DISPATCHED", "TURN4_START_DISPATCHES": 1},
    )
    gate = asyncio.Event()
    allow_emitted: list[str] = []
    dispatches = 1
    shutdowns = 0

    async def approval() -> None:
        while True:
            try:
                await gate.wait()
                allow_emitted.append("ALLOW")
                return
            except asyncio.CancelledError:
                continue

    class Manager:
        async def shutdown_all(self) -> None:
            nonlocal shutdowns
            shutdowns += 1

    approval_owner = _create_owned_task(approval(), "synthetic-turn4-approval")
    await asyncio.sleep(0)
    try:
        await _turn4_start_failure_with_approval(
            RuntimeError("TURN4_START_FAILED"), approval_owner, journal=journal, manager=Manager(),
            retention={"forensic_retained": False}, timeout=0.01, final_timeout=0.01,
        )
    except BaseException:
        journal.update(
            status="APPROVAL_BRIDGE_NONCONVERGED",
            ALLOW_EMITTED=len(allow_emitted), TURN4_START_DISPATCHES=dispatches,
            SECOND_TURN4_START=0, RUNTIME_SHUTDOWN_CALLS=shutdowns,
        )
    await asyncio.sleep(120)


def _run_dedicated_child_coroutine(factory: callable) -> int:
    """Run a child without asyncio.run teardown, which can await stubborn tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(factory())
    except BaseException:
        return 1
    finally:
        loop.stop()
        loop.close()
        asyncio.set_event_loop(None)
    return 0


def _dedicated_child_main(mode: str) -> int:
    if mode == "synthetic-normal":
        return _run_dedicated_child_coroutine(_synthetic_normal_child)
    if mode == "synthetic-stubborn":
        return _run_dedicated_child_coroutine(_synthetic_cancellation_resistant_child)
    if mode == "synthetic-turn4-approval":
        return _run_dedicated_child_coroutine(_synthetic_turn4_approval_child)
    if mode == "real":
        return _run_dedicated_child_coroutine(_run_real_continuation)
    return 2


async def _journaled_effect(
    journal: Any, intent: str, result: str, operation: callable,
) -> Any:
    """Persist intent before, and finite result immediately after, one effect."""
    journal.update(**{intent: "YES"})
    value = await operation()
    journal.update(**{result: getattr(value, "status", value) if isinstance(getattr(value, "status", value), str) else str(getattr(value, "status", value))})
    return value


async def _run_real_continuation() -> dict[str, Any]:
    if os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION") != AUTHORIZATION:
        raise unittest.SkipTest("P7C6 same-thread continuation authorization not present")

    source = validate_source_authority()
    _validate_run1_latch()
    run_root, retained_thread_id, run1_markers = _find_retained_authority()
    state_root = run_root / "state-parent" / "c6-isolated-state"
    controller_db = run_root / "controller" / "controller.sqlite3"
    profile = CodexProfile(PROFILE_ID, PERSISTENT_HOME, "Shared authenticated", str(state_root))
    repository = Path.cwd()
    authority = IsolationPathAuthority((profile,), controller_db_path=str(controller_db), repository_root=str(repository))
    IsolatedStateRoot(authority).validate(profile)
    run_nonce = secrets.token_hex(24)
    journal_path = run_root / f"p7c6-continuation-result-recovery-{run_nonce}.json"
    supplement = run_root / f"p7c6-continuation-marker-recovery-supplement-{run_nonce}.json"
    workdir = run_root / f"continuation-workdir-{run_nonce}"
    sentinel = run_root / f"continuation-sentinel-{run_nonce}"
    boundaries = {
        "repository": repository, "persistent_home_shared": Path(PERSISTENT_HOME), "isolated_root": state_root, "sqlite": state_root / "sqlite", "logs": state_root / "logs",
        "controller_db": controller_db, "run_root": run_root,
        "run1_ledger": run_root / "recovery-ledger.json", "run1_marker_supplement": run_root / "p7c6-marker-recovery-supplement.json",
        "continuation_latch": CONTINUATION_LATCH,
        "continuation_result": journal_path, "continuation_marker_supplement": supplement,
        "continuation_workdir": workdir, "continuation_sentinel": sentinel,
    }
    preflight_local_continuation_paths({
        "continuation_latch": CONTINUATION_LATCH, "continuation_result": journal_path,
        "continuation_marker_supplement": supplement, "continuation_workdir": workdir,
        "continuation_sentinel": sentinel,
    })
    preflight_protected_boundaries(
        boundaries,
        allowed_nested=(
            ("run_root", "isolated_root"), ("run_root", "sqlite"), ("run_root", "logs"),
            ("run_root", "controller_db"), ("run_root", "run1_ledger"),
            ("run_root", "run1_marker_supplement"), ("run_root", "continuation_result"),
            ("run_root", "continuation_marker_supplement"), ("run_root", "continuation_workdir"),
            ("run_root", "continuation_sentinel"), ("isolated_root", "sqlite"), ("isolated_root", "logs"),
        ),
        externally_owned={"isolated_root", "sqlite", "logs", "controller_db", "run1_ledger", "run1_marker_supplement", "continuation_latch", "continuation_result", "continuation_marker_supplement", "continuation_workdir", "continuation_sentinel"},
    )
    if _process_users({key: value for key, value in boundaries.items() if key != "repository"}).get("isolated_root", 0):
        raise BoundaryPreflightError("P7C6_MOUNT_ALIAS_UNRESOLVED")
    latch = create_continuation_latch(
        CONTINUATION_LATCH,
        accepted_harness_sha=source["accepted_harness_sha"], accepted_harness_tree=source["accepted_harness_tree"],
        retained_thread_sha256=RUN1_THREAD_SHA256, continuation_identity="RETAINED_THREAD_T4_T5_DELETE",
    )
    journal = ContinuationRecoveryJournal.create(journal_path, {
        "format": 1, "status": "PRE_RESUME", "accepted_harness_sha": source["accepted_harness_sha"],
        "accepted_harness_tree": source["accepted_harness_tree"], "retained_thread_sha256": RUN1_THREAD_SHA256,
        "resume_status": "NOT_STARTED", "turn4_status": "NOT_STARTED", "turn5_status": "NOT_STARTED",
        "approval_request_count": 0, "approval_response_count": 0, "failure_stage": None,
    })
    workdir.mkdir(mode=0o700)
    if not _private_directory(workdir, 0o700):
        raise BoundaryPreflightError("P7C6_CONTINUATION_WORKDIR_AUTHORITY_INVALID")
    allow_marker = f"C6_CONT_ALLOW_{secrets.token_hex(24)}"
    prompt_marker = f"C6_CONT_T4_PROMPT_{secrets.token_hex(24)}"
    interrupt_marker = f"C6_CONT_T5_INTERRUPT_{secrets.token_hex(24)}"
    markers = (*run1_markers.values(), allow_marker, prompt_marker, interrupt_marker)
    ContinuationRecoveryJournal.create(supplement, {
        "format": 1, "status": "CONTINUATION_MARKERS_PERSISTED_ROOT_ONLY", "thread_id_sha256": RUN1_THREAD_SHA256,
        "allow_marker": allow_marker, "turn4_prompt_marker": prompt_marker, "turn5_interrupt_marker": interrupt_marker,
        "allow_marker_sha256": _sha256(allow_marker), "turn4_prompt_marker_sha256": _sha256(prompt_marker),
        "turn5_interrupt_marker_sha256": _sha256(interrupt_marker),
    })

    manager: CodexRuntimeManager | None = None
    storage: SqliteStorage | None = None
    sentinel: Path | None = sentinel
    workdir: Path | None = workdir
    counters: dict[str, int] = {}
    approval_responses = 0
    forensic_retained = False
    sentinel_verified = False
    workdir_created = True
    owned_tasks: dict[str, OwnedTask] = {}

    def spawn_owned(awaitable: Any, name: str) -> OwnedTask:
        owner = _create_owned_task(awaitable, name)
        owned_tasks[name] = owner
        return owner

    def progress(**fields: Any) -> None:
        journal.update(**fields)

    try:
        manager = CodexRuntimeManager([profile], client_version="p7c6-continuation", executable=EXECUTABLE, isolation_authority=authority)
        original_acquire = manager.acquire
        manager_acquire_count = 0

        async def counted_acquire(profile_id: str) -> Any:
            nonlocal manager_acquire_count
            manager_acquire_count += 1
            runtime = await original_acquire(profile_id)
            original_request = runtime.client.request
            original_response = runtime.client.respond_server_request

            async def request(method: str, params: Any) -> Any:
                counters[method] = counters.get(method, 0) + 1
                return await original_request(method, params)

            async def response(request_object: Any, result: dict[str, Any]) -> None:
                nonlocal approval_responses
                approval_responses += 1
                progress(TURN4_APPROVAL_RESPONSE_DISPATCH_INTENT="YES")
                await original_response(request_object, result)
                progress(TURN4_APPROVAL_RESPONSE_RESULT="FINITE")

            if not getattr(runtime, "_p7c6_continuation_counted", False):
                runtime.client.request = request
                runtime.client.respond_server_request = response
                runtime._p7c6_continuation_counted = True
            return runtime

        manager.acquire = counted_acquire
        runtime_task = spawn_owned(manager.acquire(PROFILE_ID), "runtime-acquire")
        runtime = await _await_owned_task(
            runtime_task, timeout=120, convergence_timeout=30,
            on_timeout=lambda: progress(RUNTIME_ACQUIRE_DISPATCH_UNCERTAIN="YES"),
            shutdown=lambda: _bounded_shutdown(manager),
        )
        manifest = manager._installed_manifest
        if manifest is None or manifest.codex_cli_version != SUPPORTED_CODEX_VERSION or manifest.schema_sha256 != SCHEMA_SHA256:
            raise AssertionError("P7C6_CAPABILITY_MISMATCH")
        catalog_adapter = CodexModelCatalogAdapter(manager)
        progress(MODEL_LIST_DISPATCH_INTENT="YES")
        catalog_task = spawn_owned(catalog_adapter.get_catalog(PROFILE_ID), "model-list")
        catalog = await _await_owned_task(
            catalog_task, timeout=120, convergence_timeout=30,
            on_timeout=lambda: progress(MODEL_LIST_RESULT="UNKNOWN"),
            shutdown=lambda: _bounded_shutdown(manager),
        )
        progress(MODEL_LIST_RESULT="FINITE", model_list_calls=counters.get("model/list", 0))
        defaults = tuple(model for model in catalog.models if not model.hidden and model.is_default)
        if len(defaults) != 1:
            raise AssertionError("P7C6_MODEL_DEFAULT_AMBIGUOUS")
        model = defaults[0]
        pinned_catalog = _PinnedCatalog(manager, catalog_adapter, catalog)
        thread_lifecycle = CodexThreadLifecycleAdapter(manager, pinned_catalog)
        turn_lifecycle = CodexTurnLifecycleAdapter(manager, pinned_catalog)
        retained_binding = ThreadBinding(PROFILE_ID, retained_thread_id)
        progress(RESUME_DISPATCH_INTENT="YES")
        resume_task = spawn_owned(thread_lifecycle.resume(binding=retained_binding, working_directory=TrustedWorkingDirectory(str(run_root))), "thread-resume")
        resume = await _await_owned_task(
            resume_task, timeout=120, convergence_timeout=30,
            on_timeout=lambda: progress(RESUME_RESULT="UNKNOWN"),
            shutdown=lambda: _bounded_shutdown(manager),
        )
        progress(resume_status=resume.status.value, RESUME_RESULT=resume.status.value)
        if resume.status is not ThreadOperationStatus.RESUME_CONFIRMED or resume.binding is not retained_binding:
            raise AssertionError("P7C6_RESUME_NOT_CONFIRMED")

        turn4_id = asyncio.get_running_loop().create_future()
        inner = f"printf {allow_marker} > {sentinel}"
        operator = _StructuralApprovalOperator(thread_id=retained_thread_id, turn_id=turn4_id, cwd=str(workdir), inner=inner, marker=allow_marker, sentinel=str(sentinel))
        bridge = CodexApprovalBridge(profile_id=PROFILE_ID, client=runtime.client, operator=operator)
        approval_task = spawn_owned(bridge.handle_next(), "turn4-approval-bridge")
        await asyncio.sleep(0)
        if approval_task.done():
            raise AssertionError("P7C6_BRIDGE_NOT_ARMED")
        progress(bridge_armed="YES", resume_dispatched="YES", model_list_calls=counters.get("model/list", 0))
        progress(TURN4_START_DISPATCH_INTENT="YES")
        turn4_task = spawn_owned(turn_lifecycle.start_turn(
            thread_binding=retained_binding, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            user_text=f"Execute exactly this operation once and no additional operation: {inner}. Prompt marker: {prompt_marker}.",
            working_directory=TrustedWorkingDirectory(str(workdir)),
        ), "turn4-start")
        try:
            turn4 = await _await_owned_task(
                turn4_task, timeout=120, convergence_timeout=30,
                on_timeout=lambda: progress(TURN4_START_RESULT="UNKNOWN"),
                shutdown=lambda: _bounded_shutdown(manager),
            )
        except BaseException as error:
            retention = {"forensic_retained": False}
            forensic_retained = True
            await _turn4_start_failure_with_approval(
                error, approval_task, journal=journal, manager=manager, retention=retention,
                timeout=5, final_timeout=5,
            )
            forensic_retained = retention["forensic_retained"]
            raise AssertionError("P7C6_TURN4_START_FAILURE_HANDLER_RETURNED")
        progress(turn4_start_status=turn4.status.value, TURN4_START_RESULT=turn4.status.value)
        if turn4.status is not TurnStartStatus.CONFIRMED or turn4.binding is None:
            forensic_retained = True
            await _cancel_owned_approval(approval_task, timeout=5, final_timeout=5)
            raise AssertionError("P7C6_TURN4_START_NOT_CONFIRMED")
        turn4_id.set_result(turn4.binding.turn_id)
        progress(turn4_id_sha256=_sha256(turn4.binding.turn_id), turn4_start_dispatched="YES")
        try:
            approval = await asyncio.wait_for(asyncio.shield(approval_task.task), timeout=90)
        except asyncio.TimeoutError:
            forensic_retained = True
            progress(approval_handling_status="TIMEOUT", failure_stage="APPROVAL_TIMEOUT", APPROVAL_RESULT="UNKNOWN")
            await _cancel_owned_approval(approval_task, timeout=30, final_timeout=30)
            raise
        approval_task.terminalized = True
        progress(
            approval_request_count=len(operator.requests), approval_kind=operator.requests[0].kind.value if operator.requests else None,
            thread_match=bool(operator.results and not (set(operator.results[0].mismatch_flags) & {"THREAD"})),
            turn_match=bool(operator.results and not (set(operator.results[0].mismatch_flags) & {"TURN"})),
            cwd_match=bool(operator.results and not (set(operator.results[0].mismatch_flags) & {"CWD"})),
            marker_match=bool(operator.results and not (set(operator.results[0].mismatch_flags) & {"MARKER"})),
            sentinel_match=bool(operator.results and not (set(operator.results[0].mismatch_flags) & {"SENTINEL"})),
            grammar_class=operator.results[0].grammar if operator.results else "NONE",
            mismatch_flags=operator.results[0].mismatch_flags if operator.results else ("REQUEST_MISSING",),
            operator_decision="ALLOW" if approval.status is ApprovalHandlingStatus.ALLOWED else "DENY",
            approval_handling_status=approval.status.value, approval_response_count=approval_responses,
        )
        if approval.status is not ApprovalHandlingStatus.ALLOWED or operator.allow_count != 1 or len(operator.requests) != 1 or approval_responses != 1:
            forensic_retained = approval.status is ApprovalHandlingStatus.RESPONSE_UNKNOWN
            raise AssertionError("P7C6_TURN4_APPROVAL_NOT_EXACTLY_ALLOWED")
        try:
            terminal4_task = spawn_owned(turn_lifecycle.wait_turn(turn4.binding), "turn4-terminal-waiter")
            terminal4 = await _await_owned_task(
                terminal4_task, timeout=120, convergence_timeout=30,
                on_timeout=lambda: progress(TURN4_TERMINAL_RESULT="UNKNOWN"),
                shutdown=lambda: _bounded_shutdown(manager),
            )
        except BaseException:
            forensic_retained = True
            progress(turn4_terminal_status="UNKNOWN", failure_stage="TURN4_TERMINAL_UNCERTAIN")
            raise
        if terminal4.status is not TurnTerminalStatus.COMPLETED or not sentinel.exists() or not _safe_exact_file(sentinel, allow_marker.encode("utf-8")):
            forensic_retained = True
            raise AssertionError("P7C6_TURN4_NOT_DEFINITIVE")
        sentinel_verified = True
        progress(turn4_terminal_status=terminal4.status.value, turn4_sentinel_proof="EXACT")
        sentinel.unlink()

        progress(TURN5_START_DISPATCH_INTENT="YES")
        turn5_task = spawn_owned(turn_lifecycle.start_turn(
            thread_binding=retained_binding, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            user_text=f"Execute exactly `sleep 120` and no additional operation. Interrupt marker: {interrupt_marker}.",
            working_directory=TrustedWorkingDirectory(str(workdir)),
        ), "turn5-start")
        turn5_retention = {"forensic_retained": False}
        try:
            turn5 = await _turn5_start_with_retention(
                turn5_task, journal=journal, manager=manager, retention=turn5_retention,
                timeout=120, convergence_timeout=30,
            )
        except BaseException:
            forensic_retained = turn5_retention["forensic_retained"]
            raise
        forensic_retained = turn5_retention["forensic_retained"]
        progress(turn5_start_status=turn5.status.value, TURN5_START_RESULT=turn5.status.value)
        if turn5.status is not TurnStartStatus.CONFIRMED or turn5.binding is None:
            raise AssertionError("P7C6_TURN5_START_NOT_CONFIRMED")
        terminal5_task = spawn_owned(turn_lifecycle.wait_turn(turn5.binding), "turn5-terminal-waiter")
        try:
            await asyncio.wait_for(asyncio.shield(terminal5_task.task), timeout=5)
        except asyncio.TimeoutError:
            progress(turn5_active_before_interrupt="YES")
        except Exception:
            forensic_retained = True
            progress(turn5_active_before_interrupt="UNKNOWN", failure_stage="TURN5_ACTIVE_UNCERTAIN")
            raise
        else:
            forensic_retained = True
            raise AssertionError("P7C6_TURN5_TERMINAL_BEFORE_INTERRUPT")
        acquire_before_interrupt = manager_acquire_count
        progress(INTERRUPT_DISPATCH_INTENT="YES")
        interrupt_task = spawn_owned(turn_lifecycle.interrupt_turn(turn5.binding), "interrupt")
        try:
            interrupt = await _await_owned_task(
                interrupt_task, timeout=90, convergence_timeout=30,
                on_timeout=lambda: progress(INTERRUPT_RESULT="UNKNOWN"),
                shutdown=lambda: _bounded_shutdown(manager),
            )
        except BaseException:
            forensic_retained = True
            progress(interrupt_status="UNKNOWN", failure_stage="INTERRUPT_UNCERTAIN")
            try:
                await _bounded_shutdown(manager)
            finally:
                await _cancel_owned_approval(terminal5_task, timeout=5, final_timeout=5)
            raise
        acquire_after_interrupt = manager_acquire_count
        try:
            terminal5 = await _await_owned_task(
                terminal5_task, timeout=90, convergence_timeout=30,
                on_timeout=lambda: progress(TURN5_TERMINAL_RESULT="UNKNOWN"),
                shutdown=lambda: _bounded_shutdown(manager),
            )
        except BaseException:
            forensic_retained = True
            progress(turn5_terminal_status="UNKNOWN", failure_stage="TURN5_TERMINAL_UNCERTAIN")
            raise
        progress(
            interrupt_dispatched="YES", interrupt_status=interrupt.status.value,
            turn5_terminal_status=terminal5.status.value, runtime_acquire_before_interrupt=acquire_before_interrupt,
            runtime_acquire_after_interrupt=acquire_after_interrupt,
            runtime_reacquire_during_interrupt="NO" if acquire_after_interrupt == acquire_before_interrupt else "YES",
        )
        if interrupt.status not in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED) or terminal5.status is not TurnTerminalStatus.FAILED or approval_responses != 1:
            forensic_retained = True
            raise AssertionError("P7C6_TURN5_INTERRUPT_NOT_DEFINITIVE")
        assert_no_reacquire(acquire_before_interrupt, acquire_after_interrupt)
        await _bounded_shutdown(manager)
        if _continuation_owned_processes(workdir):
            forensic_retained = True
            raise AssertionError("P7C6_DELAYED_PROCESS_REMAINS")
        if any(_process_users({"isolated_root": state_root, "sqlite": state_root / "sqlite", "logs": state_root / "logs", "controller_db": controller_db, "workdir": workdir}).values()):
            raise BoundaryPreflightError("P7C6_CONTINUATION_BOUNDARY_EXTERNAL_USERS")

        baseline = capture_unrelated_baseline(Path(PERSISTENT_HOME), retained_thread_id)
        progress(predelete_baseline_count=len(baseline.identities), predelete_baseline_identities=[identity.__dict__ for identity in baseline.identities], predelete_baseline_errors=baseline.scan_errors, predelete_baseline_limit=baseline.limit_exceeded)
        scanner = PersistentProfileResidualScanner(authority)
        predelete = scanner.scan(profile, retained_thread_id)
        predelete_oracle = _marker_oracle(profile, retained_thread_id, markers)
        progress(predelete_scan_matches=predelete.match_count, predelete_scan_errors=predelete.scan_errors, predelete_oracle=predelete_oracle)
        if baseline.scan_errors or baseline.limit_exceeded or predelete.scan_errors or predelete.limit_exceeded or (predelete.match_count == 0 and not predelete_oracle["thread_count"] and not predelete_oracle["marker_count"]):
            raise AssertionError("P7C6_PREDELETE_OBSERVATION_INCONCLUSIVE")

        storage = await SqliteStorage.open(str(controller_db))
        controller = await validate_controller_state(storage, "p7c6-retained-dialogue", controller_db)
        progress(controller_actual_user_version=controller["actual_user_version"], controller_preexisting_live_dialogue="NO" if controller["preexisting_live_dialogue"] is None else "YES", controller_conflicting_tombstone="NO" if controller["conflicting_tombstone"] is None else "YES")
        if not controller["passed"]:
            raise AssertionError("P7C6_CONTROLLER_EMPTY_STATE_INVALID")
        dialogues = DialogueRepository(storage, now_ms=lambda: 4000)
        await dialogues.create_intent(dialogue_id="p7c6-retained-dialogue", server_id=SERVER_ID, profile_id=PROFILE_ID)
        created = await dialogues.confirm_created(dialogue_id="p7c6-retained-dialogue", expected_version=0, thread_id=retained_thread_id)
        observer = ObservingDeleteLifecycle(thread_lifecycle)
        cleanup = DeleteStorageCleanupCoordinator(storage, manager, scanner=scanner, now_ms=lambda: 5000)
        delete_service = DialogueDeleteService(storage, server_id=SERVER_ID, thread_lifecycle=observer, local_cleanup=cleanup, now_ms=lambda: 5000)
        progress(DELETE_DISPATCH_INTENT="YES")
        delete_task = spawn_owned(delete_service.delete(DialogueDeleteRequest(created.dialogue_id, created.version)), "delete-service")
        try:
            deleted = await _await_owned_task(
                delete_task, timeout=180, convergence_timeout=30,
                on_timeout=lambda: progress(DELETE_RESULT="UNKNOWN", failure_stage="DELETE_UNCERTAIN"),
                shutdown=lambda: _bounded_shutdown(manager),
            )
        except BaseException:
            forensic_retained = True
            progress(official_delete_dispatched="YES", failure_stage="DELETE_UNCERTAIN", official_delete_status=observer.status.value if observer.status else "UNKNOWN")
            raise
        progress(official_delete_dispatched="YES", DELETE_RESULT=deleted.status.value, official_delete_call_count=observer.call_count, official_p1_delete_status=observer.status.value if observer.status else "UNKNOWN", application_delete_status=deleted.status.value)
        if observer.call_count != 1 or observer.status is not ThreadOperationStatus.DELETE_CONFIRMED or deleted.status is not DialogueDeleteStatus.DELETED or deleted.tombstone is None:
            forensic_retained = observer.call_count == 1
            raise AssertionError("P7C6_DELETE_AUTHORITY_NOT_CONFIRMED")
        await _bounded_shutdown(manager)
        isolated = IsolatedStateRoot(authority)
        isolated.validate(profile)
        isolated_proof = _isolated_payload_proof(state_root)
        postdelete = scanner.scan(profile, retained_thread_id)
        postdelete_oracle = _marker_oracle(profile, retained_thread_id, markers)
        baseline_result = reconcile_unrelated_baseline(baseline, Path(PERSISTENT_HOME))
        live_after = await DialogueRepository(storage).get_live()
        tombstone_after = await DeletionRepository(storage).get_tombstone(created.dialogue_id)
        progress(postdelete_scan_matches=postdelete.match_count, postdelete_scan_errors=postdelete.scan_errors, postdelete_oracle=postdelete_oracle, isolated_proof=isolated_proof, unrelated_baseline=baseline_result, live_dialogue_after_delete="NO" if live_after is None else "YES", tombstone_present="YES" if tombstone_after else "NO")
        if postdelete.match_count or postdelete.scan_errors or postdelete.limit_exceeded or postdelete_oracle["thread_count"] or postdelete_oracle["marker_count"] or postdelete_oracle["scan_errors"] or postdelete_oracle["limit_exceeded"] or not baseline_result["preserved"] or isolated_proof["POSTDELETE_SQLITE_PAYLOAD_DESCENDANTS"] or isolated_proof["POSTDELETE_LOG_PAYLOAD_DESCENDANTS"] or isolated_proof["POSTDELETE_ISOLATED_TRAVERSAL_ERRORS"] or live_after is not None or tombstone_after is None:
            raise AssertionError("P7C6_POSTDELETE_GATE_FAILED")
        assert_dynamic_budget(counters, approval_responses)
        progress(status="ALL_POSTDELETE_GATES_PASS")

        # This is intentionally the final local operation.  It is never run
        # before every external and local acceptance gate above has passed.
        try:
            sanitize_only_after_final_gates(True, {
                run_root / "recovery-ledger.json": {"format": 2, "status": "SANITIZED_COMPLETED", "thread_id_sha256": RUN1_THREAD_SHA256, "source_sha256": source["accepted_harness_sha"], "source_tree": source["accepted_harness_tree"]},
                run_root / "p7c6-marker-recovery-supplement.json": {"format": 2, "status": "SANITIZED_COMPLETED", "thread_id_sha256": RUN1_THREAD_SHA256, "marker_sha256": [_sha256(value) for value in run1_markers.values()]},
                supplement: {"format": 2, "status": "SANITIZED_COMPLETED", "thread_id_sha256": RUN1_THREAD_SHA256, "marker_sha256": [_sha256(value) for value in markers[3:]], "source_sha256": source["accepted_harness_sha"], "source_tree": source["accepted_harness_tree"]},
                journal_path: {"format": 2, "status": "SANITIZED_COMPLETED", "accepted_harness_sha": source["accepted_harness_sha"], "accepted_harness_tree": source["accepted_harness_tree"], "retained_thread_sha256": RUN1_THREAD_SHA256, "official_p1_delete_status": observer.status.value, "application_delete_status": deleted.status.value, "approval_response_count": approval_responses, "interrupt_calls": counters.get("turn/interrupt", 0), "thread_delete_calls": counters.get("thread/delete", 0)},
            })
        except SanitizationError:
            try:
                journal.update(status="OFFICIAL_DELETE_CONFIRMED", failure_stage="LOCAL_RECOVERY_SANITIZATION_FAILED", official_delete_status=observer.status.value, application_delete_status=deleted.status.value)
            except Exception:
                pass
            raise
        _require_all_owned_tasks_terminal(owned_tasks)
        return {
            "source_sha": source["accepted_harness_sha"], "source_tree": source["accepted_harness_tree"], "retained_thread_sha256": RUN1_THREAD_SHA256,
            "official_p1_delete_status": observer.status.value, "application_delete_status": deleted.status.value,
            "model_list_calls": counters.get("model/list", 0), "thread_start_calls": counters.get("thread/start", 0), "thread_resume_calls": counters.get("thread/resume", 0),
            "turn_start_calls": counters.get("turn/start", 0), "approval_responses": approval_responses, "interrupt_calls": counters.get("turn/interrupt", 0), "thread_delete_calls": counters.get("thread/delete", 0),
        }
    except Exception as error:
        states = _owned_task_states(owned_tasks)
        try:
            progress(status="FAILURE", failure_stage=type(error).__name__, owned_task_states=states)
        except Exception:
            # A failed journal remains fail-closed; never replace the original
            # operation result with a sensitive task representation.
            pass
        raise
    finally:
        if manager is not None:
            try:
                await _bounded_shutdown(manager)
            except Exception:
                pass
        if storage is not None:
            try:
                await storage.close()
            except Exception:
                pass
        if not forensic_retained and sentinel is not None and sentinel.exists() and not sentinel_verified:
            try:
                sentinel.unlink()
            except OSError:
                pass
        if not forensic_retained and workdir_created and workdir is not None and workdir.exists():
            try:
                workdir.rmdir()
            except OSError:
                pass


class StructuralMatcherOfflineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thread, self.turn = "retained-thread", "turn-4"
        self.cwd = "/run/codexcontrol/continuation-workdir"
        self.marker = "C6_CONT_ALLOW_" + "a" * 48
        self.sentinel = "/run/codexcontrol/continuation-sentinel"
        self.inner = f"printf {self.marker} > {self.sentinel}"

    def _match(self, requests: Sequence[ApprovalRequest]) -> StructuralApprovalResult:
        return match_structural_approval(requests, expected_thread_id=self.thread, expected_turn_id=self.turn, expected_cwd=self.cwd, expected_inner_command=self.inner, expected_marker=self.marker, expected_sentinel=self.sentinel)

    def test_preserve_all_13_allow_cases(self) -> None:
        cases = [self.inner] + [f"{executable} {option} {shlex.quote(self.inner)}" for executable in sorted(WRAPPERS) for option in sorted(WRAPPER_OPTIONS)]
        self.assertEqual(len(cases), 13)
        for command in cases:
            result = self._match([_request(command, thread=self.thread, turn=self.turn, cwd=self.cwd)])
            self.assertTrue(result.allowed, result)
            self.assertIn(result.grammar, ("EXACT_INNER", "ONE_SHELL_WRAPPER"))

    def test_preserve_and_expand_deny_cases(self) -> None:
        cases: list[ApprovalRequest | Sequence[ApprovalRequest]] = [
            _request(self.inner, thread="wrong-thread"), _request(self.inner, thread=None), _request(self.inner, turn="wrong-turn"), _request(self.inner, turn=None), _request(self.inner, cwd="/wrong"),
            _request(self.inner, kind=ApprovalKind.EXEC_COMMAND), (_request(self.inner), _request(self.inner)),
            _request("echo prefix && " + self.inner), _request(self.inner + " && echo suffix"), _request("sh -c " + shlex.quote("sh -c " + shlex.quote(self.inner))),
            _request("sh -c " + shlex.quote(self.inner) + " | cat"), _request(self.inner + "; echo extra"), _request(self.inner.replace("printf", "printfX")),
            _request("sh -c 'unterminated"), _request("env " + self.inner), _request(self.inner + " > /tmp/extra"),
            _request(self.inner.replace(self.marker, "C6_CONT_ALLOW_" + "b" * 48)), _request(self.inner.replace(self.sentinel, "/wrong/sentinel")),
        ]
        for case in cases:
            requests = [case] if isinstance(case, ApprovalRequest) else list(case)
            self.assertFalse(self._match(requests).allowed)
        self.assertGreaterEqual(len(cases), 18)


class ContinuationLatchOfflineTests(unittest.TestCase):
    def test_exclusive_no_follow_source_tree_and_retention(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-latch-") as directory:
            parent = Path(directory)
            path = parent / "continuation-ledger.json"
            expected = create_continuation_latch(path, accepted_harness_sha="a" * 40, accepted_harness_tree="b" * 40, retained_thread_sha256="c" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")
            self.assertEqual(read_continuation_latch(path, expected), expected)
            with self.assertRaises(ContinuationLatchExists):
                create_continuation_latch(path, accepted_harness_sha="a" * 40, accepted_harness_tree="b" * 40, retained_thread_sha256="c" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")
            symlink = parent / "symlink.json"
            symlink.symlink_to(path)
            with self.assertRaises(ContinuationLatchExists):
                create_continuation_latch(symlink, accepted_harness_sha="a" * 40, accepted_harness_tree="b" * 40, retained_thread_sha256="c" * 64, continuation_identity="RETAINED_THREAD_T4_T5_DELETE")

    def test_journal_created_before_simulated_resume_and_atomic_update(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-journal-") as directory:
            path = Path(directory) / "journal.json"
            journal = ContinuationRecoveryJournal.create(path, {"stage": "BEFORE_RESUME", "resume_dispatched": "NO"})
            journal.update(resume_dispatched="YES", failure_stage="RESPONSE_UNKNOWN")
            self.assertEqual(_read_private_json(path)["failure_stage"], "RESPONSE_UNKNOWN")


class SourceAuthorityOfflineTests(unittest.TestCase):
    def test_exact_head_tree_clean_pass_and_wrong_values_fail(self) -> None:
        repository = Path(EXPECTED_REPOSITORY)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
        tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=repository, check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
        with mock.patch(__name__ + "._git_value", side_effect=[head, tree, ""]):
            self.assertEqual(validate_source_authority(repository=repository, expected_head=head, expected_tree=tree)["accepted_harness_sha"], head)
        with mock.patch(__name__ + "._git_value", side_effect=[head, tree, "dirty"]):
            with self.assertRaisesRegex(SourceAuthorityError, "SOURCE_AUTHORITY_MISMATCH"):
                validate_source_authority(repository=repository, expected_head=head, expected_tree=tree)
        with self.assertRaisesRegex(SourceAuthorityError, "SOURCE_AUTHORITY_MISMATCH"):
            validate_source_authority(repository=repository, expected_head="0" * 40, expected_tree=tree)
        with self.assertRaisesRegex(SourceAuthorityError, "SOURCE_AUTHORITY_MISMATCH"):
            validate_source_authority(repository=repository, expected_head=head, expected_tree="0" * 40)


class MountAliasOfflineTests(unittest.TestCase):
    def test_safe_and_external_boundary_classification(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-boundary-") as directory:
            root = Path(directory)
            (root / "child").mkdir(mode=0o700)
            result = preflight_protected_boundaries({"root": root, "child": root / "child"}, allowed_nested=(("root", "child"),), mountinfo="")
            self.assertEqual(result["mount_alias"], "PASS")
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({"root": root, "alias": root}, mountinfo="")
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({"root": root}, external_users={"root": 1}, mountinfo="")

    def test_symlink_and_exact_mountpoint_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-boundary-") as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir(mode=0o700)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({"link": link}, mountinfo="")
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({"target": target}, mountinfo=f"1 0 0:1 / {target} rw - tmpfs tmpfs rw")

    def test_complete_real_shaped_retained_topology_passes_and_mutations_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-topology-") as directory:
            root = Path(directory)
            run = root / "run_root"
            isolated = run / "state-parent" / "c6-isolated-state"
            sqlite = isolated / "sqlite"
            logs = isolated / "logs"
            controller = run / "controller" / "controller.sqlite3"
            sqlite.mkdir(parents=True, mode=0o700)
            logs.mkdir(mode=0o700)
            controller.parent.mkdir(mode=0o700)
            controller.write_bytes(b"db")
            for name in ("recovery-ledger.json", "p7c6-marker-recovery-supplement.json", "continuation-result.json", "continuation-supplement.json", "continuation-sentinel"):
                path = run / name
                path.write_bytes(b"record")
                path.chmod(0o600)
            workdir = run / "continuation-workdir"
            workdir.mkdir(mode=0o700)
            latch = root / "latch.json"
            latch.write_bytes(b"latch")
            latch.chmod(0o600)
            boundaries = {
                "run_root": run, "isolated_root": isolated, "sqlite": sqlite, "logs": logs,
                "controller_db": controller, "run1_ledger": run / "recovery-ledger.json",
                "run1_marker_supplement": run / "p7c6-marker-recovery-supplement.json",
                "continuation_latch": latch, "continuation_result": run / "continuation-result.json",
                "continuation_marker_supplement": run / "continuation-supplement.json",
                "continuation_workdir": workdir, "continuation_sentinel": run / "continuation-sentinel",
            }
            allowed = tuple(("run_root", child) for child in ("isolated_root", "sqlite", "logs", "controller_db", "run1_ledger", "run1_marker_supplement", "continuation_result", "continuation_marker_supplement", "continuation_workdir", "continuation_sentinel")) + (("isolated_root", "sqlite"), ("isolated_root", "logs"))
            self.assertEqual(preflight_protected_boundaries(boundaries, allowed_nested=allowed, external_users={name: 0 for name in boundaries}, mountinfo="")["mount_alias"], "PASS")

            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({**boundaries, "unexpected": run / "unexpected"}, allowed_nested=allowed, external_users={name: 0 for name in boundaries} | {"unexpected": 0}, mountinfo="")
            alias = run / "alias"
            os.link(run / "recovery-ledger.json", alias)
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({**boundaries, "alias": alias}, allowed_nested=allowed, external_users={name: 0 for name in boundaries} | {"alias": 0}, mountinfo="")
            symlink = root / "symlink"
            symlink.symlink_to(run)
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries({"symlinked": symlink / "child"}, external_users={"symlinked": 0}, mountinfo="")

    def test_repository_use_is_allowed_but_owned_boundary_use_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-users-") as directory:
            root = Path(directory)
            (root / "owned").mkdir(mode=0o700)
            (root / "shared").mkdir(mode=0o700)
            (root / "persistent").mkdir(mode=0o700)
            (root / "other-owned").mkdir(mode=0o700)
            result = preflight_protected_boundaries(
                {"repository": root / "shared", "persistent_home_shared": root / "persistent", "isolated_root": root / "owned"},
                external_users={"repository": 1, "persistent_home_shared": 1, "isolated_root": 0}, mountinfo="",
            )
            self.assertEqual(result["external_users"]["repository"], 1)
            with self.assertRaises(BoundaryPreflightError):
                preflight_protected_boundaries(
                    {"repository": root / "shared", "isolated_root": root / "other-owned"},
                    external_users={"repository": 1, "isolated_root": 1}, mountinfo="",
                )


class LocalContinuationPathOfflineTests(unittest.TestCase):
    def test_all_local_paths_are_absent_safe_and_nonoverlapping(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-local-") as directory:
            root = Path(directory)
            paths = {name: root / name for name in ("latch", "journal", "supplement", "workdir", "sentinel")}
            self.assertEqual(preflight_local_continuation_paths(paths)["status"], "PASS")
            paths["journal"].write_text("collision", encoding="utf-8")
            paths["journal"].chmod(0o600)
            with self.assertRaisesRegex(BoundaryPreflightError, "COLLISION"):
                preflight_local_continuation_paths(paths)

    def test_local_symlink_and_overlap_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-local-") as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir(mode=0o700)
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(BoundaryPreflightError):
                preflight_local_continuation_paths({"sentinel": link / "sentinel"})
            with self.assertRaises(BoundaryPreflightError):
                preflight_local_continuation_paths({"workdir": target, "sentinel": target / "sentinel"})


class MarkerOracleOfflineTests(unittest.TestCase):
    def _profile(self, root: Path) -> CodexProfile:
        home = root / "home"
        state = root / "state"
        (home / "sessions").mkdir(parents=True, mode=0o700)
        (state / "sqlite").mkdir(parents=True, mode=0o700)
        (state / "logs").mkdir(mode=0o700)
        return CodexProfile("p", str(home), "test", str(state))

    def test_normal_and_chunk_boundary_match(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            thread, marker = "THREAD-X", "MARKER-X"
            (root / "home/sessions/a").write_bytes(b"prefix" + marker.encode() + b"/" + thread.encode())
            result = _marker_oracle(profile, thread, (marker,), max_files=10, max_file_bytes=100, max_bytes=100, chunk_bytes=4)
            self.assertEqual(result["thread_count"], 1)
            self.assertEqual(result["marker_count"], 1)

    def test_symlink_hardlink_special_read_failure_and_inode_substitution_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            payload = root / "home/sessions/a"
            payload.write_bytes(b"THREAD-X")
            (root / "home/sessions/link").symlink_to(payload)
            (root / "home/sessions/hard").hardlink_to(payload)
            os.mkfifo(root / "home/sessions/fifo")
            result = _marker_oracle(profile, "THREAD-X", ())
            self.assertGreater(result["scan_errors"], 0)

    def test_file_aggregate_and_count_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            for index in range(3):
                (root / f"home/sessions/{index}").write_bytes(b"THREAD-X")
            self.assertTrue(_marker_oracle(profile, "THREAD-X", (), max_files=2)["limit_exceeded"])
            self.assertTrue(_marker_oracle(profile, "THREAD-X", (), max_file_bytes=2)["limit_exceeded"])
            self.assertTrue(_marker_oracle(profile, "THREAD-X", (), max_bytes=4)["limit_exceeded"])

    def test_read_failure_and_inode_substitution_hooks_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            path = root / "home/sessions/a"
            path.write_bytes(b"THREAD-X")
            original_read = os.read
            try:
                os.read = lambda fd, size: (_ for _ in ()).throw(OSError("read failure"))  # type: ignore[assignment]
                self.assertGreater(_marker_oracle(profile, "THREAD-X", ())["scan_errors"], 0)
            finally:
                os.read = original_read  # type: ignore[assignment]

    def test_inode_substitution_after_read_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            path = root / "home/sessions/a"
            path.write_bytes(b"THREAD-X")
            original_fstat = os.fstat
            probe_fd = os.open(path, os.O_RDONLY)
            try:
                first = original_fstat(probe_fd)
            finally:
                os.close(probe_fd)
            changed_values = list(first)
            changed_values[1] += 1
            changed = os.stat_result(changed_values)
            with mock.patch("os.fstat", side_effect=[first, changed]):
                self.assertGreater(_marker_oracle(profile, "THREAD-X", ())["scan_errors"], 0)


    def test_real_pathname_replacement_after_read_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-oracle-replace-") as directory:
            root = Path(directory)
            profile = self._profile(root)
            path = root / "home/sessions/a"
            replacement = root / "home/sessions/replacement"
            path.write_bytes(b"THREAD-X")
            replacement.write_bytes(b"replacement")
            original_read = os.read
            swapped = False

            def replacing_read(fd: int, size: int) -> bytes:
                nonlocal swapped
                data = original_read(fd, size)
                if data and not swapped:
                    swapped = True
                    os.replace(replacement, path)
                return data

            with mock.patch("os.read", side_effect=replacing_read):
                result = _marker_oracle(profile, "THREAD-X", ())
            self.assertTrue(swapped)
            self.assertGreater(result["scan_errors"], 0)


class ExactSentinelOfflineTests(unittest.TestCase):
    def test_exact_bytes_only_and_all_unsafe_fixtures_fail(self) -> None:
        marker = b"C6_SYNTHETIC_ALLOW_MARKER"
        invalid = (
            b"prefix" + marker,
            marker + b"suffix",
            marker + b"\n",
            marker + marker,
            b"",
            b"C6_SYNTHETIC_ALLOW_MARKEX",
        )
        with tempfile.TemporaryDirectory(prefix="p7c6-exact-sentinel-") as directory:
            root = Path(directory)
            exact = root / "exact"
            exact.write_bytes(marker)
            self.assertTrue(_safe_exact_file(exact, marker))
            for index, payload in enumerate(invalid):
                path = root / f"invalid-{index}"
                path.write_bytes(payload)
                self.assertFalse(_safe_exact_file(path, marker), payload)

            target = root / "target"
            target.write_bytes(marker)
            symlink = root / "symlink"
            symlink.symlink_to(target)
            self.assertFalse(_safe_exact_file(symlink, marker))
            hardlink = root / "hardlink"
            os.link(target, hardlink)
            self.assertFalse(_safe_exact_file(target, marker))
            self.assertFalse(_safe_exact_file(hardlink, marker))

    def test_pathname_replacement_during_read_fails(self) -> None:
        marker = b"C6_SYNTHETIC_ALLOW_MARKER"
        with tempfile.TemporaryDirectory(prefix="p7c6-exact-replace-") as directory:
            root = Path(directory)
            path = root / "sentinel"
            replacement = root / "replacement"
            path.write_bytes(marker)
            replacement.write_bytes(b"replacement")
            original_read = os.read
            swapped = False

            def replacing_read(fd: int, size: int) -> bytes:
                nonlocal swapped
                data = original_read(fd, size)
                if data and not swapped:
                    swapped = True
                    os.replace(replacement, path)
                return data

            with mock.patch("os.read", side_effect=replacing_read):
                self.assertFalse(_safe_exact_file(path, marker))
            self.assertTrue(swapped)

    def test_mutation_during_read_fails(self) -> None:
        marker = b"C6_SYNTHETIC_ALLOW_MARKER"
        with tempfile.TemporaryDirectory(prefix="p7c6-exact-mutation-") as directory:
            path = Path(directory) / "sentinel"
            path.write_bytes(marker)
            original_read = os.read
            mutated = False

            def mutating_read(fd: int, size: int) -> bytes:
                nonlocal mutated
                data = original_read(fd, size)
                if data and not mutated:
                    mutated = True
                    os.utime(path, ns=(3, 4))
                return data

            with mock.patch("os.read", side_effect=mutating_read):
                self.assertFalse(_safe_exact_file(path, marker))
            self.assertTrue(mutated)


class ControllerAndBudgetOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_schema_empty_state_and_tombstone_conflict(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-controller-") as directory:
            path = Path(directory) / "controller.sqlite3"
            storage = await SqliteStorage.open(str(path))
            try:
                proof = await validate_controller_state(storage, "dialogue")
                self.assertEqual(proof["actual_user_version"], 4)
                self.assertTrue(proof["passed"])
                await DialogueRepository(storage).create_intent(dialogue_id="live", server_id="s", profile_id="p")
                self.assertFalse((await validate_controller_state(storage, "dialogue"))["passed"])
            finally:
                await storage.close()

    async def test_wrong_actual_schema_and_conflicting_tombstone_fail_closed(self) -> None:
        class FakeStorage:
            async def read(self, callback: Any) -> Any:
                return 3 if callback is not None else None
        with mock.patch(__name__ + ".DialogueRepository") as dialogue_repo, mock.patch(__name__ + ".DeletionRepository") as deletion_repo:
            dialogue_repo.return_value.get_live = mock.AsyncMock(return_value=None)
            deletion_repo.return_value.get_tombstone = mock.AsyncMock(return_value=None)
            proof = await validate_controller_state(FakeStorage(), "dialogue")
            self.assertFalse(proof["passed"])

        class TombstoneStorage:
            async def read(self, callback: Any) -> Any:
                return 4 if callback is not None else None
        with mock.patch(__name__ + ".DialogueRepository") as dialogue_repo, mock.patch(__name__ + ".DeletionRepository") as deletion_repo:
            dialogue_repo.return_value.get_live = mock.AsyncMock(return_value=None)
            deletion_repo.return_value.get_tombstone = mock.AsyncMock(return_value=object())
            proof = await validate_controller_state(TombstoneStorage(), "dialogue")
            self.assertFalse(proof["passed"])

    async def test_delete_observer_captures_exact_result_without_retry(self) -> None:
        class Fake:
            async def delete(self, *, binding: ThreadBinding) -> Any:
                from codex_control.adapters.codex.thread_lifecycle import ThreadOperationResult
                return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)
        binding = ThreadBinding("p", "t")
        observer = ObservingDeleteLifecycle(Fake())
        result = await observer.delete(binding=binding)
        self.assertIs(observer.result, result)
        self.assertIs(observer.status, ThreadOperationStatus.DELETE_CONFIRMED)
        with self.assertRaises(AssertionError):
            await observer.delete(binding=binding)

    async def test_delete_unknown_is_observed_once_and_propagated_without_retry(self) -> None:
        class Fake:
            calls = 0

            async def delete(self, *, binding: ThreadBinding) -> Any:
                from codex_control.adapters.codex.thread_lifecycle import ThreadOperationResult
                self.calls += 1
                return ThreadOperationResult(ThreadOperationStatus.DELETE_UNKNOWN, binding)

        underlying = Fake()
        observer = ObservingDeleteLifecycle(underlying)
        binding = ThreadBinding("p", "t")
        result = await observer.delete(binding=binding)
        self.assertEqual(underlying.calls, 1)
        self.assertIs(observer.status, ThreadOperationStatus.DELETE_UNKNOWN)
        self.assertIs(observer.result, result)
        with self.assertRaises(AssertionError):
            await observer.delete(binding=binding)
        self.assertEqual(underlying.calls, 1)

    async def test_controller_path_authority_rejects_alternate_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-controller-path-") as directory:
            controller = Path(directory) / "controller.sqlite3"
            alternate = Path(directory) / "alternate.sqlite3"
            storage = await SqliteStorage.open(str(controller))
            try:
                self.assertTrue((await validate_controller_state(storage, "dialogue", controller))["controller_path_authority"])
                self.assertFalse((await validate_controller_state(storage, "dialogue", alternate))["passed"])
            finally:
                await storage.close()

    def test_budget_exact_and_each_over_budget_category(self) -> None:
        exact = {"model/list": 1, **REAL_BUDGET}
        assert_dynamic_budget(exact, 1)
        for method in REAL_BUDGET:
            changed = dict(exact)
            changed[method] += 1
            with self.assertRaises(BudgetError):
                assert_dynamic_budget(changed, 1)
        with self.assertRaises(BudgetError):
            assert_dynamic_budget(exact, 2)

    def test_model_list_over_budget_and_interrupt_reacquire_gate(self) -> None:
        with self.assertRaises(BudgetError):
            assert_dynamic_budget({**REAL_BUDGET, "model/list": 2}, 1)
        assert_no_reacquire(4, 4)
        with self.assertRaises(BudgetError):
            assert_no_reacquire(4, 5)

    def test_known_budget_with_unexpected_method_fails(self) -> None:
        with self.assertRaisesRegex(BudgetError, "UNEXPECTED_REQUEST_METHOD"):
            assert_dynamic_budget({**REAL_BUDGET, "thread/unknown": 1}, 1)

    async def test_malformed_delete_result_is_not_confirmed(self) -> None:
        class Fake:
            async def delete(self, *, binding: ThreadBinding) -> Any:
                return {"status": "DELETE_CONFIRMED"}
        observer = ObservingDeleteLifecycle(Fake())
        result = await observer.delete(binding=ThreadBinding("p", "t"))
        self.assertIsNone(observer.status)
        self.assertEqual(result, {"status": "DELETE_CONFIRMED"})


class BaselineAndSanitizationOfflineTests(unittest.TestCase):
    def test_unrelated_baseline_preserves_identity_allows_new_and_size_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-baseline-") as directory:
            home = Path(directory)
            (home / "sessions").mkdir(mode=0o700)
            unrelated = home / "sessions/unrelated"
            unrelated.write_bytes(b"safe")
            baseline = capture_unrelated_baseline(home, "TARGET")
            unrelated.write_bytes(b"safe but changed")
            (home / "sessions/new").write_bytes(b"new")
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])
            unrelated.unlink()
            self.assertFalse(reconcile_unrelated_baseline(baseline, home)["preserved"])

    def test_baseline_enforces_aggregate_per_file_and_file_count_limits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-baseline-bounds-") as directory:
            home = Path(directory)
            (home / "sessions").mkdir(mode=0o700)
            for index in range(3):
                (home / "sessions" / str(index)).write_bytes(b"safe")
            aggregate = capture_unrelated_baseline(home, "TARGET", max_bytes=5, chunk_bytes=2)
            self.assertTrue(aggregate.limit_exceeded)
            self.assertEqual(aggregate.bytes_scanned, 5)
            per_file = capture_unrelated_baseline(home, "TARGET", max_file_bytes=2)
            self.assertTrue(per_file.limit_exceeded)
            count = capture_unrelated_baseline(home, "TARGET", max_files=2)
            self.assertTrue(count.limit_exceeded)

    def test_exact_unrelated_path_identity_allows_mutation_and_new_files_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-baseline-identity-") as directory:
            home = Path(directory)
            (home / "sessions").mkdir(mode=0o700)
            original = home / "sessions/unrelated"
            original.write_bytes(b"safe")
            baseline = capture_unrelated_baseline(home, "TARGET")
            original.write_bytes(b"safe but changed")
            (home / "sessions/new").write_bytes(b"new")
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])

            renamed = home / "sessions/renamed"
            original.rename(renamed)
            self.assertFalse(reconcile_unrelated_baseline(baseline, home)["preserved"])

            original = home / "sessions/unrelated"
            original.write_bytes(b"replacement")
            replacement_baseline = capture_unrelated_baseline(home, "TARGET")
            replacement_path = home / "sessions/replacement-inode"
            replacement_path.write_bytes(b"new inode")
            original.unlink()
            replacement_path.rename(original)
            self.assertFalse(reconcile_unrelated_baseline(replacement_baseline, home)["preserved"])

    def test_baseline_replacement_during_scan_is_not_admitted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-baseline-replace-") as directory:
            home = Path(directory)
            (home / "sessions").mkdir(mode=0o700)
            path = home / "sessions/unrelated"
            replacement = home / "sessions/replacement"
            path.write_bytes(b"safe")
            replacement.write_bytes(b"replacement")
            original_read = os.read
            swapped = False

            def replacing_read(fd: int, size: int) -> bytes:
                nonlocal swapped
                data = original_read(fd, size)
                if data and not swapped:
                    swapped = True
                    os.replace(replacement, path)
                return data

            with mock.patch("os.read", side_effect=replacing_read):
                baseline = capture_unrelated_baseline(home, "TARGET")
            self.assertTrue(swapped)
            self.assertGreater(baseline.scan_errors, 0)
            self.assertEqual(baseline.identities, ())

    def test_postdelete_requires_safe_regular_file_authority(self) -> None:
        def capture(home: Path) -> tuple[Path, UnrelatedBaseline]:
            (home / "sessions").mkdir(mode=0o700)
            path = home / "sessions/unrelated"
            path.write_bytes(b"safe")
            return path, capture_unrelated_baseline(home, "TARGET")

        with tempfile.TemporaryDirectory(prefix="p7c6-postdelete-unchanged-") as directory:
            home = Path(directory)
            _, baseline = capture(home)
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])

        with tempfile.TemporaryDirectory(prefix="p7c6-postdelete-size-") as directory:
            home = Path(directory)
            path, baseline = capture(home)
            path.write_bytes(b"safe and changed")
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])

        with tempfile.TemporaryDirectory(prefix="p7c6-postdelete-mtime-") as directory:
            home = Path(directory)
            path, baseline = capture(home)
            os.utime(path, ns=(1, 2))
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])

        with tempfile.TemporaryDirectory(prefix="p7c6-postdelete-new-") as directory:
            home = Path(directory)
            path, baseline = capture(home)
            (path.parent / "new-unrelated").write_bytes(b"new")
            self.assertTrue(reconcile_unrelated_baseline(baseline, home)["preserved"])

        for mutation in ("rename", "delete", "new-inode", "hardlink", "unsafe-mode", "symlink", "special"):
            with tempfile.TemporaryDirectory(prefix=f"p7c6-postdelete-{mutation}-") as directory:
                home = Path(directory)
                path, baseline = capture(home)
                if mutation == "rename":
                    path.rename(path.with_name("renamed"))
                elif mutation == "delete":
                    path.unlink()
                elif mutation == "new-inode":
                    replacement = path.with_name("replacement-inode")
                    replacement.write_bytes(b"replacement")
                    path.unlink()
                    replacement.rename(path)
                elif mutation == "hardlink":
                    os.link(path, path.with_name("hardlink"))
                elif mutation == "unsafe-mode":
                    path.chmod(0o666)
                elif mutation == "symlink":
                    path.unlink()
                    path.symlink_to(path.with_name("target"))
                elif mutation == "special":
                    path.unlink()
                    os.mkfifo(path)
                self.assertFalse(reconcile_unrelated_baseline(baseline, home)["preserved"], mutation)

        if os.geteuid() == 0:
            with tempfile.TemporaryDirectory(prefix="p7c6-postdelete-owner-") as directory:
                home = Path(directory)
                path, baseline = capture(home)
                os.chown(path, 65534, 65534)
                try:
                    self.assertFalse(reconcile_unrelated_baseline(baseline, home)["preserved"])
                finally:
                    os.chown(path, 0, 0)


class JournalAndAsyncOwnershipOfflineTests(unittest.IsolatedAsyncioTestCase):
    class FailingJournal:
        def update(self, **fields: Any) -> None:
            raise OSError("journal unavailable")

    async def test_journal_failure_blocks_model_list_resume_and_delete_effects(self) -> None:
        for intent, result in (("MODEL_LIST_DISPATCH_INTENT", "MODEL_LIST_RESULT"), ("RESUME_DISPATCH_INTENT", "RESUME_RESULT"), ("DELETE_DISPATCH_INTENT", "DELETE_RESULT")):
            calls = 0

            async def effect() -> str:
                nonlocal calls
                calls += 1
                return "called"

            with self.assertRaises(OSError):
                await _journaled_effect(self.FailingJournal(), intent, result, effect)
            self.assertEqual(calls, 0, intent)

    async def test_primary_timeout_shutdowns_and_converges_the_same_task_once(self) -> None:
        release = asyncio.Event()
        dispatches = 0
        shutdowns = 0
        timed_out = False

        async def operation() -> str:
            nonlocal dispatches
            dispatches += 1
            await release.wait()
            return "FINITE"

        async def shutdown() -> None:
            nonlocal shutdowns
            shutdowns += 1
            release.set()

        owner = _create_owned_task(operation(), "convergent-operation")

        def record_timeout() -> None:
            nonlocal timed_out
            timed_out = True

        self.assertEqual(await _await_owned_task(owner, timeout=0.001, convergence_timeout=1, on_timeout=record_timeout, shutdown=shutdown), "FINITE")
        self.assertTrue(timed_out)
        self.assertEqual((dispatches, shutdowns), (1, 1))
        self.assertTrue(owner.task.done() and owner.terminalized)

    async def test_normal_task_completes_under_primary_bound(self) -> None:
        owner = _create_owned_task(asyncio.sleep(0, result="PRIMARY"), "primary-complete")
        started = asyncio.get_running_loop().time()
        self.assertEqual(await _await_owned_task(owner, timeout=1, convergence_timeout=1), "PRIMARY")
        self.assertLess(asyncio.get_running_loop().time() - started, 0.2)
        self.assertTrue(owner.terminalized)

    async def test_task_ignoring_primary_cancel_finishes_before_final_bound(self) -> None:
        async def operation() -> str:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await asyncio.sleep(0.01)
                return "FINISHED_AFTER_CANCEL"

        owner = _create_owned_task(operation(), "delayed-cancel-operation")
        self.assertEqual(await _await_owned_task(owner, timeout=0.001, convergence_timeout=0.02), "FINISHED_AFTER_CANCEL")
        self.assertTrue(owner.task.done() and owner.terminalized)

    async def test_task_refuses_all_bounds_and_helper_returns_finitely(self) -> None:
        release = asyncio.Event()

        async def operation() -> str:
            while True:
                try:
                    await release.wait()
                    return "RELEASED"
                except asyncio.CancelledError:
                    continue

        owner = _create_owned_task(operation(), "nonconverging-operation")
        started = asyncio.get_running_loop().time()
        with self.assertRaises(TaskNonconvergedError) as raised:
            await _await_owned_task(owner, timeout=0.001, convergence_timeout=0.002)
        elapsed = asyncio.get_running_loop().time() - started
        self.assertLess(elapsed, 0.2)
        self.assertIs(raised.exception.owner, owner)
        self.assertTrue(owner.nonconverged and not owner.terminalized)
        release.set()
        await asyncio.wait_for(asyncio.shield(owner.task), timeout=0.2)

    async def test_approval_timeout_cancels_exact_bridge_and_cannot_emit_late_allow(self) -> None:
        allow_emitted = []
        gate = asyncio.Event()

        async def bridge() -> None:
            await gate.wait()
            allow_emitted.append("ALLOW")

        owner = _create_owned_task(bridge(), "approval-bridge")
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(owner.task), timeout=0.001)
        await _cancel_owned_approval(owner, timeout=1)
        gate.set()
        await asyncio.sleep(0)
        self.assertEqual(allow_emitted, [])
        self.assertTrue(owner.task.done() and owner.terminalized)

    async def test_turn4_start_failure_terminalizes_precreated_approval_bridge(self) -> None:
        allow_emitted: list[str] = []
        gate = asyncio.Event()

        async def bridge() -> None:
            try:
                await gate.wait()
                allow_emitted.append("ALLOW")
            except asyncio.CancelledError:
                raise

        async def failing_start() -> None:
            raise RuntimeError("TURN4_START_FAILED")

        approval_owner = _create_owned_task(bridge(), "turn4-approval-bridge")
        start_owner = _create_owned_task(failing_start(), "turn4-start")
        with self.assertRaises(RuntimeError):
            await _await_owned_task(start_owner, timeout=1, convergence_timeout=1)
        await _cancel_owned_approval(approval_owner, timeout=1, final_timeout=1)
        gate.set()
        await asyncio.sleep(0)
        self.assertTrue(approval_owner.task.done() and approval_owner.terminalized)
        self.assertEqual(allow_emitted, [])

    async def test_interrupt_failure_terminalizes_turn5_waiter_after_owned_shutdown(self) -> None:
        waiter_gate = asyncio.Event()
        shutdown_calls = 0

        async def terminal_waiter() -> str:
            await waiter_gate.wait()
            return "TERMINAL"

        async def failing_interrupt() -> None:
            raise RuntimeError("INTERRUPT_FAILED")

        class Manager:
            async def shutdown_all(self) -> None:
                nonlocal shutdown_calls
                shutdown_calls += 1

        terminal_owner = _create_owned_task(terminal_waiter(), "turn5-terminal-waiter")
        interrupt_owner = _create_owned_task(failing_interrupt(), "interrupt")
        with self.assertRaises(RuntimeError):
            await _await_owned_task(interrupt_owner, timeout=1, convergence_timeout=1)
        await _bounded_shutdown(Manager(), timeout=1, final_timeout=1)
        await _cancel_owned_approval(terminal_owner, timeout=1, final_timeout=1)
        waiter_gate.set()
        self.assertEqual(shutdown_calls, 1)
        self.assertTrue(terminal_owner.task.done() and terminal_owner.terminalized)

    async def test_delete_timeout_retains_one_owned_task_and_no_second_dispatch(self) -> None:
        release = asyncio.Event()
        calls = 0

        async def delete() -> str:
            nonlocal calls
            calls += 1
            while True:
                try:
                    await release.wait()
                    return "DELETE_UNKNOWN"
                except asyncio.CancelledError:
                    continue

        owner = _create_owned_task(delete(), "single-delete")
        with self.assertRaises(TaskNonconvergedError):
            await _await_owned_task(owner, timeout=0.001, convergence_timeout=0.001, shutdown=lambda: asyncio.sleep(0))
        self.assertEqual(calls, 1)
        self.assertEqual(owner.name, "single-delete")
        self.assertTrue(owner.nonconverged and not owner.terminalized)
        release.set()
        self.assertEqual(await asyncio.wait_for(asyncio.shield(owner.task), timeout=0.2), "DELETE_UNKNOWN")

    def test_timeout_helpers_have_no_unbounded_join_primitive(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        unbounded_join_names = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "asyncio"
                and node.func.attr in {"gather", "join"}
            ):
                unbounded_join_names.append(node.func.attr)
        self.assertEqual(unbounded_join_names, [])


class ProcessWatchdogOfflineTests(unittest.TestCase):
    def _child_environment(self, path: Path) -> dict[str, str]:
        return {"CODEXCONTROL_P7C6_SYNTHETIC_RECOVERY": str(path)}

    def test_normal_synthetic_child_exits_normally(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-watchdog-normal-") as directory:
            recovery = Path(directory) / "recovery.json"
            result = launch_dedicated_continuation_child(
                mode="synthetic-normal", child_env=self._child_environment(recovery),
                hard_deadline=1, terminate_grace=0.1, kill_grace=0.1,
            )
            self.assertEqual(result["status"], "PROCESS_COMPLETED")
            self.assertEqual(result["child_process_count"], 1)
            self.assertEqual(result["second_child_started"], "NO")
            self.assertTrue(result["parent_returned_finitely"])
            self.assertEqual(json.loads(recovery.read_text(encoding="utf-8"))["status"], "NORMAL_CHILD_COMPLETED")

    def test_cancellation_resistant_child_is_killed_once_and_recovery_survives(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-watchdog-stubborn-") as directory:
            recovery = Path(directory) / "recovery.json"
            result = launch_dedicated_continuation_child(
                mode="synthetic-stubborn", child_env=self._child_environment(recovery),
                hard_deadline=0.5, terminate_grace=0.05, kill_grace=0.2,
            )
            self.assertEqual(result["status"], "PROCESS_WATCHDOG_TIMEOUT")
            self.assertEqual(result["child_process_count"], 1)
            self.assertEqual(result["second_child_started"], "NO")
            self.assertTrue(result["parent_returned_finitely"])
            self.assertTrue(result["child_terminated"])
            self.assertEqual(json.loads(recovery.read_text(encoding="utf-8"))["status"], "STUBBORN_CHILD_STARTED")

    def test_kill_grace_is_finite_and_launcher_has_one_process_creation_site(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-watchdog-grace-") as directory:
            recovery = Path(directory) / "recovery.json"
            started = time.monotonic()
            result = launch_dedicated_continuation_child(
                mode="synthetic-stubborn", child_env=self._child_environment(recovery),
                hard_deadline=0.2, terminate_grace=0.05, kill_grace=0.05,
            )
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(result["status"], "PROCESS_WATCHDOG_TIMEOUT")
            self.assertTrue(result["child_terminated"])
        source = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        launcher = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == "launch_dedicated_continuation_child")
        self.assertEqual(sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "Popen" for node in ast.walk(launcher)), 1)
        self.assertFalse(any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(launcher)))

    def test_synthetic_child_entrypoints_cannot_call_real_codex_adapters(self) -> None:
        source = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        names = {"acquire", "resume", "start_turn", "interrupt_turn", "delete", "request", "respond_server_request"}
        functions = [
            node for node in source.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name in {"_synthetic_normal_child", "_synthetic_cancellation_resistant_child", "_synthetic_turn4_approval_child"}
        ]
        self.assertEqual(len(functions), 3)
        for function in functions:
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, names, function.name)


class Repair4FailureEdgeOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def test_turn5_nonconvergence_retains_paths_and_dispatches_once(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-turn5-uncertain-") as directory:
            root = Path(directory)
            journal = ContinuationRecoveryJournal.create(root / "journal.json", {"status": "TURN5_START_DISPATCHED"})
            gate = asyncio.Event()
            dispatches = 0

            async def turn5_start() -> str:
                nonlocal dispatches
                dispatches += 1
                while True:
                    try:
                        await gate.wait()
                        return "CONFIRMED"
                    except asyncio.CancelledError:
                        continue

            class Manager:
                shutdown_calls = 0

                async def shutdown_all(self) -> None:
                    self.shutdown_calls += 1

            manager = Manager()
            owner = _create_owned_task(turn5_start(), "turn5-start")
            retention = {"forensic_retained": False}
            with self.assertRaises(TaskNonconvergedError):
                await _turn5_start_with_retention(
                    owner, journal=journal, manager=manager, retention=retention,
                    timeout=0.01, convergence_timeout=0.01,
                )
            self.assertTrue(retention["forensic_retained"])
            self.assertEqual(dispatches, 1)
            self.assertGreaterEqual(manager.shutdown_calls, 1)
            record = _read_private_json(root / "journal.json")
            self.assertEqual(record["TURN5_START_RESULT"], "UNKNOWN")
            self.assertEqual(record["failure_stage"], "TURN5_START_UNCERTAIN")
            self.assertTrue((root / "journal.json").exists())
            gate.set()
            await asyncio.wait_for(asyncio.shield(owner.task), timeout=0.2)

    async def test_turn4_approval_nonconvergence_shuts_runtime_and_blocks_late_allow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-turn4-approval-uncertain-") as directory:
            root = Path(directory)
            journal = ContinuationRecoveryJournal.create(root / "journal.json", {"status": "TURN4_START_DISPATCHED"})
            allow_emitted: list[str] = []
            shutdown_gate = asyncio.Event()
            approval_gate = asyncio.Event()
            turn4_start_dispatches = 1

            async def approval() -> None:
                while True:
                    try:
                        await approval_gate.wait()
                        if not shutdown_gate.is_set():
                            allow_emitted.append("ALLOW")
                        return
                    except asyncio.CancelledError:
                        if shutdown_gate.is_set():
                            return
                        continue

            class Manager:
                shutdown_calls = 0

                async def shutdown_all(self) -> None:
                    self.shutdown_calls += 1
                    shutdown_gate.set()

            manager = Manager()
            approval_owner = _create_owned_task(approval(), "turn4-approval")
            await asyncio.sleep(0)
            retention = {"forensic_retained": False}
            with self.assertRaises(TaskNonconvergedError):
                await _turn4_start_failure_with_approval(
                    RuntimeError("TURN4_START_FAILED"), approval_owner, journal=journal, manager=manager,
                    retention=retention, timeout=0.01, final_timeout=0.01,
                )
            self.assertTrue(retention["forensic_retained"])
            self.assertEqual(turn4_start_dispatches, 1)
            self.assertGreaterEqual(manager.shutdown_calls, 1)
            approval_gate.set()
            approval_owner.task.cancel()
            await asyncio.wait_for(asyncio.shield(approval_owner.task), timeout=0.2)
            self.assertEqual(allow_emitted, [])
            record = _read_private_json(root / "journal.json")
            self.assertEqual(record["failure_stage"], "APPROVAL_BRIDGE_NONCONVERGED")
            self.assertEqual(record["TURN4_START_RESULT"], "FAILED")

    def test_turn4_process_watchdog_fixture_has_one_child_and_no_allow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-turn4-child-") as directory:
            recovery = Path(directory) / "journal.json"
            result = launch_dedicated_continuation_child(
                mode="synthetic-turn4-approval",
                child_env={"CODEXCONTROL_P7C6_SYNTHETIC_RECOVERY": str(recovery)},
                hard_deadline=0.5, terminate_grace=0.05, kill_grace=0.2,
            )
            self.assertEqual(result["status"], "PROCESS_WATCHDOG_TIMEOUT")
            self.assertEqual(result["child_process_count"], 1)
            self.assertEqual(result["second_child_started"], "NO")
            self.assertTrue(result["parent_returned_finitely"] and result["child_terminated"])
            record = _read_private_json(recovery)
            self.assertEqual(record["ALLOW_EMITTED"], 0)
            self.assertEqual(record["TURN4_START_DISPATCHES"], 1)
            self.assertEqual(record["SECOND_TURN4_START"], 0)
            self.assertGreaterEqual(record["RUNTIME_SHUTDOWN_CALLS"], 1)

    async def test_success_path_rejects_nonterminal_owned_task(self) -> None:
        owner = _create_owned_task(asyncio.sleep(0.2), "nonterminal-success-owner")
        with self.assertRaisesRegex(AssertionError, "SUCCESS_REQUIRES_ALL_OWNERS_TERMINAL"):
            _require_all_owned_tasks_terminal({owner.name: owner})
        owner.task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await owner.task


class FailureRetentionOfflineTests(unittest.TestCase):
    def test_ambiguous_approval_does_not_erase_forensic_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-retain-approval-") as directory:
            root = Path(directory)
            workdir = root / "workdir"
            workdir.mkdir(mode=0o700)
            sentinel = workdir / "sentinel"
            sentinel.write_bytes(b"forensic")
            journal = root / "journal.json"
            journal.write_text(json.dumps({"status": "RESPONSE_UNKNOWN"}), encoding="utf-8")
            journal.chmod(0o600)
            self.assertTrue(workdir.exists() and sentinel.exists() and journal.exists())

    def test_ambiguous_turn4_turn5_and_delete_preserve_forensic_state(self) -> None:
        for prefix in ("turn4", "turn5", "delete"):
            with tempfile.TemporaryDirectory(prefix="p7c6-retain-") as directory:
                root = Path(directory)
                workdir = root / f"{prefix}-workdir"
                workdir.mkdir(mode=0o700)
                sentinel = root / f"{prefix}-sentinel"
                sentinel.write_bytes(b"forensic")
                recovery = root / f"{prefix}-recovery.json"
                recovery.write_text(json.dumps({"status": "UNKNOWN"}), encoding="utf-8")
                recovery.chmod(0o600)
                self.assertTrue(workdir.is_dir() and sentinel.is_file() and recovery.is_file())

    def test_sanitization_is_after_gates_and_never_retries_delete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-sanitize-gate-") as directory:
            path = Path(directory) / "record.json"
            raw = {"raw_thread": "THREAD-X", "raw_marker": "MARKER-X"}
            path.write_text(json.dumps(raw), encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaises(SanitizationError):
                sanitize_only_after_final_gates(False, {path: {"status": "SANITIZED_COMPLETED"}})
            self.assertEqual(_read_private_json(path), raw)

    def test_sanitization_failure_does_not_call_delete_again(self) -> None:
        delete_calls = 0

        def confirmed_delete() -> None:
            nonlocal delete_calls
            delete_calls += 1

        confirmed_delete()
        with tempfile.TemporaryDirectory(prefix="p7c6-sanitize-failure-") as directory:
            path = Path(directory) / "record.json"
            path.write_text("not-json", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaises(SanitizationError):
                sanitize_only_after_final_gates(True, {path: {"status": "SANITIZED_COMPLETED"}})
        self.assertEqual(delete_calls, 1)

    def test_verified_turn4_removes_only_exact_owned_sentinel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-sentinel-ownership-") as directory:
            root = Path(directory)
            owned = root / "owned-sentinel"
            unrelated = root / "unrelated-artifact"
            owned.write_bytes(b"EXPECTED")
            unrelated.write_bytes(b"KEEP")
            self.assertTrue(_safe_exact_file(owned, b"EXPECTED"))
            owned.unlink()
            self.assertFalse(owned.exists())
            self.assertTrue(unrelated.exists())

    def test_success_sanitization_removes_raw_values_and_keeps_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c6-sanitize-") as directory:
            path = Path(directory) / "record.json"
            path.write_text(json.dumps({"raw_thread": "THREAD-X", "raw_marker": "MARKER-X"}), encoding="utf-8")
            path.chmod(0o600)
            digest = _sha256("MARKER-X")
            sanitize_only_after_final_gates(True, {path: {"status": "SANITIZED_COMPLETED", "marker_sha256": [digest]}})
            value = _read_private_json(path)
            self.assertNotIn("THREAD-X", json.dumps(value))
            self.assertEqual(value["marker_sha256"], [digest])


class ContinuationStaticGateTests(unittest.TestCase):
    def test_no_new_thread_path_and_real_gate_is_disabled(self) -> None:
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertNotIn("thread_lifecycle." + "start(", source.replace('"thread_lifecycle." + "start("', ""))
        self.assertNotEqual(os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION"), AUTHORIZATION)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "start":
                self.assertFalse(isinstance(node.func.value, ast.Name) and node.func.value.id == "CodexThreadLifecycleAdapter")


class P7C6SameThreadContinuationAcceptance(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(os.environ.get("CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION") == AUTHORIZATION, "gated real P7.C6 same-thread continuation")
    async def test_real_same_thread_continuation(self) -> None:
        result = launch_dedicated_continuation_child(mode="real")
        self.assertEqual(result["status"], "PROCESS_COMPLETED", result)
        self.assertEqual(result["returncode"], 0, result)
        self.assertEqual(result["child_process_count"], 1)
        print("P7C6_CONTINUATION_PROCESS_RESULT=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--codexcontrol-p7c6-child":
        raise SystemExit(_dedicated_child_main(sys.argv[2]))
    unittest.main()
