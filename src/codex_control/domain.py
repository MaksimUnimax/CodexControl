"""Immutable, secret-free domain objects used by all server controllers."""
from dataclasses import dataclass
from enum import StrEnum


class ControllerMode(StrEnum):
    ACTIVE = "ACTIVE"
    SLEEP = "SLEEP"


@dataclass(frozen=True)
class ServerIdentity:
    server_id: str
    display_name: str


@dataclass(frozen=True, repr=False)
class CodexProfile:
    profile_id: str
    codex_home: str
    display_name: str

    def __repr__(self) -> str:
        return f"CodexProfile(profile_id={self.profile_id!r}, display_name={self.display_name!r}, codex_home='[REDACTED]')"


@dataclass(frozen=True)
class CodexSelection:
    profile: CodexProfile
    model: str | None = None
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class DialogueBinding:
    server_id: str
    profile_id: str
    thread_id: str
