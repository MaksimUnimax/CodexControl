"""Immutable delivery records and states for P2.4b."""

from dataclasses import dataclass
from enum import StrEnum

from .transient_payloads import TransientPayloadRecord
from .turn_job_records import TurnJobRecord


class DeliveryOperation(StrEnum):
    CREATE = "CREATE"
    EDIT = "EDIT"

    def __str__(self) -> str:
        return self.value


class DeliverySegmentState(StrEnum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value


class DeliveryFinishOutcome(StrEnum):
    CONFIRMED = "CONFIRMED"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DeliveryPlanItem:
    operation: DeliveryOperation
    payload_id: str
    target_message_id: int | None


@dataclass(frozen=True)
class DeliverySegmentRecord:
    job_id: str
    sequence: int
    operation: DeliveryOperation
    target_message_id: int | None
    payload_id: str | None
    payload_sha256: str
    state: DeliverySegmentState
    attempt_count: int
    confirmed_message_id: int | None
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class DeliveryPlanResult:
    job: TurnJobRecord
    segments: tuple[DeliverySegmentRecord, ...]


@dataclass(frozen=True)
class DeliveryClaimResult:
    job: TurnJobRecord
    segment: DeliverySegmentRecord
    payload: TransientPayloadRecord


@dataclass(frozen=True)
class DeliveryFinishResult:
    job: TurnJobRecord
    segment: DeliverySegmentRecord
