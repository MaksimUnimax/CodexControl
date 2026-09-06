"""Telegram-agnostic durable operator interrupt orchestration."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Protocol
from uuid import uuid4

from codex_control.adapters.codex.turn_lifecycle import (
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnLifecycleError,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.storage import (
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    InterruptCoordinationRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
    TurnJobFinishResult,
    TransientPayloadRecord,
)
from codex_control.storage.errors import StorageError

from ._turn_common import _prepare_output, _project_terminal
from .active_turn_registry import ActiveTurnRegistry


MAX_SIGNED_64 = 9_223_372_036_854_775_807
MAX_INTERRUPT_ID_CHARS = 128


class DialogueInterruptStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    RECONCILED = "RECONCILED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"


class DialogueInterruptReason(StrEnum):
    NO_DIALOGUE = "NO_DIALOGUE"
    DIALOGUE_NOT_RUNNING = "DIALOGUE_NOT_RUNNING"
    JOB_NOT_RUNNING = "JOB_NOT_RUNNING"
    ACTIVE_BINDING_UNAVAILABLE = "ACTIVE_BINDING_UNAVAILABLE"
    INTERRUPT_IN_PROGRESS = "INTERRUPT_IN_PROGRESS"
    STALE_REQUEST = "STALE_REQUEST"


class DialogueInterruptErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class DialogueInterruptError(Exception):
    """Finite, content-free interrupt application diagnostic."""

    def __init__(self, category: DialogueInterruptErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, DialogueInterruptErrorCategory)
                else DialogueInterruptErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = DialogueInterruptErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"DialogueInterruptError({self.category.value!r})"


def _invalid() -> DialogueInterruptError:
    return DialogueInterruptError(DialogueInterruptErrorCategory.INVALID_ARGUMENT)


def _storage() -> DialogueInterruptError:
    return DialogueInterruptError(DialogueInterruptErrorCategory.STORAGE)


def _invariant() -> DialogueInterruptError:
    return DialogueInterruptError(DialogueInterruptErrorCategory.INVARIANT)


def _validate_id(value: object) -> None:
    if (
        type(value) is not str
        or not value
        or "\x00" in value
        or len(value) > MAX_INTERRUPT_ID_CHARS
    ):
        raise _invalid()


def _validate_version(value: object) -> None:
    if type(value) is not int or not 0 <= value <= MAX_SIGNED_64:
        raise _invalid()


def _validate_request(request: object) -> None:
    if not isinstance(request, DialogueInterruptRequest):
        raise _invalid()
    _validate_id(request.dialogue_id)
    _validate_id(request.job_id)
    _validate_version(request.expected_dialogue_version)
    _validate_version(request.expected_job_version)


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _default_id_factory(kind: str) -> str:
    return f"p3-{kind}-{uuid4().hex}"


def _repository_error(error: BaseException) -> DialogueInterruptError:
    if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
        return _invariant()
    if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
        return _invalid()
    if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.ALREADY_EXISTS:
        return _invariant()
    if isinstance(error, (RepositoryError, StorageError)):
        return _storage()
    return _storage()


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


@dataclass(frozen=True, repr=False)
class DialogueInterruptRequest:
    dialogue_id: str
    job_id: str
    expected_dialogue_version: int
    expected_job_version: int

    def __post_init__(self) -> None:
        _validate_request(self)

    def __repr__(self) -> str:
        return "DialogueInterruptRequest(<redacted>)"


@dataclass(frozen=True, repr=False)
class DialogueInterruptResult:
    status: DialogueInterruptStatus
    job: TurnJobRecord | None
    dialogue: DialogueRecord | None
    output_payload: TransientPayloadRecord | None
    reason: DialogueInterruptReason | None

    def __repr__(self) -> str:
        return (
            "DialogueInterruptResult("
            f"status={getattr(self.status, 'value', 'INVALID')!r}, "
            f"job_present={self.job is not None!r}, "
            f"dialogue_present={self.dialogue is not None!r}, "
            f"output_present={self.output_payload is not None!r}, "
            f"reason={getattr(self.reason, 'value', None)!r})"
        )


class InterruptRecoveryStatus(StrEnum):
    NO_ACTION = "NO_ACTION"
    MARKED_UNKNOWN = "MARKED_UNKNOWN"


@dataclass(frozen=True, repr=False)
class InterruptRecoveryResult:
    status: InterruptRecoveryStatus
    job: TurnJobRecord | None
    dialogue: DialogueRecord | None

    def __repr__(self) -> str:
        return (
            "InterruptRecoveryResult("
            f"status={getattr(self.status, 'value', 'INVALID')!r}, "
            f"job_present={self.job is not None!r}, "
            f"dialogue_present={self.dialogue is not None!r})"
        )


class InterruptLifecyclePort(Protocol):
    async def interrupt_turn(self, binding: TurnBinding) -> TurnInterruptResult: ...

    async def wait_turn(self, binding: TurnBinding) -> TurnTerminalResult: ...


class DialogueInterruptService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        active_turn_registry: ActiveTurnRegistry,
        turn_lifecycle: InterruptLifecyclePort,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        if type(server_id) is not str or not server_id or "\x00" in server_id or len(server_id) > MAX_INTERRUPT_ID_CHARS:
            raise _invalid()
        if type(active_turn_registry) is not ActiveTurnRegistry:
            raise _invalid()
        if not _async_callable(turn_lifecycle, "interrupt_turn") or not _async_callable(turn_lifecycle, "wait_turn"):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._registry = active_turn_registry
        self._turn_lifecycle = turn_lifecycle
        self._clock = now_ms if now_ms is not None else _default_clock
        self._id_factory = id_factory if id_factory is not None else _default_id_factory

    def __repr__(self) -> str:
        return f"<DialogueInterruptService server_id={self._server_id!r}>"

    async def interrupt(self, request: DialogueInterruptRequest) -> DialogueInterruptResult:
        _validate_request(request)
        try:
            dialogue, job, binding = await self._preflight(request)
        except _PreflightResult as result:
            return result.result
        owned = asyncio.create_task(self._orchestrate(request, dialogue, job, binding))
        return await self._await_owned(owned)

    async def recover_preexisting_interrupt(self) -> InterruptRecoveryResult:
        try:
            current = await DialogueRepository(self._storage, now_ms=self._clock).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if current is None or current.state is not DialogueState.INTERRUPTING:
            return InterruptRecoveryResult(InterruptRecoveryStatus.NO_ACTION, None, current)
        try:
            recovered = await InterruptCoordinationRepository(self._storage, now_ms=self._clock).recover_preexisting_interrupt()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if not isinstance(recovered, TurnJobFinishResult):
            raise _invariant()
        if recovered.job.state is not TurnJobState.UNKNOWN or recovered.dialogue.state is not DialogueState.TURN_UNKNOWN:
            raise _invariant()
        return InterruptRecoveryResult(InterruptRecoveryStatus.MARKED_UNKNOWN, recovered.job, recovered.dialogue)

    async def _preflight(self, request: DialogueInterruptRequest) -> tuple[DialogueRecord, TurnJobRecord, TurnBinding]:
        try:
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if dialogue is None:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, None, None, None,
                                        DialogueInterruptReason.NO_DIALOGUE)
            )
        if dialogue.dialogue_id != request.dialogue_id or dialogue.version != request.expected_dialogue_version:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.CONFLICT, None, dialogue, None,
                                        DialogueInterruptReason.STALE_REQUEST)
            )
        if dialogue.server_id != self._server_id:
            raise _invariant()
        if dialogue.state is DialogueState.INTERRUPTING:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, None, dialogue, None,
                                        DialogueInterruptReason.INTERRUPT_IN_PROGRESS)
            )
        if dialogue.state is not DialogueState.TURN_RUNNING:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, None, dialogue, None,
                                        DialogueInterruptReason.DIALOGUE_NOT_RUNNING)
            )
        try:
            job = await TurnJobRepository(self._storage).get(request.job_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if job is None:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, None, dialogue, None,
                                        DialogueInterruptReason.JOB_NOT_RUNNING)
            )
        if job.dialogue_id != dialogue.dialogue_id or job.server_id != dialogue.server_id or job.profile_id != dialogue.profile_id:
            raise _invariant()
        if dialogue.thread_id is None:
            raise _invariant()
        if job.thread_id is not None and job.thread_id != dialogue.thread_id:
            raise _invariant()
        if job.state is not TurnJobState.CODEX_RUNNING or job.thread_id is None or job.codex_turn_id is None:
            return self._raise_preflight(DialogueInterruptResult(
                DialogueInterruptStatus.BLOCKED, job, dialogue, None,
                DialogueInterruptReason.JOB_NOT_RUNNING,
            ))
        if job.version != request.expected_job_version:
            raise _PreflightResult(
                DialogueInterruptResult(DialogueInterruptStatus.CONFLICT, job, dialogue, None,
                                        DialogueInterruptReason.STALE_REQUEST)
            )
        try:
            binding = self._registry.lookup(job.job_id)
        except Exception:
            raise _invariant() from None
        if binding is None:
            raise _PreflightResult(DialogueInterruptResult(
                DialogueInterruptStatus.BLOCKED, job, dialogue, None,
                DialogueInterruptReason.ACTIVE_BINDING_UNAVAILABLE,
            ))
        if type(binding) is not TurnBinding:
            raise _invariant()
        if (
            binding.profile_id != job.profile_id
            or binding.thread_id != job.thread_id
            or binding.turn_id != job.codex_turn_id
        ):
            raise _invariant()
        return dialogue, job, binding

    @staticmethod
    def _raise_preflight(result: DialogueInterruptResult):
        raise _PreflightResult(result)

    async def _orchestrate(
        self,
        request: DialogueInterruptRequest,
        dialogue: DialogueRecord,
        job: TurnJobRecord,
        binding: TurnBinding,
    ) -> DialogueInterruptResult:
        coordinator = InterruptCoordinationRepository(self._storage, now_ms=self._clock)
        try:
            claimed = await coordinator.claim_interrupt(
                dialogue_id=request.dialogue_id,
                job_id=request.job_id,
                expected_dialogue_version=request.expected_dialogue_version,
                expected_job_version=request.expected_job_version,
            )
        except RepositoryError as error:
            if error.category in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT):
                return await self._claim_lost(request)
            raise _repository_error(error) from None
        except StorageError as error:
            raise _repository_error(error) from None
        if (
            not isinstance(claimed, TurnJobFinishResult)
            or claimed.job != job
            or claimed.dialogue.dialogue_id != dialogue.dialogue_id
            or claimed.dialogue.state is not DialogueState.INTERRUPTING
            or claimed.dialogue.version != dialogue.version + 1
        ):
            raise _invariant()

        interrupt_result: object
        try:
            interrupt_result = await self._turn_lifecycle.interrupt_turn(binding)
        except asyncio.CancelledError:
            interrupt_result = None
        except Exception:
            interrupt_result = None

        validated = self._valid_interrupt_terminal(interrupt_result, binding)
        if validated is not None:
            outcome, error_class, messages = _project_terminal(validated, binding)
            return await self._terminal_result(
                coordinator, request, job, claimed.dialogue, binding,
                outcome, error_class, messages,
                self._interrupt_status(interrupt_result),
            )

        if (
            type(interrupt_result) is TurnInterruptResult
            and interrupt_result.binding is binding
            and type(interrupt_result.status) is TurnInterruptStatus
            and interrupt_result.status is TurnInterruptStatus.REJECTED
            and self._valid_terminal(interrupt_result.terminal_result, binding)
        ):
            outcome, error_class, messages = _project_terminal(interrupt_result.terminal_result, binding)
            return await self._terminal_result(
                coordinator, request, job, claimed.dialogue, binding,
                outcome, error_class, messages, DialogueInterruptStatus.RECONCILED,
            )

        if type(interrupt_result) is TurnInterruptResult and interrupt_result.binding is binding \
                and type(interrupt_result.status) is TurnInterruptStatus \
                and interrupt_result.status is TurnInterruptStatus.REJECTED \
                and interrupt_result.terminal_result is None:
            return await self._restore_or_reconcile(coordinator, request, job, claimed.dialogue)

        terminal = await self._collect_once(binding)
        if self._valid_terminal(terminal, binding):
            outcome, error_class, messages = _project_terminal(terminal, binding)
            if outcome in (TurnTerminalOutcome.COMPLETED, TurnTerminalOutcome.FAILED):
                return await self._terminal_result(
                    coordinator, request, job, claimed.dialogue, binding,
                    outcome, error_class, messages, DialogueInterruptStatus.RECONCILED,
                )
        messages = terminal.messages if self._valid_terminal_shape(terminal, binding) else ()
        return await self._terminal_result(
            coordinator, request, job, claimed.dialogue, binding,
            TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", messages, DialogueInterruptStatus.UNKNOWN,
        )

    async def _restore_or_reconcile(self, coordinator, request, job, claimed_dialogue):
        try:
            restored = await coordinator.restore_rejected_interrupt(
                dialogue_id=request.dialogue_id,
                job_id=request.job_id,
                claimed_dialogue_version=claimed_dialogue.version,
                expected_job_version=job.version,
            )
            if restored.dialogue.state is not DialogueState.TURN_RUNNING:
                raise _invariant()
            return DialogueInterruptResult(
                DialogueInterruptStatus.REJECTED, restored.job, restored.dialogue, None, None
            )
        except RepositoryError as error:
            if error.category not in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT):
                raise _repository_error(error) from None
        except StorageError as error:
            raise _repository_error(error) from None
        try:
            current_dialogue = await DialogueRepository(self._storage).get_live()
            current_job = await TurnJobRepository(self._storage).get(request.job_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if current_dialogue is None or current_job is None:
            raise _invariant()
        if current_job.state in (TurnJobState.CODEX_COMPLETED, TurnJobState.FAILED, TurnJobState.UNKNOWN):
            try:
                reconciled = await coordinator.reconcile_natural_terminal(
                    dialogue_id=request.dialogue_id, job_id=request.job_id,
                    profile_id=job.profile_id, thread_id=job.thread_id,
                    codex_turn_id=job.codex_turn_id,
                    base_dialogue_version=request.expected_dialogue_version,
                    expected_job_version=request.expected_job_version,
                    outcome=TurnTerminalOutcome.UNKNOWN,
                    error_class="CODEX_AMBIGUOUS",
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            return DialogueInterruptResult(DialogueInterruptStatus.RECONCILED, reconciled.job, reconciled.dialogue, reconciled.output_payload, None)
        raise _invariant()

    async def _terminal_result(
        self, coordinator, request, job, claimed_dialogue, binding,
        outcome, error_class, messages, requested_status,
    ) -> DialogueInterruptResult:
        try:
            output_id, output_content, output_expiry = _prepare_output(
                self._clock, self._id_factory, outcome, messages
            )
        except DialogueInterruptError:
            raise
        except Exception:
            raise _invariant() from None
        try:
            finished = await coordinator.terminalize_interrupt(
                dialogue_id=request.dialogue_id,
                job_id=request.job_id,
                profile_id=job.profile_id,
                thread_id=job.thread_id,
                codex_turn_id=job.codex_turn_id,
                claimed_dialogue_version=claimed_dialogue.version,
                expected_job_version=job.version,
                outcome=outcome,
                error_class=None if outcome is TurnTerminalOutcome.COMPLETED else error_class,
                output_payload_id=output_id,
                output_content=output_content,
                output_expires_at_ms=output_expiry,
            )
        except RepositoryError as error:
            if error.category in (RepositoryErrorCategory.VERSION_CONFLICT, RepositoryErrorCategory.STATE_CONFLICT):
                raise _invariant() from None
            raise _repository_error(error) from None
        except StorageError as error:
            raise _repository_error(error) from None
        if not isinstance(finished, TurnJobFinishResult):
            raise _invariant()
        if requested_status is DialogueInterruptStatus.UNKNOWN and outcome in (TurnTerminalOutcome.COMPLETED, TurnTerminalOutcome.FAILED):
            requested_status = DialogueInterruptStatus.RECONCILED
        return DialogueInterruptResult(
            requested_status,
            finished.job,
            finished.dialogue,
            finished.output_payload,
            None,
        )

    async def _claim_lost(self, request: DialogueInterruptRequest) -> DialogueInterruptResult:
        try:
            dialogue = await DialogueRepository(self._storage).get_live()
            job = await TurnJobRepository(self._storage).get(request.job_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if dialogue is not None and dialogue.state is DialogueState.INTERRUPTING:
            return DialogueInterruptResult(DialogueInterruptStatus.BLOCKED, job, dialogue, None, DialogueInterruptReason.INTERRUPT_IN_PROGRESS)
        return DialogueInterruptResult(DialogueInterruptStatus.CONFLICT, job, dialogue, None, DialogueInterruptReason.STALE_REQUEST)

    async def _collect_once(self, binding: TurnBinding) -> TurnTerminalResult | None:
        try:
            return await self._turn_lifecycle.wait_turn(binding)
        except BaseException:
            return None

    @staticmethod
    def _valid_terminal_shape(value: object, binding: TurnBinding) -> bool:
        return (
            type(value) is TurnTerminalResult
            and (value.binding is binding or value.binding == binding)
            and type(value.status) is TurnTerminalStatus
        )

    @classmethod
    def _valid_terminal(cls, value: object, binding: TurnBinding) -> bool:
        return cls._valid_terminal_shape(value, binding) and value.status in (
            TurnTerminalStatus.COMPLETED, TurnTerminalStatus.FAILED
        )

    @classmethod
    def _valid_interrupt_terminal(cls, value: object, binding: TurnBinding) -> TurnTerminalResult | None:
        if type(value) is not TurnInterruptResult or value.binding is not binding:
            return None
        if type(value.status) is not TurnInterruptStatus:
            return None
        if value.status not in (TurnInterruptStatus.CONFIRMED, TurnInterruptStatus.RECONCILED):
            return None
        terminal = value.terminal_result
        if not cls._valid_terminal(terminal, binding):
            return None
        return terminal

    @staticmethod
    def _interrupt_status(value: object) -> DialogueInterruptStatus:
        if type(value) is TurnInterruptResult and value.status is TurnInterruptStatus.CONFIRMED:
            return DialogueInterruptStatus.CONFIRMED
        return DialogueInterruptStatus.RECONCILED

    async def _await_owned(self, task: asyncio.Task[DialogueInterruptResult]) -> DialogueInterruptResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None


class _PreflightResult(Exception):
    def __init__(self, result: DialogueInterruptResult) -> None:
        self.result = result
