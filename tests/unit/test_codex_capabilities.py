import copy
import json
import os
import tempfile
import unittest
from importlib import resources
from codex_control.adapters.codex.capabilities import *

def packaged_raw():
    return json.loads(resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text())

class CapabilityManifestTests(unittest.TestCase):
    def setUp(self): self.manifest = load_manifest("0.144.6")
    def test_packaged_manifest_loads_with_embedded_authority(self):
        self.assertEqual(self.manifest.codex_cli_version, "0.144.6")
        self.assertEqual(self.manifest.schema_sha256, SCHEMA_SHA256)
    def test_foreign_embedded_version_is_rejected_by_authority_layer(self):
        raw = packaged_raw(); raw["codex_cli_version"] = "0.144.7"
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_version_mismatch"):
            validate_manifest_authority(load_manifest_data(raw), "0.144.6")
    def test_foreign_valid_sha_is_rejected_by_authority_layer(self):
        raw = packaged_raw(); raw["schema_sha256"] = "a" * 64
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_sha_mismatch"):
            validate_manifest_authority(load_manifest_data(raw), "0.144.6")
    def test_unsupported_requested_version_is_rejected(self):
        with self.assertRaisesRegex(CapabilityManifestError, "unsupported_codex_version"): load_manifest("0.144.7")
    def test_unknown_format_is_rejected(self):
        raw = packaged_raw(); raw["manifest_format"] = 2
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_format_invalid"): load_manifest_data(raw)
    def test_invalid_sha_syntax_is_rejected(self):
        raw = packaged_raw(); raw["schema_sha256"] = "not-a-sha"
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_sha_invalid"): load_manifest_data(raw)
    def test_duplicate_wire_method_is_rejected(self):
        raw = packaged_raw(); raw["wire"]["client_requests"].append("model/list")
        with self.assertRaisesRegex(CapabilityManifestError, "duplicate_wire_method"): load_manifest_data(raw)
    def test_absent_wire_reference_is_rejected(self):
        raw = packaged_raw(); raw["capabilities"]["MODEL_LIST"]["client_requests"] = ["missing/method"]
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_capability_reference_invalid"): load_manifest_data(raw)
    def test_unknown_logical_capability_is_rejected(self):
        raw = packaged_raw(); raw["capabilities"]["FUTURE"] = raw["capabilities"].pop("MODEL_LIST")
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_capability_unknown"): load_manifest_data(raw)
    def test_missing_logical_capability_is_rejected_structurally(self):
        raw = packaged_raw(); raw["capabilities"].pop("TURN_START")
        with self.assertRaisesRegex(CapabilityManifestError, "manifest_capabilities_invalid"): load_manifest_data(raw)
    def test_required_report_identifies_missing_on_explicit_representation(self):
        altered = copy.deepcopy(self.manifest.capabilities); altered.pop(CodexCapability.TURN_START)
        report = CodexCapabilityManifest(self.manifest.manifest_format, self.manifest.codex_cli_version, self.manifest.schema_sha256, self.manifest.framing, self.manifest.client_requests, self.manifest.client_notifications, self.manifest.server_requests, self.manifest.server_notifications, self.manifest.approval_response_schemas, altered).check_required((CodexCapability.TURN_START,))
        self.assertEqual(report.missing, (CodexCapability.TURN_START,))
    def test_directional_facts_include_completed_agent_messages(self):
        self.assertIn("item/agentMessage/delta", self.manifest.server_notifications)
        self.assertIn("item/completed", self.manifest.server_notifications)
        self.assertIn("turn/completed", self.manifest.server_notifications)
        self.assertNotEqual(self.manifest.client_requests, self.manifest.server_requests)
    def test_exact_installed_approval_server_request_directionality(self):
        expected = ("item/commandExecution/requestApproval", "item/fileChange/requestApproval", "item/permissions/requestApproval", "applyPatchApproval", "execCommandApproval")
        self.assertEqual(self.manifest.server_requests, expected)
        self.assertEqual(self.manifest.capabilities[CodexCapability.APPROVAL_SERVER_REQUESTS].server_requests, expected)
        self.assertTrue(set(expected).isdisjoint(self.manifest.client_requests))
        self.assertTrue(set(expected).isdisjoint(self.manifest.server_notifications))
    def test_exact_installed_approval_response_schemas(self):
        expected = ("CommandExecutionRequestApprovalResponse", "FileChangeRequestApprovalResponse", "PermissionsRequestApprovalResponse", "ApplyPatchApprovalResponse", "ExecCommandApprovalResponse")
        self.assertEqual(self.manifest.approval_response_schemas, expected)
        self.assertEqual(self.manifest.capabilities[CodexCapability.APPROVAL_RESPONSE_SCHEMA].approval_response_schemas, expected)
    def test_package_resource_loads_outside_repository_cwd(self):
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try: self.assertEqual(load_manifest().schema_sha256, SCHEMA_SHA256)
            finally: os.chdir(original)
    def test_manifest_has_no_secret_fields(self):
        text = resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text().lower()
        for term in ("token", "auth", "cookie", "account"): self.assertNotIn(term, text)
    def test_p1_9_delete_and_prior_capabilities_are_locally_implemented(self):
        manifest = load_manifest()
        implemented = {CodexCapability.MODEL_LIST, CodexCapability.THREAD_START, CodexCapability.THREAD_RESUME, CodexCapability.THREAD_DELETE, CodexCapability.TURN_START, CodexCapability.TURN_INTERRUPT, CodexCapability.AGENT_MESSAGE_EVENTS, CodexCapability.TURN_TERMINAL_EVENTS, CodexCapability.APPROVAL_SERVER_REQUESTS, CodexCapability.APPROVAL_RESPONSE_SCHEMA}
        for capability in CodexCapability:
            if capability in implemented:
                self.assertIs(manifest.capabilities[capability].adapter_implementation, AdapterImplementation.IMPLEMENTED)
            else:
                self.assertIs(manifest.capabilities[capability].adapter_implementation, AdapterImplementation.NOT_IMPLEMENTED)

    def test_p1_9_exact_capability_readiness(self):
        manifest = load_manifest()
        implemented = {
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
        not_implemented = set()
        for capability in implemented:
            self.assertIs(manifest.capabilities[capability].adapter_implementation, AdapterImplementation.IMPLEMENTED)
        for capability in not_implemented:
            self.assertIs(manifest.capabilities[capability].adapter_implementation, AdapterImplementation.NOT_IMPLEMENTED)
        for capability in CodexCapability:
            if capability in implemented or capability in not_implemented:
                continue
            self.assertIs(manifest.capabilities[capability].adapter_implementation, AdapterImplementation.NOT_IMPLEMENTED)
