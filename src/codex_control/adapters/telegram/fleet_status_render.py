"""Pure Telegram-shaped rendering for local fleet status."""

from __future__ import annotations

from codex_control.application.fleet_status import (
    P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS,
    FleetStatusError,
    FleetStatusProjection,
)


class TelegramFleetStatusRenderer:
    def render(self, projection: FleetStatusProjection) -> dict[str, str]:
        if type(projection) is not FleetStatusProjection:
            raise FleetStatusError("INVALID_ARGUMENT")
        return {
            "text": "\n".join(
                (
                    f"🖥 {projection.display_name}",
                    f"Server: {projection.server_id}",
                    f"Mode: {projection.effective_mode.value}",
                    f"Fleet: {projection.fleet_version}",
                    f"Members: {projection.member_count}",
                    f"Manifest: {projection.manifest_fingerprint_sha256[:P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS]}",
                    f"Boot: {projection.boot_generation}",
                    f"Control epoch: {projection.last_control_epoch}",
                )
            )
        }


__all__ = ["TelegramFleetStatusRenderer"]
