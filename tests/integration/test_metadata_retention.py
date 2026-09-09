import asyncio
import hashlib
import os
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from codex_control.domain import ControllerMode
import codex_control.storage.metadata_retention as retention_module
from codex_control.storage import (
    ApprovalState,
    CallbackActionRepository,
    ControlIngressRepository,
    ControllerRuntimeRepository,
    DeletionRepository,
    DeliverySegmentRepository,
    DialogueRepository,
    ErrorFingerprintRepository,
    IngressUpdateRepository,
    MetadataRetentionRepository,
    METADATA_RETENTION_MS,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
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

    async def raw_job(self, storage, *, job_id, update_id, state, updated=1,
                      thread="thread", codex_turn=None, error=None):
        await self.sql(
            storage,
            "INSERT INTO turn_jobs VALUES (?, ?, -100, 1, 'd', 'server', 'profile', "
            "?, 'model', 'high', ?, ?, ?, 0, 1, ?, ?)",
            (job_id, update_id, thread, INPUT_HASH, codex_turn, state, updated, error),
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

    async def standalone_ingress(self, storage, update_id, disposition="CONTROL", completed=1):
        await self.sql(
            storage,
            "INSERT INTO ingress_updates VALUES (?, 1, ?, ?)",
            (update_id, completed, disposition),
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

    async def test_job_only_generic_payload_is_cascaded_and_counted_once(self):
        storage = await self.open()
        try:
            before = await self.dialogue(storage)
            await self.terminal_job(storage)
            await TransientPayloadRepository(storage, now_ms=lambda: 2).create(
                payload_id="job-only-display", job_id="job", dialogue_id=None,
                kind=TransientPayloadKind.DISPLAY, content=b"display", expires_at_ms=100,
            )
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual(2, result.payloads_deleted)
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM transient_payloads"))
            self.assertEqual(before, await DialogueRepository(storage).get_live())
        finally:
            await storage.close()

    async def test_delivery_owned_failed_group_is_deleted_with_exact_counts(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="delivery-failed", update_id=7)
            await self.sql(
                storage,
                "UPDATE turn_jobs SET codex_turn_id = 'turn', state = 'FAILED' "
                "WHERE job_id = 'delivery-failed'",
            )
            display = await TransientPayloadRepository(storage, now_ms=lambda: 2).create(
                payload_id="delivery-display", job_id="delivery-failed", dialogue_id="d",
                kind=TransientPayloadKind.DISPLAY, content=b"pending", expires_at_ms=100,
            )
            await self.sql(
                storage,
                "INSERT INTO delivery_segments VALUES "
                "('delivery-failed', 1, 'CREATE', NULL, NULL, ?, 'CONFIRMED', 1, 9, 1, 1), "
                "('delivery-failed', 2, 'CREATE', NULL, NULL, ?, 'FAILED', 1, NULL, 1, 1), "
                "('delivery-failed', 3, 'CREATE', NULL, ?, ?, 'PENDING', 0, NULL, 1, 1)",
                (OLD, OLD, display.payload_id, display.content_sha256),
            )
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual((1, 2, 3, 0, 1), (
                result.terminal_jobs_deleted, result.payloads_deleted,
                result.delivery_segments_deleted, result.approvals_deleted,
                result.ingress_deleted,
            ))
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM turn_jobs"))
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM delivery_segments"))
            self.assertIsNotNone(await DialogueRepository(storage).get_live())
        finally:
            await storage.close()

    async def test_hard_delete_orphan_job_ingress_is_removed_but_tombstone_horizon_remains(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="deleted-job", update_id=8)
            deletion = DeletionRepository(storage, now_ms=lambda: 2)
            await deletion.claim_delete_intent(dialogue_id="d", expected_version=1)
            await deletion.claim_deleting(dialogue_id="d", expected_version=2)
            await deletion.mark_delete_confirmed_pending_storage(dialogue_id="d", expected_version=3)
            await deletion.finalize_confirmed(
                dialogue_id="d", expected_version=4, tombstone_expires_at_ms=OLD_NOW + 1,
            )
            self.assertIsNone(await DialogueRepository(storage).get_live())
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(8))
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.ingress_deleted)
            self.assertIsNone(await IngressUpdateRepository(storage).get(8))
            self.assertEqual((("d",),), await self.query(
                storage, "SELECT dialogue_id FROM deletion_tombstones"
            ))
        finally:
            await storage.close()

    async def test_old_job_ingress_identity_corruption_rolls_back_everything(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage, job_id="job-A", update_id=10)
            await self.sql(storage, "UPDATE ingress_updates SET update_id = 11 WHERE update_id = 10")
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual((("job-A",),), await self.query(storage, "SELECT job_id FROM turn_jobs"))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(11))
        finally:
            await storage.close()

    async def test_incomplete_old_ingress_is_never_selected_or_deleted(self):
        storage = await self.open()
        try:
            await self.standalone_ingress(storage, 20, "CONTROL", completed=None)
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(0, result.ingress_deleted)
            self.assertEqual(((20, None),), await self.query(
                storage, "SELECT update_id, completed_at_ms FROM ingress_updates"
            ))
        finally:
            await storage.close()

    async def test_missing_required_job_ingress_is_invariant_and_blocks_other_cleanup(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage)
            await self.sql(storage, "DELETE FROM ingress_updates WHERE update_id = 1")
            await self.standalone_ingress(storage, 2, "CONTROL")
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual((("job",),), await self.query(storage, "SELECT job_id FROM turn_jobs"))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(2))
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

    async def test_callback_consumed_old_is_deleted_recent_expiry_and_unexpired_are_protected(self):
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
            await self.sql(storage, "UPDATE callback_actions SET consumed_at_ms = 2 WHERE token_hash_sha256 = ?", ("1" * 64,))
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(10)
            self.assertEqual(1, result.callback_actions_deleted)
            self.assertEqual("NOT_FOUND", (await repo.claim(
                token_hash_sha256="1" * 64, authorized_user_id=1, authorized_chat_id=-2,
            )).status.value)
            self.assertEqual(((1,),), await self.query(
                storage, "SELECT 1 FROM callback_actions WHERE token_hash_sha256 = ?", ("2" * 64,)
            ))
            self.assertEqual(((1,),), await self.query(
                storage, "SELECT 1 FROM callback_actions WHERE token_hash_sha256 = ?", ("3" * 64,)
            ))
        finally:
            await storage.close()

    async def test_dual_case_callback_alias_is_invariant_without_deletion(self):
        storage = await self.open()
        try:
            token_hash = "a" * 64
            repo = CallbackActionRepository(storage, now_ms=lambda: 1)
            await repo.create(token_hash_sha256=token_hash, action="a", subject_type="s", subject_id="x",
                              expected_version=0, expected_state="IDLE", authorized_user_id=1,
                              authorized_chat_id=-2, expires_at_ms=2)
            await self.sql(
                storage,
                "INSERT INTO callback_actions VALUES (?, 'a', 's', 'x', 0, 'IDLE', 1, -2, 1, ?, NULL)",
                (token_hash.upper(), OLD_NOW + 1),
            )
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual(((2,),), await self.query(
                storage, "SELECT COUNT(*) FROM callback_actions"
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

    async def test_corrupt_tombstone_rolls_back_an_earlier_terminal_job_cleanup(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage)
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('bad', ?, 1, 1, 2)", (OLD.upper(),))
            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual((("job",),), await self.query(storage, "SELECT job_id FROM turn_jobs"))
            self.assertIsNotNone(await IngressUpdateRepository(storage).get(1))
            self.assertEqual(((1,),), await self.query(
                storage, "SELECT COUNT(*) FROM transient_payloads WHERE job_id='job'"
            ))
            self.assertEqual(((1,),), await self.query(
                storage, "SELECT COUNT(*) FROM deletion_tombstones"
            ))
        finally:
            await storage.close()

    async def test_deterministic_oldest_first_for_every_root_category(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            for index in (1, 2, 3):
                await self.terminal_job(storage, job_id=f"job-{index}", update_id=100 + index, updated=index)
            await self.standalone_ingress(storage, 200, "CONTROL")
            await self.standalone_ingress(storage, 201, "CONTROL")
            await self.standalone_ingress(storage, 202, "CONTROL")
            callback_repo = CallbackActionRepository(storage, now_ms=lambda: 1)
            for index in (1, 2, 3):
                await callback_repo.create(
                    token_hash_sha256=str(index) * 64, action="a", subject_type="s", subject_id="x",
                    expected_version=0, expected_state="IDLE", authorized_user_id=1,
                    authorized_chat_id=-2, expires_at_ms=index + 1,
                )
            for index in (1, 2, 3):
                await self.sql(
                    storage, "INSERT INTO deletion_tombstones VALUES (?, ?, 1, 1, ?)",
                    (f"t-{index}", OLD, index + 1),
                )
                await self.sql(
                    storage, "INSERT INTO errors VALUES (?, 'ERR', 1, ?, ?, NULL, NULL)",
                    (str(index + 3) * 64, index, index),
                )
            first = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, first.terminal_jobs_deleted)
            self.assertEqual(2, first.ingress_deleted)
            self.assertEqual(1, first.callback_actions_deleted)
            self.assertEqual(1, first.tombstones_deleted)
            self.assertEqual(1, first.errors_deleted)
            self.assertEqual((("job-2",), ("job-3",)), await self.query(
                storage, "SELECT job_id FROM turn_jobs ORDER BY job_id"
            ))
            self.assertEqual(((201,), (202,),), await self.query(
                storage, "SELECT update_id FROM ingress_updates WHERE disposition='CONTROL' ORDER BY update_id"
            ))
            second = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, second.terminal_jobs_deleted)
            self.assertEqual(2, second.ingress_deleted)
            self.assertEqual(1, second.callback_actions_deleted)
            self.assertEqual(1, second.tombstones_deleted)
            self.assertEqual(1, second.errors_deleted)
            self.assertEqual((("job-3",),), await self.query(storage, "SELECT job_id FROM turn_jobs"))
        finally:
            await storage.close()

    async def test_terminal_root_limit_bounds_job_materialization(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            for index in range(20):
                await self.terminal_job(storage, job_id=f"bounded-{index:02d}", update_id=300 + index)
            with mock.patch.object(
                retention_module, "_materialize_job", wraps=retention_module._materialize_job,
            ) as materialize:
                result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertLess(materialize.call_count, 20)
        finally:
            await storage.close()

    async def test_standalone_ingress_limit_bounds_ingress_materialization(self):
        storage = await self.open()
        try:
            for index in range(20):
                await self.standalone_ingress(storage, 400 + index, "CONTROL")
            with mock.patch.object(
                retention_module, "_materialize_ingress", wraps=retention_module._materialize_ingress,
            ) as materialize:
                result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.ingress_deleted)
            self.assertEqual(1, materialize.call_count)
        finally:
            await storage.close()

    async def test_callback_limit_bounds_callback_materialization(self):
        storage = await self.open()
        try:
            repo = CallbackActionRepository(storage, now_ms=lambda: 1)
            for index in range(20):
                await repo.create(
                    token_hash_sha256=f"{index + 1:064x}", action="a", subject_type="s", subject_id="x",
                    expected_version=0, expected_state="IDLE", authorized_user_id=1,
                    authorized_chat_id=-2, expires_at_ms=2,
                )
            with mock.patch.object(
                retention_module, "_materialize_callback", wraps=retention_module._materialize_callback,
            ) as materialize:
                result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.callback_actions_deleted)
            self.assertEqual(1, materialize.call_count)
        finally:
            await storage.close()

    async def test_error_limit_bounds_error_materialization(self):
        storage = await self.open()
        try:
            for index in range(20):
                await self.sql(
                    storage, "INSERT INTO errors VALUES (?, 'ERR', 1, ?, ?, NULL, NULL)",
                    (f"{index + 1:064x}", index + 1, index + 1),
                )
            with mock.patch.object(
                retention_module, "_materialize_error", wraps=retention_module._materialize_error,
            ) as materialize:
                result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.errors_deleted)
            self.assertEqual(1, materialize.call_count)
        finally:
            await storage.close()

    async def test_tombstone_limit_bounds_tombstone_materialization(self):
        storage = await self.open()
        try:
            for index in range(20):
                await self.sql(
                    storage, "INSERT INTO deletion_tombstones VALUES (?, ?, 1, 1, ?)",
                    (f"tombstone-{index:02d}", OLD, index + 2),
                )
            with mock.patch.object(
                retention_module, "_materialize_tombstone", wraps=retention_module._materialize_tombstone,
            ) as materialize:
                result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.tombstones_deleted)
            self.assertEqual(1, materialize.call_count)
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
            await self.dialogue(storage)
            await self.terminal_job(storage)
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
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual((), await self.query(storage, "SELECT 1 FROM turn_jobs"))
            self.assertIsNone(await IngressUpdateRepository(storage).get(1))

            await self.terminal_job(storage, job_id="clock-failure", update_id=2)

            def bad_clock():
                raise RuntimeError("PRIVATE_P2_6A_CLOCK_MUST_NOT_LEAK")

            with self.assertRaises(RepositoryError) as raised:
                await MetadataRetentionRepository(storage, now_ms=bad_clock).sweep(1)
            self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertNotIn("PRIVATE_P2_6A_CLOCK_MUST_NOT_LEAK", str(raised.exception))
            self.assertEqual((("clock-failure",),), await self.query(
                storage, "SELECT job_id FROM turn_jobs"
            ))
        finally:
            await storage.close()

    async def test_empty_and_multi_category_sweeps_each_call_the_clock_once(self):
        empty_calls = []
        storage = await self.open()
        try:
            result = await MetadataRetentionRepository(
                storage, now_ms=lambda: empty_calls.append(True) or OLD_NOW,
            ).sweep(1)
            self.assertEqual(0, result.terminal_jobs_deleted)
            self.assertEqual(1, len(empty_calls))
        finally:
            await storage.close()

        calls = []
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.terminal_job(storage)
            await self.standalone_ingress(storage, 2, "CONTROL")
            await CallbackActionRepository(storage, now_ms=lambda: 1).create(
                token_hash_sha256="1" * 64, action="a", subject_type="s", subject_id="x",
                expected_version=0, expected_state="IDLE", authorized_user_id=1,
                authorized_chat_id=-2, expires_at_ms=2,
            )
            await self.sql(storage, "INSERT INTO deletion_tombstones VALUES ('t', ?, 1, 1, 2)", (OLD,))
            await self.sql(storage, "INSERT INTO errors VALUES (?, 'ERR', 1, 1, 1, NULL, NULL)", ("2" * 64,))
            result = await MetadataRetentionRepository(
                storage, now_ms=lambda: calls.append(True) or OLD_NOW,
            ).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual(1, result.callback_actions_deleted)
            self.assertEqual(1, result.tombstones_deleted)
            self.assertEqual(1, result.errors_deleted)
            self.assertEqual(1, len(calls))
        finally:
            await storage.close()

    async def test_active_and_recovery_job_matrix_is_preserved(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            matrix = (
                ("received", 1, "RECEIVED", None, None, None),
                ("claimed", 2, "CLAIMED", "thread", None, None),
                ("starting", 3, "CODEX_STARTING", "thread", None, None),
                ("running", 4, "CODEX_RUNNING", "thread", "turn-running", None),
                ("completed", 5, "CODEX_COMPLETED", "thread", "turn-completed", None),
                ("unknown", 6, "UNKNOWN", "thread", "turn-unknown", "ERR"),
                ("delivery-pending", 7, "DELIVERY_PENDING", "thread", "turn-pending", None),
                ("delivering", 8, "DELIVERING", "thread", "turn-delivering", None),
                ("delivery-unknown", 9, "DELIVERY_UNKNOWN", "thread", "turn-unknown-delivery", "ERR"),
            )
            for job_id, update_id, state, thread, turn, error in matrix:
                await self.raw_job(
                    storage, job_id=job_id, update_id=update_id, state=state,
                    thread=thread, codex_turn=turn, error=error,
                )
            display_repo = TransientPayloadRepository(storage, now_ms=lambda: 1)
            pending = await display_repo.create(
                payload_id="display-pending", job_id="delivery-pending", kind=TransientPayloadKind.DISPLAY,
                content=b"pending", expires_at_ms=100,
            )
            sending = await display_repo.create(
                payload_id="display-sending", job_id="delivering", kind=TransientPayloadKind.DISPLAY,
                content=b"sending", expires_at_ms=100,
            )
            pending_delivery = await display_repo.create(
                payload_id="display-delivering-pending", job_id="delivering", kind=TransientPayloadKind.DISPLAY,
                content=b"pending", expires_at_ms=100,
            )
            unknown = await display_repo.create(
                payload_id="display-unknown", job_id="delivery-unknown", kind=TransientPayloadKind.DISPLAY,
                content=b"unknown", expires_at_ms=100,
            )
            await self.sql(storage, "INSERT INTO delivery_segments VALUES ('delivery-pending', 1, 'CREATE', NULL, ?, ?, 'PENDING', 0, NULL, 1, 1)", (pending.payload_id, pending.content_sha256))
            await self.sql(storage, "INSERT INTO delivery_segments VALUES ('delivering', 1, 'CREATE', NULL, NULL, ?, 'CONFIRMED', 1, 9, 1, 1)", (OLD,))
            await self.sql(storage, "INSERT INTO delivery_segments VALUES ('delivering', 2, 'CREATE', NULL, ?, ?, 'SENDING', 1, NULL, 1, 1)", (sending.payload_id, sending.content_sha256))
            await self.sql(storage, "INSERT INTO delivery_segments VALUES ('delivering', 3, 'CREATE', NULL, ?, ?, 'PENDING', 0, NULL, 1, 1)", (pending_delivery.payload_id, pending_delivery.content_sha256))
            await self.sql(storage, "INSERT INTO delivery_segments VALUES ('delivery-unknown', 1, 'CREATE', NULL, ?, ?, 'UNKNOWN', 1, NULL, 1, 1)", (unknown.payload_id, unknown.content_sha256))
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(0, result.terminal_jobs_deleted)
            self.assertEqual(9, (await self.query(storage, "SELECT COUNT(*) FROM turn_jobs"))[0][0])
            self.assertEqual(9, (await self.query(storage, "SELECT COUNT(*) FROM ingress_updates"))[0][0])
        finally:
            await storage.close()

    async def test_controller_settings_and_live_dialogue_are_exactly_preserved(self):
        storage = await self.open()
        try:
            controller = await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
            settings = await SettingsRepository(storage, now_ms=lambda: 1).initialize_if_absent(
                profile_id="profile", model_id="model", reasoning_effort="high",
            )
            dialogue = await self.dialogue(storage)
            await self.terminal_job(storage)
            result = await MetadataRetentionRepository(storage, now_ms=lambda: OLD_NOW).sweep(1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            self.assertEqual(controller.record, await ControllerRuntimeRepository(storage).get())
            self.assertEqual(settings.record, (await SettingsRepository(storage).initialize_if_absent(
                profile_id=None, model_id=None, reasoning_effort=None,
            )).record)
            self.assertEqual(dialogue, await DialogueRepository(storage).get_live())
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
