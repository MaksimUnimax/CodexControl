"""Immutable records and finite states for P2.4a turn jobs."""

from dataclasses import dataclass
from enum import StrEnum

from .idempotency_records import IngressUpdateRecord
from .records import DialogueRecord
from .transient_payloads import TransientPayloadRecord


class TurnJobState(StrEnum):
    RECEIVED = "RECEIVED"
    CLAIMED = "CLAIMED"
    CODEX_STARTING = "CODEX_STARTING"
    CODEX_RUNNING = "CODEX_RUNNING"
    CODEX_COMPLETED = "CODEX_COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TurnJobRecord:
    job_id: str
    telegram_update_id: int
    source_chat_id: int
    source_message_id: int
    dialogue_id: str
    server_id: str
    profile_id: str
    thread_id: str | None
    model_id: str | None
    reasoning_effort: str | None
    input_sha256: str
    codex_turn_id: str | None
    state: TurnJobState
    version: int
    created_at_ms: int
    updated_at_ms: int
    error_class: str | None


class TurnIngressClaimStatus(StrEnum):
    CREATED = "CREATED"
    DUPLICATE = "DUPLICATE"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TurnIngressClaimResult:
    status: TurnIngressClaimStatus
    ingress: IngressUpdateRecord
    job: TurnJobRecord | None
    input_payload: TransientPayloadRecord | None


@dataclass(frozen=True)
class TurnExecutionClaimResult:
    job: TurnJobRecord
    dialogue: DialogueRecord


class TurnTerminalOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TurnJobFinishResult:
    job: TurnJobRecord
    dialogue: DialogueRecord
    output_payload: TransientPayloadRecord | None
