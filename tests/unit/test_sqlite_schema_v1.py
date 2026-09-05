import asyncio
import os
import sqlite3
import tempfile
import unittest
from hashlib import sha256

from codex_control.storage import (
    MIGRATION_ID,
    SCHEMA_V1_CANONICAL_SQL,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V1_STATEMENTS,
    SqliteStorage,
    StorageError,
    StorageErrorCategory,
)
from codex_control.storage.schema import INDEX_NAMES, TABLE_NAMES, canonicalize_sql


class SchemaV1Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    def tearDown(self):
        self.tempdir.cleanup()

    async def _open(self, **kwargs):
        return await SqliteStorage.open(self.path, **kwargs)

    async def _objects(self, storage):
        return await storage.read(
            lambda c: [(row[0], row[1], row[2]) for row in c.execute(
                "SELECT type, name, sql FROM sqlite_master "
                "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
            )]
        )

    def _direct(self):
        return sqlite3.connect(self.path)

    async def test_fresh_bootstrap_exact_objects_hash_and_no_seed_rows(self):
        storage = await self._open(now_ms=lambda: 1234567890)
        try:
            row = await storage.read(
                lambda c: tuple(c.execute(
                    "SELECT version, migration_id, ddl_sha256, applied_at_ms "
                    "FROM schema_migrations"
                ).fetchone())
            )
            self.assertEqual((1, MIGRATION_ID, SCHEMA_V1_DDL_SHA256, 1234567890), row)
            objects = await self._objects(storage)
            self.assertEqual(TABLE_NAMES, {name for kind, name, _ in objects if kind == "table"})
            self.assertEqual(INDEX_NAMES, {name for kind, name, _ in objects if kind == "index"})
            self.assertFalse([x for x in objects if x[0] in ("view", "trigger")])
            counts = await storage.read(lambda c: {
                table: c.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in TABLE_NAMES if table != "schema_migrations"
            })
            self.assertTrue(all(count == 0 for count in counts.values()))
        finally:
            await storage.close()

    async def test_hash_is_derived_from_one_ordered_constant(self):
        expected = "\n".join(canonicalize_sql(s) for s in SCHEMA_V1_STATEMENTS) + "\n"
        self.assertEqual(expected, SCHEMA_V1_CANONICAL_SQL)
        self.assertEqual(sha256(expected.encode("utf-8")).hexdigest(), SCHEMA_V1_DDL_SHA256)
        self.assertEqual(len(SCHEMA_V1_STATEMENTS), 26)

    async def test_reopen_is_idempotent_and_does_not_call_clock(self):
        storage = await self._open(now_ms=lambda: 7)
        await storage.close()

        def must_not_run():
            raise AssertionError("migration clock was reused")

        storage = await self._open(now_ms=must_not_run)
        try:
            self.assertEqual(7, await storage.read(
                lambda c: c.execute("SELECT applied_at_ms FROM schema_migrations").fetchone()[0]
            ))
        finally:
            await storage.close()

    async def test_unversioned_nonempty_rejected_without_adoption(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("CREATE TABLE foreign_state (id INTEGER)")
        with self.assertRaises(StorageError) as raised:
            await self._open(now_ms=lambda: 1)
        self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)

    async def test_future_version_rejected(self):
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA user_version = 2")
        with self.assertRaises(StorageError) as raised:
            await self._open()
        self.assertEqual(StorageErrorCategory.SCHEMA_UNSUPPORTED, raised.exception.category)

    async def test_v1_migration_hash_missing_index_extra_object_and_sql_drift_rejected(self):
        cases = ("hash", "row", "index", "extra", "table", "view", "trigger", "drift")
        for case in cases:
            with self.subTest(case=case):
                storage = await self._open(now_ms=lambda: 1)
                await storage.close()
                with self._direct() as connection:
                    if case == "hash":
                        connection.execute("UPDATE schema_migrations SET ddl_sha256 = ? WHERE version = 1", ("b" * 64,))
                    elif case == "row":
                        connection.execute("DELETE FROM schema_migrations")
                    elif case == "index":
                        connection.execute("DROP INDEX idx_errors_job")
                    elif case == "extra":
                        connection.execute("CREATE INDEX extra_index ON errors(error_class)")
                    elif case == "table":
                        connection.execute("CREATE TABLE extra_table (value TEXT)")
                    elif case == "view":
                        connection.execute("CREATE VIEW extra_view AS SELECT 1")
                    elif case == "trigger":
                        connection.execute("CREATE TRIGGER extra_trigger AFTER INSERT ON errors BEGIN SELECT 1; END")
                    else:
                        connection.execute("ALTER TABLE errors RENAME TO errors_old")
                        connection.execute(SCHEMA_V1_STATEMENTS[11])
                with self.assertRaises(StorageError) as raised:
                    await self._open()
                self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)
                # Give each subtest a fresh path; no repair is performed by open.
                self.tempdir.cleanup()
                self.tempdir = tempfile.TemporaryDirectory()
                self.path = os.path.join(self.tempdir.name, "controller.sqlite3")

    async def test_schema_master_sql_is_exactly_canonicalized(self):
        storage = await self._open(now_ms=lambda: 2)
        try:
            expected = {s.split()[2]: canonicalize_sql(s) for s in SCHEMA_V1_STATEMENTS}
            actual = await self._objects(storage)
            actual_by_name = {name: canonicalize_sql(sql) for _, name, sql in actual}
            self.assertEqual(expected, actual_by_name)
        finally:
            await storage.close()

    async def test_content_boundary_and_approval_schema_shape(self):
        storage = await self._open(now_ms=lambda: 3)
        try:
            columns = await storage.read(lambda c: {
                table: [row[1] for row in c.execute(f"PRAGMA table_info({table})")]
                for table in TABLE_NAMES
            })
            self.assertEqual(["content"], [name for table, names in columns.items() if "content" in names for name in names if name == "content"])
            joined = " ".join(" ".join(names) for names in columns.values()).lower()
            for forbidden in ("prompt", "response", "raw_json", "stdout", "stderr", "environment", "cookie", "secret"):
                self.assertNotIn(forbidden, joined)
            self.assertIn("token_hash_sha256", columns["callback_actions"])
            self.assertNotIn("token", columns["callback_actions"])
        finally:
            await storage.close()


if __name__ == "__main__":
    unittest.main()
