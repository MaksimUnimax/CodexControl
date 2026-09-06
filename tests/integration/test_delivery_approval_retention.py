import hashlib
import asyncio
import os
import sqlite3
import tempfile
import unittest

from codex_control.adapters.codex.approvals import ApprovalKind
from codex_control.storage import (
    ApprovalCallbackClaimStatus,
    ApprovalRepository,
    ApprovalState,
    CallbackActionRepository,
    DeliveryFinishOutcome,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliverySegmentRepository,
    DeliverySegmentState,
    DialogueRepository,
    RepositoryError,
    RepositoryErrorCategory,
    RetentionRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)


MAX_SQLITE_INT = 9223372036854775807


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class DeliveryApprovalRetentionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self):
        return await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def running_completed(self, storage, *, update=10, with_output=True):
        dialogue_repo = DialogueRepository(storage, now_ms=lambda: 2)
        dialogue_id = f"d-{update}"
        await dialogue_repo.create_intent(dialogue_id=dialogue_id, server_id="server", profile_id="profile")
        dialogue = await dialogue_repo.confirm_created(dialogue_id=dialogue_id, expected_version=0, thread_id="thread")
        jobs = TurnJobRepository(storage, now_ms=lambda: 3)
        claimed = await jobs.claim_ingress(
            update_id=update, job_id=f"job-{update}", source_chat_id=-100,
            source_message_id=update, dialogue_id=dialogue_id, server_id="server", profile_id="profile",
            thread_id="thread", model_id="model", reasoning_effort="high",
            input_payload_id=f"input-{update}", input_content=b"input", input_expires_at_ms=100,
        )
        execution = await jobs.claim_turn(job_id=claimed.job.job_id, expected_job_version=0,
                                          expected_dialogue_version=dialogue.version, thread_id="thread")
        starting = await jobs.mark_codex_starting(job_id=claimed.job.job_id,
                                                  expected_version=execution.job.version)
        running = await jobs.mark_codex_running(job_id=claimed.job.job_id,
                                                 expected_version=starting.version, codex_turn_id="turn")
        finished = await jobs.finish_codex(
            job_id=claimed.job.job_id, expected_job_version=running.version,
            expected_dialogue_version=execution.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
            **({"output_payload_id": f"output-{update}", "output_content": b"output",
                "output_expires_at_ms": 100} if with_output else {}),
        )
        return finished.job, finished.dialogue

    async def make_display(self, storage, job_id, payload_id="display", dialogue_id=None):
        return await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
            payload_id=payload_id, dialogue_id=dialogue_id or f"d-{job_id.split('-')[-1]}", job_id=job_id,
            kind=TransientPayloadKind.DISPLAY, content=b"display", expires_at_ms=100,
        )

    async def make_running(self, storage, update=20, existing_dialogue_id=None):
        dialogue_repo = DialogueRepository(storage, now_ms=lambda: 2)
        if existing_dialogue_id is None:
            await dialogue_repo.create_intent(dialogue_id=f"d-{update}", server_id="server", profile_id="profile")
            dialogue = await dialogue_repo.confirm_created(dialogue_id=f"d-{update}", expected_version=0,
                                                            thread_id="thread")
        else:
            dialogue = await dialogue_repo.get_live()
            assert dialogue is not None and dialogue.dialogue_id == existing_dialogue_id
        jobs = TurnJobRepository(storage, now_ms=lambda: 3)
        accepted = await jobs.claim_ingress(
            update_id=update, job_id=f"job-{update}", source_chat_id=-100, source_message_id=update,
            dialogue_id=dialogue.dialogue_id, server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id=f"input-{update}",
            input_content=b"input", input_expires_at_ms=100,
        )
        execution = await jobs.claim_turn(job_id=accepted.job.job_id, expected_job_version=0,
                                          expected_dialogue_version=dialogue.version, thread_id="thread")
        starting = await jobs.mark_codex_starting(job_id=accepted.job.job_id, expected_version=execution.job.version)
        running = await jobs.mark_codex_running(job_id=accepted.job.job_id, expected_version=starting.version,
                                                codex_turn_id="turn")
        return jobs, accepted.job, execution.dialogue, running

    async def test_plan_claim_finish_and_restart(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            planned = await repo.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=[DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),
                       DeliveryPlanItem(DeliveryOperation.EDIT, display.payload_id, 42)],
            )
            self.assertEqual(TurnJobState.DELIVERY_PENDING, planned.job.state)
            self.assertEqual((1, 2), tuple(x.sequence for x in planned.segments))
            claimed = await repo.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
            self.assertEqual((DeliverySegmentState.SENDING, 1),
                             (claimed.segment.state, claimed.segment.attempt_count))
            finished = await repo.finish_sending(
                job_id=job.job_id, sequence=1, expected_job_version=claimed.job.version,
                outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=101,
            )
            self.assertEqual(TurnJobState.DELIVERING, finished.job.state)
            claimed2 = await repo.claim_next(job_id=job.job_id, expected_job_version=finished.job.version)
            self.assertEqual(2, claimed2.segment.sequence)
            finished2 = await repo.finish_sending(
                job_id=job.job_id, sequence=2, expected_job_version=claimed2.job.version,
                outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=42,
            )
            self.assertEqual(TurnJobState.DELIVERED, finished2.job.state)
            await storage.close()
            storage = await self.open()
            self.assertEqual(finished2.segment, await DeliverySegmentRepository(storage).get(job.job_id, 2))
        finally:
            await storage.close()

    async def test_plan_accepts_exact_4096_segments(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=12)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            result = await repo.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=tuple(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None)
                            for _ in range(4096)),
            )
            self.assertEqual(4096, len(result.segments))
            self.assertEqual(4096, result.segments[-1].sequence)
        finally:
            await storage.close()

    async def test_unknown_is_terminal_and_never_retried(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            plan = await repo.plan(job_id=job.job_id, expected_job_version=job.version,
                                   items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),))
            claim = await repo.claim_next(job_id=job.job_id, expected_job_version=plan.job.version)
            unknown = await repo.finish_sending(job_id=job.job_id, sequence=1,
                                                expected_job_version=claim.job.version,
                                                outcome=DeliveryFinishOutcome.UNKNOWN, error_class="TELEGRAM_NETWORK_AMBIGUOUS")
            self.assertEqual((TurnJobState.DELIVERY_UNKNOWN, DeliverySegmentState.UNKNOWN),
                             (unknown.job.state, unknown.segment.state))
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_next(job_id=job.job_id, expected_job_version=unknown.job.version)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_concurrent_claims_and_callback_claims_have_one_winner(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=13)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            delivery = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            plan = await delivery.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=[DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None)],
            )
            claims = await asyncio.gather(
                delivery.claim_next(job_id=job.job_id, expected_job_version=plan.job.version),
                delivery.claim_next(job_id=job.job_id, expected_job_version=plan.job.version),
                return_exceptions=True,
            )
            self.assertEqual(1, sum(not isinstance(value, Exception) for value in claims))
            self.assertEqual(1, sum(isinstance(value, RepositoryError) for value in claims))

            jobs, running_job, running_dialogue, running = await self.make_running(
                storage, update=14, existing_dialogue_id=dialogue.dialogue_id
            )
            approvals = ApprovalRepository(storage, now_ms=lambda: 20)
            approval = await approvals.create_pending(
                approval_id="concurrent-approval", profile_id="profile", wire_request_id=14,
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=running_job.job_id,
                expected_job_version=running.version, expires_at_ms=100,
            )
            callback_token = token_hash("concurrent-callback")
            await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                token_hash_sha256=callback_token, action="approval_allow", subject_type="approval",
                subject_id=approval.approval_id, expected_version=running.version,
                expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=90,
            )
            results = await asyncio.gather(
                approvals.claim_callback(token_hash_sha256=callback_token, authorized_user_id=1,
                                         authorized_chat_id=-2),
                approvals.claim_callback(token_hash_sha256=callback_token, authorized_user_id=1,
                                         authorized_chat_id=-2),
            )
            self.assertEqual(1, sum(value.status is ApprovalCallbackClaimStatus.APPROVED for value in results))
            self.assertEqual(1, sum(value.status is ApprovalCallbackClaimStatus.ALREADY_CONSUMED for value in results))
            self.assertEqual(ApprovalState.APPROVED, (await approvals.get(approval.approval_id)).state)
        finally:
            await storage.close()

    async def test_plan_bounds_and_payload_coherence(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage)
            payload = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK")))
            for items in ([], [DeliveryPlanItem(DeliveryOperation.CREATE, payload.payload_id, None)] * 4097):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.plan(job_id=job.job_id, expected_job_version=job.version, items=items)
                self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            other_payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="other-display", dialogue_id=dialogue.dialogue_id,
                kind=TransientPayloadKind.DISPLAY, content=b"other", expires_at_ms=100,
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.plan(job_id=job.job_id, expected_job_version=job.version,
                                items=[DeliveryPlanItem(DeliveryOperation.CREATE, other_payload.payload_id, None)])
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_approval_wire_forms_reuse_and_atomic_callback(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage)
            approval_payload = await TransientPayloadRepository(storage, now_ms=lambda: 4).create(
                payload_id="approval-display", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                kind=TransientPayloadKind.APPROVAL, content=b"safe approval", expires_at_ms=100,
            )
            approvals = ApprovalRepository(storage, now_ms=lambda: 10)
            first = await approvals.create_pending(
                approval_id="approval-1", profile_id="profile", wire_request_id=7,
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                expected_job_version=running.version, display_payload_id=approval_payload.payload_id,
                expires_at_ms=50,
            )
            self.assertEqual(7, first.wire_request_id)
            callback = await CallbackActionRepository(storage, now_ms=lambda: 11).create(
                token_hash_sha256=token_hash("allow"), action="approval_allow", subject_type="approval",
                subject_id=first.approval_id, expected_version=running.version, expected_state="PENDING",
                authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=40,
            )
            claimed = await approvals.claim_callback(token_hash_sha256=callback.token_hash_sha256,
                                                     authorized_user_id=1, authorized_chat_id=-2)
            self.assertEqual(ApprovalCallbackClaimStatus.APPROVED, claimed.status)
            self.assertEqual(ApprovalState.APPROVED, claimed.record.state)
            reused = await approvals.create_pending(
                approval_id="approval-2", profile_id="profile", wire_request_id=7,
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=60,
            )
            self.assertEqual(7, reused.wire_request_id)
            string_form = await approvals.create_pending(
                approval_id="approval-3", profile_id="profile", wire_request_id="7",
                kind=ApprovalKind.FILE_CHANGE, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=60,
            )
            self.assertEqual("7", string_form.wire_request_id)
        finally:
            await storage.close()

    async def test_callback_privacy_stale_and_expiry(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage)
            approvals = ApprovalRepository(storage, now_ms=lambda: 20)
            pending = await approvals.create_pending(
                approval_id="approval", profile_id="profile", wire_request_id="wire",
                kind=ApprovalKind.EXEC_COMMAND, job_id=job.job_id, expected_job_version=running.version,
                expires_at_ms=30,
            )
            token = token_hash("private")
            await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                token_hash_sha256=token, action="approval_deny", subject_type="approval",
                subject_id=pending.approval_id, expected_version=running.version, expected_state="PENDING",
                authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=100,
            )
            wrong = await approvals.claim_callback(token_hash_sha256=token, authorized_user_id=9,
                                                   authorized_chat_id=-2)
            self.assertEqual(ApprovalCallbackClaimStatus.UNAUTHORIZED, wrong.status)
            self.assertIsNone(wrong.record)

            # A legitimate state/version change makes the callback stale. It is
            # consumed, while the approval remains pending.
            await jobs.finish_codex(job_id=job.job_id, expected_job_version=running.version,
                                    expected_dialogue_version=dialogue.version, outcome=TurnTerminalOutcome.FAILED,
                                    error_class="CODEX_TURN_FAILED")
            stale = await approvals.claim_callback(token_hash_sha256=token, authorized_user_id=1,
                                                   authorized_chat_id=-2)
            self.assertEqual(ApprovalCallbackClaimStatus.STALE, stale.status)
            replay = await approvals.claim_callback(token_hash_sha256=token, authorized_user_id=1,
                                                    authorized_chat_id=-2)
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)
            self.assertEqual(ApprovalState.PENDING, (await approvals.get(pending.approval_id)).state)
        finally:
            await storage.close()

    async def test_cancel_and_bounded_retention_protection(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage)
            approvals = ApprovalRepository(storage, now_ms=lambda: 20)
            pending = await approvals.create_pending(
                approval_id="pending", profile_id="profile", wire_request_id="wire",
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=100,
            )
            with self.assertRaises(RepositoryError) as raised:
                await approvals.cancel_pending_for_job(job.job_id)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            failed = await jobs.finish_codex(job_id=job.job_id, expected_job_version=running.version,
                                             expected_dialogue_version=dialogue.version,
                                             outcome=TurnTerminalOutcome.FAILED, error_class="CODEX_TURN_FAILED")
            cancelled = await approvals.cancel_pending_for_job(job.job_id)
            self.assertEqual((pending.approval_id, ApprovalState.CANCELLED),
                             (cancelled[0].approval_id, cancelled[0].state))

            # Expired unreferenced data is deleted, while a received input and
            # pending approval reference remain protected by the same bounded sweep.
            old = await TransientPayloadRepository(storage, now_ms=lambda: 1).create(
                payload_id="old", dialogue_id=dialogue.dialogue_id, kind=TransientPayloadKind.DISPLAY,
                content=b"old", expires_at_ms=2,
            )
            result = await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
            self.assertLessEqual(result.payloads_deleted, 1)
            self.assertIsNone(await TransientPayloadRepository(storage).get(old.payload_id))
            self.assertEqual(ApprovalState.CANCELLED, (await approvals.get(pending.approval_id)).state)
            self.assertEqual(failed.job.state, TurnJobState.FAILED)
        finally:
            await storage.close()

    async def test_retention_expires_due_approval_and_limit_input_validation(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=30)
            approvals = ApprovalRepository(storage, now_ms=lambda: 5)
            pending = await approvals.create_pending(
                approval_id="due", profile_id="profile", wire_request_id=1,
                kind=ApprovalKind.PERMISSIONS, job_id=job.job_id, expected_job_version=running.version,
                expires_at_ms=10,
            )
            with self.assertRaises(RepositoryError):
                await RetentionRepository(storage).sweep(0)
            with self.assertRaises(RepositoryError):
                await RetentionRepository(storage).sweep(1001)
            with self.assertRaises(RepositoryError):
                await RetentionRepository(storage).sweep(True)
            result = await RetentionRepository(storage, now_ms=lambda: 10).sweep(1000)
            self.assertEqual(1, result.approvals_expired)
            self.assertEqual(ApprovalState.EXPIRED, (await approvals.get(pending.approval_id)).state)
        finally:
            await storage.close()

    async def test_corrupt_delivery_shape_fails_closed_without_value(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage)
            payload = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            plan = await repo.plan(job_id=job.job_id, expected_job_version=job.version,
                                   items=[DeliveryPlanItem(DeliveryOperation.CREATE, payload.payload_id, None)])
            await storage.close()
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    "UPDATE delivery_segments SET state = 'CONFIRMED', confirmed_message_id = NULL WHERE job_id = ?",
                    (job.job_id,))
            storage = await self.open()
            repo = DeliverySegmentRepository(storage)
            with self.assertRaises(RepositoryError) as raised:
                await repo.get(job.job_id, 1)
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("CONFIRMED", repr(raised.exception))
            self.assertEqual(TurnJobState.DELIVERY_PENDING, plan.job.state)
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
