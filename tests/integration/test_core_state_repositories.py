import asyncio
import os
import sqlite3
import tempfile
import unittest

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    DialogueRepository,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsRepository,
    SqliteStorage,
    StorageError,
    StorageErrorCategory,
)


class CoreStateRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.clock_calls = 0

    def tearDown(self):
        self.tempdir.cleanup()

    async def open(self, now_ms=None):
        return await SqliteStorage.open(self.path, now_ms=now_ms or (lambda: 1))

    async def test_empty_reads_and_controller_boot_restart_sleep(self):
        storage = await self.open()
        runtime = ControllerRuntimeRepository(storage, now_ms=lambda: 100)
        settings = SettingsRepository(storage, now_ms=lambda: 100)
        dialogues = DialogueRepository(storage, now_ms=lambda: 100)
        self.assertIsNone(await runtime.get())
        self.assertIsNone(await settings.get())
        self.assertIsNone(await dialogues.get_live())

        first = await runtime.begin_boot("fleet-v1")
        self.assertEqual(1, first.record.boot_generation)
        self.assertEqual(0, first.record.last_control_epoch)
        self.assertEqual(ControllerMode.SLEEP, first.record.requested_mode)
        self.assertEqual(ControllerMode.SLEEP, first.effective_mode)
        second = await runtime.begin_boot("fleet-v2")
        self.assertEqual(2, second.record.boot_generation)
        self.assertEqual(ControllerMode.SLEEP, second.effective_mode)
        await storage.close()

        storage = await self.open()
        try:
            self.assertEqual(second.record, await ControllerRuntimeRepository(storage).get())
        finally:
            await storage.close()

    async def test_historical_active_is_preserved_but_boot_effective_mode_is_sleep(self):
        storage = await self.open()
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO controller_runtime VALUES (1, 55, 'ACTIVE', 7, 'fleet-v1', 10, 20)"
            ), None)[1])
            result = await ControllerRuntimeRepository(storage, now_ms=lambda: 15).begin_boot("fleet-v2")
            self.assertEqual(ControllerMode.ACTIVE, result.record.requested_mode)
            self.assertEqual(55, result.record.last_control_epoch)
            self.assertEqual(8, result.record.boot_generation)
            self.assertEqual("fleet-v2", result.record.fleet_version)
            self.assertEqual(ControllerMode.SLEEP, result.effective_mode)
            self.assertEqual(20, result.record.updated_at_ms)
        finally:
            await storage.close()

    async def test_controller_generation_overflow_is_not_mutated(self):
        storage = await self.open()
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO controller_runtime VALUES (1, 0, 'SLEEP', ?, 'fleet', 1, 1)",
                (9223372036854775807,),
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await ControllerRuntimeRepository(storage, now_ms=lambda: 2).begin_boot("next")
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual("fleet", (await ControllerRuntimeRepository(storage).get()).fleet_version)
        finally:
            await storage.close()

    async def test_settings_durable_over_fallback_and_replace(self):
        storage = await self.open()
        try:
            calls = []
            repo = SettingsRepository(storage, now_ms=lambda: calls.append(10) or 10)
            created = await repo.initialize_if_absent(
                profile_id="profile-a", model_id="model-a", reasoning_effort="high"
            )
            self.assertTrue(created.created)
            self.assertEqual(1, len(calls))
            fallback = SettingsRepository(storage, now_ms=lambda: calls.append(11) or 11)
            existing = await fallback.initialize_if_absent(
                profile_id="profile-b", model_id="model-b", reasoning_effort="low"
            )
            self.assertFalse(existing.created)
            self.assertEqual(created.record, existing.record)
            self.assertEqual(1, len(calls))
            replaced = await repo.replace(
                expected_version=0, profile_id="profile-b", model_id="model-b", reasoning_effort="low"
            )
            self.assertEqual(1, replaced.version)
            self.assertEqual(10, replaced.updated_at_ms)
            same = await repo.replace(
                expected_version=1, profile_id="profile-b", model_id="model-b", reasoning_effort="low"
            )
            self.assertEqual(2, same.version)
            with self.assertRaises(RepositoryError) as raised:
                await repo.replace(
                    expected_version=1, profile_id=None, model_id=None, reasoning_effort=None
                )
            self.assertEqual(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_settings_missing_and_stale_paths_do_not_call_clock(self):
        storage = await self.open()
        try:
            def fail_clock():
                raise RuntimeError("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK")

            repo = SettingsRepository(storage, now_ms=fail_clock)
            with self.assertRaises(RepositoryError) as raised:
                await repo.replace(expected_version=0, profile_id=None, model_id=None, reasoning_effort=None)
            self.assertEqual(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            await SettingsRepository(storage, now_ms=lambda: 1).initialize_if_absent(
                profile_id="p", model_id="m", reasoning_effort="e"
            )
            with self.assertRaises(RepositoryError) as raised:
                await repo.replace(expected_version=1, profile_id=None, model_id=None, reasoning_effort=None)
            self.assertEqual(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            self.assertNotIn("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK", repr(raised.exception))
        finally:
            await storage.close()

    async def test_settings_concurrent_compare_and_swap_has_one_winner(self):
        storage = await self.open()
        try:
            await SettingsRepository(storage, now_ms=lambda: 1).initialize_if_absent(
                profile_id="p", model_id="m", reasoning_effort="e"
            )
            first, second = await asyncio.gather(
                SettingsRepository(storage, now_ms=lambda: 2).replace(
                    expected_version=0, profile_id="winner-a", model_id="ma", reasoning_effort="a"
                ),
                SettingsRepository(storage, now_ms=lambda: 3).replace(
                    expected_version=0, profile_id="winner-b", model_id="mb", reasoning_effort="b"
                ),
                return_exceptions=True,
            )
            results = [first, second]
            self.assertEqual(1, sum(not isinstance(item, Exception) for item in results))
            self.assertEqual(1, sum(
                isinstance(item, RepositoryError) and item.category is RepositoryErrorCategory.VERSION_CONFLICT
                for item in results
            ))
            final = await SettingsRepository(storage).get()
            self.assertEqual(1, final.version)
            self.assertIn(final.profile_id, {"winner-a", "winner-b"})
        finally:
            await storage.close()

    async def test_dialogue_create_intent_duplicate_and_terminal_claims(self):
        storage = await self.open()
        try:
            calls = []
            repo = DialogueRepository(storage, now_ms=lambda: calls.append(10) or 10)
            created = await repo.create_intent(dialogue_id="d", server_id="server", profile_id="profile")
            self.assertEqual(DialogueState.CREATING, created.state)
            self.assertEqual(0, created.version)
            self.assertEqual(1, len(calls))
            with self.assertRaises(RepositoryError) as raised:
                await repo.create_intent(dialogue_id="d", server_id="server", profile_id="profile")
            self.assertEqual(RepositoryErrorCategory.ALREADY_EXISTS, raised.exception.category)
            self.assertEqual(1, len(calls))
            confirmed = await repo.confirm_created(dialogue_id="d", expected_version=0, thread_id="thread")
            self.assertEqual(DialogueState.IDLE, confirmed.state)
            self.assertEqual(1, confirmed.version)
            self.assertEqual("thread", confirmed.thread_id)
            self.assertEqual("server", confirmed.server_id)
            self.assertEqual("profile", confirmed.profile_id)
            with self.assertRaises(RepositoryError) as raised:
                await repo.confirm_created(dialogue_id="d", expected_version=1, thread_id="other")
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_dialogue_unknown_error_and_conflict_ordering(self):
        storage = await self.open()
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 20)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_create_unknown(dialogue_id="missing", expected_version=0, error_class="E")
            self.assertEqual(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_create_unknown(dialogue_id="d", expected_version=2, error_class="E")
            self.assertEqual(RepositoryErrorCategory.VERSION_CONFLICT, raised.exception.category)
            unknown = await repo.mark_create_unknown(dialogue_id="d", expected_version=0, error_class="CODEX:timeout-1")
            self.assertEqual(DialogueState.CREATE_UNKNOWN, unknown.state)
            self.assertEqual("CODEX:timeout-1", unknown.last_error_class)
            with self.assertRaises(RepositoryError) as raised:
                await repo.mark_create_error(dialogue_id="d", expected_version=1, error_class="second")
            self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)
        finally:
            await storage.close()

    async def test_dialogue_error_claim_and_sanitization(self):
        storage = await self.open()
        try:
            repo = DialogueRepository(storage, now_ms=lambda: 3)
            await repo.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            for invalid in ("", "raw prose", "/private/path", "line\nfeed", "OPENAI_API_KEY=P2_2_SECRET"):
                with self.subTest(error_class=invalid):
                    with self.assertRaises(RepositoryError) as raised:
                        await repo.mark_create_error(dialogue_id="d", expected_version=0, error_class=invalid)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            error = await repo.mark_create_error(dialogue_id="d", expected_version=0, error_class="CODEX.error:1")
            self.assertEqual(DialogueState.ERROR, error.state)
            self.assertIsNone(error.thread_id)
        finally:
            await storage.close()

    async def test_dialogue_concurrent_create_intent_has_one_row(self):
        storage = await self.open()
        try:
            results = await asyncio.gather(
                DialogueRepository(storage, now_ms=lambda: 1).create_intent(
                    dialogue_id="one", server_id="s1", profile_id="p1"
                ),
                DialogueRepository(storage, now_ms=lambda: 2).create_intent(
                    dialogue_id="two", server_id="s2", profile_id="p2"
                ),
                return_exceptions=True,
            )
            self.assertEqual(1, sum(not isinstance(item, Exception) for item in results))
            self.assertEqual(1, sum(
                isinstance(item, RepositoryError) and item.category is RepositoryErrorCategory.ALREADY_EXISTS
                for item in results
            ))
            row = await storage.read(lambda c: c.execute("SELECT count(*) FROM dialogues").fetchone()[0])
            self.assertEqual(1, row)
        finally:
            await storage.close()

    async def test_clock_validation_and_backward_timestamp(self):
        storage = await self.open()
        try:
            repo = ControllerRuntimeRepository(storage, now_ms=lambda: 100)
            await repo.begin_boot("fleet")
            backwards = ControllerRuntimeRepository(storage, now_ms=lambda: 50)
            result = await backwards.begin_boot("fleet-2")
            self.assertEqual(100, result.record.updated_at_ms)
            failing = SettingsRepository(storage, now_ms=lambda: True)
            with self.assertRaises(RepositoryError) as raised:
                await failing.initialize_if_absent(profile_id=None, model_id=None, reasoning_effort=None)
            self.assertEqual(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
            self.assertNotIn("True", repr(raised.exception))
        finally:
            await storage.close()

    async def test_corrupt_persisted_row_fails_closed_and_storage_errors_stay_storage_errors(self):
        storage = await self.open()
        await storage.close()
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT INTO settings VALUES (1, NULL, NULL, NULL, 1.5, 1, 1)"
            )
        storage = await self.open()
        try:
            with self.assertRaises(RepositoryError) as raised:
                await SettingsRepository(storage).get()
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("1.5", repr(raised.exception))
        finally:
            await storage.close()
        storage = await self.open()
        await storage.close()
        with self.assertRaises(StorageError) as raised:
            await SettingsRepository(storage).get()
        self.assertEqual(StorageErrorCategory.CLOSED, raised.exception.category)

    async def test_restarted_records_materialize_without_cache(self):
        storage = await self.open()
        try:
            runtime = await ControllerRuntimeRepository(storage, now_ms=lambda: 10).begin_boot("fleet")
            settings = await SettingsRepository(storage, now_ms=lambda: 11).initialize_if_absent(
                profile_id="p", model_id="m", reasoning_effort="e"
            )
            dialogues = DialogueRepository(storage, now_ms=lambda: 12)
            dialogue = await dialogues.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            await dialogues.confirm_created(dialogue_id="d", expected_version=0, thread_id="t")
        finally:
            await storage.close()
        reopened = await self.open()
        try:
            self.assertEqual(runtime.record, await ControllerRuntimeRepository(reopened).get())
            self.assertEqual(settings.record, await SettingsRepository(reopened).get())
            materialized = await DialogueRepository(reopened).get_live()
            self.assertEqual(dialogue.dialogue_id, materialized.dialogue_id)
            self.assertEqual(1, materialized.version)
            self.assertEqual("t", materialized.thread_id)
        finally:
            await reopened.close()


if __name__ == "__main__":
    unittest.main()
