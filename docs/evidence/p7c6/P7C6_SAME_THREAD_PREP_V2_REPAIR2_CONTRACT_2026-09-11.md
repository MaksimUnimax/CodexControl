# P7.C6 same-thread prep-v2 Repair-2 contract — 2026-09-11

Status: **FROZEN / ZERO-REAL-EFFECT / HARNESS-ONLY REWORK**

Reviewed candidate: `821be881f1e6b04d3905080191cc0f1141799923`.

Binding architect review: `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR_ARCHITECT_REVIEW_2026-09-11.md`.

This slice repairs only the gated acceptance harness. It does not authorize any real Codex effect and does not establish a production defect.

## Absolute zero-real-effect boundary

The entire Repair-2 must perform zero real Codex/app-server starts, `model/list`, `thread/start`, `thread/resume`, `turn/start`, approval response, interrupt, `thread/delete`, `thread/read`, `thread/list`, Telegram call, or process signal. All real authorization variables remain unset.

## Repository boundary

Normal changes are limited to:

- `tests/real/test_p7_c6_same_thread_continuation.py`;
- optional offline-only tests under `tests/**`;
- sanitized `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_EVIDENCE_2026-09-11.md`.

Do not modify production `src/**`, the rejected Run-1 harness, ADRs, deployment/configuration, CURRENT_WORK, ROADMAP or DECISIONS. If production code appears necessary, stop `P7C6_CONTINUATION_PREP_PRODUCTION_DEFECT_STOP`.

## 1. Correct the retained topology matrix

The future real preflight must admit only the exact legitimate run-owned containment relationships while still rejecting aliasing.

At minimum the real retained topology has:

- `run_root` contains `isolated_root`;
- `run_root` contains `sqlite`;
- `run_root` contains `logs`;
- `run_root` contains `controller_db`;
- `run_root` contains Run-1 ledger and marker supplement;
- `run_root` contains continuation recovery/result files and future workdir/sentinel paths;
- `isolated_root` contains `sqlite` and `logs`.

These exact relationships are allowed; unrelated overlapping paths, same-inode aliases and symlink substitutions remain forbidden.

Add an offline test that constructs the complete real-shaped synthetic topology and proves it passes. Then mutate each important relationship/identity to prove fail-closed behavior.

## 2. Scope external-user blocking correctly

Shared use of `/root/.codex_second` remains allowed. Ordinary repository use by another process is not itself a C6 blocker.

External-user rejection must be scoped to the exact continuation-owned mutable/recovery boundaries that would create correctness ambiguity, especially:

- retained isolated root/sqlite/logs;
- controller DB;
- Run-1 recovery/marker authority;
- continuation latch/journal/supplement/workdir/sentinel boundary.

Do not introduce a host-wide repository lock.

## 3. Preflight every local continuation path before first RPC

Before creating the continuation latch and before runtime acquire, derive all deterministic/local candidate paths needed by the run.

The continuation marker supplement, result/recovery journal, workdir and sentinel identity must be proven absent/safe before first business effect. Avoid a fixed reusable sentinel name; use a high-entropy run-owned sentinel path and retain only root-local recovery authority for its exact path.

After the durable continuation latch is created, materialize required local records/workdir before `model/list` or `thread/resume` so purely local collisions cannot consume a real RPC budget.

Use exclusive/no-follow creation where applicable.

## 4. Make recovery progress fail-closed

Replace the fail-open `progress()` behavior.

A required journal update failure must prevent the next material effect. Do not silently swallow it and continue.

Persist dispatch intent before each material business effect, including at least:

- model-list dispatch;
- resume dispatch;
- Turn-4 start dispatch;
- approval response dispatch/handling authority where observable;
- Turn-5 start dispatch;
- interrupt dispatch;
- official delete dispatch.

Persist finite result/status immediately after each effect resolves.

An exception/failure handler may make a best-effort final diagnostic update after execution has already stopped, but that best-effort path must never authorize subsequent business effects.

Add behavior tests where journal update failure proves the next stubbed effect is not called.

## 5. Own every timeout-sensitive async task

No shielded task may be abandoned after timeout.

For manager/runtime acquisition, model-list, resume, Turn-4 start, approval bridge task, Turn-4 terminal wait, Turn-5 start/terminal wait, interrupt and delete orchestration:

- retain the actual task object when a task exists;
- use finite primary waits;
- on timeout record durable uncertainty first;
- do not retry the same operation;
- for an owned Codex operation, shut down/reap the owned runtime as needed to force protocol-terminal convergence;
- boundedly await task convergence after shutdown;
- never permit a late approval ALLOW or late unobserved turn/delete effect after the harness has declared timeout.

For `DialogueDeleteService.delete()`, once started, the exact task remains owned until it reaches a finite result after any forced runtime shutdown. The task is never redispatched. If it cannot converge within the bounded recovery window, retain all recovery authority and fail without claiming C6 acceptance.

Add offline/fake tests for timeout ownership and no second dispatch.

## 6. Harden descriptor scanning against pathname replacement

After reading a candidate file through `O_NOFOLLOW`, re-`lstat` the pathname and require the pathname still names the same `(st_dev, st_ino)` as the opened descriptor.

Also fail closed if relevant file metadata demonstrates mutation during the bounded read. The scanner must not accept a stable old fd after the pathname was replaced.

Keep regular-file/owner/mode/nlink checks, chunk-boundary handling and all file/aggregate limits.

Add a real pathname-replacement offline test, not only an `fstat` mock.

## 7. Make unrelated-baseline scanning truly bounded

`capture_unrelated_baseline()` must enforce:

- max file count;
- max per-file bytes;
- max aggregate bytes actually read;
- chunked/no-follow descriptor reads;
- scan error and limit-exceeded outputs.

The `max_bytes` argument must be real authority, not unused.

Add aggregate-byte exhaustion tests.

## 8. Reconcile exact path identity

The unrelated baseline identity is the tuple of at least:

- exact relative path/category;
- `st_dev`;
- `st_ino`.

After delete, each exact pre-delete unrelated identity must still exist at the same relative path with the same device/inode identity.

New unrelated artifacts are allowed. Size and mtime changes are allowed. Renaming/removing/replacing a pre-delete unrelated artifact is not a PASS.

Add tests for:

- unchanged identity PASS;
- size mutation PASS;
- new unrelated file PASS;
- rename FAIL;
- delete FAIL;
- replacement at same path with different inode FAIL.

## 9. Reject unknown business RPCs in dynamic budget

The final PASS budget must reject any counted request method outside the explicit allowed method set.

The allowed future business methods are only those required for the accepted continuation: `model/list`, `thread/resume`, `turn/start`, `turn/interrupt`, and `thread/delete` with the exact counts frozen by the architect. `thread/start`, `thread/read`, `thread/list` remain exactly zero.

An unexpected method with otherwise-correct expected counters must fail the budget.

Add an explicit unknown-method test.

## 10. Preserve controller path authority

In addition to actual `PRAGMA user_version == 4`, live-dialogue/tombstone/idempotency checks, require the opened `SqliteStorage` to report `matches_database_path(controller_db) == True` before synthetic dialogue creation.

No alternate controller path is accepted.

## 11. Preserve official delete semantics

Keep the observing wrapper around the exact real `CodexThreadLifecycleAdapter`.

Add an explicit offline case where the underlying lifecycle returns real `ThreadOperationStatus.DELETE_UNKNOWN`; prove one call is recorded, UNKNOWN is preserved and no retry occurs.

Malformed result remains non-confirmed.

## 12. Strengthen behavioral recovery tests

Replace source-string-only safety assertions with behavior where practical.

At minimum prove:

- journal persistence failure prevents next material effect;
- approval timeout/cancellation cannot later emit ALLOW;
- ambiguous approval/Turn-4/Turn-5/delete states preserve forensic workdir/sentinel/recovery authority;
- definitive successful Turn-4 may remove only its verified sentinel;
- delete uncertainty never creates a second delete call;
- success sanitization occurs only after budget/post-delete/baseline gates;
- sanitization failure after confirmed delete never invokes external delete again.

## 13. Keep already-correct gates unchanged

Do not weaken:

- source HEAD/tree/clean-worktree authority;
- accepted Run-1 latch SHA check;
- retained thread hash;
- 13 structural ALLOW cases and strict DENY grammar;
- no-new-thread static and dynamic gates;
- actual schema-v4/live/tombstone checks;
- no-reacquire interrupt gate;
- all-marker post-delete proof;
- success-only raw recovery sanitization;
- real method disabled during ordinary testing.

## 14. Test execution

With every real authorization variable unset:

1. explicitly execute the continuation test file and require all offline tests PASS plus exactly one gated real skip;
2. run focused C2–C5 regressions;
3. compile/import and `git diff --check`;
4. run one ordinary full `unittest discover -s tests -v`.

Report explicit-real-file counts separately because `tests/real` is not relied upon to be part of ordinary recursive discovery.

All real-effect counters remain zero.

## 15. Evidence

Create `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_EVIDENCE_2026-09-11.md` with finite results for every Repair-2 gate, test counts and zero-real-effect accounting. Never commit raw thread IDs, marker plaintext, prompts, responses, runtime commands, credentials, tokens or root-only recovery records.

## 16. Result authority

For every Repair-2 outcome:

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

Only independent architect review of the Repair-2 commit may grant a separate one-shot real continuation authority.

P8/P9 remain blocked.
