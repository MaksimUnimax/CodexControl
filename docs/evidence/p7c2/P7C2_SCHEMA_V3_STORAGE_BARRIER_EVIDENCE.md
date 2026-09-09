# P7.C2 schema-v3 storage barrier evidence

Date: 2026-09-09
Branch: `impl-p7-c2-v3-storage-barrier-2026-09-09`

## Lineage and authority

- Required `origin/main`: `4e1117e2a5ebb50add5d0bbf17cecb6682b2f571`
- Required base tree: `6f0c3ffd3a8c5e077c36514b8e025cc4af9c7a0a`
- Authority: accepted ADR-0043; original real P7 remains rejected and was not run.
- ADR-0043 and all roadmap/current-work/decision files were left unchanged.

P7.C2 changes the durable confirmed boundary only. Exact external
`DELETE_CONFIRMED` now commits `DELETE_CONFIRMED_PENDING_STORAGE`; storage
cleanup and filesystem work remain out of scope for P7.C4/P7.C3+.

## Schema-v3 migration

- Version: `3`
- Migration ID: `0003_confirmed_pending_storage`
- Migration SHA-256: `cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`
- Ordered migration statements: `52`
- The migration transactionally rebuilds the dialogue foreign-key graph while
  foreign-key enforcement remains enabled. It uses no `writable_schema` and
  never disables integrity checks.
- Fresh v0, v1, and v2 paths produce the exact ordered ledger rows 1, 2, 3.
- v3 reopen performs no migration and does not call the migration clock.
- A failed v3 migration rolls back to exact valid v2: `user_version=2`, two
  ledger rows, preserved data, no temporary `_v2` table, and a later retry
  succeeds.
- Forged hashes, missing ledger entries, SQL/index drift, extra tables, and
  malformed dialogue rows fail closed.
- Populated v2 rows are preserved row-for-row and direct SQLite foreign-key
  validation is clean after migration.

## Durable barrier and finalizer

`DeletionRepository.mark_delete_confirmed_pending_storage` requires
`DELETING`, the exact optimistic version, a bound thread, no tombstone, and
canonical delete readiness. It increments the version, preserves the full
dialogue binding, clears `last_error_class`, and uses a monotonic timestamp.
It performs no tombstone insertion or local purge.

`finalize_confirmed` now accepts only
`DELETE_CONFIRMED_PENDING_STORAGE`. Tests prove rejection from `DELETING` and
`DELETE_UNKNOWN`, successful atomic purge+tombstone from pending-storage, and
stale/duplicate version safety.

## Application, recovery, and private projection

- A fake P1.9 `DELETE_CONFIRMED` produces exactly one external delete call and
  returns `CONFIRMED_PENDING_STORAGE` with the live dialogue and no tombstone.
- The live thread binding remains present before finalization; no dialogue,
  job, payload, delivery, approval, or tombstone is removed.
- Replay from pending-storage makes zero external delete, interrupt, or
  finalizer calls and returns the same truthful pending status.
- A post-confirmation local transition failure surfaces a finite invariant or
  storage error, leaves `DELETING`, creates no tombstone, and performs no
  retry. A crash before the pending commit therefore remains conservative.
- Startup maps pre-existing `DELETING` to `DELETE_UNKNOWN` with zero external
  calls. It preserves pending-storage as
  `DELETE_CONFIRMED_STORAGE_PENDING`, with zero P1.9/finalization calls.
- Application recovery validates pending-storage binding, null error, and
  zero active jobs; malformed shapes fail invariant validation.
- Private dialogue and private-control projections expose
  `CONFIRMED_PENDING_STORAGE`, never `DELETED`, and offer no second delete
  action from that state.
- Pending-storage was added to the existing non-IDLE state-surface matrices:
  turns, lazy creation, model/reasoning/profile changes, deletion, interrupt,
  ordinary prompt admission, and dialogue replacement are blocked.

## Architect repair — v2 migration exception ownership

- Initial candidate: `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc`
- Initial architect verdict: `REWORK_REQUIRED`
- The architect detected that the candidate accidentally inserted `_migrate_v3()`
  after `_migrate_v2()`'s `StorageError` handler, causing the accepted v2
  `sqlite3.Error` and `BaseException` handlers to be lost from v2.
- The accepted base behavior is: `StorageError` rolls back and re-raises;
  `sqlite3.Error` rolls back and maps to `SCHEMA_INVALID`; and `BaseException`
  rolls back and re-raises the original exception.
- The repair restores those two missing handlers to `_migrate_v2()` verbatim in
  the historical position. `_migrate_v3()` retains its complete independent
  three-handler structure.
- Focused regression tests use a deterministic fake connection and prove v2
  SQLite-error rollback plus `SCHEMA_INVALID` mapping, and v2
  `BaseException` rollback plus original-exception re-raise.
- Full regression: `967` tests, `0` skipped, `0` failures, `0` errors.
- `SCHEMA_V1_DDL_SHA256` unchanged:
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- `SCHEMA_V2_MIGRATION_SHA256` unchanged:
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`
- `SCHEMA_V3_MIGRATION_SHA256` unchanged:
  `cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`

## Test evidence

Migration coverage includes fresh v0→v3, v1→v3, populated v2→v3, every legal
pre-v3 dialogue state, v3 reopen, exact IDs/hashes/order, rollback/retry,
forged v2/v3 cases, and foreign-key preservation. Repository/application
coverage includes the barrier transition, finalizer boundary, replay,
concurrency/version races, unknown preservation, restart recovery, malformed
pending shapes, and private projections.

Required gates:

- `PYTHONPATH=src python3 -m compileall -q src tests`: pass
- `git diff --check`: pass
- Ordinary full suite: `967` tests, `0` skipped, `0` failures, `0` errors

## Historical hashes and effects

- `SCHEMA_V1_DDL_SHA256` unchanged:
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- `SCHEMA_V2_MIGRATION_SHA256` unchanged:
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`
- Real Codex business RPCs: `0`
- Model-list, thread start/resume/delete/read/list, turn start, interrupt,
  approval response, and Telegram calls: `0`
- Real Codex storage mutation: `0`
- Credential content reads/copies: `0`
- Process mutation: `0`

All effects above refer to the real Codex/P7 effect budget. Tests used only
synthetic local SQLite databases and fake lifecycle ports; no raw thread,
prompt, authentication, or credential material is recorded here.

## Changed files

Production:

- `src/codex_control/application/dialogue_delete.py`
- `src/codex_control/application/dialogue_recovery.py`
- `src/codex_control/application/private_control.py`
- `src/codex_control/application/private_dialogue.py`
- `src/codex_control/storage/__init__.py`
- `src/codex_control/storage/application_recovery.py`
- `src/codex_control/storage/core_repositories.py`
- `src/codex_control/storage/deletion_repositories.py`
- `src/codex_control/storage/records.py`
- `src/codex_control/storage/schema.py`
- `src/codex_control/storage/sqlite.py`

Tests:

- `tests/acceptance/test_p2_6b_contract_snapshot.py`
- `tests/acceptance/test_p2_6b_replay_matrix.py`
- `tests/acceptance/test_p2_6b_restart_matrix.py`
- `tests/acceptance/test_p2_c2_rejected_ingress_schema_v2.py`
- `tests/acceptance/test_p3_5_fake_application.py`
- `tests/integration/test_core_state_repositories.py`
- `tests/integration/test_dialogue_delete_recovery_application.py`
- `tests/integration/test_existing_dialogue_turn_application.py`
- `tests/integration/test_hard_delete_tombstones_errors.py`
- `tests/integration/test_lazy_dialogue_turn_application.py`
- `tests/integration/test_metadata_retention.py`
- `tests/integration/test_private_dialogue_control.py`
- `tests/integration/test_rejected_ingress_schema_v2.py`
- `tests/integration/test_settings_selection_application.py`
- `tests/integration/test_sqlite_storage_kernel.py`
- `tests/integration/test_p7_c2_schema_v3_storage_barrier.py`
- `tests/unit/test_core_repository_records.py`
- `tests/unit/test_dialogue_delete_recovery_application.py`
- `tests/unit/test_private_control.py`
- `tests/unit/test_private_dialogue_control.py`
- `tests/unit/test_rejected_ingress_schema_v2.py`
- `tests/unit/test_sqlite_schema_v1.py`
