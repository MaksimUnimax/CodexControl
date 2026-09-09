import asyncio
import inspect
import os
import tempfile
import unittest
from dataclasses import fields, FrozenInstanceError, is_dataclass

from codex_control.adapters.codex.thread_lifecycle import TrustedWorkingDirectory
from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.application import (
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
    ModelCatalogPort,
    P3_COMPLETED_OUTPUT_RETENTION_MS,
    P3_INPUT_PAYLOAD_RETENTION_MS,
    P3_UNCERTAIN_OUTPUT_RETENTION_MS,
    TurnLifecyclePort,
    WorkingDirectoryResolver,
)
from codex_control.domain import CodexProfile
from codex_control.storage import SqliteStorage


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        raise AssertionError("catalog called")


class _Turns:
    async def start_turn(self, **kwargs):
        raise AssertionError("turn called")

    async def wait_turn(self, binding):
        raise AssertionError("wait called")


class _Workdir:
    def resolve(self, profile_id):
        raise AssertionError("workdir called")


class _ValidCatalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(profile_id, 1, (CodexModelDescriptor("m", "wire", "m", ("high",), "high", True, False),), 0.0, 1.0)


class _ValidWorkdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class ExistingDialogueApplicationUnitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=lambda: 1)

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, **kwargs):
        return ExistingDialogueTurnService(
            self.storage,
            server_id="server",
        profiles=(CodexProfile("profile", "/private/CODEX_HOME", "Profile", "/private/STATE_ROOT"),),
            model_catalog=kwargs.pop("model_catalog", _Catalog()),
            turn_lifecycle=kwargs.pop("turn_lifecycle", _Turns()),
            working_directory_resolver=kwargs.pop("working_directory_resolver", _Workdir()),
            **kwargs,
        )

    def test_exact_enums_and_constants(self):
        self.assertEqual(["COMPLETED", "FAILED", "UNKNOWN", "DUPLICATE", "BUSY", "BLOCKED"], [x.value for x in ExistingDialogueTurnStatus])
        self.assertEqual(
            ["NO_DIALOGUE", "DIALOGUE_NOT_READY", "SETTINGS_MISSING", "SETTINGS_PROFILE_MISMATCH", "PROFILE_NOT_CONFIGURED", "MODEL_NOT_CONFIGURED", "MODEL_UNAVAILABLE", "WORKING_DIRECTORY_UNAVAILABLE", "DUPLICATE_NON_JOB", "DUPLICATE_ORPHAN_JOB", "SETTINGS_CHANGED"],
            [x.value for x in ExistingDialogueTurnReason],
        )
        self.assertEqual(["INVALID_ARGUMENT", "STORAGE", "CODEX", "INVARIANT"], [x.value for x in DialogueApplicationErrorCategory])
        self.assertEqual((3_600_000, 3_600_000, 86_400_000), (P3_INPUT_PAYLOAD_RETENTION_MS, P3_COMPLETED_OUTPUT_RETENTION_MS, P3_UNCERTAIN_OUTPUT_RETENTION_MS))

    def test_exact_frozen_public_records_and_repr_safety(self):
        self.assertTrue(is_dataclass(ExistingDialoguePromptRequest))
        self.assertTrue(is_dataclass(ExistingDialogueTurnResult))
        self.assertEqual(["update_id", "source_chat_id", "source_message_id", "text"], [f.name for f in fields(ExistingDialoguePromptRequest)])
        self.assertEqual(["status", "job", "dialogue", "output_payload", "reason"], [f.name for f in fields(ExistingDialogueTurnResult)])
        self.assertFalse(fields(ExistingDialoguePromptRequest)[3].repr)
        request = ExistingDialoguePromptRequest(1, -2, 3, "PRIVATE_PROMPT_P3_1")
        self.assertNotIn("PRIVATE_PROMPT_P3_1", repr(request))
        with self.assertRaises(FrozenInstanceError):
            request.update_id = 4
        result = ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, None, None, None)
        self.assertNotIn("PRIVATE_OUTPUT_P3_1", repr(result))
        self.assertNotIn("PRIVATE_CODEX_HOME_P3_1", repr(self.service()))

    def test_exact_port_and_service_callable_surfaces(self):
        self.assertEqual({"get_catalog"}, {n for n, v in inspect.getmembers(ModelCatalogPort) if callable(v) and not n.startswith("_")})
        self.assertEqual({"start_turn", "wait_turn"}, {n for n, v in inspect.getmembers(TurnLifecyclePort) if callable(v) and not n.startswith("_")})
        self.assertEqual({"resolve"}, {n for n, v in inspect.getmembers(WorkingDirectoryResolver) if callable(v) and not n.startswith("_")})
        self.assertEqual({"execute"}, {n for n, v in inspect.getmembers(ExistingDialogueTurnService) if callable(v) and not n.startswith("_")})

    def test_request_numeric_boundaries_and_text_matrix(self):
        valid = [(0, -9223372036854775808, 0), (9223372036854775807, 9223372036854775807, 9223372036854775807)]
        for update_id, chat_id, message_id in valid:
            ExistingDialoguePromptRequest(update_id, chat_id, message_id, "x")
        for args in [(True, 1, 1, "x"), (False, 1, 1, "x"), (1.0, 1, 1, "x"), (-1, 1, 1, "x"), (9223372036854775808, 1, 1, "x"), (1, 0, 1, "x"), (1, True, 1, "x"), (1, 1.0, 1, "x"), (1, 1, -1, "x"), (1, 1, 9223372036854775808, "x")]:
            with self.subTest(args=args), self.assertRaises(DialogueApplicationError) as raised:
                ExistingDialoguePromptRequest(*args)
            self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVALID_ARGUMENT)
        ExistingDialoguePromptRequest(1, -1, 1, "a")
        ExistingDialoguePromptRequest(1, -1, 1, "x" * 65536)
        for text in ("", "a\x00b", "x" * 65537, "\ud800"):
            with self.subTest(text=repr(text)), self.assertRaises(DialogueApplicationError):
                ExistingDialoguePromptRequest(1, -1, 1, text)

    def test_error_is_finite_and_redacted(self):
        error = DialogueApplicationError("PRIVATE_ADAPTER_ERROR_P3_1")
        self.assertEqual(DialogueApplicationErrorCategory.INVARIANT, error.category)
        self.assertEqual("INVARIANT", str(error))
        self.assertEqual("DialogueApplicationError('INVARIANT')", repr(error))
        self.assertNotIn("PRIVATE_ADAPTER_ERROR_P3_1", str(error) + repr(error))

    def test_constructor_validation_is_bounded(self):
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(object(), server_id="server", profiles=(), model_catalog=_Catalog(), turn_lifecycle=_Turns(), working_directory_resolver=_Workdir())
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(self.storage, server_id="server", profiles=[], model_catalog=_Catalog(), turn_lifecycle=_Turns(), working_directory_resolver=_Workdir())
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(self.storage, server_id="", profiles=(), model_catalog=_Catalog(), turn_lifecycle=_Turns(), working_directory_resolver=_Workdir())
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(self.storage, server_id="server\x00", profiles=(), model_catalog=_Catalog(), turn_lifecycle=_Turns(), working_directory_resolver=_Workdir())
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(self.storage, server_id="server", profiles=(CodexProfile("p", "/a", "a", "/sa"), CodexProfile("p", "/b", "b", "/sb")), model_catalog=_Catalog(), turn_lifecycle=_Turns(), working_directory_resolver=_Workdir())

    def test_output_bound_arithmetic(self):
        self.assertEqual(8_000_510, 2_000_000 * 4 + 255 * 2)
        self.assertLess(8_000_510, 8_388_608)

    async def test_static_validation_happens_before_storage(self):
        with self.assertRaises(DialogueApplicationError):
            await self.service().execute(object())
        self.assertIsNone(await __import__("codex_control.storage", fromlist=["IngressUpdateRepository"]).IngressUpdateRepository(self.storage).get(1))

    async def test_no_dialogue_is_blocked_without_effect(self):
        result = await self.service(now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock"))).execute(ExistingDialoguePromptRequest(1, -10, 2, "x"))
        self.assertEqual((ExistingDialogueTurnStatus.BLOCKED, ExistingDialogueTurnReason.NO_DIALOGUE), (result.status, result.reason))

    async def test_invalid_id_factory_and_clock_are_finite(self):
        from codex_control.storage import DialogueRepository, SettingsRepository
        await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(dialogue_id="d", server_id="server", profile_id="profile")
        await DialogueRepository(self.storage, now_ms=lambda: 1).confirm_created(dialogue_id="d", expected_version=0, thread_id="t")
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(profile_id="profile", model_id="m", reasoning_effort="high")
        for value in ("", "x\x00", "x" * 129, 1):
            with self.subTest(value=repr(value)), self.assertRaises(DialogueApplicationError) as raised:
                await self.service(model_catalog=_ValidCatalog(), working_directory_resolver=_ValidWorkdir(), id_factory=lambda kind, value=value: value, now_ms=lambda: 1).execute(ExistingDialoguePromptRequest(10, -1, 1, "x"))
            self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVARIANT)
        for clock in (lambda: True, lambda: False, lambda: -1, lambda: 9223372036854775808, lambda: 1.5, lambda: (_ for _ in ()).throw(RuntimeError("PRIVATE_P3_CLOCK"))):
            with self.subTest(clock=clock), self.assertRaises(DialogueApplicationError) as raised:
                await self.service(model_catalog=_ValidCatalog(), working_directory_resolver=_ValidWorkdir(), now_ms=clock).execute(ExistingDialoguePromptRequest(20 + id(clock) % 100, -1, 1, "x"))
            self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.STORAGE)
            self.assertNotIn("PRIVATE_P3_CLOCK", repr(raised.exception))

    async def test_generated_input_id_validation_is_independent_of_job_id(self):
        from codex_control.storage import DialogueRepository, IngressUpdateRepository, SettingsRepository

        await DialogueRepository(self.storage, now_ms=lambda: 1).create_intent(
            dialogue_id="d", server_id="server", profile_id="profile"
        )
        await DialogueRepository(self.storage, now_ms=lambda: 1).confirm_created(
            dialogue_id="d", expected_version=0, thread_id="t"
        )
        await SettingsRepository(self.storage, now_ms=lambda: 1).initialize_if_absent(
            profile_id="profile", model_id="m", reasoning_effort="high"
        )
        invalid_inputs = ("", "input\x00id", "i" * 129, 42)
        for offset, invalid_input in enumerate(invalid_inputs):
            calls = []

            def ids(kind, *, invalid_input=invalid_input, offset=offset):
                calls.append(kind)
                return f"job-{offset}" if kind == "job" else invalid_input

            with self.subTest(invalid_input=repr(invalid_input)), self.assertRaises(DialogueApplicationError) as raised:
                await self.service(
                    model_catalog=_ValidCatalog(),
                    working_directory_resolver=_ValidWorkdir(),
                    id_factory=ids,
                ).execute(ExistingDialoguePromptRequest(30 + offset, -1, 1, "x"))
            self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVARIANT)
            self.assertEqual(["job", "input"], calls)
            self.assertIsNone(await IngressUpdateRepository(self.storage).get(30 + offset))
            self.assertEqual(0, await self.storage.read(
                lambda connection: connection.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]
            ))


if __name__ == "__main__":
    unittest.main()
