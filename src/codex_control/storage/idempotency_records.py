"""Immutable records used by ingress/control/callback idempotency repositories."""

from dataclasses import dataclass
from enum import StrEnum

from codex_control.domain import ControllerMode

from .records import ControllerRuntimeRecord


class IngressDispositionKind(StrEnum):
    CONTROL = "CONTROL"
    IGNORED_SLEEP = "IGNORED_SLEEP"
    IGNORED_UNAUTHORIZED = "IGNORED_UNAUTHORIZED"
    JOB = "JOB"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class IngressUpdateRecord:
    update_id: int
    received_at_ms: int
    completed_at_ms: int | None
    disposition: IngressDispositionKind
    job_id: str | None


@dataclass(frozen=True)
class IngressClaimResult:
    record: IngressUpdateRecord
    duplicate: bool


class ControlClaimStatus(StrEnum):
    APPLIED = "APPLIED"
    STALE = "STALE"
    DUPLICATE = "DUPLICATE"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ControlClaimResult:
    status: ControlClaimStatus
    ingress: IngressUpdateRecord
    controller: ControllerRuntimeRecord | None


@dataclass(frozen=True)
class CallbackActionRecord:
    token_hash_sha256: str
    action: str
    subject_type: str
    subject_id: str
    expected_version: int
    expected_state: str
    authorized_user_id: int
    authorized_chat_id: int
    created_at_ms: int
    expires_at_ms: int
    consumed_at_ms: int | None


class CallbackClaimStatus(StrEnum):
    CLAIMED = "CLAIMED"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    EXPIRED = "EXPIRED"
    ALREADY_CONSUMED = "ALREADY_CONSUMED"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CallbackClaimResult:
    status: CallbackClaimStatus
    record: CallbackActionRecord | None
