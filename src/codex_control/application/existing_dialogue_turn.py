"""P3.1 application service for a prompt on an existing dialogue.

This module deliberately owns orchestration only.  Durable state transitions
remain in the accepted P2 repositories and Codex behavior remains behind the
narrow P1 lifecycle ports below.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Protocol
from uuid import uuid4

from codex_control.adapters.codex.model_catalog import CodexModelCatalog
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnLifecycleError,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
    MAX_AGENT_MESSAGE_CHARS,
    MAX_AGENT_MESSAGES_PER_TURN,
    MAX_TOTAL_AGENT_MESSAGE_CHARS,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsRepository,
    SqliteStorage,
    MAX_TRANSIENT_PAYLOAD_BYTES,
    TransientPayloadKind,
    TransientPayloadRecord,
    TransientPayloadRepository,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnExecutionClaimResult,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobFinishResult,
    TurnTerminalOutcome,
    DialogueRecord,
)
from codex_control.storage.errors import StorageError


P3_INPUT_PAYLOAD_RETENTION_MS = 3_600_000
P3_COMPLETED_OUTPUT_RETENTION_MS = 3_600_000
P3_UNCERTAIN_OUTPUT_RETENTION_MS = 86_400_000
MAX_SIGNED_64 = 9_223_372_036_854_775_807
MIN_SIGNED_64 = -9_223_372_036_854_775_808
MAX_SERVICE_STRING_CHARS = 128
MAX_REASONING_EFFORT_CHARS = 64
MAX_PROMPT_CHARS = 65_536
MAX_PROJECTED_OUTPUT_BYTES = (
    MAX_TOTAL_AGENT_MESSAGE_CHARS * 4
    + (MAX_AGENT_MESSAGES_PER_TURN - 1) * 2
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


class DialogueApplicationErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    CODEX = "CODEX"
    INVARIANT = "INVARIANT"


class DialogueApplicationError(Exception):
    """Finite, content-free application diagnostic."""

    def __init__(self, category: DialogueApplicationErrorCategory | str) -> None:
        try:
            normalized = (
                category
                if isinstance(category, DialogueApplicationErrorCategory)
                else DialogueApplicationErrorCategory(category)
            )
        except (TypeError, ValueError):
            normalized = DialogueApplicationErrorCategory.INVARIANT
        self.category = normalized
        super().__init__(normalized.value)

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
    async def get_catalog(
        self, profile_id: str, *, refresh: bool = False
    ) -> CodexModelCatalog: ...


class TurnLifecyclePort(Protocol):
    async def start_turn(
        self,
        *,
        thread_binding: ThreadBinding,
        model_id: str,
        reasoning_effort: str | None,
        user_text: str,
        working_directory: TrustedWorkingDirectory,
    ) -> TurnStartResult: ...

    async def wait_turn(self, binding: TurnBinding) -> TurnTerminalResult: ...


class WorkingDirectoryResolver(Protocol):
    def resolve(self, profile_id: str) -> TrustedWorkingDirectory: ...


def _invalid() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.INVALID_ARGUMENT)


def _storage_failure() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.STORAGE)


def _invariant() -> DialogueApplicationError:
    return DialogueApplicationError(DialogueApplicationErrorCategory.INVARIANT)


def _validate_request(request: object) -> None:
    if not isinstance(request, ExistingDialoguePromptRequest):
        raise _invalid()
    if (
        type(request.update_id) is not int
        or not 0 <= request.update_id <= MAX_SIGNED_64
        or type(request.source_message_id) is not int
        or not 0 <= request.source_message_id <= MAX_SIGNED_64
        or type(request.source_chat_id) is not int
        or not MIN_SIGNED_64 <= request.source_chat_id <= MAX_SIGNED_64
        or request.source_chat_id == 0
    ):
        raise _invalid()
    if (
        not isinstance(request.text, str)
        or not request.text
        or "\x00" in request.text
        or len(request.text) > MAX_PROMPT_CHARS
    ):
        raise _invalid()
    try:
        request.text.encode("utf-8")
    except UnicodeEncodeError:
        raise _invalid() from None


def _validate_service_string(value: object, *, limit: int = MAX_SERVICE_STRING_CHARS) -> None:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > limit:
        raise _invalid()


def _validate_clock_value(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise _storage_failure() from None
    if type(value) is not int or not 0 <= value <= MAX_SIGNED_64:
        raise _storage_failure()
    return value


def _future_expiry(now: int, ttl: int) -> int:
    if now > MAX_SIGNED_64 - ttl:
        raise _invariant()
    return now + ttl


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _default_id_factory(kind: str) -> str:
    return f"p3-{kind}-{uuid4().hex}"


def _error_for_repository(error: BaseException) -> DialogueApplicationError:
    if isinstance(error, StorageError):
        return _storage_failure()
    if isinstance(error, RepositoryError):
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.ALREADY_EXISTS:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invalid()
        return _storage_failure()
    return _storage_failure()


def _validate_generated_id(value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > MAX_SERVICE_STRING_CHARS:
        raise _invariant()
    return value


def _lifecycle_category(error: TurnLifecycleError) -> str:
    category = getattr(error, "category", None)
    return getattr(category, "value", category)


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
        if type(storage) is not SqliteStorage:
            raise _invalid()
        _validate_service_string(server_id)
        if type(profiles) is not tuple:
            raise _invalid()
        profile_ids: set[str] = set()
        for profile in profiles:
            if type(profile) is not CodexProfile:
                raise _invalid()
            _validate_service_string(profile.profile_id)
            if profile.profile_id in profile_ids:
                raise _invalid()
            profile_ids.add(profile.profile_id)
        if not _has_async_method(model_catalog, "get_catalog"):
            raise _invalid()
        if not _has_async_method(turn_lifecycle, "start_turn") or not _has_async_method(turn_lifecycle, "wait_turn"):
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

        # This is intentionally the first operation after static validation.
        try:
            ingress = await IngressUpdateRepository(self._storage).get(request.update_id)
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
        if ingress is not None:
            return await self._duplicate(ingress)

        try:
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
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
            raise _error_for_repository(error) from None
        if settings is None:
            return self._blocked(dialogue, ExistingDialogueTurnReason.SETTINGS_MISSING)
        if settings.profile_id is None or settings.profile_id != dialogue.profile_id:
            return self._blocked(dialogue, ExistingDialogueTurnReason.SETTINGS_PROFILE_MISMATCH)
        profile = next((p for p in self._profiles if p.profile_id == dialogue.profile_id), None)
        if profile is None:
            return self._blocked(dialogue, ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED)
        if settings.model_id is None:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED)

        try:
            catalog = await self._model_catalog.get_catalog(dialogue.profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        try:
            catalog_profile_id = catalog.profile_id
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if catalog_profile_id != dialogue.profile_id:
            raise _invariant()
        validator = getattr(catalog, "validate_reasoning_effort", None)
        if not callable(validator):
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        try:
            effort = validator(settings.model_id, settings.reasoning_effort)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if (
            not isinstance(effort, str)
            or not effort
            or "\x00" in effort
            or len(effort) > MAX_REASONING_EFFORT_CHARS
        ):
            return self._blocked(dialogue, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)

        resolver = getattr(self._working_directory_resolver, "resolve", None)
        try:
            working_directory = resolver(dialogue.profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(dialogue, ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        if not isinstance(working_directory, TrustedWorkingDirectory):
            _close_unawaited(working_directory)
            return self._blocked(dialogue, ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)

        # IDs and the INPUT expiry are deliberately reached only after all
        # configuration/effect preflight has succeeded.
        job_id = self._generated_id("job")
        input_payload_id = self._generated_id("input")
        now = _validate_clock_value(self._clock)
        input_expires_at_ms = _future_expiry(now, P3_INPUT_PAYLOAD_RETENTION_MS)
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
                input_payload_id=input_payload_id,
                input_content=request.text.encode("utf-8"),
                input_expires_at_ms=input_expires_at_ms,
            )
        except asyncio.CancelledError:
            raise
        except RepositoryError as error:
            if error.category is RepositoryErrorCategory.STATE_CONFLICT:
                return await self._state_conflict_result()
            if error.category is RepositoryErrorCategory.NOT_FOUND:
                return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
            raise _error_for_repository(error) from None
        except StorageError as error:
            raise _error_for_repository(error) from None
        if not isinstance(admission, TurnIngressClaimResult):
            raise _invariant()
        if admission.status is TurnIngressClaimStatus.DUPLICATE:
            return self._admission_duplicate(admission)
        if admission.status is not TurnIngressClaimStatus.CREATED or admission.job is None:
            raise _invariant()

        # The task is created synchronously immediately after the durable
        # admission returns.  Everything after this point is owned by it.
        owned = asyncio.create_task(
            self._run_admitted(
                admission.job,
                request.text,
                working_directory,
            )
        )
        return await self._await_owned(owned)

    async def _duplicate(self, ingress) -> ExistingDialogueTurnResult:
        try:
            if ingress.disposition is not IngressDispositionKind.JOB:
                dialogue = await DialogueRepository(self._storage).get_live()
                return ExistingDialogueTurnResult(
                    ExistingDialogueTurnStatus.DUPLICATE,
                    None,
                    dialogue,
                    None,
                    ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
                )
            if ingress.job_id is None:
                raise _invariant()
            jobs = TurnJobRepository(self._storage)
            job = await jobs.get(ingress.job_id)
            if job is None:
                dialogue = await DialogueRepository(self._storage).get_live()
                if dialogue is None:
                    return ExistingDialogueTurnResult(
                        ExistingDialogueTurnStatus.DUPLICATE,
                        None,
                        None,
                        None,
                        ExistingDialogueTurnReason.DUPLICATE_ORPHAN_JOB,
                    )
                raise _invariant()
            if job.job_id != ingress.job_id or job.telegram_update_id != ingress.update_id:
                raise _invariant()
            payload = await TransientPayloadRepository(self._storage).get_input_for_job(job.job_id)
            if (
                payload.job_id != job.job_id
                or payload.dialogue_id != job.dialogue_id
                or payload.kind is not TransientPayloadKind.INPUT
                or payload.content_sha256 != job.input_sha256
            ):
                raise _invariant()
            dialogue = await DialogueRepository(self._storage).get_live()
            return ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.DUPLICATE, job, dialogue, None, None
            )
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None

    def _admission_duplicate(self, admission: TurnIngressClaimResult) -> ExistingDialogueTurnResult:
        ingress = admission.ingress
        if ingress.disposition is not IngressDispositionKind.JOB:
            return ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.DUPLICATE,
                None,
                None,
                None,
                ExistingDialogueTurnReason.DUPLICATE_NON_JOB,
            )
        if admission.job is None or admission.input_payload is None:
            raise _invariant()
        if (
            admission.job.job_id != ingress.job_id
            or admission.job.telegram_update_id != ingress.update_id
            or admission.input_payload.job_id != admission.job.job_id
            or admission.input_payload.dialogue_id != admission.job.dialogue_id
            or admission.input_payload.kind is not TransientPayloadKind.INPUT
            or admission.input_payload.content_sha256 != admission.job.input_sha256
        ):
            raise _invariant()
        return ExistingDialogueTurnResult(
            ExistingDialogueTurnStatus.DUPLICATE, admission.job, None, None, None
        )

    async def _state_conflict_result(self) -> ExistingDialogueTurnResult:
        try:
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
        if dialogue is None:
            return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
        if dialogue.server_id != self._server_id:
            raise _invariant()
        if dialogue.state in (DialogueState.IDLE, DialogueState.TURN_RUNNING):
            return self._busy(dialogue)
        return self._blocked(dialogue, ExistingDialogueTurnReason.DIALOGUE_NOT_READY)

    async def _run_admitted(
        self,
        admitted_job: TurnJobRecord,
        user_text: str,
        working_directory: TrustedWorkingDirectory,
    ) -> ExistingDialogueTurnResult:
        jobs = TurnJobRepository(self._storage, now_ms=self._clock)
        try:
            current = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
        if current is None:
            raise _invariant()
        if (
            current.dialogue_id != admitted_job.dialogue_id
            or current.server_id != admitted_job.server_id
            or current.profile_id != admitted_job.profile_id
            or current.thread_id != admitted_job.thread_id
            or current.state is not DialogueState.IDLE
        ):
            raise _invariant()
        if current.thread_id is None:
            raise _invariant()
        try:
            claimed = await jobs.claim_turn(
                job_id=admitted_job.job_id,
                expected_job_version=admitted_job.version,
                expected_dialogue_version=current.version,
                thread_id=current.thread_id,
            )
            if not isinstance(claimed, TurnExecutionClaimResult):
                raise _invariant()
            starting = await jobs.mark_codex_starting(
                job_id=admitted_job.job_id,
                expected_version=claimed.job.version,
            )
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
        if not isinstance(claimed.job, TurnJobRecord) or not isinstance(claimed.dialogue, DialogueRecord):
            raise _invariant()
        if not isinstance(starting, TurnJobRecord):
            raise _invariant()
        if (
            not isinstance(claimed.dialogue.thread_id, str)
            or not isinstance(starting.model_id, str)
            or not starting.model_id
            or "\x00" in starting.model_id
            or not isinstance(starting.reasoning_effort, str)
            or not starting.reasoning_effort
            or "\x00" in starting.reasoning_effort
            or len(starting.reasoning_effort) > MAX_REASONING_EFFORT_CHARS
        ):
            raise _invariant()
        # The repository's mark_codex_starting returns only the job.  The
        # claimed dialogue is the exact durable binding and version for this
        # execution path.
        try:
            thread_binding = ThreadBinding(claimed.dialogue.profile_id, claimed.dialogue.thread_id)
        except Exception:
            raise _invariant() from None
        job = starting
        dialogue = claimed.dialogue
        start_result: TurnStartResult
        try:
            start_result = await self._turn_lifecycle.start_turn(
                thread_binding=thread_binding,
                model_id=job.model_id,
                reasoning_effort=job.reasoning_effort,
                user_text=user_text,
                working_directory=working_directory,
            )
        except asyncio.CancelledError:
            raise
        except TurnLifecycleError as error:
            if _lifecycle_category(error) in {
                "turn_request_invalid",
                "turn_precondition_changed",
                "turn_operation_busy",
            }:
                return await self._finish_from_starting(
                    jobs, job, dialogue, TurnTerminalOutcome.FAILED, "CODEX_PROCESS", None
                )
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        except Exception:
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )

        if not isinstance(start_result, TurnStartResult):
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        if start_result.status is TurnStartStatus.REJECTED:
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.FAILED, "CODEX_TURN_FAILED", None
            )
        if start_result.status is TurnStartStatus.UNKNOWN:
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        if start_result.status is not TurnStartStatus.CONFIRMED:
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        binding = start_result.binding
        if (
            not isinstance(binding, TurnBinding)
            or binding.profile_id != job.profile_id
            or binding.thread_id != job.thread_id
        ):
            return await self._finish_from_starting(
                jobs, job, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        try:
            running = await jobs.mark_codex_running(
                job_id=job.job_id,
                expected_version=job.version,
                codex_turn_id=binding.turn_id,
            )
        except (StorageError, RepositoryError) as error:
            return await self._finish_after_running_bind_failure(
                jobs, job, dialogue, error
            )
        if not isinstance(running, TurnJobRecord):
            return await self._finish_after_running_bind_failure(
                jobs, job, dialogue, _invariant()
            )

        terminal: TurnTerminalResult | None
        try:
            terminal = await self._turn_lifecycle.wait_turn(binding)
        except asyncio.CancelledError:
            raise
        except Exception:
            terminal = None
        outcome, error_class, messages = self._terminal_projection(terminal, binding)
        return await self._finish_terminal(
            jobs, running, dialogue, outcome, error_class, messages
        )

    async def _finish_after_running_bind_failure(
        self,
        jobs: TurnJobRepository,
        starting: TurnJobRecord,
        dialogue: DialogueRecord,
        error: BaseException,
    ) -> ExistingDialogueTurnResult:
        try:
            return await self._finish_from_starting(
                jobs, starting, dialogue, TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", None
            )
        except DialogueApplicationError:
            if isinstance(error, (StorageError, RepositoryError)):
                raise _error_for_repository(error) from None
            raise _invariant() from None

    def _terminal_projection(
        self, terminal: TurnTerminalResult | None, binding: TurnBinding
    ) -> tuple[TurnTerminalOutcome, str | None, tuple[AgentMessageCompleted, ...]]:
        if (
            not isinstance(terminal, TurnTerminalResult)
            or terminal.binding is not binding
            or not isinstance(terminal.messages, tuple)
            or len(terminal.messages) > MAX_AGENT_MESSAGES_PER_TURN
            or any(not isinstance(message, AgentMessageCompleted) for message in terminal.messages)
        ):
            return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
        for message in terminal.messages:
            if not isinstance(message.text, str) or len(message.text) > MAX_AGENT_MESSAGE_CHARS:
                return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
        if sum(len(message.text) for message in terminal.messages) > MAX_TOTAL_AGENT_MESSAGE_CHARS:
            return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()
        if terminal.status is TurnTerminalStatus.COMPLETED:
            return TurnTerminalOutcome.COMPLETED, None, terminal.messages
        if terminal.status is TurnTerminalStatus.FAILED:
            return TurnTerminalOutcome.FAILED, "CODEX_TURN_FAILED", terminal.messages
        if terminal.status is TurnTerminalStatus.UNKNOWN:
            return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", terminal.messages
        return TurnTerminalOutcome.UNKNOWN, "CODEX_AMBIGUOUS", ()

    async def _finish_from_starting(
        self,
        jobs: TurnJobRepository,
        job: TurnJobRecord,
        dialogue: DialogueRecord,
        outcome: TurnTerminalOutcome,
        error_class: str,
        messages: tuple[AgentMessageCompleted, ...] | None,
    ) -> ExistingDialogueTurnResult:
        return await self._finish_terminal(jobs, job, dialogue, outcome, error_class, messages)

    async def _finish_terminal(
        self,
        jobs: TurnJobRepository,
        job: TurnJobRecord,
        dialogue: DialogueRecord,
        outcome: TurnTerminalOutcome,
        error_class: str | None,
        messages: tuple[AgentMessageCompleted, ...] | None,
    ) -> ExistingDialogueTurnResult:
        output = b""
        if messages:
            try:
                output = "\n\n".join(message.text for message in messages).encode("utf-8")
            except UnicodeEncodeError:
                raise _invariant() from None
            if len(output) > MAX_TRANSIENT_PAYLOAD_BYTES or len(output) > MAX_PROJECTED_OUTPUT_BYTES:
                raise _invariant()
        output_id: str | None = None
        output_expiry: int | None = None
        if output:
            now = _validate_clock_value(self._clock)
            ttl = (
                P3_COMPLETED_OUTPUT_RETENTION_MS
                if outcome is TurnTerminalOutcome.COMPLETED
                else P3_UNCERTAIN_OUTPUT_RETENTION_MS
            )
            output_expiry = _future_expiry(now, ttl)
            output_id = self._generated_id("output")
        try:
            finished: TurnJobFinishResult = await jobs.finish_codex(
                job_id=job.job_id,
                expected_job_version=job.version,
                expected_dialogue_version=dialogue.version,
                outcome=outcome,
                error_class=error_class,
                output_payload_id=output_id,
                output_content=output if output_id is not None else None,
                output_expires_at_ms=output_expiry,
            )
        except (StorageError, RepositoryError) as error:
            raise _error_for_repository(error) from None
        if not isinstance(finished, TurnJobFinishResult):
            raise _invariant()
        status = {
            TurnTerminalOutcome.COMPLETED: ExistingDialogueTurnStatus.COMPLETED,
            TurnTerminalOutcome.FAILED: ExistingDialogueTurnStatus.FAILED,
            TurnTerminalOutcome.UNKNOWN: ExistingDialogueTurnStatus.UNKNOWN,
        }[outcome]
        return ExistingDialogueTurnResult(
            status, finished.job, finished.dialogue, finished.output_payload, None
        )

    async def _await_owned(self, task: asyncio.Task[ExistingDialogueTurnResult]) -> ExistingDialogueTurnResult:
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None
                continue

    def _generated_id(self, kind: str) -> str:
        try:
            value = self._id_factory(kind)
        except Exception:
            raise _invariant() from None
        return _validate_generated_id(value)

    @staticmethod
    def _busy(dialogue: DialogueRecord) -> ExistingDialogueTurnResult:
        return ExistingDialogueTurnResult(
            ExistingDialogueTurnStatus.BUSY, None, dialogue, None, None
        )

    @staticmethod
    def _blocked(
        dialogue: DialogueRecord | None, reason: ExistingDialogueTurnReason
    ) -> ExistingDialogueTurnResult:
        return ExistingDialogueTurnResult(
            ExistingDialogueTurnStatus.BLOCKED, None, dialogue, None, reason
        )


def _has_async_method(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and inspect.iscoroutinefunction(method)


def _close_unawaited(value: object) -> None:
    close = getattr(value, "close", None)
    if callable(close):
        close()
