"""Narrow repository for the separate UNKNOWN local-containment fact."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from .containment_records import DeleteStorageContainmentRecord
from .core_repositories import MAX_SQLITE_INT, _RepositoryBase, _materialize_dialogue, _validate_clock
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .records import DialogueState
from .sqlite import SqliteStorage

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _state_conflict() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.STATE_CONFLICT)


def _validate_id(value: object) -> str:
    if type(value) is not str or not value or "\x00" in value or len(value) > 128:
        raise _invalid()
    return value


def _validate_version(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _stored_string(value: object, limit: int) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invariant()
    return value


def _stored_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _containment_select() -> str:
    return (
        "SELECT dialogue_id, profile_id, thread_identity_sha256, dialogue_version, "
        "official_delete_authority, local_isolated_storage_containment, contained_at_ms "
        "FROM delete_storage_containment"
    )


def _materialize_containment(row: Any) -> DeleteStorageContainmentRecord:
    if row is None or len(row) != 7:
        raise _invariant()
    dialogue_id = _stored_string(row[0], 128)
    profile_id = _stored_string(row[1], 128)
    thread_hash = row[2]
    if not isinstance(thread_hash, str) or _SHA256_RE.fullmatch(thread_hash) is None:
        raise _invariant()
    dialogue_version = _stored_int(row[3])
    if row[4] != "UNKNOWN" or row[5] != "COMPLETED":
        raise _invariant()
    contained_at_ms = _stored_int(row[6])
    return DeleteStorageContainmentRecord(
        dialogue_id, profile_id, thread_hash, dialogue_version,
        "UNKNOWN", "COMPLETED", contained_at_ms,
    )


def _validate_attached_containment(connection: Any, dialogue_id: str, dialogue: Any) -> DeleteStorageContainmentRecord | None:
    row = connection.execute(
        _containment_select() + " WHERE dialogue_id = ?", (dialogue_id,)
    ).fetchone()
    if row is None:
        return None
    record = _materialize_containment(row)
    if (
        dialogue is None
        or dialogue.state is not DialogueState.DELETE_UNKNOWN
        or dialogue.last_error_class != "DELETE_UNKNOWN"
        or record.dialogue_id != dialogue.dialogue_id
        or record.profile_id != dialogue.profile_id
        or record.dialogue_version != dialogue.version
        or record.thread_identity_sha256 != hashlib.sha256(dialogue.thread_id.encode("utf-8")).hexdigest()
    ):
        raise _invariant()
    if connection.execute(
        "SELECT 1 FROM turn_jobs WHERE dialogue_id = ? AND state IN "
        "('RECEIVED','CLAIMED','CODEX_STARTING','CODEX_RUNNING') LIMIT 1",
        (dialogue_id,),
    ).fetchone() is not None:
        raise _invariant()
    return record


def validate_all_containment_rows(connection: Any) -> None:
    rows = connection.execute(
        _containment_select() + " ORDER BY dialogue_id"
    ).fetchall()
    for row in rows:
        record = _materialize_containment(row)
        dialogue_row = connection.execute(
            "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
            "created_at_ms, updated_at_ms, last_error_class FROM dialogues WHERE dialogue_id = ?",
            (record.dialogue_id,),
        ).fetchone()
        if dialogue_row is None:
            raise _invariant()
        dialogue = _materialize_dialogue(dialogue_row)
        _validate_attached_containment(connection, record.dialogue_id, dialogue)
        if connection.execute(
            "SELECT 1 FROM deletion_tombstones WHERE dialogue_id = ?", (record.dialogue_id,)
        ).fetchone() is not None:
            raise _invariant()


class DeleteStorageContainmentRepository(_RepositoryBase):
    async def get(self, dialogue_id: str) -> DeleteStorageContainmentRecord | None:
        dialogue_id = _validate_id(dialogue_id)

        def read(connection: Any) -> DeleteStorageContainmentRecord | None:
            dialogue_row = connection.execute(
                "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class FROM dialogues WHERE dialogue_id = ?",
                (dialogue_id,),
            ).fetchone()
            if dialogue_row is None:
                if connection.execute(
                    "SELECT 1 FROM delete_storage_containment WHERE dialogue_id = ?", (dialogue_id,)
                ).fetchone() is not None:
                    raise _invariant()
                return None
            return _validate_attached_containment(
                connection, dialogue_id, _materialize_dialogue(dialogue_row)
            )

        return await self._storage.read(read)

    async def mark_unknown_contained(
        self, *, dialogue_id: str, expected_dialogue_version: int
    ) -> DeleteStorageContainmentRecord:
        dialogue_id = _validate_id(dialogue_id)
        expected_dialogue_version = _validate_version(expected_dialogue_version)

        def write(connection: Any) -> DeleteStorageContainmentRecord:
            row = connection.execute(
                "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class FROM dialogues WHERE dialogue_id = ?",
                (dialogue_id,),
            ).fetchone()
            if row is None:
                raise _invariant()
            dialogue = _materialize_dialogue(row)
            if dialogue.version != expected_dialogue_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if dialogue.state is not DialogueState.DELETE_UNKNOWN:
                raise _state_conflict()
            if dialogue.thread_id is None or dialogue.last_error_class != "DELETE_UNKNOWN":
                raise _invariant()
            if connection.execute(
                "SELECT 1 FROM deletion_tombstones WHERE dialogue_id = ?", (dialogue_id,)
            ).fetchone() is not None:
                raise _invariant()
            active = connection.execute(
                "SELECT 1 FROM turn_jobs WHERE dialogue_id = ? AND state IN "
                "('RECEIVED','CLAIMED','CODEX_STARTING','CODEX_RUNNING') LIMIT 1",
                (dialogue_id,),
            ).fetchone()
            if active is not None:
                raise _state_conflict()
            existing = _validate_attached_containment(connection, dialogue_id, dialogue)
            thread_hash = hashlib.sha256(dialogue.thread_id.encode("utf-8")).hexdigest()
            if existing is not None:
                if (
                    existing.profile_id != dialogue.profile_id
                    or existing.dialogue_version != dialogue.version
                    or existing.thread_identity_sha256 != thread_hash
                ):
                    raise _invariant()
                return existing
            now = _validate_clock(self._clock)
            connection.execute(
                "INSERT INTO delete_storage_containment "
                "(dialogue_id, profile_id, thread_identity_sha256, dialogue_version, "
                "official_delete_authority, local_isolated_storage_containment, contained_at_ms) "
                "VALUES (?, ?, ?, ?, 'UNKNOWN', 'COMPLETED', ?)",
                (dialogue_id, dialogue.profile_id, thread_hash, dialogue.version, now),
            )
            return DeleteStorageContainmentRecord(
                dialogue_id, dialogue.profile_id, thread_hash, dialogue.version,
                "UNKNOWN", "COMPLETED", now,
            )

        return await self._storage.write(write)


__all__ = [
    "DeleteStorageContainmentRepository",
    "_materialize_containment",
    "validate_all_containment_rows",
]
