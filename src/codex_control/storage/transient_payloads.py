"""Immutable bounded transient payload records for P2.4a."""

from dataclasses import dataclass, field
from enum import StrEnum


MAX_TRANSIENT_PAYLOAD_BYTES = 8_388_608


class TransientPayloadKind(StrEnum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    APPROVAL = "APPROVAL"
    DISPLAY = "DISPLAY"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TransientPayloadRecord:
    payload_id: str
    dialogue_id: str | None
    job_id: str | None
    kind: TransientPayloadKind
    content: bytes = field(repr=False)
    content_sha256: str
    byte_length: int
    created_at_ms: int
    expires_at_ms: int
