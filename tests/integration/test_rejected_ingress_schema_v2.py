from __future__ import annotations

import hashlib
import os
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
    SqliteStorage,
    StorageError,
    StorageErrorCategory,
)
from codex_control.storage.schema import SCHEMA_V1_STATEMENTS


class RejectedIngressSchemaV2IntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "state.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def _make_v1(path: str, *, populated: bool = False) -> list[tuple]:
        rows = [
            (1, 10, 10, "CONTROL"),
            (2, 11, 11, "IGNORED_SLEEP"),
            (3, 12, 12, "IGNORED_UNAUTHORIZED"),
            (4, 13, 13, "JOB:job-1"),
        ] if populated else []
        with sqlite3.connect(path) as connection:
            for statement in SCHEMA_V1_STATEMENTS:
                connection.execute(statement)
            if populated:
                connection.execute(
                    "INSERT INTO dialogues(dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms) "
                    "VALUES ('dialogue-1', 'server-1', 'profile-1', 'thread-1', 'IDLE', 0, 1, 1)"
                )
                connection.execute(
                    "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, thread_id, input_sha256, codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                    "VALUES ('job-1', 4, -100, 40, 'dialogue-1', 'server-1', 'profile-1', 'thread-1', ?, 'turn-1', 'FAILED', 0, 1, 1, 'CODEX_TURN_FAILED')",
                    (hashlib.sha256(b"x").hexdigest(),),
                )
                for row in rows:
                    connection.execute("INSERT INTO ingress_updates VALUES (?, ?, ?, ?)", row)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (1, '0001_initial_state', ?, 123)",
                (SCHEMA_V1_DDL_SHA256,),
            )
            connection.execute("PRAGMA user_version = 1")
        os.chmod(path, 0o600)
        return rows

    @staticmethod
    def _mutate(path: str, statement: str, parameters: tuple = ()) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute(statement, parameters)

    async def _fresh_v2(self, *, now_ms=lambda: 1):
        return await SqliteStorage.open(self.path, now_ms=now_ms)

    async def test_fresh_v0_bootstraps_v2_with_two_clock_calls_and_exact_ledger(self):
        calls = []

        def clock():
            calls.append(1)
            return 100 + len(calls)

        storage = await self._fresh_v2(now_ms=clock)
        try:
            self.assertEqual(2, len(calls))
            actual = await storage.read(lambda c: (
                c.execute("PRAGMA user_version").fetchone()[0],
                [tuple(row) for row in c.execute("SELECT version, migration_id, ddl_sha256, applied_at_ms FROM schema_migrations ORDER BY version")],
            ))
            self.assertEqual(2, actual[0])
            self.assertEqual(
                [
                    (1, "0001_initial_state", SCHEMA_V1_DDL_SHA256, 101),
                    (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256, 102),
                ],
                actual[1],
            )
        finally:
            await storage.close()

    async def test_v2_reopen_does_not_call_clock(self):
        storage = await self._fresh_v2(now_ms=lambda: 1)
        await storage.close()

        def trap():
            raise AssertionError("v2 migration clock called on reopen")

        storage = await self._fresh_v2(now_ms=trap)
        await storage.close()

    async def test_populated_v1_migrates_row_for_row_and_preserves_job_relation(self):
        before = self._make_v1(self.path, populated=True)
        calls = []
        storage = await SqliteStorage.open(self.path, now_ms=lambda: calls.append(1) or 456)
        try:
            after = await storage.read(lambda c: [tuple(row) for row in c.execute(
                "SELECT update_id, received_at_ms, completed_at_ms, disposition FROM ingress_updates ORDER BY update_id"
            )])
            self.assertEqual(before, after)
            self.assertEqual(1, len(calls))
            self.assertEqual(2, await storage.read(lambda c: c.execute("PRAGMA user_version").fetchone()[0]))
            self.assertEqual(1, await storage.read(lambda c: c.execute(
                "SELECT COUNT(*) FROM ingress_updates WHERE disposition = 'JOB:job-1'"
            ).fetchone()[0]))
            ingress = await IngressUpdateRepository(storage).get(4)
            self.assertEqual(IngressDispositionKind.JOB, ingress.disposition)
            self.assertEqual("job-1", ingress.job_id)
        finally:
            await storage.close()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual([], connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'ingress_updates_v1'"
            ).fetchall())

    async def test_malformed_v1_fails_before_v2_clock_and_without_backup(self):
        mutations = (
            "UPDATE schema_migrations SET ddl_sha256 = 'c' || substr(ddl_sha256, 2)",
            "DELETE FROM schema_migrations",
            "DROP INDEX idx_errors_job",
            "CREATE TABLE extra_user_object (value TEXT)",
            "ALTER TABLE errors RENAME TO errors_old",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                for path in (self.path, self.path + ".lock"):
                    if os.path.exists(path):
                        os.remove(path)
                self._make_v1(self.path)
                self._mutate(self.path, mutation)
                calls = []
                with self.assertRaises(StorageError) as raised:
                    await SqliteStorage.open(self.path, now_ms=lambda: calls.append(1) or 5)
                self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)
                self.assertEqual([], calls)
                with sqlite3.connect(self.path) as connection:
                    self.assertEqual(1, connection.execute("PRAGMA user_version").fetchone()[0])
                    self.assertEqual([], connection.execute(
                        "SELECT name FROM sqlite_master WHERE name = 'ingress_updates_v1'"
                    ).fetchall())
                os.remove(self.path)

    async def test_forged_v2_variants_fail_closed(self):
        cases = ("old_ingress", "missing_v2", "wrong_hash", "backup", "sql_drift", "bad_disposition")
        for case in cases:
            with self.subTest(case=case):
                if case == "old_ingress":
                    self._make_v1(self.path)
                    self._mutate(self.path, "INSERT INTO schema_migrations VALUES (2, ?, ?, 2)", (SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256))
                    self._mutate(self.path, "PRAGMA user_version = 2")
                else:
                    storage = await self._fresh_v2(now_ms=lambda: 1)
                    await storage.close()
                    if case == "missing_v2":
                        self._mutate(self.path, "DELETE FROM schema_migrations WHERE version = 2")
                    elif case == "wrong_hash":
                        self._mutate(self.path, "UPDATE schema_migrations SET ddl_sha256 = ? WHERE version = 2", ("c" * 64,))
                    elif case == "backup":
                        self._mutate(self.path, "CREATE TABLE ingress_updates_v1 (value TEXT)")
                    elif case == "sql_drift":
                        self._mutate(self.path, "DROP INDEX idx_errors_job")
                        self._mutate(self.path, "CREATE INDEX idx_errors_job ON errors(error_class)")
                    else:
                        with sqlite3.connect(self.path) as connection:
                            connection.execute("PRAGMA ignore_check_constraints = ON")
                            connection.execute("INSERT INTO ingress_updates VALUES (99, 1, 1, 'IGNORED_REJECT')")
                with self.assertRaises(StorageError) as raised:
                    await SqliteStorage.open(self.path)
                self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)
                os.remove(self.path)

    async def test_failed_v2_migration_rolls_back_exact_v1_and_retry_succeeds(self):
        self._make_v1(self.path)
        calls = []

        def invalid_clock():
            calls.append(1)
            return -1

        with self.assertRaises(StorageError) as raised:
            await SqliteStorage.open(self.path, now_ms=invalid_clock)
        self.assertEqual(StorageErrorCategory.OPEN_FAILED, raised.exception.category)
        self.assertEqual([1], calls)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(1, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual([], connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'ingress_updates_v1'"
            ).fetchall())
            self.assertEqual([(1, "0001_initial_state", SCHEMA_V1_DDL_SHA256, 123)], connection.execute(
                "SELECT version, migration_id, ddl_sha256, applied_at_ms FROM schema_migrations"
            ).fetchall())
        storage = await SqliteStorage.open(self.path, now_ms=lambda: 789)
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(2, connection.execute("PRAGMA user_version").fetchone()[0])

    async def test_rejected_claim_materializes_is_content_free_and_duplicate_is_clock_free(self):
        storage = await self._fresh_v2(now_ms=lambda: 1)
        try:
            calls = []
            repo = IngressUpdateRepository(storage, now_ms=lambda: calls.append(1) or 50)
            first = await repo.claim_ignored(update_id=500, disposition=IngressDispositionKind.IGNORED_REJECTED)
            self.assertFalse(first.duplicate)
            self.assertEqual(IngressDispositionKind.IGNORED_REJECTED, first.record.disposition)
            self.assertIsNone(first.record.job_id)
            self.assertEqual(50, first.record.received_at_ms)
            self.assertEqual(50, first.record.completed_at_ms)
            self.assertEqual(1, await storage.read(lambda c: c.execute(
                "SELECT COUNT(*) FROM ingress_updates WHERE disposition = 'IGNORED_REJECTED'"
            ).fetchone()[0]))

            def trap():
                raise AssertionError("duplicate rejected claim called clock")

            duplicate = await IngressUpdateRepository(storage, now_ms=trap).claim_ignored(
                update_id=500, disposition=IngressDispositionKind.IGNORED_REJECTED
            )
            self.assertTrue(duplicate.duplicate)
            self.assertEqual(first.record, duplicate.record)
            self.assertEqual(1, len(calls))
        finally:
            await storage.close()

    async def test_duplicate_rejected_request_preserves_every_existing_disposition(self):
        storage = await self._fresh_v2(now_ms=lambda: 1)
        try:
            await storage.write(lambda c: (
                c.execute("INSERT INTO dialogues(dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms) VALUES ('d', 's', 'p', 't', 'IDLE', 0, 1, 1)"),
                c.execute("INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, thread_id, input_sha256, codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) VALUES ('j', 4, -100, 4, 'd', 's', 'p', 't', ?, 'turn', 'FAILED', 0, 1, 1, 'CODEX_TURN_FAILED')", (hashlib.sha256(b'x').hexdigest(),)),
                c.executemany("INSERT INTO ingress_updates VALUES (?, 1, 1, ?)", [(1, "CONTROL"), (2, "IGNORED_SLEEP"), (3, "IGNORED_UNAUTHORIZED"), (4, "IGNORED_REJECTED"), (5, "JOB:j")]),
                None,
            )[3])
            original = {index: await IngressUpdateRepository(storage).get(index) for index in range(1, 6)}
            for index in range(1, 6):
                result = await IngressUpdateRepository(storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).claim_ignored(
                    update_id=index, disposition=IngressDispositionKind.IGNORED_REJECTED
                )
                self.assertTrue(result.duplicate)
                self.assertEqual(original[index], result.record)
        finally:
            await storage.close()

    async def test_rejected_ingress_uses_existing_standalone_retention_policy(self):
        storage = await self._fresh_v2(now_ms=lambda: 1)
        try:
            await IngressUpdateRepository(storage, now_ms=lambda: 1).claim_ignored(
                update_id=600, disposition=IngressDispositionKind.IGNORED_REJECTED
            )
            await IngressUpdateRepository(storage, now_ms=lambda: 2).claim_ignored(
                update_id=601, disposition=IngressDispositionKind.IGNORED_REJECTED
            )
            result = await MetadataRetentionRepository(
                storage, now_ms=lambda: METADATA_RETENTION_MS + 1
            ).sweep(1)
            self.assertEqual(1, result.ingress_deleted)
            remaining = await storage.read(lambda c: [tuple(row) for row in c.execute(
                "SELECT update_id, disposition FROM ingress_updates ORDER BY update_id"
            )])
            self.assertEqual([(601, "IGNORED_REJECTED")], remaining)
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
