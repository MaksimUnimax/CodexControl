import asyncio, json, unittest
from pathlib import Path
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import *

class Client:
 def __init__(s,response=None,gate=None): s.calls=[];s.events=asyncio.Queue();s.terminal=asyncio.Event();s.response={"turn":{"id":"Turn-AbC  123"}} if response is None else response;s.gate=gate;s.dispatched=asyncio.Event()
 async def request(s,m,p):
  s.calls.append((m,p));s.dispatched.set()
  if s.gate: await s.gate.wait()
  if isinstance(s.response,BaseException): raise s.response
  return s.response
 async def next_notification(s): return await s.events.get()
 async def wait_terminal(s): await s.terminal.wait()
class Runtime:
 def __init__(s,p="p",g=1,c=None):s.profile_id=p;s.generation=g;s.client=c or Client()
class Manager:
 def __init__(s,*r):s.r=list(r);s.calls=0
 async def acquire(s,p):s.calls+=1;return s.r[min(s.calls-1,len(s.r)-1)]
class Catalog:
 def __init__(s,p="p",g=1):s.value=s.make(p,g)
 @staticmethod
 def make(p,g):return CodexModelCatalog(p,g,(CodexModelDescriptor("chosen","wire-model","shown",("low","high"),"high",True,False),CodexModelDescriptor("hidden","hidden-wire","hidden",("low",),"low",False,True)),0,99)
 async def get_catalog(s,p):return s.value
def terminal(b,status="completed"):return {"method":"turn/completed","params":{"threadId":b.thread_id,"turn":{"id":b.turn_id,"status":status}}}
def item(b,i="i",text="A",typ="agentMessage"):return {"method":"item/completed","params":{"threadId":b.thread_id,"turnId":b.turn_id,"item":{"id":i,"type":typ,"text":text}}}

class Tests(unittest.IsolatedAsyncioTestCase):
 def setUp(s):s.client=Client();s.runtime=Runtime(c=s.client);s.manager=Manager(s.runtime);s.catalog=Catalog();s.adapter=CodexTurnLifecycleAdapter(s.manager,s.catalog);s.thread=ThreadBinding("p","Thread-A");s.cwd=TrustedWorkingDirectory("/safe")
 async def start(s,**kw):
  v=dict(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="Hello  MiXeD ",working_directory=s.cwd);v.update(kw);return await s.adapter.start_turn(**v)
 async def finish(s,st,status="completed"):await s.client.events.put(terminal(st.binding,status));return await s.adapter.wait_turn(st.binding)
 def test_fixture_authority(s):
  r=Path(__file__).parents[1]/"fixtures/codex_app_server_0_144_6";a=json.loads((r/"turn_start_protocol.json").read_text());e=json.loads((r/"turn_events_protocol.json").read_text())
  s.assertEqual((a["codex_version"],a["schema_sha256"],a["turn_start_method"]),("0.144.6","40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466","turn/start"));s.assertEqual(a["turn_start_required_fields"],["input","threadId"]);s.assertEqual(a["turn_start_parameter_fields"],["personality","approvalPolicy","approvalsReviewer","clientUserMessageId","serviceTier","cwd","effort","threadId","input","model","summary","outputSchema","sandboxPolicy"])
  s.assertEqual((a["thread_id_request_field"],a["plain_text_input_source_shape"],a["model_wire_field"],a["reasoning_effort_field"],a["cwd_field"],a["config_field"],a["turn_id_result_path"]),("threadId",{"type":"text","text":"string"},"model","effort","cwd","absent","turn.id"));s.assertEqual((a["reasoning_effort_required"],a["reasoning_effort_schema_ref"],a["reasoning_effort_json_type"],a["reasoning_effort_enum"],a["reasoning_effort_min_length"],a["reasoning_effort_nullable"]),(False,"#/definitions/v2/ReasoningEffort","string",None,1,True));s.assertEqual((a["approval_field"],a["sandbox_field"]),("approvalPolicy:on-request","sandboxPolicy:{type:workspaceWrite}"));s.assertEqual((e["agent_message_delta_method"],e["item_completed_method"],e["turn_terminal_method"]),("item/agentMessage/delta","item/completed","turn/completed"));s.assertEqual(e["completed_item_identity_paths"],["threadId","turnId","item.id"]);s.assertEqual(e["terminal_status_values"],["completed","interrupted","failed","inProgress"]);s.assertIsNone(e["agent_message_text_min_length"]);s.assertIsNone(e["delta_min_length"])
 async def test_request_and_effort(s):
  x=await s.start();p=s.client.calls[0][1];s.assertEqual(p,{"threadId":"Thread-A","input":[{"type":"text","text":"Hello  MiXeD "}],"model":"wire-model","effort":"high","cwd":"/safe","approvalPolicy":"on-request","sandboxPolicy":{"type":"workspaceWrite"}});s.assertEqual((await s.finish(x)).status,TurnTerminalStatus.COMPLETED)
  x=await s.start(reasoning_effort="low");s.assertEqual(s.client.calls[-1][1]["effort"],"low")
 async def test_predispatch_matrix_and_no_reacquire(s):
  for v in (dict(thread_binding="bad"),dict(user_text=""),dict(user_text="x\0"),dict(user_text="x"*(MAX_TURN_INPUT_CHARS+1)),dict(model_id="unknown"),dict(model_id="hidden"),dict(reasoning_effort="bad")):
   with s.subTest(v=v):
    with s.assertRaises(TurnLifecycleError):await s.start(**v)
    s.assertFalse(s.client.calls)
  s.catalog.value=Catalog.make("wrong",1)
  with s.assertRaises(TurnLifecycleError):await s.start()
  s.catalog.value=Catalog.make("p",2)
  with s.assertRaises(TurnLifecycleError):await s.start()
  first,later=Runtime("p",1,Client()),Runtime("p",2,Client());a=CodexTurnLifecycleAdapter(Manager(first,later),Catalog("p",2))
  with s.assertRaises(TurnLifecycleError):await a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="x",working_directory=s.cwd)
  s.assertFalse(first.client.calls);s.assertFalse(later.client.calls)
 async def test_pre_and_inner_cancel(s):
  gate=asyncio.Event();hit=asyncio.Event()
  class G(Catalog):
   async def get_catalog(q,p):hit.set();await gate.wait();return await super().get_catalog(p)
  a=CodexTurnLifecycleAdapter(s.manager,G());t=asyncio.create_task(a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="x",working_directory=s.cwd));await hit.wait();t.cancel()
  with s.assertRaises(asyncio.CancelledError):await t
  gate.set();s.assertFalse(s.client.calls);s.assertNotIn(("p","Thread-A"),a._active)
  class C(Client):
   async def request(q,m,p):q.calls.append((m,p));q.dispatched.set();raise asyncio.CancelledError()
  c=C();a=CodexTurnLifecycleAdapter(Manager(Runtime(c=c)),Catalog());r=await asyncio.wait_for(a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="x",working_directory=s.cwd),.5);s.assertEqual(r.status,TurnStartStatus.UNKNOWN);s.assertEqual(r.error.category,CodexAdapterErrorCategory.TURN_START_UNKNOWN);s.assertEqual(len(c.calls),1);s.assertFalse(a._active)
 async def test_start_id_failure_and_postdispatch_cancel(s):
  for response,status in (({},TurnStartStatus.UNKNOWN),({"turn":{"id":1}},TurnStartStatus.UNKNOWN),({"turn":{"id":{}}},TurnStartStatus.UNKNOWN),({"turn":{"id":[]}},TurnStartStatus.UNKNOWN),({"turn":{"id":""}},TurnStartStatus.UNKNOWN),({"turn":{"id":"x"*513}},TurnStartStatus.UNKNOWN),({"turn":{"id":"x\0"}},TurnStartStatus.UNKNOWN),(ProtocolRemoteError(4),TurnStartStatus.REJECTED),(ProtocolFault("x"),TurnStartStatus.UNKNOWN),(OSError(),TurnStartStatus.UNKNOWN)):
   s.client.response=response;r=await s.start();s.assertEqual(r.status,status);s.assertEqual(len(s.client.calls),1);s.client.calls.clear()
  for response,status in (({"turn":{"id":"T"}},TurnStartStatus.CONFIRMED),(ProtocolRemoteError(4),TurnStartStatus.REJECTED),(ProtocolFault("x"),TurnStartStatus.UNKNOWN)):
   g=asyncio.Event();c=Client(response,g);a=CodexTurnLifecycleAdapter(Manager(Runtime(c=c)),Catalog());t=asyncio.create_task(a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="x",working_directory=s.cwd));await c.dispatched.wait();t.cancel();t.cancel();s.assertFalse(t.done())
   with s.assertRaises(TurnLifecycleError):await a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="y",working_directory=s.cwd)
   g.set();s.assertEqual((await t).status,status);s.assertEqual(len(c.calls),1)
 async def test_messages_bounds_delta_and_routing(s):
  x=await s.start();b=x.binding;await s.client.events.put({"method":"item/agentMessage/delta","params":{"threadId":b.thread_id,"turnId":b.turn_id,"itemId":"d","delta":"PRIVATE"}});await s.client.events.put(item(b," I ",""));await s.client.events.put(item(b,"cmd","OUT","commandExecution"));await s.client.events.put(item(b,"two","B"));r=await s.finish(x);s.assertEqual([(m.sequence,m.item_id,m.text)for m in r.messages],[(1," I ",""),(2,"two","B")]);s.assertNotIn("PRIVATE",repr(r));s.assertNotIn("OUT",repr(r))
  for raw in ({"method":"item/agentMessage/delta","params":{}},{"method":"item/completed","params":{}},{"method":"turn/completed","params":{}},{"method":"item/completed","params":{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{}}},{"method":"turn/completed","params":{"threadId":"Thread-A","turn":{}}}):
   x=await s.start();await s.client.events.put(raw);s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();await s.client.events.put(item(x.binding,"a","x"*MAX_AGENT_MESSAGE_CHARS));await s.client.events.put(terminal(x.binding));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.COMPLETED)
  x=await s.start();await s.client.events.put(item(x.binding,"a","x"*(MAX_AGENT_MESSAGE_CHARS+1)));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();await s.client.events.put(item(x.binding,"a","A"));await s.client.events.put(item(x.binding,"a","B"));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
 async def test_terminal_notification_retention_and_wait_cancel(s):
  for status,want in (("completed",TurnTerminalStatus.COMPLETED),("failed",TurnTerminalStatus.FAILED),("interrupted",TurnTerminalStatus.FAILED),("inProgress",TurnTerminalStatus.UNKNOWN),("bad",TurnTerminalStatus.UNKNOWN)):
   x=await s.start();await s.client.events.put(terminal(x.binding,status));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,want);s.assertNotIn(("p","Thread-A"),s.adapter._active);s.assertFalse(s.adapter._collectors);s.assertEqual(len(s.adapter._completed),1)
  x=await s.start();w=asyncio.create_task(s.adapter.wait_turn(x.binding));w.cancel()
  with s.assertRaises(asyncio.CancelledError):await w
  await s.client.events.put(terminal(x.binding));task=s.adapter._collectors[x.binding];await task;s.assertNotIn(("p","Thread-A"),s.adapter._active);a=await s.adapter.wait_turn(x.binding);s.assertIs(a,await s.adapter.wait_turn(x.binding));s.client.response={"turn":{"id":"new"}};new=await s.start();s.assertNotIn(x.binding,s.adapter._collectors);await s.client.events.put(terminal(new.binding));await s.adapter.wait_turn(new.binding)
 async def test_protocol_count_other_turn_and_late_event(s):
  x=await s.start();s.client.terminal.set();s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();b=x.binding
  for _ in range(MAX_TURN_NOTIFICATIONS):await s.client.events.put({"method":"unknown","params":{"private":"NO"}})
  await s.client.events.put({"method":"unknown","params":{}});s.assertEqual((await s.adapter.wait_turn(b)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();old=TurnBinding("p","Thread-A","old");await s.client.events.put(item(old,"old","OLD"));await s.client.events.put(terminal(old));await s.client.events.put(terminal(x.binding));s.assertEqual((await s.adapter.wait_turn(x.binding)).messages,())
 async def test_input_exact_boundary_and_preservation(s):
  text="  MiXeD\nUnicode: é  " + "x"*(MAX_TURN_INPUT_CHARS-len("  MiXeD\nUnicode: é  "))
  x=await s.start(user_text=text);s.assertEqual(s.client.calls[-1][1]["input"][0]["text"],text);await s.finish(x)
  before=len(s.client.calls)
  with s.assertRaises(TurnLifecycleError):await s.start(user_text="x"*(MAX_TURN_INPUT_CHARS+1))
  s.assertEqual(len(s.client.calls),before)
 async def test_remote_numeric_code_and_runtime_profile_mismatch(s):
  s.client.response=ProtocolRemoteError(9876);r=await s.start();s.assertEqual((r.status,r.error.category,r.error.remote_code,len(s.client.calls)),(TurnStartStatus.REJECTED,CodexAdapterErrorCategory.TURN_START_REJECTED,9876,1))
  wrong=Runtime("wrong",1,Client());m=Manager(wrong);a=CodexTurnLifecycleAdapter(m,Catalog("p",1))
  with s.assertRaises(TurnLifecycleError) as raised:await a.start_turn(thread_binding=s.thread,model_id="chosen",reasoning_effort=None,user_text="x",working_directory=s.cwd)
  s.assertEqual(raised.exception.category,CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED);s.assertEqual((m.calls,len(wrong.client.calls)),(1,0))
 async def test_exact_message_count_and_total_boundaries(s):
  x=await s.start()
  for n in range(MAX_AGENT_MESSAGES_PER_TURN):await s.client.events.put(item(x.binding,f"i{n}",""))
  await s.client.events.put(terminal(x.binding));r=await s.adapter.wait_turn(x.binding);s.assertEqual((r.status,len(r.messages)),(TurnTerminalStatus.COMPLETED,256))
  x=await s.start()
  for n in range(MAX_AGENT_MESSAGES_PER_TURN+1):await s.client.events.put(item(x.binding,f"i{n}",""))
  s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start()
  for n in range(2):await s.client.events.put(item(x.binding,f"c{n}","x"*MAX_AGENT_MESSAGE_CHARS))
  await s.client.events.put(terminal(x.binding));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.COMPLETED)
  x=await s.start()
  for n,t in enumerate(("x"*MAX_AGENT_MESSAGE_CHARS,"x"*MAX_AGENT_MESSAGE_CHARS,"x")):await s.client.events.put(item(x.binding,f"z{n}",t))
  s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
 async def test_delta_routing_matrix(s):
  x=await s.start();b=x.binding
  for d in ("","x"*MAX_AGENT_MESSAGE_CHARS):await s.client.events.put({"method":"item/agentMessage/delta","params":{"threadId":b.thread_id,"turnId":b.turn_id,"itemId":"d"+str(len(d)),"delta":d}})
  await s.client.events.put({"method":"item/agentMessage/delta","params":{"threadId":"other","turnId":b.turn_id,"itemId":"d","delta":"x"}});await s.client.events.put({"method":"item/agentMessage/delta","params":{"threadId":b.thread_id,"turnId":"other","itemId":"d","delta":"x"}});await s.client.events.put(item(b,"a","A"));await s.client.events.put(terminal(b));r=await s.adapter.wait_turn(b);s.assertEqual([m.text for m in r.messages],["A"]);s.assertNotIn("x"*MAX_AGENT_MESSAGE_CHARS,repr(r))
  invalid=[None,{}, {"threadId":b.thread_id,"turnId":b.turn_id,"delta":"x"}, {"threadId":b.thread_id,"turnId":b.turn_id,"itemId":"d","delta":1}]
  for bad in invalid:
   x=await s.start();raw={"method":"item/agentMessage/delta","params":bad};await s.client.events.put(raw);s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  for field in ("threadId","turnId","itemId"):
   for bad in (1,"","x"*513,"x\0"):
    x=await s.start();p={"threadId":x.binding.thread_id,"turnId":x.binding.turn_id,"itemId":"d","delta":"x"};p[field]=bad;await s.client.events.put({"method":"item/agentMessage/delta","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();p={"threadId":x.binding.thread_id,"turnId":x.binding.turn_id,"itemId":"d","delta":"x"*(MAX_AGENT_MESSAGE_CHARS+1)};await s.client.events.put({"method":"item/agentMessage/delta","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
 async def test_item_and_terminal_routing_matrices_and_non_agent_exclusion(s):
  invalid=[None,{}, {"threadId":"Thread-A","turnId":"Turn-AbC  123","item":None},{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{}},{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{"id":"i"}},{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{"id":1,"type":"agentMessage"}}]
  for p in invalid:
   x=await s.start();await s.client.events.put({"method":"item/completed","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();b=x.binding
  for typ,text in (("commandExecution","PRIVATE_COMMAND_STDOUT_MUST_NOT_LEAK"),("fileChange","PRIVATE_FILE_CHANGE_MUST_NOT_LEAK"),("reasoning","PRIVATE_REASONING_MUST_NOT_LEAK")):await s.client.events.put(item(b,typ,text,typ))
  await s.client.events.put(item(TurnBinding("p","other","other"),"o","OTHER"));await s.client.events.put(item(b,"ok","OK"));await s.client.events.put(terminal(b));r=await s.adapter.wait_turn(b);s.assertEqual([m.text for m in r.messages],["OK"]);s.assertNotIn("PRIVATE_",repr(r))
  for p in (None,{}, {"threadId":"Thread-A","turn":None},{"threadId":"Thread-A","turn":{}},{"threadId":"Thread-A","turn":{"id":1,"status":"completed"}},{"threadId":"Thread-A","turn":{"id":"T"}}):
   x=await s.start();await s.client.events.put({"method":"turn/completed","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();b=x.binding;await s.client.events.put(terminal(TurnBinding("p","other","other")));await s.client.events.put(terminal(b));s.assertEqual((await s.adapter.wait_turn(b)).status,TurnTerminalStatus.COMPLETED)
  x=await s.start();b=x.binding;await s.client.events.put(terminal(TurnBinding("p",b.thread_id,"other")));await s.client.events.put(terminal(b));s.assertEqual((await s.adapter.wait_turn(b)).status,TurnTerminalStatus.COMPLETED)
  for field in ("threadId","turnId"):
   for bad in (1,"","x"*513,"x\0"):
    x=await s.start();p={"threadId":x.binding.thread_id,"turnId":x.binding.turn_id,"item":{"id":"i","type":"agentMessage","text":"x"}};p[field]=bad;await s.client.events.put({"method":"item/completed","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  for bad in ("",1,"x"*513,"x\0"):
   x=await s.start();await s.client.events.put({"method":"item/completed","params":{"threadId":x.binding.thread_id,"turnId":x.binding.turn_id,"item":{"id":bad,"type":"agentMessage","text":"x"}}});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  for field in ("threadId",):
   for bad in (1,"","x"*513,"x\0"):
    x=await s.start();p={"threadId":bad,"turn":{"id":x.binding.turn_id,"status":"completed"}};await s.client.events.put({"method":"turn/completed","params":p});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  for bad in (1,"","x"*513,"x\0"):
   x=await s.start();await s.client.events.put({"method":"turn/completed","params":{"threadId":x.binding.thread_id,"turn":{"id":bad,"status":"completed"}}});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();await s.client.events.put({"method":"turn/completed","params":{"threadId":x.binding.thread_id,"turn":{"id":x.binding.turn_id,"status":"bad"}}});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
 async def test_terminal_cleanup_keeps_one_completed_result(s):
  for event in (terminal, lambda b:{"method":"turn/completed","params":{}}, None):
   x=await s.start()
   if event is None:s.client.terminal.set()
   else:await s.client.events.put(event(x.binding))
   await s.adapter.wait_turn(x.binding);key=(x.binding.profile_id,x.binding.thread_id);s.assertNotIn(key,s.adapter._active);s.assertFalse(s.adapter._collectors);s.assertEqual(s.adapter._completed[key][0],x.binding)
   if event is None:s.client.terminal=asyncio.Event()
 async def test_atomic_publication_stale_token_and_cleanup(s):
  a=CodexTurnLifecycleAdapter(s.manager,s.catalog);key=("p","Thread-A");old,new=object(),object();ba=TurnBinding("p","Thread-A","A");bb=TurnBinding("p","Thread-A","B");ra=TurnTerminalResult(ba,TurnTerminalStatus.COMPLETED,())
  a._active[key]=old;await a._publish_terminal(ba,old,ra);s.assertEqual(a._completed[key],(ba,ra));s.assertNotIn(key,a._active)
  a._active[key]=new;await a._publish_terminal(ba,old,ra);s.assertIs(a._active[key],new);s.assertEqual(a._completed[key],(ba,ra))
  rb=TurnTerminalResult(bb,TurnTerminalStatus.COMPLETED,());await a._publish_terminal(bb,new,rb);s.assertEqual(a._completed[key],(bb,rb));s.assertFalse(a._collectors);s.assertNotIn(key,a._active)
 async def test_notification_exact_boundary_and_simultaneous_terminal(s):
  x=await s.start()
  for _ in range(MAX_TURN_NOTIFICATIONS-1):await s.client.events.put({"method":"unknown","params":{}})
  await s.client.events.put(terminal(x.binding));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.COMPLETED)
  x=await s.start()
  for _ in range(MAX_TURN_NOTIFICATIONS):await s.client.events.put({"method":"unknown","params":{}})
  await s.client.events.put({"method":"unknown","params":{}});s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();b=x.binding;await s.client.events.put(item(b,"a","A"));await s.client.events.put(item(b,"b","B"));await s.client.events.put(terminal(b));s.client.terminal.set();r=await s.adapter.wait_turn(b);s.assertEqual((r.status,[m.text for m in r.messages]),(TurnTerminalStatus.COMPLETED,["A","B"]))
 async def test_late_old_turn_and_profile_independence(s):
  first=await s.start();await s.client.events.put(item(first.binding,"a","A"));await s.client.events.put(terminal(first.binding));ra=await s.adapter.wait_turn(first.binding);await s.client.events.put(item(first.binding,"late","LATE"));s.client.response={"turn":{"id":"B"}};second=await s.start();await s.client.events.put(item(second.binding,"b","B"));await s.client.events.put(terminal(second.binding));rb=await s.adapter.wait_turn(second.binding);s.assertEqual(([m.text for m in ra.messages],[m.text for m in rb.messages]),(["A"],["B"]))
  cp,cq=Client({"turn":{"id":"P"}}),Client({"turn":{"id":"Q"}});m=Manager(Runtime("p",1,cp),Runtime("q",1,cq))
  class DualCatalog:
   async def get_catalog(z,p):return Catalog.make(p,1)
  a=CodexTurnLifecycleAdapter(m,DualCatalog());tp=asyncio.create_task(a.start_turn(thread_binding=ThreadBinding("p","p-thread"),model_id="chosen",reasoning_effort=None,user_text="p",working_directory=s.cwd));tq=asyncio.create_task(a.start_turn(thread_binding=ThreadBinding("q","q-thread"),model_id="chosen",reasoning_effort=None,user_text="q",working_directory=s.cwd));p,q=await tp,await tq;s.assertEqual((len(cp.calls),len(cq.calls)),(1,1));await cp.events.put(terminal(p.binding));await cq.events.put(terminal(q.binding));s.assertEqual((await a.wait_turn(p.binding)).status,TurnTerminalStatus.COMPLETED);s.assertEqual((await a.wait_turn(q.binding)).status,TurnTerminalStatus.COMPLETED)
