import asyncio
import json
import unittest
from pathlib import Path

from codex_control.adapters.codex.capabilities import SCHEMA_SHA256
from codex_control.adapters.codex.errors import CodexAdapterError, CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnBinding,
    AgentMessageCompleted,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnLifecycleError,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
    TURN_START_METHOD,
    TURN_INTERRUPT_METHOD,
)

def terminal_event(binding: TurnBinding, status: str) -> dict:
    return {
        "method": "turn/completed",
        "params": {
            "threadId": binding.thread_id,
            "turn": {"id": binding.turn_id, "status": status},
        },
    }


class TestCatalog:
    def __init__(self, profile: str = "p", generation: int = 1):
        self.profile = profile
        self.generation = generation

    @staticmethod
    def build(profile: str, generation: int) -> CodexModelCatalog:
        return CodexModelCatalog(
            profile,
            generation,
            (
                CodexModelDescriptor(
                    "chosen",
                    "wire-model",
                    "shown",
                    ("low", "high"),
                    "high",
                    True,
                    False,
                ),
            ),
            0,
            1,
        )

    async def get_catalog(self, profile: str) -> CodexModelCatalog:
        return self.build(profile, self.generation)


class FakeClient:
    def __init__(
        self,
        response=None,
        *,
        request_gate: asyncio.Event | None = None,
        interrupt_gate: asyncio.Event | None = None,
        next_notification_raises: Exception | None = None,
    ):
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.events = asyncio.Queue()
        self.hit = asyncio.Event()
        self.terminal = asyncio.Event()
        self.response = {"turn": {"id": "T"}} if response is None else response
        self.request_gate = request_gate
        self.interrupt_gate = interrupt_gate
        self.next_notification_calls = 0
        self._next_notification_in_flight = 0
        self.max_concurrent_notification_consumers = 0
        self.next_notification_raises = next_notification_raises
        self.before_request_hook = None

    async def request(self, method: str, params: dict[str, object]):
        self.calls.append((method, params))
        if self.before_request_hook is not None:
            self.before_request_hook(method, params)
        self.hit.set()
        if self.request_gate is not None:
            await self.request_gate.wait()
        if method == TURN_INTERRUPT_METHOD and self.interrupt_gate is not None:
            await self.interrupt_gate.wait()

        response = self.response
        if isinstance(response, list):
            response = response.pop(0)
        if callable(response):
            response = response(method, params)
            if asyncio.iscoroutine(response):
                response = await response
        if isinstance(response, BaseException):
            raise response
        return response

    async def next_notification(self):
        self.next_notification_calls += 1
        self._next_notification_in_flight += 1
        self.max_concurrent_notification_consumers = max(
            self.max_concurrent_notification_consumers, self._next_notification_in_flight
        )
        try:
            if self.next_notification_raises is not None:
                raise self.next_notification_raises
            return await self.events.get()
        finally:
            self._next_notification_in_flight -= 1

    async def wait_terminal(self):
        await self.terminal.wait()


class Runtime:
    def __init__(self, profile: str = "p", generation: int = 1, client: FakeClient | None = None, *, repr_text: str | None = None):
        self.profile_id = profile
        self.generation = generation
        self.client = client or FakeClient()
        self.repr_text = repr_text

    def __repr__(self) -> str:
        return self.repr_text or f"Runtime(profile={self.profile_id!r}, generation={self.generation})"


class Manager:
    def __init__(self, *runtimes: Runtime):
        self.runtimes = list(runtimes)
        self.calls = 0

    async def acquire(self, profile: str) -> Runtime:
        self.calls += 1
        index = min(self.calls - 1, len(self.runtimes) - 1)
        return self.runtimes[index]


class GateAdapter(CodexTurnLifecycleAdapter):
    def __init__(self, manager: Manager, catalog: TestCatalog, entered: asyncio.Event, released: asyncio.Event):
        super().__init__(manager, catalog)
        self._entered = entered
        self._released = released

    async def _before_interrupt_dispatch(self) -> None:
        self._entered.set()
        await self._released.wait()


class Tests(unittest.IsolatedAsyncioTestCase):
    async def make_active(self, *, runtime: Runtime | None = None, manager: Manager | None = None, profile: str = "p") -> tuple[CodexTurnLifecycleAdapter, Runtime, TurnBinding]:
        runtime = runtime or Runtime(profile=profile)
        manager = manager or Manager(runtime)
        adapter = CodexTurnLifecycleAdapter(manager, TestCatalog(profile))
        result = await adapter.start_turn(
            thread_binding=ThreadBinding(profile, "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="hello",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        self.assertEqual(result.status, TurnStartStatus.CONFIRMED)
        assert result.binding is not None
        return adapter, runtime, result.binding

    async def finish(self, binding: TurnBinding, client: FakeClient, status: str = "completed") -> None:
        await client.events.put(terminal_event(binding, status))

    def test_fixture_exact_with_additional_properties(self):
        fixture = json.loads((Path(__file__).parents[1] / "fixtures/codex_app_server_0_144_6/turn_interrupt_protocol.json").read_text())
        expected = {
            "codex_version": "0.144.6",
            "schema_sha256": SCHEMA_SHA256,
            "turn_interrupt_method": "turn/interrupt",
            "request_schema_name": "TurnInterruptParams",
            "request_json_type": "object",
            "request_properties": ["threadId", "turnId"],
            "required_fields": ["threadId", "turnId"],
            "request_additional_properties": True,
            "thread_id_field": "threadId",
            "thread_id_type": "string",
            "thread_id_nullable": False,
            "thread_id_min_length": None,
            "turn_id_field": "turnId",
            "turn_id_type": "string",
            "turn_id_nullable": False,
            "turn_id_min_length": None,
            "response_schema_name": "TurnInterruptResponse",
            "response_json_type": "object",
            "response_properties": [],
            "response_required_fields": [],
            "response_additional_properties": True,
            "startup_empty_turn_id_schema_fact": "string permits empty value; product does not expose startup interruption",
            "product_startup_interrupt_allowed": False,
            "behavioral_semantics_source": "exact Codex 0.144.6 / ADR-0015",
            "normal_interrupt_response_terminal_correlated": True,
            "terminal_reconciliation_source": "existing P1.6 collector",
        }
        self.assertEqual(fixture, expected)

    async def test_cancelled_collector_maps_to_unknown(self):
        adapter, runtime, binding = await self.make_active()
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        adapter._collectors[binding].cancel()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual((result.status, result.error.category), (TurnInterruptStatus.UNKNOWN, CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN))

    async def test_cancelled_collector_exception_maps_to_unknown(self):
        runtime = Runtime(client=FakeClient({"turn": {"id": "T"}}, next_notification_raises=RuntimeError("PRIVATE_RUNTIME_MUST_NOT_LEAK")))
        adapter, runtime, binding = await self.make_active(runtime=runtime)
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.UNKNOWN)
        rendered = f"{result!r}{result!s}{result.error!r}{result.error!s}"
        self.assertNotIn("PRIVATE_RUNTIME_MUST_NOT_LEAK", rendered)

    async def test_active_turn_repr_redacts_runtime_and_token(self):
        runtime = Runtime(
            client=FakeClient(response={"turn": {"id": "T"}}),
            repr_text="Runtime PRIVATE_RUNTIME_MUST_NOT_LEAK /private/CODEX_HOME /private/cwd",
        )
        adapter, runtime, binding = await self.make_active(runtime=runtime)
        active = adapter._active_turns[binding]
        active_repr = repr(active)
        self.assertNotIn("PRIVATE_RUNTIME_MUST_NOT_LEAK", active_repr)
        self.assertNotIn("/private/CODEX_HOME", active_repr)
        self.assertNotIn("/private/cwd", active_repr)

        runtime.client.response = {"unknown": True}
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        await self.finish(binding, runtime.client, "bad")
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.UNKNOWN)

    async def test_interrupt_not_active_matrix_zero_rpc(self):
        profile_runtime = Runtime(profile="p", client=FakeClient(response=[{"turn": {"id": "T"}}, {"turn": {"id": "T2"}}]))
        adapter, runtime, active = await self.make_active(runtime=profile_runtime)

        other_runtime = Runtime(profile="q", client=FakeClient(response={"turn": {"id": "Q"}}))
        other_adapter, _, other = await self.make_active(runtime=other_runtime, profile="q")

        await self.finish(active, runtime.client)
        await adapter.wait_turn(active)
        newer = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="again",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        call_base_count = len(runtime.client.calls)
        invalid_and_stale = [
            ("invalid_public_argument", 123),
            ("reconstructed", TurnBinding("p", "Thread-A", active.turn_id)),
            ("reconstructed-live", TurnBinding("p", "Thread-A", newer.binding.turn_id)),
            ("different-turn", TurnBinding("p", "Thread-A", "other")),
            ("foreign-profile", TurnBinding("q", active.thread_id, active.turn_id)),
            ("foreign-thread", TurnBinding("p", "Other", active.turn_id)),
            ("other-adapter", other),
            ("completed-old", active),
            ("stale-after-newer", active),
        ]

        for _name, candidate in invalid_and_stale:
            with self.subTest(_name):
                expected = (
                    CodexAdapterErrorCategory.TURN_REQUEST_INVALID
                    if isinstance(candidate, int)
                    else CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE
                )
                with self.assertRaises(TurnLifecycleError) as raised:
                    await adapter.interrupt_turn(candidate)
                self.assertEqual(raised.exception.category, expected)
                self.assertEqual(len(runtime.client.calls), call_base_count)
                self.assertNotIn(("p", "Thread-A"), adapter._interrupts)
        await self.finish(newer.binding, runtime.client)
        await adapter.wait_turn(newer.binding)
        await self.finish(other, other_runtime.client)
        await other_adapter.wait_turn(other)

    async def test_interrupt_uses_exact_runtime_and_no_reacquire(self):
        primary = Runtime("p", 1, FakeClient(response={"turn": {"id": "T"}}))
        secondary = Runtime("p", 2, FakeClient(response={"turn": {"id": "R"}}))
        manager = Manager(primary, secondary)
        adapter = CodexTurnLifecycleAdapter(manager, TestCatalog("p"))
        start = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="x",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        self.assertEqual(start.status, TurnStartStatus.CONFIRMED)
        task = asyncio.create_task(adapter.interrupt_turn(start.binding))
        await primary.client.hit.wait()
        await self.finish(start.binding, primary.client)
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)
        self.assertEqual(manager.calls, 1)
        self.assertEqual(start.binding.turn_id, primary.client.calls[1][1]["turnId"])
        self.assertEqual([], secondary.client.calls)

    async def test_interrupt_request_shape_exact(self):
        client = FakeClient(response={"turn": {"id": "T"}})
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client)
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(client.calls[1], ("turn/interrupt", {"threadId": binding.thread_id, "turnId": binding.turn_id}))
        self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)

    async def test_confirmed_matrix(self):
        for status in ("completed", "failed"):
            with self.subTest(status=status):
                client = FakeClient(response={"turn": {"id": "T"}})
                adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
                collector = adapter._collectors[binding]
                task = asyncio.create_task(adapter.interrupt_turn(binding))
                await client.hit.wait()
                await self.finish(binding, client, status)
                result = await asyncio.wait_for(task, 1)
                terminal = await collector
                self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)
                self.assertEqual(result.terminal_result, terminal)
                expected = TurnTerminalStatus.COMPLETED if status == "completed" else TurnTerminalStatus.FAILED
                self.assertEqual(result.terminal_result.status, expected)

    async def test_success_with_unknown_terminal(self):
        client = FakeClient(response={"turn": {"id": "T"}})
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client, "bad")
        result = await asyncio.wait_for(task, 1)
        self.assertEqual((result.status, result.error.category), (TurnInterruptStatus.UNKNOWN, CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN))

    async def run_ambiguity_case(self, ambiguity: object, collector_status: str, expected: TurnInterruptStatus):
        client = FakeClient(response={"turn": {"id": "T"}})
        runtime = Runtime(client=client)
        manager = Manager(runtime)
        adapter = CodexTurnLifecycleAdapter(manager, TestCatalog("p"))
        result = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="x",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        self.assertEqual(result.status, TurnStartStatus.CONFIRMED)
        assert result.binding is not None
        binding = result.binding
        client.response = ambiguity
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client, collector_status)
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, expected)
        self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)

    async def test_ambiguity_matrix(self):
        for ambiguity in (ProtocolFault("PRIVATE_PROTOCOL_FAULT_MUST_NOT_LEAK"), OSError("PRIVATE_TRANSPORT_MUST_NOT_LEAK"), asyncio.CancelledError("PRIVATE_REQUEST_CANCEL_MUST_NOT_LEAK"), None, "", 7, []):
            await self.run_ambiguity_case(ambiguity, "completed", TurnInterruptStatus.RECONCILED)
            await self.run_ambiguity_case(ambiguity, "failed", TurnInterruptStatus.RECONCILED)
            await self.run_ambiguity_case(ambiguity, "bad", TurnInterruptStatus.UNKNOWN)

    async def test_schema_valid_empty_and_extra_object_success_are_not_malformed(self):
        for response in ({}, {"futureField": "allowed-by-schema"}):
            with self.subTest(response=response):
                client = FakeClient(response=[{"turn": {"id": "T"}}, response])
                adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
                task = asyncio.create_task(adapter.interrupt_turn(binding))
                await runtime.client.hit.wait()
                await self.finish(binding, runtime.client)
                result = await asyncio.wait_for(task, 1)
                self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)
                self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)

    async def test_malformed_success_discards_raw_response(self):
        raw = "PRIVATE_INTERRUPT_RESPONSE_MUST_NOT_LEAK"
        client = FakeClient(response=[{"turn": {"id": "T"}}, raw])
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        await self.finish(binding, runtime.client, "bad")
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.UNKNOWN)
        self.assertNotIn(raw, str(result) + repr(result))
        self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)

    async def test_remote_rejection_matrix(self):
        # non definitive -> rejected
        client = FakeClient(response=[{"turn": {"id": "T"}}, ProtocolRemoteError(9876)])
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        client.hit.clear()
        await runtime.client.hit.wait()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual((result.status, result.error.category, result.error.remote_code), (TurnInterruptStatus.REJECTED, CodexAdapterErrorCategory.TURN_INTERRUPT_REJECTED, 9876))
        self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)
        self.assertFalse(task.cancelled())
        await self.finish(binding, runtime.client)
        await adapter.wait_turn(binding)

        for status in ("completed", "failed"):
            block = asyncio.Event()
            async def blocked_remote_reject(method: str, params: dict[str, object]) -> ProtocolRemoteError:
                await block.wait()
                return ProtocolRemoteError(9876)
            client = FakeClient(response=[{"turn": {"id": "T"}}, blocked_remote_reject])
            adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
            task = asyncio.create_task(adapter.interrupt_turn(binding))
            client.hit.clear()
            await runtime.client.hit.wait()
            await self.finish(binding, runtime.client, status)
            collector = adapter._collectors[binding]
            await asyncio.wait_for(collector, 1)
            block.set()
            result = await asyncio.wait_for(task, 1)
            self.assertEqual(result.status, TurnInterruptStatus.RECONCILED)
            self.assertEqual(result.terminal_result.status, TurnTerminalStatus.COMPLETED if status == "completed" else TurnTerminalStatus.FAILED)
            self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)

    async def test_rejection_returns_without_waiting_for_active_collector(self):
        client = FakeClient(response=[{"turn": {"id": "T"}}, ProtocolRemoteError(9876)])
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual((result.status, result.error.remote_code), (TurnInterruptStatus.REJECTED, 9876))
        self.assertIn(binding, adapter._collectors)
        await self.finish(binding, runtime.client)
        await adapter.wait_turn(binding)

    async def test_pre_dispatch_cancellation(self):
        entered = asyncio.Event()
        released = asyncio.Event()
        client = FakeClient(response={"turn": {"id": "T"}})
        runtime = Runtime("p", 1, client)
        adapter = GateAdapter(Manager(runtime), TestCatalog("p"), entered, released)
        start = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="x",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        task = asyncio.create_task(adapter.interrupt_turn(start.binding))
        await entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(len(client.calls), 1)
        self.assertFalse(any(method == TURN_INTERRUPT_METHOD for method, _ in client.calls))
        self.assertNotIn(("p", "Thread-A"), adapter._interrupts)
        released.set()
        self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 0)

        retry_task = asyncio.create_task(adapter.interrupt_turn(start.binding))
        await self.finish(start.binding, client)
        retry = await retry_task
        self.assertEqual(retry.status, TurnInterruptStatus.CONFIRMED)

    async def test_post_dispatch_cancel_matrix(self):
        matrix = [
            ("success", {"turn": {"id": "T"}}, "completed", TurnInterruptStatus.CONFIRMED),
            ("rejected-active", ProtocolRemoteError(9876), None, TurnInterruptStatus.REJECTED),
            ("protocol", ProtocolFault("x"), "completed", TurnInterruptStatus.RECONCILED),
            ("protocol", ProtocolFault("x"), "failed", TurnInterruptStatus.RECONCILED),
            ("protocol", ProtocolFault("x"), "bad", TurnInterruptStatus.UNKNOWN),
            ("rejected", ProtocolRemoteError(9876), "bad", TurnInterruptStatus.REJECTED),
        ]
        for name, response, terminal_state, expected in matrix:
            with self.subTest(name=name, terminal=terminal_state):
                interrupt_gate = asyncio.Event()
                client = FakeClient(response=[{"turn": {"id": "T"}}, response], interrupt_gate=interrupt_gate)
                adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
                task = asyncio.create_task(adapter.interrupt_turn(binding))
                client.hit.clear()
                await runtime.client.hit.wait()
                task.cancel(); task.cancel()
                self.assertFalse(task.done())
                with self.assertRaises(TurnLifecycleError) as raised:
                    await adapter.interrupt_turn(binding)
                self.assertEqual(raised.exception.category, CodexAdapterErrorCategory.TURN_INTERRUPT_BUSY)
                if terminal_state is not None:
                    await self.finish(binding, runtime.client, terminal_state)
                interrupt_gate.set()
                result = await asyncio.wait_for(task, 1)
                self.assertEqual(result.status, expected)
                self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)
                if terminal_state is None:
                    await self.finish(binding, runtime.client)
                    await adapter.wait_turn(binding)

    async def test_response_before_terminal_waits_for_terminal(self):
        client = FakeClient(response={"turn": {"id": "T"}})
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        self.assertFalse(task.done())
        await self.finish(binding, client, "completed")
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)

    async def test_terminal_before_response(self):
        gate = asyncio.Event()
        async def block_interrupt(method:str, params:dict[str,object]) -> dict[str, object]:
            if method == TURN_INTERRUPT_METHOD:
                await gate.wait()
            return {"turn": {"id": "T"}}
        client = FakeClient(response=[{"turn": {"id": "T"}}, block_interrupt])
        runtime = Runtime(client=client)
        adapter, _, binding = await self.make_active(runtime=runtime)
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client, "completed")
        self.assertFalse(task.done())
        gate.set()
        result = await asyncio.wait_for(task, 1)
        self.assertEqual(result.status, TurnInterruptStatus.CONFIRMED)

    async def test_shared_collector_and_single_notification_consumer(self):
        client = FakeClient(response={"turn": {"id": "T"}})
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        wait_task = asyncio.create_task(adapter.wait_turn(binding))
        int_task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client, "completed")
        result = await asyncio.wait_for(int_task, 1)
        terminal = await wait_task
        self.assertIs(result.terminal_result, terminal)
        self.assertEqual(client.max_concurrent_notification_consumers, 1)
        self.assertEqual(client.next_notification_calls, 1)

    async def test_inner_request_cancelled_classification(self):
        for terminal_status, expected in (("completed", TurnInterruptStatus.RECONCILED), ("bad", TurnInterruptStatus.UNKNOWN)):
            client = FakeClient(response=[{"turn": {"id": "T"}}, asyncio.CancelledError("PRIVATE_REQUEST_CANCELLED_MUST_NOT_LEAK")])
            adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
            task = asyncio.create_task(adapter.interrupt_turn(binding))
            await runtime.client.hit.wait()
            await self.finish(binding, runtime.client, terminal_status)
            result = await asyncio.wait_for(task, 1)
            self.assertEqual(result.status, expected)
            self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 1)

    async def test_stale_interrupt_release_token_identity(self):
        adapter, runtime, binding = await self.make_active()
        key = (binding.profile_id, binding.thread_id)
        stale = object()
        live = object()
        adapter._interrupts[key] = live
        await adapter._release_interrupt(key, stale)
        self.assertIs(adapter._interrupts[key], live)

    async def test_new_turn_not_released_by_old_interrupt_cleanup(self):
        gate = asyncio.Event()
        async def block_interrupt(method:str, params:dict[str,object]) -> dict[str, object]:
            if method == TURN_INTERRUPT_METHOD:
                await gate.wait()
            return {"turn": {"id": "T"}}
        client = FakeClient(response=[{"turn": {"id": "T"}}, block_interrupt, {"turn": {"id": "T2"}}, block_interrupt])
        runtime = Runtime("p", 1, client)
        adapter = CodexTurnLifecycleAdapter(Manager(runtime), TestCatalog("p"))

        first = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="first",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        first_task = asyncio.create_task(adapter.interrupt_turn(first.binding))
        await client.hit.wait()
        await self.finish(first.binding, client, "completed")
        await adapter.wait_turn(first.binding)

        second = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="second",
            working_directory=TrustedWorkingDirectory("/safe"),
        )

        key = ("p", "Thread-A")
        reservation_a = adapter._interrupts[key]
        reservation_b = object()
        adapter._interrupts[key] = reservation_b
        self.assertIs(adapter._interrupts[key], reservation_b)
        gate.set()
        final = await asyncio.wait_for(first_task, 1)
        self.assertEqual(final.status, TurnInterruptStatus.CONFIRMED)
        await adapter._release_interrupt(key, reservation_a)
        self.assertIs(adapter._interrupts[key], reservation_b)
        self.assertIs(adapter._active_turns[second.binding].binding, second.binding)
        self.assertIn(second.binding, adapter._collectors)

        await adapter._release_interrupt(key, reservation_b)
        client.hit.clear()
        await self.finish(second.binding, client, "bad")
        result = await adapter.interrupt_turn(second.binding)
        self.assertEqual(result.status, TurnInterruptStatus.UNKNOWN)
        interrupt_calls = [call for call in client.calls if call[0] == TURN_INTERRUPT_METHOD]
        self.assertEqual([call[1]["turnId"] for call in interrupt_calls], [first.binding.turn_id, second.binding.turn_id])

    async def test_guard_clears_for_all_finite_results(self):
        cases = (
            ({"turn": {"id": "T"}}, "completed", TurnInterruptStatus.CONFIRMED),
            (ProtocolFault("fault"), "completed", TurnInterruptStatus.RECONCILED),
            (ProtocolRemoteError(9876), None, TurnInterruptStatus.REJECTED),
            ({"turn": {"id": "T"}}, "bad", TurnInterruptStatus.UNKNOWN),
        )
        for response, terminal_status, expected in cases:
            with self.subTest(expected=expected):
                client = FakeClient(response=[{"turn": {"id": "T"}}, response])
                adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
                task = asyncio.create_task(adapter.interrupt_turn(binding))
                await runtime.client.hit.wait()
                if terminal_status is not None:
                    await self.finish(binding, runtime.client, terminal_status)
                result = await asyncio.wait_for(task, 1)
                self.assertEqual(result.status, expected)
                self.assertNotIn((binding.profile_id, binding.thread_id), adapter._interrupts)
                if terminal_status is None:
                    await self.finish(binding, runtime.client)
                    await adapter.wait_turn(binding)

    async def test_guard_clears_and_reuses_after_pre_dispatch_cancel(self):
        entered = asyncio.Event()
        released = asyncio.Event()
        client = FakeClient(response={"turn": {"id": "T"}})
        runtime = Runtime(client=client)
        adapter = GateAdapter(Manager(runtime), TestCatalog("p"), entered, released)
        start = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-A"), model_id="chosen",
            reasoning_effort=None, user_text="hello",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        first = asyncio.create_task(adapter.interrupt_turn(start.binding))
        await entered.wait()
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertNotIn(("p", "Thread-A"), adapter._interrupts)
        self.assertEqual(sum(method == TURN_INTERRUPT_METHOD for method, _ in client.calls), 0)
        released.set()
        second = asyncio.create_task(adapter.interrupt_turn(start.binding))
        await self.finish(start.binding, client)
        self.assertEqual((await second).status, TurnInterruptStatus.CONFIRMED)

    async def test_different_profile_independence(self):
        client_p = FakeClient(response={"turn": {"id": "P"}})
        client_q = FakeClient(response={"turn": {"id": "Q"}})
        adapter = CodexTurnLifecycleAdapter(Manager(Runtime("p", 1, client_p), Runtime("q", 1, client_q)), TestCatalog("p"))

        first = await adapter.start_turn(
            thread_binding=ThreadBinding("p", "Thread-p"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="x",
            working_directory=TrustedWorkingDirectory("/safe"),
        )
        second = await adapter.start_turn(
            thread_binding=ThreadBinding("q", "Thread-q"),
            model_id="chosen",
            reasoning_effort=None,
            user_text="x",
            working_directory=TrustedWorkingDirectory("/safe"),
        )

        p_task = asyncio.create_task(adapter.interrupt_turn(first.binding))
        q_task = asyncio.create_task(adapter.interrupt_turn(second.binding))
        await asyncio.gather(client_p.hit.wait(), client_q.hit.wait())
        await self.finish(first.binding, client_p)
        await self.finish(second.binding, client_q)
        p_result, q_result = await asyncio.gather(p_task, q_task)
        self.assertEqual((p_result.status, q_result.status), (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.CONFIRMED))
        self.assertEqual(len(client_p.calls) - 1, 1)
        self.assertEqual(len(client_q.calls) - 1, 1)
        self.assertEqual(client_p.calls[0][0], TURN_START_METHOD)
        self.assertEqual(client_q.calls[0][0], TURN_START_METHOD)
        self.assertEqual((client_p.calls[1][1]["threadId"], client_p.calls[1][1]["turnId"]), (first.binding.thread_id, first.binding.turn_id))
        self.assertEqual((client_q.calls[1][1]["threadId"], client_q.calls[1][1]["turnId"]), (second.binding.thread_id, second.binding.turn_id))

    async def test_reconnect_redaction_matrix(self):
        client = FakeClient(
            response=[{"turn": {"id": "T"}}, ProtocolFault("PRIVATE_REMOTE_ERROR_MUST_NOT_LEAK")],
            next_notification_raises=RuntimeError("PRIVATE_RUNTIME_MUST_NOT_LEAK"),
        )
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await runtime.client.hit.wait()
        await self.finish(binding, runtime.client, "bad")
        result = await asyncio.wait_for(task, 1)
        rendered = f"{result!r}{result!s}{result.error!r}{result.error!s}"
        for token in (
            "PRIVATE_REMOTE_ERROR_MUST_NOT_LEAK",
            "PRIVATE_RUNTIME_MUST_NOT_LEAK",
            "/private/CODEX_HOME",
            "/private/cwd",
            "PRIVATE_USER_PROMPT_MUST_NOT_LEAK",
            "PRIVATE_REASONING_MUST_NOT_LEAK",
        ):
            self.assertNotIn(token, rendered)

    def test_generic_interrupt_result_redacts_payloads_and_errors(self):
        binding = TurnBinding("safe-profile", "safe-thread", "safe-turn")
        terminal = TurnTerminalResult(
            binding,
            TurnTerminalStatus.COMPLETED,
            (
                AgentMessageCompleted(1, "safe-item", "PRIVATE_USER_PROMPT_MUST_NOT_LEAK"),
                AgentMessageCompleted(2, "safe-item-2", "PRIVATE_REASONING_MUST_NOT_LEAK"),
            ),
        )
        result = TurnInterruptResult(TurnInterruptStatus.CONFIRMED, binding, terminal, CodexAdapterError(CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN))
        rendered = str(result) + repr(result)
        for token in (
            "PRIVATE_INTERRUPT_RESPONSE_MUST_NOT_LEAK",
            "PRIVATE_REMOTE_ERROR_MUST_NOT_LEAK",
            "PRIVATE_RUNTIME_MUST_NOT_LEAK",
            "PRIVATE_USER_PROMPT_MUST_NOT_LEAK",
            "PRIVATE_REASONING_MUST_NOT_LEAK",
            "/private/CODEX_HOME",
            "/private/cwd",
        ):
            self.assertNotIn(token, rendered)

    async def test_post_interrupt_matrix_reuse_after_result(self):
        client = FakeClient(response={"turn": {"id": "T"}})
        adapter, runtime, binding = await self.make_active(runtime=Runtime(client=client))
        task = asyncio.create_task(adapter.interrupt_turn(binding))
        await client.hit.wait()
        await self.finish(binding, client)
        await asyncio.wait_for(task, 1)
        self.assertNotIn(("p", "Thread-A"), adapter._interrupts)
        # if still active impossible after confirmation; this is explicit guard cleanup check


if __name__ == "__main__":
    unittest.main()
