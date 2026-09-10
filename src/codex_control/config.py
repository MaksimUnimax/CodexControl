"""Explicit, fail-closed server configuration parsing."""
from dataclasses import dataclass
import os
from pathlib import Path
import tomllib

from .domain import CodexProfile, ServerIdentity


class ConfigurationError(ValueError):
    """Safe configuration failure; paths and parser details are not rendered."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


@dataclass(frozen=True, repr=False)
class ServerConfiguration:
    identity: ServerIdentity
    profiles: tuple[CodexProfile, ...]
    controller_db_path: str | None = None
    controller_db_root: str | None = None
    repository_root: str | None = None
    protected_roots: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            f"ServerConfiguration(identity={self.identity!r}, "
            f"profiles={tuple((p.profile_id, p.display_name) for p in self.profiles)!r})"
        )


def _path(value: object, category: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ConfigurationError(category)
    if not os.path.isabs(value):
        raise ConfigurationError("relative_path")
    return os.path.normpath(os.path.abspath(value))


def _overlap(left: str, right: str) -> bool:
    try:
        return os.path.commonpath((left, right)) == left or os.path.commonpath((left, right)) == right
    except ValueError:
        return False


def _existing_path_has_symlink_component(value: str) -> bool:
    path_object = Path(value)
    current = Path(path_object.anchor or os.sep)
    for part in path_object.parts[1:]:
        current /= part
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
    return False


def _optional_path(data: dict, *keys: str) -> str | None:
    for key in keys:
        if key in data and data[key] is not None:
            return _path(data[key], "protected_path_invalid")
    return None


def parse_server_configuration(data: dict) -> ServerConfiguration:
    if not isinstance(data, dict) or not isinstance(data.get("server"), dict):
        raise ConfigurationError("server_invalid")
    server = data["server"]
    if not isinstance(server.get("server_id"), str) or not server["server_id"] or "\x00" in server["server_id"]:
        raise ConfigurationError("server_invalid")
    if not isinstance(server.get("display_name"), str) or not server["display_name"]:
        raise ConfigurationError("server_invalid")
    raw_profiles = data.get("profiles", [])
    if not isinstance(raw_profiles, list):
        raise ConfigurationError("profiles_invalid")
    profiles_list: list[CodexProfile] = []
    for item in raw_profiles:
        if not isinstance(item, dict) or set(item) != {"profile_id", "codex_home", "display_name", "isolated_state_root"}:
            raise ConfigurationError("isolated_state_root_required")
        profile_id = item.get("profile_id")
        display_name = item.get("display_name")
        if not isinstance(profile_id, str) or not profile_id or "\x00" in profile_id or "\n" in profile_id or "\r" in profile_id:
            raise ConfigurationError("profile_id_invalid")
        if not isinstance(display_name, str) or not display_name:
            raise ConfigurationError("display_name_invalid")
        home = _path(item.get("codex_home"), "codex_home_invalid")
        state_root = _path(item.get("isolated_state_root"), "isolated_state_root_invalid")
        if _existing_path_has_symlink_component(home) or _existing_path_has_symlink_component(state_root):
            raise ConfigurationError("symlink_path")
        profiles_list.append(CodexProfile(profile_id, home, display_name, state_root))
    profiles = tuple(profiles_list)
    ids = [profile.profile_id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("duplicate_profile_id")

    homes = [os.path.normpath(os.path.abspath(p.codex_home)) for p in profiles]
    roots = [os.path.normpath(os.path.abspath(p.isolated_state_root)) for p in profiles]
    if len(set(homes)) != len(homes):
        raise ConfigurationError("duplicate_codex_home")
    if len(set(roots)) != len(roots):
        raise ConfigurationError("duplicate_isolated_state_root")
    all_profile_paths = [(home, root) for home, root in zip(homes, roots)]
    for home, root in all_profile_paths:
        if _overlap(home, root):
            raise ConfigurationError("profile_home_state_overlap")
    for index, (home, root) in enumerate(all_profile_paths):
        for other_home, other_root in all_profile_paths[index + 1:]:
            if any(_overlap(left, right) for left in (home, root) for right in (other_home, other_root)):
                raise ConfigurationError("profile_path_overlap")

    controller = data.get("controller") if isinstance(data.get("controller"), dict) else {}
    controller_db_path = _optional_path(data, "controller_db_path") or _optional_path(controller, "database_path")
    controller_db_root = _optional_path(data, "controller_db_root") or _optional_path(controller, "state_root")
    repository_root = _optional_path(data, "repository_root")
    raw_protected = data.get("protected_roots", ())
    if not isinstance(raw_protected, (list, tuple)):
        raise ConfigurationError("protected_path_invalid")
    protected_roots = tuple(_path(value, "protected_path_invalid") for value in raw_protected)
    configured_protected = tuple(
        path for path in (controller_db_path, controller_db_root, repository_root) if path is not None
    ) + protected_roots
    if any(_existing_path_has_symlink_component(path) for path in configured_protected):
        raise ConfigurationError("symlink_path")
    protected = tuple(path for path in (controller_db_path, controller_db_root, repository_root) if path) + protected_roots
    if len(set(protected)) != len(protected):
        raise ConfigurationError("duplicate_protected_path")
    if any(_overlap(profile_path, protected_path) for profile_path in homes + roots for protected_path in protected):
        raise ConfigurationError("protected_path_overlap")
    return ServerConfiguration(
        ServerIdentity(server["server_id"], server["display_name"]), profiles,
        controller_db_path, controller_db_root, repository_root, protected_roots,
    )


def load_server_configuration(path: str | Path) -> ServerConfiguration:
    with Path(path).open("rb") as handle:
        return parse_server_configuration(tomllib.load(handle))
