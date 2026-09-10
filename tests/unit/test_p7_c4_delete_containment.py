import asyncio
import hashlib
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadOperationResult,
    ThreadOperationStatus,
)
import codex_control.adapters.codex.persistent_scanner as scanner_module
from codex_control.adapters.codex.persistent_scanner import PersistentProfileResidualScanner
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.application import (
    DeleteStorageCleanupCoordinator,
    DeleteStorageCleanupStatus,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteStatus,
    DialogueRecoveryError,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DeleteStorageContainmentRepository,
    DeletionFinalizeResult,
    DeletionTombstoneRecord,
    DeletionRepository,
    DialogueRepository,
    DialogueState,
    RepositoryErrorCategory,
    SqliteStorage,
)
from codex_control.storage.errors import StorageErrorCategory


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


class _FailingScanner:
    def scan(self, profile, thread_id):
        return scanner_module.PersistentProfileScanResult(0, 0, 0, 1)


class P7C4DeleteContainmentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        base = self.tempdir.name
        self.home = os.path.join(base, "profile")
        self.parent = os.path.join(base, "roots")
        self.state_root = os.path.join(self.parent, "isolated")
        self.repository = os.path.join(base, "repository")
        self.controller = os.path.join(base, "controller.sqlite3")
        self.database = os.path.join(base, "control.sqlite3")
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
            self.database, now_ms=lambda: 1
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

    async def test_recovery_outcome_statuses_are_distinct_and_truthful(self):
        self.assertIsNot(
            DialogueRecoveryStatus.DELETE_FINALIZED_AFTER_STORAGE,
            DialogueRecoveryStatus.DELETE_CONFIRMED_STORAGE_PENDING,
        )
        self.assertIsNot(
            DialogueRecoveryStatus.DELETE_UNKNOWN_CONTAINED,
            DialogueRecoveryStatus.DELETE_UNKNOWN_CONTAINMENT_PENDING,
        )
        self.assertEqual("DELETE_FINALIZED_AFTER_STORAGE", DialogueRecoveryStatus.DELETE_FINALIZED_AFTER_STORAGE.value)
        self.assertEqual("DELETE_UNKNOWN_CONTAINED", DialogueRecoveryStatus.DELETE_UNKNOWN_CONTAINED.value)
        self.assertEqual("DELETE_UNKNOWN_CONTAINMENT_PENDING", DialogueRecoveryStatus.DELETE_UNKNOWN_CONTAINMENT_PENDING.value)

        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        finalized = await DialogueRecoveryService(
            self.storage, now_ms=lambda: 20,
            local_cleanup=DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20),
        ).recover_startup()
        self.assertEqual("DELETE_FINALIZED_AFTER_STORAGE", finalized.status.value)
        self.assertIsNone(finalized.dialogue)

        unknown = await self._seed(DialogueState.DELETE_UNKNOWN, "unknown-status")
        contained = await DialogueRecoveryService(
            self.storage, now_ms=lambda: 20,
            local_cleanup=DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20),
        ).recover_startup()
        self.assertEqual("DELETE_UNKNOWN_CONTAINED", contained.status.value)
        self.assertEqual(DialogueState.DELETE_UNKNOWN, contained.dialogue.state)

        def remove_containment(connection):
            connection.execute(
                "DELETE FROM delete_storage_containment WHERE dialogue_id = ?", (unknown.dialogue_id,)
            )
        await self.storage.write(remove_containment)
        failing = DeleteStorageCleanupCoordinator(
            self.storage, self.manager, scanner=_FailingScanner(), now_ms=lambda: 20
        )
        pending_unknown = await DialogueRecoveryService(
            self.storage, now_ms=lambda: 20, local_cleanup=failing
        ).recover_startup()
        self.assertEqual("DELETE_UNKNOWN_CONTAINMENT_PENDING", pending_unknown.status.value)
        self.assertEqual(DialogueState.DELETE_UNKNOWN, pending_unknown.dialogue.state)

    async def test_committed_finalizer_never_regresses_when_old_verification_seam_fails(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        original = DeletionRepository.finalize_confirmed

        async def commit_then_fail(repository, **kwargs):
            result = await original(repository, **kwargs)
            self.assertIs(type(result), DeletionFinalizeResult)
            raise RuntimeError("old post-finalizer verification seam")

        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        with patch.object(DeletionRepository, "finalize_confirmed", new=commit_then_fail):
            result = await coordinator.cleanup_confirmed(
                dialogue_id="d", expected_dialogue_version=pending.version
            )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, result.status)
        self.assertIsNone(result.dialogue)
        self.assertIsNotNone(result.tombstone)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())
        self.assertIsNotNone(await DeletionRepository(self.storage).get_tombstone("d"))

    async def test_post_commit_reservation_release_failure_is_truthful_and_not_retried(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        calls = []

        async def fail_release(reservation):
            calls.append(1)
            raise RuntimeError("release failure")

        with patch.object(self.manager, "release", new=fail_release):
            result = await coordinator.cleanup_confirmed(
                dialogue_id="d", expected_dialogue_version=pending.version
            )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, result.status)
        self.assertEqual("RESERVATION_RELEASE_FAILED", result.reason.value)
        self.assertEqual(1, len(calls))
        self.assertIn("profile", coordinator._reservations)
        self.assertIsNone(await DialogueRepository(self.storage).get_live())

    async def test_stale_and_mismatched_replay_tombstones_fail_closed(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        first = await coordinator.cleanup_confirmed(
            dialogue_id="d", expected_dialogue_version=pending.version
        )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_FINALIZED, first.status)
        stale = await coordinator.cleanup_confirmed(
            dialogue_id="d", expected_dialogue_version=pending.version + 1
        )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, stale.status)

        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE, "d2")
        original = DeletionRepository.finalize_confirmed

        async def commit_corrupt_then_fail(repository, **kwargs):
            result = await original(repository, **kwargs)
            def corrupt_tombstone(connection):
                connection.execute(
                    "UPDATE deletion_tombstones SET thread_identity_sha256 = ? WHERE dialogue_id = ?",
                    (hashlib.sha256(b"other-thread").hexdigest(), "d2"),
                )
            await self.storage.write(corrupt_tombstone)
            raise RuntimeError("concurrent mismatched tombstone")

        with patch.object(DeletionRepository, "finalize_confirmed", new=commit_corrupt_then_fail):
            replay = await DeleteStorageCleanupCoordinator(
                self.storage, self.manager, now_ms=lambda: 20
            ).cleanup_confirmed(
                dialogue_id="d2", expected_dialogue_version=pending.version
            )
        self.assertEqual(DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE, replay.status)

    async def test_regular_file_substitution_after_stat_is_rejected_before_read(self):
        os.mkdir(os.path.join(self.home, "sessions"), 0o700)
        victim = os.path.join(self.home, "sessions", "victim")
        replacement = os.path.join(self.home, "replacement")
        with open(victim, "wb") as handle:
            handle.write(b"safe")
        with open(replacement, "wb") as handle:
            handle.write(b"thread-c4")
        reads = []
        original_open = os.open
        original_read = os.read
        replaced = False

        def substitute_open(name, flags, *args, **kwargs):
            nonlocal replaced
            if name == "victim" and not replaced:
                replaced = True
                os.replace(replacement, victim)
            return original_open(name, flags, *args, **kwargs)

        def observe_read(fd, size):
            reads.append(fd)
            return original_read(fd, size)

        with patch.object(scanner_module.os, "open", side_effect=substitute_open), \
                patch.object(scanner_module.os, "read", side_effect=observe_read):
            result = self._scanner().scan(self.profile, "thread-c4")
        self.assertGreater(result.scan_errors, 0)
        self.assertEqual(0, result.match_count)
        self.assertEqual([], reads)

    async def test_v4_containment_tombstone_collision_is_rejected_at_open(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        await DeleteStorageContainmentRepository(self.storage, now_ms=lambda: 20).mark_unknown_contained(
            dialogue_id=unknown.dialogue_id, expected_dialogue_version=unknown.version
        )
        await self.storage.close()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "INSERT INTO deletion_tombstones "
                "(dialogue_id, thread_identity_sha256, stale_generation, deleted_at_ms, expires_at_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                ("d", hashlib.sha256(b"thread-c4").hexdigest(), unknown.version, 20, 21),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(Exception) as raised:
            await SqliteStorage.open(self.database, now_ms=lambda: 1)
        self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)

    async def test_v4_containment_active_job_collision_is_rejected_at_open(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        await DeleteStorageContainmentRepository(self.storage, now_ms=lambda: 20).mark_unknown_contained(
            dialogue_id=unknown.dialogue_id, expected_dialogue_version=unknown.version
        )
        await self.storage.close()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "INSERT INTO turn_jobs "
                "(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
                "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
                "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'RECEIVED', 0, 1, 1, NULL)",
                ("job", 99, 1, 1, "d", "s", "profile", "thread-c4", "model", "low", "0" * 64),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(Exception) as raised:
            await SqliteStorage.open(self.database, now_ms=lambda: 1)
        self.assertEqual(StorageErrorCategory.SCHEMA_INVALID, raised.exception.category)

    async def test_application_recovery_rejects_forged_containment_active_job(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        await DeleteStorageContainmentRepository(self.storage, now_ms=lambda: 20).mark_unknown_contained(
            dialogue_id=unknown.dialogue_id, expected_dialogue_version=unknown.version
        )

        def insert_active_job(connection):
            connection.execute(
                "INSERT INTO turn_jobs "
                "(job_id, telegram_update_id, source_chat_id, source_message_id, dialogue_id, "
                "server_id, profile_id, thread_id, model_id, reasoning_effort, input_sha256, "
                "codex_turn_id, state, version, created_at_ms, updated_at_ms, error_class) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'RECEIVED', 0, 1, 1, NULL)",
                ("job", 99, 1, 1, "d", "s", "profile", "thread-c4", "model", "low", "0" * 64),
            )
        await self.storage.write(insert_active_job)
        with self.assertRaises(DialogueRecoveryError) as raised:
            await DialogueRecoveryService(self.storage, now_ms=lambda: 20).recover_startup()
        self.assertEqual("INVARIANT", raised.exception.category.value)

    async def test_two_concurrent_confirmed_calls_have_one_local_commit_and_release(self):
        pending = await self._seed(DialogueState.DELETE_CONFIRMED_PENDING_STORAGE)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        entered = asyncio.Event()
        release = asyncio.Event()
        root_calls = []
        finalize_calls = []
        release_calls = []
        original_recreate = self.manager.recreate_isolated_state_root
        original_finalize = DeletionRepository.finalize_confirmed
        original_release = self.manager.release

        async def recreate(reservation):
            root_calls.append(1)
            entered.set()
            await release.wait()
            await original_recreate(reservation)

        async def finalize(repository, **kwargs):
            finalize_calls.append(1)
            return await original_finalize(repository, **kwargs)

        async def release_reservation(reservation):
            release_calls.append(1)
            return await original_release(reservation)

        with patch.object(self.manager, "recreate_isolated_state_root", new=recreate), \
                patch.object(self.manager, "release", new=release_reservation), \
                patch.object(DeletionRepository, "finalize_confirmed", new=finalize):
            first = asyncio.create_task(coordinator.cleanup_confirmed(
                dialogue_id="d", expected_dialogue_version=pending.version
            ))
            second = asyncio.create_task(coordinator.cleanup_confirmed(
                dialogue_id="d", expected_dialogue_version=pending.version
            ))
            await entered.wait()
            release.set()
            results = await asyncio.gather(first, second)
        self.assertEqual([1], root_calls)
        self.assertEqual([1], finalize_calls)
        self.assertEqual([1], release_calls)
        self.assertTrue(all(result.status is DeleteStorageCleanupStatus.CONFIRMED_FINALIZED for result in results))

    async def test_two_concurrent_unknown_calls_have_one_containment_and_keep_quarantine(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        entered = asyncio.Event()
        release = asyncio.Event()
        root_calls = []
        insert_calls = []
        original_recreate = self.manager.recreate_isolated_state_root
        original_insert = DeleteStorageContainmentRepository.mark_unknown_contained

        async def recreate(reservation):
            root_calls.append(1)
            entered.set()
            await release.wait()
            await original_recreate(reservation)

        async def insert(repository, **kwargs):
            insert_calls.append(1)
            return await original_insert(repository, **kwargs)

        with patch.object(self.manager, "recreate_isolated_state_root", new=recreate), \
                patch.object(DeleteStorageContainmentRepository, "mark_unknown_contained", new=insert):
            first = asyncio.create_task(coordinator.contain_unknown(
                dialogue_id="d", expected_dialogue_version=unknown.version
            ))
            second = asyncio.create_task(coordinator.contain_unknown(
                dialogue_id="d", expected_dialogue_version=unknown.version
            ))
            await entered.wait()
            release.set()
            results = await asyncio.gather(first, second)
        self.assertEqual([1], root_calls)
        self.assertEqual([1], insert_calls)
        self.assertTrue(all(result.status is DeleteStorageCleanupStatus.UNKNOWN_CONTAINED for result in results))
        self.assertIn("profile", coordinator._reservations)

    async def test_caller_cancellation_after_ownership_keeps_unknown_quarantine(self):
        unknown = await self._seed(DialogueState.DELETE_UNKNOWN)
        coordinator = DeleteStorageCleanupCoordinator(self.storage, self.manager, now_ms=lambda: 20)
        entered = asyncio.Event()
        release = asyncio.Event()
        original_recreate = self.manager.recreate_isolated_state_root

        async def recreate(reservation):
            entered.set()
            await release.wait()
            await original_recreate(reservation)

        with patch.object(self.manager, "recreate_isolated_state_root", new=recreate):
            caller = asyncio.create_task(coordinator.contain_unknown(
                dialogue_id="d", expected_dialogue_version=unknown.version
            ))
            await entered.wait()
            caller.cancel()
            await asyncio.sleep(0)
            release.set()
            result = await caller
        self.assertEqual(DeleteStorageCleanupStatus.UNKNOWN_CONTAINED, result.status)
        self.assertIn("profile", coordinator._reservations)

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
