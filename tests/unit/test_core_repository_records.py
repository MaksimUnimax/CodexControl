import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControllerBootResult,
    ControllerRuntimeRepository,
    ControllerRuntimeRecord,
    DialogueRecord,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsInitializeResult,
    SettingsRepository,
    SettingsRecord,
    DialogueRepository,
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

        for category in RepositoryErrorCategory:
            with self.subTest(category=category):
                value = RepositoryError(category)
                self.assertEqual(category.value, str(value))
                self.assertEqual(f"RepositoryError({category.value!r})", repr(value))
                self.assertFalse(hasattr(value, "retryable"))
                self.assertFalse(hasattr(value, "safe_to_retry"))

    def test_repository_error_unknown_constructor_text_maps_without_leaking(self):
        value = RepositoryError("PRIVATE_REPOSITORY_ERROR_TEXT_MUST_NOT_LEAK")
        self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, value.category)
        self.assertEqual("invalid_argument", str(value))
        self.assertEqual("RepositoryError('invalid_argument')", repr(value))
        self.assertNotIn("PRIVATE_REPOSITORY_ERROR_TEXT_MUST_NOT_LEAK", str(value))
        self.assertNotIn("PRIVATE_REPOSITORY_ERROR_TEXT_MUST_NOT_LEAK", repr(value))

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

    def test_public_repository_callable_surface_is_exact(self):
        def defined_public_callables(repository_type):
            return {
                name for name, value in vars(repository_type).items()
                if not name.startswith("_") and callable(value)
            }

        self.assertEqual(
            {"get", "begin_boot"},
            defined_public_callables(ControllerRuntimeRepository),
        )
        self.assertEqual(
            {"get", "initialize_if_absent", "replace"},
            defined_public_callables(SettingsRepository),
        )
        self.assertEqual(
            {"get_live", "create_intent", "confirm_created", "mark_create_unknown", "mark_create_error"},
            defined_public_callables(DialogueRepository),
        )
        self.assertNotIn("accept_control", defined_public_callables(ControllerRuntimeRepository))
        self.assertNotIn("transition", defined_public_callables(DialogueRepository))
        self.assertNotIn("delete", defined_public_callables(DialogueRepository))


if __name__ == "__main__":
    unittest.main()
