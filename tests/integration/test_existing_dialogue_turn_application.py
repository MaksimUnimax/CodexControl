import asyncio
import os
import tempfile
import unittest

from codex_control.application import (
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
)
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import (
    CodexModelCatalog,
    CodexModelDescriptor,
)
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnTerminalOutcome,
)


class _Catalog:
    def __init__(self, profile="profile", effort="medium", error=None):
        self.profile = profile
        self.effort = effort
        self.error = error
        self.calls = 0

    async def get_catalog(self, profile_id, *, refresh=False):
        self.calls += 1
        if self.error:
            raise self.error
        return CodexModelCatalog(
            self.profile, 1,
            (CodexModelDescriptor("model", "wire-model", "Model", ("medium", "high"), self.effort, True, False),),
            0.0, 100.0,
        )


class _Workdir:
    def __init__(self, value=TrustedWorkingDirectory("/trusted"), error=None):
        self.value = value
        self.error = error
        self.calls = 0

    def resolve(self, profile_id):
        self.calls += 1
        if self.error:
            raise self.error
        return self.value


class _Turns:
    def __init__(self, start=TurnStartStatus.CONFIRMED, terminal=TurnTerminalStatus.COMPLETED, messages=()):
        self.start = start
        self.terminal = terminal
        self.messages = tuple(messages)
        self.start_calls = []
        self.wait_calls = []
        self.wait_gate = None
        self.start_error = None
        self.start_event = None
        self.wait_event = None

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        if self.start_event is not None:
            self.start_event.set()
        if self.start_error:
            raise self.start_error
        if self.start is TurnStartStatus.REJECTED:
            return TurnStartResult(TurnStartStatus.REJECTED)
        if self.start is TurnStartStatus.UNKNOWN:
            return TurnStartResult(TurnStartStatus.UNKNOWN)
        return TurnStartResult(TurnStartStatus.CONFIRMED, TurnBinding("profile", "thread", "turn"))

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if self.wait_event is not None:
            self.wait_event.set()
        if self.wait_gate is not None:
            await self.wait_gate.wait()
        return TurnTerminalResult(binding, self.terminal, self.messages)


class ExistingDialogueApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "state.sqlite3")
        self.clock_value = 1_000
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: self.clock_value)
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="dialogue", server_id="server", profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(
            dialogue_id="dialogue", expected_version=0, thread_id="thread"
        )
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="medium"
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def reset_fixture(self):
        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "state.sqlite3")
        self.clock_value = 1_000
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: self.clock_value)
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="dialogue", server_id="server", profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(
            dialogue_id="dialogue", expected_version=0, thread_id="thread"
        )
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="medium"
        )

    def service(self, catalog=None, turns=None, workdir=None, ids=None, clock=None):
        if ids is None:
            sequence = iter(range(1000))
            ids = lambda kind: f"{kind}-{next(sequence)}"
        return ExistingDialogueTurnService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/private", "Profile"),),
            model_catalog=catalog or _Catalog(),
            turn_lifecycle=turns or _Turns(),
            working_directory_resolver=workdir or _Workdir(),
            now_ms=clock or (lambda: self.clock_value),
            id_factory=ids,
        )

    async def test_happy_completion_preserves_order_and_snapshot(self):
        turns = _Turns(messages=(AgentMessageCompleted(1, "a", "first"), AgentMessageCompleted(2, "b", "second")))
        service = self.service(turns=turns)
        result = await service.execute(ExistingDialoguePromptRequest(1, -100, 2, "prompt"))
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual(b"first\n\nsecond", result.output_payload.content)
        self.assertEqual("model", result.job.model_id)
        self.assertEqual("medium", result.job.reasoning_effort)
        self.assertEqual(1, len(turns.start_calls))
        self.assertEqual(1, len(turns.wait_calls))
        self.assertEqual(TurnBinding("profile", "thread", "turn"), turns.wait_calls[0])
        self.assertEqual(DialogueState.IDLE, result.dialogue.state)

    async def test_default_effort_is_durably_resolved_before_admission(self):
        await SettingsRepository(self.storage).replace(
            expected_version=0, profile_id="profile", model_id="model", reasoning_effort=None
        )
        catalog = _Catalog(effort="high")
        turns = _Turns()
        result = await self.service(catalog=catalog, turns=turns).execute(
            ExistingDialoguePromptRequest(2, -100, 3, "prompt")
        )
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual("high", result.job.reasoning_effort)
        self.assertEqual("high", turns.start_calls[0]["reasoning_effort"])

    async def test_selection_failures_do_not_admit_jobs(self):
        cases = [
            (None, None, ExistingDialogueTurnReason.SETTINGS_MISSING),
            ("profile", None, ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED),
        ]
        for index, (profile, model, reason) in enumerate(cases, 10):
            if index != 10:
                await self.reset_fixture()
            if profile is None:
                # The singleton exists in the normal fixture; remove it only
                # through a fresh database would broaden this test.  Missing
                # settings is proven by using an uninitialized service DB.
                await self.storage.write(lambda connection: (connection.execute("DELETE FROM settings"), None)[1])
            else:
                await SettingsRepository(self.storage).replace(
                    expected_version=0, profile_id=profile, model_id=model, reasoning_effort=None
                )
            turns = _Turns()
            result = await self.service(turns=turns).execute(
                ExistingDialoguePromptRequest(index, -100, index, "prompt")
            )
            self.assertEqual(ExistingDialogueTurnStatus.BLOCKED, result.status)
            self.assertEqual(reason, result.reason)
            self.assertEqual([], turns.start_calls)
            if profile is None:
                await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
                    profile_id="profile", model_id="model", reasoning_effort="medium"
                )

    async def test_catalog_and_working_directory_fail_closed(self):
        catalog = _Catalog(error=RuntimeError("PRIVATE_ADAPTER_ERROR_P3_1"))
        workdir = _Workdir()
        result = await self.service(catalog=catalog, workdir=workdir).execute(
            ExistingDialoguePromptRequest(20, -100, 20, "prompt")
        )
        self.assertEqual(ExistingDialogueTurnReason.MODEL_UNAVAILABLE, result.reason)
        self.assertEqual(0, workdir.calls)
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(20))

    async def test_rejected_unknown_and_binding_mismatch_never_retry(self):
        for index, start in enumerate((TurnStartStatus.REJECTED, TurnStartStatus.UNKNOWN), 30):
            if index != 30:
                await self.reset_fixture()
            turns = _Turns(start=start)
            result = await self.service(turns=turns).execute(
                ExistingDialoguePromptRequest(index, -100, index, "prompt")
            )
            expected = ExistingDialogueTurnStatus.FAILED if start is TurnStartStatus.REJECTED else ExistingDialogueTurnStatus.UNKNOWN
            self.assertEqual(expected, result.status)
            self.assertEqual([], turns.wait_calls)
        await self.reset_fixture()
        turns = _Turns()
        turns.start = "mismatch"
        async def mismatched(**kwargs):
            turns.start_calls.append(kwargs)
            return TurnStartResult(TurnStartStatus.CONFIRMED, TurnBinding("other", "thread", "turn"))
        turns.start_turn = mismatched
        result = await self.service(turns=turns).execute(
            ExistingDialoguePromptRequest(32, -100, 32, "prompt")
        )
        self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
        self.assertEqual(1, len(turns.start_calls))
        self.assertEqual([], turns.wait_calls)

    async def test_terminal_failed_and_unknown_capture_partial_output(self):
        for index, terminal in enumerate((TurnTerminalStatus.FAILED, TurnTerminalStatus.UNKNOWN), 40):
            if index != 40:
                await self.reset_fixture()
            turns = _Turns(terminal=terminal, messages=(AgentMessageCompleted(1, "a", "partial"),))
            result = await self.service(turns=turns).execute(
                ExistingDialoguePromptRequest(index, -100, index, "prompt")
            )
            self.assertEqual(
                ExistingDialogueTurnStatus.FAILED if terminal is TurnTerminalStatus.FAILED else ExistingDialogueTurnStatus.UNKNOWN,
                result.status,
            )
            self.assertEqual(b"partial", result.output_payload.content)
            self.assertEqual(86_400_000, result.output_payload.expires_at_ms - result.output_payload.created_at_ms)

    async def test_duplicate_job_skips_catalog_workdir_clock_ids_and_turn(self):
        await TurnJobRepository(self.storage, now_ms=lambda: 20).claim_ingress(
            update_id=50, job_id="job-50", source_chat_id=-100, source_message_id=50,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="medium", input_payload_id="input-50",
            input_content=b"original", input_expires_at_ms=100_000,
        )
        catalog = _Catalog()
        workdir = _Workdir()
        turns = _Turns()
        service = self.service(
            catalog=catalog, workdir=workdir, turns=turns,
            clock=lambda: (_ for _ in ()).throw(AssertionError("clock")),
            ids=lambda kind: (_ for _ in ()).throw(AssertionError("id")),
        )
        result = await service.execute(ExistingDialoguePromptRequest(50, -100, 999, "changed"))
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, result.status)
        self.assertEqual("job-50", result.job.job_id)
        self.assertEqual(0, catalog.calls)
        self.assertEqual(0, workdir.calls)
        self.assertEqual([], turns.start_calls)

    async def test_different_updates_have_no_queue(self):
        turns = _Turns()
        service = self.service(turns=turns)
        results = await asyncio.gather(
            service.execute(ExistingDialoguePromptRequest(60, -100, 60, "one")),
            service.execute(ExistingDialoguePromptRequest(61, -100, 61, "two")),
        )
        self.assertEqual(1, sum(result.status in (ExistingDialogueTurnStatus.COMPLETED, ExistingDialogueTurnStatus.FAILED, ExistingDialogueTurnStatus.UNKNOWN) for result in results))
        self.assertEqual(1, sum(result.status is ExistingDialogueTurnStatus.BUSY for result in results))
        self.assertEqual(1, len(turns.start_calls))
        self.assertIsNone(await IngressUpdateRepository(self.storage).get(61))

    async def test_post_admission_cancellation_keeps_owned_execution(self):
        gate = asyncio.Event()
        turns = _Turns()
        turns.wait_gate = gate
        turns.start_event = asyncio.Event()
        turns.wait_event = asyncio.Event()
        service = self.service(turns=turns)
        task = asyncio.create_task(service.execute(ExistingDialoguePromptRequest(70, -100, 70, "prompt")))
        # The event is set only after the durable CODEX_STARTING boundary has
        # been reached and the single P1 start call has begun.
        await turns.start_event.wait()
        await turns.wait_event.wait()
        self.assertEqual(1, len(turns.wait_calls))
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        gate.set()
        result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual(1, len(turns.start_calls))
        self.assertEqual(1, len(turns.wait_calls))
