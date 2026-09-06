"""Lazy first-dialogue creation and startup create recovery."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable, Protocol

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeletionRepository,
    DialogueRecord,
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRecord,
    IngressUpdateRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SettingsRepository,
    SettingsDialogueGuardRepository,
    SqliteStorage,
    TurnIngressClaimResult,
    TurnIngressClaimStatus,
    TurnJobRecord,
    TurnJobRepository,
    TurnJobState,
    TransientPayloadKind,
    TransientPayloadRecord,
)
from codex_control.storage.errors import StorageError

from .existing_dialogue_turn import (
    DialogueApplicationError,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
    ModelCatalogPort,
    TurnLifecyclePort,
    WorkingDirectoryResolver,
    _async_callable,
    _default_clock,
    _default_id_factory,
    _expiry,
    _generated_id,
    _invariant,
    _repository_error,
    _validate_clock,
    _validate_service_string,
    MAX_REASONING_EFFORT_CHARS,
    P3_INPUT_PAYLOAD_RETENTION_MS,
)

from ._turn_common import run_admitted_turn
from .active_turn_registry import ActiveTurnRegistry


class ThreadLifecyclePort(Protocol):
    async def start(
        self,
        profile_id: str,
        *,
        model_id: str,
        reasoning_effort: str | None,
        working_directory: TrustedWorkingDirectory,
    ) -> ThreadOperationResult: ...


class CreationRecoveryStatus(StrEnum):
    NO_ACTION = "NO_ACTION"
    MARKED_UNKNOWN = "MARKED_UNKNOWN"


@dataclass(frozen=True)
class CreationRecoveryResult:
    status: CreationRecoveryStatus
    dialogue: DialogueRecord | None


class DialogueTurnService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        profiles: tuple[CodexProfile, ...],
        model_catalog: ModelCatalogPort,
        thread_lifecycle: ThreadLifecyclePort,
        turn_lifecycle: TurnLifecyclePort,
        working_directory_resolver: WorkingDirectoryResolver,
        now_ms: Callable[[], int] | None = None,
        id_factory: Callable[[str], str] | None = None,
        active_turn_registry: ActiveTurnRegistry | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise DialogueApplicationError("INVALID_ARGUMENT")
        _validate_service_string(server_id)
        if not _async_callable(thread_lifecycle, "start"):
            raise DialogueApplicationError("INVALID_ARGUMENT")
        if now_ms is not None and not callable(now_ms):
            raise DialogueApplicationError("INVALID_ARGUMENT")
        if id_factory is not None and not callable(id_factory):
            raise DialogueApplicationError("INVALID_ARGUMENT")
        if active_turn_registry is not None and type(active_turn_registry) is not ActiveTurnRegistry:
            raise DialogueApplicationError("INVALID_ARGUMENT")
        self._storage = storage
        self._server_id = server_id
        self._profiles = profiles
        self._model_catalog = model_catalog
        self._thread_lifecycle = thread_lifecycle
        self._turn_lifecycle = turn_lifecycle
        self._working_directory_resolver = working_directory_resolver
        self._clock = now_ms if now_ms is not None else _default_clock
        self._id_factory = id_factory if id_factory is not None else _default_id_factory
        self._active_turn_registry = active_turn_registry if active_turn_registry is not None else ActiveTurnRegistry()
        # This is the single accepted existing-dialogue authority used for
        # the mandatory top-level delegation and all race re-evaluations.
        self._existing = ExistingDialogueTurnService(
            storage,
            server_id=server_id,
            profiles=profiles,
            model_catalog=model_catalog,
            turn_lifecycle=turn_lifecycle,
            working_directory_resolver=working_directory_resolver,
            now_ms=self._clock,
            id_factory=self._id_factory,
            active_turn_registry=self._active_turn_registry,
        )

    def __repr__(self) -> str:
        return f"<DialogueTurnService server_id={self._server_id!r}>"

    async def execute(self, request: ExistingDialoguePromptRequest) -> ExistingDialogueTurnResult:
        existing = await self._existing.execute(request)
        if not (
            isinstance(existing, ExistingDialogueTurnResult)
            and existing.status is ExistingDialogueTurnStatus.BLOCKED
            and existing.reason is ExistingDialogueTurnReason.NO_DIALOGUE
            and existing.job is None
        ):
            return existing

        settings = await self._settings()
        if settings is None:
            return self._blocked(None, ExistingDialogueTurnReason.SETTINGS_MISSING)
        profile_id = settings.profile_id
        if profile_id is None or not any(profile.profile_id == profile_id for profile in self._profiles):
            return self._blocked(None, ExistingDialogueTurnReason.PROFILE_NOT_CONFIGURED)
        if settings.model_id is None:
            return self._blocked(None, ExistingDialogueTurnReason.MODEL_NOT_CONFIGURED)

        catalog = await self._catalog(profile_id)
        if type(catalog) is not CodexModelCatalog or catalog.profile_id != profile_id:
            if type(catalog) is CodexModelCatalog:
                raise _invariant()
            return self._blocked(None, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        try:
            descriptor = catalog.resolve_model(settings.model_id)
            if type(descriptor) is not CodexModelDescriptor or descriptor.hidden:
                return self._blocked(None, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
            effort = catalog.validate_reasoning_effort(settings.model_id, settings.reasoning_effort)
        except asyncio.CancelledError:
            raise
        except Exception:
            return self._blocked(None, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)
        if not isinstance(effort, str) or not effort or "\x00" in effort or len(effort) > MAX_REASONING_EFFORT_CHARS:
            return self._blocked(None, ExistingDialogueTurnReason.MODEL_UNAVAILABLE)

        try:
            working_directory = self._resolve_workdir(profile_id)
        except _WorkdirBlocked as blocked:
            return self._blocked(None, blocked.reason)
        dialogue_id = self._make_id("dialogue")
        job_id = self._make_id("job")
        input_id = self._make_id("input")
        now = _validate_clock(self._clock)
        input_expiry = _expiry(now, P3_INPUT_PAYLOAD_RETENTION_MS)
        try:
            tombstone = await DeletionRepository(self._storage).get_tombstone(dialogue_id)
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if tombstone is not None:
            raise _invariant()

        owned = asyncio.create_task(self._create_and_run(
            request=request,
            profile_id=profile_id,
            model_id=settings.model_id,
            reasoning_effort=effort,
            expected_settings_version=settings.version,
            expected_model_id=settings.model_id,
            expected_reasoning_effort=settings.reasoning_effort,
            working_directory=working_directory,
            dialogue_id=dialogue_id,
            job_id=job_id,
            input_id=input_id,
            input_expiry=input_expiry,
        ))
        return await self._await_owned(owned)

    async def recover_preexisting_creation(self) -> CreationRecoveryResult:
        repository = DialogueRepository(self._storage, now_ms=self._clock)
        try:
            current = await repository.get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if current is None or current.state is not DialogueState.CREATING:
            return CreationRecoveryResult(CreationRecoveryStatus.NO_ACTION, current)
        try:
            marked = await repository.mark_create_unknown(
                dialogue_id=current.dialogue_id,
                expected_version=current.version,
                error_class="CODEX_AMBIGUOUS",
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if (
            type(marked) is not DialogueRecord
            or marked.dialogue_id != current.dialogue_id
            or marked.state is not DialogueState.CREATE_UNKNOWN
            or marked.thread_id is not None
            or marked.last_error_class != "CODEX_AMBIGUOUS"
        ):
            raise _invariant()
        return CreationRecoveryResult(CreationRecoveryStatus.MARKED_UNKNOWN, marked)

    async def _settings(self):
        try:
            return await SettingsRepository(self._storage).get()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None

    async def _catalog(self, profile_id: str):
        try:
            return await self._model_catalog.get_catalog(profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            return None

    def _resolve_workdir(self, profile_id: str) -> TrustedWorkingDirectory:
        try:
            value = self._working_directory_resolver.resolve(profile_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            raise _blocked_error(ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        if inspect.isawaitable(value):
            try:
                close = getattr(value, "close", None)
                if callable(close):
                    close()
            except Exception:
                pass
            raise _blocked_error(ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        if type(value) is not TrustedWorkingDirectory:
            raise _blocked_error(ExistingDialogueTurnReason.WORKING_DIRECTORY_UNAVAILABLE)
        return value

    async def _create_and_run(
        self,
        *,
        request,
        profile_id,
        model_id,
        reasoning_effort,
        expected_settings_version,
        expected_model_id,
        expected_reasoning_effort,
        working_directory,
        dialogue_id,
        job_id,
        input_id,
        input_expiry,
    ):
        dialogues = DialogueRepository(self._storage, now_ms=self._clock)
        try:
            created = await SettingsDialogueGuardRepository(self._storage, now_ms=self._clock).create_dialogue_if_settings_current(
                dialogue_id=dialogue_id,
                server_id=self._server_id,
                profile_id=profile_id,
                expected_settings_version=expected_settings_version,
                expected_model_id=expected_model_id,
                expected_reasoning_effort=expected_reasoning_effort,
            )
        except RepositoryError as error:
            if error.category is RepositoryErrorCategory.ALREADY_EXISTS:
                return await self._race_loss_result(request)
            if error.category is RepositoryErrorCategory.VERSION_CONFLICT:
                return self._blocked(None, ExistingDialogueTurnReason.SETTINGS_CHANGED)
            raise _repository_error(error) from None
        except StorageError as error:
            raise _repository_error(error) from None
        except Exception as error:
            raise _repository_error(error) from None
        if (
            type(created) is not DialogueRecord
            or created.dialogue_id != dialogue_id
            or created.server_id != self._server_id
            or created.profile_id != profile_id
            or created.state is not DialogueState.CREATING
            or created.thread_id is not None
            or created.version != 0
            or created.last_error_class is not None
        ):
            raise _invariant()

        jobs = TurnJobRepository(self._storage, now_ms=self._clock)
        try:
            admission = await jobs.claim_ingress(
                update_id=request.update_id,
                job_id=job_id,
                source_chat_id=request.source_chat_id,
                source_message_id=request.source_message_id,
                dialogue_id=created.dialogue_id,
                server_id=created.server_id,
                profile_id=created.profile_id,
                thread_id=None,
                model_id=model_id,
                reasoning_effort=reasoning_effort,
                input_payload_id=input_id,
                input_content=request.text.encode("utf-8"),
                input_expires_at_ms=input_expiry,
            )
        except RepositoryError as error:
            if error.category is RepositoryErrorCategory.ALREADY_EXISTS:
                await self._admission_failure(dialogues, created)
                raise _invariant() from None
            if error.category is RepositoryErrorCategory.STATE_CONFLICT:
                return await self._race_loss_result(request)
            raise _repository_error(error) from None
        except StorageError as error:
            raise _repository_error(error) from None
        except Exception as error:
            raise _repository_error(error) from None
        if not isinstance(admission, TurnIngressClaimResult):
            await self._admission_failure(dialogues, created)
            raise _invariant()
        if admission.status is TurnIngressClaimStatus.DUPLICATE:
            return await self._existing._admission_duplicate(admission)
        if (
            admission.status is not TurnIngressClaimStatus.CREATED
            or type(admission.ingress) is not IngressUpdateRecord
            or admission.ingress.update_id != request.update_id
            or admission.ingress.disposition is not IngressDispositionKind.JOB
            or admission.ingress.job_id != job_id
            or type(admission.job) is not TurnJobRecord
            or admission.job.job_id != job_id
            or admission.job.telegram_update_id != request.update_id
            or admission.job.source_chat_id != request.source_chat_id
            or admission.job.source_message_id != request.source_message_id
            or admission.job.dialogue_id != created.dialogue_id
            or admission.job.server_id != self._server_id
            or admission.job.profile_id != profile_id
            or admission.job.thread_id is not None
            or admission.job.model_id != model_id
            or admission.job.reasoning_effort != reasoning_effort
            or admission.job.state is not TurnJobState.RECEIVED
            or admission.job.version != 0
            or admission.job.codex_turn_id is not None
            or admission.job.error_class is not None
            or admission.input_payload is None
            or type(admission.input_payload) is not TransientPayloadRecord
            or admission.input_payload.payload_id != input_id
            or admission.input_payload.dialogue_id != created.dialogue_id
            or admission.input_payload.job_id != job_id
            or admission.input_payload.kind is not TransientPayloadKind.INPUT
            or admission.input_payload.content != request.text.encode("utf-8")
            or admission.input_payload.content_sha256 != hashlib.sha256(request.text.encode("utf-8")).hexdigest()
        ):
            await self._admission_failure(dialogues, created)
            raise _invariant()

        admitted = admission.job
        try:
            started = await self._thread_lifecycle.start(
                created.profile_id,
                model_id=admitted.model_id,
                reasoning_effort=admitted.reasoning_effort,
                working_directory=working_directory,
            )
        except asyncio.CancelledError:
            return await self._mark_unknown(dialogues, created, admitted)
        except ThreadLifecycleError as error:
            if _thread_lifecycle_name(error) in {
                "thread_request_invalid",
                "thread_precondition_changed",
                "thread_operation_busy",
            }:
                return await self._mark_error(dialogues, created, admitted, "CODEX_PROCESS")
            return await self._mark_unknown(dialogues, created, admitted)
        except Exception:
            return await self._mark_unknown(dialogues, created, admitted)

        if type(started) is not ThreadOperationResult:
            return await self._mark_unknown(dialogues, created, admitted)
        if started.status is ThreadOperationStatus.START_REJECTED:
            return await self._mark_error(dialogues, created, admitted, "CODEX_THREAD_FAILED")
        if started.status is ThreadOperationStatus.START_UNKNOWN:
            return await self._mark_unknown(dialogues, created, admitted)
        if (
            started.status is not ThreadOperationStatus.START_CONFIRMED
            or type(started.binding) is not ThreadBinding
            or started.binding.profile_id != admitted.profile_id
            or started.model_id != admitted.model_id
            or started.reasoning_effort != admitted.reasoning_effort
        ):
            return await self._mark_unknown(dialogues, created, admitted)

        binding = started.binding
        try:
            confirmed = await dialogues.confirm_created(
                dialogue_id=created.dialogue_id,
                expected_version=created.version,
                thread_id=binding.thread_id,
            )
        except BaseException:
            return await self._reconcile_confirmation(dialogues, created, admitted, binding, request, working_directory)
        if not _exact_confirmed_dialogue(confirmed, created, binding):
            return await self._reconcile_confirmation(dialogues, created, admitted, binding, request, working_directory)
        return await run_admitted_turn(
            storage=self._storage,
            clock=self._clock,
            id_factory=self._id_factory,
            turn_lifecycle=self._turn_lifecycle,
            active_turn_registry=self._active_turn_registry,
            admitted=admitted,
            user_text=request.text,
            working_directory=working_directory,
        )

    async def _admission_failure(self, dialogues, created) -> None:
        try:
            marked = await dialogues.mark_create_error(
                dialogue_id=created.dialogue_id,
                expected_version=created.version,
                error_class="APPLICATION_ADMISSION_FAILED",
            )
            if type(marked) is not DialogueRecord or marked.state is not DialogueState.ERROR:
                raise _invariant()
        except BaseException:
            # The application admission invariant is the primary finite
            # failure; if terminalization could not commit, recovery evidence
            # remains in the still-CREATING row.
            raise _invariant() from None

    async def _race_loss_result(self, request: ExistingDialoguePromptRequest) -> ExistingDialogueTurnResult:
        """Reconstruct a lost first-path race without admitting new work.

        This invocation already lost its original no-dialogue admission
        attempt.  Reading the current canonical state is only for reporting;
        it must never hand the request back to the effect-capable existing
        dialogue service, because that could turn a delayed loser into a
        later prompt.
        """
        try:
            ingress = await IngressUpdateRepository(self._storage).get(request.update_id)
            if ingress is not None:
                return await self._existing._duplicate(ingress)
            dialogue = await DialogueRepository(self._storage).get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if dialogue is None:
            return self._blocked(None, ExistingDialogueTurnReason.NO_DIALOGUE)
        if dialogue.server_id != self._server_id:
            raise _invariant()
        if dialogue.state in (DialogueState.IDLE, DialogueState.TURN_RUNNING):
            return ExistingDialogueTurnResult(
                ExistingDialogueTurnStatus.BUSY, None, dialogue, None, None
            )
        return self._blocked(dialogue, ExistingDialogueTurnReason.DIALOGUE_NOT_READY)

    async def _mark_error(self, dialogues, created, job, error_class):
        try:
            dialogue = await dialogues.mark_create_error(
                dialogue_id=created.dialogue_id,
                expected_version=created.version,
                error_class=error_class,
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception as error:
            raise _repository_error(error) from None
        if (
            type(dialogue) is not DialogueRecord
            or dialogue.state is not DialogueState.ERROR
            or dialogue.thread_id is not None
            or dialogue.last_error_class != error_class
        ):
            raise _invariant()
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.FAILED, job, dialogue, None, None)

    async def _mark_unknown(self, dialogues, created, job):
        try:
            dialogue = await dialogues.mark_create_unknown(
                dialogue_id=created.dialogue_id,
                expected_version=created.version,
                error_class="CODEX_AMBIGUOUS",
            )
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        except Exception as error:
            raise _repository_error(error) from None
        if (
            type(dialogue) is not DialogueRecord
            or dialogue.state is not DialogueState.CREATE_UNKNOWN
            or dialogue.thread_id is not None
            or dialogue.last_error_class != "CODEX_AMBIGUOUS"
        ):
            raise _invariant()
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.UNKNOWN, job, dialogue, None, None)

    async def _reconcile_confirmation(self, dialogues, created, admitted, binding, request, working_directory):
        try:
            current = await dialogues.get_live()
        except (StorageError, RepositoryError) as error:
            raise _repository_error(error) from None
        if current is None:
            raise _invariant()
        if _exact_confirmed_dialogue(current, created, binding):
            return await run_admitted_turn(
                storage=self._storage,
                clock=self._clock,
                id_factory=self._id_factory,
                turn_lifecycle=self._turn_lifecycle,
                admitted=admitted,
                user_text=request.text,
                working_directory=working_directory,
            )
        if (
            current.dialogue_id == created.dialogue_id
            and current.state is DialogueState.CREATE_UNKNOWN
            and current.thread_id is None
        ):
            return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.UNKNOWN, admitted, current, None, None)
        if (
            current.dialogue_id == created.dialogue_id
            and current.server_id == created.server_id
            and current.profile_id == created.profile_id
            and current.state is DialogueState.CREATING
            and current.thread_id is None
            and current.version == created.version
        ):
            try:
                marked = await dialogues.mark_create_unknown(
                    dialogue_id=current.dialogue_id,
                    expected_version=current.version,
                    error_class="CODEX_AMBIGUOUS",
                )
            except (StorageError, RepositoryError) as error:
                raise _repository_error(error) from None
            except Exception as error:
                raise _repository_error(error) from None
            if type(marked) is not DialogueRecord or marked.state is not DialogueState.CREATE_UNKNOWN:
                raise _invariant()
            return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.UNKNOWN, admitted, marked, None, None)
        raise _invariant()

    async def _await_owned(self, task):
        while True:
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                if task.cancelled():
                    raise _invariant() from None

    def _make_id(self, kind: str) -> str:
        try:
            return _generated_id(self._id_factory(kind))
        except Exception:
            raise _invariant() from None

    @staticmethod
    def _blocked(dialogue, reason):
        return ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, dialogue, None, reason)


def _blocked_error(reason: ExistingDialogueTurnReason) -> _WorkdirBlocked:
    # A private sentinel exception keeps the synchronous resolver's failure
    # path separate from the public finite result construction.
    return _WorkdirBlocked(reason)


class _WorkdirBlocked(Exception):
    def __init__(self, reason):
        self.reason = reason


def _thread_lifecycle_name(error: ThreadLifecycleError) -> str:
    category = getattr(error, "category", None)
    return getattr(category, "value", category)


def _exact_confirmed_dialogue(value, created: DialogueRecord, binding: ThreadBinding) -> bool:
    return (
        type(value) is DialogueRecord
        and value.dialogue_id == created.dialogue_id
        and value.server_id == created.server_id
        and value.profile_id == created.profile_id
        and value.state is DialogueState.IDLE
        and value.thread_id == binding.thread_id
        and value.last_error_class is None
    )
