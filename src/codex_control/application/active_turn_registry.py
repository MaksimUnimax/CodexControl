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


class ActiveTurnRegistry:
    """A deliberately small, process-local exact-binding registry.

    The registry never serializes or recreates a binding.  A lease token makes
    cleanup conditional on the publication that owns the entry, so an old
    runner cannot retire a replacement publication.
    """

    def __init__(self) -> None:
        self._entries: dict[str, _RegistryEntry] = {}
        # Keep exact object identities long enough to distinguish an already
        # retired owner from an equal-looking binding that never owned this
        # job.  This is intentionally process-local and content-free.
        self._retired: dict[str, list[TurnBinding]] = {}

    def __repr__(self) -> str:
        return f"<ActiveTurnRegistry entries={len(self._entries)}>"

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
            self._retired.setdefault(job_id, []).append(entry.binding)
            entry.retired.set()

    async def wait_retired(self, job_id: str, binding: TurnBinding) -> None:
        """Wait for retirement of this exact ownership generation.

        A missing entry is success only when this exact object was previously
        retired.  Any other owner, including an equal-looking clone or a
        replacement generation, fails closed.
        """
        if not isinstance(job_id, str) or not job_id or "\x00" in job_id:
            raise ValueError("invalid registry key")
        if type(binding) is not TurnBinding:
            raise ValueError("invalid registry binding")
        entry = self._entries.get(job_id)
        if entry is None:
            if any(candidate is binding for candidate in self._retired.get(job_id, ())):
                return
            raise RuntimeError("active binding ownership unavailable")
        if entry.binding is not binding:
            raise RuntimeError("different active binding owns job")
        await entry.retired.wait()
        current = self._entries.get(job_id)
        if current is not None or not any(
            candidate is binding for candidate in self._retired.get(job_id, ())
        ):
            raise RuntimeError("replacement active binding owns job")
