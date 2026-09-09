"""Narrow schema-v1 coordination for final application startup recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .core_repositories import (
    MAX_SQLITE_INT,
    _materialize_dialogue,
    _next_version,
    _validate_clock,
)
from .idempotency_repositories import _materialize_ingress
from .records import DialogueRecord, DialogueState
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .turn_job_records import TurnJobRecord, TurnJobState
from .turn_job_repositories import (
    _input_for_job,
    _job_select,
    _materialize_job,
)


_ACTIVE_STATES = frozenset(
    (
        TurnJobState.RECEIVED,
        TurnJobState.CLAIMED,
        TurnJobState.CODEX_STARTING,
        TurnJobState.CODEX_RUNNING,
    )
)

_UNBOUND_CREATE_ERROR_CLASSES = frozenset(
    ("CODEX_PROCESS", "CODEX_THREAD_FAILED", "APPLICATION_ADMISSION_FAILED")
)
_BOUND_ERROR_CLASSES = frozenset(("CODEX_PROCESS", "CODEX_TURN_FAILED"))


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


@dataclass(frozen=True)
class ApplicationRecoverySnapshot:
    dialogue: DialogueRecord | None
    active_jobs: tuple[TurnJobRecord, ...]


@dataclass(frozen=True)
class ApplicationRecoveryTransition:
    action: str
    job: TurnJobRecord | None
    dialogue: DialogueRecord | None


def _dialogue_row(connection: Any) -> Any:
    rows = connection.execute(
        "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
        "created_at_ms, updated_at_ms, last_error_class FROM dialogues"
    ).fetchall()
    if len(rows) > 1:
        raise _invariant()
    return rows[0] if rows else None


def _validate_ingress_and_input(connection: Any, job: TurnJobRecord) -> None:
    row = connection.execute(
        "SELECT update_id, received_at_ms, completed_at_ms, disposition "
        "FROM ingress_updates WHERE update_id = ?",
        (job.telegram_update_id,),
    ).fetchone()
    if row is None:
        raise _invariant()
    ingress = _materialize_ingress(row)
    if ingress.disposition.value != "JOB" or ingress.job_id != job.job_id:
        raise _invariant()
    _input_for_job(
        connection,
        job,
        missing_category=RepositoryErrorCategory.INVARIANT_VIOLATION,
    )


def _validate_owner(dialogue: DialogueRecord, job: TurnJobRecord) -> None:
    if (
        job.dialogue_id != dialogue.dialogue_id
        or job.server_id != dialogue.server_id
        or job.profile_id != dialogue.profile_id
        or dialogue.thread_id is None
        or job.thread_id != dialogue.thread_id
    ):
        raise _invariant()


def _validate_received_job(job: TurnJobRecord, *, unbound: bool) -> None:
    if (
        job.state is not TurnJobState.RECEIVED
        or (job.thread_id is not None if unbound else job.thread_id is None)
        or job.codex_turn_id is not None
        or job.error_class is not None
        or job.model_id is None
        or job.reasoning_effort is None
    ):
        raise _invariant()


def _validate_canonical_dialogue(
    dialogue: DialogueRecord, jobs: tuple[TurnJobRecord, ...]
) -> None:
    """Apply P3.5's complete cross-table dialogue state authority.

    Core materialization validates schema shape.  This layer additionally
    validates the application meaning of every state, including dialogue-side
    binding and error fields.
    """
    state = dialogue.state
    if state is DialogueState.CREATING:
        if dialogue.thread_id is not None or dialogue.last_error_class is not None:
            raise _invariant()
        if len(jobs) > 1:
            raise _invariant()
        if jobs:
            _validate_received_job(jobs[0], unbound=True)
        return

    if state is DialogueState.CREATE_UNKNOWN:
        if dialogue.thread_id is not None or dialogue.last_error_class != "CODEX_AMBIGUOUS":
            raise _invariant()
        if len(jobs) > 1:
            raise _invariant()
        if jobs:
            _validate_received_job(jobs[0], unbound=True)
        return

    if state is DialogueState.ERROR and dialogue.thread_id is None:
        if dialogue.last_error_class not in _UNBOUND_CREATE_ERROR_CLASSES:
            raise _invariant()
        if len(jobs) > 1:
            raise _invariant()
        if jobs:
            _validate_received_job(jobs[0], unbound=True)
        return

    if state is DialogueState.ERROR:
        if dialogue.last_error_class not in _BOUND_ERROR_CLASSES or jobs:
            raise _invariant()
        return

    if state is DialogueState.IDLE:
        if dialogue.thread_id is None or dialogue.last_error_class is not None:
            raise _invariant()
        if len(jobs) > 1:
            raise _invariant()
        if jobs:
            if jobs[0].state is not TurnJobState.RECEIVED:
                raise _invariant()
            _validate_received_job(jobs[0], unbound=False)
            _validate_owner(dialogue, jobs[0])
        return

    if state is DialogueState.TURN_RUNNING:
        if dialogue.thread_id is None or dialogue.last_error_class is not None or len(jobs) != 1:
            raise _invariant()
        if jobs[0].state not in (
            TurnJobState.CLAIMED, TurnJobState.CODEX_STARTING, TurnJobState.CODEX_RUNNING
        ):
            raise _invariant()
        _validate_owner(dialogue, jobs[0])
        if jobs[0].state is TurnJobState.CODEX_STARTING and jobs[0].codex_turn_id is not None:
            raise _invariant()
        if jobs[0].state is TurnJobState.CODEX_RUNNING and jobs[0].codex_turn_id is None:
            raise _invariant()
        if jobs[0].error_class is not None:
            raise _invariant()
        return

    if state is DialogueState.INTERRUPTING:
        if dialogue.thread_id is None or dialogue.last_error_class is not None or len(jobs) != 1:
            raise _invariant()
        if jobs[0].state is not TurnJobState.CODEX_RUNNING or jobs[0].codex_turn_id is None:
            raise _invariant()
        _validate_owner(dialogue, jobs[0])
        if jobs[0].error_class is not None:
            raise _invariant()
        return

    if state is DialogueState.TURN_UNKNOWN:
        if dialogue.thread_id is None or dialogue.last_error_class != "CODEX_AMBIGUOUS" or jobs:
            raise _invariant()
        return

    if state in (
        DialogueState.DELETE_PENDING,
        DialogueState.DELETING,
        DialogueState.DELETE_CONFIRMED_PENDING_STORAGE,
    ):
        if dialogue.thread_id is None or dialogue.last_error_class is not None or jobs:
            raise _invariant()
        return

    if state is DialogueState.DELETE_UNKNOWN:
        if dialogue.thread_id is None or dialogue.last_error_class != "DELETE_UNKNOWN" or jobs:
            raise _invariant()
        return

    raise _invariant()


def _snapshot(connection: Any) -> ApplicationRecoverySnapshot:
    row = _dialogue_row(connection)
    if row is None:
        return ApplicationRecoverySnapshot(None, ())
    dialogue = _materialize_dialogue(row)
    rows = connection.execute(
        _job_select()
        + " WHERE dialogue_id = ? AND state IN "
        + "('RECEIVED', 'CLAIMED', 'CODEX_STARTING', 'CODEX_RUNNING') "
        + "ORDER BY job_id",
        (dialogue.dialogue_id,),
    ).fetchall()
    jobs = tuple(_materialize_job(value) for value in rows)
    for job in jobs:
        if (
            job.dialogue_id != dialogue.dialogue_id
            or job.server_id != dialogue.server_id
            or job.profile_id != dialogue.profile_id
        ):
            raise _invariant()
        if (
            dialogue.state in (DialogueState.CREATING, DialogueState.CREATE_UNKNOWN, DialogueState.ERROR)
            and job.state is TurnJobState.RECEIVED
        ):
            if job.thread_id is not None or job.codex_turn_id is not None or job.error_class is not None:
                raise _invariant()
        else:
            _validate_owner(dialogue, job)
        _validate_ingress_and_input(connection, job)
    _validate_canonical_dialogue(dialogue, jobs)
    return ApplicationRecoverySnapshot(dialogue, jobs)


class ApplicationRecoveryRepository:
    """Read one canonical live dialogue and atomically recover its turn job."""

    def __init__(self, storage: SqliteStorage, *, now_ms) -> None:
        if not isinstance(storage, SqliteStorage) or not callable(now_ms):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms

    async def inspect(self) -> ApplicationRecoverySnapshot:
        return await self._storage.read(_snapshot)

    async def recover_turn(
        self,
        *,
        dialogue_id: str,
        expected_dialogue_version: int,
        expected_job_id: str,
        expected_job_version: int,
    ) -> ApplicationRecoveryTransition:
        if (
            type(dialogue_id) is not str
            or not dialogue_id
            or type(expected_dialogue_version) is not int
            or not 0 <= expected_dialogue_version <= MAX_SQLITE_INT
            or type(expected_job_id) is not str
            or not expected_job_id
            or type(expected_job_version) is not int
            or not 0 <= expected_job_version <= MAX_SQLITE_INT
        ):
            raise _invalid()

        def write(connection: Any) -> ApplicationRecoveryTransition:
            state = _snapshot(connection)
            dialogue = state.dialogue
            if dialogue is None:
                return ApplicationRecoveryTransition("NO_ACTION", None, None)
            if dialogue.dialogue_id != dialogue_id or dialogue.version != expected_dialogue_version:
                raise _invariant()
            if len(state.active_jobs) != 1:
                raise _invariant()
            job = state.active_jobs[0]
            if job.job_id != expected_job_id or job.version != expected_job_version:
                raise _invariant()
            _validate_owner(dialogue, job)
            _validate_ingress_and_input(connection, job)

            if dialogue.state is DialogueState.IDLE:
                if job.state is not TurnJobState.RECEIVED:
                    raise _invariant()
                if job.thread_id != dialogue.thread_id or job.codex_turn_id is not None or job.error_class is not None:
                    raise _invariant()
                job_version = _next_version(job.version)
                now = _validate_clock(self._clock)
                updated = max(now, job.updated_at_ms)
                if connection.execute(
                    "UPDATE turn_jobs SET state = 'FAILED', version = ?, updated_at_ms = ?, "
                    "error_class = 'CODEX_PROCESS' WHERE job_id = ? AND version = ? AND state = 'RECEIVED'",
                    (job_version, updated, job.job_id, job.version),
                ).rowcount != 1:
                    raise _invariant()
                return ApplicationRecoveryTransition(
                    "PRE_EFFECT_FAILED",
                    TurnJobRecord(
                        job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                        job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
                        job.reasoning_effort, job.input_sha256, job.codex_turn_id, TurnJobState.FAILED,
                        job_version, job.created_at_ms, updated, "CODEX_PROCESS",
                    ),
                    dialogue,
                )

            if dialogue.state is not DialogueState.TURN_RUNNING:
                raise _invariant()
            if job.state is TurnJobState.CLAIMED:
                if job.codex_turn_id is not None or job.error_class is not None:
                    raise _invariant()
                next_job_state = TurnJobState.FAILED
                next_job_error = "CODEX_PROCESS"
                next_dialogue_state = DialogueState.IDLE
                next_dialogue_error = None
                action = "PRE_EFFECT_FAILED"
            elif job.state in (TurnJobState.CODEX_STARTING, TurnJobState.CODEX_RUNNING):
                if job.state is TurnJobState.CODEX_STARTING and job.codex_turn_id is not None:
                    raise _invariant()
                if job.state is TurnJobState.CODEX_RUNNING and job.codex_turn_id is None:
                    raise _invariant()
                if job.error_class is not None:
                    raise _invariant()
                next_job_state = TurnJobState.UNKNOWN
                next_job_error = "CODEX_AMBIGUOUS"
                next_dialogue_state = DialogueState.TURN_UNKNOWN
                next_dialogue_error = "CODEX_AMBIGUOUS"
                action = "TURN_MARKED_UNKNOWN"
            else:
                raise _invariant()

            job_version = _next_version(job.version)
            dialogue_version = _next_version(dialogue.version)
            now = _validate_clock(self._clock)
            job_updated = max(now, job.updated_at_ms)
            dialogue_updated = max(now, dialogue.updated_at_ms)
            if connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ?, error_class = ? "
                "WHERE job_id = ? AND version = ?",
                (
                    next_job_state.value, job_version, job_updated, next_job_error,
                    job.job_id, job.version,
                ),
            ).rowcount != 1:
                raise _invariant()
            if connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, last_error_class = ? "
                "WHERE dialogue_id = ? AND version = ? AND state = 'TURN_RUNNING'",
                (
                    next_dialogue_state.value, dialogue_version, dialogue_updated,
                    next_dialogue_error, dialogue.dialogue_id, dialogue.version,
                ),
            ).rowcount != 1:
                raise _invariant()
            return ApplicationRecoveryTransition(
                action,
                TurnJobRecord(
                    job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                    job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
                    job.reasoning_effort, job.input_sha256, job.codex_turn_id, next_job_state,
                    job_version, job.created_at_ms, job_updated, next_job_error,
                ),
                DialogueRecord(
                    dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
                    next_dialogue_state, dialogue_version, dialogue.created_at_ms,
                    dialogue_updated, next_dialogue_error,
                ),
            )

        return await self._storage.write(write)
