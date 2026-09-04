"""Fail-closed, profile-bound approval bridge (fake operator only)."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from .protocol import (APPROVAL_SERVER_REQUEST_METHODS, CodexProtocolClient, InboundServerRequest, ProtocolApprovalResponseUnknown, ProtocolState)

COMMAND="item/commandExecution/requestApproval"; FILE_CHANGE="item/fileChange/requestApproval"; PERMISSIONS="item/permissions/requestApproval"; APPLY_PATCH="applyPatchApproval"; EXEC_COMMAND="execCommandApproval"; APPROVAL_METHODS=APPROVAL_SERVER_REQUEST_METHODS
MAX_APPROVAL_ID_CHARS=512; MAX_APPROVAL_CONTEXT_LINES=32; MAX_APPROVAL_CONTEXT_LINE_CHARS=2048; MAX_APPROVAL_CONTEXT_TOTAL_CHARS=8192
class ApprovalDecision(StrEnum): ALLOW="ALLOW"; DENY="DENY"
class ApprovalKind(StrEnum): COMMAND_EXECUTION="command_execution"; FILE_CHANGE="file_change"; PERMISSIONS="permissions"; APPLY_PATCH="apply_patch"; EXEC_COMMAND="exec_command"
_KINDS={COMMAND:ApprovalKind.COMMAND_EXECUTION,FILE_CHANGE:ApprovalKind.FILE_CHANGE,PERMISSIONS:ApprovalKind.PERMISSIONS,APPLY_PATCH:ApprovalKind.APPLY_PATCH,EXEC_COMMAND:ApprovalKind.EXEC_COMMAND}
class ApprovalHandlingStatus(StrEnum): ALLOWED="allowed"; DENIED="denied"; RESPONSE_UNKNOWN="response_unknown"
class ApprovalResponseUnknown(Exception): pass
class ApprovalError(Exception):
    def __init__(self,category:str)->None:self.category=category;super().__init__(category)
class AsyncApprovalOperator(Protocol):
    async def decide(self,request:"ApprovalRequest")->ApprovalDecision: ...
@dataclass(frozen=True)
class ApprovalRequest:
    local_sequence:int; profile_id:str; wire_request_id:str|int; kind:ApprovalKind; thread_id:str|None; turn_id:str|None; item_or_call_id:str
    context_lines:tuple[str,...]=field(repr=False)
@dataclass(frozen=True)
class ApprovalHandlingResult:
    status:ApprovalHandlingStatus; profile_id:str; local_sequence:int; wire_request_id:str|int; kind:ApprovalKind; error_category:str|None=None

def _id(v:Any,required=True)->str|None:
    if v is None and not required:return None
    if not isinstance(v,str) or not v or "\0" in v or len(v)>MAX_APPROVAL_ID_CHARS:raise ValueError
    return v
def _lines(params:dict[str,Any],keys:tuple[str,...])->tuple[str,...]:
    out=[]
    for k in keys:
        v=params.get(k)
        if v is None:continue
        if isinstance(v,list): v=" ".join(str(x) for x in v if isinstance(x,str))
        if not isinstance(v,str) or "\0" in v or len(v)>MAX_APPROVAL_CONTEXT_LINE_CHARS:raise ValueError
        out.append(f"{k}: {v}")
    if len(out)>MAX_APPROVAL_CONTEXT_LINES or sum(map(len,out))>MAX_APPROVAL_CONTEXT_TOTAL_CHARS:raise ValueError
    return tuple(out)
def _grant(v:Any)->dict[str,Any]:
    # Keep only JSON-shaped request grants; ownership is copied before wire use.
    if not isinstance(v,dict) or not v:raise ValueError
    import copy
    return copy.deepcopy(v)

class CodexApprovalBridge:
    def __init__(self,*,profile_id:str,client:CodexProtocolClient,operator:AsyncApprovalOperator)->None:
        if not isinstance(profile_id,str) or not profile_id:raise ValueError("profile_id")
        self.profile_id=profile_id; self.client=client; self._operator=operator; self._lock=asyncio.Lock(); self._sequence=1
    async def handle_next(self)->ApprovalHandlingResult:
        async with self._lock:
            get=asyncio.create_task(self.client.next_server_request()); term=asyncio.create_task(self.client.wait_terminal())
            done,_=await asyncio.wait((get,term),return_when=asyncio.FIRST_COMPLETED)
            if term in done:
                get.cancel(); await asyncio.gather(get,return_exceptions=True); return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,0,0,ApprovalKind.COMMAND_EXECUTION,"approval_protocol_terminal")
            term.cancel(); await asyncio.gather(term,return_exceptions=True)
            return await self._handle(await get)
    async def handle_request(self,request:InboundServerRequest)->ApprovalHandlingResult:
        async with self._lock:return await self._handle(request)
    async def _handle(self,inbound:InboundServerRequest)->ApprovalHandlingResult:
        method=inbound.method; kind=_KINDS.get(method)
        if kind is None: raise ApprovalError("approval_request_invalid")
        seq=self._sequence; self._sequence+=1; grant=None
        try: normalized,grant=self._normalize(inbound,seq,kind)
        except ValueError: return await self._send(inbound,seq,kind,ApprovalDecision.DENY,None,"approval_request_invalid")
        decision=ApprovalDecision.DENY
        operator=asyncio.create_task(self._operator.decide(normalized)); terminal=asyncio.create_task(self.client.wait_terminal())
        try:
            done,_=await asyncio.wait((operator,terminal),return_when=asyncio.FIRST_COMPLETED)
            if terminal in done:
                operator.cancel(); await asyncio.gather(operator,return_exceptions=True); return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,"approval_protocol_terminal")
            try:
                chosen=operator.result()
                if chosen is ApprovalDecision.ALLOW and (method!=PERMISSIONS or grant is not None):decision=chosen
            except asyncio.CancelledError: pass
            except Exception: pass
        except asyncio.CancelledError:
            operator.cancel(); await asyncio.gather(operator,return_exceptions=True)
            # Caller cancellation before send is deliberately converted to deny.
        finally:
            terminal.cancel(); await asyncio.gather(terminal,return_exceptions=True)
        return await self._send(inbound,seq,kind,decision,grant,None)
    def _normalize(self,inbound:InboundServerRequest,seq:int,kind:ApprovalKind)->tuple[ApprovalRequest,dict[str,Any]|None]:
        p=inbound._params_copy()
        if inbound.method in (COMMAND,FILE_CHANGE,PERMISSIONS):
            thread=_id(p.get("threadId")); turn=_id(p.get("turnId")); item=_id(p.get("itemId"));
            if not isinstance(p.get("startedAtMs"),int) or isinstance(p["startedAtMs"],bool):raise ValueError
            keys=("reason","cwd","command")
        else:
            thread=_id(p.get("conversationId"));turn=None;item=_id(p.get("callId"));keys=("reason","cwd","command")
        if inbound.method==APPLY_PATCH and not isinstance(p.get("fileChanges"),dict):raise ValueError
        # Frozen JSON arrays thaw to tuples in the degenerate empty/list cases;
        # accept both immutable and mutable sequence forms before projection.
        if inbound.method==EXEC_COMMAND and (not isinstance(p.get("cwd"),str) or not isinstance(p.get("command"),(list,tuple)) or not isinstance(p.get("parsedCmd"),(list,tuple))):raise ValueError
        grant=_grant(p.get("permissions")) if inbound.method==PERMISSIONS else None
        return ApprovalRequest(seq,self.profile_id,inbound.request_id,kind,thread,turn,item,_lines(p,keys)),grant
    async def _send(self,inbound:InboundServerRequest,seq:int,kind:ApprovalKind,decision:ApprovalDecision,grant:dict[str,Any]|None,error:str|None)->ApprovalHandlingResult:
        result={"permissions":grant if decision is ApprovalDecision.ALLOW and grant is not None else {},"scope":"turn"} if inbound.method==PERMISSIONS else {"decision":("accept" if decision is ApprovalDecision.ALLOW else "decline") if inbound.method in (COMMAND,FILE_CHANGE) else ("approved" if decision is ApprovalDecision.ALLOW else "denied")}
        task=asyncio.create_task(self.client.respond_server_request(inbound,result))
        while True:
            try: await asyncio.shield(task); break
            except asyncio.CancelledError: continue
            except ProtocolApprovalResponseUnknown:return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,"approval_response_unknown")
            except Exception:return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,"approval_response_unknown")
        return ApprovalHandlingResult(ApprovalHandlingStatus.ALLOWED if decision is ApprovalDecision.ALLOW else ApprovalHandlingStatus.DENIED,self.profile_id,seq,inbound.request_id,kind,error)

# Compatibility name retained for the P1.7 fake-operator tests; new code uses the bound bridge.
class CodexApprovalAdapter:
    def __init__(self,operator:AsyncApprovalOperator)->None:self._operator=operator
    async def handle_envelope(self,client:CodexProtocolClient,envelope:InboundServerRequest)->ApprovalHandlingResult:
        return await CodexApprovalBridge(profile_id="test",client=client,operator=self._operator).handle_request(envelope)
    async def handle_next(self,client:CodexProtocolClient)->ApprovalHandlingResult:
        return await CodexApprovalBridge(profile_id="test",client=client,operator=self._operator).handle_next()
