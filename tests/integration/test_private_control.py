import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

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
    PrivateControlError,
    PrivateControlErrorCategory,
    PrivateApprovalProjectionRequest,
)
from codex_control.domain import CodexProfile, ControllerMode
from codex_control.storage import (
    ControllerRuntimeRepository,
    ApprovalKind,
    ApprovalRepository,
    ApprovalState,
    DialogueRepository,
    RepositoryError,
    RepositoryErrorCategory,
    TransientPayloadKind,
    TransientPayloadRepository,
    TurnJobRepository,
    TurnTerminalOutcome,
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

        self.now = 100

        def clock():
            self.clock_calls += 1
            return self.now

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
            profiles=(CodexProfile("profile-a", "/synthetic/profile-a", "Profile A", "/synthetic/state-a"),),
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

    async def seed_running_job(self):
        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).create_intent(
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a"
        )
        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).confirm_created(
            dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id="thread"
        )
        jobs = TurnJobRepository(self.storage, now_ms=self.clock)
        admitted = await jobs.claim_ingress(
            update_id=1000, job_id="job", source_chat_id=-7, source_message_id=1,
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a",
            thread_id="thread", model_id="model-a", reasoning_effort="high",
            input_payload_id="input", input_content=b"input", input_expires_at_ms=10000,
        )
        claimed = await jobs.claim_turn(
            job_id="job", expected_job_version=admitted.job.version,
            expected_dialogue_version=dialogue.version, thread_id="thread",
        )
        starting = await jobs.mark_codex_starting(job_id="job", expected_version=claimed.job.version)
        return await jobs.mark_codex_running(
            job_id="job", expected_version=starting.version, codex_turn_id="turn"
        )

    async def seed_approval(self, *, approval_id="approval", content=b"safe details", display=True, expires=10000):
        running = await self.seed_running_job()
        payload_id = None
        if display:
            payload_id = approval_id + "-payload"
            await TransientPayloadRepository(self.storage, now_ms=self.clock).create(
                payload_id=payload_id, dialogue_id="dialogue", job_id="job",
                kind=TransientPayloadKind.APPROVAL, content=content, expires_at_ms=expires,
            )
        approval = await ApprovalRepository(self.storage, now_ms=self.clock).create_pending(
            approval_id=approval_id, profile_id="profile-a", wire_request_id=approval_id + "-wire",
            kind=ApprovalKind.COMMAND_EXECUTION, job_id="job", expected_job_version=running.version,
            display_payload_id=payload_id, expires_at_ms=expires,
        )
        return running, approval

    async def approval_panel(self, *, approval_id="approval", content=b"safe details", display=True, expires=10000):
        await self.seed_approval(approval_id=approval_id, content=content, display=display, expires=expires)
        root = await self.service.handle_command(PrivateCommandRequest(1001, 7, 7, PrivateCommand.MENU))
        result = await self.service.handle_callback(
            PrivateCallbackRequest(1002, 7, 7, "approval", self.token(root.panel, "Approvals"))
        )
        self.assertEqual(PrivateControlStatus.RENDERED, result.status)
        return result

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

    async def test_p41_settings_binding_and_real_callback_delegation_without_facade_preclaim(self):
        root = await self.service.handle_command(PrivateCommandRequest(20, 7, 7, PrivateCommand.MENU))
        token = self.token(root.panel, "Settings")
        row = await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): tuple(c.execute(
            "SELECT action, subject_type, subject_id, expected_version, expected_state, consumed_at_ms "
            "FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()))
        self.assertEqual(("OPEN_ROOT", "panel", "0", 0, "NO_DIALOGUE", None), row)

        class ForbiddenFacadeClaim:
            def __init__(self, *args, **kwargs):
                pass
            async def claim(self, *args, **kwargs):
                raise AssertionError("facade generic-preclaimed a P4.1 callback")

        with patch("codex_control.application.private_control.CallbackActionRepository", ForbiddenFacadeClaim):
            settings = await self.service.handle_callback(PrivateCallbackRequest(21, 7, 7, "settings", token))
        self.assertEqual(PrivateControlStatus.RENDERED, settings.status)
        models = await self.service.handle_callback(
            PrivateCallbackRequest(22, 7, 7, "models", self.token(settings.panel, "Models"))
        )
        selected = await self.service.handle_callback(
            PrivateCallbackRequest(23, 7, 7, "model", self.token(models.panel, "Model A"))
        )
        self.assertEqual(PrivateControlStatus.NO_CHANGE, selected.status)
        self.assertIsNotNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)
        ).fetchone()[0]))

    async def test_p42_callback_delegation_and_begin_cancel_delete_have_zero_effect(self):
        dialogue = await DialogueRepository(self.storage, now_ms=self.clock).create_intent(
            dialogue_id="dialogue", server_id="server-80", profile_id="profile-a"
        )
        await DialogueRepository(self.storage, now_ms=self.clock).confirm_created(
            dialogue_id=dialogue.dialogue_id, expected_version=dialogue.version, thread_id="thread"
        )
        root = await self.service.handle_command(PrivateCommandRequest(24, 7, 7, PrivateCommand.MENU))
        dialogue_status = await self.service.handle_callback(
            PrivateCallbackRequest(25, 7, 7, "dialogue", self.token(root.panel, "Dialogue"))
        )
        self.assertEqual(PrivateControlStatus.RENDERED, dialogue_status.status)
        begin = self.token(dialogue_status.panel, "Delete")
        begin_row = await self.storage.read(lambda c, h=hashlib.sha256(begin.encode()).hexdigest(): tuple(c.execute(
            "SELECT action, consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)
        ).fetchone()))
        self.assertEqual(("P42_BEGIN_DELETE", None), begin_row)

        class ForbiddenFacadeClaim:
            def __init__(self, *args, **kwargs):
                pass
            async def claim(self, *args, **kwargs):
                raise AssertionError("facade generic-preclaimed a P4.2 callback")

        with patch("codex_control.application.private_control.CallbackActionRepository", ForbiddenFacadeClaim):
            confirmation = await self.service.handle_callback(PrivateCallbackRequest(26, 7, 7, "delete", begin))
        self.assertEqual(PrivateControlStatus.CONFIRM_REQUIRED, confirmation.status)
        cancel = self.token(confirmation.panel, "Cancel")
        result = await self.service.handle_callback(PrivateCallbackRequest(27, 7, 7, "cancel", cancel))
        self.assertEqual(PrivateControlStatus.RENDERED, result.status)
        self.assertEqual([], getattr(self.service._dialogue_service._delete_service, "calls", []))

    async def test_list_pending_for_job_is_exact_order_read_only_and_missing_job_is_not_found(self):
        running = await self.seed_running_job()
        repo = ApprovalRepository(self.storage, now_ms=self.clock)
        await repo.create_pending(
            approval_id="z", profile_id="profile-a", wire_request_id="wire-z", kind=ApprovalKind.COMMAND_EXECUTION,
            job_id="job", expected_job_version=running.version, expires_at_ms=10000,
        )
        await repo.create_pending(
            approval_id="a", profile_id="profile-a", wire_request_id="wire-a", kind=ApprovalKind.FILE_CHANGE,
            job_id="job", expected_job_version=running.version, expires_at_ms=10000,
        )
        before = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM approvals").fetchone()[0])
        self.clock_calls = 0
        values = await repo.list_pending_for_job("job")
        self.assertEqual(["a", "z"], [value.approval_id for value in values])
        self.assertTrue(all(value.state is ApprovalState.PENDING and value.job_id == "job" for value in values))
        self.assertEqual(before, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]))
        self.assertEqual(0, self.clock_calls)
        with self.assertRaises(RepositoryError) as raised:
            await repo.list_pending_for_job("missing")
        self.assertIs(RepositoryErrorCategory.NOT_FOUND, raised.exception.category)

    async def test_complete_approval_projection_has_exact_safe_details_and_bindings(self):
        result = await self.approval_panel(approval_id="approval-server-id", content=b"operator-safe details")
        current_job = await TurnJobRepository(self.storage).get("job")
        self.assertIsNotNone(current_job)
        self.assertIn("operator-safe details", result.panel.text)
        self.assertNotIn("approval-server-id", result.panel.text)
        self.assertNotIn("approval-server-id-wire", result.panel.text)
        self.assertNotIn("dialogue", result.panel.text)
        self.assertNotIn("job", result.panel.text)
        labels = [button.label for row in result.panel.rows for button in row]
        self.assertIn("Allow", labels)
        self.assertIn("Deny", labels)
        for label in ("Allow", "Deny"):
            token = self.token(result.panel, label)
            row = await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): tuple(c.execute(
                "SELECT action, subject_type, subject_id, expected_version, expected_state, authorized_user_id, authorized_chat_id, consumed_at_ms "
                "FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()))
            self.assertEqual(("approval_allow" if label == "Allow" else "approval_deny", "approval", "approval-server-id", current_job.version, "PENDING", 7, 7, None), row)
            self.assertEqual(36, len("cc1:" + token))
            self.assertTrue(("cc1:" + token).startswith("cc1:"))
            self.assertNotIn("approval-server-id", "cc1:" + token)

    async def assert_deny_only(self, *, approval_id, content, display):
        result = await self.approval_panel(approval_id=approval_id, content=content, display=display)
        labels = [button.label for row in result.panel.rows for button in row]
        self.assertNotIn("Allow", labels)
        self.assertIn("Deny", labels)

    async def test_approval_missing_details_is_deny_only(self):
        await self.assert_deny_only(approval_id="approval-missing", content=b"", display=False)

    async def test_approval_invalid_utf8_is_deny_only(self):
        await self.assert_deny_only(approval_id="approval-invalid", content=b"\xff", display=True)

    async def test_approval_empty_details_is_deny_only(self):
        await self.assert_deny_only(approval_id="approval-empty", content=b"   ", display=True)

    async def test_approval_2401_details_is_deny_only_without_truncation(self):
        await self.assert_deny_only(approval_id="approval-oversized", content=b"x" * 2401, display=True)

    async def test_complete_2400_details_enable_allow_without_truncation(self):
        details = b"x" * 2400
        result = await self.approval_panel(content=details)
        self.assertIn("Allow", [button.label for row in result.panel.rows for button in row])
        self.assertIn("x" * 2400, result.panel.text)

    async def test_wrong_approval_principal_is_unconsumed_then_right_principal_succeeds(self):
        result = await self.approval_panel()
        token = self.token(result.panel, "Allow")
        wrong = await self.service.handle_callback(PrivateCallbackRequest(30, 8, 8, "wrong", token))
        self.assertEqual(PrivateControlStatus.UNAUTHORIZED, wrong.status)
        self.assertIsNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))
        self.assertIs(ApprovalState.PENDING, (await ApprovalRepository(self.storage).get("approval")).state)
        right = await self.service.handle_callback(PrivateCallbackRequest(31, 7, 7, "right", token))
        self.assertEqual(PrivateControlStatus.APPROVED, right.status)

    async def test_allow_is_atomic_and_never_generic_preclaimed(self):
        result = await self.approval_panel()
        token = self.token(result.panel, "Allow")
        class ForbiddenFacadeClaim:
            def __init__(self, *args, **kwargs):
                pass
            async def claim(self, *args, **kwargs):
                raise AssertionError("approval was generically preclaimed")
        with patch("codex_control.application.private_control.CallbackActionRepository", ForbiddenFacadeClaim):
            decided = await self.service.handle_callback(PrivateCallbackRequest(32, 7, 7, "allow", token))
        self.assertEqual(PrivateControlStatus.APPROVED, decided.status)
        self.assertIs(ApprovalState.APPROVED, (await ApprovalRepository(self.storage).get("approval")).state)
        self.assertIsNotNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))

    async def test_deny_is_atomic_and_has_no_external_response(self):
        result = await self.approval_panel()
        token = self.token(result.panel, "Deny")
        with patch("codex_control.application.private_control.CallbackActionRepository.claim", side_effect=AssertionError("generic claim")):
            denied = await self.service.handle_callback(PrivateCallbackRequest(33, 7, 7, "deny", token))
        self.assertEqual(PrivateControlStatus.DENIED, denied.status)
        self.assertIs(ApprovalState.DENIED, (await ApprovalRepository(self.storage).get("approval")).state)
        self.assertIsNotNone(await self.storage.read(lambda c, h=hashlib.sha256(token.encode()).hexdigest(): c.execute(
            "SELECT consumed_at_ms FROM callback_actions WHERE token_hash_sha256 = ?", (h,)).fetchone()[0]))

    async def test_approval_replay_and_sibling_cannot_decide_twice(self):
        result = await self.approval_panel()
        allow = self.token(result.panel, "Allow")
        deny = self.token(result.panel, "Deny")
        self.assertEqual(PrivateControlStatus.APPROVED, (await self.service.handle_callback(PrivateCallbackRequest(34, 7, 7, "allow", allow))).status)
        self.assertEqual(PrivateControlStatus.ALREADY_USED, (await self.service.handle_callback(PrivateCallbackRequest(35, 7, 7, "replay", allow))).status)
        self.assertEqual(PrivateControlStatus.STALE, (await self.service.handle_callback(PrivateCallbackRequest(36, 7, 7, "sibling", deny))).status)
        self.assertIs(ApprovalState.APPROVED, (await ApprovalRepository(self.storage).get("approval")).state)

    async def test_stale_approval_callback_is_consumed_without_decision(self):
        running, _ = await self.seed_approval()
        root = await self.service.handle_command(PrivateCommandRequest(37, 7, 7, PrivateCommand.MENU))
        panel = await self.service.handle_callback(PrivateCallbackRequest(38, 7, 7, "approval", self.token(root.panel, "Approvals")))
        allow = self.token(panel.panel, "Allow")
        dialogue = await DialogueRepository(self.storage).get_live()
        await TurnJobRepository(self.storage, now_ms=self.clock).finish_codex(
            job_id="job", expected_job_version=running.version, expected_dialogue_version=dialogue.version,
            outcome=TurnTerminalOutcome.UNKNOWN, error_class="CODEX_AMBIGUOUS",
        )
        stale = await self.service.handle_callback(PrivateCallbackRequest(39, 7, 7, "stale", allow))
        self.assertEqual((PrivateControlStatus.STALE, PrivateControlReason.STALE_ACTION), (stale.status, stale.reason))
        self.assertIs(ApprovalState.PENDING, (await ApprovalRepository(self.storage).get("approval")).state)
        self.assertEqual(PrivateControlStatus.ALREADY_USED, (await self.service.handle_callback(PrivateCallbackRequest(40, 7, 7, "replay", allow))).status)

    async def test_approval_expiry_is_deterministic_and_no_external_effect(self):
        result = await self.approval_panel(expires=200)
        allow = self.token(result.panel, "Allow")
        self.now = 201
        expired = await self.service.handle_callback(PrivateCallbackRequest(41, 7, 7, "expired", allow))
        self.assertEqual(PrivateControlStatus.EXPIRED, expired.status)
        self.assertIs(ApprovalState.EXPIRED, (await ApprovalRepository(self.storage).get("approval")).state)
        self.assertEqual(PrivateControlStatus.ALREADY_USED, (await self.service.handle_callback(PrivateCallbackRequest(42, 7, 7, "replay", allow))).status)

    async def test_project_approval_current_and_terminal_blocked(self):
        await self.seed_approval()
        current = await self.service.project_approval(PrivateApprovalProjectionRequest("approval"))
        self.assertEqual(PrivateControlStatus.RENDERED, current.status)
        deny = self.token(current.panel, "Deny")
        self.assertEqual(PrivateControlStatus.DENIED, (await self.service.handle_callback(PrivateCallbackRequest(43, 7, 7, "deny", deny))).status)
        terminal = await self.service.project_approval(PrivateApprovalProjectionRequest("approval"))
        self.assertEqual((PrivateControlStatus.BLOCKED, PrivateControlReason.NO_PENDING_APPROVAL), (terminal.status, terminal.reason))

    async def test_latest_error_order_is_tied_by_fingerprint_without_clock_or_mutation(self):
        self.now = 99
        errors = ErrorFingerprintRepository(self.storage, now_ms=self.clock)
        await errors.record(fingerprint_sha256="c" * 64, error_class="C")
        self.now = 100
        await errors.record(fingerprint_sha256="b" * 64, error_class="B")
        await errors.record(fingerprint_sha256="a" * 64, error_class="A")
        count = await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM errors").fetchone()[0])
        self.clock_calls = 0
        latest = await errors.latest()
        self.assertEqual("a" * 64, latest.fingerprint_sha256)
        self.assertEqual(100, latest.last_seen_at_ms)
        self.assertEqual(0, self.clock_calls)
        self.assertEqual(count, await self.storage.read(lambda c: c.execute("SELECT COUNT(*) FROM errors").fetchone()[0]))

    async def test_diagnostics_absent_provider_is_unavailable(self):
        root = await self.service.handle_command(PrivateCommandRequest(44, 7, 7, PrivateCommand.MENU))
        result = await self.service.handle_callback(PrivateCallbackRequest(45, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertEqual(PrivateControlStatus.RENDERED, result.status)
        self.assertIn("Storage: UNAVAILABLE", result.panel.text)
        self.assertIn("Codex runtime: UNAVAILABLE", result.panel.text)

    async def test_diagnostics_valid_snapshot_and_provider_failures_are_safe(self):
        self.service._diagnostics_provider = lambda: PrivateDiagnosticsSnapshot(
            PrivateDiagnosticState.OK, PrivateDiagnosticState.DEGRADED, 12, 34, 56
        )
        root = await self.service.handle_command(PrivateCommandRequest(46, 7, 7, PrivateCommand.MENU))
        result = await self.service.handle_callback(PrivateCallbackRequest(47, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertIn("Storage: OK", result.panel.text)
        self.assertIn("Codex runtime: DEGRADED", result.panel.text)
        self.assertIn("Database bytes: 12", result.panel.text)
        self.assertIn("Transient payload bytes: 34", result.panel.text)
        self.assertIn("Filesystem free bytes: 56", result.panel.text)
        self.service._diagnostics_provider = lambda: (_ for _ in ()).throw(RuntimeError("raw exception"))
        root = await self.service.handle_command(PrivateCommandRequest(48, 7, 7, PrivateCommand.MENU))
        with self.assertRaises(PrivateControlError) as raised:
            await self.service.handle_callback(PrivateCallbackRequest(49, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertIs(PrivateControlErrorCategory.INVARIANT, raised.exception.category)
        self.service._diagnostics_provider = lambda: object()
        root = await self.service.handle_command(PrivateCommandRequest(50, 7, 7, PrivateCommand.MENU))
        with self.assertRaises(PrivateControlError) as raised:
            await self.service.handle_callback(PrivateCallbackRequest(51, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertIs(PrivateControlErrorCategory.INVARIANT, raised.exception.category)

    async def test_diagnostics_latest_error_shows_safe_scope_without_fingerprint_or_entity_ids(self):
        running = await self.seed_running_job()
        fingerprint = "d" * 64
        await ErrorFingerprintRepository(self.storage, now_ms=self.clock).record(
            fingerprint_sha256=fingerprint, error_class="CODEX_PROCESS", dialogue_id="dialogue", job_id="job"
        )
        root = await self.service.handle_command(PrivateCommandRequest(52, 7, 7, PrivateCommand.MENU))
        result = await self.service.handle_callback(PrivateCallbackRequest(53, 7, 7, "diagnostics", self.token(root.panel, "Diagnostics")))
        self.assertIn("CODEX_PROCESS", result.panel.text)
        self.assertIn("count 1", result.panel.text)
        self.assertIn("scope dialogue+job", result.panel.text)
        for secret in (fingerprint, "dialogue", "job", "thread", "turn", "/synthetic/profile-a", "raw exception"):
            if secret in {"dialogue", "job"}:
                continue
            self.assertNotIn(secret, result.panel.text)
        self.assertNotIn("dialogue)" , result.panel.text)
        self.assertEqual("job", running.job_id)
