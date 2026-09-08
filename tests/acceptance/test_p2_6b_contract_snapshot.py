"""P2.6b frozen contract snapshot acceptance."""

from __future__ import annotations

import inspect
import sqlite3
import tempfile
import unittest
from dataclasses import fields, is_dataclass
from enum import StrEnum

from codex_control.storage import *
from codex_control.storage.schema import INDEX_NAMES, TABLE_NAMES


DDL_SHA = "b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c"


def defined_public_callables(cls: type) -> set[str]:
    return {
        name for name, value in vars(cls).items()
        if not name.startswith("_") and callable(value)
    }


class P26bContractSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_version_hash_and_exact_object_sets(self):
        self.assertEqual(2, SCHEMA_VERSION)
        self.assertEqual("0001_initial_state", MIGRATION_ID)
        self.assertEqual(DDL_SHA, SCHEMA_V1_DDL_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            import os
            storage = await SqliteStorage.open(os.path.join(directory, "state.sqlite3"), now_ms=lambda: 1)
            try:
                actual = await storage.read(lambda c: {
                    "tables": {row[0] for row in c.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )},
                    "indexes": {row[0] for row in c.execute(
                        "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                    )},
                    "user_version": c.execute("PRAGMA user_version").fetchone()[0],
                })
            finally:
                await storage.close()
        expected_tables = {
            "schema_migrations", "controller_runtime", "settings", "dialogues",
            "turn_jobs", "transient_payloads", "delivery_segments", "ingress_updates",
            "callback_actions", "approvals", "deletion_tombstones", "errors",
        }
        expected_indexes = {
            "idx_turn_jobs_dialogue_state", "idx_transient_payloads_expires",
            "idx_transient_payloads_dialogue", "idx_transient_payloads_job",
            "idx_delivery_segments_state", "idx_delivery_segments_payload",
            "idx_callback_actions_expiry", "idx_approvals_job_state_expiry",
            "idx_approvals_wire_request", "idx_approvals_display_payload",
            "idx_deletion_tombstones_expiry", "idx_errors_last_seen",
            "idx_errors_dialogue", "idx_errors_job",
        }
        self.assertEqual(expected_tables, actual["tables"])
        self.assertEqual(expected_indexes, actual["indexes"])
        self.assertEqual(expected_tables, set(TABLE_NAMES))
        self.assertEqual(expected_indexes, set(INDEX_NAMES))
        self.assertEqual(2, actual["user_version"])

    def test_repository_public_surfaces_are_exact(self):
        expected = {
            ControllerRuntimeRepository: {"get", "begin_boot"},
            SettingsRepository: {"get", "initialize_if_absent", "replace"},
            DialogueRepository: {"get_live", "create_intent", "confirm_created", "mark_create_unknown", "mark_create_error"},
            IngressUpdateRepository: {"get", "claim_ignored"},
            ControlIngressRepository: {"claim_control"},
            CallbackActionRepository: {"create", "claim"},
            TurnJobRepository: {"get", "claim_ingress", "claim_turn", "mark_codex_starting", "mark_codex_running", "finish_codex"},
            TransientPayloadRepository: {"get", "get_input_for_job", "create"},
            DeliverySegmentRepository: {"get", "list_for_job", "plan", "claim_next", "finish_sending"},
            ApprovalRepository: {"get", "list_pending_for_job", "create_pending", "claim_callback", "cancel_pending_for_job"},
            RetentionRepository: {"sweep"},
            DeletionRepository: {"get_tombstone", "claim_delete_intent", "claim_deleting", "mark_delete_unknown", "mark_delete_error", "finalize_confirmed"},
            ErrorFingerprintRepository: {"get", "record", "latest"},
            MetadataRetentionRepository: {"sweep"},
        }
        forbidden = {"retry", "requeue", "reset", "reconcile", "transition", "set_state", "send", "respond", "thread_delete", "purge_dialogue", "run_forever"}
        for cls, surface in expected.items():
            with self.subTest(repository=cls.__name__):
                self.assertEqual(surface, defined_public_callables(cls))
                self.assertFalse(forbidden & defined_public_callables(cls))
                for method in surface:
                    self.assertTrue(inspect.iscoroutinefunction(vars(cls)[method]))

    def test_enum_values_are_exact(self):
        expected = {
            DialogueState: "CREATING IDLE CREATE_UNKNOWN ERROR TURN_RUNNING INTERRUPTING TURN_UNKNOWN DELETE_PENDING DELETING DELETE_UNKNOWN",
            IngressDispositionKind: "CONTROL IGNORED_SLEEP IGNORED_UNAUTHORIZED IGNORED_REJECTED JOB",
            ControlClaimStatus: "APPLIED STALE DUPLICATE",
            CallbackClaimStatus: "CLAIMED NOT_FOUND UNAUTHORIZED EXPIRED ALREADY_CONSUMED",
            TurnJobState: "RECEIVED CLAIMED CODEX_STARTING CODEX_RUNNING CODEX_COMPLETED FAILED UNKNOWN DELIVERY_PENDING DELIVERING DELIVERED DELIVERY_UNKNOWN",
            TransientPayloadKind: "INPUT OUTPUT APPROVAL DISPLAY",
            TurnIngressClaimStatus: "CREATED DUPLICATE",
            TurnTerminalOutcome: "COMPLETED FAILED UNKNOWN",
            DeliveryOperation: "CREATE EDIT",
            DeliverySegmentState: "PENDING SENDING CONFIRMED UNKNOWN FAILED",
            DeliveryFinishOutcome: "CONFIRMED UNKNOWN FAILED",
            ApprovalState: "PENDING APPROVED DENIED EXPIRED CANCELLED",
            ApprovalCallbackClaimStatus: "APPROVED DENIED NOT_FOUND UNAUTHORIZED EXPIRED ALREADY_CONSUMED STALE",
        }
        for enum, values in expected.items():
            self.assertTrue(issubclass(enum, StrEnum))
            self.assertEqual(values.split(), [member.value for member in enum])

    def test_public_record_dataclass_fields_are_frozen_and_exact(self):
        expected = {
            ControllerRuntimeRecord: "last_control_epoch requested_mode boot_generation fleet_version created_at_ms updated_at_ms",
            ControllerBootResult: "record effective_mode",
            SettingsRecord: "profile_id model_id reasoning_effort version created_at_ms updated_at_ms",
            SettingsInitializeResult: "record created",
            DialogueRecord: "dialogue_id server_id profile_id thread_id state version created_at_ms updated_at_ms last_error_class",
            IngressUpdateRecord: "update_id received_at_ms completed_at_ms disposition job_id",
            IngressClaimResult: "record duplicate",
            ControlClaimResult: "status ingress controller",
            CallbackActionRecord: "token_hash_sha256 action subject_type subject_id expected_version expected_state authorized_user_id authorized_chat_id created_at_ms expires_at_ms consumed_at_ms",
            CallbackClaimResult: "status record",
            TurnJobRecord: "job_id telegram_update_id source_chat_id source_message_id dialogue_id server_id profile_id thread_id model_id reasoning_effort input_sha256 codex_turn_id state version created_at_ms updated_at_ms error_class",
            TurnIngressClaimResult: "status ingress job input_payload",
            TurnExecutionClaimResult: "job dialogue",
            TurnJobFinishResult: "job dialogue output_payload",
            TransientPayloadRecord: "payload_id dialogue_id job_id kind content content_sha256 byte_length created_at_ms expires_at_ms",
            DeliveryPlanItem: "operation payload_id target_message_id",
            DeliverySegmentRecord: "job_id sequence operation target_message_id payload_id payload_sha256 state attempt_count confirmed_message_id created_at_ms updated_at_ms",
            DeliveryPlanResult: "job segments",
            DeliveryClaimResult: "job segment payload",
            DeliveryFinishResult: "job segment",
            ApprovalRecord: "approval_id profile_id wire_request_id kind job_id display_payload_id state created_at_ms updated_at_ms expires_at_ms",
            ApprovalCallbackClaimResult: "status record",
            DeletionTombstoneRecord: "dialogue_id thread_identity_sha256 stale_generation deleted_at_ms expires_at_ms",
            DeletionFinalizeResult: "tombstone purged_jobs purged_payloads purged_delivery_segments purged_approvals",
            ErrorFingerprintRecord: "fingerprint_sha256 error_class count first_seen_at_ms last_seen_at_ms dialogue_id job_id",
            MetadataRetentionSweepResult: "terminal_jobs_deleted payloads_deleted delivery_segments_deleted approvals_deleted ingress_deleted callback_actions_deleted tombstones_deleted errors_deleted",
        }
        forbidden = {"raw_token", "token", "prompt", "response", "exception", "traceback", "stderr", "stdout", "environment", "secret"}
        for cls, fields_text in expected.items():
            with self.subTest(record=cls.__name__):
                self.assertTrue(is_dataclass(cls))
                self.assertTrue(getattr(cls, "__dataclass_params__").frozen)
                names = [field.name for field in fields(cls)]
                self.assertEqual(fields_text.split(), names)
                self.assertFalse(forbidden & set(names))
        self.assertTrue(fields(TransientPayloadRecord)[4].repr is False)

    async def test_schema_has_only_the_transient_content_column_async(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            storage = await SqliteStorage.open(os.path.join(directory, "state.sqlite3"), now_ms=lambda: 1)
            try:
                columns = await storage.read(lambda c: {
                    table: [row[1] for row in c.execute(f"PRAGMA table_info({table})")]
                    for table in ("controller_runtime", "settings", "dialogues", "turn_jobs", "transient_payloads", "delivery_segments", "ingress_updates", "callback_actions", "approvals", "deletion_tombstones", "errors")
                })
            finally:
                await storage.close()
        self.assertEqual(
            {"content"},
            {column for values in columns.values() for column in values if column in {"content", "prompt", "response", "raw_update", "token"}},
        )
