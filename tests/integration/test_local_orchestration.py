from __future__ import annotations

import unittest

from codex_control.storage import TurnJobRepository, TurnJobState
from tests.acceptance.test_p2_6b_support import (
    DeterministicClock,
    TempDatabase,
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
