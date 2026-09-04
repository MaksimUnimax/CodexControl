"""Safe diagnostic classification only; no automatic retry conclusion is encoded."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .capabilities import CapabilityManifestError
from .protocol import ProtocolFault, ProtocolRemoteError
from .runtime import RuntimeErrorSafe
from .subprocess_transport import SubprocessTransportError
from .version_probe import VersionProbeError
from .model_catalog import ModelCatalogError

class CodexAdapterErrorCategory(str, Enum):
    CONFIGURATION="configuration"; UNSUPPORTED_CODEX_VERSION="unsupported_codex_version"; VERSION_PROBE_FAILURE="version_probe_failure"; CAPABILITY_MANIFEST_INVALID="capability_manifest_invalid"; REQUIRED_CAPABILITY_MISSING="required_capability_missing"; RUNTIME_UNAVAILABLE="runtime_unavailable"; PROFILE_STOPPING="profile_stopping"; MANAGER_SHUTTING_DOWN="manager_shutting_down"; UNRESOLVED_PROCESS="unresolved_process"; RUNTIME_SHUTDOWN_FAILURE="runtime_shutdown_failure"; PROTOCOL_FAULT="protocol_fault"; REMOTE_APP_SERVER_ERROR="remote_app_server_error"; TRANSPORT_FAULT="transport_fault"; MODEL_CATALOG_INVALID="model_catalog_invalid"; MODEL_NOT_AVAILABLE="model_not_available"; REASONING_EFFORT_UNSUPPORTED="reasoning_effort_unsupported"; TIMEOUT="timeout"; INTERNAL="internal"
    THREAD_REQUEST_INVALID="thread_request_invalid"; THREAD_PRECONDITION_CHANGED="thread_precondition_changed"; THREAD_OPERATION_BUSY="thread_operation_busy"; THREAD_START_REJECTED="thread_start_rejected"; THREAD_START_UNKNOWN="thread_start_unknown"; THREAD_RESUME_REJECTED="thread_resume_rejected"; THREAD_RESUME_UNKNOWN="thread_resume_unknown"
@dataclass(frozen=True)
class CodexAdapterError(Exception):
    category: CodexAdapterErrorCategory; profile_id: str | None = None; remote_code: int | None = None
    def __str__(self) -> str: return self.category.value
    def __repr__(self) -> str: return f"CodexAdapterError(category={self.category.value!r}, profile_id={self.profile_id!r}, remote_code={self.remote_code!r})"

def normalize_error(error: BaseException) -> CodexAdapterError:
    if isinstance(error, CodexAdapterError): return error
    # This lazy exact-type import avoids the reverse module-initialization
    # dependency: thread_lifecycle imports this module's categories.
    from .thread_lifecycle import ThreadLifecycleError
    if isinstance(error, ThreadLifecycleError): return CodexAdapterError(error.category)
    if isinstance(error, ProtocolRemoteError): return CodexAdapterError(CodexAdapterErrorCategory.REMOTE_APP_SERVER_ERROR, remote_code=error.code)
    if isinstance(error, ProtocolFault): return CodexAdapterError(CodexAdapterErrorCategory.PROTOCOL_FAULT)
    if isinstance(error, SubprocessTransportError): return CodexAdapterError(CodexAdapterErrorCategory.TRANSPORT_FAULT)
    if isinstance(error, ModelCatalogError):
        mapping={"model_not_available":CodexAdapterErrorCategory.MODEL_NOT_AVAILABLE,"reasoning_effort_unsupported":CodexAdapterErrorCategory.REASONING_EFFORT_UNSUPPORTED}
        return CodexAdapterError(mapping.get(error.category, CodexAdapterErrorCategory.MODEL_CATALOG_INVALID))
    if isinstance(error, RuntimeErrorSafe):
        mapping={"executable_invalid":CodexAdapterErrorCategory.CONFIGURATION,"profile_stopping":CodexAdapterErrorCategory.PROFILE_STOPPING,"manager_shutting_down":CodexAdapterErrorCategory.MANAGER_SHUTTING_DOWN,"unresolved_process":CodexAdapterErrorCategory.UNRESOLVED_PROCESS,"kill_reap_timeout":CodexAdapterErrorCategory.RUNTIME_SHUTDOWN_FAILURE}
        return CodexAdapterError(mapping.get(error.category,CodexAdapterErrorCategory.RUNTIME_UNAVAILABLE), profile_id=error.profile_id)
    if isinstance(error, CapabilityManifestError):
        if error.category == "unsupported_codex_version": category=CodexAdapterErrorCategory.UNSUPPORTED_CODEX_VERSION
        elif error.category == "required_capability_missing": category=CodexAdapterErrorCategory.REQUIRED_CAPABILITY_MISSING
        else: category=CodexAdapterErrorCategory.CAPABILITY_MANIFEST_INVALID
        return CodexAdapterError(category)
    if isinstance(error, VersionProbeError):
        if error.category == "executable_invalid": category=CodexAdapterErrorCategory.CONFIGURATION
        elif error.category == "unsupported_codex_version": category=CodexAdapterErrorCategory.UNSUPPORTED_CODEX_VERSION
        elif error.category in ("version_probe_timeout", "version_probe_spawn_timeout"): category=CodexAdapterErrorCategory.TIMEOUT
        else: category=CodexAdapterErrorCategory.VERSION_PROBE_FAILURE
        return CodexAdapterError(category)
    return CodexAdapterError(CodexAdapterErrorCategory.INTERNAL)
