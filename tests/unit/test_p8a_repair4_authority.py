"""Focused P8.A Repair-4 pending-journal authority tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import codex_control.deployment as deployment
from codex_control.deployment import (
    DeploymentError,
    _pending_path,
    _read_pending,
    _recover_pending_previous,
    _write_pending,
    current_target,
    rehearsal_rollback,
    rehearsal_switch_current,
    stage_rehearsal_release,
)


class Repair4PendingAuthorityTests(unittest.TestCase):
    def _pair(self, base: Path) -> tuple[Path, str, str]:
        source = base / "source"
        source.mkdir()
        (source / "payload").write_text("offline fixture\n")
        root = base / "root"
        old = "a" * 40
        new = "b" * 40
        stage_rehearsal_release(source, root=root, git_sha=old)
        rehearsal_switch_current(root, old, current_db_schema=4)
        stage_rehearsal_release(source, root=root, git_sha=new)
        return root, old, new

    def _switch_without_state_update(self, root: Path, old: str, new: str) -> None:
        pending = _pending_path(root)
        _write_pending(pending, old_current_sha=old, new_target_sha=new, state="PREPARED")
        current = root / "opt/codex-control/current"
        temporary = current.parent / ".repair4-current.next"
        os.symlink(os.path.relpath(root / "opt/codex-control/releases" / new, current.parent), temporary)
        os.replace(temporary, current)

    def test_pending_journal_rewrite_is_atomic_and_preserves_prior_record_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            pending = _pending_path(root)
            pending.parent.mkdir(mode=0o755, parents=True)
            old = "a" * 40
            new = "b" * 40
            _write_pending(pending, old_current_sha=old, new_target_sha=new, state="PREPARED")
            before = pending.read_bytes()

            original_replace = os.replace

            def fail_pending(source: str | os.PathLike[str], target: str | os.PathLike[str]):
                if Path(target) == pending:
                    raise OSError("injected pending replacement failure")
                return original_replace(source, target)

            with mock.patch.object(deployment.os, "replace", side_effect=fail_pending):
                with self.assertRaisesRegex(DeploymentError, "pending_previous_write_failed"):
                    _write_pending(pending, old_current_sha=old, new_target_sha=new, state="CURRENT_SWITCHED")
            self.assertEqual(before, pending.read_bytes())
            self.assertEqual(0o600, pending.stat().st_mode & 0o777)
            self.assertEqual([], list(pending.parent.glob(".previous.next.*")))

    def test_prepared_record_with_current_new_recovers_immediate_old_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root, old, new = self._pair(Path(directory))
            self._switch_without_state_update(root, old, new)
            self.assertFalse((root / "opt/codex-control/previous").exists())

            recovered = _recover_pending_previous(root)

            self.assertEqual(old, recovered)
            self.assertEqual(new, current_target(root).name)
            self.assertEqual(old, (root / "opt/codex-control/previous").read_text().strip())
            self.assertIsNone(_read_pending(root))

    def test_first_upgrade_prepared_after_switch_recovers_without_prior_previous_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root, old, new = self._pair(Path(directory))
            previous = root / "opt/codex-control/previous"
            self.assertFalse(previous.exists())
            self._switch_without_state_update(root, old, new)

            rehearsal_rollback(root, current_db_schema=4)

            self.assertEqual(old, current_target(root).name)
            self.assertEqual(new, previous.read_text().strip())
            self.assertFalse(_pending_path(root).exists())

    def test_finalized_journal_write_failure_keeps_previous_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root, old, new = self._pair(Path(directory))
            pending = _pending_path(root)
            original_replace = os.replace
            pending_replacements = 0

            def fail_finalized(source: str | os.PathLike[str], target: str | os.PathLike[str]):
                nonlocal pending_replacements
                if Path(target) == pending:
                    pending_replacements += 1
                    if pending_replacements == 3:
                        raise OSError("injected finalized journal failure")
                return original_replace(source, target)

            with mock.patch.object(deployment.os, "replace", side_effect=fail_finalized):
                with self.assertRaisesRegex(DeploymentError, "pending_previous_write_failed"):
                    rehearsal_switch_current(root, new, current_db_schema=4)

            self.assertEqual(new, current_target(root).name)
            self.assertEqual(old, (root / "opt/codex-control/previous").read_text().strip())
            record = _read_pending(root)
            self.assertEqual("CURRENT_SWITCHED", record["state"])
            pending_bytes = pending.read_bytes()
            json.loads(pending_bytes.decode("ascii"))

            rehearsal_rollback(root, current_db_schema=4)
            self.assertEqual(old, current_target(root).name)

    def test_prepared_state_update_failure_retains_complete_record_through_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root, old, new = self._pair(Path(directory))
            self._switch_without_state_update(root, old, new)
            pending = _pending_path(root)
            before = pending.read_bytes()
            original_replace = os.replace

            def fail_current_switched(source: str | os.PathLike[str], target: str | os.PathLike[str]):
                if Path(target) == pending:
                    raise OSError("injected CURRENT_SWITCHED failure")
                return original_replace(source, target)

            with mock.patch.object(deployment.os, "replace", side_effect=fail_current_switched):
                with self.assertRaisesRegex(DeploymentError, "pending_previous_write_failed"):
                    _recover_pending_previous(root)
            self.assertEqual(before, pending.read_bytes())
            self.assertEqual("PREPARED", _read_pending(root)["state"])

            rehearsal_rollback(root, current_db_schema=4)
            self.assertEqual(old, current_target(root).name)
            self.assertEqual(new, (root / "opt/codex-control/previous").read_text().strip())

    def test_pending_journal_malformed_or_oversize_fails_closed(self):
        for value in (b"not-json\n", b'{"old_current_sha":null,"new_target_sha":"' + b"b" * 40 + b'","state":"PREPARED","extra":1}\n', b"x" * (deployment._MAX_PENDING_JOURNAL + 1)):
            with self.subTest(value=value[:20]), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "root"
                pending = _pending_path(root)
                pending.parent.mkdir(mode=0o755, parents=True)
                pending.write_bytes(value)
                with self.assertRaisesRegex(DeploymentError, "pending_previous_invalid"):
                    _read_pending(root)

    def test_pending_temp_collision_or_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            pending = _pending_path(root)
            pending.parent.mkdir(mode=0o755, parents=True)
            old = "a" * 40
            new = "b" * 40
            _write_pending(pending, old_current_sha=old, new_target_sha=new, state="PREPARED")
            before = pending.read_bytes()
            with mock.patch.object(deployment.uuid, "uuid4", return_value=mock.Mock(hex="collision")):
                collision = pending.parent / ".previous.next.collision.tmp"
                collision.symlink_to(pending)
                with self.assertRaisesRegex(DeploymentError, "pending_previous_invalid"):
                    _write_pending(pending, old_current_sha=old, new_target_sha=new, state="CURRENT_SWITCHED")
                self.assertTrue(collision.is_symlink())
            self.assertEqual(before, pending.read_bytes())


if __name__ == "__main__":
    unittest.main()
