# P7.C14 real execution — architect review — 2026-09-12

Status: **FINAL FAIL / RUN CONSUMED / REAL-EFFECT BOUNDARY UNRESOLVED / HARD-DELETE NOT ACCEPTED / NO RETRY**

## Reviewed authority

Sanitized real evidence branch:

- branch: `real-p7-c14-final-hard-delete-acceptance-2026-09-12`;
- evidence head: `2676e4c9eeb3f343112d41c3307948599fc81837`;
- evidence tree: `2abd7132c374c829ab683c3c0b4894ea4aa74b02`;
- evidence blob: `f06b469c8ea6afb5d6925a95c7de8f2293500544`;
- execution source: `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- execution tree: `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

The real branch is exactly one commit ahead of the accepted executable source and adds only the sanitized P7.C14 evidence file.

## Accepted terminal facts

P7.C14 was invoked exactly once and is permanently consumed.

The supported terminal facts are:

- P7.C14 ledger state `FAILED`;
- child result status `FAILED`;
- child verdict `false`;
- child failure class `FAIL_CLOSED`;
- child terminal exception class `TurnLifecycleError`;
- deletion stage not established as reached; official/application delete classes are unavailable;
- second-child count `0`;
- retry count `0`;
- P7.C14 retry remains forbidden;
- P7.C13 retry remains forbidden.

No PASS inference is permitted from parent exit `0`.

## Architect-discovered evidence defect: failure-path effect accounting

The inherited production child path creates a fresh budget inside `build_production_real_seam_factory(...)` and stores it on `ProductionRealChildOrchestrator.budget`.

On the success path `_future_child_main()` explicitly switches to `result_budget = child.budget` before writing the child result.

On the exception path, however, `_future_child_main()` writes the FAIL_CLOSED child result using the separate outer `budget` created before the production child is built. That outer budget is not the budget mutated by `ProductionRealChildOrchestrator.run_async()`.

Therefore the P7.C14 sanitized evidence statement that every real-effect count was zero is **not architect-accepted as factual dispatch authority**. The failure result can report zeros even after production-child budget reservations occurred before the exception.

The exact real-effect boundary is currently:

`UNRESOLVED_FROM_SANITIZED_CHILD_RESULT`.

This does not imply that effects occurred; it means the current evidence cannot prove that they did not.

## Architect-discovered parent exit projection defect

The P7.C14 module entrypoint catches only `P7C14PreparationGateError`. If the real entrypoint returns a failed `WatchdogResult`, the module returns process exit `0` without projecting the failed ledger/child state into its exit code.

Accordingly:

`PARENT_EXIT=0` is not a PASS fact and must not be used as acceptance authority for this run.

The authoritative terminal result remains ledger `FAILED` + child `FAILED`.

## TurnLifecycleError evidence limitation

The inherited production child exception writer records only `type(error).__name__` and a generic `FAIL_CLOSED` class. It does not preserve the `TurnLifecycleError.category`, exact stage, or last confirmed lifecycle boundary in the sanitized child result.

The exact category and stage therefore cannot be reconstructed from the Git evidence alone.

## Required next step

Do not prepare or authorize another real run yet.

First perform a zero-real-effect retained forensic pass over the already-created P7.C14 root-only authorities and persisted local state to determine, as far as physically supportable:

- exact installed/runtime start boundary;
- whether model/list was dispatched/confirmed;
- whether thread/start was dispatched/confirmed;
- whether a fresh thread binding was materialized;
- whether any turn/start was dispatched/confirmed;
- the most precise recoverable `TurnLifecycleError` category/stage;
- whether a P7.C14-created thread/session remains in persistent or isolated storage;
- whether approval/interrupt/delete were definitely not reached;
- whether any orphan current-run process or filesystem boundary remains.

No new Codex/app-server process, RPC, approval response, interrupt, delete or cleanup is permitted in that forensic pass.

Only after this forensic result may a distinct successor (P7.C15) preparation contract be frozen. That successor must additionally correct:

1. failure-path effect accounting so the actual production child budget is persisted even on exceptions;
2. parent CLI exit projection so a failed watchdog/ledger/child cannot return success exit;
3. stage/category recovery authority sufficient to classify a future failure without guessing.

## Authorization state

`P7C14_REAL_RUN_CONSUMED=YES`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_FINAL_VERDICT=FAIL`

`P7C14_REAL_EFFECT_BOUNDARY=UNRESOLVED`

`P7C14_HARD_DELETE_ACCEPTED=NO`

`P7C14_RETAINED_FORENSIC_REQUIRED=YES`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
