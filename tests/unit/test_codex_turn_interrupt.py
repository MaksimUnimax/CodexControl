import asyncio,json,unittest
from pathlib import Path
from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog,CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolFault,ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding,TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import *
class C:
 def __init__(s):s.calls=[];s.events=asyncio.Queue();s.gate=None;s.response={};s.hit=asyncio.Event();s.consumers=0
 async def request(s,m,p):
  s.calls.append((m,p))
  if m=="turn/start":return {"turn":{"id":"T"}}
  s.hit.set()
  if s.gate:await s.gate.wait()
  if isinstance(s.response,BaseException):raise s.response
  return s.response
 async def next_notification(s):s.consumers+=1;return await s.events.get()
 async def wait_terminal(s):await asyncio.Event().wait()
class R:
 def __init__(s,p,c):s.profile_id=p;s.generation=1;s.client=c
class M:
 def __init__(s,*r):s.r=r;s.calls=0
 async def acquire(s,p):v=s.r[s.calls];s.calls+=1;return v
class K:
 async def get_catalog(s,p):return CodexModelCatalog(p,1,(CodexModelDescriptor("m","m","m",("low",),"low",True,False),),0,1)
def end(b,status="completed"):return {"method":"turn/completed","params":{"threadId":b.thread_id,"turn":{"id":b.turn_id,"status":status}}}
class Tests(unittest.IsolatedAsyncioTestCase):
 async def make(s):
  s.c=C();s.m=M(R("p",s.c),R("p",C()));s.a=CodexTurnLifecycleAdapter(s.m,K());s.r=await s.a.start_turn(thread_binding=ThreadBinding("p","th"),model_id="m",reasoning_effort=None,user_text="x",working_directory=TrustedWorkingDirectory("/safe"));return s.r.binding
 async def done(s,b,status="completed"):await s.c.events.put(end(b,status));return await s.a.wait_turn(b)
 def test_fixture_exact(s):
  d=json.loads((Path(__file__).parents[1]/"fixtures/codex_app_server_0_144_6/turn_interrupt_protocol.json").read_text());s.assertEqual((d["codex_version"],d["schema_sha256"],d["turn_interrupt_method"]),("0.144.6","40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466","turn/interrupt"));s.assertEqual((d["request_properties"],d["required_fields"]),(["threadId","turnId"],["threadId","turnId"]));s.assertEqual((d["thread_id_type"],d["turn_id_type"],d["thread_id_nullable"],d["turn_id_nullable"],d["thread_id_min_length"],d["turn_id_min_length"]),("string","string",False,False,None,None));s.assertEqual((d["response_json_type"],d["response_properties"],d["response_required_fields"],d["response_additional_properties"]),("object",[],[],True));s.assertFalse(d["product_startup_interrupt_allowed"]);s.assertEqual(d["behavioral_semantics_source"],"exact Codex 0.144.6 / ADR-0015")
 async def test_same_runtime_exact_shape_confirmed(s):
  b=await s.make();t=asyncio.create_task(s.a.interrupt_turn(b));await s.c.hit.wait();s.assertEqual((s.m.calls,s.c.calls[-1]),(1,("turn/interrupt",{"threadId":"th","turnId":"T"})));await s.done(b);r=await t;s.assertEqual((r.status,r.terminal_result.status),(TurnInterruptStatus.CONFIRMED,TurnTerminalStatus.COMPLETED))
 async def test_active_busy_rejection_and_ambiguity(s):
  b=await s.make()
  for x in ("bad",TurnBinding("p","th","T"),TurnBinding("p","th","other")):
   with s.assertRaises(TurnLifecycleError):await s.a.interrupt_turn(x)
  s.c.gate=asyncio.Event();t=asyncio.create_task(s.a.interrupt_turn(b));await s.c.hit.wait()
  with s.assertRaises(TurnLifecycleError) as x:await s.a.interrupt_turn(b)
  s.assertEqual(x.exception.category,CodexAdapterErrorCategory.TURN_INTERRUPT_BUSY);s.c.gate.set();await s.done(b);await t
  b=await s.make();s.c.response=ProtocolRemoteError(9876);r=await s.a.interrupt_turn(b);s.assertEqual((r.status,r.error.category,r.error.remote_code),(TurnInterruptStatus.REJECTED,CodexAdapterErrorCategory.TURN_INTERRUPT_REJECTED,9876));await s.done(b)
  b=await s.make();s.c.response=ProtocolFault("PRIVATE_REMOTE_ERROR_MUST_NOT_LEAK");t=asyncio.create_task(s.a.interrupt_turn(b));await s.c.hit.wait();await s.done(b,"failed");r=await t;s.assertEqual(r.status,TurnInterruptStatus.RECONCILED)
 async def test_success_unknown_and_cancel(s):
  b=await s.make();before=s.c.consumers;t=asyncio.create_task(s.a.interrupt_turn(b));await s.c.hit.wait();await s.c.events.put({"method":"turn/completed","params":{}});r=await t;s.assertEqual((r.status,r.error.category),(TurnInterruptStatus.UNKNOWN,CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN));s.assertEqual(s.c.consumers,before+1)
  b=await s.make();s.c.gate=asyncio.Event();t=asyncio.create_task(s.a.interrupt_turn(b));await s.c.hit.wait();t.cancel();t.cancel();s.c.gate.set();await asyncio.sleep(0);s.assertFalse(t.done());await s.done(b);s.assertEqual((await t).status,TurnInterruptStatus.CONFIRMED)
