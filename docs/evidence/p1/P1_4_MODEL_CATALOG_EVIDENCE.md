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

## Architect repair pass

- Rejected candidate: `c0cd876ecf91cb15f74faca93ba82490dd579f9c`.
- Raw response pages are bounded before normalization or hidden filtering by `MAX_MODEL_LIST_PAGE_ITEMS = MODEL_LIST_PAGE_SIZE = 100`; an oversized page fails with `catalog_limit_exceeded` and is not truncated.
- Test-only generated entries prove a raw page of 100 valid entries is accepted, while 101 visible entries and 101 hidden entries each fail closed, do not populate cache, and do not render the test payload description.
- Event-gated tests prove two simultaneous forced refresh callers use one `model/list` sequence, share the completed immutable catalog identity, and clear the in-flight registry.
- A separate event-gated five-caller cache-miss test proves one sequence, one in-flight entry, one installed cache entry, and one shared completed catalog identity.
- The all-waiters-cancel test proves cancelled public callers do not cancel the owned refresh; it completes, caches successfully, clears in-flight bookkeeping, and a later normal caller uses the cached result without another request.
- The failed-miss test proves a failing first fetch leaves no cache or same-key in-flight entry; a later explicit get performs one new successful sequence and caches it.
- The multi-generation test covers generations 1 through 5 and proves only generation 5 remains for the profile, with no older completed cache/in-flight bookkeeping, while another profile's independent cache remains.
- Explicit selection tests prove hidden model IDs fail both descriptor and wire lookup, and model ID lookup is case-sensitive.
- Focused error tests prove `ModelCatalogError` category normalization, redaction of arbitrary constructor payload text, and absence of automatic retry fields.
- Manifest readiness test proves `MODEL_LIST` is `IMPLEMENTED` and every other `CodexCapability` is `NOT_IMPLEMENTED`.
- Final counts: P1.4 catalog 18; P1.4 errors 12; P1.4 capabilities 17; version probe 22; runtime 27; protocol 16; full discovery 116. `compileall` and package import passed.
