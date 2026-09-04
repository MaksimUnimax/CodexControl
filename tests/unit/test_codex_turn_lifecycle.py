import asyncio
import unittest
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.protocol import ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import *

class Client:
    def __init__(self): self.calls=[]; self.events=asyncio.Queue(); self.terminal=asyncio.Event(); self.response={"turn":{"id":"Turn-AbC  123"}}
    async def request(self,m,p):
        self.calls.append((m,p))
        if isinstance(self.response, BaseException): raise self.response
        return self.response
    async def next_notification(self): return await self.events.get()
    async def wait_terminal(self): await self.terminal.wait()
class Runtime:
    def __init__(self,p="p",g=1): self.profile_id=p; self.generation=g; self.client=Client()
class Manager:
    def __init__(self,r): self.r=r; self.calls=0
    async def acquire(self,p): self.calls+=1; return self.r
class Catalog:
    def __init__(self,p="p",g=1): self.value=CodexModelCatalog(p,g,(CodexModelDescriptor("chosen","wire-model","shown",("low","high"),"high",True,False),),0,99)
    async def get_catalog(self,p): return self.value

class TurnLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime=Runtime(); self.manager=Manager(self.runtime); self.adapter=CodexTurnLifecycleAdapter(self.manager,Catalog()); self.thread=ThreadBinding("p","Thread-A"); self.cwd=TrustedWorkingDirectory("/safe")
    async def start(self): return await self.adapter.start_turn(thread_binding=self.thread,model_id="chosen",reasoning_effort=None,user_text="hello",working_directory=self.cwd)
    async def test_request_and_completed_messages_preserve_order(self):
        started=await self.start(); self.assertEqual(started.binding.turn_id,"Turn-AbC  123")
        method,params=self.runtime.client.calls[-1]; self.assertEqual(method,"turn/start"); self.assertEqual(params,{"threadId":"Thread-A","input":[{"type":"text","text":"hello"}],"model":"wire-model","effort":"high","cwd":"/safe","approvalPolicy":"on-request","sandboxPolicy":{"type":"workspaceWrite"}})
        await self.runtime.client.events.put({"method":"item/agentMessage/delta","params":{"threadId":"Thread-A","turnId":"Turn-AbC  123","itemId":"i1","delta":"not canonical"}})
        await self.runtime.client.events.put({"method":"item/completed","params":{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{"id":"i1","type":"agentMessage","text":"A"}}})
        await self.runtime.client.events.put({"method":"item/completed","params":{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{"id":"cmd","type":"commandExecution","aggregatedOutput":"PRIVATE_COMMAND_STDOUT_MUST_NOT_LEAK"}}})
        await self.runtime.client.events.put({"method":"item/completed","params":{"threadId":"Thread-A","turnId":"Turn-AbC  123","item":{"id":"i2","type":"agentMessage","text":"B"}}})
        await self.runtime.client.events.put({"method":"turn/completed","params":{"threadId":"Thread-A","turn":{"id":"Turn-AbC  123","status":"completed"}}})
        result=await self.adapter.wait_turn(started.binding); self.assertEqual(result.status,TurnTerminalStatus.COMPLETED); self.assertEqual(tuple(x.text for x in result.messages),("A","B")); self.assertNotIn("not canonical",repr(result))
    async def test_remote_error_and_bad_result_are_not_retried(self):
        self.runtime.client.response=ProtocolRemoteError(41); result=await self.start(); self.assertEqual(result.status,TurnStartStatus.REJECTED); self.assertEqual(result.error.remote_code,41); self.assertEqual(len(self.runtime.client.calls),1)
        self.runtime.client.response={"turn":{}}; result=await self.start(); self.assertEqual(result.status,TurnStartStatus.UNKNOWN); self.assertEqual(len(self.runtime.client.calls),2)
    async def test_invalid_input_and_busy_do_not_send_second_rpc(self):
        with self.assertRaises(TurnLifecycleError): await self.adapter.start_turn(thread_binding=self.thread,model_id="chosen",reasoning_effort=None,user_text="",working_directory=self.cwd)
        first=await self.start()
        with self.assertRaises(TurnLifecycleError): await self.start()
        self.assertEqual(len(self.runtime.client.calls),1)
        await self.runtime.client.events.put({"method":"turn/completed","params":{"threadId":"Thread-A","turn":{"id":first.binding.turn_id,"status":"failed"}}}); self.assertEqual((await self.adapter.wait_turn(first.binding)).status,TurnTerminalStatus.FAILED)
    async def test_duplicate_and_protocol_terminal_fail_closed(self):
        first=await self.start(); p={"threadId":"Thread-A","turnId":first.binding.turn_id,"item":{"id":"i","type":"agentMessage","text":"A"}}
        await self.runtime.client.events.put({"method":"item/completed","params":p}); await self.runtime.client.events.put({"method":"item/completed","params":p})
        self.assertEqual((await self.adapter.wait_turn(first.binding)).status,TurnTerminalStatus.UNKNOWN)
        second=await self.start(); self.runtime.client.terminal.set(); self.assertEqual((await self.adapter.wait_turn(second.binding)).status,TurnTerminalStatus.UNKNOWN)
    async def test_waiter_cancellation_does_not_cancel_collector(self):
        start=await self.start(); waiter=asyncio.create_task(self.adapter.wait_turn(start.binding)); waiter.cancel()
        with self.assertRaises(asyncio.CancelledError): await waiter
        await self.runtime.client.events.put({"method":"turn/completed","params":{"threadId":"Thread-A","turn":{"id":start.binding.turn_id,"status":"completed"}}})
        self.assertEqual((await self.adapter.wait_turn(start.binding)).status,TurnTerminalStatus.COMPLETED)
