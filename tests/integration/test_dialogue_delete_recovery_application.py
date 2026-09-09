import asyncio
import os
import tempfile
import unittest
from dataclasses import replace

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueDeleteError,
    DialogueDeleteReason,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueInterruptService,
    DialogueInterruptResult,
    DialogueInterruptStatus,
    DialogueRecoveryError,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
    DialogueTurnService,
    ExistingDialoguePromptRequest,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    IngressUpdateRepository,
    RepositoryError,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
    TransientPayloadRepository,
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
    def __init__(self, result_status=DialogueInterruptStatus.CONFIRMED, *, dialogue=None, job=None,
                 before_return=None):
        self.result_status = result_status
        self.dialogue = dialogue
        self.job = job
        self.before_return = before_return
        self.calls = []

    async def interrupt(self, request):
        self.calls.append(request)
        if self.before_return is not None:
            self.before_return()
        return DialogueInterruptResult(self.result_status, self.job, self.dialogue, None, None)


class CreationCatalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (CodexModelDescriptor("model", "wire-model", "Model", ("high",), "high", True, False),),
            0.0, 100.0,
        )


class CreationWorkdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class CreationThread:
    def __init__(self, status):
        self.status = status
        self.calls = []

    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        self.calls.append((profile_id, model_id, reasoning_effort, working_directory))
        return ThreadOperationResult(self.status)


class CreationTurns:
    def __init__(self):
        self.start_calls = []

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        raise AssertionError("thread-start failure must precede turn/start")

    async def wait_turn(self, binding):
        raise AssertionError("thread-start failure must precede turn/wait")


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
        self.active_registry = ActiveTurnRegistry()
        self.active_registry.publish(
            job_id, TurnBinding("profile", "thread", "turn-" + job_id)
        )
        return current, claimed.dialogue, running

    def delete_service(self, lifecycle, *, interrupt=None, clock=lambda: 100, registry=None):
        selected_registry = (
            self.active_registry if registry is None and hasattr(self, "active_registry") else registry
        )
        return DialogueDeleteService(
            self.storage, server_id="server", thread_lifecycle=lifecycle,
            interrupt_service=interrupt, active_turn_registry=selected_registry, now_ms=clock,
        )

    def creation_service(self, thread, turns):
        return DialogueTurnService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/private/CODEX_HOME", "Profile"),),
            model_catalog=CreationCatalog(),
            thread_lifecycle=thread,
            turn_lifecycle=turns,
            working_directory_resolver=CreationWorkdir(),
            now_ms=lambda: 10,
            id_factory=lambda kind: f"creation-{kind}",
        )

    async def reset_storage(self):
        def clear(connection):
            for table in (
                "delivery_segments", "approvals", "transient_payloads", "turn_jobs",
                "ingress_updates", "callback_actions", "errors", "dialogues",
                "deletion_tombstones",
            ):
                connection.execute(f"DELETE FROM {table}")
        await self.storage.write(clear)

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
        self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, result.status)
        self.assertIsNotNone(result.dialogue)
        self.assertEqual(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, result.dialogue.state)
        self.assertIsNone(result.tombstone)
        self.assertEqual(1, len(life.calls))
        self.assertEqual(1, len(observed))
        self.assertEqual("thread", result.dialogue.thread_id)
        replay = await service.delete(DialogueDeleteRequest("dialogue", result.dialogue.version))
        self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, replay.status)
        self.assertEqual(result.dialogue, replay.dialogue)
        self.assertIsNone(replay.tombstone)
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
        current_unknown = await DialogueRepository(self.storage).get_live()
        replay = await self.delete_service(FakeDeleteLifecycle()).delete(
            DialogueDeleteRequest("dialogue", current_unknown.version)
        )
        self.assertEqual(DialogueDeleteStatus.UNKNOWN, replay.status)
        self.assertIsNone(replay.tombstone)

    async def test_stale_and_current_versions_precede_deleting_and_unknown_state_mapping(self):
        current = await self.seed_idle()
        pending = await DeletionRepository(self.storage, now_ms=lambda: 2).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        deleting = await DeletionRepository(self.storage, now_ms=lambda: 3).claim_deleting(
            dialogue_id="dialogue", expected_version=pending.version
        )
        clock_calls = []
        lifecycle = FakeDeleteLifecycle()
        stale = await self.delete_service(lifecycle, clock=lambda: clock_calls.append(1) or 100).delete(
            DialogueDeleteRequest("dialogue", deleting.version - 1)
        )
        self.assertEqual((DialogueDeleteStatus.CONFLICT, DialogueDeleteReason.STALE_REQUEST),
                         (stale.status, stale.reason))
        current_result = await self.delete_service(lifecycle, clock=lambda: clock_calls.append(1) or 100).delete(
            DialogueDeleteRequest("dialogue", deleting.version)
        )
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.DELETE_IN_PROGRESS),
                         (current_result.status, current_result.reason))
        self.assertEqual([], lifecycle.calls)
        self.assertEqual([], clock_calls)

        await self.reset_storage()
        current = await self.seed_idle()
        pending = await DeletionRepository(self.storage, now_ms=lambda: 2).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        deleting = await DeletionRepository(self.storage, now_ms=lambda: 3).claim_deleting(
            dialogue_id="dialogue", expected_version=pending.version
        )
        unknown = await DeletionRepository(self.storage, now_ms=lambda: 4).mark_delete_unknown(
            dialogue_id="dialogue", expected_version=deleting.version, error_class="DELETE_UNKNOWN"
        )
        stale = await self.delete_service(FakeDeleteLifecycle(), clock=lambda: clock_calls.append(1) or 100).delete(
            DialogueDeleteRequest("dialogue", unknown.version - 1)
        )
        self.assertEqual((DialogueDeleteStatus.CONFLICT, DialogueDeleteReason.STALE_REQUEST),
                         (stale.status, stale.reason))
        exact = await self.delete_service(FakeDeleteLifecycle(), clock=lambda: clock_calls.append(1) or 100).delete(
            DialogueDeleteRequest("dialogue", unknown.version)
        )
        self.assertEqual(DialogueDeleteStatus.UNKNOWN, exact.status)
        self.assertEqual([], clock_calls)

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
        self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, first_result.status)
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
        self.assertEqual(DialogueDeleteStatus.CONFIRMED_PENDING_STORAGE, fresh.status)
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
        exact_binding = self.active_registry.lookup(running_job.job_id)
        watches = []
        original_arm = self.active_registry.wait_retired

        def arm(job_id, binding):
            watch = original_arm(job_id, binding)
            watches.append(watch)
            return watch

        self.active_registry.wait_retired = arm

        def assert_armed_before_interrupt():
            self.assertEqual(1, len(watches))
            self.assertIs(exact_binding, self.active_registry.lookup(running_job.job_id))

        unresolved = FakeInterruptService(DialogueInterruptStatus.UNKNOWN,
                                          dialogue=running_dialogue, job=running_job,
                                          before_return=assert_armed_before_interrupt)
        life = FakeDeleteLifecycle()
        result = await self.delete_service(life, interrupt=unresolved).delete(
            DialogueDeleteRequest("dialogue", running_dialogue.version)
        )
        self.assertEqual((DialogueDeleteStatus.BLOCKED, DialogueDeleteReason.INTERRUPT_UNRESOLVED),
                         (result.status, result.reason))
        self.assertEqual(1, len(unresolved.calls))
        self.assertEqual([], life.calls)
        self.assertTrue(watches[0]._disposed)
        self.assertIs(exact_binding, self.active_registry.lookup(running_job.job_id))
        self.active_registry.retire(running_job.job_id, exact_binding)
        self.assertIsNone(self.active_registry.lookup(running_job.job_id))
        self.assertNotIn("_retired", vars(self.active_registry))

    async def test_running_delete_fails_closed_after_transient_replacements_before_quiescence(self):
        _, running_dialogue, running_job = await self.seed_running()
        old_binding = self.active_registry.lookup(running_job.job_id)

        class TransientReplacementLifecycle:
            async def interrupt_turn(inner_self, binding):
                self.assertIs(binding, old_binding)
                self.active_registry.retire(running_job.job_id, old_binding)
                replacement = TurnBinding("profile", "thread", "replacement")
                self.active_registry.publish(running_job.job_id, replacement)
                self.active_registry.retire(running_job.job_id, replacement)
                return TurnInterruptResult(
                    TurnInterruptStatus.CONFIRMED,
                    binding,
                    TurnTerminalResult(binding, TurnTerminalStatus.FAILED, ()),
                )

            async def wait_turn(inner_self, binding):
                raise AssertionError("confirmed interrupt must not collect again")

        interrupt = DialogueInterruptService(
            self.storage,
            server_id="server",
            active_turn_registry=self.active_registry,
            turn_lifecycle=TransientReplacementLifecycle(),
            now_ms=lambda: 20,
        )
        lifecycle = FakeDeleteLifecycle()
        with self.assertRaises(DialogueDeleteError) as raised:
            await self.delete_service(lifecycle, interrupt=interrupt).delete(
                DialogueDeleteRequest("dialogue", running_dialogue.version)
            )
        self.assertEqual("INVARIANT", str(raised.exception))
        self.assertEqual([], lifecycle.calls)

        durable_dialogue = await DialogueRepository(self.storage).get_live()
        durable_job = await TurnJobRepository(self.storage).get(running_job.job_id)
        self.assertEqual(DialogueState.IDLE, durable_dialogue.state)
        self.assertEqual(TurnJobState.FAILED, durable_job.state)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("dialogue"))
        self.assertEqual({}, self.active_registry._entries)
        self.assertEqual({}, self.active_registry._watches)

    async def test_running_delete_rejects_every_mismatched_definitive_interrupt_result(self):
        mutations = (
            ("job_id", lambda job, dialogue: replace(job, job_id="other-job")),
            ("server_id", lambda job, dialogue: replace(job, server_id="other-server")),
            ("profile_id", lambda job, dialogue: replace(job, profile_id="other-profile")),
            ("thread_id", lambda job, dialogue: replace(job, thread_id="other-thread")),
            ("codex_turn_id", lambda job, dialogue: replace(job, codex_turn_id="other-turn")),
            ("state", lambda job, dialogue: replace(job, state=TurnJobState.UNKNOWN)),
            ("error", lambda job, dialogue: replace(job, error_class="WRONG_ERROR")),
            ("version", lambda job, dialogue: replace(job, version=job.version + 9)),
            ("dialogue_thread", lambda job, dialogue: (job, replace(dialogue, thread_id="other-thread"))),
            ("dialogue_profile", lambda job, dialogue: (job, replace(dialogue, profile_id="other-profile"))),
            ("dialogue_server", lambda job, dialogue: (job, replace(dialogue, server_id="other-server"))),
            ("dialogue_version", lambda job, dialogue: (job, replace(dialogue, version=dialogue.version + 9))),
        )
        for name, mutate in mutations:
            await self.reset_storage()
            _, running_dialogue, running_job = await self.seed_running()
            terminal_job = replace(
                running_job,
                state=TurnJobState.CODEX_COMPLETED,
                version=running_job.version + 1,
                error_class=None,
                updated_at_ms=running_job.updated_at_ms + 1,
            )
            terminal_dialogue = replace(
                running_dialogue,
                state=DialogueState.IDLE,
                version=running_dialogue.version + 2,
                updated_at_ms=running_dialogue.updated_at_ms + 2,
                last_error_class=None,
            )
            mutated = mutate(terminal_job, terminal_dialogue)
            if isinstance(mutated, tuple):
                terminal_job, terminal_dialogue = mutated
            else:
                terminal_job = mutated
            interrupt = FakeInterruptService(
                DialogueInterruptStatus.CONFIRMED,
                dialogue=terminal_dialogue,
                job=terminal_job,
            )
            lifecycle = FakeDeleteLifecycle()
            with self.subTest(mismatch=name):
                with self.assertRaises(DialogueDeleteError) as raised:
                    await self.delete_service(lifecycle, interrupt=interrupt).delete(
                        DialogueDeleteRequest("dialogue", running_dialogue.version)
                    )
                self.assertEqual("INVARIANT", str(raised.exception))
                self.assertEqual([], lifecycle.calls)

    async def test_synthetic_p34_v_plus_3_definitive_results_are_not_delete_authority(self):
        for status in (DialogueInterruptStatus.CONFIRMED, DialogueInterruptStatus.RECONCILED):
            await self.reset_storage()
            _, running_dialogue, running_job = await self.seed_running()
            terminal_job = replace(
                running_job,
                state=TurnJobState.FAILED,
                version=running_job.version + 1,
                error_class="CODEX_TURN_FAILED",
                updated_at_ms=running_job.updated_at_ms + 1,
            )
            terminal_dialogue = replace(
                running_dialogue,
                state=DialogueState.IDLE,
                version=running_dialogue.version + 3,
                updated_at_ms=running_dialogue.updated_at_ms + 3,
                last_error_class=None,
            )
            interrupt = FakeInterruptService(
                status, dialogue=terminal_dialogue, job=terminal_job
            )
            lifecycle = FakeDeleteLifecycle()
            with self.subTest(status=status.value):
                with self.assertRaises(DialogueDeleteError) as raised:
                    await self.delete_service(lifecycle, interrupt=interrupt).delete(
                        DialogueDeleteRequest("dialogue", running_dialogue.version)
                    )
                self.assertEqual("INVARIANT", str(raised.exception))
                self.assertEqual([], lifecycle.calls)

    async def test_canonical_dialogue_matrix_rejects_schema_valid_corruption_everywhere(self):
        async def make_creating(mutate):
            dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
                dialogue_id="dialogue", server_id="server", profile_id="profile"
            )
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        async def make_create_unknown(mutate):
            dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
                dialogue_id="dialogue", server_id="server", profile_id="profile"
            )
            dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).mark_create_unknown(
                dialogue_id="dialogue", expected_version=dialogue.version,
                error_class="CODEX_AMBIGUOUS",
            )
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        async def make_unbound_error(mutate):
            dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
                dialogue_id="dialogue", server_id="server", profile_id="profile"
            )
            await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
                update_id=55, job_id="job", source_chat_id=-1, source_message_id=1,
                dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id=None,
                model_id="model", reasoning_effort="high", input_payload_id="input",
                input_content=b"input", input_expires_at_ms=1000,
            )
            dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).mark_create_error(
                dialogue_id="dialogue", expected_version=dialogue.version,
                error_class="CODEX_PROCESS",
            )
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        async def make_idle(mutate):
            dialogue = await self.seed_idle()
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        async def make_running(mutate):
            _, dialogue, _ = await self.seed_running()
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        async def make_turn_unknown(mutate):
            _, dialogue, job = await self.seed_running()
            def terminalize(connection):
                connection.execute(
                    "UPDATE turn_jobs SET state = 'UNKNOWN', error_class = 'CODEX_AMBIGUOUS' "
                    "WHERE job_id = ?", (job.job_id,)
                )
                connection.execute(
                    "UPDATE dialogues SET state = 'TURN_UNKNOWN', last_error_class = NULL "
                    "WHERE dialogue_id = 'dialogue'"
                )
                mutate(connection)
            await self.storage.write(terminalize)
            return dialogue

        async def make_delete_unknown(mutate):
            dialogue = await self.seed_idle()
            pending = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
                dialogue_id="dialogue", expected_version=dialogue.version
            )
            deleting = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_deleting(
                dialogue_id="dialogue", expected_version=pending.version
            )
            dialogue = await DeletionRepository(self.storage, now_ms=lambda: 1).mark_delete_unknown(
                dialogue_id="dialogue", expected_version=deleting.version,
                error_class="DELETE_UNKNOWN",
            )
            await self.storage.write(lambda c: (mutate(c), None)[1])
            return dialogue

        cases = (
            ("creating_thread", make_creating,
             lambda c: c.execute("UPDATE dialogues SET thread_id = 'thread'")),
            ("create_unknown_thread", make_create_unknown,
             lambda c: c.execute("UPDATE dialogues SET thread_id = 'thread'")),
            ("creating_error", make_creating,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'CODEX_PROCESS'")),
            ("create_unknown_error", make_create_unknown,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
            ("unbound_error_thread", make_unbound_error,
             lambda c: c.execute("UPDATE dialogues SET thread_id = 'thread'")),
            ("unbound_error_class", make_unbound_error,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
            ("idle_error", make_idle,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
            ("running_error", make_running,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
            ("turn_unknown_missing_error", make_turn_unknown, lambda c: None),
            ("turn_unknown_wrong_error", make_turn_unknown,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
            ("delete_unknown_error", make_delete_unknown,
             lambda c: c.execute("UPDATE dialogues SET last_error_class = 'WRONG_ERROR'")),
        )
        for name, maker, mutate in cases:
            await self.reset_storage()
            await maker(mutate)
            dialogue_rows = await self.storage.read(
                lambda c: [tuple(row) for row in c.execute(
                    "SELECT state, version, last_error_class FROM dialogues"
                ).fetchall()]
            )
            job_count = await self.storage.read(
                lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]
            )
            raw = (dialogue_rows, job_count)
            with self.subTest(corruption=name):
                with self.assertRaises(DialogueRecoveryError) as recovery_error:
                    await DialogueRecoveryService(
                        self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))
                    ).recover_startup()
                self.assertEqual("INVARIANT", str(recovery_error.exception))
                current_version = raw[0][0][1]
                lifecycle = FakeDeleteLifecycle()
                with self.assertRaises(DialogueDeleteError) as delete_error:
                    await self.delete_service(
                        lifecycle, registry=getattr(self, "active_registry", None)
                    ).delete(DialogueDeleteRequest("dialogue", current_version))
                self.assertEqual("INVARIANT", str(delete_error.exception))
                self.assertNotIn("PRIVATE", repr(recovery_error.exception))
                self.assertNotIn("PRIVATE", repr(delete_error.exception))
                self.assertEqual([], lifecycle.calls)
                after = (
                    await self.storage.read(
                        lambda c: [tuple(row) for row in c.execute(
                            "SELECT state, version, last_error_class FROM dialogues"
                        ).fetchall()]
                    ),
                    await self.storage.read(
                        lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]
                    ),
                )
                self.assertEqual(raw, after)

    async def test_post_confirmed_expiry_failure_is_internal_and_retains_deleting_evidence(self):
        current = await self.seed_idle()
        admitted = await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
            update_id=77, job_id="job", source_chat_id=-1, source_message_id=1,
            dialogue_id="dialogue", server_id="server", profile_id="profile", thread_id="thread",
            model_id="model", reasoning_effort="high", input_payload_id="input",
            input_content=b"input", input_expires_at_ms=1000,
        )
        recovered = await DialogueRecoveryService(self.storage, now_ms=lambda: 2).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.PRE_EFFECT_FAILED, recovered.status)
        clock_values = iter((10, 20))
        def failing_clock():
            try:
                return next(clock_values)
            except StopIteration:
                raise RuntimeError("PRIVATE_POST_CONFIRMED_STORAGE_FAILURE")
        lifecycle = FakeDeleteLifecycle()
        with self.assertRaises(DialogueDeleteError) as raised:
            await self.delete_service(
                lifecycle, clock=failing_clock
            ).delete(DialogueDeleteRequest("dialogue", current.version))
        self.assertEqual("STORAGE", str(raised.exception))
        self.assertEqual(1, len(lifecycle.calls))
        deleting = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETING, deleting.state)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("dialogue"))
        self.assertIsNotNone(await TurnJobRepository(self.storage).get(admitted.job.job_id))
        self.assertIsNotNone(await TransientPayloadRepository(self.storage).get_input_for_job(admitted.job.job_id))
        recovered_again = await DialogueRecoveryService(self.storage, now_ms=lambda: 999).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.DELETE_MARKED_UNKNOWN, recovered_again.status)
        self.assertEqual(1, len(lifecycle.calls))
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION,
                         (await DialogueRecoveryService(self.storage).recover_startup()).status)

    async def test_p34_invalid_argument_is_p35_invariant_and_never_deletes(self):
        _, running_dialogue, _ = await self.seed_running()

        class InvalidInterrupt:
            async def interrupt(self, request):
                from codex_control.application import DialogueInterruptError
                raise DialogueInterruptError("INVALID_ARGUMENT")

        lifecycle = FakeDeleteLifecycle()
        with self.assertRaises(DialogueDeleteError) as raised:
            await self.delete_service(lifecycle, interrupt=InvalidInterrupt()).delete(
                DialogueDeleteRequest("dialogue", running_dialogue.version)
            )
        self.assertEqual("INVARIANT", str(raised.exception))
        self.assertEqual([], lifecycle.calls)

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

    async def test_creating_with_admitted_received_recovers_once_and_reopens_no_action(self):
        dialogue = await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
            dialogue_id="creating-dialogue", server_id="server", profile_id="profile"
        )
        admitted = await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
            update_id=43, job_id="creating-job", source_chat_id=-1, source_message_id=1,
            dialogue_id=dialogue.dialogue_id, server_id="server", profile_id="profile", thread_id=None,
            model_id="model", reasoning_effort="high", input_payload_id="creating-input",
            input_content=b"first", input_expires_at_ms=1000,
        )
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: 10)
        marked = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.CREATE_MARKED_UNKNOWN, marked.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, marked.dialogue.state)
        self.assertEqual(admitted.job, marked.job)
        repeated = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, repeated.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, repeated.dialogue.state)
        self.assertEqual(admitted.job, repeated.job)
        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        reopened = await DialogueRecoveryService(self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, reopened.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, reopened.dialogue.state)
        self.assertEqual(TurnJobState.RECEIVED, reopened.job.state)

    async def test_real_p32_create_unknown_received_is_no_action_repeat_and_restart_safe(self):
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        thread = CreationThread(ThreadOperationStatus.START_UNKNOWN)
        turns = CreationTurns()
        result = await self.creation_service(thread, turns).execute(
            ExistingDialoguePromptRequest(41, -1, 41, "first")
        )
        self.assertEqual("UNKNOWN", result.status.value)
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertEqual((DialogueState.CREATE_UNKNOWN, None), (dialogue.state, dialogue.thread_id))
        ingress = await IngressUpdateRepository(self.storage).get(41)
        job = await TurnJobRepository(self.storage).get(ingress.job_id)
        payload = await TransientPayloadRepository(self.storage).get_input_for_job(job.job_id)
        self.assertEqual((TurnJobState.RECEIVED, None, None, None),
                         (job.state, job.thread_id, job.codex_turn_id, job.error_class))
        self.assertEqual(job.job_id, ingress.job_id)
        self.assertEqual(b"first", payload.content)
        self.assertEqual([], turns.start_calls)

        clock_calls = []
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: clock_calls.append(1) or 50)
        first = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, first.status)
        self.assertEqual(dialogue, first.dialogue)
        self.assertEqual(job, first.job)
        self.assertEqual([], clock_calls)
        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        reopened = await DialogueRecoveryService(self.storage, now_ms=lambda: clock_calls.append(1) or 60).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, reopened.status)
        self.assertEqual(DialogueState.CREATE_UNKNOWN, reopened.dialogue.state)
        self.assertEqual([], clock_calls)
        self.assertEqual(1, len(thread.calls))

    async def test_real_p32_error_received_is_no_action_and_restart_safe(self):
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        thread = CreationThread(ThreadOperationStatus.START_REJECTED)
        turns = CreationTurns()
        result = await self.creation_service(thread, turns).execute(
            ExistingDialoguePromptRequest(42, -1, 42, "first")
        )
        self.assertEqual("FAILED", result.status.value)
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertEqual((DialogueState.ERROR, None), (dialogue.state, dialogue.thread_id))
        ingress = await IngressUpdateRepository(self.storage).get(42)
        job = await TurnJobRepository(self.storage).get(ingress.job_id)
        self.assertEqual((TurnJobState.RECEIVED, None, None, None),
                         (job.state, job.thread_id, job.codex_turn_id, job.error_class))
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock")))
        first = await recovery.recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, first.status)
        self.assertEqual(dialogue, first.dialogue)
        await self.storage.close()
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        reopened = await DialogueRecoveryService(self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, reopened.status)
        self.assertEqual(DialogueState.ERROR, reopened.dialogue.state)

    async def test_creation_family_corruption_variants_fail_closed(self):
        variants = (
            ("claimed", lambda c, job: c.execute("UPDATE turn_jobs SET state = 'CLAIMED' WHERE job_id = ?", (job.job_id,))),
            ("starting", lambda c, job: c.execute("UPDATE turn_jobs SET state = 'CODEX_STARTING' WHERE job_id = ?", (job.job_id,))),
            ("thread", lambda c, job: c.execute("UPDATE turn_jobs SET thread_id = 'thread' WHERE job_id = ?", (job.job_id,))),
            ("turn", lambda c, job: c.execute("UPDATE turn_jobs SET codex_turn_id = 'turn' WHERE job_id = ?", (job.job_id,))),
            ("job_ingress", lambda c, job: c.execute("UPDATE ingress_updates SET disposition = 'JOB:other' WHERE update_id = ?", (job.telegram_update_id,))),
            ("input", lambda c, job: c.execute("DELETE FROM transient_payloads WHERE job_id = ?", (job.job_id,))),
            ("multiple", lambda c, job: c.execute(
                "INSERT INTO turn_jobs (job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                "SELECT 'other-job', telegram_update_id + 100, source_chat_id, source_message_id + 100, dialogue_id, server_id, profile_id, NULL, model_id, reasoning_effort, input_sha256, NULL, 'RECEIVED', 0, created_at_ms, updated_at_ms, NULL FROM turn_jobs WHERE job_id = ?",
                (job.job_id,),
            )),
        )
        for name, mutate in variants:
            await self.reset_storage()
            await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
                profile_id="profile", model_id="model", reasoning_effort="high"
            )
            thread = CreationThread(ThreadOperationStatus.START_UNKNOWN)
            await self.creation_service(thread, CreationTurns()).execute(
                ExistingDialoguePromptRequest(100 + len(name), -1, 100 + len(name), "first")
            )
            ingress = await IngressUpdateRepository(self.storage).get(100 + len(name))
            job = await TurnJobRepository(self.storage).get(ingress.job_id)
            await self.storage.write(lambda c: (mutate(c, job), None)[1])
            with self.subTest(corruption=name):
                with self.assertRaises(DialogueRecoveryError) as raised:
                    await DialogueRecoveryService(self.storage, now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).recover_startup()
                self.assertEqual("INVARIANT", str(raised.exception))

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
