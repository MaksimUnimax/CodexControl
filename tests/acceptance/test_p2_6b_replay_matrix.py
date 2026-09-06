"""P2.6b replay and no-blind-effect acceptance matrix."""
from __future__ import annotations

import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import *
from tests.acceptance.test_p2_6b_support import (
    TempDatabase,
    create_received,
    finish_delivery,
    make_approval,
)


class P26bReplayMatrixTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = TempDatabase.create()

    def tearDown(self):
        self.db.cleanup()

    async def open(self, now: int = 1_000):
        return await SqliteStorage.open(self.db.path, now_ms=lambda: now)

    async def test_same_update_across_reopens_is_one_job_input_and_ingress(self):
        storage = await self.open()
        created = await create_received(storage)
        await storage.close()
        for index in range(3):
            storage = await self.open()
            try:
                replay = await TurnJobRepository(storage, now_ms=lambda: 2_000 + index).claim_ingress(
                    update_id=101, job_id=f"caller-job-{index}", source_chat_id=-1002,
                    source_message_id=500 + index, dialogue_id="dialogue-1", server_id="other",
                    profile_id="other", thread_id="other", model_id="other", reasoning_effort="low",
                    input_payload_id=f"caller-input-{index}", input_content=b"different", input_expires_at_ms=100_000,
                )
                self.assertEqual(TurnIngressClaimStatus.DUPLICATE, replay.status)
                self.assertEqual(created.job, replay.job)
                self.assertEqual(created.input_payload, replay.input_payload)
            finally:
                await storage.close()
        storage = await self.open()
        try:
            counts = await storage.read(lambda c: tuple(c.execute("SELECT (SELECT COUNT(*) FROM turn_jobs), (SELECT COUNT(*) FROM transient_payloads WHERE kind='INPUT'), (SELECT COUNT(*) FROM ingress_updates WHERE disposition LIKE 'JOB:%')").fetchone()))
            self.assertEqual((1, 1, 1), counts)
        finally:
            await storage.close()

    async def test_outstanding_received_blocks_u2_u3_without_queue(self):
        storage = await self.open()
        await create_received(storage)
        await storage.close()
        for update_id in (102, 103):
            storage = await self.open()
            try:
                with self.assertRaises(RepositoryError) as raised:
                    await TurnJobRepository(storage, now_ms=lambda: 2_000).claim_ingress(
                        update_id=update_id, job_id=f"job-{update_id}", source_chat_id=-1001,
                        source_message_id=update_id, dialogue_id="dialogue-1", server_id="server-1",
                        profile_id="profile-1", thread_id="thread-1", model_id="model-test",
                        reasoning_effort="medium", input_payload_id=f"input-{update_id}",
                        input_content=b"second", input_expires_at_ms=100_000,
                    )
                self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            finally:
                await storage.close()
        storage = await self.open()
        try:
            self.assertEqual(1, await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
        finally:
            await storage.close()

    async def test_control_replay_is_duplicate_and_new_stale_epoch_cannot_reactivate(self):
        storage = await self.open()
        await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet")
        await ControlIngressRepository(storage, now_ms=lambda: 2).claim_control(update_id=10, control_epoch=10, requested_mode=ControllerMode.ACTIVE)
        await storage.close()
        storage = await self.open()
        try:
            await ControllerRuntimeRepository(storage, now_ms=lambda: 3).begin_boot("fleet-restart")
            controls = ControlIngressRepository(storage, now_ms=lambda: 4)
            duplicate = await controls.claim_control(update_id=10, control_epoch=10, requested_mode=ControllerMode.ACTIVE)
            self.assertEqual(ControlClaimStatus.DUPLICATE, duplicate.status)
            self.assertIsNone(duplicate.controller)
            stale = await controls.claim_control(update_id=11, control_epoch=9, requested_mode=ControllerMode.ACTIVE)
            self.assertEqual(ControlClaimStatus.STALE, stale.status)
            runtime = await ControllerRuntimeRepository(storage).get()
            self.assertEqual(10, runtime.last_control_epoch)
            self.assertEqual(ControllerMode.ACTIVE, runtime.requested_mode)
        finally:
            await storage.close()

    async def test_callback_claimed_expired_stale_are_one_time_across_reopens(self):
        storage = await self.open()
        approval, token = await make_approval(storage, token_label="replay-allow")
        await storage.close()
        storage = await self.open()
        try:
            result = await ApprovalRepository(storage, now_ms=lambda: 1_500).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.APPROVED, result.status)
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        for _ in range(2):
            storage = await self.open()
            try:
                replay = await ApprovalRepository(storage).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
                self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)
            finally:
                await storage.close()

        db = TempDatabase.create()
        storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
        try:
            approval, token = await make_approval(storage, approval_id="approval-expired", token_label="replay-expired", expires_at_ms=2_000)
            expired = await ApprovalRepository(storage, now_ms=lambda: 2_000).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.EXPIRED, expired.status)
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, (await ApprovalRepository(storage).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)).status)
        finally:
            await storage.close()
            db.cleanup()

        db = TempDatabase.create()
        storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
        try:
            approval, token = await make_approval(storage, approval_id="approval-stale-replay", token_label="replay-stale")
            await TurnJobRepository(storage, now_ms=lambda: 2).finish_codex(job_id="job-1", expected_job_version=3, expected_dialogue_version=2, outcome=TurnTerminalOutcome.COMPLETED)
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            stale = await ApprovalRepository(storage, now_ms=lambda: 2).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.STALE, stale.status)
            self.assertEqual(ApprovalState.PENDING, (await ApprovalRepository(storage).get(approval.approval_id)).state)
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            replay = await ApprovalRepository(storage).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)
        finally:
            await storage.close()
            db.cleanup()

    async def test_sending_is_never_reclaimed_and_attempt_stays_one(self):
        storage = await self.open()
        from tests.acceptance.test_p2_6b_support import add_display_payload, create_completed
        completed = await create_completed(storage)
        await add_display_payload(storage)
        plan = await DeliverySegmentRepository(storage, now_ms=lambda: 10).plan(job_id="job-1", expected_job_version=completed.job.version, items=[DeliveryPlanItem(DeliveryOperation.CREATE, "display-1", None)])
        claim = await DeliverySegmentRepository(storage, now_ms=lambda: 11).claim_next(job_id="job-1", expected_job_version=plan.job.version)
        await storage.close()
        for _ in range(3):
            storage = await self.open()
            try:
                with self.assertRaises(RepositoryError) as raised:
                    await DeliverySegmentRepository(storage).claim_next(job_id="job-1", expected_job_version=claim.job.version)
                self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
                segment = await DeliverySegmentRepository(storage).get("job-1", 1)
                self.assertEqual((DeliverySegmentState.SENDING, 1), (segment.state, segment.attempt_count))
            finally:
                await storage.close()

    async def test_delivery_unknown_has_no_retry_or_reset_after_reopen(self):
        storage = await self.open()
        finished = await finish_delivery(storage, outcome=DeliveryFinishOutcome.UNKNOWN)
        await storage.close()
        for _ in range(2):
            storage = await self.open()
            try:
                with self.assertRaises(RepositoryError) as raised:
                    await DeliverySegmentRepository(storage).claim_next(job_id="job-1", expected_job_version=finished.job.version)
                self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
                self.assertEqual(DeliverySegmentState.UNKNOWN, (await DeliverySegmentRepository(storage).get("job-1", 1)).state)
            finally:
                await storage.close()

    async def test_delete_unknown_has_no_retry_surface_or_return_to_deleting(self):
        from tests.acceptance.test_p2_6b_support import make_deleteable
        self.assertEqual({"get_tombstone", "claim_delete_intent", "claim_deleting", "mark_delete_unknown", "mark_delete_error", "finalize_confirmed"}, {
            name for name, value in vars(DeletionRepository).items() if not name.startswith("_") and callable(value)
        })
        storage = await self.open()
        dialogue, deletion = await make_deleteable(storage)
        pending = await DeletionRepository(storage, now_ms=lambda: 2).claim_delete_intent(dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version)
        deleting = await DeletionRepository(storage, now_ms=lambda: 3).claim_deleting(dialogue_id=dialogue.dialogue_id, expected_version=pending.version)
        unknown = await DeletionRepository(storage, now_ms=lambda: 4).mark_delete_unknown(dialogue_id=dialogue.dialogue_id, expected_version=deleting.version, error_class="CODEX_AMBIGUOUS")
        await storage.close()
        storage = await self.open()
        try:
            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage).claim_deleting(dialogue_id=dialogue.dialogue_id, expected_version=unknown.version)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            self.assertFalse(hasattr(DeletionRepository, "retry"))
            self.assertFalse(hasattr(DeletionRepository, "reconcile"))
            self.assertFalse(hasattr(DeletionRepository, "resume_delete"))
        finally:
            await storage.close()

    async def test_retention_deleted_terminal_group_stays_absent_after_reopen(self):
        storage = await self.open()
        finished = await finish_delivery(storage)
        dialogue_before = await DialogueRepository(storage).get_live()
        await storage.close()
        storage = await self.open()
        try:
            result = await MetadataRetentionRepository(storage, now_ms=lambda: 604_801_000).sweep(limit=1)
            self.assertEqual(1, result.terminal_jobs_deleted)
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        storage = await self.open()
        try:
            self.assertIsNone(await TurnJobRepository(storage).get(finished.job.job_id))
            self.assertIsNone(await IngressUpdateRepository(storage).get(101))
            counts = await storage.read(lambda c: tuple(c.execute("SELECT (SELECT COUNT(*) FROM transient_payloads), (SELECT COUNT(*) FROM delivery_segments), (SELECT COUNT(*) FROM approvals)").fetchone()))
            self.assertEqual((0, 0, 0), counts)
            self.assertEqual(dialogue_before, await DialogueRepository(storage).get_live())
        finally:
            await storage.close()
