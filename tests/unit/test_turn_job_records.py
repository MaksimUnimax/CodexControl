import inspect
import unittest
from dataclasses import fields

from codex_control.storage import (
    TransientPayloadKind,
    TransientPayloadRecord,
    TransientPayloadRepository,
    TurnExecutionClaimResult,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnJobFinishResult,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)


class TurnJobRecordTests(unittest.TestCase):
    def test_exact_enums(self):
        self.assertEqual(
            {"RECEIVED", "CLAIMED", "CODEX_STARTING", "CODEX_RUNNING", "CODEX_COMPLETED",
             "FAILED", "UNKNOWN", "DELIVERY_PENDING", "DELIVERING", "DELIVERED", "DELIVERY_UNKNOWN"},
            {item.value for item in TurnJobState},
        )
        self.assertEqual({"CREATED", "DUPLICATE"}, {item.value for item in TurnIngressClaimStatus})
        self.assertEqual({"COMPLETED", "FAILED", "UNKNOWN"}, {item.value for item in TurnTerminalOutcome})
        self.assertEqual({"INPUT", "OUTPUT", "APPROVAL", "DISPLAY"}, {item.value for item in TransientPayloadKind})

    def test_exact_record_fields_and_immutability(self):
        self.assertEqual(
            ["job_id", "telegram_update_id", "source_chat_id", "source_message_id", "dialogue_id",
             "server_id", "profile_id", "thread_id", "model_id", "reasoning_effort", "input_sha256",
             "codex_turn_id", "state", "version", "created_at_ms", "updated_at_ms", "error_class"],
            [item.name for item in fields(TurnJobRecord)],
        )
        self.assertEqual(
            ["payload_id", "dialogue_id", "job_id", "kind", "content", "content_sha256", "byte_length",
             "created_at_ms", "expires_at_ms"],
            [item.name for item in fields(TransientPayloadRecord)],
        )
        record = TurnJobRecord("j", 1, -1, 2, "d", "s", "p", None, None, None, "a" * 64, None,
                               TurnJobState.RECEIVED, 0, 1, 1, None)
        with self.assertRaises(AttributeError):
            record.state = TurnJobState.CLAIMED

    def test_result_fields_are_exact_and_immutable(self):
        self.assertEqual(["status", "ingress", "job", "input_payload"],
                         [item.name for item in fields(TurnIngressClaimResult)])
        self.assertEqual(["job", "dialogue"], [item.name for item in fields(TurnExecutionClaimResult)])
        self.assertEqual(["job", "dialogue", "output_payload"],
                         [item.name for item in fields(TurnJobFinishResult)])

    def test_payload_content_is_repr_redacted(self):
        secret = b"PRIVATE_P2_4A_CONTENT_MUST_NOT_LEAK"
        record = TransientPayloadRecord("p", "d", None, TransientPayloadKind.OUTPUT, secret,
                                        "a" * 64, len(secret), 1, 2)
        self.assertNotIn(secret.decode(), repr(record))
        self.assertIn("content", TransientPayloadRecord.__dataclass_fields__)
        self.assertFalse(TransientPayloadRecord.__dataclass_fields__["content"].repr)

    def test_records_have_no_content_or_telegram_json_fields(self):
        names = set(TurnJobRecord.__dataclass_fields__)
        self.assertFalse(names & {"input_content", "prompt", "response", "output", "raw_update", "raw_json"})

    def test_public_repository_surfaces_are_exact(self):
        public = lambda cls: {name for name, value in vars(cls).items() if not name.startswith("_") and callable(value)}
        self.assertEqual({"get", "claim_ingress", "claim_turn", "mark_codex_starting", "mark_codex_running", "finish_codex"},
                         public(TurnJobRepository))
        self.assertEqual({"get", "get_input_for_job", "create"}, public(TransientPayloadRepository))
        for cls in (TurnJobRepository, TransientPayloadRepository):
            self.assertFalse(public(cls) & {"delete", "purge", "cleanup", "expire", "retry", "requeue", "transition"})

    def test_public_signatures_are_keyword_only_operations(self):
        self.assertIn("input_content", inspect.signature(TurnJobRepository.claim_ingress).parameters)
        self.assertIn("output_content", inspect.signature(TurnJobRepository.finish_codex).parameters)
        self.assertIn("expires_at_ms", inspect.signature(TransientPayloadRepository.create).parameters)

    def test_payload_size_constant(self):
        from codex_control.storage import MAX_TRANSIENT_PAYLOAD_BYTES
        self.assertEqual(8_388_608, MAX_TRANSIENT_PAYLOAD_BYTES)


if __name__ == "__main__":
    unittest.main()
