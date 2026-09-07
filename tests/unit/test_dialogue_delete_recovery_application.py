import inspect
import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass

from codex_control.application import (
    DialogueDeleteError,
    DialogueDeleteErrorCategory,
    DialogueDeleteReason,
    DialogueDeleteRequest,
    DialogueDeleteResult,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueRecoveryError,
    DialogueRecoveryErrorCategory,
    DialogueRecoveryResult,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.storage import SqliteStorage


class _DeleteLifecycle:
    async def delete(self, *, binding):
        raise AssertionError


class _Interrupt:
    async def interrupt(self, request):
        raise AssertionError


class DialogueDeleteRecoveryApplicationUnitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=lambda: 1
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def test_exact_public_contracts(self):
        self.assertEqual(
            ["DELETED", "FAILED", "UNKNOWN", "BLOCKED", "CONFLICT"],
            [item.value for item in DialogueDeleteStatus],
        )
        self.assertEqual(
            ["NO_DIALOGUE", "DIALOGUE_NOT_READY", "DELETE_NOT_READY", "INTERRUPT_IN_PROGRESS",
             "INTERRUPT_UNRESOLVED", "DELETE_IN_PROGRESS", "STALE_REQUEST"],
            [item.value for item in DialogueDeleteReason],
        )
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "INVARIANT"],
                         [item.value for item in DialogueDeleteErrorCategory])
        self.assertEqual(["NO_ACTION", "CREATE_MARKED_UNKNOWN", "PRE_EFFECT_FAILED",
                          "TURN_MARKED_UNKNOWN", "INTERRUPT_MARKED_UNKNOWN", "DELETE_MARKED_UNKNOWN"],
                         [item.value for item in DialogueRecoveryStatus])
        self.assertEqual(["STORAGE", "INVARIANT"],
                         [item.value for item in DialogueRecoveryErrorCategory])
        self.assertEqual({"delete"}, {
            name for name, value in inspect.getmembers(DialogueDeleteService)
            if callable(value) and not name.startswith("_")
        })
        self.assertEqual({"recover_startup"}, {
            name for name, value in inspect.getmembers(DialogueRecoveryService)
            if callable(value) and not name.startswith("_")
        })
        self.assertEqual(["dialogue_id", "expected_dialogue_version"],
                         [field.name for field in fields(DialogueDeleteRequest)])
        self.assertEqual(["status", "dialogue", "tombstone", "reason"],
                         [field.name for field in fields(DialogueDeleteResult)])
        self.assertEqual(["status", "job", "dialogue"],
                         [field.name for field in fields(DialogueRecoveryResult)])
        self.assertTrue(all(is_dataclass(record) for record in (
            DialogueDeleteRequest, DialogueDeleteResult, DialogueRecoveryResult
        )))

    def test_frozen_redacted_records_and_finite_errors(self):
        request = DialogueDeleteRequest("dialogue", 0)
        result = DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None)
        recovery = DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, None)
        self.assertNotIn("dialogue", repr(request))
        self.assertNotIn("PRIVATE_THREAD", repr(result))
        self.assertNotIn("PRIVATE_THREAD", repr(recovery))
        with self.assertRaises(FrozenInstanceError):
            request.dialogue_id = "other"
        self.assertEqual("INVARIANT", str(DialogueDeleteError("PRIVATE_RAW")))
        self.assertEqual("INVARIANT", str(DialogueRecoveryError("PRIVATE_RAW")))
        self.assertNotIn("PRIVATE_RAW", repr(DialogueDeleteError("PRIVATE_RAW")))
        self.assertNotIn("PRIVATE_RAW", repr(DialogueRecoveryError("PRIVATE_RAW")))

    async def test_validation_precedes_storage_and_recovery_has_no_external_port(self):
        for args in (("", 0), ("d\x00", 0), ("d", True), ("d", -1),
                     ("d", 9_223_372_036_854_775_808)):
            with self.assertRaises(DialogueDeleteError) as raised:
                DialogueDeleteRequest(*args)
            self.assertIs(raised.exception.category, DialogueDeleteErrorCategory.INVALID_ARGUMENT)
        with self.assertRaises(DialogueDeleteError):
            await DialogueDeleteService(
                self.storage, server_id="server", thread_lifecycle=object()
            ).delete(object())
        recovery = DialogueRecoveryService(self.storage)
        self.assertNotIn("thread_lifecycle", vars(recovery))
        self.assertNotIn("turn_lifecycle", vars(recovery))

    async def test_no_dialogue_recovery_is_zero_effect(self):
        calls = []
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: calls.append(1) or 10)
        result = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, result.status)
        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()
