import copy, unittest
from codex_control.adapters.codex.capabilities import *

class CapabilityManifestTests(unittest.TestCase):
    def setUp(self): self.manifest=load_manifest()
    def test_installed_manifest_facts_and_directions(self):
        self.assertEqual(self.manifest.codex_cli_version,"0.144.6"); self.assertEqual(self.manifest.schema_sha256,SCHEMA_SHA256)
        self.assertIn("model/list",self.manifest.client_requests); self.assertIn("thread/start",self.manifest.client_requests); self.assertIn("thread/resume",self.manifest.client_requests); self.assertIn("thread/delete",self.manifest.client_requests); self.assertIn("turn/start",self.manifest.client_requests); self.assertIn("turn/interrupt",self.manifest.client_requests)
        self.assertIn("item/agentMessage/delta",self.manifest.server_notifications); self.assertIn("turn/completed",self.manifest.server_notifications)
        self.assertIn("item/commandExecution/requestApproval",self.manifest.server_requests); self.assertNotEqual(self.manifest.client_requests,self.manifest.server_requests)
        self.assertIn("CommandExecutionRequestApprovalResponse",self.manifest.approval_response_schemas)
    def test_future_capabilities_are_not_local_implementation(self):
        self.assertTrue(all(s.adapter_implementation is AdapterImplementation.NOT_IMPLEMENTED for s in self.manifest.capabilities.values()))
    def test_required_report_and_missing(self):
        report=self.manifest.check_required(REQUIRED_V1_CAPABILITIES); self.assertFalse(report.missing)
        altered=copy.deepcopy(self.manifest.capabilities); altered.pop(CodexCapability.TURN_START)
        report=CodexCapabilityManifest(self.manifest.manifest_format,self.manifest.codex_cli_version,self.manifest.schema_sha256,self.manifest.framing,self.manifest.client_requests,self.manifest.client_notifications,self.manifest.server_requests,self.manifest.server_notifications,self.manifest.approval_response_schemas,altered).check_required((CodexCapability.TURN_START,)); self.assertEqual(report.missing,(CodexCapability.TURN_START,))
    def test_malformed_rejected(self):
        raw={"manifest_format":1,"codex_cli_version":"0.144.6","schema_sha256":"x","framing":"x","wire":{},"capabilities":{}}
        with self.assertRaises(CapabilityManifestError): load_manifest_data(raw)
    def test_duplicate_wire_and_bad_reference_rejected(self):
        import json; from importlib import resources
        raw=json.loads(resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text())
        raw["wire"]["client_requests"].append("model/list")
        with self.assertRaises(CapabilityManifestError): load_manifest_data(raw)
        raw=json.loads(resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text()); raw["capabilities"]["MODEL_LIST"]["client_requests"]=["not/a/method"]
        with self.assertRaises(CapabilityManifestError): load_manifest_data(raw)
    def test_manifest_has_no_secret_fields(self):
        import json; from importlib import resources
        text=resources.files("codex_control.adapters.codex.manifests").joinpath("codex_0_144_6.json").read_text().lower()
        for term in ("token", "auth", "cookie", "account"): self.assertNotIn(term, text)
