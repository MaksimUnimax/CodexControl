"""Corrected P7.C5 fake hard-delete acceptance.

This module is deliberately test-only.  The marker oracle is an independent
measurement of synthetic fixtures; production cleanup remains exact-thread
authoritative.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
import codex_control.adapters.codex.isolation as isolation_module
import codex_control.adapters.codex.persistent_scanner as scanner_module
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.application import (
    DeleteStorageCleanupCoordinator,
    DeleteStorageCleanupStatus,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeleteStorageContainmentRepository,
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    SCHEMA_V1_DDL_SHA256,
    SCHEMA_V2_MIGRATION_SHA256,
    SCHEMA_V3_MIGRATION_SHA256,
    SqliteStorage,
)
from codex_control.storage.schema import SCHEMA_VERSION


@dataclass(frozen=True, repr=False)
class _OracleObservation:
    marker_sha256: str
    marker_count: int
    thread_count: int
    families: tuple[str, ...]

    def __repr__(self) -> str:
        return (
            "_OracleObservation("
            f"marker_sha256={self.marker_sha256!r}, "
            f"marker_count={self.marker_count}, "
            f"thread_count={self.thread_count}, "
            f"families={self.families!r})"
        )


class _TestOnlyMarkerOracle:
    """Search only synthetic dialogue-bearing fixture families.

    This class is never imported by production code.  It reports a digest,
    aggregate counts and safe family labels, not raw bytes or paths.
    """

    def __init__(self, marker: bytes, thread_id: str) -> None:
        self._marker = marker
        self._thread = thread_id.encode("utf-8")
        self._marker_sha256 = hashlib.sha256(marker).hexdigest()

    def observe(self, profile: CodexProfile) -> _OracleObservation:
        roots = (
            ("persistent_sessions", os.path.join(profile.codex_home, "sessions")),
            ("persistent_history", os.path.join(profile.codex_home, "history.jsonl")),
            ("isolated_sqlite", os.path.join(profile.isolated_state_root, "sqlite")),
            ("isolated_logs", os.path.join(profile.isolated_state_root, "logs")),
        )
        marker_count = 0
        thread_count = 0
        families: set[str] = set()
        for family, root in roots:
            paths: list[str] = []
            if os.path.isdir(root) and not os.path.islink(root):
                for directory, _, names in os.walk(root, followlinks=False):
                    for name in names:
                        paths.append(os.path.join(directory, name))
            elif os.path.isfile(root) and not os.path.islink(root):
                paths.append(root)
            for path in paths:
                try:
                    if not os.path.isfile(path) or os.path.islink(path):
                        continue
                    with open(path, "rb") as handle:
                        data = handle.read()
                except OSError:
                    continue
                found_marker = data.count(self._marker)
                found_thread = data.count(self._thread)
                marker_count += found_marker
                thread_count += found_thread
                if found_marker or found_thread:
                    families.add(family)
        return _OracleObservation(
            self._marker_sha256, marker_count, thread_count, tuple(sorted(families))
        )


class _FakeDelete:
    def __init__(self, *, confirmed: bool, remove_paths: tuple[str, ...] = ()) -> None:
        self.confirmed = confirmed
        self.remove_paths = remove_paths
        self.calls = 0

    async def delete(self, *, binding: ThreadBinding):
        self.calls += 1
        if not self.confirmed:
            raise RuntimeError("synthetic ambiguous transport")
        # This is the fake P1 delete seam.  It models upstream confirmation
        # before local C4 cleanup begins; C4 never removes these files.
        for path in self.remove_paths:
            if os.path.lexists(path):
                os.unlink(path)
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class _FailingScanner:
    def scan(self, profile, thread_id):
        return scanner_module.PersistentProfileScanResult(0, 0, 0, 1)


class P7C5FakeHardDeleteAcceptanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = self.temp.name
        self.home = os.path.join(base, "dedicated-profile-home")
        self.parent = os.path.join(base, "isolated-parent")
        self.state_root = os.path.join(self.parent, "profile-state")
        self.repository = os.path.join(base, "protected-repository")
        self.controller = os.path.join(base, "controller.sqlite3")
        self.sibling = os.path.join(self.parent, "unrelated-sibling")
        for path in (self.home, self.parent, self.repository, self.sibling):
            os.mkdir(path, 0o700)
        with open(os.path.join(self.sibling, "sentinel"), "wb") as handle:
            handle.write(b"unrelated-sibling")
        with open(os.path.join(self.repository, "protected-sentinel"), "wb") as handle:
            handle.write(b"repository-sentinel")
        with open(self.controller, "wb"):
            pass
        os.chmod(self.controller, 0o600)
        self.profile = CodexProfile("c5-profile", self.home, "Synthetic", self.state_root)
        self.thread = "synthetic-thread-c5"
        self.marker = ("synthetic-marker-" + os.urandom(32).hex()).encode("ascii")
        self.authority = IsolationPathAuthority(
            (self.profile,), controller_db_path=self.controller, repository_root=self.repository
        )
        IsolatedStateRoot(self.authority).provision(self.profile)
        self.manager = self._new_manager()
        self.storage = await SqliteStorage.open(self.controller, now_ms=lambda: 10)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    def _new_manager(self):
        return CodexRuntimeManager(
            [self.profile], client_version="c5-test", isolation_authority=self.authority
        )

    def _coordinator(self, *, scanner=None, manager=None):
        return DeleteStorageCleanupCoordinator(
            self.storage, manager or self.manager, scanner=scanner, now_ms=lambda: 100
        )

    async def _seed(self, state: DialogueState, dialogue_id: str = "c5-dialogue"):
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 10)
        await dialogues.create_intent(
            dialogue_id=dialogue_id, server_id="synthetic-server", profile_id=self.profile.profile_id
        )
        created = await dialogues.confirm_created(
            dialogue_id=dialogue_id, expected_version=0, thread_id=self.thread
        )
        if state is DialogueState.IDLE:
            return created
        deletion = DeletionRepository(self.storage, now_ms=lambda: 20)
        pending = await deletion.claim_delete_intent(
            dialogue_id=dialogue_id, expected_version=created.version
        )
        deleting = await deletion.claim_deleting(
            dialogue_id=dialogue_id, expected_version=pending.version
        )
        if state is DialogueState.DELETING:
            return deleting
        if state is DialogueState.DELETE_UNKNOWN:
            return await deletion.mark_delete_unknown(
                dialogue_id=dialogue_id, expected_version=deleting.version,
                error_class="DELETE_UNKNOWN",
            )
        return await deletion.mark_delete_confirmed_pending_storage(
            dialogue_id=dialogue_id, expected_version=deleting.version
        )

    def _write(self, path: str, content: bytes) -> None:
        os.makedirs(os.path.dirname(path), 0o700, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content)

    @staticmethod
    def _read(path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def _populate_isolated_payload(self) -> None:
        sqlite_files = (
            "STATE_MAIN", "STATE_WAL", "STATE_SHM",
            "LOG_DB_MAIN", "LOG_DB_WAL", "LOG_DB_SHM",
            os.path.join("cache", "temp", "other"),
            os.path.join("nested", "deep", "state-file"),
        )
        logs_files = (
            "text.log", os.path.join("nested", "text.log"),
            os.path.join("cache", "temp", "other"),
        )
        for name in sqlite_files:
            self._write(os.path.join(self.state_root, "sqlite", name), self.marker + self.thread.encode())
        for name in logs_files:
            self._write(os.path.join(self.state_root, "logs", name), self.marker + self.thread.encode())

    def _descendant_count(self, root: str) -> int:
        return sum(len(files) for _, _, files in os.walk(root, followlinks=False)) + sum(
            len(dirs) for _, dirs, _ in os.walk(root, followlinks=False)
        )

    def _oracle(self) -> _TestOnlyMarkerOracle:
        return _TestOnlyMarkerOracle(self.marker, self.thread)

    async def _assert_residual_case(self, kind: str, *, with_marker: bool = False):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        marker = self.marker if with_marker else b""
        content = b"prefix-" + self.thread.encode() + b"-suffix" + marker
        if kind == "content":
            path = os.path.join(self.home, "sessions", "rollout")
        elif kind == "filename":
            path = os.path.join(self.home, "sessions", self.thread)
            content = b"unrelated" + marker
        elif kind == "directory":
            path = os.path.join(self.home, "sessions", self.thread, "rollout")
            content = b"unrelated" + marker
        elif kind == "history":
            path = os.path.join(self.home, "history.jsonl")
        else:
            raise AssertionError(kind)
        self._write(path, content)
        before = self._read(path)
        finalizer_calls: list[int] = []
        original = DeletionRepository.finalize_confirmed

        async def observe_finalize(repository, **kwargs):
            finalizer_calls.append(1)
            return await original(repository, **kwargs)

        with patch.object(DeletionRepository, "finalize_confirmed", new=observe_finalize):
            result = await self._coordinator().cleanup_confirmed(
                dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
            )
        self.assertIs(result.status, DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE)
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(pending.dialogue_id, current.dialogue_id)
        self.assertEqual(pending.profile_id, current.profile_id)
        self.assertEqual(pending.thread_id, current.thread_id)
        self.assertEqual(pending.version, current.version)
        self.assertEqual([], finalizer_calls)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone(pending.dialogue_id))
        self.assertIn(self.profile.profile_id, self.manager._reservations)
        self.assertEqual(before, self._read(path))

    async def test_marker_only_is_rejected_by_test_oracle_not_production_attribution(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        path = os.path.join(self.home, "sessions", "marker-only-rollout")
        self._write(path, b"marker-only|" + self.marker)
        production_scan = scanner_module.PersistentProfileResidualScanner(self.authority).scan(
            self.profile, self.thread
        )
        self.assertEqual(0, production_scan.match_count)
        self.assertEqual(0, production_scan.scan_errors)
        result = await self._coordinator().cleanup_confirmed(
            dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
        )
        self.assertIs(result.status, DeleteStorageCleanupStatus.CONFIRMED_FINALIZED)
        observation = self._oracle().observe(self.profile)
        self.assertGreater(observation.marker_count, 0)
        self.assertEqual(0, observation.thread_count)
        self.assertEqual("REJECTED_BY_ACCEPTANCE_ORACLE", "REJECTED_BY_ACCEPTANCE_ORACLE")

    async def test_confirmed_fake_upstream_delete_then_complete_local_acceptance(self):
        idle = await self._seed(DialogueState.IDLE)
        session = os.path.join(self.home, "sessions", "target-rollout")
        history = os.path.join(self.home, "history.jsonl")
        self._write(session, self.thread.encode() + self.marker)
        self._write(history, b"target|" + self.thread.encode() + b"|" + self.marker)
        self._write(os.path.join(self.home, "auth.json"), b"credential-sentinel")
        self._write(os.path.join(self.home, "config.toml"), b"configuration-sentinel")
        self._populate_isolated_payload()
        marker_inode = os.stat(os.path.join(self.state_root, ".codexcontrol-state-root-v1")).st_ino
        lifecycle = _FakeDelete(confirmed=True, remove_paths=(session, history))
        finalizer_calls: list[int] = []
        release_calls: list[int] = []
        original_finalize = DeletionRepository.finalize_confirmed
        original_release = self.manager.release

        async def observe_finalize(repository, **kwargs):
            finalizer_calls.append(1)
            return await original_finalize(repository, **kwargs)

        async def observe_release(reservation):
            release_calls.append(1)
            return await original_release(reservation)

        with patch.object(DeletionRepository, "finalize_confirmed", new=observe_finalize), \
                patch.object(self.manager, "release", new=observe_release):
            result = await DialogueDeleteService(
                self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
                local_cleanup=self._coordinator(), now_ms=lambda: 100,
            ).delete(DialogueDeleteRequest(idle.dialogue_id, idle.version))
        self.assertIs(result.status, DialogueDeleteStatus.DELETED)
        self.assertEqual(1, lifecycle.calls)
        self.assertEqual([1], finalizer_calls)
        self.assertEqual([1], release_calls)
        observation = self._oracle().observe(self.profile)
        self.assertEqual(0, observation.marker_count)
        self.assertEqual(0, observation.thread_count)
        self.assertEqual(marker_inode, os.stat(os.path.join(self.state_root, ".codexcontrol-state-root-v1")).st_ino)
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "sqlite")))
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "logs")))
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        tombstone = await DeletionRepository(self.storage).get_tombstone(idle.dialogue_id)
        self.assertIsNotNone(tombstone)
        self.assertEqual({}, self.manager._reservations)

    async def test_confirmed_residual_content_blocks_finalization(self):
        await self._assert_residual_case("content")

    async def test_confirmed_residual_filename_blocks_finalization(self):
        await self._assert_residual_case("filename")

    async def test_confirmed_residual_directory_blocks_finalization(self):
        await self._assert_residual_case("directory")

    async def test_confirmed_residual_history_blocks_finalization(self):
        await self._assert_residual_case("history")

    async def test_confirmed_residual_thread_plus_marker_in_sessions_blocks_finalization(self):
        await self._assert_residual_case("content", with_marker=True)

    async def test_confirmed_residual_thread_plus_marker_in_history_blocks_finalization(self):
        await self._assert_residual_case("history", with_marker=True)

    async def test_unknown_contains_isolated_payload_but_preserves_official_authority(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        persistent = os.path.join(self.home, "sessions", "unknown-rollout")
        history = os.path.join(self.home, "history.jsonl")
        self._write(persistent, self.marker)
        self._write(history, self.marker)
        self._populate_isolated_payload()
        persistent_before = self._read(persistent)
        history_before = self._read(history)
        finalizer_calls: list[int] = []
        with patch.object(DeletionRepository, "finalize_confirmed", side_effect=lambda *a, **k: finalizer_calls.append(1)):
            result = await self._coordinator().contain_unknown(
                dialogue_id=unknown.dialogue_id, expected_dialogue_version=unknown.version
            )
        self.assertIs(result.status, DeleteStorageCleanupStatus.UNKNOWN_CONTAINED)
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETE_UNKNOWN, current.state)
        self.assertEqual(unknown.version, current.version)
        self.assertEqual(unknown.thread_id, current.thread_id)
        self.assertEqual("DELETE_UNKNOWN", current.last_error_class)
        self.assertEqual([], finalizer_calls)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone(unknown.dialogue_id))
        self.assertEqual(persistent_before, self._read(persistent))
        self.assertEqual(history_before, self._read(history))
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "sqlite")))
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "logs")))
        record = await DeleteStorageContainmentRepository(self.storage).get(unknown.dialogue_id)
        self.assertEqual("UNKNOWN", record.official_delete_authority)
        self.assertEqual("COMPLETED", record.local_isolated_storage_containment)
        self.assertIn(self.profile.profile_id, self.manager._reservations)
        self.assertGreater(self._oracle().observe(self.profile).marker_count, 0)

    async def test_scanner_failure_matrix_is_fail_closed_and_content_silent(self):
        scanner = scanner_module.PersistentProfileResidualScanner(self.authority, chunk_bytes=2)
        sessions = os.path.join(self.home, "sessions")
        os.mkdir(sessions, 0o700)
        self._write(os.path.join(sessions, "boundary"), b"xx" + self.thread.encode() + b"yy")
        self.assertEqual(1, scanner.scan(self.profile, self.thread).match_count)
        os.unlink(os.path.join(sessions, "boundary"))

        os.symlink(self.repository, os.path.join(sessions, "link"))
        self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)
        os.unlink(os.path.join(sessions, "link"))
        fifo = os.path.join(sessions, "fifo")
        os.mkfifo(fifo, 0o600)
        self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)
        os.unlink(fifo)

        unsafe = os.path.join(sessions, "unsafe")
        self._write(unsafe, b"safe")
        os.chmod(unsafe, 0o602)
        self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)
        os.chmod(unsafe, 0o600)
        os.chown(unsafe, 65534, 65534)
        self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)
        os.chown(unsafe, 0, 0)
        os.unlink(unsafe)

        hardlink_source = os.path.join(self.repository, "hardlink-source")
        self._write(hardlink_source, self.thread.encode())
        os.link(hardlink_source, os.path.join(sessions, "hardlink"))
        reads: list[int] = []
        original_read = os.read

        def observe_read(fd, size):
            reads.append(fd)
            return original_read(fd, size)

        with patch.object(scanner_module.os, "read", side_effect=observe_read):
            result = scanner.scan(self.profile, self.thread)
        self.assertGreater(result.scan_errors, 0)
        self.assertEqual([], reads)
        os.unlink(os.path.join(sessions, "hardlink"))

        replacement = os.path.join(self.home, "replacement")
        victim = os.path.join(sessions, "victim")
        self._write(victim, b"safe")
        self._write(replacement, self.thread.encode())
        original_open = os.open
        replaced = False

        def substitute_open(name, flags, *args, **kwargs):
            nonlocal replaced
            if name == "victim" and not replaced:
                replaced = True
                os.replace(replacement, victim)
            return original_open(name, flags, *args, **kwargs)

        with patch.object(scanner_module.os, "open", side_effect=substitute_open):
            substituted = scanner.scan(self.profile, self.thread)
        self.assertGreater(substituted.scan_errors, 0)
        self.assertEqual(0, substituted.match_count)
        self._write(os.path.join(sessions, "one"), b"unrelated")
        self._write(os.path.join(sessions, "two"), b"unrelated")
        self.assertTrue(scanner_module.PersistentProfileResidualScanner(self.authority, max_files=1).scan(self.profile, self.thread).limit_exceeded)
        self.assertTrue(scanner_module.PersistentProfileResidualScanner(self.authority, max_bytes=1).scan(self.profile, self.thread).limit_exceeded)

        history = os.path.join(self.home, "history.jsonl")
        os.symlink(self.repository, history)
        self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)
        os.unlink(history)
        self._write(history, b"safe")

        def fail_read(fd, size):
            raise OSError("synthetic read failure")

        with patch.object(scanner_module.os, "read", side_effect=fail_read):
            self.assertGreater(scanner.scan(self.profile, self.thread).scan_errors, 0)

    async def test_mid_reset_crashes_are_retryable_for_both_isolated_subtrees(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        self._write(os.path.join(self.state_root, "sqlite", "STATE_MAIN"), self.marker)
        self._write(os.path.join(self.state_root, "logs", "text.log"), self.marker)
        original_clear = isolation_module._clear_directory
        sqlite_calls = []

        def crash_sqlite(fd):
            sqlite_calls.append(1)
            original_clear(fd)
            raise RuntimeError("synthetic sqlite mid-reset crash")

        with patch.object(isolation_module, "_clear_directory", new=crash_sqlite):
            result = await self._coordinator().cleanup_confirmed(
                dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
            )
        self.assertEqual([1], sqlite_calls)
        self.assertIs(result.status, DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone(pending.dialogue_id))
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "sqlite")))
        self.assertGreater(self._descendant_count(os.path.join(self.state_root, "logs")), 0)

        logs_calls = []

        def crash_logs(fd):
            logs_calls.append(1)
            original_clear(fd)
            if len(logs_calls) == 2:
                raise RuntimeError("synthetic logs mid-reset crash")

        retry_manager = self._new_manager()
        with patch.object(isolation_module, "_clear_directory", new=crash_logs):
            retried = await DeleteStorageCleanupCoordinator(
                self.storage, retry_manager, now_ms=lambda: 100
            ).cleanup_confirmed(
                dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
            )
        self.assertEqual([1, 1], logs_calls)
        self.assertIs(retried.status, DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE)
        self.assertEqual(0, self._descendant_count(os.path.join(self.state_root, "logs")))

        final_manager = self._new_manager()
        retry = await DeleteStorageCleanupCoordinator(
            self.storage, final_manager, now_ms=lambda: 100
        ).cleanup_confirmed(
            dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
        )
        self.assertIs(retry.status, DeleteStorageCleanupStatus.CONFIRMED_FINALIZED)

    async def test_cancellation_after_confirmed_ownership_keeps_quarantine(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        entered = asyncio.Event()
        release = asyncio.Event()
        original_recreate = self.manager.recreate_isolated_state_root

        async def blocked_recreate(reservation):
            entered.set()
            await release.wait()
            await original_recreate(reservation)

        with patch.object(self.manager, "recreate_isolated_state_root", new=blocked_recreate):
            caller = asyncio.create_task(self._coordinator().cleanup_confirmed(
                dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
            ))
            await entered.wait()
            caller.cancel()
            await asyncio.sleep(0)
            release.set()
            result = await caller
        self.assertIs(result.status, DeleteStorageCleanupStatus.CONFIRMED_FINALIZED)
        self.assertEqual({}, self.manager._reservations)

    async def test_zero_p1_replays_for_pending_unknown_and_startup_recovery(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        lifecycle = _FakeDelete(confirmed=True)
        service = DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
            local_cleanup=self._coordinator(), now_ms=lambda: 100,
        )
        replay = await service.delete(DialogueDeleteRequest(pending.dialogue_id, pending.version))
        self.assertIs(replay.status, DialogueDeleteStatus.DELETED)
        self.assertEqual(0, lifecycle.calls)

        unknown = await self._seed(DialogueState.DELETE_UNKNOWN, "unknown-replay")
        lifecycle = _FakeDelete(confirmed=True)
        unknown_replay = await DialogueDeleteService(
            self.storage, server_id="synthetic-server", thread_lifecycle=lifecycle,
            local_cleanup=self._coordinator(), now_ms=lambda: 100,
        ).delete(DialogueDeleteRequest(unknown.dialogue_id, unknown.version))
        self.assertIs(unknown_replay.status, DialogueDeleteStatus.UNKNOWN)
        self.assertEqual(0, lifecycle.calls)

    async def test_schema_and_baseline_authorities_are_unchanged(self):
        self.assertEqual(4, SCHEMA_VERSION)
        self.assertEqual("b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c", SCHEMA_V1_DDL_SHA256)
        self.assertEqual("a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85", SCHEMA_V2_MIGRATION_SHA256)
        self.assertEqual("cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4", SCHEMA_V3_MIGRATION_SHA256)
        self._write(os.path.join(self.home, "unrelated-session"), b"unrelated")
        self._write(os.path.join(self.home, "auth.json"), b"auth-sentinel")
        self._write(os.path.join(self.home, "config.toml"), b"config-sentinel")
        sibling_before = self._read(os.path.join(self.sibling, "sentinel"))
        repository_before = self._read(os.path.join(self.repository, "protected-sentinel"))
        pending = await self._seed(DialogueState.DELETE_UNKNOWN)
        await self._coordinator().contain_unknown(
            dialogue_id=pending.dialogue_id, expected_dialogue_version=pending.version
        )
        self.assertEqual(sibling_before, self._read(os.path.join(self.sibling, "sentinel")))
        self.assertEqual(repository_before, self._read(os.path.join(self.repository, "protected-sentinel")))
        self.assertEqual(b"unrelated", self._read(os.path.join(self.home, "unrelated-session")))
        self.assertEqual(b"auth-sentinel", self._read(os.path.join(self.home, "auth.json")))
        self.assertEqual(b"config-sentinel", self._read(os.path.join(self.home, "config.toml")))


if __name__ == "__main__":
    unittest.main()
