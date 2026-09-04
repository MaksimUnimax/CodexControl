import unittest
from codex_control.adapters.codex.errors import *
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.approvals import ApprovalError, ApprovalErrorCategory
from codex_control.adapters.codex.runtime import RuntimeErrorSafe
from codex_control.adapters.codex.subprocess_transport import SubprocessTransportError
from codex_control.adapters.codex.version_probe import VersionProbeError
from codex_control.adapters.codex.capabilities import CapabilityManifestError
from codex_control.adapters.codex.model_catalog import ModelCatalogError
from codex_control.adapters.codex.thread_lifecycle import ThreadLifecycleError
from codex_control.adapters.codex.turn_lifecycle import TurnLifecycleError

class ErrorTests(unittest.TestCase):
    def test_approval_errors_are_finite_and_normalization_is_total(self):
        for category in ApprovalErrorCategory:
            self.assertEqual(normalize_error(ApprovalError(category)).category, CodexAdapterErrorCategory(category.value))
        private="PRIVATE /root/secret OPENAI_API_KEY=MUST_NOT_LEAK"
        error=ApprovalError(private)
        normalized=normalize_error(error)
        self.assertEqual(normalized.category, CodexAdapterErrorCategory.APPROVAL_REQUEST_INVALID)
        self.assertNotIn(private, str(error)+repr(error)+str(normalized)+repr(normalized))
        self.assertFalse(hasattr(normalized,"retryable")); self.assertFalse(hasattr(normalized,"safe_to_retry"))
    def test_protocol_and_remote_are_safe(self):
        self.assertEqual(normalize_error(ProtocolFault("raw")).category, CodexAdapterErrorCategory.PROTOCOL_FAULT)
        self.assertEqual(normalize_error(ProtocolRemoteError(42)).remote_code, 42)
    def test_runtime_categories(self):
        for source, target in (("executable_invalid", CodexAdapterErrorCategory.CONFIGURATION), ("profile_stopping", CodexAdapterErrorCategory.PROFILE_STOPPING), ("manager_shutting_down", CodexAdapterErrorCategory.MANAGER_SHUTTING_DOWN), ("unresolved_process", CodexAdapterErrorCategory.UNRESOLVED_PROCESS), ("kill_reap_timeout", CodexAdapterErrorCategory.RUNTIME_SHUTDOWN_FAILURE)):
            self.assertEqual(normalize_error(RuntimeErrorSafe(source, "safe-profile")).category, target)
    def test_manifest_unsupported_version_normalizes_dedicated_category(self):
        self.assertEqual(normalize_error(CapabilityManifestError("unsupported_codex_version")).category, CodexAdapterErrorCategory.UNSUPPORTED_CODEX_VERSION)
    def test_probe_unsupported_version_normalizes_dedicated_category(self):
        self.assertEqual(normalize_error(VersionProbeError("unsupported_codex_version")).category, CodexAdapterErrorCategory.UNSUPPORTED_CODEX_VERSION)
    def test_manifest_version_mismatch_is_invalid_manifest(self):
        self.assertEqual(normalize_error(CapabilityManifestError("manifest_version_mismatch")).category, CodexAdapterErrorCategory.CAPABILITY_MANIFEST_INVALID)
    def test_manifest_sha_mismatch_is_invalid_manifest(self):
        self.assertEqual(normalize_error(CapabilityManifestError("manifest_sha_mismatch")).category, CodexAdapterErrorCategory.CAPABILITY_MANIFEST_INVALID)
    def test_probe_ownership_categories_are_safe_diagnostics(self):
        self.assertEqual(normalize_error(VersionProbeError("version_probe_cleanup_unresolved")).category, CodexAdapterErrorCategory.VERSION_PROBE_FAILURE)
        self.assertEqual(normalize_error(VersionProbeError("version_probe_busy")).category, CodexAdapterErrorCategory.VERSION_PROBE_FAILURE)
        self.assertEqual(normalize_error(VersionProbeError("version_probe_spawn_unresolved")).category, CodexAdapterErrorCategory.VERSION_PROBE_FAILURE)
    def test_spawn_timeout_normalizes_to_timeout_without_retry_fields(self):
        error = normalize_error(VersionProbeError("version_probe_spawn_timeout"))
        self.assertEqual(error.category, CodexAdapterErrorCategory.TIMEOUT)
        self.assertFalse(hasattr(error, "retryable")); self.assertFalse(hasattr(error, "safe_to_retry"))
    def test_cleanup_error_redacts_stderr_and_environment(self):
        error = normalize_error(VersionProbeError("version_probe_cleanup_unresolved"))
        rendered = str(error) + repr(error)
        self.assertNotIn("private stderr", rendered); self.assertNotIn("OPENAI_API_KEY=secret", rendered)
    def test_unknown_exception_text_is_redacted(self):
        error = normalize_error(Exception("private secret /root/.codex"))
        self.assertEqual(error.category, CodexAdapterErrorCategory.INTERNAL)
        self.assertNotIn("private", str(error) + repr(error))
    def test_no_normalized_error_encodes_retry_decision(self):
        for error in (normalize_error(SubprocessTransportError("x")), normalize_error(VersionProbeError("version_probe_busy")), normalize_error(CapabilityManifestError("manifest_sha_mismatch"))):
            self.assertFalse(hasattr(error, "retryable")); self.assertFalse(hasattr(error, "safe_to_retry")); self.assertNotIn("retry", str(error) + repr(error))

    def test_model_catalog_errors_normalize_and_redact_payloads_without_retry_fields(self):
        cases = (
            ("model_not_available", CodexAdapterErrorCategory.MODEL_NOT_AVAILABLE),
            ("reasoning_effort_unsupported", CodexAdapterErrorCategory.REASONING_EFFORT_UNSUPPORTED),
            ("catalog_response_invalid", CodexAdapterErrorCategory.MODEL_CATALOG_INVALID),
            ("catalog_limit_exceeded", CodexAdapterErrorCategory.MODEL_CATALOG_INVALID),
            ("pagination_invalid", CodexAdapterErrorCategory.MODEL_CATALOG_INVALID),
        )
        for source, target in cases:
            with self.subTest(source=source):
                error = normalize_error(ModelCatalogError(source))
                self.assertEqual(error.category, target)
                self.assertFalse(hasattr(error, "retryable"))
                self.assertFalse(hasattr(error, "safe_to_retry"))
        raw_payload = "PRIVATE_MODEL_DESCRIPTION_MUST_NOT_APPEAR"
        source = ModelCatalogError(raw_payload)
        self.assertNotIn(raw_payload, str(source) + repr(source))
        self.assertEqual(normalize_error(source).category, CodexAdapterErrorCategory.MODEL_CATALOG_INVALID)

    def test_thread_lifecycle_errors_normalize_exactly_and_redact_unknown_input(self):
        categories = (
            CodexAdapterErrorCategory.THREAD_REQUEST_INVALID,
            CodexAdapterErrorCategory.THREAD_PRECONDITION_CHANGED,
            CodexAdapterErrorCategory.THREAD_OPERATION_BUSY,
            CodexAdapterErrorCategory.THREAD_START_REJECTED,
            CodexAdapterErrorCategory.THREAD_START_UNKNOWN,
            CodexAdapterErrorCategory.THREAD_RESUME_REJECTED,
            CodexAdapterErrorCategory.THREAD_RESUME_UNKNOWN,
        )
        for category in categories:
            with self.subTest(category=category):
                normalized = normalize_error(ThreadLifecycleError(category))
                self.assertEqual(normalized.category, category)
                self.assertFalse(hasattr(normalized, "retryable"))
                self.assertFalse(hasattr(normalized, "safe_to_retry"))
        unsafe = ThreadLifecycleError("PRIVATE /root/secret")
        normalized = normalize_error(unsafe)
        rendered = str(unsafe) + repr(unsafe) + str(normalized) + repr(normalized)
        self.assertEqual(normalized.category, CodexAdapterErrorCategory.THREAD_REQUEST_INVALID)
        self.assertNotIn("PRIVATE /root/secret", rendered)

    def test_turn_lifecycle_errors_normalize_exactly(self):
        for category in (CodexAdapterErrorCategory.TURN_REQUEST_INVALID, CodexAdapterErrorCategory.TURN_PRECONDITION_CHANGED, CodexAdapterErrorCategory.TURN_OPERATION_BUSY, CodexAdapterErrorCategory.TURN_START_REJECTED, CodexAdapterErrorCategory.TURN_START_UNKNOWN, CodexAdapterErrorCategory.TURN_STREAM_UNKNOWN, CodexAdapterErrorCategory.TURN_TERMINAL_FAILED):
            normalized = normalize_error(TurnLifecycleError(category))
            self.assertEqual(normalized.category, category)
            self.assertFalse(hasattr(normalized, "retryable")); self.assertFalse(hasattr(normalized, "safe_to_retry"))
        raw = "PRIVATE /root/secret PRIVATE_USER_PROMPT_MUST_NOT_LEAK"
        unsafe = TurnLifecycleError(raw)
        normalized = normalize_error(unsafe)
        self.assertEqual(unsafe.category, CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        self.assertEqual(normalized.category, CodexAdapterErrorCategory.TURN_REQUEST_INVALID)
        self.assertNotIn(raw, str(unsafe) + repr(unsafe) + str(normalized) + repr(normalized))
        self.assertFalse(hasattr(normalized, "retryable")); self.assertFalse(hasattr(normalized, "safe_to_retry"))
