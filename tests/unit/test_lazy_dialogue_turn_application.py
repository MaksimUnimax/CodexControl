import inspect
import unittest
from dataclasses import fields, is_dataclass

from codex_control.application import (
    CreationRecoveryResult,
    CreationRecoveryStatus,
    DialogueTurnService,
    ThreadLifecyclePort,
)


class LazyDialogueTurnApplicationUnitTests(unittest.TestCase):
    def test_exact_public_surface_and_recovery_records(self):
        self.assertEqual({"start"}, {
            name for name, value in inspect.getmembers(ThreadLifecyclePort)
            if callable(value) and not name.startswith("_")
        })
        self.assertEqual({"execute", "recover_preexisting_creation"}, {
            name for name, value in inspect.getmembers(DialogueTurnService)
            if callable(value) and not name.startswith("_")
        })
        self.assertEqual(["NO_ACTION", "MARKED_UNKNOWN"], [item.value for item in CreationRecoveryStatus])
        self.assertTrue(is_dataclass(CreationRecoveryResult))
        self.assertEqual(["status", "dialogue"], [item.name for item in fields(CreationRecoveryResult)])
        self.assertTrue(getattr(CreationRecoveryResult, "__dataclass_params__").frozen)

    def test_public_protocol_has_no_resume_or_delete(self):
        self.assertNotIn("resume", dir(ThreadLifecyclePort))
        self.assertNotIn("delete", dir(ThreadLifecyclePort))
        self.assertNotIn("run_forever", dir(ThreadLifecyclePort))


if __name__ == "__main__":
    unittest.main()
