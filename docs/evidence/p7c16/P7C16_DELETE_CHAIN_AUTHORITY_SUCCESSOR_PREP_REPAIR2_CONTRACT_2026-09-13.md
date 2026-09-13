# P7.C16 delete-chain authority successor preparation Repair-2 contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / FINAL DEFAULT-ENTRY + QUIESCENCE + EVIDENCE-INTEGRATION REPAIR / NO REAL EXECUTION**

## Exact base

Repair-2 starts exactly from:

- HEAD `aaccc8fddc4df763e7412524be85d83134f5bd64`;
- P7.C16 launcher blob `08e6be10f4f7444c87a2e72572e4a8107ed7a3b2`;
- P7.C16 evidence blob `4f0caaf4e3c795bc8ca1dc8d052b663f8a644d47`.

Binding review:

`docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_REPAIR1_ARCHITECT_REVIEW_2026-09-13.md`

Repair-2 is deliberately narrow. Preserve all Repair-1 accepted source bundle, package marker, late-bound controller, underlying reservation delegation, authenticated home, root-only authority, watchdog, installed-runtime, delete-chain and exact-effect material.

## Zero-real-effect boundary

During Repair-2:

- real Codex/app-server starts = `0`;
- real model/thread/Turn RPCs = `0`;
- real approval/ALLOW/DENY = `0`;
- real interrupt/delete = `0`;
- real P7.C16 ledger creation = `0`;
- historical ledger mutation/cleanup = `0`;
- persistent-home mutation = `0`;
- Telegram = `0`;
- real process signals = `0`.

Do not create or set a P7.C16 real token.

## 1. Default real entrypoint MUST select production executor

Correct `p7c16_real_entrypoint()`.

When `executor is None`, it MUST select:

`P7C16PreparedFutureExecutor.production(contract)`

not a bare constructor.

Required default path:

source bundle gate
-> `.production(contract)`
-> durable P7.C16 ledger reserve
-> post-reserve run-parent creation
-> root-only boot
-> one owned child/watchdog
-> root-only child-result validation
-> process-group validation
-> terminal P7.C16 ledger mapping.

An injected executor remains allowed only for explicit offline negative/unit seams.

Static test must reject the old expression:

`P7C16PreparedFutureExecutor(P7C16DurableOneShotLedger(P7C16_LEDGER_PATH))`

as the default real-entrypoint selection.

## 2. Exact authorized default-entrypoint offline handoff

Add a mandatory positive test that traverses the actual default entrypoint, not `_production_with_authority()` directly.

Use a fully matching synthetic source authority/environment and a production-factory injection seam below the entrypoint, not an injected executor parameter.

Required traversal:

`p7c16_source_bundle_gate`
-> `p7c16_real_entrypoint(executor=None)`
-> `P7C16PreparedFutureExecutor.production(contract)`
-> temp durable ledger
-> production boot
-> owned child/watchdog seam
-> actual P7.C16 future-child main
-> fake external runtime/protocol boundary
-> real cleanup coordinator/delete service
-> child PASS
-> clean watchdog
-> ledger COMPLETED.

The test must prove default production selection count = 1 and must fail if the default entrypoint uses a bare executor.

A safe factory/path override may be injected through an explicit test-only production factory hook so the real `/root/.codexcontrol/p7c16-one-shot.json` is never created during preparation.

## 3. Correct real runtime quiescence authority

The P7.C16 facade must not return false merely because the underlying real `CodexRuntimeManager` lacks a `runtime_quiescent` property.

Use the accepted P7.C15 semantics. Preferred implementation:

- remove the facade `runtime_quiescent` property entirely and allow the inherited P7.C15 `_runtime_quiescent(manager)` helper to inspect delegated `_runtimes`, `_starting`, `_unresolved`; or
- expose an equivalent property computed from those underlying ownership maps.

For a real-shaped manager:

quiescent = no active/starting/unresolved child ownership.

Do not infer quiescence from fake-only booleans.

Add tests with a real-shaped manager that intentionally has no `runtime_quiescent` attribute:

- active runtime -> false;
- starting child -> false;
- unresolved child -> false;
- all three empty after shutdown -> true.

Positive successor PASS must use this real-shaped quiescence authority.

## 4. Bounded late-failure convergence through accepted owned wait

Replace direct production `asyncio.wait_for(manager.shutdown_profile(...))` in the successor convergence path with:

`p7c13._await_owned(...)`

or a no-weaker P7.C16 owner.

Use the accepted effective engine profile:

`P7C16_ENGINE_PROFILE_ID = p7c15.P7C15_PROFILE_ID`.

Use the accepted final-runtime/convergence timeout authority; no ad-hoc short literal.

Required forced-failure proof:

- delete generation acquired;
- local late-stage exception raised;
- bounded shutdown owned and joined;
- real-shaped underlying runtime maps become empty;
- failure verdict remains FAILED;
- `runtime_child_quiescent=true` only because actual convergence succeeded;
- shutdown failure/nonconvergence => quiescence false and non-PASS;
- no second child/delete/retry.

## 5. Safe controller/delete-chain stage authority

The P7.C16 stage journal currently defines successor-specific stage names but production does not emit them.

Add a P7.C16-owned production hook around the exact late controller/cleanup boundary without copying or faking the whole P7.C15 engine.

Retained safe stages must include, in actual order when reached:

- `CONTROLLER_BINDING`;
- `DELETE_CLEANUP_AUTHORITY_CONFIRMED`;
- `DELETE_CHAIN_READY`;
- `THREAD_DELETE_DISPATCH`;
- `THREAD_DELETE_RESULT`;
- `APPLICATION_DELETE_RESULT`.

It is acceptable to adapt a narrow cleanup/service factory seam in the inherited orchestrator if and only if:

- the actual `DeleteStorageCleanupCoordinator` constructor still executes;
- the actual `DialogueDeleteService` constructor still executes;
- no delete is dispatched by the hook itself;
- the inherited canonical service still owns the only delete.

Do not journal a confirmation before the corresponding real constructor/validation succeeds.

## 6. Finite safe controller-storage error category

Known P7.C16 late-bound controller authority failures must retain a finite safe category:

`controller_storage_mismatch`

without raw path content.

Do not persist only generic `ValueError` when the failure is one of the known controller-storage authority conditions.

Allowed implementation patterns:

- a P7.C16 finite exception type with `.category`/`.value`;
- translation of the known `ValueError("controller_storage_mismatch")` immediately at the successor-owned boundary.

Do not weaken or modify production `DeleteStorageCleanupCoordinator` validation.

Child result/stage journal on such failure must show:

- terminal exception class safe;
- terminal error category `controller_storage_mismatch`;
- last confirmed stage no later than `CONTROLLER_BINDING` or `DELETE_CLEANUP_AUTHORITY_CONFIRMED` depending on the exact failure boundary;
- thread/delete count `0` when delete-chain readiness was not reached.

## 7. Preserve root-only and one-shot containment

Do not regress:

- corrected historical blobs/package markers;
- repository-origin import proof;
- ledger-before-run-mutation ordering;
- root-only boot/result/ledger authority;
- `/root/.codex_second` production home;
- P7.C16 watchdog hard deadline and process-group proof;
- installed Codex preflight;
- exact effect PASS gate;
- real underlying reservation/recreate/release ownership;
- late-bound exact controller DB path;
- real cleanup coordinator and real delete service;
- P7.C15/P7.C14/P7.C13 permanent non-retry boundaries.

## 8. Parent terminal / CLI projection regression

After fixing default entrypoint selection, prove exact CLI semantics using the same default path:

- gate/source disabled -> `2`, no ledger;
- valid COMPLETED -> `0`;
- FAILED -> nonzero;
- UNKNOWN -> nonzero;
- CONFIRMED_PENDING -> nonzero;
- TIMEOUT -> nonzero.

No test may obtain PASS by injecting a mock executor directly into `p7c16_real_entrypoint()`.

## 9. Required production-shaped matrix

At minimum cover:

1. exact default entrypoint positive -> COMPLETED/exit 0 on temp authority;
2. default entrypoint source mismatch -> pre-ledger exit 2;
3. real-shaped manager quiescent after shutdown -> true;
4. real-shaped active/starting/unresolved manager -> false;
5. controller-storage mismatch -> finite category + delete 0;
6. real cleanup coordinator + real delete service positive -> one delete;
7. late failure + successful owned convergence -> FAILED + quiescent true;
8. late failure + convergence failure -> FAILED + quiescent false;
9. UNKNOWN -> ledger UNKNOWN/no retry;
10. CONFIRMED_PENDING -> ledger CONFIRMED_PENDING/no second delete;
11. malformed/missing child result -> FAILED;
12. process-group residual/scan error -> not COMPLETED;
13. missing exact positive effect -> not COMPLETED;
14. second executor call -> rejected.

## 10. File scope

Allowed tracked changes only:

- `tests/real/test_p7_c16_final_hard_delete_successor.py`;
- `docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`.

Optional one P7.C16-only helper under `tests/real/` only if strictly necessary.

Forbidden: `src/**`, P7.C15/P7.C14/P7.C13/P7.C12 protected files, package markers, historical evidence/ledgers, deployment, Telegram, P8/P9.

## 11. Validation

Run:

- focused P7.C16 Repair-2;
- exact default-entrypoint authorized synthetic handoff;
- real-shaped runtime-quiescence matrix;
- safe controller stage/error-category matrix;
- late convergence matrix;
- Repair-1 root-only ledger/boot/result safety regression;
- full real cleanup-coordinator handoff;
- P7.C15/P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- P7.C2-P7.C5 relevant non-real regressions;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed failures remain immutable and must be reported separately.

## 12. Gate-disabled smoke

With every P7.C16 real env var unset, exact CLI must exit `2`, leave the real P7.C16 ledger absent, create no run parents, child or Codex process, and touch no historical authority.

## 13. Evidence

Update:

`docs/evidence/p7c16/P7C16_DELETE_CHAIN_AUTHORITY_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`

Record:

- `P7C16_REPAIR2_BASE_HEAD=aaccc8fddc4df763e7412524be85d83134f5bd64`;
- prior launcher blob `08e6be10f4f7444c87a2e72572e4a8107ed7a3b2`;
- prior evidence blob `4f0caaf4e3c795bc8ca1dc8d052b663f8a644d47`;
- final launcher/evidence/helper blobs;
- default-entrypoint production selection proof;
- real-shaped quiescence proof;
- owned convergence proof;
- successor-stage order;
- controller-storage finite error-category proof;
- full validation totals;
- zero-real-effect accounting.

Required final lines:

`P7C16_REPAIR2_DEFAULT_REAL_ENTRYPOINT_PRODUCTION=PASS|FAIL`

`P7C16_REPAIR2_REAL_RUNTIME_QUIESCENCE_AUTHORITY=PASS|FAIL`

`P7C16_REPAIR2_OWNED_LATE_FAILURE_CONVERGENCE=PASS|FAIL`

`P7C16_REPAIR2_SUCCESSOR_STAGE_AUTHORITY=PASS|FAIL`

`P7C16_REPAIR2_CONTROLLER_ERROR_CATEGORY=PASS|FAIL`

`P7C16_REPAIR2_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS|FAIL`

`P7C16_PREP_READY=YES|NO`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c16-delete-chain-authority-successor-repair2-2026-09-13`

created from exact Repair-1 candidate `aaccc8fddc4df763e7412524be85d83134f5bd64`.

No force, no rebase, no main mutation by executor. After remote readback STOP. Independent architect acceptance is still required before any real token or one-shot execution contract exists.
