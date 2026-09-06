"""P2.6b deterministic close/reopen acceptance matrix."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import *
from tests.acceptance.test_p2_6b_support import (
    DeterministicClock,
    TempDatabase,
    add_display_payload,
    create_completed,
    create_idle,
    create_received,
    create_running,
    finish_delivery,
    make_deleteable,
    make_approval,
    sha,
)


class P26bRestartMatrixTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = TempDatabase.create()

    def tearDown(self):
        self.db.cleanup()

    async def open(self, now: int = 1_000):
        return await SqliteStorage.open(self.db.path, now_ms=lambda: now)

    async def test_controller_control_restart_sleep_duplicate_and_stale(self):
        storage = await self.open()
        runtime = ControllerRuntimeRepository(storage, now_ms=lambda: 10)
        await runtime.begin_boot("fleet-1")
        applied = await ControlIngressRepository(storage, now_ms=lambda: 20).claim_control(
            update_id=10, control_epoch=10, requested_mode=ControllerMode.ACTIVE
        )
        self.assertEqual(ControlClaimStatus.APPLIED, applied.status)
        await storage.close()

        storage = await self.open()
        try:
            runtime = ControllerRuntimeRepository(storage, now_ms=lambda: 30)
            boot = await runtime.begin_boot("fleet-2")
            self.assertEqual(ControllerMode.ACTIVE, boot.record.requested_mode)
            self.assertEqual(10, boot.record.last_control_epoch)
            self.assertEqual(2, boot.record.boot_generation)
            self.assertEqual(ControllerMode.SLEEP, boot.effective_mode)
            control = ControlIngressRepository(storage, now_ms=lambda: 31)
            duplicate = await control.claim_control(
                update_id=10, control_epoch=11, requested_mode=ControllerMode.ACTIVE
            )
            self.assertEqual(ControlClaimStatus.DUPLICATE, duplicate.status)
            self.assertIsNone(duplicate.controller)
            stale = await control.claim_control(
                update_id=11, control_epoch=10, requested_mode=ControllerMode.ACTIVE
            )
            self.assertEqual(ControlClaimStatus.STALE, stale.status)
            self.assertEqual(10, stale.controller.last_control_epoch)
            self.assertEqual(ControllerMode.ACTIVE, stale.controller.requested_mode)
        finally:
            await storage.close()

    async def test_ignored_ingress_duplicate_preserves_original_disposition(self):
        storage = await self.open()
        try:
            first = await IngressUpdateRepository(storage, now_ms=lambda: 11).claim_ignored(
                update_id=12, disposition=IngressDispositionKind.IGNORED_SLEEP
            )
        finally:
            await storage.close()
        storage = await self.open()
        try:
            replay = await IngressUpdateRepository(storage, now_ms=lambda: 99).claim_ignored(
                update_id=12, disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED
            )
            self.assertTrue(replay.duplicate)
            self.assertEqual(IngressDispositionKind.IGNORED_SLEEP, replay.record.disposition)
            self.assertEqual(first.record, replay.record)
        finally:
            await storage.close()

    async def test_callback_fresh_consumed_expired_and_unauthorized_restart(self):
        async def callback_case(label: str, expires: int, claim_at: int | None):
            storage = await self.open()
            callbacks = CallbackActionRepository(storage, now_ms=lambda: 1_000)
            token = sha("callback-" + label)
            await callbacks.create(
                token_hash_sha256=token, action="approval_allow", subject_type="approval",
                subject_id="approval-" + label, expected_version=3, expected_state="PENDING",
                authorized_user_id=42, authorized_chat_id=-1001, expires_at_ms=expires,
            )
            await storage.close()
            storage = await self.open()
            try:
                if claim_at is not None:
                    result = await CallbackActionRepository(storage, now_ms=lambda: claim_at).claim(
                        token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
                    )
                    return token, result
                result = await CallbackActionRepository(storage, now_ms=lambda: 1_000).claim(
                    token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
                )
                return token, result
            finally:
                await storage.close()

        token, fresh = await callback_case("fresh", 2_000, 1_500)
        self.assertEqual(CallbackClaimStatus.CLAIMED, fresh.status)
        storage = await self.open()
        try:
            replay = await CallbackActionRepository(storage, now_ms=lambda: 1_500).claim(
                token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
            )
            self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, replay.status)
        finally:
            await storage.close()

        token, expired = await callback_case("expired", 2_000, 2_000)
        self.assertEqual(CallbackClaimStatus.EXPIRED, expired.status)
        storage = await self.open()
        try:
            replay = await CallbackActionRepository(storage, now_ms=lambda: 1_000).claim(
                token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
            )
            self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, replay.status)
            unauthorized = await CallbackActionRepository(storage, now_ms=lambda: 99_999).claim(
                token_hash_sha256=token, authorized_user_id=7, authorized_chat_id=-1001
            )
            self.assertEqual(CallbackClaimStatus.UNAUTHORIZED, unauthorized.status)
            self.assertIsNone(unauthorized.record)
        finally:
            await storage.close()

    async def test_dialogue_create_states_restart_without_synthesis(self):
        storage = await self.open()
        dialogue = DialogueRepository(storage, now_ms=lambda: 10)
        creating = await dialogue.create_intent(dialogue_id="d-create", server_id="server-1", profile_id="profile-1")
        await storage.close()
        storage = await self.open()
        try:
            dialogue = DialogueRepository(storage, now_ms=lambda: 20)
            self.assertEqual(creating, await dialogue.get_live())
            self.assertIsNone((await dialogue.get_live()).thread_id)
            with self.assertRaises(RepositoryError) as raised:
                await dialogue.create_intent(dialogue_id="d-create", server_id="server-1", profile_id="profile-1")
            self.assertEqual(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            idle = await dialogue.confirm_created(dialogue_id="d-create", expected_version=0, thread_id="thread-create")
            self.assertEqual(DialogueState.IDLE, idle.state)
            self.assertEqual("thread-create", idle.thread_id)
        finally:
            await storage.close()

        for method_name, expected_state in (("mark_create_unknown", DialogueState.CREATE_UNKNOWN), ("mark_create_error", DialogueState.ERROR)):
            db = TempDatabase.create()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            try:
                repo = DialogueRepository(storage, now_ms=lambda: 10)
                await repo.create_intent(dialogue_id="d-terminal", server_id="server-1", profile_id="profile-1")
                await storage.close()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                result = await getattr(DialogueRepository(storage, now_ms=lambda: 20), method_name)(
                    dialogue_id="d-terminal", expected_version=0, error_class="CODEX_PROCESS"
                )
                self.assertEqual(expected_state, result.state)
                await storage.close()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                persisted = await DialogueRepository(storage).get_live()
                self.assertEqual(result, persisted)
            finally:
                await storage.close()
                db.cleanup()

    async def test_turn_received_claimed_starting_running_and_rebind_block(self):
        storage = await self.open()
        received = await create_received(storage)
        await storage.close()
        storage = await self.open()
        try:
            jobs = TurnJobRepository(storage, now_ms=lambda: 20)
            duplicate = await jobs.claim_ingress(
                update_id=101, job_id="different-job", source_chat_id=-1002, source_message_id=999,
                dialogue_id="dialogue-1", server_id="other-server", profile_id="other-profile",
                thread_id="other-thread", model_id="other-model", reasoning_effort="low",
                input_payload_id="different-input", input_content=b"different-input", input_expires_at_ms=100_000,
            )
            self.assertEqual(TurnIngressClaimStatus.DUPLICATE, duplicate.status)
            self.assertEqual(received.job, duplicate.job)
            self.assertEqual(received.input_payload, duplicate.input_payload)
            with self.assertRaises(RepositoryError) as raised:
                await jobs.claim_ingress(
                    update_id=102, job_id="job-2", source_chat_id=-1001, source_message_id=202,
                    dialogue_id="dialogue-1", server_id="server-1", profile_id="profile-1", thread_id="thread-1",
                    model_id="model-test", reasoning_effort="medium", input_payload_id="input-2",
                    input_content=b"second", input_expires_at_ms=100_000,
                )
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            claimed = await jobs.claim_turn(job_id="job-1", expected_job_version=0, expected_dialogue_version=1, thread_id="thread-1")
        finally:
            await storage.close()
        storage = await self.open()
        try:
            jobs = TurnJobRepository(storage, now_ms=lambda: 30)
            job = await jobs.get("job-1")
            dialogue = await DialogueRepository(storage).get_live()
            self.assertEqual(TurnJobState.CLAIMED, job.state)
            self.assertEqual(DialogueState.TURN_RUNNING, dialogue.state)
            self.assertEqual("thread-1", job.thread_id)
            with self.assertRaises(RepositoryError) as raised:
                await jobs.claim_turn(job_id="job-1", expected_job_version=0, expected_dialogue_version=1, thread_id="thread-1")
            self.assertEqual(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            starting = await jobs.mark_codex_starting(job_id="job-1", expected_version=job.version)
        finally:
            await storage.close()
        storage = await self.open()
        try:
            jobs = TurnJobRepository(storage, now_ms=lambda: 40)
            starting = await jobs.get("job-1")
            self.assertEqual(TurnJobState.CODEX_STARTING, starting.state)
            self.assertIsNone(starting.codex_turn_id)
            running = await jobs.mark_codex_running(job_id="job-1", expected_version=starting.version, codex_turn_id="codex-turn-1")
        finally:
            await storage.close()
        storage = await self.open()
        try:
            jobs = TurnJobRepository(storage, now_ms=lambda: 50)
            running = await jobs.get("job-1")
            self.assertEqual(TurnJobState.CODEX_RUNNING, running.state)
            self.assertEqual("codex-turn-1", running.codex_turn_id)
            with self.assertRaises(RepositoryError) as raised:
                await jobs.mark_codex_running(job_id="job-1", expected_version=running.version, codex_turn_id="codex-turn-2")
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_terminal_turn_states_and_output_survive_restart(self):
        storage = await self.open()
        running = await create_running(storage)
        completed = await TurnJobRepository(storage, now_ms=lambda: 20).finish_codex(
            job_id=running.job_id, expected_job_version=running.version, expected_dialogue_version=2,
            outcome=TurnTerminalOutcome.COMPLETED, output_payload_id="output-final", output_content=b"final-output",
            output_expires_at_ms=100_000,
        )
        await storage.close()
        storage = await self.open()
        try:
            self.assertEqual(TurnJobState.CODEX_COMPLETED, (await TurnJobRepository(storage).get("job-1")).state)
            output = await TransientPayloadRepository(storage).get("output-final")
            self.assertEqual(b"final-output", output.content)
            self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)
        finally:
            await storage.close()

        for outcome, job_state, dialogue_state in ((TurnTerminalOutcome.FAILED, TurnJobState.FAILED, DialogueState.ERROR), (TurnTerminalOutcome.UNKNOWN, TurnJobState.UNKNOWN, DialogueState.TURN_UNKNOWN)):
            db = TempDatabase.create()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            try:
                running = await create_running(storage)
                await TurnJobRepository(storage, now_ms=lambda: 20).finish_codex(
                    job_id=running.job_id, expected_job_version=running.version, expected_dialogue_version=2,
                    outcome=outcome, error_class="CODEX_AMBIGUOUS",
                )
                await storage.close()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                self.assertEqual(job_state, (await TurnJobRepository(storage).get("job-1")).state)
                dialogue = await DialogueRepository(storage).get_live()
                self.assertEqual(dialogue_state, dialogue.state)
                self.assertEqual("CODEX_AMBIGUOUS", dialogue.last_error_class)
            finally:
                await storage.close()
                db.cleanup()

    async def test_delivery_plan_sending_resume_unknown_and_terminals_restart(self):
        storage = await self.open()
        completed = await create_completed(storage)
        await add_display_payload(storage)
        delivery = DeliverySegmentRepository(storage, now_ms=lambda: 20)
        planned = await delivery.plan(job_id=completed.job.job_id, expected_job_version=completed.job.version, items=[DeliveryPlanItem(DeliveryOperation.CREATE, "display-1", None), DeliveryPlanItem(DeliveryOperation.EDIT, "display-1", 800)])
        await storage.close()
        storage = await self.open()
        try:
            job = await TurnJobRepository(storage).get("job-1")
            segments = await DeliverySegmentRepository(storage).list_for_job("job-1")
            self.assertEqual(TurnJobState.DELIVERY_PENDING, job.state)
            self.assertEqual((DeliverySegmentState.PENDING, DeliverySegmentState.PENDING), tuple(x.state for x in segments))
            claim = await DeliverySegmentRepository(storage, now_ms=lambda: 30).claim_next(job_id="job-1", expected_job_version=job.version)
        finally:
            await storage.close()
        storage = await self.open()
        try:
            job = await TurnJobRepository(storage).get("job-1")
            segment = await DeliverySegmentRepository(storage).get("job-1", 1)
            self.assertEqual(TurnJobState.DELIVERING, job.state)
            self.assertEqual((DeliverySegmentState.SENDING, 1), (segment.state, segment.attempt_count))
            with self.assertRaises(RepositoryError) as raised:
                await DeliverySegmentRepository(storage).claim_next(job_id="job-1", expected_job_version=job.version)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            confirmed = await DeliverySegmentRepository(storage, now_ms=lambda: 40).finish_sending(job_id="job-1", sequence=1, expected_job_version=job.version, outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=900)
        finally:
            await storage.close()
        storage = await self.open()
        try:
            job = await TurnJobRepository(storage).get("job-1")
            segments = await DeliverySegmentRepository(storage).list_for_job("job-1")
            self.assertEqual((DeliverySegmentState.CONFIRMED, DeliverySegmentState.PENDING), tuple(x.state for x in segments))
            next_claim = await DeliverySegmentRepository(storage, now_ms=lambda: 50).claim_next(job_id="job-1", expected_job_version=job.version)
            self.assertEqual(2, next_claim.segment.sequence)
            self.assertEqual(1, next_claim.segment.attempt_count)
        finally:
            await storage.close()

        for outcome, expected_job, expected_segment in ((DeliveryFinishOutcome.CONFIRMED, TurnJobState.DELIVERED, DeliverySegmentState.CONFIRMED), (DeliveryFinishOutcome.FAILED, TurnJobState.FAILED, DeliverySegmentState.FAILED)):
            db = TempDatabase.create()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            try:
                finished = await finish_delivery(storage, outcome=outcome)
                await storage.close()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                job = await TurnJobRepository(storage).get("job-1")
                segment = await DeliverySegmentRepository(storage).get("job-1", 1)
                self.assertEqual(expected_job, job.state)
                self.assertEqual(expected_segment, segment.state)
                self.assertEqual(1, segment.attempt_count)
            finally:
                await storage.close()
                db.cleanup()

    async def test_delivery_unknown_restart_has_no_retry(self):
        storage = await self.open()
        finished = await finish_delivery(storage, outcome=DeliveryFinishOutcome.UNKNOWN)
        await storage.close()
        storage = await self.open()
        try:
            job = await TurnJobRepository(storage).get("job-1")
            segment = await DeliverySegmentRepository(storage).get("job-1", 1)
            self.assertEqual(TurnJobState.DELIVERY_UNKNOWN, job.state)
            self.assertEqual((DeliverySegmentState.UNKNOWN, 1), (segment.state, segment.attempt_count))
            with self.assertRaises(RepositoryError) as raised:
                await DeliverySegmentRepository(storage).claim_next(job_id="job-1", expected_job_version=job.version)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_approval_pending_allow_deny_stale_and_expired_restart(self):
        storage = await self.open()
        approval, token = await make_approval(storage, token_label="allow")
        await storage.close()
        storage = await self.open()
        try:
            persisted = await ApprovalRepository(storage).get(approval.approval_id)
            self.assertEqual(approval, persisted)
            claimed = await ApprovalRepository(storage, now_ms=lambda: 1_500).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.APPROVED, claimed.status)
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        storage = await self.open()
        try:
            self.assertEqual(ApprovalState.APPROVED, (await ApprovalRepository(storage).get(approval.approval_id)).state)
            replay = await ApprovalRepository(storage).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)
        finally:
            await storage.close()

        for action, status, state in (("deny", ApprovalCallbackClaimStatus.DENIED, ApprovalState.DENIED), ("expired", ApprovalCallbackClaimStatus.EXPIRED, ApprovalState.EXPIRED)):
            db = TempDatabase.create()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            try:
                approval, token = await make_approval(storage, approval_id="approval-" + action, token_label=action, expires_at_ms=2_000)
                if action == "expired":
                    result = await ApprovalRepository(storage, now_ms=lambda: 2_000).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
                else:
                    await storage.write(lambda c: (c.execute("UPDATE callback_actions SET action='approval_deny' WHERE token_hash_sha256=?", (token,)), None)[1])
                    result = await ApprovalRepository(storage, now_ms=lambda: 1_500).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
                self.assertEqual(status, result.status)
                await storage.close()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                self.assertEqual(state, (await ApprovalRepository(storage).get(approval.approval_id)).state)
                replay = await ApprovalRepository(storage).claim_callback(token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001)
                self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)
            finally:
                await storage.close()
                db.cleanup()

        db = TempDatabase.create()
        storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
        try:
            approval, token = await make_approval(storage, approval_id="approval-stale", token_label="stale")
            await TurnJobRepository(storage, now_ms=lambda: 2).finish_codex(
                job_id="job-1", expected_job_version=3, expected_dialogue_version=2,
                outcome=TurnTerminalOutcome.COMPLETED,
            )
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            result = await ApprovalRepository(storage, now_ms=lambda: 2).claim_callback(
                token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
            )
            self.assertEqual(ApprovalCallbackClaimStatus.STALE, result.status)
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            self.assertEqual(ApprovalState.PENDING, (await ApprovalRepository(storage).get(approval.approval_id)).state)
            self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, (await ApprovalRepository(storage).claim_callback(
                token_hash_sha256=token, authorized_user_id=42, authorized_chat_id=-1001
            )).status)
        finally:
            await storage.close()
            db.cleanup()

    async def test_delete_pending_deleting_unknown_and_confirmed_finalization_restart(self):
        storage = await self.open()
        dialogue, deletion = await make_deleteable(storage)
        pending = await DeletionRepository(storage, now_ms=lambda: 20).claim_delete_intent(dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version)
        await storage.close()
        storage = await self.open()
        try:
            persisted = await DialogueRepository(storage).get_live()
            self.assertEqual(DialogueState.DELETE_PENDING, persisted.state)
            self.assertEqual("profile-1", persisted.profile_id)
            self.assertEqual("thread-1", persisted.thread_id)
            deleting = await DeletionRepository(storage, now_ms=lambda: 30).claim_deleting(dialogue_id="dialogue-1", expected_version=persisted.version)
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        storage = await self.open()
        try:
            persisted = await DialogueRepository(storage).get_live()
            self.assertEqual(DialogueState.DELETING, persisted.state)
            self.assertEqual("profile-1", persisted.profile_id)
            self.assertEqual("thread-1", persisted.thread_id)
            unknown = await DeletionRepository(storage, now_ms=lambda: 40).mark_delete_unknown(dialogue_id="dialogue-1", expected_version=persisted.version, error_class="CODEX_AMBIGUOUS")
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        storage = await self.open()
        try:
            persisted = await DialogueRepository(storage).get_live()
            self.assertEqual(DialogueState.DELETE_UNKNOWN, persisted.state)
            self.assertEqual("profile-1", persisted.profile_id)
            self.assertEqual("thread-1", persisted.thread_id)
            self.assertEqual("CODEX_AMBIGUOUS", persisted.last_error_class)
            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage).claim_deleting(dialogue_id="dialogue-1", expected_version=persisted.version)
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

        db = TempDatabase.create()
        storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
        try:
            running = await create_running(storage)
            approval = await ApprovalRepository(storage, now_ms=lambda: 4).create_pending(
                approval_id="approval-delete", profile_id="profile-1", wire_request_id=77,
                kind=ApprovalKind.COMMAND_EXECUTION, job_id=running.job_id,
                expected_job_version=running.version, expires_at_ms=50_000,
            )
            completed = await TurnJobRepository(storage, now_ms=lambda: 5).finish_codex(
                job_id=running.job_id, expected_job_version=running.version,
                expected_dialogue_version=2, outcome=TurnTerminalOutcome.COMPLETED,
            )
            await ApprovalRepository(storage, now_ms=lambda: 6).cancel_pending_for_job(running.job_id)
            await add_display_payload(storage)
            planned = await DeliverySegmentRepository(storage, now_ms=lambda: 7).plan(
                job_id=running.job_id, expected_job_version=completed.job.version,
                items=[DeliveryPlanItem(DeliveryOperation.CREATE, "display-1", None)],
            )
            claimed = await DeliverySegmentRepository(storage, now_ms=lambda: 8).claim_next(
                job_id=running.job_id, expected_job_version=planned.job.version,
            )
            await DeliverySegmentRepository(storage, now_ms=lambda: 9).finish_sending(
                job_id=running.job_id, sequence=1, expected_job_version=claimed.job.version,
                outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=901,
            )
            dialogue = await DialogueRepository(storage).get_live()
            old_ingress = await IngressUpdateRepository(storage).get(101)
            self.assertIsNotNone(old_ingress)
            self.assertEqual(IngressDispositionKind.JOB, old_ingress.disposition)
            self.assertEqual(running.job_id, old_ingress.job_id)

            callback_hash = sha("delete-retained-callback")
            await CallbackActionRepository(storage, now_ms=lambda: 9).create(
                token_hash_sha256=callback_hash,
                action="retained_callback",
                subject_type="dialogue",
                subject_id=dialogue.dialogue_id,
                expected_version=dialogue.version,
                expected_state=dialogue.state.value,
                authorized_user_id=42,
                authorized_chat_id=-1001,
                expires_at_ms=50_000,
            )
            callback_claim = await CallbackActionRepository(storage, now_ms=lambda: 9).claim(
                token_hash_sha256=callback_hash,
                authorized_user_id=42,
                authorized_chat_id=-1001,
            )
            self.assertEqual(CallbackClaimStatus.CLAIMED, callback_claim.status)

            error_fingerprint = sha("delete-retained-error")
            retained_error = await ErrorFingerprintRepository(storage, now_ms=lambda: 9).record(
                fingerprint_sha256=error_fingerprint,
                error_class="CODEX_PROCESS",
                dialogue_id=dialogue.dialogue_id,
                job_id=running.job_id,
            )
            pending = await DeletionRepository(storage, now_ms=lambda: 10).claim_delete_intent(dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version)
            deleting = await DeletionRepository(storage, now_ms=lambda: 11).claim_deleting(dialogue_id=dialogue.dialogue_id, expected_version=pending.version)
            final = await DeletionRepository(storage, now_ms=lambda: 12).finalize_confirmed(dialogue_id=dialogue.dialogue_id, expected_version=deleting.version, tombstone_expires_at_ms=100_000)
            await storage.close()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            self.assertIsNone(await DialogueRepository(storage).get_live())
            tombstone = await DeletionRepository(storage).get_tombstone(dialogue.dialogue_id)
            self.assertEqual(final.tombstone, tombstone)
            self.assertNotIn("thread-1", repr(tombstone))
            self.assertEqual(old_ingress, await IngressUpdateRepository(storage).get(101))
            counts = await storage.read(lambda c: tuple(c.execute("SELECT (SELECT COUNT(*) FROM turn_jobs), (SELECT COUNT(*) FROM transient_payloads), (SELECT COUNT(*) FROM delivery_segments), (SELECT COUNT(*) FROM approvals)").fetchone()))
            self.assertEqual((0, 0, 0, 0), counts)
            self.assertEqual((1, 2, 1, 1), (final.purged_jobs, final.purged_payloads, final.purged_delivery_segments, final.purged_approvals))
            callback_replay = await CallbackActionRepository(storage).claim(
                token_hash_sha256=callback_hash,
                authorized_user_id=42,
                authorized_chat_id=-1001,
            )
            self.assertEqual(CallbackClaimStatus.ALREADY_CONSUMED, callback_replay.status)
            persisted_error = await ErrorFingerprintRepository(storage).get(error_fingerprint)
            self.assertEqual(
                ErrorFingerprintRecord(
                    retained_error.fingerprint_sha256,
                    retained_error.error_class,
                    retained_error.count,
                    retained_error.first_seen_at_ms,
                    retained_error.last_seen_at_ms,
                    None,
                    None,
                ),
                persisted_error,
            )
        finally:
            await storage.close()
            db.cleanup()

    async def test_metadata_retention_and_error_fingerprint_restart(self):
        storage = await self.open()
        received = await create_received(storage)
        await IngressUpdateRepository(storage, now_ms=lambda: 1).claim_ignored(update_id=300, disposition=IngressDispositionKind.IGNORED_SLEEP)
        await IngressUpdateRepository(storage, now_ms=lambda: 2).claim_ignored(update_id=301, disposition=IngressDispositionKind.IGNORED_SLEEP)
        await storage.close()
        storage = await self.open()
        try:
            retention = MetadataRetentionRepository(storage, now_ms=lambda: 604_801_000)
            result = await retention.sweep(limit=1)
            self.assertGreaterEqual(result.ingress_deleted, 1)
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()
        storage = await self.open()
        try:
            remaining = await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates WHERE update_id=301").fetchone()[0])
            self.assertEqual(1, remaining)
            second_sweep = await MetadataRetentionRepository(storage, now_ms=lambda: 604_802_000).sweep(limit=1)
            self.assertGreaterEqual(second_sweep.ingress_deleted, 1)
            self.assertEqual(0, await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates WHERE update_id=301").fetchone()[0]))
            await storage.close()
        finally:
            if repr(storage).endswith("open>"):
                await storage.close()

        fingerprint = sha("error-restart-count")
        first_storage = await self.open()
        try:
            first = await ErrorFingerprintRepository(first_storage, now_ms=lambda: 604_803_001).record(
                fingerprint_sha256=fingerprint,
                error_class="CODEX_PROCESS",
                dialogue_id=received.job.dialogue_id,
                job_id=received.job.job_id,
            )
        finally:
            await first_storage.close()

        second_storage = await self.open()
        try:
            second = await ErrorFingerprintRepository(second_storage, now_ms=lambda: 604_804_000).record(
                fingerprint_sha256=fingerprint,
                error_class="CODEX_PROCESS",
                dialogue_id=received.job.dialogue_id,
                job_id=received.job.job_id,
            )
            self.assertEqual(2, second.count)
            self.assertEqual(first.first_seen_at_ms, second.first_seen_at_ms)
            self.assertGreaterEqual(second.last_seen_at_ms, first.last_seen_at_ms)
            self.assertEqual(first.error_class, second.error_class)
            self.assertEqual(first.dialogue_id, second.dialogue_id)
            self.assertEqual(first.job_id, second.job_id)
        finally:
            await second_storage.close()

        final_storage = await self.open()
        try:
            final = await ErrorFingerprintRepository(final_storage).get(fingerprint)
            self.assertEqual(second, final)
        finally:
            await final_storage.close()

    async def test_representative_corruption_fails_closed_and_redacts_values(self):
        cases = (
            ("UPDATE controller_runtime SET boot_generation=1.5", "1.5", ControllerRuntimeRepository, "get"),
            ("UPDATE turn_jobs SET error_class='PRIVATE_RAW_JOB_VALUE' WHERE job_id='job-1'", "PRIVATE_RAW_JOB_VALUE", TurnJobRepository, "get"),
            ("INSERT INTO deletion_tombstones VALUES ('d-tomb', '" + "A" * 64 + "', 1, 2, 2)", "A" * 64, DeletionRepository, "get_tombstone"),
            ("INSERT INTO errors VALUES ('" + "a" * 64 + "', 'PRIVATE_RAW_ERROR_VALUE WITH SPACE', 1, 1, 1, NULL, NULL)", "PRIVATE_RAW_ERROR_VALUE WITH SPACE", ErrorFingerprintRepository, "get"),
        )
        for index, (sql, raw_value, repo_type, method) in enumerate(cases):
            db = TempDatabase.create()
            storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
            try:
                if index == 0:
                    await ControllerRuntimeRepository(storage, now_ms=lambda: 1).begin_boot("fleet-1")
                if index == 1:
                    await create_received(storage)
                await storage.close()
                with sqlite3.connect(db.path) as connection:
                    connection.execute("PRAGMA foreign_keys=OFF")
                    connection.execute(sql)
                    connection.commit()
                storage = await SqliteStorage.open(db.path, now_ms=lambda: 1)
                with self.assertRaises(RepositoryError) as raised:
                    if index == 0:
                        await repo_type(storage).get()
                    elif index == 1:
                        await repo_type(storage).get("job-1")
                    elif index == 2:
                        await repo_type(storage).get_tombstone("d-tomb")
                    else:
                        await repo_type(storage).get("a" * 64)
                self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn(raw_value, str(raised.exception))
                self.assertNotIn(raw_value, repr(raised.exception))
            finally:
                await storage.close()
                db.cleanup()
