from __future__ import annotations

import os
import hashlib
import sqlite3
import tempfile
import unittest

from codex_control.storage import (
    IngressDispositionKind,
    IngressUpdateRepository,
    METADATA_RETENTION_MS,
    MetadataRetentionRepository,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V2_MIGRATION_ID,
    SCHEMA_V2_MIGRATION_SHA256,
    SCHEMA_V3_MIGRATION_ID,
    SCHEMA_V3_MIGRATION_SHA256,
    SqliteStorage,
)
from codex_control.storage.schema import SCHEMA_V1_STATEMENTS


class P2C2RejectedIngressSchemaV2AcceptanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_coherent_temporary_sqlite_rejected_ingress_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "state.sqlite3")
            with sqlite3.connect(path) as connection:
                for statement in SCHEMA_V1_STATEMENTS:
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO dialogues(dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms) "
                    "VALUES ('dialogue-1', 'server-1', 'profile-1', 'thread-1', 'IDLE', 0, 1, 1)"
                )
                connection.execute(
                    "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, thread_id, input_sha256, codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                    "VALUES ('job-1', 4, -100, 40, 'dialogue-1', 'server-1', 'profile-1', 'thread-1', ?, 'turn-1', 'FAILED', 0, 1, 1, 'CODEX_TURN_FAILED')",
                    (hashlib.sha256(b"x").hexdigest(),),
                )
                connection.executemany(
                    "INSERT INTO ingress_updates VALUES (?, ?, ?, ?)",
                    [(1, 10, 10, "CONTROL"), (2, 11, 11, "IGNORED_SLEEP"),
                     (3, 12, 12, "IGNORED_UNAUTHORIZED"), (4, 13, 13, "JOB:job-1")],
                )
                connection.execute(
                    "INSERT INTO schema_migrations VALUES (1, '0001_initial_state', ?, 1)",
                    (SCHEMA_V1_DDL_SHA256,),
                )
                connection.execute("PRAGMA user_version = 1")
            os.chmod(path, 0o600)
            migration_calls = []
            storage = await SqliteStorage.open(path, now_ms=lambda: migration_calls.append(1) or 10)
            try:
                ledger = await storage.read(lambda c: (
                    c.execute("PRAGMA user_version").fetchone()[0],
                    [tuple(row) for row in c.execute("SELECT version, migration_id, ddl_sha256 FROM schema_migrations ORDER BY version")],
                ))
                self.assertEqual(4, ledger[0])
                self.assertEqual(4, len(ledger[1]))
                self.assertEqual(SCHEMA_V2_MIGRATION_ID, ledger[1][1][1])
                self.assertEqual(SCHEMA_V2_MIGRATION_SHA256, ledger[1][1][2])
                self.assertEqual(SCHEMA_V3_MIGRATION_ID, ledger[1][2][1])
                self.assertEqual(SCHEMA_V3_MIGRATION_SHA256, ledger[1][2][2])
                self.assertEqual(3, len(migration_calls))
                self.assertEqual("0004_delete_local_containment", ledger[1][3][1])
                self.assertEqual("400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059", ledger[1][3][2])
                self.assertEqual(
                    [(1, "CONTROL"), (2, "IGNORED_SLEEP"),
                     (3, "IGNORED_UNAUTHORIZED"), (4, "JOB:job-1")],
                    await storage.read(lambda c: [tuple(row) for row in c.execute(
                        "SELECT update_id, disposition FROM ingress_updates ORDER BY update_id"
                    )]),
                )

                calls = []
                rejected = await IngressUpdateRepository(storage, now_ms=lambda: calls.append(1) or 20).claim_ignored(
                    update_id=900, disposition=IngressDispositionKind.IGNORED_REJECTED
                )
                self.assertFalse(rejected.duplicate)
                self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, rejected.record.disposition)
                self.assertIsNone(rejected.record.job_id)
                self.assertEqual(rejected.record.received_at_ms, rejected.record.completed_at_ms)
                self.assertEqual(1, len(calls))
            finally:
                await storage.close()

            def migration_trap():
                raise AssertionError("v3 reopen attempted migration")

            storage = await SqliteStorage.open(path, now_ms=migration_trap)
            try:
                duplicate = await IngressUpdateRepository(storage, now_ms=migration_trap).claim_ignored(
                    update_id=900, disposition=IngressDispositionKind.IGNORED_REJECTED
                )
                self.assertTrue(duplicate.duplicate)
                self.assertEqual(rejected.record, duplicate.record)
                self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, duplicate.record.disposition)
                self.assertIsNone(duplicate.record.job_id)

                fresh = await IngressUpdateRepository(storage, now_ms=lambda: 21).claim_ignored(
                    update_id=901, disposition=IngressDispositionKind.IGNORED_REJECTED
                )
                self.assertFalse(fresh.duplicate)

                retention = await MetadataRetentionRepository(
                    storage, now_ms=lambda: METADATA_RETENTION_MS + 20
                ).sweep(1000)
                self.assertGreaterEqual(retention.ingress_deleted, 1)
                self.assertEqual(0, await storage.read(lambda c: c.execute(
                    "SELECT COUNT(*) FROM ingress_updates WHERE update_id = 900"
                ).fetchone()[0]))
                self.assertEqual(1, await storage.read(lambda c: c.execute(
                    "SELECT COUNT(*) FROM ingress_updates WHERE update_id = 901"
                ).fetchone()[0]))
            finally:
                await storage.close()


if __name__ == "__main__":
    unittest.main()
