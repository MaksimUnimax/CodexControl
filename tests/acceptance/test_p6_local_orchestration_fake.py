import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import CodexProtocolClient, ProtocolState
from codex_control.adapters.codex.thread_lifecycle import TrustedWorkingDirectory
from codex_control.adapters.telegram import (
    PrivateCommand,
    TelegramGroupUpdateAdapter,
)
from codex_control.application import (
    ApprovalAwareTurnLifecycle,
    ApprovalDecisionSignal,
    DialogueTurnService,
    FleetControlService,
    FleetGroupRoutingService,
    FleetMember,
    FleetManifest,
    FleetStatusService,
    LocalControllerOrchestrator,
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlService,
    TurnDeliveryService,
    WorkStatusAttempt,
)
from codex_control.domain import CodexProfile, ControllerMode
from codex_control.storage import (
    ApprovalRepository,
    ControllerRuntimeRepository,
    DialogueRepository,
    SettingsRepository,
    StorageError,
    StorageErrorCategory,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
)
from codex_control.application.dialogue_recovery import DialogueRecoveryService
from codex_control.application.fleet_control import GroupInboundKind
from codex_control.application.response_delivery import (
    TelegramDeliveryEffectResult,
    TelegramDeliveryEffectStatus,
)
from tests.acceptance.test_p2_6b_support import create_completed


class _Transport:
    def __init__(self):
        self.incoming = asyncio.Queue()
        self.sent = []

    async def send(self, message):
        self.sent.append(message)
        if message.get("method") == "initialize":
            await self.incoming.put(json.dumps({
                "id": message["id"],
                "result": {
                    "userAgent": "fake",
                    "codexHome": "/synthetic",
                    "platformFamily": "unix",
                    "platformOs": "linux",
                },
            }))
        elif message.get("method") == "turn/start":
            await self.incoming.put(json.dumps({
                "id": message["id"], "result": {"turn": {"id": "turn-1"}}
            }))
        elif message.get("method") == "turn/interrupt":
            await self.incoming.put(json.dumps({"id": message["id"], "result": {}}))

    async def receive(self):
        return await self.incoming.get()

    async def feed(self, value):
        await self.incoming.put(json.dumps(value))


class _Runtime:
    def __init__(self, client):
        self.profile_id = "profile-1"
        self.generation = 1
        self.client = client


class _RuntimeManager:
    def __init__(self, runtime):
        self.runtime = runtime
        self.acquire_calls = 0
        self.shutdown_calls = 0

    async def acquire(self, profile_id):
        self.acquire_calls += 1
        return self.runtime

    async def shutdown_profile(self, profile_id):
        self.shutdown_calls += 1
        await self.runtime.client.close()


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id,
            1,
            (CodexModelDescriptor("model-1", "wire-1", "Model", ("high",), "high", True, False),),
            0.0,
            100.0,
        )


class _Telegram:
    def __init__(self):
        self.creates = []
        self.edits = []
        self.next_id = 1

    async def create_message(self, *, chat_id, text):
        message_id = self.next_id
        self.next_id += 1
        self.creates.append((chat_id, message_id, text))
        return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)

    async def edit_message(self, *, chat_id, message_id, text):
        self.edits.append((chat_id, message_id, text))
        return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)


class _NoEffect:
    async def interrupt(self, request):
        raise AssertionError("unexpected interrupt")

    async def delete(self, request):
        raise AssertionError("unexpected delete")


class _Thread:
    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        raise AssertionError("existing dialogue must not start a thread")


class P6LocalOrchestrationAcceptance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.clock = 100
        self.storage = await SqliteStorage.open(
            os.path.join(self.directory.name, "state.sqlite3"), now_ms=lambda: self.clock
        )
        manifest = FleetManifest("fleet-1", (FleetMember("server-80", "SERVER-80"),))
        boot = await ControllerRuntimeRepository(self.storage, now_ms=lambda: self.clock).begin_boot("fleet-1")
        await SettingsRepository(self.storage, now_ms=lambda: self.clock).initialize_if_absent(
            profile_id="profile-1", model_id="model-1", reasoning_effort="high"
        )
        dialogue = await DialogueRepository(self.storage, now_ms=lambda: self.clock).create_intent(
            dialogue_id="dialogue-1", server_id="server-80", profile_id="profile-1"
        )
        await DialogueRepository(self.storage, now_ms=lambda: self.clock).confirm_created(
            dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id="thread-1"
        )
        transport = _Transport()
        client = CodexProtocolClient(transport, client_version="fake")
        await client.initialize()
        runtime = _Runtime(client)
        manager = _RuntimeManager(runtime)
        telegram = _Telegram()
        signal = ApprovalDecisionSignal()
        p3_job_number = 0
        def p3_id(kind):
            nonlocal p3_job_number
            if kind == "job":
                p3_job_number += 1
                return "job-id" if p3_job_number == 1 else f"job-{p3_job_number}-id"
            return f"{kind}-{p3_job_number}-id"
        lifecycle = ApprovalAwareTurnLifecycle(
            self.storage, runtime_manager=manager, model_catalog=_Catalog(), telegram=telegram,
            approval_signal=signal, now_ms=lambda: self.clock, id_factory=lambda kind: kind + "-id",
            approval_sleep=self._blocked_sleep,
        )
        p3 = DialogueTurnService(
            self.storage, server_id="server-80", profiles=(CodexProfile("profile-1", "/synthetic", "Profile"),),
            model_catalog=_Catalog(), thread_lifecycle=_Thread(), turn_lifecycle=lifecycle,
            working_directory_resolver=type("W", (), {"resolve": lambda _, profile_id: TrustedWorkingDirectory("/synthetic")})(),
            now_ms=lambda: self.clock, id_factory=p3_id,
        )
        control = FleetControlService(
            self.storage, manifest=manifest, server_id="server-80", operator_user_id=7,
            control_chat_id=-100, boot_result=boot, now_ms=lambda: self.clock,
        )
        routing = FleetGroupRoutingService(self.storage, fleet_control=control, dialogue_turn=p3, now_ms=lambda: self.clock)
        private = PrivateControlService(
            self.storage, server_id="server-80", server_display_name="SERVER-80", operator_user_id=7,
            profiles=(CodexProfile("profile-1", "/synthetic", "Profile"),), model_catalog=_Catalog(),
            interrupt_service=_NoEffect(), delete_service=_NoEffect(), mode_provider=lambda: ControllerMode.ACTIVE,
            now_ms=lambda: self.clock, token_factory=self._token_factory,
        )
        display_number = 0
        def display_id(kind):
            nonlocal display_number
            display_number += 1
            return f"{kind}-display-{display_number}"
        delivery = TurnDeliveryService(self.storage, telegram=telegram, text_limit=512, now_ms=lambda: self.clock, id_factory=display_id)
        self.controller = LocalControllerOrchestrator(
            self.storage, group_routing=routing, fleet_status=FleetStatusService(manifest, server_id="server-80"),
            fleet_status_renderer=__import__("codex_control.adapters.telegram", fromlist=["TelegramFleetStatusRenderer"]).TelegramFleetStatusRenderer(),
            private_control=private, turn_delivery=delivery, turn_lifecycle=lifecycle,
            approval_signal=signal, dialogue_recovery=DialogueRecoveryService(self.storage, now_ms=lambda: self.clock),
        )
        self.transport, self.runtime_manager, self.telegram = transport, manager, telegram
        self.group_adapter = TelegramGroupUpdateAdapter(manifest, 7, -100)
        self.token_number = 0

    async def asyncTearDown(self):
        await self.storage.close()
        self.directory.cleanup()

    async def _blocked_sleep(self, delay):
        await asyncio.Event().wait()

    def _token_factory(self):
        self.token_number += 1
        return f"{self.token_number:032d}"

    def _raw_group(self, update_id, message_id, text):
        return {"update_id": update_id, "message": {"message_id": message_id,
            "from": {"id": 7, "is_bot": False}, "chat": {"id": -100, "type": "supergroup"}, "text": text}}

    async def _wait_pending(self):
        for _ in range(200):
            approvals = await self.storage.read(
                lambda c: tuple(row[0] for row in c.execute(
                    "SELECT approval_id FROM approvals WHERE state = 'PENDING'"
                ).fetchall())
            )
            if approvals:
                return approvals[0][0]
            await asyncio.sleep(0)
        self.fail("approval not published")

    async def _wait_wire_response(self):
        for _ in range(200):
            if any(item.get("id") == "approval-wire" for item in self.transport.sent):
                return
            await asyncio.sleep(0)
        self.fail("approval response not sent")

    async def _start_prompt(self, *, update_id=2, message_id=2):
        if update_id == 2:
            await self.controller.handle_group(self.group_adapter.normalize(self._raw_group(1, 1, "🖥 SERVER-80")))
        prompt = self.group_adapter.normalize(self._raw_group(update_id, message_id, "synthetic prompt"))
        task = asyncio.create_task(self.controller.handle_group(prompt))
        for _ in range(2000):
            candidate = await TurnJobRepository(self.storage).get("job-id" if update_id == 2 else "job-2-id")
            if candidate is not None and candidate.state is TurnJobState.CODEX_RUNNING:
                return task
            await asyncio.sleep(0)
        self.fail("turn did not reach running")

    async def _feed_completed(self, *, text=(), status="completed"):
        for index, value in enumerate(text):
            await self.transport.feed({
                "method": "item/completed",
                "params": {"threadId": "thread-1", "turnId": "turn-1", "item": {
                    "id": f"item-{index}", "type": "agentMessage", "text": value,
                }},
            })
        await self.transport.feed({
            "method": "turn/completed",
            "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": status}},
        })

    async def test_real_fake_p6_happy_path(self):
        self.assertEqual(ControllerMode.SLEEP, (await ControllerRuntimeRepository(self.storage).get()).requested_mode)
        activation = self.group_adapter.normalize(self._raw_group(1, 1, "🖥 SERVER-80"))
        await self.controller.handle_group(activation)
        prompt = self.group_adapter.normalize(self._raw_group(2, 2, "synthetic prompt"))
        self.assertEqual(GroupInboundKind.TEXT, prompt.kind)
        group_task = asyncio.create_task(self.controller.handle_group(prompt))
        for _ in range(200):
            candidate = await TurnJobRepository(self.storage).get("job-id")
            if candidate is not None and candidate.state is TurnJobState.CODEX_RUNNING:
                break
            await asyncio.sleep(0)
        job = await TurnJobRepository(self.storage).get("job-id")
        self.assertIsNotNone(job)
        self.assertEqual(TurnJobState.CODEX_RUNNING, (await TurnJobRepository(self.storage).get(job.job_id)).state)
        self.assertEqual(1, len(self.telegram.creates))
        self.assertTrue(self.telegram.creates[0][2].startswith("⏳ Выполняю запрос\n"))
        await self.transport.feed({
            "id": "approval-wire", "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1", "startedAtMs": 1,
                        "command": "echo safe", "cwd": "/synthetic", "reason": "synthetic"},
        })
        approval_id = await self._wait_pending()
        root = await self.controller.handle_private_command(PrivateCommandRequest(3, 7, 7, PrivateCommand.MENU))
        opened = await self.controller.handle_private_callback(PrivateCallbackRequest(
            4, 7, 7, "query", next(button.callback_data[4:] for row in root.panel.rows for button in row if button.label == "Approvals")
        ))
        allow = next(button.callback_data[4:] for row in opened.panel.rows for button in row if button.label == "Allow")
        await self.controller.handle_private_callback(PrivateCallbackRequest(5, 7, 7, "query", allow))
        await self._wait_wire_response()
        await self.transport.feed({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1", "item": {"id": "a", "type": "agentMessage", "text": "A" * 600}}})
        await self.transport.feed({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1", "item": {"id": "b", "type": "agentMessage", "text": "B" * 600}}})
        await self.transport.feed({"method": "turn/completed", "params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"}}})
        result = await group_task
        self.assertEqual(WorkStatusAttempt.CONFIRMED, result.acknowledgement_status)
        self.assertEqual(TurnJobState.DELIVERED, (await TurnJobRepository(self.storage).get("job-id")).state)
        self.assertGreaterEqual(len(self.telegram.edits), 1)
        self.assertEqual(self.telegram.creates[0][1], self.telegram.edits[0][1])
        self.assertGreaterEqual(len(self.telegram.creates) - 1, 2)
        self.assertEqual(1, len([item for item in self.transport.sent if item.get("id") == "approval-wire"]))
        self.assertEqual("accept", next(item["result"]["decision"] for item in self.transport.sent if item.get("id") == "approval-wire"))
        self.assertFalse([task for task in asyncio.all_tasks() if not task.done() and "local_orchestration" in getattr(task.get_coro(), "__qualname__", "")])

    async def test_real_deny_duplicate_callback_has_one_wire_response(self):
        group_task = await self._start_prompt()
        await self.transport.feed({
            "id": "deny-wire", "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1",
                        "startedAtMs": 1, "command": "echo safe", "cwd": "/synthetic", "reason": "synthetic"},
        })
        await self._wait_pending()
        root = await self.controller.handle_private_command(PrivateCommandRequest(3, 7, 7, PrivateCommand.MENU))
        opened = await self.controller.handle_private_callback(PrivateCallbackRequest(
            4, 7, 7, "query", next(b.callback_data[4:] for row in root.panel.rows for b in row if b.label == "Approvals")
        ))
        deny = next(b.callback_data[4:] for row in opened.panel.rows for b in row if b.label == "Deny")
        first = await self.controller.handle_private_callback(PrivateCallbackRequest(5, 7, 7, "query", deny))
        second = await self.controller.handle_private_callback(PrivateCallbackRequest(6, 7, 7, "query", deny))
        self.assertEqual("DENIED", first.status.value)
        self.assertEqual("ALREADY_USED", second.status.value)
        for _ in range(200):
            if any(item.get("id") == "deny-wire" for item in self.transport.sent):
                break
            await asyncio.sleep(0)
        await self._feed_completed()
        await group_task
        responses = [item for item in self.transport.sent if item.get("id") == "deny-wire"]
        self.assertEqual(1, len(responses))
        self.assertEqual("decline", responses[0]["result"]["decision"])

    async def test_second_turn_uses_new_binding_and_hint(self):
        first = await self._start_prompt()
        await self._feed_completed()
        await first
        second = await self._start_prompt(update_id=3, message_id=3)
        self.assertEqual(2, len(self.telegram.creates))
        await self._feed_completed()
        await second
        self.assertEqual((1, 2), tuple(item[1] for item in self.telegram.edits))
        self.assertEqual(2, self.runtime_manager.acquire_calls)

    async def test_outer_group_cancellation_keeps_owned_operation(self):
        task = await self._start_prompt()
        task.cancel()
        await self._feed_completed(text=("A" * 600, "B" * 600))
        result = await task
        self.assertEqual("COMPLETED", result.routing.turn_result.status.value)
        self.assertEqual(TurnJobState.DELIVERED, (await TurnJobRepository(self.storage).get("job-id")).state)

    async def test_interrupt_uses_same_lifecycle_without_reacquire(self):
        group_task = await self._start_prompt()
        binding = self.controller._turn_lifecycle._lease.binding
        interrupt_task = asyncio.create_task(self.controller._turn_lifecycle.interrupt_turn(binding))
        await self._feed_completed()
        interrupt = await interrupt_task
        await group_task
        self.assertEqual("CONFIRMED", interrupt.status.value)
        self.assertEqual(1, self.runtime_manager.acquire_calls)

    async def test_terminal_live_approval_cancels_without_wire_response(self):
        group_task = await self._start_prompt()
        await self.transport.feed({
            "id": "terminal-wire", "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1",
                        "startedAtMs": 1, "command": "echo safe", "cwd": "/synthetic", "reason": "synthetic"},
        })
        await self._wait_pending()
        await self._feed_completed()
        result = await group_task
        self.assertEqual("UNKNOWN", result.routing.turn_result.status.value)
        self.assertEqual(1, self.runtime_manager.shutdown_calls)
        self.assertFalse(any(item.get("id") == "terminal-wire" for item in self.transport.sent))
        states = await self.storage.read(lambda c: tuple(row[0] for row in c.execute("SELECT state FROM approvals").fetchall()))
        self.assertEqual(("CANCELLED",), states)

    async def test_unconsumed_confirmed_start_is_shutdown_once(self):
        async def fail_running(repository, **kwargs):
            raise StorageError(StorageErrorCategory.TRANSACTION_FAILED)

        with patch.object(TurnJobRepository, "mark_codex_running", fail_running):
            await self.controller.handle_group(self.group_adapter.normalize(self._raw_group(1, 1, "🖥 SERVER-80")))
            task = asyncio.create_task(self.controller.handle_group(
                self.group_adapter.normalize(self._raw_group(2, 2, "synthetic prompt"))
            ))
            result = await task
        self.assertEqual("UNKNOWN", result.routing.turn_result.status.value)
        self.assertEqual(1, self.runtime_manager.shutdown_calls)
        self.assertEqual(TurnJobState.UNKNOWN, (await TurnJobRepository(self.storage).get("job-id")).state)

    async def test_startup_without_candidates_is_ready_and_does_not_replay_ack(self):
        result = await self.controller.recover_startup()
        self.assertEqual("READY", result.status.value)
        self.assertEqual((), result.delivery_statuses)
        self.assertEqual([], self.telegram.creates)

    async def test_restart_recovery_completed_job_uses_create_without_ack_replay(self):
        await create_completed(self.storage)
        result = await self.controller.recover_startup()
        self.assertEqual("READY", result.status.value)
        self.assertEqual(("DELIVERED",), tuple(status.value for status in result.delivery_statuses))
        self.assertEqual(1, len(self.telegram.creates))
        self.assertEqual([], self.telegram.edits)
