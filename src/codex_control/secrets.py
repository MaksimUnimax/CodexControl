"""Root-only, non-shell secrets authority for the production process."""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path


class SecretsError(ValueError):
    """Finite secret-loader category; values and source text never escape."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


@dataclass(frozen=True, repr=False)
class SecretAuthority:
    telegram_bot_token: str

    def __post_init__(self) -> None:
        if not isinstance(self.telegram_bot_token, str) or not self.telegram_bot_token:
            raise SecretsError("token_missing")
        if "\x00" in self.telegram_bot_token or "\n" in self.telegram_bot_token or "\r" in self.telegram_bot_token:
            raise SecretsError("token_invalid")

    def __repr__(self) -> str:
        return "SecretAuthority(telegram_bot_token='[REDACTED]')"


_ASSIGNMENT = re.compile(r"\A([A-Z][A-Z0-9_]*)=([^\x00\r\n]*)\Z")
_UNSAFE = re.compile(r"[;&|<>`]|\$\(")
_MAX_FILE_BYTES = 16 * 1024
_MAX_LINE_BYTES = 4096


def _validate_file_authority(path: Path, *, test_only: bool) -> bytes:
    try:
        info = path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            raise SecretsError("secrets_not_regular")
        if not test_only and info.st_uid != 0:
            raise SecretsError("secrets_owner")
        if stat.S_IMODE(info.st_mode) != 0o600:
            raise SecretsError("secrets_mode")
        data = path.read_bytes()
    except SecretsError:
        raise
    except OSError:
        raise SecretsError("secrets_unavailable") from None
    if len(data) > _MAX_FILE_BYTES:
        raise SecretsError("secrets_oversized")
    return data


def parse_secrets(data: bytes | str) -> SecretAuthority:
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, bytes) or len(data) > _MAX_FILE_BYTES or b"\x00" in data:
        raise SecretsError("secrets_invalid")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise SecretsError("secrets_invalid") from None
    values: dict[str, str] = {}
    lines = text.splitlines()
    if text and not text.endswith("\n") and "\r" in text:
        raise SecretsError("secrets_invalid")
    for line in lines:
        if len(line.encode("utf-8")) > _MAX_LINE_BYTES or not line or line.lstrip().startswith("#"):
            if line.lstrip().startswith("#"):
                continue
            raise SecretsError("secrets_assignment_invalid")
        match = _ASSIGNMENT.fullmatch(line)
        if match is None or match.group(1) in values or _UNSAFE.search(match.group(2)):
            raise SecretsError("secrets_assignment_invalid")
        values[match.group(1)] = match.group(2)
    token = values.get("TELEGRAM_BOT_TOKEN")
    if token is None:
        raise SecretsError("token_missing")
    if not token or any(char.isspace() for char in token):
        raise SecretsError("token_invalid")
    return SecretAuthority(token)


def load_secrets(path: str | os.PathLike[str], *, test_only: bool = False) -> SecretAuthority:
    path_object = Path(path)
    # lstat prevents a symlink from becoming an authority by path traversal.
    try:
        if path_object.is_symlink():
            raise SecretsError("secrets_symlink")
    except OSError:
        raise SecretsError("secrets_unavailable") from None
    return parse_secrets(_validate_file_authority(path_object, test_only=test_only))


__all__ = ["SecretAuthority", "SecretsError", "load_secrets", "parse_secrets"]
