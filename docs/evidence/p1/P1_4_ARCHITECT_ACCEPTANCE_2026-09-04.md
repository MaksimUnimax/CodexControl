# P1.4 architect acceptance — 2026-09-04

## Decision
P1.4 is architect-accepted.

Accepted implementation head:
`981b0c359f09e82354c50bb68eb3317d389a9c15`

Initial candidate requiring repair:
`c0cd876ecf91cb15f74faca93ba82490dd579f9c`

## Review summary
The initial implementation established the correct installed-0.144.6 `model/list` wire adapter, strict model/reasoning normalization, generation-scoped memory cache and single-flight refresh semantics, but its raw response bound was applied only after hidden filtering and several independent cache/concurrency contracts lacked explicit proof.

The accepted repair added a raw per-page bound of 100 entries before normalization/filtering and supplied deterministic proof for simultaneous cache misses, simultaneous forced refresh, all-waiter cancellation, failed-miss recovery, multi-generation cache retention, hidden selection rejection, case-sensitive IDs, catalog-error normalization and implementation-readiness state.

## Accepted invariants
- `model/list` runtime data is the product catalog authority; bundled debug models are not used as product data.
- Model `id` and exact wire `model` values remain distinct.
- Supported reasoning efforts and default reasoning effort come from runtime data and are never globally guessed.
- Hidden models are excluded from the normal selectable catalog without name heuristics.
- Raw response pages are bounded to 100 entries before normalization/filtering; selectable complete catalogs are bounded to 512 models and pagination to 32 pages.
- Catalogs are complete/atomic: failures and partial pagination are never cached or returned as valid catalogs.
- Cache key is `(profile_id, runtime_generation)` with 60-second monotonic TTL; historical generation entries are purged and late old-generation results cannot install current cache.
- Same-key misses and forced refreshes are single-flight. Caller cancellation does not cancel the shared read-only refresh.
- A failed refresh clears in-flight bookkeeping and does not poison later attempts. A failed forced refresh does not overwrite an unexpired prior catalog.
- Hidden models cannot be selected; model-ID matching is exact and case-sensitive; display names are not request identities.
- `ModelCatalogError` and normalized adapter errors remain bounded, payload-free and encode no retry decision.
- Only `MODEL_LIST` is locally `IMPLEMENTED`; all other P1 capabilities remain `NOT_IMPLEMENTED`.
- No real authenticated `model/list`, production `CODEX_HOME`, thread, production service or architecture file was changed during P1.4.

## Verification evidence
Codex reported the accepted repair suites as: P1.4 catalog 18 tests, errors 12, capabilities 17, full discovery 116, plus P1.1–P1.3 focused regressions and compile/import checks. The architect independently reviewed the GitHub diff, implementation, fixture, evidence and repaired concurrency/bounds tests before acceptance.

P1.5 may proceed only through a new architect-issued implementation slice.
