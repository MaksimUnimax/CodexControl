"""P2 acceptance supplement for replay after legal INPUT retention."""

from __future__ import annotations

import unittest

from codex_control.storage import (
    IngressUpdateRepository,
    RetentionRepository,
    TransientPayloadRepository,
    TurnIngressClaimStatus,
    TurnJobRepository,
)
from tests.acceptance.test_p2_6b_support import TempDatabase, create_completed


class P2C1RetentionReplayAcceptanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = TempDatabase.create()

    def tearDown(self):
        self.db.cleanup()

    async def test_same_update_retained_job_replays_without_new_effect_claim(self):
        from codex_control.storage import SqliteStorage

        storage = await SqliteStorage.open(self.db.path, now_ms=lambda: 1)
        try:
            finished = await create_completed(storage)
            original_job = finished.job
            original_ingress = await IngressUpdateRepository(storage).get(101)
            await storage.write(lambda connection: (connection.execute(
                "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 "
                "WHERE payload_id = 'input-1'"
            ), None)[1])
            sweep = await RetentionRepository(storage, now_ms=lambda: 10).sweep(100)
            self.assertEqual(1, sweep.payloads_deleted)
            self.assertIsNone(await TransientPayloadRepository(storage).get("input-1"))
            self.assertEqual(original_job, await TurnJobRepository(storage).get("job-1"))
            self.assertEqual(original_ingress, await IngressUpdateRepository(storage).get(101))

            clock_calls = []

            def raising_clock():
                clock_calls.append(1)
                raise AssertionError("replay called a mutation clock")

            replay = await TurnJobRepository(storage, now_ms=raising_clock).claim_ingress(
                update_id=101,
                job_id="new-job-from-replay",
                source_chat_id=-2002,
                source_message_id=999,
                dialogue_id="caller-dialogue",
                server_id="caller-server",
                profile_id="caller-profile",
                thread_id="caller-thread",
                model_id="caller-model",
                reasoning_effort="low",
                input_payload_id="new-input-from-replay",
                input_content=b"different-caller-content",
                input_expires_at_ms=1000,
            )
            self.assertIs(TurnIngressClaimStatus.DUPLICATE, replay.status)
            self.assertEqual(original_job, replay.job)
            self.assertEqual(original_ingress, replay.ingress)
            self.assertIsNone(replay.input_payload)
            self.assertEqual([], clock_calls)
            self.assertEqual((1, 1, 0), await storage.read(lambda c: tuple(c.execute(
                "SELECT (SELECT COUNT(*) FROM turn_jobs), "
                "(SELECT COUNT(*) FROM ingress_updates WHERE disposition LIKE 'JOB:%'), "
                "(SELECT COUNT(*) FROM transient_payloads WHERE kind = 'INPUT')"
            ).fetchone())))
            self.assertIsNone(await TurnJobRepository(storage).get("new-job-from-replay"))
            self.assertIsNone(await TransientPayloadRepository(storage).get("new-input-from-replay"))
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
