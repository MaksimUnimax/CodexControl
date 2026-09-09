import asyncio
import json
import os
import stat
import tempfile
import unittest

from codex_control.adapters.codex.capabilities import SCHEMA_SHA256, SUPPORTED_CODEX_VERSION, StorageRuntimeCapabilities
from codex_control.adapters.codex.isolation import (
    IsolationError,
    IsolationPathAuthority,
    IsolatedStateRoot,
    STATE_ROOT_MARKER,
)
from codex_control.adapters.codex.runtime import (
    CodexRuntimeManager,
    ProfileReservation,
    RuntimeErrorSafe,
    build_child_argv,
    build_child_config_overrides,
    build_child_environment,
)
from codex_control.config import ConfigurationError, parse_server_configuration
from codex_control.domain import CodexProfile


def _configuration(profiles, **extra):
    value = {
        "server": {"server_id": "server", "display_name": "Server"},
        "profiles": [
            {"profile_id": p[0], "codex_home": p[1], "display_name": p[2], "isolated_state_root": p[3]}
            for p in profiles
        ],
    }
    value.update(extra)
    return value


class ConfigurationAuthorityTests(unittest.TestCase):
    def test_valid_profile_has_explicit_distinct_root(self):
        config = parse_server_configuration(_configuration([("p", "/srv/p", "P", "/var/lib/codexcontrol/p")]))
        self.assertEqual(config.profiles[0].isolated_state_root, "/var/lib/codexcontrol/p")
        self.assertNotIn("/srv/p", repr(config))
        self.assertNotIn("/var/lib/codexcontrol/p", repr(config))

    def test_profile_path_rejections(self):
        cases = {
            "missing": {"profile_id": "p", "codex_home": "/home/p", "display_name": "P"},
            "relative_home": {"profile_id": "p", "codex_home": "home/p", "display_name": "P", "isolated_state_root": "/state/p"},
            "relative_root": {"profile_id": "p", "codex_home": "/home/p", "display_name": "P", "isolated_state_root": "state/p"},
            "nul": {"profile_id": "p", "codex_home": "/home/p\x00x", "display_name": "P", "isolated_state_root": "/state/p"},
        }
        for name, item in cases.items():
            with self.subTest(name=name), self.assertRaises(ConfigurationError):
                parse_server_configuration({"server": {"server_id": "s", "display_name": "S"}, "profiles": [item]})

    def test_duplicate_and_overlap_rejections(self):
        cases = [
            _configuration([("a", "/home/a", "A", "/state/x"), ("b", "/home/b", "B", "/state/./x")]),
            _configuration([("a", "/home/a", "A", "/state/a"), ("b", "/home/./a", "B", "/state/b")]),
            _configuration([("a", "/home/a", "A", "/home/a")]),
            _configuration([("a", "/home/a", "A", "/home/a/state")]),
            _configuration([("a", "/home/a/state", "A", "/home/a")]),
            _configuration([("a", "/profiles/a", "A", "/profiles/a/state"), ("b", "/profiles/b", "B", "/profiles/a/other")]),
            _configuration([("a", "/home/a", "A", "/state/a")], repository_root="/home"),
            _configuration([("a", "/home/a", "A", "/state/a")], controller_db_path="/state/a/controller.sqlite"),
            _configuration([("a", "/home/a", "A", "/state/a")], protected_roots=["/state"]),
        ]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(ConfigurationError):
                parse_server_configuration(value)

    def test_symlink_alias_is_rejected_without_resolving_through_it(self):
        with tempfile.TemporaryDirectory() as directory:
            real = os.path.join(directory, "real"); state = os.path.join(directory, "state")
            os.mkdir(real); os.mkdir(state); alias = os.path.join(directory, "alias"); os.symlink(real, alias)
            with self.assertRaises(ConfigurationError):
                parse_server_configuration(_configuration([("p", alias, "P", state)]))

    def test_profile_repr_never_contains_either_sensitive_absolute_path(self):
        profile = CodexProfile("p", "/private/home", "P", "/private/state")
        self.assertNotIn("/private/home", repr(profile))
        self.assertNotIn("/private/state", repr(profile))


class StateRootAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = self.temp.name
        self.home = os.path.join(self.parent, "home"); self.root = os.path.join(self.parent, "state")
        self.sibling = os.path.join(self.parent, "sibling"); self.controller = os.path.join(self.parent, "controller.sqlite")
        os.mkdir(self.home, 0o700); os.mkdir(self.sibling, 0o700); open(self.controller, "wb").close()
        self.profile = CodexProfile("profile", self.home, "Profile", self.root)
        self.authority = IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=os.path.join(self.parent, "repo"))
        self.roots = IsolatedStateRoot(self.authority)
        self.roots.provision(self.profile)

    def tearDown(self):
        self.temp.cleanup()

    def test_valid_layout_and_required_permissions(self):
        self.roots.validate(self.profile)
        self.assertEqual(set(os.listdir(self.root)), {STATE_ROOT_MARKER, "sqlite", "logs"})
        self.assertEqual(stat.S_IMODE(os.lstat(self.root).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.lstat(os.path.join(self.root, STATE_ROOT_MARKER)).st_mode), 0o600)

    def test_root_ownership_and_permission_gates(self):
        os.chmod(self.root, 0o770)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chmod(self.root, 0o700)
        os.chmod(self.root, 0o707)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chmod(self.root, 0o700)
        os.chown(self.root, 65534, 65534)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chown(self.root, 0, 0)
        os.chmod(self.home, 0o770)
        with self.assertRaises(IsolationError): self.authority.validate_profile_paths(self.profile)
        os.chmod(self.home, 0o700)

    def test_symlink_marker_and_foreign_entry_gates(self):
        marker = os.path.join(self.root, STATE_ROOT_MARKER)
        os.unlink(marker); os.symlink(os.path.join(self.parent, "outside"), marker)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.unlink(marker)
        with open(marker, "wb") as handle: handle.write(b"bad")
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chmod(marker, 0o640)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chmod(marker, 0o600)
        os.chown(marker, 65534, 65534)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chown(marker, 0, 0)
        os.unlink(marker)
        with open(marker, "wb") as handle: handle.write(b"format=codexcontrol-state-root-v1\nprofile_id=profile\n")
        os.chmod(marker, 0o600)
        foreign = os.path.join(self.root, "unexpected"); open(foreign, "wb").close()
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.unlink(foreign)
        os.mkdir(foreign, 0o700)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.rmdir(foreign)
        self.roots.validate(self.profile)

    def test_nested_symlink_special_and_foreign_owner_gates(self):
        nested = os.path.join(self.root, "sqlite", "nested"); os.mkdir(nested, 0o700)
        os.symlink(self.home, os.path.join(nested, "escape"))
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.unlink(os.path.join(nested, "escape")); os.mkfifo(os.path.join(nested, "fifo"))
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.unlink(os.path.join(nested, "fifo")); os.chown(nested, 65534, 65534)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)
        os.chown(nested, 0, 0)

    def test_root_symlink_and_ancestor_symlink_fail_closed(self):
        target = os.path.join(self.parent, "target"); os.mkdir(target, 0o700)
        linked = os.path.join(self.parent, "linked"); os.symlink(target, linked)
        linked_profile = CodexProfile("linked", self.home, "Linked", linked)
        linked_authority = IsolationPathAuthority((linked_profile,), require_global_roots=False)
        with self.assertRaises(IsolationError): IsolatedStateRoot(linked_authority).validate(linked_profile)
        ancestor = os.path.join(self.parent, "ancestor"); os.symlink(self.parent, ancestor)
        ancestor_profile = CodexProfile("ancestor", self.home, "Ancestor", os.path.join(ancestor, "state"))
        with self.assertRaises(IsolationError): IsolationPathAuthority((ancestor_profile,), require_global_roots=False).validate_profile_paths(ancestor_profile, state_root_may_be_missing=True)

    def test_recreate_is_bounded_idempotent_and_preserves_parent_sibling_controller(self):
        with open(os.path.join(self.root, "sqlite", "codex.sqlite"), "wb") as handle: handle.write(b"synthetic")
        with open(os.path.join(self.root, "logs", "codex.log"), "wb") as handle: handle.write(b"synthetic")
        with open(os.path.join(self.sibling, "keep"), "wb") as handle: handle.write(b"keep")
        with open(os.path.join(self.parent, "keep"), "wb") as handle: handle.write(b"keep")
        async def recreate_twice():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                schema_sha256=SCHEMA_SHA256, isolation_authority=self.authority,
            )
            reservation = await manager.reserve("profile")
            self.roots.recreate(self.profile, reservation=reservation)
            self.roots.recreate(self.profile, reservation=reservation)
            await reservation.release()

        asyncio.run(recreate_twice())
        self.roots.validate(self.profile)
        self.assertFalse(os.path.exists(os.path.join(self.root, "sqlite", "codex.sqlite")))
        self.assertTrue(os.path.exists(os.path.join(self.sibling, "keep")))
        self.assertTrue(os.path.exists(os.path.join(self.parent, "keep")))
        self.assertTrue(os.path.exists(self.controller))

    def test_recreate_requires_exact_reservation_and_quiescence(self):
        with self.assertRaises(IsolationError): self.roots.recreate(self.profile, reservation=None)
        with self.assertRaises(IsolationError): self.roots.recreate(self.profile, reservation=object())

        async def recreate_with_busy_runtime():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                schema_sha256=SCHEMA_SHA256, isolation_authority=self.authority,
            )
            reservation = await manager.reserve("profile")
            manager._runtimes["profile"] = object()
            with self.assertRaises(IsolationError):
                self.roots.recreate(self.profile, reservation=reservation)
            await reservation.release()

        asyncio.run(recreate_with_busy_runtime())

    def test_recreate_rejects_symlink_substitution_before_mutation(self):
        sqlite = os.path.join(self.root, "sqlite"); os.rename(sqlite, sqlite + ".saved"); os.symlink(self.home, sqlite)

        async def recreate_with_substitution():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                schema_sha256=SCHEMA_SHA256, isolation_authority=self.authority,
            )
            reservation = await manager.reserve("profile")
            with self.assertRaises(IsolationError):
                self.roots.recreate(self.profile, reservation=reservation)
            await reservation.release()

        asyncio.run(recreate_with_substitution())


class _FakeWriter:
    def __init__(self, process): self.process = process; self.data = []; self.closed = False
    def write(self, value):
        self.data.append(value)
        message = json.loads(value)
        if message.get("method") == "initialize":
            self.process.stdout.feed_data((json.dumps({"id": message["id"], "result": {"userAgent": "fake", "codexHome": "/fake", "platformFamily": "unix", "platformOs": "linux"}}) + "\n").encode())
    async def drain(self): pass
    def close(self): self.closed = True
    async def wait_closed(self): pass


class _FakeProcess:
    def __init__(self):
        self.stdout = asyncio.StreamReader(); self.stderr = asyncio.StreamReader(); self.stderr.feed_eof(); self.returncode = None
        self.done = asyncio.Event(); self.terminate_calls = 0; self.kill_calls = 0; self.stdin = _FakeWriter(self)
    async def wait(self): await self.done.wait(); return self.returncode
    def terminate(self): self.terminate_calls += 1; self.exit(-15)
    def kill(self): self.kill_calls += 1; self.exit(-9)
    def exit(self, code=0):
        if self.returncode is None: self.returncode = code; self.stdout.feed_eof(); self.done.set()


class _FakeFactory:
    def __init__(self): self.calls = []; self.processes = []; self.created = asyncio.Event()
    async def __call__(self, argv, env, limit):
        self.calls.append((argv, dict(env), limit)); process = _FakeProcess(); self.processes.append(process); self.created.set(); return process


class ReservationRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.home = os.path.join(self.temp.name, "home"); self.state = os.path.join(self.temp.name, "state")
        self.repository = os.path.join(self.temp.name, "repository"); self.controller = os.path.join(self.temp.name, "controller.sqlite")
        os.mkdir(self.home, 0o700); os.mkdir(self.repository, 0o700); open(self.controller, "wb").close()
        self.profile = CodexProfile("p", self.home, "P", self.state)
        self.authority = IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository); IsolatedStateRoot(self.authority).provision(self.profile)
        self.executable = os.path.join(self.temp.name, "codex"); open(self.executable, "wb").close(); os.chmod(self.executable, 0o755)
    async def asyncTearDown(self): self.temp.cleanup()
    def manager(self, factory, **kwargs):
        kwargs.setdefault("client_version", SUPPORTED_CODEX_VERSION); kwargs.setdefault("schema_sha256", SCHEMA_SHA256)
        return CodexRuntimeManager([self.profile], executable=self.executable, process_factory=factory, isolation_authority=self.authority, initialize_timeout=.05, graceful_shutdown_timeout=.01, terminate_timeout=.01, kill_reap_timeout=.01, **kwargs)

    async def test_reserve_blocks_acquire_and_valid_release_allows_future_acquire(self):
        factory = _FakeFactory(); manager = self.manager(factory); reservation = await manager.reserve("p")
        with self.assertRaisesRegex(RuntimeErrorSafe, "profile_reserved"): await manager.acquire("p")
        self.assertEqual(factory.calls, [])
        await reservation.release(); await manager.acquire("p"); self.assertEqual(len(factory.calls), 1); await manager.shutdown_all()

    async def test_ready_reservation_blocks_new_acquire_but_shutdown_is_legal(self):
        factory = _FakeFactory(); manager = self.manager(factory); runtime = await manager.acquire("p"); reservation = await manager.reserve("p")
        with self.assertRaisesRegex(RuntimeErrorSafe, "profile_reserved"): await manager.acquire("p")
        self.assertIs(manager._runtimes["p"], runtime); self.assertFalse(reservation.quiescence_proof().is_quiescent); await manager.shutdown_profile("p")
        self.assertTrue(reservation.quiescence_proof().is_quiescent); await reservation.release()

    async def test_reservation_wins_startup_ready_publication_and_reaps_child(self):
        factory = _FakeFactory(); manager = self.manager(factory); entered = asyncio.Event(); release = asyncio.Event()
        async def hook(runtime): entered.set(); await release.wait()
        manager._before_ready_publication = hook
        startup = asyncio.create_task(manager.acquire("p")); await entered.wait(); reservation = await manager.reserve("p"); release.set()
        with self.assertRaisesRegex(RuntimeErrorSafe, "profile_reserved"): await startup
        self.assertNotIn("p", manager._runtimes); self.assertIsNotNone(factory.processes[0].returncode); await reservation.release()

    async def test_two_reservations_and_wrong_release_are_safe(self):
        manager = self.manager(_FakeFactory()); first = await manager.reserve("p")
        results = await asyncio.gather(manager.reserve("p"), return_exceptions=True)
        self.assertIsInstance(results[0], RuntimeErrorSafe); self.assertEqual(results[0].category, "profile_reserved")
        forged = ProfileReservation("p", manager, object())
        with self.assertRaisesRegex(RuntimeErrorSafe, "reservation_token_invalid"): await manager.release(forged)
        with self.assertRaisesRegex(RuntimeErrorSafe, "profile_reserved"): await manager.acquire("p")
        await first.release()

    async def test_capability_drift_fails_before_factory(self):
        for capabilities in (
            StorageRuntimeCapabilities(sqlite_home_environment=False),
            StorageRuntimeCapabilities(sqlite_home_config=False),
            StorageRuntimeCapabilities(log_dir_config=False),
            StorageRuntimeCapabilities(history_persistence_none=False),
        ):
            factory = _FakeFactory(); manager = self.manager(factory, storage_capabilities=capabilities)
            with self.subTest(capabilities=capabilities), self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"): await manager.acquire("p")
            self.assertEqual(factory.calls, [])
        for version, schema in (("0.144.7", SCHEMA_SHA256), (SUPPORTED_CODEX_VERSION, "0" * 64)):
            factory = _FakeFactory(); manager = self.manager(factory, client_version=version, schema_sha256=schema)
            with self.subTest(version=version, schema=schema), self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"): await manager.acquire("p")
            self.assertEqual(factory.calls, [])

    async def test_child_routing_is_exact_and_parent_secrets_cannot_override(self):
        env = build_child_environment(self.profile, {"CODEX_HOME": "/bad", "CODEX_SQLITE_HOME": "/bad", "RUST_LOG": "debug", "OPENAI_API_KEY": "test-only-noncredential-sentinel", "PATH": "/bin"})
        self.assertEqual(env["CODEX_HOME"], self.home); self.assertEqual(env["CODEX_SQLITE_HOME"], os.path.join(self.state, "sqlite")); self.assertNotIn("RUST_LOG", env); self.assertNotIn("OPENAI_API_KEY", env)
        overrides = build_child_config_overrides(self.profile)
        self.assertIn("sqlite_home=\"" + os.path.join(self.state, "sqlite") + "\"", overrides)
        self.assertIn("log_dir=\"" + os.path.join(self.state, "logs") + "\"", overrides)
        self.assertIn('history.persistence="none"', overrides)
        self.assertEqual(build_child_argv("/codex", self.profile)[1:4], ["app-server", "--stdio", "-c"])

    async def test_unresolved_child_makes_quiescence_false(self):
        manager = self.manager(_FakeFactory()); reservation = await manager.reserve("p")
        manager._unresolved["p"] = object()
        proof = reservation.quiescence_proof()
        self.assertFalse(proof.is_quiescent); self.assertTrue(proof.unresolved_child)
        await reservation.release()

    async def test_shutdown_all_stops_owned_runtime_while_reservation_is_retained(self):
        factory = _FakeFactory(); manager = self.manager(factory); await manager.acquire("p"); reservation = await manager.reserve("p")
        await manager.shutdown_all()
        self.assertIsNotNone(factory.processes[0].returncode); self.assertTrue(reservation.quiescence_proof().is_quiescent)
        await reservation.release()


if __name__ == "__main__": unittest.main()
