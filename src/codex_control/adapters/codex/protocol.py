"""Transport-independent newline-delimited Codex app-server protocol client."""
from __future__ import annotations
import asyncio, json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from .types import AsyncLineTransport, CLIENT_NAME, ClientInfo, InitializeResult

MAX_PENDING_SERVER_REQUESTS=64
MAX_SERVER_REQUEST_ID_CHARS=256
SERVER_REQUEST_INT_MIN=-(2**63)
SERVER_REQUEST_INT_MAX=2**63-1
APPROVAL_SERVER_REQUEST_METHODS=frozenset(("item/commandExecution/requestApproval","item/fileChange/requestApproval","item/permissions/requestApproval","applyPatchApproval","execCommandApproval"))

class ProtocolState(Enum):
    NEW="new"; INITIALIZING="initializing"; READY="ready"; CLOSED="closed"; FAULTED="faulted"
class ProtocolError(Exception):
    def __init__(self,category:str)->None: self.category=category; super().__init__(category)
class ProtocolFault(ProtocolError): pass
class ProtocolRemoteError(ProtocolError):
    def __init__(self,code:int)->None: self.code=code; super().__init__("remote_error")
class ProtocolApprovalResponseUnknown(ProtocolError):
    def __init__(self)->None: super().__init__("approval_response_unknown")

class _FrozenList(tuple): pass
def _freeze(v:Any)->Any:
    if isinstance(v,dict): return tuple((k,_freeze(x)) for k,x in v.items())
    if isinstance(v,list): return _FrozenList(_freeze(x) for x in v)
    return v
def thaw_server_request_params(v:Any)->Any:
    if isinstance(v,_FrozenList): return [thaw_server_request_params(x) for x in v]
    if isinstance(v,tuple):
        if all(isinstance(x,tuple) and len(x)==2 and isinstance(x[0],str) for x in v): return {k:thaw_server_request_params(x) for k,x in v}
        return [thaw_server_request_params(x) for x in v]
    return v
@dataclass(frozen=True)
class InboundServerRequest:
    local_sequence:int; request_id:str|int; method:str; _params:Any=field(repr=False,compare=False)
    def _params_copy(self)->dict[str,Any]:
        x=thaw_server_request_params(self._params); return x if isinstance(x,dict) else {}

class CodexProtocolClient:
    def __init__(self,transport:AsyncLineTransport,*,client_version:str)->None:
        self._transport=transport; self._client_info=ClientInfo(name=CLIENT_NAME,title="CodexControl",version=client_version); self._state=ProtocolState.NEW; self._next_id=1; self._next_server_sequence=1
        self._pending:dict[int,asyncio.Future[Any]]={}; self._completed_ids:set[int]=set(); self._pending_server:dict[str|int,InboundServerRequest]={}
        self._server_requests:asyncio.Queue[InboundServerRequest]=asyncio.Queue(maxsize=MAX_PENDING_SERVER_REQUESTS); self._notifications:asyncio.Queue[dict[str,Any]]=asyncio.Queue(); self._reader_task:asyncio.Task[None]|None=None; self._terminal=asyncio.Event(); self.initialize_result:InitializeResult|None=None
    @property
    def state(self)->ProtocolState: return self._state
    async def initialize(self)->InitializeResult:
        if self._state is not ProtocolState.NEW: raise ProtocolFault("initialize_not_allowed")
        self._state=ProtocolState.INITIALIZING
        try:
            result=await self._send_request("initialize",{"clientInfo":self._client_info.as_params(),"capabilities":{}})
            try: parsed=InitializeResult.from_result(result)
            except ValueError as e: self._fault(e.args[0]); raise ProtocolFault(e.args[0]) from None
            if self._state is not ProtocolState.INITIALIZING: raise ProtocolFault("initialize_terminal")
            await self._transport.send({"method":"initialized"}); self.initialize_result=parsed; self._state=ProtocolState.READY; return parsed
        except ProtocolRemoteError:
            if self._state is ProtocolState.INITIALIZING: self._fault("initialize_remote_error")
            raise
    async def request(self,method:str,params:Any)->Any:
        if self._state is not ProtocolState.READY: raise ProtocolFault("request_not_allowed")
        if not isinstance(method,str) or not method: raise ValueError("method must be a non-empty string")
        return await self._send_request(method,params)
    async def next_notification(self)->dict[str,Any]: return await self._notifications.get()
    async def next_server_request(self)->InboundServerRequest: return await self._server_requests.get()
    async def respond_server_request(self,request:InboundServerRequest,result:dict[str,Any])->None:
        if not isinstance(request,InboundServerRequest) or self._pending_server.get(request.request_id) is not request: raise ProtocolFault("server_response_not_owned")
        if self._state is not ProtocolState.READY: raise ProtocolApprovalResponseUnknown()
        del self._pending_server[request.request_id]
        try: await self._transport.send({"id":request.request_id,"result":result})
        except Exception: self._fault("approval_response_unknown"); raise ProtocolApprovalResponseUnknown() from None
    async def wait_terminal(self)->ProtocolState: await self._terminal.wait(); return self._state
    async def close(self)->None:
        if self._state not in (ProtocolState.CLOSED,ProtocolState.FAULTED): self._state=ProtocolState.CLOSED; self._fail_pending(ProtocolFault("client_closed"))
        self._terminal.set()
        if self._reader_task:
            self._reader_task.cancel()
            try: await self._reader_task
            except asyncio.CancelledError: pass
    async def _send_request(self,method:str,params:Any)->Any:
        ident=self._next_id; self._next_id+=1; future=asyncio.get_running_loop().create_future(); self._pending[ident]=future; self._start_reader()
        try: await self._transport.send({"id":ident,"method":method,"params":params})
        except Exception: self._pending.pop(ident,None); self._fault("transport_send_failed"); raise ProtocolFault("transport_send_failed") from None
        return await future
    def _start_reader(self)->None:
        if self._reader_task is None: self._reader_task=asyncio.create_task(self._read_messages())
    async def _read_messages(self)->None:
        try:
            while self._state not in (ProtocolState.CLOSED,ProtocolState.FAULTED):
                line=await self._transport.receive()
                if line is None:
                    if self._pending or self._pending_server: self._fault("eof_pending_server_request" if self._pending_server else "eof_pending")
                    else: self._state=ProtocolState.CLOSED; self._terminal.set()
                    return
                self._handle_line(line)
        except asyncio.CancelledError: raise
        except Exception: self._fault("transport_receive_failed")
    def _handle_line(self,line:str)->None:
        try: m=json.loads(line)
        except (TypeError,json.JSONDecodeError): self._fault("malformed_json"); return
        if not isinstance(m,dict): self._fault("invalid_envelope"); return
        i="id" in m; me="method" in m; p="params" in m; r="result" in m; e="error" in m
        if i and not me and (r^e) and not p: self._handle_response(m); return
        if i and me and p and not r and not e: self._handle_server_request(m); return
        if not i and me and p and not r and not e and isinstance(m["method"],str): self._notifications.put_nowait(m); return
        self._fault("invalid_envelope")
    @staticmethod
    def _valid_request_id(v:Any)->bool:
        if isinstance(v,int) and not isinstance(v,bool): return SERVER_REQUEST_INT_MIN<=v<=SERVER_REQUEST_INT_MAX
        return isinstance(v,str) and bool(v) and "\0" not in v and len(v)<=MAX_SERVER_REQUEST_ID_CHARS
    def _handle_server_request(self,m:dict[str,Any])->None:
        ident=m["id"]; method=m["method"]
        if self._state is not ProtocolState.READY: self._fault("server_request_not_allowed"); return
        if not self._valid_request_id(ident) or not isinstance(method,str) or not method: self._fault("invalid_server_request"); return
        if method not in APPROVAL_SERVER_REQUEST_METHODS: self._fault("unsupported_server_request_method"); return
        if ident in self._pending_server: self._fault("duplicate_server_request_id"); return
        if len(self._pending_server)>=MAX_PENDING_SERVER_REQUESTS: self._fault("server_request_limit"); return
        req=InboundServerRequest(self._next_server_sequence,ident,method,_freeze(m["params"])); self._next_server_sequence+=1; self._pending_server[ident]=req
        try: self._server_requests.put_nowait(req)
        except asyncio.QueueFull: self._pending_server.pop(ident,None); self._fault("server_request_limit")
    def _handle_response(self,m:dict[str,Any])->None:
        ident=m["id"]
        if not isinstance(ident,int) or isinstance(ident,bool): self._fault("invalid_response_id"); return
        if ident in self._completed_ids: self._fault("duplicate_response_id"); return
        f=self._pending.pop(ident,None)
        if f is None: self._fault("unexpected_response_id"); return
        self._completed_ids.add(ident)
        if "error" in m:
            error=m["error"]
            if not isinstance(error,dict) or not isinstance(error.get("code"),int): f.set_exception(ProtocolFault("invalid_error_envelope")); self._fault("invalid_error_envelope"); return
            f.set_exception(ProtocolRemoteError(error["code"])); return
        f.set_result(m["result"])
    def _fault(self,category:str)->None:
        if self._state is ProtocolState.FAULTED:return
        self._state=ProtocolState.FAULTED; self._terminal.set(); self._fail_pending(ProtocolFault(category))
    def _fail_pending(self,error:ProtocolError)->None:
        values=tuple(self._pending.values()); self._pending.clear()
        for f in values:
            if not f.done(): f.set_exception(error)
