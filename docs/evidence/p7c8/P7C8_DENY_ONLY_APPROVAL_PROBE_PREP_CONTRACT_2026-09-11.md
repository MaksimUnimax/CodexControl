# P7.C8 DENY-only approval probe preparation contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / SUCCESSOR TO CONSUMED P7.C7 / REAL EXECUTION NOT AUTHORIZED**

## Purpose

Prepare a new fresh-thread DENY-only approval-probe successor after P7.C7 was permanently consumed before runtime acquisition completed.

P7.C8 is not a retry of P7.C7 and must not reuse any P7.C7 one-shot authority, run root, thread, Turn, latch, result, outcome, wire authority or recovery journal.

The first P7.C8 slice is preparation only. It authorizes zero Codex/app-server effects.

## Binding P7.C7 findings

P7.C7 forensic established:

- one real P7.C7 attempt only;
- global P7.C7 latch reserved;
- `RUNTIME_ACQUIRE_RESULT=NONCONVERGED`;
- no model/list stage recorded;
- no fresh thread;
- no fresh Turn;
- approval path not reached;
- no wire authority;
- production defect not established.

Architect review additionally establishes a P7.C7 harness defect:

- the harness wrapped the entire `CodexRuntimeManager.acquire()` path in a 5-second outer timeout;
- production runtime has a 15-second app-server initialize timeout;
- installed-version authority probing inside acquire has its own 3-second spawn, 3-second output and 3-second wait bounds;
- `_finite_await()` collapsed timeout and arbitrary exception into one false result, and P7.C7 recorded only `NONCONVERGED`, losing the safe exception category.

The exact concrete trigger of the consumed P7.C7 run remains `NOT_ESTABLISHED`.

## New namespace

P7.C8 must use distinct authorities, at minimum:

- authorization token: `AUTHORIZED_P7C8_DENY_ONLY_APPROVAL_PROBE_2026_09_11`;
- expected source envs: `CODEXCONTROL_P7C8_PROBE_EXPECTED_HEAD`, `CODEXCONTROL_P7C8_PROBE_EXPECTED_TREE`;
- profile ID: `p7c8-fresh-probe`;
- global latch: `/root/.codexcontrol/p7c8-deny-only-approval-probe-ledger.json`;
- global normal result: `/root/.codexcontrol/p7c8-deny-only-approval-probe-result.json`;
- global outcome: `/root/.codexcontrol/p7c8-deny-only-approval-probe-outcome.json`;
- fresh parent/run prefixes containing `p7c8`, never `p7c7`.

No P7.C7 authority may be used as an execution gate or reset to permit P7.C8.

## Runtime-acquire observation authority

P7.C8 must not reuse the P7.C7 generic `_finite_await` result for runtime acquisition.

Implement a dedicated acquisition observer with distinct finite outcomes:

- `RUNTIME_ACQUIRE_CONFIRMED`;
- `RUNTIME_ACQUIRE_TIMEOUT`;
- `RUNTIME_ACQUIRE_SAFE_EXCEPTION`;
- `RUNTIME_ACQUIRE_UNEXPECTED_EXCEPTION`;
- `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT`.

When `CodexRuntimeManager.acquire()` raises `RuntimeErrorSafe`, preserve only its safe `.category` in the root-only journal/result authority. Do not publish raw exception text or chained errors.

An arbitrary unexpected exception is recorded only as the fixed class `UNEXPECTED_EXCEPTION`; do not publish `repr`, traceback, environment or process output in durable sanitized authority.

Timeout must never be journaled as the same result as exception.

## Runtime-acquire horizon

Freeze preparation target values:

- `P7C8_RUNTIME_ACQUIRE_TIMEOUT_SECONDS=45.0`;
- `P7C8_RUNTIME_ACQUIRE_CLEANUP_TIMEOUT_SECONDS=12.0`.

Known named bounded startup components inside production source include:

- version spawn bound: 3s;
- version stdout/read bound: 3s;
- version process-wait bound: 3s;
- app-server initialize bound: 15s.

The sum of those named bounds is 24 seconds. The 45-second P7.C8 acquisition horizon must therefore exceed those named bounded stages with explicit margin.

Production app-server process creation itself is not separately bounded inside `CodexRuntimeManager._start()`. Therefore 45 seconds is a test-harness outer ceiling, not a claim that every internal production operation has a complete mathematical worst-case bound.

## Failed-acquire containment

On timeout or failed acquire:

1. persist the exact acquisition outcome before any containment effect;
2. cancel/join the outer acquire owner finitely;
3. invoke only owned `manager.shutdown_profile(profile_id)` containment under the 12-second cleanup authority where applicable;
4. persist cleanup outcome separately;
5. do not continue to model/list, thread/start or turn/start;
6. if cleanup does not converge, exit child failure and leave the dedicated parent process-group watchdog as final owner.

No thread/read/list/delete, resume, interrupt or approval response is authorized as acquire recovery.

## Full future process watchdog budget

Preserve the accepted P7.C7 values except for the corrected acquire horizon.

Preparation target:

- candidate sleep: 30s;
- observation margin: 60s;
- observation timeout: 100s;
- model/list: 5s;
- thread/start: 5s;
- turn/start: 5s;
- each approval-response observation: 5s, max 3;
- runtime shutdown: 5s;
- child-result read/write authority: 2s;
- TERM grace: 2s;
- KILL grace: 2s;
- runtime acquire: 45s.

The corresponding normal-path internal budget is 186 seconds. Freeze:

- `P7C8_INTERNAL_WORST_CASE_SECONDS=186.0`;
- `P7C8_WATCHDOG_MARGIN_SECONDS=15.0`;
- `P7C8_WATCHDOG_HARD_DEADLINE=205.0`.

Require strictly:

`205 > 186 + 15`.

Synthetic tests may use smaller explicitly test-only values. Real mode may not inherit synthetic limits.

## Durable acquisition chronology

Before acquisition:

- source gate;
- one-shot latch reservation;
- `RUNTIME_ACQUIRE_INTENT`.

Then record exactly one terminal acquire result:

- `CONFIRMED`;
- `TIMEOUT`;
- `SAFE_EXCEPTION` with safe category;
- `UNEXPECTED_EXCEPTION`;
- `CANCELLATION_NONCONVERGENT`.

If acquisition fails, also record `RUNTIME_ACQUIRE_CLEANUP_INTENT/RESULT` where containment is attempted.

The parent execution outcome must include sanitized acquisition status/category/cleanup status so that a future consumed run can be diagnosed without replay.

## Retained P7.C7 safety authorities to preserve

P7.C8 preparation must carry forward, with new P7.C8 names:

- DENY-only operator with zero ALLOW code paths;
- exact Turn authority before approval dequeue;
- buffered queued-request capture;
- exact thread/Turn/cwd gate before authoritative wire capture;
- request-observed journal before DENY response intent;
- at most three DENY attempts;
- response ambiguity consumes one attempt and is never retried;
- exact `1/1/1` normal model-list/thread-start/turn-start ledger;
- valid fresh thread/Turn SHA-256 required for normal child/final result;
- resume/interrupt/delete/read/list exact zero;
- immutable recovery-journal creation-time device/inode;
- no later journal `O_CREAT`;
- replacement/unlink/symlink/hardlink/mode/owner drift fail closed;
- dedicated one-child parent with `start_new_session=True`;
- exact owned process-group TERM <= 1 and KILL <= 1;
- no second child and no retry;
- child-result vs parent-final separation;
- measured parent outcome facts;
- post-quiescence parent boundary recheck;
- child result treated as exact harness-owned authority;
- distinct durable parent failure outcome;
- exact source HEAD/tree/clean gate;
- one-shot semantics once a future P7.C8 real execution is separately authorized.

## Zero-effect preparation scope

Allowed repository work:

- new `tests/real/test_p7_c8_deny_only_approval_probe.py`;
- optional P7.C8-only offline helpers under `tests/**`;
- one sanitized P7.C8 preparation evidence file.

Do not modify `src/**`.

Do not modify the consumed P7.C7 harness/evidence to make P7.C8 pass.

During preparation:

- real P7.C8 authorization token unset;
- real expected HEAD/tree envs unset;
- real P7.C8 unittest skipped;
- no P7.C8 global latch/result/outcome created;
- no Codex/app-server child;
- no real RPC;
- no process signal to real Codex;
- no P7.C7 mutation.

## Required offline acquisition tests

At minimum prove:

1. successful acquire -> `CONFIRMED` and safe runtime returned;
2. `RuntimeErrorSafe("capability_mismatch", ...)` -> `SAFE_EXCEPTION`, category preserved;
3. `RuntimeErrorSafe("storage_boundary_invalid", ...)` -> category preserved;
4. arbitrary exception -> `UNEXPECTED_EXCEPTION`, no raw message persisted;
5. timeout -> `TIMEOUT`, not `SAFE_EXCEPTION`;
6. cancellation owner fails to converge -> `CANCELLATION_NONCONVERGENT`;
7. failed acquire never reaches model/list/thread/start/turn/start;
8. failed acquire cleanup is finite and separately classified;
9. cleanup failure does not trigger retry;
10. journal-intent failure blocks acquire dispatch;
11. normal acquire timeout constant is 45s and exceeds the 24s named bounded startup components with margin;
12. full watchdog budget relation is exact and real mode uses 205s, not legacy 165s.

## Required offline regression

The P7.C8 test suite must additionally prove all carried-forward DENY-only, race, wire authority, process group, boundary, journal, measured outcome, effect-budget and normal `1/1/1` properties.

Run focused production adapter suites and exactly one full test discovery with all real authorization variables unset.

## Final preparation disposition

Preparation may only produce:

`P7C8_DENY_ONLY_PROBE_PREPARATION_COMPLETE`

or a finite fail-closed preparation failure.

It may not authorize a real P7.C8 probe by itself.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
