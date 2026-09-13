# P7.C16 delete-chain authority successor preparation contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / DISTINCT SUCCESSOR / P7.C15 RETRY FORBIDDEN / REAL EXECUTION NOT AUTHORIZED**

## Exact base

P7.C16 preparation starts exactly from the P7.C15 real-evidence head:

- base HEAD `3744cb19fba8ecba53d163b9e77f7adc9a213e6c`;
- base tree `2fd391fb6fff9c3e84bda7d3640155677a42f070`;
- consumed P7.C15 execution source `17f8907068aa58de85d92800b9d87621e59ad1a3`;
- consumed P7.C15 launcher blob `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C15 real evidence blob `b0f1f2014e23c60cb611c3176ad5f880b50dfc35`;
- inherited P7.C14 launcher blob `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Binding architect review:

`docs/evidence/p7c15/P7C15_REAL_FAILURE_ARCHITECT_REVIEW_2026-09-13.md`

## Permanent historical boundaries

P7.C15 is consumed `FAILED`. P7.C15 may never be rerun or have its ledger reset/bypassed.

P7.C14 and P7.C13 also remain permanently non-retryable.

P7.C16 must use a **new gate, new one-shot ledger, new fresh run paths and a new fresh thread**.

Do not clean or mutate retained P7.C14/P7.C15 historical controller, isolated or persistent material during preparation.

## Absolute zero-real-effect preparation boundary

During P7.C16 preparation:

- real Codex/app-server starts = `0`;
- real model/thread/Turn RPCs = `0`;
- real approval responses / ALLOW / DENY = `0`;
- real interrupt = `0`;
- real delete = `0`;
- P7.C16 real ledger creation = `0`;
- P7.C15/P7.C14/P7.C13 ledger mutation = `0`;
- persistent-home mutation = `0`;
- retained historical cleanup = `0`;
- Telegram = `0`;
- real process signals = `0`.

Do not create or set a P7.C16 real authorization token.

## Accepted P7.C15 material frozen for reuse

Do not redesign the already accepted P7.C15 behavior unless a direct P7.C16 integration test requires a narrow adapter:

- exact source/import gate principles;
- ledger-before-run-mutation ordering;
- one owned child / no retry;
- P7.C15 timeout invocation-plan principles and bounded stage ownership;
- one authenticated model/list;
- generation tracking + generation rebound;
- fresh Turn-1/Turn-2 marker proofs;
- authenticated selected model/reasoning authority;
- private child/app-server umask;
- actual Turn-3 C11/P7.C12 approval path;
- Turn-3 post-join second-request observer;
- actual Turn-4 observer/interrupt;
- schema-v4 controller IDLE binding;
- canonical `DialogueDeleteService.delete()` semantics;
- independent `OfficialDeleteObservation`;
- UNKNOWN / CONFIRMED_PENDING no-retry semantics;
- separate persistent/isolated post-delete proof;
- derived unrelated-removal fact;
- isolation-envelope and post-delete schema proof;
- live-budget failure accounting;
- stage journal;
- exact-effect parent PASS predicate;
- safe parent terminal recovery authority.

## Deterministic P7.C15 defect to reproduce first

Before implementing the successor correction, reproduce offline the exact consumed P7.C15 defect using real production classes:

1. create/open a temporary schema-v4 controller DB;
2. create an early-runtime `IsolationPathAuthority` with only `controller_db_root=<parent>` and no `controller_db_path`;
3. expose it through a runtime-manager-shaped object;
4. construct `DeleteStorageCleanupCoordinator(storage, runtime_manager)`;
5. require ordinary `ValueError` with safe class/reason `controller_storage_mismatch`;
6. prove no `DialogueDeleteService.delete()` call and no thread/delete dispatch occurs.

This reproduction is required so P7.C16 is correcting the real consumed defect rather than a guessed symptom.

Required flag:

`P7C16_PREP_P7C15_CONTROLLER_AUTHORITY_ROOT_CAUSE_REPRODUCED=PASS`

## Required architecture — late-bound exact controller-storage authority

The early Codex runtime must continue to use root-level controller authority because the controller DB does not yet exist when runtime generations start.

After `SqliteStorage.open()` creates the fresh controller DB and before the real `DeleteStorageCleanupCoordinator` is constructed, P7.C16 must expose an exact-path authority view over the **same underlying runtime manager**.

Preferred component:

`P7C16LateBoundControllerRuntimeView`

or an equivalently strict immutable/delegating facade.

The view must:

- hold/delegate the same underlying runtime manager used by the current run;
- expose an `IsolationPathAuthority` with the same profile/repository but `controller_db_path=<exact fresh current-run controller DB>`;
- not start a second Codex runtime manager/process;
- not perform model/list;
- delegate the actual runtime cleanup operations required by `DeleteStorageCleanupCoordinator`, including `reserve`, `shutdown_profile`, `recreate_isolated_state_root` and profile lookup, to the same underlying manager;
- preserve the underlying reservation token semantics; reservation release must still return to the same underlying manager;
- expose only the exact current-run controller DB, never a historical P7.C14/P7.C15 DB;
- validate the exact controller authority only after the fresh DB exists;
- prove `storage.matches_database_path(exact_authority.controller_db_path)` before coordinator construction.

The underlying early runtime manager may retain its accepted root-level controller authority internally. P7.C16 must not mutate that manager's private authority object in place.

## Exact-path authority validation

Before constructing the real cleanup coordinator, require all of:

- exact controller DB path is absolute;
- exact controller DB exists;
- regular file, root-owned, not group/world writable, no symlink;
- exact DB parent authority valid;
- exact profile persistent home / isolated root / repository authority valid;
- `IsolationPathAuthority.validate_runtime_authority()` passes with `controller_db_path`;
- opened `SqliteStorage` matches that exact path.

Any mismatch => non-PASS before `thread/delete` budget/dispatch.

## No fake cleanup shortcut in the positive path

The P7.C15 preparation missed the defect because `_FakeRuntimeManager` selected `_P7C15FakeStorageCleanup` instead of the real coordinator.

P7.C16 production and production-shaped positive tests MUST use:

`DeleteStorageCleanupCoordinator`

for the local cleanup chain.

Forbidden in the positive/full-handoff path:

- selecting fake cleanup based on `isinstance(manager, Fake...)`;
- replacing `DeleteStorageCleanupCoordinator` with a fake object;
- monkeypatching its constructor to PASS;
- skipping its exact controller-path checks.

Fakes may exist only at external/runtime/process/filesystem/provider boundaries while the real coordinator/service orchestration classes execute.

## Preferred thin successor architecture

Create a distinct module:

`tests/real/test_p7_c16_final_hard_delete_successor.py`

P7.C16 should be thin and may reuse the accepted P7.C15 execution engine as frozen library authority rather than copying the full orchestration, provided all of the following hold:

- P7.C15 real parent/ledger is never invoked;
- `/root/.codexcontrol/p7c15-one-shot.json` is read-only historical authority and is never mutated;
- P7.C16 owns a distinct source gate and distinct replay ledger;
- P7.C16 child invocation can call the frozen P7.C15 production child/orchestrator only through a P7.C16-owned wrapper/runtime factory that supplies the late-bound exact controller authority;
- current-run boot/result/stage/wire paths are P7.C16-prefixed or otherwise unambiguously P7.C16-bound;
- source/boot authority is bound to the P7.C16 executable source;
- no nested P7.C15 ledger reservation occurs.

A mechanical copy of the full P7.C15 orchestrator is discouraged unless composition cannot satisfy the frozen authority requirements.

## Distinct P7.C16 authority

Define at minimum:

- `P7C16_FUTURE_REAL_GATE`;
- `P7C16_EXPECTED_HEAD`;
- `P7C16_EXPECTED_TREE`;
- `P7C16_EXPECTED_LAUNCHER_BLOB`;
- expected inherited P7.C15/P7.C14/P7.C13/P7.C12 blobs;
- parent CLI `--p7c16-real-run`;
- child CLI `--p7c16-future-child` if a child wrapper is used;
- replay barrier `/root/.codexcontrol/p7c16-one-shot.json`;
- fresh P7.C16 run authority prefixes.

P7.C16 source gate must fail before ledger/run mutation on any mismatch.

## Replay and mutation ordering

Preserve the accepted P7.C15 ordering:

source gate -> in-memory path plan -> P7.C16 ledger reserve -> current-run state/work/boot creation -> one child.

Before successful P7.C16 ledger reserve: zero run-specific filesystem mutation.

After reserve: every failure is permanently consumed; no retry.

Use temporary ledgers only during preparation tests.

## Full real coordinator production-shaped positive proof

Mandatory zero-real-effect test must traverse the actual successor path with fake external boundaries but real application cleanup classes:

P7.C16 source gate
-> temporary P7.C16 ledger
-> fresh boot
-> one owned child seam
-> accepted P7.C15 Turn1/2/3/4 path
-> actual schema-v4 controller binding
-> P7.C16 late-bound exact controller authority view
-> **real `DeleteStorageCleanupCoordinator` constructor**
-> **real `DialogueDeleteService.delete()`**
-> fake official lifecycle delete through accepted lifecycle seam
-> real cleanup coordinator confirmed-finalization path
-> post-delete observed proof
-> child PASS
-> P7.C16 ledger COMPLETED.

The positive test must prove:

- real cleanup coordinator constructor count = 1;
- exact controller path matches storage = YES;
- second Codex runtime manager created = 0;
- additional model/list dispatch = 0;
- canonical delete-service invocation = 1;
- official lifecycle delete call = 1;
- cleanup reservation = 1;
- cleanup bounded shutdown = 1 as required;
- cleanup isolated-root recreate = 1 on confirmed-success path if required by the accepted coordinator;
- retry = 0;
- second delete = 0;
- historical P7.C15 ledger access/mutation = 0.

## Wrong-authority negative matrix

At minimum prove with production-shaped fakes:

1. `controller_db_path=None` reproduces P7.C15 `controller_storage_mismatch`;
2. exact path points to a different DB => blocked before delete;
3. exact path file missing => blocked before delete;
4. exact path symlink => blocked;
5. exact path non-root/non-private authority => blocked;
6. storage opened on different path => blocked;
7. historical P7.C15 controller path supplied => blocked/current-run binding mismatch;
8. exact authority validates only after current-run DB exists;
9. fake-cleanup shortcut cannot satisfy the positive production-shaped gate.

All pre-delete-chain authority failures must leave `thread/delete=0`.

## Late-stage failure convergence

P7.C16 must correct the P7.C15 failure-convergence weakness.

Once a delete-generation runtime has been acquired, any exception before/inside/after delete-chain assembly must enter a bounded final convergence path.

Requirements:

- same underlying runtime manager only;
- bounded shutdown/finalization in `finally` or equivalent owned structure;
- no second child;
- no retry;
- no duplicate delete;
- child failure result reports actual `runtime_child_quiescent` after convergence attempt;
- a successful convergence after a local pre-delete failure should report quiescent true even though overall verdict remains FAILED;
- shutdown failure remains explicit non-PASS and quiescence false.

Add forced failures at least:

- immediately before late-bound authority validation;
- exact-authority validation failure;
- cleanup coordinator constructor failure;
- service-constructor failure seam if injectable;
- delete operation failure.

Prove bounded convergence and no duplicate destructive effect.

## Safe stage/error authority

P7.C16 retained evidence must make this boundary explicit.

Add safe finite stage/class authority, for example:

- `CONTROLLER_BINDING`;
- `DELETE_CLEANUP_AUTHORITY_CONFIRMED`;
- `DELETE_CHAIN_READY`;
- `THREAD_DELETE_DISPATCH`.

If composition with the frozen P7.C15 journal prevents adding a stage record safely, P7.C16 may keep a separate bounded root-only successor-stage authority, but it must not duplicate raw identifiers/content.

Known local authority errors should retain a finite safe category such as:

`controller_storage_mismatch`

rather than only generic `ValueError`, without exposing raw paths.

## Retained P7.C15 material isolation

Do not clean P7.C15 retained controller or isolated/persistent material in preparation.

P7.C16 full-handoff tests must include unrelated historical P7.C15-like material and prove it does not:

- satisfy the fresh target oracle;
- block the exact current-run controller authority;
- get deleted as part of P7.C16 target cleanup;
- count as a current-run residual.

## Exact effect authority

Preserve the accepted PASS-exact matrix:

- new_threads 1;
- model/list 1;
- thread/start 1;
- thread/resume 1;
- turn/start 4;
- approval_responses 1;
- allow_responses 1;
- turn/interrupt 1;
- thread/delete 1;
- thread/read 0;
- thread/list 0;
- second_child 0;
- real_retry 0;
- telegram 0.

No second model/list may be introduced by the late-bound view.

## Terminal semantics

Preserve exactly:

- full verified success => COMPLETED;
- official `DELETE_UNKNOWN` => UNKNOWN, no retry/read/list/manual cleanup inference;
- official confirmed + application `CONFIRMED_PENDING_STORAGE` => CONFIRMED_PENDING, no second external delete;
- timeout => TIMEOUT;
- normal failure => FAILED.

No terminal class is retryable.

## Source / static anti-regression gates

Focused P7.C16 tests must reject production equivalents of:

- P7.C15 ledger reservation or P7.C15 real parent invocation;
- early exact `controller_db_path` authority used to start Codex before DB exists;
- cleanup coordinator receiving only `controller_db_root`;
- fake-cleanup positive shortcut;
- second runtime manager/process solely for cleanup;
- second model/list;
- raw/manual `thread/delete` fallback;
- duplicate delete/retry;
- failure path leaving an owned runtime active without a bounded convergence attempt.

## File scope

Allowed tracked changes only:

- `tests/real/test_p7_c16_final_hard_delete_successor.py`;
- `docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`;
- optional ONE P7.C16-only helper under `tests/real/` if strictly necessary.

Forbidden:

- `src/**`;
- consumed P7.C15 launcher/evidence modification;
- P7.C14 launcher;
- P7.C13 harness;
- P7.C12 matcher;
- historical ledgers/evidence;
- package markers;
- migrations/deployment/Telegram/P8/P9.

## Validation

Run:

- focused P7.C16 tests;
- exact P7.C15 root-cause reproduction;
- late-bound exact controller-authority matrix;
- full positive production-shaped handoff using the real `DeleteStorageCleanupCoordinator`;
- late-stage failure-convergence matrix;
- P7.C15/P7.C14/P7.C13 offline regressions only;
- P7.C12 focused;
- relevant P7.C2-P7.C5 non-real regressions;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and must be reported separately.

## Gate-disabled smoke

With every P7.C16 real variable unset, exact successor parent invocation must return a finite disabled exit, create no P7.C16 ledger/run parent and start no Codex process.

P7.C15/P7.C14/P7.C13 historical authorities must remain untouched.

## Evidence

Create:

`docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`

Record:

- exact base HEAD/tree;
- consumed P7.C15 real-evidence commit/blob;
- inherited protected blobs;
- final P7.C16 launcher/helper/evidence blobs;
- P7.C15 root-cause reproduction class;
- late-bound exact-controller-path proof;
- real cleanup coordinator constructor/use counts;
- same-underlying-manager / second-manager-zero proof;
- no-second-model-list proof;
- full canonical delete/cleanup positive facts;
- failure-convergence results/quiescence classes;
- historical-material isolation proof;
- exact effect matrix;
- validation totals;
- zero-real-effect accounting.

Required final lines:

`P7C16_PREP_P7C15_CONTROLLER_AUTHORITY_ROOT_CAUSE_REPRODUCED=PASS|FAIL`

`P7C16_PREP_LATE_BOUND_EXACT_CONTROLLER_AUTHORITY=PASS|FAIL`

`P7C16_PREP_REAL_DELETE_STORAGE_CLEANUP_COORDINATOR=PASS|FAIL`

`P7C16_PREP_SAME_RUNTIME_MANAGER_NO_SECOND_MODEL_LIST=PASS|FAIL`

`P7C16_PREP_LATE_FAILURE_RUNTIME_CONVERGENCE=PASS|FAIL`

`P7C16_PREP_FULL_PRODUCTION_SHAPED_HANDOFF=PASS|FAIL`

`P7C16_PREP_READY=YES|NO`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to a P7.C16 preparation branch created from exact base `3744cb19fba8ecba53d163b9e77f7adc9a213e6c`.

No force, no rebase, no mutation of `main` by executor.

After remote readback STOP. Independent architect acceptance is required before any P7.C16 real token or real execution contract exists.
