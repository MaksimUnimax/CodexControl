# P1.1 Codex stdio handshake implementation evidence

## Baseline and environment

- Architect baseline SHA: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Implementation branch: `impl-p1-1-codex-stdio-handshake-2026-09-04`.
- Installed executable: `/usr/local/bin/codex`.
- Installed version: `codex-cli 0.144.6`.

## Installed-schema evidence

- Exact command: `codex app-server generate-json-schema --out /tmp/codex-app-server-schema-0.144.6.AKb2Ma`.
- Full generated schema bundle source: `/tmp/codex-app-server-schema-0.144.6.AKb2Ma/codex_app_server_protocol.schemas.json`.
- SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- The generated JSON-RPC schemas define request fields `id`, `method`, `params`; successful response fields `id`, `result`; error response fields `id`, `error`; and notification fields `method`, optional `params`. They do not define a `jsonrpc` wire field.
- `RequestId` accepts an integer or string. This client emits monotonically increasing integer IDs, which are unique for its connection lifetime.
- The generated v1 initialize schema requires `params.clientInfo.name` and `params.clientInfo.version`, permits nullable `title`, and defines optional capability keys `experimentalApi`, `mcpServerOpenaiFormElicitation`, `optOutNotificationMethods`, and `requestAttestation`.
- The generated v1 initialize result requires `userAgent`, `codexHome`, `platformFamily`, and `platformOs`.
- The generated client notification schema defines `initialized` as `{ "method": "initialized" }` with no request ID or params.
- Installed `app-server --help` identifies `stdio://` as the default transport. Embedded installed-binary diagnostics identify JSON-RPC serialization followed by writing a newline to stdout; the implemented transport is therefore one UTF-8 JSON message per newline-delimited stdio line.

## Implemented files

- `src/codex_control/adapters/__init__.py`
- `src/codex_control/adapters/codex/__init__.py`
- `src/codex_control/adapters/codex/types.py`
- `src/codex_control/adapters/codex/protocol.py`
- `tests/fixtures/codex_app_server_0_144_6/initialize_protocol.json`
- `tests/unit/__init__.py`
- `tests/unit/test_codex_protocol.py`

The fixture is a minimal secret-free excerpt tied to the installed version and full-schema SHA; the generated schema itself remains only under `/tmp`.

## Verification

- `PYTHONPATH=src python3 -m unittest discover -s tests -v`: 20 tests passed.
- `PYTHONPATH=src python3 -m unittest tests.unit.test_codex_protocol -v`: 16 tests passed.
- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- `PYTHONPATH=src python3 -c 'import codex_control'`: passed.

The tests use an in-memory asynchronous line transport only. No app-server was launched, no Codex thread or business RPC was started, and no production service or configuration was changed.

## Later-slice facts not implemented

This implementation does not provide child-process supervision, capability probing beyond initialize schema facts, authenticated model discovery, thread/turn operations, approval handling, persistence, Telegram integration, or production runtime wiring.
