"""P7.C13 final hard-delete acceptance preparation.

This module is preparation-only.  The offline harness models the future
one-shot protocol and exercises the accepted production delete chain against
synthetic temporary state.  The future-real entry point requires an
architect-supplied contract object and is deliberately unreachable during
ordinary discovery.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shlex
import stat
import tempfile
import unittest
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping, Sequence
from unittest.mock import patch

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex import persistent_scanner as scanner_module
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.adapters.codex.thread_lifecycle import (
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


P7C13_BASE_SHA = "a5c66a778800d1c5ee5811d97d961fe0dccd677c"
P7C13_BASE_TREE = "e6a46445d11d660a50891eabf412b01aef883fca"
P7C12_MATCHER_BLOB = "f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1"
ARCHITECT_MAIN_HEAD = "ddc3cb48cbe82bcee6d2b5387774287b66d582fb"
ARCHITECT_MAIN_TREE = "c6288dfefecce00bbca7e6ff84aacda4b20fce8d"
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


class PreparationGateError(RuntimeError):
    """Finite fail-closed preparation gate error."""


@dataclass(frozen=True)
class FutureArchitectContract:
    """Values a later architect execution contract must supply out of band."""

    authorization_token: str
    expected_head: str
    expected_tree: str


def future_real_gate(
    environ: Mapping[str, str],
    contract: FutureArchitectContract | None,
    *,
    current_head: str | None = None,
    current_tree: str | None = None,
) -> bool:
    """Return true only for a later exact contract; never acquires anything."""
    if contract is None:
        return False
    if not all((contract.authorization_token, contract.expected_head, contract.expected_tree)):
        return False
    return (
        environ.get(FUTURE_GATE_ENV) == contract.authorization_token
        and environ.get("P7C13_EXPECTED_HEAD") == contract.expected_head
        and environ.get("P7C13_EXPECTED_TREE") == contract.expected_tree
        and current_head == contract.expected_head
        and current_tree == contract.expected_tree
    )


def future_real_entrypoint(
    *, environ: Mapping[str, str], contract: FutureArchitectContract | None,
    current_head: str | None = None, current_tree: str | None = None,
) -> None:
    """Preparation deliberately has no real executor after the gate."""
    if not future_real_gate(environ, contract, current_head=current_head, current_tree=current_tree):
        raise PreparationGateError("P7C13_FUTURE_REAL_GATE=DISABLED")
    raise PreparationGateError("P7C13_REAL_EXECUTOR_REQUIRES_SEPARATE_AUTHORIZED_SLICE")


@dataclass
class EffectBudget:
    limits: Mapping[str, int] = field(default_factory=lambda: FROZEN_EFFECT_BUDGET)
    counts: dict[str, int] = field(default_factory=dict)

    def record(self, effect: str) -> None:
        value = self.counts.get(effect, 0) + 1
        if value > self.limits.get(effect, 0):
            raise PreparationGateError(f"effect budget exceeded: {effect}")
        self.counts[effect] = value

    def count(self, effect: str) -> int:
        return self.counts.get(effect, 0)


@dataclass(frozen=True)
class FlowBinding:
    thread_id: str
    turn_id: str
    cwd: str
    local_sequence: int


class Terminal(StrEnum):
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    UNKNOWN = "UNKNOWN"


@dataclass
class OfflineFutureFlow:
    """Finite model of the four future turns and the delete eligibility gates."""

    budget: EffectBudget = field(default_factory=EffectBudget)
    binding: FlowBinding = field(default_factory=lambda: FlowBinding("thread-13", "turn-1", "/root/work-13", 1))
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

    def turn1(self) -> bool:
        self.budget.record("model/list")
        self.budget.record("thread/start")
        self.budget.record("new_threads")
        self.budget.record("turn/start")
        self.start_confirmed = True
        self.turn1_terminal = Terminal.COMPLETED
        return True

    def restart_and_resume(self) -> bool:
        if not self.start_confirmed or self.resume_confirmed:
            return False
        self.budget.record("thread/resume")
        self.budget.record("turn/start")
        self.resume_confirmed = True
        self.turn2_terminal = Terminal.COMPLETED
        return True

    def turn2_remembers(self, expected_marker: str) -> bool:
        return bool(
            self.resume_confirmed
            and expected_marker
            and self.turn2_terminal is Terminal.COMPLETED
        )

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
        if not self.resume_confirmed or self.approval_requests:
            return False
        self.budget.record("turn/start")
        self.approval_requests += 1
        if target_exists_before or request is None or expected is None or wire is None:
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

    def turn4_interrupt(self, *, binding: FlowBinding | None, stimulus: str = TURN4_STIMULUS, unknown: bool = False) -> bool:
        if self.turn3_terminal is not Terminal.COMPLETED or self.turn4_terminal is not None:
            return False
        self.budget.record("turn/start")
        if binding != self.binding or stimulus != TURN4_STIMULUS or unknown:
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
            self.interrupt_binding == self.binding,
            predelete_observed,
            idle_binding,
        ))


def _matcher_fixture(target: str, *, thread: str = "thread-13", turn: str = "turn-3", cwd: str = "/root/work-13"):
    command = shlex.join(["/bin/bash", "-lc", f"touch {target}"])
    digest = _sha256(command)
    thread_sha = _sha256(thread)
    turn_sha = _sha256(turn)
    cwd_sha = _sha256(cwd)
    request = c12.CapturedRequest("COMMAND_EXECUTION", 1, 1, thread_sha, turn_sha, cwd_sha, digest)
    expected = c12.ExpectedAuthority("COMMAND_EXECUTION", 1, 1, thread_sha, turn_sha, cwd_sha, target, digest)
    wire = c12.CorrelatedWireRecord(
        "COMMAND_EXECUTION", 1, 1, thread_sha, turn_sha, cwd_sha,
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
    return not target_exists_before


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


class BoundedTargetOracle:
    """No-follow, bounded, target-specific scanner for synthetic fixtures."""

    def __init__(self, profile: CodexProfile, thread_id: str, markers: Sequence[bytes], *, max_bytes: int = 4 * 1024 * 1024) -> None:
        self.profile = profile
        self.thread = thread_id.encode()
        self.markers = tuple(markers)
        self.max_bytes = max_bytes

    @staticmethod
    def _files(root: Path) -> tuple[list[Path], int]:
        if root.is_symlink():
            return [], 1
        if root.is_file():
            return [root], 0
        if not root.is_dir():
            return [], 0
        result: list[Path] = []
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
                try:
                    if entry.is_symlink():
                        errors += 1
                    elif entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        result.append(Path(entry.path))
                    else:
                        errors += 1
                except OSError:
                    errors += 1
        return result, errors

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
        for family, root in roots:
            paths, walk_errors = self._files(root)
            errors += walk_errors
            for path in paths:
                found_thread, found_marker, _ = self._count(path)
                thread_count += found_thread
                marker_count += found_marker
                if found_thread or found_marker:
                    families.add(family)
        return OracleObservation(thread_count, marker_count, errors, tuple(sorted(families)), marker_hash)


def post_delete_acceptance(
    *, official_delete: str, application_result: str, tombstone_bounded: bool,
    live_binding: bool, envelope_valid: bool, isolated_sqlite_descendants: int,
    isolated_logs_descendants: int, persistent: OracleObservation,
    isolated: OracleObservation, scan_errors: int, owned_children: int,
    owned_group_active: bool, owned_group_zombies: int,
    unrelated_signals: int, budgets_ok: bool,
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
        budgets_ok,
    ))


@dataclass(frozen=True)
class WatchdogResult:
    status: str
    second_child: bool = False
    retry: bool = False


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


@dataclass
class OneShotLatch:
    reserved: bool = False
    completed: bool = False

    def reserve(self) -> bool:
        if self.reserved or self.completed:
            return False
        self.reserved = True
        return True

    def finish(self) -> None:
        if not self.reserved:
            raise PreparationGateError("latch was not reserved")
        self.completed = True


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

    def test_turn3_exact_match_is_one_allow_and_target_must_start_absent(self) -> None:
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        target = "/root/p7c13-approval-synthetic"
        request, expected, wire = _matcher_fixture(target, turn="turn-3")
        self.assertTrue(validate_approval_target(target, cwd="/root/work-13", workdir="/root/work-13", repository="/root/CodexControl", isolated_root="/root/p7c13-state", controller_root="/root/p7c13-controller", target_exists_before=False))
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
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        self.assertFalse(flow.approval_candidate(target=expected.target, target_exists_before=True, request=request, expected=expected, wire=wire))
        self.assertFalse(flow.delete_reachable(predelete_observed=True))

    def test_turn4_is_separate_sleep_interrupt_and_unknown_fails(self) -> None:
        flow = OfflineFutureFlow()
        flow.turn1()
        flow.restart_and_resume()
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        flow.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        self.assertTrue(flow.turn4_interrupt(binding=flow.binding))
        self.assertEqual(flow.budget.count("turn/interrupt"), 1)
        self.assertEqual(flow.allow_responses, 1)
        self.assertFalse(flow.turn4_unexpected_approval())
        self.assertFalse(flow.turn4_interrupt(binding=flow.binding))
        unknown = OfflineFutureFlow()
        unknown.turn1()
        unknown.restart_and_resume()
        unknown.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        self.assertFalse(unknown.turn4_interrupt(binding=unknown.binding, unknown=True))
        self.assertEqual(unknown.budget.count("turn/interrupt"), 0)

    def test_delete_is_unreachable_until_all_turn_and_predelete_gates_pass(self) -> None:
        flow = OfflineFutureFlow()
        self.assertFalse(flow.delete_reachable(predelete_observed=True))
        flow.turn1()
        flow.restart_and_resume()
        request, expected, wire = _matcher_fixture("/root/p7c13-approval-synthetic")
        flow.approval_candidate(target=expected.target, request=request, expected=expected, wire=wire)
        flow.turn4_interrupt(binding=flow.binding)
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
        latch = OneShotLatch()
        self.assertTrue(latch.reserve())
        self.assertFalse(latch.reserve())
        latch.finish()
        self.assertFalse(latch.reserve())

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


if __name__ == "__main__":
    unittest.main()
