"""Ambiguity-safe, profile-bound thread lifecycle operations."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Awaitable, Callable, Protocol

from .errors import CodexAdapterError, CodexAdapterErrorCategory
from .model_catalog import CodexModelCatalogAdapter
from .protocol import ProtocolRemoteError

MAX_THREAD_ID_CHARS = 512
MAX_WORKING_DIRECTORY_CHARS = 4096
THREAD_START_METHOD = "thread/start"
THREAD_RESUME_METHOD = "thread/resume"
THREAD_DELETE_METHOD = "thread/delete"
THREAD_APPROVAL_POLICY = "on-request"
THREAD_SANDBOX = "workspace-write"


class ThreadLifecycleError(Exception):
    """A finite local failure. Untrusted text never enters its rendering."""
    _ALLOWED = frozenset((
        CodexAdapterErrorCategory.THREAD_REQUEST_INVALID,
        CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED,
        CodexAdapterErrorCategory.THREAD_OPERATION_BUSY,
        CodexAdapterErrorCategory.THREAD_START_REJECTED,
        CodexAdapterErrorCategory.THREAD_START_UNKNOWN,
        CodexAdapterErrorCategory.THREAD_RESUME_REJECTED,
        CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN,
        CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN,
    ))

    def __init__(self, category: CodexAdapterErrorCategory | str) -> None:
        try:
            parsed = CodexAdapterErrorCategory(category)
        except (TypeError, ValueError):
            parsed = CodexAdapterErrorCategory.THREAD_REQUEST_INVALID
        self.category = parsed if parsed in self._ALLOWED else CodexAdapterErrorCategory.THREAD_REQUEST_INVALID
        super().__init__(self.category.value)


@dataclass(frozen=True)
class TrustedWorkingDirectory:
    path: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path or "\0" in self.path or len(self.path) > MAX_WORKING_DIRECTORY_CHARS or not os.path.isabs(self.path):
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)


def _validate_thread_id(value: Any) -> str:
    if not isinstance(value, str) or not value or "\0" in value or len(value) > MAX_THREAD_ID_CHARS:
        raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
    return value


@dataclass(frozen=True)
class ThreadBinding:
    """P1.5 durable identity only: owning profile and opaque Codex thread ID."""
    profile_id: str
    thread_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        _validate_thread_id(self.thread_id)


class ThreadOperationStatus(StrEnum):
    START_CONFIRMED = "START_CONFIRMED"; START_REJECTED = "START_REJECTED"; START_UNKNOWN = "START_UNKNOWN"
    RESUME_CONFIRMED = "RESUME_CONFIRMED"; RESUME_REJECTED = "RESUME_REJECTED"; RESUME_UNKNOWN = "RESUME_UNKNOWN"
    DELETE_CONFIRMED = "DELETE_CONFIRMED"; DELETE_UNKNOWN = "DELETE_UNKNOWN"


@dataclass(frozen=True)
class ThreadOperationResult:
    status: ThreadOperationStatus
    binding: ThreadBinding | None = None
    error: CodexAdapterError | None = None
    model_id: str | None = None
    reasoning_effort: str | None = None


class RuntimeManagerLike(Protocol):
    async def acquire(self, profile_id: str) -> Any: ...


class CodexThreadLifecycleAdapter:
    """One side effect per profile, with exact ownership after dispatch."""

    def __init__(self, manager: RuntimeManagerLike, catalog: CodexModelCatalogAdapter) -> None:
        self._manager, self._catalog = manager, catalog
        self._locks: dict[str, asyncio.Lock] = {}
        self._inflight: dict[str, object] = {}

    async def start(self, profile_id: str, *, model_id: str, reasoning_effort: str | None,
                    working_directory: TrustedWorkingDirectory) -> ThreadOperationResult:
        if not isinstance(profile_id, str) or not profile_id or not isinstance(model_id, str) or not model_id or "\0" in model_id or not isinstance(working_directory, TrustedWorkingDirectory):
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        return await self._begin(profile_id, lambda: self._start(profile_id, model_id, reasoning_effort, working_directory))

    async def resume(self, *, binding: ThreadBinding,
                     working_directory: TrustedWorkingDirectory) -> ThreadOperationResult:
        if not isinstance(binding, ThreadBinding) or not isinstance(working_directory, TrustedWorkingDirectory):
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        return await self._begin(binding.profile_id, lambda: self._resume(binding, working_directory))

    async def delete(self, *, binding: ThreadBinding) -> ThreadOperationResult:
        if not isinstance(binding, ThreadBinding):
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        return await self._begin(binding.profile_id, lambda: self._delete(binding))

    async def _before_delete_dispatch(self) -> None:
        """Test seam only; production performs no pre-dispatch work."""

    async def _delete(self, binding: ThreadBinding) -> ThreadOperationResult:
        try:
            runtime = await self._manager.acquire(binding.profile_id)
            if runtime.profile_id != binding.profile_id:
                raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED)
        except asyncio.CancelledError:
            raise
        except ThreadLifecycleError:
            raise
        except Exception as error:
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED) from error

        await self._before_delete_dispatch()
        return await self._delete_request(runtime, binding)

    async def _delete_request(self, runtime: Any, binding: ThreadBinding) -> ThreadOperationResult:
        """Own exactly one destructive request after it is dispatched."""
        dispatched = asyncio.Event()

        async def invoke() -> Any:
            dispatched.set()
            return await runtime.client.request(THREAD_DELETE_METHOD, {"threadId": binding.thread_id})

        request = asyncio.create_task(invoke())
        while True:
            try:
                response = await asyncio.shield(request)
                if isinstance(response, dict):
                    return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)
                return ThreadOperationResult(
                    ThreadOperationStatus.DELETE_UNKNOWN,
                    binding,
                    CodexAdapterError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN),
                )
            except asyncio.CancelledError:
                if request.cancelled():
                    return ThreadOperationResult(
                        ThreadOperationStatus.DELETE_UNKNOWN,
                        binding,
                        CodexAdapterError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN),
                    )
                if not dispatched.is_set():
                    request.cancel()
                    await asyncio.gather(request, return_exceptions=True)
                    raise
                # Caller cancellation cannot detach the owned destructive RPC.
                continue
            except ProtocolRemoteError as error:
                return ThreadOperationResult(
                    ThreadOperationStatus.DELETE_UNKNOWN,
                    binding,
                    CodexAdapterError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN, remote_code=error.code),
                )
            except Exception:
                return ThreadOperationResult(
                    ThreadOperationStatus.DELETE_UNKNOWN,
                    binding,
                    CodexAdapterError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN),
                )

    async def _begin(self, profile_id: str, operation: Callable[[], Awaitable[ThreadOperationResult]]) -> ThreadOperationResult:
        token = object()
        lock = self._locks.setdefault(profile_id, asyncio.Lock())
        async with lock:
            if profile_id in self._inflight:
                raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_OPERATION_BUSY)
            self._inflight[profile_id] = token
        try:
            return await operation()
        finally:
            await self._release_reservation(profile_id, token)

    async def _release_reservation(self, profile_id: str, token: object) -> None:
        """Release only the reservation owned by this completed operation."""
        lock = self._locks.setdefault(profile_id, asyncio.Lock())
        async with lock:
            if self._inflight.get(profile_id) is token:
                self._inflight.pop(profile_id, None)

    async def _request(self, runtime: Any, method: str, params: dict[str, Any], *,
                       rejected: ThreadOperationStatus, unknown: ThreadOperationStatus,
                       rejected_category: CodexAdapterErrorCategory,
                       unknown_category: CodexAdapterErrorCategory) -> tuple[bool, ThreadOperationStatus, Any | None, CodexAdapterError | None]:
        dispatched = asyncio.Event()

        async def invoke() -> Any:
            dispatched.set()
            return await runtime.client.request(method, params)

        task = asyncio.create_task(invoke())
        while True:
            try:
                return True, ThreadOperationStatus.START_CONFIRMED, await asyncio.shield(task), None
            except asyncio.CancelledError:
                if task.cancelled():
                    return False, unknown, None, CodexAdapterError(unknown_category)
                if not dispatched.is_set():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
                    raise
                # Defer every post-dispatch cancellation until this exact RPC ends.
                continue
            except ProtocolRemoteError as error:
                return False, rejected, None, CodexAdapterError(rejected_category, remote_code=error.code)
            except Exception:
                return False, unknown, None, CodexAdapterError(unknown_category)

    async def _start(self, profile_id: str, model_id: str, requested_effort: str | None,
                     cwd: TrustedWorkingDirectory) -> ThreadOperationResult:
        try:
            # The runtime is deliberately captured before catalog lookup.  A
            # catalog describes one runtime generation; reacquiring here could
            # silently rebase a caller's selection onto a later child.
            runtime = await self._manager.acquire(profile_id)
            catalog = await self._catalog.get_catalog(profile_id)
            if runtime.profile_id != profile_id or catalog.profile_id != profile_id or runtime.generation != catalog.runtime_generation:
                raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED)
            descriptor = catalog.resolve_model(model_id)
            effort = catalog.validate_reasoning_effort(model_id, requested_effort)
        except asyncio.CancelledError:
            raise
        except ThreadLifecycleError:
            raise
        except Exception as error:
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED) from error
        success, status, response, error = await self._request(
            runtime, THREAD_START_METHOD,
            {"cwd": cwd.path, "approvalPolicy": THREAD_APPROVAL_POLICY, "sandbox": THREAD_SANDBOX, "model": descriptor.wire_model, "ephemeral": False},
            rejected=ThreadOperationStatus.START_REJECTED, unknown=ThreadOperationStatus.START_UNKNOWN,
            rejected_category=CodexAdapterErrorCategory.THREAD_START_REJECTED,
            unknown_category=CodexAdapterErrorCategory.THREAD_START_UNKNOWN)
        if not success:
            return ThreadOperationResult(status, error=error, model_id=model_id, reasoning_effort=effort)
        try:
            thread_id = _validate_thread_id(response["thread"]["id"] if isinstance(response, dict) and isinstance(response.get("thread"), dict) else None)
        except ThreadLifecycleError:
            return ThreadOperationResult(ThreadOperationStatus.START_UNKNOWN, error=CodexAdapterError(CodexAdapterErrorCategory.THREAD_START_UNKNOWN), model_id=model_id, reasoning_effort=effort)
        return ThreadOperationResult(ThreadOperationStatus.START_CONFIRMED, ThreadBinding(profile_id, thread_id), model_id=model_id, reasoning_effort=effort)

    async def _resume(self, binding: ThreadBinding, cwd: TrustedWorkingDirectory) -> ThreadOperationResult:
        try:
            runtime = await self._manager.acquire(binding.profile_id)
            if runtime.profile_id != binding.profile_id:
                raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED)
        except asyncio.CancelledError:
            raise
        except ThreadLifecycleError:
            raise
        except Exception as error:
            raise ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED) from error
        success, status, response, error = await self._request(
            runtime, THREAD_RESUME_METHOD,
            {"threadId": binding.thread_id, "cwd": cwd.path, "approvalPolicy": THREAD_APPROVAL_POLICY, "sandbox": THREAD_SANDBOX},
            rejected=ThreadOperationStatus.RESUME_REJECTED, unknown=ThreadOperationStatus.RESUME_UNKNOWN,
            rejected_category=CodexAdapterErrorCategory.THREAD_RESUME_REJECTED,
            unknown_category=CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN)
        if not success:
            return ThreadOperationResult(status, error=error)
        try:
            returned = _validate_thread_id(response["thread"]["id"] if isinstance(response, dict) and isinstance(response.get("thread"), dict) else None)
        except ThreadLifecycleError:
            return ThreadOperationResult(ThreadOperationStatus.RESUME_UNKNOWN, error=CodexAdapterError(CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN))
        if returned != binding.thread_id:
            return ThreadOperationResult(ThreadOperationStatus.RESUME_UNKNOWN, error=CodexAdapterError(CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN))
        return ThreadOperationResult(ThreadOperationStatus.RESUME_CONFIRMED, binding)
