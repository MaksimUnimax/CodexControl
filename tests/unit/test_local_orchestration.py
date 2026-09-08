import asyncio
import inspect
import os
import tempfile
import unittest

from codex_control.application import (
    ApprovalAwareTurnLifecycle,
    ApprovalDecisionSignal,
    LocalControllerOrchestrator,
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

    def test_controller_requires_the_lifecycle_approval_signal_identity(self):
        class AsyncSurface:
            async def handle(self, value):
                return value

            async def handle_command(self, value):
                return value

            async def handle_callback(self, value):
                return value

            async def deliver(self, value):
                return value

            async def recover_startup(self):
                return value

        class Projection:
            def project(self, value):
                return value

        class Renderer:
            def render(self, value):
                return {"text": "status"}

        async def check():
            with tempfile.TemporaryDirectory() as directory:
                storage = await __import__("codex_control.storage", fromlist=["SqliteStorage"]).SqliteStorage.open(
                    os.path.join(directory, "state.sqlite3"), now_ms=lambda: 1
                )
                try:
                    signal_a = ApprovalDecisionSignal()
                    signal_b = ApprovalDecisionSignal()
                    lifecycle = object.__new__(ApprovalAwareTurnLifecycle)
                    lifecycle._approval_signal = signal_a
                    services = AsyncSurface()
                    with self.assertRaises(LocalOrchestrationError) as mismatch:
                        LocalControllerOrchestrator(
                            storage, group_routing=services, fleet_status=Projection(),
                            fleet_status_renderer=Renderer(), private_control=services,
                            turn_delivery=services, turn_lifecycle=lifecycle,
                            approval_signal=signal_b, dialogue_recovery=services,
                        )
                    self.assertEqual(LocalOrchestrationErrorCategory.INVALID_ARGUMENT, mismatch.exception.category)
                    controller = LocalControllerOrchestrator(
                        storage, group_routing=services, fleet_status=Projection(),
                        fleet_status_renderer=Renderer(), private_control=services,
                        turn_delivery=services, turn_lifecycle=lifecycle,
                        approval_signal=signal_a, dialogue_recovery=services,
                    )
                    self.assertIs(signal_a, controller._approval_signal)
                finally:
                    await storage.close()

        asyncio.run(check())

    def test_delivery_discovery_rejects_zero_and_upper_bound_before_storage(self):
        async def check():
            with tempfile.TemporaryDirectory() as directory:
                storage = await __import__("codex_control.storage", fromlist=["SqliteStorage"]).SqliteStorage.open(
                    os.path.join(directory, "state.sqlite3"), now_ms=lambda: 1
                )
                try:
                    repository = TurnJobRepository(storage)
                    for invalid in (0, 4097, "1"):
                        with self.assertRaises(Exception):
                            await repository.list_delivery_candidates(limit=invalid)
                finally:
                    await storage.close()

        asyncio.run(check())
