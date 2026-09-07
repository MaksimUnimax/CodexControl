import unittest
from dataclasses import fields, is_dataclass

from codex_control.adapters.telegram import TelegramPrivateDialoguePanelRenderer
from codex_control.application import (
    PrivateAdminButton,
    PrivateCallbackRequest,
    PrivateDialogueError,
    PrivateDialogueErrorCategory,
    PrivateDialogueOpenRequest,
    PrivateDialoguePanel,
    PrivateDialoguePanelSection,
    PrivateDialogueReason,
    PrivateDialogueResult,
    PrivateDialogueStatus,
)
from codex_control.application.private_settings import (
    P4_PRIVATE_BUTTON_LABEL_MAX_CHARS,
    P4_PRIVATE_PANEL_TEXT_MAX_CHARS,
    PrivatePanelSection,
    PrivateAdminStatus,
    PrivateAdminReason,
)


class PrivateDialogueControlUnitTests(unittest.TestCase):
    def test_exact_enums_and_frozen_public_records(self):
        self.assertEqual(
            ["RENDERED", "CONFIRM_REQUIRED", "INTERRUPTED", "DELETED", "BLOCKED", "STALE", "UNKNOWN", "FAILED", "EXPIRED", "ALREADY_USED", "UNAUTHORIZED"],
            [item.value for item in PrivateDialogueStatus],
        )
        self.assertEqual(
            ["CALLBACK_NOT_FOUND", "STALE_ACTION", "NO_DIALOGUE", "DIALOGUE_NOT_RUNNING", "JOB_NOT_RUNNING", "ACTIVE_BINDING_UNAVAILABLE", "INTERRUPT_IN_PROGRESS", "INTERRUPT_UNRESOLVED", "DIALOGUE_NOT_READY", "DELETE_NOT_READY", "DELETE_IN_PROGRESS", "DELETE_UNKNOWN", "ACTION_UNAVAILABLE"],
            [item.value for item in PrivateDialogueReason],
        )
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "INVARIANT"], [item.value for item in PrivateDialogueErrorCategory])
        expected = {
            PrivateDialogueOpenRequest: ["user_id", "chat_id"],
            PrivateDialoguePanel: ["section", "text", "rows"],
            PrivateDialogueResult: ["status", "panel", "reason"],
        }
        for record, names in expected.items():
            self.assertTrue(is_dataclass(record))
            self.assertTrue(record.__dataclass_params__.frozen)
            self.assertEqual(names, [field.name for field in fields(record)])

    def test_p41_exact_enums_are_unchanged(self):
        self.assertEqual(["ROOT", "PROFILES", "MODELS", "REASONING"], [item.value for item in PrivatePanelSection])
        self.assertEqual(["RENDERED", "UPDATED", "NO_CHANGE", "BLOCKED", "STALE", "EXPIRED", "ALREADY_USED", "DUPLICATE", "UNAUTHORIZED", "UNSUPPORTED"], [item.value for item in PrivateAdminStatus])
        self.assertEqual(["CALLBACK_NOT_FOUND", "STALE_ACTION", "SETTINGS_MISSING", "PROFILE_NOT_CONFIGURED", "PROFILE_LOCKED", "DIALOGUE_NOT_IDLE", "MODEL_NOT_CONFIGURED", "MODEL_UNAVAILABLE", "REASONING_EFFORT_UNSUPPORTED", "CATALOG_UNAVAILABLE", "ACTION_UNAVAILABLE"], [item.value for item in PrivateAdminReason])

    def test_bounds_and_redaction(self):
        token = "Z" * 32
        with self.assertRaises(PrivateDialogueError):
            PrivateDialogueOpenRequest(0, 7)
        button = PrivateAdminButton("label\n" + "x" * 100, "cc1:" + token)
        panel = PrivateDialoguePanel(
            PrivateDialoguePanelSection.STATUS,
            "bounded status text " * 200,
            ((button,),),
        )
        result = PrivateDialogueResult(PrivateDialogueStatus.RENDERED, panel, None)
        self.assertLessEqual(len(button.label), P4_PRIVATE_BUTTON_LABEL_MAX_CHARS)
        self.assertLessEqual(len(panel.text), P4_PRIVATE_PANEL_TEXT_MAX_CHARS)
        self.assertNotIn(token, repr(result))
        self.assertNotIn(token, repr(result))
        self.assertEqual("INVARIANT", str(PrivateDialogueError("PRIVATE_RAW_EXCEPTION")))
        self.assertNotIn("PRIVATE_RAW_EXCEPTION", repr(PrivateDialogueError("PRIVATE_RAW_EXCEPTION")))

    def test_renderer_is_minimal_and_zero_rows_are_deterministic(self):
        token = "A" * 32
        panel = PrivateDialoguePanel(
            PrivateDialoguePanelSection.STATUS,
            "status",
            ((PrivateAdminButton("Refresh", "cc1:" + token),),),
        )
        rendered = TelegramPrivateDialoguePanelRenderer().render(panel)
        self.assertEqual({"text", "reply_markup"}, set(rendered))
        self.assertEqual({"inline_keyboard"}, set(rendered["reply_markup"]))
        self.assertEqual("cc1:" + token, rendered["reply_markup"]["inline_keyboard"][0][0]["callback_data"])
        self.assertNotIn("parse_mode", rendered)
        empty = TelegramPrivateDialoguePanelRenderer().render(
            PrivateDialoguePanel(PrivateDialoguePanelSection.STATUS, "none", ())
        )
        self.assertEqual([], empty["reply_markup"]["inline_keyboard"])

    def test_callback_request_is_reused_and_not_duplicated(self):
        names = [field.name for field in fields(PrivateCallbackRequest)]
        self.assertEqual(["update_id", "user_id", "chat_id", "callback_query_id", "callback_token"], names)
        self.assertNotIn("PrivateDialogueCallbackRequest", globals())


if __name__ == "__main__":
    unittest.main()
