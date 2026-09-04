import asyncio,json,unittest
from codex_control.adapters.codex.approvals import *
from codex_control.adapters.codex.protocol import CodexProtocolClient

class Transport:
 def __init__(self):self.sent=[];self.incoming=asyncio.Queue();self.block=None;self.cancel_send=False
 async def send(self,m):
  self.sent.append(m)
  if self.cancel_send:raise asyncio.CancelledError
  if self.block:await self.block.wait()
 async def receive(self):return await self.incoming.get()
 def deliver(self,m):self.incoming.put_nowait(json.dumps(m))
class Operator:
 def __init__(self,d=ApprovalDecision.DENY):self.d=d;self.requests=[];self.started=asyncio.Event();self.release=None
 async def decide(self,r):
  self.requests.append(r);self.started.set()
  if self.release:await self.release.wait()
  return self.d
def permission(entries=None,network=True):
 p={"cwd":"/work","itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u","permissions":{}}
 if entries is not None:p["permissions"]["fileSystem"]={"entries":entries}
 if network is not None:p["permissions"]["network"]={"enabled":network}
 return p
class Tests(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.t=Transport();self.c=CodexProtocolClient(self.t,client_version="test");x=asyncio.create_task(self.c.initialize());await asyncio.sleep(0);self.t.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}});await x
 async def asyncTearDown(self):await self.c.close()
 async def inbound(self,m,p,ident="s"):
  self.t.deliver({"id":ident,"method":m,"params":p});await asyncio.sleep(0);return await self.c.next_server_request()
 def bridge(self,o):return CodexApprovalBridge(profile_id="p",client=self.c,operator=o)
 async def test_permission_validation_bounds_and_redaction(self):
  e={"access":"read","path":{"type":"path","path":"x"*4096}}
  o=Operator(ApprovalDecision.ALLOW);r=await self.bridge(o).handle_request(await self.inbound(PERMISSIONS,permission([e])))
  self.assertEqual(r.status,ApprovalHandlingStatus.ALLOWED);self.assertEqual(self.t.sent[-1]["result"]["permissions"]["fileSystem"]["entries"][0],e)
  for bad in ({"PRIVATE_UNKNOWN_GRANT":"MUST_NOT_PASS"},{"network":{"enabled":"true"}},{"fileSystem":{"entries":[{"access":"admin","path":{"type":"path","path":"/x"}}]}},{"fileSystem":{"entries":[{"access":"read","path":{"type":"bad","path":"/x"}}]}},{"fileSystem":{"entries":["bad"]}},{"fileSystem":{"entries":[{"access":"read","path":{"type":"path","path":"x"*4097}}]}}):
   op=Operator(ApprovalDecision.ALLOW);await self.bridge(op).handle_request(await self.inbound(PERMISSIONS,{**permission(network=None),"permissions":bad},str(len(self.t.sent))))
   self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],{"permissions":{},"scope":"turn"})
  entries=[{"access":"read","path":{"type":"path","path":"/x"}}]*128
  await self.bridge(Operator(ApprovalDecision.ALLOW)).handle_request(await self.inbound(PERMISSIONS,permission(entries),"128"));self.assertEqual(len(self.t.sent[-1]["result"]["permissions"]["fileSystem"]["entries"]),128)
  await self.bridge(Operator(ApprovalDecision.ALLOW)).handle_request(await self.inbound(PERMISSIONS,permission(entries+[entries[0]]),"129"));self.assertEqual(self.t.sent[-1]["result"],{"permissions":{},"scope":"turn"})
 async def test_exact_mappings_and_malformed_all_five(self):
  cases=[(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},{"decision":"accept"},{"decision":"decline"}),(FILE_CHANGE,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},{"decision":"accept"},{"decision":"decline"}),(APPLY_PATCH,{"callId":"c","conversationId":"t","fileChanges":{}},{"decision":"approved"},{"decision":"denied"}),(EXEC_COMMAND,{"callId":"c","conversationId":"t","cwd":"/x","command":["x"],"parsedCmd":[]},{"decision":"approved"},{"decision":"denied"})]
  for n,(m,p,a,d) in enumerate(cases):
   await self.bridge(Operator(ApprovalDecision.ALLOW)).handle_request(await self.inbound(m,p,"a"+str(n)));self.assertEqual(self.t.sent[-1]["result"],a)
   op=Operator(ApprovalDecision.ALLOW);bad=dict(p);bad.pop(next(iter(p)));await self.bridge(op).handle_request(await self.inbound(m,bad,"b"+str(n)));self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],d)
 async def test_finite_error_and_terminal_no_identity(self):
  raw="PRIVATE /root/secret OPENAI_API_KEY=MUST_NOT_LEAK";e=ApprovalError(raw);self.assertEqual(e.category,ApprovalErrorCategory.APPROVAL_REQUEST_INVALID);self.assertNotIn(raw,str(e)+repr(e))
  task=asyncio.create_task(self.bridge(Operator()).handle_next());await asyncio.sleep(0);await self.c.close()
  with self.assertRaises(ApprovalError) as got:await task
  self.assertEqual(got.exception.category,ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL)
 async def test_inner_send_cancel_unknown_once(self):
  self.t.cancel_send=True;r=await asyncio.wait_for(self.bridge(Operator()).handle_request(await self.inbound(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"})),1)
  self.assertEqual(r.status,ApprovalHandlingStatus.RESPONSE_UNKNOWN);self.assertEqual(sum(x.get("id")=="s" for x in self.t.sent),1)
 async def test_same_bridge_serializes_and_different_bridges_do_not(self):
  release=asyncio.Event();o=Operator();o.release=release;b=self.bridge(o)
  a=await self.inbound(COMMAND,{"itemId":"a","startedAtMs":1,"threadId":"t","turnId":"u"},"a");z=await self.inbound(COMMAND,{"itemId":"b","startedAtMs":1,"threadId":"t","turnId":"u"},"b")
  ta=asyncio.create_task(b.handle_request(a));await o.started.wait();tb=asyncio.create_task(b.handle_request(z));await asyncio.sleep(0);self.assertEqual(len(o.requests),1);release.set();await ta;await tb;self.assertEqual([x.item_or_call_id for x in o.requests],["a","b"])
