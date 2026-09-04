# P1.3 capabilities and normalized errors evidence

## Baseline and installed schema facts

- Base SHA: `19fe0de2da8fc95bda733f6fb83539bbf8bb3d0b`.
- Branch: `impl-p1-3-capabilities-errors-2026-09-04`.
- Installed executable: `/usr/local/bin/codex`.
- Installed version command/result: `/usr/local/bin/codex --version` -> `codex-cli 0.144.6`.
- Schema generation command: `/usr/local/bin/codex app-server generate-json-schema --out /tmp/codex-p1-3-schema.1EUiMC`.
- Observed SHA-256 of `codex_app_server_protocol.schemas.json`: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- The observed SHA matched the established P1.1 SHA.

## Manifest facts

- Manifest format: `1`; Codex CLI version: `0.144.6`; framing: newline-delimited UTF-8 JSON messages.
- Client-to-app-server requests: `model/list`, `thread/start`, `thread/resume`, `thread/delete`, `turn/start`, `turn/interrupt`.
- Client-to-app-server notifications: `initialized`.
- App-server-to-client notifications: `item/agentMessage/delta`, `turn/completed`.
- Approval-related app-server-to-client requests: `item/commandExecution/requestApproval`, `item/fileChange/requestApproval`, `item/permissions/requestApproval`, `applyPatchApproval`, `execCommandApproval`.
- Recorded approval response schemas: `CommandExecutionRequestApprovalResponse`, `FileChangeRequestApprovalResponse`, `PermissionsRequestApprovalResponse`, `ApplyPatchApprovalResponse`, `ExecCommandApprovalResponse`.
- Installed schema support is represented separately from local implementation readiness. All future business capabilities are `PRESENT` in installed schema and `NOT_IMPLEMENTED` locally.

## Version probe and errors

- Fixed probe argv: `<configured absolute executable> --version`; process creation uses `asyncio.create_subprocess_exec` only.
- Version stdout limit: `4096` bytes. Timeout: `3.0` seconds. Terminate/kill cleanup waits are each bounded by `1.0` seconds.
- Allowed child environment names only: `HOME`, `PATH`, `LANG`, `LC_ALL`, `SSL_CERT_FILE`, `SSL_CERT_DIR`; no `CODEX_HOME` is set for the probe.
- Normalized categories: configuration, unsupported version, version-probe failure, invalid manifest, missing capability, runtime unavailable, profile stopping, manager shutdown, unresolved process, runtime shutdown failure, protocol fault, remote app-server error, transport fault, timeout, internal.
- The error taxonomy encodes **no automatic retry decision**.

## Files and verification

- Changed: adapter capability/error/version-probe modules, version-labelled JSON package resource, exports, package-data declaration, P1.3 unit tests, and this evidence.
- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_capabilities tests.unit.test_codex_errors tests.unit.test_codex_version_probe -v`: 14 passed.
- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_runtime -v`: 27 passed.
- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_protocol -v`: 16 passed.
- `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 61 passed.
- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- `PYTHONPATH=src python3 -c 'import codex_control'`: passed.
- A temporary `pip install --no-deps --target` isolated package-resource check loaded the JSON manifest successfully.

No Codex business RPC was sent, no production `CODEX_HOME` was used, no production service changed, and no architecture document changed.
