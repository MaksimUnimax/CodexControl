from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from codex_control.storage import TurnJobRepository, TurnJobState
from tests.acceptance.test_p2_6b_support import (
    DeterministicClock,
    TempDatabase,
    create_idle,
    create_received,
    open_storage,
)
from codex_control.storage import DialogueRepository, TurnTerminalOutcome


class LocalOrchestrationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.database = TempDatabase.create()
        self.storage = await open_storage(self.database)

    async def asyncTearDown(self):
        await self.storage.close()
        self.database.cleanup()

    async def _completed(self, job_id: str, update_id: int):
        ingress = await create_received(
            self.storage,
            job_id=job_id,
            update_id=update_id,
            payload_id=f"input-{job_id}",
        )
        dialogue = await DialogueRepository(self.storage).get_live()
        jobs = TurnJobRepository(self.storage, now_ms=DeterministicClock())
        claimed = await jobs.claim_turn(
            job_id=job_id,
            expected_job_version=ingress.job.version,
            expected_dialogue_version=dialogue.version,
            thread_id="thread-1",
        )
        starting = await jobs.mark_codex_starting(job_id=job_id, expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(
            job_id=job_id, expected_version=starting.version, codex_turn_id=f"turn-{job_id}"
        )
        return await jobs.finish_codex(
            job_id=job_id,
            expected_job_version=running.version,
            expected_dialogue_version=claimed.dialogue.version,
            outcome=TurnTerminalOutcome.COMPLETED,
            output_payload_id=f"output-{job_id}",
            output_content=b"output",
            output_expires_at_ms=100_000,
        )

    async def test_delivery_discovery_is_oldest_first_bounded_and_read_only(self):
        await self._completed("job-b", 2)
        await self._completed("job-a", 1)
        clock = DeterministicClock()
        repository = TurnJobRepository(self.storage, now_ms=clock)

        candidates = await repository.list_delivery_candidates(limit=1)

        self.assertEqual(("job-a",), tuple(job.job_id for job in candidates))
        self.assertEqual(0, clock.calls)
        self.assertEqual(TurnJobState.CODEX_COMPLETED, candidates[0].state)

        all_candidates = await repository.list_delivery_candidates(limit=4096)
        self.assertEqual(("job-a", "job-b"), tuple(job.job_id for job in all_candidates))
        self.assertEqual(0, clock.calls)

    async def test_discovery_excludes_non_delivery_states_after_materialization(self):
        await self._completed("job-completed", 1)
        await create_received(self.storage, job_id="job-received", update_id=2)
        repository = TurnJobRepository(self.storage)
        candidates = await repository.list_delivery_candidates(limit=4096)

        def states(connection):
            return tuple(row[0] for row in connection.execute(
                "SELECT state FROM turn_jobs ORDER BY job_id"
            ).fetchall())

        self.assertEqual(("job-completed",), tuple(job.job_id for job in candidates))
        self.assertEqual(
            (TurnJobState.CODEX_COMPLETED.value, TurnJobState.RECEIVED.value),
            await self.storage.read(states),
        )

    async def test_discovery_complete_state_matrix_order_limit_bool_zero_clock_and_no_write(self):
        await create_idle(self.storage)
        states = (
            ("received", TurnJobState.RECEIVED, None, None),
            ("claimed", TurnJobState.CLAIMED, None, None),
            ("starting", TurnJobState.CODEX_STARTING, None, None),
            ("running", TurnJobState.CODEX_RUNNING, "turn-running", None),
            ("completed", TurnJobState.CODEX_COMPLETED, "turn-completed", None),
            ("pending", TurnJobState.DELIVERY_PENDING, "turn-pending", None),
            ("delivering", TurnJobState.DELIVERING, "turn-delivering", None),
            ("received-delivered", TurnJobState.DELIVERED, "turn-delivered", None),
            ("failed", TurnJobState.FAILED, "turn-failed", "CODEX_TURN_FAILED"),
            ("unknown", TurnJobState.UNKNOWN, "turn-unknown", "CODEX_AMBIGUOUS"),
            ("delivery-unknown", TurnJobState.DELIVERY_UNKNOWN, "turn-delivery-unknown", "TELEGRAM_RECOVERY_AMBIGUOUS"),
        )
        digest = hashlib.sha256(b"matrix").hexdigest()

        def insert(connection):
            for index, (job_id, state, turn_id, error_class) in enumerate(states):
                candidate_time = 100 if state in {
                    TurnJobState.CODEX_COMPLETED, TurnJobState.DELIVERY_PENDING, TurnJobState.DELIVERING
                } else 200 + index
                connection.execute(
                    "INSERT INTO turn_jobs (job_id, telegram_update_id, source_chat_id, source_message_id, "
                    "dialogue_id, server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
                    "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                    "VALUES (?, ?, ?, ?, 'dialogue-1', 'server-1', 'profile-1', ?, 'model-test', 'medium', ?, ?, ?, 0, ?, ?, ?)",
                    (job_id, index + 1000, -1001, index + 1,
                     None if state is TurnJobState.RECEIVED else "thread-1", digest, turn_id,
                     state.value, candidate_time, candidate_time, error_class),
                )

        await self.storage.write(insert)
        clock = DeterministicClock()
        repository = TurnJobRepository(self.storage, now_ms=clock)
        with patch.object(self.storage, "write", side_effect=AssertionError("discovery must be read-only")):
            candidates = await repository.list_delivery_candidates(limit=4096)
            limited = await repository.list_delivery_candidates(limit=2)
        self.assertEqual(("completed", "delivering", "pending"), tuple(job.job_id for job in candidates))
        self.assertEqual(("completed", "delivering"), tuple(job.job_id for job in limited))
        self.assertEqual((TurnJobState.CODEX_COMPLETED, TurnJobState.DELIVERING, TurnJobState.DELIVERY_PENDING), tuple(job.state for job in candidates))
        self.assertEqual(0, clock.calls)
        for invalid in (True, False, 0, 4097):
            with self.assertRaises(Exception):
                await repository.list_delivery_candidates(limit=invalid)
