"""Atomic settings/dialogue coordination primitives for P3.3."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .core_repositories import (
    _DIALOGUE_ID_LENGTH as MAX_DIALOGUE_ID_LENGTH,
    _MODEL_ID_LENGTH as MAX_MODEL_ID_LENGTH,
    _PROFILE_ID_LENGTH as MAX_PROFILE_ID_LENGTH,
    _REASONING_EFFORT_LENGTH as MAX_REASONING_EFFORT_LENGTH,
    _SERVER_ID_LENGTH as MAX_SERVER_ID_LENGTH,
    _materialize_dialogue,
    _materialize_settings,
    _next_version,
    _singleton_row,
    _validate_clock,
    _validate_expected_version,
    _validate_string,
)
from .records import DialogueRecord, DialogueState, SettingsRecord
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _settings_row(connection: Any) -> Any:
    return _singleton_row(
        connection,
        "SELECT singleton, profile_id, model_id, reasoning_effort, version, "
        "created_at_ms, updated_at_ms FROM settings",
    )


def _dialogue_row(connection: Any) -> Any:
    rows = connection.execute(
        "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
        "created_at_ms, updated_at_ms, last_error_class FROM dialogues"
    ).fetchall()
    if len(rows) > 1:
        raise _invariant()
    return rows[0] if rows else None


def _validate_required(value: object, limit: int) -> str:
    normalized = _validate_string(value, limit)
    if normalized is None:
        raise _invalid()
    return normalized


class SettingsDialogueGuardRepository:
    """One-transaction settings mutations and first-dialogue coordination."""

    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<SettingsDialogueGuardRepository>"

    async def replace_profile_no_dialogue(
        self,
        *,
        expected_version: int,
        profile_id: str,
    ) -> SettingsRecord:
        expected_version = _validate_expected_version(expected_version)
        profile_id = _validate_required(profile_id, MAX_PROFILE_ID_LENGTH)

        def write(connection: Any) -> SettingsRecord:
            row = _settings_row(connection)
            if row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            current = _materialize_settings(row)
            if current.version != expected_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            dialogue_row = _dialogue_row(connection)
            if dialogue_row is not None:
                _materialize_dialogue(dialogue_row)
                raise RepositoryError(RepositoryErrorCategory.STATE_CONFLICT)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE settings SET profile_id = ?, model_id = NULL, reasoning_effort = NULL, "
                "version = ?, updated_at_ms = ? WHERE singleton = 1 AND version = ?",
                (profile_id, version, updated, expected_version),
            ).rowcount
            if changed != 1:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            return _materialize_settings(
                (1, profile_id, None, None, version, current.created_at_ms, updated)
            )

        return await self._storage.write(write)

    async def replace_selection_idle_or_no_dialogue(
        self,
        *,
        expected_version: int,
        server_id: str,
        profile_id: str,
        model_id: str,
        reasoning_effort: str,
    ) -> SettingsRecord:
        expected_version = _validate_expected_version(expected_version)
        server_id = _validate_required(server_id, MAX_SERVER_ID_LENGTH)
        profile_id = _validate_required(profile_id, MAX_PROFILE_ID_LENGTH)
        model_id = _validate_required(model_id, MAX_MODEL_ID_LENGTH)
        reasoning_effort = _validate_required(reasoning_effort, MAX_REASONING_EFFORT_LENGTH)

        def write(connection: Any) -> SettingsRecord:
            row = _settings_row(connection)
            if row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            current = _materialize_settings(row)
            if current.version != expected_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.profile_id != profile_id:
                raise _invariant()
            dialogue_row = _dialogue_row(connection)
            if dialogue_row is not None:
                dialogue = _materialize_dialogue(dialogue_row)
                if dialogue.server_id != server_id or dialogue.profile_id != profile_id:
                    raise _invariant()
                if dialogue.state is not DialogueState.IDLE:
                    raise RepositoryError(RepositoryErrorCategory.STATE_CONFLICT)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE settings SET model_id = ?, reasoning_effort = ?, version = ?, "
                "updated_at_ms = ? WHERE singleton = 1 AND version = ?",
                (model_id, reasoning_effort, version, updated, expected_version),
            ).rowcount
            if changed != 1:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            return _materialize_settings(
                (1, current.profile_id, model_id, reasoning_effort, version, current.created_at_ms, updated)
            )

        return await self._storage.write(write)

    async def create_dialogue_if_settings_current(
        self,
        *,
        dialogue_id: str,
        server_id: str,
        profile_id: str,
        expected_settings_version: int,
        expected_model_id: str | None,
        expected_reasoning_effort: str | None,
    ) -> DialogueRecord:
        dialogue_id = _validate_required(dialogue_id, MAX_DIALOGUE_ID_LENGTH)
        server_id = _validate_required(server_id, MAX_SERVER_ID_LENGTH)
        profile_id = _validate_required(profile_id, MAX_PROFILE_ID_LENGTH)
        expected_settings_version = _validate_expected_version(expected_settings_version)
        expected_model_id = _validate_string(expected_model_id, MAX_MODEL_ID_LENGTH, nullable=True)
        expected_reasoning_effort = _validate_string(
            expected_reasoning_effort, MAX_REASONING_EFFORT_LENGTH, nullable=True
        )

        def write(connection: Any) -> DialogueRecord:
            settings_row = _settings_row(connection)
            if settings_row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            settings = _materialize_settings(settings_row)
            if settings.version != expected_settings_version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if (
                settings.profile_id != profile_id
                or settings.model_id != expected_model_id
                or settings.reasoning_effort != expected_reasoning_effort
            ):
                raise _invariant()
            dialogue_row = _dialogue_row(connection)
            if dialogue_row is not None:
                _materialize_dialogue(dialogue_row)
                raise RepositoryError(RepositoryErrorCategory.ALREADY_EXISTS)
            now = _validate_clock(self._clock)
            connection.execute(
                "INSERT INTO dialogues "
                "(dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class) "
                "VALUES (?, 1, ?, ?, NULL, ?, 0, ?, ?, NULL)",
                (dialogue_id, server_id, profile_id, DialogueState.CREATING.value, now, now),
            )
            return _materialize_dialogue(
                (dialogue_id, 1, server_id, profile_id, None, DialogueState.CREATING.value, 0, now, now, None)
            )

        return await self._storage.write(write)


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


__all__ = ["SettingsDialogueGuardRepository"]
