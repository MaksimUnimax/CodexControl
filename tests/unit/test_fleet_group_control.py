import unittest
from dataclasses import FrozenInstanceError, fields

from codex_control.adapters.telegram import TelegramFleetKeyboardRenderer, TelegramGroupUpdateAdapter
from codex_control.application import (
    FleetControlError,
    FleetControlErrorCategory,
    FleetControlResult,
    FleetControlStatus,
    FleetManifest,
    FleetMember,
    FleetModeSnapshot,
    GroupControlKind,
    GroupInboundKind,
    GroupInboundUpdate,
    P5_ACTIVATION_PREFIX,
    P5_ALL_SLEEP_LABEL,
    P5_STATUS_LABEL,
)
from codex_control.domain import ControllerMode


class FleetGroupContractTests(unittest.TestCase):
    def manifest(self, count=3):
        return FleetManifest(
            "fleet-v1",
            tuple(FleetMember(f"SERVER-{n}", f"Сервер {n}") for n in range(1, count + 1)),
        )

    def raw(self, text, *, user=7, chat=-100, chat_type="supergroup", bot=False, sender_chat=None):
        message = {
            "message_id": 10,
            "from": {"id": user, "is_bot": bot},
            "chat": {"id": chat, "type": chat_type},
            "text": text,
        }
        if sender_chat is not None:
            message["sender_chat"] = sender_chat
        return {"update_id": 9, "message": message}

    def test_exact_constants_enums_and_frozen_records(self):
        self.assertEqual("🖥 ", P5_ACTIVATION_PREFIX)
        self.assertEqual("💤 ВСЕ СПАТЬ", P5_ALL_SLEEP_LABEL)
        self.assertEqual("📊 СТАТУС", P5_STATUS_LABEL)
        self.assertEqual(
            ["CONTROL", "TEXT", "UNAUTHORIZED", "UNSUPPORTED", "MALFORMED"],
            [item.value for item in GroupInboundKind],
        )
        self.assertEqual(["ACTIVATE", "ALL_SLEEP", "STATUS"], [item.value for item in GroupControlKind])
        self.assertEqual(
            ["APPLIED", "STALE", "DUPLICATE", "STATUS", "TEXT", "UNAUTHORIZED", "UNSUPPORTED", "MALFORMED"],
            [item.value for item in FleetControlStatus],
        )
        self.assertEqual(
            ["server_id", "display_name"], [field.name for field in fields(FleetMember)]
        )
        self.assertEqual(
            ["fleet_version", "members"], [field.name for field in fields(FleetManifest)]
        )
        update = GroupInboundUpdate(GroupInboundKind.TEXT, 1, 2, 7, -100, None, None, "fake fixture")
        self.assertIn("text='[REDACTED]'", repr(update))
        self.assertNotIn("fake fixture", repr(update))
        with self.assertRaises(FrozenInstanceError):
            update.text = "changed"

    def test_manifest_validation_bounds_uniqueness_and_normalization(self):
        with self.assertRaises(FleetControlError):
            FleetManifest("fleet", ())
        with self.assertRaises(FleetControlError):
            FleetManifest("fleet", tuple(FleetMember(str(i), str(i)) for i in range(33)))
        with self.assertRaises(FleetControlError):
            FleetManifest("fleet", (FleetMember("a", "same"), FleetMember("b", "same")))
        with self.assertRaises(FleetControlError):
            FleetManifest("fleet", (FleetMember("a", "a"), FleetMember("a", "b")))
        for server_id in ("", "bad id", "bad/", "x\x00"):
            with self.subTest(server_id=server_id), self.assertRaises(FleetControlError):
                FleetMember(server_id, "Display")
        for display_name in ("", " leading", "trailing ", "two  spaces", "line\nname", "bad\x00"):
            with self.subTest(display_name=display_name), self.assertRaises(FleetControlError):
                FleetMember("server", display_name)
        with self.assertRaises(FleetControlError):
            FleetManifest("bad version", (FleetMember("server", "Display"),))
        with self.assertRaises(FleetControlError):
            FleetMember("server", "x" * 65)
        with self.assertRaises(FleetControlError):
            FleetManifest("fleet", (object(),))
        self.assertEqual("Сервер 80", FleetMember("server", "Сервер 80").display_name)

    def test_keyboard_is_persistent_ordered_and_server_independent(self):
        renderer = TelegramFleetKeyboardRenderer()
        for count in (1, 2, 3, 32):
            with self.subTest(count=count):
                value = renderer.render(self.manifest(count))
                self.assertEqual({"keyboard", "resize_keyboard", "is_persistent"}, set(value))
                self.assertTrue(value["resize_keyboard"])
                self.assertTrue(value["is_persistent"])
                self.assertEqual(
                    [[{"text": P5_ACTIVATION_PREFIX + f"Сервер {n}"} for n in row]
                     for row in [range(i, min(i + 2, count + 1)) for i in range(1, count + 1, 2)]],
                    value["keyboard"][:-1],
                )
                self.assertEqual(
                    [{"text": P5_ALL_SLEEP_LABEL}, {"text": P5_STATUS_LABEL}],
                    value["keyboard"][-1],
                )
                self.assertTrue(all(set(button) == {"text"} for row in value["keyboard"] for button in row))
        self.assertEqual(renderer.render(self.manifest(3)), renderer.render(self.manifest(3)))
        with self.assertRaises(ValueError):
            renderer.render(object())

    def test_authentication_matrix_and_update_surface(self):
        adapter = TelegramGroupUpdateAdapter(self.manifest(1), 7, -100)
        self.assertIs(GroupInboundKind.TEXT, adapter.normalize(self.raw("hello")).kind)
        cases = (
            {"user": 8}, {"bot": True}, {"chat": -101}, {"chat_type": "group"}, {"sender_chat": {"id": 8}},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertIs(GroupInboundKind.UNAUTHORIZED, adapter.normalize(self.raw("hello", **changes)).kind)
        malformed = (
            {}, {"update_id": -1}, {"update_id": 1, "callback_query": {}},
            {"update_id": 1, "callback_query": {}, "message": {}},
            {"update_id": 1, "message": {"message_id": True}},
        )
        for value in malformed:
            with self.subTest(value=value):
                self.assertIs(GroupInboundKind.MALFORMED, adapter.normalize(value).kind)
        nontext = self.raw("unused")
        del nontext["message"]["text"]
        self.assertIs(GroupInboundKind.UNSUPPORTED, adapter.normalize(nontext).kind)

    def test_authentication_precedes_text_for_trap_messages(self):
        class TrapMessage(dict):
            def get(self, key, default=None):
                if key == "text":
                    raise AssertionError("text accessed before auth")
                return super().get(key, default)

        adapter = TelegramGroupUpdateAdapter(self.manifest(1), 7, -100)
        for principal in (
            {"id": 8, "is_bot": False},
            {"id": 7, "is_bot": True},
        ):
            message = TrapMessage(message_id=10, **{"from": principal, "chat": {"id": -100, "type": "supergroup"}})
            self.assertIs(
                GroupInboundKind.UNAUTHORIZED,
                adapter.normalize({"update_id": 9, "message": message}).kind,
            )

    def test_classification_is_exact_and_control_looking_never_text(self):
        adapter = TelegramGroupUpdateAdapter(self.manifest(2), 7, -100)
        expected = {
            "🖥 Сервер 1": (GroupInboundKind.CONTROL, GroupControlKind.ACTIVATE, "SERVER-1"),
            "🖥 Сервер 2": (GroupInboundKind.CONTROL, GroupControlKind.ACTIVATE, "SERVER-2"),
            "🖥 SOMETHING": (GroupInboundKind.CONTROL, GroupControlKind.ACTIVATE, None),
            P5_ALL_SLEEP_LABEL: (GroupInboundKind.CONTROL, GroupControlKind.ALL_SLEEP, None),
            P5_STATUS_LABEL: (GroupInboundKind.CONTROL, GroupControlKind.STATUS, None),
        }
        for text, result in expected.items():
            with self.subTest(text=text):
                value = adapter.normalize(self.raw(text))
                self.assertEqual(result, (value.kind, value.control, value.target_server_id))
        for text in (" 🖥 Сервер 1", "🖥SERVER-1", "💤 ВСЕ СПАТЬ ", "📊 СТАТУС extra", "/start", "/status", "  /whatever"):
            with self.subTest(text=text):
                self.assertIsNot(GroupInboundKind.TEXT, adapter.normalize(self.raw(text)).kind)
        self.assertIs(GroupInboundKind.UNSUPPORTED, adapter.normalize(self.raw("")).kind)
        self.assertIs(GroupInboundKind.MALFORMED, adapter.normalize(self.raw("bad\x00text")).kind)
        self.assertIs(GroupInboundKind.UNSUPPORTED, adapter.normalize(self.raw("x" * 4097)).kind)

    def test_result_and_error_contracts_are_content_free(self):
        snapshot = FleetModeSnapshot("SERVER-1", ControllerMode.SLEEP, 1, 0, "fleet-v1")
        result = FleetControlResult(FleetControlStatus.STATUS, snapshot)
        self.assertEqual(snapshot, result.snapshot)
        for status in (FleetControlStatus.UNAUTHORIZED, FleetControlStatus.UNSUPPORTED, FleetControlStatus.MALFORMED):
            self.assertIsNone(FleetControlResult(status, None).snapshot)
        with self.assertRaises(FleetControlError):
            FleetControlResult(FleetControlStatus.STATUS, None)
        error = FleetControlError(FleetControlErrorCategory.INVARIANT)
        self.assertEqual("INVARIANT", str(error))
        self.assertEqual("FleetControlError('INVARIANT')", repr(error))
        self.assertNotIn("fake", repr(error))


if __name__ == "__main__":
    unittest.main()
