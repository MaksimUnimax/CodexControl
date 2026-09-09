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
    TelegramPrivateUpdateAdapter,
)
from codex_control.application import (
    ActiveTurnRegistry,
    ApprovalAwareTurnLifecycle,
    ApprovalDecisionSignal,
    DialogueTurnService,
    DialogueInterruptService,
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
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.turn_lifecycle import TurnBinding, TurnLifecycleError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding
from codex_control.application.local_orchestration import (
    LocalOrchestrationError,
    LocalOrchestrationErrorCategory,
    LocalStartupStatus,
)
from codex_control.application.response_delivery import TurnDeliveryRequest, TurnDeliveryStatus
from codex_control.storage import (
    ApprovalKind,
    ApprovalState,
    DeliveryFinishOutcome,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliverySegmentRepository,
    TransientPayloadKind,
    TransientPayloadRepository,
)
from tests.acceptance.test_p2_6b_support import create_completed, create_received


class _Transport:
    def __init__(self):
        self.incoming = asyncio.Queue()
        self.sent = []
        self.turn_number = 0
        self.current_turn_id = None
        self.interrupt_effects = []
        self.interrupt_seen = asyncio.Event()

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
            self.turn_number += 1
            self.current_turn_id = f"turn-{self.turn_number}"
            await self.incoming.put(json.dumps({
                "id": message["id"], "result": {"turn": {"id": self.current_turn_id}}
            }))
        elif message.get("method") == "turn/interrupt":
            self.interrupt_effects.append(message)
            self.interrupt_seen.set()
            await self.incoming.put(json.dumps({"id": message["id"], "result": {}}))

    async def receive(self):
        return await self.incoming.get()

    async def feed(self, value):
        await self.incoming.put(json.dumps(value))

    def feed_nowait(self, value):
        self.incoming.put_nowait(json.dumps(value))


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
        self.final_delivery_started = asyncio.Event()
        self.release_final_delivery = asyncio.Event()
        self.block_final_delivery = False

    async def create_message(self, *, chat_id, text):
        if self.block_final_delivery and not text.startswith("⏳ Выполняю запрос"):
            self.final_delivery_started.set()
            await self.release_final_delivery.wait()
        message_id = self.next_id
        self.next_id += 1
        self.creates.append((chat_id, message_id, text))
        return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)

    async def edit_message(self, *, chat_id, message_id, text):
        if self.block_final_delivery and not text.startswith("⏳ Выполняю запрос"):
            self.final_delivery_started.set()
            await self.release_final_delivery.wait()
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
        approval_id_number = 0
        def approval_id_factory(kind):
            nonlocal approval_id_number
            approval_id_number += 1
            return f"{kind}-{approval_id_number}-id"
        p3_job_number = 0
        def p3_id(kind):
            nonlocal p3_job_number
            if kind == "job":
                p3_job_number += 1
                return "job-id" if p3_job_number == 1 else f"job-{p3_job_number}-id"
            return f"{kind}-{p3_job_number}-id"
        shared_registry = ActiveTurnRegistry()
        lifecycle = ApprovalAwareTurnLifecycle(
            self.storage, runtime_manager=manager, model_catalog=_Catalog(), telegram=telegram,
            approval_signal=signal, now_ms=lambda: self.clock, id_factory=approval_id_factory,
            approval_sleep=self._blocked_sleep,
        )
        p3 = DialogueTurnService(
            self.storage, server_id="server-80", profiles=(CodexProfile("profile-1", "/synthetic", "Profile", "/synthetic-state"),),
            model_catalog=_Catalog(), thread_lifecycle=_Thread(), turn_lifecycle=lifecycle,
            working_directory_resolver=type("W", (), {"resolve": lambda _, profile_id: TrustedWorkingDirectory("/synthetic")})(),
            now_ms=lambda: self.clock, id_factory=p3_id,
            active_turn_registry=shared_registry,
        )
        control = FleetControlService(
            self.storage, manifest=manifest, server_id="server-80", operator_user_id=7,
            control_chat_id=-100, boot_result=boot, now_ms=lambda: self.clock,
        )
        routing = FleetGroupRoutingService(self.storage, fleet_control=control, dialogue_turn=p3, now_ms=lambda: self.clock)
        dialogue_interrupt = DialogueInterruptService(
            self.storage,
            server_id="server-80",
            active_turn_registry=shared_registry,
            turn_lifecycle=lifecycle,
            now_ms=lambda: self.clock,
            id_factory=lambda kind: f"{kind}-interrupt-id",
        )
        private = PrivateControlService(
            self.storage, server_id="server-80", server_display_name="SERVER-80", operator_user_id=7,
            profiles=(CodexProfile("profile-1", "/synthetic", "Profile", "/synthetic-state"),), model_catalog=_Catalog(),
            interrupt_service=dialogue_interrupt, delete_service=_NoEffect(), mode_provider=lambda: ControllerMode.ACTIVE,
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
        self.shared_registry = shared_registry
        self.dialogue_interrupt = dialogue_interrupt
        self.dialogue_turn = p3
        self.group_adapter = TelegramGroupUpdateAdapter(manifest, 7, -100)
        self.private_adapter = TelegramPrivateUpdateAdapter(7)
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

    def _raw_private_command(self, update_id, text):
        return self.private_adapter.normalize({
            "update_id": update_id,
            "message": {"from": {"id": 7, "is_bot": False}, "chat": {"id": 7, "type": "private"}, "text": text},
        })

    def _raw_private_callback(self, update_id, query_id, token):
        return self.private_adapter.normalize({
            "update_id": update_id,
            "callback_query": {
                "id": query_id,
                "from": {"id": 7, "is_bot": False},
                "message": {"chat": {"id": 7, "type": "private"}},
                "data": "cc1:" + token,
            },
        })

    def _private_command_request(self, normalized):
        self.assertEqual("COMMAND", normalized.kind.value)
        return PrivateCommandRequest(normalized.update_id, normalized.user_id, normalized.chat_id, normalized.command)

    def _private_callback_request(self, normalized):
        self.assertEqual("CALLBACK", normalized.kind.value)
        return PrivateCallbackRequest(
            normalized.update_id, normalized.user_id, normalized.chat_id,
            normalized.callback_query_id, normalized.callback_token,
        )

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

    async def _wait_wire_response_id(self, request_id):
        for _ in range(200):
            if any(item.get("id") == request_id for item in self.transport.sent):
                return
            await asyncio.sleep(0)
        self.fail("approval response not sent")

    async def _wait_no_pending_approvals(self):
        for _ in range(200):
            pending = await self.storage.read(lambda c: c.execute(
                "SELECT approval_id FROM approvals WHERE state = 'PENDING'"
            ).fetchall())
            if not pending:
                return
            await asyncio.sleep(0)
        self.fail("approval remained pending")

    async def _create_display_payload(self, job_id, payload_id, text):
        return await TransientPayloadRepository(self.storage, now_ms=lambda: self.clock).create(
            payload_id=payload_id,
            dialogue_id="dialogue-1",
            job_id=job_id,
            kind=TransientPayloadKind.DISPLAY,
            content=text.encode("utf-8"),
            expires_at_ms=100_000,
        )

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
        turn_id = self.transport.current_turn_id
        for index, value in enumerate(text):
            await self.transport.feed({
                "method": "item/completed",
                "params": {"threadId": "thread-1", "turnId": turn_id, "item": {
                    "id": f"item-{index}", "type": "agentMessage", "text": value,
                }},
            })
        await self.transport.feed({
            "method": "turn/completed",
            "params": {"threadId": "thread-1", "turn": {"id": turn_id, "status": status}},
        })

    def _feed_completed_nowait(self, *, text=(), status="completed"):
        turn_id = self.transport.current_turn_id
        for index, value in enumerate(text):
            self.transport.feed_nowait({
                "method": "item/completed",
                "params": {"threadId": "thread-1", "turnId": turn_id, "item": {
                    "id": f"item-{index}", "type": "agentMessage", "text": value,
                }},
            })
        self.transport.feed_nowait({
            "method": "turn/completed",
            "params": {"threadId": "thread-1", "turn": {"id": turn_id, "status": status}},
        })

    async def test_real_fake_p6_happy_path(self):
        self.assertEqual(ControllerMode.SLEEP, (await ControllerRuntimeRepository(self.storage).get()).requested_mode)
        startup = await self.controller.recover_startup()
        self.assertEqual(LocalStartupStatus.READY, startup.status)
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
        root = await self.controller.handle_private_command(self._private_command_request(self._raw_private_command(3, "/menu")))
        opened_token = next(button.callback_data[4:] for row in root.panel.rows for button in row if button.label == "Approvals")
        opened = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(4, "query", opened_token)))
        allow = next(button.callback_data[4:] for row in opened.panel.rows for button in row if button.label == "Allow")
        await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(5, "query", allow)))
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
        root = await self.controller.handle_private_command(self._private_command_request(self._raw_private_command(3, "/menu")))
        opened_token = next(b.callback_data[4:] for row in root.panel.rows for b in row if b.label == "Approvals")
        opened = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(4, "query", opened_token)))
        deny = next(b.callback_data[4:] for row in opened.panel.rows for b in row if b.label == "Deny")
        first = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(5, "query", deny)))
        second = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(6, "query", deny)))
        self.assertEqual("DENIED", first.status.value)
        self.assertEqual("ALREADY_USED", second.status.value)
        for _ in range(200):
            if any(item.get("id") == "deny-wire" for item in self.transport.sent):
                break
            await asyncio.sleep(0)
        await self._feed_completed(text=("first turn",))
        await group_task
        responses = [item for item in self.transport.sent if item.get("id") == "deny-wire"]
        self.assertEqual(1, len(responses))
        self.assertEqual("decline", responses[0]["result"]["decision"])

    async def test_second_turn_uses_new_binding_and_hint(self):
        first = await self._start_prompt()
        await self._feed_completed(text=("second turn",))
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

    async def test_real_private_interrupt_uses_shared_p3_composition_without_reacquire(self):
        group_task = await self._start_prompt()
        binding = self.controller._turn_lifecycle._lease.binding
        job = await TurnJobRepository(self.storage).get("job-id")
        self.assertIs(binding, self.shared_registry.lookup(job.job_id))
        self.assertIs(self.dialogue_turn._active_turn_registry, self.shared_registry)
        self.assertIs(self.dialogue_interrupt._registry, self.shared_registry)
        self.assertIs(self.dialogue_turn._turn_lifecycle, self.dialogue_interrupt._turn_lifecycle)
        self.assertEqual("thread-1", binding.thread_id)
        self.assertEqual("turn-1", binding.turn_id)
        acquire_calls = self.runtime_manager.acquire_calls

        root = await self.controller.handle_private_command(
            self._private_command_request(self._raw_private_command(30, "/menu"))
        )
        dialogue_token = next(
            button.callback_data[4:]
            for row in root.panel.rows
            for button in row
            if button.label == "Dialogue"
        )
        dialogue_panel = await self.controller.handle_private_callback(
            self._private_callback_request(self._raw_private_callback(31, "dialogue-query", dialogue_token))
        )
        interrupt_token = next(
            button.callback_data[4:]
            for row in dialogue_panel.panel.rows
            for button in row
            if button.label == "Interrupt"
        )
        callback_task = asyncio.create_task(self.controller.handle_private_callback(
            self._private_callback_request(self._raw_private_callback(32, "interrupt-query", interrupt_token))
        ))
        await asyncio.wait_for(self.transport.interrupt_seen.wait(), 1)
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertEqual("INTERRUPTING", dialogue.state.value)
        running_job = await TurnJobRepository(self.storage).get("job-id")
        self.assertEqual((job.profile_id, job.thread_id, job.codex_turn_id),
                         (running_job.profile_id, running_job.thread_id, running_job.codex_turn_id))
        self.assertEqual(1, len(self.transport.interrupt_effects))
        self.assertEqual({"threadId": "thread-1", "turnId": "turn-1"},
                         self.transport.interrupt_effects[0]["params"])
        self.assertEqual(acquire_calls, self.runtime_manager.acquire_calls)

        await self._feed_completed(status="interrupted")
        private_result = await callback_task
        await group_task
        self.assertEqual("INTERRUPTED", private_result.status.value)
        self.assertIn((await TurnJobRepository(self.storage).get("job-id")).state.value,
                      {"FAILED", "DELIVERY_UNKNOWN", "DELIVERED"})
        self.assertEqual("IDLE", (await DialogueRepository(self.storage).get_live()).state.value)
        self.assertIsNone(self.shared_registry.lookup("job-id"))
        self.assertEqual(1, len(self.transport.interrupt_effects))
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

    async def test_second_turn_is_admitted_while_first_final_delivery_is_blocked(self):
        first = await self._start_prompt()
        first_binding = self.controller._turn_lifecycle._lease.binding
        first_hint = self.controller._turn_lifecycle._hints["job-id"]
        self.telegram.block_final_delivery = True
        await self._feed_completed(text=("first turn",))
        await asyncio.wait_for(self.telegram.final_delivery_started.wait(), 1)
        self.assertTrue(self.telegram.final_delivery_started.is_set())
        self.assertIsNone(self.controller._turn_lifecycle._lease)
        self.assertEqual(first_hint, self.controller._turn_lifecycle._hints["job-id"])

        second = await self._start_prompt(update_id=3, message_id=3)
        second_binding = self.controller._turn_lifecycle._lease.binding
        self.assertIsNot(first_binding, second_binding)
        self.assertNotEqual(first_binding.turn_id, second_binding.turn_id)
        self.assertEqual(2, len(self.telegram.creates))
        self.assertNotEqual(self.telegram.creates[0][1], self.telegram.creates[1][1])
        self.assertNotEqual(first_hint[1], self.controller._turn_lifecycle._hints["job-2-id"][1])
        self.assertEqual("CODEX_RUNNING", (await TurnJobRepository(self.storage).get("job-2-id")).state.value)

        # P6.1 holds its durable claim until the dialogue is idle.  Keep both
        # final effects blocked while the second turn terminalizes, then
        # release them together; the important admission overlap remains
        # real and no prompt is queued.
        self._feed_completed_nowait(text=("second turn",))
        for _ in range(1000):
            second_job = await TurnJobRepository(self.storage).get("job-2-id")
            if second_job is not None and second_job.state is TurnJobState.CODEX_COMPLETED:
                break
            await asyncio.sleep(0)
        self.assertEqual(TurnJobState.CODEX_COMPLETED, (await TurnJobRepository(self.storage).get("job-2-id")).state)
        self.telegram.release_final_delivery.set()
        first_result = await first
        self.assertEqual("DELIVERED", (await TurnJobRepository(self.storage).get("job-id")).state.value)
        second_result = await second
        self.assertEqual("DELIVERED", (await TurnJobRepository(self.storage).get("job-2-id")).state.value)
        self.assertEqual(2, len([item for item in self.telegram.edits if item[1] in (first_hint[1], self.telegram.creates[1][1])]))
        self.assertEqual("PROMPT", first_result.routing.status.value)
        self.assertEqual("PROMPT", second_result.routing.status.value)

    async def test_wait_pump_setup_failure_shuts_down_retires_and_preserves_hint_until_unknown_status(self):
        self.telegram.block_final_delivery = True
        with patch("codex_control.application.local_orchestration.DurableApprovalOperator", side_effect=TypeError("setup")):
            await self.controller.handle_group(self.group_adapter.normalize(self._raw_group(1, 1, "🖥 SERVER-80")))
            task = asyncio.create_task(self.controller.handle_group(
                self.group_adapter.normalize(self._raw_group(2, 2, "synthetic prompt"))
            ))
            for _ in range(1000):
                candidate = await TurnJobRepository(self.storage).get("job-id")
                if candidate is not None and candidate.state is TurnJobState.CODEX_RUNNING:
                    break
                await asyncio.sleep(0)
            for _ in range(1000):
                if self.telegram.final_delivery_started.is_set() and self.controller._turn_lifecycle._lease is None:
                    break
                await asyncio.sleep(0)
            self.assertTrue(self.telegram.final_delivery_started.is_set())
            self.assertIsNone(self.controller._turn_lifecycle._lease)
            self.assertIn("job-id", self.controller._turn_lifecycle._hints)
            self.assertEqual(1, self.runtime_manager.shutdown_calls)
            self.assertEqual("UNKNOWN", (await TurnJobRepository(self.storage).get("job-id")).state.value)
            self.telegram.release_final_delivery.set()
            result = await task
        self.assertEqual("UNKNOWN", result.routing.turn_result.status.value)
        self.assertNotIn("job-id", self.controller._turn_lifecycle._hints)
        self.assertEqual(0, len([item for item in self.transport.sent if item.get("id") in {"approval-wire", "old-wire"}]))
        self.assertFalse([
            task for task in asyncio.all_tasks() if not task.done()
            and "local_orchestration" in getattr(task.get_coro(), "__qualname__", "")
        ])

    async def test_startup_stranded_sending_is_zero_resend_delivery_unknown(self):
        completed = await __import__("tests.acceptance.test_p2_6b_support", fromlist=["create_completed"]).create_completed(self.storage)
        await self._create_display_payload(completed.job.job_id, "stranded-display", "stranded")
        planned = await DeliverySegmentRepository(self.storage, now_ms=lambda: self.clock).plan(
            job_id=completed.job.job_id, expected_job_version=completed.job.version,
            items=[DeliveryPlanItem(DeliveryOperation.CREATE, "stranded-display", None)],
        )
        claim = await DeliverySegmentRepository(self.storage, now_ms=lambda: self.clock).claim_next(
            job_id=completed.job.job_id, expected_job_version=planned.job.version
        )
        self.assertEqual(1, claim.segment.attempt_count)
        result = await self.controller.recover_startup()
        self.assertEqual(LocalStartupStatus.READY, result.status)
        self.assertEqual((TurnDeliveryStatus.DELIVERY_UNKNOWN,), result.delivery_statuses)
        self.assertEqual([], self.telegram.creates)
        self.assertEqual([], self.telegram.edits)
        recovered = await TurnJobRepository(self.storage).get(completed.job.job_id)
        self.assertEqual(TurnJobState.DELIVERY_UNKNOWN, recovered.state)
        self.assertEqual("TELEGRAM_RECOVERY_AMBIGUOUS", recovered.error_class)
        self.assertEqual((), await TurnJobRepository(self.storage).list_delivery_candidates(limit=4096))

    async def test_startup_confirmed_prefix_resumes_pending_suffix_without_resend(self):
        completed = await __import__("tests.acceptance.test_p2_6b_support", fromlist=["create_completed"]).create_completed(self.storage)
        await self._create_display_payload(completed.job.job_id, "prefix-one", "first")
        await self._create_display_payload(completed.job.job_id, "prefix-two", "second")
        delivery = DeliverySegmentRepository(self.storage, now_ms=lambda: self.clock)
        planned = await delivery.plan(
            job_id=completed.job.job_id, expected_job_version=completed.job.version,
            items=[
                DeliveryPlanItem(DeliveryOperation.EDIT, "prefix-one", 700),
                DeliveryPlanItem(DeliveryOperation.CREATE, "prefix-two", None),
            ],
        )
        claim = await delivery.claim_next(job_id=completed.job.job_id, expected_job_version=planned.job.version)
        finished = await delivery.finish_sending(
            job_id=completed.job.job_id, sequence=1, expected_job_version=claim.job.version,
            outcome=DeliveryFinishOutcome.CONFIRMED, confirmed_message_id=700,
        )
        self.assertEqual(TurnJobState.DELIVERING, finished.job.state)
        result = await self.controller.recover_startup()
        self.assertEqual((TurnDeliveryStatus.DELIVERED,), result.delivery_statuses)
        self.assertEqual([], self.telegram.edits)
        self.assertEqual(["second"], [item[2] for item in self.telegram.creates])
        segments = await DeliverySegmentRepository(self.storage).list_for_job(completed.job.job_id)
        self.assertEqual(("CONFIRMED", "CONFIRMED"), tuple(segment.state.value for segment in segments))

    async def test_startup_active_job_marks_unknown_then_cancels_pending_approval(self):
        ingress = await __import__("tests.acceptance.test_p2_6b_support", fromlist=["create_received"]).create_received(
            self.storage, job_id="recovered-job", update_id=10
        )
        dialogue = await DialogueRepository(self.storage).get_live()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: self.clock)
        claimed = await jobs.claim_turn(
            job_id="recovered-job", expected_job_version=ingress.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread-1",
        )
        starting = await jobs.mark_codex_starting(job_id="recovered-job", expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(
            job_id="recovered-job", expected_version=starting.version, codex_turn_id="recovered-turn"
        )
        await ApprovalRepository(self.storage, now_ms=lambda: self.clock).create_pending(
            approval_id="recovered-approval", profile_id="profile-1", wire_request_id="old-wire",
            kind=ApprovalKind.COMMAND_EXECUTION, job_id=running.job_id,
            expected_job_version=running.version, expires_at_ms=50_000,
        )
        result = await self.controller.recover_startup()
        self.assertEqual("TURN_MARKED_UNKNOWN", result.dialogue_recovery.status.value)
        self.assertEqual(TurnJobState.UNKNOWN, (await TurnJobRepository(self.storage).get("recovered-job")).state)
        self.assertEqual("TURN_UNKNOWN", (await DialogueRepository(self.storage).get_live()).state.value)
        approval = await ApprovalRepository(self.storage).get("recovered-approval")
        self.assertEqual(ApprovalState.CANCELLED, approval.state)
        self.assertEqual(1, result.approvals_cancelled)
        self.assertEqual([], [item for item in self.transport.sent if item.get("id") == "old-wire"])
        self.assertEqual([], self.telegram.creates)

    async def test_startup_delivery_bound_is_exactly_256_with_final_probe_and_no_worker(self):
        completed = await create_completed(self.storage)
        delivered = await self.controller._turn_delivery.deliver(TurnDeliveryRequest(completed.job.job_id))
        self.assertEqual(TurnDeliveryStatus.DELIVERED, delivered.status)
        discovery_calls = 0
        delivery_calls = []

        async def discover(repository, *, limit):
            nonlocal discovery_calls
            discovery_calls += 1
            return (completed.job,) if discovery_calls <= 257 else ()

        class DeliverySeam:
            async def deliver(self, request):
                delivery_calls.append(request)
                return delivered

        original_delivery = self.controller._turn_delivery
        self.controller._turn_delivery = DeliverySeam()
        with patch.object(TurnJobRepository, "list_delivery_candidates", new=discover):
            result = await self.controller.recover_startup()
            self.assertEqual(LocalStartupStatus.LIMIT_REACHED, result.status)
            self.assertEqual(256, len(result.delivery_statuses))
            self.assertEqual(256, len(delivery_calls))
            self.assertEqual(257, discovery_calls)
            resumed = await self.controller.recover_startup()
        self.controller._turn_delivery = original_delivery
        self.assertEqual(LocalStartupStatus.READY, resumed.status)
        self.assertEqual((), resumed.delivery_statuses)
        self.assertFalse([
            task for task in asyncio.all_tasks() if not task.done()
            and "local_orchestration" in getattr(task.get_coro(), "__qualname__", "")
        ])

    async def test_status_is_pure_routing_projection(self):
        await self.controller.recover_startup()
        await self.controller.handle_group(self.group_adapter.normalize(self._raw_group(1, 1, "🖥 SERVER-80")))
        before = await ControllerRuntimeRepository(self.storage).get()
        before_jobs = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0])
        status = await self.controller.handle_group(self.group_adapter.normalize(self._raw_group(2, 2, "📊 СТАТУС")))
        after = await ControllerRuntimeRepository(self.storage).get()
        after_jobs = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0])
        self.assertEqual("STATUS", status.routing.status.value)
        self.assertEqual(set(status.fleet_status_payload), {"text"})
        self.assertIsInstance(status.fleet_status_payload["text"], str)
        self.assertEqual([], self.telegram.creates)
        self.assertEqual([], self.telegram.edits)
        self.assertEqual(before.last_control_epoch, after.last_control_epoch)
        self.assertEqual(ControllerMode.ACTIVE, before.requested_mode)
        self.assertEqual(before.requested_mode, after.requested_mode)
        self.assertEqual(before_jobs, after_jobs)

    async def test_failed_live_turn_uses_one_safe_status_and_never_p6_1(self):
        task = await self._start_prompt()
        calls = []
        original = self.controller._turn_delivery.deliver
        async def unexpected(request):
            calls.append(request)
            raise AssertionError("P6.1 must not handle FAILED")
        self.controller._turn_delivery.deliver = unexpected
        try:
            await self._feed_completed(status="failed")
            result = await task
        finally:
            self.controller._turn_delivery.deliver = original
        self.assertEqual("FAILED", result.routing.turn_result.status.value)
        self.assertEqual([], calls)
        self.assertEqual(1, len(self.telegram.creates))
        self.assertEqual(1, len(self.telegram.edits))
        self.assertEqual("❌ Выполнение завершилось с ошибкой\nСервер: server-80\nПрофиль: profile-1\nМодель: model-1\nРассуждение: high", self.telegram.edits[0][2])
        self.assertNotIn("error", self.telegram.edits[0][2].lower())
        self.assertEqual({}, self.controller._turn_lifecycle._hints)

    async def test_unknown_live_turn_uses_one_safe_status_and_never_p6_1(self):
        task = await self._start_prompt()
        calls = []
        original = self.controller._turn_delivery.deliver
        async def unexpected(request):
            calls.append(request)
            raise AssertionError("P6.1 must not handle UNKNOWN")
        self.controller._turn_delivery.deliver = unexpected
        try:
            await self._feed_completed(status="not-a-terminal-status")
            result = await task
        finally:
            self.controller._turn_delivery.deliver = original
        self.assertEqual("UNKNOWN", result.routing.turn_result.status.value)
        self.assertEqual([], calls)
        self.assertEqual(1, len(self.telegram.creates))
        self.assertEqual(1, len(self.telegram.edits))
        self.assertEqual("⚠️ Результат выполнения не подтверждён\nСервер: server-80\nПрофиль: profile-1\nМодель: model-1\nРассуждение: high", self.telegram.edits[0][2])
        self.assertNotIn("error", self.telegram.edits[0][2].lower())
        self.assertEqual({}, self.controller._turn_lifecycle._hints)

    async def test_multiple_sequential_approvals_use_one_binding_and_two_wire_responses(self):
        task = await self._start_prompt()
        binding = self.controller._turn_lifecycle._lease.binding
        await self.transport.feed({
            "id": "approval-wire-1", "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1",
                        "startedAtMs": 1, "command": "echo one", "cwd": "/synthetic", "reason": "synthetic"},
        })
        await self._wait_pending()
        root = await self.controller.handle_private_command(self._private_command_request(self._raw_private_command(20, "/menu")))
        opened_token = next(b.callback_data[4:] for row in root.panel.rows for b in row if b.label == "Approvals")
        opened = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(21, "query-1", opened_token)))
        allow = next(b.callback_data[4:] for row in opened.panel.rows for b in row if b.label == "Allow")
        await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(22, "query-2", allow)))
        await self._wait_wire_response_id("approval-wire-1")
        await self._wait_no_pending_approvals()
        await self.transport.feed({
            "id": "approval-wire-2", "method": "item/commandExecution/requestApproval",
            "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-2",
                        "startedAtMs": 2, "command": "echo two", "cwd": "/synthetic", "reason": "synthetic"},
        })
        await self._wait_pending()
        root = await self.controller.handle_private_command(self._private_command_request(self._raw_private_command(23, "/menu")))
        opened_token = next(b.callback_data[4:] for row in root.panel.rows for b in row if b.label == "Approvals")
        opened = await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(24, "query-3", opened_token)))
        deny = next(b.callback_data[4:] for row in opened.panel.rows for b in row if b.label == "Deny")
        await self.controller.handle_private_callback(self._private_callback_request(self._raw_private_callback(25, "query-4", deny)))
        await self._wait_wire_response_id("approval-wire-2")
        self.assertIs(binding, self.controller._turn_lifecycle._lease.binding)
        self.assertIs(self.runtime_manager.runtime, self.controller._turn_lifecycle._lease.runtime)
        self.assertIs(self.runtime_manager.runtime.client, self.controller._turn_lifecycle._lease.runtime.client)
        await self._feed_completed()
        await task
        responses = [item for item in self.transport.sent if item.get("id") in {"approval-wire-1", "approval-wire-2"}]
        self.assertEqual(2, len(responses))
        self.assertEqual({"accept", "decline"}, {item["result"]["decision"] for item in responses})
        self.assertEqual(1, self.runtime_manager.acquire_calls)

    async def test_terminal_clean_request_get_race_keeps_terminal_authoritative(self):
        task = await self._start_prompt()
        await self._feed_completed()
        result = await task
        self.assertEqual("COMPLETED", result.routing.turn_result.status.value)
        self.assertEqual(0, self.runtime_manager.shutdown_calls)
        self.assertEqual([], await self.storage.read(lambda c: c.execute("SELECT approval_id FROM approvals").fetchall()))
        self.assertEqual([], [item for item in self.transport.sent if isinstance(item.get("id"), str) and item.get("id").startswith("approval")])
        self.assertIsNone(self.controller._turn_lifecycle._lease)

    async def test_terminal_captured_request_race_denies_once_without_durable_pending(self):
        task = await self._start_prompt()

        async def wait_both(owner, *tasks):
            await asyncio.gather(*(asyncio.shield(value) for value in tasks))
            return set(tasks)

        with patch.object(ApprovalAwareTurnLifecycle, "_wait_first", new=wait_both):
            await self.transport.feed({
                "id": "race-wire", "method": "item/commandExecution/requestApproval",
                "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "race-item",
                            "startedAtMs": 1, "command": "echo race", "cwd": "/synthetic", "reason": "synthetic"},
            })
            await self._feed_completed()
            result = await task
        self.assertEqual("UNKNOWN", result.routing.turn_result.status.value)
        self.assertEqual(1, self.runtime_manager.shutdown_calls)
        self.assertEqual([], await self.storage.read(lambda c: c.execute("SELECT approval_id FROM approvals").fetchall()))
        responses = [item for item in self.transport.sent if item.get("id") == "race-wire"]
        self.assertEqual(1, len(responses))
        self.assertEqual("decline", responses[0]["result"]["decision"])
        self.assertIsNone(self.controller._turn_lifecycle._lease)
        self.assertFalse([
            task for task in asyncio.all_tasks() if not task.done()
            and "local_orchestration" in getattr(task.get_coro(), "__qualname__", "")
        ])

    async def test_reconstructed_equal_binding_is_rejected_for_wait_and_interrupt(self):
        task = await self._start_prompt()
        exact = self.controller._turn_lifecycle._lease.binding
        reconstructed = TurnBinding(exact.profile_id, exact.thread_id, exact.turn_id)
        self.assertEqual(exact, reconstructed)
        self.assertIsNot(exact, reconstructed)
        with self.assertRaises(TurnLifecycleError) as wait_error:
            await self.controller._turn_lifecycle.wait_turn(reconstructed)
        with self.assertRaises(TurnLifecycleError) as interrupt_error:
            await self.controller._turn_lifecycle.interrupt_turn(reconstructed)
        self.assertEqual(CodexAdapterErrorCategory.TURN_REQUEST_INVALID, wait_error.exception.category)
        self.assertEqual(CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE, interrupt_error.exception.category)
        await self._feed_completed()
        await task
        self.assertEqual(1, self.runtime_manager.acquire_calls)

    async def test_concurrent_direct_start_fails_immediately_busy_without_second_effect(self):
        ingress = await create_received(self.storage, job_id="direct-job", update_id=30)
        await self.storage.write(lambda connection: connection.execute(
            "UPDATE turn_jobs SET model_id = 'model-1', reasoning_effort = 'high' WHERE job_id = 'direct-job'"
        ).rowcount)
        dialogue = await DialogueRepository(self.storage).get_live()
        jobs = TurnJobRepository(self.storage, now_ms=lambda: self.clock)
        claimed = await jobs.claim_turn(
            job_id="direct-job", expected_job_version=ingress.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread-1",
        )
        starting = await jobs.mark_codex_starting(job_id="direct-job", expected_version=claimed.job.version)
        thread = ThreadBinding("profile-1", "thread-1")
        entered = asyncio.Event()
        release = asyncio.Event()
        original_status = self.controller._turn_lifecycle._work_status

        async def blocked_status(job, prefix):
            entered.set()
            await release.wait()
            return await original_status(job, prefix)

        self.controller._turn_lifecycle._work_status = blocked_status
        try:
            first = asyncio.create_task(self.controller._turn_lifecycle.start_turn(
                thread_binding=thread, model_id="model-1", reasoning_effort="high",
                user_text="direct prompt", working_directory=TrustedWorkingDirectory("/synthetic"),
            ))
            await entered.wait()
            sent_before = len(self.transport.sent)
            job_count_before = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0])
            second = asyncio.create_task(self.controller._turn_lifecycle.start_turn(
                thread_binding=thread, model_id="model-1", reasoning_effort="high",
                user_text="second direct prompt", working_directory=TrustedWorkingDirectory("/synthetic"),
            ))
            with self.assertRaises(TurnLifecycleError) as busy:
                await asyncio.wait_for(second, 0.2)
            self.assertEqual(CodexAdapterErrorCategory.TURN_OPERATION_BUSY, busy.exception.category)
            self.assertEqual(sent_before, len(self.transport.sent))
            self.assertEqual(0, len(self.telegram.creates))
            self.assertEqual(job_count_before, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
            release.set()
            started = await first
        finally:
            self.controller._turn_lifecycle._work_status = original_status
        self.assertEqual("TURN_START_CONFIRMED", started.status.value)
        await self.controller._turn_lifecycle._cleanup_unconsumed_confirmed(starting.job_id)
        self.assertIsNone(self.controller._turn_lifecycle._lease)

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
