"""Pure rendering of semantic private panels to a minimal Telegram shape."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from codex_control.application.private_settings import PrivateAdminPanel


class TelegramPrivatePanelRenderer:
    def render(self, panel: "PrivateAdminPanel") -> dict[str, Any]:
        from codex_control.application.private_settings import PrivateAdminPanel
        if not isinstance(panel, PrivateAdminPanel):
            raise ValueError("invalid private panel")
        return {
            "text": panel.text,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {"text": button.label, "callback_data": button.callback_data}
                        for button in row
                    ]
                    for row in panel.rows
                ]
            },
        }


__all__ = ["TelegramPrivatePanelRenderer"]
