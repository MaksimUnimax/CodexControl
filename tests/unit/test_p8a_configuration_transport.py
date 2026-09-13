import asyncio
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from codex_control.adapters.telegram.bot_api import HttpResponse, TelegramBotApiTransport
from codex_control.config import ConfigurationError, parse_production_server_configuration
from codex_control.secrets import SecretsError, parse_secrets


class P8AConfigTransportTests(unittest.TestCase):
    def _data(self):
        return {
            "server": {"server_id": "server-80", "display_name": "SERVER-80", "operator_user_id": 7, "control_chat_id": -100, "fleet_version": "v1"},
            "fleet": {"servers": [{"server_id": "server-80", "display_name": "SERVER-80"}]},
            "runtime": {"state_root": "/tmp/p8a-state", "working_directory": "/tmp", "repository_root": "/tmp/p8a-repo", "telegram_text_limit": 3800},
            "profiles": [{"profile_id": "p1", "display_name": "P1", "codex_home": "/tmp/p8a-home", "isolated_state_root": "/tmp/p8a-isolated"}],
        }

    def test_complete_schema_and_required_field_failures(self):
        parsed = parse_production_server_configuration(self._data())
        self.assertEqual(parsed.fleet.members[0].server_id, "server-80")
        for field in ("operator_user_id", "control_chat_id"):
            data = self._data()
            del data["server"][field]
            with self.assertRaises(ConfigurationError):
                parse_production_server_configuration(data)
        data = self._data()
        del data["fleet"]
        with self.assertRaises(ConfigurationError):
            parse_production_server_configuration(data)

    def test_duplicates_overlap_and_unsafe_paths_fail(self):
        data = self._data()
        data["fleet"]["servers"].append({"server_id": "server-80", "display_name": "OTHER"})
        with self.assertRaises(ConfigurationError):
            parse_production_server_configuration(data)
        data = self._data()
        data["profiles"].append({"profile_id": "p1", "display_name": "P2", "codex_home": "/tmp/p8a-home-2", "isolated_state_root": "/tmp/p8a-isolated-2"})
        with self.assertRaises(ConfigurationError):
            parse_production_server_configuration(data)
        data = self._data()
        data["runtime"]["telegram_text_limit"] = 1
        with self.assertRaises(ConfigurationError):
            parse_production_server_configuration(data)
        data = self._data()
        data["runtime"]["state_root"] = "relative"
        with self.assertRaises(ConfigurationError):
            parse_production_server_configuration(data)

    def test_secrets_are_bounded_and_redacted(self):
        secret = parse_secrets("# comment\nTELEGRAM_BOT_TOKEN=offline-token\n")
        self.assertNotIn("offline-token", repr(secret))
        for value in ("TELEGRAM_BOT_TOKEN=\n", "TELEGRAM_BOT_TOKEN=x\nTELEGRAM_BOT_TOKEN=y\n", "TELEGRAM_BOT_TOKEN=$(id)\n", "BAD LINE\n"):
            with self.assertRaises(SecretsError):
                parse_secrets(value)


class _FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def request(self, method, payload, *, timeout):
        self.calls.append((method, dict(payload), timeout))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class P8ATransportTests(unittest.IsolatedAsyncioTestCase):
    def response(self, result, ok=True):
        return HttpResponse(200, json.dumps({"ok": ok, "result": result} if ok else {"ok": False, "description": "safe"}).encode())

    async def test_poll_offset_and_order(self):
        fake = _FakeHttp([self.response([{"update_id": 4}, {"update_id": 8}]), self.response([])])
        transport = TelegramBotApiTransport("123:offline", http=fake)
        self.assertEqual([4, 8], [u["update_id"] for u in await transport.get_updates()])
        self.assertEqual(9, transport.offset)
        await transport.get_updates()
        self.assertEqual(9, fake.calls[-1][1]["offset"])

    async def test_send_edit_callback_projection_and_no_retry(self):
        fake = _FakeHttp([self.response({"message_id": 12}), self.response(True), self.response({})])
        transport = TelegramBotApiTransport("123:offline", http=fake)
        created = await transport.create_message(chat_id=-100, text="safe")
        edited = await transport.edit_message(chat_id=-100, message_id=12, text="safe-2")
        await transport.answer_callback_query(callback_query_id="q1")
        self.assertEqual(12, created.message_id)
        self.assertEqual(12, edited.message_id)
        self.assertEqual(["sendMessage", "editMessageText", "answerCallbackQuery"], [c[0] for c in fake.calls])
        self.assertNotIn("123:offline", repr(transport))

    async def test_bad_response_and_ambiguous_failure_are_safe(self):
        fake = _FakeHttp([HttpResponse(200, b"not-json")])
        transport = TelegramBotApiTransport("123:offline", http=fake)
        with self.assertRaises(Exception) as error:
            await transport.get_updates()
        self.assertNotIn("123:offline", str(error.exception))
        fake = _FakeHttp([TimeoutError()])
        transport = TelegramBotApiTransport("123:offline", http=fake)
        result = await transport.create_message(chat_id=1, text="safe")
        self.assertEqual("UNKNOWN", result.status.value)
        self.assertEqual(1, len(fake.calls))
