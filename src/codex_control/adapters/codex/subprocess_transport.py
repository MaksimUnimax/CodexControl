"""Secret-free stdio transport for one owned Codex app-server child."""

from __future__ import annotations

import asyncio
import json
from typing import Any


DEFAULT_STDOUT_LINE_LIMIT_BYTES = 4 * 1024 * 1024


class SubprocessTransportError(Exception):
    """A categorized transport error which intentionally contains no payload."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class SubprocessStdioTransport:
    """JSON-lines stdin/stdout boundary; process lifecycle is owned elsewhere."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._closed = False

    async def send(self, message: dict[str, Any]) -> None:
        if self._closed:
            raise SubprocessTransportError("transport_closed")
        try:
            encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._writer.write(encoded + b"\n")
            await self._writer.drain()
        except (TypeError, ValueError, UnicodeError):
            raise SubprocessTransportError("transport_encode_failed") from None
        except (ConnectionError, OSError, asyncio.IncompleteReadError):
            raise SubprocessTransportError("transport_send_failed") from None

    async def receive(self) -> str | None:
        if self._closed:
            return None
        try:
            line = await self._reader.readline()
        except (ValueError, asyncio.LimitOverrunError):
            raise SubprocessTransportError("stdout_line_limit_exceeded") from None
        except (ConnectionError, OSError, asyncio.IncompleteReadError):
            raise SubprocessTransportError("transport_receive_failed") from None
        if not line:
            return None
        try:
            return line.decode("utf-8").rstrip("\n")
        except UnicodeDecodeError:
            raise SubprocessTransportError("stdout_invalid_utf8") from None

    async def close_stdin(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except (ConnectionError, OSError):
            pass
