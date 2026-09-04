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
  s.assertEqual((a["thread_id_request_field"],a["plain_text_input_source_shape"],a["model_wire_field"],a["reasoning_effort_field"],a["cwd_field"],a["config_field"],a["turn_id_result_path"]),("threadId",{"type":"text","text":"string"},"model","effort","cwd","absent","turn.id"));s.assertEqual((a["approval_field"],a["sandbox_field"]),("approvalPolicy:on-request","sandboxPolicy:{type:workspaceWrite}"));s.assertEqual((e["agent_message_delta_method"],e["item_completed_method"],e["turn_terminal_method"]),("item/agentMessage/delta","item/completed","turn/completed"));s.assertEqual(e["completed_item_identity_paths"],["threadId","turnId","item.id"]);s.assertEqual(e["terminal_status_values"],["completed","interrupted","failed","inProgress"]);s.assertIsNone(e["agent_message_text_min_length"]);s.assertIsNone(e["delta_min_length"])
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
   x=await s.start();await s.client.events.put(terminal(x.binding,status));s.assertEqual((await s.adapter.wait_turn(x.binding)).status,want)
  x=await s.start();w=asyncio.create_task(s.adapter.wait_turn(x.binding));w.cancel()
  with s.assertRaises(asyncio.CancelledError):await w
  await s.client.events.put(terminal(x.binding));task=s.adapter._collectors[x.binding];await task;s.assertNotIn(("p","Thread-A"),s.adapter._active);a=await s.adapter.wait_turn(x.binding);s.assertIs(a,await s.adapter.wait_turn(x.binding));s.client.response={"turn":{"id":"new"}};new=await s.start();s.assertNotIn(x.binding,s.adapter._collectors);await s.client.events.put(terminal(new.binding));await s.adapter.wait_turn(new.binding)
 async def test_protocol_count_other_turn_and_late_event(s):
  x=await s.start();s.client.terminal.set();s.assertEqual((await s.adapter.wait_turn(x.binding)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();b=x.binding
  for _ in range(MAX_TURN_NOTIFICATIONS):await s.client.events.put({"method":"unknown","params":{"private":"NO"}})
  await s.client.events.put({"method":"unknown","params":{}});s.assertEqual((await s.adapter.wait_turn(b)).status,TurnTerminalStatus.UNKNOWN)
  x=await s.start();old=TurnBinding("p","Thread-A","old");await s.client.events.put(item(old,"old","OLD"));await s.client.events.put(terminal(old));await s.client.events.put(terminal(x.binding));s.assertEqual((await s.adapter.wait_turn(x.binding)).messages,())
