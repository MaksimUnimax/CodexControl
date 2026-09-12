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
import inspect
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
from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalKind,
    ApprovalRequest,
    ApprovalHandlingStatus,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.model_catalog import (
    CodexModelCatalog,
    CodexModelCatalogAdapter,
)
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
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
REPAIR3_BASE_HEAD = "aae95407650c10b16387bbe4a27cec8bd96efe2b"
REPAIR4_BASE_HEAD = "86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d"
P7C13_BASE_SHA = REPAIR4_BASE_HEAD
P7C13_BASE_TREE = "2968187b6300e1ed03e336340aa906c199819d48"
PRIOR_HARNESS_BLOB = "61853860ed0955df6119edb288d22573299cd1b3"
P7C12_MATCHER_BLOB = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"
ORIGINAL_HARNESS_BLOB = "a6962a14ffd4c10d6e4ff072cd24622077f839c2"
ARCHITECT_MAIN_HEAD = "2b9970212c75d873ab4dcb25ac1251dbb5e3a98a"
ARCHITECT_MAIN_TREE = "bd7e027d014401e45c4149fdf1f3db3f020100b3"
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
TURN3_PROMPT_NO_RETRY = "Do not retry."
REAL_STAGE_TIMEOUTS = {
    "runtime_acquire_generation_1": 30.0,
    "model_list": 20.0,
    "thread_start": 30.0,
    "turn1_start_terminal": 60.0,
    "runtime_shutdown_generation_1": 30.0,
    "runtime_acquire_generation_2": 30.0,
    "thread_resume": 30.0,
    "turn2_start_terminal": 60.0,
    "turn3_start_approval_terminal": 90.0,
    "turn4_start": 30.0,
    "turn4_active_observation": 5.0,
    "turn4_interrupt_terminal": 45.0,
    "runtime_shutdown_before_scan": 30.0,
    "controller_open_binding": 30.0,
    "canonical_application_delete": 60.0,
    "final_runtime_local_convergence": 30.0,
}
REAL_WATCHDOG_HARD_DEADLINE = sum(REAL_STAGE_TIMEOUTS.values()) + 60.0
REAL_WATCHDOG_TERM_GRACE = 5.0
REAL_WATCHDOG_KILL_GRACE = 5.0
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


def _current_source_authority() -> tuple[str, str, str, bool]:
    """Return source authority and reject both tracked worktree/index drift."""
    repository = Path(__file__).resolve().parents[2]
    def git(*arguments: str) -> str:
        completed = subprocess.run(
            ("git", *arguments), cwd=repository, check=True,
            capture_output=True, text=True,
        )
        return completed.stdout.strip()
    head = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    harness_blob = git("hash-object", str(Path(__file__).resolve()))
    worktree_clean = subprocess.run(("git", "diff", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
    index_clean = subprocess.run(("git", "diff", "--cached", "--quiet", "HEAD", "--", "."), cwd=repository).returncode == 0
    clean = worktree_clean and index_clean
    return head, tree, harness_blob, clean


async def _await_owned(awaitable: Any, *, timeout: float, stage: str, convergence: float | None = None) -> Any:
    """Own one potentially blocking operation through bounded convergence."""
    if type(timeout) not in (int, float) or timeout <= 0:
        raise PreparationGateError(f"{stage} timeout invalid")
    task = awaitable if isinstance(awaitable, asyncio.Task) else asyncio.create_task(awaitable)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
    except asyncio.TimeoutError as error:
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=convergence if convergence is not None else min(timeout, 5.0))
        except (asyncio.CancelledError, asyncio.TimeoutError):
            raise PreparationGateError(f"{stage} nonconvergent") from error
        raise PreparationGateError(f"{stage} timeout") from error


def future_real_cli_entrypoint(
    *, environ: Mapping[str, str] | None = None, executor: FutureRealExecutor | None = None,
) -> Any:
    """The direct future parent mode; source gate precedes any ledger effect."""
    environment = dict(os.environ if environ is None else environ)
    token = environment.get(FUTURE_GATE_ENV, "")
    contract = FutureArchitectContract(
        authorization_token=token,
        expected_head=environment.get("P7C13_EXPECTED_HEAD", ""),
        expected_tree=environment.get("P7C13_EXPECTED_TREE", ""),
        expected_harness_blob=environment.get("P7C13_EXPECTED_HARNESS_BLOB", ""),
    )
    head, tree, harness_blob, clean = _current_source_authority()
    if not clean:
        raise PreparationGateError("tracked source drift")
    return future_real_entrypoint(
        environ=environment, contract=contract, current_head=head,
        current_tree=tree, current_harness_blob=harness_blob, executor=executor,
    )


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

    def __init__(self, profile: CodexProfile, thread_id: str, markers: Sequence[bytes], *, max_bytes: int = 4 * 1024 * 1024, families: Sequence[str] | None = None) -> None:
        self.profile = profile
        self.thread = thread_id.encode()
        self.markers = tuple(markers)
        self.max_bytes = max_bytes
        self.families = frozenset(families) if families is not None else None

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
            if self.families is not None and family not in self.families:
                continue
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


def bounded_descendant_observation(root: Path) -> tuple[int, int, int, int]:
    """Derive regular/special/symlink/scan-error counts without following links."""
    regular = special = symlinks = errors = 0
    if not root.exists():
        return 0, 0, 0, 0
    pending = [root]
    while pending:
        current = pending.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            errors += 1
            continue
        for entry in entries:
            try:
                if entry.is_symlink():
                    symlinks += 1
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    regular += 1
                else:
                    special += 1
            except OSError:
                errors += 1
    return regular, special, symlinks, errors


def derived_unrelated_removal_fact(before: Mapping[str, tuple[int, int]], after: Mapping[str, tuple[int, int]], *, target_paths: set[str]) -> bool:
    """Attribute removal only when an exact unrelated path disappeared."""
    removed = {path for path in before if path not in after and path not in target_paths}
    return bool(removed)


def target_metadata_snapshot(profile: CodexProfile, thread_id: str) -> tuple[dict[str, tuple[int, int]], set[str]]:
    """Capture metadata only, preserving attribution-safe shared-home evidence."""
    snapshot: dict[str, tuple[int, int]] = {}
    target_paths: set[str] = set()
    roots = (Path(profile.codex_home) / "sessions", Path(profile.codex_home) / "history.jsonl")
    pending = list(roots)
    seen = 0
    while pending and seen < 4096:
        root = pending.pop()
        try:
            value_root = root.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            continue
        if stat.S_ISLNK(value_root.st_mode):
            continue
        if stat.S_ISDIR(value_root.st_mode):
            try:
                pending.extend(Path(entry.path) for entry in os.scandir(root) if not entry.is_symlink())
            except OSError:
                continue
            continue
        if not stat.S_ISREG(value_root.st_mode):
            continue
        seen += 1
        for path in (root,):
            try:
                value = path.lstat()
            except OSError:
                continue
            snapshot[str(path)] = (value.st_dev, value.st_ino)
            if thread_id in str(path):
                target_paths.add(str(path))
    return snapshot, target_paths


def map_terminal_recovery_class(*, official_status: str | None, application_status: str | None) -> str:
    """Map finite outcomes without retry or success inference."""
    if official_status == ThreadOperationStatus.DELETE_UNKNOWN.value:
        return "UNKNOWN"
    if application_status == DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE.value:
        return "CONFIRMED_PENDING"
    if official_status == ThreadOperationStatus.DELETE_CONFIRMED.value and application_status == DialogueDeleteStatus.DELETED.value:
        return "COMPLETED"
    return "FAILED"


def post_delete_acceptance(
    *, official_delete: str, application_result: str, tombstone_bounded: bool,
    live_binding: bool, envelope_valid: bool, isolated_sqlite_descendants: int,
    isolated_logs_descendants: int, persistent: OracleObservation,
    isolated: OracleObservation, scan_errors: int, owned_children: int | None,
    owned_group_active: bool | None, owned_group_zombies: int | None,
    unrelated_signals: int | None, budgets_ok: bool,
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
        owned_children is None or owned_children == 0,
        owned_group_active is None or not owned_group_active,
        owned_group_zombies is None or owned_group_zombies == 0,
        unrelated_signals is None or unrelated_signals == 0,
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
    group_scan_errors: int = 0
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


def inspect_owned_process_group(pgid: int, *, proc_root: Path = Path("/proc")) -> tuple[int, int, int]:
    """Bounded active/zombie/error observation for one exact owned PGID."""
    if type(pgid) is not int or pgid <= 1:
        raise PreparationGateError("owned PGID invalid")
    try:
        pids = tuple(int(name) for name in os.listdir(proc_root) if name.isdigit())
    except OSError as error:
        raise PreparationGateError("process group scan failed") from error
    active = zombies = errors = 0
    for pid in pids:
        try:
            raw = (proc_root / str(pid) / "stat").read_bytes()
            closing = raw.rfind(b") ")
            fields = raw[closing + 2:].split() if closing > 0 else ()
            if len(fields) < 4:
                raise ValueError("stat shape")
            state = fields[0].decode("ascii")
            member_pgid = int(fields[2])
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError, ValueError):
            errors += 1
            continue
        if member_pgid != pgid:
            continue
        if state == "Z":
            zombies += 1
        else:
            active += 1
    return active, zombies, errors


def _real_active_group_probe(pgid: int) -> int:
    active, _, errors = inspect_owned_process_group(pgid)
    return -1 if errors else active


def _real_zombie_group_probe(pgid: int) -> int:
    _, zombies, errors = inspect_owned_process_group(pgid)
    return -1 if errors else zombies


def _real_group_scan_error_probe(pgid: int) -> int:
    return inspect_owned_process_group(pgid)[2]


MAX_LEDGER_BYTES = 8192
LEDGER_SCHEMA = "p7c13-repair4-v1"


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


def _safe_child_result(value: Any, *, boot: Mapping[str, Any] | None = None) -> bool:
    """Single final child-result validator used by both watchdog and parent.

    The former ``p7c13-child-result-v1`` record is intentionally not accepted.
    A boot-bound validator is required for PASS classification; a missing boot
    is useful only for structural watchdog tests and can never authorize PASS.
    """
    if boot is None:
        return False
    return _safe_child_result_authority(value, boot)


# The boot and result records are intentionally separate authorities.  The
# parent owns the boot record; the child owns the result record.  Both are
# bounded, root-only JSON files and contain hashes/classes rather than raw
# recovery identities.
BOOT_SCHEMA = "p7c13-repair3-boot-v1"
CHILD_RESULT_SCHEMA = "p7c13-repair4-child-result-v1"
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
    "runtime_child_quiescent", "parent_process_group_quiescent",
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
    if value.get("schema") != CHILD_RESULT_SCHEMA or value.get("status") not in {"PASS", "FAILED", "UNKNOWN", "CONFIRMED_PENDING", "TIMEOUT"}:
        return False
    if value.get("source_head") != boot.get("source_head") or value.get("source_tree") != boot.get("source_tree") or value.get("harness_blob") != boot.get("harness_blob") or value.get("run_id_hash") != boot.get("run_id_hash"):
        return False
    if type(value.get("verdict")) is not bool or type(value.get("runtime_child_quiescent")) is not bool:
        return False
    if value.get("parent_process_group_quiescent") is not None and type(value.get("parent_process_group_quiescent")) is not bool:
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


def _child_result_file_is_valid(path: Path, boot: Mapping[str, Any]) -> bool:
    """The watchdog and parent use this exact bounded final authority."""
    try:
        return _safe_child_result_authority(
            _safe_json_file(path, max_bytes=MAX_CHILD_RESULT_BYTES,
                            expected_keys=CHILD_RESULT_KEYS, label="child result"),
            boot,
        )
    except (OSError, UnicodeError, PreparationGateError, json.JSONDecodeError):
        return False


def child_result_passes(value: Mapping[str, Any], boot: Mapping[str, Any]) -> bool:
    """Strict parent PASS predicate; FAILED/UNKNOWN are evidence only."""
    if not _safe_child_result_authority(value, boot):
        return False
    if value["status"] != "PASS" or value["verdict"] is not True or value["runtime_child_quiescent"] is not True:
        return False
    expected = {key: limit for key, limit in FROZEN_EFFECT_BUDGET.items()}
    if any(value["effect_counts"].get(key, 0) != expected[key] for key in (
        "new_threads", "model/list", "thread/start", "thread/resume", "turn/start",
        "approval_responses", "allow_responses", "turn/interrupt", "thread/delete",
    )):
        return False
    if any(value["effect_counts"].get(key, 0) != 0 for key in (
        "thread/read", "thread/list", "second_child", "real_retry", "telegram",
    )):
        return False
    if any(type(item) is not int or item != 0 for item in value["residual_counts"].values()):
        return False
    return True


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

    def __init__(self, *, process_factory: Callable[..., Any] = subprocess.Popen, signal_group: Callable[[int, int], None] | None = None, active_group_probe: Callable[[int], int] | None = None, zombie_group_probe: Callable[[int], int] | None = None, group_scan_error_probe: Callable[[int], int] | None = None, result_validator: Callable[[Path], bool] | None = None) -> None:
        self.process_factory = process_factory
        self.signal_group = signal_group or os.killpg
        self.active_group_probe = active_group_probe or _real_active_group_probe
        self.zombie_group_probe = zombie_group_probe or _real_zombie_group_probe
        self.group_scan_error_probe = group_scan_error_probe or _real_group_scan_error_probe
        self.result_validator = result_validator
        self.child_count = 0
        self.retry_count = 0
        self.owned_pid: int | None = None
        self.owned_pgid: int | None = None
        self.signals: list[int] = []

    def run(self, command: Sequence[str], *, result_path: str | Path, timeout_seconds: float = REAL_WATCHDOG_HARD_DEADLINE, term_grace_seconds: float = REAL_WATCHDOG_TERM_GRACE, kill_grace_seconds: float = REAL_WATCHDOG_KILL_GRACE, result_validator: Callable[[Path], bool] | None = None) -> WatchdogResult:
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
                    process.wait(timeout=kill_grace_seconds)
            active = self.active_group_probe(self.owned_pgid)
            zombies = self.zombie_group_probe(self.owned_pgid)
            scan_errors = self.group_scan_error_probe(self.owned_pgid)
            if active < 0 or zombies < 0 or scan_errors < 0:
                raise PreparationGateError("owned process group observation invalid")
            if active or zombies or scan_errors:
                status = "RESIDUAL_OWNED_GROUP"
            validator = result_validator or self.result_validator
            try:
                result_valid = False if validator is None else bool(validator(Path(result_path)))
            except Exception:
                result_valid = False
            if status == "COMPLETED" and not result_valid:
                status = "MALFORMED_CHILD_RESULT"
            return WatchdogResult(status, child_count=1, child_result_valid=result_valid, owned_group_active=active, owned_group_zombies=zombies, group_scan_errors=scan_errors, signals_sent=tuple(self.signals))
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

    def __init__(self, *, ledger: DurableOneShotLedger, watchdog: OwnedParentChildWatchdog, child_command: Sequence[str], result_path: str | Path, record: Mapping[str, Any], boot_path: str | Path | None = None, child_factory: Callable[[Path], Sequence[str]] | None = None, run_paths: Mapping[str, str] | None = None, fresh_production: bool = False) -> None:
        self.ledger, self.watchdog = ledger, watchdog
        self.child_command, self.result_path, self.record = tuple(child_command), Path(result_path), dict(record)
        self.boot_path = Path(boot_path) if boot_path is not None else self.ledger.path.with_name("p7c13-test-boot.json")
        self.run_paths = dict(run_paths or {})
        self.fresh_production = fresh_production
        self.child_factory = child_factory
        self.calls = 0
        self.order: list[str] = []

    @classmethod
    def production(cls, contract: FutureArchitectContract) -> "PreparedFutureRealExecutor":
        authority_root = Path("/root/.codexcontrol")
        ledger_path = authority_root / "p7c13-one-shot.json"
        result_path = authority_root / "p7c13-child-result-pending.json"
        record = {
            "schema": LEDGER_SCHEMA, "state": "RESERVED", "source_head": contract.expected_head,
            "source_tree": contract.expected_tree, "harness_blob": contract.expected_harness_blob,
            "run_id_hash": _sha256(secrets.token_bytes(32)), "path_hashes": {
                "ledger": _sha256(str(ledger_path)),
            }, "effect_counts": {}, "recovery": {},
        }
        return cls(ledger=DurableOneShotLedger(ledger_path), watchdog=OwnedParentChildWatchdog(), child_command=(), result_path=result_path, record=record, fresh_production=True)

    def _select_fresh_run_paths(self) -> None:
        authority_root = Path("/root/.codexcontrol")
        try:
            root_stat = authority_root.lstat()
        except OSError as error:
            raise PreparationGateError("P7C13 authority root unavailable") from error
        if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != 0 or stat.S_IMODE(root_stat.st_mode) & 0o022:
            raise PreparationGateError("P7C13 authority root unsafe")
        run_id = secrets.token_hex(24)
        paths = {
            "isolated_root": str(Path("/root") / f"p7c13-isolated-{run_id}"),
            "controller_db": str(authority_root / f"p7c13-controller-{run_id}.sqlite3"),
            "workdir": str(Path("/root") / f"p7c13-work-{run_id}"),
            "approval_target": str(Path("/root") / f"p7c13-approval-{run_id}"),
        }
        self.result_path = authority_root / f"p7c13-child-result-{run_id}.json"
        self.boot_path = authority_root / f"p7c13-boot-{run_id}.json"
        fresh_run_owned_paths(
            isolated_root=Path(paths["isolated_root"]), controller_db=Path(paths["controller_db"]),
            workdir=Path(paths["workdir"]), approval_target=Path(paths["approval_target"]),
            ledger_path=self.ledger.path, persistent_home=Path(PERSISTENT_HOME),
            repository=Path.cwd(),
        )
        self.run_paths = paths

    def _boot_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize only safe authority; raw IDs are never synthesized here."""
        path_hashes = record.get("path_hashes", {})
        test_root = self.ledger.path.parent / f"p7c13-test-{record['run_id_hash'][:16]}"
        paths = self.run_paths or {
            "isolated_root": str(test_root / "isolated"),
            "controller_db": str(test_root / "controller.sqlite3"),
            "workdir": str(test_root / "work"),
            "approval_target": f"/root/p7c13-approval-test-{record['run_id_hash'][:16]}",
        }
        return {
            "schema": BOOT_SCHEMA,
            "source_head": record["source_head"], "source_tree": record["source_tree"], "harness_blob": record["harness_blob"],
            "run_id_hash": record["run_id_hash"], "profile_id": "p7c13-future-profile",
            "codex_home": PERSISTENT_HOME, "isolated_root": paths["isolated_root"],
            "controller_db": paths["controller_db"], "workdir": paths["workdir"],
            "approval_target": paths["approval_target"], "ledger_path": str(self.ledger.path),
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
        if self.fresh_production:
            self._select_fresh_run_paths()
            self.order.append("fresh_paths")
        boot_record = self._boot_record(record)
        boot_authority = RootOnlyBootAuthority(self.boot_path)
        boot_authority.create(boot_record)
        boot_authority.read(expected=boot_record)
        self.order.append("boot")
        command = tuple(self.child_factory(self.boot_path) if self.child_factory is not None else self.child_command)
        if not command and self.child_factory is None:
            command = (
                sys.executable, "-m", "tests.real.test_p7_c13_final_hard_delete_acceptance",
                "--p7c13-future-child", "--boot-authority", str(self.boot_path),
            )
        self.order.append("child")
        result = self.watchdog.run(
            command, result_path=self.result_path,
            timeout_seconds=REAL_WATCHDOG_HARD_DEADLINE,
            term_grace_seconds=REAL_WATCHDOG_TERM_GRACE,
            kill_grace_seconds=REAL_WATCHDOG_KILL_GRACE,
            result_validator=lambda path: _child_result_file_is_valid(path, boot_record),
        )
        state = "COMPLETED" if result.status == "COMPLETED" and result.child_result_valid and result.group_scan_errors == 0 and result.owned_group_active == 0 and result.owned_group_zombies == 0 else "FAILED"
        if state == "COMPLETED":
            try:
                final_result = read_child_result(self.result_path, boot=boot_record)
                if not child_result_passes(final_result, boot_record):
                    state = "FAILED"
                    result = WatchdogResult("CHILD_FAILURE", child_count=result.child_count, child_result_valid=True, owned_group_active=result.owned_group_active, owned_group_zombies=result.owned_group_zombies, group_scan_errors=result.group_scan_errors, signals_sent=result.signals_sent)
            except PreparationGateError:
                state = "FAILED"
                result = WatchdogResult("MALFORMED_CHILD_RESULT", child_count=result.child_count, child_result_valid=False, owned_group_active=result.owned_group_active, owned_group_zombies=result.owned_group_zombies, group_scan_errors=result.group_scan_errors, signals_sent=result.signals_sent)
        if state == "FAILED" and self.result_path.exists():
            try:
                child_status = read_child_result(self.result_path, boot=boot_record).get("status")
                if child_status in {"UNKNOWN", "CONFIRMED_PENDING"}:
                    state = child_status
            except PreparationGateError:
                pass
        self.ledger.update(state=state, recovery={"child_result": _sha256(str(self.result_path)), "parent_group_scan_errors": result.group_scan_errors})
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

    def single_protocol_allow(self, callback: Callable[[], Any]) -> Any:
        """Reserve both accounting facts before one bridge callback."""
        self.budget.record("approval_responses")
        self.budget.record("allow_responses")
        return callback()


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
        # Classification is local.  The response and ALLOW reservations are
        # made before either effect callback can be entered.
        self.effects.single_protocol_allow(self.approval)
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
    runtime_child_quiescent: bool = True


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


class OfficialDeleteObservation:
    """Independent P1.9 observation kept separate from application status."""

    def __init__(self, lifecycle: CodexThreadLifecycleAdapter) -> None:
        self.lifecycle = lifecycle
        self.calls = 0
        self.status: ThreadOperationStatus | None = None
        self.binding: ThreadBinding | None = None

    async def delete(self, *, binding: ThreadBinding) -> ThreadOperationResult:
        self.calls += 1
        result = await self.lifecycle.delete(binding=binding)
        self.status = result.status
        self.binding = result.binding
        return result


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
    lifecycle: Any | None = None,
) -> DialogueDeleteService:
    """Assemble the accepted application chain; the service owns the only delete."""
    lifecycle = lifecycle or CodexThreadLifecycleAdapter(runtime_manager, catalog)
    cleanup = DeleteStorageCleanupCoordinator(storage, runtime_manager)
    return DialogueDeleteService(
        storage, server_id=server_id, thread_lifecycle=lifecycle, local_cleanup=cleanup,
    )


def c11_explicit_escalation_prompt(target: str) -> str:
    """Source-backed Turn-3 stimulus; no default attempt or retry is allowed."""
    if not isinstance(target, str) or not target.startswith("/") or "\0" in target:
        raise PreparationGateError("approval target authority invalid")
    return (
        "Make exactly one shell-command tool call, and make it your first and only tool call. "
        f"On that call perform exactly one command operation: touch {target}. "
        "Before execution request approval with sandbox_permissions=require_escalated and include a "
        "short justification for why elevation is requested. Do not first try this command with "
        "default sandbox permissions. Do not use apply_patch, Python, a file-editing tool, or network "
        "access. Do not substitute another path or alternative command. Do not issue a second tool "
        "call. If approval is denied, stop immediately. Do not retry."
    )


class RootOnlyWireCommandAuthority:
    """Immutable first-capture root-only authority used before C12 projection."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def capture_once(self, *, request: Any, request_ordinal: int, target: str) -> dict[str, Any]:
        if self.path.exists():
            raise PreparationGateError("wire authority already captured")
        commands = [line[len("command: "):] for line in request.context_lines if line.startswith("command: ")]
        cwds = [line[len("cwd: "):] for line in request.context_lines if line.startswith("cwd: ")]
        if request.kind is not ApprovalKind.COMMAND_EXECUTION or len(commands) != 1 or len(cwds) != 1:
            raise PreparationGateError("wire request shape invalid")
        cwd = os.path.normpath(os.path.abspath(cwds[0]))
        record = {
            "format": 1,
            "request_ordinal": request_ordinal,
            "local_sequence": request.local_sequence,
            "request_kind": request.kind.value,
            "thread_id_sha256": _sha256(request.thread_id or ""),
            "turn_id_sha256": _sha256(request.turn_id or ""),
            "cwd_sha256": _sha256(cwd),
            "target_sha256": _sha256(target),
            "command_plaintext": commands[0],
            "command_sha256": _sha256(commands[0]),
            "capture_status": "CAPTURED_ROOT_ONLY",
        }
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError as error:
            raise PreparationGateError("wire authority already captured") from error
        try:
            os.fchmod(fd, 0o600)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        return self.read()

    def read(self) -> dict[str, Any]:
        value = _safe_json_file(
            self.path, max_bytes=MAX_CHILD_RESULT_BYTES,
            expected_keys=frozenset({
                "format", "request_ordinal", "local_sequence", "request_kind",
                "thread_id_sha256", "turn_id_sha256", "cwd_sha256", "target_sha256",
                "command_plaintext", "command_sha256", "capture_status",
            }), label="wire authority",
        )
        if value["format"] != 1 or value["request_kind"] != ApprovalKind.COMMAND_EXECUTION.value or value["capture_status"] != "CAPTURED_ROOT_ONLY":
            raise PreparationGateError("wire authority schema invalid")
        if type(value["request_ordinal"]) is not int or type(value["local_sequence"]) is not int:
            raise PreparationGateError("wire authority sequence invalid")
        if not isinstance(value["command_plaintext"], str) or _sha256(value["command_plaintext"]) != value["command_sha256"]:
            raise PreparationGateError("wire authority command hash invalid")
        return value


class RootOnlyApprovalRecoveryJournal:
    """Bounded run-owned request/response journal, never used as wire authority."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: Mapping[str, Any]) -> None:
        safe = dict(record)
        if len(json.dumps(safe, sort_keys=True, separators=(",", ":"))) > 2048:
            raise PreparationGateError("approval journal record too large")
        records = self.read() if self.path.exists() else []
        records.append(safe)
        if len(records) > 8:
            raise PreparationGateError("approval journal cardinality invalid")
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        if self.path.exists():
            st = os.lstat(self.path)
            if stat.S_ISLNK(st.st_mode) or st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
                raise PreparationGateError("approval journal unsafe")
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
                if (os.fstat(fd).st_dev, os.fstat(fd).st_ino) != (st.st_dev, st.st_ino):
                    raise PreparationGateError("approval journal identity drift")
                os.write(fd, payload)
                os.fsync(fd)
            except OSError as error:
                raise PreparationGateError("approval journal write failed") from error
            finally:
                try:
                    os.close(fd)
                except (UnboundLocalError, OSError):
                    pass
            return
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(self.path, flags)
            try:
                data = os.read(fd, MAX_CHILD_RESULT_BYTES + 1)
            finally:
                os.close(fd)
            records = json.loads(data.decode())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise PreparationGateError("approval journal invalid") from error
        if not isinstance(records, list) or any(not isinstance(item, dict) for item in records):
            raise PreparationGateError("approval journal schema invalid")
        return records


def _correlate_root_wire(
    request: Any, *, authority: RootOnlyWireCommandAuthority, expected_target: str,
    request_ordinal: int, expected_thread: str, expected_turn: str, expected_cwd: str,
) -> tuple[c12.CapturedRequest, c12.ExpectedAuthority, c12.CorrelatedWireRecord] | None:
    """Validate immutable wire facts, then and only then project C12 inputs."""
    try:
        wire = authority.read()
    except PreparationGateError:
        return None
    if (
        wire["request_ordinal"] != request_ordinal
        or wire["local_sequence"] != request.local_sequence
        or wire["request_kind"] != request.kind.value
        or wire["thread_id_sha256"] != _sha256(expected_thread)
        or wire["turn_id_sha256"] != _sha256(expected_turn)
        or wire["cwd_sha256"] != _sha256(os.path.normpath(os.path.abspath(expected_cwd)))
        or wire["target_sha256"] != _sha256(expected_target)
    ):
        return None
    command = wire["command_plaintext"]
    request_fixture = c12.CapturedRequest(
        request.kind.name if isinstance(request.kind, ApprovalKind) else str(request.kind),
        request_ordinal, request.local_sequence, wire["thread_id_sha256"],
        wire["turn_id_sha256"], wire["cwd_sha256"], wire["command_sha256"],
    )
    expected = c12.ExpectedAuthority(
        ApprovalKind.COMMAND_EXECUTION.name, request_ordinal, request.local_sequence,
        wire["thread_id_sha256"], wire["turn_id_sha256"], wire["cwd_sha256"],
        expected_target, wire["command_sha256"],
    )
    correlation = c12.CorrelatedWireRecord(
        ApprovalKind.COMMAND_EXECUTION.name, request_ordinal, request.local_sequence,
        wire["thread_id_sha256"], wire["turn_id_sha256"], wire["cwd_sha256"],
        wire["target_sha256"], command, wire["command_sha256"],
    )
    return request_fixture, expected, correlation


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


@dataclass(frozen=True)
class Turn4GateResult:
    """Content-free final facts for the owned Turn-4 observation window."""

    passed: bool
    terminal: Any | None
    interrupt: Any | None
    unexpected_request_count: int
    same_tick: bool
    active_proof: bool
    request_observer_joined: bool
    terminal_waiter_joined: bool
    request_observer_class: str
    preliminary_request_done: bool


class Turn4RequestObserverClass(StrEnum):
    """Terminal classes for the observation-only Turn-4 request waiter."""

    REQUEST_OBSERVED = "REQUEST_OBSERVED"
    CANCELLED_BY_HARNESS_WITHOUT_REQUEST = "CANCELLED_BY_HARNESS_WITHOUT_REQUEST"
    OBSERVER_ERROR = "OBSERVER_ERROR"


def _turn4_task_fact(task: asyncio.Task[Any]) -> tuple[Any | None, bool]:
    """Return a completed task fact and whether it faulted/cancelled."""
    if task.cancelled():
        return None, True
    try:
        return task.result(), False
    except (asyncio.CancelledError, Exception):
        return None, True


def _classify_turn4_request_observer(
    task: asyncio.Task[Any], *, harness_cancel_requested: bool,
) -> tuple[Turn4RequestObserverClass, int, bool]:
    """Classify the request observer only after its final join has completed."""
    if not task.done():
        return Turn4RequestObserverClass.OBSERVER_ERROR, 0, True
    if task.cancelled():
        if harness_cancel_requested:
            return Turn4RequestObserverClass.CANCELLED_BY_HARNESS_WITHOUT_REQUEST, 0, False
        return Turn4RequestObserverClass.OBSERVER_ERROR, 0, True
    try:
        task.result()
    except BaseException:
        return Turn4RequestObserverClass.OBSERVER_ERROR, 0, True
    return Turn4RequestObserverClass.REQUEST_OBSERVED, 1, False


async def _join_turn4_task(task: asyncio.Task[Any], *, timeout: float, stage: str) -> None:
    """Cancel and join one owned waiter; never leave a detached task."""
    if not task.done():
        task.cancel()
    try:
        await asyncio.wait_for(task, timeout=timeout)
    except asyncio.CancelledError:
        return
    except asyncio.TimeoutError as error:
        raise PreparationGateError(f"{stage} nonconvergent") from error
    except Exception:
        # The exception is consumed here; the final gate is non-PASS.
        return


async def observe_owned_turn4(
    *, client: Any, turn_lifecycle: Any, binding: TurnBinding, budget: EffectBudget,
    active_timeout: float = REAL_STAGE_TIMEOUTS["turn4_active_observation"],
    interrupt_timeout: float = REAL_STAGE_TIMEOUTS["turn4_interrupt_terminal"],
    join_timeout: float = REAL_STAGE_TIMEOUTS["final_runtime_local_convergence"],
) -> Turn4GateResult:
    """Own terminal and protocol-request observers through Turn-4 convergence.

    The request waiter only observes/dequeues the current client's next server
    request. It has no response authority. Any completed request is therefore
    a permanent non-PASS fact, including a request racing terminal completion.
    """
    if type(active_timeout) not in (int, float) or active_timeout <= 0:
        raise PreparationGateError("Turn-4 active timeout invalid")
    terminal_task = asyncio.create_task(turn_lifecycle.wait_turn(binding))
    request_task = asyncio.create_task(client.next_server_request())
    terminal: Any | None = None
    interrupt: Any | None = None
    unexpected_request_count = 0
    same_tick = False
    active_proof = False
    observer_fault = False
    terminal_fault = False
    request_cancel_requested = False
    preliminary_request_done = False

    try:
        done, _ = await asyncio.wait(
            (terminal_task, request_task), timeout=active_timeout,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not done:
            # Give both current-run waiters one scheduler turn before
            # establishing ACTIVE/NONTERMINAL; this closes the same-slice race.
            await asyncio.sleep(0)
            done = {task for task in (terminal_task, request_task) if task.done()}

        terminal_done = terminal_task in done or terminal_task.done()
        request_done = request_task in done or request_task.done()
        if request_done:
            request_fact, observer_fault = _turn4_task_fact(request_task)
            if not observer_fault:
                # The object is intentionally not inspected or answered.
                unexpected_request_count = 1
            if terminal_done:
                same_tick = True
                terminal, terminal_fault = _turn4_task_fact(terminal_task)
            else:
                # An unexpected request can use the one exact interrupt only
                # to terminate the owned active Turn safely.
                try:
                    budget.record("turn/interrupt")
                    interrupt = await _await_owned(
                        turn_lifecycle.interrupt_turn(binding),
                        timeout=interrupt_timeout, stage="Turn-4 cleanup interrupt",
                    )
                except (PreparationGateError, Exception):
                    terminal_fault = True
                if terminal_task.done():
                    terminal, terminal_fault = _turn4_task_fact(terminal_task)
                else:
                    try:
                        terminal = await asyncio.wait_for(asyncio.shield(terminal_task), timeout=interrupt_timeout)
                    except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                        terminal_fault = True
        elif terminal_done:
            # Terminal-before-active is a fail-closed zero-interrupt result.
            terminal, terminal_fault = _turn4_task_fact(terminal_task)
            await asyncio.sleep(0)
            if request_task.done():
                _, observer_fault = _turn4_task_fact(request_task)
                if not observer_fault:
                    unexpected_request_count = 1
                same_tick = True
        else:
            active_proof = True
            budget.record("turn/interrupt")
            try:
                interrupt = await _await_owned(
                    turn_lifecycle.interrupt_turn(binding),
                    timeout=interrupt_timeout, stage="Turn-4 interrupt",
                )
            except (PreparationGateError, Exception):
                terminal_fault = True
            if terminal_task.done():
                terminal, terminal_fault = _turn4_task_fact(terminal_task)
            else:
                try:
                    terminal = await asyncio.wait_for(asyncio.shield(terminal_task), timeout=interrupt_timeout)
                except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                    terminal_fault = True
    finally:
        # The request observer remains owned through terminal convergence.
        await asyncio.sleep(0)
        # This is only a diagnostic snapshot. It is deliberately not used for
        # the final PASS predicate because a request may complete immediately
        # after this point while the owned terminal waiter is being joined.
        preliminary_request_done = request_task.done()
        if not terminal_task.done():
            await _join_turn4_task(terminal_task, timeout=join_timeout, stage="Turn-4 terminal waiter")
        # Let a request delivered while the terminal waiter was closing finish
        # its owned observer task before deciding whether cancellation wins.
        await asyncio.sleep(0)
        if not request_task.done():
            request_cancel_requested = True
            await _join_turn4_task(request_task, timeout=join_timeout, stage="Turn-4 request observer")
        request_observer_class, final_unexpected_request_count, final_observer_fault = _classify_turn4_request_observer(
            request_task, harness_cancel_requested=request_cancel_requested,
        )
        unexpected_request_count = final_unexpected_request_count
        observer_fault = observer_fault or final_observer_fault

    interrupt_ok = (
        interrupt is not None
        and getattr(interrupt, "status", None) in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED)
        and getattr(getattr(interrupt, "terminal_result", None), "status", None) is TurnTerminalStatus.FAILED
    )
    passed = (
        active_proof and not observer_fault and not terminal_fault
        and request_observer_class is Turn4RequestObserverClass.CANCELLED_BY_HARNESS_WITHOUT_REQUEST
        and unexpected_request_count == 0
        and interrupt_ok
        and getattr(terminal, "status", None) is TurnTerminalStatus.FAILED
        and terminal_task.done() and request_task.done()
    )
    return Turn4GateResult(
        passed=passed, terminal=terminal, interrupt=interrupt,
        unexpected_request_count=unexpected_request_count, same_tick=same_tick,
        active_proof=active_proof, request_observer_joined=request_task.done(),
        terminal_waiter_joined=terminal_task.done(),
        request_observer_class=request_observer_class,
        preliminary_request_done=preliminary_request_done,
    )


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
        self.effects.single_protocol_allow(self.seams.approval_response)
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


@dataclass
class ProductionRealChildOrchestrator:
    """Production-default adapter assembly; no synthetic business seam."""

    profile: CodexProfile
    boot: Mapping[str, Any]
    runtime_manager: CodexRuntimeManager
    catalog_adapter: CodexModelCatalogAdapter
    thread_lifecycle: CodexThreadLifecycleAdapter
    turn_lifecycle: CodexTurnLifecycleAdapter
    isolation_root: IsolatedStateRoot
    budget: EffectBudget

    async def run_async(self) -> CompleteChildResult:
        # The implementation is intentionally real-capable and derives every
        # identity below from an adapter result. Repair tests inject fakes at
        # the adapter boundary and never enter this method with real effects.
        repository_root = Path(__file__).resolve().parents[2]
        controller_root = Path(self.boot["controller_db"]).parent
        root = Path("/root/.codexcontrol")
        production_read_only_boundary_preflight({
            "persistent_home": Path(self.profile.codex_home), "repository": repository_root,
            "isolated_root": Path(self.profile.isolated_state_root),
            "isolated_sqlite": Path(self.profile.isolated_state_root) / "sqlite",
            "isolated_logs": Path(self.profile.isolated_state_root) / "logs",
            "controller_root": controller_root, "controller_db": Path(self.boot["controller_db"]),
            "workdir": Path(self.boot["workdir"]), "approval_target": Path(self.boot["approval_target"]),
            "ledger": Path(self.boot["ledger_path"]), "boot": Path(self.boot["boot_authority_path"]),
            "result": Path(self.boot["child_result_path"]),
        })
        workdir = await _await_owned(
            asyncio.to_thread(create_fresh_private_workdir, self.boot["workdir"]),
            timeout=REAL_STAGE_TIMEOUTS["thread_start"], stage="fresh workdir creation",
        )
        workdir_identity = workdir.path
        workdir_stat = Path(workdir_identity).lstat()
        workdir_identity_pair = (workdir_stat.st_dev, workdir_stat.st_ino)
        validate_stable_workdir(workdir_identity, workdir_identity_pair)
        profile_id = self.profile.profile_id
        self.isolation_root.provision(self.profile)
        self.isolation_root.validate(self.profile)
        self.budget.record("new_threads")
        runtime = await _await_owned(
            self.runtime_manager.acquire(profile_id),
            timeout=REAL_STAGE_TIMEOUTS["runtime_acquire_generation_1"], stage="runtime acquire generation 1",
        )
        self.budget.record("model/list")
        catalog = await _await_owned(
            self.catalog_adapter.get_catalog(profile_id),
            timeout=REAL_STAGE_TIMEOUTS["model_list"], stage="model list",
        )
        visible = tuple(model for model in catalog.models if not model.hidden)
        defaults = tuple(model for model in visible if model.is_default)
        if not visible or len(defaults) != 1:
            raise PreparationGateError("canonical model catalog/default invalid")
        model = defaults[0]
        reasoning_effort = catalog.validate_reasoning_effort(model.model_id, None)
        pinned_catalog = _PinnedCatalogAdapter(catalog)
        thread_lifecycle = CodexThreadLifecycleAdapter(self.runtime_manager, pinned_catalog)
        turn_lifecycle = CodexTurnLifecycleAdapter(self.runtime_manager, pinned_catalog)
        self.budget.record("thread/start")
        thread_result = await _await_owned(thread_lifecycle.start(
            profile_id, model_id=model.model_id, reasoning_effort=reasoning_effort,
            working_directory=workdir,
        ), timeout=REAL_STAGE_TIMEOUTS["thread_start"], stage="thread start")
        if thread_result.status is not ThreadOperationStatus.START_CONFIRMED or thread_result.binding is None:
            raise PreparationGateError("START_CONFIRMED required")
        thread_binding = thread_result.binding
        memory_marker, response_marker = fresh_non_secret_markers()
        self.budget.record("turn/start")
        validate_stable_workdir(workdir_identity, workdir_identity_pair)
        turn1 = await _await_owned(turn_lifecycle.start_turn(
            thread_binding=thread_binding, model_id=model.model_id,
            reasoning_effort=reasoning_effort,
            user_text=f"Remember {memory_marker}; respond with {response_marker}.",
            working_directory=workdir,
        ), timeout=REAL_STAGE_TIMEOUTS["turn1_start_terminal"], stage="turn 1 start")
        if turn1.status is not TurnStartStatus.CONFIRMED or turn1.binding is None:
            raise PreparationGateError("Turn-1 start not confirmed")
        turn1_terminal = await _await_owned(turn_lifecycle.wait_turn(turn1.binding), timeout=REAL_STAGE_TIMEOUTS["turn1_start_terminal"], stage="turn 1 terminal")
        if turn1_terminal.status is not TurnTerminalStatus.COMPLETED or response_marker not in " ".join(message.text for message in turn1_terminal.messages):
            raise PreparationGateError("Turn-1 observed output marker missing")
        await _await_owned(self.runtime_manager.shutdown_profile(profile_id), timeout=REAL_STAGE_TIMEOUTS["runtime_shutdown_generation_1"], stage="runtime shutdown generation 1")

        # The catalog is pinned from the one authenticated model/list result;
        # a new runtime generation is not permitted to trigger model/list.
        second_runtime = await _await_owned(self.runtime_manager.acquire(profile_id), timeout=REAL_STAGE_TIMEOUTS["runtime_acquire_generation_2"], stage="runtime acquire generation 2")
        resume_lifecycle = CodexThreadLifecycleAdapter(self.runtime_manager, pinned_catalog)
        resume_turns = CodexTurnLifecycleAdapter(self.runtime_manager, pinned_catalog)
        self.budget.record("thread/resume")
        validate_stable_workdir(workdir_identity, workdir_identity_pair)
        resumed = await _await_owned(resume_lifecycle.resume(binding=thread_binding, working_directory=workdir), timeout=REAL_STAGE_TIMEOUTS["thread_resume"], stage="thread resume")
        if resumed.status is not ThreadOperationStatus.RESUME_CONFIRMED or resumed.binding != thread_binding:
            raise PreparationGateError("RESUME_CONFIRMED required")
        self.budget.record("turn/start")
        turn2 = await _await_owned(resume_turns.start_turn(
            thread_binding=thread_binding, model_id=model.model_id,
            reasoning_effort=reasoning_effort,
            user_text=f"Return the exact remembered marker {memory_marker}.",
            working_directory=workdir,
        ), timeout=REAL_STAGE_TIMEOUTS["turn2_start_terminal"], stage="turn 2 start")
        if turn2.status is not TurnStartStatus.CONFIRMED or turn2.binding is None or turn2.binding.turn_id == turn1.binding.turn_id:
            raise PreparationGateError("Turn-2 actual distinct binding required")
        turn2_terminal = await _await_owned(resume_turns.wait_turn(turn2.binding), timeout=REAL_STAGE_TIMEOUTS["turn2_start_terminal"], stage="turn 2 terminal")
        if turn2_terminal.status is not TurnTerminalStatus.COMPLETED or memory_marker not in " ".join(message.text for message in turn2_terminal.messages):
            raise PreparationGateError("Turn-2 memory marker missing")

        # The approval bridge is the sole protocol response route.  The
        # operator reserves total-response and ALLOW accounting together.
        target = Path(self.boot["approval_target"])
        if target.exists() or target.is_symlink():
            raise PreparationGateError("approval target must be absent")
        client = second_runtime.client
        authority_dir = Path("/root/.codexcontrol")
        wire_authority = RootOnlyWireCommandAuthority(authority_dir / f"p7c13-wire-{self.boot['run_id_hash'][:16]}.json")
        recovery_journal = RootOnlyApprovalRecoveryJournal(authority_dir / f"p7c13-approval-journal-{self.boot['run_id_hash'][:16]}.json")
        operator = ProductionApprovalOperator(
            profile_id=profile_id, thread_id=thread_binding.thread_id,
            cwd=workdir.path, target=target, budget=self.budget,
            wire_authority=wire_authority, recovery_journal=recovery_journal,
        )
        approval_bridge = CodexApprovalBridge(profile_id=profile_id, client=client, operator=operator)
        self.budget.record("turn/start")
        validate_stable_workdir(workdir_identity, workdir_identity_pair)
        turn3_prompt = c11_explicit_escalation_prompt(str(target))
        turn3 = await _await_owned(resume_turns.start_turn(
            thread_binding=thread_binding, model_id=model.model_id,
            reasoning_effort=reasoning_effort,
            user_text=turn3_prompt, working_directory=workdir,
        ), timeout=REAL_STAGE_TIMEOUTS["turn3_start_approval_terminal"], stage="turn 3 start")
        if turn3.status is not TurnStartStatus.CONFIRMED or turn3.binding is None:
            raise PreparationGateError("Turn-3 actual binding required")
        if operator.turn_binding is None:
            operator.turn_binding = turn3.binding
        approval = await _await_owned(approval_bridge.handle_next(), timeout=REAL_STAGE_TIMEOUTS["turn3_start_approval_terminal"], stage="turn 3 approval")
        recovery_journal.append({"event": "RESPONSE", "request_ordinal": operator.request_count, "response_count": 1, "status": approval.status.value})
        if approval.status is not ApprovalHandlingStatus.ALLOWED or operator.allow_count != 1 or operator.deny_count != 0 or operator.request_count != 1 or self.budget.count("approval_responses") != 1:
            raise PreparationGateError("single protocol ALLOW required")
        turn3_terminal = await _await_owned(resume_turns.wait_turn(turn3.binding), timeout=REAL_STAGE_TIMEOUTS["turn3_start_approval_terminal"], stage="turn 3 terminal")
        if turn3_terminal.status is not TurnTerminalStatus.COMPLETED:
            raise PreparationGateError("Turn-3 completion required")
        target_stat = target.lstat()
        if not stat.S_ISREG(target_stat.st_mode) or target_stat.st_uid != 0 or target_stat.st_nlink != 1 or stat.S_IMODE(target_stat.st_mode) != 0o600:
            raise PreparationGateError("approval target metadata unsafe")
        target.unlink()

        self.budget.record("turn/start")
        validate_stable_workdir(workdir_identity, workdir_identity_pair)
        turn4 = await _await_owned(resume_turns.start_turn(
            thread_binding=thread_binding, model_id=model.model_id,
            reasoning_effort=reasoning_effort, user_text=TURN4_STIMULUS,
            working_directory=workdir,
        ), timeout=REAL_STAGE_TIMEOUTS["turn4_start"], stage="turn 4 start")
        if turn4.status is not TurnStartStatus.CONFIRMED or turn4.binding is None or turn4.binding.turn_id in {turn1.binding.turn_id, turn2.binding.turn_id, turn3.binding.turn_id}:
            raise PreparationGateError("Turn-4 actual distinct binding required")
        turn4_gate = await observe_owned_turn4(
            client=client, turn_lifecycle=resume_turns, binding=turn4.binding,
            budget=self.budget,
        )
        if not turn4_gate.passed:
            if turn4_gate.unexpected_request_count:
                raise PreparationGateError("unexpected Turn-4 server request")
            raise PreparationGateError("Turn-4 active/interrupt gate failed")
        await _await_owned(self.runtime_manager.shutdown_profile(profile_id), timeout=REAL_STAGE_TIMEOUTS["runtime_shutdown_before_scan"], stage="runtime shutdown before scan")

        material_markers = (memory_marker.encode(), response_marker.encode(), str(target).encode(), turn3_prompt.encode(), TURN4_STIMULUS.encode())
        oracle = BoundedTargetOracle(self.profile, thread_binding.thread_id, material_markers)
        before = oracle.observe()
        if not predelete_observation_conclusive(before) or before.scan_errors:
            raise PreparationGateError("pre-delete physical oracle inconclusive")
        unrelated_before, target_paths = target_metadata_snapshot(self.profile, thread_binding.thread_id)
        storage = await _await_owned(SqliteStorage.open(self.boot["controller_db"]), timeout=REAL_STAGE_TIMEOUTS["controller_open_binding"], stage="controller open")
        try:
            schema_version = await _await_owned(storage.read(lambda connection: int(connection.execute("PRAGMA user_version").fetchone()[0])), timeout=REAL_STAGE_TIMEOUTS["controller_open_binding"], stage="controller schema observation")
            if schema_version != 4:
                raise PreparationGateError("controller schema is not v4")
            repository = DialogueRepository(storage)
            created = await _await_owned(repository.create_intent(dialogue_id=f"p7c13-{self.boot['run_id_hash'][:24]}", server_id="server-80", profile_id=profile_id), timeout=REAL_STAGE_TIMEOUTS["controller_open_binding"], stage="controller create binding")
            idle = await _await_owned(repository.confirm_created(dialogue_id=created.dialogue_id, expected_version=created.version, thread_id=thread_binding.thread_id), timeout=REAL_STAGE_TIMEOUTS["controller_open_binding"], stage="controller confirm binding")
            durable = await _await_owned(repository.get_live(), timeout=REAL_STAGE_TIMEOUTS["controller_open_binding"], stage="controller live binding observation")
            if durable is None or durable.state is not DialogueState.IDLE or durable.thread_id != thread_binding.thread_id:
                raise PreparationGateError("schema-v4 durable binding invalid")
            official = OfficialDeleteObservation(CodexThreadLifecycleAdapter(self.runtime_manager, catalog))
            service = assemble_production_delete_chain(storage, self.runtime_manager, catalog, server_id="server-80", lifecycle=official)
            self.budget.record("thread/delete")
            delete_result = await _await_owned(service.delete(DialogueDeleteRequest(idle.dialogue_id, idle.version)), timeout=REAL_STAGE_TIMEOUTS["canonical_application_delete"], stage="canonical application delete")
            application_status = getattr(delete_result.status, "value", None)
            await _await_owned(self.runtime_manager.shutdown_profile(profile_id), timeout=REAL_STAGE_TIMEOUTS["final_runtime_local_convergence"], stage="final runtime shutdown")
            runtime_child_quiescent = not any(getattr(self.runtime_manager, name, {}) for name in ("_runtimes", "_starting", "_unresolved"))
            tombstone = await _await_owned(DeletionRepository(storage).get_tombstone(idle.dialogue_id), timeout=REAL_STAGE_TIMEOUTS["final_runtime_local_convergence"], stage="tombstone observation")
            live_after = await _await_owned(repository.get_live(), timeout=REAL_STAGE_TIMEOUTS["final_runtime_local_convergence"], stage="post-delete live binding observation")
        finally:
            await _await_owned(storage.close(), timeout=REAL_STAGE_TIMEOUTS["final_runtime_local_convergence"], stage="controller close")
        after_persistent = BoundedTargetOracle(self.profile, thread_binding.thread_id, material_markers, families=("persistent_sessions", "persistent_history")).observe()
        after_isolated = BoundedTargetOracle(self.profile, thread_binding.thread_id, material_markers, families=("isolated_sqlite", "isolated_logs")).observe()
        unrelated_after, _ = target_metadata_snapshot(self.profile, thread_binding.thread_id)
        unrelated_removed = derived_unrelated_removal_fact(unrelated_before, unrelated_after, target_paths=target_paths)
        try:
            self.isolation_root.validate(self.profile)
            envelope_valid = True
        except Exception:
            envelope_valid = False
        sqlite_descendants, sqlite_special, sqlite_symlinks, sqlite_errors = bounded_descendant_observation(Path(self.profile.isolated_state_root) / "sqlite")
        logs_descendants, logs_special, logs_symlinks, logs_errors = bounded_descendant_observation(Path(self.profile.isolated_state_root) / "logs")
        post_schema_ok = schema_version == 4
        tombstone_bounded = tombstone is not None and tombstone.dialogue_id == idle.dialogue_id and tombstone.thread_identity_sha256 == _sha256(thread_binding.thread_id) and tombstone.expires_at_ms >= tombstone.deleted_at_ms
        official_status = official.status.value if official.status is not None else None
        recovery_class = map_terminal_recovery_class(official_status=official_status, application_status=application_status)
        if recovery_class in {"UNKNOWN", "CONFIRMED_PENDING"}:
            return CompleteChildResult(False, {"delete": official_status or "UNKNOWN", "application": application_status or "UNKNOWN"}, {"persistent": after_persistent.thread_count + after_persistent.marker_count, "isolated": after_isolated.thread_count + after_isolated.marker_count, "scan_errors": after_persistent.scan_errors + after_isolated.scan_errors + sqlite_errors + logs_errors}, {"delete": official_status or "UNKNOWN", "application": application_status or "UNKNOWN", "recovery": recovery_class}, runtime_child_quiescent)
        if not post_delete_acceptance(
            official_delete=official_status or "", application_result=application_status or "", tombstone_bounded=tombstone_bounded,
            live_binding=live_after is not None, envelope_valid=envelope_valid and post_schema_ok and sqlite_special == 0 and sqlite_symlinks == 0 and logs_special == 0 and logs_symlinks == 0,
            isolated_sqlite_descendants=sqlite_descendants, isolated_logs_descendants=logs_descendants,
            persistent=after_persistent, isolated=after_isolated,
            scan_errors=sqlite_errors + logs_errors, owned_children=None, owned_group_active=None, owned_group_zombies=None,
            unrelated_signals=None, budgets_ok=recovery_class == "COMPLETED",
            unrelated_target_specific_removal_detected=unrelated_removed,
        ):
            raise PreparationGateError("post-delete physical oracle failed")
        return CompleteChildResult(runtime_child_quiescent, {"turn1": "COMPLETED", "turn2": "COMPLETED", "turn3": "COMPLETED", "turn4": "INTERRUPTED"}, {"persistent": after_persistent.thread_count + after_persistent.marker_count, "isolated": after_isolated.thread_count + after_isolated.marker_count, "scan_errors": after_persistent.scan_errors + after_isolated.scan_errors + sqlite_errors + logs_errors}, {"delete": official_status or "UNKNOWN", "application": application_status or "UNKNOWN", "recovery": recovery_class}, runtime_child_quiescent)


class _PinnedCatalogAdapter:
    def __init__(self, catalog: CodexModelCatalog) -> None:
        self.catalog = catalog

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        if profile_id != self.catalog.profile_id:
            raise PreparationGateError("pinned catalog profile mismatch")
        return self.catalog


class ProductionApprovalOperator:
    """One bridge-facing ALLOW decision with atomic accounting reservation."""

    def __init__(self, *, profile_id: str, thread_id: str, cwd: str, target: Path, budget: EffectBudget,
                 wire_authority: RootOnlyWireCommandAuthority | None = None,
                 recovery_journal: RootOnlyApprovalRecoveryJournal | None = None) -> None:
        self.profile_id, self.thread_id, self.cwd, self.target, self.budget = profile_id, thread_id, cwd, target, budget
        self.wire_authority = wire_authority
        self.recovery_journal = recovery_journal
        self.turn_binding: TurnBinding | None = None
        self.allow_count = 0
        self.deny_count = 0
        self.request_count = 0
        self.in_memory_captures: list[tuple[int, int, str | int]] = []
        self.response_unknown = False

    def _deny(self, *, ordinal: int, reason: str) -> ApprovalDecision:
        if self.budget.count("approval_responses"):
            raise PreparationGateError("second approval response denied by one-shot budget")
        self.budget.record("approval_responses")
        self.deny_count += 1
        if self.recovery_journal is not None:
            self.recovery_journal.append({"event": "DENY", "request_ordinal": ordinal, "reason": reason})
        return ApprovalDecision.DENY

    async def decide(self, request: Any) -> ApprovalDecision:
        self.request_count += 1
        ordinal = self.request_count
        if self.turn_binding is None:
            return self._deny(ordinal=ordinal, reason="turn-unbound")
        if getattr(request, "kind", None) is not ApprovalKind.COMMAND_EXECUTION:
            return self._deny(ordinal=ordinal, reason="kind")
        if getattr(request, "profile_id", None) != self.profile_id or getattr(request, "thread_id", None) != self.thread_id or getattr(request, "turn_id", None) != self.turn_binding.turn_id:
            return self._deny(ordinal=ordinal, reason="binding")
        cwd_lines = [line[len("cwd: "):] for line in request.context_lines if line.startswith("cwd: ")]
        command_lines = [line[len("command: "):] for line in request.context_lines if line.startswith("command: ")]
        if len(cwd_lines) != 1 or len(command_lines) != 1:
            return self._deny(ordinal=ordinal, reason="context-cardinality")
        actual_cwd = os.path.normpath(os.path.abspath(cwd_lines[0]))
        if actual_cwd != os.path.normpath(os.path.abspath(self.cwd)):
            return self._deny(ordinal=ordinal, reason="cwd")
        self.in_memory_captures.append((ordinal, request.local_sequence, request.wire_request_id))
        if len(self.in_memory_captures) != 1:
            return self._deny(ordinal=ordinal, reason="capture-cardinality")
        if self.wire_authority is None:
            self.wire_authority = RootOnlyWireCommandAuthority(self.target.parent / ".p7c13-wire-authority.json")
        if self.recovery_journal is None:
            self.recovery_journal = RootOnlyApprovalRecoveryJournal(self.target.parent / ".p7c13-approval-journal.json")
        try:
            self.wire_authority.capture_once(request=request, request_ordinal=ordinal, target=str(self.target))
        except PreparationGateError:
            return self._deny(ordinal=ordinal, reason="wire-capture")
        correlated = _correlate_root_wire(
            request, authority=self.wire_authority, expected_target=str(self.target),
            request_ordinal=ordinal, expected_thread=self.thread_id,
            expected_turn=self.turn_binding.turn_id, expected_cwd=self.cwd,
        )
        if correlated is None:
            return self._deny(ordinal=ordinal, reason="wire-correlation")
        request_fixture, expected, wire = correlated
        self.recovery_journal.append({
            "event": "APPROVAL_REQUEST", "request_ordinal": ordinal,
            "local_sequence": request.local_sequence, "kind": request.kind.value,
            "thread_sha256": _sha256(self.thread_id), "turn_sha256": _sha256(self.turn_binding.turn_id),
            "cwd_sha256": _sha256(actual_cwd), "wire_sha256": wire.command_sha256,
        })
        if c12.strict_p7c12_match(request_fixture, expected, [wire]) is not c12.MatcherResult.MATCH_EXACT_P7_APPROVAL_COMMAND:
            return self._deny(ordinal=ordinal, reason="matcher")
        if self.target.exists() or self.target.is_symlink():
            return self._deny(ordinal=ordinal, reason="target-not-absent")
        # Reserve the total response and ALLOW slots before bridge callback.
        self.budget.record("approval_responses")
        self.budget.record("allow_responses")
        self.allow_count += 1
        self.recovery_journal.append({"event": "ALLOW", "request_ordinal": ordinal, "local_sequence": request.local_sequence})
        return ApprovalDecision.ALLOW


def build_production_real_seam_factory(
    boot: Mapping[str, Any], *, runtime_factory: Callable[[dict[str, str], tuple[str, ...]], Any] | None = None,
) -> ProductionRealChildOrchestrator:
    """Construct the real adapter graph selected by the production default."""
    profile = CodexProfile(boot["profile_id"], boot["codex_home"], "P7.C13", boot["isolated_root"])
    routing = FutureRuntimeRouting(profile)
    environment = routing.environment()
    overrides = routing.config_overrides()
    repository_root = Path(__file__).resolve().parents[2]
    controller_root = Path(boot["controller_db"]).parent
    authority = IsolationPathAuthority(
        (profile,), controller_db_root=str(controller_root),
        repository_root=str(repository_root), protected_roots=(),
    )
    manager = runtime_factory(environment, overrides) if runtime_factory is not None else CodexRuntimeManager(
        (profile,), client_version="p7c13-future", isolation_authority=authority,
        parent_environment=environment,
    )
    catalog = CodexModelCatalogAdapter(manager)
    thread_lifecycle = CodexThreadLifecycleAdapter(manager, catalog)
    turn_lifecycle = CodexTurnLifecycleAdapter(manager, catalog)
    isolated_state_root = IsolatedStateRoot(authority)
    return ProductionRealChildOrchestrator(
        profile=profile, boot=boot, runtime_manager=manager, catalog_adapter=catalog,
        thread_lifecycle=thread_lifecycle, turn_lifecycle=turn_lifecycle,
        isolation_root=isolated_state_root, budget=EffectBudget(dict(boot["effect_ceiling"])),
    )


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
        turn3_capture=lambda: capture, approval_response=lambda: True,
        turn4_start=lambda: FlowBinding(binding.thread_id, "turn-4", binding.cwd, 4), interrupt=lambda: True, predelete=lambda: clean,
        bind_controller=lambda: FreshSchemaV4ControllerBinding(boot.get("controller_db", ""), boot.get("profile_id", "synthetic-p7c13"), binding.thread_id), delete_service=lambda: "DELETED",
        postdelete=lambda result, observed: result == "DELETED" and observed.thread_count > 0,
    )


def _child_result_payload(boot: Mapping[str, Any], result: CompleteChildResult, budget: EffectBudget) -> dict[str, Any]:
    recovery = result.classes.get("recovery")
    status = "PASS" if result.verdict else recovery if recovery in {"UNKNOWN", "CONFIRMED_PENDING"} else "FAILED"
    return {
        "schema": CHILD_RESULT_SCHEMA, "status": status, "verdict": result.verdict,
        "source_head": boot["source_head"], "source_tree": boot["source_tree"], "harness_blob": boot["harness_blob"], "run_id_hash": boot["run_id_hash"],
        "effect_counts": {key: budget.count(key) for key in FROZEN_EFFECT_BUDGET}, "outcomes": dict(result.outcomes),
        "residual_counts": {key: result.residual_counts.get(key, 0) for key in ("persistent", "isolated", "scan_errors")},
        "classes": dict(result.classes),
        "runtime_child_quiescent": result.runtime_child_quiescent,
        # Parent owns the OS process-group fact; child cannot assert it.
        "parent_process_group_quiescent": None,
    }


def _future_child_injected_main(
    boot: Mapping[str, Any], *, installed: InstalledRuntimeAuthority,
    runtime_factory: Callable[[dict[str, str], tuple[str, ...]], Any] | None,
    business_factory: Callable[[Any], Any] | None,
    seams_factory: Callable[[Mapping[str, Any], FlowBinding, str, str], FutureChildSeams] | None,
) -> int:
    """Explicit test-only child route; inaccessible to production defaults."""
    budget = EffectBudget(dict(boot["effect_ceiling"]))
    previous_umask = os.umask(0o077)
    try:
        profile = CodexProfile(boot["profile_id"], boot["codex_home"], "P7.C13", boot["isolated_root"])
        binding = FlowBinding("test-injected-thread", "test-injected-turn-1", boot["workdir"], 1)
        memory_marker, response_marker = fresh_non_secret_markers()
        seams = seams_factory(boot, binding, memory_marker, response_marker) if seams_factory is not None else None
        if runtime_factory is None:
            runtime_factory = lambda environment, overrides: object()
        if business_factory is None and seams is not None:
            dispatch = {name: (lambda: True) for name in FROZEN_EFFECT_BUDGET if name not in {"thread/read", "thread/list", "second_child", "real_retry", "telegram"}}
            effects = FutureRealEffectBridge(budget, dispatch)
            business_factory = lambda runtime: CompleteFutureChildOrchestrator(
                effects=effects, binding=binding, memory_marker=memory_marker,
                response_marker=response_marker, seams=seams, boot=boot,
            )
        if business_factory is None:
            raise PreparationGateError("explicit injected business seam missing")
        child = FutureRealChildPath(
            installed=installed, routing=FutureRuntimeRouting(profile),
            runtime_factory=runtime_factory, business_factory=business_factory,
        )
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
    finally:
        os.umask(previous_umask)


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
    # This runtime-only binding is not written into the child authority file;
    # it lets production preflight inspect the exact boot inode as well.
    boot = {**boot, "boot_authority_path": str(Path(boot_path).absolute())}
    if seams_factory is not None or business_factory is not None:
        return _future_child_injected_main(
            boot, installed=installed or InstalledRuntimeAuthority(),
            runtime_factory=runtime_factory, business_factory=business_factory,
            seams_factory=seams_factory,
        )
    budget = EffectBudget(dict(boot["effect_ceiling"]))
    previous_umask = os.umask(0o077)
    try:
        authority = installed or InstalledRuntimeAuthority()
        authority.verify()
        child = build_production_real_seam_factory(boot, runtime_factory=runtime_factory)
        result = asyncio.run(child.run_async())
        result_budget = child.budget
        if not isinstance(result, CompleteChildResult):
            raise PreparationGateError("complete child result missing")
        _write_child_result(boot["child_result_path"], _child_result_payload(boot, result, result_budget))
        return 0 if result.verdict else 1
    except Exception as error:
        failure = CompleteChildResult(False, {"terminal": type(error).__name__}, {"scan_errors": 1}, {"failure": "FAIL_CLOSED"})
        try:
            _write_child_result(boot["child_result_path"], _child_result_payload(boot, failure, budget))
        except (OSError, PreparationGateError):
            pass
        return 1
    finally:
        os.umask(previous_umask)


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


def _synthetic_boot_record(base: str | Path, *, source_head: str = REPAIR3_BASE_HEAD, source_tree: str = P7C13_BASE_TREE, harness_blob: str = PRIOR_HARNESS_BLOB) -> dict[str, Any]:
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
            def write_valid_result(command, *, result_path, result_validator=None, **kwargs):
                budget = EffectBudget()
                budget.counts = dict(FROZEN_EFFECT_BUDGET)
                _write_child_result(result_path, _child_result_payload(executor._boot_record(executor.record), CompleteChildResult(True, {}, {"persistent": 0, "isolated": 0, "scan_errors": 0}, {}), budget))
                return WatchdogResult("COMPLETED", child_result_valid=True)
            fake_watchdog.run.side_effect = write_valid_result
            self.assertEqual("COMPLETED", executor.run().status)
            fake_watchdog.run.assert_called_once()
            self.assertEqual(("synthetic-child",), fake_watchdog.run.call_args.args[0])
            self.assertEqual(result_path, fake_watchdog.run.call_args.kwargs["result_path"])
            with self.assertRaises(PreparationGateError):
                executor.run()
            self.assertEqual("COMPLETED", DurableOneShotLedger(Path(directory) / "ledger.json").read()["state"])

    def test_watchdog_uses_one_synthetic_child_and_validates_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-watchdog-") as directory:
            boot = _synthetic_boot_record(directory)
            result = Path(directory) / "result.json"
            payload = json.dumps(_child_result_payload(boot, CompleteChildResult(True, {}, {}, {}), EffectBudget()))
            code = "import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])"
            watchdog = OwnedParentChildWatchdog(result_validator=lambda path: _child_result_file_is_valid(path, boot))
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
                seams_factory=_default_child_seams,
            )
            self.assertEqual(0, code)
            self.assertEqual(["runtime"], runtime_calls)
            result = read_child_result(boot["child_result_path"], boot=boot)
            self.assertEqual("PASS", result["status"])
            self.assertTrue(result["verdict"])
            self.assertTrue(result["runtime_child_quiescent"])
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


def _path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _process_users_for_boundaries(boundaries: Mapping[str, Path]) -> dict[str, int]:
    """Bounded diagnostic /proc scan; shared persistent home is not owned here."""
    users = {name: set() for name in boundaries}
    try:
        pids = tuple(int(name) for name in os.listdir("/proc") if name.isdigit())
    except OSError as error:
        raise PreparationGateError("external-user scan failed") from error
    for pid in pids:
        if pid == os.getpid():
            continue
        proc = Path("/proc") / str(pid)
        values: list[Path] = []
        try:
            values.append(Path(os.readlink(proc / "cwd")))
        except OSError:
            pass
        try:
            for fd_name in os.listdir(proc / "fd"):
                try:
                    values.append(Path(os.readlink(proc / "fd" / fd_name)))
                except OSError:
                    continue
        except OSError:
            continue
        for name, path in boundaries.items():
            if any(value == path or _path_is_under(value, path) for value in values):
                users[name].add(pid)
    return {name: len(value) for name, value in users.items()}


def production_read_only_boundary_preflight(
    boundaries: Mapping[str, Path], *, mountinfo: str | None = None,
    external_users: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Actual future-path preflight for mount aliases and owned external users."""
    report_only_users = frozenset(("persistent_home", "repository", "controller_root"))
    destructive_user_boundaries = frozenset((
        "isolated_root", "isolated_sqlite", "isolated_logs", "controller_db",
        "workdir", "approval_target", "ledger", "boot", "result",
    ))
    normalized = {name: Path(os.path.abspath(os.fspath(path))) for name, path in boundaries.items()}
    if not normalized or "persistent_home" not in normalized or "repository" not in normalized:
        raise PreparationGateError("boundary set incomplete")
    identities: dict[str, tuple[int, int] | None] = {}
    for name, path in normalized.items():
        try:
            value = path.lstat()
        except FileNotFoundError:
            identities[name] = None
            continue
        except OSError as error:
            raise PreparationGateError("boundary stat failed") from error
        if stat.S_ISLNK(value.st_mode) or (not stat.S_ISDIR(value.st_mode) and value.st_nlink != 1) or value.st_uid != 0:
            raise PreparationGateError("boundary alias/ownership invalid")
        identities[name] = (value.st_dev, value.st_ino)
    names = tuple(normalized)
    allowed_nested = {("isolated_root", "isolated_sqlite"), ("isolated_root", "isolated_logs"), ("controller_root", "controller_db"),
                      ("controller_root", "ledger"), ("controller_root", "boot"), ("controller_root", "result")}
    for index, left_name in enumerate(names):
        for right_name in names[index + 1:]:
            left, right = normalized[left_name], normalized[right_name]
            if identities[left_name] is not None and identities[left_name] == identities[right_name]:
                raise PreparationGateError("boundary physical alias")
            if (_path_is_under(left, right) or _path_is_under(right, left)) and (left_name, right_name) not in allowed_nested and (right_name, left_name) not in allowed_nested:
                raise PreparationGateError("boundary topology overlap")
    info = mountinfo if mountinfo is not None else Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    mount_points = {line.split()[4] for line in info.splitlines() if len(line.split()) >= 5}
    if any(str(path) in mount_points for path in normalized.values()):
        raise PreparationGateError("mount alias unresolved")
    users = dict(external_users) if external_users is not None else _process_users_for_boundaries(normalized)
    if not destructive_user_boundaries.issubset(normalized):
        raise PreparationGateError("destructive boundary set incomplete")
    if any(name not in report_only_users | destructive_user_boundaries for name in users):
        raise PreparationGateError("unknown boundary user classification")
    for count in users.values():
        if type(count) is not int or count < 0:
            raise PreparationGateError("boundary user count invalid")
    for name in destructive_user_boundaries:
        count = users.get(name, 0)
        if count:
            raise PreparationGateError("owned external boundary user")
    return {
        "mount_alias": "PASS", "external_users": users,
        "report_only_user_boundaries": tuple(sorted(report_only_users)),
        "destructive_user_boundaries": tuple(sorted(destructive_user_boundaries)),
        "persistent_home_shared": "YES",
    }


def create_fresh_private_workdir(path: str | Path) -> TrustedWorkingDirectory:
    """Create exactly one root-owned private workdir before thread/start."""
    target = Path(path)
    if target.exists() or target.is_symlink() or not target.is_absolute():
        raise PreparationGateError("workdir must start absent")
    try:
        target.mkdir(mode=0o700)
        os.chmod(target, 0o700)
        value = target.lstat()
    except OSError as error:
        raise PreparationGateError("workdir creation failed") from error
    if not stat.S_ISDIR(value.st_mode) or value.st_uid != 0 or stat.S_IMODE(value.st_mode) != 0o700:
        raise PreparationGateError("workdir authority invalid")
    return TrustedWorkingDirectory(str(target))


def validate_stable_workdir(path: str | Path, identity: tuple[int, int]) -> None:
    value = Path(path).lstat()
    if stat.S_ISLNK(value.st_mode) or not stat.S_ISDIR(value.st_mode) or (value.st_dev, value.st_ino) != identity:
        raise PreparationGateError("workdir identity drift")


def fresh_run_owned_paths(
    *, isolated_root: Path, controller_db: Path, workdir: Path, approval_target: Path,
    ledger_path: Path, persistent_home: Path, repository: Path,
) -> dict[str, str]:
    """Read-only proof for the four fresh mutable boundaries."""
    paths = {
        "isolated_root": isolated_root, "controller_db": controller_db,
        "workdir": workdir, "approval_target": approval_target,
    }
    if approval_target.parent != Path("/root") or not approval_target.name.startswith("p7c13-approval-"):
        raise PreparationGateError("approval target is not a direct root child")
    protected = (persistent_home, repository, Path("/tmp"), Path("/root/.codexcontrol"))
    all_values = tuple(paths.values()) + (ledger_path,)
    if len({str(path) for path in all_values}) != len(all_values):
        raise PreparationGateError("run-owned path collision")
    for name, path in paths.items():
        if not path.is_absolute() or path.is_symlink() or path.exists():
            raise PreparationGateError(f"{name} is not fresh")
        if name == "approval_target" and any(_path_is_under(path, root) or _path_is_under(root, path) for root in protected):
            raise PreparationGateError(f"{name} aliases protected root")
    canonical = [os.path.realpath(path) for path in all_values]
    if len(set(canonical)) != len(canonical):
        raise PreparationGateError("physical path alias")
    return {name: str(path) for name, path in paths.items()}


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


class _Turn4FakeProtocolClient:
    """Injected queue-only client used by offline Turn-4 observer tests."""

    def __init__(self) -> None:
        self.requests: asyncio.Queue[Any] = asyncio.Queue()
        self.response_calls = 0

    async def next_server_request(self) -> Any:
        return await self.requests.get()

    async def respond_server_request(self, *_: Any, **__: Any) -> None:
        self.response_calls += 1


class _Turn4FakeLifecycle:
    def __init__(
        self, binding: TurnBinding, *, terminal_ready: bool = False,
        complete_on_interrupt: bool = True,
    ) -> None:
        self.binding = binding
        self.terminal_event = asyncio.Event()
        if terminal_ready:
            self.terminal_event.set()
        self.terminal_status = TurnTerminalStatus.FAILED
        self.interrupt_calls = 0
        self.on_interrupt: Callable[[], Any] | None = None
        self.complete_on_interrupt = complete_on_interrupt
        self.on_wait_cancel: Callable[[], Any] | None = None

    async def wait_turn(self, binding: TurnBinding) -> TurnTerminalResult:
        if binding != self.binding:
            raise AssertionError("wrong Turn-4 binding")
        try:
            await self.terminal_event.wait()
        except asyncio.CancelledError:
            if self.on_wait_cancel is not None:
                callback = self.on_wait_cancel()
                if hasattr(callback, "__await__"):
                    await callback
            raise
        return TurnTerminalResult(binding, self.terminal_status, ())

    async def interrupt_turn(self, binding: TurnBinding) -> TurnInterruptResult:
        if binding != self.binding:
            raise AssertionError("wrong Turn-4 interrupt binding")
        self.interrupt_calls += 1
        if self.on_interrupt is not None:
            callback = self.on_interrupt()
            if hasattr(callback, "__await__"):
                await callback
        if self.complete_on_interrupt:
            self.terminal_event.set()
        terminal = TurnTerminalResult(binding, TurnTerminalStatus.FAILED, ())
        return TurnInterruptResult(TurnInterruptStatus.CONFIRMED, binding, terminal)


class _Turn4ErrorProtocolClient(_Turn4FakeProtocolClient):
    async def next_server_request(self) -> Any:
        raise RuntimeError("synthetic observer failure")


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

    def test_direct_parent_cli_unset_or_drifted_source_has_zero_executor_calls(self) -> None:
        with patch(__name__ + "._current_source_authority", return_value=("head", "tree", "harness", True)):
            fake = unittest.mock.Mock(spec=FutureRealExecutor)
            with self.assertRaises(PreparationGateError):
                future_real_cli_entrypoint(environ={}, executor=fake)
            fake.run.assert_not_called()
        exact = {
            FUTURE_GATE_ENV: "offline-token",
            "P7C13_EXPECTED_HEAD": "head", "P7C13_EXPECTED_TREE": "tree",
            "P7C13_EXPECTED_HARNESS_BLOB": "harness",
        }
        with patch(__name__ + "._current_source_authority", return_value=("head", "tree", "harness", False)):
            fake = unittest.mock.Mock(spec=FutureRealExecutor)
            with self.assertRaises(PreparationGateError):
                future_real_cli_entrypoint(environ=exact, executor=fake)
            fake.run.assert_not_called()

    def test_direct_parent_cli_exact_source_gate_enters_executor_once(self) -> None:
        environment = {
            FUTURE_GATE_ENV: "offline-token", "P7C13_EXPECTED_HEAD": "head",
            "P7C13_EXPECTED_TREE": "tree", "P7C13_EXPECTED_HARNESS_BLOB": "harness",
        }
        fake = unittest.mock.Mock(spec=FutureRealExecutor)
        fake.run.return_value = "prepared"
        with patch(__name__ + "._current_source_authority", return_value=("head", "tree", "harness", True)):
            self.assertEqual("prepared", future_real_cli_entrypoint(environ=environment, executor=fake))
        fake.run.assert_called_once()

    def test_fresh_run_owned_paths_are_unique_absent_and_alias_checked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-fresh-") as directory:
            root = Path(directory)
            paths = fresh_run_owned_paths(
                isolated_root=root / "isolated", controller_db=root / "controller.sqlite3",
                workdir=root / "work", approval_target=Path("/root/p7c13-approval-offline-unique"),
                ledger_path=root / "ledger", persistent_home=Path(PERSISTENT_HOME),
                repository=Path("/root/CodexControl"),
            )
            self.assertEqual(4, len(paths))
            self.assertFalse(any(Path(value).exists() for value in paths.values()))
            existing = root / "existing"
            existing.touch()
            with self.assertRaises(PreparationGateError):
                fresh_run_owned_paths(
                    isolated_root=existing, controller_db=root / "c.sqlite3", workdir=root / "w",
                    approval_target=Path("/root/p7c13-approval-offline-existing"), ledger_path=root / "l",
                    persistent_home=Path(PERSISTENT_HOME), repository=Path("/root/CodexControl"),
                )

    def test_private_umask_makes_exact_touch_target_private_without_command_chmod(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-umask-") as directory:
            target = Path(directory) / "approval"
            previous = os.umask(0o077)
            try:
                target.touch()
            finally:
                os.umask(previous)
            self.assertEqual(0o600, stat.S_IMODE(target.lstat().st_mode))

    def test_production_default_selects_real_factory_and_never_synthetic_default(self) -> None:
        child_source = inspect.getsource(_future_child_main)
        factory_source = inspect.getsource(build_production_real_seam_factory)
        self.assertNotIn("_default_child_seams", child_source)
        self.assertNotIn("synthetic-future-thread", child_source)
        for name in ("CodexRuntimeManager", "CodexModelCatalogAdapter", "CodexThreadLifecycleAdapter", "CodexTurnLifecycleAdapter", "CodexApprovalBridge", "assemble_production_delete_chain", "BoundedTargetOracle"):
            self.assertIn(name, factory_source + inspect.getsource(ProductionRealChildOrchestrator))

    def test_final_child_result_is_one_schema_and_failed_unknown_wrong_authority_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-result-authority-") as directory:
            boot = _synthetic_boot_record(directory)
            budget = EffectBudget()
            budget.counts = dict(FROZEN_EFFECT_BUDGET)
            value = _child_result_payload(boot, CompleteChildResult(True, {}, {"persistent": 0, "isolated": 0, "scan_errors": 0}, {}), budget)
            self.assertTrue(child_result_passes(value, boot))
            for mutation in (
                {"status": "FAILED", "verdict": False},
                {"status": "UNKNOWN", "verdict": False},
                {"source_head": "wrong"},
                {"effect_counts": {**value["effect_counts"], "thread/delete": 0}},
                {"process_group_quiescent": False},
            ):
                candidate = dict(value)
                candidate.update(mutation)
                self.assertFalse(child_result_passes(candidate, boot))
            self.assertFalse(_safe_child_result({"schema": "p7c13-child-result-v1", "status": "COMPLETED"}))

    def test_model_catalog_adapter_requires_one_visible_default_and_thread_start_uses_returned_binding(self) -> None:
        class Client:
            def __init__(self, defaults: int) -> None:
                self.defaults, self.calls = defaults, []
            async def request(self, method: str, params: Any) -> dict[str, Any]:
                self.calls.append(method)
                if method == "model/list":
                    return {"data": [
                        {"id": f"m{i}", "model": f"wire-{i}", "displayName": f"Model {i}", "description": "offline", "hidden": False, "isDefault": i < self.defaults, "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "medium"}], "defaultReasoningEffort": "medium"}
                        for i in range(max(1, self.defaults))
                    ]}
                if method == "thread/start":
                    return {"thread": {"id": "actual-thread-returned"}}
                raise AssertionError(method)
        class Runtime:
            profile_id = "offline-profile"
            generation = 1
            def __init__(self, client: Client) -> None: self.client = client
        class Manager:
            def __init__(self, client: Client) -> None: self.runtime, self.acquire_calls = Runtime(client), 0
            async def acquire(self, profile_id: str) -> Runtime: self.acquire_calls += 1; return self.runtime
        client = Client(1); manager = Manager(client); catalog = CodexModelCatalogAdapter(manager)
        lifecycle = CodexThreadLifecycleAdapter(manager, catalog)
        result = asyncio.run(lifecycle.start("offline-profile", model_id="m0", reasoning_effort=None, working_directory=TrustedWorkingDirectory("/root/offline-work")))
        self.assertIs(result.status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual("actual-thread-returned", result.binding.thread_id)
        self.assertEqual(1, client.calls.count("model/list"))
        bad = Client(2)
        with self.assertRaises(Exception):
            asyncio.run(CodexModelCatalogAdapter(Manager(bad)).get_catalog("offline-profile"))

    def test_single_allow_reserves_two_accounting_facts_and_sends_one_fake_protocol_response(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-approval-") as directory:
            target = Path(directory) / "target"
            client = type("Client", (), {})()
            request = type("Request", (), {})
            from codex_control.adapters.codex.protocol import InboundServerRequest
            inbound = InboundServerRequest(1, "approval-1", "item/commandExecution/requestApproval", {"itemId": "item", "startedAtMs": 1, "threadId": "thread-real", "turnId": "turn-real", "cwd": "/root/offline-work", "command": shlex.join(["/bin/bash", "-lc", f"touch {target}"])})
            client.request = inbound
            client.responses = []
            client.wait_terminal = lambda: asyncio.Event().wait()
            client.owns_server_request = lambda candidate: candidate is inbound
            async def respond(candidate: Any, result: dict[str, Any]) -> None:
                client.responses.append((candidate, result))
            client.respond_server_request = respond
            budget = EffectBudget()
            operator = ProductionApprovalOperator(profile_id="offline-profile", thread_id="thread-real", cwd="/root/offline-work", target=target, budget=budget)
            operator.turn_binding = TurnBinding("offline-profile", "thread-real", "turn-real")
            bridge = CodexApprovalBridge(profile_id="offline-profile", client=client, operator=operator)
            result = asyncio.run(bridge.handle_request(inbound))
            self.assertIs(result.status, ApprovalHandlingStatus.ALLOWED)
            self.assertEqual(1, len(client.responses))
            self.assertEqual(1, budget.count("approval_responses"))
            self.assertEqual(1, budget.count("allow_responses"))

    def test_turn4_no_request_active_interrupt_failed_terminal_passes(self) -> None:
        async def scenario() -> Turn4GateResult:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            budget = EffectBudget()
            budget.counts = {"approval_responses": 1, "allow_responses": 1}
            return await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=budget, active_timeout=0.01, interrupt_timeout=0.1,
            )

        result = asyncio.run(scenario())
        self.assertTrue(result.passed)
        self.assertIs(result.interrupt.status, TurnInterruptStatus.CONFIRMED)
        self.assertEqual(0, result.unexpected_request_count)
        self.assertEqual(Turn4RequestObserverClass.CANCELLED_BY_HARNESS_WITHOUT_REQUEST, result.request_observer_class)
        self.assertTrue(result.request_observer_joined)
        self.assertTrue(result.terminal_waiter_joined)

    def test_turn4_terminal_before_active_has_zero_interrupts(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, int]:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"), terminal_ready=True)
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.1, interrupt_timeout=0.1,
            )
            return result, lifecycle.interrupt_calls

        result, interrupt_calls = asyncio.run(scenario())
        self.assertFalse(result.passed)
        self.assertEqual(0, interrupt_calls)

    def test_turn4_request_before_active_timeout_has_no_response_and_no_delete_eligibility(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, _Turn4FakeProtocolClient, EffectBudget, int]:
            client = _Turn4FakeProtocolClient()
            await client.requests.put(object())
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            budget = EffectBudget()
            budget.counts = {"approval_responses": 1, "allow_responses": 1}
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=budget, active_timeout=0.1, interrupt_timeout=0.1,
            )
            return result, client, budget, lifecycle.interrupt_calls

        result, client, budget, interrupt_calls = asyncio.run(scenario())
        self.assertFalse(result.passed)
        self.assertEqual(1, result.unexpected_request_count)
        self.assertEqual(1, interrupt_calls)
        self.assertEqual(0, client.response_calls)
        self.assertEqual(1, budget.count("approval_responses"))
        self.assertEqual(1, budget.count("allow_responses"))
        self.assertEqual(0, budget.count("deny_responses"))

    def test_turn4_request_during_interrupt_is_nonpass_without_response(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, _Turn4FakeProtocolClient]:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            async def request_during_interrupt() -> None:
                await client.requests.put(object())
                await asyncio.sleep(0)
            lifecycle.on_interrupt = request_during_interrupt
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.01, interrupt_timeout=0.1,
            )
            return result, client

        result, client = asyncio.run(scenario())
        self.assertFalse(result.passed)
        self.assertEqual(1, result.unexpected_request_count)
        self.assertEqual(0, client.response_calls)

    def test_turn4_request_before_final_terminal_convergence_is_nonpass(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, _Turn4FakeProtocolClient]:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            async def request_before_terminal() -> None:
                await client.requests.put(object())
                await asyncio.sleep(0.01)
            lifecycle.on_interrupt = request_before_terminal
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.01, interrupt_timeout=0.1,
            )
            return result, client

        result, client = asyncio.run(scenario())
        self.assertFalse(result.passed)
        self.assertEqual(1, result.unexpected_request_count)
        self.assertEqual(0, client.response_calls)

    def test_turn4_request_and_terminal_same_scheduler_slice_fail_closed(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, int]:
            client = _Turn4FakeProtocolClient()
            await client.requests.put(object())
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"), terminal_ready=True)
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.1, interrupt_timeout=0.1,
            )
            return result, lifecycle.interrupt_calls

        result, interrupt_calls = asyncio.run(scenario())
        self.assertFalse(result.passed)
        self.assertTrue(result.same_tick)
        self.assertEqual(0, interrupt_calls)

    def test_turn4_late_request_after_preliminary_snapshot_is_nonpass(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, _Turn4FakeProtocolClient, EffectBudget, int, int]:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(
                TurnBinding("p", "thread", "turn-4"), complete_on_interrupt=False,
            )
            # The request is delivered from terminal-waiter cancellation. This
            # is precisely after the preliminary done() snapshot and before
            # the final request-observer join.
            lifecycle.on_wait_cancel = lambda: client.requests.put_nowait(object())
            budget = EffectBudget()
            budget.counts = {"approval_responses": 1, "allow_responses": 1}
            controller_callbacks = 0
            delete_callbacks = 0
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=budget, active_timeout=0.01, interrupt_timeout=0.01,
                join_timeout=0.1,
            )
            if result.passed:
                controller_callbacks += 1
                delete_callbacks += 1
            return result, client, budget, controller_callbacks, delete_callbacks

        result, client, budget, controller_callbacks, delete_callbacks = asyncio.run(scenario())
        self.assertFalse(result.preliminary_request_done)
        self.assertEqual(Turn4RequestObserverClass.REQUEST_OBSERVED, result.request_observer_class)
        self.assertEqual(1, result.unexpected_request_count)
        self.assertFalse(result.passed)
        self.assertEqual(0, client.response_calls)
        self.assertEqual(1, budget.count("approval_responses"))
        self.assertEqual(1, budget.count("allow_responses"))
        self.assertEqual(0, budget.count("deny_responses"))
        self.assertEqual(0, controller_callbacks)
        self.assertEqual(0, delete_callbacks)
        self.assertTrue(result.request_observer_joined)
        self.assertTrue(result.terminal_waiter_joined)

    def test_turn4_observer_exception_is_nonpass_and_not_harness_cancellation(self) -> None:
        async def scenario() -> tuple[Turn4GateResult, _Turn4ErrorProtocolClient]:
            client = _Turn4ErrorProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            result = await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.1, interrupt_timeout=0.1,
            )
            return result, client

        result, client = asyncio.run(scenario())
        self.assertEqual(Turn4RequestObserverClass.OBSERVER_ERROR, result.request_observer_class)
        self.assertEqual(0, result.unexpected_request_count)
        self.assertFalse(result.passed)
        self.assertEqual(0, client.response_calls)
        self.assertTrue(result.request_observer_joined)
        self.assertTrue(result.terminal_waiter_joined)

    def test_turn4_observer_and_terminal_waiter_are_joined_without_detached_tasks(self) -> None:
        async def scenario() -> Turn4GateResult:
            client = _Turn4FakeProtocolClient()
            lifecycle = _Turn4FakeLifecycle(TurnBinding("p", "thread", "turn-4"))
            return await observe_owned_turn4(
                client=client, turn_lifecycle=lifecycle, binding=lifecycle.binding,
                budget=EffectBudget(), active_timeout=0.01, interrupt_timeout=0.1,
            )

        result = asyncio.run(scenario())
        self.assertTrue(result.request_observer_joined)
        self.assertTrue(result.terminal_waiter_joined)

    def test_turn4_observer_path_has_no_response_or_approval_bridge_dispatch(self) -> None:
        source = inspect.getsource(observe_owned_turn4)
        self.assertIn("next_server_request", source)
        self.assertNotIn("respond_server_request", source)
        self.assertNotIn("CodexApprovalBridge", source)

    def test_unexpected_turn4_request_blocks_controller_and_delete_dispatch(self) -> None:
        source = inspect.getsource(ProductionRealChildOrchestrator.run_async)
        gate = source.index("if not turn4_gate.passed")
        controller = source.index("SqliteStorage.open", gate)
        delete = source.index("service.delete", controller)
        self.assertLess(gate, controller)
        self.assertLess(gate, delete)

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
    def test_repair4_source_gate_is_tracked_worktree_and_index_clean(self) -> None:
        source = inspect.getsource(_current_source_authority)
        self.assertIn('"--cached"', source)
        self.assertIn('"git", "diff", "--quiet", "HEAD", "--", "."', source)

    def test_production_isolation_topology_validates_with_controller_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-topology-") as directory:
            root = Path(directory)
            home, state_parent, repo, controller_root = (root / name for name in ("home", "state-parent", "repo", "controller"))
            for path in (home, state_parent, repo, controller_root):
                path.mkdir(mode=0o700)
            profile = CodexProfile("topology", str(home), "Topology", str(state_parent / "isolated"))
            authority = IsolationPathAuthority((profile,), controller_db_root=str(controller_root), repository_root=str(repo))
            authority.validate_runtime_authority(state_root_may_be_missing=True)
            self.assertEqual(str(controller_root), authority.protected_paths[0])

    def test_workdir_is_fresh_private_and_alias_or_symlink_blocks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-workdir-") as directory:
            root = Path(directory)
            workdir = root / "work"
            trusted = create_fresh_private_workdir(workdir)
            value = workdir.lstat()
            identity = (value.st_dev, value.st_ino)
            self.assertEqual(0o700, stat.S_IMODE(value.st_mode))
            validate_stable_workdir(trusted.path, identity)
            with self.assertRaises(PreparationGateError):
                create_fresh_private_workdir(workdir)
            link = root / "link"
            link.symlink_to(workdir)
            with self.assertRaises(PreparationGateError):
                create_fresh_private_workdir(link)

    def test_production_mount_alias_and_external_boundary_preflight(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-boundary-") as directory:
            root = Path(directory)
            names = (
                "persistent_home", "repository", "isolated_root", "isolated_sqlite",
                "isolated_logs", "controller_root", "controller_db", "workdir",
                "approval_target", "ledger", "boot", "result",
            )
            boundaries = {name: root / name for name in names}
            for name in ("persistent_home", "repository", "isolated_root", "isolated_sqlite", "isolated_logs", "controller_root"):
                boundaries[name].mkdir(mode=0o700)
            passed = production_read_only_boundary_preflight(boundaries, mountinfo="1 2 3 4 /other", external_users={name: 0 for name in boundaries} | {"persistent_home": 4})
            self.assertEqual("PASS", passed["mount_alias"])
            self.assertEqual(4, passed["external_users"]["persistent_home"])
            for name in ("repository", "controller_root"):
                with self.subTest(report_only=name):
                    reported = production_read_only_boundary_preflight(
                        boundaries, mountinfo="1 2 3 4 /other",
                        external_users={key: 0 for key in boundaries} | {name: 2},
                    )
                    self.assertEqual(2, reported["external_users"][name])
            for name in ("isolated_root", "isolated_sqlite", "isolated_logs", "controller_db", "workdir", "approval_target", "ledger", "boot", "result"):
                with self.subTest(destructive=name), self.assertRaises(PreparationGateError):
                    production_read_only_boundary_preflight(
                        boundaries, mountinfo="1 2 3 4 /other",
                        external_users={key: 0 for key in boundaries} | {name: 1},
                    )
            with self.assertRaises(PreparationGateError):
                production_read_only_boundary_preflight(boundaries, mountinfo=f"1 2 3 4 {boundaries['repository']}", external_users={name: 0 for name in boundaries})
            with self.assertRaises(PreparationGateError):
                production_read_only_boundary_preflight(boundaries, mountinfo=f"1 2 3 4 {boundaries['controller_root']}", external_users={name: 0 for name in boundaries})
            repository_alias = dict(boundaries, repository=boundaries["persistent_home"])
            with self.assertRaises(PreparationGateError):
                production_read_only_boundary_preflight(repository_alias, mountinfo="1 2 3 4 /other", external_users={name: 0 for name in boundaries})
            controller_alias = dict(boundaries, controller_db=boundaries["controller_root"])
            with self.assertRaises(PreparationGateError):
                production_read_only_boundary_preflight(controller_alias, mountinfo="1 2 3 4 /other", external_users={name: 0 for name in boundaries})

    def test_repository_parent_executor_authority_is_report_only_and_owned_boundaries_block(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-boundary-users-") as directory:
            root = Path(directory)
            boundaries = {name: root / name for name in (
                "persistent_home", "repository", "isolated_root", "isolated_sqlite",
                "isolated_logs", "controller_root", "controller_db", "workdir",
                "approval_target", "ledger", "boot", "result",
            )}
            for name in ("persistent_home", "repository", "isolated_root", "isolated_sqlite", "isolated_logs", "controller_root"):
                boundaries[name].mkdir(mode=0o700)
            users = {name: 0 for name in boundaries}
            users["repository"] = 1  # simulated live parent/executor cwd
            result = production_read_only_boundary_preflight(boundaries, mountinfo="1 2 3 4 /other", external_users=users)
            self.assertEqual(1, result["external_users"]["repository"])
            for name in ("workdir", "controller_db", "ledger"):
                with self.subTest(boundary=name), self.assertRaises(PreparationGateError):
                    production_read_only_boundary_preflight(
                        boundaries, mountinfo="1 2 3 4 /other",
                        external_users={**users, name: 1},
                    )

    def test_real_proc_group_probe_reports_active_zombie_and_scan_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-proc-") as directory:
            proc = Path(directory)
            (proc / "101").mkdir()
            (proc / "102").mkdir()
            (proc / "101" / "stat").write_text("101 (active) S 1 777 777\n", encoding="ascii")
            (proc / "102" / "stat").write_text("102 (zombie) Z 1 777 777\n", encoding="ascii")
            self.assertEqual((1, 1, 0), inspect_owned_process_group(777, proc_root=proc))
            (proc / "103").mkdir()
            (proc / "103" / "stat").write_text("malformed", encoding="ascii")
            self.assertEqual((1, 1, 1), inspect_owned_process_group(777, proc_root=proc))

    def test_production_watchdog_has_real_bounds_and_scan_errors_fail_closed(self) -> None:
        self.assertGreater(REAL_WATCHDOG_HARD_DEADLINE, sum(REAL_STAGE_TIMEOUTS.values()))
        with tempfile.TemporaryDirectory(prefix="p7c13-watchdog-probe-") as directory:
            result = OwnedParentChildWatchdog(group_scan_error_probe=lambda _: 1).run((sys.executable, "-c", "pass"), result_path=Path(directory) / "missing")
            self.assertEqual("RESIDUAL_OWNED_GROUP", result.status)
            self.assertEqual(1, result.group_scan_errors)

    def test_turn3_explicit_escalation_prompt_and_real_wire_ordinal_sequence(self) -> None:
        target = "/root/p7c13-explicit-synthetic"
        prompt = c11_explicit_escalation_prompt(target)
        for phrase in ("first and only tool call", TURN3_SANDBOX_PERMISSION, "Do not first try", "Do not retry"):
            self.assertIn(phrase, prompt)
        with tempfile.TemporaryDirectory(prefix="p7c13-wire-") as directory:
            base = Path(directory)
            actual_target = base / "target"
            authority = RootOnlyWireCommandAuthority(base / "wire.json")
            journal = RootOnlyApprovalRecoveryJournal(base / "journal.json")
            operator = ProductionApprovalOperator(profile_id="p", thread_id="thread", cwd="/root/work", target=actual_target, budget=EffectBudget(), wire_authority=authority, recovery_journal=journal)
            operator.turn_binding = TurnBinding("p", "thread", "turn-3")
            command = shlex.join(["/bin/bash", "-lc", f"touch {actual_target}"])
            request = ApprovalRequest(7, "p", "request-1", ApprovalKind.COMMAND_EXECUTION, "thread", "turn-3", "item", ("cwd: /root/work", f"command: {command}"))
            self.assertIs(asyncio.run(operator.decide(request)), ApprovalDecision.ALLOW)
            wire = authority.read()
            self.assertEqual(1, wire["request_ordinal"])
            self.assertEqual(7, wire["local_sequence"])
            self.assertEqual(1, operator.request_count)
            with self.assertRaises(PreparationGateError):
                authority.capture_once(request=request, request_ordinal=1, target=str(actual_target))

    def test_wrong_kind_and_cwd_are_one_response_denies_without_allow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p7c13-deny-") as directory:
            target = Path(directory) / "target"
            operator = ProductionApprovalOperator(profile_id="p", thread_id="thread", cwd="/root/work", target=target, budget=EffectBudget(), wire_authority=RootOnlyWireCommandAuthority(Path(directory) / "wire.json"), recovery_journal=RootOnlyApprovalRecoveryJournal(Path(directory) / "journal.json"))
            operator.turn_binding = TurnBinding("p", "thread", "turn-3")
            wrong = ApprovalRequest(4, "p", "request-1", ApprovalKind.FILE_CHANGE, "thread", "turn-3", "item", ("cwd: /root/work",))
            self.assertIs(asyncio.run(operator.decide(wrong)), ApprovalDecision.DENY)
            self.assertEqual(1, operator.budget.count("approval_responses"))
            self.assertEqual(0, operator.allow_count)
            cwd_mismatch = ApprovalRequest(5, "p", "request-2", ApprovalKind.COMMAND_EXECUTION, "thread", "turn-3", "item", ("cwd: /root/other", "command: touch /wrong"))
            with self.assertRaises(PreparationGateError):
                asyncio.run(operator.decide(cwd_mismatch))

    def test_recovery_classes_are_terminal_and_not_success(self) -> None:
        self.assertEqual("UNKNOWN", map_terminal_recovery_class(official_status="DELETE_UNKNOWN", application_status=DialogueDeleteStatus.UNKNOWN.value))
        self.assertEqual("CONFIRMED_PENDING", map_terminal_recovery_class(official_status="DELETE_CONFIRMED", application_status=DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE.value))
        self.assertEqual("COMPLETED", map_terminal_recovery_class(official_status="DELETE_CONFIRMED", application_status=DialogueDeleteStatus.DELETED.value))
        self.assertEqual("FAILED", map_terminal_recovery_class(official_status="DELETE_CONFIRMED", application_status="ERROR"))

    def test_production_oracle_has_observed_delete_inputs_and_separate_quiescence(self) -> None:
        source = inspect.getsource(ProductionRealChildOrchestrator.run_async)
        for forbidden in ("official_delete=ThreadOperationStatus.DELETE_CONFIRMED.value", "tombstone_bounded=True", "isolated_sqlite_descendants=0", "isolated_logs_descendants=0"):
            self.assertNotIn(forbidden, source)
        self.assertIn("runtime_child_quiescent", inspect.getsource(_child_result_payload))
        self.assertIn("parent_process_group_quiescent", inspect.getsource(_child_result_payload))

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
        official = OfficialDeleteObservation(lifecycle)
        service = DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=official,
            local_cleanup=self._cleanup(), now_ms=lambda: 100,
        )
        result = await service.delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.DELETED)
        self.assertEqual(lifecycle.calls, 1)
        self.assertEqual(1, official.calls)
        self.assertIs(official.status, ThreadOperationStatus.DELETE_CONFIRMED)
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
    if "--p7c13-real-run" in arguments:
        try:
            result = future_real_cli_entrypoint()
        except PreparationGateError:
            return 2
        return 0 if getattr(result, "status", None) in (None, "COMPLETED") else 1
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
