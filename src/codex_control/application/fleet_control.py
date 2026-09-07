"""P5.1 fleet manifest and durable group-control application boundary."""

from __future__ import annotations

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from codex_control.domain import ControllerMode
from codex_control.storage import (
    ControlClaimResult,
    ControlClaimStatus,
    ControlIngressRepository,
    ControllerBootResult,
    ControllerRuntimeRecord,
    ControllerRuntimeRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
)


P5_ACTIVATION_PREFIX = "🖥 "
P5_ALL_SLEEP_LABEL = "💤 ВСЕ СПАТЬ"
P5_STATUS_LABEL = "📊 СТАТУС"
P5_FLEET_MAX_MEMBERS = 32
P5_SERVER_ID_MAX_CHARS = 128
P5_DISPLAY_NAME_MAX_CHARS = 64
P5_FLEET_VERSION_MAX_CHARS = 128
P5_GROUP_TEXT_MAX_CHARS = 4096

MAX_SQLITE_INT = 9223372036854775807
MIN_SQLITE_INT = -9223372036854775808
_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9_.:-]+")


class FleetControlErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class FleetControlError(Exception):
    """Finite, content-free P5.1 diagnostic."""

    def __init__(self, category: FleetControlErrorCategory | str) -> None:
        try:
            self.category = (
                category
                if isinstance(category, FleetControlErrorCategory)
                else FleetControlErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = FleetControlErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"FleetControlError({self.category.value!r})"


def _invalid() -> FleetControlError:
    return FleetControlError(FleetControlErrorCategory.INVALID_ARGUMENT)


def _storage() -> FleetControlError:
    return FleetControlError(FleetControlErrorCategory.STORAGE)


def _invariant() -> FleetControlError:
    return FleetControlError(FleetControlErrorCategory.INVARIANT)


def _valid_nonnegative(value: object) -> bool:
    return type(value) is int and 0 <= value <= MAX_SQLITE_INT


def _valid_positive(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_SQLITE_INT


def _valid_signed_nonzero(value: object) -> bool:
    return type(value) is int and MIN_SQLITE_INT <= value <= MAX_SQLITE_INT and value != 0


def _valid_identifier(value: object, limit: int) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= limit
        and "\x00" not in value
        and _IDENTIFIER_RE.fullmatch(value) is not None
    )


@dataclass(frozen=True)
class FleetMember:
    server_id: str
    display_name: str

    def __post_init__(self) -> None:
        if not _valid_identifier(self.server_id, P5_SERVER_ID_MAX_CHARS):
            raise _invalid()
        if (
            type(self.display_name) is not str
            or not 1 <= len(self.display_name) <= P5_DISPLAY_NAME_MAX_CHARS
            or "\x00" in self.display_name
            or any(unicodedata.category(char) == "Cc" for char in self.display_name)
            or self.display_name != " ".join(self.display_name.split())
        ):
            raise _invalid()


@dataclass(frozen=True)
class FleetManifest:
    fleet_version: str
    members: tuple[FleetMember, ...]

    def __post_init__(self) -> None:
        if not _valid_identifier(self.fleet_version, P5_FLEET_VERSION_MAX_CHARS):
            raise _invalid()
        if type(self.members) is not tuple or not 1 <= len(self.members) <= P5_FLEET_MAX_MEMBERS:
            raise _invalid()
        if any(type(member) is not FleetMember for member in self.members):
            raise _invalid()
        server_ids = [member.server_id for member in self.members]
        display_names = [member.display_name for member in self.members]
        if len(server_ids) != len(set(server_ids)) or len(display_names) != len(set(display_names)):
            raise _invalid()


class GroupInboundKind(StrEnum):
    CONTROL = "CONTROL"
    TEXT = "TEXT"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"


class GroupControlKind(StrEnum):
    ACTIVATE = "ACTIVATE"
    ALL_SLEEP = "ALL_SLEEP"
    STATUS = "STATUS"


@dataclass(frozen=True, repr=False)
class GroupInboundUpdate:
    kind: GroupInboundKind
    update_id: int | None
    message_id: int | None
    user_id: int | None
    chat_id: int | None
    control: GroupControlKind | None
    target_server_id: str | None
    text: str | None

    def __post_init__(self) -> None:
        if type(self.kind) is not GroupInboundKind:
            raise _invalid()
        if self.update_id is not None and not _valid_nonnegative(self.update_id):
            raise _invalid()
        if self.message_id is not None and not _valid_positive(self.message_id):
            raise _invalid()
        if self.user_id is not None and not _valid_positive(self.user_id):
            raise _invalid()
        if self.chat_id is not None and not _valid_signed_nonzero(self.chat_id):
            raise _invalid()
        if self.control is not None and type(self.control) is not GroupControlKind:
            raise _invalid()
        if self.target_server_id is not None and not _valid_identifier(
            self.target_server_id, P5_SERVER_ID_MAX_CHARS
        ):
            raise _invalid()

        if self.kind in (GroupInboundKind.CONTROL, GroupInboundKind.TEXT):
            if not (
                _valid_nonnegative(self.update_id)
                and _valid_positive(self.message_id)
                and _valid_positive(self.user_id)
                and _valid_signed_nonzero(self.chat_id)
            ):
                raise _invalid()
        if self.kind is GroupInboundKind.CONTROL:
            if type(self.control) is not GroupControlKind or self.text is not None:
                raise _invalid()
            if self.control is not GroupControlKind.ACTIVATE and self.target_server_id is not None:
                raise _invalid()
        elif self.kind is GroupInboundKind.TEXT:
            if (
                self.control is not None
                or self.target_server_id is not None
                or type(self.text) is not str
                or not self.text
                or len(self.text) > P5_GROUP_TEXT_MAX_CHARS
                or "\x00" in self.text
            ):
                raise _invalid()
        else:
            if self.control is not None or self.target_server_id is not None or self.text is not None:
                raise _invalid()

    def __repr__(self) -> str:
        safe_text = "'[REDACTED]'" if self.text is not None else "None"
        return (
            "GroupInboundUpdate("
            f"kind={self.kind!r}, update_id={self.update_id!r}, "
            f"message_id={self.message_id!r}, user_id={self.user_id!r}, "
            f"chat_id={self.chat_id!r}, control={self.control!r}, "
            f"target_server_id={self.target_server_id!r}, text={safe_text})"
        )


@dataclass(frozen=True)
class FleetModeSnapshot:
    server_id: str
    effective_mode: ControllerMode
    boot_generation: int
    last_control_epoch: int
    fleet_version: str

    def __post_init__(self) -> None:
        if not _valid_identifier(self.server_id, P5_SERVER_ID_MAX_CHARS):
            raise _invalid()
        if type(self.effective_mode) is not ControllerMode:
            raise _invalid()
        if not _valid_nonnegative(self.boot_generation) or not _valid_nonnegative(self.last_control_epoch):
            raise _invalid()
        if not _valid_identifier(self.fleet_version, P5_FLEET_VERSION_MAX_CHARS):
            raise _invalid()


class FleetControlStatus(StrEnum):
    APPLIED = "APPLIED"
    STALE = "STALE"
    DUPLICATE = "DUPLICATE"
    STATUS = "STATUS"
    TEXT = "TEXT"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"


@dataclass(frozen=True)
class FleetControlResult:
    status: FleetControlStatus
    snapshot: FleetModeSnapshot | None

    def __post_init__(self) -> None:
        if type(self.status) is not FleetControlStatus:
            raise _invariant()
        needs_snapshot = self.status in {
            FleetControlStatus.APPLIED,
            FleetControlStatus.STALE,
            FleetControlStatus.DUPLICATE,
            FleetControlStatus.STATUS,
            FleetControlStatus.TEXT,
        }
        if needs_snapshot != (type(self.snapshot) is FleetModeSnapshot):
            raise _invariant()


class FleetControlService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        manifest: FleetManifest,
        server_id: str,
        operator_user_id: int,
        control_chat_id: int,
        boot_result: ControllerBootResult,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        if type(storage) is not SqliteStorage or type(manifest) is not FleetManifest:
            raise _invalid()
        if not _valid_identifier(server_id, P5_SERVER_ID_MAX_CHARS):
            raise _invalid()
        if sum(member.server_id == server_id for member in manifest.members) != 1:
            raise _invalid()
        if not _valid_positive(operator_user_id) or not (
            type(control_chat_id) is int and MIN_SQLITE_INT <= control_chat_id <= -1
        ):
            raise _invalid()
        if type(boot_result) is not ControllerBootResult or type(boot_result.record) is not ControllerRuntimeRecord:
            raise _invalid()
        if type(boot_result.effective_mode) is not ControllerMode or boot_result.effective_mode is not ControllerMode.SLEEP:
            raise _invalid()
        if boot_result.record.fleet_version != manifest.fleet_version:
            raise _invalid()
        if not _valid_nonnegative(boot_result.record.boot_generation) or not _valid_nonnegative(
            boot_result.record.last_control_epoch
        ):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()

        self._storage = storage
        self._manifest = manifest
        self._server_id = server_id
        self._operator_user_id = operator_user_id
        self._control_chat_id = control_chat_id
        self._clock = now_ms
        self._captured_boot_generation = boot_result.record.boot_generation
        self._boot_baseline_control_epoch = boot_result.record.last_control_epoch
        self._captured_fleet_version = manifest.fleet_version
        self._lock = asyncio.Lock()

    async def current_mode(self) -> FleetModeSnapshot:
        async with self._lock:
            _, snapshot = await self._read_current_unlocked()
            return snapshot

    async def handle(self, update: GroupInboundUpdate) -> FleetControlResult:
        if type(update) is not GroupInboundUpdate:
            raise _invalid()
        async with self._lock:
            if update.kind is GroupInboundKind.UNAUTHORIZED:
                return await self._handle_unauthorized_unlocked(update)
            if update.kind is GroupInboundKind.MALFORMED:
                return FleetControlResult(FleetControlStatus.MALFORMED, None)
            if update.kind is GroupInboundKind.UNSUPPORTED:
                return FleetControlResult(FleetControlStatus.UNSUPPORTED, None)
            if update.user_id != self._operator_user_id or update.chat_id != self._control_chat_id:
                return await self._handle_unauthorized_unlocked(update)
            if update.kind is GroupInboundKind.TEXT:
                _, snapshot = await self._read_current_unlocked()
                return FleetControlResult(FleetControlStatus.TEXT, snapshot)
            if update.kind is not GroupInboundKind.CONTROL or type(update.control) is not GroupControlKind:
                raise _invariant()
            if update.control is GroupControlKind.STATUS:
                _, snapshot = await self._read_current_unlocked()
                return FleetControlResult(FleetControlStatus.STATUS, snapshot)
            if update.control is GroupControlKind.ACTIVATE:
                if update.target_server_id is not None and update.target_server_id not in {
                    member.server_id for member in self._manifest.members
                }:
                    raise _invalid()
                requested_mode = (
                    ControllerMode.ACTIVE
                    if update.target_server_id == self._server_id
                    else ControllerMode.SLEEP
                )
            elif update.control is GroupControlKind.ALL_SLEEP:
                requested_mode = ControllerMode.SLEEP
            else:
                raise _invariant()

            before, _ = await self._read_current_unlocked()
            try:
                claim = await ControlIngressRepository(self._storage, now_ms=self._clock).claim_control(
                    update_id=update.update_id,
                    control_epoch=update.message_id,
                    requested_mode=requested_mode,
                )
            except RepositoryError as exc:
                raise _storage_or_invalid(exc) from None
            except StorageError:
                raise _storage() from None
            if type(claim) is not ControlClaimResult or type(claim.status) is not ControlClaimStatus:
                raise _invariant()
            if claim.status is ControlClaimStatus.DUPLICATE:
                if claim.controller is not None:
                    raise _invariant()
                _, snapshot = await self._read_current_unlocked()
                return FleetControlResult(FleetControlStatus.DUPLICATE, snapshot)
            if claim.status not in (ControlClaimStatus.APPLIED, ControlClaimStatus.STALE):
                raise _invariant()
            if type(claim.controller) is not ControllerRuntimeRecord:
                raise _invariant()
            self._validate_controller_authority(claim.controller)
            if claim.status is ControlClaimStatus.APPLIED:
                if (
                    claim.controller.last_control_epoch != update.message_id
                    or claim.controller.requested_mode is not requested_mode
                ):
                    raise _invariant()
                status = FleetControlStatus.APPLIED
            else:
                if claim.controller != before:
                    raise _invariant()
                status = FleetControlStatus.STALE
            current, snapshot = await self._read_current_unlocked()
            if claim.status is ControlClaimStatus.STALE and current != before:
                raise _invariant()
            if claim.status is ControlClaimStatus.APPLIED and current != claim.controller:
                raise _invariant()
            return FleetControlResult(status, snapshot)

    async def _handle_unauthorized_unlocked(self, update: GroupInboundUpdate) -> FleetControlResult:
        if not _valid_nonnegative(update.update_id):
            raise _invalid()
        try:
            await IngressUpdateRepository(self._storage, now_ms=self._clock).claim_ignored(
                update_id=update.update_id,
                disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED,
            )
        except RepositoryError as exc:
            raise _storage_or_invalid(exc) from None
        except StorageError:
            raise _storage() from None
        return FleetControlResult(FleetControlStatus.UNAUTHORIZED, None)

    async def _read_current_unlocked(self) -> tuple[ControllerRuntimeRecord, FleetModeSnapshot]:
        try:
            current = await ControllerRuntimeRepository(self._storage, now_ms=self._clock).get()
        except RepositoryError as exc:
            if exc.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
                raise _invariant() from None
            raise _storage() from None
        except StorageError:
            raise _storage() from None
        if type(current) is not ControllerRuntimeRecord:
            raise _invariant()
        self._validate_controller_authority(current)
        effective = (
            ControllerMode.SLEEP
            if current.last_control_epoch <= self._boot_baseline_control_epoch
            else current.requested_mode
        )
        return current, FleetModeSnapshot(
            self._server_id,
            effective,
            current.boot_generation,
            current.last_control_epoch,
            current.fleet_version,
        )

    def _validate_controller_authority(self, current: ControllerRuntimeRecord) -> None:
        if (
            current.boot_generation != self._captured_boot_generation
            or current.fleet_version != self._captured_fleet_version
            or current.last_control_epoch < self._boot_baseline_control_epoch
            or type(current.requested_mode) is not ControllerMode
            or not _valid_nonnegative(current.last_control_epoch)
        ):
            raise _invariant()


def _storage_or_invalid(error: RepositoryError) -> FleetControlError:
    if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
        return _invalid()
    if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
        return _invariant()
    return _storage()


__all__ = [
    "P5_ACTIVATION_PREFIX",
    "P5_ALL_SLEEP_LABEL",
    "P5_STATUS_LABEL",
    "P5_FLEET_MAX_MEMBERS",
    "P5_SERVER_ID_MAX_CHARS",
    "P5_DISPLAY_NAME_MAX_CHARS",
    "P5_FLEET_VERSION_MAX_CHARS",
    "P5_GROUP_TEXT_MAX_CHARS",
    "FleetMember",
    "FleetManifest",
    "GroupInboundKind",
    "GroupControlKind",
    "GroupInboundUpdate",
    "FleetModeSnapshot",
    "FleetControlStatus",
    "FleetControlErrorCategory",
    "FleetControlError",
    "FleetControlResult",
    "FleetControlService",
]
