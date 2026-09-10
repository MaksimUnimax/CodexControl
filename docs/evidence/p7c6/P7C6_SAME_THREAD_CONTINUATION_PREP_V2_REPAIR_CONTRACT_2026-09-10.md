# P7.C6 same-thread continuation prep v2 repair contract — 2026-09-10

Status: **FROZEN / ZERO-REAL-EFFECT / REPAIR ONLY**

Binding predecessor review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_ARCHITECT_REVIEW_2026-09-10.md`

Candidate under repair:

`1c9b03108bb2493fd6547a92c807397bb4c0868c`

This repair may modify only the gated continuation harness, offline tests, and sanitized P7.C6 preparation evidence. No production `src/**` change is authorized. No real Codex/app-server/business effect is authorized.

## Required repaired source gate

The future real method must require three architect-supplied environment authorities in addition to its distinct real authorization token:

- exact accepted continuation harness `HEAD` SHA;
- exact accepted `HEAD^{tree}` SHA;
- a root-only result path/identity if needed by the implementation.

Before creating the continuation latch, starting app-server, model/list, resume, or any other business effect, prove:

- repository canonical path is expected;
- current `HEAD` equals architect-supplied SHA;
- current tree equals architect-supplied tree;
- worktree/index are clean;
- accepted Run-1 latch SHA is unchanged;
- retained recovery thread SHA is unchanged.

The continuation latch must store the architect-supplied accepted harness SHA/tree, not the pre-preparation base.

## Required fresh protected-boundary preflight

Before real runtime acquire, perform read-only path/mount/process proof for the retained isolated root/sqlite/logs, controller DB, repository, recovery ledgers/supplements, and new continuation-owned paths. Shared use of `/root/.codex_second` is allowed. Exact protected-boundary alias/use uncertainty fails closed. No mount/namespace mutation and no unrelated-process signal is allowed.

## Required controller proof

After `SqliteStorage.open(controller_db)` and before creating the synthetic dialogue:

- query actual `PRAGMA user_version` through `storage.read(...)` and require `4`;
- require `DialogueRepository(storage).get_live() is None`;
- require no conflicting tombstone for the chosen synthetic dialogue ID;
- keep the exact controller path bound into `IsolationPathAuthority` and `DeleteStorageCleanupCoordinator`.

## Required unrelated baseline

Immediately before delete, derive a bounded content-free identity set for pre-existing unrelated persistent `sessions/**` and optional `history.jsonl`, excluding exact target-thread artifacts. The identity may include relative path plus device/inode and must not include unrelated content.

After confirmed cleanup, every pre-delete unrelated identity must still be present. Additions/size changes from concurrent shared-home activity are allowed; disappearance of a baseline identity blocks C6 PASS.

## Required marker oracle safety

The acceptance-only all-marker oracle must be bounded and descriptor-safe:

- regular files only;
- no symlink following;
- owner/mode/link checks appropriate to the accepted persistent/isolated family;
- descriptor `O_NOFOLLOW|O_CLOEXEC` where available;
- inode stability before/after read;
- bounded file count and aggregate/per-file bytes;
- chunked reads with overlap carry for boundary-spanning needles;
- explicit scan error / limit-exceeded fields.

Search exact retained thread ID and all known Run-1 + continuation markers. Do not modify the production exact-thread scanner.

## Required dynamic budget gate

Count and final-gate all relevant effects for the continuation:

- new thread/start = `0`;
- model/list `<=1`;
- thread/resume exactly `1` if the real continuation reaches business effects;
- turn/start exactly `2` for a full PASS;
- approval responses exactly `1`, only Turn 4;
- turn/interrupt exactly `1`, only Turn 5;
- thread/delete exactly `1` cumulative for this retained thread because Run 1 used `0`;
- thread/read `0`;
- thread/list `0`;
- Telegram `0`.

Unexpected extra calls block PASS.

## Required interrupt no-reacquire proof

Count manager acquisitions. Snapshot immediately before `interrupt_turn(exact_original_turn5_binding)` and require the count is unchanged when interrupt returns. Require the exact original `TurnBinding` object, status `CONFIRMED|RECONCILED`, definitive terminal `FAILED`, and no Turn-5 approval response.

## Required official delete authority capture

Place a narrow counting/observing lifecycle wrapper around the exact `CodexThreadLifecycleAdapter` supplied to `DialogueDeleteService`. It must call the underlying `delete` once, preserve identity/semantics, and record the actual `ThreadOperationResult.status` without raw identifiers in Git evidence.

PASS requires actual `ThreadOperationStatus.DELETE_CONFIRMED`, application `DialogueDeleteStatus.DELETED`, tombstone present, and no live dialogue binding.

## Required post-delete local proof

After application delete and manager shutdown:

- production exact-thread persistent scan zero matches/errors/limits;
- all-marker oracle zero retained thread/marker matches/errors/limits;
- `IsolatedStateRoot.validate(profile)` passes;
- bounded sqlite/log payload descendant counts are zero with zero traversal errors;
- unrelated baseline preservation passes;
- protected-boundary external users remain zero.

## Required durable continuation recovery diagnostics

Before the first `thread/resume`, after the continuation latch is durably created, create a root-only mode-0600 continuation result/recovery record under the retained run-owned root using no-follow/exclusive creation. It must not enter Git.

Persist finite safe stage/counters/status after each material effect, including:

- source SHA/tree;
- retained thread SHA only plus raw thread identity only where strictly required by root-only recovery;
- resume status;
- Turn-4 start ID/status (raw only root-only if needed; SHA in Git);
- approval request count/kind/thread-turn-cwd-marker-sentinel relation booleans, grammar class, mismatch flags, operator decision, handling result, response count;
- Turn-4 terminal/sentinel proof;
- Turn-5 start/active proof/interrupt status/terminal status/no-reacquire proof;
- pre-delete scan/oracle counts;
- actual official delete status and application status;
- post-delete counts;
- failure stage.

Every update must be atomic or otherwise crash-safe and retain the one-shot no-retry authority.

On `RESPONSE_UNKNOWN`, turn/interrupt uncertainty, or any non-definitive command state, do not erase the run-owned sentinel/workdir merely for cosmetic cleanup. Stop/reap only the owned app-server runtime, preserve bounded forensic authority, and do not retry.

## Required success sanitization

Only after every PASS gate succeeds, atomically sanitize:

- original retained recovery ledger;
- Run-1 marker-recovery supplement;
- continuation marker/result supplement(s);

to content-free completion records containing hashes/status/source authority only. Remove raw target thread identity and marker plaintext from those recovery artifacts. Keep the Run-1 consumed latch and continuation consumed latch.

If sanitization fails after official delete, record confirmed external authority and local sanitization failure; never redispatch delete. C6 remains unaccepted until a separately authorized local-only recovery completes.

## Required finite waits

Before Turn 4, prove the approval bridge task is armed and not already terminal. Use finite bounded waits for approval handling and Turn-4 terminal. Use a bounded active proof before Turn-5 interrupt and finite bounded interrupt/terminal waits. Timeout becomes finite retained recovery state; it never triggers a retry.

## Required static/offline tests

Add/repair tests proving:

- exact source/head/tree/clean gate pass/fail;
- continuation latch stores accepted source SHA/tree;
- no new thread path;
- structural matcher 13 safe ALLOW cases and expanded DENY matrix;
- bounded marker oracle chunk-boundary match plus symlink/hardlink/inode-substitution/size/file-count/read-failure cases;
- actual controller schema check and preexisting-live-dialogue/tombstone refusal with synthetic DBs only;
- unrelated baseline subset preservation and removal failure;
- dynamic budget exact/over-budget failures;
- no-reacquire interrupt accounting;
- actual delete result capture wrapper semantics with fakes;
- recovery/result record retention across simulated failures;
- success-only sanitization and sanitization-failure no-delete-retry semantics;
- gate-disabled real method skips before any real runtime effect.

Run the continuation test file explicitly with real authorization unset. Run focused C2-C5 regressions and one ordinary full suite with all real gates unset. Do not infer real-test coverage from ordinary discovery alone.

## Allowed repository scope

Allowed:

- `tests/real/test_p7_c6_same_thread_continuation.py`;
- optional offline-only tests under `tests/**`;
- `docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_REPAIR_EVIDENCE_2026-09-10.md`.

Forbidden:

- `src/**`;
- deployment/config;
- ADR changes;
- Run-1 harness changes;
- real Codex effects;
- P8/P9.

## Acceptance consequence

For this repair itself:

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

Only independent architect review of the repaired commit may freeze a later one-shot real continuation authority.