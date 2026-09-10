import asyncio
import hashlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.application import (
    DialogueDeleteError,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.storage import (
    ApplicationRecoveryRepository,
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V2_MIGRATION_ID,
    SCHEMA_V2_MIGRATION_SHA256,
    SCHEMA_V3_MIGRATION_ID,
    SCHEMA_V3_MIGRATION_SHA256,
    SqliteStorage,
    StorageError,
    StorageErrorCategory,
)
from codex_control.storage.schema import (
    INDEX_NAMES,
    MIGRATION_ID,
    SCHEMA_V1_STATEMENTS,
    SCHEMA_V2_MIGRATION_STATEMENTS,
)


class _ConfirmedDelete:
    def __init__(self):
        self.calls = []

    async def delete(self, *, binding):
        self.calls.append(binding)
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class P7C2SchemaV3StorageBarrierTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def _make_v1(path):
        with sqlite3.connect(path) as connection:
            for statement in SCHEMA_V1_STATEMENTS:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (1, ?, ?, 11)",
                (MIGRATION_ID, SCHEMA_V1_DDL_SHA256),
            )
            connection.execute("PRAGMA user_version = 1")
        os.chmod(path, 0o600)

    @staticmethod
    def _make_v2(path, *, populated=False):
        P7C2SchemaV3StorageBarrierTests._make_v1(path)
        with sqlite3.connect(path) as connection:
            for statement in SCHEMA_V2_MIGRATION_STATEMENTS:
                connection.execute(statement)
            connection.execute(
                "INSERT INTO schema_migrations VALUES (2, ?, ?, 12)",
                (SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256),
            )
            connection.execute("PRAGMA user_version = 2")
            if populated:
                connection.execute(
                    "INSERT INTO dialogues(dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms) "
                    "VALUES ('d', 's', 'p', 't', 'IDLE', 0, 1, 1)"
                )
                digest = hashlib.sha256(b"x").hexdigest()
                connection.execute(
                    "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, thread_id, input_sha256, codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                    "VALUES ('j', 1, -100, 1, 'd', 's', 'p', 't', ?, 'turn', 'FAILED', 0, 1, 1, 'E')",
                    (digest,),
                )
                connection.execute(
                    "INSERT INTO transient_payloads(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, created_at_ms, expires_at_ms) "
                    "VALUES ('payload', 'd', 'j', 'INPUT', ?, ?, 1, 1, 100)",
                    (b"x", digest),
                )
                connection.execute(
                    "INSERT INTO errors VALUES ('%s', 'E', 1, 1, 1, 'd', 'j')" % ("a" * 64)
                )

    async def _open(self, clock=lambda: 20):
        return await SqliteStorage.open(self.path, now_ms=clock)

    async def test_fresh_v0_v1_v2_v3_ledger_and_hash_order(self):
        calls = []

        def clock():
            calls.append(True)
            return 100 + len(calls)

        storage = await self._open(clock)
        try:
            ledger = await storage.read(lambda c: [tuple(row) for row in c.execute(
                "SELECT version, migration_id, ddl_sha256, applied_at_ms FROM schema_migrations ORDER BY version"
            )])
            self.assertEqual(4, len(calls))
            self.assertEqual(4, await storage.read(lambda c: c.execute("PRAGMA user_version").fetchone()[0]))
            self.assertEqual([
                (1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256, 101),
                (2, SCHEMA_V2_MIGRATION_ID, SCHEMA_V2_MIGRATION_SHA256, 102),
                (3, SCHEMA_V3_MIGRATION_ID, SCHEMA_V3_MIGRATION_SHA256, 103),
                (4, "0004_delete_local_containment", "400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059", 104),
            ], ledger)
            self.assertEqual(
                SCHEMA_V1_DDL_SHA256,
                "b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c",
            )
            self.assertEqual(
                SCHEMA_V2_MIGRATION_SHA256,
                "a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85",
            )
        finally:
            await storage.close()

    async def test_v1_to_v3_and_populated_v2_to_v3_preserve_rows_and_fks(self):
        self._make_v1(self.path)
        storage = await self._open(lambda: 30)
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(4, connection.execute("PRAGMA user_version").fetchone()[0])
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self._make_v2(self.path, populated=True)
        storage = await self._open(lambda: 30)
        try:
            rows = await storage.read(lambda c: {
                table: c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ("dialogues", "turn_jobs", "transient_payloads", "errors")
            })
            self.assertEqual({"dialogues": 1, "turn_jobs": 1, "transient_payloads": 1, "errors": 1}, rows)
            state = await storage.read(lambda c: c.execute("SELECT state FROM dialogues").fetchone()[0])
            self.assertEqual("IDLE", state)
            self.assertEqual([], await storage.read(lambda c: [
                row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE name LIKE '%_v2'")
            ]))
            self.assertEqual(set(INDEX_NAMES), await storage.read(lambda c: {
                row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'")
            }))
        finally:
            await storage.close()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())

    async def test_every_legal_pre_v3_dialogue_state_migrates_unchanged(self):
        cases = (
            ("CREATING", None, None),
            ("IDLE", "thread", None),
            ("CREATE_UNKNOWN", None, "CODEX_AMBIGUOUS"),
            ("ERROR", None, "CODEX_PROCESS"),
            ("TURN_RUNNING", "thread", None),
            ("INTERRUPTING", "thread", None),
            ("TURN_UNKNOWN", "thread", "CODEX_AMBIGUOUS"),
            ("DELETE_PENDING", "thread", None),
            ("DELETING", "thread", None),
            ("DELETE_UNKNOWN", "thread", "DELETE_UNKNOWN"),
        )
        for state, thread_id, error_class in cases:
            with self.subTest(state=state):
                self.tempdir.cleanup()
                self.tempdir = tempfile.TemporaryDirectory()
                self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
                self._make_v2(self.path)
                with sqlite3.connect(self.path) as connection:
                    connection.execute(
                        "INSERT INTO dialogues(dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms, last_error_class) "
                        "VALUES ('d', 's', 'p', ?, ?, 4, 5, 6, ?)",
                        (thread_id, state, error_class),
                    )
                storage = await self._open(lambda: 30)
                try:
                    self.assertEqual(
                        ("d", "s", "p", thread_id, state, 4, 5, 6, error_class),
                        await storage.read(lambda c: tuple(c.execute(
                            "SELECT dialogue_id, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms, last_error_class FROM dialogues"
                        ).fetchone())),
                    )
                finally:
                    await storage.close()

    async def test_application_recovery_rejects_malformed_pending_storage_shape(self):
        storage = await self._open(lambda: 1)
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 1)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            idle = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            deletion = DeletionRepository(storage, now_ms=lambda: 2)
            pending = await deletion.claim_delete_intent(dialogue_id="d", expected_version=idle.version)
            deleting = await deletion.claim_deleting(dialogue_id="d", expected_version=pending.version)
            confirmed = await deletion.mark_delete_confirmed_pending_storage(
                dialogue_id="d", expected_version=deleting.version
            )
            def corrupt(connection):
                connection.execute(
                    "UPDATE dialogues SET thread_id = NULL WHERE dialogue_id = ? AND version = ?",
                    ("d", confirmed.version),
                )
            await storage.write(corrupt)
            with self.assertRaises(RepositoryError) as raised:
                await ApplicationRecoveryRepository(storage, now_ms=lambda: 3).inspect()
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_v3_reopen_is_clock_free_and_failed_v3_rolls_back_exact_v2_then_retries(self):
        self._make_v2(self.path, populated=True)
        calls = []

        def failing_clock():
            calls.append(True)
            return -1

        with self.assertRaises(StorageError) as raised:
            await self._open(failing_clock)
        self.assertEqual(StorageErrorCategory.OPEN_FAILED, raised.exception.category)
        self.assertEqual([True], calls)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(2, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertEqual(2, connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])
            self.assertEqual([], connection.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '%_v2'"
            ).fetchall())
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0])
        storage = await self._open(lambda: 40)
        await storage.close()
        def trap():
            raise AssertionError("v3 reopen migration clock called")
        storage = await self._open(trap)
        await storage.close()

    async def test_forged_v2_and_v3_shapes_fail_closed_without_repair(self):
        for mutation in ("wrong_hash", "missing_migration", "sql_drift", "extra_table", "malformed_dialogue"):
            with self.subTest(mutation=mutation):
                self.tempdir.cleanup()
                self.tempdir = tempfile.TemporaryDirectory()
                self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
                self._make_v2(self.path, populated=mutation == "malformed_dialogue")
                with sqlite3.connect(self.path) as connection:
                    if mutation == "wrong_hash":
                        connection.execute("UPDATE schema_migrations SET ddl_sha256 = ? WHERE version = 2", ("b" * 64,))
                    elif mutation == "missing_migration":
                        connection.execute("DELETE FROM schema_migrations WHERE version = 2")
                    elif mutation == "sql_drift":
                        connection.execute("DROP INDEX idx_errors_job")
                        connection.execute("CREATE INDEX idx_errors_job ON errors(error_class)")
                    elif mutation == "extra_table":
                        connection.execute("CREATE TABLE extra_table(value TEXT)")
                    else:
                        connection.execute("UPDATE dialogues SET state = 'DELETE_PENDING', thread_id = NULL")
                with self.assertRaises(StorageError) as raised:
                    await self._open(lambda: (_ for _ in ()).throw(AssertionError("clock must not run")))
                self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)
                with sqlite3.connect(self.path) as connection:
                    self.assertEqual(2, connection.execute("PRAGMA user_version").fetchone()[0])
                    self.assertEqual([], connection.execute("SELECT name FROM sqlite_master WHERE name LIKE '%_v2'").fetchall())

        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        storage = await self._open(lambda: 1)
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute("ALTER TABLE dialogues RENAME TO dialogues_drift")
        with self.assertRaises(StorageError) as raised:
            await self._open()
        self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)

    async def test_repository_barrier_finalizer_boundary_and_race_safety(self):
        storage = await self._open(lambda: 1)
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 1)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            idle = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            deletion = DeletionRepository(storage, now_ms=lambda: 2)
            pending = await deletion.claim_delete_intent(dialogue_id="d", expected_version=idle.version)
            deleting = await deletion.claim_deleting(dialogue_id="d", expected_version=pending.version)
            with self.assertRaises(RepositoryError) as raised:
                await deletion.finalize_confirmed(
                    dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100
                )
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            confirmed = await deletion.mark_delete_confirmed_pending_storage(
                dialogue_id="d", expected_version=deleting.version
            )
            self.assertEqual(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, confirmed.state)
            self.assertEqual(deleting.version + 1, confirmed.version)
            self.assertEqual(("s", "p", "thread", None), (
                confirmed.server_id, confirmed.profile_id, confirmed.thread_id, confirmed.last_error_class
            ))
            self.assertIsNone(await deletion.get_tombstone("d"))
            with self.assertRaises(RepositoryError) as raised:
                await deletion.mark_delete_confirmed_pending_storage(
                    dialogue_id="d", expected_version=confirmed.version
                )
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            finalized = await deletion.finalize_confirmed(
                dialogue_id="d", expected_version=confirmed.version, tombstone_expires_at_ms=100
            )
            self.assertEqual(confirmed.version, finalized.tombstone.stale_generation)
        finally:
            await storage.close()

    async def test_finalize_from_delete_unknown_is_rejected(self):
        storage = await self._open(lambda: 1)
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 1)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            idle = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            deletion = DeletionRepository(storage, now_ms=lambda: 2)
            pending = await deletion.claim_delete_intent(dialogue_id="d", expected_version=idle.version)
            deleting = await deletion.claim_deleting(dialogue_id="d", expected_version=pending.version)
            unknown = await deletion.mark_delete_unknown(
                dialogue_id="d", expected_version=deleting.version, error_class="DELETE_UNKNOWN"
            )
            with self.assertRaises(RepositoryError) as raised:
                await deletion.finalize_confirmed(
                    dialogue_id="d", expected_version=unknown.version, tombstone_expires_at_ms=100
                )
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            self.assertIsNone(await deletion.get_tombstone("d"))
        finally:
            await storage.close()

    async def test_confirmed_application_barrier_replay_failure_and_recovery_are_zero_retry(self):
        storage = await self._open(lambda: 1)
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 1)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            idle = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            lifecycle = _ConfirmedDelete()
            service = DialogueDeleteService(storage, server_id="s", thread_lifecycle=lifecycle, now_ms=lambda: 2)
            result = await service.delete(DialogueDeleteRequest("d", idle.version))
            self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, result.status)
            self.assertEqual(1, len(lifecycle.calls))
            self.assertEqual(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, result.dialogue.state)
            self.assertIsNone(result.tombstone)
            self.assertIsNotNone(await DialogueRepository(storage).get_live())
            replay = await service.delete(DialogueDeleteRequest("d", result.dialogue.version))
            self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, replay.status)
            self.assertEqual(1, len(lifecycle.calls))

            recovery = await DialogueRecoveryService(storage, now_ms=lambda: 3).recover_startup()
            self.assertEqual(DialogueRecoveryStatus.DELETE_CONFIRMED_STORAGE_PENDING, recovery.status)
            self.assertEqual(result.dialogue, recovery.dialogue)

        finally:
            await storage.close()

    async def test_confirmed_application_local_transition_failure_keeps_deleting_and_does_not_retry(self):
        storage = await self._open(lambda: 1)
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 1)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            idle = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            lifecycle = _ConfirmedDelete()
            with patch(
                "codex_control.application.dialogue_delete.DeletionRepository.mark_delete_confirmed_pending_storage",
                side_effect=RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION),
            ):
                with self.assertRaises(DialogueDeleteError) as raised:
                    await DialogueDeleteService(
                        storage, server_id="s", thread_lifecycle=lifecycle, now_ms=lambda: 2
                    ).delete(DialogueDeleteRequest("d", idle.version))
            self.assertEqual("INVARIANT", str(raised.exception))
            self.assertEqual(1, len(lifecycle.calls))
            current = await DialogueRepository(storage).get_live()
            self.assertEqual(DialogueState.DELETING, current.state)
            self.assertIsNone(await DeletionRepository(storage).get_tombstone("d"))
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
