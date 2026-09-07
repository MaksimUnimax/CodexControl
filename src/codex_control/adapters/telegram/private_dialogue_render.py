"""Pure Telegram-shaped rendering for P4.2 dialogue panels."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from codex_control.application.private_dialogue import PrivateDialoguePanel


class TelegramPrivateDialoguePanelRenderer:
    def render(self, panel: "PrivateDialoguePanel") -> dict[str, Any]:
        from codex_control.application.private_dialogue import PrivateDialoguePanel
        if type(panel) is not PrivateDialoguePanel:
            raise ValueError("invalid private dialogue panel")
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


__all__ = ["TelegramPrivateDialoguePanelRenderer"]
