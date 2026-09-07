"""Fail-closed normalization for untrusted private Telegram-like updates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from codex_control.storage.core_repositories import MAX_SQLITE_INT


_CALLBACK_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32}")
_CALLBACK_QUERY_ID_MAX = 256


class PrivateInboundKind(StrEnum):
    COMMAND = "COMMAND"
    CALLBACK = "CALLBACK"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"


class PrivateCommand(StrEnum):
    MENU = "MENU"
    SETTINGS = "SETTINGS"


@dataclass(frozen=True, repr=False)
class PrivateInboundUpdate:
    kind: PrivateInboundKind
    update_id: int | None
    user_id: int | None
    chat_id: int | None
    command: PrivateCommand | None
    callback_query_id: str | None
    callback_token: str | None

    def __repr__(self) -> str:
        token = "[REDACTED]" if self.callback_token is not None else None
        return (
            "PrivateInboundUpdate("
            f"kind={self.kind!r}, update_id={self.update_id!r}, "
            f"user_id={self.user_id!r}, chat_id={self.chat_id!r}, "
            f"command={self.command!r}, callback_query_id={self.callback_query_id!r}, "
            f"callback_token={token!r})"
        )


def _valid_nonnegative_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_SQLITE_INT


def _valid_user_id(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SQLITE_INT


def _valid_chat_id(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and -MAX_SQLITE_INT <= value <= MAX_SQLITE_INT
        and value != 0
    )


def _valid_query_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and "\x00" not in value
        and len(value) <= _CALLBACK_QUERY_ID_MAX
    )


def _record(
    kind: PrivateInboundKind,
    *,
    update_id: int | None = None,
    user_id: int | None = None,
    chat_id: int | None = None,
    command: PrivateCommand | None = None,
    callback_query_id: str | None = None,
    callback_token: str | None = None,
) -> PrivateInboundUpdate:
    return PrivateInboundUpdate(kind, update_id, user_id, chat_id, command, callback_query_id, callback_token)


class TelegramPrivateUpdateAdapter:
    """Normalize one raw update without retaining its untrusted payload."""

    def __init__(self, operator_user_id: int) -> None:
        if not _valid_user_id(operator_user_id):
            raise ValueError("invalid operator user id")
        self._operator_user_id = operator_user_id

    def normalize(self, update: object) -> PrivateInboundUpdate:
        if not isinstance(update, dict):
            return _record(PrivateInboundKind.MALFORMED)

        raw_update_id = update.get("update_id")
        if not _valid_nonnegative_id(raw_update_id):
            return _record(PrivateInboundKind.MALFORMED)
        update_id = raw_update_id

        has_callback = "callback_query" in update
        has_message = "message" in update
        if has_callback and has_message:
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        if has_callback:
            return self._callback(update.get("callback_query"), update_id)
        if has_message:
            return self._message(update.get("message"), update_id)
        return _record(PrivateInboundKind.MALFORMED, update_id=update_id)

    def _message(self, message: object, update_id: int) -> PrivateInboundUpdate:
        if not isinstance(message, dict):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        sender = message.get("from")
        chat = message.get("chat")
        if not isinstance(sender, dict) or not isinstance(chat, dict):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        sender_id = sender.get("id")
        chat_id = chat.get("id")
        if not _valid_user_id(sender_id) or not _valid_chat_id(chat_id):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        if type(sender.get("is_bot")) is not bool or not isinstance(chat.get("type"), str):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id, user_id=sender_id, chat_id=chat_id)
        if sender_id != self._operator_user_id or sender.get("is_bot") is not False:
            return _record(PrivateInboundKind.UNAUTHORIZED, update_id=update_id, user_id=sender_id, chat_id=chat_id)
        if chat_id != self._operator_user_id or chat.get("type") != "private":
            return _record(PrivateInboundKind.UNAUTHORIZED, update_id=update_id, user_id=sender_id, chat_id=chat_id)

        text = message.get("text")
        if text is None:
            return _record(PrivateInboundKind.UNSUPPORTED, update_id=update_id, user_id=sender_id, chat_id=chat_id)
        if not isinstance(text, str):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id, user_id=sender_id, chat_id=chat_id)
        command = {"/start": PrivateCommand.MENU, "/menu": PrivateCommand.MENU, "/settings": PrivateCommand.SETTINGS}.get(text)
        if command is None:
            return _record(PrivateInboundKind.UNSUPPORTED, update_id=update_id, user_id=sender_id, chat_id=chat_id)
        return _record(
            PrivateInboundKind.COMMAND,
            update_id=update_id,
            user_id=sender_id,
            chat_id=chat_id,
            command=command,
        )

    def _callback(self, callback: object, update_id: int) -> PrivateInboundUpdate:
        if not isinstance(callback, dict):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        sender = callback.get("from")
        callback_query_id = callback.get("id")
        if not isinstance(sender, dict) or not _valid_query_id(callback_query_id):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id)
        sender_id = sender.get("id")
        if not _valid_user_id(sender_id) or type(sender.get("is_bot")) is not bool:
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id, callback_query_id=callback_query_id)
        message = callback.get("message")
        if not isinstance(message, dict):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id, user_id=sender_id, callback_query_id=callback_query_id)
        chat = message.get("chat")
        if not isinstance(chat, dict):
            return _record(PrivateInboundKind.MALFORMED, update_id=update_id, user_id=sender_id, callback_query_id=callback_query_id)
        chat_id = chat.get("id")
        chat_type = chat.get("type")
        if not _valid_chat_id(chat_id) or not isinstance(chat_type, str):
            return _record(
                PrivateInboundKind.MALFORMED,
                update_id=update_id,
                user_id=sender_id,
                callback_query_id=callback_query_id,
            )
        # Do not inspect callback data until the principal and private chat pass.
        if sender_id != self._operator_user_id or sender.get("is_bot") is not False:
            return _record(
                PrivateInboundKind.UNAUTHORIZED,
                update_id=update_id,
                user_id=sender_id,
                chat_id=chat_id,
                callback_query_id=callback_query_id,
            )
        if chat_id != self._operator_user_id or chat_type != "private":
            return _record(
                PrivateInboundKind.UNAUTHORIZED,
                update_id=update_id,
                user_id=sender_id,
                chat_id=chat_id,
                callback_query_id=callback_query_id,
            )
        data = callback.get("data")
        if not isinstance(data, str) or len(data) != 36 or not data.startswith("cc1:"):
            return _record(
                PrivateInboundKind.MALFORMED,
                update_id=update_id,
                user_id=sender_id,
                chat_id=chat_id,
                callback_query_id=callback_query_id,
            )
        token = data[4:]
        if _CALLBACK_TOKEN_RE.fullmatch(token) is None:
            return _record(
                PrivateInboundKind.MALFORMED,
                update_id=update_id,
                user_id=sender_id,
                chat_id=chat_id,
                callback_query_id=callback_query_id,
            )
        return _record(
            PrivateInboundKind.CALLBACK,
            update_id=update_id,
            user_id=sender_id,
            chat_id=chat_id,
            callback_query_id=callback_query_id,
            callback_token=token,
        )


__all__ = [
    "PrivateInboundKind",
    "PrivateCommand",
    "PrivateInboundUpdate",
    "TelegramPrivateUpdateAdapter",
]
