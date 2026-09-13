import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from codex_control.service import ProductionService, build_production_assembly
from codex_control.storage import ControllerRuntimeRepository, SqliteStorage
from codex_control.adapters.telegram.bot_api import HttpResponse, TelegramBotApiTransport

from codex_control.deployment import (
    DeploymentError, current_target, install_upgrade, rollback, stage_release,
    switch_current, validate_release, verify_installation,
)


class P8ADeploymentOfflineAcceptance(unittest.TestCase):
    def test_a_to_b_failed_health_rolls_back_without_state_config_secret_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "alternate-root"
            root.mkdir()
            source_a = Path(directory) / "release-a"
            source_b = Path(directory) / "release-b"
            source_a.mkdir(); source_b.mkdir()
            (source_a / "app.py").write_text("release A\n")
            (source_b / "app.py").write_text("release B\n")
            config = root / "etc" / "codex-control" / "server.toml"
            secrets = root / "etc" / "codex-control" / "secrets.env"
            state = root / "var" / "lib" / "codex-control" / "controller.sqlite3"
            config.parent.mkdir(parents=True)
            state.parent.mkdir(parents=True)
            config.write_bytes(b"config-authority\n")
            secrets.write_bytes(b"TELEGRAM_BOT_TOKEN=offline-only\n")
            secrets.chmod(0o600)
            with sqlite3.connect(state) as connection:
                connection.execute("PRAGMA user_version=4")
            before = (config.read_bytes(), secrets.read_bytes(), state.read_bytes())
            sha_a, sha_b = "a" * 40, "b" * 40
            stage_release(source_a, root=root, git_sha=sha_a)
            switch_current(root, sha_a)
            result = install_upgrade(root, source_b, git_sha=sha_b, health_check=lambda: False)
            self.assertTrue(result["rolled_back"])
            self.assertEqual(sha_a, current_target(root).name)
            self.assertEqual(before, (config.read_bytes(), secrets.read_bytes(), state.read_bytes()))
            self.assertEqual(sha_a, validate_release(current_target(root)).git_sha)

    def test_manifest_idempotence_schema_gate_and_path_attacks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"; root.mkdir()
            source = Path(directory) / "source"; source.mkdir(); (source / "x").write_text("x")
            sha = "c" * 40
            first = stage_release(source, root=root, git_sha=sha)
            second = stage_release(source, root=root, git_sha=sha)
            self.assertEqual(first, second)
            with self.assertRaises(DeploymentError):
                switch_current(root, sha, current_db_schema=3)
            switch_current(root, sha)
            current = root / "opt" / "codex-control" / "current"
            current.unlink()
            current.symlink_to("../../../../outside")
            with self.assertRaises(DeploymentError):
                current_target(root)

    def test_verification_reports_manifest_and_authority_without_external_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"; root.mkdir()
            source = Path(directory) / "source"; source.mkdir(); (source / "x").write_text("x")
            sha = "d" * 40
            stage_release(source, root=root, git_sha=sha); switch_current(root, sha)
            info = verify_installation(root, expected_sha=sha)
            self.assertEqual(sha, info["installed_release_sha"])
            self.assertEqual(64, len(info["manifest_sha256"]))
            self.assertEqual((), info["configured_profiles"])

    def test_assembly_boots_sleep_and_recovers_before_poll(self):
        import asyncio

        async def exercise():
            with tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                state, repo, work, home, isolated = [base / name for name in ("state", "repo", "work", "home", "isolated")]
                for item in (state, repo, work, home, isolated): item.mkdir(mode=0o700)
                executable = base / "codex"
                executable.write_text("#!/bin/sh\nexit 0\n"); executable.chmod(0o755)
                db = state / "controller.sqlite3"
                seed = await SqliteStorage.open(str(db)); await seed.close()
                config = base / "server.toml"
                config.write_text(f'''[server]\nserver_id="server-80"\ndisplay_name="SERVER-80"\noperator_user_id=7\ncontrol_chat_id=-100\nfleet_version="v1"\n[fleet]\n[[fleet.servers]]\nserver_id="server-80"\ndisplay_name="SERVER-80"\n[runtime]\nstate_root="{state}"\nworking_directory="{work}"\nrepository_root="{repo}"\ncontroller_db_path="{db}"\ntelegram_text_limit=3800\ncodex_executable="{executable}"\n[[profiles]]\nprofile_id="p1"\ndisplay_name="P1"\ncodex_home="{home}"\nisolated_state_root="{isolated}"\n''')
                secrets = base / "secrets.env"; secrets.write_text("TELEGRAM_BOT_TOKEN=offline-only\n"); secrets.chmod(0o600)
                fake_http = type("Fake", (), {"request": lambda self, *args, **kwargs: None})()
                # No polling call is made by startup; the fake is intentionally
                # never awaited and therefore cannot reach a network.
                class OfflineHttp:
                    async def request(self, method, payload, *, timeout):
                        raise AssertionError("polling must not begin during startup")
                telegram = TelegramBotApiTransport("offline-only", http=OfflineHttp())
                assembly = await build_production_assembly(config, secrets, test_only=True, telegram=telegram)
                service = ProductionService(assembly)
                await service.startup()
                runtime = await ControllerRuntimeRepository(assembly.storage).get()
                self.assertEqual("SLEEP", runtime.requested_mode.value)
                self.assertTrue(service._accepting)
                await service.shutdown()
        asyncio.run(exercise())
