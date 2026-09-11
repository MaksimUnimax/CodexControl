# P7.C6 real same-thread continuation execution contract — 2026-09-11

Status: **FROZEN / ONE-SHOT REAL EXECUTION AUTHORIZED**

This contract authorizes exactly one real continuation attempt against the retained P7.C6 Run-1 thread.

## Executable source authority

The real attempt MUST execute the exact architect-accepted Repair-6 snapshot:

- commit: `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`
- tree: `92abebdfb3390d4c58f4aefc00aa84b83841e99e`
- harness: `tests/real/test_p7_c6_same_thread_continuation.py`

The repository worktree must be clean and `git rev-parse HEAD` / `HEAD^{tree}` must match those exact authorities before the real authorization environment is set.

## Retained authority

- profile: `server-80-codexcontrol`
- persistent authenticated home: `/root/.codex_second`
- retained thread SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`
- accepted Run-1 replay latch: `/root/.codexcontrol/p7c6-real-one-shot-ledger.json`
- accepted Run-1 latch SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`
- retained recovery root is discovered by the accepted harness and must resolve uniquely.

No new real thread is authorized.

## Authorization environment

Exactly for the single real unittest command, set:

`CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION=AUTHORIZED_RETAINED_THREAD_T4_T5_DELETE_2026_09_10`

`CODEXCONTROL_P7C6_CONTINUATION_EXPECTED_HEAD=76a7aa24e3cfdfb12c3314a7e01691d4a943b551`

`CODEXCONTROL_P7C6_CONTINUATION_EXPECTED_TREE=92abebdfb3390d4c58f4aefc00aa84b83841e99e`

Unset them immediately after the command returns.

## Mandatory pre-dispatch stop gates

Before the real command, require:

- exact accepted HEAD/tree and clean worktree;
- accepted Run-1 latch present and unchanged;
- `/root/.codexcontrol/p7c6-same-thread-continuation-ledger.json` ABSENT;
- `/root/.codexcontrol/p7c6-same-thread-continuation-process-result.json` ABSENT;
- retained recovery root and marker supplement present;
- no existing external user of the retained isolated/controller boundary;
- no real authorization variable already set from a prior shell/session.

Any failed pre-dispatch gate means **NO REAL COMMAND**.

## One-shot effect budget

The accepted harness is the sole real executor. Maximum/required successful budget:

- new thread: `0`
- `model/list`: `1`
- retained `thread/resume`: `1`
- `turn/start`: `2`
- approval responses: `1`, Turn 4 only
- `turn/interrupt`: `1`, exact Turn-5 binding only
- official `thread/delete`: `1`
- `thread/read`: `0`
- `thread/list`: `0`
- Telegram: `0`

No second real invocation is allowed after the first command starts, regardless of PASS, FAIL, timeout, signal termination or ambiguous status.

## Required continuation behavior

The accepted harness performs:

1. one retained-thread resume;
2. Turn 4 exact command approval proof with strict structural matcher and exact sentinel bytes;
3. Turn 5 `sleep 120` interrupt proof using the exact original binding and no runtime reacquire;
4. pre-delete retained-thread/all-marker physical proof;
5. one canonical `DialogueDeleteService.delete()` call, with the official P1.9 lifecycle result observed exactly once;
6. post-delete persistent/isolated/baseline/controller/budget gates;
7. success-only sanitization;
8. durable safe process-result creation only on complete PASS.

The real continuation runs inside the accepted dedicated OS session/process-group watchdog. Parent PASS requires the continuation process group to be quiescent and the exact safe process-result authority to pass validation.

## Failure authority

Any failure, timeout or ambiguity is terminal for this one-shot execution.

Never:

- retry the continuation;
- start another child;
- resume again;
- answer another approval request;
- interrupt again;
- dispatch another delete;
- use `thread/read` or `thread/list` to infer outcome;
- manually clean persistent Codex session/history artifacts;
- delete/rewrite the continuation latch, recovery journal or forensic artifacts to manufacture PASS.

If official delete is `DELETE_UNKNOWN`, preserve UNKNOWN exactly.

If official delete is confirmed but a later local gate fails, never redispatch delete.

## Evidence publication

After the one real command returns, authorization variables must be unset. Collect only sanitized finite evidence. Never commit raw thread IDs, marker plaintext, prompts, commands, credentials, environment dumps or root-only recovery contents.

Publish an evidence-only branch based on the then-current `origin/main`, containing only:

`docs/evidence/p7c6/P7C6_REAL_SAME_THREAD_CONTINUATION_EVIDENCE_2026-09-11.md`

The evidence must record source SHA/tree, command exit classification, process-group status, safe process-result fields if PASS, effect counters, and finite hashed/classified recovery state if FAIL. Do not change `src/**`, the harness, ADRs, CURRENT_WORK or ROADMAP in that executor branch.

Architect review is required before P7.C6 can be marked DONE or P8 can begin.
