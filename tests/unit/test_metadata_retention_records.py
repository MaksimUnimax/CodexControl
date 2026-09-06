import dataclasses
import os
import tempfile
import unittest

from codex_control.storage import (
    METADATA_RETENTION_MS,
    MetadataRetentionRepository,
    MetadataRetentionSweepResult,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
)


class MetadataRetentionRecordTests(unittest.IsolatedAsyncioTestCase):
    async def test_constant_and_result_shape(self):
        self.assertEqual(604_800_000, METADATA_RETENTION_MS)
        self.assertEqual(
            (
                "terminal_jobs_deleted", "payloads_deleted", "delivery_segments_deleted",
                "approvals_deleted", "ingress_deleted", "callback_actions_deleted",
                "tombstones_deleted", "errors_deleted",
            ),
            tuple(field.name for field in dataclasses.fields(MetadataRetentionSweepResult)),
        )
        result = MetadataRetentionSweepResult(0, 1, 2, 3, 4, 5, 6, 7)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.errors_deleted = 8

    async def test_public_surface_and_repr(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "controller.sqlite3")
            storage = await SqliteStorage.open(path, now_ms=lambda: 1)
            try:
                repository = MetadataRetentionRepository(storage, now_ms=lambda: 2)
                self.assertEqual({"sweep"}, {
                    name for name, value in vars(MetadataRetentionRepository).items()
                    if not name.startswith("_") and callable(value)
                })
                self.assertEqual("<MetadataRetentionRepository>", repr(repository))
                self.assertNotIn(path, repr(repository))
            finally:
                await storage.close()

    async def test_limit_validation_happens_before_clock(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "controller.sqlite3")
            storage = await SqliteStorage.open(path, now_ms=lambda: 1)
            try:
                repository = MetadataRetentionRepository(storage, now_ms=lambda: calls.append(True))
                for invalid in (0, 1001, True, False, 1.5, "1", None):
                    with self.assertRaises(RepositoryError) as raised:
                        await repository.sweep(invalid)
                    self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
                self.assertEqual([], calls)
            finally:
                await storage.close()

    async def test_constructor_rejects_invalid_storage_or_clock(self):
        with self.assertRaises(RepositoryError) as raised:
            MetadataRetentionRepository(object())
        self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "controller.sqlite3")
            storage = await SqliteStorage.open(path, now_ms=lambda: 1)
            try:
                with self.assertRaises(RepositoryError) as raised:
                    MetadataRetentionRepository(storage, now_ms=object())
                self.assertIs(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            finally:
                await storage.close()


if __name__ == "__main__":
    unittest.main()
