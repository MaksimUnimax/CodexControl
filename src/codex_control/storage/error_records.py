"""Immutable, content-free error fingerprint records."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorFingerprintRecord:
    fingerprint_sha256: str
    error_class: str
    count: int
    first_seen_at_ms: int
    last_seen_at_ms: int
    dialogue_id: str | None
    job_id: str | None
