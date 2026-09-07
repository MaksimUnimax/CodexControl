import inspect
import unittest
from dataclasses import fields, is_dataclass

from codex_control.adapters.telegram import (
    PrivateCommand,
    PrivateInboundKind,
    PrivateInboundUpdate,
    TelegramPrivatePanelRenderer,
    TelegramPrivateUpdateAdapter,
)
from codex_control.application import (
    P4_PRIVATE_BUTTON_LABEL_MAX_CHARS,
    P4_PRIVATE_PANEL_TEXT_MAX_CHARS,
    PrivateAdminButton,
    PrivateAdminError,
    PrivateAdminErrorCategory,
    PrivateAdminPanel,
    PrivateAdminReason,
    PrivateAdminResult,
    PrivateAdminStatus,
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivatePanelSection,
)


def message(user=7, chat=7, chat_type="private", text="/menu", is_bot=False):
    return {
        "update_id": 1,
        "message": {
            "from": {"id": user, "is_bot": is_bot},
            "chat": {"id": chat, "type": chat_type},
            "text": text,
        },
    }


def callback(token="A" * 32, user=7, chat=7, chat_type="private", data=None):
    return {
        "update_id": 2,
        "callback_query": {
            "id": "query-1",
            "from": {"id": user, "is_bot": False},
            "message": {"chat": {"id": chat, "type": chat_type}},
            "data": "cc1:" + token if data is None else data,
        },
    }


class PrivateTelegramUnitTests(unittest.TestCase):
    def setUp(self):
        self.adapter = TelegramPrivateUpdateAdapter(7)

    def test_exact_public_enums_records_and_surfaces(self):
        self.assertEqual(["COMMAND", "CALLBACK", "UNAUTHORIZED", "UNSUPPORTED", "MALFORMED"], [x.value for x in PrivateInboundKind])
        self.assertEqual(["MENU", "SETTINGS"], [x.value for x in PrivateCommand])
        self.assertEqual(["ROOT", "PROFILES", "MODELS", "REASONING"], [x.value for x in PrivatePanelSection])
        self.assertEqual(["RENDERED", "UPDATED", "NO_CHANGE", "BLOCKED", "STALE", "EXPIRED", "ALREADY_USED", "DUPLICATE", "UNAUTHORIZED", "UNSUPPORTED"], [x.value for x in PrivateAdminStatus])
        self.assertEqual(["CALLBACK_NOT_FOUND", "STALE_ACTION", "SETTINGS_MISSING", "PROFILE_NOT_CONFIGURED", "PROFILE_LOCKED", "DIALOGUE_NOT_IDLE", "MODEL_NOT_CONFIGURED", "MODEL_UNAVAILABLE", "REASONING_EFFORT_UNSUPPORTED", "CATALOG_UNAVAILABLE", "ACTION_UNAVAILABLE"], [x.value for x in PrivateAdminReason])
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "INVARIANT"], [x.value for x in PrivateAdminErrorCategory])
        expected = {
            PrivateInboundUpdate: ["kind", "update_id", "user_id", "chat_id", "command", "callback_query_id", "callback_token"],
            PrivateCommandRequest: ["update_id", "user_id", "chat_id", "command"],
            PrivateCallbackRequest: ["update_id", "user_id", "chat_id", "callback_query_id", "callback_token"],
            PrivateAdminButton: ["label", "callback_data"],
            PrivateAdminPanel: ["section", "text", "rows"],
            PrivateAdminResult: ["status", "panel", "reason"],
        }
        for record, names in expected.items():
            self.assertTrue(is_dataclass(record))
            self.assertTrue(record.__dataclass_params__.frozen)
            self.assertEqual(names, [field.name for field in fields(record)])

    def test_exact_commands_and_unsupported_arguments(self):
        for text, command in (("/start", PrivateCommand.MENU), ("/menu", PrivateCommand.MENU), ("/settings", PrivateCommand.SETTINGS)):
            normalized = self.adapter.normalize(message(text=text))
            self.assertEqual((PrivateInboundKind.COMMAND, command), (normalized.kind, normalized.command))
        for text in ("/start x", "/menu ", "/settings@bot", " /menu", "/menu\n", "/delete", "ordinary"):
            normalized = self.adapter.normalize(message(text=text))
            self.assertEqual(PrivateInboundKind.UNSUPPORTED, normalized.kind)
            self.assertNotIn(text, repr(normalized))

    def test_authorization_matrix(self):
        cases = (
            message(user=8), message(chat=8), message(chat_type="group"), message(is_bot=True),
        )
        for raw in cases:
            normalized = self.adapter.normalize(raw)
            self.assertEqual(PrivateInboundKind.UNAUTHORIZED, normalized.kind)
        self.assertEqual(PrivateInboundKind.MALFORMED, self.adapter.normalize(None).kind)
        self.assertEqual(PrivateInboundKind.MALFORMED, self.adapter.normalize({"update_id": True}).kind)
        self.assertEqual(PrivateInboundKind.MALFORMED, self.adapter.normalize({"update_id": 1, "message": []}).kind)
        self.assertEqual(PrivateInboundKind.MALFORMED, self.adapter.normalize({"update_id": 1, "message": {"from": {}, "chat": {}}}).kind)

    def test_callback_authorization_grammar_and_inline_rejection(self):
        normalized = self.adapter.normalize(callback())
        self.assertEqual(PrivateInboundKind.CALLBACK, normalized.kind)
        self.assertEqual("A" * 32, normalized.callback_token)
        self.assertEqual(36, len("cc1:" + normalized.callback_token))
        for raw in (callback(user=8), callback(chat=8), callback(chat_type="group"), callback(data="OPEN_ROOT"), callback(data="cc1:" + "A" * 31)):
            self.assertIn(self.adapter.normalize(raw).kind, (PrivateInboundKind.UNAUTHORIZED, PrivateInboundKind.MALFORMED))
        inline = {"update_id": 2, "callback_query": {"id": "q", "from": {"id": 7, "is_bot": False}, "inline_message_id": "i", "data": "cc1:" + "A" * 32}}
        self.assertEqual(PrivateInboundKind.MALFORMED, self.adapter.normalize(inline).kind)

    def test_raw_text_and_token_are_absent_or_redacted(self):
        text = "PRIVATE_RAW_TEXT_SENTINEL"
        normalized = self.adapter.normalize(message(text=text))
        self.assertNotIn(text, repr(normalized))
        normalized = self.adapter.normalize(callback(token="B" * 32))
        self.assertNotIn("B" * 32, repr(normalized))
        self.assertIn("REDACTED", repr(normalized))

    def test_request_error_button_panel_repr_redaction_and_bounds(self):
        token = "C" * 32
        self.assertNotIn(token, repr(PrivateCallbackRequest(1, 7, 7, "q", token)))
        self.assertNotIn("PRIVATE", repr(PrivateAdminError("PRIVATE")))
        button = PrivateAdminButton("line\n" + "x" * 100, "cc1:" + token)
        panel = PrivateAdminPanel(PrivatePanelSection.ROOT, "a\n" * 4000, ((button,),))
        self.assertLessEqual(len(button.label), P4_PRIVATE_BUTTON_LABEL_MAX_CHARS)
        self.assertLessEqual(len(panel.text), P4_PRIVATE_PANEL_TEXT_MAX_CHARS)
        self.assertNotIn(token, repr(button) + repr(panel))

    def test_renderer_is_exact_minimal_plain_structure(self):
        panel = PrivateAdminPanel(PrivatePanelSection.ROOT, "hello", ((PrivateAdminButton("Go", "cc1:" + "D" * 32),),))
        rendered = TelegramPrivatePanelRenderer().render(panel)
        self.assertEqual({"text", "reply_markup"}, set(rendered))
        self.assertEqual({"inline_keyboard"}, set(rendered["reply_markup"]))
        self.assertEqual("cc1:" + "D" * 32, rendered["reply_markup"]["inline_keyboard"][0][0]["callback_data"])
        self.assertNotIn("parse_mode", repr(rendered))

    def test_invalid_operator_and_token_factory_shape_are_fail_closed_at_surface(self):
        for value in (0, True, -1, 1.0):
            with self.assertRaises(ValueError):
                TelegramPrivateUpdateAdapter(value)
        with self.assertRaises(ValueError):
            PrivateAdminButton("x", "cc1:short")


if __name__ == "__main__":
    unittest.main()
