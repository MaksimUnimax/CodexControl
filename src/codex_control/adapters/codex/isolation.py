"""Secret-free path, ownership, and isolated-state-root authority for C3."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from ...domain import CodexProfile

STATE_ROOT_MARKER = ".codexcontrol-state-root-v1"
STATE_ROOT_FORMAT = "codexcontrol-state-root-v1"
MAX_MARKER_BYTES = 512


class IsolationError(Exception):
    """Finite, path-free filesystem authority failure."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


def canonical_path(value: str | os.PathLike[str]) -> str:
    if not isinstance(value, (str, os.PathLike)):
        raise IsolationError("path_invalid")
    text = os.fspath(value)
    if not text or "\x00" in text or not os.path.isabs(text):
        raise IsolationError("path_invalid")
    return os.path.normpath(os.path.abspath(text))


def paths_overlap(left: str, right: str) -> bool:
    try:
        return os.path.commonpath((left, right)) in (left, right)
    except ValueError:
        return False


def _mode_is_private(mode: int, expected: int) -> bool:
    return stat.S_IMODE(mode) == expected


def _is_root_owned(st: os.stat_result) -> bool:
    return st.st_uid == 0


def _is_persistent_mode(mode: int) -> bool:
    """Persistent homes may be readable, but never group/world writable."""
    return not (mode & (stat.S_IWGRP | stat.S_IWOTH))


def _is_nested_mode(mode: int) -> bool:
    """The exact 0700 containment boundary protects nested Codex entries."""
    return not (mode & (stat.S_IWGRP | stat.S_IWOTH))


def _walk_existing_components(path: str) -> None:
    path_object = Path(path)
    current = Path(path_object.anchor or os.sep)
    parts = path_object.parts
    for part in parts[1:]:
        current /= part
        try:
            st = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError:
            raise IsolationError("path_inspection_failed") from None
        if stat.S_ISLNK(st.st_mode):
            raise IsolationError("symlink_path")


def _metadata_path(path: str, *, must_exist: bool, directory: bool = False) -> os.stat_result | None:
    _walk_existing_components(path)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        if not must_exist:
            return None
        raise IsolationError("path_missing") from None
    except OSError:
        raise IsolationError("path_inspection_failed") from None
    if stat.S_ISLNK(st.st_mode):
        raise IsolationError("symlink_path")
    if directory and not stat.S_ISDIR(st.st_mode):
        raise IsolationError("not_directory")
    return st


@dataclass(frozen=True)
class IsolationPathAuthority:
    """Explicit protected-path set; no repository/cwd discovery is performed."""

    profiles: tuple[CodexProfile, ...]
    controller_db_path: str | None = None
    controller_db_root: str | None = None
    repository_root: str | None = None
    protected_roots: tuple[str, ...] = ()
    require_global_roots: bool = True

    def __post_init__(self) -> None:
        homes: list[str] = []
        roots: list[str] = []
        for profile in self.profiles:
            if not isinstance(profile.isolated_state_root, str) or not profile.isolated_state_root:
                raise IsolationError("isolated_state_root_required")
            homes.append(canonical_path(profile.codex_home))
            roots.append(canonical_path(profile.isolated_state_root))
        if len(homes) != len(set(homes)):
            raise IsolationError("duplicate_codex_home")
        if len(roots) != len(set(roots)):
            raise IsolationError("duplicate_isolated_state_root")
        all_paths = homes + roots
        if any(paths_overlap(a, b) for index, a in enumerate(all_paths) for b in all_paths[index + 1:]):
            raise IsolationError("profile_path_overlap")
        protected = tuple(
            canonical_path(path) for path in (
                self.controller_db_path, self.controller_db_root, self.repository_root,
            ) if path is not None
        ) + tuple(canonical_path(path) for path in self.protected_roots)
        if self.require_global_roots and not protected:
            raise IsolationError("protected_roots_required")
        if len(protected) != len(set(protected)):
            raise IsolationError("duplicate_protected_path")
        if any(paths_overlap(path, protected_path) for path in all_paths for protected_path in protected):
            raise IsolationError("protected_path_overlap")

    @property
    def protected_paths(self) -> tuple[str, ...]:
        return tuple(
            canonical_path(path) for path in (
                self.controller_db_path, self.controller_db_root, self.repository_root,
            ) if path is not None
        ) + tuple(canonical_path(path) for path in self.protected_roots)

    def profile(self, profile_id: str) -> CodexProfile:
        for profile in self.profiles:
            if profile.profile_id == profile_id:
                return profile
        raise IsolationError("unknown_profile")

    def _bound_profile(self, profile: CodexProfile) -> CodexProfile:
        configured = self.profile(profile.profile_id)
        try:
            same_paths = (
                canonical_path(profile.codex_home) == canonical_path(configured.codex_home)
                and canonical_path(profile.isolated_state_root) == canonical_path(configured.isolated_state_root)
            )
        except IsolationError:
            raise IsolationError("profile_binding_mismatch") from None
        if not same_paths:
            raise IsolationError("profile_binding_mismatch")
        return configured

    def validate_profile_paths(self, profile: CodexProfile, *, state_root_may_be_missing: bool = False) -> tuple[str, str]:
        configured = self._bound_profile(profile)
        home = canonical_path(configured.codex_home)
        state_root = canonical_path(configured.isolated_state_root or "")
        if any(paths_overlap(path, protected) for path in (home, state_root) for protected in self.protected_paths):
            raise IsolationError("protected_path_overlap")
        if paths_overlap(home, state_root):
            raise IsolationError("profile_home_state_overlap")
        home_stat = _metadata_path(home, must_exist=True, directory=True)
        assert home_stat is not None
        if not _is_root_owned(home_stat) or not _is_persistent_mode(home_stat.st_mode):
            raise IsolationError("persistent_home_ownership")
        state_stat = _metadata_path(state_root, must_exist=not state_root_may_be_missing, directory=True)
        if state_stat is not None and (not _is_root_owned(state_stat) or not _is_persistent_mode(state_stat.st_mode)):
            raise IsolationError("state_root_ownership")
        return home, state_root

    def validate_all(self, *, state_root_may_be_missing: bool = False) -> None:
        for profile in self.profiles:
            self.validate_profile_paths(profile, state_root_may_be_missing=state_root_may_be_missing)


def _safe_entry_stat(name: str, parent_fd: int) -> os.stat_result:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError:
        raise IsolationError("state_entry_inspection_failed") from None


def _validate_tree(fd: int) -> None:
    try:
        names = os.listdir(fd)
    except OSError:
        raise IsolationError("state_entry_inspection_failed") from None
    for name in names:
        st = _safe_entry_stat(name, fd)
        if stat.S_ISLNK(st.st_mode):
            raise IsolationError("state_symlink_entry")
        if not _is_root_owned(st) or not _is_nested_mode(st.st_mode):
            raise IsolationError("state_entry_ownership")
        if stat.S_ISDIR(st.st_mode):
            try:
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except OSError:
                raise IsolationError("state_entry_open_failed") from None
            try:
                _validate_tree(child)
            finally:
                os.close(child)
        elif not stat.S_ISREG(st.st_mode):
            raise IsolationError("state_special_entry")


def _expected_marker(profile_id: str) -> bytes:
    if not isinstance(profile_id, str) or not profile_id or any(char in profile_id for char in "\x00\r\n"):
        raise IsolationError("profile_id_invalid")
    value = f"format={STATE_ROOT_FORMAT}\nprofile_id={profile_id}\n".encode("utf-8")
    if len(value) > MAX_MARKER_BYTES:
        raise IsolationError("marker_invalid")
    return value


class IsolatedStateRoot:
    """Provision/validate/recreate one profile-owned root without recursive pathname deletion."""

    def __init__(self, authority: IsolationPathAuthority) -> None:
        self.authority = authority

    def _open_root(self, profile: CodexProfile) -> tuple[int, str, str]:
        home, root = self.authority.validate_profile_paths(profile)
        try:
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise IsolationError("state_root_open_failed") from None
        try:
            st = os.fstat(fd)
            if st.st_uid != 0 or not _is_private_mode(st.st_mode, 0o700):
                raise IsolationError("state_root_ownership")
            self._validate_layout(fd, profile.profile_id)
        except Exception:
            os.close(fd)
            raise
        return fd, home, root

    def _validate_layout(self, fd: int, profile_id: str) -> None:
        expected = _expected_marker(profile_id)
        try:
            names = set(os.listdir(fd))
        except OSError:
            raise IsolationError("state_root_inspection_failed") from None
        if names != {STATE_ROOT_MARKER, "sqlite", "logs"}:
            raise IsolationError("unexpected_state_entry")
        marker_stat = _safe_entry_stat(STATE_ROOT_MARKER, fd)
        if not stat.S_ISREG(marker_stat.st_mode) or marker_stat.st_uid != 0 or not _is_private_mode(marker_stat.st_mode, 0o600):
            raise IsolationError("marker_invalid")
        try:
            marker_fd = os.open(STATE_ROOT_MARKER, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                content = os.read(marker_fd, MAX_MARKER_BYTES + 1)
            finally:
                os.close(marker_fd)
        except OSError:
            raise IsolationError("marker_invalid") from None
        if content != expected:
            raise IsolationError("marker_mismatch")
        for directory in ("sqlite", "logs"):
            entry = _safe_entry_stat(directory, fd)
            if not stat.S_ISDIR(entry.st_mode) or entry.st_uid != 0 or not _is_private_mode(entry.st_mode, 0o700):
                raise IsolationError("state_directory_invalid")
            child = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                _validate_tree(child)
            finally:
                os.close(child)

    def validate(self, profile: CodexProfile) -> None:
        fd, _, _ = self._open_root(profile)
        os.close(fd)

    def provision(self, profile: CodexProfile) -> None:
        _, root = self.authority.validate_profile_paths(profile, state_root_may_be_missing=True)
        parent = os.path.dirname(root)
        parent_stat = _metadata_path(parent, must_exist=True, directory=True)
        assert parent_stat is not None
        if not _is_root_owned(parent_stat) or not _is_persistent_mode(parent_stat.st_mode):
            raise IsolationError("state_parent_ownership")
        try:
            os.mkdir(root, 0o700)
        except FileExistsError:
            self.validate(profile)
            return
        except OSError:
            raise IsolationError("state_root_create_failed") from None
        try:
            os.chmod(root, 0o700)
            for directory in ("sqlite", "logs"):
                os.mkdir(os.path.join(root, directory), 0o700)
                os.chmod(os.path.join(root, directory), 0o700)
            marker_path = os.path.join(root, STATE_ROOT_MARKER)
            descriptor = os.open(marker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                os.write(descriptor, _expected_marker(profile.profile_id))
            finally:
                os.close(descriptor)
            self.validate(profile)
        except Exception:
            # Only this newly created, still-unvalidated root is touched.  Do not
            # recursively remove it: leave a failed root for explicit inspection.
            raise

    def recreate(self, profile: CodexProfile, *, reservation: Any = None) -> None:
        """Reject raw reservation tokens; the runtime manager owns recreation."""
        raise IsolationError("manager_recreation_required")

    def _recreate_bound(self, profile: CodexProfile) -> None:
        configured = self.authority._bound_profile(profile)
        fd, _, root = self._open_root(configured)
        try:
            initial = os.fstat(fd)
            _clear_directory(fd)
            current = os.fstat(fd)
            if (initial.st_dev, initial.st_ino) != (current.st_dev, current.st_ino):
                raise IsolationError("state_root_replaced")
            for directory in ("sqlite", "logs"):
                os.mkdir(directory, 0o700, dir_fd=fd)
            marker_fd = os.open(STATE_ROOT_MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                os.write(marker_fd, _expected_marker(configured.profile_id))
            finally:
                os.close(marker_fd)
        except IsolationError:
            raise
        except OSError:
            raise IsolationError("state_root_recreate_failed") from None
        finally:
            os.close(fd)
        self.validate(configured)


def _clear_directory(fd: int) -> None:
    try:
        names = os.listdir(fd)
    except OSError:
        raise IsolationError("state_root_mutation_failed") from None
    for name in names:
        st = _safe_entry_stat(name, fd)
        if stat.S_ISLNK(st.st_mode):
            raise IsolationError("state_symlink_entry")
        if not _is_root_owned(st) or not _is_nested_mode(st.st_mode):
            raise IsolationError("state_entry_ownership")
        if stat.S_ISDIR(st.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                _clear_directory(child)
            finally:
                os.close(child)
            try:
                os.rmdir(name, dir_fd=fd)
            except OSError:
                raise IsolationError("state_root_mutation_failed") from None
        elif stat.S_ISREG(st.st_mode):
            try:
                os.unlink(name, dir_fd=fd)
            except OSError:
                raise IsolationError("state_root_mutation_failed") from None
        else:
            raise IsolationError("state_special_entry")


def _is_private_mode(mode: int, expected: int) -> bool:
    return stat.S_IMODE(mode) == expected
