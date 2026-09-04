import asyncio
import os
import tempfile
import unittest
from codex_control.adapters.codex.version_probe import *
from codex_control.adapters.codex.capabilities import SUPPORTED_CODEX_VERSION

class FakeProcess:
    def __init__(self, out=b"codex-cli 0.144.6\n", code=0, running=False, exit_on_terminate=True, exit_on_kill=True, stderr=b"private stderr OPENAI_API_KEY=secret"):
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader()
        if out is not None: self.stdout.feed_data(out); self.stdout.feed_eof()
        self.stderr.feed_data(stderr); self.stderr.feed_eof()
        self.returncode = None; self.code = code; self.exit_on_terminate, self.exit_on_kill = exit_on_terminate, exit_on_kill
        self._exited = asyncio.Event(); self.terminated = self.killed = 0
        if not running: self.exit(code)
    async def wait(self): await self._exited.wait(); return self.returncode
    def exit(self, code=None):
        if self.returncode is None:
            self.returncode = self.code if code is None else code; self.stdout.feed_eof(); self.stderr.feed_eof(); self._exited.set()
    def terminate(self):
        self.terminated += 1
        if self.exit_on_terminate: self.exit(-15)
    def kill(self):
        self.killed += 1
        if self.exit_on_kill: self.exit(-9)

class Factory:
    def __init__(self, processes): self.processes = list(processes); self.calls = []; self.created = asyncio.Event(); self.gate = None
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit)); self.created.set()
        if self.gate is not None: await self.gate.wait()
        return self.processes.pop(0)

class CooperativeHungFactory:
    def __init__(self): self.calls = []; self.entered = asyncio.Event()
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit)); self.entered.set()
        await asyncio.Event().wait()

class CancellationResistantFactory:
    def __init__(self, late_process=None, late_error=False, late_cancel=False, next_process=None):
        self.calls = []; self.entered = asyncio.Event(); self.cancelled = asyncio.Event(); self.release = asyncio.Event()
        self.late_process, self.late_error, self.late_cancel, self.next_process = late_process, late_error, late_cancel, next_process
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit))
        if len(self.calls) > 1: return self.next_process
        self.entered.set()
        try: await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            await self.release.wait()
        if self.late_error: raise RuntimeError("private factory failure OPENAI_API_KEY=secret")
        if self.late_cancel: raise asyncio.CancelledError
        return self.late_process

class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fd, self.path = tempfile.mkstemp(); os.close(fd); os.chmod(self.path, 0o755)
    async def asyncTearDown(self): os.unlink(self.path)
    def probe(self, factory, **kwargs):
        return CodexVersionProbe(self.path, parent_environment={"PATH":"/bin", "OPENAI_API_KEY":"secret", "CODEX_HOME":"/bad"}, process_factory=factory, timeout=.01, cleanup_timeout=.01, **kwargs)
    async def test_valid_fixed_exec_and_secret_filter(self):
        factory = Factory([FakeProcess()]); probe = self.probe(factory)
        self.assertEqual(await probe.probe(), SUPPORTED_CODEX_VERSION)
        argv, env, _ = factory.calls[0]; self.assertEqual(argv, [self.path, "--version"]); self.assertEqual(env, {"PATH":"/bin"}); self.assertNotIn("CODEX_HOME", env)
        self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
    async def test_invalid_paths_and_malformed_output_are_safe(self):
        with self.assertRaises(VersionProbeError): await CodexVersionProbe("codex").probe()
        factory = Factory([FakeProcess(b"wrong\n")])
        probe = self.probe(factory)
        with self.assertRaisesRegex(VersionProbeError, "version_output_invalid"): await probe.probe()
        self.assertIsNone(probe._unresolved_process)
        self.assertEqual(parse_version_stdout(b"codex-cli 0.144.7\n"), "0.144.7")
    async def test_missing_absolute_executable_is_rejected_before_spawn(self):
        factory = Factory([])
        probe = CodexVersionProbe("/some/absolute/path/that/does/not/exist", parent_environment={"PATH": "/bin", "TEST_ONLY_ENV_NAME": "TEST_ONLY_ENV_VALUE_DOES_NOT_LEAK"}, process_factory=factory, timeout=.01, cleanup_timeout=.01)
        with self.assertRaisesRegex(VersionProbeError, "executable_invalid") as raised:
            await probe.probe()
        self.assertEqual(factory.calls, [])
        self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
        self.assertNotIn("TEST_ONLY_ENV_VALUE_DOES_NOT_LEAK", str(raised.exception) + repr(raised.exception))
    async def test_existing_non_executable_file_is_rejected_before_spawn(self):
        descriptor, path = tempfile.mkstemp()
        os.close(descriptor); os.chmod(path, 0o644)
        try:
            factory = Factory([])
            probe = CodexVersionProbe(path, parent_environment={"PATH": "/bin"}, process_factory=factory, timeout=.01, cleanup_timeout=.01)
            with self.assertRaisesRegex(VersionProbeError, "executable_invalid"):
                await probe.probe()
            self.assertEqual(factory.calls, [])
            self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
        finally:
            os.unlink(path)
    def test_malformed_semver_outputs_are_rejected(self):
        for output in (b"codex-cli 0.144\n", b"codex-cli 0.144.x\n", b"codex-cli v0.144.6\n", b"codex-cli 0.144.6 extra\n"):
            with self.subTest(output=output), self.assertRaisesRegex(VersionProbeError, "version_output_invalid"):
                parse_version_stdout(output)
    def test_multiple_nonempty_version_lines_are_rejected(self):
        with self.assertRaisesRegex(VersionProbeError, "version_output_invalid"):
            parse_version_stdout(b"codex-cli 0.144.6\nunexpected second line\n")
    async def test_nonzero_completed_process_releases_ownership(self):
        probe = self.probe(Factory([FakeProcess(code=2)]))
        with self.assertRaisesRegex(VersionProbeError, "version_probe_failed"): await probe.probe()
        self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
    async def test_oversized_stdout_is_rejected(self):
        probe = self.probe(Factory([FakeProcess(b"x" * 20)]), stdout_limit=10)
        with self.assertRaisesRegex(VersionProbeError, "version_output_oversized"): await probe.probe()
    async def test_timeout_terminate_exit_leaves_no_unresolved_ownership(self):
        process = FakeProcess(out=b"codex-cli 0.144.6\n", running=True, exit_on_terminate=True); probe = self.probe(Factory([process]))
        with self.assertRaisesRegex(VersionProbeError, "version_probe_timeout"): await probe.probe()
        self.assertEqual(process.terminated, 1); self.assertEqual(process.killed, 0); self.assertIsNone(probe._unresolved_process)
    async def test_timeout_kill_exit_leaves_no_unresolved_ownership(self):
        process = FakeProcess(out=b"codex-cli 0.144.6\n", running=True, exit_on_terminate=False, exit_on_kill=True); probe = self.probe(Factory([process]))
        with self.assertRaisesRegex(VersionProbeError, "version_probe_timeout"): await probe.probe()
        self.assertEqual(process.terminated, 1); self.assertEqual(process.killed, 1); self.assertIsNone(probe._unresolved_process)
    async def test_kill_reap_timeout_is_bounded_and_retains_exact_child(self):
        process = FakeProcess(out=b"codex-cli 0.144.6\n", running=True, exit_on_terminate=False, exit_on_kill=False); probe = self.probe(Factory([process]))
        with self.assertRaisesRegex(VersionProbeError, "version_probe_cleanup_unresolved") as raised:
            await asyncio.wait_for(probe.probe(), .2)
        self.assertIs(probe._unresolved_process, process); self.assertEqual(process.terminated, 1); self.assertEqual(process.killed, 1)
        self.assertNotIn("private stderr", str(raised.exception) + repr(raised.exception)); self.assertNotIn("OPENAI_API_KEY", str(raised.exception) + repr(raised.exception))
    async def test_probe_is_blocked_while_cleanup_unresolved_without_new_factory_call(self):
        process = FakeProcess(running=True, exit_on_terminate=False, exit_on_kill=False); factory = Factory([process]); probe = self.probe(factory)
        with self.assertRaisesRegex(VersionProbeError, "cleanup_unresolved"): await probe.probe()
        with self.assertRaisesRegex(VersionProbeError, "cleanup_unresolved"): await probe.probe()
        self.assertEqual(len(factory.calls), 1); process.exit(); await probe._unresolved_watcher
    async def test_late_exit_watcher_clears_ownership_and_explicit_probe_can_restart(self):
        old = FakeProcess(running=True, exit_on_terminate=False, exit_on_kill=False); new = FakeProcess(); factory = Factory([old, new]); probe = self.probe(factory)
        with self.assertRaisesRegex(VersionProbeError, "cleanup_unresolved"): await probe.probe()
        watcher = probe._unresolved_watcher; old.exit(); await watcher
        self.assertIsNone(probe._unresolved_process); self.assertIsNone(probe._unresolved_watcher)
        self.assertEqual(await probe.probe(), SUPPORTED_CODEX_VERSION); self.assertEqual(len(factory.calls), 2)
    async def test_concurrent_probe_is_busy_and_does_not_spawn_second_child(self):
        process = FakeProcess(running=True); factory = Factory([process, FakeProcess()]); probe = self.probe(factory)
        first = asyncio.create_task(probe.probe()); await factory.created.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_busy"): await probe.probe()
        self.assertEqual(len(factory.calls), 1); process.exit(); self.assertEqual(await first, SUPPORTED_CODEX_VERSION)
    async def test_unresolved_watcher_does_not_retry_or_signal_again(self):
        process = FakeProcess(running=True, exit_on_terminate=False, exit_on_kill=False); factory = Factory([process]); probe = self.probe(factory)
        with self.assertRaisesRegex(VersionProbeError, "cleanup_unresolved"): await probe.probe()
        self.assertEqual((process.terminated, process.killed, len(factory.calls)), (1, 1, 1))
        process.exit(); await probe._unresolved_watcher
        self.assertEqual((process.terminated, process.killed, len(factory.calls)), (1, 1, 1))
    async def test_spawn_timeout_cooperative_factory_creates_no_fake_process(self):
        factory = CooperativeHungFactory(); probe = self.probe(factory, spawn_timeout=.01)
        result = asyncio.create_task(probe.probe()); await factory.entered.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout") as raised:
            await asyncio.wait_for(result, .2)
        self.assertEqual(len(factory.calls), 1); self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
        self.assertIsNone(probe._unresolved_spawn_task); self.assertNotIn("OPENAI_API_KEY", str(raised.exception) + repr(raised.exception))
    async def test_unresolved_spawn_blocks_second_probe_without_second_factory_call(self):
        factory = CancellationResistantFactory(late_error=True); probe = self.probe(factory, spawn_timeout=.01)
        first = asyncio.create_task(probe.probe()); await factory.entered.wait(); await factory.cancelled.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout"): await asyncio.wait_for(first, .2)
        self.assertIsNotNone(probe._unresolved_spawn_task)
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_unresolved"): await probe.probe()
        self.assertEqual(len(factory.calls), 1)
        factory.release.set(); await probe._unresolved_spawn_watcher
    async def test_late_spawn_error_clears_ownership_and_allows_explicit_probe(self):
        factory = CancellationResistantFactory(late_error=True, next_process=FakeProcess()); probe = self.probe(factory, spawn_timeout=.01)
        first = asyncio.create_task(probe.probe()); await factory.entered.wait(); await factory.cancelled.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout"): await first
        watcher = probe._unresolved_spawn_watcher; factory.release.set(); await watcher
        self.assertIsNone(probe._unresolved_spawn_task); self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
        self.assertEqual(await probe.probe(), SUPPORTED_CODEX_VERSION); self.assertEqual(len(factory.calls), 2)
    async def test_late_spawn_cancellation_clears_ownership(self):
        factory = CancellationResistantFactory(late_cancel=True); probe = self.probe(factory, spawn_timeout=.01)
        first = asyncio.create_task(probe.probe()); await factory.entered.wait(); await factory.cancelled.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout"): await first
        watcher = probe._unresolved_spawn_watcher; factory.release.set(); await watcher
        self.assertIsNone(probe._unresolved_spawn_task); self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
    async def test_late_spawned_process_is_owned_cleaned_and_not_retried(self):
        process = FakeProcess(running=True, exit_on_terminate=False, exit_on_kill=True)
        factory = CancellationResistantFactory(late_process=process); probe = self.probe(factory, spawn_timeout=.01)
        first = asyncio.create_task(probe.probe()); await factory.entered.wait(); await factory.cancelled.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout"): await first
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_unresolved"): await probe.probe()
        factory.release.set(); watcher = probe._unresolved_spawn_watcher; await watcher
        self.assertEqual((process.terminated, process.killed), (1, 1)); self.assertIsNone(probe._owned_process); self.assertIsNone(probe._unresolved_process)
        self.assertIsNone(probe._unresolved_spawn_task); self.assertEqual(len(factory.calls), 1)
    async def test_late_spawned_cleanup_unresolved_transitions_to_process_ownership(self):
        process = FakeProcess(running=True, exit_on_terminate=False, exit_on_kill=False)
        factory = CancellationResistantFactory(late_process=process); probe = self.probe(factory, spawn_timeout=.01)
        first = asyncio.create_task(probe.probe()); await factory.entered.wait(); await factory.cancelled.wait()
        with self.assertRaisesRegex(VersionProbeError, "version_probe_spawn_timeout"): await first
        factory.release.set(); await probe._unresolved_spawn_watcher
        self.assertIs(probe._unresolved_process, process); self.assertIsNone(probe._unresolved_spawn_task)
        with self.assertRaisesRegex(VersionProbeError, "version_probe_cleanup_unresolved"): await probe.probe()
        self.assertEqual(len(factory.calls), 1); process.exit(); await probe._unresolved_watcher
        self.assertIsNone(probe._unresolved_process)
    async def test_exact_supported_version_selects_manifest(self):
        manifest = await probe_supported_manifest(self.probe(Factory([FakeProcess()])))
        self.assertEqual(manifest.codex_cli_version, SUPPORTED_CODEX_VERSION)
        with self.assertRaisesRegex(VersionProbeError, "unsupported_codex_version"):
            await probe_supported_manifest(self.probe(Factory([FakeProcess(b"codex-cli 0.144.7\n")])))
