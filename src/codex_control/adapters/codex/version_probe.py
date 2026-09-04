"""Fixed-exec, bounded installed Codex version probe."""
from __future__ import annotations
import asyncio, os, re
from pathlib import Path
from typing import Mapping, Protocol

DEFAULT_VERSION_STDOUT_LIMIT_BYTES = 4096
DEFAULT_VERSION_TIMEOUT_SECONDS = 3.0
DEFAULT_VERSION_CLEANUP_TIMEOUT_SECONDS = 1.0
VERSION_ENV_ALLOWLIST = ("HOME", "PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR")

class VersionProbeError(Exception):
    def __init__(self, category: str) -> None: self.category = category; super().__init__(category)
class VersionProcess(Protocol):
    stdout: asyncio.StreamReader | None; stderr: asyncio.StreamReader | None; returncode: int | None
    async def wait(self) -> int: ...
    def terminate(self) -> None: ...
    def kill(self) -> None: ...

async def create_version_process(argv: list[str], environment: Mapping[str, str], stdout_limit: int) -> VersionProcess:
    return await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=dict(environment), limit=stdout_limit)

def version_environment(parent: Mapping[str, str]) -> dict[str, str]: return {k: parent[k] for k in VERSION_ENV_ALLOWLIST if parent.get(k)}
def parse_version_stdout(output: bytes) -> str:
    if not isinstance(output, bytes): raise VersionProbeError("version_output_invalid")
    try: lines = [line for line in output.decode("utf-8").splitlines() if line]
    except UnicodeDecodeError: raise VersionProbeError("version_output_invalid") from None
    if len(lines) != 1: raise VersionProbeError("version_output_invalid")
    match = re.fullmatch(r"codex-cli (\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)", lines[0])
    if match is None: raise VersionProbeError("version_output_invalid")
    return match.group(1)

class CodexVersionProbe:
    def __init__(self, executable: str = "/usr/local/bin/codex", *, parent_environment: Mapping[str,str] | None = None, process_factory=create_version_process, stdout_limit: int = DEFAULT_VERSION_STDOUT_LIMIT_BYTES, timeout: float = DEFAULT_VERSION_TIMEOUT_SECONDS, cleanup_timeout: float = DEFAULT_VERSION_CLEANUP_TIMEOUT_SECONDS) -> None:
        self.executable, self.parent_environment, self.process_factory = executable, dict(os.environ if parent_environment is None else parent_environment), process_factory
        self.stdout_limit, self.timeout, self.cleanup_timeout = stdout_limit, timeout, cleanup_timeout
    async def probe(self) -> str:
        executable = Path(self.executable)
        if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK): raise VersionProbeError("executable_invalid")
        if self.stdout_limit <= 0 or self.timeout <= 0 or self.cleanup_timeout <= 0: raise VersionProbeError("probe_configuration_invalid")
        try: process = await self.process_factory([str(executable), "--version"], version_environment(self.parent_environment), self.stdout_limit)
        except Exception: raise VersionProbeError("version_probe_failed") from None
        if process.stdout is None or process.stderr is None: await self._cleanup(process); raise VersionProbeError("version_probe_failed")
        stderr_task = asyncio.create_task(self._discard(process.stderr))
        try:
            output = await asyncio.wait_for(process.stdout.read(self.stdout_limit + 1), self.timeout)
            exit_code = await asyncio.wait_for(process.wait(), self.timeout)
        except asyncio.TimeoutError:
            await self._cleanup(process); raise VersionProbeError("version_probe_timeout") from None
        except Exception:
            await self._cleanup(process); raise VersionProbeError("version_probe_failed") from None
        finally:
            if not stderr_task.done(): stderr_task.cancel()
            try: await stderr_task
            except asyncio.CancelledError: pass
        if len(output) > self.stdout_limit: raise VersionProbeError("version_output_oversized")
        if exit_code != 0: raise VersionProbeError("version_probe_failed")
        return parse_version_stdout(output)
    async def _discard(self, stream: asyncio.StreamReader) -> None:
        while await stream.read(65536): pass
    async def _cleanup(self, process: VersionProcess) -> None:
        if process.returncode is not None: return
        process.terminate()
        try: await asyncio.wait_for(process.wait(), self.cleanup_timeout); return
        except asyncio.TimeoutError: process.kill()
        try: await asyncio.wait_for(process.wait(), self.cleanup_timeout)
        except asyncio.TimeoutError: pass

async def probe_supported_manifest(probe: CodexVersionProbe):
    """Probe first, then select only the exact version-labelled manifest."""
    from .capabilities import SUPPORTED_CODEX_VERSION, load_manifest
    version = await probe.probe()
    if version != SUPPORTED_CODEX_VERSION:
        raise VersionProbeError("unsupported_codex_version")
    return load_manifest(version)
