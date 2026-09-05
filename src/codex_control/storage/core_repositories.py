"""P2.2 repositories for the controller's core durable state."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

from codex_control.domain import ControllerMode

from .records import (
    ControllerBootResult,
    ControllerRuntimeRecord,
    DialogueRecord,
    DialogueState,
    SettingsInitializeResult,
    SettingsRecord,
)
from .repository_errors import RepositoryError, RepositoryErrorCategory
from .sqlite import SqliteStorage

MAX_SQLITE_INT = 9223372036854775807

_DIALOGUE_ID_LENGTH = 128
_SERVER_ID_LENGTH = 128
_PROFILE_ID_LENGTH = 128
_FLEET_VERSION_LENGTH = 128
_MODEL_ID_LENGTH = 256
_REASONING_EFFORT_LENGTH = 64
_THREAD_ID_LENGTH = 512
_ERROR_CLASS_LENGTH = 128
_ERROR_CLASS_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def _invalid() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVALID_ARGUMENT)


def _invariant() -> RepositoryError:
    return RepositoryError(RepositoryErrorCategory.INVARIANT_VIOLATION)


def _validate_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()
    return value


def _validate_expected_version(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()
    return value


def _validate_error_class(value: object) -> str:
    if not isinstance(value, str) or not _ERROR_CLASS_RE.fullmatch(value):
        raise _invalid()
    return value


def _validate_stored_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invariant()
    return value


def _validate_stored_string(value: object, limit: int, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invariant()
    return value


def _validate_stored_timestamp(value: object) -> int:
    return _validate_stored_int(value)


def _validate_clock(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise RepositoryError(RepositoryErrorCategory.CLOCK_INVALID) from None
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise RepositoryError(RepositoryErrorCategory.CLOCK_INVALID)
    return value


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _next_version(value: int) -> int:
    if value >= MAX_SQLITE_INT:
        raise _invariant()
    return value + 1


def _materialize_controller(row: Any) -> ControllerRuntimeRecord:
    if row is None or len(row) != 7:
        raise _invariant()
    singleton = _validate_stored_int(row[0])
    if singleton != 1:
        raise _invariant()
    epoch = _validate_stored_int(row[1])
    requested = row[2]
    if not isinstance(requested, str):
        raise _invariant()
    try:
        requested_mode = ControllerMode(requested)
    except (TypeError, ValueError):
        raise _invariant() from None
    generation = _validate_stored_int(row[3])
    fleet_version = _validate_stored_string(row[4], _FLEET_VERSION_LENGTH)
    created = _validate_stored_timestamp(row[5])
    updated = _validate_stored_timestamp(row[6])
    if updated < created:
        raise _invariant()
    assert fleet_version is not None
    return ControllerRuntimeRecord(epoch, requested_mode, generation, fleet_version, created, updated)


def _materialize_settings(row: Any) -> SettingsRecord:
    if row is None or len(row) != 7:
        raise _invariant()
    singleton = _validate_stored_int(row[0])
    if singleton != 1:
        raise _invariant()
    profile_id = _validate_stored_string(row[1], _PROFILE_ID_LENGTH, nullable=True)
    model_id = _validate_stored_string(row[2], _MODEL_ID_LENGTH, nullable=True)
    reasoning_effort = _validate_stored_string(row[3], _REASONING_EFFORT_LENGTH, nullable=True)
    version = _validate_stored_int(row[4])
    created = _validate_stored_timestamp(row[5])
    updated = _validate_stored_timestamp(row[6])
    if updated < created:
        raise _invariant()
    return SettingsRecord(profile_id, model_id, reasoning_effort, version, created, updated)


def _materialize_dialogue(row: Any) -> DialogueRecord:
    if row is None or len(row) != 10:
        raise _invariant()
    dialogue_id = _validate_stored_string(row[0], _DIALOGUE_ID_LENGTH)
    live_slot = _validate_stored_int(row[1])
    if live_slot != 1:
        raise _invariant()
    server_id = _validate_stored_string(row[2], _SERVER_ID_LENGTH)
    profile_id = _validate_stored_string(row[3], _PROFILE_ID_LENGTH)
    thread_id = _validate_stored_string(row[4], _THREAD_ID_LENGTH, nullable=True)
    state_value = row[5]
    if not isinstance(state_value, str):
        raise _invariant()
    try:
        state = DialogueState(state_value)
    except (TypeError, ValueError):
        raise _invariant() from None
    version = _validate_stored_int(row[6])
    created = _validate_stored_timestamp(row[7])
    updated = _validate_stored_timestamp(row[8])
    if updated < created:
        raise _invariant()
    last_error_class = _validate_stored_string(row[9], _ERROR_CLASS_LENGTH, nullable=True)
    if last_error_class is not None and _ERROR_CLASS_RE.fullmatch(last_error_class) is None:
        raise _invariant()
    assert dialogue_id is not None
    assert server_id is not None
    assert profile_id is not None
    return DialogueRecord(
        dialogue_id,
        server_id,
        profile_id,
        thread_id,
        state,
        version,
        created,
        updated,
        last_error_class,
    )


def _one_row(connection: Any, sql: str, parameters: tuple[object, ...]) -> Any:
    return connection.execute(sql, parameters).fetchone()


def _singleton_row(connection: Any, sql: str) -> Any:
    rows = connection.execute(sql).fetchall()
    if len(rows) > 1:
        raise _invariant()
    return rows[0] if rows else None


class _RepositoryBase:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invalid()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class ControllerRuntimeRepository(_RepositoryBase):
    async def get(self) -> ControllerRuntimeRecord | None:
        def read(connection: Any) -> ControllerRuntimeRecord | None:
            row = _singleton_row(
                connection,
                "SELECT singleton, last_control_epoch, requested_mode, boot_generation, "
                "fleet_version, created_at_ms, updated_at_ms FROM controller_runtime",
            )
            return None if row is None else _materialize_controller(row)

        return await self._storage.read(read)

    async def begin_boot(self, fleet_version: str) -> ControllerBootResult:
        fleet_version = _validate_string(fleet_version, _FLEET_VERSION_LENGTH)
        assert fleet_version is not None

        def write(connection: Any) -> ControllerBootResult:
            row = _singleton_row(
                connection,
                "SELECT singleton, last_control_epoch, requested_mode, boot_generation, "
                "fleet_version, created_at_ms, updated_at_ms FROM controller_runtime",
            )
            if row is None:
                now = _validate_clock(self._clock)
                connection.execute(
                    "INSERT INTO controller_runtime "
                    "(singleton, last_control_epoch, requested_mode, boot_generation, "
                    "fleet_version, created_at_ms, updated_at_ms) VALUES (1, 0, ?, 1, ?, ?, ?)",
                    (ControllerMode.SLEEP.value, fleet_version, now, now),
                )
                record = _materialize_controller(
                    (1, 0, ControllerMode.SLEEP.value, 1, fleet_version, now, now)
                )
                return ControllerBootResult(record, ControllerMode.SLEEP)

            current = _materialize_controller(row)
            generation = _next_version(current.boot_generation)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE controller_runtime SET boot_generation = ?, fleet_version = ?, "
                "updated_at_ms = ? WHERE singleton = 1 AND boot_generation = ?",
                (generation, fleet_version, updated, current.boot_generation),
            ).rowcount
            if changed != 1:
                raise _invariant()
            record = _materialize_controller(
                (1, current.last_control_epoch, current.requested_mode.value, generation,
                 fleet_version, current.created_at_ms, updated)
            )
            return ControllerBootResult(record, ControllerMode.SLEEP)

        return await self._storage.write(write)


class SettingsRepository(_RepositoryBase):
    async def get(self) -> SettingsRecord | None:
        def read(connection: Any) -> SettingsRecord | None:
            row = _singleton_row(
                connection,
                "SELECT singleton, profile_id, model_id, reasoning_effort, version, "
                "created_at_ms, updated_at_ms FROM settings",
            )
            return None if row is None else _materialize_settings(row)

        return await self._storage.read(read)

    async def initialize_if_absent(
        self,
        *,
        profile_id: str | None,
        model_id: str | None,
        reasoning_effort: str | None,
    ) -> SettingsInitializeResult:
        profile_id = _validate_string(profile_id, _PROFILE_ID_LENGTH, nullable=True)
        model_id = _validate_string(model_id, _MODEL_ID_LENGTH, nullable=True)
        reasoning_effort = _validate_string(reasoning_effort, _REASONING_EFFORT_LENGTH, nullable=True)

        def write(connection: Any) -> SettingsInitializeResult:
            row = _singleton_row(
                connection,
                "SELECT singleton, profile_id, model_id, reasoning_effort, version, "
                "created_at_ms, updated_at_ms FROM settings",
            )
            if row is not None:
                return SettingsInitializeResult(_materialize_settings(row), False)
            now = _validate_clock(self._clock)
            connection.execute(
                "INSERT INTO settings "
                "(singleton, profile_id, model_id, reasoning_effort, version, created_at_ms, updated_at_ms) "
                "VALUES (1, ?, ?, ?, 0, ?, ?)",
                (profile_id, model_id, reasoning_effort, now, now),
            )
            record = _materialize_settings((1, profile_id, model_id, reasoning_effort, 0, now, now))
            return SettingsInitializeResult(record, True)

        return await self._storage.write(write)

    async def replace(
        self,
        *,
        expected_version: int,
        profile_id: str | None,
        model_id: str | None,
        reasoning_effort: str | None,
    ) -> SettingsRecord:
        expected_version = _validate_expected_version(expected_version)
        profile_id = _validate_string(profile_id, _PROFILE_ID_LENGTH, nullable=True)
        model_id = _validate_string(model_id, _MODEL_ID_LENGTH, nullable=True)
        reasoning_effort = _validate_string(reasoning_effort, _REASONING_EFFORT_LENGTH, nullable=True)

        def write(connection: Any) -> SettingsRecord:
            row = _singleton_row(
                connection,
                "SELECT singleton, profile_id, model_id, reasoning_effort, version, "
                "created_at_ms, updated_at_ms FROM settings",
            )
            if row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            current = _materialize_settings(row)
            if expected_version != current.version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            changed = connection.execute(
                "UPDATE settings SET profile_id = ?, model_id = ?, reasoning_effort = ?, "
                "version = ?, updated_at_ms = ? WHERE singleton = 1 AND version = ?",
                (profile_id, model_id, reasoning_effort, version, updated, expected_version),
            ).rowcount
            if changed != 1:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            return _materialize_settings(
                (1, profile_id, model_id, reasoning_effort, version, current.created_at_ms, updated)
            )

        return await self._storage.write(write)


class DialogueRepository(_RepositoryBase):
    async def get_live(self) -> DialogueRecord | None:
        def read(connection: Any) -> DialogueRecord | None:
            rows = connection.execute(
                "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class FROM dialogues"
            ).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                raise _invariant()
            return _materialize_dialogue(rows[0])

        return await self._storage.read(read)

    async def create_intent(
        self,
        *,
        dialogue_id: str,
        server_id: str,
        profile_id: str,
    ) -> DialogueRecord:
        dialogue_id = _validate_string(dialogue_id, _DIALOGUE_ID_LENGTH)
        server_id = _validate_string(server_id, _SERVER_ID_LENGTH)
        profile_id = _validate_string(profile_id, _PROFILE_ID_LENGTH)
        assert dialogue_id is not None and server_id is not None and profile_id is not None

        def write(connection: Any) -> DialogueRecord:
            retained = connection.execute("SELECT 1 FROM dialogues LIMIT 1").fetchone()
            if retained is not None:
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

    async def confirm_created(
        self,
        *,
        dialogue_id: str,
        expected_version: int,
        thread_id: str,
    ) -> DialogueRecord:
        dialogue_id = _validate_string(dialogue_id, _DIALOGUE_ID_LENGTH)
        expected_version = _validate_expected_version(expected_version)
        thread_id = _validate_string(thread_id, _THREAD_ID_LENGTH)
        assert dialogue_id is not None and thread_id is not None
        return await self._finish_create(dialogue_id, expected_version, thread_id=thread_id)

    async def mark_create_unknown(
        self,
        *,
        dialogue_id: str,
        expected_version: int,
        error_class: str,
    ) -> DialogueRecord:
        dialogue_id = _validate_string(dialogue_id, _DIALOGUE_ID_LENGTH)
        expected_version = _validate_expected_version(expected_version)
        error_class = _validate_error_class(error_class)
        assert dialogue_id is not None
        return await self._finish_create(dialogue_id, expected_version, error_class=error_class)

    async def mark_create_error(
        self,
        *,
        dialogue_id: str,
        expected_version: int,
        error_class: str,
    ) -> DialogueRecord:
        dialogue_id = _validate_string(dialogue_id, _DIALOGUE_ID_LENGTH)
        expected_version = _validate_expected_version(expected_version)
        error_class = _validate_error_class(error_class)
        assert dialogue_id is not None
        return await self._finish_create(dialogue_id, expected_version, error_class=error_class, error_state=True)

    async def _finish_create(
        self,
        dialogue_id: str,
        expected_version: int,
        *,
        thread_id: str | None = None,
        error_class: str | None = None,
        error_state: bool = False,
    ) -> DialogueRecord:
        def write(connection: Any) -> DialogueRecord:
            row = _one_row(
                connection,
                "SELECT dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, "
                "created_at_ms, updated_at_ms, last_error_class FROM dialogues WHERE dialogue_id = ?",
                (dialogue_id,),
            )
            if row is None:
                raise RepositoryError(RepositoryErrorCategory.NOT_FOUND)
            current = _materialize_dialogue(row)
            if expected_version != current.version:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            if current.state is not DialogueState.CREATING or current.thread_id is not None:
                raise RepositoryError(RepositoryErrorCategory.STATE_CONFLICT)
            version = _next_version(current.version)
            now = _validate_clock(self._clock)
            updated = max(now, current.updated_at_ms)
            if thread_id is not None:
                state = DialogueState.IDLE
                new_thread_id = thread_id
            elif error_state:
                state = DialogueState.ERROR
                new_thread_id = None
            else:
                state = DialogueState.CREATE_UNKNOWN
                new_thread_id = None
            changed = connection.execute(
                "UPDATE dialogues SET thread_id = ?, state = ?, version = ?, updated_at_ms = ?, "
                "last_error_class = ? WHERE dialogue_id = ? AND version = ? "
                "AND state = ? AND thread_id IS NULL",
                (new_thread_id, state.value, version, updated, error_class, dialogue_id,
                 expected_version, DialogueState.CREATING.value),
            ).rowcount
            if changed != 1:
                raise RepositoryError(RepositoryErrorCategory.VERSION_CONFLICT)
            return _materialize_dialogue(
                (current.dialogue_id, 1, current.server_id, current.profile_id, new_thread_id,
                 state.value, version, current.created_at_ms, updated, error_class)
            )

        return await self._storage.write(write)
