"""Transport-independent newline-delimited Codex app-server protocol client."""

from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any

from .types import AsyncLineTransport, CLIENT_NAME, ClientInfo, InitializeResult


class ProtocolState(Enum):
    NEW = "new"
    INITIALIZING = "initializing"
    READY = "ready"
    CLOSED = "closed"
    FAULTED = "faulted"


class ProtocolError(Exception):
    """A safe protocol exception: it never contains raw remote payloads."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class ProtocolFault(ProtocolError):
    pass


class ProtocolRemoteError(ProtocolError):
    """A remote error normalized to its numeric code, without remote text/data."""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__("remote_error")


class CodexProtocolClient:
    """P1.1 client; it owns protocol state but never starts a process."""

    def __init__(self, transport: AsyncLineTransport, *, client_version: str) -> None:
        self._transport = transport
        self._client_info = ClientInfo(name=CLIENT_NAME, title="CodexControl", version=client_version)
        self._state = ProtocolState.NEW
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._completed_ids: set[int] = set()
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._reader_task: asyncio.Task[None] | None = None
        self.initialize_result: InitializeResult | None = None

    @property
    def state(self) -> ProtocolState:
        return self._state

    async def initialize(self) -> InitializeResult:
        if self._state is not ProtocolState.NEW:
            raise ProtocolFault("initialize_not_allowed")
        self._state = ProtocolState.INITIALIZING
        try:
            result = await self._send_request(
                "initialize",
                {"clientInfo": self._client_info.as_params(), "capabilities": {}},
            )
            try:
                initialize_result = InitializeResult.from_result(result)
            except ValueError as error:
                self._fault(error.args[0])
                raise ProtocolFault(error.args[0]) from None
            await self._transport.send({"method": "initialized"})
            self.initialize_result = initialize_result
            self._state = ProtocolState.READY
            return initialize_result
        except ProtocolRemoteError:
            if self._state is ProtocolState.INITIALIZING:
                self._state = ProtocolState.FAULTED
            raise

    async def request(self, method: str, params: Any) -> Any:
        if self._state is not ProtocolState.READY:
            raise ProtocolFault("request_not_allowed")
        if not isinstance(method, str) or not method:
            raise ValueError("method must be a non-empty string")
        return await self._send_request(method, params)

    async def next_notification(self) -> dict[str, Any]:
        return await self._notifications.get()

    async def close(self) -> None:
        if self._state not in (ProtocolState.CLOSED, ProtocolState.FAULTED):
            self._state = ProtocolState.CLOSED
            self._fail_pending(ProtocolFault("client_closed"))
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

    async def _send_request(self, method: str, params: Any) -> Any:
        request_id = self._next_id
        self._next_id += 1
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        self._start_reader()
        try:
            await self._transport.send({"id": request_id, "method": method, "params": params})
        except Exception:
            self._pending.pop(request_id, None)
            self._fault("transport_send_failed")
            raise ProtocolFault("transport_send_failed") from None
        return await future

    def _start_reader(self) -> None:
        if self._reader_task is None:
            self._reader_task = asyncio.create_task(self._read_messages())

    async def _read_messages(self) -> None:
        try:
            while self._state not in (ProtocolState.CLOSED, ProtocolState.FAULTED):
                line = await self._transport.receive()
                if line is None:
                    if self._pending:
                        self._fault("eof_pending")
                    elif self._state not in (ProtocolState.CLOSED, ProtocolState.FAULTED):
                        self._state = ProtocolState.CLOSED
                    return
                self._handle_line(line)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._fault("transport_receive_failed")

    def _handle_line(self, line: str) -> None:
        try:
            message = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            self._fault("malformed_json")
            return
        if not isinstance(message, dict):
            self._fault("invalid_envelope")
            return
        if "id" in message:
            self._handle_response(message)
            return
        if isinstance(message.get("method"), str):
            self._notifications.put_nowait(message)
            return
        self._fault("invalid_envelope")

    def _handle_response(self, message: dict[str, Any]) -> None:
        response_id = message.get("id")
        if not isinstance(response_id, int) or isinstance(response_id, bool):
            self._fault("invalid_response_id")
            return
        if response_id in self._completed_ids:
            self._fault("duplicate_response_id")
            return
        future = self._pending.pop(response_id, None)
        if future is None:
            self._fault("unexpected_response_id")
            return
        self._completed_ids.add(response_id)
        has_result = "result" in message
        has_error = "error" in message
        if has_result == has_error:
            if not future.done():
                future.set_exception(ProtocolFault("invalid_response_envelope"))
            self._fault("invalid_response_envelope")
            return
        if has_error:
            error = message["error"]
            if not isinstance(error, dict) or not isinstance(error.get("code"), int):
                if not future.done():
                    future.set_exception(ProtocolFault("invalid_error_envelope"))
                self._fault("invalid_error_envelope")
                return
            future.set_exception(ProtocolRemoteError(error["code"]))
            return
        future.set_result(message["result"])

    def _fault(self, category: str) -> None:
        if self._state is ProtocolState.FAULTED:
            return
        self._state = ProtocolState.FAULTED
        self._fail_pending(ProtocolFault(category))

    def _fail_pending(self, error: ProtocolError) -> None:
        pending = tuple(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(error)
