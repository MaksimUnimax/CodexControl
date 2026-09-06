import hashlib
import asyncio
import os
import sqlite3
import tempfile
import threading
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
MIN_SQLITE_INT = -9223372036854775808


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

    async def execute_write(self, storage, sql, parameters=()):
        def write(connection):
            connection.execute(sql, parameters)
        await storage.write(write)

    async def corrupt(self, storage, sql, parameters=()):
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(sql, parameters)
            connection.commit()
        return await self.open()

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

    async def test_global_delivery_job_shapes_and_pre_delivery_empty_lists(self):
        storage = await self.open()
        try:
            jobs, running_job, dialogue, running = await self.make_running(storage, update=40)
            delivery = DeliverySegmentRepository(storage)
            self.assertEqual((), await delivery.list_for_job(running_job.job_id))
            completed = await jobs.finish_codex(
                job_id=running_job.job_id, expected_job_version=running.version,
                expected_dialogue_version=dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
            )
            self.assertEqual((), await delivery.list_for_job(completed.job.job_id))

            def set_job_shape(connection, state, thread, codex_turn, error):
                connection.execute(
                    "UPDATE turn_jobs SET state = ?, thread_id = ?, codex_turn_id = ?, error_class = ?",
                    (state.value, thread, codex_turn, error),
                )

            invalid = (
                (TurnJobState.DELIVERY_PENDING, None, "turn", None),
                (TurnJobState.DELIVERY_PENDING, "thread", None, None),
                (TurnJobState.DELIVERING, "thread", "turn", "DELIVERY.error"),
                (TurnJobState.DELIVERED, "thread", None, None),
                (TurnJobState.DELIVERY_UNKNOWN, "thread", "turn", None),
                (TurnJobState.DELIVERY_UNKNOWN, "thread", "turn", "bad value"),
            )
            for state, thread, codex_turn, error in invalid:
                await storage.write(
                    lambda c, s=state, t=thread, ct=codex_turn, e=error:
                    set_job_shape(c, s, t, ct, e)
                )
                with self.assertRaises(RepositoryError) as raised:
                    await TurnJobRepository(storage).get(running_job.job_id)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn("bad value", repr(raised.exception))

            await storage.write(
                lambda c: set_job_shape(
                    c, TurnJobState.DELIVERY_UNKNOWN, "thread", "turn", "DELIVERY.unknown"
                )
            )
            self.assertEqual(
                TurnJobState.DELIVERY_UNKNOWN,
                (await TurnJobRepository(storage).get(running_job.job_id)).state,
            )
        finally:
            await storage.close()

    async def test_delivery_exact_reachable_patterns_and_read_fail_closed(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=43)
            display = await self.make_display(storage, job.job_id, payload_id="shape-display",
                                              dialogue_id=dialogue.dialogue_id)
            delivery = DeliverySegmentRepository(storage)

            async def seed(state, pattern):
                error = (
                    "DELIVERY.unknown" if state is TurnJobState.DELIVERY_UNKNOWN
                    else "DELIVERY.failed" if state is TurnJobState.FAILED else None
                )

                def write(connection):
                    connection.execute(
                        "UPDATE turn_jobs SET state = ?, thread_id = 'thread', "
                        "codex_turn_id = 'turn', error_class = ? WHERE job_id = ?",
                        (state.value, error, job.job_id),
                    )
                    connection.execute("DELETE FROM delivery_segments WHERE job_id = ?", (job.job_id,))
                    for sequence, segment_state in enumerate(pattern, 1):
                        attempt = 0 if segment_state is DeliverySegmentState.PENDING else 1
                        confirmed = (
                            None if segment_state is not DeliverySegmentState.CONFIRMED
                            else 100 + sequence
                        )
                        connection.execute(
                            "INSERT INTO delivery_segments "
                            "(job_id, sequence, operation, target_message_id, payload_id, "
                            "payload_sha256, state, attempt_count, confirmed_message_id, "
                            "created_at_ms, updated_at_ms) VALUES (?, ?, 'CREATE', NULL, ?, ?, ?, ?, ?, 1, 1)",
                            (job.job_id, sequence, display.payload_id, display.content_sha256,
                             segment_state.value, attempt, confirmed),
                        )

                await storage.write(write)

            canonical = (
                (TurnJobState.DELIVERY_PENDING, (DeliverySegmentState.PENDING,)),
                (TurnJobState.DELIVERY_PENDING,
                 (DeliverySegmentState.PENDING, DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.SENDING, DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.SENDING,
                  DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.UNKNOWN, DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.UNKNOWN,
                  DeliverySegmentState.PENDING)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.FAILED, DeliverySegmentState.PENDING)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.FAILED,
                  DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERED, (DeliverySegmentState.CONFIRMED,)),
                (TurnJobState.DELIVERED,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.CONFIRMED)),
            )
            for state, pattern in canonical:
                await seed(state, pattern)
                listed = await delivery.list_for_job(job.job_id)
                self.assertEqual(pattern, tuple(segment.state for segment in listed))
                self.assertEqual(listed[0], await delivery.get(job.job_id, 1))

            invalid = (
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.PENDING, DeliverySegmentState.PENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.PENDING, DeliverySegmentState.SENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.PENDING,
                  DeliverySegmentState.CONFIRMED)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.SENDING, DeliverySegmentState.SENDING)),
                (TurnJobState.DELIVERING,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.CONFIRMED)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.UNKNOWN, DeliverySegmentState.UNKNOWN)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.PENDING, DeliverySegmentState.UNKNOWN)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.UNKNOWN, DeliverySegmentState.CONFIRMED)),
                (TurnJobState.DELIVERY_UNKNOWN,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.UNKNOWN,
                  DeliverySegmentState.CONFIRMED)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.FAILED, DeliverySegmentState.FAILED)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.PENDING, DeliverySegmentState.FAILED)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.FAILED, DeliverySegmentState.CONFIRMED)),
                (TurnJobState.FAILED,
                 (DeliverySegmentState.CONFIRMED, DeliverySegmentState.FAILED,
                  DeliverySegmentState.CONFIRMED)),
            )
            for state, pattern in invalid:
                await seed(state, pattern)
                for read in (
                    lambda: delivery.list_for_job(job.job_id),
                    lambda: delivery.get(job.job_id, 1),
                ):
                    with self.assertRaises(RepositoryError) as raised:
                        await read()
                    self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            await seed(TurnJobState.DELIVERING,
                       (DeliverySegmentState.PENDING, DeliverySegmentState.PENDING))
            before = await storage.read(
                lambda c: tuple(tuple(row) for row in c.execute(
                    "SELECT turn_jobs.state, turn_jobs.version, delivery_segments.attempt_count FROM turn_jobs "
                    "JOIN delivery_segments USING (job_id) WHERE turn_jobs.job_id = ? "
                    "ORDER BY sequence",
                    (job.job_id,),
                ).fetchall())
            )
            clock_calls = []
            with self.assertRaises(RepositoryError) as raised:
                await DeliverySegmentRepository(
                    storage, now_ms=lambda: clock_calls.append(1) or 99
                ).claim_next(job_id=job.job_id, expected_job_version=job.version)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], clock_calls)
            after = await storage.read(
                lambda c: tuple(tuple(row) for row in c.execute(
                    "SELECT turn_jobs.state, turn_jobs.version, delivery_segments.attempt_count FROM turn_jobs "
                    "JOIN delivery_segments USING (job_id) WHERE turn_jobs.job_id = ? "
                    "ORDER BY sequence",
                    (job.job_id,),
                ).fetchall())
            )
            self.assertEqual(before, after)
        finally:
            await storage.close()

    async def test_duplicate_live_wire_corruption_fails_closed_everywhere(self):
        for index, (wire_type, wire_value) in enumerate((("INTEGER", 7), ("STRING", "7"))):
            self.path = os.path.join(self.tempdir.name, f"duplicate-live-{index}.sqlite3")
            storage = await self.open()
            try:
                jobs, job, dialogue, running = await self.make_running(storage, update=44 + index)
                await self.execute_write(
                    storage,
                    "INSERT INTO transient_payloads "
                    "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                    "created_at_ms, expires_at_ms) VALUES ('duplicate-retention-payload', ?, ?, 'DISPLAY', "
                    "?, ?, 3, 1, 2)",
                    (dialogue.dialogue_id, job.job_id, b"old", hashlib.sha256(b"old").hexdigest()),
                )
                wire_columns = (
                    (wire_value, None) if wire_type == "INTEGER" else (None, wire_value)
                )
                for approval_id in ("approval-A", "approval-B"):
                    await self.execute_write(
                        storage,
                        "INSERT INTO approvals "
                        "(approval_id, profile_id, wire_request_id_type, wire_request_id_int, "
                        "wire_request_id_text, job_id, kind, display_payload_id, state, created_at_ms, "
                        "updated_at_ms, expires_at_ms) VALUES (?, 'profile', ?, ?, ?, ?, 'permissions', "
                        "NULL, 'PENDING', 1, 1, 2)",
                        (approval_id, wire_type, wire_columns[0], wire_columns[1], job.job_id),
                    )

                approvals = ApprovalRepository(storage)
                for approval_id in ("approval-A", "approval-B"):
                    with self.assertRaises(RepositoryError) as raised:
                        await approvals.get(approval_id)
                    self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

                token = token_hash(f"duplicate-live-{index}")
                callback = await CallbackActionRepository(storage, now_ms=lambda: 3).create(
                    token_hash_sha256=token, action="approval_allow", subject_type="approval",
                    subject_id="approval-A", expected_version=running.version,
                    expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2,
                    expires_at_ms=100,
                )
                clock_calls = []
                with self.assertRaises(RepositoryError) as raised:
                    await ApprovalRepository(
                        storage, now_ms=lambda: clock_calls.append(1) or 4
                    ).claim_callback(
                        token_hash_sha256=callback.token_hash_sha256,
                        authorized_user_id=1, authorized_chat_id=-2,
                    )
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], clock_calls)
                durable = await storage.read(
                    lambda c: tuple(tuple(row) for row in c.execute(
                        "SELECT state FROM approvals WHERE approval_id IN ('approval-A', 'approval-B') "
                        "ORDER BY approval_id"
                    ).fetchall())
                )
                self.assertEqual(["PENDING", "PENDING"], [row[0] for row in durable])
                self.assertIsNone(await storage.read(
                    lambda c: c.execute(
                        "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
                        (callback.token_hash_sha256,),
                    ).fetchone()[0]
                ))

                with self.assertRaises(RepositoryError) as raised:
                    await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                durable = await storage.read(
                    lambda c: tuple(tuple(row) for row in c.execute(
                        "SELECT state FROM approvals WHERE approval_id IN ('approval-A', 'approval-B') "
                        "ORDER BY approval_id"
                    ).fetchall())
                )
                self.assertEqual(["PENDING", "PENDING"], [row[0] for row in durable])
                self.assertIsNotNone(await TransientPayloadRepository(storage).get(
                    "duplicate-retention-payload"
                ))

                await self.execute_write(
                    storage, "UPDATE approvals SET state = 'APPROVED' "
                    "WHERE approval_id IN ('approval-A', 'approval-B')"
                )
                current = await ApprovalRepository(storage, now_ms=lambda: 10).create_pending(
                    approval_id="approval-current", profile_id="profile", wire_request_id=wire_value,
                    kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                    expected_job_version=running.version, expires_at_ms=100,
                )
                await self.execute_write(
                    storage,
                    "INSERT INTO approvals "
                    "(approval_id, profile_id, wire_request_id_type, wire_request_id_int, "
                    "wire_request_id_text, job_id, kind, display_payload_id, state, created_at_ms, "
                    "updated_at_ms, expires_at_ms) VALUES ('approval-history', 'profile', ?, ?, ?, ?, "
                    "'permissions', NULL, 'DENIED', 1, 1, 2)",
                    (wire_type, wire_columns[0], wire_columns[1], job.job_id),
                )
                self.assertEqual(ApprovalState.PENDING, current.state)
                self.assertEqual(ApprovalState.PENDING,
                                 (await ApprovalRepository(storage).get("approval-current")).state)
                self.assertEqual(ApprovalState.DENIED,
                                 (await ApprovalRepository(storage).get("approval-history")).state)
                self.assertEqual(ApprovalState.APPROVED,
                                 (await ApprovalRepository(storage).get("approval-A")).state)
            finally:
                await storage.close()

    async def test_delivery_coherence_and_unknown_payload_authority(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=41)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            planned = await repo.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
            )
            claim = await repo.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
            unknown = await repo.finish_sending(
                job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                outcome=DeliveryFinishOutcome.UNKNOWN, error_class="TELEGRAM_NETWORK_AMBIGUOUS",
            )
            self.assertEqual(DeliverySegmentState.UNKNOWN, unknown.segment.state)
            self.assertIsNotNone(await TransientPayloadRepository(storage).get(display.payload_id))
            self.assertEqual(unknown.segment, await repo.get(job.job_id, 1))

            await self.execute_write(
                storage,
                "UPDATE delivery_segments SET payload_id = NULL WHERE job_id = ? AND sequence = 1",
                (job.job_id,),
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.get(job.job_id, 1)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_delivery_coherence_rejects_seeded_impossible_phases(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=42)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            planned = await repo.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
            )
            await self.execute_write(storage, "UPDATE turn_jobs SET state = 'DELIVERED' WHERE job_id = ?",
                                     (job.job_id,))
            with self.assertRaises(RepositoryError) as raised:
                await repo.list_for_job(job.job_id)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            await self.execute_write(
                storage,
                "UPDATE turn_jobs SET state = 'DELIVERY_UNKNOWN', error_class = 'DELIVERY.unknown' WHERE job_id = ?",
                (job.job_id,),
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.list_for_job(job.job_id)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            await self.execute_write(
                storage, "UPDATE turn_jobs SET state = 'DELIVERING', error_class = NULL WHERE job_id = ?",
                (job.job_id,),
            )
            await self.execute_write(
                storage,
                "UPDATE delivery_segments SET state = 'CONFIRMED', attempt_count = 1, "
                "confirmed_message_id = 99 WHERE job_id = ? AND sequence = 1",
                (job.job_id,),
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.list_for_job(job.job_id)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual(1, planned.segments[0].sequence)
        finally:
            await storage.close()

    async def test_approval_display_mismatch_vs_corruption_classification(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=50)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            raising = ApprovalRepository(
                storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
            )
            with self.assertRaises(RepositoryError) as raised:
                await raising.create_pending(
                    approval_id="wrong-kind", profile_id="profile", wire_request_id=1,
                    kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=display.payload_id,
                    expires_at_ms=100,
                )
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)

            other_payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="other-approval", dialogue_id=dialogue.dialogue_id,
                kind=TransientPayloadKind.APPROVAL, content=b"approval", expires_at_ms=100,
            )
            with self.assertRaises(RepositoryError) as raised:
                await raising.create_pending(
                    approval_id="wrong-owner", profile_id="profile", wire_request_id=2,
                    kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=other_payload.payload_id,
                    expires_at_ms=100,
                )
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)

            approval_payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="corrupt-approval", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                kind=TransientPayloadKind.APPROVAL, content=b"canonical", expires_at_ms=100,
            )
            await self.execute_write(
                storage, "UPDATE transient_payloads SET content_sha256 = ? WHERE payload_id = ?",
                ("0" * 64, approval_payload.payload_id),
            )
            with self.assertRaises(RepositoryError) as raised:
                await raising.create_pending(
                    approval_id="corrupt-hash", profile_id="profile", wire_request_id=3,
                    kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=approval_payload.payload_id,
                    expires_at_ms=100,
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("canonical", repr(raised.exception))

            content_payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="corrupt-content", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                kind=TransientPayloadKind.APPROVAL, content=b"content", expires_at_ms=100,
            )
            await self.execute_write(
                storage, "UPDATE transient_payloads SET content = ? WHERE payload_id = ?",
                (b"changed", content_payload.payload_id),
            )
            with self.assertRaises(RepositoryError) as raised:
                await raising.create_pending(
                    approval_id="corrupt-content-row", profile_id="profile", wire_request_id=4,
                    kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=content_payload.payload_id,
                    expires_at_ms=100,
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            owner_payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="corrupt-owner", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                kind=TransientPayloadKind.APPROVAL, content=b"owner", expires_at_ms=100,
            )
            storage = await self.corrupt(
                storage, "UPDATE transient_payloads SET dialogue_id = 'missing-dialogue' WHERE payload_id = ?",
                (owner_payload.payload_id,),
            )
            raising = ApprovalRepository(
                storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
            )
            with self.assertRaises(RepositoryError) as raised:
                await raising.create_pending(
                    approval_id="corrupt-owner-row", profile_id="profile", wire_request_id=5,
                    kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=owner_payload.payload_id,
                    expires_at_ms=100,
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_live_wire_duplicates_and_wire_id_boundaries(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=51)
            approvals = ApprovalRepository(storage, now_ms=lambda: 10)
            for wire_id, duplicate_id, kind in (
                (7, "duplicate-integer", ApprovalKind.COMMAND_EXECUTION),
                ("7", "duplicate-string", ApprovalKind.FILE_CHANGE),
            ):
                await approvals.create_pending(
                    approval_id=f"first-{duplicate_id}", profile_id="profile", wire_request_id=wire_id,
                    kind=kind, job_id=job.job_id, expected_job_version=running.version, expires_at_ms=100,
                )
                no_clock = ApprovalRepository(
                    storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
                )
                with self.assertRaises(RepositoryError) as raised:
                    await no_clock.create_pending(
                        approval_id=duplicate_id, profile_id="profile", wire_request_id=wire_id,
                        kind=kind, job_id=job.job_id, expected_job_version=running.version, expires_at_ms=100,
                    )
                self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)

            accepted = (MIN_SQLITE_INT, MAX_SQLITE_INT, "x", "x" * 256)
            for index, wire_id in enumerate(accepted):
                record = await approvals.create_pending(
                    approval_id=f"boundary-{index}", profile_id="profile", wire_request_id=wire_id,
                    kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                    expected_job_version=running.version, expires_at_ms=100,
                )
                self.assertEqual(wire_id, record.wire_request_id)
            self.assertNotEqual(
                (await approvals.get("first-duplicate-integer")).wire_request_id,
                (await approvals.get("first-duplicate-string")).wire_request_id,
            )
            invalid = (True, False, MIN_SQLITE_INT - 1, MAX_SQLITE_INT + 1, "", "x" * 257, "bad\x00id")
            for index, wire_id in enumerate(invalid):
                with self.assertRaises(RepositoryError) as raised:
                    await ApprovalRepository(
                        storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
                    ).create_pending(
                        approval_id=f"invalid-{index}", profile_id="profile", wire_request_id=wire_id,
                        kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                        expected_job_version=running.version, expires_at_ms=100,
                    )
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        finally:
            await storage.close()

    async def test_fresh_denied_and_callback_expiry_paths(self):
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=52)
            approvals = ApprovalRepository(storage, now_ms=lambda: 20)
            pending = await approvals.create_pending(
                approval_id="denied", profile_id="profile", wire_request_id=52,
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=100,
            )
            token = token_hash("deny")
            await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                token_hash_sha256=token, action="approval_deny", subject_type="approval",
                subject_id=pending.approval_id, expected_version=running.version,
                expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=90,
            )
            denied = await approvals.claim_callback(
                token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=-2
            )
            self.assertEqual(ApprovalCallbackClaimStatus.DENIED, denied.status)
            self.assertEqual(ApprovalState.DENIED, denied.record.state)
            self.assertEqual(ApprovalState.DENIED, (await approvals.get(pending.approval_id)).state)
            replay = await approvals.claim_callback(
                token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=-2
            )
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)

            due = await approvals.create_pending(
                approval_id="due-callback", profile_id="profile", wire_request_id=53,
                kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=25,
            )
            due_token = token_hash("due-callback")
            await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                token_hash_sha256=due_token, action="approval_allow", subject_type="approval",
                subject_id=due.approval_id, expected_version=running.version,
                expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=25,
            )
            expired = await ApprovalRepository(storage, now_ms=lambda: 25).claim_callback(
                token_hash_sha256=due_token, authorized_user_id=1, authorized_chat_id=-2
            )
            self.assertEqual(ApprovalCallbackClaimStatus.EXPIRED, expired.status)
            self.assertIsNone(expired.record)
            self.assertEqual(ApprovalState.EXPIRED, (await approvals.get(due.approval_id)).state)

            not_due = await approvals.create_pending(
                approval_id="callback-only-expiry", profile_id="profile", wire_request_id=54,
                kind=ApprovalKind.FILE_CHANGE, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=50,
            )
            not_due_token = token_hash("callback-only-expiry")
            await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                token_hash_sha256=not_due_token, action="approval_allow", subject_type="approval",
                subject_id=not_due.approval_id, expected_version=running.version,
                expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=25,
            )
            callback_expired = await ApprovalRepository(storage, now_ms=lambda: 25).claim_callback(
                token_hash_sha256=not_due_token, authorized_user_id=1, authorized_chat_id=-2
            )
            self.assertEqual(ApprovalCallbackClaimStatus.EXPIRED, callback_expired.status)
            self.assertEqual(ApprovalState.PENDING, (await approvals.get(not_due.approval_id)).state)
        finally:
            await storage.close()

    async def test_approval_privacy_precedes_consumed_expired_and_stale(self):
        for index, subject_setup in enumerate(("consumed", "expired", "stale")):
            self.path = os.path.join(self.tempdir.name, f"privacy-{index}.sqlite3")
            storage = await self.open()
            try:
                jobs, job, dialogue, running = await self.make_running(storage, update=60 + index)
                approvals = ApprovalRepository(storage, now_ms=lambda: 20)
                approval = await approvals.create_pending(
                    approval_id="privacy", profile_id="profile", wire_request_id=index + 60,
                    kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                    expected_job_version=running.version, expires_at_ms=30,
                )
                token = token_hash(f"privacy-{index}")
                callback_expiry = 25 if subject_setup == "expired" else 100
                await CallbackActionRepository(storage, now_ms=lambda: 21).create(
                    token_hash_sha256=token, action="approval_allow", subject_type="approval",
                    subject_id=approval.approval_id, expected_version=running.version,
                    expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2,
                    expires_at_ms=callback_expiry,
                )
                if subject_setup == "consumed":
                    result = await approvals.claim_callback(
                        token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=-2
                    )
                    self.assertEqual(ApprovalCallbackClaimStatus.APPROVED, result.status)
                elif subject_setup == "expired":
                    result = await ApprovalRepository(storage, now_ms=lambda: 25).claim_callback(
                        token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=-2
                    )
                    self.assertEqual(ApprovalCallbackClaimStatus.EXPIRED, result.status)
                else:
                    await jobs.finish_codex(
                        job_id=job.job_id, expected_job_version=running.version,
                        expected_dialogue_version=dialogue.version,
                        outcome=TurnTerminalOutcome.FAILED, error_class="CODEX.failed",
                    )

                for user_id, chat_id in ((9, -2), (1, -9)):
                    no_clock = ApprovalRepository(
                        storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
                    )
                    unauthorized = await no_clock.claim_callback(
                        token_hash_sha256=token, authorized_user_id=user_id,
                        authorized_chat_id=chat_id,
                    )
                    self.assertEqual(ApprovalCallbackClaimStatus.UNAUTHORIZED, unauthorized.status)
                    self.assertIsNone(unauthorized.record)
            finally:
                await storage.close()

    async def test_delivery_failed_edit_mismatch_and_no_clock_preconditions(self):
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=70)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            plan = await repo.plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=(DeliveryPlanItem(DeliveryOperation.EDIT, display.payload_id, 42),),
            )
            claim = await repo.claim_next(job_id=job.job_id, expected_job_version=plan.job.version)
            no_clock = DeliverySegmentRepository(
                storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
            )
            with self.assertRaises(RepositoryError) as raised:
                await no_clock.finish_sending(
                    job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                    outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=41,
                )
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            self.assertEqual(DeliverySegmentState.SENDING, (await repo.get(job.job_id, 1)).state)

            confirmed = await repo.finish_sending(
                job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=42,
            )
            self.assertEqual(TurnJobState.DELIVERED, confirmed.job.state)

            await storage.close()
            self.path = os.path.join(self.tempdir.name, "delivery-failed.sqlite3")
            storage = await self.open()
            repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
            failed_job, failed_dialogue = await self.running_completed(storage, update=71)
            failed_display = await self.make_display(
                storage, failed_job.job_id, payload_id="failed-display", dialogue_id=failed_dialogue.dialogue_id
            )
            failed_plan = await repo.plan(
                job_id=failed_job.job_id, expected_job_version=failed_job.version,
                items=(DeliveryPlanItem(DeliveryOperation.CREATE, failed_display.payload_id, None),),
            )
            failed_claim = await repo.claim_next(
                job_id=failed_job.job_id, expected_job_version=failed_plan.job.version
            )
            failed = await repo.finish_sending(
                job_id=failed_job.job_id, sequence=1, expected_job_version=failed_claim.job.version,
                outcome=DeliveryFinishOutcome.FAILED, error_class="TELEGRAM_PERMISSION",
            )
            self.assertEqual((TurnJobState.FAILED, DeliverySegmentState.FAILED),
                             (failed.job.state, failed.segment.state))
            self.assertEqual(1, failed.segment.attempt_count)
            self.assertEqual("TELEGRAM_PERMISSION", failed.job.error_class)
            self.assertEqual("IDLE", failed_dialogue.state.value)
            no_clock = DeliverySegmentRepository(
                storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
            )
            with self.assertRaises(RepositoryError) as raised:
                await no_clock.claim_next(job_id=failed_job.job_id, expected_job_version=failed.job.version)
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)

            # A stale expected version and a wrong job state fail before clock.
            with self.assertRaises(RepositoryError) as raised:
                await no_clock.claim_next(job_id=failed_job.job_id, expected_job_version=failed.job.version - 1)
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_delivery_version_overflow_fails_before_clock(self):
        for mode, update in (("plan", 80), ("claim", 81), ("finish", 82)):
            self.path = os.path.join(self.tempdir.name, f"overflow-{mode}.sqlite3")
            storage = await self.open()
            try:
                job, dialogue = await self.running_completed(storage, update=update)
                display = await self.make_display(
                    storage, job.job_id, payload_id=f"overflow-display-{mode}", dialogue_id=dialogue.dialogue_id
                )
                repo = DeliverySegmentRepository(storage, now_ms=lambda: 6)
                if mode == "plan":
                    # Restore a canonical completed job at the maximum version.
                    await self.execute_write(
                        storage, "UPDATE turn_jobs SET state = 'CODEX_COMPLETED', version = ? WHERE job_id = ?",
                        (MAX_SQLITE_INT, job.job_id),
                    )
                    expected = MAX_SQLITE_INT
                    call = lambda: repo.plan(
                        job_id=job.job_id, expected_job_version=expected,
                        items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
                    )
                elif mode == "claim":
                    plan = await repo.plan(
                        job_id=job.job_id, expected_job_version=job.version,
                        items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
                    )
                    await self.execute_write(
                        storage, "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (MAX_SQLITE_INT, job.job_id)
                    )
                    expected = MAX_SQLITE_INT
                    call = lambda: repo.claim_next(job_id=job.job_id, expected_job_version=expected)
                else:
                    plan = await repo.plan(
                        job_id=job.job_id, expected_job_version=job.version,
                        items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
                    )
                    claimed = await repo.claim_next(job_id=job.job_id, expected_job_version=plan.job.version)
                    await self.execute_write(
                        storage, "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (MAX_SQLITE_INT, job.job_id)
                    )
                    expected = MAX_SQLITE_INT
                    call = lambda: repo.finish_sending(
                        job_id=job.job_id, sequence=1, expected_job_version=expected,
                        outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=101,
                    )
                raising = DeliverySegmentRepository(
                    storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
                )
                if mode == "plan":
                    call = lambda: raising.plan(
                        job_id=job.job_id, expected_job_version=expected,
                        items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
                    )
                elif mode == "claim":
                    call = lambda: raising.claim_next(job_id=job.job_id, expected_job_version=expected)
                else:
                    call = lambda: raising.finish_sending(
                        job_id=job.job_id, sequence=1, expected_job_version=expected,
                        outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=101,
                    )
                with self.assertRaises(RepositoryError) as raised:
                    await call()
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertIsNotNone(await TransientPayloadRepository(storage).get(display.payload_id))
            finally:
                await storage.close()

    async def test_retention_input_and_output_protection_matrix(self):
        input_cases = (
            (TurnJobState.RECEIVED, True),
            (TurnJobState.CLAIMED, True),
            (TurnJobState.CODEX_STARTING, True),
            (TurnJobState.CODEX_RUNNING, True),
            (TurnJobState.FAILED, False),
        )
        for index, (state, retained) in enumerate(input_cases):
            self.path = os.path.join(self.tempdir.name, f"input-retention-{index}.sqlite3")
            storage = await self.open()
            try:
                _, created, dialogue, _ = await self.make_running(storage, update=100 + index)
                input_payload = await TransientPayloadRepository(storage).get_input_for_job(created.job_id)
                await self.execute_write(storage, "UPDATE turn_jobs SET state = ?, codex_turn_id = ?, "
                                           "error_class = ? WHERE job_id = ?", (
                    state.value, "turn" if state is TurnJobState.CODEX_RUNNING else None,
                    "CODEX.failed" if state is TurnJobState.FAILED else None, created.job_id,
                ))
                await self.execute_write(storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                                         (input_payload.payload_id,))
                result = await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
                self.assertEqual(retained, await TransientPayloadRepository(storage).get(
                    input_payload.payload_id
                ) is not None)
                self.assertEqual(created.job_id, (await TurnJobRepository(storage).get(created.job_id)).job_id)
            finally:
                await storage.close()

        output_cases = (
            (TurnJobState.CODEX_COMPLETED, True),
            (TurnJobState.DELIVERY_PENDING, True),
            (TurnJobState.DELIVERING, True),
            (TurnJobState.DELIVERY_UNKNOWN, True),
            (TurnJobState.DELIVERED, False),
        )
        for index, (state, retained) in enumerate(output_cases):
            self.path = os.path.join(self.tempdir.name, f"output-retention-{index}.sqlite3")
            storage = await self.open()
            try:
                job, dialogue = await self.running_completed(storage, update=120 + index)
                await self.execute_write(storage, "UPDATE turn_jobs SET state = ?, error_class = ? WHERE job_id = ?",
                                         (state.value, "DELIVERY.unknown" if state is TurnJobState.DELIVERY_UNKNOWN else None,
                                          job.job_id))
                await self.execute_write(storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                                         (f"output-{120 + index}",))
                await RetentionRepository(storage, now_ms=lambda: 10).sweep(1000)
                self.assertEqual(retained, await TransientPayloadRepository(storage).get(
                    f"output-{120 + index}"
                ) is not None)
                self.assertIsNotNone(await TurnJobRepository(storage).get(job.job_id))
            finally:
                await storage.close()

    async def test_retention_delivery_and_approval_reference_matrix(self):
        delivery_cases = (
            ("pending", DeliverySegmentState.PENDING),
            ("sending", DeliverySegmentState.SENDING),
            ("unknown", DeliverySegmentState.UNKNOWN),
            ("confirmed", DeliverySegmentState.CONFIRMED),
            ("failed", DeliverySegmentState.FAILED),
        )
        for index, (label, expected_state) in enumerate(delivery_cases):
            self.path = os.path.join(self.tempdir.name, f"display-retention-{index}.sqlite3")
            storage = await self.open()
            try:
                job, dialogue = await self.running_completed(storage, update=150 + index)
                display = await self.make_display(
                    storage, job.job_id, payload_id=f"display-{label}", dialogue_id=dialogue.dialogue_id
                )
                delivery = DeliverySegmentRepository(storage, now_ms=lambda: 6)
                planned = await delivery.plan(
                    job_id=job.job_id, expected_job_version=job.version,
                    items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
                )
                if expected_state is DeliverySegmentState.SENDING:
                    await delivery.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
                elif expected_state is DeliverySegmentState.UNKNOWN:
                    claim = await delivery.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
                    await delivery.finish_sending(
                        job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                        outcome=DeliveryFinishOutcome.UNKNOWN, error_class="TELEGRAM_NETWORK_AMBIGUOUS",
                    )
                elif expected_state is DeliverySegmentState.CONFIRMED:
                    claim = await delivery.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
                    await delivery.finish_sending(
                        job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                        outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=101,
                    )
                elif expected_state is DeliverySegmentState.FAILED:
                    claim = await delivery.claim_next(job_id=job.job_id, expected_job_version=planned.job.version)
                    await delivery.finish_sending(
                        job_id=job.job_id, sequence=1, expected_job_version=claim.job.version,
                        outcome=DeliveryFinishOutcome.FAILED, error_class="TELEGRAM_PERMISSION",
                    )
                await self.execute_write(
                    storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                    (display.payload_id,),
                )
                await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
                payload = await TransientPayloadRepository(storage).get(display.payload_id)
                if expected_state in (DeliverySegmentState.PENDING, DeliverySegmentState.SENDING,
                                       DeliverySegmentState.UNKNOWN):
                    self.assertIsNotNone(payload)
                else:
                    self.assertIsNone(payload)
                    segment = await delivery.get(job.job_id, 1)
                    self.assertEqual(expected_state, segment.state)
                    self.assertIsNone(segment.payload_id)
                self.assertIsNotNone(await TurnJobRepository(storage).get(job.job_id))
            finally:
                await storage.close()

        approval_cases = (ApprovalState.PENDING, ApprovalState.APPROVED, ApprovalState.DENIED,
                          ApprovalState.EXPIRED, ApprovalState.CANCELLED)
        for index, state in enumerate(approval_cases):
            self.path = os.path.join(self.tempdir.name, f"approval-retention-{index}.sqlite3")
            storage = await self.open()
            try:
                jobs, job, dialogue, running = await self.make_running(storage, update=170 + index)
                payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                    payload_id="approval-payload", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                    kind=TransientPayloadKind.APPROVAL, content=b"approval", expires_at_ms=100,
                )
                approvals = ApprovalRepository(storage, now_ms=lambda: 10)
                approval = await approvals.create_pending(
                    approval_id="retained-approval", profile_id="profile", wire_request_id=index + 170,
                    kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                    expected_job_version=running.version, display_payload_id=payload.payload_id,
                    expires_at_ms=200,
                )
                if state is not ApprovalState.PENDING:
                    await self.execute_write(
                        storage, "UPDATE approvals SET state = ? WHERE approval_id = ?",
                        (state.value, approval.approval_id),
                    )
                await self.execute_write(
                    storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                    (payload.payload_id,),
                )
                await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
                stored = await approvals.get(approval.approval_id)
                self.assertIsNotNone(stored)
                if state is ApprovalState.PENDING:
                    self.assertIsNotNone(await TransientPayloadRepository(storage).get(payload.payload_id))
                else:
                    self.assertIsNone(await TransientPayloadRepository(storage).get(payload.payload_id))
                    self.assertIsNone(stored.display_payload_id)
            finally:
                await storage.close()

    async def test_retention_starvation_and_one_clock_progress(self):
        for protection in ("job", "delivery", "approval"):
            self.path = os.path.join(self.tempdir.name, f"starvation-{protection}.sqlite3")
            storage = await self.open()
            try:
                if protection == "job":
                    _, created, dialogue, _ = await self.make_running(storage, update=190)
                    protected_id = (await TransientPayloadRepository(storage).get_input_for_job(
                        created.job_id
                    )).payload_id
                    await self.execute_write(
                        storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                        (protected_id,),
                    )
                    eligible = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                        payload_id="eligible", dialogue_id=dialogue.dialogue_id,
                        kind=TransientPayloadKind.DISPLAY, content=b"eligible", expires_at_ms=100,
                    )
                elif protection == "delivery":
                    job, dialogue = await self.running_completed(storage, update=191)
                    protected = await self.make_display(storage, job.job_id, payload_id="protected",
                                                        dialogue_id=dialogue.dialogue_id)
                    delivery = DeliverySegmentRepository(storage, now_ms=lambda: 6)
                    await delivery.plan(
                        job_id=job.job_id, expected_job_version=job.version,
                        items=(DeliveryPlanItem(DeliveryOperation.CREATE, protected.payload_id, None),),
                    )
                    eligible = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                        payload_id="eligible", dialogue_id=dialogue.dialogue_id,
                        kind=TransientPayloadKind.DISPLAY, content=b"eligible", expires_at_ms=100,
                    )
                    protected_id = protected.payload_id
                else:
                    jobs, job, dialogue, running = await self.make_running(storage, update=192)
                    protected = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                        payload_id="protected", dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                        kind=TransientPayloadKind.APPROVAL, content=b"protected", expires_at_ms=100,
                    )
                    approvals = ApprovalRepository(storage, now_ms=lambda: 10)
                    await approvals.create_pending(
                        approval_id="protecting-approval", profile_id="profile", wire_request_id=192,
                        kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                        expected_job_version=running.version, display_payload_id=protected.payload_id,
                        expires_at_ms=200,
                    )
                    eligible = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                        payload_id="eligible", dialogue_id=dialogue.dialogue_id,
                        kind=TransientPayloadKind.DISPLAY, content=b"eligible", expires_at_ms=100,
                    )
                    protected_id = protected.payload_id
                await self.execute_write(
                    storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = ?",
                    (protected_id,),
                )
                await self.execute_write(
                    storage, "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 3 WHERE payload_id = 'eligible'"
                )
                result = await RetentionRepository(storage, now_ms=lambda: 10).sweep(1)
                self.assertEqual(1, result.payloads_deleted)
                self.assertIsNotNone(await TransientPayloadRepository(storage).get(protected_id))
                self.assertIsNone(await TransientPayloadRepository(storage).get(eligible.payload_id))
            finally:
                await storage.close()

        self.path = os.path.join(self.tempdir.name, "one-clock.sqlite3")
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=193)
            approval = await ApprovalRepository(storage, now_ms=lambda: 5).create_pending(
                approval_id="due-one-clock", profile_id="profile", wire_request_id=193,
                kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=10,
            )
            payload = await TransientPayloadRepository(storage, now_ms=lambda: 5).create(
                payload_id="one-clock-payload", dialogue_id=dialogue.dialogue_id,
                kind=TransientPayloadKind.DISPLAY, content=b"old", expires_at_ms=10,
            )
            calls = []
            result = await RetentionRepository(storage, now_ms=lambda: calls.append(10) or 10).sweep(1)
            self.assertEqual((1, 1), (result.approvals_expired, result.payloads_deleted))
            self.assertEqual([10], calls)
            self.assertEqual(ApprovalState.EXPIRED, (await ApprovalRepository(storage).get(approval.approval_id)).state)
            self.assertIsNone(await TransientPayloadRepository(storage).get(payload.payload_id))
            for limit in (1, 1000):
                self.assertIsNotNone(await RetentionRepository(storage, now_ms=lambda: 10).sweep(limit))
            for invalid_limit in (0, 1001, True, False, 1.0):
                with self.assertRaises(RepositoryError) as raised:
                    await RetentionRepository(storage).sweep(invalid_limit)
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        finally:
            await storage.close()

    async def test_delivery_approval_retention_cancellation_stays_owned(self):
        async def cancel_after_clock(task, started, release):
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            for _ in range(3):
                task.cancel()
            release.set()
            return await task

        self.path = os.path.join(self.tempdir.name, "cancel-delivery.sqlite3")
        storage = await self.open()
        try:
            job, dialogue = await self.running_completed(storage, update=200)
            display = await self.make_display(storage, job.job_id, dialogue_id=dialogue.dialogue_id)
            plan = await DeliverySegmentRepository(storage, now_ms=lambda: 6).plan(
                job_id=job.job_id, expected_job_version=job.version,
                items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
            )
            started = threading.Event()
            release = threading.Event()

            def blocking_clock():
                started.set()
                release.wait(2)
                return 10

            delivery_task = asyncio.create_task(
                DeliverySegmentRepository(storage, now_ms=blocking_clock).claim_next(
                    job_id=job.job_id, expected_job_version=plan.job.version
                )
            )
            claimed = await cancel_after_clock(delivery_task, started, release)
            self.assertEqual(DeliverySegmentState.SENDING, claimed.segment.state)
            self.assertEqual(DeliverySegmentState.SENDING,
                             (await DeliverySegmentRepository(storage).get(job.job_id, 1)).state)
        finally:
            await storage.close()

        self.path = os.path.join(self.tempdir.name, "cancel-approval.sqlite3")
        storage = await self.open()
        try:
            jobs, job, dialogue, running = await self.make_running(storage, update=201)
            approval = await ApprovalRepository(storage, now_ms=lambda: 10).create_pending(
                approval_id="cancel-approval", profile_id="profile", wire_request_id=201,
                kind=ApprovalKind.PERMISSIONS, job_id=job.job_id,
                expected_job_version=running.version, expires_at_ms=100,
            )
            token = token_hash("cancel-approval")
            await CallbackActionRepository(storage, now_ms=lambda: 11).create(
                token_hash_sha256=token, action="approval_allow", subject_type="approval",
                subject_id=approval.approval_id, expected_version=running.version,
                expected_state="PENDING", authorized_user_id=1, authorized_chat_id=-2, expires_at_ms=90,
            )
            started = threading.Event()
            release = threading.Event()

            def blocking_clock():
                started.set()
                release.wait(2)
                return 20

            approval_task = asyncio.create_task(
                ApprovalRepository(storage, now_ms=blocking_clock).claim_callback(
                    token_hash_sha256=token, authorized_user_id=1, authorized_chat_id=-2
                )
            )
            result = await cancel_after_clock(approval_task, started, release)
            self.assertEqual(ApprovalCallbackClaimStatus.APPROVED, result.status)
            self.assertEqual(ApprovalState.APPROVED, (await ApprovalRepository(storage).get(approval.approval_id)).state)
        finally:
            await storage.close()

        self.path = os.path.join(self.tempdir.name, "cancel-retention.sqlite3")
        storage = await self.open()
        try:
            _, _, dialogue, _ = await self.make_running(storage, update=202)
            started = threading.Event()
            release = threading.Event()

            def blocking_clock():
                started.set()
                release.wait(2)
                return 20

            retention_task = asyncio.create_task(
                RetentionRepository(storage, now_ms=blocking_clock).sweep(1)
            )
            result = await cancel_after_clock(retention_task, started, release)
            self.assertEqual((0, 0), (result.approvals_expired, result.payloads_deleted))
            self.assertIsNotNone(await TurnJobRepository(storage).get("job-202"))
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
