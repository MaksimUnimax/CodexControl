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
from codex_control.storage import (
    DeliveryOperation,
    DeliverySegmentRecord,
    DeliverySegmentState,
    TurnJobRecord,
    TurnJobState,
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
        from codex_control.application import TurnDeliveryReason
        self.assertEqual(
            [member.value for member in TurnDeliveryStatus],
            ["DELIVERED", "ALREADY_DELIVERED", "DELIVERY_UNKNOWN", "FAILED", "BLOCKED"],
        )
        self.assertEqual(
            [member.value for member in TurnDeliveryReason],
            ["JOB_NOT_FOUND", "JOB_NOT_DELIVERABLE"],
        )
        self.assertEqual(
            [member.value for member in TurnDeliveryErrorCategory],
            ["INVALID_ARGUMENT", "STORAGE", "INVARIANT"],
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
        self.assertEqual(2_000_510, projected_chars)
        self.assertEqual(3908, math.ceil(projected_chars / P61_MIN_TEXT_LIMIT))
        self.assertLessEqual(math.ceil(projected_chars / P61_MIN_TEXT_LIMIT), 4096)

    def test_pathological_preferred_segmentation_uses_bounded_hard_fallback(self):
        limit = 512
        text = ("\n\n" + ("a" * 512)) * 2050
        self.assertEqual(1_053_700, len(text))

        remaining = text
        preferred_count = 0
        while len(remaining) > limit:
            paragraph = remaining.rfind("\n\n", 0, limit - 1)
            if paragraph >= 0:
                cut = paragraph + 2
            else:
                line = remaining.rfind("\n", 0, limit)
                if line >= 0:
                    cut = line + 1
                else:
                    space = remaining.rfind(" ", 0, limit)
                    cut = space + 1 if space >= 0 else limit
            preferred_count += 1
            remaining = remaining[cut:]
        preferred_count += 1
        self.assertEqual(4100, preferred_count)
        self.assertGreater(preferred_count, 4096)

        chunks = segment_telegram_text(text, limit)
        self.assertLessEqual(len(chunks), 4096)
        self.assertEqual(512, len(chunks[0]))
        self.assertEqual(text[:512], chunks[0])
        self.assertEqual(text, "".join(chunks))
        self.assertEqual(
            tuple(text[offset:offset + limit] for offset in range(0, len(text), limit)),
            chunks,
        )
        self.assertTrue(all(chunk and len(chunk) <= limit for chunk in chunks))

        with self.assertRaises(TurnDeliveryError) as raised:
            segment_telegram_text("a" * (limit * 4096 + 1), limit)
        self.assertEqual(TurnDeliveryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

    def test_request_validation_is_bounded(self):
        TurnDeliveryRequest("j")
        for value in ("", "a\x00b", "x" * 129, 1, True):
            with self.assertRaises(TurnDeliveryError):
                TurnDeliveryRequest(value)
        for value in (0, -1, True, 2**63, 1.0):
            with self.assertRaises(TurnDeliveryError):
                TurnDeliveryRequest("j", value)

    def test_effect_result_constructor_accepts_only_canonical_shapes(self):
        canonical = (
            TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, 1, None),
            TelegramDeliveryEffectResult(
                TelegramDeliveryEffectStatus.FAILED,
                None,
                TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED,
            ),
            TelegramDeliveryEffectResult(
                TelegramDeliveryEffectStatus.UNKNOWN,
                None,
                TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS,
            ),
        )
        self.assertEqual(1, canonical[0].message_id)
        self.assertIsNone(canonical[1].message_id)
        self.assertIsNone(canonical[2].message_id)

        invalid = (
            ("CONFIRMED", 1, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, None, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, 0, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, -1, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, True, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, 2**63, None),
            (TelegramDeliveryEffectStatus.CONFIRMED, 1, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED),
            (TelegramDeliveryEffectStatus.FAILED, 1, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED),
            (TelegramDeliveryEffectStatus.FAILED, None, None),
            (TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryEffectStatus.UNKNOWN),
            (TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_LOCAL_DISPATCH_FAILED),
            (TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID),
            (TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_RECOVERY_AMBIGUOUS),
            (TelegramDeliveryEffectStatus.UNKNOWN, 1, TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS),
            (TelegramDeliveryEffectStatus.UNKNOWN, None, None),
            (TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED),
            (TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_LOCAL_DISPATCH_FAILED),
            (TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID),
            (TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_RECOVERY_AMBIGUOUS),
        )
        for shape in invalid:
            with self.subTest(shape=repr(shape)):
                with self.assertRaises(TurnDeliveryError) as raised:
                    TelegramDeliveryEffectResult(*shape)
                self.assertEqual(TurnDeliveryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

    def test_turn_delivery_result_constructor_enforces_public_relations(self):
        from codex_control.application import TurnDeliveryReason

        def job(state, error_class=None):
            return TurnJobRecord(
                "job-result", 1, -100, 2, "dialogue-result", "server-80", "profile-1",
                "thread-1", None, None, "a" * 64, "turn-1", state, 1, 1, 1, error_class,
            )

        def segment(state, *, payload_id=None):
            return DeliverySegmentRecord(
                "job-result", 1, DeliveryOperation.CREATE, None, payload_id, "b" * 64,
                state, 1, 99 if state is DeliverySegmentState.CONFIRMED else None, 1, 1,
            )

        delivered_job = job(TurnJobState.DELIVERED)
        delivered_segments = (segment(DeliverySegmentState.CONFIRMED),)
        unknown_job = job(TurnJobState.DELIVERY_UNKNOWN, "TELEGRAM_NETWORK_AMBIGUOUS")
        unknown_segments = (segment(DeliverySegmentState.UNKNOWN, payload_id="display"),)
        failed_job = job(TurnJobState.FAILED, "TELEGRAM_REQUEST_REJECTED")
        failed_segments = (segment(DeliverySegmentState.FAILED, payload_id="display"),)

        TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, delivered_job, delivered_segments, None)
        TurnDeliveryResult(TurnDeliveryStatus.ALREADY_DELIVERED, delivered_job, delivered_segments, None)
        TurnDeliveryResult(TurnDeliveryStatus.DELIVERY_UNKNOWN, unknown_job, unknown_segments, None)
        TurnDeliveryResult(TurnDeliveryStatus.FAILED, failed_job, failed_segments, None)
        TurnDeliveryResult(TurnDeliveryStatus.BLOCKED, None, (), TurnDeliveryReason.JOB_NOT_FOUND)
        TurnDeliveryResult(
            TurnDeliveryStatus.BLOCKED, failed_job, (), TurnDeliveryReason.JOB_NOT_DELIVERABLE
        )

        invalid = (
            ("DELIVERED", delivered_job, delivered_segments, None),
            (TurnDeliveryStatus.DELIVERED, None, (), None),
            (TurnDeliveryStatus.DELIVERED, delivered_job, (), None),
            (TurnDeliveryStatus.DELIVERED, failed_job, failed_segments, None),
            (TurnDeliveryStatus.DELIVERY_UNKNOWN, delivered_job, delivered_segments, None),
            (TurnDeliveryStatus.FAILED, failed_job, (), None),
            (TurnDeliveryStatus.BLOCKED, delivered_job, (), TurnDeliveryReason.JOB_NOT_FOUND),
            (TurnDeliveryStatus.BLOCKED, None, (), TurnDeliveryReason.JOB_NOT_DELIVERABLE),
            (TurnDeliveryStatus.BLOCKED, None, (), None),
            (TurnDeliveryStatus.BLOCKED, None, delivered_segments, TurnDeliveryReason.JOB_NOT_FOUND),
            (TurnDeliveryStatus.DELIVERED, delivered_job, delivered_segments, TurnDeliveryReason.JOB_NOT_FOUND),
            (TurnDeliveryStatus.DELIVERED, delivered_job, [], None),
            (TurnDeliveryStatus.DELIVERED, delivered_job, delivered_segments, "JOB_NOT_FOUND"),
        )
        for shape in invalid:
            with self.subTest(shape=repr(shape)):
                with self.assertRaises(TurnDeliveryError) as raised:
                    TurnDeliveryResult(*shape)
                self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)

    def test_turn_delivery_result_accepts_canonical_terminal_segment_records(self):
        def job(state, error_class=None):
            return TurnJobRecord(
                "job-canonical", 1, -100, 2, "dialogue-canonical", "server-80", "profile-1",
                "thread-1", None, None, "a" * 64, "turn-1", state, 1, 1, 1, error_class,
            )

        def segment(state, *, operation=DeliveryOperation.CREATE, target=None, payload_id=None,
                    confirmed_message_id=None):
            return DeliverySegmentRecord(
                "job-canonical", 1, operation, target, payload_id, "b" * 64,
                state, 1, confirmed_message_id, 1, 1,
            )

        TurnDeliveryResult(
            TurnDeliveryStatus.DELIVERED,
            job(TurnJobState.DELIVERED),
            (segment(DeliverySegmentState.CONFIRMED, confirmed_message_id=99),),
            None,
        )
        TurnDeliveryResult(
            TurnDeliveryStatus.DELIVERED,
            job(TurnJobState.DELIVERED),
            (segment(
                DeliverySegmentState.CONFIRMED,
                operation=DeliveryOperation.EDIT,
                target=77,
                confirmed_message_id=77,
            ),),
            None,
        )
        TurnDeliveryResult(
            TurnDeliveryStatus.DELIVERY_UNKNOWN,
            job(TurnJobState.DELIVERY_UNKNOWN, "TELEGRAM_NETWORK_AMBIGUOUS"),
            (segment(DeliverySegmentState.UNKNOWN, payload_id="display"),),
            None,
        )
        TurnDeliveryResult(
            TurnDeliveryStatus.FAILED,
            job(TurnJobState.FAILED, "TELEGRAM_REQUEST_REJECTED"),
            (segment(DeliverySegmentState.FAILED),),
            None,
        )

    def test_turn_delivery_result_accepts_terminal_payload_retention(self):
        def job(state):
            return TurnJobRecord(
                "job-retained", 1, -100, 2, "dialogue-retained", "server-80", "profile-1",
                "thread-1", None, None, "a" * 64, "turn-1", state, 1, 1, 1,
                "TELEGRAM_REQUEST_REJECTED" if state is TurnJobState.FAILED else None,
            )

        def segment(state):
            return DeliverySegmentRecord(
                "job-retained", 1, DeliveryOperation.CREATE, None, None, "b" * 64,
                state, 1, 99 if state is DeliverySegmentState.CONFIRMED else None, 1, 1,
            )

        TurnDeliveryResult(
            TurnDeliveryStatus.DELIVERED,
            job(TurnJobState.DELIVERED),
            (segment(DeliverySegmentState.CONFIRMED),),
            None,
        )
        TurnDeliveryResult(
            TurnDeliveryStatus.FAILED,
            job(TurnJobState.FAILED),
            (segment(DeliverySegmentState.FAILED),),
            None,
        )

    def test_turn_delivery_result_rejects_terminal_attempt_and_confirmation_forgery(self):
        def job(state, error_class=None):
            return TurnJobRecord(
                "job-forged", 1, -100, 2, "dialogue-forged", "server-80", "profile-1",
                "thread-1", None, None, "a" * 64, "turn-1", state, 1, 1, 1, error_class,
            )

        def result(status, job_state, segment_state, attempt_count, confirmed_message_id):
            error_class = {
                TurnJobState.DELIVERY_UNKNOWN: "TELEGRAM_NETWORK_AMBIGUOUS",
                TurnJobState.FAILED: "TELEGRAM_REQUEST_REJECTED",
            }.get(job_state)
            record = DeliverySegmentRecord(
                "job-forged", 1, DeliveryOperation.CREATE, None, "display", "b" * 64,
                segment_state, attempt_count, confirmed_message_id, 1, 1,
            )
            return TurnDeliveryResult(
                status, job(job_state, error_class), (record,), None,
            )

        invalid = (
            (TurnDeliveryStatus.DELIVERED, TurnJobState.DELIVERED,
             DeliverySegmentState.CONFIRMED, 0, 99),
            (TurnDeliveryStatus.DELIVERY_UNKNOWN, TurnJobState.DELIVERY_UNKNOWN,
             DeliverySegmentState.UNKNOWN, 0, None),
            (TurnDeliveryStatus.FAILED, TurnJobState.FAILED,
             DeliverySegmentState.FAILED, 0, None),
            (TurnDeliveryStatus.DELIVERY_UNKNOWN, TurnJobState.DELIVERY_UNKNOWN,
             DeliverySegmentState.UNKNOWN, 1, 99),
            (TurnDeliveryStatus.FAILED, TurnJobState.FAILED,
             DeliverySegmentState.FAILED, 1, 99),
            (TurnDeliveryStatus.DELIVERED, TurnJobState.DELIVERED,
             DeliverySegmentState.CONFIRMED, 1, None),
        )
        for shape in invalid:
            with self.subTest(shape=shape):
                with self.assertRaises(TurnDeliveryError) as raised:
                    result(*shape)
                self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)

    def test_turn_delivery_result_rejects_edit_identity_and_sequence_forgery(self):
        job = TurnJobRecord(
            "job-edit", 1, -100, 2, "dialogue-edit", "server-80", "profile-1",
            "thread-1", None, None, "a" * 64, "turn-1", TurnJobState.DELIVERED,
            1, 1, 1, None,
        )
        mismatched_edit = DeliverySegmentRecord(
            "job-edit", 1, DeliveryOperation.EDIT, 77, None, "b" * 64,
            DeliverySegmentState.CONFIRMED, 1, 88, 1, 1,
        )
        later_edit = (
            DeliverySegmentRecord(
                "job-edit", 1, DeliveryOperation.CREATE, None, None, "b" * 64,
                DeliverySegmentState.CONFIRMED, 1, 99, 1, 1,
            ),
            DeliverySegmentRecord(
                "job-edit", 2, DeliveryOperation.EDIT, 100, None, "c" * 64,
                DeliverySegmentState.CONFIRMED, 1, 100, 1, 1,
            ),
        )
        for segments in ((mismatched_edit,), later_edit):
            with self.subTest(segments=segments):
                with self.assertRaises(TurnDeliveryError) as raised:
                    TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, job, segments, None)
                self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)

    def test_turn_delivery_result_rejects_sha_and_timestamp_forgery(self):
        job = TurnJobRecord(
            "job-fields", 1, -100, 2, "dialogue-fields", "server-80", "profile-1",
            "thread-1", None, None, "a" * 64, "turn-1", TurnJobState.DELIVERED,
            1, 1, 1, None,
        )
        invalid_sha = ("B" * 64, "b" * 63, "g" * 64)
        for sha in invalid_sha:
            with self.subTest(sha=sha):
                segment = DeliverySegmentRecord(
                    "job-fields", 1, DeliveryOperation.CREATE, None, None, sha,
                    DeliverySegmentState.CONFIRMED, 1, 99, 1, 1,
                )
                with self.assertRaises(TurnDeliveryError) as raised:
                    TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, job, (segment,), None)
                self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)

        segment = DeliverySegmentRecord(
            "job-fields", 1, DeliveryOperation.CREATE, None, None, "b" * 64,
            DeliverySegmentState.CONFIRMED, 1, 99, 2, 1,
        )
        with self.assertRaises(TurnDeliveryError) as raised:
            TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, job, (segment,), None)
        self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)

    def test_turn_delivery_result_rejects_bool_and_out_of_bounds_segment_fields(self):
        job = TurnJobRecord(
            "job-types", 1, -100, 2, "dialogue-types", "server-80", "profile-1",
            "thread-1", None, None, "a" * 64, "turn-1", TurnJobState.DELIVERED,
            1, 1, 1, None,
        )

        variants = (
            {"sequence": True},
            {"attempt_count": True},
            {"created_at_ms": True},
            {"updated_at_ms": True},
            {"sequence": 0},
            {"created_at_ms": -1},
            {"updated_at_ms": 2**63},
        )
        for changes in variants:
            with self.subTest(changes=changes):
                values = {
                    "job_id": "job-types", "sequence": 1, "operation": DeliveryOperation.CREATE,
                    "target_message_id": None, "payload_id": None, "payload_sha256": "b" * 64,
                    "state": DeliverySegmentState.CONFIRMED, "attempt_count": 1,
                    "confirmed_message_id": 99, "created_at_ms": 1, "updated_at_ms": 1,
                }
                values.update(changes)
                segment = DeliverySegmentRecord(**values)
                with self.assertRaises(TurnDeliveryError) as raised:
                    TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, job, (segment,), None)
                self.assertEqual(TurnDeliveryErrorCategory.INVARIANT, raised.exception.category)
