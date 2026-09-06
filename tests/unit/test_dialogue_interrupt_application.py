import inspect
import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass

from codex_control.adapters.codex.turn_lifecycle import TurnBinding
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueInterruptError,
    DialogueInterruptErrorCategory,
    DialogueInterruptReason,
    DialogueInterruptRequest,
    DialogueInterruptResult,
    DialogueInterruptService,
    DialogueInterruptStatus,
    InterruptRecoveryResult,
    InterruptRecoveryStatus,
)
from codex_control.storage import SqliteStorage


class _Lifecycle:
    async def interrupt_turn(self, binding):
        raise AssertionError

    async def wait_turn(self, binding):
        raise AssertionError


class DialogueInterruptApplicationUnitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=lambda: 1
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def test_exact_enums_records_and_surfaces(self):
        self.assertEqual(
            ["CONFIRMED", "RECONCILED", "REJECTED", "UNKNOWN", "BLOCKED", "CONFLICT"],
            [item.value for item in DialogueInterruptStatus],
        )
        self.assertEqual(
            ["NO_DIALOGUE", "DIALOGUE_NOT_RUNNING", "JOB_NOT_RUNNING",
             "ACTIVE_BINDING_UNAVAILABLE", "INTERRUPT_IN_PROGRESS", "STALE_REQUEST"],
            [item.value for item in DialogueInterruptReason],
        )
        self.assertEqual(["NO_ACTION", "MARKED_UNKNOWN"], [item.value for item in InterruptRecoveryStatus])
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "INVARIANT"], [item.value for item in DialogueInterruptErrorCategory])
        self.assertEqual({"interrupt", "recover_preexisting_interrupt"}, {
            name for name, value in inspect.getmembers(DialogueInterruptService)
            if callable(value) and not name.startswith("_")
        })
        self.assertEqual(["dialogue_id", "job_id", "expected_dialogue_version", "expected_job_version"],
                         [field.name for field in fields(DialogueInterruptRequest)])
        self.assertEqual(["status", "job", "dialogue", "output_payload", "reason"],
                         [field.name for field in fields(DialogueInterruptResult)])
        self.assertEqual(["status", "job", "dialogue"],
                         [field.name for field in fields(InterruptRecoveryResult)])
        self.assertTrue(all(is_dataclass(record) for record in (
            DialogueInterruptRequest, DialogueInterruptResult, InterruptRecoveryResult
        )))

    def test_records_are_frozen_and_request_has_no_wire_identity(self):
        request = DialogueInterruptRequest("dialogue", "job", 0, 0)
        self.assertNotIn("thread", repr(request))
        self.assertNotIn("turn", repr(request))
        with self.assertRaises(FrozenInstanceError):
            request.job_id = "other"
        result = DialogueInterruptResult(DialogueInterruptStatus.UNKNOWN, None, None, None, None)
        recovery = InterruptRecoveryResult(InterruptRecoveryStatus.NO_ACTION, None, None)
        self.assertNotIn("PRIVATE_OUTPUT", repr(result))
        self.assertNotIn("PRIVATE_THREAD", repr(result))
        self.assertNotIn("PRIVATE_OUTPUT", repr(recovery))

    def test_request_validation_and_finite_error(self):
        valid = (
            ("d", "j", 0, 0),
            ("d", "j", 9_223_372_036_854_775_807, 9_223_372_036_854_775_807),
        )
        for args in valid:
            DialogueInterruptRequest(*args)
        invalid = (
            ("", "j", 0, 0), ("d\x00", "j", 0, 0), ("d", "", 0, 0),
            ("d", "j\x00", 0, 0), ("d", "j", True, 0), ("d", "j", -1, 0),
            ("d", "j", 0, True), ("d", "j", 0, -1),
            ("d", "j", 9_223_372_036_854_775_808, 0),
        )
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(DialogueInterruptError) as raised:
                DialogueInterruptRequest(*args)
            self.assertIs(raised.exception.category, DialogueInterruptErrorCategory.INVALID_ARGUMENT)
        error = DialogueInterruptError("PRIVATE_RAW_ADAPTER_ERROR")
        self.assertEqual("INVARIANT", str(error))
        self.assertNotIn("PRIVATE_RAW_ADAPTER_ERROR", repr(error))
        self.assertNotIn("CODEX_HOME", repr(error))

    def test_constructor_and_port_reject_invalid_values(self):
        registry = ActiveTurnRegistry()
        with self.assertRaises(DialogueInterruptError):
            DialogueInterruptService(object(), server_id="server", active_turn_registry=registry, turn_lifecycle=_Lifecycle())
        with self.assertRaises(DialogueInterruptError):
            DialogueInterruptService(self.storage, server_id="", active_turn_registry=registry, turn_lifecycle=_Lifecycle())
        with self.assertRaises(DialogueInterruptError):
            DialogueInterruptService(self.storage, server_id="server", active_turn_registry=object(), turn_lifecycle=_Lifecycle())
        with self.assertRaises(DialogueInterruptError):
            DialogueInterruptService(self.storage, server_id="server", active_turn_registry=registry, turn_lifecycle=object())

    def test_registry_identity_and_stale_cleanup(self):
        registry = ActiveTurnRegistry()
        first = TurnBinding("profile", "thread", "turn-a")
        second = TurnBinding("profile", "thread", "turn-b")
        owner_a = registry.publish("job-a", first)
        self.assertIs(first, registry.lookup("job-a"))
        with self.assertRaises(RuntimeError):
            registry.publish("job-a", second)
        registry.retire("job-a", owner_a)
        owner_b = registry.publish("job-b", second)
        registry.retire("job-b", owner_a)
        self.assertIs(second, registry.lookup("job-b"))
        registry.retire("job-b", owner_b)
        self.assertIsNone(registry.lookup("job-b"))
        self.assertNotIn("profile", repr(registry))
        self.assertNotIn("thread", repr(registry))
        self.assertNotIn("turn-a", repr(registry))

    async def test_invalid_public_request_is_before_storage(self):
        service = DialogueInterruptService(
            self.storage, server_id="server", active_turn_registry=ActiveTurnRegistry(), turn_lifecycle=_Lifecycle()
        )
        with self.assertRaises(DialogueInterruptError):
            await service.interrupt(object())
        self.assertEqual(0, await self.storage.read(
            lambda connection: connection.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0]
        ))


if __name__ == "__main__":
    unittest.main()
