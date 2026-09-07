"""Narrow schema-v1 durable authority for private menu/callback batches."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .idempotency_records import (
    CallbackActionRecord,
    IngressClaimResult,
    IngressDispositionKind,
)
from .idempotency_repositories import (
    _default_clock,
    _materialize_callback,
    _materialize_ingress,
    _validate_clock,
    _validate_expected_version,
    _validate_identified,
    _validate_nonneg_int,
    _validate_subject_id,
    _validate_token_hash,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage


@dataclass(frozen=True, repr=False)
class PrivateCallbackActionSpec:
    token_hash_sha256: str
    action: str
    subject_type: str
    subject_id: str
    expected_version: int
    expected_state: str
    authorized_user_id: int
    authorized_chat_id: int

    def __repr__(self) -> str:
        return (
            "PrivateCallbackActionSpec(token_hash_sha256='[REDACTED]', "
            f"action={self.action!r}, subject_type={self.subject_type!r}, "
            "subject_id='[REDACTED]', "
            f"expected_version={self.expected_version!r}, "
            f"expected_state={self.expected_state!r}, authorized_user_id={self.authorized_user_id!r}, "
            f"authorized_chat_id={self.authorized_chat_id!r})"
        )


class DeleteConfirmationRevocationStatus(StrEnum):
    REVOKED = "REVOKED"
    CONFIRM_ALREADY_CLAIMED = "CONFIRM_ALREADY_CLAIMED"


@dataclass(frozen=True)
class DeleteConfirmationRevocationResult:
    status: DeleteConfirmationRevocationStatus
    revoked_count: int


class PrivateManagementRepository:
    """Private-menu ingress and all-or-none callback creation."""

    def __init__(self, storage: SqliteStorage, *, now_ms=None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<PrivateManagementRepository>"

    async def claim_private_command(self, *, update_id: int) -> IngressClaimResult:
        update_id = _validate_nonneg_int(update_id)

        def write(connection: Any) -> IngressClaimResult:
            row = connection.execute(
                "SELECT update_id, received_at_ms, completed_at_ms, disposition "
                "FROM ingress_updates WHERE update_id = ?",
                (update_id,),
            ).fetchone()
            if row is not None:
                return IngressClaimResult(_materialize_ingress(row), True)
            now = _validate_clock(self._clock)
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES (?, ?, ?, ?)",
                (update_id, now, now, IngressDispositionKind.CONTROL.value),
            )
            return IngressClaimResult(
                _materialize_ingress((update_id, now, now, IngressDispositionKind.CONTROL.value)),
                False,
            )

        return await self._storage.write(write)

    async def create_callback_batch(
        self,
        *,
        actions: tuple[PrivateCallbackActionSpec, ...],
        created_at_ms: int,
        expires_at_ms: int,
    ) -> tuple[CallbackActionRecord, ...]:
        if type(actions) is not tuple or not actions:
            raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
        created_at_ms = _validate_nonneg_int(created_at_ms)
        expires_at_ms = _validate_nonneg_int(expires_at_ms)
        if expires_at_ms <= created_at_ms:
            raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)

        normalized: list[PrivateCallbackActionSpec] = []
        hashes: set[str] = set()
        for item in actions:
            if not isinstance(item, PrivateCallbackActionSpec):
                raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
            token_hash = _validate_token_hash(item.token_hash_sha256)
            action = _validate_identified(item.action, 128)
            subject_type = _validate_identified(item.subject_type, 64)
            subject_id = _validate_subject_id(item.subject_id)
            expected_version = _validate_expected_version(item.expected_version)
            expected_state = _validate_identified(item.expected_state, 64)
            authorized_user_id = _validate_nonneg_int(item.authorized_user_id)
            if authorized_user_id == 0:
                raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
            authorized_chat_id = _validate_nonzero_chat_id(item.authorized_chat_id)
            if token_hash in hashes:
                raise RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)
            hashes.add(token_hash)
            normalized.append(
                PrivateCallbackActionSpec(
                    token_hash, action, subject_type, subject_id, expected_version,
                    expected_state, authorized_user_id, authorized_chat_id,
                )
            )

        def write(connection: Any) -> tuple[CallbackActionRecord, ...]:
            for item in normalized:
                if connection.execute(
                    "SELECT 1 FROM callback_actions WHERE token_hash_sha256 = ?",
                    (item.token_hash_sha256,),
                ).fetchone() is not None:
                    raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)
            try:
                for item in normalized:
                    connection.execute(
                        "INSERT INTO callback_actions"
                        "(token_hash_sha256, action, subject_type, subject_id, expected_version, "
                        "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                        (
                            item.token_hash_sha256, item.action, item.subject_type, item.subject_id,
                            item.expected_version, item.expected_state, item.authorized_user_id,
                            item.authorized_chat_id, created_at_ms, expires_at_ms,
                        ),
                    )
            except sqlite3.IntegrityError:
                raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)
            return tuple(
                _materialize_callback(
                    (
                        item.token_hash_sha256, item.action, item.subject_type, item.subject_id,
                        item.expected_version, item.expected_state, item.authorized_user_id,
                        item.authorized_chat_id, created_at_ms, expires_at_ms, None,
                    )
                )
                for item in normalized
            )

        return await self._storage.write(write)

    async def peek_callback(self, token_hash_sha256: str) -> CallbackActionRecord | None:
        """Read one callback action without consuming or consulting the clock."""
        token_hash_sha256 = _validate_token_hash(token_hash_sha256)

        def read(connection: Any) -> CallbackActionRecord | None:
            row = connection.execute(
                "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, expires_at_ms, consumed_at_ms "
                "FROM callback_actions WHERE token_hash_sha256 = ?",
                (token_hash_sha256,),
            ).fetchone()
            return None if row is None else _materialize_callback(row)

        return await self._storage.read(read)

    async def revoke_delete_confirmations(
        self,
        *,
        subject_id: str,
        expected_version: int,
        expected_state: str,
        authorized_user_id: int,
        authorized_chat_id: int,
        consumed_at_ms: int,
    ) -> DeleteConfirmationRevocationResult:
        """Revoke all unconsumed confirmations for one exact delete context.

        This is deliberately one writer transaction.  A confirmation claimed
        before this transaction linearizes the cancel as stale; expired
        confirmation rows are already non-destructive and may be finalized.
        """
        subject_id = _validate_subject_id(subject_id)
        expected_version = _validate_expected_version(expected_version)
        expected_state = _validate_identified(expected_state, 64)
        authorized_user_id = _validate_nonneg_int(authorized_user_id)
        if authorized_user_id == 0:
            raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
        authorized_chat_id = _validate_nonzero_chat_id(authorized_chat_id)
        consumed_at_ms = _validate_nonneg_int(consumed_at_ms)

        def write(connection: Any) -> DeleteConfirmationRevocationResult:
            rows = connection.execute(
                "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
                "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
                "expires_at_ms, consumed_at_ms FROM callback_actions "
                "WHERE action = 'P42_CONFIRM_DELETE' AND subject_type = 'p42_delete' "
                "AND subject_id = ? AND expected_version = ? AND expected_state = ? "
                "AND authorized_user_id = ? AND authorized_chat_id = ? "
                "ORDER BY token_hash_sha256",
                (subject_id, expected_version, expected_state, authorized_user_id, authorized_chat_id),
            ).fetchall()
            records = tuple(_materialize_callback(row) for row in rows)
            if any(
                record.consumed_at_ms is not None
                and record.consumed_at_ms < record.expires_at_ms
                for record in records
            ):
                return DeleteConfirmationRevocationResult(
                    DeleteConfirmationRevocationStatus.CONFIRM_ALREADY_CLAIMED,
                    0,
                )

            revoked_count = 0
            for record in records:
                if record.consumed_at_ms is not None:
                    continue
                changed = connection.execute(
                    "UPDATE callback_actions SET consumed_at_ms = ? "
                    "WHERE token_hash_sha256 = ? AND consumed_at_ms IS NULL",
                    (record.expires_at_ms, record.token_hash_sha256),
                ).rowcount
                if changed != 1:
                    raise RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)
                revoked_count += 1
            return DeleteConfirmationRevocationResult(
                DeleteConfirmationRevocationStatus.REVOKED,
                revoked_count,
            )

        return await self._storage.write(write)


def _validate_nonzero_chat_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value == 0 or not -(2**63) <= value <= 2**63 - 1:
        raise RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)
    return value


__all__ = [
    "PrivateCallbackActionSpec",
    "DeleteConfirmationRevocationStatus",
    "DeleteConfirmationRevocationResult",
    "PrivateManagementRepository",
]
