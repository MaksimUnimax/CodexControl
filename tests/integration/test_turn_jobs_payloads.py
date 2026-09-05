import asyncio
import hashlib
import os
import sqlite3
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

    async def corrupt(self, storage, sql, parameters=()):
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(sql, parameters)
            connection.commit()
        return await self.open()

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

    async def test_new_update_with_orphan_job_update_is_invariant(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)

            def seed_orphan(connection):
                connection.execute(
                    "INSERT INTO turn_jobs "
                    "(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
                    "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
                    "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, ?, ?, NULL)",
                    ("orphan-job", 77, -1, 1, "d", "server", "profile", "thread", None, None,
                     hashlib.sha256(b"orphan").hexdigest(), TurnJobState.RECEIVED.value, 20, 20),
                )

            await storage.write(seed_orphan)
            calls = []
            repo = TurnJobRepository(storage, now_ms=lambda: calls.append(1) or 30)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_ingress(
                    update_id=77, job_id="new-job", source_chat_id=-1, source_message_id=2,
                    dialogue_id="d", server_id="server", profile_id="profile", thread_id="thread",
                    model_id=None, reasoning_effort=None, input_payload_id="new-payload",
                    input_content=b"new", input_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], calls)
            self.assertIsNone(await IngressUpdateRepository(storage).get(77))
            self.assertEqual("orphan-job", (await repo.get("orphan-job")).job_id)
            self.assertIsNone(await TransientPayloadRepository(storage).get("new-payload"))
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

    async def test_missing_input_classification_public_and_internal(self):
        storage = await self.open()
        try:
            dialogue, repo, created = await self.job(storage)

            def remove_input(connection):
                connection.execute("DELETE FROM transient_payloads WHERE payload_id = ?", (created.input_payload.payload_id,))

            await storage.write(remove_input)
            public = TransientPayloadRepository(storage)
            with self.assertRaises(RepositoryError) as raised:
                await public.get_input_for_job(created.job.job_id)
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)

            duplicate_calls = []
            duplicate = TurnJobRepository(storage, now_ms=lambda: duplicate_calls.append(1) or 20)
            with self.assertRaises(RepositoryError) as raised:
                await duplicate.claim_ingress(
                    update_id=created.job.telegram_update_id, job_id="replacement", source_chat_id=-1,
                    source_message_id=99, dialogue_id="d", server_id="server", profile_id="profile",
                    thread_id="thread", model_id=None, reasoning_effort=None,
                    input_payload_id="replacement-payload", input_content=b"replacement",
                    input_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], duplicate_calls)

            claim_calls = []
            with self.assertRaises(RepositoryError) as raised:
                await TurnJobRepository(storage, now_ms=lambda: claim_calls.append(1) or 20).claim_turn(
                    job_id=created.job.job_id, expected_job_version=0,
                    expected_dialogue_version=dialogue.version, thread_id="thread")
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], claim_calls)
            self.assertEqual(TurnJobState.RECEIVED, (await repo.get(created.job.job_id)).state)
            self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)
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

    async def test_codex_running_turn_id_is_bound_once_and_validated(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)
            claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                            expected_dialogue_version=1, thread_id="thread")
            starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
            self.assertEqual(TurnJobState.CODEX_STARTING, starting.state)

            calls = []
            invalid = TurnJobRepository(storage, now_ms=lambda: calls.append(1) or 30)
            for turn_id in ("", "bad\x00id", "x" * 513):
                with self.assertRaises(RepositoryError) as raised:
                    await invalid.mark_codex_running(
                        job_id=created.job.job_id, expected_version=starting.version, codex_turn_id=turn_id)
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual([], calls)

            running = await repo.mark_codex_running(
                job_id=created.job.job_id, expected_version=starting.version, codex_turn_id="x" * 512)
            self.assertEqual(TurnJobState.CODEX_RUNNING, running.state)
            self.assertEqual("x" * 512, running.codex_turn_id)
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_codex_running(
                    job_id=created.job.job_id, expected_version=starting.version, codex_turn_id="turn-A")
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_codex_running(
                    job_id=created.job.job_id, expected_version=running.version, codex_turn_id="turn-B")
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            durable = await repo.get(created.job.job_id)
            self.assertEqual("x" * 512, durable.codex_turn_id)
        finally:
            await storage.close()

    async def test_first_dialogue_thread_binding_is_exactly_once(self):
        storage = await self.open()
        try:
            creating = await self.dialogue(storage, state=DialogueState.CREATING)
            repo = TurnJobRepository(storage, now_ms=lambda: 20)
            created = await repo.claim_ingress(
                update_id=31, job_id="first-job", source_chat_id=-1, source_message_id=1,
                dialogue_id="d", server_id="server", profile_id="profile", thread_id=None,
                model_id=None, reasoning_effort=None, input_payload_id="first-payload",
                input_content=b"first", input_expires_at_ms=100)
            self.assertIsNone(created.job.thread_id)
            confirmed = await DialogueRepository(storage, now_ms=lambda: 30).confirm_created(
                dialogue_id="d", expected_version=creating.version, thread_id="thread-A")
            claimed = await repo.claim_turn(
                job_id="first-job", expected_job_version=0,
                expected_dialogue_version=confirmed.version, thread_id="thread-A")
            self.assertEqual(TurnJobState.CLAIMED, claimed.job.state)
            self.assertEqual(DialogueState.TURN_RUNNING, claimed.dialogue.state)
            self.assertEqual("thread-A", claimed.job.thread_id)
            self.assertEqual("thread-A", claimed.dialogue.thread_id)

            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_turn(
                    job_id="first-job", expected_job_version=0,
                    expected_dialogue_version=confirmed.version, thread_id="thread-A")
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_turn(
                    job_id="first-job", expected_job_version=claimed.job.version,
                    expected_dialogue_version=claimed.dialogue.version, thread_id="thread-B")
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            self.assertEqual("thread-A", (await repo.get("first-job")).thread_id)
        finally:
            await storage.close()

    async def test_all_job_states_materialize_and_owned_shapes_fail_closed(self):
        storage = await self.open()
        try:
            _, repo, created = await self.job(storage)

            def update_shape(connection, state, thread, codex_turn, error):
                connection.execute(
                    "UPDATE turn_jobs SET state = ?, thread_id = ?, codex_turn_id = ?, error_class = ? WHERE job_id = ?",
                    (state.value, thread, codex_turn, error, created.job.job_id),
                )

            canonical = {
                TurnJobState.RECEIVED: ("thread", None, None),
                TurnJobState.CLAIMED: ("thread", None, None),
                TurnJobState.CODEX_STARTING: ("thread", None, None),
                TurnJobState.CODEX_RUNNING: ("thread", "turn", None),
                TurnJobState.CODEX_COMPLETED: ("thread", "turn", None),
                TurnJobState.FAILED: ("thread", None, "CODEX.failed"),
                TurnJobState.UNKNOWN: ("thread", "turn", "CODEX.unknown"),
                TurnJobState.DELIVERY_PENDING: ("thread", "turn", None),
                TurnJobState.DELIVERING: ("thread", "turn", None),
                TurnJobState.DELIVERED: ("thread", "turn", None),
                TurnJobState.DELIVERY_UNKNOWN: ("thread", "turn", None),
            }
            for state, (thread, codex_turn, error) in canonical.items():
                await storage.write(lambda c, s=state, t=thread, ct=codex_turn, e=error: update_shape(c, s, t, ct, e))
                materialized = await repo.get(created.job.job_id)
                self.assertEqual(state, materialized.state)

            invalid_shapes = (
                (TurnJobState.CLAIMED, None, None, None),
                (TurnJobState.CODEX_STARTING, "thread", "turn", None),
                (TurnJobState.CODEX_RUNNING, "thread", None, None),
                (TurnJobState.CODEX_COMPLETED, "thread", None, None),
                (TurnJobState.CODEX_COMPLETED, "thread", "turn", "PRIVATE_STATE_SHAPE"),
                (TurnJobState.FAILED, "thread", None, None),
                (TurnJobState.UNKNOWN, "thread", "turn", None),
                (TurnJobState.RECEIVED, "thread", "turn", None),
            )
            for state, thread, codex_turn, error in invalid_shapes:
                await storage.write(lambda c, s=state, t=thread, ct=codex_turn, e=error: update_shape(c, s, t, ct, e))
                with self.assertRaises(RepositoryError) as raised:
                    await repo.get(created.job.job_id)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn("PRIVATE_STATE_SHAPE", repr(raised.exception))
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
            collision_calls = []
            collision_repo = TurnJobRepository(storage, now_ms=lambda: collision_calls.append(1) or 30)
            with self.assertRaises(RepositoryError) as raised:
                await collision_repo.finish_codex(
                    job_id=created.job.job_id, expected_job_version=running.version,
                    expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                    output_payload_id="collision", output_content=b"y", output_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            self.assertEqual([], collision_calls)
            self.assertEqual(TurnJobState.CODEX_RUNNING, (await repo.get(created.job.job_id)).state)
            self.assertEqual(DialogueState.TURN_RUNNING, (await DialogueRepository(storage).get_live()).state)
            failing = TurnJobRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_CLOCK")))
            with self.assertRaises(RepositoryError) as raised:
                await failing.finish_codex(job_id=created.job.job_id, expected_job_version=running.version,
                                           expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                                           output_payload_id="out", output_content=b"y", output_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertIsNone(await TransientPayloadRepository(storage).get("out"))
            self.assertEqual(TurnJobState.CODEX_RUNNING, (await repo.get(created.job.job_id)).state)
            self.assertEqual(DialogueState.TURN_RUNNING, (await DialogueRepository(storage).get_live()).state)
        finally:
            await storage.close()

    async def test_generic_payload_duplicate_does_not_call_clock_or_change_record(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            repo = TransientPayloadRepository(storage, now_ms=lambda: 20)
            original = await repo.create(
                payload_id="duplicate-payload", dialogue_id="d", kind=TransientPayloadKind.DISPLAY,
                content=b"original", expires_at_ms=30)
            calls = []
            duplicate_repo = TransientPayloadRepository(storage, now_ms=lambda: calls.append(1) or 25)
            with self.assertRaises(RepositoryError) as raised:
                await duplicate_repo.create(
                    payload_id="duplicate-payload", dialogue_id="d", kind=TransientPayloadKind.DISPLAY,
                    content=b"replacement", expires_at_ms=40)
            self.assertIs(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            self.assertEqual([], calls)
            self.assertEqual(original, await repo.get("duplicate-payload"))
        finally:
            await storage.close()

    async def test_finish_concurrent_identical_versions_has_one_winner(self):
        storage = await self.open()
        try:
            _, repo, created, claimed, running = await self.running_job(storage)
            results = await asyncio.gather(
                repo.finish_codex(
                    job_id=created.job.job_id, expected_job_version=running.version,
                    expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                    output_payload_id="concurrent-output", output_content=b"output", output_expires_at_ms=100),
                repo.finish_codex(
                    job_id=created.job.job_id, expected_job_version=running.version,
                    expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
                    output_payload_id="concurrent-output", output_content=b"output", output_expires_at_ms=100),
                return_exceptions=True,
            )
            self.assertEqual(1, sum(not isinstance(result, Exception) for result in results))
            self.assertEqual(1, sum(
                isinstance(result, RepositoryError)
                and result.category in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT)
                for result in results
            ))
            final_job = await repo.get(created.job.job_id)
            final_dialogue = await DialogueRepository(storage).get_live()
            self.assertEqual(TurnJobState.CODEX_COMPLETED, final_job.state)
            self.assertEqual(DialogueState.IDLE, final_dialogue.state)
            self.assertEqual(running.version + 1, final_job.version)
            self.assertEqual(claimed.dialogue.version + 1, final_dialogue.version)
            self.assertEqual(1, await storage.read(
                lambda c: c.execute(
                    "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT' AND payload_id = ?",
                    ("concurrent-output",),
                ).fetchone()[0]
            ))
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

    async def test_payload_owner_and_input_coherence_corruption_fails_closed(self):
        cases = (
            ("dangling-dialogue", "UPDATE transient_payloads SET dialogue_id = ? WHERE payload_id = ?", ("missing-dialogue", "payload"), False),
            ("dangling-job", "UPDATE transient_payloads SET job_id = ? WHERE payload_id = ?", ("missing-job", "payload"), False),
            ("input-dialogue-only", "UPDATE transient_payloads SET job_id = NULL WHERE payload_id = ?", ("payload-10",), True),
            ("input-job-only", "UPDATE transient_payloads SET dialogue_id = NULL WHERE payload_id = ?", ("payload-10",), True),
            ("input-hash", "UPDATE turn_jobs SET input_sha256 = ? WHERE job_id = ?", (hashlib.sha256(b"changed").hexdigest(), "job-10"), True),
            ("job-dialogue-coherence", "UPDATE turn_jobs SET dialogue_id = ? WHERE job_id = ?", ("missing-dialogue", "job-10"), False),
        )
        for index, (name, sql, parameters, is_input) in enumerate(cases):
            storage = await self.open()
            try:
                _, _, created = await self.job(storage, update=10)
                if is_input:
                    payload_id = created.input_payload.payload_id
                else:
                    await TransientPayloadRepository(storage, now_ms=lambda: 25).create(
                        payload_id="payload", dialogue_id="d",
                        job_id=created.job.job_id if name == "job-dialogue-coherence" else None,
                        kind=TransientPayloadKind.DISPLAY,
                        content=b"display", expires_at_ms=100)
                    payload_id = "payload"
                if "payload_id = ?" in sql and len(parameters) == 1:
                    corruption_parameters = parameters
                elif payload_id != "payload" and "transient_payloads" in sql:
                    corruption_parameters = (parameters[0], payload_id)
                else:
                    corruption_parameters = parameters
                storage = await self.corrupt(storage, sql, corruption_parameters)
                with self.assertRaises(RepositoryError) as raised:
                    await TransientPayloadRepository(storage).get(payload_id)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category, name)
                self.assertNotIn("missing-dialogue", repr(raised.exception))
                self.assertNotIn("missing-job", repr(raised.exception))
            finally:
                await storage.close()
            self.path = os.path.join(self.tempdir.name, f"payload-corruption-{index}.sqlite3")

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

    async def test_version_overflow_paths_fail_before_clock(self):
        async def assert_overflow(index, setup, operation, verify):
            storage = await self.open()
            try:
                context = await setup(storage)
                calls = []
                with self.assertRaises(RepositoryError) as raised:
                    await operation(storage, context, lambda: calls.append(1) or 30)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], calls)
                await verify(storage, context)
            finally:
                await storage.close()
            self.path = os.path.join(self.tempdir.name, f"overflow-{index}.sqlite3")

        async def setup_claim_job(storage):
            dialogue, repo, created = await self.job(storage, update=40)
            await storage.write(lambda c: (c.execute(
                "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (9223372036854775807, created.job.job_id)
            ), None)[1])
            return dialogue, repo, created

        async def operation_claim_job(storage, context, clock):
            dialogue, _, created = context
            return await TurnJobRepository(storage, now_ms=clock).claim_turn(
                job_id=created.job.job_id, expected_job_version=9223372036854775807,
                expected_dialogue_version=dialogue.version, thread_id="thread")

        async def verify_claim_job(storage, context):
            _, repo, created = context
            self.assertEqual(9223372036854775807, (await repo.get(created.job.job_id)).version)
            self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)

        await assert_overflow(0, setup_claim_job, operation_claim_job, verify_claim_job)

        async def setup_claim_dialogue(storage):
            dialogue, repo, created = await self.job(storage, update=41)
            await storage.write(lambda c: (c.execute(
                "UPDATE dialogues SET version = ? WHERE dialogue_id = ?", (9223372036854775807, dialogue.dialogue_id)
            ), None)[1])
            return dialogue, repo, created

        async def operation_claim_dialogue(storage, context, clock):
            _, _, created = context
            return await TurnJobRepository(storage, now_ms=clock).claim_turn(
                job_id=created.job.job_id, expected_job_version=0,
                expected_dialogue_version=9223372036854775807, thread_id="thread")

        async def verify_claim_dialogue(storage, context):
            _, repo, created = context
            self.assertEqual(TurnJobState.RECEIVED, (await repo.get(created.job.job_id)).state)
            self.assertEqual(9223372036854775807, (await DialogueRepository(storage).get_live()).version)

        await assert_overflow(1, setup_claim_dialogue, operation_claim_dialogue, verify_claim_dialogue)

        async def setup_starting(storage):
            _, repo, created = await self.job(storage, update=42)
            claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                            expected_dialogue_version=1, thread_id="thread")
            await storage.write(lambda c: (c.execute(
                "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (9223372036854775807, created.job.job_id)
            ), None)[1])
            return repo, created, claimed

        async def operation_starting(storage, context, clock):
            _, created, _ = context
            return await TurnJobRepository(storage, now_ms=clock).mark_codex_starting(
                job_id=created.job.job_id, expected_version=9223372036854775807)

        async def verify_starting(storage, context):
            repo, created, claimed = context
            job = await repo.get(created.job.job_id)
            self.assertEqual(TurnJobState.CLAIMED, job.state)
            self.assertEqual(9223372036854775807, job.version)
            self.assertEqual(claimed.dialogue.state, (await DialogueRepository(storage).get_live()).state)

        await assert_overflow(2, setup_starting, operation_starting, verify_starting)

        async def setup_running(storage):
            _, repo, created = await self.job(storage, update=43)
            claimed = await repo.claim_turn(job_id=created.job.job_id, expected_job_version=0,
                                            expected_dialogue_version=1, thread_id="thread")
            starting = await repo.mark_codex_starting(job_id=created.job.job_id, expected_version=claimed.job.version)
            await storage.write(lambda c: (c.execute(
                "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (9223372036854775807, created.job.job_id)
            ), None)[1])
            return repo, created, starting

        async def operation_running(storage, context, clock):
            _, created, _ = context
            return await TurnJobRepository(storage, now_ms=clock).mark_codex_running(
                job_id=created.job.job_id, expected_version=9223372036854775807, codex_turn_id="turn")

        async def verify_running(storage, context):
            repo, created, starting = context
            job = await repo.get(created.job.job_id)
            self.assertEqual(TurnJobState.CODEX_STARTING, job.state)
            self.assertEqual(9223372036854775807, job.version)

        await assert_overflow(3, setup_running, operation_running, verify_running)

        async def setup_finish_job(storage):
            _, repo, created, claimed, running = await self.running_job(storage, update=44)
            await storage.write(lambda c: (c.execute(
                "UPDATE turn_jobs SET version = ? WHERE job_id = ?", (9223372036854775807, created.job.job_id)
            ), None)[1])
            return repo, created, claimed, running

        async def operation_finish_job(storage, context, clock):
            _, created, claimed, _ = context
            return await TurnJobRepository(storage, now_ms=clock).finish_codex(
                job_id=created.job.job_id, expected_job_version=9223372036854775807,
                expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED)

        async def verify_finish_job(storage, context):
            repo, created, _, _ = context
            self.assertEqual(TurnJobState.CODEX_RUNNING, (await repo.get(created.job.job_id)).state)

        await assert_overflow(4, setup_finish_job, operation_finish_job, verify_finish_job)

        async def setup_finish_dialogue(storage):
            _, repo, created, claimed, running = await self.running_job(storage, update=45)
            await storage.write(lambda c: (c.execute(
                "UPDATE dialogues SET version = ? WHERE dialogue_id = ?", (9223372036854775807, "d")
            ), None)[1])
            return repo, created, claimed, running

        async def operation_finish_dialogue(storage, context, clock):
            _, created, _, running = context
            return await TurnJobRepository(storage, now_ms=clock).finish_codex(
                job_id=created.job.job_id, expected_job_version=running.version,
                expected_dialogue_version=9223372036854775807, outcome=TurnTerminalOutcome.COMPLETED)

        async def verify_finish_dialogue(storage, context):
            repo, created, _, running = context
            self.assertEqual(running.version, (await repo.get(created.job.job_id)).version)
            self.assertEqual(9223372036854775807, (await DialogueRepository(storage).get_live()).version)

        await assert_overflow(5, setup_finish_dialogue, operation_finish_dialogue, verify_finish_dialogue)

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

    async def test_public_input_boundary_matrix(self):
        max_int = 9223372036854775807
        max_id = "i" * 128
        max_thread = "t" * 512
        max_model = "m" * 256
        max_effort = "e" * 64

        for index, (update_id, source_chat_id) in enumerate(((0, -9223372036854775808), (max_int, max_int))):
            storage = await self.open()
            try:
                dialogue_repo = DialogueRepository(storage, now_ms=lambda: 10)
                await dialogue_repo.create_intent(dialogue_id=max_id, server_id="s" * 128, profile_id="p" * 128)
                await dialogue_repo.confirm_created(dialogue_id=max_id, expected_version=0, thread_id=max_thread)
                result = await TurnJobRepository(storage, now_ms=lambda: 20).claim_ingress(
                    update_id=update_id, job_id=max_id, source_chat_id=source_chat_id,
                    source_message_id=0, dialogue_id=max_id, server_id="s" * 128, profile_id="p" * 128,
                    thread_id=max_thread, model_id=max_model, reasoning_effort=max_effort,
                    input_payload_id=max_id, input_content=b"x", input_expires_at_ms=30)
                self.assertIs(TurnIngressClaimStatus.CREATED, result.status)
            finally:
                await storage.close()
            self.path = os.path.join(self.tempdir.name, f"boundaries-{index + 1}.sqlite3")

        storage = await self.open()
        try:
            await self.dialogue(storage)
            calls = []
            repo = TurnJobRepository(storage, now_ms=lambda: calls.append(1) or 20)
            base = dict(
                update_id=100, job_id="job", source_chat_id=-1, source_message_id=1, dialogue_id="d",
                server_id="server", profile_id="profile", thread_id="thread", model_id="model",
                reasoning_effort="high", input_payload_id="payload", input_content=b"x",
                input_expires_at_ms=30,
            )
            invalid_claim_values = {
                "update_id": (True, -1, max_int + 1),
                "job_id": ("", "bad\x00id", "x" * 129),
                "source_chat_id": (0, True, -9223372036854775809, max_int + 1),
                "source_message_id": (-1, True, max_int + 1),
                "dialogue_id": ("", "bad\x00id", "x" * 129),
                "server_id": ("", "bad\x00id", "x" * 129),
                "profile_id": ("", "bad\x00id", "x" * 129),
                "thread_id": ("", "bad\x00id", "x" * 513),
                "model_id": ("", "bad\x00id", "x" * 257),
                "reasoning_effort": ("", "bad\x00id", "x" * 65),
                "input_payload_id": ("", "bad\x00id", "x" * 129),
                "input_expires_at_ms": (-1, True, max_int + 1),
            }
            for field, values in invalid_claim_values.items():
                for value in values:
                    with self.assertRaises(RepositoryError) as raised:
                        await repo.claim_ingress(**{**base, field: value})
                    self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            payload_repo = TransientPayloadRepository(storage)
            for field, values in (("payload_id", ("", "bad\x00id", "x" * 129)),
                                  ("job_id", ("", "bad\x00id", "x" * 129))):
                for value in values:
                    with self.assertRaises(RepositoryError) as raised:
                        await (payload_repo.get(value) if field == "payload_id" else payload_repo.get_input_for_job(value))
                    self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)

            for field, values in (
                ("expected_job_version", (True, -1, 1.5, max_int + 1)),
                ("expected_dialogue_version", (True, -1, 1.5, max_int + 1)),
                ("thread_id", ("", "bad\x00id", "x" * 513)),
            ):
                turn_args = dict(
                    job_id="missing", expected_job_version=0,
                    expected_dialogue_version=1, thread_id="thread",
                )
                for value in values:
                    with self.assertRaises(RepositoryError) as raised:
                        await repo.claim_turn(**{**turn_args, field: value})
                    self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            for version in (0, max_int):
                with self.assertRaises(RepositoryError) as raised:
                    await repo.claim_turn(
                        job_id="missing", expected_job_version=version,
                        expected_dialogue_version=version, thread_id="thread")
                self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            self.assertEqual([], calls)
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
