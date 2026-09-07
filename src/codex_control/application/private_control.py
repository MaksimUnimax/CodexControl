"""Final fake/application private-management composition for P4.3."""

from __future__ import annotations

import hashlib
import re
import secrets
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from codex_control.adapters.telegram.private_updates import PrivateCommand
from codex_control.domain import ControllerMode, CodexProfile
from codex_control.storage import (
    ApprovalCallbackClaimStatus,
    ApprovalRecord,
    ApprovalRepository,
    ApprovalState,
    ApplicationRecoveryRepository,
    CallbackActionRecord,
    CallbackActionRepository,
    CallbackClaimStatus,
    ControllerRuntimeRepository,
    DialogueState,
    ErrorFingerprintRecord,
    ErrorFingerprintRepository,
    IngressDispositionKind,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    RepositoryError,
    RepositoryErrorCategory,
    SqliteStorage,
    StorageError,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobState,
)

from .private_dialogue import (
    PrivateDialogueManagementService,
    PrivateDialogueOpenRequest,
    PrivateDialoguePanel,
    PrivateDialogueReason,
    PrivateDialogueResult,
    PrivateDialogueStatus,
)
from .private_settings import (
    P4_PRIVATE_BUTTON_LABEL_MAX_CHARS,
    P4_PRIVATE_CALLBACK_TTL_MS,
    P4_PRIVATE_PANEL_TEXT_MAX_CHARS,
    PrivateAdminButton,
    PrivateAdminPanel,
    PrivateAdminReason,
    PrivateAdminResult,
    PrivateAdminStatus,
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivatePanelSection,
    PrivateSettingsManagementService,
    _display_text,
)
from .settings_selection import SettingsSelectionService, SettingsSelectionView


P43_APPROVAL_DETAILS_MAX_CHARS = 2400
_MAX_SQLITE_INT = 9223372036854775807
_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32}")
_HASH_RE = re.compile(r"[0-9a-f]{64}")
_P43_ACTIONS = frozenset(
    {"P43_REFRESH_ROOT", "P43_OPEN_DIALOGUE", "P43_OPEN_DIAGNOSTICS", "P43_OPEN_APPROVALS"}
)
_P41_ACTIONS = frozenset(
    {"OPEN_ROOT", "OPEN_PROFILES", "OPEN_MODELS", "OPEN_REASONING", "SELECT_PROFILE", "SELECT_MODEL", "SELECT_REASONING"}
)
_P42_ACTIONS = frozenset(
    {"P42_REFRESH", "P42_INTERRUPT", "P42_BEGIN_DELETE", "P42_CONFIRM_DELETE", "P42_CANCEL_DELETE"}
)
_APPROVAL_ACTIONS = frozenset({"approval_allow", "approval_deny"})


class PrivateControlStatus(StrEnum):
    RENDERED = "RENDERED"
    UPDATED = "UPDATED"
    NO_CHANGE = "NO_CHANGE"
    CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
    INTERRUPTED = "INTERRUPTED"
    DELETED = "DELETED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    ALREADY_USED = "ALREADY_USED"
    DUPLICATE = "DUPLICATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNSUPPORTED = "UNSUPPORTED"


class PrivateControlReason(StrEnum):
    CALLBACK_NOT_FOUND = "CALLBACK_NOT_FOUND"
    STALE_ACTION = "STALE_ACTION"
    ACTION_UNAVAILABLE = "ACTION_UNAVAILABLE"
    SETTINGS_MISSING = "SETTINGS_MISSING"
    PROFILE_NOT_CONFIGURED = "PROFILE_NOT_CONFIGURED"
    PROFILE_LOCKED = "PROFILE_LOCKED"
    DIALOGUE_NOT_IDLE = "DIALOGUE_NOT_IDLE"
    MODEL_NOT_CONFIGURED = "MODEL_NOT_CONFIGURED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    REASONING_EFFORT_UNSUPPORTED = "REASONING_EFFORT_UNSUPPORTED"
    CATALOG_UNAVAILABLE = "CATALOG_UNAVAILABLE"
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
    NO_PENDING_APPROVAL = "NO_PENDING_APPROVAL"
    DIAGNOSTICS_UNAVAILABLE = "DIAGNOSTICS_UNAVAILABLE"


class PrivateControlErrorCategory(StrEnum):
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    STORAGE = "STORAGE"
    INVARIANT = "INVARIANT"


class PrivateControlError(Exception):
    """Finite, content-free final facade diagnostic."""

    def __init__(self, category: PrivateControlErrorCategory | str) -> None:
        try:
            self.category = category if isinstance(category, PrivateControlErrorCategory) else PrivateControlErrorCategory(category)
        except (TypeError, ValueError):
            self.category = PrivateControlErrorCategory.INVARIANT
        super().__init__(self.category.value)

    def __str__(self) -> str:
        return self.category.value

    def __repr__(self) -> str:
        return f"PrivateControlError({self.category.value!r})"


class PrivateControlPanelSection(StrEnum):
    ROOT = "ROOT"
    DIAGNOSTICS = "DIAGNOSTICS"
    APPROVAL = "APPROVAL"


def _invalid() -> PrivateControlError:
    return PrivateControlError(PrivateControlErrorCategory.INVALID_ARGUMENT)


def _storage() -> PrivateControlError:
    return PrivateControlError(PrivateControlErrorCategory.STORAGE)


def _invariant() -> PrivateControlError:
    return PrivateControlError(PrivateControlErrorCategory.INVARIANT)


def _valid_nonnegative(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_SQLITE_INT


def _valid_user(value: object) -> bool:
    return type(value) is int and 1 <= value <= _MAX_SQLITE_INT


def _valid_chat(value: object) -> bool:
    return type(value) is int and -(2**63) <= value <= _MAX_SQLITE_INT and value != 0


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe(value: object, fallback: str = "unavailable", limit: int = 256) -> str:
    if not isinstance(value, str):
        return fallback
    return _display_text(value, limit) or fallback


def _sanitize_approval_details(value: str) -> str | None:
    sanitized = "".join(" " if unicodedata.category(char) == "Cc" else char for char in value)
    sanitized = " ".join(sanitized.split())
    if not sanitized or len(sanitized) > P43_APPROVAL_DETAILS_MAX_CHARS:
        return None
    return sanitized


def _clock_value(clock: Callable[[], int]) -> int:
    try:
        value = clock()
    except Exception:
        raise _storage() from None
    if not _valid_nonnegative(value):
        raise _storage()
    return value


@dataclass(frozen=True, repr=False)
class PrivateControlPanel:
    section: PrivateControlPanelSection
    text: str
    rows: tuple[tuple[PrivateAdminButton, ...], ...]

    def __post_init__(self) -> None:
        if type(self.section) is not PrivateControlPanelSection:
            raise _invalid()
        if type(self.rows) is not tuple or any(type(row) is not tuple for row in self.rows):
            raise _invalid()
        if any(type(button) is not PrivateAdminButton for row in self.rows for button in row):
            raise _invalid()
        object.__setattr__(self, "text", _display_text(self.text, P4_PRIVATE_PANEL_TEXT_MAX_CHARS) or "Control")

    def __repr__(self) -> str:
        labels = tuple(tuple(button.label for button in row) for row in self.rows)
        return f"PrivateControlPanel(section={self.section!r}, text='[REDACTED]', rows={labels!r})"


@dataclass(frozen=True, repr=False)
class PrivateControlResult:
    status: PrivateControlStatus
    panel: PrivateAdminPanel | PrivateDialoguePanel | PrivateControlPanel | None
    reason: PrivateControlReason | None

    def __post_init__(self) -> None:
        if type(self.status) is not PrivateControlStatus:
            raise _invalid()
        if self.panel is not None and type(self.panel) not in (PrivateAdminPanel, PrivateDialoguePanel, PrivateControlPanel):
            raise _invalid()
        if self.reason is not None and type(self.reason) is not PrivateControlReason:
            raise _invalid()

    def __repr__(self) -> str:
        return f"PrivateControlResult(status={self.status!r}, panel={self.panel!r}, reason={self.reason!r})"


@dataclass(frozen=True, repr=False)
class PrivateApprovalProjectionRequest:
    approval_id: str

    def __post_init__(self) -> None:
        if type(self.approval_id) is not str or not self.approval_id or "\x00" in self.approval_id or len(self.approval_id) > 128:
            raise _invalid()

    def __repr__(self) -> str:
        return "PrivateApprovalProjectionRequest(approval_id='[REDACTED]')"


@dataclass(frozen=True)
class PrivateDiagnosticsSnapshot:
    storage_state: "PrivateDiagnosticState"
    codex_state: "PrivateDiagnosticState"
    database_bytes: int | None
    transient_payload_bytes: int | None
    filesystem_free_bytes: int | None

    def __post_init__(self) -> None:
        if type(self.storage_state) is not PrivateDiagnosticState or type(self.codex_state) is not PrivateDiagnosticState:
            raise _invalid()
        for value in (self.database_bytes, self.transient_payload_bytes, self.filesystem_free_bytes):
            if value is not None and not _valid_nonnegative(value):
                raise _invalid()


class PrivateDiagnosticState(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


def _result(status: PrivateControlStatus, panel: Any = None, reason: PrivateControlReason | None = None) -> PrivateControlResult:
    return PrivateControlResult(status, panel, reason)


class PrivateControlService:
    def __init__(
        self,
        storage: SqliteStorage,
        *,
        server_id: str,
        server_display_name: str,
        operator_user_id: int,
        profiles: tuple[CodexProfile, ...],
        model_catalog: object,
        interrupt_service: object,
        delete_service: object,
        mode_provider: Callable[[], ControllerMode] | None = None,
        diagnostics_provider: Callable[[], PrivateDiagnosticsSnapshot] | None = None,
        now_ms: Callable[[], int] | None = None,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if (
            not isinstance(storage, SqliteStorage)
            or type(server_id) is not str or not server_id or "\x00" in server_id
            or type(server_display_name) is not str or not server_display_name or "\x00" in server_display_name
            or not _valid_user(operator_user_id) or type(profiles) is not tuple
            or (now_ms is not None and not callable(now_ms))
            or (mode_provider is not None and not callable(mode_provider))
            or (diagnostics_provider is not None and not callable(diagnostics_provider))
            or (token_factory is not None and not callable(token_factory))
        ):
            raise _invalid()
        self._storage = storage
        self._server_id = server_id
        self._server_display_name = server_display_name
        self._operator_user_id = operator_user_id
        self._profiles = profiles
        self._mode_provider = mode_provider
        self._diagnostics_provider = diagnostics_provider
        self._clock = now_ms if now_ms is not None else lambda: time.time_ns() // 1_000_000
        self._token_factory = token_factory if token_factory is not None else lambda: secrets.token_urlsafe(24)
        try:
            self._settings_service = PrivateSettingsManagementService(
                storage, server_id=server_id, server_display_name=server_display_name,
                operator_user_id=operator_user_id, profiles=profiles, model_catalog=model_catalog,
                now_ms=self._clock, token_factory=self._token_factory,
            )
            self._dialogue_service = PrivateDialogueManagementService(
                storage, server_id=server_id, server_display_name=server_display_name,
                operator_user_id=operator_user_id, interrupt_service=interrupt_service,
                delete_service=delete_service, mode_provider=mode_provider,
                now_ms=self._clock, token_factory=self._token_factory,
            )
            self._selection = SettingsSelectionService(
                storage, server_id=server_id, profiles=profiles, model_catalog=model_catalog,
                now_ms=self._clock,
            )
        except (PrivateControlError, ValueError) as error:
            raise _invalid() from error
        except Exception as error:
            # Accepted constructors expose finite errors; no arbitrary detail leaves this boundary.
            if hasattr(error, "category"):
                raise _invalid() from None
            raise

    async def handle_command(self, request: PrivateCommandRequest) -> PrivateControlResult:
        self._validate_command(request)
        if not self._authorized(request.user_id, request.chat_id):
            try:
                await self._ignored_unauthorized(request.update_id)
            except (RepositoryError, StorageError):
                raise _storage() from None
            return _result(PrivateControlStatus.UNAUTHORIZED)
        if request.command is None:
            return _result(PrivateControlStatus.UNSUPPORTED)
        if request.command is PrivateCommand.SETTINGS:
            return self._map_admin(await self._call_settings_command(request))
        if request.command is not PrivateCommand.MENU:
            return _result(PrivateControlStatus.UNSUPPORTED)
        try:
            claim = await PrivateManagementRepository(self._storage, now_ms=self._clock).claim_private_command(update_id=request.update_id)
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error, internal=True) from None
        if claim.duplicate:
            return _result(PrivateControlStatus.DUPLICATE)
        return await self._render_root()

    async def handle_callback(self, request: PrivateCallbackRequest) -> PrivateControlResult:
        self._validate_callback(request)
        if not self._authorized(request.user_id, request.chat_id):
            return _result(PrivateControlStatus.UNAUTHORIZED)
        if _TOKEN_RE.fullmatch(request.callback_token) is None:
            raise _invalid()
        token_hash = _hash(request.callback_token)
        try:
            peeked = await PrivateManagementRepository(self._storage, now_ms=self._clock).peek_callback(token_hash)
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None
        if peeked is None:
            return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.CALLBACK_NOT_FOUND)
        if peeked.action in _P41_ACTIONS:
            return self._map_admin(await self._call_settings_callback(request))
        if peeked.action in _P42_ACTIONS:
            return self._map_dialogue(await self._call_dialogue_callback(request))
        if peeked.action in _APPROVAL_ACTIONS:
            return await self._claim_approval(token_hash, peeked)
        if peeked.action in _P43_ACTIONS:
            return await self._handle_p43(request, token_hash, peeked)
        return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.ACTION_UNAVAILABLE)

    async def project_approval(self, request: PrivateApprovalProjectionRequest) -> PrivateControlResult:
        if type(request) is not PrivateApprovalProjectionRequest:
            raise _invalid()
        try:
            approval = await ApprovalRepository(self._storage, now_ms=self._clock).get(request.approval_id)
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None
        if approval is None or approval.state is not ApprovalState.PENDING:
            return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
        snapshot = await self._inspect()
        if not self._is_current_approval(approval, snapshot):
            return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
        now = _clock_value(self._clock)
        if approval.expires_at_ms <= now:
            return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
        return await self._approval_panel(approval, snapshot, now)

    async def _render_root(self) -> PrivateControlResult:
        controller = await self._controller()
        snapshot = await self._inspect()
        try:
            view = await self._selection.get_view(refresh=False)
        except Exception as error:
            raise self._map_selection_exception(error) from None
        pending: tuple[ApprovalRecord, ...] = ()
        if snapshot.dialogue is not None and len(snapshot.active_jobs) == 1 and snapshot.active_jobs[0].state is TurnJobState.CODEX_RUNNING:
            pending = await self._pending_for_job(snapshot.active_jobs[0].job_id)
        mode = self._mode()
        labels: list[tuple[str, str, str, str]] = []
        if view.settings is not None:
            labels.append(("Settings", "OPEN_ROOT", "panel", "0"))
        dialogue_id = "-" if snapshot.dialogue is None else snapshot.dialogue.dialogue_id
        dialogue_version = "-" if snapshot.dialogue is None else str(snapshot.dialogue.version)
        labels.extend(
            (
                ("Dialogue", "P43_OPEN_DIALOGUE", "p43_nav", _hash(f"dialogue\x00{dialogue_id}\x00{dialogue_version}")),
                ("Diagnostics", "P43_OPEN_DIAGNOSTICS", "p43_nav", _hash(f"diagnostics\x00{self._server_id}\x00{controller.boot_generation}")),
            )
        )
        if pending:
            labels.append(("Approvals", "P43_OPEN_APPROVALS", "p43_nav", _hash(f"approval\x00{pending[0].approval_id}")))
        labels.append(("Refresh", "P43_REFRESH_ROOT", "p43_nav", _hash(f"root\x00{self._server_id}\x00{controller.boot_generation}")))
        panel_text = self._root_text(view, snapshot, pending, mode)
        panel, rows = await self._batch_panel(
            PrivateControlPanelSection.ROOT, panel_text, labels,
            settings_view=view, controller_generation=controller.boot_generation,
        )
        return _result(PrivateControlStatus.RENDERED, panel)

    async def _batch_panel(
        self, section: PrivateControlPanelSection, text: str,
        labels: list[tuple[str, str, str, str]], *,
        settings_view: SettingsSelectionView | None = None,
        controller_generation: int | None = None,
        approval: ApprovalRecord | None = None,
        approval_job_version: int | None = None,
        expiry_limit: int | None = None,
        created_at_ms: int | None = None,
    ) -> tuple[PrivateControlPanel, tuple[tuple[PrivateAdminButton, ...], ...]]:
        now = _clock_value(self._clock) if created_at_ms is None else created_at_ms
        if not _valid_nonnegative(now):
            raise _invariant()
        if now > _MAX_SQLITE_INT - P4_PRIVATE_CALLBACK_TTL_MS:
            raise _invariant()
        expires = now + P4_PRIVATE_CALLBACK_TTL_MS
        if expiry_limit is not None:
            expires = min(expires, expiry_limit)
        if expires <= now:
            raise _invariant()
        specs: list[PrivateCallbackActionSpec] = []
        rows: list[tuple[PrivateAdminButton, ...]] = []
        seen: set[str] = set()
        for label, action, subject_type, subject_id in labels:
            try:
                token = self._token_factory()
            except Exception:
                raise _invariant() from None
            if type(token) is not str or _TOKEN_RE.fullmatch(token) is None or token in seen:
                raise _invariant()
            seen.add(token)
            expected_version: int
            expected_state: str
            if action == "OPEN_ROOT" and settings_view is not None:
                if settings_view.settings is None:
                    raise _invariant()
                expected_version = settings_view.settings.version
                expected_state = "NO_DIALOGUE" if settings_view.dialogue_state is None else settings_view.dialogue_state.value
            elif approval is not None and action in _APPROVAL_ACTIONS:
                if approval_job_version is None:
                    raise _invariant()
                expected_version = approval_job_version
                expected_state = ApprovalState.PENDING.value
            else:
                if controller_generation is None:
                    raise _invariant()
                expected_version = controller_generation
                expected_state = "PRIVATE_ROOT"
            specs.append(PrivateCallbackActionSpec(
                _hash(token), action, subject_type, subject_id, expected_version,
                expected_state, self._operator_user_id, self._operator_user_id,
            ))
            rows.append((PrivateAdminButton(label, "cc1:" + token),))
        try:
            await PrivateManagementRepository(self._storage, now_ms=self._clock).create_callback_batch(
                actions=tuple(specs), created_at_ms=now, expires_at_ms=expires
            )
        except (RepositoryError, StorageError) as error:
            raise self._map_batch_error(error) from None
        return PrivateControlPanel(section, text, tuple(rows)), tuple(rows)

    async def _handle_p43(self, request: PrivateCallbackRequest, token_hash: str, peeked: CallbackActionRecord) -> PrivateControlResult:
        try:
            claimed = await CallbackActionRepository(self._storage, now_ms=self._clock).claim(
                token_hash_sha256=token_hash, authorized_user_id=request.user_id, authorized_chat_id=request.chat_id
            )
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error, internal=True) from None
        if claimed.status is CallbackClaimStatus.NOT_FOUND:
            return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.CALLBACK_NOT_FOUND)
        if claimed.status is CallbackClaimStatus.UNAUTHORIZED:
            return _result(PrivateControlStatus.UNAUTHORIZED)
        if claimed.status is CallbackClaimStatus.EXPIRED:
            return _result(PrivateControlStatus.EXPIRED)
        if claimed.status is CallbackClaimStatus.ALREADY_CONSUMED:
            return _result(PrivateControlStatus.ALREADY_USED)
        if claimed.status is not CallbackClaimStatus.CLAIMED or claimed.record is None:
            raise _invariant()
        record = claimed.record
        if (
            record.action != peeked.action or record.action not in _P43_ACTIONS
            or record.subject_type != "p43_nav" or record.expected_state != "PRIVATE_ROOT"
            or not _HASH_RE.fullmatch(record.subject_id) or not _valid_nonnegative(record.expected_version)
        ):
            raise _invariant()
        controller = await self._controller()
        if controller.boot_generation != record.expected_version:
            return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
        if record.action == "P43_REFRESH_ROOT":
            expected = _hash(f"root\x00{self._server_id}\x00{controller.boot_generation}")
            if record.subject_id != expected:
                return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
            return await self._render_root()
        if record.action == "P43_OPEN_DIAGNOSTICS":
            expected = _hash(f"diagnostics\x00{self._server_id}\x00{controller.boot_generation}")
            if record.subject_id != expected:
                return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
            return await self._render_diagnostics()
        snapshot = await self._inspect()
        if record.action == "P43_OPEN_DIALOGUE":
            dialogue_id = "-" if snapshot.dialogue is None else snapshot.dialogue.dialogue_id
            dialogue_version = "-" if snapshot.dialogue is None else str(snapshot.dialogue.version)
            if record.subject_id != _hash(f"dialogue\x00{dialogue_id}\x00{dialogue_version}"):
                return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
            return self._map_dialogue(await self._dialogue_service.open_status(
                PrivateDialogueOpenRequest(self._operator_user_id, self._operator_user_id)
            ))
        if len(snapshot.active_jobs) != 1 or snapshot.active_jobs[0].state is not TurnJobState.CODEX_RUNNING or snapshot.dialogue is None or snapshot.dialogue.state is not DialogueState.TURN_RUNNING:
            return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
        pending = await self._pending_for_job(snapshot.active_jobs[0].job_id)
        matches = [item for item in pending if _hash(f"approval\x00{item.approval_id}") == record.subject_id]
        if len(matches) > 1:
            raise _invariant()
        if not matches:
            return _result(PrivateControlStatus.STALE, reason=PrivateControlReason.STALE_ACTION)
        now = _clock_value(self._clock)
        if matches[0].expires_at_ms <= now:
            return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
        return await self._approval_panel(matches[0], snapshot, now)

    async def _approval_panel(self, approval: ApprovalRecord, snapshot: Any, now: int) -> PrivateControlResult:
        if approval.expires_at_ms <= now:
            return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
        details = await self._approval_details(approval, snapshot)
        pending = await self._pending_for_job(snapshot.active_jobs[0].job_id)
        index = next((i for i, item in enumerate(pending) if item.approval_id == approval.approval_id), None)
        if index is None:
            raise _invariant()
        profile = next((p.display_name for p in self._profiles if p.profile_id == approval.profile_id), approval.profile_id)
        lines = ["Approval", f"Kind: {approval.kind.value}", f"Profile: {_safe(profile)}", f"Position: {index + 1} of {len(pending)}"]
        if details is None:
            lines.append("Approval details unavailable; Allow is disabled.")
        else:
            lines.append(details)
        labels: list[tuple[str, str, str, str]] = []
        if details is not None:
            labels.append(("Allow", "approval_allow", "approval", approval.approval_id))
        labels.append(("Deny", "approval_deny", "approval", approval.approval_id))
        if index > 0:
            labels.append(("Previous", "P43_OPEN_APPROVALS", "p43_nav", _hash(f"approval\x00{pending[index - 1].approval_id}")))
        if index + 1 < len(pending):
            labels.append(("Next", "P43_OPEN_APPROVALS", "p43_nav", _hash(f"approval\x00{pending[index + 1].approval_id}")))
        labels.append(("Back", "P43_REFRESH_ROOT", "p43_nav", _hash(f"root\x00{self._server_id}\x00{(await self._controller()).boot_generation}")))
        expiry = approval.expires_at_ms
        try:
            panel, _ = await self._batch_panel(
                PrivateControlPanelSection.APPROVAL, "\n".join(lines), labels,
                controller_generation=(await self._controller()).boot_generation,
                approval=approval, approval_job_version=snapshot.active_jobs[0].version,
                expiry_limit=expiry,
                created_at_ms=now,
            )
        except PrivateControlError as error:
            if error.category is PrivateControlErrorCategory.INVARIANT and expiry <= now:
                return _result(PrivateControlStatus.BLOCKED, reason=PrivateControlReason.NO_PENDING_APPROVAL)
            raise
        return _result(PrivateControlStatus.RENDERED, panel)

    async def _approval_details(self, approval: ApprovalRecord, snapshot: Any) -> str | None:
        if approval.display_payload_id is None:
            return None
        try:
            payload = await TransientPayloadRepository(self._storage, now_ms=self._clock).get(approval.display_payload_id)
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None
        if payload is None or payload.kind is not TransientPayloadKind.APPROVAL or payload.job_id != approval.job_id or snapshot.dialogue is None or payload.dialogue_id != snapshot.dialogue.dialogue_id:
            raise _invariant()
        try:
            decoded = payload.content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
        return _sanitize_approval_details(decoded)

    async def _claim_approval(self, token_hash: str, peeked: CallbackActionRecord) -> PrivateControlResult:
        try:
            claimed = await ApprovalRepository(self._storage, now_ms=self._clock).claim_callback(
                token_hash_sha256=token_hash, authorized_user_id=self._operator_user_id,
                authorized_chat_id=self._operator_user_id,
            )
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error, internal=True) from None
        status = claimed.status
        if status is ApprovalCallbackClaimStatus.APPROVED:
            if claimed.record is None or claimed.record.state is not ApprovalState.APPROVED or peeked.action != "approval_allow":
                raise _invariant()
            return _result(PrivateControlStatus.APPROVED)
        if status is ApprovalCallbackClaimStatus.DENIED:
            if claimed.record is None or claimed.record.state is not ApprovalState.DENIED or peeked.action != "approval_deny":
                raise _invariant()
            return _result(PrivateControlStatus.DENIED)
        if claimed.record is not None:
            raise _invariant()
        mapping = {
            ApprovalCallbackClaimStatus.NOT_FOUND: (PrivateControlStatus.STALE, PrivateControlReason.CALLBACK_NOT_FOUND),
            ApprovalCallbackClaimStatus.UNAUTHORIZED: (PrivateControlStatus.UNAUTHORIZED, None),
            ApprovalCallbackClaimStatus.EXPIRED: (PrivateControlStatus.EXPIRED, None),
            ApprovalCallbackClaimStatus.ALREADY_CONSUMED: (PrivateControlStatus.ALREADY_USED, None),
            ApprovalCallbackClaimStatus.STALE: (PrivateControlStatus.STALE, PrivateControlReason.STALE_ACTION),
        }
        if status not in mapping:
            raise _invariant()
        final_status, reason = mapping[status]
        return _result(final_status, reason=reason)

    async def _render_diagnostics(self) -> PrivateControlResult:
        state = await self._diagnostics()
        latest = await self._latest_error()
        mode = self._mode()
        lines = [
            f"Server: {_safe(self._server_display_name)} ({_safe(self._server_id)})",
            f"Mode: {mode}", f"Storage: {state.storage_state.value}", f"Codex runtime: {state.codex_state.value}",
        ]
        if state.database_bytes is not None:
            lines.append(f"Database bytes: {state.database_bytes}")
        if state.transient_payload_bytes is not None:
            lines.append(f"Transient payload bytes: {state.transient_payload_bytes}")
        if state.filesystem_free_bytes is not None:
            lines.append(f"Filesystem free bytes: {state.filesystem_free_bytes}")
        if latest is None:
            lines.append("Last error: none")
        else:
            scope = "dialogue+job" if latest.dialogue_id is not None and latest.job_id is not None else "dialogue" if latest.dialogue_id is not None else "job" if latest.job_id is not None else "controller"
            lines.append(f"Last error: {latest.error_class}; count {latest.count}; scope {scope}; first {latest.first_seen_at_ms}; last {latest.last_seen_at_ms}")
        controller = await self._controller()
        labels = [
            ("Back", "P43_REFRESH_ROOT", "p43_nav", _hash(f"root\x00{self._server_id}\x00{controller.boot_generation}")),
        ]
        panel, _ = await self._batch_panel(
            PrivateControlPanelSection.DIAGNOSTICS, "\n".join(lines), labels,
            controller_generation=controller.boot_generation,
        )
        return _result(PrivateControlStatus.RENDERED, panel)

    async def _diagnostics(self) -> PrivateDiagnosticsSnapshot:
        if self._diagnostics_provider is None:
            return PrivateDiagnosticsSnapshot(
                PrivateDiagnosticState.UNAVAILABLE, PrivateDiagnosticState.UNAVAILABLE, None, None, None
            )
        try:
            value = self._diagnostics_provider()
        except Exception:
            raise _invariant() from None
        if type(value) is not PrivateDiagnosticsSnapshot:
            raise _invariant()
        return value

    async def _latest_error(self) -> ErrorFingerprintRecord | None:
        try:
            return await ErrorFingerprintRepository(self._storage, now_ms=self._clock).latest()
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None

    async def _controller(self):
        try:
            value = await ControllerRuntimeRepository(self._storage, now_ms=self._clock).get()
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None
        if value is None:
            raise _invariant()
        return value

    async def _inspect(self):
        try:
            value = await ApplicationRecoveryRepository(self._storage, now_ms=self._clock).inspect()
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None
        return value

    async def _pending_for_job(self, job_id: str) -> tuple[ApprovalRecord, ...]:
        try:
            return await ApprovalRepository(self._storage, now_ms=self._clock).list_pending_for_job(job_id)
        except (RepositoryError, StorageError) as error:
            raise self._map_repo_error(error) from None

    def _is_current_approval(self, approval: ApprovalRecord, snapshot: Any) -> bool:
        if snapshot.dialogue is None or snapshot.dialogue.state is not DialogueState.TURN_RUNNING or len(snapshot.active_jobs) != 1:
            return False
        job = snapshot.active_jobs[0]
        return job.state is TurnJobState.CODEX_RUNNING and approval.job_id == job.job_id and approval.profile_id == job.profile_id

    def _root_text(self, view: SettingsSelectionView, snapshot: Any, pending: tuple[ApprovalRecord, ...], mode: str) -> str:
        lines = [f"Server: {_safe(self._server_display_name)} ({_safe(self._server_id)})", f"Mode: {mode}"]
        settings = view.settings
        profile = None if settings is None else settings.profile_id
        if snapshot.dialogue is not None:
            profile = snapshot.dialogue.profile_id
        profile_display = next((p.display_name for p in self._profiles if p.profile_id == profile), profile)
        lines.append(f"Profile: {_safe(profile_display, 'not configured')}")
        if settings is None:
            lines.extend(("Model: not configured", "Reasoning: not configured"))
        else:
            lines.append(f"Model: {_safe(settings.model_id, 'not configured') if view.catalog_available else 'unavailable'}")
            lines.append(f"Reasoning: {_safe(settings.reasoning_effort, 'not configured') if view.catalog_available else 'unavailable'}")
        lines.append(f"Dialogue: {snapshot.dialogue.state.value if snapshot.dialogue is not None else 'NO_DIALOGUE'}")
        lines.append(f"Pending approvals: {len(pending)}")
        return _display_text("\n".join(lines), P4_PRIVATE_PANEL_TEXT_MAX_CHARS)

    async def _call_settings_command(self, request):
        try:
            return await self._settings_service.handle_command(request)
        except Exception as error:
            if isinstance(error, (PrivateControlError,)):
                raise
            if hasattr(error, "category"):
                raise self._map_accepted_error(error) from None
            raise _invariant() from None

    async def _call_settings_callback(self, request):
        try:
            return await self._settings_service.handle_callback(request)
        except Exception as error:
            if hasattr(error, "category"):
                raise self._map_accepted_error(error) from None
            raise _invariant() from None

    async def _call_dialogue_callback(self, request):
        try:
            return await self._dialogue_service.handle_callback(request)
        except Exception as error:
            if hasattr(error, "category"):
                raise self._map_accepted_error(error) from None
            raise _invariant() from None

    async def _ignored_unauthorized(self, update_id: int) -> None:
        from codex_control.storage import IngressUpdateRepository
        await IngressUpdateRepository(self._storage, now_ms=self._clock).claim_ignored(
            update_id=update_id, disposition=IngressDispositionKind.IGNORED_UNAUTHORIZED
        )

    async def _dialogue_open(self, request):
        return await self._dialogue_service.open_status(request)

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

    def _authorized(self, user_id: int, chat_id: int) -> bool:
        return user_id == self._operator_user_id and chat_id == self._operator_user_id

    @staticmethod
    def _validate_command(request: object) -> None:
        if type(request) is not PrivateCommandRequest or not _valid_nonnegative(request.update_id) or not _valid_user(request.user_id) or not _valid_chat(request.chat_id) or (request.command is not None and type(request.command) is not PrivateCommand):
            raise _invalid()

    @staticmethod
    def _validate_callback(request: object) -> None:
        if type(request) is not PrivateCallbackRequest or not _valid_nonnegative(request.update_id) or not _valid_user(request.user_id) or not _valid_chat(request.chat_id) or type(request.callback_query_id) is not str or not request.callback_query_id or "\x00" in request.callback_query_id or len(request.callback_query_id) > 256 or type(request.callback_token) is not str:
            raise _invalid()

    @staticmethod
    def _map_repo_error(error: RepositoryError | StorageError, *, internal: bool = False) -> PrivateControlError:
        if isinstance(error, StorageError):
            return _storage()
        if error.category is RepositoryErrorCategory.INVARIANT_VIOLATION:
            return _invariant()
        if error.category is RepositoryErrorCategory.INVALID_ARGUMENT:
            return _invariant() if internal else _invalid()
        if error.category is RepositoryErrorCategory.NOT_FOUND:
            return _invariant() if internal else _storage()
        return _storage()

    def _map_selection_exception(self, error: Exception) -> PrivateControlError:
        if hasattr(error, "category"):
            return self._map_accepted_error(error)
        return _invariant()

    @staticmethod
    def _map_accepted_error(error: Exception) -> PrivateControlError:
        category = getattr(error, "category", None)
        name = getattr(category, "value", category)
        if name == "STORAGE":
            return _storage()
        if name in {"INVALID_ARGUMENT", "INVARIANT"}:
            return _invariant()
        return _invariant()

    @staticmethod
    def _map_batch_error(error: RepositoryError | StorageError) -> PrivateControlError:
        if isinstance(error, StorageError):
            return _storage()
        if error.category in {RepositoryErrorCategory.ALREADY_EXISTS, RepositoryErrorCategory.INVALID_ARGUMENT, RepositoryErrorCategory.INVARIANT_VIOLATION}:
            return _invariant()
        return _storage()

    @staticmethod
    def _map_admin(value: PrivateAdminResult) -> PrivateControlResult:
        if type(value) is not PrivateAdminResult or type(value.status) is not PrivateAdminStatus or (value.panel is not None and type(value.panel) is not PrivateAdminPanel) or (value.reason is not None and type(value.reason) is not PrivateAdminReason):
            raise _invariant()
        reason = None if value.reason is None else PrivateControlReason(value.reason.value)
        mapping = {
            PrivateAdminStatus.RENDERED: PrivateControlStatus.RENDERED,
            PrivateAdminStatus.UPDATED: PrivateControlStatus.UPDATED,
            PrivateAdminStatus.NO_CHANGE: PrivateControlStatus.NO_CHANGE,
            PrivateAdminStatus.BLOCKED: PrivateControlStatus.BLOCKED,
            PrivateAdminStatus.STALE: PrivateControlStatus.STALE,
            PrivateAdminStatus.EXPIRED: PrivateControlStatus.EXPIRED,
            PrivateAdminStatus.ALREADY_USED: PrivateControlStatus.ALREADY_USED,
            PrivateAdminStatus.DUPLICATE: PrivateControlStatus.DUPLICATE,
            PrivateAdminStatus.UNAUTHORIZED: PrivateControlStatus.UNAUTHORIZED,
            PrivateAdminStatus.UNSUPPORTED: PrivateControlStatus.UNSUPPORTED,
        }
        if value.status not in mapping or (value.status is PrivateAdminStatus.RENDERED and (value.panel is None or value.reason is not None)) or (value.status in {PrivateAdminStatus.UPDATED, PrivateAdminStatus.NO_CHANGE} and (value.panel is not None or value.reason is not None)) or (value.status in {PrivateAdminStatus.EXPIRED, PrivateAdminStatus.ALREADY_USED, PrivateAdminStatus.DUPLICATE, PrivateAdminStatus.UNAUTHORIZED, PrivateAdminStatus.UNSUPPORTED} and (value.panel is not None or value.reason is not None)):
            raise _invariant()
        if value.status is PrivateAdminStatus.STALE and value.reason not in {PrivateAdminReason.CALLBACK_NOT_FOUND, PrivateAdminReason.STALE_ACTION}:
            raise _invariant()
        if value.status is PrivateAdminStatus.BLOCKED and reason not in {
            PrivateControlReason.SETTINGS_MISSING, PrivateControlReason.PROFILE_NOT_CONFIGURED, PrivateControlReason.PROFILE_LOCKED,
            PrivateControlReason.DIALOGUE_NOT_IDLE, PrivateControlReason.MODEL_NOT_CONFIGURED, PrivateControlReason.MODEL_UNAVAILABLE,
            PrivateControlReason.REASONING_EFFORT_UNSUPPORTED, PrivateControlReason.CATALOG_UNAVAILABLE, PrivateControlReason.ACTION_UNAVAILABLE,
        }:
            raise _invariant()
        return _result(mapping[value.status], value.panel, reason)

    @staticmethod
    def _map_dialogue(value: PrivateDialogueResult) -> PrivateControlResult:
        if type(value) is not PrivateDialogueResult or type(value.status) is not PrivateDialogueStatus or (value.panel is not None and type(value.panel) is not PrivateDialoguePanel) or (value.reason is not None and type(value.reason) is not PrivateDialogueReason):
            raise _invariant()
        mapping = {
            PrivateDialogueStatus.RENDERED: PrivateControlStatus.RENDERED,
            PrivateDialogueStatus.CONFIRM_REQUIRED: PrivateControlStatus.CONFIRM_REQUIRED,
            PrivateDialogueStatus.INTERRUPTED: PrivateControlStatus.INTERRUPTED,
            PrivateDialogueStatus.DELETED: PrivateControlStatus.DELETED,
            PrivateDialogueStatus.BLOCKED: PrivateControlStatus.BLOCKED,
            PrivateDialogueStatus.STALE: PrivateControlStatus.STALE,
            PrivateDialogueStatus.UNKNOWN: PrivateControlStatus.UNKNOWN,
            PrivateDialogueStatus.FAILED: PrivateControlStatus.FAILED,
            PrivateDialogueStatus.EXPIRED: PrivateControlStatus.EXPIRED,
            PrivateDialogueStatus.ALREADY_USED: PrivateControlStatus.ALREADY_USED,
            PrivateDialogueStatus.UNAUTHORIZED: PrivateControlStatus.UNAUTHORIZED,
        }
        if value.status not in mapping:
            raise _invariant()
        if value.status in {PrivateDialogueStatus.RENDERED, PrivateDialogueStatus.CONFIRM_REQUIRED} and value.panel is None:
            raise _invariant()
        if value.status not in {PrivateDialogueStatus.RENDERED, PrivateDialogueStatus.CONFIRM_REQUIRED} and value.panel is not None:
            raise _invariant()
        allowed = {
            PrivateDialogueStatus.RENDERED: {None, PrivateDialogueReason.NO_DIALOGUE},
            PrivateDialogueStatus.CONFIRM_REQUIRED: {None}, PrivateDialogueStatus.INTERRUPTED: {None},
            PrivateDialogueStatus.DELETED: {None}, PrivateDialogueStatus.FAILED: {None},
            PrivateDialogueStatus.UNKNOWN: {PrivateDialogueReason.INTERRUPT_UNRESOLVED, PrivateDialogueReason.DELETE_UNKNOWN},
            PrivateDialogueStatus.STALE: {PrivateDialogueReason.CALLBACK_NOT_FOUND, PrivateDialogueReason.STALE_ACTION},
            PrivateDialogueStatus.BLOCKED: {PrivateDialogueReason.NO_DIALOGUE, PrivateDialogueReason.DIALOGUE_NOT_RUNNING, PrivateDialogueReason.JOB_NOT_RUNNING, PrivateDialogueReason.ACTIVE_BINDING_UNAVAILABLE, PrivateDialogueReason.INTERRUPT_IN_PROGRESS, PrivateDialogueReason.DIALOGUE_NOT_READY, PrivateDialogueReason.DELETE_NOT_READY, PrivateDialogueReason.DELETE_IN_PROGRESS, PrivateDialogueReason.DELETE_UNKNOWN, PrivateDialogueReason.ACTION_UNAVAILABLE},
            PrivateDialogueStatus.EXPIRED: {None}, PrivateDialogueStatus.ALREADY_USED: {None}, PrivateDialogueStatus.UNAUTHORIZED: {None},
        }
        if value.reason not in allowed[value.status]:
            raise _invariant()
        return _result(mapping[value.status], value.panel, None if value.reason is None else PrivateControlReason(value.reason.value))


__all__ = [
    "P43_APPROVAL_DETAILS_MAX_CHARS", "PrivateControlStatus", "PrivateControlReason",
    "PrivateControlErrorCategory", "PrivateControlError", "PrivateControlPanelSection",
    "PrivateControlPanel", "PrivateControlResult", "PrivateApprovalProjectionRequest",
    "PrivateDiagnosticState", "PrivateDiagnosticsSnapshot", "PrivateControlService",
]
