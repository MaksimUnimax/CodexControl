import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.telegram import PrivateCommand
from codex_control.application import (
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlPanel,
    PrivateControlReason,
    PrivateControlService,
    PrivateControlStatus,
    PrivateDiagnosticState,
    PrivateDiagnosticsSnapshot,
)
from codex_control.domain import CodexProfile, ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    ErrorFingerprintRepository,
    IngressDispositionKind,
    IngressUpdateRepository,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    SettingsRepository,
    SqliteStorage,
)


class Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (CodexModelDescriptor("model-a", "wire-a", "Model A", ("high",), "high", True, False),),
            0.0, 1.0,
        )


class PassiveEffects:
    async def interrupt(self, request):
        raise AssertionError("interrupt must not be called")

    async def delete(self, request):
        raise AssertionError("delete must not be called")


class PrivateControlIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.clock_calls = 0

        def clock():
            self.clock_calls += 1
            return 100

        self.clock = clock
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=clock)
        await ControllerRuntimeRepository(self.storage, now_ms=clock).begin_boot("fleet")
        await SettingsRepository(self.storage, now_ms=clock).initialize_if_absent(
            profile_id="profile-a", model_id="model-a", reasoning_effort="high"
        )
        self.number = 0

        def token_factory():
            self.number += 1
            return f"{self.number:032d}"

        self.service = PrivateControlService(
            self.storage,
            server_id="server-80",
            server_display_name="Server 80",
            operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A"),),
            model_catalog=Catalog(), interrupt_service=PassiveEffects(), delete_service=PassiveEffects(),
            mode_provider=lambda: ControllerMode.SLEEP,
            now_ms=clock, token_factory=token_factory,
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    @staticmethod
    def token(panel, label):
        return next(button.callback_data[4:] for row in panel.rows for button in row if button.label == label)

    async def test_menu_control_dedupe_and_no_mode_or_job(self):
        first = await self.service.handle_command(PrivateCommandRequest(10, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateControlStatus.RENDERED, first.status)
        self.assertIsInstance(first.panel, PrivateControlPanel)
        self.assertEqual(IngressDispositionKind.CONTROL, (await IngressUpdateRepository(self.storage).get(10)).disposition)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
        before = await ControllerRuntimeRepository(self.storage).get()
        duplicate = await self.service.handle_command(PrivateCommandRequest(10, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateControlStatus.DUPLICATE, duplicate.status)
        self.assertIsNone(duplicate.panel)
        self.assertEqual(4, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        self.assertEqual(before, await ControllerRuntimeRepository(self.storage).get())

    async def test_unauthorized_menu_is_durable_ignored_without_content(self):
        result = await self.service.handle_command(PrivateCommandRequest(11, 8, 8, PrivateCommand.MENU))
        self.assertEqual(PrivateControlStatus.UNAUTHORIZED, result.status)
        self.assertEqual(IngressDispositionKind.IGNORED_UNAUTHORIZED, (await IngressUpdateRepository(self.storage).get(11)).disposition)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))

    async def test_unknown_callback_is_blocked_and_not_consumed(self):
        token = "u" * 32
        await PrivateManagementRepository(self.storage, now_ms=self.clock).create_callback_batch(
            actions=(PrivateCallbackActionSpec(
                hashlib.sha256(token.encode()).hexdigest(), "UNKNOWN_ACTION", "test", "target", 1,
                "PRIVATE_ROOT", 7, 7,
            ),), created_at_ms=100, expires_at_ms=1000,
        )
        result = await self.service.handle_callback(PrivateCallbackRequest(12, 7, 7, "query", token))
        self.assertEqual((PrivateControlStatus.BLOCKED, PrivateControlReason.ACTION_UNAVAILABLE), (result.status, result.reason))
        self.assertIsNone(await self.storage.read(lambda c: c.execute("SELECT consumed_at_ms FROM callback_actions").fetchone()[0]))

    async def test_diagnostics_uses_latest_safe_error_projection(self):
        fingerprint = "a" * 64
        await ErrorFingerprintRepository(self.storage, now_ms=self.clock).record(
            fingerprint_sha256=fingerprint, error_class="CODEX_PROCESS"
        )
        provider = lambda: PrivateDiagnosticsSnapshot(PrivateDiagnosticState.OK, PrivateDiagnosticState.DEGRADED, 12, 34, 56)
        self.service._diagnostics_provider = provider
        root = await self.service.handle_command(PrivateCommandRequest(13, 7, 7, PrivateCommand.MENU))
        result = await self.service.handle_callback(PrivateCallbackRequest(14, 7, 7, "query", self.token(root.panel, "Diagnostics")))
        self.assertEqual(PrivateControlStatus.RENDERED, result.status)
        self.assertIn("CODEX_PROCESS", result.panel.text)
        self.assertIn("scope controller", result.panel.text)
        self.assertNotIn(fingerprint, result.panel.text)

    async def test_wrong_principal_does_not_peek_or_consume_callback(self):
        root = await self.service.handle_command(PrivateCommandRequest(15, 7, 7, PrivateCommand.MENU))
        token = self.token(root.panel, "Refresh")
        result = await self.service.handle_callback(PrivateCallbackRequest(16, 8, 8, "query", token))
        self.assertEqual(PrivateControlStatus.UNAUTHORIZED, result.status)
        self.assertIsNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute("SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))

    async def test_boot_generation_drift_consumes_old_p43_callback_as_stale(self):
        root = await self.service.handle_command(PrivateCommandRequest(17, 7, 7, PrivateCommand.MENU))
        token = self.token(root.panel, "Refresh")
        await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet")
        result = await self.service.handle_callback(PrivateCallbackRequest(18, 7, 7, "query", token))
        self.assertEqual((PrivateControlStatus.STALE, PrivateControlReason.STALE_ACTION), (result.status, result.reason))
        self.assertIsNotNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute("SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))
