import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControllerBootResult,
    ControllerRuntimeRecord,
    DialogueRecord,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsInitializeResult,
    SettingsRecord,
)


class CoreRepositoryRecordTests(unittest.TestCase):
    def test_repository_error_categories_are_finite_and_redacted(self):
        expected = {
            "invalid_argument",
            "not_found",
            "already_exists",
            "version_conflict",
            "state_conflict",
            "clock_invalid",
            "invariant_violation",
        }
        self.assertEqual(expected, {category.value for category in RepositoryErrorCategory})
        error = RepositoryError("PRIVATE_REPOSITORY_ERROR_MUST_NOT_LEAK")
        self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, error.category)
        self.assertEqual("invalid_argument", str(error))
        self.assertEqual("RepositoryError('invalid_argument')", repr(error))
        self.assertNotIn("PRIVATE_REPOSITORY_ERROR_MUST_NOT_LEAK", repr(error))

    def test_records_are_immutable(self):
        runtime = ControllerRuntimeRecord(1, ControllerMode.SLEEP, 2, "fleet", 3, 4)
        boot = ControllerBootResult(runtime, ControllerMode.SLEEP)
        settings = SettingsRecord(None, "model", "high", 0, 3, 3)
        initialized = SettingsInitializeResult(settings, True)
        dialogue = DialogueRecord("d", "s", "p", None, DialogueState.CREATING, 0, 3, 3, None)
        for value, field in (
            (runtime, "boot_generation"),
            (boot, "effective_mode"),
            (settings, "version"),
            (initialized, "created"),
            (dialogue, "state"),
        ):
            with self.subTest(type=type(value).__name__):
                with self.assertRaises(AttributeError):
                    setattr(value, field, None)

    def test_dialogue_state_contains_only_schema_states(self):
        self.assertEqual(
            {
                "CREATING", "IDLE", "CREATE_UNKNOWN", "ERROR", "TURN_RUNNING",
                "INTERRUPTING", "TURN_UNKNOWN", "DELETE_PENDING", "DELETING", "DELETE_UNKNOWN",
            },
            {state.value for state in DialogueState},
        )

    def test_records_do_not_have_content_or_live_slot_fields(self):
        self.assertNotIn("live_slot", DialogueRecord.__dataclass_fields__)
        self.assertNotIn("content", DialogueRecord.__dataclass_fields__)
        self.assertNotIn("secret", SettingsRecord.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
