# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted implementation: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted implementation after two repair reviews: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted implementation after three repair reviews: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted implementation after one repair review: `981b0c359f09e82354c50bb68eb3317d389a9c15`.

## P1.4 accepted model-catalog facts
- Product model data comes from authenticated runtime `model/list`, never from a hardcoded or bundled debug catalog.
- Installed `model/list` request fields are `cursor`, `includeHidden`, and `limit`; P1.4 uses `includeHidden: false` and `limit: 100`.
- Response collection is `data`; pagination cursor is `nextCursor`.
- Model record identity `id` and exact future request model value `model` remain distinct.
- User-selectable metadata is normalized from `displayName`, `supportedReasoningEfforts[].reasoningEffort`, `defaultReasoningEffort`, `isDefault`, and `hidden`; descriptions/unknown response fields are not retained.
- Catalog input is bounded before hidden filtering at 100 raw entries/page; pagination is bounded to 32 pages and selectable catalog size to 512 models.
- Catalog cache is memory-only, TTL 60 seconds, keyed by `(profile_id, runtime_generation)`, and older generations cannot become current cache after a newer generation is observed.
- Same-key misses and forced refreshes are single-flight; caller cancellation does not cancel the shared read-only refresh; failed refreshes do not poison in-flight state or overwrite a valid old cache entry.
- Hidden models are not selectable; model IDs are case-sensitive; unknown models and unsupported reasoning efforts fail closed.
- Only `MODEL_LIST` is locally `IMPLEMENTED`; every other P1 capability remains `NOT_IMPLEMENTED`.

## Execution authority
Codex must not self-start work from this document.

Only **P1.5 — thread start/resume adapter** is eligible for the next explicit implementation prompt.

P1.5 does not authorize turn execution, approval handling, interrupt, hard delete, Telegram, SQLite, systemd, production deployment, or architecture/roadmap edits.

P1.5 must use fake/simulated READY runtimes for tests. Real production-profile thread creation/resume is reserved for P7 unless an architect prompt explicitly authorizes an isolated disposable acceptance operation.
