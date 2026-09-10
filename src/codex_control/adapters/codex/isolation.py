"""Secret-free path, ownership, and isolated-state-root authority for C3."""
from __future__ import annotations

import os
import stat
from dataclasses import dataclass
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


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )


def _open_directory_chain(path: str) -> int:
    """Open an absolute directory one component at a time from the root fd."""
    path = canonical_path(path)
    parent_fd: int | None = None
    try:
        try:
            parent_fd = os.open(os.sep, _directory_open_flags())
        except OSError:
            raise IsolationError("path_open_failed") from None
        try:
            if not stat.S_ISDIR(os.fstat(parent_fd).st_mode):
                raise IsolationError("path_not_directory")
        except IsolationError:
            raise
        except OSError:
            raise IsolationError("path_inspection_failed") from None
        for component in path.split(os.sep)[1:]:
            if not component:
                continue
            try:
                child_fd = os.open(component, _directory_open_flags(), dir_fd=parent_fd)
            except FileNotFoundError:
                raise IsolationError("path_missing") from None
            except OSError:
                raise IsolationError("path_open_failed") from None
            try:
                try:
                    child_stat = os.fstat(child_fd)
                except OSError:
                    raise IsolationError("path_inspection_failed") from None
                if not stat.S_ISDIR(child_stat.st_mode):
                    raise IsolationError("path_not_directory")
            except Exception:
                os.close(child_fd)
                raise
            os.close(parent_fd)
            parent_fd = child_fd
        assert parent_fd is not None
        return parent_fd
    except Exception:
        if parent_fd is not None:
            os.close(parent_fd)
        raise


def _entry_matches_fd(parent_fd: int, name: str, expected_fd: int, category: str) -> None:
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        expected = os.fstat(expected_fd)
    except OSError:
        raise IsolationError(category) from None
    if (entry.st_dev, entry.st_ino) != (expected.st_dev, expected.st_ino):
        raise IsolationError(category)


def _chain_matches_fd(path: str, expected_fd: int, category: str) -> None:
    current_fd = _open_directory_chain(path)
    try:
        try:
            current = os.fstat(current_fd)
            expected = os.fstat(expected_fd)
        except OSError:
            raise IsolationError(category) from None
        if (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
            raise IsolationError(category)
    finally:
        os.close(current_fd)


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

    def _profile_paths(self, profile: CodexProfile, *, state_root_may_be_missing: bool = False) -> tuple[str, str]:
        configured = self._bound_profile(profile)
        home = canonical_path(configured.codex_home)
        state_root = canonical_path(configured.isolated_state_root or "")
        if any(paths_overlap(path, protected) for path in (home, state_root) for protected in self.protected_paths):
            raise IsolationError("protected_path_overlap")
        if paths_overlap(home, state_root):
            raise IsolationError("profile_home_state_overlap")
        return home, state_root

    def validate_profile_paths(self, profile: CodexProfile, *, state_root_may_be_missing: bool = False) -> tuple[str, str]:
        home, state_root = self._profile_paths(profile, state_root_may_be_missing=state_root_may_be_missing)
        home_fd = _open_directory_chain(home)
        try:
            home_stat = os.fstat(home_fd)
            if not _is_root_owned(home_stat) or not _is_persistent_mode(home_stat.st_mode):
                raise IsolationError("persistent_home_ownership")
        except IsolationError:
            raise
        except OSError:
            raise IsolationError("path_inspection_failed") from None
        finally:
            os.close(home_fd)
        try:
            state_fd = _open_directory_chain(state_root)
        except IsolationError as error:
            if state_root_may_be_missing and error.category == "path_missing":
                return home, state_root
            raise
        try:
            state_stat = os.fstat(state_fd)
            if not _is_root_owned(state_stat) or not _is_persistent_mode(state_stat.st_mode):
                raise IsolationError("state_root_ownership")
        except IsolationError:
            raise
        except OSError:
            raise IsolationError("path_inspection_failed") from None
        finally:
            os.close(state_fd)
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
                child = os.open(name, _directory_open_flags(), dir_fd=fd)
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

    def _open_root_with_parent(self, profile: CodexProfile) -> tuple[int, int, str, str, str]:
        configured = self.authority._bound_profile(profile)
        home, root = self.authority._profile_paths(configured)
        home_fd = _open_directory_chain(home)
        try:
            home_stat = os.fstat(home_fd)
            if not _is_root_owned(home_stat) or not _is_persistent_mode(home_stat.st_mode):
                raise IsolationError("persistent_home_ownership")
        finally:
            os.close(home_fd)

        parent = os.path.dirname(root)
        leaf = os.path.basename(root)
        if not leaf:
            raise IsolationError("state_root_open_failed")
        parent_fd = _open_directory_chain(parent)
        try:
            parent_stat = os.fstat(parent_fd)
            if not _is_root_owned(parent_stat) or not _is_persistent_mode(parent_stat.st_mode):
                raise IsolationError("state_parent_ownership")
            try:
                root_fd = os.open(leaf, _directory_open_flags(), dir_fd=parent_fd)
            except OSError:
                raise IsolationError("state_root_open_failed") from None
            try:
                root_stat = os.fstat(root_fd)
                if not stat.S_ISDIR(root_stat.st_mode):
                    raise IsolationError("state_root_open_failed")
                _chain_matches_fd(parent, parent_fd, "state_root_replaced")
                _entry_matches_fd(parent_fd, leaf, root_fd, "state_root_replaced")
                if root_stat.st_uid != 0 or not _is_private_mode(root_stat.st_mode, 0o700):
                    raise IsolationError("state_root_ownership")
                self._validate_layout(root_fd, configured.profile_id)
            except Exception:
                os.close(root_fd)
                raise
            return root_fd, parent_fd, home, root, leaf
        except Exception:
            os.close(parent_fd)
            raise

    def _open_root(self, profile: CodexProfile) -> tuple[int, str, str]:
        root_fd, parent_fd, home, root, _ = self._open_root_with_parent(profile)
        os.close(parent_fd)
        return root_fd, home, root

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
            marker_fd = os.open(
                STATE_ROOT_MARKER,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=fd,
            )
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
            child = os.open(directory, _directory_open_flags(), dir_fd=fd)
            try:
                _validate_tree(child)
            finally:
                os.close(child)

    def validate(self, profile: CodexProfile) -> None:
        fd, _, _ = self._open_root(profile)
        os.close(fd)

    def provision(self, profile: CodexProfile) -> None:
        configured = self.authority._bound_profile(profile)
        home, root = self.authority._profile_paths(configured, state_root_may_be_missing=True)
        home_fd = _open_directory_chain(home)
        try:
            home_stat = os.fstat(home_fd)
            if not _is_root_owned(home_stat) or not _is_persistent_mode(home_stat.st_mode):
                raise IsolationError("persistent_home_ownership")
        finally:
            os.close(home_fd)
        parent = os.path.dirname(root)
        leaf = os.path.basename(root)
        if not leaf:
            raise IsolationError("state_root_create_failed")
        parent_fd = _open_directory_chain(parent)
        try:
            parent_stat = os.fstat(parent_fd)
            if not _is_root_owned(parent_stat) or not _is_persistent_mode(parent_stat.st_mode):
                raise IsolationError("state_parent_ownership")
            _chain_matches_fd(parent, parent_fd, "state_root_replaced")
            created = False
            try:
                os.mkdir(leaf, 0o700, dir_fd=parent_fd)
                created = True
            except FileExistsError:
                pass
            except OSError:
                raise IsolationError("state_root_create_failed") from None
            try:
                root_fd = os.open(leaf, _directory_open_flags(), dir_fd=parent_fd)
            except OSError:
                raise IsolationError("state_root_open_failed") from None
            try:
                root_stat = os.fstat(root_fd)
                _entry_matches_fd(parent_fd, leaf, root_fd, "state_root_replaced")
                if root_stat.st_uid != 0 or not _is_private_mode(root_stat.st_mode, 0o700):
                    raise IsolationError("state_root_ownership")
                if not created:
                    self._validate_layout(root_fd, configured.profile_id)
                    return
                # The descriptor and its parent entry were opened from the same
                # parent descriptor. Recheck immediately before the first write.
                _entry_matches_fd(parent_fd, leaf, root_fd, "state_root_replaced")
                for directory in ("sqlite", "logs"):
                    os.mkdir(directory, 0o700, dir_fd=root_fd)
                    child_fd = os.open(directory, _directory_open_flags(), dir_fd=root_fd)
                    try:
                        child_stat = os.fstat(child_fd)
                        if child_stat.st_uid != 0 or not _is_private_mode(child_stat.st_mode, 0o700):
                            raise IsolationError("state_directory_invalid")
                    finally:
                        os.close(child_fd)
                marker_fd = os.open(
                    STATE_ROOT_MARKER,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                    0o600,
                    dir_fd=root_fd,
                )
                try:
                    os.write(marker_fd, _expected_marker(configured.profile_id))
                finally:
                    os.close(marker_fd)
                _entry_matches_fd(parent_fd, leaf, root_fd, "state_root_replaced")
                self._validate_layout(root_fd, configured.profile_id)
            finally:
                os.close(root_fd)
        except OSError:
            raise IsolationError("state_root_create_failed") from None
        finally:
            os.close(parent_fd)

    def recreate(self, profile: CodexProfile, *, reservation: Any = None) -> None:
        """Reject raw reservation tokens; the runtime manager owns recreation."""
        raise IsolationError("manager_recreation_required")

    def _recreate_bound(self, profile: CodexProfile) -> None:
        configured = self.authority._bound_profile(profile)
        fd, parent_fd, _, root, leaf = self._open_root_with_parent(configured)
        try:
            initial = os.fstat(fd)
            _chain_matches_fd(os.path.dirname(root), parent_fd, "state_root_replaced")
            _entry_matches_fd(parent_fd, leaf, fd, "state_root_replaced")
            _clear_directory(fd)
            current = os.fstat(fd)
            if (initial.st_dev, initial.st_ino) != (current.st_dev, current.st_ino):
                raise IsolationError("state_root_replaced")
            _entry_matches_fd(parent_fd, leaf, fd, "state_root_replaced")
            for directory in ("sqlite", "logs"):
                _entry_matches_fd(parent_fd, leaf, fd, "state_root_replaced")
                os.mkdir(directory, 0o700, dir_fd=fd)
            _entry_matches_fd(parent_fd, leaf, fd, "state_root_replaced")
            marker_fd = os.open(
                STATE_ROOT_MARKER,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=fd,
            )
            try:
                os.write(marker_fd, _expected_marker(configured.profile_id))
            finally:
                os.close(marker_fd)
            current = os.fstat(fd)
            if (initial.st_dev, initial.st_ino) != (current.st_dev, current.st_ino):
                raise IsolationError("state_root_replaced")
            _entry_matches_fd(parent_fd, leaf, fd, "state_root_replaced")
            self._validate_layout(fd, configured.profile_id)
        except IsolationError:
            raise
        except OSError:
            raise IsolationError("state_root_recreate_failed") from None
        finally:
            os.close(fd)
            os.close(parent_fd)


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
            child = os.open(name, _directory_open_flags(), dir_fd=fd)
            try:
                _clear_directory(child)
                _entry_matches_fd(fd, name, child, "state_root_mutation_failed")
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
