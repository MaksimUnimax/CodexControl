# P7.C15 real failure — architect review — 2026-09-13

Status: **CONSUMED FAIL / RETRY FORBIDDEN / DELETE NOT DISPATCHED / ROOT CAUSE DETERMINISTICALLY ESTABLISHED**

## Exact consumed authority

- real execution source HEAD: `17f8907068aa58de85d92800b9d87621e59ad1a3`;
- source tree: `993f094a50e062459908f1ddd373c48de478d7a1`;
- launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- sanitized real evidence commit: `3744cb19fba8ecba53d163b9e77f7adc9a213e6c`;
- sanitized real evidence blob: `b0f1f2014e23c60cb611c3176ad5f880b50dfc35`.

P7.C15 was invoked exactly once. The authoritative replay ledger is consumed and terminal `FAILED`. P7.C15 may never be rerun, reset, renamed, replaced, truncated or bypassed.

## Observed real boundary

The sanitized retained authority proves:

- parent exit `1`;
- ledger `FAILED`;
- watchdog `CHILD_FAILURE`;
- child result valid / child `FAILED` / verdict false;
- last confirmed stage `CONTROLLER_BINDING`;
- terminal exception class `ValueError`;
- runtime-child quiescence false;
- process-group active/zombies/scan-errors all zero;
- one child, zero retry;
- exact real effects through Turn 4: one model/list, one thread/start, one resume, four turn/start, one approval response, one ALLOW, one interrupt;
- `thread/delete=0`;
- official delete `NOT_CALLED`;
- application delete `NOT_CALLED`;
- post-delete oracle not reached.

The retained stage/wire/recovery authorities show that Turn 1/2, generation rebound, Turn 3 approval and completion, Turn 4 interrupt/terminal, runtime shutdown before oracle, pre-delete proof and schema-v4 controller binding were reached. No destructive delete dispatch occurred.

## Deterministic root cause

The failure window after `CONTROLLER_BINDING` and before `THREAD_DELETE_DISPATCH` is deterministic from the accepted source.

The P7.C15 real runtime manager is created with an `IsolationPathAuthority` containing `controller_db_root=<controller parent>` but **no exact `controller_db_path`**.

After durable schema-v4 controller binding, P7.C15 constructs:

`DeleteStorageCleanupCoordinator(storage, tracker)`

before recording or dispatching `thread/delete`.

`DeleteStorageCleanupCoordinator.__init__()` requires:

- an isolation authority with a string `controller_db_path`; and
- `storage.matches_database_path(controller_db_path) == True`.

If either is false it raises ordinary:

`ValueError("controller_storage_mismatch")`.

Because the generation-tracking wrapper delegates `isolation_authority` to the same early runtime manager, its authority still has `controller_db_path=None`. Therefore the real coordinator constructor deterministically raises before the canonical delete budget/dispatch.

The other constructor boundaries in this window do not match the retained exception class: `OfficialDeleteObservation` merely stores the lifecycle, while invalid `DialogueDeleteService` constructor arguments raise `DialogueDeleteError`, not ordinary `ValueError`.

Architect root-cause class:

`P7C15_ROOT_CAUSE=DELETE_CLEANUP_CONTROLLER_STORAGE_AUTHORITY_MISMATCH`

## Why preparation did not catch it

The Repair-2/3/4 production-shaped fake path selected `_P7C15FakeStorageCleanup` when the manager was `_FakeRuntimeManager`. It therefore bypassed the real `DeleteStorageCleanupCoordinator` constructor and its exact controller-storage path validation.

That fake-only local-cleanup branch made the full handoff less production-shaped at precisely the boundary that failed in the real run.

This is a test-seam defect, not a Codex provider/API defect and not an official delete failure: no delete request was sent.

## Required successor architecture

P7.C16 must be a distinct successor, never a P7.C15 retry.

The early runtime cannot simply be changed from `controller_db_root` to `controller_db_path`, because the controller DB does not yet exist when generations 1/2 are started and runtime authority validation of an exact DB path requires the file to exist.

The required architecture is a **late-bound exact controller-storage authority view** over the same underlying runtime manager:

1. early Codex runtime generations continue to use the accepted root-level controller storage authority;
2. after `SqliteStorage.open()` has created the fresh controller DB and durable binding has been confirmed, construct a new exact-path `IsolationPathAuthority` for the same profile/repository with `controller_db_path=<exact fresh controller DB>`;
3. validate that exact authority after the DB exists;
4. expose that exact authority to `DeleteStorageCleanupCoordinator` while delegating `reserve`, `shutdown_profile`, `recreate_isolated_state_root`, `profile` and reservation semantics to the **same underlying runtime manager**;
5. do not start a second Codex runtime manager/process and do not perform a second model/list;
6. use the real `DeleteStorageCleanupCoordinator` in production-shaped positive tests. No manager-type branch may replace it with a fake cleanup implementation.

The exact storage path view must be current-run bound and must not touch retained P7.C14/P7.C15 historical controller/material.

## Failure convergence requirement

P7.C15 also demonstrated that an exception after the delete-generation reacquire can leave the child reporting `runtime_child_quiescent=false` even though the parent eventually observes a clean process group.

P7.C16 must own a bounded late-stage shutdown/finalization path so any failure after delete-generation acquire attempts to converge the same underlying runtime manager before the child result is written. The failure result must record actual quiescence, never fabricate true.

## Retained historical material

Do not clean or mutate P7.C15 retained controller/isolated/persistent material during successor preparation. The real evidence confirms controller binding and retained isolated descendants after failure; post-delete residual classes were not observed and must not be inferred.

P7.C16 must use fresh target-specific paths/identities and prove retained P7.C14/P7.C15 material is unrelated to the new target.

## Verdict

`P7C15_REAL_RUN_CONSUMED=YES`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_FINAL_VERDICT=FAIL`

`P7C15_DELETE_DISPATCH_REACHED=NO`

`P7C15_ROOT_CAUSE=DELETE_CLEANUP_CONTROLLER_STORAGE_AUTHORITY_MISMATCH`

`P7C16_PREPARATION_AUTHORIZED=YES`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
