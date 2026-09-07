import hashlib
import os
import tempfile
import unittest

from codex_control.adapters.telegram import PrivateCommand
from codex_control.application import (
    PrivateCallbackRequest,
    PrivateCommandRequest,
    PrivateControlStatus,
    PrivateApprovalProjectionRequest,
)
from codex_control.storage import (
    ApprovalKind,
    ApprovalRepository,
    DialogueRepository,
    PrivateCallbackActionSpec,
    PrivateManagementRepository,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
)

from tests.integration.test_private_control import Catalog, PassiveEffects


class FinalFakeP4AcceptanceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.clock = lambda: 100
        from codex_control.storage import ControllerRuntimeRepository, SettingsRepository, SqliteStorage
        self.storage = await SqliteStorage.open(os.path.join(self.tempdir.name, "state.sqlite3"), now_ms=self.clock)
        await ControllerRuntimeRepository(self.storage, now_ms=self.clock).begin_boot("fleet")
        await SettingsRepository(self.storage, now_ms=self.clock).initialize_if_absent(
            profile_id="profile-a", model_id="model-a", reasoning_effort="high"
        )
        self.number = 0

        def token_factory():
            self.number += 1
            return f"{self.number:032d}"

        from codex_control.application import PrivateControlService
        from codex_control.domain import CodexProfile
        self.service = PrivateControlService(
            self.storage, server_id="server-80", server_display_name="Server 80", operator_user_id=7,
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A"),),
            model_catalog=Catalog(), interrupt_service=PassiveEffects(), delete_service=PassiveEffects(),
            now_ms=self.clock, token_factory=token_factory,
        )

    async def asyncTearDown(self):
        await self.storage.close()
        self.tempdir.cleanup()

    @staticmethod
    def token(panel, label):
        return next(button.callback_data[4:] for row in panel.rows for button in row if button.label == label)

    async def test_final_private_management_composition_fake(self):
        root = await self.service.handle_command(PrivateCommandRequest(200, 7, 7, PrivateCommand.MENU))
        self.assertEqual(PrivateControlStatus.RENDERED, root.status)

        settings_token = self.token(root.panel, "Settings")
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
        root = await self.service.handle_command(PrivateCommandRequest(207, 7, 7, PrivateCommand.MENU))
        dialogue_token = self.token(root.panel, "Dialogue")
        running_status = await self.service.handle_callback(PrivateCallbackRequest(208, 7, 7, "running-dialogue", dialogue_token))
        delete_token = self.token(running_status.panel, "Delete")
        confirmation = await self.service.handle_callback(PrivateCallbackRequest(209, 7, 7, "delete", delete_token))
        self.assertEqual(PrivateControlStatus.CONFIRM_REQUIRED, confirmation.status)
        self.assertIn("CONFIRM DELETE", [button.label for row in confirmation.panel.rows for button in row])

        root = await self.service.handle_command(PrivateCommandRequest(210, 7, 7, PrivateCommand.MENU))
        approval_token = self.token(root.panel, "Approvals")
        approval = await self.service.handle_callback(PrivateCallbackRequest(211, 7, 7, "approval", approval_token))
        self.assertEqual(PrivateControlStatus.RENDERED, approval.status)
        self.assertIn("fake privileged command", approval.panel.text)
        self.assertIn("Allow", [button.label for row in approval.panel.rows for button in row])
        allow = self.token(approval.panel, "Allow")
        unauthorized = await self.service.handle_callback(PrivateCallbackRequest(212, 8, 8, "approval", allow))
        self.assertEqual(PrivateControlStatus.UNAUTHORIZED, unauthorized.status)
        decided = await self.service.handle_callback(PrivateCallbackRequest(213, 7, 7, "approval", allow))
        self.assertEqual(PrivateControlStatus.APPROVED, decided.status)
        replay = await self.service.handle_callback(PrivateCallbackRequest(214, 7, 7, "approval", allow))
        self.assertEqual(PrivateControlStatus.ALREADY_USED, replay.status)
        self.assertEqual("APPROVED", (await ApprovalRepository(self.storage).get("approval")).state.value)
        projected = await self.service.project_approval(PrivateApprovalProjectionRequest("approval"))
        self.assertEqual(PrivateControlStatus.BLOCKED, projected.status)

        unknown = "z" * 32
        await PrivateManagementRepository(self.storage, now_ms=self.clock).create_callback_batch(
            actions=(PrivateCallbackActionSpec(
                hashlib.sha256(unknown.encode()).hexdigest(), "P5_UNKNOWN", "future", "future", 1,
                "PRIVATE_ROOT", 7, 7,
            ),), created_at_ms=100, expires_at_ms=1000,
        )
        unknown_result = await self.service.handle_callback(PrivateCallbackRequest(215, 7, 7, "unknown", unknown))
        self.assertEqual(PrivateControlStatus.BLOCKED, unknown_result.status)
