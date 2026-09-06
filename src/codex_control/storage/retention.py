"""Bounded, explicit transient-content retention for P2.4b."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .approval_repositories import _approval_select, _materialize_approval
from .approval_records import ApprovalState
from .core_repositories import _default_clock, _validate_clock
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .transient_payloads import TransientPayloadKind
from .turn_job_records import TurnJobState
from .turn_job_repositories import _materialize_payload, _payload_select, _payload_row


@dataclass(frozen=True)
class RetentionSweepResult:
    approvals_expired: int
    payloads_deleted: int


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


class RetentionRepository:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<RetentionRepository>"

    async def sweep(self, limit: int) -> RetentionSweepResult:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise _invalid()

        def write(connection: Any) -> RetentionSweepResult:
            now = _validate_clock(self._clock)
            due_rows = connection.execute(
                _approval_select() + " WHERE state = 'PENDING' AND expires_at_ms <= ? ORDER BY approval_id",
                (now,),
            ).fetchall()
            due = tuple(_materialize_approval(connection, row) for row in due_rows)
            for approval in due:
                updated = max(now, approval.updated_at_ms)
                changed = connection.execute(
                    "UPDATE approvals SET state = ?, updated_at_ms = ? "
                    "WHERE approval_id = ? AND state = 'PENDING' AND expires_at_ms <= ?",
                    (ApprovalState.EXPIRED.value, updated, approval.approval_id, now),
                ).rowcount
                if changed != 1:
                    raise RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)

            candidates = connection.execute(
                _payload_select() + " WHERE expires_at_ms <= ? ORDER BY expires_at_ms, payload_id LIMIT ?",
                (now, limit),
            ).fetchall()
            deleted = 0
            for row in candidates:
                payload = _materialize_payload(connection, row)
                if _protected(connection, payload.payload_id, payload.kind, payload.job_id):
                    continue
                changed = connection.execute(
                    "DELETE FROM transient_payloads WHERE payload_id = ?", (payload.payload_id,)
                ).rowcount
                if changed != 1:
                    raise RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)
                deleted += 1
            return RetentionSweepResult(len(due), deleted)

        return await self._storage.write(write)


def _protected(connection: Any, payload_id: str, kind: TransientPayloadKind,
               job_id: str | None) -> bool:
    if connection.execute(
        "SELECT 1 FROM delivery_segments WHERE payload_id = ? "
        "AND state IN ('PENDING', 'SENDING', 'UNKNOWN') LIMIT 1", (payload_id,)
    ).fetchone() is not None:
        return True
    if connection.execute(
        "SELECT 1 FROM approvals WHERE display_payload_id = ? AND state = 'PENDING' LIMIT 1",
        (payload_id,),
    ).fetchone() is not None:
        return True
    if job_id is None:
        return False
    if kind is TransientPayloadKind.INPUT:
        protected_states = ("RECEIVED", "CLAIMED", "CODEX_STARTING", "CODEX_RUNNING")
    elif kind is TransientPayloadKind.OUTPUT:
        protected_states = ("CODEX_COMPLETED", "DELIVERY_PENDING", "DELIVERING", "DELIVERY_UNKNOWN")
    else:
        return False
    placeholders = ", ".join("?" for _ in protected_states)
    return connection.execute(
        f"SELECT 1 FROM turn_jobs WHERE job_id = ? AND state IN ({placeholders}) LIMIT 1",
        (job_id, *protected_states),
    ).fetchone() is not None
