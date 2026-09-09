import asyncio
import os
import tempfile
import unittest

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor, ModelCatalogError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.application import (
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    RetentionRepository,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnIngressClaimStatus,
    TurnTerminalOutcome,
    TurnJobRepository,
    TurnJobState,
)


class FakeCatalog:
    def __init__(self, *, profile="profile", hidden=False, effort="high", supported=("low", "high"), gate=None, error=None):
        self.profile = profile
        self.hidden = hidden
        self.effort = effort
        self.supported = supported
        self.gate = gate
        self.error = error
        self.calls = 0

    async def get_catalog(self, profile_id, *, refresh=False):
        self.calls += 1
        if self.gate is not None:
            await self.gate(self.calls)
        if self.error is not None:
            raise self.error
        return CodexModelCatalog(
            self.profile, 1,
            (CodexModelDescriptor("model", "wire-model", "Model", self.supported, self.effort, True, self.hidden),),
            0.0, 100.0,
        )


class FakeWorkdir:
    def __init__(self, value=TrustedWorkingDirectory("/trusted"), error=None):
        self.value = value
        self.error = error
        self.calls = 0

    def resolve(self, profile_id):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.value


class FakeTurns:
    def __init__(self, *, start=TurnStartStatus.CONFIRMED, terminal=TurnTerminalStatus.COMPLETED, messages=(), start_error=None, wait_error=None, wait_gate=None, start_event=None, wait_event=None, binding=None):
        self.start = start
        self.terminal = terminal
        self.messages = tuple(messages)
        self.start_error = start_error
        self.wait_error = wait_error
        self.wait_gate = wait_gate
        self.start_event = start_event
        self.wait_event = wait_event
        self.binding = binding or TurnBinding("profile", "thread", "turn")
        self.start_calls = []
        self.wait_calls = []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        if self.start_event:
            self.start_event.set()
        if self.start_error:
            raise self.start_error
        if self.start is TurnStartStatus.REJECTED:
            return TurnStartResult(TurnStartStatus.REJECTED)
        if self.start is TurnStartStatus.UNKNOWN:
            return TurnStartResult(TurnStartStatus.UNKNOWN)
        return TurnStartResult(TurnStartStatus.CONFIRMED, self.binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if self.wait_event:
            self.wait_event.set()
        if self.wait_gate:
            await self.wait_gate.wait()
        if self.wait_error:
            raise self.wait_error
        return TurnTerminalResult(binding, self.terminal, self.messages)


class ExistingDialogueApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.clock_value = 1_000
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: self.clock_value)
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(dialogue_id="dialogue", server_id="server", profile_id="profile")
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(dialogue_id="dialogue", expected_version=0, thread_id="thread")
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(profile_id="profile", model_id="model", reasoning_effort="high")

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, catalog=None, turns=None, workdir=None, ids=None, clock=None):
        sequence = iter(range(1000))
        return ExistingDialogueTurnService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/private/CODEX_HOME", "Profile"),),
            model_catalog=catalog or FakeCatalog(),
            turn_lifecycle=turns or FakeTurns(),
            working_directory_resolver=workdir or FakeWorkdir(),
            now_ms=clock or (lambda: self.clock_value),
            id_factory=ids or (lambda kind: f"{kind}-{next(sequence)}"),
        )

    async def assert_no_admission(self, update_id, turns):
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(update_id))
        self.assertEqual(0, await self.storage.read(
            lambda connection: connection.execute(
                "SELECT COUNT(*) FROM turn_jobs WHERE telegram_update_id = ?", (update_id,)
            ).fetchone()[0]
        ))
        self.assertEqual(0, await self.storage.read(
            lambda connection: connection.execute(
                "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'INPUT'"
            ).fetchone()[0]
        ))
        self.assertEqual(0, len(turns.start_calls))

    async def test_no_dialogue_blocks_with_no_admission(self):
        await self.storage.write(lambda connection: (connection.execute("DELETE FROM dialogues"), None)[1])
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(3, -1, 3, "x"))
        self.assertEqual((ExistingDialogueTurnStatus.BLOCKED, ExistingDialogueTurnReason.NO_DIALOGUE), (result.status, result.reason))
        await self.assert_no_admission(3, turns)

    async def test_happy_path_order_snapshot_and_output(self):
        class OrderedTurns(FakeTurns):
            async def start_turn(inner, **kwargs):
                ingress = await IngressUpdateRepository(self.storage).get(1)
                job = await TurnJobRepository(self.storage).get(ingress.job_id)
                dialogue = await DialogueRepository(self.storage).get_live()
                self.assertEqual(TurnJobState.CODEX_STARTING, job.state)
                self.assertEqual(DialogueState.TURN_RUNNING, dialogue.state)
                return await super(OrderedTurns, inner).start_turn(**kwargs)
        turns = OrderedTurns(messages=(AgentMessageCompleted(1, "a", "PRIVATE_OUTPUT_P3_1"), AgentMessageCompleted(2, "b", "second")))
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(1, -100, 2, "PRIVATE_PROMPT_P3_1"))
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual(b"PRIVATE_OUTPUT_P3_1\n\nsecond", result.output_payload.content)
        self.assertNotIn("PRIVATE_OUTPUT_P3_1", repr(result))
        self.assertNotIn("PRIVATE_OUTPUT_P3_1", repr(result.output_payload))
        self.assertEqual(("model", "high"), (result.job.model_id, result.job.reasoning_effort))
        self.assertEqual(1, len(turns.start_calls))
        self.assertEqual([TurnBinding("profile", "thread", "turn")], turns.wait_calls)
        self.assertEqual(DialogueState.IDLE, result.dialogue.state)
        self.assertEqual(1, (await IngressUpdateRepository(self.storage).get(1)).update_id)
        self.assertIsNotNone(await TurnJobRepository(self.storage).get(result.job.job_id))
        self.assertEqual(result.job.input_sha256, (await TransientPayloadRepository(self.storage).get_input_for_job(result.job.job_id)).content_sha256)

    async def test_default_effort_is_explicitly_captured(self):
        await SettingsRepository(self.storage).replace(expected_version=0, profile_id="profile", model_id="model", reasoning_effort=None)
        turns = FakeTurns()
        result = await self.service(catalog=FakeCatalog(effort="high", supported=("high",)), turns=turns).execute(ExistingDialoguePromptRequest(2, -1, 2, "x"))
        self.assertEqual("high", result.job.reasoning_effort)
        self.assertEqual("high", turns.start_calls[0]["reasoning_effort"])

    async def test_hidden_missing_and_unsupported_models_block_before_admission(self):
        for index, catalog in enumerate((FakeCatalog(hidden=True), FakeCatalog(error=ModelCatalogError("model_not_available")), FakeCatalog(supported=("low",), effort="low")), 10):
            if index != 10:
                await self._reset()
            if index == 12:
                await SettingsRepository(self.storage).replace(expected_version=0, profile_id="profile", model_id="model", reasoning_effort="high")
            turns = FakeTurns()
            result = await self.service(catalog=catalog, turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual((ExistingDialogueTurnStatus.BLOCKED, ExistingDialogueTurnReason.MODEL_UNAVAILABLE), (result.status, result.reason))
            await self.assert_no_admission(index, turns)

    async def test_full_non_idle_and_preflight_block_matrix(self):
        states = (DialogueState.CREATING, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR, DialogueState.INTERRUPTING, DialogueState.TURN_UNKNOWN, DialogueState.DELETE_PENDING, DialogueState.DELETING, DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, DialogueState.DELETE_UNKNOWN)
        for index, state in enumerate(states, 30):
            await self._reset()
            await self._set_dialogue_state(state)
            turns = FakeTurns()
            result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual((ExistingDialogueTurnStatus.BLOCKED, ExistingDialogueTurnReason.DIALOGUE_NOT_READY), (result.status, result.reason))
            await self.assert_no_admission(index, turns)

    async def test_turn_running_is_busy_and_no_queue(self):
        await self._set_dialogue_state(DialogueState.TURN_RUNNING)
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(50, -1, 50, "x"))
        self.assertEqual((ExistingDialogueTurnStatus.BUSY, None), (result.status, result.reason))
        await self.assert_no_admission(50, turns)

    async def test_settings_profile_and_workdir_matrix(self):
        await self.storage.write(lambda c: (c.execute("DELETE FROM settings"), None)[1])
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(60, -1, 60, "x"))
        self.assertEqual(ExistingDialogueTurnReason.SETTINGS_MISSING, result.reason)
        await self.assert_no_admission(60, turns)
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(profile_id=None, model_id="model", reasoning_effort="high")
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(61, -1, 61, "x"))
        self.assertEqual(ExistingDialogueTurnReason.SETTINGS_PROFILE_MISMATCH, result.reason)
        await self.assert_no_admission(61, turns)
        await SettingsRepository(self.storage).replace(expected_version=0, profile_id="other", model_id="model", reasoning_effort="high")
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(62, -1, 62, "x"))
        self.assertEqual(ExistingDialogueTurnReason.SETTINGS_PROFILE_MISMATCH, result.reason)
        await self.assert_no_admission(62, turns)
        await SettingsRepository(self.storage).replace(expected_version=1, profile_id="profile", model_id="model", reasoning_effort="high")
        workdir = FakeWorkdir(error=RuntimeError("PRIVATE_WORKDIR_ERROR"))
        turns = FakeTurns()
        result = await self.service(workdir=workdir, turns=turns).execute(ExistingDialoguePromptRequest(63, -1, 63, "x"))
        self.assertEqual(ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE, result.reason)
        await self.assert_no_admission(63, turns)

    async def test_profile_not_configured_model_not_configured_and_invalid_workdir_block(self):
        no_profile_service = ExistingDialogueTurnService(
            self.storage, server_id="server", profiles=(), model_catalog=FakeCatalog(),
            turn_lifecycle=FakeTurns(), working_directory_resolver=FakeWorkdir(), now_ms=lambda: self.clock_value,
        )
        result = await no_profile_service.execute(ExistingDialoguePromptRequest(64, -1, 64, "x"))
        self.assertEqual(ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED, result.reason)
        await self.assert_no_admission(64, no_profile_service._turn_lifecycle)
        await self._reset()
        await SettingsRepository(self.storage).replace(expected_version=0, profile_id="profile", model_id=None, reasoning_effort="high")
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(65, -1, 65, "x"))
        self.assertEqual(ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED, result.reason)
        await self.assert_no_admission(65, turns)
        await self._reset()
        workdir = FakeWorkdir(value=object())
        result = await self.service(workdir=workdir, turns=turns).execute(ExistingDialoguePromptRequest(66, -1, 66, "x"))
        self.assertEqual(ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE, result.reason)
        await self.assert_no_admission(66, turns)

    async def test_duplicate_first_retained_input_has_zero_configuration_effect_calls(self):
        turns = FakeTurns()
        original = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(70, -1, 7, "original"))
        catalog = FakeCatalog()
        workdir = FakeWorkdir()
        calls = {"clock": 0, "id": 0}
        def clock():
            calls["clock"] += 1
            raise AssertionError("clock")
        def ids(kind):
            calls["id"] += 1
            raise AssertionError("id")
        duplicate_turns = FakeTurns()
        replay = await self.service(catalog=catalog, workdir=workdir, turns=duplicate_turns, clock=clock, ids=ids).execute(ExistingDialoguePromptRequest(70, -999, 999, "PRIVATE_PROMPT_P3_1"))
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, replay.status)
        self.assertEqual(original.job, replay.job)
        self.assertEqual((0, 0), (catalog.calls + workdir.calls, calls["clock"] + calls["id"]))
        self.assertEqual(([], []), (duplicate_turns.start_calls, duplicate_turns.wait_calls))

    async def test_retention_compatible_duplicate_does_not_reconstruct_input(self):
        original = await self.service().execute(ExistingDialoguePromptRequest(71, -1, 7, "original"))
        self.clock_value = 3_601_001
        await RetentionRepository(self.storage, now_ms=lambda: self.clock_value).sweep(100)
        with self.assertRaises(Exception):
            await TransientPayloadRepository(self.storage).get_input_for_job(original.job.job_id)
        catalog, workdir, turns = FakeCatalog(), FakeWorkdir(), FakeTurns()
        replay = await self.service(catalog=catalog, workdir=workdir, turns=turns, clock=lambda: (_ for _ in ()).throw(AssertionError("clock")), ids=lambda kind: (_ for _ in ()).throw(AssertionError("id"))).execute(ExistingDialoguePromptRequest(71, -8, 88, "changed"))
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, replay.status)
        self.assertEqual(original.job, replay.job)
        self.assertEqual((0, 0, 0), (catalog.calls, workdir.calls, len(turns.start_calls)))

    async def test_active_missing_and_corrupt_input_are_invariants(self):
        original = (await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
            update_id=72, job_id="active-job", source_chat_id=-1, source_message_id=7,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="active-input",
            input_content=b"x", input_expires_at_ms=3_601_000,
        )).job
        await self.storage.write(lambda c: (c.execute("DELETE FROM transient_payloads WHERE job_id = ?", (original.job_id,)), None)[1])
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service().execute(ExistingDialoguePromptRequest(72, -1, 7, "x"))
        self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVARIANT)
        await self._reset()
        original = await self.service().execute(ExistingDialoguePromptRequest(73, -1, 7, "x"))
        self.clock_value = 3_601_001
        await RetentionRepository(self.storage, now_ms=lambda: self.clock_value).sweep(100)
        await self.storage.write(lambda c: (c.execute("UPDATE transient_payloads SET content = ?, byte_length = ? WHERE job_id = ? AND kind = 'OUTPUT'", (b"bad", 3, original.job.job_id)), None)[1])
        # The retained INPUT was deleted; seed a malformed INPUT row for the terminal optional job.
        await self.storage.write(lambda c: (c.execute("INSERT INTO transient_payloads(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, created_at_ms, expires_at_ms) VALUES ('bad-input','dialogue',?,?,?, ?,3,1,999999999)", (original.job.job_id, "INPUT", b"bad", "0" * 64)), None)[1])
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service().execute(ExistingDialoguePromptRequest(73, -1, 7, "x"))
        self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVARIANT)

    async def test_non_job_and_orphan_job_duplicates(self):
        from codex_control.storage import IngressDispositionKind
        await IngressUpdateRepository(self.storage, now_ms=lambda: 1).claim_ignored(update_id=80, disposition=IngressDispositionKind.IGNORED_SLEEP)
        turns = FakeTurns()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(80, -1, 1, "x"))
        self.assertEqual((ExistingDialogueTurnStatus.DUPLICATE, ExistingDialogueTurnReason.DUPLICATE_NON_JOB), (result.status, result.reason))
        original = await self.service().execute(ExistingDialoguePromptRequest(81, -1, 1, "x"))
        await self.storage.write(lambda c: (c.execute("DELETE FROM turn_jobs WHERE job_id = ?", (original.job.job_id,)), c.execute("DELETE FROM dialogues"), None)[2])
        catalog = FakeCatalog(error=AssertionError("catalog"))
        workdir = FakeWorkdir(error=AssertionError("workdir"))
        turns = FakeTurns(start_error=AssertionError("start"), wait_error=AssertionError("wait"))
        result = await self.service(
            catalog=catalog,
            workdir=workdir,
            turns=turns,
            clock=lambda: (_ for _ in ()).throw(AssertionError("clock")),
            ids=lambda kind: (_ for _ in ()).throw(AssertionError("id")),
        ).execute(ExistingDialoguePromptRequest(81, -1, 1, "x"))
        self.assertEqual((ExistingDialogueTurnStatus.DUPLICATE, ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB), (result.status, result.reason))
        self.assertEqual((0, 0, [], []), (catalog.calls, workdir.calls, turns.start_calls, turns.wait_calls))

    async def test_non_job_duplicate_has_zero_configuration_and_effect_dependencies(self):
        from codex_control.storage import IngressDispositionKind

        await IngressUpdateRepository(self.storage, now_ms=lambda: 1).claim_ignored(
            update_id=160, disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED
        )
        catalog = FakeCatalog(error=AssertionError("catalog"))
        workdir = FakeWorkdir(error=AssertionError("workdir"))
        turns = FakeTurns(start_error=AssertionError("start"), wait_error=AssertionError("wait"))
        result = await self.service(
            catalog=catalog,
            workdir=workdir,
            turns=turns,
            clock=lambda: (_ for _ in ()).throw(AssertionError("clock")),
            ids=lambda kind: (_ for _ in ()).throw(AssertionError("id")),
        ).execute(ExistingDialoguePromptRequest(160, -1, 1, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, result.status)
        self.assertIsNone(result.job)
        self.assertEqual(ExistingDialogueTurnReason.DUPLICATE_NON_JOB, result.reason)
        self.assertEqual(0, catalog.calls)
        self.assertEqual(0, workdir.calls)
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)

    async def test_orphan_job_with_live_dialogue_is_invariant_with_zero_dependencies(self):
        original = await self.service().execute(ExistingDialoguePromptRequest(161, -1, 1, "x"))
        await self.storage.write(lambda connection: (connection.execute(
            "DELETE FROM turn_jobs WHERE job_id = ?", (original.job.job_id,)
        ), None)[1])
        catalog = FakeCatalog(error=AssertionError("catalog"))
        workdir = FakeWorkdir(error=AssertionError("workdir"))
        turns = FakeTurns(start_error=AssertionError("start"), wait_error=AssertionError("wait"))
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(
                catalog=catalog,
                workdir=workdir,
                turns=turns,
                clock=lambda: (_ for _ in ()).throw(AssertionError("clock")),
                ids=lambda kind: (_ for _ in ()).throw(AssertionError("id")),
            ).execute(ExistingDialoguePromptRequest(161, -1, 1, "x"))
        self.assertIs(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(0, catalog.calls)
        self.assertEqual(0, workdir.calls)
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)

    async def test_start_result_matrix_and_local_errors(self):
        cases = ((TurnStartStatus.REJECTED, ExistingDialogueTurnStatus.FAILED), (TurnStartStatus.UNKNOWN, ExistingDialogueTurnStatus.UNKNOWN))
        for index, (start, expected) in enumerate(cases, 90):
            await self._reset()
            turns = FakeTurns(start=start)
            result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(expected, result.status)
            self.assertEqual([], turns.wait_calls)
        for index, category in enumerate(("turn_request_invalid", "turn_precondition_changed", "turn_operation_busy"), 92):
            await self._reset()
            turns = FakeTurns(start_error=TurnLifecycleError(category))
            result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(ExistingDialogueTurnStatus.FAILED, result.status)
            self.assertEqual("CODEX_PROCESS", result.job.error_class)
        await self._reset()
        turns = FakeTurns(start_error=RuntimeError("PRIVATE_ADAPTER_ERROR_P3_1"))
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(96, -1, 96, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
        self.assertNotIn("PRIVATE_ADAPTER_ERROR_P3_1", repr(result))

    async def test_binding_and_wait_failures_never_retry(self):
        for index, binding in enumerate((TurnBinding("other", "thread", "turn"), TurnBinding("profile", "other", "turn")), 100):
            await self._reset()
            turns = FakeTurns(binding=binding)
            result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
            self.assertEqual([], turns.wait_calls)
            self.assertEqual(1, len(turns.start_calls))
        await self._reset()
        turns = FakeTurns(wait_error=RuntimeError("PRIVATE_WAIT_ERROR"))
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(102, -1, 1, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
        self.assertEqual((1, 1), (len(turns.start_calls), len(turns.wait_calls)))

    async def test_mismatched_terminal_binding_is_unknown_without_retry(self):
        class MismatchedTerminal(FakeTurns):
            async def wait_turn(self, binding):
                self.wait_calls.append(binding)
                return TurnTerminalResult(TurnBinding("profile", "thread", "other"), TurnTerminalStatus.COMPLETED, ())
        turns = MismatchedTerminal()
        result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(103, -1, 1, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
        self.assertEqual((1, 1), (len(turns.start_calls), len(turns.wait_calls)))

    async def test_terminal_output_matrix_and_empty_output(self):
        for index, terminal, expected, ttl in ((110, TurnTerminalStatus.COMPLETED, ExistingDialogueTurnStatus.COMPLETED, 3_600_000), (111, TurnTerminalStatus.FAILED, ExistingDialogueTurnStatus.FAILED, 86_400_000), (112, TurnTerminalStatus.UNKNOWN, ExistingDialogueTurnStatus.UNKNOWN, 86_400_000)):
            await self._reset()
            turns = FakeTurns(terminal=terminal, messages=(AgentMessageCompleted(1, "i", "partial"),))
            result = await self.service(turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(expected, result.status)
            self.assertEqual(b"partial", result.output_payload.content)
            self.assertEqual(1000 + ttl, result.output_payload.expires_at_ms)
        await self._reset()
        turns = FakeTurns(messages=(AgentMessageCompleted(1, "i", ""),))
        id_calls = []
        def ids(kind):
            id_calls.append(kind)
            if kind == "output":
                raise AssertionError("empty output generated an OUTPUT ID")
            return f"{kind}-empty"
        result = await self.service(turns=turns, ids=ids).execute(ExistingDialoguePromptRequest(113, -1, 1, "x"))
        self.assertIsNone(result.output_payload)
        self.assertEqual(["job", "input"], id_calls)

    async def test_same_update_concurrency_has_one_job_and_effect(self):
        barrier = asyncio.Event()
        calls = 0
        async def gate(number):
            nonlocal calls
            if number == 2:
                barrier.set()
            await barrier.wait()
        turns = FakeTurns(wait_gate=asyncio.Event(), wait_event=asyncio.Event())
        service = self.service(catalog=FakeCatalog(gate=gate), turns=turns)
        first = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(120, -1, 1, "same")))
        second = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(120, -1, 2, "changed")))
        await asyncio.wait_for(asyncio.shield(turns.wait_event.wait()), 1)
        results = await asyncio.wait_for(asyncio.gather(first, asyncio.create_task(self._release_wait(turns, second))), 1)
        self.assertEqual(1, len(turns.start_calls))
        self.assertEqual(1, await self._all_jobs())
        self.assertIn(ExistingDialogueTurnStatus.DUPLICATE, {results[0].status, results[1].status})

    async def test_atomic_race_duplicate_after_input_retention_is_optional(self):
        preflight = asyncio.Event()
        release = asyncio.Event()

        async def gate(number):
            preflight.set()
            await release.wait()

        turns = FakeTurns()
        task = asyncio.create_task(self.service(catalog=FakeCatalog(gate=gate), turns=turns).execute(
            ExistingDialoguePromptRequest(150, -1, 1, "race")
        ))
        await asyncio.wait_for(asyncio.shield(preflight.wait()), 1)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(150))

        jobs = TurnJobRepository(self.storage, now_ms=lambda: self.clock_value)
        admitted = await jobs.claim_ingress(
            update_id=150, job_id="race-job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="race-input",
            input_content=b"race", input_expires_at_ms=3_601_000,
        )
        self.assertIs(TurnIngressClaimStatus.CREATED, admitted.status)
        dialogue = await DialogueRepository(self.storage).get_live()
        claimed = await jobs.claim_turn(
            job_id="race-job", expected_job_version=admitted.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread",
        )
        starting = await jobs.mark_codex_starting(job_id="race-job", expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(job_id="race-job", expected_version=starting.version, codex_turn_id="race-turn")
        completed = await jobs.finish_codex(
            job_id="race-job", expected_job_version=running.version,
            expected_dialogue_version=claimed.dialogue.version, outcome=TurnTerminalOutcome.COMPLETED,
        )
        await self.storage.write(lambda connection: (connection.execute(
            "UPDATE transient_payloads SET created_at_ms = 1, expires_at_ms = 2 WHERE payload_id = 'race-input'"
        ), None)[1])
        sweep = await RetentionRepository(self.storage, now_ms=lambda: 10).sweep(100)
        self.assertEqual(1, sweep.payloads_deleted)
        self.assertIsNone(await TransientPayloadRepository(self.storage).get("race-input"))
        self.assertEqual("race-job", (await TurnJobRepository(self.storage).get("race-job")).job_id)
        self.assertEqual(TurnJobState.CODEX_COMPLETED, (await TurnJobRepository(self.storage).get("race-job")).state)
        race_ingress = await IngressUpdateRepository(self.storage).get(150)
        self.assertEqual("race-job", race_ingress.job_id)

        release.set()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, result.status)
        self.assertEqual(completed.job, result.job)
        self.assertIsNone(result.reason)
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)

    async def test_atomic_race_active_missing_input_is_invariant_without_effect(self):
        preflight = asyncio.Event()
        release = asyncio.Event()

        async def gate(number):
            preflight.set()
            await release.wait()

        turns = FakeTurns()
        task = asyncio.create_task(self.service(catalog=FakeCatalog(gate=gate), turns=turns).execute(
            ExistingDialoguePromptRequest(151, -1, 1, "race")
        ))
        await asyncio.wait_for(asyncio.shield(preflight.wait()), 1)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(151))
        jobs = TurnJobRepository(self.storage, now_ms=lambda: self.clock_value)
        admitted = await jobs.claim_ingress(
            update_id=151, job_id="active-race-job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="active-race-input",
            input_content=b"race", input_expires_at_ms=3_601_000,
        )
        await self.storage.write(lambda connection: (connection.execute(
            "DELETE FROM transient_payloads WHERE payload_id = 'active-race-input'"
        ), None)[1])
        release.set()
        with self.assertRaises(DialogueApplicationError) as raised:
            await asyncio.wait_for(task, 1)
        self.assertIs(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)
        self.assertEqual(admitted.job, await TurnJobRepository(self.storage).get("active-race-job"))
        self.assertEqual(admitted.ingress, await IngressUpdateRepository(self.storage).get(151))
        self.assertIsNone(await TransientPayloadRepository(self.storage).get("active-race-input"))
        self.assertEqual(1, await self._all_jobs())

    async def test_different_update_no_queue_and_winner_accounting(self):
        barrier = asyncio.Event()
        async def gate(number):
            if number == 2:
                barrier.set()
            await barrier.wait()
        turns = FakeTurns(wait_gate=asyncio.Event(), wait_event=asyncio.Event())
        service = self.service(catalog=FakeCatalog(gate=gate), turns=turns)
        one = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(130, -1, 1, "one")))
        two = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(131, -1, 2, "two")))
        await asyncio.wait_for(asyncio.shield(turns.wait_event.wait()), 1)
        turns.wait_gate.set()
        results = await asyncio.gather(one, two)
        self.assertEqual(1, len(turns.start_calls))
        winner = next(result for result in results if result.job is not None)
        loser = next(result for result in results if result.job is None)
        self.assertIn(winner.job.telegram_update_id, (130, 131))
        self.assertIn(loser.status, (ExistingDialogueTurnStatus.BUSY, ExistingDialogueTurnStatus.BLOCKED))
        ingress_ids = [record.update_id for record in [await IngressUpdateRepository(self.storage).get(130), await IngressUpdateRepository(self.storage).get(131)] if record]
        self.assertEqual([winner.job.telegram_update_id], ingress_ids)

    async def test_post_admission_cancellation_is_owned(self):
        turns = FakeTurns(wait_gate=asyncio.Event(), wait_event=asyncio.Event())
        service = self.service(turns=turns)
        task = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(140, -1, 1, "x")))
        await asyncio.wait_for(asyncio.shield(turns.wait_event.wait()), 1)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        turns.wait_gate.set()
        result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual((1, 1), (len(turns.start_calls), len(turns.wait_calls)))

    async def test_output_id_failure_and_expiry_overflow_fail_without_retry(self):
        turns = FakeTurns(messages=(AgentMessageCompleted(1, "i", "output"),))
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(turns=turns, ids=lambda kind: "bad" if kind == "job" else ("bad\x00" if kind == "output" else "input")).execute(ExistingDialoguePromptRequest(141, -1, 1, "x"))
        self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(1, len(turns.start_calls))
        await self._reset()
        turns = FakeTurns()
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(turns=turns, clock=lambda: 9223372036854775807).execute(ExistingDialoguePromptRequest(142, -1, 1, "x"))
        self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual([], turns.start_calls)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(142))

    async def test_generated_job_collision_is_invariant_without_second_job(self):
        first = await self.service().execute(ExistingDialoguePromptRequest(143, -1, 1, "x"))
        await self._reset()
        # Seed the same opaque job identifier in the fresh dialogue, then use
        # it for a different update. P2 must reject the collision atomically.
        await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
            update_id=144, job_id=first.job.job_id, source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="collision-input",
            input_content=b"seed", input_expires_at_ms=3_601_000,
        )
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(ids=lambda kind: first.job.job_id if kind == "job" else "new-input").execute(ExistingDialoguePromptRequest(145, -1, 2, "x"))
        self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(145))
        self.assertEqual(1, await self._all_jobs())

    async def test_input_payload_id_collision_is_invariant_without_retry(self):
        existing = await TransientPayloadRepository(self.storage, now_ms=lambda: 1).create(
            payload_id="collision-payload", dialogue_id="dialogue", kind=TransientPayloadKind.DISPLAY,
            content=b"existing", expires_at_ms=100,
        )
        calls = []

        def ids(kind):
            calls.append(kind)
            return "new-job" if kind == "job" else "collision-payload"

        turns = FakeTurns()
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(turns=turns, ids=ids).execute(ExistingDialoguePromptRequest(144, -1, 1, "x"))
        self.assertIs(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(["job", "input"], calls)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(144))
        self.assertEqual(0, await self._all_jobs())
        self.assertEqual(existing, await TransientPayloadRepository(self.storage).get("collision-payload"))
        self.assertEqual([], turns.start_calls)
        self.assertEqual([], turns.wait_calls)

    async def _release_wait(self, turns, other):
        turns.wait_gate.set()
        return await other

    async def _all_jobs(self):
        return await self.storage.read(lambda c: c.execute("SELECT count(*) FROM turn_jobs").fetchone()[0])

    async def _set_dialogue_state(self, state):
        thread = None if state in (DialogueState.CREATING, DialogueState.CREATE_UNKNOWN) else "thread"
        error = "CODEX_AMBIGUOUS" if state in (DialogueState.ERROR, DialogueState.TURN_UNKNOWN, DialogueState.DELETE_UNKNOWN) else None
        await self.storage.write(lambda c: (c.execute("UPDATE dialogues SET state = ?, thread_id = ?, last_error_class = ?", (state.value, thread, error)), None)[1])

    async def _reset(self):
        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.clock_value = 1_000
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: self.clock_value)
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(dialogue_id="dialogue", server_id="server", profile_id="profile")
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(dialogue_id="dialogue", expected_version=0, thread_id="thread")
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(profile_id="profile", model_id="model", reasoning_effort="high")


if __name__ == "__main__":
    unittest.main()
