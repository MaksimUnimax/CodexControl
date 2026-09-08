"""Final local group routing and ordinary prompt admission facade."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Protocol

from codex_control.domain import ControllerMode
from codex_control.storage import (
    IngressClaimResult,
    IngressDispositionKind,
    IngressUpdateRecord,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
    TransientPayloadRecord,
    TurnJobRecord,
    TurnJobState,
)

from .existing_dialogue_turn import (
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnStatus,
)
from .fleet_control import (
    FleetControlError,
    FleetControlErrorCategory,
    FleetControlResult,
    FleetControlStatus,
    FleetModeSnapshot,
    GroupInboundKind,
    GroupInboundUpdate,
)


class FleetControlPort(Protocol):
    async def handle(self, update: GroupInboundUpdate) -> FleetControlResult: ...


class DialogueTurnPort(Protocol):
    async def execute(self, request: ExistingDialoguePromptRequest) -> ExistingDialogueTurnResult: ...


class GroupRoutingStatus(StrEnum):
    CONTROL = "CONTROL"
    STATUS = "STATUS"
    PROMPT = "PROMPT"
    DUPLICATE = "DUPLICATE"
    BUSY = "BUSY"
    BLOCKED = "BLOCKED"
    IGNORED_SLEEP = "IGNORED_SLEEP"
    REJECTED = "REJECTED"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"
    MALFORMED = "MALFORMED"


class GroupRoutingReason(StrEnum):
    STALE_PROMPT = "STALE_PROMPT"
    LOCAL_PROMPT_IN_FLIGHT = "LOCAL_PROMPT_IN_FLIGHT"
    IN_FLIGHT_DUPLICATE = "IN_FLIGHT_DUPLICATE"
    INVALID_PROMPT = "INVALID_PROMPT"


class GroupRoutingErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    CODEX = "CODEX"
    INVARIANT = "INVARIANT"


class GroupRoutingError(Exception):
    """Finite, content-free group-routing diagnostic."""

    def __init__(self, category: GroupRoutingErrorCategory | str) -> None:
        try:
            self.category = (
                category
                if isinstance(category, GroupRoutingErrorCategory)
                else GroupRoutingErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = GroupRoutingErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"GroupRoutingError({self.category.value!r})"


@dataclass(frozen=True, repr=False)
class GroupRoutingResult:
    status: GroupRoutingStatus
    snapshot: FleetModeSnapshot | None
    control_result: FleetControlResult | None = field(repr=False)
    turn_result: ExistingDialogueTurnResult | None = field(repr=False)
    disposition: IngressDispositionKind | None
    reason: GroupRoutingReason | None

    def __post_init__(self) -> None:
        _validate_group_result(self)

    def __repr__(self) -> str:
        return (
            "GroupRoutingResult("
            f"status={self.status!r}, snapshot={self.snapshot!r}, "
            f"disposition={self.disposition!r}, reason={self.reason!r})"
        )


@dataclass(frozen=True)
class _PromptMarker:
    update_id: int
    token: object = field(compare=False, repr=False)


_BLOCKED_REASONS = frozenset(
    (
        ExistingDialogueTurnReason.NO_DIALOGUE,
        ExistingDialogueTurnReason.DIALOGUE_NOT_READY,
        ExistingDialogueTurnReason.SETTINGS_MISSING,
        ExistingDialogueTurnReason.SETTINGS_PROFILE_MISMATCH,
        ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED,
        ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED,
        ExistingDialogueTurnReason.MODEL_UNAVAILABLE,
        ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE,
        ExistingDialogueTurnReason.SETTINGS_CHANGED,
    )
)
_MAX_SIGNED_64 = 9_223_372_036_854_775_807
_DUPLICATE_REASONS = frozenset(
    (ExistingDialogueTurnReason.DUPLICATE_NON_JOB, ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB)
)
_TERMINAL_TURN_STATUSES = frozenset(
    (
        ExistingDialogueTurnStatus.COMPLETED,
        ExistingDialogueTurnStatus.FAILED,
        ExistingDialogueTurnStatus.UNKNOWN,
    )
)


def _invalid() -> GroupRoutingError:
    return GroupRoutingError(GroupRoutingErrorCategory.INVALID_ARGUMENT)


def _storage() -> GroupRoutingError:
    return GroupRoutingError(GroupRoutingErrorCategory.STORAGE)


def _codex() -> GroupRoutingError:
    return GroupRoutingError(GroupRoutingErrorCategory.CODEX)


def _invariant() -> GroupRoutingError:
    return GroupRoutingError(GroupRoutingErrorCategory.INVARIANT)


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _map_fleet_error(error: FleetControlError) -> GroupRoutingError:
    mapping = {
        FleetControlErrorCategory.INVALID_ARGUMENT: GroupRoutingErrorCategory.INVALID_ARGUMENT,
        FleetControlErrorCategory.STORAGE: GroupRoutingErrorCategory.STORAGE,
        FleetControlErrorCategory.INVARIANT: GroupRoutingErrorCategory.INVARIANT,
    }
    return GroupRoutingError(mapping.get(error.category, GroupRoutingErrorCategory.INVARIANT))


def _map_dialogue_error(error: DialogueApplicationError) -> GroupRoutingError:
    mapping = {
        DialogueApplicationErrorCategory.INVALID_ARGUMENT: GroupRoutingErrorCategory.INVARIANT,
        DialogueApplicationErrorCategory.STORAGE: GroupRoutingErrorCategory.STORAGE,
        DialogueApplicationErrorCategory.CODEX: GroupRoutingErrorCategory.CODEX,
        DialogueApplicationErrorCategory.INVARIANT: GroupRoutingErrorCategory.INVARIANT,
    }
    return GroupRoutingError(mapping.get(error.category, GroupRoutingErrorCategory.INVARIANT))


def _validate_fleet_result(value: object) -> FleetControlResult:
    if type(value) is not FleetControlResult or type(value.status) is not FleetControlStatus:
        raise _invariant()
    if value.status in {
        FleetControlStatus.APPLIED,
        FleetControlStatus.STALE,
        FleetControlStatus.DUPLICATE,
        FleetControlStatus.STATUS,
        FleetControlStatus.TEXT,
    }:
        if type(value.snapshot) is not FleetModeSnapshot:
            raise _invariant()
    elif value.snapshot is not None:
        raise _invariant()
    return value


def _validate_ingress(value: object, update_id: int | None = None) -> IngressUpdateRecord:
    if type(value) is not IngressUpdateRecord:
        raise _invariant()
    if type(value.update_id) is not int or not 0 <= value.update_id <= _MAX_SIGNED_64:
        raise _invariant()
    if update_id is not None and value.update_id != update_id:
        raise _invariant()
    if type(value.received_at_ms) is not int or not 0 <= value.received_at_ms <= _MAX_SIGNED_64:
        raise _invariant()
    if value.completed_at_ms is not None and (
        type(value.completed_at_ms) is not int
        or not 0 <= value.completed_at_ms <= _MAX_SIGNED_64
        or value.completed_at_ms < value.received_at_ms
    ):
        raise _invariant()
    if type(value.disposition) is not IngressDispositionKind:
        raise _invariant()
    if value.disposition is IngressDispositionKind.JOB:
        if type(value.job_id) is not str or not value.job_id or "\x00" in value.job_id:
            raise _invariant()
    elif value.job_id is not None:
        raise _invariant()
    return value


def _validate_claim(value: object, update_id: int, requested: IngressDispositionKind) -> IngressClaimResult:
    if type(value) is not IngressClaimResult or type(value.duplicate) is not bool:
        raise _invariant()
    record = _validate_ingress(value.record, update_id)
    if not value.duplicate:
        if (
            record.disposition is not requested
            or record.completed_at_ms is None
            or record.received_at_ms != record.completed_at_ms
        ):
            raise _invariant()
    return value


def _validate_job(value: object) -> TurnJobRecord:
    if type(value) is not TurnJobRecord:
        raise _invariant()
    if (
        type(value.job_id) is not str
        or not value.job_id
        or "\x00" in value.job_id
        or type(value.telegram_update_id) is not int
        or value.telegram_update_id < 0
        or type(value.source_chat_id) is not int
        or value.source_chat_id == 0
        or type(value.source_message_id) is not int
        or value.source_message_id < 0
        or type(value.dialogue_id) is not str
        or not value.dialogue_id
        or type(value.server_id) is not str
        or not value.server_id
        or type(value.profile_id) is not str
        or not value.profile_id
        or type(value.state) is not TurnJobState
        or type(value.version) is not int
        or value.version < 0
        or type(value.created_at_ms) is not int
        or value.created_at_ms < 0
        or type(value.updated_at_ms) is not int
        or value.updated_at_ms < value.created_at_ms
        or type(value.input_sha256) is not str
        or not value.input_sha256
    ):
        raise _invariant()
    return value


def _validate_turn_result(value: object) -> ExistingDialogueTurnResult:
    if type(value) is not ExistingDialogueTurnResult:
        raise _invariant()
    if type(value.status) is not ExistingDialogueTurnStatus:
        raise _invariant()
    if value.job is not None:
        _validate_job(value.job)
    if value.output_payload is not None and type(value.output_payload) is not TransientPayloadRecord:
        raise _invariant()
    if value.reason is not None and type(value.reason) is not ExistingDialogueTurnReason:
        raise _invariant()
    if value.status is ExistingDialogueTurnStatus.BUSY:
        if value.job is not None or value.output_payload is not None or value.reason is not None:
            raise _invariant()
    elif value.status is ExistingDialogueTurnStatus.BLOCKED:
        if value.job is not None or value.output_payload is not None or value.reason not in _BLOCKED_REASONS:
            raise _invariant()
    elif value.status is ExistingDialogueTurnStatus.DUPLICATE:
        if value.output_payload is not None or value.reason not in (_DUPLICATE_REASONS | {None}):
            raise _invariant()
    elif value.status in _TERMINAL_TURN_STATUSES:
        if value.job is None or value.reason is not None:
            raise _invariant()
    else:
        raise _invariant()
    return value


def _validate_group_result(value: GroupRoutingResult) -> None:
    if type(value.status) is not GroupRoutingStatus:
        raise _invariant()
    if value.snapshot is not None and type(value.snapshot) is not FleetModeSnapshot:
        raise _invariant()
    if value.control_result is not None:
        _validate_fleet_result(value.control_result)
    if value.turn_result is not None:
        _validate_turn_result(value.turn_result)
    if value.disposition is not None and type(value.disposition) is not IngressDispositionKind:
        raise _invariant()
    if value.reason is not None and type(value.reason) is not GroupRoutingReason:
        raise _invariant()

    status = value.status
    if status is GroupRoutingStatus.CONTROL:
        if (
            value.control_result is None
            or value.control_result.status not in {
                FleetControlStatus.APPLIED,
                FleetControlStatus.STALE,
                FleetControlStatus.DUPLICATE,
            }
            or value.turn_result is not None
            or value.disposition is not None
            or value.reason is not None
        ):
            raise _invariant()
    elif status is GroupRoutingStatus.STATUS:
        if (
            value.control_result is None
            or value.control_result.status is not FleetControlStatus.STATUS
            or value.turn_result is not None
            or value.disposition is not None
            or value.reason is not None
        ):
            raise _invariant()
    elif status is GroupRoutingStatus.PROMPT:
        if (
            value.control_result is not None
            or value.turn_result is None
            or value.turn_result.status not in _TERMINAL_TURN_STATUSES
            or value.disposition is not IngressDispositionKind.JOB
            or value.reason is not None
        ):
            raise _invariant()
    elif status is GroupRoutingStatus.DUPLICATE:
        if value.control_result is not None or value.turn_result is not None:
            raise _invariant()
        if value.reason is GroupRoutingReason.IN_FLIGHT_DUPLICATE:
            if value.disposition is not None:
                raise _invariant()
        elif value.reason is not None or value.disposition is None:
            raise _invariant()
    elif status in (GroupRoutingStatus.BUSY, GroupRoutingStatus.BLOCKED):
        if value.control_result is not None or value.disposition is not IngressDispositionKind.IGNORED_REJECTED:
            raise _invariant()
        if status is GroupRoutingStatus.BUSY:
            if value.reason is GroupRoutingReason.LOCAL_PROMPT_IN_FLIGHT:
                if value.turn_result is not None:
                    raise _invariant()
            elif value.turn_result is None or value.turn_result.status is not ExistingDialogueTurnStatus.BUSY:
                raise _invariant()
            elif value.reason is not None:
                raise _invariant()
        elif value.turn_result is None or value.turn_result.status is not ExistingDialogueTurnStatus.BLOCKED or value.reason is not None:
            raise _invariant()
    elif status is GroupRoutingStatus.IGNORED_SLEEP:
        if (
            value.control_result is not None
            or value.turn_result is not None
            or value.disposition is not IngressDispositionKind.IGNORED_SLEEP
            or value.reason is not None
            or value.snapshot is None
            or value.snapshot.effective_mode is not ControllerMode.SLEEP
        ):
            raise _invariant()
    elif status is GroupRoutingStatus.REJECTED:
        if (
            value.control_result is not None
            or value.turn_result is not None
            or value.disposition is not IngressDispositionKind.IGNORED_REJECTED
            or value.reason not in (GroupRoutingReason.STALE_PROMPT, GroupRoutingReason.INVALID_PROMPT)
        ):
            raise _invariant()
    elif status in (
        GroupRoutingStatus.UNAUTHORIZED,
        GroupRoutingStatus.UNSUPPORTED,
        GroupRoutingStatus.MALFORMED,
    ):
        expected = {
            GroupRoutingStatus.UNAUTHORIZED: FleetControlStatus.UNAUTHORIZED,
            GroupRoutingStatus.UNSUPPORTED: FleetControlStatus.UNSUPPORTED,
            GroupRoutingStatus.MALFORMED: FleetControlStatus.MALFORMED,
        }[status]
        if (
            value.control_result is None
            or value.control_result.status is not expected
            or value.turn_result is not None
            or value.disposition is not None
            or value.reason is not None
        ):
            raise _invariant()
    else:
        raise _invariant()


class FleetGroupRoutingService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        fleet_control: FleetControlPort,
        dialogue_turn: DialogueTurnPort,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        if type(storage) is not SqliteStorage:
            raise _invalid()
        if not _async_callable(fleet_control, "handle") or not _async_callable(dialogue_turn, "execute"):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        self._storage = storage
        self._fleet_control = fleet_control
        self._dialogue_turn = dialogue_turn
        self._clock = now_ms
        self._routing_lock = asyncio.Lock()
        self._prompt_marker: _PromptMarker | None = None

    async def handle(self, update: GroupInboundUpdate) -> GroupRoutingResult:
        if type(update) is not GroupInboundUpdate:
            raise _invalid()
        async with self._routing_lock:
            control_result = await self._fleet_handle(update)
            if update.kind is not GroupInboundKind.TEXT:
                return self._map_non_text(update, control_result)
            if control_result.status is FleetControlStatus.UNAUTHORIZED:
                return GroupRoutingResult(GroupRoutingStatus.UNAUTHORIZED, None, control_result, None, None, None)
            if control_result.status is not FleetControlStatus.TEXT or type(control_result.snapshot) is not FleetModeSnapshot:
                raise _invariant()
            snapshot = control_result.snapshot
            ingress = await self._get_ingress(update.update_id)
            if ingress is not None:
                return self._duplicate(ingress)
            marker = self._prompt_marker
            if marker is not None and marker.update_id == update.update_id:
                return GroupRoutingResult(
                    GroupRoutingStatus.DUPLICATE,
                    None,
                    None,
                    None,
                    None,
                    GroupRoutingReason.IN_FLIGHT_DUPLICATE,
                )
            if update.message_id <= snapshot.last_control_epoch:
                return await self._claim_rejected(
                    update.update_id,
                    snapshot,
                    GroupRoutingReason.STALE_PROMPT,
                )
            if snapshot.effective_mode is ControllerMode.SLEEP:
                return await self._claim_sleep(update.update_id, snapshot)
            if snapshot.effective_mode is not ControllerMode.ACTIVE:
                raise _invariant()
            if marker is not None:
                return await self._claim_local_busy(update.update_id, snapshot)
            try:
                request = ExistingDialoguePromptRequest(
                    update_id=update.update_id,
                    source_chat_id=update.chat_id,
                    source_message_id=update.message_id,
                    text=update.text,
                )
            except DialogueApplicationError as error:
                if error.category is not DialogueApplicationErrorCategory.INVALID_ARGUMENT:
                    raise _invariant()
                return await self._claim_rejected(update.update_id, snapshot, GroupRoutingReason.INVALID_PROMPT)
            marker = _PromptMarker(update.update_id, object())
            self._prompt_marker = marker
            try:
                task = asyncio.create_task(self._run_owned(update, snapshot, request, marker))
            except BaseException:
                self._prompt_marker = None
                raise _invariant() from None
        return await self._await_owned(task)

    async def _fleet_handle(self, update: GroupInboundUpdate) -> FleetControlResult:
        try:
            result = await self._fleet_control.handle(update)
        except asyncio.CancelledError:
            raise
        except FleetControlError as error:
            raise _map_fleet_error(error) from None
        except Exception:
            raise _invariant() from None
        return _validate_fleet_result(result)

    @staticmethod
    def _map_non_text(update: GroupInboundUpdate, result: FleetControlResult) -> GroupRoutingResult:
        if result.status in {
            FleetControlStatus.APPLIED,
            FleetControlStatus.STALE,
            FleetControlStatus.DUPLICATE,
        }:
            if update.kind is not GroupInboundKind.CONTROL:
                raise _invariant()
            return GroupRoutingResult(GroupRoutingStatus.CONTROL, result.snapshot, result, None, None, None)
        if result.status is FleetControlStatus.STATUS:
            if update.kind is not GroupInboundKind.CONTROL:
                raise _invariant()
            return GroupRoutingResult(GroupRoutingStatus.STATUS, result.snapshot, result, None, None, None)
        expected = {
            FleetControlStatus.UNAUTHORIZED: GroupRoutingStatus.UNAUTHORIZED,
            FleetControlStatus.UNSUPPORTED: GroupRoutingStatus.UNSUPPORTED,
            FleetControlStatus.MALFORMED: GroupRoutingStatus.MALFORMED,
        }
        if result.status in expected:
            return GroupRoutingResult(expected[result.status], None, result, None, None, None)
        raise _invariant()

    async def _get_ingress(self, update_id: int) -> IngressUpdateRecord | None:
        try:
            value = await IngressUpdateRepository(self._storage).get(update_id)
        except (StorageError, RepositoryError) as error:
            raise self._map_storage_error(error) from None
        if value is None:
            return None
        return _validate_ingress(value, update_id)

    def _duplicate(self, ingress: IngressUpdateRecord) -> GroupRoutingResult:
        return GroupRoutingResult(GroupRoutingStatus.DUPLICATE, None, None, None, ingress.disposition, None)

    async def _claim(self, update_id: int, disposition: IngressDispositionKind) -> IngressClaimResult:
        try:
            claim = await IngressUpdateRepository(self._storage, now_ms=self._clock).claim_ignored(
                update_id=update_id, disposition=disposition
            )
        except (StorageError, RepositoryError) as error:
            raise self._map_storage_error(error) from None
        return _validate_claim(claim, update_id, disposition)

    async def _claim_sleep(self, update_id: int, snapshot: FleetModeSnapshot) -> GroupRoutingResult:
        claim = await self._claim(update_id, IngressDispositionKind.IGNORED_SLEEP)
        if claim.duplicate:
            return self._duplicate(claim.record)
        return GroupRoutingResult(
            GroupRoutingStatus.IGNORED_SLEEP, snapshot, None, None, IngressDispositionKind.IGNORED_SLEEP, None
        )

    async def _claim_local_busy(self, update_id: int, snapshot: FleetModeSnapshot) -> GroupRoutingResult:
        claim = await self._claim(update_id, IngressDispositionKind.IGNORED_REJECTED)
        if claim.duplicate:
            return self._duplicate(claim.record)
        return GroupRoutingResult(
            GroupRoutingStatus.BUSY,
            snapshot,
            None,
            None,
            IngressDispositionKind.IGNORED_REJECTED,
            GroupRoutingReason.LOCAL_PROMPT_IN_FLIGHT,
        )

    async def _claim_rejected(
        self, update_id: int, snapshot: FleetModeSnapshot, reason: GroupRoutingReason
    ) -> GroupRoutingResult:
        claim = await self._claim(update_id, IngressDispositionKind.IGNORED_REJECTED)
        if claim.duplicate:
            return self._duplicate(claim.record)
        return GroupRoutingResult(
            GroupRoutingStatus.REJECTED,
            snapshot,
            None,
            None,
            IngressDispositionKind.IGNORED_REJECTED,
            reason,
        )

    async def _run_owned(
        self,
        update: GroupInboundUpdate,
        snapshot: FleetModeSnapshot,
        request: ExistingDialoguePromptRequest,
        marker: _PromptMarker,
    ) -> GroupRoutingResult:
        try:
            try:
                turn_result = await self._dialogue_turn.execute(request)
            except asyncio.CancelledError:
                raise
            except DialogueApplicationError as error:
                raise _map_dialogue_error(error) from None
            except Exception:
                raise _invariant() from None
            turn_result = _validate_turn_result(turn_result)
            if turn_result.status is ExistingDialogueTurnStatus.DUPLICATE:
                ingress = await self._get_ingress(update.update_id)
                if ingress is None:
                    raise _invariant()
                return self._duplicate(ingress)
            if turn_result.status in (ExistingDialogueTurnStatus.BUSY, ExistingDialogueTurnStatus.BLOCKED):
                claim = await self._claim(update.update_id, IngressDispositionKind.IGNORED_REJECTED)
                if claim.duplicate:
                    return self._duplicate(claim.record)
                return GroupRoutingResult(
                    GroupRoutingStatus.BUSY if turn_result.status is ExistingDialogueTurnStatus.BUSY else GroupRoutingStatus.BLOCKED,
                    snapshot,
                    None,
                    turn_result,
                    IngressDispositionKind.IGNORED_REJECTED,
                    None,
                )
            if turn_result.status not in _TERMINAL_TURN_STATUSES or turn_result.job is None:
                raise _invariant()
            job = turn_result.job
            if (
                job.telegram_update_id != update.update_id
                or job.source_chat_id != update.chat_id
                or job.source_message_id != update.message_id
            ):
                raise _invariant()
            ingress = await self._get_ingress(update.update_id)
            if ingress is None or ingress.disposition is not IngressDispositionKind.JOB or ingress.job_id != job.job_id:
                raise _invariant()
            return GroupRoutingResult(
                GroupRoutingStatus.PROMPT,
                snapshot,
                None,
                turn_result,
                IngressDispositionKind.JOB,
                None,
            )
        finally:
            async with self._routing_lock:
                if self._prompt_marker is marker:
                    self._prompt_marker = None

    async def _await_owned(self, task: asyncio.Task[GroupRoutingResult]) -> GroupRoutingResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None

    @staticmethod
    def _map_storage_error(error: BaseException) -> GroupRoutingError:
        if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invalid()
        if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        return _storage()


__all__ = [
    "FleetControlPort",
    "DialogueTurnPort",
    "GroupRoutingStatus",
    "GroupRoutingReason",
    "GroupRoutingErrorCategory",
    "GroupRoutingError",
    "GroupRoutingResult",
    "FleetGroupRoutingService",
]
