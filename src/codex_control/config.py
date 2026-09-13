"""Explicit, fail-closed production server configuration parsing.

The small legacy parser remains available for the frozen foundation tests.  A
production load always uses :func:`load_production_configuration`, which
requires the complete V1 authority and never discovers profiles from disk.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import tomllib
import unicodedata

from .domain import CodexProfile, ServerIdentity
from .application.fleet_control import FleetManifest, FleetMember
from .application.response_delivery import P61_MIN_TEXT_LIMIT, P61_MAX_TEXT_LIMIT


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
    operator_user_id: int | None = None
    control_chat_id: int | None = None
    fleet: FleetManifest | None = None
    state_root: str | None = None
    working_directory: str | None = None
    telegram_text_limit: int = P61_MAX_TEXT_LIMIT
    codex_executable: str = "/usr/local/bin/codex"
    expected_codex_version: str = "0.144.6"

    def __repr__(self) -> str:
        return (
            f"ServerConfiguration(identity={self.identity!r}, "
            f"profiles={tuple((p.profile_id, p.display_name) for p in self.profiles)!r}, "
            f"fleet_version={None if self.fleet is None else self.fleet.fleet_version!r})"
        )


def _path(value: object, category: str) -> str:
    if not isinstance(value, str) or not value or any(unicodedata.category(char) == "Cc" for char in value):
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


_ID_RE = re.compile(r"[A-Za-z0-9_.:-]+")
_MAX_ID = 9_223_372_036_854_775_807


def _required_path(value: object, category: str) -> str:
    result = _path(value, category)
    if _existing_path_has_symlink_component(result):
        raise ConfigurationError("symlink_path")
    return result


def _required_executable_path(value: object) -> str:
    result = _path(value, "codex_executable_invalid")
    # Installed command shims may be symlinks; their containing authority
    # chain must still be physical and non-symlinked.
    if _existing_path_has_symlink_component(os.path.dirname(result)):
        raise ConfigurationError("symlink_path")
    return result


def _valid_identifier(value: object, maximum: int = 128) -> bool:
    return (
        type(value) is str and 1 <= len(value) <= maximum and
        _ID_RE.fullmatch(value) is not None
    )


def _valid_display(value: object, maximum: int = 64) -> bool:
    return (
        type(value) is str and 1 <= len(value) <= maximum and
        "\x00" not in value and not any(unicodedata.category(char) == "Cc" for char in value) and
        value == " ".join(value.split())
    )


def _required_int(value: object, category: str, *, positive: bool = False) -> int:
    if type(value) is not int or not (1 <= value <= _MAX_ID if positive else value != 0):
        raise ConfigurationError(category)
    return value


def _secure_config_file(path: str | Path, *, test_only: bool) -> None:
    """Validate a config file without reading or reporting its contents."""
    try:
        info = os.stat(path, follow_symlinks=False)
    except OSError:
        raise ConfigurationError("config_unavailable") from None
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o022:
        raise ConfigurationError("config_permissions")
    if not test_only and info.st_uid != 0:
        raise ConfigurationError("config_owner")


def parse_production_server_configuration(data: object) -> ServerConfiguration:
    """Parse the complete V1 production schema.

    This function is deliberately separate from the permissive foundation
    parser so old P0 tests retain their source contract while executable
    production loading is strict.
    """
    if not isinstance(data, dict) or not isinstance(data.get("server"), dict):
        raise ConfigurationError("server_invalid")
    server = data["server"]
    if not _valid_identifier(server.get("server_id")):
        raise ConfigurationError("server_invalid")
    if not _valid_display(server.get("display_name")):
        raise ConfigurationError("display_name_invalid")
    operator = _required_int(server.get("operator_user_id"), "operator_invalid", positive=True)
    control_chat = server.get("control_chat_id")
    if type(control_chat) is not int or not -(2**63) <= control_chat <= -1:
        raise ConfigurationError("control_chat_invalid")
    fleet_version = server.get("fleet_version")
    if not _valid_identifier(fleet_version):
        raise ConfigurationError("fleet_invalid")

    fleet_data = data.get("fleet")
    if not isinstance(fleet_data, dict) or not isinstance(fleet_data.get("servers"), list):
        raise ConfigurationError("fleet_missing")
    members: list[FleetMember] = []
    for item in fleet_data["servers"]:
        if not isinstance(item, dict) or set(item) != {"server_id", "display_name"}:
            raise ConfigurationError("fleet_invalid")
        if not _valid_identifier(item.get("server_id")) or not _valid_display(item.get("display_name")):
            raise ConfigurationError("fleet_invalid")
        try:
            members.append(FleetMember(item["server_id"], item["display_name"]))
        except Exception:
            raise ConfigurationError("fleet_invalid") from None
    if not members:
        raise ConfigurationError("fleet_missing")
    try:
        fleet = FleetManifest(fleet_version, tuple(members))
    except Exception:
        raise ConfigurationError("fleet_invalid") from None
    if sum(member.server_id == server["server_id"] for member in members) != 1:
        raise ConfigurationError("own_server_missing")
    if next(member.display_name for member in members if member.server_id == server["server_id"]) != server["display_name"]:
        raise ConfigurationError("own_server_display_mismatch")

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ConfigurationError("runtime_missing")
    state_root = _required_path(runtime.get("state_root"), "state_root_invalid")
    working_directory = _required_path(runtime.get("working_directory"), "working_directory_invalid")
    text_limit = runtime.get("telegram_text_limit")
    if type(text_limit) is not int or not P61_MIN_TEXT_LIMIT <= text_limit <= P61_MAX_TEXT_LIMIT:
        raise ConfigurationError("telegram_text_limit_invalid")
    executable = runtime.get("codex_executable", "/usr/local/bin/codex")
    executable = _required_executable_path(executable)
    expected_codex_version = runtime.get("expected_codex_version", "0.144.6")
    if expected_codex_version != "0.144.6":
        raise ConfigurationError("codex_version_invalid")
    if not isinstance(runtime.get("repository_root"), str) and not isinstance(data.get("repository_root"), str):
        raise ConfigurationError("repository_root_missing")
    repository_root = _required_path(runtime.get("repository_root", data.get("repository_root")), "repository_root_invalid")
    db_path_value = runtime.get("controller_db_path")
    db_path = _required_path(db_path_value, "controller_db_invalid") if db_path_value is not None else os.path.join(state_root, "controller.sqlite3")
    db_root = _required_path(runtime.get("controller_db_root", state_root), "controller_db_root_invalid")
    raw_protected = runtime.get("protected_roots", data.get("protected_roots", []))
    if not isinstance(raw_protected, list):
        raise ConfigurationError("protected_path_invalid")
    protected = tuple(_required_path(item, "protected_path_invalid") for item in raw_protected)

    raw_profiles = data.get("profiles")
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise ConfigurationError("profiles_missing")
    parsed: list[CodexProfile] = []
    for item in raw_profiles:
        if not isinstance(item, dict) or set(item) != {"profile_id", "display_name", "codex_home", "isolated_state_root"}:
            raise ConfigurationError("profile_invalid")
        if not _valid_identifier(item.get("profile_id")):
            raise ConfigurationError("profile_id_invalid")
        if not _valid_display(item.get("display_name"), 256):
            raise ConfigurationError("display_name_invalid")
        home = _required_path(item.get("codex_home"), "codex_home_invalid")
        isolated = _required_path(item.get("isolated_state_root"), "isolated_state_root_invalid")
        parsed.append(CodexProfile(item["profile_id"], home, item["display_name"], isolated))
    profile_ids = [item.profile_id for item in parsed]
    profile_names = [item.display_name for item in parsed]
    if len(profile_ids) != len(set(profile_ids)):
        raise ConfigurationError("duplicate_profile_id")
    if len(profile_names) != len(set(profile_names)):
        raise ConfigurationError("duplicate_profile_display_name")
    all_paths = [item.codex_home for item in parsed] + [item.isolated_state_root for item in parsed]
    protected_all = (state_root, db_path, db_root, repository_root) + protected
    if any(_overlap(left, right) for index, left in enumerate(all_paths) for right in all_paths[index + 1:]):
        raise ConfigurationError("profile_path_overlap")
    if any(_overlap(left, right) for left in all_paths for right in protected_all):
        raise ConfigurationError("protected_path_overlap")
    return ServerConfiguration(
        ServerIdentity(server["server_id"], server["display_name"]), tuple(parsed),
        db_path, db_root, repository_root, protected, operator, control_chat, fleet,
        state_root, working_directory, text_limit, executable, expected_codex_version,
    )


def load_production_configuration(path: str | Path, *, test_only: bool = False) -> ServerConfiguration:
    path = Path(path)
    _secure_config_file(path, test_only=test_only)
    try:
        with path.open("rb") as handle:
            return parse_production_server_configuration(tomllib.load(handle))
    except ConfigurationError:
        raise
    except (OSError, tomllib.TOMLDecodeError):
        raise ConfigurationError("config_invalid") from None
