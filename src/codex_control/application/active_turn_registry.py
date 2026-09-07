"""In-memory ownership of the exact P1 active-turn binding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from codex_control.adapters.codex.turn_lifecycle import TurnBinding


@dataclass(frozen=True)
class _RegistryLease:
    """Opaque ownership returned to the invocation that published a binding."""

    job_id: str
    binding: TurnBinding
    token: object


@dataclass(frozen=True)
class _RegistryEntry:
    binding: TurnBinding
    token: object
    retired: asyncio.Event


class _RetirementWatch:
    """A one-generation watch captured while its exact entry is active."""

    __slots__ = (
        "_registry",
        "_job_id",
        "_token",
        "_event",
        "_disposed",
        "_superseded",
        "_retired",
        "_finished",
    )

    def __init__(self, registry, job_id: str, token: object, event: asyncio.Event) -> None:
        self._registry = registry
        self._job_id = job_id
        self._token = token
        self._event = event
        self._disposed = False
        self._superseded = False
        self._retired = False
        self._finished = False

    def dispose(self) -> None:
        """Release the caller's watch without touching ownership."""

        if self._finished:
            return
        self._disposed = True
        self._finished = True
        self._registry._unregister_watch(self)

    def _mark_superseded(self) -> None:
        if not self._finished:
            self._superseded = True

    def _mark_retired(self, token: object) -> None:
        if not self._finished and self._token is token:
            self._retired = True

    async def wait(self) -> None:
        if self._finished or self._disposed:
            raise RuntimeError("retirement watch disposed")
        try:
            await self._event.wait()
            if self._disposed:
                raise RuntimeError("retirement watch disposed")
            if self._superseded:
                raise RuntimeError("replacement binding was published")
            if not self._retired:
                raise RuntimeError("exact binding retirement was not observed")
        finally:
            self._finished = True
            self._registry._unregister_watch(self)

    def __await__(self):
        return self.wait().__await__()


class ActiveTurnRegistry:
    """A deliberately small, process-local exact-binding registry.

    The registry never serializes or recreates a binding.  A lease token makes
    cleanup conditional on the publication that owns the entry, so an old
    runner cannot retire a replacement publication.
    """

    def __init__(self) -> None:
        self._entries: dict[str, _RegistryEntry] = {}
        self._watches: dict[str, set[_RetirementWatch]] = {}

    def __repr__(self) -> str:
        return (
            f"<ActiveTurnRegistry entries={len(self._entries)} "
            f"watches={sum(len(watches) for watches in self._watches.values())}>"
        )

    def publish(self, job_id: str, binding: TurnBinding) -> _RegistryLease:
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise ValueError("invalid registry key")
        if type(binding) is not TurnBinding:
            raise ValueError("invalid registry binding")
        current = self._entries.get(job_id)
        if current is not None:
            if current.binding is binding:
                return _RegistryLease(job_id, binding, current.token)
            raise RuntimeError("active binding already published")
        for watch in tuple(self._watches.get(job_id, ())):
            watch._mark_superseded()
        token = object()
        self._entries[job_id] = _RegistryEntry(binding, token, asyncio.Event())
        return _RegistryLease(job_id, binding, token)

    def lookup(self, job_id: str) -> TurnBinding | None:
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise ValueError("invalid registry key")
        entry = self._entries.get(job_id)
        return None if entry is None else entry.binding

    def retire(self, job_id: str, ownership: object) -> None:
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise ValueError("invalid registry key")
        entry = self._entries.get(job_id)
        if entry is None:
            return
        if isinstance(ownership, _RegistryLease):
            owned = (
                ownership.job_id == job_id
                and entry.token is ownership.token
                and entry.binding is ownership.binding
            )
        else:
            # Binding identity is accepted for simple callers, but never
            # equality.  Runner cleanup uses the stronger private lease.
            owned = entry.binding is ownership
        if owned:
            self._entries.pop(job_id, None)
            for watch in tuple(self._watches.get(job_id, ())):
                watch._mark_retired(entry.token)
            entry.retired.set()

    def _unregister_watch(self, watch: _RetirementWatch) -> None:
        watches = self._watches.get(watch._job_id)
        if watches is None:
            return
        watches.discard(watch)
        if not watches:
            self._watches.pop(watch._job_id, None)

    def wait_retired(self, job_id: str, binding: TurnBinding) -> _RetirementWatch:
        """Arm an exact-generation retirement watch synchronously.

        The active entry and its retirement event are captured before this
        method returns.  Callers may then await the returned watch without a
        post-retirement identity archive.
        """
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise ValueError("invalid registry key")
        if type(binding) is not TurnBinding:
            raise ValueError("invalid registry binding")
        entry = self._entries.get(job_id)
        if entry is None:
            raise RuntimeError("active binding ownership unavailable")
        if entry.binding is not binding:
            raise RuntimeError("different active binding owns job")
        watch = _RetirementWatch(self, job_id, entry.token, entry.retired)
        self._watches.setdefault(job_id, set()).add(watch)
        return watch
