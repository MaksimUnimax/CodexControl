"""Immutable records returned by the P2.5 deletion repository."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeletionTombstoneRecord:
    dialogue_id: str
    thread_identity_sha256: str
    stale_generation: int
    deleted_at_ms: int
    expires_at_ms: int


@dataclass(frozen=True)
class DeletionFinalizeResult:
    tombstone: DeletionTombstoneRecord
    purged_jobs: int
    purged_payloads: int
    purged_delivery_segments: int
    purged_approvals: int
