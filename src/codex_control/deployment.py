"""Exact-object release packaging and non-destructive offline transactions."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import uuid
from dataclasses import asdict, dataclass
from enum import StrEnum
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


class DeploymentState(StrEnum):
    PRE_SWITCH_VALIDATED = "PRE_SWITCH_VALIDATED"
    SWITCHED_AWAITING_SERVICE_HEALTH = "SWITCHED_AWAITING_SERVICE_HEALTH"
    HEALTH_CONFIRMED = "HEALTH_CONFIRMED"
    HEALTH_FAILED_ROLLBACK_REQUIRED = "HEALTH_FAILED_ROLLBACK_REQUIRED"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass(frozen=True)
class DeploymentRootAuthority:
    """Explicit layout authority; production root is never implicit."""

    root: Path
    allow_production_root: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.root, Path):
            object.__setattr__(self, "root", Path(self.root))


_SHA = re.compile(r"[0-9a-f]{40}\Z")
_TREE_SHA = _SHA
_MAX_MANIFEST = 256 * 1024
_EXECUTABLE_RELATIVE = ".venv/bin/codex-control"


@dataclass(frozen=True)
class ReleaseManifest:
    product_name: str
    package_version: str
    source_git_sha: str
    source_tree_sha: str
    python_requirement: str
    expected_codex_version: str
    codex_capability_schema_sha256: str
    supported_controller_db_schema: int
    artifact_digests: dict[str, str]
    service_unit_sha256: str | None = None
    manifest_format: int = 1

    @property
    def git_sha(self) -> str:
        """Compatibility spelling; it is the exact source commit SHA."""
        return self.source_git_sha

    def to_bytes(self) -> bytes:
        return (json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()

    @classmethod
    def from_bytes(cls, value: bytes) -> "ReleaseManifest":
        if not isinstance(value, bytes) or len(value) > _MAX_MANIFEST:
            raise DeploymentError("manifest_invalid")
        try:
            raw = json.loads(value.decode("utf-8"))
            required = {
                "product_name", "package_version", "source_git_sha", "source_tree_sha",
                "python_requirement", "expected_codex_version", "codex_capability_schema_sha256",
                "supported_controller_db_schema", "artifact_digests", "service_unit_sha256",
                "manifest_format",
            }
            if not isinstance(raw, dict) or set(raw) != required:
                raise ValueError
            result = cls(**raw)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError):
            raise DeploymentError("manifest_invalid") from None
        if (
            type(result.manifest_format) is not int or result.manifest_format != 1
            or type(result.product_name) is not str or result.product_name != "codex-control"
            or type(result.package_version) is not str or not 1 <= len(result.package_version) <= 128
            or type(result.python_requirement) is not str or not 1 <= len(result.python_requirement) <= 128
            or type(result.expected_codex_version) is not str
            or type(result.codex_capability_schema_sha256) is not str
            or type(result.supported_controller_db_schema) is not int
            or not _SHA.fullmatch(result.source_git_sha or "")
            or not _TREE_SHA.fullmatch(result.source_tree_sha or "")
        ):
            raise DeploymentError("manifest_invalid")
        if (
            result.expected_codex_version != SUPPORTED_CODEX_VERSION
            or result.codex_capability_schema_sha256 != SCHEMA_SHA256
            or result.supported_controller_db_schema != 4
        ):
            raise DeploymentError("manifest_invalid")
        if not isinstance(result.artifact_digests, dict) or any(
            not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts
            or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            for path, digest in result.artifact_digests.items()
        ):
            raise DeploymentError("manifest_invalid")
        if _EXECUTABLE_RELATIVE not in result.artifact_digests:
            raise DeploymentError("executable_missing")
        if result.service_unit_sha256 is not None and (
            not isinstance(result.service_unit_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", result.service_unit_sha256) is None
        ):
            raise DeploymentError("manifest_invalid")
        return result


def _layout_root(root: str | os.PathLike[str] | DeploymentRootAuthority, *, allow_production_root: bool = False) -> Path:
    authority = root if isinstance(root, DeploymentRootAuthority) else None
    value = Path(authority.root if authority is not None else root)
    allow_production_root = allow_production_root or bool(authority and authority.allow_production_root)
    if not value.is_absolute() or (value == Path("/") and not allow_production_root) or value.is_symlink() or ".." in value.parts:
        raise DeploymentError("alternate_root_required")
    current = Path(value.anchor or os.sep)
    for part in value.parts[1:]:
        current /= part
        if current.is_symlink():
            raise DeploymentError("layout_symlink")
    return value


def _assert_layout_chain(root: Path) -> None:
    current = root
    for component in ("opt", "codex-control", "releases"):
        current /= component
        if current.is_symlink():
            raise DeploymentError("layout_symlink")


def release_path(root: str | os.PathLike[str] | DeploymentRootAuthority, git_sha: str, *, allow_production_root: bool = False) -> Path:
    root_path = _layout_root(root, allow_production_root=allow_production_root)
    _assert_layout_chain(root_path)
    if not isinstance(git_sha, str) or _SHA.fullmatch(git_sha) is None:
        raise DeploymentError("release_sha_invalid")
    return root_path / "opt" / "codex-control" / "releases" / git_sha


def _regular_files(path: Path) -> list[Path]:
    """Return regular artifacts while allowing interpreter venv links only."""
    files: list[Path] = []
    for directory, directories, names in os.walk(path, followlinks=False):
        directory_path = Path(directory)
        for name in sorted(directories + names):
            item = directory_path / name
            relative = item.relative_to(path).as_posix()
            if item.is_symlink():
                if not relative.startswith(".venv/"):
                    raise DeploymentError("release_symlink")
                continue
            if item.is_file():
                files.append(item)
    return sorted(files)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        raise DeploymentError("artifact_unreadable") from None
    return digest.hexdigest()


def _assert_release_executable(release: Path) -> Path:
    executable = release / _EXECUTABLE_RELATIVE
    try:
        info = executable.lstat()
    except OSError:
        raise DeploymentError("executable_missing") from None
    if not stat.S_ISREG(info.st_mode) or not stat.S_IMODE(info.st_mode) & 0o111:
        raise DeploymentError("executable_invalid")
    return executable


def _manifest_for(
    release: Path,
    *,
    package_version: str,
    source_git_sha: str,
    source_tree_sha: str,
    python_requirement: str,
    service_unit: Path | None,
) -> ReleaseManifest:
    _assert_release_executable(release)
    digests = {
        str(item.relative_to(release)): _digest(item)
        for item in _regular_files(release) if item.name != "release-manifest.json"
    }
    unit_digest = _digest(service_unit) if service_unit is not None else None
    return ReleaseManifest(
        "codex-control", package_version, source_git_sha, source_tree_sha, python_requirement,
        SUPPORTED_CODEX_VERSION, SCHEMA_SHA256, 4, digests, unit_digest,
    )


def _git_output(repository: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise DeploymentError("git_source_invalid") from None
    value = result.stdout.decode("ascii", errors="strict").strip()
    if not value:
        raise DeploymentError("git_source_invalid")
    return value


def _git_source_authority(repository: Path, source_git_sha: str) -> str:
    if not repository.is_absolute() or not repository.is_dir() or repository.is_symlink():
        raise DeploymentError("git_source_invalid")
    if not _SHA.fullmatch(source_git_sha or ""):
        raise DeploymentError("release_sha_invalid")
    try:
        _git_output(repository, "rev-parse", "--git-dir")
        resolved = _git_output(repository, "rev-parse", "--verify", f"{source_git_sha}^{{commit}}")
        tree = _git_output(repository, "rev-parse", "--verify", f"{source_git_sha}^{{tree}}")
    except (UnicodeError, DeploymentError):
        raise DeploymentError("git_source_invalid") from None
    if resolved != source_git_sha or not _TREE_SHA.fullmatch(tree):
        raise DeploymentError("git_source_invalid")
    return tree


def _export_exact_git(repository: Path, source_git_sha: str, target: Path) -> str:
    tree = _git_source_authority(repository, source_git_sha)
    try:
        result = subprocess.run(
            ["git", "-C", str(repository), "archive", "--format=tar", source_git_sha],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=60,
        )
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                name = Path(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise DeploymentError("git_export_invalid")
                destination = target / name
                if member.isdir():
                    destination.mkdir(mode=0o755, parents=True, exist_ok=True)
                elif member.isfile():
                    destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise DeploymentError("git_export_invalid")
                    with destination.open("wb") as handle:
                        shutil.copyfileobj(stream, handle)
                    os.chmod(destination, member.mode & 0o777)
                else:
                    raise DeploymentError("git_export_symlink")
    except DeploymentError:
        raise
    except (OSError, tarfile.TarError, subprocess.SubprocessError):
        raise DeploymentError("git_export_failed") from None
    return tree


def _build_release_executable(stage: Path, *, python_executable: str | None = None) -> None:
    interpreter = python_executable or sys.executable
    environment = os.environ.copy()
    environment.update({"PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    venv = stage / ".venv"
    try:
        subprocess.run(
            [interpreter, "-m", "venv", "--system-site-packages", str(venv)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60,
            env=environment,
        )
        # A normal offline wheel install is preferred.  Some minimal host
        # Python images ship setuptools but not wheel; in that case the
        # dependency-free repository is packaged by a deterministic local
        # launcher, still inside the release venv and without an index.
        try:
            import wheel  # type: ignore[import-not-found]
        except ImportError:
            wheel_available = False
        else:
            wheel_available = wheel is not None
        if wheel_available:
            subprocess.run(
                [str(venv / "bin" / "python"), "-m", "pip", "install", "--no-index", "--no-deps",
                 "--no-build-isolation", str(stage)], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=120,
                env=environment, cwd=str(stage),
            )
        # Console-script shebangs generated inside a private staging path
        # would become stale after the atomic rename.  Replace it with a
        # stable, source-relative launcher in the release venv.  It remains a
        # real regular executable and never depends on the staging pathname.
        launcher = venv / "bin" / "codex-control"
        stable_interpreter = "/usr/bin/python" if Path("/usr/bin/python").is_file() else sys.executable
        launcher.write_text(
            "#!" + stable_interpreter + "\n"
            "import sys\n"
            "from pathlib import Path\n"
            "sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))\n"
            "from codex_control.__main__ import main\n"
            "raise SystemExit(main())\n",
            encoding="utf-8",
        )
        os.chmod(launcher, 0o755)
    except (OSError, subprocess.SubprocessError):
        raise DeploymentError("release_build_failed") from None
    _assert_release_executable(stage)


def _make_immutable(release: Path) -> None:
    try:
        for item in _regular_files(release):
            os.chmod(item, 0o555 if stat.S_IMODE(item.stat().st_mode) & 0o111 else 0o444)
        for directory, directories, _ in os.walk(release, followlinks=False):
            for name in directories:
                item = Path(directory) / name
                if not item.is_symlink():
                    os.chmod(item, 0o555)
    except OSError:
        raise DeploymentError("release_immutable_failed") from None


def _validate_release_artifacts(
    release: Path,
    *,
    current_db_schema: int | None = None,
    service_unit: Path | None = None,
    source_repository: Path | None = None,
    allow_private_stage: bool = False,
) -> ReleaseManifest:
    if not release.is_absolute() or release.is_symlink() or not release.is_dir():
        raise DeploymentError("release_invalid")
    manifest_path = release / "release-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise DeploymentError("manifest_missing")
    manifest = ReleaseManifest.from_bytes(manifest_path.read_bytes())
    if not allow_private_stage and release.name != manifest.source_git_sha:
        raise DeploymentError("manifest_sha_mismatch")
    if current_db_schema is not None and current_db_schema != manifest.supported_controller_db_schema:
        raise DeploymentError("schema_incompatible")
    if source_repository is not None:
        tree = _git_source_authority(Path(source_repository), manifest.source_git_sha)
        if tree != manifest.source_tree_sha:
            raise DeploymentError("source_tree_mismatch")
    _assert_release_executable(release)
    actual = {
        str(item.relative_to(release)): _digest(item)
        for item in _regular_files(release) if item.name != "release-manifest.json"
    }
    if actual != manifest.artifact_digests:
        raise DeploymentError("artifact_digest_mismatch")
    if service_unit is not None:
        if manifest.service_unit_sha256 != _digest(Path(service_unit)):
            raise DeploymentError("service_unit_mismatch")
    return manifest


def validate_release(
    path: str | os.PathLike[str], *, current_db_schema: int | None = None,
    service_unit: str | os.PathLike[str] | None = None,
    source_repository: str | os.PathLike[str] | None = None,
    allow_private_stage: bool = False,
) -> ReleaseManifest:
    return _validate_release_artifacts(
        Path(path), current_db_schema=current_db_schema,
        service_unit=None if service_unit is None else Path(service_unit),
        source_repository=None if source_repository is None else Path(source_repository),
        allow_private_stage=allow_private_stage,
    )


def stage_release(
    source: str | os.PathLike[str], *, root: str | os.PathLike[str] | DeploymentRootAuthority,
    git_sha: str, package_version: str = "0.1.0", python_requirement: str = ">=3.11",
    service_unit: str | os.PathLike[str] | None = None,
    allow_production_root: bool = False,
    python_executable: str | None = None,
    export_hook: Callable[[Path, str, Path], str] | None = None,
    build_hook: Callable[[Path], None] | None = None,
    manifest_hook: Callable[..., ReleaseManifest] | None = None,
    validation_hook: Callable[..., ReleaseManifest] | None = None,
) -> tuple[Path, str]:
    """Export an exact Git object, build privately, then atomically publish."""
    root_path = _layout_root(root, allow_production_root=allow_production_root)
    target = release_path(root_path, git_sha, allow_production_root=allow_production_root)
    repository = Path(source).resolve()
    if repository == root_path or root_path in repository.parents:
        raise DeploymentError("release_source_invalid")
    unit = Path(service_unit).resolve() if service_unit is not None else None
    if unit is not None and (not unit.is_file() or unit.is_symlink()):
        raise DeploymentError("service_unit_invalid")
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise DeploymentError("release_target_invalid")
        existing = validate_release(target, service_unit=unit, source_repository=repository)
        if existing.source_git_sha != git_sha:
            raise DeploymentError("release_already_present_invalid")
        return target, hashlib.sha256((target / "release-manifest.json").read_bytes()).hexdigest()

    stage = target.parent / f".stage-{git_sha}-{uuid.uuid4().hex}"
    try:
        stage.mkdir(mode=0o700)
        tree = export_hook(repository, git_sha, stage) if export_hook is not None else _export_exact_git(repository, git_sha, stage)
        if not _TREE_SHA.fullmatch(tree or ""):
            raise DeploymentError("source_tree_mismatch")
        if build_hook is not None:
            build_hook(stage)
        else:
            _build_release_executable(stage, python_executable=python_executable)
        _assert_release_executable(stage)
        manifest = (
            manifest_hook(stage, package_version, git_sha, tree, python_requirement, unit)
            if manifest_hook is not None else _manifest_for(
                stage, package_version=package_version, source_git_sha=git_sha,
                source_tree_sha=tree, python_requirement=python_requirement, service_unit=unit,
            )
        )
        (stage / "release-manifest.json").write_bytes(manifest.to_bytes())
        validator = validation_hook or (lambda path, **kwargs: validate_release(path, **kwargs))
        validator(stage, service_unit=unit, source_repository=repository, allow_private_stage=True)
        _make_immutable(stage)
        validator(stage, service_unit=unit, source_repository=repository, allow_private_stage=True)
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not target.is_dir():
                raise DeploymentError("release_target_invalid")
            shutil.rmtree(stage)
            existing = validate_release(target, service_unit=unit)
            return target, hashlib.sha256((target / "release-manifest.json").read_bytes()).hexdigest()
        os.replace(stage, target)
    except DeploymentError:
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    except (OSError, shutil.Error, TypeError, ValueError, Exception):
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise DeploymentError("release_stage_failed") from None
    data = (target / "release-manifest.json").read_bytes()
    return target, hashlib.sha256(data).hexdigest()


def stage_rehearsal_release(
    source: str | os.PathLike[str], *, root: str | os.PathLike[str], git_sha: str,
    package_version: str = "0.1.0", python_requirement: str = ">=3.11",
    service_unit: str | os.PathLike[str] | None = None,
) -> tuple[Path, str]:
    """Synthetic artifact helper for unit tests; never a production stage path."""
    root_path = _layout_root(root)
    target = release_path(root_path, git_sha)
    source_path = Path(source)
    if not source_path.is_dir() or not _SHA.fullmatch(git_sha or ""):
        raise DeploymentError("release_source_invalid")
    target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    if target.exists():
        validate_release(target)
        return target, hashlib.sha256((target / "release-manifest.json").read_bytes()).hexdigest()
    stage = target.parent / f".rehearsal-{git_sha}-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source_path, stage, symlinks=False, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        launcher = stage / _EXECUTABLE_RELATIVE
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.write_text("#!/bin/sh\nexit 0\n", encoding="ascii")
        os.chmod(launcher, 0o755)
        manifest = _manifest_for(
            stage, package_version=package_version, source_git_sha=git_sha,
            source_tree_sha=git_sha, python_requirement=python_requirement,
            service_unit=None if service_unit is None else Path(service_unit),
        )
        (stage / "release-manifest.json").write_bytes(manifest.to_bytes())
        _make_immutable(stage)
        validate_release(stage, allow_private_stage=True)
        os.replace(stage, target)
    except DeploymentError:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise
    except (OSError, shutil.Error):
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise DeploymentError("rehearsal_stage_failed") from None
    data = (target / "release-manifest.json").read_bytes()
    return target, hashlib.sha256(data).hexdigest()


def current_target(root: str | os.PathLike[str] | DeploymentRootAuthority, *, allow_production_root: bool = False) -> Path | None:
    root_path = _layout_root(root, allow_production_root=allow_production_root)
    _assert_layout_chain(root_path)
    current = root_path / "opt" / "codex-control" / "current"
    if current.exists() and not current.is_symlink():
        raise DeploymentError("current_target_invalid")
    if not current.is_symlink():
        return None
    target = (current.parent / os.readlink(current)).resolve()
    releases = (current.parent / "releases").resolve()
    if releases not in target.parents or target == releases or target.is_symlink() or not target.is_dir():
        raise DeploymentError("current_target_invalid")
    return target


def rehearsal_switch_current(root: str | os.PathLike[str], git_sha: str, *, current_db_schema: int) -> Path:
    """Caller-fact based primitive for offline rehearsal tests only."""
    root_path = _layout_root(root)
    target = release_path(root_path, git_sha)
    manifest = validate_release(target, current_db_schema=current_db_schema)
    if manifest.source_git_sha != git_sha:
        raise DeploymentError("manifest_sha_mismatch")
    current = root_path / "opt" / "codex-control" / "current"
    if current.exists() and not current.is_symlink():
        raise DeploymentError("current_target_invalid")
    current.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    prior = current_target(root_path)
    temporary_previous = current.parent / ".previous.next"
    temporary_current = current.parent / ".current.next"
    for path in (temporary_previous, temporary_current):
        if path.exists() or path.is_symlink():
            path.unlink()
    if prior is not None:
        if (current.parent / "previous").is_symlink() or (current.parent / "previous").exists() and not (current.parent / "previous").is_file():
            raise DeploymentError("previous_release_invalid")
        temporary_previous.write_text(prior.name + "\n", encoding="ascii")
    # Current is the linearization point.  A failure here leaves the old
    # previous record untouched and therefore cannot fabricate a rollback fact.
    os.symlink(os.path.relpath(target, current.parent), temporary_current)
    try:
        os.replace(temporary_current, current)
    except OSError:
        if temporary_current.is_symlink() or temporary_current.exists():
            temporary_current.unlink()
        if temporary_previous.exists():
            temporary_previous.unlink()
        raise DeploymentError("current_switch_failed") from None
    if prior is not None:
        try:
            os.replace(temporary_previous, current.parent / "previous")
        except OSError:
            if temporary_previous.exists():
                temporary_previous.unlink()
            # The new current still has the old previous record, which is
            # truthful and safer than fabricating a target.
            raise DeploymentError("previous_record_failed") from None
    return target


def _previous_sha(root: Path) -> str:
    try:
        value = (root / "opt" / "codex-control" / "previous").read_text(encoding="ascii").strip()
    except OSError:
        raise DeploymentError("previous_release_missing") from None
    if _SHA.fullmatch(value) is None:
        raise DeploymentError("previous_release_invalid")
    return value


def rehearsal_rollback(root: str | os.PathLike[str], *, current_db_schema: int) -> Path:
    root_path = _layout_root(root)
    target = release_path(root_path, _previous_sha(root_path))
    validate_release(target, current_db_schema=current_db_schema)
    return rehearsal_switch_current(root_path, target.name, current_db_schema=current_db_schema)


def _actual_db_schema(path: str | os.PathLike[str]) -> int:
    database = Path(path)
    if not database.is_absolute() or database.is_symlink():
        raise DeploymentError("database_authority_invalid")
    try:
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            value = connection.execute("PRAGMA user_version").fetchone()[0]
    except (OSError, sqlite3.Error, IndexError, TypeError):
        raise DeploymentError("database_unavailable") from None
    if type(value) is not int:
        raise DeploymentError("schema_incompatible")
    return value


def _production_authority(root_authority: DeploymentRootAuthority) -> Path:
    if not isinstance(root_authority, DeploymentRootAuthority):
        raise DeploymentError("production_root_authority_required")
    return _layout_root(root_authority)


def _run_staged_validate(executable: Path, config: Path, secrets: Path, *, test_only: bool) -> None:
    command = [str(executable), "validate", "--config", str(config), "--secrets", str(secrets)]
    if test_only:
        command.append("--test-only-authority")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=30, env=environment)
    except (OSError, subprocess.SubprocessError):
        raise DeploymentError("staged_validate_failed") from None


def _preflight_for_deployment(config_path: Path, secrets_path: Path, *, test_only: bool, installed_authority_probe: Any | None) -> tuple[Any, Any, Any]:
    from .service import preflight_production_authority
    try:
        return asyncio.run(preflight_production_authority(
            config_path, secrets_path, test_only=test_only,
            installed_authority_probe=installed_authority_probe,
        ))
    except DeploymentError:
        raise
    except Exception:
        raise DeploymentError("precheck_failed") from None


def install_upgrade(
    root_authority: DeploymentRootAuthority,
    source: str | os.PathLike[str], *, git_sha: str,
    config_path: str | os.PathLike[str], secrets_path: str | os.PathLike[str],
    service_unit: str | os.PathLike[str], health_check: Callable[[], bool] | None = None,
    installed_authority_probe: Any | None = None, test_only: bool = False,
    python_executable: str | None = None,
) -> dict[str, Any]:
    """Production-shaped transaction requiring all real authority inputs."""
    root = _production_authority(root_authority)
    config, _, _ = _preflight_for_deployment(Path(config_path), Path(secrets_path), test_only=test_only, installed_authority_probe=installed_authority_probe)
    schema = _actual_db_schema(config.controller_db_path)
    old = current_target(root_authority)
    if old is not None:
        validate_release(old, current_db_schema=schema, service_unit=service_unit)
    target, _ = stage_release(
        source, root=root_authority, git_sha=git_sha, service_unit=service_unit,
        allow_production_root=root == Path("/"), python_executable=python_executable,
    )
    manifest = validate_release(target, current_db_schema=schema, service_unit=service_unit, source_repository=source)
    if manifest.source_git_sha != git_sha:
        raise DeploymentError("manifest_sha_mismatch")
    _run_staged_validate(target / _EXECUTABLE_RELATIVE, Path(config_path), Path(secrets_path), test_only=test_only)
    state = DeploymentState.PRE_SWITCH_VALIDATED
    rehearsal_switch_current(root_authority, git_sha, current_db_schema=schema)
    state = DeploymentState.SWITCHED_AWAITING_SERVICE_HEALTH
    if health_check is None:
        return {"previous_sha": None if old is None else old.name, "requested_sha": git_sha, "healthy": None, "rolled_back": False, "state": state.value, "current_sha": current_target(root_authority).name}
    try:
        healthy = bool(health_check())
    except Exception:
        healthy = False
    if healthy:
        state = DeploymentState.HEALTH_CONFIRMED
        return {"previous_sha": None if old is None else old.name, "requested_sha": git_sha, "healthy": True, "rolled_back": False, "state": state.value, "current_sha": current_target(root_authority).name}
    state = DeploymentState.HEALTH_FAILED_ROLLBACK_REQUIRED
    if old is None:
        raise DeploymentError("health_gate_failed")
    production_rollback(root_authority, config_path=config_path, secrets_path=secrets_path, service_unit=service_unit, installed_authority_probe=installed_authority_probe, test_only=test_only)
    return {"previous_sha": old.name, "requested_sha": git_sha, "healthy": False, "rolled_back": True, "state": DeploymentState.ROLLED_BACK.value, "current_sha": current_target(root_authority).name}


def production_rollback(
    root_authority: DeploymentRootAuthority, *, config_path: str | os.PathLike[str],
    secrets_path: str | os.PathLike[str], service_unit: str | os.PathLike[str],
    installed_authority_probe: Any | None = None, test_only: bool = False,
) -> Path:
    root = _production_authority(root_authority)
    config, _, _ = _preflight_for_deployment(Path(config_path), Path(secrets_path), test_only=test_only, installed_authority_probe=installed_authority_probe)
    schema = _actual_db_schema(config.controller_db_path)
    previous = _previous_sha(root)
    target = release_path(root_authority, previous, allow_production_root=root == Path("/"))
    validate_release(target, current_db_schema=schema, service_unit=service_unit)
    return rehearsal_switch_current(root_authority, previous, current_db_schema=schema)


def rehearsal_install_upgrade(
    root: str | os.PathLike[str], source: str | os.PathLike[str], *, git_sha: str,
    current_db_schema: int, health_check: Callable[[], bool] | None = None,
    service_unit: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Explicit offline primitive; schema and health are injected facts."""
    root_path = _layout_root(root)
    old = current_target(root_path)
    if old is not None:
        validate_release(old, current_db_schema=current_db_schema, service_unit=service_unit)
    stage_rehearsal_release(source, root=root_path, git_sha=git_sha, service_unit=service_unit)
    rehearsal_switch_current(root_path, git_sha, current_db_schema=current_db_schema)
    if health_check is None:
        return {"previous_sha": None if old is None else old.name, "requested_sha": git_sha, "healthy": None, "rolled_back": False, "state": DeploymentState.SWITCHED_AWAITING_SERVICE_HEALTH.value, "current_sha": current_target(root_path).name}
    try:
        healthy = bool(health_check())
    except Exception:
        healthy = False
    if healthy:
        state = DeploymentState.HEALTH_CONFIRMED
        rolled_back = False
    elif old is None:
        raise DeploymentError("health_gate_failed")
    else:
        state = DeploymentState.ROLLED_BACK
        rehearsal_rollback(root_path, current_db_schema=current_db_schema)
        rolled_back = True
    return {"previous_sha": None if old is None else old.name, "requested_sha": git_sha, "healthy": healthy, "rolled_back": rolled_back, "state": state.value, "current_sha": current_target(root_path).name}


def verify_installation(
    root_authority: DeploymentRootAuthority, *, expected_sha: str | None = None,
    config_path: str | os.PathLike[str], secrets_path: str | os.PathLike[str],
    service_unit: str | os.PathLike[str], installed_authority_probe: Any | None = None,
    test_only: bool = False,
) -> dict[str, Any]:
    root = _production_authority(root_authority)
    config, _, installed_manifest = _preflight_for_deployment(Path(config_path), Path(secrets_path), test_only=test_only, installed_authority_probe=installed_authority_probe)
    current = current_target(root_authority)
    if current is None:
        raise DeploymentError("current_missing")
    manifest = validate_release(current, current_db_schema=_actual_db_schema(config.controller_db_path), service_unit=service_unit)
    if expected_sha is not None and manifest.source_git_sha != expected_sha:
        raise DeploymentError("current_sha_mismatch")
    unit_digest = _digest(Path(service_unit))
    if manifest.service_unit_sha256 != unit_digest:
        raise DeploymentError("service_unit_mismatch")
    config_info = Path(config_path).stat(follow_symlinks=False)
    secret_info = Path(secrets_path).stat(follow_symlinks=False)
    return {
        "installed_release_sha": manifest.source_git_sha,
        "installed_source_tree_sha": manifest.source_tree_sha,
        "manifest_sha256": hashlib.sha256((current / "release-manifest.json").read_bytes()).hexdigest(),
        "current_target": str(current),
        "config_authority": "ROOT_REGULAR_PRIVATE" if stat.S_ISREG(config_info.st_mode) and stat.S_IMODE(config_info.st_mode) & 0o022 == 0 else "INVALID",
        "secrets_authority": "ROOT_0600" if stat.S_ISREG(secret_info.st_mode) and stat.S_IMODE(secret_info.st_mode) == 0o600 else "INVALID",
        "controller_db_schema": _actual_db_schema(config.controller_db_path),
        "configured_profiles": tuple(profile.profile_id for profile in config.profiles),
        "codex_home_authority": tuple(profile.codex_home for profile in config.profiles),
        "codex_version_authority": installed_manifest.codex_cli_version,
        "codex_capability_schema_sha256": installed_manifest.schema_sha256,
        "service_unit_sha256": unit_digest,
        "release_executable": str(current / _EXECUTABLE_RELATIVE),
    }


__all__ = [
    "DeploymentError", "DeploymentRootAuthority", "DeploymentState", "ReleaseManifest",
    "current_target", "install_upgrade", "production_rollback", "rehearsal_install_upgrade",
    "rehearsal_rollback", "rehearsal_switch_current", "release_path", "stage_release",
    "stage_rehearsal_release", "validate_release", "verify_installation",
]
