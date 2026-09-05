import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from codex_control.adapters.codex.capabilities import AdapterImplementation, load_manifest


CODEX = "/usr/local/bin/codex"
VERSION = "0.144.6"
SCHEMA_SHA256 = "40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466"
FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "codex_app_server_0_144_6"


def isolated_environment(home):
    return {
        "CODEX_HOME": str(home),
        "HOME": str(home),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "LANG": "C.UTF-8",
    }


def run_read_only(*args, home):
    return subprocess.run(
        [CODEX, *args],
        env=isolated_environment(home),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
    )


def walk(value, key=None):
    yield key, value
    if isinstance(value, dict):
        for child_key, child in value.items():
            yield from walk(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child, key)


def schema_index(schema):
    definitions = set()
    refs = set()
    enum_strings = set()

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "$ref" and isinstance(child, str):
                    refs.add(child.rsplit("/", 1)[-1])
                if key == "enum" and isinstance(child, list):
                    enum_strings.update(item for item in child if isinstance(item, str))
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    # The observed aggregate is a root schema with a ``definitions`` map;
    # its ``v2`` namespace is itself a second definition map.  Index only
    # those map keys, while walking the whole document for refs/enums.
    root_definitions = schema.get("definitions")
    if not isinstance(root_definitions, dict):
        raise AssertionError("generated schema has no definitions map")
    definitions.update(root_definitions)
    for namespace, value in root_definitions.items():
        if namespace == "v2" and isinstance(value, dict):
            definitions.update(value)
    visit(schema)
    return definitions, refs, enum_strings


def fixture_schema_names(value):
    names = set()
    for key, child in walk(value):
        if not isinstance(child, str):
            continue
        if key in {"request_schema_name", "response_schema_name", "thread_deleted_notification_schema", "response"}:
            names.add(child)
        elif key and key.endswith("_schema_ref"):
            names.add(child.rsplit("/", 1)[-1])
    return names


def fixture_methods(value):
    methods = set()
    for key, child in walk(value):
        if key == "accepted_methods" or key == "server_requests":
            if isinstance(child, list):
                methods.update(item for item in child if isinstance(item, str))
        elif key and key.endswith("_method") and isinstance(child, str):
            methods.add(child)
        elif key == "method" and isinstance(child, str):
            methods.add(child)
    return methods


class P110T2Acceptance(unittest.TestCase):
    def test_installed_version_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_read_only("--version", home=Path(directory) / "codex-home")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "codex-cli 0.144.6")

    def test_app_server_help_exposes_stdio_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_read_only("app-server", "--help", home=Path(directory) / "codex-home")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--stdio", result.stdout)
        self.assertIn("stdio://", result.stdout)

    def test_fresh_schema_has_exact_sha_and_fixture_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            output = Path(directory) / "schema-output"
            output.mkdir()
            result = run_read_only("app-server", "generate-json-schema", "--out", str(output), home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            aggregate = output / "codex_app_server_protocol.schemas.json"
            self.assertTrue(aggregate.is_file())
            raw = aggregate.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), SCHEMA_SHA256)
            schema = json.loads(raw)

        definitions, refs, enum_strings = schema_index(schema)
        fixtures = sorted(FIXTURE_ROOT.glob("*.json"))
        self.assertEqual([path.name for path in fixtures], [
            "approval_protocol.json",
            "initialize_protocol.json",
            "model_list_protocol.json",
            "server_request_protocol.json",
            "thread_delete_protocol.json",
            "thread_resume_protocol.json",
            "thread_start_protocol.json",
            "turn_events_protocol.json",
            "turn_interrupt_protocol.json",
            "turn_start_protocol.json",
        ])
        all_fixture_schema_names = set()
        all_fixture_methods = set()
        for path in fixtures:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            version = fixture["codex_version"]
            self.assertIn(version, {VERSION, "codex-cli " + VERSION})
            self.assertEqual(fixture["schema_sha256"], SCHEMA_SHA256)
            all_fixture_schema_names.update(fixture_schema_names(fixture))
            all_fixture_methods.update(fixture_methods(fixture))

        manifest = load_manifest()
        all_fixture_methods.update(manifest.client_requests)
        all_fixture_methods.update(manifest.client_notifications)
        all_fixture_methods.update(manifest.server_requests)
        all_fixture_methods.update(manifest.server_notifications)
        self.assertTrue(all_fixture_methods.issubset(enum_strings), sorted(all_fixture_methods - enum_strings))
        self.assertTrue(all_fixture_schema_names.issubset(definitions), sorted(all_fixture_schema_names - definitions))
        self.assertTrue({
            "initialize",
            "model/list",
            "thread/start",
            "thread/resume",
            "thread/delete",
            "turn/start",
            "turn/interrupt",
            "item/agentMessage/delta",
            "item/completed",
            "turn/completed",
            "thread/deleted",
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
            "item/permissions/requestApproval",
            "applyPatchApproval",
            "execCommandApproval",
        }.issubset(enum_strings))
        self.assertTrue({
            "ThreadDeleteParams",
            "ThreadDeleteResponse",
            "ThreadDeletedNotification",
            "TurnInterruptParams",
            "TurnInterruptResponse",
        }.issubset(definitions))

    def test_manifest_is_version_bound_ready_and_schema_referenced(self):
        manifest = load_manifest()
        self.assertEqual(manifest.codex_cli_version, VERSION)
        self.assertEqual(manifest.schema_sha256, SCHEMA_SHA256)
        self.assertTrue(all(
            status.adapter_implementation is AdapterImplementation.IMPLEMENTED
            for status in manifest.capabilities.values()
        ))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "schema-output"
            output.mkdir()
            result = run_read_only(
                "app-server", "generate-json-schema", "--out", str(output),
                home=Path(directory) / "codex-home",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            schema = json.loads((output / "codex_app_server_protocol.schemas.json").read_text(encoding="utf-8"))
        definitions, refs, enum_strings = schema_index(schema)
        for status in manifest.capabilities.values():
            self.assertTrue(set(status.client_requests + status.client_notifications + status.server_requests + status.server_notifications).issubset(enum_strings))
            self.assertTrue(set(status.approval_response_schemas).issubset(definitions))


if __name__ == "__main__":
    unittest.main()
