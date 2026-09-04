"""Exact 0.144.6 turn start and completed-agent-message projection."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from .errors import CodexAdapterError, CodexAdapterErrorCategory
from .model_catalog import CodexModelCatalogAdapter
from .protocol import ProtocolRemoteError
from .thread_lifecycle import ThreadBinding, TrustedWorkingDirectory

MAX_TURN_ID_CHARS=512; MAX_TURN_ITEM_ID_CHARS=512; MAX_TURN_INPUT_CHARS=65536
MAX_AGENT_MESSAGE_CHARS=1000000; MAX_AGENT_MESSAGES_PER_TURN=256; MAX_TOTAL_AGENT_MESSAGE_CHARS=2000000; MAX_TURN_NOTIFICATIONS=16384
TURN_START_METHOD="turn/start"
TURN_INTERRUPT_METHOD="turn/interrupt"

class TurnLifecycleError(Exception):
    _ALLOWED=frozenset((CodexAdapterErrorCategory.TURN_REQUEST_INVALID,CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED,CodexAdapterErrorCategory.TURN_OPERATION_BUSY,CodexAdapterErrorCategory.TURN_START_REJECTED,CodexAdapterErrorCategory.TURN_START_UNKNOWN,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN,CodexAdapterErrorCategory.TURN_TERMINAL_FAILED,CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE,CodexAdapterErrorCategory.TURN_INTERRUPT_BUSY,CodexAdapterErrorCategory.TURN_INTERRUPT_REJECTED,CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN))
    def __init__(self, category: CodexAdapterErrorCategory|str)->None:
        try: parsed=CodexAdapterErrorCategory(category)
        except (TypeError,ValueError): parsed=CodexAdapterErrorCategory.TURN_REQUEST_INVALID
        self.category=parsed if parsed in self._ALLOWED else CodexAdapterErrorCategory.TURN_REQUEST_INVALID; super().__init__(self.category.value)
def _opaque(value:Any,limit:int,category:CodexAdapterErrorCategory=CodexAdapterErrorCategory.TURN_REQUEST_INVALID)->str:
    if not isinstance(value,str) or not value or "\0" in value or len(value)>limit: raise TurnLifecycleError(category)
    return value

def _content(value:Any,limit:int)->str:
    """Installed event content is a JSON string, not an opaque identifier.

    The 0.144.6 schema has no minLength for agent text or delta text.  In
    particular an empty completed agent message is a valid remote value.
    """
    if not isinstance(value,str) or len(value)>limit:
        raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
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
class TurnInterruptStatus(StrEnum): CONFIRMED="CONFIRMED"; RECONCILED="RECONCILED"; REJECTED="REJECTED"; UNKNOWN="UNKNOWN"
@dataclass(frozen=True)
class TurnStartResult: status:TurnStartStatus; binding:TurnBinding|None=None; error:CodexAdapterError|None=None
@dataclass(frozen=True)
class TurnTerminalResult: binding:TurnBinding; status:TurnTerminalStatus; messages:tuple[AgentMessageCompleted,...]; error:CodexAdapterError|None=None
@dataclass(frozen=True)
class TurnInterruptResult:
    status:TurnInterruptStatus; binding:TurnBinding; terminal_result:TurnTerminalResult|None=None; error:CodexAdapterError|None=None
    def __repr__(self)->str:
        """Keep terminal message payloads out of generic diagnostics."""
        terminal_status = self.terminal_result.status.value if self.terminal_result is not None else None
        error_category = self.error.category.value if self.error is not None else None
        return (
            "TurnInterruptResult("
            f"status={self.status.value!r}, profile_id={self.binding.profile_id!r}, "
            f"thread_id={self.binding.thread_id!r}, turn_id={self.binding.turn_id!r}, "
            f"terminal_status={terminal_status!r}, error_category={error_category!r})"
        )
@dataclass(frozen=True)
class _ActiveTurn:
    binding:TurnBinding; token:object=field(repr=False,compare=False); runtime:Any=field(repr=False,compare=False)
class RuntimeManagerLike(Protocol):
    async def acquire(self,profile_id:str)->Any: ...

class CodexTurnLifecycleAdapter:
    def __init__(self,manager:RuntimeManagerLike,catalog:CodexModelCatalogAdapter)->None:
        self._manager,self._catalog=manager,catalog; self._lock=asyncio.Lock(); self._active:dict[tuple[str,str],object]={}; self._active_turns:dict[TurnBinding,_ActiveTurn]={}; self._interrupts:dict[tuple[str,str],object]={}; self._collectors:dict[TurnBinding,asyncio.Task[TurnTerminalResult]]={}; self._completed:dict[tuple[str,str],tuple[TurnBinding,TurnTerminalResult]]={}
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
            if descriptor.hidden:
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
            params={"threadId":thread_binding.thread_id,"input":[{"type":"text","text":user_text}],"model":descriptor.wire_model,"effort":effort,"cwd":working_directory.path,"approvalPolicy":"on-request","sandboxPolicy":{"type":"workspaceWrite"}}
            result=await self._request(runtime,params)
            if result.status is not TurnStartStatus.CONFIRMED:return result
            assert result.binding is not None
            # Confirmation is the sole supersession point.  Publication and
            # replacement use the same lock, so no task-done observation is
            # needed to enforce one retained result per profile/thread key.
            async with self._lock:
                if self._active.get(key) is not token:
                    return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
                self._completed.pop(key,None)
                self._active_turns[result.binding]=_ActiveTurn(result.binding,token,runtime)
                self._collectors[result.binding]=asyncio.create_task(self._collect(runtime,result.binding,token))
                keep=True
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
                # A CancelledError can be from this public caller or from the
                # owned request itself.  Once dispatched, only the former is
                # deferred; an inner cancellation is an ambiguous start.
                if task.cancelled():
                    return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
                if not dispatched.is_set(): task.cancel(); await asyncio.gather(task,return_exceptions=True); raise
                continue
            except ProtocolRemoteError as error:return TurnStartResult(TurnStartStatus.REJECTED,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_REJECTED,remote_code=error.code))
            except Exception:return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
        try: turn_id=_opaque(response.get("turn",{}).get("id") if isinstance(response,dict) and isinstance(response.get("turn"),dict) else None,MAX_TURN_ID_CHARS,CodexAdapterErrorCategory.TURN_START_UNKNOWN)
        except TurnLifecycleError:return TurnStartResult(TurnStartStatus.UNKNOWN,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_START_UNKNOWN))
        return TurnStartResult(TurnStartStatus.CONFIRMED,TurnBinding(runtime.profile_id,params["threadId"],turn_id))
    async def wait_turn(self,binding:TurnBinding)->TurnTerminalResult:
        if not isinstance(binding,TurnBinding):raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        key=(binding.profile_id,binding.thread_id)
        async with self._lock:
            task=self._collectors.get(binding)
            completed=self._completed.get(key)
            if task is None and (completed is None or completed[0] != binding):
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
            if task is None:
                return completed[1]
        return await asyncio.shield(task)
    async def _before_interrupt_dispatch(self)->None:
        """Test seam only: production has no pre-dispatch work."""
    async def interrupt_turn(self,binding:TurnBinding)->TurnInterruptResult:
        if not isinstance(binding,TurnBinding): raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        key=(binding.profile_id,binding.thread_id); reservation=object()
        async with self._lock:
            active=self._active_turns.get(binding)
            collector=self._collectors.get(binding)
            # Identity, rather than dataclass equality, rejects reconstructed
            # values and values owned by a different lifecycle adapter.
            if active is None or active.binding is not binding or collector is None:
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE)
            if key in self._interrupts: raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_INTERRUPT_BUSY)
            self._interrupts[key]=reservation
        dispatched=asyncio.Event()
        async def invoke()->Any:
            await self._before_interrupt_dispatch()
            dispatched.set()
            return await active.runtime.client.request(TURN_INTERRUPT_METHOD,{"threadId":binding.thread_id,"turnId":binding.turn_id})
        request=asyncio.create_task(invoke())
        try:
            wire="unknown"
            while True:
                try:
                    response=await asyncio.shield(request)
                    wire="success" if isinstance(response,dict) else "ambiguous"
                    break
                except asyncio.CancelledError:
                    if request.cancelled():
                        wire="ambiguous"; break
                    if not dispatched.is_set():
                        request.cancel(); await asyncio.gather(request,return_exceptions=True); raise
                    continue
                except ProtocolRemoteError as error:
                    terminal=self._definitive_if_done(collector)
                    if terminal is not None:return TurnInterruptResult(TurnInterruptStatus.RECONCILED,binding,terminal)
                    return TurnInterruptResult(TurnInterruptStatus.REJECTED,binding,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_INTERRUPT_REJECTED,remote_code=error.code))
                except Exception: wire="ambiguous"; break
            terminal=await self._interrupt_terminal(collector)
            if wire=="success" and terminal is not None:return TurnInterruptResult(TurnInterruptStatus.CONFIRMED,binding,terminal)
            if wire!="success" and terminal is not None:return TurnInterruptResult(TurnInterruptStatus.RECONCILED,binding,terminal)
            return TurnInterruptResult(TurnInterruptStatus.UNKNOWN,binding,error=CodexAdapterError(CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN))
        finally:
            # The request is always owned through completion after dispatch;
            # pre-dispatch cancellation explicitly cancels it above.
            if dispatched.is_set() and not request.done():
                while True:
                    try: await asyncio.shield(request); break
                    except asyncio.CancelledError: continue
                    except Exception: break
            await self._release_interrupt(key,reservation)
    def _definitive_if_done(self,collector:asyncio.Task[TurnTerminalResult])->TurnTerminalResult|None:
        if not collector.done() or collector.cancelled(): return None
        try: result=collector.result()
        except Exception: return None
        return result if result.status in (TurnTerminalStatus.COMPLETED,TurnTerminalStatus.FAILED) else None
    async def _interrupt_terminal(self,collector:asyncio.Task[TurnTerminalResult])->TurnTerminalResult|None:
        while True:
            try:
                result=await asyncio.shield(collector)
                return result if result.status in (TurnTerminalStatus.COMPLETED,TurnTerminalStatus.FAILED) else None
            except asyncio.CancelledError:
                if collector.cancelled():
                    return None
                continue
            except Exception:return None
    async def _release_interrupt(self,key:tuple[str,str],reservation:object)->None:
        async with self._lock:
            if self._interrupts.get(key) is reservation:self._interrupts.pop(key,None)
    async def _collect(self,runtime:Any,binding:TurnBinding,token:object)->TurnTerminalResult:
        messages:list[AgentMessageCompleted]=[]; seen:set[str]=set(); count=0; notification=asyncio.create_task(runtime.client.next_notification()); terminal=asyncio.create_task(runtime.client.wait_terminal()); result=self._unknown(binding,messages)
        try:
            while True:
                done,_=await asyncio.wait((notification,terminal),return_when=asyncio.FIRST_COMPLETED)
                if notification in done:
                    try: raw=notification.result()
                    except Exception:
                        result=self._unknown(binding,messages); break
                    notification=asyncio.create_task(runtime.client.next_notification()); count+=1
                    if count>MAX_TURN_NOTIFICATIONS:
                        result=self._unknown(binding,messages); break
                    outcome=self._consume(raw,binding,messages,seen)
                    if outcome is not None:
                        result=outcome; break
                    continue
                result=self._unknown(binding,messages); break
        finally:
            notification.cancel(); terminal.cancel(); await asyncio.gather(notification,terminal,return_exceptions=True)
            await self._publish_terminal(binding,token,result)
        return result
    def _unknown(self,binding:TurnBinding,messages:list[AgentMessageCompleted])->TurnTerminalResult:return TurnTerminalResult(binding,TurnTerminalStatus.UNKNOWN,tuple(messages),CodexAdapterError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN))
    def _consume(self,raw:Any,binding:TurnBinding,messages:list[AgentMessageCompleted],seen:set[str])->TurnTerminalResult|None:
        if not isinstance(raw,dict) or not isinstance(raw.get("method"),str):return None
        method=raw["method"]
        if method not in ("item/agentMessage/delta","item/completed","turn/completed"):return None
        p=raw.get("params")
        if not isinstance(p,dict):return self._unknown(binding,messages)
        try: thread_id=_opaque(p.get("threadId"),512,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
        except TurnLifecycleError:return self._unknown(binding,messages)
        if method=="item/agentMessage/delta":
            try:_opaque(p.get("itemId"),MAX_TURN_ITEM_ID_CHARS,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN); _content(p.get("delta"),MAX_AGENT_MESSAGE_CHARS)
            except TurnLifecycleError:return self._unknown(binding,messages)
            try: turn_id=_opaque(p.get("turnId"),MAX_TURN_ID_CHARS,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            if thread_id!=binding.thread_id or turn_id!=binding.turn_id:return None
            return None
        if method=="item/completed":
            item=p.get("item")
            if not isinstance(item,dict) or not isinstance(item.get("type"),str):return self._unknown(binding,messages)
            try: turn_id=_opaque(p.get("turnId"),MAX_TURN_ID_CHARS,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            try: item_id=_opaque(item.get("id"),MAX_TURN_ITEM_ID_CHARS,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            if thread_id!=binding.thread_id or turn_id!=binding.turn_id:return None
            if item["type"]!="agentMessage":return None
            try:
                iid=item_id; text=_content(item.get("text"),MAX_AGENT_MESSAGE_CHARS)
                if iid in seen or len(messages)>=MAX_AGENT_MESSAGES_PER_TURN or sum(len(m.text) for m in messages)+len(text)>MAX_TOTAL_AGENT_MESSAGE_CHARS:raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            seen.add(iid); messages.append(AgentMessageCompleted(len(messages)+1,iid,text)); return None
        if method=="turn/completed":
            turn=p.get("turn")
            if not isinstance(turn,dict):return self._unknown(binding,messages)
            try: turn_id=_opaque(turn.get("id"),MAX_TURN_ID_CHARS,CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
            except TurnLifecycleError:return self._unknown(binding,messages)
            if turn.get("status") not in ("completed","failed","interrupted","inProgress"):return self._unknown(binding,messages)
            if thread_id!=binding.thread_id or turn_id!=binding.turn_id:return None
            if turn.get("status")=="completed":return TurnTerminalResult(binding,TurnTerminalStatus.COMPLETED,tuple(messages))
            if turn.get("status") in ("failed","interrupted"):return TurnTerminalResult(binding,TurnTerminalStatus.FAILED,tuple(messages),CodexAdapterError(CodexAdapterErrorCategory.TURN_TERMINAL_FAILED))
            return self._unknown(binding,messages)
        return None
    async def _release(self,key:tuple[str,str],token:object)->None:
        async with self._lock:
            if self._active.get(key) is token:self._active.pop(key,None)
    async def _publish_terminal(self,binding:TurnBinding,token:object,result:TurnTerminalResult)->None:
        """Atomically publish only the terminal state still owned by *token*."""
        key=(binding.profile_id,binding.thread_id)
        current=asyncio.current_task()
        async with self._lock:
            if self._active.get(key) is not token:
                return
            self._active.pop(key,None)
            if self._collectors.get(binding) is current:
                self._collectors.pop(binding,None)
            active=self._active_turns.get(binding)
            if active is not None and active.token is token:
                self._active_turns.pop(binding,None)
            self._completed[key]=(binding,result)
