# P7.C6 same-thread continuation preparation contract — 2026-09-10

Status: **FROZEN / ZERO-REAL-EFFECT / HARNESS PREPARATION ONLY**

This slice prepares a corrected gated same-thread recovery continuation for the rejected P7.C6 Run 1. It does **not** authorize any real Codex business effect.

## Exact predecessor authority

Accepted retained-Turn-3 forensic: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.

Run-1 evidence: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

Architect review: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_ARCHITECT_REVIEW_2026-09-10.md`.

The retained Run-1 target thread SHA-256 is:

`9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`.

The exact raw thread ID remains only in the root-owned retained recovery ledger and must never enter Git output.

## Absolute no-real-effect boundary

This preparation must perform zero:

- real Codex/app-server process starts;
- `model/list`;
- `thread/start`;
- `thread/resume`;
- `turn/start`;
- approval response;
- interrupt;
- `thread/delete`;
- `thread/read`;
- `thread/list`;
- Telegram call;
- unrelated process signal/termination.

All real-run authorization environment variables remain unset.

If any Codex business effect is needed to complete preparation, stop. Do not weaken the boundary.

## Historical Run-1 harness is immutable evidence

Do not modify `tests/real/test_p7_c6_real_hard_delete.py` merely to make Run 1 look correct. Its defects are retained evidence.

Create a new gated continuation harness, preferably:

`tests/real/test_p7_c6_same_thread_continuation.py`.

Ordinary discovery must never execute real continuation. The future real method must require a new exact authorization value distinct from Run 1, for example:

`CODEXCONTROL_P7C6_SAME_THREAD_CONTINUATION=AUTHORIZED_RETAINED_THREAD_T4_T5_DELETE_2026_09_10`.

Preparation must run with this value unset.

## Root-only Run-1 consumed latch

The rejected Run-1 harness declared:

`/root/.codexcontrol/p7c6-real-one-shot-ledger.json`

but did not materialize it.

Preparation must close that safety hole without any Codex RPC:

- require `/root/.codexcontrol` to be root-owned, non-symlink and mode `0700`, creating only that directory if absent and safe;
- create the Run-1 consumed latch using `O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode `0600`;
- if the path already exists, inspect metadata/content only enough to prove it is the expected safe CodexControl latch; do not overwrite an unknown file;
- the latch stores no raw thread ID, marker, prompt, command, token or credential;
- store only finite safe authority such as status `RUN1_CONSUMED_REJECTED_RECOVERY_ONLY`, Run-1 evidence commit and target thread SHA-256;
- fsync the file and parent directory;
- after preparation, the historical Run-1 harness must be unable to pass its one-shot precondition.

Required evidence:

`RUN1_GLOBAL_ONE_SHOT_LATCH=MATERIALIZED_SAFE|ALREADY_SAFE|FAIL`.

## Recover all Run-1 synthetic marker values offline

The rejected Run-1 failure path lost the generated marker plaintext from its recovery ledger. Final hard-delete proof therefore requires deterministic recovery from the exact retained target session artifact.

Use the exact raw target thread ID only in process memory to locate exactly one target session artifact under `/root/.codex_second/sessions/**` with zero scan errors.

Read only that exact target artifact. Do not read unrelated conversation content.

Recover exactly one unique runtime-generated value matching each family:

- `C6_RESPONSE_[0-9a-f]{48}`;
- `C6_MEMORY_[0-9a-f]{48}`;
- `C6_INTERRUPT_[0-9a-f]{48}`.

Occurrences may repeat; uniqueness is by full marker value.

Require exactly three unique marker values total: one in each family. If any family is missing or has more than one unique candidate, stop:

`P7C6_RUN1_MARKER_RECOVERY_AMBIGUOUS`.

Create a new root-owned `0600` recovery supplement beneath the retained Run-1 root, outside Git, using exclusive/no-follow creation. It may contain the three recovered marker plaintext values because they are synthetic run-owned material required for later erasure measurement. It must also contain their SHA-256 values and the target thread SHA-256.

Do not expose marker plaintext in stdout/log/Git evidence.

Required evidence:

- `RUN1_MARKER_RECOVERY=PASS|FAIL`;
- `RUN1_RESPONSE_MARKER_SHA256=`;
- `RUN1_MEMORY_MARKER_SHA256=`;
- `RUN1_INTERRUPT_MARKER_SHA256=`;
- `RUN1_MARKER_FAMILY_COUNT=3|FAIL`;
- `RUN1_MARKER_SUPPLEMENT_MODE=0600|FAIL`.

## Retained run-owned topology reconstruction

Derive the retained Run-1 root from the exact recovery-ledger location; do not guess a different run.

Require the expected retained boundaries to exist and be safe:

- Run-1 root;
- `state-parent/c6-isolated-state`;
- isolated ownership marker;
- `sqlite/`;
- `logs/`;
- `controller/controller.sqlite3`;
- retained recovery ledger.

The temporary Run-1 workdir may be absent because Run 1 cleaned it.

Prove no unrelated process uses or aliases the exact retained isolated root/controller boundary. Shared use of `/root/.codex_second` remains allowed under ADR-0045.

Do not reset or clean the retained isolated root during preparation.

Required:

- `RETAINED_ISOLATED_ROOT=SAFE|FAIL`;
- `RETAINED_CONTROLLER_DB=SAFE|FAIL`;
- `RETAINED_ISOLATED_ROOT_EXTERNAL_USERS=0|FAIL`;
- `RETAINED_CONTROLLER_DB_EXTERNAL_USERS=0|FAIL`.

## Correct structural approval matcher

The new continuation harness must not copy Run-1 `_ExactApprovalOperator`.

Implement the historical safe structural relation, using `shlex` or an equivalently strict token parser.

For the future approval-proof turn, ALLOW is possible only when **all** are true:

- request count is exactly one;
- request kind is exactly `COMMAND_EXECUTION`;
- exact retained thread ID matches;
- exact newly created continuation turn ID matches;
- exact continuation workdir matches normalized `cwd`;
- exact new approval marker is present in the normalized command;
- exact new approval sentinel path is present in the normalized command;
- normalized command grammar is either `EXACT_INNER` or `ONE_SHELL_WRAPPER`.

`EXACT_INNER` means the observed shell-token sequence exactly equals the expected inner command token sequence.

`ONE_SHELL_WRAPPER` means exactly three outer tokens:

1. one wrapper from `sh`, `/bin/sh`, `/usr/bin/sh`, `bash`, `/bin/bash`, `/usr/bin/bash`;
2. exactly `-c` or `-lc`;
3. one script string whose tokenization exactly equals the expected inner-command tokens.

No second wrapper, additional executable, extra prefix/suffix, pipeline, subshell, alternate target, alternate marker, extra command or additional control operation is accepted.

The prepared future approval inner command is:

`printf <NEW_ALLOW_MARKER> > <NEW_RUN_OWNED_SENTINEL>`

where marker and sentinel are generated only at future real continuation runtime and never hardcoded in Git.

The matcher must persist only safe finite diagnostics/hash metadata in future evidence.

## Matcher offline tests

Add no-real-effect tests proving at least:

- exact inner command ALLOW;
- each accepted wrapper path with `-c` and `-lc` around the exact inner command ALLOW;
- wrong thread DENY;
- wrong turn DENY;
- wrong cwd DENY;
- wrong marker DENY;
- wrong sentinel DENY;
- second request DENY;
- wrong approval kind DENY;
- extra prefix DENY;
- extra suffix DENY;
- second wrapper DENY;
- pipeline DENY;
- additional command DENY;
- token mutation DENY;
- unparsable command DENY.

No production P1.7 code is changed.

## Future continuation-specific one-shot latch

Implement a separate future continuation latch, e.g.:

`/root/.codexcontrol/p7c6-same-thread-continuation-ledger.json`.

Do not create/consume this continuation latch during preparation unless doing so is part of a purely temporary test path outside the authoritative location.

The future direct real continuation must create the authoritative latch atomically with `O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, mode `0600`, and fsync it **before the first real `thread/resume` RPC**.

The latch stores only safe identity hashes/commit/status, not raw thread/markers.

After the first continuation business RPC is dispatched, every failure leaves the latch present so the continuation cannot be blindly rerun. A pre-dispatch failure may still require architect review before another authorization; the harness does not delete the latch automatically.

Add offline tests for exclusive creation, pre-existing-file refusal, mode, no-follow behavior and persistence after simulated post-dispatch failure.

## Future same-thread real sequence — prepare only

The harness must encode but not execute during this slice:

### Recovery initialization

- exactly one retained recovery ledger and target thread hash;
- marker supplement must be present and exact;
- reuse `/root/.codex_second` as `SHARED_AUTHENTICATED` persistent home;
- reuse the exact retained Run-1 isolated root and controller path;
- no new thread creation path may exist in the continuation harness;
- validate exact `/usr/local/bin/codex`, `codex-cli 0.144.6` and schema hash before future business work;
- one future authenticated model catalog validation is allowed only by the later real authorization;
- construct retained `ThreadBinding` from local raw recovery identity;
- future real continuation may call exact `thread/resume` once.

### Future Turn 4 — approval proof

Create a fresh continuation workdir and a new sentinel outside that workdir but inside the retained run-owned root.

Generate new high-entropy approval marker and prompt marker and persist them only in the root-only recovery supplement before Turn 4 so crash recovery preserves the final oracle needles.

Arm the structural approval bridge before starting Turn 4, using a future for the exact new turn ID as in the historical accepted proof.

Turn 4 asks for exactly the bounded `printf marker > sentinel` inner command and requires operator approval rather than substitution.

The future continuation authorizes at most one **new distinct** approval response for this new Turn-4 request. This is not a retry of Run-1 Turn 3.

Required future success:

- request observed exactly once;
- exact thread/turn/cwd/marker/sentinel all match;
- grammar `EXACT_INNER|ONE_SHELL_WRAPPER`;
- operator ALLOW count exactly one;
- approval handling result exactly `ALLOWED`;
- Turn 4 terminal `COMPLETED`;
- sentinel contains exactly the new approval marker;
- remove only that run-owned sentinel after proof.

Any DENY, mismatch, timeout or `RESPONSE_UNKNOWN` stops the continuation. Never retry or answer the same request again.

### Future Turn 5 — interrupt proof

No approval response is authorized for Turn 5.

Turn 5 requests one harmless long-running command `sleep 120` in the continuation workdir and no file/network effect.

After `TURN_START_CONFIRMED`, prove the turn is still active without any new external effect: wait a short bounded interval on the already-owned terminal collector under `asyncio.shield`; a timeout means the turn remains active. If it has already terminated, stop without interrupt.

Then invoke accepted P1.8 `interrupt_turn` exactly once on the same exact `TurnBinding` object and same captured runtime. Require no runtime reacquire during interrupt.

Required future success:

- interrupt status `CONFIRMED|RECONCILED`;
- definitive terminal status `FAILED`;
- no continuation-owned delayed `sleep` process remains after owned runtime shutdown/reap;
- no Turn-5 approval response was sent.

If an approval request happens to be queued for Turn 5, do not answer it. The interrupt/terminal boundary must dispose the turn without a second approval response.

### Future pre-delete proof

After Turn 5, shutdown/reap continuation-owned runtime children only.

The final marker oracle must include:

- all three recovered Run-1 markers;
- Turn-4 approval marker;
- Turn-4 prompt marker;
- Turn-5 interrupt prompt marker;
- any additional explicitly declared continuation marker that can enter dialogue-bearing storage.

Before any delete, require zero scan errors and at least one target thread/known-marker occurrence in dialogue-bearing storage. Otherwise stop as inconclusive and do not delete.

### Future delete

Use the retained controller DB as the exact protected `controller_db_path`. Open/validate schema v4 and require no conflicting live dialogue state from Run 1 before binding the retained thread.

Persist one canonical synthetic IDLE dialogue bound to the retained exact thread/profile and call accepted `DialogueDeleteService.delete()` once.

Cumulative Run-1 + continuation delete budget remains:

`REAL_THREAD_DELETE_CALLS_MAX=1`.

Run 1 used zero, so one remains.

No raw direct `thread/delete` call outside `DialogueDeleteService` is allowed.

`DELETE_UNKNOWN` is terminal; no retry/read/list/manual persistent cleanup.

Confirmed but local-pending remains `DELETE_CONFIRMED_PENDING_STORAGE`; no second external delete.

### Future final oracle

P7.C6 can pass only if the future continuation establishes:

- official P1.9 `DELETE_CONFIRMED`;
- application `DELETED` with exact tombstone and no live binding;
- production exact-thread persistent scanner: zero target matches/errors;
- independent marker oracle: zero target residual for every recovered Run-1 marker and every continuation marker;
- retained isolated `sqlite/` descendants zero;
- retained isolated `logs/` descendants zero;
- isolated ownership envelope valid;
- zero unrelated process termination;
- zero manual persistent-home cleanup;
- all continuation-owned runtime/process/sentinel/workdir cleanup complete.

On PASS, sanitize the retained recovery ledger and marker supplement to hashes/status only; preserve host-level one-shot/continuation completion latches.

## Extended future real budget

Preparation does not consume this budget.

If later separately authorized, the same-thread continuation maximum is:

- new real threads: `0`;
- additional `model/list`: `1`;
- additional `thread/resume`: `1`;
- additional turns: `2`;
- additional approval responses: `1`, only the new Turn-4 request;
- additional interrupt calls: `1`, only Turn 5;
- cumulative official `thread/delete`: `1` total across Run 1 + continuation;
- `thread/read`: `0`;
- `thread/list`: `0`;
- Telegram: `0`.

Run-1 Turn-3 `RESPONSE_UNKNOWN` is historical and never retried.

## Repository scope

Normal preparation changes may include only:

- `tests/real/test_p7_c6_same_thread_continuation.py`;
- optional no-real-effect helper tests under `tests/**`;
- sanitized preparation evidence under `docs/evidence/p7c6/**`.

No `src/**`, configuration, ADR, deployment, Telegram, `CURRENT_WORK`, `ROADMAP` or `DECISIONS` change is authorized for the executor.

If preparation reveals a production defect, stop and report it; do not patch production source.

## Preparation evidence

Create:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_EVIDENCE_2026-09-10.md`.

Record at minimum:

- architect base SHA/tree;
- Run-1/forensic identities;
- zero real-effect counters;
- Run-1 global latch result;
- marker recovery counts/hashes only;
- marker supplement safe metadata only;
- retained topology validation;
- structural matcher test matrix;
- continuation latch test matrix;
- static proof that new thread creation is absent from continuation harness;
- gate-disabled real method skip;
- focused/full ordinary regression if run;
- changed-file scope;
- remote readback.

Never put raw thread ID, marker plaintext, command runtime value, session line, credential/token or recovery file content in Git.

## Acceptance consequence

Successful preparation does **not** itself authorize real continuation.

Final preparation report must state:

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

Only independent architect review of the preparation commit may issue the later one-shot same-thread real authorization.

P8/P9 remain blocked.
