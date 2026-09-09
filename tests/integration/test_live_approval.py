import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalHandlingStatus,
    ApprovalKind,
    ApprovalRequest,
)
from codex_control.adapters.codex.protocol import CodexProtocolClient, InboundServerRequest
from codex_control.adapters.telegram import PrivateCommand
from codex_control.application import (
    ApprovalDecisionSignal,
    ApprovalTurnBinding,
    DurableApprovalOperator,
    OwnedApprovalResponseService,
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlStatus,
)
from codex_control.domain import CodexProfile, ControllerMode
from codex_control.storage import (
    ApprovalRepository,
    ApprovalState,
    ControllerRuntimeRepository,
    DialogueRepository,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
)
from codex_control.application import PrivateControlService


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor

        return CodexModelCatalog(profile_id, 1, (CodexModelDescriptor(
            "model-a", "wire-a", "Model A", ("high",), "high", True, False,
        ),), 0.0, 1.0)


class _Effects:
    async def interrupt(self, request):
        raise AssertionError("unexpected interrupt")

    async def delete(self, request):
        raise AssertionError("unexpected delete")


class _Transport:
    def __init__(self):
        self.sent = []
        self.incoming = asyncio.Queue()

    async def send(self, message):
        self.sent.append(message)

    async def receive(self):
        return await self.incoming.get()


class LiveApprovalIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.now = 100
        self.clock_calls = 0

        def clock():
            self.clock_calls += 1
            return self.now

        self.clock = clock
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=clock
        )
        self.database_path = os.path.join(self.tempdir.name, "state.sqlite3")
        await ControllerRuntimeRepository(self.storage, now_ms=clock).begin_boot("fleet")
        await SettingsRepository(self.storage, now_ms=clock).initialize_if_absent(
            profile_id="profile-a", model_id="model-a", reasoning_effort="high"
        )
        self.token_number = 0
        self.update_number = 10

        def token_factory():
            self.token_number += 1
            return f"{self.token_number:032d}"

        self.service = PrivateControlService(
            self.storage,
            server_id="server-80", server_display_name="Server 80", operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A", "/synthetic/state-a"),),
            model_catalog=_Catalog(), interrupt_service=_Effects(), delete_service=_Effects(),
            mode_provider=lambda: ControllerMode.SLEEP, now_ms=clock,
            token_factory=token_factory,
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def seed_running(self):
        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).create_intent(
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a"
        )
        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).confirm_created(
            dialogue_id="dialogue", expected_version=dialogue.version, thread_id="thread"
        )
        jobs = TurnJobRepository(self.storage, now_ms=self.clock)
        admitted = await jobs.claim_ingress(
            update_id=1000, job_id="job", source_chat_id=-7, source_message_id=1,
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a",
            thread_id="thread", model_id="model-a", reasoning_effort="high",
            input_payload_id="input", input_content=b"input", input_expires_at_ms=10000,
        )
        claimed = await jobs.claim_turn(
            job_id="job", expected_job_version=admitted.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread"
        )
        starting = await jobs.mark_codex_starting(job_id="job", expected_version=claimed.job.version)
        return await jobs.mark_codex_running(
            job_id="job", expected_version=starting.version, codex_turn_id="turn"
        )

    async def seed_pending(self, approval_id="approval", *, display=False, expires=1000):
        running = await self.seed_running()
        payload_id = None
        if display:
            payload_id = approval_id + "-payload"
            await TransientPayloadRepository(self.storage, now_ms=self.clock).create(
                payload_id=payload_id, dialogue_id="dialogue", job_id="job",
                kind=TransientPayloadKind.APPROVAL, content=b"safe details", expires_at_ms=expires,
            )
        record = await ApprovalRepository(self.storage, now_ms=self.clock).create_pending(
            approval_id=approval_id, profile_id="profile-a", wire_request_id=approval_id + "-wire",
            kind=ApprovalKind.COMMAND_EXECUTION, job_id="job",
            expected_job_version=running.version, display_payload_id=payload_id,
            expires_at_ms=expires,
        )
        return running, record

    async def approval_callbacks(self, approval_id="approval"):
        root_update = self.update_number
        self.update_number += 1
        open_update = self.update_number
        self.update_number += 1
        root = await self.service.handle_command(PrivateCommandRequest(root_update, 7, 7, PrivateCommand.MENU))
        opened = await self.service.handle_callback(PrivateCallbackRequest(
            open_update, 7, 7, "open", next(button.callback_data[4:] for row in root.panel.rows for button in row if button.label == "Approvals")
        ))
        return {
            button.label: button.callback_data[4:]
            for row in opened.panel.rows for button in row
        }

    def operator(self, signal, sleep):
        return DurableApprovalOperator(
            self.storage,
            binding=ApprovalTurnBinding("job", "profile-a", "thread", "turn"),
            signal=signal, now_ms=lambda: self.now,
            id_factory=lambda label: label + "-generated", sleep=sleep,
        )

    @staticmethod
    async def blocked_sleeper(delay):
        await asyncio.Event().wait()

    async def wait_for_pending_waiter(self, signal):
        for _ in range(1000):
            wait_tasks = tuple(
                candidate for candidate in asyncio.all_tasks()
                if not candidate.done()
                and getattr(candidate.get_coro(), "__qualname__", "") == "_SignalWaiter.wait"
            )
            if len(wait_tasks) == 1:
                waiter = wait_tasks[0].get_coro().cr_frame.f_locals["self"]
                if waiter._future is not None and waiter._signal is signal:
                    return wait_tasks[0]
            await asyncio.sleep(0)
        self.fail("decision waiter was not pending")

    async def wait_pending(self, approval_id="approval-generated"):
        for _ in range(1000):
            record = await ApprovalRepository(self.storage).get(approval_id)
            if record is not None:
                return record
            await asyncio.sleep(0)
        self.fail("PENDING approval was not published")

    async def test_terminalizer_due_and_zero_clock(self):
        await self.seed_pending("due")
        self.now = 1000
        before = self.clock_calls
        due = await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            "due", target_state=ApprovalState.EXPIRED
        )
        self.assertIs(ApprovalState.EXPIRED, due.state)
        self.assertEqual(1, self.clock_calls - before)

    async def test_terminalizer_not_due_is_state_conflict(self):
        await self.seed_pending("not-due")
        self.now = 500
        before = self.clock_calls
        with self.assertRaises(Exception) as raised:
            await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
                "not-due", target_state=ApprovalState.EXPIRED
            )
        self.assertEqual("state_conflict", str(raised.exception))
        self.assertEqual(1, self.clock_calls - before)
        self.assertIs(ApprovalState.PENDING, (await ApprovalRepository(self.storage).get("not-due")).state)

    async def test_terminalizer_cancels_live_running_approval(self):
        await self.seed_pending("live")
        before = self.clock_calls
        cancelled = await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            "live", target_state=ApprovalState.CANCELLED
        )
        self.assertIs(ApprovalState.CANCELLED, cancelled.state)
        self.assertEqual(1, self.clock_calls - before)

    async def test_terminalizer_existing_terminal_has_zero_clock_and_callback_is_not_consumed(self):
        running, _ = await self.seed_pending("approval", display=True)
        callbacks = await self.approval_callbacks()
        allow_hash = callbacks["Allow"]
        consumed = lambda: self.storage.read(lambda c: c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?",
            (__import__("hashlib").sha256(allow_hash.encode()).hexdigest(),),
        ).fetchone()[0])
        self.assertIsNone(await consumed())
        self.now = 100
        await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "allow", allow_hash))
        self.assertIs(ApprovalState.APPROVED, (await ApprovalRepository(self.storage).get("approval")).state)
        before = self.clock_calls
        same = await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            "approval", target_state=ApprovalState.CANCELLED
        )
        self.assertIs(ApprovalState.APPROVED, same.state)
        self.assertEqual(0, self.clock_calls - before)

        await TransientPayloadRepository(self.storage, now_ms=self.clock).create(
            payload_id="denied-payload", dialogue_id="dialogue", job_id="job",
            kind=TransientPayloadKind.APPROVAL, content=b"safe details", expires_at_ms=1000,
        )
        await ApprovalRepository(self.storage, now_ms=self.clock).create_pending(
            approval_id="denied", profile_id="profile-a", wire_request_id="denied-wire",
            kind=ApprovalKind.COMMAND_EXECUTION, job_id="job",
            expected_job_version=running.version, display_payload_id="denied-payload",
            expires_at_ms=1000,
        )
        callbacks = await self.approval_callbacks("denied")
        await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "deny", callbacks["Deny"]))
        before = self.clock_calls
        same = await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            "denied", target_state=ApprovalState.EXPIRED
        )
        self.assertIs(ApprovalState.DENIED, same.state)
        self.assertEqual(0, self.clock_calls - before)
        self.assertIsNotNone(await consumed())

    async def test_later_callback_cannot_revive_cancelled_approval(self):
        await self.seed_pending("approval", display=True)
        callbacks = await self.approval_callbacks()
        await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            "approval", target_state=ApprovalState.CANCELLED
        )
        result = await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "late", callbacks["Allow"]))
        self.assertIn(result.status, (PrivateControlStatus.STALE, PrivateControlStatus.ALREADY_USED))
        self.assertIs(ApprovalState.CANCELLED, (await ApprovalRepository(self.storage).get("approval")).state)

    async def test_operator_publishes_pending_safe_payload_and_empty_details_are_deny_only(self):
        await self.seed_running()
        gate = asyncio.Event()
        async def sleeper(delay):
            self.assertEqual(900.0, delay)
            await gate.wait()
        signal = ApprovalDecisionSignal()
        operator = self.operator(signal, sleeper)
        task = asyncio.create_task(operator.decide(ApprovalRequest(
            1, "profile-a", "wire", ApprovalKind.COMMAND_EXECUTION,
            "thread", "turn", "item", ("line one", "line two"),
        )))
        record = await self.wait_pending()
        self.assertIs(ApprovalState.PENDING, record.state)
        self.assertEqual(900000, record.expires_at_ms - record.created_at_ms)
        payload = await TransientPayloadRepository(self.storage).get(record.display_payload_id)
        self.assertEqual(b"line one\nline two", payload.content)
        gate.set()
        self.now = record.expires_at_ms
        self.assertIs(ApprovalDecision.DENY, await task)
        self.assertIs(ApprovalState.EXPIRED, (await ApprovalRepository(self.storage).get(record.approval_id)).state)

    async def test_operator_empty_context_creates_no_payload_and_malformed_input_denies_before_publication(self):
        await self.seed_running()
        signal = ApprovalDecisionSignal()
        gate = asyncio.Event()

        async def sleeper(delay):
            await gate.wait()

        operator = self.operator(signal, sleeper)
        result = await operator.decide(ApprovalRequest(
            1, "wrong", "wire", ApprovalKind.COMMAND_EXECUTION,
            "thread", "turn", "item", (),
        ))
        self.assertIs(ApprovalDecision.DENY, result)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]))
        task = asyncio.create_task(operator.decide(ApprovalRequest(
            1, "profile-a", "wire", ApprovalKind.COMMAND_EXECUTION,
            "thread", "turn", "item", (),
        )))
        record = await self.wait_pending()
        self.assertIsNone(record.display_payload_id)
        await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(
            record.approval_id, target_state=ApprovalState.CANCELLED
        )
        signal.notify()
        self.assertIs(ApprovalDecision.DENY, await task)

    async def protocol_client(self):
        transport = _Transport()
        client = CodexProtocolClient(transport, client_version="test")
        init = asyncio.create_task(client.initialize())
        await asyncio.sleep(0)
        transport.incoming.put_nowait(json.dumps({
            "id": 1, "result": {"userAgent": "x", "codexHome": "/safe", "platformFamily": "unix", "platformOs": "linux"}
        }))
        await init
        return transport, client

    async def start_owned(self, method, params, *, sleep=None):
        transport, client = await self.protocol_client()
        signal = ApprovalDecisionSignal()
        operator = self.operator(signal, self.blocked_sleeper if sleep is None else sleep)
        service = OwnedApprovalResponseService("profile-a", client, operator)
        transport.incoming.put_nowait(json.dumps({"id": "wire", "method": method, "params": params}))
        await asyncio.sleep(0)
        inbound = await client.next_server_request()
        task = asyncio.create_task(service.handle_owned(inbound))
        await self.wait_pending()
        await self.wait_for_pending_waiter(signal)
        return transport, client, signal, service, inbound, task

    async def test_failed_async_expiry_stays_pending_then_real_allow_responds_once(self):
        await self.seed_running()

        async def failing_sleeper(delay):
            self.assertEqual(900.0, delay)
            raise RuntimeError("synthetic")

        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
            sleep=failing_sleeper,
        )
        operator = service._operator
        expiry_calls = 0
        original_terminalize = operator._terminalize_expired

        async def counted_terminalize(approval_id):
            nonlocal expiry_calls
            expiry_calls += 1
            return await original_terminalize(approval_id)

        with patch.object(operator, "_terminalize_expired", counted_terminalize):
            for _ in range(1000):
                expiry_tasks = tuple(
                    candidate for candidate in asyncio.all_tasks()
                    if not candidate.done()
                    and getattr(candidate.get_coro(), "__qualname__", "")
                    == "DurableApprovalOperator._sleep_expiry"
                )
                if not expiry_tasks:
                    break
                await asyncio.sleep(0)
            self.assertEqual((), expiry_tasks)
            self.assertIs(ApprovalState.PENDING, (await ApprovalRepository(self.storage).get("approval-generated")).state)
            self.assertEqual(0, expiry_calls)
            self.assertFalse(task.done())
            self.assertEqual([], [message for message in transport.sent if message.get("id") == "wire"])

            callbacks = await self.approval_callbacks()
            await self.service.handle_callback(
                PrivateCallbackRequest(12, 7, 7, "allow", callbacks["Allow"])
            )
            signal.notify()
            result = await asyncio.wait_for(task, 2)
            self.assertIs(ApprovalHandlingStatus.ALLOWED, result.status)
            self.assertIs(
                ApprovalState.APPROVED,
                (await ApprovalRepository(self.storage).get("approval-generated")).state,
            )
            self.assertEqual(1, len([message for message in transport.sent if message.get("id") == "wire"]))
            self.assertEqual([], [message for message in transport.sent if message.get("result") == {"decision": "decline"}])
            self.assertEqual(set(), signal._waiters)
            self.assertEqual(
                [],
                [
                    candidate for candidate in asyncio.all_tasks()
                    if not candidate.done()
                    and getattr(getattr(candidate.get_coro(), "cr_code", None), "co_filename", "")
                    .endswith("codex_control/application/live_approval.py")
                ],
            )
        await client.close()

    async def test_failed_async_expiry_then_protocol_terminal_cancels_without_response(self):
        await self.seed_running()

        async def failing_sleeper(delay):
            self.assertEqual(900.0, delay)
            raise RuntimeError("synthetic")

        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
            sleep=failing_sleeper,
        )
        operator = service._operator
        expiry_calls = 0

        async def counted_terminalize(approval_id):
            nonlocal expiry_calls
            expiry_calls += 1
            return await DurableApprovalOperator._terminalize_expired(operator, approval_id)

        with patch.object(operator, "_terminalize_expired", counted_terminalize):
            for _ in range(1000):
                expiry_tasks = tuple(
                    candidate for candidate in asyncio.all_tasks()
                    if not candidate.done()
                    and getattr(candidate.get_coro(), "__qualname__", "")
                    == "DurableApprovalOperator._sleep_expiry"
                )
                if not expiry_tasks:
                    break
                await asyncio.sleep(0)
            self.assertEqual((), expiry_tasks)
            self.assertIs(ApprovalState.PENDING, (await ApprovalRepository(self.storage).get("approval-generated")).state)
            self.assertEqual(0, expiry_calls)
            self.assertFalse(task.done())
            self.assertEqual([], [message for message in transport.sent if message.get("id") == "wire"])

            transport.incoming.put_nowait(None)
            done, _ = await asyncio.wait({task}, timeout=2)
            self.assertEqual({task}, done)
            result = await task
            self.assertIs(ApprovalHandlingStatus.RESPONSE_UNKNOWN, result.status)
            self.assertEqual([], [message for message in transport.sent if message.get("id") == "wire"])
            self.assertIs(
                ApprovalState.CANCELLED,
                (await ApprovalRepository(self.storage).get("approval-generated")).state,
            )
            self.assertEqual(set(), signal._waiters)
            self.assertEqual(
                [],
                [
                    candidate for candidate in asyncio.all_tasks()
                    if not candidate.done()
                    and getattr(getattr(candidate.get_coro(), "cr_code", None), "co_filename", "")
                    .endswith("codex_control/application/live_approval.py")
                ],
            )
        await client.close()

    async def test_real_allow_and_deny_are_exact_one_method_specific_response(self):
        await self.seed_running()
        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
        )
        callbacks = await self.approval_callbacks()
        await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "allow", callbacks["Allow"]))
        signal.notify()
        result = await asyncio.wait_for(task, 2)
        self.assertIs(ApprovalHandlingStatus.ALLOWED, result.status)
        self.assertEqual(1, len([m for m in transport.sent if m.get("id") == "wire"]))
        self.assertEqual({"decision": "accept"}, [m for m in transport.sent if m.get("id") == "wire"][0]["result"])
        await client.close()

        await self.asyncTearDown()
        await self.asyncSetUp()
        await self.seed_running()
        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
        )
        callbacks = await self.approval_callbacks()
        await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "deny", callbacks["Deny"]))
        signal.notify()
        result = await asyncio.wait_for(task, 2)
        self.assertIs(ApprovalHandlingStatus.DENIED, result.status)
        self.assertEqual({"decision": "decline"}, [m for m in transport.sent if m.get("id") == "wire"][0]["result"])
        await client.close()

    async def test_callback_and_expiry_orderings_have_one_durable_winner(self):
        await self.seed_running()
        gate = asyncio.Event()
        signal = ApprovalDecisionSignal()

        async def sleeper(delay):
            await gate.wait()

        task = asyncio.create_task(self.operator(signal, sleeper).decide(ApprovalRequest(
            1, "profile-a", "wire", ApprovalKind.COMMAND_EXECUTION, "thread", "turn", "item", ("safe",)
        )))
        record = await self.wait_pending()
        await ApprovalRepository(self.storage, now_ms=self.clock).terminalize_pending(record.approval_id, target_state=ApprovalState.CANCELLED)
        signal.notify()
        self.assertIs(ApprovalDecision.DENY, await task)
        gate.set()

    async def test_outer_cancellation_is_shielded_and_protocol_terminal_is_unknown_with_cleanup(self):
        await self.seed_running()
        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
        )
        task.cancel()
        await asyncio.sleep(0)
        callbacks = await self.approval_callbacks()
        await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "allow", callbacks["Allow"]))
        signal.notify()
        result = await asyncio.wait_for(task, 2)
        self.assertIs(ApprovalHandlingStatus.ALLOWED, result.status)
        self.assertEqual(1, len([m for m in transport.sent if m.get("id") == "wire"]))
        await client.close()

    async def test_operator_cancellation_joins_wake_task_and_cancels_pending(self):
        await self.seed_running()
        signal = ApprovalDecisionSignal()

        operator = self.operator(signal, self.blocked_sleeper)
        task = asyncio.create_task(operator.decide(ApprovalRequest(
            1, "profile-a", "wire", ApprovalKind.COMMAND_EXECUTION,
            "thread", "turn", "item", ("safe",),
        )))
        record = await self.wait_pending()
        wake_task = await self.wait_for_pending_waiter(signal)
        self.assertIs(ApprovalState.PENDING, record.state)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(wake_task.done())
        self.assertEqual(set(), signal._waiters)
        self.assertIs(ApprovalState.CANCELLED, (await ApprovalRepository(self.storage).get(record.approval_id)).state)

    async def test_protocol_terminal_is_unknown_with_pending_cleanup(self):
        await self.seed_running()
        transport, client, signal, service, inbound, task = await self.start_owned(
            "item/commandExecution/requestApproval",
            {"itemId": "item", "startedAtMs": 1, "threadId": "thread", "turnId": "turn", "reason": "safe"},
        )
        wake_tasks = tuple(
            candidate for candidate in asyncio.all_tasks()
            if not candidate.done()
            and getattr(candidate.get_coro(), "__qualname__", "") == "_SignalWaiter.wait"
        )
        self.assertEqual(1, len(wake_tasks))
        wake_task = wake_tasks[0]
        wake_waiter = wake_task.get_coro().cr_frame.f_locals["self"]
        self.assertIsNotNone(wake_waiter._future)
        self.assertEqual(1, len(signal._waiters))
        expiry_tasks = tuple(
            candidate for candidate in asyncio.all_tasks()
            if not candidate.done()
            and getattr(candidate.get_coro(), "__qualname__", "") == "DurableApprovalOperator._sleep_expiry"
        )
        self.assertEqual(1, len(expiry_tasks))
        expiry_task = expiry_tasks[0]
        transport.incoming.put_nowait(None)
        done, _ = await asyncio.wait({task}, timeout=2)
        self.assertTrue(done)
        result = await task
        self.assertIs(ApprovalHandlingStatus.RESPONSE_UNKNOWN, result.status)
        self.assertEqual([], [m for m in transport.sent if m.get("id") == "wire"])
        self.assertIs(ApprovalState.CANCELLED, (await ApprovalRepository(self.storage).get("approval-generated")).state)
        self.assertTrue(wake_task.done())
        self.assertTrue(expiry_task.done())
        self.assertEqual(set(), signal._waiters)
        self.assertEqual(
            [],
            [
                candidate for candidate in asyncio.all_tasks()
                if not candidate.done()
                and getattr(getattr(candidate.get_coro(), "cr_code", None), "co_filename", "").endswith(
                    "codex_control/application/live_approval.py"
                )
            ],
        )
        await client.close()

    async def test_restart_new_client_rejects_same_wire_value_without_replay(self):
        await self.seed_running()
        old_transport, old_client = await self.protocol_client()
        old_transport.incoming.put_nowait(json.dumps({
            "id": "same-wire",
            "method": "item/commandExecution/requestApproval",
            "params": {
                "itemId": "item", "startedAtMs": 1,
                "threadId": "thread", "turnId": "turn", "reason": "safe",
            },
        }))
        await asyncio.sleep(0)
        old_inbound = await old_client.next_server_request()
        self.assertTrue(old_client.owns_server_request(old_inbound))
        signal = ApprovalDecisionSignal()
        operator = self.operator(signal, self.blocked_sleeper)
        service = OwnedApprovalResponseService("profile-a", old_client, operator)
        old_task = asyncio.create_task(service.handle_owned(old_inbound))
        old_record = await self.wait_pending("approval-generated")
        self.assertIs(ApprovalState.PENDING, old_record.state)
        self.assertIsNotNone(old_record.display_payload_id)
        self.assertTrue(old_client.owns_server_request(old_inbound))
        await old_client.close()
        old_result = await asyncio.wait_for(old_task, 2)
        self.assertIs(ApprovalHandlingStatus.RESPONSE_UNKNOWN, old_result.status)
        self.assertEqual([], [m for m in old_transport.sent if m.get("id") == "same-wire"])
        self.assertIs(ApprovalState.CANCELLED, (await ApprovalRepository(self.storage).get(old_record.approval_id)).state)

        await self.storage.close()
        self.storage = await SqliteStorage.open(self.database_path, now_ms=self.clock)
        persisted = await ApprovalRepository(self.storage).get(old_record.approval_id)
        self.assertIsNotNone(persisted)
        self.assertIs(ApprovalState.CANCELLED, persisted.state)

        new_transport, new_client = await self.protocol_client()
        self.assertFalse(new_client.owns_server_request(old_inbound))
        reconstructed = InboundServerRequest(
            old_inbound.local_sequence,
            old_inbound.request_id,
            old_inbound.method,
            old_inbound._params,
        )
        self.assertFalse(new_client.owns_server_request(reconstructed))
        new_signal = ApprovalDecisionSignal()
        new_operator = self.operator(new_signal, self.blocked_sleeper)
        new_service = OwnedApprovalResponseService("profile-a", new_client, new_operator)
        with self.assertRaises(Exception):
            await new_service.handle_owned(old_inbound)
        with self.assertRaises(Exception):
            await new_service.handle_owned(reconstructed)
        self.assertEqual([], [m for m in new_transport.sent if m.get("id") == "same-wire"])
        await new_client.close()


if __name__ == "__main__":
    unittest.main()
