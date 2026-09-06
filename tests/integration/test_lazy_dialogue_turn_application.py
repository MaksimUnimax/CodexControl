import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.application import (
    CreationRecoveryStatus,
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    DialogueTurnService,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    SettingsRepository,
    SqliteStorage,
    RepositoryError,
    RepositoryErrorCategory,
    TurnJobRepository,
    TurnJobState,
    TransientPayloadRepository,
)


class Catalog:
    def __init__(self, profile="profile", hidden=False, effort="high", supported=("low", "high"), error=None):
        self.profile = profile
        self.hidden = hidden
        self.effort = effort
        self.supported = supported
        self.error = error
        self.calls = 0

    async def get_catalog(self, profile_id, *, refresh=False):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return CodexModelCatalog(
            self.profile, 1,
            (CodexModelDescriptor("model", "wire-model", "Model", self.supported, self.effort, True, self.hidden),),
            0.0, 100.0,
        )


class Workdir:
    def __init__(self, value=TrustedWorkingDirectory("/trusted"), error=None):
        self.value, self.error, self.calls = value, error, 0

    def resolve(self, profile_id):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.value


class Thread:
    def __init__(self, storage, result=None, gate=None, inspect_durable=False, error=None):
        self.storage = storage
        self.result = result or ThreadOperationResult(
            ThreadOperationStatus.START_CONFIRMED,
            ThreadBinding("profile", "thread-new"),
            model_id="model", reasoning_effort="high",
        )
        self.gate, self.inspect_durable, self.error = gate, inspect_durable, error
        self.calls = []

    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        self.calls.append((profile_id, model_id, reasoning_effort, working_directory))
        if self.inspect_durable:
            dialogue = await DialogueRepository(self.storage).get_live()
            ingress = await IngressUpdateRepository(self.storage).get(1)
            job = await TurnJobRepository(self.storage).get(ingress.job_id)
            payload = await TransientPayloadRepository(self.storage).get_input_for_job(job.job_id)
            assert dialogue.state is DialogueState.CREATING
            assert dialogue.thread_id is None
            assert job.state is TurnJobState.RECEIVED
            assert job.thread_id is None
            assert job.profile_id == profile_id
            assert job.model_id == model_id
            assert job.reasoning_effort == reasoning_effort
            assert payload.content == b"first"
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        return self.result


class Turns:
    def __init__(self, terminal=TurnTerminalStatus.COMPLETED, messages=(), wait_gate=None):
        self.terminal, self.messages, self.wait_gate = terminal, tuple(messages), wait_gate
        self.start_calls, self.wait_calls = [], []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        binding = TurnBinding(kwargs["thread_binding"].profile_id, kwargs["thread_binding"].thread_id, "turn-1")
        return TurnStartResult(TurnStartStatus.CONFIRMED, binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if self.wait_gate is not None:
            await self.wait_gate.wait()
        return TurnTerminalResult(binding, self.terminal, self.messages)


class LazyDialogueTurnIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: 1000)
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, *, catalog=None, thread=None, turns=None, workdir=None, ids=None, clock=None):
        return DialogueTurnService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/private/CODEX_HOME", "Profile"),),
            model_catalog=catalog or Catalog(),
            thread_lifecycle=thread or Thread(self.storage),
            turn_lifecycle=turns or Turns(),
            working_directory_resolver=workdir or Workdir(),
            now_ms=clock or (lambda: 1000),
            id_factory=ids or (lambda kind: f"{kind}-1"),
        )

    async def test_happy_path_durable_order_and_single_job(self):
        thread = Thread(self.storage, inspect_durable=True)
        turns = Turns(messages=(AgentMessageCompleted(1, "a", "one"), AgentMessageCompleted(2, "b", "two")))
        result = await self.service(thread=thread, turns=turns).execute(
            ExistingDialoguePromptRequest(1, -100, 2, "first")
        )
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual((1, 1), (len(thread.calls), len(turns.start_calls)))
        self.assertEqual(1, len(turns.wait_calls))
        self.assertEqual(b"one\n\ntwo", result.output_payload.content)
        self.assertEqual((DialogueState.IDLE, "thread-new"), ((await DialogueRepository(self.storage).get_live()).state, (await DialogueRepository(self.storage).get_live()).thread_id))
        self.assertEqual(TurnJobState.CODEX_COMPLETED, (await TurnJobRepository(self.storage).get(result.job.job_id)).state)
        self.assertEqual("thread-new", (await TurnJobRepository(self.storage).get(result.job.job_id)).thread_id)

    async def test_existing_dialogue_is_delegated_without_thread_start(self):
        await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(dialogue_id="existing", server_id="server", profile_id="profile")
        await DialogueRepository(self.storage, now_ms=lambda: 10).confirm_created(dialogue_id="existing", expected_version=0, thread_id="old-thread")
        thread = Thread(self.storage)
        turns = Turns()
        result = await self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(2, -1, 2, "old"))
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual([], thread.calls)
        self.assertEqual(1, len(turns.start_calls))

    async def test_preflight_matrix_has_no_local_state_or_external_effect(self):
        cases = (
            (None, ExistingDialogueTurnReason.SETTINGS_MISSING, None),
            ("null-profile", ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED, None),
            ("absent-profile", ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED, None),
            ("model-null", ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED, None),
            ("hidden", ExistingDialogueTurnReason.MODEL_UNAVAILABLE, Catalog(hidden=True)),
            ("bad-effort", ExistingDialogueTurnReason.MODEL_UNAVAILABLE, Catalog(supported=("low",), effort="low")),
        )
        for index, (kind, expected, catalog) in enumerate(cases, 10):
            await self.storage.write(lambda c: (c.execute("DELETE FROM settings"), c.execute("DELETE FROM dialogues"), None)[2])
            if kind is not None:
                profile = None if kind == "null-profile" else ("other" if kind == "absent-profile" else "profile")
                model = None if kind == "model-null" else "model"
                await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(profile_id=profile, model_id=model, reasoning_effort="high")
            thread, turns = Thread(self.storage), Turns()
            result = await self.service(catalog=catalog, thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(expected, result.reason)
            self.assertIsNone(await DialogueRepository(self.storage).get_live())
            self.assertEqual([], thread.calls)
            self.assertEqual([], turns.start_calls)
            self.assertIsNone(await IngressUpdateRepository(self.storage).get(index))
            await self.storage.write(lambda c: (c.execute("DELETE FROM settings"), None)[1])
        await SettingsRepository(self.storage, now_ms=lambda: 10).initialize_if_absent(profile_id="profile", model_id="model", reasoning_effort="high")

    async def test_thread_failure_mapping_is_fail_closed_without_turn(self):
        for index, error, expected in (
            (20, ThreadLifecycleError("thread_request_invalid"), ExistingDialogueTurnStatus.FAILED),
            (21, ThreadLifecycleError("thread_precondition_changed"), ExistingDialogueTurnStatus.FAILED),
            (22, ThreadLifecycleError("thread_operation_busy"), ExistingDialogueTurnStatus.FAILED),
            (23, ThreadLifecycleError("thread_start_unknown"), ExistingDialogueTurnStatus.UNKNOWN),
            (24, RuntimeError("PRIVATE_THREAD_ERROR_P3_2"), ExistingDialogueTurnStatus.UNKNOWN),
        ):
            thread = Thread(self.storage, error=error)
            turns = Turns()
            result = await self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(index, -1, index, "x"))
            self.assertEqual(expected, result.status)
            self.assertEqual([], turns.start_calls)
            self.assertEqual("CODEX_PROCESS" if expected is ExistingDialogueTurnStatus.FAILED else "CODEX_AMBIGUOUS", result.dialogue.last_error_class)
            await self.storage.write(lambda c: (c.execute("DELETE FROM turn_jobs"), c.execute("DELETE FROM ingress_updates"), c.execute("DELETE FROM transient_payloads"), c.execute("DELETE FROM dialogues"), None)[4])

    async def test_recovery_marks_only_preexisting_creating_and_is_idempotent(self):
        dialogue = await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(dialogue_id="recover", server_id="server", profile_id="profile")
        thread = Thread(self.storage)
        turns = Turns()
        service = self.service(thread=thread, turns=turns)
        first = await service.recover_preexisting_creation()
        second = await service.recover_preexisting_creation()
        self.assertEqual(CreationRecoveryStatus.MARKED_UNKNOWN, first.status)
        self.assertEqual(CreationRecoveryStatus.NO_ACTION, second.status)
        self.assertEqual(first.dialogue, second.dialogue)
        self.assertEqual(0, len(thread.calls))
        self.assertEqual(0, len(turns.start_calls))

    async def test_recovery_preserves_received_job_ingress_and_input(self):
        creating = await DialogueRepository(self.storage, now_ms=lambda: 10).create_intent(
            dialogue_id="recover-job", server_id="server", profile_id="profile"
        )
        admitted = await TurnJobRepository(self.storage, now_ms=lambda: 20).claim_ingress(
            update_id=32, job_id="recover-job-job", source_chat_id=-1, source_message_id=1,
            dialogue_id=creating.dialogue_id, server_id="server", profile_id="profile", thread_id=None,
            model_id="model", reasoning_effort="high", input_payload_id="recover-job-input",
            input_content=b"evidence", input_expires_at_ms=10000,
        )
        result = await self.service().recover_preexisting_creation()
        self.assertEqual(CreationRecoveryStatus.MARKED_UNKNOWN, result.status)
        self.assertEqual(admitted.job, await TurnJobRepository(self.storage).get(admitted.job.job_id))
        self.assertEqual(admitted.input_payload, await TransientPayloadRepository(self.storage).get(admitted.input_payload.payload_id))
        ingress = await IngressUpdateRepository(self.storage).get(32)
        self.assertEqual("JOB", ingress.disposition.value)
        self.assertEqual("recover-job-job", ingress.job_id)

    async def test_same_and_different_update_races_have_one_winner_and_no_queue(self):
        for first_update, second_update in ((60, 60), (61, 62)):
            await self.storage.write(lambda c: (c.execute("DELETE FROM turn_jobs"), c.execute("DELETE FROM ingress_updates"), c.execute("DELETE FROM transient_payloads"), c.execute("DELETE FROM dialogues"), None)[4])
            gate = asyncio.Event()
            first_thread = Thread(self.storage, gate=gate)
            second_thread = Thread(self.storage, gate=gate)
            first_service = self.service(thread=first_thread, turns=Turns(), ids=lambda kind: f"first-{kind}")
            second_service = self.service(thread=second_thread, turns=Turns(), ids=lambda kind: f"second-{kind}")
            first = asyncio.create_task(first_service.execute(ExistingDialoguePromptRequest(first_update, -1, 1, "first")))
            second = asyncio.create_task(second_service.execute(ExistingDialoguePromptRequest(second_update, -1, 2, "second")))
            while not (first_thread.calls or second_thread.calls):
                await asyncio.sleep(0)
            gate.set()
            results = await asyncio.gather(first, second)
            self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0]))
            self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
            self.assertEqual(1, len(first_thread.calls) + len(second_thread.calls))
            if first_update == second_update:
                self.assertEqual(1, sum(result.status is ExistingDialogueTurnStatus.DUPLICATE for result in results))
            else:
                self.assertEqual(1, sum(result.job is not None for result in results))
                self.assertIn(next(result for result in results if result.job is None).status, (ExistingDialogueTurnStatus.BLOCKED, ExistingDialogueTurnStatus.BUSY))

    async def test_admission_id_collision_terminalizes_owned_creation_without_retry(self):
        for collision_kind in ("job", "input"):
            await self.storage.write(lambda c: (c.execute("DELETE FROM turn_jobs"), c.execute("DELETE FROM ingress_updates"), c.execute("DELETE FROM transient_payloads"), c.execute("DELETE FROM dialogues"), None)[4])

            async def collision(repo, **kwargs):
                raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)

            ids = lambda kind, collision_kind=collision_kind: "collision" if kind == collision_kind else f"fresh-{kind}"
            with patch.object(TurnJobRepository, "claim_ingress", collision):
                with self.assertRaises(DialogueApplicationError) as raised:
                    await self.service(ids=ids).execute(ExistingDialoguePromptRequest(70 if collision_kind == "job" else 71, -1, 1, "x"))
            self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
            dialogue = await DialogueRepository(self.storage).get_live()
            self.assertEqual((DialogueState.ERROR, "APPLICATION_ADMISSION_FAILED"), (dialogue.state, dialogue.last_error_class))
            self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
            self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]))

    async def test_confirm_failure_reconciles_committed_local_confirmation(self):
        thread = Thread(self.storage)
        turns = Turns()
        original = DialogueRepository.confirm_created

        async def committed_then_lost(repo, **kwargs):
            value = await original(repo, **kwargs)
            raise RuntimeError("caller lost result")

        with patch.object(DialogueRepository, "confirm_created", committed_then_lost):
            result = await self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(30, -1, 1, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual((1, 1), (len(thread.calls), len(turns.start_calls)))

    async def test_confirm_failure_remaining_creating_becomes_unknown_without_turn(self):
        thread = Thread(self.storage)
        turns = Turns()

        async def failed_confirm(repo, **kwargs):
            raise RuntimeError("no commit")

        with patch.object(DialogueRepository, "confirm_created", failed_confirm):
            result = await self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(31, -1, 1, "x"))
        self.assertEqual(ExistingDialogueTurnStatus.UNKNOWN, result.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, result.dialogue.state)
        self.assertEqual([], turns.start_calls)

    async def test_tombstone_collision_has_no_creation_or_effect(self):
        await self.storage.write(lambda c: (c.execute("INSERT INTO deletion_tombstones VALUES ('dialogue-1', ?, 1, 1, 10000)", ("a" * 64,)), None)[1])
        thread, turns = Thread(self.storage), Turns()
        with self.assertRaises(DialogueApplicationError) as raised:
            await self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(40, -1, 1, "x"))
        self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, raised.exception.category)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        self.assertEqual([], thread.calls)
        self.assertEqual([], turns.start_calls)

    async def test_post_admission_cancellation_remains_owned(self):
        thread_gate = asyncio.Event()
        wait_gate = asyncio.Event()
        thread = Thread(self.storage, gate=thread_gate)
        turns = Turns(wait_gate=wait_gate)
        task = asyncio.create_task(self.service(thread=thread, turns=turns).execute(ExistingDialoguePromptRequest(50, -1, 1, "x")))
        while not thread.calls:
            await asyncio.sleep(0)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        thread_gate.set()
        while not turns.wait_calls:
            await asyncio.sleep(0)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        wait_gate.set()
        result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertEqual((1, 1), (len(thread.calls), len(turns.start_calls)))


if __name__ == "__main__":
    unittest.main()
