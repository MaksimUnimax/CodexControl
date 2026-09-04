"""Exact 0.144.6 turn start and completed-agent-message projection."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol
from .errors import CodexAdapterError, CodexAdapterErrorCategory
from .model_catalog import CodexModelCatalogAdapter
from .protocol import ProtocolRemoteError
from .thread_lifecycle import ThreadBinding, TrustedWorkingDirectory

MAX_TURN_ID_CHARS=512; MAX_TURN_ITEM_ID_CHARS=512; MAX_TURN_INPUT_CHARS=65536
MAX_AGENT_MESSAGE_CHARS=1000000; MAX_AGENT_MESSAGES_PER_TURN=256; MAX_TOTAL_AGENT_MESSAGE_CHARS=2000000; MAX_TURN_NOTIFICATIONS=16384
TURN_START_METHOD="turn/start"

class TurnLifecycleError(Exception):
    _ALLOWED=frozenset((CodexAdapterErrorCategory.TURN_REQUEST_INVALID,CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED,CodexAdapterErrorCategory.TURN_OPERATION_BUSY,CodexAdapterErrorCategory.TURN_START_REJECTED,CodexAdapterErrorCategory.TURN_START_UNKNOWN,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN,CodexAdapterErrorCategory.TURN_TERMINAL_FAILED))
    def __init__(self, category: CodexAdapterErrorCategory|str)->None:
        try: parsed=CodexAdapterErrorCategory(category)
        except (TypeError,ValueError): parsed=CodexAdapterErrorCategory.TURN_REQUEST_INVALID
        self.category=parsed if parsed in self._ALLOWED else CodexAdapterErrorCategory.TURN_REQUEST_INVALID; super().__init__(self.category.value)
def _opaque(value:Any,limit:int,category:CodexAdapterErrorCategory=CodexAdapterErrorCategory.TURN_REQUEST_INVALID)->str:
    if not isinstance(value,str) or not value or "\0" in value or len(value)>limit: raise TurnLifecycleError(category)
    return value

@dataclass(frozen=True)
class TurnBinding:
    profile_id:str; thread_id:str; turn_id:str
    def __post_init__(self)->None:
        if not isinstance(self.profile_id,str) or not self.profile_id: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        _opaque(self.thread_id,512); _opaque(self.turn_id,MAX_TURN_ID_CHARS)
@dataclass(frozen=True)
class AgentMessageCompleted: sequence:int; item_id:str; text:str
class TurnStartStatus(StrEnum): CONFIRMED="TURN_START_CONFIRMED"; REJECTED="TURN_START_REJECTED"; UNKNOWN="TURN_START_UNKNOWN"
class TurnTerminalStatus(StrEnum): COMPLETED="COMPLETED"; FAILED="FAILED"; UNKNOWN="UNKNOWN"
@dataclass(frozen=True)
class TurnStartResult: status:TurnStartStatus; binding:TurnBinding|None=None; error:CodexAdapterError|None=None
@dataclass(frozen=True)
class TurnTerminalResult: binding:TurnBinding; status:TurnTerminalStatus; messages:tuple[AgentMessageCompleted,...]; error:CodexAdapterError|None=None
class RuntimeManagerLike(Protocol):
    async def acquire(self,profile_id:str)->Any: ...

class CodexTurnLifecycleAdapter:
    def __init__(self,manager:RuntimeManagerLike,catalog:CodexModelCatalogAdapter)->None:
        self._manager,self._catalog=manager,catalog; self._lock=asyncio.Lock(); self._active:dict[tuple[str,str],object]={}; self._collectors:dict[TurnBinding,asyncio.Task[TurnTerminalResult]]={}
    async def start_turn(self,*,thread_binding:ThreadBinding,model_id:str,reasoning_effort:str|None,user_text:str,working_directory:TrustedWorkingDirectory)->TurnStartResult:
        if not isinstance(thread_binding,ThreadBinding) or not isinstance(model_id,str) or not model_id or "\0" in model_id or not isinstance(working_directory,TrustedWorkingDirectory) or not isinstance(user_text,str) or not user_text or "\0" in user_text or len(user_text)>MAX_TURN_INPUT_CHARS: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        key=(thread_binding.profile_id,thread_binding.thread_id); token=object()
        async with self._lock:
            if key in self._active: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_OPERATION_BUSY)
            self._active[key]=token
        keep=False
        try:
            runtime=await self._manager.acquire(thread_binding.profile_id); catalog=await self._catalog.get_catalog(thread_binding.profile_id)
            if runtime.profile_id!=thread_binding.profile_id or catalog.profile_id!=thread_binding.profile_id or runtime.generation!=catalog.runtime_generation: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
            descriptor=catalog.resolve_model(model_id); effort=catalog.validate_reasoning_effort(model_id,reasoning_effort)
            params={"threadId":thread_binding.thread_id,"input":[{"type":"text","text":user_text}],"model":descriptor.wire_model,"effort":effort,"cwd":working_directory.path,"approvalPolicy":"on-request","sandboxPolicy":{"type":"workspaceWrite"}}
            result=await self._request(runtime,params)
            if result.status is not TurnStartStatus.CONFIRMED:return result
            assert result.binding is not None
            self._collectors[result.binding]=asyncio.create_task(self._collect(runtime,result.binding,token)); keep=True
            return result
        except asyncio.CancelledError: raise
        except TurnLifecycleError: raise
        except Exception as error: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED) from error
        finally:
            if not keep: await self._release(key,token)
    async def _request(self,runtime:Any,params:dict[str,Any])->TurnStartResult:
        dispatched=asyncio.Event()
        async def invoke()->Any: dispatched.set(); return await runtime.client.request(TURN_START_METHOD,params)
        task=asyncio.create_task(invoke())
        while True:
            try: response=await asyncio.shield(task); break
            except asyncio.CancelledError:
                if not dispatched.is_set(): task.cancel(); await asyncio.gather(task,return_exceptions=True); raise
                continue
            except ProtocolRemoteError as error:return TurnStartResult(TurnStartStatus.REJECTED,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_REJECTED,remote_code=error.code))
            except Exception:return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
        try: turn_id=_opaque(response.get("turn",{}).get("id") if isinstance(response,dict) and isinstance(response.get("turn"),dict) else None,MAX_TURN_ID_CHARS,CodexAdapterErrorCategory.TURN_START_UNKNOWN)
        except TurnLifecycleError:return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
        return TurnStartResult(TurnStartStatus.CONFIRMED,TurnBinding(runtime.profile_id,params["threadId"],turn_id))
    async def wait_turn(self,binding:TurnBinding)->TurnTerminalResult:
        if not isinstance(binding,TurnBinding):raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        task=self._collectors.get(binding)
        if task is None:raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        return await asyncio.shield(task)
    async def _collect(self,runtime:Any,binding:TurnBinding,token:object)->TurnTerminalResult:
        messages:list[AgentMessageCompleted]=[]; seen:set[str]=set(); count=0; notification=asyncio.create_task(runtime.client.next_notification()); terminal=asyncio.create_task(runtime.client.wait_terminal())
        try:
            while True:
                done,_=await asyncio.wait((notification,terminal),return_when=asyncio.FIRST_COMPLETED)
                if notification in done:
                    try: raw=notification.result()
                    except Exception:return self._unknown(binding,messages)
                    notification=asyncio.create_task(runtime.client.next_notification()); count+=1
                    if count>MAX_TURN_NOTIFICATIONS:return self._unknown(binding,messages)
                    outcome=self._consume(raw,binding,messages,seen)
                    if outcome is not None:return outcome
                    continue
                return self._unknown(binding,messages)
        finally:
            notification.cancel(); terminal.cancel(); await asyncio.gather(notification,terminal,return_exceptions=True); self._collectors.pop(binding,None); await self._release((binding.profile_id,binding.thread_id),token)
    def _unknown(self,binding:TurnBinding,messages:list[AgentMessageCompleted])->TurnTerminalResult:return TurnTerminalResult(binding,TurnTerminalStatus.UNKNOWN,tuple(messages),CodexAdapterError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN))
    def _consume(self,raw:Any,binding:TurnBinding,messages:list[AgentMessageCompleted],seen:set[str])->TurnTerminalResult|None:
        if not isinstance(raw,dict) or not isinstance(raw.get("method"),str) or not isinstance(raw.get("params"),dict):return None
        method,p=raw["method"],raw["params"]
        if method=="item/agentMessage/delta":
            if p.get("threadId")!=binding.thread_id or p.get("turnId")!=binding.turn_id:return None
            try:_opaque(p.get("itemId"),MAX_TURN_ITEM_ID_CHARS); _opaque(p.get("delta"),MAX_AGENT_MESSAGE_CHARS)
            except TurnLifecycleError:return self._unknown(binding,messages)
            return None
        if method=="item/completed":
            if p.get("threadId")!=binding.thread_id or p.get("turnId")!=binding.turn_id:return None
            item=p.get("item")
            if not isinstance(item,dict) or not isinstance(item.get("type"),str):return self._unknown(binding,messages)
            if item["type"]!="agentMessage":return None
            try:
                iid=_opaque(item.get("id"),MAX_TURN_ITEM_ID_CHARS); text=_opaque(item.get("text"),MAX_AGENT_MESSAGE_CHARS)
                if iid in seen or len(messages)>=MAX_AGENT_MESSAGES_PER_TURN or sum(len(m.text) for m in messages)+len(text)>MAX_TOTAL_AGENT_MESSAGE_CHARS:raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            seen.add(iid); messages.append(AgentMessageCompleted(len(messages)+1,iid,text)); return None
        if method=="turn/completed":
            turn=p.get("turn")
            if p.get("threadId")!=binding.thread_id or not isinstance(turn,dict) or turn.get("id")!=binding.turn_id:return None
            if turn.get("status")=="completed":return TurnTerminalResult(binding,TurnTerminalStatus.COMPLETED,tuple(messages))
            if turn.get("status") in ("failed","interrupted"):return TurnTerminalResult(binding,TurnTerminalStatus.FAILED,tuple(messages),CodexAdapterError(CodexAdapterErrorCategory.TURN_TERMINAL_FAILED))
            return self._unknown(binding,messages)
        return None
    async def _release(self,key:tuple[str,str],token:object)->None:
        async with self._lock:
            if self._active.get(key) is token:self._active.pop(key,None)
