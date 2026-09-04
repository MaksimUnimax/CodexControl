import asyncio
import json
from pathlib import Path
import unittest

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter, MAX_THREAD_ID_CHARS, ThreadBinding,
    ThreadLifecycleError, ThreadOperationStatus, TrustedWorkingDirectory,
)


def catalog(profile="p", generation=1):
    descriptor = CodexModelDescriptor("visible-id", "wire-model", "Visible", ("low", "high"), "low", True, False)
    return CodexModelCatalog(profile, generation, (descriptor,), 0.0, 60.0)


class Client:
    def __init__(self, responses=None, gate=None):
        self.responses = list(responses or [])
        self.gate = gate
        self.calls = []
        self.dispatched = asyncio.Event()

    async def request(self, method, params):
        self.calls.append((method, dict(params)))
        self.dispatched.set()
        if self.gate is not None:
            await self.gate.wait()
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class Runtime:
    def __init__(self, profile_id, generation, client):
        self.profile_id, self.generation, self.client = profile_id, generation, client


class Manager:
    def __init__(self, runtimes):
        self.runtimes = runtimes
        self.calls = []

    async def acquire(self, profile_id):
        self.calls.append(profile_id)
        return self.runtimes[profile_id]


class Catalog:
    def __init__(self, values):
        self.values = values
        self.calls = []

    async def get_catalog(self, profile_id):
        self.calls.append(profile_id)
        return self.values[profile_id]


class FixtureTests(unittest.TestCase):
    def test_schema_bound_start_and_resume_fixtures(self):
        root = Path("tests/fixtures/codex_app_server_0_144_6")
        start = json.loads((root / "thread_start_protocol.json").read_text())
        resume = json.loads((root / "thread_resume_protocol.json").read_text())
        for fixture in (start, resume):
            self.assertEqual(fixture["codex_version"], "0.144.6")
            self.assertEqual(fixture["schema_sha256"], "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466")
            self.assertEqual(fixture["result_thread_id_path"], ["thread", "id"])
        self.assertEqual(start["sent_parameter_fields"], ["cwd", "approvalPolicy", "sandbox", "model", "ephemeral"])
        self.assertIsNone(start["typed_reasoning_effort_field"])
        self.assertTrue(start["config_additional_properties"])
        self.assertEqual(resume["sent_parameter_fields"], ["threadId"])


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = Client([{"thread": {"id": "thread-1", "turns": ["private"]}}])
        self.manager = Manager({"p": Runtime("p", 1, self.client), "q": Runtime("q", 1, Client([{"thread": {"id": "thread-q"}}]))})
        self.catalog = Catalog({"p": catalog(), "q": catalog("q")})
        self.adapter = CodexThreadLifecycleAdapter(self.manager, self.catalog)
        self.cwd = TrustedWorkingDirectory("/trusted/workspace")

    async def test_start_uses_exact_wire_model_validates_default_effort_and_omits_config(self):
        result = await self.adapter.start("p", model_id="visible-id", reasoning_effort=None, working_directory=self.cwd)
        self.assertEqual(result.status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual(result.binding, ThreadBinding("p", "thread-1"))
        self.assertEqual((result.model_id, result.reasoning_effort), ("visible-id", "low"))
        self.assertEqual(self.client.calls, [("thread/start", {"cwd": "/trusted/workspace", "approvalPolicy": "on-request", "sandbox": "workspace-write", "model": "wire-model", "ephemeral": False})])
        self.assertNotIn("config", self.client.calls[0][1])
        self.assertNotIn("reasoningEffort", self.client.calls[0][1])

    async def test_selection_and_generation_fail_before_thread_start_dispatch(self):
        for model_id, effort in (("hidden", None), ("visible-id", "unsupported")):
            with self.subTest(model_id=model_id, effort=effort):
                with self.assertRaises(Exception):
                    await self.adapter.start("p", model_id=model_id, reasoning_effort=effort, working_directory=self.cwd)
                self.assertEqual(self.client.calls, [])
        self.catalog.values["p"] = catalog(generation=2)
        with self.assertRaisesRegex(ThreadLifecycleError, "runtime_catalog_generation_mismatch"):
            await self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(self.client.calls, [])

    async def test_start_rejected_unknown_and_malformed_success_never_retry(self):
        self.client.responses = [ProtocolRemoteError(400)]
        rejected = await self.adapter.start("p", model_id="visible-id", reasoning_effort="high", working_directory=self.cwd)
        self.assertEqual(rejected.status, ThreadOperationStatus.START_REJECTED)
        self.assertEqual(rejected.error.category, CodexAdapterErrorCategory.REMOTE_APP_SERVER_ERROR)
        self.client.responses = [ProtocolFault("eof_pending")]
        unknown = await self.adapter.start("p", model_id="visible-id", reasoning_effort="high", working_directory=self.cwd)
        self.assertEqual(unknown.status, ThreadOperationStatus.START_UNKNOWN)
        self.client.responses = [{"thread": {"id": "x" * (MAX_THREAD_ID_CHARS + 1), "history": "SECRET"}}]
        malformed = await self.adapter.start("p", model_id="visible-id", reasoning_effort="high", working_directory=self.cwd)
        self.assertEqual(malformed.status, ThreadOperationStatus.START_UNKNOWN)
        self.assertIsNone(malformed.binding)
        self.assertEqual(len(self.client.calls), 3)

    async def test_resume_uses_owner_exact_id_and_confirms_returned_id(self):
        self.client.responses = [{"thread": {"id": "thread-1", "turns": ["PRIVATE"]}}]
        binding = ThreadBinding("p", "thread-1")
        result = await self.adapter.resume(binding)
        self.assertEqual(result.status, ThreadOperationStatus.RESUME_CONFIRMED)
        self.assertEqual(self.client.calls, [("thread/resume", {"threadId": "thread-1"})])
        self.client.responses = [{"thread": {"id": "different"}}]
        mismatch = await self.adapter.resume(binding)
        self.assertEqual(mismatch.status, ThreadOperationStatus.RESUME_UNKNOWN)

    async def test_resume_rejected_unknown_and_caller_cancellation_keeps_dispatched_task_owned(self):
        self.client.responses = [ProtocolRemoteError(403)]
        rejected = await self.adapter.resume(ThreadBinding("p", "thread-1"))
        self.assertEqual(rejected.status, ThreadOperationStatus.RESUME_REJECTED)
        self.client.responses = [ProtocolFault("eof_pending")]
        unknown = await self.adapter.resume(ThreadBinding("p", "thread-1"))
        self.assertEqual(unknown.status, ThreadOperationStatus.RESUME_UNKNOWN)

        gate = asyncio.Event()
        client = Client([{"thread": {"id": "thread-1"}}], gate)
        self.manager.runtimes["p"] = Runtime("p", 1, client)
        caller = asyncio.create_task(self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
        await client.dispatched.wait()
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        with self.assertRaisesRegex(ThreadLifecycleError, "profile_lifecycle_busy"):
            await self.adapter.resume(ThreadBinding("p", "thread-1"))
        gate.set()
        completed = await self.adapter.await_inflight("p")
        self.assertEqual(completed.status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual(len(client.calls), 1)

    async def test_different_profiles_are_independent_and_inputs_are_bounded(self):
        p_gate, q_gate = asyncio.Event(), asyncio.Event()
        p = Client([{"thread": {"id": "p"}}], p_gate)
        q = Client([{"thread": {"id": "q"}}], q_gate)
        self.manager.runtimes.update({"p": Runtime("p", 1, p), "q": Runtime("q", 1, q)})
        first = asyncio.create_task(self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
        second = asyncio.create_task(self.adapter.start("q", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
        await asyncio.gather(p.dispatched.wait(), q.dispatched.wait())
        p_gate.set(); q_gate.set()
        self.assertEqual((await first).status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual((await second).status, ThreadOperationStatus.START_CONFIRMED)
        for value in ("relative", "/bad\0path", "/" + "x" * 4097):
            with self.subTest(value=value[:10]):
                with self.assertRaisesRegex(ThreadLifecycleError, "working_directory_invalid"):
                    TrustedWorkingDirectory(value)
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_id_invalid"):
            ThreadBinding("p", "x" * (MAX_THREAD_ID_CHARS + 1))
