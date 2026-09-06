import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, ThreadOperationResult, ThreadOperationStatus, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import TurnBinding, TurnStartResult, TurnStartStatus, TurnTerminalResult, TurnTerminalStatus
from codex_control.application import (
    DialogueTurnService,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnStatus,
    SettingsMutationReason,
    SettingsMutationStatus,
    SettingsSelectionError,
    SettingsSelectionErrorCategory,
    SettingsSelectionService,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SCHEMA_V1_DDL_SHA256,
    SettingsDialogueGuardRepository,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
)
from codex_control.storage.core_repositories import MAX_SQLITE_INT


class _Clock:
    def __init__(self, value=1000):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


class _Catalog:
    def __init__(self, *, error=None, mismatch=False):
        self.error = error
        self.mismatch = mismatch
        self.calls = []

    async def get_catalog(self, profile_id, *, refresh=False):
        self.calls.append((profile_id, refresh))
        if self.error is not None:
            raise self.error
        returned_profile = "wrong-profile" if self.mismatch else profile_id
        models = (
            CodexModelDescriptor("model-a", "PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", "Model A", ("low", "high"), "high", True, False),
            CodexModelDescriptor("model-b", "wire-b", "Model B", ("low",), "low", False, False),
            CodexModelDescriptor("hidden", "hidden-wire", "Hidden", ("high",), "high", False, True),
        )
        return CodexModelCatalog(returned_profile, 1, models, 0.0, 100.0)


class _Workdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class _Thread:
    def __init__(self, gate=None):
        self.calls = []
        self.gate = gate

    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        self.calls.append((profile_id, model_id, reasoning_effort))
        if self.gate is not None:
            await self.gate.wait()
        return ThreadOperationResult(
            ThreadOperationStatus.START_CONFIRMED,
            ThreadBinding(profile_id, "thread-a"),
            model_id=model_id,
            reasoning_effort=reasoning_effort,
        )


class _Turns:
    def __init__(self):
        self.start_calls = []
        self.wait_calls = []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        binding = kwargs["thread_binding"]
        return TurnStartResult(TurnStartStatus.CONFIRMED, TurnBinding(binding.profile_id, binding.thread_id, "turn-a"))

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        return TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())


class SettingsSelectionApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        self.clock = _Clock()
        self.catalog = _Catalog()
        self.profiles = (
            CodexProfile("profile-a", "/PRIVATE/CODEX_HOME/A", "Profile A"),
            CodexProfile("profile-b", "/PRIVATE/CODEX_HOME/B", "Profile B"),
            CodexProfile("profile-c", "/PRIVATE/CODEX_HOME/C", "Profile C"),
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, *, catalog=None, clock=None):
        return SettingsSelectionService(
            self.storage,
            server_id="server",
            profiles=self.profiles,
            model_catalog=catalog or self.catalog,
            now_ms=clock or self.clock,
        )

    async def settings(self, profile="profile-a", model="model-a", effort="high"):
        return await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id=profile, model_id=model, reasoning_effort=effort
        )

    async def clear(self, *, profile="profile-a", model="model-a", effort="high"):
        await self.storage.write(lambda c: (
            c.execute("DELETE FROM turn_jobs"),
            c.execute("DELETE FROM transient_payloads"),
            c.execute("DELETE FROM ingress_updates"),
            c.execute("DELETE FROM dialogues"),
            c.execute("DELETE FROM settings"),
            None,
        )[-1])
        self.clock.calls = 0
        await self.settings(profile, model, effort)

    async def put_dialogue_state(self, state: DialogueState, *, profile="profile-a", server="server"):
        dialogue = await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="dialogue", server_id=server, profile_id=profile
        )
        thread_id = None if state in (DialogueState.CREATING, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR) else "thread"
        error = "CODEX_AMBIGUOUS" if state in (DialogueState.CREATE_UNKNOWN, DialogueState.DELETE_UNKNOWN) else (
            "CODEX_PROCESS" if state is DialogueState.ERROR else None
        )
        await self.storage.write(lambda c: (
            c.execute(
                "UPDATE dialogues SET thread_id = ?, state = ?, last_error_class = ? WHERE dialogue_id = ?",
                (thread_id, state.value, error, dialogue.dialogue_id),
            ),
            None,
        )[-1])
        return await DialogueRepository(self.storage).get_live()

    async def test_view_profiles_catalog_and_fail_closed(self):
        view = await self.service().get_view(refresh=False)
        self.assertIsNone(view.settings)
        self.assertEqual(("profile-a", "profile-b", "profile-c"), tuple(option.profile_id for option in view.profiles))
        self.assertFalse(view.catalog_available)
        await self.settings()
        view = await self.service().get_view(refresh=True)
        self.assertTrue(view.catalog_available)
        self.assertEqual(("model-a", "model-b"), tuple(option.model_id for option in view.models))
        self.assertEqual([("profile-a", True)], self.catalog.calls[-1:])
        unavailable = await self.service(catalog=_Catalog(error=RuntimeError("PRIVATE_CATALOG_ERROR_MUST_NOT_LEAK"))).get_view()
        self.assertEqual(((), False), (unavailable.models, unavailable.catalog_available))
        mismatched = await self.service(catalog=_Catalog(mismatch=True)).get_view()
        self.assertEqual(((), False), (mismatched.models, mismatched.catalog_available))

    async def test_profile_no_change_change_and_unknown(self):
        current = await self.settings()
        result = await self.service().select_profile("profile-a", expected_version=current.record.version)
        self.assertEqual((SettingsMutationStatus.NO_CHANGE, current.record), (result.status, result.settings))
        self.assertEqual(0, self.clock.calls)
        unknown = await self.service().select_profile("missing", expected_version=0)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.PROFILE_NOT_CONFIGURED), (unknown.status, unknown.reason))
        result = await self.service().select_profile("profile-b", expected_version=0)
        self.assertEqual(SettingsMutationStatus.UPDATED, result.status)
        self.assertEqual(("profile-b", None, None, 1), (result.settings.profile_id, result.settings.model_id, result.settings.reasoning_effort, result.settings.version))
        self.assertEqual(1, self.clock.calls)

    async def test_profile_precedence_establishes_settings_authority_first(self):
        async def wipe():
            await self.storage.write(lambda c: (
                c.execute("DELETE FROM turn_jobs"),
                c.execute("DELETE FROM transient_payloads"),
                c.execute("DELETE FROM ingress_updates"),
                c.execute("DELETE FROM dialogues"),
                c.execute("DELETE FROM settings"),
                None,
            )[-1])

        await wipe()
        self.clock.calls = 0
        self.catalog.calls.clear()
        configured_missing = await self.service().select_profile("profile-b", expected_version=0)
        unknown_missing = await self.service().select_profile("unknown-profile", expected_version=0)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.SETTINGS_MISSING),
                         (configured_missing.status, configured_missing.reason))
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.SETTINGS_MISSING),
                         (unknown_missing.status, unknown_missing.reason))
        self.assertEqual(0, self.clock.calls)
        self.assertEqual([], self.catalog.calls)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())

        current = await self.settings()
        self.clock.calls = 0
        self.catalog.calls.clear()
        configured_stale = await self.service().select_profile("profile-b", expected_version=9)
        unknown_stale = await self.service().select_profile("unknown-profile", expected_version=9)
        for result in (configured_stale, unknown_stale):
            self.assertEqual((SettingsMutationStatus.CONFLICT, SettingsMutationReason.STALE_SETTINGS),
                             (result.status, result.reason))
        self.assertEqual(0, self.clock.calls)
        self.assertEqual([], self.catalog.calls)
        self.assertEqual(current.record, await SettingsRepository(self.storage).get())

        self.clock.calls = 0
        self.catalog.calls.clear()
        unknown_current = await self.service().select_profile("unknown-profile", expected_version=0)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.PROFILE_NOT_CONFIGURED),
                         (unknown_current.status, unknown_current.reason))
        self.assertEqual(current.record, unknown_current.settings)
        self.assertEqual(0, self.clock.calls)
        self.assertEqual([], self.catalog.calls)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())

    async def test_profile_change_is_locked_by_every_live_state(self):
        states = (
            DialogueState.CREATING, DialogueState.IDLE, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR,
            DialogueState.TURN_RUNNING, DialogueState.INTERRUPTING, DialogueState.TURN_UNKNOWN,
            DialogueState.DELETE_PENDING, DialogueState.DELETING, DialogueState.DELETE_UNKNOWN,
        )
        for state in states:
            await self.clear()
            await self.put_dialogue_state(state)
            result = await self.service().select_profile("profile-b", expected_version=0)
            self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.PROFILE_LOCKED), (result.status, result.reason), state)
            self.assertEqual(0, self.clock.calls)
            self.assertEqual("profile-a", (await SettingsRepository(self.storage).get()).profile_id)

    async def test_model_selection_authentication_default_reset_and_no_change(self):
        await self.settings(model="model-a", effort="low")
        result = await self.service().select_model("model-b", expected_version=0)
        self.assertEqual((SettingsMutationStatus.UPDATED, "model-b", "low", 1), (result.status, result.settings.model_id, result.settings.reasoning_effort, result.settings.version))
        self.assertEqual(("profile-a", True), self.catalog.calls[-1])
        self.assertEqual(1, self.clock.calls)
        self.clock.calls = 0
        result = await self.service().select_model("model-b", expected_version=1)
        self.assertEqual(SettingsMutationStatus.NO_CHANGE, result.status)
        self.assertEqual(0, self.clock.calls)
        self.assertEqual(SettingsMutationStatus.BLOCKED, (await self.service().select_model("hidden", expected_version=1)).status)
        self.assertEqual(SettingsMutationStatus.BLOCKED, (await self.service().select_model("unknown", expected_version=1)).status)

    async def test_model_and_reasoning_lock_matrix_and_idle_success(self):
        await self.settings()
        for state in (
            DialogueState.CREATING, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR,
            DialogueState.TURN_RUNNING, DialogueState.INTERRUPTING, DialogueState.TURN_UNKNOWN,
            DialogueState.DELETE_PENDING, DialogueState.DELETING, DialogueState.DELETE_UNKNOWN,
        ):
            await self.clear()
            await self.put_dialogue_state(state)
            result = await self.service().select_model("model-b", expected_version=0)
            self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.DIALOGUE_NOT_IDLE), (result.status, result.reason), state)
        await self.clear()
        await self.put_dialogue_state(DialogueState.IDLE)
        result = await self.service().select_model("model-b", expected_version=0)
        self.assertEqual(SettingsMutationStatus.UPDATED, result.status)
        result = await self.service().select_reasoning_effort("low", expected_version=1)
        self.assertEqual(SettingsMutationStatus.NO_CHANGE, result.status)

    async def test_reasoning_non_idle_matrix_is_an_independent_real_mutation_check(self):
        states = (
            DialogueState.CREATING, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR,
            DialogueState.TURN_RUNNING, DialogueState.INTERRUPTING, DialogueState.TURN_UNKNOWN,
            DialogueState.DELETE_PENDING, DialogueState.DELETING, DialogueState.DELETE_UNKNOWN,
        )
        for state in states:
            await self.clear(model="model-a", effort="high")
            await self.put_dialogue_state(state)
            before_settings = await SettingsRepository(self.storage).get()
            before_dialogue = await DialogueRepository(self.storage).get_live()
            self.clock.calls = 0
            result = await self.service().select_reasoning_effort("low", expected_version=0)
            self.assertEqual(
                (SettingsMutationStatus.BLOCKED, SettingsMutationReason.DIALOGUE_NOT_IDLE),
                (result.status, result.reason), state,
            )
            self.assertEqual(before_settings, await SettingsRepository(self.storage).get())
            self.assertEqual(before_dialogue, await DialogueRepository(self.storage).get_live())
            self.assertEqual(0, self.clock.calls)

    async def test_idle_reasoning_selection_is_a_real_mutation_and_preserves_dialogue(self):
        await self.settings(model="model-a", effort="high")
        dialogue = await self.put_dialogue_state(DialogueState.IDLE)
        self.clock.calls = 0
        result = await self.service().select_reasoning_effort("low", expected_version=0)
        self.assertEqual((SettingsMutationStatus.UPDATED, "model-a", "low", 1),
                         (result.status, result.settings.model_id, result.settings.reasoning_effort, result.settings.version))
        self.assertEqual(dialogue, await DialogueRepository(self.storage).get_live())
        self.assertEqual(1, self.clock.calls)
        self.assertEqual([("profile-a", True)], self.catalog.calls[-1:])

    async def test_same_model_non_default_effort_resets_and_default_is_no_change(self):
        await self.settings(model="model-a", effort="low")
        dialogue = await self.put_dialogue_state(DialogueState.IDLE)
        self.clock.calls = 0
        result = await self.service().select_model("model-a", expected_version=0)
        self.assertEqual((SettingsMutationStatus.UPDATED, "model-a", "high", 1),
                         (result.status, result.settings.model_id, result.settings.reasoning_effort, result.settings.version))
        self.assertEqual([("profile-a", True)], self.catalog.calls[-1:])
        self.assertEqual(1, self.clock.calls)
        self.assertEqual(dialogue, await DialogueRepository(self.storage).get_live())

        self.clock.calls = 0
        result = await self.service().select_model("model-a", expected_version=1)
        self.assertEqual(SettingsMutationStatus.NO_CHANGE, result.status)
        self.assertEqual(0, self.clock.calls)

    async def test_reasoning_validation_missing_model_unsupported_and_success(self):
        await self.clear(model=None, effort=None)
        result = await self.service().select_reasoning_effort("high", expected_version=0)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.MODEL_NOT_CONFIGURED), (result.status, result.reason))
        await self.clear(model="model-a", effort="high")
        result = await self.service().select_reasoning_effort("low", expected_version=0)
        self.assertEqual((SettingsMutationStatus.UPDATED, "low", 1), (result.status, result.settings.reasoning_effort, result.settings.version))
        result = await self.service().select_reasoning_effort("unsupported", expected_version=1)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.REASONING_EFFORT_UNSUPPORTED), (result.status, result.reason))
        self.assertEqual(1, (await self.service(catalog=_Catalog(error=RuntimeError("PRIVATE_CATALOG_ERROR_MUST_NOT_LEAK"))).select_reasoning_effort("high", expected_version=1)).reason is SettingsMutationReason.MODEL_UNAVAILABLE)

    async def test_stale_conflict_blocked_and_no_change_do_not_call_clock(self):
        await self.settings()
        self.clock.calls = 0
        result = await self.service().select_profile("profile-b", expected_version=9)
        self.assertEqual((SettingsMutationStatus.CONFLICT, SettingsMutationReason.STALE_SETTINGS), (result.status, result.reason))
        self.assertEqual(0, self.clock.calls)
        result = await self.service().select_model("model-b", expected_version=0)
        self.assertEqual(1, self.clock.calls)
        self.clock.calls = 0
        result = await self.service().select_model("model-b", expected_version=1)
        self.assertEqual(SettingsMutationStatus.NO_CHANGE, result.status)
        self.assertEqual(0, self.clock.calls)

    async def test_same_version_concurrent_mutations_have_one_winner(self):
        await self.settings()
        first, second = await asyncio.gather(
            self.service().select_profile("profile-b", expected_version=0),
            self.service().select_profile("profile-c", expected_version=0),
        )
        self.assertEqual(1, sum(item.status is SettingsMutationStatus.UPDATED for item in (first, second)))
        self.assertEqual(1, sum(item.status is SettingsMutationStatus.CONFLICT for item in (first, second)))
        self.assertEqual(1, (await SettingsRepository(self.storage).get()).version)

    async def test_cross_profile_corruption_fails_closed_and_guard_persists(self):
        await self.settings(profile="profile-b")
        await self.put_dialogue_state(DialogueState.IDLE, profile="profile-a")
        with self.assertRaises(SettingsSelectionError) as raised:
            await self.service().select_model("model-b", expected_version=0)
        self.assertEqual(SettingsSelectionErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(0, self.clock.calls)
        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        self.assertEqual("profile-b", (await SettingsRepository(self.storage).get()).profile_id)

    async def test_profile_guard_materializes_corrupt_dialogue_before_lock_result(self):
        before = await self.settings()
        await self.put_dialogue_state(DialogueState.IDLE)
        await self.storage.write(lambda c: (
            c.execute(
                "UPDATE dialogues SET thread_id = NULL, state = 'DELETE_PENDING', "
                "last_error_class = ? WHERE dialogue_id = 'dialogue'",
                ("PRIVATE_CORRUPT_DIALOGUE_MUST_NOT_LEAK",),
            ), None,
        )[-1])
        self.clock.calls = 0
        with self.assertRaises(RepositoryError) as raised:
            await SettingsDialogueGuardRepository(self.storage, now_ms=self.clock).replace_profile_no_dialogue(
                expected_version=0, profile_id="profile-b"
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertNotIn("PRIVATE_CORRUPT_DIALOGUE_MUST_NOT_LEAK", str(raised.exception) + repr(raised.exception))
        self.assertEqual(before.record, await SettingsRepository(self.storage).get())
        self.assertEqual(0, self.clock.calls)

    async def test_create_guard_materializes_corrupt_dialogue_before_already_exists(self):
        before = await self.settings()
        await self.put_dialogue_state(DialogueState.IDLE)
        await self.storage.write(lambda c: (
            c.execute(
                "UPDATE dialogues SET thread_id = NULL, state = 'DELETE_PENDING', "
                "last_error_class = ? WHERE dialogue_id = 'dialogue'",
                ("PRIVATE_CORRUPT_DIALOGUE_MUST_NOT_LEAK",),
            ), None,
        )[-1])
        self.clock.calls = 0
        with self.assertRaises(RepositoryError) as raised:
            await SettingsDialogueGuardRepository(self.storage, now_ms=self.clock).create_dialogue_if_settings_current(
                dialogue_id="new-dialogue", server_id="server", profile_id="profile-a",
                expected_settings_version=0, expected_model_id="model-a", expected_reasoning_effort="high",
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertNotIn("PRIVATE_CORRUPT_DIALOGUE_MUST_NOT_LEAK", str(raised.exception) + repr(raised.exception))
        self.assertEqual(before.record, await SettingsRepository(self.storage).get())
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0]))
        self.assertEqual(0, self.clock.calls)

    async def test_guard_materializes_corrupt_settings_as_invariant(self):
        await self.settings()
        corrupt = "PRIVATE_CORRUPT_SETTINGS_VALUE\x00MUST_NOT_LEAK"
        await self.storage.write(lambda c: (
            c.execute("UPDATE settings SET profile_id = ?", (corrupt,)), None
        )[-1])
        self.clock.calls = 0
        with self.assertRaises(RepositoryError) as raised:
            await SettingsDialogueGuardRepository(self.storage, now_ms=self.clock).replace_profile_no_dialogue(
                expected_version=0, profile_id="profile-b"
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertNotIn(corrupt, str(raised.exception) + repr(raised.exception))
        stored = await self.storage.read(lambda c: tuple(c.execute(
            "SELECT profile_id, version FROM settings"
        ).fetchone()))
        self.assertEqual((corrupt, 0), stored)
        self.assertEqual(0, self.clock.calls)

    async def test_guard_corruption_categories_are_redacted(self):
        await self.settings()
        with self.assertRaises(RepositoryError) as raised:
            await SettingsDialogueGuardRepository(self.storage, now_ms=self.clock).create_dialogue_if_settings_current(
                dialogue_id="d", server_id="server", profile_id="profile-b", expected_settings_version=0,
                expected_model_id="model-a", expected_reasoning_effort="high",
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertNotIn("PRIVATE", repr(raised.exception))

    async def test_clock_failures_are_finite_and_do_not_commit(self):
        await self.settings()
        for value in (True, False, -1, 2**63, 1.0, "not-an-int", RuntimeError("PRIVATE_CLOCK_SENTINEL")):
            clock = _Clock(value)
            with self.subTest(value=repr(value)), self.assertRaises(SettingsSelectionError) as raised:
                await self.service(clock=clock).select_profile("profile-b", expected_version=0)
            self.assertEqual(SettingsSelectionErrorCategory.STORAGE, raised.exception.category)
            self.assertNotIn("PRIVATE_CLOCK_SENTINEL", repr(raised.exception))
            self.assertEqual(0, (await SettingsRepository(self.storage).get()).version)

    async def test_clock_zero_and_signed_64_max_are_valid_and_monotonic(self):
        await self.settings(model="model-a", effort="high")
        self.clock.value = 0
        self.clock.calls = 0
        zero = await self.service().select_reasoning_effort("low", expected_version=0)
        self.assertEqual(SettingsMutationStatus.UPDATED, zero.status)
        self.assertEqual(10, zero.settings.updated_at_ms)
        self.assertEqual(1, self.clock.calls)

        await self.clear(model="model-a", effort="high")
        self.clock.value = MAX_SQLITE_INT
        self.clock.calls = 0
        maximum = await self.service().select_profile("profile-b", expected_version=0)
        self.assertEqual(SettingsMutationStatus.UPDATED, maximum.status)
        self.assertEqual(MAX_SQLITE_INT, maximum.settings.updated_at_ms)
        self.assertEqual(1, self.clock.calls)

    async def test_settings_version_max_fails_closed_without_wrap_or_clock(self):
        await self.settings()
        await self.storage.write(lambda c: (
            c.execute("UPDATE settings SET version = ?", (MAX_SQLITE_INT,)), None
        )[-1])
        self.clock.calls = 0
        with self.assertRaises(SettingsSelectionError) as raised:
            await self.service().select_profile("profile-b", expected_version=MAX_SQLITE_INT)
        self.assertEqual(SettingsSelectionErrorCategory.INVARIANT, raised.exception.category)
        current = await self.storage.read(lambda c: tuple(c.execute(
            "SELECT profile_id, model_id, reasoning_effort, version FROM settings"
        ).fetchone()))
        self.assertEqual(("profile-a", "model-a", "high", MAX_SQLITE_INT), current)
        self.assertEqual(0, self.clock.calls)

    async def test_profile_mutation_wins_p3_2_race_has_no_effects(self):
        await self.settings()
        entered, release = asyncio.Event(), asyncio.Event()
        original = SettingsDialogueGuardRepository.create_dialogue_if_settings_current

        async def gated(repo, **kwargs):
            entered.set()
            await release.wait()
            return await original(repo, **kwargs)

        thread, turns = _Thread(), _Turns()
        service = DialogueTurnService(
            self.storage, server_id="server", profiles=self.profiles, model_catalog=self.catalog,
            thread_lifecycle=thread, turn_lifecycle=turns, working_directory_resolver=_Workdir(),
            now_ms=self.clock, id_factory=lambda kind: f"p3-{kind}",
        )
        with patch.object(SettingsDialogueGuardRepository, "create_dialogue_if_settings_current", gated):
            task = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(1, -1, 1, "first")))
            await entered.wait()
            mutation = await self.service().select_profile("profile-b", expected_version=0)
            self.assertEqual(SettingsMutationStatus.UPDATED, mutation.status)
            release.set()
            result = await task
        self.assertEqual((ExistingDialogueTurnStatus.BLOCKED, "SETTINGS_CHANGED"), (result.status, result.reason.value))
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM transient_payloads WHERE kind = 'INPUT'").fetchone()[0]))
        self.assertEqual([], thread.calls)
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)
        self.assertEqual([], [item for item in asyncio.all_tasks() if item is not asyncio.current_task() and not item.done()])

    async def test_p3_2_create_wins_profile_is_locked_then_completes(self):
        await self.settings()
        entered, release = asyncio.Event(), asyncio.Event()
        original = SettingsDialogueGuardRepository.create_dialogue_if_settings_current

        async def gated(repo, **kwargs):
            created = await original(repo, **kwargs)
            entered.set()
            await release.wait()
            return created

        thread, turns = _Thread(), _Turns()
        service = DialogueTurnService(
            self.storage, server_id="server", profiles=self.profiles, model_catalog=self.catalog,
            thread_lifecycle=thread, turn_lifecycle=turns, working_directory_resolver=_Workdir(),
            now_ms=self.clock, id_factory=lambda kind: f"p3-{kind}",
        )
        with patch.object(SettingsDialogueGuardRepository, "create_dialogue_if_settings_current", gated):
            task = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(2, -1, 1, "first")))
            await entered.wait()
            mutation = await self.service().select_profile("profile-b", expected_version=0)
            self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.PROFILE_LOCKED), (mutation.status, mutation.reason))
            release.set()
            result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual("profile-a", (await SettingsRepository(self.storage).get()).profile_id)
        self.assertEqual("profile-a", (await DialogueRepository(self.storage).get_live()).profile_id)
        self.assertEqual(1, len(thread.calls))
        self.assertEqual(1, len(turns.start_calls))

    async def test_admitted_job_snapshot_survives_settings_change(self):
        await self.settings()
        dialogue = await self.put_dialogue_state(DialogueState.IDLE)
        entered, release = asyncio.Event(), asyncio.Event()
        original = TurnJobRepository.claim_ingress

        async def gated(repo, **kwargs):
            admitted = await original(repo, **kwargs)
            entered.set()
            await release.wait()
            return admitted

        turns = _Turns()
        from codex_control.application import ExistingDialogueTurnService
        existing = ExistingDialogueTurnService(
            self.storage, server_id="server", profiles=self.profiles, model_catalog=self.catalog,
            turn_lifecycle=turns, working_directory_resolver=_Workdir(), now_ms=self.clock,
            id_factory=lambda kind: f"job-{kind}",
        )
        with patch.object(TurnJobRepository, "claim_ingress", gated):
            task = asyncio.create_task(existing.execute(ExistingDialoguePromptRequest(3, -1, 1, "turn")))
            await entered.wait()
            mutation = await self.service().select_model("model-b", expected_version=0)
            self.assertEqual(SettingsMutationStatus.UPDATED, mutation.status)
            release.set()
            result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual(("model-a", "high"), (result.job.model_id, result.job.reasoning_effort))
        self.assertEqual(("model-a", "high"), (turns.start_calls[0]["model_id"], turns.start_calls[0]["reasoning_effort"]))
        current = await SettingsRepository(self.storage).get()
        self.assertEqual(("model-b", "low"), (current.model_id, current.reasoning_effort))
        self.assertEqual(dialogue.profile_id, result.job.profile_id)

    async def test_turn_running_selection_is_blocked(self):
        await self.settings()
        await self.put_dialogue_state(DialogueState.TURN_RUNNING)
        self.clock.calls = 0
        result = await self.service().select_reasoning_effort("low", expected_version=0)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.DIALOGUE_NOT_IDLE), (result.status, result.reason))
        self.assertEqual(0, self.clock.calls)

    async def test_ddl_is_unchanged(self):
        self.assertEqual("b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c", SCHEMA_V1_DDL_SHA256)


if __name__ == "__main__":
    unittest.main()
