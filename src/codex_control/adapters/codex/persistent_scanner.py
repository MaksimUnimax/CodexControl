"""Bounded, content-silent residual scanning for the persistent profile home."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass

from codex_control.domain import CodexProfile

from .isolation import (
    IsolationError,
    IsolationPathAuthority,
    _open_directory_chain,
    _safe_entry_stat,
)

DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
DEFAULT_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, repr=False)
class PersistentProfileScanResult:
    files_scanned: int
    bytes_scanned: int
    match_count: int
    scan_errors: int
    limit_exceeded: bool = False

    @property
    def passed(self) -> bool:
        return self.scan_errors == 0 and not self.limit_exceeded and self.match_count == 0

    def __repr__(self) -> str:
        return (
            "PersistentProfileScanResult("
            f"files_scanned={self.files_scanned!r}, bytes_scanned={self.bytes_scanned!r}, "
            f"match_count={self.match_count!r}, scan_errors={self.scan_errors!r}, "
            f"limit_exceeded={self.limit_exceeded!r})"
        )


class PersistentProfileResidualScanner:
    """Scan only ``sessions/**`` and optional ``history.jsonl`` by descriptors."""

    def __init__(
        self,
        authority: IsolationPathAuthority,
        *,
        max_files: int = DEFAULT_MAX_FILES,
        max_bytes: int = DEFAULT_MAX_BYTES,
        chunk_bytes: int = DEFAULT_CHUNK_BYTES,
    ) -> None:
        if not isinstance(authority, IsolationPathAuthority):
            raise ValueError("authority_invalid")
        if any(type(value) is not int or value <= 0 for value in (max_files, max_bytes, chunk_bytes)):
            raise ValueError("scan_limit_invalid")
        self._authority = authority
        self._max_files = max_files
        self._max_bytes = max_bytes
        self._chunk_bytes = chunk_bytes

    def scan(self, profile: CodexProfile, thread_id: str) -> PersistentProfileScanResult:
        if not isinstance(profile, CodexProfile) or type(thread_id) is not str or not thread_id:
            raise ValueError("scan_argument_invalid")
        needle = thread_id.encode("utf-8")
        result = _ScanAccumulator(needle, self._max_files, self._max_bytes, self._chunk_bytes)
        home_fd: int | None = None
        try:
            self._authority.validate_runtime_authority()
            configured = self._authority._bound_profile(profile)
            home, _ = self._authority._profile_paths(configured)
            home_fd = _open_directory_chain(home)
            home_stat = os.fstat(home_fd)
            if home_stat.st_uid != 0 or stat.S_IMODE(home_stat.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                result.error()
                return result.result()
            self._scan_sessions(home_fd, result)
            self._scan_history(home_fd, result)
        except (IsolationError, OSError, ValueError):
            result.error()
        finally:
            if home_fd is not None:
                try:
                    os.close(home_fd)
                except OSError:
                    result.error()
        return result.result()

    def _scan_sessions(self, home_fd: int, result: "_ScanAccumulator") -> None:
        try:
            entry = _safe_entry_stat("sessions", home_fd)
            if (
                not stat.S_ISDIR(entry.st_mode)
                or entry.st_uid != 0
                or stat.S_IMODE(entry.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                result.error()
                return
            sessions_fd = os.open(
                "sessions",
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=home_fd,
            )
        except IsolationError:
            try:
                os.stat("sessions", dir_fd=home_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            except OSError:
                result.error()
                return
            result.error()
            return
        except OSError:
            result.error()
            return
        try:
            self._validate_directory(sessions_fd, entry)
            self._scan_directory(sessions_fd, "sessions", result)
        finally:
            try:
                os.close(sessions_fd)
            except OSError:
                result.error()

    def _scan_history(self, home_fd: int, result: "_ScanAccumulator") -> None:
        try:
            entry = _safe_entry_stat("history.jsonl", home_fd)
        except IsolationError:
            # A missing optional history file is an accepted empty scope.
            try:
                os.stat("history.jsonl", dir_fd=home_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            except OSError:
                result.error()
                return
            result.error()
            return
        if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
            result.error()
            return
        if entry.st_uid != 0 or stat.S_IMODE(entry.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
            result.error()
            return
        result.path_match("history.jsonl")
        self._scan_file(home_fd, "history.jsonl", "history.jsonl", result, entry)

    @staticmethod
    def _validate_directory(fd: int, expected: os.stat_result | None = None) -> None:
        value = os.fstat(fd)
        if not stat.S_ISDIR(value.st_mode) or value.st_uid != 0:
            raise OSError("directory_unsafe")
        if stat.S_IMODE(value.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
            raise OSError("directory_writable")
        if expected is not None and (value.st_dev, value.st_ino) != (expected.st_dev, expected.st_ino):
            raise OSError("directory_replaced")

    def _scan_directory(self, fd: int, relative: str, result: "_ScanAccumulator") -> None:
        try:
            names = os.listdir(fd)
        except OSError:
            result.error()
            return
        for name in sorted(names):
            child_relative = f"{relative}/{name}"
            result.path_match(child_relative)
            try:
                entry = _safe_entry_stat(name, fd)
            except IsolationError:
                result.error()
                continue
            if stat.S_ISLNK(entry.st_mode):
                result.error()
                continue
            if entry.st_uid != 0 or stat.S_IMODE(entry.st_mode) & (stat.S_IWGRP | stat.S_IWOTH):
                result.error()
                continue
            if stat.S_ISDIR(entry.st_mode):
                try:
                    child_fd = os.open(
                        name,
                        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                        dir_fd=fd,
                    )
                except OSError:
                    result.error()
                    continue
                try:
                    self._validate_directory(child_fd, entry)
                    self._scan_directory(child_fd, child_relative, result)
                finally:
                    try:
                        os.close(child_fd)
                    except OSError:
                        result.error()
            elif stat.S_ISREG(entry.st_mode):
                self._scan_file(fd, name, child_relative, result, entry)
            else:
                result.error()

    def _scan_file(self, parent_fd: int, name: str, relative: str, result: "_ScanAccumulator", entry: os.stat_result) -> None:
        if not result.start_file():
            return
        try:
            fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                dir_fd=parent_fd,
            )
        except OSError:
            result.error()
            return
        try:
            opened = os.fstat(fd)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_uid != 0
                or stat.S_IMODE(opened.st_mode) & (stat.S_IWGRP | stat.S_IWOTH)
                or (opened.st_dev, opened.st_ino) != (entry.st_dev, entry.st_ino)
            ):
                result.error()
                return
            self._read_file(fd, relative, result)
        finally:
            try:
                os.close(fd)
            except OSError:
                result.error()

    def _read_file(self, fd: int, relative: str, result: "_ScanAccumulator") -> None:
        tail = b""
        try:
            while True:
                chunk = os.read(fd, self._chunk_bytes)
                if not chunk:
                    return
                if not result.add_bytes(len(chunk)):
                    return
                combined = tail + chunk
                result.content_matches(combined)
                tail = combined[-(len(result.needle) - 1):] if len(result.needle) > 1 else b""
        except OSError:
            result.error()


class _ScanAccumulator:
    def __init__(self, needle: bytes, max_files: int, max_bytes: int, chunk_bytes: int) -> None:
        self.needle = needle
        self.max_files = max_files
        self.max_bytes = max_bytes
        self.chunk_bytes = chunk_bytes
        self.files_scanned = 0
        self.bytes_scanned = 0
        self.match_count = 0
        self.scan_errors = 0
        self.limit_exceeded = False

    def path_match(self, relative: str) -> None:
        self.match_count += relative.encode("utf-8").count(self.needle)

    def start_file(self) -> bool:
        if self.files_scanned >= self.max_files:
            self.limit_exceeded = True
            self.scan_errors += 1
            return False
        self.files_scanned += 1
        return True

    def add_bytes(self, count: int) -> bool:
        if self.bytes_scanned + count > self.max_bytes:
            self.limit_exceeded = True
            self.scan_errors += 1
            self.bytes_scanned = self.max_bytes
            return False
        self.bytes_scanned += count
        return True

    def content_matches(self, data: bytes) -> None:
        self.match_count += data.count(self.needle)

    def error(self) -> None:
        self.scan_errors += 1

    def result(self) -> PersistentProfileScanResult:
        return PersistentProfileScanResult(
            self.files_scanned, self.bytes_scanned, self.match_count,
            self.scan_errors, self.limit_exceeded,
        )


__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_FILES",
    "PersistentProfileResidualScanner",
    "PersistentProfileScanResult",
]
