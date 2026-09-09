import asyncio
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.approvals import ApprovalKind
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueInterruptError,
    DialogueInterruptReason,
    DialogueInterruptRequest,
    DialogueInterruptService,
    DialogueInterruptStatus,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
    P3_COMPLETED_OUTPUT_RETENTION_MS,
    P3_UNCERTAIN_OUTPUT_RETENTION_MS,
    SettingsMutationReason,
    SettingsMutationStatus,
    SettingsSelectionService,
    InterruptRecoveryStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    ApprovalRepository,
    ApprovalState,
    ApprovalCallbackClaimStatus,
    CallbackActionRepository,
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SCHEMA_V1_DDL_SHA256,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)
from codex_control.storage.core_repositories import MAX_SQLITE_INT
from codex_control.storage.interrupt_coordination import InterruptCoordinationRepository


class FakeInterruptLifecycle:
    def __init__(self, *, interrupt_status=TurnInterruptStatus.CONFIRMED,
                 terminal_status=TurnTerminalStatus.COMPLETED, messages=(), interrupt_error=None,
                 wait_result=None, interrupt_gate=None, interrupt_terminal_binding=None,
                 wait_terminal_binding=None):
        self.binding = None
        self.interrupt_status = interrupt_status
        self.terminal_status = terminal_status
        self.messages = tuple(messages)
        self.interrupt_error = interrupt_error
        self.wait_result = wait_result
        self.interrupt_gate = interrupt_gate
        self.interrupt_terminal_binding = interrupt_terminal_binding
        self.wait_terminal_binding = wait_terminal_binding
        self.interrupt_calls = []
        self.wait_calls = []

    def _terminal(self, binding, terminal_binding=None):
        return TurnTerminalResult(terminal_binding or binding, self.terminal_status, self.messages)

    async def interrupt_turn(self, binding):
        self.interrupt_calls.append(binding)
        if self.interrupt_gate is not None:
            await self.interrupt_gate.wait()
        if self.interrupt_error is not None:
            raise self.interrupt_error
        result = TurnInterruptResult(self.interrupt_status, binding)
        if self.interrupt_status in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED):
            result = TurnInterruptResult(
                self.interrupt_status, binding,
                self._terminal(binding, self.interrupt_terminal_binding),
            )
        return result

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if self.wait_result is not None:
            return self.wait_result
        return self._terminal(binding, self.wait_terminal_binding)


class _CountingClock:
    def __init__(self, value=1000):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


class _SettingsCatalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (
                CodexModelDescriptor("model-a", "wire-a", "Model A", ("low", "high"), "high", True, False),
                CodexModelDescriptor("model-b", "wire-b", "Model B", ("low",), "low", False, False),
            ),
            0.0, 100.0,
        )


class _RunnerWorkdir:
    def resolve(self, profile_id):
        from codex_control.adapters.codex.thread_lifecycle import TrustedWorkingDirectory
        return TrustedWorkingDirectory("/trusted")


class _RunnerLifecycle:
    def __init__(self, binding, *, race=False):
        self.binding = binding
        self.race = race
        self.start_calls = []
        self.interrupt_calls = []
        self.wait_calls = []
        self.runner_wait_entered = asyncio.Event()
        self.interrupt_called = asyncio.Event()
        self.terminal_available = asyncio.Event()
        self.fallback_done = asyncio.Event()

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        return TurnStartResult(TurnStartStatus.CONFIRMED, self.binding)

    async def interrupt_turn(self, binding):
        self.interrupt_calls.append(binding)
        self.interrupt_called.set()
        return TurnInterruptResult(TurnInterruptStatus.UNKNOWN, binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if len(self.wait_calls) == 1:
            self.runner_wait_entered.set()
            await self.terminal_available.wait()
        else:
            await self.fallback_done.wait()
        return TurnTerminalResult(
            binding, TurnTerminalStatus.COMPLETED,
            (AgentMessageCompleted(1, "item", "race-output"),),
        )


class DialogueInterruptApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: 1000
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def seed_running(self, *, registry=True, job_id="job", update_id=1):
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 1)
        await dialogues.create_intent(dialogue_id="dialogue", server_id="server", profile_id="profile")
        await dialogues.confirm_created(dialogue_id="dialogue", expected_version=0, thread_id="thread")
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(
            update_id=update_id, job_id=job_id, source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id=f"input-{job_id}",
            input_content=b"input", input_expires_at_ms=10_000,
        )
        current = await dialogues.get_live()
        claimed = await jobs.claim_turn(
            job_id=job_id, expected_job_version=admitted.job.version,
            expected_dialogue_version=current.version, thread_id="thread",
        )
        starting = await jobs.mark_codex_starting(job_id=job_id, expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(
            job_id=job_id, expected_version=starting.version, codex_turn_id=f"turn-{job_id}"
        )
        binding = TurnBinding("profile", "thread", f"turn-{job_id}")
        registry_obj = ActiveTurnRegistry()
        if registry:
            registry_obj.publish(job_id, binding)
        return claimed, running, binding, registry_obj

    def service(self, registry, lifecycle, *, ids=None):
        return DialogueInterruptService(
            self.storage, server_id="server", active_turn_registry=registry,
            turn_lifecycle=lifecycle, now_ms=lambda: 1000,
            id_factory=ids or (lambda kind: f"{kind}-interrupt"),
        )

    async def seed_idle_application(self):
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 1)
        await dialogues.create_intent(dialogue_id="dialogue", server_id="server", profile_id="profile")
        await dialogues.confirm_created(dialogue_id="dialogue", expected_version=0, thread_id="thread")
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model-a", reasoning_effort="high"
        )

    async def reset_storage(self):
        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: 1000
        )

    async def test_no_dialogue_and_nonrunning_are_blocked(self):
        registry = ActiveTurnRegistry()
        life = FakeInterruptLifecycle()
        service = self.service(registry, life)
        no_dialogue = await service.interrupt(DialogueInterruptRequest("d", "j", 0, 0))
        self.assertEqual((DialogueInterruptStatus.BLOCKED, DialogueInterruptReason.NO_DIALOGUE), (no_dialogue.status, no_dialogue.reason))
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 1)
        await dialogues.create_intent(dialogue_id="d", server_id="server", profile_id="profile")
        idle = await service.interrupt(DialogueInterruptRequest("d", "j", 0, 0))
        self.assertEqual((DialogueInterruptStatus.BLOCKED, DialogueInterruptReason.DIALOGUE_NOT_RUNNING), (idle.status, idle.reason))
        self.assertEqual([], life.interrupt_calls)

    async def test_stale_dialogue_and_job_requests_do_not_interrupt(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle()
        service = self.service(registry, life)
        stale_dialogue = await service.interrupt(DialogueInterruptRequest("other", "job", claimed.dialogue.version, running.version))
        self.assertEqual((DialogueInterruptStatus.CONFLICT, DialogueInterruptReason.STALE_REQUEST), (stale_dialogue.status, stale_dialogue.reason))
        stale_job = await service.interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version - 1))
        self.assertEqual((DialogueInterruptStatus.CONFLICT, DialogueInterruptReason.STALE_REQUEST), (stale_job.status, stale_job.reason))
        self.assertEqual([], life.interrupt_calls)

    async def test_registry_absent_and_mismatch_fail_closed(self):
        claimed, running, binding, registry = await self.seed_running(registry=False)
        life = FakeInterruptLifecycle()
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual((DialogueInterruptStatus.BLOCKED, DialogueInterruptReason.ACTIVE_BINDING_UNAVAILABLE), (result.status, result.reason))
        self.assertEqual([], life.interrupt_calls)
        await self.reset_storage()
        claimed, running, binding, registry = await self.seed_running(job_id="job2", update_id=2)
        registry.retire("job2", binding)
        registry.publish("job2", TurnBinding("profile", "thread", "wrong"))
        with self.assertRaises(DialogueInterruptError):
            await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job2", claimed.dialogue.version, running.version))
        self.assertEqual([], life.interrupt_calls)

    async def test_claim_is_durable_before_p1_and_confirmed_completed(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle()
        original = life.interrupt_turn
        async def checked(value):
            dialogue = await DialogueRepository(self.storage).get_live()
            job = await TurnJobRepository(self.storage).get("job")
            self.assertEqual(DialogueState.INTERRUPTING, dialogue.state)
            self.assertEqual(TurnJobState.CODEX_RUNNING, job.state)
            self.assertIs(value, binding)
            return await original(value)
        life.interrupt_turn = checked
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.CONFIRMED, result.status)
        self.assertEqual(TurnJobState.CODEX_COMPLETED, result.job.state)
        self.assertEqual(DialogueState.IDLE, result.dialogue.state)
        self.assertEqual(1, len(life.interrupt_calls))

    async def test_confirmed_failed_maps_to_idle_with_failed_job(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(terminal_status=TurnTerminalStatus.FAILED)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.CONFIRMED, result.status)
        self.assertEqual(TurnJobState.FAILED, result.job.state)
        self.assertEqual("CODEX_TURN_FAILED", result.job.error_class)
        self.assertEqual(DialogueState.IDLE, result.dialogue.state)
        self.assertIsNone(result.dialogue.last_error_class)

    async def test_reconciled_and_rejected_restore(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(interrupt_status=TurnInterruptStatus.RECONCILED)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.RECONCILED, result.status)
        await self.reset_storage()
        claimed, running, binding, registry = await self.seed_running(job_id="job2", update_id=2)
        life = FakeInterruptLifecycle(interrupt_status=TurnInterruptStatus.REJECTED)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job2", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.REJECTED, result.status)
        self.assertEqual(DialogueState.TURN_RUNNING, result.dialogue.state)
        self.assertEqual(TurnJobState.CODEX_RUNNING, result.job.state)
        self.assertEqual(1, len(life.interrupt_calls))

    async def test_unknown_definitive_and_unknown_unprovable(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(interrupt_error=RuntimeError("PRIVATE_RAW"), terminal_status=TurnTerminalStatus.COMPLETED)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.RECONCILED, result.status)
        self.assertEqual(1, len(life.wait_calls))
        await self.reset_storage()
        claimed, running, binding, registry = await self.seed_running(job_id="job2", update_id=2)
        life = FakeInterruptLifecycle(interrupt_error=RuntimeError("PRIVATE_RAW"), terminal_status=TurnTerminalStatus.UNKNOWN)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job2", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.UNKNOWN, result.status)
        self.assertEqual(TurnJobState.UNKNOWN, result.job.state)
        self.assertEqual(DialogueState.TURN_UNKNOWN, result.dialogue.state)
        self.assertNotIn("PRIVATE_RAW", repr(result))

    async def test_not_active_busy_and_malformed_use_one_collector_no_retry(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(interrupt_error=TurnLifecycleError("turn_interrupt_busy"), terminal_status=TurnTerminalStatus.UNKNOWN)
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.UNKNOWN, result.status)
        self.assertEqual((1, 1), (len(life.interrupt_calls), len(life.wait_calls)))

    async def test_equal_but_cloned_direct_terminal_is_not_confirmed(self):
        claimed, running, binding, registry = await self.seed_running()
        clone = TurnBinding(binding.profile_id, binding.thread_id, binding.turn_id)
        self.assertEqual(clone, binding)
        self.assertIsNot(clone, binding)
        life = FakeInterruptLifecycle(
            interrupt_terminal_binding=clone,
            wait_terminal_binding=clone,
        )
        result = await self.service(registry, life).interrupt(
            DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        )
        self.assertEqual(DialogueInterruptStatus.UNKNOWN, result.status)
        self.assertEqual(TurnJobState.UNKNOWN, result.job.state)
        self.assertEqual(DialogueState.TURN_UNKNOWN, result.dialogue.state)
        self.assertEqual((1, 1), (len(life.interrupt_calls), len(life.wait_calls)))

    async def test_equal_but_cloned_collector_terminal_is_not_definitive(self):
        claimed, running, binding, registry = await self.seed_running()
        clone = TurnBinding(binding.profile_id, binding.thread_id, binding.turn_id)
        life = FakeInterruptLifecycle(
            interrupt_error=RuntimeError("PRIVATE_CLONED_COLLECTOR_ERROR"),
            wait_terminal_binding=clone,
        )
        result = await self.service(registry, life).interrupt(
            DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        )
        self.assertEqual(DialogueInterruptStatus.UNKNOWN, result.status)
        self.assertEqual(TurnJobState.UNKNOWN, result.job.state)
        self.assertEqual(DialogueState.TURN_UNKNOWN, result.dialogue.state)
        self.assertEqual((1, 1), (len(life.interrupt_calls), len(life.wait_calls)))

    async def test_not_active_exact_terminal_reconciles_once_without_retry(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(
            interrupt_error=TurnLifecycleError(CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE),
            terminal_status=TurnTerminalStatus.COMPLETED,
        )
        result = await self.service(registry, life).interrupt(
            DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        )
        self.assertEqual(DialogueInterruptStatus.RECONCILED, result.status)
        self.assertEqual((1, 1), (len(life.interrupt_calls), len(life.wait_calls)))

    async def test_local_request_and_precondition_errors_fail_closed_without_collector(self):
        for category in (
            CodexAdapterErrorCategory.TURN_REQUEST_INVALID,
            CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED,
        ):
            if category is not CodexAdapterErrorCategory.TURN_REQUEST_INVALID:
                await self.reset_storage()
            claimed, running, binding, registry = await self.seed_running(
                job_id=f"job-{category.value}", update_id=10 + len(category.value)
            )
            life = FakeInterruptLifecycle(interrupt_error=TurnLifecycleError(category))
            service = self.service(registry, life)
            with self.assertRaises(DialogueInterruptError) as raised:
                await service.interrupt(DialogueInterruptRequest(
                    "dialogue", claimed.job.job_id, claimed.dialogue.version, running.version
                ))
            self.assertEqual("INVARIANT", str(raised.exception))
            self.assertNotIn(category.value, str(raised.exception) + repr(raised.exception))
            current_dialogue = await DialogueRepository(self.storage).get_live()
            current_job = await TurnJobRepository(self.storage).get(claimed.job.job_id)
            self.assertEqual(DialogueState.INTERRUPTING, current_dialogue.state)
            self.assertEqual(TurnJobState.CODEX_RUNNING, current_job.state)
            self.assertEqual(0, len(life.wait_calls))
            self.assertEqual(0, await self.storage.read(
                lambda connection: connection.execute(
                    "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT'"
                ).fetchone()[0]
            ))

    async def test_output_clock_failure_is_storage_redacted_and_leaves_claim_running(self):
        claimed, running, binding, registry = await self.seed_running()

        class _SequenceClock:
            def __init__(self):
                self.calls = 0

            def __call__(self):
                self.calls += 1
                if self.calls == 1:
                    return 1000
                raise RuntimeError("PRIVATE_P3_4_OUTPUT_CLOCK_MUST_NOT_LEAK")

        clock = _SequenceClock()
        life = FakeInterruptLifecycle(messages=(AgentMessageCompleted(1, "item", "partial"),))
        with self.assertRaises(DialogueInterruptError) as raised:
            await DialogueInterruptService(
                self.storage, server_id="server", active_turn_registry=registry,
                turn_lifecycle=life, now_ms=clock, id_factory=lambda kind: f"{kind}-clock",
            ).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
        self.assertEqual("STORAGE", str(raised.exception))
        self.assertNotIn("PRIVATE_P3_4_OUTPUT_CLOCK_MUST_NOT_LEAK", str(raised.exception) + repr(raised.exception))
        self.assertEqual(2, clock.calls)
        self.assertEqual((DialogueState.INTERRUPTING, TurnJobState.CODEX_RUNNING), (
            (await DialogueRepository(self.storage).get_live()).state,
            (await TurnJobRepository(self.storage).get("job")).state,
        ))
        self.assertEqual(1, len(life.interrupt_calls))
        self.assertEqual(0, await self.storage.read(
            lambda connection: connection.execute(
                "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT'"
            ).fetchone()[0]
        ))
        await self.reset_storage()
        claimed, running, binding, registry = await self.seed_running(job_id="job2", update_id=2)
        life = FakeInterruptLifecycle()
        async def malformed(value):
            life.interrupt_calls.append(value)
            return object()
        life.interrupt_turn = malformed
        life.wait_result = TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())
        result = await self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job2", claimed.dialogue.version, running.version))
        self.assertEqual(DialogueInterruptStatus.RECONCILED, result.status)
        self.assertEqual((1, 1), (len(life.interrupt_calls), len(life.wait_calls)))

    async def test_post_claim_cancellation_is_owned_and_single_rpc(self):
        claimed, running, binding, registry = await self.seed_running()
        gate = asyncio.Event()
        life = FakeInterruptLifecycle(interrupt_gate=gate)
        task = asyncio.create_task(self.service(registry, life).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)))
        while (await DialogueRepository(self.storage).get_live()).state is not DialogueState.INTERRUPTING:
            await asyncio.sleep(0)
        for _ in range(3):
            task.cancel()
            await asyncio.sleep(0)
        gate.set()
        result = await task
        self.assertEqual(DialogueInterruptStatus.CONFIRMED, result.status)
        self.assertEqual(1, len(life.interrupt_calls))

    async def test_concurrent_interrupts_have_one_winner_and_one_rpc(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle(interrupt_gate=asyncio.Event())
        request = DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        first = asyncio.create_task(self.service(registry, life).interrupt(request))
        second = asyncio.create_task(self.service(registry, life).interrupt(request))
        while (await DialogueRepository(self.storage).get_live()).state is not DialogueState.INTERRUPTING:
            await asyncio.sleep(0)
        life.interrupt_gate.set()
        results = await asyncio.gather(first, second)
        self.assertEqual(1, len(life.interrupt_calls))
        self.assertEqual(1, sum(r.status is DialogueInterruptStatus.CONFIRMED for r in results))
        self.assertIn(
            next(r.status for r in results if r.status is not DialogueInterruptStatus.CONFIRMED),
            {DialogueInterruptStatus.BLOCKED, DialogueInterruptStatus.CONFLICT},
        )

    async def test_stale_request_cannot_interrupt_next_turn(self):
        claimed, running, binding, registry = await self.seed_running()
        life = FakeInterruptLifecycle()
        service = self.service(registry, life)
        old_request = DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        completed = await service.interrupt(old_request)
        self.assertEqual(DialogueInterruptStatus.CONFIRMED, completed.status)
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 1)
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(update_id=2, job_id="job-b", source_chat_id=-1, source_message_id=2,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input-b", input_content=b"b", input_expires_at_ms=10_000)
        current = await dialogues.get_live()
        new_claim = await jobs.claim_turn(job_id="job-b", expected_job_version=admitted.job.version,
            expected_dialogue_version=current.version, thread_id="thread")
        start = await jobs.mark_codex_starting(job_id="job-b", expected_version=new_claim.job.version)
        new_running = await jobs.mark_codex_running(job_id="job-b", expected_version=start.version, codex_turn_id="turn-b")
        result = await service.interrupt(old_request)
        self.assertEqual((DialogueInterruptStatus.CONFLICT, DialogueInterruptReason.STALE_REQUEST), (result.status, result.reason))
        self.assertEqual(1, len(life.interrupt_calls))
        self.assertEqual(TurnJobState.CODEX_RUNNING, new_running.state)

    async def test_natural_terminal_before_claim_has_zero_interrupt_rpc(self):
        claimed, running, binding, registry = await self.seed_running()
        natural = await TurnJobRepository(self.storage, now_ms=lambda: 1).finish_codex(
            job_id="job", expected_job_version=running.version,
            expected_dialogue_version=claimed.dialogue.version,
            outcome=TurnTerminalOutcome.COMPLETED,
        )
        life = FakeInterruptLifecycle()
        result = await self.service(registry, life).interrupt(
            DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        )
        self.assertIn((result.status, result.reason), {
            (DialogueInterruptStatus.BLOCKED, DialogueInterruptReason.JOB_NOT_RUNNING),
            (DialogueInterruptStatus.CONFLICT, DialogueInterruptReason.STALE_REQUEST),
        })
        self.assertEqual(TurnJobState.CODEX_COMPLETED, natural.job.state)
        self.assertEqual([], life.interrupt_calls)

    async def test_claim_wins_natural_terminal_reconciliation_and_duplicate_write(self):
        claimed, running, binding, registry = await self.seed_running()
        coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
        interrupted = await coordinator.claim_interrupt(
            dialogue_id="dialogue", job_id="job",
            expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        first = await coordinator.reconcile_natural_terminal(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", base_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.COMPLETED,
            error_class=None,
        )
        second = await coordinator.terminalize_interrupt(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", claimed_dialogue_version=interrupted.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.COMPLETED,
            error_class=None,
        )
        self.assertEqual(TurnJobState.CODEX_COMPLETED, first.job.state)
        self.assertEqual(first.job, second.job)
        self.assertEqual(first.dialogue, second.dialogue)
        self.assertEqual(1, await self.storage.read(
            lambda connection: connection.execute("SELECT COUNT(*) FROM turn_jobs WHERE state = 'CODEX_COMPLETED'").fetchone()[0]
        ))

    async def test_rejected_restore_then_natural_terminal_uses_restored_shape(self):
        claimed, running, binding, registry = await self.seed_running()
        coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
        interrupted = await coordinator.claim_interrupt(
            dialogue_id="dialogue", job_id="job",
            expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        restored = await coordinator.restore_rejected_interrupt(
            dialogue_id="dialogue", job_id="job",
            claimed_dialogue_version=interrupted.dialogue.version,
            expected_job_version=running.version,
        )
        terminal = await coordinator.reconcile_natural_terminal(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", base_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.FAILED,
            error_class="CODEX_TURN_FAILED",
        )
        self.assertEqual(DialogueState.TURN_RUNNING, restored.dialogue.state)
        self.assertEqual(TurnJobState.FAILED, terminal.job.state)
        self.assertEqual(DialogueState.ERROR, terminal.dialogue.state)
        self.assertEqual(claimed.dialogue.version + 3, terminal.dialogue.version)

    async def test_terminal_wins_restore_race_without_rollback(self):
        claimed, running, binding, registry = await self.seed_running()
        coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
        interrupted = await coordinator.claim_interrupt(
            dialogue_id="dialogue", job_id="job",
            expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        terminal = await coordinator.reconcile_natural_terminal(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", base_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.COMPLETED,
            error_class=None,
        )
        with self.assertRaises(RepositoryError):
            await coordinator.restore_rejected_interrupt(
                dialogue_id="dialogue", job_id="job",
                claimed_dialogue_version=interrupted.dialogue.version,
                expected_job_version=running.version,
            )
        self.assertEqual(DialogueState.IDLE, (await DialogueRepository(self.storage).get_live()).state)
        self.assertEqual(terminal.job, await TurnJobRepository(self.storage).get("job"))

    async def test_empty_output_does_not_generate_output_id(self):
        claimed, running, binding, registry = await self.seed_running()
        ids = []
        life = FakeInterruptLifecycle(messages=(AgentMessageCompleted(1, "item", ""),))
        result = await self.service(registry, life, ids=lambda kind: ids.append(kind) or f"{kind}-id").interrupt(
            DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version)
        )
        self.assertEqual(DialogueInterruptStatus.CONFIRMED, result.status)
        self.assertIsNone(result.output_payload)
        self.assertEqual([], ids)

    async def test_real_admitted_runner_publishes_and_retires_exact_start_binding(self):
        await self.seed_idle_application()
        binding = TurnBinding("profile", "thread", "runner-turn")
        lifecycle = _RunnerLifecycle(binding)
        registry = ActiveTurnRegistry()
        service = ExistingDialogueTurnService(
            self.storage, server_id="server",
            profiles=(CodexProfile("profile", "/PRIVATE/CODEX_HOME", "Profile", "/PRIVATE/STATE_ROOT"),),
            model_catalog=_SettingsCatalog(), turn_lifecycle=lifecycle,
            working_directory_resolver=_RunnerWorkdir(), now_ms=lambda: 1000,
            id_factory=lambda kind: f"{kind}-runner", active_turn_registry=registry,
        )
        task = asyncio.create_task(service.execute(
            ExistingDialoguePromptRequest(20, -1, 20, "prompt")
        ))
        await lifecycle.runner_wait_entered.wait()
        running = await TurnJobRepository(self.storage).get("job-runner")
        self.assertEqual(TurnJobState.CODEX_RUNNING, running.state)
        self.assertIs(binding, registry.lookup("job-runner"))
        self.assertEqual(1, len(lifecycle.start_calls))
        self.assertIs(binding, lifecycle.binding)
        lifecycle.terminal_available.set()
        result = await task
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, result.status)
        self.assertIsNone(registry.lookup("job-runner"))
        self.assertIs(binding, lifecycle.binding)

    async def test_real_runner_interrupt_race_finishes_normally_first_then_falls_back_once(self):
        await self.seed_idle_application()
        binding = TurnBinding("profile", "thread", "race-turn")
        lifecycle = _RunnerLifecycle(binding, race=True)
        registry = ActiveTurnRegistry()
        turn_service = ExistingDialogueTurnService(
            self.storage, server_id="server",
            profiles=(CodexProfile("profile", "/PRIVATE/CODEX_HOME", "Profile", "/PRIVATE/STATE_ROOT"),),
            model_catalog=_SettingsCatalog(), turn_lifecycle=lifecycle,
            working_directory_resolver=_RunnerWorkdir(), now_ms=lambda: 1000,
            id_factory=lambda kind: f"{kind}-runner", active_turn_registry=registry,
        )
        interrupt_service = DialogueInterruptService(
            self.storage, server_id="server", active_turn_registry=registry,
            turn_lifecycle=lifecycle, now_ms=lambda: 1000,
            id_factory=lambda kind: f"{kind}-interrupt",
        )
        events = []
        original_finish = TurnJobRepository.finish_codex
        original_fallback = InterruptCoordinationRepository.reconcile_natural_terminal

        async def finish_spy(repository, *args, **kwargs):
            events.append("finish_codex")
            return await original_finish(repository, *args, **kwargs)

        async def fallback_spy(repository, *args, **kwargs):
            events.append("reconcile_natural_terminal")
            result = await original_fallback(repository, *args, **kwargs)
            lifecycle.fallback_done.set()
            return result

        with patch.object(TurnJobRepository, "finish_codex", finish_spy), \
             patch.object(InterruptCoordinationRepository, "reconcile_natural_terminal", fallback_spy):
            runner_task = asyncio.create_task(turn_service.execute(
                ExistingDialoguePromptRequest(21, -1, 21, "race prompt")
            ))
            await lifecycle.runner_wait_entered.wait()
            running = await TurnJobRepository(self.storage).get("job-runner")
            interrupt_task = asyncio.create_task(interrupt_service.interrupt(
                DialogueInterruptRequest("dialogue", "job-runner", 2, running.version)
            ))
            await lifecycle.interrupt_called.wait()
            current = await DialogueRepository(self.storage).get_live()
            self.assertEqual(DialogueState.INTERRUPTING, current.state)
            self.assertIs(binding, lifecycle.interrupt_calls[0])
            lifecycle.terminal_available.set()
            runner_result, interrupt_result = await asyncio.gather(runner_task, interrupt_task)

        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, runner_result.status)
        self.assertEqual(DialogueInterruptStatus.RECONCILED, interrupt_result.status)
        self.assertEqual(["finish_codex", "reconcile_natural_terminal"], events)
        self.assertEqual(TurnJobState.CODEX_COMPLETED, (await TurnJobRepository(self.storage).get("job-runner")).state)
        self.assertEqual(DialogueState.IDLE, (await DialogueRepository(self.storage).get_live()).state)
        self.assertEqual(1, await self.storage.read(lambda c: c.execute(
            "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT'"
        ).fetchone()[0]))
        self.assertEqual(runner_result.output_payload.payload_id, interrupt_result.output_payload.payload_id)
        self.assertIsNone(registry.lookup("job-runner"))

    async def test_legitimate_interrupt_claim_keeps_settings_mutations_blocked(self):
        await self.seed_running()
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model-a", reasoning_effort="high"
        )
        claimed = await DialogueRepository(self.storage).get_live()
        running = await TurnJobRepository(self.storage).get("job")
        interrupted = await InterruptCoordinationRepository(self.storage, now_ms=lambda: 1).claim_interrupt(
            dialogue_id="dialogue", job_id="job", expected_dialogue_version=claimed.version,
            expected_job_version=running.version,
        )
        self.assertEqual(DialogueState.INTERRUPTING, interrupted.dialogue.state)
        settings_before = await SettingsRepository(self.storage).get()
        selection = SettingsSelectionService(
            self.storage, server_id="server",
            profiles=(
                CodexProfile("profile", "/PRIVATE/CODEX_HOME", "Profile", "/PRIVATE/STATE_ROOT"),
                CodexProfile("profile-b", "/PRIVATE/CODEX_HOME/B", "Profile B", "/PRIVATE/STATE/B"),
            ), model_catalog=_SettingsCatalog(), now_ms=lambda: 1000,
        )
        profile = await selection.select_profile("profile-b", expected_version=settings_before.version)
        model = await selection.select_model("model-b", expected_version=settings_before.version)
        effort = await selection.select_reasoning_effort("low", expected_version=settings_before.version)
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.PROFILE_LOCKED), (profile.status, profile.reason))
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.DIALOGUE_NOT_IDLE), (model.status, model.reason))
        self.assertEqual((SettingsMutationStatus.BLOCKED, SettingsMutationReason.DIALOGUE_NOT_IDLE), (effort.status, effort.reason))
        self.assertEqual(settings_before, await SettingsRepository(self.storage).get())
        self.assertEqual(DialogueState.INTERRUPTING, (await DialogueRepository(self.storage).get_live()).state)

    async def test_approval_callback_created_before_interrupt_is_stale_and_one_time(self):
        claimed, running, binding, registry = await self.seed_running()
        approval = await ApprovalRepository(self.storage, now_ms=lambda: 1).create_pending(
            approval_id="approval", profile_id="profile", wire_request_id=7,
            kind=ApprovalKind.COMMAND_EXECUTION, job_id="job",
            expected_job_version=running.version, expires_at_ms=10_000,
        )
        token_hash = hashlib.sha256(b"approval-token").hexdigest()
        await CallbackActionRepository(self.storage, now_ms=lambda: 1).create(
            token_hash_sha256=token_hash, action="approval_allow",
            subject_type="approval", subject_id=approval.approval_id,
            expected_version=running.version, expected_state="PENDING",
            authorized_user_id=7, authorized_chat_id=-77, expires_at_ms=10_000,
        )
        interrupted = await InterruptCoordinationRepository(self.storage, now_ms=lambda: 1).claim_interrupt(
            dialogue_id="dialogue", job_id="job",
            expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        self.assertEqual(DialogueState.INTERRUPTING, interrupted.dialogue.state)
        approvals = ApprovalRepository(self.storage, now_ms=lambda: 1)
        stale = await approvals.claim_callback(
            token_hash_sha256=token_hash, authorized_user_id=7, authorized_chat_id=-77,
        )
        self.assertEqual(ApprovalCallbackClaimStatus.STALE, stale.status)
        self.assertIsNone(stale.record)
        self.assertEqual(ApprovalState.PENDING, (await approvals.get("approval")).state)
        replay = await approvals.claim_callback(
            token_hash_sha256=token_hash, authorized_user_id=7, authorized_chat_id=-77,
        )
        self.assertEqual(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, replay.status)

    async def test_partial_output_projection_and_accepted_retention(self):
        async def check(status, terminal_status, interrupt_error, retention):
            claimed, running, binding, registry = await self.seed_running()
            life = FakeInterruptLifecycle(
                terminal_status=terminal_status,
                interrupt_error=interrupt_error,
                messages=(
                    AgentMessageCompleted(1, "item-a", "first"),
                    AgentMessageCompleted(2, "item-b", "second"),
                ),
            )
            result = await self.service(
                registry, life, ids=lambda kind: f"{kind}-{status.value.lower()}"
            ).interrupt(DialogueInterruptRequest("dialogue", "job", claimed.dialogue.version, running.version))
            self.assertEqual(status, result.status)
            self.assertIsNotNone(result.output_payload)
            self.assertEqual(b"first\n\nsecond", result.output_payload.content)
            self.assertEqual("OUTPUT", result.output_payload.kind.value)
            self.assertEqual("job", result.output_payload.job_id)
            self.assertEqual("dialogue", result.output_payload.dialogue_id)
            self.assertEqual(retention, result.output_payload.expires_at_ms - result.output_payload.created_at_ms)
            self.assertEqual(hashlib.sha256(b"first\n\nsecond").hexdigest(), result.output_payload.content_sha256)
            self.assertEqual(len(b"first\n\nsecond"), result.output_payload.byte_length)
            self.assertNotIn("first", repr(result))
            self.assertNotIn("second", repr(result))

        await check(
            DialogueInterruptStatus.CONFIRMED, TurnTerminalStatus.COMPLETED, None,
            P3_COMPLETED_OUTPUT_RETENTION_MS,
        )
        await self.reset_storage()
        await check(
            DialogueInterruptStatus.CONFIRMED, TurnTerminalStatus.FAILED, None,
            P3_UNCERTAIN_OUTPUT_RETENTION_MS,
        )
        await self.reset_storage()
        await check(
            DialogueInterruptStatus.UNKNOWN, TurnTerminalStatus.UNKNOWN,
            RuntimeError("PRIVATE_UNKNOWN_OUTPUT_ERROR"), P3_UNCERTAIN_OUTPUT_RETENTION_MS,
        )

    async def test_startup_recovery_is_no_p1_idempotent_and_preserves_evidence(self):
        claimed, running, binding, registry = await self.seed_running()
        claimed_interrupt = await InterruptCoordinationRepository(self.storage, now_ms=lambda: 1).claim_interrupt(
            dialogue_id="dialogue", job_id="job", expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        life = FakeInterruptLifecycle()
        service = self.service(ActiveTurnRegistry(), life)
        recovered = await service.recover_preexisting_interrupt()
        self.assertEqual(InterruptRecoveryStatus.MARKED_UNKNOWN, recovered.status)
        self.assertEqual(TurnJobState.UNKNOWN, recovered.job.state)
        self.assertEqual(DialogueState.TURN_UNKNOWN, recovered.dialogue.state)
        self.assertEqual(1, recovered.job.telegram_update_id)
        self.assertEqual("thread", recovered.job.thread_id)
        self.assertEqual("turn-job", recovered.job.codex_turn_id)
        self.assertEqual([], life.interrupt_calls)
        again = await service.recover_preexisting_interrupt()
        self.assertEqual(InterruptRecoveryStatus.NO_ACTION, again.status)
        self.assertEqual(claimed_interrupt.dialogue.version + 1, recovered.dialogue.version)

    async def test_ddl_unchanged_and_input_evidence_survives_recovery(self):
        claimed, running, binding, registry = await self.seed_running()
        await InterruptCoordinationRepository(self.storage, now_ms=lambda: 1).claim_interrupt(
            dialogue_id="dialogue", job_id="job", expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        await DialogueInterruptService(self.storage, server_id="server", active_turn_registry=ActiveTurnRegistry(), turn_lifecycle=FakeInterruptLifecycle()).recover_preexisting_interrupt()
        self.assertEqual("job", (await IngressUpdateRepository(self.storage).get(1)).job_id)
        payload = await self.storage.read(lambda connection: connection.execute(
            "SELECT content FROM transient_payloads WHERE payload_id = 'input-job'").fetchone()[0])
        self.assertEqual(b"input", payload)
        self.assertEqual(SCHEMA_V1_DDL_SHA256, "b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c")

    async def test_terminal_reconstruction_requires_exact_canonical_error_semantics(self):
        async def canonical(outcome, *, natural=False):
            claimed, running, binding, registry = await self.seed_running()
            coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
            interrupted = await coordinator.claim_interrupt(
                dialogue_id="dialogue", job_id="job",
                expected_dialogue_version=claimed.dialogue.version,
                expected_job_version=running.version,
            )
            error_class = None if outcome is TurnTerminalOutcome.COMPLETED else (
                "CODEX_TURN_FAILED" if outcome is TurnTerminalOutcome.FAILED else "CODEX_AMBIGUOUS"
            )
            if natural:
                await coordinator.restore_rejected_interrupt(
                    dialogue_id="dialogue", job_id="job",
                    claimed_dialogue_version=interrupted.dialogue.version,
                    expected_job_version=running.version,
                )
                terminal = await coordinator.reconcile_natural_terminal(
                    dialogue_id="dialogue", job_id="job", profile_id="profile",
                    thread_id="thread", codex_turn_id="turn-job",
                    base_dialogue_version=claimed.dialogue.version,
                    expected_job_version=running.version, outcome=outcome,
                    error_class=error_class,
                )
            else:
                terminal = await coordinator.terminalize_interrupt(
                    dialogue_id="dialogue", job_id="job", profile_id="profile",
                    thread_id="thread", codex_turn_id="turn-job",
                    claimed_dialogue_version=interrupted.dialogue.version,
                    expected_job_version=running.version, outcome=outcome,
                    error_class=error_class,
                )
            return claimed, running, terminal

        await canonical(TurnTerminalOutcome.COMPLETED)
        await self.storage.write(lambda c: (
            c.execute("UPDATE turn_jobs SET error_class = 'PRIVATE_CORRUPT_TERMINAL' WHERE job_id = 'job'"),
            None,
        )[-1])
        clock = _CountingClock()
        with self.assertRaises(RepositoryError) as raised:
            await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
                dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
                codex_turn_id="turn-job", claimed_dialogue_version=3,
                expected_job_version=3, outcome=TurnTerminalOutcome.COMPLETED,
                error_class=None,
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertNotIn("PRIVATE_CORRUPT_TERMINAL", str(raised.exception) + repr(raised.exception))
        self.assertEqual(0, clock.calls)

        await self.reset_storage()
        claimed, running, failed = await canonical(TurnTerminalOutcome.FAILED)
        self.assertEqual(TurnJobState.FAILED, failed.job.state)
        self.assertEqual(DialogueState.IDLE, failed.dialogue.state)
        self.assertEqual("CODEX_TURN_FAILED", failed.job.error_class)
        self.assertIsNone(failed.dialogue.last_error_class)
        clock = _CountingClock()
        rebuilt = await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", claimed_dialogue_version=3,
            expected_job_version=3, outcome=TurnTerminalOutcome.FAILED,
            error_class="CODEX_TURN_FAILED",
        )
        self.assertEqual(failed, rebuilt)
        self.assertEqual(0, clock.calls)
        await self.storage.write(lambda c: (
            c.execute("UPDATE turn_jobs SET error_class = 'WRONG_TERMINAL_ERROR' WHERE job_id = 'job'"),
            None,
        )[-1])
        clock = _CountingClock()
        with self.assertRaises(RepositoryError) as raised:
            await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
                dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
                codex_turn_id="turn-job", claimed_dialogue_version=3,
                expected_job_version=3, outcome=TurnTerminalOutcome.FAILED,
                error_class="CODEX_TURN_FAILED",
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertEqual(0, clock.calls)

        await self.reset_storage()
        claimed, running, natural_failed = await canonical(TurnTerminalOutcome.FAILED, natural=True)
        self.assertEqual(DialogueState.ERROR, natural_failed.dialogue.state)
        self.assertEqual("CODEX_TURN_FAILED", natural_failed.dialogue.last_error_class)
        clock = _CountingClock()
        rebuilt_natural = await InterruptCoordinationRepository(self.storage, now_ms=clock).reconcile_natural_terminal(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", base_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.FAILED,
            error_class="CODEX_TURN_FAILED",
        )
        self.assertEqual(natural_failed, rebuilt_natural)
        self.assertEqual(0, clock.calls)

        for corrupt_job, corrupt_dialogue in (("WRONG_TERMINAL_ERROR", None), (None, "WRONG_TERMINAL_ERROR")):
            await self.reset_storage()
            await canonical(TurnTerminalOutcome.UNKNOWN)
            await self.storage.write(lambda c, cj=corrupt_job, cd=corrupt_dialogue: (
                c.execute("UPDATE turn_jobs SET error_class = ? WHERE job_id = 'job'", (cj,)) if cj else
                c.execute("UPDATE dialogues SET last_error_class = ? WHERE dialogue_id = 'dialogue'", (cd,)),
                None,
            )[-1])
            clock = _CountingClock()
            with self.assertRaises(RepositoryError) as raised:
                await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
                    dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
                    codex_turn_id="turn-job", claimed_dialogue_version=3,
                    expected_job_version=3, outcome=TurnTerminalOutcome.UNKNOWN,
                    error_class="CODEX_AMBIGUOUS",
                )
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertNotIn("WRONG_TERMINAL_ERROR", str(raised.exception) + repr(raised.exception))
            self.assertEqual(0, clock.calls)

    async def test_terminal_version_overflow_is_invariant_before_clock_and_output(self):
        async def overflow(axis):
            claimed, running, binding, registry = await self.seed_running()
            coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
            interrupted = await coordinator.claim_interrupt(
                dialogue_id="dialogue", job_id="job",
                expected_dialogue_version=claimed.dialogue.version,
                expected_job_version=running.version,
            )
            if axis == "job":
                await self.storage.write(lambda c: (
                    c.execute("UPDATE turn_jobs SET version = ? WHERE job_id = 'job'", (MAX_SQLITE_INT,)), None
                )[-1])
                claimed_dialogue_version = interrupted.dialogue.version
                expected_job_version = MAX_SQLITE_INT
            else:
                await self.storage.write(lambda c: (
                    c.execute("UPDATE dialogues SET version = ? WHERE dialogue_id = 'dialogue'", (MAX_SQLITE_INT,)), None
                )[-1])
                claimed_dialogue_version = MAX_SQLITE_INT
                expected_job_version = running.version
            before = await self.storage.read(lambda c: tuple(c.execute(
                "SELECT state, version, error_class FROM turn_jobs WHERE job_id = 'job'"
            ).fetchone()) + tuple(c.execute(
                "SELECT state, version, last_error_class FROM dialogues WHERE dialogue_id = 'dialogue'"
            ).fetchone()))
            clock = _CountingClock()
            with self.assertRaises(RepositoryError) as raised:
                await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
                    dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
                    codex_turn_id="turn-job", claimed_dialogue_version=claimed_dialogue_version,
                    expected_job_version=expected_job_version, outcome=TurnTerminalOutcome.COMPLETED,
                    error_class=None, output_payload_id=f"output-{axis}", output_content=b"valid",
                    output_expires_at_ms=MAX_SQLITE_INT,
                )
            self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
            self.assertEqual(0, clock.calls)
            after = await self.storage.read(lambda c: tuple(c.execute(
                "SELECT state, version, error_class FROM turn_jobs WHERE job_id = 'job'"
            ).fetchone()) + tuple(c.execute(
                "SELECT state, version, last_error_class FROM dialogues WHERE dialogue_id = 'dialogue'"
            ).fetchone()))
            self.assertEqual(before, after)
            self.assertEqual(0, await self.storage.read(lambda c: c.execute(
                "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT'"
            ).fetchone()[0]))

        await overflow("job")
        await self.reset_storage()
        await overflow("dialogue")

    async def test_exact_max_terminal_reconstruction_is_idempotent_without_clock(self):
        claimed, running, binding, registry = await self.seed_running()
        coordinator = InterruptCoordinationRepository(self.storage, now_ms=lambda: 1)
        interrupted = await coordinator.claim_interrupt(
            dialogue_id="dialogue", job_id="job",
            expected_dialogue_version=claimed.dialogue.version,
            expected_job_version=running.version,
        )
        terminal = await coordinator.terminalize_interrupt(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", claimed_dialogue_version=interrupted.dialogue.version,
            expected_job_version=running.version, outcome=TurnTerminalOutcome.COMPLETED,
            error_class=None,
        )
        await self.storage.write(lambda c: (
            c.execute("UPDATE turn_jobs SET version = ? WHERE job_id = 'job'", (MAX_SQLITE_INT,)),
            c.execute("UPDATE dialogues SET version = ? WHERE dialogue_id = 'dialogue'", (MAX_SQLITE_INT,)),
            None,
        )[-1])
        clock = _CountingClock()
        reconstructed = await InterruptCoordinationRepository(self.storage, now_ms=clock).terminalize_interrupt(
            dialogue_id="dialogue", job_id="job", profile_id="profile", thread_id="thread",
            codex_turn_id="turn-job", claimed_dialogue_version=MAX_SQLITE_INT - 1,
            expected_job_version=MAX_SQLITE_INT - 1, outcome=TurnTerminalOutcome.COMPLETED,
            error_class=None,
        )
        self.assertEqual(TurnJobState.CODEX_COMPLETED, reconstructed.job.state)
        self.assertEqual(DialogueState.IDLE, reconstructed.dialogue.state)
        self.assertEqual(MAX_SQLITE_INT, reconstructed.job.version)
        self.assertEqual(MAX_SQLITE_INT, reconstructed.dialogue.version)
        self.assertEqual(0, clock.calls)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute(
            "SELECT COUNT(*) FROM transient_payloads WHERE kind = 'OUTPUT'"
        ).fetchone()[0]))


if __name__ == "__main__":
    unittest.main()
