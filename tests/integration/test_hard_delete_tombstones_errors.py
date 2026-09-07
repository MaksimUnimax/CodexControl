import asyncio
import hashlib
import os
import sqlite3
import tempfile
import threading
import unittest

from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    ErrorFingerprintRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
)


MAX_SQLITE_INT = 9223372036854775807
THREAD_SENTINEL = "PRIVATE_THREAD_ID_MUST_NOT_SURVIVE_DELETE"


class HardDeleteTombstonesErrorsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self):
        return await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def write_sql(self, storage, sql, parameters=()):
        def write(connection):
            connection.execute(sql, parameters)
        await storage.write(write)

    async def fresh_storage(self):
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        return await self.open()

    async def dialogue(self, storage, *, thread_id=THREAD_SENTINEL):
        repo = DialogueRepository(storage, now_ms=lambda: 10)
        await repo.create_intent(dialogue_id="d", server_id="server", profile_id="profile")
        return await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id=thread_id)

    async def delete_claimed(self, storage, *, clock=lambda: 20):
        current = await self.dialogue(storage)
        repo = DeletionRepository(storage, now_ms=clock)
        pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
        deleting = await repo.claim_deleting(dialogue_id="d", expected_version=pending.version)
        return repo, deleting

    async def insert_job(self, storage, state, *, job_id="job", error_class=None, delivery=False):
        shape = {
            "RECEIVED": (None, None, None),
            "CLAIMED": (THREAD_SENTINEL, None, None),
            "CODEX_STARTING": (THREAD_SENTINEL, None, None),
            "CODEX_RUNNING": (THREAD_SENTINEL, "turn", None),
            "CODEX_COMPLETED": (THREAD_SENTINEL, "turn", None),
            "UNKNOWN": (THREAD_SENTINEL, None, "ERR"),
            "DELIVERY_PENDING": (THREAD_SENTINEL, "turn", None),
            "DELIVERING": (THREAD_SENTINEL, "turn", None),
            "DELIVERY_UNKNOWN": (THREAD_SENTINEL, "turn", "ERR"),
            "FAILED": (THREAD_SENTINEL, "turn" if delivery else None, error_class or "ERR"),
            "DELIVERED": (THREAD_SENTINEL, "turn", None),
        }
        thread_id, codex_turn_id, stored_error = shape[state]
        await self.write_sql(
            storage,
            "INSERT INTO turn_jobs "
            "(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
            "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
            "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
            "VALUES (?, ?, -100, 1, 'd', 'server', 'profile', ?, 'model', 'high', ?, ?, ?, 0, 1, 1, ?)",
            (job_id, abs(hash(job_id)) % 1000000, thread_id, "a" * 64, codex_turn_id, state, stored_error),
        )

    async def insert_terminal_job_with_segments(self, storage, job_state, segment_states):
        await self.insert_job(storage, job_state, delivery=bool(segment_states))
        digest = hashlib.sha256(b"display").hexdigest()
        for sequence, segment_state in enumerate(segment_states, 1):
            payload_id = f"display-{sequence}" if segment_state in ("PENDING", "SENDING", "UNKNOWN") else None
            if payload_id is not None:
                await self.write_sql(
                    storage,
                    "INSERT INTO transient_payloads VALUES (?, 'd', 'job', 'DISPLAY', ?, ?, 7, 1, 100)",
                    (payload_id, b"display", digest),
                )
            attempt_count = 0 if segment_state == "PENDING" else 1
            confirmed_message_id = 10 + sequence if segment_state == "CONFIRMED" else None
            await self.write_sql(
                storage,
                "INSERT INTO delivery_segments VALUES ('job', ?, 'CREATE', NULL, ?, ?, ?, ?, ?, 1, 1)",
                (sequence, payload_id, digest, segment_state, attempt_count, confirmed_message_id),
            )

    async def corrupt_segment_to_active_state(self, storage, state):
        digest = hashlib.sha256(b"corrupt").hexdigest()
        await self.write_sql(
            storage,
            "INSERT INTO transient_payloads VALUES ('corrupt-display', 'd', 'job', 'DISPLAY', ?, ?, 7, 1, 100)",
            (b"corrupt", digest),
        )
        await self.write_sql(
            storage,
            "UPDATE delivery_segments SET payload_id = 'corrupt-display', payload_sha256 = ?, state = ?, "
            "attempt_count = 1, confirmed_message_id = NULL WHERE job_id = 'job' AND sequence = 1",
            (digest, state),
        )

    async def test_public_surfaces_and_input_validation(self):
        self.assertEqual(
            {"get_tombstone", "claim_delete_intent", "claim_deleting", "mark_delete_unknown",
             "mark_delete_error", "finalize_confirmed"},
            {name for name, value in vars(DeletionRepository).items() if not name.startswith("_") and callable(value)},
        )
        self.assertEqual(
            {"get", "record", "latest"},
            {name for name, value in vars(ErrorFingerprintRepository).items() if not name.startswith("_") and callable(value)},
        )
        storage = await self.open()
        try:
            deletion = DeletionRepository(storage)
            errors = ErrorFingerprintRepository(storage)
            for bad in ("", "x\x00y", "x" * 129, True, 1):
                with self.assertRaises(RepositoryError) as raised:
                    await deletion.get_tombstone(bad)
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            for bad in ("A" * 64, "g" * 64, "a" * 63, "a" * 65, ""):
                with self.assertRaises(RepositoryError):
                    await errors.get(bad)
            with self.assertRaises(RepositoryError):
                await errors.record(fingerprint_sha256="a" * 64, error_class="raw prose")
        finally:
            await storage.close()

    async def test_zero_jobs_terminal_history_and_full_readiness_matrix(self):
        storage = await self.open()
        try:
            current = await self.dialogue(storage)
            repo = DeletionRepository(storage, now_ms=lambda: 20)
            pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
            self.assertEqual(DialogueState.DELETE_PENDING, pending.state)
            self.assertEqual(20, pending.updated_at_ms)
        finally:
            await storage.close()

        for state, segment_states in (
            ("DELIVERED", ("CONFIRMED",)),
            ("FAILED", ()),
            ("FAILED", ("FAILED",)),
            ("FAILED", ("CONFIRMED", "FAILED")),
            ("FAILED", ("CONFIRMED", "FAILED", "PENDING")),
        ):
            storage = await self.fresh_storage()
            try:
                current = await self.dialogue(storage)
                await self.insert_terminal_job_with_segments(storage, state, segment_states)
                result = await DeletionRepository(storage, now_ms=lambda: 20).claim_delete_intent(
                    dialogue_id="d", expected_version=current.version
                )
                self.assertEqual(DialogueState.DELETE_PENDING, result.state)
            finally:
                await storage.close()

        for state, segment_states in (
            ("DELIVERED", ()),
            ("DELIVERED", ("SENDING",)),
            ("DELIVERED", ("UNKNOWN",)),
            ("FAILED", ("PENDING", "FAILED")),
            ("FAILED", ("FAILED", "CONFIRMED")),
            ("FAILED", ("FAILED", "FAILED")),
            ("FAILED", ("CONFIRMED", "FAILED", "CONFIRMED")),
        ):
            storage = await self.fresh_storage()
            clock_calls = []
            try:
                current = await self.dialogue(storage)
                await self.insert_terminal_job_with_segments(storage, state, segment_states)

                def failing_clock():
                    clock_calls.append(True)
                    raise AssertionError("clock must not be called")

                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage, now_ms=failing_clock).claim_delete_intent(
                        dialogue_id="d", expected_version=current.version
                    )
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], clock_calls)
                self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)
                self.assertIsNone(await DeletionRepository(storage).get_tombstone("d"))
            finally:
                await storage.close()

        for state in (
            "RECEIVED", "CLAIMED", "CODEX_STARTING", "CODEX_RUNNING", "CODEX_COMPLETED",
            "UNKNOWN", "DELIVERY_PENDING", "DELIVERING", "DELIVERY_UNKNOWN",
        ):
            storage = await self.fresh_storage()
            try:
                current = await self.dialogue(storage)
                await self.insert_job(storage, state)
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).claim_delete_intent(
                        dialogue_id="d", expected_version=current.version
                    )
                self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            finally:
                await storage.close()

    async def test_delivery_coherence_remains_a_gate_after_delete_state_changes(self):
        for target_state in ("DELETE_PENDING", "DELETING"):
            storage = await self.fresh_storage()
            clock_calls = []
            try:
                current = await self.dialogue(storage)
                await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
                repo = DeletionRepository(storage, now_ms=lambda: 20)
                pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
                if target_state == "DELETE_PENDING":
                    expected_version = pending.version
                else:
                    deleting = await repo.claim_deleting(dialogue_id="d", expected_version=pending.version)
                    expected_version = deleting.version
                await self.corrupt_segment_to_active_state(storage, "SENDING")

                def failing_clock():
                    clock_calls.append(True)
                    raise AssertionError("clock must not be called")

                gated_repo = DeletionRepository(storage, now_ms=failing_clock)
                if target_state == "DELETE_PENDING":
                    with self.assertRaises(RepositoryError) as raised:
                        await gated_repo.claim_deleting(dialogue_id="d", expected_version=expected_version)
                    self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                    self.assertEqual(DialogueState.DELETE_PENDING, (await DialogueRepository(storage).get_live()).state)
                else:
                    with self.assertRaises(RepositoryError) as raised:
                        await gated_repo.finalize_confirmed(
                            dialogue_id="d", expected_version=expected_version, tombstone_expires_at_ms=100
                        )
                    self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                    self.assertEqual(DialogueState.DELETING, (await DialogueRepository(storage).get_live()).state)
                    self.assertIsNone(await gated_repo.get_tombstone("d"))
                self.assertEqual([], clock_calls)
            finally:
                await storage.close()

    async def test_tombstone_collision_is_blocked_before_delete_effect_boundary(self):
        storage = await self.open()
        try:
            current = await self.dialogue(storage)
            await self.write_sql(storage, "INSERT INTO deletion_tombstones VALUES ('d', ?, 1, 1, 100)", ("a" * 64,))
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=failing_clock).claim_delete_intent(
                    dialogue_id="d", expected_version=current.version
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], clock_calls)
            self.assertEqual(DialogueState.IDLE, (await DialogueRepository(storage).get_live()).state)
            self.assertIsNotNone(await DeletionRepository(storage).get_tombstone("d"))
        finally:
            await storage.close()

        storage = await self.fresh_storage()
        try:
            current = await self.dialogue(storage)
            repo = DeletionRepository(storage, now_ms=lambda: 20)
            pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
            await self.write_sql(storage, "INSERT INTO deletion_tombstones VALUES ('d', ?, 1, 1, 100)", ("b" * 64,))
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=failing_clock).claim_deleting(
                    dialogue_id="d", expected_version=pending.version
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], clock_calls)
            self.assertEqual(DialogueState.DELETE_PENDING, (await DialogueRepository(storage).get_live()).state)
            self.assertIsNotNone(await repo.get_tombstone("d"))
        finally:
            await storage.close()

    async def test_pending_approval_blocks_without_clock_and_concurrent_intent_has_one_winner(self):
        storage = await self.open()
        try:
            current = await self.dialogue(storage)
            await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
            await self.write_sql(storage,
                "INSERT INTO approvals "
                "(approval_id, profile_id, wire_request_id_type, wire_request_id_int, wire_request_id_text, "
                "job_id, kind, display_payload_id, state, created_at_ms, updated_at_ms, expires_at_ms) "
                "VALUES ('approval', 'profile', 'INTEGER', 1, NULL, 'job', 'command_execution', NULL, 'PENDING', 1, 1, 100)"
            )
            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).claim_delete_intent(
                    dialogue_id="d", expected_version=current.version
                )
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            await self.write_sql(storage, "DELETE FROM approvals")
            results = await asyncio.gather(
                DeletionRepository(storage, now_ms=lambda: 20).claim_delete_intent(dialogue_id="d", expected_version=current.version),
                DeletionRepository(storage, now_ms=lambda: 21).claim_delete_intent(dialogue_id="d", expected_version=current.version),
                return_exceptions=True,
            )
            self.assertEqual(1, sum(not isinstance(item, Exception) for item in results))
            self.assertEqual(1, sum(
                isinstance(item, RepositoryError)
                and item.category in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT)
                for item in results
            ))
        finally:
            await storage.close()

    async def test_claim_deleting_persists_exact_binding_and_unknown_error_are_terminal(self):
        storage = await self.open()
        try:
            current = await self.dialogue(storage)
            repo = DeletionRepository(storage, now_ms=lambda: 20)
            pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
            await storage.close()
            storage = await self.open()
            repo = DeletionRepository(storage, now_ms=lambda: 30)
            deleting = await repo.claim_deleting(dialogue_id="d", expected_version=pending.version)
            self.assertEqual(THREAD_SENTINEL, deleting.thread_id)
            self.assertEqual("profile", deleting.profile_id)
            await storage.close()
            storage = await self.open()
            repo = DeletionRepository(storage, now_ms=lambda: 40)
            unknown = await repo.mark_delete_unknown(dialogue_id="d", expected_version=deleting.version, error_class="DELETE_UNKNOWN")
            self.assertEqual(DialogueState.DELETE_UNKNOWN, unknown.state)
            self.assertEqual(THREAD_SENTINEL, unknown.thread_id)
            self.assertIsNone(await repo.get_tombstone("d"))
            with self.assertRaises(RepositoryError) as raised:
                await repo.claim_deleting(dialogue_id="d", expected_version=unknown.version)
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_mark_delete_error_and_invalid_preconditions_do_not_call_clock(self):
        storage = await self.open()
        try:
            repo, deleting = await self.delete_claimed(storage)
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_delete_error(dialogue_id="d", expected_version=deleting.version, error_class="raw prose")
            self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            error = await DeletionRepository(storage, now_ms=lambda: 30).mark_delete_error(
                dialogue_id="d", expected_version=deleting.version, error_class="LOCAL:failure"
            )
            self.assertEqual(DialogueState.ERROR, error.state)
            self.assertEqual(THREAD_SENTINEL, error.thread_id)
            self.assertIsNone(await repo.get_tombstone("d"))
        finally:
            await storage.close()

    async def test_finalize_hash_counts_cascades_refs_and_metadata_preservation(self):
        storage = await self.open()
        try:
            repo, deleting = await self.delete_claimed(storage)
            await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
            digest = hashlib.sha256(b"x").hexdigest()
            def write_children(connection):
                connection.execute("INSERT INTO transient_payloads VALUES ('p-dialogue', 'd', NULL, 'DISPLAY', X'78', ?, 1, 1, 100)", (digest,))
                connection.execute("INSERT INTO transient_payloads VALUES ('p-job', NULL, 'job', 'OUTPUT', X'78', ?, 1, 1, 100)", (digest,))
                connection.execute("INSERT INTO transient_payloads VALUES ('p-both', 'd', 'job', 'OUTPUT', X'78', ?, 1, 1, 100)", (digest,))
                connection.execute("INSERT INTO approvals VALUES ('approval', 'profile', 'INTEGER', 1, NULL, 'job', 'command_execution', NULL, 'DENIED', 1, 1, 100)")
                connection.execute("INSERT INTO errors VALUES (?, 'STORAGE:failure', 2, 2, 5, 'd', 'job')", ('b' * 64,))
                connection.execute("INSERT INTO ingress_updates VALUES (7, 1, 1, 'JOB:job')")
                connection.execute("INSERT INTO callback_actions VALUES (?, 'action', 'subject', 'job', 1, 'STATE', 1, -100, 1, 100, NULL)", ('c' * 64,))
            await storage.write(write_children)
            result = await repo.finalize_confirmed(dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100)
            self.assertEqual(1, result.purged_jobs)
            self.assertEqual(3, result.purged_payloads)
            self.assertEqual(1, result.purged_delivery_segments)
            self.assertEqual(1, result.purged_approvals)
            self.assertEqual(hashlib.sha256(THREAD_SENTINEL.encode()).hexdigest(), result.tombstone.thread_identity_sha256)
            self.assertNotIn(THREAD_SENTINEL, repr(result))
            await storage.close()
            storage = await self.open()
            repo = DeletionRepository(storage)
            self.assertIsNone(await DialogueRepository(storage).get_live())
            self.assertEqual(result.tombstone, await repo.get_tombstone("d"))
            rows = await storage.read(lambda c: [tuple(row) for row in c.execute(
                "SELECT dialogue_id, job_id, count, first_seen_at_ms, last_seen_at_ms, error_class FROM errors"
            ).fetchall()])
            self.assertEqual([(None, None, 2, 2, 5, "STORAGE:failure")], rows)
            self.assertEqual(1, await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))
            self.assertEqual(1, await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        finally:
            await storage.close()

    async def test_finalize_failure_paths_roll_back_atomically(self):
        for mode in ("expiry", "clock"):
            storage = await self.fresh_storage()
            try:
                repo, deleting = await self.delete_claimed(storage)
                if mode == "clock":
                    repo = DeletionRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_ERROR_BODY_MUST_NOT_LEAK")))
                    expiry = 100
                else:
                    repo = DeletionRepository(storage, now_ms=lambda: 20)
                    expiry = 20
                with self.assertRaises(RepositoryError) as raised:
                    await repo.finalize_confirmed(dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=expiry)
                expected = RepositoryErrorCategory.CLOCK_INVALID if mode == "clock" else RepositoryErrorCategory.INVALID_ARGUMENT
                self.assertIs(expected, raised.exception.category)
                self.assertEqual(deleting, await DialogueRepository(storage).get_live())
                self.assertIsNone(await repo.get_tombstone("d"))
            finally:
                await storage.close()

        storage = await self.fresh_storage()
        try:
            repo, deleting = await self.delete_claimed(storage)
            await self.write_sql(storage,
                "INSERT INTO deletion_tombstones VALUES ('d', ?, 1, 1, 100)", ('a' * 64,)
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.finalize_confirmed(dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual(deleting, await DialogueRepository(storage).get_live())
        finally:
            await storage.close()

    async def test_finalize_repeated_cancellation_is_owned_and_single(self):
        storage = await self.open()
        started = threading.Event()
        release = threading.Event()

        def blocked_clock():
            started.set()
            release.wait(5)
            return 20

        try:
            repo, deleting = await self.delete_claimed(storage)
            await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
            repo = DeletionRepository(storage, now_ms=blocked_clock)
            task = asyncio.create_task(repo.finalize_confirmed(
                dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100
            ))
            await asyncio.to_thread(started.wait, 2)
            self.assertTrue(started.is_set())
            for _ in range(5):
                task.cancel()
                await asyncio.sleep(0)
            release.set()
            result = await task
            self.assertEqual(1, result.purged_jobs)
            self.assertEqual(1, await storage.read(lambda c: c.execute("SELECT COUNT(*) FROM deletion_tombstones").fetchone()[0]))
        finally:
            release.set()
            await storage.close()

    async def test_finalize_binds_exact_stale_generation_and_accepts_max_version(self):
        storage = await self.open()
        try:
            repo, deleting = await self.delete_claimed(storage)
            result = await repo.finalize_confirmed(
                dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100
            )
            self.assertEqual(deleting.version, result.tombstone.stale_generation)
            persisted = await repo.get_tombstone("d")
            self.assertEqual(deleting.version, persisted.stale_generation)
        finally:
            await storage.close()

        storage = await self.fresh_storage()
        try:
            await self.dialogue(storage)
            await self.write_sql(
                storage,
                "UPDATE dialogues SET state = 'DELETING', version = ?, last_error_class = NULL WHERE dialogue_id = 'd'",
                (MAX_SQLITE_INT,),
            )
            repo = DeletionRepository(storage, now_ms=lambda: 20)
            result = await repo.finalize_confirmed(
                dialogue_id="d", expected_version=MAX_SQLITE_INT, tombstone_expires_at_ms=100
            )
            self.assertEqual(MAX_SQLITE_INT, result.tombstone.stale_generation)
            self.assertEqual(MAX_SQLITE_INT, (await repo.get_tombstone("d")).stale_generation)
        finally:
            await storage.close()

    async def test_finalize_preconditions_are_exact_and_do_not_call_clock(self):
        storage = await self.open()
        try:
            repo, deleting = await self.delete_claimed(storage)
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=failing_clock).finalize_confirmed(
                    dialogue_id="d", expected_version=deleting.version - 1, tombstone_expires_at_ms=100
                )
            self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            self.assertEqual([], clock_calls)
            self.assertEqual(deleting, await DialogueRepository(storage).get_live())
            self.assertIsNone(await repo.get_tombstone("d"))
        finally:
            await storage.close()

        storage = await self.fresh_storage()
        try:
            current = await self.dialogue(storage)
            repo = DeletionRepository(storage, now_ms=lambda: 20)
            pending = await repo.claim_delete_intent(dialogue_id="d", expected_version=current.version)
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=failing_clock).finalize_confirmed(
                    dialogue_id="d", expected_version=pending.version, tombstone_expires_at_ms=100
                )
            self.assertIs(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
            self.assertEqual([], clock_calls)
            self.assertEqual(pending, await DialogueRepository(storage).get_live())
            self.assertIsNone(await repo.get_tombstone("d"))
        finally:
            await storage.close()

        storage = await self.fresh_storage()
        try:
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await DeletionRepository(storage, now_ms=failing_clock).finalize_confirmed(
                    dialogue_id="missing", expected_version=0, tombstone_expires_at_ms=100
                )
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            self.assertEqual([], clock_calls)
        finally:
            await storage.close()

    async def test_delete_transition_version_overflow_matrix_is_fail_closed(self):
        cases = (
            ("IDLE", "claim_delete_intent"),
            ("DELETE_PENDING", "claim_deleting"),
            ("DELETING", "mark_delete_unknown"),
            ("DELETING", "mark_delete_error"),
        )
        for state, method_name in cases:
            storage = await self.fresh_storage()
            try:
                await self.dialogue(storage)
                await self.write_sql(
                    storage,
                    "UPDATE dialogues SET state = ?, version = ?, last_error_class = ? WHERE dialogue_id = 'd'",
                    (state, MAX_SQLITE_INT, None),
                )
                before = await DialogueRepository(storage).get_live()
                clock_calls = []

                def failing_clock():
                    clock_calls.append(True)
                    raise AssertionError("clock must not be called")

                repo = DeletionRepository(storage, now_ms=failing_clock)
                kwargs = {"dialogue_id": "d", "expected_version": MAX_SQLITE_INT}
                if method_name in ("mark_delete_unknown", "mark_delete_error"):
                    kwargs["error_class"] = "E"
                with self.assertRaises(RepositoryError) as raised:
                    await getattr(repo, method_name)(**kwargs)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], clock_calls)
                self.assertEqual(before, await DialogueRepository(storage).get_live())
            finally:
                await storage.close()

    async def test_deletion_numeric_input_boundaries_are_distinct_from_expiry_relation(self):
        storage = await self.open()
        try:
            current = await self.dialogue(storage)
            clock_calls = []

            def failing_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            for value in (True, False, -1, 1.5, MAX_SQLITE_INT + 1):
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage, now_ms=failing_clock).claim_delete_intent(
                        dialogue_id="d", expected_version=value
                    )
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            for value in (0, MAX_SQLITE_INT):
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage, now_ms=failing_clock).claim_delete_intent(
                        dialogue_id="d", expected_version=value
                    )
                self.assertIs(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            self.assertEqual([], clock_calls)
        finally:
            await storage.close()

        for value in (True, False, -1, 1.5, MAX_SQLITE_INT + 1):
            storage = await self.fresh_storage()
            try:
                _, deleting = await self.delete_claimed(storage)
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage, now_ms=lambda: 20).finalize_confirmed(
                        dialogue_id="d", expected_version=deleting.version,
                        tombstone_expires_at_ms=value,
                    )
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            finally:
                await storage.close()

        for value in (0, MAX_SQLITE_INT):
            storage = await self.fresh_storage()
            try:
                _, deleting = await self.delete_claimed(storage)
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(
                        storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))
                    ).finalize_confirmed(
                        dialogue_id="d", expected_version=deleting.version,
                        tombstone_expires_at_ms=value,
                    )
                self.assertIs(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            finally:
                await storage.close()

    async def test_error_first_duplicate_references_concurrency_and_overflow(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
            repo = ErrorFingerprintRepository(storage, now_ms=lambda: 10)
            first = await repo.record(fingerprint_sha256="a" * 64, error_class="STORAGE:failure", dialogue_id="d", job_id="job")
            duplicate = await ErrorFingerprintRepository(storage, now_ms=lambda: 5).record(
                fingerprint_sha256="a" * 64, error_class="STORAGE:failure", dialogue_id="d", job_id="job"
            )
            self.assertEqual(2, duplicate.count)
            self.assertEqual(first.first_seen_at_ms, duplicate.first_seen_at_ms)
            self.assertEqual(10, duplicate.last_seen_at_ms)
            with self.assertRaises(RepositoryError) as raised:
                await ErrorFingerprintRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).record(
                    fingerprint_sha256="a" * 64, error_class="OTHER", dialogue_id="d", job_id="job"
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            results = await asyncio.gather(
                ErrorFingerprintRepository(storage, now_ms=lambda: 20).record(fingerprint_sha256="b" * 64, error_class="E"),
                ErrorFingerprintRepository(storage, now_ms=lambda: 21).record(fingerprint_sha256="b" * 64, error_class="E"),
            )
            self.assertEqual({1, 2}, {item.count for item in results})
            await self.write_sql(storage, "UPDATE errors SET count = ? WHERE fingerprint_sha256 = ?", (MAX_SQLITE_INT, "a" * 64))
            with self.assertRaises(RepositoryError) as raised:
                await ErrorFingerprintRepository(storage, now_ms=lambda: (_ for _ in ()).throw(RuntimeError("CLOCK"))).record(
                    fingerprint_sha256="a" * 64, error_class="STORAGE:failure", dialogue_id="d", job_id="job"
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        finally:
            await storage.close()

    async def test_error_fingerprint_case_aliases_are_unique_semantically(self):
        storage = await self.open()
        try:
            await self.write_sql(
                storage,
                "INSERT INTO errors VALUES (?, 'E', 1, 2, 3, NULL, NULL)",
                ("A" * 64,),
            )
            with self.assertRaises(RepositoryError) as raised:
                await ErrorFingerprintRepository(storage).get("a" * 64)
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("A" * 64, repr(raised.exception))
        finally:
            await storage.close()

        for order in (("a" * 64, "A" * 64), ("A" * 64, "a" * 64)):
            storage = await self.fresh_storage()
            try:
                await self.dialogue(storage)
                await self.insert_job(storage, "DELIVERED")
                for fingerprint in order:
                    await self.write_sql(
                        storage,
                        "INSERT INTO errors VALUES (?, 'E', 1, 2, 3, 'd', 'job')",
                        (fingerprint,),
                    )
                with self.assertRaises(RepositoryError) as raised:
                    await ErrorFingerprintRepository(storage).get("a" * 64)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                before = await storage.read(lambda c: [tuple(row) for row in c.execute(
                    "SELECT fingerprint_sha256, count FROM errors ORDER BY rowid"
                ).fetchall()])
                clock_calls = []

                def no_clock():
                    clock_calls.append(True)
                    raise AssertionError("clock must not be called")

                with self.assertRaises(RepositoryError) as raised:
                    await ErrorFingerprintRepository(storage, now_ms=no_clock).record(
                        fingerprint_sha256="a" * 64, error_class="E", dialogue_id="d", job_id="job"
                    )
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertEqual([], clock_calls)
                self.assertEqual(before, await storage.read(lambda c: [tuple(row) for row in c.execute(
                    "SELECT fingerprint_sha256, count FROM errors ORDER BY rowid"
                ).fetchall()]))
            finally:
                await storage.close()

    async def test_error_entity_coherence_and_post_delete_fk_clearing(self):
        storage = await self.open()
        try:
            await self.dialogue(storage)
            await self.insert_terminal_job_with_segments(storage, "DELIVERED", ("CONFIRMED",))
            repo = ErrorFingerprintRepository(storage, now_ms=lambda: 10)
            with self.assertRaises(RepositoryError) as raised:
                await repo.record(fingerprint_sha256="a" * 64, error_class="E", dialogue_id="missing")
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            await repo.record(fingerprint_sha256="a" * 64, error_class="E", dialogue_id="d", job_id="job")
            clock_calls = []

            def no_clock():
                clock_calls.append(True)
                raise AssertionError("clock must not be called")

            with self.assertRaises(RepositoryError) as raised:
                await ErrorFingerprintRepository(storage, now_ms=no_clock).record(
                    fingerprint_sha256="a" * 64, error_class="E"
                )
            self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], clock_calls)
            self.assertEqual(1, (await repo.get("a" * 64)).count)
            with self.assertRaises(RepositoryError) as raised:
                await repo.record(fingerprint_sha256="b" * 64, error_class="E", dialogue_id="d", job_id="other")
            self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            deletion = DeletionRepository(storage, now_ms=lambda: 20)
            deleting = await deletion.claim_delete_intent(
                dialogue_id="d", expected_version=(await DialogueRepository(storage).get_live()).version
            )
            deleting = await deletion.claim_deleting(dialogue_id="d", expected_version=deleting.version)
            await deletion.finalize_confirmed(dialogue_id="d", expected_version=deleting.version, tombstone_expires_at_ms=100)
            record = await repo.get("a" * 64)
            self.assertEqual((None, None, 1, "E"), (record.dialogue_id, record.job_id, record.count, record.error_class))
        finally:
            await storage.close()

    async def test_corrupt_tombstones_errors_and_global_delete_shapes_fail_closed(self):
        tombstone_cases = (
            ("thread_identity_sha256", "A" * 64),
            ("stale_generation", 1.5),
            ("expires_at_ms", 10),
        )
        for column, value in tombstone_cases:
            storage = await self.fresh_storage()
            try:
                await self.write_sql(storage,
                    "INSERT INTO deletion_tombstones VALUES ('d', ?, 1, 10, 20)", ('a' * 64,)
                )
                await storage.close()
                with sqlite3.connect(self.path) as connection:
                    connection.execute(f"UPDATE deletion_tombstones SET {column} = ?", (value,))
                    connection.commit()
                storage = await self.open()
                with self.assertRaises(RepositoryError) as raised:
                    await DeletionRepository(storage).get_tombstone("d")
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn(str(value), repr(raised.exception))
            finally:
                await storage.close()

        error_cases = (
            ("fingerprint_sha256", "A" * 64),
            ("error_class", "raw prose"),
            ("count", 1.5),
            ("first_seen_at_ms", 1.5),
            ("last_seen_at_ms", 1),
        )
        for column, value in error_cases:
            storage = await self.fresh_storage()
            try:
                await self.write_sql(storage,
                    "INSERT INTO errors VALUES (?, 'E', 1, 2, 3, NULL, NULL)", ('a' * 64,)
                )
                await storage.close()
                with sqlite3.connect(self.path) as connection:
                    connection.execute("PRAGMA ignore_check_constraints = ON")
                    connection.execute(f"UPDATE errors SET {column} = ?", (value,))
                    connection.commit()
                storage = await self.open()
                with self.assertRaises(RepositoryError) as raised:
                    await ErrorFingerprintRepository(storage).get("a" * 64)
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn(str(value), repr(raised.exception))
            finally:
                await storage.close()

        for state, thread_id, error_class in (
            ("DELETE_PENDING", None, None), ("DELETE_PENDING", "thread", "E"),
            ("DELETING", None, None), ("DELETING", "thread", "E"),
            ("DELETE_UNKNOWN", None, "E"), ("DELETE_UNKNOWN", "thread", None),
            ("DELETE_UNKNOWN", "thread", "raw prose"),
        ):
            storage = await self.fresh_storage()
            try:
                await self.dialogue(storage, thread_id="thread")
                await self.write_sql(storage,
                    "UPDATE dialogues SET state = ?, thread_id = ?, last_error_class = ? WHERE dialogue_id = 'd'",
                    (state, thread_id, error_class),
                )
                with self.assertRaises(RepositoryError) as raised:
                    await DialogueRepository(storage).get_live()
                self.assertIs(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
                self.assertNotIn("raw prose", repr(raised.exception))
            finally:
                await storage.close()


if __name__ == "__main__":
    unittest.main()
