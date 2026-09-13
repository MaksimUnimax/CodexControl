"""Exact-SHA release layout and non-destructive offline transactions."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .adapters.codex.capabilities import SCHEMA_SHA256, SUPPORTED_CODEX_VERSION
from .secrets import load_secrets


class DeploymentError(RuntimeError):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)

    def __repr__(self) -> str:
        return f"DeploymentError({self.category!r})"


_SHA = re.compile(r"[0-9a-f]{40,64}\Z")
_MAX_MANIFEST = 256 * 1024


@dataclass(frozen=True)
class ReleaseManifest:
    product_name: str
    package_version: str
    git_sha: str
    python_requirement: str
    expected_codex_version: str
    codex_capability_schema_sha256: str
    supported_controller_db_schema: int
    artifact_digests: dict[str, str]
    service_unit_sha256: str | None = None
    manifest_format: int = 1

    def to_bytes(self) -> bytes:
        return (json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()

    @classmethod
    def from_bytes(cls, value: bytes) -> "ReleaseManifest":
        if not isinstance(value, bytes) or len(value) > _MAX_MANIFEST:
            raise DeploymentError("manifest_invalid")
        try:
            raw = json.loads(value.decode("utf-8"))
            result = cls(**raw)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError):
            raise DeploymentError("manifest_invalid") from None
        if result.manifest_format != 1 or result.product_name != "codex-control":
            raise DeploymentError("manifest_invalid")
        if not _SHA.fullmatch(result.git_sha) or result.expected_codex_version != SUPPORTED_CODEX_VERSION:
            raise DeploymentError("manifest_invalid")
        if result.codex_capability_schema_sha256 != SCHEMA_SHA256 or result.supported_controller_db_schema != 4:
            raise DeploymentError("manifest_invalid")
        if not isinstance(result.artifact_digests, dict) or any(
            not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or
            not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for path, digest in result.artifact_digests.items()
        ):
            raise DeploymentError("manifest_invalid")
        if result.service_unit_sha256 is not None and re.fullmatch(r"[0-9a-f]{64}", result.service_unit_sha256) is None:
            raise DeploymentError("manifest_invalid")
        return result


def _layout_root(root: str | os.PathLike[str]) -> Path:
    value = Path(root)
    if not value.is_absolute() or value == Path("/") or value.is_symlink():
        raise DeploymentError("alternate_root_required")
    return value


def _assert_layout_chain(root: Path) -> None:
    current = root
    for component in ("opt", "codex-control", "releases"):
        current = current / component
        if current.is_symlink():
            raise DeploymentError("layout_symlink")


def release_path(root: str | os.PathLike[str], git_sha: str) -> Path:
    root_path = _layout_root(root)
    _assert_layout_chain(root_path)
    if not isinstance(git_sha, str) or _SHA.fullmatch(git_sha) is None:
        raise DeploymentError("release_sha_invalid")
    return root_path / "opt" / "codex-control" / "releases" / git_sha


def _regular_files(path: Path) -> list[Path]:
    files: list[Path] = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise DeploymentError("release_symlink")
        if item.is_file():
            files.append(item)
    return files


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise DeploymentError("artifact_unreadable") from None
    return digest.hexdigest()


def _manifest_for(release: Path, *, package_version: str, git_sha: str, python_requirement: str,
                  service_unit: Path | None) -> ReleaseManifest:
    digests = {
        str(item.relative_to(release)): _digest(item)
        for item in _regular_files(release) if item.name != "release-manifest.json"
    }
    unit_digest = _digest(service_unit) if service_unit is not None else None
    return ReleaseManifest("codex-control", package_version, git_sha, python_requirement,
                           SUPPORTED_CODEX_VERSION, SCHEMA_SHA256, 4, digests, unit_digest)


def stage_release(source: str | os.PathLike[str], *, root: str | os.PathLike[str], git_sha: str,
                  package_version: str = "0.1.0", python_requirement: str = ">=3.11",
                  service_unit: str | os.PathLike[str] | None = None) -> tuple[Path, str]:
    """Copy an immutable artifact into the explicit alternate-root layout."""
    target = release_path(root, git_sha)
    source_path = Path(source).resolve()
    if not source_path.is_dir() or (target.exists() and source_path == target.resolve()):
        raise DeploymentError("release_source_invalid")
    if source_path == _layout_root(root) or _layout_root(root) in source_path.parents:
        raise DeploymentError("release_source_invalid")
    _regular_files(source_path)
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise DeploymentError("release_target_invalid")
        manifest_path = target / "release-manifest.json"
        if not manifest_path.is_file():
            raise DeploymentError("release_already_present_invalid")
        existing = validate_release(target)
        if existing.git_sha != git_sha:
            raise DeploymentError("release_already_present_invalid")
        return target, hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    try:
        shutil.copytree(source_path, target, symlinks=False, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        unit = Path(service_unit) if service_unit is not None else None
        manifest = _manifest_for(target, package_version=package_version, git_sha=git_sha,
                                python_requirement=python_requirement, service_unit=unit)
        (target / "release-manifest.json").write_bytes(manifest.to_bytes())
        for item in _regular_files(target):
            os.chmod(item, 0o555 if os.access(item, os.X_OK) else 0o444)
        for directory in sorted((item for item in target.rglob("*") if item.is_dir()), reverse=True):
            os.chmod(directory, 0o555)
    except DeploymentError:
        raise
    except (OSError, shutil.Error):
        raise DeploymentError("release_stage_failed") from None
    data = (target / "release-manifest.json").read_bytes()
    return target, hashlib.sha256(data).hexdigest()


def validate_release(path: str | os.PathLike[str], *, current_db_schema: int = 4) -> ReleaseManifest:
    release = Path(path)
    if not release.is_absolute() or release.is_symlink() or not release.is_dir():
        raise DeploymentError("release_invalid")
    manifest_path = release / "release-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise DeploymentError("manifest_missing")
    manifest = ReleaseManifest.from_bytes(manifest_path.read_bytes())
    if current_db_schema not in {manifest.supported_controller_db_schema}:
        raise DeploymentError("schema_incompatible")
    actual = {str(item.relative_to(release)): _digest(item) for item in _regular_files(release) if item.name != "release-manifest.json"}
    if actual != manifest.artifact_digests:
        raise DeploymentError("artifact_digest_mismatch")
    return manifest


def current_target(root: str | os.PathLike[str]) -> Path | None:
    root_path = _layout_root(root)
    _assert_layout_chain(root_path)
    current = root_path / "opt" / "codex-control" / "current"
    if current.exists() and not current.is_symlink():
        raise DeploymentError("current_target_invalid")
    if not current.is_symlink():
        return None
    target = (current.parent / os.readlink(current)).resolve()
    releases = (current.parent / "releases").resolve()
    if releases not in target.parents or target == releases or not target.is_dir():
        raise DeploymentError("current_target_invalid")
    return target


def switch_current(root: str | os.PathLike[str], git_sha: str, *, current_db_schema: int = 4) -> Path:
    root_path = _layout_root(root)
    target = release_path(root_path, git_sha)
    manifest = validate_release(target, current_db_schema=current_db_schema)
    if manifest.git_sha != git_sha:
        raise DeploymentError("manifest_sha_mismatch")
    current = root_path / "opt" / "codex-control" / "current"
    if current.exists() and not current.is_symlink():
        raise DeploymentError("current_target_invalid")
    current.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    prior = current_target(root_path)
    if prior is not None:
        (current.parent / "previous").write_text(prior.name + "\n", encoding="ascii")
    temp = current.parent / ".current.next"
    if temp.exists() or temp.is_symlink():
        temp.unlink()
    os.symlink(os.path.relpath(target, current.parent), temp)
    os.replace(temp, current)
    return target


def _previous_sha(root: Path) -> str:
    previous = root / "opt" / "codex-control" / "previous"
    try:
        value = previous.read_text(encoding="ascii").strip()
    except OSError:
        raise DeploymentError("previous_release_missing") from None
    if _SHA.fullmatch(value) is None:
        raise DeploymentError("previous_release_invalid")
    return value


def rollback(root: str | os.PathLike[str], *, current_db_schema: int = 4) -> Path:
    root_path = _layout_root(root)
    target = release_path(root_path, _previous_sha(root_path))
    validate_release(target, current_db_schema=current_db_schema)
    return switch_current(root_path, target.name, current_db_schema=current_db_schema)


def install_upgrade(root: str | os.PathLike[str], source: str | os.PathLike[str], *, git_sha: str,
                    current_db_schema: int = 4, health_check: Callable[[], bool] | None = None) -> dict[str, Any]:
    """Stage, atomically switch, and optionally rehearse a health-gated upgrade."""
    root_path = _layout_root(root)
    old = current_target(root_path)
    stage_release(source, root=root_path, git_sha=git_sha)
    switch_current(root_path, git_sha, current_db_schema=current_db_schema)
    healthy = True if health_check is None else bool(health_check())
    rolled_back = False
    if not healthy:
        rollback(root_path, current_db_schema=current_db_schema)
        rolled_back = True
    return {"previous_sha": None if old is None else old.name, "requested_sha": git_sha, "healthy": healthy, "rolled_back": rolled_back, "current_sha": None if current_target(root_path) is None else current_target(root_path).name}


def verify_installation(root: str | os.PathLike[str], *, expected_sha: str | None = None,
                        config_path: str | os.PathLike[str] | None = None,
                        secrets_path: str | os.PathLike[str] | None = None,
                        database_path: str | os.PathLike[str] | None = None,
                        unit_path: str | os.PathLike[str] | None = None,
                        test_only: bool = False) -> dict[str, Any]:
    root_path = _layout_root(root)
    current = current_target(root_path)
    if current is None:
        raise DeploymentError("current_missing")
    manifest = validate_release(current)
    if expected_sha is not None and manifest.git_sha != expected_sha:
        raise DeploymentError("current_sha_mismatch")
    result: dict[str, Any] = {
        "installed_release_sha": manifest.git_sha,
        "manifest_sha256": hashlib.sha256((current / "release-manifest.json").read_bytes()).hexdigest(),
        "current_target": str(current),
        "config_authority": None,
        "secrets_authority": None,
        "controller_db_schema": None,
        "configured_profiles": (),
        "codex_home_authority": (),
        "codex_version_authority": manifest.expected_codex_version,
        "service_unit_sha256": None,
    }
    if config_path is not None:
        try:
            from .config import load_production_configuration
            config = load_production_configuration(config_path, test_only=test_only)
            info = Path(config_path).stat(follow_symlinks=False)
            result["config_authority"] = "ROOT_REGULAR_PRIVATE" if stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) & 0o022 == 0 else "INVALID"
            result["configured_profiles"] = tuple(profile.profile_id for profile in config.profiles)
            result["codex_home_authority"] = tuple(profile.codex_home for profile in config.profiles)
        except Exception:
            raise DeploymentError("config_invalid") from None
    if secrets_path is not None:
        load_secrets(secrets_path, test_only=test_only)
        info = Path(secrets_path).stat(follow_symlinks=False)
        result["secrets_authority"] = "ROOT_0600" if info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600 else "INVALID"
    if database_path is not None:
        try:
            with sqlite3.connect(f"file:{Path(database_path)}?mode=ro", uri=True) as connection:
                schema = connection.execute("PRAGMA user_version").fetchone()[0]
        except (OSError, sqlite3.Error):
            raise DeploymentError("database_unavailable") from None
        if schema != manifest.supported_controller_db_schema:
            raise DeploymentError("schema_incompatible")
        result["controller_db_schema"] = schema
    if unit_path is not None:
        result["service_unit_sha256"] = _digest(Path(unit_path))
    return result


__all__ = ["DeploymentError", "ReleaseManifest", "current_target", "install_upgrade", "release_path", "rollback", "stage_release", "switch_current", "validate_release", "verify_installation"]
