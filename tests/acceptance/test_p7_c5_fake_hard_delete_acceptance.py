"""Minimal P7.C5 defect proof; all marker material is process-local only."""

import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex import IsolationPathAuthority, IsolatedStateRoot
from codex_control.adapters.codex.runtime import CodexRuntimeManager
from codex_control.application import DeleteStorageCleanupCoordinator, DeleteStorageCleanupStatus
from codex_control.domain import CodexProfile
from codex_control.storage import DeletionRepository, DialogueRepository, DialogueState, SqliteStorage


class P7C5ImplementationDefectProof(unittest.IsolatedAsyncioTestCase):
    """The frozen contract requires marker-only persistent residuals to block."""

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = self.temp.name
        self.home = os.path.join(base, "dedicated-profile-home")
        parent = os.path.join(base, "isolated-parent")
        self.state = os.path.join(parent, "profile-state")
        repository = os.path.join(base, "protected-repository")
        self.controller = os.path.join(base, "controller.sqlite3")
        for path in (self.home, parent, repository):
            os.mkdir(path, 0o700)
        with open(self.controller, "wb"):
            pass
        os.chmod(self.controller, 0o600)
        self.profile = CodexProfile("c5-defect-profile", self.home, "Synthetic", self.state)
        self.thread = "synthetic-thread-c5-defect"
        self.marker = os.urandom(32).hex().encode("ascii")
        self.marker_sha256 = hashlib.sha256(self.marker).hexdigest()
        self.authority = IsolationPathAuthority(
            (self.profile,), controller_db_path=self.controller, repository_root=repository
        )
        IsolatedStateRoot(self.authority).provision(self.profile)
        self.manager = CodexRuntimeManager(
            [self.profile], client_version="c5-defect-proof", isolation_authority=self.authority
        )
        self.storage = await SqliteStorage.open(self.controller, now_ms=lambda: 10)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def _seed_confirmed_pending(self):
        dialogues = DialogueRepository(self.storage, now_ms=lambda: 10)
        await dialogues.create_intent(
            dialogue_id="defect-proof", server_id="synthetic-server", profile_id=self.profile.profile_id
        )
        created = await dialogues.confirm_created(
            dialogue_id="defect-proof", expected_version=0, thread_id=self.thread
        )
        deletion = DeletionRepository(self.storage, now_ms=lambda: 20)
        pending = await deletion.claim_delete_intent(
            dialogue_id=created.dialogue_id, expected_version=created.version
        )
        deleting = await deletion.claim_deleting(
            dialogue_id=pending.dialogue_id, expected_version=pending.version
        )
        return await deletion.mark_delete_confirmed_pending_storage(
            dialogue_id=deleting.dialogue_id, expected_version=deleting.version
        )

    async def test_marker_only_sessions_or_history_residual_must_block_finalization(self):
        """Expected red test: accepted scanner/coordinator currently ignores marker-only data."""
        pending = await self._seed_confirmed_pending()
        path = os.path.join(self.home, "sessions", "rollout")
        os.makedirs(os.path.dirname(path), 0o700, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"marker-only-residual|" + self.marker)
        result = await DeleteStorageCleanupCoordinator(
            self.storage, self.manager, now_ms=lambda: 1000
        ).cleanup_confirmed(
            dialogue_id=pending.dialogue_id,
            expected_dialogue_version=pending.version,
        )
        # The contract requires this assertion. It currently fails because
        # production scans only the exact thread identity, not the marker.
        self.assertIs(result.status, DeleteStorageCleanupStatus.CONFIRMED_PENDING_STORAGE)


if __name__ == "__main__":
    unittest.main()
