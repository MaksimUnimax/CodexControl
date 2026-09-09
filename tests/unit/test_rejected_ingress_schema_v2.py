import hashlib
import inspect
import unittest

from codex_control.storage import (
    IngressDispositionKind,
    IngressUpdateRepository,
    MIGRATION_ID,
    SCHEMA_VERSION,
    SCHEMA_V1_CANONICAL_SQL,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V1_STATEMENTS,
    SCHEMA_V2_MIGRATION_ID,
    SCHEMA_V2_MIGRATION_SHA256,
    SCHEMA_V3_MIGRATION_ID,
    SCHEMA_V3_MIGRATION_SHA256,
)
from codex_control.storage.schema import (
    SCHEMA_V2_MIGRATION_STATEMENTS,
    canonicalize_sql,
)


class RejectedIngressSchemaV2UnitTests(unittest.TestCase):
    def test_current_and_historical_schema_authority(self):
        self.assertEqual(3, SCHEMA_VERSION)
        self.assertEqual("0001_initial_state", MIGRATION_ID)
        self.assertEqual(
            "b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c",
            SCHEMA_V1_DDL_SHA256,
        )
        historical = "\n".join(canonicalize_sql(s) for s in SCHEMA_V1_STATEMENTS) + "\n"
        self.assertEqual(historical, SCHEMA_V1_CANONICAL_SQL)
        self.assertEqual(SCHEMA_V1_DDL_SHA256, hashlib.sha256(historical.encode()).hexdigest())

    def test_v2_migration_statements_are_exact_and_hash_derived(self):
        expected = (
            "ALTER TABLE ingress_updates RENAME TO ingress_updates_v1;",
            "CREATE TABLE ingress_updates ( update_id INTEGER PRIMARY KEY CHECK (update_id >= 0), received_at_ms INTEGER NOT NULL CHECK (received_at_ms >= 0), completed_at_ms INTEGER CHECK (completed_at_ms IS NULL OR completed_at_ms >= received_at_ms), disposition TEXT NOT NULL CHECK ( disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED','IGNORED_REJECTED') OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) > 4) ) );",
            "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) SELECT update_id, received_at_ms, completed_at_ms, disposition FROM ingress_updates_v1;",
            "DROP TABLE ingress_updates_v1;",
        )
        canonical = tuple(canonicalize_sql(s) for s in SCHEMA_V2_MIGRATION_STATEMENTS)
        self.assertEqual(expected, canonical)
        digest = hashlib.sha256(("\n".join(canonical) + "\n").encode()).hexdigest()
        self.assertEqual("0002_ingress_rejected_disposition", SCHEMA_V2_MIGRATION_ID)
        self.assertEqual(
            "a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85",
            SCHEMA_V2_MIGRATION_SHA256,
        )
        self.assertEqual(SCHEMA_V2_MIGRATION_SHA256, digest)

    def test_enum_is_exactly_ordered(self):
        self.assertEqual(
            ["CONTROL", "IGNORED_SLEEP", "IGNORED_UNAUTHORIZED", "IGNORED_REJECTED", "JOB"],
            [value.value for value in IngressDispositionKind],
        )

    def test_public_exports_and_repository_surface(self):
        from codex_control import storage

        for name in (
            "MIGRATION_ID", "SCHEMA_VERSION", "SCHEMA_V1_DDL_SHA256",
            "SCHEMA_V2_MIGRATION_ID", "SCHEMA_V2_MIGRATION_SHA256",
            "SCHEMA_V3_MIGRATION_ID", "SCHEMA_V3_MIGRATION_SHA256",
        ):
            self.assertIn(name, storage.__all__)
            self.assertTrue(hasattr(storage, name))
        public = {
            name for name, value in vars(IngressUpdateRepository).items()
            if not name.startswith("_") and callable(value)
        }
        self.assertEqual({"get", "claim_ignored"}, public)
        self.assertTrue(inspect.iscoroutinefunction(IngressUpdateRepository.claim_ignored))

    def test_materializer_exact_rejected_and_near_misses_fail_closed(self):
        from codex_control.storage.idempotency_repositories import _materialize_ingress
        from codex_control.storage.repository_errors import RepositoryError, RepositoryErrorCategory

        record = _materialize_ingress((1, 10, 10, "IGNORED_REJECTED"))
        self.assertIs(IngressDispositionKind.IGNORED_REJECTED, record.disposition)
        self.assertIsNone(record.job_id)
        for value in ("IGNORED_REJECT", "ignored_rejected", "IGNORED_REJECTED:", "JOB:", "arbitrary"):
            with self.subTest(value=value):
                with self.assertRaises(RepositoryError) as raised:
                    _materialize_ingress((1, 10, 10, value))
                self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)


if __name__ == "__main__":
    unittest.main()
