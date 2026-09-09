"""P2.5 durable hard-delete claims, tombstones and local finalization."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .approval_repositories import _approval_select, _materialize_approval
from .core_repositories import (
    MAX_SQLITE_INT,
    _RepositoryBase,
    _default_clock,
    _materialize_dialogue,
    _next_version,
    _validate_clock,
)
from .delivery_records import DeliverySegmentState
from .delivery_repositories import _load_segments
from .deletion_records import DeletionFinalizeResult, DeletionTombstoneRecord
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .records import DialogueRecord, DialogueState
from .sqlite import SqliteStorage
from .turn_job_records import TurnJobState
from .turn_job_repositories import (
    _dialogue_row,
    _job_select,
    _materialize_job,
)


_ID_LENGTH = 128
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ERROR_CLASS_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _error(category: RepositoryErrorCategory) -> RepositoryError:
    return RepositoryError(category)


def _invalid() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVALID_ARGUMENT)


def _not_found() -> RepositoryError:
    return _error(RepositoryErrorCategory.NOT_FOUND)


def _state_conflict() -> RepositoryError:
    return _error(RepositoryErrorCategory.STATE_CONFLICT)


def _invariant() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_id(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invalid()
    return value


def _validate_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_error_class(value: object) -> str:
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _stored_id(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invariant()
    return value


def _stored_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _stored_sha(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _tombstone_select() -> str:
    return (
        "SELECT dialogue_id, thread_identity_sha256, stale_generation, "
        "deleted_at_ms, expires_at_ms FROM deletion_tombstones"
    )


def _materialize_tombstone(row: Any) -> DeletionTombstoneRecord:
    if row is None or len(row) != 5:
        raise _invariant()
    dialogue_id = _stored_id(row[0])
    thread_hash = _stored_sha(row[1])
    stale_generation = _stored_nonnegative(row[2])
    deleted_at_ms = _stored_nonnegative(row[3])
    expires_at_ms = _stored_nonnegative(row[4])
    if expires_at_ms <= deleted_at_ms:
        raise _invariant()
    return DeletionTombstoneRecord(
        dialogue_id, thread_hash, stale_generation, deleted_at_ms, expires_at_ms
    )


def _dialogue_from_row(row: Any) -> DialogueRecord:
    if row is None:
        raise _not_found()
    return _materialize_dialogue(row)


def _validate_job_binding(dialogue: DialogueRecord, job: Any) -> None:
    if (
        job.dialogue_id != dialogue.dialogue_id
        or job.server_id != dialogue.server_id
        or job.profile_id != dialogue.profile_id
        or job.thread_id != dialogue.thread_id
    ):
        raise _invariant()


def _ensure_no_tombstone(connection: Any, dialogue_id: str) -> None:
    if connection.execute(
        "SELECT 1 FROM deletion_tombstones WHERE dialogue_id = ?", (dialogue_id,)
    ).fetchone() is not None:
        raise _invariant()


def _is_exact_delivery_failure_pattern(states: list[DeliverySegmentState]) -> bool:
    if not states or states.count(DeliverySegmentState.FAILED) != 1:
        return False
    failed_index = states.index(DeliverySegmentState.FAILED)
    return (
        all(state is DeliverySegmentState.CONFIRMED for state in states[:failed_index])
        and all(state is DeliverySegmentState.PENDING for state in states[failed_index + 1:])
    )


def _check_delete_readiness(connection: Any, dialogue: DialogueRecord) -> tuple[Any, ...]:
    rows = connection.execute(
        _job_select() + " WHERE dialogue_id = ? ORDER BY job_id", (dialogue.dialogue_id,)
    ).fetchall()
    jobs = []
    for row in rows:
        job = _materialize_job(row)
        if job.state not in (TurnJobState.DELIVERED, TurnJobState.FAILED):
            raise _state_conflict()
        _validate_job_binding(dialogue, job)
        segments = _load_segments(connection, job)
        states = [segment.state for segment, _ in segments]
        if job.state is TurnJobState.DELIVERED:
            if not segments or any(state is not DeliverySegmentState.CONFIRMED for state in states):
                raise _invariant()
        elif segments:
            if job.codex_turn_id is None or not _is_exact_delivery_failure_pattern(states):
                raise _invariant()
        jobs.append(job)

    approval_rows = connection.execute(
        _approval_select()
        + " WHERE job_id IN (SELECT job_id FROM turn_jobs WHERE dialogue_id = ?) ORDER BY approval_id",
        (dialogue.dialogue_id,),
    ).fetchall()
    for row in approval_rows:
        approval = _materialize_approval(connection, row)
        if approval.state.value == "PENDING":
            raise _state_conflict()
    return tuple(jobs)


def _dialogue_for_update(connection: Any, dialogue_id: str) -> DialogueRecord:
    return _dialogue_from_row(_dialogue_row(connection, dialogue_id))


def _record_dialogue(
    current: DialogueRecord,
    *,
    state: DialogueState,
    version: int,
    updated_at_ms: int,
    last_error_class: str | None,
) -> DialogueRecord:
    return DialogueRecord(
        current.dialogue_id, current.server_id, current.profile_id, current.thread_id,
        state, version, current.created_at_ms, updated_at_ms, last_error_class,
    )


class DeletionRepository(_RepositoryBase):
    async def get_tombstone(self, dialogue_id: str) -> DeletionTombstoneRecord | None:
        dialogue_id = _validate_id(dialogue_id)

        def read(connection: Any) -> DeletionTombstoneRecord | None:
            row = connection.execute(
                _tombstone_select() + " WHERE dialogue_id = ?", (dialogue_id,)
            ).fetchone()
            return None if row is None else _materialize_tombstone(row)

        return await self._storage.read(read)

    async def claim_delete_intent(
        self, *, dialogue_id: str, expected_version: int
    ) -> DialogueRecord:
        dialogue_id = _validate_id(dialogue_id)
        expected_version = _validate_nonnegative(expected_version)

        def write(connection: Any) -> DialogueRecord:
            current = _dialogue_for_update(connection, dialogue_id)
            _ensure_no_tombstone(connection, dialogue_id)
            if current.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.IDLE or current.thread_id is None:
                raise _state_conflict()
            _check_delete_readiness(connection, current)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, "
                "last_error_class = NULL WHERE dialogue_id = ? AND version = ? AND state = ?",
                (
                    DialogueState.DELETE_PENDING.value, version, updated,
                    dialogue_id, expected_version, DialogueState.IDLE.value,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return _record_dialogue(
                current, state=DialogueState.DELETE_PENDING, version=version,
                updated_at_ms=updated, last_error_class=None,
            )

        return await self._storage.write(write)

    async def claim_deleting(
        self, *, dialogue_id: str, expected_version: int
    ) -> DialogueRecord:
        dialogue_id = _validate_id(dialogue_id)
        expected_version = _validate_nonnegative(expected_version)

        def write(connection: Any) -> DialogueRecord:
            current = _dialogue_for_update(connection, dialogue_id)
            _ensure_no_tombstone(connection, dialogue_id)
            if current.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.DELETE_PENDING or current.thread_id is None:
                raise _state_conflict()
            _check_delete_readiness(connection, current)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, "
                "last_error_class = NULL WHERE dialogue_id = ? AND version = ? AND state = ?",
                (
                    DialogueState.DELETING.value, version, updated,
                    dialogue_id, expected_version, DialogueState.DELETE_PENDING.value,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return _record_dialogue(
                current, state=DialogueState.DELETING, version=version,
                updated_at_ms=updated, last_error_class=None,
            )

        return await self._storage.write(write)

    async def mark_delete_unknown(
        self, *, dialogue_id: str, expected_version: int, error_class: str
    ) -> DialogueRecord:
        return await self._mark_delete_outcome(
            dialogue_id=dialogue_id, expected_version=expected_version,
            error_class=error_class, state=DialogueState.DELETE_UNKNOWN,
        )

    async def mark_delete_error(
        self, *, dialogue_id: str, expected_version: int, error_class: str
    ) -> DialogueRecord:
        return await self._mark_delete_outcome(
            dialogue_id=dialogue_id, expected_version=expected_version,
            error_class=error_class, state=DialogueState.ERROR,
        )

    async def mark_delete_confirmed_pending_storage(
        self, *, dialogue_id: str, expected_version: int
    ) -> DialogueRecord:
        dialogue_id = _validate_id(dialogue_id)
        expected_version = _validate_nonnegative(expected_version)

        def write(connection: Any) -> DialogueRecord:
            current = _dialogue_for_update(connection, dialogue_id)
            _ensure_no_tombstone(connection, dialogue_id)
            if current.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.DELETING or current.thread_id is None:
                raise _state_conflict()
            _check_delete_readiness(connection, current)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, "
                "last_error_class = NULL WHERE dialogue_id = ? AND version = ? AND state = ?",
                (
                    DialogueState.DELETE_CONFIRMED_PENDING_STORAGE.value, version, updated,
                    dialogue_id, expected_version, DialogueState.DELETING.value,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return _record_dialogue(
                current, state=DialogueState.DELETE_CONFIRMED_PENDING_STORAGE,
                version=version, updated_at_ms=updated, last_error_class=None,
            )

        return await self._storage.write(write)

    async def _mark_delete_outcome(
        self, *, dialogue_id: str, expected_version: int,
        error_class: str, state: DialogueState,
    ) -> DialogueRecord:
        dialogue_id = _validate_id(dialogue_id)
        expected_version = _validate_nonnegative(expected_version)
        error_class = _validate_error_class(error_class)

        def write(connection: Any) -> DialogueRecord:
            current = _dialogue_for_update(connection, dialogue_id)
            if current.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.DELETING or current.thread_id is None:
                raise _state_conflict()
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, "
                "last_error_class = ? WHERE dialogue_id = ? AND version = ? AND state = ?",
                (
                    state.value, version, updated, error_class,
                    dialogue_id, expected_version, DialogueState.DELETING.value,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return _record_dialogue(
                current, state=state, version=version,
                updated_at_ms=updated, last_error_class=error_class,
            )

        return await self._storage.write(write)

    async def finalize_confirmed(
        self, *, dialogue_id: str, expected_version: int,
        tombstone_expires_at_ms: int,
    ) -> DeletionFinalizeResult:
        dialogue_id = _validate_id(dialogue_id)
        expected_version = _validate_nonnegative(expected_version)
        tombstone_expires_at_ms = _validate_nonnegative(tombstone_expires_at_ms)

        def write(connection: Any) -> DeletionFinalizeResult:
            current = _dialogue_for_update(connection, dialogue_id)
            if current.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.DELETE_CONFIRMED_PENDING_STORAGE:
                raise _state_conflict()
            if current.thread_id is None:
                raise _invariant()
            jobs = _check_delete_readiness(connection, current)
            collision = connection.execute(
                "SELECT 1 FROM deletion_tombstones WHERE dialogue_id = ?", (dialogue_id,)
            ).fetchone()
            if collision is not None:
                raise _invariant()

            now = _validate_clock(self._clock)
            deleted_at_ms = max(now, current.updated_at_ms)
            if tombstone_expires_at_ms <= deleted_at_ms:
                raise _invalid()
            thread_hash = hashlib.sha256(current.thread_id.encode("utf-8")).hexdigest()
            tombstone = DeletionTombstoneRecord(
                dialogue_id, thread_hash, current.version, deleted_at_ms,
                tombstone_expires_at_ms,
            )

            job_count = len(jobs)
            payload_count = connection.execute(
                "SELECT COUNT(*) FROM transient_payloads WHERE dialogue_id = ? "
                "OR job_id IN (SELECT job_id FROM turn_jobs WHERE dialogue_id = ?)",
                (dialogue_id, dialogue_id),
            ).fetchone()[0]
            segment_count = connection.execute(
                "SELECT COUNT(*) FROM delivery_segments WHERE job_id IN "
                "(SELECT job_id FROM turn_jobs WHERE dialogue_id = ?)",
                (dialogue_id,),
            ).fetchone()[0]
            approval_count = connection.execute(
                "SELECT COUNT(*) FROM approvals WHERE job_id IN "
                "(SELECT job_id FROM turn_jobs WHERE dialogue_id = ?)",
                (dialogue_id,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO deletion_tombstones "
                "(dialogue_id, thread_identity_sha256, stale_generation, deleted_at_ms, expires_at_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    tombstone.dialogue_id, tombstone.thread_identity_sha256,
                    tombstone.stale_generation, tombstone.deleted_at_ms,
                    tombstone.expires_at_ms,
                ),
            )
            changed = connection.execute(
                "DELETE FROM dialogues WHERE dialogue_id = ? AND version = ? AND state = ?",
                (
                    dialogue_id, expected_version,
                    DialogueState.DELETE_CONFIRMED_PENDING_STORAGE.value,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return DeletionFinalizeResult(
                tombstone, job_count, payload_count, segment_count, approval_count
            )

        return await self._storage.write(write)
