import unittest
from dataclasses import FrozenInstanceError, fields

from codex_control.adapters.telegram import PrivateCommand, TelegramPrivateControlRenderer
from codex_control.application import (
    P43_APPROVAL_DETAILS_MAX_CHARS,
    PrivateAdminButton,
    PrivateAdminPanel,
    PrivateApprovalProjectionRequest,
    PrivateControlError,
    PrivateControlErrorCategory,
    PrivateControlPanel,
    PrivateControlPanelSection,
    PrivateControlReason,
    PrivateControlResult,
    PrivateControlService,
    PrivateControlStatus,
    PrivateDiagnosticState,
    PrivateDiagnosticsSnapshot,
)
from codex_control.application.private_control import _sanitize_approval_details
from codex_control.application.private_dialogue import (
    PrivateDialoguePanel,
    PrivateDialoguePanelSection,
)
from codex_control.application.private_settings import (
    PrivateAdminReason,
    PrivateAdminStatus,
    PrivatePanelSection,
)
from codex_control.application.private_dialogue import (
    PrivateDialogueReason,
    PrivateDialogueResult,
    PrivateDialogueStatus,
)


class PrivateControlContractTests(unittest.TestCase):
    def test_exact_final_enums(self):
        self.assertEqual(
            "RENDERED UPDATED NO_CHANGE CONFIRM_REQUIRED INTERRUPTED DELETED CONFIRMED_PENDING_STORAGE APPROVED DENIED BLOCKED STALE UNKNOWN FAILED EXPIRED ALREADY_USED DUPLICATE UNAUTHORIZED UNSUPPORTED".split(),
            [item.value for item in PrivateControlStatus],
        )
        self.assertEqual(
            "CALLBACK_NOT_FOUND STALE_ACTION ACTION_UNAVAILABLE SETTINGS_MISSING PROFILE_NOT_CONFIGURED PROFILE_LOCKED DIALOGUE_NOT_IDLE MODEL_NOT_CONFIGURED MODEL_UNAVAILABLE REASONING_EFFORT_UNSUPPORTED CATALOG_UNAVAILABLE NO_DIALOGUE DIALOGUE_NOT_RUNNING JOB_NOT_RUNNING ACTIVE_BINDING_UNAVAILABLE INTERRUPT_IN_PROGRESS INTERRUPT_UNRESOLVED DIALOGUE_NOT_READY DELETE_NOT_READY DELETE_IN_PROGRESS DELETE_UNKNOWN NO_PENDING_APPROVAL DIAGNOSTICS_UNAVAILABLE".split(),
            [item.value for item in PrivateControlReason],
        )
        self.assertEqual("INVALID_ARGUMENT STORAGE INVARIANT".split(), [item.value for item in PrivateControlErrorCategory])

    def test_accepted_private_command_p41_and_p42_enums_are_unchanged(self):
        self.assertEqual(["MENU", "SETTINGS"], [item.value for item in PrivateCommand])
        self.assertEqual(
            "RENDERED UPDATED NO_CHANGE BLOCKED STALE EXPIRED ALREADY_USED DUPLICATE UNAUTHORIZED UNSUPPORTED".split(),
            [item.value for item in PrivateAdminStatus],
        )
        self.assertEqual(
            "CALLBACK_NOT_FOUND STALE_ACTION SETTINGS_MISSING PROFILE_NOT_CONFIGURED PROFILE_LOCKED DIALOGUE_NOT_IDLE MODEL_NOT_CONFIGURED MODEL_UNAVAILABLE REASONING_EFFORT_UNSUPPORTED CATALOG_UNAVAILABLE ACTION_UNAVAILABLE".split(),
            [item.value for item in PrivateAdminReason],
        )
        self.assertEqual(["ROOT", "PROFILES", "MODELS", "REASONING"], [item.value for item in PrivatePanelSection])
        self.assertEqual(
            "RENDERED CONFIRM_REQUIRED INTERRUPTED DELETED CONFIRMED_PENDING_STORAGE BLOCKED STALE UNKNOWN FAILED EXPIRED ALREADY_USED UNAUTHORIZED".split(),
            [item.value for item in PrivateDialogueStatus],
        )
        self.assertEqual(
            "CALLBACK_NOT_FOUND STALE_ACTION NO_DIALOGUE DIALOGUE_NOT_RUNNING JOB_NOT_RUNNING ACTIVE_BINDING_UNAVAILABLE INTERRUPT_IN_PROGRESS INTERRUPT_UNRESOLVED DIALOGUE_NOT_READY DELETE_NOT_READY DELETE_IN_PROGRESS DELETE_UNKNOWN ACTION_UNAVAILABLE".split(),
            [item.value for item in PrivateDialogueReason],
        )
        from codex_control.application.private_dialogue import PrivateDialoguePanelSection
        self.assertEqual(["STATUS", "DELETE_CONFIRM"], [item.value for item in PrivateDialoguePanelSection])

    def test_pending_storage_projection_is_truthful_and_not_deleted(self):
        result = PrivateControlService._map_dialogue(
            PrivateDialogueResult(PrivateDialogueStatus.CONFIRMED_PENDING_STORAGE, None, None)
        )
        self.assertEqual(PrivateControlStatus.CONFIRMED_PENDING_STORAGE, result.status)
        self.assertNotEqual(PrivateControlStatus.DELETED, result.status)

    def test_public_records_are_frozen_and_redacted(self):
        request = PrivateApprovalProjectionRequest("approval-secret")
        self.assertEqual("PrivateApprovalProjectionRequest(approval_id='[REDACTED]')", repr(request))
        button = PrivateAdminButton("Allow", "cc1:" + "a" * 32)
        panel = PrivateControlPanel(PrivateControlPanelSection.APPROVAL, "secret command/path", ((button,),))
        self.assertNotIn("secret command/path", repr(panel))
        self.assertNotIn("cc1:", repr(panel))
        self.assertEqual(["section", "text", "rows"], [field.name for field in fields(panel)])
        with self.assertRaises(FrozenInstanceError):
            panel.text = "changed"

    def test_diagnostics_snapshot_exact_validation(self):
        value = PrivateDiagnosticsSnapshot(PrivateDiagnosticState.OK, PrivateDiagnosticState.DEGRADED, 0, 12, None)
        self.assertEqual(12, value.transient_payload_bytes)
        with self.assertRaises(PrivateControlError):
            PrivateDiagnosticsSnapshot(PrivateDiagnosticState.OK, PrivateDiagnosticState.OK, True, None, None)
        with self.assertRaises(PrivateControlError):
            PrivateDiagnosticsSnapshot(PrivateDiagnosticState.OK, PrivateDiagnosticState.OK, -1, None, None)

    def test_renderer_has_only_minimal_structure_and_exact_panel_types(self):
        button = PrivateAdminButton("Back", "cc1:" + "b" * 32)
        panels = (
            PrivateAdminPanel(PrivatePanelSection.ROOT, "root", ((button,),)),
            PrivateDialoguePanel(PrivateDialoguePanelSection.STATUS, "status", ((button,),)),
            PrivateControlPanel(PrivateControlPanelSection.ROOT, "control", ((button,),)),
        )
        for panel in panels:
            result = TelegramPrivateControlRenderer().render(panel)
            self.assertEqual({"text", "reply_markup"}, set(result))
            self.assertNotIn("parse_mode", result)
            self.assertEqual("Back", result["reply_markup"]["inline_keyboard"][0][0]["text"])
        with self.assertRaises(ValueError):
            TelegramPrivateControlRenderer().render(object())

    def test_complete_details_budget_is_not_truncated(self):
        self.assertEqual("a b", _sanitize_approval_details("a\n\t b"))
        self.assertEqual("x" * P43_APPROVAL_DETAILS_MAX_CHARS, _sanitize_approval_details("x" * P43_APPROVAL_DETAILS_MAX_CHARS))
        self.assertIsNone(_sanitize_approval_details("x" * (P43_APPROVAL_DETAILS_MAX_CHARS + 1)))
        self.assertIsNone(_sanitize_approval_details(""))

    def test_invalid_utf8_is_not_accepted(self):
        with self.assertRaises(UnicodeDecodeError):
            b"\xff".decode("utf-8", errors="strict")
