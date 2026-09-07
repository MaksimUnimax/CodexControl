"""P4.1 private settings management over the accepted P3.3 service."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable

from codex_control.adapters.telegram.private_updates import PrivateCommand
from codex_control.domain import CodexProfile
from codex_control.storage import (
    CallbackActionRepository,
    CallbackClaimStatus,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
)
from codex_control.storage.core_repositories import MAX_SQLITE_INT

from .settings_selection import (
    SettingsMutationReason,
    SettingsMutationStatus,
    SettingsSelectionError,
    SettingsSelectionErrorCategory,
    SettingsSelectionService,
    SettingsSelectionView,
)


P4_PRIVATE_PAGE_SIZE = 8
P4_PRIVATE_CALLBACK_TTL_MS = 900000
P4_PRIVATE_PANEL_TEXT_MAX_CHARS = 3500
P4_PRIVATE_BUTTON_LABEL_MAX_CHARS = 64

_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32}")
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_ACTION_VALUES = frozenset(
    {
        "OPEN_ROOT", "OPEN_PROFILES", "OPEN_MODELS", "OPEN_REASONING",
        "SELECT_PROFILE", "SELECT_MODEL", "SELECT_REASONING",
    }
)
_DIALOGUE_STATES = frozenset(state.value for state in DialogueState)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class PrivatePanelSection(StrEnum):
    ROOT = "ROOT"
    PROFILES = "PROFILES"
    MODELS = "MODELS"
    REASONING = "REASONING"


class PrivateAdminStatus(StrEnum):
    RENDERED = "RENDERED"
    UPDATED = "UPDATED"
    NO_CHANGE = "NO_CHANGE"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    ALREADY_USED = "ALREADY_USED"
    DUPLICATE = "DUPLICATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"


class PrivateAdminReason(StrEnum):
    CALLBACK_NOT_FOUND = "CALLBACK_NOT_FOUND"
    STALE_ACTION = "STALE_ACTION"
    SETTINGS_MISSING = "SETTINGS_MISSING"
    PROFILE_NOT_CONFIGURED = "PROFILE_NOT_CONFIGURED"
    PROFILE_LOCKED = "PROFILE_LOCKED"
    DIALOGUE_NOT_IDLE = "DIALOGUE_NOT_IDLE"
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    REASONING_EFFORT_UNSUPPORTED = "REASONING_EFFORT_UNSUPPORTED"
    CATALOG_UNAVAILABLE = "CATALOG_UNAVAILABLE"
    ACTION_UNAVAILABLE = "ACTION_UNAVAILABLE"


class PrivateAdminErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class PrivateAdminError(Exception):
    """Finite, content-free P4.1 diagnostic."""

    def __init__(self, category: PrivateAdminErrorCategory | str) -> None:
        try:
            self.category = category if isinstance(category, PrivateAdminErrorCategory) else PrivateAdminErrorCategory(category)
        except (TypeError, ValueError):
            self.category = PrivateAdminErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"PrivateAdminError({self.category.value!r})"


@dataclass(frozen=True, repr=False)
class PrivateCommandRequest:
    update_id: int
    user_id: int
    chat_id: int
    command: PrivateCommand | None

    def __repr__(self) -> str:
        command = self.command if isinstance(self.command, PrivateCommand) else None
        return (
            "PrivateCommandRequest("
            f"update_id={self.update_id!r}, user_id={self.user_id!r}, "
            f"chat_id={self.chat_id!r}, command={command!r})"
        )


@dataclass(frozen=True, repr=False)
class PrivateCallbackRequest:
    update_id: int
    user_id: int
    chat_id: int
    callback_query_id: str
    callback_token: str

    def __repr__(self) -> str:
        return (
            "PrivateCallbackRequest("
            f"update_id={self.update_id!r}, user_id={self.user_id!r}, chat_id={self.chat_id!r}, "
            f"callback_query_id={self.callback_query_id!r}, callback_token='[REDACTED]')"
        )


@dataclass(frozen=True, repr=False)
class PrivateAdminButton:
    label: str
    callback_data: str

    def __post_init__(self) -> None:
        label = _display_text(self.label, P4_PRIVATE_BUTTON_LABEL_MAX_CHARS) or "Option"
        if not isinstance(self.callback_data, str) or len(self.callback_data) != 36 or not self.callback_data.startswith("cc1:") or _TOKEN_RE.fullmatch(self.callback_data[4:]) is None:
            raise ValueError("invalid callback data")
        object.__setattr__(self, "label", label)

    def __repr__(self) -> str:
        return f"PrivateAdminButton(label={self.label!r}, callback_data='[REDACTED]')"


@dataclass(frozen=True, repr=False)
class PrivateAdminPanel:
    section: PrivatePanelSection
    text: str
    rows: tuple[tuple[PrivateAdminButton, ...], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.section, PrivatePanelSection):
            raise ValueError("invalid panel section")
        if type(self.rows) is not tuple or any(type(row) is not tuple for row in self.rows):
            raise ValueError("invalid panel rows")
        for row in self.rows:
            if any(not isinstance(button, PrivateAdminButton) for button in row):
                raise ValueError("invalid panel button")
        object.__setattr__(self, "text", _display_text(self.text, P4_PRIVATE_PANEL_TEXT_MAX_CHARS) or "Settings")

    def __repr__(self) -> str:
        labels = tuple(tuple(button.label for button in row) for row in self.rows)
        return f"PrivateAdminPanel(section={self.section!r}, text={self.text!r}, rows={labels!r})"


@dataclass(frozen=True, repr=False)
class PrivateAdminResult:
    status: PrivateAdminStatus
    panel: PrivateAdminPanel | None
    reason: PrivateAdminReason | None

    def __repr__(self) -> str:
        return f"PrivateAdminResult(status={self.status!r}, panel={self.panel!r}, reason={self.reason!r})"


def _display_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    value = _CONTROL_RE.sub(" ", value)
    return " ".join(value.split())[:limit]


def _hash_target(target: str) -> str:
    return hashlib.sha256(target.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    return _display_text(value, 256) or "[unavailable]"


def _invalid() -> PrivateAdminError:
    return PrivateAdminError(PrivateAdminErrorCategory.INVALID_ARGUMENT)


def _storage() -> PrivateAdminError:
    return PrivateAdminError(PrivateAdminErrorCategory.STORAGE)


def _invariant() -> PrivateAdminError:
    return PrivateAdminError(PrivateAdminErrorCategory.INVARIANT)


def _valid_nonnegative(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= MAX_SQLITE_INT


def _valid_user(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SQLITE_INT


def _valid_chat(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and -(2**63) <= value <= MAX_SQLITE_INT and value != 0


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


class PrivateSettingsManagementService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        server_display_name: str,
        operator_user_id: int,
        profiles: tuple[CodexProfile, ...],
        model_catalog: object,
        now_ms: Callable[[], int] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage) or not isinstance(server_id, str) or not server_id or "\x00" in server_id:
            raise _invalid()
        if not isinstance(server_display_name, str) or not server_display_name or "\x00" in server_display_name:
            raise _invalid()
        if not _valid_user(operator_user_id) or type(profiles) is not tuple:
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if token_factory is not None and not callable(token_factory):
            raise _invalid()
        try:
            self._settings = SettingsSelectionService(
                storage,
                server_id=server_id,
                profiles=profiles,
                model_catalog=model_catalog,
                now_ms=now_ms,
            )
        except Exception as error:
            if isinstance(error, SettingsSelectionError):
                raise _invalid() from None
            raise
        self._storage = storage
        self._server_id = server_id
        self._server_display_name = server_display_name
        self._operator_user_id = operator_user_id
        self._clock = now_ms if now_ms is not None else _default_clock
        self._token_factory = token_factory if token_factory is not None else lambda: secrets.token_urlsafe(24)
        self._profiles = profiles

    async def handle_command(self, request: PrivateCommandRequest) -> PrivateAdminResult:
        self._validate_command_request(request)
        if request.user_id != self._operator_user_id or request.chat_id != self._operator_user_id:
            try:
                await IngressUpdateRepository(self._storage, now_ms=self._clock).claim_ignored(
                    update_id=request.update_id,
                    disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED,
                )
            except (RepositoryError, StorageError):
                raise _storage() from None
            return PrivateAdminResult(PrivateAdminStatus.UNAUTHORIZED, None, None)
        if request.command is None:
            return PrivateAdminResult(PrivateAdminStatus.UNSUPPORTED, None, None)

        try:
            claim = await PrivateManagementRepository(self._storage, now_ms=self._clock).claim_private_command(
                update_id=request.update_id
            )
        except RepositoryError as error:
            raise self._map_repository_error(error, internal=True) from None
        except StorageError:
            raise _storage() from None
        if claim.duplicate:
            return PrivateAdminResult(PrivateAdminStatus.DUPLICATE, None, None)
        try:
            view = await self._settings.get_view(refresh=True)
        except SettingsSelectionError as error:
            raise self._map_selection_error(error) from None
        panel = await self._render(PrivatePanelSection.ROOT, view, page=0)
        if view.settings is None:
            return PrivateAdminResult(PrivateAdminStatus.BLOCKED, panel, PrivateAdminReason.SETTINGS_MISSING)
        return PrivateAdminResult(PrivateAdminStatus.RENDERED, panel, None)

    async def handle_callback(self, request: PrivateCallbackRequest) -> PrivateAdminResult:
        self._validate_callback_request(request)
        if request.user_id != self._operator_user_id or request.chat_id != self._operator_user_id:
            return PrivateAdminResult(PrivateAdminStatus.UNAUTHORIZED, None, None)
        if _TOKEN_RE.fullmatch(request.callback_token) is None:
            raise _invalid()
        token_hash = _hash_target(request.callback_token)
        try:
            claimed = await CallbackActionRepository(self._storage, now_ms=self._clock).claim(
                token_hash_sha256=token_hash,
                authorized_user_id=request.user_id,
                authorized_chat_id=request.chat_id,
            )
        except RepositoryError as error:
            raise self._map_repository_error(error, internal=True) from None
        except StorageError:
            raise _storage() from None
        if claimed.status is CallbackClaimStatus.NOT_FOUND:
            return PrivateAdminResult(PrivateAdminStatus.STALE, None, PrivateAdminReason.CALLBACK_NOT_FOUND)
        if claimed.status is CallbackClaimStatus.UNAUTHORIZED:
            return PrivateAdminResult(PrivateAdminStatus.UNAUTHORIZED, None, None)
        if claimed.status is CallbackClaimStatus.EXPIRED:
            return PrivateAdminResult(PrivateAdminStatus.EXPIRED, None, None)
        if claimed.status is CallbackClaimStatus.ALREADY_CONSUMED:
            return PrivateAdminResult(PrivateAdminStatus.ALREADY_USED, None, None)
        if claimed.status is not CallbackClaimStatus.CLAIMED or claimed.record is None:
            raise _invariant()
        record = claimed.record
        self._validate_claimed_record(record)
        try:
            view = await self._settings.get_view(refresh=True)
        except SettingsSelectionError as error:
            raise self._map_selection_error(error) from None
        if view.settings is None:
            return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.SETTINGS_MISSING)
        current_state = _expected_state(view)
        if record.expected_version != view.settings.version or record.expected_state != current_state:
            panel = None
            if record.action.startswith("OPEN_"):
                panel = await self._render(PrivatePanelSection.ROOT, view, page=0)
            return PrivateAdminResult(PrivateAdminStatus.STALE, panel, PrivateAdminReason.STALE_ACTION)
        if record.action.startswith("OPEN_"):
            return await self._handle_navigation(record.action, record.subject_id, view)
        return await self._handle_selection(record.action, record.subject_id, view, record.expected_version)

    def _validate_command_request(self, request: object) -> None:
        if not isinstance(request, PrivateCommandRequest) or not _valid_nonnegative(request.update_id) or not _valid_user(request.user_id) or not _valid_chat(request.chat_id):
            raise _invalid()
        if request.command is not None and not isinstance(request.command, PrivateCommand):
            raise _invalid()

    def _validate_callback_request(self, request: object) -> None:
        if (
            not isinstance(request, PrivateCallbackRequest)
            or not _valid_nonnegative(request.update_id)
            or not _valid_user(request.user_id)
            or not _valid_chat(request.chat_id)
            or not isinstance(request.callback_query_id, str)
            or not request.callback_query_id
            or "\x00" in request.callback_query_id
            or len(request.callback_query_id) > 256
            or not isinstance(request.callback_token, str)
        ):
            raise _invalid()

    def _validate_claimed_record(self, record: Any) -> None:
        if (
            record.action not in _ACTION_VALUES
            or record.expected_state not in (_DIALOGUE_STATES | {"NO_DIALOGUE"})
            or not _valid_nonnegative(record.expected_version)
            or not _HASH_RE.fullmatch(record.token_hash_sha256)
        ):
            raise _invariant()
        if record.action == "OPEN_ROOT" and record.subject_type == "panel":
            self._validate_page(record.subject_id)
        elif record.action in {"OPEN_PROFILES", "OPEN_MODELS", "OPEN_REASONING"} and record.subject_type == "panel":
            self._validate_page(record.subject_id)
        elif record.action == "SELECT_PROFILE" and record.subject_type == "profile_choice" and _HASH_RE.fullmatch(record.subject_id):
            if record.expected_state != "NO_DIALOGUE":
                raise _invariant()
        elif record.action == "SELECT_MODEL" and record.subject_type == "model_choice" and _HASH_RE.fullmatch(record.subject_id):
            if record.expected_state not in {"NO_DIALOGUE", DialogueState.IDLE.value}:
                raise _invariant()
        elif record.action == "SELECT_REASONING" and record.subject_type == "reasoning_choice" and _HASH_RE.fullmatch(record.subject_id):
            if record.expected_state not in {"NO_DIALOGUE", DialogueState.IDLE.value}:
                raise _invariant()
        else:
            raise _invariant()

    @staticmethod
    def _validate_page(value: str) -> int:
        if not isinstance(value, str) or (value != "0" and value.startswith("0")) or not value.isdigit():
            raise _invariant()
        page = int(value)
        if page > MAX_SQLITE_INT:
            raise _invariant()
        return page

    async def _handle_navigation(self, action: str, subject_id: str, view: SettingsSelectionView) -> PrivateAdminResult:
        page = self._validate_page(subject_id)
        section = {
            "OPEN_ROOT": PrivatePanelSection.ROOT,
            "OPEN_PROFILES": PrivatePanelSection.PROFILES,
            "OPEN_MODELS": PrivatePanelSection.MODELS,
            "OPEN_REASONING": PrivatePanelSection.REASONING,
        }[action]
        if page >= self._page_count(section, view):
            panel = await self._render(PrivatePanelSection.ROOT, view, page=0)
            return PrivateAdminResult(PrivateAdminStatus.STALE, panel, PrivateAdminReason.STALE_ACTION)
        panel = await self._render(section, view, page=page)
        return PrivateAdminResult(PrivateAdminStatus.RENDERED, panel, None)

    async def _handle_selection(
        self, action: str, subject_id: str, view: SettingsSelectionView, expected_version: int
    ) -> PrivateAdminResult:
        try:
            if action == "SELECT_PROFILE":
                targets = tuple(option.profile_id for option in view.profiles)
                matches = [target for target in targets if _hash_target(target) == subject_id]
                if len(matches) == 0:
                    raise _invariant()
                if len(matches) != 1:
                    raise _invariant()
                result = await self._settings.select_profile(matches[0], expected_version=expected_version)
            elif action == "SELECT_MODEL":
                if not view.catalog_available:
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.CATALOG_UNAVAILABLE)
                targets = tuple(option.model_id for option in view.models)
                matches = [target for target in targets if _hash_target(target) == subject_id]
                if len(matches) > 1:
                    raise _invariant()
                if not matches:
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.MODEL_UNAVAILABLE)
                result = await self._settings.select_model(matches[0], expected_version=expected_version)
            else:
                if not view.catalog_available:
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.CATALOG_UNAVAILABLE)
                if view.settings is None or view.settings.model_id is None:
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.MODEL_NOT_CONFIGURED)
                if not any(option.model_id == view.settings.model_id for option in view.models):
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.MODEL_UNAVAILABLE)
                efforts = self._current_reasoning_efforts(view)
                matches = [target for target in efforts if _hash_target(target) == subject_id]
                if len(matches) > 1:
                    raise _invariant()
                if not matches:
                    return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, PrivateAdminReason.REASONING_EFFORT_UNSUPPORTED)
                result = await self._settings.select_reasoning_effort(matches[0], expected_version=expected_version)
        except SettingsSelectionError as error:
            raise self._map_selection_error(error) from None
        return self._map_mutation(result)

    def _map_mutation(self, result: Any) -> PrivateAdminResult:
        if result.status is SettingsMutationStatus.UPDATED:
            return PrivateAdminResult(PrivateAdminStatus.UPDATED, None, None)
        if result.status is SettingsMutationStatus.NO_CHANGE:
            return PrivateAdminResult(PrivateAdminStatus.NO_CHANGE, None, None)
        if result.status is SettingsMutationStatus.CONFLICT:
            return PrivateAdminResult(PrivateAdminStatus.STALE, None, PrivateAdminReason.STALE_ACTION)
        if result.status is SettingsMutationStatus.BLOCKED:
            reason = {
                SettingsMutationReason.SETTINGS_MISSING: PrivateAdminReason.SETTINGS_MISSING,
                SettingsMutationReason.PROFILE_NOT_CONFIGURED: PrivateAdminReason.PROFILE_NOT_CONFIGURED,
                SettingsMutationReason.PROFILE_LOCKED: PrivateAdminReason.PROFILE_LOCKED,
                SettingsMutationReason.DIALOGUE_NOT_IDLE: PrivateAdminReason.DIALOGUE_NOT_IDLE,
                SettingsMutationReason.MODEL_NOT_CONFIGURED: PrivateAdminReason.MODEL_NOT_CONFIGURED,
                SettingsMutationReason.MODEL_UNAVAILABLE: PrivateAdminReason.MODEL_UNAVAILABLE,
                SettingsMutationReason.REASONING_EFFORT_UNSUPPORTED: PrivateAdminReason.REASONING_EFFORT_UNSUPPORTED,
            }.get(result.reason)
            if reason is None:
                raise _invariant()
            return PrivateAdminResult(PrivateAdminStatus.BLOCKED, None, reason)
        raise _invariant()

    def _map_selection_error(self, error: SettingsSelectionError) -> PrivateAdminError:
        if error.category is SettingsSelectionErrorCategory.STORAGE:
            return _storage()
        return _invariant()

    @staticmethod
    def _map_repository_error(error: RepositoryError, *, internal: bool = False) -> PrivateAdminError:
        if error.category in {
            RepositoryErrorCategory.INVARIANT_VIOLATION,
            RepositoryErrorCategory.INVALID_ARGUMENT,
        }:
            return _invariant() if internal or error.category is RepositoryErrorCategory.INVARIANT_VIOLATION else _invalid()
        return _storage()

    async def _render(self, section: PrivatePanelSection, view: SettingsSelectionView, *, page: int) -> PrivateAdminPanel:
        panel_text = self._panel_text(section, view, page)
        buttons: list[tuple[str, str, str, str]] = []
        if section is PrivatePanelSection.ROOT:
            if view.profiles:
                buttons.append(("Profiles", "OPEN_PROFILES", "panel", "0"))
            if view.catalog_available and view.models:
                buttons.append(("Models", "OPEN_MODELS", "panel", "0"))
                if self._current_reasoning_efforts(view):
                    buttons.append(("Reasoning", "OPEN_REASONING", "panel", "0"))
        else:
            options = self._options(section, view)
            start = page * P4_PRIVATE_PAGE_SIZE
            for option in options[start:start + P4_PRIVATE_PAGE_SIZE]:
                target, label, action, subject_type = option
                buttons.append((label, action, subject_type, _hash_target(target)))
            if page > 0:
                buttons.append(("Previous", self._open_action(section), "panel", str(page - 1)))
            if (page + 1) * P4_PRIVATE_PAGE_SIZE < len(options):
                buttons.append(("Next", self._open_action(section), "panel", str(page + 1)))
            buttons.append(("Back", "OPEN_ROOT", "panel", "0"))

        if not buttons:
            return PrivateAdminPanel(section, panel_text, ())
        now = self._read_clock()
        if now > MAX_SQLITE_INT - P4_PRIVATE_CALLBACK_TTL_MS:
            raise _invariant()
        expires = now + P4_PRIVATE_CALLBACK_TTL_MS
        rows: list[tuple[PrivateAdminButton, ...]] = []
        specs: list[PrivateCallbackActionSpec] = []
        seen_tokens: set[str] = set()
        for label, action, subject_type, subject_id in buttons:
            token = self._new_token(seen_tokens)
            seen_tokens.add(token)
            callback_data = "cc1:" + token
            rows.append((PrivateAdminButton(label, callback_data),))
            specs.append(
                PrivateCallbackActionSpec(
                    _hash_target(token), action, subject_type, subject_id,
                    view.settings.version if view.settings is not None else 0,
                    _expected_state(view), self._operator_user_id, self._operator_user_id,
                )
            )
        try:
            await PrivateManagementRepository(self._storage, now_ms=self._clock).create_callback_batch(
                actions=tuple(specs), created_at_ms=now, expires_at_ms=expires
            )
        except RepositoryError as error:
            raise self._map_repository_error(error, internal=True) from None
        except StorageError:
            raise _storage() from None
        return PrivateAdminPanel(section, panel_text, tuple(rows))

    def _new_token(self, seen: set[str]) -> str:
        try:
            token = self._token_factory()
        except Exception:
            raise _invariant() from None
        if not isinstance(token, str) or _TOKEN_RE.fullmatch(token) is None or token in seen:
            raise _invariant()
        return token

    def _read_clock(self) -> int:
        try:
            value = self._clock()
        except Exception:
            raise _storage() from None
        if not _valid_nonnegative(value):
            raise _storage()
        return value

    def _panel_text(self, section: PrivatePanelSection, view: SettingsSelectionView, page: int) -> str:
        settings = view.settings
        profile = settings.profile_id if settings is not None else None
        model = settings.model_id if settings is not None else None
        effort = settings.reasoning_effort if settings is not None else None
        state = _expected_state(view)
        lines = [
            f"Server: {_display_text(self._server_display_name, 256) or _safe_id(self._server_id)} ({_safe_id(self._server_id)})",
            f"Profile: {_safe_id(profile) if profile else 'not configured'}",
            f"Model: {_safe_id(model) if model else 'not configured'}",
            f"Reasoning: {_safe_id(effort) if effort else 'not configured'}",
            f"Dialogue: {state}",
            f"Catalog: {'available' if view.catalog_available else 'unavailable'}",
        ]
        if section is not PrivatePanelSection.ROOT:
            lines.insert(0, f"{section.value.title()} (page {page + 1})")
        return _display_text("\n".join(lines), P4_PRIVATE_PANEL_TEXT_MAX_CHARS)

    def _options(self, section: PrivatePanelSection, view: SettingsSelectionView) -> tuple[tuple[str, str, str, str], ...]:
        if section is PrivatePanelSection.PROFILES and view.dialogue_state is not None:
            return ()
        if section in {PrivatePanelSection.MODELS, PrivatePanelSection.REASONING} and view.dialogue_state not in (None, DialogueState.IDLE):
            return ()
        if section is PrivatePanelSection.PROFILES:
            return tuple((item.profile_id, _button_label(item.display_name, item.profile_id), "SELECT_PROFILE", "profile_choice") for item in view.profiles)
        if section is PrivatePanelSection.MODELS:
            if not view.catalog_available:
                return ()
            return tuple((item.model_id, _button_label(item.display_name, item.model_id), "SELECT_MODEL", "model_choice") for item in view.models)
        if section is PrivatePanelSection.REASONING:
            return tuple((effort, _button_label(effort, effort), "SELECT_REASONING", "reasoning_choice") for effort in self._current_reasoning_efforts(view))
        return ()

    def _current_reasoning_efforts(self, view: SettingsSelectionView) -> tuple[str, ...]:
        if view.settings is None or view.settings.model_id is None or not view.catalog_available:
            return ()
        for model in view.models:
            if model.model_id == view.settings.model_id:
                return model.supported_reasoning_efforts
        return ()

    def _page_count(self, section: PrivatePanelSection, view: SettingsSelectionView) -> int:
        count = len(self._options(section, view))
        return max(1, (count + P4_PRIVATE_PAGE_SIZE - 1) // P4_PRIVATE_PAGE_SIZE)

    @staticmethod
    def _open_action(section: PrivatePanelSection) -> str:
        return {
            PrivatePanelSection.PROFILES: "OPEN_PROFILES",
            PrivatePanelSection.MODELS: "OPEN_MODELS",
            PrivatePanelSection.REASONING: "OPEN_REASONING",
        }[section]


def _expected_state(view: SettingsSelectionView) -> str:
    return "NO_DIALOGUE" if view.dialogue_state is None else view.dialogue_state.value


def _button_label(display: str, fallback: str) -> str:
    return _display_text(display, P4_PRIVATE_BUTTON_LABEL_MAX_CHARS) or _display_text(
        fallback, P4_PRIVATE_BUTTON_LABEL_MAX_CHARS
    ) or "Option"


__all__ = [
    "P4_PRIVATE_PAGE_SIZE",
    "P4_PRIVATE_CALLBACK_TTL_MS",
    "P4_PRIVATE_PANEL_TEXT_MAX_CHARS",
    "P4_PRIVATE_BUTTON_LABEL_MAX_CHARS",
    "PrivatePanelSection",
    "PrivateAdminStatus",
    "PrivateAdminReason",
    "PrivateAdminErrorCategory",
    "PrivateAdminError",
    "PrivateCommandRequest",
    "PrivateCallbackRequest",
    "PrivateAdminButton",
    "PrivateAdminPanel",
    "PrivateAdminResult",
    "PrivateSettingsManagementService",
]
