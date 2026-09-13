"""Focused P8.A Repair-3 transactional authority tests."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codex_control.deployment import (
    DeploymentError,
    DeploymentRootAuthority,
    current_target,
    install_upgrade,
    rehearsal_rollback,
    rehearsal_switch_current,
    release_path,
    stage_rehearsal_release,
    stage_release,
    _read_pending,
    validate_release,
)
from codex_control.service import ServiceError, initialize_controller_state


class Repair3AuthorityTests(unittest.TestCase):
    def _authority_files(self, base: Path, *, database: Path | None = None) -> tuple[Path, Path, Path]:
        state, repo, work, home, isolated = [base / name for name in ("state", "repo", "work", "home", "isolated")]
        for item in (state, repo, work, home, isolated):
            item.mkdir(mode=0o700)
        executable = base / "codex"
        executable.write_text("#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo 'codex-cli 0.144.6'; fi\n")
        executable.chmod(0o755)
        database = database or state / "controller.sqlite3"
        config = base / "server.toml"
        config.write_text(
            f'''[server]\nserver_id="server-80"\ndisplay_name="SERVER-80"\noperator_user_id=7\ncontrol_chat_id=-100\nfleet_version="v1"\n[fleet]\n[[fleet.servers]]\nserver_id="server-80"\ndisplay_name="SERVER-80"\n[runtime]\nstate_root="{state}"\nworking_directory="{work}"\nrepository_root="{repo}"\ncontroller_db_path="{database}"\ntelegram_text_limit=3800\ncodex_executable="{executable}"\n[[profiles]]\nprofile_id="p1"\ndisplay_name="P1"\ncodex_home="{home}"\nisolated_state_root="{isolated}"\n''',
        )
        secrets = base / "secrets.env"
        secrets.write_text("TELEGRAM_BOT_TOKEN=offline-only\n")
        secrets.chmod(0o600)
        return config, secrets, executable

    def _git_repo(self, base: Path) -> tuple[Path, str, str]:
        repo = base / "source"
        repo.mkdir()
        (repo / "pyproject.toml").write_text(
            "[build-system]\nrequires=[]\nbuild-backend='setuptools.build_meta'\n"
            "[project]\nname='fixture'\nversion='1.0.0'\n",
        )
        (repo / "tracked.txt").write_text("tracked\n")
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "P8A Repair-3"], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
        sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()
        return repo, sha, tree

    def test_initialize_controller_state_canonical_existing_state_root(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, executable = self._authority_files(base)
            self.assertEqual(4, initialize_controller_state(config, secrets, test_only=True))
            database = base / "state/controller.sqlite3"
            self.assertTrue(database.is_file())
            self.assertFalse(database.is_symlink())
            with sqlite3.connect(database) as connection:
                self.assertEqual(4, connection.execute("PRAGMA user_version").fetchone()[0])
            self.assertTrue(executable.is_file())

    def test_initialize_controller_state_second_attempt_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _ = self._authority_files(base)
            initialize_controller_state(config, secrets, test_only=True)
            with self.assertRaisesRegex(ServiceError, "database_already_initialized"):
                initialize_controller_state(config, secrets, test_only=True)

    def test_serve_missing_db_does_not_initialize(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _ = self._authority_files(base)
            from codex_control.service import build_production_assembly

            with self.assertRaises(ServiceError):
                import asyncio
                asyncio.run(build_production_assembly(config, secrets, test_only=True))
            self.assertFalse((base / "state/controller.sqlite3").exists())

    def test_initialize_rejects_unsafe_parent_symlink_db_and_special_file(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            unsafe_parent = base / "outside"
            unsafe_parent.mkdir(mode=0o700)
            config, secrets, _ = self._authority_files(base, database=unsafe_parent / "controller.sqlite3")
            with self.assertRaises(ServiceError):
                initialize_controller_state(config, secrets, test_only=True)
            self.assertFalse((unsafe_parent / "controller.sqlite3").exists())

            second = base / "second"
            second.mkdir()
            config, secrets, _ = self._authority_files(second)
            database = second / "state/controller.sqlite3"
            database.symlink_to(second / "outside-db")
            with self.assertRaises(ServiceError):
                initialize_controller_state(config, secrets, test_only=True)
            database.unlink()
            database.write_text("not sqlite")
            with self.assertRaises(ServiceError):
                initialize_controller_state(config, secrets, test_only=True)

    def test_staged_validate_failure_never_publishes_final_release(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, executable = self._authority_files(base)
            with sqlite3.connect(base / "state/controller.sqlite3") as connection:
                connection.execute("PRAGMA user_version=4")
            source, sha, _ = self._git_repo(base)
            unit = base / "codex-control.service"
            unit.write_text("[Service]\n")
            with mock.patch("codex_control.deployment._run_staged_validate", side_effect=DeploymentError("injected")):
                with self.assertRaises(DeploymentError):
                    install_upgrade(
                        DeploymentRootAuthority(base / "root"), source, git_sha=sha,
                        config_path=config, secrets_path=secrets, service_unit=unit,
                        test_only=True, python_executable=sys.executable,
                    )
            self.assertFalse(release_path(base / "root", sha).exists())
            self.assertIsNone(current_target(base / "root"))
            self.assertTrue(executable.is_file())

    def test_staged_validate_failure_keeps_current_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _ = self._authority_files(base)
            with sqlite3.connect(base / "state/controller.sqlite3") as connection:
                connection.execute("PRAGMA user_version=4")
            source, sha_b, _ = self._git_repo(base)
            sha_a = "a" * 40
            unit = base / "codex-control.service"
            unit.write_text("[Service]\n")
            source_a = base / "release-a"
            source_a.mkdir()
            stage_rehearsal_release(source_a, root=base / "root", git_sha=sha_a, service_unit=unit)
            rehearsal_switch_current(base / "root", sha_a, current_db_schema=4)
            with mock.patch("codex_control.deployment._run_staged_validate", side_effect=DeploymentError("injected")):
                with self.assertRaises(DeploymentError):
                    install_upgrade(
                        DeploymentRootAuthority(base / "root"), source, git_sha=sha_b,
                        config_path=config, secrets_path=secrets, service_unit=unit,
                        test_only=True, python_executable=sys.executable,
                    )
            self.assertEqual(sha_a, current_target(base / "root").name)
            self.assertFalse(release_path(base / "root", sha_b).exists())

    def test_existing_valid_release_survives_failed_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _ = self._authority_files(base)
            with sqlite3.connect(base / "state/controller.sqlite3") as connection:
                connection.execute("PRAGMA user_version=4")
            source, sha, _ = self._git_repo(base)
            unit = base / "codex-control.service"
            unit.write_text("[Service]\n")
            stage_release(source, root=base / "root", git_sha=sha, service_unit=unit)
            with mock.patch("codex_control.deployment._run_staged_validate", side_effect=DeploymentError("injected")):
                with self.assertRaises(DeploymentError):
                    install_upgrade(
                        DeploymentRootAuthority(base / "root"), source, git_sha=sha,
                        config_path=config, secrets_path=secrets, service_unit=unit,
                        test_only=True, python_executable=sys.executable,
                    )
            self.assertTrue(release_path(base / "root", sha).is_dir())

    def test_successful_private_validation_publishes_exact_git_tree_and_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _ = self._authority_files(base)
            with sqlite3.connect(base / "state/controller.sqlite3") as connection:
                connection.execute("PRAGMA user_version=4")
            source, sha, tree = self._git_repo(base)
            unit = base / "codex-control.service"
            unit.write_text("[Service]\n")
            observed: list[Path] = []

            def private_validate(executable: Path, *_args):
                observed.append(executable)
                self.assertTrue(executable.is_file())
                self.assertIn(".stage-", executable.as_posix())
                self.assertFalse(release_path(base / "root", sha).exists())

            with mock.patch("codex_control.deployment._run_staged_validate", side_effect=private_validate):
                result = install_upgrade(
                    DeploymentRootAuthority(base / "root"), source, git_sha=sha,
                    config_path=config, secrets_path=secrets, service_unit=unit,
                    test_only=True, python_executable=sys.executable,
                )
            target = current_target(base / "root")
            self.assertEqual(sha, target.name)
            self.assertTrue(observed)
            manifest = validate_release(target, source_repository=source, service_unit=unit)
            self.assertEqual(tree, manifest.source_tree_sha)
            self.assertEqual(sha, result["current_sha"])
            self.assertTrue((target / ".venv/bin/codex-control").is_file())

    def test_current_failure_keeps_previous_truthful(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "release"
            source.mkdir()
            (source / "payload").write_text("release")
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            stage_rehearsal_release(source, root=base / "root", git_sha="b" * 40)
            original_replace = os.replace

            def fail_current(source_path, target_path):
                if Path(target_path).name == "current":
                    raise OSError("injected current failure")
                return original_replace(source_path, target_path)

            with mock.patch("codex_control.deployment.os.replace", side_effect=fail_current):
                with self.assertRaisesRegex(DeploymentError, "current_switch_failed"):
                    rehearsal_switch_current(base / "root", "b" * 40, current_db_schema=4)
            self.assertEqual("a" * 40, current_target(base / "root").name)
            self.assertFalse((base / "root/opt/codex-control/previous").exists())
            self.assertFalse((base / "root/opt/codex-control/.previous.next").exists())

    def test_previous_finalize_failure_retains_recoverable_old_current(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "release"
            source.mkdir()
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            stage_rehearsal_release(source, root=base / "root", git_sha="b" * 40)
            original_replace = os.replace

            def fail_previous(source_path, target_path):
                if Path(target_path).name == "previous":
                    raise OSError("injected previous failure")
                return original_replace(source_path, target_path)

            with mock.patch("codex_control.deployment.os.replace", side_effect=fail_previous):
                with self.assertRaisesRegex(DeploymentError, "previous_record_failed"):
                    rehearsal_switch_current(base / "root", "b" * 40, current_db_schema=4)
            self.assertEqual("b" * 40, current_target(base / "root").name)
            pending = base / "root/opt/codex-control/.previous.next"
            self.assertTrue(pending.is_file())
            self.assertIn("CURRENT_SWITCHED", pending.read_text())
            self.assertEqual("a" * 40, _read_pending(base / "root")["old_current_sha"])

    def test_restart_recovery_resolves_pending_previous_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "release"
            source.mkdir()
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            stage_rehearsal_release(source, root=base / "root", git_sha="b" * 40)
            original_replace = os.replace

            def fail_once(source_path, target_path):
                if Path(target_path).name == "previous":
                    raise OSError("injected previous failure")
                return original_replace(source_path, target_path)

            with mock.patch("codex_control.deployment.os.replace", side_effect=fail_once):
                with self.assertRaises(DeploymentError):
                    rehearsal_switch_current(base / "root", "b" * 40, current_db_schema=4)
            # A fresh recovery process promotes the pending immediate prior
            # current before rollback consults the durable previous record.
            rehearsal_rollback(base / "root", current_db_schema=4)
            self.assertEqual("a" * 40, current_target(base / "root").name)
            self.assertEqual("b" * 40, (base / "root/opt/codex-control/previous").read_text().strip())
            self.assertFalse((base / "root/opt/codex-control/.previous.next").exists())

    def test_pending_previous_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "release"
            source.mkdir()
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            pending = base / "root/opt/codex-control/.previous.next"
            pending.write_text('{"old_current_sha":"' + "a" * 40 + '","new_target_sha":"' + "c" * 40 + '","state":"CURRENT_SWITCHED"}\n')
            with self.assertRaisesRegex(DeploymentError, "pending_release_missing"):
                rehearsal_rollback(base / "root", current_db_schema=4)

    def test_production_deploy_cli_has_no_test_only_authority_flag(self):
        command = [
            sys.executable, "/root/CodexControl/deploy/codex_control_deploy.py", "upgrade",
            "--root", "/tmp/p8a-repair3-root", "--source", "/tmp/source", "--sha", "a" * 40,
            "--config", "/tmp/config", "--secrets", "/tmp/secrets", "--service-unit", "/tmp/unit",
            "--test-only-authority",
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unrecognized arguments", result.stderr)
        source = Path("/root/CodexControl/deploy/codex_control_deploy.py").read_text()
        self.assertNotIn("test-only-authority", source)


if __name__ == "__main__":
    unittest.main()
