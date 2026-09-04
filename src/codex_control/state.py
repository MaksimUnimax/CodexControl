"""State-machine vocabulary for the later durable adapter."""
from enum import StrEnum


class JobState(StrEnum):
    RECEIVED = "RECEIVED"
    CLAIMED = "CLAIMED"
    CODEX_RUNNING = "CODEX_RUNNING"
    CODEX_COMPLETED = "CODEX_COMPLETED"
    TELEGRAM_DELIVERING = "TELEGRAM_DELIVERING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
