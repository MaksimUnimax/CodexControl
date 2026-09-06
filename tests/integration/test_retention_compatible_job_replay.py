"""Focused P2.C1 proof for retention-compatible JOB duplicate replay."""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest

from codex_control.storage import (
    DeliveryFinishOutcome,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliverySegmentRepository,
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    RetentionRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnIngressClaimStatus,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)


class RetentionCompatibleJobReplayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "state.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self):
        return await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def make_job(self, storage, state: TurnJobState = TurnJobState.CODEX_COMPLETED):
        dialogue_repo = DialogueRepository(storage, now_ms=lambda: 2)
        creating = await dialogue_repo.create_intent(
            dialogue_id="dialogue", server_id="server", profile_id="profile"
        )
        dialogue = await dialogue_repo.confirm_created(
            dialogue_id=creating.dialogue_id, expected_version=creating.version, thread_id="thread"
        )
        jobs = TurnJobRepository(storage, now_ms=lambda: 3)
        created = await jobs.claim_ingress(
            update_id=101,
            job_id="job",
            source_chat_id=-100,
            source_message_id=202,
            dialogue_id=dialogue.dialogue_id,
            server_id=dialogue.server_id,
            profile_id=dialogue.profile_id,
            thread_id=dialogue.thread_id,
            model_id="model",
            reasoning_effort="high",
            input_payload_id="input",
            input_content=b"canonical-input",
            input_expires_at_ms=100,
        )
        if state is TurnJobState.RECEIVED:
            return jobs, created.job, dialogue
        execution = await jobs.claim_turn(
            job_id=created.job.job_id,
            expected_job_version=created.job.version,
            expected_dialogue_version=dialogue.version,
            thread_id="thread",
        )
        if state is TurnJobState.CLAIMED:
            return jobs, execution.job, execution.dialogue
        starting = await jobs.mark_codex_starting(
            job_id=created.job.job_id, expected_version=execution.job.version
        )
        if state is TurnJobState.CODEX_STARTING:
            return jobs, starting, execution.dialogue
        running = await jobs.mark_codex_running(
            job_id=created.job.job_id,
            expected_version=starting.version,
            codex_turn_id="turn",
        )
        if state is TurnJobState.CODEX_RUNNING:
            return jobs, running, execution.dialogue
        if state is TurnJobState.CODEX_COMPLETED:
            finished = await jobs.finish_codex(
                job_id=created.job.job_id,
                expected_job_version=running.version,
                expected_dialogue_version=execution.dialogue.version,
                outcome=TurnTerminalOutcome.COMPLETED,
            )
            return jobs, finished.job, finished.dialogue
        if state is TurnJobState.FAILED:
            finished = await jobs.finish_codex(
                job_id=created.job.job_id,
                expected_job_version=running.version,
                expected_dialogue_version=execution.dialogue.version,
                outcome=TurnTerminalOutcome.FAILED,
                error_class="CODEX.failed",
            )
            return jobs, finished.job, finished.dialogue
        if state is TurnJobState.UNKNOWN:
            finished = await jobs.finish_codex(
                job_id=created.job.job_id,
                expected_job_version=running.version,
                expected_dialogue_version=execution.dialogue.version,
                outcome=TurnTerminalOutcome.UNKNOWN,
                error_class="CODEX.unknown",
            )
            return jobs, finished.job, finished.dialogue

        finished = await jobs.finish_codex(
            job_id=created.job.job_id,
            expected_job_version=running.version,
            expected_dialogue_version=execution.dialogue.version,
            outcome=TurnTerminalOutcome.COMPLETED,
        )
        display = await TransientPayloadRepository(storage, now_ms=lambda: 4).create(
            payload_id="display",
            dialogue_id="dialogue",
            job_id="job",
            kind=TransientPayloadKind.DISPLAY,
            content=b"display",
            expires_at_ms=100,
        )
        planned = await DeliverySegmentRepository(storage, now_ms=lambda: 5).plan(
            job_id=created.job.job_id,
            expected_job_version=(await jobs.get(created.job.job_id)).version,
            items=(DeliveryPlanItem(DeliveryOperation.CREATE, display.payload_id, None),),
        )
        if state is TurnJobState.DELIVERY_PENDING:
            return jobs, planned.job, finished.dialogue
        claimed = await DeliverySegmentRepository(storage, now_ms=lambda: 6).claim_next(
            job_id=created.job.job_id, expected_job_version=planned.job.version
        )
        if state is TurnJobState.DELIVERING:
            return jobs, claimed.job, finished.dialogue
        if state is TurnJobState.DELIVERED:
            delivered = await DeliverySegmentRepository(storage, now_ms=lambda: 7).finish_sending(
                job_id=created.job.job_id,
                sequence=1,
                expected_job_version=claimed.job.version,
                outcome=DeliveryFinishOutcome.CONFIRMED,
                confirmed_message_id=303,
            )
            return jobs, delivered.job, finished.dialogue
        if state is TurnJobState.DELIVERY_UNKNOWN:
            unknown = await DeliverySegmentRepository(storage, now_ms=lambda: 7).finish_sending(
                job_id=created.job.job_id,
                sequence=1,
                expected_job_version=claimed.job.version,
                outcome=DeliveryFinishOutcome.UNKNOWN,
                error_class="TELEGRAM.unknown",
            )
            return jobs, unknown.job, finished.dialogue
        raise AssertionError(state)

    async def expire_input(self, storage):
        await storage.write(
            lambda connection: (connection.execute(
                "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 "
                "WHERE payload_id = 'input'"
            ), None)[1]
        )

    async def replay(self, storage, clock):
        return await TurnJobRepository(storage, now_ms=clock).claim_ingress(
            update_id=101,
            job_id="caller-job",
            source_chat_id=-999,
            source_message_id=999,
            dialogue_id="caller-dialogue",
            server_id="caller-server",
            profile_id="caller-profile",
            thread_id="caller-thread",
            model_id="caller-model",
            reasoning_effort="low",
            input_payload_id="caller-input",
            input_content=b"caller-content",
            input_expires_at_ms=1000,
        )

    async def assert_retained_duplicate_after_sweep(self, state):
        storage = await self.open()
        try:
            jobs, original_job, _ = await self.make_job(storage, state)
            original_ingress = await IngressUpdateRepository(storage).get(101)
            await self.expire_input(storage)
            sweep = await RetentionRepository(storage, now_ms=lambda: 10).sweep(100)
            self.assertEqual(1, sweep.payloads_deleted)
            self.assertIsNone(await TransientPayloadRepository(storage).get("input"))
            self.assertEqual(original_job, await jobs.get("job"))
            self.assertEqual(original_ingress, await IngressUpdateRepository(storage).get(101))
            calls = []

            def raising_clock():
                calls.append(1)
                raise AssertionError("duplicate replay called the clock")

            duplicate = await self.replay(storage, raising_clock)
            self.assertIs(TurnIngressClaimStatus.DUPLICATE, duplicate.status)
            self.assertEqual(original_job, duplicate.job)
            self.assertEqual(original_ingress, duplicate.ingress)
            self.assertIsNone(duplicate.input_payload)
            self.assertEqual([], calls)
            self.assertEqual((1, 1, 0), await storage.read(lambda c: tuple(c.execute(
                "SELECT (SELECT COUNT(*) FROM turn_jobs), "
                "(SELECT COUNT(*) FROM ingress_updates WHERE disposition LIKE 'JOB:%'), "
                "(SELECT COUNT(*) FROM transient_payloads WHERE kind = 'INPUT')"
            ).fetchone())))
            self.assertEqual(original_job, await jobs.get("job"))
            self.assertEqual(original_ingress, await IngressUpdateRepository(storage).get(101))
        finally:
            await storage.close()

    async def test_real_retention_deletes_input_but_replay_is_duplicate(self):
        await self.assert_retained_duplicate_after_sweep(TurnJobState.CODEX_COMPLETED)

    async def test_all_input_optional_states_allow_missing_input_duplicate(self):
        for state in (
            TurnJobState.CODEX_COMPLETED,
            TurnJobState.FAILED,
            TurnJobState.UNKNOWN,
            TurnJobState.DELIVERY_PENDING,
            TurnJobState.DELIVERING,
            TurnJobState.DELIVERED,
            TurnJobState.DELIVERY_UNKNOWN,
        ):
            self.path = os.path.join(self.tempdir.name, f"optional-{state.value}.sqlite3")
            await self.assert_retained_duplicate_after_sweep(state)

    async def test_active_missing_input_is_invariant_without_mutation_or_clock(self):
        for state in (
            TurnJobState.RECEIVED,
            TurnJobState.CLAIMED,
            TurnJobState.CODEX_STARTING,
            TurnJobState.CODEX_RUNNING,
        ):
            self.path = os.path.join(self.tempdir.name, f"required-{state.value}.sqlite3")
            storage = await self.open()
            try:
                jobs, original_job, _ = await self.make_job(storage, state)
                original_ingress = await IngressUpdateRepository(storage).get(101)
                await storage.write(lambda connection: (connection.execute(
                    "DELETE FROM transient_payloads WHERE payload_id = 'input'"
                ), None)[1])
                calls = []

                def raising_clock():
                    calls.append(1)
                    raise AssertionError("active duplicate called the clock")

                with self.assertRaises(RepositoryError) as raised:
                    await self.replay(storage, raising_clock)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], calls)
                self.assertEqual(original_job, await jobs.get("job"))
                self.assertEqual(original_ingress, await IngressUpdateRepository(storage).get(101))
                self.assertEqual(0, await storage.read(lambda c: c.execute(
                    "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'INPUT'"
                ).fetchone()[0]))
            finally:
                await storage.close()

    async def test_existing_input_is_strict_and_public_boundaries_remain_unchanged(self):
        storage = await self.open()
        try:
            jobs, original_job, _ = await self.make_job(storage)
            duplicate = await self.replay(storage, lambda: 99)
            self.assertIs(TurnIngressClaimStatus.DUPLICATE, duplicate.status)
            self.assertEqual(original_job, duplicate.job)
            self.assertEqual("input", duplicate.input_payload.payload_id)

            await storage.write(lambda connection: (connection.execute(
                "UPDATE transient_payloads SET content = ?, content_sha256 = ? "
                " , byte_length = ? WHERE payload_id = 'input'",
                (b"corrupt-input", hashlib.sha256(b"canonical-input").hexdigest(), 13),
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await self.replay(storage, lambda: 99)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            await storage.write(lambda connection: (connection.execute(
                "UPDATE transient_payloads SET content = ?, content_sha256 = ?, byte_length = ? "
                "WHERE payload_id = 'input'",
                (b"canonical-input", hashlib.sha256(b"canonical-input").hexdigest(), 15),
            ), None)[1])
            await storage.write(lambda connection: (connection.execute(
                "UPDATE transient_payloads SET dialogue_id = NULL WHERE payload_id = 'input'"
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await self.replay(storage, lambda: 99)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            await storage.write(lambda connection: (connection.execute(
                "UPDATE transient_payloads SET dialogue_id = 'dialogue', byte_length = 15 "
                "WHERE payload_id = 'input'"
            ), None)[1])
            await storage.write(lambda connection: (connection.execute(
                "INSERT INTO transient_payloads "
                "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                "created_at_ms, expires_at_ms) VALUES "
                "('input-duplicate', 'dialogue', 'job', 'INPUT', ?, ?, ?, 3, 100)",
                (b"canonical-input", hashlib.sha256(b"canonical-input").hexdigest(), 15),
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await self.replay(storage, lambda: 99)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)

            with self.assertRaises(RepositoryError) as raised:
                await TransientPayloadRepository(storage).get_input_for_job("job")
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_public_get_input_missing_and_claim_turn_missing_remain_strict(self):
        storage = await self.open()
        try:
            jobs, original_job, dialogue = await self.make_job(storage, TurnJobState.RECEIVED)
            await storage.write(lambda connection: (connection.execute(
                "DELETE FROM transient_payloads WHERE payload_id = 'input'"
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await TransientPayloadRepository(storage).get_input_for_job("job")
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            calls = []

            def raising_clock():
                calls.append(1)
                raise AssertionError("claim_turn called the clock after missing input")

            with self.assertRaises(RepositoryError) as raised:
                await TurnJobRepository(storage, now_ms=raising_clock).claim_turn(
                    job_id="job",
                    expected_job_version=original_job.version,
                    expected_dialogue_version=dialogue.version,
                    thread_id="thread",
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], calls)
            self.assertEqual(TurnJobState.RECEIVED, (await jobs.get("job")).state)
            self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
