"""Configuration parsing. Secrets intentionally have no representation here."""
from dataclasses import dataclass
from pathlib import Path
import tomllib

from .domain import CodexProfile, ServerIdentity


@dataclass(frozen=True)
class ServerConfiguration:
    identity: ServerIdentity
    profiles: tuple[CodexProfile, ...]


def parse_server_configuration(data: dict) -> ServerConfiguration:
    server = data["server"]
    profiles = tuple(CodexProfile(**item) for item in data.get("profiles", []))
    ids = [profile.profile_id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("profile_id values must be unique")
    return ServerConfiguration(ServerIdentity(server["server_id"], server["display_name"]), profiles)


def load_server_configuration(path: str | Path) -> ServerConfiguration:
    with Path(path).open("rb") as handle:
        return parse_server_configuration(tomllib.load(handle))
