import asyncio
import os
import tempfile
import unittest

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.adapters.codex.turn_lifecycle import TurnBinding
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueDeleteError,
    DialogueDeleteReason,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueInterruptResult,
    DialogueInterruptStatus,
    DialogueRecoveryError,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    RepositoryError,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)


class FakeDeleteLifecycle:
    def __init__(self, *, mode="confirmed", gate=None):
        self.mode = mode
        self.gate = gate
        self.calls = []
        self.before_call = None
        self.entered = asyncio.Event()

    async def delete(self, *, binding):
        self.calls.append(binding)
        self.entered.set()
        if self.before_call is not None:
            await self.before_call(binding)
        if self.gate is not None:
            await self.gate.wait()
        if self.mode == "local":
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        if self.mode == "exception":
            raise RuntimeError("PRIVATE_DELETE_ERROR")
        if self.mode == "clone":
            return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED,
                                         ThreadBinding(binding.profile_id, binding.thread_id))
        if self.mode == "malformed":
            return object()
        if self.mode == "unknown":
            return ThreadOperationResult(ThreadOperationStatus.DELETE_UNKNOWN, binding)
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class FakeInterruptService:
    def __init__(self, result_status=DialogueInterruptStatus.CONFIRMED, *, dialogue=None, job=None):
        self.result_status = result_status
        self.dialogue = dialogue
        self.job = job
        self.calls = []

    async def interrupt(self, request):
        self.calls.append(request)
        return DialogueInterruptResult(self.result_status, self.job, self.dialogue, None, None)


class DialogueDeleteRecoveryApplicationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def seed_idle(self, *, dialogue_id="dialogue", thread_id="thread"):
        repo = DialogueRepository(self.storage, now_ms=lambda: 1)
        await repo.create_intent(dialogue_id=dialogue_id, server_id="server", profile_id="profile")
        return await repo.confirm_created(dialogue_id=dialogue_id, expected_version=0, thread_id=thread_id)

    async def seed_running(self, *, job_id="job", update_id=1):
        current = await self.seed_idle()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(
            update_id=update_id, job_id=job_id, source_chat_id=-1, source_message_id=1,
            dialogue_id=current.dialogue_id, server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input-" + job_id,
            input_content=b"input", input_expires_at_ms=1000,
        )
        now = await DialogueRepository(self.storage).get_live()
        claimed = await jobs.claim_turn(job_id=job_id, expected_job_version=admitted.job.version,
                                         expected_dialogue_version=now.version, thread_id="thread")
        starting = await jobs.mark_codex_starting(job_id=job_id, expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(job_id=job_id, expected_version=starting.version,
                                                codex_turn_id="turn-" + job_id)
        return current, claimed.dialogue, running

    def delete_service(self, lifecycle, *, interrupt=None, clock=lambda: 100):
        return DialogueDeleteService(
            self.storage, server_id="server", thread_lifecycle=lifecycle,
            interrupt_service=interrupt, now_ms=clock,
        )

    async def test_no_dialogue_and_stale_requests_are_effect_free(self):
        life = FakeDeleteLifecycle()
        service = self.delete_service(life)
        result = await service.delete(DialogueDeleteRequest("missing", 0))
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.NO_DIALOGUE),
                         (result.status, result.reason))
        current = await self.seed_idle()
        stale = await service.delete(DialogueDeleteRequest("dialogue", current.version + 1))
        self.assertEqual((DialogueDeleteStatus.CONFLICT, DialogueDeleteReason.STALE_REQUEST),
                         (stale.status, stale.reason))
        self.assertEqual([], life.calls)

    async def test_durable_deleting_precedes_one_confirmed_p1_delete_and_replays(self):
        current = await self.seed_idle()
        observed = []
        life = FakeDeleteLifecycle()

        async def proof(binding):
            durable = await DialogueRepository(self.storage).get_live()
            observed.append(durable)
            self.assertEqual(DialogueState.DELETING, durable.state)
            self.assertEqual(current.version + 2, durable.version)
            self.assertEqual("profile", binding.profile_id)
            self.assertEqual("thread", binding.thread_id)

        life.before_call = proof
        service = self.delete_service(life)
        result = await service.delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertEqual(DialogueDeleteStatus.DELETED, result.status)
        self.assertIsNone(result.dialogue)
        self.assertEqual(1, len(life.calls))
        self.assertEqual(1, len(observed))
        self.assertEqual(604800000, result.tombstone.expires_at_ms - result.tombstone.deleted_at_ms)
        replay = await service.delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertEqual(DialogueDeleteStatus.DELETED, replay.status)
        self.assertEqual(result.tombstone, replay.tombstone)
        self.assertEqual(1, len(life.calls))

    async def test_local_preeffect_failure_is_failed_and_unknown_is_never_retried(self):
        current = await self.seed_idle()
        local = FakeDeleteLifecycle(mode="local")
        result = await self.delete_service(local).delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertEqual(DialogueDeleteStatus.FAILED, result.status)
        self.assertEqual(DialogueState.ERROR, result.dialogue.state)
        self.assertEqual("CODEX_PROCESS", result.dialogue.last_error_class)
        self.assertEqual(1, len(local.calls))

        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        current = await self.seed_idle()
        unknown = FakeDeleteLifecycle(mode="clone")
        result = await self.delete_service(unknown).delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertEqual(DialogueDeleteStatus.UNKNOWN, result.status)
        self.assertEqual(DialogueState.DELETE_UNKNOWN, result.dialogue.state)
        replay = await self.delete_service(FakeDeleteLifecycle()).delete(
            DialogueDeleteRequest("dialogue", current.version)
        )
        self.assertEqual(DialogueDeleteStatus.UNKNOWN, replay.status)
        self.assertIsNone(replay.tombstone)

    async def test_codex_completed_without_terminal_delivery_is_delete_not_ready(self):
        _, claimed_dialogue, running = await self.seed_running()
        finished = await TurnJobRepository(self.storage, now_ms=lambda: 2).finish_codex(
            job_id=running.job_id,
            expected_job_version=running.version,
            expected_dialogue_version=claimed_dialogue.version,
            outcome=TurnTerminalOutcome.COMPLETED,
        )
        life = FakeDeleteLifecycle()
        result = await self.delete_service(life).delete(
            DialogueDeleteRequest("dialogue", finished.dialogue.version)
        )
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.DELETE_NOT_READY),
                         (result.status, result.reason))
        self.assertEqual([], life.calls)

    async def test_same_generation_concurrent_requests_have_one_owner_and_one_p1(self):
        current = await self.seed_idle()
        gate = asyncio.Event()
        first_life = FakeDeleteLifecycle(gate=gate)
        second_life = FakeDeleteLifecycle()
        first = self.delete_service(first_life)
        second = self.delete_service(second_life)
        first_task = asyncio.create_task(first.delete(DialogueDeleteRequest("dialogue", current.version)))
        await first_life.entered.wait()
        second_result = await second.delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertIn(second_result.status, (DialogueDeleteStatus.CONFLICT, DialogueDeleteStatus.BLOCKED))
        if second_result.status is DialogueDeleteStatus.BLOCKED:
            self.assertEqual(DialogueDeleteReason.DELETE_IN_PROGRESS, second_result.reason)
        self.assertEqual([], second_life.calls)
        gate.set()
        first_result = await first_task
        self.assertEqual(DialogueDeleteStatus.DELETED, first_result.status)
        self.assertEqual(1, len(first_life.calls))

    async def test_delete_pending_fresh_request_continues_after_restart_old_request_is_stale(self):
        current = await self.seed_idle()
        pending = await DeletionRepository(self.storage, now_ms=lambda: 10).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 10)
        old = await self.delete_service(FakeDeleteLifecycle()).delete(
            DialogueDeleteRequest("dialogue", current.version)
        )
        self.assertEqual((DialogueDeleteStatus.CONFLICT, DialogueDeleteReason.STALE_REQUEST),
                         (old.status, old.reason))
        life = FakeDeleteLifecycle()
        fresh = await self.delete_service(life).delete(
            DialogueDeleteRequest("dialogue", pending.version)
        )
        self.assertEqual(DialogueDeleteStatus.DELETED, fresh.status)
        self.assertEqual(1, len(life.calls))

    async def test_deleting_startup_recovery_marks_unknown_without_p1(self):
        current = await self.seed_idle()
        pending = await DeletionRepository(self.storage, now_ms=lambda: 2).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        deleting = await DeletionRepository(self.storage, now_ms=lambda: 3).claim_deleting(
            dialogue_id="dialogue", expected_version=pending.version
        )
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: 4)
        result = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.DELETE_MARKED_UNKNOWN, result.status)
        self.assertEqual(DialogueState.DELETE_UNKNOWN, result.dialogue.state)
        self.assertEqual("DELETE_UNKNOWN", result.dialogue.last_error_class)
        repeated = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, repeated.status)
        self.assertEqual(deleting.version + 1, result.dialogue.version)

    async def test_running_delete_uses_interrupt_and_unresolved_interrupt_never_deletes(self):
        _, running_dialogue, running_job = await self.seed_running()
        unresolved = FakeInterruptService(DialogueInterruptStatus.UNKNOWN,
                                          dialogue=running_dialogue, job=running_job)
        life = FakeDeleteLifecycle()
        result = await self.delete_service(life, interrupt=unresolved).delete(
            DialogueDeleteRequest("dialogue", running_dialogue.version)
        )
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.INTERRUPT_UNRESOLVED),
                         (result.status, result.reason))
        self.assertEqual(1, len(unresolved.calls))
        self.assertEqual([], life.calls)

    async def test_running_claimed_is_not_fabricated_into_an_interrupt(self):
        current = await self.seed_idle()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(
            update_id=3, job_id="job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input",
            input_content=b"input", input_expires_at_ms=1000,
        )
        claimed = await jobs.claim_turn(job_id="job", expected_job_version=admitted.job.version,
                                        expected_dialogue_version=current.version, thread_id="thread")
        life = FakeDeleteLifecycle()
        interrupt = FakeInterruptService()
        result = await self.delete_service(life, interrupt=interrupt).delete(
            DialogueDeleteRequest("dialogue", claimed.dialogue.version)
        )
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.DIALOGUE_NOT_READY),
                         (result.status, result.reason))
        self.assertEqual([], interrupt.calls)
        self.assertEqual([], life.calls)

    async def test_recovery_received_claimed_starting_running_and_idempotence(self):
        current = await self.seed_idle()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(
            update_id=4, job_id="job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input",
            input_content=b"input", input_expires_at_ms=1000,
        )
        result = await DialogueRecoveryService(self.storage, now_ms=lambda: 8).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.PRE_EFFECT_FAILED, result.status)
        self.assertEqual(TurnJobState.FAILED, result.job.state)
        self.assertEqual(DialogueState.IDLE, result.dialogue.state)
        self.assertEqual(current.version, result.dialogue.version)
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION,
                         (await DialogueRecoveryService(self.storage).recover_startup()).status)

        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.IDLE, current.state)

    async def test_recovery_creating_and_interrupting_are_zero_p1_transitions(self):
        await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
            dialogue_id="dialogue", server_id="server", profile_id="profile"
        )
        creating = await DialogueRecoveryService(self.storage, now_ms=lambda: 2).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.CREATE_MARKED_UNKNOWN, creating.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, creating.dialogue.state)

        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        _, claimed_dialogue, running = await self.seed_running()
        def mark_interrupting(connection):
            connection.execute(
                "UPDATE dialogues SET state = 'INTERRUPTING', version = ? WHERE dialogue_id = ?",
                (claimed_dialogue.version + 1, "dialogue"),
            )
        await self.storage.write(mark_interrupting)
        interrupted = await DialogueRecoveryService(self.storage, now_ms=lambda: 3).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.INTERRUPT_MARKED_UNKNOWN, interrupted.status)
        self.assertEqual(DialogueState.TURN_UNKNOWN, interrupted.dialogue.state)
        self.assertEqual(TurnJobState.UNKNOWN, interrupted.job.state)

    async def test_recovery_running_effect_possible_marks_both_unknown(self):
        _, claimed_dialogue, running = await self.seed_running()
        result = await DialogueRecoveryService(self.storage, now_ms=lambda: 9).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.TURN_MARKED_UNKNOWN, result.status)
        self.assertEqual(TurnJobState.UNKNOWN, result.job.state)
        self.assertEqual(DialogueState.TURN_UNKNOWN, result.dialogue.state)
        self.assertEqual(claimed_dialogue.version + 1, result.dialogue.version)
        self.assertEqual(running.version + 1, result.job.version)

    async def test_recovery_pending_is_held_without_clock_or_effect(self):
        current = await self.seed_idle()
        pending = await DeletionRepository(self.storage, now_ms=lambda: 5).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        calls = []
        result = await DialogueRecoveryService(self.storage, now_ms=lambda: calls.append(1) or 8).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, result.status)
        self.assertEqual([], calls)
        now = await DialogueRepository(self.storage).get_live()
        self.assertEqual((DialogueState.DELETE_PENDING, pending.version), (now.state, now.version))

    async def test_recovery_version_overflow_and_missing_running_job_fail_closed(self):
        current = await self.seed_idle()
        admitted = await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
            update_id=8, job_id="job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input-overflow",
            input_content=b"input", input_expires_at_ms=1000,
        )
        def bump_job(connection):
            connection.execute(
                "UPDATE turn_jobs SET version = ? WHERE job_id = ?",
                (9_223_372_036_854_775_807, admitted.job.job_id),
            )
        await self.storage.write(bump_job)
        with self.assertRaises(DialogueRecoveryError) as raised:
            await DialogueRecoveryService(self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).recover_startup()
        self.assertEqual("INVARIANT", str(raised.exception))
        await self.storage.close()
        self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        await self.seed_idle()
        def strand_running(connection):
            connection.execute("UPDATE dialogues SET state = 'TURN_RUNNING', version = 1")
        await self.storage.write(strand_running)
        with self.assertRaises(DialogueRecoveryError):
            await DialogueRecoveryService(self.storage, now_ms=lambda: 2).recover_startup()


if __name__ == "__main__":
    unittest.main()
