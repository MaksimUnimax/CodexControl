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
import shutil
import stat
import subprocess
import sys
import tempfile
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
PROFILE_HOMES = {
    "codex3": "/root/.codex_third",
    "codex2": "/root/.codex_second",
}
CATEGORIES = ("SESSION_HISTORY", "STATE_DB", "LOG", "CACHE", "OTHER")
CONTENT_MARKER = "content_marker"
THREAD_ID = "thread_id"


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


def _path_is_under(path: str, root: Path) -> bool:
    try:
        return os.path.commonpath((os.path.abspath(path), str(root))) == str(root)
    except (OSError, ValueError):
        return False


def _codex_process_owns_candidate(pid: int, candidate: Path) -> bool:
    """Return true for ownership or ambiguity, without exposing /proc data."""
    try:
        executable = os.path.basename(os.readlink(f"/proc/{pid}/exe")).lower()
    except OSError:
        return False
    try:
        command_line = Path(f"/proc/{pid}/cmdline").read_bytes()
        command_tokens = tuple(
            token.decode("utf-8", errors="strict")
            for token in command_line.split(b"\0")
            if token
        )
    except (OSError, UnicodeDecodeError):
        return True if executable in {"codex", "codex-cli"} else False
    invoked_codex = executable in {"codex", "codex-cli"} or any(
        os.path.basename(token) in {"codex", "codex-cli"}
        for token in command_tokens
    )
    if not invoked_codex:
        return False
    environment = _proc_environment(pid)
    if environment is None:
        return True
    home = environment.get("CODEX_HOME")
    if home == str(candidate):
        return True
    if home is None:
        # An unqualified Codex process is the excluded default profile, not
        # evidence that either named non-default candidate is in use.
        return str(candidate) == "/root/.codex"
    if not os.path.isabs(home):
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


def _home_baseline(home: Path) -> dict[str, Any]:
    identities: set[tuple[str, str]] = set()
    regular_count = 0
    total_bytes = 0
    for root, directories, files in os.walk(home, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in files:
            path = Path(root) / name
            info = _is_regular(path)
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
    }


def _scan_file(path: Path, needles: tuple[tuple[str, bytes], ...]) -> tuple[dict[str, int], int, int]:
    counts = {name: 0 for name, _ in needles}
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return counts, 0, 0
    total_bytes = 0
    hit_bytes = 0
    overlap = b""
    offset = 0
    maximum = max((len(needle) for _, needle in needles), default=1)
    try:
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
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
        return {name: 0 for name, _ in needles}, 0, 0
    if any(counts.values()):
        hit_bytes = total_bytes
    return counts, hit_bytes, total_bytes


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
    for root, directories, files in os.walk(home, followlinks=False):
        directories[:] = [name for name in directories if not (Path(root) / name).is_symlink()]
        for name in files:
            path = Path(root) / name
            info = _is_regular(path)
            if info is None:
                continue
            relative = path.relative_to(home)
            category = _category(relative)
            counts, matched_bytes, _ = _scan_file(path, needles)
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
    }


def _isolated_environment(home: Path) -> dict[str, str]:
    return {
        "CODEX_HOME": str(home),
        "HOME": str(home),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
    }


def _verify_installed_authority() -> None:
    executable = Path(CODEX)
    try:
        info = executable.lstat()
    except OSError:
        raise _P7Stop("P7_INSTALLED_AUTHORITY_DRIFT_STOP") from None
    _require(stat.S_ISREG(info.st_mode) and os.access(executable, os.X_OK), "P7_INSTALLED_AUTHORITY_DRIFT_STOP")
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
            "thread_id_sha256": None,
            "marker_sha256": [],
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
            _verify_installed_authority()
            selected = _eligible_profile_alias()
            _require(selected == alias, "P7_ISOLATION_GATE_BLOCKED", blocked=True)
            home = _safe_profile_path(selected)
            baseline = _home_baseline(home)
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
            _require(
                turn2_terminal.status is TurnTerminalStatus.COMPLETED
                and bool(turn2_terminal.messages)
                and any(m1 in message.text and a2 in message.text for message in turn2_terminal.messages),
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
            active_thread_residuals = sum(postdelete["thread_id_matches_by_category"][name] for name in ("SESSION_HISTORY", "STATE_DB"))
            unclassified_residuals = sum(postdelete["thread_id_matches_by_category"][name] for name in ("CACHE", "OTHER"))
            _require(postdelete["content_marker_matches"] == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            _require(active_thread_residuals == 0 and unclassified_residuals == 0, "P7_HARD_DELETE_RESIDUAL_BLOCKER")
            result["postdelete_active_thread_id_matches"] = active_thread_residuals
            result["postdelete_log_identifier_residuals"] = postdelete["log_only_identifier_matches"]
            result["postdelete_unclassified_residuals"] = unclassified_residuals
            result["postdelete_content_marker_matches"] = postdelete["content_marker_matches"]

            final_baseline = _home_baseline(home)
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


if __name__ == "__main__" and "--isolation-preflight" in sys.argv:
    print(f"ELIGIBLE_PROFILE={_eligible_profile_alias() or 'P7_ISOLATION_GATE_BLOCKED'}")
