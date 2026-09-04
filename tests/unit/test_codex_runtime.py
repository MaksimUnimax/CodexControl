import asyncio
import json
import os
import tempfile
import unittest

from codex_control.adapters.codex.protocol import ProtocolState
from codex_control.adapters.codex.runtime import (
    CodexRuntimeManager, RuntimeErrorSafe, RuntimeState,
    build_child_environment,
)
from codex_control.domain import CodexProfile
from codex_control.adapters.codex.subprocess_transport import (
    DEFAULT_STDOUT_LINE_LIMIT_BYTES, SubprocessStdioTransport, SubprocessTransportError,
)


class Writer:
    def __init__(self, on_write=None): self.data, self.closed, self.on_write = [], False, on_write
    def write(self, data):
        self.data.append(data)
        if self.on_write: self.on_write(data)
    async def drain(self): pass
    def close(self): self.closed = True
    async def wait_closed(self): pass


class Process:
    def __init__(self, initialize=True, stderr_payload=b""):
        self.stdout, self.stderr = asyncio.StreamReader(), asyncio.StreamReader()
        self.returncode = None
        self._done = asyncio.Event(); self.terminate_calls = self.kill_calls = 0
        self.stdin = Writer(self._respond if initialize else None)
        if stderr_payload: self.stderr.feed_data(stderr_payload)
        self.stderr.feed_eof()
    def _respond(self, data):
        message = json.loads(data)
        if message.get("method") == "initialize":
            self.stdout.feed_data(json.dumps({"id": message["id"], "result": {"userAgent":"test", "codexHome":"/isolated", "platformFamily":"unix", "platformOs":"linux"}}).encode() + b"\n")
    async def wait(self):
        await self._done.wait(); return self.returncode
    def exit(self, code=0):
        self.returncode = code; self.stdout.feed_eof(); self._done.set()
    def terminate(self): self.terminate_calls += 1; self.exit(-15)
    def kill(self): self.kill_calls += 1; self.exit(-9)


class Factory:
    def __init__(self, initialize=True, stderr_payload=b""): self.calls, self.processes, self.initialize, self.stderr_payload = [], [], initialize, stderr_payload
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit)); p = Process(self.initialize, self.stderr_payload)
        self.processes.append(p); return p


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_json_line_and_receive(self):
        reader, writer = asyncio.StreamReader(), Writer()
        transport = SubprocessStdioTransport(reader, writer)
        await transport.send({"x": "y"})
        self.assertEqual(writer.data, [b'{"x":"y"}\n'])
        reader.feed_data(b'{"ok":true}\n'); reader.feed_eof()
        self.assertEqual(await transport.receive(), '{"ok":true}')
        self.assertIsNone(await transport.receive())

    async def test_oversized_stdout_is_sanitized(self):
        reader = asyncio.StreamReader(limit=8); reader.feed_data(b"x" * 16 + b"\n")
        with self.assertRaisesRegex(SubprocessTransportError, "stdout_line_limit_exceeded") as raised:
            await SubprocessStdioTransport(reader, Writer()).receive()
        self.assertNotIn("x" * 16, repr(raised.exception))


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.executable = tempfile.NamedTemporaryFile(delete=False); self.executable.close(); os.chmod(self.executable.name, 0o755)
    def tearDown(self): os.unlink(self.executable.name)

    def test_environment_filters_secrets_and_binds_profile(self):
        env = build_child_environment(CodexProfile("p", "/chosen", "P"), {"CODEX_HOME":"/parent", "PATH":"/bin", "SECRET_TOKEN":"fake", "OPENAI_API_KEY":"fake", "TELEGRAM_BOT_TOKEN":"fake"})
        self.assertEqual(env["CODEX_HOME"], "/chosen"); self.assertEqual(env["PATH"], "/bin")
        self.assertFalse({"SECRET_TOKEN", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN"} & env.keys())

    async def test_single_flight_and_profile_isolation(self):
        factory = Factory(); manager = CodexRuntimeManager([CodexProfile("one", "/a", "One"), CodexProfile("any-profile", "/b", "Any")], executable=self.executable.name, process_factory=factory)
        runtimes = await asyncio.gather(*(manager.acquire("one") for _ in range(5)))
        self.assertEqual(len(factory.calls), 1); self.assertTrue(all(x is runtimes[0] for x in runtimes)); self.assertEqual(runtimes[0].state, RuntimeState.READY)
        second = await manager.acquire("any-profile")
        self.assertIsNot(second, runtimes[0]); self.assertEqual(len(factory.calls), 2)
        self.assertEqual(factory.calls[0][0], [self.executable.name, "app-server", "--stdio"])
        self.assertEqual(factory.calls[0][2], DEFAULT_STDOUT_LINE_LIMIT_BYTES)
        await manager.shutdown_all()

    async def test_timeout_cleans_up_and_later_acquire_retries(self):
        factory = Factory(initialize=False); manager = CodexRuntimeManager([CodexProfile("p", "/a", "P")], executable=self.executable.name, process_factory=factory, initialize_timeout=.01)
        with self.assertRaisesRegex(RuntimeErrorSafe, "initialize_timeout") as raised: await manager.acquire("p")
        self.assertNotIn("/a", repr(raised.exception)); self.assertIsNotNone(factory.processes[0].returncode)
        factory.initialize = True
        runtime = await manager.acquire("p")
        self.assertEqual(runtime.generation, 2); await manager.shutdown_all()

    async def test_shutdown_all_racing_startup_reaps_child(self):
        factory = Factory(initialize=False)
        manager = CodexRuntimeManager([CodexProfile("p", "/a", "P")], executable=self.executable.name, process_factory=factory)
        acquire = asyncio.create_task(manager.acquire("p"))
        while not factory.processes: await asyncio.sleep(0)
        await manager.shutdown_all()
        with self.assertRaises(asyncio.CancelledError): await acquire
        self.assertIsNotNone(factory.processes[0].returncode)

    async def test_exit_invalidates_without_restart_then_explicit_acquire_replaces(self):
        factory = Factory(); manager = CodexRuntimeManager([CodexProfile("p", "/a", "P")], executable=self.executable.name, process_factory=factory)
        old = await manager.acquire("p"); old.process.exit(7); await asyncio.sleep(0)
        self.assertEqual(old.state, RuntimeState.FAULTED); self.assertEqual(len(factory.calls), 1)
        new = await manager.acquire("p"); self.assertIsNot(new, old); self.assertEqual(new.generation, 2)
        # A stale old watcher cannot remove the replacement: it only removes by identity.
        self.assertIs(await manager.acquire("p"), new); await manager.shutdown_all()

    async def test_shutdown_is_idempotent_and_only_target_profile(self):
        factory = Factory(); manager = CodexRuntimeManager([CodexProfile("a", "/a", "A"), CodexProfile("b", "/b", "B")], executable=self.executable.name, process_factory=factory)
        a, b = await manager.acquire("a"), await manager.acquire("b")
        await manager.shutdown_profile("a"); await manager.shutdown_profile("a")
        self.assertEqual(a.state, RuntimeState.STOPPED); self.assertEqual(b.state, RuntimeState.READY)
        await manager.shutdown_all(); self.assertEqual(b.state, RuntimeState.STOPPED)

    async def test_spawn_failure_sanitized(self):
        manager = CodexRuntimeManager([CodexProfile("p", "/secret", "P")], executable="relative-codex")
        with self.assertRaisesRegex(RuntimeErrorSafe, "executable_invalid") as raised: await manager.acquire("p")
        self.assertNotIn("/secret", repr(raised.exception))

    async def test_stderr_is_counted_but_never_retained(self):
        secret_like = b"private-stderr-secret\n" * 2000
        factory = Factory(stderr_payload=secret_like)
        manager = CodexRuntimeManager([CodexProfile("p", "/a", "P")], executable=self.executable.name, process_factory=factory)
        runtime = await manager.acquire("p")
        await asyncio.sleep(0)
        self.assertEqual(runtime.stderr_bytes, len(secret_like))
        self.assertEqual(runtime.stderr_lines, 2000)
        self.assertNotIn("private-stderr-secret", repr(runtime))
        await manager.shutdown_all()


if __name__ == "__main__": unittest.main()
