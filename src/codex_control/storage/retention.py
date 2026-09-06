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
from .turn_job_repositories import _materialize_payload, _payload_select


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

            # Apply every protection predicate in SQL before LIMIT. This keeps
            # an old protected row from hiding later eligible content forever.
            candidates = connection.execute(
                _payload_select().replace(
                    "FROM transient_payloads", "FROM transient_payloads AS p"
                )
                + " WHERE p.expires_at_ms <= ?"
                + " AND NOT EXISTS ("
                + "SELECT 1 FROM delivery_segments AS ds "
                + "WHERE ds.payload_id = p.payload_id "
                + "AND ds.state IN ('PENDING', 'SENDING', 'UNKNOWN'))"
                + " AND NOT EXISTS ("
                + "SELECT 1 FROM approvals AS a "
                + "WHERE a.display_payload_id = p.payload_id AND a.state = 'PENDING')"
                + " AND NOT EXISTS ("
                + "SELECT 1 FROM turn_jobs AS j WHERE j.job_id = p.job_id AND ("
                + "(p.kind = 'INPUT' AND j.state IN "
                + "('RECEIVED', 'CLAIMED', 'CODEX_STARTING', 'CODEX_RUNNING'))"
                + " OR (p.kind = 'OUTPUT' AND j.state IN "
                + "('CODEX_COMPLETED', 'DELIVERY_PENDING', 'DELIVERING', 'DELIVERY_UNKNOWN'))"
                + "))"
                + " ORDER BY p.expires_at_ms, p.payload_id LIMIT ?",
                (now, limit),
            ).fetchall()
            selected = tuple(_materialize_payload(connection, row) for row in candidates)
            deleted = 0
            for payload in selected:
                changed = connection.execute(
                    "DELETE FROM transient_payloads WHERE payload_id = ?", (payload.payload_id,)
                ).rowcount
                if changed != 1:
                    raise RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)
                deleted += 1
            return RetentionSweepResult(len(due), deleted)

        return await self._storage.write(write)
