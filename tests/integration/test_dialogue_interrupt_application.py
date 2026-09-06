import asyncio
import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnLifecycleError,
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
    InterruptRecoveryStatus,
)
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    RepositoryError,
    SCHEMA_V1_DDL_SHA256,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)
from codex_control.storage.interrupt_coordination import InterruptCoordinationRepository


class FakeInterruptLifecycle:
    def __init__(self, *, interrupt_status=TurnInterruptStatus.CONFIRMED,
                 terminal_status=TurnTerminalStatus.COMPLETED, messages=(), interrupt_error=None,
                 wait_result=None, interrupt_gate=None):
        self.binding = None
        self.interrupt_status = interrupt_status
        self.terminal_status = terminal_status
        self.messages = tuple(messages)
        self.interrupt_error = interrupt_error
        self.wait_result = wait_result
        self.interrupt_gate = interrupt_gate
        self.interrupt_calls = []
        self.wait_calls = []

    def _terminal(self, binding):
        return TurnTerminalResult(binding, self.terminal_status, self.messages)

    async def interrupt_turn(self, binding):
        self.interrupt_calls.append(binding)
        if self.interrupt_gate is not None:
            await self.interrupt_gate.wait()
        if self.interrupt_error is not None:
            raise self.interrupt_error
        result = TurnInterruptResult(self.interrupt_status, binding)
        if self.interrupt_status in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED):
            result = TurnInterruptResult(self.interrupt_status, binding, self._terminal(binding))
        return result

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        if self.wait_result is not None:
            return self.wait_result
        return self._terminal(binding)


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
        self.assertEqual({DialogueInterruptStatus.CONFIRMED, DialogueInterruptStatus.BLOCKED}, {r.status for r in results})

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


if __name__ == "__main__":
    unittest.main()
