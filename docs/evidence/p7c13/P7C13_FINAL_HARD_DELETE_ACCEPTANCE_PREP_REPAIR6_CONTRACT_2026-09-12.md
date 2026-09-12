# P7.C13 preparation Repair-6 contract — final Turn-4 post-join snapshot — 2026-09-12

Status: **FROZEN / MICRO REPAIR / ZERO REAL EFFECT / NO REAL EXECUTION**

## Exact base

Repair-6 starts from exact Repair-5 candidate:

- commit: `c09b5b3dfb197a647bd2f732ed343d42bf4aec0e`;
- tree: `4ecd65c7a251b5931b579b3b324724731fda785b`;
- harness blob: `cb64f44bc71339300e2d697167daa08b0b601f15`;
- evidence blob: `d9baf8af54b9b2bc6597ed7c5b2db5933ee7f184`.

Binding review:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_REPAIR5_ARCHITECT_REVIEW_2026-09-12.md`

## Scope

This is one micro race repair only.

Do not redesign or modify accepted Repair-4/Repair-5 behavior outside the Turn-4 observer close/final-snapshot path and its tests/evidence.

Allowed tracked files:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`

Optional one P7.C13-only test helper only if strictly required.

No `src/**`, no matcher change, no historical P7.C6-P7.C12 mutation.

## Zero-effect boundary

All real Codex/app-server/RPC/thread/Turn/approval/interrupt/delete/persistent-home/controller/approval-target/Telegram/process-signal effects remain `0`.

Do not set or invent the future execution token.

Do not execute `--p7c13-real-run`.

## Required semantic correction

The final PASS/non-PASS fact for the Turn-4 request observer must be based on a terminal post-join/post-close classification, not only a pre-join `task.done()` snapshot.

The implementation must distinguish at least these terminal observer classes:

1. `REQUEST_OBSERVED` — task completed normally with one server request before observer closure;
2. `CANCELLED_BY_HARNESS_WITHOUT_REQUEST` — harness cancellation won before any request was delivered;
3. `OBSERVER_ERROR` — any other exception/fault/ambiguous class.

Rules:

- `REQUEST_OBSERVED` => `unexpected_request_count=1`, non-PASS;
- `CANCELLED_BY_HARNESS_WITHOUT_REQUEST` => zero unexpected request and not an observer fault;
- `OBSERVER_ERROR` => non-PASS;
- no second protocol response is sent in any class;
- Turn-3 `approval_responses=1`, `allow_responses=1`, `deny_responses=0` remain unchanged;
- if request arrives during the final close/join window, it must be classified as `REQUEST_OBSERVED`, not lost;
- final PASS predicate must consume this terminal observer classification after both owned tasks are terminalized/joined;
- controller DB binding and `DialogueDeleteService.delete()` remain unreachable on any positive/ambiguous observer class.

## Deterministic required tests

Add/retain offline tests proving:

1. ordinary no-request path closes observer by harness cancellation and can PASS;
2. request before active window => non-PASS;
3. request during interrupt => non-PASS;
4. request before terminal convergence => non-PASS;
5. same-tick request+terminal => non-PASS;
6. **late request after the preliminary snapshot but before/during final observer join** => non-PASS;
7. late-request case has protocol response callback count `0`;
8. late-request case leaves approval/ALLOW/DENY accounting unchanged at `1/1/0`;
9. late-request case reaches controller/delete callback count `0`;
10. harness-owned cancellation with no delivered request is not misclassified as observer fault;
11. observer exception is non-PASS;
12. both observer and terminal waiter are done after return; no detached task.

The late-window test must control scheduling explicitly; a generic timing sleep that does not prove the former race window is insufficient.

## Validation

Run:

- focused P7.C13 Repair-6;
- accepted P7.C12 focused suite;
- relevant C2-C5 fake/non-real regressions;
- complete non-real pytest with real gates unset;
- unittest discovery with real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

After the final evidence edit, rerun compileall, diff-check, and leakage scan.

## Evidence

Update the existing P7.C13 preparation evidence with:

`REPAIR6_BASE_HEAD=c09b5b3dfb197a647bd2f732ed343d42bf4aec0e`

`REPAIR6_BASE_TREE=4ecd65c7a251b5931b579b3b324724731fda785b`

`PRIOR_HARNESS_BLOB=cb64f44bc71339300e2d697167daa08b0b601f15`

Record final harness/evidence blobs and the deterministic late-window proof.

Required final lines:

`P7C13_REPAIR6_POST_JOIN_REQUEST_SNAPSHOT=PASS|FAIL`

`P7C13_REPAIR6_HARNESS_CANCELLATION_CLASS=PASS|FAIL`

`P7C13_REPAIR6_NO_SECOND_RESPONSE=PASS|FAIL`

`P7C13_REPAIR6_DELETE_UNREACHABLE_ON_LATE_REQUEST=PASS|FAIL`

`P7C13_REPAIR6_TASK_OWNERSHIP=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Commit and push only to:

`prep-p7-c13-final-hard-delete-acceptance-repair6-2026-09-12`

No force, no rebase, no main mutation.

After remote readback, STOP. Do not execute the real run.
