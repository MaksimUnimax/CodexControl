# P7.C7 DENY-only approval-probe preparation Repair-6 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / HARNESS-ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

Repair-5 closes the durable parent-outcome and recovery-journal continuity defects it targeted. Independent architect review found one remaining deterministic normal-result truthfulness defect: normal child/final result authority writes false zero counts for `model/list`, `thread/start` and `turn/start` even though the authoritative `FutureProbeBudget` has observed one of each.

Repair-6 must close only this effect-ledger projection defect and make the exact normal-result invariants explicit.

No real P7.C7 Codex operation is authorized by this contract.

## Reviewed candidate

Repair-5 candidate:

`b78b9fe93423c456e4557926745f9109e3992ea8`

Candidate tree:

`d395857adabf8e19c7524566258614c4180bdd4b`

## Absolute boundary

Repair-6 has zero real effects:

- no Codex/app-server start;
- no model/list;
- no thread/start/resume/read/list/delete;
- no turn/start/interrupt;
- no approval response;
- no Telegram;
- no signal to a real Codex process;
- no P7.C6 mutation;
- no real P7.C7 latch/result/outcome authority.

Production `src/**` remains frozen.

## Preserve all accepted Repair-5 properties

Do not weaken:

- DENY-only operator / zero ALLOW path;
- exact Turn authority before approval dequeue;
- queued request capture after Turn confirmation;
- exact thread/Turn/cwd gating for authoritative wire capture;
- request-observed journal before DENY intent;
- request-journal failure blocks response;
- exact wire schema/hash consistency;
- separate wire and adapter/catalog result stages;
- maximum three DENY attempts and truthful ambiguity accounting;
- owner-terminalization gate;
- real observation authority 100 seconds for frozen 30-second stimulus;
- watchdog deadline dominance at 165 seconds over 146-second internal budget;
- one dedicated parent/one child/no retry;
- `start_new_session=True` process-group ownership;
- exact-group TERM/KILL maximum once each;
- child-result phase-aware boundary authority;
- post-quiescence parent boundary recheck;
- strict normal parent-final writer/readback;
- distinct durable parent execution-outcome authority;
- measured latch/result/child-result facts;
- narrow child execution-class enum and parent outcome semantic matrix;
- immutable RecoveryJournal inode/device continuity;
- later journal appends without `O_CREAT`;
- fail-closed journal replacement/unlink/mode/hardlink behavior;
- source HEAD/tree/clean gate;
- exclusive global one-shot latch;
- zero resume/interrupt/delete/read/list.

## R6-A — normal child result projects the authoritative budget

When `make_sanitized_result(...)` is supplied an authoritative `FutureProbeBudget`, require:

- `model_list_calls = budget.model_list_calls`;
- `thread_start_calls = budget.thread_start_calls`;
- `turn_start_calls = budget.turn_start_calls`;
- `approval_deny_responses = budget.approval_deny_responses`;
- `approval_deny_attempts = budget.approval_deny_attempts`;
- `approval_deny_confirmed = budget.approval_deny_confirmed`;
- `approval_deny_unknown_or_failed = budget.approval_deny_unknown_or_failed`;
- `approval_allow_responses = budget.approval_allow_responses`.

Forbidden lifecycle fields remain exact zero:

- thread_resume_calls;
- interrupt_calls;
- thread_delete_calls;
- thread_read_calls;
- thread_list_calls.

Do not invent separate counters.

## R6-B — exact normal child invariant

A normal real child result can only be materialized after the real sequence has confirmed the fresh thread and primary Turn.

Therefore the normal child result validator must require exactly:

- `model_list_calls == 1`;
- `thread_start_calls == 1`;
- `turn_start_calls == 1`;
- `thread_resume_calls == 0`;
- `interrupt_calls == 0`;
- `thread_delete_calls == 0`;
- `thread_read_calls == 0`;
- `thread_list_calls == 0`;
- `approval_allow_responses == 0`;
- `fresh_thread_sha256` is a valid SHA-256 string;
- `fresh_turn_sha256` is a valid SHA-256 string.

A normal child result with 0 or partial `model/list`, `thread/start`, or `turn/start` counts is invalid.

Synthetic helper paths that need incomplete/zero lifecycle state must not use the normal real-child result schema unless they construct a fully synthetic normal `1/1/1` budget.

## R6-C — exact normal parent-final invariant

`validate_parent_final_result(...)` must require exact:

- model_list_calls == 1;
- thread_start_calls == 1;
- turn_start_calls == 1.

The old upper-bound-only condition (`> 1` rejection) is insufficient.

All other existing normal parent-final gates remain binding:

- PROCESS_COMPLETED;
- CHILD_COMPLETED;
- group active count 0;
- group scan errors 0;
- one child;
- no retry;
- all owners terminalized;
- valid boundary;
- no drift;
- no ALLOW;
- valid exact source SHA/tree.

## R6-D — effect count meaning

Counts represent dispatch attempts at the frozen external effect boundary.

For the normal result path, each of the three required real operations has one authoritative dispatch:

- one model/list;
- one thread/start;
- one turn/start.

Do not reinterpret counts as adapter confirmation counts.

Wire/adaptor semantic status remains separately journaled as already frozen.

## R6-E — failure/outcome authority stays separate

Parent execution-outcome authority may exist when no valid normal child result exists.

Do not add fake `1/1/1` lifecycle counts to parent failure outcome schema merely to satisfy normal result validation.

The normal child/final schema and parent failure/outcome schema remain separate.

## Required offline tests

At minimum prove:

1. normal synthetic `FutureProbeBudget` with one model/list, one thread/start and one turn/start projects exactly `1/1/1` into child result;
2. normal child result with model_list_calls=0 is rejected;
3. normal child result with thread_start_calls=0 is rejected;
4. normal child result with turn_start_calls=0 is rejected;
5. normal child result with any of the three counts >1 is rejected;
6. normal child result with missing/null thread hash is rejected;
7. normal child result with missing/null Turn hash is rejected;
8. normal parent-final result with any lifecycle count !=1 is rejected;
9. forbidden resume/interrupt/delete/read/list remain zero;
10. DENY 0..3 accounting remains valid and ALLOW remains zero;
11. Repair-5 parent outcome semantic matrix remains PASS;
12. Repair-5 child-result failure discovery remains PASS;
13. Repair-5 immutable journal inode/replacement tests remain PASS;
14. observation/watchdog dominance remains PASS;
15. real method remains skipped with all real authorities unset.

## Allowed repository changes

Only:

- `tests/real/test_p7_c7_deny_only_approval_probe.py`;
- optional offline-only helpers/tests under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR6_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, DECISIONS, config or deployment edits in the executor branch.

## Completion criterion

Repair-6 passes only if independent architect review can conclude that every normal child/final result truthfully records the exact real effect ledger `model/list=1`, `thread/start=1`, `turn/start=1`, retains every Repair-5 safety/evidence authority, and performs zero real effects during preparation.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR6=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
