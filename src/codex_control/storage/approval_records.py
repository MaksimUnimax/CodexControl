"""Immutable approval records and callback-claim results for P2.4b."""

from dataclasses import dataclass
from enum import StrEnum

from codex_control.adapters.codex.approvals import ApprovalKind


class ApprovalState(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"

    def __str__(self) -> str:
        return self.value


class ApprovalCallbackClaimStatus(StrEnum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    EXPIRED = "EXPIRED"
    ALREADY_CONSUMED = "ALREADY_CONSUMED"
    STALE = "STALE"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    profile_id: str
    wire_request_id: str | int
    kind: ApprovalKind
    job_id: str
    display_payload_id: str | None
    state: ApprovalState
    created_at_ms: int
    updated_at_ms: int
    expires_at_ms: int


@dataclass(frozen=True)
class ApprovalCallbackClaimResult:
    status: ApprovalCallbackClaimStatus
    record: ApprovalRecord | None
