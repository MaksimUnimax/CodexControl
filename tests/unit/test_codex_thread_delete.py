import asyncio
import json
from pathlib import Path
import unittest

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import (
    CodexThreadLifecycleAdapter,
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.errors import normalize_error


def catalog(profile="p", generation=1):
    model = CodexModelDescriptor("visible-id", "wire-model", "Visible", ("low",), "low", True, False)
    return CodexModelCatalog(profile, generation, (model,), 0.0, 60.0)


class DeleteClient:
    def __init__(self, responses=None, gate=None):
        self.responses = list(responses or [])
        self.gate = gate
        self.calls = []
        self.notification_calls = 0
        self.dispatched = asyncio.Event()

    async def request(self, method, params):
        self.calls.append((method, dict(params)))
        self.dispatched.set()
        if self.gate is not None:
            await self.gate.wait()
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    async def next_notification(self):
        self.notification_calls += 1
        raise AssertionError("delete must not consume notifications")


class Runtime:
    def __init__(self, profile_id, client, generation=99):
        self.profile_id = profile_id
        self.generation = generation
        self.client = client


class Manager:
    def __init__(self, runtimes):
        self.runtimes = runtimes
        self.calls = []

    async def acquire(self, profile_id):
        self.calls.append(profile_id)
        return self.runtimes[profile_id]


class CatalogThatMustNotBeCalled:
    async def get_catalog(self, profile_id):
        raise AssertionError("delete must not access the model catalog")


class Catalog:
    async def get_catalog(self, profile_id):
        return catalog(profile_id)


def make_adapter(response, profile="p", client=None, manager=None, catalog_adapter=None):
    client = client or DeleteClient([response])
    manager = manager or Manager({profile: Runtime(profile, client)})
    adapter = CodexThreadLifecycleAdapter(manager, catalog_adapter or CatalogThatMustNotBeCalled())
    return adapter, manager, client


class FixtureTests(unittest.TestCase):
    def test_thread_delete_fixture_matches_every_frozen_field(self):
        path = Path("tests/fixtures/codex_app_server_0_144_6/thread_delete_protocol.json")
        actual = json.loads(path.read_text())
        expected = {
            "codex_version": "0.144.6",
            "schema_sha256": "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466",
            "thread_delete_method": "thread/delete",
            "request_schema_name": "ThreadDeleteParams",
            "request_json_type": "object",
            "request_properties": ["threadId"],
            "required_fields": ["threadId"],
            "request_additional_properties": True,
            "thread_id_field": "threadId",
            "thread_id_type": "string",
            "thread_id_nullable": False,
            "thread_id_min_length": None,
            "response_schema_name": "ThreadDeleteResponse",
            "response_json_type": "object",
            "response_properties": [],
            "response_required_fields": [],
            "response_additional_properties": True,
            "thread_deleted_notification_method": "thread/deleted",
            "thread_deleted_notification_schema": "ThreadDeletedNotification",
            "notification_json_type": "object",
            "notification_properties": ["threadId"],
            "notification_required_fields": ["threadId"],
            "notification_additional_properties": True,
            "exact_version_behavior_source": "exact Codex 0.144.6 / ADR-0016",
            "spawn_subtree_delete": True,
            "loaded_thread_prepare_removal": True,
            "descendants_before_root": True,
            "state_db_delete_after_thread_store": True,
            "response_after_delete_success": True,
            "thread_deleted_notification_after_response": True,
            "partial_side_effect_before_error_possible": True,
            "product_remote_error_status": "DELETE_UNKNOWN",
            "product_notification_reconciliation_used": False,
            "product_read_reconciliation_used": False,
            "product_auto_retry": False,
            "storage_erasure_empirically_proven": False,
            "storage_erasure_proof_deferred_to": "P7",
        }
        self.assertEqual(actual, expected)


class DeleteTests(unittest.IsolatedAsyncioTestCase):
    def binding(self):
        return ThreadBinding("p", "persisted-thread")

    async def test_empty_and_future_object_responses_confirm_exact_binding_and_do_not_notify(self):
        for response in ({}, {"futureField": "ignored"}):
            with self.subTest(response=response):
                adapter, manager, client = make_adapter(response)
                supplied = ThreadBinding("p", "persisted-thread")
                result = await adapter.delete(binding=supplied)
                self.assertIs(result.binding, supplied)
                self.assertEqual(result.status, ThreadOperationStatus.DELETE_CONFIRMED)
                self.assertIsNone(result.error)
                self.assertEqual(manager.calls, ["p"])
                self.assertEqual(client.calls, [("thread/delete", {"threadId": "persisted-thread"})])
                self.assertEqual(client.notification_calls, 0)

    async def test_exact_request_has_only_thread_id_and_delete_does_not_use_catalog(self):
        adapter, _, client = make_adapter({}, catalog_adapter=CatalogThatMustNotBeCalled())
        await adapter.delete(binding=self.binding())
        method, params = client.calls[0]
        self.assertEqual(method, "thread/delete")
        self.assertEqual(params, {"threadId": "persisted-thread"})
        for forbidden in ("profile", "cwd", "model", "effort", "approvalPolicy", "sandbox", "config", "generation", "retry token", "turnId"):
            self.assertNotIn(forbidden, params)

    async def test_delete_has_no_read_or_notification_reconciliation_path(self):
        for response in ({}, ProtocolRemoteError(9876), ProtocolFault("PRIVATE"), None):
            with self.subTest(response=type(response).__name__):
                adapter, _, client = make_adapter(response)
                await adapter.delete(binding=self.binding())
                self.assertEqual(client.notification_calls, 0)
                self.assertEqual([method for method, _ in client.calls], ["thread/delete"])
                self.assertNotIn("thread/read", [method for method, _ in client.calls])
                self.assertNotIn("thread/list", [method for method, _ in client.calls])
                self.assertNotIn("thread/resume", [method for method, _ in client.calls])

    async def test_current_same_profile_runtime_is_allowed_for_reconstructed_binding(self):
        original = ThreadBinding("p", "persisted-thread")
        supplied = ThreadBinding(original.profile_id, original.thread_id)
        client = DeleteClient([{}])
        manager = Manager({"p": Runtime("p", client, generation=7)})
        adapter = CodexThreadLifecycleAdapter(manager, CatalogThatMustNotBeCalled())
        result = await adapter.delete(binding=supplied)
        self.assertIs(result.binding, supplied)
        self.assertEqual(manager.calls, ["p"])
        self.assertEqual(client.calls, [("thread/delete", {"threadId": "persisted-thread"})])

    async def test_runtime_profile_mismatch_fails_before_dispatch(self):
        client = DeleteClient([{}])
        manager = Manager({"p": Runtime("wrong-profile", client)})
        adapter = CodexThreadLifecycleAdapter(manager, CatalogThatMustNotBeCalled())
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_precondition_changed") as raised:
            await adapter.delete(binding=self.binding())
        self.assertEqual(raised.exception.category, CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED)
        self.assertEqual(manager.calls, ["p"])
        self.assertEqual(client.calls, [])

    async def test_same_profile_busy_matrix_uses_existing_reservation_without_queue(self):
        entered, release = asyncio.Event(), asyncio.Event()

        class GatedAdapter(CodexThreadLifecycleAdapter):
            async def _before_delete_dispatch(self):
                entered.set()
                await release.wait()

        client = DeleteClient([{}])
        manager = Manager({"p": Runtime("p", client)})
        adapter = GatedAdapter(manager, Catalog())
        first = asyncio.create_task(adapter.delete(binding=self.binding()))
        await entered.wait()
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
            await adapter.delete(binding=self.binding())
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
            await adapter.start("p", model_id="visible-id", reasoning_effort=None, working_directory=TrustedWorkingDirectory("/trusted/workspace"))
        with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
            await adapter.resume(binding=self.binding(), working_directory=TrustedWorkingDirectory("/trusted/workspace"))
        self.assertEqual(client.calls, [])
        release.set()
        self.assertEqual((await first).status, ThreadOperationStatus.DELETE_CONFIRMED)
        self.assertEqual(len(client.calls), 1)

    async def test_different_profiles_are_independent(self):
        entered = {"p": asyncio.Event(), "q": asyncio.Event()}
        release = asyncio.Event()

        class GatedAdapter(CodexThreadLifecycleAdapter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.entered_count = 0

            async def _before_delete_dispatch(self):
                self.entered_count += 1
                entered["p" if self.entered_count == 1 else "q"].set()
                await release.wait()

        p_client, q_client = DeleteClient([{}]), DeleteClient([{}])
        manager = Manager({"p": Runtime("p", p_client), "q": Runtime("q", q_client)})
        adapter = GatedAdapter(manager, CatalogThatMustNotBeCalled())
        p = asyncio.create_task(adapter.delete(binding=ThreadBinding("p", "p-thread")))
        await entered["p"].wait()
        q = asyncio.create_task(adapter.delete(binding=ThreadBinding("q", "q-thread")))
        await entered["q"].wait()
        release.set()
        self.assertEqual((await p).status, ThreadOperationStatus.DELETE_CONFIRMED)
        self.assertEqual((await q).status, ThreadOperationStatus.DELETE_CONFIRMED)
        self.assertEqual(p_client.calls, [("thread/delete", {"threadId": "p-thread"})])
        self.assertEqual(q_client.calls, [("thread/delete", {"threadId": "q-thread"})])

    async def test_remote_errors_are_unknown_with_only_safe_numeric_code_and_no_retry(self):
        for code in (9876, 1, -1):
            with self.subTest(code=code):
                adapter, _, client = make_adapter(ProtocolRemoteError(code))
                supplied = self.binding()
                result = await adapter.delete(binding=supplied)
                self.assertEqual(result.status, ThreadOperationStatus.DELETE_UNKNOWN)
                self.assertIs(result.binding, supplied)
                self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN)
                self.assertEqual(result.error.remote_code, code)
                self.assertEqual(len(client.calls), 1)
                self.assertNotIn("DELETE_REJECTED", {status.value for status in ThreadOperationStatus})

    async def test_protocol_transport_and_inner_cancellation_are_unknown_redacted_and_not_retried(self):
        cases = (
            ProtocolFault("PRIVATE_DELETE_RESPONSE_MUST_NOT_LEAK"),
            OSError("PRIVATE_THREAD_STORE_PATH_MUST_NOT_LEAK /private/CODEX_HOME /private/thread.jsonl"),
            RuntimeError("PRIVATE_REMOTE_DELETE_ERROR_MUST_NOT_LEAK"),
            asyncio.CancelledError(),
        )
        for source in cases:
            with self.subTest(source=type(source).__name__):
                adapter, _, client = make_adapter(source)
                result = await asyncio.wait_for(adapter.delete(binding=self.binding()), timeout=1)
                rendered = repr(result) + str(result) + repr(result.error) + str(result.error)
                self.assertEqual(result.status, ThreadOperationStatus.DELETE_UNKNOWN)
                self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN)
                self.assertNotIn("PRIVATE_", rendered)
                self.assertNotIn("/private/", rendered)
                self.assertEqual(len(client.calls), 1)

    async def test_malformed_success_types_are_unknown_and_payload_is_discarded(self):
        for response in (None, "string", 123, True, []):
            with self.subTest(response=repr(response)):
                adapter, _, client = make_adapter(response)
                supplied = self.binding()
                result = await adapter.delete(binding=supplied)
                self.assertEqual(result.status, ThreadOperationStatus.DELETE_UNKNOWN)
                self.assertIs(result.binding, supplied)
                self.assertEqual(result.error.category, CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN)
                self.assertEqual(len(client.calls), 1)

    async def test_pre_dispatch_cancellation_is_zero_rpc_and_guard_reusable(self):
        entered, release = asyncio.Event(), asyncio.Event()

        class GatedAdapter(CodexThreadLifecycleAdapter):
            async def _before_delete_dispatch(self):
                entered.set()
                await release.wait()

        client = DeleteClient([{}])
        adapter = GatedAdapter(Manager({"p": Runtime("p", client)}), CatalogThatMustNotBeCalled())
        caller = asyncio.create_task(adapter.delete(binding=self.binding()))
        await entered.wait()
        caller.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await caller
        self.assertEqual(client.calls, [])
        self.assertNotIn("p", adapter._inflight)
        release.set()
        client.responses.append({})
        result = await adapter.delete(binding=self.binding())
        self.assertEqual(result.status, ThreadOperationStatus.DELETE_CONFIRMED)
        self.assertEqual(len(client.calls), 1)

    async def test_post_dispatch_repeated_cancellation_stays_owned_for_all_outcomes(self):
        for response, expected in (({}, ThreadOperationStatus.DELETE_CONFIRMED), (ProtocolRemoteError(9876), ThreadOperationStatus.DELETE_UNKNOWN), (ProtocolFault("PRIVATE"), ThreadOperationStatus.DELETE_UNKNOWN), (OSError("PRIVATE"), ThreadOperationStatus.DELETE_UNKNOWN)):
            with self.subTest(expected=expected):
                gate = asyncio.Event()
                client = DeleteClient([response], gate)
                adapter = CodexThreadLifecycleAdapter(Manager({"p": Runtime("p", client)}), CatalogThatMustNotBeCalled())
                supplied = self.binding()
                caller = asyncio.create_task(adapter.delete(binding=supplied))
                await client.dispatched.wait()
                with self.assertRaisesRegex(ThreadLifecycleError, "thread_operation_busy"):
                    await adapter.delete(binding=self.binding())
                caller.cancel()
                caller.cancel()
                self.assertFalse(caller.done())
                self.assertEqual(len(client.calls), 1)
                gate.set()
                result = await caller
                self.assertEqual(result.status, expected)
                self.assertIs(result.binding, supplied)
                if isinstance(response, ProtocolRemoteError):
                    self.assertEqual(result.error.remote_code, 9876)
                self.assertNotIn("p", adapter._inflight)

    async def test_stale_reservation_token_cannot_release_live_replacement(self):
        stale, live = object(), object()
        adapter, _, _ = make_adapter({}, catalog_adapter=CatalogThatMustNotBeCalled())
        adapter._inflight["p"] = live
        await adapter._release_reservation("p", stale)
        self.assertIs(adapter._inflight["p"], live)
        await adapter._release_reservation("p", live)
        self.assertNotIn("p", adapter._inflight)

    async def test_error_normalization_accepts_delete_unknown_and_remains_fail_closed(self):
        normalized = normalize_error(ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN))
        self.assertEqual(normalized.category, CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN)
        self.assertFalse(hasattr(normalized, "retryable"))
        self.assertFalse(hasattr(normalized, "safe_to_retry"))
        unsafe = ThreadLifecycleError("PRIVATE_DELETE_RESPONSE_MUST_NOT_LEAK")
        self.assertEqual(normalize_error(unsafe).category, CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        self.assertNotIn("PRIVATE_DELETE_RESPONSE_MUST_NOT_LEAK", repr(unsafe) + str(unsafe))
