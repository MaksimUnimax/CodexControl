"""Immutable materialized records used by the core durable repositories."""

from dataclasses import dataclass
from enum import StrEnum

from codex_control.domain import ControllerMode


class DialogueState(StrEnum):
    CREATING = "CREATING"
    IDLE = "IDLE"
    CREATE_UNKNOWN = "CREATE_UNKNOWN"
    ERROR = "ERROR"
    TURN_RUNNING = "TURN_RUNNING"
    INTERRUPTING = "INTERRUPTING"
    TURN_UNKNOWN = "TURN_UNKNOWN"
    DELETE_PENDING = "DELETE_PENDING"
    DELETING = "DELETING"
    DELETE_UNKNOWN = "DELETE_UNKNOWN"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ControllerRuntimeRecord:
    last_control_epoch: int
    requested_mode: ControllerMode
    boot_generation: int
    fleet_version: str
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class ControllerBootResult:
    record: ControllerRuntimeRecord
    effective_mode: ControllerMode


@dataclass(frozen=True)
class SettingsRecord:
    profile_id: str | None
    model_id: str | None
    reasoning_effort: str | None
    version: int
    created_at_ms: int
    updated_at_ms: int


@dataclass(frozen=True)
class SettingsInitializeResult:
    record: SettingsRecord
    created: bool


@dataclass(frozen=True)
class DialogueRecord:
    dialogue_id: str
    server_id: str
    profile_id: str
    thread_id: str | None
    state: DialogueState
    version: int
    created_at_ms: int
    updated_at_ms: int
    last_error_class: str | None
