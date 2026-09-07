"""Final no-external-effect startup recovery for P3 dialogue state."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from codex_control.storage import (
    DeletionRepository,
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    InterruptCoordinationRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TurnJobRecord,
)
from codex_control.storage.application_recovery import ApplicationRecoveryRepository
from codex_control.storage.errors import StorageError

class DialogueRecoveryStatus(StrEnum):
    NO_ACTION = "NO_ACTION"
    CREATE_MARKED_UNKNOWN = "CREATE_MARKED_UNKNOWN"
    PRE_EFFECT_FAILED = "PRE_EFFECT_FAILED"
    TURN_MARKED_UNKNOWN = "TURN_MARKED_UNKNOWN"
    INTERRUPT_MARKED_UNKNOWN = "INTERRUPT_MARKED_UNKNOWN"
    DELETE_MARKED_UNKNOWN = "DELETE_MARKED_UNKNOWN"


class DialogueRecoveryErrorCategory(StrEnum):
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class DialogueRecoveryError(Exception):
    """Finite, content-free startup recovery diagnostic."""

    def __init__(self, category: DialogueRecoveryErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, DialogueRecoveryErrorCategory)
                else DialogueRecoveryErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = DialogueRecoveryErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"DialogueRecoveryError({self.category.value!r})"


def _storage() -> DialogueRecoveryError:
    return DialogueRecoveryError(DialogueRecoveryErrorCategory.STORAGE)


def _invariant() -> DialogueRecoveryError:
    return DialogueRecoveryError(DialogueRecoveryErrorCategory.INVARIANT)


def _repository_error(error: BaseException) -> DialogueRecoveryError:
    if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
        return _invariant()
    return _storage()


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True, repr=False)
class DialogueRecoveryResult:
    status: DialogueRecoveryStatus
    job: TurnJobRecord | None
    dialogue: DialogueRecord | None

    def __repr__(self) -> str:
        return (
            "DialogueRecoveryResult("
            f"status={getattr(self.status, 'value', 'INVALID')!r}, "
            f"job_present={self.job is not None!r}, "
            f"dialogue_present={self.dialogue is not None!r})"
        )


class DialogueRecoveryService:
    def __init__(self, storage: SqliteStorage, *, now_ms: Callable[[], int] | None = None) -> None:
        if not isinstance(storage, SqliteStorage) or (now_ms is not None and not callable(now_ms)):
            raise _invariant()
        self._storage = storage
        self._clock = now_ms if now_ms is not None else _default_clock

    def __repr__(self) -> str:
        return "<DialogueRecoveryService>"

    async def recover_startup(self) -> DialogueRecoveryResult:
        coordinator = ApplicationRecoveryRepository(self._storage, now_ms=self._clock)
        try:
            snapshot = await coordinator.inspect()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        current = snapshot.dialogue
        if current is None:
            return DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, None)

        if current.state is DialogueState.CREATING:
            if len(snapshot.active_jobs) > 1:
                raise _invariant()
            try:
                marked = await DialogueRepository(self._storage, now_ms=self._clock).mark_create_unknown(
                    dialogue_id=current.dialogue_id,
                    expected_version=current.version,
                    error_class="CODEX_AMBIGUOUS",
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            if marked.state is not DialogueState.CREATE_UNKNOWN or marked.version != current.version + 1:
                raise _invariant()
            job = snapshot.active_jobs[0] if snapshot.active_jobs else None
            return DialogueRecoveryResult(DialogueRecoveryStatus.CREATE_MARKED_UNKNOWN, job, marked)

        if current.state is DialogueState.INTERRUPTING:
            try:
                recovered = await InterruptCoordinationRepository(self._storage, now_ms=self._clock).recover_preexisting_interrupt()
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            if recovered is None or recovered.dialogue.state is not DialogueState.TURN_UNKNOWN:
                raise _invariant()
            return DialogueRecoveryResult(
                DialogueRecoveryStatus.INTERRUPT_MARKED_UNKNOWN, recovered.job, recovered.dialogue
            )

        if current.state is DialogueState.DELETING:
            if snapshot.active_jobs:
                raise _invariant()
            try:
                marked = await DeletionRepository(self._storage, now_ms=self._clock).mark_delete_unknown(
                    dialogue_id=current.dialogue_id,
                    expected_version=current.version,
                    error_class="DELETE_UNKNOWN",
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            if marked.state is not DialogueState.DELETE_UNKNOWN or marked.version != current.version + 1:
                raise _invariant()
            return DialogueRecoveryResult(DialogueRecoveryStatus.DELETE_MARKED_UNKNOWN, None, marked)

        if current.state is DialogueState.DELETE_PENDING:
            if snapshot.active_jobs:
                raise _invariant()
            return DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, current)

        if current.state in (DialogueState.CREATE_UNKNOWN, DialogueState.ERROR):
            if len(snapshot.active_jobs) > 1:
                raise _invariant()
            return DialogueRecoveryResult(
                DialogueRecoveryStatus.NO_ACTION,
                snapshot.active_jobs[0] if snapshot.active_jobs else None,
                current,
            )

        if current.state not in (DialogueState.IDLE, DialogueState.TURN_RUNNING):
            if snapshot.active_jobs:
                raise _invariant()
            return DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, current)

        if len(snapshot.active_jobs) != 1:
            if len(snapshot.active_jobs) == 0 and current.state is DialogueState.IDLE:
                return DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, None, current)
            raise _invariant()
        job = snapshot.active_jobs[0]
        try:
            transition = await coordinator.recover_turn(
                dialogue_id=current.dialogue_id,
                expected_dialogue_version=current.version,
                expected_job_id=job.job_id,
                expected_job_version=job.version,
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if transition.action == "PRE_EFFECT_FAILED":
            return DialogueRecoveryResult(DialogueRecoveryStatus.PRE_EFFECT_FAILED, transition.job, transition.dialogue)
        if transition.action == "TURN_MARKED_UNKNOWN":
            return DialogueRecoveryResult(DialogueRecoveryStatus.TURN_MARKED_UNKNOWN, transition.job, transition.dialogue)
        if transition.action == "NO_ACTION":
            return DialogueRecoveryResult(DialogueRecoveryStatus.NO_ACTION, transition.job, transition.dialogue)
        raise _invariant()


__all__ = [
    "DialogueRecoveryError",
    "DialogueRecoveryErrorCategory",
    "DialogueRecoveryResult",
    "DialogueRecoveryService",
    "DialogueRecoveryStatus",
]
