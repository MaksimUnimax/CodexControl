import asyncio
import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.adapters.codex.turn_lifecycle import (
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.adapters.telegram import PrivateCommand, TelegramPrivateDialoguePanelRenderer
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueDeleteService,
    DialogueDeleteRequest,
    DialogueDeleteResult,
    DialogueDeleteReason,
    DialogueDeleteStatus,
    DialogueInterruptService,
    DialogueInterruptResult,
    DialogueInterruptReason,
    DialogueInterruptStatus,
    PrivateCallbackRequest,
    PrivateDialogueError,
    PrivateDialogueErrorCategory,
    PrivateDialogueManagementService,
    PrivateDialogueOpenRequest,
    PrivateDialogueReason,
    PrivateDialogueStatus,
    PrivateSettingsManagementService,
    PrivateCommandRequest,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    InterruptCoordinationRepository,
    PrivateManagementRepository,
    PrivateCallbackActionSpec,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)
from codex_control.storage.application_recovery import ApplicationRecoveryRepository
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor


class Clock:
    def __init__(self, value=1000):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


class InterruptLifecycle:
    def __init__(self):
        self.interrupt_calls = []
        self.wait_calls = []

    async def interrupt_turn(self, binding):
        self.interrupt_calls.append(binding)
        terminal = TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())
        return TurnInterruptResult(TurnInterruptStatus.CONFIRMED, binding, terminal)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        return TurnTerminalResult(binding, TurnTerminalStatus.COMPLETED, ())


class DeleteLifecycle:
    def __init__(self):
        self.calls = []

    async def delete(self, *, binding):
        self.calls.append(binding)
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class PassiveService:
    def __init__(self):
        self.calls = []

    async def interrupt(self, request):
        self.calls.append(request)
        raise AssertionError("unexpected interrupt")

    async def delete(self, request):
        self.calls.append(request)
        raise AssertionError("unexpected delete")


class MappingDeleteService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def delete(self, request):
        self.calls.append(request)
        return self.result


class MappingInterruptService:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def interrupt(self, request):
        self.calls.append(request)
        return self.result


class BlockingDeleteService:
    def __init__(self, result):
        self.result = result
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = []

    async def delete(self, request):
        self.calls.append(request)
        self.entered.set()
        await self.release.wait()
        return self.result


class BlockingInterruptService:
    def __init__(self):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = []

    async def interrupt(self, request):
        self.calls.append(request)
        self.entered.set()
        await self.release.wait()


class Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id,
            1,
            (CodexModelDescriptor("model-a", "wire", "Model A", ("high",), "high", True, False),),
            0.0,
            1.0,
        )


class PrivateDialogueControlIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "controller.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)
        self.clock = Clock()
        self.token_number = 0

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def token_factory(self):
        self.token_number += 1
        return f"{self.token_number:032d}"

    async def seed_idle(self, dialogue_id="dialogue"):
        repo = DialogueRepository(self.storage, now_ms=lambda: 1)
        await repo.create_intent(dialogue_id=dialogue_id, server_id="server-80", profile_id="profile-a")
        return await repo.confirm_created(dialogue_id=dialogue_id, expected_version=0, thread_id="raw-thread-id")

    async def seed_running(self, stage="running"):
        current = await self.seed_idle()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: 1)
        admitted = await jobs.claim_ingress(
            update_id=1,
            job_id="raw-job-id",
            source_chat_id=-7,
            source_message_id=9,
            dialogue_id=current.dialogue_id,
            server_id="server-80",
            profile_id="profile-a",
            thread_id="raw-thread-id",
            model_id="model-a",
            reasoning_effort="high",
            input_payload_id="input-1",
            input_content=b"input",
            input_expires_at_ms=100000,
        )
        current = await DialogueRepository(self.storage).get_live()
        claimed = await jobs.claim_turn(
            job_id="raw-job-id",
            expected_job_version=admitted.job.version,
            expected_dialogue_version=current.version,
            thread_id="raw-thread-id",
        )
        if stage == "claimed":
            return claimed, None, None
        starting = await jobs.mark_codex_starting(job_id="raw-job-id", expected_version=claimed.job.version)
        if stage == "starting":
            return starting, None, None
        running = await jobs.mark_codex_running(
            job_id="raw-job-id", expected_version=starting.version, codex_turn_id="raw-turn-id"
        )
        registry = ActiveTurnRegistry()
        binding = TurnBinding("profile-a", "raw-thread-id", "raw-turn-id")
        registry.publish("raw-job-id", binding)
        return running, registry, binding

    async def clear_state(self):
        def clear(connection):
            for table in (
                "delivery_segments", "approvals", "transient_payloads", "turn_jobs",
                "ingress_updates", "callback_actions", "errors", "dialogues",
                "deletion_tombstones",
            ):
                connection.execute(f"DELETE FROM {table}")
        await self.storage.write(clear)

    def p42(self, interrupt, delete, *, mode_provider=None, token_factory=None):
        return PrivateDialogueManagementService(
            self.storage,
            server_id="server-80",
            server_display_name="Server 80",
            operator_user_id=7,
            interrupt_service=interrupt,
            delete_service=delete,
            mode_provider=mode_provider,
            now_ms=self.clock,
            token_factory=token_factory or self.token_factory,
        )

    async def action_token(self, panel, action):
        for row in panel.rows:
            token = row[0].callback_data[4:]
            stored = await self.storage.read(
                lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
                    "SELECT action FROM callback_actions WHERE token_hash_sha256 = ?", (h,)
                ).fetchone()[0]
            )
            if stored == action:
                return token
        raise AssertionError(action)

    async def panel_actions(self, panel):
        actions = []
        for row in panel.rows:
            token = row[0].callback_data[4:]
            action = await self.storage.read(
                lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
                    "SELECT action FROM callback_actions WHERE token_hash_sha256 = ?", (h,)
                ).fetchone()[0]
            )
            actions.append(action)
        return set(actions)

    async def test_no_dialogue_is_static_and_has_zero_callback_authority(self):
        service = self.p42(PassiveService(), PassiveService())
        result = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertEqual((PrivateDialogueStatus.RENDERED, PrivateDialogueReason.NO_DIALOGUE), (result.status, result.reason))
        self.assertIsNotNone(result.panel)
        self.assertEqual((), result.panel.rows)
        self.assertIn("Server: Server 80", result.panel.text)
        self.assertEqual(0, self.token_number)
        self.assertEqual(0, self.clock.calls)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))

    async def test_not_found_expired_and_replay_are_effect_free(self):
        service = self.p42(PassiveService(), PassiveService())
        missing = await service.handle_callback(PrivateCallbackRequest(40, 7, 7, "query", "Z" * 32))
        self.assertEqual((PrivateDialogueStatus.STALE, PrivateDialogueReason.CALLBACK_NOT_FOUND), (missing.status, missing.reason))
        await self.seed_idle()
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(opened.panel, "P42_REFRESH")
        self.clock.value = 901000
        expired = await service.handle_callback(PrivateCallbackRequest(41, 7, 7, "query", token))
        replay = await service.handle_callback(PrivateCallbackRequest(42, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.EXPIRED, expired.status)
        self.assertEqual(PrivateDialogueStatus.ALREADY_USED, replay.status)

    async def test_cancellation_after_claim_does_not_retry_effect(self):
        await self.seed_running()
        blocker = BlockingInterruptService()
        service = self.p42(blocker, PassiveService())
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(opened.panel, "P42_INTERRUPT")
        task = asyncio.create_task(service.handle_callback(PrivateCallbackRequest(43, 7, 7, "query", token)))
        await blocker.entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        replay = await service.handle_callback(PrivateCallbackRequest(44, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.ALREADY_USED, replay.status)
        self.assertEqual(1, len(blocker.calls))

    async def test_peek_is_read_only_and_deleting_states_have_refresh_only(self):
        current = await self.seed_idle()
        p42 = self.p42(PassiveService(), PassiveService())
        opened = await p42.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(opened.panel, "P42_REFRESH")
        self.clock.calls = 0
        record = await PrivateManagementRepository(self.storage, now_ms=self.clock).peek_callback(
            hashlib.sha256(token.encode()).hexdigest()
        )
        self.assertEqual("P42_REFRESH", record.action)
        self.assertEqual(0, self.clock.calls)
        pending = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        deleting = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_deleting(
            dialogue_id="dialogue", expected_version=pending.version
        )
        deleting_panel = (await p42.open_status(PrivateDialogueOpenRequest(7, 7))).panel
        self.assertEqual({"P42_REFRESH"}, await self.panel_actions(deleting_panel))
        await DeletionRepository(self.storage, now_ms=lambda: 1).mark_delete_unknown(
            dialogue_id="dialogue", expected_version=deleting.version, error_class="DELETE_UNKNOWN"
        )
        unknown_panel = (await p42.open_status(PrivateDialogueOpenRequest(7, 7))).panel
        self.assertEqual({"P42_REFRESH"}, await self.panel_actions(unknown_panel))

    async def test_canonical_schema_valid_noncanonical_relation_is_invariant_and_redacted(self):
        await self.seed_idle()
        await self.storage.write(lambda c: c.execute(
            "UPDATE dialogues SET state = 'TURN_RUNNING', version = version + 1 WHERE dialogue_id = 'dialogue'"
        ).rowcount)
        service = self.p42(PassiveService(), PassiveService())
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)
        self.assertNotIn("raw-thread-id", str(raised.exception) + repr(raised.exception))

    async def test_action_matrix_core_states_and_redacted_render(self):
        await self.seed_idle()
        service = self.p42(PassiveService(), PassiveService())
        result = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertEqual({"P42_REFRESH", "P42_BEGIN_DELETE"}, {
            (await self.storage.read(lambda c, h=hashlib.sha256(row[0].callback_data[4:].encode()).hexdigest(): c.execute("SELECT action FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))
            for row in result.panel.rows
        })
        rendered = TelegramPrivateDialoguePanelRenderer().render(result.panel)
        combined = repr(result) + repr(rendered)
        self.assertNotIn("raw-thread-id", repr(result))
        self.assertNotIn("raw-job-id", repr(result))
        self.assertNotIn("raw-turn-id", repr(result))
        self.assertNotIn("CODEX_HOME", combined)
        self.assertNotIn("parse_mode", combined)

    async def test_table_driven_canonical_status_action_matrix(self):
        expected = {
            "NO_DIALOGUE": set(),
            "CREATING": {"P42_REFRESH"},
            "CREATE_UNKNOWN": {"P42_REFRESH"},
            "ERROR": {"P42_REFRESH"},
            "IDLE": {"P42_REFRESH", "P42_BEGIN_DELETE"},
            "IDLE_RECEIVED": {"P42_REFRESH"},
            "TURN_RUNNING_CLAIMED": {"P42_REFRESH"},
            "TURN_RUNNING_CODEX_STARTING": {"P42_REFRESH"},
            "TURN_RUNNING_CODEX_RUNNING": {"P42_REFRESH", "P42_INTERRUPT", "P42_BEGIN_DELETE"},
            "INTERRUPTING": {"P42_REFRESH"},
            "TURN_UNKNOWN": {"P42_REFRESH"},
            "DELETE_PENDING": {"P42_REFRESH", "P42_BEGIN_DELETE"},
            "DELETING": {"P42_REFRESH"},
            "DELETE_CONFIRMED_PENDING_STORAGE": {"P42_REFRESH"},
            "DELETE_UNKNOWN": {"P42_REFRESH"},
        }
        for name, wanted in expected.items():
            await self.clear_state()
            if name == "NO_DIALOGUE":
                pass
            elif name == "CREATING":
                await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
                    dialogue_id="dialogue", server_id="server-80", profile_id="profile-a"
                )
            elif name == "CREATE_UNKNOWN":
                repo = DialogueRepository(self.storage, now_ms=lambda: 1)
                await repo.create_intent(dialogue_id="dialogue", server_id="server-80", profile_id="profile-a")
                await repo.mark_create_unknown(dialogue_id="dialogue", expected_version=0, error_class="CODEX_AMBIGUOUS")
            elif name == "ERROR":
                repo = DialogueRepository(self.storage, now_ms=lambda: 1)
                await repo.create_intent(dialogue_id="dialogue", server_id="server-80", profile_id="profile-a")
                await repo.mark_create_error(dialogue_id="dialogue", expected_version=0, error_class="CODEX_THREAD_FAILED")
            elif name == "IDLE":
                await self.seed_idle()
            elif name == "IDLE_RECEIVED":
                current = await self.seed_idle()
                await TurnJobRepository(self.storage, now_ms=lambda: 1).claim_ingress(
                    update_id=99, job_id="raw-job-id", source_chat_id=-7, source_message_id=9,
                    dialogue_id=current.dialogue_id, server_id="server-80", profile_id="profile-a",
                    thread_id="raw-thread-id", model_id="model-a", reasoning_effort="high",
                    input_payload_id="input-99", input_content=b"input", input_expires_at_ms=100000,
                )
            elif name.startswith("TURN_RUNNING_"):
                stage = {"TURN_RUNNING_CLAIMED": "claimed", "TURN_RUNNING_CODEX_STARTING": "starting"}.get(name, "running")
                await self.seed_running(stage)
                if name == "INTERRUPTING":
                    raise AssertionError("unreachable")
            elif name == "INTERRUPTING":
                job, _, _ = await self.seed_running()
                dialogue = await DialogueRepository(self.storage).get_live()
                await InterruptCoordinationRepository(self.storage, now_ms=lambda: 1).claim_interrupt(
                    dialogue_id=dialogue.dialogue_id, job_id=job.job_id,
                    expected_dialogue_version=dialogue.version, expected_job_version=job.version,
                )
            elif name == "TURN_UNKNOWN":
                job, _, _ = await self.seed_running()
                dialogue = await DialogueRepository(self.storage).get_live()
                await TurnJobRepository(self.storage, now_ms=lambda: 1).finish_codex(
                    job_id=job.job_id, expected_job_version=job.version,
                    expected_dialogue_version=dialogue.version,
                    outcome=TurnTerminalOutcome.UNKNOWN, error_class="CODEX_AMBIGUOUS",
                )
            elif name == "DELETE_PENDING":
                current = await self.seed_idle()
                await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
                    dialogue_id=current.dialogue_id, expected_version=current.version
                )
            elif name in ("DELETING", "DELETE_CONFIRMED_PENDING_STORAGE", "DELETE_UNKNOWN"):
                current = await self.seed_idle()
                pending = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
                    dialogue_id=current.dialogue_id, expected_version=current.version
                )
                deleting = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_deleting(
                    dialogue_id=current.dialogue_id, expected_version=pending.version
                )
                if name == "DELETE_CONFIRMED_PENDING_STORAGE":
                    await DeletionRepository(self.storage, now_ms=lambda: 1).mark_delete_confirmed_pending_storage(
                        dialogue_id=current.dialogue_id, expected_version=deleting.version
                    )
                elif name == "DELETE_UNKNOWN":
                    await DeletionRepository(self.storage, now_ms=lambda: 1).mark_delete_unknown(
                        dialogue_id=current.dialogue_id, expected_version=deleting.version,
                        error_class="DELETE_UNKNOWN",
                    )
            snapshot = await ApplicationRecoveryRepository(self.storage, now_ms=lambda: 1).inspect()
            service = self.p42(PassiveService(), PassiveService())
            result = await service.open_status(PrivateDialogueOpenRequest(7, 7))
            self.assertEqual(wanted, set() if result.panel is None else await self.panel_actions(result.panel), name)

    async def test_real_p34_interrupt_is_one_call_and_exact_request(self):
        running, registry, binding = await self.seed_running()
        lifecycle = InterruptLifecycle()
        p34 = DialogueInterruptService(
            self.storage,
            server_id="server-80",
            active_turn_registry=registry,
            turn_lifecycle=lifecycle,
            now_ms=lambda: 1000,
            id_factory=lambda kind: "p34-output",
        )
        delete = PassiveService()
        service = self.p42(p34, delete)
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(opened.panel, "P42_INTERRUPT")
        result = await service.handle_callback(PrivateCallbackRequest(2, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.INTERRUPTED, result.status)
        self.assertIsNone(result.panel)
        self.assertEqual(1, len(lifecycle.interrupt_calls))
        self.assertIs(binding, lifecycle.interrupt_calls[0])
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.IDLE, current.state)
        self.assertEqual([], delete.calls)

    async def test_stale_interrupt_is_consumed_without_effect(self):
        running, registry, binding = await self.seed_running()
        lifecycle = InterruptLifecycle()
        p34 = DialogueInterruptService(
            self.storage,
            server_id="server-80",
            active_turn_registry=registry,
            turn_lifecycle=lifecycle,
            now_ms=lambda: 1000,
        )
        service = self.p42(p34, PassiveService())
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(opened.panel, "P42_INTERRUPT")
        await self.storage.write(lambda c: (
            c.execute(
                "UPDATE dialogues SET state = 'INTERRUPTING', version = version + 1 WHERE dialogue_id = 'dialogue'"
            ).rowcount
        ))
        result = await service.handle_callback(PrivateCallbackRequest(8, 7, 7, "query", token))
        self.assertEqual((PrivateDialogueStatus.STALE, PrivateDialogueReason.STALE_ACTION), (result.status, result.reason))
        self.assertEqual([], lifecycle.interrupt_calls)
        replay = await service.handle_callback(PrivateCallbackRequest(9, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.ALREADY_USED, replay.status)

    async def test_callback_collision_and_duplicate_generation_are_atomic_without_retry(self):
        current = await self.seed_idle()
        collision = "C" * 32
        collision_hash = hashlib.sha256(collision.encode()).hexdigest()
        await PrivateManagementRepository(self.storage, now_ms=self.clock).create_callback_batch(
            actions=(
                # This is an existing durable row owned by another private surface.
                PrivateCallbackActionSpec(
                    collision_hash, "OPEN_ROOT", "panel", "0", current.version, current.state.value, 7, 7
                ),
            ),
            created_at_ms=1000,
            expires_at_ms=901000,
        )
        service = self.p42(PassiveService(), PassiveService(), token_factory=lambda: collision)
        with self.assertRaises(Exception) as raised:
            await service.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertEqual("INVARIANT", str(raised.exception))
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        duplicate = self.p42(PassiveService(), PassiveService(), token_factory=lambda: "D" * 32)
        with self.assertRaises(Exception):
            await duplicate.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))

    async def test_idle_delete_is_always_two_step_and_real_p35_deletes_once(self):
        await self.seed_idle()
        delete_lifecycle = DeleteLifecycle()
        p34 = PassiveService()
        p35 = DialogueDeleteService(
            self.storage,
            server_id="server-80",
            thread_lifecycle=delete_lifecycle,
            now_ms=lambda: 1000,
        )
        service = self.p42(p34, p35)
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(opened.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(PrivateCallbackRequest(3, 7, 7, "query", begin))
        self.assertEqual(PrivateDialogueStatus.CONFIRM_REQUIRED, confirmation.status)
        self.assertEqual(0, len(delete_lifecycle.calls))
        self.assertEqual(2, len(confirmation.panel.rows))
        self.assertIn("official Codex thread deletion", confirmation.panel.text)
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        result = await service.handle_callback(PrivateCallbackRequest(4, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueStatus.CONFIRMED_PENDING_STORAGE, result.status)
        self.assertEqual(1, len(delete_lifecycle.calls))
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("dialogue"))
        replay = await service.handle_callback(PrivateCallbackRequest(5, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueStatus.ALREADY_USED, replay.status)
        self.assertEqual(1, len(delete_lifecycle.calls))

    async def test_delete_pending_continuation_and_deleting_have_no_second_authority(self):
        current = await self.seed_idle()
        await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
            dialogue_id="dialogue", expected_version=current.version
        )
        delete_lifecycle = DeleteLifecycle()
        p35 = DialogueDeleteService(
            self.storage,
            server_id="server-80",
            thread_lifecycle=delete_lifecycle,
            now_ms=lambda: 1000,
        )
        service = self.p42(PassiveService(), p35)
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        self.assertIsNotNone(await self.action_token(opened.panel, "P42_BEGIN_DELETE"))
        begin = await self.action_token(opened.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(PrivateCallbackRequest(6, 7, 7, "query", begin))
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        result = await service.handle_callback(PrivateCallbackRequest(7, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueStatus.CONFIRMED_PENDING_STORAGE, result.status)
        self.assertEqual(1, len(delete_lifecycle.calls))
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM dialogues").fetchone()[0]))

    async def test_wrong_owner_and_p41_token_are_nonconsuming(self):
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile-a", model_id="model-a", reasoning_effort="high"
        )
        p41_token_number = [0]
        def p41_token_factory():
            p41_token_number[0] += 1
            return f"{p41_token_number[0]:032d}"
        settings = PrivateSettingsManagementService(
            self.storage,
            server_id="server-80",
            server_display_name="Server 80",
            operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/not-displayed", "Profile A", "/not-displayed-state"),),
            model_catalog=Catalog(),
            now_ms=self.clock,
            token_factory=p41_token_factory,
        )
        p41_panel = await settings.handle_command(PrivateCommandRequest(20, 7, 7, PrivateCommand.MENU))
        token = p41_panel.panel.rows[0][0].callback_data[4:]
        p42 = self.p42(PassiveService(), PassiveService())
        blocked = await p42.handle_callback(PrivateCallbackRequest(21, 7, 7, "query", token))
        self.assertEqual((PrivateDialogueStatus.BLOCKED, PrivateDialogueReason.ACTION_UNAVAILABLE), (blocked.status, blocked.reason))
        consumed = await self.storage.read(lambda c: c.execute("SELECT consumed_at_ms FROM callback_actions WHERE action = 'OPEN_PROFILES'").fetchone()[0])
        self.assertIsNone(consumed)
        right = await settings.handle_callback(PrivateCallbackRequest(23, 7, 7, "query", token))
        self.assertEqual("RENDERED", right.status.value)
        wrong = await p42.handle_callback(PrivateCallbackRequest(22, 8, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.UNAUTHORIZED, wrong.status)

    async def test_running_delete_is_delegated_once_without_local_interrupt_or_registry_access(self):
        running, registry, binding = await self.seed_running()
        interrupt = PassiveService()
        from codex_control.application import DialogueDeleteResult, DialogueDeleteStatus
        delete = MappingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None))
        service = self.p42(interrupt, delete)
        opened = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(opened.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(PrivateCallbackRequest(30, 7, 7, "query", begin))
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        result = await service.handle_callback(PrivateCallbackRequest(31, 7, 7, "query", confirm))
        self.assertEqual((PrivateDialogueStatus.UNKNOWN, PrivateDialogueReason.DELETE_UNKNOWN), (result.status, result.reason))
        self.assertEqual(1, len(delete.calls))
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(
            DialogueDeleteRequest(current.dialogue_id, current.version),
            delete.calls[0],
        )
        self.assertEqual([], interrupt.calls)

    async def test_cancel_revokes_all_same_context_confirmations(self):
        await self.seed_idle()
        delete = MappingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None))
        service = self.p42(PassiveService(), delete)

        first_status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        first_begin = await self.action_token(first_status.panel, "P42_BEGIN_DELETE")
        first_confirmation = await service.handle_callback(
            PrivateCallbackRequest(50, 7, 7, "query", first_begin)
        )
        first_confirm = await self.action_token(first_confirmation.panel, "P42_CONFIRM_DELETE")
        first_cancel = await self.action_token(first_confirmation.panel, "P42_CANCEL_DELETE")

        second_status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        second_begin = await self.action_token(second_status.panel, "P42_BEGIN_DELETE")
        second_confirmation = await service.handle_callback(
            PrivateCallbackRequest(51, 7, 7, "query", second_begin)
        )
        second_confirm = await self.action_token(second_confirmation.panel, "P42_CONFIRM_DELETE")
        self.assertNotEqual(first_confirm, second_confirm)

        cancelled = await service.handle_callback(
            PrivateCallbackRequest(52, 7, 7, "query", first_cancel)
        )
        self.assertEqual(
            (PrivateDialogueStatus.RENDERED, None),
            (cancelled.status, cancelled.reason),
        )
        self.assertEqual(0, len(delete.calls))
        self.assertEqual(
            PrivateDialogueStatus.ALREADY_USED,
            (await service.handle_callback(PrivateCallbackRequest(53, 7, 7, "query", first_confirm))).status,
        )
        self.assertEqual(
            PrivateDialogueStatus.ALREADY_USED,
            (await service.handle_callback(PrivateCallbackRequest(54, 7, 7, "query", second_confirm))).status,
        )
        for token in (first_confirm, second_confirm):
            consumed, expires = await self.storage.read(
                lambda c, token_hash=hashlib.sha256(token.encode()).hexdigest(): tuple(c.execute(
                    "SELECT consumed_at_ms, expires_at_ms FROM callback_actions "
                    "WHERE token_hash_sha256 = ?",
                    (token_hash,),
                ).fetchone())
            )
            self.assertEqual(consumed, expires)

    async def test_cancel_is_repeatable_in_unchanged_idle_generation_with_expiry_sentinel(self):
        await self.seed_idle()
        delete = MappingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None))
        service = self.p42(PassiveService(), delete)

        initial = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        generation_before = await DialogueRepository(self.storage).get_live()
        first_begin = await self.action_token(initial.panel, "P42_BEGIN_DELETE")
        first_confirmation = await service.handle_callback(
            PrivateCallbackRequest(79, 7, 7, "query", first_begin)
        )
        first_confirm = await self.action_token(first_confirmation.panel, "P42_CONFIRM_DELETE")
        first_cancel = await self.action_token(first_confirmation.panel, "P42_CANCEL_DELETE")
        first_confirm_hash = hashlib.sha256(first_confirm.encode()).hexdigest()
        first_expiry = await self.storage.read(
            lambda c: c.execute(
                "SELECT expires_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
                (first_confirm_hash,),
            ).fetchone()[0]
        )

        cancelled_first = await service.handle_callback(
            PrivateCallbackRequest(80, 7, 7, "query", first_cancel)
        )
        self.assertEqual(PrivateDialogueStatus.RENDERED, cancelled_first.status)
        first_row = await self.storage.read(
            lambda c: tuple(c.execute(
                "SELECT consumed_at_ms, expires_at_ms FROM callback_actions "
                "WHERE token_hash_sha256 = ?",
                (first_confirm_hash,),
            ).fetchone())
        )
        self.assertEqual(first_expiry, first_row[1])
        self.assertEqual(first_row[0], first_row[1])
        self.assertEqual(
            PrivateDialogueStatus.ALREADY_USED,
            (await service.handle_callback(
                PrivateCallbackRequest(81, 7, 7, "query", first_confirm)
            )).status,
        )

        second_begin = await self.action_token(cancelled_first.panel, "P42_BEGIN_DELETE")
        second_confirmation = await service.handle_callback(
            PrivateCallbackRequest(82, 7, 7, "query", second_begin)
        )
        second_confirm = await self.action_token(second_confirmation.panel, "P42_CONFIRM_DELETE")
        second_cancel = await self.action_token(second_confirmation.panel, "P42_CANCEL_DELETE")
        cancelled_second = await service.handle_callback(
            PrivateCallbackRequest(83, 7, 7, "query", second_cancel)
        )
        self.assertEqual(PrivateDialogueStatus.RENDERED, cancelled_second.status)
        generation_after = await DialogueRepository(self.storage).get_live()
        self.assertEqual(
            (generation_before.dialogue_id, generation_before.version, generation_before.state),
            (generation_after.dialogue_id, generation_after.version, generation_after.state),
        )
        second_confirm_hash = hashlib.sha256(second_confirm.encode()).hexdigest()
        second_row = await self.storage.read(
            lambda c: tuple(c.execute(
                "SELECT consumed_at_ms, expires_at_ms FROM callback_actions "
                "WHERE token_hash_sha256 = ?",
                (second_confirm_hash,),
            ).fetchone())
        )
        self.assertEqual(second_row[0], second_row[1])
        self.assertEqual(
            PrivateDialogueStatus.ALREADY_USED,
            (await service.handle_callback(
                PrivateCallbackRequest(84, 7, 7, "query", second_confirm)
            )).status,
        )
        self.assertEqual(0, len(delete.calls))

    async def test_direct_revocation_ignores_old_expiry_sentinel_and_marks_new_row_at_expiry(self):
        current = await self.seed_idle()
        repository = PrivateManagementRepository(self.storage, now_ms=self.clock)
        old_token = "O" * 32
        new_token = "N" * 32
        old_hash = hashlib.sha256(old_token.encode()).hexdigest()
        new_hash = hashlib.sha256(new_token.encode()).hexdigest()
        subject_id = hashlib.sha256(
            f"{current.dialogue_id}\x00{current.state.value}\x00-\x00-".encode()
        ).hexdigest()
        await repository.create_callback_batch(
            actions=(
                PrivateCallbackActionSpec(
                    old_hash, "P42_CONFIRM_DELETE", "p42_delete", subject_id,
                    current.version, current.state.value, 7, 7,
                ),
                PrivateCallbackActionSpec(
                    new_hash, "P42_CONFIRM_DELETE", "p42_delete", subject_id,
                    current.version, current.state.value, 7, 7,
                ),
            ),
            created_at_ms=1000,
            expires_at_ms=901000,
        )
        await self.storage.write(lambda c: c.execute(
            "UPDATE callback_actions SET consumed_at_ms = expires_at_ms "
            "WHERE token_hash_sha256 = ?",
            (old_hash,),
        ).rowcount)
        self.clock.calls = 0
        result = await repository.revoke_delete_confirmations(
            subject_id=subject_id,
            expected_version=current.version,
            expected_state=current.state.value,
            authorized_user_id=7,
            authorized_chat_id=7,
            consumed_at_ms=1001,
        )
        self.assertEqual("REVOKED", result.status.value)
        self.assertEqual(1, result.revoked_count)
        self.assertEqual(0, self.clock.calls)
        rows = await self.storage.read(lambda c: tuple(
            tuple(row) for row in c.execute(
                "SELECT token_hash_sha256, consumed_at_ms, expires_at_ms "
                "FROM callback_actions WHERE subject_id = ? ORDER BY token_hash_sha256",
                (subject_id,),
            ).fetchall()
        ))
        self.assertEqual(2, len(rows))
        by_hash = {row[0]: row[1:] for row in rows}
        self.assertEqual(by_hash[old_hash][0], by_hash[old_hash][1])
        self.assertEqual(by_hash[new_hash][0], by_hash[new_hash][1])

    async def test_cancel_does_not_revoke_other_generation(self):
        current = await self.seed_idle()
        service = self.p42(PassiveService(), PassiveService())
        original_status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        original_begin = await self.action_token(original_status.panel, "P42_BEGIN_DELETE")
        original_confirmation = await service.handle_callback(
            PrivateCallbackRequest(55, 7, 7, "query", original_begin)
        )
        original_confirm = await self.action_token(original_confirmation.panel, "P42_CONFIRM_DELETE")
        original_hash = hashlib.sha256(original_confirm.encode()).hexdigest()

        pending = await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
            dialogue_id=current.dialogue_id, expected_version=current.version
        )
        current_status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        current_begin = await self.action_token(current_status.panel, "P42_BEGIN_DELETE")
        current_confirmation = await service.handle_callback(
            PrivateCallbackRequest(56, 7, 7, "query", current_begin)
        )
        current_cancel = await self.action_token(current_confirmation.panel, "P42_CANCEL_DELETE")
        cancelled = await service.handle_callback(
            PrivateCallbackRequest(57, 7, 7, "query", current_cancel)
        )
        self.assertEqual(PrivateDialogueStatus.RENDERED, cancelled.status)
        original_consumed = await self.storage.read(
            lambda c: c.execute(
                "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
                (original_hash,),
            ).fetchone()[0]
        )
        self.assertIsNone(original_consumed)
        self.assertEqual(pending.version, 2)

    async def test_confirm_claimed_before_cancel_returns_stale_without_cancel_effect(self):
        await self.seed_idle()
        delete = BlockingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None))
        service = self.p42(PassiveService(), delete)
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(status.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(
            PrivateCallbackRequest(58, 7, 7, "query", begin)
        )
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        cancel = await self.action_token(confirmation.panel, "P42_CANCEL_DELETE")
        confirm_hash = hashlib.sha256(confirm.encode()).hexdigest()

        confirm_task = asyncio.create_task(
            service.handle_callback(PrivateCallbackRequest(59, 7, 7, "query", confirm))
        )
        await delete.entered.wait()
        claimed_consumed, claimed_expires = await self.storage.read(
            lambda c: tuple(c.execute(
                "SELECT consumed_at_ms, expires_at_ms FROM callback_actions "
                "WHERE token_hash_sha256 = ?",
                (confirm_hash,),
            ).fetchone())
        )
        self.assertLess(claimed_consumed, claimed_expires)
        cancelled = await service.handle_callback(
            PrivateCallbackRequest(60, 7, 7, "query", cancel)
        )
        self.assertEqual(
            (PrivateDialogueStatus.STALE, PrivateDialogueReason.STALE_ACTION),
            (cancelled.status, cancelled.reason),
        )
        self.assertEqual(1, len(delete.calls))
        delete.release.set()
        confirmed = await confirm_task
        self.assertEqual(PrivateDialogueStatus.UNKNOWN, confirmed.status)
        self.assertEqual(1, len(delete.calls))

    async def test_expired_unclaimed_confirmation_does_not_block_cancel(self):
        await self.seed_idle()
        service = self.p42(PassiveService(), PassiveService())
        initial = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        initial_begin = await self.action_token(initial.panel, "P42_BEGIN_DELETE")
        initial_confirmation = await service.handle_callback(
            PrivateCallbackRequest(61, 7, 7, "query", initial_begin)
        )
        initial_confirm = await self.action_token(initial_confirmation.panel, "P42_CONFIRM_DELETE")
        initial_hash = hashlib.sha256(initial_confirm.encode()).hexdigest()

        self.clock.value = 901000
        fresh = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        fresh_begin = await self.action_token(fresh.panel, "P42_BEGIN_DELETE")
        fresh_confirmation = await service.handle_callback(
            PrivateCallbackRequest(62, 7, 7, "query", fresh_begin)
        )
        fresh_cancel = await self.action_token(fresh_confirmation.panel, "P42_CANCEL_DELETE")
        cancelled = await service.handle_callback(
            PrivateCallbackRequest(63, 7, 7, "query", fresh_cancel)
        )
        self.assertEqual(PrivateDialogueStatus.RENDERED, cancelled.status)
        initial_row = await self.storage.read(
            lambda c: tuple(c.execute(
                "SELECT consumed_at_ms, expires_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
                (initial_hash,),
            ).fetchone())
        )
        self.assertEqual(initial_row[0], initial_row[1])

    async def test_stale_confirm_consumes_callback_without_delete(self):
        current = await self.seed_idle()
        delete = MappingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, None, None, None))
        service = self.p42(PassiveService(), delete)
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(status.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(
            PrivateCallbackRequest(64, 7, 7, "query", begin)
        )
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        await DeletionRepository(self.storage, now_ms=lambda: 1).claim_delete_intent(
            dialogue_id=current.dialogue_id, expected_version=current.version
        )
        stale = await service.handle_callback(PrivateCallbackRequest(65, 7, 7, "query", confirm))
        self.assertEqual(
            (PrivateDialogueStatus.STALE, PrivateDialogueReason.STALE_ACTION),
            (stale.status, stale.reason),
        )
        self.assertEqual(0, len(delete.calls))
        replay = await service.handle_callback(PrivateCallbackRequest(66, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueStatus.ALREADY_USED, replay.status)

    async def test_wrong_principal_p42_token_is_unconsumed_then_right_principal_succeeds(self):
        await self.seed_idle()
        service = self.p42(PassiveService(), PassiveService())
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(status.panel, "P42_REFRESH")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        wrong = await service.handle_callback(PrivateCallbackRequest(67, 8, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.UNAUTHORIZED, wrong.status)
        self.assertIsNone(await self.storage.read(
            lambda c: c.execute(
                "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
                (token_hash,),
            ).fetchone()[0]
        ))
        right = await service.handle_callback(PrivateCallbackRequest(68, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueStatus.RENDERED, right.status)

    async def test_p34_blocked_none_is_invariant(self):
        await self.seed_running()
        service = self.p42(
            MappingInterruptService(DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, None, None, None, None)),
            PassiveService(),
        )
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(status.panel, "P42_INTERRUPT")
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.handle_callback(PrivateCallbackRequest(69, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)

    async def test_p34_blocked_stale_request_is_invariant(self):
        await self.seed_running()
        service = self.p42(
            MappingInterruptService(DialogueInterruptResult(
                DialogueInterruptStatus.BLOCKED, None, None, None, DialogueInterruptReason.STALE_REQUEST
            )),
            PassiveService(),
        )
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(status.panel, "P42_INTERRUPT")
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.handle_callback(PrivateCallbackRequest(70, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)

    async def test_p34_rejected_reason_is_invariant(self):
        await self.seed_running()
        service = self.p42(
            MappingInterruptService(DialogueInterruptResult(
                DialogueInterruptStatus.REJECTED, None, None, None, DialogueInterruptReason.JOB_NOT_RUNNING
            )),
            PassiveService(),
        )
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        token = await self.action_token(status.panel, "P42_INTERRUPT")
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.handle_callback(PrivateCallbackRequest(71, 7, 7, "query", token))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)

    async def test_p34_canonical_rejected_and_blocked_results_map_safely(self):
        for result, expected in (
            (
                DialogueInterruptResult(DialogueInterruptStatus.REJECTED, None, None, None, None),
                (PrivateDialogueStatus.BLOCKED, None),
            ),
            (
                DialogueInterruptResult(
                    DialogueInterruptStatus.BLOCKED, None, None, None,
                    DialogueInterruptReason.JOB_NOT_RUNNING,
                ),
                (PrivateDialogueStatus.BLOCKED, PrivateDialogueReason.JOB_NOT_RUNNING),
            ),
        ):
            await self.clear_state()
            await self.seed_running()
            service = self.p42(MappingInterruptService(result), PassiveService())
            status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
            token = await self.action_token(status.panel, "P42_INTERRUPT")
            mapped = await service.handle_callback(PrivateCallbackRequest(72, 7, 7, "query", token))
            self.assertEqual(expected, (mapped.status, mapped.reason))

    async def test_p35_blocked_none_is_invariant(self):
        await self.seed_idle()
        service = self.p42(
            PassiveService(),
            MappingDeleteService(DialogueDeleteResult(DialogueDeleteStatus.BLOCKED, None, None, None)),
        )
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(status.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(PrivateCallbackRequest(73, 7, 7, "query", begin))
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.handle_callback(PrivateCallbackRequest(74, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)

    async def test_p35_blocked_stale_request_is_invariant(self):
        await self.seed_idle()
        service = self.p42(
            PassiveService(),
            MappingDeleteService(DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, None, None, DialogueDeleteReason.STALE_REQUEST
            )),
        )
        status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
        begin = await self.action_token(status.panel, "P42_BEGIN_DELETE")
        confirmation = await service.handle_callback(PrivateCallbackRequest(75, 7, 7, "query", begin))
        confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
        with self.assertRaises(PrivateDialogueError) as raised:
            await service.handle_callback(PrivateCallbackRequest(76, 7, 7, "query", confirm))
        self.assertEqual(PrivateDialogueErrorCategory.INVARIANT, raised.exception.category)

    async def test_p35_canonical_blocked_and_conflict_results_map_safely(self):
        for result, expected in (
            (
                DialogueDeleteResult(
                    DialogueDeleteStatus.BLOCKED, None, None, DialogueDeleteReason.DELETE_NOT_READY
                ),
                (PrivateDialogueStatus.BLOCKED, PrivateDialogueReason.DELETE_NOT_READY),
            ),
            (
                DialogueDeleteResult(
                    DialogueDeleteStatus.CONFLICT, None, None, DialogueDeleteReason.STALE_REQUEST
                ),
                (PrivateDialogueStatus.STALE, PrivateDialogueReason.STALE_ACTION),
            ),
        ):
            await self.clear_state()
            await self.seed_idle()
            service = self.p42(PassiveService(), MappingDeleteService(result))
            status = await service.open_status(PrivateDialogueOpenRequest(7, 7))
            begin = await self.action_token(status.panel, "P42_BEGIN_DELETE")
            confirmation = await service.handle_callback(PrivateCallbackRequest(77, 7, 7, "query", begin))
            confirm = await self.action_token(confirmation.panel, "P42_CONFIRM_DELETE")
            mapped = await service.handle_callback(PrivateCallbackRequest(78, 7, 7, "query", confirm))
            self.assertEqual(expected, (mapped.status, mapped.reason))


if __name__ == "__main__":
    unittest.main()
