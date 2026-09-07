import inspect
import unittest
from dataclasses import fields

from codex_control.adapters.codex.approvals import ApprovalKind
from codex_control.storage import (
    ApprovalCallbackClaimResult,
    ApprovalCallbackClaimStatus,
    ApprovalRecord,
    ApprovalRepository,
    ApprovalState,
    DeliveryFinishOutcome,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliverySegmentRecord,
    DeliverySegmentRepository,
    DeliverySegmentState,
    RetentionRepository,
    RetentionSweepResult,
)


class DeliveryApprovalRecordTests(unittest.TestCase):
    def test_exact_enums(self):
        self.assertEqual({"CREATE", "EDIT"}, {x.value for x in DeliveryOperation})
        self.assertEqual({"PENDING", "SENDING", "CONFIRMED", "UNKNOWN", "FAILED"},
                         {x.value for x in DeliverySegmentState})
        self.assertEqual({"CONFIRMED", "UNKNOWN", "FAILED"},
                         {x.value for x in DeliveryFinishOutcome})
        self.assertEqual({"PENDING", "APPROVED", "DENIED", "EXPIRED", "CANCELLED"},
                         {x.value for x in ApprovalState})
        self.assertEqual({"APPROVED", "DENIED", "NOT_FOUND", "UNAUTHORIZED", "EXPIRED",
                          "ALREADY_CONSUMED", "STALE"},
                         {x.value for x in ApprovalCallbackClaimStatus})

    def test_delivery_record_fields_are_exact_and_frozen(self):
        self.assertEqual(
            ["job_id", "sequence", "operation", "target_message_id", "payload_id", "payload_sha256",
             "state", "attempt_count", "confirmed_message_id", "created_at_ms", "updated_at_ms"],
            [x.name for x in fields(DeliverySegmentRecord)],
        )
        item = DeliveryPlanItem(DeliveryOperation.CREATE, "payload", None)
        with self.assertRaises(AttributeError):
            item.operation = DeliveryOperation.EDIT

    def test_approval_record_fields_are_public_wire_id_not_split_columns(self):
        self.assertEqual(
            ["approval_id", "profile_id", "wire_request_id", "kind", "job_id", "display_payload_id",
             "state", "created_at_ms", "updated_at_ms", "expires_at_ms"],
            [x.name for x in fields(ApprovalRecord)],
        )
        self.assertNotIn("wire_request_id_type", ApprovalRecord.__dataclass_fields__)
        self.assertNotIn("wire_request_id_int", ApprovalRecord.__dataclass_fields__)
        self.assertNotIn("wire_request_id_text", ApprovalRecord.__dataclass_fields__)
        self.assertEqual(ApprovalKind.COMMAND_EXECUTION,
                         ApprovalRecord("a", "p", 1, ApprovalKind.COMMAND_EXECUTION, "j", None,
                                        ApprovalState.PENDING, 1, 1, 2).kind)

    def test_result_fields_are_frozen(self):
        self.assertEqual(["status", "record"],
                         [x.name for x in fields(ApprovalCallbackClaimResult)])
        self.assertEqual(["approvals_expired", "payloads_deleted"],
                         [x.name for x in fields(RetentionSweepResult)])

    def test_repository_surfaces_are_exact(self):
        public = lambda cls: {name for name, value in vars(cls).items()
                              if not name.startswith("_") and callable(value)}
        self.assertEqual({"get", "list_for_job", "plan", "claim_next", "finish_sending"},
                         public(DeliverySegmentRepository))
        self.assertEqual({"get", "list_pending_for_job", "create_pending", "claim_callback", "cancel_pending_for_job"},
                         public(ApprovalRepository))
        self.assertEqual({"sweep"}, public(RetentionRepository))
        for cls in (DeliverySegmentRepository, ApprovalRepository, RetentionRepository):
            self.assertFalse(public(cls) & {"send", "edit", "retry", "resend", "delete", "purge",
                                            "background", "run_forever", "respond", "approve_direct"})

    def test_signatures_have_no_external_effect_methods_or_sequence_input(self):
        plan_parameters = set(inspect.signature(DeliverySegmentRepository.plan).parameters)
        self.assertIn("items", plan_parameters)
        self.assertNotIn("sequence", plan_parameters)
        self.assertIn("outcome", inspect.signature(DeliverySegmentRepository.finish_sending).parameters)
        self.assertIn("wire_request_id", inspect.signature(ApprovalRepository.create_pending).parameters)
        self.assertEqual(["self", "limit"], list(inspect.signature(RetentionRepository.sweep).parameters))


if __name__ == "__main__":
    unittest.main()
