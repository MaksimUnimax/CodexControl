# P7.C13 preparation Repair-1 architect review — 2026-09-12

Status: **REWORK_REQUIRED / PREPARATION NOT YET ACCEPTED / ZERO REAL EFFECT**

## Reviewed candidate

- Repair-1 commit: `e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`.
- Parent/base: `8fa749856c678cb1ae120f7802c6c553c1272e34`.
- Harness blob: `82a7f3c1e31456205fb316eb4e692973dc3d0361`.
- Evidence blob: `5e495ba56c22621d38f66eda5fe35bea97ce7a5c`.
- Scope: only the P7.C13 harness and P7.C13 evidence changed; no `src/**`, accepted P7.C12 matcher, historical P7.C6-P7.C12, schema, deployment or Telegram mutation.

## Accepted Repair-1 work

The following preparation work is materially accepted and should be preserved:

- exact future gate includes authorization token, HEAD, TREE and harness blob;
- gate mismatch reaches zero executor calls in the offline proof;
- durable root-only one-shot ledger design uses exclusive creation, mode/ownership/link/schema/duplicate-key/identity checks and permanently consumed semantics;
- one-child dedicated-session/process-group watchdog with bounded owned-group TERM/KILL and no retry/second-child path;
- installed version/schema/routing pre-effect gates;
- Turn-1 response-marker and Turn-2 remembered-marker observation model;
- four distinct Turn authorities;
- Turn-3 independent owned thread/Turn/cwd/sequence/selected-target binding before P7.C12 MATCH;
- Turn-4 separate active binding and exact interrupt target;
- persistent session content + filename + directory residual oracle;
- explicit unrelated target-specific removal acceptance gate;
- accepted synthetic `DialogueDeleteService` confirmed/UNKNOWN/confirmed-pending matrices;
- zero real effects during Repair-1.

## Blocking defect A — future child is still not executable

`PreparedFutureRealExecutor.production()` prepares a child command equivalent to running the P7.C13 module with `--p7c13-future-child`.

However the exact reviewed harness does not dispatch that argument to a completed real child orchestration path. `_future_child_main()` still raises `future child requires architect root-only boot configuration`, and the module's final `__main__` path invokes `unittest.main()`.

Therefore a later execution contract cannot merely authorize the exact reviewed harness. A real run would require another code change to supply/parse root-only boot authority and assemble the actual child path.

This violates the frozen preparation requirement that the exact accepted harness contain the complete future-real path and that the later execution contract supply only exact authorization/source values.

## Blocking defect B — effect budget reservation occurs after some effect callbacks

`FutureRealBusinessPath.run()` currently invokes the approval callback before reserving the `approval_responses` / `allow_responses` budget slots, and invokes the interrupt callback before reserving the `turn/interrupt` slot.

For the future real path, budget reservation/checking must happen before the callback capable of sending the approval response or interrupt RPC. Over-budget state must fail before any such effect can be emitted.

The same rule must be demonstrated for the official delete path: the budgeted delete authorization must be bound to the single production `DialogueDeleteService.delete()` call without creating a parallel raw delete dispatch path.

## Blocking defect C — production child assembly and bounded result publication are absent

The reviewed harness contains useful injectable classes (`InstalledRuntimeAuthority`, `FutureRuntimeRouting`, `FutureRealChildPath`, `FutureRealBusinessPath`) but does not yet assemble them into the actual future child invocation.

Before preparation can be accepted, the exact harness must already implement, behind the disabled gate:

1. root-only boot-authority loading and validation;
2. exact source/head/tree/harness/ledger/run-boundary reconciliation;
3. installed authority check;
4. fresh run-owned boundary materialization/preflight;
5. real adapter/runtime orchestration for Turn 1 -> restart/resume -> Turn 2 -> Turn 3 approval -> Turn 4 interrupt;
6. pre-delete physical observation;
7. fresh schema-v4 controller binding;
8. exactly one production `DialogueDeleteService.delete()` path;
9. post-delete acceptance oracle;
10. bounded root-only child-result write consumed by the parent watchdog.

No real effects are authorized while implementing or testing this assembly; all Repair-2 tests must use injected fake/synthetic seams.

## Verdict

- lineage/scope: **PASS**;
- durable one-shot design: **ACCEPTED FOR REUSE**;
- parent/watchdog design: **ACCEPTED FOR REUSE**;
- Turn 1/2 proof model: **ACCEPTED FOR REUSE**;
- owned Turn-3 binding: **ACCEPTED FOR REUSE**;
- distinct Turn-4 binding: **ACCEPTED FOR REUSE**;
- residual/unrelated-removal oracle: **ACCEPTED FOR REUSE**;
- actual exact future child executor: **NOT ESTABLISHED**;
- pre-dispatch effect-budget ordering for approval/interrupt: **NOT ESTABLISHED**;
- P7.C13 preparation overall: **REWORK_REQUIRED**.

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.