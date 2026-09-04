import asyncio
import json
import unittest

from codex_control.adapters.codex.approvals import (
    APPLY_PATCH, COMMAND, EXEC_COMMAND, FILE_CHANGE, PERMISSIONS,
    ApprovalDecision, ApprovalRequest, CodexApprovalAdapter,
)
from codex_control.adapters.codex.protocol import CodexProtocolClient, ProtocolState
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory, normalize_error


class Transport:
    def __init__(self): self.sent=[]; self.incoming=asyncio.Queue(); self.fail_send=False
    async def send(self, message):
        self.sent.append(message)
        if self.fail_send: raise OSError("lost")
    async def receive(self): return await self.incoming.get()
    def deliver(self, message): self.incoming.put_nowait(json.dumps(message))


class Operator:
    def __init__(self, decision=ApprovalDecision.DENY, error=None): self.decision=decision; self.error=error; self.requests=[]
    async def decide(self, request):
        self.requests.append(request)
        if self.error: raise self.error
        return self.decision


class WaitingOperator:
    def __init__(self): self.started=asyncio.Event()
    async def decide(self, request):
        self.started.set()
        await asyncio.Event().wait()


def permissions(entries=None, network=None):
    p={"cwd":"/work","itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u","permissions":{}}
    if entries is not None: p["permissions"]["fileSystem"]={"entries":entries}
    if network is not None: p["permissions"]["network"]={"enabled":network}
    return p


class ApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.transport=Transport(); self.client=CodexProtocolClient(self.transport,client_version="test")
        task=asyncio.create_task(self.client.initialize()); await asyncio.sleep(0)
        self.transport.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}}); await task

    async def asyncTearDown(self): await self.client.close()

    async def _inbound(self, method, params, request_id="server-1"):
        self.transport.deliver({"id":request_id,"method":method,"params":params}); await asyncio.sleep(0)
        return await self.client.next_server_request()

    async def test_permissions_deny_is_exact_empty_turn_grant_once(self):
        inbound=await self._inbound(PERMISSIONS,permissions(network=True))
        await CodexApprovalAdapter(Operator()).handle_envelope(self.client,inbound)
        self.assertEqual(self.transport.sent[-1],{"id":"server-1","result":{"permissions":{},"scope":"turn"}})
        self.assertNotIn("network",self.transport.sent[-1]["result"]["permissions"])
        self.assertNotIn("fileSystem",self.transport.sent[-1]["result"]["permissions"])
        self.assertEqual(sum("server-1" == x.get("id") for x in self.transport.sent),1)

    async def test_permissions_allow_preserves_multiple_entries_without_broadening(self):
        entries=[{"access":"read","path":{"type":"path","path":"/a"}},{"access":"write","path":{"type":"path","path":"/b"}}]
        inbound=await self._inbound(PERMISSIONS,permissions(entries=entries))
        await CodexApprovalAdapter(Operator(ApprovalDecision.ALLOW)).handle_envelope(self.client,inbound)
        self.assertEqual(self.transport.sent[-1]["result"],{"permissions":{"fileSystem":{"entries":entries}},"scope":"turn"})

    async def test_permissions_network_only_and_filesystem_only_are_turn_scoped(self):
        adapter=CodexApprovalAdapter(Operator(ApprovalDecision.ALLOW))
        await adapter.handle_envelope(self.client,await self._inbound(PERMISSIONS,permissions(network=True),"n"))
        self.assertEqual(self.transport.sent[-1]["result"],{"permissions":{"network":{"enabled":True}},"scope":"turn"})
        entry=[{"access":"read","path":{"type":"path","path":"/only"}}]
        await adapter.handle_envelope(self.client,await self._inbound(PERMISSIONS,permissions(entries=entry),"f"))
        self.assertEqual(self.transport.sent[-1]["result"]["permissions"],{"fileSystem":{"entries":entry}})

    async def test_permissions_empty_exception_cancel_and_invalid_all_deny(self):
        for request_id, op, payload in (("empty",Operator(ApprovalDecision.ALLOW),permissions()),("error",Operator(error=RuntimeError()),permissions(network=True)),("bad",Operator("allow"),permissions(network=True))):
            await CodexApprovalAdapter(op).handle_envelope(self.client,await self._inbound(PERMISSIONS,payload,request_id))
            self.assertEqual(self.transport.sent[-1]["result"],{"permissions":{},"scope":"turn"})
        # A cancelling operator is contained and produces exactly the same DENY.
        result=await CodexApprovalAdapter(Operator(error=asyncio.CancelledError())).handle_envelope(self.client,await self._inbound(PERMISSIONS,permissions(network=True),"cancel"))
        self.assertEqual(result.status.value,"denied")
        self.assertEqual(self.transport.sent[-1]["result"],{"permissions":{},"scope":"turn"})

    async def test_handler_cancellation_before_send_denies_then_propagates_cancel(self):
        operator=WaitingOperator(); adapter=CodexApprovalAdapter(operator)
        task=asyncio.create_task(adapter.handle_envelope(self.client,await self._inbound(PERMISSIONS,permissions(network=True),"outer-cancel")))
        await operator.started.wait(); task.cancel()
        self.assertEqual((await task).status.value,"denied")
        self.assertEqual(self.transport.sent[-1],{"id":"outer-cancel","result":{"permissions":{},"scope":"turn"}})

    async def test_each_non_permission_exact_mapping(self):
        cases=[(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},{"decision":"accept"},{"decision":"decline"}),
               (FILE_CHANGE,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},{"decision":"accept"},{"decision":"decline"}),
               (APPLY_PATCH,{"callId":"c","conversationId":"t","fileChanges":{}},{"decision":"approved"},{"decision":"denied"}),
               (EXEC_COMMAND,{"callId":"c","conversationId":"t","cwd":"/x","command":["x"],"parsedCmd":[]},{"decision":"approved"},{"decision":"denied"})]
        for number,(method,params,allow,deny) in enumerate(cases):
            await CodexApprovalAdapter(Operator(ApprovalDecision.ALLOW)).handle_envelope(self.client,await self._inbound(method,params,f"a{number}"))
            self.assertEqual(self.transport.sent[-1]["result"],allow)
            await CodexApprovalAdapter(Operator()).handle_envelope(self.client,await self._inbound(method,params,f"d{number}"))
            self.assertEqual(self.transport.sent[-1]["result"],deny)

    async def test_public_request_is_redacted_and_bounded(self):
        operator=Operator(ApprovalDecision.ALLOW)
        await CodexApprovalAdapter(operator).handle_envelope(self.client,await self._inbound(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u","command":"secret"}))
        request=operator.requests[0]
        self.assertIsInstance(request,ApprovalRequest); self.assertNotIn("secret",repr(request)); self.assertFalse(hasattr(request,"params"))

    async def test_server_request_is_not_notification_and_opposite_direction_same_id_works(self):
        client_request=asyncio.create_task(self.client.request("test",{})); await asyncio.sleep(0)
        self.transport.deliver({"id":2,"method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}})
        self.transport.deliver({"id":2,"result":{}}); await asyncio.sleep(0)
        inbound=await self.client.next_server_request(); self.assertEqual(inbound.request_id,2); self.assertEqual(await client_request,{})

    async def test_duplicate_pending_server_id_faults_and_eof_is_terminal(self):
        await self._inbound(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},"same")
        self.transport.deliver({"id":"same","method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}}); await asyncio.sleep(0)
        self.assertIs(self.client.state,ProtocolState.FAULTED)

    async def test_ambiguous_send_is_not_retried_and_normalizes_unknown(self):
        self.transport.fail_send=True
        inbound=await self._inbound(PERMISSIONS,permissions(network=True),"lost")
        result=await CodexApprovalAdapter(Operator()).handle_envelope(self.client,inbound)
        self.assertEqual(result.status.value,"response_unknown")
        self.assertEqual(sum(x.get("id")=="lost" for x in self.transport.sent),1)
