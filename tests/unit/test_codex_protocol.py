import asyncio
import json
from pathlib import Path
import unittest

from codex_control.adapters.codex.protocol import (
    CodexProtocolClient,
    InboundServerRequest,
    MAX_PENDING_SERVER_REQUESTS,
    ProtocolFault,
    ProtocolRemoteError,
    ProtocolState,
)


class FakeLineTransport:
    def __init__(self):
        self.sent = []
        self.incoming = asyncio.Queue()

    async def send(self, message):
        self.sent.append(message)

    async def receive(self):
        return await self.incoming.get()

    def deliver(self, message):
        self.incoming.put_nowait(json.dumps(message))

    def deliver_raw(self, line):
        self.incoming.put_nowait(line)

    def eof(self):
        self.incoming.put_nowait(None)


class CodexProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.transport = FakeLineTransport()
        self.client = CodexProtocolClient(self.transport, client_version="test-1.2.3")

    async def asyncTearDown(self):
        await self.client.close()

    async def _ready(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.transport.deliver({"id": 1, "result": {"userAgent": "Codex/0.144.6", "codexHome": "/safe", "platformFamily": "unix", "platformOs": "linux"}})
        await task

    async def test_initial_state_is_new(self):
        self.assertIs(self.client.state, ProtocolState.NEW)

    async def test_server_request_is_immutable_redacted_and_exact_instance_owned(self):
        await self._ready()
        sentinel="PRIVATE_SERVER_PARAMS_MUST_NOT_LEAK"
        self.transport.deliver({"id":" A ","method":"item/commandExecution/requestApproval","params":{"secret":sentinel}})
        await asyncio.sleep(0)
        request=await self.client.next_server_request()
        self.assertIsInstance(request,InboundServerRequest)
        self.assertEqual(request.request_id," A ")
        self.assertNotIn(sentinel,repr(request))
        await self.client.respond_server_request(request,{"decision":"decline"})
        self.assertEqual(self.transport.sent[-1],{"id":" A ","result":{"decision":"decline"}})
        with self.assertRaises(ProtocolFault):
            await self.client.respond_server_request(request,{"decision":"decline"})

    async def test_server_request_id_matrix_pending_bound_and_reuse(self):
        await self._ready()
        for ident in (0, -(2**63), 2**63-1, "a", "x"*256, " Case Preserved "):
            self.transport.deliver({"id":ident,"method":"item/commandExecution/requestApproval","params":{}})
        await asyncio.sleep(0)
        accepted=[await self.client.next_server_request() for _ in range(6)]
        self.assertEqual([x.request_id for x in accepted],[0,-(2**63),2**63-1,"a","x"*256," Case Preserved "])
        for request in accepted: await self.client.respond_server_request(request,{"decision":"decline"})
        self.transport.deliver({"id":7,"method":"item/commandExecution/requestApproval","params":{}});await asyncio.sleep(0)
        old=await self.client.next_server_request();await self.client.respond_server_request(old,{"decision":"decline"})
        self.transport.deliver({"id":7,"method":"item/commandExecution/requestApproval","params":{}});await asyncio.sleep(0)
        new=await self.client.next_server_request();self.assertNotEqual(old.local_sequence,new.local_sequence)
        with self.assertRaises(ProtocolFault):await self.client.respond_server_request(old,{"decision":"decline"})
        await self.client.respond_server_request(new,{"decision":"decline"})
        self.assertEqual(sum(x.get("id")==7 for x in self.transport.sent),2)

    async def test_invalid_server_ids_and_65th_fault(self):
        for ident in (True,False,None,1.5,{},[],-(2**63)-1,2**63,"","x"*257,"abc\0def"):
            transport=FakeLineTransport();client=CodexProtocolClient(transport,client_version="x")
            init=asyncio.create_task(client.initialize());await asyncio.sleep(0);transport.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}});await init
            transport.deliver({"id":ident,"method":"item/commandExecution/requestApproval","params":{}});await asyncio.sleep(0)
            self.assertIs(client.state,ProtocolState.FAULTED);self.assertTrue(client._server_requests.empty());await client.close()
        await self._ready()
        for ident in range(MAX_PENDING_SERVER_REQUESTS):self.transport.deliver({"id":ident,"method":"item/commandExecution/requestApproval","params":{}})
        await asyncio.sleep(0);self.assertIs(self.client.state,ProtocolState.READY);self.assertEqual(len(self.client._pending_server),64)
        self.transport.deliver({"id":64,"method":"item/commandExecution/requestApproval","params":{}});await asyncio.sleep(0)
        self.assertIs(self.client.state,ProtocolState.FAULTED)

    async def test_mixed_envelope_and_pre_ready_server_request_fault(self):
        task=asyncio.create_task(self.client.initialize()); await asyncio.sleep(0)
        self.transport.deliver({"id":9,"method":"item/commandExecution/requestApproval","params":{},"result":{}})
        await asyncio.sleep(0)
        self.assertIs(self.client.state,ProtocolState.FAULTED)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task

    async def test_business_request_before_initialize_is_rejected_without_send(self):
        with self.assertRaisesRegex(ProtocolFault, "request_not_allowed"):
            await self.client.request("model/list", {})
        self.assertEqual(self.transport.sent, [])

    async def test_initialize_has_exact_fixture_shape(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.assertEqual(self.transport.sent, [{"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codex_control", "title": "CodexControl", "version": "test-1.2.3"}, "capabilities": {}}}])
        self.assertNotIn("jsonrpc", self.transport.sent[0])
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_successful_initialize_sends_initialized_after_response(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.assertEqual(len(self.transport.sent), 1)
        self.transport.deliver({"id": 1, "result": {"userAgent": "Codex/0.144.6", "codexHome": "/safe", "platformFamily": "unix", "platformOs": "linux"}})
        result = await task
        self.assertEqual(result.platform_os, "linux")
        self.assertEqual(self.transport.sent[-1], {"method": "initialized"})
        self.assertIs(self.client.state, ProtocolState.READY)

    async def test_initialize_error_sends_no_initialized_and_is_not_ready(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.transport.deliver({"id": 1, "error": {"code": -32000, "message": "private remote detail"}})
        with self.assertRaises(ProtocolRemoteError) as raised:
            await task
        self.assertEqual(raised.exception.code, -32000)
        self.assertNotIn("private remote detail", repr(raised.exception))
        self.assertEqual(len(self.transport.sent), 1)
        self.assertIs(self.client.state, ProtocolState.FAULTED)

    async def test_initialize_cannot_be_performed_twice(self):
        await self._ready()
        with self.assertRaisesRegex(ProtocolFault, "initialize_not_allowed"):
            await self.client.initialize()

    async def test_request_ids_are_monotonic_and_responses_correlate_exactly(self):
        await self._ready()
        first = asyncio.create_task(self.client.request("test/one", {}))
        second = asyncio.create_task(self.client.request("test/two", {}))
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual([item["id"] for item in self.transport.sent if "id" in item], [1, 2, 3])
        self.transport.deliver({"id": 3, "result": "second"})
        self.assertEqual(await second, "second")
        self.assertFalse(first.done())
        self.transport.deliver({"id": 2, "result": "first"})
        self.assertEqual(await first, "first")

    async def test_notification_does_not_resolve_pending_and_is_observable(self):
        await self._ready()
        request = asyncio.create_task(self.client.request("test/pending", {}))
        await asyncio.sleep(0)
        self.transport.deliver({"method": "thread/started", "params": {"safe": "metadata"}})
        self.assertEqual(await self.client.next_notification(), {"method": "thread/started", "params": {"safe": "metadata"}})
        self.assertFalse(request.done())
        self.transport.deliver({"id": 2, "result": {}})
        await request

    async def test_unknown_response_id_faults_deterministically(self):
        await self._ready()
        request = asyncio.create_task(self.client.request("test/pending", {}))
        await asyncio.sleep(0)
        self.transport.deliver({"id": 999, "result": {}})
        with self.assertRaisesRegex(ProtocolFault, "unexpected_response_id"):
            await request
        self.assertIs(self.client.state, ProtocolState.FAULTED)

    async def test_duplicate_completed_response_id_faults_deterministically(self):
        await self._ready()
        request = asyncio.create_task(self.client.request("test/pending", {}))
        await asyncio.sleep(0)
        self.transport.deliver({"id": 2, "result": {}})
        await request
        self.transport.deliver({"id": 2, "result": {}})
        await asyncio.sleep(0)
        self.assertIs(self.client.state, ProtocolState.FAULTED)

    async def test_malformed_json_is_sanitized_fault(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        raw = '{not-json secret-token-should-not-appear}'
        self.transport.deliver_raw(raw)
        with self.assertRaisesRegex(ProtocolFault, "malformed_json") as raised:
            await task
        self.assertNotIn(raw, str(raised.exception))
        self.assertNotIn(raw, repr(raised.exception))

    async def test_invalid_top_level_and_envelope_fault(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.transport.deliver_raw("[]")
        with self.assertRaisesRegex(ProtocolFault, "invalid_envelope"):
            await task

    async def test_valid_json_with_invalid_object_envelope_faults(self):
        task = asyncio.create_task(self.client.initialize())
        await asyncio.sleep(0)
        self.transport.deliver({"unexpected": "shape"})
        with self.assertRaisesRegex(ProtocolFault, "invalid_envelope"):
            await task

    async def test_eof_while_pending_fails_without_retry(self):
        await self._ready()
        request = asyncio.create_task(self.client.request("test/pending", {}))
        await asyncio.sleep(0)
        sends_before_eof = list(self.transport.sent)
        self.transport.eof()
        with self.assertRaisesRegex(ProtocolFault, "eof_pending"):
            await request
        self.assertEqual(self.transport.sent, sends_before_eof)
        self.assertIs(self.client.state, ProtocolState.FAULTED)

    async def test_eof_after_initialize_closes_client(self):
        await self._ready()
        self.transport.eof()
        await asyncio.sleep(0)
        self.assertIs(self.client.state, ProtocolState.CLOSED)

    def test_fixture_identifies_installed_version(self):
        fixture = Path(__file__).parents[1] / "fixtures" / "codex_app_server_0_144_6" / "initialize_protocol.json"
        facts = json.loads(fixture.read_text())
        self.assertEqual(facts["codex_version"], "codex-cli 0.144.6")
        self.assertFalse(facts["jsonrpc_field_on_wire"])
        self.assertEqual(facts["initialized_notification"], {"method": "initialized"})


if __name__ == "__main__":
    unittest.main()
