# P7.C13 preparation Repair-6 evidence — 2026-09-12

Status: **REPAIR-6 PREPARATION READY / ZERO REAL EFFECT / NO REAL EXECUTION**

## Authority, lineage and scope

`REPAIR5_BASE_HEAD=86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`

`REPAIR5_BASE_TREE=2968187b6300e1ed03e336340aa906c199819d48`

`REPAIR5_PRIOR_HARNESS_BLOB=61853860ed0955df6119edb288d22573299cd1b3`

`REPAIR6_BASE_HEAD=c09b5b3dfb197a647bd2f732ed343d42bf4aec0e`

`REPAIR6_BASE_TREE=4ecd65c7a251b5931b579b3b324724731fda785b`

`PRIOR_HARNESS_BLOB=cb64f44bc71339300e2d697167daa08b0b601f15`

`P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

`ARCHITECT_MAIN_HEAD=2b9970212c75d873ab4dcb25ac1251dbb5e3a98a`

`ARCHITECT_MAIN_TREE=bd7e027d014401e45c4149fdf1f3db3f020100b3`

`REPAIR6_ARCHITECT_MAIN_HEAD=13617b8e5364cd66b32d488b2c9767e106aa70d2`

`REPAIR6_ARCHITECT_MAIN_TREE=5d5fbc6a583b4fcb87de026737189e18ae96e0b3`

`FINAL_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c`

`FINAL_EVIDENCE_BLOB=DERIVED_BY_FINAL_REMOTE_READBACK`

`HELPER_BLOB=NONE — no optional helper; Repair-6 changes are in the harness file`

The Repair-6 branch starts at the exact accepted Repair-5 commit and remains
linear. No merge, rebase, squash or history rewrite was used. Tracked
modifications are limited to this evidence file and the P7.C13 harness. The pre-existing
untracked `tests/real/__init__.py` was preserved. No `src/**`, accepted matcher,
historical P7.C6–P7.C12 file, schema/migration, ADR, deployment, Telegram,
CURRENT_WORK or ROADMAP file changed.

## Repair-5 external-user classification

The production read-only preflight continues to perform all existing
normalization, `/proc/self/mountinfo`, root-ownership, symlink, physical inode
alias and topology-overlap checks. Only the process-user role classification was
corrected.

| Boundary role | Boundaries | External users |
|---|---|---|
| report-only/shared or source | `persistent_home`, `repository`, `controller_root` | allowed and reported |
| exact destructive run-owned | `isolated_root`, `isolated_sqlite`, `isolated_logs`, `controller_db`, `workdir`, `approval_target`, `ledger`, `boot`, `result` | fail closed when count is nonzero |

Offline matrix: `persistent_home=4`, `repository=2` and `controller_root=2`
were each allowed and reported. Each of the nine destructive boundaries was
tested independently with one external user and failed closed. Repository and
controller-root mount ambiguity failed. Physical aliases across shared and
destructive classes failed. A simulated live parent/executor using the
repository checkout as cwd was reported and did not block the child; exact
run-owned `workdir`, `controller_db` and `ledger` users blocked.

## Repair-5 Turn-4 unexpected-request gate

After actual Turn-4 `START_CONFIRMED`, the production path owns exactly two
bounded current-run tasks: the exact `wait_turn(binding)` terminal waiter and a
request observer awaiting `client.next_server_request()`. The observer only
records that a request was dequeued; it never calls a response method and never
uses `CodexApprovalBridge`.

| Synthetic fact timing | Result | Interrupt |
|---|---|---:|
| no request during active window; active/nonterminal proof; failed terminal after interrupt | PASS | 1 |
| terminal before active window | NON-PASS | 0 |
| request before active timeout | NON-PASS; `unexpected_request_count=1` | at most one cleanup interrupt |
| request during interrupt | NON-PASS; no response | 1 cleanup interrupt |
| request before final terminal convergence | NON-PASS; no response | 1 cleanup interrupt |
| request and terminal in same scheduler slice | NON-PASS / fail closed | 0 |

The observer remains owned through interrupt and terminal convergence. The final
snapshot requires zero unexpected requests for PASS, a definitive failed
terminal, and both waiters terminalized or cancellation-joined. All synthetic
observer tests ended with no pending request task and no detached terminal task.

Turn-3 accounting remained exactly `approval_responses=1`,
`allow_responses=1`, `deny_responses=0` when Turn-4 produced an unexpected
request. The response callback count was zero. The source-order proof places
the non-PASS Turn-4 gate before controller DB open and before
`DialogueDeleteService.delete()`; the controller/delete callbacks are
therefore unreachable after an unexpected request. The one exact interrupt is
available only for cleanup of the exact actual Turn-4 binding.

## Repair-6 post-join request classification

The sole Repair-6 production change is the final Turn-4 request-observer
close/join snapshot. The old preliminary `request_task.done()` value is now
diagnostic only. The terminal waiter is joined first; the request observer is
then given its owned final scheduler turn, cancelled and joined only if still
pending, and classified from its terminal state after that join.

| Final observer class | Terminal fact | Unexpected requests | Gate result |
|---|---|---:|---|
| `REQUEST_OBSERVED` | task completed normally with one request | 1 | NON-PASS |
| `CANCELLED_BY_HARNESS_WITHOUT_REQUEST` | harness cancellation completed without delivery | 0 | PASS remains possible |
| `OBSERVER_ERROR` | exception, non-harness cancellation or ambiguous state | 0 | NON-PASS |

The deterministic late-window test controls scheduling through the fake
lifecycle: its preliminary request-task snapshot is `done=False`; terminal
waiter cancellation then synchronously delivers one fake request while the
terminal waiter is being joined; the post-join observer task completes
normally and is classified `REQUEST_OBSERVED`. It proves
`unexpected_request_count=1`, `passed=False`, protocol response calls `0`,
Turn-3 accounting `approval_responses=1`, `allow_responses=1`,
`deny_responses=0`, controller callback count `0`, delete callback count `0`,
and both owned tasks `done=True`.

The no-request active/interrupt path is classified
`CANCELLED_BY_HARNESS_WITHOUT_REQUEST`, remains PASS-capable, and is not an
observer fault. The synthetic observer exception is classified
`OBSERVER_ERROR` and is NON-PASS. Requests before active timeout, during
interrupt, before terminal convergence, in the same scheduler slice, and
after the preliminary snapshot are all NON-PASS with no second response.
The production Turn-4 gate remains before controller DB binding and before
`DialogueDeleteService.delete()`; a late request therefore cannot reach either
callback. No Turn-4 response capability was added.

## Preserved Repair-4 authorities

The accepted C11 root-only wire authority, C12 matcher and independent
request/Turn/cwd/local-sequence/target correlation remain unchanged. Turn-3
explicit escalation and its single response, official delete observation,
schema-v4 controller proof, post-delete oracle, UNKNOWN and CONFIRMED_PENDING
mapping, runtime/parent quiescence, watchdog bounds, source/index gate and
fresh topology remain present and covered by the focused regression suites.

## Validation

- Focused P7.C13 Repair-6: `75 passed`, `36 subtests`.
- Accepted P7.C12 plus relevant P7.C2/C3/C4/C5 fake/non-real regressions:
  `119 passed`, `133 subtests`.
- Complete non-real pytest with real authorization gates unset:
  `1851 passed`, `7 skipped`, `6 failures`; the six failures are the preserved
  historical P7.C7–P7.C11 consumed-latch/absence authorities, including the
  existing P7.C11 preflight error. No historical latch was deleted or changed.
- Ordinary unittest discovery with real authorization gates unset:
  `1864 run`, `5 failures`, `1 error`, `7 skipped`; these are the same six
  preserved historical consumed-latch/absence authorities.
- `python -m compileall -q src tests`: PASS before final evidence edit.
- `git diff --check`: PASS before final evidence edit.
- Leakage/security scan: PASS; no future authorization token, credential,
  private key, raw retained real identifiers, raw wire payload, Telegram call
  or real-process signal was added.
- Exact changed-path scope and accepted matcher/historical immutability:
  PASS before final evidence edit.

## Zero-real-effect accounting

All Repair-6 testing used synthetic state or injected fakes. No future gate
token was set or invented, and `--p7c13-real-run` was not executed.

`REAL_CODEX_PROCESS_STARTS=0`

`APP_SERVER_STARTS=0`

`REAL_MODEL_LIST_CALLS=0`

`REAL_THREAD_START_CALLS=0`

`REAL_THREAD_RESUME_CALLS=0`

`REAL_THREAD_READ_CALLS=0`

`REAL_THREAD_LIST_CALLS=0`

`REAL_THREAD_DELETE_CALLS=0`

`REAL_TURN_START_CALLS=0`

`REAL_TURN_INTERRUPT_CALLS=0`

`REAL_APPROVAL_RESPONSES=0`

`REAL_ALLOW_RESPONSES=0`

`REAL_DENY_RESPONSES=0`

`REAL_PERSISTENT_HOME_MUTATIONS=0`

`REAL_ISOLATED_ROOT_MUTATIONS=0`

`REAL_CONTROLLER_DB_MUTATIONS=0`

`REAL_APPROVAL_TARGET_MUTATIONS=0`

`REAL_P7C13_LEDGER_CREATIONS=0`

`REAL_P7C13_BOOT_CREATIONS=0`

`REAL_P7C13_RESULT_CREATIONS=0`

`TELEGRAM_CALLS=0`

`REAL_CODEX_PROCESS_SIGNALS=0`

`HISTORICAL_AUTHORITY_MUTATIONS=0`

P7C13_REPAIR6_POST_JOIN_REQUEST_SNAPSHOT=PASS
P7C13_REPAIR6_HARNESS_CANCELLATION_CLASS=PASS
P7C13_REPAIR6_NO_SECOND_RESPONSE=PASS
P7C13_REPAIR6_DELETE_UNREACHABLE_ON_LATE_REQUEST=PASS
P7C13_REPAIR6_TASK_OWNERSHIP=PASS
P7C13_PREP_HARNESS_READY=YES
P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
