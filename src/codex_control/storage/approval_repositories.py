"""P2.4b durable approvals and atomic approval callback subject claims."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from codex_control.adapters.codex.approvals import ApprovalKind

from .approval_records import (
    ApprovalCallbackClaimResult,
    ApprovalCallbackClaimStatus,
    ApprovalRecord,
    ApprovalState,
)
from .core_repositories import _default_clock, _materialize_dialogue, _validate_clock
from .idempotency_repositories import _materialize_callback
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .transient_payloads import TransientPayloadKind
from .turn_job_records import TurnJobState
from .turn_job_repositories import (
    MAX_SQLITE_INT,
    MIN_SQLITE_INT,
    _dialogue_row,
    _job_row,
    _materialize_job,
    _materialize_payload,
    _payload_row,
)


_ID_LENGTH = 128
_WIRE_TEXT_LENGTH = 256


def _error(category: RepositoryErrorCategory) -> RepositoryError:
    return RepositoryError(category)


def _invalid() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVALID_ARGUMENT)


def _not_found() -> RepositoryError:
    return _error(RepositoryErrorCategory.NOT_FOUND)


def _invariant() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_id(value: object, limit: int = _ID_LENGTH) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()
    return value


def _validate_optional_id(value: object) -> str | None:
    if value is None:
        return None
    return _validate_id(value)


def _validate_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_wire_id(value: object) -> tuple[str, int | str]:
    if isinstance(value, bool):
        raise _invalid()
    if isinstance(value, int):
        if not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT:
            raise _invalid()
        return "INTEGER", value
    if isinstance(value, str) and value and "\x00" not in value and len(value) <= _WIRE_TEXT_LENGTH:
        return "STRING", value
    raise _invalid()


def _validate_kind(value: object) -> ApprovalKind:
    if not isinstance(value, ApprovalKind):
        raise _invalid()
    return value


def _validate_state(value: object) -> ApprovalState:
    if not isinstance(value, str):
        raise _invariant()
    try:
        return ApprovalState(value)
    except (TypeError, ValueError):
        raise _invariant() from None


def _stored_id(value: object, limit: int = _ID_LENGTH, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invariant()
    return value


def _stored_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _stored_int64(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _approval_select() -> str:
    return (
        "SELECT approval_id, profile_id, wire_request_id_type, wire_request_id_int, "
        "wire_request_id_text, job_id, kind, display_payload_id, state, created_at_ms, "
        "updated_at_ms, expires_at_ms FROM approvals"
    )


def _approval_row(connection: Any, approval_id: str) -> Any:
    return connection.execute(_approval_select() + " WHERE approval_id = ?", (approval_id,)).fetchone()


def _validate_approval_display(connection: Any, row: Any, *, job_id: str, dialogue_id: str) -> None:
    if row is None:
        raise _invariant()
    payload = _materialize_payload(connection, row)
    if (
        payload.kind is not TransientPayloadKind.APPROVAL
        or payload.job_id != job_id
        or payload.dialogue_id != dialogue_id
    ):
        raise _invariant()


def _materialize_approval(connection: Any, row: Any) -> ApprovalRecord:
    if row is None or len(row) != 12:
        raise _invariant()
    approval_id = _stored_id(row[0])
    profile_id = _stored_id(row[1])
    wire_type = row[2]
    if wire_type == "INTEGER":
        if row[4] is not None:
            raise _invariant()
        wire_request_id: int | str = _stored_int64(row[3])
    elif wire_type == "STRING":
        if row[3] is not None:
            raise _invariant()
        wire_request_id = _stored_id(row[4], _WIRE_TEXT_LENGTH)
        assert wire_request_id is not None
    else:
        raise _invariant()
    job_id = _stored_id(row[5])
    kind_value = row[6]
    if not isinstance(kind_value, str):
        raise _invariant()
    try:
        kind = ApprovalKind(kind_value)
    except (TypeError, ValueError):
        raise _invariant() from None
    display_payload_id = _stored_id(row[7], nullable=True)
    state = _validate_state(row[8])
    created_at_ms = _stored_nonnegative(row[9])
    updated_at_ms = _stored_nonnegative(row[10])
    expires_at_ms = _stored_nonnegative(row[11])
    if updated_at_ms < created_at_ms or expires_at_ms <= created_at_ms:
        raise _invariant()
    if state is ApprovalState.PENDING:
        if wire_type == "INTEGER":
            live_count = connection.execute(
                "SELECT COUNT(*) FROM approvals "
                "WHERE profile_id = ? AND wire_request_id_type = 'INTEGER' "
                "AND wire_request_id_int = ? AND state = 'PENDING'",
                (profile_id, wire_request_id),
            ).fetchone()[0]
        else:
            live_count = connection.execute(
                "SELECT COUNT(*) FROM approvals "
                "WHERE profile_id = ? AND wire_request_id_type = 'STRING' "
                "AND wire_request_id_text = ? AND state = 'PENDING'",
                (profile_id, wire_request_id),
            ).fetchone()[0]
        if live_count != 1:
            raise _invariant()
    assert approval_id is not None and profile_id is not None and job_id is not None
    job_row = _job_row(connection, job_id)
    if job_row is None:
        raise _invariant()
    job = _materialize_job(job_row)
    if job.profile_id != profile_id:
        raise _invariant()
    dialogue_row = _dialogue_row(connection, job.dialogue_id)
    if dialogue_row is None:
        raise _invariant()
    dialogue = _materialize_dialogue(dialogue_row)
    if display_payload_id is not None:
        _validate_approval_display(
            connection, _payload_row(connection, display_payload_id),
            job_id=job.job_id, dialogue_id=dialogue.dialogue_id,
        )
    return ApprovalRecord(
        approval_id, profile_id, wire_request_id, kind, job_id, display_payload_id,
        state, created_at_ms, updated_at_ms, expires_at_ms,
    )


def _callback_row(connection: Any, token_hash: str) -> Any:
    return connection.execute(
        "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
        "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
        "FROM callback_actions WHERE token_hash_sha256 = ?", (token_hash,)
    ).fetchone()


def _consume_callback(connection: Any, token_hash: str, consumed_at_ms: int) -> None:
    changed = connection.execute(
        "UPDATE callback_actions SET consumed_at_ms = ? "
        "WHERE token_hash_sha256 = ? AND consumed_at_ms IS NULL",
        (consumed_at_ms, token_hash),
    ).rowcount
    if changed != 1:
        raise _invariant()


class _RepositoryBase:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class ApprovalRepository(_RepositoryBase):
    async def get(self, approval_id: str) -> ApprovalRecord | None:
        approval_id = _validate_id(approval_id)

        def read(connection: Any) -> ApprovalRecord | None:
            row = _approval_row(connection, approval_id)
            return None if row is None else _materialize_approval(connection, row)

        return await self._storage.read(read)

    async def create_pending(
        self,
        *,
        approval_id: str,
        profile_id: str,
        wire_request_id: str | int,
        kind: ApprovalKind,
        job_id: str,
        expected_job_version: int,
        display_payload_id: str | None = None,
        expires_at_ms: int,
    ) -> ApprovalRecord:
        approval_id = _validate_id(approval_id)
        profile_id = _validate_id(profile_id)
        wire_type, wire_value = _validate_wire_id(wire_request_id)
        kind = _validate_kind(kind)
        job_id = _validate_id(job_id)
        expected_job_version = _validate_nonnegative(expected_job_version)
        display_payload_id = _validate_optional_id(display_payload_id)
        expires_at_ms = _validate_nonnegative(expires_at_ms)

        def write(connection: Any) -> ApprovalRecord:
            if _approval_row(connection, approval_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if job.version != expected_job_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.CODEX_RUNNING:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if job.profile_id != profile_id:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            dialogue_row = _dialogue_row(connection, job.dialogue_id)
            if dialogue_row is None:
                raise _invariant()
            dialogue = _materialize_dialogue(dialogue_row)
            if dialogue.state.value != "TURN_RUNNING" or dialogue.profile_id != profile_id:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if display_payload_id is not None:
                payload_row = _payload_row(connection, display_payload_id)
                if payload_row is None:
                    raise _not_found()
                # First establish that the persisted payload is canonical. A
                # canonical payload selected with the wrong kind or owner is a
                # caller state conflict; corrupt payload bytes/hash/ownership
                # remain invariant failures from materialization.
                payload = _materialize_payload(connection, payload_row)
                if (
                    payload.kind is not TransientPayloadKind.APPROVAL
                    or payload.job_id != job.job_id
                    or payload.dialogue_id != dialogue.dialogue_id
                ):
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if wire_type == "INTEGER":
                rows = connection.execute(
                    _approval_select() + " WHERE profile_id = ? AND wire_request_id_type = 'INTEGER' "
                    "AND wire_request_id_int = ?",
                    (profile_id, wire_value),
                ).fetchall()
            else:
                rows = connection.execute(
                    _approval_select() + " WHERE profile_id = ? AND wire_request_id_type = 'STRING' "
                    "AND wire_request_id_text = ?",
                    (profile_id, wire_value),
                ).fetchall()
            for existing_row in rows:
                existing = _materialize_approval(connection, existing_row)
                if existing.state is ApprovalState.PENDING:
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            now = _validate_clock(self._clock)
            if expires_at_ms <= now:
                raise _invalid()
            values = (
                approval_id, profile_id, wire_type,
                wire_value if wire_type == "INTEGER" else None,
                wire_value if wire_type == "STRING" else None,
                job.job_id, kind.value, display_payload_id, ApprovalState.PENDING.value,
                now, now, expires_at_ms,
            )
            try:
                connection.execute(
                    "INSERT INTO approvals "
                    "(approval_id, profile_id, wire_request_id_type, wire_request_id_int, "
                    "wire_request_id_text, job_id, kind, display_payload_id, state, created_at_ms, "
                    "updated_at_ms, expires_at_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", values,
                )
            except sqlite3.IntegrityError:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS) from None
            return ApprovalRecord(
                approval_id, profile_id, wire_request_id, kind, job.job_id, display_payload_id,
                ApprovalState.PENDING, now, now, expires_at_ms,
            )

        return await self._storage.write(write)

    async def claim_callback(
        self,
        *,
        token_hash_sha256: str,
        authorized_user_id: int,
        authorized_chat_id: int,
    ) -> ApprovalCallbackClaimResult:
        # Hash and caller identity validation intentionally occurs before SQL.
        if not isinstance(token_hash_sha256, str) or len(token_hash_sha256) != 64:
            raise _invalid()
        if any(character not in "0123456789abcdef" for character in token_hash_sha256):
            raise _invalid()
        authorized_user_id = _validate_nonnegative(authorized_user_id)
        if authorized_user_id == 0:
            raise _invalid()
        if isinstance(authorized_chat_id, bool) or not isinstance(authorized_chat_id, int) \
                or not -9223372036854775808 <= authorized_chat_id <= MAX_SQLITE_INT \
                or authorized_chat_id == 0:
            raise _invalid()

        def write(connection: Any) -> ApprovalCallbackClaimResult:
            row = _callback_row(connection, token_hash_sha256)
            if row is None:
                return ApprovalCallbackClaimResult(ApprovalCallbackClaimStatus.NOT_FOUND, None)
            callback = _materialize_callback(row)
            if callback.authorized_user_id != authorized_user_id or callback.authorized_chat_id != authorized_chat_id:
                return ApprovalCallbackClaimResult(ApprovalCallbackClaimStatus.UNAUTHORIZED, None)
            if callback.consumed_at_ms is not None:
                return ApprovalCallbackClaimResult(ApprovalCallbackClaimStatus.ALREADY_CONSUMED, None)

            # Binding mismatches are authorized stale clicks.  They are consumed
            # exactly once, but never expose approval metadata.
            stale = callback.subject_type != "approval" \
                or callback.expected_state != ApprovalState.PENDING.value \
                or callback.action not in ("approval_allow", "approval_deny")
            approval_row = None if stale else _approval_row(connection, callback.subject_id)
            if approval_row is None and not stale:
                stale = True
            approval = None if approval_row is None else _materialize_approval(connection, approval_row)
            job = None
            if approval is not None:
                job_row = _job_row(connection, approval.job_id)
                if job_row is None:
                    stale = True
                else:
                    job = _materialize_job(job_row)
                    dialogue_row = _dialogue_row(connection, job.dialogue_id)
                    if dialogue_row is None:
                        stale = True
                    else:
                        dialogue = _materialize_dialogue(dialogue_row)
                        if (
                            callback.expected_version != job.version
                            or approval.job_id != job.job_id
                            or approval.profile_id != job.profile_id
                            or approval.state is not ApprovalState.PENDING
                            or job.state is not TurnJobState.CODEX_RUNNING
                            or dialogue.state.value != "TURN_RUNNING"
                        ):
                            stale = True

            now = _validate_clock(self._clock)
            effective_now = max(now, callback.created_at_ms)
            if stale:
                marker = callback.expires_at_ms if effective_now >= callback.expires_at_ms else effective_now
                _consume_callback(connection, token_hash_sha256, marker)
                return ApprovalCallbackClaimResult(ApprovalCallbackClaimStatus.STALE, None)

            assert approval is not None and job is not None
            callback_expired = effective_now >= callback.expires_at_ms
            approval_expired = approval.expires_at_ms <= effective_now
            if callback_expired or approval_expired:
                marker = callback.expires_at_ms if callback_expired else effective_now
                _consume_callback(connection, token_hash_sha256, marker)
                if approval_expired:
                    updated = max(effective_now, approval.updated_at_ms)
                    changed = connection.execute(
                        "UPDATE approvals SET state = ?, updated_at_ms = ? "
                        "WHERE approval_id = ? AND state = ?",
                        (ApprovalState.EXPIRED.value, updated, approval.approval_id,
                         ApprovalState.PENDING.value),
                    ).rowcount
                    if changed != 1:
                        raise _invariant()
                return ApprovalCallbackClaimResult(ApprovalCallbackClaimStatus.EXPIRED, None)

            next_state = ApprovalState.APPROVED if callback.action == "approval_allow" else ApprovalState.DENIED
            updated = max(effective_now, approval.updated_at_ms)
            _consume_callback(connection, token_hash_sha256, effective_now)
            changed = connection.execute(
                "UPDATE approvals SET state = ?, updated_at_ms = ? "
                "WHERE approval_id = ? AND state = ?",
                (next_state.value, updated, approval.approval_id, ApprovalState.PENDING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return ApprovalCallbackClaimResult(
                ApprovalCallbackClaimStatus.APPROVED if next_state is ApprovalState.APPROVED
                else ApprovalCallbackClaimStatus.DENIED,
                ApprovalRecord(
                    approval.approval_id, approval.profile_id, approval.wire_request_id,
                    approval.kind, approval.job_id, approval.display_payload_id,
                    next_state, approval.created_at_ms, updated, approval.expires_at_ms,
                ),
            )

        return await self._storage.write(write)

    async def cancel_pending_for_job(self, job_id: str) -> tuple[ApprovalRecord, ...]:
        job_id = _validate_id(job_id)

        def write(connection: Any) -> tuple[ApprovalRecord, ...]:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if job.state is TurnJobState.CODEX_RUNNING:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            rows = connection.execute(
                _approval_select() + " WHERE job_id = ? AND state = 'PENDING' ORDER BY approval_id",
                (job_id,),
            ).fetchall()
            approvals = tuple(_materialize_approval(connection, row) for row in rows)
            if not approvals:
                return ()
            now = _validate_clock(self._clock)
            updated = max(now, *(approval.updated_at_ms for approval in approvals))
            result = []
            for approval in approvals:
                changed = connection.execute(
                    "UPDATE approvals SET state = ?, updated_at_ms = ? "
                    "WHERE approval_id = ? AND state = ?",
                    (ApprovalState.CANCELLED.value, updated, approval.approval_id,
                     ApprovalState.PENDING.value),
                ).rowcount
                if changed != 1:
                    raise _invariant()
                result.append(ApprovalRecord(
                    approval.approval_id, approval.profile_id, approval.wire_request_id,
                    approval.kind, approval.job_id, approval.display_payload_id,
                    ApprovalState.CANCELLED, approval.created_at_ms, updated, approval.expires_at_ms,
                ))
            return tuple(result)

        return await self._storage.write(write)
