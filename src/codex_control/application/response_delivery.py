"""Durable, one-attempt delivery of a completed turn's user-visible output."""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from codex_control.storage import (
    DeliveryClaimResult,
    DeliveryFinishOutcome,
    DeliveryFinishResult,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliveryPlanResult,
    DeliverySegmentRecord,
    DeliverySegmentRepository,
    DeliverySegmentState,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
    TransientPayloadKind,
    TransientPayloadRecord,
    TransientPayloadRepository,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
)


P61_MIN_TEXT_LIMIT = 512
P61_MAX_TEXT_LIMIT = 4096
P61_DISPLAY_PAYLOAD_RETENTION_MS = 86_400_000
P61_EMPTY_COMPLETION_TEXT = "✅ Выполнено"

_MAX_SIGNED_64 = 9_223_372_036_854_775_807
_ID_LENGTH = 128
_P61_MAX_SEGMENTS = 4096


class TelegramDeliveryEffectStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class TelegramDeliveryErrorClass(StrEnum):
    TELEGRAM_REQUEST_REJECTED = "TELEGRAM_REQUEST_REJECTED"
    TELEGRAM_NETWORK_AMBIGUOUS = "TELEGRAM_NETWORK_AMBIGUOUS"
    TELEGRAM_LOCAL_DISPATCH_FAILED = "TELEGRAM_LOCAL_DISPATCH_FAILED"
    TELEGRAM_RESULT_INVALID = "TELEGRAM_RESULT_INVALID"
    TELEGRAM_RECOVERY_AMBIGUOUS = "TELEGRAM_RECOVERY_AMBIGUOUS"


class TelegramDeliveryPort(Protocol):
    async def create_message(
        self, *, chat_id: int, text: str
    ) -> TelegramDeliveryEffectResult: ...

    async def edit_message(
        self, *, chat_id: int, message_id: int, text: str
    ) -> TelegramDeliveryEffectResult: ...


@dataclass(frozen=True, repr=False)
class TelegramDeliveryEffectResult:
    status: TelegramDeliveryEffectStatus
    message_id: int | None
    error_class: TelegramDeliveryErrorClass | None

    def __post_init__(self) -> None:
        if type(self.status) is not TelegramDeliveryEffectStatus:
            raise _invalid()
        if self.status is TelegramDeliveryEffectStatus.CONFIRMED:
            if _positive_message_id(self.message_id) is None or self.error_class is not None:
                raise _invalid()
        elif self.status is TelegramDeliveryEffectStatus.FAILED:
            if (
                self.message_id is not None
                or self.error_class is not TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED
            ):
                raise _invalid()
        elif self.status is TelegramDeliveryEffectStatus.UNKNOWN:
            if (
                self.message_id is not None
                or self.error_class is not TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS
            ):
                raise _invalid()
        else:
            raise _invalid()

    def __repr__(self) -> str:
        return (
            "TelegramDeliveryEffectResult("
            f"status={getattr(self.status, 'value', self.status)!r}, error_class="
            f"{None if self.error_class is None else getattr(self.error_class, 'value', self.error_class)!r})"
        )


@dataclass(frozen=True, repr=False)
class TurnDeliveryRequest:
    job_id: str
    status_message_id: int | None = None

    def __post_init__(self) -> None:
        _validate_job_id(self.job_id)
        _validate_message_id(self.status_message_id, nullable=True)

    def __repr__(self) -> str:
        return "TurnDeliveryRequest(<redacted>)"


class TurnDeliveryStatus(StrEnum):
    DELIVERED = "DELIVERED"
    ALREADY_DELIVERED = "ALREADY_DELIVERED"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class TurnDeliveryReason(StrEnum):
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_NOT_DELIVERABLE = "JOB_NOT_DELIVERABLE"


class TurnDeliveryErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class TurnDeliveryError(Exception):
    """Finite, content-free delivery application error."""

    def __init__(self, category: TurnDeliveryErrorCategory | str) -> None:
        try:
            self.category = (
                category
                if isinstance(category, TurnDeliveryErrorCategory)
                else TurnDeliveryErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = TurnDeliveryErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"TurnDeliveryError({self.category.value!r})"


@dataclass(frozen=True, repr=False)
class TurnDeliveryResult:
    status: TurnDeliveryStatus
    job: TurnJobRecord | None
    segments: tuple[DeliverySegmentRecord, ...]
    reason: TurnDeliveryReason | None

    def __post_init__(self) -> None:
        if type(self.status) is not TurnDeliveryStatus:
            raise _invariant()
        if type(self.segments) is not tuple:
            raise _invariant()
        if self.reason is not None and type(self.reason) is not TurnDeliveryReason:
            raise _invariant()

        try:
            if self.status in (TurnDeliveryStatus.DELIVERED, TurnDeliveryStatus.ALREADY_DELIVERED):
                if (
                    type(self.job) is not TurnJobRecord
                    or self.job.state is not TurnJobState.DELIVERED
                    or not self.segments
                    or self.reason is not None
                ):
                    raise _invariant()
                _validate_p6_plan(self.job, self.segments)
                if any(segment.state is not DeliverySegmentState.CONFIRMED for segment in self.segments):
                    raise _invariant()
            elif self.status is TurnDeliveryStatus.DELIVERY_UNKNOWN:
                if (
                    type(self.job) is not TurnJobRecord
                    or self.job.state is not TurnJobState.DELIVERY_UNKNOWN
                    or not self.segments
                    or self.reason is not None
                ):
                    raise _invariant()
                _validate_p6_plan(self.job, self.segments)
            elif self.status is TurnDeliveryStatus.FAILED:
                if (
                    type(self.job) is not TurnJobRecord
                    or self.job.state is not TurnJobState.FAILED
                    or not self.segments
                    or self.reason is not None
                ):
                    raise _invariant()
                _validate_p6_plan(self.job, self.segments)
            elif self.status is TurnDeliveryStatus.BLOCKED:
                if self.segments:
                    raise _invariant()
                if self.reason is TurnDeliveryReason.JOB_NOT_FOUND:
                    if self.job is not None:
                        raise _invariant()
                elif self.reason is TurnDeliveryReason.JOB_NOT_DELIVERABLE:
                    if (
                        type(self.job) is not TurnJobRecord
                        or self.job.state
                        not in (
                            TurnJobState.FAILED,
                            TurnJobState.UNKNOWN,
                            TurnJobState.RECEIVED,
                            TurnJobState.CLAIMED,
                            TurnJobState.CODEX_STARTING,
                            TurnJobState.CODEX_RUNNING,
                        )
                    ):
                        raise _invariant()
                else:
                    raise _invariant()
            else:
                raise _invariant()
        except TurnDeliveryError:
            raise
        except Exception:
            raise _invariant() from None

    def __repr__(self) -> str:
        return (
            "TurnDeliveryResult("
            f"status={getattr(self.status, 'value', self.status)!r}, reason="
            f"{None if self.reason is None else getattr(self.reason, 'value', self.reason)!r})"
        )


def _invalid() -> TurnDeliveryError:
    return TurnDeliveryError(TurnDeliveryErrorCategory.INVALID_ARGUMENT)


def _storage_error() -> TurnDeliveryError:
    return TurnDeliveryError(TurnDeliveryErrorCategory.STORAGE)


def _invariant() -> TurnDeliveryError:
    return TurnDeliveryError(TurnDeliveryErrorCategory.INVARIANT)


def _validate_job_id(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invalid()
    return value


def _validate_message_id(value: object, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int or not 1 <= value <= _MAX_SIGNED_64:
        raise _invalid()
    return value


def _validate_limit(value: object) -> int:
    if type(value) is not int or not P61_MIN_TEXT_LIMIT <= value <= P61_MAX_TEXT_LIMIT:
        raise _invalid()
    return value


def _validate_clock_value(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise _invariant() from None
    if type(value) is not int or not 0 <= value <= _MAX_SIGNED_64:
        raise _invariant()
    return value


def _fixed_clock(value: int) -> Callable[[], int]:
    return lambda: value


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _close_awaitable(value: object) -> None:
    close = getattr(value, "close", None)
    if callable(close):
        close()


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _default_id_factory(kind: str) -> str:
    return f"p61-{kind}-{uuid4().hex}"


def _repository_error(error: BaseException) -> TurnDeliveryError:
    if isinstance(error, StorageError):
        return _storage_error()
    if isinstance(error, RepositoryError):
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.ALREADY_EXISTS:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invalid()
        return _storage_error()
    return _storage_error()


def _generated_id(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invariant()
    return value


def segment_telegram_text(text: str, limit: int) -> tuple[str, ...]:
    """Split plain text using the frozen P6.1 boundary priority."""
    if type(text) is not str or not text or "\x00" in text:
        raise _invalid()
    _validate_limit(limit)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise _invalid() from None

    if len(text) > limit * _P61_MAX_SEGMENTS:
        raise _invalid()

    preferred: list[str] = []
    remaining = text
    while len(remaining) > limit:
        paragraph = remaining.rfind("\n\n", 0, limit - 1)
        if paragraph >= 0:
            cut = paragraph + 2
        else:
            line = remaining.rfind("\n", 0, limit)
            if line >= 0:
                cut = line + 1
            else:
                space = remaining.rfind(" ", 0, limit)
                cut = space + 1 if space >= 0 else limit
        preferred.append(remaining[:cut])
        remaining = remaining[cut:]
    preferred.append(remaining)
    if len(preferred) <= _P61_MAX_SEGMENTS:
        return tuple(preferred)

    chunks = tuple(
        text[offset:offset + limit]
        for offset in range(0, len(text), limit)
    )
    if not 1 <= len(chunks) <= _P61_MAX_SEGMENTS:
        raise _invariant()
    if any(not chunk or len(chunk) > limit for chunk in chunks) or "".join(chunks) != text:
        raise _invariant()
    return chunks


def _validate_p6_plan(job: TurnJobRecord, segments: tuple[DeliverySegmentRecord, ...]) -> None:
    if not segments:
        raise _invariant()
    for expected, segment in enumerate(segments, 1):
        if not isinstance(segment, DeliverySegmentRecord) or segment.job_id != job.job_id:
            raise _invariant()
        if segment.sequence != expected:
            raise _invariant()
        if segment.payload_id is None and segment.state not in (
            DeliverySegmentState.CONFIRMED,
            DeliverySegmentState.FAILED,
        ):
            raise _invariant()
        if segment.operation is DeliveryOperation.CREATE:
            if segment.target_message_id is not None:
                raise _invariant()
        elif segment.operation is DeliveryOperation.EDIT:
            if expected != 1 or _positive_message_id(segment.target_message_id) is None:
                raise _invariant()
        else:
            raise _invariant()
        if segment.state is DeliverySegmentState.CONFIRMED:
            if _positive_message_id(segment.confirmed_message_id) is None:
                raise _invariant()

    states = tuple(segment.state for segment in segments)
    if job.state is TurnJobState.DELIVERY_PENDING:
        if any(state is not DeliverySegmentState.PENDING for state in states):
            raise _invariant()
    elif job.state is TurnJobState.DELIVERING:
        sending = states.count(DeliverySegmentState.SENDING)
        if sending == 1:
            sending_index = states.index(DeliverySegmentState.SENDING)
            if (
                not all(state is DeliverySegmentState.CONFIRMED for state in states[:sending_index])
                or not all(state is DeliverySegmentState.PENDING for state in states[sending_index + 1:])
            ):
                raise _invariant()
        else:
            pending = next((i for i, state in enumerate(states) if state is DeliverySegmentState.PENDING), None)
            if pending is None or pending == 0:
                raise _invariant()
            if (
                not all(state is DeliverySegmentState.CONFIRMED for state in states[:pending])
                or not all(state is DeliverySegmentState.PENDING for state in states[pending:])
            ):
                raise _invariant()
    elif job.state is TurnJobState.DELIVERED:
        if any(state is not DeliverySegmentState.CONFIRMED for state in states):
            raise _invariant()
    elif job.state is TurnJobState.DELIVERY_UNKNOWN:
        _validate_terminal_pattern(states, DeliverySegmentState.UNKNOWN)
    elif job.state is TurnJobState.FAILED:
        _validate_terminal_pattern(states, DeliverySegmentState.FAILED)
    else:
        raise _invariant()


def _validate_terminal_pattern(
    states: tuple[DeliverySegmentState, ...], terminal: DeliverySegmentState
) -> None:
    if states.count(terminal) != 1:
        raise _invariant()
    index = states.index(terminal)
    if (
        not all(state is DeliverySegmentState.CONFIRMED for state in states[:index])
        or not all(state is DeliverySegmentState.PENDING for state in states[index + 1:])
    ):
        raise _invariant()


def _positive_message_id(value: object) -> int | None:
    if type(value) is int and 1 <= value <= _MAX_SIGNED_64:
        return value
    return None


def _replace_segment(
    segments: tuple[DeliverySegmentRecord, ...], replacement: DeliverySegmentRecord
) -> tuple[DeliverySegmentRecord, ...]:
    result = tuple(
        replacement if segment.sequence == replacement.sequence else segment
        for segment in segments
    )
    if all(segment is not replacement for segment in result):
        raise _invariant()
    return result


def _validate_claim(
    claim: object,
    job: TurnJobRecord,
    pending: DeliverySegmentRecord,
) -> tuple[DeliverySegmentRecord, str]:
    if not isinstance(claim, DeliveryClaimResult):
        raise _invariant()
    claimed_job = claim.job
    segment = claim.segment
    payload = claim.payload
    if (
        not isinstance(claimed_job, TurnJobRecord)
        or claimed_job.job_id != job.job_id
        or claimed_job.dialogue_id != job.dialogue_id
        or claimed_job.version != job.version + 1
        or claimed_job.state is not TurnJobState.DELIVERING
        or not isinstance(segment, DeliverySegmentRecord)
        or segment.job_id != job.job_id
        or segment.sequence != pending.sequence
        or segment.operation is not pending.operation
        or segment.target_message_id != pending.target_message_id
        or segment.payload_id != pending.payload_id
        or segment.payload_sha256 != pending.payload_sha256
        or segment.state is not DeliverySegmentState.SENDING
        or segment.attempt_count != 1
        or not isinstance(payload, TransientPayloadRecord)
        or type(payload.content) is not bytes
        or payload.kind is not TransientPayloadKind.DISPLAY
        or payload.job_id != job.job_id
        or payload.dialogue_id != job.dialogue_id
        or payload.content_sha256 != segment.payload_sha256
        or payload.content_sha256 != _sha256(payload.content)
        or payload.byte_length != len(payload.content)
    ):
        raise _invariant()
    if segment.operation is DeliveryOperation.EDIT and _positive_message_id(segment.target_message_id) is None:
        raise _invariant()
    try:
        text = payload.content.decode("utf-8")
    except (AttributeError, UnicodeDecodeError):
        raise _invariant() from None
    return segment, text


def _validate_effect_result(value: object) -> bool:
    return (
        type(value) is TelegramDeliveryEffectResult
        and type(value.status) is TelegramDeliveryEffectStatus
        and (
            (
                value.status is TelegramDeliveryEffectStatus.CONFIRMED
                and _positive_message_id(value.message_id) is not None
                and value.error_class is None
            )
            or (
                value.status is TelegramDeliveryEffectStatus.FAILED
                and value.message_id is None
                and value.error_class is TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED
            )
            or (
                value.status is TelegramDeliveryEffectStatus.UNKNOWN
                and value.message_id is None
                and value.error_class is TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS
            )
        )
    )


class TurnDeliveryService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        telegram: TelegramDeliveryPort,
        text_limit: int,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        _validate_limit(text_limit)
        if not _async_callable(telegram, "create_message") or not _async_callable(telegram, "edit_message"):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        self._storage = storage
        self._telegram = telegram
        self._text_limit = text_limit
        self._clock = now_ms if now_ms is not None else _default_clock
        self._id_factory = id_factory if id_factory is not None else _default_id_factory
        self._lock = asyncio.Lock()

    async def deliver(self, request: TurnDeliveryRequest) -> TurnDeliveryResult:
        if type(request) is not TurnDeliveryRequest:
            raise _invalid()
        owned = asyncio.create_task(self._deliver_locked(request))
        return await self._await_owned(owned)

    async def _deliver_locked(self, request: TurnDeliveryRequest) -> TurnDeliveryResult:
        async with self._lock:
            jobs = TurnJobRepository(self._storage)
            delivery = DeliverySegmentRepository(self._storage)
            try:
                job = await jobs.get(request.job_id)
                if job is None:
                    return TurnDeliveryResult(
                        TurnDeliveryStatus.BLOCKED, None, (), TurnDeliveryReason.JOB_NOT_FOUND
                    )
                segments = await delivery.list_for_job(request.job_id)
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            except Exception:
                raise _invariant() from None

            if job.state is TurnJobState.CODEX_COMPLETED:
                if segments:
                    raise _invariant()
                job, segments, delivery = await self._create_plan(job, request)
            elif job.state in (
                TurnJobState.DELIVERY_PENDING,
                TurnJobState.DELIVERING,
                TurnJobState.DELIVERED,
                TurnJobState.DELIVERY_UNKNOWN,
            ):
                _validate_p6_plan(job, segments)
                if job.state is TurnJobState.DELIVERED:
                    return TurnDeliveryResult(TurnDeliveryStatus.ALREADY_DELIVERED, job, segments, None)
                if job.state is TurnJobState.DELIVERY_UNKNOWN:
                    return TurnDeliveryResult(TurnDeliveryStatus.DELIVERY_UNKNOWN, job, segments, None)
            elif job.state is TurnJobState.FAILED and segments:
                _validate_p6_plan(job, segments)
                return TurnDeliveryResult(TurnDeliveryStatus.FAILED, job, segments, None)
            elif job.state in (
                TurnJobState.FAILED,
                TurnJobState.UNKNOWN,
                TurnJobState.RECEIVED,
                TurnJobState.CLAIMED,
                TurnJobState.CODEX_STARTING,
                TurnJobState.CODEX_RUNNING,
            ):
                if segments:
                    raise _invariant()
                return TurnDeliveryResult(
                    TurnDeliveryStatus.BLOCKED, job, (), TurnDeliveryReason.JOB_NOT_DELIVERABLE
                )
            else:
                raise _invariant()

            if job.state is TurnJobState.DELIVERING:
                sending = tuple(
                    segment for segment in segments if segment.state is DeliverySegmentState.SENDING
                )
                if sending:
                    return await self._recover_sending(job, segments, sending[0], delivery)
            return await self._execute(job, segments, delivery)

    async def _create_plan(
        self, job: TurnJobRecord, request: TurnDeliveryRequest
    ) -> tuple[TurnJobRecord, tuple[DeliverySegmentRecord, ...], DeliverySegmentRepository]:
        output_repo = TransientPayloadRepository(self._storage)
        try:
            output = await output_repo.get_output_for_job(job.job_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception:
            raise _invariant() from None
        if output is None:
            text = P61_EMPTY_COMPLETION_TEXT
        else:
            if (
                not isinstance(output, TransientPayloadRecord)
                or output.kind is not TransientPayloadKind.OUTPUT
                or output.job_id != job.job_id
                or output.dialogue_id != job.dialogue_id
            ):
                raise _invariant()
            try:
                text = output.content.decode("utf-8")
            except (AttributeError, UnicodeDecodeError):
                raise _invariant() from None
        try:
            chunks = segment_telegram_text(text, self._text_limit)
        except TurnDeliveryError:
            raise _invariant() from None

        now = _validate_clock_value(self._clock)
        if now > _MAX_SIGNED_64 - P61_DISPLAY_PAYLOAD_RETENTION_MS:
            raise _invariant()
        expiry = now + P61_DISPLAY_PAYLOAD_RETENTION_MS
        payloads = TransientPayloadRepository(self._storage, now_ms=_fixed_clock(now))

        created: list[TransientPayloadRecord] = []
        for chunk in chunks:
            try:
                payload_id = _generated_id(self._id_factory("display"))
            except TurnDeliveryError:
                raise
            except Exception:
                raise _invariant() from None
            try:
                payload = await payloads.create(
                    payload_id=payload_id,
                    dialogue_id=job.dialogue_id,
                    job_id=job.job_id,
                    kind=TransientPayloadKind.DISPLAY,
                    content=chunk.encode("utf-8"),
                    expires_at_ms=expiry,
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            except Exception:
                raise _invariant() from None
            if (
                not isinstance(payload, TransientPayloadRecord)
                or payload.payload_id != payload_id
                or payload.dialogue_id != job.dialogue_id
                or payload.job_id != job.job_id
                or payload.kind is not TransientPayloadKind.DISPLAY
                or payload.content != chunk.encode("utf-8")
                or payload.content_sha256 != _sha256(payload.content)
                or payload.byte_length != len(payload.content)
                or payload.expires_at_ms != expiry
            ):
                raise _invariant()
            created.append(payload)

        items = tuple(
            DeliveryPlanItem(
                DeliveryOperation.EDIT if index == 0 and request.status_message_id is not None else DeliveryOperation.CREATE,
                payload.payload_id,
                request.status_message_id if index == 0 and request.status_message_id is not None else None,
            )
            for index, payload in enumerate(created)
        )
        delivery = DeliverySegmentRepository(self._storage, now_ms=_fixed_clock(now))
        try:
            planned = await delivery.plan(
                job_id=job.job_id, expected_job_version=job.version, items=items
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception:
            raise _invariant() from None
        if not isinstance(planned, DeliveryPlanResult):
            raise _invariant()
        if planned.job.job_id != job.job_id or planned.job.state is not TurnJobState.DELIVERY_PENDING:
            raise _invariant()
        segments = planned.segments
        _validate_p6_plan(planned.job, segments)
        return planned.job, segments, delivery

    async def _recover_sending(
        self,
        job: TurnJobRecord,
        segments: tuple[DeliverySegmentRecord, ...],
        segment: DeliverySegmentRecord,
        delivery: DeliverySegmentRepository,
    ) -> TurnDeliveryResult:
        try:
            finished = await delivery.finish_sending(
                job_id=job.job_id,
                sequence=segment.sequence,
                expected_job_version=job.version,
                outcome=DeliveryFinishOutcome.UNKNOWN,
                error_class=TelegramDeliveryErrorClass.TELEGRAM_RECOVERY_AMBIGUOUS.value,
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception:
            raise _invariant() from None
        updated = self._validate_finished(
            finished, job, segment, DeliveryFinishOutcome.UNKNOWN, None,
            TelegramDeliveryErrorClass.TELEGRAM_RECOVERY_AMBIGUOUS.value,
        )
        updated_segments = _replace_segment(segments, updated.segment)
        return TurnDeliveryResult(
            TurnDeliveryStatus.DELIVERY_UNKNOWN, updated.job, updated_segments, None
        )

    async def _execute(
        self,
        job: TurnJobRecord,
        segments: tuple[DeliverySegmentRecord, ...],
        delivery: DeliverySegmentRepository,
    ) -> TurnDeliveryResult:
        while True:
            pending = next(
                (segment for segment in segments if segment.state is DeliverySegmentState.PENDING), None
            )
            if pending is None:
                if job.state is not TurnJobState.DELIVERED:
                    raise _invariant()
                _validate_p6_plan(job, segments)
                return TurnDeliveryResult(TurnDeliveryStatus.DELIVERED, job, segments, None)
            try:
                claim = await delivery.claim_next(
                    job_id=job.job_id, expected_job_version=job.version
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            except Exception:
                raise _invariant() from None
            try:
                claimed_segment, text = _validate_claim(claim, job, pending)
                if not text or "\x00" in text or len(text) > self._text_limit:
                    raise _invariant()
            except TurnDeliveryError:
                return await self._finish_local_failure(claim, pending, segments, delivery)

            effect, created_task, effect_error = await self._effect_task(
                claim.job, claimed_segment, text
            )
            if created_task is None:
                return await self._finish_local_failure(
                    claim, claimed_segment, segments, delivery
                )
            if effect is None:
                outcome = DeliveryFinishOutcome.UNKNOWN
                error_class = (
                    effect_error
                    or TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID.value
                )
                confirmed_id = None
            elif effect.status is TelegramDeliveryEffectStatus.CONFIRMED:
                if (
                    claimed_segment.operation is DeliveryOperation.EDIT
                    and effect.message_id != claimed_segment.target_message_id
                ):
                    outcome = DeliveryFinishOutcome.UNKNOWN
                    error_class = TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID.value
                    confirmed_id = None
                else:
                    outcome = DeliveryFinishOutcome.CONFIRMED
                    error_class = None
                    confirmed_id = effect.message_id
            elif effect.status is TelegramDeliveryEffectStatus.FAILED:
                outcome = DeliveryFinishOutcome.FAILED
                error_class = TelegramDeliveryErrorClass.TELEGRAM_REQUEST_REJECTED.value
                confirmed_id = None
            else:
                outcome = DeliveryFinishOutcome.UNKNOWN
                error_class = TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS.value
                confirmed_id = None

            try:
                finished = await delivery.finish_sending(
                    job_id=claim.job.job_id,
                    sequence=claimed_segment.sequence,
                    expected_job_version=claim.job.version,
                    outcome=outcome,
                    confirmed_message_id=confirmed_id,
                    error_class=error_class,
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            except Exception:
                raise _invariant() from None
            completed = self._validate_finished(
                finished, claim.job, claimed_segment, outcome, confirmed_id, error_class
            )
            segments = _replace_segment(segments, completed.segment)
            job = completed.job
            if outcome is DeliveryFinishOutcome.CONFIRMED:
                continue
            status = (
                TurnDeliveryStatus.FAILED
                if outcome is DeliveryFinishOutcome.FAILED
                else TurnDeliveryStatus.DELIVERY_UNKNOWN
            )
            return TurnDeliveryResult(status, job, segments, None)

    async def _finish_local_failure(
        self,
        claim: object,
        segment: DeliverySegmentRecord,
        segments: tuple[DeliverySegmentRecord, ...],
        delivery: DeliverySegmentRepository,
    ) -> TurnDeliveryResult:
        if not isinstance(claim, DeliveryClaimResult):
            raise _invariant()
        try:
            finished = await delivery.finish_sending(
                job_id=claim.job.job_id,
                sequence=segment.sequence,
                expected_job_version=claim.job.version,
                outcome=DeliveryFinishOutcome.FAILED,
                error_class=TelegramDeliveryErrorClass.TELEGRAM_LOCAL_DISPATCH_FAILED.value,
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception:
            raise _invariant() from None
        completed = self._validate_finished(
            finished, claim.job, segment, DeliveryFinishOutcome.FAILED, None,
            TelegramDeliveryErrorClass.TELEGRAM_LOCAL_DISPATCH_FAILED.value,
        )
        return TurnDeliveryResult(TurnDeliveryStatus.FAILED, completed.job, _replace_segment(segments, completed.segment), None)

    async def _effect_task(
        self, job: TurnJobRecord, segment: DeliverySegmentRecord, text: str
    ) -> tuple[
        TelegramDeliveryEffectResult | None,
        asyncio.Task[object] | None,
        str | None,
    ]:
        try:
            if segment.operation is DeliveryOperation.CREATE:
                awaitable = self._telegram.create_message(chat_id=job.source_chat_id, text=text)
            elif segment.operation is DeliveryOperation.EDIT:
                target = _positive_message_id(segment.target_message_id)
                if target is None:
                    raise _invariant()
                awaitable = self._telegram.edit_message(
                    chat_id=job.source_chat_id, message_id=target, text=text
                )
            else:
                raise _invariant()
        except TurnDeliveryError:
            raise
        except Exception:
            return None, None, None
        if not inspect.isawaitable(awaitable):
            return None, None, None
        try:
            task = asyncio.create_task(awaitable)
        except Exception:
            _close_awaitable(awaitable)
            return None, None, None
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.cancelled():
                return (
                    None,
                    task,
                    TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS.value,
                )
            raise
        except Exception:
            return (
                None,
                task,
                TelegramDeliveryErrorClass.TELEGRAM_NETWORK_AMBIGUOUS.value,
            )
        if not _validate_effect_result(result):
            return (
                None,
                task,
                TelegramDeliveryErrorClass.TELEGRAM_RESULT_INVALID.value,
            )
        return result, task, None

    @staticmethod
    def _validate_finished(
        finished: object,
        job: TurnJobRecord,
        segment: DeliverySegmentRecord,
        outcome: DeliveryFinishOutcome,
        confirmed_id: int | None,
        expected_error_class: str | None,
    ) -> DeliveryFinishResult:
        if (
            not isinstance(finished, DeliveryFinishResult)
            or not isinstance(finished.job, TurnJobRecord)
            or not isinstance(finished.segment, DeliverySegmentRecord)
        ):
            raise _invariant()
        if (
            finished.job.job_id != job.job_id
            or finished.job.dialogue_id != job.dialogue_id
            or finished.job.version != job.version + 1
            or finished.segment.job_id != job.job_id
            or finished.segment.sequence != segment.sequence
            or finished.segment.operation is not segment.operation
            or finished.segment.target_message_id != segment.target_message_id
            or finished.segment.payload_id != segment.payload_id
            or finished.segment.payload_sha256 != segment.payload_sha256
        ):
            raise _invariant()
        expected_state = {
            DeliveryFinishOutcome.CONFIRMED: DeliverySegmentState.CONFIRMED,
            DeliveryFinishOutcome.UNKNOWN: DeliverySegmentState.UNKNOWN,
            DeliveryFinishOutcome.FAILED: DeliverySegmentState.FAILED,
        }[outcome]
        if finished.segment.state is not expected_state:
            raise _invariant()
        if outcome is DeliveryFinishOutcome.CONFIRMED:
            if _positive_message_id(finished.segment.confirmed_message_id) != confirmed_id:
                raise _invariant()
            if finished.job.state not in (TurnJobState.DELIVERING, TurnJobState.DELIVERED):
                raise _invariant()
        elif outcome is DeliveryFinishOutcome.UNKNOWN:
            if (
                finished.job.state is not TurnJobState.DELIVERY_UNKNOWN
                or finished.job.error_class != expected_error_class
            ):
                raise _invariant()
        elif (
            finished.job.state is not TurnJobState.FAILED
            or finished.job.error_class != expected_error_class
        ):
            raise _invariant()
        return finished

    async def _await_owned(self, task: asyncio.Task[TurnDeliveryResult]) -> TurnDeliveryResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None


def _sha256(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
