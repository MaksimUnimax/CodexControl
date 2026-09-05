"""P2.4a repositories for atomic turn-job ingress and transient payloads."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any

from .core_repositories import (
    _default_clock,
    _materialize_dialogue,
    _next_version,
    _validate_clock,
)
from .idempotency_repositories import _materialize_ingress
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .records import DialogueRecord, DialogueState
from .sqlite import SqliteStorage
from .transient_payloads import (
    MAX_TRANSIENT_PAYLOAD_BYTES,
    TransientPayloadKind,
    TransientPayloadRecord,
)
from .turn_job_records import (
    TurnExecutionClaimResult,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnJobFinishResult,
    TurnJobRecord,
    TurnJobState,
    TurnTerminalOutcome,
)


MAX_SQLITE_INT = 9223372036854775807
MIN_SQLITE_INT = -9223372036854775808

_ID_LENGTH = 128
_SERVER_ID_LENGTH = 128
_PROFILE_ID_LENGTH = 128
_THREAD_ID_LENGTH = 512
_MODEL_ID_LENGTH = 256
_REASONING_EFFORT_LENGTH = 64
_CODEX_TURN_ID_LENGTH = 512
_ERROR_CLASS_LENGTH = 128
_ERROR_CLASS_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _error(category: RepositoryErrorCategory) -> RepositoryError:
    return RepositoryError(category)


def _invalid() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVALID_ARGUMENT)


def _not_found() -> RepositoryError:
    return _error(RepositoryErrorCategory.NOT_FOUND)


def _invariant() -> RepositoryError:
    return _error(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()
    return value


def _validate_id(value: object) -> str:
    result = _validate_string(value, _ID_LENGTH)
    assert result is not None
    return result


def _validate_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_chat_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT:
        raise _invalid()
    if value == 0:
        raise _invalid()
    return value


def _validate_content(value: object) -> bytes:
    if type(value) is not bytes or not 1 <= len(value) <= MAX_TRANSIENT_PAYLOAD_BYTES:
        raise _invalid()
    return value


def _validate_error_class(value: object) -> str:
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _validate_hash(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invalid()
    return value


def _validate_stored_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invariant()
    return value


def _validate_stored_nonnegative(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _validate_stored_chat_id(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_SQLITE_INT <= value <= MAX_SQLITE_INT:
        raise _invariant()
    if value == 0:
        raise _invariant()
    return value


def _validate_stored_hash(value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _validate_stored_error(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or _ERROR_CLASS_RE.fullmatch(value) is None:
        raise _invariant()
    return value


def _validate_stored_kind(value: object) -> TransientPayloadKind:
    if not isinstance(value, str):
        raise _invariant()
    try:
        return TransientPayloadKind(value)
    except (TypeError, ValueError):
        raise _invariant() from None


def _validate_kind(value: object) -> TransientPayloadKind:
    if not isinstance(value, TransientPayloadKind):
        raise _invalid()
    return value


def _validate_outcome(value: object) -> TurnTerminalOutcome:
    if not isinstance(value, TurnTerminalOutcome):
        raise _invalid()
    return value


def _materialize_job(row: Any) -> TurnJobRecord:
    if row is None or len(row) != 17:
        raise _invariant()
    job_id = _validate_stored_string(row[0], _ID_LENGTH)
    telegram_update_id = _validate_stored_nonnegative(row[1])
    source_chat_id = _validate_stored_chat_id(row[2])
    source_message_id = _validate_stored_nonnegative(row[3])
    dialogue_id = _validate_stored_string(row[4], _ID_LENGTH)
    server_id = _validate_stored_string(row[5], _SERVER_ID_LENGTH)
    profile_id = _validate_stored_string(row[6], _PROFILE_ID_LENGTH)
    thread_id = _validate_stored_string(row[7], _THREAD_ID_LENGTH, nullable=True)
    model_id = _validate_stored_string(row[8], _MODEL_ID_LENGTH, nullable=True)
    reasoning_effort = _validate_stored_string(row[9], _REASONING_EFFORT_LENGTH, nullable=True)
    input_sha256 = _validate_stored_hash(row[10])
    codex_turn_id = _validate_stored_string(row[11], _CODEX_TURN_ID_LENGTH, nullable=True)
    if not isinstance(row[12], str):
        raise _invariant()
    try:
        state = TurnJobState(row[12])
    except (TypeError, ValueError):
        raise _invariant() from None
    version = _validate_stored_nonnegative(row[13])
    created_at_ms = _validate_stored_nonnegative(row[14])
    updated_at_ms = _validate_stored_nonnegative(row[15])
    if updated_at_ms < created_at_ms:
        raise _invariant()
    error_class = _validate_stored_error(row[16])
    assert job_id is not None and dialogue_id is not None and server_id is not None and profile_id is not None
    assert input_sha256 is not None
    return TurnJobRecord(
        job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id,
        server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256,
        codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class,
    )


def _materialize_payload(row: Any) -> TransientPayloadRecord:
    if row is None or len(row) != 9:
        raise _invariant()
    payload_id = _validate_stored_string(row[0], _ID_LENGTH)
    dialogue_id = _validate_stored_string(row[1], _ID_LENGTH, nullable=True)
    job_id = _validate_stored_string(row[2], _ID_LENGTH, nullable=True)
    if dialogue_id is None and job_id is None:
        raise _invariant()
    kind = _validate_stored_kind(row[3])
    content = row[4]
    if type(content) is not bytes or not 1 <= len(content) <= MAX_TRANSIENT_PAYLOAD_BYTES:
        raise _invariant()
    content_sha256 = _validate_stored_hash(row[5])
    byte_length = _validate_stored_nonnegative(row[6])
    if byte_length != len(content) or hashlib.sha256(content).hexdigest() != content_sha256:
        raise _invariant()
    created_at_ms = _validate_stored_nonnegative(row[7])
    expires_at_ms = _validate_stored_nonnegative(row[8])
    if expires_at_ms <= created_at_ms:
        raise _invariant()
    assert payload_id is not None and content_sha256 is not None
    return TransientPayloadRecord(
        payload_id, dialogue_id, job_id, kind, content, content_sha256,
        byte_length, created_at_ms, expires_at_ms,
    )


def _job_select() -> str:
    return (
        "SELECT job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
        "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
        "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class "
        "FROM turn_jobs"
    )


def _payload_select() -> str:
    return (
        "SELECT payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
        "created_at_ms, expires_at_ms FROM transient_payloads"
    )


def _dialogue_row(connection: Any, dialogue_id: str) -> Any:
    return connection.execute(
        "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
        "created_at_ms, updated_at_ms, last_error_class FROM dialogues WHERE dialogue_id = ?",
        (dialogue_id,),
    ).fetchone()


def _job_row(connection: Any, job_id: str) -> Any:
    return connection.execute(_job_select() + " WHERE job_id = ?", (job_id,)).fetchone()


def _payload_row(connection: Any, payload_id: str) -> Any:
    return connection.execute(_payload_select() + " WHERE payload_id = ?", (payload_id,)).fetchone()


def _ingress_row(connection: Any, update_id: int) -> Any:
    return connection.execute(
        "SELECT update_id, received_at_ms, completed_at_ms, disposition "
        "FROM ingress_updates WHERE update_id = ?",
        (update_id,),
    ).fetchone()


def _input_for_job(connection: Any, job: TurnJobRecord) -> TransientPayloadRecord:
    rows = connection.execute(
        _payload_select() + " WHERE job_id = ? AND kind = 'INPUT'", (job.job_id,)
    ).fetchall()
    if not rows:
        raise _not_found()
    if len(rows) != 1:
        raise _invariant()
    payload = _materialize_payload(rows[0])
    if (
        payload.job_id != job.job_id
        or payload.dialogue_id != job.dialogue_id
        or payload.kind is not TransientPayloadKind.INPUT
        or payload.content_sha256 != job.input_sha256
    ):
        raise _invariant()
    return payload


class _RepositoryBase:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class TransientPayloadRepository(_RepositoryBase):
    async def get(self, payload_id: str) -> TransientPayloadRecord | None:
        payload_id = _validate_id(payload_id)

        def read(connection: Any) -> TransientPayloadRecord | None:
            row = _payload_row(connection, payload_id)
            return None if row is None else _materialize_payload(row)

        return await self._storage.read(read)

    async def get_input_for_job(self, job_id: str) -> TransientPayloadRecord:
        job_id = _validate_id(job_id)

        def read(connection: Any) -> TransientPayloadRecord:
            row = _job_row(connection, job_id)
            if row is None:
                raise _not_found()
            return _input_for_job(connection, _materialize_job(row))

        return await self._storage.read(read)

    async def create(
        self,
        *,
        payload_id: str,
        dialogue_id: str | None = None,
        job_id: str | None = None,
        kind: TransientPayloadKind,
        content: bytes,
        expires_at_ms: int,
    ) -> TransientPayloadRecord:
        payload_id = _validate_id(payload_id)
        dialogue_id = _validate_string(dialogue_id, _ID_LENGTH, nullable=True)
        job_id = _validate_string(job_id, _ID_LENGTH, nullable=True)
        if dialogue_id is None and job_id is None:
            raise _invalid()
        kind = _validate_kind(kind)
        if kind is TransientPayloadKind.INPUT:
            raise _invalid()
        content = _validate_content(content)
        expires_at_ms = _validate_nonnegative(expires_at_ms)

        def write(connection: Any) -> TransientPayloadRecord:
            if _payload_row(connection, payload_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)

            dialogue: DialogueRecord | None = None
            if dialogue_id is not None:
                row = _dialogue_row(connection, dialogue_id)
                if row is None:
                    raise _not_found()
                dialogue = _materialize_dialogue(row)

            job: TurnJobRecord | None = None
            if job_id is not None:
                row = _job_row(connection, job_id)
                if row is None:
                    raise _not_found()
                job = _materialize_job(row)

            if dialogue is not None and job is not None and job.dialogue_id != dialogue.dialogue_id:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)

            now = _validate_clock(self._clock)
            if expires_at_ms <= now:
                raise _invalid()
            digest = hashlib.sha256(content).hexdigest()
            byte_length = len(content)
            connection.execute(
                "INSERT INTO transient_payloads "
                "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                "created_at_ms, expires_at_ms) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (payload_id, dialogue_id, job_id, kind.value, content, digest, byte_length, now, expires_at_ms),
            )
            return TransientPayloadRecord(
                payload_id, dialogue_id, job_id, kind, content, digest, byte_length, now, expires_at_ms
            )

        return await self._storage.write(write)


class TurnJobRepository(_RepositoryBase):
    async def get(self, job_id: str) -> TurnJobRecord | None:
        job_id = _validate_id(job_id)

        def read(connection: Any) -> TurnJobRecord | None:
            row = _job_row(connection, job_id)
            return None if row is None else _materialize_job(row)

        return await self._storage.read(read)

    async def claim_ingress(
        self,
        *,
        update_id: int,
        job_id: str,
        source_chat_id: int,
        source_message_id: int,
        dialogue_id: str,
        server_id: str,
        profile_id: str,
        thread_id: str | None,
        model_id: str | None,
        reasoning_effort: str | None,
        input_payload_id: str,
        input_content: bytes,
        input_expires_at_ms: int,
    ) -> TurnIngressClaimResult:
        update_id = _validate_nonnegative(update_id)
        job_id = _validate_id(job_id)
        source_chat_id = _validate_chat_id(source_chat_id)
        source_message_id = _validate_nonnegative(source_message_id)
        dialogue_id = _validate_id(dialogue_id)
        server_id = _validate_string(server_id, _SERVER_ID_LENGTH)
        profile_id = _validate_string(profile_id, _PROFILE_ID_LENGTH)
        thread_id = _validate_string(thread_id, _THREAD_ID_LENGTH, nullable=True)
        model_id = _validate_string(model_id, _MODEL_ID_LENGTH, nullable=True)
        reasoning_effort = _validate_string(reasoning_effort, _REASONING_EFFORT_LENGTH, nullable=True)
        input_payload_id = _validate_id(input_payload_id)
        input_content = _validate_content(input_content)
        input_expires_at_ms = _validate_nonnegative(input_expires_at_ms)
        assert server_id is not None and profile_id is not None

        def write(connection: Any) -> TurnIngressClaimResult:
            existing_ingress_row = _ingress_row(connection, update_id)
            if existing_ingress_row is not None:
                ingress = _materialize_ingress(existing_ingress_row)
                if ingress.disposition.value == "JOB":
                    assert ingress.job_id is not None
                    job_row = _job_row(connection, ingress.job_id)
                    if job_row is None:
                        raise _invariant()
                    job = _materialize_job(job_row)
                    if job.telegram_update_id != update_id or job.job_id != ingress.job_id:
                        raise _invariant()
                    payload = _input_for_job(connection, job)
                    return TurnIngressClaimResult(
                        TurnIngressClaimStatus.DUPLICATE, ingress, job, payload
                    )
                return TurnIngressClaimResult(
                    TurnIngressClaimStatus.DUPLICATE, ingress, None, None
                )

            if _job_row(connection, job_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)
            if _payload_row(connection, input_payload_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)

            dialogue_row = _dialogue_row(connection, dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            if dialogue.server_id != server_id or dialogue.profile_id != profile_id:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if dialogue.state is DialogueState.CREATING:
                if dialogue.thread_id is not None or thread_id is not None:
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            elif dialogue.state is DialogueState.IDLE:
                if dialogue.thread_id is None or thread_id != dialogue.thread_id:
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            else:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)

            outstanding = connection.execute(
                "SELECT 1 FROM turn_jobs WHERE dialogue_id = ? AND state = 'RECEIVED' LIMIT 1",
                (dialogue_id,),
            ).fetchone()
            if outstanding is not None:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)

            now = _validate_clock(self._clock)
            if input_expires_at_ms <= now:
                raise _invalid()
            digest = hashlib.sha256(input_content).hexdigest()
            byte_length = len(input_content)
            connection.execute(
                "INSERT INTO turn_jobs "
                "(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
                "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
                "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0, ?, ?, NULL)",
                (
                    job_id, update_id, source_chat_id, source_message_id, dialogue_id,
                    server_id, profile_id, thread_id, model_id, reasoning_effort,
                    digest, TurnJobState.RECEIVED.value, now, now,
                ),
            )
            connection.execute(
                "INSERT INTO transient_payloads "
                "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                "created_at_ms, expires_at_ms) VALUES (?, ?, ?, 'INPUT', ?, ?, ?, ?, ?)",
                (input_payload_id, dialogue_id, job_id, input_content, digest, byte_length, now, input_expires_at_ms),
            )
            disposition = "JOB:" + job_id
            connection.execute(
                "INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition) "
                "VALUES (?, ?, ?, ?)",
                (update_id, now, now, disposition),
            )
            job = _materialize_job(
                (job_id, update_id, source_chat_id, source_message_id, dialogue_id,
                 server_id, profile_id, thread_id, model_id, reasoning_effort, digest,
                 None, TurnJobState.RECEIVED.value, 0, now, now, None)
            )
            payload = TransientPayloadRecord(
                input_payload_id, dialogue_id, job_id, TransientPayloadKind.INPUT,
                input_content, digest, byte_length, now, input_expires_at_ms,
            )
            ingress = _materialize_ingress((update_id, now, now, disposition))
            return TurnIngressClaimResult(TurnIngressClaimStatus.CREATED, ingress, job, payload)

        return await self._storage.write(write)

    async def claim_turn(
        self,
        *,
        job_id: str,
        expected_job_version: int,
        expected_dialogue_version: int,
        thread_id: str,
    ) -> TurnExecutionClaimResult:
        job_id = _validate_id(job_id)
        expected_job_version = _validate_nonnegative(expected_job_version)
        expected_dialogue_version = _validate_nonnegative(expected_dialogue_version)
        thread_id = _validate_string(thread_id, _THREAD_ID_LENGTH)
        assert thread_id is not None

        def write(connection: Any) -> TurnExecutionClaimResult:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if job.version != expected_job_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.RECEIVED:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            dialogue_row = _dialogue_row(connection, job.dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            if dialogue.version != expected_dialogue_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if dialogue.state is not DialogueState.IDLE:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if (
                dialogue.server_id != job.server_id
                or dialogue.profile_id != job.profile_id
                or dialogue.thread_id is None
                or dialogue.thread_id != thread_id
                or (job.thread_id is not None and job.thread_id != thread_id)
            ):
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            ingress_row = _ingress_row(connection, job.telegram_update_id)
            if ingress_row is None:
                raise _invariant()
            ingress = _materialize_ingress(ingress_row)
            if ingress.disposition.value != "JOB" or ingress.job_id != job.job_id:
                raise _invariant()
            _input_for_job(connection, job)

            job_version = _next_version(job.version)
            dialogue_version = _next_version(dialogue.version)
            now = _validate_clock(self._clock)
            job_updated = max(now, job.updated_at_ms)
            dialogue_updated = max(now, dialogue.updated_at_ms)
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ?, thread_id = ? "
                "WHERE job_id = ? AND version = ? AND state = ?",
                (TurnJobState.CLAIMED.value, job_version, job_updated, thread_id,
                 job.job_id, job.version, TurnJobState.RECEIVED.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ? "
                "WHERE dialogue_id = ? AND version = ? AND state = ?",
                (DialogueState.TURN_RUNNING.value, dialogue_version, dialogue_updated,
                 dialogue.dialogue_id, dialogue.version, DialogueState.IDLE.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return TurnExecutionClaimResult(
                TurnJobRecord(
                    job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                    job.dialogue_id, job.server_id, job.profile_id, thread_id, job.model_id,
                    job.reasoning_effort, job.input_sha256, job.codex_turn_id,
                    TurnJobState.CLAIMED, job_version, job.created_at_ms, job_updated, job.error_class,
                ),
                DialogueRecord(
                    dialogue.dialogue_id, dialogue.server_id, dialogue.profile_id, dialogue.thread_id,
                    DialogueState.TURN_RUNNING, dialogue_version, dialogue.created_at_ms,
                    dialogue_updated, dialogue.last_error_class,
                ),
            )

        return await self._storage.write(write)

    async def mark_codex_starting(self, *, job_id: str, expected_version: int) -> TurnJobRecord:
        job_id = _validate_id(job_id)
        expected_version = _validate_nonnegative(expected_version)

        def write(connection: Any) -> TurnJobRecord:
            row = _job_row(connection, job_id)
            if row is None:
                raise _not_found()
            job = _materialize_job(row)
            if job.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.CLAIMED or job.codex_turn_id is not None:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            version = _next_version(job.version)
            now = _validate_clock(self._clock)
            updated = max(now, job.updated_at_ms)
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ? "
                "WHERE job_id = ? AND version = ? AND state = ? AND codex_turn_id IS NULL",
                (TurnJobState.CODEX_STARTING.value, version, updated, job.job_id,
                 job.version, TurnJobState.CLAIMED.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return TurnJobRecord(
                job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
                job.reasoning_effort, job.input_sha256, None, TurnJobState.CODEX_STARTING,
                version, job.created_at_ms, updated, job.error_class,
            )

        return await self._storage.write(write)

    async def mark_codex_running(
        self, *, job_id: str, expected_version: int, codex_turn_id: str
    ) -> TurnJobRecord:
        job_id = _validate_id(job_id)
        expected_version = _validate_nonnegative(expected_version)
        codex_turn_id = _validate_string(codex_turn_id, _CODEX_TURN_ID_LENGTH)
        assert codex_turn_id is not None

        def write(connection: Any) -> TurnJobRecord:
            row = _job_row(connection, job_id)
            if row is None:
                raise _not_found()
            job = _materialize_job(row)
            if job.version != expected_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if job.state is not TurnJobState.CODEX_STARTING or job.codex_turn_id is not None:
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            version = _next_version(job.version)
            now = _validate_clock(self._clock)
            updated = max(now, job.updated_at_ms)
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, codex_turn_id = ?, version = ?, updated_at_ms = ? "
                "WHERE job_id = ? AND version = ? AND state = ? AND codex_turn_id IS NULL",
                (TurnJobState.CODEX_RUNNING.value, codex_turn_id, version, updated,
                 job.job_id, job.version, TurnJobState.CODEX_STARTING.value),
            ).rowcount
            if changed != 1:
                raise _invariant()
            return TurnJobRecord(
                job.job_id, job.telegram_update_id, job.source_chat_id, job.source_message_id,
                job.dialogue_id, job.server_id, job.profile_id, job.thread_id, job.model_id,
                job.reasoning_effort, job.input_sha256, codex_turn_id, TurnJobState.CODEX_RUNNING,
                version, job.created_at_ms, updated, job.error_class,
            )

        return await self._storage.write(write)

    async def finish_codex(
        self,
        *,
        job_id: str,
        expected_job_version: int,
        expected_dialogue_version: int,
        outcome: TurnTerminalOutcome,
        error_class: str | None = None,
        output_payload_id: str | None = None,
        output_content: bytes | None = None,
        output_expires_at_ms: int | None = None,
    ) -> TurnJobFinishResult:
        job_id = _validate_id(job_id)
        expected_job_version = _validate_nonnegative(expected_job_version)
        expected_dialogue_version = _validate_nonnegative(expected_dialogue_version)
        outcome = _validate_outcome(outcome)
        if outcome is TurnTerminalOutcome.COMPLETED:
            if error_class is not None:
                raise _invalid()
        else:
            if error_class is None:
                raise _invalid()
            error_class = _validate_error_class(error_class)
        output_values = (output_payload_id, output_content, output_expires_at_ms)
        if any(value is None for value in output_values) and not all(value is None for value in output_values):
            raise _invalid()
        if output_payload_id is not None:
            output_payload_id = _validate_id(output_payload_id)
            output_content = _validate_content(output_content)
            output_expires_at_ms = _validate_nonnegative(output_expires_at_ms)
        assert error_class is None or isinstance(error_class, str)

        def write(connection: Any) -> TurnJobFinishResult:
            job_row = _job_row(connection, job_id)
            if job_row is None:
                raise _not_found()
            job = _materialize_job(job_row)
            if job.version != expected_job_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            dialogue_row = _dialogue_row(connection, job.dialogue_id)
            if dialogue_row is None:
                raise _not_found()
            dialogue = _materialize_dialogue(dialogue_row)
            if dialogue.version != expected_dialogue_version:
                raise _error(RepositoryErrorCategory.VERSION_CONFLICT)
            if (
                dialogue.dialogue_id != job.dialogue_id
                or dialogue.server_id != job.server_id
                or dialogue.profile_id != job.profile_id
                or dialogue.thread_id is None
                or job.thread_id is None
                or dialogue.thread_id != job.thread_id
                or dialogue.state is not DialogueState.TURN_RUNNING
            ):
                raise _error(RepositoryErrorCategory.STATE_CONFLICT)
            if outcome is TurnTerminalOutcome.COMPLETED:
                if job.state is not TurnJobState.CODEX_RUNNING:
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
                next_job_state = TurnJobState.CODEX_COMPLETED
                next_dialogue_state = DialogueState.IDLE
                next_error = None
            elif outcome is TurnTerminalOutcome.FAILED:
                if job.state not in (TurnJobState.CODEX_STARTING, TurnJobState.CODEX_RUNNING):
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
                next_job_state = TurnJobState.FAILED
                next_dialogue_state = DialogueState.ERROR
                next_error = error_class
            else:
                if job.state not in (TurnJobState.CODEX_STARTING, TurnJobState.CODEX_RUNNING):
                    raise _error(RepositoryErrorCategory.STATE_CONFLICT)
                next_job_state = TurnJobState.UNKNOWN
                next_dialogue_state = DialogueState.TURN_UNKNOWN
                next_error = error_class

            job_version = _next_version(job.version)
            dialogue_version = _next_version(dialogue.version)
            if output_payload_id is not None and _payload_row(connection, output_payload_id) is not None:
                raise _error(RepositoryErrorCategory.ALREADY_EXISTS)
            now = _validate_clock(self._clock)
            output_payload: TransientPayloadRecord | None = None
            if output_payload_id is not None:
                assert output_content is not None and output_expires_at_ms is not None
                if output_expires_at_ms <= now:
                    raise _invalid()
                digest = hashlib.sha256(output_content).hexdigest()
                byte_length = len(output_content)
                connection.execute(
                    "INSERT INTO transient_payloads "
                    "(payload_id, dialogue_id, job_id, kind, content, content_sha256, byte_length, "
                    "created_at_ms, expires_at_ms) VALUES (?, ?, ?, 'OUTPUT', ?, ?, ?, ?, ?)",
                    (output_payload_id, dialogue.dialogue_id, job.job_id, output_content,
                     digest, byte_length, now, output_expires_at_ms),
                )
                output_payload = TransientPayloadRecord(
                    output_payload_id, dialogue.dialogue_id, job.job_id,
                    TransientPayloadKind.OUTPUT, output_content, digest, byte_length, now, output_expires_at_ms,
                )
            job_updated = max(now, job.updated_at_ms)
            dialogue_updated = max(now, dialogue.updated_at_ms)
            changed = connection.execute(
                "UPDATE turn_jobs SET state = ?, version = ?, updated_at_ms = ?, error_class = ? "
                "WHERE job_id = ? AND version = ?",
                (next_job_state.value, job_version, job_updated, next_error,
                 job.job_id, job.version),
            ).rowcount
            if changed != 1:
                raise _invariant()
            changed = connection.execute(
                "UPDATE dialogues SET state = ?, version = ?, updated_at_ms = ?, last_error_class = ? "
                "WHERE dialogue_id = ? AND version = ?",
                (next_dialogue_state.value, dialogue_version, dialogue_updated, next_error,
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
                    next_dialogue_state, dialogue_version, dialogue.created_at_ms,
                    dialogue_updated, next_error,
                ),
                output_payload,
            )

        return await self._storage.write(write)
