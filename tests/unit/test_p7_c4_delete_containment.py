import asyncio
import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadOperationResult,
    ThreadOperationStatus,
)
from codex_control.adapters.codex.persistent_scanner import PersistentProfileResidualScanner
from codex_control.adapters.codex.runtime import CodexRuntimeManager
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
    RepositoryErrorCategory,
    SqliteStorage,
)


class _ConfirmedDelete:
    def __init__(self):
        self.calls = 0

    async def delete(self, *, binding):
        self.calls += 1
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class _AmbiguousDelete:
    def __init__(self):
        self.calls = 0

    async def delete(self, *, binding):
        self.calls += 1
        raise RuntimeError("synthetic ambiguous transport")


class P7C4DeleteContainmentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        base = self.tempdir.name
        self.home = os.path.join(base, "profile")
        self.parent = os.path.join(base, "roots")
        self.state_root = os.path.join(self.parent, "isolated")
        self.repository = os.path.join(base, "repository")
        self.controller = os.path.join(base, "controller.sqlite3")
        for path in (self.home, self.parent, self.repository):
            os.mkdir(path, 0o700)
        with open(self.controller, "wb"):
            pass
        os.chmod(self.controller, 0o600)
        self.profile = CodexProfile("profile", self.home, "Profile", self.state_root)
        self.authority = IsolationPathAuthority(
            (self.profile,), controller_db_path=self.controller,
            repository_root=self.repository,
        )
        IsolatedStateRoot(self.authority).provision(self.profile)
        self.manager = CodexRuntimeManager(
            [self.profile], client_version="test",
            isolation_authority=self.authority,
        )
        self.storage = await SqliteStorage.open(
            os.path.join(base, "control.sqlite3"), now_ms=lambda: 1
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def _seed(self, state, dialogue_id="d"):
        repo = DialogueRepository(self.storage, now_ms=lambda: 1)
        await repo.create_intent(dialogue_id=dialogue_id, server_id="s", profile_id="profile")
        dialogue = await repo.confirm_created(
            dialogue_id=dialogue_id, expected_version=0, thread_id="thread-c4"
        )
        deletion = DeletionRepository(self.storage, now_ms=lambda: 2)
        dialogue = await deletion.claim_delete_intent(
            dialogue_id=dialogue_id, expected_version=dialogue.version
        )
        dialogue = await deletion.claim_deleting(
            dialogue_id=dialogue_id, expected_version=dialogue.version
        )
        if state == DialogueState.DELETE_UNKNOWN:
            return await deletion.mark_delete_unknown(
                dialogue_id=dialogue_id, expected_version=dialogue.version,
                error_class="DELETE_UNKNOWN",
            )
        return await deletion.mark_delete_confirmed_pending_storage(
            dialogue_id=dialogue_id, expected_version=dialogue.version
        )

    def _scanner(self, **kwargs):
        return PersistentProfileResidualScanner(self.authority, **kwargs)

    async def test_schema_v4_and_unknown_record_are_content_free_and_idempotent(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        repository = DeleteStorageContainmentRepository(self.storage, now_ms=lambda: 10)
        first = await repository.mark_unknown_contained(
            dialogue_id="d", expected_dialogue_version=unknown.version
        )
        second = await repository.mark_unknown_contained(
            dialogue_id="d", expected_dialogue_version=unknown.version
        )
        self.assertEqual(first, second)
        self.assertEqual(10, first.contained_at_ms)
        self.assertNotIn("thread-c4", repr(first))
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETE_UNKNOWN, current.state)
        self.assertEqual(unknown.version, current.version)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("d"))

    async def test_scanner_scope_chunk_boundary_path_match_and_credential_non_read(self):
        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        os.mkdir(os.path.join(self.home, "sessions", "nested"), 0o700)
        with open(os.path.join(self.home, "sessions", "nested", "rollout"), "wb") as handle:
            handle.write(b"prefix-thread-c4-suffix")
        with open(os.path.join(self.home, "auth.json"), "wb") as handle:
            handle.write(b"credential-sentinel-thread-c4")
        result = self._scanner(chunk_bytes=3).scan(self.profile, "thread-c4")
        self.assertEqual(1, result.match_count)
        self.assertEqual(1, result.files_scanned)
        self.assertEqual(0, result.scan_errors)

    async def test_scanner_missing_scope_passes_and_unsafe_entries_fail_closed(self):
        self.assertTrue(self._scanner().scan(self.profile, "thread-c4").passed)
        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        os.symlink(self.repository, os.path.join(self.home, "sessions", "link"))
        result = self._scanner().scan(self.profile, "thread-c4")
        self.assertGreater(result.scan_errors, 0)
        self.assertFalse(result.passed)

    async def test_scanner_history_multiple_matches_and_finite_limits(self):
        with open(os.path.join(self.home, "history.jsonl"), "wb") as handle:
            handle.write(b"thread-c4|thread-c4|thread-c4")
        result = self._scanner(chunk_bytes=2).scan(self.profile, "thread-c4")
        self.assertEqual(3, result.match_count)
        self.assertEqual(1, result.files_scanned)
        self.assertEqual(0, result.scan_errors)

        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        for name in ("one", "two"):
            with open(os.path.join(self.home, "sessions", name), "wb") as handle:
                handle.write(b"unrelated")
        limited_files = self._scanner(max_files=1).scan(self.profile, "thread-c4")
        self.assertTrue(limited_files.limit_exceeded)
        self.assertGreater(limited_files.scan_errors, 0)
        limited_bytes = self._scanner(max_bytes=1).scan(self.profile, "thread-c4")
        self.assertTrue(limited_bytes.limit_exceeded)
        self.assertGreater(limited_bytes.scan_errors, 0)

    async def test_scanner_special_and_writable_entries_fail_closed(self):
        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        fifo = os.path.join(self.home, "sessions", "fifo")
        os.mkfifo(fifo, 0o600)
        try:
            result = self._scanner().scan(self.profile, "thread-c4")
            self.assertFalse(result.passed)
            self.assertGreater(result.scan_errors, 0)
        finally:
            os.unlink(fifo)
        path = os.path.join(self.home, "sessions", "writable")
        with open(path, "wb") as handle:
            handle.write(b"unrelated")
        os.chmod(path, 0o602)
        result = self._scanner().scan(self.profile, "thread-c4")
        self.assertFalse(result.passed)
        self.assertGreater(result.scan_errors, 0)

    async def test_confirmed_clean_path_finalizes_and_residual_path_stays_pending(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        result = await coordinator.cleanup_confirmed(
            dialogue_id="d", expected_dialogue_version=pending.version
        )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, result.status)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        self.assertIsNotNone(await DeletionRepository(self.storage).get_tombstone("d"))

    async def test_confirmed_persistent_residual_blocks_finalizer_and_holds_quarantine(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        with open(os.path.join(self.home, "sessions", "residual"), "wb") as handle:
            handle.write(b"thread-c4")
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        result = await coordinator.cleanup_confirmed(
            dialogue_id="d", expected_dialogue_version=pending.version
        )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, result.status)
        self.assertEqual("PERSISTENT_RESIDUAL_MATCHES", result.reason.value)
        self.assertIsNotNone(await DialogueRepository(self.storage).get_live())
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("d"))
        self.assertIn("profile", self.manager._reservations)

    async def test_unknown_containment_keeps_official_unknown_and_replay_has_no_duplicate_root(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        first = await coordinator.contain_unknown(
            dialogue_id="d", expected_dialogue_version=unknown.version
        )
        second = await coordinator.contain_unknown(
            dialogue_id="d", expected_dialogue_version=unknown.version
        )
        self.assertEqual(DeleteStorageCleanupStatus.UNKNOWN_CONTAINED, first.status)
        self.assertEqual(DeleteStorageCleanupStatus.UNKNOWN_CONTAINED, second.status)
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETE_UNKNOWN, current.state)
        self.assertEqual("DELETE_UNKNOWN", current.last_error_class)
        self.assertIn("profile", self.manager._reservations)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("d"))

    async def test_delete_and_recovery_optional_composition_has_no_external_replay(self):
        repository = DialogueRepository(self.storage, now_ms=lambda: 1)
        await repository.create_intent(dialogue_id="d", server_id="s", profile_id="profile")
        idle = await repository.confirm_created(
            dialogue_id="d", expected_version=0, thread_id="thread-c4"
        )
        lifecycle = _ConfirmedDelete()
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        service = DialogueDeleteService(
            self.storage, server_id="s", thread_lifecycle=lifecycle,
            local_cleanup=coordinator, now_ms=lambda: 20,
        )
        result = await service.delete(DialogueDeleteRequest("d", idle.version))
        self.assertEqual(DialogueDeleteStatus.DELETED, result.status)
        self.assertEqual(1, lifecycle.calls)

        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, "d2")
        recovery = await DialogueRecoveryService(
            self.storage, now_ms=lambda: 20,
            local_cleanup=DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20),
        ).recover_startup()
        self.assertEqual(DialogueRecoveryStatus.DELETE_FINALIZED_AFTER_STORAGE, recovery.status)
        self.assertEqual(pending.dialogue_id, "d2")

    async def test_ambiguous_delete_is_unknown_even_when_local_containment_succeeds(self):
        repository = DialogueRepository(self.storage, now_ms=lambda: 1)
        await repository.create_intent(dialogue_id="d", server_id="s", profile_id="profile")
        idle = await repository.confirm_created(
            dialogue_id="d", expected_version=0, thread_id="thread-c4"
        )
        lifecycle = _AmbiguousDelete()
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        result = await DialogueDeleteService(
            self.storage, server_id="s", thread_lifecycle=lifecycle,
            local_cleanup=coordinator, now_ms=lambda: 20,
        ).delete(DialogueDeleteRequest("d", idle.version))
        self.assertEqual(DialogueDeleteStatus.UNKNOWN, result.status)
        self.assertEqual(1, lifecycle.calls)
        current = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETE_UNKNOWN, current.state)
        self.assertIsNotNone(await DeleteStorageContainmentRepository(self.storage).get("d"))
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("d"))

    async def test_containment_state_conflicts_and_confirmed_finalizer_collision_fail_closed(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        repository = DeleteStorageContainmentRepository(self.storage, now_ms=lambda: 20)
        with self.assertRaises(Exception) as raised:
            await repository.mark_unknown_contained(
                dialogue_id="d", expected_dialogue_version=pending.version
            )
        self.assertEqual(RepositoryErrorCategory.STATE_CONFLICT, raised.exception.category)

        def forge(connection):
            connection.execute(
                "INSERT INTO delete_storage_containment "
                "(dialogue_id, profile_id, thread_identity_sha256, dialogue_version, "
                "official_delete_authority, local_isolated_storage_containment, contained_at_ms) "
                "VALUES (?, ?, ?, ?, 'UNKNOWN', 'COMPLETED', ?)",
                ("d", "profile", hashlib.sha256(b"thread-c4").hexdigest(), pending.version, 20),
            )
        await self.storage.write(forge)
        with self.assertRaises(Exception) as raised:
            await DeletionRepository(self.storage, now_ms=lambda: 30).finalize_confirmed(
                dialogue_id="d", expected_version=pending.version,
                tombstone_expires_at_ms=100,
            )
        self.assertEqual(RepositoryErrorCategory.INVARIANT_VIOLATION, raised.exception.category)
        self.assertIsNone(await DeletionRepository(self.storage).get_tombstone("d"))


if __name__ == "__main__":
    unittest.main()
