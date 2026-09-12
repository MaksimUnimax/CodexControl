# P7.C13 preparation Repair-5 contract — final two safety gates — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / NARROW FINAL CORRECTION / NO REAL EXECUTION**

## Purpose

Repair-5 is limited to the two remaining blockers found in independent architect review of Repair-4 candidate `86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`.

No other Repair-4 behavior is to be redesigned.

After Repair-5 architect acceptance, the next action must be the separate one-shot real P7.C13 execution contract. No further implementation pass is intended or authorized by this contract.

## Exact base

Repair-5 must start from:

- commit: `86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`;
- tree: `2968187b6300e1ed03e336340aa906c199819d48`;
- harness blob: `61853860ed0955df6119edb288d22573299cd1b3`;
- evidence blob: `fe1d2df4b360c126b2d6d4b5d488caa9d83fbf51`.

Accepted P7.C12 matcher remains immutable:

`f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Repair-5 must obey in full:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_REPAIR4_ARCHITECT_REVIEW_2026-09-12.md`.

## Absolute zero-real-effect boundary

Repair-5 implementation and testing remain offline only.

All real Codex/app-server starts, model/thread/Turn RPCs, approval responses, ALLOW/DENY, interrupts, deletes, persistent-home/controller/isolated/target mutation, real P7.C13 ledger/boot/result creation, Telegram and real-process signals must remain `0`.

Do not set or invent the future architect authorization token.

Do not execute `--p7c13-real-run`.

Historical P7.C6–P7.C12 real authorities remain immutable.

## A. Preserve accepted Repair-4 material

Do not weaken or redesign any Repair-4 component listed as accepted in the Repair-4 architect review, including source gate, topology, timeouts/watchdog, C11 wire authority, P7.C12 matcher, single protocol response, physical oracle, official delete observation, controller/tombstone proof, UNKNOWN/pending semantics and child/parent quiescence.

## B. External-user classification must distinguish source/shared authorities from destructive run-owned authorities

`production_read_only_boundary_preflight()` must still inspect and report every frozen boundary and preserve mount/alias/root-ownership validation.

External-user blocking must be classified by boundary role.

Allowed/report-only external users:

- `persistent_home` — shared authenticated home under ADR-0045;
- `repository` — read-only source authority and expected parent/executor cwd;
- `controller_root` — global private authority root, not itself the fresh destructive controller DB.

Blocking external users:

- `isolated_root`;
- `isolated_sqlite`;
- `isolated_logs`;
- `controller_db`;
- `workdir`;
- `approval_target`;
- `ledger`;
- `boot`;
- `result`.

A user of any blocking exact boundary must fail before authenticated business RPC/destructive work.

Do not suppress mount aliases or physical aliases merely because a boundary is report-only for process users.

Required tests:

1. nonzero `persistent_home` external-user count is allowed and reported;
2. nonzero `repository` external-user count is allowed and reported;
3. nonzero `controller_root` external-user count is allowed and reported;
4. each blocking boundary independently fails on nonzero external users;
5. mountpoint ambiguity still fails for repository/controller/shared boundaries;
6. physical alias still fails across all boundary classes;
7. a simulated live parent process using repository authority cannot consume/fail the child preflight merely for repository cwd authority.

## C. Turn-4 unexpected server-request observer is mandatory

The production real Turn-4 path must own TWO concurrent observation authorities from actual Turn-4 start until terminal convergence:

1. the exact Turn-4 terminal waiter;
2. one bounded unexpected-server-request observer on the current runtime protocol client.

The unexpected-request observer must not use `CodexApprovalBridge` and must never send a response.

It may use `client.next_server_request()` or an equivalent current protocol observation seam, but task ownership must be explicit and finite.

### Active-window classification

After Turn-4 `START_CONFIRMED`:

- if terminal wins before the active window: fail with interrupt dispatch `0`;
- if an unexpected server request is observed before/during the active window: mark Turn-4 unexpected-request failure, send no response, do not permit delete eligibility;
- if neither is observed during the bounded active window: active/nonterminal proof is established and the one interrupt may be reserved/dispatched.

### Through-interrupt observation

The unexpected-request observer must remain owned through interrupt and terminal convergence.

If a request appears:

- before interrupt,
- concurrently with interrupt,
- while waiting for final terminal,

then the final acceptance path is non-PASS.

There must be no second protocol response. The Turn-3 accounting remains:

`approval_responses=1`

`allow_responses=1`

`deny_responses=0`

for the successful Turn-3 path; an observed Turn-4 request adds no response count.

If an unexpected request is observed while Turn 4 is active, the single permitted exact Turn-4 interrupt may be used solely as owned cleanup. After cleanup/convergence the child must fail before controller DB creation/delete eligibility.

### Race semantics

If request and terminal facts become available in the same scheduler slice, fail closed as unexpected/ambiguous; do not choose PASS based on waiter ordering.

At final Turn-4 observation snapshot require:

- terminal authority definitive;
- unexpected request count `0` for PASS;
- request-observer owner terminalized/cancelled+joined;
- terminal waiter owner terminalized;
- no detached task.

Required tests:

8. no request + active Turn + interrupt + failed terminal passes Turn-4 gate;
9. terminal before active window => zero interrupt;
10. request before active timeout => no second response and no delete eligibility;
11. request during interrupt => non-PASS;
12. request before terminal convergence => non-PASS;
13. same-tick request+terminal => non-PASS;
14. observer cancellation/join leaves no pending task;
15. unexpected request keeps approval/ALLOW protocol-response totals at exactly `1/1` from Turn 3;
16. unexpected request path may use the one exact interrupt for cleanup but cannot reach controller/delete;
17. no `CodexApprovalBridge` or `respond_server_request` call exists in the Turn-4 observer path.

## D. Evidence correction

Update the existing P7.C13 evidence to describe Repair-5 truthfully.

Record exact base and final blobs plus final post-edit validation outcomes.

The evidence must not retain phrases saying compileall/diff-check are still pending if they were completed.

Required final lines:

`P7C13_REPAIR5_EXTERNAL_USER_CLASSIFICATION=PASS|FAIL`

`P7C13_REPAIR5_TURN4_UNEXPECTED_REQUEST_GATE=PASS|FAIL`

`P7C13_REPAIR5_TURN4_NO_SECOND_RESPONSE=PASS|FAIL`

`P7C13_REPAIR5_TASK_OWNERSHIP=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## E. File scope

Allowed tracked modifications only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`.

Optionally one P7.C13-only helper under `tests/real/` only if strictly required.

Forbidden:

- `src/**`;
- accepted P7.C12 matcher;
- historical P7.C6–P7.C12;
- migrations/schema;
- ADR;
- deployment/Telegram;
- CURRENT_WORK/ROADMAP.

Preserve unrelated untracked files.

## F. Validation

Run:

- focused P7.C13 including all Repair-5 tests;
- accepted P7.C12 focused suite;
- relevant P7.C2/C3/C4/C5 fake/non-real regression;
- complete non-real pytest with every real gate unset;
- ordinary unittest discovery with every real gate unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch absence tests remain immutable and may be reported separately; never delete or rewrite historical authorities to make them green.

## G. Publication

Use branch:

`prep-p7-c13-final-hard-delete-acceptance-repair5-2026-09-12`

No rebase. No force push. Do not mutate main.

Remote readback must prove:

- exact base `86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`;
- exact base tree `2968187b6300e1ed03e336340aa906c199819d48`;
- linear history;
- only allowed P7.C13 files changed;
- no `src/**`;
- accepted matcher unchanged;
- historical P7.C6–P7.C12 unchanged;
- remote final harness/evidence blobs;
- architect main unchanged by executor.

## Final state

Repair-5 publication does not itself authorize the real run.

Independent architect review remains required.

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
