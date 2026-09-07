"""Telegram-agnostic hard-delete orchestration over P1.9 and P2.5."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Protocol
from uuid import uuid4

from codex_control.adapters.codex.errors import CodexAdapterErrorCategory
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.storage import (
    DeletionRepository,
    DeletionTombstoneRecord,
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TurnJobRecord,
    TurnJobState,
)
from codex_control.storage.application_recovery import ApplicationRecoveryRepository
from codex_control.storage.core_repositories import MAX_SQLITE_INT
from codex_control.storage.errors import StorageError

from .dialogue_interrupt import (
    DialogueInterruptError,
    DialogueInterruptErrorCategory,
    DialogueInterruptReason,
    DialogueInterruptRequest,
    DialogueInterruptResult,
    DialogueInterruptStatus,
)


P3_DELETE_TOMBSTONE_RETENTION_MS = 604800000


class DialogueDeleteStatus(StrEnum):
    DELETED = "DELETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"


class DialogueDeleteReason(StrEnum):
    NO_DIALOGUE = "NO_DIALOGUE"
    DIALOGUE_NOT_READY = "DIALOGUE_NOT_READY"
    DELETE_NOT_READY = "DELETE_NOT_READY"
    INTERRUPT_IN_PROGRESS = "INTERRUPT_IN_PROGRESS"
    INTERRUPT_UNRESOLVED = "INTERRUPT_UNRESOLVED"
    DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"
    STALE_REQUEST = "STALE_REQUEST"


class DialogueDeleteErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class DialogueDeleteError(Exception):
    """Finite, content-free hard-delete application diagnostic."""

    def __init__(self, category: DialogueDeleteErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, DialogueDeleteErrorCategory)
                else DialogueDeleteErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = DialogueDeleteErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"DialogueDeleteError({self.category.value!r})"


def _invalid() -> DialogueDeleteError:
    return DialogueDeleteError(DialogueDeleteErrorCategory.INVALID_ARGUMENT)


def _storage() -> DialogueDeleteError:
    return DialogueDeleteError(DialogueDeleteErrorCategory.STORAGE)


def _invariant() -> DialogueDeleteError:
    return DialogueDeleteError(DialogueDeleteErrorCategory.INVARIANT)


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _default_id_factory(kind: str) -> str:
    return f"p3-{kind}-{uuid4().hex}"


def _validate_id(value: object) -> None:
    if type(value) is not str or not value or "\x00" in value or len(value) > 128:
        raise _invalid()


def _validate_version(value: object) -> None:
    if type(value) is not int or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()


def _validate_request(value: object) -> None:
    if not isinstance(value, DialogueDeleteRequest):
        raise _invalid()
    _validate_id(value.dialogue_id)
    _validate_version(value.expected_dialogue_version)


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _repository_error(error: BaseException) -> DialogueDeleteError:
    if isinstance(error, RepositoryError):
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invalid()
    return _storage()


def _interrupt_error(error: DialogueInterruptError) -> DialogueDeleteError:
    if error.category in (
        DialogueInterruptErrorCategory.INVALID_ARGUMENT,
        DialogueInterruptErrorCategory.INVARIANT,
    ):
        return _invariant()
    return _storage()


def _valid_interrupt_terminal_result(
    original_dialogue: DialogueRecord,
    original_job: TurnJobRecord,
    result: DialogueInterruptResult,
) -> bool:
    """Require the exact terminal shape produced by accepted P3.4."""
    if type(result.dialogue) is not DialogueRecord or type(result.job) is not TurnJobRecord:
        return False
    terminal_job = result.job
    terminal_dialogue = result.dialogue
    if original_job.state is not TurnJobState.CODEX_RUNNING:
        return False
    if (
        terminal_job.job_id != original_job.job_id
        or terminal_job.telegram_update_id != original_job.telegram_update_id
        or terminal_job.source_chat_id != original_job.source_chat_id
        or terminal_job.source_message_id != original_job.source_message_id
        or terminal_job.dialogue_id != original_job.dialogue_id
        or terminal_job.server_id != original_job.server_id
        or terminal_job.profile_id != original_job.profile_id
        or terminal_job.thread_id != original_job.thread_id
        or terminal_job.codex_turn_id != original_job.codex_turn_id
        or terminal_job.model_id != original_job.model_id
        or terminal_job.reasoning_effort != original_job.reasoning_effort
        or terminal_job.input_sha256 != original_job.input_sha256
        or terminal_job.version != original_job.version + 1
        or terminal_job.created_at_ms != original_job.created_at_ms
        or terminal_job.updated_at_ms < original_job.updated_at_ms
    ):
        return False
    if terminal_job.state not in (TurnJobState.CODEX_COMPLETED, TurnJobState.FAILED):
        return False
    if terminal_job.state is TurnJobState.CODEX_COMPLETED:
        if terminal_job.error_class is not None:
            return False
    elif terminal_job.error_class != "CODEX_TURN_FAILED":
        return False
    if (
        terminal_dialogue.dialogue_id != original_dialogue.dialogue_id
        or terminal_dialogue.server_id != original_dialogue.server_id
        or terminal_dialogue.profile_id != original_dialogue.profile_id
        or terminal_dialogue.thread_id != original_dialogue.thread_id
        or terminal_dialogue.state is not DialogueState.IDLE
        or terminal_dialogue.version not in (original_dialogue.version + 2, original_dialogue.version + 3)
        or terminal_dialogue.created_at_ms != original_dialogue.created_at_ms
        or terminal_dialogue.updated_at_ms < original_dialogue.updated_at_ms
        or terminal_dialogue.last_error_class is not None
    ):
        return False
    return True


@dataclass(frozen=True, repr=False)
class DialogueDeleteRequest:
    dialogue_id: str
    expected_dialogue_version: int

    def __post_init__(self) -> None:
        _validate_request(self)

    def __repr__(self) -> str:
        return "DialogueDeleteRequest(<redacted>)"


@dataclass(frozen=True, repr=False)
class DialogueDeleteResult:
    status: DialogueDeleteStatus
    dialogue: DialogueRecord | None
    tombstone: DeletionTombstoneRecord | None
    reason: DialogueDeleteReason | None

    def __repr__(self) -> str:
        return (
            "DialogueDeleteResult("
            f"status={getattr(self.status, 'value', 'INVALID')!r}, "
            f"dialogue_present={self.dialogue is not None!r}, "
            f"tombstone_present={self.tombstone is not None!r}, "
            f"reason={getattr(self.reason, 'value', None)!r})"
        )


class DeleteLifecyclePort(Protocol):
    async def delete(self, *, binding: ThreadBinding) -> ThreadOperationResult: ...


class DialogueDeleteService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        thread_lifecycle: DeleteLifecyclePort,
        interrupt_service: object | None = None,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        if type(server_id) is not str or not server_id or "\x00" in server_id or len(server_id) > 128:
            raise _invalid()
        if not _async_callable(thread_lifecycle, "delete"):
            raise _invalid()
        if interrupt_service is not None and not _async_callable(interrupt_service, "interrupt"):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._thread_lifecycle = thread_lifecycle
        self._interrupt_service = interrupt_service
        self._clock = now_ms if now_ms is not None else _default_clock
        self._id_factory = id_factory if id_factory is not None else _default_id_factory
        self._owned: dict[str, asyncio.Task[DialogueDeleteResult]] = {}

    def __repr__(self) -> str:
        return f"<DialogueDeleteService server_id={self._server_id!r}>"

    async def delete(self, request: DialogueDeleteRequest) -> DialogueDeleteResult:
        _validate_request(request)
        try:
            tombstone = await DeletionRepository(self._storage).get_tombstone(request.dialogue_id)
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if tombstone is not None:
            if dialogue is None:
                return DialogueDeleteResult(DialogueDeleteStatus.DELETED, None, tombstone, None)
            if dialogue.dialogue_id == request.dialogue_id:
                raise _invariant()
            return DialogueDeleteResult(
                DialogueDeleteStatus.CONFLICT, dialogue, tombstone, DialogueDeleteReason.STALE_REQUEST
            )
        if dialogue is None:
            return DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, None, None, DialogueDeleteReason.NO_DIALOGUE
            )
        if dialogue.dialogue_id != request.dialogue_id:
            return DialogueDeleteResult(
                DialogueDeleteStatus.CONFLICT, dialogue, None, DialogueDeleteReason.STALE_REQUEST
            )
        if dialogue.version != request.expected_dialogue_version:
            return DialogueDeleteResult(
                DialogueDeleteStatus.CONFLICT, dialogue, None, DialogueDeleteReason.STALE_REQUEST
            )
        if dialogue.server_id != self._server_id:
            raise _invariant()
        # These durable states are already post-claim authorities.  A replay
        # must report their finite state rather than accidentally becoming a
        # new request against an older optimistic version.
        if dialogue.state is DialogueState.DELETE_UNKNOWN:
            return DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, dialogue, None, None)
        if dialogue.state is DialogueState.DELETING:
            return DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, dialogue, None, DialogueDeleteReason.DELETE_IN_PROGRESS
            )
        if dialogue.dialogue_id in self._owned and not self._owned[dialogue.dialogue_id].done():
            return DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, dialogue, None, DialogueDeleteReason.DELETE_IN_PROGRESS
            )

        snapshot = None
        if dialogue.state is DialogueState.TURN_RUNNING:
            try:
                snapshot = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            if snapshot.dialogue != dialogue:
                raise _invariant()
            if len(snapshot.active_jobs) != 1:
                raise _invariant()
            active = snapshot.active_jobs[0]
            if active.state in (TurnJobState.CLAIMED, TurnJobState.CODEX_STARTING):
                return DialogueDeleteResult(
                    DialogueDeleteStatus.BLOCKED, dialogue, None, DialogueDeleteReason.DIALOGUE_NOT_READY
                )
            if active.state is not TurnJobState.CODEX_RUNNING:
                raise _invariant()
        elif dialogue.state is DialogueState.DELETE_PENDING:
            pass
        elif dialogue.state is DialogueState.INTERRUPTING:
            return DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, dialogue, None, DialogueDeleteReason.INTERRUPT_IN_PROGRESS
            )
        elif dialogue.state is not DialogueState.IDLE:
            return DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, dialogue, None, DialogueDeleteReason.DIALOGUE_NOT_READY
            )

        task = asyncio.create_task(self._orchestrate(request, dialogue, snapshot))
        self._owned[dialogue.dialogue_id] = task
        try:
            return await self._await_owned(task)
        finally:
            if self._owned.get(dialogue.dialogue_id) is task:
                self._owned.pop(dialogue.dialogue_id, None)

    async def _orchestrate(self, request, dialogue, snapshot) -> DialogueDeleteResult:
        current = dialogue
        if current.state is DialogueState.TURN_RUNNING:
            if self._interrupt_service is None or snapshot is None or len(snapshot.active_jobs) != 1:
                raise _invariant()
            job = snapshot.active_jobs[0]
            interrupt_request = DialogueInterruptRequest(
                current.dialogue_id, job.job_id, current.version, job.version
            )
            try:
                interrupt = await self._interrupt_service.interrupt(interrupt_request)
            except DialogueInterruptError as error:
                raise _interrupt_error(error) from None
            if type(interrupt) is not DialogueInterruptResult:
                raise _invariant()
            if type(interrupt.status) is not DialogueInterruptStatus:
                raise _invariant()
            if interrupt.status in (DialogueInterruptStatus.CONFIRMED, DialogueInterruptStatus.RECONCILED):
                if not _valid_interrupt_terminal_result(current, job, interrupt):
                    raise _invariant()
                current = interrupt.dialogue
            elif interrupt.status in (DialogueInterruptStatus.REJECTED, DialogueInterruptStatus.UNKNOWN):
                return DialogueDeleteResult(
                    DialogueDeleteStatus.BLOCKED, interrupt.dialogue or current, None,
                    DialogueDeleteReason.INTERRUPT_UNRESOLVED,
                )
            elif interrupt.status is DialogueInterruptStatus.BLOCKED:
                reason = (
                    DialogueDeleteReason.INTERRUPT_IN_PROGRESS
                    if interrupt.reason is DialogueInterruptReason.INTERRUPT_IN_PROGRESS
                    else DialogueDeleteReason.INTERRUPT_UNRESOLVED
                )
                return DialogueDeleteResult(DialogueDeleteStatus.BLOCKED, interrupt.dialogue or current, None, reason)
            elif interrupt.status is DialogueInterruptStatus.CONFLICT:
                return DialogueDeleteResult(
                    DialogueDeleteStatus.CONFLICT, interrupt.dialogue, None, DialogueDeleteReason.STALE_REQUEST
                )
            else:
                raise _invariant()

        if current.state is DialogueState.IDLE:
            try:
                current = await self._claim_intent(request, current)
            except _ClaimRace as race:
                return race.result
        elif current.state is not DialogueState.DELETE_PENDING:
            raise _invariant()
        try:
            deleting = await self._claim_deleting(request.dialogue_id, current.version)
        except _ClaimRace as race:
            return race.result
        try:
            binding = ThreadBinding(deleting.profile_id, deleting.thread_id or "")
        except Exception:
            raise _invariant() from None
        try:
            result = await self._thread_lifecycle.delete(binding=binding)
        except asyncio.CancelledError:
            raise
        except ThreadLifecycleError as error:
            if _lifecycle_name(error) in {
                "thread_request_invalid", "thread_precondition_changed", "thread_operation_busy",
            }:
                failed = await self._mark_error(deleting, "CODEX_PROCESS")
                return DialogueDeleteResult(DialogueDeleteStatus.FAILED, failed, None, None)
            unknown = await self._mark_unknown(deleting)
            return DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, unknown, None, None)
        except Exception:
            unknown = await self._mark_unknown(deleting)
            return DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, unknown, None, None)

        if (
            type(result) is not ThreadOperationResult
            or type(result.status) is not ThreadOperationStatus
            or result.binding is not binding
        ):
            unknown = await self._mark_unknown(deleting)
            return DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, unknown, None, None)
        if result.status is ThreadOperationStatus.DELETE_CONFIRMED:
            now = self._clock_value()
            if now > MAX_SQLITE_INT - P3_DELETE_TOMBSTONE_RETENTION_MS:
                raise _invariant()
            expiry = now + P3_DELETE_TOMBSTONE_RETENTION_MS
            try:
                finalized = await DeletionRepository(self._storage, now_ms=self._clock).finalize_confirmed(
                    dialogue_id=deleting.dialogue_id,
                    expected_version=deleting.version,
                    tombstone_expires_at_ms=expiry,
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            if (
                finalized.tombstone.dialogue_id != deleting.dialogue_id
                or finalized.tombstone.stale_generation != deleting.version
                or finalized.tombstone.expires_at_ms != expiry
            ):
                raise _invariant()
            return DialogueDeleteResult(DialogueDeleteStatus.DELETED, None, finalized.tombstone, None)
        unknown = await self._mark_unknown(deleting)
        return DialogueDeleteResult(DialogueDeleteStatus.UNKNOWN, unknown, None, None)

    async def _claim_intent(self, request, dialogue: DialogueRecord) -> DialogueRecord:
        try:
            claimed = await DeletionRepository(self._storage, now_ms=self._clock).claim_delete_intent(
                dialogue_id=request.dialogue_id, expected_version=dialogue.version
            )
        except (StorageError, RepositoryError) as error:
            if isinstance(error, RepositoryError) and error.category in (
                RepositoryErrorCategory.STATE_CONFLICT,
                RepositoryErrorCategory.VERSION_CONFLICT,
            ):
                return await self._claim_race(request, dialogue)
            raise _repository_error(error) from None
        if (
            type(claimed) is not DialogueRecord
            or claimed.dialogue_id != dialogue.dialogue_id
            or claimed.version != dialogue.version + 1
            or claimed.state is not DialogueState.DELETE_PENDING
            or claimed.profile_id != dialogue.profile_id
            or claimed.thread_id != dialogue.thread_id
        ):
            raise _invariant()
        return claimed

    async def _claim_deleting(self, dialogue_id: str, expected_version: int) -> DialogueRecord:
        try:
            claimed = await DeletionRepository(self._storage, now_ms=self._clock).claim_deleting(
                dialogue_id=dialogue_id, expected_version=expected_version
            )
        except (StorageError, RepositoryError) as error:
            if isinstance(error, RepositoryError) and error.category in (
                RepositoryErrorCategory.STATE_CONFLICT,
                RepositoryErrorCategory.VERSION_CONFLICT,
            ):
                try:
                    current = await DialogueRepository(self._storage).get_live()
                except (StorageError, RepositoryError) as reread_error:
                    raise _repository_error(reread_error) from None
                if current is None or current.dialogue_id != dialogue_id:
                    raise _invariant()
                if current.state is DialogueState.DELETE_PENDING and current.version == expected_version:
                    raise _ClaimRace(
                        DialogueDeleteResult(
                            DialogueDeleteStatus.BLOCKED, current, None,
                            DialogueDeleteReason.DELETE_NOT_READY,
                        )
                    )
                if current.state is DialogueState.DELETE_PENDING:
                    raise _ClaimRace(
                        DialogueDeleteResult(
                            DialogueDeleteStatus.CONFLICT, current, None,
                            DialogueDeleteReason.STALE_REQUEST,
                        )
                    )
                if current.state is DialogueState.DELETING:
                    raise _ClaimRace(
                        DialogueDeleteResult(
                            DialogueDeleteStatus.BLOCKED, current, None,
                            DialogueDeleteReason.DELETE_IN_PROGRESS,
                        )
                    )
                raise _invariant()
            raise _repository_error(error) from None
        if (
            type(claimed) is not DialogueRecord
            or claimed.dialogue_id != dialogue_id
            or claimed.version != expected_version + 1
            or claimed.state is not DialogueState.DELETING
            or claimed.thread_id is None
        ):
            raise _invariant()
        return claimed

    async def _claim_race(self, request, original: DialogueRecord) -> DialogueRecord:
        try:
            current = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if current is None or current.dialogue_id != request.dialogue_id:
            raise _invariant()
        if current.version != original.version:
            raise _ClaimRace(
                DialogueDeleteResult(
                    DialogueDeleteStatus.CONFLICT, current, None, DialogueDeleteReason.STALE_REQUEST
                )
            )
        raise _ClaimRace(
            DialogueDeleteResult(
                DialogueDeleteStatus.BLOCKED, current, None, DialogueDeleteReason.DELETE_NOT_READY
            )
        )

    async def _mark_unknown(self, deleting: DialogueRecord) -> DialogueRecord:
        try:
            marked = await DeletionRepository(self._storage, now_ms=self._clock).mark_delete_unknown(
                dialogue_id=deleting.dialogue_id,
                expected_version=deleting.version,
                error_class="DELETE_UNKNOWN",
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if (
            type(marked) is not DialogueRecord
            or marked.state is not DialogueState.DELETE_UNKNOWN
            or marked.version != deleting.version + 1
            or marked.last_error_class != "DELETE_UNKNOWN"
        ):
            raise _invariant()
        return marked

    async def _mark_error(self, deleting: DialogueRecord, error_class: str) -> DialogueRecord:
        try:
            marked = await DeletionRepository(self._storage, now_ms=self._clock).mark_delete_error(
                dialogue_id=deleting.dialogue_id,
                expected_version=deleting.version,
                error_class=error_class,
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if (
            type(marked) is not DialogueRecord
            or marked.state is not DialogueState.ERROR
            or marked.version != deleting.version + 1
            or marked.last_error_class != error_class
        ):
            raise _invariant()
        return marked

    def _clock_value(self) -> int:
        try:
            value = self._clock()
        except Exception:
            raise _storage() from None
        if type(value) is not int or not 0 <= value <= MAX_SQLITE_INT:
            raise _storage()
        return value

    async def _await_owned(self, task: asyncio.Task[DialogueDeleteResult]) -> DialogueDeleteResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None


def _lifecycle_name(error: ThreadLifecycleError) -> str:
    category = getattr(error, "category", None)
    return getattr(category, "value", category)


class _ClaimRace(Exception):
    def __init__(self, result: DialogueDeleteResult) -> None:
        self.result = result
