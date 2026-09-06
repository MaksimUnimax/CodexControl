import unittest

from codex_control.storage import (
    DeletionFinalizeResult,
    DeletionTombstoneRecord,
    ErrorFingerprintRecord,
)


class DeletionErrorRecordTests(unittest.TestCase):
    def test_deletion_tombstone_record_is_immutable_and_content_free(self):
        record = DeletionTombstoneRecord("d", "a" * 64, 3, 10, 20)
        with self.assertRaises(AttributeError):
            record.deleted_at_ms = 11
        self.assertNotIn("PRIVATE_THREAD_ID_MUST_NOT_SURVIVE_DELETE", repr(record))
        self.assertEqual(
            {"dialogue_id", "thread_identity_sha256", "stale_generation", "deleted_at_ms", "expires_at_ms"},
            set(type(record).__dataclass_fields__),
        )

    def test_finalize_result_is_immutable_and_only_contains_counts(self):
        tombstone = DeletionTombstoneRecord("d", "b" * 64, 4, 10, 20)
        result = DeletionFinalizeResult(tombstone, 1, 2, 3, 4)
        with self.assertRaises(AttributeError):
            result.purged_jobs = 5
        self.assertEqual(
            {"tombstone", "purged_jobs", "purged_payloads", "purged_delivery_segments", "purged_approvals"},
            set(type(result).__dataclass_fields__),
        )

    def test_error_fingerprint_record_is_immutable_and_has_no_content_fields(self):
        record = ErrorFingerprintRecord("c" * 64, "STORAGE:failure", 1, 10, 10, None, None)
        with self.assertRaises(AttributeError):
            record.count = 2
        self.assertEqual(
            {
                "fingerprint_sha256", "error_class", "count", "first_seen_at_ms",
                "last_seen_at_ms", "dialogue_id", "job_id",
            },
            set(type(record).__dataclass_fields__),
        )
        for forbidden in ("message", "exception", "traceback", "stderr", "stdout", "prompt", "response", "token"):
            self.assertNotIn(forbidden, type(record).__dataclass_fields__)

    def test_records_are_exact_frozen_dataclasses(self):
        for record in (
            DeletionTombstoneRecord("d", "a" * 64, 0, 0, 1),
            DeletionFinalizeResult(DeletionTombstoneRecord("d", "a" * 64, 0, 0, 1), 0, 0, 0, 0),
            ErrorFingerprintRecord("a" * 64, "E", 1, 0, 0, None, None),
        ):
            self.assertTrue(type(record).__dataclass_params__.frozen)


if __name__ == "__main__":
    unittest.main()
