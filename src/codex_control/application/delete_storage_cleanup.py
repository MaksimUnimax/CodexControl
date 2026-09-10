"""Local-only P7.C4 cleanup and UNKNOWN containment orchestration."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from codex_control.adapters.codex.persistent_scanner import (
    PersistentProfileResidualScanner,
    PersistentProfileScanResult,
)
from codex_control.storage import (
    ApplicationRecoveryRepository,
    DeleteStorageContainmentRecord,
    DeleteStorageContainmentRepository,
    DeletionFinalizeResult,
    DeletionRepository,
    DeletionTombstoneRecord,
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    SqliteStorage,
)

P7C4_DELETE_TOMBSTONE_RETENTION_MS = 604800000


class DeleteStorageCleanupStatus(StrEnum):
    CONFIRMED_FINALIZED = "CONFIRMED_FINALIZED"
    CONFIRMED_PENDING_STORAGE = "CONFIRMED_PENDING_STORAGE"
    UNKNOWN_CONTAINED = "UNKNOWN_CONTAINED"
    UNKNOWN_PENDING = "UNKNOWN_PENDING"


class DeleteStorageCleanupReason(StrEnum):
    RESERVATION_FAILED = "RESERVATION_FAILED"
    SHUTDOWN_FAILED = "SHUTDOWN_FAILED"
    QUIESCENCE_FAILED = "QUIESCENCE_FAILED"
    RECREATE_FAILED = "RECREATE_FAILED"
    PERSISTENT_RESIDUAL_MATCHES = "PERSISTENT_RESIDUAL_MATCHES"
    PERSISTENT_SCAN_ERROR = "PERSISTENT_SCAN_ERROR"
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    FINALIZE_FAILED = "FINALIZE_FAILED"
    CONTAINMENT_FAILED = "CONTAINMENT_FAILED"
    RESERVATION_RELEASE_FAILED = "RESERVATION_RELEASE_FAILED"


@dataclass(frozen=True, repr=False)
class DeleteStorageCleanupResult:
    status: DeleteStorageCleanupStatus
    dialogue: DialogueRecord | None = None
    tombstone: object | None = None
    reason: DeleteStorageCleanupReason | None = None
    scan: PersistentProfileScanResult | None = None

    def __repr__(self) -> str:
        return (
            "DeleteStorageCleanupResult("
            f"status={getattr(self.status, 'value', 'INVALID')!r}, "
            f"dialogue_present={self.dialogue is not None!r}, "
            f"tombstone_present={self.tombstone is not None!r}, "
            f"reason={getattr(self.reason, 'value', None)!r}, "
            f"scan_present={self.scan is not None!r})"
        )


class DeleteStorageCleanupError(Exception):
    """Finite local cleanup diagnostic; no filesystem or thread data."""

    def __init__(self, reason: DeleteStorageCleanupReason | str) -> None:
        try:
            self.reason = reason if isinstance(reason, DeleteStorageCleanupReason) else DeleteStorageCleanupReason(reason)
        except (TypeError, ValueError):
            self.reason = DeleteStorageCleanupReason.FINALIZE_FAILED
        super().__init__(self.reason.value)

    def __repr__(self) -> str:
        return f"DeleteStorageCleanupError({self.reason.value!r})"


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


class DeleteStorageCleanupCoordinator:
    """Own one local task and quarantine reservation per live profile."""

    def __init__(
        self,
        storage: SqliteStorage,
        runtime_manager: object,
        *,
        scanner: PersistentProfileResidualScanner | None = None,
        now_ms: Callable[[], int] | None = None,
        tombstone_retention_ms: int = P7C4_DELETE_TOMBSTONE_RETENTION_MS,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise ValueError("storage_invalid")
        if not _async_callable(runtime_manager, "reserve") or not _async_callable(runtime_manager, "shutdown_profile") or not _async_callable(runtime_manager, "recreate_isolated_state_root"):
            raise ValueError("runtime_manager_invalid")
        if now_ms is not None and not callable(now_ms):
            raise ValueError("clock_invalid")
        if type(tombstone_retention_ms) is not int or tombstone_retention_ms <= 0:
            raise ValueError("retention_invalid")
        authority = getattr(runtime_manager, "isolation_authority", None)
        if scanner is None:
            if authority is None:
                raise ValueError("isolation_authority_required")
            scanner = PersistentProfileResidualScanner(authority)
        if not callable(getattr(scanner, "scan", None)):
            raise ValueError("scanner_invalid")
        self._storage = storage
        self._runtime_manager = runtime_manager
        self._scanner = scanner
        self._clock = now_ms if now_ms is not None else _default_clock
        self._retention_ms = tombstone_retention_ms
        self._tasks: dict[str, asyncio.Task[DeleteStorageCleanupResult]] = {}
        self._reservations: dict[str, object] = {}

    def __repr__(self) -> str:
        return "<DeleteStorageCleanupCoordinator>"

    async def cleanup_confirmed(
        self, *, dialogue_id: str, expected_dialogue_version: int
    ) -> DeleteStorageCleanupResult:
        key = dialogue_id
        task = self._tasks.get(key)
        if task is None or task.done():
            task = asyncio.create_task(self._cleanup_confirmed(dialogue_id, expected_dialogue_version))
            self._tasks[key] = task
        try:
            return await self._await_owned(task)
        finally:
            if task.done() and self._tasks.get(key) is task:
                self._tasks.pop(key, None)

    async def contain_unknown(
        self, *, dialogue_id: str, expected_dialogue_version: int
    ) -> DeleteStorageCleanupResult:
        key = dialogue_id
        task = self._tasks.get(key)
        if task is None or task.done():
            task = asyncio.create_task(self._contain_unknown(dialogue_id, expected_dialogue_version))
            self._tasks[key] = task
        try:
            return await self._await_owned(task)
        finally:
            if task.done() and self._tasks.get(key) is task:
                self._tasks.pop(key, None)

    async def cleanup(self, *, dialogue_id: str, expected_dialogue_version: int) -> DeleteStorageCleanupResult:
        snapshot = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
        if snapshot.dialogue is not None and snapshot.dialogue.dialogue_id == dialogue_id:
            if snapshot.dialogue.state is DialogueState.DELETE_UNKNOWN:
                return await self.contain_unknown(
                    dialogue_id=dialogue_id, expected_dialogue_version=expected_dialogue_version
                )
            if snapshot.dialogue.state is DialogueState.DELETE_CONFIRMED_PENDING_STORAGE:
                return await self.cleanup_confirmed(
                    dialogue_id=dialogue_id, expected_dialogue_version=expected_dialogue_version
                )
        raise DeleteStorageCleanupError(DeleteStorageCleanupReason.FINALIZE_FAILED)

    async def _load_dialogue(self, dialogue_id: str, expected_version: int, state: DialogueState) -> DialogueRecord | None:
        snapshot = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
        dialogue = snapshot.dialogue
        if dialogue is None:
            return None
        if dialogue.dialogue_id != dialogue_id or dialogue.version != expected_version or dialogue.state is not state:
            return None
        if dialogue.thread_id is None:
            return None
        return dialogue

    async def _reservation(self, profile_id: str) -> object | None:
        current = self._reservations.get(profile_id)
        if current is not None:
            proof = current.quiescence_proof()
            if getattr(proof, "reserved", False):
                return current
            return None
        try:
            reservation = await self._runtime_manager.reserve(profile_id)
        except Exception:
            return None
        if not callable(getattr(reservation, "quiescence_proof", None)):
            return None
        self._reservations[profile_id] = reservation
        return reservation

    def _profile(self, profile_id: str):
        getter = getattr(self._runtime_manager, "profile", None)
        if callable(getter):
            return getter(profile_id)
        profiles = getattr(self._runtime_manager, "_profiles", {})
        if isinstance(profiles, dict) and profile_id in profiles:
            return profiles[profile_id]
        raise DeleteStorageCleanupError(DeleteStorageCleanupReason.RECREATE_FAILED)

    @staticmethod
    def _quiescent(reservation: object) -> bool:
        proof = reservation.quiescence_proof()
        return (
            getattr(proof, "reserved", False) is True
            and getattr(proof, "starting_child", False) is False
            and getattr(proof, "ready_child", False) is False
            and getattr(proof, "unresolved_child", False) is False
        )

    async def _prepare(self, dialogue: DialogueRecord, reservation: object) -> DeleteStorageCleanupReason | None:
        try:
            await self._runtime_manager.shutdown_profile(dialogue.profile_id)
        except Exception:
            return DeleteStorageCleanupReason.SHUTDOWN_FAILED
        try:
            if not self._quiescent(reservation):
                return DeleteStorageCleanupReason.QUIESCENCE_FAILED
        except Exception:
            return DeleteStorageCleanupReason.QUIESCENCE_FAILED
        try:
            await self._runtime_manager.recreate_isolated_state_root(reservation)
        except Exception:
            return DeleteStorageCleanupReason.RECREATE_FAILED
        return None

    async def _cleanup_confirmed(self, dialogue_id: str, expected_version: int) -> DeleteStorageCleanupResult:
        dialogue: DialogueRecord | None = None
        try:
            dialogue = await self._load_dialogue(dialogue_id, expected_version, DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
            if dialogue is None:
                live = await DialogueRepository(self._storage).get_live()
                if live is not None:
                    return DeleteStorageCleanupResult(
                        DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE,
                        live, reason=DeleteStorageCleanupReason.FINALIZE_FAILED,
                    )
                tombstone = await DeletionRepository(self._storage).get_tombstone(dialogue_id)
                if self._valid_replay_tombstone(tombstone, dialogue_id, expected_version):
                    return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, None, tombstone)
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, None, reason=DeleteStorageCleanupReason.FINALIZE_FAILED)
            reservation = await self._reservation(dialogue.profile_id)
            if reservation is None:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.RESERVATION_FAILED)
            failure = await self._prepare(dialogue, reservation)
            if failure is not None:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=failure)
            profile = self._profile(dialogue.profile_id)
            try:
                scan = self._scanner.scan(profile, dialogue.thread_id or "")
            except Exception:
                return DeleteStorageCleanupResult(
                    DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE,
                    dialogue,
                    reason=DeleteStorageCleanupReason.PERSISTENT_SCAN_ERROR,
                )
            if scan.limit_exceeded:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.LIMIT_EXCEEDED, scan=scan)
            if scan.scan_errors:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.PERSISTENT_SCAN_ERROR, scan=scan)
            if scan.match_count:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.PERSISTENT_RESIDUAL_MATCHES, scan=scan)
            try:
                now = self._clock()
                if type(now) is not int or now < 0:
                    raise ValueError
                expiry = max(now, dialogue.updated_at_ms) + self._retention_ms
                finalized = await DeletionRepository(self._storage, now_ms=self._clock).finalize_confirmed(
                    dialogue_id=dialogue_id, expected_version=dialogue.version,
                    tombstone_expires_at_ms=expiry,
                )
            except Exception:
                replay = await self._reconcile_committed_tombstone(
                    dialogue, dialogue_id, expected_version
                )
                if replay is not None:
                    release_error = await self._release_after_commit(dialogue.profile_id, reservation)
                    return DeleteStorageCleanupResult(
                        replay.status, replay.dialogue, replay.tombstone,
                        reason=release_error, scan=scan,
                    )
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.FINALIZE_FAILED, scan=scan)
            if not self._valid_finalize_result(finalized, dialogue):
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.FINALIZE_FAILED, scan=scan)
            release_error = await self._release_after_commit(dialogue.profile_id, reservation)
            return DeleteStorageCleanupResult(
                DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, None, finalized.tombstone,
                reason=release_error, scan=scan,
            )
        except Exception:
            if dialogue is None:
                try:
                    dialogue = await DialogueRepository(self._storage).get_live()
                except Exception:
                    pass
            return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, dialogue, reason=DeleteStorageCleanupReason.FINALIZE_FAILED)

    @staticmethod
    def _valid_finalize_result(value: object, pending: DialogueRecord) -> bool:
        if type(value) is not DeletionFinalizeResult:
            return False
        tombstone = value.tombstone
        if type(tombstone) is not DeletionTombstoneRecord:
            return False
        if (
            tombstone.dialogue_id != pending.dialogue_id
            or tombstone.stale_generation != pending.version
            or tombstone.thread_identity_sha256 != hashlib.sha256(pending.thread_id.encode("utf-8")).hexdigest()
            or type(tombstone.deleted_at_ms) is not int
            or tombstone.deleted_at_ms < pending.updated_at_ms
            or type(tombstone.expires_at_ms) is not int
            or tombstone.expires_at_ms <= tombstone.deleted_at_ms
        ):
            return False
        counts = (
            value.purged_jobs,
            value.purged_payloads,
            value.purged_delivery_segments,
            value.purged_approvals,
        )
        return all(type(count) is int and 0 <= count <= 9223372036854775807 for count in counts)

    @classmethod
    def _valid_replay_tombstone(
        cls, tombstone: object, dialogue_id: str, expected_version: int
    ) -> bool:
        return (
            type(tombstone) is DeletionTombstoneRecord
            and tombstone.dialogue_id == dialogue_id
            and tombstone.stale_generation == expected_version
            and type(tombstone.deleted_at_ms) is int
            and type(tombstone.expires_at_ms) is int
            and tombstone.expires_at_ms > tombstone.deleted_at_ms
        )

    async def _reconcile_committed_tombstone(
        self, pending: DialogueRecord, dialogue_id: str, expected_version: int
    ) -> DeleteStorageCleanupResult | None:
        try:
            live = await DialogueRepository(self._storage).get_live()
            tombstone = await DeletionRepository(self._storage).get_tombstone(dialogue_id)
        except Exception:
            return None
        if live is not None or not self._valid_replay_tombstone(tombstone, dialogue_id, expected_version):
            return None
        if tombstone.thread_identity_sha256 != hashlib.sha256(pending.thread_id.encode("utf-8")).hexdigest():
            return None
        return DeleteStorageCleanupResult(
            DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, None, tombstone
        )

    async def _release_after_commit(
        self, profile_id: str, reservation: object
    ) -> DeleteStorageCleanupReason | None:
        try:
            await reservation.release()
        except Exception:
            return DeleteStorageCleanupReason.RESERVATION_RELEASE_FAILED
        self._reservations.pop(profile_id, None)
        return None

    async def _contain_unknown(self, dialogue_id: str, expected_version: int) -> DeleteStorageCleanupResult:
        dialogue: DialogueRecord | None = None
        try:
            dialogue = await self._load_dialogue(dialogue_id, expected_version, DialogueState.DELETE_UNKNOWN)
            if dialogue is None:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_PENDING, reason=DeleteStorageCleanupReason.CONTAINMENT_FAILED)
            repository = DeleteStorageContainmentRepository(self._storage, now_ms=self._clock)
            existing = await repository.get(dialogue_id)
            reservation = self._reservations.get(dialogue.profile_id)
            if existing is not None and reservation is not None:
                try:
                    if self._quiescent(reservation):
                        return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_CONTAINED, dialogue)
                except Exception:
                    pass
            reservation = await self._reservation(dialogue.profile_id)
            if reservation is None:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_PENDING, dialogue, reason=DeleteStorageCleanupReason.RESERVATION_FAILED)
            failure = await self._prepare(dialogue, reservation)
            if failure is not None:
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_PENDING, dialogue, reason=failure)
            record = await repository.mark_unknown_contained(
                dialogue_id=dialogue_id, expected_dialogue_version=dialogue.version
            )
            if not isinstance(record, DeleteStorageContainmentRecord) or (
                record.dialogue_id != dialogue_id
                or record.profile_id != dialogue.profile_id
                or record.dialogue_version != dialogue.version
                or record.thread_identity_sha256 != hashlib.sha256(dialogue.thread_id.encode("utf-8")).hexdigest()
                or record.official_delete_authority != "UNKNOWN"
                or record.local_isolated_storage_containment != "COMPLETED"
            ):
                return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_PENDING, dialogue, reason=DeleteStorageCleanupReason.CONTAINMENT_FAILED)
            return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_CONTAINED, dialogue)
        except Exception:
            if dialogue is None:
                try:
                    dialogue = await DialogueRepository(self._storage).get_live()
                except Exception:
                    pass
            return DeleteStorageCleanupResult(DeleteStorageCleanupStatus.UNKNOWN_PENDING, dialogue, reason=DeleteStorageCleanupReason.CONTAINMENT_FAILED)

    async def _await_owned(self, task: asyncio.Task[DeleteStorageCleanupResult]) -> DeleteStorageCleanupResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.done() and task.cancelled():
                    raise DeleteStorageCleanupError(DeleteStorageCleanupReason.FINALIZE_FAILED)


__all__ = [
    "DeleteStorageCleanupCoordinator",
    "DeleteStorageCleanupError",
    "DeleteStorageCleanupReason",
    "DeleteStorageCleanupResult",
    "DeleteStorageCleanupStatus",
    "P7C4_DELETE_TOMBSTONE_RETENTION_MS",
]
