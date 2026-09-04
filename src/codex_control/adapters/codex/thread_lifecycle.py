"""P1.5 ambiguity-safe ``thread/start`` and ``thread/resume`` adapter."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from .errors import CodexAdapterError, normalize_error
from .model_catalog import CodexModelCatalogAdapter


MAX_THREAD_ID_CHARS = 512
MAX_WORKING_DIRECTORY_CHARS = 4096
THREAD_START_METHOD = "thread/start"
THREAD_RESUME_METHOD = "thread/resume"
THREAD_START_APPROVAL_POLICY = "on-request"
THREAD_START_SANDBOX = "workspace-write"


class ThreadLifecycleError(Exception):
    """Finite local validation failures; no remote data is retained."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


@dataclass(frozen=True)
class TrustedWorkingDirectory:
    """A deployment/config supplied path, validated before any RPC dispatch."""

    path: str

    def __post_init__(self) -> None:
        if (not isinstance(self.path, str) or not self.path or "\0" in self.path
                or len(self.path) > MAX_WORKING_DIRECTORY_CHARS or not os.path.isabs(self.path)):
            raise ThreadLifecycleError("working_directory_invalid")


@dataclass(frozen=True)
class ThreadBinding:
    """The complete durable Codex thread identity: owner profile plus exact ID."""

    profile_id: str
    thread_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id:
            raise ThreadLifecycleError("profile_id_invalid")
        _validate_thread_id(self.thread_id)


class ThreadOperationStatus(StrEnum):
    START_CONFIRMED = "START_CONFIRMED"
    START_REJECTED = "START_REJECTED"
    START_UNKNOWN = "START_UNKNOWN"
    RESUME_CONFIRMED = "RESUME_CONFIRMED"
    RESUME_REJECTED = "RESUME_REJECTED"
    RESUME_UNKNOWN = "RESUME_UNKNOWN"


@dataclass(frozen=True)
class ThreadOperationResult:
    status: ThreadOperationStatus
    binding: ThreadBinding | None = None
    error: CodexAdapterError | None = None
    # Operation metadata only.  It is deliberately not part of ThreadBinding.
    model_id: str | None = None
    reasoning_effort: str | None = None


class RuntimeManagerLike(Protocol):
    async def acquire(self, profile_id: str) -> Any: ...


def _validate_thread_id(value: Any) -> str:
    if not isinstance(value, str) or not value or "\0" in value or len(value) > MAX_THREAD_ID_CHARS:
        raise ThreadLifecycleError("thread_id_invalid")
    return value


class CodexThreadLifecycleAdapter:
    """Owns one side-effecting thread operation at a time per profile.

    A dispatched RPC is run in an adapter-owned task.  Awaiting callers are
    shielded, so their cancellation cannot cancel the wire request.  Terminal
    task results are retained until observed by ``await_inflight``.
    """

    def __init__(self, manager: RuntimeManagerLike, catalog: CodexModelCatalogAdapter) -> None:
        self._manager = manager
        self._catalog = catalog
        self._locks: dict[str, asyncio.Lock] = {}
        self._inflight: dict[str, asyncio.Task[ThreadOperationResult]] = {}

    async def start(self, profile_id: str, *, model_id: str,
                    reasoning_effort: str | None,
                    working_directory: TrustedWorkingDirectory) -> ThreadOperationResult:
        if not isinstance(model_id, str) or not model_id or "\0" in model_id:
            raise ThreadLifecycleError("model_id_invalid")
        if not isinstance(working_directory, TrustedWorkingDirectory):
            raise ThreadLifecycleError("working_directory_untrusted")
        return await self._begin(profile_id, self._start_operation(
            profile_id, model_id, reasoning_effort, working_directory))

    async def resume(self, binding: ThreadBinding) -> ThreadOperationResult:
        if not isinstance(binding, ThreadBinding):
            raise ThreadLifecycleError("thread_binding_invalid")
        return await self._begin(binding.profile_id, self._resume_operation(binding))

    async def await_inflight(self, profile_id: str) -> ThreadOperationResult | None:
        """Observe the exact task that survived a caller cancellation, if any."""
        task = self._inflight.get(profile_id)
        if task is None:
            return None
        return await asyncio.shield(task)

    async def _begin(self, profile_id: str, operation: Any) -> ThreadOperationResult:
        if not isinstance(profile_id, str) or not profile_id:
            raise ThreadLifecycleError("profile_id_invalid")
        lock = self._locks.setdefault(profile_id, asyncio.Lock())
        async with lock:
            existing = self._inflight.get(profile_id)
            if existing is not None and not existing.done():
                # Avoid leaving an un-awaited coroutine when the busy guard wins.
                operation.close()
                raise ThreadLifecycleError("profile_lifecycle_busy")
            task = asyncio.create_task(operation)
            self._inflight[profile_id] = task
            task.add_done_callback(lambda completed, p=profile_id: self._completed(p, completed))
        return await asyncio.shield(task)

    def _completed(self, profile_id: str, task: asyncio.Task[ThreadOperationResult]) -> None:
        # Retrieve unexpected task exceptions without ever rendering wire data.
        if not task.cancelled():
            try:
                task.exception()
            except (asyncio.CancelledError, Exception):
                pass

    async def _start_operation(self, profile_id: str, model_id: str,
                               requested_effort: str | None,
                               cwd: TrustedWorkingDirectory) -> ThreadOperationResult:
        # Acquire first, fetch the P1.4 catalog, then prove the dispatch runtime
        # has the same owner and generation as the catalog snapshot.
        await self._manager.acquire(profile_id)
        catalog = await self._catalog.get_catalog(profile_id)
        runtime = await self._manager.acquire(profile_id)
        if runtime.profile_id != profile_id or catalog.profile_id != profile_id or runtime.generation != catalog.runtime_generation:
            raise ThreadLifecycleError("runtime_catalog_generation_mismatch")
        descriptor = catalog.resolve_model(model_id)
        effort = catalog.validate_reasoning_effort(model_id, requested_effort)
        params = {
            "cwd": cwd.path,
            "approvalPolicy": THREAD_START_APPROVAL_POLICY,
            "sandbox": THREAD_START_SANDBOX,
            "model": descriptor.wire_model,
            "ephemeral": False,
        }
        try:
            response = await runtime.client.request(THREAD_START_METHOD, params)
        except Exception as error:
            normalized = normalize_error(error)
            if normalized.category.value == "remote_app_server_error":
                return ThreadOperationResult(ThreadOperationStatus.START_REJECTED, error=normalized,
                                             model_id=model_id, reasoning_effort=effort)
            return ThreadOperationResult(ThreadOperationStatus.START_UNKNOWN, error=normalized,
                                         model_id=model_id, reasoning_effort=effort)
        try:
            binding = ThreadBinding(profile_id, response["thread"]["id"] if isinstance(response, dict) and isinstance(response.get("thread"), dict) else None)
        except ThreadLifecycleError:
            return ThreadOperationResult(ThreadOperationStatus.START_UNKNOWN,
                                         model_id=model_id, reasoning_effort=effort)
        return ThreadOperationResult(ThreadOperationStatus.START_CONFIRMED, binding,
                                     model_id=model_id, reasoning_effort=effort)

    async def _resume_operation(self, binding: ThreadBinding) -> ThreadOperationResult:
        runtime = await self._manager.acquire(binding.profile_id)
        if runtime.profile_id != binding.profile_id:
            raise ThreadLifecycleError("runtime_profile_mismatch")
        try:
            response = await runtime.client.request(THREAD_RESUME_METHOD, {"threadId": binding.thread_id})
        except Exception as error:
            normalized = normalize_error(error)
            if normalized.category.value == "remote_app_server_error":
                return ThreadOperationResult(ThreadOperationStatus.RESUME_REJECTED, error=normalized)
            return ThreadOperationResult(ThreadOperationStatus.RESUME_UNKNOWN, error=normalized)
        try:
            returned_id = _validate_thread_id(response["thread"]["id"] if isinstance(response, dict) and isinstance(response.get("thread"), dict) else None)
        except ThreadLifecycleError:
            return ThreadOperationResult(ThreadOperationStatus.RESUME_UNKNOWN)
        if returned_id != binding.thread_id:
            return ThreadOperationResult(ThreadOperationStatus.RESUME_UNKNOWN)
        return ThreadOperationResult(ThreadOperationStatus.RESUME_CONFIRMED, binding)
