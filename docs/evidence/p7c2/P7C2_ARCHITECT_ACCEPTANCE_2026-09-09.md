# P7.C2 architect acceptance — 2026-09-09

Status: **ARCHITECT_ACCEPTED**

Repository: `MaksimUnimax/CodexControl`

Accepted implementation lineage:

- architect base: `4e1117e2a5ebb50add5d0bbf17cecb6682b2f571`
- initial implementation candidate: `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc`
- initial architect verdict: `REWORK_REQUIRED`
- repair commit: `80673db644962b0cc5b1a388d64cb5902bd4f46c`
- accepted candidate tree: `067adc00429608a5b86b7d3ccb21af0eda6d86f5`

## Independent architect review

The candidate was reviewed as repository state rather than accepted from executor claims alone. The final branch is exactly two commits ahead of the frozen base. The repair commit is exactly one commit above the initial candidate and changes only:

- `src/codex_control/storage/sqlite.py`;
- `tests/unit/test_sqlite_schema_v1.py`;
- `docs/evidence/p7c2/P7C2_SCHEMA_V3_STORAGE_BARRIER_EVIDENCE.md`.

The initial candidate had one architect-detected regression: `_migrate_v3()` had been inserted before the historical `sqlite3.Error` and `BaseException` handlers belonging to `_migrate_v2()`. This changed accepted schema-v2 rollback/error-mapping behavior. The repair restores the exact three-handler v2 structure while preserving a separate complete three-handler v3 structure. Focused regression tests now prove both the historical SQLite-error rollback plus `SCHEMA_INVALID` mapping and BaseException rollback plus original-exception re-raise.

No remaining architect-blocking defect was found after the repair.

## Accepted schema authority

Current CodexControl storage schema is v3.

Historical authorities remain immutable:

- `SCHEMA_V1_DDL_SHA256=b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- `SCHEMA_V2_MIGRATION_SHA256=a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

Accepted v3 authority:

- migration ID: `0003_confirmed_pending_storage`
- `SCHEMA_V3_MIGRATION_SHA256=cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`

The v3 migration widens only the durable dialogue-state authority required by ADR-0043 and rebuilds the complete dialogue FK graph transactionally. No `writable_schema` shortcut or FK-disabled migration path is accepted.

## Accepted confirmed-delete barrier

Exact accepted behavior is now:

`DELETE_PENDING -> DELETING -> P1.9 thread/delete`

Then:

- exact schema-valid upstream confirmation -> `DELETE_CONFIRMED_PENDING_STORAGE`;
- dispatched uncertainty/non-success -> existing `DELETE_UNKNOWN`;
- deterministic accepted pre-dispatch failure -> existing deterministic failure semantics.

`DELETE_CONFIRMED_PENDING_STORAGE` retains the exact live dialogue/profile/thread binding, has no tombstone, performs no local purge, and cannot redispatch upstream delete. `finalize_confirmed()` is no longer legal from `DELETING` or `DELETE_UNKNOWN`; it accepts only the confirmed-pending state for later P7.C4 composition.

Startup recovery keeps the existing conservative `DELETING -> DELETE_UNKNOWN` rule, while an already durable `DELETE_CONFIRMED_PENDING_STORAGE` remains confirmed-pending and performs zero external delete/reconciliation effects.

Private dialogue/control projections expose confirmed-pending truthfully and never report it as `DELETED`.

## Regression/effect evidence

Executor evidence after architect repair records:

- focused repair tests: 64 pass;
- ordinary full suite: 967 tests, 0 skipped, 0 failures, 0 errors;
- real Codex business RPCs: 0;
- real thread-delete calls: 0;
- Telegram calls: 0;
- real Codex storage mutation: 0;
- credential content reads/copies: 0;
- process mutation: 0.

P7.C2 itself did not run a new real Codex acceptance experiment.

## P7.C3 — frozen next executable slice

P7.C3 is now the only executable correction slice.

Goal: implement the ADR-0043 **dedicated profile + isolated state-root runtime authority**, without performing hard-delete cleanup orchestration yet.

Frozen boundary:

1. Extend the configured profile authority so every production-enabled CodexControl profile has an explicit persistent `CODEX_HOME` and a distinct explicit isolated state root. Do not add a boolean that can merely claim a shared home is dedicated; safe dedication is established by path/ownership/runtime invariants.
2. The profile home and isolated root must be absolute, canonical, root-owned, non-symlink, not group/world writable, mutually non-overlapping, and non-overlapping with the controller SQLite path/root, repository, credential authority, or another profile's home/state root.
3. Runtime startup must fail closed before app-server publication if any configured root is missing, foreign-owned, symlinked, unsafe, overlapping, shared, contains disallowed foreign entries, or cannot be proved to belong exclusively to the configured profile.
4. The isolated root is the product-owned disposable boundary for Codex SQLite state/log DBs, WAL/SHM sidecars, configurable text logs, cache/temp material inside that root. Child launch must route SQLite through exact installed 0.144.6 `CODEX_SQLITE_HOME` / `sqlite_home` authority and route configurable logs through `log_dir` inside the same isolated product boundary.
5. `history.persistence=none` is mandatory for production-enabled dedicated profiles unless a later architect decision explicitly replaces it. P7.C3 must prove the exact child configuration contains this policy and does not silently inherit a weaker setting.
6. Exact installed Codex authority remains `codex-cli 0.144.6` with generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`. The runtime/capability gate must fail closed on version/capability drift. No upgrade is authorized.
7. No credential material may be copied, symlinked, migrated, read into evidence, or placed in the isolated state root. File auth may remain only under an independently provisioned dedicated profile home; P7.C3 does not provision or migrate credentials.
8. Add an exclusive per-profile runtime reservation primitive sufficient for later P7.C4 cleanup. While reserved, new runtime acquire/start must fail closed. Reservation must linearize against concurrent acquire/start and profile shutdown and must not be a best-effort flag.
9. Add secure isolated-root create/validate/recreate primitives needed by the runtime authority, but do not yet connect them to `DELETE_CONFIRMED_PENDING_STORAGE` or `DELETE_UNKNOWN` cleanup. Whole-root destruction as part of delete orchestration belongs to P7.C4.
10. Preserve the accepted P1.2 invariant of at most one READY app-server child per profile and the V1 invariant of at most one live dialogue per physical server.
11. Use fake process/filesystem tests only. P7.C3 has zero real model/thread/turn/delete/approval/Telegram effects and must not mutate real Codex profile homes or real isolated state roots.
12. Do not change P7.C2 delete/recovery semantics except for narrow compatibility needed to block runtime acquisition on an explicitly reserved profile; no P7.C4 cleanup/finalization composition is allowed.

Required P7.C3 acceptance evidence includes configuration/domain validation, path canonicalization/ownership/symlink/permission/overlap matrices, profile-to-profile collision proof, controller/repository/credential overlap proof, exact child environment/argv/config proof, mandatory history/log/SQLite routing proof, capability-drift failure, concurrent acquire/reserve/shutdown races, secure root creation/recreation tests, no-credential exposure tests, ordinary full regression, commit/push, and independent architect readback.

P7.C4, P7.C5, P7.C6, P8 and P9 remain blocked.

## Architect verdict

`P7C2_ARCHITECT_ACCEPTED`

Next action: execute P7.C3 only under ADR-0043 and the frozen boundary above.
