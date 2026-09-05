import unittest

from codex_control.adapters.codex.approvals import (
    ApprovalDecision,
    ApprovalError,
    ApprovalErrorCategory,
    ApprovalHandlingStatus,
)
from codex_control.adapters.codex.capabilities import (
    AdapterImplementation,
    CodexCapability,
    load_manifest,
)
from codex_control.adapters.codex.errors import (
    CodexAdapterError,
    CodexAdapterErrorCategory,
    normalize_error,
)
from codex_control.adapters.codex.protocol import InboundServerRequest, ProtocolRemoteError
from codex_control.adapters.codex.thread_lifecycle import (
    ThreadBinding,
    ThreadLifecycleError,
    ThreadOperationStatus,
)
from codex_control.adapters.codex.turn_lifecycle import (
    AgentMessageCompleted,
    TurnBinding,
    TurnInterruptResult,
    TurnInterruptStatus,
    TurnLifecycleError,
    TurnTerminalResult,
    TurnTerminalStatus,
)


class P110T0Acceptance(unittest.TestCase):
    def test_manifest_has_exact_current_capability_set_and_all_are_implemented(self):
        expected = {
            CodexCapability.MODEL_LIST,
            CodexCapability.THREAD_START,
            CodexCapability.THREAD_RESUME,
            CodexCapability.THREAD_DELETE,
            CodexCapability.TURN_START,
            CodexCapability.TURN_INTERRUPT,
            CodexCapability.AGENT_MESSAGE_EVENTS,
            CodexCapability.TURN_TERMINAL_EVENTS,
            CodexCapability.APPROVAL_SERVER_REQUESTS,
            CodexCapability.APPROVAL_RESPONSE_SCHEMA,
        }
        self.assertEqual(set(CodexCapability), expected)
        manifest = load_manifest()
        self.assertEqual(set(manifest.capabilities), expected)
        self.assertTrue(all(
            status.adapter_implementation is AdapterImplementation.IMPLEMENTED
            for status in manifest.capabilities.values()
        ))

    def test_status_and_approval_contracts_are_finite(self):
        self.assertEqual(
            set(ThreadOperationStatus),
            {
                ThreadOperationStatus.START_CONFIRMED,
                ThreadOperationStatus.START_REJECTED,
                ThreadOperationStatus.START_UNKNOWN,
                ThreadOperationStatus.RESUME_CONFIRMED,
                ThreadOperationStatus.RESUME_REJECTED,
                ThreadOperationStatus.RESUME_UNKNOWN,
                ThreadOperationStatus.DELETE_CONFIRMED,
                ThreadOperationStatus.DELETE_UNKNOWN,
            },
        )
        self.assertFalse(hasattr(ThreadOperationStatus, "DELETE_REJECTED"))
        self.assertEqual(
            set(TurnInterruptStatus),
            {
                TurnInterruptStatus.CONFIRMED,
                TurnInterruptStatus.RECONCILED,
                TurnInterruptStatus.REJECTED,
                TurnInterruptStatus.UNKNOWN,
            },
        )
        self.assertEqual(set(TurnTerminalStatus), {
            TurnTerminalStatus.COMPLETED,
            TurnTerminalStatus.FAILED,
            TurnTerminalStatus.UNKNOWN,
        })
        self.assertEqual(set(ApprovalDecision), {ApprovalDecision.ALLOW, ApprovalDecision.DENY})
        self.assertEqual(set(ApprovalHandlingStatus), {
            ApprovalHandlingStatus.ALLOWED,
            ApprovalHandlingStatus.DENIED,
            ApprovalHandlingStatus.RESPONSE_UNKNOWN,
        })
        self.assertEqual(set(ApprovalErrorCategory), {
            ApprovalErrorCategory.APPROVAL_REQUEST_INVALID,
            ApprovalErrorCategory.APPROVAL_DECISION_INVALID,
            ApprovalErrorCategory.APPROVAL_OPERATION_BUSY,
            ApprovalErrorCategory.APPROVAL_PROTOCOL_TERMINAL,
            ApprovalErrorCategory.APPROVAL_RESPONSE_UNKNOWN,
        })

    def test_finite_errors_have_no_retry_policy_fields(self):
        categories = {
            CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN,
            CodexAdapterErrorCategory.TURN_INTERRUPT_NOT_ACTIVE,
            CodexAdapterErrorCategory.TURN_INTERRUPT_BUSY,
            CodexAdapterErrorCategory.TURN_INTERRUPT_REJECTED,
            CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN,
            CodexAdapterErrorCategory.THREAD_START_REJECTED,
            CodexAdapterErrorCategory.THREAD_START_UNKNOWN,
            CodexAdapterErrorCategory.THREAD_RESUME_REJECTED,
            CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN,
            CodexAdapterErrorCategory.TURN_START_REJECTED,
            CodexAdapterErrorCategory.TURN_START_UNKNOWN,
            CodexAdapterErrorCategory.APPROVAL_REQUEST_INVALID,
            CodexAdapterErrorCategory.APPROVAL_DECISION_INVALID,
            CodexAdapterErrorCategory.APPROVAL_OPERATION_BUSY,
            CodexAdapterErrorCategory.APPROVAL_PROTOCOL_TERMINAL,
            CodexAdapterErrorCategory.APPROVAL_RESPONSE_UNKNOWN,
        }
        self.assertTrue(categories.issubset(set(CodexAdapterErrorCategory)))
        source_errors = [
            ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_DELETE_UNKNOWN),
            ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_START_REJECTED),
            ThreadLifecycleError(CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN),
            TurnLifecycleError(CodexAdapterErrorCategory.TURN_INTERRUPT_UNKNOWN),
            TurnLifecycleError(CodexAdapterErrorCategory.TURN_START_REJECTED),
            ApprovalError(ApprovalErrorCategory.APPROVAL_RESPONSE_UNKNOWN),
            ProtocolRemoteError(409),
        ]
        normalized = [normalize_error(error) for error in source_errors]
        for error in normalized:
            self.assertIsInstance(error, CodexAdapterError)
            self.assertFalse(hasattr(error, "retryable"))
            self.assertFalse(hasattr(error, "safe_to_retry"))

    def test_identity_bounds_are_exact_and_nul_free(self):
        for value in ("x" * 512,):
            self.assertEqual(ThreadBinding("p", value).thread_id, value)
            self.assertEqual(TurnBinding("p", value, value).turn_id, value)
        for value in ("", "x" * 513, "x\0y"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ThreadLifecycleError):
                    ThreadBinding("p", value)
                with self.assertRaises(TurnLifecycleError):
                    TurnBinding("p", "thread", value)
        with self.assertRaises(TurnLifecycleError):
            TurnBinding("p", "thread", "")

    def test_startup_empty_turn_interrupt_path_is_not_public(self):
        with self.assertRaises(TurnLifecycleError):
            TurnBinding("p", "thread-P1-10", "")

    def test_diagnostic_surfaces_redact_content_and_private_paths(self):
        sentinels = (
            "PRIVATE_P1_10_PROMPT_MUST_NOT_LEAK",
            "PRIVATE_P1_10_REASONING_MUST_NOT_LEAK",
            "OPENAI_API_KEY=P1_10_SECRET",
            "/private/CODEX_HOME",
            "/private/thread.jsonl",
        )
        binding = TurnBinding("p", "thread-P1-10", "turn-P1-10")
        terminal = TurnTerminalResult(
            binding,
            TurnTerminalStatus.COMPLETED,
            (AgentMessageCompleted(1, "item-P1-10", sentinels[0]),),
        )
        surfaces = (
            repr(CodexAdapterError(CodexAdapterErrorCategory.INTERNAL)),
            repr(ThreadLifecycleError("remote text " + sentinels[3])),
            repr(TurnLifecycleError("remote text " + sentinels[1])),
            repr(ApprovalError("remote text " + sentinels[2])),
            repr(TurnInterruptResult(TurnInterruptStatus.CONFIRMED, binding, terminal)),
            repr(InboundServerRequest(1, "request-1", "applyPatchApproval", {"secret": sentinels[4]})),
        )
        for surface in surfaces:
            for sentinel in sentinels:
                self.assertNotIn(sentinel, surface)


if __name__ == "__main__":
    unittest.main()
