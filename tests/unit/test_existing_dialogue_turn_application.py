import asyncio
import inspect
import os
import tempfile
import unittest
from dataclasses import fields, is_dataclass

from codex_control.application import (
    DialogueApplicationError,
    DialogueApplicationErrorCategory,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnReason,
    ExistingDialogueTurnResult,
    ExistingDialogueTurnService,
    ExistingDialogueTurnStatus,
    ModelCatalogPort,
    TurnLifecyclePort,
    WorkingDirectoryResolver,
)
from codex_control.domain import CodexProfile
from codex_control.storage import SqliteStorage


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        raise AssertionError("catalog must not be called")


class _Turns:
    async def start_turn(self, **kwargs):
        raise AssertionError("turn must not be called")

    async def wait_turn(self, binding):
        raise AssertionError("turn must not be called")


class _Workdir:
    def resolve(self, profile_id):
        raise AssertionError("working directory must not be called")


class ExistingDialogueApplicationUnitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "state.sqlite3")
        self.storage = await SqliteStorage.open(self.path, now_ms=lambda: 1)

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    def service(self, **kwargs):
        return ExistingDialogueTurnService(
            self.storage,
            server_id="server",
            profiles=(CodexProfile("profile", "/private/home", "Profile"),),
            model_catalog=kwargs.pop("model_catalog", _Catalog()),
            turn_lifecycle=kwargs.pop("turn_lifecycle", _Turns()),
            working_directory_resolver=kwargs.pop("working_directory_resolver", _Workdir()),
            **kwargs,
        )

    async def test_public_contract_is_exact_and_frozen(self):
        self.assertEqual(
            ["COMPLETED", "FAILED", "UNKNOWN", "DUPLICATE", "BUSY", "BLOCKED"],
            [item.value for item in ExistingDialogueTurnStatus],
        )
        self.assertEqual(
            [
                "NO_DIALOGUE", "DIALOGUE_NOT_READY", "SETTINGS_MISSING",
                "SETTINGS_PROFILE_MISMATCH", "PROFILE_NOT_CONFIGURED", "MODEL_NOT_CONFIGURED",
                "MODEL_UNAVAILABLE", "WORKING_DIRECTORY_UNAVAILABLE", "DUPLICATE_NON_JOB",
                "DUPLICATE_ORPHAN_JOB",
            ],
            [item.value for item in ExistingDialogueTurnReason],
        )
        self.assertEqual(
            ["INVALID_ARGUMENT", "STORAGE", "CODEX", "INVARIANT"],
            [item.value for item in DialogueApplicationErrorCategory],
        )
        self.assertTrue(is_dataclass(ExistingDialoguePromptRequest))
        self.assertTrue(is_dataclass(ExistingDialogueTurnResult))
        self.assertEqual(
            ["update_id", "source_chat_id", "source_message_id", "text"],
            [item.name for item in fields(ExistingDialoguePromptRequest)],
        )
        self.assertEqual(
            ["status", "job", "dialogue", "output_payload", "reason"],
            [item.name for item in fields(ExistingDialogueTurnResult)],
        )
        self.assertTrue(fields(ExistingDialoguePromptRequest)[-1].repr is False)

    async def test_request_static_validation_rejects_without_storage(self):
        cases = [
            (True, -1, 1, "x"), (0, 0, 1, "x"),
            (0, 1, True, "x"), (0, 1, 1, ""), (0, 1, 1, "a\x00b"),
            (0, 1, 1, "x" * 65537), (0, 1, 1, "\ud800"),
        ]
        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises(DialogueApplicationError) as raised:
                    ExistingDialoguePromptRequest(*values)
                self.assertIs(raised.exception.category, DialogueApplicationErrorCategory.INVALID_ARGUMENT)

    async def test_request_boundaries_and_repr(self):
        request = ExistingDialoguePromptRequest(
            9223372036854775807, -9223372036854775808, 9223372036854775807, "PRIVATE_PROMPT_P3_1"
        )
        self.assertNotIn("PRIVATE_PROMPT_P3_1", repr(request))
        with self.assertRaises(DialogueApplicationError):
            ExistingDialoguePromptRequest(9223372036854775808, -1, 1, "x")

    async def test_error_is_finite_and_redacted(self):
        error = DialogueApplicationError("PRIVATE_ADAPTER_ERROR_P3_1")
        self.assertIs(error.category, DialogueApplicationErrorCategory.INVARIANT)
        self.assertEqual("INVARIANT", str(error))
        self.assertEqual("DialogueApplicationError('INVARIANT')", repr(error))
        self.assertNotIn("PRIVATE_ADAPTER_ERROR_P3_1", str(error) + repr(error))

    async def test_constructor_rejects_invalid_dependencies_without_filesystem_access(self):
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(
                object(), server_id="server", profiles=(), model_catalog=_Catalog(),
                turn_lifecycle=_Turns(), working_directory_resolver=_Workdir()
            )
        with self.assertRaises(DialogueApplicationError):
            ExistingDialogueTurnService(
                self.storage, server_id="server", profiles=[], model_catalog=_Catalog(),
                turn_lifecycle=_Turns(), working_directory_resolver=_Workdir()
            )

    async def test_no_dialogue_is_blocked_without_effect(self):
        service = self.service()
        result = await service.execute(ExistingDialoguePromptRequest(1, -100, 2, "prompt"))
        self.assertEqual(ExistingDialogueTurnStatus.BLOCKED, result.status)
        self.assertEqual(ExistingDialogueTurnReason.NO_DIALOGUE, result.reason)
        self.assertIsNone(result.job)

    async def test_service_and_result_repr_are_content_safe(self):
        service = self.service()
        self.assertNotIn("PRIVATE_CODEX_HOME_P3_1", repr(service))
        self.assertNotIn("PRIVATE_OUTPUT_P3_1", repr(service))
        result = ExistingDialogueTurnResult(ExistingDialogueTurnStatus.BLOCKED, None, None, None, None)
        self.assertNotIn("PRIVATE_PROMPT_P3_1", repr(result))

    async def test_port_surfaces_and_service_callable_surface(self):
        self.assertEqual({"get_catalog"}, {name for name, value in inspect.getmembers(ModelCatalogPort) if callable(value) and not name.startswith("_")})
        self.assertEqual({"start_turn", "wait_turn"}, {name for name, value in inspect.getmembers(TurnLifecyclePort) if callable(value) and not name.startswith("_")})
        self.assertEqual({"resolve"}, {name for name, value in inspect.getmembers(WorkingDirectoryResolver) if callable(value) and not name.startswith("_")})
        public = {name for name, value in inspect.getmembers(ExistingDialogueTurnService) if callable(value) and not name.startswith("_")}
        self.assertEqual({"execute"}, public)

    async def test_duplicate_non_job_is_first_and_needs_no_configuration(self):
        from codex_control.storage import IngressDispositionKind, IngressUpdateRepository
        await IngressUpdateRepository(self.storage, now_ms=lambda: 10).claim_ignored(
            update_id=9, disposition=IngressDispositionKind.IGNORED_SLEEP
        )
        service = self.service(
            now_ms=lambda: (_ for _ in ()).throw(AssertionError("clock")),
            id_factory=lambda kind: (_ for _ in ()).throw(AssertionError("id")),
        )
        result = await service.execute(ExistingDialoguePromptRequest(9, -100, 2, "PRIVATE_PROMPT_P3_1"))
        self.assertEqual(ExistingDialogueTurnStatus.DUPLICATE, result.status)
        self.assertEqual(ExistingDialogueTurnReason.DUPLICATE_NON_JOB, result.reason)
