"""Validated facts from a version-specific installed Codex schema, never RPC probes."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from importlib import resources
from typing import Any, Iterable


MANIFEST_FORMAT = 1
SUPPORTED_CODEX_VERSION = "0.144.6"
SCHEMA_SHA256 = "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466"


class CapabilityManifestError(Exception):
    """Safe validation failure; malformed source data is never exposed."""
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class CodexCapability(str, Enum):
    MODEL_LIST = "MODEL_LIST"; THREAD_START = "THREAD_START"; THREAD_RESUME = "THREAD_RESUME"
    THREAD_DELETE = "THREAD_DELETE"; TURN_START = "TURN_START"; TURN_INTERRUPT = "TURN_INTERRUPT"
    AGENT_MESSAGE_EVENTS = "AGENT_MESSAGE_EVENTS"; TURN_TERMINAL_EVENTS = "TURN_TERMINAL_EVENTS"
    APPROVAL_SERVER_REQUESTS = "APPROVAL_SERVER_REQUESTS"; APPROVAL_RESPONSE_SCHEMA = "APPROVAL_RESPONSE_SCHEMA"


class InstalledSchemaSupport(str, Enum): PRESENT = "PRESENT"
class AdapterImplementation(str, Enum): NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


@dataclass(frozen=True)
class CapabilityStatus:
    installed_schema_support: InstalledSchemaSupport
    adapter_implementation: AdapterImplementation
    client_requests: tuple[str, ...] = ()
    client_notifications: tuple[str, ...] = ()
    server_requests: tuple[str, ...] = ()
    server_notifications: tuple[str, ...] = ()
    approval_response_schemas: tuple[str, ...] = ()


@dataclass(frozen=True)
class CapabilityReport:
    required: tuple[CodexCapability, ...]
    present: tuple[CodexCapability, ...]
    missing: tuple[CodexCapability, ...]


@dataclass(frozen=True)
class CodexCapabilityManifest:
    manifest_format: int; codex_cli_version: str; schema_sha256: str; framing: str
    client_requests: tuple[str, ...]; client_notifications: tuple[str, ...]
    server_requests: tuple[str, ...]; server_notifications: tuple[str, ...]
    approval_response_schemas: tuple[str, ...]
    capabilities: dict[CodexCapability, CapabilityStatus]

    def check_required(self, required: Iterable[CodexCapability]) -> CapabilityReport:
        required_tuple = tuple(required)
        if len(set(required_tuple)) != len(required_tuple): raise CapabilityManifestError("duplicate_required_capability")
        present = tuple(c for c in required_tuple if c in self.capabilities and self.capabilities[c].installed_schema_support is InstalledSchemaSupport.PRESENT)
        return CapabilityReport(required_tuple, present, tuple(c for c in required_tuple if c not in present))


REQUIRED_V1_CAPABILITIES = tuple(CodexCapability)
_DIRECTIONS = ("client_requests", "client_notifications", "server_requests", "server_notifications")


def _strings(value: Any, category: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value): raise CapabilityManifestError(category)
    result = tuple(value)
    if len(set(result)) != len(result): raise CapabilityManifestError("duplicate_wire_method")
    return result


def load_manifest_data(data: Any) -> CodexCapabilityManifest:
    if not isinstance(data, dict) or data.get("manifest_format") != MANIFEST_FORMAT: raise CapabilityManifestError("manifest_format_invalid")
    version, sha, framing = data.get("codex_cli_version"), data.get("schema_sha256"), data.get("framing")
    if not isinstance(version, str) or not version: raise CapabilityManifestError("manifest_version_invalid")
    if not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{64}", sha) is None: raise CapabilityManifestError("manifest_sha_invalid")
    if not isinstance(framing, str) or not framing: raise CapabilityManifestError("manifest_framing_invalid")
    wire = data.get("wire")
    if not isinstance(wire, dict): raise CapabilityManifestError("manifest_wire_invalid")
    groups = {name: _strings(wire.get(name), "manifest_wire_invalid") for name in _DIRECTIONS}
    approval_response_schemas = _strings(data.get("approval_response_schemas"), "manifest_approval_response_invalid")
    raw_capabilities = data.get("capabilities")
    if not isinstance(raw_capabilities, dict) or len(raw_capabilities) != len(CodexCapability): raise CapabilityManifestError("manifest_capabilities_invalid")
    statuses: dict[CodexCapability, CapabilityStatus] = {}
    for name, raw in raw_capabilities.items():
        try: capability = CodexCapability(name)
        except (TypeError, ValueError): raise CapabilityManifestError("manifest_capability_unknown") from None
        if capability in statuses or not isinstance(raw, dict): raise CapabilityManifestError("manifest_capabilities_invalid")
        try:
            support = InstalledSchemaSupport(raw["installed_schema_support"]); implementation = AdapterImplementation(raw["adapter_implementation"])
        except (KeyError, ValueError, TypeError): raise CapabilityManifestError("manifest_capability_status_invalid") from None
        references = {direction: _strings(raw.get(direction, []), "manifest_capability_reference_invalid") for direction in _DIRECTIONS}
        response_schemas = _strings(raw.get("approval_response_schemas", []), "manifest_capability_reference_invalid")
        if not any(references.values()) and not response_schemas: raise CapabilityManifestError("manifest_capability_reference_invalid")
        if any(method not in groups[direction] for direction, methods in references.items() for method in methods) or any(schema not in approval_response_schemas for schema in response_schemas): raise CapabilityManifestError("manifest_capability_reference_invalid")
        statuses[capability] = CapabilityStatus(support, implementation, **references, approval_response_schemas=response_schemas)
    return CodexCapabilityManifest(MANIFEST_FORMAT, version, sha.lower(), framing, **groups, approval_response_schemas=approval_response_schemas, capabilities=statuses)


def load_manifest(version: str = SUPPORTED_CODEX_VERSION) -> CodexCapabilityManifest:
    if version != SUPPORTED_CODEX_VERSION: raise CapabilityManifestError("unsupported_codex_version")
    try: raw = resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError): raise CapabilityManifestError("manifest_resource_unavailable") from None
    try: return load_manifest_data(json.loads(raw))
    except json.JSONDecodeError: raise CapabilityManifestError("manifest_json_invalid") from None
