import asyncio
import hashlib
import os
import tempfile
import threading
import unittest

from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnIngressClaimStatus,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)


class TurnJobsAndPayloadsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self):
        return await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def dialogue(self, storage, *, state=DialogueState.IDLE):
        repo = DialogueRepository(storage, now_ms=lambda: 10)
        await repo.create_intent(dialogue_id="d", server_id="server", profile_id="profile")
        if state is DialogueState.IDLE:
            return await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
        return await repo.get_live()

    async def job(self, storage, *, update=10, state=DialogueState.IDLE):
        dialogue = await self.dialogue(storage, state=state)
        repo = TurnJobRepository(storage, now_ms=lambda: 20)
        result = await repo.claim_ingress(
            update_id=update, job_id=f"job-{update}", source_chat_id=-100,
            source_message_id=update, dialogue_id="d", server_id="server",
            profile_id="profile", thread_id=None if state is DialogueState.CREATING else "thread",
            model_id="model", reasoning_effort="high", input_payload_id=f"payload-{update}",
            input_content=b"input", input_expires_at_ms=100,
        )
        return dialogue, repo, result

    async def running_job(self, storage, *, update=10):
        dialogue, repo, created = await self.job(storage, update=update)
        claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                        expected_dialogue_version=dialogue.version, thread_id="thread")
        starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
        running = await repo.mark_codex_running(job_id=created.job.job_id, expected_version=starting.version,
                                                codex_turn_id="turn")
        return dialogue, repo, created, claimed, running

    async def test_ingress_new_and_duplicate_job_restart_authority(self):
        storage = await self.open()
        try:
            calls = []
            await self.dialogue(storage)
            repo = TurnJobRepository(storage, now_ms=lambda: calls.append(20) or 20)
            created = await repo.claim_ingress(
                update_id=1, job_id="job-1", source_chat_id=-100, source_message_id=2,
                dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                model_id="model", reasoning_effort="high", input_payload_id="payload-1",
                input_content=b"hello", input_expires_at_ms=30)
            self.assertIs(TurnIngressClaimStatus.CREATED, created.status)
            self.assertEqual(1, len(calls))
            await storage.close()
            storage = await self.open()
            duplicate = await TurnJobRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).claim_ingress(
                update_id=1, job_id="replacement", source_chat_id=-1, source_message_id=3,
                dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                model_id="other", reasoning_effort="low", input_payload_id="replacement-payload",
                input_content=b"replacement", input_expires_at_ms=40)
            self.assertIs(TurnIngressClaimStatus.DUPLICATE, duplicate.status)
            self.assertEqual(created.job, duplicate.job)
            self.assertEqual(created.input_payload, duplicate.input_payload)
        finally:
            await storage.close()

    async def test_duplicate_non_job_does_not_reclassify(self):
        storage = await self.open()
        try:
            await IngressUpdateRepository(storage, now_ms=lambda: 5).claim_ignored(
                update_id=2, disposition=IngressDispositionKind.IGNORED_SLEEP)
            result = await TurnJobRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).claim_ingress(
                update_id=2, job_id="job", source_chat_id=-1, source_message_id=1, dialogue_id="missing",
                server_id="s", profile_id="p", thread_id=None, model_id=None, reasoning_effort=None,
                input_payload_id="payload", input_content=b"x", input_expires_at_ms=10)
            self.assertIs(TurnIngressClaimStatus.DUPLICATE, result.status)
            self.assertIsNone(result.job)
            self.assertIsNone(result.input_payload)
        finally:
            await storage.close()

    async def test_ingress_id_collisions_and_received_guard(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            repo = TurnJobRepository(storage, now_ms=lambda: 20)
            await repo.claim_ingress(update_id=1, job_id="same", source_chat_id=-1, source_message_id=1,
                                     dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                                     model_id=None, reasoning_effort=None, input_payload_id="p1",
                                     input_content=b"x", input_expires_at_ms=30)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_ingress(update_id=2, job_id="same", source_chat_id=-1, source_message_id=2,
                                         dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                                         model_id=None, reasoning_effort=None, input_payload_id="p2",
                                         input_content=b"x", input_expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_ingress(update_id=3, job_id="other", source_chat_id=-1, source_message_id=3,
                                         dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                                         model_id=None, reasoning_effort=None, input_payload_id="p1",
                                         input_content=b"x", input_expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_ingress(update_id=4, job_id="other2", source_chat_id=-1, source_message_id=4,
                                         dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                                         model_id=None, reasoning_effort=None, input_payload_id="p4",
                                         input_content=b"x", input_expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_ingress_creating_path(self):
        storage = await self.open()
        try:
            await self.dialogue(storage, state=DialogueState.CREATING)
            result = await TurnJobRepository(storage, now_ms=lambda: 20).claim_ingress(
                update_id=1, job_id="j", source_chat_id=-1, source_message_id=1, dialogue_id="d",
                server_id="server", profile_id="profile", thread_id=None, model_id=None, reasoning_effort=None,
                input_payload_id="p", input_content=b"x", input_expires_at_ms=30)
            self.assertEqual(TurnJobState.RECEIVED, result.job.state)
        finally:
            await storage.close()

    async def test_ingress_concurrency(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            async def claim(update, job, payload):
                return await TurnJobRepository(storage, now_ms=lambda: 20).claim_ingress(
                    update_id=update, job_id=job, source_chat_id=-1, source_message_id=update,
                    dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                    model_id=None, reasoning_effort=None, input_payload_id=payload, input_content=b"x", input_expires_at_ms=30)
            other = await asyncio.gather(claim(1, "j1", "p1"), claim(2, "j2", "p2"), return_exceptions=True)
            self.assertEqual(1, sum(not isinstance(r, Exception) for r in other))
            self.assertEqual(1, sum(isinstance(r, RepositoryError) and r.category is RepositoryErrorCategory.STATE_CONFLICT for r in other))
            await storage.close()
            self.path = os.path.join(self.tempdir.name, "second.sqlite3")
            storage = await self.open()
            await self.dialogue(storage)
            same = await asyncio.gather(claim(3, "j3", "p3"), claim(3, "j4", "p4"))
            self.assertEqual(1, sum(r.status is TurnIngressClaimStatus.CREATED for r in same))
            self.assertEqual(1, sum(r.status is TurnIngressClaimStatus.DUPLICATE for r in same))
        finally:
            await storage.close()

    async def test_ingress_repeated_cancellation_stays_owned_after_submission(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            entered = threading.Event()
            release = threading.Event()

            def blocked_clock():
                entered.set()
                release.wait(5)
                return 20

            task = asyncio.create_task(TurnJobRepository(storage, now_ms=blocked_clock).claim_ingress(
                update_id=1, job_id="cancel-job", source_chat_id=-1, source_message_id=1,
                dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                model_id=None, reasoning_effort=None, input_payload_id="cancel-payload",
                input_content=b"x", input_expires_at_ms=30))
            await asyncio.to_thread(entered.wait, 5)
            for _ in range(3):
                task.cancel()
                await asyncio.sleep(0)
            release.set()
            result = await task
            self.assertIs(TurnIngressClaimStatus.CREATED, result.status)
            self.assertFalse(task.cancelled())
            self.assertEqual(result.job, await TurnJobRepository(storage).get("cancel-job"))
        finally:
            await storage.close()

    async def test_claim_turn_atomic_thread_binding_and_conflict_precedence(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)
            result = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                           expected_dialogue_version=dialogue.version, thread_id="thread")
            self.assertEqual(TurnJobState.CLAIMED, result.job.state)
            self.assertEqual(DialogueState.TURN_RUNNING, result.dialogue.state)
            self.assertEqual("thread", result.job.thread_id)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                       expected_dialogue_version=dialogue.version, thread_id="thread")
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_claim_turn_requires_exact_thread(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                       expected_dialogue_version=dialogue.version, thread_id="wrong")
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_claim_turn_requires_durable_ingress_input_coherence(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)
            await storage.write(lambda c: (c.execute("UPDATE transient_payloads SET content_sha256 = ? WHERE payload_id = ?", ("0" * 64, created.input_payload.payload_id)), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                       expected_dialogue_version=dialogue.version, thread_id="thread")
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_claim_turn_concurrent_one_winner(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)
            results = await asyncio.gather(
                repo.claim_turn(job_id=created.job.job_id, expected_job_version=0, expected_dialogue_version=dialogue.version, thread_id="thread"),
                repo.claim_turn(job_id=created.job.job_id, expected_job_version=0, expected_dialogue_version=dialogue.version, thread_id="thread"),
                return_exceptions=True)
            self.assertEqual(1, sum(not isinstance(r, Exception) for r in results))
            self.assertEqual(1, sum(isinstance(r, RepositoryError) for r in results))
        finally:
            await storage.close()

    async def test_codex_starting_and_running_are_one_time_claims(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)
            claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                            expected_dialogue_version=1, thread_id="thread")
            starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
            self.assertEqual(TurnJobState.CODEX_STARTING, starting.state)
        finally:
            await storage.close()

    async def test_finish_completed_atomic_output_and_restart(self):
        storage = await self.open()
        try:
            _, repo, created, claimed, running = await self.running_job(storage)
            output = b"PRIVATE_P2_4A_CONTENT_MUST_NOT_LEAK"
            result = await repo.finish_codex(
                job_id=created.job.job_id, expected_job_version=running.version,
                expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                output_payload_id="out", output_content=output, output_expires_at_ms=100)
            self.assertEqual(TurnJobState.CODEX_COMPLETED, result.job.state)
            self.assertEqual(DialogueState.IDLE, result.dialogue.state)
            self.assertEqual(hashlib.sha256(output).hexdigest(), result.output_payload.content_sha256)
            await storage.close()
            storage = await self.open()
            self.assertEqual(result.job, await TurnJobRepository(storage).get(created.job.job_id))
            self.assertEqual(result.output_payload, await TransientPayloadRepository(storage).get("out"))
        finally:
            await storage.close()

    async def test_finish_failed_and_unknown_from_starting(self):
        for outcome, job_state, dialogue_state, update in (
            (TurnTerminalOutcome.FAILED, TurnJobState.FAILED, DialogueState.ERROR, 11),
            (TurnTerminalOutcome.UNKNOWN, TurnJobState.UNKNOWN, DialogueState.TURN_UNKNOWN, 12),
        ):
            storage = await self.open()
            try:
                _, repo, created = await self.job(storage, update=update)
                claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                                expected_dialogue_version=1, thread_id="thread")
                starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
                result = await repo.finish_codex(job_id=created.job.job_id, expected_job_version=starting.version,
                                                 expected_dialogue_version=claimed.dialogue.version, outcome=outcome,
                                                 error_class="CODEX.timeout:1")
                self.assertEqual(job_state, result.job.state)
                self.assertEqual(dialogue_state, result.dialogue.state)
                self.assertEqual("CODEX.timeout:1", result.dialogue.last_error_class)
            finally:
                await storage.close()
            self.path = os.path.join(self.tempdir.name, f"{update}.sqlite3")

    async def test_finish_failed_and_unknown_from_running(self):
        for outcome, job_state, dialogue_state, update in (
            (TurnTerminalOutcome.FAILED, TurnJobState.FAILED, DialogueState.ERROR, 21),
            (TurnTerminalOutcome.UNKNOWN, TurnJobState.UNKNOWN, DialogueState.TURN_UNKNOWN, 22),
        ):
            storage = await self.open()
            try:
                _, repo, created, claimed, running = await self.running_job(storage, update=update)
                result = await repo.finish_codex(job_id=created.job.job_id, expected_job_version=running.version,
                                                 expected_dialogue_version=claimed.dialogue.version, outcome=outcome,
                                                 error_class="CODEX.failed:1")
                self.assertEqual(job_state, result.job.state)
                self.assertEqual(dialogue_state, result.dialogue.state)
            finally:
                await storage.close()
            self.path = os.path.join(self.tempdir.name, f"running-{update}.sqlite3")

    async def test_finish_invalid_state_and_conflict_order(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)
            claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                            expected_dialogue_version=1, thread_id="thread")
            starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
            with self.assertRaises(RepositoryError) as raised:
                await repo.finish_codex(job_id=created.job.job_id, expected_job_version=starting.version,
                                        expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED)
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.finish_codex(job_id=created.job.job_id, expected_job_version=99,
                                        expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.FAILED,
                                        error_class="x")
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_output_collision_and_clock_failure_rollback(self):
        storage = await self.open()
        try:
            _, repo, created, claimed, running = await self.running_job(storage)
            await TransientPayloadRepository(storage, now_ms=lambda: 25).create(
                payload_id="collision", dialogue_id="d", kind=TransientPayloadKind.DISPLAY, content=b"x", expires_at_ms=100)
            with self.assertRaises(RepositoryError) as raised:
                await repo.finish_codex(job_id=created.job.job_id, expected_job_version=running.version,
                                        expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                                        output_payload_id="collision", output_content=b"y", output_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            self.assertEqual(TurnJobState.CODEX_RUNNING, (await repo.get(created.job.job_id)).state)
            failing = TurnJobRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_CLOCK")))
            with self.assertRaises(RepositoryError) as raised:
                await failing.finish_codex(job_id=created.job.job_id, expected_job_version=running.version,
                                           expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                                           output_payload_id="out", output_content=b"y", output_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertIsNone(await TransientPayloadRepository(storage).get("out"))
        finally:
            await storage.close()

    async def test_payload_exact_type_and_size_boundaries(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            repo = TransientPayloadRepository(storage, now_ms=lambda: 10)
            for index, value in enumerate((b"", b"x" * 8_388_609, bytearray(b"x"), memoryview(b"x"), "x", None)):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.create(payload_id=f"bad-{index}", dialogue_id="d",
                                      kind=TransientPayloadKind.DISPLAY, content=value, expires_at_ms=20)
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            one = await repo.create(payload_id="one", dialogue_id="d", kind=TransientPayloadKind.DISPLAY, content=b"x", expires_at_ms=20)
            eight = await repo.create(payload_id="eight", dialogue_id="d", kind=TransientPayloadKind.DISPLAY, content=b"x" * 8_388_608, expires_at_ms=20)
            self.assertEqual(1, one.byte_length)
            self.assertEqual(8_388_608, eight.byte_length)
        finally:
            await storage.close()

    async def test_payload_owners_kinds_and_duplicate(self):
        storage = await self.open()
        try:
            dialogue, _, created = await self.job(storage)
            repo = TransientPayloadRepository(storage, now_ms=lambda: 20)
            for kind in (TransientPayloadKind.OUTPUT, TransientPayloadKind.APPROVAL, TransientPayloadKind.DISPLAY):
                result = await repo.create(payload_id=kind.value.lower(), dialogue_id="d", kind=kind, content=b"x", expires_at_ms=30)
                self.assertEqual(kind, result.kind)
            with self.assertRaises(RepositoryError) as raised:
                await repo.create(payload_id="input", job_id=created.job.job_id, kind=TransientPayloadKind.INPUT, content=b"x", expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.create(payload_id="wrong", dialogue_id="other", job_id=created.job.job_id,
                                  kind=TransientPayloadKind.DISPLAY, content=b"x", expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            await repo.create(payload_id="dup", dialogue_id="d", kind=TransientPayloadKind.DISPLAY, content=b"x", expires_at_ms=30)
            with self.assertRaises(RepositoryError) as raised:
                await repo.create(payload_id="dup", dialogue_id="d", kind=TransientPayloadKind.DISPLAY, content=b"y", expires_at_ms=30)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
        finally:
            await storage.close()

    async def test_get_input_for_job_missing_and_corruption(self):
        storage = await self.open()
        try:
            _, _, created = await self.job(storage)
            repo = TransientPayloadRepository(storage)
            self.assertEqual(created.input_payload, await repo.get_input_for_job(created.job.job_id))
            with self.assertRaises(RepositoryError) as raised:
                await repo.get_input_for_job("missing")
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            await storage.write(lambda c: (c.execute("UPDATE transient_payloads SET content = ? WHERE payload_id = ?", (b"y" * created.input_payload.byte_length, created.input_payload.payload_id)), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await repo.get_input_for_job(created.job.job_id)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_job_corruption_and_redaction(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)
            await storage.write(lambda c: (c.execute("UPDATE turn_jobs SET input_sha256 = ?, error_class = ? WHERE job_id = ?", ("0" * 64, "PRIVATE JOB VALUE", created.job.job_id)), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await repo.get(created.job.job_id)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("PRIVATE_JOB_VALUE", repr(raised.exception))
        finally:
            await storage.close()

    async def test_clock_and_version_boundaries(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)
            calls = []
            bad = TurnJobRepository(storage, now_ms=lambda: calls.append(1) or True)
            with self.assertRaises(RepositoryError) as raised:
                await bad.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                     expected_dialogue_version=dialogue.version, thread_id="thread")
            self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertEqual(1, len(calls))
        finally:
            await storage.close()

    async def test_get_reads_do_not_call_clock(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)
            self.assertEqual(created.job, await TurnJobRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).get(created.job.job_id))
            self.assertEqual(created.input_payload, await TransientPayloadRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).get(created.input_payload.payload_id))
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
