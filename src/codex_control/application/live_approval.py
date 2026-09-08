"""Durable live approval coordination for one owned Codex request."""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from codex_control.adapters.codex.approvals import (
    APPROVAL_METHODS,
    ApprovalDecision,
    ApprovalError,
    ApprovalErrorCategory,
    ApprovalHandlingResult,
    ApprovalHandlingStatus,
    ApprovalKind,
    ApprovalRequest,
    CodexApprovalBridge,
)
from codex_control.adapters.codex.protocol import CodexProtocolClient, InboundServerRequest
from codex_control.storage import (
    ApprovalRecord,
    ApprovalRepository,
    ApprovalState,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnJobState,
)
from codex_control.storage.core_repositories import MAX_SQLITE_INT


P62_APPROVAL_TTL_MS = 900_000
P62_APPROVAL_PAYLOAD_RETENTION_MS = 900_000


class LiveApprovalErrorCategory(StrEnum):
    INVALID_ARGUMENT = "invalid_argument"
    STORAGE = "storage"
    INVARIANT = "invariant"

    def __str__(self) -> str:
        return self.value


class LiveApprovalError(Exception):
    """Finite, content-free application diagnostics."""

    def __init__(self, category: LiveApprovalErrorCategory) -> None:
        try:
            self.category = (
                category
                if isinstance(category, LiveApprovalErrorCategory)
                else LiveApprovalErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = LiveApprovalErrorCategory.INVALID_ARGUMENT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"LiveApprovalError({self.category.value!r})"


def _invalid() -> LiveApprovalError:
    return LiveApprovalError(LiveApprovalErrorCategory.INVALID_ARGUMENT)


def _is_bounded_string(value: object, limit: int) -> bool:
    return (
        type(value) is str
        and bool(value)
        and "\x00" not in value
        and len(value) <= limit
    )


def _validate_binding_value(value: object, limit: int) -> None:
    if not _is_bounded_string(value, limit):
        raise _invalid()


@dataclass(frozen=True, repr=False)
class ApprovalTurnBinding:
    job_id: str
    profile_id: str
    thread_id: str
    codex_turn_id: str

    def __post_init__(self) -> None:
        _validate_binding_value(self.job_id, 128)
        _validate_binding_value(self.profile_id, 128)
        _validate_binding_value(self.thread_id, 512)
        _validate_binding_value(self.codex_turn_id, 512)

    def __repr__(self) -> str:
        return "ApprovalTurnBinding(job_id='[REDACTED]', profile_id='[REDACTED]', thread_id='[REDACTED]', codex_turn_id='[REDACTED]')"


class _SignalWaiter:
    __slots__ = ("_signal", "_seen", "_future")

    def __init__(self, signal: "ApprovalDecisionSignal") -> None:
        self._signal = signal
        self._seen = signal._generation
        self._future: asyncio.Future[None] | None = None

    async def wait(self) -> None:
        if self._seen != self._signal._generation:
            self._seen = self._signal._generation
            return
        future = asyncio.get_running_loop().create_future()
        self._future = future
        # The generation check is deliberately after installing the future.
        # A notify that happened before the actual await remains observable.
        if self._seen != self._signal._generation:
            self._future = None
            self._seen = self._signal._generation
            return
        try:
            await future
        finally:
            if self._future is future:
                self._future = None
        self._seen = self._signal._generation


class ApprovalDecisionSignal:
    """Process-local, content-free, wake-only decision coordination."""

    def __init__(self) -> None:
        self._generation = 0
        self._waiters: set[_SignalWaiter] = set()

    def notify(self) -> None:
        self._generation += 1
        for waiter in tuple(self._waiters):
            future = waiter._future
            if future is not None and not future.done():
                future.set_result(None)

    def _register(self) -> _SignalWaiter:
        waiter = _SignalWaiter(self)
        self._waiters.add(waiter)
        return waiter

    def _unregister(self, waiter: _SignalWaiter) -> None:
        self._waiters.discard(waiter)


def _default_id_factory(label: str) -> str:
    return f"{label}-{uuid.uuid4().hex}"


def _default_now_ms() -> int:
    return time.time_ns() // 1_000_000


def _valid_wire_request_id(value: object) -> bool:
    if type(value) is int:
        return -(2**63) <= value <= MAX_SQLITE_INT
    return _is_bounded_string(value, 256)


def _valid_local_sequence(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_SQLITE_INT


def _valid_context(lines: object) -> bool:
    if type(lines) is not tuple or len(lines) > 32:
        return False
    if any(type(line) is not str or "\x00" in line or len(line) > 2048 for line in lines):
        return False
    return sum(len(line) for line in lines) <= 8192


def _is_async_callable(value: object) -> bool:
    return callable(value) and (
        inspect.iscoroutinefunction(value)
        or inspect.iscoroutinefunction(getattr(value, "__call__", None))
    )


async def _join_task(task: asyncio.Task[Any]) -> None:
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            continue
        except Exception:
            break
    try:
        task.result()
    except (asyncio.CancelledError, Exception):
        pass


async def _cancel_join(task: asyncio.Task[Any]) -> None:
    if not task.done():
        task.cancel()
    await _join_task(task)


class DurableApprovalOperator:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        binding: ApprovalTurnBinding,
        signal: ApprovalDecisionSignal,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
        sleep: Callable[[float], Any] | None = None,
    ) -> None:
        if type(storage) is not SqliteStorage:
            raise _invalid()
        if type(binding) is not ApprovalTurnBinding:
            raise _invalid()
        if type(signal) is not ApprovalDecisionSignal:
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        if sleep is not None and not _is_async_callable(sleep):
            raise _invalid()
        self._storage = storage
        self.binding = binding
        self._signal = signal
        self._now_ms = now_ms if now_ms is not None else _default_now_ms
        self._id_factory = id_factory if id_factory is not None else _default_id_factory
        self._sleep = sleep if sleep is not None else asyncio.sleep

    def _read_now(self) -> int:
        try:
            value = self._now_ms()
        except Exception:
            raise LiveApprovalError(LiveApprovalErrorCategory.STORAGE) from None
        if type(value) is not int or not 0 <= value <= MAX_SQLITE_INT:
            raise LiveApprovalError(LiveApprovalErrorCategory.INVALID_ARGUMENT)
        return value

    def _new_id(self, label: str) -> str:
        try:
            value = self._id_factory(label)
        except Exception:
            raise _invalid() from None
        if not _is_bounded_string(value, 128):
            raise _invalid()
        return value

    def _valid_request(self, request: object) -> bool:
        if type(request) is not ApprovalRequest:
            return False
        if not _valid_local_sequence(request.local_sequence):
            return False
        if type(request.profile_id) is not str or request.profile_id != self.binding.profile_id:
            return False
        if not _valid_wire_request_id(request.wire_request_id):
            return False
        if type(request.kind) is not ApprovalKind:
            return False
        if not _is_bounded_string(request.thread_id, 512) or request.thread_id != self.binding.thread_id:
            return False
        if not _is_bounded_string(request.item_or_call_id, 512):
            return False
        if not _valid_context(request.context_lines):
            return False
        modern = (
            ApprovalKind.COMMAND_EXECUTION,
            ApprovalKind.FILE_CHANGE,
            ApprovalKind.PERMISSIONS,
        )
        if request.kind in modern:
            return (
                type(request.turn_id) is str
                and request.turn_id == self.binding.codex_turn_id
            )
        if request.kind in (ApprovalKind.APPLY_PATCH, ApprovalKind.EXEC_COMMAND):
            return request.turn_id is None
        return False

    async def _bound_running_job(self) -> Any | None:
        try:
            job = await TurnJobRepository(self._storage).get(self.binding.job_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return None
        if job is None:
            return None
        if (
            job.job_id != self.binding.job_id
            or job.profile_id != self.binding.profile_id
            or job.thread_id != self.binding.thread_id
            or job.codex_turn_id != self.binding.codex_turn_id
            or job.state is not TurnJobState.CODEX_RUNNING
        ):
            return None
        return job

    async def _sleep_expiry(self) -> bool:
        try:
            await self._sleep(900.0)
        except asyncio.CancelledError:
            raise
        except Exception:
            # A broken test/clock seam is not durable expiry authority.
            return False
        return True

    async def _terminalize_expired(self, approval_id: str) -> ApprovalRecord | None:
        try:
            now = self._read_now()
            return await ApprovalRepository(
                self._storage, now_ms=lambda: now
            ).terminalize_pending(
                approval_id,
                target_state=ApprovalState.EXPIRED,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            return None

    async def _best_effort_cancel(self, approval_id: str) -> None:
        task = asyncio.create_task(
            ApprovalRepository(self._storage, now_ms=self._now_ms).terminalize_pending(
                approval_id,
                target_state=ApprovalState.CANCELLED,
            )
        )
        await _join_task(task)

    @staticmethod
    def _decision(record: ApprovalRecord) -> ApprovalDecision | None:
        if record.state is ApprovalState.APPROVED:
            return ApprovalDecision.ALLOW
        if record.state in (
            ApprovalState.DENIED,
            ApprovalState.EXPIRED,
            ApprovalState.CANCELLED,
        ):
            return ApprovalDecision.DENY
        return None

    async def _wait_for_decision(
        self,
        approval_id: str,
        waiter: _SignalWaiter,
        expiry_task: asyncio.Task[Any],
    ) -> ApprovalDecision:
        expiry_attempted = False
        while True:
            try:
                record = await ApprovalRepository(self._storage).get(approval_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                record = None
            if asyncio.current_task() is not None and asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            if type(record) is ApprovalRecord:
                decision = self._decision(record)
                if decision is not None:
                    return decision

            wake_task = asyncio.create_task(waiter.wait())
            try:
                wait_tasks: tuple[asyncio.Task[Any], ...]
                if expiry_attempted:
                    wait_tasks = (wake_task,)
                else:
                    wait_tasks = (wake_task, expiry_task)
                done, _ = await asyncio.wait(
                    wait_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if wake_task in done:
                    try:
                        wake_task.result()
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        pass
                if expiry_task in done and not expiry_attempted:
                    expiry_attempted = True
                    try:
                        expiry_elapsed = expiry_task.result()
                    except asyncio.CancelledError:
                        # The outer cancellation path owns cancellation cleanup.
                        raise
                    except Exception:
                        expiry_elapsed = False
                    if expiry_elapsed is True:
                        terminal = await self._terminalize_expired(approval_id)
                    else:
                        terminal = None
                    if terminal is not None:
                        decision = self._decision(terminal)
                        if decision is not None:
                            return decision
            finally:
                # asyncio.wait does not own child tasks.  The operator does:
                # no waiter helper may outlive this iteration or its owner.
                if not wake_task.done():
                    await _cancel_join(wake_task)
                else:
                    try:
                        wake_task.result()
                    except (asyncio.CancelledError, Exception):
                        pass

    async def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        if not self._valid_request(request):
            return ApprovalDecision.DENY
        job = await self._bound_running_job()
        if asyncio.current_task() is not None and asyncio.current_task().cancelling():
            raise asyncio.CancelledError
        if job is None:
            return ApprovalDecision.DENY

        content: bytes | None = None
        if request.context_lines:
            try:
                content = "\n".join(request.context_lines).encode("utf-8", "strict")
            except (UnicodeEncodeError, ValueError):
                return ApprovalDecision.DENY

        approval_id: str | None = None
        waiter: _SignalWaiter | None = None
        expiry_task: asyncio.Task[Any] | None = None
        published = False
        try:
            approval_id = self._new_id("approval")
            payload_id = self._new_id("approval_payload") if content is not None else None
            waiter = self._signal._register()
            now = self._read_now()
            if now > MAX_SQLITE_INT - P62_APPROVAL_TTL_MS:
                return ApprovalDecision.DENY
            expires_at_ms = now + P62_APPROVAL_TTL_MS
            expiry_task = asyncio.create_task(self._sleep_expiry())

            if payload_id is not None:
                await TransientPayloadRepository(
                    self._storage, now_ms=lambda: now
                ).create(
                    payload_id=payload_id,
                    dialogue_id=job.dialogue_id,
                    job_id=job.job_id,
                    kind=TransientPayloadKind.APPROVAL,
                    content=content,
                    expires_at_ms=now + P62_APPROVAL_PAYLOAD_RETENTION_MS,
                )
                if asyncio.current_task() is not None and asyncio.current_task().cancelling():
                    raise asyncio.CancelledError
            record = await ApprovalRepository(
                self._storage, now_ms=lambda: now
            ).create_pending(
                approval_id=approval_id,
                profile_id=self.binding.profile_id,
                wire_request_id=request.wire_request_id,
                kind=request.kind,
                job_id=job.job_id,
                expected_job_version=job.version,
                display_payload_id=payload_id,
                expires_at_ms=expires_at_ms,
            )
            if (
                type(record) is not ApprovalRecord
                or record.state is not ApprovalState.PENDING
                or record.approval_id != approval_id
                or record.profile_id != self.binding.profile_id
                or record.job_id != job.job_id
                or record.display_payload_id != payload_id
                or record.expires_at_ms != expires_at_ms
            ):
                raise LiveApprovalError(LiveApprovalErrorCategory.INVARIANT)
            published = True
            if asyncio.current_task() is not None and asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            return await self._wait_for_decision(approval_id, waiter, expiry_task)
        except asyncio.CancelledError:
            if published and approval_id is not None:
                await self._best_effort_cancel(approval_id)
            raise
        except LiveApprovalError:
            if published:
                # A malformed durable result after publication is not a safe
                # wire decision.  Keep the durable approval for later authority.
                raise
            return ApprovalDecision.DENY
        except Exception:
            if published:
                # Storage failure after PENDING is fail-closed waiting state;
                # this branch is only reached outside the normal wait loop.
                try:
                    return await self._wait_for_decision(approval_id, waiter, expiry_task)
                except asyncio.CancelledError:
                    await self._best_effort_cancel(approval_id)
                    raise
                except Exception:
                    return await self._wait_for_decision(approval_id, waiter, expiry_task)
            return ApprovalDecision.DENY
        finally:
            if waiter is not None:
                self._signal._unregister(waiter)
            if expiry_task is not None:
                await _cancel_join(expiry_task)


_METHOD_KINDS = {
    "item/commandExecution/requestApproval": ApprovalKind.COMMAND_EXECUTION,
    "item/fileChange/requestApproval": ApprovalKind.FILE_CHANGE,
    "item/permissions/requestApproval": ApprovalKind.PERMISSIONS,
    "applyPatchApproval": ApprovalKind.APPLY_PATCH,
    "execCommandApproval": ApprovalKind.EXEC_COMMAND,
}


class OwnedApprovalResponseService:
    def __init__(
        self,
        profile_id: str,
        client: CodexProtocolClient,
        operator: DurableApprovalOperator,
    ) -> None:
        if not _is_bounded_string(profile_id, 128):
            raise _invalid()
        if type(client) is not CodexProtocolClient:
            raise _invalid()
        if type(operator) is not DurableApprovalOperator:
            raise _invalid()
        if operator.binding.profile_id != profile_id:
            raise _invalid()
        self._profile_id = profile_id
        self._client = client
        self._operator = operator
        self._bridge = CodexApprovalBridge(
            profile_id=profile_id,
            client=client,
            operator=operator,
        )

    async def _owned_bridge(self, inbound: InboundServerRequest) -> Any:
        task = asyncio.create_task(self._bridge.handle_request(inbound))
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                # The already-owned bridge remains the owner.  Continue until
                # the one accepted P1.7 response attempt reaches a result.
                continue

    @staticmethod
    def _valid_result(
        result: object,
        inbound: InboundServerRequest,
        profile_id: str,
    ) -> bool:
        if type(result) is not ApprovalHandlingResult:
            return False
        expected_kind = _METHOD_KINDS.get(inbound.method)
        if expected_kind is None:
            return False
        if (
            type(result.status) is not ApprovalHandlingStatus
            or result.profile_id != profile_id
            or result.wire_request_id != inbound.request_id
            or type(result.local_sequence) is not int
            or result.local_sequence <= 0
            or type(result.kind) is not ApprovalKind
            or result.kind is not expected_kind
        ):
            return False
        if result.status in (ApprovalHandlingStatus.ALLOWED, ApprovalHandlingStatus.DENIED):
            return True
        if result.status is ApprovalHandlingStatus.RESPONSE_UNKNOWN:
            return result.error_category in (
                ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL,
                ApprovalErrorCategory.APPROVAL_RESPONSE_UNKNOWN,
            )
        return False

    async def handle_owned(self, inbound: InboundServerRequest) -> ApprovalHandlingResult:
        if type(inbound) is not InboundServerRequest:
            raise _invalid()
        if self._client.owns_server_request(inbound) is not True:
            raise _invalid()
        try:
            result = await self._owned_bridge(inbound)
        except ApprovalError:
            raise LiveApprovalError(LiveApprovalErrorCategory.INVARIANT) from None
        except asyncio.CancelledError:
            raise LiveApprovalError(LiveApprovalErrorCategory.INVARIANT) from None
        except Exception:
            raise LiveApprovalError(LiveApprovalErrorCategory.INVARIANT) from None
        if not self._valid_result(result, inbound, self._profile_id):
            raise LiveApprovalError(LiveApprovalErrorCategory.INVARIANT)
        return result
