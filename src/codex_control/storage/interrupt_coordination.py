"""Additive, schema-v1 coordination for durable turn interruption."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from typing import Any

from .core_repositories import (
    MAX_SQLITE_INT,
    _default_clock,
    _materialize_dialogue,
    _next_version,
    _validate_clock,
)
from .idempotency_repositories import _materialize_ingress
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage
from .transient_payloads import TransientPayloadKind, TransientPayloadRecord
from .turn_job_records import (
    DialogueRecord,
    TurnJobRecord,
    TurnJobState,
    TurnTerminalOutcome,
    TurnJobFinishResult,
)
from .records import DialogueState
from .turn_job_repositories import (
    MAX_TRANSIENT_PAYLOAD_BYTES,
    _dialogue_row,
    _ingress_row,
    _input_for_job,
    _job_row,
    _job_select,
    _materialize_job,
    _materialize_payload,
    _payload_row,
)


_ID_LENGTH = 128
_THREAD_ID_LENGTH = 512
_CODEX_TURN_ID_LENGTH = 512
_SERVER_ID_LENGTH = 128
_PROFILE_ID_LENGTH = 128
_ERROR_CLASS_LENGTH = 128


def _error(category: RepositoryErrorCategory) -> RepositoryError:
    return RepositoryError(category)


def _invalid() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVALID_ARGUMENT)


def _not_found() -> RepositoryError:
    return _error(RepositoryErrorCategory.NOT_FOUND)


def _state_conflict() -> RepositoryError:
    return _error(RepositoryErrorCategory.STATE_CONFLICT)


def _version_conflict() -> RepositoryError:
    return _error(RepositoryErrorCategory.VERSION_CONFLICT)


def _invariant() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_id(value: object, limit: int = _ID_LENGTH) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()
    return value


def _validate_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_clock_value(clock: Callable[[], int]) -> int:
    return _validate_clock(clock)


def _validate_payload_args(
    outcome: TurnTerminalOutcome,
    error_class: str | None,
    output_payload_id: str | None,
    output_content: bytes | None,
    output_expires_at_ms: int | None,
) -> tuple[str | None, bytes | None, int | None]:
    if not isinstance(outcome, TurnTerminalOutcome):
        raise _invalid()
    if outcome is TurnTerminalOutcome.COMPLETED:
        if error_class is not None:
            raise _invalid()
    elif outcome is TurnTerminalOutcome.FAILED:
        if error_class != "CODEX_TURN_FAILED":
            raise _invalid()
    elif outcome is TurnTerminalOutcome.UNKNOWN:
        if error_class != "CODEX_AMBIGUOUS":
            raise _invalid()
    else:
        raise _invalid()
    values = (output_payload_id, output_content, output_expires_at_ms)
    if any(value is None for value in values) and not all(value is None for value in values):
        raise _invalid()
    if output_payload_id is not None:
        output_payload_id = _validate_id(output_payload_id)
        if type(output_content) is not bytes or not 1 <= len(output_content) <= MAX_TRANSIENT_PAYLOAD_BYTES:
            raise _invalid()
        if isinstance(output_expires_at_ms, bool) or not isinstance(output_expires_at_ms, int):
            raise _invalid()
        if not 0 <= output_expires_at_ms <= MAX_SQLITE_INT:
            raise _invalid()
    return output_payload_id, output_content, output_expires_at_ms


def _validate_owner_in_transaction(connection: Any, dialogue: DialogueRecord, job: TurnJobRecord) -> None:
    if (
        dialogue.dialogue_id != job.dialogue_id
        or dialogue.server_id != job.server_id
        or dialogue.profile_id != job.profile_id
        or dialogue.thread_id is None
        or job.thread_id is None
        or dialogue.thread_id != job.thread_id
        or job.codex_turn_id is None
    ):
        raise _invariant()
    ingress_row = _ingress_row(connection, job.telegram_update_id)
    if ingress_row is None:
        raise _invariant()
    ingress = _materialize_ingress(ingress_row)
    if ingress.disposition.value != "JOB" or ingress.job_id != job.job_id:
        raise _invariant()
    _input_for_job(connection, job, missing_category=RepositoryErrorCategory.INVARIANT_VIOLATION)


def _dialogue_row_for_id(connection: Any, dialogue_id: str) -> Any:
    return _dialogue_row(connection, dialogue_id)


def _finish_records(
    connection: Any,
    job: TurnJobRecord,
    dialogue: DialogueRecord,
    next_job_state: TurnJobState,
    next_dialogue_state: DialogueState,
    next_error: str | None,
    job_version: int,
    dialogue_version: int,
    now: int,
    output_payload: TransientPayloadRecord | None,
) -> TurnJobFinishResult:
    job_updated = max(now, job.updated_at_ms)
    dialogue_updated = max(now, dialogue.updated_at_ms)
    changed = connection.execute(
        "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ?, error_class = ? "
        "WHERE job_id = ? AND version = ?",
        (next_job_state.value, job_version, job_updated, next_error, job.job_id, job.version),
    ).rowcount
    if changed != 1:
        raise _invariant()
    changed = connection.execute(
        "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, last_error_class = ? "
        "WHERE dialogue_id = ? AND version = ?",
        (next_dialogue_state.value, dialogue_version, dialogue_updated,
         None if next_dialogue_state is DialogueState.IDLE else next_error,
         dialogue.dialogue_id, dialogue.version),
    ).rowcount
    if changed != 1:
        raise _invariant()
    return TurnJobFinishResult(
        TurnJobRecord(
            job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
            job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
            job.reasoning_effort, job.input_sha256, job.codex_turn_id, next_job_state,
            job_version, job.created_at_ms, job_updated, next_error,
        ),
        DialogueRecord(
            dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
            next_dialogue_state, dialogue_version, dialogue.created_at_ms, dialogue_updated,
            None if next_dialogue_state is DialogueState.IDLE else next_error,
        ),
        output_payload,
    )


def _existing_output(connection: Any, job: TurnJobRecord) -> TransientPayloadRecord | None:
    rows = connection.execute(
        "SELECT payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
        "created_at_ms, expires_at_ms FROM transient_payloads WHERE job_id = ? AND kind = 'OUTPUT'",
        (job.job_id,),
    ).fetchall()
    if len(rows) > 1:
        raise _invariant()
    return None if not rows else _materialize_payload(connection, rows[0])


class InterruptCoordinationRepository:
    """Atomic interrupt claims, terminalization, and startup recovery."""

    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<InterruptCoordinationRepository>"

    async def claim_interrupt(
        self,
        *,
        dialogue_id: str,
        job_id: str,
        expected_dialogue_version: int,
        expected_job_version: int,
    ) -> TurnJobFinishResult:
        dialogue_id = _validate_id(dialogue_id)
        job_id = _validate_id(job_id)
        expected_dialogue_version = _validate_version(expected_dialogue_version)
        expected_job_version = _validate_version(expected_job_version)

        def write(connection: Any) -> TurnJobFinishResult:
            dialogue_row = _dialogue_row_for_id(connection, dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if dialogue.version != expected_dialogue_version:
                raise _version_conflict()
            if job.version != expected_job_version:
                raise _version_conflict()
            if dialogue.state is not DialogueState.TURN_RUNNING:
                raise _state_conflict()
            if dialogue.thread_id is None or dialogue.last_error_class is not None:
                raise _invariant()
            if job.state is not TurnJobState.CODEX_RUNNING:
                raise _state_conflict()
            _validate_owner_in_transaction(connection, dialogue, job)
            version = _next_version(dialogue.version)
            now = _validate_clock_value(self._clock)
            updated = max(now, dialogue.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ? "
                "WHERE dialogue_id = ? AND state = ? AND version = ?",
                (DialogueState.INTERRUPTING.value, version, updated, dialogue.dialogue_id,
                 DialogueState.TURN_RUNNING.value, dialogue.version),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return TurnJobFinishResult(
                job,
                DialogueRecord(
                    dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
                    DialogueState.INTERRUPTING, version, dialogue.created_at_ms, updated,
                    dialogue.last_error_class,
                ),
                None,
            )

        return await self._storage.write(write)

    async def restore_rejected_interrupt(
        self,
        *,
        dialogue_id: str,
        job_id: str,
        claimed_dialogue_version: int,
        expected_job_version: int,
    ) -> TurnJobFinishResult:
        dialogue_id = _validate_id(dialogue_id)
        job_id = _validate_id(job_id)
        claimed_dialogue_version = _validate_version(claimed_dialogue_version)
        expected_job_version = _validate_version(expected_job_version)

        def write(connection: Any) -> TurnJobFinishResult:
            dialogue_row = _dialogue_row_for_id(connection, dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if dialogue.version != claimed_dialogue_version or job.version != expected_job_version:
                raise _version_conflict()
            if dialogue.state is not DialogueState.INTERRUPTING or job.state is not TurnJobState.CODEX_RUNNING:
                raise _state_conflict()
            _validate_owner_in_transaction(connection, dialogue, job)
            version = _next_version(dialogue.version)
            now = _validate_clock_value(self._clock)
            updated = max(now, dialogue.updated_at_ms)
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, last_error_class = NULL "
                "WHERE dialogue_id = ? AND state = ? AND version = ?",
                (DialogueState.TURN_RUNNING.value, version, updated, dialogue.dialogue_id,
                 DialogueState.INTERRUPTING.value, dialogue.version),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return TurnJobFinishResult(
                job,
                DialogueRecord(
                    dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
                    DialogueState.TURN_RUNNING, version, dialogue.created_at_ms, updated, None,
                ),
                None,
            )

        return await self._storage.write(write)

    async def terminalize_interrupt(self, **kwargs: object) -> TurnJobFinishResult:
        return await self._reconcile_terminal(mode="interrupt", **kwargs)

    async def reconcile_natural_terminal(self, **kwargs: object) -> TurnJobFinishResult:
        return await self._reconcile_terminal(mode="natural", **kwargs)

    async def _reconcile_terminal(self, *, mode: str, **kwargs: object) -> TurnJobFinishResult:
        if mode not in ("interrupt", "natural"):
            raise _invalid()
        dialogue_id = _validate_id(kwargs.pop("dialogue_id", None))
        job_id = _validate_id(kwargs.pop("job_id", None))
        profile_id = _validate_id(kwargs.pop("profile_id", None), _PROFILE_ID_LENGTH)
        thread_id = _validate_id(kwargs.pop("thread_id", None), _THREAD_ID_LENGTH)
        codex_turn_id = _validate_id(kwargs.pop("codex_turn_id", None), _CODEX_TURN_ID_LENGTH)
        claimed_version = kwargs.pop("claimed_dialogue_version", None)
        base_version = kwargs.pop("base_dialogue_version", None)
        if mode == "interrupt":
            base_dialogue_version = _validate_version(claimed_version)
            interrupt_dialogue_version = base_dialogue_version
            terminal_versions = (base_dialogue_version + 1, base_dialogue_version + 2)
        else:
            base_dialogue_version = _validate_version(base_version)
            interrupt_dialogue_version = base_dialogue_version + 1
            terminal_versions = (base_dialogue_version + 2, base_dialogue_version + 3)
        expected_job_version = _validate_version(kwargs.pop("expected_job_version", None))
        outcome = kwargs.pop("outcome", None)
        error_class = kwargs.pop("error_class", None)
        output_payload_id, output_content, output_expires_at_ms = _validate_payload_args(
            outcome, error_class, kwargs.pop("output_payload_id", None),
            kwargs.pop("output_content", None), kwargs.pop("output_expires_at_ms", None),
        )
        if kwargs:
            raise _invalid()

        def write(connection: Any) -> TurnJobFinishResult:
            dialogue_row = _dialogue_row_for_id(connection, dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if (
                job.version < expected_job_version
                or job.job_id != job_id
                or job.dialogue_id != dialogue_id
                or job.profile_id != profile_id
                or job.thread_id != thread_id
                or job.codex_turn_id != codex_turn_id
            ):
                raise _invariant()
            if dialogue.profile_id != profile_id or dialogue.thread_id != thread_id:
                raise _invariant()
            # A terminal result committed by the other owner is reconstructable
            # only in the two exact interrupt-induced version shapes.
            if job.version == expected_job_version + 1 and dialogue.version in terminal_versions \
                    and job.state in (TurnJobState.CODEX_COMPLETED, TurnJobState.FAILED, TurnJobState.UNKNOWN):
                ingress_row = _ingress_row(connection, job.telegram_update_id)
                if ingress_row is None:
                    raise _invariant()
                ingress = _materialize_ingress(ingress_row)
                if ingress.disposition.value != "JOB" or ingress.job_id != job.job_id:
                    raise _invariant()
                if job.state is TurnJobState.CODEX_COMPLETED and dialogue.state is not DialogueState.IDLE:
                    raise _invariant()
                if job.state is TurnJobState.UNKNOWN and dialogue.state is not DialogueState.TURN_UNKNOWN:
                    raise _invariant()
                if job.state is TurnJobState.FAILED and dialogue.state not in (DialogueState.IDLE, DialogueState.ERROR):
                    raise _invariant()
                if (
                    job.dialogue_id != dialogue.dialogue_id
                    or job.server_id != dialogue.server_id
                    or job.profile_id != dialogue.profile_id
                    or job.thread_id is None
                    or dialogue.thread_id != job.thread_id
                    or job.codex_turn_id is None
                ):
                    raise _invariant()
                if job.state is TurnJobState.FAILED:
                    if dialogue.state is DialogueState.ERROR and dialogue.version != terminal_versions[-1]:
                        raise _invariant()
                    if dialogue.state is DialogueState.IDLE and dialogue.version != terminal_versions[0]:
                        raise _invariant()
                return TurnJobFinishResult(job, dialogue, _existing_output(connection, job))

            if job.version != expected_job_version or dialogue.version == MAX_SQLITE_INT:
                raise _state_conflict()
            if dialogue.state is DialogueState.INTERRUPTING:
                if dialogue.version != interrupt_dialogue_version:
                    raise _state_conflict()
                terminal_mode = "interrupt"
            elif dialogue.state is DialogueState.TURN_RUNNING:
                if mode != "natural" or dialogue.version != base_dialogue_version + 2:
                    raise _state_conflict()
                terminal_mode = "natural"
            else:
                raise _state_conflict()
            _validate_owner_in_transaction(connection, dialogue, job)
            if job.state is not TurnJobState.CODEX_RUNNING:
                raise _state_conflict()
            if terminal_mode == "interrupt" and mode != "interrupt":
                # The natural runner may finalize the exact interrupt claim;
                # this is the one narrow race fallback permitted by ADR-0030.
                pass
            elif terminal_mode == "interrupt" and mode == "interrupt":
                pass

            next_job_state = {
                TurnTerminalOutcome.COMPLETED: TurnJobState.CODEX_COMPLETED,
                TurnTerminalOutcome.FAILED: TurnJobState.FAILED,
                TurnTerminalOutcome.UNKNOWN: TurnJobState.UNKNOWN,
            }[outcome]
            if outcome is TurnTerminalOutcome.COMPLETED:
                next_dialogue_state = DialogueState.IDLE
                next_error = None
            elif outcome is TurnTerminalOutcome.FAILED:
                next_dialogue_state = DialogueState.IDLE if terminal_mode == "interrupt" else DialogueState.ERROR
                next_error = "CODEX_TURN_FAILED"
            else:
                next_dialogue_state = DialogueState.TURN_UNKNOWN
                next_error = "CODEX_AMBIGUOUS"
            if next_job_state is TurnJobState.CODEX_COMPLETED and next_error is not None:
                raise _invariant()
            if output_payload_id is not None and _payload_row(connection, output_payload_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)
            now = _validate_clock_value(self._clock)
            output_payload = None
            if output_payload_id is not None:
                assert output_content is not None and output_expires_at_ms is not None
                if output_expires_at_ms <= now:
                    raise _invalid()
                digest = hashlib.sha256(output_content).hexdigest()
                connection.execute(
                    "INSERT INTO transient_payloads "
                    "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                    "created_at_ms, expires_at_ms) VALUES (?, ?, ?, 'OUTPUT', ?, ?, ?, ?, ?)",
                    (output_payload_id, dialogue_id, job_id, output_content, digest, len(output_content), now,
                     output_expires_at_ms),
                )
                output_payload = TransientPayloadRecord(
                    output_payload_id, dialogue_id, job_id, TransientPayloadKind.OUTPUT,
                    output_content, digest, len(output_content), now, output_expires_at_ms,
                )
            return _finish_records(
                connection, job, dialogue, next_job_state, next_dialogue_state, next_error,
                _next_version(job.version), _next_version(dialogue.version), now, output_payload,
            )

        return await self._storage.write(write)

    async def recover_preexisting_interrupt(self) -> TurnJobFinishResult | None:
        def write(connection: Any) -> TurnJobFinishResult | None:
            rows = connection.execute(
                "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class FROM dialogues"
            ).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                raise _invariant()
            dialogue = _materialize_dialogue(rows[0])
            if dialogue.state is not DialogueState.INTERRUPTING:
                return None
            job_rows = connection.execute(
                _job_select() + " WHERE dialogue_id = ? AND state = 'CODEX_RUNNING'",
                (dialogue.dialogue_id,),
            ).fetchall()
            if len(job_rows) != 1:
                raise _invariant()
            job = _materialize_job(job_rows[0])
            _validate_owner_in_transaction(connection, dialogue, job)
            job_version = _next_version(job.version)
            dialogue_version = _next_version(dialogue.version)
            now = _validate_clock_value(self._clock)
            job_updated = max(now, job.updated_at_ms)
            dialogue_updated = max(now, dialogue.updated_at_ms)
            if connection.execute(
                "UPDATE turn_jobs SET state = 'UNKNOWN', version = ?, updated_at_ms = ?, "
                "error_class = 'CODEX_AMBIGUOUS' WHERE job_id = ? AND state = 'CODEX_RUNNING' AND version = ?",
                (job_version, job_updated, job.job_id, job.version),
            ).rowcount != 1:
                raise _invariant()
            if connection.execute(
                "UPDATE dialogues SET state = 'TURN_UNKNOWN', version = ?, updated_at_ms = ?, "
                "last_error_class = 'CODEX_AMBIGUOUS' WHERE dialogue_id = ? AND state = 'INTERRUPTING' AND version = ?",
                (dialogue_version, dialogue_updated, dialogue.dialogue_id, dialogue.version),
            ).rowcount != 1:
                raise _invariant()
            return TurnJobFinishResult(
                TurnJobRecord(
                    job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                    job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
                    job.reasoning_effort, job.input_sha256, job.codex_turn_id, TurnJobState.UNKNOWN,
                    job_version, job.created_at_ms, job_updated, "CODEX_AMBIGUOUS",
                ),
                DialogueRecord(
                    dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
                    DialogueState.TURN_UNKNOWN, dialogue_version, dialogue.created_at_ms,
                    dialogue_updated, "CODEX_AMBIGUOUS",
                ),
                None,
            )

        return await self._storage.write(write)
