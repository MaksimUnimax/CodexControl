"""Telegram-agnostic settings/profile/model/reasoning selection."""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsDialogueGuardRepository,
    SettingsRecord,
    SettingsRepository,
    SqliteStorage,
)
from codex_control.storage.core_repositories import MAX_SQLITE_INT
from codex_control.storage.errors import StorageError


MAX_SERVICE_STRING_CHARS = 128


@dataclass(frozen=True)
class SettingsProfileOption:
    profile_id: str
    display_name: str


@dataclass(frozen=True)
class SettingsModelOption:
    model_id: str
    display_name: str
    supported_reasoning_efforts: tuple[str, ...]
    default_reasoning_effort: str
    is_default: bool


@dataclass(frozen=True)
class SettingsSelectionView:
    settings: SettingsRecord | None
    dialogue_state: DialogueState | None
    dialogue_profile_id: str | None
    profiles: tuple[SettingsProfileOption, ...]
    models: tuple[SettingsModelOption, ...]
    catalog_available: bool


class SettingsMutationStatus(StrEnum):
    UPDATED = "UPDATED"
    NO_CHANGE = "NO_CHANGE"
    BLOCKED = "BLOCKED"
    CONFLICT = "CONFLICT"


class SettingsMutationReason(StrEnum):
    SETTINGS_MISSING = "SETTINGS_MISSING"
    PROFILE_NOT_CONFIGURED = "PROFILE_NOT_CONFIGURED"
    PROFILE_LOCKED = "PROFILE_LOCKED"
    DIALOGUE_NOT_IDLE = "DIALOGUE_NOT_IDLE"
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    REASONING_EFFORT_UNSUPPORTED = "REASONING_EFFORT_UNSUPPORTED"
    STALE_SETTINGS = "STALE_SETTINGS"


class SettingsSelectionErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class SettingsSelectionError(Exception):
    """Finite, payload-free settings application diagnostic."""

    def __init__(self, category: SettingsSelectionErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, SettingsSelectionErrorCategory)
                else SettingsSelectionErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = SettingsSelectionErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"SettingsSelectionError({self.category.value!r})"


@dataclass(frozen=True)
class SettingsMutationResult:
    status: SettingsMutationStatus
    settings: SettingsRecord | None
    reason: SettingsMutationReason | None


class SettingsSelectionService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        profiles: tuple[CodexProfile, ...],
        model_catalog: object,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        _validate_string(server_id, MAX_SERVICE_STRING_CHARS)
        if type(profiles) is not tuple:
            raise _invalid()
        profile_ids: set[str] = set()
        for profile in profiles:
            if not isinstance(profile, CodexProfile):
                raise _invalid()
            _validate_string(profile.profile_id, MAX_SERVICE_STRING_CHARS)
            if profile.profile_id in profile_ids:
                raise _invalid()
            profile_ids.add(profile.profile_id)
            if not isinstance(profile.display_name, str) or not profile.display_name or "\x00" in profile.display_name:
                raise _invalid()
        if not _async_callable(model_catalog, "get_catalog"):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._profiles = profiles
        self._profile_options = tuple(
            SettingsProfileOption(profile.profile_id, profile.display_name) for profile in profiles
        )
        self._profile_ids = frozenset(profile_ids)
        self._model_catalog = model_catalog
        self._clock = now_ms if now_ms is not None else _default_clock

    async def get_view(self, *, refresh: bool = False) -> SettingsSelectionView:
        if type(refresh) is not bool:
            raise _invalid()
        settings = await self._settings()
        dialogue = await self._dialogue()
        effective_profile: str | None = None
        if dialogue is not None:
            if dialogue.server_id != self._server_id or dialogue.profile_id not in self._profile_ids:
                raise _invariant()
            if settings is not None and settings.profile_id is not None and settings.profile_id != dialogue.profile_id:
                raise _invariant()
            effective_profile = dialogue.profile_id
        elif settings is not None:
            effective_profile = settings.profile_id

        models: tuple[SettingsModelOption, ...] = ()
        catalog_available = False
        if effective_profile is not None and effective_profile in self._profile_ids:
            models, catalog_available = await self._project_catalog(effective_profile, refresh=refresh)
        return SettingsSelectionView(
            settings,
            None if dialogue is None else dialogue.state,
            None if dialogue is None else dialogue.profile_id,
            self._profile_options,
            models,
            catalog_available,
        )

    async def select_profile(
        self,
        profile_id: str,
        *,
        expected_version: int,
    ) -> SettingsMutationResult:
        _validate_string(profile_id, MAX_SERVICE_STRING_CHARS)
        _validate_version(expected_version)
        if profile_id not in self._profile_ids:
            return _blocked(None, SettingsMutationReason.PROFILE_NOT_CONFIGURED)
        settings = await self._settings()
        if settings is None:
            return _blocked(None, SettingsMutationReason.SETTINGS_MISSING)
        if settings.version != expected_version:
            return _conflict()
        if profile_id == settings.profile_id:
            dialogue = await self._dialogue()
            if dialogue is not None and (
                dialogue.server_id != self._server_id or dialogue.profile_id != settings.profile_id
            ):
                raise _invariant()
            return _no_change(settings)
        try:
            updated = await SettingsDialogueGuardRepository(self._storage, now_ms=self._clock).replace_profile_no_dialogue(
                expected_version=expected_version,
                profile_id=profile_id,
            )
        except RepositoryError as error:
            return self._profile_guard_failure(settings, error)
        except StorageError:
            raise _storage() from None
        return _updated(updated)

    async def select_model(
        self,
        model_id: str,
        *,
        expected_version: int,
    ) -> SettingsMutationResult:
        _validate_string(model_id, 256)
        _validate_version(expected_version)
        settings = await self._settings()
        if settings is None:
            return _blocked(None, SettingsMutationReason.SETTINGS_MISSING)
        if settings.version != expected_version:
            return _conflict()
        profile_id = settings.profile_id
        if profile_id is None or profile_id not in self._profile_ids:
            return _blocked(settings, SettingsMutationReason.PROFILE_NOT_CONFIGURED)
        catalog = await self._authenticated_catalog(profile_id)
        descriptor = _visible_descriptor(catalog, model_id)
        if descriptor is None:
            return _blocked(settings, SettingsMutationReason.MODEL_UNAVAILABLE)
        if settings.model_id == model_id and settings.reasoning_effort == descriptor.default_reasoning_effort:
            return _no_change(settings)
        try:
            updated = await SettingsDialogueGuardRepository(self._storage, now_ms=self._clock).replace_selection_idle_or_no_dialogue(
                expected_version=expected_version,
                server_id=self._server_id,
                profile_id=profile_id,
                model_id=model_id,
                reasoning_effort=descriptor.default_reasoning_effort,
            )
        except RepositoryError as error:
            return self._selection_guard_failure(settings, error)
        except StorageError:
            raise _storage() from None
        return _updated(updated)

    async def select_reasoning_effort(
        self,
        reasoning_effort: str,
        *,
        expected_version: int,
    ) -> SettingsMutationResult:
        _validate_string(reasoning_effort, 64)
        _validate_version(expected_version)
        settings = await self._settings()
        if settings is None:
            return _blocked(None, SettingsMutationReason.SETTINGS_MISSING)
        if settings.version != expected_version:
            return _conflict()
        profile_id = settings.profile_id
        if profile_id is None or profile_id not in self._profile_ids:
            return _blocked(settings, SettingsMutationReason.PROFILE_NOT_CONFIGURED)
        if settings.model_id is None:
            return _blocked(settings, SettingsMutationReason.MODEL_NOT_CONFIGURED)
        catalog = await self._authenticated_catalog(profile_id)
        descriptor = _visible_descriptor(catalog, settings.model_id)
        if descriptor is None:
            return _blocked(settings, SettingsMutationReason.MODEL_UNAVAILABLE)
        if reasoning_effort not in descriptor.supported_reasoning_efforts:
            return _blocked(settings, SettingsMutationReason.REASONING_EFFORT_UNSUPPORTED)
        if settings.reasoning_effort == reasoning_effort:
            return _no_change(settings)
        try:
            updated = await SettingsDialogueGuardRepository(self._storage, now_ms=self._clock).replace_selection_idle_or_no_dialogue(
                expected_version=expected_version,
                server_id=self._server_id,
                profile_id=profile_id,
                model_id=settings.model_id,
                reasoning_effort=reasoning_effort,
            )
        except RepositoryError as error:
            return self._selection_guard_failure(settings, error)
        except StorageError:
            raise _storage() from None
        return _updated(updated)

    async def _settings(self) -> SettingsRecord | None:
        try:
            return await SettingsRepository(self._storage).get()
        except RepositoryError as error:
            _raise_repository(error)
        except StorageError:
            raise _storage() from None

    async def _dialogue(self):
        try:
            return await DialogueRepository(self._storage).get_live()
        except RepositoryError as error:
            _raise_repository(error)
        except StorageError:
            raise _storage() from None

    async def _authenticated_catalog(self, profile_id: str) -> CodexModelCatalog | None:
        try:
            catalog = await self._model_catalog.get_catalog(profile_id, refresh=True)
        except asyncio.CancelledError:
            raise
        except Exception:
            return None
        if type(catalog) is not CodexModelCatalog or catalog.profile_id != profile_id:
            return None
        return catalog if _catalog_descriptors(catalog) is not None else None

    async def _project_catalog(
        self, profile_id: str, *, refresh: bool
    ) -> tuple[tuple[SettingsModelOption, ...], bool]:
        try:
            catalog = await self._model_catalog.get_catalog(profile_id, refresh=refresh)
        except asyncio.CancelledError:
            raise
        except Exception:
            return (), False
        if type(catalog) is not CodexModelCatalog or catalog.profile_id != profile_id:
            return (), False
        descriptors = _catalog_descriptors(catalog)
        if descriptors is None:
            return (), False
        return tuple(
            SettingsModelOption(
                descriptor.model_id,
                descriptor.display_name,
                descriptor.supported_reasoning_efforts,
                descriptor.default_reasoning_effort,
                descriptor.is_default,
            )
            for descriptor in descriptors
            if not descriptor.hidden
        ), True

    @staticmethod
    def _profile_guard_failure(settings: SettingsRecord, error: RepositoryError) -> SettingsMutationResult:
        if error.category is RepositoryErrorCategory.STATE_CONFLICT:
            return _blocked(settings, SettingsMutationReason.PROFILE_LOCKED)
        if error.category is RepositoryErrorCategory.VERSION_CONFLICT:
            return _conflict()
        _raise_repository(error)

    @staticmethod
    def _selection_guard_failure(settings: SettingsRecord, error: RepositoryError) -> SettingsMutationResult:
        if error.category is RepositoryErrorCategory.STATE_CONFLICT:
            return _blocked(settings, SettingsMutationReason.DIALOGUE_NOT_IDLE)
        if error.category is RepositoryErrorCategory.VERSION_CONFLICT:
            return _conflict()
        _raise_repository(error)


def _catalog_descriptors(catalog: CodexModelCatalog) -> tuple[CodexModelDescriptor, ...] | None:
    if type(catalog.models) is not tuple:
        return None
    seen: set[str] = set()
    visible: list[CodexModelDescriptor] = []
    for descriptor in catalog.models:
        if type(descriptor) is not CodexModelDescriptor:
            return None
        if not _valid_string(descriptor.model_id, 256) or not _valid_string(descriptor.wire_model, 256):
            return None
        if not _valid_string(descriptor.display_name, 256) or type(descriptor.hidden) is not bool:
            return None
        if type(descriptor.is_default) is not bool or type(descriptor.supported_reasoning_efforts) is not tuple:
            return None
        efforts = descriptor.supported_reasoning_efforts
        if not efforts or len(efforts) > 16 or len(set(efforts)) != len(efforts):
            return None
        if any(not _valid_string(effort, 64) for effort in efforts):
            return None
        if not _valid_string(descriptor.default_reasoning_effort, 64) or descriptor.default_reasoning_effort not in efforts:
            return None
        if descriptor.model_id in seen:
            return None
        seen.add(descriptor.model_id)
        if not descriptor.hidden:
            visible.append(descriptor)
    return tuple(visible)


def _visible_descriptor(catalog: CodexModelCatalog | None, model_id: str) -> CodexModelDescriptor | None:
    if catalog is None:
        return None
    for descriptor in _catalog_descriptors(catalog) or ():
        if descriptor.model_id == model_id:
            return descriptor
    return None


def _valid_string(value: object, limit: int) -> bool:
    return isinstance(value, str) and bool(value) and "\x00" not in value and len(value) <= limit


def _validate_string(value: object, limit: int) -> None:
    if not _valid_string(value, limit):
        raise _invalid()


def _validate_version(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SQLITE_INT:
        raise _invalid()


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _invalid() -> SettingsSelectionError:
    return SettingsSelectionError(SettingsSelectionErrorCategory.INVALID_ARGUMENT)


def _storage() -> SettingsSelectionError:
    return SettingsSelectionError(SettingsSelectionErrorCategory.STORAGE)


def _invariant() -> SettingsSelectionError:
    return SettingsSelectionError(SettingsSelectionErrorCategory.INVARIANT)


def _raise_repository(error: RepositoryError) -> None:
    if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
        raise _invariant() from None
    if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
        raise _invalid() from None
    raise _storage() from None


def _blocked(settings: SettingsRecord | None, reason: SettingsMutationReason) -> SettingsMutationResult:
    return SettingsMutationResult(SettingsMutationStatus.BLOCKED, settings, reason)


def _no_change(settings: SettingsRecord) -> SettingsMutationResult:
    return SettingsMutationResult(SettingsMutationStatus.NO_CHANGE, settings, None)


def _updated(settings: SettingsRecord) -> SettingsMutationResult:
    return SettingsMutationResult(SettingsMutationStatus.UPDATED, settings, None)


def _conflict() -> SettingsMutationResult:
    return SettingsMutationResult(SettingsMutationStatus.CONFLICT, None, SettingsMutationReason.STALE_SETTINGS)


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


__all__ = [
    "SettingsProfileOption",
    "SettingsModelOption",
    "SettingsSelectionView",
    "SettingsMutationStatus",
    "SettingsMutationReason",
    "SettingsMutationResult",
    "SettingsSelectionErrorCategory",
    "SettingsSelectionError",
    "SettingsSelectionService",
]
