# P7.C7 DENY-only approval-probe preparation Repair-3 — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `05107b7c2d1afd547fc6ab253f62b528649268c7`.
- Base tree: `b53a874101c74dda30d80ada9e236e02201416a6`.
- Repair-3 candidate: `6cb422b5ef6dc5ad0a63580fa052f298f940c5fc`.
- Candidate diff is exactly one commit and changes only the P7.C7 test harness plus Repair-3 evidence. No `src/**` change occurred.

## Repair-3 improvements accepted as useful

Independent source review confirms Repair-3 closes the six Repair-2 blockers it targeted:

- a dedicated parent-final writer validates the parent schema, uses exclusive private persistence, performs bounded readback and requires equality;
- request-observed journaling is now in the DENY decision boundary before a response may be dispatched;
- request-journal failure blocks the response path;
- wire-level and adapter/catalog semantic results use distinct durable stage names;
- parent performs a post-quiescence boundary recheck and records child/parent boundary classes plus drift;
- watchdog child classifications distinguish completed, nonzero, timeout, residual group and scan error;
- normal child-result authority requires approval/terminal owners to be terminalized and nonconvergence blocks a normal child result;
- Repair-2 queued-request capture, DENY-only operator, finite stage waits, exact source gate, process-group ownership and no forbidden lifecycle calls are preserved.

These properties remain binding.

## Blocker A — parent recheck false-fails on the harness's own child-result file

The child performs its local boundary scan before writing `probe-child-result.json`, then writes that child result and exits.

The parent subsequently reconstructs the run root and calls `scan_fresh_run_boundary(...)` after group quiescence. However the scanner's allowed run-root authority set includes `probe-recovery.json`, `wire-command-recovery.json`, `probe-result.json` and `probe-latch.json`, but does **not** include the actual `CHILD_RESULT_FILENAME` (`probe-child-result.json`).

Therefore a healthy child can have a clean child-local boundary, write its required child result, exit cleanly, and the parent recheck will classify that legitimate harness-generated file as an unexpected root sibling. The child/parent boundary classes then differ and `BOUNDARY_DRIFT_DETECTED` prevents a valid parent-final authority.

This is a deterministic happy-path false failure.

Repair-4 must explicitly classify the child-result file as harness-owned authority during the parent post-quiescence scan, while still validating it as a safe root-owned regular authority file. It must not broadly allow arbitrary sibling files.

Offline proof must execute this exact sequence: clean child scan -> valid child-result write -> parent recheck -> `BOUNDARY_DRIFT_NONE`.

## Blocker B — observation horizon is shorter than the candidate stimulus itself

The candidate prompt asks for exactly `sleep 30` followed by one touch. Repair-3 retains `PROBE_OBSERVATION_TIMEOUT=10.0` seconds and a total watchdog hard deadline of 58 seconds.

The DENY-only probe has two legitimate empirical branches:

1. an approval request appears before command execution and is denied;
2. no approval request appears and the turn is allowed to complete naturally, after which terminal/sentinel state is observed.

The second branch cannot complete inside a 10-second observation window because the requested command itself contains a 30-second sleep, before model/tool latency and terminal propagation are considered. A healthy no-approval run is therefore forced into a timeout/nonconvergence classification before it can establish the intended empirical result.

Repair-4 must define a real observation horizon that strictly dominates the bounded candidate command duration plus explicit model/tool/terminal margin. The parent watchdog deadline must then be recalculated from the complete internal worst-case budget plus margin.

Synthetic tests may still use short explicit test-only timeouts; real mode may not inherit them.

Offline authority must prove at minimum:

`REAL_OBSERVATION_TIMEOUT > CANDIDATE_SLEEP_SECONDS + OBSERVATION_MARGIN_SECONDS`

and:

`REAL_WATCHDOG_HARD_DEADLINE > INTERNAL_WORST_CASE_SECONDS + WATCHDOG_MARGIN_SECONDS`.

## Blocker C — parent failure classes are not durably materialized

Repair-3 computes exact watchdog classifications, but `run_future_real_probe_parent()` raises before parent-final persistence when there are active group members or process-group scan errors. A missing child result after timeout similarly becomes an exception without a dedicated root-only parent failure authority.

For a one-shot probe, timeout/residual/scan-error/missing-child-result are terminal outcomes and must remain reviewable after the invocation is consumed. They must not rely only on process stderr or an in-memory local variable.

Repair-4 must add one exact, sanitized, root-only parent execution outcome authority that is written once for both normal and failure classes, without manufacturing observational success. It must distinguish at least:

- `CHILD_COMPLETED`;
- `CHILD_NONZERO`;
- `CHILD_TIMEOUT`;
- `CHILD_GROUP_RESIDUAL`;
- `CHILD_GROUP_SCAN_ERROR`;
- `CHILD_RESULT_MISSING_OR_INVALID`;
- `PARENT_BOUNDARY_INVALID_OR_DRIFTED`.

A failure authority must never be accepted by the normal parent-final result validator and must contain no raw thread/Turn/command/sentinel data. The global one-shot latch remains the replay barrier; no failure class permits retry.

## Additional observation — retain exact parent-result semantics

The dedicated parent-final writer itself is accepted. Repair-4 must preserve child/parent schema separation and exact readback equality. It should add a distinct failure-outcome schema/writer rather than weakening the normal parent-final validator.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR3=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
