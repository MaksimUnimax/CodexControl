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

    async def open_fresh(self):
        tempdir = tempfile.TemporaryDirectory()
        path = os.path.join(tempdir.name, "controller.sqlite3")
        storage = await SqliteStorage.open(path, now_ms=lambda: 1)
        return tempdir, storage

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
            confirmed = await dialogues.confirm_created(dialogue_id="d", expected_version=0, thread_id="t")
        finally:
            await storage.close()
        reopened = await self.open()
        try:
            self.assertEqual(runtime.record, await ControllerRuntimeRepository(reopened).get())
            self.assertEqual(settings.record, await SettingsRepository(reopened).get())
            materialized = await DialogueRepository(reopened).get_live()
            self.assertEqual(confirmed, materialized)
        finally:
            await reopened.close()

    async def test_all_schema_dialogue_states_materialize_as_exact_enum_values(self):
        storage = await self.open()
        states = (
            "CREATING", "IDLE", "CREATE_UNKNOWN", "ERROR", "TURN_RUNNING",
            "INTERRUPTING", "TURN_UNKNOWN", "DELETE_PENDING", "DELETING", "DELETE_UNKNOWN",
        )
        try:
            for index, state in enumerate(states):
                with self.subTest(state=state):
                    await storage.close()
                    self.tempdir.cleanup()
                    self.tempdir = tempfile.TemporaryDirectory()
                    self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
                    storage = await self.open()
                    dialogue_id = f"dialogue-{index}"
                    thread_id = None if state == "CREATING" else f"thread-{index}"
                    last_error = None if state == "CREATING" else f"ERR:{index}"
                    await storage.write(lambda c, values=(
                        dialogue_id, "server-materialized", "profile-materialized", thread_id,
                        state, 7, 100, 200, last_error,
                    ): (c.execute(
                        "INSERT INTO dialogues "
                        "(dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                        "created_at_ms, updated_at_ms, last_error_class) "
                        "VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)",
                        values,
                    ), None)[1])
                    record = await DialogueRepository(storage).get_live()
                    self.assertIsNotNone(record)
                    self.assertEqual(DialogueState(state), record.state)
                    self.assertEqual(dialogue_id, record.dialogue_id)
                    self.assertEqual("server-materialized", record.server_id)
                    self.assertEqual("profile-materialized", record.profile_id)
                    self.assertEqual(thread_id, record.thread_id)
                    self.assertEqual(7, record.version)
                    self.assertEqual(100, record.created_at_ms)
                    self.assertEqual(200, record.updated_at_ms)
                    self.assertEqual(last_error, record.last_error_class)
        finally:
            await storage.close()

    async def test_actual_raising_clock_is_redacted_and_rolls_back_each_repository_family(self):
        storage = await self.open()
        sentinel = "PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK"
        calls = {"controller": 0, "settings": 0, "dialogue": 0}

        def raising_clock(name):
            def clock():
                calls[name] += 1
                raise RuntimeError(sentinel)
            return clock

        try:
            cases = (
                ("controller", lambda: ControllerRuntimeRepository(
                    storage, now_ms=raising_clock("controller")).begin_boot("fleet"), "controller_runtime"),
                ("settings", lambda: SettingsRepository(
                    storage, now_ms=raising_clock("settings")).initialize_if_absent(
                        profile_id="p", model_id="m", reasoning_effort="e"), "settings"),
                ("dialogue", lambda: DialogueRepository(
                    storage, now_ms=raising_clock("dialogue")).create_intent(
                        dialogue_id="d", server_id="s", profile_id="p"), "dialogues"),
            )
            for name, operation, table in cases:
                with self.subTest(repository=name):
                    with self.assertRaises(RepositoryError) as raised:
                        await operation()
                    self.assertEqual(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
                    self.assertNotIn(sentinel, str(raised.exception))
                    self.assertNotIn(sentinel, repr(raised.exception))
                    self.assertEqual(1, calls[name])
                    self.assertEqual(0, await storage.read(
                        lambda c, table=table: c.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    ))
            self.assertIsNone(await ControllerRuntimeRepository(storage).get())
            self.assertIsNone(await SettingsRepository(storage).get())
            self.assertIsNone(await DialogueRepository(storage).get_live())
        finally:
            await storage.close()

    async def test_invalid_clock_values_are_rejected_without_mutation_and_boundaries_work(self):
        invalid_values = (True, False, "123", 1.5, -1, 9223372036854775808)
        for value in invalid_values:
            tempdir, storage = await self.open_fresh()
            try:
                with self.subTest(value=repr(value)):
                    with self.assertRaises(RepositoryError) as raised:
                        await ControllerRuntimeRepository(storage, now_ms=lambda value=value: value).begin_boot("fleet")
                    self.assertEqual(RepositoryErrorCategory.CLOCK_INVALID, raised.exception.category)
                    self.assertEqual(0, await storage.read(
                        lambda c: c.execute("SELECT count(*) FROM controller_runtime").fetchone()[0]
                    ))
                    self.assertIsNone(await ControllerRuntimeRepository(storage).get())
            finally:
                await storage.close()
                tempdir.cleanup()

        for value in (0, 9223372036854775807):
            tempdir, storage = await self.open_fresh()
            try:
                with self.subTest(valid_value=value):
                    result = await ControllerRuntimeRepository(storage, now_ms=lambda value=value: value).begin_boot("fleet")
                    self.assertEqual(value, result.record.created_at_ms)
                    self.assertEqual(value, result.record.updated_at_ms)
            finally:
                await storage.close()
                tempdir.cleanup()

    async def test_settings_and_dialogue_version_overflow_fail_closed_before_clock(self):
        maximum = 9223372036854775807
        storage = await self.open()
        settings_clock_calls = []
        dialogue_clock_calls = []
        try:
            settings = SettingsRepository(storage, now_ms=lambda: settings_clock_calls.append(1) or 1)
            await settings.initialize_if_absent(profile_id="old", model_id="model", reasoning_effort="high")
            await storage.write(lambda c: (c.execute("UPDATE settings SET version = ?", (maximum,)), None)[1])
            settings_before_overflow = await settings.get()
            with self.assertRaises(RepositoryError) as raised:
                await SettingsRepository(
                    storage, now_ms=lambda: settings_clock_calls.append(1) or (_ for _ in ()).throw(
                        RuntimeError("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK")
                    )
                ).replace(expected_version=maximum, profile_id="new", model_id="new", reasoning_effort="low")
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], settings_clock_calls[1:])
            self.assertEqual(settings_before_overflow, await settings.get())

            dialogue = DialogueRepository(storage, now_ms=lambda: dialogue_clock_calls.append(1) or 1)
            await dialogue.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            await storage.write(lambda c: (c.execute(
                "UPDATE dialogues SET version = ? WHERE dialogue_id = 'd'", (maximum,)
            ), None)[1])
            dialogue_before_overflow = await dialogue.get_live()
            with self.assertRaises(RepositoryError) as raised:
                await DialogueRepository(
                    storage, now_ms=lambda: dialogue_clock_calls.append(1) or (_ for _ in ()).throw(
                        RuntimeError("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK")
                    )
                ).mark_create_unknown(dialogue_id="d", expected_version=maximum, error_class="ERR")
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual([], dialogue_clock_calls[1:])
            self.assertEqual(dialogue_before_overflow, await dialogue.get_live())
        finally:
            await storage.close()

    async def test_public_input_boundaries_are_exact_and_invalid_values_do_not_mutate(self):
        maximum = 9223372036854775807

        storage = await self.open()
        try:
            dialogue = DialogueRepository(storage, now_ms=lambda: 1)
            created = await dialogue.create_intent(
                dialogue_id="d" * 128, server_id="s" * 128, profile_id="p" * 128
            )
            self.assertEqual("d" * 128, created.dialogue_id)
            self.assertEqual("s" * 128, created.server_id)
            self.assertEqual("p" * 128, created.profile_id)
            for field, value in (
                ("dialogue_id", "d" * 129), ("dialogue_id", ""), ("dialogue_id", "d\x00"),
                ("server_id", "s" * 129), ("server_id", ""), ("server_id", "s\x00"),
                ("profile_id", "p" * 129), ("profile_id", ""), ("profile_id", "p\x00"),
            ):
                with self.subTest(field=field, value=repr(value)):
                    kwargs = {"dialogue_id": "new", "server_id": "server", "profile_id": "profile"}
                    kwargs[field] = value
                    with self.assertRaises(RepositoryError) as raised:
                        await dialogue.create_intent(**kwargs)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(created, await dialogue.get_live())
        finally:
            await storage.close()

        storage = await self.open()
        try:
            settings = SettingsRepository(storage, now_ms=lambda: 1)
            accepted = await settings.initialize_if_absent(
                profile_id="p" * 128, model_id="m" * 256, reasoning_effort="e" * 64
            )
            self.assertEqual("p" * 128, accepted.record.profile_id)
            self.assertEqual("m" * 256, accepted.record.model_id)
            self.assertEqual("e" * 64, accepted.record.reasoning_effort)
            for field, value in (
                ("profile_id", "p" * 129), ("profile_id", ""), ("profile_id", "p\x00"),
                ("model_id", "m" * 257), ("model_id", ""), ("model_id", "m\x00"),
                ("reasoning_effort", "e" * 65), ("reasoning_effort", ""), ("reasoning_effort", "e\x00"),
            ):
                with self.subTest(field=field, value=repr(value)):
                    kwargs = {"profile_id": "p", "model_id": "m", "reasoning_effort": "e"}
                    kwargs[field] = value
                    with self.assertRaises(RepositoryError) as raised:
                        await settings.initialize_if_absent(**kwargs)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(accepted.record, (await settings.get()))
        finally:
            await storage.close()

        storage = await self.open()
        try:
            runtime = ControllerRuntimeRepository(storage, now_ms=lambda: 1)
            accepted = await runtime.begin_boot("f" * 128)
            for value in ("f" * 129, "", "f\x00"):
                with self.subTest(field="fleet_version", value=repr(value)):
                    with self.assertRaises(RepositoryError) as raised:
                        await runtime.begin_boot(value)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(accepted.record, await runtime.get())
        finally:
            await storage.close()

        storage = await self.open()
        try:
            dialogue = DialogueRepository(storage, now_ms=lambda: 1)
            await storage.write(lambda c: (c.execute("DELETE FROM dialogues"), None)[1])
            await dialogue.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            accepted = await dialogue.confirm_created(
                dialogue_id="d", expected_version=0, thread_id="t" * 512
            )
            self.assertEqual("t" * 512, accepted.thread_id)
            for value in ("t" * 513, "", "t\x00"):
                with self.subTest(field="thread_id", value=repr(value)):
                    with self.assertRaises(RepositoryError) as raised:
                        await dialogue.confirm_created(dialogue_id="d", expected_version=1, thread_id=value)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(accepted, await dialogue.get_live())
        finally:
            await storage.close()

        storage = await self.open()
        try:
            dialogue = DialogueRepository(storage, now_ms=lambda: 1)
            await storage.write(lambda c: (c.execute("DELETE FROM dialogues"), None)[1])
            await dialogue.create_intent(dialogue_id="d", server_id="s", profile_id="p")
            accepted = await dialogue.mark_create_unknown(
                dialogue_id="d", expected_version=0, error_class="A" * 128
            )
            self.assertEqual("A" * 128, accepted.last_error_class)
            for value in (
                "A" * 129, "white space", "/slash", "\\backslash", "line\nfeed", "NUL\x00value",
            ):
                with self.subTest(field="last_error_class", value=repr(value)):
                    with self.assertRaises(RepositoryError) as raised:
                        await dialogue.mark_create_error(dialogue_id="d", expected_version=1, error_class=value)
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(accepted, await dialogue.get_live())
        finally:
            await storage.close()

        storage = await self.open()
        try:
            settings = SettingsRepository(storage, now_ms=lambda: 1)
            await settings.initialize_if_absent(profile_id="p", model_id="m", reasoning_effort="e")
            self.assertEqual(1, (await settings.replace(
                expected_version=0, profile_id="p2", model_id="m2", reasoning_effort="e2"
            )).version)
            await storage.write(lambda c: (c.execute("UPDATE settings SET version = ?", (maximum,)), None)[1])
            overflow = SettingsRepository(storage, now_ms=lambda: (_ for _ in ()).throw(
                RuntimeError("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK")
            ))
            with self.assertRaises(RepositoryError) as raised:
                await overflow.replace(expected_version=maximum, profile_id="p", model_id="m", reasoning_effort="e")
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            for value in (True, False, -1, maximum + 1, 1.5):
                with self.subTest(field="expected_version", value=repr(value)):
                    with self.assertRaises(RepositoryError) as raised:
                        await settings.replace(
                            expected_version=value, profile_id="p", model_id="m", reasoning_effort="e"
                        )
                    self.assertEqual(RepositoryErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertEqual(maximum, (await settings.get()).version)
        finally:
            await storage.close()

    async def test_controller_and_dialogue_corrupt_rows_fail_closed_without_raw_values(self):
        tempdir, storage = await self.open_fresh()
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO controller_runtime VALUES (1, 0, 'SLEEP', 1.5, 'fleet', 1, 1)"
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await ControllerRuntimeRepository(storage).get()
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("1.5", str(raised.exception))
            self.assertNotIn("1.5", repr(raised.exception))
        finally:
            await storage.close()
            tempdir.cleanup()

        tempdir, storage = await self.open_fresh()
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO dialogues VALUES ('d', 1, 's', 'p', NULL, 'ERROR', 0, 1, 1, 'raw prose')"
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await DialogueRepository(storage).get_live()
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("raw prose", str(raised.exception))
            self.assertNotIn("raw prose", repr(raised.exception))
        finally:
            await storage.close()
            tempdir.cleanup()

        tempdir, storage = await self.open_fresh()
        try:
            await storage.write(lambda c: (c.execute(
                "INSERT INTO dialogues VALUES ('d', 1, 's', 'p', NULL, 'CREATING', 1.5, 1, 1, NULL)"
            ), None)[1])
            with self.assertRaises(RepositoryError) as raised:
                await DialogueRepository(storage).get_live()
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("1.5", str(raised.exception))
            self.assertNotIn("1.5", repr(raised.exception))
        finally:
            await storage.close()
            tempdir.cleanup()

    async def test_repository_object_repr_redacts_temporary_database_path(self):
        tempdir = tempfile.TemporaryDirectory()
        path = os.path.join(tempdir.name, "PRIVATE_REPOSITORY_DB_PATH_MUST_NOT_LEAK.sqlite3")
        storage = await SqliteStorage.open(path, now_ms=lambda: 1)
        try:
            for repository in (
                ControllerRuntimeRepository(storage), SettingsRepository(storage), DialogueRepository(storage),
            ):
                rendered = repr(repository)
                self.assertNotIn("PRIVATE_REPOSITORY_DB_PATH_MUST_NOT_LEAK", rendered)
                self.assertNotIn(path, rendered)
        finally:
            await storage.close()
            tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
