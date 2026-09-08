import asyncio
import unittest
from dataclasses import FrozenInstanceError, fields

from codex_control.application import (
    DialogueTurnPort,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnStatus,
    FleetControlPort,
    FleetControlResult,
    FleetControlStatus,
    FleetModeSnapshot,
    GroupRoutingError,
    GroupRoutingErrorCategory,
    GroupRoutingReason,
    GroupRoutingResult,
    GroupRoutingStatus,
)
from codex_control.domain import ControllerMode
from codex_control.storage import IngressDispositionKind, TurnJobRecord, TurnJobState


class _AsyncFleet:
    async def handle(self, update):
        return FleetControlResult(FleetControlStatus.MALFORMED, None)


class _AsyncTurns:
    async def execute(self, request):
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, None, None, None)


class FleetGroupRoutingContractTests(unittest.TestCase):
    @staticmethod
    def _terminal_turn_result():
        job = TurnJobRecord(
            job_id="job-synthetic",
            telegram_update_id=7,
            source_chat_id=-100,
            source_message_id=8,
            dialogue_id="dialogue-synthetic",
            server_id="SERVER",
            profile_id="profile-synthetic",
            thread_id="thread-synthetic",
            model_id="model-synthetic",
            reasoning_effort="high",
            input_sha256="input-hash-synthetic",
            codex_turn_id="turn-synthetic",
            state=TurnJobState.DELIVERED,
            version=1,
            created_at_ms=10,
            updated_at_ms=11,
            error_class=None,
        )
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.COMPLETED, job, None, None, None)

    def _prompt(self, snapshot):
        return GroupRoutingResult(
            GroupRoutingStatus.PROMPT,
            snapshot,
            None,
            self._terminal_turn_result(),
            IngressDispositionKind.JOB,
            None,
        )

    def test_exact_public_enum_order(self):
        self.assertEqual(
            ["CONTROL", "STATUS", "PROMPT", "DUPLICATE", "BUSY", "BLOCKED", "IGNORED_SLEEP", "REJECTED", "UNAUTHORIZED", "UNSUPPORTED", "MALFORMED"],
            [item.value for item in GroupRoutingStatus],
        )
        self.assertEqual(
            ["STALE_PROMPT", "LOCAL_PROMPT_IN_FLIGHT", "IN_FLIGHT_DUPLICATE", "INVALID_PROMPT"],
            [item.value for item in GroupRoutingReason],
        )
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "CODEX", "INVARIANT"], [item.value for item in GroupRoutingErrorCategory])

    def test_accepted_p51_and_p3_enum_authority_is_unchanged(self):
        self.assertEqual(
            ["APPLIED", "STALE", "DUPLICATE", "STATUS", "TEXT", "UNAUTHORIZED", "UNSUPPORTED", "MALFORMED"],
            [item.value for item in FleetControlStatus],
        )
        self.assertEqual(
            ["COMPLETED", "FAILED", "UNKNOWN", "DUPLICATE", "BUSY", "BLOCKED"],
            [item.value for item in ExistingDialogueTurnStatus],
        )
        self.assertEqual(
            ["NO_DIALOGUE", "DIALOGUE_NOT_READY", "SETTINGS_MISSING", "SETTINGS_PROFILE_MISMATCH", "PROFILE_NOT_CONFIGURED", "MODEL_NOT_CONFIGURED", "MODEL_UNAVAILABLE", "WORKING_DIRECTORY_UNAVAILABLE", "DUPLICATE_NON_JOB", "DUPLICATE_ORPHAN_JOB", "SETTINGS_CHANGED"],
            [item.value for item in ExistingDialogueTurnReason],
        )

    def test_result_is_frozen_and_has_exact_fields(self):
        self.assertEqual(
            ["status", "snapshot", "control_result", "turn_result", "disposition", "reason"],
            [item.name for item in fields(GroupRoutingResult)],
        )
        result = GroupRoutingResult(
            GroupRoutingStatus.DUPLICATE,
            None,
            None,
            None,
            IngressDispositionKind.IGNORED_SLEEP,
            None,
        )
        with self.assertRaises(FrozenInstanceError):
            result.status = GroupRoutingStatus.CONTROL

    def test_nested_results_and_error_repr_are_redacted(self):
        snapshot = FleetModeSnapshot("SERVER", ControllerMode.ACTIVE, 1, 2, "fleet")
        control = FleetControlResult(FleetControlStatus.STATUS, snapshot)
        result = GroupRoutingResult(GroupRoutingStatus.STATUS, snapshot, control, None, None, None)
        self.assertNotIn("control_result", repr(result))
        self.assertNotIn("control_result", repr(result))
        self.assertNotIn("synthetic prompt", repr(result))
        error = GroupRoutingError(GroupRoutingErrorCategory.CODEX)
        self.assertEqual("CODEX", str(error))
        self.assertEqual("GroupRoutingError('CODEX')", repr(error))
        self.assertNotIn("exception body", repr(error))

    def test_port_surfaces_are_async(self):
        self.assertTrue(hasattr(FleetControlPort, "handle"))
        self.assertTrue(hasattr(DialogueTurnPort, "execute"))
        self.assertTrue(asyncio.iscoroutinefunction(_AsyncFleet.handle))
        self.assertTrue(asyncio.iscoroutinefunction(_AsyncTurns.execute))

    def test_canonical_shapes_and_local_busy_shape(self):
        snapshot = FleetModeSnapshot("SERVER", ControllerMode.ACTIVE, 1, 2, "fleet")
        local = GroupRoutingResult(
            GroupRoutingStatus.BUSY,
            snapshot,
            None,
            None,
            IngressDispositionKind.IGNORED_REJECTED,
            GroupRoutingReason.LOCAL_PROMPT_IN_FLIGHT,
        )
        self.assertIsNone(local.turn_result)
        p3_busy = ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BUSY, None, None, None, None)
        delegated = GroupRoutingResult(
            GroupRoutingStatus.BUSY,
            snapshot,
            None,
            p3_busy,
            IngressDispositionKind.IGNORED_REJECTED,
            None,
        )
        self.assertIs(p3_busy, delegated.turn_result)
        with self.assertRaises(GroupRoutingError) as raised:
            GroupRoutingResult(GroupRoutingStatus.BUSY, snapshot, None, None, IngressDispositionKind.IGNORED_REJECTED, None)
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)

    def test_prompt_requires_exact_active_snapshot(self):
        snapshot = FleetModeSnapshot("SERVER", ControllerMode.ACTIVE, 1, 2, "fleet")
        result = self._prompt(snapshot)
        self.assertIs(GroupRoutingStatus.PROMPT, result.status)
        self.assertIs(snapshot, result.snapshot)

    def test_prompt_none_snapshot_fails_invariant(self):
        with self.assertRaises(GroupRoutingError) as raised:
            self._prompt(None)
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)

    def test_prompt_sleep_snapshot_fails_invariant(self):
        snapshot = FleetModeSnapshot("SERVER", ControllerMode.SLEEP, 1, 2, "fleet")
        with self.assertRaises(GroupRoutingError) as raised:
            self._prompt(snapshot)
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, raised.exception.category)

    def test_invalid_result_relations_fail_closed(self):
        snapshot = FleetModeSnapshot("SERVER", ControllerMode.SLEEP, 1, 2, "fleet")
        control = FleetControlResult(FleetControlStatus.STATUS, snapshot)
        cases = (
            (GroupRoutingStatus.CONTROL, snapshot, control, None, IngressDispositionKind.JOB, None),
            (GroupRoutingStatus.STATUS, snapshot, None, None, None, None),
            (GroupRoutingStatus.REJECTED, snapshot, None, None, IngressDispositionKind.IGNORED_SLEEP, GroupRoutingReason.STALE_PROMPT),
            (GroupRoutingStatus.IGNORED_SLEEP, snapshot, None, None, IngressDispositionKind.IGNORED_SLEEP, None),
        )
        for args in cases[:3]:
            with self.subTest(args=args), self.assertRaises(GroupRoutingError):
                GroupRoutingResult(*args)
        self.assertIs(GroupRoutingStatus.IGNORED_SLEEP, GroupRoutingResult(*cases[3]).status)

    def test_error_categories_are_finite_and_content_free(self):
        self.assertIs(GroupRoutingErrorCategory.INVARIANT, GroupRoutingError("not-a-category").category)
        self.assertEqual("INVALID_ARGUMENT", str(GroupRoutingError(GroupRoutingErrorCategory.INVALID_ARGUMENT)))


if __name__ == "__main__":
    unittest.main()
