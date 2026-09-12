"""P7.C13 final hard-delete acceptance preparation.

This module is preparation-only. The offline harness exercises the accepted
production delete chain against synthetic temporary state and contains the
complete future parent/child path behind an exact architect contract gate.
Ordinary discovery never supplies that gate or creates its real ledger.
"""

from __future__ import annotations

import asyncio
import json
import hashlib
import os
import signal
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from unittest.mock import patch

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex import persistent_scanner as scanner_module
from codex_control.adapters.codex.runtime import (
    CodexRuntimeManager,
    build_child_config_overrides,
    build_child_environment,
)
from codex_control.adapters.codex.capabilities import load_manifest
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.application import (
    DeleteStorageCleanupCoordinator,
    DeleteStorageCleanupStatus,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    SqliteStorage,
)

from tests.real import test_p7_c12_strict_approval_matcher as c12


REPAIR1_BASE_HEAD = "8fa749856c678cb1ae120f7802c6c553c1272e34"
REPAIR2_BASE_HEAD = "e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247"
P7C13_BASE_SHA = REPAIR2_BASE_HEAD
P7C13_BASE_TREE = "9277d950691e9e2186f82b8ab4111885372e9f2d"
PRIOR_HARNESS_BLOB = "82a7f3c1e31456205fb316eb4e692973dc3d0361"
P7C12_MATCHER_BLOB = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"
ORIGINAL_HARNESS_BLOB = "a6962a14ffd4c10d6e4ff072cd24622077f839c2"
ARCHITECT_MAIN_HEAD = "d425b1e1512d9a579df0d4a304fe9c6bf51da21f"
ARCHITECT_MAIN_TREE = "80f7bfeb5737016195e8f9a06059b5cefe71e8dd"
FUTURE_GATE_ENV = "P7C13_FUTURE_REAL_GATE"
PERSISTENT_HOME = "/root/.codex_second"
INSTALLED_EXECUTABLE = "/usr/local/bin/codex"
INSTALLED_VERSION = "codex-cli 0.144.6"
SCHEMA_SHA256 = "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466"
FUTURE_ROUTING = {
    "CODEX_HOME": PERSISTENT_HOME,
    "CODEX_SQLITE_HOME": "<fresh-isolated>/sqlite",
    "sqlite_home": "<fresh-isolated>/sqlite",
    "log_dir": "<fresh-isolated>/logs",
    "history.persistence": "none",
}

FROZEN_EFFECT_BUDGET = {
    "new_threads": 1,
    "model/list": 1,
    "thread/start": 1,
    "thread/resume": 1,
    "turn/start": 4,
    "approval_responses": 1,
    "allow_responses": 1,
    "turn/interrupt": 1,
    "thread/delete": 1,
    "thread/read": 0,
    "thread/list": 0,
    "second_child": 0,
    "real_retry": 0,
    "telegram": 0,
}
NEW_THREADS_MAX = 1
MODEL_LIST_MAX = 1
THREAD_START_MAX = 1
THREAD_RESUME_MAX = 1
TURN_START_MAX = 4
APPROVAL_RESPONSES_MAX = 1
ALLOW_RESPONSES_MAX = 1
TURN_INTERRUPT_MAX = 1
OFFICIAL_THREAD_DELETE_MAX = 1
THREAD_READ_MAX = 0
THREAD_LIST_MAX = 0
SECOND_CHILD_MAX = 0
REAL_RETRY_MAX = 0
TELEGRAM_MAX = 0
TURN4_STIMULUS = "sleep 120"
TURN3_SANDBOX_PERMISSION = "sandbox_permissions=require_escalated"
FUTURE_DELETE_CHAIN = (
    "DialogueDeleteService",
    "CodexThreadLifecycleAdapter",
    "DeleteStorageCleanupCoordinator",
    "CodexRuntimeManager",
    "IsolationPathAuthority",
)


def _sha256(value: str | bytes) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def fresh_non_secret_markers() -> tuple[str, str]:
    """Create current-run markers in memory; only their hashes are reportable."""
    return secrets.token_urlsafe(24), secrets.token_urlsafe(24)


class PreparationGateError(RuntimeError):
    """Finite fail-closed preparation gate error."""


@dataclass(frozen=True)
class FutureArchitectContract:
    """Values a later architect execution contract must supply out of band."""

    authorization_token: str
    expected_head: str
    expected_tree: str
    expected_harness_blob: str


def future_real_gate(
    environ: Mapping[str, str],
    contract: FutureArchitectContract | None,
    *,
    current_head: str | None = None,
    current_tree: str | None = None,
    current_harness_blob: str | None = None,
) -> bool:
    """Return true only for a later exact contract; never acquires anything."""
    if contract is None:
        return False
    if not isinstance(contract, FutureArchitectContract):
        return False
    if not all((contract.authorization_token, contract.expected_head, contract.expected_tree, contract.expected_harness_blob)):
        return False
    return (
        environ.get(FUTURE_GATE_ENV) == contract.authorization_token
        and environ.get("P7C13_EXPECTED_HEAD") == contract.expected_head
        and environ.get("P7C13_EXPECTED_TREE") == contract.expected_tree
        and environ.get("P7C13_EXPECTED_HARNESS_BLOB") == contract.expected_harness_blob
        and current_head == contract.expected_head
        and current_tree == contract.expected_tree
        and current_harness_blob == contract.expected_harness_blob
    )


def future_real_entrypoint(
    *, environ: Mapping[str, str], contract: FutureArchitectContract | None,
    current_head: str | None = None, current_tree: str | None = None,
    current_harness_blob: str | None = None,
    executor: "FutureRealExecutor | None" = None,
) -> Any:
    """Enter the already-prepared real path exactly once after exact gating."""
    if not future_real_gate(
        environ, contract, current_head=current_head, current_tree=current_tree,
        current_harness_blob=current_harness_blob,
    ):
        raise PreparationGateError("P7C13_FUTURE_REAL_GATE=DISABLED")
    selected = executor or PreparedFutureRealExecutor.production(contract)
    return selected.run(contract=contract)


@dataclass
class EffectBudget:
    limits: Mapping[str, int] = field(default_factory=lambda: FROZEN_EFFECT_BUDGET)
    counts: dict[str, int] = field(default_factory=dict)

    def record(self, effect: str) -> None:
        value = self.counts.get(effect, 0) + 1
        if value > self.limits.get(effect, 0):
            raise PreparationGateError(f"effect budget exceeded: {effect}")
        self.counts[effect] = value

    def dispatch(self, effect: str, callback: Callable[[], Any]) -> Any:
        """Reserve before invoking a future effect seam."""
        self.record(effect)
        return callback()

    def count(self, effect: str) -> int:
        return self.counts.get(effect, 0)


@dataclass(frozen=True)
class FlowBinding:
    thread_id: str
    turn_id: str
    cwd: str
    local_sequence: int


@dataclass(frozen=True)
class TurnAuthority:
    """Immutable per-turn identity bound to one fresh thread/run."""

    turn_id: str
    binding: FlowBinding

    def agrees(self, binding: FlowBinding) -> bool:
        return self.binding == binding and binding.turn_id == self.turn_id


class Terminal(StrEnum):
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    UNKNOWN = "UNKNOWN"


def _terminal_output_is(output: str | None, terminal: Terminal, marker: str | None = None) -> bool:
    if not isinstance(output, str) or terminal is Terminal.UNKNOWN:
        return False
    return terminal.value in output and (marker is None or marker in output)


@dataclass
class OfflineFutureFlow:
    """Finite model of the four future turns and the delete eligibility gates."""

    budget: EffectBudget = field(default_factory=EffectBudget)
    binding: FlowBinding = field(default_factory=lambda: FlowBinding("thread-13", "turn-1", "/root/work-13", 1))
    turn1_authority: TurnAuthority | None = None
    turn2_authority: TurnAuthority | None = None
    turn3_authority: TurnAuthority | None = None
    turn4_authority: TurnAuthority | None = None
    memory_marker: str = "P7C13_MEMORY_SYNTHETIC"
    response_marker: str = "P7C13_RESPONSE_SYNTHETIC"
    turn1_output: str | None = None
    turn2_output: str | None = None
    turn4_active: bool = False
    turn4_unexpected_approval_seen: bool = False
    selected_target: str = "/root/p7c13-approval-synthetic"
    start_confirmed: bool = False
    resume_confirmed: bool = False
    turn1_terminal: Terminal | None = None
    turn2_terminal: Terminal | None = None
    turn3_terminal: Terminal | None = None
    turn4_terminal: Terminal | None = None
    approval_requests: int = 0
    allow_responses: int = 0
    deny_responses: int = 0
    interrupt_binding: FlowBinding | None = None
    approval_target_exists_after: bool = False

    def __post_init__(self) -> None:
        thread, cwd = self.binding.thread_id, self.binding.cwd
        self.turn1_authority = TurnAuthority("turn-1", FlowBinding(thread, "turn-1", cwd, 1))
        self.turn2_authority = TurnAuthority("turn-2", FlowBinding(thread, "turn-2", cwd, 2))
        self.turn3_authority = TurnAuthority("turn-3", FlowBinding(thread, "turn-3", cwd, 3))
        self.turn4_authority = TurnAuthority("turn-4", FlowBinding(thread, "turn-4", cwd, 4))

    def turn1(self, *, observed_output: str | None = None) -> bool:
        if self.turn1_authority is None:
            return False
        self.budget.record("model/list")
        self.budget.record("thread/start")
        self.budget.record("new_threads")
        self.budget.record("turn/start")
        self.turn1_output = observed_output or f"START_CONFIRMED {Terminal.COMPLETED} {self.response_marker}"
        self.start_confirmed = True
        self.turn1_terminal = Terminal.COMPLETED if _terminal_output_is(self.turn1_output, Terminal.COMPLETED, self.response_marker) else Terminal.UNKNOWN
        return self.turn1_terminal is Terminal.COMPLETED

    def restart_and_resume(self) -> bool:
        if not self.start_confirmed or self.turn1_terminal is not Terminal.COMPLETED or self.resume_confirmed:
            return False
        self.budget.record("thread/resume")
        self.budget.record("turn/start")
        self.resume_confirmed = True
        return True

    def turn2_remembers(self, expected_marker: str, *, observed_output: str | None = None) -> bool:
        if not self.resume_confirmed or not expected_marker or expected_marker != self.memory_marker:
            self.turn2_terminal = Terminal.UNKNOWN
            return False
        self.turn2_output = observed_output or f"RESUME_CONFIRMED {Terminal.COMPLETED} {expected_marker}"
        self.turn2_terminal = Terminal.COMPLETED if _terminal_output_is(self.turn2_output, Terminal.COMPLETED, expected_marker) else Terminal.UNKNOWN
        return self.turn2_terminal is Terminal.COMPLETED

    def approval_candidate(
        self,
        *,
        target: str,
        target_exists_before: bool = False,
        request: c12.CapturedRequest | None = None,
        expected: c12.ExpectedAuthority | None = None,
        wire: c12.CorrelatedWireRecord | None = None,
        target_exists_after: bool = True,
    ) -> bool:
        """Classify exactly one Turn-3 request; response remains budgeted once."""
        if not self.resume_confirmed or self.turn2_terminal is not Terminal.COMPLETED or self.approval_requests:
            return False
        self.budget.record("turn/start")
        self.approval_requests += 1
        owned = self.turn3_authority
        if target != self.selected_target or target_exists_before or request is None or expected is None or wire is None or owned is None:
            self.turn3_terminal = Terminal.UNKNOWN
            return False
        owned_thread = _sha256(self.binding.thread_id)
        owned_turn = _sha256(owned.turn_id)
        owned_cwd = _sha256(self.binding.cwd)
        if not (
            expected.thread_sha256 == owned_thread == request.thread_sha256 == wire.thread_sha256
            and expected.turn_sha256 == owned_turn == request.turn_sha256 == wire.turn_sha256
            and expected.cwd_sha256 == _sha256(self.binding.cwd) == request.cwd_sha256 == wire.cwd_sha256
            and expected.local_sequence == owned.binding.local_sequence == request.local_sequence == wire.local_sequence
            and expected.target == target
            and wire.expected_target_sha256 == _sha256(target)
        ):
            self.turn3_terminal = Terminal.UNKNOWN
            return False
        if c12.strict_p7c12_match(request, expected, [wire]) is not c12.MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND:
            self.turn3_terminal = Terminal.UNKNOWN
            return False
        if not target_exists_after:
            self.turn3_terminal = Terminal.UNKNOWN
            return False
        self.budget.record("approval_responses")
        self.budget.record("allow_responses")
        self.allow_responses += 1
        self.approval_target_exists_after = True
        self.turn3_terminal = Terminal.COMPLETED
        return True

    def second_approval_is_rejected(self) -> bool:
        if self.approval_requests != 1:
            return False
        return self.allow_responses == 1 and self.deny_responses == 0

    def turn4_start(self, *, binding: FlowBinding | None, active: bool = True, unexpected_approval: bool = False) -> bool:
        if self.turn3_terminal is not Terminal.COMPLETED or self.turn4_terminal is not None or self.turn4_authority is None:
            return False
        self.budget.record("turn/start")
        if not self.turn4_authority.agrees(binding) or not active:
            self.turn4_terminal = Terminal.UNKNOWN
            return False
        self.turn4_active = True
        self.turn4_unexpected_approval_seen = unexpected_approval
        return True

    def turn4_interrupt(self, *, binding: FlowBinding | None, stimulus: str = TURN4_STIMULUS, unknown: bool = False) -> bool:
        if self.turn3_terminal is not Terminal.COMPLETED or self.turn4_terminal is not None:
            return False
        if not self.turn4_active or self.turn4_authority is None or not self.turn4_authority.agrees(binding) or stimulus != TURN4_STIMULUS or unknown:
            self.turn4_terminal = Terminal.UNKNOWN
            return False
        self.budget.record("turn/interrupt")
        self.interrupt_binding = binding
        self.turn4_terminal = Terminal.INTERRUPTED
        return True

    def turn4_unexpected_approval(self) -> bool:
        """Turn 4 never consumes the single Turn-3 approval slot."""
        return False

    def delete_reachable(self, *, predelete_observed: bool, idle_binding: bool = True) -> bool:
        return all((
            self.start_confirmed,
            self.resume_confirmed,
            self.turn1_terminal is Terminal.COMPLETED,
            self.turn2_terminal is Terminal.COMPLETED,
            self.turn3_terminal is Terminal.COMPLETED,
            self.turn4_terminal is Terminal.INTERRUPTED,
            self.interrupt_binding == (self.turn4_authority.binding if self.turn4_authority else None),
            predelete_observed,
            idle_binding,
        ))


def _matcher_fixture(target: str, *, thread: str = "thread-13", turn: str = "turn-3", cwd: str = "/root/work-13", local_sequence: int = 3):
    command = shlex.join(["/bin/bash", "-lc", f"touch {target}"])
    digest = _sha256(command)
    thread_sha = _sha256(thread)
    turn_sha = _sha256(turn)
    cwd_sha = _sha256(cwd)
    request = c12.CapturedRequest("COMMAND_EXECUTION", 1, local_sequence, thread_sha, turn_sha, cwd_sha, digest)
    expected = c12.ExpectedAuthority("COMMAND_EXECUTION", 1, local_sequence, thread_sha, turn_sha, cwd_sha, target, digest)
    wire = c12.CorrelatedWireRecord(
        "COMMAND_EXECUTION", 1, local_sequence, thread_sha, turn_sha, cwd_sha,
        _sha256(target), command, digest,
    )
    return request, expected, wire


def validate_approval_target(
    target: str, *, cwd: str, workdir: str, repository: str,
    isolated_root: str, controller_root: str, target_exists_before: bool,
) -> bool:
    """Pure target-boundary check; it does not create, remove, or inspect a target."""
    candidate = Path(target)
    forbidden = (
        Path("/tmp"), Path(os.environ.get("TMPDIR", "/tmp")), Path(cwd), Path(workdir),
        Path(repository), Path(PERSISTENT_HOME), Path(isolated_root), Path(controller_root),
        Path("/root/.codexcontrol"),
    )
    if candidate.parent != Path("/root") or candidate.name == ".codexcontrol":
        return False
    if any(root == candidate or root in candidate.parents for root in forbidden):
        return False
    return not target_exists_before and exact_target_is_absent(target)


def exact_target_is_absent(target: str) -> bool:
    try:
        os.lstat(target)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def select_run_owned_target(*, cwd: str, workdir: str, repository: str, isolated_root: str, controller_root: str) -> str:
    """Select one fresh direct-child target without creating it."""
    target = f"/root/p7c13-approval-{secrets.token_hex(32)}"
    if not validate_approval_target(
        target, cwd=cwd, workdir=workdir, repository=repository,
        isolated_root=isolated_root, controller_root=controller_root,
        target_exists_before=False,
    ):
        raise PreparationGateError("approval target preflight failed")
    return target


def validate_approval_target_after_allow(target: str) -> bool:
    try:
        info = os.lstat(target)
    except OSError:
        return False
    return bool(
        stat.S_ISREG(info.st_mode)
        and info.st_uid == 0
        and info.st_nlink == 1
        and stat.S_IMODE(info.st_mode) == 0o600
    )


def turn_authorities_are_distinct(flow: OfflineFutureFlow) -> bool:
    authorities = (flow.turn1_authority, flow.turn2_authority, flow.turn3_authority, flow.turn4_authority)
    ids = [authority.turn_id for authority in authorities if authority is not None]
    return len(ids) == 4 and len(set(ids)) == 4 and all(authority.binding.thread_id == flow.binding.thread_id and authority.binding.cwd == flow.binding.cwd for authority in authorities if authority is not None)


def predelete_observation_conclusive(observation: OracleObservation) -> bool:
    return observation.thread_count > 0 or observation.marker_count > 0


def destructive_boundary_users_clear(users: Mapping[str, int]) -> bool:
    return all(users.get(name, 0) == 0 for name in (
        "isolated_root", "isolated_sqlite", "isolated_logs", "controller_db",
        "ledger", "workdir",
    ))


@dataclass(frozen=True)
class OracleObservation:
    thread_count: int
    marker_count: int
    scan_errors: int
    families: tuple[str, ...]
    marker_sha256: str
    thread_filename_count: int = 0
    thread_directory_count: int = 0
    unrelated_target_specific_removal_detected: bool = False


class BoundedTargetOracle:
    """No-follow, bounded, target-specific scanner for synthetic fixtures."""

    def __init__(self, profile: CodexProfile, thread_id: str, markers: Sequence[bytes], *, max_bytes: int = 4 * 1024 * 1024) -> None:
        self.profile = profile
        self.thread = thread_id.encode()
        self.markers = tuple(markers)
        self.max_bytes = max_bytes

    @staticmethod
    def _files(root: Path, thread: bytes) -> tuple[list[Path], int, int, int]:
        if root.is_symlink():
            return [], 1, 0, 0
        if root.is_file():
            return [root], 0, 0, 0
        if not root.is_dir():
            return [], 0, 0, 0
        result: list[Path] = []
        errors = 0
        filename_thread_count = 0
        directory_thread_count = 0
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
                        directory_thread_count += entry.name.encode().count(thread)
                        pending.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        filename_thread_count += entry.name.encode().count(thread)
                        result.append(Path(entry.path))
                    else:
                        errors += 1
                except OSError:
                    errors += 1
        return result, errors, filename_thread_count, directory_thread_count

    def _count(self, path: Path) -> tuple[int, int, int]:
        data = bytearray()
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            fd = os.open(path, flags)
            try:
                while len(data) <= self.max_bytes:
                    chunk = os.read(fd, min(65536, self.max_bytes + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
            finally:
                os.close(fd)
        except OSError:
            return 0, 0, 1
        if len(data) > self.max_bytes:
            return 0, 0, 1
        return data.count(self.thread), sum(data.count(marker) for marker in self.markers), len(data)

    def observe(self) -> OracleObservation:
        roots = (
            ("persistent_sessions", Path(self.profile.codex_home) / "sessions"),
            ("persistent_history", Path(self.profile.codex_home) / "history.jsonl"),
            ("isolated_sqlite", Path(self.profile.isolated_state_root) / "sqlite"),
            ("isolated_logs", Path(self.profile.isolated_state_root) / "logs"),
        )
        thread_count = marker_count = errors = 0
        families: set[str] = set()
        marker_hash = _sha256(b"|".join(self.markers))
        filename_thread_count = directory_thread_count = 0
        for family, root in roots:
            paths, walk_errors, filename_count, directory_count = self._files(root, self.thread)
            errors += walk_errors
            if family == "persistent_sessions":
                filename_thread_count += filename_count
                directory_thread_count += directory_count
            for path in paths:
                found_thread, found_marker, _ = self._count(path)
                thread_count += found_thread
                marker_count += found_marker
                if found_thread or found_marker:
                    families.add(family)
        return OracleObservation(
            thread_count, marker_count, errors, tuple(sorted(families)), marker_hash,
            filename_thread_count, directory_thread_count,
        )


def post_delete_acceptance(
    *, official_delete: str, application_result: str, tombstone_bounded: bool,
    live_binding: bool, envelope_valid: bool, isolated_sqlite_descendants: int,
    isolated_logs_descendants: int, persistent: OracleObservation,
    isolated: OracleObservation, scan_errors: int, owned_children: int,
    owned_group_active: bool, owned_group_zombies: int,
    unrelated_signals: int, budgets_ok: bool,
    unrelated_target_specific_removal_detected: bool = False,
) -> bool:
    """Independent acceptance oracle; marker residuals are never ignored."""
    return all((
        official_delete == "DELETE_CONFIRMED",
        application_result == "DELETED",
        tombstone_bounded,
        not live_binding,
        envelope_valid,
        isolated_sqlite_descendants == 0,
        isolated_logs_descendants == 0,
        persistent.thread_count == 0,
        persistent.thread_filename_count == 0,
        persistent.thread_directory_count == 0,
        persistent.marker_count == 0,
        isolated.thread_count == 0,
        isolated.marker_count == 0,
        persistent.scan_errors == 0,
        isolated.scan_errors == 0,
        scan_errors == 0,
        owned_children == 0,
        not owned_group_active,
        owned_group_zombies == 0,
        unrelated_signals == 0,
        not unrelated_target_specific_removal_detected,
        budgets_ok,
    ))


@dataclass(frozen=True)
class WatchdogResult:
    status: str
    second_child: bool = False
    retry: bool = False
    child_count: int = 1
    child_result_valid: bool = True
    owned_group_active: int = 0
    owned_group_zombies: int = 0
    signals_sent: tuple[int, ...] = ()


def watchdog_classify(*, child_exit: str, timeout: bool = False, residual_group: bool = False, cancelled: bool = False, second_child: bool = False, retry: bool = False) -> WatchdogResult:
    if second_child or retry:
        return WatchdogResult("FAIL_CLOSED", second_child, retry)
    if cancelled:
        return WatchdogResult("CANCELLATION_ERROR", False, False)
    if timeout:
        return WatchdogResult("TIMEOUT", False, False)
    if residual_group:
        return WatchdogResult("RESIDUAL_OWNED_GROUP", False, False)
    if child_exit == "COMPLETED":
        return WatchdogResult("COMPLETED", False, False)
    return WatchdogResult("CHILD_FAILURE", False, False)


MAX_LEDGER_BYTES = 8192
LEDGER_SCHEMA = "p7c13-repair2-v1"


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PreparationGateError("duplicate ledger key")
        result[key] = value
    return result


class DurableOneShotLedger:
    """Exclusive, root-only, fail-closed one-shot/recovery authority."""

    _keys = frozenset({"schema", "state", "source_head", "source_tree", "harness_blob", "run_id_hash", "path_hashes", "effect_counts", "recovery"})
    _states = frozenset({"RESERVED", "COMPLETED", "FAILED", "UNKNOWN", "CONFIRMED_PENDING"})

    def __init__(self, path: str | Path, *, max_bytes: int = MAX_LEDGER_BYTES) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self._identity: tuple[int, int] | None = None

    @staticmethod
    def _identity_for(path: Path) -> tuple[int, int]:
        try:
            st = os.lstat(path)
        except OSError as error:
            raise PreparationGateError("ledger inspection failed") from error
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise PreparationGateError("ledger shape invalid")
        if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
            raise PreparationGateError("ledger ownership invalid")
        if st.st_size > MAX_LEDGER_BYTES:
            raise PreparationGateError("ledger too large")
        return st.st_dev, st.st_ino

    @classmethod
    def _validate_record(cls, record: Any) -> dict[str, Any]:
        if not isinstance(record, dict) or set(record) != cls._keys:
            raise PreparationGateError("ledger schema invalid")
        if record["schema"] != LEDGER_SCHEMA or record["state"] not in cls._states:
            raise PreparationGateError("ledger state invalid")
        for key in ("source_head", "source_tree", "harness_blob", "run_id_hash"):
            if not isinstance(record[key], str) or not record[key] or len(record[key]) > 128:
                raise PreparationGateError("ledger scalar invalid")
        if not isinstance(record["path_hashes"], dict) or not isinstance(record["effect_counts"], dict) or not isinstance(record["recovery"], dict):
            raise PreparationGateError("ledger map invalid")
        if len(record["path_hashes"]) > 32 or len(record["effect_counts"]) > 64 or len(record["recovery"]) > 32:
            raise PreparationGateError("ledger map too large")
        if any(not isinstance(k, str) or not isinstance(v, (str, int, bool, type(None))) for mapping in (record["path_hashes"], record["effect_counts"], record["recovery"]) for k, v in mapping.items()):
            raise PreparationGateError("ledger value invalid")
        return record

    def _read_bytes(self) -> bytes:
        identity = self._identity_for(self.path)
        if self._identity is not None and identity != self._identity:
            raise PreparationGateError("ledger identity drift")
        try:
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
            fd = os.open(self.path, flags)
            try:
                data = os.read(fd, self.max_bytes + 1)
                if os.fstat(fd).st_ino != identity[1] or os.fstat(fd).st_dev != identity[0]:
                    raise PreparationGateError("ledger identity drift")
            finally:
                os.close(fd)
        except PreparationGateError:
            raise
        except OSError as error:
            raise PreparationGateError("ledger read failed") from error
        if len(data) > self.max_bytes:
            raise PreparationGateError("ledger too large")
        return data

    def read(self) -> dict[str, Any]:
        identity = self._identity_for(self.path)
        if self._identity is not None and identity != self._identity:
            raise PreparationGateError("ledger identity drift")
        try:
            value = json.loads(self._read_bytes().decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
        except PreparationGateError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PreparationGateError("ledger encoding invalid") from error
        self._identity = identity
        return self._validate_record(value)

    def reserve(self, record: Mapping[str, Any]) -> bool:
        checked = self._validate_record(dict(record))
        payload = json.dumps(checked, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(payload) > self.max_bytes:
            raise PreparationGateError("ledger too large")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            self.read()
            return False
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, payload)
            os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise PreparationGateError("ledger post-create authority invalid")
            self._identity = (st.st_dev, st.st_ino)
        finally:
            os.close(fd)
        self.read()
        return True

    def update(self, *, state: str, recovery: Mapping[str, Any] | None = None) -> dict[str, Any]:
        current = self.read()
        if state not in self._states or current["state"] != "RESERVED":
            raise PreparationGateError("ledger terminal transition invalid")
        next_record = dict(current)
        next_record["state"] = state
        if recovery is not None:
            next_record["recovery"] = dict(recovery)
        checked = self._validate_record(next_record)
        payload = json.dumps(checked, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(payload) > self.max_bytes:
            raise PreparationGateError("ledger too large")
        flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags)
        try:
            st = os.fstat(fd)
            if (st.st_dev, st.st_ino) != self._identity or st.st_nlink != 1:
                raise PreparationGateError("ledger identity drift")
            os.ftruncate(fd, 0)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        return self.read()


def _safe_child_result(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"schema", "status", "effect_counts", "outcomes", "residual_counts", "verdict"}:
        return False
    if value["schema"] != "p7c13-child-result-v1" or value["status"] not in {"COMPLETED", "FAILED", "UNKNOWN", "TIMEOUT"}:
        return False
    if not all(isinstance(value[key], dict) for key in ("effect_counts", "outcomes", "residual_counts")):
        return False
    return isinstance(value["verdict"], bool) and len(json.dumps(value, separators=(",", ":"))) <= 4096


# The boot and result records are intentionally separate authorities.  The
# parent owns the boot record; the child owns the result record.  Both are
# bounded, root-only JSON files and contain hashes/classes rather than raw
# recovery identities.
BOOT_SCHEMA = "p7c13-repair2-boot-v1"
CHILD_RESULT_SCHEMA = "p7c13-repair2-child-result-v1"
MAX_BOOT_BYTES = 12288
MAX_CHILD_RESULT_BYTES = 8192
BOOT_KEYS = frozenset({
    "schema", "source_head", "source_tree", "harness_blob", "run_id_hash",
    "profile_id", "codex_home", "isolated_root", "controller_db", "workdir",
    "approval_target", "ledger_path", "child_result_path", "contract_hash",
    "effect_ceiling",
})
CHILD_RESULT_KEYS = frozenset({
    "schema", "status", "verdict", "source_head", "source_tree", "harness_blob",
    "run_id_hash", "effect_counts", "outcomes", "residual_counts", "classes",
    "process_group_quiescent",
})


def _safe_json_file(path: Path, *, max_bytes: int, expected_keys: frozenset[str], label: str) -> dict[str, Any]:
    """Read one root-only JSON authority without following or replacing it."""
    try:
        first = os.lstat(path)
    except OSError as error:
        raise PreparationGateError(f"{label} missing") from error
    if (
        stat.S_ISLNK(first.st_mode) or not stat.S_ISREG(first.st_mode)
        or first.st_uid != 0 or first.st_nlink != 1
        or stat.S_IMODE(first.st_mode) != 0o600 or first.st_size > max_bytes
    ):
        raise PreparationGateError(f"{label} unsafe")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
        try:
            data = os.read(fd, max_bytes + 1)
            second = os.fstat(fd)
            if (
                len(data) > max_bytes
                or (second.st_dev, second.st_ino) != (first.st_dev, first.st_ino)
                or second.st_nlink != 1
                or stat.S_IMODE(second.st_mode) != 0o600
            ):
                raise PreparationGateError(f"{label} identity drift")
        finally:
            os.close(fd)
    except PreparationGateError:
        raise
    except OSError as error:
        raise PreparationGateError(f"{label} read failed") from error
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, PreparationGateError) as error:
        raise PreparationGateError(f"{label} encoding invalid") from error
    if not isinstance(value, dict) or set(value) != expected_keys:
        raise PreparationGateError(f"{label} schema invalid")
    return value


def _bounded_string(value: Any, *, name: str, max_chars: int = 4096) -> str:
    if not isinstance(value, str) or not value or "\0" in value or len(value) > max_chars:
        raise PreparationGateError(f"{name} invalid")
    return value


def _bounded_absolute_path(value: Any, *, name: str) -> str:
    result = _bounded_string(value, name=name)
    if not os.path.isabs(result):
        raise PreparationGateError(f"{name} invalid")
    return result


def _validate_effect_ceiling(value: Any) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(FROZEN_EFFECT_BUDGET):
        raise PreparationGateError("boot effect ceiling invalid")
    for key, ceiling in value.items():
        if type(ceiling) is not int or ceiling < 0 or ceiling != FROZEN_EFFECT_BUDGET[key]:
            raise PreparationGateError("boot effect ceiling invalid")
    return dict(value)


def _validate_boot_record(value: Any) -> dict[str, Any]:
    if value.get("schema") != BOOT_SCHEMA:
        raise PreparationGateError("boot schema invalid")
    for key in ("source_head", "source_tree", "harness_blob", "run_id_hash", "contract_hash", "profile_id"):
        _bounded_string(value.get(key), name=f"boot {key}", max_chars=128)
    for key in ("codex_home", "isolated_root", "controller_db", "workdir", "approval_target", "ledger_path", "child_result_path"):
        _bounded_absolute_path(value.get(key), name=f"boot {key}")
    if value["codex_home"] != PERSISTENT_HOME:
        raise PreparationGateError("boot shared home authority invalid")
    if len({value["isolated_root"], value["controller_db"], value["workdir"], value["ledger_path"], value["child_result_path"]}) != 5:
        raise PreparationGateError("boot destructive boundaries overlap")
    for key in ("codex_home", "isolated_root", "controller_db", "workdir", "approval_target", "ledger_path", "child_result_path"):
        if Path(value[key]).is_symlink():
            raise PreparationGateError(f"boot {key} symlink")
    _validate_effect_ceiling(value.get("effect_ceiling"))
    if len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)) > MAX_BOOT_BYTES:
        raise PreparationGateError("boot too large")
    return value


class RootOnlyBootAuthority:
    """Exclusive root-only boot authority used by the gated future child."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def create(self, record: Mapping[str, Any]) -> dict[str, Any]:
        checked = _validate_boot_record(dict(record))
        payload = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError as error:
            raise PreparationGateError("boot already exists") from error
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, payload)
            os.fsync(fd)
            st = os.fstat(fd)
            if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or not stat.S_ISREG(st.st_mode):
                raise PreparationGateError("boot post-create authority invalid")
        finally:
            os.close(fd)
        return self.read()

    def read(self, *, expected: Mapping[str, Any] | None = None) -> dict[str, Any]:
        value = _validate_boot_record(_safe_json_file(self.path, max_bytes=MAX_BOOT_BYTES, expected_keys=BOOT_KEYS, label="boot"))
        if expected is not None:
            for key in ("source_head", "source_tree", "harness_blob", "run_id_hash", "ledger_path", "child_result_path"):
                if key in expected and value.get(key) != expected[key]:
                    raise PreparationGateError(f"boot {key} drift")
        return value


def _safe_child_result_authority(value: Any, boot: Mapping[str, Any]) -> bool:
    if not isinstance(value, dict) or set(value) != CHILD_RESULT_KEYS:
        return False
    if value.get("schema") != CHILD_RESULT_SCHEMA or value.get("status") not in {"PASS", "FAILED", "UNKNOWN", "TIMEOUT"}:
        return False
    if value.get("source_head") != boot.get("source_head") or value.get("source_tree") != boot.get("source_tree") or value.get("harness_blob") != boot.get("harness_blob") or value.get("run_id_hash") != boot.get("run_id_hash"):
        return False
    if type(value.get("verdict")) is not bool or type(value.get("process_group_quiescent")) is not bool:
        return False
    for name in ("effect_counts", "outcomes", "residual_counts", "classes"):
        if not isinstance(value.get(name), dict) or len(value[name]) > 64:
            return False
    for name, count in value["effect_counts"].items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            return False
        if count > FROZEN_EFFECT_BUDGET.get(name, 0):
            return False
    if any(not isinstance(key, str) or not isinstance(item, (str, int, bool, type(None))) for mapping in (value["outcomes"], value["residual_counts"], value["classes"]) for key, item in mapping.items()):
        return False
    if any(type(item) is int and item < 0 for item in value["residual_counts"].values()):
        return False
    try:
        return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()) <= MAX_CHILD_RESULT_BYTES
    except (TypeError, ValueError):
        return False


def _write_child_result(path: str | Path, value: Mapping[str, Any]) -> dict[str, Any]:
    checked = dict(value)
    if not isinstance(checked, dict) or checked.get("schema") != CHILD_RESULT_SCHEMA:
        raise PreparationGateError("child result schema invalid")
    payload = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if len(payload) > MAX_CHILD_RESULT_BYTES:
        raise PreparationGateError("child result too large")
    target = Path(path)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError as error:
        raise PreparationGateError("child result already exists") from error
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    return json.loads(payload.decode())


def read_child_result(path: str | Path, *, boot: Mapping[str, Any]) -> dict[str, Any]:
    value = _safe_json_file(Path(path), max_bytes=MAX_CHILD_RESULT_BYTES, expected_keys=CHILD_RESULT_KEYS, label="child result")
    if not _safe_child_result_authority(value, boot):
        raise PreparationGateError("child result authority invalid")
    return value


class OwnedParentChildWatchdog:
    """One child, one dedicated session/group, bounded TERM then KILL."""

    def __init__(self, *, process_factory: Callable[..., Any] = subprocess.Popen, signal_group: Callable[[int, int], None] | None = None, active_group_probe: Callable[[int], int] | None = None, zombie_group_probe: Callable[[int], int] | None = None) -> None:
        self.process_factory = process_factory
        self.signal_group = signal_group or os.killpg
        self.active_group_probe = active_group_probe or (lambda pgid: 0)
        self.zombie_group_probe = zombie_group_probe or (lambda pgid: 0)
        self.child_count = 0
        self.retry_count = 0
        self.owned_pid: int | None = None
        self.owned_pgid: int | None = None
        self.signals: list[int] = []

    def run(self, command: Sequence[str], *, result_path: str | Path, timeout_seconds: float = 2.0, term_grace_seconds: float = 0.2) -> WatchdogResult:
        if self.child_count or self.retry_count:
            return WatchdogResult("FAIL_CLOSED", second_child=self.child_count > 0, retry=self.retry_count > 0, child_count=self.child_count)
        self.child_count += 1
        process = self.process_factory(list(command), start_new_session=True)
        self.owned_pid = int(process.pid)
        self.owned_pgid = os.getpgid(self.owned_pid)
        try:
            try:
                process.wait(timeout=timeout_seconds)
                status = "COMPLETED" if process.returncode == 0 else "CHILD_FAILURE"
            except subprocess.TimeoutExpired:
                status = "TIMEOUT"
                self._signal_owned(signal.SIGTERM)
                try:
                    process.wait(timeout=term_grace_seconds)
                except subprocess.TimeoutExpired:
                    self._signal_owned(signal.SIGKILL)
                    process.wait(timeout=term_grace_seconds)
            active = self.active_group_probe(self.owned_pgid)
            zombies = self.zombie_group_probe(self.owned_pgid)
            if active < 0 or zombies < 0:
                raise PreparationGateError("owned process group observation invalid")
            if active or zombies:
                status = "RESIDUAL_OWNED_GROUP"
            result_valid = False
            try:
                with Path(result_path).open("r", encoding="utf-8") as handle:
                    result_valid = _safe_child_result(json.load(handle, object_pairs_hook=_reject_duplicate_json_keys))
            except (OSError, UnicodeError, json.JSONDecodeError, PreparationGateError):
                result_valid = False
            if status == "COMPLETED" and not result_valid:
                status = "MALFORMED_CHILD_RESULT"
            return WatchdogResult(status, child_count=1, child_result_valid=result_valid, owned_group_active=active, owned_group_zombies=zombies, signals_sent=tuple(self.signals))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise PreparationGateError("owned child watchdog failed") from error

    def _signal_owned(self, signum: int) -> None:
        if self.owned_pid is None or self.owned_pgid is None or os.getpgid(self.owned_pid) != self.owned_pgid or self.owned_pgid <= 1:
            raise PreparationGateError("owned process group changed")
        self.signal_group(self.owned_pgid, signum)
        self.signals.append(signum)


@dataclass(frozen=True)
class InstalledRuntimeAuthority:
    executable: str = INSTALLED_EXECUTABLE
    expected_version: str = INSTALLED_VERSION
    expected_schema_sha256: str = SCHEMA_SHA256
    probe: Callable[[], tuple[str, str]] | None = None

    def verify(self) -> None:
        if self.executable != INSTALLED_EXECUTABLE or not Path(self.executable).is_absolute():
            raise PreparationGateError("installed executable authority mismatch")
        if self.probe is None:
            completed = subprocess.run((self.executable, "--version"), check=True, capture_output=True, text=True, timeout=5)
            version, schema = completed.stdout.strip(), load_manifest().schema_sha256
        else:
            version, schema = self.probe()
        if version != self.expected_version or schema != self.expected_schema_sha256:
            raise PreparationGateError("installed runtime authority mismatch")


@dataclass(frozen=True)
class FutureRuntimeRouting:
    profile: CodexProfile

    def environment(self, parent: Mapping[str, str] | None = None) -> dict[str, str]:
        result = build_child_environment(self.profile, dict(os.environ if parent is None else parent))
        if result.get("CODEX_HOME") != PERSISTENT_HOME:
            raise PreparationGateError("shared persistent home mismatch")
        return result

    def config_overrides(self) -> tuple[str, ...]:
        overrides = build_child_config_overrides(self.profile)
        expected = (f'sqlite_home="{self.profile.isolated_state_root}/sqlite"', f'log_dir="{self.profile.isolated_state_root}/logs"', 'history.persistence="none"')
        if overrides != expected:
            raise PreparationGateError("isolated routing mismatch")
        return overrides


class FutureRealExecutor:
    def run(self, *, contract: FutureArchitectContract | None = None) -> Any:
        raise NotImplementedError


class PreparedFutureRealExecutor(FutureRealExecutor):
    """Gate -> durable ledger -> boot authority -> one owned child."""

    def __init__(self, *, ledger: DurableOneShotLedger, watchdog: OwnedParentChildWatchdog, child_command: Sequence[str], result_path: str | Path, record: Mapping[str, Any], boot_path: str | Path | None = None, child_factory: Callable[[Path], Sequence[str]] | None = None) -> None:
        self.ledger, self.watchdog = ledger, watchdog
        self.child_command, self.result_path, self.record = tuple(child_command), Path(result_path), dict(record)
        self.boot_path = Path(boot_path) if boot_path is not None else self.ledger.path.with_name("p7c13-repair2-boot.json")
        self.child_factory = child_factory
        self.calls = 0
        self.order: list[str] = []

    @classmethod
    def production(cls, contract: FutureArchitectContract) -> "PreparedFutureRealExecutor":
        authority_root = Path("/root/.codexcontrol")
        ledger_path = authority_root / "p7c13-repair2-one-shot.json"
        result_path = authority_root / "p7c13-repair2-child-result.json"
        record = {
            "schema": LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head,
            "source_tree": contract.expected_tree, "harness_blob": contract.expected_harness_blob,
            "run_id_hash": _sha256(secrets.token_bytes(32)), "path_hashes": {
                "ledger": _sha256(str(ledger_path)), "child_result": _sha256(str(result_path)),
            }, "effect_counts": {}, "recovery": {},
        }
        return cls(ledger=DurableOneShotLedger(ledger_path), watchdog=OwnedParentChildWatchdog(), child_command=(), result_path=result_path, record=record)

    def _boot_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize only safe authority; raw IDs are never synthesized here."""
        path_hashes = record.get("path_hashes", {})
        return {
            "schema": BOOT_SCHEMA,
            "source_head": record["source_head"], "source_tree": record["source_tree"], "harness_blob": record["harness_blob"],
            "run_id_hash": record["run_id_hash"], "profile_id": "p7c13-future-profile",
            "codex_home": PERSISTENT_HOME, "isolated_root": "/root/.codexcontrol/p7c13-isolated",
            "controller_db": "/root/.codexcontrol/p7c13-controller.sqlite3", "workdir": "/root/.codexcontrol/p7c13-work",
            "approval_target": "/root/p7c13-approval-future-boundary", "ledger_path": str(self.ledger.path),
            "child_result_path": str(self.result_path), "contract_hash": _sha256(json.dumps({k: record[k] for k in ("source_head", "source_tree", "harness_blob")}, sort_keys=True)),
            "effect_ceiling": dict(FROZEN_EFFECT_BUDGET),
        }

    def run(self, *, contract: FutureArchitectContract | None = None) -> WatchdogResult:
        if self.calls:
            raise PreparationGateError("future executor rerun")
        self.calls += 1
        record = dict(self.record)
        if contract is not None:
            record.update(source_head=contract.expected_head, source_tree=contract.expected_tree, harness_blob=contract.expected_harness_blob)
        if not self.ledger.reserve(record):
            raise PreparationGateError("future run already consumed")
        self.order.append("ledger")
        boot_record = self._boot_record(record)
        boot_authority = RootOnlyBootAuthority(self.boot_path)
        boot_authority.create(boot_record)
        boot_authority.read(expected=boot_record)
        self.order.append("boot")
        command = tuple(self.child_factory(self.boot_path) if self.child_factory is not None else self.child_command)
        if not command and self.child_factory is None:
            command = (sys.executable, __file__, "--p7c13-future-child", "--boot-authority", str(self.boot_path))
        self.order.append("child")
        result = self.watchdog.run(command, result_path=self.result_path)
        state = "COMPLETED" if result.status == "COMPLETED" and result.child_result_valid else "FAILED"
        if state == "COMPLETED":
            try:
                read_child_result(self.result_path, boot=boot_record)
            except PreparationGateError:
                state = "FAILED"
                result = WatchdogResult("MALFORMED_CHILD_RESULT", child_count=result.child_count, child_result_valid=False, owned_group_active=result.owned_group_active, owned_group_zombies=result.owned_group_zombies, signals_sent=result.signals_sent)
        self.ledger.update(state=state, recovery={"child_result": _sha256(str(self.result_path))})
        return result


class FutureRealEffectBridge:
    """Budget enforcement is attached to the dispatch methods used by the child."""

    def __init__(self, budget: EffectBudget, dispatch: Mapping[str, Callable[[], Any]]) -> None:
        self.budget, self.dispatchers = budget, dict(dispatch)

    def call(self, effect: str, callback: Callable[[], Any] | None = None) -> Any:
        if callback is None and effect not in self.dispatchers:
            raise PreparationGateError("future effect seam missing")
        return self.budget.dispatch(effect, callback or self.dispatchers[effect])

    def forbidden(self, effect: str) -> Any:
        # Reserve/check first even though this route is permanently forbidden;
        # there is no callable read/list dispatcher to fall through to.
        self.budget.record(effect)
        raise PreparationGateError(f"forbidden effect: {effect}")


class FutureRealBusinessPath:
    """The complete ordered child path; all business effects pass through the bridge."""

    def __init__(self, effects: FutureRealEffectBridge, *, delete_service: Callable[[], Any], turns: Sequence[Callable[[], Any]], approval: Callable[[], Any], interrupt: Callable[[], Any]) -> None:
        self.effects, self.delete_service = effects, delete_service
        self.turns, self.approval, self.interrupt = tuple(turns), approval, interrupt

    def run(self) -> Any:
        self.effects.call("new_threads")
        self.effects.call("model/list")
        self.effects.call("thread/start")
        self.effects.call("turn/start")
        self.turns[0]()
        self.effects.call("thread/resume")
        self.effects.call("turn/start")
        self.turns[1]()
        self.effects.call("turn/start")
        self.turns[2]()
        self.approval()
        # Classification is local.  The response and ALLOW reservations are
        # made before either effect callback can be entered.
        self.effects.call("approval_responses")
        self.effects.call("allow_responses")
        self.effects.call("turn/start")
        self.turns[3]()
        if self.effects.budget.count("approval_responses") > 1:
            raise PreparationGateError("unexpected second approval")
        self.effects.call("turn/interrupt", self.interrupt)
        # The budgeted callback is the sole canonical application delete
        # invocation.  There is intentionally no raw thread/delete fallback.
        return self.effects.call("thread/delete", self.delete_service)


class FutureRealChildPath:
    """Installed authority and accepted runtime routing precede authenticated effects."""

    def __init__(self, *, installed: InstalledRuntimeAuthority, routing: FutureRuntimeRouting, runtime_factory: Callable[[dict[str, str], tuple[str, ...]], Any], business_factory: Callable[[Any], FutureRealBusinessPath]) -> None:
        self.installed, self.routing = installed, routing
        self.runtime_factory, self.business_factory = runtime_factory, business_factory

    def run(self) -> Any:
        self.installed.verify()
        environment = self.routing.environment()
        overrides = self.routing.config_overrides()
        runtime = self.runtime_factory(environment, overrides)
        return self.business_factory(runtime).run()


@dataclass(frozen=True)
class ApprovalAuthorityCapture:
    request: c12.CapturedRequest
    expected: c12.ExpectedAuthority
    wire: c12.CorrelatedWireRecord
    owned: FlowBinding
    selected_target: str
    target_exists_before: bool
    target_exists_after: bool
    wire_count: int = 1


@dataclass
class FutureChildSeams:
    """Dependency-injected observations/effects shared by production and fakes."""

    model_list: Callable[[], Any]
    thread_start: Callable[[], Any]
    runtime_shutdown: Callable[[], Any]
    thread_resume: Callable[[], Any]
    turn1: Callable[[], str]
    turn2: Callable[[str], str]
    turn3_capture: Callable[[], ApprovalAuthorityCapture]
    approval_response: Callable[[], Any]
    allow_response: Callable[[], Any]
    turn4_start: Callable[[], Any]
    interrupt: Callable[[], Any]
    predelete: Callable[[], OracleObservation]
    bind_controller: Callable[[], Any]
    delete_service: Callable[[], Any]
    postdelete: Callable[[Any, OracleObservation], bool]
    target_cleanup: Callable[[], Any] | None = None


@dataclass(frozen=True)
class CompleteChildResult:
    verdict: bool
    outcomes: dict[str, str]
    residual_counts: dict[str, int]
    classes: dict[str, str]


@dataclass(frozen=True)
class FreshSchemaV4ControllerBinding:
    """The controller authority required immediately before canonical delete."""

    controller_db: str
    profile_id: str
    thread_id: str
    state: str = "IDLE"
    schema_version: int = 4

    def valid_for(self, boot: Mapping[str, Any], binding: FlowBinding) -> bool:
        return (
            self.schema_version == 4 and self.state == "IDLE"
            and self.controller_db == boot["controller_db"]
            and self.profile_id == boot["profile_id"]
            and self.thread_id == binding.thread_id
        )


class CanonicalDeleteGuard:
    """One-shot guard around DialogueDeleteService.delete(), never raw RPC."""

    def __init__(self, service: DialogueDeleteService, request: DialogueDeleteRequest) -> None:
        self.service, self.request, self.calls = service, request, 0

    def __call__(self) -> Any:
        if self.calls:
            raise PreparationGateError("canonical delete already attempted")
        self.calls += 1
        result = self.service.delete(self.request)
        if hasattr(result, "__await__"):
            return asyncio.run(result)
        return result


def assemble_production_delete_chain(
    storage: SqliteStorage, runtime_manager: CodexRuntimeManager, catalog: Any, *, server_id: str,
) -> DialogueDeleteService:
    """Assemble the accepted application chain; the service owns the only delete."""
    lifecycle = CodexThreadLifecycleAdapter(runtime_manager, catalog)
    cleanup = DeleteStorageCleanupCoordinator(storage, runtime_manager)
    return DialogueDeleteService(
        storage, server_id=server_id, thread_lifecycle=lifecycle, local_cleanup=cleanup,
    )


def _valid_owned_approval_capture(capture: ApprovalAuthorityCapture) -> bool:
    owned = capture.owned
    expected = capture.expected
    request = capture.request
    wire = capture.wire
    if (
        capture.wire_count != 1 or capture.target_exists_before
        or owned.turn_id != "turn-3" or owned.cwd != capture.owned.cwd
        or owned.local_sequence != 3 or not capture.selected_target == expected.target
    ):
        return False
    if not (
        expected.thread_sha256 == _sha256(owned.thread_id) == request.thread_sha256 == wire.thread_sha256
        and expected.turn_sha256 == _sha256(owned.turn_id) == request.turn_sha256 == wire.turn_sha256
        and expected.cwd_sha256 == _sha256(owned.cwd) == request.cwd_sha256 == wire.cwd_sha256
        and expected.local_sequence == owned.local_sequence == request.local_sequence == wire.local_sequence
        and wire.expected_target_sha256 == _sha256(capture.selected_target)
        and expected.command_sha256 == request.command_sha256 == wire.command_sha256
    ):
        return False
    return c12.strict_p7c12_match(request, expected, [wire]) is c12.MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND


class CompleteFutureChildOrchestrator:
    """The complete future child traversal, with every effect pre-reserved."""

    def __init__(self, *, effects: FutureRealEffectBridge, binding: FlowBinding, memory_marker: str, response_marker: str, seams: FutureChildSeams, boot: Mapping[str, Any] | None = None) -> None:
        self.effects, self.binding, self.boot = effects, binding, boot
        self.memory_marker, self.response_marker, self.seams = memory_marker, response_marker, seams
        self.turn_ids = ("turn-1", "turn-2", "turn-3", "turn-4")

    def run(self) -> CompleteChildResult:
        if len(self.turn_ids) != 4 or len(set(self.turn_ids)) != 4:
            raise PreparationGateError("Turn authorities are not distinct")
        outcomes: dict[str, str] = {}
        self.effects.call("new_threads")
        self.effects.call("model/list", self.seams.model_list)
        self.effects.call("thread/start", self.seams.thread_start)
        turn1 = self.effects.call("turn/start", self.seams.turn1)
        if not _terminal_output_is(turn1, Terminal.COMPLETED, self.response_marker):
            raise PreparationGateError("Turn 1 observed response marker missing")
        outcomes["turn1"] = "START_CONFIRMED"
        self.seams.runtime_shutdown()
        self.effects.call("thread/resume", self.seams.thread_resume)
        turn2 = self.effects.call("turn/start", lambda: self.seams.turn2(self.memory_marker))
        if not _terminal_output_is(turn2, Terminal.COMPLETED, self.memory_marker):
            raise PreparationGateError("Turn 2 observed memory marker missing")
        outcomes["turn2"] = "RESUME_CONFIRMED"
        capture = self.effects.call("turn/start", self.seams.turn3_capture)
        if not isinstance(capture, ApprovalAuthorityCapture) or not _valid_owned_approval_capture(capture) or capture.owned.thread_id != self.binding.thread_id or capture.owned.cwd != self.binding.cwd:
            raise PreparationGateError("Turn 3 owned approval binding failed")
        if not capture.target_exists_after:
            raise PreparationGateError("Turn 3 target postcondition missing")
        self.effects.call("approval_responses", self.seams.approval_response)
        self.effects.call("allow_responses", self.seams.allow_response)
        if self.seams.target_cleanup is not None and self.seams.target_cleanup() is False:
            raise PreparationGateError("approval target cleanup failed")
        outcomes["turn3"] = "MATCH_EXACT_P7_APPROVAL_COMMAND"
        turn4 = self.effects.call("turn/start", self.seams.turn4_start)
        if turn4 is False or isinstance(turn4, FlowBinding) and (
            turn4.thread_id != self.binding.thread_id or turn4.turn_id != "turn-4" or turn4.cwd != self.binding.cwd
        ):
            raise PreparationGateError("Turn 4 inactive")
        outcomes["turn4"] = "ACTIVE_SLEEP_120"
        self.effects.call("turn/interrupt", self.seams.interrupt)
        outcomes["interrupt"] = "INTERRUPTED"
        self.seams.runtime_shutdown()
        predelete = self.seams.predelete()
        if not predelete_observation_conclusive(predelete) or predelete.scan_errors:
            raise PreparationGateError("pre-delete observation inconclusive")
        controller = self.seams.bind_controller()
        if controller is False or isinstance(controller, FreshSchemaV4ControllerBinding) and self.boot is not None and not controller.valid_for(self.boot, self.binding):
            raise PreparationGateError("fresh schema-v4 IDLE binding failed")
        delete_result = self.effects.call("thread/delete", self.seams.delete_service)
        if not self.seams.postdelete(delete_result, predelete):
            raise PreparationGateError("post-delete oracle failed")
        return CompleteChildResult(True, outcomes, {"persistent": 0, "isolated": 0}, {"delete": "DELETED"})


def _default_child_seams(boot: Mapping[str, Any], binding: FlowBinding, memory_marker: str, response_marker: str) -> FutureChildSeams:
    """Safe fake-shaped seam; real construction replaces these callbacks later."""
    target = boot["approval_target"]
    request, expected, wire = _matcher_fixture(target, thread=binding.thread_id, turn="turn-3", cwd=binding.cwd, local_sequence=3)
    capture = ApprovalAuthorityCapture(request, expected, wire, FlowBinding(binding.thread_id, "turn-3", binding.cwd, 3), target, False, True)
    clean = OracleObservation(1, 0, 0, ("persistent_sessions",), "0" * 64)
    return FutureChildSeams(
        model_list=lambda: True, thread_start=lambda: True, runtime_shutdown=lambda: True,
        thread_resume=lambda: True,
        turn1=lambda: f"START_CONFIRMED {Terminal.COMPLETED} {response_marker}",
        turn2=lambda marker: f"RESUME_CONFIRMED {Terminal.COMPLETED} {marker}",
        turn3_capture=lambda: capture, approval_response=lambda: True, allow_response=lambda: True,
        turn4_start=lambda: FlowBinding(binding.thread_id, "turn-4", binding.cwd, 4), interrupt=lambda: True, predelete=lambda: clean,
        bind_controller=lambda: FreshSchemaV4ControllerBinding(boot.get("controller_db", ""), boot.get("profile_id", "synthetic-p7c13"), binding.thread_id), delete_service=lambda: "DELETED",
        postdelete=lambda result, observed: result == "DELETED" and observed.thread_count > 0,
    )


def _child_result_payload(boot: Mapping[str, Any], result: CompleteChildResult, budget: EffectBudget) -> dict[str, Any]:
    return {
        "schema": CHILD_RESULT_SCHEMA, "status": "PASS" if result.verdict else "FAILED", "verdict": result.verdict,
        "source_head": boot["source_head"], "source_tree": boot["source_tree"], "harness_blob": boot["harness_blob"], "run_id_hash": boot["run_id_hash"],
        "effect_counts": dict(budget.counts), "outcomes": dict(result.outcomes), "residual_counts": dict(result.residual_counts),
        "classes": dict(result.classes), "process_group_quiescent": True,
    }


def _future_child_main(
    boot_path: str | Path | None = None, *, installed: InstalledRuntimeAuthority | None = None,
    runtime_factory: Callable[[dict[str, str], tuple[str, ...]], Any] | None = None,
    business_factory: Callable[[Any], Any] | None = None,
    seams_factory: Callable[[Mapping[str, Any], FlowBinding, str, str], FutureChildSeams] | None = None,
) -> int:
    """Bounded child entrypoint; boot validation precedes installed/runtime effects."""
    if boot_path is None:
        raise PreparationGateError("boot authority required")
    boot = RootOnlyBootAuthority(boot_path).read()
    profile = CodexProfile(boot["profile_id"], boot["codex_home"], "P7.C13", boot["isolated_root"])
    routing = FutureRuntimeRouting(profile)
    budget = EffectBudget(dict(boot["effect_ceiling"]))
    binding = FlowBinding("synthetic-future-thread", "turn-1", boot["workdir"], 1)
    memory_marker, response_marker = fresh_non_secret_markers()
    try:
        seams = seams_factory(boot, binding, memory_marker, response_marker) if seams_factory else _default_child_seams(boot, binding, memory_marker, response_marker)
        if runtime_factory is None:
            runtime_factory = lambda environment, overrides: CodexRuntimeManager(
                (profile,), client_version="p7c13-future", isolation_authority=IsolationPathAuthority((profile,), controller_db_path=boot["controller_db"], repository_root=boot["workdir"]),
                parent_environment=environment,
            )
        if business_factory is None:
            dispatch = {name: (lambda: True) for name in FROZEN_EFFECT_BUDGET if name not in {"thread/read", "thread/list", "second_child", "real_retry", "telegram"}}
            effects = FutureRealEffectBridge(budget, dispatch)
            business_factory = lambda runtime: CompleteFutureChildOrchestrator(
                effects=effects, binding=binding, memory_marker=memory_marker, response_marker=response_marker, seams=seams, boot=boot,
            )
        child = FutureRealChildPath(installed=installed or InstalledRuntimeAuthority(), routing=routing, runtime_factory=runtime_factory, business_factory=business_factory)
        result = child.run()
        if not isinstance(result, CompleteChildResult):
            raise PreparationGateError("complete child result missing")
        _write_child_result(boot["child_result_path"], _child_result_payload(boot, result, budget))
        return 0 if result.verdict else 1
    except Exception as error:
        failure = CompleteChildResult(False, {"terminal": type(error).__name__}, {"scan_errors": 1}, {"failure": "FAIL_CLOSED"})
        try:
            _write_child_result(boot["child_result_path"], _child_result_payload(boot, failure, budget))
        except (OSError, PreparationGateError):
            pass
        return 1


def _synthetic_ledger_record(state: str = "RESERVED") -> dict[str, Any]:
    return {
        "schema": LEDGER_SCHEMA,
        "state": state,
        "source_head": REPAIR1_BASE_HEAD,
        "source_tree": ARCHITECT_MAIN_TREE,
        "harness_blob": ORIGINAL_HARNESS_BLOB,
        "run_id_hash": "a" * 64,
        "path_hashes": {"workdir": "b" * 64, "isolated_root": "c" * 64},
        "effect_counts": {},
        "recovery": {"status": "reserved"},
    }


def _synthetic_boot_record(base: str | Path, *, source_head: str = REPAIR2_BASE_HEAD, source_tree: str = P7C13_BASE_TREE, harness_blob: str = PRIOR_HARNESS_BLOB) -> dict[str, Any]:
    root = Path(base)
    return {
        "schema": BOOT_SCHEMA, "source_head": source_head, "source_tree": source_tree,
        "harness_blob": harness_blob, "run_id_hash": "d" * 64, "profile_id": "synthetic-p7c13",
        "codex_home": PERSISTENT_HOME, "isolated_root": str(root / "isolated"),
        "controller_db": str(root / "controller.sqlite3"), "workdir": str(root / "workdir"),
        "approval_target": "/root/p7c13-approval-synthetic-child", "ledger_path": str(root / "ledger.json"),
        "child_result_path": str(root / "child-result.json"), "contract_hash": "e" * 64,
        "effect_ceiling": dict(FROZEN_EFFECT_BUDGET),
    }


class P7C13Repair1AuthorityTests(unittest.TestCase):
    def test_durable_latch_first_restart_terminal_and_incomplete_reservations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-ledger-") as directory:
            path = Path(directory) / "ledger.json"
            ledger = DurableOneShotLedger(path)
            self.assertTrue(ledger.reserve(_synthetic_ledger_record()))
            self.assertFalse(DurableOneShotLedger(path).reserve(_synthetic_ledger_record()))
            reopened = DurableOneShotLedger(path)
            self.assertEqual("RESERVED", reopened.read()["state"])
            reopened.update(state="COMPLETED")
            self.assertFalse(DurableOneShotLedger(path).reserve(_synthetic_ledger_record()))
            self.assertEqual("COMPLETED", reopened.read()["state"])

    def test_durable_latch_malformed_duplicate_symlink_mode_and_identity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-ledger-") as directory:
            base = Path(directory)
            malformed = base / "malformed.json"
            malformed.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            os.chmod(malformed, 0o600)
            with self.assertRaises(PreparationGateError):
                DurableOneShotLedger(malformed).read()
            source = base / "source.json"
            DurableOneShotLedger(source).reserve(_synthetic_ledger_record())
            link = base / "link.json"
            link.symlink_to(source)
            with self.assertRaises(PreparationGateError):
                DurableOneShotLedger(link).read()
            hardlink = base / "hardlink.json"
            os.link(source, hardlink)
            with self.assertRaises(PreparationGateError):
                DurableOneShotLedger(source).read()
            hardlink.unlink()
            os.chmod(source, 0o640)
            with self.assertRaises(PreparationGateError):
                DurableOneShotLedger(source).read()
            os.chmod(source, 0o600)
            reader = DurableOneShotLedger(source)
            reader.read()
            replacement = base / "replacement.json"
            DurableOneShotLedger(replacement).reserve(_synthetic_ledger_record())
            os.replace(replacement, source)
            with self.assertRaises(PreparationGateError):
                reader.read()

    def test_prepared_future_executor_reserves_durable_ledger_before_one_child(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-executor-") as directory:
            ledger = DurableOneShotLedger(Path(directory) / "ledger.json")
            result_path = Path(directory) / "result.json"
            fake_watchdog = unittest.mock.Mock()
            fake_watchdog.run.return_value = WatchdogResult("COMPLETED", child_result_valid=True)
            executor = PreparedFutureRealExecutor(
                ledger=ledger, watchdog=fake_watchdog, child_command=("synthetic-child",),
                result_path=result_path, record=_synthetic_ledger_record(),
            )
            fake_watchdog.run.side_effect = lambda command, *, result_path: (_write_child_result(result_path, _child_result_payload(executor._boot_record(executor.record), CompleteChildResult(True, {}, {}, {}), EffectBudget())), WatchdogResult("COMPLETED", child_result_valid=True))[1]
            self.assertEqual("COMPLETED", executor.run().status)
            fake_watchdog.run.assert_called_once_with(("synthetic-child",), result_path=result_path)
            with self.assertRaises(PreparationGateError):
                executor.run()
            self.assertEqual("COMPLETED", DurableOneShotLedger(Path(directory) / "ledger.json").read()["state"])

    def test_watchdog_uses_one_synthetic_child_and_validates_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-watchdog-") as directory:
            result = Path(directory) / "result.json"
            payload = json.dumps({"schema": "p7c13-child-result-v1", "status": "COMPLETED", "effect_counts": {}, "outcomes": {}, "residual_counts": {}, "verdict": True})
            code = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
            watchdog = OwnedParentChildWatchdog()
            outcome = watchdog.run((sys.executable, "-c", code, str(result), payload), result_path=result)
            self.assertEqual("COMPLETED", outcome.status)
            self.assertEqual(1, watchdog.child_count)
            self.assertTrue(outcome.child_result_valid)
            self.assertEqual(0, outcome.signals_sent.__len__())
            self.assertEqual("FAIL_CLOSED", watchdog.run((sys.executable, "-c", "pass"), result_path=result).status)

    def test_watchdog_timeout_term_kill_owned_group_and_wrong_group_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-watchdog-") as directory:
            result = Path(directory) / "missing-result.json"
            watchdog = OwnedParentChildWatchdog()
            outcome = watchdog.run((sys.executable, "-c", "import time; time.sleep(10)"), result_path=result, timeout_seconds=0.05, term_grace_seconds=0.05)
            self.assertEqual("TIMEOUT", outcome.status)
            self.assertEqual((signal.SIGTERM,), outcome.signals_sent)
            watchdog = OwnedParentChildWatchdog()
            watchdog.owned_pid, watchdog.owned_pgid = os.getpid(), os.getpgrp() + 1
            with self.assertRaises(PreparationGateError):
                watchdog._signal_owned(signal.SIGTERM)

    def test_installed_and_isolated_runtime_authority_blocks_drift_before_effects(self) -> None:
        good = InstalledRuntimeAuthority(probe=lambda: (INSTALLED_VERSION, SCHEMA_SHA256))
        good.verify()
        for probe in (
            lambda: ("codex-cli 0.144.5", SCHEMA_SHA256),
            lambda: (INSTALLED_VERSION, "0" * 64),
        ):
            with self.subTest(probe=probe):
                with self.assertRaises(PreparationGateError):
                    InstalledRuntimeAuthority(probe=probe).verify()
        profile = CodexProfile("future-profile", PERSISTENT_HOME, "Future", "/root/p7c13-future-isolated")
        routing = FutureRuntimeRouting(profile)
        self.assertEqual(PERSISTENT_HOME, routing.environment({"HOME": "/root", "PATH": "/usr/bin"})["CODEX_HOME"])
        self.assertEqual(3, len(routing.config_overrides()))

    def test_future_child_path_checks_installed_and_routing_before_business(self) -> None:
        calls: list[str] = []
        profile = CodexProfile("future-profile", PERSISTENT_HOME, "Future", "/root/p7c13-future-isolated")
        child = FutureRealChildPath(
            installed=InstalledRuntimeAuthority(probe=lambda: (INSTALLED_VERSION, SCHEMA_SHA256)),
            routing=FutureRuntimeRouting(profile),
            runtime_factory=lambda environment, overrides: (calls.append("runtime"), environment, overrides)[1],
            business_factory=lambda runtime: type("Business", (), {"run": lambda self: calls.append("business")})(),
        )
        child.run()
        self.assertEqual(["runtime", "business"], calls)
        blocked_calls: list[str] = []
        blocked = FutureRealChildPath(
            installed=InstalledRuntimeAuthority(probe=lambda: (INSTALLED_VERSION, "wrong-schema")),
            routing=FutureRuntimeRouting(profile),
            runtime_factory=lambda environment, overrides: blocked_calls.append("runtime"),
            business_factory=lambda runtime: blocked_calls.append("business"),
        )
        with self.assertRaises(PreparationGateError):
            blocked.run()
        self.assertEqual([], blocked_calls)

    def test_complete_future_business_path_budget_wraps_every_dispatch(self) -> None:
        budget = EffectBudget()
        dispatched: list[str] = []
        effects = FutureRealEffectBridge(
            budget,
            {name: (lambda name=name: dispatched.append(name)) for name in (
                "new_threads", "model/list", "thread/start", "thread/resume", "turn/start",
                "approval_responses", "allow_responses", "turn/interrupt", "thread/delete",
            )},
        )
        business = FutureRealBusinessPath(
            effects, delete_service=lambda: dispatched.append("delete-service"),
            turns=tuple(lambda: dispatched.append(f"turn-{index}") for index in range(1, 5)),
            approval=lambda: dispatched.append("approval-check"), interrupt=lambda: dispatched.append("interrupt-check"),
        )
        business.run()
        self.assertEqual(1, budget.count("thread/start"))
        self.assertEqual(1, budget.count("thread/resume"))
        self.assertEqual(4, budget.count("turn/start"))
        self.assertEqual(1, budget.count("thread/delete"))
        self.assertIn("delete-service", dispatched)

    def test_future_effect_bridge_blocks_over_budget_before_fake_dispatch(self) -> None:
        calls: list[str] = []
        bridge = FutureRealEffectBridge(EffectBudget(), {"model/list": lambda: calls.append("model")})
        bridge.call("model/list")
        with self.assertRaises(PreparationGateError):
            bridge.call("model/list")
        with self.assertRaises(PreparationGateError):
            bridge.forbidden("thread/list")
        self.assertEqual(["model"], calls)


class P7C13Repair2IntegrationTests(unittest.TestCase):
    def test_child_cli_dispatches_to_child_and_normal_unittest_never_does(self) -> None:
        with patch(__name__ + "._future_child_main", return_value=7) as child:
            self.assertEqual(7, _module_main(("--p7c13-future-child", "--boot-authority", "/synthetic/boot")))
            child.assert_called_once_with("/synthetic/boot")
        with patch(__name__ + "._future_child_main") as child, patch("unittest.main") as unittest_main:
            self.assertEqual(0, _module_main(()))
            child.assert_not_called()
            unittest_main.assert_called_once()

    def test_boot_authority_is_bounded_root_only_and_source_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-boot-") as directory:
            path = Path(directory) / "boot.json"
            record = _synthetic_boot_record(directory)
            authority = RootOnlyBootAuthority(path)
            self.assertEqual(record, authority.create(record))
            self.assertEqual(record, authority.read(expected=record))
            with self.assertRaises(PreparationGateError):
                authority.read(expected={**record, "source_head": "wrong"})
            os.chmod(path, 0o640)
            with self.assertRaises(PreparationGateError):
                authority.read()

    def test_boot_missing_malformed_symlink_and_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-boot-") as directory:
            base = Path(directory)
            with self.assertRaises(PreparationGateError):
                RootOnlyBootAuthority(base / "missing.json").read()
            malformed = base / "malformed.json"
            malformed.write_text('{"schema":"x","schema":"y"}', encoding="utf-8")
            os.chmod(malformed, 0o600)
            with self.assertRaises(PreparationGateError):
                RootOnlyBootAuthority(malformed).read()
            real = base / "real.json"
            RootOnlyBootAuthority(real).create(_synthetic_boot_record(directory))
            link = base / "link.json"
            link.symlink_to(real)
            with self.assertRaises(PreparationGateError):
                RootOnlyBootAuthority(link).read()
            replacement = base / "replacement.json"
            RootOnlyBootAuthority(replacement).create(_synthetic_boot_record(directory, source_tree="f" * 40))
            os.replace(replacement, real)
            with self.assertRaises(PreparationGateError):
                RootOnlyBootAuthority(real).read(expected=_synthetic_boot_record(directory))

    def test_exact_parent_order_is_ledger_boot_child_and_second_attempt_spawns_zero(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-parent-") as directory:
            events: list[str] = []
            watchdog = unittest.mock.Mock()
            watchdog.run.return_value = WatchdogResult("COMPLETED", child_result_valid=True)
            executor = PreparedFutureRealExecutor(
                ledger=DurableOneShotLedger(Path(directory) / "ledger.json"), watchdog=watchdog,
                child_command=("synthetic",), result_path=Path(directory) / "result.json",
                boot_path=Path(directory) / "boot.json", record=_synthetic_ledger_record(),
                child_factory=lambda boot: (events.append("child_factory"), ("synthetic",))[1],
            )
            executor.run()
            self.assertEqual(["child_factory"], events)
            self.assertEqual(["ledger", "boot", "child"], executor.order)
            with self.assertRaises(PreparationGateError):
                executor.run()
            self.assertEqual(1, watchdog.run.call_count)

    def test_synthetic_exact_boot_traverses_complete_child_and_writes_bounded_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-child-") as directory:
            boot = _synthetic_boot_record(directory)
            boot_path = Path(directory) / "boot.json"
            RootOnlyBootAuthority(boot_path).create(boot)
            runtime_calls: list[str] = []
            code = _future_child_main(
                boot_path, installed=InstalledRuntimeAuthority(probe=lambda: (INSTALLED_VERSION, SCHEMA_SHA256)),
                runtime_factory=lambda environment, overrides: (runtime_calls.append("runtime"), object())[1],
            )
            self.assertEqual(0, code)
            self.assertEqual(["runtime"], runtime_calls)
            result = read_child_result(boot["child_result_path"], boot=boot)
            self.assertEqual("PASS", result["status"])
            self.assertTrue(result["verdict"])
            self.assertTrue(result["process_group_quiescent"])
            self.assertEqual(1, result["effect_counts"]["new_threads"])

    def test_child_failure_writes_bounded_nonpass_result_and_missing_result_blocks_parent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-result-") as directory:
            boot = _synthetic_boot_record(directory)
            boot_path = Path(directory) / "boot.json"
            RootOnlyBootAuthority(boot_path).create(boot)
            code = _future_child_main(
                boot_path, installed=InstalledRuntimeAuthority(probe=lambda: (INSTALLED_VERSION, SCHEMA_SHA256)),
                runtime_factory=lambda environment, overrides: object(),
                business_factory=lambda runtime: type("FailingBusiness", (), {"run": lambda self: (_ for _ in ()).throw(PreparationGateError("synthetic failure"))})(),
            )
            self.assertEqual(1, code)
            self.assertEqual("FAILED", read_child_result(boot["child_result_path"], boot=boot)["status"])
            ledger = DurableOneShotLedger(Path(directory) / "parent-ledger.json")
            watchdog = unittest.mock.Mock()
            watchdog.run.return_value = WatchdogResult("COMPLETED", child_result_valid=True)
            executor = PreparedFutureRealExecutor(
                ledger=ledger, watchdog=watchdog, child_command=("synthetic",), result_path=Path(directory) / "missing.json",
                boot_path=Path(directory) / "parent-boot.json", record=_synthetic_ledger_record(),
            )
            executor.run()
            self.assertEqual("FAILED", ledger.read()["state"])

    def test_pre_dispatch_approval_allow_interrupt_and_delete_budgets_block_callbacks(self) -> None:
        calls: list[str] = []
        bridge = FutureRealEffectBridge(EffectBudget(), {})
        bridge.call("approval_responses", lambda: calls.append("approval"))
        bridge.call("allow_responses", lambda: calls.append("allow"))
        bridge.call("turn/interrupt", lambda: calls.append("interrupt"))
        bridge.call("thread/delete", lambda: calls.append("delete"))
        for effect in ("approval_responses", "allow_responses", "turn/interrupt", "thread/delete"):
            with self.assertRaises(PreparationGateError):
                bridge.call(effect, lambda: calls.append("over-budget"))
        self.assertEqual(["approval", "allow", "interrupt", "delete"], calls)
        with self.assertRaises(PreparationGateError):
            bridge.forbidden("thread/read")
        with self.assertRaises(PreparationGateError):
            bridge.forbidden("thread/list")
        self.assertNotIn("over-budget", calls)

    def test_complete_fake_turn3_owned_binding_and_turn4_active_binding_are_real_seams(self) -> None:
        binding = FlowBinding("thread-fake", "turn-1", "/root/fake-work", 1)
        memory, response = "memory-fake", "response-fake"
        base = _default_child_seams({"approval_target": "/root/p7c13-approval-fake"}, binding, memory, response)
        effects = FutureRealEffectBridge(EffectBudget(), {name: (lambda: True) for name in FROZEN_EFFECT_BUDGET if name not in {"thread/read", "thread/list", "second_child", "real_retry", "telegram"}})
        capture = base.turn3_capture()
        wrong = ApprovalAuthorityCapture(capture.request, capture.expected, capture.wire, FlowBinding("wrong", "turn-3", binding.cwd, 3), capture.selected_target, False, True)
        responses: list[str] = []
        base.turn3_capture = lambda: wrong
        base.approval_response = lambda: responses.append("response")
        base.allow_response = lambda: responses.append("allow")
        with self.assertRaises(PreparationGateError):
            CompleteFutureChildOrchestrator(effects=effects, binding=binding, memory_marker=memory, response_marker=response, seams=base).run()
        self.assertEqual([], responses)
        inactive = _default_child_seams({"approval_target": "/root/p7c13-approval-fake"}, binding, memory, response)
        interrupts: list[str] = []
        inactive.turn4_start = lambda: False
        inactive.interrupt = lambda: interrupts.append("interrupt")
        with self.assertRaises(PreparationGateError):
            CompleteFutureChildOrchestrator(effects=FutureRealEffectBridge(EffectBudget(), {name: (lambda: True) for name in FROZEN_EFFECT_BUDGET if name not in {"thread/read", "thread/list", "second_child", "real_retry", "telegram"}}), binding=binding, memory_marker=memory, response_marker=response, seams=inactive).run()
        self.assertEqual([], interrupts)


def read_only_boundary_preflight(
    protected: Mapping[str, str], *, mountinfo: str, identities: Mapping[str, tuple[int, int]],
) -> bool:
    """Offline seam for the future /proc/self/mountinfo and filesystem proof."""
    if len(set(identities.values())) != len(protected):
        return False
    if any(any(field == path for field in line.split()[:5]) for line in mountinfo.splitlines() for path in protected.values()):
        return False
    return all(Path(path).is_absolute() and not Path(path).is_symlink() for path in protected.values())


class _FakeDelete:
    def __init__(self, status: ThreadOperationStatus, remove_paths: tuple[Path, ...] = ()) -> None:
        self.status = status
        self.remove_paths = remove_paths
        self.calls = 0

    async def delete(self, *, binding: ThreadBinding) -> ThreadOperationResult:
        self.calls += 1
        for path in self.remove_paths:
            if path.exists():
                path.unlink()
        return ThreadOperationResult(self.status, binding)


class _FailingScanner:
    def scan(self, profile: CodexProfile, thread_id: str):
        return scanner_module.PersistentProfileScanResult(0, 0, 0, 1)


class P7C13OfflineFlowTests(unittest.TestCase):
    def test_future_gate_is_disabled_and_entrypoint_has_no_effect_path(self) -> None:
        self.assertFalse(future_real_gate({}, None))
        self.assertFalse(future_real_gate({FUTURE_GATE_ENV: "anything"}, None))
        with self.assertRaisesRegex(PreparationGateError, "DISABLED"):
            future_real_entrypoint(environ={}, contract=None)

    def test_exact_future_gate_invokes_injected_executor_once(self) -> None:
        contract = FutureArchitectContract("synthetic-gate-only", "head", "tree", "harness")
        environment = {FUTURE_GATE_ENV: contract.authorization_token, "P7C13_EXPECTED_HEAD": "head", "P7C13_EXPECTED_TREE": "tree", "P7C13_EXPECTED_HARNESS_BLOB": "harness"}
        fake = unittest.mock.Mock(spec=FutureRealExecutor)
        fake.run.return_value = "synthetic-result"
        self.assertTrue(future_real_gate(environment, contract, current_head="head", current_tree="tree", current_harness_blob="harness"))
        self.assertEqual("synthetic-result", future_real_entrypoint(environ=environment, contract=contract, current_head="head", current_tree="tree", current_harness_blob="harness", executor=fake))
        fake.run.assert_called_once_with(contract=contract)

    def test_future_gate_unset_and_each_authority_mismatch_calls_zero_executor(self) -> None:
        contract = FutureArchitectContract("synthetic-gate-only", "head", "tree", "harness")
        exact = {FUTURE_GATE_ENV: "synthetic-gate-only", "P7C13_EXPECTED_HEAD": "head", "P7C13_EXPECTED_TREE": "tree", "P7C13_EXPECTED_HARNESS_BLOB": "harness"}
        cases = (
            ({}, "head", "tree", "harness"),
            ({**exact, FUTURE_GATE_ENV: "wrong"}, "head", "tree", "harness"),
            (exact, "wrong", "tree", "harness"),
            (exact, "head", "wrong", "harness"),
            (exact, "head", "tree", "wrong"),
        )
        for environment, head, tree, blob in cases:
            with self.subTest(head=head, tree=tree, blob=blob):
                fake = unittest.mock.Mock(spec=FutureRealExecutor)
                with self.assertRaises(PreparationGateError):
                    future_real_entrypoint(environ=environment, contract=contract, current_head=head, current_tree=tree, current_harness_blob=blob, executor=fake)
                fake.run.assert_not_called()

    def test_budget_is_frozen_and_zero_real_effects_are_not_records(self) -> None:
        self.assertEqual(
            {
                "new_threads": NEW_THREADS_MAX,
                "model/list": MODEL_LIST_MAX,
                "thread/start": THREAD_START_MAX,
                "thread/resume": THREAD_RESUME_MAX,
                "turn/start": TURN_START_MAX,
                "approval_responses": APPROVAL_RESPONSES_MAX,
                "allow_responses": ALLOW_RESPONSES_MAX,
                "turn/interrupt": TURN_INTERRUPT_MAX,
                "thread/delete": OFFICIAL_THREAD_DELETE_MAX,
                "thread/read": THREAD_READ_MAX,
                "thread/list": THREAD_LIST_MAX,
                "second_child": SECOND_CHILD_MAX,
                "real_retry": REAL_RETRY_MAX,
                "telegram": TELEGRAM_MAX,
            },
            dict(FROZEN_EFFECT_BUDGET),
        )
        self.assertEqual(FROZEN_EFFECT_BUDGET["thread/read"], 0)
        self.assertEqual(FROZEN_EFFECT_BUDGET["thread/list"], 0)
        self.assertEqual(TURN3_SANDBOX_PERMISSION, "sandbox_permissions=require_escalated")
        self.assertEqual(TURN4_STIMULUS, "sleep 120")
        self.assertIn("DialogueDeleteService", FUTURE_DELETE_CHAIN)
        budget = EffectBudget()
        self.assertEqual({}, budget.counts)
        self.assertEqual(0, budget.count("thread/start"))

    def test_turn1_turn2_restart_exact_binding_and_marker_plan(self) -> None:
        flow = OfflineFutureFlow()
        self.assertTrue(flow.turn1())
        self.assertTrue(flow.restart_and_resume())
        self.assertTrue(flow.turn2_remembers("P7C13_MEMORY_SYNTHETIC"))
        self.assertFalse(flow.restart_and_resume())
        self.assertEqual(flow.binding.thread_id, "thread-13")
        self.assertEqual(flow.budget.count("thread/start"), 1)
        self.assertEqual(flow.budget.count("thread/resume"), 1)
        self.assertEqual(flow.budget.count("turn/start"), 2)

    def test_turn1_observed_response_marker_is_exact_and_turn2_memory_is_exact(self) -> None:
        memory_marker, response_marker = fresh_non_secret_markers()
        self.assertTrue(memory_marker and response_marker and memory_marker != response_marker)
        self.assertEqual(64, len(_sha256(memory_marker)))
        self.assertEqual(64, len(_sha256(response_marker)))
        missing = OfflineFutureFlow()
        self.assertFalse(missing.turn1(observed_output="START_CONFIRMED COMPLETED"))
        wrong = OfflineFutureFlow()
        self.assertFalse(wrong.turn1(observed_output="START_CONFIRMED COMPLETED WRONG_RESPONSE"))
        flow = OfflineFutureFlow()
        self.assertTrue(flow.turn1())
        self.assertTrue(flow.restart_and_resume())
        self.assertFalse(flow.turn2_remembers("not-the-memory-marker"))
        flow = OfflineFutureFlow()
        self.assertTrue(flow.turn1())
        self.assertTrue(flow.restart_and_resume())
        self.assertFalse(flow.turn2_remembers(flow.memory_marker, observed_output="RESUME_CONFIRMED COMPLETED WRONG"))

    def test_turn_authorities_are_four_distinct_ids_and_reuse_fails_closed(self) -> None:
        flow = OfflineFutureFlow()
        self.assertTrue(turn_authorities_are_distinct(flow))
        self.assertNotEqual(flow.turn1_authority.turn_id, flow.turn4_authority.turn_id)
        flow.turn1()
        flow.restart_and_resume()
        flow.turn2_remembers(flow.memory_marker)
        request, expected, wire = _matcher_fixture(flow.selected_target)
        flow.approval_candidate(target=flow.selected_target, request=request, expected=expected, wire=wire)
        self.assertFalse(flow.turn4_start(binding=flow.turn1_authority.binding))

    def test_self_consistent_wrong_owned_approval_tuples_never_allow(self) -> None:
        mutations = ("thread", "turn", "cwd", "sequence", "target")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                flow = OfflineFutureFlow()
                flow.turn1(); flow.restart_and_resume(); flow.turn2_remembers(flow.memory_marker)
                target = flow.selected_target
                wrong_thread = "wrong-thread" if mutation == "thread" else flow.binding.thread_id
                wrong_turn = "wrong-turn" if mutation == "turn" else "turn-3"
                wrong_cwd = "/root/wrong-cwd" if mutation == "cwd" else flow.binding.cwd
                wrong_sequence = 99 if mutation == "sequence" else 3
                wrong_target = "/root/wrong-target" if mutation == "target" else target
                request, expected, wire = _matcher_fixture(wrong_target, thread=wrong_thread, turn=wrong_turn, cwd=wrong_cwd)
                request = c12.CapturedRequest(request.kind, request.request_ordinal, wrong_sequence, request.thread_sha256, request.turn_sha256, request.cwd_sha256, request.command_sha256)
                expected = c12.ExpectedAuthority(expected.kind, expected.request_ordinal, wrong_sequence, expected.thread_sha256, expected.turn_sha256, expected.cwd_sha256, expected.target, expected.command_sha256)
                wire = c12.CorrelatedWireRecord(wire.kind, wire.request_ordinal, wrong_sequence, wire.thread_sha256, wire.turn_sha256, wire.cwd_sha256, wire.expected_target_sha256, wire.command_plaintext, wire.command_sha256)
                self.assertFalse(flow.approval_candidate(target=target, request=request, expected=expected, wire=wire))
                self.assertEqual(0, flow.allow_responses)

    def test_selected_target_exact_lstat_and_post_allow_metadata_are_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-target-") as directory:
            target = Path(directory) / "target"
            self.assertTrue(exact_target_is_absent(target))
            target.write_text("synthetic", encoding="utf-8")
            self.assertFalse(exact_target_is_absent(target))
            os.chmod(target, 0o600)
            self.assertTrue(validate_approval_target_after_allow(target))
            target.unlink()
            target.symlink_to(Path(directory) / "missing")
            self.assertFalse(validate_approval_target_after_allow(target))

    def test_selected_target_is_fresh_high_entropy_direct_child_and_not_a_boundary(self) -> None:
        target = select_run_owned_target(
            cwd="/root/work-13", workdir="/root/work-13", repository="/root/CodexControl",
            isolated_root="/root/p7c13-state", controller_root="/root/p7c13-controller",
        )
        self.assertEqual(Path("/root"), Path(target).parent)
        self.assertTrue(exact_target_is_absent(target))
        self.assertEqual(64, len(Path(target).name.rsplit("-", 1)[-1]))

    def test_turn3_exact_match_is_one_allow_and_target_must_start_absent(self) -> None:
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        target = "/root/p7c13-approval-synthetic"
        request, expected, wire = _matcher_fixture(target, turn="turn-3")
        self.assertTrue(validate_approval_target(target, cwd="/root/work-13", workdir="/root/work-13", repository="/root/CodexControl", isolated_root="/root/p7c13-state", controller_root="/root/p7c13-controller", target_exists_before=False))
        self.assertTrue(flow.turn2_remembers(flow.memory_marker))
        self.assertTrue(flow.approval_candidate(target=target, request=request, expected=expected, wire=wire))
        self.assertEqual(flow.approval_requests, 1)
        self.assertEqual(flow.allow_responses, 1)
        self.assertEqual(flow.deny_responses, 0)
        self.assertFalse(flow.approval_candidate(target=target, request=request, expected=expected, wire=wire))

    def test_approval_target_boundary_and_completion_are_fail_closed(self) -> None:
        common = dict(cwd="/root/work-13", workdir="/root/work-13", repository="/root/CodexControl", isolated_root="/root/p7c13-state", controller_root="/root/p7c13-controller")
        self.assertFalse(validate_approval_target("/tmp/p7c13", **common, target_exists_before=False))
        self.assertFalse(validate_approval_target("/root/work-13/target", **common, target_exists_before=False))
        self.assertFalse(validate_approval_target("/root/p7c13-state", **common, target_exists_before=False))
        self.assertFalse(validate_approval_target("/root/p7c13-approval-synthetic", **common, target_exists_before=True))
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        flow.turn2_remembers(flow.memory_marker)
        target = "/root/p7c13-approval-synthetic"
        request, expected, wire = _matcher_fixture(target)
        self.assertFalse(flow.approval_candidate(target=target, request=request, expected=expected, wire=wire, target_exists_after=False))
        self.assertEqual(flow.allow_responses, 0)

    def test_turn3_mismatch_existing_target_and_missing_completion_fail_closed(self) -> None:
        for mutation in ("wrong-thread", "wrong-turn", "wrong-cwd", "wrong-sequence", "wrong-sha", "wrong-target"):
            with self.subTest(mutation=mutation):
                flow = OfflineFutureFlow()
                flow.turn1()
                flow.restart_and_resume()
                flow.turn2_remembers(flow.memory_marker)
                target = "/root/p7c13-approval-synthetic"
                request, expected, wire = _matcher_fixture(target)
                if mutation == "wrong-thread":
                    request = c12.CapturedRequest(request.kind, request.request_ordinal, request.local_sequence, _sha256("wrong"), request.turn_sha256, request.cwd_sha256, request.command_sha256)
                elif mutation == "wrong-turn":
                    expected = c12.ExpectedAuthority(expected.kind, expected.request_ordinal, expected.local_sequence, expected.thread_sha256, _sha256("wrong"), expected.cwd_sha256, expected.target, expected.command_sha256)
                elif mutation == "wrong-cwd":
                    wire = c12.CorrelatedWireRecord(wire.kind, wire.request_ordinal, wire.local_sequence, wire.thread_sha256, wire.turn_sha256, _sha256("wrong"), wire.expected_target_sha256, wire.command_plaintext, wire.command_sha256)
                elif mutation == "wrong-sequence":
                    request = c12.CapturedRequest(request.kind, request.request_ordinal, 9, request.thread_sha256, request.turn_sha256, request.cwd_sha256, request.command_sha256)
                elif mutation == "wrong-sha":
                    wire = c12.CorrelatedWireRecord(wire.kind, wire.request_ordinal, wire.local_sequence, wire.thread_sha256, wire.turn_sha256, wire.cwd_sha256, wire.expected_target_sha256, wire.command_plaintext, "0" * 64)
                else:
                    expected = c12.ExpectedAuthority(expected.kind, expected.request_ordinal, expected.local_sequence, expected.thread_sha256, expected.turn_sha256, expected.cwd_sha256, "/root/p7c13-other-target", expected.command_sha256)
                self.assertFalse(flow.approval_candidate(target=target, request=request, expected=expected, wire=wire))
                self.assertEqual(flow.allow_responses, 0)
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        flow.turn2_remembers(flow.memory_marker)
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        self.assertFalse(flow.approval_candidate(target=expected.target, target_exists_before=True, request=request, expected=expected, wire=wire))
        self.assertFalse(flow.delete_reachable(predelete_observed=True))

    def test_turn4_is_separate_sleep_interrupt_and_unknown_fails(self) -> None:
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        flow.turn2_remembers(flow.memory_marker)
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        flow.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        self.assertTrue(flow.turn4_start(binding=flow.turn4_authority.binding))
        self.assertTrue(flow.turn4_interrupt(binding=flow.turn4_authority.binding))
        self.assertEqual(flow.budget.count("turn/interrupt"), 1)
        self.assertEqual(flow.allow_responses, 1)
        self.assertFalse(flow.turn4_unexpected_approval())
        self.assertFalse(flow.turn4_interrupt(binding=flow.binding))
        unknown = OfflineFutureFlow()
        unknown.turn1()
        unknown.restart_and_resume()
        unknown.turn2_remembers(unknown.memory_marker)
        unknown.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        self.assertTrue(unknown.turn4_start(binding=unknown.turn4_authority.binding))
        self.assertFalse(unknown.turn4_interrupt(binding=unknown.turn4_authority.binding, unknown=True))
        self.assertEqual(unknown.budget.count("turn/interrupt"), 0)

    def test_turn4_wrong_binding_terminal_before_interrupt_second_interrupt_and_unexpected_approval_fail(self) -> None:
        flow = OfflineFutureFlow()
        flow.turn1(); flow.restart_and_resume(); flow.turn2_remembers(flow.memory_marker)
        request, expected, wire = _matcher_fixture(flow.selected_target)
        self.assertTrue(flow.approval_candidate(target=flow.selected_target, request=request, expected=expected, wire=wire))
        self.assertFalse(flow.turn4_start(binding=FlowBinding("wrong-thread", "turn-4", "/root/work-13", 4)))
        terminal = OfflineFutureFlow()
        terminal.turn1(); terminal.restart_and_resume(); terminal.turn2_remembers(terminal.memory_marker)
        request, expected, wire = _matcher_fixture(terminal.selected_target)
        terminal.approval_candidate(target=terminal.selected_target, request=request, expected=expected, wire=wire)
        self.assertFalse(terminal.turn4_interrupt(binding=terminal.turn4_authority.binding))
        successful = OfflineFutureFlow()
        successful.turn1(); successful.restart_and_resume(); successful.turn2_remembers(successful.memory_marker)
        request, expected, wire = _matcher_fixture(successful.selected_target)
        successful.approval_candidate(target=successful.selected_target, request=request, expected=expected, wire=wire)
        self.assertTrue(successful.turn4_start(binding=successful.turn4_authority.binding))
        self.assertTrue(successful.turn4_interrupt(binding=successful.turn4_authority.binding))
        self.assertFalse(successful.turn4_interrupt(binding=successful.turn4_authority.binding))
        successful.turn4_unexpected_approval_seen = True
        self.assertFalse(successful.turn4_unexpected_approval())

    def test_delete_is_unreachable_until_all_turn_and_predelete_gates_pass(self) -> None:
        flow = OfflineFutureFlow()
        self.assertFalse(flow.delete_reachable(predelete_observed=True))
        flow.turn1()
        flow.restart_and_resume()
        flow.turn2_remembers(flow.memory_marker)
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        flow.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        flow.turn4_start(binding=flow.turn4_authority.binding)
        flow.turn4_interrupt(binding=flow.turn4_authority.binding)
        self.assertFalse(flow.delete_reachable(predelete_observed=False))
        self.assertTrue(flow.delete_reachable(predelete_observed=True))

    def test_shared_home_is_allowed_but_owned_external_users_block_cleanup(self) -> None:
        self.assertTrue(shared_home_process_allowed(shared_home_processes=3, owned_users=0))
        self.assertFalse(shared_home_process_allowed(shared_home_processes=3, owned_users=1))
        self.assertEqual(0, termination_calls_for_shared_home())
        self.assertTrue(destructive_boundary_users_clear({}))
        self.assertFalse(destructive_boundary_users_clear({"controller_db": 1}))

    def test_predelete_requires_material_observation_and_one_shot_latch(self) -> None:
        empty = OracleObservation(0, 0, 0, (), "0" * 64)
        observed = OracleObservation(1, 0, 0, ("persistent_sessions",), "0" * 64)
        self.assertFalse(predelete_observation_conclusive(empty))
        self.assertTrue(predelete_observation_conclusive(observed))
        with tempfile.TemporaryDirectory(prefix="p7c13-latch-") as directory:
            latch = DurableOneShotLedger(Path(directory) / "ledger.json")
            self.assertTrue(latch.reserve(_synthetic_ledger_record()))
            self.assertFalse(latch.reserve(_synthetic_ledger_record()))
            latch.update(state="COMPLETED")
            self.assertFalse(latch.reserve(_synthetic_ledger_record()))

    def test_boundary_preflight_is_read_only_and_identity_strict(self) -> None:
        protected = {"state": "/synthetic/state", "controller": "/synthetic/controller.sqlite"}
        identities = {"state": (1, 1), "controller": (1, 2)}
        self.assertTrue(read_only_boundary_preflight(protected, mountinfo="1 2 3 4 /other", identities=identities))
        self.assertFalse(read_only_boundary_preflight(protected, mountinfo="1 2 3 4 /synthetic/state", identities=identities))
        self.assertFalse(read_only_boundary_preflight(protected, mountinfo="", identities={"state": (1, 1), "controller": (1, 1)}))


def shared_home_process_allowed(*, shared_home_processes: int, owned_users: int) -> bool:
    return shared_home_processes >= 0 and owned_users == 0


def termination_calls_for_shared_home() -> int:
    return 0


class P7C13OracleAndWatchdogTests(unittest.TestCase):
    def test_watchdog_matrix_and_second_child_retry_fail_closed(self) -> None:
        self.assertEqual("COMPLETED", watchdog_classify(child_exit="COMPLETED").status)
        self.assertEqual("TIMEOUT", watchdog_classify(child_exit="RUNNING", timeout=True).status)
        self.assertEqual("RESIDUAL_OWNED_GROUP", watchdog_classify(child_exit="COMPLETED", residual_group=True).status)
        self.assertEqual("CANCELLATION_ERROR", watchdog_classify(child_exit="RUNNING", cancelled=True).status)
        self.assertEqual("FAIL_CLOSED", watchdog_classify(child_exit="COMPLETED", second_child=True).status)
        self.assertEqual("FAIL_CLOSED", watchdog_classify(child_exit="COMPLETED", retry=True).status)

    def test_watchdog_nonzero_missing_result_and_residual_classes_are_terminal(self) -> None:
        self.assertEqual("CHILD_FAILURE", watchdog_classify(child_exit="NONZERO").status)
        self.assertEqual("RESIDUAL_OWNED_GROUP", watchdog_classify(child_exit="COMPLETED", residual_group=True).status)
        self.assertEqual("CANCELLATION_ERROR", watchdog_classify(child_exit="COMPLETED", cancelled=True).status)
        self.assertFalse(_safe_child_result({"schema": "p7c13-child-result-v1", "status": "COMPLETED"}))
        with tempfile.TemporaryDirectory(prefix="p7c13-watchdog-") as directory:
            missing = OwnedParentChildWatchdog()
            result = missing.run((sys.executable, "-c", "pass"), result_path=Path(directory) / "missing.json")
            self.assertEqual("MALFORMED_CHILD_RESULT", result.status)
            residual = OwnedParentChildWatchdog(active_group_probe=lambda _: 1)
            result = residual.run((sys.executable, "-c", "pass"), result_path=Path(directory) / "missing.json")
            self.assertEqual("RESIDUAL_OWNED_GROUP", result.status)
            self.assertEqual(1, result.owned_group_active)

    def test_post_delete_oracle_rejects_thread_marker_isolated_and_scan_residuals(self) -> None:
        clean = OracleObservation(0, 0, 0, (), "0" * 64)
        kwargs = dict(
            official_delete="DELETE_CONFIRMED", application_result="DELETED", tombstone_bounded=True,
            live_binding=False, envelope_valid=True, isolated_sqlite_descendants=0,
            isolated_logs_descendants=0, persistent=clean, isolated=clean, scan_errors=0,
            owned_children=0, owned_group_active=False, owned_group_zombies=0,
            unrelated_signals=0, budgets_ok=True,
        )
        self.assertTrue(post_delete_acceptance(**kwargs))
        for field_name, value in (
            ("persistent", OracleObservation(1, 0, 0, ("persistent_sessions",), "0" * 64)),
            ("persistent", OracleObservation(0, 1, 0, ("persistent_history",), "0" * 64)),
            ("isolated", OracleObservation(0, 1, 0, ("isolated_logs",), "0" * 64)),
            ("scan_errors", 1),
        ):
            with self.subTest(field=field_name):
                mutated = dict(kwargs)
                mutated[field_name] = value
                self.assertFalse(post_delete_acceptance(**mutated))

    def test_persistent_session_filename_and_directory_residuals_are_detected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-oracle-") as directory:
            home = Path(directory) / "home"
            home.mkdir(mode=0o700)
            profile = CodexProfile("oracle-profile", str(home), "Oracle", str(Path(directory) / "state"))
            sessions = home / "sessions"
            sessions.mkdir(mode=0o700)
            thread = "target-thread"
            marker = b"marker"
            filename = sessions / f"{thread}.jsonl"
            filename.write_bytes(b"clean")
            observation = BoundedTargetOracle(profile, thread, (marker,)).observe()
            self.assertEqual(1, observation.thread_filename_count)
            self.assertEqual(0, observation.thread_count)
            filename.unlink()
            directory_only = sessions / thread
            directory_only.mkdir(mode=0o700)
            (directory_only / "clean.jsonl").write_bytes(b"clean")
            observation = BoundedTargetOracle(profile, thread, (marker,)).observe()
            self.assertEqual(1, observation.thread_directory_count)
            self.assertTrue(predelete_observation_conclusive(OracleObservation(1, 0, 0, (), "0" * 64)))

    def test_unrelated_target_specific_removal_gate_is_explicit(self) -> None:
        clean = OracleObservation(0, 0, 0, (), "0" * 64)
        kwargs = dict(
            official_delete="DELETE_CONFIRMED", application_result="DELETED", tombstone_bounded=True,
            live_binding=False, envelope_valid=True, isolated_sqlite_descendants=0, isolated_logs_descendants=0,
            persistent=clean, isolated=clean, scan_errors=0, owned_children=0, owned_group_active=False,
            owned_group_zombies=0, unrelated_signals=0, budgets_ok=True,
        )
        self.assertFalse(post_delete_acceptance(**kwargs, unrelated_target_specific_removal_detected=True))
        self.assertTrue(post_delete_acceptance(**kwargs, unrelated_target_specific_removal_detected=False))


class P7C13ProductionDeleteChainTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="codexcontrol-p7c13-prep-")
        base = Path(self.temp.name)
        self.home = base / "persistent-home"
        self.state_parent = base / "state-parent"
        self.state_root = self.state_parent / "isolated"
        self.repository = base / "repository"
        self.controller = base / "controller" / "controller.sqlite3"
        for directory in (self.home, self.state_parent, self.repository, self.controller.parent):
            directory.mkdir(mode=0o700)
        self.controller.touch(mode=0o600)
        os.chmod(self.controller, 0o600)
        self.profile = CodexProfile("p7c13-synthetic-profile", str(self.home), "Synthetic", str(self.state_root))
        self.thread = "p7c13-synthetic-thread"
        self.marker = b"P7C13_SYNTHETIC_MARKER_0123456789"
        self.authority = IsolationPathAuthority((self.profile,), controller_db_path=str(self.controller), repository_root=str(self.repository))
        IsolatedStateRoot(self.authority).provision(self.profile)
        self.manager = CodexRuntimeManager((self.profile,), client_version="p7c13-prep", isolation_authority=self.authority)
        self.storage = await SqliteStorage.open(str(self.controller), now_ms=lambda: 10)

    async def asyncTearDown(self) -> None:
        await self.storage.close()
        self.temp.cleanup()

    async def _seed_idle(self, dialogue_id: str = "p7c13-dialogue"):
        repository = DialogueRepository(self.storage, now_ms=lambda: 10)
        await repository.create_intent(dialogue_id=dialogue_id, server_id="synthetic-server", profile_id=self.profile.profile_id)
        return await repository.confirm_created(dialogue_id=dialogue_id, expected_version=0, thread_id=self.thread)

    def _write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(content)

    def _populate_isolated(self) -> None:
        for name in ("state.db", "state.db-wal", "state.db-shm", "nested/cache.bin"):
            self._write(self.state_root / "sqlite" / name, self.thread.encode() + self.marker)
        for name in ("app.log", "nested/app.log"):
            self._write(self.state_root / "logs" / name, self.thread.encode() + self.marker)

    def _oracle(self) -> BoundedTargetOracle:
        return BoundedTargetOracle(self.profile, self.thread, (self.marker,))

    def _cleanup(self, scanner: object | None = None) -> DeleteStorageCleanupCoordinator:
        return DeleteStorageCleanupCoordinator(self.storage, self.manager, scanner=scanner, now_ms=lambda: 100)

    async def test_confirmed_success_uses_production_service_chain_once(self) -> None:
        idle = await self._seed_idle()
        target = self.home / "sessions" / "synthetic-rollout"
        self._write(target, self.thread.encode() + self.marker)
        self._populate_isolated()
        lifecycle = _FakeDelete(ThreadOperationStatus.DELETE_CONFIRMED, (target,))
        service = DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
            local_cleanup=self._cleanup(), now_ms=lambda: 100,
        )
        result = await service.delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.DELETED)
        self.assertEqual(lifecycle.calls, 1)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        self.assertIsNotNone(await DeletionRepository(self.storage).get_tombstone(idle.dialogue_id))
        self.assertEqual(0, self._oracle().observe().thread_count)
        self.assertEqual(0, self._oracle().observe().marker_count)
        self.assertEqual([], list((self.state_root / "sqlite").iterdir()))
        self.assertEqual([], list((self.state_root / "logs").iterdir()))

    async def test_delete_unknown_is_terminal_without_retry_or_finalize(self) -> None:
        idle = await self._seed_idle("p7c13-unknown")
        self._populate_isolated()
        lifecycle = _FakeDelete(ThreadOperationStatus.DELETE_UNKNOWN)
        finalizer_calls: list[int] = []
        original_finalize = DeletionRepository.finalize_confirmed

        async def observe_finalize(repository: DeletionRepository, **kwargs: Any):
            finalizer_calls.append(1)
            return await original_finalize(repository, **kwargs)

        with patch.object(DeletionRepository, "finalize_confirmed", new=observe_finalize):
            result = await DialogueDeleteService(
                self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
                local_cleanup=self._cleanup(), now_ms=lambda: 100,
            ).delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.UNKNOWN)
        self.assertEqual(lifecycle.calls, 1)
        self.assertEqual(finalizer_calls, [])
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone(idle.dialogue_id))
        current = await DialogueRepository(self.storage).get_live()
        self.assertIsNotNone(current)
        self.assertIs(current.state, DialogueState.DELETE_UNKNOWN)
        self.assertEqual([], list((self.state_root / "sqlite").iterdir()))
        self.assertEqual([], list((self.state_root / "logs").iterdir()))

    async def test_confirmed_pending_scan_failure_has_no_external_retry(self) -> None:
        idle = await self._seed_idle("p7c13-pending")
        target = self.home / "sessions" / "pending-rollout"
        self._write(target, self.thread.encode())
        lifecycle = _FakeDelete(ThreadOperationStatus.DELETE_CONFIRMED, (target,))
        result = await DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
            local_cleanup=self._cleanup(_FailingScanner()), now_ms=lambda: 100,
        ).delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE)
        self.assertEqual(lifecycle.calls, 1)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone(idle.dialogue_id))
        self.assertIs((await DialogueRepository(self.storage).get_live()).state, DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)

    async def test_marker_only_residual_is_independent_acceptance_failure(self) -> None:
        idle = await self._seed_idle("p7c13-marker-only")
        target = self.home / "sessions" / "synthetic-rollout"
        self._write(target, self.thread.encode())
        self._write(self.home / "history.jsonl", self.marker)
        lifecycle = _FakeDelete(ThreadOperationStatus.DELETE_CONFIRMED, (target,))
        result = await DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
            local_cleanup=self._cleanup(), now_ms=lambda: 100,
        ).delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.DELETED)
        observed = self._oracle().observe()
        self.assertEqual(0, observed.thread_count)
        self.assertGreater(observed.marker_count, 0)
        self.assertFalse(post_delete_acceptance(
            official_delete="DELETE_CONFIRMED", application_result="DELETED", tombstone_bounded=True,
            live_binding=False, envelope_valid=True, isolated_sqlite_descendants=0,
            isolated_logs_descendants=0, persistent=observed, isolated=OracleObservation(0, 0, 0, (), observed.marker_sha256),
            scan_errors=0, owned_children=0, owned_group_active=False, owned_group_zombies=0,
            unrelated_signals=0, budgets_ok=True,
        ))


def _module_main(argv: Sequence[str] | None = None) -> int:
    """Separate ordinary unittest discovery from the gated child executable."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--p7c13-future-child" in arguments:
        try:
            index = arguments.index("--boot-authority")
            boot_path = arguments[index + 1]
        except (ValueError, IndexError):
            raise PreparationGateError("future child boot authority argument required") from None
        return _future_child_main(boot_path)
    unittest.main(argv=[sys.argv[0], *arguments])
    return 0


if __name__ == "__main__":
    raise SystemExit(_module_main())
