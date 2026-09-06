"""P2.4b durable delivery-segment claims."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .core_repositories import _default_clock, _next_version, _validate_clock, _materialize_dialogue
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .transient_payloads import TransientPayloadKind, TransientPayloadRecord
from .turn_job_records import TurnJobRecord, TurnJobState
from .turn_job_repositories import (
    MAX_SQLITE_INT,
    _dialogue_row,
    _job_row,
    _materialize_job,
    _materialize_payload,
    _payload_row,
)
from .delivery_records import (
    DeliveryClaimResult,
    DeliveryFinishOutcome,
    DeliveryFinishResult,
    DeliveryOperation,
    DeliveryPlanItem,
    DeliveryPlanResult,
    DeliverySegmentRecord,
    DeliverySegmentState,
)


_ID_LENGTH = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CLASS_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _not_found() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.NOT_FOUND)


def _state_conflict() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.STATE_CONFLICT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_id(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invalid()
    return value


def _validate_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_message_id(value: object, *, nullable: bool = False) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_sha(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _validate_error_class(value: object) -> str:
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _validate_operation(value: object) -> DeliveryOperation:
    if not isinstance(value, DeliveryOperation):
        raise _invalid()
    return value


def _validate_state(value: object) -> DeliverySegmentState:
    if not isinstance(value, str):
        raise _invariant()
    try:
        return DeliverySegmentState(value)
    except (TypeError, ValueError):
        raise _invariant() from None


def _validate_outcome(value: object) -> DeliveryFinishOutcome:
    if not isinstance(value, DeliveryFinishOutcome):
        raise _invalid()
    return value


def _stored_id(value: object, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invariant()
    return value


def _stored_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _stored_message_id(value: object) -> int | None:
    if value is None:
        return None
    return _stored_nonnegative(value)


def _stored_sha(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _segment_select() -> str:
    return (
        "SELECT job_id, sequence, operation, target_message_id, payload_id, payload_sha256, "
        "state, attempt_count, confirmed_message_id, created_at_ms, updated_at_ms "
        "FROM delivery_segments"
    )


def _segment_row(connection: Any, job_id: str, sequence: int) -> Any:
    return connection.execute(
        _segment_select() + " WHERE job_id = ? AND sequence = ?", (job_id, sequence)
    ).fetchone()


def _payload_for_segment(
    connection: Any,
    segment: DeliverySegmentRecord,
    job: TurnJobRecord,
    *,
    required: bool,
) -> TransientPayloadRecord | None:
    if segment.payload_id is None:
        if required:
            raise _invariant()
        return None
    row = _payload_row(connection, segment.payload_id)
    if row is None:
        raise _invariant()
    payload = _materialize_payload(connection, row)
    dialogue_row = _dialogue_row(connection, job.dialogue_id)
    if dialogue_row is None:
        raise _invariant()
    dialogue = _materialize_dialogue(dialogue_row)
    if (
        payload.kind is not TransientPayloadKind.DISPLAY
        or payload.job_id != job.job_id
        or payload.dialogue_id != job.dialogue_id
        or payload.content_sha256 != segment.payload_sha256
        or dialogue.dialogue_id != job.dialogue_id
    ):
        raise _invariant()
    return payload


def _materialize_segment(
    connection: Any,
    row: Any,
    *,
    job: TurnJobRecord,
) -> tuple[DeliverySegmentRecord, TransientPayloadRecord | None]:
    if row is None or len(row) != 11:
        raise _invariant()
    row_job_id = _stored_id(row[0])
    if row_job_id != job.job_id:
        raise _invariant()
    sequence = _stored_nonnegative(row[1])
    if sequence < 1:
        raise _invariant()
    operation_value = row[2]
    if not isinstance(operation_value, str):
        raise _invariant()
    try:
        operation = DeliveryOperation(operation_value)
    except (TypeError, ValueError):
        raise _invariant() from None
    target_message_id = _stored_message_id(row[3])
    payload_id = _stored_id(row[4], nullable=True)
    payload_sha256 = _stored_sha(row[5])
    state = _validate_state(row[6])
    attempt_count = _stored_nonnegative(row[7])
    confirmed_message_id = _stored_message_id(row[8])
    created_at_ms = _stored_nonnegative(row[9])
    updated_at_ms = _stored_nonnegative(row[10])
    if updated_at_ms < created_at_ms:
        raise _invariant()
    if operation is DeliveryOperation.CREATE:
        if target_message_id is not None:
            raise _invariant()
    elif target_message_id is None:
        raise _invariant()
    if state is DeliverySegmentState.PENDING:
        if attempt_count != 0 or confirmed_message_id is not None:
            raise _invariant()
    elif state in (DeliverySegmentState.SENDING, DeliverySegmentState.UNKNOWN, DeliverySegmentState.FAILED):
        if attempt_count != 1 or confirmed_message_id is not None:
            raise _invariant()
    elif state is DeliverySegmentState.CONFIRMED:
        if attempt_count != 1 or confirmed_message_id is None:
            raise _invariant()
        if operation is DeliveryOperation.EDIT and confirmed_message_id != target_message_id:
            raise _invariant()
    segment = DeliverySegmentRecord(
        job.job_id, sequence, operation, target_message_id, payload_id, payload_sha256,
        state, attempt_count, confirmed_message_id, created_at_ms, updated_at_ms,
    )
    payload = _payload_for_segment(
        connection, segment, job,
        required=state in (
            DeliverySegmentState.PENDING,
            DeliverySegmentState.SENDING,
            DeliverySegmentState.UNKNOWN,
        ),
    )
    return segment, payload


def _load_segments(connection: Any, job: TurnJobRecord) -> list[tuple[DeliverySegmentRecord, TransientPayloadRecord | None]]:
    rows = connection.execute(
        _segment_select() + " WHERE job_id = ? ORDER BY sequence", (job.job_id,)
    ).fetchall()
    result = []
    for expected, row in enumerate(rows, 1):
        segment, payload = _materialize_segment(connection, row, job=job)
        if segment.sequence != expected:
            raise _invariant()
        result.append((segment, payload))
    return result


def _job_with_state(job: TurnJobRecord, state: TurnJobState, version: int, updated: int,
                    error_class: str | None) -> TurnJobRecord:
    return TurnJobRecord(
        job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
        job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
        job.reasoning_effort, job.input_sha256, job.codex_turn_id, state, version,
        job.created_at_ms, updated, error_class,
    )


def _validate_delivery_job_shape(job: TurnJobRecord) -> None:
    if job.state in (TurnJobState.DELIVERY_PENDING, TurnJobState.DELIVERING, TurnJobState.DELIVERED):
        if job.thread_id is None or job.codex_turn_id is None or job.error_class is not None:
            raise _invariant()
    elif job.state is TurnJobState.DELIVERY_UNKNOWN:
        if job.thread_id is None or job.codex_turn_id is None or job.error_class is None:
            raise _invariant()


def _validate_delivery_dialogue(connection: Any, job: TurnJobRecord) -> None:
    row = _dialogue_row(connection, job.dialogue_id)
    if row is None:
        raise _invariant()
    dialogue = _materialize_dialogue(row)
    if (
        dialogue.state.value != "IDLE"
        or dialogue.server_id != job.server_id
        or dialogue.profile_id != job.profile_id
        or dialogue.thread_id != job.thread_id
    ):
        raise _invariant()


def _validate_delivery_coherence(
    connection: Any,
    job: TurnJobRecord,
    segments: list[tuple[DeliverySegmentRecord, TransientPayloadRecord | None]],
) -> None:
    """Validate the durable job phase against its complete delivery plan."""
    states = [segment.state for segment, _ in segments]
    delivery_states = (
        TurnJobState.DELIVERY_PENDING,
        TurnJobState.DELIVERING,
        TurnJobState.DELIVERED,
        TurnJobState.DELIVERY_UNKNOWN,
    )
    if not segments:
        if job.state in delivery_states:
            raise _invariant()
        return

    if job.state not in delivery_states and job.state is not TurnJobState.FAILED:
        raise _invariant()
    _validate_delivery_dialogue(connection, job)

    if job.state is TurnJobState.DELIVERY_PENDING:
        if any(state is not DeliverySegmentState.PENDING for state in states):
            raise _invariant()
        return
    if job.state is TurnJobState.DELIVERED:
        if any(state is not DeliverySegmentState.CONFIRMED for state in states):
            raise _invariant()
        return
    if job.state is TurnJobState.DELIVERY_UNKNOWN:
        if DeliverySegmentState.UNKNOWN not in states or any(
            state in (DeliverySegmentState.SENDING, DeliverySegmentState.FAILED)
            for state in states
        ):
            raise _invariant()
        return
    if job.state is TurnJobState.FAILED:
        if job.codex_turn_id is None or states.count(DeliverySegmentState.FAILED) != 1 or any(
            state in (DeliverySegmentState.SENDING, DeliverySegmentState.UNKNOWN)
            for state in states
        ):
            raise _invariant()
        return

    # DELIVERING is C* (S)? P*. A confirmed segment can never follow work
    # that is still pending or being sent, and there is at most one SENDING.
    if DeliverySegmentState.UNKNOWN in states or DeliverySegmentState.FAILED in states:
        raise _invariant()
    sending_count = states.count(DeliverySegmentState.SENDING)
    if sending_count > 1 or all(state is DeliverySegmentState.CONFIRMED for state in states):
        raise _invariant()
    phase = "CONFIRMED"
    for state in states:
        if phase == "CONFIRMED":
            if state is DeliverySegmentState.SENDING:
                phase = "SENDING"
            elif state is DeliverySegmentState.PENDING:
                phase = "PENDING"
            elif state is not DeliverySegmentState.CONFIRMED:
                raise _invariant()
        elif phase == "SENDING":
            if state is DeliverySegmentState.PENDING:
                phase = "PENDING"
            else:
                raise _invariant()
        elif state is not DeliverySegmentState.PENDING:
            raise _invariant()
class _RepositoryBase:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class DeliverySegmentRepository(_RepositoryBase):
    async def get(self, job_id: str, sequence: int) -> DeliverySegmentRecord | None:
        job_id = _validate_id(job_id)
        sequence = _validate_nonnegative(sequence)
        if sequence < 1:
            raise _invalid()

        def read(connection: Any) -> DeliverySegmentRecord | None:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                if _segment_row(connection, job_id, sequence) is not None:
                    raise _invariant()
                return None
            job = _materialize_job(job_row)
            segments = _load_segments(connection, job)
            _validate_delivery_coherence(connection, job, segments)
            for segment, _ in segments:
                if segment.sequence == sequence:
                    return segment
            return None

        return await self._storage.read(read)

    async def list_for_job(self, job_id: str) -> tuple[DeliverySegmentRecord, ...]:
        job_id = _validate_id(job_id)

        def read(connection: Any) -> tuple[DeliverySegmentRecord, ...]:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            segments = _load_segments(connection, job)
            _validate_delivery_coherence(connection, job, segments)
            return tuple(segment for segment, _ in segments)

        return await self._storage.read(read)

    async def plan(
        self,
        *,
        job_id: str,
        expected_job_version: int,
        items: list[DeliveryPlanItem] | tuple[DeliveryPlanItem, ...],
    ) -> DeliveryPlanResult:
        job_id = _validate_id(job_id)
        expected_job_version = _validate_nonnegative(expected_job_version)
        if type(items) not in (list, tuple) or not 1 <= len(items) <= 4096:
            raise _invalid()
        validated_items: list[DeliveryPlanItem] = []
        for item in items:
            if not isinstance(item, DeliveryPlanItem):
                raise _invalid()
            operation = _validate_operation(item.operation)
            payload_id = _validate_id(item.payload_id)
            target = _validate_message_id(item.target_message_id, nullable=True)
            if operation is DeliveryOperation.CREATE and target is not None:
                raise _invalid()
            if operation is DeliveryOperation.EDIT and target is None:
                raise _invalid()
            validated_items.append(DeliveryPlanItem(operation, payload_id, target))

        def write(connection: Any) -> DeliveryPlanResult:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            _validate_delivery_job_shape(job)
            if job.version != expected_job_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.CODEX_COMPLETED:
                raise _state_conflict()
            if connection.execute(
                "SELECT 1 FROM delivery_segments WHERE job_id = ? LIMIT 1", (job_id,)
            ).fetchone() is not None:
                raise _state_conflict()
            dialogue_row = _dialogue_row(connection, job.dialogue_id)
            if dialogue_row is None:
                raise _invariant()
            dialogue = _materialize_dialogue(dialogue_row)
            if (
                dialogue.dialogue_id != job.dialogue_id
                or dialogue.state.value != "IDLE"
                or dialogue.server_id != job.server_id
                or dialogue.profile_id != job.profile_id
                or dialogue.thread_id != job.thread_id
            ):
                raise _invariant()
            payloads: list[TransientPayloadRecord] = []
            for item in validated_items:
                row = _payload_row(connection, item.payload_id)
                if row is None:
                    raise _not_found()
                payload = _materialize_payload(connection, row)
                if payload.kind is not TransientPayloadKind.DISPLAY:
                    raise _state_conflict()
                if payload.job_id != job.job_id or payload.dialogue_id != job.dialogue_id:
                    raise _invariant()
                if not _SHA256_RE.fullmatch(payload.content_sha256):
                    raise _invariant()
                payloads.append(payload)
            version = _next_version(job.version)
            now = _validate_clock(self._clock)
            updated = max(now, job.updated_at_ms)
            for sequence, (item, payload) in enumerate(zip(validated_items, payloads), 1):
                connection.execute(
                    "INSERT INTO delivery_segments "
                    "(job_id, sequence, operation, target_message_id, payload_id, payload_sha256, "
                    "state, attempt_count, confirmed_message_id, created_at_ms, updated_at_ms) "
                    "VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, NULL, ?, ?)",
                    (job.job_id, sequence, item.operation.value, item.target_message_id,
                     payload.payload_id, payload.content_sha256, now, now),
                )
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ? "
                "WHERE job_id = ? AND version = ? AND state = ?",
                (TurnJobState.DELIVERY_PENDING.value, version, updated, job.job_id,
                 job.version, TurnJobState.CODEX_COMPLETED.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return DeliveryPlanResult(
                _job_with_state(job, TurnJobState.DELIVERY_PENDING, version, updated, None),
                tuple(DeliverySegmentRecord(
                    job.job_id, sequence, item.operation, item.target_message_id,
                    payload.payload_id, payload.content_sha256, DeliverySegmentState.PENDING,
                    0, None, now, now,
                ) for sequence, (item, payload) in enumerate(zip(validated_items, payloads), 1)),
            )

        return await self._storage.write(write)

    async def claim_next(self, *, job_id: str, expected_job_version: int) -> DeliveryClaimResult:
        job_id = _validate_id(job_id)
        expected_job_version = _validate_nonnegative(expected_job_version)

        def write(connection: Any) -> DeliveryClaimResult:
            row = _job_row(connection, job_id)
            if row is None:
                raise _not_found()
            job = _materialize_job(row)
            _validate_delivery_job_shape(job)
            _validate_delivery_dialogue(connection, job)
            if job.version != expected_job_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state not in (TurnJobState.DELIVERY_PENDING, TurnJobState.DELIVERING):
                raise _state_conflict()
            segments = _load_segments(connection, job)
            _validate_delivery_coherence(connection, job, segments)
            if not segments:
                raise _state_conflict()
            if any(segment.state in (DeliverySegmentState.SENDING,
                                     DeliverySegmentState.UNKNOWN,
                                     DeliverySegmentState.FAILED)
                   for segment, _ in segments):
                raise _state_conflict()
            pending_index = next(
                (index for index, (segment, _) in enumerate(segments)
                 if segment.state is DeliverySegmentState.PENDING), None
            )
            if pending_index is None:
                raise _state_conflict()
            if any(segment.state is not DeliverySegmentState.CONFIRMED
                   for segment, _ in segments[:pending_index]):
                raise _state_conflict()
            segment, payload = segments[pending_index]
            if payload is None:
                raise _invariant()
            if segment.attempt_count != 0:
                raise _invariant()
            version = _next_version(job.version)
            now = _validate_clock(self._clock)
            segment_updated = max(now, segment.updated_at_ms)
            job_updated = max(now, job.updated_at_ms)
            changed = connection.execute(
                "UPDATE delivery_segments SET state = ?, attempt_count = 1, updated_at_ms = ? "
                "WHERE job_id = ? AND sequence = ? AND state = ? AND attempt_count = 0",
                (DeliverySegmentState.SENDING.value, segment_updated, job.job_id,
                 segment.sequence, DeliverySegmentState.PENDING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ? "
                "WHERE job_id = ? AND version = ? AND state IN (?, ?)",
                (TurnJobState.DELIVERING.value, version, job_updated, job.job_id, job.version,
                 TurnJobState.DELIVERY_PENDING.value, TurnJobState.DELIVERING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            sent = DeliverySegmentRecord(
                segment.job_id, segment.sequence, segment.operation, segment.target_message_id,
                segment.payload_id, segment.payload_sha256, DeliverySegmentState.SENDING,
                1, None, segment.created_at_ms, segment_updated,
            )
            return DeliveryClaimResult(
                _job_with_state(job, TurnJobState.DELIVERING, version, job_updated, None), sent, payload,
            )

        return await self._storage.write(write)

    async def finish_sending(
        self,
        *,
        job_id: str,
        sequence: int,
        expected_job_version: int,
        outcome: DeliveryFinishOutcome,
        confirmed_message_id: int | None = None,
        error_class: str | None = None,
    ) -> DeliveryFinishResult:
        job_id = _validate_id(job_id)
        sequence = _validate_nonnegative(sequence)
        if sequence < 1:
            raise _invalid()
        expected_job_version = _validate_nonnegative(expected_job_version)
        outcome = _validate_outcome(outcome)
        if outcome is DeliveryFinishOutcome.CONFIRMED:
            confirmed_message_id = _validate_message_id(confirmed_message_id)
            if error_class is not None:
                raise _invalid()
        else:
            if confirmed_message_id is not None:
                raise _invalid()
            if error_class is None:
                raise _invalid()
            error_class = _validate_error_class(error_class)

        def write(connection: Any) -> DeliveryFinishResult:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            _validate_delivery_job_shape(job)
            _validate_delivery_dialogue(connection, job)
            if job.version != expected_job_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.DELIVERING:
                raise _state_conflict()
            segments = _load_segments(connection, job)
            _validate_delivery_coherence(connection, job, segments)
            row = _segment_row(connection, job.job_id, sequence)
            if row is None:
                raise _not_found()
            segment, _ = _materialize_segment(connection, row, job=job)
            if segment.state is not DeliverySegmentState.SENDING or segment.attempt_count != 1:
                raise _state_conflict()
            assert confirmed_message_id is None or isinstance(confirmed_message_id, int)
            if outcome is DeliveryFinishOutcome.CONFIRMED:
                if confirmed_message_id is None:
                    raise _invalid()
                if segment.operation is DeliveryOperation.EDIT and confirmed_message_id != segment.target_message_id:
                    raise _state_conflict()
                next_segment_state = DeliverySegmentState.CONFIRMED
                next_job_error = None
            elif outcome is DeliveryFinishOutcome.UNKNOWN:
                next_segment_state = DeliverySegmentState.UNKNOWN
                next_job_error = error_class
            else:
                next_segment_state = DeliverySegmentState.FAILED
                next_job_error = error_class
            version = _next_version(job.version)
            now = _validate_clock(self._clock)
            segment_updated = max(now, segment.updated_at_ms)
            job_updated = max(now, job.updated_at_ms)
            changed = connection.execute(
                "UPDATE delivery_segments SET state = ?, confirmed_message_id = ?, updated_at_ms = ? "
                "WHERE job_id = ? AND sequence = ? AND state = ? AND attempt_count = 1",
                (next_segment_state.value, confirmed_message_id, segment_updated, job.job_id,
                 segment.sequence, DeliverySegmentState.SENDING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            if outcome is DeliveryFinishOutcome.CONFIRMED:
                remaining = connection.execute(
                    "SELECT 1 FROM delivery_segments WHERE job_id = ? AND state <> 'CONFIRMED' LIMIT 1",
                    (job.job_id,),
                ).fetchone()
                next_job_state = TurnJobState.DELIVERED if remaining is None else TurnJobState.DELIVERING
            elif outcome is DeliveryFinishOutcome.UNKNOWN:
                next_job_state = TurnJobState.DELIVERY_UNKNOWN
            else:
                next_job_state = TurnJobState.FAILED
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ?, error_class = ? "
                "WHERE job_id = ? AND version = ? AND state = ?",
                (next_job_state.value, version, job_updated, next_job_error, job.job_id,
                 job.version, TurnJobState.DELIVERING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            finished = DeliverySegmentRecord(
                segment.job_id, segment.sequence, segment.operation, segment.target_message_id,
                segment.payload_id, segment.payload_sha256, next_segment_state, 1,
                confirmed_message_id, segment.created_at_ms, segment_updated,
            )
            return DeliveryFinishResult(
                _job_with_state(job, next_job_state, version, job_updated, next_job_error), finished,
            )

        return await self._storage.write(write)
