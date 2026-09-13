"""Focused P8.A Repair-2 authority and zero-effect tests."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from codex_control.adapters.codex.capabilities import load_manifest
from codex_control.adapters.telegram.bot_api import HttpResponse, TelegramBotApiTransport
from codex_control.deployment import (
    DeploymentError,
    DeploymentRootAuthority,
    DeploymentState,
    install_upgrade,
    production_rollback,
    release_path,
    rehearsal_install_upgrade,
    rehearsal_switch_current,
    stage_rehearsal_release,
    stage_release,
    validate_release,
    verify_installation,
)
from codex_control.service import ServiceError, build_production_assembly, validate_production_authority
from codex_control.storage import SqliteStorage


BASE_SHA = "09214a2a0a0ce92a2847dda24c3512447c822f1c"
BASE_TREE = "56ac091de95ad809df9408a3da91fb4c00baa6f3"


class _FakeHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, float]] = []

    async def request(self, method, payload, *, timeout):
        self.calls.append((method, dict(payload), timeout))
        return HttpResponse(200, b'{"ok":true,"result":[]}')


class Repair2AuthorityTests(unittest.TestCase):
    def _git_repo(self, directory: Path) -> tuple[Path, str, str]:
        repo = directory / "repo"
        repo.mkdir()
        (repo / "pyproject.toml").write_text(
            "[build-system]\nrequires=[]\nbuild-backend='setuptools.build_meta'\n"
            "[project]\nname='fixture'\nversion='1.0.0'\n",
        )
        (repo / "tracked.txt").write_text("tracked\n")
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "P8A test"], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
        sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        tree = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD^{tree}"], text=True).strip()
        return repo, sha, tree

    def test_installed_codex_wrong_version_blocks_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, executable, db = self._service_authority(base, "codex-cli 0.144.7")
            with self.assertRaises(ServiceError):
                validate_production_authority(config, secrets, test_only=True)
            self.assertTrue(db.exists())

    def test_installed_codex_wrong_version_blocks_serve_before_storage_and_poll(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                config, secrets, _, _ = self._service_authority(base, "codex-cli 0.144.7")
                with mock.patch.object(SqliteStorage, "open", side_effect=AssertionError("writable open")):
                    with self.assertRaises(ServiceError):
                        await build_production_assembly(config, secrets, test_only=True)
        asyncio.run(exercise())

    async def _poll(self, fake: _FakeHttp) -> None:
        await TelegramBotApiTransport("offline", http=fake).get_updates()

    def test_long_poll_http_deadline_exceeds_telegram_timeout(self):
        fake = _FakeHttp()
        asyncio.run(self._poll(fake))
        method, payload, timeout = fake.calls[0]
        self.assertEqual("getUpdates", method)
        self.assertGreater(timeout, payload["timeout"])
        self.assertEqual(35.0, timeout)

    def test_root_requires_explicit_production_authority(self):
        sha = "a" * 40
        with self.assertRaises(DeploymentError):
            release_path("/", sha)
        self.assertEqual(Path("/opt/codex-control/releases") / sha, release_path(DeploymentRootAuthority(Path("/"), True), sha))

    def test_arbitrary_directory_cannot_claim_git_sha(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            arbitrary = base / "arbitrary"
            arbitrary.mkdir()
            (arbitrary / "x").write_text("not git")
            with self.assertRaises(DeploymentError):
                stage_release(arbitrary, root=base / "root", git_sha=BASE_SHA)

    def test_exact_git_commit_tree_is_exported(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, sha, tree = self._git_repo(Path(directory))
            target, _ = stage_release(repo, root=Path(directory) / "root", git_sha=sha)
            manifest = validate_release(target, source_repository=repo)
            self.assertEqual(tree, manifest.source_tree_sha)
            self.assertEqual("tracked\n", (target / "tracked.txt").read_text())
            (repo / "untracked.txt").write_text("must not export")
            self.assertFalse((target / "untracked.txt").exists())

    def test_stage_builds_release_local_codex_control_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            target, _ = stage_release("/root/CodexControl", root=Path(directory) / "root", git_sha=BASE_SHA)
            executable = target / ".venv/bin/codex-control"
            self.assertTrue(executable.is_file())
            self.assertFalse(executable.is_symlink())
            self.assertTrue(os.access(executable, os.X_OK))
            self.assertEqual(0, subprocess.run([str(executable), "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode)

    def test_build_failure_never_publishes_final_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            with self.assertRaises(DeploymentError):
                stage_release(
                    "/root/CodexControl", root=root, git_sha=BASE_SHA,
                    build_hook=lambda stage: (_ for _ in ()).throw(RuntimeError("injected")),
                )
            self.assertFalse(release_path(root, BASE_SHA).exists())

    def test_production_switch_requires_actual_db_config_secrets_runtime_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            repo, sha, _ = self._git_repo(base)
            with self.assertRaises(TypeError):
                install_upgrade(DeploymentRootAuthority(base / "root"), repo, git_sha=sha)  # type: ignore[call-arg]

    def test_missing_health_evidence_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            (source / "payload").write_text("A")
            result = rehearsal_install_upgrade(base / "root", source, git_sha="a" * 40, current_db_schema=4)
            self.assertEqual(DeploymentState.SWITCHED_AWAITING_SERVICE_HEALTH.value, result["state"])
            self.assertIsNone(result["healthy"])

    def test_verify_probes_actual_installed_codex(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _, _ = self._service_authority(base, "codex-cli 0.144.7")
            source = base / "source"
            source.mkdir()
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            with self.assertRaises(DeploymentError):
                verify_installation(
                    DeploymentRootAuthority(base / "root"), config_path=config,
                    secrets_path=secrets, service_unit="/root/CodexControl/deploy/systemd/codex-control.service",
                    test_only=True,
                )

    def test_production_rollback_reads_actual_db_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            config, secrets, _, db = self._service_authority(base, "codex-cli 0.144.6")
            source = base / "source"
            source.mkdir()
            stage_rehearsal_release(source, root=base / "root", git_sha="a" * 40)
            rehearsal_switch_current(base / "root", "a" * 40, current_db_schema=4)
            stage_rehearsal_release(source, root=base / "root", git_sha="b" * 40)
            rehearsal_switch_current(base / "root", "b" * 40, current_db_schema=4)
            with sqlite3.connect(db) as connection:
                connection.execute("PRAGMA user_version=3")
            with self.assertRaises(DeploymentError):
                production_rollback(
                    DeploymentRootAuthority(base / "root"), config_path=config,
                    secrets_path=secrets, service_unit="/root/CodexControl/deploy/systemd/codex-control.service",
                    test_only=True,
                )

    def _service_authority(self, base: Path, version: str) -> tuple[Path, Path, Path, Path]:
        state, repo, work, home, isolated = [base / name for name in ("state", "repo", "work", "home", "isolated")]
        for item in (state, repo, work, home, isolated):
            item.mkdir(mode=0o700)
        executable = base / "codex"
        executable.write_text(f"#!/bin/sh\nif [ \"$1\" = \"--version\" ]; then echo '{version}'; exit 0; fi\nexit 0\n")
        executable.chmod(0o755)
        db = state / "controller.sqlite3"
        with sqlite3.connect(db) as connection:
            connection.execute("PRAGMA user_version=4")
        config = base / "server.toml"
        config.write_text(
            f'''[server]\nserver_id="server-80"\ndisplay_name="SERVER-80"\noperator_user_id=7\ncontrol_chat_id=-100\nfleet_version="v1"\n[fleet]\n[[fleet.servers]]\nserver_id="server-80"\ndisplay_name="SERVER-80"\n[runtime]\nstate_root="{state}"\nworking_directory="{work}"\nrepository_root="{repo}"\ncontroller_db_path="{db}"\ntelegram_text_limit=3800\ncodex_executable="{executable}"\n[[profiles]]\nprofile_id="p1"\ndisplay_name="P1"\ncodex_home="{home}"\nisolated_state_root="{isolated}"\n''',
        )
        secrets = base / "secrets.env"
        secrets.write_text("TELEGRAM_BOT_TOKEN=offline-only\n")
        secrets.chmod(0o600)
        return config, secrets, executable, db


if __name__ == "__main__":
    unittest.main()
