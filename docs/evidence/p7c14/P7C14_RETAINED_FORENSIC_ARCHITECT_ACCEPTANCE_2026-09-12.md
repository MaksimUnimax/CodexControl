# P7.C14 retained real-failure forensic — architect acceptance — 2026-09-12

Status: **ARCHITECT_ACCEPTED / ROOT CAUSE ESTABLISHED / P7.C14 CONSUMED / P7.C15 PREPARATION MAY PROCEED / NO REAL EXECUTION**

## Accepted forensic authority

Accepted forensic commit:

- `98e168c82f7fd9d8f50c491017323e97d3ed396f`
- parent/base `2676e4c9eeb3f343112d41c3307948599fc81837`
- only added file: `docs/evidence/p7c14/P7C14_RETAINED_REAL_FAILURE_FORENSIC_EVIDENCE_2026-09-12.md`

Execution authority remains:

- P7.C14 execution HEAD `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`
- execution tree `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`
- P7.C14 launcher blob `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- inherited P7.C13 harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`
- inherited P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

## Accepted real-effect boundary

The retained forensic establishes the real boundary independently of the broken exception-path counters:

- installed authority verified;
- runtime generation 1 acquired;
- model/list confirmed;
- thread/start confirmed;
- fresh thread/session materialized;
- Turn 1 start confirmed;
- Turn 1 terminal completed;
- generation 1 shutdown confirmed;
- runtime generation 2 acquired;
- thread/resume confirmed;
- Turn 2 `turn/start` RPC was **not dispatched**;
- Turn 3, approval, Turn 4, controller binding and delete were not reached.

A P7.C14-created persistent session remains retained. It is historical orphan material and is not authorized for cleanup by this acceptance.

## Accepted root cause

The root cause is uniquely established as:

`TURN_PRECONDITION_CHANGED`

at boundary:

`AFTER_THREAD_RESUME_CONFIRMED_BEFORE_TURN2_START_DISPATCH`

The accepted P7.C14/P7.C13 orchestration obtains one authenticated catalog snapshot while runtime generation 1 is active, wraps it in `_PinnedCatalogAdapter`, then after shutdown acquires runtime generation 2 and reuses that generation-1 catalog in a new `CodexTurnLifecycleAdapter`.

`CodexTurnLifecycleAdapter.start_turn()` correctly fails closed before RPC when:

`runtime.generation != catalog.runtime_generation`.

The retained evidence proves the second runtime and resume were confirmed and no second `turn/start` dispatch occurred, so this source branch is uniquely established.

## Accepted evidence defects

Two independent harness/evidence defects are also accepted:

1. **Exception-path effect accounting defect.** The production path mutates `ProductionRealChildOrchestrator.budget`, but `_future_child_main()` serializes the separate outer zero-valued budget on exception. Exception-path zero counts are therefore not dispatch authority.

2. **Parent exit projection defect.** P7.C14 `_module_main()` returns process exit `0` when a failed `WatchdogResult` is returned normally. Ledger `FAILED` + child `FAILED` remain authoritative.

## Successor policy

P7.C14 is permanently consumed and MUST NOT be rerun.

P7.C15 preparation is authorized as a distinct successor only. It must:

- use a new gate/token/ledger and fresh thread/run identity;
- preserve strict generation checks in `CodexTurnLifecycleAdapter`;
- reuse the one authenticated model-list semantic snapshot without a second provider call, while explicitly rebinding its runtime-generation authority to the confirmed generation-2 runtime before Turn 2;
- prove the P7.C14 mismatch offline and prove the corrected generation-rebound path offline;
- persist the actual live production budget on every failure path;
- persist a root-only safe stage journal / last-confirmed stage authority;
- retain a safe `TurnLifecycleError.category` on failure;
- project failed watchdog/ledger/child outcomes to nonzero parent exit;
- never use the P7.C14 ledger or token as successor replay authority;
- leave the retained P7.C14 orphan session untouched unless a separate cleanup contract is later authorized.

`P7C14_FORENSIC_ARCHITECT_ACCEPTED=YES`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C15_PREPARATION_AUTHORIZED=YES`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
