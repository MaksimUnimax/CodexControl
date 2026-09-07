import asyncio
import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.codex.model_catalog import CodexModelCatalog, CodexModelDescriptor
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadOperationResult,
    ThreadOperationStatus,
    TrustedWorkingDirectory,
)
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnStartResult,
    TurnStartStatus,
    TurnTerminalResult,
    TurnTerminalStatus,
)
from codex_control.application import (
    ActiveTurnRegistry,
    DialogueDeleteRequest,
    DialogueDeleteService,
    DialogueDeleteRequest,
    DialogueDeleteStatus,
    DialogueInterruptService,
    DialogueRecoveryService,
    DialogueRecoveryStatus,
    DialogueTurnService,
    ExistingDialoguePromptRequest,
    ExistingDialogueTurnStatus,
    SettingsMutationStatus,
    SettingsSelectionService,
)
from codex_control.domain import CodexProfile
from codex_control.storage import (
    DialogueRepository,
    DialogueState,
    SettingsRepository,
    SqliteStorage,
    TurnJobRepository,
    TurnJobState,
)


class _Catalog:
    async def get_catalog(self, profile_id, *, refresh=False):
        return CodexModelCatalog(
            profile_id, 1,
            (CodexModelDescriptor("model", "wire-model", "Model", ("low", "high"), "high", True, False),),
            0.0, 100.0,
        )


class _Workdir:
    def resolve(self, profile_id):
        return TrustedWorkingDirectory("/trusted")


class _Thread:
    async def start(self, profile_id, *, model_id, reasoning_effort, working_directory):
        return ThreadOperationResult(
            ThreadOperationStatus.START_CONFIRMED,
            ThreadBinding(profile_id, "thread-one"),
            model_id=model_id,
            reasoning_effort=reasoning_effort,
        )


class _FakeP3Lifecycle:
    def __init__(self):
        self.turn_binding = None
        self.start_calls = []
        self.wait_calls = []
        self.interrupt_calls = []
        self.wait_entered = asyncio.Event()
        self.collector_ready = asyncio.Event()
        self.collector_ready.set()

    async def start_turn(self, **kwargs):
        self.start_calls.append(kwargs)
        self.turn_binding = TurnBinding("profile-a", "thread-one", f"turn-{len(self.start_calls)}")
        if len(self.start_calls) > 1:
            self.collector_ready.clear()
        return TurnStartResult(TurnStartStatus.CONFIRMED, self.turn_binding)

    async def wait_turn(self, binding):
        self.wait_calls.append(binding)
        self.wait_entered.set()
        await self.collector_ready.wait()
        return TurnTerminalResult(
            binding,
            TurnTerminalStatus.FAILED if binding.turn_id == "turn-2" else TurnTerminalStatus.COMPLETED,
            (AgentMessageCompleted(1, "item", "fake output"),),
        )

    async def interrupt_turn(self, binding):
        self.interrupt_calls.append(binding)
        self.collector_ready.set()
        return TurnInterruptResult(
            TurnInterruptStatus.CONFIRMED,
            binding,
            TurnTerminalResult(binding, TurnTerminalStatus.FAILED, ()),
        )


class _FakeDelete:
    def __init__(self):
        self.calls = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def delete(self, *, binding):
        self.calls.append(binding)
        self.entered.set()
        await self.release.wait()
        return ThreadOperationResult(ThreadOperationStatus.DELETE_CONFIRMED, binding)


class FinalP3FakeApplicationAcceptance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = await SqliteStorage.open(
            os.path.join(self.tempdir.name, "controller.sqlite3"), now_ms=lambda: 1
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    async def test_final_fake_p3_matrix(self):
        settings = SettingsRepository(self.storage, now_ms=lambda: 1)
        initialized = await settings.initialize_if_absent(
            profile_id="profile-a", model_id="model", reasoning_effort="high"
        )
        self.assertTrue(initialized.created)
        registry = ActiveTurnRegistry()
        catalog = _Catalog()
        lifecycle = _FakeP3Lifecycle()
        turns = DialogueTurnService(
            self.storage, server_id="server",
            profiles=(
                CodexProfile("profile-a", "/fake/a", "A"),
                CodexProfile("profile-b", "/fake/b", "B"),
            ),
            model_catalog=catalog, thread_lifecycle=_Thread(), turn_lifecycle=lifecycle,
            working_directory_resolver=_Workdir(), now_ms=lambda: 10,
            active_turn_registry=registry,
        )

        first = await turns.execute(ExistingDialoguePromptRequest(1, -1, 1, "first"))
        self.assertEqual(ExistingDialogueTurnStatus.COMPLETED, first.status)
        dialogue = await DialogueRepository(self.storage).get_live()
        self.assertEqual((DialogueState.IDLE, "thread-one"), (dialogue.state, dialogue.thread_id))
        self.assertEqual(1, len(lifecycle.start_calls))
        self.assertEqual({}, registry._entries)
        self.assertNotIn("_retired", vars(registry))
        # Keep the fake acceptance deletion-ready under the accepted P2.5
        # rule: this completed job is projected to a terminal failed path
        # with no delivery-owned segments.
        def make_first_terminal_failed(connection):
            connection.execute(
                "UPDATE turn_jobs SET state = 'FAILED', error_class = 'CODEX_TURN_FAILED' "
                "WHERE state = 'CODEX_COMPLETED'"
            )
        await self.storage.write(make_first_terminal_failed)
        first_job_id = await self.storage.read(
            lambda c: c.execute("SELECT job_id FROM turn_jobs WHERE state = 'FAILED'").fetchone()[0]
        )
        display_sha = hashlib.sha256(b"display").hexdigest()
        def add_retained_owned_rows(connection):
            for payload_id in ("display-1", "display-2"):
                connection.execute(
                    "INSERT INTO transient_payloads VALUES (?, ?, ?, 'DISPLAY', ?, ?, 7, 1, 1000)",
                    (payload_id, dialogue.dialogue_id, first_job_id, b"display", display_sha),
                )
            connection.execute(
                "INSERT INTO delivery_segments VALUES (?, 1, 'CREATE', NULL, 'display-1', ?, 'CONFIRMED', 1, 10, 1, 1)",
                (first_job_id, display_sha),
            )
            connection.execute(
                "INSERT INTO delivery_segments VALUES (?, 2, 'CREATE', NULL, 'display-2', ?, 'FAILED', 1, NULL, 1, 1)",
                (first_job_id, display_sha),
            )
            connection.execute(
                "INSERT INTO approvals VALUES ('approval-1', 'profile-a', 'INTEGER', 7, NULL, ?, 'exec_command', NULL, 'APPROVED', 1, 1, 1000)",
                (first_job_id,),
            )
            connection.execute(
                "INSERT INTO callback_actions VALUES (?, 'approval_allow', 'approval', 'approval-1', 1, 'PENDING', 1, -1, 1, 1000, 10)",
                ("b" * 64,),
            )
            connection.execute(
                "INSERT INTO errors VALUES (?, 'CODEX_TURN_FAILED', 1, 1, 1, ?, ?)",
                ("a" * 64, dialogue.dialogue_id, first_job_id),
            )
        await self.storage.write(add_retained_owned_rows)

        lifecycle.wait_entered.clear()
        second_task = asyncio.create_task(
            turns.execute(ExistingDialoguePromptRequest(2, -1, 2, "second"))
        )
        await lifecycle.wait_entered.wait()
        running = await DialogueRepository(self.storage).get_live()
        running_job = await TurnJobRepository(self.storage).get(
            (await self.storage.read(lambda c: c.execute(
                "SELECT job_id FROM turn_jobs WHERE state = 'CODEX_RUNNING'"
            ).fetchone()[0]))
        )
        self.assertEqual(DialogueState.TURN_RUNNING, running.state)
        self.assertIs(registry.lookup(running_job.job_id), lifecycle.turn_binding)
        self.assertEqual("thread-one", running_job.thread_id)

        settings_service = SettingsSelectionService(
            self.storage, server_id="server",
            profiles=(CodexProfile("profile-a", "/fake/a", "A"), CodexProfile("profile-b", "/fake/b", "B")),
            model_catalog=catalog, now_ms=lambda: 20,
        )
        blocked_settings = await settings_service.select_reasoning_effort(
            "low", expected_version=(await settings.get()).version
        )
        self.assertEqual(SettingsMutationStatus.BLOCKED, blocked_settings.status)
        busy = await turns.execute(ExistingDialoguePromptRequest(3, -1, 3, "queued-never"))
        self.assertEqual(ExistingDialogueTurnStatus.BUSY, busy.status)
        self.assertEqual(2, len(lifecycle.start_calls))

        interrupt = DialogueInterruptService(
            self.storage, server_id="server", active_turn_registry=registry,
            turn_lifecycle=lifecycle, now_ms=lambda: 30,
        )
        fake_delete = _FakeDelete()
        delete = DialogueDeleteService(
            self.storage, server_id="server", thread_lifecycle=fake_delete,
            interrupt_service=interrupt, active_turn_registry=registry, now_ms=lambda: 40,
        )
        delete_task = asyncio.create_task(
            delete.delete(DialogueDeleteRequest(running.dialogue_id, running.version))
        )
        await fake_delete.entered.wait()
        deleting = await DialogueRepository(self.storage).get_live()
        self.assertEqual(DialogueState.DELETING, deleting.state)
        self.assertEqual(1, len(lifecycle.interrupt_calls))
        self.assertEqual(1, len(fake_delete.calls))
        self.assertIsNone(registry.lookup(running_job.job_id))
        blocked_delete_prompt = await turns.execute(ExistingDialoguePromptRequest(4, -1, 4, "not-admitted"))
        self.assertEqual(ExistingDialogueTurnStatus.BLOCKED, blocked_delete_prompt.status)
        fake_delete.release.set()
        deleted = await delete_task
        self.assertEqual(DialogueDeleteStatus.DELETED, deleted.status)
        counts = await self.storage.read(lambda c: tuple(
            c.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            for table in ("dialogues", "turn_jobs", "transient_payloads", "delivery_segments", "approvals", "deletion_tombstones")
        ))
        self.assertEqual((0, 0, 0, 0, 0, 1), counts)
        self.assertNotIn("thread-one", repr(deleted.tombstone))
        self.assertGreaterEqual(
            await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM ingress_updates").fetchone()[0]),
            2,
        )
        runner_result = await second_task
        self.assertEqual("FAILED", runner_result.status.value)
        self.assertEqual("CODEX_TURN_FAILED", runner_result.job.error_class)
        self.assertEqual({}, registry._entries)
        self.assertNotIn("_retired", vars(registry))

        replay = await delete.delete(DialogueDeleteRequest(running.dialogue_id, running.version))
        self.assertEqual(DialogueDeleteStatus.DELETED, replay.status)
        self.assertEqual(1, len(fake_delete.calls))

        current_settings = await settings.get()
        changed = await settings_service.select_profile("profile-b", expected_version=current_settings.version)
        self.assertEqual(SettingsMutationStatus.UPDATED, changed.status)
        self.assertEqual("profile-b", changed.settings.profile_id)
        recovery = DialogueRecoveryService(self.storage, now_ms=lambda: 50)
        self.assertEqual(DialogueRecoveryStatus.NO_ACTION, (await recovery.recover_startup()).status)


if __name__ == "__main__":
    unittest.main()
