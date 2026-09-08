"""Pure local fleet-status identity and projection for P5.3."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from codex_control.domain import ControllerMode

from .fleet_control import (
    FleetControlResult,
    FleetControlStatus,
    FleetManifest,
    FleetMember,
    FleetModeSnapshot,
    P5_DISPLAY_NAME_MAX_CHARS,
    P5_FLEET_MAX_MEMBERS,
    P5_FLEET_VERSION_MAX_CHARS,
    P5_SERVER_ID_MAX_CHARS,
)
from .fleet_group_routing import GroupRoutingResult, GroupRoutingStatus


P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS = 16

_MAX_SQLITE_INT = 9223372036854775807
_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9_.:-]+")


class FleetStatusErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    INVARIANT = "INVARIANT"


class FleetStatusError(Exception):
    """Finite, content-free P5.3 diagnostic."""

    def __init__(self, category: FleetStatusErrorCategory | str) -> None:
        try:
            self.category = (
                category
                if isinstance(category, FleetStatusErrorCategory)
                else FleetStatusErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = FleetStatusErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"FleetStatusError({self.category.value!r})"


def _invalid() -> FleetStatusError:
    return FleetStatusError(FleetStatusErrorCategory.INVALID_ARGUMENT)


def _invariant() -> FleetStatusError:
    return FleetStatusError(FleetStatusErrorCategory.INVARIANT)


def _valid_identifier(value: object, limit: int) -> bool:
    return type(value) is str and 1 <= len(value) <= limit and _IDENTIFIER_RE.fullmatch(value) is not None


def _valid_display_name(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= P5_DISPLAY_NAME_MAX_CHARS
        and "\x00" not in value
        and all(unicodedata.category(char) != "Cc" for char in value)
        and value == " ".join(value.split())
    )


def _valid_counter(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_SQLITE_INT


def fleet_manifest_fingerprint_sha256(manifest: FleetManifest) -> str:
    """Return the deterministic SHA-256 identity of an exact fleet manifest."""

    if type(manifest) is not FleetManifest:
        raise _invalid()
    parts: list[str] = [
        "codex-control-fleet-v1",
        manifest.fleet_version,
        str(len(manifest.members)),
    ]
    for member in manifest.members:
        parts.extend((member.server_id, member.display_name))
    try:
        source = "\x00".join(parts).encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise _invariant() from None
    return hashlib.sha256(source).hexdigest()


@dataclass(frozen=True)
class FleetStatusProjection:
    server_id: str
    display_name: str
    effective_mode: ControllerMode
    fleet_version: str
    manifest_fingerprint_sha256: str
    member_count: int
    boot_generation: int
    last_control_epoch: int

    def __post_init__(self) -> None:
        if not _valid_identifier(self.server_id, P5_SERVER_ID_MAX_CHARS):
            raise _invalid()
        if not _valid_display_name(self.display_name):
            raise _invalid()
        if type(self.effective_mode) is not ControllerMode:
            raise _invalid()
        if not _valid_identifier(self.fleet_version, P5_FLEET_VERSION_MAX_CHARS):
            raise _invalid()
        if (
            type(self.manifest_fingerprint_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", self.manifest_fingerprint_sha256) is None
        ):
            raise _invalid()
        if type(self.member_count) is not int or not 1 <= self.member_count <= P5_FLEET_MAX_MEMBERS:
            raise _invalid()
        if not _valid_counter(self.boot_generation) or not _valid_counter(self.last_control_epoch):
            raise _invalid()


class FleetStatusService:
    def __init__(self, manifest: FleetManifest, *, server_id: str) -> None:
        if type(manifest) is not FleetManifest or not _valid_identifier(server_id, P5_SERVER_ID_MAX_CHARS):
            raise _invalid()
        local_members = tuple(member for member in manifest.members if member.server_id == server_id)
        if len(local_members) != 1:
            raise _invalid()
        self._manifest = manifest
        self._local_member: FleetMember = local_members[0]
        self._manifest_fingerprint = fleet_manifest_fingerprint_sha256(manifest)

    def project(self, result: GroupRoutingResult) -> FleetStatusProjection:
        if type(result) is not GroupRoutingResult:
            raise _invalid()
        if result.status is not GroupRoutingStatus.STATUS:
            raise _invariant()
        if (
            type(result.control_result) is not FleetControlResult
            or result.control_result.status is not FleetControlStatus.STATUS
            or type(result.snapshot) is not FleetModeSnapshot
            or result.control_result.snapshot is not result.snapshot
            or result.turn_result is not None
            or result.disposition is not None
            or result.reason is not None
        ):
            raise _invariant()
        snapshot = result.snapshot
        if (
            snapshot.server_id != self._local_member.server_id
            or snapshot.fleet_version != self._manifest.fleet_version
            or type(snapshot.effective_mode) is not ControllerMode
            or not _valid_counter(snapshot.boot_generation)
            or not _valid_counter(snapshot.last_control_epoch)
        ):
            raise _invariant()
        return FleetStatusProjection(
            server_id=snapshot.server_id,
            display_name=self._local_member.display_name,
            effective_mode=snapshot.effective_mode,
            fleet_version=self._manifest.fleet_version,
            manifest_fingerprint_sha256=self._manifest_fingerprint,
            member_count=len(self._manifest.members),
            boot_generation=snapshot.boot_generation,
            last_control_epoch=snapshot.last_control_epoch,
        )


__all__ = [
    "P53_MANIFEST_FINGERPRINT_DISPLAY_CHARS",
    "FleetStatusErrorCategory",
    "FleetStatusError",
    "fleet_manifest_fingerprint_sha256",
    "FleetStatusProjection",
    "FleetStatusService",
]
