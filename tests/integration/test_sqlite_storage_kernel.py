import asyncio
import os
import sqlite3
import stat
import tempfile
import threading
import unittest
import warnings
from unittest import mock

from codex_control.storage import SqliteStorage, StorageError, StorageErrorCategory


HASH = "a" * 64


class StorageKernelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self, **kwargs):
        return await SqliteStorage.open(self.path, **kwargs)

    async def valid_dialogue(self, storage, dialogue_id="d1"):
        await storage.write(lambda c: (c.execute(
            "INSERT INTO dialogues(dialogue_id, server_id, profile_id, state, version, created_at_ms, updated_at_ms) "
            "VALUES (?, 'server', 'profile', 'IDLE', 0, 1, 1)", (dialogue_id,)
        ), None)[1])

    async def valid_job(self, storage, job_id="j1", dialogue_id="d1"):
        await storage.write(lambda c: (c.execute(
            "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
            "server_id, profile_id, input_sha256, state, version, created_at_ms, updated_at_ms) "
            "VALUES (?, 1, 2, 3, ?, 'server', 'profile', ?, 'RECEIVED', 0, 1, 1)",
            (job_id, dialogue_id, HASH)
        ), None)[1])

    async def assert_storage_category(self, awaitable, category):
        with self.assertRaises(StorageError) as raised:
            await awaitable
        self.assertEqual(category, raised.exception.category)

    async def test_pragma_contract_and_connection_thread_ownership(self):
        storage = await self.open(now_ms=lambda: 10)
        try:
            loop_thread = threading.get_ident()
            values = await storage.read(lambda c: (
                c.execute("PRAGMA foreign_keys").fetchone()[0],
                c.execute("PRAGMA journal_mode").fetchone()[0],
                c.execute("PRAGMA busy_timeout").fetchone()[0],
                c.execute("PRAGMA synchronous").fetchone()[0],
                c.execute("PRAGMA trusted_schema").fetchone()[0],
                c.isolation_level,
                c.row_factory,
                threading.get_ident(),
            ))
            self.assertEqual((1, "wal", 5000, 2, 0, None, sqlite3.Row), values[:-1])
            self.assertNotEqual(loop_thread, values[-1])
            thread_ids = await asyncio.gather(*[
                storage.read(lambda c: threading.get_ident()) for _ in range(8)
            ])
            self.assertEqual({values[-1]}, set(thread_ids))
        finally:
            await storage.close()

    async def test_read_is_readonly_and_restores_query_only(self):
        storage = await self.open(now_ms=lambda: 1)
        try:
            def read_callback(connection):
                self.assertEqual(1, connection.execute("PRAGMA query_only").fetchone()[0])
                connection.execute("SELECT 1").fetchone()
                connection.execute("CREATE TABLE should_rollback (value TEXT)")

            await self.assert_storage_category(storage.read(read_callback), StorageErrorCategory.TRANSACTION_FAILED)
            self.assertEqual(0, await storage.write(lambda c: c.execute("PRAGMA query_only").fetchone()[0]))
            self.assertEqual(1, await storage.write(lambda c: c.execute("SELECT 1").fetchone()[0]))
        finally:
            await storage.close()

    async def test_write_commit_materializes_value(self):
        storage = await self.open(now_ms=lambda: 1)
        try:
            result = await storage.write(lambda c: (
                c.execute("INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (1, 1, 'CONTROL')"),
                "materialized",
            )[1])
            self.assertEqual("materialized", result)
            self.assertEqual(1, await storage.read(lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id=1"
            ).fetchone()[0]))
        finally:
            await storage.close()

    async def test_write_callback_exception_rolls_back_and_propagates_exact_exception(self):
        storage = await self.open(now_ms=lambda: 1)
        marker = RuntimeError("application marker")
        try:
            def callback(c):
                c.execute("INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (2, 1, 'CONTROL')")
                raise marker

            with self.assertRaises(RuntimeError) as raised:
                await storage.write(callback)
            self.assertIs(marker, raised.exception)
            self.assertEqual(0, await storage.read(lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id=2"
            ).fetchone()[0]))
        finally:
            await storage.close()

    async def test_write_sqlite_error_rolls_back_and_redacts(self):
        storage = await self.open(now_ms=lambda: 1)
        try:
            def callback(c):
                c.execute("INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (3, 1, 'CONTROL')")
                c.execute("INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (3, 1, 'CONTROL')")

            with self.assertRaises(StorageError) as raised:
                await storage.write(callback)
            self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)
            self.assertNotIn("UNIQUE", str(raised.exception).upper())
            self.assertNotIn("PRIVATE_SQL_MUST_NOT_LEAK", repr(raised.exception))
            self.assertEqual(0, await storage.read(lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id=3"
            ).fetchone()[0]))
        finally:
            await storage.close()

    async def test_connection_cursor_and_row_escape_are_rejected(self):
        storage = await self.open(now_ms=lambda: 1)
        try:
            for escaped in (
                lambda c: c,
                lambda c: c.execute("SELECT 1"),
                lambda c: c.execute("SELECT 1").fetchone(),
            ):
                with self.subTest(escaped=escaped):
                    with self.assertRaises(StorageError) as raised:
                        await storage.write(escaped)
                    self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)
        finally:
            await storage.close()

    async def test_async_and_lazy_callback_results_are_rejected_and_closed(self):
        storage = await self.open(now_ms=lambda: 1)
        calls = 0
        try:
            async def obvious_async_callback(_connection):
                raise AssertionError("async callback body must not run")

            with self.assertRaises(StorageError) as raised:
                await storage.write(obvious_async_callback)
            self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)

            def coroutine_result(connection):
                nonlocal calls
                calls += 1
                connection.execute(
                    "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) "
                    "VALUES (20, 1, 'CONTROL')"
                )

                async def captures_connection():
                    connection.execute("SELECT 1")
                    return "must not escape"

                return captures_connection()

            with warnings.catch_warnings(record=True) as warning_records:
                warnings.simplefilter("always")
                with self.assertRaises(StorageError) as raised:
                    await storage.write(coroutine_result)
            self.assertFalse(any(item.category is RuntimeWarning for item in warning_records))
            self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)
            self.assertEqual(1, calls)
            self.assertEqual(
                0,
                await storage.read(lambda c: c.execute(
                    "SELECT count(*) FROM ingress_updates WHERE update_id=20"
                ).fetchone()[0]),
            )

            def generator_result(connection):
                connection.execute(
                    "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) "
                    "VALUES (21, 1, 'CONTROL')"
                )

                def captures_connection():
                    yield connection.execute("SELECT 1").fetchone()[0]

                return captures_connection()

            with self.assertRaises(StorageError) as raised:
                await storage.write(generator_result)
            self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)
            self.assertEqual(
                0,
                await storage.read(lambda c: c.execute(
                    "SELECT count(*) FROM ingress_updates WHERE update_id=21"
                ).fetchone()[0]),
            )
            self.assertEqual(1, await storage.read(lambda c: c.execute("SELECT 1").fetchone()[0]))
            await storage.write(lambda c: (c.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) "
                "VALUES (22, 1, 'CONTROL')"
            ), None)[1])
        finally:
            await storage.close()

    async def test_callback_transaction_control_is_denied_and_rolled_back(self):
        storage = await self.open(now_ms=lambda: 1)
        operations = [
            ("connection.commit", lambda c: c.commit()),
            ("connection.rollback", lambda c: c.rollback()),
            ("explicit COMMIT", lambda c: c.execute("COMMIT")),
            ("explicit ROLLBACK", lambda c: c.execute("ROLLBACK")),
            ("SAVEPOINT", lambda c: c.execute("SAVEPOINT nested")),
            ("RELEASE", lambda c: c.execute("RELEASE nested")),
            ("ROLLBACK TO", lambda c: c.execute("ROLLBACK TO nested")),
            ("nested BEGIN", lambda c: c.execute("BEGIN IMMEDIATE")),
        ]
        try:
            for update_id, (name, operation) in enumerate(operations, start=30):
                with self.subTest(operation=name):
                    calls = 0

                    def callback(connection, *, update_id=update_id, operation=operation):
                        nonlocal calls
                        calls += 1
                        connection.execute(
                            "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) "
                            "VALUES (?, 1, 'CONTROL')",
                            (update_id,),
                        )
                        operation(connection)

                    with self.assertRaises(StorageError) as raised:
                        await storage.write(callback)
                    self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)
                    self.assertEqual(1, calls)
                    self.assertEqual(
                        0,
                        await storage.read(lambda c, update_id=update_id: c.execute(
                            "SELECT count(*) FROM ingress_updates WHERE update_id=?", (update_id,)
                        ).fetchone()[0]),
                    )

            await storage.write(lambda c: (c.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) "
                "VALUES (99, 1, 'CONTROL')"
            ), None)[1])
            self.assertEqual(1, await storage.read(lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id=99"
            ).fetchone()[0]))
        finally:
            await storage.close()

    async def test_serialization_is_deterministic(self):
        storage = await self.open(now_ms=lambda: 1)
        entered = threading.Event()
        release = threading.Event()
        second_entered = threading.Event()
        second_submitted = threading.Event()
        executor = storage._executor
        assert executor is not None
        original_submit = executor.submit
        try:
            def first(c):
                entered.set()
                release.wait(5)
                return "a"

            def second(c):
                second_entered.set()
                return "b"

            def observed_submit(function, *args, **kwargs):
                if function == storage._transaction and args and args[0] is second:
                    second_submitted.set()
                return original_submit(function, *args, **kwargs)

            executor.submit = observed_submit

            first_task = asyncio.create_task(storage.write(first))
            await asyncio.to_thread(entered.wait, 5)
            second_task = asyncio.create_task(storage.write(second))
            self.assertTrue(await asyncio.to_thread(second_submitted.wait, 5))
            self.assertFalse(second_entered.is_set())
            release.set()
            self.assertEqual(["a", "b"], await asyncio.gather(first_task, second_task))
        finally:
            release.set()
            executor.submit = original_submit
            await storage.close()

    async def test_post_submission_write_cancellation_stays_attached_once(self):
        storage = await self.open(now_ms=lambda: 1)
        entered = threading.Event()
        release = threading.Event()
        calls = 0
        calls_lock = threading.Lock()
        try:
            def callback(c):
                nonlocal calls
                with calls_lock:
                    calls += 1
                c.execute("INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (4, 1, 'CONTROL')")
                entered.set()
                release.wait(5)
                return 42

            task = asyncio.create_task(storage.write(callback))
            await asyncio.to_thread(entered.wait, 5)
            for _ in range(5):
                task.cancel()
                await asyncio.sleep(0)
            self.assertFalse(task.done())
            release.set()
            self.assertEqual(42, await task)
            self.assertEqual(1, calls)
            self.assertEqual(1, await storage.read(lambda c: c.execute(
                "SELECT count(*) FROM ingress_updates WHERE update_id=4"
            ).fetchone()[0]))
        finally:
            release.set()
            await storage.close()

    async def test_post_submission_read_cancellation_stays_attached(self):
        storage = await self.open(now_ms=lambda: 1)
        entered = threading.Event()
        release = threading.Event()
        try:
            def callback(c):
                entered.set()
                release.wait(5)
                return c.execute("SELECT 9").fetchone()[0]

            task = asyncio.create_task(storage.read(callback))
            await asyncio.to_thread(entered.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            release.set()
            self.assertEqual(9, await task)
        finally:
            release.set()
            await storage.close()

    async def test_close_owns_cleanup_after_cancellation_and_rejects_new_work(self):
        storage = await self.open(now_ms=lambda: 1)
        entered = threading.Event()
        release = threading.Event()
        try:
            operation = asyncio.create_task(storage.read(lambda c: (entered.set(), release.wait(5), "done")[2]))
            await asyncio.to_thread(entered.wait, 5)
            close_task = asyncio.create_task(storage.close())
            await asyncio.sleep(0)
            for _ in range(5):
                close_task.cancel()
                await asyncio.sleep(0)
            self.assertFalse(close_task.done())
            release.set()
            self.assertEqual("done", await operation)
            await close_task
            await storage.close()
            await self.assert_storage_category(storage.read(lambda c: 1), StorageErrorCategory.CLOSED)
        finally:
            release.set()
            await storage.close()

    async def test_second_owner_locked_then_reopens_after_close(self):
        first = await self.open(now_ms=lambda: 1)
        try:
            with self.assertRaises(StorageError) as raised:
                await self.open(now_ms=lambda: 2)
            self.assertEqual(StorageErrorCategory.LOCKED, raised.exception.category)
        finally:
            await first.close()
        second = await self.open(now_ms=lambda: 3)
        await second.close()

    async def test_failed_open_releases_lifetime_lock(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE unrelated (value TEXT)")
        await self.assert_storage_category(
            SqliteStorage.open(self.path), StorageErrorCategory.SCHEMA_INVALID
        )
        os.unlink(self.path)
        reopened = await self.open(now_ms=lambda: 5)
        await reopened.close()

    async def test_clock_exception_is_normalized_and_migration_rolls_back(self):
        sentinel = "PRIVATE_CLOCK_MUST_NOT_LEAK"

        def failing_clock():
            raise RuntimeError(sentinel)

        with self.assertRaises(StorageError) as raised:
            await self.open(now_ms=failing_clock)
        self.assertEqual(StorageErrorCategory.OPEN_FAILED, raised.exception.category)
        self.assertNotIn(sentinel, str(raised.exception))
        self.assertNotIn(sentinel, repr(raised.exception))
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(0, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='schema_migrations'"
            ).fetchone())

        reopened = await self.open(now_ms=lambda: 123)
        await reopened.close()

    @staticmethod
    def _wrong_uid_stat(info):
        values = list(info)
        values[stat.ST_UID] = os.geteuid() + 1
        return os.stat_result(values)

    async def test_existing_lock_file_uid_mismatch_is_rejected_before_sqlite(self):
        lock_path = self.path + ".lock"
        with open(lock_path, "w"):
            pass
        os.chmod(lock_path, 0o600)
        real_fstat = os.fstat
        calls = 0

        def fake_fstat(fd):
            nonlocal calls
            calls += 1
            info = real_fstat(fd)
            return self._wrong_uid_stat(info) if calls == 1 else info

        with mock.patch("codex_control.storage.sqlite.os.fstat", side_effect=fake_fstat), \
                mock.patch("codex_control.storage.sqlite.sqlite3.connect") as connect:
            await self.assert_storage_category(
                self.open(now_ms=lambda: 1), StorageErrorCategory.INSECURE_PATH
            )
            connect.assert_not_called()

        storage = await self.open(now_ms=lambda: 123)
        await storage.close()

    async def test_existing_db_file_uid_mismatch_is_rejected_before_sqlite(self):
        with sqlite3.connect(self.path):
            pass
        os.chmod(self.path, 0o600)
        real_fstat = os.fstat
        calls = 0

        def fake_fstat(fd):
            nonlocal calls
            calls += 1
            info = real_fstat(fd)
            return self._wrong_uid_stat(info) if calls == 2 else info

        with mock.patch("codex_control.storage.sqlite.os.fstat", side_effect=fake_fstat), \
                mock.patch("codex_control.storage.sqlite.sqlite3.connect") as connect:
            await self.assert_storage_category(
                self.open(now_ms=lambda: 1), StorageErrorCategory.INSECURE_PATH
            )
            connect.assert_not_called()

        storage = await self.open(now_ms=lambda: 123)
        await storage.close()

    async def test_effective_uid_mismatch_is_rejected(self):
        with mock.patch("codex_control.storage.sqlite.os.geteuid", return_value=os.geteuid() + 1):
            await self.assert_storage_category(
                SqliteStorage.open(self.path), StorageErrorCategory.INSECURE_PATH
            )

    async def test_secure_file_modes(self):
        storage = await self.open(now_ms=lambda: 1)
        await storage.close()
        self.assertEqual(0o600, stat.S_IMODE(os.stat(self.path).st_mode))
        self.assertEqual(0o600, stat.S_IMODE(os.stat(self.path + ".lock").st_mode))

    async def test_path_security_matrix(self):
        cases = [
            ("relative", "relative.sqlite3", StorageErrorCategory.INVALID_PATH),
            ("nul", self.path + "\x00x", StorageErrorCategory.INVALID_PATH),
            ("missing-parent", os.path.join(self.tempdir.name, "missing", "db"), StorageErrorCategory.INVALID_PATH),
        ]
        for name, path, category in cases:
            with self.subTest(name=name):
                with self.assertRaises(StorageError) as raised:
                    await SqliteStorage.open(path)
                self.assertEqual(category, raised.exception.category)

        symlink_parent = os.path.join(self.tempdir.name, "parent-link")
        real_parent = os.path.join(self.tempdir.name, "real-parent")
        os.mkdir(real_parent)
        os.symlink(real_parent, symlink_parent)
        with self.assertRaises(StorageError) as raised:
            await SqliteStorage.open(os.path.join(symlink_parent, "db"))
        self.assertEqual(StorageErrorCategory.INSECURE_PATH, raised.exception.category)

        real_db = os.path.join(self.tempdir.name, "real-db")
        with sqlite3.connect(real_db):
            pass
        os.chmod(real_db, 0o600)
        os.symlink(real_db, self.path)
        with self.assertRaises(StorageError) as raised:
            await self.open()
        self.assertEqual(StorageErrorCategory.INSECURE_PATH, raised.exception.category)
        os.unlink(self.path)
        with open(self.path + ".lock", "w"):
            pass
        os.chmod(self.path + ".lock", 0o600)
        os.unlink(self.path + ".lock")
        os.symlink(real_db, self.path + ".lock")
        with self.assertRaises(StorageError) as raised:
            await self.open()
        self.assertEqual(StorageErrorCategory.INSECURE_PATH, raised.exception.category)

    async def test_existing_insecure_modes_and_parent_are_rejected(self):
        with open(self.path, "w"):
            pass
        os.chmod(self.path, 0o644)
        await self.assert_storage_category(SqliteStorage.open(self.path), StorageErrorCategory.INSECURE_PATH)
        os.unlink(self.path)
        with open(self.path + ".lock", "w"):
            pass
        os.chmod(self.path + ".lock", 0o644)
        await self.assert_storage_category(SqliteStorage.open(self.path), StorageErrorCategory.INSECURE_PATH)
        os.unlink(self.path + ".lock")
        os.chmod(self.tempdir.name, 0o755 | stat.S_IWGRP)
        try:
            await self.assert_storage_category(SqliteStorage.open(self.path), StorageErrorCategory.INSECURE_PATH)
        finally:
            os.chmod(self.tempdir.name, 0o700)

    async def test_storage_error_and_repr_redact_sentinels(self):
        error = StorageError(StorageErrorCategory.INSECURE_PATH)
        sentinel_path = os.path.join(self.tempdir.name, "PRIVATE_DB_PATH_MUST_NOT_LEAK.sqlite3")
        storage = await SqliteStorage.open(sentinel_path, now_ms=lambda: 1)
        try:
            rendered = str(error) + repr(error) + repr(storage)
        finally:
            await storage.close()
        self.assertNotIn(sentinel_path, rendered)
        for sentinel in (
            "PRIVATE_DB_PATH_MUST_NOT_LEAK", "PRIVATE_SQL_MUST_NOT_LEAK",
            "PRIVATE_PAYLOAD_MUST_NOT_LEAK", "OPENAI_API_KEY=P2_1_SECRET",
            "/private/CODEX_HOME", "/private/controller.sqlite3",
        ):
            self.assertNotIn(sentinel, rendered)


class SchemaConstraintTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "constraints.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def test_fk_live_slot_and_check_constraint_matrix(self):
        storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        try:
            async def rejected(sql, params=()):
                with self.assertRaises(StorageError) as raised:
                    await storage.write(lambda c: c.execute(sql, params))
                self.assertEqual(StorageErrorCategory.TRANSACTION_FAILED, raised.exception.category)

            await rejected(
                "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, input_sha256, state, version, created_at_ms, updated_at_ms) VALUES ('j0', 0, 1, 1, 'absent', 's', 'p', ?, 'RECEIVED', 0, 1, 1)",
                (HASH,),
            )
            await rejected(
                "INSERT INTO dialogues(dialogue_id, server_id, profile_id, state, version, created_at_ms, updated_at_ms) VALUES ('d1', 's', 'p', 'BAD', 0, 1, 1)"
            )
            await storage.write(lambda c: (c.execute(
                "INSERT INTO dialogues(dialogue_id, server_id, profile_id, state, version, created_at_ms, updated_at_ms) VALUES ('d1', 's', 'p', 'IDLE', 0, 1, 1)"
            ), None)[1])
            await rejected(
                "INSERT INTO dialogues(dialogue_id, server_id, profile_id, state, version, created_at_ms, updated_at_ms) VALUES ('d2', 's', 'p', 'IDLE', 0, 1, 1)"
            )
            await rejected(
                "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, input_sha256, state, version, created_at_ms, updated_at_ms) VALUES ('j1', 1, 1, 1, 'd1', 's', 'p', ?, 'BAD', 0, 1, 1)",
                (HASH,),
            )
            await rejected(
                "INSERT INTO transient_payloads(payload_id, kind, content, content_sha256, byte_length, created_at_ms, expires_at_ms) VALUES ('p0', 'INPUT', x'61', ?, 1, 1, 1)",
                (HASH,),
            )
            await rejected(
                "INSERT INTO transient_payloads(payload_id, dialogue_id, kind, content, content_sha256, byte_length, created_at_ms, expires_at_ms) VALUES ('p1', 'd1', 'INPUT', x'61', ?, 2, 1, 1)",
                (HASH,),
            )
            await self._valid_job(storage)
            await rejected(
                "INSERT INTO delivery_segments(job_id, sequence, operation, payload_sha256, state, attempt_count, created_at_ms, updated_at_ms) VALUES ('j1', 0, 'CREATE', ?, 'PENDING', 0, 1, 1)",
                (HASH,),
            )
            await rejected(
                "INSERT INTO approvals(approval_id, profile_id, wire_request_id_type, wire_request_id_int, wire_request_id_text, job_id, kind, state, created_at_ms, updated_at_ms, expires_at_ms) VALUES ('a1', 'p', 'INTEGER', 4, 'also-set', 'j1', 'permissions', 'PENDING', 1, 1, 1)"
            )
            await rejected(
                "INSERT INTO ingress_updates(update_id, received_at_ms, disposition) VALUES (1, 1, 'NOT_ALLOWED')"
            )
        finally:
            await storage.close()

    async def _valid_job(self, storage):
        await storage.write(lambda c: (c.execute(
            "INSERT INTO turn_jobs(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, input_sha256, state, version, created_at_ms, updated_at_ms) VALUES ('j1', 1, 1, 1, 'd1', 's', 'p', ?, 'RECEIVED', 0, 1, 1)",
            (HASH,)
        ), None)[1])

    async def test_fk_cascade_set_null_and_reusable_wire_ids(self):
        storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO dialogues(dialogue_id, server_id, profile_id, state, version, created_at_ms, updated_at_ms) VALUES ('d1', 's', 'p', 'IDLE', 0, 1, 1)"
            ), None)[1])
            await self._valid_job(storage)
            await storage.write(lambda c: (c.execute(
                "INSERT INTO transient_payloads(payload_id, dialogue_id, kind, content, content_sha256, byte_length, created_at_ms, expires_at_ms) VALUES ('p1', 'd1', 'INPUT', x'61', ?, 1, 1, 1)", (HASH,)
            ), None)[1])
            for approval_id in ("a1", "a2"):
                await storage.write(lambda c, approval_id=approval_id: (c.execute(
                    "INSERT INTO approvals(approval_id, profile_id, wire_request_id_type, wire_request_id_int, job_id, kind, state, created_at_ms, updated_at_ms, expires_at_ms) VALUES (?, 'p', 'INTEGER', 4, 'j1', 'permissions', 'PENDING', 1, 1, 1)", (approval_id,)
                ), None)[1])
            await storage.write(lambda c: (c.execute(
                "INSERT INTO errors(fingerprint_sha256, error_class, count, first_seen_at_ms, last_seen_at_ms, dialogue_id, job_id) VALUES (?, 'X', 1, 1, 1, 'd1', 'j1')", (HASH,)
            ), None)[1])
            await storage.write(lambda c: (c.execute("DELETE FROM dialogues WHERE dialogue_id='d1'"), None)[1])
            remaining = await storage.read(lambda c: (
                c.execute("SELECT count(*) FROM turn_jobs").fetchone()[0],
                c.execute("SELECT count(*) FROM transient_payloads").fetchone()[0],
                c.execute("SELECT count(*) FROM approvals").fetchone()[0],
                tuple(c.execute("SELECT dialogue_id, job_id FROM errors WHERE fingerprint_sha256=?", (HASH,)).fetchone()),
            ))
            self.assertEqual((0, 0, 0, (None, None)), remaining)
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
