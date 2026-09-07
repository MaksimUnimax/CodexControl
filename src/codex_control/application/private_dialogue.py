"""P4.2 private dialogue status and confirmed hard-delete control."""

from __future__ import annotations

import hashlib
import inspect
import re
import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from codex_control.domain import ControllerMode
from codex_control.storage import (
    CallbackActionRecord,
    CallbackActionRepository,
    CallbackClaimStatus,
    DeleteConfirmationRevocationResult,
    DeleteConfirmationRevocationStatus,
    DialogueState,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
    SettingsRepository,
    TurnJobState,
)
from codex_control.storage.application_recovery import (
    ApplicationRecoveryRepository,
    ApplicationRecoverySnapshot,
)

from .dialogue_delete import (
    DialogueDeleteError,
    DialogueDeleteErrorCategory,
    DialogueDeleteReason,
    DialogueDeleteRequest,
    DialogueDeleteResult,
    DialogueDeleteService,
    DialogueDeleteStatus,
)
from .dialogue_interrupt import (
    DialogueInterruptError,
    DialogueInterruptErrorCategory,
    DialogueInterruptReason,
    DialogueInterruptRequest,
    DialogueInterruptResult,
    DialogueInterruptService,
    DialogueInterruptStatus,
)
from .private_settings import (
    P4_PRIVATE_BUTTON_LABEL_MAX_CHARS,
    P4_PRIVATE_CALLBACK_TTL_MS,
    P4_PRIVATE_PANEL_TEXT_MAX_CHARS,
    PrivateAdminButton,
    PrivateCallbackRequest,
    _display_text,
)


_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32}")
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_MAX_SQLITE_INT = 9223372036854775807
_P42_ACTIONS = frozenset(
    {
        "P42_REFRESH",
        "P42_INTERRUPT",
        "P42_BEGIN_DELETE",
        "P42_CONFIRM_DELETE",
        "P42_CANCEL_DELETE",
    }
)
_P42_STATES = frozenset(state.value for state in DialogueState)
_DELETE_STATES = frozenset(
    {
        DialogueState.IDLE.value,
        DialogueState.TURN_RUNNING.value,
        DialogueState.DELETE_PENDING.value,
    }
)


class PrivateDialogueStatus(StrEnum):
    RENDERED = "RENDERED"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    INTERRUPTED = "INTERRUPTED"
    DELETED = "DELETED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    ALREADY_USED = "ALREADY_USED"
    UNAUTHORIZED = "UNAUTHORIZED"


class PrivateDialogueReason(StrEnum):
    CALLBACK_NOT_FOUND = "CALLBACK_NOT_FOUND"
    STALE_ACTION = "STALE_ACTION"
    NO_DIALOGUE = "NO_DIALOGUE"
    DIALOGUE_NOT_RUNNING = "DIALOGUE_NOT_RUNNING"
    JOB_NOT_RUNNING = "JOB_NOT_RUNNING"
    ACTIVE_BINDING_UNAVAILABLE = "ACTIVE_BINDING_UNAVAILABLE"
    INTERRUPT_IN_PROGRESS = "INTERRUPT_IN_PROGRESS"
    INTERRUPT_UNRESOLVED = "INTERRUPT_UNRESOLVED"
    DIALOGUE_NOT_READY = "DIALOGUE_NOT_READY"
    DELETE_NOT_READY = "DELETE_NOT_READY"
    DELETE_IN_PROGRESS = "DELETE_IN_PROGRESS"
    DELETE_UNKNOWN = "DELETE_UNKNOWN"
    ACTION_UNAVAILABLE = "ACTION_UNAVAILABLE"


class PrivateDialogueErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class PrivateDialogueError(Exception):
    """Finite, content-free P4.2 diagnostic."""

    def __init__(self, category: PrivateDialogueErrorCategory | str) -> None:
        try:
            self.category = (
                category if isinstance(category, PrivateDialogueErrorCategory)
                else PrivateDialogueErrorCategory(category)
            )
        except (TypeError, ValueError):
            self.category = PrivateDialogueErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"PrivateDialogueError({self.category.value!r})"


@dataclass(frozen=True, repr=False)
class PrivateDialogueOpenRequest:
    user_id: int
    chat_id: int

    def __post_init__(self) -> None:
        if not _valid_user(self.user_id) or not _valid_chat(self.chat_id):
            raise _invalid()

    def __repr__(self) -> str:
        return f"PrivateDialogueOpenRequest(user_id={self.user_id!r}, chat_id={self.chat_id!r})"


class PrivateDialoguePanelSection(StrEnum):
    STATUS = "STATUS"
    DELETE_CONFIRM = "DELETE_CONFIRM"


@dataclass(frozen=True, repr=False)
class PrivateDialoguePanel:
    section: PrivateDialoguePanelSection
    text: str
    rows: tuple[tuple[PrivateAdminButton, ...], ...]

    def __post_init__(self) -> None:
        if type(self.section) is not PrivateDialoguePanelSection:
            raise _invalid()
        if type(self.rows) is not tuple or any(type(row) is not tuple for row in self.rows):
            raise _invalid()
        for row in self.rows:
            if any(type(button) is not PrivateAdminButton for button in row):
                raise _invalid()
        object.__setattr__(
            self,
            "text",
            _display_text(self.text, P4_PRIVATE_PANEL_TEXT_MAX_CHARS) or "Status",
        )

    def __repr__(self) -> str:
        labels = tuple(tuple(button.label for button in row) for row in self.rows)
        return f"PrivateDialoguePanel(section={self.section!r}, text={self.text!r}, rows={labels!r})"


@dataclass(frozen=True, repr=False)
class PrivateDialogueResult:
    status: PrivateDialogueStatus
    panel: PrivateDialoguePanel | None
    reason: PrivateDialogueReason | None

    def __post_init__(self) -> None:
        if type(self.status) is not PrivateDialogueStatus:
            raise _invalid()
        if self.panel is not None and type(self.panel) is not PrivateDialoguePanel:
            raise _invalid()
        if self.reason is not None and type(self.reason) is not PrivateDialogueReason:
            raise _invalid()

    def __repr__(self) -> str:
        return f"PrivateDialogueResult(status={self.status!r}, panel={self.panel!r}, reason={self.reason!r})"


def _invalid() -> PrivateDialogueError:
    return PrivateDialogueError(PrivateDialogueErrorCategory.INVALID_ARGUMENT)


def _storage() -> PrivateDialogueError:
    return PrivateDialogueError(PrivateDialogueErrorCategory.STORAGE)


def _invariant() -> PrivateDialogueError:
    return PrivateDialogueError(PrivateDialogueErrorCategory.INVARIANT)


def _valid_nonnegative(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_SQLITE_INT


def _valid_user(value: object) -> bool:
    return type(value) is int and 1 <= value <= _MAX_SQLITE_INT


def _valid_chat(value: object) -> bool:
    return type(value) is int and -(2**63) <= value <= _MAX_SQLITE_INT and value != 0


def _default_clock() -> int:
    return time.time_ns() // 1_000_000


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe(value: object, fallback: str = "unavailable") -> str:
    if not isinstance(value, str):
        return fallback
    return _display_text(value, 256) or fallback


def _async_method(value: object, name: str) -> bool:
    method = getattr(value, name, None)
    return callable(method) and (
        inspect.iscoroutinefunction(method)
        or inspect.iscoroutinefunction(getattr(method, "__call__", None))
    )


class PrivateDialogueManagementService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        server_display_name: str,
        operator_user_id: int,
        interrupt_service: DialogueInterruptService,
        delete_service: DialogueDeleteService,
        mode_provider: Callable[[], ControllerMode] | None = None,
        now_ms: Callable[[], int] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(storage, SqliteStorage):
            raise _invalid()
        if (
            type(server_id) is not str or not server_id or "\x00" in server_id
            or len(server_id) > 128
            or type(server_display_name) is not str or not server_display_name
            or "\x00" in server_display_name or len(server_display_name) > 256
            or not _valid_user(operator_user_id)
        ):
            raise _invalid()
        if not _async_method(interrupt_service, "interrupt") or not _async_method(delete_service, "delete"):
            raise _invalid()
        if mode_provider is not None and not callable(mode_provider):
            raise _invalid()
        if now_ms is not None and not callable(now_ms):
            raise _invalid()
        if token_factory is not None and not callable(token_factory):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._server_display_name = server_display_name
        self._operator_user_id = operator_user_id
        self._interrupt_service = interrupt_service
        self._delete_service = delete_service
        self._mode_provider = mode_provider
        self._clock = now_ms if now_ms is not None else _default_clock
        self._token_factory = token_factory if token_factory is not None else lambda: secrets.token_urlsafe(24)

    async def open_status(self, request: PrivateDialogueOpenRequest) -> PrivateDialogueResult:
        self._validate_open_request(request)
        if request.user_id != self._operator_user_id or request.chat_id != self._operator_user_id:
            return PrivateDialogueResult(PrivateDialogueStatus.UNAUTHORIZED, None, None)
        snapshot = await self._inspect()
        mode = self._mode()
        if snapshot.dialogue is None:
            panel = self._status_panel(snapshot, mode)
            return PrivateDialogueResult(PrivateDialogueStatus.RENDERED, panel, PrivateDialogueReason.NO_DIALOGUE)
        settings = await self._settings()
        panel = await self._status_panel_with_callbacks(snapshot, mode, settings)
        return PrivateDialogueResult(PrivateDialogueStatus.RENDERED, panel, None)

    async def handle_callback(self, request: PrivateCallbackRequest) -> PrivateDialogueResult:
        self._validate_callback_request(request)
        if request.user_id != self._operator_user_id or request.chat_id != self._operator_user_id:
            return PrivateDialogueResult(PrivateDialogueStatus.UNAUTHORIZED, None, None)
        if _TOKEN_RE.fullmatch(request.callback_token) is None:
            raise _invalid()
        token_hash = _hash(request.callback_token)
        try:
            peeked = await PrivateManagementRepository(self._storage, now_ms=self._clock).peek_callback(token_hash)
        except (StorageError, RepositoryError) as error:
            raise self._map_repository_error(error) from None
        if peeked is None:
            return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.CALLBACK_NOT_FOUND)
        if peeked.action not in _P42_ACTIONS:
            return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, PrivateDialogueReason.ACTION_UNAVAILABLE)
        try:
            claimed = await CallbackActionRepository(self._storage, now_ms=self._clock).claim(
                token_hash_sha256=token_hash,
                authorized_user_id=request.user_id,
                authorized_chat_id=request.chat_id,
            )
        except (StorageError, RepositoryError) as error:
            raise self._map_repository_error(error, internal=True) from None
        if claimed.status is CallbackClaimStatus.NOT_FOUND:
            return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.CALLBACK_NOT_FOUND)
        if claimed.status is CallbackClaimStatus.UNAUTHORIZED:
            return PrivateDialogueResult(PrivateDialogueStatus.UNAUTHORIZED, None, None)
        if claimed.status is CallbackClaimStatus.EXPIRED:
            return PrivateDialogueResult(PrivateDialogueStatus.EXPIRED, None, None)
        if claimed.status is CallbackClaimStatus.ALREADY_CONSUMED:
            return PrivateDialogueResult(PrivateDialogueStatus.ALREADY_USED, None, None)
        if claimed.status is not CallbackClaimStatus.CLAIMED or type(claimed.record) is not CallbackActionRecord:
            raise _invariant()
        record = claimed.record
        self._validate_owned_record(record)
        snapshot = await self._inspect()
        dialogue = snapshot.dialogue
        if (
            dialogue is None
            or dialogue.version != record.expected_version
            or dialogue.state.value != record.expected_state
            or record.subject_id != self._subject_for(record.action, snapshot)
        ):
            return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.STALE_ACTION)

        if record.action == "P42_REFRESH":
            panel = await self._status_panel_with_callbacks(snapshot, self._mode(), await self._settings())
            return PrivateDialogueResult(PrivateDialogueStatus.RENDERED, panel, None)
        if record.action == "P42_INTERRUPT":
            if not self._interrupt_available(snapshot):
                return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, PrivateDialogueReason.JOB_NOT_RUNNING)
            job = snapshot.active_jobs[0]
            result = await self._call_interrupt(
                DialogueInterruptRequest(dialogue.dialogue_id, job.job_id, dialogue.version, job.version)
            )
            return self._map_interrupt(result)
        if record.action == "P42_BEGIN_DELETE":
            if not self._delete_available(snapshot):
                return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, PrivateDialogueReason.ACTION_UNAVAILABLE)
            panel = await self._delete_confirmation_panel(snapshot)
            return PrivateDialogueResult(PrivateDialogueStatus.CONFIRM_REQUIRED, panel, None)
        if record.action == "P42_CANCEL_DELETE":
            if not self._delete_available(snapshot):
                return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.STALE_ACTION)
            if record.consumed_at_ms is None:
                raise _invariant()
            try:
                revocation = await PrivateManagementRepository(
                    self._storage, now_ms=self._clock
                ).revoke_delete_confirmations(
                    subject_id=record.subject_id,
                    expected_version=dialogue.version,
                    expected_state=dialogue.state.value,
                    authorized_user_id=record.authorized_user_id,
                    authorized_chat_id=record.authorized_chat_id,
                    consumed_at_ms=record.consumed_at_ms,
                )
            except (StorageError, RepositoryError) as error:
                raise self._map_repository_error(error, internal=True) from None
            if (
                type(revocation) is not DeleteConfirmationRevocationResult
                or type(revocation.status) is not DeleteConfirmationRevocationStatus
                or type(revocation.revoked_count) is not int
                or revocation.revoked_count < 0
            ):
                raise _invariant()
            if revocation.status is DeleteConfirmationRevocationStatus.CONFIRM_ALREADY_CLAIMED:
                return PrivateDialogueResult(
                    PrivateDialogueStatus.STALE,
                    None,
                    PrivateDialogueReason.STALE_ACTION,
                )
            if revocation.status is not DeleteConfirmationRevocationStatus.REVOKED:
                raise _invariant()
            panel = await self._status_panel_with_callbacks(snapshot, self._mode(), await self._settings())
            return PrivateDialogueResult(PrivateDialogueStatus.RENDERED, panel, None)
        if record.action == "P42_CONFIRM_DELETE":
            if not self._delete_available(snapshot):
                return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, PrivateDialogueReason.ACTION_UNAVAILABLE)
            result = await self._call_delete(DialogueDeleteRequest(dialogue.dialogue_id, dialogue.version))
            return self._map_delete(result)
        raise _invariant()

    @staticmethod
    def _validate_open_request(request: object) -> None:
        if type(request) is not PrivateDialogueOpenRequest:
            raise _invalid()
        if not _valid_user(request.user_id) or not _valid_chat(request.chat_id):
            raise _invalid()

    @staticmethod
    def _validate_callback_request(request: object) -> None:
        if (
            type(request) is not PrivateCallbackRequest
            or not _valid_nonnegative(request.update_id)
            or not _valid_user(request.user_id)
            or not _valid_chat(request.chat_id)
            or type(request.callback_query_id) is not str
            or not request.callback_query_id
            or "\x00" in request.callback_query_id
            or len(request.callback_query_id) > 256
            or type(request.callback_token) is not str
        ):
            raise _invalid()

    @staticmethod
    def _validate_owned_record(record: CallbackActionRecord) -> None:
        if (
            type(record) is not CallbackActionRecord
            or record.action not in _P42_ACTIONS
            or not _HASH_RE.fullmatch(record.token_hash_sha256)
            or not _HASH_RE.fullmatch(record.subject_id)
            or not _valid_nonnegative(record.expected_version)
            or record.expected_state not in _P42_STATES
        ):
            raise _invariant()
        if record.action == "P42_REFRESH":
            if record.subject_type != "p42_status":
                raise _invariant()
            return
        if record.action == "P42_INTERRUPT":
            if record.subject_type != "p42_interrupt" or record.expected_state != DialogueState.TURN_RUNNING.value:
                raise _invariant()
            return
        if record.subject_type != "p42_delete" or record.expected_state not in _DELETE_STATES:
            raise _invariant()

    async def _inspect(self) -> ApplicationRecoverySnapshot:
        try:
            snapshot = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
        except (StorageError, RepositoryError) as error:
            raise self._map_repository_error(error) from None
        if type(snapshot) is not ApplicationRecoverySnapshot:
            raise _invariant()
        return snapshot

    def _mode(self) -> str:
        if self._mode_provider is None:
            return "UNAVAILABLE"
        try:
            value = self._mode_provider()
        except Exception:
            raise _invariant() from None
        if type(value) is not ControllerMode:
            raise _invariant()
        return value.value

    async def _settings(self):
        try:
            return await SettingsRepository(self._storage).get()
        except (StorageError, RepositoryError) as error:
            raise self._map_repository_error(error) from None

    def _status_panel(self, snapshot, mode: str) -> PrivateDialoguePanel:
        return PrivateDialoguePanel(
            PrivateDialoguePanelSection.STATUS,
            self._status_text(snapshot, mode),
            (),
        )

    async def _status_panel_with_callbacks(self, snapshot, mode: str, settings) -> PrivateDialoguePanel:
        dialogue = snapshot.dialogue
        if dialogue is None:
            return self._status_panel(snapshot, mode)
        actions: list[tuple[str, str, str, str]] = [
            ("Refresh", "P42_REFRESH", "p42_status", _hash(dialogue.dialogue_id)),
        ]
        if self._interrupt_available(snapshot):
            job = snapshot.active_jobs[0]
            actions.append(
                ("Interrupt", "P42_INTERRUPT", "p42_interrupt", _hash(
                    f"{dialogue.dialogue_id}\x00{job.job_id}\x00{job.version}"
                ))
            )
        if self._delete_available(snapshot):
            actions.append(("Delete", "P42_BEGIN_DELETE", "p42_delete", self._delete_subject(snapshot)))
        rows = await self._callback_rows(dialogue.version, dialogue.state.value, actions)
        return PrivateDialoguePanel(
            PrivateDialoguePanelSection.STATUS,
            self._status_text(snapshot, mode, settings),
            rows,
        )

    async def _delete_confirmation_panel(self, snapshot) -> PrivateDialoguePanel:
        dialogue = snapshot.dialogue
        if dialogue is None:
            raise _invariant()
        subject = self._delete_subject(snapshot)
        rows = await self._callback_rows(
            dialogue.version,
            dialogue.state.value,
            (
                ("CONFIRM DELETE", "P42_CONFIRM_DELETE", "p42_delete", subject),
                ("Cancel", "P42_CANCEL_DELETE", "p42_delete", subject),
            ),
        )
        return PrivateDialoguePanel(
            PrivateDialoguePanelSection.DELETE_CONFIRM,
            "Destructive hard-delete request. Accepted P3.5 will request official Codex thread deletion. "
            "CodexControl-owned dialogue content is purged only after definitive external delete confirmation. "
            "If a turn is running, accepted P3.5 may interrupt and reconcile it first. "
            "This UI does not claim that every possible Codex internal trace has been empirically erased; P7 owns storage measurement.",
            rows,
        )

    async def _callback_rows(self, version: int, state: str, actions) -> tuple[tuple[PrivateAdminButton, ...], ...]:
        now = self._read_clock()
        if now > _MAX_SQLITE_INT - P4_PRIVATE_CALLBACK_TTL_MS:
            raise _invariant()
        expires = now + P4_PRIVATE_CALLBACK_TTL_MS
        specs = []
        rows = []
        seen: set[str] = set()
        for label, action, subject_type, subject_id in actions:
            try:
                token = self._token_factory()
            except Exception:
                raise _invariant() from None
            if type(token) is not str or _TOKEN_RE.fullmatch(token) is None or token in seen:
                raise _invariant()
            seen.add(token)
            rows.append((PrivateAdminButton(label, "cc1:" + token),))
            specs.append(PrivateCallbackActionSpec(
                _hash(token), action, subject_type, subject_id,
                version, state, self._operator_user_id, self._operator_user_id,
            ))
        try:
            await PrivateManagementRepository(self._storage, now_ms=self._clock).create_callback_batch(
                actions=tuple(specs), created_at_ms=now, expires_at_ms=expires
            )
        except (StorageError, RepositoryError) as error:
            raise self._map_callback_batch_error(error) from None
        return tuple(rows)

    def _read_clock(self) -> int:
        try:
            value = self._clock()
        except Exception:
            raise _storage() from None
        if not _valid_nonnegative(value):
            raise _storage()
        return value

    def _status_text(self, snapshot, mode: str, settings=None) -> str:
        return self._status_text_for(snapshot, mode, self._server_display_name, self._server_id, settings)

    @staticmethod
    def _status_text_for(snapshot, mode: str, display_name: str, server_id: str, settings=None) -> str:
        lines = [f"Server: {_safe(display_name)} ({_safe(server_id)})", f"Mode: {mode}"]
        dialogue = snapshot.dialogue
        if dialogue is None:
            lines.append("Dialogue: NO_DIALOGUE")
        else:
            lines.extend((f"Dialogue: {dialogue.state.value}", f"Profile: {_safe(dialogue.profile_id)}"))
            if len(snapshot.active_jobs) == 1:
                job = snapshot.active_jobs[0]
                lines.extend((
                    f"Job: {job.state.value}",
                    f"Model: {_safe(job.model_id) if job.model_id else 'not configured'}",
                    f"Reasoning: {_safe(job.reasoning_effort) if job.reasoning_effort else 'not configured'}",
                ))
            elif settings is not None:
                lines.extend((
                    f"Model: {_safe(settings.model_id) if settings.model_id else 'not configured'}",
                    f"Reasoning: {_safe(settings.reasoning_effort) if settings.reasoning_effort else 'not configured'}",
                ))
        return _display_text("\n".join(lines), P4_PRIVATE_PANEL_TEXT_MAX_CHARS)

    @staticmethod
    def _interrupt_available(snapshot) -> bool:
        return (
            snapshot.dialogue is not None
            and snapshot.dialogue.state is DialogueState.TURN_RUNNING
            and len(snapshot.active_jobs) == 1
            and snapshot.active_jobs[0].state is TurnJobState.CODEX_RUNNING
        )

    @staticmethod
    def _delete_available(snapshot) -> bool:
        if snapshot.dialogue is None:
            return False
        state = snapshot.dialogue.state
        if state is DialogueState.IDLE:
            return not snapshot.active_jobs
        if state is DialogueState.TURN_RUNNING:
            return len(snapshot.active_jobs) == 1 and snapshot.active_jobs[0].state is TurnJobState.CODEX_RUNNING
        return state is DialogueState.DELETE_PENDING and not snapshot.active_jobs

    @staticmethod
    def _delete_subject(snapshot) -> str:
        dialogue = snapshot.dialogue
        if dialogue is None:
            raise _invariant()
        if len(snapshot.active_jobs) == 1:
            job_id, job_version = snapshot.active_jobs[0].job_id, str(snapshot.active_jobs[0].version)
        else:
            job_id, job_version = "-", "-"
        return _hash(f"{dialogue.dialogue_id}\x00{dialogue.state.value}\x00{job_id}\x00{job_version}")

    def _subject_for(self, action: str, snapshot) -> str:
        dialogue = snapshot.dialogue
        if dialogue is None:
            raise _invariant()
        if action == "P42_REFRESH":
            return _hash(dialogue.dialogue_id)
        if action == "P42_INTERRUPT":
            if len(snapshot.active_jobs) != 1:
                return "-"
            job = snapshot.active_jobs[0]
            return _hash(f"{dialogue.dialogue_id}\x00{job.job_id}\x00{job.version}")
        return self._delete_subject(snapshot)

    async def _call_interrupt(self, request: DialogueInterruptRequest) -> DialogueInterruptResult:
        try:
            result = await self._interrupt_service.interrupt(request)
        except DialogueInterruptError as error:
            raise self._map_interrupt_error(error) from None
        except Exception:
            raise _invariant() from None
        if type(result) is not DialogueInterruptResult or type(result.status) is not DialogueInterruptStatus:
            raise _invariant()
        if result.reason is not None and type(result.reason) is not DialogueInterruptReason:
            raise _invariant()
        return result

    async def _call_delete(self, request: DialogueDeleteRequest) -> DialogueDeleteResult:
        try:
            result = await self._delete_service.delete(request)
        except DialogueDeleteError as error:
            raise self._map_delete_error(error) from None
        except Exception:
            raise _invariant() from None
        if type(result) is not DialogueDeleteResult or type(result.status) is not DialogueDeleteStatus:
            raise _invariant()
        if result.reason is not None and type(result.reason) is not DialogueDeleteReason:
            raise _invariant()
        return result

    @staticmethod
    def _map_interrupt_error(error: DialogueInterruptError) -> PrivateDialogueError:
        if error.category is DialogueInterruptErrorCategory.STORAGE:
            return _storage()
        if error.category in (
            DialogueInterruptErrorCategory.INVALID_ARGUMENT,
            DialogueInterruptErrorCategory.INVARIANT,
        ):
            return _invariant()
        return _invariant()

    @staticmethod
    def _map_delete_error(error: DialogueDeleteError) -> PrivateDialogueError:
        if error.category is DialogueDeleteErrorCategory.STORAGE:
            return _storage()
        if error.category in (
            DialogueDeleteErrorCategory.INVALID_ARGUMENT,
            DialogueDeleteErrorCategory.INVARIANT,
        ):
            return _invariant()
        return _invariant()

    def _map_interrupt(self, result: DialogueInterruptResult) -> PrivateDialogueResult:
        if result.status in (DialogueInterruptStatus.CONFIRMED, DialogueInterruptStatus.RECONCILED):
            if result.reason is not None:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.INTERRUPTED, None, None)
        if result.status is DialogueInterruptStatus.UNKNOWN:
            if result.reason is not None:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.UNKNOWN, None, PrivateDialogueReason.INTERRUPT_UNRESOLVED)
        if result.status is DialogueInterruptStatus.CONFLICT:
            if result.reason is not DialogueInterruptReason.STALE_REQUEST:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.STALE_ACTION)
        if result.status is DialogueInterruptStatus.REJECTED:
            if result.reason is not None:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, None)
        if result.status is DialogueInterruptStatus.BLOCKED:
            if result.reason not in {
                DialogueInterruptReason.NO_DIALOGUE,
                DialogueInterruptReason.DIALOGUE_NOT_RUNNING,
                DialogueInterruptReason.JOB_NOT_RUNNING,
                DialogueInterruptReason.ACTIVE_BINDING_UNAVAILABLE,
                DialogueInterruptReason.INTERRUPT_IN_PROGRESS,
            }:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, self._map_interrupt_reason(result.reason))
        raise _invariant()

    @staticmethod
    def _map_interrupt_reason(reason: DialogueInterruptReason | None) -> PrivateDialogueReason | None:
        if reason is None:
            return None
        mapping = {
            DialogueInterruptReason.NO_DIALOGUE: PrivateDialogueReason.NO_DIALOGUE,
            DialogueInterruptReason.DIALOGUE_NOT_RUNNING: PrivateDialogueReason.DIALOGUE_NOT_RUNNING,
            DialogueInterruptReason.JOB_NOT_RUNNING: PrivateDialogueReason.JOB_NOT_RUNNING,
            DialogueInterruptReason.ACTIVE_BINDING_UNAVAILABLE: PrivateDialogueReason.ACTIVE_BINDING_UNAVAILABLE,
            DialogueInterruptReason.INTERRUPT_IN_PROGRESS: PrivateDialogueReason.INTERRUPT_IN_PROGRESS,
            DialogueInterruptReason.STALE_REQUEST: PrivateDialogueReason.STALE_ACTION,
        }
        if reason not in mapping:
            raise _invariant()
        return mapping[reason]

    def _map_delete(self, result: DialogueDeleteResult) -> PrivateDialogueResult:
        if result.status in (DialogueDeleteStatus.DELETED, DialogueDeleteStatus.FAILED):
            if result.reason is not None:
                raise _invariant()
            status = PrivateDialogueStatus.DELETED if result.status is DialogueDeleteStatus.DELETED else PrivateDialogueStatus.FAILED
            return PrivateDialogueResult(status, None, None)
        if result.status is DialogueDeleteStatus.UNKNOWN:
            if result.reason is not None:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.UNKNOWN, None, PrivateDialogueReason.DELETE_UNKNOWN)
        if result.status is DialogueDeleteStatus.CONFLICT:
            if result.reason is not DialogueDeleteReason.STALE_REQUEST:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.STALE, None, PrivateDialogueReason.STALE_ACTION)
        if result.status is DialogueDeleteStatus.BLOCKED:
            if result.reason not in {
                DialogueDeleteReason.NO_DIALOGUE,
                DialogueDeleteReason.DIALOGUE_NOT_READY,
                DialogueDeleteReason.DELETE_NOT_READY,
                DialogueDeleteReason.INTERRUPT_IN_PROGRESS,
                DialogueDeleteReason.INTERRUPT_UNRESOLVED,
                DialogueDeleteReason.DELETE_IN_PROGRESS,
            }:
                raise _invariant()
            return PrivateDialogueResult(PrivateDialogueStatus.BLOCKED, None, self._map_delete_reason(result.reason))
        raise _invariant()

    @staticmethod
    def _map_delete_reason(reason: DialogueDeleteReason | None) -> PrivateDialogueReason | None:
        if reason is None:
            return None
        mapping = {
            DialogueDeleteReason.NO_DIALOGUE: PrivateDialogueReason.NO_DIALOGUE,
            DialogueDeleteReason.DIALOGUE_NOT_READY: PrivateDialogueReason.DIALOGUE_NOT_READY,
            DialogueDeleteReason.DELETE_NOT_READY: PrivateDialogueReason.DELETE_NOT_READY,
            DialogueDeleteReason.INTERRUPT_IN_PROGRESS: PrivateDialogueReason.INTERRUPT_IN_PROGRESS,
            DialogueDeleteReason.INTERRUPT_UNRESOLVED: PrivateDialogueReason.INTERRUPT_UNRESOLVED,
            DialogueDeleteReason.DELETE_IN_PROGRESS: PrivateDialogueReason.DELETE_IN_PROGRESS,
            DialogueDeleteReason.STALE_REQUEST: PrivateDialogueReason.STALE_ACTION,
        }
        if reason not in mapping:
            raise _invariant()
        return mapping[reason]

    @staticmethod
    def _map_repository_error(error: RepositoryError, *, internal: bool = False) -> PrivateDialogueError:
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invariant() if internal else _storage()
        return _storage()

    @staticmethod
    def _map_callback_batch_error(error: RepositoryError) -> PrivateDialogueError:
        if error.category in (
            RepositoryErrorCategory.ALREADY_EXISTS,
            RepositoryErrorCategory.INVARIANT_VIOLATION,
            RepositoryErrorCategory.INVALID_ARGUMENT,
        ):
            return _invariant()
        return _storage()


__all__ = [
    "PrivateDialogueOpenRequest",
    "PrivateDialogueStatus",
    "PrivateDialogueReason",
    "PrivateDialogueErrorCategory",
    "PrivateDialogueError",
    "PrivateDialoguePanelSection",
    "PrivateDialoguePanel",
    "PrivateDialogueResult",
    "PrivateDialogueManagementService",
]
