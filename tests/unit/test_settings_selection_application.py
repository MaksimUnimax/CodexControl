import inspect
import tempfile
import unittest
from dataclasses import FrozenInstanceError, fields, is_dataclass

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.application import (
    SettingsModelOption,
    SettingsMutationReason,
    SettingsMutationResult,
    SettingsMutationStatus,
    SettingsProfileOption,
    SettingsSelectionError,
    SettingsSelectionErrorCategory,
    SettingsSelectionService,
    SettingsSelectionView,
)
from codex_control.domain import CodexProfile
from codex_control.storage import SettingsRepository, SqliteStorage


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (CodexModelDescriptor("model", "PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", "Model", ("high",), "high", True, False),),
            0.0, 1.0,
        )


class SettingsSelectionApplicationUnitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(self.tempdir.name + "/controller.sqlite3", now_ms=lambda: 1)

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, **kwargs):
        return SettingsSelectionService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/PRIVATE/CODEX_HOME/MUST_NOT_LEAK", "Profile"),),
            model_catalog=_Catalog(),
            **kwargs,
        )

    def test_exact_public_surface_enums_and_records(self):
        self.assertEqual(
            {"get_view", "select_profile", "select_model", "select_reasoning_effort"},
            {name for name, value in inspect.getmembers(SettingsSelectionService) if callable(value) and not name.startswith("_")},
        )
        self.assertEqual(["UPDATED", "NO_CHANGE", "BLOCKED", "CONFLICT"], [x.value for x in SettingsMutationStatus])
        self.assertEqual(
            ["SETTINGS_MISSING", "PROFILE_NOT_CONFIGURED", "PROFILE_LOCKED", "DIALOGUE_NOT_IDLE", "MODEL_NOT_CONFIGURED", "MODEL_UNAVAILABLE", "REASONING_EFFORT_UNSUPPORTED", "STALE_SETTINGS"],
            [x.value for x in SettingsMutationReason],
        )
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "INVARIANT"], [x.value for x in SettingsSelectionErrorCategory])
        expected = {
            SettingsProfileOption: ["profile_id", "display_name"],
            SettingsModelOption: ["model_id", "display_name", "supported_reasoning_efforts", "default_reasoning_effort", "is_default"],
            SettingsSelectionView: ["settings", "dialogue_state", "dialogue_profile_id", "profiles", "models", "catalog_available"],
            SettingsMutationResult: ["status", "settings", "reason"],
        }
        for record, names in expected.items():
            self.assertTrue(is_dataclass(record))
            self.assertTrue(record.__dataclass_params__.frozen)
            self.assertEqual(names, [field.name for field in fields(record)])

    async def test_static_validation_and_payload_free_errors(self):
        for value in (None, "", "bad\x00value", 1, True, "x" * 129):
            with self.subTest(value=repr(value)), self.assertRaises(SettingsSelectionError) as raised:
                SettingsSelectionService(
                    self.storage, server_id=value, profiles=(), model_catalog=_Catalog()
                )
            self.assertEqual(SettingsSelectionErrorCategory.INVALID_ARGUMENT, raised.exception.category)
            self.assertNotIn("PRIVATE_CATALOG_ERROR_MUST_NOT_LEAK", repr(raised.exception))
        with self.assertRaises(SettingsSelectionError):
            await self.service().get_view(refresh=1)
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        for expected_version in (True, -1, 2**63, 1.0, "1"):
            with self.subTest(expected_version=repr(expected_version)), self.assertRaises(SettingsSelectionError):
                await self.service().select_profile("profile", expected_version=expected_version)

    async def test_public_projection_and_redaction(self):
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="model", reasoning_effort="high"
        )
        view = await self.service().get_view()
        profile_option = view.profiles[0]
        model_option = view.models[0]
        self.assertEqual((SettingsProfileOption("profile", "Profile"),), view.profiles)
        self.assertEqual(("model",), tuple(option.model_id for option in view.models))
        self.assertNotIn("/PRIVATE/CODEX_HOME/MUST_NOT_LEAK", repr(profile_option))
        self.assertNotIn("PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", repr(model_option))
        self.assertNotIn("/PRIVATE/CODEX_HOME/MUST_NOT_LEAK", repr(view))
        self.assertNotIn("PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", repr(view))
        self.assertNotIn("thread_id", repr(view))
        self.assertNotIn("PRIVATE_CATALOG_ERROR_MUST_NOT_LEAK", repr(view))
        mutation = SettingsMutationResult(SettingsMutationStatus.NO_CHANGE, view.settings, None)
        self.assertNotIn("/PRIVATE/CODEX_HOME/MUST_NOT_LEAK", repr(mutation))
        self.assertNotIn("PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", repr(mutation))
        with self.assertRaises(FrozenInstanceError):
            view.models = ()

    def test_public_error_constructor_and_individual_record_redaction(self):
        error = SettingsSelectionError("PRIVATE_SETTINGS_ERROR_MUST_NOT_LEAK")
        self.assertEqual(SettingsSelectionErrorCategory.INVARIANT, error.category)
        self.assertNotIn("PRIVATE_SETTINGS_ERROR_MUST_NOT_LEAK", str(error) + repr(error))
        profile_option = SettingsProfileOption("profile", "Profile")
        model_option = SettingsModelOption("model", "Model", ("high",), "high", True)
        view = SettingsSelectionView(None, None, None, (profile_option,), (model_option,), True)
        mutation = SettingsMutationResult(SettingsMutationStatus.BLOCKED, None, SettingsMutationReason.SETTINGS_MISSING)
        for record in (profile_option, model_option, view, mutation):
            with self.subTest(record=type(record).__name__):
                self.assertNotIn("/PRIVATE/CODEX_HOME/MUST_NOT_LEAK", repr(record))
                self.assertNotIn("PRIVATE_WIRE_MODEL_MUST_NOT_LEAK", repr(record))
                self.assertNotIn("PRIVATE_SETTINGS_ERROR_MUST_NOT_LEAK", repr(record))

    async def test_mutation_contract_when_settings_are_missing(self):
        service = self.service()
        for operation, argument in (
            (service.select_profile, "profile"),
            (service.select_model, "model"),
            (service.select_reasoning_effort, "high"),
        ):
            result = await operation(argument, expected_version=0)
            self.assertEqual(SettingsMutationStatus.BLOCKED, result.status)
            self.assertEqual(SettingsMutationReason.SETTINGS_MISSING, result.reason)
            self.assertIsNone(result.settings)


if __name__ == "__main__":
    unittest.main()
