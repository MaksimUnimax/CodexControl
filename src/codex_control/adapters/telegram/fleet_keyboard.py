"""Pure persistent Telegram-shaped fleet keyboard rendering."""

from __future__ import annotations

from codex_control.application.fleet_control import (
    FleetManifest,
    P5_ACTIVATION_PREFIX,
    P5_ALL_SLEEP_LABEL,
    P5_STATUS_LABEL,
)


class TelegramFleetKeyboardRenderer:
    def render(self, manifest: FleetManifest) -> dict:
        if type(manifest) is not FleetManifest:
            raise ValueError("invalid fleet manifest")
        rows: list[list[dict[str, str]]] = []
        activation_row: list[dict[str, str]] = []
        for member in manifest.members:
            activation_row.append({"text": P5_ACTIVATION_PREFIX + member.display_name})
            if len(activation_row) == 2:
                rows.append(activation_row)
                activation_row = []
        if activation_row:
            rows.append(activation_row)
        rows.append([{"text": P5_ALL_SLEEP_LABEL}, {"text": P5_STATUS_LABEL}])
        return {
            "keyboard": rows,
            "resize_keyboard": True,
            "is_persistent": True,
        }


__all__ = ["TelegramFleetKeyboardRenderer"]
