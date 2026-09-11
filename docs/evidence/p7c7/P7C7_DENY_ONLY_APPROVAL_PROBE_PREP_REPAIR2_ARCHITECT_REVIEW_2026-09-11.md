# P7.C7 DENY-only approval-probe preparation Repair-2 — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `8205af59196eca7e8b8d3ebc57bd131a3bf1980a`.
- Base tree: `97c234bfac6aa2caedd0daafdca1de85a847edb5`.
- Repair-2 candidate: `388b1a1bf46b56bc1734bbf2e3eb630266b822a7`.
- Candidate tree: `45cfb17776d70d41cef9b1b503ffd7dbf6bed088`.
- Candidate diff is exactly one commit and changes only the P7.C7 test harness plus Repair-2 evidence. No `src/**` change occurred.

## Repair-2 improvements accepted as useful

Independent review confirms Repair-2 materially advances the disabled future real path:

- the operator remains DENY-only with zero ALLOW decision paths;
- exact Turn authority is established before the approval observer starts;
- production protocol buffering can preserve a fast approval request until the observer dequeues it after Turn confirmation;
- wrong identity does not consume wire authority;
- a root-only recovery journal exists and effect intent is generally written before real effects;
- DENY attempts are reserved before production response dispatch and ambiguous response outcomes consume an attempt;
- maximum DENY attempts remains three; no ALLOW path is introduced;
- named finite inner timeouts and an auditable watchdog budget are present;
- the future real unittest now uses a parent launcher and exactly one `start_new_session=True` child;
- child and parent result schemas are separated;
- `/proc` PID disappearance is separated from malformed/unreadable stat failures;
- runtime-owned sqlite/log payload is separated from command-owned mutation surface;
- final runtime shutdown precedes child-local boundary proof.

These properties remain binding for Repair-3.

## Blocker A — parent final result cannot be persisted

`run_future_real_probe_parent()` builds an extended parent-final value through `make_parent_final_result(...)`, but then calls `write_sanitized_result(REAL_PROBE_RESULT, final)`. That writer always calls `validate_sanitized_result(...)`, whose exact key set is the child-local schema. Parent-only keys therefore make the global final write fail with `SANITIZED_RESULT_SCHEMA_INVALID`.

Repair-3 must provide a dedicated parent-final writer using `validate_parent_final_result(...)`, then the same exclusive/private/fsync write. Offline proof must persist and re-read a valid parent-final synthetic record.

## Blocker B — request-observed journal chronology is too late

`APPROVAL_REQUEST_<N>_OBSERVED` is currently appended only after `_observe_future_race(...)` returns, although a DENY may already have been dispatched during the race. A crash during response send can therefore leave DENY dispatch intent without a prior durable request-observed record.

Repair-3 must durably append sanitized request-observed authority before returning the DENY decision that allows the bridge to reach its response path. Journal failure must block the response dispatch.

## Blocker C — wire-level and adapter-level results are conflated

The patched client records `MODEL_LIST_RESULT`, `THREAD_START_RESULT` and `TURN_START_RESULT` on finite wire return. Thread/turn adapters then validate the response and the child writes thread/turn result rows again. Malformed responses can therefore produce contradictory records; model-list can be called `CONFIRMED` although catalog parsing later fails.

Repair-3 must split semantic layers explicitly, for example:

- `MODEL_LIST_WIRE_RESULT` vs `MODEL_CATALOG_RESULT`;
- `THREAD_START_WIRE_RESULT` vs `THREAD_START_ADAPTER_RESULT`;
- `TURN_START_WIRE_RESULT` vs `TURN_START_ADAPTER_RESULT`.

No stage name may represent two semantic layers. Malformed-response offline tests are required.

## Blocker D — child boundary proof can become stale before parent quiescence

The child scans workdir/sentinel/root after runtime shutdown, but the parent only later proves or enforces full process-group quiescence. A surviving descendant can mutate command-owned state between those moments.

Repair-3 must perform a final read-only boundary recheck in the parent after exact group quiescence. Parent-final authority must use that post-quiescence result or reject any drift from the child result. No evidence may be deleted before recheck.

## Blocker E — watchdog timeout loses its exact classification

`CHILD_RETURN_TIMEOUT` exists, but parent finalization chooses only completed vs generic nonzero from return code. A watchdog-killed child can therefore be mislabeled `CHILD_NONZERO` if a child result exists.

Repair-3 must derive child return classification from watchdog facts and preserve normal completed, normal nonzero, hard timeout, group residual failure and scan failure distinctly.

## Blocker F — child result does not require owned observer convergence

`ProbeObservation.observer_joined` exists but is not a child-result gate. A cancellation-resistant approval or terminal task can remain pending while a normal child result is still written.

Repair-3 must make owner terminalization explicit. Normal child-result materialization requires every approval/terminal owner terminalized. Nonconvergence must be durably classified and cannot masquerade as a normal observation result.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR2=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
