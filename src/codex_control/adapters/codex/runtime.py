"""Owned Codex app-server children and per-profile single-flight startup."""
from __future__ import annotations
import asyncio
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Mapping, Protocol
from codex_control.domain import CodexProfile
from .capabilities import (
    SCHEMA_SHA256,
    SUPPORTED_CODEX_VERSION,
    CodexCapabilityManifest,
    StorageRuntimeCapabilities,
    validate_manifest_authority,
)
from .isolation import IsolationError, IsolationPathAuthority, IsolatedStateRoot, canonical_path
from .protocol import CodexProtocolClient, ProtocolState
from .subprocess_transport import DEFAULT_STDOUT_LINE_LIMIT_BYTES, SubprocessStdioTransport
from .version_probe import CodexVersionProbe, probe_supported_manifest

DEFAULT_INITIALIZE_TIMEOUT_SECONDS = 15.0
DEFAULT_GRACEFUL_SHUTDOWN_SECONDS = 2.0
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 2.0
DEFAULT_KILL_REAP_TIMEOUT_SECONDS = 2.0

class RuntimeErrorSafe(Exception):
    def __init__(self, category: str, profile_id: str) -> None:
        self.category, self.profile_id = category, profile_id
        super().__init__(f"{category}:profile={profile_id}")

class RuntimeState(Enum):
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAULTED = "faulted"

class ProcessLike(Protocol):
    stdin: asyncio.StreamWriter | None
    stdout: asyncio.StreamReader | None
    stderr: asyncio.StreamReader | None
    returncode: int | None
    async def wait(self) -> int: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...

ProcessFactory = Callable[[list[str], Mapping[str, str], int], Awaitable[ProcessLike]]
RuntimeHook = Callable[["CodexRuntime"], Awaitable[None]]
InstalledAuthorityProbe = Callable[[], Awaitable[CodexCapabilityManifest]]


@dataclass(frozen=True, repr=False)
class RuntimeQuiescenceProof:
    profile_id: str
    reserved: bool
    starting_child: bool
    ready_child: bool
    unresolved_child: bool

    @property
    def is_quiescent(self) -> bool:
        return self.reserved and not (self.starting_child or self.ready_child or self.unresolved_child)

    def __repr__(self) -> str:
        return (
            "RuntimeQuiescenceProof(profile_id=" + repr(self.profile_id)
            + f", reserved={self.reserved!r}, starting_child={self.starting_child!r}, "
            + f"ready_child={self.ready_child!r}, unresolved_child={self.unresolved_child!r})"
        )


@dataclass(frozen=True, repr=False)
class ProfileReservation:
    profile_id: str
    _manager: "CodexRuntimeManager" = field(repr=False, compare=False)
    _token: object = field(repr=False, compare=False)

    def quiescence_proof(self) -> RuntimeQuiescenceProof:
        return self._manager.quiescence_proof(self)

    async def release(self) -> None:
        await self._manager.release(self)

    def __repr__(self) -> str:
        return f"ProfileReservation(profile_id={self.profile_id!r})"


def build_child_environment(profile: CodexProfile, parent: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(profile.isolated_state_root, str) or not profile.isolated_state_root:
        raise RuntimeErrorSafe("isolated_state_root_required", profile.profile_id)
    environment = {
        "CODEX_HOME": canonical_path(profile.codex_home),
        "CODEX_SQLITE_HOME": canonical_path(os.path.join(profile.isolated_state_root, "sqlite")),
    }
    for key in ("HOME", "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        if value := parent.get(key): environment[key] = value
    return environment


def build_child_config_overrides(profile: CodexProfile) -> tuple[str, ...]:
    if not isinstance(profile.isolated_state_root, str) or not profile.isolated_state_root:
        raise RuntimeErrorSafe("isolated_state_root_required", profile.profile_id)
    sqlite_home = canonical_path(os.path.join(profile.isolated_state_root, "sqlite"))
    log_dir = canonical_path(os.path.join(profile.isolated_state_root, "logs"))
    return (
        "sqlite_home=" + json.dumps(sqlite_home),
        "log_dir=" + json.dumps(log_dir),
        "history.persistence=\"none\"",
    )


def build_child_argv(executable: str, profile: CodexProfile) -> list[str]:
    overrides = build_child_config_overrides(profile)
    return [executable, "app-server", "--stdio", "-c", overrides[0], "-c", overrides[1], "-c", overrides[2]]

async def create_codex_process(argv: list[str], environment: Mapping[str, str], stdout_limit: int) -> ProcessLike:
    return await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=dict(environment), limit=stdout_limit)

@dataclass
class CodexRuntime:
    profile_id: str; generation: int; process: ProcessLike; transport: SubprocessStdioTransport; client: CodexProtocolClient
    state: RuntimeState = RuntimeState.STARTING; stderr_bytes: int = 0; stderr_lines: int = 0
    watcher: asyncio.Task[None] | None = None; protocol_watcher: asyncio.Task[None] | None = None
    stderr_drain: asyncio.Task[None] | None = None; shutdown_lock: asyncio.Lock | None = None
    kill_reap_timed_out: bool = False

class CodexRuntimeManager:
    def __init__(self, profiles: list[CodexProfile], *, client_version: str, executable: str = "/usr/local/bin/codex",
                 parent_environment: Mapping[str, str] | None = None, process_factory: ProcessFactory = create_codex_process,
                 schema_sha256: str = SCHEMA_SHA256,
                 storage_capabilities: StorageRuntimeCapabilities | None = None,
                 isolation_authority: IsolationPathAuthority | None = None,
                 version_probe: CodexVersionProbe | None = None,
                 installed_authority_probe: InstalledAuthorityProbe | None = None,
                 stdout_line_limit: int = DEFAULT_STDOUT_LINE_LIMIT_BYTES, initialize_timeout: float = DEFAULT_INITIALIZE_TIMEOUT_SECONDS,
                 graceful_shutdown_timeout: float = DEFAULT_GRACEFUL_SHUTDOWN_SECONDS, terminate_timeout: float = DEFAULT_TERMINATE_TIMEOUT_SECONDS,
                 kill_reap_timeout: float = DEFAULT_KILL_REAP_TIMEOUT_SECONDS) -> None:
        if not client_version: raise ValueError("client_version_required")
        self._executable, self._client_version = executable, client_version
        authority = isolation_authority or IsolationPathAuthority(tuple(profiles))
        configured_profiles: dict[str, CodexProfile] = {}
        for profile in profiles:
            configured = authority._bound_profile(profile)
            configured_profiles[configured.profile_id] = configured
        if len(configured_profiles) != len(profiles): raise ValueError("duplicate_profile_id")
        self._profiles = configured_profiles
        self._storage_capabilities = storage_capabilities or StorageRuntimeCapabilities()
        # `client_version` is only CodexControl's protocol identity.  It is
        # intentionally never used as installed Codex authority.
        self._capability_failure: str | None = None
        self._version_probe = version_probe or CodexVersionProbe(executable)
        self._installed_authority_probe = installed_authority_probe
        self._installed_manifest: CodexCapabilityManifest | None = None
        self._authority_lock = asyncio.Lock()
        self._parent_environment = dict(os.environ if parent_environment is None else parent_environment)
        self._factory, self._stdout_line_limit = process_factory, stdout_line_limit
        self._initialize_timeout, self._graceful_timeout = initialize_timeout, graceful_shutdown_timeout
        self._terminate_timeout, self._kill_reap_timeout = terminate_timeout, kill_reap_timeout
        self._runtimes: dict[str, CodexRuntime] = {}; self._starting: dict[str, asyncio.Task[CodexRuntime]] = {}
        self._unresolved: dict[str, CodexRuntime] = {}; self._stopping: set[str] = set(); self._generations: dict[str, int] = {}
        self._lock = asyncio.Lock(); self._shutting_down = False
        self._reservations: dict[str, ProfileReservation] = {}
        self._isolation_authority = authority
        self._state_root = IsolatedStateRoot(self._isolation_authority)
        self._before_ready_publication: RuntimeHook | None = None
        self._before_watcher_update: RuntimeHook | None = None
        self._profile_shutdown_reserved: Callable[[str], Awaitable[None]] | None = None

    async def acquire(self, profile_id: str) -> CodexRuntime:
        async with self._lock:
            if self._capability_failure is not None: raise RuntimeErrorSafe(self._capability_failure, profile_id)
            if self._shutting_down: raise RuntimeErrorSafe("manager_shutting_down", profile_id)
            if profile_id not in self._profiles: raise RuntimeErrorSafe("unknown_profile", profile_id)
            if profile_id in self._reservations: raise RuntimeErrorSafe("profile_reserved", profile_id)
            if profile_id in self._stopping: raise RuntimeErrorSafe("profile_stopping", profile_id)
            if profile_id in self._unresolved: raise RuntimeErrorSafe("unresolved_process", profile_id)
            existing = self._runtimes.get(profile_id)
            if existing is not None and existing.state is RuntimeState.READY and existing.process.returncode is None and existing.client.state is ProtocolState.READY: return existing
            task = self._starting.get(profile_id)
            if task is None:
                generation = self._generations.get(profile_id, 0) + 1; self._generations[profile_id] = generation
                task = asyncio.create_task(self._start(self._profiles[profile_id], generation)); self._starting[profile_id] = task
        try: return await asyncio.shield(task)
        finally:
            if task.done():
                async with self._lock:
                    if self._starting.get(profile_id) is task: self._starting.pop(profile_id, None)

    async def _start(self, profile: CodexProfile, generation: int) -> CodexRuntime:
        process: ProcessLike | None = None; runtime: CodexRuntime | None = None; failure = RuntimeErrorSafe("startup_failed", profile.profile_id)
        try:
            try:
                self._isolation_authority.validate_profile_paths(profile)
                self._state_root.validate(profile)
            except IsolationError as error:
                raise RuntimeErrorSafe("storage_boundary_invalid", profile.profile_id) from error
            await self._ensure_installed_authority(profile.profile_id)
            executable = Path(self._executable)
            if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK): raise RuntimeErrorSafe("executable_invalid", profile.profile_id)
            process = await self._factory(build_child_argv(str(executable), profile), build_child_environment(profile, self._parent_environment), self._stdout_line_limit)
            if process.stdin is None or process.stdout is None or process.stderr is None: raise RuntimeErrorSafe("process_streams_missing", profile.profile_id)
            transport = SubprocessStdioTransport(process.stdout, process.stdin)
            runtime = CodexRuntime(profile.profile_id, generation, process, transport, CodexProtocolClient(transport, client_version=self._client_version), shutdown_lock=asyncio.Lock())
            runtime.stderr_drain = asyncio.create_task(self._drain_stderr(runtime)); runtime.watcher = asyncio.create_task(self._watch(runtime))
            await asyncio.wait_for(runtime.client.initialize(), timeout=self._initialize_timeout)
            if process.returncode is not None or runtime.client.state is not ProtocolState.READY: raise RuntimeErrorSafe("initialize_failed", profile.profile_id)
            if self._before_ready_publication is not None: await self._before_ready_publication(runtime)
            async with self._lock:
                # Sole READY-publication linearization point: no state can regress after it.
                if self._shutting_down: raise RuntimeErrorSafe("manager_shutting_down", profile.profile_id)
                if profile.profile_id in self._stopping: raise RuntimeErrorSafe("profile_stopping", profile.profile_id)
                if profile.profile_id in self._reservations: raise RuntimeErrorSafe("profile_reserved", profile.profile_id)
                if process.returncode is not None or runtime.client.state is not ProtocolState.READY: raise RuntimeErrorSafe("initialize_failed", profile.profile_id)
                runtime.state = RuntimeState.READY; self._runtimes[profile.profile_id] = runtime
            runtime.protocol_watcher = asyncio.create_task(self._watch_protocol(runtime)); return runtime
        except asyncio.CancelledError:
            if runtime is not None: await self._shutdown_runtime(runtime)
            elif process is not None: await self._reap_process(process)
            raise
        except asyncio.TimeoutError: failure = RuntimeErrorSafe("initialize_timeout", profile.profile_id)
        except RuntimeErrorSafe as error: failure = error
        except Exception: pass
        if runtime is not None:
            try: await self._shutdown_runtime(runtime)
            except RuntimeErrorSafe as error: failure = error
        elif process is not None: await self._reap_process(process)
        raise failure

    async def _ensure_installed_authority(self, profile_id: str) -> None:
        if self._capability_failure is not None:
            raise RuntimeErrorSafe(self._capability_failure, profile_id)
        if self._installed_manifest is not None:
            return
        async with self._authority_lock:
            if self._installed_manifest is not None:
                return
            try:
                if self._installed_authority_probe is None:
                    manifest = await probe_supported_manifest(self._version_probe)
                else:
                    manifest = await self._installed_authority_probe()
                manifest = validate_manifest_authority(manifest, SUPPORTED_CODEX_VERSION)
                self._storage_capabilities.validate(
                    installed_version=manifest.codex_cli_version,
                    installed_schema=manifest.schema_sha256,
                )
                self._installed_manifest = manifest
            except Exception as error:
                self._capability_failure = "capability_mismatch"
                raise RuntimeErrorSafe("capability_mismatch", profile_id) from error

    async def reserve(self, profile_id: str) -> ProfileReservation:
        async with self._lock:
            if self._shutting_down: raise RuntimeErrorSafe("manager_shutting_down", profile_id)
            if profile_id not in self._profiles: raise RuntimeErrorSafe("unknown_profile", profile_id)
            if profile_id in self._reservations: raise RuntimeErrorSafe("profile_reserved", profile_id)
            reservation = ProfileReservation(profile_id, self, object())
            self._reservations[profile_id] = reservation
            return reservation

    async def release(self, reservation: ProfileReservation) -> None:
        if not isinstance(reservation, ProfileReservation):
            raise RuntimeErrorSafe("reservation_token_invalid", "unknown")
        async with self._lock:
            current = self._reservations.get(reservation.profile_id)
            if current is not reservation or current._token is not reservation._token or current._manager is not self:
                raise RuntimeErrorSafe("reservation_token_invalid", reservation.profile_id)
            self._reservations.pop(reservation.profile_id, None)

    async def recreate_isolated_state_root(self, reservation: ProfileReservation) -> None:
        """Recreate only the configured root under this manager's lock."""
        if not isinstance(reservation, ProfileReservation):
            raise IsolationError("reservation_invalid")
        async with self._lock:
            current = self._reservations.get(reservation.profile_id)
            if current is not reservation or current._token is not reservation._token or current._manager is not self:
                raise IsolationError("reservation_invalid")
            profile = self._profiles.get(reservation.profile_id)
            if profile is None:
                raise IsolationError("unknown_profile")
            proof = self._quiescence_proof_locked(reservation)
            if not proof.is_quiescent:
                raise IsolationError("runtime_not_quiescent")
            try:
                self._state_root._recreate_bound(profile)
            except IsolationError:
                raise
            except Exception:
                raise IsolationError("state_root_recreate_failed") from None

    def _quiescence_proof_locked(self, reservation: ProfileReservation) -> RuntimeQuiescenceProof:
        current = self._reservations.get(reservation.profile_id)
        valid = current is reservation and current._token is reservation._token and current._manager is self
        runtime = self._runtimes.get(reservation.profile_id)
        return RuntimeQuiescenceProof(
            reservation.profile_id,
            valid,
            reservation.profile_id in self._starting,
            runtime is not None,
            reservation.profile_id in self._unresolved,
        )

    def quiescence_proof(self, reservation: ProfileReservation) -> RuntimeQuiescenceProof:
        return self._quiescence_proof_locked(reservation)

    async def _drain_stderr(self, runtime: CodexRuntime) -> None:
        assert runtime.process.stderr is not None
        try:
            while chunk := await runtime.process.stderr.read(65536): runtime.stderr_bytes += len(chunk); runtime.stderr_lines += chunk.count(b"\n")
        except (ConnectionError, OSError): pass

    async def _watch(self, runtime: CodexRuntime) -> None:
        await runtime.process.wait()
        if self._before_watcher_update is not None: await self._before_watcher_update(runtime)
        async with self._lock:
            if runtime.state not in (RuntimeState.STOPPING, RuntimeState.STOPPED):
                runtime.state = RuntimeState.FAULTED
                if self._runtimes.get(runtime.profile_id) is runtime: self._runtimes.pop(runtime.profile_id, None)
            if self._unresolved.get(runtime.profile_id) is runtime: self._unresolved.pop(runtime.profile_id, None)
        if runtime.state is RuntimeState.FAULTED: await runtime.client.close()

    async def _watch_protocol(self, runtime: CodexRuntime) -> None:
        await runtime.client.wait_terminal()
        async with self._lock:
            if runtime.state not in (RuntimeState.STOPPING, RuntimeState.STOPPED):
                runtime.state = RuntimeState.FAULTED
                if self._runtimes.get(runtime.profile_id) is runtime: self._runtimes.pop(runtime.profile_id, None)
                if runtime.process.returncode is None: self._unresolved[runtime.profile_id] = runtime

    async def shutdown_profile(self, profile_id: str) -> None:
        async with self._lock:
            self._stopping.add(profile_id); task = self._starting.get(profile_id); runtime = self._runtimes.get(profile_id)
        startup_cleanup_failure: RuntimeErrorSafe | None = None
        try:
            if self._profile_shutdown_reserved is not None: await self._profile_shutdown_reserved(profile_id)
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except RuntimeErrorSafe as error:
                    # A normal startup error is harmless only after the current
                    # ownership state below proves that cleanup completed.
                    startup_cleanup_failure = error
            # Cancellation can run _start() cleanup and install unresolved
            # ownership.  These values must be read after awaiting that task.
            async with self._lock:
                starting = self._starting.get(profile_id)
                if task is not None and starting is task and starting.done(): self._starting.pop(profile_id, None)
                runtime = self._runtimes.get(profile_id)
                unresolved = self._unresolved.get(profile_id)
            if runtime is not None: await self._shutdown_runtime(runtime)
            if unresolved is not None and unresolved is not runtime:
                if unresolved.kill_reap_timed_out:
                    if startup_cleanup_failure is not None:
                        raise startup_cleanup_failure
                    raise RuntimeErrorSafe("kill_reap_timeout", profile_id)
                await self._shutdown_runtime(unresolved)
            async with self._lock:
                unresolved = self._unresolved.get(profile_id)
            if unresolved is not None:
                if startup_cleanup_failure is not None:
                    raise startup_cleanup_failure
                if unresolved.kill_reap_timed_out:
                    raise RuntimeErrorSafe("kill_reap_timeout", profile_id)
                raise RuntimeErrorSafe("unresolved_process", profile_id)
            if startup_cleanup_failure is not None and startup_cleanup_failure.category == "kill_reap_timeout":
                # A bounded cleanup failure remains observable even if a late
                # watcher exit races with this final ownership observation.
                raise startup_cleanup_failure
        finally:
            async with self._lock: self._stopping.discard(profile_id)

    async def shutdown_all(self) -> None:
        async with self._lock:
            self._shutting_down = True; profiles = sorted(set(self._starting) | set(self._runtimes) | set(self._unresolved) | set(self._reservations))
        results = await asyncio.gather(*(self.shutdown_profile(p) for p in profiles), return_exceptions=True)
        failures = {profile: result for profile, result in zip(profiles, results) if isinstance(result, RuntimeErrorSafe)}
        async with self._lock:
            unresolved = {profile: runtime for profile, runtime in self._unresolved.items()}
        if unresolved:
            profile_id = sorted(unresolved)[0]
            failure = failures.get(profile_id)
            if failure is not None: raise failure
            if unresolved[profile_id].kill_reap_timed_out: raise RuntimeErrorSafe("kill_reap_timeout", profile_id)
            raise RuntimeErrorSafe("unresolved_process", profile_id)
        if failures: raise failures[sorted(failures)[0]]

    async def _shutdown_runtime(self, runtime: CodexRuntime) -> None:
        assert runtime.shutdown_lock is not None
        async with runtime.shutdown_lock:
            if runtime.state is RuntimeState.STOPPED: return
            runtime.state = RuntimeState.STOPPING; await runtime.client.close(); await runtime.transport.close_stdin()
            if not await self._reap_process(runtime.process):
                runtime.state = RuntimeState.FAULTED; runtime.kill_reap_timed_out = True
                async with self._lock:
                    if self._runtimes.get(runtime.profile_id) is runtime: self._runtimes.pop(runtime.profile_id, None)
                    self._unresolved[runtime.profile_id] = runtime
                raise RuntimeErrorSafe("kill_reap_timeout", runtime.profile_id)
            for task in (runtime.watcher, runtime.protocol_watcher, runtime.stderr_drain):
                if task is not None and task is not asyncio.current_task() and not task.done():
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass
            runtime.state = RuntimeState.STOPPED
            async with self._lock:
                if self._runtimes.get(runtime.profile_id) is runtime: self._runtimes.pop(runtime.profile_id, None)
                if self._unresolved.get(runtime.profile_id) is runtime: self._unresolved.pop(runtime.profile_id, None)

    async def _reap_process(self, process: ProcessLike) -> bool:
        if process.returncode is not None: return True
        try: await asyncio.wait_for(process.wait(), timeout=self._graceful_timeout); return True
        except asyncio.TimeoutError: process.terminate()
        try: await asyncio.wait_for(process.wait(), timeout=self._terminate_timeout); return True
        except asyncio.TimeoutError: process.kill()
        try: await asyncio.wait_for(process.wait(), timeout=self._kill_reap_timeout); return True
        except asyncio.TimeoutError: return False
