"""The final local composition of the accepted P3--P6 application slices."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable

from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.errors import CodexAdapterError, CodexAdapterErrorCategory
from codex_control.adapters.codex.protocol import CodexProtocolClient, InboundServerRequest
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    CodexTurnLifecycleAdapter,
    MAX_AGENT_MESSAGE_CHARS,
    MAX_AGENT_MESSAGES_PER_TURN,
    MAX_TOTAL_AGENT_MESSAGE_CHARS,
    TurnBinding,
    TurnInterruptResult,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.adapters.telegram.fleet_status_render import TelegramFleetStatusRenderer
from codex_control.application.dialogue_recovery import (
    DialogueRecoveryError,
    DialogueRecoveryErrorCategory,
    DialogueRecoveryResult,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.application.fleet_group_routing import (
    FleetGroupRoutingService,
    GroupRoutingError,
    GroupRoutingErrorCategory,
    GroupRoutingResult,
    GroupRoutingStatus,
)
from codex_control.application.existing_dialogue_turn import (
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    ExistingDialogueTurnStatus,
)
from codex_control.application.fleet_status import FleetStatusService
from codex_control.application.live_approval import (
    ApprovalDecisionSignal,
    ApprovalTurnBinding,
    DurableApprovalOperator,
    OwnedApprovalResponseService,
)
from codex_control.application.private_control import (
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlError,
    PrivateControlErrorCategory,
    PrivateControlResult,
    PrivateControlService,
    PrivateControlStatus,
)
from codex_control.application.response_delivery import (
    TelegramDeliveryEffectResult,
    TelegramDeliveryEffectStatus,
    TelegramDeliveryPort,
    TurnDeliveryError,
    TurnDeliveryRequest,
    TurnDeliveryResult,
    TurnDeliveryService,
    TurnDeliveryStatus,
)
from codex_control.application.fleet_control import GroupInboundUpdate
from codex_control.storage import (
    ApprovalRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
)
from codex_control.storage.application_recovery import ApplicationRecoveryRepository


P63_STARTUP_DELIVERY_MAX_JOBS = 256
P63_WORK_STATUS_TEXT_MAX_CHARS = 1024
_MAX_SIGNED_64 = 9_223_372_036_854_775_807


class WorkStatusAttempt(StrEnum):
    SKIPPED = "SKIPPED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class LocalStartupStatus(StrEnum):
    READY = "READY"
    LIMIT_REACHED = "LIMIT_REACHED"


class LocalOrchestrationErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    CODEX = "CODEX"
    TELEGRAM = "TELEGRAM"
    INVARIANT = "INVARIANT"


class LocalOrchestrationError(Exception):
    """Finite, content-free local composition diagnostic."""

    def __init__(self, category: LocalOrchestrationErrorCategory | str) -> None:
        try:
            self.category = (
                category
                if isinstance(category, LocalOrchestrationErrorCategory)
                else LocalOrchestrationErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = LocalOrchestrationErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"LocalOrchestrationError({self.category.value!r})"


def _invalid() -> LocalOrchestrationError:
    return LocalOrchestrationError(LocalOrchestrationErrorCategory.INVALID_ARGUMENT)


def _invariant() -> LocalOrchestrationError:
    return LocalOrchestrationError(LocalOrchestrationErrorCategory.INVARIANT)


def _map_delivery_error(error: TurnDeliveryError) -> LocalOrchestrationError:
    if error.category.value == "INVALID_ARGUMENT":
        return _invalid()
    if error.category.value == "STORAGE":
        return LocalOrchestrationError(LocalOrchestrationErrorCategory.STORAGE)
    return _invariant()


def _map_local_error(error: BaseException) -> LocalOrchestrationError:
    if isinstance(error, LocalOrchestrationError):
        return error
    if isinstance(error, RepositoryError):
        return _invariant() if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION else LocalOrchestrationError(LocalOrchestrationErrorCategory.STORAGE)
    if isinstance(error, StorageError):
        return LocalOrchestrationError(LocalOrchestrationErrorCategory.STORAGE)
    if isinstance(error, TurnLifecycleError):
        return LocalOrchestrationError(LocalOrchestrationErrorCategory.CODEX)
    if isinstance(error, TurnDeliveryError):
        return _map_delivery_error(error)
    if isinstance(error, GroupRoutingError):
        mapping = {
            GroupRoutingErrorCategory.INVALID_ARGUMENT: LocalOrchestrationErrorCategory.INVALID_ARGUMENT,
            GroupRoutingErrorCategory.STORAGE: LocalOrchestrationErrorCategory.STORAGE,
            GroupRoutingErrorCategory.CODEX: LocalOrchestrationErrorCategory.CODEX,
            GroupRoutingErrorCategory.INVARIANT: LocalOrchestrationErrorCategory.INVARIANT,
        }
        return LocalOrchestrationError(mapping.get(error.category, LocalOrchestrationErrorCategory.INVARIANT))
    if isinstance(error, DialogueApplicationError):
        mapping = {
            DialogueApplicationErrorCategory.INVALID_ARGUMENT: LocalOrchestrationErrorCategory.INVALID_ARGUMENT,
            DialogueApplicationErrorCategory.STORAGE: LocalOrchestrationErrorCategory.STORAGE,
            DialogueApplicationErrorCategory.CODEX: LocalOrchestrationErrorCategory.CODEX,
            DialogueApplicationErrorCategory.INVARIANT: LocalOrchestrationErrorCategory.INVARIANT,
        }
        return LocalOrchestrationError(mapping.get(error.category, LocalOrchestrationErrorCategory.INVARIANT))
    if isinstance(error, DialogueRecoveryError):
        mapping = {
            DialogueRecoveryErrorCategory.STORAGE: LocalOrchestrationErrorCategory.STORAGE,
            DialogueRecoveryErrorCategory.INVARIANT: LocalOrchestrationErrorCategory.INVARIANT,
        }
        return LocalOrchestrationError(mapping.get(error.category, LocalOrchestrationErrorCategory.INVARIANT))
    if isinstance(error, PrivateControlError):
        mapping = {
            PrivateControlErrorCategory.INVALID_ARGUMENT: LocalOrchestrationErrorCategory.INVALID_ARGUMENT,
            PrivateControlErrorCategory.STORAGE: LocalOrchestrationErrorCategory.STORAGE,
            PrivateControlErrorCategory.INVARIANT: LocalOrchestrationErrorCategory.INVARIANT,
        }
        return LocalOrchestrationError(mapping.get(error.category, LocalOrchestrationErrorCategory.INVARIANT))
    if isinstance(error, asyncio.CancelledError):
        raise error
    return _invariant()


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _clock_value(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise _invariant() from None
    if type(value) is not int or not 0 <= value <= _MAX_SIGNED_64:
        raise _invariant()
    return value


@dataclass(frozen=True, repr=False)
class LocalGroupResult:
    routing: GroupRoutingResult
    delivery: TurnDeliveryResult | None
    fleet_status_payload: dict[str, str] | None
    acknowledgement_status: WorkStatusAttempt
    terminal_status: WorkStatusAttempt

    def __post_init__(self) -> None:
        if type(self.routing) is not GroupRoutingResult:
            raise _invariant()
        if type(self.acknowledgement_status) is not WorkStatusAttempt:
            raise _invariant()
        if type(self.terminal_status) is not WorkStatusAttempt:
            raise _invariant()
        if self.delivery is not None and type(self.delivery) is not TurnDeliveryResult:
            raise _invariant()
        if self.fleet_status_payload is not None:
            if type(self.fleet_status_payload) is not dict or set(self.fleet_status_payload) != {"text"}:
                raise _invariant()
            if type(self.fleet_status_payload["text"]) is not str:
                raise _invariant()

        if self.routing.status is GroupRoutingStatus.STATUS:
            if self.fleet_status_payload is None or self.delivery is not None:
                raise _invariant()
            if self.acknowledgement_status is not WorkStatusAttempt.SKIPPED or self.terminal_status is not WorkStatusAttempt.SKIPPED:
                raise _invariant()
        elif self.routing.status is GroupRoutingStatus.PROMPT:
            turn = self.routing.turn_result
            if turn is None or self.fleet_status_payload is not None:
                raise _invariant()
            if turn.status is ExistingDialogueTurnStatus.COMPLETED:
                if (
                    self.delivery is None
                    or self.delivery.status is TurnDeliveryStatus.BLOCKED
                    or self.terminal_status is not WorkStatusAttempt.SKIPPED
                    or self.acknowledgement_status is WorkStatusAttempt.SKIPPED
                ):
                    raise _invariant()
            elif turn.status in (ExistingDialogueTurnStatus.FAILED, ExistingDialogueTurnStatus.UNKNOWN):
                if self.delivery is not None or self.acknowledgement_status is WorkStatusAttempt.SKIPPED or self.terminal_status is WorkStatusAttempt.SKIPPED:
                    raise _invariant()
            else:
                raise _invariant()
        else:
            if self.delivery is not None or self.fleet_status_payload is not None:
                raise _invariant()
            if self.acknowledgement_status is not WorkStatusAttempt.SKIPPED or self.terminal_status is not WorkStatusAttempt.SKIPPED:
                raise _invariant()

    def __repr__(self) -> str:
        return (
            "LocalGroupResult(routing='[REDACTED]', delivery='[REDACTED]', "
            "fleet_status_payload='[REDACTED]', "
            f"acknowledgement_status={self.acknowledgement_status.value!r}, "
            f"terminal_status={self.terminal_status.value!r})"
        )


@dataclass(frozen=True, repr=False)
class LocalStartupResult:
    status: LocalStartupStatus
    dialogue_recovery: DialogueRecoveryResult
    delivery_statuses: tuple[TurnDeliveryStatus, ...]
    approvals_cancelled: int

    def __post_init__(self) -> None:
        if type(self.status) is not LocalStartupStatus or type(self.dialogue_recovery) is not DialogueRecoveryResult:
            raise _invariant()
        if type(self.delivery_statuses) is not tuple or len(self.delivery_statuses) > P63_STARTUP_DELIVERY_MAX_JOBS:
            raise _invariant()
        if any(type(status) is not TurnDeliveryStatus for status in self.delivery_statuses):
            raise _invariant()
        if any(status is TurnDeliveryStatus.BLOCKED for status in self.delivery_statuses):
            raise _invariant()
        if type(self.approvals_cancelled) is not int or not 0 <= self.approvals_cancelled <= P63_STARTUP_DELIVERY_MAX_JOBS:
            raise _invariant()
        if self.status is LocalStartupStatus.LIMIT_REACHED and len(self.delivery_statuses) != P63_STARTUP_DELIVERY_MAX_JOBS:
            raise _invariant()

    def __repr__(self) -> str:
        values = tuple(status.value for status in self.delivery_statuses)
        return (
            "LocalStartupResult(status="
            f"{self.status.value!r}, dialogue_recovery='[REDACTED]', "
            f"delivery_statuses={values!r}, approvals_cancelled={self.approvals_cancelled!r})"
        )


@dataclass
class _Lease:
    binding: TurnBinding
    runtime: Any
    job_id: str
    acknowledgement_status: WorkStatusAttempt
    hint_id: int | None
    wait_started: bool = False
    shutdown_called: bool = False


class _CaptureManager:
    def __init__(self, owner: "ApprovalAwareTurnLifecycle") -> None:
        self._owner = owner
        self._captured: Any | None = None

    async def acquire(self, profile_id: str) -> Any:
        if self._owner._capture_owner is None:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_OPERATION_BUSY)
        if self._captured is not None:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_OPERATION_BUSY)
        runtime = await self._owner._runtime_manager.acquire(profile_id)
        self._captured = runtime
        return runtime


class _ImmediateDeny:
    async def decide(self, request: object) -> ApprovalDecision:
        return ApprovalDecision.DENY


class ApprovalAwareTurnLifecycle:
    """P1.6 lifecycle composition with exact runtime and P6.2 ownership."""

    def __init__(
        self,
        storage: SqliteStorage,
        *,
        runtime_manager: object,
        model_catalog: object,
        telegram: TelegramDeliveryPort,
        approval_signal: ApprovalDecisionSignal,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
        approval_sleep: Callable[[float], Any] | None = None,
    ) -> None:
        if type(storage) is not SqliteStorage:
            raise _invalid()
        if not _async_callable(runtime_manager, "acquire") or not _async_callable(runtime_manager, "shutdown_profile"):
            raise _invalid()
        if not _async_callable(model_catalog, "get_catalog"):
            raise _invalid()
        if not _async_callable(telegram, "create_message") or not _async_callable(telegram, "edit_message"):
            raise _invalid()
        if type(approval_signal) is not ApprovalDecisionSignal:
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        if approval_sleep is not None and not (
            inspect.iscoroutinefunction(approval_sleep)
            or inspect.iscoroutinefunction(getattr(approval_sleep, "__call__", None))
        ):
            raise _invalid()
        self._storage = storage
        self._runtime_manager = runtime_manager
        self._model_catalog = model_catalog
        self._telegram = telegram
        self._approval_signal = approval_signal
        self._clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
        self._id_factory = id_factory
        self._approval_sleep = approval_sleep
        self._capture_owner: object | None = None
        self._lease: _Lease | None = None
        self._hints: dict[str, tuple[WorkStatusAttempt, int | None]] = {}
        self._capture_manager = _CaptureManager(self)
        self._delegate = CodexTurnLifecycleAdapter(self._capture_manager, model_catalog)

    async def start_turn(
        self,
        *,
        thread_binding: Any,
        model_id: str,
        reasoning_effort: str | None,
        user_text: str,
        working_directory: Any,
    ) -> TurnStartResult:
        owner = object()
        if self._capture_owner is not None or self._lease is not None:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_OPERATION_BUSY)
        self._capture_owner = owner
        capture = self._capture_manager
        capture._captured = None
        try:
            snapshot = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
            if (
                snapshot.dialogue is None
                or snapshot.dialogue.state.value != "TURN_RUNNING"
                or len(snapshot.active_jobs) != 1
            ):
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
            job = snapshot.active_jobs[0]
            if (
                job.state is not TurnJobState.CODEX_STARTING
                or job.profile_id != getattr(thread_binding, "profile_id", None)
                or job.thread_id != getattr(thread_binding, "thread_id", None)
                or job.model_id != model_id
                or job.reasoning_effort != reasoning_effort
                or job.codex_turn_id is not None
                or not isinstance(job.model_id, str)
                or not isinstance(job.reasoning_effort, str)
            ):
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)

            acknowledgement, hint_id = await self._work_status(job, "⏳ Выполняю запрос")
            self._hints[job.job_id] = (acknowledgement, hint_id)
            result = await self._delegate.start_turn(
                thread_binding=thread_binding,
                model_id=model_id,
                reasoning_effort=reasoning_effort,
                user_text=user_text,
                working_directory=working_directory,
            )
            if type(result) is not TurnStartResult:
                raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_START_UNKNOWN)
            if result.status is TurnStartStatus.CONFIRMED:
                if not isinstance(result.binding, TurnBinding) or capture._captured is None:
                    raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_START_UNKNOWN)
                if capture._captured.profile_id != result.binding.profile_id:
                    raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
                self._lease = _Lease(result.binding, capture._captured, job.job_id, acknowledgement, hint_id)
            return result
        finally:
            if self._capture_owner is owner:
                self._capture_owner = None
            if self._lease is None:
                capture._captured = None

    async def wait_turn(self, binding: TurnBinding) -> TurnTerminalResult:
        lease = self._lease
        if type(binding) is not TurnBinding or lease is None or lease.binding is not binding:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        job = await self._running_job(lease)
        lease.wait_started = True
        client = lease.runtime.client
        if type(client) is not CodexProtocolClient:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN)
        approval_binding = ApprovalTurnBinding(job.job_id, job.profile_id, job.thread_id or "", job.codex_turn_id or "")
        operator = DurableApprovalOperator(
            self._storage,
            binding=approval_binding,
            signal=self._approval_signal,
            now_ms=self._clock,
            id_factory=self._id_factory,
            sleep=self._approval_sleep,
        )
        response_service = OwnedApprovalResponseService(job.profile_id, client, operator)
        turn_task = asyncio.create_task(self._delegate.wait_turn(binding))
        get_task: asyncio.Task[Any] | None = None
        handler_task: asyncio.Task[Any] | None = None
        try:
            while True:
                if handler_task is None:
                    get_task = asyncio.create_task(client.next_server_request())
                    done = await self._wait_first(turn_task, get_task)
                    if turn_task in done:
                        terminal = await self._task_value(turn_task)
                        inbound = await self._cancel_get_and_capture(get_task, client)
                        get_task = None
                        if inbound is not None:
                            await self._immediate_deny(client, job.profile_id, inbound)
                            await self._shutdown_once(lease)
                            return self._unknown_projection(binding, terminal)
                        return self._terminal_projection(binding, terminal)
                    inbound = await self._task_value(get_task)
                    get_task = None
                    if type(inbound) is not InboundServerRequest or client.owns_server_request(inbound) is not True:
                        await self._shutdown_once(lease)
                        terminal = await self._task_value(turn_task)
                        return self._unknown_projection(binding, terminal)
                    handler_task = asyncio.create_task(response_service.handle_owned(inbound))

                done = await self._wait_first(turn_task, handler_task)
                if turn_task in done and handler_task not in done:
                    await self._shutdown_once(lease)
                    handled = await self._task_value(handler_task)
                    if not self._response_unknown(handled):
                        raise _invariant()
                    terminal = await self._task_value(turn_task)
                    return self._unknown_projection(binding, terminal)
                if handler_task in done:
                    handled = await self._task_value(handler_task)
                    handler_task = None
                    if self._response_unknown(handled):
                        terminal = await self._task_value(turn_task)
                        return self._unknown_projection(binding, terminal)
                    if not self._response_allowed_or_denied(handled):
                        raise _invariant()
                    if turn_task.done():
                        terminal = await self._task_value(turn_task)
                        return self._terminal_projection(binding, terminal)
        finally:
            if get_task is not None:
                await self._cancel_join(get_task)
            if handler_task is not None:
                if not handler_task.done():
                    await self._shutdown_once(lease)
                await self._observe(handler_task)
            await self._observe(turn_task)

    async def interrupt_turn(self, binding: TurnBinding) -> TurnInterruptResult:
        lease = self._lease
        if type(binding) is not TurnBinding or lease is None or lease.binding is not binding:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE)
        return await self._delegate.interrupt_turn(binding)

    async def _running_job(self, lease: _Lease) -> TurnJobRecord:
        try:
            job = await TurnJobRepository(self._storage).get(lease.job_id)
        except Exception:
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED) from None
        if (
            type(job) is not TurnJobRecord
            or job.state is not TurnJobState.CODEX_RUNNING
            or job.profile_id != lease.binding.profile_id
            or job.thread_id != lease.binding.thread_id
            or job.codex_turn_id != lease.binding.turn_id
        ):
            raise TurnLifecycleError(CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED)
        return job

    async def _work_status(self, job: TurnJobRecord, prefix: str) -> tuple[WorkStatusAttempt, int | None]:
        text = "\n".join((prefix, f"Сервер: {job.server_id}", f"Профиль: {job.profile_id}", f"Модель: {job.model_id}", f"Рассуждение: {job.reasoning_effort}"))
        if len(text) > P63_WORK_STATUS_TEXT_MAX_CHARS:
            return WorkStatusAttempt.UNKNOWN, None
        try:
            task = asyncio.create_task(self._telegram.create_message(chat_id=job.source_chat_id, text=text))
        except Exception:
            return WorkStatusAttempt.UNKNOWN, None
        result = await self._task_value(task)
        if (
            type(result) is TelegramDeliveryEffectResult
            and result.status is TelegramDeliveryEffectStatus.CONFIRMED
            and type(result.message_id) is int
            and not isinstance(result.message_id, bool)
            and 1 <= result.message_id <= _MAX_SIGNED_64
        ):
            return WorkStatusAttempt.CONFIRMED, result.message_id
        if type(result) is TelegramDeliveryEffectResult and result.status is TelegramDeliveryEffectStatus.FAILED:
            return WorkStatusAttempt.FAILED, None
        return WorkStatusAttempt.UNKNOWN, None

    async def _finish_live_status(self, job: TurnJobRecord, status: TurnJobState) -> tuple[WorkStatusAttempt, WorkStatusAttempt]:
        lease = self._lease
        acknowledgement, stored_hint = self._hints.get(job.job_id, (WorkStatusAttempt.UNKNOWN, None))
        if lease is not None and lease.job_id == job.job_id:
            acknowledgement, stored_hint = lease.acknowledgement_status, lease.hint_id
        hint = stored_hint if acknowledgement is WorkStatusAttempt.CONFIRMED else None
        prefix = "❌ Выполнение завершилось с ошибкой" if status is TurnJobState.FAILED else "⚠️ Результат выполнения не подтверждён"
        text = "\n".join((prefix, f"Сервер: {job.server_id}", f"Профиль: {job.profile_id}", f"Модель: {job.model_id}", f"Рассуждение: {job.reasoning_effort}"))
        try:
            if len(text) > P63_WORK_STATUS_TEXT_MAX_CHARS:
                terminal = WorkStatusAttempt.UNKNOWN
            else:
                try:
                    if hint is None:
                        task = asyncio.create_task(self._telegram.create_message(chat_id=job.source_chat_id, text=text))
                    else:
                        task = asyncio.create_task(self._telegram.edit_message(chat_id=job.source_chat_id, message_id=hint, text=text))
                    result = await self._task_value(task)
                    terminal = self._map_status_result(result, hint)
                except Exception:
                    terminal = WorkStatusAttempt.UNKNOWN
        finally:
            self._clear_lease(job.job_id)
        return acknowledgement, terminal

    def _hint_for_job(self, job_id: str) -> tuple[WorkStatusAttempt, int | None]:
        lease = self._lease
        if lease is not None and lease.job_id == job_id:
            return lease.acknowledgement_status, lease.hint_id
        return self._hints.get(job_id, (WorkStatusAttempt.UNKNOWN, None))

    def _clear_job(self, job_id: str) -> None:
        self._clear_lease(job_id)

    async def _cleanup_unconsumed_confirmed(self, job_id: str) -> None:
        lease = self._lease
        if lease is None or lease.job_id != job_id or lease.wait_started:
            return
        await self._shutdown_once(lease)
        self._clear_lease(job_id)

    def _clear_lease(self, job_id: str) -> None:
        if self._lease is not None and self._lease.job_id == job_id:
            self._lease = None
        self._hints.pop(job_id, None)

    async def _shutdown_once(self, lease: _Lease) -> None:
        if lease.shutdown_called:
            return
        lease.shutdown_called = True
        try:
            task = asyncio.create_task(self._runtime_manager.shutdown_profile(lease.binding.profile_id))
        except Exception:
            return
        await self._observe(task)

    async def _immediate_deny(self, client: CodexProtocolClient, profile_id: str, inbound: InboundServerRequest) -> None:
        bridge = CodexApprovalBridge(profile_id=profile_id, client=client, operator=_ImmediateDeny())
        task = asyncio.create_task(bridge.handle_request(inbound))
        await self._observe(task)

    @staticmethod
    def _map_status_result(result: object, hint: int | None) -> WorkStatusAttempt:
        if type(result) is not TelegramDeliveryEffectResult:
            return WorkStatusAttempt.UNKNOWN
        if result.status is TelegramDeliveryEffectStatus.CONFIRMED:
            if hint is None or result.message_id == hint:
                return WorkStatusAttempt.CONFIRMED
            return WorkStatusAttempt.UNKNOWN
        if result.status is TelegramDeliveryEffectStatus.FAILED:
            return WorkStatusAttempt.FAILED
        return WorkStatusAttempt.UNKNOWN

    @staticmethod
    def _response_unknown(value: object) -> bool:
        return getattr(getattr(value, "status", None), "value", None) == "response_unknown"

    @staticmethod
    def _response_allowed_or_denied(value: object) -> bool:
        return getattr(getattr(value, "status", None), "value", None) in {"allowed", "denied"}

    @staticmethod
    async def _task_value(task: asyncio.Task[Any]) -> Any:
        while True:
            try:
                value = await asyncio.shield(task)
                return value
            except asyncio.CancelledError:
                if task.cancelled():
                    return None
                continue
            except BaseException:
                return None

    @staticmethod
    async def _await_propagating(task: asyncio.Task[Any]) -> Any:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise
                continue

    @classmethod
    async def _observe(cls, task: asyncio.Task[Any]) -> Any:
        return await cls._task_value(task)

    @classmethod
    async def _cancel_join(cls, task: asyncio.Task[Any]) -> Any:
        if not task.done():
            task.cancel()
        return await cls._observe(task)

    @classmethod
    async def _wait_first(cls, *tasks: asyncio.Task[Any]) -> set[asyncio.Task[Any]]:
        waiter = asyncio.create_task(asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))
        value = await cls._task_value(waiter)
        if not value:
            return {tasks[0]}
        return value[0]

    @classmethod
    async def _cancel_get_and_capture(cls, task: asyncio.Task[Any], client: CodexProtocolClient) -> InboundServerRequest | None:
        if not task.done():
            task.cancel()
        await cls._observe(task)
        if task.cancelled() or not task.done():
            return None
        try:
            inbound = task.result()
        except BaseException:
            return None
        return inbound if type(inbound) is InboundServerRequest and client.owns_server_request(inbound) is True else None

    @staticmethod
    def _terminal_projection(binding: TurnBinding, terminal: object) -> TurnTerminalResult:
        if type(terminal) is TurnTerminalResult and terminal.binding is binding:
            return terminal
        return TurnTerminalResult(binding, TurnTerminalStatus.UNKNOWN, (), CodexAdapterError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN))

    @staticmethod
    def _unknown_projection(binding: TurnBinding, terminal: object) -> TurnTerminalResult:
        messages: tuple[AgentMessageCompleted, ...] = ()
        if type(terminal) is TurnTerminalResult and terminal.binding is binding and type(terminal.messages) is tuple:
            safe = tuple(
                message for message in terminal.messages
                if type(message) is AgentMessageCompleted
                and type(message.text) is str
                and "\x00" not in message.text
                and len(message.text) <= MAX_AGENT_MESSAGE_CHARS
            )
            if (
                len(safe) == len(terminal.messages)
                and len(safe) <= MAX_AGENT_MESSAGES_PER_TURN
                and sum(len(message.text) for message in safe) <= MAX_TOTAL_AGENT_MESSAGE_CHARS
            ):
                messages = safe
        return TurnTerminalResult(binding, TurnTerminalStatus.UNKNOWN, messages, CodexAdapterError(CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN))


class LocalControllerOrchestrator:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        group_routing: FleetGroupRoutingService,
        fleet_status: FleetStatusService,
        fleet_status_renderer: TelegramFleetStatusRenderer,
        private_control: PrivateControlService,
        turn_delivery: TurnDeliveryService,
        turn_lifecycle: ApprovalAwareTurnLifecycle,
        approval_signal: ApprovalDecisionSignal,
        dialogue_recovery: DialogueRecoveryService,
    ) -> None:
        if type(storage) is not SqliteStorage or type(turn_lifecycle) is not ApprovalAwareTurnLifecycle or type(approval_signal) is not ApprovalDecisionSignal:
            raise _invalid()
        for value, method in (
            (group_routing, "handle"), (private_control, "handle_command"),
            (private_control, "handle_callback"), (turn_delivery, "deliver"),
            (dialogue_recovery, "recover_startup"),
        ):
            if not _async_callable(value, method):
                raise _invalid()
        if not callable(getattr(fleet_status, "project", None)) or not callable(getattr(fleet_status_renderer, "render", None)):
            raise _invalid()
        self._storage = storage
        self._group_routing = group_routing
        self._fleet_status = fleet_status
        self._fleet_status_renderer = fleet_status_renderer
        self._private_control = private_control
        self._turn_delivery = turn_delivery
        self._turn_lifecycle = turn_lifecycle
        self._approval_signal = approval_signal
        self._dialogue_recovery = dialogue_recovery
        self._startup_task: asyncio.Task[LocalStartupResult] | None = None
        self._startup_lock = asyncio.Lock()

    async def handle_group(self, update: GroupInboundUpdate) -> LocalGroupResult:
        if type(update) is not GroupInboundUpdate:
            raise _invalid()
        task = asyncio.create_task(self._handle_group_owned(update))
        return await ApprovalAwareTurnLifecycle._await_propagating(task)

    async def _handle_group_owned(self, update: GroupInboundUpdate) -> LocalGroupResult:
        try:
            routing = await self._group_routing.handle(update)
            if type(routing) is not GroupRoutingResult:
                raise _invariant()
            if routing.status is GroupRoutingStatus.STATUS:
                projection = self._fleet_status.project(routing)
                payload = self._fleet_status_renderer.render(projection)
                if type(payload) is not dict or set(payload) != {"text"} or type(payload["text"]) is not str:
                    raise _invariant()
                return LocalGroupResult(routing, None, payload, WorkStatusAttempt.SKIPPED, WorkStatusAttempt.SKIPPED)
            if routing.status is not GroupRoutingStatus.PROMPT:
                return LocalGroupResult(routing, None, None, WorkStatusAttempt.SKIPPED, WorkStatusAttempt.SKIPPED)
            turn = routing.turn_result
            if turn is None or turn.job is None:
                raise _invariant()
            if turn.status is ExistingDialogueTurnStatus.COMPLETED:
                acknowledgement, hint = self._turn_lifecycle._hint_for_job(turn.job.job_id)
                try:
                    delivery = await self._turn_delivery.deliver(TurnDeliveryRequest(turn.job.job_id, hint if acknowledgement is WorkStatusAttempt.CONFIRMED else None))
                except TurnDeliveryError as error:
                    raise _map_delivery_error(error) from None
                finally:
                    self._turn_lifecycle._clear_job(turn.job.job_id)
                if type(delivery) is not TurnDeliveryResult or delivery.status is TurnDeliveryStatus.BLOCKED:
                    raise _invariant()
                return LocalGroupResult(routing, delivery, None, acknowledgement, WorkStatusAttempt.SKIPPED)
            if turn.status in (ExistingDialogueTurnStatus.FAILED, ExistingDialogueTurnStatus.UNKNOWN):
                if turn.status is ExistingDialogueTurnStatus.UNKNOWN:
                    await self._turn_lifecycle._cleanup_unconsumed_confirmed(turn.job.job_id)
                acknowledgement, terminal = await self._turn_lifecycle._finish_live_status(turn.job, TurnJobState.FAILED if turn.status is ExistingDialogueTurnStatus.FAILED else TurnJobState.UNKNOWN)
                return LocalGroupResult(routing, None, None, acknowledgement, terminal)
            raise _invariant()
        except LocalOrchestrationError:
            raise
        except Exception as error:
            raise _map_local_error(error) from None

    async def handle_private_command(self, request: PrivateCommandRequest) -> PrivateControlResult:
        if type(request) is not PrivateCommandRequest:
            raise _invalid()
        try:
            result = await self._private_control.handle_command(request)
        except Exception as error:
            raise _map_local_error(error) from None
        if type(result) is not PrivateControlResult:
            raise _invariant()
        return result

    async def handle_private_callback(self, request: PrivateCallbackRequest) -> PrivateControlResult:
        if type(request) is not PrivateCallbackRequest:
            raise _invalid()
        task = asyncio.create_task(self._private_control.handle_callback(request))
        try:
            result = await ApprovalAwareTurnLifecycle._await_propagating(task)
        except Exception as error:
            raise _map_local_error(error) from None
        if type(result) is not PrivateControlResult:
            raise _invariant()
        if result.status in {
            PrivateControlStatus.APPROVED,
            PrivateControlStatus.DENIED,
            PrivateControlStatus.EXPIRED,
            PrivateControlStatus.STALE,
            PrivateControlStatus.ALREADY_USED,
        }:
            self._approval_signal.notify()
        return result

    async def recover_startup(self) -> LocalStartupResult:
        async with self._startup_lock:
            task = self._startup_task
            if task is None or task.done():
                task = asyncio.create_task(self._recover_startup_owned())
                self._startup_task = task
        try:
            return await ApprovalAwareTurnLifecycle._await_propagating(task)
        except Exception as error:
            raise _map_local_error(error) from None
        finally:
            async with self._startup_lock:
                if self._startup_task is task and task.done():
                    self._startup_task = None

    async def _recover_startup_owned(self) -> LocalStartupResult:
        recovery = await self._dialogue_recovery.recover_startup()
        if type(recovery) is not DialogueRecoveryResult:
            raise _invariant()
        approvals_cancelled = 0
        if recovery.job is not None and recovery.status is not DialogueRecoveryStatus.NO_ACTION and recovery.job.state is not TurnJobState.CODEX_RUNNING:
            cancelled = await ApprovalRepository(self._storage).cancel_pending_for_job(recovery.job.job_id)
            if type(cancelled) is not tuple or len(cancelled) > P63_STARTUP_DELIVERY_MAX_JOBS:
                raise _invariant()
            approvals_cancelled = len(cancelled)

        statuses: list[TurnDeliveryStatus] = []
        jobs = TurnJobRepository(self._storage)
        for _ in range(P63_STARTUP_DELIVERY_MAX_JOBS):
            candidates = await jobs.list_delivery_candidates(limit=1)
            if not candidates:
                return LocalStartupResult(LocalStartupStatus.READY, recovery, tuple(statuses), approvals_cancelled)
            if len(candidates) != 1:
                raise _invariant()
            candidate = candidates[0]
            delivery = await self._turn_delivery.deliver(TurnDeliveryRequest(candidate.job_id))
            if type(delivery) is not TurnDeliveryResult or delivery.status is TurnDeliveryStatus.BLOCKED:
                raise _invariant()
            if delivery.status not in {
                TurnDeliveryStatus.DELIVERED,
                TurnDeliveryStatus.ALREADY_DELIVERED,
                TurnDeliveryStatus.FAILED,
                TurnDeliveryStatus.DELIVERY_UNKNOWN,
            }:
                raise _invariant()
            current = await jobs.get(candidate.job_id)
            if type(current) is not TurnJobRecord or current.state in {
                TurnJobState.CODEX_COMPLETED,
                TurnJobState.DELIVERY_PENDING,
                TurnJobState.DELIVERING,
            }:
                raise _invariant()
            statuses.append(delivery.status)

        remaining = await jobs.list_delivery_candidates(limit=1)
        return LocalStartupResult(
            LocalStartupStatus.LIMIT_REACHED if remaining else LocalStartupStatus.READY,
            recovery,
            tuple(statuses),
            approvals_cancelled,
        )


__all__ = [
    "P63_STARTUP_DELIVERY_MAX_JOBS",
    "P63_WORK_STATUS_TEXT_MAX_CHARS",
    "WorkStatusAttempt",
    "LocalStartupStatus",
    "LocalOrchestrationErrorCategory",
    "LocalOrchestrationError",
    "LocalGroupResult",
    "LocalStartupResult",
    "ApprovalAwareTurnLifecycle",
    "LocalControllerOrchestrator",
]
