# P7.C7 DENY-only approval-probe preparation Repair-5 — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `9acd8238092bfb351c093209e7fa6c40951d4b47`.
- Base tree: `54e6168e5f8bd9ba3ed7afc118dd30b79dab1545`.
- Repair-5 candidate: `b78b9fe93423c456e4557926745f9109e3992ea8`.
- Candidate tree: `d395857adabf8e19c7524566258614c4180bdd4b`.
- Candidate is exactly one commit ahead of the architect base and changes only the P7.C7 real-test harness plus Repair-5 evidence. No `src/**` change occurred.

## Repair-5 improvements accepted as useful

Independent review confirms Repair-5 closes the Repair-4 durable-authority defects it targeted:

- parent execution-outcome facts are measured rather than optimistically defaulted;
- global latch presence and normal-final-result presence are measured at outcome construction time;
- child-result discovery is bounded/read-only and distinguishes confirmed, missing, ambiguous and unreadable states;
- timeout/residual/scan-error classes can retain truthful child-result-present/valid facts without being upgraded to normal success;
- `child_returncode_class` is narrowed to child execution classes;
- class-to-facts validation rejects contradictory parent outcomes;
- post-child authority requires exactly one child, no retry and no second child;
- RecoveryJournal initial creation is exclusive and later appends do not use `O_CREAT`;
- later appends are checked against the retained creation identity and replacement/unlink/mode/hardlink failures are fail-closed;
- journal continuity failure prevents the next effect from dispatching;
- all previously accepted DENY-only, queued-request, request-before-response, wire/adapter-stage, owner-terminalization, observation-budget, process-group and one-shot gates remain present.

These properties remain binding.

## Remaining deterministic blocker — normal result writes false lifecycle effect counts

`make_sanitized_result(...)` still emits:

- `model_list_calls: 0`;
- `thread_start_calls: 0`;
- `turn_start_calls: 0`.

Those values are literal constants even when a real `FutureProbeBudget` object is supplied.

That is false for every normal future P7.C7 probe result. The normal child-result path is reachable only after the frozen real sequence has successfully progressed through:

1. one authenticated `model/list` request;
2. one fresh `thread/start` request with adapter confirmation;
3. one primary `turn/start` request with adapter confirmation;
4. finite approval/terminal observation;
5. runtime shutdown and child boundary proof.

`FutureProbeBudget` already counts those real dispatches, but the child-result projection discards those counts and writes zero. `validate_parent_final_result(...)` compounds the problem by requiring only `<= 1`, so a normal durable parent result containing false zero values is accepted.

This is not a production protocol defect. It is a deterministic test-harness/result-projection defect.

## Required Repair-6 correction

Repair-6 must be limited to effect-ledger truthfulness and adjacent exact-normal-result invariants.

For a normal child result with an authoritative budget:

- `model_list_calls = budget.model_list_calls`;
- `thread_start_calls = budget.thread_start_calls`;
- `turn_start_calls = budget.turn_start_calls`;
- existing zero values for resume/interrupt/delete/read/list remain zero;
- DENY counters remain projected from the authoritative budget.

A normal child result must require exactly:

- `model_list_calls == 1`;
- `thread_start_calls == 1`;
- `turn_start_calls == 1`;
- `fresh_thread_sha256` present and valid;
- `fresh_turn_sha256` present and valid.

The normal parent-final validator must require the same exact `1/1/1` counts, not merely upper bounds.

Failure/outcome authority must remain separate and must not fabricate normal effect counts when no valid normal child result exists.

Offline tests must prove:

- a synthetic normal child built with budget `1/1/1` persists exactly `1/1/1`;
- zero/partial counts are rejected by normal child validation;
- zero/partial counts are rejected by normal parent-final validation;
- forbidden lifecycle counts remain exactly zero;
- DENY accounting remains unchanged and truthful;
- all Repair-5 outcome/journal-continuity tests remain PASS.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR5=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
