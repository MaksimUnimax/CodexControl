import asyncio
import inspect
import os
import tempfile
import unittest

from codex_control.application import (
    LocalGroupResult,
    LocalOrchestrationError,
    LocalOrchestrationErrorCategory,
    LocalStartupResult,
    LocalStartupStatus,
    P63_STARTUP_DELIVERY_MAX_JOBS,
    P63_WORK_STATUS_TEXT_MAX_CHARS,
    WorkStatusAttempt,
)
from codex_control.application.dialogue_recovery import DialogueRecoveryResult, DialogueRecoveryStatus
from codex_control.application.fleet_control import FleetControlResult, FleetControlStatus, FleetModeSnapshot
from codex_control.application.fleet_group_routing import GroupRoutingResult, GroupRoutingStatus
from codex_control.domain import ControllerMode
from codex_control.storage import TurnJobRepository


class LocalOrchestrationUnitTests(unittest.TestCase):
    def test_constants_errors_and_redacted_records(self):
        self.assertEqual(256, P63_STARTUP_DELIVERY_MAX_JOBS)
        self.assertEqual(1024, P63_WORK_STATUS_TEXT_MAX_CHARS)
        self.assertEqual([item.value for item in WorkStatusAttempt], ["SKIPPED", "CONFIRMED", "FAILED", "UNKNOWN"])
        self.assertEqual([item.value for item in LocalStartupStatus], ["READY", "LIMIT_REACHED"])
        self.assertEqual(
            [item.value for item in LocalOrchestrationErrorCategory],
            ["INVALID_ARGUMENT", "STORAGE", "CODEX", "TELEGRAM", "INVARIANT"],
        )
        self.assertEqual(LocalOrchestrationErrorCategory.INVARIANT, LocalOrchestrationError("bad").category)
        self.assertNotIn("prompt", repr(LocalOrchestrationError(LocalOrchestrationErrorCategory.STORAGE)))
        unauthorized = GroupRoutingResult(
            GroupRoutingStatus.UNAUTHORIZED,
            None,
            FleetControlResult(FleetControlStatus.UNAUTHORIZED, None),
            None,
            None,
            None,
        )
        self.assertEqual(
            "LocalGroupResult(routing='[REDACTED]', delivery='[REDACTED]', fleet_status_payload='[REDACTED]', acknowledgement_status='SKIPPED', terminal_status='SKIPPED')",
            repr(LocalGroupResult(unauthorized, None, None, WorkStatusAttempt.SKIPPED, WorkStatusAttempt.SKIPPED)),
        )

    def test_startup_result_is_frozen_and_bound(self):
        recovery = DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, None)
        result = LocalStartupResult(LocalStartupStatus.READY, recovery, (), 0)
        self.assertIn("dialogue_recovery='[REDACTED]'", repr(result))
        with self.assertRaises(LocalOrchestrationError):
            LocalStartupResult(LocalStartupStatus.LIMIT_REACHED, recovery, (), 0)

    def test_public_orchestration_surfaces_are_narrow(self):
        from codex_control.application import ApprovalAwareTurnLifecycle, LocalControllerOrchestrator

        self.assertEqual(
            {name for name, value in vars(ApprovalAwareTurnLifecycle).items() if not name.startswith("_") and callable(value)},
            {"start_turn", "wait_turn", "interrupt_turn"},
        )
        self.assertEqual(
            {name for name, value in vars(LocalControllerOrchestrator).items() if not name.startswith("_") and callable(value)},
            {"handle_group", "handle_private_command", "handle_private_callback", "recover_startup"},
        )
        self.assertTrue(inspect.iscoroutinefunction(ApprovalAwareTurnLifecycle.start_turn))

    def test_delivery_discovery_rejects_bool_limit_before_storage(self):
        async def check():
            with tempfile.TemporaryDirectory() as directory:
                storage = await __import__("codex_control.storage", fromlist=["SqliteStorage"]).SqliteStorage.open(
                    os.path.join(directory, "state.sqlite3"), now_ms=lambda: 1
                )
                try:
                    with self.assertRaises(Exception):
                        await TurnJobRepository(storage).list_delivery_candidates(limit=True)
                finally:
                    await storage.close()
        asyncio.run(check())
