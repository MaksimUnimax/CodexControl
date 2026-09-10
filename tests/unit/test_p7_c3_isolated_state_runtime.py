import asyncio
import inspect
import json
import os
import stat
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch

from codex_control.adapters.codex.capabilities import SCHEMA_SHA256, SUPPORTED_CODEX_VERSION, StorageRuntimeCapabilities, load_manifest
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


async def fake_installed_authority():
    return load_manifest()


def fake_authority(version=SUPPORTED_CODEX_VERSION, schema=SCHEMA_SHA256):
    async def probe():
        return replace(load_manifest(), codex_cli_version=version, schema_sha256=schema)
    return probe


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

    def test_configured_protected_paths_reject_existing_symlink_components(self):
        with tempfile.TemporaryDirectory() as directory:
            home = os.path.join(directory, "home"); state = os.path.join(directory, "state")
            real = os.path.join(directory, "real"); alias = os.path.join(directory, "alias")
            os.mkdir(home); os.mkdir(state); os.mkdir(real); os.symlink(real, alias)
            cases = (
                {"repository_root": alias},
                {"controller_db_root": alias},
                {"controller_db_path": os.path.join(alias, "controller.sqlite")},
                {"protected_roots": [alias]},
            )
            for extra in cases:
                with self.subTest(extra=extra), self.assertRaises(ConfigurationError):
                    parse_server_configuration(_configuration([("p", home, "P", state)], **extra))

    def test_profile_repr_never_contains_either_sensitive_absolute_path(self):
        profile = CodexProfile("p", "/private/home", "P", "/private/state")
        self.assertNotIn("/private/home", repr(profile))
        self.assertNotIn("/private/state", repr(profile))


class StateRootAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.parent = self.temp.name
        self.home = os.path.join(self.parent, "home"); self.root = os.path.join(self.parent, "state")
        self.sibling = os.path.join(self.parent, "sibling"); self.repository = os.path.join(self.parent, "repo"); self.controller = os.path.join(self.parent, "controller.sqlite")
        os.mkdir(self.home, 0o700); os.mkdir(self.sibling, 0o700); os.mkdir(self.repository, 0o700); open(self.controller, "wb").close()
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

    def test_persistent_home_readable_modes_are_allowed_but_writable_modes_are_not(self):
        os.chmod(self.home, 0o755)
        self.authority.validate_profile_paths(self.profile)
        for mode in (0o775, 0o777):
            os.chmod(self.home, mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(IsolationError):
                self.authority.validate_profile_paths(self.profile)
        os.chmod(self.home, 0o700)

    def test_nested_codex_files_allow_read_bits_but_not_write_bits(self):
        sqlite_file = os.path.join(self.root, "sqlite", "state.sqlite")
        for mode in (0o600, 0o644):
            with open(sqlite_file, "wb") as handle: handle.write(b"synthetic")
            os.chmod(sqlite_file, mode)
            with self.subTest(mode=oct(mode)): self.roots.validate(self.profile)
            os.unlink(sqlite_file)
        for mode in (0o664, 0o666):
            with open(sqlite_file, "wb") as handle: handle.write(b"synthetic")
            os.chmod(sqlite_file, mode)
            with self.subTest(mode=oct(mode)), self.assertRaises(IsolationError): self.roots.validate(self.profile)
            os.unlink(sqlite_file)

    def test_nested_directories_may_be_readable_but_not_group_writable(self):
        nested = os.path.join(self.root, "logs", "nested")
        os.mkdir(nested, 0o755)
        self.roots.validate(self.profile)
        os.chmod(nested, 0o775)
        with self.assertRaises(IsolationError): self.roots.validate(self.profile)

    def test_top_level_modes_remain_exact(self):
        for path in (self.root,):
            os.chmod(path, 0o755)
            with self.subTest(path=path), self.assertRaises(IsolationError): self.roots.validate(self.profile)
            os.chmod(path, 0o700)
        sqlite = os.path.join(self.root, "sqlite")
        logs = os.path.join(self.root, "logs")
        marker = os.path.join(self.root, STATE_ROOT_MARKER)
        for path, mode, expected in ((sqlite, 0o755, "state_directory_invalid"), (logs, 0o755, "state_directory_invalid"), (marker, 0o640, "marker_invalid")):
            os.chmod(path, mode)
            with self.subTest(path=path), self.assertRaises(IsolationError): self.roots.validate(self.profile)
            os.chmod(path, 0o700 if path != marker else 0o600)

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

    def _assert_runtime_authority_rejected_without_mutation(self, authority):
        marker = os.path.join(self.root, STATE_ROOT_MARKER)
        with open(marker, "rb") as handle:
            before = handle.read()
        factory = _FakeFactory()

        async def attempt():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                isolation_authority=authority, installed_authority_probe=fake_installed_authority,
                process_factory=factory,
            )
            with self.assertRaises(RuntimeErrorSafe):
                await manager.acquire("profile")

        asyncio.run(attempt())
        self.assertEqual(factory.calls, [])
        with open(marker, "rb") as handle:
            self.assertEqual(handle.read(), before)

    def test_runtime_requires_repository_and_controller_authority(self):
        incomplete = IsolationPathAuthority((self.profile,), require_global_roots=False)
        with self.assertRaises(IsolationError):
            CodexRuntimeManager([self.profile], client_version=SUPPORTED_CODEX_VERSION, isolation_authority=incomplete)

    def test_runtime_accepts_controller_root_as_storage_authority(self):
        controller_root = os.path.join(self.parent, "controller-root")
        os.mkdir(controller_root, 0o700)
        authority = IsolationPathAuthority((self.profile,), controller_db_root=controller_root, repository_root=self.repository)
        factory = _FakeFactory()

        async def attempt():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                isolation_authority=authority, installed_authority_probe=fake_installed_authority,
                process_factory=factory,
            )
            await manager.acquire("profile")
            await manager.shutdown_all()

        asyncio.run(attempt())
        self.assertEqual(len(factory.calls), 1)

    def test_protected_path_descriptor_and_physical_alias_gates(self):
        repository_alias = os.path.join(self.parent, "repository-alias")
        os.symlink(self.root, repository_alias)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=repository_alias)
        )

        ancestor_target = os.path.join(self.parent, "ancestor-target")
        ancestor_alias = os.path.join(self.parent, "ancestor-alias")
        os.mkdir(ancestor_target, 0o700); os.symlink(ancestor_target, ancestor_alias)
        repository = os.path.join(ancestor_target, "repository")
        os.mkdir(repository, 0o700)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=os.path.join(ancestor_alias, "repository"))
        )

        protected_alias = os.path.join(self.parent, "protected-alias")
        os.symlink(self.root, protected_alias)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository, protected_roots=(protected_alias,))
        )

        controller_root_alias = os.path.join(self.parent, "controller-root-alias")
        os.symlink(self.root, controller_root_alias)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=self.controller, controller_db_root=controller_root_alias, repository_root=self.repository)
        )

        controller_target = os.path.join(self.parent, "controller-target")
        controller_alias = os.path.join(self.parent, "controller-alias")
        os.mkdir(controller_target, 0o700)
        with open(os.path.join(controller_target, "db.sqlite"), "wb"):
            pass
        os.symlink(controller_target, controller_alias)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=os.path.join(controller_alias, "db.sqlite"), repository_root=self.repository)
        )

        controller_final_alias = os.path.join(self.parent, "controller-final-alias.sqlite")
        os.symlink(self.controller, controller_final_alias)
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=controller_final_alias, repository_root=self.repository)
        )

    def test_protected_path_missing_foreign_owner_and_writable_modes_fail_before_spawn(self):
        missing = os.path.join(self.parent, "missing-protected")
        self._assert_runtime_authority_rejected_without_mutation(
            IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository, protected_roots=(missing,))
        )
        protected = os.path.join(self.parent, "protected")
        os.mkdir(protected, 0o700)
        try:
            os.chown(protected, 65534, 65534)
            self._assert_runtime_authority_rejected_without_mutation(
                IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository, protected_roots=(protected,))
            )
            os.chown(protected, 0, 0)
            for mode in (0o770, 0o707):
                os.chmod(protected, mode)
                with self.subTest(mode=oct(mode)):
                    self._assert_runtime_authority_rejected_without_mutation(
                        IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository, protected_roots=(protected,))
                    )
        finally:
            os.chown(protected, 0, 0); os.chmod(protected, 0o700)

    def test_recreate_ancestor_substitution_is_rejected_without_foreign_mutation(self):
        anchor = os.path.join(self.parent, "anchor")
        foreign = os.path.join(self.parent, "foreign")
        # Build the configured tree as <anchor>/state while retaining the
        # already-provisioned root's exact layout and inode.
        os.mkdir(anchor, 0o700)
        os.rename(self.root, os.path.join(anchor, "state"))
        self.profile = CodexProfile("profile", self.home, "Profile", os.path.join(anchor, "state"))
        self.authority = IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=os.path.join(self.parent, "repo"))
        self.roots = IsolatedStateRoot(self.authority)
        os.mkdir(foreign, 0o700)
        foreign_root = os.path.join(foreign, "state")
        foreign_profile = CodexProfile("profile", self.home, "Profile", foreign_root)
        foreign_authority = IsolationPathAuthority((foreign_profile,), controller_db_path=self.controller, repository_root=os.path.join(self.parent, "repo"), require_global_roots=True)
        IsolatedStateRoot(foreign_authority).provision(foreign_profile)
        sentinel = os.path.join(foreign_root, "sqlite", "sentinel")
        with open(sentinel, "wb") as handle: handle.write(b"keep")
        original_open = os.open
        substituted = False

        def substitute(component, flags, mode=0o777, *, dir_fd=None):
            nonlocal substituted
            if component == "anchor" and dir_fd is not None and not substituted:
                substituted = True
                saved = anchor + ".saved"
                os.rename(anchor, saved)
                os.symlink(foreign, anchor)
                self._ancestor_saved = saved
            return original_open(component, flags, mode, dir_fd=dir_fd)

        with patch("codex_control.adapters.codex.isolation.os.open", side_effect=substitute):
            manager = CodexRuntimeManager([self.profile], client_version="0.1.0-test", isolation_authority=self.authority, installed_authority_probe=fake_installed_authority)
            async def attempt():
                reservation = await manager.reserve("profile")
                with self.assertRaises(IsolationError): await manager.recreate_isolated_state_root(reservation)
                await reservation.release()
            asyncio.run(attempt())
        os.unlink(anchor)
        os.rename(self._ancestor_saved, anchor)
        self.assertTrue(substituted)
        with open(sentinel, "rb") as handle: self.assertEqual(handle.read(), b"keep")
        self.roots.validate(self.profile)

    def test_recreate_root_leaf_substitution_is_rejected_without_foreign_mutation(self):
        foreign = os.path.join(self.parent, "foreign-leaf")
        os.mkdir(foreign, 0o700)
        foreign_root = os.path.join(foreign, "state")
        foreign_profile = CodexProfile("profile", self.home, "Profile", foreign_root)
        foreign_authority = IsolationPathAuthority((foreign_profile,), controller_db_path=self.controller, repository_root=os.path.join(self.parent, "repo"))
        IsolatedStateRoot(foreign_authority).provision(foreign_profile)
        sentinel = os.path.join(foreign_root, "sqlite", "sentinel")
        with open(sentinel, "wb") as handle: handle.write(b"keep")
        original_open = os.open
        substituted = False

        def substitute(component, flags, mode=0o777, *, dir_fd=None):
            nonlocal substituted
            if component == "state" and dir_fd is not None and not substituted:
                substituted = True
                saved = self.root + ".saved"
                os.rename(self.root, saved)
                os.symlink(foreign_root, self.root)
                self._leaf_saved = saved
            return original_open(component, flags, mode, dir_fd=dir_fd)

        with patch("codex_control.adapters.codex.isolation.os.open", side_effect=substitute):
            manager = CodexRuntimeManager([self.profile], client_version="0.1.0-test", isolation_authority=self.authority, installed_authority_probe=fake_installed_authority)
            async def attempt():
                reservation = await manager.reserve("profile")
                with self.assertRaises(IsolationError): await manager.recreate_isolated_state_root(reservation)
                await reservation.release()
            asyncio.run(attempt())
        os.unlink(self.root)
        os.rename(self._leaf_saved, self.root)
        self.assertTrue(substituted)
        with open(sentinel, "rb") as handle: self.assertEqual(handle.read(), b"keep")
        self.roots.validate(self.profile)

    def test_provision_ancestor_substitution_is_rejected_without_foreign_creation(self):
        anchor = os.path.join(self.parent, "provision-anchor")
        foreign = os.path.join(self.parent, "provision-foreign")
        os.mkdir(anchor, 0o700); os.mkdir(foreign, 0o700)
        root = os.path.join(anchor, "state")
        profile = CodexProfile("provision", self.home, "Provision", root)
        authority = IsolationPathAuthority((profile,), controller_db_path=self.controller, repository_root=os.path.join(self.parent, "repo"))
        roots = IsolatedStateRoot(authority)
        original_open = os.open
        substituted = False

        def substitute(component, flags, mode=0o777, *, dir_fd=None):
            nonlocal substituted
            if component == "provision-anchor" and dir_fd is not None and not substituted:
                nonlocal_anchor = anchor + ".saved"
                substituted = True
                os.rename(anchor, nonlocal_anchor)
                os.symlink(foreign, anchor)
                self._provision_anchor_saved = nonlocal_anchor
            return original_open(component, flags, mode, dir_fd=dir_fd)

        with patch("codex_control.adapters.codex.isolation.os.open", side_effect=substitute):
            with self.assertRaises(IsolationError): roots.provision(profile)
        os.unlink(anchor)
        os.rename(self._provision_anchor_saved, anchor)
        self.assertTrue(substituted)
        self.assertFalse(os.path.exists(os.path.join(foreign, "state")))
        self.assertFalse(os.path.exists(root))

    def test_recreate_post_anchor_ancestor_substitution_is_rejected_after_mutation(self):
        anchor = os.path.join(self.parent, "post-recreate-anchor")
        foreign = os.path.join(self.parent, "post-recreate-foreign")
        os.mkdir(anchor, 0o700); os.mkdir(foreign, 0o700)
        os.rename(self.root, os.path.join(anchor, "state"))
        self.profile = CodexProfile("profile", self.home, "Profile", os.path.join(anchor, "state"))
        self.authority = IsolationPathAuthority((self.profile,), controller_db_path=self.controller, repository_root=self.repository)
        self.roots = IsolatedStateRoot(self.authority)
        foreign_root = os.path.join(foreign, "state")
        foreign_profile = CodexProfile("profile", self.home, "Profile", foreign_root)
        IsolatedStateRoot(IsolationPathAuthority((foreign_profile,), controller_db_path=self.controller, repository_root=self.repository)).provision(foreign_profile)
        sentinel = os.path.join(foreign_root, "sqlite", "sentinel")
        with open(sentinel, "wb") as handle: handle.write(b"keep")
        original = IsolatedStateRoot._prove_final_binding
        saved = anchor + ".saved"

        def substitute(instance, parent, parent_fd, leaf, root_fd, initial):
            os.rename(anchor, saved)
            os.symlink(foreign, anchor)
            return original(instance, parent, parent_fd, leaf, root_fd, initial)

        try:
            with patch.object(IsolatedStateRoot, "_prove_final_binding", new=substitute):
                async def attempt():
                    manager = CodexRuntimeManager(
                        [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                        isolation_authority=self.authority, installed_authority_probe=fake_installed_authority,
                    )
                    reservation = await manager.reserve("profile")
                    with self.assertRaises(IsolationError):
                        await manager.recreate_isolated_state_root(reservation)
                    await reservation.release()
                asyncio.run(attempt())
        finally:
            os.unlink(anchor); os.rename(saved, anchor)
        with open(sentinel, "rb") as handle: self.assertEqual(handle.read(), b"keep")
        self.roots.validate(self.profile)

    def test_provision_post_anchor_ancestor_substitution_is_rejected_before_success(self):
        anchor = os.path.join(self.parent, "post-provision-anchor")
        foreign = os.path.join(self.parent, "post-provision-foreign")
        os.mkdir(anchor, 0o700); os.mkdir(foreign, 0o700)
        root = os.path.join(anchor, "state")
        profile = CodexProfile("provision-post", self.home, "Provision", root)
        authority = IsolationPathAuthority((profile,), controller_db_path=self.controller, repository_root=self.repository)
        roots = IsolatedStateRoot(authority)
        foreign_sentinel = os.path.join(foreign, "sentinel")
        with open(foreign_sentinel, "wb") as handle: handle.write(b"keep")
        original = IsolatedStateRoot._prove_final_binding
        saved = anchor + ".saved"

        def substitute(instance, parent, parent_fd, leaf, root_fd, initial):
            os.rename(anchor, saved)
            os.symlink(foreign, anchor)
            return original(instance, parent, parent_fd, leaf, root_fd, initial)

        try:
            with patch.object(IsolatedStateRoot, "_prove_final_binding", new=substitute):
                with self.assertRaises(IsolationError): roots.provision(profile)
        finally:
            os.unlink(anchor); os.rename(saved, anchor)
        self.assertFalse(os.path.exists(os.path.join(foreign, "state")))
        self.assertEqual(os.listdir(foreign), ["sentinel"])
        self.assertTrue(os.path.isdir(root))

    def test_root_leaf_post_open_substitution_is_rejected_before_success(self):
        foreign = os.path.join(self.parent, "post-leaf-foreign")
        os.mkdir(foreign, 0o700)
        foreign_root = os.path.join(foreign, "state")
        foreign_profile = CodexProfile("profile", self.home, "Profile", foreign_root)
        IsolatedStateRoot(IsolationPathAuthority((foreign_profile,), controller_db_path=self.controller, repository_root=self.repository)).provision(foreign_profile)
        sentinel = os.path.join(foreign_root, "sqlite", "sentinel")
        with open(sentinel, "wb") as handle: handle.write(b"keep")
        original = IsolatedStateRoot._prove_final_binding
        saved = self.root + ".saved"

        def substitute(instance, parent, parent_fd, leaf, root_fd, initial):
            os.rename(self.root, saved)
            os.symlink(foreign_root, self.root)
            return original(instance, parent, parent_fd, leaf, root_fd, initial)

        try:
            with patch.object(IsolatedStateRoot, "_prove_final_binding", new=substitute):
                with self.assertRaises(IsolationError): self.roots._recreate_bound(self.profile)
        finally:
            os.unlink(self.root); os.rename(saved, self.root)
        with open(sentinel, "rb") as handle: self.assertEqual(handle.read(), b"keep")
        self.roots.validate(self.profile)

    def test_recreate_is_bounded_idempotent_and_preserves_parent_sibling_controller(self):
        with open(os.path.join(self.root, "sqlite", "codex.sqlite"), "wb") as handle: handle.write(b"synthetic")
        with open(os.path.join(self.root, "logs", "codex.log"), "wb") as handle: handle.write(b"synthetic")
        with open(os.path.join(self.sibling, "keep"), "wb") as handle: handle.write(b"keep")
        with open(os.path.join(self.parent, "keep"), "wb") as handle: handle.write(b"keep")
        async def recreate_twice():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                isolation_authority=self.authority,
                installed_authority_probe=fake_installed_authority,
            )
            reservation = await manager.reserve("profile")
            await manager.recreate_isolated_state_root(reservation)
            await manager.recreate_isolated_state_root(reservation)
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
                isolation_authority=self.authority,
                installed_authority_probe=fake_installed_authority,
            )
            reservation = await manager.reserve("profile")
            manager._runtimes["profile"] = object()
            with self.assertRaises(IsolationError):
                await manager.recreate_isolated_state_root(reservation)
            await reservation.release()

        asyncio.run(recreate_with_busy_runtime())

    def test_recreate_rejects_symlink_substitution_before_mutation(self):
        sqlite = os.path.join(self.root, "sqlite"); os.rename(sqlite, sqlite + ".saved"); os.symlink(self.home, sqlite)

        async def recreate_with_substitution():
            manager = CodexRuntimeManager(
                [self.profile], client_version=SUPPORTED_CODEX_VERSION,
                isolation_authority=self.authority,
                installed_authority_probe=fake_installed_authority,
            )
            reservation = await manager.reserve("profile")
            with self.assertRaises(IsolationError):
                await manager.recreate_isolated_state_root(reservation)
            await reservation.release()

        asyncio.run(recreate_with_substitution())

    def test_same_id_different_root_is_rejected_without_mutation(self):
        foreign_home = os.path.join(self.parent, "foreign-home")
        foreign_root = os.path.join(self.parent, "foreign-root")
        os.mkdir(foreign_home, 0o700)
        foreign_profile = CodexProfile("profile", foreign_home, "Profile", foreign_root)
        foreign_authority = IsolationPathAuthority((foreign_profile,), controller_db_path=os.path.join(self.parent, "foreign-controller.sqlite"), repository_root=os.path.join(self.parent, "foreign-repo"))
        open(os.path.join(self.parent, "foreign-controller.sqlite"), "wb").close()
        os.mkdir(os.path.join(self.parent, "foreign-repo"), 0o700)
        foreign_roots = IsolatedStateRoot(foreign_authority)
        foreign_roots.provision(foreign_profile)
        content = os.path.join(foreign_root, "sqlite", "keep")
        with open(content, "wb") as handle: handle.write(b"keep")
        async def attempt():
            manager = CodexRuntimeManager([self.profile], isolation_authority=self.authority, installed_authority_probe=fake_installed_authority, client_version="0.1.0-test")
            reservation = await manager.reserve("profile")
            with self.assertRaises(IsolationError): self.roots.recreate(foreign_profile, reservation=reservation)
            await reservation.release()
        asyncio.run(attempt())
        with open(content, "rb") as handle: self.assertEqual(handle.read(), b"keep")
        self.roots.validate(self.profile)

    def test_unconfigured_profile_provision_and_validate_are_rejected(self):
        foreign_home = os.path.join(self.parent, "unconfigured-home")
        foreign_root = os.path.join(self.parent, "unconfigured-root")
        os.mkdir(foreign_home, 0o700)
        foreign = CodexProfile("other", foreign_home, "Other", foreign_root)
        with self.assertRaises(IsolationError): self.roots.provision(foreign)
        with self.assertRaises(IsolationError): self.roots.validate(foreign)


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
        kwargs.setdefault("client_version", SUPPORTED_CODEX_VERSION)
        kwargs.setdefault("installed_authority_probe", fake_installed_authority)
        return CodexRuntimeManager([self.profile], executable=self.executable, process_factory=factory, isolation_authority=self.authority, initialize_timeout=.05, graceful_shutdown_timeout=.01, terminate_timeout=.01, kill_reap_timeout=.01, **kwargs)

    def sequenced_probe(self, *manifests):
        calls = []

        async def probe():
            index = len(calls)
            calls.append(index)
            return manifests[min(index, len(manifests) - 1)]

        return probe, calls

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
            factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=fake_authority(version, schema))
            with self.subTest(version=version, schema=schema), self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"): await manager.acquire("p")
            self.assertEqual(factory.calls, [])

    async def test_client_protocol_version_is_independent_of_installed_authority(self):
        factory = _FakeFactory(); manager = self.manager(factory, client_version="0.1.0-test", installed_authority_probe=fake_authority("0.144.6", SCHEMA_SHA256))
        runtime = await manager.acquire("p")
        initialize = json.loads(factory.processes[0].stdin.data[0])
        self.assertEqual(initialize["params"]["clientInfo"]["version"], "0.1.0-test")
        self.assertIsNotNone(manager._installed_manifest)
        self.assertEqual(manager._installed_manifest.codex_cli_version, "0.144.6")
        await manager.shutdown_all()

    async def test_same_ready_runtime_does_not_reprobe(self):
        probe, calls = self.sequenced_probe(load_manifest())
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=probe)
        first = await manager.acquire("p")
        self.assertEqual(len(calls), 1)
        second = await manager.acquire("p")
        self.assertIs(second, first)
        self.assertEqual(len(calls), 1)
        await manager.shutdown_all()

    async def test_new_generation_reprobes(self):
        probe, calls = self.sequenced_probe(load_manifest(), load_manifest())
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=probe)
        await manager.acquire("p")
        await manager.shutdown_profile("p")
        await manager.acquire("p")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(factory.calls), 2)
        await manager.shutdown_all()

    async def test_version_drift_after_success_blocks_second_generation(self):
        probe, calls = self.sequenced_probe(load_manifest(), replace(load_manifest(), codex_cli_version="0.144.7"))
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=probe)
        await manager.acquire("p")
        await manager.shutdown_profile("p")
        with self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"):
            await manager.acquire("p")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(factory.calls), 1)
        self.assertEqual(factory.processes[0].returncode is not None, True)

    async def test_schema_drift_after_success_blocks_second_generation(self):
        probe, calls = self.sequenced_probe(load_manifest(), replace(load_manifest(), schema_sha256="0" * 64))
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=probe)
        await manager.acquire("p")
        await manager.shutdown_profile("p")
        with self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"):
            await manager.acquire("p")
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(factory.calls), 1)

    async def test_storage_capability_authority_is_immutable_manager_source(self):
        capabilities = StorageRuntimeCapabilities()
        probe, calls = self.sequenced_probe(load_manifest(), load_manifest())
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=probe, storage_capabilities=capabilities)
        await manager.acquire("p")
        await manager.shutdown_profile("p")
        await manager.acquire("p")
        self.assertIs(manager._storage_capabilities, capabilities)
        self.assertEqual(len(calls), 2)
        await manager.shutdown_all()

    async def test_caller_schema_string_cannot_create_authority(self):
        self.assertNotIn("schema_sha256", inspect.signature(CodexRuntimeManager).parameters)

    async def test_unavailable_installed_authority_blocks_before_factory(self):
        async def unavailable(): raise RuntimeError("probe failed")
        factory = _FakeFactory(); manager = self.manager(factory, installed_authority_probe=unavailable)
        with self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"): await manager.acquire("p")
        self.assertEqual(factory.calls, [])

    async def test_storage_capability_matrix_blocks_before_factory(self):
        for capability in ("sqlite_home_environment", "sqlite_home_config", "log_dir_config", "history_persistence_none"):
            kwargs = {capability: False}
            factory = _FakeFactory(); manager = self.manager(factory, storage_capabilities=StorageRuntimeCapabilities(**kwargs))
            with self.subTest(capability=capability), self.assertRaisesRegex(RuntimeErrorSafe, "capability_mismatch"): await manager.acquire("p")
            self.assertEqual(factory.calls, [])

    async def test_foreign_and_stale_reservations_cannot_recreate(self):
        manager_a = self.manager(_FakeFactory()); manager_b = self.manager(_FakeFactory())
        reservation_a = await manager_a.reserve("p"); reservation_b = await manager_b.reserve("p")
        with self.assertRaises(IsolationError): await manager_a.recreate_isolated_state_root(reservation_b)
        await reservation_b.release();
        with self.assertRaises(IsolationError): await manager_a.recreate_isolated_state_root(reservation_b)
        await reservation_a.release()

    async def test_active_starting_and_unresolved_runtime_recreation_is_rejected(self):
        manager = self.manager(_FakeFactory()); reservation = await manager.reserve("p")
        manager._starting["p"] = asyncio.create_task(asyncio.sleep(1))
        with self.assertRaises(IsolationError): await manager.recreate_isolated_state_root(reservation)
        manager._starting["p"].cancel()
        try: await manager._starting["p"]
        except asyncio.CancelledError: pass
        manager._starting.pop("p")
        manager._unresolved["p"] = object()
        with self.assertRaises(IsolationError): await manager.recreate_isolated_state_root(reservation)
        manager._unresolved.pop("p")
        manager._runtimes["p"] = object()
        with self.assertRaises(IsolationError): await manager.recreate_isolated_state_root(reservation)
        manager._runtimes.pop("p")
        await reservation.release()

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
