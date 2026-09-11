"""P7.C8 deny-only approval-probe preparation.

This module is deliberately test-only.  It prepares a future fresh-thread
observation harness, but ordinary execution cannot acquire a runtime and the
real method is gated by three unset future authorities.  The operator below
has one decision: DENY.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import inspect
import json
import os
import re
import secrets
import shlex
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalError,
    ApprovalHandlingStatus,
    ApprovalKind,
    ApprovalRequest,
    CodexApprovalBridge,
    COMMAND,
)
from codex_control.adapters.codex.model_catalog import CodexModelCatalogAdapter
from codex_control.adapters.codex.runtime import CodexRuntimeManager, RuntimeErrorSafe
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import CodexTurnLifecycleAdapter, TurnStartStatus
from codex_control.adapters.codex.isolation import IsolationPathAuthority
from codex_control.domain import CodexProfile
from codex_control.adapters.codex.protocol import InboundServerRequest


ARCHITECT_BASE_SHA = "2b6e514f419e263af62530232f8220cd4079f953"
ARCHITECT_BASE_TREE = "6d774ecf66e38f82b1b5ac530205919c2850780f"
AUTHORIZED_ENV = "AUTHORIZED_P7C8_DENY_ONLY_APPROVAL_PROBE_2026_09_11"
EXPECTED_HEAD_ENV = "CODEXCONTROL_P7C8_PROBE_EXPECTED_HEAD"
EXPECTED_TREE_ENV = "CODEXCONTROL_P7C8_PROBE_EXPECTED_TREE"
REAL_PROBE_LATCH = Path("/root/.codexcontrol/p7c8-deny-only-approval-probe-ledger.json")
REAL_PROBE_RESULT = Path("/root/.codexcontrol/p7c8-deny-only-approval-probe-result.json")
REAL_PROBE_OUTCOME = Path("/root/.codexcontrol/p7c8-deny-only-approval-probe-outcome.json")
MAX_PROBE_APPROVAL_REQUESTS = 3
MAX_AUTHORITY_BYTES = 16 * 1024
MAX_WIRE_COMMAND_CHARS = 4096
MAX_WIRE_VECTOR_TOKENS = 64
MAX_SEQUENCE = MAX_PROBE_APPROVAL_REQUESTS
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

OUTCOME_APPROVAL_FIRST = "APPROVAL_REQUEST_OBSERVED_BEFORE_TERMINAL"
OUTCOME_TERMINAL_FIRST = "TURN_TERMINAL_BEFORE_APPROVAL_REQUEST"
OUTCOME_AMBIGUOUS = "APPROVAL_AND_TERMINAL_RACE_AMBIGUOUS"
OUTCOME_PROTOCOL = "PROTOCOL_TERMINAL"
OUTCOME_WATCHDOG = "WATCHDOG_TIMEOUT"
OUTCOME_LIMIT = "PROBE_APPROVAL_REQUEST_LIMIT_EXCEEDED"
OUTCOME_NONCONVERGENT = "WATCHDOG_TIMEOUT"

# These are future-real authorities.  The ordinary test process never uses
# them to start Codex; keeping them named and finite makes the future path
# auditable before a separate authorization supplies its environment gate.
PROBE_RUNTIME_ACQUIRE_TIMEOUT = 45.0
PROBE_MODEL_LIST_TIMEOUT = 5.0
PROBE_THREAD_START_TIMEOUT = 5.0
PROBE_TURN_START_TIMEOUT = 5.0
P7C8_CANDIDATE_SLEEP_SECONDS = 30.0
PROBE_OBSERVATION_MARGIN_SECONDS = 60.0
PROBE_OBSERVATION_TIMEOUT = 100.0
PROBE_APPROVAL_RESPONSE_TIMEOUT = 5.0
PROBE_RUNTIME_SHUTDOWN_TIMEOUT = 5.0
PROBE_CHILD_RESULT_TIMEOUT = 2.0
PROBE_TERM_GRACE_SECONDS = 2.0
PROBE_KILL_GRACE_SECONDS = 2.0
NORMAL_PATH_INTERNAL_WORST_CASE_SECONDS = sum((
    PROBE_RUNTIME_ACQUIRE_TIMEOUT,
    PROBE_MODEL_LIST_TIMEOUT,
    PROBE_THREAD_START_TIMEOUT,
    PROBE_TURN_START_TIMEOUT,
    PROBE_OBSERVATION_TIMEOUT,
    PROBE_APPROVAL_RESPONSE_TIMEOUT * MAX_PROBE_APPROVAL_REQUESTS,
    PROBE_RUNTIME_SHUTDOWN_TIMEOUT,
    PROBE_CHILD_RESULT_TIMEOUT,
    PROBE_TERM_GRACE_SECONDS,
    PROBE_KILL_GRACE_SECONDS,
))
P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS = 1.0
FAILED_ACQUIRE_INTERNAL_WORST_CASE_SECONDS = sum((
    PROBE_RUNTIME_ACQUIRE_TIMEOUT,
    12.0,
    P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS,
    PROBE_CHILD_RESULT_TIMEOUT,
    PROBE_TERM_GRACE_SECONDS,
    PROBE_KILL_GRACE_SECONDS,
))
PROBE_INTERNAL_WORST_CASE_SECONDS = NORMAL_PATH_INTERNAL_WORST_CASE_SECONDS
PROBE_WATCHDOG_MARGIN_SECONDS = 15.0
PROBE_WATCHDOG_HARD_DEADLINE = 205.0

# P7.C8 frozen real-mode authorities.  Synthetic tests may inject smaller values.
PROFILE_ID = "p7c8-fresh-probe"
SAFE_RUNTIME_CATEGORIES = frozenset({
    "capability_mismatch", "manager_shutting_down", "unknown_profile", "profile_reserved",
    "profile_stopping", "unresolved_process", "storage_boundary_invalid", "executable_invalid",
    "process_streams_missing", "initialize_failed", "initialize_timeout", "startup_failed",
    "kill_reap_timeout",
})
SAFE_CATEGORY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED = "SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED"
P7C8_RUNTIME_ACQUIRE_TIMEOUT_SECONDS = PROBE_RUNTIME_ACQUIRE_TIMEOUT
P7C8_RUNTIME_ACQUIRE_CLEANUP_TIMEOUT_SECONDS = 12.0
P7C8_KNOWN_NAMED_STARTUP_BOUND_SECONDS = 24.0
KNOWN_NAMED_STARTUP_BOUND_SECONDS = P7C8_KNOWN_NAMED_STARTUP_BOUND_SECONDS
P7C8_RUNTIME_ACQUIRE_NAMED_STAGE_MARGIN_SECONDS = 15.0
P7C8_OBSERVATION_MARGIN_SECONDS = PROBE_OBSERVATION_MARGIN_SECONDS
P7C8_OBSERVATION_TIMEOUT_SECONDS = PROBE_OBSERVATION_TIMEOUT
P7C8_MODEL_LIST_TIMEOUT_SECONDS = PROBE_MODEL_LIST_TIMEOUT
P7C8_THREAD_START_TIMEOUT_SECONDS = PROBE_THREAD_START_TIMEOUT
P7C8_TURN_START_TIMEOUT_SECONDS = PROBE_TURN_START_TIMEOUT
P7C8_APPROVAL_RESPONSE_TIMEOUT_SECONDS = PROBE_APPROVAL_RESPONSE_TIMEOUT
P7C8_RUNTIME_SHUTDOWN_TIMEOUT_SECONDS = PROBE_RUNTIME_SHUTDOWN_TIMEOUT
P7C8_CHILD_RESULT_TIMEOUT_SECONDS = PROBE_CHILD_RESULT_TIMEOUT
P7C8_TERM_GRACE_SECONDS = PROBE_TERM_GRACE_SECONDS
P7C8_KILL_GRACE_SECONDS = PROBE_KILL_GRACE_SECONDS
P7C8_INTERNAL_WORST_CASE_SECONDS = PROBE_INTERNAL_WORST_CASE_SECONDS
P7C8_WATCHDOG_MARGIN_SECONDS = PROBE_WATCHDOG_MARGIN_SECONDS
P7C8_WATCHDOG_HARD_DEADLINE_SECONDS = PROBE_WATCHDOG_HARD_DEADLINE

CHILD_RESULT_FILENAME = "probe-child-result.json"
CHILD_PRE_RESULT = "CHILD_PRE_RESULT"
PARENT_POST_QUIESCENCE = "PARENT_POST_QUIESCENCE"
CHILD_RETURN_COMPLETED = "CHILD_COMPLETED"
CHILD_RETURN_NONZERO = "CHILD_NONZERO"
CHILD_RETURN_TIMEOUT = "CHILD_TIMEOUT"
CHILD_GROUP_RESIDUAL = "CHILD_GROUP_RESIDUAL"
CHILD_GROUP_SCAN_ERROR = "CHILD_GROUP_SCAN_ERROR"

WIRE_RESPONSE_RETURNED = "RESPONSE_RETURNED"
WIRE_RESPONSE_UNKNOWN = "RESPONSE_UNKNOWN"

BOUNDARY_DRIFT_NONE = "BOUNDARY_DRIFT_NONE"
BOUNDARY_DRIFT_DETECTED = "BOUNDARY_DRIFT_DETECTED"

PARENT_EXECUTION_CLASSES = frozenset({
    CHILD_RETURN_COMPLETED,
    CHILD_RETURN_NONZERO,
    CHILD_RETURN_TIMEOUT,
    CHILD_GROUP_RESIDUAL,
    CHILD_GROUP_SCAN_ERROR,
    "CHILD_RESULT_MISSING_OR_INVALID",
    "PARENT_BOUNDARY_INVALID_OR_DRIFTED",
    "PARENT_FINAL_RESULT_CONFIRMED",
})
CHILD_EXECUTION_CLASSES = frozenset({
    CHILD_RETURN_COMPLETED,
    CHILD_RETURN_NONZERO,
    CHILD_RETURN_TIMEOUT,
    CHILD_GROUP_RESIDUAL,
    CHILD_GROUP_SCAN_ERROR,
})
PARENT_OUTCOME_WATCHDOG_STATUSES = frozenset({
    "PROCESS_COMPLETED", "PROCESS_WATCHDOG_TIMEOUT", "PROCESS_GROUP_NOT_QUIESCENT",
    "PROCESS_GROUP_SCAN_ERROR", "NOT_ESTABLISHED",
})
PARENT_OUTCOME_BOUNDARY_CLASSES = frozenset({
    "BOUNDARY_ONLY_EXPECTED_MUTATION", "UNEXPECTED_PROBE_MUTATION", "BOUNDARY_NOT_PROVED",
})
PARENT_OUTCOME_KEYS = frozenset({
    "format", "accepted_source_sha", "accepted_source_tree", "execution_class", "watchdog_status",
    "child_returncode_class", "child_result_present", "child_result_valid", "parent_boundary_class",
    "boundary_drift_class", "group_active_count", "group_zombie_count", "group_scan_errors",
    "term_group_signal_count", "kill_group_signal_count", "one_child_count", "second_child_started",
    "retry_count", "global_latch_present", "normal_final_result_present", "child_result_discovery_class",
    "runtime_acquire_initial_result", "runtime_acquire_result", "runtime_acquire_error_category",
    "runtime_acquire_cleanup_result", "runtime_acquire_cleanup_error_category",
})
CHILD_RESULT_DISCOVERY_CLASSES = frozenset({
    "CHILD_RESULT_DISCOVERY_CONFIRMED",
    "CHILD_RESULT_DISCOVERY_MISSING",
    "CHILD_RESULT_DISCOVERY_AMBIGUOUS",
    "CHILD_RESULT_DISCOVERY_UNREADABLE",
})

SENTINEL_EXACT_ARG = "EXACT_ARG_TOKEN"
SENTINEL_EMBEDDED = "EMBEDDED_OCCURRENCE"
SENTINEL_ABSENT = "ABSENT"
SENTINEL_VECTOR_UNKNOWN = "VECTOR_NOT_ESTABLISHED"


def _sha256(value: str | bytes) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _private_directory(path: Path, mode: int = 0o700) -> bool:
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


def _private_regular(path: Path, mode: int = 0o600) -> bool:
    try:
        value = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISREG(value.st_mode)
        and value.st_uid == 0
        and value.st_gid == 0
        and value.st_nlink == 1
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
        count = os.write(fd, payload[offset:])
        if count <= 0:
            raise OSError("short write")
        offset += count


def _private_json_payload(value: Mapping[str, Any], maximum: int = MAX_AUTHORITY_BYTES) -> bytes:
    payload = (json.dumps(dict(value), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > maximum:
        raise ValueError("AUTHORITY_RECORD_OVERSIZE")
    return payload


def write_exclusive_private_json(path: Path, value: Mapping[str, Any], *, maximum: int = MAX_AUTHORITY_BYTES) -> None:
    """Create one root-only authority record, never overwriting an existing one."""
    if not _private_directory(path.parent):
        raise ValueError("AUTHORITY_PARENT_INVALID")
    payload = _private_json_payload(value, maximum)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        _write_all(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_parent(path)
    if not _private_regular(path):
        raise ValueError("AUTHORITY_RECORD_INVALID_AFTER_CREATE")


def read_bounded_private_json(path: Path, *, maximum: int = MAX_AUTHORITY_BYTES) -> dict[str, Any]:
    """Read a root-only record through a no-follow descriptor with identity checks."""
    if not _private_regular(path):
        raise ValueError("AUTHORITY_RECORD_INVALID")
    before_path = path.lstat()
    if before_path.st_size > maximum:
        raise ValueError("AUTHORITY_RECORD_OVERSIZE")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(path), flags)
    chunks: list[bytes] = []
    total = 0
    try:
        before_fd = os.fstat(fd)
        if (before_fd.st_dev, before_fd.st_ino, before_fd.st_size) != (before_path.st_dev, before_path.st_ino, before_path.st_size):
            raise ValueError("AUTHORITY_IDENTITY_CHANGED")
        while True:
            chunk = os.read(fd, min(4096, maximum - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise ValueError("AUTHORITY_RECORD_OVERSIZE")
            chunks.append(chunk)
        after_fd = os.fstat(fd)
        after_path = path.lstat()
        metadata = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mode, value.st_uid, value.st_gid, value.st_nlink, value.st_mtime_ns, value.st_ctime_ns)
        if metadata(after_fd) != metadata(before_fd):
            raise ValueError("AUTHORITY_IDENTITY_CHANGED")
        if metadata(after_path) != metadata(before_path):
            raise ValueError("AUTHORITY_PATH_REPLACED")
    finally:
        os.close(fd)
    try:
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("AUTHORITY_RECORD_MALFORMED") from error
    if not isinstance(value, dict):
        raise ValueError("AUTHORITY_RECORD_MALFORMED")
    return value


class RecoveryJournal:
    """Root-only append journal with fail-closed effect sequencing.

    The journal is JSONL so every intent/result is durable independently.  It
    deliberately accepts only sanitized scalar values; raw protocol values
    never have a route into the journal or into Git evidence.
    """

    def __init__(self, path: Path, *, source_sha: str, source_tree: str) -> None:
        if not _private_directory(path.parent):
            raise ValueError("JOURNAL_PARENT_INVALID")
        if not re.fullmatch(r"[0-9a-f]{40}", source_sha) or not re.fullmatch(r"[0-9a-f]{40}", source_tree):
            raise ValueError("JOURNAL_SOURCE_INVALID")
        self.path = path
        self._original_identity: tuple[int, int] | None = None
        self._identity_fd: int | None = None
        self._append({"event": "SOURCE_GATE", "result": "PASS", "source_sha": source_sha, "source_tree": source_tree})

    @staticmethod
    def _safe(value: Any) -> bool:
        if value is None or isinstance(value, (bool, int, float)):
            return True
        if isinstance(value, str):
            return "\0" not in value and len(value) <= 256 and not any(
                marker in value.lower() for marker in ("command:", "thread_id", "turn_id", "sentinel_path", "prompt")
            )
        if isinstance(value, (tuple, list)):
            return len(value) <= 64 and all(RecoveryJournal._safe(item) for item in value)
        if isinstance(value, dict):
            return len(value) <= 32 and all(
                isinstance(key, str) and re.fullmatch(r"[A-Z0-9_]+", key) and RecoveryJournal._safe(item)
                for key, item in value.items()
            )
        return False

    def _append(self, record: Mapping[str, Any]) -> None:
        if set(record) - {
            "event", "result", "source_sha", "source_tree", "attempt", "request_count", "status", "class",
            "kind", "thread_match", "turn_match", "cwd_match", "wire_hash", "wire_command_sha256", "category",
            "sentinel_reference_class",
        }:
            raise ValueError("JOURNAL_FIELD_UNSAFE")
        if not all(self._safe(value) for value in record.values()):
            raise ValueError("JOURNAL_VALUE_UNSAFE")
        payload = (json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(payload) > 4096:
            raise ValueError("JOURNAL_RECORD_OVERSIZE")
        initial_create = self._original_identity is None
        if initial_create:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            fd = os.open(str(self.path), flags, 0o600)
        else:
            before_path = self._validated_path_identity()
            flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            try:
                fd = os.open(str(self.path), flags)
            except FileNotFoundError as error:
                raise ValueError("JOURNAL_PATH_MISSING") from error
        try:
            before_fd = os.fstat(fd)
            self._require_journal_metadata(before_fd)
            if not initial_create and (before_fd.st_dev, before_fd.st_ino) != self._original_identity:
                raise ValueError("JOURNAL_IDENTITY_CHANGED")
            current_path = self.path.lstat()
            self._require_journal_metadata(current_path)
            if (before_fd.st_dev, before_fd.st_ino) != (current_path.st_dev, current_path.st_ino):
                raise ValueError("JOURNAL_PATH_IDENTITY_CHANGED")
            _write_all(fd, payload)
            os.fsync(fd)
            after_fd = os.fstat(fd)
            path_stat = self.path.lstat()
            self._require_journal_metadata(after_fd)
            self._require_journal_metadata(path_stat)
            expected_identity = self._original_identity or (before_fd.st_dev, before_fd.st_ino)
            if (
                (after_fd.st_dev, after_fd.st_ino) != expected_identity
                or (path_stat.st_dev, path_stat.st_ino) != expected_identity
            ):
                raise ValueError("JOURNAL_PATH_IDENTITY_CHANGED")
        finally:
            os.close(fd)
        if initial_create:
            final_path = self.path.lstat()
            self._require_journal_metadata(final_path)
            self._original_identity = (final_path.st_dev, final_path.st_ino)
            identity_fd = os.open(
                str(self.path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
            )
            try:
                identity_stat = os.fstat(identity_fd)
                self._require_journal_metadata(identity_stat)
                if (identity_stat.st_dev, identity_stat.st_ino) != self._original_identity:
                    raise ValueError("JOURNAL_IDENTITY_CHANGED")
            except BaseException:
                os.close(identity_fd)
                raise
            self._identity_fd = identity_fd
            _fsync_parent(self.path)

    @staticmethod
    def _require_journal_metadata(value: os.stat_result) -> None:
        if (
            not stat.S_ISREG(value.st_mode)
            or value.st_uid != 0 or value.st_gid != 0
            or stat.S_IMODE(value.st_mode) != 0o600
            or value.st_nlink != 1
        ):
            raise ValueError("JOURNAL_AUTHORITY_INVALID")

    def _validated_path_identity(self) -> os.stat_result:
        try:
            value = self.path.lstat()
        except FileNotFoundError as error:
            raise ValueError("JOURNAL_PATH_MISSING") from error
        except OSError as error:
            raise ValueError("JOURNAL_PATH_UNREADABLE") from error
        self._require_journal_metadata(value)
        if self._original_identity != (value.st_dev, value.st_ino):
            raise ValueError("JOURNAL_IDENTITY_CHANGED")
        if self._identity_fd is not None:
            identity_stat = os.fstat(self._identity_fd)
            self._require_journal_metadata(identity_stat)
            if (identity_stat.st_dev, identity_stat.st_ino) != self._original_identity:
                raise ValueError("JOURNAL_IDENTITY_CHANGED")
        return value

    def assert_continuity(self) -> None:
        """Perform a bounded read-only path/identity check before an effect."""
        self._validated_path_identity()

    def approval_request_observed(
        self, ordinal: int, *, kind: ApprovalKind, thread_match: bool, turn_match: bool,
        cwd_match: bool, wire_command_sha256: str | None, sentinel_reference_class: str,
    ) -> None:
        if type(ordinal) is not int or not 1 <= ordinal <= MAX_PROBE_APPROVAL_REQUESTS:
            raise ValueError("APPROVAL_REQUEST_ORDINAL_INVALID")
        if wire_command_sha256 is not None and SHA256_RE.fullmatch(wire_command_sha256) is None:
            raise ValueError("APPROVAL_REQUEST_WIRE_HASH_INVALID")
        if sentinel_reference_class not in {
            SENTINEL_EXACT_ARG, SENTINEL_EMBEDDED, SENTINEL_ABSENT, SENTINEL_VECTOR_UNKNOWN,
        }:
            raise ValueError("APPROVAL_REQUEST_SENTINEL_CLASS_INVALID")
        self._append({
            "event": f"APPROVAL_REQUEST_{ordinal}_OBSERVED", "request_count": ordinal,
            "kind": kind.value, "thread_match": bool(thread_match), "turn_match": bool(turn_match),
            "cwd_match": bool(cwd_match), "wire_command_sha256": wire_command_sha256,
            "sentinel_reference_class": sentinel_reference_class,
        })

    def intent(self, stage: str, *, attempt: int | None = None, request_count: int | None = None) -> None:
        record: dict[str, Any] = {"event": stage + "_INTENT", "status": "PENDING"}
        if attempt is not None:
            record["attempt"] = attempt
        if request_count is not None:
            record["request_count"] = request_count
        self._append(record)

    def result(self, stage: str, value: str, *, attempt: int | None = None, request_count: int | None = None) -> None:
        record: dict[str, Any] = {"event": stage + "_RESULT", "result": value}
        if attempt is not None:
            record["attempt"] = attempt
        if request_count is not None:
            record["request_count"] = request_count
        self._append(record)


RECOVERY_JOURNAL_FIELDS = frozenset({
    "event", "result", "source_sha", "source_tree", "attempt", "request_count", "status", "class",
    "kind", "thread_match", "turn_match", "cwd_match", "wire_hash", "wire_command_sha256", "category",
    "sentinel_reference_class",
})
MAX_RECOVERY_JOURNAL_BYTES = 256 * 1024
MAX_RECOVERY_JOURNAL_RECORDS = 512


def _journal_metadata(value: os.stat_result) -> tuple[int, int, int, int, int, int, int, int, int]:
    return (
        value.st_dev, value.st_ino, value.st_size, value.st_mode, value.st_uid, value.st_gid,
        value.st_nlink, value.st_mtime_ns, value.st_ctime_ns,
    )


def _json_object_without_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("JOURNAL_DUPLICATE_FIELD")
        value[key] = item
    return value


def _validate_recovery_journal_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - RECOVERY_JOURNAL_FIELDS:
        raise ValueError("JOURNAL_SCHEMA_INVALID")
    event = value.get("event")
    if not isinstance(event, str) or re.fullmatch(r"[A-Z0-9_]+", event) is None:
        raise ValueError("JOURNAL_EVENT_INVALID")
    if not all(RecoveryJournal._safe(item) for item in value.values()):
        raise ValueError("JOURNAL_VALUE_UNSAFE")
    return value


def read_authoritative_recovery_journal(
    path: Path, *, maximum: int = MAX_RECOVERY_JOURNAL_BYTES,
    maximum_records: int = MAX_RECOVERY_JOURNAL_RECORDS,
) -> list[dict[str, Any]]:
    """Read acquisition evidence through a bounded, stable, no-follow fd."""
    if not _private_regular(path):
        raise ValueError("JOURNAL_AUTHORITY_INVALID")
    before_path = path.lstat()
    if before_path.st_size > maximum:
        raise ValueError("JOURNAL_OVERSIZE")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(str(path), flags)
    chunks: list[bytes] = []
    total = 0
    try:
        before_fd = os.fstat(fd)
        if _journal_metadata(before_fd) != _journal_metadata(before_path):
            raise ValueError("JOURNAL_IDENTITY_CHANGED")
        while True:
            chunk = os.read(fd, min(8192, maximum - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise ValueError("JOURNAL_OVERSIZE")
            chunks.append(chunk)
        after_fd = os.fstat(fd)
        after_path = path.lstat()
        if (
            _journal_metadata(after_fd) != _journal_metadata(before_fd)
            or _journal_metadata(after_path) != _journal_metadata(before_path)
        ):
            raise ValueError("JOURNAL_IDENTITY_CHANGED")
    finally:
        os.close(fd)
    try:
        text = b"".join(chunks).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("JOURNAL_UTF8_INVALID") from error
    lines = text.splitlines()
    if not lines or len(lines) > maximum_records or any(not line for line in lines):
        raise ValueError("JOURNAL_RECORD_COUNT_INVALID")
    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            record = json.loads(
                line, object_pairs_hook=_json_object_without_duplicate_fields,
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError("JOURNAL_CONSTANT_INVALID")),
            )
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError("JOURNAL_JSON_INVALID") from error
        records.append(_validate_recovery_journal_record(record))
    return records


def read_journal_records(path: Path) -> list[dict[str, Any]]:
    """Compatibility name; all journal reads use the authoritative reader."""
    return read_authoritative_recovery_journal(path)


def record_synthetic_wire_adapter_result(
    journal: RecoveryJournal, *, wire_stage: str, adapter_stage: str, response: Any,
    parser: Callable[[Any], Any],
) -> str:
    """Record transport return independently from semantic adapter parsing."""
    journal.result(wire_stage, WIRE_RESPONSE_RETURNED)
    try:
        parser(response)
    except Exception:
        journal.result(adapter_stage, "INVALID")
        return "INVALID"
    journal.result(adapter_stage, "CONFIRMED")
    return "CONFIRMED"


class WireCommandAuthority:
    """Root-only first-capture authority for future raw wire grammar."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def capture_once(
        self, *, thread_id: str, turn_id: str, cwd: str, sentinel: str,
        wire_command: str, kind: ApprovalKind, sequence: int,
    ) -> None:
        if (
            kind is not ApprovalKind.COMMAND_EXECUTION
            or not isinstance(thread_id, str) or not thread_id
            or not isinstance(turn_id, str) or not turn_id
            or not isinstance(cwd, str) or not os.path.isabs(cwd)
            or not isinstance(sentinel, str) or not os.path.isabs(sentinel)
            or type(sequence) is not int or not 1 <= sequence <= MAX_SEQUENCE
            or not isinstance(wire_command, str) or not wire_command
            or len(wire_command) > MAX_WIRE_COMMAND_CHARS
            or "\0" in wire_command
        ):
            raise ValueError("WIRE_COMMAND_UNSAFE")
        normalized_cwd = os.path.normpath(os.path.abspath(cwd))
        record = {
            "format": 1,
            "thread_id_sha256": _sha256(thread_id),
            "turn_id_sha256": _sha256(turn_id),
            "actual_cwd_sha256": _sha256(normalized_cwd),
            "expected_sentinel_path_sha256": _sha256(sentinel),
            "wire_command_plaintext": wire_command,
            "wire_command_sha256": _sha256(wire_command),
            "request_kind": kind.value,
            "local_request_sequence": sequence,
            "capture_status": "CAPTURED_ROOT_ONLY",
        }
        if self.path.exists():
            raise FileExistsError("WIRE_AUTHORITY_ALREADY_EXISTS")
        write_exclusive_private_json(self.path, record)


WIRE_AUTHORITY_KEYS = frozenset({
    "format", "thread_id_sha256", "turn_id_sha256", "actual_cwd_sha256",
    "expected_sentinel_path_sha256", "wire_command_plaintext", "wire_command_sha256",
    "request_kind", "local_request_sequence", "capture_status",
})


def validate_wire_authority_record(value: Mapping[str, Any]) -> None:
    """Validate the complete root-only wire schema before any projection."""
    if set(value) != WIRE_AUTHORITY_KEYS:
        raise ValueError("WIRE_AUTHORITY_SCHEMA_INVALID")
    if type(value["format"]) is not int or value["format"] != 1:
        raise ValueError("WIRE_AUTHORITY_FORMAT_INVALID")
    for key in ("thread_id_sha256", "turn_id_sha256", "actual_cwd_sha256", "expected_sentinel_path_sha256", "wire_command_sha256"):
        if not isinstance(value[key], str) or SHA256_RE.fullmatch(value[key]) is None:
            raise ValueError("WIRE_AUTHORITY_HASH_INVALID")
    if value["request_kind"] != ApprovalKind.COMMAND_EXECUTION.value:
        raise ValueError("WIRE_AUTHORITY_KIND_INVALID")
    if type(value["local_request_sequence"]) is not int or not 1 <= value["local_request_sequence"] <= MAX_SEQUENCE:
        raise ValueError("WIRE_AUTHORITY_SEQUENCE_INVALID")
    if value["capture_status"] != "CAPTURED_ROOT_ONLY":
        raise ValueError("WIRE_AUTHORITY_STATUS_INVALID")
    plaintext = value["wire_command_plaintext"]
    if not isinstance(plaintext, str) or not plaintext or "\0" in plaintext or len(plaintext) > MAX_WIRE_COMMAND_CHARS:
        raise ValueError("WIRE_AUTHORITY_PLAINTEXT_INVALID")
    if _sha256(plaintext) != value["wire_command_sha256"]:
        raise ValueError("WIRE_AUTHORITY_HASH_MISMATCH")


def read_wire_authority(path: Path) -> dict[str, Any]:
    record = read_bounded_private_json(path)
    validate_wire_authority_record(record)
    return record


@dataclass(frozen=True)
class WireVectorRecovery:
    established: bool
    wire_sha256: str
    vector_length: int | None
    token_classes: tuple[str, ...]
    token_sha256: tuple[str, ...]


def _token_class(token: str, index: int) -> str:
    if index == 0:
        return "ABSOLUTE_EXECUTABLE" if token.startswith("/") else "EXECUTABLE"
    if token.startswith("-"):
        return "OPTION"
    if token.isdigit():
        return "INTEGER"
    if "/" in token:
        return "PATH_TOKEN"
    if any(character in token for character in ";&|$`()<>*?"):
        return "LITERAL_SHELL_META_TOKEN"
    return "ARGUMENT"


def recover_wire_vector(wire: str) -> WireVectorRecovery:
    digest = _sha256(wire) if isinstance(wire, str) else ""
    if not isinstance(wire, str) or not wire or "\0" in wire or len(wire) > MAX_WIRE_COMMAND_CHARS:
        return WireVectorRecovery(False, digest, None, (), ())
    try:
        vector = shlex.split(wire, comments=False, posix=True)
        if not vector or len(vector) > MAX_WIRE_VECTOR_TOKENS or shlex.join(vector) != wire:
            return WireVectorRecovery(False, digest, None, (), ())
    except ValueError:
        return WireVectorRecovery(False, digest, None, (), ())
    return WireVectorRecovery(
        True, digest, len(vector), tuple(_token_class(token, index) for index, token in enumerate(vector)),
        tuple(_sha256(token) for token in vector),
    )


def classify_sentinel_reference(wire: str, sentinel: str) -> str:
    """Return an observation class; this is deliberately not matcher authority."""
    recovered = recover_wire_vector(wire)
    if not recovered.established:
        return SENTINEL_VECTOR_UNKNOWN
    vector = shlex.split(wire, comments=False, posix=True)
    if sentinel in vector:
        return SENTINEL_EXACT_ARG
    if any(sentinel in token for token in vector):
        return SENTINEL_EMBEDDED
    return SENTINEL_ABSENT


def candidate_probe_prompt(sentinel: str) -> str:
    if not isinstance(sentinel, str) or not sentinel.startswith("/") or "\0" in sentinel:
        raise ValueError("SENTINEL_AUTHORITY_INVALID")
    return (
        "Perform only this operation: sleep for exactly 30 seconds, then touch the exact sentinel at "
        f"{sentinel}. Do not perform alternatives or any other operation. If permission or approval is "
        "denied, stop immediately. Do not retry via another tool or command."
    )


@dataclass(frozen=True)
class ApprovalCapture:
    request_sequence: int
    kind: ApprovalKind
    thread_match: bool
    turn_match: bool
    cwd_match: bool
    sentinel_reference_class: str
    request_count: int
    response_count: int
    wire_command: str | None
    context_line: str | None
    wire_command_sha256: str | None


class DenyOnlyApprovalOperator:
    """The future probe operator.  Its only executable decision is DENY."""

    def __init__(
        self, *, thread_id: str, turn_id: asyncio.Future[str], cwd: str, sentinel: str,
        wire_authority: WireCommandAuthority | None = None,
        request_journal: RecoveryJournal | None = None,
    ) -> None:
        self.thread_id = thread_id
        self.turn_id = turn_id
        self.cwd = os.path.normpath(os.path.abspath(cwd))
        self.sentinel = sentinel
        self.wire_authority = wire_authority
        self.request_journal = request_journal
        self.request_observation_failed = False
        self.captures: list[ApprovalCapture] = []
        self.response_count = 0
        self.allow_count = 0

    @staticmethod
    def _context(request: ApprovalRequest, prefix: str) -> tuple[str, ...]:
        return tuple(line[len(prefix):] for line in request.context_lines if line.startswith(prefix))

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        expected_turn = self.turn_id.result() if self.turn_id.done() and not self.turn_id.cancelled() else None
        commands = self._context(request, "command: ")
        cwds = self._context(request, "cwd: ")
        command = commands[0] if len(commands) == 1 else None
        normalized_cwd = os.path.normpath(os.path.abspath(cwds[0])) if len(cwds) == 1 and os.path.isabs(cwds[0]) else None
        exact_identity = (
            request.kind is ApprovalKind.COMMAND_EXECUTION
            and len(commands) == 1
            and len(cwds) == 1
            and request.thread_id == self.thread_id
            and expected_turn is not None
            and request.turn_id == expected_turn
            and normalized_cwd == self.cwd
            and isinstance(command, str)
            and bool(command)
        )
        sequence = len(self.captures) + 1
        capture = ApprovalCapture(
            request_sequence=request.local_sequence,
            kind=request.kind,
            thread_match=request.thread_id == self.thread_id,
            turn_match=expected_turn is not None and request.turn_id == expected_turn,
            cwd_match=normalized_cwd == self.cwd,
            sentinel_reference_class=classify_sentinel_reference(command, self.sentinel) if command is not None else SENTINEL_VECTOR_UNKNOWN,
            request_count=sequence,
            response_count=self.response_count,
            wire_command=command,
            context_line=next((line for line in request.context_lines if line.startswith("command: ")), None),
            wire_command_sha256=_sha256(command) if command is not None else None,
        )
        self.captures.append(capture)
        if exact_identity and self.wire_authority is not None and not self.wire_authority.path.exists():
            self.wire_authority.capture_once(
                thread_id=request.thread_id, turn_id=request.turn_id, cwd=normalized_cwd,
                sentinel=self.sentinel, wire_command=command, kind=request.kind, sequence=request.local_sequence,
            )
        if self.request_journal is not None:
            try:
                self.request_journal.approval_request_observed(
                    capture.request_count, kind=capture.kind, thread_match=capture.thread_match,
                    turn_match=capture.turn_match, cwd_match=capture.cwd_match,
                    wire_command_sha256=capture.wire_command_sha256,
                    sentinel_reference_class=capture.sentinel_reference_class,
                )
            except Exception:
                self.request_observation_failed = True
                raise
        return ApprovalDecision.DENY

    def require_response_dispatch(self) -> None:
        if self.request_observation_failed:
            raise RuntimeError("APPROVAL_REQUEST_OBSERVED_JOURNAL_FAILED")


class SyntheticApprovalClient:
    """Minimal local protocol seam; it never starts an external process."""

    def __init__(self, *, terminal_status: str = "COMPLETED", response_gate: Callable[[], None] | None = None) -> None:
        self.queue: asyncio.Queue[InboundServerRequest] = asyncio.Queue()
        self.pending: dict[str | int, InboundServerRequest] = {}
        self.responses: list[dict[str, Any]] = []
        self.allow_response_count = 0
        self.deny_response_count = 0
        self.approval_response_count = 0
        self.response_calls = 0
        self.response_intent: Callable[[], None] | None = None
        self.terminal = asyncio.Event()
        self.terminal_status = terminal_status
        self.response_gate = response_gate
        self._sequence = 1

    def offer(self, *, params: Mapping[str, Any], request_id: str | int = "synthetic-request") -> InboundServerRequest:
        request = InboundServerRequest(self._sequence, request_id, COMMAND, dict(params))
        self._sequence += 1
        self.pending[request_id] = request
        return request

    def offer_unsupported(self, *, method: str, params: Mapping[str, Any], request_id: str = "unsupported") -> InboundServerRequest:
        request = InboundServerRequest(self._sequence, request_id, method, dict(params))
        self._sequence += 1
        self.pending[request_id] = request
        return request

    async def enqueue(self, request: InboundServerRequest) -> None:
        await self.queue.put(request)

    async def next_server_request(self) -> InboundServerRequest:
        return await self.queue.get()

    async def wait_terminal(self) -> str:
        await self.terminal.wait()
        return self.terminal_status

    def owns_server_request(self, request: InboundServerRequest) -> bool:
        return self.pending.get(request.request_id) is request

    async def respond_server_request(self, request: InboundServerRequest, result: dict[str, Any]) -> None:
        if not self.owns_server_request(request):
            raise RuntimeError("SYNTHETIC_REQUEST_NOT_OWNED")
        if self.response_gate is not None:
            self.response_gate()
        if self.response_intent is not None:
            self.response_intent()
        if result.get("decision") in ("accept", "approved") or result.get("permissions"):
            raise AssertionError("ALLOW_RESPONSE_FORBIDDEN")
        self.pending.pop(request.request_id, None)
        self.responses.append({"request_id": request.request_id, "result": dict(result)})
        self.response_calls += 1
        self.approval_response_count += 1
        self.deny_response_count += 1
        if hasattr(self, "response_observer"):
            self.response_observer.response_count = len(self.responses)


@dataclass(frozen=True)
class ProbeObservation:
    primary_outcome_class: str
    terminal_status: str | None
    request_count: int
    deny_response_count: int
    allow_response_count: int
    observer_joined: bool
    approval_statuses: tuple[ApprovalHandlingStatus, ...] = ()
    approval_owner_terminalized: bool = True
    terminal_owner_terminalized: bool = True
    owner_nonconverged: bool = False


async def _cancel_and_join(task: asyncio.Task[Any], timeout: float = 0.25) -> bool:
    if not task.done():
        task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout)
    except asyncio.TimeoutError:
        return False
    except BaseException:
        return True
    return True


async def _finite_await(awaitable: Any, timeout: float, *, stage: str) -> tuple[bool, Any | None]:
    """Own one awaitable with a finite timeout and finite cancellation join."""
    task = asyncio.create_task(awaitable)
    try:
        return True, await asyncio.wait_for(asyncio.shield(task), timeout)
    except asyncio.TimeoutError:
        joined = await _cancel_and_join(task, min(timeout, 0.25))
        return False, stage if not joined else None
    except asyncio.CancelledError:
        if not task.done():
            await _cancel_and_join(task, min(timeout, 0.25))
        raise
    except Exception as error:
        return False, error


async def _dispatch_after_journal_intent(journal: RecoveryJournal, stage: str, effect: Any, **kwargs: Any) -> Any:
    """The only ordering allowed for a future external effect."""
    journal.intent(stage, **kwargs)
    journal.assert_continuity()
    return await effect()


def _terminal_value(value: Any) -> str | None:
    candidate = getattr(value, "value", value)
    return candidate if isinstance(candidate, str) else None


def classify_race(
    *, terminal_status: str | None, approval_statuses: Sequence[ApprovalHandlingStatus],
    deny_response_count: int, request_dequeued: bool, converged: bool = True,
) -> str:
    """Freeze classification from observed facts, never waiter scheduling."""
    if not converged:
        return OUTCOME_NONCONVERGENT
    if terminal_status is not None and terminal_status != "COMPLETED":
        return OUTCOME_PROTOCOL
    if len(approval_statuses) >= MAX_PROBE_APPROVAL_REQUESTS and terminal_status is None:
        return OUTCOME_LIMIT
    if ApprovalHandlingStatus.RESPONSE_UNKNOWN in approval_statuses and (terminal_status is not None or request_dequeued):
        return OUTCOME_AMBIGUOUS
    if deny_response_count > 0:
        return OUTCOME_APPROVAL_FIRST
    if terminal_status is not None and not request_dequeued:
        return OUTCOME_TERMINAL_FIRST
    if request_dequeued:
        return OUTCOME_APPROVAL_FIRST
    return OUTCOME_WATCHDOG


async def observe_probe_turn(
    bridge: CodexApprovalBridge, client: SyntheticApprovalClient, operator: DenyOnlyApprovalOperator,
    *, terminal_timeout: float = 0.5,
) -> ProbeObservation:
    """Observe both sides and classify only from completed protocol facts."""
    approval_results: list[ApprovalHandlingStatus] = []
    request_dequeued = False

    async def observe_approvals() -> None:
        nonlocal request_dequeued
        while len(approval_results) < MAX_PROBE_APPROVAL_REQUESTS:
            try:
                result = await bridge.handle_next()
            except ApprovalError:
                return
            approval_results.append(result.status)
            request_dequeued = True
            if result.status is ApprovalHandlingStatus.RESPONSE_UNKNOWN:
                return
            if len(approval_results) == MAX_PROBE_APPROVAL_REQUESTS:
                return

    approval_task = asyncio.create_task(observe_approvals())
    terminal_task = asyncio.create_task(client.wait_terminal())
    terminal_event = getattr(client, "terminal", None)
    request_queue = getattr(client, "queue", None)
    same_tick_fixture = bool(
        terminal_event is not None and terminal_event.is_set()
        and request_queue is not None and not request_queue.empty()
    )
    terminal_status: str | None = None
    try:
        if same_tick_fixture:
            # Freeze the synthetic fact set before either waiter can win the
            # scheduler: a queued request and terminal are concurrent facts.
            await asyncio.wait_for(asyncio.shield(approval_task), terminal_timeout)
            terminal_status = _terminal_value(await terminal_task)
            outcome = classify_race(
                terminal_status=terminal_status, approval_statuses=tuple(approval_results),
                deny_response_count=client.deny_response_count, request_dequeued=True,
            )
            return ProbeObservation(
                outcome, terminal_status, len(operator.captures), client.deny_response_count,
                client.allow_response_count, True, tuple(approval_results),
                approval_owner_terminalized=True, terminal_owner_terminalized=True,
            )
        done, _ = await asyncio.wait((approval_task, terminal_task), timeout=terminal_timeout, return_when=asyncio.FIRST_COMPLETED)
        if terminal_task in done:
            terminal_status = _terminal_value(terminal_task.result())
        # Let a completed approval response (or RESPONSE_UNKNOWN dequeue) be
        # observed before taking the final fact snapshot.
        if approval_task not in done and terminal_task in done:
            await asyncio.sleep(0)
        if not terminal_task.done() and approval_task.done() and len(approval_results) >= MAX_PROBE_APPROVAL_REQUESTS:
            terminal_status = None
        elif terminal_task.done() and terminal_status is None:
            terminal_status = _terminal_value(terminal_task.result())
        outcome = classify_race(
            terminal_status=terminal_status,
            approval_statuses=tuple(approval_results),
            deny_response_count=client.deny_response_count,
            request_dequeued=request_dequeued,
            converged=terminal_task.done() or approval_task.done() or bool(done),
        )
    finally:
        approval_owner_terminalized = await _cancel_and_join(approval_task)
        terminal_owner_terminalized = await _cancel_and_join(terminal_task)
    owner_nonconverged = not (approval_owner_terminalized and terminal_owner_terminalized)
    return ProbeObservation(
        outcome,
        terminal_status,
        len(operator.captures),
        client.deny_response_count,
        client.allow_response_count,
        approval_owner_terminalized and terminal_owner_terminalized,
        tuple(approval_results),
        approval_owner_terminalized=approval_owner_terminalized,
        terminal_owner_terminalized=terminal_owner_terminalized,
        owner_nonconverged=owner_nonconverged,
    )


@dataclass(frozen=True)
class FreshProbeRun:
    root: Path
    state_parent: Path
    isolated_state: Path
    sqlite: Path
    logs: Path
    controller: Path
    workdir: Path
    sentinel: Path
    probe_recovery: Path
    wire_recovery: Path
    result: Path
    latch: Path

    @classmethod
    def materialize(cls, parent: Path) -> "FreshProbeRun":
        root = parent / ("codexcontrol-p7c8-probe-" + secrets.token_hex(16))
        root.mkdir(mode=0o700)
        state_parent = root / "state-parent"
        isolated = state_parent / "p7c8-isolated-state"
        sqlite = isolated / "sqlite"
        logs = isolated / "logs"
        workdir = root / "workdir"
        controller = root / "controller"
        for directory in (state_parent, isolated, sqlite, logs, workdir, controller):
            directory.mkdir(mode=0o700)
        sentinel = root / "outside-workdir-sentinel"
        return cls(root, state_parent, isolated, sqlite, logs, controller, workdir, sentinel, root / "probe-recovery.json", root / "wire-command-recovery.json", root / "probe-result.json", root / "probe-latch.json")

    @classmethod
    def reconstruct(cls, root: Path) -> "FreshProbeRun":
        """Rebuild the exact run paths without creating or cleaning anything."""
        if not _private_directory(root):
            raise ValueError("FRESH_RUN_ROOT_INVALID")
        state_parent = root / "state-parent"
        isolated = state_parent / "p7c8-isolated-state"
        return cls(
            root, state_parent, isolated, isolated / "sqlite", isolated / "logs", root / "controller",
            root / "workdir", root / "outside-workdir-sentinel", root / "probe-recovery.json",
            root / "wire-command-recovery.json", root / "probe-result.json", root / "probe-latch.json",
        )


@dataclass(frozen=True)
class ChildResultDiscovery:
    run: FreshProbeRun | None
    present: bool
    valid: bool
    classification: str


def discover_child_result(parent: Path, *, timeout: float = PROBE_CHILD_RESULT_TIMEOUT) -> ChildResultDiscovery:
    """Perform bounded, read-only discovery of one child root and result."""
    started = time.monotonic()
    if not _private_directory(parent):
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    try:
        entries: list[Path] = []
        with os.scandir(parent) as scan:
            for entry in scan:
                if time.monotonic() - started > timeout:
                    return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
                entries.append(Path(entry.path))
                if len(entries) > 1:
                    return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_AMBIGUOUS")
    except OSError:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    if time.monotonic() - started > timeout:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    if not entries:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_MISSING")
    if len(entries) != 1:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_AMBIGUOUS")
    root = entries[0]
    try:
        root_stat = root.lstat()
    except OSError:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    if not (
        stat.S_ISDIR(root_stat.st_mode)
        and root_stat.st_uid == 0 and root_stat.st_gid == 0
        and stat.S_IMODE(root_stat.st_mode) == 0o700
    ):
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_AMBIGUOUS")
    try:
        run = FreshProbeRun.reconstruct(root)
    except (OSError, ValueError):
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    if time.monotonic() - started > timeout:
        return ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    result_path = run.root / CHILD_RESULT_FILENAME
    try:
        result_path.lstat()
    except FileNotFoundError:
        return ChildResultDiscovery(run, False, False, "CHILD_RESULT_DISCOVERY_MISSING")
    except OSError:
        return ChildResultDiscovery(run, True, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    try:
        value = read_bounded_private_json(result_path)
        if time.monotonic() - started > timeout:
            raise ValueError("CHILD_RESULT_READ_TIMEOUT")
        validate_child_result(value)
    except (OSError, ValueError, AssertionError):
        return ChildResultDiscovery(run, True, False, "CHILD_RESULT_DISCOVERY_UNREADABLE")
    return ChildResultDiscovery(run, True, True, "CHILD_RESULT_DISCOVERY_CONFIRMED")


@dataclass
class FutureProbeBudget:
    """Call budget for a future authorized run; no RPC is made here."""

    model_list_calls: int = 0
    thread_start_calls: int = 0
    thread_resume_calls: int = 0
    turn_start_calls: int = 0
    approval_deny_responses: int = 0
    approval_deny_attempts: int = 0
    approval_deny_confirmed: int = 0
    approval_deny_unknown_or_failed: int = 0
    approval_total_responses: int = 0
    thread_delete_calls: int = 0
    thread_read_calls: int = 0
    thread_list_calls: int = 0
    interrupt_calls: int = 0
    approval_allow_responses: int = 0

    def record(self, name: str) -> None:
        if not hasattr(self, name):
            raise AssertionError("UNSUPPORTED_FUTURE_PROBE_ACTION")
        setattr(self, name, getattr(self, name) + 1)
        limits = {
            "model_list_calls": 1, "thread_start_calls": 1, "thread_resume_calls": 0,
            "turn_start_calls": 1, "approval_deny_responses": MAX_PROBE_APPROVAL_REQUESTS,
            "approval_deny_attempts": MAX_PROBE_APPROVAL_REQUESTS,
            "approval_deny_confirmed": MAX_PROBE_APPROVAL_REQUESTS,
            "approval_deny_unknown_or_failed": MAX_PROBE_APPROVAL_REQUESTS,
            "approval_total_responses": MAX_PROBE_APPROVAL_REQUESTS,
            "thread_delete_calls": 0, "thread_read_calls": 0, "thread_list_calls": 0,
            "interrupt_calls": 0, "approval_allow_responses": 0,
        }
        if getattr(self, name) > limits[name]:
            raise AssertionError("FUTURE_PROBE_BUDGET_EXCEEDED")

    def record_approval_deny(self) -> None:
        self.reserve_deny_attempt()
        self.record_deny_result(confirmed=True)

    def reserve_deny_attempt(self) -> int:
        if self.approval_deny_attempts >= MAX_PROBE_APPROVAL_REQUESTS:
            raise AssertionError("PROBE_APPROVAL_REQUEST_LIMIT_EXCEEDED")
        self.record("approval_deny_attempts")
        self.record("approval_total_responses")
        self.approval_deny_responses = self.approval_deny_attempts
        return self.approval_deny_attempts

    def record_deny_result(self, *, confirmed: bool) -> None:
        if self.approval_deny_confirmed + self.approval_deny_unknown_or_failed >= self.approval_deny_attempts:
            if not confirmed and self.approval_deny_unknown_or_failed >= self.approval_deny_attempts:
                raise AssertionError("DENY_RESULT_WITHOUT_ATTEMPT")
        field = "approval_deny_confirmed" if confirmed else "approval_deny_unknown_or_failed"
        self.record(field)
        self.approval_deny_responses = self.approval_deny_attempts

    def reconcile(self) -> None:
        if self.approval_deny_attempts != self.approval_deny_confirmed + self.approval_deny_unknown_or_failed:
            raise AssertionError("DENY_COUNTERS_DO_NOT_RECONCILE")
        if self.approval_total_responses != self.approval_deny_attempts or self.approval_allow_responses != 0:
            raise AssertionError("APPROVAL_COUNTERS_INVALID")

    def record_approval_allow(self) -> None:
        raise AssertionError("ALLOW_DECISION_PATHS=0")


def synthetic_normal_budget() -> FutureProbeBudget:
    """Build one complete synthetic normal lifecycle through the sole ledger."""
    budget = FutureProbeBudget()
    for action in ("model_list_calls", "thread_start_calls", "turn_start_calls"):
        budget.record(action)
    budget.reconcile()
    return budget


def write_sanitized_result(path: Path, value: Mapping[str, Any]) -> None:
    validate_sanitized_result(value)
    write_exclusive_private_json(path, value, maximum=MAX_AUTHORITY_BYTES)


def write_parent_final_result(path: Path, value: Mapping[str, Any]) -> None:
    """Persist only the extended parent authority, then prove its readback."""
    validate_parent_final_result(value)
    write_exclusive_private_json(path, value, maximum=MAX_AUTHORITY_BYTES)
    readback = read_bounded_private_json(path, maximum=MAX_AUTHORITY_BYTES)
    validate_parent_final_result(readback)
    if readback != dict(value):
        raise ValueError("PARENT_RESULT_READBACK_MISMATCH")


def write_parent_execution_outcome(path: Path, value: Mapping[str, Any]) -> None:
    """Persist one sanitized parent execution classification, never overwrite."""
    validate_parent_execution_outcome(value)
    write_exclusive_private_json(path, value, maximum=MAX_AUTHORITY_BYTES)
    readback = read_bounded_private_json(path, maximum=MAX_AUTHORITY_BYTES)
    validate_parent_execution_outcome(readback)
    if readback != dict(value):
        raise ValueError("PARENT_OUTCOME_READBACK_MISMATCH")


def create_probe_latch(path: Path, *, source_sha: str, source_tree: str) -> None:
    if not _private_directory(path.parent):
        raise ValueError("LATCH_PARENT_INVALID")
    if not (len(source_sha) == 40 and len(source_tree) == 40):
        raise ValueError("LATCH_SOURCE_INVALID")
    write_exclusive_private_json(path, {"format": 1, "status": "RESERVED_BEFORE_FIRST_RPC", "source_sha": source_sha, "source_tree": source_tree})


def validate_future_source_authority(repository: Path = Path("/opt/codex-control")) -> tuple[str, str]:
    """Validate architect-supplied source before latch creation or any RPC."""
    expected_head = os.environ.get(EXPECTED_HEAD_ENV)
    expected_tree = os.environ.get(EXPECTED_TREE_ENV)
    if not expected_head or not expected_tree or len(expected_head) != 40 or len(expected_tree) != 40:
        raise RuntimeError("P7C8_SOURCE_AUTHORITY_UNSET")
    if repository != Path("/opt/codex-control") or repository.resolve() != Path("/opt/codex-control"):
        raise RuntimeError("P7C8_CANONICAL_REPOSITORY_REQUIRED")
    try:
        head = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "-C", str(repository), "rev-parse", "HEAD^{tree}"], text=True).strip()
        clean = subprocess.check_output(["git", "-C", str(repository), "status", "--porcelain"], text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError("P7C8_SOURCE_GATE_UNAVAILABLE") from error
    if head != expected_head or tree != expected_tree or clean:
        raise RuntimeError("P7C8_SOURCE_GATE_MISMATCH")
    return head, tree


def _authority_path_present(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def measure_parent_authority_presence(*paths: Path) -> tuple[bool, ...]:
    """Measure durable path presence without creating or following paths."""
    return tuple(_authority_path_present(path) for path in paths)


def require_parent_execution_authorities_absent(
    latch: Path, normal_result: Path, execution_outcome: Path,
) -> None:
    """Require all one-shot parent authorities absent before child creation."""
    if any(_authority_path_present(path) for path in (latch, normal_result, execution_outcome)):
        raise RuntimeError("P7C8_PREEXISTING_PARENT_AUTHORITY")


def preflight_future_probe_boundaries(run: FreshProbeRun) -> None:
    protected = (Path("/opt/codex-control"), Path("/root/.codex_second"), Path("/root/.codexcontrol"))
    for path in (run.root, run.state_parent, run.isolated_state, run.sqlite, run.logs, run.controller, run.workdir, run.sentinel):
        if any(path == other or other in path.parents or path in other.parents for other in protected):
            raise RuntimeError("P7C8_PROBE_PATH_OVERLAP")
    if not _private_directory(run.root) or not _private_directory(run.workdir):
        raise RuntimeError("P7C8_PROBE_ROOT_AUTHORITY_INVALID")
    if run.sentinel.exists():
        raise RuntimeError("P7C8_PREEXISTING_PROBE_ARTIFACT")
    require_parent_execution_authorities_absent(REAL_PROBE_LATCH, REAL_PROBE_RESULT, REAL_PROBE_OUTCOME)


def require_dedicated_future_process_group() -> tuple[int, int, int]:
    """The authorized runner must itself be the single session/group leader."""
    pid = os.getpid()
    pgid = os.getpgid(pid)
    sid = os.getsid(pid)
    parent_pgid = os.getpgid(os.getppid())
    if pid != pgid or pid != sid or pgid <= 1 or pgid == parent_pgid:
        raise RuntimeError("P7C8_DEDICATED_PROCESS_GROUP_REQUIRED")
    return pid, pgid, sid


async def _drain_future_approvals(bridge: CodexApprovalBridge, statuses: list[ApprovalHandlingStatus]) -> None:
    """Finite approval owner retained for offline compatibility tests."""
    while len(statuses) < MAX_PROBE_APPROVAL_REQUESTS:
        try:
            result = await bridge.handle_next()
        except ApprovalError:
            return
        statuses.append(result.status)
        if result.status is not ApprovalHandlingStatus.DENIED:
            return


async def _observe_future_race(
    bridge: CodexApprovalBridge, client: Any, operator: DenyOnlyApprovalOperator,
    terminal_waiter: Any,
) -> ProbeObservation:
    """Run the approval and exact-turn terminal owners at one boundary."""
    class _ExactTurnObservationClient:
        @property
        def deny_response_count(self) -> int:
            return int(getattr(client, "deny_response_count", 0))

        @property
        def allow_response_count(self) -> int:
            return int(getattr(client, "allow_response_count", 0))

        async def next_server_request(self) -> Any:
            return await client.next_server_request()

        async def wait_terminal(self) -> str | None:
            terminal = await terminal_waiter()
            return _terminal_value(getattr(terminal, "status", terminal))

    return await observe_probe_turn(
        bridge, _ExactTurnObservationClient(), operator,
        terminal_timeout=PROBE_OBSERVATION_TIMEOUT,
    )


async def future_real_deny_only_approval_probe(run_parent: Path | None = None) -> dict[str, Any]:
    """Future child path; callable only under the separately frozen gate.

    The parent process owns the hard deadline and final group/result authority.
    This child owns only finite stage effects and child-local observations.
    """
    if os.environ.get(AUTHORIZED_ENV) != AUTHORIZED_ENV:
        raise unittest.SkipTest("P7C8_REAL_PROBE_GATE_DISABLED")
    accepted_head, accepted_tree = validate_future_source_authority()
    require_dedicated_future_process_group()
    if not _private_directory(REAL_PROBE_LATCH.parent):
        raise RuntimeError("P7C8_LATCH_PARENT_INVALID")
    if REAL_PROBE_LATCH.exists() or REAL_PROBE_RESULT.exists():
        raise RuntimeError("P7C8_ONE_SHOT_ALREADY_CONSUMED")
    temporary_parent = run_parent or Path(tempfile.mkdtemp(prefix="codexcontrol-p7c8-real-", dir="/tmp"))
    run = FreshProbeRun.materialize(temporary_parent)
    preflight_future_probe_boundaries(run)
    journal = RecoveryJournal(run.probe_recovery, source_sha=accepted_head, source_tree=accepted_tree)
    create_probe_latch(REAL_PROBE_LATCH, source_sha=accepted_head, source_tree=accepted_tree)
    journal._append({"event": "GLOBAL_LATCH_RESERVED", "result": "YES"})

    profile = CodexProfile("p7c8-fresh-probe", "/root/.codex_second", "P7.C8 fresh disposable", str(run.isolated_state))
    authority = IsolationPathAuthority(
        (profile,), controller_db_root=str(run.controller), repository_root="/opt/codex-control",
        protected_roots=("/root/.codexcontrol",),
    )
    manager = CodexRuntimeManager([profile], client_version="p7c8-deny-only-probe", isolation_authority=authority)
    budget = FutureProbeBudget()
    runtime: Any | None = None
    operator: DenyOnlyApprovalOperator | None = None
    boundary: Mapping[str, Any] = {
        "sentinel_present": False, "sentinel_touch_authority_class": SENTINEL_ABSENT,
        "classification": "BOUNDARY_NOT_PROVED",
    }
    terminal_status: str | None = None
    observation: ProbeObservation | None = None
    outcome = OUTCOME_WATCHDOG
    shutdown_result = "NOT_ATTEMPTED"
    thread_established = False
    try:
        journal.intent("RUNTIME_ACQUIRE")
        acquire_observer = RuntimeAcquireObserver(
            timeout=P7C8_RUNTIME_ACQUIRE_TIMEOUT_SECONDS,
            cleanup_timeout=P7C8_RUNTIME_ACQUIRE_CLEANUP_TIMEOUT_SECONDS,
        )
        acquire_observation, acquire_owner = await acquire_observer.observe(manager, profile.profile_id)
        if acquire_observation.result != RuntimeAcquireClass.CONFIRMED:
            result_name = {
                RuntimeAcquireClass.TIMEOUT: "TIMEOUT",
                RuntimeAcquireClass.SAFE_EXCEPTION: "SAFE_EXCEPTION",
                RuntimeAcquireClass.UNEXPECTED_EXCEPTION: "UNEXPECTED_EXCEPTION",
                RuntimeAcquireClass.CANCELLATION_NONCONVERGENT: "CANCELLATION_NONCONVERGENT",
            }[acquire_observation.result]
            journal.result("RUNTIME_ACQUIRE", result_name)
            if acquire_observation.error_category is not None:
                journal._append({"event": "RUNTIME_ACQUIRE_ERROR_CATEGORY", "result": acquire_observation.error_category})
            acquire_observation = await acquire_observer.contain(
                manager, profile.profile_id, acquire_owner, acquire_observation, journal,
            )
            journal.result("RUNTIME_ACQUIRE_FINAL", {
                RuntimeAcquireClass.TIMEOUT: "TIMEOUT",
                RuntimeAcquireClass.SAFE_EXCEPTION: "SAFE_EXCEPTION",
                RuntimeAcquireClass.UNEXPECTED_EXCEPTION: "UNEXPECTED_EXCEPTION",
                RuntimeAcquireClass.CANCELLATION_NONCONVERGENT: "CANCELLATION_NONCONVERGENT",
            }[acquire_observation.result])
            raise RuntimeError("RUNTIME_ACQUIRE_FAILED")
        runtime = await acquire_owner
        journal.result("RUNTIME_ACQUIRE", "CONFIRMED")
        journal.result("RUNTIME_ACQUIRE_FINAL", "CONFIRMED")
        original_request = runtime.client.request
        original_response = runtime.client.respond_server_request

        async def counted_request(method: str, params: Any) -> Any:
            methods = {
                "model/list": ("model_list_calls", PROBE_MODEL_LIST_TIMEOUT, "MODEL_LIST"),
                "thread/start": ("thread_start_calls", PROBE_THREAD_START_TIMEOUT, "THREAD_START"),
                "turn/start": ("turn_start_calls", PROBE_TURN_START_TIMEOUT, "TURN_START"),
            }
            action_timeout = methods.get(method)
            if action_timeout is None:
                raise AssertionError("UNSUPPORTED_FUTURE_PROBE_ACTION")
            action, timeout, stage_name = action_timeout
            stage = stage_name + "_WIRE_DISPATCH"
            async def effect() -> tuple[bool, Any | None]:
                budget.record(action)
                return await _finite_await(original_request(method, params), timeout, stage=stage + "_NONCONVERGED")

            succeeded, value = await _dispatch_after_journal_intent(journal, stage, effect)
            journal.result(stage_name + "_WIRE", WIRE_RESPONSE_RETURNED if succeeded else WIRE_RESPONSE_UNKNOWN)
            if not succeeded:
                if isinstance(value, BaseException):
                    raise value
                raise RuntimeError(stage + "_NONCONVERGED")
            return value

        async def counted_response(request: InboundServerRequest, result: dict[str, Any]) -> None:
            if result.get("decision") in ("accept", "approved") or result.get("permissions"):
                budget.record_approval_allow()
            if operator is not None:
                operator.require_response_dispatch()
            attempt = budget.approval_deny_attempts + 1
            async def effect() -> tuple[bool, Any | None]:
                budget.reserve_deny_attempt()
                return await _finite_await(original_response(request, result), PROBE_APPROVAL_RESPONSE_TIMEOUT, stage="DENY_RESPONSE_NONCONVERGED")

            succeeded, value = await _dispatch_after_journal_intent(journal, f"DENY_RESPONSE_{attempt}_DISPATCH", effect, attempt=attempt)
            if succeeded:
                budget.record_deny_result(confirmed=True)
                approval_client.deny_response_count = budget.approval_deny_attempts
                journal.result(f"DENY_RESPONSE_{attempt}", "DENIED_CONFIRMED", attempt=attempt)
                return
            budget.record_deny_result(confirmed=False)
            approval_client.deny_response_count = budget.approval_deny_attempts
            journal.result(f"DENY_RESPONSE_{attempt}", "RESPONSE_UNKNOWN", attempt=attempt)
            if isinstance(value, BaseException):
                raise value
            raise RuntimeError("DENY_RESPONSE_NONCONVERGED")

        runtime.client.request = counted_request
        runtime.client.respond_server_request = counted_response
        catalog_adapter = CodexModelCatalogAdapter(manager)
        try:
            catalog = await asyncio.wait_for(catalog_adapter.get_catalog(profile.profile_id), PROBE_MODEL_LIST_TIMEOUT)
        except Exception:
            journal.result("MODEL_CATALOG", "INVALID")
            raise
        journal.result("MODEL_CATALOG", "CONFIRMED")
        defaults = tuple(model for model in catalog.models if model.is_default and not model.hidden)
        if len(defaults) != 1:
            raise RuntimeError("P7C8_MODEL_DEFAULT_AMBIGUOUS")
        model = defaults[0]
        thread_lifecycle = CodexThreadLifecycleAdapter(manager, catalog_adapter)
        turn_lifecycle = CodexTurnLifecycleAdapter(manager, catalog_adapter)
        thread = await asyncio.wait_for(thread_lifecycle.start(
            profile.profile_id, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            working_directory=TrustedWorkingDirectory(str(run.workdir)),
        ), PROBE_THREAD_START_TIMEOUT)
        journal.result("THREAD_START_ADAPTER", {
            ThreadOperationStatus.START_CONFIRMED: "START_CONFIRMED",
            ThreadOperationStatus.START_REJECTED: "START_REJECTED",
            ThreadOperationStatus.START_UNKNOWN: "START_UNKNOWN",
        }[thread.status])
        if thread.status is not ThreadOperationStatus.START_CONFIRMED or thread.binding is None:
            raise RuntimeError("P7C8_THREAD_START_NOT_CONFIRMED")
        thread_established = True
        turn_future = asyncio.get_running_loop().create_future()
        operator = DenyOnlyApprovalOperator(
            thread_id=thread.binding.thread_id, turn_id=turn_future, cwd=str(run.workdir), sentinel=str(run.sentinel),
            wire_authority=WireCommandAuthority(run.wire_recovery), request_journal=journal,
        )
        turn = await asyncio.wait_for(turn_lifecycle.start_turn(
            thread_binding=thread.binding, model_id=model.model_id, reasoning_effort=model.default_reasoning_effort,
            user_text=candidate_probe_prompt(str(run.sentinel)), working_directory=TrustedWorkingDirectory(str(run.workdir)),
        ), PROBE_TURN_START_TIMEOUT)
        journal.result("TURN_START_ADAPTER", {
            TurnStartStatus.CONFIRMED: "START_CONFIRMED",
            TurnStartStatus.REJECTED: "START_REJECTED",
            TurnStartStatus.UNKNOWN: "START_UNKNOWN",
        }[turn.status])
        if turn.status is not TurnStartStatus.CONFIRMED or turn.binding is None:
            raise RuntimeError("P7C8_PRIMARY_TURN_NOT_CONFIRMED")
        turn_future.set_result(turn.binding.turn_id)
        journal._append({"event": "TURN_ID_AUTHORITY", "result": "ESTABLISHED"})

        class _ExactTurnApprovalClient:
            deny_response_count = 0
            allow_response_count = 0

            async def next_server_request(self) -> Any:
                return await runtime.client.next_server_request()

            async def wait_terminal(self) -> str | None:
                terminal = await turn_lifecycle.wait_turn(turn.binding)
                return _terminal_value(getattr(terminal, "status", terminal))

            def owns_server_request(self, request: InboundServerRequest) -> bool:
                return runtime.client.owns_server_request(request)

            async def respond_server_request(self, request: InboundServerRequest, result: dict[str, Any]) -> None:
                operator.require_response_dispatch()
                return await runtime.client.respond_server_request(request, result)

        approval_client = _ExactTurnApprovalClient()
        bridge = CodexApprovalBridge(profile_id=profile.profile_id, client=approval_client, operator=operator)

        # The exact Turn authority is established before either observer is
        # created.  CodexProtocolClient has already buffered any fast request.
        journal._append({"event": "APPROVAL_OBSERVER_ARMED", "result": "YES"})
        observation = await _observe_future_race(
            bridge, approval_client, operator,
            lambda: turn_lifecycle.wait_turn(turn.binding),
        )
        terminal_status = _terminal_value(observation.terminal_status)
        outcome = observation.primary_outcome_class
        journal.result("TERMINAL_OBSERVATION", terminal_status or "NOT_ESTABLISHED")
        if outcome == OUTCOME_LIMIT:
            journal.result("REQUEST_LIMIT", "PROBE_APPROVAL_REQUEST_LIMIT_EXCEEDED")
        if observation.owner_nonconverged:
            journal._append({"event": "OWNER_NONCONVERGED", "class": "APPROVAL_OR_TERMINAL_OWNER"})
            raise RuntimeError("OWNER_NONCONVERGED")
        budget.reconcile()
    finally:
        if runtime is not None:
            journal.intent("RUNTIME_SHUTDOWN")
            shutdown_ok, shutdown_value = await _finite_await(manager.shutdown_profile(profile.profile_id), PROBE_RUNTIME_SHUTDOWN_TIMEOUT, stage="RUNTIME_SHUTDOWN_NONCONVERGED")
            shutdown_result = "CONFIRMED" if shutdown_ok else "NONCONVERGED"
            journal.result("RUNTIME_SHUTDOWN", shutdown_result)
        if runtime is not None and shutdown_result == "CONFIRMED":
            boundary = scan_fresh_run_boundary(run)
            journal.result("BOUNDARY_PROOF", boundary["classification"])
        else:
            journal.result("BOUNDARY_PROOF", "DEFERRED_TO_PARENT")

    if operator is None:
        # A child failure before a fresh thread has a safe observational shape.
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-child-unestablished", turn_id=asyncio.get_running_loop().create_future(),
            cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
    budget.reconcile()
    child_result = make_sanitized_result(
        terminal_status=terminal_status, operator=operator, run=run, boundary=boundary,
        outcome=outcome, source_sha=accepted_head, source_tree=accepted_tree, budget=budget,
        runtime_shutdown_result=shutdown_result, thread_established=thread_established, observation=observation,
    )
    journal.intent("CHILD_RESULT_WRITE")
    write_sanitized_result(run.root / CHILD_RESULT_FILENAME, child_result)
    journal.result("CHILD_RESULT_WRITE", "CONFIRMED")
    return child_result


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sentinel_touch_authority(path: Path) -> str:
    try:
        before = path.lstat()
        after = path.lstat()
    except FileNotFoundError:
        return SENTINEL_ABSENT
    except OSError:
        return "SENTINEL_INSPECTION_FAILED"
    safe = (
        stat.S_ISREG(before.st_mode)
        and before.st_uid == 0 and before.st_gid == 0 and before.st_nlink == 1
        and not (stat.S_IMODE(before.st_mode) & (stat.S_IWGRP | stat.S_IWOTH))
        and before.st_size == 0
        and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        and after.st_size == 0
    )
    return "EXPECTED_TOUCH" if safe else "UNEXPECTED_PROBE_MUTATION"


def _safe_runtime_payload(path: Path) -> tuple[bool, int]:
    """Validate runtime-owned roots without classifying normal DB/log files."""
    errors = 0
    if not _private_directory(path):
        return False, 1
    for directory, dirs, files in os.walk(path, topdown=True, followlinks=False):
        for name in (*dirs, *files):
            entry = Path(directory) / name
            try:
                value = entry.lstat()
            except OSError:
                errors += 1
                continue
            if stat.S_ISLNK(value.st_mode) or not stat.S_ISREG(value.st_mode) and not stat.S_ISDIR(value.st_mode):
                errors += 1
            if value.st_uid != 0 or value.st_gid != 0 or stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                errors += 1
    return errors == 0, errors


def scan_fresh_run_boundary(
    run: FreshProbeRun, *, phase: str = CHILD_PRE_RESULT,
    process_references: Sequence[Path] = (),
) -> dict[str, Any]:
    """Scan a run root with an exact child-result phase boundary.

    The child-result authority is absent during the child scan and is the one
    explicitly permitted harness sibling during the parent's post-quiescence
    scan.  It is still opened and validated through the same bounded,
    no-follow authority reader before it can be considered expected.
    """
    if phase not in (CHILD_PRE_RESULT, PARENT_POST_QUIESCENCE):
        raise ValueError("BOUNDARY_PHASE_INVALID")
    fixed = {"state-parent", "state-parent/p7c8-isolated-state", "controller", "workdir", "outside-workdir-sentinel",
             "probe-recovery.json", "wire-command-recovery.json", "probe-result.json", "probe-latch.json"}
    unexpected: list[str] = []
    for entry in run.root.iterdir():
        relative = _relative(entry, run.root)
        if relative in fixed:
            continue
        if relative == CHILD_RESULT_FILENAME and phase == PARENT_POST_QUIESCENCE:
            continue
        if relative == "state-parent/p7c8-isolated-state":
            continue
        unexpected.append(relative)
    for required_directory in (run.state_parent, run.isolated_state, run.sqlite, run.logs, run.controller, run.workdir):
        if not _private_directory(required_directory):
            unexpected.append(_relative(required_directory, run.root))
    runtime_ok, runtime_errors = True, 0
    for runtime_root in (run.sqlite, run.logs):
        okay, errors = _safe_runtime_payload(runtime_root)
        runtime_ok, runtime_errors = runtime_ok and okay, runtime_errors + errors
    for directory, dirs, files in os.walk(run.workdir, topdown=True, followlinks=False):
        for name in (*dirs, *files):
            unexpected.append(_relative(Path(directory) / name, run.root))
    for authority in (run.probe_recovery, run.wire_recovery, run.result, run.latch):
        if authority.exists() and (authority.is_symlink() or not _private_regular(authority)):
            unexpected.append(_relative(authority, run.root))
    child_result_path = run.root / CHILD_RESULT_FILENAME
    if phase == CHILD_PRE_RESULT:
        try:
            child_result_path.lstat()
        except FileNotFoundError:
            pass
        except OSError:
            unexpected.append("CHILD_RESULT_UNEXPECTED")
        else:
            unexpected.append("CHILD_RESULT_PRESENT_BEFORE_WRITE")
    else:
        try:
            child_result = read_bounded_private_json(child_result_path)
            validate_child_result(child_result)
        except (OSError, ValueError, AssertionError):
            unexpected.append("CHILD_RESULT_AUTHORITY_INVALID")
    for reference in process_references:
        if reference == run.root or run.root in reference.parents:
            unexpected.append("PROCESS_REFERENCE")
    touch_class = sentinel_touch_authority(run.sentinel)
    if touch_class == "UNEXPECTED_PROBE_MUTATION":
        unexpected.append("SENTINEL")
    if not runtime_ok:
        unexpected.append("RUNTIME_AUTHORITY")
    return {
        "sentinel_present": touch_class in ("EXPECTED_TOUCH", "UNEXPECTED_PROBE_MUTATION"),
        "sentinel_touch_authority_class": touch_class,
        "runtime_owned_state_valid": runtime_ok,
        "runtime_owned_scan_errors": runtime_errors,
        "classification": "UNEXPECTED_PROBE_MUTATION" if unexpected else "BOUNDARY_ONLY_EXPECTED_MUTATION",
        "unexpected_count": len(unexpected),
        "unexpected_labels": tuple(unexpected),
    }


def make_sanitized_result(*, terminal_status: str | None, operator: DenyOnlyApprovalOperator, run: FreshProbeRun, boundary: Mapping[str, Any], outcome: str, source_sha: str = ARCHITECT_BASE_SHA, source_tree: str = ARCHITECT_BASE_TREE, budget: FutureProbeBudget | None = None, runtime_shutdown_result: str = "NOT_ATTEMPTED", thread_established: bool = True, observation: ProbeObservation | None = None) -> dict[str, Any]:
    if observation is not None and not normal_child_result_allowed(observation):
        raise AssertionError("OWNER_NONCONVERGED_NO_NORMAL_RESULT")
    wire_sha = None
    vector_length = None
    vector_class = SENTINEL_VECTOR_UNKNOWN
    sentinel_class = SENTINEL_ABSENT
    if run.wire_recovery.exists():
        wire = read_wire_authority(run.wire_recovery)
        wire_sha = wire["wire_command_sha256"]
        vector = recover_wire_vector(wire["wire_command_plaintext"])
        vector_length = vector.vector_length if vector.established else None
        vector_class = "ESTABLISHED" if vector.established else SENTINEL_VECTOR_UNKNOWN
        sentinel_class = classify_sentinel_reference(wire["wire_command_plaintext"], operator.sentinel)
    result = {
        "status": "OBSERVATION_ONLY",
        "accepted_source_sha": source_sha,
        "accepted_source_tree": source_tree,
        "fresh_thread_sha256": _sha256(operator.thread_id) if thread_established else None,
        "fresh_turn_sha256": _sha256(operator.turn_id.result()) if operator.turn_id.done() else None,
        "request_count": len(operator.captures),
        "deny_response_count": budget.approval_deny_attempts if budget is not None else operator.response_count,
        "allow_response_count": 0,
        "primary_outcome_class": outcome,
        "terminal_status": terminal_status,
        "wire_command_sha256": wire_sha,
        "wire_vector_length": vector_length,
        "wire_vector_reconstruction_class": vector_class,
        "thread_identity_match": all(c.thread_match for c in operator.captures),
        "turn_identity_match": all(c.turn_match for c in operator.captures),
        "cwd_identity_match": all(c.cwd_match for c in operator.captures),
        "sentinel_reference_class": sentinel_class,
        "sentinel_present": bool(boundary["sentinel_present"]),
        "sentinel_touch_authority_class": boundary["sentinel_touch_authority_class"],
        "boundary_mutation_class": boundary["classification"],
        "observer_joined": True if observation is None else observation.observer_joined,
        "approval_owner_terminalized": True if observation is None else observation.approval_owner_terminalized,
        "terminal_owner_terminalized": True if observation is None else observation.terminal_owner_terminalized,
        "owner_nonconverged": False if observation is None else observation.owner_nonconverged,
        "model_list_calls": budget.model_list_calls if budget is not None else 0,
        "thread_start_calls": budget.thread_start_calls if budget is not None else 0,
        "thread_resume_calls": 0,
        "turn_start_calls": budget.turn_start_calls if budget is not None else 0,
        "approval_deny_responses": budget.approval_deny_responses if budget is not None else operator.response_count,
        "approval_deny_attempts": budget.approval_deny_attempts if budget is not None else operator.response_count,
        "approval_deny_confirmed": budget.approval_deny_confirmed if budget is not None else operator.response_count,
        "approval_deny_unknown_or_failed": budget.approval_deny_unknown_or_failed if budget is not None else 0,
        "approval_allow_responses": budget.approval_allow_responses if budget is not None else 0,
        "interrupt_calls": 0,
        "thread_delete_calls": 0,
        "thread_read_calls": 0,
        "thread_list_calls": 0,
        "request_limit_result": "PROBE_APPROVAL_REQUEST_LIMIT_EXCEEDED" if outcome == OUTCOME_LIMIT else "NOT_REACHED",
        "runtime_shutdown_result": runtime_shutdown_result,
        "boundary_proof_result": boundary["classification"],
        "child_result_authority": "CHILD_OBSERVATION_ONLY",
    }
    if "wire_command_plaintext" in result:
        raise AssertionError("RAW_COMMAND_IN_SANITIZED_RESULT")
    return result


def validate_sanitized_result(value: Mapping[str, Any]) -> None:
    required = {
        "status", "accepted_source_sha", "accepted_source_tree", "fresh_thread_sha256", "fresh_turn_sha256", "request_count",
        "deny_response_count", "allow_response_count", "primary_outcome_class", "terminal_status",
        "wire_command_sha256", "wire_vector_length", "wire_vector_reconstruction_class",
        "thread_identity_match", "turn_identity_match", "cwd_identity_match", "sentinel_reference_class",
        "terminal_status", "sentinel_present", "sentinel_touch_authority_class", "boundary_mutation_class",
        "observer_joined", "approval_owner_terminalized", "terminal_owner_terminalized", "owner_nonconverged",
        "model_list_calls", "thread_start_calls", "thread_resume_calls", "turn_start_calls",
        "approval_deny_responses", "approval_allow_responses", "interrupt_calls", "thread_delete_calls",
        "approval_deny_attempts", "approval_deny_confirmed", "approval_deny_unknown_or_failed",
        "thread_read_calls", "thread_list_calls", "request_limit_result", "runtime_shutdown_result",
        "boundary_proof_result", "child_result_authority",
    }
    if set(value) != required or value["allow_response_count"] != 0 or value["approval_allow_responses"] != 0:
        raise AssertionError("SANITIZED_RESULT_SCHEMA_INVALID")
    if (
        value["observer_joined"] is not True
        or value["approval_owner_terminalized"] is not True
        or value["terminal_owner_terminalized"] is not True
        or value["owner_nonconverged"] is not False
    ):
        raise AssertionError("OWNER_TERMINALIZATION_INVALID")
    for key in ("accepted_source_sha", "accepted_source_tree"):
        if not isinstance(value[key], str) or len(value[key]) != 40 or any(c not in "0123456789abcdef" for c in value[key]):
            raise AssertionError("SANITIZED_RESULT_SOURCE_INVALID")
    for key in ("fresh_thread_sha256", "fresh_turn_sha256", "wire_command_sha256"):
        if value[key] is not None and (not isinstance(value[key], str) or SHA256_RE.fullmatch(value[key]) is None):
            raise AssertionError("SANITIZED_RESULT_HASH_INVALID")
    if "wire_command_plaintext" in value or any(
        isinstance(item, str) and item.startswith("command: ")
        for item in value.values()
    ) or any(key in value for key in ("thread_id", "turn_id", "wire_command", "sentinel_path")):
        raise AssertionError("RAW_COMMAND_IN_SANITIZED_RESULT")


def _child_result_keys() -> frozenset[str]:
    return frozenset({
        "status", "accepted_source_sha", "accepted_source_tree", "fresh_thread_sha256", "fresh_turn_sha256", "request_count",
        "deny_response_count", "allow_response_count", "primary_outcome_class", "terminal_status", "wire_command_sha256",
        "wire_vector_length", "wire_vector_reconstruction_class", "thread_identity_match", "turn_identity_match",
        "cwd_identity_match", "sentinel_reference_class", "sentinel_present", "sentinel_touch_authority_class",
        "boundary_mutation_class", "observer_joined", "approval_owner_terminalized", "terminal_owner_terminalized",
        "owner_nonconverged", "model_list_calls", "thread_start_calls", "thread_resume_calls", "turn_start_calls",
        "approval_deny_responses", "approval_deny_attempts", "approval_deny_confirmed", "approval_deny_unknown_or_failed",
        "approval_allow_responses", "interrupt_calls", "thread_delete_calls", "thread_read_calls",
        "thread_list_calls", "request_limit_result", "runtime_shutdown_result", "boundary_proof_result", "child_result_authority",
    })


PARENT_RESULT_KEYS = frozenset(set(_child_result_keys()) | {
    "watchdog_status", "child_return_classification", "one_child_count", "second_child_started", "retry_count", "child_pid",
    "continuation_pgid", "continuation_sid", "group_active_count", "group_zombie_count", "group_scan_errors",
    "term_group_signal_count", "kill_group_signal_count", "signalled_parent_pgid", "second_pgid_targeted",
    "child_result_write_result", "parent_final_result_authority",
    "child_boundary_mutation_class", "parent_boundary_mutation_class", "boundary_drift_class",
    "child_sentinel_touch_class", "parent_sentinel_touch_class",
})


def normal_child_result_allowed(observation: ProbeObservation) -> bool:
    return (
        observation.observer_joined is True
        and observation.approval_owner_terminalized is True
        and observation.terminal_owner_terminalized is True
        and observation.owner_nonconverged is False
    )


def validate_child_result(value: Mapping[str, Any]) -> None:
    validate_sanitized_result(value)
    if set(value) != _child_result_keys() or value["child_result_authority"] != "CHILD_OBSERVATION_ONLY":
        raise AssertionError("CHILD_RESULT_SCHEMA_INVALID")
    if any(value[key] != 1 for key in ("model_list_calls", "thread_start_calls", "turn_start_calls")):
        raise AssertionError("CHILD_RESULT_NORMAL_LIFECYCLE_INVALID")
    for key in ("fresh_thread_sha256", "fresh_turn_sha256"):
        if not isinstance(value[key], str) or SHA256_RE.fullmatch(value[key]) is None:
            raise AssertionError("CHILD_RESULT_IDENTITY_HASH_INVALID")
    if any(value[key] != 0 for key in (
        "thread_resume_calls", "interrupt_calls", "thread_delete_calls", "thread_read_calls", "thread_list_calls",
    )):
        raise AssertionError("CHILD_RESULT_FORBIDDEN_EFFECT_INVALID")
    if value["approval_allow_responses"] != 0:
        raise AssertionError("CHILD_RESULT_ALLOW_EFFECT_INVALID")
    if any(key in value for key in ("process_group_final_active_count", "process_group_scan_errors", "group_active_count", "group_scan_errors")):
        raise AssertionError("CHILD_RESULT_CLAIMS_PARENT_AUTHORITY")


def make_parent_final_result(
    child: Mapping[str, Any], *, child_return_classification: str, one_child_count: int,
    second_child_started: str, retry_count: int, authority: Mapping[str, Any],
    snapshot: "ProcessGroupSnapshot", child_result_write_result: str = "CONFIRMED",
    parent_boundary: Mapping[str, Any] | None = None, watchdog_status: str = "PROCESS_COMPLETED",
) -> dict[str, Any]:
    validate_child_result(child)
    if parent_boundary is None:
        parent_boundary = {
            "classification": child["boundary_mutation_class"],
            "sentinel_present": child["sentinel_present"],
            "sentinel_touch_authority_class": child["sentinel_touch_authority_class"],
            "unexpected_labels": (),
        }
    child_boundary_class = str(child["boundary_mutation_class"])
    parent_boundary_class = str(parent_boundary["classification"])
    child_sentinel_class = str(child["sentinel_touch_authority_class"])
    parent_sentinel_class = str(parent_boundary["sentinel_touch_authority_class"])
    drift = (
        BOUNDARY_DRIFT_DETECTED
        if (
            child_boundary_class != parent_boundary_class
            or bool(child["sentinel_present"]) != bool(parent_boundary["sentinel_present"])
            or child_sentinel_class != parent_sentinel_class
            or tuple(child.get("unexpected_labels", ())) != tuple(parent_boundary.get("unexpected_labels", ()))
        )
        else BOUNDARY_DRIFT_NONE
    )
    result = dict(child)
    result.update({
        "watchdog_status": watchdog_status,
        "child_return_classification": child_return_classification,
        "one_child_count": one_child_count,
        "second_child_started": second_child_started,
        "retry_count": retry_count,
        "child_pid": authority["pid"],
        "continuation_pgid": authority["pgid"],
        "continuation_sid": authority["sid"],
        "group_active_count": len(snapshot.active_members),
        "group_zombie_count": len(snapshot.zombie_members),
        "group_scan_errors": snapshot.scan_errors,
        "term_group_signal_count": authority.get("term_count", 0),
        "kill_group_signal_count": authority.get("kill_count", 0),
        "signalled_parent_pgid": authority.get("signalled_parent_pgid", "NO"),
        "second_pgid_targeted": authority.get("second_pgid_targeted", "NO"),
        "child_result_write_result": child_result_write_result,
        "parent_final_result_authority": "PARENT_MEASURED_GROUP_AND_CHILD",
        "child_boundary_mutation_class": child_boundary_class,
        "parent_boundary_mutation_class": parent_boundary_class,
        "boundary_drift_class": drift,
        "child_sentinel_touch_class": child_sentinel_class,
        "parent_sentinel_touch_class": parent_sentinel_class,
    })
    validate_parent_final_result(result)
    return result


def validate_parent_final_result(value: Mapping[str, Any]) -> None:
    if set(value) != PARENT_RESULT_KEYS:
        raise AssertionError("PARENT_RESULT_SCHEMA_INVALID")
    validate_child_result({key: value[key] for key in _child_result_keys()})
    if (
        value["allow_response_count"] != 0 or value["approval_allow_responses"] != 0
        or value["model_list_calls"] != 1 or value["thread_start_calls"] != 1 or value["turn_start_calls"] != 1
        or any(value[key] != 0 for key in ("thread_resume_calls", "interrupt_calls", "thread_delete_calls", "thread_read_calls", "thread_list_calls"))
        or value["approval_deny_attempts"] > MAX_PROBE_APPROVAL_REQUESTS
        or value["approval_deny_attempts"] != value["approval_deny_confirmed"] + value["approval_deny_unknown_or_failed"]
        or value["approval_deny_responses"] != value["approval_deny_attempts"]
        or value["approval_deny_attempts"] != value["deny_response_count"]
        or value["group_active_count"] != 0 or value["group_scan_errors"] != 0
        or value["second_child_started"] != "NO" or value["retry_count"] != 0
        or value["term_group_signal_count"] > 1 or value["kill_group_signal_count"] > 1
        or value["signalled_parent_pgid"] != "NO" or value["second_pgid_targeted"] != "NO"
        or value["one_child_count"] != 1 or value["child_result_write_result"] != "CONFIRMED"
        or value["parent_final_result_authority"] != "PARENT_MEASURED_GROUP_AND_CHILD"
        or value["boundary_proof_result"] != "BOUNDARY_ONLY_EXPECTED_MUTATION"
        or value["parent_boundary_mutation_class"] != "BOUNDARY_ONLY_EXPECTED_MUTATION"
        or value["watchdog_status"] != "PROCESS_COMPLETED"
        or value["child_return_classification"] != CHILD_RETURN_COMPLETED
        or value["boundary_drift_class"] != BOUNDARY_DRIFT_NONE
    ):
        raise AssertionError("PARENT_RESULT_CONSISTENCY_INVALID")
    for key in ("accepted_source_sha", "accepted_source_tree"):
        if not isinstance(value[key], str) or len(value[key]) != 40:
            raise AssertionError("PARENT_RESULT_SOURCE_INVALID")


def make_parent_execution_outcome(
    *, execution_class: str, watchdog_status: str, child_returncode_class: str,
    child_result_present: bool, child_result_valid: bool,
    parent_boundary_class: str, boundary_drift_class: str,
    accepted_source_sha: str = ARCHITECT_BASE_SHA,
    accepted_source_tree: str = ARCHITECT_BASE_TREE,
    group_active_count: int = 0, group_zombie_count: int = 0,
    group_scan_errors: int = 0, term_group_signal_count: int = 0,
    kill_group_signal_count: int = 0, one_child_count: int = 1,
    second_child_started: str = "NO", retry_count: int = 0,
    global_latch_present: bool,
    normal_final_result_present: bool,
    child_result_discovery_class: str,
    runtime_acquire_initial_result: str | None = None,
    runtime_acquire_result: str = "RUNTIME_ACQUIRE_NOT_ESTABLISHED",
    runtime_acquire_error_category: str | None = None,
    runtime_acquire_cleanup_result: str | None = None,
    runtime_acquire_cleanup_error_category: str | None = None,
) -> dict[str, Any]:
    """Build the distinct, sanitized parent execution-outcome authority."""
    value = {
        "format": 1,
        "accepted_source_sha": accepted_source_sha,
        "accepted_source_tree": accepted_source_tree,
        "execution_class": execution_class,
        "watchdog_status": watchdog_status,
        "child_returncode_class": child_returncode_class,
        "child_result_present": child_result_present,
        "child_result_valid": child_result_valid,
        "parent_boundary_class": parent_boundary_class,
        "boundary_drift_class": boundary_drift_class,
        "group_active_count": group_active_count,
        "group_zombie_count": group_zombie_count,
        "group_scan_errors": group_scan_errors,
        "term_group_signal_count": term_group_signal_count,
        "kill_group_signal_count": kill_group_signal_count,
        "one_child_count": one_child_count,
        "second_child_started": second_child_started,
        "retry_count": retry_count,
        "global_latch_present": global_latch_present,
        "normal_final_result_present": normal_final_result_present,
        "child_result_discovery_class": child_result_discovery_class,
        "runtime_acquire_initial_result": runtime_acquire_initial_result,
        "runtime_acquire_result": runtime_acquire_result,
        "runtime_acquire_error_category": runtime_acquire_error_category,
        "runtime_acquire_cleanup_result": runtime_acquire_cleanup_result,
        "runtime_acquire_cleanup_error_category": runtime_acquire_cleanup_error_category,
    }
    validate_parent_execution_outcome(value)
    return value


def validate_parent_execution_outcome(value: Mapping[str, Any]) -> None:
    """Validate exact finite parent outcome fields and their fact matrix."""
    if set(value) != PARENT_OUTCOME_KEYS:
        raise AssertionError("PARENT_OUTCOME_SCHEMA_INVALID")
    if type(value["format"]) is not int or value["format"] != 1:
        raise AssertionError("PARENT_OUTCOME_FORMAT_INVALID")
    for key in ("accepted_source_sha", "accepted_source_tree"):
        if not isinstance(value[key], str) or re.fullmatch(r"[0-9a-f]{40}", value[key]) is None:
            raise AssertionError("PARENT_OUTCOME_SOURCE_INVALID")
    if value["execution_class"] not in PARENT_EXECUTION_CLASSES:
        raise AssertionError("PARENT_OUTCOME_CLASS_INVALID")
    if value["watchdog_status"] not in PARENT_OUTCOME_WATCHDOG_STATUSES:
        raise AssertionError("PARENT_OUTCOME_WATCHDOG_INVALID")
    if value["child_returncode_class"] not in CHILD_EXECUTION_CLASSES:
        raise AssertionError("PARENT_OUTCOME_CHILD_CLASS_INVALID")
    if type(value["child_result_present"]) is not bool or type(value["child_result_valid"]) is not bool:
        raise AssertionError("PARENT_OUTCOME_CHILD_RESULT_FLAGS_INVALID")
    if value["child_result_valid"] and not value["child_result_present"]:
        raise AssertionError("PARENT_OUTCOME_CHILD_RESULT_FLAGS_INCONSISTENT")
    if value["parent_boundary_class"] not in PARENT_OUTCOME_BOUNDARY_CLASSES:
        raise AssertionError("PARENT_OUTCOME_BOUNDARY_INVALID")
    if value["boundary_drift_class"] not in {BOUNDARY_DRIFT_NONE, BOUNDARY_DRIFT_DETECTED}:
        raise AssertionError("PARENT_OUTCOME_DRIFT_INVALID")
    if value["child_result_discovery_class"] not in CHILD_RESULT_DISCOVERY_CLASSES:
        raise AssertionError("PARENT_OUTCOME_DISCOVERY_INVALID")
    if value["runtime_acquire_initial_result"] is not None and value["runtime_acquire_initial_result"] not in {
        RuntimeAcquireClass.CONFIRMED, RuntimeAcquireClass.TIMEOUT, RuntimeAcquireClass.SAFE_EXCEPTION,
        RuntimeAcquireClass.UNEXPECTED_EXCEPTION, RuntimeAcquireClass.CANCELLATION_NONCONVERGENT,
    }:
        raise AssertionError("PARENT_OUTCOME_INITIAL_ACQUIRE_INVALID")
    if value["runtime_acquire_result"] not in {
        RuntimeAcquireClass.CONFIRMED, RuntimeAcquireClass.TIMEOUT, RuntimeAcquireClass.SAFE_EXCEPTION,
        RuntimeAcquireClass.UNEXPECTED_EXCEPTION, RuntimeAcquireClass.CANCELLATION_NONCONVERGENT,
        "RUNTIME_ACQUIRE_NOT_ESTABLISHED",
    }:
        raise AssertionError("PARENT_OUTCOME_ACQUIRE_INVALID")
    category = value["runtime_acquire_error_category"]
    if category is not None and category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and (
        category not in SAFE_RUNTIME_CATEGORIES or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", category) is None
    ):
        raise AssertionError("PARENT_OUTCOME_ACQUIRE_CATEGORY_INVALID")
    if value["runtime_acquire_result"] != RuntimeAcquireClass.SAFE_EXCEPTION and category is not None:
        raise AssertionError("PARENT_OUTCOME_ACQUIRE_CATEGORY_UNEXPECTED")
    if value["runtime_acquire_cleanup_result"] not in {None, "CONFIRMED", "SAFE_EXCEPTION", "TIMEOUT", "NONCONVERGENT"}:
        raise AssertionError("PARENT_OUTCOME_CLEANUP_INVALID")
    cleanup_category = value["runtime_acquire_cleanup_error_category"]
    if cleanup_category is not None and cleanup_category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and (
        cleanup_category not in SAFE_RUNTIME_CATEGORIES
        or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", cleanup_category) is None
    ):
        raise AssertionError("PARENT_OUTCOME_CLEANUP_CATEGORY_INVALID")
    if value["runtime_acquire_cleanup_result"] != "SAFE_EXCEPTION" and cleanup_category is not None:
        raise AssertionError("PARENT_OUTCOME_CLEANUP_CATEGORY_UNEXPECTED")
    if value["runtime_acquire_result"] == "RUNTIME_ACQUIRE_NOT_ESTABLISHED" and (
        value["runtime_acquire_initial_result"] is not None
        or category is not None
        or value["runtime_acquire_cleanup_result"] is not None
        or cleanup_category is not None
    ):
        raise AssertionError("PARENT_OUTCOME_NOT_ESTABLISHED_FACTS_INVALID")
    if value["child_result_valid"] and value["child_result_discovery_class"] != "CHILD_RESULT_DISCOVERY_CONFIRMED":
        raise AssertionError("PARENT_OUTCOME_DISCOVERY_FACTS_INVALID")
    if value["child_result_present"] and not value["child_result_valid"]:
        if value["child_result_discovery_class"] != "CHILD_RESULT_DISCOVERY_UNREADABLE":
            raise AssertionError("PARENT_OUTCOME_DISCOVERY_FACTS_INVALID")
    if not value["child_result_present"] and value["child_result_discovery_class"] == "CHILD_RESULT_DISCOVERY_CONFIRMED":
        raise AssertionError("PARENT_OUTCOME_DISCOVERY_FACTS_INVALID")
    for key in (
        "group_active_count", "group_zombie_count", "group_scan_errors",
        "term_group_signal_count", "kill_group_signal_count", "one_child_count", "retry_count",
    ):
        if type(value[key]) is not int or value[key] < 0 or value[key] > 1_000_000:
            raise AssertionError("PARENT_OUTCOME_COUNT_INVALID")
    if value["term_group_signal_count"] > 1 or value["kill_group_signal_count"] > 1:
        raise AssertionError("PARENT_OUTCOME_SIGNAL_COUNT_INVALID")
    if (
        value["second_child_started"] != "NO"
        or value["retry_count"] != 0
        or value["one_child_count"] != 1
    ):
        raise AssertionError("PARENT_OUTCOME_ONE_SHOT_INVALID")
    if type(value["global_latch_present"]) is not bool or type(value["normal_final_result_present"]) is not bool:
        raise AssertionError("PARENT_OUTCOME_AUTHORITY_FLAGS_INVALID")
    if value["execution_class"] == "PARENT_FINAL_RESULT_CONFIRMED":
        required = (
            value["watchdog_status"] == "PROCESS_COMPLETED",
            value["child_returncode_class"] == CHILD_RETURN_COMPLETED,
            value["child_result_present"] is True,
            value["child_result_valid"] is True,
            value["normal_final_result_present"] is True,
            value["global_latch_present"] is True,
            value["group_active_count"] == 0,
            value["group_scan_errors"] == 0,
            value["parent_boundary_class"] == "BOUNDARY_ONLY_EXPECTED_MUTATION",
            value["boundary_drift_class"] == BOUNDARY_DRIFT_NONE,
            value["child_result_discovery_class"] == "CHILD_RESULT_DISCOVERY_CONFIRMED",
            value["runtime_acquire_initial_result"] == RuntimeAcquireClass.CONFIRMED,
            value["runtime_acquire_result"] == RuntimeAcquireClass.CONFIRMED,
            value["runtime_acquire_error_category"] is None,
            value["runtime_acquire_cleanup_result"] is None,
            value["runtime_acquire_cleanup_error_category"] is None,
        )
        if not all(required):
            raise AssertionError("PARENT_OUTCOME_SUCCESS_FACTS_INVALID")
    elif value["normal_final_result_present"]:
        raise AssertionError("PARENT_OUTCOME_FAILURE_CLAIMS_NORMAL_RESULT")

    child_class = value["child_returncode_class"]
    execution_class = value["execution_class"]
    if execution_class == CHILD_RETURN_TIMEOUT:
        if child_class != CHILD_RETURN_TIMEOUT or value["watchdog_status"] != "PROCESS_WATCHDOG_TIMEOUT":
            raise AssertionError("PARENT_OUTCOME_TIMEOUT_FACTS_INVALID")
    elif execution_class == CHILD_GROUP_RESIDUAL:
        if child_class != CHILD_GROUP_RESIDUAL or value["watchdog_status"] != "PROCESS_GROUP_NOT_QUIESCENT":
            raise AssertionError("PARENT_OUTCOME_RESIDUAL_FACTS_INVALID")
    elif execution_class == CHILD_GROUP_SCAN_ERROR:
        if (
            child_class != CHILD_GROUP_SCAN_ERROR
            or value["watchdog_status"] != "PROCESS_GROUP_SCAN_ERROR"
            or value["group_scan_errors"] <= 0
        ):
            raise AssertionError("PARENT_OUTCOME_SCAN_FACTS_INVALID")
    elif execution_class == CHILD_RETURN_NONZERO:
        if (
            child_class != CHILD_RETURN_NONZERO
            or value["watchdog_status"] != "PROCESS_COMPLETED"
            or value["group_active_count"] != 0
            or value["group_scan_errors"] != 0
        ):
            raise AssertionError("PARENT_OUTCOME_NONZERO_FACTS_INVALID")
    elif execution_class == "CHILD_RESULT_MISSING_OR_INVALID":
        if (
            child_class != CHILD_RETURN_COMPLETED
            or value["watchdog_status"] != "PROCESS_COMPLETED"
            or value["normal_final_result_present"]
            or (value["child_result_present"] and value["child_result_valid"])
        ):
            raise AssertionError("PARENT_OUTCOME_CHILD_RESULT_FACTS_INVALID")
    elif execution_class == "PARENT_BOUNDARY_INVALID_OR_DRIFTED":
        if (
            child_class != CHILD_RETURN_COMPLETED
            or value["watchdog_status"] != "PROCESS_COMPLETED"
            or value["child_result_present"] is not True
            or value["child_result_valid"] is not True
            or value["normal_final_result_present"]
            or (
                value["parent_boundary_class"] == "BOUNDARY_ONLY_EXPECTED_MUTATION"
                and value["boundary_drift_class"] != BOUNDARY_DRIFT_DETECTED
            )
        ):
            raise AssertionError("PARENT_OUTCOME_BOUNDARY_FACTS_INVALID")
    elif execution_class == CHILD_RETURN_COMPLETED:
        raise AssertionError("PARENT_OUTCOME_COMPLETED_CLASS_INVALID")
    elif execution_class != "PARENT_FINAL_RESULT_CONFIRMED":
        raise AssertionError("PARENT_OUTCOME_CLASS_MATRIX_INVALID")
    if any(key in value for key in (
        "thread_id", "turn_id", "wire_command", "wire_command_plaintext", "sentinel_path", "prompt", "response",
        "credentials", "tokens",
    )):
        raise AssertionError("PARENT_OUTCOME_RAW_FIELD")


@dataclass(frozen=True)
class ProcessGroupSnapshot:
    active_members: tuple[int, ...]
    zombie_members: tuple[int, ...]
    scan_errors: int


def _proc_group_session(pid: int) -> tuple[str, int, int] | None:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    tail = raw.rsplit(")", 1)[1].split()
    if len(tail) < 4 or len(tail[0]) != 1:
        raise ValueError("PROC_STAT_MALFORMED")
    try:
        return tail[0], int(tail[2]), int(tail[3])
    except (TypeError, ValueError) as error:
        raise ValueError("PROC_STAT_MALFORMED") from error


def inspect_process_group(pgid: int) -> ProcessGroupSnapshot:
    members: list[int] = []
    zombies: list[int] = []
    errors = 0
    try:
        names = os.listdir("/proc")
    except OSError:
        return ProcessGroupSnapshot((), (), 1)
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        try:
            value = _proc_group_session(pid)
        except FileNotFoundError:
            # The PID was in the finite snapshot but exited before its stat
            # read.  That is ordinary process churn, not a scan failure.
            continue
        except (PermissionError, OSError, ValueError):
            errors += 1
            continue
        if value is None:
            errors += 1
            continue
        if value[1] == pgid and value[0] == "Z":
            zombies.append(pid)
        elif value[1] == pgid:
            members.append(pid)
    return ProcessGroupSnapshot(tuple(sorted(members)), tuple(sorted(zombies)), errors)


def classify_watchdog_child(watchdog: Mapping[str, Any]) -> str:
    """Classify from watchdog facts before consulting the child return code."""
    if int(watchdog.get("final_scan_errors", 0)) > 0 or watchdog.get("status") == "PROCESS_GROUP_SCAN_ERROR":
        return CHILD_GROUP_SCAN_ERROR
    if watchdog.get("final_active_members") or watchdog.get("status") == "PROCESS_GROUP_NOT_QUIESCENT":
        return CHILD_GROUP_RESIDUAL
    if bool(watchdog.get("timed_out")) or watchdog.get("status") == "PROCESS_WATCHDOG_TIMEOUT":
        return CHILD_RETURN_TIMEOUT
    return CHILD_RETURN_COMPLETED if watchdog.get("returncode") == 0 else CHILD_RETURN_NONZERO


class ExactProcessGroupSignalAuthority:
    """The sole signal path for one owned process group."""

    def __init__(self, pgid: int, parent_pgid: int, *, killpg: Any = os.killpg) -> None:
        if type(pgid) is not int or pgid <= 1 or pgid == parent_pgid:
            raise ValueError("PROCESS_GROUP_SIGNAL_AUTHORITY_INVALID")
        self.pgid = pgid
        self.parent_pgid = parent_pgid
        self.killpg = killpg
        self.history: list[tuple[int, int]] = []

    def dispatch(self, sig: int) -> None:
        if sig not in (signal.SIGTERM, signal.SIGKILL):
            raise ValueError("PROCESS_GROUP_SIGNAL_INVALID")
        if any(previous == sig for _, previous in self.history):
            raise AssertionError("PROCESS_GROUP_SIGNAL_ALREADY_DISPATCHED")
        self.killpg(self.pgid, sig)
        self.history.append((self.pgid, sig))


def derive_process_group_authority(process: subprocess.Popen[Any]) -> dict[str, int | str]:
    pid = process.pid
    pgid = os.getpgid(pid)
    sid = os.getsid(pid)
    parent_pgid = os.getpgrp()
    if pid != pgid or pid != sid or pgid <= 1 or pgid == parent_pgid:
        raise AssertionError("PROCESS_GROUP_AUTHORITY_INVALID")
    return {"pid": pid, "pgid": pgid, "sid": sid, "parent_pgid": parent_pgid, "authority": "PASS"}


def run_synthetic_watchdog(command: Sequence[str], *, deadline: float = 0.5, terminate_grace: float = 0.1, kill_grace: float = 0.2, killpg: Any | None = None) -> dict[str, Any]:
    process = subprocess.Popen(list(command), close_fds=True, start_new_session=True)
    authority = derive_process_group_authority(process)
    pgid = int(authority["pgid"])
    signal_authority = ExactProcessGroupSignalAuthority(pgid, int(authority["parent_pgid"]), killpg=killpg or os.killpg)
    timed_out = False
    try:
        try:
            process.wait(timeout=deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
            signal_authority.dispatch(signal.SIGTERM)
            try:
                process.wait(timeout=terminate_grace)
            except subprocess.TimeoutExpired:
                signal_authority.dispatch(signal.SIGKILL)
                try:
                    process.wait(timeout=kill_grace)
                except subprocess.TimeoutExpired:
                    pass

        snapshot = inspect_process_group(pgid)
        residual_detected = bool(snapshot.active_members)
        if snapshot.active_members:
            # A leader can exit while a descendant remains.  The same exact
            # group authority must converge it; a normal leader exit is not
            # accepted as quiescence.
            if not any(sig == signal.SIGTERM for _, sig in signal_authority.history):
                signal_authority.dispatch(signal.SIGTERM)
                try:
                    process.wait(timeout=terminate_grace)
                except subprocess.TimeoutExpired:
                    pass
                snapshot = inspect_process_group(pgid)
            if snapshot.active_members and not any(sig == signal.SIGKILL for _, sig in signal_authority.history):
                signal_authority.dispatch(signal.SIGKILL)
                try:
                    process.wait(timeout=kill_grace)
                except subprocess.TimeoutExpired:
                    pass
                snapshot = inspect_process_group(pgid)

        if snapshot.scan_errors:
            status = "PROCESS_GROUP_SCAN_ERROR"
        elif snapshot.active_members:
            status = "PROCESS_GROUP_NOT_QUIESCENT"
        elif timed_out:
            status = "PROCESS_WATCHDOG_TIMEOUT"
        elif residual_detected:
            status = "PROCESS_GROUP_NOT_QUIESCENT"
        else:
            status = "PROCESS_COMPLETED"
        authority.update({
            "term_count": sum(sig == signal.SIGTERM for _, sig in signal_authority.history),
            "kill_count": sum(sig == signal.SIGKILL for _, sig in signal_authority.history),
            "signalled_parent_pgid": "NO",
            "second_pgid_targeted": "NO",
        })
        return {
            "status": status,
            "timed_out": timed_out,
            "authority": authority,
            "term_count": authority["term_count"],
            "kill_count": authority["kill_count"],
            "signal_history": tuple(signal_authority.history),
            "final_active_members": snapshot.active_members,
            "final_zombie_members": snapshot.zombie_members,
            "final_scan_errors": snapshot.scan_errors,
            "returncode": process.returncode,
        }
    finally:
        # Cleanup never contains a hidden signal path.  The caller must have
        # explicitly dispatched TERM/KILL through the authority above.
        if process.poll() is None:
            try:
                process.wait(timeout=max(terminate_grace, kill_grace, 1.0))
            except subprocess.TimeoutExpired:
                pass


def _watch_existing_process(
    process: subprocess.Popen[Any], authority: Mapping[str, Any], *, deadline: float,
    terminate_grace: float, kill_grace: float, killpg: Any = os.killpg,
) -> dict[str, Any]:
    """Parent-owned watchdog for an already-created dedicated child."""
    mutable_authority = dict(authority)
    signal_authority = ExactProcessGroupSignalAuthority(
        int(mutable_authority["pgid"]), int(mutable_authority["parent_pgid"]), killpg=killpg,
    )
    timed_out = False
    residual_detected = False
    try:
        try:
            process.wait(timeout=deadline)
        except subprocess.TimeoutExpired:
            timed_out = True
            signal_authority.dispatch(signal.SIGTERM)
            try:
                process.wait(timeout=terminate_grace)
            except subprocess.TimeoutExpired:
                signal_authority.dispatch(signal.SIGKILL)
                try:
                    process.wait(timeout=kill_grace)
                except subprocess.TimeoutExpired:
                    pass
        snapshot = inspect_process_group(int(mutable_authority["pgid"]))
        residual_detected = bool(snapshot.active_members)
        if snapshot.active_members and not any(sig == signal.SIGTERM for _, sig in signal_authority.history):
            signal_authority.dispatch(signal.SIGTERM)
            try:
                process.wait(timeout=terminate_grace)
            except subprocess.TimeoutExpired:
                pass
            snapshot = inspect_process_group(int(mutable_authority["pgid"]))
        if snapshot.active_members and not any(sig == signal.SIGKILL for _, sig in signal_authority.history):
            signal_authority.dispatch(signal.SIGKILL)
            try:
                process.wait(timeout=kill_grace)
            except subprocess.TimeoutExpired:
                pass
            snapshot = inspect_process_group(int(mutable_authority["pgid"]))
        if snapshot.scan_errors:
            status = "PROCESS_GROUP_SCAN_ERROR"
        elif snapshot.active_members:
            status = "PROCESS_GROUP_NOT_QUIESCENT"
        elif residual_detected and not timed_out:
            status = "PROCESS_GROUP_NOT_QUIESCENT"
        elif timed_out:
            status = "PROCESS_WATCHDOG_TIMEOUT"
        else:
            status = "PROCESS_COMPLETED"
        mutable_authority.update({
            "term_count": sum(sig == signal.SIGTERM for _, sig in signal_authority.history),
            "kill_count": sum(sig == signal.SIGKILL for _, sig in signal_authority.history),
            "signalled_parent_pgid": "NO",
            "second_pgid_targeted": "NO",
        })
        return {
            "status": status, "timed_out": timed_out, "authority": mutable_authority,
            "final_active_members": snapshot.active_members,
            "final_zombie_members": snapshot.zombie_members,
            "final_scan_errors": snapshot.scan_errors,
            "returncode": process.returncode,
        }
    finally:
        if process.poll() is None:
            try:
                process.wait(timeout=max(terminate_grace, kill_grace, 1.0))
            except subprocess.TimeoutExpired:
                pass


def run_future_real_probe_parent() -> dict[str, Any]:
    """Launch exactly one future-probe child and own final authority."""
    accepted_head, accepted_tree = validate_future_source_authority()
    if not _private_directory(REAL_PROBE_LATCH.parent):
        raise RuntimeError("P7C8_LATCH_PARENT_INVALID")
    try:
        require_parent_execution_authorities_absent(REAL_PROBE_LATCH, REAL_PROBE_RESULT, REAL_PROBE_OUTCOME)
    except RuntimeError:
        raise RuntimeError("P7C8_ONE_SHOT_ALREADY_CONSUMED") from None
    child_parent = Path(tempfile.mkdtemp(prefix="codexcontrol-p7c8-parent-", dir="/tmp"))
    child = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--codexcontrol-p7c8-probe-child", str(child_parent)],
        close_fds=True, start_new_session=True,
    )
    authority = derive_process_group_authority(child)
    watchdog = _watch_existing_process(
        child, authority, deadline=PROBE_WATCHDOG_HARD_DEADLINE,
        terminate_grace=PROBE_TERM_GRACE_SECONDS, kill_grace=PROBE_KILL_GRACE_SECONDS,
    )
    child_return_classification = classify_watchdog_child(watchdog)
    snapshot = ProcessGroupSnapshot(
        tuple(watchdog["final_active_members"]), tuple(watchdog["final_zombie_members"]), watchdog["final_scan_errors"],
    )
    discovery = discover_child_result(child_parent)
    acquisition = recover_parent_acquisition_authority(discovery)
    runtime_acquire_initial_result = acquisition.initial_result
    runtime_acquire_result = acquisition.final_result
    runtime_acquire_error_category = acquisition.error_category
    runtime_acquire_cleanup_result = acquisition.cleanup_result
    runtime_acquire_cleanup_error_category = acquisition.cleanup_error_category

    def persist_failure(execution_class: str, *, child_result_present: bool = discovery.present,
                        child_result_valid: bool = discovery.valid,
                        child_result_discovery_class: str = discovery.classification,
                        parent_boundary_class: str = "BOUNDARY_NOT_PROVED",
                        boundary_drift_class: str = BOUNDARY_DRIFT_DETECTED) -> dict[str, Any]:
        latch_present, normal_result_present = measure_parent_authority_presence(
            REAL_PROBE_LATCH, REAL_PROBE_RESULT,
        )
        outcome = make_parent_execution_outcome(
            accepted_source_sha=accepted_head, accepted_source_tree=accepted_tree,
            execution_class=execution_class, watchdog_status=watchdog["status"],
            child_returncode_class=child_return_classification,
            child_result_present=child_result_present, child_result_valid=child_result_valid,
            parent_boundary_class=parent_boundary_class, boundary_drift_class=boundary_drift_class,
            group_active_count=len(snapshot.active_members), group_zombie_count=len(snapshot.zombie_members),
            group_scan_errors=snapshot.scan_errors,
            term_group_signal_count=watchdog["authority"].get("term_count", 0),
            kill_group_signal_count=watchdog["authority"].get("kill_count", 0),
            one_child_count=1, second_child_started="NO", retry_count=0,
            global_latch_present=latch_present,
            normal_final_result_present=normal_result_present,
            child_result_discovery_class=child_result_discovery_class,
            runtime_acquire_initial_result=runtime_acquire_initial_result,
            runtime_acquire_result=runtime_acquire_result,
            runtime_acquire_error_category=runtime_acquire_error_category,
            runtime_acquire_cleanup_result=runtime_acquire_cleanup_result,
            runtime_acquire_cleanup_error_category=runtime_acquire_cleanup_error_category,
        )
        # Exactly one exclusive persistence attempt.  A persistence failure
        # is returned as a finite failure without retrying the probe.
        try:
            write_parent_execution_outcome(REAL_PROBE_OUTCOME, outcome)
        except Exception as error:
            raise RuntimeError("PARENT_OUTCOME_PERSISTENCE_FAILED") from error
        return outcome

    if child_return_classification != CHILD_RETURN_COMPLETED:
        return persist_failure(child_return_classification)

    if not discovery.valid or discovery.run is None:
        return persist_failure(
            "CHILD_RESULT_MISSING_OR_INVALID", child_result_present=discovery.present,
            child_result_valid=discovery.valid,
        )
    child_run = discovery.run
    child_result_path = child_run.root / CHILD_RESULT_FILENAME
    try:
        child_value = read_bounded_private_json(child_result_path)
        validate_child_result(child_value)
    except (OSError, ValueError, AssertionError):
        return persist_failure(
            "CHILD_RESULT_MISSING_OR_INVALID", child_result_present=True,
            child_result_valid=False, child_result_discovery_class="CHILD_RESULT_DISCOVERY_UNREADABLE",
        )
    try:
        parent_boundary = scan_fresh_run_boundary(child_run, phase=PARENT_POST_QUIESCENCE)
    except (OSError, ValueError):
        return persist_failure(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", child_result_present=True, child_result_valid=True,
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
        )
    if parent_boundary["classification"] != "BOUNDARY_ONLY_EXPECTED_MUTATION":
        return persist_failure(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", child_result_present=True, child_result_valid=True,
            parent_boundary_class=parent_boundary["classification"],
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
        )
    if runtime_acquire_result != RuntimeAcquireClass.CONFIRMED:
        return persist_failure(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", child_result_present=True, child_result_valid=True,
            parent_boundary_class=parent_boundary["classification"],
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
        )
    try:
        final = make_parent_final_result(
            child_value,
            child_return_classification=CHILD_RETURN_COMPLETED,
            one_child_count=1, second_child_started="NO", retry_count=0,
            authority=watchdog["authority"], snapshot=snapshot,
            parent_boundary=parent_boundary, watchdog_status="PROCESS_COMPLETED",
        )
    except (AssertionError, ValueError):
        return persist_failure(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", child_result_present=True, child_result_valid=True,
            parent_boundary_class=parent_boundary["classification"],
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
        )
    if final["accepted_source_sha"] != accepted_head or final["accepted_source_tree"] != accepted_tree:
        return persist_failure(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", child_result_present=True, child_result_valid=True,
            parent_boundary_class=parent_boundary["classification"],
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
        )
    try:
        write_parent_final_result(REAL_PROBE_RESULT, final)
        global_latch_present, normal_final_result_present = measure_parent_authority_presence(
            REAL_PROBE_LATCH, REAL_PROBE_RESULT,
        )
        confirmed = make_parent_execution_outcome(
            accepted_source_sha=accepted_head, accepted_source_tree=accepted_tree,
            execution_class="PARENT_FINAL_RESULT_CONFIRMED", watchdog_status="PROCESS_COMPLETED",
            child_returncode_class=CHILD_RETURN_COMPLETED, child_result_present=True,
            child_result_valid=True, parent_boundary_class=parent_boundary["classification"],
            boundary_drift_class=BOUNDARY_DRIFT_NONE, group_active_count=0,
            group_zombie_count=len(snapshot.zombie_members), group_scan_errors=0,
            term_group_signal_count=watchdog["authority"].get("term_count", 0),
            kill_group_signal_count=watchdog["authority"].get("kill_count", 0),
            one_child_count=1, second_child_started="NO", retry_count=0,
            global_latch_present=global_latch_present,
            normal_final_result_present=normal_final_result_present,
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
            runtime_acquire_initial_result=runtime_acquire_initial_result,
            runtime_acquire_result=runtime_acquire_result,
            runtime_acquire_error_category=runtime_acquire_error_category,
            runtime_acquire_cleanup_result=runtime_acquire_cleanup_result,
            runtime_acquire_cleanup_error_category=runtime_acquire_cleanup_error_category,
        )
        write_parent_execution_outcome(REAL_PROBE_OUTCOME, confirmed)
    except Exception as error:
        raise RuntimeError("PARENT_OUTCOME_PERSISTENCE_FAILED") from error
    return final


class RuntimeAcquireClass:
    CONFIRMED = "RUNTIME_ACQUIRE_CONFIRMED"
    TIMEOUT = "RUNTIME_ACQUIRE_TIMEOUT"
    SAFE_EXCEPTION = "RUNTIME_ACQUIRE_SAFE_EXCEPTION"
    UNEXPECTED_EXCEPTION = "RUNTIME_ACQUIRE_UNEXPECTED_EXCEPTION"
    CANCELLATION_NONCONVERGENT = "RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT"


class CleanupClass:
    CONFIRMED = "CONFIRMED"
    SAFE_EXCEPTION = "SAFE_EXCEPTION"
    TIMEOUT = "TIMEOUT"
    NONCONVERGENT = "NONCONVERGENT"


@dataclass(frozen=True)
class AcquireObservation:
    result: str
    error_category: str | None = None
    acquire_owner_terminalized: bool = True
    cleanup_result: str | None = None
    cleanup_error_category: str | None = None
    raw_error_persisted: bool = False


def _safe_runtime_category(category: Any) -> str:
    if isinstance(category, str) and category in SAFE_RUNTIME_CATEGORIES and SAFE_CATEGORY_RE.fullmatch(category):
        return category
    return SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED


class RuntimeAcquireObserver:
    """Dedicated observer; it never uses the legacy generic await helper."""

    def __init__(
        self, *, timeout: float = P7C8_RUNTIME_ACQUIRE_TIMEOUT_SECONDS,
        cleanup_timeout: float = P7C8_RUNTIME_ACQUIRE_CLEANUP_TIMEOUT_SECONDS,
        cleanup_cancel_join: float = P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS,
    ) -> None:
        self.timeout = timeout
        self.cleanup_timeout = cleanup_timeout
        self.cleanup_cancel_join = cleanup_cancel_join

    async def observe(self, manager: Any, profile_id: str) -> tuple[AcquireObservation, asyncio.Task[Any]]:
        owner = asyncio.create_task(manager.acquire(profile_id))
        try:
            runtime = await asyncio.wait_for(asyncio.shield(owner), self.timeout)
            return AcquireObservation(RuntimeAcquireClass.CONFIRMED), owner
        except asyncio.TimeoutError:
            return AcquireObservation(RuntimeAcquireClass.TIMEOUT, acquire_owner_terminalized=owner.done()), owner
        except RuntimeErrorSafe as error:
            return AcquireObservation(RuntimeAcquireClass.SAFE_EXCEPTION, error_category=_safe_runtime_category(error.category)), owner
        except asyncio.CancelledError:
            return AcquireObservation(RuntimeAcquireClass.CANCELLATION_NONCONVERGENT, acquire_owner_terminalized=owner.done()), owner
        except Exception:
            return AcquireObservation(RuntimeAcquireClass.UNEXPECTED_EXCEPTION), owner

    async def contain(self, manager: Any, profile_id: str, owner: asyncio.Task[Any], observation: AcquireObservation, journal: RecoveryJournal | None = None) -> AcquireObservation:
        if observation.result == RuntimeAcquireClass.CONFIRMED:
            return observation
        if journal is not None:
            journal.intent("RUNTIME_ACQUIRE_CLEANUP")
            journal.assert_continuity()
        cleanup_result = CleanupClass.CONFIRMED
        cleanup_category: str | None = None
        cleanup_task: asyncio.Task[Any] | None = None
        try:
            cleanup_task = asyncio.create_task(manager.shutdown_profile(profile_id))
            cleanup = await asyncio.wait_for(asyncio.shield(cleanup_task), self.cleanup_timeout)
            if isinstance(cleanup, RuntimeErrorSafe):
                cleanup_result, cleanup_category = CleanupClass.SAFE_EXCEPTION, _safe_runtime_category(cleanup.category)
        except RuntimeErrorSafe as error:
            cleanup_result, cleanup_category = CleanupClass.SAFE_EXCEPTION, _safe_runtime_category(error.category)
        except asyncio.TimeoutError:
            cleanup_result = CleanupClass.TIMEOUT
            if cleanup_task is None:
                cleanup_result = CleanupClass.NONCONVERGENT
            else:
                # This is the sole cancellation of the sole cleanup task.
                cleanup_task.cancel()
                if not await _bounded_task_join(cleanup_task, self.cleanup_cancel_join, cancel=False):
                    cleanup_result = CleanupClass.NONCONVERGENT
        except Exception:
            cleanup_result = CleanupClass.NONCONVERGENT
        if journal is not None:
            journal.result("RUNTIME_ACQUIRE_CLEANUP", cleanup_result)
            if cleanup_category is not None:
                journal._append({"event": "RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY", "result": cleanup_category})
        joined = await _join_task(owner, self.cleanup_cancel_join)
        result = observation.result
        if not joined:
            result = RuntimeAcquireClass.CANCELLATION_NONCONVERGENT
        if cleanup_result == CleanupClass.NONCONVERGENT:
            result = RuntimeAcquireClass.CANCELLATION_NONCONVERGENT
        return AcquireObservation(result, observation.error_category, joined, cleanup_result, cleanup_category)


async def _join_task(task: asyncio.Task[Any], timeout: float) -> bool:
    return await _bounded_task_join(task, timeout, cancel=True)


async def _bounded_task_join(task: asyncio.Task[Any], timeout: float, *, cancel: bool) -> bool:
    if cancel and not task.done():
        task.cancel()
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout)
    except asyncio.TimeoutError:
        return False
    except BaseException:
        return True
    return True


@dataclass(frozen=True)
class ParentAcquisitionAuthority:
    initial_result: str | None
    final_result: str
    error_category: str | None = None
    cleanup_result: str | None = None
    cleanup_error_category: str | None = None


def _not_established_acquisition() -> ParentAcquisitionAuthority:
    return ParentAcquisitionAuthority(None, "RUNTIME_ACQUIRE_NOT_ESTABLISHED")


def recover_parent_acquisition_authority(discovery: ChildResultDiscovery) -> ParentAcquisitionAuthority:
    """Reconstruct acquisition facts fail-closed from one validated journal."""
    if discovery.run is None:
        return _not_established_acquisition()
    try:
        records = read_authoritative_recovery_journal(discovery.run.probe_recovery)
    except (OSError, ValueError):
        return _not_established_acquisition()

    def event_records(name: str) -> list[dict[str, Any]]:
        return [record for record in records if record.get("event") == name]

    source = event_records("SOURCE_GATE")
    latch = event_records("GLOBAL_LATCH_RESERVED")
    intent = event_records("RUNTIME_ACQUIRE_INTENT")
    initial = event_records("RUNTIME_ACQUIRE_RESULT")
    final = event_records("RUNTIME_ACQUIRE_FINAL_RESULT")
    if not (len(source) == len(latch) == len(intent) == len(initial) == len(final) == 1):
        return _not_established_acquisition()
    initial_values = {
        "CONFIRMED": RuntimeAcquireClass.CONFIRMED,
        "TIMEOUT": RuntimeAcquireClass.TIMEOUT,
        "SAFE_EXCEPTION": RuntimeAcquireClass.SAFE_EXCEPTION,
        "UNEXPECTED_EXCEPTION": RuntimeAcquireClass.UNEXPECTED_EXCEPTION,
        "CANCELLATION_NONCONVERGENT": RuntimeAcquireClass.CANCELLATION_NONCONVERGENT,
    }
    final_values = dict(initial_values)
    if initial[0].get("result") not in initial_values or final[0].get("result") not in final_values:
        return _not_established_acquisition()
    initial_result = initial_values[initial[0]["result"]]
    final_result = final_values[final[0]["result"]]
    positions = {id(record): index for index, record in enumerate(records)}
    if not (
        positions[id(source[0])] < positions[id(latch[0])] < positions[id(intent[0])] < positions[id(initial[0])] < positions[id(final[0])]
    ):
        return _not_established_acquisition()
    if source[0].get("result") != "PASS" or latch[0].get("result") != "YES" or intent[0].get("status") != "PENDING":
        return _not_established_acquisition()

    acquire_categories = event_records("RUNTIME_ACQUIRE_ERROR_CATEGORY")
    cleanup_intents = event_records("RUNTIME_ACQUIRE_CLEANUP_INTENT")
    cleanup_results = event_records("RUNTIME_ACQUIRE_CLEANUP_RESULT")
    cleanup_categories = event_records("RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY")
    if len(acquire_categories) > 1 or len(cleanup_intents) > 1 or len(cleanup_results) > 1 or len(cleanup_categories) > 1:
        return _not_established_acquisition()
    error_category = acquire_categories[0].get("result") if acquire_categories else None
    if error_category is not None and (
        initial_result != RuntimeAcquireClass.SAFE_EXCEPTION
        or (error_category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and error_category not in SAFE_RUNTIME_CATEGORIES)
        or (error_category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and SAFE_CATEGORY_RE.fullmatch(error_category) is None)
    ):
        return _not_established_acquisition()
    if acquire_categories and not positions[id(acquire_categories[0])] > positions[id(initial[0])]:
        return _not_established_acquisition()

    if initial_result == RuntimeAcquireClass.CONFIRMED:
        if final_result != RuntimeAcquireClass.CONFIRMED or cleanup_intents or cleanup_results or cleanup_categories or acquire_categories:
            return _not_established_acquisition()
        return ParentAcquisitionAuthority(initial_result, final_result)

    if len(cleanup_intents) != 1 or len(cleanup_results) != 1:
        return _not_established_acquisition()
    cleanup_values = {"CONFIRMED", "SAFE_EXCEPTION", "TIMEOUT", "NONCONVERGENT"}
    cleanup_value = cleanup_results[0].get("result")
    if cleanup_value not in cleanup_values:
        return _not_established_acquisition()
    if not (
        positions[id(initial[0])] < positions[id(cleanup_intents[0])] < positions[id(cleanup_results[0])] < positions[id(final[0])]
    ):
        return _not_established_acquisition()
    cleanup_category = cleanup_categories[0].get("result") if cleanup_categories else None
    if cleanup_category is not None and (
        cleanup_value != "SAFE_EXCEPTION"
        or (cleanup_category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and cleanup_category not in SAFE_RUNTIME_CATEGORIES)
        or (cleanup_category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and SAFE_CATEGORY_RE.fullmatch(cleanup_category) is None)
        or not positions[id(cleanup_categories[0])] > positions[id(cleanup_results[0])]
    ):
        return _not_established_acquisition()
    if final_result == RuntimeAcquireClass.CONFIRMED:
        return _not_established_acquisition()
    if final_result not in {initial_result, RuntimeAcquireClass.CANCELLATION_NONCONVERGENT}:
        return _not_established_acquisition()
    if cleanup_value == CleanupClass.NONCONVERGENT and final_result != RuntimeAcquireClass.CANCELLATION_NONCONVERGENT:
        return _not_established_acquisition()
    return ParentAcquisitionAuthority(initial_result, final_result, error_category, cleanup_value, cleanup_category)


class SyntheticAcquireManager:
    """A local manager seam that models shielded startup ownership."""

    def __init__(self, fixture: str) -> None:
        self.fixture = fixture
        self.startup_task: asyncio.Task[Any] | None = None
        self.shutdown_calls = 0
        self.cleanup_fixture: str | None = None
        self.cleanup_nonconvergent = False
        self.cleanup_task: asyncio.Task[Any] | None = None
        self.downstream = {name: 0 for name in ("model/list", "thread/start", "turn/start", "approval")}
        self.release = asyncio.Event()

    async def acquire(self, profile_id: str) -> Any:
        if self.fixture == "confirmed":
            return object()
        if self.fixture.startswith("safe:"):
            raise RuntimeErrorSafe(self.fixture.split(":", 1)[1], profile_id)
        if self.fixture == "unexpected":
            raise RuntimeError("secret-ish synthetic message")
        if self.fixture == "timeout":
            self.startup_task = asyncio.create_task(self.release.wait())
            return await asyncio.shield(self.startup_task)
        if self.fixture == "owner_nonconvergent":
            self.startup_task = asyncio.create_task(self.release.wait())
            try:
                return await asyncio.shield(self.startup_task)
            except asyncio.CancelledError:
                while not self.release.is_set():
                    try:
                        await self.release.wait()
                    except asyncio.CancelledError:
                        continue
                return object()
        raise AssertionError("unknown synthetic acquire fixture")

    async def shutdown_profile(self, profile_id: str) -> Any:
        self.shutdown_calls += 1
        self.cleanup_task = asyncio.current_task()
        fixture = self.cleanup_fixture or self.fixture
        if fixture == "cleanup_safe":
            raise RuntimeErrorSafe("storage_boundary_invalid", profile_id)
        if fixture == "cleanup_timeout":
            await asyncio.sleep(10)
        if fixture == "cleanup_nonconvergent":
            self.cleanup_nonconvergent = True
            while not self.release.is_set():
                try:
                    await self.release.wait()
                except asyncio.CancelledError:
                    # Test-only cancellation-resistant cleanup fixture.  The
                    # external release event is the only way it terminalizes.
                    continue
        if self.startup_task is not None and not self.startup_task.done():
            self.startup_task.cancel()
            await asyncio.gather(self.startup_task, return_exceptions=True)
        return None


def safe_runtime_parent_outcome(observation: AcquireObservation, *, normal_final_result_present: bool = False) -> dict[str, Any]:
    category = observation.error_category
    if category is not None and category != SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED and (
        category not in SAFE_RUNTIME_CATEGORIES or SAFE_CATEGORY_RE.fullmatch(category) is None
    ):
        category = SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED
    return {
        "runtime_acquire_initial_result": observation.result,
        "runtime_acquire_result": observation.result,
        "runtime_acquire_error_category": category,
        "runtime_acquire_cleanup_result": observation.cleanup_result,
        "runtime_acquire_cleanup_error_category": observation.cleanup_error_category,
        "normal_final_result_present": normal_final_result_present,
    }



class RuntimeAcquireOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def _observe(self, fixture: str, *, timeout: float = 0.03) -> tuple[AcquireObservation, SyntheticAcquireManager]:
        manager = SyntheticAcquireManager(fixture)
        observation, owner = await RuntimeAcquireObserver(timeout=timeout, cleanup_timeout=0.03).observe(manager, PROFILE_ID)
        if observation.result != RuntimeAcquireClass.CONFIRMED:
            observation = await RuntimeAcquireObserver(timeout=timeout, cleanup_timeout=0.03).contain(manager, PROFILE_ID, owner, observation)
        manager.release.set()
        if manager.startup_task is not None:
            await asyncio.gather(manager.startup_task, return_exceptions=True)
        await asyncio.gather(owner, return_exceptions=True)
        return observation, manager

    async def test_confirmed_acquire_is_distinct(self) -> None:
        observation, manager = await self._observe("confirmed")
        self.assertEqual(observation.result, RuntimeAcquireClass.CONFIRMED)
        self.assertEqual(manager.shutdown_calls, 0)

    async def test_safe_categories_are_preserved_without_text(self) -> None:
        for category in sorted(SAFE_RUNTIME_CATEGORIES):
            observation, _ = await self._observe("safe:" + category)
            self.assertEqual(observation.result, RuntimeAcquireClass.SAFE_EXCEPTION)
            self.assertEqual(observation.error_category, category)
            self.assertNotIn("profile=", json.dumps(safe_runtime_parent_outcome(observation)))

    async def test_unexpected_exception_is_fixed_class_and_sanitized(self) -> None:
        observation, _ = await self._observe("unexpected")
        self.assertEqual(observation.result, RuntimeAcquireClass.UNEXPECTED_EXCEPTION)
        encoded = json.dumps(safe_runtime_parent_outcome(observation))
        self.assertNotIn("secret-ish", encoded)
        self.assertNotIn("RuntimeError", encoded)

    async def test_timeout_is_not_exception(self) -> None:
        observation, manager = await self._observe("timeout")
        self.assertEqual(observation.result, RuntimeAcquireClass.TIMEOUT)
        self.assertEqual(observation.cleanup_result, CleanupClass.CONFIRMED)
        self.assertEqual(manager.shutdown_calls, 1)

    async def test_owner_cancellation_nonconvergence_is_distinct(self) -> None:
        observation, manager = await self._observe("owner_nonconvergent")
        self.assertEqual(observation.result, RuntimeAcquireClass.CANCELLATION_NONCONVERGENT)
        self.assertFalse(observation.acquire_owner_terminalized)
        manager.release.set()

    async def test_outer_timeout_does_not_cancel_internal_startup_before_containment(self) -> None:
        manager = SyntheticAcquireManager("timeout")
        observer = RuntimeAcquireObserver(timeout=0.01, cleanup_timeout=0.03)
        observation, owner = await observer.observe(manager, PROFILE_ID)
        self.assertEqual(observation.result, RuntimeAcquireClass.TIMEOUT)
        self.assertIsNotNone(manager.startup_task)
        self.assertFalse(manager.startup_task.done())
        observation = await observer.contain(manager, PROFILE_ID, owner, observation)
        self.assertEqual(observation.cleanup_result, CleanupClass.CONFIRMED)
        manager.release.set()
        await asyncio.gather(manager.startup_task, return_exceptions=True)

    async def test_cleanup_safe_exception_timeout_and_nonconvergence_are_separate(self) -> None:
        for fixture, expected in (("cleanup_safe", CleanupClass.SAFE_EXCEPTION), ("cleanup_timeout", CleanupClass.TIMEOUT), ("cleanup_nonconvergent", CleanupClass.NONCONVERGENT)):
            manager = SyntheticAcquireManager("timeout")
            manager.cleanup_fixture = fixture
            observation, owner = await RuntimeAcquireObserver(timeout=0.01, cleanup_timeout=0.01).observe(manager, PROFILE_ID)
            observation = await RuntimeAcquireObserver(timeout=0.01, cleanup_timeout=0.01).contain(manager, PROFILE_ID, owner, observation)
            self.assertEqual(observation.cleanup_result, expected)
            manager.release.set()
            await asyncio.gather(owner, return_exceptions=True)

    async def test_cancellation_resistant_cleanup_returns_before_external_release(self) -> None:
        manager = SyntheticAcquireManager("timeout")
        manager.cleanup_fixture = "cleanup_nonconvergent"
        observer = RuntimeAcquireObserver(timeout=0.01, cleanup_timeout=0.01, cleanup_cancel_join=0.02)
        observation, owner = await observer.observe(manager, PROFILE_ID)
        started = time.monotonic()
        observation = await observer.contain(manager, PROFILE_ID, owner, observation)
        elapsed = time.monotonic() - started
        self.assertEqual(observation.cleanup_result, CleanupClass.NONCONVERGENT)
        self.assertEqual(observation.result, RuntimeAcquireClass.CANCELLATION_NONCONVERGENT)
        self.assertLess(elapsed, 0.20)
        self.assertFalse(manager.release.is_set())
        self.assertIsNotNone(manager.cleanup_task)
        manager.release.set()
        await asyncio.gather(manager.cleanup_task, owner, return_exceptions=True)

    async def test_cleanup_safe_category_uses_separate_event_without_typeerror(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-cleanup-category-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
            manager = SyntheticAcquireManager("timeout")
            manager.cleanup_fixture = "cleanup_safe"
            observation, owner = await RuntimeAcquireObserver(
                timeout=0.01, cleanup_timeout=0.03,
            ).observe(manager, PROFILE_ID)
            observation = await RuntimeAcquireObserver(
                timeout=0.01, cleanup_timeout=0.03,
            ).contain(manager, PROFILE_ID, owner, observation, journal)
            self.assertEqual(observation.cleanup_result, CleanupClass.SAFE_EXCEPTION)
            self.assertEqual(observation.cleanup_error_category, "storage_boundary_invalid")
            records = read_authoritative_recovery_journal(run.probe_recovery)
            self.assertEqual(
                [record["result"] for record in records if record["event"] == "RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY"],
                ["storage_boundary_invalid"],
            )

    async def test_unrecognized_safe_category_is_fixed_and_not_published_raw(self) -> None:
        observation, _ = await self._observe("safe:syntactically_safe_but_unrecognized")
        self.assertEqual(observation.result, RuntimeAcquireClass.SAFE_EXCEPTION)
        self.assertEqual(observation.error_category, SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED)
        self.assertNotIn("syntactically_safe_but_unrecognized", json.dumps(safe_runtime_parent_outcome(observation)))

    async def test_failed_acquire_has_zero_downstream_effects(self) -> None:
        for fixture in ("timeout", "unexpected", "safe:capability_mismatch", "owner_nonconvergent"):
            observation, manager = await self._observe(fixture)
            self.assertNotEqual(observation.result, RuntimeAcquireClass.CONFIRMED)
            self.assertEqual(manager.downstream, {"model/list": 0, "thread/start": 0, "turn/start": 0, "approval": 0})



class Repair1AcquisitionAuthorityOfflineTests(unittest.TestCase):
    @staticmethod
    def _write_journal(
        run: FreshProbeRun, *, initial: str = "CONFIRMED", final: str | None = "CONFIRMED",
        acquire_category: str | None = None, cleanup: str | None = None,
        cleanup_category: str | None = None, duplicate_final: bool = False,
        conflicting_final: bool = False,
    ) -> ChildResultDiscovery:
        journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
        journal._append({"event": "GLOBAL_LATCH_RESERVED", "result": "YES"})
        journal.intent("RUNTIME_ACQUIRE")
        journal.result("RUNTIME_ACQUIRE", initial)
        if acquire_category is not None:
            journal._append({"event": "RUNTIME_ACQUIRE_ERROR_CATEGORY", "result": acquire_category})
        if cleanup is not None:
            journal.intent("RUNTIME_ACQUIRE_CLEANUP")
            journal.result("RUNTIME_ACQUIRE_CLEANUP", cleanup)
            if cleanup_category is not None:
                journal._append({"event": "RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY", "result": cleanup_category})
        if final is not None:
            journal.result("RUNTIME_ACQUIRE_FINAL", final)
            if duplicate_final or conflicting_final:
                journal.result("RUNTIME_ACQUIRE_FINAL", "SAFE_EXCEPTION" if conflicting_final else final)
        return ChildResultDiscovery(run, True, True, "CHILD_RESULT_DISCOVERY_CONFIRMED")

    def test_complete_safe_runtime_category_set_matches_reviewed_production_paths(self) -> None:
        self.assertEqual(SAFE_RUNTIME_CATEGORIES, frozenset({
            "capability_mismatch", "manager_shutting_down", "unknown_profile", "profile_reserved",
            "profile_stopping", "unresolved_process", "storage_boundary_invalid", "executable_invalid",
            "process_streams_missing", "initialize_failed", "initialize_timeout", "startup_failed",
            "kill_reap_timeout",
        }))
        self.assertTrue(all(SAFE_CATEGORY_RE.fullmatch(category) for category in SAFE_RUNTIME_CATEGORIES))

    def test_success_and_failed_chronologies_are_final_result_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-acquire-authority-") as directory:
            root = Path(directory)
            success_run = FreshProbeRun.materialize(root)
            success = recover_parent_acquisition_authority(self._write_journal(success_run))
            self.assertEqual(success, ParentAcquisitionAuthority(RuntimeAcquireClass.CONFIRMED, RuntimeAcquireClass.CONFIRMED))
            failed_run = FreshProbeRun.materialize(root)
            failed = recover_parent_acquisition_authority(self._write_journal(
                failed_run, initial="TIMEOUT", final="TIMEOUT", cleanup="CONFIRMED",
            ))
            self.assertEqual(failed.initial_result, RuntimeAcquireClass.TIMEOUT)
            self.assertEqual(failed.final_result, RuntimeAcquireClass.TIMEOUT)
            self.assertEqual(failed.cleanup_result, CleanupClass.CONFIRMED)

    def test_parent_negative_matrix_is_never_normal_success(self) -> None:
        cases = (
            "no_child_run", "ambiguous_child_root", "missing_journal", "unsafe_journal", "symlink_journal",
            "hardlinked_journal", "wrong_mode", "oversize", "malformed_jsonl", "unknown_field",
            "missing_final", "duplicate_final", "conflicting_final", "invalid_final", "confirmed_without_confirmed_initial",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="p7c8-acquire-negative-") as directory:
                root = Path(directory)
                if case in {"no_child_run", "ambiguous_child_root"}:
                    authority = recover_parent_acquisition_authority(
                        ChildResultDiscovery(None, False, False, "CHILD_RESULT_DISCOVERY_" + case.upper()),
                    )
                else:
                    run = FreshProbeRun.materialize(root)
                    discovery = self._write_journal(run)
                    path = run.probe_recovery
                    if case == "missing_journal":
                        path.unlink()
                    elif case == "unsafe_journal":
                        path.chmod(0o640)
                    elif case == "symlink_journal":
                        target = root / "journal-target"
                        os.replace(path, target)
                        path.symlink_to(target)
                    elif case == "hardlinked_journal":
                        target = root / "journal-target"
                        os.replace(path, target)
                        os.link(target, path)
                    elif case == "wrong_mode":
                        path.chmod(0o640)
                    elif case == "oversize":
                        path.write_bytes(b"x" * (MAX_RECOVERY_JOURNAL_BYTES + 1))
                        path.chmod(0o600)
                    elif case == "malformed_jsonl":
                        path.write_bytes(b"{\n")
                        path.chmod(0o600)
                    elif case == "unknown_field":
                        path.write_bytes(b'{"event":"SOURCE_GATE","result":"PASS","UNKNOWN_FIELD":true}\n')
                        path.chmod(0o600)
                    elif case == "missing_final":
                        path.unlink()
                        discovery = self._write_journal(run, final=None)
                    elif case == "duplicate_final":
                        path.unlink()
                        discovery = self._write_journal(run, duplicate_final=True)
                    elif case == "conflicting_final":
                        path.unlink()
                        discovery = self._write_journal(run, initial="TIMEOUT", final="TIMEOUT", cleanup="CONFIRMED", conflicting_final=True)
                    elif case == "invalid_final":
                        path.unlink()
                        discovery = self._write_journal(run, final="INVALID")
                    elif case == "confirmed_without_confirmed_initial":
                        path.unlink()
                        discovery = self._write_journal(run, initial="TIMEOUT", final="CONFIRMED", cleanup="CONFIRMED")
                    authority = recover_parent_acquisition_authority(discovery)
                self.assertEqual(authority.final_result, "RUNTIME_ACQUIRE_NOT_ESTABLISHED")
                self.assertNotEqual(authority.final_result, RuntimeAcquireClass.CONFIRMED)

    def test_parent_final_outcome_rejects_not_established_and_nonconfirmed_final(self) -> None:
        for result in (
            "RUNTIME_ACQUIRE_NOT_ESTABLISHED", RuntimeAcquireClass.TIMEOUT,
            RuntimeAcquireClass.SAFE_EXCEPTION, RuntimeAcquireClass.UNEXPECTED_EXCEPTION,
            RuntimeAcquireClass.CANCELLATION_NONCONVERGENT,
        ):
            with self.subTest(result=result):
                with self.assertRaises(AssertionError):
                    make_parent_execution_outcome(
                        execution_class="PARENT_FINAL_RESULT_CONFIRMED", watchdog_status="PROCESS_COMPLETED",
                        child_returncode_class=CHILD_RETURN_COMPLETED, child_result_present=True,
                        child_result_valid=True, parent_boundary_class="BOUNDARY_ONLY_EXPECTED_MUTATION",
                        boundary_drift_class=BOUNDARY_DRIFT_NONE, global_latch_present=True,
                        normal_final_result_present=True, child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
                        runtime_acquire_initial_result=RuntimeAcquireClass.CONFIRMED,
                        runtime_acquire_result=result,
                    )


class DenyOnlyApprovalOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory(prefix="p7c8-synthetic-")
        self.root = Path(self.directory.name)
        self.run = FreshProbeRun.materialize(self.root)
        self.turn_id = asyncio.get_running_loop().create_future()
        self.turn_id.set_result("synthetic-turn-id")
        self.client = SyntheticApprovalClient()
        self.operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread-id", turn_id=self.turn_id, cwd=str(self.run.workdir),
            sentinel=str(self.run.sentinel), wire_authority=WireCommandAuthority(self.run.wire_recovery),
        )
        self.client.response_observer = self.operator
        self.bridge = CodexApprovalBridge(profile_id="synthetic-profile", client=self.client, operator=self.operator)

    async def asyncTearDown(self) -> None:
        self.directory.cleanup()

    def _params(self, *, thread: str = "synthetic-thread-id", turn: str = "synthetic-turn-id", cwd: str | None = None, command: str | None = None) -> dict[str, Any]:
        return {
            "itemId": "synthetic-item", "startedAtMs": 1, "threadId": thread, "turnId": turn,
            "cwd": cwd if cwd is not None else str(self.run.workdir),
            "command": command if command is not None else "synthetic-executable --bounded 30",
        }

    async def _deny(self, params: Mapping[str, Any], *, request_id: str = "synthetic-request") -> Any:
        request = self.client.offer(params=params, request_id=request_id)
        return await self.bridge.handle_request(request)

    async def test_exact_request_is_captured_and_denied(self) -> None:
        result = await self._deny(self._params())
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertEqual(self.client.responses[-1]["result"], {"decision": "decline"})
        self.assertEqual(self.operator.allow_count, 0)
        self.assertEqual(self.operator.captures[0].request_count, 1)
        self.assertEqual(self.operator.captures[0].kind, ApprovalKind.COMMAND_EXECUTION)
        self.assertEqual(self.operator.captures[0].sentinel_reference_class, SENTINEL_ABSENT)
        self.assertTrue(self.operator.captures[0].thread_match)
        self.assertTrue(_private_regular(self.run.wire_recovery))
        raw = read_wire_authority(self.run.wire_recovery)
        self.assertEqual(raw["wire_command_sha256"], _sha256("synthetic-executable --bounded 30"))

    async def test_wrong_thread_does_not_consume_then_exact_request_captures(self) -> None:
        result = await self._deny(self._params(thread="wrong-thread"), request_id="wrong-thread")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertFalse(self.run.wire_recovery.exists())
        result = await self._deny(self._params(), request_id="exact-after-thread")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertTrue(self.run.wire_recovery.exists())

    async def test_wrong_turn_does_not_consume_then_exact_request_captures(self) -> None:
        result = await self._deny(self._params(turn="wrong-turn"), request_id="wrong-turn")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertFalse(self.run.wire_recovery.exists())
        result = await self._deny(self._params(), request_id="exact-after-turn")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertTrue(self.run.wire_recovery.exists())

    async def test_wrong_cwd_does_not_consume_then_exact_request_captures(self) -> None:
        result = await self._deny(self._params(cwd="/synthetic/wrong-cwd"), request_id="wrong-cwd")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertFalse(self.run.wire_recovery.exists())
        result = await self._deny(self._params(), request_id="exact-after-cwd")
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertTrue(self.run.wire_recovery.exists())

    async def test_identity_mismatches_and_missing_values_are_denied_without_authority(self) -> None:
        cases = [self._params(thread="wrong-thread"), self._params(thread=None), self._params(turn="wrong-turn"), self._params(turn=None), self._params(cwd="/synthetic/wrong-cwd")]
        for index, params in enumerate(cases):
            with self.subTest(index=index):
                result = await self._deny(params, request_id=f"mismatch-{index}")
                self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertFalse(self.run.wire_recovery.exists())
        self.assertEqual(self.operator.allow_count, 0)
        self.assertTrue(any(not capture.thread_match for capture in self.operator.captures))
        self.assertTrue(any(not capture.turn_match for capture in self.operator.captures))
        self.assertTrue(any(not capture.cwd_match for capture in self.operator.captures))

    async def test_unsupported_kind_and_malformed_production_inbound_fail_closed(self) -> None:
        unsupported = self.client.offer_unsupported(method="future/unsupportedApproval", params={}, request_id="unsupported")
        with self.assertRaises(ApprovalError):
            await self.bridge.handle_request(unsupported)
        malformed = self.client.offer(params={"itemId": "synthetic-item"}, request_id="malformed")
        result = await self.bridge.handle_request(malformed)
        self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertEqual(self.client.responses[-1]["result"], {"decision": "decline"})
        direct = ApprovalRequest(1, "synthetic-profile", "wire", ApprovalKind.FILE_CHANGE, "t", "u", "i", ())
        self.assertEqual(await self.operator.decide(direct), ApprovalDecision.DENY)
        self.assertEqual(self.operator.allow_count, 0)

    async def test_turn_identity_future_is_fail_closed_until_confirmation(self) -> None:
        pending_turn = asyncio.get_running_loop().create_future()
        operator = DenyOnlyApprovalOperator(thread_id="synthetic-thread-id", turn_id=pending_turn, cwd=str(self.run.workdir), sentinel=str(self.run.sentinel))
        request = ApprovalRequest(1, "synthetic-profile", "wire", ApprovalKind.COMMAND_EXECUTION, "synthetic-thread-id", "unconfirmed-turn", "item", (f"cwd: {self.run.workdir}", "command: synthetic-command"))
        self.assertEqual(await operator.decide(request), ApprovalDecision.DENY)
        self.assertFalse(operator.captures[0].turn_match)

    async def test_three_requests_are_denied_and_no_fourth_response_path_is_used(self) -> None:
        for index in range(MAX_PROBE_APPROVAL_REQUESTS):
            result = await self._deny(self._params(command=f"synthetic-executable --request {index}"), request_id=f"bounded-{index}")
            self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
        self.assertEqual(len(self.client.responses), MAX_PROBE_APPROVAL_REQUESTS)
        self.assertEqual(self.operator.allow_count, 0)
        fourth = self.client.offer(params=self._params(), request_id="bounded-fourth")
        self.assertIn(fourth.request_id, self.client.pending)
        self.assertEqual(len(self.client.responses), MAX_PROBE_APPROVAL_REQUESTS)

    def test_ast_operator_has_no_allow_decision_value(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "DenyOnlyApprovalOperator")
        decide_node = next(node for node in class_node.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "decide")
        allow_values = [node for node in ast.walk(decide_node) if isinstance(node, ast.Attribute) and node.attr == "ALLOW"]
        self.assertEqual(allow_values, [])
        returns = [node for node in ast.walk(decide_node) if isinstance(node, ast.Return)]
        self.assertEqual(len(returns), 1)
        self.assertIsInstance(returns[0].value, ast.Attribute)
        self.assertEqual(returns[0].value.attr, "DENY")


class RaceOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def _fixture(self, *, terminal_status: str = "COMPLETED") -> tuple[FreshProbeRun, SyntheticApprovalClient, DenyOnlyApprovalOperator, CodexApprovalBridge]:
        root = Path(tempfile.mkdtemp(prefix="p7c8-race-"))
        self.addCleanup(shutil.rmtree, root, True)
        run = FreshProbeRun.materialize(root)
        future = asyncio.get_running_loop().create_future()
        future.set_result("synthetic-turn-id")
        client = SyntheticApprovalClient(terminal_status=terminal_status)
        operator = DenyOnlyApprovalOperator(thread_id="synthetic-thread-id", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel), wire_authority=WireCommandAuthority(run.wire_recovery))
        client.response_observer = operator
        return run, client, operator, CodexApprovalBridge(profile_id="synthetic-profile", client=client, operator=operator)

    async def test_terminal_completes_before_approval_is_finite_and_observer_joined(self) -> None:
        _, client, operator, bridge = await self._fixture()
        client.terminal.set()
        result = await observe_probe_turn(bridge, client, operator)
        self.assertEqual(result.primary_outcome_class, OUTCOME_TERMINAL_FIRST)
        self.assertEqual(result.request_count, 0)
        self.assertTrue(result.observer_joined)

    async def test_approval_arrives_before_terminal_is_denied_then_terminal_observed(self) -> None:
        _, client, operator, bridge = await self._fixture()
        observing = asyncio.create_task(observe_probe_turn(bridge, client, operator))
        await asyncio.sleep(0)
        request = client.offer(params={"itemId": "item", "startedAtMs": 1, "threadId": "synthetic-thread-id", "turnId": "synthetic-turn-id", "cwd": "/tmp/synthetic", "command": "synthetic-command --bounded"})
        # Keep the identity authority exact for this independent race fixture.
        operator.cwd = "/tmp/synthetic"
        await client.enqueue(request)
        while not client.responses:
            await asyncio.sleep(0)
        await asyncio.sleep(0)
        client.terminal.set()
        result = await observing
        self.assertEqual(result.primary_outcome_class, OUTCOME_APPROVAL_FIRST)
        self.assertEqual(result.deny_response_count, 1)
        self.assertEqual(result.allow_response_count, 0)

    async def test_queued_before_observer_exact_turn_is_captured_and_denied(self) -> None:
        run, client, operator, bridge = await self._fixture()
        request = client.offer(params={
            "itemId": "queued-item", "startedAtMs": 1, "threadId": "synthetic-thread-id",
            "turnId": "synthetic-turn-id", "cwd": str(run.workdir), "command": "synthetic-command --queued",
        }, request_id="queued-before-observer")
        await client.enqueue(request)
        # The future was resolved before this observer starts, matching the
        # production Turn-ID ordering; the queue itself is the authority seam.
        self.assertTrue(client.queue.qsize() == 1)
        observing = asyncio.create_task(observe_probe_turn(bridge, client, operator))
        while not client.responses:
            await asyncio.sleep(0)
        client.terminal.set()
        result = await observing
        self.assertEqual(result.primary_outcome_class, OUTCOME_APPROVAL_FIRST)
        self.assertEqual(client.deny_response_count, 1)
        self.assertEqual(client.allow_response_count, 0)
        self.assertTrue(run.wire_recovery.exists())

    async def test_queued_wrong_thread_is_denied_without_wire_authority(self) -> None:
        run, client, operator, bridge = await self._fixture()
        request = client.offer(params={
            "itemId": "queued-item", "startedAtMs": 1, "threadId": "wrong-thread",
            "turnId": "synthetic-turn-id", "cwd": str(run.workdir), "command": "synthetic-command --queued",
        }, request_id="queued-wrong-thread")
        await client.enqueue(request)
        observing = asyncio.create_task(observe_probe_turn(bridge, client, operator))
        while not client.responses:
            await asyncio.sleep(0)
        client.terminal.set()
        result = await observing
        self.assertEqual(result.deny_response_count, 1)
        self.assertFalse(run.wire_recovery.exists())

    async def test_approval_and_terminal_same_tick_is_ambiguous_and_no_double_response(self) -> None:
        _, client, operator, bridge = await self._fixture()
        request = client.offer(params={"itemId": "item", "startedAtMs": 1, "threadId": "synthetic-thread-id", "turnId": "synthetic-turn-id", "cwd": str(Path("/tmp/synthetic")), "command": "synthetic-command"})
        await client.enqueue(request)
        client.terminal.set()
        result = await observe_probe_turn(bridge, client, operator)
        self.assertEqual(result.primary_outcome_class, OUTCOME_AMBIGUOUS)
        self.assertLessEqual(result.deny_response_count, 1)
        self.assertEqual(result.allow_response_count, 0)
        self.assertTrue(result.observer_joined)

    async def test_response_unknown_is_explicit_ambiguous_state(self) -> None:
        statuses = (ApprovalHandlingStatus.RESPONSE_UNKNOWN,)
        self.assertEqual(
            classify_race(terminal_status="COMPLETED", approval_statuses=statuses, deny_response_count=0, request_dequeued=True),
            OUTCOME_AMBIGUOUS,
        )

    async def test_nonconvergence_is_watchdog_class(self) -> None:
        self.assertEqual(
            classify_race(terminal_status=None, approval_statuses=(), deny_response_count=0, request_dequeued=False, converged=False),
            OUTCOME_NONCONVERGENT,
        )

    async def test_protocol_terminal_is_finite(self) -> None:
        _, client, operator, bridge = await self._fixture(terminal_status="FAULTED")
        client.terminal.set()
        result = await observe_probe_turn(bridge, client, operator)
        self.assertEqual(result.primary_outcome_class, OUTCOME_PROTOCOL)
        self.assertEqual(result.terminal_status, "FAULTED")

    async def test_approval_observer_ignoring_cancellation_has_finite_owner_classification(self) -> None:
        release = asyncio.Event()

        async def stubborn() -> None:
            while not release.is_set():
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    continue

        task = asyncio.create_task(stubborn())
        await asyncio.sleep(0)
        self.assertFalse(await _cancel_and_join(task, timeout=0.01))
        release.set()
        self.assertTrue(await _cancel_and_join(task, timeout=0.2))

    async def test_successful_synthetic_completion_has_no_pending_observer(self) -> None:
        _, client, operator, bridge = await self._fixture()
        client.terminal.set()
        result = await observe_probe_turn(bridge, client, operator)
        self.assertTrue(result.observer_joined)

    async def test_three_request_observation_stops_at_frozen_limit(self) -> None:
        _, client, operator, bridge = await self._fixture()
        for index in range(MAX_PROBE_APPROVAL_REQUESTS):
            await client.enqueue(client.offer(params={"itemId": "item", "startedAtMs": 1, "threadId": "synthetic-thread-id", "turnId": "synthetic-turn-id", "cwd": "/synthetic", "command": f"synthetic-command {index}"}, request_id=f"limit-{index}"))
        result = await observe_probe_turn(bridge, client, operator)
        self.assertEqual(result.primary_outcome_class, OUTCOME_LIMIT)
        self.assertEqual(result.request_count, MAX_PROBE_APPROVAL_REQUESTS)
        self.assertEqual(result.deny_response_count, MAX_PROBE_APPROVAL_REQUESTS)
        self.assertEqual(result.allow_response_count, 0)


class JournalOfflineTests(unittest.IsolatedAsyncioTestCase):
    async def test_journal_identity_continuity_matrix_is_fail_closed(self) -> None:
        import unittest.mock as mock

        with tempfile.TemporaryDirectory(prefix="p7c8-journal-continuity-") as directory:
            root = Path(directory)
            path = root / "recovery.jsonl"
            journal = RecoveryJournal(path, source_sha="a" * 40, source_tree="b" * 40)
            original_identity = journal._original_identity
            self.assertIsNotNone(original_identity)
            journal.intent("FIRST")
            journal.result("FIRST", "CONFIRMED")
            self.assertEqual(
                journal._original_identity,
                (path.stat().st_dev, path.stat().st_ino),
            )
            self.assertEqual(path.stat().st_nlink, 1)

            for replacement in ("unlink", "regular", "symlink", "hardlink", "mode", "owner"):
                with self.subTest(replacement=replacement):
                    case_root = root / replacement
                    case_root.mkdir(mode=0o700)
                    case_path = case_root / "recovery.jsonl"
                    case_journal = RecoveryJournal(case_path, source_sha="a" * 40, source_tree="b" * 40)
                    replacement_source: Path | None = None
                    if replacement == "regular":
                        replacement_source = case_root / "regular-target"
                        write_exclusive_private_json(replacement_source, {"synthetic": "replacement"})
                    if case_path.exists() or case_path.is_symlink():
                        case_path.unlink()
                    if replacement == "unlink":
                        pass
                    elif replacement == "regular":
                        assert replacement_source is not None
                        os.replace(replacement_source, case_path)
                    elif replacement == "symlink":
                        target = case_root / "symlink-target"
                        write_exclusive_private_json(target, {"synthetic": "target"})
                        case_path.symlink_to(target)
                    elif replacement == "hardlink":
                        target = case_root / "hardlink-target"
                        write_exclusive_private_json(target, {"synthetic": "target"})
                        os.link(target, case_path)
                    elif replacement == "mode":
                        write_exclusive_private_json(case_path, {"synthetic": "mode"})
                        case_path.chmod(0o640)
                    else:
                        write_exclusive_private_json(case_path, {"synthetic": "owner"})
                        if hasattr(os, "chown"):
                            os.chown(case_path, 65534, 65534)
                        else:
                            self.skipTest("owner mutation unavailable")
                    with self.assertRaises((OSError, ValueError)):
                        case_journal.result("REPLACEMENT", "MUST_NOT_APPEND")
                    if replacement == "unlink":
                        self.assertFalse(case_path.exists())

            swap_root = root / "swap"
            swap_root.mkdir(mode=0o700)
            swap_path = swap_root / "recovery.jsonl"
            swap_journal = RecoveryJournal(swap_path, source_sha="a" * 40, source_tree="b" * 40)
            replacement_path = swap_root / "swap-target"
            write_exclusive_private_json(replacement_path, {"synthetic": "swap-target"})
            original_write_all = _write_all
            swapped = False

            def swap_before_write(fd: int, payload: bytes) -> None:
                nonlocal swapped
                os.replace(replacement_path, swap_path)
                swapped = True
                original_write_all(fd, payload)

            with mock.patch(__name__ + "._write_all", side_effect=swap_before_write):
                with self.assertRaises(ValueError):
                    swap_journal.result("PATH_SWAP", "MUST_FAIL")
            self.assertTrue(swapped)

    async def test_journal_initial_creation_is_exclusive_and_appends_keep_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-journal-create-") as directory:
            path = Path(directory) / "recovery.jsonl"
            journal = RecoveryJournal(path, source_sha="a" * 40, source_tree="b" * 40)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_nlink, 1)
            identity = journal._original_identity
            for index in range(3):
                journal.result(f"SEQUENTIAL_{index}", "CONFIRMED")
                self.assertEqual(journal._original_identity, identity)
                self.assertEqual((path.stat().st_dev, path.stat().st_ino), identity)

    async def test_journal_intent_failure_blocks_model_thread_turn_and_deny_effects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-journal-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            for stage in ("MODEL_LIST_WIRE_DISPATCH", "THREAD_START_WIRE_DISPATCH", "TURN_START_WIRE_DISPATCH", "DENY_RESPONSE_1_DISPATCH"):
                journal = RecoveryJournal(run.root / f"{stage}.jsonl", source_sha="a" * 40, source_tree="b" * 40)
                calls = 0

                def fail_intent(*args: Any, **kwargs: Any) -> None:
                    raise OSError("synthetic journal failure")

                journal.intent = fail_intent  # type: ignore[method-assign]

                async def effect() -> None:
                    nonlocal calls
                    calls += 1

                with self.assertRaises(OSError):
                    await _dispatch_after_journal_intent(journal, stage, effect)
                self.assertEqual(calls, 0, stage)

    async def test_journal_continuity_failure_does_not_dispatch_effect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-journal-effect-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
            journal.path.unlink()
            calls = 0

            async def effect() -> None:
                nonlocal calls
                calls += 1

            with self.assertRaises(ValueError):
                await _dispatch_after_journal_intent(journal, "MUST_NOT_DISPATCH", effect)
            self.assertEqual(calls, 0)

    async def test_ambiguous_deny_consumes_one_authoritative_attempt(self) -> None:
        budget = FutureProbeBudget()
        budget.reserve_deny_attempt()
        budget.record_deny_result(confirmed=False)
        budget.reconcile()
        self.assertEqual(budget.approval_deny_attempts, 1)
        self.assertEqual(budget.approval_deny_confirmed, 0)
        self.assertEqual(budget.approval_deny_unknown_or_failed, 1)
        self.assertEqual(budget.approval_allow_responses, 0)

    async def test_request_observed_is_durable_before_deny_intent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-request-journal-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
            future = asyncio.get_running_loop().create_future()
            future.set_result("synthetic-turn")
            operator = DenyOnlyApprovalOperator(
                thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
                wire_authority=WireCommandAuthority(run.wire_recovery), request_journal=journal,
            )
            client = SyntheticApprovalClient(response_gate=operator.require_response_dispatch)
            client.response_intent = lambda: journal.intent("DENY_RESPONSE_1_DISPATCH", attempt=1)
            bridge = CodexApprovalBridge(profile_id="synthetic-profile", client=client, operator=operator)
            request = client.offer(params={
                "itemId": "item", "startedAtMs": 1, "threadId": "synthetic-thread", "turnId": "synthetic-turn",
                "cwd": str(run.workdir), "command": "synthetic-command",
            })
            result = await bridge.handle_request(request)
            self.assertEqual(result.status, ApprovalHandlingStatus.DENIED)
            events = [record["event"] for record in read_journal_records(run.probe_recovery)]
            self.assertLess(events.index("APPROVAL_REQUEST_1_OBSERVED"), events.index("DENY_RESPONSE_1_DISPATCH_INTENT"))
            observed = read_journal_records(run.probe_recovery)[events.index("APPROVAL_REQUEST_1_OBSERVED")]
            self.assertNotIn("thread_id", observed)
            self.assertNotIn("turn_id", observed)
            self.assertNotIn("sentinel_path", observed)
            self.assertNotIn("command", observed)

    async def test_request_journal_failure_blocks_response_and_deny_attempt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-request-journal-fail-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
            def fail_observed(*args: Any, **kwargs: Any) -> None:
                raise OSError("REQUEST_JOURNAL_FAILS")
            journal.approval_request_observed = fail_observed  # type: ignore[method-assign]
            future = asyncio.get_running_loop().create_future()
            future.set_result("synthetic-turn")
            operator = DenyOnlyApprovalOperator(
                thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
                request_journal=journal,
            )
            client = SyntheticApprovalClient(response_gate=operator.require_response_dispatch)
            attempts: list[int] = []
            client.response_intent = lambda: attempts.append(1)
            bridge = CodexApprovalBridge(profile_id="synthetic-profile", client=client, operator=operator)
            request = client.offer(params={
                "itemId": "item", "startedAtMs": 1, "threadId": "synthetic-thread", "turnId": "synthetic-turn",
                "cwd": str(run.workdir), "command": "synthetic-command",
            })
            result = await bridge.handle_request(request)
            self.assertEqual(result.status, ApprovalHandlingStatus.RESPONSE_UNKNOWN)
            self.assertEqual(client.response_calls, 0)
            self.assertEqual(attempts, [])
            self.assertEqual(operator.response_count, 0)


class Repair3AuthorityOfflineTests(unittest.TestCase):
    def _child(self, run: FreshProbeRun) -> dict[str, Any]:
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("synthetic-turn")
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
        child = make_sanitized_result(
            terminal_status="COMPLETED", operator=operator, run=run,
            boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
            budget=synthetic_normal_budget(),
        )
        loop.close()
        return child

    def _parent(self, child: Mapping[str, Any], *, watchdog_status: str = "PROCESS_COMPLETED") -> dict[str, Any]:
        authority = {
            "pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
            "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO",
        }
        return make_parent_final_result(
            child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
            second_child_started="NO", retry_count=0, authority=authority,
            snapshot=ProcessGroupSnapshot((), (), 0), watchdog_status=watchdog_status,
        )

    def test_parent_writer_persists_parent_schema_and_child_writer_rejects_it(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-parent-writer-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            parent = self._parent(child)
            with self.assertRaises(AssertionError):
                write_sanitized_result(run.result, parent)
            write_parent_final_result(run.result, parent)
            self.assertEqual(read_bounded_private_json(run.result), parent)
            for mutation in ("missing", "extra"):
                invalid = dict(parent)
                if mutation == "missing":
                    invalid.pop("watchdog_status")
                else:
                    invalid["unexpected_parent_field"] = True
                with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                    validate_parent_final_result(invalid)

    def test_parent_writer_rejects_active_group_scan_error_and_bad_effects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-parent-invalid-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            authority = {"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
                         "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"}
            for snapshot in (ProcessGroupSnapshot((101,), (), 0), ProcessGroupSnapshot((), (), 1)):
                with self.subTest(snapshot=snapshot), self.assertRaises(AssertionError):
                    make_parent_final_result(
                        child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
                        second_child_started="NO", retry_count=0, authority=authority, snapshot=snapshot,
                    )
            bad = self._parent(child)
            bad["approval_deny_attempts"] = 4
            with self.assertRaises(AssertionError):
                validate_parent_final_result(bad)

    def test_parent_recheck_detects_late_sentinel_and_workdir_drift(self) -> None:
        for mutation in ("sentinel", "workdir"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix="p7c8-drift-") as directory:
                run = FreshProbeRun.materialize(Path(directory))
                child_boundary = scan_fresh_run_boundary(run)
                if mutation == "sentinel":
                    run.sentinel.touch(mode=0o600)
                else:
                    (run.workdir / "late-file").write_bytes(b"synthetic")
                parent_boundary = scan_fresh_run_boundary(run)
                child = self._child(run)
                child["boundary_mutation_class"] = child_boundary["classification"]
                child["sentinel_touch_authority_class"] = child_boundary["sentinel_touch_authority_class"]
                child["sentinel_present"] = child_boundary["sentinel_present"]
                with self.assertRaises(AssertionError):
                    make_parent_final_result(
                        child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
                        second_child_started="NO", retry_count=0,
                        authority={"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
                                  "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"},
                        snapshot=ProcessGroupSnapshot((), (), 0), parent_boundary=parent_boundary,
                    )

    def test_unchanged_parent_recheck_is_drift_none(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-no-drift-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            parent = self._parent(child)
            self.assertEqual(parent["boundary_drift_class"], BOUNDARY_DRIFT_NONE)

    def test_wire_and_adapter_results_are_separate_for_malformed_responses(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-stage-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            journal = RecoveryJournal(run.probe_recovery, source_sha="a" * 40, source_tree="b" * 40)
            catalog_parser = CodexModelCatalogAdapter.__new__(CodexModelCatalogAdapter)
            def parse_model(value: Any) -> Any:
                entries, cursor = catalog_parser._parse_page(value)
                if cursor is not None:
                    raise ValueError("synthetic single page only")
                return [catalog_parser._normalize_model(entry) for entry in entries]
            def parse_thread(value: Any) -> str:
                thread = value["thread"]
                if not isinstance(thread, dict) or not isinstance(thread.get("id"), str) or not thread["id"]:
                    raise ValueError("thread response invalid")
                return thread["id"]
            def parse_turn(value: Any) -> str:
                turn = value["turn"]
                if not isinstance(turn, dict) or not isinstance(turn.get("id"), str) or not turn["id"]:
                    raise ValueError("turn response invalid")
                return turn["id"]
            self.assertEqual(record_synthetic_wire_adapter_result(
                journal, wire_stage="MODEL_LIST_WIRE", adapter_stage="MODEL_CATALOG",
                response={"data": "malformed"}, parser=parse_model,
            ), "INVALID")
            self.assertEqual(record_synthetic_wire_adapter_result(
                journal, wire_stage="THREAD_START_WIRE", adapter_stage="THREAD_START_ADAPTER",
                response={"thread": "malformed"}, parser=parse_thread,
            ), "INVALID")
            self.assertEqual(record_synthetic_wire_adapter_result(
                journal, wire_stage="TURN_START_WIRE", adapter_stage="TURN_START_ADAPTER",
                response={"turn": "malformed"}, parser=parse_turn,
            ), "INVALID")
            records = read_journal_records(run.probe_recovery)
            values = {record["event"]: record.get("result") for record in records}
            self.assertEqual(values["MODEL_LIST_WIRE_RESULT"], WIRE_RESPONSE_RETURNED)
            self.assertEqual(values["MODEL_CATALOG_RESULT"], "INVALID")
            self.assertEqual(values["THREAD_START_WIRE_RESULT"], WIRE_RESPONSE_RETURNED)
            self.assertEqual(values["THREAD_START_ADAPTER_RESULT"], "INVALID")
            self.assertEqual(values["TURN_START_WIRE_RESULT"], WIRE_RESPONSE_RETURNED)
            self.assertEqual(values["TURN_START_ADAPTER_RESULT"], "INVALID")

    def test_exact_watchdog_child_classes_precede_return_code(self) -> None:
        cases = (
            ({"status": "PROCESS_COMPLETED", "returncode": 0}, CHILD_RETURN_COMPLETED),
            ({"status": "PROCESS_COMPLETED", "returncode": 7}, CHILD_RETURN_NONZERO),
            ({"status": "PROCESS_WATCHDOG_TIMEOUT", "timed_out": True, "returncode": -15}, CHILD_RETURN_TIMEOUT),
            ({"status": "PROCESS_GROUP_NOT_QUIESCENT", "final_active_members": (42,), "returncode": -9}, CHILD_GROUP_RESIDUAL),
            ({"status": "PROCESS_GROUP_SCAN_ERROR", "final_scan_errors": 1, "returncode": 0}, CHILD_GROUP_SCAN_ERROR),
        )
        for facts, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_watchdog_child(facts), expected)

    def test_normal_child_result_requires_all_owned_observers_terminalized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-owner-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            loop = asyncio.new_event_loop()
            future = loop.create_future()
            future.set_result("synthetic-turn")
            operator = DenyOnlyApprovalOperator(
                thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
            )
            for approval_joined, terminal_joined, nonconverged in (
                (False, True, True), (True, False, True), (True, True, False),
            ):
                observation = ProbeObservation(
                    OUTCOME_TERMINAL_FIRST, "COMPLETED", 0, 0, 0,
                    approval_joined and terminal_joined, (), approval_joined, terminal_joined, nonconverged,
                )
                with self.subTest(observation=observation):
                    if nonconverged:
                        with self.assertRaises(AssertionError):
                            make_sanitized_result(
                                terminal_status="COMPLETED", operator=operator, run=run,
                                boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
                                observation=observation,
                            )
                    else:
                        result = make_sanitized_result(
                            terminal_status="COMPLETED", operator=operator, run=run,
                            boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
                            budget=synthetic_normal_budget(), observation=observation,
                        )
                        validate_child_result(result)
            loop.close()


class Repair4AuthorityOfflineTests(unittest.TestCase):
    def _child(self, run: FreshProbeRun) -> dict[str, Any]:
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("synthetic-turn")
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
        child_boundary = scan_fresh_run_boundary(run, phase=CHILD_PRE_RESULT)
        child = make_sanitized_result(
            terminal_status="COMPLETED", operator=operator, run=run,
            boundary=child_boundary, outcome=OUTCOME_TERMINAL_FIRST,
            budget=synthetic_normal_budget(),
        )
        loop.close()
        return child

    def test_child_result_is_exact_parent_harness_authority_and_no_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-happy-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child_boundary = scan_fresh_run_boundary(run, phase=CHILD_PRE_RESULT)
            self.assertEqual(child_boundary["classification"], "BOUNDARY_ONLY_EXPECTED_MUTATION")
            child = self._child(run)
            child_path = run.root / CHILD_RESULT_FILENAME
            write_sanitized_result(child_path, child)
            self.assertEqual(
                scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)["classification"],
                "BOUNDARY_ONLY_EXPECTED_MUTATION",
            )
            parent_boundary = scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)
            final = make_parent_final_result(
                child, child_return_classification=CHILD_RETURN_COMPLETED,
                one_child_count=1, second_child_started="NO", retry_count=0,
                authority={"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
                           "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"},
                snapshot=ProcessGroupSnapshot((), (), 0), parent_boundary=parent_boundary,
            )
            self.assertEqual(final["boundary_drift_class"], BOUNDARY_DRIFT_NONE)

    def test_child_result_is_absent_at_child_pre_result_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-pre-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            write_sanitized_result(run.root / CHILD_RESULT_FILENAME, child)
            boundary = scan_fresh_run_boundary(run, phase=CHILD_PRE_RESULT)
            self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
            self.assertIn("CHILD_RESULT_PRESENT_BEFORE_WRITE", boundary["unexpected_labels"])

    def test_parent_boundary_rejects_unsafe_child_result_without_repairing_it(self) -> None:
        cases = ("malformed", "wrong_schema", "unsafe_mode", "symlink", "hardlink", "oversized")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="p7c8-r4-child-unsafe-") as directory:
                root = Path(directory)
                run = FreshProbeRun.materialize(root)
                child = self._child(run)
                path = run.root / CHILD_RESULT_FILENAME
                if case == "malformed":
                    path.write_bytes(b"{")
                    path.chmod(0o600)
                elif case == "wrong_schema":
                    write_exclusive_private_json(path, {"format": 1})
                elif case == "unsafe_mode":
                    write_sanitized_result(path, child)
                    path.chmod(0o640)
                elif case == "symlink":
                    target = root / "child-target.json"
                    write_sanitized_result(target, child)
                    path.symlink_to(target)
                elif case == "hardlink":
                    target = root / "child-target.json"
                    write_sanitized_result(target, child)
                    os.link(target, path)
                else:
                    path.write_bytes(b"x" * (MAX_AUTHORITY_BYTES + 1))
                    path.chmod(0o600)
                boundary = scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)
                self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
                self.assertIn("CHILD_RESULT_AUTHORITY_INVALID", boundary["unexpected_labels"])
                self.assertTrue(path.is_symlink() or path.exists())

    def test_parent_boundary_rejects_child_result_path_replacement_and_read_mutation(self) -> None:
        import unittest.mock as mock
        for mutation in ("replace", "metadata"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix="p7c8-r4-child-race-") as directory:
                root = Path(directory)
                run = FreshProbeRun.materialize(root)
                child = self._child(run)
                path = run.root / CHILD_RESULT_FILENAME
                replacement = root / "replacement.json"
                write_sanitized_result(path, child)
                write_exclusive_private_json(replacement, child)
                original_read = os.read
                changed = False

                def change_after_read(fd: int, size: int) -> bytes:
                    nonlocal changed
                    data = original_read(fd, size)
                    if data and not changed:
                        changed = True
                        if mutation == "replace":
                            os.replace(replacement, path)
                        else:
                            os.utime(path, ns=(3, 4))
                    return data

                with mock.patch("os.read", side_effect=change_after_read):
                    boundary = scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)
                self.assertTrue(changed)
                self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
                self.assertIn("CHILD_RESULT_AUTHORITY_INVALID", boundary["unexpected_labels"])

    def test_arbitrary_sibling_remains_unexpected_probe_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-sibling-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            write_sanitized_result(run.root / CHILD_RESULT_FILENAME, child)
            (run.root / "arbitrary-sibling").write_bytes(b"synthetic")
            boundary = scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)
            self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
            self.assertIn("arbitrary-sibling", boundary["unexpected_labels"])

    def test_real_observation_authority_dominates_frozen_stimulus(self) -> None:
        self.assertEqual(P7C8_CANDIDATE_SLEEP_SECONDS, 30.0)
        self.assertGreater(PROBE_OBSERVATION_MARGIN_SECONDS, 0.0)
        self.assertGreater(
            PROBE_OBSERVATION_TIMEOUT,
            P7C8_CANDIDATE_SLEEP_SECONDS + PROBE_OBSERVATION_MARGIN_SECONDS,
        )
        self.assertNotEqual(PROBE_OBSERVATION_TIMEOUT, 10.0)
        self.assertIn("PROBE_OBSERVATION_TIMEOUT", inspect.getsource(_observe_future_race))

    def test_watchdog_authority_dominates_complete_internal_budget(self) -> None:
        self.assertGreater(PROBE_INTERNAL_WORST_CASE_SECONDS, PROBE_OBSERVATION_TIMEOUT)
        self.assertGreater(PROBE_WATCHDOG_MARGIN_SECONDS, 0.0)
        self.assertGreater(
            PROBE_WATCHDOG_HARD_DEADLINE,
            PROBE_INTERNAL_WORST_CASE_SECONDS + PROBE_WATCHDOG_MARGIN_SECONDS,
        )
        self.assertEqual(NORMAL_PATH_INTERNAL_WORST_CASE_SECONDS, 186.0)
        self.assertEqual(FAILED_ACQUIRE_INTERNAL_WORST_CASE_SECONDS, 64.0)
        self.assertGreater(
            PROBE_WATCHDOG_HARD_DEADLINE,
            FAILED_ACQUIRE_INTERNAL_WORST_CASE_SECONDS + PROBE_WATCHDOG_MARGIN_SECONDS,
        )
        self.assertEqual(P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS, 1.0)

    def test_no_approval_terminal_branch_can_form_a_finite_child_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-no-approval-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            validate_child_result(child)
            self.assertEqual(child["request_count"], 0)
            self.assertEqual(child["deny_response_count"], 0)
            self.assertEqual(child["sentinel_touch_authority_class"], SENTINEL_ABSENT)

    def _make_outcome(self, run: FreshProbeRun, execution_class: str, *, boundary: str = "BOUNDARY_NOT_PROVED",
                 drift: str = BOUNDARY_DRIFT_DETECTED, watchdog: str = "PROCESS_COMPLETED",
                 child_class: str = CHILD_RETURN_COMPLETED, child_present: bool = False,
                 child_valid: bool = False, latch_present: bool = False,
                 normal_present: bool = False,
                 discovery: str = "CHILD_RESULT_DISCOVERY_MISSING", group_active_count: int = 0,
                 group_scan_errors: int = 0) -> dict[str, Any]:
        return make_parent_execution_outcome(
            execution_class=execution_class, watchdog_status=watchdog,
            child_returncode_class=child_class, child_result_present=child_present,
            child_result_valid=child_valid, parent_boundary_class=boundary,
            boundary_drift_class=drift, accepted_source_sha=ARCHITECT_BASE_SHA,
            accepted_source_tree=ARCHITECT_BASE_TREE,
            global_latch_present=latch_present, normal_final_result_present=normal_present,
            child_result_discovery_class=discovery, group_active_count=group_active_count,
            group_scan_errors=group_scan_errors,
        )

    def test_each_failure_class_persists_one_exact_outcome_authority(self) -> None:
        cases = (
            (CHILD_RETURN_TIMEOUT, "PROCESS_WATCHDOG_TIMEOUT", CHILD_RETURN_TIMEOUT, {}, "MISSING"),
            (CHILD_RETURN_NONZERO, "PROCESS_COMPLETED", CHILD_RETURN_NONZERO, {}, "MISSING"),
            (CHILD_GROUP_RESIDUAL, "PROCESS_GROUP_NOT_QUIESCENT", CHILD_GROUP_RESIDUAL, {"group_active_count": 1}, "MISSING"),
            (CHILD_GROUP_SCAN_ERROR, "PROCESS_GROUP_SCAN_ERROR", CHILD_GROUP_SCAN_ERROR, {"group_scan_errors": 1}, "MISSING"),
            ("CHILD_RESULT_MISSING_OR_INVALID", "PROCESS_COMPLETED", CHILD_RETURN_COMPLETED, {}, "MISSING"),
            ("PARENT_BOUNDARY_INVALID_OR_DRIFTED", "PROCESS_COMPLETED", CHILD_RETURN_COMPLETED, {
                "child_present": True, "child_valid": True, "boundary": "UNEXPECTED_PROBE_MUTATION",
            }, "CONFIRMED"),
        )
        for execution_class, watchdog, child_class, extra, discovery in cases:
            with self.subTest(execution_class=execution_class), tempfile.TemporaryDirectory(prefix="p7c8-r4-outcome-") as directory:
                run = FreshProbeRun.materialize(Path(directory))
                outcome = self._make_outcome(
                    run, execution_class, watchdog=watchdog, child_class=child_class,
                    **extra, discovery=f"CHILD_RESULT_DISCOVERY_{discovery}",
                )
                path = run.root / "parent-execution-outcome.json"
                write_parent_execution_outcome(path, outcome)
                readback = read_bounded_private_json(path)
                validate_parent_execution_outcome(readback)
                self.assertEqual(readback, outcome)
                self.assertTrue(_private_regular(path))
                with self.assertRaises(FileExistsError):
                    write_parent_execution_outcome(path, outcome)
                self.assertFalse(run.result.exists())

    def test_normal_success_persists_final_result_before_confirmed_outcome(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-success-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._child(run)
            child_path = run.root / CHILD_RESULT_FILENAME
            write_sanitized_result(child_path, child)
            parent_boundary = scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE)
            final = make_parent_final_result(
                child, child_return_classification=CHILD_RETURN_COMPLETED,
                one_child_count=1, second_child_started="NO", retry_count=0,
                authority={"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
                           "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"},
                snapshot=ProcessGroupSnapshot((), (), 0), parent_boundary=parent_boundary,
            )
            write_parent_final_result(run.result, final)
            self.assertTrue(run.result.exists())
            outcome = make_parent_execution_outcome(
                execution_class="PARENT_FINAL_RESULT_CONFIRMED", watchdog_status="PROCESS_COMPLETED",
                child_returncode_class=CHILD_RETURN_COMPLETED, child_result_present=True,
                child_result_valid=True, parent_boundary_class="BOUNDARY_ONLY_EXPECTED_MUTATION",
                boundary_drift_class=BOUNDARY_DRIFT_NONE, normal_final_result_present=True,
                global_latch_present=True, child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
                runtime_acquire_initial_result=RuntimeAcquireClass.CONFIRMED,
                runtime_acquire_result=RuntimeAcquireClass.CONFIRMED,
            )
            outcome_path = run.root / "parent-execution-outcome.json"
            write_parent_execution_outcome(outcome_path, outcome)
            self.assertEqual(read_bounded_private_json(outcome_path), outcome)

    def test_failure_outcome_is_not_a_normal_parent_final_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-outcome-schema-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            outcome = self._make_outcome(run, CHILD_RETURN_TIMEOUT, watchdog="PROCESS_WATCHDOG_TIMEOUT", child_class=CHILD_RETURN_TIMEOUT)
            with self.assertRaises(AssertionError):
                validate_parent_final_result(outcome)

    def test_parent_outcome_schema_rejects_raw_fields_and_arbitrary_classes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-outcome-invalid-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            outcome = self._make_outcome(run, CHILD_RETURN_NONZERO, child_class=CHILD_RETURN_NONZERO)
            for mutation in ({"raw": "thread-id"}, {"execution_class": "ARBITRARY"}, {"format": True}):
                invalid = dict(outcome)
                invalid.update(mutation)
                with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                    validate_parent_execution_outcome(invalid)

    def test_preexisting_parent_outcome_blocks_launch_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r4-preexisting-") as directory:
            root = Path(directory)
            latch = root / "latch.json"
            result = root / "result.json"
            outcome_path = root / "outcome.json"
            write_exclusive_private_json(outcome_path, {"synthetic": True})
            with self.assertRaises(RuntimeError):
                require_parent_execution_authorities_absent(latch, result, outcome_path)
            self.assertTrue(outcome_path.exists())


class AuthorityAndBoundaryOfflineTests(unittest.TestCase):
    def test_fresh_run_layout_prompt_and_separate_authority(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-layout-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            self.assertTrue(_private_directory(run.root))
            self.assertTrue(_private_directory(run.sqlite))
            self.assertTrue(_private_directory(run.logs))
            prompt = candidate_probe_prompt(str(run.sentinel))
            self.assertIn("exactly 30 seconds", prompt)
            self.assertIn("stop immediately", prompt)
            self.assertIn("Do not retry", prompt)
            self.assertNotEqual(run.root, Path("/root") / ".codex_second")

    def test_probe_latch_is_exclusive_no_follow_and_blocks_preexisting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-latch-") as directory:
            parent = Path(directory)
            latch = parent / "latch.json"
            create_probe_latch(latch, source_sha="a" * 40, source_tree="b" * 40)
            self.assertTrue(_private_regular(latch))
            with self.assertRaises(FileExistsError):
                create_probe_latch(latch, source_sha="a" * 40, source_tree="b" * 40)
            self.assertEqual(read_bounded_private_json(latch)["status"], "RESERVED_BEFORE_FIRST_RPC")

    def test_future_budget_has_no_resume_delete_read_list_or_allow_capacity(self) -> None:
        budget = FutureProbeBudget()
        for name in ("model_list_calls", "thread_start_calls", "turn_start_calls"):
            budget.record(name)
        for _ in range(MAX_PROBE_APPROVAL_REQUESTS):
            budget.record_approval_deny()
        self.assertEqual(budget.approval_total_responses, MAX_PROBE_APPROVAL_REQUESTS)
        with self.assertRaises(AssertionError):
            budget.record_approval_deny()
        with self.assertRaises(AssertionError):
            budget.record_approval_allow()
        with self.assertRaises(AssertionError):
            budget.record("thread_resume_calls")
        with self.assertRaises(AssertionError):
            budget.record("approval_allow_responses")
        with self.assertRaises(AssertionError):
            budget.record("thread_delete_calls")

    def test_boundary_no_sentinel_exact_sentinel_and_unexpected_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-boundary-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            self.assertEqual(scan_fresh_run_boundary(run)["classification"], "BOUNDARY_ONLY_EXPECTED_MUTATION")
            run.sentinel.touch(mode=0o600)
            self.assertEqual(scan_fresh_run_boundary(run)["sentinel_touch_authority_class"], "EXPECTED_TOUCH")
            run.sentinel.write_bytes(b"synthetic")
            self.assertEqual(scan_fresh_run_boundary(run)["classification"], "UNEXPECTED_PROBE_MUTATION")
            (run.root / "unexpected-second-file").write_bytes(b"synthetic")
            boundary = scan_fresh_run_boundary(run)
            self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")

    def test_boundary_unexpected_process_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-process-boundary-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            boundary = scan_fresh_run_boundary(run, process_references=[run.root / "workdir"])
            self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
            self.assertIn("PROCESS_REFERENCE", boundary["unexpected_labels"])

    def test_exact_touch_authority_rejects_nonzero_hardlink_symlink_and_unsafe_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-touch-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            run.sentinel.touch(mode=0o600)
            self.assertEqual(sentinel_touch_authority(run.sentinel), "EXPECTED_TOUCH")
            run.sentinel.write_bytes(b"x")
            self.assertEqual(sentinel_touch_authority(run.sentinel), "UNEXPECTED_PROBE_MUTATION")
            run.sentinel.unlink()
            run.sentinel.touch(mode=0o600)
            hardlink = run.root / "sentinel-hardlink"
            os.link(run.sentinel, hardlink)
            self.assertEqual(sentinel_touch_authority(run.sentinel), "UNEXPECTED_PROBE_MUTATION")
            run.sentinel.unlink()
            hardlink.unlink()
            run.sentinel.symlink_to(run.root / "missing-target")
            self.assertEqual(sentinel_touch_authority(run.sentinel), "UNEXPECTED_PROBE_MUTATION")
            run.sentinel.unlink()
            run.sentinel.touch(mode=0o600)
            run.sentinel.chmod(0o666)
            self.assertEqual(sentinel_touch_authority(run.sentinel), "UNEXPECTED_PROBE_MUTATION")

    def test_unexpected_root_sibling_and_process_reference_are_command_owned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-boundary-extra-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            (run.root / "unexpected-sibling").mkdir(mode=0o700)
            boundary = scan_fresh_run_boundary(run, process_references=[run.root / "workdir"])
            self.assertEqual(boundary["classification"], "UNEXPECTED_PROBE_MUTATION")
            self.assertIn("unexpected-sibling", boundary["unexpected_labels"])

    def test_sanitized_result_excludes_raw_wire_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-result-") as directory:
            root = Path(directory)
            run = FreshProbeRun.materialize(root)
            (run.sqlite / "runtime.sqlite").write_bytes(b"synthetic sqlite payload")
            (run.logs / "app.log").write_bytes(b"synthetic log payload")
            self.assertEqual(scan_fresh_run_boundary(run)["classification"], "BOUNDARY_ONLY_EXPECTED_MUTATION")
            future = asyncio.new_event_loop().create_future()
            future.set_result("synthetic-turn-id")
            operator = DenyOnlyApprovalOperator(thread_id="synthetic-thread-id", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel))
            value = make_sanitized_result(terminal_status="COMPLETED", operator=operator, run=run, boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST)
            validate_sanitized_result(value)
            write_sanitized_result(run.result, value)
            self.assertEqual(read_bounded_private_json(run.result), json.loads(json.dumps(value)))
            self.assertNotIn("synthetic-command", json.dumps(value))
            future.get_loop().close()

    def test_child_result_has_no_process_group_final_claims(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-child-result-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            future = asyncio.new_event_loop().create_future()
            future.set_result("synthetic-turn-id")
            operator = DenyOnlyApprovalOperator(
                thread_id="synthetic-thread-id", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
            )
            child = make_sanitized_result(
                terminal_status="COMPLETED", operator=operator, run=run,
                boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
                budget=synthetic_normal_budget(),
            )
            validate_child_result(child)
            self.assertNotIn("process_group_final_active_count", child)
            self.assertNotIn("process_group_scan_errors", child)
            future.get_loop().close()

    def test_parent_final_result_requires_quiescent_group_and_valid_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-parent-result-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            future = asyncio.new_event_loop().create_future()
            future.set_result("synthetic-turn-id")
            operator = DenyOnlyApprovalOperator(
                thread_id="synthetic-thread-id", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
            )
            child = make_sanitized_result(
                terminal_status="COMPLETED", operator=operator, run=run,
                boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
                budget=synthetic_normal_budget(),
            )
            authority = {"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0, "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"}
            final = make_parent_final_result(
                child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
                second_child_started="NO", retry_count=0, authority=authority,
                snapshot=ProcessGroupSnapshot((), (), 0),
            )
            validate_parent_final_result(final)
            for bad_snapshot in (ProcessGroupSnapshot((101,), (), 0), ProcessGroupSnapshot((), (), 1)):
                with self.subTest(snapshot=bad_snapshot):
                    with self.assertRaises(AssertionError):
                        make_parent_final_result(
                            child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
                            second_child_started="NO", retry_count=0, authority=authority, snapshot=bad_snapshot,
                        )
            invalid = dict(child)
            invalid["wire_command_plaintext"] = "synthetic raw"
            with self.assertRaises(AssertionError):
                validate_child_result(invalid)
            future.get_loop().close()


class Repair5AuthorityOfflineTests(unittest.TestCase):
    def _child(self, run: FreshProbeRun) -> dict[str, Any]:
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("synthetic-turn")
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
        child = make_sanitized_result(
            terminal_status="COMPLETED", operator=operator, run=run,
            boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
            budget=synthetic_normal_budget(),
        )
        loop.close()
        return child

    def _make_r5_outcome(self, execution_class: str, **changes: Any) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "execution_class": execution_class,
            "watchdog_status": "PROCESS_COMPLETED",
            "child_returncode_class": CHILD_RETURN_NONZERO,
            "child_result_present": False,
            "child_result_valid": False,
            "parent_boundary_class": "BOUNDARY_NOT_PROVED",
            "boundary_drift_class": BOUNDARY_DRIFT_DETECTED,
            "group_active_count": 0,
            "group_scan_errors": 0,
            "global_latch_present": False,
            "normal_final_result_present": False,
            "child_result_discovery_class": "CHILD_RESULT_DISCOVERY_MISSING",
        }
        if execution_class == "PARENT_FINAL_RESULT_CONFIRMED":
            defaults.update(
                watchdog_status="PROCESS_COMPLETED", child_returncode_class=CHILD_RETURN_COMPLETED,
                child_result_present=True, child_result_valid=True,
                parent_boundary_class="BOUNDARY_ONLY_EXPECTED_MUTATION",
                boundary_drift_class=BOUNDARY_DRIFT_NONE, global_latch_present=True,
                normal_final_result_present=True,
                child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
                runtime_acquire_initial_result=RuntimeAcquireClass.CONFIRMED,
                runtime_acquire_result=RuntimeAcquireClass.CONFIRMED,
            )
        elif execution_class == CHILD_RETURN_TIMEOUT:
            defaults.update(watchdog_status="PROCESS_WATCHDOG_TIMEOUT", child_returncode_class=CHILD_RETURN_TIMEOUT)
        elif execution_class == CHILD_GROUP_RESIDUAL:
            defaults.update(
                watchdog_status="PROCESS_GROUP_NOT_QUIESCENT", child_returncode_class=CHILD_GROUP_RESIDUAL,
                group_active_count=1,
            )
        elif execution_class == CHILD_GROUP_SCAN_ERROR:
            defaults.update(
                watchdog_status="PROCESS_GROUP_SCAN_ERROR", child_returncode_class=CHILD_GROUP_SCAN_ERROR,
                group_scan_errors=1,
            )
        elif execution_class == "CHILD_RESULT_MISSING_OR_INVALID":
            defaults.update(child_returncode_class=CHILD_RETURN_COMPLETED)
        elif execution_class == "PARENT_BOUNDARY_INVALID_OR_DRIFTED":
            defaults.update(
                child_returncode_class=CHILD_RETURN_COMPLETED, child_result_present=True,
                child_result_valid=True, parent_boundary_class="UNEXPECTED_PROBE_MUTATION",
                child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
            )
        defaults.update(changes)
        return make_parent_execution_outcome(
            accepted_source_sha=ARCHITECT_BASE_SHA, accepted_source_tree=ARCHITECT_BASE_TREE,
            **defaults,
        )

    def test_child_result_discovery_is_bounded_read_only_and_factful(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r5-discovery-") as directory:
            parent = Path(directory)
            self.assertEqual(
                discover_child_result(parent).classification,
                "CHILD_RESULT_DISCOVERY_MISSING",
            )
            run = FreshProbeRun.materialize(parent)
            child = self._child(run)
            write_sanitized_result(run.root / CHILD_RESULT_FILENAME, child)
            discovered = discover_child_result(parent)
            self.assertEqual((discovered.present, discovered.valid), (True, True))
            self.assertEqual(discovered.classification, "CHILD_RESULT_DISCOVERY_CONFIRMED")
            malformed = run.root / CHILD_RESULT_FILENAME
            malformed.write_bytes(b"{")
            malformed.chmod(0o600)
            invalid = discover_child_result(parent)
            self.assertEqual((invalid.present, invalid.valid), (True, False))
            self.assertEqual(invalid.classification, "CHILD_RESULT_DISCOVERY_UNREADABLE")

    def test_ambiguous_child_root_does_not_invent_absent_result_fact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r5-ambiguous-") as directory:
            parent = Path(directory)
            FreshProbeRun.materialize(parent)
            FreshProbeRun.materialize(parent)
            discovered = discover_child_result(parent)
            self.assertEqual(discovered.classification, "CHILD_RESULT_DISCOVERY_AMBIGUOUS")
            self.assertFalse(discovered.valid)

    def test_latch_presence_is_measured_before_and_after_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r5-latch-") as directory:
            latch = Path(directory) / "latch.json"
            outcome_before = self._make_r5_outcome(CHILD_RETURN_NONZERO, global_latch_present=measure_parent_authority_presence(latch)[0])
            self.assertFalse(outcome_before["global_latch_present"])
            write_exclusive_private_json(latch, {"synthetic": "latch"})
            outcome_after = self._make_r5_outcome(CHILD_RETURN_NONZERO, global_latch_present=measure_parent_authority_presence(latch)[0])
            self.assertTrue(outcome_after["global_latch_present"])

    def test_valid_canonical_parent_outcome_exists_for_each_allowed_execution_class(self) -> None:
        for execution_class in (
            "PARENT_FINAL_RESULT_CONFIRMED", CHILD_RETURN_NONZERO, CHILD_RETURN_TIMEOUT,
            CHILD_GROUP_RESIDUAL, CHILD_GROUP_SCAN_ERROR,
            "CHILD_RESULT_MISSING_OR_INVALID", "PARENT_BOUNDARY_INVALID_OR_DRIFTED",
        ):
            with self.subTest(execution_class=execution_class):
                validate_parent_execution_outcome(self._make_r5_outcome(execution_class))

    def test_timeout_residual_and_scan_error_retain_valid_child_facts(self) -> None:
        for execution_class in (CHILD_RETURN_TIMEOUT, CHILD_GROUP_RESIDUAL, CHILD_GROUP_SCAN_ERROR):
            with self.subTest(execution_class=execution_class):
                outcome = self._make_r5_outcome(
                    execution_class, child_result_present=True, child_result_valid=True,
                    child_result_discovery_class="CHILD_RESULT_DISCOVERY_CONFIRMED",
                )
                self.assertTrue(outcome["child_result_present"])
                self.assertTrue(outcome["child_result_valid"])
                self.assertEqual(outcome["execution_class"], execution_class)

    def test_completed_missing_malformed_and_boundary_drift_classes_are_exact(self) -> None:
        missing = self._make_r5_outcome("CHILD_RESULT_MISSING_OR_INVALID")
        malformed = self._make_r5_outcome(
            "CHILD_RESULT_MISSING_OR_INVALID", child_result_present=True,
            child_result_discovery_class="CHILD_RESULT_DISCOVERY_UNREADABLE",
        )
        boundary = self._make_r5_outcome(
            "PARENT_BOUNDARY_INVALID_OR_DRIFTED", parent_boundary_class="BOUNDARY_ONLY_EXPECTED_MUTATION",
            boundary_drift_class=BOUNDARY_DRIFT_DETECTED,
        )
        for value in (missing, malformed, boundary):
            validate_parent_execution_outcome(value)

    def test_parent_outcome_semantic_matrix_rejects_contradictions(self) -> None:
        mutations = (
            {"watchdog_status": "PROCESS_WATCHDOG_TIMEOUT"},
            {"child_returncode_class": CHILD_RETURN_NONZERO},
            {"group_active_count": 1},
            {"group_scan_errors": 1},
            {"global_latch_present": False},
            {"normal_final_result_present": False},
            {"one_child_count": 0},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    self._make_r5_outcome("PARENT_FINAL_RESULT_CONFIRMED", **mutation)

    def test_parent_outcome_validator_rejects_invalid_child_class_names(self) -> None:
        valid = self._make_r5_outcome(CHILD_RETURN_NONZERO)
        for child_class in ("PARENT_FINAL_RESULT_CONFIRMED", "CHILD_RESULT_MISSING_OR_INVALID", "UNKNOWN"):
            invalid = dict(valid, child_returncode_class=child_class)
            with self.subTest(child_class=child_class), self.assertRaises(AssertionError):
                validate_parent_execution_outcome(invalid)

    def test_post_child_outcome_requires_exactly_one_child(self) -> None:
        with self.assertRaises(AssertionError):
            self._make_r5_outcome(CHILD_RETURN_NONZERO, one_child_count=0)


class Repair6EffectLedgerOfflineTests(unittest.TestCase):
    def _normal_child(self, run: FreshProbeRun) -> dict[str, Any]:
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("synthetic-turn")
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
        try:
            return make_sanitized_result(
                terminal_status="COMPLETED", operator=operator, run=run,
                boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST,
                budget=synthetic_normal_budget(),
            )
        finally:
            loop.close()

    def test_normal_child_projects_and_persists_authoritative_one_one_one_ledger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r6-child-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            budget = synthetic_normal_budget()
            self.assertEqual(
                (budget.model_list_calls, budget.thread_start_calls, budget.turn_start_calls),
                (1, 1, 1),
            )
            child = make_sanitized_result(
                terminal_status="COMPLETED", operator=self._operator(run), run=run,
                boundary=scan_fresh_run_boundary(run), outcome=OUTCOME_TERMINAL_FIRST, budget=budget,
            )
            validate_child_result(child)
            self.assertEqual(
                (child["model_list_calls"], child["thread_start_calls"], child["turn_start_calls"]),
                (1, 1, 1),
            )
            self.assertIsInstance(child["fresh_thread_sha256"], str)
            self.assertRegex(child["fresh_thread_sha256"], SHA256_RE)
            self.assertIsInstance(child["fresh_turn_sha256"], str)
            self.assertRegex(child["fresh_turn_sha256"], SHA256_RE)
            path = run.root / CHILD_RESULT_FILENAME
            write_sanitized_result(path, child)
            readback = read_bounded_private_json(path)
            validate_child_result(readback)
            self.assertEqual(readback, child)

    def _operator(self, run: FreshProbeRun) -> DenyOnlyApprovalOperator:
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result("synthetic-turn")
        operator = DenyOnlyApprovalOperator(
            thread_id="synthetic-thread", turn_id=future, cwd=str(run.workdir), sentinel=str(run.sentinel),
        )
        # The Future retains the established synthetic identity after its
        # private loop is closed; no asynchronous operation is performed.
        loop.close()
        return operator

    def test_normal_child_negative_matrix_rejects_lifecycle_hash_forbidden_and_allow_mutations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r6-child-negative-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._normal_child(run)
            mutations = (
                ("model_list_calls", 0), ("thread_start_calls", 0), ("turn_start_calls", 0),
                ("model_list_calls", 2), ("thread_start_calls", 2), ("turn_start_calls", 2),
                ("fresh_thread_sha256", None), ("fresh_turn_sha256", None),
                ("fresh_thread_sha256", "malformed"), ("fresh_turn_sha256", "malformed"),
                ("thread_resume_calls", 1), ("interrupt_calls", 1),
                ("thread_delete_calls", 1), ("thread_read_calls", 1), ("thread_list_calls", 1),
                ("approval_allow_responses", 1),
            )
            for key, replacement in mutations:
                invalid = dict(child)
                invalid[key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(AssertionError):
                    validate_child_result(invalid)

    def test_normal_parent_requires_exact_one_one_one_ledger(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-r6-parent-") as directory:
            run = FreshProbeRun.materialize(Path(directory))
            child = self._normal_child(run)
            path = run.root / CHILD_RESULT_FILENAME
            write_sanitized_result(path, child)
            parent = make_parent_final_result(
                child, child_return_classification=CHILD_RETURN_COMPLETED, one_child_count=1,
                second_child_started="NO", retry_count=0,
                authority={"pid": 101, "pgid": 101, "sid": 101, "term_count": 0, "kill_count": 0,
                           "signalled_parent_pgid": "NO", "second_pgid_targeted": "NO"},
                snapshot=ProcessGroupSnapshot((), (), 0),
                parent_boundary=scan_fresh_run_boundary(run, phase=PARENT_POST_QUIESCENCE),
            )
            validate_parent_final_result(parent)
            for key in ("model_list_calls", "thread_start_calls", "turn_start_calls"):
                for replacement in (0, 2):
                    invalid = dict(parent)
                    invalid[key] = replacement
                    with self.subTest(key=key, replacement=replacement), self.assertRaises(AssertionError):
                        validate_parent_final_result(invalid)

    def test_failure_outcome_does_not_gain_normal_effect_ledger_fields(self) -> None:
        outcome = make_parent_execution_outcome(
            execution_class=CHILD_RETURN_NONZERO, watchdog_status="PROCESS_COMPLETED",
            child_returncode_class=CHILD_RETURN_NONZERO, child_result_present=False,
            child_result_valid=False, parent_boundary_class="BOUNDARY_NOT_PROVED",
            boundary_drift_class=BOUNDARY_DRIFT_DETECTED, global_latch_present=False,
            normal_final_result_present=False, child_result_discovery_class="CHILD_RESULT_DISCOVERY_MISSING",
        )
        for key in ("model_list_calls", "thread_start_calls", "turn_start_calls"):
            self.assertNotIn(key, outcome)
            invalid = dict(outcome, **{key: 1})
            with self.subTest(key=key), self.assertRaises(AssertionError):
                validate_parent_execution_outcome(invalid)

    def test_deny_accounting_remains_valid_from_zero_through_three_and_fourth_is_blocked(self) -> None:
        for count in range(MAX_PROBE_APPROVAL_REQUESTS + 1):
            budget = FutureProbeBudget()
            for _ in range(count):
                budget.record_approval_deny()
            budget.reconcile()
            self.assertEqual(budget.approval_deny_attempts, count)
            self.assertEqual(budget.approval_deny_responses, count)
            self.assertEqual(budget.approval_deny_confirmed, count)
            self.assertEqual(budget.approval_deny_unknown_or_failed, 0)
            self.assertEqual(budget.approval_allow_responses, 0)
        budget = FutureProbeBudget()
        for _ in range(MAX_PROBE_APPROVAL_REQUESTS):
            budget.record_approval_deny()
        with self.assertRaises(AssertionError):
            budget.record_approval_deny()


class RawWireAuthorityOfflineTests(unittest.TestCase):
    def test_exclusive_root_only_record_and_bounded_reader(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-wire-") as directory:
            root = Path(directory)
            run = FreshProbeRun.materialize(root)
            authority = WireCommandAuthority(run.wire_recovery)
            authority.capture_once(thread_id="synthetic-thread", turn_id="synthetic-turn", cwd="/synthetic/cwd", sentinel=str(run.sentinel), wire_command="synthetic executable --arg", kind=ApprovalKind.COMMAND_EXECUTION, sequence=1)
            record = read_wire_authority(run.wire_recovery)
            self.assertEqual(record["wire_command_plaintext"], "synthetic executable --arg")
            with self.assertRaises(FileExistsError):
                authority.capture_once(thread_id="synthetic-thread", turn_id="synthetic-turn", cwd="/synthetic/cwd", sentinel=str(run.sentinel), wire_command="replacement", kind=ApprovalKind.COMMAND_EXECUTION, sequence=1)

    def test_exact_schema_hash_identity_kind_sequence_and_size_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-wire-schema-") as directory:
            root = Path(directory)
            run = FreshProbeRun.materialize(root)
            authority = WireCommandAuthority(run.wire_recovery)
            authority.capture_once(thread_id="actual-thread", turn_id="actual-turn", cwd="/actual/cwd", sentinel=str(run.sentinel), wire_command="synthetic command", kind=ApprovalKind.COMMAND_EXECUTION, sequence=1)
            record = read_wire_authority(run.wire_recovery)
            self.assertEqual(set(record), WIRE_AUTHORITY_KEYS)
            self.assertEqual(record["thread_id_sha256"], _sha256("actual-thread"))
            self.assertEqual(record["turn_id_sha256"], _sha256("actual-turn"))
            self.assertEqual(record["actual_cwd_sha256"], _sha256("/actual/cwd"))
            self.assertEqual(record["expected_sentinel_path_sha256"], _sha256(str(run.sentinel)))
            self.assertEqual(record["wire_command_sha256"], _sha256(record["wire_command_plaintext"]))
            for key in ("thread_id_sha256", "turn_id_sha256", "actual_cwd_sha256", "expected_sentinel_path_sha256", "wire_command_sha256"):
                self.assertIsNotNone(SHA256_RE.fullmatch(record[key]))

            for missing in ("wire_command_sha256", "actual_cwd_sha256"):
                invalid = dict(record)
                invalid.pop(missing)
                with self.subTest(missing=missing), self.assertRaises(ValueError):
                    validate_wire_authority_record(invalid)
            invalid = dict(record, unknown_field=True)
            with self.assertRaises(ValueError):
                validate_wire_authority_record(invalid)
            invalid = dict(record, wire_command_sha256="0" * 64)
            with self.assertRaises(ValueError):
                validate_wire_authority_record(invalid)
            invalid = dict(record, request_kind="file_change")
            with self.assertRaises(ValueError):
                validate_wire_authority_record(invalid)
            invalid = dict(record, local_request_sequence=0)
            with self.assertRaises(ValueError):
                validate_wire_authority_record(invalid)
            invalid = dict(record, wire_command_plaintext="x" * (MAX_WIRE_COMMAND_CHARS + 1))
            with self.assertRaises(ValueError):
                validate_wire_authority_record(invalid)

    def test_symlink_hardlink_unsafe_mode_oversize_and_malformed_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-wire-unsafe-") as directory:
            root = Path(directory)
            target = root / "target.json"
            write_exclusive_private_json(target, {"synthetic": True})
            symlink = root / "symlink.json"
            symlink.symlink_to(target)
            with self.assertRaises(ValueError):
                read_bounded_private_json(symlink)
            hardlink = root / "hardlink.json"
            os.link(target, hardlink)
            with self.assertRaises(ValueError):
                read_bounded_private_json(hardlink)
            unsafe = root / "unsafe.json"
            unsafe.write_text("{}", encoding="utf-8")
            unsafe.chmod(0o644)
            with self.assertRaises(ValueError):
                read_bounded_private_json(unsafe)
            oversized = root / "oversized.json"
            oversized.write_bytes(b"x" * (MAX_AUTHORITY_BYTES + 1))
            oversized.chmod(0o600)
            with self.assertRaises(ValueError):
                read_bounded_private_json(oversized)
            malformed = root / "malformed.json"
            malformed.write_text("{", encoding="utf-8")
            malformed.chmod(0o600)
            with self.assertRaises(ValueError):
                read_bounded_private_json(malformed)

    def test_path_replacement_and_mutation_during_read_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c8-wire-race-") as directory:
            root = Path(directory)
            path = root / "record.json"
            replacement = root / "replacement.json"
            write_exclusive_private_json(path, {"synthetic": "original"})
            write_exclusive_private_json(replacement, {"synthetic": "replacement"})
            original_read = os.read
            replaced = False

            def replace_after_read(fd: int, size: int) -> bytes:
                nonlocal replaced
                data = original_read(fd, size)
                if data and not replaced:
                    replaced = True
                    os.replace(replacement, path)
                return data

            import unittest.mock as mock
            with mock.patch("os.read", side_effect=replace_after_read), self.assertRaises(ValueError):
                read_bounded_private_json(path)
            self.assertTrue(replaced)

            path.unlink()
            write_exclusive_private_json(path, {"synthetic": "original"})
            mutated = False

            def mutate_after_read(fd: int, size: int) -> bytes:
                nonlocal mutated
                data = original_read(fd, size)
                if data and not mutated:
                    mutated = True
                    os.utime(path, ns=(3, 4))
                return data

            with mock.patch("os.read", side_effect=mutate_after_read), self.assertRaises(ValueError):
                read_bounded_private_json(path)
            self.assertTrue(mutated)


class ShlexAndWatchdogOfflineTests(unittest.TestCase):
    def test_named_watchdog_budget_dominates_inner_budget(self) -> None:
        self.assertGreater(
            PROBE_WATCHDOG_HARD_DEADLINE,
            PROBE_INTERNAL_WORST_CASE_SECONDS + PROBE_WATCHDOG_MARGIN_SECONDS,
        )

    def test_release_equivalent_shlex_round_trip_synthetic_vectors(self) -> None:
        vectors = [
            ["synthetic-executable", "--flag", "value"],
            ["/synthetic path/executable", "space value"],
            ["synthetic", "single'quote", 'double"quote'],
            ["synthetic", ";|&$()<>*? literal"],
        ]
        for vector in vectors:
            wire = shlex.join(vector)
            recovered = recover_wire_vector(wire)
            with self.subTest(vector=vector):
                self.assertTrue(recovered.established)
                self.assertEqual(recovered.vector_length, len(vector))
                self.assertEqual(len(recovered.token_sha256), len(vector))

    def test_malformed_or_noncanonical_wire_is_not_established(self) -> None:
        for wire in ("synthetic 'unterminated", "synthetic\0bad", "synthetic  plain"):
            self.assertFalse(recover_wire_vector(wire).established)

    def test_sentinel_reference_is_observational_and_never_substring_match(self) -> None:
        sentinel = "/synthetic/sentinel"
        cases = (
            (shlex.join(["synthetic", sentinel]), SENTINEL_EXACT_ARG),
            (shlex.join(["synthetic", f"prefix-{sentinel}-suffix"]), SENTINEL_EMBEDDED),
            (shlex.join(["synthetic", "other"]), SENTINEL_ABSENT),
            ("synthetic 'unterminated " + sentinel, SENTINEL_VECTOR_UNKNOWN),
        )
        for wire, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_sentinel_reference(wire, sentinel), expected)

    def test_python_shlex_authority_is_only_claimed_on_exact_round_trip(self) -> None:
        vectors = [["synthetic", "", "space value", "single'quote", 'double"quote', ";|&$()<>*?"]]
        for vector in vectors:
            wire = shlex.join(vector)
            result = recover_wire_vector(wire)
            self.assertTrue(result.established)
            self.assertEqual(result.vector_length, len(vector))
        self.assertEqual(classify_sentinel_reference("synthetic  plain", "/synthetic"), SENTINEL_VECTOR_UNKNOWN)

    def test_watchdog_normal_exit_and_exact_group_authority(self) -> None:
        result = run_synthetic_watchdog(["/bin/sh", "-c", "exit 0"], deadline=1.0)
        self.assertEqual(result["status"], "PROCESS_COMPLETED")
        self.assertEqual(result["authority"]["authority"], "PASS")
        self.assertEqual(result["final_active_members"], ())
        self.assertEqual(result["term_count"], 0)
        self.assertEqual(result["kill_count"], 0)

    def test_watchdog_terminates_stubborn_tree_finitely(self) -> None:
        calls: list[tuple[int, int]] = []
        real_killpg = os.killpg

        def instrumented_killpg(pgid: int, sig: int) -> None:
            calls.append((pgid, sig))
            real_killpg(pgid, sig)

        result = run_synthetic_watchdog(["/bin/sh", "-c", "sleep 30 & sh -c 'sleep 30 & wait' & wait"], deadline=0.05, terminate_grace=0.05, kill_grace=0.2, killpg=instrumented_killpg)
        self.assertEqual(result["status"], "PROCESS_WATCHDOG_TIMEOUT")
        self.assertEqual(result["term_count"], 1)
        self.assertLessEqual(result["kill_count"], 1)
        self.assertEqual(result["final_active_members"], ())
        self.assertLessEqual(sum(sig == signal.SIGTERM for _, sig in calls), 1)
        self.assertLessEqual(sum(sig == signal.SIGKILL for _, sig in calls), 1)
        self.assertEqual({pgid for pgid, _ in calls}, {result["authority"]["pgid"]})
        self.assertNotIn((result["authority"]["parent_pgid"], signal.SIGTERM), calls)
        self.assertNotIn((result["authority"]["parent_pgid"], signal.SIGKILL), calls)

    def test_normal_leader_exit_with_residual_descendant_is_not_accepted(self) -> None:
        result = run_synthetic_watchdog(
            ["/bin/sh", "-c", "sleep 30 & exit 0"], deadline=0.2,
            terminate_grace=0.05, kill_grace=0.2,
        )
        self.assertEqual(result["status"], "PROCESS_GROUP_NOT_QUIESCENT")
        self.assertEqual(result["final_active_members"], ())
        self.assertLessEqual(result["term_count"], 1)
        self.assertLessEqual(result["kill_count"], 1)

    def test_watchdog_does_not_signal_unrelated_separate_session(self) -> None:
        unrelated = subprocess.Popen(["/bin/sh", "-c", "sleep 30"], close_fds=True, start_new_session=True)
        try:
            result = run_synthetic_watchdog(["/bin/sh", "-c", "sleep 30"], deadline=0.05, terminate_grace=0.05, kill_grace=0.2)
            self.assertEqual(result["status"], "PROCESS_WATCHDOG_TIMEOUT")
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=1)

    def test_watchdog_scan_separates_zombies_and_counts_scan_errors(self) -> None:
        import unittest.mock as mock
        with mock.patch(__name__ + "._proc_group_session", side_effect=[("R", 42, 7), ("Z", 42, 7), None]):
            with mock.patch("os.listdir", return_value=["101", "102", "103"]):
                snapshot = inspect_process_group(42)
        self.assertEqual(snapshot.active_members, (101,))
        self.assertEqual(snapshot.zombie_members, (102,))
        self.assertEqual(snapshot.scan_errors, 1)

    def test_pid_disappearance_after_snapshot_is_benign(self) -> None:
        import unittest.mock as mock
        with mock.patch(__name__ + "._proc_group_session", side_effect=FileNotFoundError):
            with mock.patch("os.listdir", return_value=["101"]):
                snapshot = inspect_process_group(42)
        self.assertEqual(snapshot.active_members, ())
        self.assertEqual(snapshot.zombie_members, ())
        self.assertEqual(snapshot.scan_errors, 0)

    def test_malformed_and_unreadable_stat_fail_closed(self) -> None:
        import unittest.mock as mock
        for error in (ValueError("bad stat"), PermissionError("unreadable")):
            with mock.patch(__name__ + "._proc_group_session", side_effect=error):
                with mock.patch("os.listdir", return_value=["101"]):
                    snapshot = inspect_process_group(42)
            self.assertGreater(snapshot.scan_errors, 0)

    def test_signal_authority_dispatches_each_exact_group_signal_at_most_once(self) -> None:
        calls: list[tuple[int, int]] = []
        authority = ExactProcessGroupSignalAuthority(42, 7, killpg=lambda pgid, sig: calls.append((pgid, sig)))
        authority.dispatch(signal.SIGTERM)
        authority.dispatch(signal.SIGKILL)
        with self.assertRaises(AssertionError):
            authority.dispatch(signal.SIGTERM)
        with self.assertRaises(AssertionError):
            authority.dispatch(signal.SIGKILL)
        self.assertEqual(calls, [(42, signal.SIGTERM), (42, signal.SIGKILL)])
        self.assertNotIn((7, signal.SIGTERM), calls)


class P7C8StaticGateTests(unittest.TestCase):
    def test_real_authorities_are_unset_and_gate_is_disabled(self) -> None:
        self.assertNotEqual(os.environ.get(AUTHORIZED_ENV), AUTHORIZED_ENV)
        self.assertIsNone(os.environ.get(EXPECTED_HEAD_ENV))
        self.assertIsNone(os.environ.get(EXPECTED_TREE_ENV))
        self.assertFalse(REAL_PROBE_LATCH.exists())
        self.assertFalse(REAL_PROBE_RESULT.exists())
        self.assertFalse(REAL_PROBE_OUTCOME.exists())

    def test_future_source_gate_precedes_latch_and_rpc(self) -> None:
        source = inspect.getsource(future_real_deny_only_approval_probe)
        self.assertLess(source.index("validate_future_source_authority"), source.index("create_probe_latch"))
        self.assertLess(source.index("create_probe_latch"), source.index("acquire_observer.observe"))
        self.assertNotIn("ARCHITECT_BASE_SHA", source)

    def test_turn_authority_precedes_approval_observer_and_terminal_owner(self) -> None:
        source = inspect.getsource(future_real_deny_only_approval_probe)
        self.assertLess(source.index("turn_future.set_result"), source.index("_observe_future_race"))
        self.assertLess(source.index("TURN_ID_AUTHORITY"), source.index("APPROVAL_OBSERVER_ARMED"))
        self.assertIn("lambda: turn_lifecycle.wait_turn(turn.binding)", source)

    def test_future_unittest_uses_parent_launcher_not_inner_coroutine(self) -> None:
        source = inspect.getsource(P7C8DenyOnlyApprovalProbeAcceptance.test_future_real_deny_only_approval_probe)
        self.assertIn("run_future_real_probe_parent", source)
        self.assertNotIn("future_real_deny_only_approval_probe()", source)
        parent_source = inspect.getsource(run_future_real_probe_parent)
        self.assertEqual(parent_source.count("subprocess.Popen("), 1)
        self.assertIn("start_new_session=True", parent_source)
        self.assertIn("--codexcontrol-p7c8-probe-child", parent_source)

    def test_child_result_and_parent_result_are_separate_authorities(self) -> None:
        self.assertNotIn("process_group_final_active_count", inspect.getsource(make_sanitized_result))
        self.assertIn("PARENT_MEASURED_GROUP_AND_CHILD", inspect.getsource(make_parent_final_result))

    def test_parent_acquisition_uses_bounded_no_follow_journal_reader(self) -> None:
        self.assertNotIn("read_text", inspect.getsource(read_authoritative_recovery_journal))
        self.assertIn("O_NOFOLLOW", inspect.getsource(read_authoritative_recovery_journal))
        self.assertIn("O_CLOEXEC", inspect.getsource(read_authoritative_recovery_journal))
        self.assertIn("read_authoritative_recovery_journal", inspect.getsource(recover_parent_acquisition_authority))

    def test_failed_containment_has_one_task_and_no_unbounded_cancel_join(self) -> None:
        source = inspect.getsource(RuntimeAcquireObserver.contain)
        self.assertEqual(source.count("asyncio.create_task(manager.shutdown_profile(profile_id))"), 1)
        self.assertNotIn("gather(cleanup_task", source)
        self.assertIn("P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS", inspect.getsource(RuntimeAcquireObserver))

    def test_parent_outcome_is_distinct_and_preflighted_before_child(self) -> None:
        self.assertNotEqual(REAL_PROBE_OUTCOME, REAL_PROBE_LATCH)
        self.assertNotEqual(REAL_PROBE_OUTCOME, REAL_PROBE_RESULT)
        source = inspect.getsource(run_future_real_probe_parent)
        self.assertIn("require_parent_execution_authorities_absent", source)
        self.assertLess(source.index("require_parent_execution_authorities_absent"), source.index("subprocess.Popen"))
        self.assertIn("write_parent_execution_outcome", source)

    def test_future_real_path_has_one_allowed_lifecycle_route_and_no_forbidden_route(self) -> None:
        tree = ast.parse(inspect.getsource(future_real_deny_only_approval_probe))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        names = [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)]
        self.assertEqual(names.count("get_catalog"), 1)
        self.assertEqual(names.count("start"), 1)
        self.assertEqual(names.count("start_turn"), 1)
        for forbidden in ("resume", "interrupt_turn", "delete", "thread_read", "thread_list"):
            self.assertNotIn(forbidden, names)
        self.assertNotIn("ALLOW", inspect.getsource(DenyOnlyApprovalOperator.decide))
        self.assertIn("ApprovalHandlingStatus.DENIED", inspect.getsource(_drain_future_approvals))

    def test_future_budget_freezes_complete_effect_surface(self) -> None:
        budget = FutureProbeBudget()
        for action in ("model_list_calls", "thread_start_calls", "turn_start_calls"):
            budget.record(action)
        self.assertEqual((budget.model_list_calls, budget.thread_start_calls, budget.turn_start_calls), (1, 1, 1))
        for action in ("thread_resume_calls", "interrupt_calls", "thread_delete_calls", "thread_read_calls", "thread_list_calls"):
            with self.subTest(action=action):
                with self.assertRaises(AssertionError):
                    budget.record(action)

    def test_normal_child_write_is_after_confirmed_stages_and_budget_projection(self) -> None:
        source = inspect.getsource(future_real_deny_only_approval_probe)
        stage_positions = (
            source.index('journal.result("MODEL_CATALOG", "CONFIRMED")'),
            source.index('journal.result("THREAD_START_ADAPTER",'),
            source.index('journal.result("TURN_START_ADAPTER",'),
            source.index("budget.reconcile()"),
            source.index("child_result = make_sanitized_result("),
        )
        self.assertEqual(stage_positions, tuple(sorted(stage_positions)))
        self.assertIn("budget.record(action)", source)
        self.assertIn('"model_list_calls"', source)
        self.assertIn('"thread_start_calls"', source)
        self.assertIn('"turn_start_calls"', source)

    def test_frozen_observation_and_watchdog_values_remain_exact(self) -> None:
        self.assertEqual(P7C8_CANDIDATE_SLEEP_SECONDS, 30.0)
        self.assertEqual(PROBE_OBSERVATION_MARGIN_SECONDS, 60.0)
        self.assertEqual(PROBE_OBSERVATION_TIMEOUT, 100.0)
        self.assertEqual(PROBE_RUNTIME_ACQUIRE_TIMEOUT, 45.0)
        self.assertEqual(PROBE_INTERNAL_WORST_CASE_SECONDS, 186.0)
        self.assertEqual(NORMAL_PATH_INTERNAL_WORST_CASE_SECONDS, 186.0)
        self.assertEqual(FAILED_ACQUIRE_INTERNAL_WORST_CASE_SECONDS, 64.0)
        self.assertEqual(PROBE_WATCHDOG_MARGIN_SECONDS, 15.0)
        self.assertEqual(PROBE_WATCHDOG_HARD_DEADLINE, 205.0)
        self.assertEqual(P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS, 1.0)

    def test_acquisition_horizon_and_parent_outcome_fields_are_frozen(self) -> None:
        self.assertGreater(
            P7C8_RUNTIME_ACQUIRE_TIMEOUT_SECONDS,
            KNOWN_NAMED_STARTUP_BOUND_SECONDS + P7C8_RUNTIME_ACQUIRE_NAMED_STAGE_MARGIN_SECONDS,
        )
        self.assertEqual(P7C8_RUNTIME_ACQUIRE_CLEANUP_TIMEOUT_SECONDS, 12.0)
        outcome = make_parent_execution_outcome(
            execution_class=CHILD_RETURN_NONZERO, watchdog_status="PROCESS_COMPLETED",
            child_returncode_class=CHILD_RETURN_NONZERO, child_result_present=False,
            child_result_valid=False, parent_boundary_class="BOUNDARY_NOT_PROVED",
            boundary_drift_class=BOUNDARY_DRIFT_DETECTED, global_latch_present=True,
            normal_final_result_present=False, child_result_discovery_class="CHILD_RESULT_DISCOVERY_MISSING",
            runtime_acquire_result=RuntimeAcquireClass.SAFE_EXCEPTION,
            runtime_acquire_error_category="capability_mismatch", runtime_acquire_cleanup_result="CONFIRMED",
        )
        self.assertEqual(outcome["runtime_acquire_error_category"], "capability_mismatch")
        self.assertFalse(outcome["normal_final_result_present"])

class P7C8DenyOnlyApprovalProbeAcceptance(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(
        os.environ.get(AUTHORIZED_ENV) == AUTHORIZED_ENV
        and bool(os.environ.get(EXPECTED_HEAD_ENV))
        and bool(os.environ.get(EXPECTED_TREE_ENV)),
        "gated future P7.C8 deny-only approval probe",
    )
    async def test_future_real_deny_only_approval_probe(self) -> None:
        # The gated test owns only the parent launcher.  The child entrypoint
        # is the sole place that can call the inner future real coroutine.
        await asyncio.to_thread(run_future_real_probe_parent)


if __name__ == "__main__":
    if "--codexcontrol-p7c8-probe-child" in sys.argv:
        index = sys.argv.index("--codexcontrol-p7c8-probe-child")
        child_parent = Path(sys.argv[index + 1])
        asyncio.run(future_real_deny_only_approval_probe(child_parent))
    else:
        unittest.main()
