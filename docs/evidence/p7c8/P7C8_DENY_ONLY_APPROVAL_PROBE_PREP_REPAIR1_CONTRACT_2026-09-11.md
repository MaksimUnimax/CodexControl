# P7.C8 DENY-only approval-probe preparation Repair-1 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY REPAIR**

## Purpose

Repair only the runtime-acquire containment and durable acquisition-authority defects found in architect review of candidate `9297395efb678356255d91aa8d90001a5fc768e0`.

This contract authorizes no real P7.C8 execution.

## Candidate authority

- Reviewed candidate: `9297395efb678356255d91aa8d90001a5fc768e0`.
- Candidate tree: `291fddbbef8a67dc918a730d363c086cbb910db3`.
- P7.C7 remains consumed and forensic-only.

## Preserve unchanged safety architecture

Repair-1 must preserve all already-correct P7.C8 properties: new P7.C8 namespace, DENY-only operator, zero ALLOW path, exact Turn authority before approval dequeue, exact identity before wire capture, max three DENY attempts, zero resume/interrupt/delete/read/list, normal exact model/list=1 + thread/start=1 + turn/start=1, fresh thread/Turn hashes, one parent child, no retry, exact process-group ownership, immutable recovery-journal inode, child/parent result separation, measured parent facts, 30-second stimulus, 100-second observation, 205-second parent watchdog, source HEAD/tree/clean gate and exclusive P7.C8 one-shot authorities.

## Repair A — bounded cleanup cancellation/join

`RuntimeAcquireObserver.contain()` must never use an unbounded await after cleanup timeout.

Freeze an explicit test-harness constant:

`P7C8_RUNTIME_ACQUIRE_CLEANUP_CANCEL_JOIN_SECONDS=1.0`

Synthetic tests may inject smaller values.

On cleanup timeout:

1. mark cleanup timeout fact;
2. cancel the cleanup task once;
3. join it for at most the cancel-join bound;
4. if it terminalizes, retain `TIMEOUT` as cleanup result;
5. if it does not terminalize, classify cleanup `NONCONVERGENT`;
6. never wait unboundedly;
7. leave the dedicated parent process-group watchdog as final process owner.

No hidden second shutdown task and no retry.

## Repair B — final acquisition classification after containment

Keep the initial observation event:

`RUNTIME_ACQUIRE_RESULT` = one of `CONFIRMED`, `TIMEOUT`, `SAFE_EXCEPTION`, `UNEXPECTED_EXCEPTION`, `CANCELLATION_NONCONVERGENT`.

After failed-acquire containment, persist exactly one additional final event:

`RUNTIME_ACQUIRE_FINAL_RESULT`.

The final class is derived from the returned post-containment `AcquireObservation`.

If cleanup or acquire-owner terminalization escalates the observation, the final event must reflect the escalated `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` class.

The real child must retain the returned containment observation; it may not discard it.

For confirmed acquisition, persist `RUNTIME_ACQUIRE_FINAL_RESULT=CONFIRMED` without running failed-acquire cleanup.

## Repair C — fail-closed parent acquisition authority

Introduce:

`RUNTIME_ACQUIRE_NOT_ESTABLISHED`.

This is a parent durable-evidence class only; it is never normal-success authority.

Parent acquisition recovery must return `NOT_ESTABLISHED` for any of:

- child run not uniquely discoverable;
- recovery journal absent/unreadable/unsafe;
- journal schema failure;
- no final acquisition result;
- duplicate/conflicting final acquisition result;
- invalid final value;
- success claimed without the required confirmed initial/final chronology.

Never default missing evidence to `CONFIRMED`.

Normal parent-final success requires exact `RUNTIME_ACQUIRE_CONFIRMED` from validated final journal authority.

## Repair D — safe cleanup error-category event

Do not call `RecoveryJournal.result(..., category=...)` unless the API is explicitly changed and fully tested.

Preferred durable form:

`RUNTIME_ACQUIRE_CLEANUP_RESULT=<class>`

plus optional separate event:

`RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY=<safe category>`.

Raw exception text, repr, traceback, stderr and environment remain forbidden.

## Repair E — complete finite RuntimeErrorSafe category set

Freeze an exact finite allowlist covering production runtime categories reachable from `CodexRuntimeManager.acquire()`, `_start()` and failed-acquire `shutdown_profile()` containment for this harness.

At minimum review and account for:

- `capability_mismatch`;
- `manager_shutting_down`;
- `unknown_profile`;
- `profile_reserved`;
- `profile_stopping`;
- `unresolved_process`;
- `storage_boundary_invalid`;
- `executable_invalid`;
- `process_streams_missing`;
- `initialize_failed`;
- `initialize_timeout`;
- `startup_failed`;
- `kill_reap_timeout`.

Every published category must also match `^[a-z][a-z0-9_]{0,63}$`.

If a `RuntimeErrorSafe.category` is syntactically safe but not in the frozen set, do not persist its raw category string. Persist only the fixed class `SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED` and fail closed for acceptance.

## Repair F — authoritative parent journal reader

Parent acquisition recovery must not use ordinary unbounded `Path.read_text()` as evidence authority.

Implement a bounded JSONL reader with:

- root-owned regular file;
- mode 0600;
- nlink 1;
- `O_RDONLY | O_NOFOLLOW | O_CLOEXEC`;
- bounded bytes and bounded record count;
- pre/post fd metadata equality;
- pre/post path metadata equality;
- stable device/inode;
- UTF-8 and JSON validation;
- accepted RecoveryJournal field/schema validation.

Any failure => `RUNTIME_ACQUIRE_NOT_ESTABLISHED`.

## Acquisition parent fact matrix

Normal parent-final success requires:

- final acquire result `RUNTIME_ACQUIRE_CONFIRMED`;
- no acquire error category;
- no failed-acquire cleanup result/category;
- exact normal 1/1/1 lifecycle ledger and all existing normal gates.

Failure outcome may preserve:

- initial acquisition class;
- final acquisition class;
- safe acquire error category;
- cleanup result;
- safe cleanup error category;

but may never fabricate success.

`RUNTIME_ACQUIRE_NOT_ESTABLISHED` is forbidden from normal result authority.

## Failed-acquire downstream boundary

For every non-confirmed final acquisition class:

- model/list = 0;
- thread/start = 0;
- turn/start = 0;
- approval responses = 0;
- resume = 0;
- interrupt = 0;
- delete = 0;
- read/list = 0;
- ALLOW = 0.

## Required offline tests

At minimum prove:

1. confirmed acquisition final class;
2. timeout + cleanup confirmed;
3. timeout + cleanup timeout + cooperative cancellation;
4. timeout + cancellation-resistant cleanup => finite `NONCONVERGENT`, no unbounded await;
5. acquire owner nonconvergent => final `CANCELLATION_NONCONVERGENT`;
6. safe exception categories for the complete frozen set;
7. unrecognized safe category is not persisted raw;
8. unexpected exception contains no raw message;
9. cleanup safe category persists through the dedicated safe event without `TypeError`;
10. missing child run => parent acquire `NOT_ESTABLISHED`;
11. missing journal => `NOT_ESTABLISHED`;
12. missing final acquire event => `NOT_ESTABLISHED`;
13. conflicting final acquire events => `NOT_ESTABLISHED`;
14. unsafe/replaced/symlink/hardlink/oversize journal => `NOT_ESTABLISHED`;
15. parent success rejects `NOT_ESTABLISHED`, timeout, safe/unexpected exception and cancellation nonconvergence;
16. journal intent failure blocks acquisition effect;
17. journal cleanup-intent failure blocks cleanup effect;
18. all non-confirmed acquisition classes have zero downstream effects;
19. all carried P7.C8 DENY/process/journal/result tests remain passing;
20. future real test remains skipped with all real auth variables unset.

## Real budgets retained

- acquire timeout: 45.0s;
- failed-acquire cleanup timeout: 12.0s;
- cleanup cancel-join: 1.0s;
- stimulus: 30.0s;
- observation: 100.0s;
- normal internal budget remains 186.0s unless the repair demonstrates a required recalculation;
- watchdog margin: 15.0s;
- watchdog hard deadline: 205.0s, and it must still dominate every real execution path including failed-acquire cleanup/cancel-join.

If the added 1-second cancel-join makes the frozen worst-case arithmetic inaccurate, recalculate the internal worst-case and increase the hard watchdog as necessary. Do not reduce any accepted stage timeout merely to preserve 205 seconds.

## Change scope

Allowed:

- `tests/real/test_p7_c8_deny_only_approval_probe.py`;
- optional P7.C8-only offline helpers/tests under `tests/**`;
- `docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_EVIDENCE_2026-09-11.md`.

Forbidden:

- `src/**`;
- P7.C7 harness/evidence/state;
- ADRs;
- CURRENT_WORK/ROADMAP/DECISIONS by executor;
- config/deployment.

Production change required => stop `P7C8_REPAIR1_PRODUCTION_CHANGE_REQUIRED`.

## Final state

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.