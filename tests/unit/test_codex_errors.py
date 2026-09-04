import unittest
from codex_control.adapters.codex.errors import *
from codex_control.adapters.codex.protocol import ProtocolFault, ProtocolRemoteError
from codex_control.adapters.codex.runtime import RuntimeErrorSafe
from codex_control.adapters.codex.subprocess_transport import SubprocessTransportError
from codex_control.adapters.codex.version_probe import VersionProbeError
from codex_control.adapters.codex.capabilities import CapabilityManifestError

class ErrorTests(unittest.TestCase):
    def test_protocol_and_remote_are_safe(self):
        self.assertEqual(normalize_error(ProtocolFault("raw")).category,CodexAdapterErrorCategory.PROTOCOL_FAULT)
        error=normalize_error(ProtocolRemoteError(42)); self.assertEqual(error.remote_code,42); self.assertNotIn("private",repr(error))
    def test_runtime_categories(self):
        for source,target in (("executable_invalid",CodexAdapterErrorCategory.CONFIGURATION),("profile_stopping",CodexAdapterErrorCategory.PROFILE_STOPPING),("manager_shutting_down",CodexAdapterErrorCategory.MANAGER_SHUTTING_DOWN),("unresolved_process",CodexAdapterErrorCategory.UNRESOLVED_PROCESS),("kill_reap_timeout",CodexAdapterErrorCategory.RUNTIME_SHUTDOWN_FAILURE)):
            self.assertEqual(normalize_error(RuntimeErrorSafe(source,"safe-profile")).category,target)
    def test_other_categories_and_redaction(self):
        self.assertEqual(normalize_error(SubprocessTransportError("x")).category,CodexAdapterErrorCategory.TRANSPORT_FAULT)
        self.assertEqual(normalize_error(VersionProbeError("unsupported_codex_version")).category,CodexAdapterErrorCategory.UNSUPPORTED_CODEX_VERSION)
        self.assertEqual(normalize_error(CapabilityManifestError("manifest_sha_invalid")).category,CodexAdapterErrorCategory.CAPABILITY_MANIFEST_INVALID)
        error=normalize_error(Exception("private secret /root/.codex")); self.assertEqual(error.category,CodexAdapterErrorCategory.INTERNAL); self.assertNotIn("private",str(error)); self.assertNotIn(".codex",repr(error)); self.assertFalse(hasattr(error,"retryable")); self.assertFalse(hasattr(error,"safe_to_retry"))
