import asyncio,json,unittest
import codex_control.adapters.codex.approvals as approval_module
from pathlib import Path
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
 async def test_permission_noops_deny_without_operator(self):
  noops=[{}, {"network":{}},{"network":{"enabled":False}},{"network":{"enabled":None}},{"fileSystem":{}},{"fileSystem":{"read":[]}},{"fileSystem":{"write":[]}},{"fileSystem":{"entries":[]}},{"fileSystem":{"entries":[{"access":"deny","path":{"type":"path","path":"/x"}}]}},{"fileSystem":{"globScanMaxDepth":1}},{"network":{},"fileSystem":{"read":[],"write":[]}}]
  for n,permissions in enumerate(noops):
   op=Operator(ApprovalDecision.ALLOW); p=permission(network=None);p["permissions"]=permissions
   result=await self.bridge(op).handle_request(await self.inbound(PERMISSIONS,p,"noop"+str(n)))
   self.assertEqual(result.status,ApprovalHandlingStatus.DENIED);self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],{"permissions":{},"scope":"turn"})
 async def test_parsed_command_variants_malformed_and_context(self):
  variants=[{"type":"read","cmd":"cat x","name":"cat","path":"/x"},{"type":"list_files","cmd":"ls","path":None},{"type":"search","cmd":"rg x","query":"x","path":"/x"},{"type":"unknown","cmd":"x"}]
  for n,parsed in enumerate(variants):
   op=Operator(ApprovalDecision.ALLOW);p={"callId":"c","conversationId":"t","cwd":"/x","command":["rg","x"],"parsedCmd":[parsed]};r=await self.bridge(op).handle_request(await self.inbound(EXEC_COMMAND,p,"v"+str(n)));self.assertEqual(r.status,ApprovalHandlingStatus.ALLOWED);self.assertIn("command: rg x",op.requests[0].context_lines)
  malformed=[{"type":"read","cmd":"x","path":"/x"},{"type":"read","cmd":"x","name":1,"path":"/x"},{"type":"list_files","cmd":"x","path":1},{"type":"search","cmd":"x","query":1},{"type":"unknown"},{"type":"future","cmd":"x"}]
  for n,parsed in enumerate(malformed):
   op=Operator();p={"callId":"c","conversationId":"t","cwd":"/x","command":["x"],"parsedCmd":[parsed]};r=await self.bridge(op).handle_request(await self.inbound(EXEC_COMMAND,p,"m"+str(n)));self.assertEqual(r.status,ApprovalHandlingStatus.DENIED);self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],{"decision":"denied"})
 async def test_apply_patch_context_excludes_content_and_context_bounds(self):
  secret="PRIVATE_FILE_CONTENT_MUST_NOT_LEAK";op=Operator(ApprovalDecision.ALLOW);p={"callId":"c","conversationId":"t","fileChanges":{"/safe":{"type":"add","content":secret}}};r=await self.bridge(op).handle_request(await self.inbound(APPLY_PATCH,p,"patch"));self.assertEqual(r.status,ApprovalHandlingStatus.ALLOWED);self.assertIn("file: /safe",op.requests[0].context_lines);self.assertNotIn(secret," ".join(op.requests[0].context_lines)+repr(op.requests[0]))
  self.assertEqual(len(approval_module._context(["x"*2048])),1)
  for lines in (["x"*2049],["x"*2048]*5,["x"]*33):
   with self.assertRaises(ValueError):approval_module._context(lines)
 def test_approval_fixture_freezes_nested_schema_facts(self):
  facts=json.loads((Path(__file__).parents[1]/"fixtures"/"codex_app_server_0_144_6"/"approval_protocol.json").read_text())
  self.assertEqual(facts["codex_version"],"codex-cli 0.144.6");self.assertEqual(len(facts["server_requests"]),5)
  self.assertEqual(set(facts["permissions_nested_schema"]["entry"]["access"]),{"read","write","deny"})
  self.assertEqual(set(facts["parsed_command_schema"]["variants"]),{"read","list_files","search","unknown"})
  self.assertEqual(set(facts["legacy_file_change_schema"]["variants"]),{"add","delete","update"})

 def test_approval_fixture_binds_every_method_and_adr_separation(self):
  facts=json.loads((Path(__file__).parents[1]/"fixtures"/"codex_app_server_0_144_6"/"approval_protocol.json").read_text())
  self.assertEqual(facts["schema_sha256"],"40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466")
  expected={COMMAND:("CommandExecutionRequestApprovalParams","CommandExecutionRequestApprovalResponse","accept","decline"),FILE_CHANGE:("FileChangeRequestApprovalParams","FileChangeRequestApprovalResponse","accept","decline"),PERMISSIONS:("PermissionsRequestApprovalParams","PermissionsRequestApprovalResponse","validated request-derived grant + scope turn",{"permissions":{},"scope":"turn"}),APPLY_PATCH:("ApplyPatchApprovalParams","ApplyPatchApprovalResponse","approved","denied"),EXEC_COMMAND:("ExecCommandApprovalParams","ExecCommandApprovalResponse","approved","denied")}
  self.assertEqual(set(facts["method_schemas"]),set(expected))
  for method,(request,response,allow,deny) in expected.items():
   item=facts["method_schemas"][method];self.assertEqual(item["request"],request);self.assertEqual(item["response"],response);self.assertTrue(item["properties"]);self.assertTrue(item["required"]);self.assertTrue(item["identity"]);self.assertTrue(item["context"]);self.assertTrue(item["response_required"]);self.assertEqual(item["allow"],allow);self.assertEqual(item["deny"],deny);self.assertTrue(item["session_allow_present"])
   if method!=PERMISSIONS:self.assertTrue(item["decision"])
  self.assertFalse(facts["permissions_schema_facts"]["decision_enum"]);self.assertEqual(facts["permissions_semantic_authority"]["permissions_deny_shape"],{"permissions":{},"scope":"turn"});self.assertFalse(facts["permissions_semantic_authority"]["session_scope_allowed_by_product"])

 async def test_handle_next_cancel_before_ownership_cleans_waiters_and_preserves_request(self):
  entered=asyncio.Event(); original=self.c.next_server_request
  async def observed_get():
   entered.set();return await original()
  self.c.next_server_request=observed_get
  bridge=self.bridge(Operator())
  old=asyncio.create_task(bridge.handle_next());await entered.wait()
  old.cancel()
  with self.assertRaises(asyncio.CancelledError):await old
  self.assertFalse(any(not task.done() for task in self.c._server_requests._getters))
  self.t.deliver({"id":"future","method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}})
  fresh=asyncio.create_task(bridge.handle_next())
  result=await fresh
  self.assertEqual(result.wire_request_id,"future");self.assertEqual(sum(x.get("id")=="future" for x in self.t.sent),1)

 async def test_foreign_direct_request_is_rejected_before_projection(self):
  other_t=Transport();other=CodexProtocolClient(other_t,client_version="test")
  init=asyncio.create_task(other.initialize());await asyncio.sleep(0);other_t.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}});await init
  other_t.deliver({"id":"foreign","method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}});await asyncio.sleep(0)
  foreign=await other.next_server_request();op=Operator(ApprovalDecision.ALLOW)
  with self.assertRaises(ApprovalError) as caught:await self.bridge(op).handle_request(foreign)
  self.assertEqual(caught.exception.category,ApprovalErrorCategory.APPROVAL_REQUEST_INVALID);self.assertFalse(op.requests);self.assertFalse(any(x.get("id")=="foreign" for x in self.t.sent))
  await other.close()

 async def test_post_send_repeated_cancellation_keeps_single_owned_response(self):
  for n,(decision,expected) in enumerate(((ApprovalDecision.ALLOW,"accept"),(ApprovalDecision.DENY,"decline"))):
   started=asyncio.Event();release=asyncio.Event();self.t.block=release
   old_send=self.t.send
   async def gated(message):
    self.t.sent.append(message)
    if message.get("id")=="post":started.set();await release.wait()
   self.t.send=gated
   task=asyncio.create_task(self.bridge(Operator(decision)).handle_request(await self.inbound(COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},"post")))
   await started.wait();task.cancel();task.cancel();self.assertFalse(task.done());release.set()
   result=await task;self.assertEqual(result.status,ApprovalHandlingStatus.ALLOWED if decision is ApprovalDecision.ALLOW else ApprovalHandlingStatus.DENIED)
   self.assertEqual(self.t.sent[-1]["result"],{"decision":expected});self.assertEqual(sum(x.get("id")=="post" for x in self.t.sent),n+1)
   self.t.send=old_send;self.t.block=None

 async def test_handle_next_dequeue_completion_wins_public_cancellation(self):
  """The real protocol queue dequeue transfers ownership before cancellation."""
  dequeued=asyncio.Event();original=self.c.next_server_request
  async def observed():
   request=await original();dequeued.set();return request
  self.c.next_server_request=observed
  task=asyncio.create_task(self.bridge(Operator(ApprovalDecision.ALLOW)).handle_next())
  self.t.deliver({"id":"won","method":PERMISSIONS,"params":permission(network=True)})
  await dequeued.wait();task.cancel()
  result=await task
  self.assertIn(result.status,(ApprovalHandlingStatus.DENIED,ApprovalHandlingStatus.RESPONSE_UNKNOWN))
  self.assertEqual([x for x in self.t.sent if x.get("id")=="won"],[{"id":"won","result":{"permissions":{},"scope":"turn"}}])
  self.assertNotIn("won",self.c._pending_server)

 async def test_allow_then_presend_cancellation_denies_command_and_permissions(self):
  for number,(method,params,expected) in enumerate(((COMMAND,{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"},{"decision":"decline"}),(PERMISSIONS,permission(network=True),{"permissions":{},"scope":"turn"}))):
   inbound=await self.inbound(method,params,"presend"+str(number));cleanup_started=asyncio.Event();cleanup_release=asyncio.Event()
   async def terminal():
    try: await asyncio.Event().wait()
    except asyncio.CancelledError:
     cleanup_started.set();await cleanup_release.wait();raise
   original=self.c.wait_terminal;self.c.wait_terminal=terminal
   try:
    task=asyncio.create_task(self.bridge(Operator(ApprovalDecision.ALLOW)).handle_request(inbound))
    await cleanup_started.wait();self.assertFalse(any(x.get("id")==inbound.request_id for x in self.t.sent))
    task.cancel();task.cancel();cleanup_release.set();result=await task
   finally: self.c.wait_terminal=original
   self.assertEqual(result.status,ApprovalHandlingStatus.DENIED)
   self.assertEqual(self.t.sent[-1],{"id":inbound.request_id,"result":expected})

 async def test_owned_request_protocol_terminal_is_unknown_and_cancels_operator(self):
  release=asyncio.Event();operator=Operator(ApprovalDecision.ALLOW);operator.release=release
  task=asyncio.create_task(self.bridge(operator).handle_next())
  self.t.deliver({"id":"terminal","method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}})
  await operator.started.wait();self.t.incoming.put_nowait(None)
  result=await task
  self.assertEqual(result.status,ApprovalHandlingStatus.RESPONSE_UNKNOWN)
  self.assertEqual((result.profile_id,result.local_sequence,result.wire_request_id,result.kind),("p",1,"terminal",ApprovalKind.COMMAND_EXECUTION))
  self.assertFalse(any(x.get("id")=="terminal" for x in self.t.sent))

 async def test_simultaneous_request_terminal_and_terminal_before_ownership(self):
  task=asyncio.create_task(self.bridge(Operator()).handle_next())
  self.t.deliver({"id":"same","method":COMMAND,"params":{"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u"}});self.t.incoming.put_nowait(None)
  result=await task
  self.assertEqual(result.status,ApprovalHandlingStatus.RESPONSE_UNKNOWN);self.assertEqual(result.wire_request_id,"same")
  self.assertFalse(any(x.get("id")=="same" for x in self.t.sent))
  t=Transport();c=CodexProtocolClient(t,client_version="test");init=asyncio.create_task(c.initialize());await asyncio.sleep(0);t.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}});await init;t.incoming.put_nowait(None);await asyncio.sleep(0)
  with self.assertRaises(ApprovalError) as raised: await CodexApprovalBridge(profile_id="q",client=c,operator=Operator()).handle_next()
  self.assertEqual(raised.exception.category,ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL);await c.close()

 async def test_public_handle_next_fifo_serializes_actual_protocol_queue(self):
  release=asyncio.Event();operator=Operator();operator.release=release;bridge=self.bridge(operator)
  self.t.deliver({"id":"A","method":COMMAND,"params":{"itemId":"A","startedAtMs":1,"threadId":"t","turnId":"u"}});self.t.deliver({"id":"B","method":COMMAND,"params":{"itemId":"B","startedAtMs":1,"threadId":"t","turnId":"u"}});await asyncio.sleep(0)
  first=asyncio.create_task(bridge.handle_next());second=asyncio.create_task(bridge.handle_next());await operator.started.wait();await asyncio.sleep(0)
  self.assertEqual([r.item_or_call_id for r in operator.requests],["A"]);self.assertFalse(any(x.get("id")=="B" for x in self.t.sent))
  release.set();await first;await second
  self.assertEqual([r.item_or_call_id for r in operator.requests],["A","B"]);self.assertEqual([x["id"] for x in self.t.sent if x.get("id") in ("A","B")],["A","B"])

 async def test_two_independent_runtime_bridges_do_not_share_lock_or_wire(self):
  async def ready(profile):
   t=Transport();c=CodexProtocolClient(t,client_version="test");init=asyncio.create_task(c.initialize());await asyncio.sleep(0);t.deliver({"id":1,"result":{"userAgent":"x","codexHome":"/safe","platformFamily":"unix","platformOs":"linux"}});await init;o=Operator();o.release=asyncio.Event();return t,c,o,CodexApprovalBridge(profile_id=profile,client=c,operator=o)
  pt,pc,po,pb=await ready("p");qt,qc,qo,qb=await ready("q")
  pt.deliver({"id":"p","method":COMMAND,"params":{"itemId":"p","startedAtMs":1,"threadId":"t","turnId":"u"}});qt.deliver({"id":"q","method":COMMAND,"params":{"itemId":"q","startedAtMs":1,"threadId":"t","turnId":"u"}})
  ptask=asyncio.create_task(pb.handle_next());qtask=asyncio.create_task(qb.handle_next());await po.started.wait();await qo.started.wait()
  self.assertEqual(po.requests[0].profile_id,"p");self.assertEqual(qo.requests[0].profile_id,"q");po.release.set();await ptask;self.assertFalse(qtask.done());qo.release.set();await qtask
  self.assertTrue(any(x.get("id")=="p" for x in pt.sent));self.assertFalse(any(x.get("id")=="p" for x in qt.sent));await pc.close();await qc.close()

 async def test_context_exact_boundaries_and_actual_overflow_denies(self):
  self.assertEqual(approval_module._context(["x"*2048]),("x"*2048,));self.assertEqual(len(approval_module._context(["x"*2048]*4)),4);self.assertEqual(len(approval_module._context(["x"]*32)),32)
  for lines in (["x"*2049],["x"*2048]*4+["x"],["x"]*33):
   with self.assertRaises(ValueError): approval_module._context(lines)
  op=Operator(ApprovalDecision.ALLOW);command={"itemId":"i","startedAtMs":1,"threadId":"t","turnId":"u","reason":"x"*2042};result=await self.bridge(op).handle_request(await self.inbound(COMMAND,command,"over-command"));self.assertEqual(result.status,ApprovalHandlingStatus.DENIED);self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],{"decision":"decline"})
  op=Operator(ApprovalDecision.ALLOW);changes={"/"+str(i):{"type":"add","content":"PRIVATE_FILE_CONTENT_MUST_NOT_LEAK"} for i in range(33)};result=await self.bridge(op).handle_request(await self.inbound(APPLY_PATCH,{"callId":"c","conversationId":"t","fileChanges":changes},"over-patch"));self.assertEqual(result.status,ApprovalHandlingStatus.DENIED);self.assertFalse(op.requests);self.assertEqual(self.t.sent[-1]["result"],{"decision":"denied"})

 async def test_all_five_nontrivial_normalization_and_local_sequence(self):
  bridge=self.bridge(Operator(ApprovalDecision.ALLOW));entries=[{"access":"read","path":{"type":"path","path":"/safe"}}]
  cases=[(COMMAND,{"itemId":"command","startedAtMs":1,"threadId":"thread","turnId":"turn","reason":"reason","cwd":"/safe","command":"ls"},ApprovalKind.COMMAND_EXECUTION),(FILE_CHANGE,{"itemId":"file","startedAtMs":2,"threadId":"thread","turnId":"turn","reason":"reason"},ApprovalKind.FILE_CHANGE),(PERMISSIONS,{**permission(entries),"reason":"reason"},ApprovalKind.PERMISSIONS),(APPLY_PATCH,{"callId":"patch","conversationId":"thread","reason":"reason","fileChanges":{"/safe":{"type":"add","content":"PRIVATE_FILE_CONTENT_MUST_NOT_LEAK"}}},ApprovalKind.APPLY_PATCH),(EXEC_COMMAND,{"callId":"exec","conversationId":"thread","cwd":"/safe","command":["rg","needle"],"parsedCmd":[{"type":"search","cmd":"rg needle","query":"needle","path":"/safe"}]},ApprovalKind.EXEC_COMMAND)]
  for index,(method,params,kind) in enumerate(cases,1):
   inbound=await self.inbound(method,params,"id"+str(index));result=await bridge.handle_request(inbound);request=bridge._operator.requests[-1]
   self.assertEqual((result.local_sequence,request.profile_id,request.wire_request_id,request.kind),(index,"p","id"+str(index),kind));self.assertTrue(request.context_lines);self.assertNotIn("PRIVATE_FILE_CONTENT_MUST_NOT_LEAK",repr(request))
  reused=await self.inbound(COMMAND,{"itemId":"again","startedAtMs":3,"threadId":"thread","turnId":"turn"},"id1");result=await bridge.handle_request(reused);self.assertGreater(result.local_sequence,1)

 def test_approval_fixture_complete_exact_records(self):
  facts=json.loads((Path(__file__).parents[1]/"fixtures"/"codex_app_server_0_144_6"/"approval_protocol.json").read_text())
  expected={COMMAND:(["turnId","approvalId","threadId","command","commandActions","cwd","environmentId","itemId","networkApprovalContext","proposedExecpolicyAmendment","proposedNetworkPolicyAmendments","reason","startedAtMs"],["itemId","startedAtMs","threadId","turnId"],["decision"],["accept","acceptForSession",{"acceptWithExecpolicyAmendment":"object"},{"applyNetworkPolicyAmendment":"object"},"decline","cancel"]),FILE_CHANGE:(["grantRoot","itemId","reason","startedAtMs","threadId","turnId"],["itemId","startedAtMs","threadId","turnId"],["decision"],["accept","acceptForSession","decline","cancel"]),PERMISSIONS:(["cwd","environmentId","itemId","permissions","reason","startedAtMs","threadId","turnId"],["cwd","itemId","permissions","startedAtMs","threadId","turnId"],["permissions"],None),APPLY_PATCH:(["callId","conversationId","fileChanges","grantRoot","reason"],["callId","conversationId","fileChanges"],["decision"],["approved",{"approved_execpolicy_amendment":"object"},"approved_for_session",{"network_policy_amendment":"object"},"denied","timed_out","abort"]),EXEC_COMMAND:(["approvalId","callId","command","conversationId","cwd","parsedCmd","reason"],["callId","command","conversationId","cwd","parsedCmd"],["decision"],["approved",{"approved_execpolicy_amendment":"object"},"approved_for_session",{"network_policy_amendment":"object"},"denied","timed_out","abort"])}
  for method,(properties,required,response_required,decision) in expected.items():
   row=facts["method_schemas"][method];self.assertEqual(row["properties"],properties);self.assertEqual(row["required"],required);self.assertEqual(row["response_required"],response_required);self.assertEqual(row.get("decision"),decision)
  self.assertEqual(facts["permissions_nested_schema"]["request_profile"],{"properties":["fileSystem","network"],"additionalProperties":False});self.assertEqual(facts["permissions_nested_schema"]["path_types"],["path","glob_pattern","special"]);self.assertEqual(facts["permissions_nested_schema"]["special_kinds"],["root","minimal","project_roots","tmpdir","slash_tmp","unknown"])
  self.assertEqual(facts["parsed_command_schema"]["variants"]["read"]["required"],["type","cmd","name","path"]);self.assertEqual(facts["parsed_command_schema"]["variants"]["search"]["optional_nullable"],["query","path"]);self.assertEqual(facts["legacy_file_change_schema"]["variants"]["update"],{"required":["type","unified_diff"],"optional_nullable":["move_path"]})
