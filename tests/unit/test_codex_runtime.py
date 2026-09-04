import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from codex_control.adapters.codex.protocol import ProtocolState
from codex_control.adapters.codex.runtime import CodexRuntimeManager, RuntimeErrorSafe, RuntimeState, build_child_environment, create_codex_process
from codex_control.adapters.codex.subprocess_transport import DEFAULT_STDOUT_LINE_LIMIT_BYTES, SubprocessStdioTransport, SubprocessTransportError
from codex_control.domain import CodexProfile

TEST_VERSION = "0.1.0-test"

class Writer:
    def __init__(self, on_write=None, on_close=None): self.data, self.closed, self.on_write, self.on_close = [], False, on_write, on_close
    def write(self, data):
        self.data.append(data)
        if self.on_write: self.on_write(data)
    async def drain(self): pass
    def close(self):
        self.closed = True
        if self.on_close: self.on_close()
    async def wait_closed(self): pass

class Process:
    def __init__(self, response="success", exit_on_close=False, exit_on_terminate=True, exit_on_kill=True, stderr_payload=b""):
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader(); self.stderr.feed_data(stderr_payload); self.stderr.feed_eof(); self.returncode = None
        self._done = asyncio.Event(); self.terminate_calls = self.kill_calls = 0
        self.response, self.exit_on_terminate, self.exit_on_kill = response, exit_on_terminate, exit_on_kill
        self.stdin = Writer(self._respond, lambda: self.exit(0) if exit_on_close else None)
    def _respond(self, data):
        message = json.loads(data)
        if message.get("method") != "initialize": return
        if self.response == "success":
            payload = {"id": message["id"], "result": {"userAgent":"test", "codexHome":"/isolated", "platformFamily":"unix", "platformOs":"linux"}}
        elif self.response == "remote": payload = {"id": message["id"], "error": {"code": -1, "message": "secret"}}
        elif self.response == "invalid": payload = {"id": message["id"], "result": {"bad": "response"}}
        elif self.response == "exit": self.exit(7); return
        else: return
        self.stdout.feed_data(json.dumps(payload).encode() + b"\n")
    async def wait(self): await self._done.wait(); return self.returncode
    def exit(self, code=0):
        if self.returncode is None: self.returncode = code; self.stdout.feed_eof(); self._done.set()
    def terminate(self):
        self.terminate_calls += 1
        if self.exit_on_terminate: self.exit(-15)
    def kill(self):
        self.kill_calls += 1
        if self.exit_on_kill: self.exit(-9)

class Factory:
    def __init__(self, **kwargs): self.calls, self.processes, self.kwargs, self.created = [], [], kwargs, asyncio.Event()
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit)); process = Process(**self.kwargs); self.processes.append(process); self.created.set(); return process

class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_json_line_and_receive(self):
        reader, writer = asyncio.StreamReader(), Writer(); transport = SubprocessStdioTransport(reader, writer)
        await transport.send({"x":"y"}); self.assertEqual(writer.data, [b'{"x":"y"}\n'])
        reader.feed_data(b'{"ok":true}\n'); reader.feed_eof(); self.assertEqual(await transport.receive(), '{"ok":true}'); self.assertIsNone(await transport.receive())
    async def test_oversized_stdout_is_sanitized(self):
        reader = asyncio.StreamReader(limit=8); reader.feed_data(b"x" * 16 + b"\n")
        with self.assertRaisesRegex(SubprocessTransportError, "stdout_line_limit_exceeded") as raised: await SubprocessStdioTransport(reader, Writer()).receive()
        self.assertNotIn("x" * 16, repr(raised.exception))

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.executable = tempfile.NamedTemporaryFile(delete=False); self.executable.close(); os.chmod(self.executable.name, 0o755)
    def tearDown(self): os.unlink(self.executable.name)
    def manager(self, factory=None, **kwargs):
        return CodexRuntimeManager([CodexProfile("p", "/chosen", "P")], client_version=TEST_VERSION, executable=self.executable.name, process_factory=factory or Factory(), initialize_timeout=.05, graceful_shutdown_timeout=.01, terminate_timeout=.01, kill_reap_timeout=.01, **kwargs)

    def test_environment_filters_secrets_and_binds_profile(self):
        env = build_child_environment(CodexProfile("p", "/chosen", "P"), {"CODEX_HOME":"/parent", "PATH":"/bin", "SECRET_TOKEN":"fake", "OPENAI_API_KEY":"fake"})
        self.assertEqual(env["CODEX_HOME"], "/chosen"); self.assertEqual(env["PATH"], "/bin"); self.assertFalse({"SECRET_TOKEN", "OPENAI_API_KEY"} & env.keys())

    def test_client_version_is_required(self):
        with self.assertRaises(TypeError): CodexRuntimeManager([CodexProfile("p", "/chosen", "P")])

    async def test_default_factory_uses_exec_fixed_argv_and_no_shell(self):
        with patch("codex_control.adapters.codex.runtime.asyncio.create_subprocess_exec", new_callable=AsyncMock) as spawn:
            await create_codex_process([self.executable.name, "app-server", "--stdio"], {"PATH":"/bin"}, 123)
        args, kwargs = spawn.await_args
        self.assertEqual(args, (self.executable.name, "app-server", "--stdio")); self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["stdin"], asyncio.subprocess.PIPE); self.assertEqual(kwargs["stdout"], asyncio.subprocess.PIPE); self.assertEqual(kwargs["stderr"], asyncio.subprocess.PIPE)

    async def test_initialize_uses_explicit_codexcontrol_client_version(self):
        factory = Factory(); runtime = await self.manager(factory).acquire("p")
        init = json.loads(factory.processes[0].stdin.data[0]); self.assertEqual(init["params"]["clientInfo"]["version"], TEST_VERSION); self.assertNotEqual(TEST_VERSION, "0.144.6")
        await runtime.client.close()

    async def test_successful_single_flight_owns_one_child(self):
        factory = Factory(); manager = self.manager(factory)
        runtimes = await asyncio.gather(*(manager.acquire("p") for _ in range(5)))
        self.assertEqual(len(factory.processes), 1); self.assertTrue(all(runtime is runtimes[0] for runtime in runtimes))
        await manager.shutdown_all()

    async def test_runtime_not_returned_before_initialize_ready(self):
        factory = Factory(response="blocked"); manager = self.manager(factory); task = asyncio.create_task(manager.acquire("p")); await factory.created.wait()
        self.assertFalse(task.done()); self.assertNotIn("p", manager._runtimes); factory.processes[0]._respond(json.dumps({"method":"initialize", "id":1}).encode())
        # blocked fake intentionally cannot respond; release with a real protocol response.
        factory.processes[0].stdout.feed_data(b'{"id":1,"result":{"userAgent":"t","codexHome":"/x","platformFamily":"unix","platformOs":"linux"}}\n')
        runtime = await task; self.assertEqual(runtime.state, RuntimeState.READY); await manager.shutdown_all()

    async def test_initialize_remote_error_cleanup(self):
        factory = Factory(response="remote"); manager = self.manager(factory)
        with self.assertRaisesRegex(RuntimeErrorSafe, "startup_failed"): await manager.acquire("p")
        self.assertIsNotNone(factory.processes[0].returncode); self.assertNotIn("p", manager._runtimes)

    async def test_initialize_protocol_fault_cleanup(self):
        factory = Factory(response="invalid"); manager = self.manager(factory)
        with self.assertRaisesRegex(RuntimeErrorSafe, "startup_failed"): await manager.acquire("p")
        self.assertIsNotNone(factory.processes[0].returncode); self.assertNotIn("p", manager._runtimes)

    async def test_premature_exit_during_initialize_no_publish_or_restart(self):
        factory = Factory(response="exit"); manager = self.manager(factory)
        with self.assertRaises(RuntimeErrorSafe): await manager.acquire("p")
        self.assertEqual(len(factory.calls), 1); self.assertNotIn("p", manager._runtimes); self.assertIsNotNone(factory.processes[0].returncode)

    async def test_startup_failure_clears_single_flight_for_later_retry(self):
        factory = Factory(response="remote"); manager = self.manager(factory)
        results = await asyncio.gather(*(manager.acquire("p") for _ in range(3)), return_exceptions=True)
        self.assertEqual(len(factory.calls), 1); self.assertTrue(all(isinstance(r, RuntimeErrorSafe) for r in results))
        factory.kwargs["response"] = "success"; runtime = await manager.acquire("p"); self.assertEqual(runtime.generation, 2); await manager.shutdown_all()

    async def test_shutdown_profile_wins_before_ready_publication(self):
        factory = Factory(); manager = self.manager(factory); entered, release = asyncio.Event(), asyncio.Event()
        async def hook(runtime): entered.set(); await release.wait()
        manager._before_ready_publication = hook; acquire = asyncio.create_task(manager.acquire("p")); await entered.wait()
        reserved, cleanup = asyncio.Event(), asyncio.Event()
        async def reserved_hook(profile): reserved.set(); await cleanup.wait()
        manager._profile_shutdown_reserved = reserved_hook; shutdown = asyncio.create_task(manager.shutdown_profile("p")); await reserved.wait()
        with self.assertRaisesRegex(RuntimeErrorSafe, "profile_stopping"): await manager.acquire("p")
        cleanup.set(); release.set(); await shutdown
        with self.assertRaises(asyncio.CancelledError): await acquire
        self.assertNotIn("p", manager._runtimes); self.assertEqual(factory.processes[0].returncode, -15)

    async def test_shutdown_all_wins_before_ready_publication(self):
        factory = Factory(); manager = self.manager(factory); entered, release = asyncio.Event(), asyncio.Event()
        async def hook(runtime): entered.set(); await release.wait()
        manager._before_ready_publication = hook; acquire = asyncio.create_task(manager.acquire("p")); await entered.wait()
        reserved, cleanup = asyncio.Event(), asyncio.Event()
        async def reserved_hook(profile): reserved.set(); await cleanup.wait()
        manager._profile_shutdown_reserved = reserved_hook; shutdown = asyncio.create_task(manager.shutdown_all()); await reserved.wait(); cleanup.set(); release.set(); await shutdown
        with self.assertRaises(asyncio.CancelledError): await acquire
        self.assertNotIn("p", manager._runtimes); self.assertNotEqual(factory.processes[0].returncode, None)

    async def test_ready_publication_wins_then_shutdown_stops_exact_runtime(self):
        factory = Factory(); manager = self.manager(factory); runtime = await manager.acquire("p"); await manager.shutdown_profile("p")
        self.assertEqual(runtime.state, RuntimeState.STOPPED); self.assertEqual(len(factory.processes), 1); self.assertNotIn("p", manager._runtimes)

    async def test_graceful_shutdown_path(self):
        factory = Factory(exit_on_close=True); manager = self.manager(factory); runtime = await manager.acquire("p"); await manager.shutdown_profile("p")
        process = factory.processes[0]; self.assertTrue(process.stdin.closed); self.assertEqual(process.terminate_calls, 0); self.assertEqual(process.kill_calls, 0); self.assertEqual(runtime.state, RuntimeState.STOPPED)

    async def test_terminate_shutdown_path(self):
        factory = Factory(exit_on_close=False, exit_on_terminate=True); manager = self.manager(factory); runtime = await manager.acquire("p"); await manager.shutdown_profile("p")
        process = factory.processes[0]; self.assertEqual(process.terminate_calls, 1); self.assertEqual(process.kill_calls, 0); self.assertEqual(runtime.state, RuntimeState.STOPPED)

    async def test_kill_shutdown_path(self):
        factory = Factory(exit_on_close=False, exit_on_terminate=False, exit_on_kill=True); manager = self.manager(factory); runtime = await manager.acquire("p"); await manager.shutdown_profile("p")
        process = factory.processes[0]; self.assertEqual(process.terminate_calls, 1); self.assertEqual(process.kill_calls, 1); self.assertEqual(runtime.state, RuntimeState.STOPPED)

    async def test_kill_reap_timeout_faults_and_blocks_replacement(self):
        factory = Factory(exit_on_close=False, exit_on_terminate=False, exit_on_kill=False); manager = self.manager(factory); runtime = await manager.acquire("p")
        with self.assertRaisesRegex(RuntimeErrorSafe, "kill_reap_timeout"): await manager.shutdown_profile("p")
        self.assertEqual(runtime.state, RuntimeState.FAULTED); self.assertEqual(factory.processes[0].kill_calls, 1)
        with self.assertRaisesRegex(RuntimeErrorSafe, "unresolved_process"): await manager.acquire("p")
        self.assertEqual(len(factory.processes), 1); factory.processes[0].exit(); await runtime.watcher

    async def test_shutdown_idempotent_after_clean_stop(self):
        manager = self.manager(); runtime = await manager.acquire("p"); await manager.shutdown_profile("p"); await manager.shutdown_profile("p"); self.assertEqual(runtime.state, RuntimeState.STOPPED)

    async def test_stopped_runtime_never_becomes_ready_again(self):
        manager = self.manager(); runtime = await manager.acquire("p"); await manager.shutdown_profile("p")
        self.assertEqual(runtime.state, RuntimeState.STOPPED); self.assertEqual(runtime.state, RuntimeState.STOPPED)

    async def test_post_ready_protocol_fault_no_auto_restart_then_resolved_retry(self):
        factory = Factory(); manager = self.manager(factory); old = await manager.acquire("p")
        old.process.stdout.feed_data(b"not-json\n"); await old.client.wait_terminal(); await old.protocol_watcher
        self.assertEqual(old.state, RuntimeState.FAULTED); self.assertNotIn("p", manager._runtimes); self.assertEqual(len(factory.processes), 1)
        with self.assertRaisesRegex(RuntimeErrorSafe, "unresolved_process"): await manager.acquire("p")
        old.process.exit(7); await old.watcher; new = await manager.acquire("p"); self.assertEqual(new.generation, 2); await manager.shutdown_all()

    async def test_true_stale_watcher_race_cannot_remove_replacement(self):
        factory = Factory(); manager = self.manager(factory); old = await manager.acquire("p"); entered, release = asyncio.Event(), asyncio.Event()
        async def hook(runtime):
            if runtime is old: entered.set(); await release.wait()
        manager._before_watcher_update = hook; old.process.exit(7); await entered.wait()
        new = await manager.acquire("p"); self.assertEqual(new.generation, 2); release.set(); await old.watcher
        self.assertIs(manager._runtimes["p"], new); self.assertEqual(new.state, RuntimeState.READY); await manager.shutdown_all()

    async def test_stderr_counted_not_retained(self):
        payload = b"private-stderr-secret\n" * 20; factory = Factory(stderr_payload=payload); manager = self.manager(factory)
        runtime = await manager.acquire("p"); await runtime.stderr_drain
        self.assertEqual(runtime.stderr_bytes, len(payload)); self.assertEqual(runtime.stderr_lines, 20); self.assertNotIn("private-stderr-secret", repr(runtime)); await manager.shutdown_all()

if __name__ == "__main__": unittest.main()
