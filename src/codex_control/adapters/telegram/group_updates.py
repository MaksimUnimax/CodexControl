"""Fail-closed normalization for the P5.1 group message surface."""

from __future__ import annotations

from codex_control.application.fleet_control import (
    FleetManifest,
    GroupControlKind,
    GroupInboundKind,
    GroupInboundUpdate,
    MAX_SQLITE_INT,
    MIN_SQLITE_INT,
    P5_ACTIVATION_PREFIX,
    P5_ALL_SLEEP_LABEL,
    P5_GROUP_TEXT_MAX_CHARS,
    P5_STATUS_LABEL,
)


def _valid_nonnegative(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_SQLITE_INT


def _valid_positive(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_SQLITE_INT


def _valid_chat(value: object) -> bool:
    return type(value) is int and MIN_SQLITE_INT <= value <= MAX_SQLITE_INT and value != 0


class TelegramGroupUpdateAdapter:
    def __init__(self, manifest: FleetManifest, operator_user_id: int, control_chat_id: int) -> None:
        if type(manifest) is not FleetManifest:
            raise ValueError("invalid fleet manifest")
        if not _valid_positive(operator_user_id):
            raise ValueError("invalid operator user id")
        if type(control_chat_id) is not int or not MIN_SQLITE_INT <= control_chat_id <= -1:
            raise ValueError("invalid control chat id")
        self._labels = {
            P5_ACTIVATION_PREFIX + member.display_name: member.server_id
            for member in manifest.members
        }
        self._operator_user_id = operator_user_id
        self._control_chat_id = control_chat_id

    def normalize(self, update: object) -> GroupInboundUpdate:
        if not isinstance(update, dict):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, None, None, None, None, None, None, None)
        update_id = update.get("update_id")
        if not _valid_nonnegative(update_id):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, None, None, None, None, None, None, None)
        has_callback = "callback_query" in update
        has_message = "message" in update
        if has_callback and has_message:
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, None, None, None, None, None, None)
        if not has_message:
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, None, None, None, None, None, None)
        return self._normalize_message(update.get("message"), update_id)

    def _normalize_message(self, message: object, update_id: int) -> GroupInboundUpdate:
        if not isinstance(message, dict):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, None, None, None, None, None, None)
        message_id = message.get("message_id")
        if not _valid_positive(message_id):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, None, None, None, None, None, None)
        sender = message.get("from")
        chat = message.get("chat")
        if not isinstance(sender, dict) or not isinstance(chat, dict):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, message_id, None, None, None, None, None)
        user_id = sender.get("id")
        chat_id = chat.get("id")
        if not _valid_positive(user_id) or not _valid_chat(chat_id):
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, message_id, None, None, None, None, None)
        if type(sender.get("is_bot")) is not bool or type(chat.get("type")) is not str:
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, update_id, message_id, user_id, chat_id, None, None, None)

        sender_chat = message.get("sender_chat")
        authorized = (
            user_id == self._operator_user_id
            and sender.get("is_bot") is False
            and sender_chat is None
            and chat_id == self._control_chat_id
            and chat.get("type") == "supergroup"
        )
        if not authorized:
            return GroupInboundUpdate(
                GroupInboundKind.UNAUTHORIZED,
                update_id,
                message_id,
                user_id,
                chat_id,
                None,
                None,
                None,
            )

        # This is intentionally the first access to message text.  Principal
        # and user-origin authorization above is a hard boundary.
        text = message.get("text")
        if text is None:
            return GroupInboundUpdate(
                GroupInboundKind.UNSUPPORTED, update_id, message_id, user_id, chat_id, None, None, None
            )
        if type(text) is not str:
            return GroupInboundUpdate(
                GroupInboundKind.MALFORMED, update_id, message_id, user_id, chat_id, None, None, None
            )
        return self._classify_text(text, update_id, message_id, user_id, chat_id)

    def _classify_text(
        self, text: str, update_id: int, message_id: int, user_id: int, chat_id: int
    ) -> GroupInboundUpdate:
        ids = (update_id, message_id, user_id, chat_id)
        target = self._labels.get(text)
        if target is not None:
            return GroupInboundUpdate(
                GroupInboundKind.CONTROL, *ids, GroupControlKind.ACTIVATE, target, None
            )
        if text.startswith(P5_ACTIVATION_PREFIX):
            return GroupInboundUpdate(
                GroupInboundKind.CONTROL, *ids, GroupControlKind.ACTIVATE, None, None
            )
        if text == P5_ALL_SLEEP_LABEL:
            return GroupInboundUpdate(
                GroupInboundKind.CONTROL, *ids, GroupControlKind.ALL_SLEEP, None, None
            )
        if text == P5_STATUS_LABEL:
            return GroupInboundUpdate(
                GroupInboundKind.CONTROL, *ids, GroupControlKind.STATUS, None, None
            )
        if text.lstrip().startswith("/"):
            return GroupInboundUpdate(GroupInboundKind.UNSUPPORTED, *ids, None, None, None)
        if text.lstrip().startswith(("🖥", "💤", "📊")):
            return GroupInboundUpdate(GroupInboundKind.UNSUPPORTED, *ids, None, None, None)
        if text == "" or len(text) > P5_GROUP_TEXT_MAX_CHARS:
            return GroupInboundUpdate(GroupInboundKind.UNSUPPORTED, *ids, None, None, None)
        if "\x00" in text:
            return GroupInboundUpdate(GroupInboundKind.MALFORMED, *ids, None, None, None)
        return GroupInboundUpdate(GroupInboundKind.TEXT, *ids, None, None, text)


__all__ = ["TelegramGroupUpdateAdapter"]
