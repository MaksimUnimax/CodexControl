"""Bounded, secret-free probe for the installed Codex executable version."""
from __future__ import annotations
import asyncio
import os
import re
from pathlib import Path
from typing import Mapping, Protocol

DEFAULT_VERSION_STDOUT_LIMIT_BYTES = 4096
DEFAULT_VERSION_TIMEOUT_SECONDS = 3.0
DEFAULT_VERSION_CLEANUP_TIMEOUT_SECONDS = 1.0
VERSION_ENV_ALLOWLIST = ("HOME", "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")

class VersionProbeError(Exception):
    """A categorized error which deliberately carries no process output or environment."""
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)

class VersionProcess(Protocol):
    stdout: asyncio.StreamReader | None
    stderr: asyncio.StreamReader | None
    returncode: int | None
    async def wait(self) -> int: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...

async def create_version_process(argv: list[str], environment: Mapping[str, str], stdout_limit: int) -> VersionProcess:
    return await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=dict(environment), limit=stdout_limit)

def version_environment(parent: Mapping[str, str]) -> dict[str, str]:
    return {key: parent[key] for key in VERSION_ENV_ALLOWLIST if parent.get(key)}

def parse_version_stdout(output: bytes) -> str:
    if not isinstance(output, bytes): raise VersionProbeError("version_output_invalid")
    try: lines = [line for line in output.decode("utf-8").splitlines() if line]
    except UnicodeDecodeError: raise VersionProbeError("version_output_invalid") from None
    if len(lines) != 1: raise VersionProbeError("version_output_invalid")
    match = re.fullmatch(r"codex-cli (\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)", lines[0])
    if match is None: raise VersionProbeError("version_output_invalid")
    return match.group(1)

class CodexVersionProbe:
    """Own at most one probe child; unresolved cleanup blocks later probes."""
    def __init__(self, executable: str = "/usr/local/bin/codex", *, parent_environment: Mapping[str, str] | None = None, process_factory=create_version_process, stdout_limit: int = DEFAULT_VERSION_STDOUT_LIMIT_BYTES, timeout: float = DEFAULT_VERSION_TIMEOUT_SECONDS, cleanup_timeout: float = DEFAULT_VERSION_CLEANUP_TIMEOUT_SECONDS) -> None:
        self.executable, self.parent_environment, self.process_factory = executable, dict(os.environ if parent_environment is None else parent_environment), process_factory
        self.stdout_limit, self.timeout, self.cleanup_timeout = stdout_limit, timeout, cleanup_timeout
        self._ownership_lock = asyncio.Lock(); self._probe_active = False; self._owned_process: VersionProcess | None = None
        self._unresolved_process: VersionProcess | None = None; self._unresolved_watcher: asyncio.Task[None] | None = None

    async def probe(self) -> str:
        await self._reserve_probe()
        process: VersionProcess | None = None; stderr_task: asyncio.Task[None] | None = None; wait_task: asyncio.Task[int] | None = None; handed_to_watcher = False
        try:
            executable = Path(self.executable)
            if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK): raise VersionProbeError("executable_invalid")
            if self.stdout_limit <= 0 or self.timeout <= 0 or self.cleanup_timeout <= 0: raise VersionProbeError("probe_configuration_invalid")
            try: process = await self.process_factory([str(executable), "--version"], version_environment(self.parent_environment), self.stdout_limit)
            except Exception: raise VersionProbeError("version_probe_failed") from None
            await self._record_owned(process); wait_task = asyncio.create_task(process.wait())
            if process.stdout is None or process.stderr is None:
                handed_to_watcher = await self._cleanup_or_retain(process, wait_task, None)
                raise VersionProbeError("version_probe_cleanup_unresolved" if handed_to_watcher else "version_probe_failed")
            stderr_task = asyncio.create_task(self._discard(process.stderr))
            try:
                output = await asyncio.wait_for(process.stdout.read(self.stdout_limit + 1), self.timeout)
                exit_code = await asyncio.wait_for(asyncio.shield(wait_task), self.timeout)
            except asyncio.TimeoutError:
                handed_to_watcher = await self._cleanup_or_retain(process, wait_task, stderr_task)
                raise VersionProbeError("version_probe_cleanup_unresolved" if handed_to_watcher else "version_probe_timeout") from None
            except asyncio.CancelledError:
                handed_to_watcher = await self._cleanup_or_retain(process, wait_task, stderr_task)
                if handed_to_watcher: raise VersionProbeError("version_probe_cleanup_unresolved") from None
                raise
            except Exception:
                handed_to_watcher = await self._cleanup_or_retain(process, wait_task, stderr_task)
                raise VersionProbeError("version_probe_cleanup_unresolved" if handed_to_watcher else "version_probe_failed") from None
            await self._clear_owned(process)
            if len(output) > self.stdout_limit: raise VersionProbeError("version_output_oversized")
            if exit_code != 0: raise VersionProbeError("version_probe_failed")
            return parse_version_stdout(output)
        finally:
            if stderr_task is not None and not handed_to_watcher: await self._stop_stderr_drain(stderr_task)
            if process is not None and process.returncode is not None: await self._clear_owned(process)
            await self._release_probe()

    async def _reserve_probe(self) -> None:
        async with self._ownership_lock:
            if self._unresolved_process is not None: raise VersionProbeError("version_probe_cleanup_unresolved")
            if self._probe_active: raise VersionProbeError("version_probe_busy")
            self._probe_active = True

    async def _release_probe(self) -> None:
        async with self._ownership_lock: self._probe_active = False

    async def _record_owned(self, process: VersionProcess) -> None:
        async with self._ownership_lock: self._owned_process = process

    async def _clear_owned(self, process: VersionProcess) -> None:
        async with self._ownership_lock:
            if self._owned_process is process: self._owned_process = None

    async def _cleanup_or_retain(self, process: VersionProcess, wait_task: asyncio.Task[int], stderr_task: asyncio.Task[None] | None) -> bool:
        if await self._cleanup(process, wait_task):
            await self._clear_owned(process)
            return False
        async with self._ownership_lock:
            self._owned_process = None; self._unresolved_process = process
            self._unresolved_watcher = asyncio.create_task(self._watch_unresolved(process, wait_task, stderr_task))
        return True

    async def _watch_unresolved(self, process: VersionProcess, wait_task: asyncio.Task[int], stderr_task: asyncio.Task[None] | None) -> None:
        try:
            await asyncio.shield(wait_task)
        except Exception:
            if process.returncode is None: return
        finally:
            if process.returncode is not None:
                if stderr_task is not None: await self._stop_stderr_drain(stderr_task)
                async with self._ownership_lock:
                    if self._unresolved_process is process:
                        self._unresolved_process = None; self._unresolved_watcher = None

    async def _discard(self, stream: asyncio.StreamReader) -> None:
        while await stream.read(65536): pass

    async def _stop_stderr_drain(self, task: asyncio.Task[None]) -> None:
        if not task.done(): task.cancel()
        try: await task
        except asyncio.CancelledError: pass

    async def _cleanup(self, process: VersionProcess, wait_task: asyncio.Task[int]) -> bool:
        if process.returncode is not None: return True
        try: process.terminate()
        except Exception: return False
        try:
            await asyncio.wait_for(asyncio.shield(wait_task), self.cleanup_timeout)
            return process.returncode is not None
        except (asyncio.TimeoutError, Exception): pass
        try: process.kill()
        except Exception: return False
        try:
            await asyncio.wait_for(asyncio.shield(wait_task), self.cleanup_timeout)
            return process.returncode is not None
        except (asyncio.TimeoutError, Exception): return False

async def probe_supported_manifest(probe: CodexVersionProbe):
    """Probe first, then select only the exact version-labelled manifest."""
    from .capabilities import SUPPORTED_CODEX_VERSION, load_manifest
    version = await probe.probe()
    if version != SUPPORTED_CODEX_VERSION: raise VersionProbeError("unsupported_codex_version")
    return load_manifest(version)
