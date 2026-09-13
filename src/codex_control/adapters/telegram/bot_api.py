"""Narrow Telegram Bot API transport with an injectable offline HTTP seam."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, Protocol
from urllib import parse, request

from codex_control.application.response_delivery import (
    TelegramDeliveryEffectResult,
    TelegramDeliveryEffectStatus,
    TelegramDeliveryErrorClass,
)


class TelegramTransportError(RuntimeError):
    """Allowlisted, token-free transport diagnostic."""

    def __init__(self, category: str) -> None:
        self.category = category if category in {
            "HTTP_REJECTED", "NETWORK_AMBIGUOUS", "RESPONSE_INVALID", "API_REJECTED",
            "OFFSET_INVALID", "POLL_TIMEOUT", "REQUEST_INVALID",
        } else "RESPONSE_INVALID"
        super().__init__(self.category)

    def __repr__(self) -> str:
        return f"TelegramTransportError({self.category!r})"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpClient(Protocol):
    async def request(self, method: str, payload: Mapping[str, Any], *, timeout: float) -> HttpResponse: ...


class UrlLibHttpClient:
    """The sole real-network implementation; URL/token never enters diagnostics."""

    def __init__(self, token: str, *, base_url: str = "https://api.telegram.org", timeout: float = 30.0) -> None:
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def request(self, method: str, payload: Mapping[str, Any], *, timeout: float) -> HttpResponse:
        return await asyncio.to_thread(self._request, method, dict(payload), min(timeout, self._timeout))

    def _request(self, method: str, payload: dict[str, Any], timeout: float) -> HttpResponse:
        url = f"{self._base_url}/bot{self._token}/{method}"
        data = parse.urlencode(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return HttpResponse(int(response.status), response.read(2 * 1024 * 1024 + 1))
        except Exception as error:
            raise TelegramTransportError("NETWORK_AMBIGUOUS") from None


def _message_id(value: object) -> int | None:
    if type(value) is int and 1 <= value <= 9_223_372_036_854_775_807:
        return value
    return None


class TelegramBotApiTransport:
    """Implements only accepted polling, delivery and callback acknowledgement."""

    def __init__(self, token: str, *, http: HttpClient | None = None,
                 connect_timeout: float = 5.0, request_timeout: float = 15.0,
                 poll_timeout: float = 30.0) -> None:
        if not isinstance(token, str) or not token or any(char.isspace() for char in token):
            raise ValueError("token_invalid")
        if any(value <= 0 or value > 120 for value in (connect_timeout, request_timeout, poll_timeout)):
            raise ValueError("timeout_invalid")
        self._token = token
        self._http = http or UrlLibHttpClient(token, timeout=max(request_timeout, poll_timeout))
        self._request_timeout = request_timeout
        self._poll_timeout = poll_timeout
        self._offset = 0

    def __repr__(self) -> str:
        return "TelegramBotApiTransport(token='[REDACTED]')"

    @property
    def offset(self) -> int:
        return self._offset

    async def _call(self, method: str, payload: Mapping[str, Any], *, timeout: float) -> object:
        try:
            response = await self._http.request(method, payload, timeout=timeout)
        except TelegramTransportError:
            raise
        except (asyncio.TimeoutError, TimeoutError):
            raise TelegramTransportError("NETWORK_AMBIGUOUS") from None
        except Exception:
            raise TelegramTransportError("NETWORK_AMBIGUOUS") from None
        if not isinstance(response, HttpResponse) or type(response.status) is not int:
            raise TelegramTransportError("RESPONSE_INVALID")
        if response.status < 200 or response.status >= 300:
            raise TelegramTransportError("HTTP_REJECTED")
        if not isinstance(response.body, bytes) or len(response.body) > 2 * 1024 * 1024:
            raise TelegramTransportError("RESPONSE_INVALID")
        try:
            value = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise TelegramTransportError("RESPONSE_INVALID") from None
        if not isinstance(value, dict) or type(value.get("ok")) is not bool:
            raise TelegramTransportError("RESPONSE_INVALID")
        if value["ok"] is not True:
            raise TelegramTransportError("API_REJECTED")
        if "result" not in value:
            raise TelegramTransportError("RESPONSE_INVALID")
        return value["result"]

    async def get_updates(self) -> tuple[dict[str, Any], ...]:
        result = await self._call("getUpdates", {"offset": self._offset, "timeout": int(self._poll_timeout)}, timeout=self._poll_timeout + 5)
        if not isinstance(result, list):
            raise TelegramTransportError("RESPONSE_INVALID")
        updates: list[dict[str, Any]] = []
        prior = self._offset - 1
        for update in result:
            if not isinstance(update, dict) or type(update.get("update_id")) is not int or update["update_id"] < 0:
                raise TelegramTransportError("RESPONSE_INVALID")
            update_id = update["update_id"]
            if update_id <= prior:
                raise TelegramTransportError("OFFSET_INVALID")
            prior = update_id
            updates.append(dict(update))
        if updates:
            self._offset = updates[-1]["update_id"] + 1
        return tuple(updates)

    async def send_message(self, *, chat_id: int, text: str, reply_markup: object | None = None) -> int:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = json.dumps(reply_markup, separators=(",", ":"))
        result = await self._call("sendMessage", payload, timeout=self._request_timeout)
        if not isinstance(result, dict) or _message_id(result.get("message_id")) is None:
            raise TelegramTransportError("RESPONSE_INVALID")
        return result["message_id"]

    async def edit_message(self, *, chat_id: int, message_id: int, text: str) -> TelegramDeliveryEffectResult:
        try:
            result = await self._call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text}, timeout=self._request_timeout)
        except TelegramTransportError as error:
            if error.category in {"NETWORK_AMBIGUOUS"}:
                return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS)
            return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED)
        if result is True:
            return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)
        if isinstance(result, dict) and _message_id(result.get("message_id")) == message_id:
            return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)
        return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED)

    async def create_message(self, *, chat_id: int, text: str) -> TelegramDeliveryEffectResult:
        try:
            message_id = await self.send_message(chat_id=chat_id, text=text)
        except TelegramTransportError as error:
            if error.category == "NETWORK_AMBIGUOUS":
                return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.UNKNOWN, None, TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS)
            return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.FAILED, None, TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED)
        return TelegramDeliveryEffectResult(TelegramDeliveryEffectStatus.CONFIRMED, message_id, None)

    async def answer_callback_query(self, *, callback_query_id: str) -> None:
        await self._call("answerCallbackQuery", {"callback_query_id": callback_query_id}, timeout=self._request_timeout)

    async def send_projection(self, *, chat_id: int, projection: Mapping[str, Any]) -> int:
        if not isinstance(projection, Mapping) or type(projection.get("text")) is not str:
            raise TelegramTransportError("REQUEST_INVALID")
        return await self.send_message(chat_id=chat_id, text=projection["text"], reply_markup=projection.get("reply_markup"))


__all__ = ["HttpResponse", "TelegramBotApiTransport", "TelegramTransportError", "UrlLibHttpClient"]
