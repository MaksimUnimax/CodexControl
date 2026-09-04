"""P1.7 bounded, fake-operator-only Codex approval bridge."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from .protocol import CodexProtocolClient, ProtocolApprovalResponseUnknown

MAX_APPROVAL_ID_CHARS = 512
MAX_APPROVAL_CONTEXT_CHARS = 4096
MAX_APPROVAL_PERMISSION_VALUE_CHARS = 4096
MAX_APPROVAL_PERMISSION_ENTRIES = 128

COMMAND = "item/commandExecution/requestApproval"
FILE_CHANGE = "item/fileChange/requestApproval"
PERMISSIONS = "item/permissions/requestApproval"
APPLY_PATCH = "applyPatchApproval"
EXEC_COMMAND = "execCommandApproval"
APPROVAL_METHODS = frozenset((COMMAND, FILE_CHANGE, PERMISSIONS, APPLY_PATCH, EXEC_COMMAND))


class ApprovalDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ApprovalResponseUnknown(Exception):
    """Safe terminal result; a response write was attempted exactly once."""


class AsyncApprovalOperator(Protocol):
    async def decide(self, request: "ApprovalRequest") -> ApprovalDecision: ...


@dataclass(frozen=True)
class ApprovalRequest:
    """Sanitized finite operator view; it deliberately contains no raw params."""
    request_id: str | int
    method: str
    thread_id: str | None
    turn_id: str | None
    item_or_call_id: str
    context_present: bool


def _opaque(value: Any, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value or "\0" in value or len(value) > MAX_APPROVAL_ID_CHARS:
        raise ValueError("approval_invalid")
    return value


def _bounded(value: Any) -> str:
    if not isinstance(value, str) or "\0" in value or len(value) > MAX_APPROVAL_CONTEXT_CHARS:
        raise ValueError("approval_invalid")
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple((key, _freeze(item)) for key, item in value.items())
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value):
            return {key: _thaw(item) for key, item in value}
        return [_thaw(item) for item in value]
    return value


def _permission_string(value: Any) -> str:
    if not isinstance(value, str) or "\0" in value or len(value) > MAX_APPROVAL_PERMISSION_VALUE_CHARS:
        raise ValueError("permission_invalid")
    return value


def _permission_path(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict): raise ValueError("permission_invalid")
    kind = value.get("type")
    if kind == "path" and set(value) == {"type", "path"}:
        return {"type": "path", "path": _permission_string(value["path"])}
    if kind == "glob_pattern" and set(value) == {"type", "pattern"}:
        return {"type": "glob_pattern", "pattern": _permission_string(value["pattern"])}
    if kind == "special" and set(value) == {"type", "value"} and isinstance(value["value"], dict):
        special = value["value"]; name = special.get("kind")
        if name in ("root", "minimal", "tmpdir", "slash_tmp") and set(special) == {"kind"}:
            return {"type": "special", "value": {"kind": name}}
        if name == "project_roots" and set(special) <= {"kind", "subpath"} and set(special) >= {"kind"}:
            subpath = special.get("subpath")
            if subpath is not None: subpath = _permission_string(subpath)
            result = {"kind": name}
            if "subpath" in special: result["subpath"] = subpath
            return {"type": "special", "value": result}
        if name == "unknown" and set(special) <= {"kind", "path", "subpath"} and {"kind", "path"} <= set(special):
            result = {"kind": name, "path": _permission_string(special["path"])}
            if "subpath" in special:
                result["subpath"] = None if special["subpath"] is None else _permission_string(special["subpath"])
            return {"type": "special", "value": result}
    raise ValueError("permission_invalid")


def _permission_profile(value: Any) -> Any:
    """Validate the installed shared request/grant profile without widening it."""
    if not isinstance(value, dict) or set(value) - {"fileSystem", "network"}:
        raise ValueError("permission_invalid")
    if not value: raise ValueError("permission_empty")
    result: dict[str, Any] = {}; count = 0
    if "fileSystem" in value:
        fs = value["fileSystem"]
        if fs is None: result["fileSystem"] = None
        elif isinstance(fs, dict) and set(fs) <= {"entries", "globScanMaxDepth", "read", "write"}:
            mapped: dict[str, Any] = {}
            for key in ("entries", "read", "write"):
                if key not in fs: continue
                raw = fs[key]
                if raw is None: mapped[key] = None; continue
                if not isinstance(raw, list): raise ValueError("permission_invalid")
                count += len(raw)
                if count > MAX_APPROVAL_PERMISSION_ENTRIES: raise ValueError("permission_invalid")
                if key == "entries":
                    entries = []
                    for entry in raw:
                        if not isinstance(entry, dict) or set(entry) != {"access", "path"} or entry.get("access") not in ("read", "write", "deny"):
                            raise ValueError("permission_invalid")
                        entries.append({"access": entry["access"], "path": _permission_path(entry["path"])})
                    mapped[key] = entries
                else: mapped[key] = [_permission_string(item) for item in raw]
            if "globScanMaxDepth" in fs:
                depth = fs["globScanMaxDepth"]
                if depth is not None and (not isinstance(depth, int) or isinstance(depth, bool) or depth < 1): raise ValueError("permission_invalid")
                mapped["globScanMaxDepth"] = depth
            result["fileSystem"] = mapped
        else: raise ValueError("permission_invalid")
    if "network" in value:
        network = value["network"]
        if network is None: result["network"] = None
        elif isinstance(network, dict) and set(network) <= {"enabled"}:
            enabled = network.get("enabled")
            if enabled is not None and not isinstance(enabled, bool): raise ValueError("permission_invalid")
            result["network"] = {"enabled": enabled} if "enabled" in network else {}
        else: raise ValueError("permission_invalid")
    # A syntactically non-empty request of only null profiles grants nothing.
    if not any(item not in (None, {}) for item in result.values()): raise ValueError("permission_empty")
    return _freeze(result)


class CodexApprovalAdapter:
    def __init__(self, operator: AsyncApprovalOperator) -> None:
        self._operator = operator

    async def handle_next(self, client: CodexProtocolClient) -> None:
        envelope = await client.next_server_request()
        await self.handle_envelope(client, envelope)

    async def handle_envelope(self, client: CodexProtocolClient, envelope: Any) -> None:
        request_id = envelope.get("id") if isinstance(envelope, dict) else None
        method = envelope.get("method") if isinstance(envelope, dict) else None
        params = envelope.get("params") if isinstance(envelope, dict) else None
        if method not in APPROVAL_METHODS or not isinstance(params, dict):
            # It is not safe to invent an error schema for an unknown request.
            return
        permission_grant: Any = None
        valid = True
        try:
            request, permission_grant = self._normalize(request_id, method, params)
        except ValueError:
            valid = False; request = None
        decision = ApprovalDecision.DENY
        cancelled = False
        if valid and request is not None:
            try:
                chosen = await self._operator.decide(request)
                if chosen is ApprovalDecision.ALLOW and (method != PERMISSIONS or permission_grant is not None):
                    decision = chosen
            except asyncio.CancelledError:
                # Cancellation before send must still fail closed.  The outer
                # cancellation is re-raised after the one protected attempt.
                cancelled = True
            except BaseException:
                pass
        result = self._result(method, decision, permission_grant)
        try:
            await asyncio.shield(client.respond_to_server_request(request_id, result))
        except ProtocolApprovalResponseUnknown as error:
            raise ApprovalResponseUnknown() from error
        if cancelled:
            raise asyncio.CancelledError

    def _normalize(self, request_id: Any, method: str, params: dict[str, Any]) -> tuple[ApprovalRequest, Any]:
        if not ((isinstance(request_id, int) and not isinstance(request_id, bool)) or isinstance(request_id, str)):
            raise ValueError("approval_invalid")
        if isinstance(request_id, str): _opaque(request_id)
        if method in (COMMAND, FILE_CHANGE, PERMISSIONS):
            thread = _opaque(params.get("threadId")); turn = _opaque(params.get("turnId")); item = _opaque(params.get("itemId"))
            if not isinstance(params.get("startedAtMs"), int) or isinstance(params.get("startedAtMs"), bool): raise ValueError("approval_invalid")
        else:
            thread = _opaque(params.get("conversationId")); turn = None; item = _opaque(params.get("callId"))
        if method == PERMISSIONS: _permission_string(params.get("cwd"))
        if method == APPLY_PATCH:
            changes = params.get("fileChanges")
            if not isinstance(changes, dict) or len(changes) > MAX_APPROVAL_PERMISSION_ENTRIES: raise ValueError("approval_invalid")
        if method == EXEC_COMMAND:
            if not isinstance(params.get("cwd"), str) or not isinstance(params.get("command"), list) or not isinstance(params.get("parsedCmd"), list): raise ValueError("approval_invalid")
            _bounded(params["cwd"])
        grant = _permission_profile(params.get("permissions")) if method == PERMISSIONS else None
        # Optional free text is validated only for bounds and never retained.
        if "reason" in params and params["reason"] is not None: _bounded(params["reason"])
        return ApprovalRequest(request_id, method, thread, turn, item, "reason" in params), grant

    @staticmethod
    def _result(method: str, decision: ApprovalDecision, grant: Any) -> dict[str, Any]:
        if method == PERMISSIONS:
            return {"permissions": _thaw(grant) if decision is ApprovalDecision.ALLOW and grant is not None else {}, "scope": "turn"}
        if method in (COMMAND, FILE_CHANGE): return {"decision": "accept" if decision is ApprovalDecision.ALLOW else "decline"}
        return {"decision": "approved" if decision is ApprovalDecision.ALLOW else "denied"}
