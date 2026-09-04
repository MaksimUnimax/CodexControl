"""Authenticated, generation-scoped normalization of ``model/list`` results."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

MODEL_LIST_METHOD = "model/list"
MODEL_LIST_PAGE_SIZE = 100
MAX_MODEL_LIST_PAGE_ITEMS = MODEL_LIST_PAGE_SIZE
DEFAULT_MODEL_CATALOG_TTL_SECONDS = 60.0
MAX_MODEL_LIST_PAGES = 32
MAX_MODEL_CATALOG_SIZE = 512
MAX_MODEL_ID_CHARS = 256
MAX_WIRE_MODEL_CHARS = 256
MAX_MODEL_DISPLAY_NAME_CHARS = 256
MAX_REASONING_EFFORTS_PER_MODEL = 16
MAX_REASONING_EFFORT_CHARS = 64
MAX_MODEL_LIST_CURSOR_CHARS = 4096


class ModelCatalogError(Exception):
    """Finite, payload-free catalog error categories."""
    def __init__(self, category: str) -> None:
        self.category = category if category in {
            "model_not_available",
            "reasoning_effort_unsupported",
            "catalog_response_invalid",
            "catalog_limit_exceeded",
            "pagination_invalid",
        } else "catalog_response_invalid"
        super().__init__(self.category)


@dataclass(frozen=True)
class CodexModelDescriptor:
    model_id: str
    wire_model: str
    display_name: str
    supported_reasoning_efforts: tuple[str, ...]
    default_reasoning_effort: str
    is_default: bool
    hidden: bool


@dataclass(frozen=True)
class CodexModelCatalog:
    profile_id: str
    runtime_generation: int
    models: tuple[CodexModelDescriptor, ...]
    fetched_at: float
    expires_at: float

    def resolve_model(self, model_id: str) -> CodexModelDescriptor:
        for model in self.models:
            if model.model_id == model_id:
                return model
        raise ModelCatalogError("model_not_available")

    def resolve_wire_model(self, model_id: str) -> str:
        return self.resolve_model(model_id).wire_model

    def validate_reasoning_effort(self, model_id: str, effort: str | None) -> str | None:
        model = self.resolve_model(model_id)
        if effort is None:
            return model.default_reasoning_effort
        if effort not in model.supported_reasoning_efforts:
            raise ModelCatalogError("reasoning_effort_unsupported")
        return effort


class RuntimeLike(Protocol):
    profile_id: str
    generation: int
    client: Any


class RuntimeManagerLike(Protocol):
    async def acquire(self, profile_id: str) -> RuntimeLike: ...


class CodexModelCatalogAdapter:
    """Fetches only complete catalog snapshots from an already READY runtime."""
    def __init__(self, manager: RuntimeManagerLike, *, ttl_seconds: float = DEFAULT_MODEL_CATALOG_TTL_SECONDS,
                 clock: Callable[[], float] = time.monotonic) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds_must_be_positive")
        self._manager, self._ttl_seconds, self._clock = manager, ttl_seconds, clock
        self._cache: dict[tuple[str, int], CodexModelCatalog] = {}
        self._inflight: dict[tuple[str, int], asyncio.Task[CodexModelCatalog]] = {}
        self._observed_generation: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog:
        runtime = await self._manager.acquire(profile_id)
        if runtime.profile_id != profile_id or not isinstance(runtime.generation, int):
            raise ModelCatalogError("catalog_response_invalid")
        key = (profile_id, runtime.generation)
        async with self._lock:
            self._observe_generation_locked(profile_id, runtime.generation)
            cached = self._cache.get(key)
            if not refresh and cached is not None and self._clock() < cached.expires_at:
                return cached
            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(self._refresh(runtime, key))
                self._inflight[key] = task
                task.add_done_callback(self._consume_task_result)
        return await asyncio.shield(task)

    def _observe_generation_locked(self, profile_id: str, generation: int) -> None:
        prior = self._observed_generation.get(profile_id)
        if prior is None or generation > prior:
            self._observed_generation[profile_id] = generation
            for key in tuple(self._cache):
                if key[0] == profile_id and key[1] < generation:
                    self._cache.pop(key, None)
            for key in tuple(self._inflight):
                if key[0] == profile_id and key[1] < generation:
                    self._inflight.pop(key, None)

    def _consume_task_result(self, task: asyncio.Task[CodexModelCatalog]) -> None:
        if task.cancelled():
            return
        try:
            task.exception()
        except (asyncio.CancelledError, Exception):
            pass

    async def _refresh(self, runtime: RuntimeLike, key: tuple[str, int]) -> CodexModelCatalog:
        try:
            models = await self._fetch_models(runtime)
            fetched_at = self._clock()
            catalog = CodexModelCatalog(key[0], key[1], models, fetched_at, fetched_at + self._ttl_seconds)
            async with self._lock:
                if self._observed_generation.get(key[0]) == key[1]:
                    self._cache[key] = catalog
            return catalog
        finally:
            async with self._lock:
                if self._inflight.get(key) is asyncio.current_task():
                    self._inflight.pop(key, None)

    async def _fetch_models(self, runtime: RuntimeLike) -> tuple[CodexModelDescriptor, ...]:
        cursor: str | None = None
        seen_cursors: set[str] = set()
        all_models: list[CodexModelDescriptor] = []
        seen_ids: set[str] = set()
        seen_wire_models: set[str] = set()
        for page_number in range(1, MAX_MODEL_LIST_PAGES + 1):
            params: dict[str, Any] = {"includeHidden": False, "limit": MODEL_LIST_PAGE_SIZE}
            if cursor is not None:
                params["cursor"] = cursor
            response = await runtime.client.request(MODEL_LIST_METHOD, params)
            entries, next_cursor = self._parse_page(response)
            for entry in entries:
                model = self._normalize_model(entry)
                if model.hidden:
                    continue
                if model.model_id in seen_ids or model.wire_model in seen_wire_models:
                    raise ModelCatalogError("catalog_response_invalid")
                seen_ids.add(model.model_id)
                seen_wire_models.add(model.wire_model)
                all_models.append(model)
                if len(all_models) > MAX_MODEL_CATALOG_SIZE:
                    raise ModelCatalogError("catalog_limit_exceeded")
            if next_cursor is None:
                self._validate_defaults(all_models)
                return tuple(all_models)
            if next_cursor in seen_cursors:
                raise ModelCatalogError("pagination_invalid")
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise ModelCatalogError("catalog_limit_exceeded")

    @staticmethod
    def _parse_page(response: Any) -> tuple[list[Any], str | None]:
        if not isinstance(response, dict) or not isinstance(response.get("data"), list):
            raise ModelCatalogError("catalog_response_invalid")
        if len(response["data"]) > MAX_MODEL_LIST_PAGE_ITEMS:
            raise ModelCatalogError("catalog_limit_exceeded")
        next_cursor = response.get("nextCursor")
        if next_cursor is not None and (not isinstance(next_cursor, str) or len(next_cursor) > MAX_MODEL_LIST_CURSOR_CHARS):
            raise ModelCatalogError("pagination_invalid")
        return response["data"], next_cursor

    @staticmethod
    def _bounded_string(value: Any, maximum: int) -> str:
        if not isinstance(value, str) or not value or len(value) > maximum:
            raise ModelCatalogError("catalog_response_invalid")
        return value

    def _normalize_model(self, entry: Any) -> CodexModelDescriptor:
        if not isinstance(entry, dict):
            raise ModelCatalogError("catalog_response_invalid")
        model_id = self._bounded_string(entry.get("id"), MAX_MODEL_ID_CHARS)
        wire_model = self._bounded_string(entry.get("model"), MAX_WIRE_MODEL_CHARS)
        display_name = self._bounded_string(entry.get("displayName"), MAX_MODEL_DISPLAY_NAME_CHARS)
        if not isinstance(entry.get("description"), str) or not isinstance(entry.get("hidden"), bool) or not isinstance(entry.get("isDefault"), bool):
            raise ModelCatalogError("catalog_response_invalid")
        efforts_raw = entry.get("supportedReasoningEfforts")
        if not isinstance(efforts_raw, list) or len(efforts_raw) > MAX_REASONING_EFFORTS_PER_MODEL:
            raise ModelCatalogError("catalog_response_invalid")
        efforts: list[str] = []
        for option in efforts_raw:
            if not isinstance(option, dict) or not isinstance(option.get("description"), str):
                raise ModelCatalogError("catalog_response_invalid")
            effort = self._bounded_string(option.get("reasoningEffort"), MAX_REASONING_EFFORT_CHARS)
            if effort in efforts:
                raise ModelCatalogError("catalog_response_invalid")
            efforts.append(effort)
        default_effort = self._bounded_string(entry.get("defaultReasoningEffort"), MAX_REASONING_EFFORT_CHARS)
        if default_effort not in efforts:
            raise ModelCatalogError("catalog_response_invalid")
        return CodexModelDescriptor(model_id, wire_model, display_name, tuple(efforts), default_effort, entry["isDefault"], entry["hidden"])

    @staticmethod
    def _validate_defaults(models: list[CodexModelDescriptor]) -> None:
        if sum(model.is_default for model in models) > 1:
            raise ModelCatalogError("catalog_response_invalid")
