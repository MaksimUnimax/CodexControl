"""Dialogue and turn snapshots. These objects do not invoke Codex."""
from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4

from .domain import CodexSelection, DialogueBinding


class DialogueState(StrEnum):
    NO_DIALOGUE = "NO_DIALOGUE"
    ACTIVE_DIALOGUE = "ACTIVE_DIALOGUE"
    TURN_RUNNING = "TURN_RUNNING"
    DELETE_PENDING = "DELETE_PENDING"
    DELETING = "DELETING"
    DELETED = "DELETED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TurnSnapshot:
    turn_id: str
    binding: DialogueBinding


def bind_dialogue(server_id: str, selection: CodexSelection, thread_id: str) -> DialogueBinding:
    return DialogueBinding(server_id, selection.profile.profile_id, thread_id, selection.model, selection.reasoning_effort)


def capture_turn(binding: DialogueBinding) -> TurnSnapshot:
    """Capture immutable execution routing before a turn is claimed."""
    return TurnSnapshot(str(uuid4()), binding)
