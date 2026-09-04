# P1.4 model catalog implementation evidence

- Base SHA: `384e05b6e45c1fa4493d325e1585eea0e25116c4`; branch: `impl-p1-4-model-catalog-2026-09-04`.
- Installed Codex checked read-only at `/usr/local/bin/codex`: `codex-cli 0.144.6`.
- Schema command: `/usr/local/bin/codex app-server generate-json-schema --out <new /tmp/codexcontrol-p14-schema.* directory>`.
- Observed SHA-256 of `codex_app_server_protocol.schemas.json`: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466` (matches authority).

## Installed wire facts

- Method is `model/list`. `ModelListParams` fields are `cursor` (`string|null`), `includeHidden` (`boolean|null`), and `limit` (`uint32`, minimum 0, nullable).
- Requests use `includeHidden: false` and `limit: 100`; later pages add `cursor` from `nextCursor`.
- `ModelListResponse.data` is the collection; `nextCursor` is `string|null` and null ends pagination.
- Model source fields are `id`, `model`, `displayName`, `supportedReasoningEfforts[].reasoningEffort`, `defaultReasoningEffort`, `isDefault`, and `hidden`. The schema also requires descriptions, which are type-checked then discarded.
- `id` and `model` are preserved separately. Later selection resolves exact `model` as the wire value.

## Behavior and bounds

- Complete immutable catalogs are memory-only, TTL 60.0 seconds using injected monotonic clock. Key: `(profile_id, runtime_generation)`.
- Bounds: pages 32; models 512; model ID/wire model/display label 256 chars; efforts/model 16; effort 64 chars; cursor 4096 chars.
- Newer observed runtime generations remove older completed entries and old in-flight registry entries; a late old-generation completion cannot install a cache entry.
- Same-key misses/refreshes share one task. Waiters use shielding, so caller cancellation does not cancel the read-only refresh. Completed task outcomes are consumed and in-flight entries clear on terminal outcome.
- Only successful, fully validated complete pagination is cached. Unknown model and unsupported effort fail closed. No descriptions or arbitrary response fields are retained.
- Only `MODEL_LIST` was changed to local `IMPLEMENTED`; all other manifest capabilities remain `NOT_IMPLEMENTED`.

## Verification

- Direct P1.4 suite: 8 tests, all passed.
- P1.3 focused regressions: version probe 22, errors 11, capabilities 16; P1.2 runtime 27; P1.1 protocol 16, all passed.
- Full discovery: 104 tests passed. `compileall` and `import codex_control` passed.
- No real `model/list`, production `CODEX_HOME`, production Codex business operation, or production service was used or changed. No architecture-owned document was changed.
