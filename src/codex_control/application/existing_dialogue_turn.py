"""Application orchestration for a prompt on an existing Codex dialogue."""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Protocol
from uuid import uuid4

from codex_control.adapters.codex.model_catalog import CodexModelCatalog
from codex_control.adapters.codex.thread_lifecycle import ThreadBinding, TrustedWorkingDirectory
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    MAX_AGENT_MESSAGE_CHARS,
    MAX_AGENT_MESSAGES_PER_TURN,
    MAX_TOTAL_AGENT_MESSAGE_CHARS,
    TurnBinding,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    MAX_TRANSIENT_PAYLOAD_BYTES,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsRepository,
    SqliteStorage,
    TransientPayloadKind,
    TransientPayloadRecord,
    TransientPayloadRepository,
    TurnExecutionClaimResult,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnJobFinishResult,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
    TurnTerminalOutcome,
)
from codex_control.storage.errors import StorageError


P3_INPUT_PAYLOAD_RETENTION_MS = 3_600_000
P3_COMPLETED_OUTPUT_RETENTION_MS = 3_600_000
P3_UNCERTAIN_OUTPUT_RETENTION_MS = 86_400_000
MAX_SIGNED_64 = 9_223_372_036_854_775_807
MIN_SIGNED_64 = -9_223_372_036_854_775_808
MAX_SERVICE_STRING_CHARS = 128
MAX_PROMPT_CHARS = 65_536
MAX_REASONING_EFFORT_CHARS = 64
MAX_PROJECTED_OUTPUT_BYTES = MAX_TOTAL_AGENT_MESSAGE_CHARS * 4 + (MAX_AGENT_MESSAGES_PER_TURN - 1) * 2

INPUT_REQUIRED_STATES = frozenset(
    (TurnJobState.RECEIVED, TurnJobState.CLAIMED, TurnJobState.CODEX_STARTING, TurnJobState.CODEX_RUNNING)
)
INPUT_OPTIONAL_STATES = frozenset(
    (
        TurnJobState.CODEX_COMPLETED,
        TurnJobState.FAILED,
        TurnJobState.UNKNOWN,
        TurnJobState.DELIVERY_PENDING,
        TurnJobState.DELIVERING,
        TurnJobState.DELIVERED,
        TurnJobState.DELIVERY_UNKNOWN,
    )
)


class ExistingDialogueTurnStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    DUPLICATE = "DUPLICATE"
    BUSY = "BUSY"
    BLOCKED = "BLOCKED"


class ExistingDialogueTurnReason(StrEnum):
    NO_DIALOGUE = "NO_DIALOGUE"
    DIALOGUE_NOT_READY = "DIALOGUE_NOT_READY"
    SETTINGS_MISSING = "SETTINGS_MISSING"
    SETTINGS_PROFILE_MISMATCH = "SETTINGS_PROFILE_MISMATCH"
    PROFILE_NOT_CONFIGURED = "PROFILE_NOT_CONFIGURED"
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    WORKING_DIRECTORY_UNAVAILABLE = "WORKING_DIRECTORY_UNAVAILABLE"
    DUPLICATE_NON_JOB = "DUPLICATE_NON_JOB"
    DUPLICATE_ORPHAN_JOB = "DUPLICATE_ORPHAN_JOB"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"


class DialogueApplicationErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    CODEX = "CODEX"
    INVARIANT = "INVARIANT"


class DialogueApplicationError(Exception):
    """Finite, payload-free application diagnostic."""

    def __init__(self, category: DialogueApplicationErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, DialogueApplicationErrorCategory)
                else DialogueApplicationErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = DialogueApplicationErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"DialogueApplicationError({self.category.value!r})"


@dataclass(frozen=True)
class ExistingDialoguePromptRequest:
    update_id: int
    source_chat_id: int
    source_message_id: int
    text: str = field(repr=False)

    def __post_init__(self) -> None:
        _validate_request(self)


@dataclass(frozen=True)
class ExistingDialogueTurnResult:
    status: ExistingDialogueTurnStatus
    job: TurnJobRecord | None
    dialogue: DialogueRecord | None
    output_payload: TransientPayloadRecord | None
    reason: ExistingDialogueTurnReason | None


class ModelCatalogPort(Protocol):
    async def get_catalog(self, profile_id: str, *, refresh: bool = False) -> CodexModelCatalog: ...


class TurnLifecyclePort(Protocol):
    async def start_turn(
        self,
        *,
        thread_binding: ThreadBinding,
        model_id: str,
        reasoning_effort: str,
        user_text: str,
        working_directory: TrustedWorkingDirectory,
    ) -> TurnStartResult: ...

    async def wait_turn(self, binding: TurnBinding) -> TurnTerminalResult: ...


class WorkingDirectoryResolver(Protocol):
    def resolve(self, profile_id: str) -> TrustedWorkingDirectory: ...


def _invalid() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.INVALID_ARGUMENT)


def _storage() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.STORAGE)


def _invariant() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.INVARIANT)


def _validate_request(request: object) -> None:
    if not isinstance(request, ExistingDialoguePromptRequest):
        raise _invalid()
    if type(request.update_id) is not int or not 0 <= request.update_id <= MAX_SIGNED_64:
        raise _invalid()
    if type(request.source_message_id) is not int or not 0 <= request.source_message_id <= MAX_SIGNED_64:
        raise _invalid()
    if type(request.source_chat_id) is not int or not MIN_SIGNED_64 <= request.source_chat_id <= MAX_SIGNED_64:
        raise _invalid()
    if request.source_chat_id == 0:
        raise _invalid()
    if not isinstance(request.text, str) or not request.text or "\x00" in request.text:
        raise _invalid()
    if len(request.text) > MAX_PROMPT_CHARS:
        raise _invalid()
    try:
        request.text.encode("utf-8")
    except UnicodeEncodeError:
        raise _invalid() from None


def _validate_service_string(value: object, *, limit: int = MAX_SERVICE_STRING_CHARS) -> None:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()


def _validate_clock(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise _storage() from None
    if type(value) is not int or not 0 <= value <= MAX_SIGNED_64:
        raise _storage()
    return value


def _expiry(now: int, retention: int) -> int:
    if now > MAX_SIGNED_64 - retention:
        raise _invariant()
    return now + retention


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _default_id_factory(kind: str) -> str:
    return f"p3-{kind}-{uuid4().hex}"


def _generated_id(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > MAX_SERVICE_STRING_CHARS:
        raise _invariant()
    return value


def _repository_error(error: BaseException) -> DialogueApplicationError:
    if isinstance(error, StorageError):
        return _storage()
    if isinstance(error, RepositoryError):
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.ALREADY_EXISTS:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invalid()
        return _storage()
    return _storage()


def _async_callable(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


def _close_awaitable(value: object) -> None:
    close = getattr(value, "close", None)
    if callable(close):
        close()


class ExistingDialogueTurnService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        profiles: tuple[CodexProfile, ...],
        model_catalog: ModelCatalogPort,
        turn_lifecycle: TurnLifecyclePort,
        working_directory_resolver: WorkingDirectoryResolver,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        _validate_service_string(server_id)
        if type(profiles) is not tuple:
            raise _invalid()
        profile_ids: set[str] = set()
        for profile in profiles:
            if not isinstance(profile, CodexProfile):
                raise _invalid()
            _validate_service_string(profile.profile_id)
            if profile.profile_id in profile_ids:
                raise _invalid()
            profile_ids.add(profile.profile_id)
        if not _async_callable(model_catalog, "get_catalog"):
            raise _invalid()
        if not _async_callable(turn_lifecycle, "start_turn") or not _async_callable(turn_lifecycle, "wait_turn"):
            raise _invalid()
        if not callable(getattr(working_directory_resolver, "resolve", None)):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if id_factory is not None and not callable(id_factory):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._profiles = profiles
        self._model_catalog = model_catalog
        self._turn_lifecycle = turn_lifecycle
        self._working_directory_resolver = working_directory_resolver
        self._clock = now_ms if now_ms is not None else _default_clock
        self._id_factory = id_factory if id_factory is not None else _default_id_factory

    def __repr__(self) -> str:
        return f"<ExistingDialogueTurnService server_id={self._server_id!r}>"

    async def execute(self, request: ExistingDialoguePromptRequest) -> ExistingDialogueTurnResult:
        _validate_request(request)
        try:
            ingress = await IngressUpdateRepository(self._storage).get(request.update_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if ingress is not None:
            return await self._duplicate(ingress)

        try:
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if dialogue is None:
            return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
        if dialogue.server_id != self._server_id:
            raise _invariant()
        if dialogue.state is DialogueState.TURN_RUNNING:
            return self._busy(dialogue)
        if dialogue.state is not DialogueState.IDLE:
            return self._blocked(dialogue, ExistingDialogueTurnReason.DIALOGUE_NOT_READY)
        if dialogue.thread_id is None:
            raise _invariant()

        try:
            settings = await SettingsRepository(self._storage).get()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if settings is None:
            return self._blocked(dialogue, ExistingDialogueTurnReason.SETTINGS_MISSING)
        if settings.profile_id is None or settings.profile_id != dialogue.profile_id:
            return self._blocked(dialogue, ExistingDialogueTurnReason.SETTINGS_PROFILE_MISMATCH)
        if not any(profile.profile_id == dialogue.profile_id for profile in self._profiles):
            return self._blocked(dialogue, ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED)
        if settings.model_id is None:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED)

        try:
            catalog = await self._model_catalog.get_catalog(dialogue.profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if not isinstance(catalog, CodexModelCatalog) or catalog.profile_id != dialogue.profile_id:
            if isinstance(catalog, CodexModelCatalog):
                raise _invariant()
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        try:
            descriptor = catalog.resolve_model(settings.model_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if not isinstance(getattr(descriptor, "hidden", None), bool) or descriptor.hidden:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        try:
            effort = catalog.validate_reasoning_effort(settings.model_id, settings.reasoning_effort)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if not isinstance(effort, str) or not effort or "\x00" in effort or len(effort) > MAX_REASONING_EFFORT_CHARS:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)

        try:
            working_directory = self._working_directory_resolver.resolve(dialogue.profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        if inspect.isawaitable(working_directory):
            _close_awaitable(working_directory)
            return self._blocked(dialogue, ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        if not isinstance(working_directory, TrustedWorkingDirectory):
            return self._blocked(dialogue, ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)

        job_id = self._make_id("job")
        input_id = self._make_id("input")
        now = _validate_clock(self._clock)
        input_expiry = _expiry(now, P3_INPUT_PAYLOAD_RETENTION_MS)
        jobs = TurnJobRepository(self._storage, now_ms=self._clock)
        try:
            admission = await jobs.claim_ingress(
                update_id=request.update_id,
                job_id=job_id,
                source_chat_id=request.source_chat_id,
                source_message_id=request.source_message_id,
                dialogue_id=dialogue.dialogue_id,
                server_id=dialogue.server_id,
                profile_id=dialogue.profile_id,
                thread_id=dialogue.thread_id,
                model_id=settings.model_id,
                reasoning_effort=effort,
                input_payload_id=input_id,
                input_content=request.text.encode("utf-8"),
                input_expires_at_ms=input_expiry,
            )
        except asyncio.CancelledError:
            raise
        except (StorageError, RepositoryError) as error:
            if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.STATE_CONFLICT:
                return await self._state_conflict_result()
            if isinstance(error, RepositoryError) and error.category is RepositoryErrorCategory.NOT_FOUND:
                return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
            raise _repository_error(error) from None
        if not isinstance(admission, TurnIngressClaimResult):
            raise _invariant()
        if admission.status is TurnIngressClaimStatus.DUPLICATE:
            return await self._admission_duplicate(admission)
        if admission.status is not TurnIngressClaimStatus.CREATED or admission.job is None:
            raise _invariant()

        owned = asyncio.create_task(self._run_admitted(admission.job, request.text, working_directory))
        return await self._await_owned(owned)

    async def _duplicate(self, ingress) -> ExistingDialogueTurnResult:
        try:
            if ingress.disposition is not IngressDispositionKind.JOB:
                dialogue = await DialogueRepository(self._storage).get_live()
                return ExistingDialogueTurnResult(
                    ExistingDialogueTurnStatus.DUPLICATE, None, dialogue, None,
                    ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
                )
            if ingress.job_id is None:
                raise _invariant()
            job = await TurnJobRepository(self._storage).get(ingress.job_id)
            if job is None:
                dialogue = await DialogueRepository(self._storage).get_live()
                if dialogue is None:
                    return ExistingDialogueTurnResult(
                        ExistingDialogueTurnStatus.DUPLICATE, None, None, None,
                        ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB,
                    )
                raise _invariant()
            if job.job_id != ingress.job_id or job.telegram_update_id != ingress.update_id:
                raise _invariant()
            try:
                payload = await TransientPayloadRepository(self._storage).get_input_for_job(job.job_id)
            except RepositoryError as error:
                if error.category is RepositoryErrorCategory.NOT_FOUND and job.state in INPUT_OPTIONAL_STATES:
                    payload = None
                elif error.category is RepositoryErrorCategory.NOT_FOUND:
                    raise _invariant()
                else:
                    raise
            if payload is not None:
                self._validate_input(job, payload)
            dialogue = await DialogueRepository(self._storage).get_live()
            return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.DUPLICATE, job, dialogue, None, None)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None

    async def _admission_duplicate(self, admission: TurnIngressClaimResult) -> ExistingDialogueTurnResult:
        ingress = admission.ingress
        if ingress.disposition is not IngressDispositionKind.JOB:
            dialogue = await self._live_dialogue_for_duplicate()
            return ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.DUPLICATE, None, dialogue, None,
                ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
            )
        job = admission.job
        if job is None or job.job_id != ingress.job_id or job.telegram_update_id != ingress.update_id:
            raise _invariant()
        if admission.input_payload is None:
            if job.state not in INPUT_OPTIONAL_STATES:
                raise _invariant()
        else:
            self._validate_input(job, admission.input_payload)
        dialogue = await self._live_dialogue_for_duplicate()
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.DUPLICATE, job, dialogue, None, None)

    async def _live_dialogue_for_duplicate(self) -> DialogueRecord | None:
        try:
            return await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None

    @staticmethod
    def _validate_input(job: TurnJobRecord, payload: TransientPayloadRecord) -> None:
        if (
            not isinstance(payload, TransientPayloadRecord)
            or payload.kind is not TransientPayloadKind.INPUT
            or payload.job_id != job.job_id
            or payload.dialogue_id != job.dialogue_id
            or payload.content_sha256 != job.input_sha256
        ):
            raise _invariant()

    async def _state_conflict_result(self) -> ExistingDialogueTurnResult:
        try:
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if dialogue is None:
            return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
        if dialogue.server_id != self._server_id:
            raise _invariant()
        if dialogue.state in (DialogueState.IDLE, DialogueState.TURN_RUNNING):
            return self._busy(dialogue)
        return self._blocked(dialogue, ExistingDialogueTurnReason.DIALOGUE_NOT_READY)

    async def _run_admitted(
        self, admitted: TurnJobRecord, user_text: str, working_directory: TrustedWorkingDirectory
    ) -> ExistingDialogueTurnResult:
        from ._turn_common import run_admitted_turn

        return await run_admitted_turn(
            storage=self._storage,
            clock=self._clock,
            id_factory=self._id_factory,
            turn_lifecycle=self._turn_lifecycle,
            admitted=admitted,
            user_text=user_text,
            working_directory=working_directory,
        )

    async def _await_owned(self, task: asyncio.Task[ExistingDialogueTurnResult]) -> ExistingDialogueTurnResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None

    def _make_id(self, kind: str) -> str:
        try:
            value = self._id_factory(kind)
        except Exception:
            raise _invariant() from None
        return _generated_id(value)

    @staticmethod
    def _busy(dialogue: DialogueRecord) -> ExistingDialogueTurnResult:
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BUSY, None, dialogue, None, None)

    @staticmethod
    def _blocked(dialogue, reason) -> ExistingDialogueTurnResult:
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, dialogue, None, reason)


def _lifecycle_name(error: TurnLifecycleError) -> str:
    category = getattr(error, "category", None)
    return getattr(category, "value", category)
