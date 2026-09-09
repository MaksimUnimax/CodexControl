"""Codex app-server protocol adapter foundation."""

from .protocol import CodexProtocolClient, ProtocolFault, ProtocolRemoteError, ProtocolState
from .capabilities import CodexCapability, CodexCapabilityManifest, CodexStorageCapabilities, StorageRuntimeCapabilities, load_manifest
from .errors import CodexAdapterError, CodexAdapterErrorCategory, normalize_error
from .version_probe import CodexVersionProbe
from .thread_lifecycle import CodexThreadLifecycleAdapter, ThreadBinding, ThreadLifecycleError, ThreadOperationResult, ThreadOperationStatus, TrustedWorkingDirectory

from .isolation import IsolationError, IsolationPathAuthority, IsolatedStateRoot

__all__ = ["CodexProtocolClient", "ProtocolFault", "ProtocolRemoteError", "ProtocolState", "CodexCapability", "CodexCapabilityManifest", "CodexStorageCapabilities", "StorageRuntimeCapabilities", "load_manifest", "CodexAdapterError", "CodexAdapterErrorCategory", "normalize_error", "CodexVersionProbe", "CodexThreadLifecycleAdapter", "ThreadBinding", "ThreadLifecycleError", "ThreadOperationResult", "ThreadOperationStatus", "TrustedWorkingDirectory", "IsolationError", "IsolationPathAuthority", "IsolatedStateRoot"]
