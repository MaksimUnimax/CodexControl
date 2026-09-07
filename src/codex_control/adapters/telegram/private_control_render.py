"""Pure renderer for the final P4.3 private-control panels."""

from __future__ import annotations

from typing import Any


class TelegramPrivateControlRenderer:
    def render(self, panel: object) -> dict[str, Any]:
        from codex_control.application.private_control import PrivateControlPanel
        from codex_control.application.private_dialogue import PrivateDialoguePanel
        from codex_control.application.private_settings import PrivateAdminPanel

        if type(panel) not in (PrivateAdminPanel, PrivateDialoguePanel, PrivateControlPanel):
            raise ValueError("invalid private control panel")
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


__all__ = ["TelegramPrivateControlRenderer"]
