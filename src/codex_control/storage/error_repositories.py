"""P2.5 sanitized error-fingerprint repository."""

from __future__ import annotations

import re
from typing import Any

from .core_repositories import (
    MAX_SQLITE_INT,
    _RepositoryBase,
    _materialize_dialogue,
    _validate_clock,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .records import DialogueRecord
from .sqlite import SqliteStorage
from .turn_job_repositories import _dialogue_row, _job_row, _materialize_job
from .error_records import ErrorFingerprintRecord


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


def _validate_optional_id(value: object) -> str | None:
    return None if value is None else _validate_id(value)


def _validate_fingerprint(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _validate_error_class(value: object) -> str:
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _stored_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > _ID_LENGTH:
        raise _invariant()
    return value


def _stored_nonnegative(value: object, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _stored_fingerprint(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _stored_error_class(value: object) -> str:
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _dialogue_for_reference(connection: Any, dialogue_id: str) -> DialogueRecord:
    row = _dialogue_row(connection, dialogue_id)
    if row is None:
        raise _not_found()
    return _materialize_dialogue(row)


def _validate_entity_references(
    connection: Any, dialogue_id: str | None, job_id: str | None
) -> None:
    dialogue: DialogueRecord | None = None
    if dialogue_id is not None:
        dialogue = _dialogue_for_reference(connection, dialogue_id)
    if job_id is not None:
        row = _job_row(connection, job_id)
        if row is None:
            raise _not_found()
        job = _materialize_job(row)
        _dialogue_for_reference(connection, job.dialogue_id)
        if dialogue is not None and job.dialogue_id != dialogue.dialogue_id:
            raise _state_conflict()


def _validate_stored_entity_references(
    connection: Any, dialogue_id: str | None, job_id: str | None
) -> None:
    try:
        _validate_entity_references(connection, dialogue_id, job_id)
    except RepositoryError:
        raise _invariant() from None


def _materialize_error(connection: Any, row: Any) -> ErrorFingerprintRecord:
    if row is None or len(row) != 7:
        raise _invariant()
    fingerprint = _stored_fingerprint(row[0])
    error_class = _stored_error_class(row[1])
    count = _stored_nonnegative(row[2], minimum=1)
    first_seen = _stored_nonnegative(row[3])
    last_seen = _stored_nonnegative(row[4])
    if last_seen < first_seen:
        raise _invariant()
    dialogue_id = _stored_id(row[5])
    job_id = _stored_id(row[6])
    _validate_stored_entity_references(connection, dialogue_id, job_id)
    return ErrorFingerprintRecord(
        fingerprint, error_class, count, first_seen, last_seen, dialogue_id, job_id
    )


def _error_select() -> str:
    return (
        "SELECT fingerprint_sha256, error_class, count, first_seen_at_ms, "
        "last_seen_at_ms, dialogue_id, job_id FROM errors"
    )


class ErrorFingerprintRepository(_RepositoryBase):
    async def get(self, fingerprint_sha256: str) -> ErrorFingerprintRecord | None:
        fingerprint_sha256 = _validate_fingerprint(fingerprint_sha256)

        def read(connection: Any) -> ErrorFingerprintRecord | None:
            row = connection.execute(
                _error_select() + " WHERE lower(fingerprint_sha256) = ?", (fingerprint_sha256,)
            ).fetchone()
            return None if row is None else _materialize_error(connection, row)

        return await self._storage.read(read)

    async def record(
        self, *, fingerprint_sha256: str, error_class: str,
        dialogue_id: str | None = None, job_id: str | None = None,
    ) -> ErrorFingerprintRecord:
        fingerprint_sha256 = _validate_fingerprint(fingerprint_sha256)
        error_class = _validate_error_class(error_class)
        dialogue_id = _validate_optional_id(dialogue_id)
        job_id = _validate_optional_id(job_id)

        def write(connection: Any) -> ErrorFingerprintRecord:
            _validate_entity_references(connection, dialogue_id, job_id)
            row = connection.execute(
                _error_select() + " WHERE lower(fingerprint_sha256) = ?", (fingerprint_sha256,)
            ).fetchone()
            if row is None:
                now = _validate_clock(self._clock)
                connection.execute(
                    "INSERT INTO errors "
                    "(fingerprint_sha256, error_class, count, first_seen_at_ms, last_seen_at_ms, dialogue_id, job_id) "
                    "VALUES (?, ?, 1, ?, ?, ?, ?)",
                    (fingerprint_sha256, error_class, now, now, dialogue_id, job_id),
                )
                return ErrorFingerprintRecord(
                    fingerprint_sha256, error_class, 1, now, now, dialogue_id, job_id
                )

            existing = _materialize_error(connection, row)
            if (
                existing.error_class != error_class
                or existing.dialogue_id != dialogue_id
                or existing.job_id != job_id
            ):
                raise _invariant()
            if existing.count >= MAX_SQLITE_INT:
                raise _invariant()
            now = _validate_clock(self._clock)
            last_seen = max(now, existing.last_seen_at_ms)
            changed = connection.execute(
                "UPDATE errors SET count = ?, last_seen_at_ms = ? "
                "WHERE fingerprint_sha256 = ? AND count = ?",
                (
                    existing.count + 1, last_seen, fingerprint_sha256, existing.count,
                ),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return ErrorFingerprintRecord(
                existing.fingerprint_sha256, existing.error_class, existing.count + 1,
                existing.first_seen_at_ms, last_seen, existing.dialogue_id, existing.job_id,
            )

        return await self._storage.write(write)
