"""Pure, Telegram-shaped private management boundary."""

from .private_render import TelegramPrivatePanelRenderer
from .private_dialogue_render import TelegramPrivateDialoguePanelRenderer
from .private_control_render import TelegramPrivateControlRenderer
from .private_updates import (
    PrivateCommand,
    PrivateInboundKind,
    PrivateInboundUpdate,
    TelegramPrivateUpdateAdapter,
)
from .fleet_keyboard import TelegramFleetKeyboardRenderer
from .group_updates import TelegramGroupUpdateAdapter

__all__ = [
    "PrivateInboundKind",
    "PrivateCommand",
    "PrivateInboundUpdate",
    "TelegramPrivateUpdateAdapter",
    "TelegramPrivatePanelRenderer",
    "TelegramPrivateDialoguePanelRenderer",
    "TelegramPrivateControlRenderer",
    "TelegramFleetKeyboardRenderer",
    "TelegramGroupUpdateAdapter",
]
