import asyncio
import hashlib
import os
import sqlite3
import tempfile
import threading
import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ApprovalState,
    CallbackActionRepository,
    ControlIngressRepository,
    ControllerRuntimeRepository,
    DeliverySegmentRepository,
    DialogueRepository,
    ErrorFingerprintRepository,
    IngressUpdateRepository,
    MetadataRetentionRepository,
    METADATA_RETENTION_MS,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TurnJobState,
)


OLD_NOW = METADATA_RETENTION_MS + 100
OLD = "a" * 64
INPUT_HASH = hashlib.sha256(b"x").hexdigest()


class MetadataRetentionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self):
        return await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def sql(self, storage, statement, parameters=()):
        def write(connection):
            connection.execute(statement, parameters)
        await storage.write(write)

    async def query(self, storage, statement, parameters=()):
        def read(connection):
            return tuple(tuple(row) for row in connection.execute(statement, parameters).fetchall())
        return await storage.read(read)

    async def dialogue(self, storage, dialogue_id="d"):
        repo = DialogueRepository(storage, now_ms=lambda: 1)
        await repo.create_intent(dialogue_id=dialogue_id, server_id="server", profile_id="profile")
        return await repo.confirm_created(dialogue_id=dialogue_id, expected_version=0, thread_id="thread")

    async def terminal_job(self, storage, job_id="job", update_id=1, updated=1, state="FAILED"):
        await self.sql(
            storage,
            "INSERT INTO turn_jobs VALUES (?, ?, -100, 1, 'd', 'server', 'profile', "
            "'thread', 'model', 'high', ?, NULL, ?, 0, 1, ?, ?)",
            (job_id, update_id, INPUT_HASH, state, updated, "ERR"),
        )
        await self.sql(
            storage,
            "INSERT INTO transient_payloads VALUES (?, 'd', ?, 'INPUT', ?, ?, 1, 1, 100)",
            (f"input-{job_id}", job_id, b"x", INPUT_HASH),
        )
        await self.sql(
            storage,
            "INSERT INTO ingress_updates VALUES (?, 1, 1, ?)",
            (update_id, f"JOB:{job_id}"),
        )

    async def test_terminal_job_group_counts_children_and_preserves_dialogue(self):
        storage = await self.open()
        try:
            before = await self.dialogue(storage)
            await self.terminal_job(storage)
            await self.sql(
                storage,
                "UPDATE turn_jobs SET codex_turn_id = 'turn', state = 'DELIVERED', error_class = NULL WHERE job_id = 'job'",
            )
            await self.sql(
                storage,
                "INSERT INTO delivery_segments VALUES ('job', 1, 'CREATE', NULL, NULL, ?, 'CONFIRMED', 1, 9, 1, 1)",
                (OLD,),
            )
            await self.sql(
                storage,
                "INSERT INTO approvals VALUES ('approval', 'profile', 'INTEGER', 5, NULL, 'job', "
                "'command_execution', NULL, 'DENIED', 1, 1, 100)",
            )
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual((1, 1, 1, 1, 1), (
                result.terminal_jobs_deleted, result.payloads_deleted,
                result.delivery_segments_deleted, result.approvals_deleted, result.ingress_deleted,
            ))
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM turn_jobs"))
            self.assertIsNone(await IngressUpdateRepository(storage).get(1))
            self.assertEqual(before, await DialogueRepository(storage).get_live())
        finally:
            await storage.close()

    async def test_protected_jobs_do_not_starve_later_eligible_job(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="protected", update_id=1)
            await self.terminal_job(storage, job_id="eligible", update_id=2)
            await self.sql(storage, "UPDATE ingress_updates SET received_at_ms = 101, completed_at_ms = 101 WHERE update_id = 1")
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual(((1,),), await self.query(storage, "SELECT 1 FROM turn_jobs WHERE job_id='protected'"))
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM turn_jobs WHERE job_id='eligible'"))
        finally:
            await storage.close()

    async def test_pending_approval_and_young_ingress_are_protected(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="pending", update_id=1)
            await self.sql(
                storage,
                "INSERT INTO approvals VALUES ('pending-approval', 'profile', 'INTEGER', 5, NULL, 'pending', "
                "'command_execution', NULL, 'PENDING', 1, 1, 100)",
            )
            await self.terminal_job(storage, job_id="young", update_id=2)
            await self.sql(storage, "UPDATE ingress_updates SET received_at_ms = 101, completed_at_ms = 101 WHERE update_id = 2")
            await self.terminal_job(storage, job_id="eligible", update_id=3)
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            remaining = await self.query(storage, "SELECT job_id FROM turn_jobs ORDER BY job_id")
            self.assertEqual(["pending", "young"], [row[0] for row in remaining])
            self.assertEqual(((ApprovalState.PENDING.value,),), await self.query(
                storage, "SELECT state FROM approvals WHERE approval_id='pending-approval'"
            ))
        finally:
            await storage.close()

    async def test_standalone_categories_and_control_epoch(self):
        storage = await self.open()
        try:
            await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
            applied = await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(
                update_id=10, control_epoch=10, requested_mode=ControllerMode.ACTIVE,
            )
            await self.sql(storage, "UPDATE ingress_updates SET received_at_ms = 1, completed_at_ms = 1 WHERE update_id = 10")
            await self.sql(storage, "INSERT INTO ingress_updates VALUES (11, 1, 1, 'IGNORED_SLEEP')")
            await self.sql(storage, "INSERT INTO ingress_updates VALUES (12, 1, 1, 'JOB:orphan')")
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.ingress_deleted)
            self.assertIsNone(await IngressUpdateRepository(storage).get(10))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(11))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(12))
            runtime = await ControllerRuntimeRepository(storage).get()
            self.assertEqual(10, runtime.last_control_epoch)
            stale = await ControlIngressRepository(storage, now_ms=lambda: 3).claim_control(
                update_id=13, control_epoch=10, requested_mode=ControllerMode.SLEEP,
            )
            self.assertEqual("STALE", stale.status.value)
            self.assertEqual(10, (await ControllerRuntimeRepository(storage).get()).last_control_epoch)
            self.assertEqual(applied.controller.boot_generation, runtime.boot_generation)
        finally:
            await storage.close()

    async def test_callback_horizon_and_expired_replay(self):
        storage = await self.open()
        try:
            repo = CallbackActionRepository(storage, now_ms=lambda: 1)
            await repo.create(token_hash_sha256="1" * 64, action="a", subject_type="s", subject_id="x",
                              expected_version=0, expected_state="IDLE", authorized_user_id=1,
                              authorized_chat_id=-2, expires_at_ms=2)
            await repo.create(token_hash_sha256="2" * 64, action="a", subject_type="s", subject_id="x",
                              expected_version=0, expected_state="IDLE", authorized_user_id=1,
                              authorized_chat_id=-2, expires_at_ms=101)
            await repo.create(token_hash_sha256="3" * 64, action="a", subject_type="s", subject_id="x",
                              expected_version=0, expected_state="IDLE", authorized_user_id=1,
                              authorized_chat_id=-2, expires_at_ms=OLD_NOW + 1)
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(10)
            self.assertEqual(1, result.callback_actions_deleted)
            self.assertEqual("NOT_FOUND", (await repo.claim(token_hash_sha256="1" * 64, authorized_user_id=1, authorized_chat_id=-2)).status.value)
            self.assertEqual(((1,),), await self.query(
                storage, "SELECT 1 FROM callback_actions WHERE token_hash_sha256 = ?", ("2" * 64,)
            ))
        finally:
            await storage.close()

    async def test_tombstone_and_error_fk_cleanup(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('old', ?, 1, 1, 2)", (OLD,))
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('future', ?, 1, 1, ?)", (OLD, OLD_NOW + 1))
            await self.terminal_job(storage)
            await self.sql(
                storage,
                "INSERT INTO errors VALUES (?, 'ERR', 1, 101, 101, 'd', 'job')",
                ("b" * 64,),
            )
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(10)
            self.assertEqual(1, result.tombstones_deleted)
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM deletion_tombstones WHERE dialogue_id='old'"))
            self.assertEqual(((1,),), await self.query(storage, "SELECT 1 FROM deletion_tombstones WHERE dialogue_id='future'"))
            error = await ErrorFingerprintRepository(storage).get("b" * 64)
            self.assertIsNotNone(error)
            self.assertIsNone(error.job_id)
            self.assertEqual("d", error.dialogue_id)
        finally:
            await storage.close()

    async def test_per_category_limit_and_restart(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="a", update_id=1)
            await self.terminal_job(storage, job_id="b", update_id=2)
            await self.sql(storage, "INSERT INTO ingress_updates VALUES (3, 1, 1, 'CONTROL')")
            await CallbackActionRepository(storage, now_ms=lambda: 1).create(
                token_hash_sha256="4" * 64, action="a", subject_type="s", subject_id="x",
                expected_version=0, expected_state="IDLE", authorized_user_id=1,
                authorized_chat_id=-2, expires_at_ms=2,
            )
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('t', ?, 1, 1, 2)", (OLD,))
            await self.sql(storage, "INSERT INTO errors VALUES (?, 'ERR', 1, 1, 1, NULL, NULL)", ("5" * 64,))
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual((1, 2, 1, 1, 1), (
                result.terminal_jobs_deleted, result.ingress_deleted,
                result.callback_actions_deleted, result.tombstones_deleted, result.errors_deleted,
            ))
            await storage.close()
            storage = await self.open()
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM turn_jobs WHERE job_id='b'"))
        finally:
            await storage.close()

    async def test_corrupt_later_category_rolls_back_early_job(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage)
            await self.sql(
                storage,
                "INSERT INTO callback_actions VALUES (?, 'a', 's', 'x', 0, 'IDLE', 1, -2, 1, 2, NULL)",
                ("A" * 64,),
            )
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual(((1,),), await self.query(storage, "SELECT 1 FROM turn_jobs WHERE job_id='job'"))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(1))
            self.assertEqual(((1,),), await self.query(storage, "SELECT 1 FROM transient_payloads WHERE job_id='job'"))
        finally:
            await storage.close()

    async def test_alias_corruption_and_live_tombstone_collision_fail_closed(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('d', ?, 1, 1, 2)", (OLD,))
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            await storage.close()
            with sqlite3.connect(self.path) as connection:
                connection.execute("DELETE FROM deletion_tombstones")
                error_hash = "abcdef" * 10 + "abcd"
                connection.execute("INSERT INTO errors VALUES (?, 'ERR', 1, 1, 1, NULL, NULL)", (error_hash,))
                connection.execute("INSERT INTO errors VALUES (?, 'ERR', 1, 1, 1, NULL, NULL)", (error_hash.upper(),))
                connection.commit()
            storage = await self.open()
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_clock_failure_and_repeated_cancellation_are_owned(self):
        storage = await self.open()
        try:
            started = threading.Event()
            release = threading.Event()

            def blocking_clock():
                started.set()
                release.wait(2)
                return OLD_NOW

            task = asyncio.create_task(MetadataRetentionRepository(storage, now_ms=blocking_clock).sweep(1))
            await asyncio.to_thread(started.wait, 2)
            for _ in range(3):
                task.cancel()
                await asyncio.sleep(0)
            release.set()
            result = await task
            self.assertEqual(0, result.terminal_jobs_deleted)

            def bad_clock():
                raise RuntimeError("PRIVATE_P2_6A_CLOCK_MUST_NOT_LEAK")

            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=bad_clock).sweep(1)
            self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertNotIn("PRIVATE_P2_6A_CLOCK_MUST_NOT_LEAK", str(raised.exception))
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
