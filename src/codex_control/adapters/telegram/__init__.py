"""Pure, Telegram-shaped private management boundary."""

from .private_render import TelegramPrivatePanelRenderer
from .private_dialogue_render import TelegramPrivateDialoguePanelRenderer
from .private_updates import (
    PrivateCommand,
    PrivateInboundKind,
    PrivateInboundUpdate,
    TelegramPrivateUpdateAdapter,
)

__all__ = [
    "PrivateInboundKind",
    "PrivateCommand",
    "PrivateInboundUpdate",
    "TelegramPrivateUpdateAdapter",
    "TelegramPrivatePanelRenderer",
    "TelegramPrivateDialoguePanelRenderer",
]
