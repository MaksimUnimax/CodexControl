import hashlib
import tempfile
import unittest

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.telegram import PrivateCommand, PrivateInboundKind, TelegramPrivateUpdateAdapter
from codex_control.application import (
    PrivateAdminError,
    PrivateAdminErrorCategory,
    PrivateAdminReason,
    PrivateAdminStatus,
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateSettingsManagementService,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    IngressDispositionKind,
    IngressUpdateRepository,
    SCHEMA_V1_DDL_SHA256,
    SettingsRepository,
    SqliteStorage,
)


class Clock:
    def __init__(self, value=100):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


class FakeCatalog:
    def __init__(self, long_model=False):
        self.long_model = long_model
        self.available = True
        self.calls = []

    async def get_catalog(self, profile_id, *, refresh=False):
        self.calls.append((profile_id, refresh))
        if not self.available:
            raise RuntimeError("PRIVATE_CATALOG_ERROR")
        model_id = "m" * 256 if self.long_model else "model-a"
        return CodexModelCatalog(
            profile_id,
            1,
            (
                CodexModelDescriptor(model_id, "wire", "Long Model" if self.long_model else "Model A", ("low", "high"), "high", True, False),
                CodexModelDescriptor("hidden", "wire-hidden", "Hidden", ("high",), "high", False, True),
            ),
            0.0,
            1.0,
        )


class PrivateTelegramSettingsIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.storage = await SqliteStorage.open(self.tempdir.name + "/controller.sqlite3", now_ms=self.clock)
        self.catalog = FakeCatalog()
        self.token_index = 0

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def token_factory(self):
        self.token_index += 1
        return f"{self.token_index:032d}"

    def service(self, **kwargs):
        values = dict(
            server_id="server-80",
            server_display_name="SERVER-80",
            operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A"), CodexProfile("profile-b", "/synthetic/profile-b", "Profile B")),
            model_catalog=self.catalog,
            now_ms=self.clock,
            token_factory=self.token_factory,
        )
        values.update(kwargs)
        return PrivateSettingsManagementService(
            self.storage,
            **values,
        )

    async def initialize_settings(self, **values):
        defaults = {"profile_id": "profile-a", "model_id": "model-a", "reasoning_effort": "high"}
        defaults.update(values)
        return await SettingsRepository(self.storage, now_ms=self.clock).initialize_if_absent(**defaults)

    async def test_menu_control_dedupe_runtime_unchanged_and_hash_only_callbacks(self):
        await self.initialize_settings()
        service = self.service()
        result = await service.handle_command(PrivateCommandRequest(10, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateAdminStatus.RENDERED, result.status)
        ingress = await IngressUpdateRepository(self.storage).get(10)
        self.assertEqual(IngressDispositionKind.CONTROL, ingress.disposition)
        self.assertEqual(1, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates WHERE disposition='CONTROL'").fetchone()[0]))
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM controller_runtime").fetchone()[0]))
        rows = await self.storage.read(lambda c: tuple(tuple(row) for row in c.execute("SELECT token_hash_sha256, subject_id, created_at_ms, expires_at_ms FROM callback_actions").fetchall()))
        self.assertEqual(3, len(rows))
        self.assertTrue(all(len(row[0]) == 64 and row[0] == row[0].lower() for row in rows))
        self.assertEqual(1, len({row[2] for row in rows}))
        self.assertEqual({900000}, {row[3] - row[2] for row in rows})
        self.assertNotIn(result.panel.rows[0][0].callback_data[4:], repr(result))

    async def test_duplicate_command_does_not_read_clock_or_create_callbacks(self):
        await self.initialize_settings()
        service = self.service()
        first = await service.handle_command(PrivateCommandRequest(11, 7, 7, PrivateCommand.MENU))
        count = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0])
        self.clock.calls = 0
        duplicate = await service.handle_command(PrivateCommandRequest(11, 7, 7, PrivateCommand.SETTINGS))
        self.assertEqual(PrivateAdminStatus.DUPLICATE, duplicate.status)
        self.assertEqual(0, self.clock.calls)
        self.assertEqual(count, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        self.assertIsNotNone(first.panel)

    async def test_unauthorized_and_unsupported_paths_have_no_content_job_or_callback(self):
        service = self.service()
        unauthorized = await service.handle_command(PrivateCommandRequest(12, 8, 7, PrivateCommand.MENU))
        unsupported = await service.handle_command(PrivateCommandRequest(13, 7, 7, None))
        self.assertEqual(PrivateAdminStatus.UNAUTHORIZED, unauthorized.status)
        self.assertEqual(PrivateAdminStatus.UNSUPPORTED, unsupported.status)
        stored = await IngressUpdateRepository(self.storage).get(12)
        self.assertEqual(IngressDispositionKind.IGNORED_UNAUTHORIZED, stored.disposition)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        self.assertNotIn("PRIVATE", repr(unauthorized) + repr(unsupported))

    async def test_wrong_callback_principal_does_not_consume_token(self):
        await self.initialize_settings()
        result = await self.service().handle_command(PrivateCommandRequest(14, 7, 7, PrivateCommand.MENU))
        token = result.panel.rows[0][0].callback_data[4:]
        wrong = await self.service().handle_callback(PrivateCallbackRequest(15, 8, 7, "q", token))
        right = await self.service().handle_callback(PrivateCallbackRequest(16, 7, 7, "q", token))
        self.assertEqual(PrivateAdminStatus.UNAUTHORIZED, wrong.status)
        self.assertEqual(PrivateAdminStatus.RENDERED, right.status)

    async def test_not_found_expired_and_replay_mapping(self):
        service = self.service()
        not_found = await service.handle_callback(PrivateCallbackRequest(17, 7, 7, "q", "Z" * 32))
        self.assertEqual((PrivateAdminStatus.STALE, PrivateAdminReason.CALLBACK_NOT_FOUND), (not_found.status, not_found.reason))
        await self.initialize_settings()
        root = await service.handle_command(PrivateCommandRequest(18, 7, 7, PrivateCommand.MENU))
        token = root.panel.rows[0][0].callback_data[4:]
        self.clock.value = 900100
        expired = await service.handle_callback(PrivateCallbackRequest(19, 7, 7, "q", token))
        replay = await service.handle_callback(PrivateCallbackRequest(20, 7, 7, "q", token))
        self.assertEqual(PrivateAdminStatus.EXPIRED, expired.status)
        self.assertEqual(PrivateAdminStatus.ALREADY_USED, replay.status)

    async def test_navigation_profile_model_reasoning_and_long_model_fingerprint(self):
        await self.initialize_settings()
        self.catalog.long_model = True
        service = self.service()
        root = await service.handle_command(PrivateCommandRequest(21, 7, 7, PrivateCommand.MENU))
        profiles = await service.handle_callback(PrivateCallbackRequest(22, 7, 7, "q", root.panel.rows[0][0].callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.RENDERED, profiles.status)
        models = await service.handle_callback(PrivateCallbackRequest(23, 7, 7, "q", root.panel.rows[1][0].callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.RENDERED, models.status)
        long_button = models.panel.rows[0][0]
        self.assertNotIn("m" * 256, repr(models.panel))
        subject = await self.storage.read(lambda c: c.execute("SELECT subject_id FROM callback_actions WHERE token_hash_sha256=?", (hashlib.sha256(long_button.callback_data[4:].encode()).hexdigest(),)).fetchone()[0])
        self.assertEqual(64, len(subject))
        self.assertEqual(hashlib.sha256(("m" * 256).encode()).hexdigest(), subject)
        selected = await service.handle_callback(PrivateCallbackRequest(24, 7, 7, "q", long_button.callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.UPDATED, selected.status)
        self.assertEqual("m" * 256, (await SettingsRepository(self.storage).get()).model_id)

    async def test_profile_and_reasoning_selection_use_real_p3_mutations(self):
        await self.initialize_settings()
        service = self.service()
        root = await service.handle_command(PrivateCommandRequest(34, 7, 7, PrivateCommand.MENU))
        profiles = await service.handle_callback(PrivateCallbackRequest(35, 7, 7, "q", root.panel.rows[0][0].callback_data[4:]))
        profile_b = profiles.panel.rows[1][0]
        changed_profile = await service.handle_callback(PrivateCallbackRequest(36, 7, 7, "q", profile_b.callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.UPDATED, changed_profile.status)
        current = await SettingsRepository(self.storage).get()
        self.assertEqual(("profile-b", None, None), (current.profile_id, current.model_id, current.reasoning_effort))

        await SettingsRepository(self.storage, now_ms=self.clock).replace(
            expected_version=current.version, profile_id="profile-b", model_id="model-a", reasoning_effort="high"
        )
        fresh = await service.handle_command(PrivateCommandRequest(37, 7, 7, PrivateCommand.MENU))
        reasoning = await service.handle_callback(PrivateCallbackRequest(38, 7, 7, "q", fresh.panel.rows[2][0].callback_data[4:]))
        low = reasoning.panel.rows[0][0]
        changed_effort = await service.handle_callback(PrivateCallbackRequest(39, 7, 7, "q", low.callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.UPDATED, changed_effort.status)
        self.assertEqual("low", (await SettingsRepository(self.storage).get()).reasoning_effort)

    async def test_stale_version_and_dialogue_state_consume_without_mutation(self):
        await self.initialize_settings()
        service = self.service()
        root = await service.handle_command(PrivateCommandRequest(25, 7, 7, PrivateCommand.MENU))
        await SettingsRepository(self.storage, now_ms=self.clock).replace(expected_version=0, profile_id="profile-a", model_id="model-a", reasoning_effort="low")
        stale = await service.handle_callback(PrivateCallbackRequest(26, 7, 7, "q", root.panel.rows[0][0].callback_data[4:]))
        self.assertEqual((PrivateAdminStatus.STALE, PrivateAdminReason.STALE_ACTION), (stale.status, stale.reason))
        self.assertEqual(1, (await SettingsRepository(self.storage).get()).version)
        fresh = await service.handle_command(PrivateCommandRequest(27, 7, 7, PrivateCommand.MENU))
        await self.storage.write(lambda c: (c.execute("INSERT INTO dialogues(dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms, last_error_class) VALUES ('d',1,'server-80','profile-a','thread','TURN_RUNNING',0,1,1,NULL)"), None)[-1])
        stale_state = await service.handle_callback(PrivateCallbackRequest(28, 7, 7, "q", fresh.panel.rows[0][0].callback_data[4:]))
        self.assertEqual(PrivateAdminStatus.STALE, stale_state.status)
        self.assertEqual(1, (await SettingsRepository(self.storage).get()).version)

    async def test_illegal_selection_buttons_are_not_emitted(self):
        await self.initialize_settings()
        await self.storage.write(lambda c: (c.execute("INSERT INTO dialogues(dialogue_id, live_slot, server_id, profile_id, thread_id, state, version, created_at_ms, updated_at_ms, last_error_class) VALUES ('d',1,'server-80','profile-a','thread','CREATING',0,1,1,NULL)"), None)[-1])
        root = await self.service().handle_command(PrivateCommandRequest(29, 7, 7, PrivateCommand.MENU))
        profiles = await self.service().handle_callback(PrivateCallbackRequest(30, 7, 7, "q", root.panel.rows[0][0].callback_data[4:]))
        self.assertTrue(all(button.label in ("Back", "Previous", "Next") for row in profiles.panel.rows for button in row))

    async def test_callback_batch_collision_is_atomic_and_no_retry(self):
        await self.initialize_settings()
        service = self.service(token_factory=lambda: "Q" * 32)
        with self.assertRaises(PrivateAdminError) as raised:
            await service.handle_command(PrivateCommandRequest(31, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateAdminErrorCategory.INVARIANT, raised.exception.category)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))

    async def test_invalid_token_factory_and_ttl_overflow_fail_closed(self):
        await self.initialize_settings()
        with self.assertRaises(PrivateAdminError) as token_error:
            await self.service(token_factory=lambda: "invalid").handle_command(PrivateCommandRequest(32, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateAdminErrorCategory.INVARIANT, token_error.exception.category)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))
        self.clock.value = 9223372036854775807
        with self.assertRaises(PrivateAdminError) as clock_error:
            await self.service().handle_command(PrivateCommandRequest(33, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateAdminErrorCategory.INVARIANT, clock_error.exception.category)
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM callback_actions").fetchone()[0]))

    async def test_ddl_and_update_adapter_effect_boundary(self):
        self.assertEqual("b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c", SCHEMA_V1_DDL_SHA256)
        normalized = TelegramPrivateUpdateAdapter(7).normalize({"update_id": 1, "message": {"from": {"id": 7, "is_bot": False}, "chat": {"id": 7, "type": "private"}, "text": "/menu"}})
        self.assertEqual(PrivateInboundKind.COMMAND, normalized.kind)
        self.assertIsNone(normalized.callback_token)


if __name__ == "__main__":
    unittest.main()
