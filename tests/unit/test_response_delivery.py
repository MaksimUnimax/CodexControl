from __future__ import annotations

import inspect
import math
import unittest
from dataclasses import fields

from codex_control.adapters.codex.turn_lifecycle import (
    MAX_AGENT_MESSAGES_PER_TURN,
    MAX_TOTAL_AGENT_MESSAGE_CHARS,
)
from codex_control.application import (
    P61_MAX_TEXT_LIMIT,
    P61_MIN_TEXT_LIMIT,
    TelegramDeliveryEffectResult,
    TelegramDeliveryEffectStatus,
    TelegramDeliveryErrorClass,
    TelegramDeliveryPort,
    TurnDeliveryError,
    TurnDeliveryErrorCategory,
    TurnDeliveryRequest,
    TurnDeliveryResult,
    TurnDeliveryStatus,
    segment_telegram_text,
)


class ResponseDeliveryUnitTests(unittest.TestCase):
    def test_constants_and_exact_enum_values(self):
        self.assertEqual((512, 4096), (P61_MIN_TEXT_LIMIT, P61_MAX_TEXT_LIMIT))
        self.assertEqual(
            [member.value for member in TelegramDeliveryEffectStatus],
            ["CONFIRMED", "FAILED", "UNKNOWN"],
        )
        self.assertEqual(
            [member.value for member in TelegramDeliveryErrorClass],
            [
                "TELEGRAM_REQUEST_REJECTED",
                "TELEGRAM_NETWORK_AMBIGUOUS",
                "TELEGRAM_LOCAL_DISPATCH_FAILED",
                "TELEGRAM_RESULT_INVALID",
                "TELEGRAM_RECOVERY_AMBIGUOUS",
            ],
        )

    def test_public_fields_are_exact_and_frozen(self):
        self.assertEqual(
            [field.name for field in fields(TelegramDeliveryEffectResult)],
            ["status", "message_id", "error_class"],
        )
        self.assertEqual(
            [field.name for field in fields(TurnDeliveryRequest)],
            ["job_id", "status_message_id"],
        )
        self.assertEqual(
            [field.name for field in fields(TurnDeliveryResult)],
            ["status", "job", "segments", "reason"],
        )
        for record in (TelegramDeliveryEffectResult, TurnDeliveryRequest, TurnDeliveryResult):
            self.assertTrue(record.__dataclass_params__.frozen)

    def test_repr_redacts_external_and_durable_identifiers(self):
        effect = TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.CONFIRMED, 987654321, None
        )
        request = TurnDeliveryRequest("job-secret", 987654321)
        result = TurnDeliveryResult.__new__(TurnDeliveryResult)
        object.__setattr__(result, "status", TurnDeliveryStatus.DELIVERED)
        object.__setattr__(result, "job", "job-secret")
        object.__setattr__(result, "segments", ("payload-secret",))
        object.__setattr__(result, "reason", None)
        for rendered in (repr(effect), repr(request), repr(result)):
            self.assertNotIn("987654321", rendered)
            self.assertNotIn("job-secret", rendered)
            self.assertNotIn("payload-secret", rendered)

    def test_port_is_exact_async_protocol_surface(self):
        public = {
            name for name, value in vars(TelegramDeliveryPort).items()
            if not name.startswith("_") and callable(value)
        }
        self.assertEqual({"create_message", "edit_message"}, public)
        self.assertTrue(inspect.iscoroutinefunction(TelegramDeliveryPort.create_message))
        self.assertTrue(inspect.iscoroutinefunction(TelegramDeliveryPort.edit_message))

    def test_segment_short_exact_and_reconstructing(self):
        for text in ("short", "x" * 512, "🙂" * 512, "a\n\n b "):
            chunks = segment_telegram_text(text, 512)
            self.assertTrue(chunks)
            self.assertEqual(text, "".join(chunks))
            self.assertTrue(all(chunk and len(chunk) <= 512 for chunk in chunks))

    def test_segment_priority_is_paragraph_then_line_then_space_then_hard(self):
        text = "a" * 490 + "\n" + "b" * 5 + "\n\n" + "c" * 20
        chunks = segment_telegram_text(text, 512)
        self.assertEqual("a" * 490 + "\n" + "b" * 5 + "\n\n", chunks[0])

        text = "a" * 500 + "\n" + "b" * 30 + "\n\n" + "c"
        chunks = segment_telegram_text(text, 512)
        self.assertEqual("a" * 500 + "\n", chunks[0])

        text = "a" * 500 + " " + "b" * 30
        chunks = segment_telegram_text(text, 512)
        self.assertEqual("a" * 500 + " ", chunks[0])

        text = "🙂" * 513
        chunks = segment_telegram_text(text, 512)
        self.assertEqual(("🙂" * 512, "🙂"), chunks)

    def test_segment_does_not_normalize_whitespace_or_unicode(self):
        text = "  a\n\n\n b \n"
        self.assertEqual(text, "".join(segment_telegram_text(text, 512)))
        self.assertEqual("é", "".join(segment_telegram_text("é", 512)))

    def test_segment_limits_are_exact_and_booleans_invalid(self):
        for limit in (512, 4096):
            self.assertEqual("x", segment_telegram_text("x", limit)[0])
        for limit in (511, 4097, True, False, 512.0):
            with self.assertRaises(TurnDeliveryError) as raised:
                segment_telegram_text("x", limit)
            self.assertEqual(TurnDeliveryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

    def test_segment_rejects_empty_nul_and_surrogate_text(self):
        for text in ("", "a\x00b", "\ud800"):
            with self.assertRaises(TurnDeliveryError):
                segment_telegram_text(text, 512)

    def test_p3_worst_case_is_within_accepted_delivery_segment_bound(self):
        projected_chars = MAX_TOTAL_AGENT_MESSAGE_CHARS + (MAX_AGENT_MESSAGES_PER_TURN - 1) * 2
        self.assertLessEqual(math.ceil(projected_chars / P61_MIN_TEXT_LIMIT), 4096)

    def test_request_validation_is_bounded(self):
        TurnDeliveryRequest("j")
        for value in ("", "a\x00b", "x" * 129, 1, True):
            with self.assertRaises(TurnDeliveryError):
                TurnDeliveryRequest(value)
        for value in (0, -1, True, 2**63, 1.0):
            with self.assertRaises(TurnDeliveryError):
                TurnDeliveryRequest("j", value)

    def test_effect_result_shapes_can_be_constructed_but_service_contract_is_explicit(self):
        confirmed = TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.CONFIRMED, 1, None
        )
        rejected = TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.FAILED,
            None,
            TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED,
        )
        unknown = TelegramDeliveryEffectResult(
            TelegramDeliveryEffectStatus.UNKNOWN,
            None,
            TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS,
        )
        self.assertEqual(1, confirmed.message_id)
        self.assertIsNone(rejected.message_id)
        self.assertIsNone(unknown.message_id)
