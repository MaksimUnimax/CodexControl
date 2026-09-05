import asyncio
import unittest

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    CodexTurnLifecycleAdapter,
    TurnInterruptStatus,
    TurnStartStatus,
    TurnTerminalStatus,
)


class FakeClient:
    def __init__(self, responses):
        self.responses = dict(responses)
        self.calls = []
        self.interrupt_called = asyncio.Event()
        self.interrupt_release = asyncio.Event()
        self.notifications = asyncio.Queue()
        self.terminal = asyncio.Event()
        self._notification_consumers = 0
        self.max_concurrent_notification_consumers = 0

    async def request(self, method, params):
        self.calls.append((method, dict(params)))
        if method == "turn/interrupt":
            self.interrupt_called.set()
            await self.interrupt_release.wait()
        response = self.responses[method]
        if isinstance(response, BaseException):
            raise response
        return response

    async def next_notification(self):
        self._notification_consumers += 1
        self.max_concurrent_notification_consumers = max(
            self.max_concurrent_notification_consumers,
            self._notification_consumers,
        )
        try:
            return await self.notifications.get()
        finally:
            self._notification_consumers -= 1

    async def wait_terminal(self):
        await self.terminal.wait()


class FakeRuntime:
    def __init__(self, profile_id, generation, client):
        self.profile_id = profile_id
        self.generation = generation
        self.client = client


class FakeManager:
    def __init__(self, runtimes):
        self.runtimes = list(runtimes)
        self.calls = []

    async def acquire(self, profile_id):
        self.calls.append(profile_id)
        if profile_id != "p":
            raise AssertionError("unrelated profile was acquired")
        return self.runtimes[len(self.calls) - 1]


class FakeCatalog:
    def __init__(self):
        self.calls = []
        self.value = CodexModelCatalog(
            "p",
            1,
            (CodexModelDescriptor("model-p", "wire-model-p", "Model P", ("low", "high"), "high", True, False),),
            0.0,
            60.0,
        )

    async def get_catalog(self, profile_id):
        self.calls.append(profile_id)
        return self.value


def terminal_event(binding, status="completed"):
    return {
        "method": "turn/completed",
        "params": {"threadId": binding.thread_id, "turn": {"id": binding.turn_id, "status": status}},
    }


class P110T1Acceptance(unittest.IsolatedAsyncioTestCase):
    async def test_integrated_lifecycle_preserves_runtime_ownership_and_exact_wire(self):
        client_a = FakeClient({
            "thread/start": {"thread": {"id": "thread-P1-10"}},
            "turn/start": {"turn": {"id": "turn-P1-10"}},
            "turn/interrupt": {},
        })
        client_b = FakeClient({"thread/delete": {}})
        unrelated = FakeClient({"unexpected": {}})
        runtime_a = FakeRuntime("p", 1, client_a)
        runtime_b = FakeRuntime("p", 2, client_b)
        manager = FakeManager([runtime_a, runtime_a, runtime_b])
        catalog = FakeCatalog()
        thread_adapter = CodexThreadLifecycleAdapter(manager, catalog)
        turn_adapter = CodexTurnLifecycleAdapter(manager, catalog)
        cwd = TrustedWorkingDirectory("/safe/p1-10")

        thread_result = await thread_adapter.start(
            "p",
            model_id="model-p",
            reasoning_effort="high",
            working_directory=cwd,
        )
        self.assertEqual(thread_result.status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual(thread_result.binding, ThreadBinding("p", "thread-P1-10"))
        thread_binding = thread_result.binding
        assert thread_binding is not None
        self.assertEqual(client_a.calls, [(
            "thread/start",
            {
                "cwd": "/safe/p1-10",
                "approvalPolicy": "on-request",
                "sandbox": "workspace-write",
                "model": "wire-model-p",
                "ephemeral": False,
            },
        )])

        turn_result = await turn_adapter.start_turn(
            thread_binding=thread_binding,
            model_id="model-p",
            reasoning_effort="low",
            user_text="P1.10 integrated fake prompt",
            working_directory=cwd,
        )
        self.assertEqual(turn_result.status, TurnStartStatus.CONFIRMED)
        turn_binding = turn_result.binding
        assert turn_binding is not None
        self.assertEqual(turn_binding.thread_id, "thread-P1-10")
        self.assertEqual(turn_binding.turn_id, "turn-P1-10")
        self.assertEqual(client_a.calls[1], (
            "turn/start",
            {
                "threadId": "thread-P1-10",
                "input": [{"type": "text", "text": "P1.10 integrated fake prompt"}],
                "model": "wire-model-p",
                "effort": "low",
                "cwd": "/safe/p1-10",
                "approvalPolicy": "on-request",
                "sandboxPolicy": {"type": "workspaceWrite"},
            },
        ))
        self.assertEqual(manager.calls, ["p", "p"])
        self.assertEqual(catalog.calls, ["p", "p"])

        interrupt_task = asyncio.create_task(turn_adapter.interrupt_turn(turn_binding))
        await client_a.interrupt_called.wait()
        self.assertEqual(manager.calls, ["p", "p"])
        self.assertEqual(client_a.calls[2], (
            "turn/interrupt",
            {"threadId": "thread-P1-10", "turnId": "turn-P1-10"},
        ))
        await client_a.notifications.put(terminal_event(turn_binding))
        client_a.interrupt_release.set()
        interrupt_result = await interrupt_task
        self.assertEqual(interrupt_result.status, TurnInterruptStatus.CONFIRMED)
        self.assertIs(interrupt_result.terminal_result.binding, turn_binding)
        self.assertEqual(interrupt_result.terminal_result.status, TurnTerminalStatus.COMPLETED)
        self.assertEqual(manager.calls, ["p", "p"])
        self.assertEqual(client_a.max_concurrent_notification_consumers, 1)

        terminal_result = await turn_adapter.wait_turn(turn_binding)
        self.assertIs(terminal_result, interrupt_result.terminal_result)
        delete_result = await thread_adapter.delete(binding=thread_binding)
        self.assertEqual(delete_result.status, ThreadOperationStatus.DELETE_CONFIRMED)
        self.assertIs(delete_result.binding, thread_binding)
        self.assertEqual(manager.calls, ["p", "p", "p"])
        self.assertEqual(client_b.calls, [("thread/delete", {"threadId": "thread-P1-10"})])
        self.assertEqual(catalog.calls, ["p", "p"])

        self.assertEqual([method for method, _ in client_a.calls], [
            "thread/start", "turn/start", "turn/interrupt",
        ])
        self.assertEqual([method for method, _ in client_b.calls], ["thread/delete"])
        self.assertEqual(unrelated.calls, [])
        self.assertEqual(sum(method == "thread/start" for method, _ in client_a.calls), 1)
        self.assertEqual(sum(method == "turn/start" for method, _ in client_a.calls), 1)
        self.assertEqual(sum(method == "turn/interrupt" for method, _ in client_a.calls), 1)
        self.assertEqual(sum(method == "thread/delete" for method, _ in client_b.calls), 1)


if __name__ == "__main__":
    unittest.main()
