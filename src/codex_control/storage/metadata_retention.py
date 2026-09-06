"""Explicit bounded retention of non-content durable metadata."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .approval_repositories import _approval_select, _materialize_approval
from .core_repositories import _default_clock, _materialize_dialogue, _validate_clock
from .deletion_repositories import _materialize_tombstone, _tombstone_select
from .delivery_repositories import _load_segments, _validate_delivery_coherence
from .error_repositories import _materialize_error, _error_select
from .idempotency_repositories import _materialize_callback, _materialize_ingress
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .turn_job_repositories import (
    _dialogue_row,
    _job_select,
    _materialize_job,
    _materialize_payload,
    _payload_select,
)


METADATA_RETENTION_MS = 604_800_000


@dataclass(frozen=True)
class MetadataRetentionSweepResult:
    terminal_jobs_deleted: int
    payloads_deleted: int
    delivery_segments_deleted: int
    approvals_deleted: int
    ingress_deleted: int
    callback_actions_deleted: int
    tombstones_deleted: int
    errors_deleted: int


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _job_dialogue(connection: Any, job: Any) -> Any:
    row = _dialogue_row(connection, job.dialogue_id)
    if row is None:
        raise _invariant()
    dialogue = _materialize_dialogue(row)
    if (
        dialogue.dialogue_id != job.dialogue_id
        or dialogue.server_id != job.server_id
        or dialogue.profile_id != job.profile_id
        or dialogue.thread_id != job.thread_id
    ):
        raise _invariant()
    return dialogue


def _required_job_ingress(connection: Any, job: Any) -> Any:
    expected_disposition = f"JOB:{job.job_id}"
    rows = connection.execute(
        "SELECT update_id, received_at_ms, completed_at_ms, disposition "
        "FROM ingress_updates WHERE disposition = ? ORDER BY update_id LIMIT 2",
        (expected_disposition,),
    ).fetchall()
    if len(rows) != 1:
        raise _invariant()
    ingress = _materialize_ingress(rows[0])
    if (
        ingress.update_id != job.telegram_update_id
        or ingress.disposition.value != "JOB"
        or ingress.job_id != job.job_id
        or ingress.completed_at_ms is None
    ):
        raise _invariant()
    return ingress


def _job_children(connection: Any, job: Any) -> tuple[int, int, int, bool]:
    payload_rows = connection.execute(
        _payload_select() + " WHERE job_id = ? ORDER BY payload_id", (job.job_id,)
    ).fetchall()
    for row in payload_rows:
        payload = _materialize_payload(connection, row)
        if payload.job_id != job.job_id:
            raise _invariant()
        if payload.dialogue_id is not None and payload.dialogue_id != job.dialogue_id:
            raise _invariant()

    segments = _load_segments(connection, job)
    _validate_delivery_coherence(connection, job, segments)

    approval_rows = connection.execute(
        _approval_select() + " WHERE job_id = ? ORDER BY approval_id", (job.job_id,)
    ).fetchall()
    pending = False
    for row in approval_rows:
        approval = _materialize_approval(connection, row)
        if approval.job_id != job.job_id:
            raise _invariant()
        if approval.state.value == "PENDING":
            pending = True

    return len(payload_rows), len(segments), len(approval_rows), pending


def _old_terminal_jobs(connection: Any, cutoff: int, limit: int) -> list[tuple[Any, int, int, int, Any]]:
    # Missing, duplicated, incomplete, or identity-incoherent JOB ingress is
    # corruption, not an ineligible root that may be hidden by LIMIT.  This
    # probe returns only one root and does not materialize any record.
    offending = connection.execute(
        "SELECT j.job_id FROM turn_jobs AS j "
        "WHERE j.state IN ('DELIVERED', 'FAILED') AND j.updated_at_ms <= ? "
        "AND ("
        "NOT EXISTS (SELECT 1 FROM ingress_updates AS i "
        "WHERE i.disposition = 'JOB:' || j.job_id) "
        "OR (SELECT COUNT(*) FROM ingress_updates AS i "
        "WHERE i.disposition = 'JOB:' || j.job_id) > 1 "
        "OR EXISTS (SELECT 1 FROM ingress_updates AS i "
        "WHERE i.disposition = 'JOB:' || j.job_id AND i.completed_at_ms IS NULL) "
        "OR EXISTS (SELECT 1 FROM ingress_updates AS i "
        "WHERE i.disposition = 'JOB:' || j.job_id AND i.update_id <> j.telegram_update_id) "
        "OR NOT EXISTS (SELECT 1 FROM ingress_updates AS i "
        "WHERE i.update_id = j.telegram_update_id "
        "AND i.disposition = 'JOB:' || j.job_id)"
        ") LIMIT 1",
        (cutoff,),
    ).fetchone()
    if offending is not None:
        raise _invariant()

    rows = connection.execute(
        _job_select()
        + " AS j WHERE j.state IN ('DELIVERED', 'FAILED') AND j.updated_at_ms <= ?"
        + " AND NOT EXISTS (SELECT 1 FROM approvals AS a "
        "WHERE a.job_id = j.job_id AND a.state = 'PENDING')"
        + " AND EXISTS (SELECT 1 FROM ingress_updates AS i "
        "WHERE i.update_id = j.telegram_update_id "
        "AND i.disposition = 'JOB:' || j.job_id "
        "AND i.completed_at_ms IS NOT NULL AND i.completed_at_ms <= ?)"
        + " ORDER BY j.updated_at_ms, j.job_id LIMIT ?",
        (cutoff, cutoff, limit),
    ).fetchall()
    eligible: list[tuple[Any, int, int, int, Any]] = []
    for row in rows:
        job = _materialize_job(row)
        _job_dialogue(connection, job)
        payload_count, segment_count, approval_count, pending = _job_children(connection, job)
        ingress = _required_job_ingress(connection, job)
        if pending or ingress.completed_at_ms is None or ingress.completed_at_ms > cutoff:
            continue
        eligible.append((job, payload_count, segment_count, approval_count, ingress))
    return eligible


def _standalone_ingress(connection: Any, cutoff: int, limit: int) -> list[Any]:
    offending = connection.execute(
        "SELECT i.update_id FROM ingress_updates AS i "
        "WHERE i.completed_at_ms IS NOT NULL AND i.completed_at_ms <= ? AND ("
        "(i.disposition LIKE 'JOB:%' AND ("
        "EXISTS (SELECT 1 FROM turn_jobs AS suffix_job "
        "WHERE suffix_job.job_id = substr(i.disposition, 5) "
        "AND suffix_job.telegram_update_id <> i.update_id) "
        "OR EXISTS (SELECT 1 FROM turn_jobs AS update_job "
        "WHERE update_job.telegram_update_id = i.update_id "
        "AND update_job.job_id <> substr(i.disposition, 5))"
        ")) "
        "OR (i.disposition NOT LIKE 'JOB:%' AND EXISTS ("
        "SELECT 1 FROM turn_jobs AS update_job "
        "WHERE update_job.telegram_update_id = i.update_id))"
        ") LIMIT 1",
        (cutoff,),
    ).fetchone()
    if offending is not None:
        raise _invariant()

    rows = connection.execute(
        "SELECT update_id, received_at_ms, completed_at_ms, disposition "
        "FROM ingress_updates AS i WHERE i.completed_at_ms IS NOT NULL AND i.completed_at_ms <= ?"
        " AND (i.disposition IN ('CONTROL', 'IGNORED_SLEEP', 'IGNORED_UNAUTHORIZED')"
        " OR (i.disposition LIKE 'JOB:%'"
        " AND NOT EXISTS (SELECT 1 FROM turn_jobs AS suffix_job "
        "WHERE suffix_job.job_id = substr(i.disposition, 5))"
        " AND NOT EXISTS (SELECT 1 FROM turn_jobs AS update_job "
        "WHERE update_job.telegram_update_id = i.update_id)))"
        " ORDER BY i.completed_at_ms, i.update_id LIMIT ?",
        (cutoff, limit),
    ).fetchall()
    eligible: list[Any] = []
    for row in rows:
        ingress = _materialize_ingress(row)
        if ingress.completed_at_ms is None:
            raise _invariant()
        eligible.append(ingress)
    return eligible


def _old_callbacks(connection: Any, cutoff: int, limit: int) -> list[Any]:
    rows = connection.execute(
        "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
        "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
        "expires_at_ms, consumed_at_ms FROM callback_actions "
        "WHERE expires_at_ms <= ? ORDER BY expires_at_ms, token_hash_sha256 LIMIT ?",
        (cutoff, limit),
    ).fetchall()
    eligible: list[Any] = []
    for row in rows:
        callback = _materialize_callback(row)
        aliases = connection.execute(
            "SELECT token_hash_sha256, action, subject_type, subject_id, expected_version, "
            "expected_state, authorized_user_id, authorized_chat_id, created_at_ms, "
            "expires_at_ms, consumed_at_ms FROM callback_actions "
            "WHERE lower(token_hash_sha256) = ? ORDER BY token_hash_sha256 LIMIT 2",
            (callback.token_hash_sha256,),
        ).fetchall()
        if len(aliases) != 1:
            raise _invariant()
        # Materialize the physical alias set as well; this explicitly rejects
        # an uppercase-only or dual-case semantic callback row.
        if aliases[0][0] != callback.token_hash_sha256:
            raise _invariant()
        eligible.append(callback)
    return eligible


def _expired_tombstones(connection: Any, now: int, limit: int) -> list[Any]:
    rows = connection.execute(
        _tombstone_select() + " WHERE expires_at_ms <= ? ORDER BY expires_at_ms, dialogue_id LIMIT ?",
        (now, limit),
    ).fetchall()
    eligible: list[Any] = []
    for row in rows:
        tombstone = _materialize_tombstone(row)
        dialogue_row = _dialogue_row(connection, tombstone.dialogue_id)
        if dialogue_row is not None:
            _materialize_dialogue(dialogue_row)
            raise _invariant()
        eligible.append(tombstone)
    return eligible


def _old_errors(connection: Any, cutoff: int, limit: int) -> list[Any]:
    rows = connection.execute(
        _error_select() + " WHERE last_seen_at_ms <= ? ORDER BY last_seen_at_ms, fingerprint_sha256 LIMIT ?",
        (cutoff, limit),
    ).fetchall()
    eligible: list[Any] = []
    for row in rows:
        error = _materialize_error(connection, row)
        aliases = connection.execute(
            _error_select()
            + " WHERE lower(fingerprint_sha256) = ? ORDER BY fingerprint_sha256 LIMIT 2",
            (error.fingerprint_sha256,),
        ).fetchall()
        if len(aliases) != 1 or aliases[0][0] != error.fingerprint_sha256:
            raise _invariant()
        eligible.append(error)
    return eligible


class MetadataRetentionRepository:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<MetadataRetentionRepository>"

    async def sweep(self, limit: int) -> MetadataRetentionSweepResult:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise _invalid()

        def write(connection: Any) -> MetadataRetentionSweepResult:
            now = _validate_clock(self._clock)
            cutoff = max(0, now - METADATA_RETENTION_MS)

            jobs = _old_terminal_jobs(connection, cutoff, limit)

            payloads_deleted = 0
            delivery_segments_deleted = 0
            approvals_deleted = 0
            ingress_deleted = 0
            for job, payload_count, segment_count, approval_count, ingress in jobs:
                deleted_ingress = connection.execute(
                    "DELETE FROM ingress_updates WHERE update_id = ? "
                    "AND disposition = ?",
                    (ingress.update_id, f"JOB:{job.job_id}"),
                ).rowcount
                if deleted_ingress != 1:
                    raise _invariant()
                deleted_job = connection.execute(
                    "DELETE FROM turn_jobs WHERE job_id = ? AND telegram_update_id = ? "
                    "AND state = ? AND version = ?",
                    (job.job_id, job.telegram_update_id, job.state.value, job.version),
                ).rowcount
                if deleted_job != 1:
                    raise _invariant()
                payloads_deleted += payload_count
                delivery_segments_deleted += segment_count
                approvals_deleted += approval_count
                ingress_deleted += deleted_ingress

            standalone = _standalone_ingress(connection, cutoff, limit)
            for ingress in standalone:
                changed = connection.execute(
                    "DELETE FROM ingress_updates WHERE update_id = ?",
                    (ingress.update_id,),
                ).rowcount
                if changed != 1:
                    raise _invariant()
                ingress_deleted += changed

            callbacks = _old_callbacks(connection, cutoff, limit)
            for callback in callbacks:
                changed = connection.execute(
                    "DELETE FROM callback_actions WHERE token_hash_sha256 = ? "
                    "AND expires_at_ms <= ?",
                    (callback.token_hash_sha256, cutoff),
                ).rowcount
                if changed != 1:
                    raise _invariant()

            tombstones = _expired_tombstones(connection, now, limit)
            for tombstone in tombstones:
                changed = connection.execute(
                    "DELETE FROM deletion_tombstones WHERE dialogue_id = ? "
                    "AND expires_at_ms <= ?",
                    (tombstone.dialogue_id, now),
                ).rowcount
                if changed != 1:
                    raise _invariant()

            errors = _old_errors(connection, cutoff, limit)
            for error in errors:
                changed = connection.execute(
                    "DELETE FROM errors WHERE fingerprint_sha256 = ? "
                    "AND last_seen_at_ms <= ?",
                    (error.fingerprint_sha256, cutoff),
                ).rowcount
                if changed != 1:
                    raise _invariant()

            return MetadataRetentionSweepResult(
                terminal_jobs_deleted=len(jobs),
                payloads_deleted=payloads_deleted,
                delivery_segments_deleted=delivery_segments_deleted,
                approvals_deleted=approvals_deleted,
                ingress_deleted=ingress_deleted,
                callback_actions_deleted=len(callbacks),
                tombstones_deleted=len(tombstones),
                errors_deleted=len(errors),
            )

        return await self._storage.write(write)
