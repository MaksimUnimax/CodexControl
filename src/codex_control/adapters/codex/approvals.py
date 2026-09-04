"""Fail-closed, profile-bound approval bridge for installed Codex 0.144.6."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from .protocol import APPROVAL_SERVER_REQUEST_METHODS, CodexProtocolClient, InboundServerRequest

COMMAND="item/commandExecution/requestApproval"; FILE_CHANGE="item/fileChange/requestApproval"; PERMISSIONS="item/permissions/requestApproval"; APPLY_PATCH="applyPatchApproval"; EXEC_COMMAND="execCommandApproval"; APPROVAL_METHODS=APPROVAL_SERVER_REQUEST_METHODS
MAX_APPROVAL_ID_CHARS=512; MAX_APPROVAL_CONTEXT_LINES=32; MAX_APPROVAL_CONTEXT_LINE_CHARS=2048; MAX_APPROVAL_CONTEXT_TOTAL_CHARS=8192
MAX_APPROVAL_PERMISSION_VALUE_CHARS=4096; MAX_APPROVAL_PERMISSION_ENTRIES=128
class ApprovalDecision(StrEnum): ALLOW="ALLOW"; DENY="DENY"
class ApprovalKind(StrEnum): COMMAND_EXECUTION="command_execution"; FILE_CHANGE="file_change"; PERMISSIONS="permissions"; APPLY_PATCH="apply_patch"; EXEC_COMMAND="exec_command"
class ApprovalHandlingStatus(StrEnum): ALLOWED="allowed"; DENIED="denied"; RESPONSE_UNKNOWN="response_unknown"
class ApprovalErrorCategory(StrEnum):
    APPROVAL_REQUEST_INVALID="approval_request_invalid"; APPROVAL_DECISION_INVALID="approval_decision_invalid"; APPROVAL_OPERATION_BUSY="approval_operation_busy"; APPROVAL_PROTOCOL_TERMINAL="approval_protocol_terminal"; APPROVAL_RESPONSE_UNKNOWN="approval_response_unknown"
_KINDS={COMMAND:ApprovalKind.COMMAND_EXECUTION,FILE_CHANGE:ApprovalKind.FILE_CHANGE,PERMISSIONS:ApprovalKind.PERMISSIONS,APPLY_PATCH:ApprovalKind.APPLY_PATCH,EXEC_COMMAND:ApprovalKind.EXEC_COMMAND}
class ApprovalError(Exception):
    def __init__(self, category:ApprovalErrorCategory|str)->None:
        try:self.category=ApprovalErrorCategory(category)
        except (TypeError,ValueError):self.category=ApprovalErrorCategory.APPROVAL_REQUEST_INVALID
        super().__init__(self.category.value)
    def __repr__(self)->str:return f"ApprovalError({self.category.value!r})"
class AsyncApprovalOperator(Protocol):
    async def decide(self,request:"ApprovalRequest")->ApprovalDecision: ...
@dataclass(frozen=True)
class ApprovalRequest:
    local_sequence:int; profile_id:str; wire_request_id:str|int; kind:ApprovalKind; thread_id:str|None; turn_id:str|None; item_or_call_id:str
    context_lines:tuple[str,...]=field(repr=False)
@dataclass(frozen=True)
class ApprovalHandlingResult:
    status:ApprovalHandlingStatus; profile_id:str; local_sequence:int; wire_request_id:str|int; kind:ApprovalKind; error_category:ApprovalErrorCategory|None=None

def _id(v:Any,required:bool=True)->str|None:
    if v is None and not required:return None
    if not isinstance(v,str) or not v or "\0" in v or len(v)>MAX_APPROVAL_ID_CHARS:raise ValueError
    return v
def _string(v:Any)->str:
    if not isinstance(v,str) or "\0" in v or len(v)>MAX_APPROVAL_PERMISSION_VALUE_CHARS:raise ValueError
    return v
def _schema_string(v:Any)->str:
    if not isinstance(v,str) or "\0" in v: raise ValueError
    return v
def _context(lines:list[str])->tuple[str,...]:
    if len(lines)>MAX_APPROVAL_CONTEXT_LINES or any("\0" in x or len(x)>MAX_APPROVAL_CONTEXT_LINE_CHARS for x in lines) or sum(map(len,lines))>MAX_APPROVAL_CONTEXT_TOTAL_CHARS:raise ValueError
    return tuple(lines)
def _optional_context(p:dict[str,Any],keys:tuple[str,...])->tuple[str,...]:
    out=[]
    for key in keys:
        value=p.get(key)
        if value is None:continue
        if not isinstance(value,str) or "\0" in value:raise ValueError
        out.append(f"{key}: {value}")
    return _context(out)

def _path(v:Any)->dict[str,Any]:
    if not isinstance(v,dict) or not isinstance(v.get("type"),str):raise ValueError
    if v["type"]=="path" and set(v)=={"type","path"}:return {"type":"path","path":_string(v["path"])}
    if v["type"]=="glob_pattern" and set(v)=={"type","pattern"}:return {"type":"glob_pattern","pattern":_string(v["pattern"])}
    if v["type"]!="special" or set(v)!={"type","value"} or not isinstance(v["value"],dict):raise ValueError
    s=v["value"]; kind=s.get("kind")
    if kind in ("root","minimal","tmpdir","slash_tmp") and set(s)=={"kind"}:return {"type":"special","value":{"kind":kind}}
    if kind=="project_roots" and set(s)<={"kind","subpath"}:
        o={"kind":kind}
        if "subpath" in s:o["subpath"]=None if s["subpath"] is None else _string(s["subpath"])
        return {"type":"special","value":o}
    if kind=="unknown" and set(s)<={"kind","path","subpath"} and "path" in s:
        o={"kind":kind,"path":_string(s["path"])}
        if "subpath" in s:o["subpath"]=None if s["subpath"] is None else _string(s["subpath"])
        return {"type":"special","value":o}
    raise ValueError
def _permissions(v:Any)->tuple[dict[str,Any],bool]:
    if not isinstance(v,dict) or not v or set(v)-{"network","fileSystem"}:raise ValueError
    out={}; entries=0; effective=False
    if "network" in v:
        x=v["network"]
        if x is None:out["network"]=None
        elif isinstance(x,dict) and set(x)<={"enabled"}:
            n={}
            if "enabled" in x:
                if x["enabled"] is not None and type(x["enabled"]) is not bool:raise ValueError
                n["enabled"]=x["enabled"]; effective=x["enabled"] is True
            out["network"]=n
        else:raise ValueError
    if "fileSystem" in v:
        x=v["fileSystem"]
        if x is None:out["fileSystem"]=None
        elif isinstance(x,dict) and set(x)<={"entries","globScanMaxDepth","read","write"}:
            f={}
            for key in ("entries","read","write"):
                if key not in x:continue
                values=x[key]
                if values is None:f[key]=None;continue
                if not isinstance(values,list):raise ValueError
                made=[]
                for item in values:
                    entries+=1
                    if entries>MAX_APPROVAL_PERMISSION_ENTRIES:raise ValueError
                    if key=="entries":
                        if not isinstance(item,dict) or set(item)!={"access","path"} or item.get("access") not in ("read","write","deny"):raise ValueError
                        made.append({"access":item["access"],"path":_path(item["path"])})
                        effective=effective or item["access"] in ("read","write")
                    else:
                        made.append(_string(item))
                        # Empty legacy lists are schema-valid but grant
                        # nothing.  ADR-0014 makes every no-op fail closed.
                        effective=effective or bool(values)
                f[key]=made
            if "globScanMaxDepth" in x:
                depth=x["globScanMaxDepth"]
                if depth is not None and (type(depth) is not int or depth<1 or depth>2**64-1):raise ValueError
                f["globScanMaxDepth"]=depth
            out["fileSystem"]=f
        else:raise ValueError
    return out,effective
async def _join(task:asyncio.Task[Any])->None:
    while not task.done():
        try:await asyncio.shield(task)
        except asyncio.CancelledError:continue
        except Exception:break
    try:task.result()
    except (asyncio.CancelledError,Exception):pass
async def _cancel_and_join_observing(task:asyncio.Task[Any], cancelled:list[bool])->None:
    """Join a helper while retaining public cancellation as a fact."""
    task.cancel()
    while not task.done():
        try: await asyncio.shield(task)
        except asyncio.CancelledError:
            if asyncio.current_task().cancelling(): cancelled[0]=True
        except Exception: break
    try: task.result()
    except (asyncio.CancelledError,Exception): pass

class CodexApprovalBridge:
    def __init__(self,*,profile_id:str,client:CodexProtocolClient,operator:AsyncApprovalOperator)->None:
        if not isinstance(profile_id,str) or not profile_id:raise ValueError("profile_id")
        self.profile_id=profile_id;self.client=client;self._operator=operator;self._lock=asyncio.Lock();self._sequence=1
    def _metadata(self,inbound:InboundServerRequest)->tuple[int,ApprovalKind]:
        kind=_KINDS.get(inbound.method)
        if kind is None:raise ApprovalError(ApprovalErrorCategory.APPROVAL_REQUEST_INVALID)
        seq=self._sequence;self._sequence+=1;return seq,kind
    async def handle_next(self)->ApprovalHandlingResult:
        async with self._lock:
            get=asyncio.create_task(self.client.next_server_request());term=asyncio.create_task(self.client.wait_terminal())
            try:
                done,_=await asyncio.wait((get,term),return_when=asyncio.FIRST_COMPLETED)
            except asyncio.CancelledError:
                # A cancellation that races a completed dequeue transfers
                # ownership; otherwise neither helper may outlive us.
                if get.done() and not get.cancelled():
                    try: inbound=get.result()
                    except Exception:
                        term.cancel(); await _join(term); raise
                    seq,kind=self._metadata(inbound)
                    term.cancel();await _join(term)
                    return await self._handle(inbound,seq,kind,[True])
                get.cancel();term.cancel();await _join(get);await _join(term)
                raise
            if get in done:
                inbound=get.result();seq,kind=self._metadata(inbound)
                if term in done:
                    term.cancel();await _join(term)
                    return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL)
                cancelled=[False]
                await _cancel_and_join_observing(term,cancelled)
                return await self._handle(inbound,seq,kind,cancelled)
            get.cancel();term.cancel();await _join(get);await _join(term);raise ApprovalError(ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL)
    async def handle_request(self,inbound:InboundServerRequest)->ApprovalHandlingResult:
        async with self._lock:
            if not self.client.owns_server_request(inbound):
                raise ApprovalError(ApprovalErrorCategory.APPROVAL_REQUEST_INVALID)
            seq,kind=self._metadata(inbound);return await self._handle(inbound,seq,kind)
    async def _handle(self,inbound:InboundServerRequest,seq:int,kind:ApprovalKind,cancelled:list[bool]|None=None)->ApprovalHandlingResult:
        # This mutable flag is intentionally carried through every pre-send
        # await.  Once ownership exists, public cancellation is fail-closed.
        if cancelled is None: cancelled=[False]
        try:request,grant,effective=self._normalize(inbound,seq,kind)
        except ValueError:return await self._send(inbound,seq,kind,ApprovalDecision.DENY,None,ApprovalErrorCategory.APPROVAL_REQUEST_INVALID,cancelled)
        if kind is ApprovalKind.PERMISSIONS and not effective:return await self._send(inbound,seq,kind,ApprovalDecision.DENY,None,ApprovalErrorCategory.APPROVAL_REQUEST_INVALID,cancelled)
        op=asyncio.create_task(self._operator.decide(request));terminal=asyncio.create_task(self.client.wait_terminal());decision=ApprovalDecision.DENY;done=set()
        try:
            while True:
                try:done,_=await asyncio.wait((op,terminal),return_when=asyncio.FIRST_COMPLETED);break
                except asyncio.CancelledError:
                    cancelled[0]=True;op.cancel();await _join(op);break
            if terminal in done:
                op.cancel();await _join(op);return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL)
            try:
                if op.result() is ApprovalDecision.ALLOW:decision=ApprovalDecision.ALLOW
            except (asyncio.CancelledError,Exception):pass
        finally:
            terminal.cancel()
            # _join intentionally consumes repeated public cancellation, but
            # it must still change the decision before the wire task exists.
            while not terminal.done():
                try: await asyncio.shield(terminal)
                except asyncio.CancelledError:
                    # A cancelled terminal helper also raises here.  Only the
                    # public task's cancellation state is a fail-closed input.
                    if asyncio.current_task().cancelling(): cancelled[0]=True
                except Exception: break
            try: terminal.result()
            except (asyncio.CancelledError,Exception): pass
        if cancelled[0]: decision=ApprovalDecision.DENY
        return await self._send(inbound,seq,kind,decision,grant,None,cancelled)
    def _normalize(self,inbound:InboundServerRequest,seq:int,kind:ApprovalKind)->tuple[ApprovalRequest,dict[str,Any]|None,bool]:
        p=inbound._params_copy()
        if not isinstance(p,dict):raise ValueError
        if kind in (ApprovalKind.COMMAND_EXECUTION,ApprovalKind.FILE_CHANGE,ApprovalKind.PERMISSIONS):
            thread=_id(p.get("threadId"));turn=_id(p.get("turnId"));item=_id(p.get("itemId"))
            if type(p.get("startedAtMs")) is not int or not -(2**63)<=p["startedAtMs"]<=2**63-1:raise ValueError
        else:thread=_id(p.get("conversationId"));turn=None;item=_id(p.get("callId"))
        if kind is ApprovalKind.PERMISSIONS:_string(p.get("cwd"));grant,effective=_permissions(p.get("permissions"));context=_optional_context(p,("reason","cwd"))
        elif kind is ApprovalKind.COMMAND_EXECUTION:grant=None;effective=False;context=_optional_context(p,("reason","cwd","command"))
        elif kind is ApprovalKind.FILE_CHANGE:grant=None;effective=False;context=_optional_context(p,("reason",))
        elif kind is ApprovalKind.APPLY_PATCH:
            changes=p.get("fileChanges")
            if not isinstance(changes,dict):raise ValueError
            paths=[]
            for path,change in changes.items():
                # Path names are the only patch payload projected to the
                # operator.  Content and diffs are deliberately never copied.
                paths.append(_string(path));self._file_change(change)
            grant=None;effective=False;context=_context(list(_optional_context(p,("reason",)))+[f"file: {path}" for path in paths])
        else:
            if not isinstance(p.get("command"),list) or not isinstance(p.get("parsedCmd"),list):raise ValueError
            _string(p.get("cwd"));command=[_string(x) for x in p["command"]]
            for x in p["parsedCmd"]:self._parsed(x)
            grant=None;effective=False;context=_context(list(_optional_context(p,("cwd","reason")))+["command: "+" ".join(command)])
        return ApprovalRequest(seq,self.profile_id,inbound.request_id,kind,thread,turn,item,context),grant,effective
    @staticmethod
    def _file_change(v:Any)->None:
        if not isinstance(v,dict) or v.get("type") not in ("add","delete","update"):raise ValueError
        if v["type"] in ("add","delete") and "content" not in v:raise ValueError
        if v["type"]=="update" and "unified_diff" not in v:raise ValueError
        # Generated schema permits extra fields. Validate the nested fields
        # it uses, but never apply permission-value limits to patch contents.
        for k in ("content","unified_diff"):
            if k in v:_schema_string(v[k])
        if "move_path" in v and v["move_path"] is not None:_string(v["move_path"])
    @staticmethod
    def _parsed(v:Any)->None:
        if not isinstance(v,dict) or v.get("type") not in ("read","list_files","search","unknown") or "cmd" not in v:raise ValueError
        _schema_string(v["cmd"])
        kind=v["type"]
        if kind=="read":
            if "name" not in v or "path" not in v:raise ValueError
            _schema_string(v["name"]);_schema_string(v["path"])
        elif kind=="list_files":
            if "path" in v and v["path"] is not None:_schema_string(v["path"])
        elif kind=="search":
            for key in ("query","path"):
                if key in v and v[key] is not None:_schema_string(v[key])
    async def _send(self,inbound:InboundServerRequest,seq:int,kind:ApprovalKind,decision:ApprovalDecision,grant:dict[str,Any]|None,error:ApprovalErrorCategory|None,cancelled:list[bool]|None=None)->ApprovalHandlingResult:
        if cancelled is not None and cancelled[0]: decision=ApprovalDecision.DENY
        result={"permissions":grant if decision is ApprovalDecision.ALLOW and grant is not None else {},"scope":"turn"} if kind is ApprovalKind.PERMISSIONS else {"decision":("accept" if decision is ApprovalDecision.ALLOW else "decline") if kind in (ApprovalKind.COMMAND_EXECUTION,ApprovalKind.FILE_CHANGE) else ("approved" if decision is ApprovalDecision.ALLOW else "denied")}
        task=asyncio.create_task(self.client.respond_server_request(inbound,result))
        while True:
            try:await asyncio.shield(task);break
            except asyncio.CancelledError:
                if task.cancelled():return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,ApprovalErrorCategory.APPROVAL_RESPONSE_UNKNOWN)
                continue
            except Exception:return ApprovalHandlingResult(ApprovalHandlingStatus.RESPONSE_UNKNOWN,self.profile_id,seq,inbound.request_id,kind,ApprovalErrorCategory.APPROVAL_RESPONSE_UNKNOWN)
        return ApprovalHandlingResult(ApprovalHandlingStatus.ALLOWED if decision is ApprovalDecision.ALLOW else ApprovalHandlingStatus.DENIED,self.profile_id,seq,inbound.request_id,kind,error)
