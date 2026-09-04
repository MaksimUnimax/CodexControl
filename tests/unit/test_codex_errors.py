import unittest
from codex_control.adapters.codex.errors import *
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.runtime import RuntimeErrorSafe
from codex_control.adapters.codex.subprocess_transport import SubprocessTransportError
from codex_control.adapters.codex.version_probe import VersionProbeError
from codex_control.adapters.codex.capabilities import CapabilityManifestError

class ErrorTests(unittest.TestCase):
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
