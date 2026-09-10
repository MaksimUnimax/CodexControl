# Current work authority

Date: 2026-09-10

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority remains `codex-cli 0.144.6`; generated app-server schema SHA-256 remains `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete at their accepted boundaries. P6 final accepted commit remains `0409ad4a0744159aad875a5ddea4deaf1181699e`; no live Telegram or production deployment acceptance has occurred.
- Historical storage schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Historical schema-v2 migration SHA-256 remains `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- Accepted schema-v3 migration ID is `0003_confirmed_pending_storage` with SHA-256 `cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`.
- Current schema is v4. Accepted v4 migration ID is `0004_delete_local_containment` with SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.

## Rejected original P7

Original real P7 under ADR-0042 remains **REJECTED / ARCHITECTURE BLOCKED**. Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; no retry/read/list occurred. Final forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL` with five synthetic material-marker matches. Issue #38 remains historical blocker evidence.

## P7.C1 — COMPLETE / architect accepted

Accepted discovery: `a9900471d0599be21b1a1834301c4421d95acb29`.

Acceptance: `docs/evidence/p7c1/P7C1_ARCHITECT_ACCEPTANCE_2026-09-09.md`.

C1 proved residual storage provenance and exact installed 0.144.6 controls: `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, `history.persistence=none`; session/rollout remains under `CODEX_HOME`.

## P7.C2 — COMPLETE / architect accepted

Accepted implementation lineage: `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc` -> `80673db644962b0cc5b1a388d64cb5902bd4f46c`.

Acceptance: `docs/evidence/p7c2/P7C2_ARCHITECT_ACCEPTANCE_2026-09-09.md`.

C2 introduced schema-v3 `DELETE_CONFIRMED_PENDING_STORAGE`: exact upstream confirmation is persisted before local purge/tombstone; full binding remains retained; `DELETING` restart remains ambiguity -> `DELETE_UNKNOWN`; confirmed-pending/UNKNOWN never redispatch external delete.

## P7.C3 — COMPLETE / architect accepted

Accepted lineage: `0654ee1cbd70d4d6a6d5a317e948d2f08b2c081f` -> `a549e6f1f295a37f14a7833ede0233d94745555a` -> `2a6c5d8f2ed0980c4c7bc32cec471002432e1c9d` -> `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`.

Accepted implementation tree: `13eea89362694da594bb2b717c037980b0df446f`.

Acceptance: `docs/evidence/p7c3/P7C3_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

C3 owns explicit persistent `CODEX_HOME` + distinct isolated state root, exact 0.144.6 per-child-generation authority, descriptor/no-follow protected-path authority, exact SQLite/log/history routing, exclusive profile reservation/quiescence and descriptor-bounded root lifecycle.

## ADR-0044

ADR-0044 freezes durable local containment and C4 cleanup semantics:

`docs/adr/0044-durable-local-containment-and-p7c4-cleanup.md`.

`DELETE_UNKNOWN` always retains `OFFICIAL_DELETE_AUTHORITY=UNKNOWN`; successful isolated local containment is a separate durable fact and never a tombstone or upstream reconciliation.

## P7.C4 — COMPLETE / architect accepted

Accepted lineage:

- architect base: `7572df1e95e79f3292489b096e8b0a22789df1e5`;
- initial candidate: `70cdf0edc3f319c0254313eabc5d3c56c2f9ef16`;
- first repair: `fe646af1487d13571337e605641ecc86dbb1f6c7`;
- second repair / accepted implementation: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`;
- accepted implementation tree: `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.

Acceptance:

`docs/evidence/p7c4/P7C4_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

Accepted C4 authority includes:

- additive schema-v4 `delete_storage_containment` metadata for UNKNOWN local containment;
- historical v1/v2/v3 schema authorities unchanged;
- exact `DELETE_UNKNOWN` state/version/binding retained after local containment;
- confirmed cleanup order `reserve -> shutdown -> quiesce -> reset isolated payload -> sessions/history scan -> finalize -> release`;
- local failures keep confirmed-pending/binding and process-local quarantine;
- UNKNOWN containment never finalizes or creates a tombstone and retains quarantine;
- persistent scanner is descriptor/no-follow, content-silent, finite, opened-FD-bound and excludes credentials/configuration;
- isolated reset preserves the ownership marker and top-level `sqlite/`/`logs/` envelope while clearing all payload descendants, making mid-reset crash retryable;
- C4 coordinator proves its actual controller `SqliteStorage` matches the protected `controller_db_path` before destructive local work;
- post-commit finalizer truth cannot regress to pending;
- recovery outcomes are distinct and all pre-existing delete recovery is local-only/no-retry.

Final executor report: `1050` tests, `0` skipped, `0` failures, `0` errors; all real Codex/Telegram/credential/production-effect counters zero.

## Current slice

**P7.C5 — NEXT / FAKE HARD-DELETE ACCEPTANCE CONTRACT FROZEN.**

Frozen contract:

`docs/evidence/p7c5/P7C5_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`.

C5 is proof-only. Normal C5 work changes tests/evidence only and independently exercises the complete accepted C2/C3/C4 architecture: full synthetic marker/path-family storage coverage, confirmed/UNKNOWN outcomes, crash/restart at all relevant local boundaries, unrelated-baseline preservation, controller DB preservation, duplicate/concurrency/cancellation behavior, no-P1 replay and path/alias hardening. A production defect discovered by C5 is a STOP requiring a separately reviewed repair, not an inline C5 production edit.

No real Codex thread/delete is authorized in C5.

## Remaining correction lane

After P7.C5 architect acceptance only:

1. **P7.C6** — separately authorized renewed isolated real T3 + one-delete hard-delete acceptance.

P8 and P9 remain blocked until P7.C6 is independently architect accepted.

## Current non-goals

Do not run another real P7 thread/delete in C5. Do not mutate retained rejected P7 evidence. Do not manually delete persistent sessions/history to manufacture a pass. Do not copy/migrate credentials. Do not start P7.C6/P8/P9 inside C5.