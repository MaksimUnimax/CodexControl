"""Small, secret-free types for Codex app-server protocol version 0.144.6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


CODEX_APP_SERVER_VERSION = "0.144.6"
CLIENT_NAME = "codex_control"
CLIENT_TITLE = "CodexControl"


class AsyncLineTransport(Protocol):
    """A newline-delimited protocol transport with no process ownership."""

    async def send(self, message: dict[str, Any]) -> None:
        """Send one decoded protocol message as one transport line."""

    async def receive(self) -> str | None:
        """Receive one raw protocol line, or ``None`` at EOF."""


@dataclass(frozen=True)
class ClientInfo:
    name: str
    version: str
    title: str = CLIENT_TITLE

    def as_params(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version, "title": self.title}


@dataclass(frozen=True)
class InitializeResult:
    """The required installed-0.144.6 initialize result fields."""

    user_agent: str
    codex_home: str
    platform_family: str
    platform_os: str

    @classmethod
    def from_result(cls, result: Any) -> "InitializeResult":
        if not isinstance(result, dict):
            raise ValueError("initialize_result_not_object")
        fields = {
            "userAgent": "user_agent",
            "codexHome": "codex_home",
            "platformFamily": "platform_family",
            "platformOs": "platform_os",
        }
        values: dict[str, str] = {}
        for wire_name, attribute in fields.items():
            value = result.get(wire_name)
            if not isinstance(value, str):
                raise ValueError("initialize_result_invalid")
            values[attribute] = value
        return cls(**values)
