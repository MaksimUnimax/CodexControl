import asyncio
import json
from pathlib import Path
import unittest

from codex_control.adapters.codex.errors import CodexAdapterError, CodexAdapterErrorCategory
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


class SequencedManager:
    def __init__(self, *runtimes):
        self.runtimes = list(runtimes)
        self.calls = []

    async def acquire(self, profile_id):
        self.calls.append(profile_id)
        return self.runtimes.pop(0)


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
        self.assertEqual(resume["sent_parameter_fields"], ["threadId", "cwd", "approvalPolicy", "sandbox"])

    def test_thread_lifecycle_error_is_finite_and_safe(self):
        categories = (
            CodexAdapterErrorCategory.THREAD_REQUEST_INVALID,
            CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED,
            CodexAdapterErrorCategory.THREAD_OPERATION_BUSY,
            CodexAdapterErrorCategory.THREAD_START_REJECTED,
            CodexAdapterErrorCategory.THREAD_START_UNKNOWN,
            CodexAdapterErrorCategory.THREAD_RESUME_REJECTED,
            CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN,
        )
        for category in categories:
            self.assertEqual(ThreadLifecycleError(category).category, category)
        unsafe = ThreadLifecycleError("remote text /private/cwd and payload")
        self.assertEqual(unsafe.category, CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        self.assertNotIn("/private", repr(unsafe))


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
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_precondition_changed"):
            await self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(self.client.calls, [])

    async def test_start_rejected_unknown_and_malformed_success_never_retry(self):
        self.client.responses = [ProtocolRemoteError(400)]
        rejected = await self.adapter.start("p", model_id="visible-id", reasoning_effort="high", working_directory=self.cwd)
        self.assertEqual(rejected.status, ThreadOperationStatus.START_REJECTED)
        self.assertEqual(rejected.error.category, CodexAdapterErrorCategory.THREAD_START_REJECTED)
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
        result = await self.adapter.resume(binding=binding, working_directory=self.cwd)
        self.assertEqual(result.status, ThreadOperationStatus.RESUME_CONFIRMED)
        self.assertEqual(self.client.calls, [("thread/resume", {"threadId": "thread-1", "cwd": "/trusted/workspace", "approvalPolicy": "on-request", "sandbox": "workspace-write"})])
        self.client.responses = [{"thread": {"id": "different"}}]
        mismatch = await self.adapter.resume(binding=binding, working_directory=self.cwd)
        self.assertEqual(mismatch.status, ThreadOperationStatus.RESUME_UNKNOWN)

    async def test_resume_rejected_unknown_and_caller_cancellation_keeps_dispatched_task_owned(self):
        self.client.responses = [ProtocolRemoteError(403)]
        rejected = await self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)
        self.assertEqual(rejected.status, ThreadOperationStatus.RESUME_REJECTED)
        self.client.responses = [ProtocolFault("eof_pending")]
        unknown = await self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)
        self.assertEqual(unknown.status, ThreadOperationStatus.RESUME_UNKNOWN)

        gate = asyncio.Event()
        client = Client([{"thread": {"id": "thread-1"}}], gate)
        self.manager.runtimes["p"] = Runtime("p", 1, client)
        caller = asyncio.create_task(self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
        await client.dispatched.wait()
        caller.cancel()
        self.assertFalse(caller.done())
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
            await self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)
        gate.set()
        completed = await caller
        self.assertEqual(completed.status, ThreadOperationStatus.START_CONFIRMED)
        self.assertEqual(len(client.calls), 1)

    async def test_post_dispatch_cancellation_is_owned_for_start_and_resume_terminal_results(self):
        for method, response, expected in (
            ("start", {"thread": {"id": "thread-1"}}, ThreadOperationStatus.START_CONFIRMED),
            ("start", ProtocolRemoteError(401), ThreadOperationStatus.START_REJECTED),
            ("start", ProtocolFault("lost"), ThreadOperationStatus.START_UNKNOWN),
            ("resume", {"thread": {"id": "thread-1"}}, ThreadOperationStatus.RESUME_CONFIRMED),
            ("resume", ProtocolRemoteError(401), ThreadOperationStatus.RESUME_REJECTED),
            ("resume", ProtocolFault("lost"), ThreadOperationStatus.RESUME_UNKNOWN),
        ):
            with self.subTest(method=method, expected=expected):
                gate, client = asyncio.Event(), Client([response], None)
                # A manual gate after observation makes cancellation ordering exact.
                client.gate = gate
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                if method == "start":
                    caller = asyncio.create_task(self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
                else:
                    caller = asyncio.create_task(self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
                await client.dispatched.wait()
                caller.cancel(); caller.cancel()
                self.assertFalse(caller.done())
                self.assertEqual(len(client.calls), 1)
                gate.set()
                self.assertEqual((await caller).status, expected)
                self.assertNotIn("p", self.adapter._inflight)

    async def test_pre_dispatch_cancellation_never_sends_and_releases_guard(self):
        gate = asyncio.Event()
        entered = asyncio.Event()
        class GatedCatalog(Catalog):
            async def get_catalog(inner, profile_id):
                entered.set()
                await gate.wait()
                return await super(GatedCatalog, inner).get_catalog(profile_id)
        adapter = CodexThreadLifecycleAdapter(self.manager, GatedCatalog(self.catalog.values))
        caller = asyncio.create_task(adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd))
        await entered.wait()
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        gate.set()
        self.assertEqual(self.client.calls, [])
        self.assertNotIn("p", adapter._inflight)
        result = await adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(result.status, ThreadOperationStatus.START_CONFIRMED)

    async def test_inner_cancellation_is_unknown_and_guard_reusable(self):
        class CancelClient(Client):
            async def request(inner, method, params):
                inner.calls.append((method, dict(params)))
                inner.dispatched.set()
                raise asyncio.CancelledError()
        client = CancelClient()
        self.manager.runtimes["p"] = Runtime("p", 1, client)
        result = await self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(result.status, ThreadOperationStatus.START_UNKNOWN)
        self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_START_UNKNOWN)
        self.assertNotIn("p", self.adapter._inflight)

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
                with self.assertRaisesRegex(ThreadLifecycleError, "thread_request_invalid"):
                    TrustedWorkingDirectory(value)
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_request_invalid"):
            ThreadBinding("p", "x" * (MAX_THREAD_ID_CHARS + 1))

    async def test_start_captures_one_runtime_and_generation_change_never_rebases(self):
        first_client, later_client = Client([{"thread": {"id": "first"}}]), Client([{"thread": {"id": "later"}}])
        manager = SequencedManager(Runtime("p", 10, first_client), Runtime("p", 11, later_client))
        adapter = CodexThreadLifecycleAdapter(manager, Catalog({"p": catalog("p", 11)}))
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_precondition_changed"):
            await adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(manager.calls, ["p"])
        self.assertEqual(first_client.calls, [])
        self.assertEqual(later_client.calls, [])

    async def test_start_dispatches_on_the_exact_captured_runtime(self):
        captured, hypothetical = Client([{"thread": {"id": "captured"}}]), Client([{"thread": {"id": "later"}}])
        manager = SequencedManager(Runtime("p", 10, captured), Runtime("p", 11, hypothetical))
        adapter = CodexThreadLifecycleAdapter(manager, Catalog({"p": catalog("p", 10)}))
        result = await adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(result.binding, ThreadBinding("p", "captured"))
        self.assertEqual(manager.calls, ["p"])
        self.assertEqual(len(captured.calls), 1)
        self.assertEqual(hypothetical.calls, [])

    async def test_captured_runtime_profile_mismatch_fails_before_dispatch(self):
        client = Client([{"thread": {"id": "never"}}])
        manager = SequencedManager(Runtime("wrong-profile", 1, client))
        adapter = CodexThreadLifecycleAdapter(manager, Catalog({"p": catalog("p", 1)}))
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_precondition_changed"):
            await adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(manager.calls, ["p"])
        self.assertEqual(client.calls, [])

    async def test_start_success_id_matrix_preserves_opaque_value_and_marks_malformed_unknown(self):
        opaque = "Thread-AbC  123"
        client = Client([{"thread": {"id": opaque, "history": "PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK", "turn": "PRIVATE_TURN_CONTENT_MUST_NOT_LEAK"}}])
        self.manager.runtimes["p"] = Runtime("p", 1, client)
        result = await self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
        self.assertEqual(result.binding, ThreadBinding("p", opaque))
        rendered = repr(result) + repr(result.binding)
        self.assertNotIn("PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK", rendered)
        self.assertNotIn("PRIVATE_TURN_CONTENT_MUST_NOT_LEAK", rendered)
        errors_rendered = (
            str(CodexAdapterError(CodexAdapterErrorCategory.THREAD_START_UNKNOWN))
            + repr(CodexAdapterError(CodexAdapterErrorCategory.THREAD_START_UNKNOWN))
            + str(ThreadLifecycleError("PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK"))
            + repr(ThreadLifecycleError("PRIVATE_TURN_CONTENT_MUST_NOT_LEAK"))
        )
        self.assertNotIn("PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK", errors_rendered)
        self.assertNotIn("PRIVATE_TURN_CONTENT_MUST_NOT_LEAK", errors_rendered)
        malformed = (None, 123, {}, [], "", "x" * (MAX_THREAD_ID_CHARS + 1), "abc\0def")
        for value in malformed:
            with self.subTest(value=repr(value)[:20]):
                client = Client([{} if value is None else {"thread": {"id": value, "history": "PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK"}}])
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                result = await self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd)
                self.assertEqual(result.status, ThreadOperationStatus.START_UNKNOWN)
                self.assertIsNone(result.binding)
                self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_START_UNKNOWN)
                self.assertEqual(len(client.calls), 1)

    async def test_resume_success_id_matrix_requires_exact_opaque_value(self):
        opaque = "Thread-AbC  123"
        binding = ThreadBinding("p", opaque)
        cases = ((opaque, ThreadOperationStatus.RESUME_CONFIRMED), ("thread-abc  123", ThreadOperationStatus.RESUME_UNKNOWN),
                 ("Thread-AbC 123", ThreadOperationStatus.RESUME_UNKNOWN), (None, ThreadOperationStatus.RESUME_UNKNOWN),
                 (123, ThreadOperationStatus.RESUME_UNKNOWN), ({}, ThreadOperationStatus.RESUME_UNKNOWN), ([], ThreadOperationStatus.RESUME_UNKNOWN),
                 ("", ThreadOperationStatus.RESUME_UNKNOWN), ("x" * (MAX_THREAD_ID_CHARS + 1), ThreadOperationStatus.RESUME_UNKNOWN), ("abc\0def", ThreadOperationStatus.RESUME_UNKNOWN))
        for value, expected in cases:
            with self.subTest(value=repr(value)[:20]):
                response = {} if value is None else {"thread": {"id": value, "history": "PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK", "turn": "PRIVATE_TURN_CONTENT_MUST_NOT_LEAK"}}
                client = Client([response])
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                result = await self.adapter.resume(binding=binding, working_directory=self.cwd)
                self.assertEqual(result.status, expected)
                self.assertEqual(len(client.calls), 1)
                if expected is ThreadOperationStatus.RESUME_UNKNOWN:
                    self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN)
                self.assertNotIn("PRIVATE_THREAD_HISTORY_MUST_NOT_LEAK", repr(result))
                self.assertNotIn("PRIVATE_TURN_CONTENT_MUST_NOT_LEAK", repr(result))

    async def test_remote_rejection_preserves_numeric_code_only(self):
        for operation, status, category, method in (("start", ThreadOperationStatus.START_REJECTED, CodexAdapterErrorCategory.THREAD_START_REJECTED, "thread/start"), ("resume", ThreadOperationStatus.RESUME_REJECTED, CodexAdapterErrorCategory.THREAD_RESUME_REJECTED, "thread/resume")):
            with self.subTest(operation=operation):
                client = Client([ProtocolRemoteError(9876)])
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                result = await (self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd) if operation == "start" else self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
                self.assertEqual((result.status, result.error.category, result.error.remote_code), (status, category, 9876))
                self.assertEqual(client.calls[0][0], method)

    async def test_same_profile_busy_matrix(self):
        for first_kind, second_kind in (("start", "start"), ("start", "resume"), ("resume", "resume")):
            with self.subTest(first=first_kind, second=second_kind):
                gate = asyncio.Event()
                client = Client([{"thread": {"id": "thread-1"}}], gate)
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                first = asyncio.create_task(self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd) if first_kind == "start" else self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
                await client.dispatched.wait()
                with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
                    await (self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd) if second_kind == "start" else self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
                self.assertEqual(len(client.calls), 1)
                gate.set()
                await first

    async def test_guard_reusable_after_start_and_resume_terminal_outcomes(self):
        scenarios = (("start", {"thread": {"id": "first"}}, ThreadOperationStatus.START_CONFIRMED), ("start", ProtocolRemoteError(4), ThreadOperationStatus.START_REJECTED), ("start", {"thread": {"id": ""}}, ThreadOperationStatus.START_UNKNOWN),
                     ("resume", {"thread": {"id": "thread-1"}}, ThreadOperationStatus.RESUME_CONFIRMED), ("resume", ProtocolRemoteError(5), ThreadOperationStatus.RESUME_REJECTED), ("resume", {"thread": {"id": "different"}}, ThreadOperationStatus.RESUME_UNKNOWN))
        for kind, first_response, expected in scenarios:
            with self.subTest(kind=kind, expected=expected):
                client = Client([first_response, {"thread": {"id": "thread-1"}}])
                self.manager.runtimes["p"] = Runtime("p", 1, client)
                first = await (self.adapter.start("p", model_id="visible-id", reasoning_effort="low", working_directory=self.cwd) if kind == "start" else self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
                self.assertEqual(first.status, expected)
                self.assertNotIn("p", self.adapter._inflight)
                second = await self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)
                self.assertEqual(second.status, ThreadOperationStatus.RESUME_CONFIRMED)
                self.assertEqual(len(client.calls), 2)

    async def test_pre_dispatch_resume_cancellation_sends_no_rpc_and_releases_guard(self):
        entered, gate = asyncio.Event(), asyncio.Event()
        class GatedManager(Manager):
            async def acquire(inner, profile_id):
                entered.set(); await gate.wait()
                return await super(GatedManager, inner).acquire(profile_id)
        manager = GatedManager(self.manager.runtimes)
        adapter = CodexThreadLifecycleAdapter(manager, self.catalog)
        caller = asyncio.create_task(adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd))
        await entered.wait(); caller.cancel()
        with self.assertRaises(asyncio.CancelledError): await caller
        gate.set()
        self.assertEqual(self.client.calls, [])
        self.assertNotIn("p", adapter._inflight)
        self.assertEqual((await adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)).status, ThreadOperationStatus.RESUME_CONFIRMED)

    async def test_resume_inner_cancellation_is_unknown(self):
        class CancelClient(Client):
            async def request(inner, method, params):
                inner.calls.append((method, dict(params))); inner.dispatched.set(); raise asyncio.CancelledError()
        client = CancelClient()
        self.manager.runtimes["p"] = Runtime("p", 1, client)
        result = await self.adapter.resume(binding=ThreadBinding("p", "thread-1"), working_directory=self.cwd)
        self.assertEqual((result.status, result.error.category), (ThreadOperationStatus.RESUME_UNKNOWN, CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN))
        self.assertNotIn("p", self.adapter._inflight)

    async def test_stale_cleanup_token_cannot_remove_replacement_reservation(self):
        old, replacement = object(), object()
        self.adapter._inflight["p"] = replacement
        await self.adapter._release_reservation("p", old)
        self.assertIs(self.adapter._inflight["p"], replacement)
        await self.adapter._release_reservation("p", replacement)
        self.assertNotIn("p", self.adapter._inflight)
