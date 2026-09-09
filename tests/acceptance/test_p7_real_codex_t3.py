"""Opt-in, one-shot real Codex T3 acceptance for P7.

This module is deliberately proof-only.  It contains no production runtime,
storage, or cleanup implementation; all filesystem inspection is bounded to
the selected Codex home and explicitly P7-owned temporary paths.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
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
from typing import Any

from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalKind,
    ApprovalHandlingStatus,
    ApprovalRequest,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.model_catalog import CodexModelCatalogAdapter
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnInterruptStatus,
    TurnStartStatus,
    TurnTerminalStatus,
)
from codex_control.domain import CodexProfile


CODEX = "/usr/local/bin/codex"
VERSION = "codex-cli 0.144.6"
SCHEMA_SHA256 = "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466"
ARCHITECT_BASE = "66f094f3592467d16382482f133b288d521c4873"
REAL_GATE = "AUTHORIZED_2026_09_08"
RECOVERY_GATE = "AUTHORIZED_RECOVERY_2026_09_09"
RECOVERY_THREAD_SHA256 = "8faed122df2a4b7d331eb20493bde272160b5f1ef2cf856c758090cd6369a266"
PROFILE_HOMES = {
    "codex3": "/root/.codex_third",
    "codex2": "/root/.codex_second",
}
CATEGORIES = ("SESSION_HISTORY", "STATE_DB", "LOG", "CACHE", "OTHER")
CONTENT_MARKER = "content_marker"
THREAD_ID = "thread_id"
CODEX_BASENAMES = frozenset(("codex", "codex-cli", "codex.js"))


class _P7Stop(Exception):
    def __init__(self, stage: str, *, blocked: bool = False) -> None:
        self.stage = stage
        self.blocked = blocked
        super().__init__(stage)


def _require(condition: bool, stage: str, *, blocked: bool = False) -> None:
    if not condition:
        raise _P7Stop(stage, blocked=blocked)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_profile_path(alias: str) -> Path:
    expected = PROFILE_HOMES.get(alias)
    if expected is None:
        raise _P7Stop("P7_GATE_INVALID")
    path = Path(expected)
    try:
        mode = path.lstat()
    except OSError:
        raise _P7Stop("P7_ISOLATION_GATE_BLOCKED", blocked=True) from None
    _require(
        path.is_absolute()
        and not path.is_symlink()
        and stat.S_ISDIR(mode.st_mode)
        and mode.st_uid == 0
        and not (mode.st_mode & stat.S_IWGRP)
        and not (mode.st_mode & stat.S_IWOTH),
        "P7_ISOLATION_GATE_BLOCKED",
        blocked=True,
    )
    return path


def _proc_environment(pid: int) -> dict[str, str] | None:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (OSError, ValueError):
        return None
    result: dict[str, str] = {}
    for item in raw.split(b"\0"):
        if b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        try:
            result[key.decode("utf-8")] = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    return result


def _proc_cmdline(pid: int) -> tuple[str, ...] | None:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except (OSError, ValueError):
        return None
    try:
        return tuple(
            token.decode("utf-8", errors="strict")
            for token in raw.split(b"\0")
            if token
        )
    except UnicodeDecodeError:
        return None


def _authority_targets() -> tuple[str, ...]:
    targets = [os.path.abspath(CODEX)]
    try:
        targets.append(str(Path(CODEX).resolve(strict=True)))
    except OSError:
        pass
    return tuple(dict.fromkeys(targets))


def _path_is_under(path: str, root: Path) -> bool:
    try:
        return os.path.commonpath((os.path.abspath(path), str(root))) == str(root)
    except (OSError, ValueError):
        return False


def _codex_process_owns_candidate(pid: int, candidate: Path) -> bool:
    """Return true for ownership or ambiguity, without exposing /proc data."""
    try:
        executable_path = os.readlink(f"/proc/{pid}/exe")
    except OSError:
        executable_path = None
    executable = os.path.basename(executable_path).lower() if executable_path else ""
    command_tokens = _proc_cmdline(pid)
    authority_targets = set(_authority_targets())
    invoked_codex = executable in CODEX_BASENAMES or (
        executable_path is not None and os.path.abspath(executable_path) in authority_targets
    )
    if command_tokens is not None:
        invoked_codex = invoked_codex or any(
            os.path.basename(token).lower() in CODEX_BASENAMES
            or os.path.abspath(token) in authority_targets
            or "@openai/codex" in token
            for token in command_tokens
        )
    if not invoked_codex:
        return False
    environment = _proc_environment(pid)
    if environment is None:
        return True
    if environment.get("CODEX_HOME") == str(candidate) or environment.get("HOME") == str(candidate):
        return True
    try:
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return True
    return _path_is_under(cwd, candidate)


def _eligible_profile_alias() -> str | None:
    """Read-only deterministic profile selection; no process is disturbed."""
    pids: list[int] = []
    try:
        for entry in os.scandir("/proc"):
            if entry.name.isdigit():
                pids.append(int(entry.name))
    except OSError:
        return None
    for alias in ("codex3", "codex2"):
        try:
            candidate = _safe_profile_path(alias)
        except _P7Stop:
            continue
        if not any(_codex_process_owns_candidate(pid, candidate) for pid in pids):
            return alias
    return None


def _is_regular(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    return info if stat.S_ISREG(info.st_mode) else None


def _lstat_regular(path: Path) -> tuple[os.stat_result | None, bool]:
    try:
        info = path.lstat()
    except OSError:
        return None, True
    return (info if stat.S_ISREG(info.st_mode) else None), False


def _category(relative: Path) -> str:
    lowered = relative.as_posix().lower()
    parts = set(lowered.split("/"))
    suffix = relative.suffix.lower()
    if "cache" in parts or "/cache/" in f"/{lowered}/":
        return "CACHE"
    if suffix in {".sqlite", ".sqlite3", ".db", ".wal", ".shm"} or "state" in parts:
        return "STATE_DB"
    if suffix in {".log", ".logjson"} or "log" in parts or "logs" in parts:
        return "LOG"
    if suffix in {".jsonl", ".json", ".rollout"} or parts.intersection({"session", "sessions", "history", "rollout", "rollouts"}):
        return "SESSION_HISTORY"
    return "OTHER"


def _empty_categories() -> dict[str, int]:
    return {name: 0 for name in CATEGORIES}


def _walk_directories(root: Path, directories: list[str], scan_errors: list[int]) -> None:
    kept: list[str] = []
    for name in directories:
        path = root / name
        try:
            info = path.lstat()
        except OSError:
            scan_errors[0] += 1
            continue
        if not stat.S_ISLNK(info.st_mode):
            kept.append(name)
    directories[:] = kept


def _home_baseline(home: Path) -> dict[str, Any]:
    identities: set[tuple[str, str]] = set()
    regular_count = 0
    total_bytes = 0
    scan_errors = [0]

    def onerror(_error: OSError) -> None:
        scan_errors[0] += 1

    for root, directories, files in os.walk(home, followlinks=False, onerror=onerror):
        _walk_directories(Path(root), directories, scan_errors)
        for name in files:
            path = Path(root) / name
            info, lstat_failed = _lstat_regular(path)
            if lstat_failed:
                scan_errors[0] += 1
                continue
            if info is None:
                continue
            relative = path.relative_to(home)
            category = _category(relative)
            regular_count += 1
            total_bytes += info.st_size
            if category == "SESSION_HISTORY":
                identities.add((relative.as_posix(), category))
    identity_bytes = "\n".join(f"{path}\0{category}" for path, category in sorted(identities)).encode()
    return {
        "regular_file_count": regular_count,
        "total_regular_bytes": total_bytes,
        "session_identities": identities,
        "session_identity_sha256": _sha256(identity_bytes),
        "scan_errors": scan_errors[0],
    }


def _session_identities_with_thread(home: Path, thread_id: str) -> tuple[set[tuple[str, str]], int]:
    identities: set[tuple[str, str]] = set()
    scan_errors = [0]
    needle = ((THREAD_ID, thread_id.encode("utf-8")),)

    def onerror(_error: OSError) -> None:
        scan_errors[0] += 1

    for root, directories, files in os.walk(home, followlinks=False, onerror=onerror):
        _walk_directories(Path(root), directories, scan_errors)
        for name in files:
            path = Path(root) / name
            info, lstat_failed = _lstat_regular(path)
            if lstat_failed:
                scan_errors[0] += 1
                continue
            if info is None:
                continue
            relative = path.relative_to(home)
            if _category(relative) != "SESSION_HISTORY":
                continue
            counts, _matched_bytes, _total_bytes, file_scan_errors = _scan_file(path, needle)
            scan_errors[0] += file_scan_errors
            if counts[THREAD_ID]:
                identities.add((relative.as_posix(), "SESSION_HISTORY"))
    return identities, scan_errors[0]


def _scan_file(path: Path, needles: tuple[tuple[str, bytes], ...]) -> tuple[dict[str, int], int, int, int]:
    counts = {name: 0 for name, _ in needles}
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return counts, 0, 0, 1
    total_bytes = 0
    hit_bytes = 0
    overlap = b""
    offset = 0
    maximum = max((len(needle) for _, needle in needles), default=1)
    try:
        stream = os.fdopen(descriptor, "rb", closefd=True)
    except OSError:
        try:
            os.close(descriptor)
        except OSError:
            pass
        return {name: 0 for name, _ in needles}, 0, 0, 1
    try:
        with stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                chunk_start = offset
                offset += len(chunk)
                total_bytes += len(chunk)
                combined = overlap + chunk
                combined_base = chunk_start - len(overlap)
                for name, needle in needles:
                    position = combined.find(needle)
                    while position >= 0:
                        absolute_start = combined_base + position
                        if absolute_start + len(needle) > chunk_start:
                            counts[name] += 1
                        position = combined.find(needle, position + 1)
                overlap = combined[-(maximum - 1):] if maximum > 1 else b""
    except OSError:
        return {name: 0 for name, _ in needles}, 0, 0, 1
    if any(counts.values()):
        hit_bytes = total_bytes
    return counts, hit_bytes, total_bytes, 0


def _scan_home(home: Path, *, thread_id: str, markers: tuple[str, ...]) -> dict[str, Any]:
    needles = ((THREAD_ID, thread_id.encode()),) + tuple(
        (CONTENT_MARKER, marker.encode()) for marker in markers
    )
    thread_by_category = _empty_categories()
    content_by_category = _empty_categories()
    files_by_category = _empty_categories()
    bytes_by_category = _empty_categories()
    log_only_identifier_matches = 0
    thread_matches = 0
    content_matches = 0
    matched_files = 0
    aggregate_bytes = 0
    scan_errors = [0]

    def onerror(_error: OSError) -> None:
        scan_errors[0] += 1

    for root, directories, files in os.walk(home, followlinks=False, onerror=onerror):
        _walk_directories(Path(root), directories, scan_errors)
        for name in files:
            path = Path(root) / name
            info, lstat_failed = _lstat_regular(path)
            if lstat_failed:
                scan_errors[0] += 1
                continue
            if info is None:
                continue
            relative = path.relative_to(home)
            category = _category(relative)
            counts, matched_bytes, _, file_scan_errors = _scan_file(path, needles)
            scan_errors[0] += file_scan_errors
            file_thread = counts[THREAD_ID]
            file_content = counts[CONTENT_MARKER]
            if file_thread or file_content:
                matched_files += 1
                files_by_category[category] += 1
                bytes_by_category[category] += matched_bytes
                aggregate_bytes += matched_bytes
            thread_matches += file_thread
            content_matches += file_content
            thread_by_category[category] += file_thread
            content_by_category[category] += file_content
            if category == "LOG" and file_thread and not file_content:
                log_only_identifier_matches += file_thread
    return {
        "thread_id_matches": thread_matches,
        "content_marker_matches": content_matches,
        "matched_file_count": matched_files,
        "aggregate_bytes": aggregate_bytes,
        "thread_id_matches_by_category": thread_by_category,
        "content_marker_matches_by_category": content_by_category,
        "matched_file_count_by_category": files_by_category,
        "aggregate_bytes_by_category": bytes_by_category,
        "log_only_identifier_matches": log_only_identifier_matches,
        "scan_errors": scan_errors[0],
    }


def _isolated_environment(home: Path) -> dict[str, str]:
    return {
        "CODEX_HOME": str(home),
        "HOME": str(home),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
    }


def _verify_parent_directories(path: Path) -> bool:
    current = path.parent
    while True:
        try:
            info = current.lstat()
        except OSError:
            return False
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            return False
        if current == current.parent:
            return True
        current = current.parent


def _verify_installed_authority() -> tuple[str, bool]:
    executable = Path(CODEX)
    _require(executable.is_absolute(), "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
    try:
        info = executable.lstat()
    except OSError:
        raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP") from None
    if stat.S_ISREG(info.st_mode):
        path_kind = "REGULAR"
        _require(
            info.st_uid == 0
            and os.access(executable, os.X_OK)
            and not info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            and _verify_parent_directories(executable),
            "P7_INSTALLED_AUTHORITY_DRIFT_STOP",
        )
    elif stat.S_ISLNK(info.st_mode):
        path_kind = "SYMLINK"
        _require(info.st_uid == 0 and _verify_parent_directories(executable), "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
        try:
            resolved = executable.resolve(strict=True)
            target_info = resolved.lstat()
        except OSError:
            raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP") from None
        _require(
            stat.S_ISREG(target_info.st_mode)
            and target_info.st_uid == 0
            and os.access(resolved, os.X_OK)
            and not target_info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            and _verify_parent_directories(resolved),
            "P7_INSTALLED_AUTHORITY_DRIFT_STOP",
        )
    else:
        raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP")
    with tempfile.TemporaryDirectory(prefix="codex-control-p7-authority-") as directory:
        root = Path(directory)
        home = root / "codex-home"
        output = root / "schema-output"
        output.mkdir()
        try:
            version = subprocess.run(
                [CODEX, "--version"],
                env=_isolated_environment(home),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
            schema = subprocess.run(
                [CODEX, "app-server", "generate-json-schema", "--out", str(output)],
                env=_isolated_environment(home),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP") from None
        _require(version.returncode == 0 and version.stdout.strip() == VERSION.encode(), "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
        _require(schema.returncode == 0, "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
        aggregate = output / "codex_app_server_protocol.schemas.json"
        aggregate_info = _is_regular(aggregate)
        _require(aggregate_info is not None, "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
        try:
            observed = _sha256(aggregate.read_bytes())
        except OSError:
            raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP") from None
        _require(observed == SCHEMA_SHA256, "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
    return path_kind, True


def _git_facts(expected_head: str) -> None:
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        status = subprocess.run(["git", "status", "--short"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError:
        raise _P7Stop("P7_REPOSITORY_GATE_STOP") from None
    _require(head.returncode == 0 and head.stdout.strip() == expected_head, "P7_REPOSITORY_GATE_STOP")
    _require(status.returncode == 0 and not status.stdout, "P7_REPOSITORY_GATE_STOP")


def _create_recovery(path: Path, *, nonce: str, alias: str, home: Path, commit: str) -> None:
    payload = {
        "run_nonce": nonce,
        "profile_alias": alias,
        "codex_home": str(home),
        "commit_a_sha": commit,
        "stage": "CATALOG_CONFIRMED",
    }
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
    except OSError:
        raise _P7Stop("P7_RECOVERY_RECORD_FAILED") from None


def _update_recovery(path: Path, *, nonce: str, alias: str, home: Path, commit: str, thread_id: str) -> None:
    payload = {
        "run_nonce": nonce,
        "profile_alias": alias,
        "codex_home": str(home),
        "commit_a_sha": commit,
        "stage": "START_CONFIRMED",
        "thread_id": thread_id,
    }
    temporary = path.with_name(path.name + ".update")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise _P7Stop("P7_RECOVERY_RECORD_FAILED") from None


def _write_result(path: Path, result: dict[str, Any]) -> None:
    encoded = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)
    except OSError:
        raise _P7Stop("P7_RESULT_WRITE_FAILED") from None


def _counting_manager(manager: CodexRuntimeManager) -> Any:
    class CountingManager:
        def __init__(self) -> None:
            self.acquire_count = 0
            self.last_runtime: Any | None = None

        async def acquire(self, profile_id: str) -> Any:
            self.acquire_count += 1
            self.last_runtime = await manager.acquire(profile_id)
            return self.last_runtime

    return CountingManager()


class _StrictApprovalOperator:
    def __init__(self, *, thread_id: str, turn_id: str, command: str, cwd: str, target: str) -> None:
        self.thread_id = thread_id
        self.turn_id = turn_id
        self.command = command
        self.cwd = cwd
        self.target = target
        self.request_count = 0
        self.allow_count = 0
        self.first_request_kind: ApprovalKind | None = None

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.request_count += 1
        if self.request_count == 1:
            self.first_request_kind = request.kind
        context = set(request.context_lines)
        allowed = (
            self.request_count == 1
            and request.kind is ApprovalKind.COMMAND_EXECUTION
            and request.thread_id == self.thread_id
            and request.turn_id == self.turn_id
            and f"command: {self.command}" in context
            and f"cwd: {self.cwd}" in context
            and self.target in "\n".join(request.context_lines)
        )
        if allowed:
            self.allow_count += 1
            return ApprovalDecision.ALLOW
        return ApprovalDecision.DENY


def _safe_json_file(path: Path, maximum_bytes: int) -> dict[str, Any] | None:
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_ISLNK(info.st_mode)
            or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > maximum_bytes
        ):
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _recovery_record_identity() -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in Path("/var/tmp").glob("codex-control-p7-recovery-*.json"):
        value = _safe_json_file(path, 64 * 1024)
        if value is None:
            continue
        thread_id = value.get("thread_id")
        nonce = value.get("run_nonce")
        if (
            value.get("profile_alias") == "codex3"
            and value.get("codex_home") == PROFILE_HOMES["codex3"]
            and value.get("commit_a_sha") == "740decef73627c9b44dfce1a0f85703e59fd6183"
            and value.get("stage") == "START_CONFIRMED"
            and isinstance(thread_id, str)
            and _sha256(thread_id.encode("utf-8")) == RECOVERY_THREAD_SHA256
            and isinstance(nonce, str)
            and len(nonce) == 48
            and all(character in "0123456789abcdef" for character in nonce)
        ):
            matches.append((path, value))
    _require(len(matches) == 1, "P7_RECOVERY_RECORD_IDENTITY_STOP")
    return matches[0]


def _original_result_identity() -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    try:
        candidates = tuple(Path("/var/tmp").iterdir())
    except OSError:
        candidates = ()
    for path in candidates:
        value = _safe_json_file(path, 256 * 1024)
        if value is None:
            continue
        if (
            value.get("commit_a_sha") == "740decef73627c9b44dfce1a0f85703e59fd6183"
            and value.get("thread_id_sha256") == RECOVERY_THREAD_SHA256
            and value.get("stage") == "P7_REAL_APPROVAL_NOT_OBSERVED"
            and value.get("profile_alias") == "codex3"
            and isinstance(value.get("preexisting_session_count"), int)
            and not isinstance(value.get("preexisting_session_count"), bool)
            and isinstance(value.get("preexisting_session_identity_sha256"), str)
        ):
            matches.append(value)
    _require(len(matches) == 1, "P7_RECOVERY_BASELINE_IDENTITY_STOP")
    return {
        "preexisting_session_count": matches[0]["preexisting_session_count"],
        "preexisting_session_identity_sha256": matches[0]["preexisting_session_identity_sha256"],
    }


def _exact_sentinel_processes(path: Path) -> list[int]:
    encoded = str(path).encode("utf-8")
    matches: list[int] = []
    try:
        entries = tuple(os.scandir("/proc"))
    except OSError:
        return matches
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            tokens = Path("/proc", entry.name, "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if any(encoded in token for token in tokens):
            matches.append(int(entry.name))
    return matches


def _safe_sentinel_cleanup(path: Path) -> tuple[int, int, bool, bool]:
    owned = _exact_sentinel_processes(path)
    for pid in owned:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except OSError:
            pass
    deadline = time.monotonic() + 5.0
    live: list[int] = []
    while time.monotonic() < deadline:
        live = []
        for pid in owned:
            try:
                os.kill(pid, 0)
                live.append(pid)
            except ProcessLookupError:
                pass
            except OSError:
                live.append(pid)
        if not live:
            break
        time.sleep(0.05)
    for pid in live:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        live = []
        for pid in owned:
            try:
                os.kill(pid, 0)
                live.append(pid)
            except ProcessLookupError:
                pass
            except OSError:
                live.append(pid)
        if not live:
            break
        time.sleep(0.05)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return len(owned), len(live), True, True
    except OSError:
        return len(owned), len(live), False, False
    safe_file = stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode) and info.st_uid == 0
    if not safe_file:
        return len(owned), len(live), False, False
    try:
        path.unlink()
    except OSError:
        return len(owned), len(live), False, False
    return len(owned), len(live), True, True


class _RecoveryApprovalOperator:
    _WRAPPERS = frozenset(("bash", "/bin/bash", "sh", "/bin/sh"))

    def __init__(
        self,
        *,
        thread_id: str,
        recovery_cwd: str,
        command: str,
        marker: str,
        sentinel: str,
        expected_turn_id: asyncio.Future[str],
    ) -> None:
        self._thread_id = thread_id
        self._recovery_cwd = recovery_cwd
        self._command = command
        self._marker = marker
        self._sentinel = sentinel
        self._expected_turn_id = expected_turn_id
        self.request_count = 0
        self.first_request_kind: ApprovalKind | None = None
        self.allow_count = 0
        self.request_observed = False
        self.mismatch_flags: tuple[str, ...] = ()

    @staticmethod
    def _context_value(lines: tuple[str, ...], prefix: str) -> str | None:
        for line in lines:
            if line.startswith(prefix):
                return line[len(prefix):]
        return None

    def _safe_command_relation(self, requested: str | None) -> bool:
        if requested is None:
            return False
        try:
            expected = shlex.split(self._command)
            observed = shlex.split(requested)
        except ValueError:
            return False
        if observed == expected:
            return True
        return (
            len(expected) == 3
            and len(observed) == 3
            and observed[0] in self._WRAPPERS
            and observed[1] == "-lc"
            and observed[2] == expected[2]
        )

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.request_count += 1
        self.request_observed = True
        self.first_request_kind = request.kind
        flags: set[str] = set()
        if self.request_count != 1:
            flags.add("REQUEST_COUNT")
        if request.kind is not ApprovalKind.COMMAND_EXECUTION:
            flags.add("KIND")
        if request.thread_id != self._thread_id:
            flags.add("THREAD")
        turn_id: str | None = None
        if not self._expected_turn_id.done():
            try:
                turn_id = await asyncio.wait_for(asyncio.shield(self._expected_turn_id), timeout=30)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                flags.add("TURN_ID_UNAVAILABLE")
                turn_id = None
        else:
            try:
                turn_id = self._expected_turn_id.result()
            except (asyncio.CancelledError, Exception):
                turn_id = None
        if turn_id is None or request.turn_id != turn_id:
            flags.add("TURN")
        cwd = self._context_value(request.context_lines, "cwd: ")
        command = self._context_value(request.context_lines, "command: ")
        if cwd != self._recovery_cwd:
            flags.add("CWD")
        command_context = command or ""
        if self._marker not in command_context:
            flags.add("COMMAND_MARKER")
        if self._sentinel not in command_context:
            flags.add("SENTINEL")
        if "sleep 120" not in command_context:
            flags.add("DELAY")
        if not self._safe_command_relation(command):
            flags.add("COMMAND_GRAMMAR")
        self.mismatch_flags = tuple(sorted(flags))
        allowed = not flags
        if allowed:
            self.allow_count += 1
            return ApprovalDecision.ALLOW
        return ApprovalDecision.DENY


async def _shutdown_manager(manager: CodexRuntimeManager) -> bool:
    try:
        await manager.shutdown_all()
    except Exception:
        return False
    return True


class P7RealCodexT3Acceptance(unittest.IsolatedAsyncioTestCase):
    async def test_authorized_real_codex_t3(self) -> None:
        if os.environ.get("CODEXCONTROL_P7_REAL_T3") != REAL_GATE:
            raise unittest.SkipTest("P7 real gate is not authorized")

        expected_head = os.environ.get("CODEXCONTROL_P7_EXPECTED_HEAD", "")
        alias = os.environ.get("CODEXCONTROL_P7_PROFILE_ID", "")
        home_value = os.environ.get("CODEXCONTROL_P7_CODEX_HOME", "")
        result_value = os.environ.get("CODEXCONTROL_P7_RESULT_PATH", "")
        result_path = Path(result_value)
        _require(
            len(expected_head) == 40
            and all(character in "0123456789abcdef" for character in expected_head)
            and alias in PROFILE_HOMES
            and home_value == PROFILE_HOMES.get(alias)
            and result_path.is_absolute()
            and result_path.parent == Path("/var/tmp")
            and not result_path.exists(),
            "P7_GATE_INVALID",
        )

        result: dict[str, Any] = {
            "status": "FAIL",
            "stage": "P7_NOT_STARTED",
            "commit_a_sha": expected_head,
            "profile_alias": alias,
            "default_home_used": False,
            "credential_copy": False,
            "auth_migration": False,
            "runtime_generations": [],
            "executable_path_kind": None,
            "executable_resolved_target_safe": None,
            "thread_id_sha256": None,
            "marker_sha256": [],
            "baseline_scan_errors": None,
            "predelete_scan_errors": None,
            "postdelete_scan_errors": None,
            "real_thread_count": 0,
            "real_turn_count": 0,
            "thread_delete_calls": 0,
            "recovery_record_present": False,
            "recovery_record_removed": False,
            "temp_workdir_removed": False,
            "sentinel_removed_or_absent": False,
            "preexisting_session_count": 0,
            "removed_preexisting_count": 0,
            "runtime_acquire_during_interrupt": False,
            "approval_request_count": 0,
            "approval_response_count": 0,
            "sentinel_after_interrupt": "UNKNOWN",
        }
        manager: CodexRuntimeManager | None = None
        counting: Any | None = None
        temp_workdir: Path | None = None
        recovery_path: Path | None = None
        sentinel_path: Path | None = None
        thread_created = False
        delete_confirmed = False
        postdelete_gate_pass = False
        cleanup_pass = False

        try:
            _git_facts(expected_head)
            path_kind, resolved_target_safe = _verify_installed_authority()
            result["executable_path_kind"] = path_kind
            result["executable_resolved_target_safe"] = "PASS" if resolved_target_safe else "FAIL"
            selected = _eligible_profile_alias()
            _require(selected == alias, "P7_ISOLATION_GATE_BLOCKED", blocked=True)
            home = _safe_profile_path(selected)
            baseline = _home_baseline(home)
            result["baseline_scan_errors"] = baseline["scan_errors"]
            _require(baseline["scan_errors"] == 0, "P7_STORAGE_SCAN_ERROR_STOP")
            result["preexisting_session_count"] = len(baseline["session_identities"])
            result["preexisting_session_identity_sha256"] = baseline["session_identity_sha256"]
            nonce = secrets.token_hex(24)
            markers = tuple(secrets.token_hex(24) for _ in range(5))
            result["marker_sha256"] = [_sha256(marker.encode()) for marker in markers]
            m1, a1, a2, turn3_marker, _ = markers
            temp_workdir = Path(tempfile.mkdtemp(prefix="codex-control-p7-", dir="/tmp"))
            cwd = TrustedWorkingDirectory(str(temp_workdir))
            sentinel_path = Path(f"/var/tmp/codex-control-p7-sentinel-{nonce}.txt")
            _require(not sentinel_path.exists(), "P7_SENTINEL_PREEXISTING")
            command = f"sh -lc 'sleep 120; printf {turn3_marker} > {sentinel_path}'"

            profile = CodexProfile(selected, str(home), f"P7 {selected}")
            parent_environment = dict(os.environ)
            parent_environment["CODEX_HOME"] = str(home)
            parent_environment["HOME"] = str(home)
            manager = CodexRuntimeManager(
                [profile],
                client_version=VERSION,
                executable=CODEX,
                parent_environment=parent_environment,
            )
            counting = _counting_manager(manager)
            catalog_adapter = CodexModelCatalogAdapter(counting)
            thread_adapter = CodexThreadLifecycleAdapter(counting, catalog_adapter)
            turn_adapter = CodexTurnLifecycleAdapter(counting, catalog_adapter)

            runtime = await counting.acquire(selected)
            catalog = await catalog_adapter.get_catalog(selected, refresh=True)
            visible_defaults = tuple(model for model in catalog.models if not model.hidden and model.is_default)
            _require(len(catalog.models) > 0 and len(visible_defaults) == 1, "P7_AUTHENTICATED_CATALOG_INVALID")
            model = visible_defaults[0]
            effort = model.default_reasoning_effort
            _require(effort in model.supported_reasoning_efforts, "P7_AUTHENTICATED_CATALOG_INVALID")
            result["model_id"] = model.model_id
            result["reasoning_effort"] = effort
            result["catalog_status"] = "PASS"
            result["visible_default_model_count"] = len(visible_defaults)
            result["catalog_runtime_generation"] = runtime.generation

            recovery_path = Path(f"/var/tmp/codex-control-p7-recovery-{nonce}.json")
            _create_recovery(recovery_path, nonce=nonce, alias=selected, home=home, commit=expected_head)
            result["recovery_record_present"] = True

            start = await thread_adapter.start(
                selected,
                model_id=model.model_id,
                reasoning_effort=effort,
                working_directory=cwd,
            )
            _require(start.status is ThreadOperationStatus.START_CONFIRMED, "P7_THREAD_START_FAILED")
            _require(isinstance(start.binding, ThreadBinding), "P7_THREAD_START_FAILED")
            thread_binding = start.binding
            thread_created = True
            result["real_thread_count"] = 1
            result["thread_id_sha256"] = _sha256(thread_binding.thread_id.encode())
            _update_recovery(
                recovery_path,
                nonce=nonce,
                alias=selected,
                home=home,
                commit=expected_head,
                thread_id=thread_binding.thread_id,
            )
            result["thread_start_status"] = start.status.name

            turn1_start = await turn_adapter.start_turn(
                thread_binding=thread_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=f"Remember this conversation marker {m1} and reply including {a1}.",
                working_directory=cwd,
            )
            _require(turn1_start.status is TurnStartStatus.CONFIRMED and turn1_start.binding is not None, "P7_TURN1_FAILED")
            turn1_binding = turn1_start.binding
            turn1_terminal = await turn_adapter.wait_turn(turn1_binding)
            _require(
                turn1_terminal.status is TurnTerminalStatus.COMPLETED
                and bool(turn1_terminal.messages)
                and any(a1 in message.text for message in turn1_terminal.messages),
                "P7_TURN1_FAILED",
            )
            result["real_turn_count"] = 1
            result["turn1_status"] = turn1_terminal.status.name
            result["turn1_marker_observed"] = True

            generation_one = runtime.generation
            result["runtime_generations"] = [generation_one]
            await manager.shutdown_profile(selected)
            resumed_runtime = await counting.acquire(selected)
            generation_two = resumed_runtime.generation
            _require(resumed_runtime is not runtime and generation_two > generation_one, "P7_RUNTIME_RESTART_FAILED")
            result["runtime_generations"].append(generation_two)
            resume = await thread_adapter.resume(binding=thread_binding, working_directory=cwd)
            _require(
                resume.status is ThreadOperationStatus.RESUME_CONFIRMED
                and resume.binding is thread_binding,
                "P7_THREAD_RESUME_FAILED",
            )
            result["resume_status"] = resume.status.name

            turn2_start = await turn_adapter.start_turn(
                thread_binding=thread_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=f"Provide the exact remembered marker {m1} and include {a2}.",
                working_directory=cwd,
            )
            _require(turn2_start.status is TurnStartStatus.CONFIRMED and turn2_start.binding is not None, "P7_TURN2_FAILED")
            turn2_terminal = await turn_adapter.wait_turn(turn2_start.binding)
            turn2_projection = "\n".join(message.text for message in turn2_terminal.messages)
            _require(
                turn2_terminal.status is TurnTerminalStatus.COMPLETED
                and bool(turn2_terminal.messages)
                and m1 in turn2_projection
                and a2 in turn2_projection,
                "P7_TURN2_FAILED",
            )
            result["real_turn_count"] = 2
            result["turn2_status"] = turn2_terminal.status.name
            result["turn2_memory_marker_observed"] = True
            result["multi_turn_memory"] = True

            turn3_start = await turn_adapter.start_turn(
                thread_binding=thread_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=f"Execute exactly this command once, with no substitute: {command}",
                working_directory=cwd,
            )
            _require(turn3_start.status is TurnStartStatus.CONFIRMED and turn3_start.binding is not None, "P7_TURN3_START_FAILED")
            turn3_binding = turn3_start.binding
            result["real_turn_count"] = 3
            operator = _StrictApprovalOperator(
                thread_id=thread_binding.thread_id,
                turn_id=turn3_binding.turn_id,
                command=command,
                cwd=str(temp_workdir),
                target=str(sentinel_path),
            )
            live_runtime = counting.last_runtime
            _require(live_runtime is not None and live_runtime.generation == generation_two, "P7_RUNTIME_OWNERSHIP_FAILED")
            bridge = CodexApprovalBridge(profile_id=selected, client=live_runtime.client, operator=operator)
            approval_task = asyncio.create_task(bridge.handle_next())
            try:
                approval = await asyncio.wait_for(asyncio.shield(approval_task), timeout=90)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                if not approval_task.done():
                    approval_task.cancel()
                    await asyncio.gather(approval_task, return_exceptions=True)
                raise _P7Stop("P7_REAL_APPROVAL_NOT_OBSERVED") from None
            _require(
                approval.status is ApprovalHandlingStatus.ALLOWED
                and approval.kind is ApprovalKind.COMMAND_EXECUTION
                and operator.request_count == 1
                and operator.allow_count == 1,
                "P7_REAL_APPROVAL_NOT_OBSERVED",
            )
            result["approval_status"] = approval.status.name
            result["approval_kind"] = approval.kind.name
            result["approval_request_count"] = operator.request_count
            result["approval_response_count"] = operator.allow_count
            result["approval_observed"] = True

            acquire_before_interrupt = counting.acquire_count
            interrupt = await turn_adapter.interrupt_turn(turn3_binding)
            result["runtime_acquire_during_interrupt"] = counting.acquire_count != acquire_before_interrupt
            _require(
                interrupt.status in {TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED}
                and interrupt.terminal_result is not None
                and interrupt.terminal_result.status is TurnTerminalStatus.FAILED,
                "P7_INTERRUPT_AMBIGUOUS",
            )
            _require(not result["runtime_acquire_during_interrupt"], "P7_INTERRUPT_RUNTIME_REACQUIRE")
            _require(not sentinel_path.exists(), "P7_INTERRUPT_SIDE_EFFECT_BLOCKER")
            result["interrupt_status"] = interrupt.status.name
            result["interrupt_terminal_status"] = interrupt.terminal_result.status.name
            result["sentinel_after_interrupt"] = "ABSENT"
            result["interrupt_runtime_reacquire"] = False

            client_pending = getattr(live_runtime.client, "_pending_server", None)
            _require(isinstance(client_pending, dict) and not client_pending, "P7_REAL_APPROVAL_NOT_OBSERVED")
            await manager.shutdown_profile(selected)
            predelete = _scan_home(home, thread_id=thread_binding.thread_id, markers=markers)
            result["predelete_scan"] = predelete
            result["predelete_scan_errors"] = predelete["scan_errors"]
            _require(predelete["scan_errors"] == 0, "P7_STORAGE_SCAN_ERROR_STOP")
            _require(
                predelete["thread_id_matches"] > 0 or predelete["content_marker_matches"] > 0,
                "P7_PREDELETE_STORAGE_PROOF_INCONCLUSIVE",
            )
            result["predelete_physical_proof"] = True

            delete = await thread_adapter.delete(binding=thread_binding)
            result["thread_delete_calls"] = 1
            _require(delete.status is ThreadOperationStatus.DELETE_CONFIRMED, "P7_DELETE_UNKNOWN_STOP")
            delete_confirmed = True
            result["delete_status"] = delete.status.name
            await manager.shutdown_profile(selected)
            postdelete = _scan_home(home, thread_id=thread_binding.thread_id, markers=markers)
            result["postdelete_scan"] = postdelete
            result["postdelete_scan_errors"] = postdelete["scan_errors"]
            _require(postdelete["scan_errors"] == 0, "P7_STORAGE_SCAN_ERROR_STOP")
            active_thread_residuals = sum(postdelete["thread_id_matches_by_category"][name] for name in ("SESSION_HISTORY", "STATE_DB"))
            unclassified_residuals = sum(postdelete["thread_id_matches_by_category"][name] for name in ("CACHE", "OTHER"))
            _require(postdelete["content_marker_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(active_thread_residuals == 0 and unclassified_residuals == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            result["postdelete_active_thread_id_matches"] = active_thread_residuals
            result["postdelete_log_identifier_residuals"] = postdelete["log_only_identifier_matches"]
            result["postdelete_unclassified_residuals"] = unclassified_residuals
            result["postdelete_content_marker_matches"] = postdelete["content_marker_matches"]

            final_baseline = _home_baseline(home)
            _require(final_baseline["scan_errors"] == 0, "P7_STORAGE_SCAN_ERROR_STOP")
            removed = baseline["session_identities"] - final_baseline["session_identities"]
            result["removed_preexisting_count"] = len(removed)
            _require(not removed, "P7_UNRELATED_STORAGE_MUTATION_BLOCKER")
            result["preexisting_session_artifacts_removed"] = 0
            postdelete_gate_pass = True
            result["final_regular_file_count"] = final_baseline["regular_file_count"]
            result["final_total_regular_bytes"] = final_baseline["total_regular_bytes"]
            result["status"] = "PASS"
            result["stage"] = "COMPLETE"
        except _P7Stop as stop:
            result["status"] = "BLOCKED" if stop.blocked else "FAIL"
            result["stage"] = stop.stage
        except Exception:
            result["status"] = "FAIL"
            result["stage"] = "P7_UNEXPECTED_RUNTIME_FAILURE"
        finally:
            if manager is not None:
                shutdown_ok = await _shutdown_manager(manager)
            else:
                shutdown_ok = True
            if result["status"] == "PASS" and not shutdown_ok:
                result["status"] = "FAIL"
                result["stage"] = "P7_CLEANUP_FAILED"
            if sentinel_path is not None:
                try:
                    sentinel_path.unlink(missing_ok=True)
                except OSError:
                    pass
                result["sentinel_removed_or_absent"] = not sentinel_path.exists()
            if temp_workdir is not None:
                try:
                    shutil.rmtree(temp_workdir)
                except OSError:
                    pass
                result["temp_workdir_removed"] = not temp_workdir.exists()
            cleanup_pass = shutdown_ok and bool(result["sentinel_removed_or_absent"]) and bool(result["temp_workdir_removed"])
            if result["status"] == "PASS" and not cleanup_pass:
                result["status"] = "FAIL"
                result["stage"] = "P7_CLEANUP_FAILED"
            if result["status"] == "PASS" and delete_confirmed and postdelete_gate_pass and cleanup_pass and recovery_path is not None:
                try:
                    recovery_path.unlink()
                except OSError:
                    result["status"] = "FAIL"
                    result["stage"] = "P7_RECOVERY_CLEANUP_FAILED"
            result["recovery_record_removed"] = recovery_path is not None and not recovery_path.exists()
            result["recovery_record_present"] = recovery_path is not None and recovery_path.exists()
            result["cleanup_pass"] = cleanup_pass
            try:
                _write_result(result_path, result)
            except _P7Stop:
                result["status"] = "FAIL"
                result["stage"] = "P7_RESULT_WRITE_FAILED"

        if result["status"] != "PASS":
            self.fail(str(result["stage"]))

    async def test_authorized_recovery_turn_and_delete(self) -> None:
        if os.environ.get("CODEXCONTROL_P7_RECOVERY_T3") != RECOVERY_GATE:
            raise unittest.SkipTest("P7 same-thread recovery gate is not authorized")

        expected_head = os.environ.get("CODEXCONTROL_P7_EXPECTED_HEAD", "")
        expected_thread_sha = os.environ.get("CODEXCONTROL_P7_RECOVERY_THREAD_SHA256", "")
        result_value = os.environ.get("CODEXCONTROL_P7_RECOVERY_RESULT_PATH", "")
        result_path = Path(result_value)
        _require(
            len(expected_head) == 40
            and all(character in "0123456789abcdef" for character in expected_head)
            and expected_thread_sha == RECOVERY_THREAD_SHA256
            and result_path.is_absolute()
            and result_path.parent == Path("/var/tmp")
            and len(result_path.name) <= 128
            and not result_path.exists()
            and not result_path.is_symlink(),
            "P7_GATE_INVALID",
        )

        result: dict[str, Any] = {
            "status": "FAIL",
            "stage": "P7_RECOVERY_NOT_STARTED",
            "commit_e_sha": expected_head,
            "profile_alias": "codex3",
            "thread_id_sha256": RECOVERY_THREAD_SHA256,
            "executable_path_kind": None,
            "executable_resolved_target_safe": None,
            "model_id": None,
            "reasoning_effort": None,
            "resume_status": "NOT_RUN",
            "turn4_start_status": "NOT_RUN",
            "approval_request_observed": "NO",
            "approval_request_count": 0,
            "approval_kind": "NONE",
            "approval_mismatch_flags": [],
            "approval_allow_count": 0,
            "approval_result": "NOT_RUN",
            "approval_wire_response_count": 0,
            "interrupt_status": "NOT_RUN",
            "interrupt_terminal_status": "NOT_RUN",
            "interrupt_runtime_reacquire": "NOT_RUN",
            "recovery_sentinel_after_interrupt": "NOT_RUN",
            "baseline_scan_errors": None,
            "predelete_scan_errors": None,
            "predelete_recovery_content_markers": 0,
            "predelete_scan_categories": {},
            "predelete_physical_proof": "NOT_RUN",
            "thread_delete_calls": 0,
            "delete_status": "NOT_RUN",
            "delete_retry": False,
            "postdelete_scan_errors": None,
            "postdelete_recovery_content_markers": None,
            "postdelete_active_thread_id_matches": None,
            "postdelete_log_thread_id_residuals": None,
            "postdelete_unclassified_thread_id_residuals": None,
            "original_baseline_reconciliation_before_turn": False,
            "original_baseline_reconciliation_after_delete": False,
            "preexisting_session_artifacts_removed": None,
            "recovery_record_removed": False,
            "runtime_cleanup_pass": False,
            "recovery_temp_workdir_removed": False,
            "recovery_sentinel_removed_or_absent": False,
            "recovery_delayed_process_live": "UNKNOWN",
            "real_thread_count": 1,
            "real_turn_count": 3,
        }

        manager: CodexRuntimeManager | None = None
        counting: Any | None = None
        recovery_path: Path | None = None
        recovery_record: dict[str, Any] | None = None
        sentinel_path: Path | None = None
        temp_workdir: Path | None = None
        approval_task: asyncio.Task[Any] | None = None
        delete_confirmed = False
        postdelete_gate_pass = False
        approval_pass = False
        interrupt_pass = False
        sentinel_cleanup_safe = True
        delayed_process_live = 0
        shutdown_ok = True
        try:
            _git_facts(expected_head)
            path_kind, resolved_target_safe = _verify_installed_authority()
            result["executable_path_kind"] = path_kind
            result["executable_resolved_target_safe"] = "PASS" if resolved_target_safe else "FAIL"

            recovery_path, recovery_record = _recovery_record_identity()
            original = _original_result_identity()
            _require(_eligible_profile_alias() == "codex3", "P7_RECOVERY_PROFILE_BUSY_STOP", blocked=True)
            home = _safe_profile_path("codex3")
            baseline = _home_baseline(home)
            owned_before, owned_before_errors = _session_identities_with_thread(home, recovery_record["thread_id"])
            result["baseline_scan_errors"] = baseline["scan_errors"] + owned_before_errors
            _require(result["baseline_scan_errors"] == 0, "P7_ORIGINAL_BASELINE_RECONCILIATION_STOP")
            unrelated_before = baseline["session_identities"] - owned_before
            unrelated_before_bytes = "\n".join(
                f"{path}\0{category}" for path, category in sorted(unrelated_before)
            ).encode("utf-8")
            before_reconciled = (
                len(unrelated_before) == original["preexisting_session_count"]
                and _sha256(unrelated_before_bytes) == original["preexisting_session_identity_sha256"]
            )
            result["original_baseline_reconciliation_before_turn"] = before_reconciled
            _require(before_reconciled, "P7_ORIGINAL_BASELINE_RECONCILIATION_STOP")

            new_nonce = secrets.token_hex(24)
            markers = tuple(secrets.token_hex(24) for _ in range(4))
            command_marker, prompt_marker, _, _ = markers
            temp_workdir = Path(tempfile.mkdtemp(prefix="codex-control-p7-recovery-", dir="/tmp"))
            cwd = TrustedWorkingDirectory(str(temp_workdir))
            sentinel_path = Path(f"/var/tmp/codex-control-p7-recovery-sentinel-{new_nonce}.txt")
            try:
                sentinel_path.lstat()
            except FileNotFoundError:
                pass
            except OSError:
                raise _P7Stop("P7_RECOVERY_SENTINEL_SAFETY_STOP") from None
            else:
                raise _P7Stop("P7_RECOVERY_SENTINEL_SAFETY_STOP")

            inner_command = f"sleep 120; printf {command_marker} > {sentinel_path}"
            command = f"sh -lc '{inner_command}'"
            retained_binding = ThreadBinding("codex3", recovery_record["thread_id"])
            profile = CodexProfile("codex3", str(home), "P7 codex3 recovery")
            parent_environment = dict(os.environ)
            parent_environment["CODEX_HOME"] = str(home)
            parent_environment["HOME"] = str(home)
            manager = CodexRuntimeManager(
                [profile],
                client_version=VERSION,
                executable=CODEX,
                parent_environment=parent_environment,
            )
            counting = _counting_manager(manager)
            catalog_adapter = CodexModelCatalogAdapter(counting)
            thread_adapter = CodexThreadLifecycleAdapter(counting, catalog_adapter)
            turn_adapter = CodexTurnLifecycleAdapter(counting, catalog_adapter)

            runtime = await counting.acquire("codex3")
            catalog = await catalog_adapter.get_catalog("codex3", refresh=True)
            visible_defaults = tuple(model for model in catalog.models if not model.hidden and model.is_default)
            _require(len(catalog.models) > 0 and len(visible_defaults) == 1, "P7_AUTHENTICATED_CATALOG_INVALID")
            model = visible_defaults[0]
            effort = model.default_reasoning_effort
            _require(effort in model.supported_reasoning_efforts, "P7_AUTHENTICATED_CATALOG_INVALID")
            result["model_id"] = model.model_id
            result["reasoning_effort"] = effort

            resumed = await thread_adapter.resume(binding=retained_binding, working_directory=cwd)
            _require(
                resumed.status is ThreadOperationStatus.RESUME_CONFIRMED
                and resumed.binding is retained_binding,
                "P7_RECOVERY_RESUME_FAILED",
            )
            result["resume_status"] = resumed.status.name

            expected_turn_id = asyncio.get_running_loop().create_future()
            operator = _RecoveryApprovalOperator(
                thread_id=retained_binding.thread_id,
                recovery_cwd=str(temp_workdir),
                command=command,
                marker=command_marker,
                sentinel=str(sentinel_path),
                expected_turn_id=expected_turn_id,
            )
            live_runtime = counting.last_runtime
            _require(live_runtime is not None and live_runtime.generation == runtime.generation, "P7_RUNTIME_OWNERSHIP_FAILED")
            bridge = CodexApprovalBridge(profile_id="codex3", client=live_runtime.client, operator=operator)
            approval_task = asyncio.create_task(bridge.handle_next())
            for _ in range(2):
                await asyncio.sleep(0)
            _require(not approval_task.done(), "P7_RECOVERY_APPROVAL_ARM_STOP")

            turn4_start = await turn_adapter.start_turn(
                thread_binding=retained_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=(
                    f"Use the command-execution tool and execute exactly this supplied command once: {command}. "
                    f"The recovery marker is {prompt_marker}. Do not simulate, explain, substitute, or execute any "
                    "other action. Because this requires permission outside the workspace, request operator "
                    "approval rather than choosing an alternative."
                ),
                working_directory=cwd,
            )
            result["turn4_start_status"] = turn4_start.status.name
            _require(
                turn4_start.status is TurnStartStatus.CONFIRMED
                and turn4_start.binding is not None,
                "P7_RECOVERY_TURN4_START_FAILED",
            )
            turn4_binding = turn4_start.binding
            result["real_turn_count"] = 4
            _require(not expected_turn_id.done(), "P7_RECOVERY_TURN4_ID_PUBLICATION_STOP")
            expected_turn_id.set_result(turn4_binding.turn_id)

            approval: Any | None = None
            approval_failed_unknown = False
            approval_timed_out = False
            try:
                approval = await asyncio.wait_for(asyncio.shield(approval_task), timeout=90)
            except asyncio.TimeoutError:
                approval_timed_out = True
                if not approval_task.done():
                    approval_task.cancel()
                    await asyncio.gather(approval_task, return_exceptions=True)
            except asyncio.CancelledError:
                if not approval_task.done():
                    approval_task.cancel()
                    await asyncio.gather(approval_task, return_exceptions=True)
                raise _P7Stop("P7_RECOVERY_APPROVAL_TIMEOUT") from None

            result["approval_request_observed"] = "YES" if operator.request_observed else "NO"
            result["approval_request_count"] = operator.request_count
            result["approval_kind"] = operator.first_request_kind.name if operator.first_request_kind is not None else "NONE"
            result["approval_mismatch_flags"] = list(operator.mismatch_flags)
            result["approval_allow_count"] = operator.allow_count
            if approval is None:
                result["approval_result"] = "TIMEOUT"
                result["approval_wire_response_count"] = 0
            else:
                result["approval_result"] = approval.status.name
                result["approval_wire_response_count"] = int(
                    approval.status in {ApprovalHandlingStatus.ALLOWED, ApprovalHandlingStatus.DENIED}
                )

            if approval_timed_out:
                approval_stage = (
                    "P7_RECOVERY_APPROVAL_STRICT_MISMATCH"
                    if operator.request_observed
                    else "P7_RECOVERY_APPROVAL_TIMEOUT"
                )
                raise _P7Stop(approval_stage)
            if approval is None or approval.status is ApprovalHandlingStatus.RESPONSE_UNKNOWN:
                if approval is not None:
                    result["approval_result"] = "RESPONSE_UNKNOWN"
                raise _P7Stop("P7_RECOVERY_APPROVAL_RESPONSE_UNKNOWN")
            if operator.request_observed and operator.mismatch_flags:
                raise _P7Stop("P7_RECOVERY_APPROVAL_STRICT_MISMATCH")
            if approval.status is ApprovalHandlingStatus.DENIED:
                raise _P7Stop("P7_RECOVERY_APPROVAL_DENIED")
            approval_pass = (
                approval.status is ApprovalHandlingStatus.ALLOWED
                and approval.kind is ApprovalKind.COMMAND_EXECUTION
                and operator.request_count == 1
                and operator.allow_count == 1
                and not operator.mismatch_flags
                and result["approval_wire_response_count"] == 1
            )
            if not approval_pass:
                raise _P7Stop("P7_RECOVERY_APPROVAL_STRICT_MISMATCH")

            acquire_before_interrupt = counting.acquire_count
            interrupt = await turn_adapter.interrupt_turn(turn4_binding)
            result["interrupt_status"] = interrupt.status.name
            result["interrupt_terminal_status"] = (
                interrupt.terminal_result.status.name if interrupt.terminal_result is not None else "NOT_RUN"
            )
            result["interrupt_runtime_reacquire"] = "YES" if counting.acquire_count != acquire_before_interrupt else "NO"
            if (
                interrupt.status not in {TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED}
                or interrupt.terminal_result is None
                or interrupt.terminal_result.status is not TurnTerminalStatus.FAILED
            ):
                raise _P7Stop("P7_RECOVERY_INTERRUPT_AMBIGUOUS")
            if counting.acquire_count != acquire_before_interrupt:
                raise _P7Stop("P7_RECOVERY_INTERRUPT_RUNTIME_REACQUIRE")
            if sentinel_path.exists() or sentinel_path.is_symlink():
                result["recovery_sentinel_after_interrupt"] = "PRESENT"
                raise _P7Stop("P7_SENTINEL_AFTER_INTERRUPT")
            result["recovery_sentinel_after_interrupt"] = "ABSENT"
            interrupt_pass = True

            try:
                await manager.shutdown_profile("codex3")
            except Exception:
                raise _P7Stop("P7_RECOVERY_RUNTIME_CLEANUP_STOP") from None
            process_count, live_count, removed, safe = _safe_sentinel_cleanup(sentinel_path)
            delayed_process_live = live_count
            sentinel_cleanup_safe = safe
            result["recovery_delayed_process_count"] = process_count
            _require(safe and live_count == 0, "P7_RECOVERY_SENTINEL_SAFETY_STOP")

            predelete = _scan_home(home, thread_id=retained_binding.thread_id, markers=markers)
            result["predelete_scan_errors"] = predelete["scan_errors"]
            result["predelete_recovery_content_markers"] = predelete["content_marker_matches"]
            result["predelete_scan_categories"] = predelete["content_marker_matches_by_category"]
            _require(predelete["scan_errors"] == 0, "P7_RECOVERY_PREDELETE_SCAN_STOP")
            _require(predelete["content_marker_matches"] > 0, "P7_RECOVERY_PREDELETE_PROOF_INCONCLUSIVE")
            result["predelete_physical_proof"] = "PASS"

            result["thread_delete_calls"] = 1
            try:
                delete = await thread_adapter.delete(binding=retained_binding)
            except Exception:
                raise _P7Stop("P7_RECOVERY_DELETE_UNKNOWN_STOP") from None
            result["delete_status"] = delete.status.name
            _require(delete.status is ThreadOperationStatus.DELETE_CONFIRMED, "P7_RECOVERY_DELETE_UNKNOWN_STOP")
            delete_confirmed = True
            try:
                await manager.shutdown_profile("codex3")
            except Exception:
                raise _P7Stop("P7_RECOVERY_RUNTIME_CLEANUP_STOP") from None

            postdelete = _scan_home(home, thread_id=retained_binding.thread_id, markers=markers)
            result["postdelete_scan_errors"] = postdelete["scan_errors"]
            result["postdelete_recovery_content_markers"] = postdelete["content_marker_matches"]
            result["postdelete_active_thread_id_matches"] = sum(
                postdelete["thread_id_matches_by_category"][name] for name in ("SESSION_HISTORY", "STATE_DB")
            )
            result["postdelete_log_thread_id_residuals"] = postdelete["log_only_identifier_matches"]
            result["postdelete_unclassified_thread_id_residuals"] = sum(
                postdelete["thread_id_matches_by_category"][name] for name in ("CACHE", "OTHER")
            )
            _require(postdelete["scan_errors"] == 0, "P7_RECOVERY_POSTDELETE_SCAN_STOP")
            _require(postdelete["content_marker_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(result["postdelete_active_thread_id_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(result["postdelete_unclassified_thread_id_residuals"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")

            final_baseline = _home_baseline(home)
            final_owned, final_owned_errors = _session_identities_with_thread(home, retained_binding.thread_id)
            _require(final_baseline["scan_errors"] + final_owned_errors == 0, "P7_RECOVERY_POSTDELETE_SCAN_STOP")
            _require(not final_owned, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            unrelated_after = final_baseline["session_identities"] - final_owned
            unrelated_after_bytes = "\n".join(
                f"{path}\0{category}" for path, category in sorted(unrelated_after)
            ).encode("utf-8")
            after_reconciled = (
                len(unrelated_after) == original["preexisting_session_count"]
                and _sha256(unrelated_after_bytes) == original["preexisting_session_identity_sha256"]
            )
            result["original_baseline_reconciliation_after_delete"] = after_reconciled
            result["preexisting_session_artifacts_removed"] = 0
            _require(after_reconciled, "P7_UNRELATED_STORAGE_MUTATION_BLOCKER")
            postdelete_gate_pass = True
            result["status"] = "PASS"
            result["stage"] = "COMPLETE"
        except _P7Stop as stop:
            result["status"] = "BLOCKED" if stop.blocked else "FAIL"
            result["stage"] = stop.stage
        except Exception:
            result["status"] = "FAIL"
            result["stage"] = "P7_UNEXPECTED_RECOVERY_FAILURE"
        finally:
            if approval_task is not None and not approval_task.done():
                approval_task.cancel()
                await asyncio.gather(approval_task, return_exceptions=True)
            if manager is not None:
                shutdown_ok = await _shutdown_manager(manager)
            if sentinel_path is not None:
                _process_count, delayed_process_live, removed, safe = _safe_sentinel_cleanup(sentinel_path)
                sentinel_cleanup_safe = sentinel_cleanup_safe and safe
                result["recovery_sentinel_removed_or_absent"] = removed
                result["recovery_delayed_process_live"] = "NO" if delayed_process_live == 0 else "YES"
            if temp_workdir is not None:
                try:
                    shutil.rmtree(temp_workdir)
                except OSError:
                    pass
                result["recovery_temp_workdir_removed"] = not temp_workdir.exists()
            cleanup_pass = shutdown_ok and sentinel_cleanup_safe and delayed_process_live == 0 and bool(
                result["recovery_temp_workdir_removed"]
            )
            result["runtime_cleanup_pass"] = cleanup_pass
            if result["status"] == "PASS" and not cleanup_pass:
                result["status"] = "FAIL"
                result["stage"] = "P7_RECOVERY_CLEANUP_FAILED"
            if (
                result["status"] == "PASS"
                and approval_pass
                and interrupt_pass
                and delete_confirmed
                and postdelete_gate_pass
                and cleanup_pass
                and recovery_path is not None
            ):
                try:
                    recovery_path.unlink()
                    result["recovery_record_removed"] = True
                except OSError:
                    result["status"] = "FAIL"
                    result["stage"] = "P7_RECOVERY_RECORD_CLEANUP_FAILED"
            try:
                _write_result(result_path, result)
            except _P7Stop:
                result["status"] = "FAIL"
                result["stage"] = "P7_RESULT_WRITE_FAILED"

        if result["status"] != "PASS":
            self.fail(str(result["stage"]))

    async def test_authorized_final_allow_interrupt_delete(self) -> None:
        if os.environ.get("CODEXCONTROL_P7_FINAL_T3") != "AUTHORIZED_FINAL_2026_09_09":
            raise unittest.SkipTest("P7 final split continuation is not authorized")

        expected_head = os.environ.get("CODEXCONTROL_P7_EXPECTED_HEAD", "")
        expected_thread_sha = os.environ.get("CODEXCONTROL_P7_RECOVERY_THREAD_SHA256", "")
        result_value = os.environ.get("CODEXCONTROL_P7_FINAL_RESULT_PATH", "")
        result_path = Path(result_value)
        _require(
            len(expected_head) == 40
            and all(character in "0123456789abcdef" for character in expected_head)
            and expected_thread_sha == RECOVERY_THREAD_SHA256
            and result_path.is_absolute()
            and result_path.parent == Path("/var/tmp")
            and 1 <= len(result_path.name) <= 128
            and all(character in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for character in result_path.name)
            and not result_path.exists()
            and not result_path.is_symlink(),
            "P7_GATE_INVALID",
        )

        result: dict[str, Any] = {
            "status": "FAIL",
            "stage": "P7_FINAL_NOT_STARTED",
            "commit_h_sha": expected_head,
            "profile_alias": "codex3",
            "thread_id_sha256": RECOVERY_THREAD_SHA256,
            "executable_path_kind": None,
            "executable_resolved_target_safe": None,
            "model_id": None,
            "reasoning_effort": None,
            "resume_status": "NOT_RUN",
            "turn5_start_status": "NOT_RUN",
            "turn5_approval_request_observed": "NO",
            "turn5_approval_request_count": 0,
            "turn5_approval_kind": "NONE",
            "turn5_approval_thread_match": False,
            "turn5_approval_turn_match": False,
            "turn5_approval_cwd_match": False,
            "turn5_approval_marker_match": False,
            "turn5_approval_sentinel_match": False,
            "turn5_approval_grammar": "OTHER",
            "turn5_approval_mismatch_flags": [],
            "turn5_approval_allow_count": 0,
            "turn5_approval_result": "NOT_RUN",
            "turn5_approval_wire_response_count": 0,
            "turn5_terminal": "NOT_RUN",
            "turn5_sentinel_exact_content": "NOT_RUN",
            "turn5_sentinel_removed": "NO",
            "turn6_start_status": "NOT_RUN",
            "turn6_interrupt_status": "NOT_RUN",
            "turn6_interrupt_terminal": "NOT_RUN",
            "turn6_interrupt_runtime_reacquire": "NOT_RUN",
            "turn6_delayed_process_live": "UNKNOWN",
            "baseline_scan_errors": None,
            "original_baseline_reconciliation_before": False,
            "predelete_scan_errors": None,
            "predelete_new_content_markers": 0,
            "predelete_new_content_categories": {},
            "predelete_physical_proof": "NOT_RUN",
            "thread_delete_calls": 0,
            "delete_status": "NOT_RUN",
            "delete_retry": "NO",
            "postdelete_scan_errors": None,
            "postdelete_new_content_markers": None,
            "postdelete_active_thread_id_matches": None,
            "postdelete_log_thread_id_residuals": None,
            "postdelete_unclassified_thread_id_matches": None,
            "original_baseline_reconciliation_after": False,
            "preexisting_session_artifacts_removed": None,
            "recovery_record_matches": 0,
            "recovery_record_removed": "NO",
            "final_temp_workdir_removed": "NO",
            "final_p7_sentinel_removed_or_absent": "NO",
            "final_p7_child_process_live": "UNKNOWN",
            "runtime_acquire_during_interrupt": False,
        }

        class _FinalAllowOperator:
            _WRAPPERS = frozenset(("sh", "/bin/sh", "/usr/bin/sh", "bash", "/bin/bash", "/usr/bin/bash"))
            _OPTIONS = frozenset(("-c", "-lc"))

            def __init__(
                self,
                *,
                thread_id: str,
                recovery_cwd: str,
                marker: str,
                sentinel: str,
                inner_command: str,
                expected_turn_id: asyncio.Future[str],
            ) -> None:
                self._thread_id = thread_id
                self._recovery_cwd = recovery_cwd
                self._marker = marker
                self._sentinel = sentinel
                self._inner_command = inner_command
                self._expected_turn_id = expected_turn_id
                self.request_observed = False
                self.request_count = 0
                self.kind = "NONE"
                self.thread_match = False
                self.turn_match = False
                self.cwd_match = False
                self.marker_match = False
                self.sentinel_match = False
                self.grammar_class = "OTHER"
                self.mismatch_flags: tuple[str, ...] = ()
                self.allow_count = 0

            @staticmethod
            def _context_value(lines: tuple[str, ...], prefix: str) -> str | None:
                for line in lines:
                    if line.startswith(prefix):
                        return line[len(prefix):]
                return None

            def _grammar(self, requested: str | None) -> str:
                if requested is None:
                    return "OTHER"
                try:
                    observed = shlex.split(requested)
                    expected = shlex.split(self._inner_command)
                except ValueError:
                    return "OTHER"
                if observed == expected and len(observed) == 4:
                    return "EXACT_INNER"
                if len(observed) != 3 or observed[0] not in self._WRAPPERS or observed[1] not in self._OPTIONS:
                    return "OTHER"
                try:
                    script = shlex.split(observed[2])
                except ValueError:
                    return "OTHER"
                return "ONE_SHELL_WRAPPER" if script == expected and len(script) == 4 else "OTHER"

            async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
                self.request_observed = True
                self.request_count += 1
                self.kind = request.kind.name
                flags: set[str] = set()
                self.thread_match = request.thread_id == self._thread_id
                if not self.thread_match:
                    flags.add("THREAD")
                try:
                    turn_id = await asyncio.wait_for(asyncio.shield(self._expected_turn_id), timeout=30)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    turn_id = None
                self.turn_match = turn_id is not None and request.turn_id == turn_id
                if not self.turn_match:
                    flags.add("TURN")
                cwd = self._context_value(request.context_lines, "cwd: ")
                command = self._context_value(request.context_lines, "command: ")
                self.cwd_match = cwd == self._recovery_cwd
                self.marker_match = command is not None and self._marker in command
                self.sentinel_match = command is not None and self._sentinel in command
                if not self.cwd_match:
                    flags.add("CWD")
                if not self.marker_match:
                    flags.add("MARKER")
                if not self.sentinel_match:
                    flags.add("SENTINEL")
                if self.request_count != 1:
                    flags.add("REQUEST_COUNT")
                if request.kind is not ApprovalKind.COMMAND_EXECUTION:
                    flags.add("KIND")
                self.grammar_class = self._grammar(command)
                if self.grammar_class == "OTHER":
                    flags.add("GRAMMAR")
                self.mismatch_flags = tuple(sorted(flags))
                if not flags:
                    self.allow_count += 1
                    return ApprovalDecision.ALLOW
                return ApprovalDecision.DENY

        def _absent(path: Path) -> bool:
            try:
                path.lstat()
            except FileNotFoundError:
                return True
            except OSError:
                return False
            return False

        def _remove_allow_sentinel(path: Path) -> bool:
            try:
                info = path.lstat()
            except FileNotFoundError:
                return True
            except OSError:
                return False
            if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != 0:
                return False
            try:
                path.unlink()
            except OSError:
                return False
            return _absent(path)

        def _owned_turn6_processes(workdir: Path) -> list[int]:
            matches: list[int] = []
            try:
                entries = tuple(os.scandir("/proc"))
            except OSError:
                return matches
            for entry in entries:
                if not entry.name.isdigit():
                    continue
                try:
                    tokens = tuple(
                        token.decode("utf-8", errors="strict")
                        for token in Path("/proc", entry.name, "cmdline").read_bytes().split(b"\0")
                        if token
                    )
                    cwd = os.readlink(f"/proc/{entry.name}/cwd")
                except (OSError, UnicodeError):
                    continue
                has_sleep = any(os.path.basename(token) == "sleep" for token in tokens)
                if cwd == str(workdir) and has_sleep and "120" in tokens:
                    matches.append(int(entry.name))
            return matches

        def _reap_turn6_processes(workdir: Path) -> tuple[int, bool]:
            initial = _owned_turn6_processes(workdir)
            for pid in initial:
                if pid in _owned_turn6_processes(workdir):
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
            deadline = time.monotonic() + 5.0
            live = _owned_turn6_processes(workdir)
            while live and time.monotonic() < deadline:
                time.sleep(0.05)
                live = _owned_turn6_processes(workdir)
            for pid in live:
                if pid in _owned_turn6_processes(workdir):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
            deadline = time.monotonic() + 5.0
            live = _owned_turn6_processes(workdir)
            while live and time.monotonic() < deadline:
                time.sleep(0.05)
                live = _owned_turn6_processes(workdir)
            return len(live), not live

        def _exact_sentinel_content(path: Path, marker: str) -> bool:
            descriptor: int | None = None
            try:
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_size > 4096:
                    return False
                content = os.read(descriptor, 4097)
                return info.st_size == len(marker.encode("utf-8")) and content == marker.encode("utf-8")
            except OSError:
                return False
            finally:
                if descriptor is not None:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass

        manager: CodexRuntimeManager | None = None
        counting: Any | None = None
        recovery_path: Path | None = None
        recovery_record: dict[str, Any] | None = None
        temp_workdir: Path | None = None
        allow_sentinel: Path | None = None
        bridge_task: asyncio.Task[Any] | None = None
        delete_confirmed = False
        postdelete_gate_pass = False
        turn5_allow_pass = False
        turn5_sentinel_pass = False
        turn6_interrupt_pass = False
        child_cleanup_pass = False
        shutdown_ok = True
        try:
            _git_facts(expected_head)
            path_kind, resolved_target_safe = _verify_installed_authority()
            result["executable_path_kind"] = path_kind
            result["executable_resolved_target_safe"] = "PASS" if resolved_target_safe else "FAIL"
            _require(_eligible_profile_alias() == "codex3", "P7_FINAL_ISOLATION_BLOCKED", blocked=True)
            home = _safe_profile_path("codex3")
            recovery_path, recovery_record = _recovery_record_identity()
            result["recovery_record_matches"] = 1
            original = _original_result_identity()

            old_sentinel = Path(f"/var/tmp/codex-control-p7-recovery-sentinel-{recovery_record['run_nonce']}.txt")
            _old_count, old_live, old_removed, old_safe = _safe_sentinel_cleanup(old_sentinel)
            _require(old_safe and old_live == 0 and not old_sentinel.exists() and not old_sentinel.is_symlink(), "P7_FINAL_OLD_SENTINEL_STOP")

            baseline = _home_baseline(home)
            owned_before, owned_before_errors = _session_identities_with_thread(home, recovery_record["thread_id"])
            result["baseline_scan_errors"] = baseline["scan_errors"] + owned_before_errors
            _require(result["baseline_scan_errors"] == 0, "P7_FINAL_BASELINE_SCAN_STOP")
            unrelated_before = baseline["session_identities"] - owned_before
            unrelated_before_bytes = "\n".join(
                f"{path}\0{category}" for path, category in sorted(unrelated_before)
            ).encode("utf-8")
            before_reconciled = (
                len(unrelated_before) == original["preexisting_session_count"]
                and _sha256(unrelated_before_bytes) == original["preexisting_session_identity_sha256"]
            )
            result["original_baseline_reconciliation_before"] = before_reconciled
            _require(before_reconciled, "P7_FINAL_BASELINE_RECONCILIATION_STOP")

            temp_workdir = Path(tempfile.mkdtemp(prefix="codex-control-p7-final-", dir="/tmp"))
            cwd = TrustedWorkingDirectory(str(temp_workdir))
            allow_nonce = secrets.token_hex(24)
            allow_marker = secrets.token_hex(24)
            allow_prompt_marker = secrets.token_hex(24)
            interrupt_prompt_marker = secrets.token_hex(24)
            allow_sentinel = Path(f"/var/tmp/codex-control-p7-final-allow-sentinel-{allow_nonce}.txt")
            _require(_absent(allow_sentinel), "P7_FINAL_ALLOW_SENTINEL_PREEXISTING")
            inner_command = f"printf {allow_marker} > {allow_sentinel}"

            profile = CodexProfile("codex3", str(home), "P7 codex3 final continuation")
            parent_environment = dict(os.environ)
            parent_environment["CODEX_HOME"] = str(home)
            parent_environment["HOME"] = str(home)
            manager = CodexRuntimeManager(
                [profile],
                client_version=VERSION,
                executable=CODEX,
                parent_environment=parent_environment,
            )
            counting = _counting_manager(manager)
            catalog_adapter = CodexModelCatalogAdapter(counting)
            thread_adapter = CodexThreadLifecycleAdapter(counting, catalog_adapter)
            turn_adapter = CodexTurnLifecycleAdapter(counting, catalog_adapter)

            runtime = await counting.acquire("codex3")
            catalog = await catalog_adapter.get_catalog("codex3", refresh=True)
            visible_defaults = tuple(model for model in catalog.models if not model.hidden and model.is_default)
            _require(len(catalog.models) > 0 and len(visible_defaults) == 1, "P7_FINAL_CATALOG_INVALID")
            model = visible_defaults[0]
            effort = model.default_reasoning_effort
            _require(effort in model.supported_reasoning_efforts, "P7_FINAL_CATALOG_INVALID")
            result["model_id"] = model.model_id
            result["reasoning_effort"] = effort

            retained_binding = ThreadBinding("codex3", recovery_record["thread_id"])
            resumed = await thread_adapter.resume(binding=retained_binding, working_directory=cwd)
            _require(
                resumed.status is ThreadOperationStatus.RESUME_CONFIRMED and resumed.binding is retained_binding,
                "P7_FINAL_RESUME_FAILED",
            )
            result["resume_status"] = resumed.status.name

            expected_turn_id = asyncio.get_running_loop().create_future()
            operator = _FinalAllowOperator(
                thread_id=retained_binding.thread_id,
                recovery_cwd=str(temp_workdir),
                marker=allow_marker,
                sentinel=str(allow_sentinel),
                inner_command=inner_command,
                expected_turn_id=expected_turn_id,
            )
            live_runtime = counting.last_runtime
            _require(live_runtime is not None and live_runtime.generation == runtime.generation, "P7_FINAL_RUNTIME_OWNERSHIP_STOP")
            bridge = CodexApprovalBridge(profile_id="codex3", client=live_runtime.client, operator=operator)
            bridge_task = asyncio.create_task(bridge.handle_next())
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            _require(not bridge_task.done(), "P7_FINAL_APPROVAL_ARM_STOP")

            turn5_start = await turn_adapter.start_turn(
                thread_binding=retained_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=(
                    f"Use the command-execution tool and execute exactly this supplied inner shell action once: {inner_command}. "
                    f"The ordinary prompt marker is {allow_prompt_marker}. Do not simulate, explain, substitute, "
                    "prepend, append, or request another operation. Because the target is outside the workspace, "
                    "request operator approval rather than choosing an alternative."
                ),
                working_directory=cwd,
            )
            result["turn5_start_status"] = turn5_start.status.name
            _require(
                turn5_start.status is TurnStartStatus.CONFIRMED and turn5_start.binding is not None,
                "P7_FINAL_TURN5_START_FAILED",
            )
            turn5_binding = turn5_start.binding
            _require(not expected_turn_id.done(), "P7_FINAL_TURN5_ID_PUBLICATION_STOP")
            expected_turn_id.set_result(turn5_binding.turn_id)

            approval: Any | None = None
            try:
                approval = await asyncio.wait_for(asyncio.shield(bridge_task), timeout=90)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                if not bridge_task.done():
                    bridge_task.cancel()
                    await asyncio.gather(bridge_task, return_exceptions=True)
            except Exception:
                approval_failed_unknown = True
                approval = None
            result["turn5_approval_request_observed"] = "YES" if operator.request_observed else "NO"
            result["turn5_approval_request_count"] = operator.request_count
            result["turn5_approval_kind"] = operator.kind
            result["turn5_approval_thread_match"] = operator.thread_match
            result["turn5_approval_turn_match"] = operator.turn_match
            result["turn5_approval_cwd_match"] = operator.cwd_match
            result["turn5_approval_marker_match"] = operator.marker_match
            result["turn5_approval_sentinel_match"] = operator.sentinel_match
            result["turn5_approval_grammar"] = operator.grammar_class
            result["turn5_approval_mismatch_flags"] = list(operator.mismatch_flags)
            result["turn5_approval_allow_count"] = operator.allow_count
            if approval is None:
                result["turn5_approval_result"] = "RESPONSE_UNKNOWN" if approval_failed_unknown else "TIMEOUT"
                result["turn5_approval_wire_response_count"] = 0
            else:
                result["turn5_approval_result"] = approval.status.name
                result["turn5_approval_wire_response_count"] = int(
                    approval.status in {ApprovalHandlingStatus.ALLOWED, ApprovalHandlingStatus.DENIED}
                )
            _require(
                result["turn5_approval_request_observed"] == "YES"
                and result["turn5_approval_request_count"] == 1
                and result["turn5_approval_kind"] == "COMMAND_EXECUTION"
                and not result["turn5_approval_mismatch_flags"]
                and result["turn5_approval_allow_count"] == 1
                and result["turn5_approval_result"] == "ALLOWED"
                and result["turn5_approval_wire_response_count"] == 1,
                "P7_FINAL_ALLOW_GRAMMAR_MISMATCH",
            )
            turn5_allow_pass = True

            turn5_terminal = await turn_adapter.wait_turn(turn5_binding)
            result["turn5_terminal"] = turn5_terminal.status.name
            _require(turn5_terminal.status is TurnTerminalStatus.COMPLETED, "P7_FINAL_TURN5_TERMINAL_STOP")
            _require(_exact_sentinel_content(allow_sentinel, allow_marker), "P7_FINAL_ALLOW_SENTINEL_STOP")
            result["turn5_sentinel_exact_content"] = "PASS"
            _require(_remove_allow_sentinel(allow_sentinel), "P7_FINAL_ALLOW_SENTINEL_STOP")
            result["turn5_sentinel_removed"] = "YES"
            turn5_sentinel_pass = True

            turn6_start = await turn_adapter.start_turn(
                thread_binding=retained_binding,
                model_id=model.model_id,
                reasoning_effort=effort,
                user_text=(
                    f"Use the command-execution tool and execute exactly this inner command once: sleep 120. "
                    f"The ordinary interrupt prompt marker is {interrupt_prompt_marker}. Do not simulate, "
                    "explain, substitute, or add another operation."
                ),
                working_directory=cwd,
            )
            result["turn6_start_status"] = turn6_start.status.name
            _require(
                turn6_start.status is TurnStartStatus.CONFIRMED and turn6_start.binding is not None,
                "P7_FINAL_TURN6_START_FAILED",
            )
            turn6_binding = turn6_start.binding
            acquire_before_interrupt = counting.acquire_count
            interrupt = await turn_adapter.interrupt_turn(turn6_binding)
            result["turn6_interrupt_status"] = interrupt.status.name
            result["turn6_interrupt_terminal"] = (
                interrupt.terminal_result.status.name if interrupt.terminal_result is not None else "NOT_RUN"
            )
            result["turn6_interrupt_runtime_reacquire"] = "YES" if counting.acquire_count != acquire_before_interrupt else "NO"
            _require(
                interrupt.status in {TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED}
                and interrupt.terminal_result is not None
                and interrupt.terminal_result.status is TurnTerminalStatus.FAILED
                and counting.acquire_count == acquire_before_interrupt,
                "P7_FINAL_INTERRUPT_STOP",
            )
            turn6_interrupt_pass = True

            await manager.shutdown_profile("codex3")
            delayed_live, delayed_safe = _reap_turn6_processes(temp_workdir)
            result["turn6_delayed_process_live"] = "NO" if delayed_live == 0 else "YES"
            result["final_p7_child_process_live"] = "NO" if delayed_live == 0 else "YES"
            _require(delayed_safe and delayed_live == 0, "P7_FINAL_DELAYED_PROCESS_STOP")
            child_cleanup_pass = True

            final_markers = (allow_marker, allow_prompt_marker, interrupt_prompt_marker)
            predelete = _scan_home(home, thread_id=retained_binding.thread_id, markers=final_markers)
            result["predelete_scan_errors"] = predelete["scan_errors"]
            result["predelete_new_content_markers"] = predelete["content_marker_matches"]
            result["predelete_new_content_categories"] = predelete["content_marker_matches_by_category"]
            _require(predelete["scan_errors"] == 0, "P7_FINAL_PREDELETE_SCAN_STOP")
            _require(predelete["content_marker_matches"] > 0, "P7_FINAL_PREDELETE_PROOF_INCONCLUSIVE")
            result["predelete_physical_proof"] = "PASS"

            result["thread_delete_calls"] = 1
            try:
                delete = await thread_adapter.delete(binding=retained_binding)
            except Exception:
                result["delete_status"] = "DELETE_UNKNOWN"
                raise _P7Stop("P7_FINAL_DELETE_UNKNOWN_STOP") from None
            result["delete_status"] = delete.status.name
            _require(delete.status is ThreadOperationStatus.DELETE_CONFIRMED, "P7_FINAL_DELETE_UNKNOWN_STOP")
            delete_confirmed = True
            await manager.shutdown_profile("codex3")

            postdelete = _scan_home(home, thread_id=retained_binding.thread_id, markers=final_markers)
            result["postdelete_scan_errors"] = postdelete["scan_errors"]
            result["postdelete_new_content_markers"] = postdelete["content_marker_matches"]
            result["postdelete_active_thread_id_matches"] = sum(
                postdelete["thread_id_matches_by_category"][name] for name in ("SESSION_HISTORY", "STATE_DB")
            )
            result["postdelete_log_thread_id_residuals"] = postdelete["log_only_identifier_matches"]
            result["postdelete_unclassified_thread_id_matches"] = sum(
                postdelete["thread_id_matches_by_category"][name] for name in ("CACHE", "OTHER")
            )
            _require(postdelete["scan_errors"] == 0, "P7_FINAL_POSTDELETE_SCAN_STOP")
            _require(postdelete["content_marker_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(
                all(postdelete["thread_id_matches_by_category"][name] == 0 for name in ("SESSION_HISTORY", "STATE_DB", "CACHE", "OTHER")),
                "P7_HARD_DELETE_RESIDUAL_BLOCKER",
            )
            _require(result["postdelete_active_thread_id_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(result["postdelete_unclassified_thread_id_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")

            final_baseline = _home_baseline(home)
            final_owned, final_owned_errors = _session_identities_with_thread(home, retained_binding.thread_id)
            _require(final_baseline["scan_errors"] + final_owned_errors == 0, "P7_FINAL_POSTDELETE_SCAN_STOP")
            _require(not final_owned, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            final_identity_bytes = "\n".join(
                f"{path}\0{category}" for path, category in sorted(final_baseline["session_identities"])
            ).encode("utf-8")
            original_preserved = (
                len(final_baseline["session_identities"]) == original["preexisting_session_count"]
                and _sha256(final_identity_bytes) == original["preexisting_session_identity_sha256"]
            )
            result["original_baseline_reconciliation_after"] = original_preserved
            result["preexisting_session_artifacts_removed"] = 0
            _require(original_preserved, "P7_UNRELATED_STORAGE_MUTATION_BLOCKER")
            _require(result["preexisting_session_artifacts_removed"] == 0, "P7_UNRELATED_STORAGE_MUTATION_BLOCKER")
            postdelete_gate_pass = True
            result["status"] = "PASS"
            result["stage"] = "COMPLETE"
        except _P7Stop as stop:
            result["status"] = "BLOCKED" if stop.blocked else "FAIL"
            result["stage"] = stop.stage
        except Exception:
            result["status"] = "FAIL"
            result["stage"] = "P7_FINAL_UNEXPECTED_FAILURE"
        finally:
            if bridge_task is not None and not bridge_task.done():
                bridge_task.cancel()
                await asyncio.gather(bridge_task, return_exceptions=True)
            if manager is not None:
                shutdown_ok = await _shutdown_manager(manager)
            if allow_sentinel is not None:
                if result["turn5_sentinel_removed"] != "YES":
                    result["turn5_sentinel_removed"] = "YES" if _remove_allow_sentinel(allow_sentinel) else "NO"
                result["final_p7_sentinel_removed_or_absent"] = "YES" if _absent(allow_sentinel) else "NO"
            if temp_workdir is not None:
                delayed_live, delayed_safe = _reap_turn6_processes(temp_workdir)
                result["final_p7_child_process_live"] = "NO" if delayed_live == 0 else "YES"
                child_cleanup_pass = child_cleanup_pass and delayed_safe and delayed_live == 0
                try:
                    shutil.rmtree(temp_workdir)
                except OSError:
                    pass
                result["final_temp_workdir_removed"] = "YES" if not temp_workdir.exists() else "NO"
            cleanup_pass = (
                shutdown_ok
                and child_cleanup_pass
                and result["final_p7_child_process_live"] == "NO"
                and result["final_p7_sentinel_removed_or_absent"] == "YES"
                and result["final_temp_workdir_removed"] == "YES"
            )
            if result["status"] == "PASS" and not cleanup_pass:
                result["status"] = "FAIL"
                result["stage"] = "P7_FINAL_CLEANUP_FAILED"
            if (
                result["status"] == "PASS"
                and turn5_allow_pass
                and turn5_sentinel_pass
                and turn6_interrupt_pass
                and delete_confirmed
                and postdelete_gate_pass
                and cleanup_pass
                and recovery_path is not None
            ):
                try:
                    recovery_path.unlink()
                    result["recovery_record_removed"] = "YES"
                except OSError:
                    result["status"] = "FAIL"
                    result["stage"] = "P7_FINAL_RECOVERY_CLEANUP_FAILED"
            try:
                _write_result(result_path, result)
            except _P7Stop:
                result["status"] = "FAIL"
                result["stage"] = "P7_FINAL_RESULT_WRITE_FAILED"

        if result["status"] != "PASS":
            self.fail(str(result["stage"]))


if __name__ == "__main__" and "--isolation-preflight" in sys.argv:
    print(f"ELIGIBLE_PROFILE={_eligible_profile_alias() or 'P7_ISOLATION_GATE_BLOCKED'}")
