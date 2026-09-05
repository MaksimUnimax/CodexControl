"""P2.3 repositories for ingress dedupe, control claims, and callback actions."""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Callable
from typing import Any

from codex_control.domain import ControllerMode

from .core_repositories import (
    _default_clock,
    _materialize_controller as _materialize_core_controller,
    _validate_clock as _validate_clock_value,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .idempotency_records import (
    CallbackActionRecord,
    CallbackClaimResult,
    CallbackClaimStatus,
    ControlClaimResult,
    ControlClaimStatus,
    IngressClaimResult,
    IngressDispositionKind,
    IngressUpdateRecord,
)


MAX_SQLITE_INT = 9223372036854775807
MIN_SQLITE_INT = -9223372036854775808

_INGRESS_UPDATE_ID_LENGTH = 128
_ACTION_LENGTH = 128
_SUBJECT_TYPE_LENGTH = 64
_SUBJECT_ID_LENGTH = 128
_EXPECTED_STATE_LENGTH = 64
_DISPOSITION_PREFIX = "JOB:"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_TOKEN_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()
    return value


def _validate_nonsized_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _invalid()
    return value


def _validate_nonneg_int(value: object) -> int:
    value = _validate_nonsized_int(value)
    if not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_chat_id(value: object) -> int:
    value = _validate_nonsized_int(value)
    if not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT or value == 0:
        raise _invalid()
    return value


def _validate_expected_version(value: object) -> int:
    return _validate_nonneg_int(value)


def _validate_disposition(value: object) -> IngressDispositionKind:
    if value is IngressDispositionKind.IGNORED_SLEEP:
        return value
    if value is IngressDispositionKind.IGNORED_UNAUTHORIZED:
        return value
    raise _invalid()


def _validate_controller_mode(value: object) -> ControllerMode:
    if isinstance(value, ControllerMode):
        return value
    raise _invalid()


def _validate_identified(value: object, limit: int) -> str:
    validated = _validate_string(value, limit)
    if validated is None or not _IDENTIFIER_RE.fullmatch(validated):
        raise _invalid()
    return validated


def _validate_subject_id(value: object) -> str:
    return _validate_string(value, _SUBJECT_ID_LENGTH)


def _validate_token_hash(value: object) -> str:
    validated = _validate_string(value, 64)
    if validated is None or not _TOKEN_HASH_RE.fullmatch(validated):
        raise _invalid()
    return validated


def _validate_stored_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invariant()
    return value


def _validate_stored_token_hash(value: object) -> str:
    validated = _validate_stored_string(value, 64)
    if validated is None or not _TOKEN_HASH_RE.fullmatch(validated):
        raise _invariant()
    return validated


def _validate_stored_identified(value: object, limit: int) -> str:
    validated = _validate_stored_string(value, limit)
    if validated is None or not _IDENTIFIER_RE.fullmatch(validated):
        raise _invariant()
    return validated


def _validate_stored_nonneg_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _validate_stored_int64(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _validate_stored_chat_id_row(value: object) -> int:
    value = _validate_stored_int64(value)
    if not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT or value == 0:
        raise _invariant()
    return value


def _materialize_ingress(row: Any) -> IngressUpdateRecord:
    if row is None or len(row) != 4:
        raise _invariant()
    update_id = _validate_stored_nonneg_int(row[0])
    received_at_ms = _validate_stored_nonneg_int(row[1])
    completed_at = None if row[2] is None else _validate_stored_nonneg_int(row[2])
    if completed_at is not None and completed_at < received_at_ms:
        raise _invariant()
    raw_disposition = _validate_stored_string(row[3], len(_DISPOSITION_PREFIX) + _INGRESS_UPDATE_ID_LENGTH)
    assert raw_disposition is not None
    if raw_disposition == IngressDispositionKind.CONTROL.value:
        disposition = IngressDispositionKind.CONTROL
        job_id = None
    elif raw_disposition == IngressDispositionKind.IGNORED_SLEEP.value:
        disposition = IngressDispositionKind.IGNORED_SLEEP
        job_id = None
    elif raw_disposition == IngressDispositionKind.IGNORED_UNAUTHORIZED.value:
        disposition = IngressDispositionKind.IGNORED_UNAUTHORIZED
        job_id = None
    elif raw_disposition.startswith(_DISPOSITION_PREFIX):
        job_id = raw_disposition[len(_DISPOSITION_PREFIX):]
        if not job_id or len(job_id) > _INGRESS_UPDATE_ID_LENGTH:
            raise _invariant()
        if "\x00" in job_id:
            raise _invariant()
        disposition = IngressDispositionKind.JOB
    else:
        raise _invariant()
    return IngressUpdateRecord(update_id, received_at_ms, completed_at, disposition, job_id)


def _materialize_callback(row: Any) -> CallbackActionRecord:
    if row is None or len(row) != 11:
        raise _invariant()
    token_hash_sha256 = _validate_stored_token_hash(row[0])
    action = _validate_stored_identified(row[1], _ACTION_LENGTH)
    subject_type = _validate_stored_identified(row[2], _SUBJECT_TYPE_LENGTH)
    subject_id = _validate_stored_string(row[3], _SUBJECT_ID_LENGTH)
    if not subject_id:
        raise _invariant()
    expected_version = _validate_stored_nonneg_int(row[4])
    expected_state = _validate_stored_identified(row[5], _EXPECTED_STATE_LENGTH)
    authorized_user_id = _validate_stored_nonneg_int(row[6])
    if authorized_user_id < 1:
        raise _invariant()
    authorized_chat_id = _validate_stored_chat_id_row(row[7])
    created_at_ms = _validate_stored_nonneg_int(row[8])
    expires_at_ms = _validate_stored_nonneg_int(row[9])
    if expires_at_ms <= created_at_ms:
        raise _invariant()
    if row[10] is not None:
        consumed_at_ms = _validate_stored_nonneg_int(row[10])
        if consumed_at_ms < created_at_ms or consumed_at_ms > expires_at_ms:
            raise _invariant()
    else:
        consumed_at_ms = None
    return CallbackActionRecord(
        token_hash_sha256=token_hash_sha256,
        action=action,
        subject_type=subject_type,
        subject_id=subject_id,
        expected_version=expected_version,
        expected_state=expected_state,
        authorized_user_id=authorized_user_id,
        authorized_chat_id=authorized_chat_id,
        created_at_ms=created_at_ms,
        expires_at_ms=expires_at_ms,
        consumed_at_ms=consumed_at_ms,
    )


def _one_row(connection: Any, sql: str, parameters: tuple[object, ...]) -> Any:
    return connection.execute(sql, parameters).fetchone()


def _ingress_disposition_text(disposition: IngressDispositionKind) -> str:
    return disposition.value


def _ensure_exact_rowcount(rowcount: int, expected: int) -> None:
    if rowcount != expected:
        raise _invariant()


class _RepositoryBase:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


def _validate_clock(clock: Callable[[], int]) -> int:
    return _validate_clock_value(clock)


class IngressUpdateRepository(_RepositoryBase):
    async def get(self, update_id: int) -> IngressUpdateRecord | None:
        update_id = _validate_nonneg_int(update_id)

        def read(connection: Any) -> IngressUpdateRecord | None:
            row = connection.execute(
                "SELECT update_id, received_at_ms, completed_at_ms, disposition "
                "FROM ingress_updates WHERE update_id = ?",
                (update_id,),
            ).fetchone()
            return None if row is None else _materialize_ingress(row)

        return await self._storage.read(read)

    async def claim_ignored(
        self,
        *,
        update_id: int,
        disposition: IngressDispositionKind,
    ) -> IngressClaimResult:
        update_id = _validate_nonneg_int(update_id)
        disposition = _validate_disposition(disposition)

        def write(connection: Any) -> IngressClaimResult:
            row = _one_row(
                connection,
                "SELECT update_id, received_at_ms, completed_at_ms, disposition "
                "FROM ingress_updates WHERE update_id = ?",
                (update_id,),
            )
            if row is not None:
                return IngressClaimResult(_materialize_ingress(row), True)

            now = _validate_clock(self._clock)
            text = _ingress_disposition_text(disposition)
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES (?, ?, ?, ?)",
                (update_id, now, now, text),
            )
            return IngressClaimResult(
                _materialize_ingress((update_id, now, now, text)),
                False,
            )

        return await self._storage.write(write)


class ControlIngressRepository(_RepositoryBase):
    async def claim_control(
        self,
        *,
        update_id: int,
        control_epoch: int,
        requested_mode: ControllerMode,
    ) -> ControlClaimResult:
        update_id = _validate_nonneg_int(update_id)
        control_epoch = _validate_nonneg_int(control_epoch)
        requested_mode = _validate_controller_mode(requested_mode)

        def write(connection: Any) -> ControlClaimResult:
            row = _one_row(
                connection,
                "SELECT update_id, received_at_ms, completed_at_ms, disposition "
                "FROM ingress_updates WHERE update_id = ?",
                (update_id,),
            )
            if row is not None:
                return ControlClaimResult(
                    status=ControlClaimStatus.DUPLICATE,
                    ingress=_materialize_ingress(row),
                    controller=None,
                )

            controller_row = connection.execute(
                "SELECT singleton, last_control_epoch, requested_mode, boot_generation, "
                "fleet_version, created_at_ms, updated_at_ms FROM controller_runtime"
            ).fetchone()
            if controller_row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            current_controller = _materialize_core_controller(controller_row)

            now = _validate_clock(self._clock)
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES (?, ?, ?, ?)",
                (update_id, now, now, IngressDispositionKind.CONTROL.value),
            )
            ingress = _materialize_ingress((update_id, now, now, IngressDispositionKind.CONTROL.value))

            if control_epoch <= current_controller.last_control_epoch:
                return ControlClaimResult(
                    status=ControlClaimStatus.STALE,
                    ingress=ingress,
                    controller=current_controller,
                )

            updated_at_ms = max(now, current_controller.updated_at_ms)
            updated = connection.execute(
                "UPDATE controller_runtime SET last_control_epoch = ?, requested_mode = ?, updated_at_ms = ? "
                "WHERE singleton = 1 AND last_control_epoch = ?",
                (control_epoch, requested_mode.value, updated_at_ms, current_controller.last_control_epoch),
            ).rowcount

            _ensure_exact_rowcount(updated, 1)
            return ControlClaimResult(
                status=ControlClaimStatus.APPLIED,
                ingress=ingress,
                controller=_materialize_core_controller(
                    (1, control_epoch, requested_mode.value, current_controller.boot_generation,
                     current_controller.fleet_version, current_controller.created_at_ms, updated_at_ms)
                ),
            )

        return await self._storage.write(write)


class CallbackActionRepository(_RepositoryBase):
    async def create(
        self,
        *,
        token_hash_sha256: str,
        action: str,
        subject_type: str,
        subject_id: str,
        expected_version: int,
        expected_state: str,
        authorized_user_id: int,
        authorized_chat_id: int,
        expires_at_ms: int,
    ) -> CallbackActionRecord:
        token_hash_sha256 = _validate_token_hash(token_hash_sha256)
        action = _validate_identified(action, _ACTION_LENGTH)
        subject_type = _validate_identified(subject_type, _SUBJECT_TYPE_LENGTH)
        subject_id = _validate_subject_id(subject_id)
        if not subject_id:
            raise _invalid()
        expected_version = _validate_expected_version(expected_version)
        expected_state = _validate_identified(expected_state, _EXPECTED_STATE_LENGTH)
        authorized_user_id = _validate_nonneg_int(authorized_user_id)
        if authorized_user_id == 0:
            raise _invalid()
        authorized_chat_id = _validate_chat_id(authorized_chat_id)
        expires_at_ms = _validate_nonneg_int(expires_at_ms)

        def write(connection: Any) -> CallbackActionRecord:
            row = _one_row(
                connection,
                "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
                "FROM callback_actions WHERE token_hash_sha256 = ?",
                (token_hash_sha256,),
            )
            if row is not None:
                raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)

            now = _validate_clock(self._clock)
            if expires_at_ms <= now:
                raise _invalid()

            try:
                connection.execute(
                    "INSERT INTO callback_actions"
                    "(token_hash_sha256, action, subject_type, subject_id, expected_version, "
                    "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (
                        token_hash_sha256,
                        action,
                        subject_type,
                        subject_id,
                        expected_version,
                        expected_state,
                        authorized_user_id,
                        authorized_chat_id,
                        now,
                        expires_at_ms,
                    ),
                )
            except sqlite3.IntegrityError:
                raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)

            return CallbackActionRecord(
                token_hash_sha256=token_hash_sha256,
                action=action,
                subject_type=subject_type,
                subject_id=subject_id,
                expected_version=expected_version,
                expected_state=expected_state,
                authorized_user_id=authorized_user_id,
                authorized_chat_id=authorized_chat_id,
                created_at_ms=now,
                expires_at_ms=expires_at_ms,
                consumed_at_ms=None,
            )

        return await self._storage.write(write)

    async def claim(
        self,
        *,
        token_hash_sha256: str,
        authorized_user_id: int,
        authorized_chat_id: int,
    ) -> CallbackClaimResult:
        token_hash_sha256 = _validate_token_hash(token_hash_sha256)
        authorized_user_id = _validate_nonneg_int(authorized_user_id)
        if authorized_user_id == 0:
            raise _invalid()
        authorized_chat_id = _validate_chat_id(authorized_chat_id)

        def write(connection: Any) -> CallbackClaimResult:
            row = _one_row(
                connection,
                "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
                "FROM callback_actions WHERE token_hash_sha256 = ?",
                (token_hash_sha256,),
            )
            if row is None:
                return CallbackClaimResult(status=CallbackClaimStatus.NOT_FOUND, record=None)

            action = _materialize_callback(row)
            if action.authorized_user_id != authorized_user_id or action.authorized_chat_id != authorized_chat_id:
                return CallbackClaimResult(status=CallbackClaimStatus.UNAUTHORIZED, record=None)
            if action.consumed_at_ms is not None:
                return CallbackClaimResult(status=CallbackClaimStatus.ALREADY_CONSUMED, record=None)

            now = _validate_clock(self._clock)
            effective_now = max(now, action.created_at_ms)

            if effective_now >= action.expires_at_ms:
                changed = connection.execute(
                    "UPDATE callback_actions SET consumed_at_ms = ? "
                    "WHERE token_hash_sha256 = ? AND consumed_at_ms IS NULL",
                    (action.expires_at_ms, token_hash_sha256),
                ).rowcount
                _ensure_exact_rowcount(changed, 1)
                return CallbackClaimResult(status=CallbackClaimStatus.EXPIRED, record=None)

            consumed_at = effective_now
            changed = connection.execute(
                "UPDATE callback_actions SET consumed_at_ms = ? "
                "WHERE token_hash_sha256 = ? AND consumed_at_ms IS NULL",
                (consumed_at, token_hash_sha256),
            ).rowcount
            _ensure_exact_rowcount(changed, 1)
            return CallbackClaimResult(
                status=CallbackClaimStatus.CLAIMED,
                record=CallbackActionRecord(
                    action.token_hash_sha256,
                    action.action,
                    action.subject_type,
                    action.subject_id,
                    action.expected_version,
                    action.expected_state,
                    action.authorized_user_id,
                    action.authorized_chat_id,
                    action.created_at_ms,
                    action.expires_at_ms,
                    consumed_at,
                ),
            )

        return await self._storage.write(write)
