# Current work authority

Date: 2026-09-10

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority remains `codex-cli 0.144.6`; generated app-server schema SHA-256 remains `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete at their accepted boundaries. P6 final accepted commit remains `0409ad4a0744159aad875a5ddea4deaf1181699e`; no live Telegram or production deployment acceptance has occurred.
- Historical storage schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Historical schema-v2 migration SHA-256 remains `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- Accepted schema-v3 migration ID is `0003_confirmed_pending_storage` with SHA-256 `cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`.

## Rejected original P7

Original real P7 under ADR-0042 remains **REJECTED / ARCHITECTURE BLOCKED**.

Exactly one real P7 thread was used. Authenticated multi-turn, approval and interrupt paths were proven, then exactly one official accepted P1.9 `thread/delete` was dispatched. Its official result was terminal `DELETE_UNKNOWN`. It was never retried or reconciled with `thread/read`/`thread/list`.

Final read-only forensic evidence at `5aac49bd1b8a349343db52071520beed7f95592d` proved `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL`: five synthetic material-marker matches remained. Issue #38 remains historical blocker evidence.

P1.9/ADR-0016 ambiguity semantics remain immutable: dispatched non-success stays UNKNOWN; no blind retry or inferred success.

## P7.C1 — COMPLETE / architect accepted

Accepted discovery commit:

`a9900471d0599be21b1a1834301c4421d95acb29`

Acceptance:

`docs/evidence/p7c1/P7C1_ARCHITECT_ACCEPTANCE_2026-09-09.md`

C1 proved the residual storage provenance and exact installed 0.144.6 controls used by ADR-0043: `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, and `history.persistence=none`; session/rollout remains under `CODEX_HOME`.

## ADR-0043 — accepted correction topology

Production profiles use a dedicated persistent CodexControl-only `CODEX_HOME` plus a distinct product-owned isolated SQLite/log state root. Credentials are never copied/symlinked/migrated. Whole-root local containment requires exact ownership, reservation and runtime quiescence. `DELETE_UNKNOWN` remains official UNKNOWN even if local isolated storage is contained.

## P7.C2 — COMPLETE / architect accepted

Accepted lineage:

- initial candidate: `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc`;
- repair / accepted implementation: `80673db644962b0cc5b1a388d64cb5902bd4f46c`.

Acceptance:

`docs/evidence/p7c2/P7C2_ARCHITECT_ACCEPTANCE_2026-09-09.md`

Accepted C2 behavior:

- schema v3 is current predecessor authority;
- exact upstream `DELETE_CONFIRMED` first becomes durable `DELETE_CONFIRMED_PENDING_STORAGE`;
- full profile/thread binding is retained;
- no tombstone/purge occurs at that transition;
- `finalize_confirmed()` accepts only confirmed-pending;
- `DELETING` restart remains ambiguity -> `DELETE_UNKNOWN`;
- confirmed-pending restart never redispatches delete;
- `DELETE_UNKNOWN` remains no-retry.

Final C2 executor regression: 967 tests, 0 failures/errors.

## P7.C3 — COMPLETE / architect accepted

Accepted lineage:

- architect base: `0637643518bfe45e471a0d777d2995b833e6bcb8`;
- initial candidate: `0654ee1cbd70d4d6a6d5a317e948d2f08b2c081f`;
- first repair: `a549e6f1f295a37f14a7833ede0233d94745555a`;
- second repair: `2a6c5d8f2ed0980c4c7bc32cec471002432e1c9d`;
- third repair / accepted implementation: `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`;
- accepted implementation tree: `13eea89362694da594bb2b717c037980b0df446f`.

Acceptance:

`docs/evidence/p7c3/P7C3_ARCHITECT_ACCEPTANCE_2026-09-10.md`

Accepted C3 authority includes:

- explicit persistent `CODEX_HOME` + explicit `isolated_state_root` per profile;
- descriptor/no-follow path and protected-boundary validation;
- repository/controller protected authority required at runtime;
- exact root ownership/permission/symlink/overlap gates;
- isolated layout `.codexcontrol-state-root-v1`, `sqlite/`, `logs/`;
- exact 0.144.6 per-new-child-generation installed authority gate;
- protocol `client_version` remains independent from installed Codex version;
- child `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, and `history.persistence="none"` routing;
- opaque manager-owned exclusive profile reservation and exact quiescence proof;
- manager-owned descriptor-bounded state-root provision/validate/recreate;
- final current-path inode binding checks before provision/recreate success;
- no credential copying/content reads and no real Codex effects.

Final C3 executor regression: 1016 tests, 0 skipped, 0 failures, 0 errors.

## ADR-0044 — accepted P7.C4 durable containment authority

ADR-0044 freezes the next composition:

`docs/adr/0044-durable-local-containment-and-p7c4-cleanup.md`

It introduces additive schema v4 only to persist the separate local containment fact for official `DELETE_UNKNOWN`.

Frozen migration authority:

- migration ID: `0004_delete_local_containment`;
- migration SHA-256: `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.

The new table stores only bounded content-free metadata and explicitly coexists with the still-live UNKNOWN dialogue:

`OFFICIAL_DELETE_AUTHORITY=UNKNOWN`

`LOCAL_ISOLATED_STORAGE_CONTAINMENT=COMPLETED`

No new dialogue state is added.

## Current slice

**P7.C4 — NEXT / AUTHORITY FROZEN BY ADR-0043 + ADR-0044.**

C4 is confirmed local cleanup plus `DELETE_UNKNOWN` isolated-root containment orchestration only.

Confirmed path:

1. durable `DELETE_CONFIRMED_PENDING_STORAGE` binding;
2. exact C3 profile reservation;
3. shutdown/reap and quiescence proof;
4. manager-owned isolated-root recreation;
5. read-only persistent `CODEX_HOME/sessions/**` + `history.jsonl` exact-thread residual gate with zero scan errors;
6. only then `DeletionRepository.finalize_confirmed()`;
7. release reservation only after final tombstone/purge success.

Any local failure leaves confirmed-pending, binding retained, no tombstone/purge and reservation held for process lifetime.

UNKNOWN path:

1. state remains `DELETE_UNKNOWN` and `last_error_class=DELETE_UNKNOWN`;
2. no external retry/read/list/reconciliation;
3. reserve profile, shutdown/reap, recreate isolated root;
4. write exact schema-v4 containment row only after recreation succeeds;
5. keep exact binding and no tombstone/finalization;
6. retain reservation as process-local quarantine; startup re-establishes quarantine and local containment.

C4 may compose an optional local-cleanup port into `DialogueDeleteService` and `DialogueRecoveryService`. Lower-level C2 behavior without that port remains compatible.

P7.C4 has zero real Codex/Telegram effect. All root/session tests use synthetic temporary files and fake process/lifecycle ports.

## Remaining correction lane

After P7.C4 architect acceptance only:

1. **P7.C5** — corrected fake hard-delete acceptance, including full marker/path-family/crash/baseline proof and additional mount/namespace alias hardening where safely available.
2. **P7.C6** — separately authorized renewed isolated real T3 + one-delete hard-delete acceptance.

P8 and P9 remain blocked until P7.C6 is independently architect accepted.

## Current non-goals

Do not run another real P7 thread/delete in C4. Do not mutate retained rejected P7 evidence. Do not manually delete persistent sessions to force a pass. Do not copy/migrate credentials. Do not start P7.C5/P7.C6/P8/P9 inside C4.