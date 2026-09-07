import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.telegram import PrivateCommand, PrivateInboundKind, TelegramPrivateUpdateAdapter
from codex_control.application import (
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlStatus,
    PrivateApprovalProjectionRequest,
)
from codex_control.storage import (
    ApprovalKind,
    ApprovalRepository,
    ApprovalState,
    ControllerRuntimeRepository,
    DialogueRepository,
    ErrorFingerprintRepository,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnJobState,
)

from tests.integration.test_private_control import Catalog


class RecordingEffects:
    def __init__(self):
        self.interrupt_calls = []
        self.delete_calls = []

    async def interrupt(self, request):
        self.interrupt_calls.append(request)
        raise AssertionError("real interrupt effect is forbidden in P4 acceptance")

    async def delete(self, request):
        self.delete_calls.append(request)
        raise AssertionError("real delete effect is forbidden in P4 acceptance")


class FinalFakeP4AcceptanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.now = 100
        self.clock = lambda: self.now
        from codex_control.storage import SettingsRepository, SqliteStorage
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=self.clock)
        await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet")
        await SettingsRepository(self.storage, now_ms=self.clock).initialize_if_absent(
            profile_id="profile-a", model_id="model-a", reasoning_effort="high"
        )
        self.number = 0
        self.effects = RecordingEffects()
        self.adapter = TelegramPrivateUpdateAdapter(7)

        def token_factory():
            self.number += 1
            return f"{self.number:032d}"

        from codex_control.application import PrivateControlService
        from codex_control.domain import CodexProfile
        self.service = PrivateControlService(
            self.storage, server_id="server-80", server_display_name="Server 80", operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A"),),
            model_catalog=Catalog(), interrupt_service=self.effects, delete_service=self.effects,
            now_ms=self.clock, token_factory=token_factory,
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    @staticmethod
    def token(panel, label):
        return next(button.callback_data[4:] for row in panel.rows for button in row if button.label == label)

    async def test_final_private_management_composition_fake(self):
        before_menu = await ControllerRuntimeRepository(self.storage).get()
        inbound = self.adapter.normalize({
            "update_id": 200,
            "message": {"from": {"id": 7, "is_bot": False}, "chat": {"id": 7, "type": "private"}, "text": "/menu"},
        })
        self.assertIs(PrivateInboundKind.COMMAND, inbound.kind)
        self.assertIs(PrivateCommand.MENU, inbound.command)
        root = await self.service.handle_command(PrivateCommandRequest(inbound.update_id, inbound.user_id, inbound.chat_id, inbound.command))
        self.assertEqual(PrivateControlStatus.RENDERED, root.status)
        self.assertEqual(before_menu, await ControllerRuntimeRepository(self.storage).get())
        self.assertEqual(0, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM turn_jobs").fetchone()[0]))

        settings_token = self.token(root.panel, "Settings")
        settings_row = await self.storage.read(lambda c, h=hashlib.sha256(settings_token.encode()).hexdigest(): tuple(c.execute(
            "SELECT action, subject_type, subject_id, expected_version, expected_state, consumed_at_ms "
            "FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()))
        self.assertEqual(("OPEN_ROOT", "panel", "0", 0, "NO_DIALOGUE", None), settings_row)
        settings = await self.service.handle_callback(PrivateCallbackRequest(201, 7, 7, "settings", settings_token))
        self.assertEqual(PrivateControlStatus.RENDERED, settings.status)
        model_token = self.token(settings.panel, "Models")
        models = await self.service.handle_callback(PrivateCallbackRequest(202, 7, 7, "models", model_token))
        selected = self.token(models.panel, "Model A")
        unchanged = await self.service.handle_callback(PrivateCallbackRequest(203, 7, 7, "model", selected))
        self.assertEqual(PrivateControlStatus.NO_CHANGE, unchanged.status)

        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).create_intent(
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a"
        )
        await DialogueRepository(self.storage, now_ms=self.clock).confirm_created(
            dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id="fake-thread"
        )
        root = await self.service.handle_command(PrivateCommandRequest(204, 7, 7, PrivateCommand.MENU))
        dialogue_token = self.token(root.panel, "Dialogue")
        status = await self.service.handle_callback(PrivateCallbackRequest(205, 7, 7, "dialogue", dialogue_token))
        self.assertEqual(PrivateControlStatus.RENDERED, status.status)

        jobs = TurnJobRepository(self.storage, now_ms=self.clock)
        admitted = await jobs.claim_ingress(
            update_id=206, job_id="job", source_chat_id=-7, source_message_id=1,
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a",
            thread_id="fake-thread", model_id="model-a", reasoning_effort="high",
            input_payload_id="input", input_content=b"fake input", input_expires_at_ms=10000,
        )
        current_dialogue = await DialogueRepository(self.storage).get_live()
        claimed = await jobs.claim_turn(
            job_id="job", expected_job_version=admitted.job.version,
            expected_dialogue_version=current_dialogue.version, thread_id="fake-thread",
        )
        starting = await jobs.mark_codex_starting(job_id="job", expected_version=claimed.job.version)
        running = await jobs.mark_codex_running(job_id="job", expected_version=starting.version, codex_turn_id="fake-turn")
        payload = await TransientPayloadRepository(self.storage, now_ms=self.clock).create(
            payload_id="approval-display", dialogue_id="dialogue", job_id="job",
            kind=TransientPayloadKind.APPROVAL, content=b"fake privileged command", expires_at_ms=10000,
        )
        await ApprovalRepository(self.storage, now_ms=self.clock).create_pending(
            approval_id="approval", profile_id="profile-a", wire_request_id="wire",
            kind=ApprovalKind.COMMAND_EXECUTION, job_id="job", expected_job_version=running.version,
            display_payload_id=payload.payload_id, expires_at_ms=10000,
        )
        fingerprint = "e" * 64
        await ErrorFingerprintRepository(self.storage, now_ms=self.clock).record(
            fingerprint_sha256=fingerprint, error_class="CODEX_PROCESS", dialogue_id="dialogue", job_id="job"
        )
        root = await self.service.handle_command(PrivateCommandRequest(207, 7, 7, PrivateCommand.MENU))
        dialogue_token = self.token(root.panel, "Dialogue")
        running_status = await self.service.handle_callback(PrivateCallbackRequest(208, 7, 7, "running-dialogue", dialogue_token))
        delete_token = self.token(running_status.panel, "Delete")
        confirmation = await self.service.handle_callback(PrivateCallbackRequest(209, 7, 7, "delete", delete_token))
        self.assertEqual(PrivateControlStatus.CONFIRM_REQUIRED, confirmation.status)
        self.assertIn("CONFIRM DELETE", [button.label for row in confirmation.panel.rows for button in row])
        cancel = self.token(confirmation.panel, "Cancel")
        cancelled = await self.service.handle_callback(PrivateCallbackRequest(210, 7, 7, "cancel", cancel))
        self.assertEqual(PrivateControlStatus.RENDERED, cancelled.status)
        self.assertEqual([], self.effects.interrupt_calls)
        self.assertEqual([], self.effects.delete_calls)

        root = await self.service.handle_command(PrivateCommandRequest(211, 7, 7, PrivateCommand.MENU))
        diagnostics = await self.service.handle_callback(PrivateCallbackRequest(212, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertEqual(PrivateControlStatus.RENDERED, diagnostics.status)
        self.assertIn("CODEX_PROCESS", diagnostics.panel.text)
        self.assertIn("count 1", diagnostics.panel.text)
        self.assertIn("scope dialogue+job", diagnostics.panel.text)
        self.assertNotIn(fingerprint, diagnostics.panel.text)
        self.assertNotIn("dialogue", diagnostics.panel.text.replace("scope dialogue+job", ""))
        self.assertNotIn("job", diagnostics.panel.text.replace("scope dialogue+job", ""))
        self.assertNotIn("fake-thread", diagnostics.panel.text)
        self.assertNotIn("fake-turn", diagnostics.panel.text)
        self.assertNotIn("/synthetic/profile-a", diagnostics.panel.text)

        root = await self.service.handle_command(PrivateCommandRequest(213, 7, 7, PrivateCommand.MENU))
        approval_token = self.token(root.panel, "Approvals")
        approval = await self.service.handle_callback(PrivateCallbackRequest(214, 7, 7, "approval", approval_token))
        self.assertEqual(PrivateControlStatus.RENDERED, approval.status)
        self.assertIn("fake privileged command", approval.panel.text)
        self.assertIn("Allow", [button.label for row in approval.panel.rows for button in row])
        allow = self.token(approval.panel, "Allow")
        unauthorized = await self.service.handle_callback(PrivateCallbackRequest(215, 8, 8, "approval", allow))
        self.assertEqual(PrivateControlStatus.UNAUTHORIZED, unauthorized.status)
        self.assertIsNone(await self.storage.read(lambda c, h=hashlib.sha256(allow.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))
        decided = await self.service.handle_callback(PrivateCallbackRequest(216, 7, 7, "approval", allow))
        self.assertEqual(PrivateControlStatus.APPROVED, decided.status)
        replay = await self.service.handle_callback(PrivateCallbackRequest(217, 7, 7, "approval", allow))
        self.assertEqual(PrivateControlStatus.ALREADY_USED, replay.status)
        self.assertIs(ApprovalState.APPROVED, (await ApprovalRepository(self.storage).get("approval")).state)
        deny = self.token(approval.panel, "Deny")
        sibling = await self.service.handle_callback(PrivateCallbackRequest(218, 7, 7, "approval", deny))
        self.assertEqual(PrivateControlStatus.STALE, sibling.status)
        self.assertIs(ApprovalState.APPROVED, (await ApprovalRepository(self.storage).get("approval")).state)
        projected = await self.service.project_approval(PrivateApprovalProjectionRequest("approval"))
        self.assertEqual(PrivateControlStatus.BLOCKED, projected.status)

        unknown = "z" * 32
        await PrivateManagementRepository(self.storage, now_ms=self.clock).create_callback_batch(
            actions=(PrivateCallbackActionSpec(
                hashlib.sha256(unknown.encode()).hexdigest(), "P5_UNKNOWN", "future", "future", 1,
                "PRIVATE_ROOT", 7, 7,
            ),), created_at_ms=100, expires_at_ms=1000,
        )
        unknown_result = await self.service.handle_callback(PrivateCallbackRequest(219, 7, 7, "unknown", unknown))
        self.assertEqual(PrivateControlStatus.BLOCKED, unknown_result.status)
        self.assertIsNone(await self.storage.read(lambda c, h=hashlib.sha256(unknown.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))

        stale_root = await self.service.handle_command(PrivateCommandRequest(220, 7, 7, PrivateCommand.MENU))
        stale_token = self.token(stale_root.panel, "Refresh")
        before_dialogue = await DialogueRepository(self.storage).get_live()
        before_job = await TurnJobRepository(self.storage).get("job")
        before_boot = await ControllerRuntimeRepository(self.storage).get()
        after_boot = await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet")
        self.assertEqual(before_boot.boot_generation + 1, after_boot.record.boot_generation)
        stale = await self.service.handle_callback(PrivateCallbackRequest(221, 7, 7, "old-root", stale_token))
        self.assertEqual(PrivateControlStatus.STALE, stale.status)
        self.assertEqual(before_dialogue, await DialogueRepository(self.storage).get_live())
        self.assertEqual(before_job, await TurnJobRepository(self.storage).get("job"))
        self.assertIsNotNone(await self.storage.read(lambda c, h=hashlib.sha256(stale_token.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))
