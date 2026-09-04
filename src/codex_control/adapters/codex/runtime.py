"""Owned Codex app-server children and per-profile single-flight startup."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Mapping, Protocol

from codex_control.domain import CodexProfile
from .protocol import CodexProtocolClient, ProtocolState
from .subprocess_transport import DEFAULT_STDOUT_LINE_LIMIT_BYTES, SubprocessStdioTransport

DEFAULT_INITIALIZE_TIMEOUT_SECONDS = 15.0
DEFAULT_GRACEFUL_SHUTDOWN_SECONDS = 2.0
DEFAULT_TERMINATE_TIMEOUT_SECONDS = 2.0


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


def build_child_environment(profile: CodexProfile, parent: Mapping[str, str]) -> dict[str, str]:
    """Create the deliberately small child environment without secret inheritance."""
    environment = {"CODEX_HOME": profile.codex_home}
    for key in ("HOME", "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"):
        value = parent.get(key)
        if value:
            environment[key] = value
    environment["CODEX_HOME"] = profile.codex_home
    return environment


async def create_codex_process(argv: list[str], environment: Mapping[str, str], stdout_limit: int) -> ProcessLike:
    return await asyncio.create_subprocess_exec(
        *argv, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, env=dict(environment), limit=stdout_limit,
    )


@dataclass
class CodexRuntime:
    profile_id: str
    generation: int
    process: ProcessLike
    transport: SubprocessStdioTransport
    client: CodexProtocolClient
    state: RuntimeState = RuntimeState.STARTING
    stderr_bytes: int = 0
    stderr_lines: int = 0
    watcher: asyncio.Task[None] | None = None
    protocol_watcher: asyncio.Task[None] | None = None
    stderr_drain: asyncio.Task[None] | None = None
    shutdown_lock: asyncio.Lock | None = None


class CodexRuntimeManager:
    def __init__(self, profiles: list[CodexProfile], *, executable: str = "/usr/local/bin/codex",
                 client_version: str = "0.144.6", parent_environment: Mapping[str, str] | None = None,
                 process_factory: ProcessFactory = create_codex_process,
                 stdout_line_limit: int = DEFAULT_STDOUT_LINE_LIMIT_BYTES,
                 initialize_timeout: float = DEFAULT_INITIALIZE_TIMEOUT_SECONDS,
                 graceful_shutdown_timeout: float = DEFAULT_GRACEFUL_SHUTDOWN_SECONDS,
                 terminate_timeout: float = DEFAULT_TERMINATE_TIMEOUT_SECONDS) -> None:
        self._profiles = {profile.profile_id: profile for profile in profiles}
        if len(self._profiles) != len(profiles):
            raise ValueError("duplicate_profile_id")
        self._executable, self._client_version = executable, client_version
        self._parent_environment = dict(os.environ if parent_environment is None else parent_environment)
        self._factory, self._stdout_line_limit = process_factory, stdout_line_limit
        self._initialize_timeout = initialize_timeout
        self._graceful_timeout, self._terminate_timeout = graceful_shutdown_timeout, terminate_timeout
        self._runtimes: dict[str, CodexRuntime] = {}
        self._starting: dict[str, asyncio.Task[CodexRuntime]] = {}
        self._generations: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._shutting_down = False

    async def acquire(self, profile_id: str) -> CodexRuntime:
        async with self._lock:
            if self._shutting_down:
                raise RuntimeErrorSafe("manager_shutting_down", profile_id)
            if profile_id not in self._profiles:
                raise RuntimeErrorSafe("unknown_profile", profile_id)
            existing = self._runtimes.get(profile_id)
            if existing is not None and existing.state is RuntimeState.READY and existing.process.returncode is None and existing.client.state is ProtocolState.READY:
                return existing
            task = self._starting.get(profile_id)
            if task is None:
                generation = self._generations.get(profile_id, 0) + 1
                self._generations[profile_id] = generation
                task = asyncio.create_task(self._start(self._profiles[profile_id], generation))
                self._starting[profile_id] = task
        try:
            return await asyncio.shield(task)
        finally:
            if task.done():
                async with self._lock:
                    if self._starting.get(profile_id) is task:
                        self._starting.pop(profile_id, None)

    async def _start(self, profile: CodexProfile, generation: int) -> CodexRuntime:
        process: ProcessLike | None = None
        runtime: CodexRuntime | None = None
        startup_error: RuntimeErrorSafe = RuntimeErrorSafe("startup_failed", profile.profile_id)
        try:
            executable = Path(self._executable)
            if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
                raise RuntimeErrorSafe("executable_invalid", profile.profile_id)
            argv = [str(executable), "app-server", "--stdio"]
            process = await self._factory(argv, build_child_environment(profile, self._parent_environment), self._stdout_line_limit)
            if process.stdin is None or process.stdout is None or process.stderr is None:
                raise RuntimeErrorSafe("process_streams_missing", profile.profile_id)
            transport = SubprocessStdioTransport(process.stdout, process.stdin)
            runtime = CodexRuntime(profile.profile_id, generation, process, transport,
                                  CodexProtocolClient(transport, client_version=self._client_version), shutdown_lock=asyncio.Lock())
            runtime.stderr_drain = asyncio.create_task(self._drain_stderr(runtime))
            runtime.watcher = asyncio.create_task(self._watch(runtime))
            await asyncio.wait_for(runtime.client.initialize(), timeout=self._initialize_timeout)
            if process.returncode is not None or runtime.client.state is not ProtocolState.READY:
                raise RuntimeErrorSafe("initialize_failed", profile.profile_id)
            async with self._lock:
                if self._shutting_down:
                    raise RuntimeErrorSafe("manager_shutting_down", profile.profile_id)
                self._runtimes[profile.profile_id] = runtime
            runtime.state = RuntimeState.READY
            runtime.protocol_watcher = asyncio.create_task(self._watch_protocol(runtime))
            return runtime
        except asyncio.CancelledError:
            if runtime is not None:
                await self._shutdown_runtime(runtime)
            elif process is not None:
                await self._reap_process(process)
            raise
        except asyncio.TimeoutError:
            startup_error = RuntimeErrorSafe("initialize_timeout", profile.profile_id)
        except RuntimeErrorSafe as caught:
            startup_error = caught
        except Exception:
            startup_error = RuntimeErrorSafe("startup_failed", profile.profile_id)
        if runtime is not None:
            await self._shutdown_runtime(runtime)
        elif process is not None:
            await self._reap_process(process)
        raise startup_error

    async def _drain_stderr(self, runtime: CodexRuntime) -> None:
        assert runtime.process.stderr is not None
        try:
            while chunk := await runtime.process.stderr.read(65536):
                runtime.stderr_bytes += len(chunk)
                runtime.stderr_lines += chunk.count(b"\n")
        except (ConnectionError, OSError):
            pass

    async def _watch(self, runtime: CodexRuntime) -> None:
        code = await runtime.process.wait()
        if runtime.state not in (RuntimeState.STOPPING, RuntimeState.STOPPED):
            runtime.state = RuntimeState.FAULTED
            await runtime.client.close()
            async with self._lock:
                if self._runtimes.get(runtime.profile_id) is runtime:
                    self._runtimes.pop(runtime.profile_id, None)

    async def _watch_protocol(self, runtime: CodexRuntime) -> None:
        state = await runtime.client.wait_terminal()
        if runtime.state not in (RuntimeState.STOPPING, RuntimeState.STOPPED):
            runtime.state = RuntimeState.FAULTED
            async with self._lock:
                if self._runtimes.get(runtime.profile_id) is runtime:
                    self._runtimes.pop(runtime.profile_id, None)

    async def shutdown_profile(self, profile_id: str) -> None:
        async with self._lock:
            task = self._starting.get(profile_id)
            runtime = self._runtimes.get(profile_id)
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, RuntimeErrorSafe):
                pass
        if runtime is not None:
            await self._shutdown_runtime(runtime)

    async def shutdown_all(self) -> None:
        async with self._lock:
            self._shutting_down = True
            profiles = set(self._starting) | set(self._runtimes)
        await asyncio.gather(*(self.shutdown_profile(profile) for profile in profiles))

    async def _shutdown_runtime(self, runtime: CodexRuntime) -> None:
        assert runtime.shutdown_lock is not None
        async with runtime.shutdown_lock:
            if runtime.state is RuntimeState.STOPPED:
                return
            runtime.state = RuntimeState.STOPPING
            await runtime.client.close()
            await runtime.transport.close_stdin()
            await self._reap_process(runtime.process)
            if runtime.watcher is not None and runtime.watcher is not asyncio.current_task() and not runtime.watcher.done():
                await runtime.watcher
            if runtime.protocol_watcher is not None and not runtime.protocol_watcher.done():
                await runtime.protocol_watcher
            if runtime.stderr_drain is not None and not runtime.stderr_drain.done():
                await runtime.stderr_drain
            runtime.state = RuntimeState.STOPPED
            async with self._lock:
                if self._runtimes.get(runtime.profile_id) is runtime:
                    self._runtimes.pop(runtime.profile_id, None)

    async def _reap_process(self, process: ProcessLike) -> None:
        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), timeout=self._graceful_timeout)
            except asyncio.TimeoutError:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=self._terminate_timeout)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
