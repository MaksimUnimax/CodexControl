# P7.C15 hard-delete successor preparation Repair-4 contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / ONE-SHOT CONTAINMENT + EVIDENCE INTEGRITY MICRO-REPAIR / NO REAL EXECUTION**

## Exact base

Repair-4 starts exactly from:

- HEAD `84b901f7af208ecde240b0ba0ed13188376b4104`;
- tree `31c2c22b5d11dafdcd06b8fb96e5dd0e880fc1ce`;
- P7.C15 launcher blob `5e964d9408413b968b03e334759037f906174ffd`;
- P7.C15 evidence blob `2cc14317db626d58d62189cc2669c9a7c78cb07d`.

Binding review:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_REPAIR3_ARCHITECT_REVIEW_2026-09-13.md`

Repair-4 is NOT a redesign. All Repair-1/2/3 Codex lifecycle, approval, generation rebound, controller/delete, oracle, stage-journal and exact-effect semantics are frozen unless a direct integration test proves a regression.

## Absolute zero-real-effect boundary

During Repair-4:

- real Codex/app-server starts = `0`;
- real model/thread/Turn RPCs = `0`;
- real approval responses/ALLOW/DENY = `0`;
- real interrupt/delete = `0`;
- real P7.C15 ledger creation = `0`;
- P7.C14/P7.C13 ledger mutations = `0`;
- persistent-home mutations = `0`;
- retained P7.C14 orphan cleanup/mutation = `0`;
- Telegram = `0`;
- real process signals = `0`.

Do not create or set a P7.C15 real token.

## 1. Durable replay barrier precedes every run-specific mutation

Production source-gate evaluation remains read-only.

`P7C15PreparedFutureExecutor.production()` / `_production_with_authority()` may generate a random run hash and compute path STRINGS before ledger reservation, but MUST NOT create run-specific directories or files before the exact ledger reserve succeeds.

Forbidden before `ledger.reserve(...) == True`:

- `p7c15-state-parent-*` mkdir;
- `p7c15-work-parent-*` mkdir;
- isolated/controller/work/approval/boot/result/wire/journal/stage creation;
- any child spawn;
- any Codex effect.

Required production order:

1. source bundle gate PASS;
2. construct in-memory run hash/path plan only;
3. `P7C15DurableOneShotLedger.reserve(...)` using `/root/.codexcontrol/p7c15-one-shot.json`;
4. ONLY AFTER reserve: create and validate private state/work parents;
5. validate fresh run boundaries;
6. create root-only boot;
7. spawn exactly one owned child.

If any step after reservation fails, the ledger remains consumed and no retry is authorized.

### Required tests

Offline instrument directory creation and ledger reservation. Prove:

- successful path event order begins `LEDGER_RESERVED` before any `RUN_PARENT_CREATED`;
- simulated state-parent mkdir failure occurs after one ledger reservation and leaves the temp ledger consumed;
- simulated work-parent mkdir failure occurs after one ledger reservation and leaves the temp ledger consumed;
- source-gate failure creates neither ledger nor run parents;
- already-consumed ledger creates no new run parents and no child.

## 2. P7.C15-specific watchdog deadline from actual invocation plan

Do not use inherited `p7c13.REAL_WATCHDOG_HARD_DEADLINE` as the P7.C15 production hard deadline unless the implementation first proves it exceeds the ACTUAL P7.C15 sequential internal timeout plan. The current inherited value does not.

Freeze an explicit P7.C15 internal timeout invocation plan that counts repeated timeout windows, not just unique dictionary keys. It must conservatively cover the maximum sequential positive/owned-convergence path, including at minimum:

- fresh workdir creation;
- runtime generation 1 acquire;
- model/list;
- thread/start;
- Turn-1 start;
- Turn-1 terminal;
- generation-1 shutdown;
- generation-2 acquire;
- thread/resume;
- Turn-2 start;
- Turn-2 terminal;
- Turn-3 start;
- approval handling;
- Turn-3 request/terminal observer primary wait;
- Turn-3 observer terminal convergence and join allowance;
- Turn-4 start;
- Turn-4 active window;
- Turn-4 interrupt/terminal window;
- Turn-4 observer join/convergence allowance;
- shutdown before oracle;
- delete-generation acquire;
- controller open;
- pre-delete schema read;
- dialogue create;
- dialogue confirm;
- durable binding read;
- canonical application delete;
- final runtime shutdown;
- tombstone read;
- post-delete live-binding read;
- post-delete schema read;
- storage close.

Define a P7.C15-specific production hard deadline as:

`sum(actual invocation plan) + explicit safety margin`

with a positive bounded safety margin.

Production watchdog must use this P7.C15 value. Inherited TERM/KILL grace may remain unchanged.

Offline injected shorter watchdog bounds remain allowed only through explicit test seams.

### Required tests

- computed production deadline > sum of the explicit P7.C15 internal invocation plan;
- production constructor selects P7.C15 deadline, not inherited 670-second value;
- offline short injected bounds remain isolated to test seams;
- no literal `5.0/0.2/0.2` production fallback reappears.

## 3. Turn-3 second-request observer final post-join classification

Repair the late-window race in `_observe_turn3_request_after_response()`.

The final second-request fact MUST be derived after task ownership/join is complete.

Required final request-observer classes:

- `REQUEST_OBSERVED` — request task completed normally with an actual server request;
- `CANCELLED_BY_HARNESS_WITHOUT_REQUEST` — harness cancellation won before a request was delivered;
- `OBSERVER_ERROR` — any unexpected exception, external cancellation, or ambiguous terminal state.

Rules:

- any `REQUEST_OBSERVED` before observer ownership ends => Turn-3 NON-PASS;
- no second response is ever sent;
- if request and terminal are both final, fail closed;
- if the request completes after the last preliminary snapshot but before/during join, final classification MUST still be `REQUEST_OBSERVED`;
- only harness-owned cancellation without request is a clean no-request close;
- all tasks terminalized/joined; no detached observer;
- response/ALLOW totals remain exactly 1/1 from the first request.

### Deterministic race test

Use controlled scheduling, not arbitrary sleeps:

1. preliminary request snapshot observes pending;
2. terminal path begins finalization;
3. request task completes normally with one second request before/during final join;
4. post-join classification observes the request;
5. Turn-3 gate fails;
6. no second response;
7. Turn-4/controller/delete callbacks remain unreachable.

## 4. Every controller close is bounded and owned

Eliminate direct production `await storage.close()` calls from early schema/binding/official-observation error branches.

Preferred structure: after successful `SqliteStorage.open()`, use one `try/finally` and close through:

`p7c13._await_owned(storage.close(), timeout=..., stage="controller close")`

exactly once.

If a preceding stage fails, bounded close still runs. If bounded close itself fails/nonconverges, child remains non-PASS.

Do not double-close.

Offline negative tests must cover at least:

- pre-delete schema mismatch;
- durable binding mismatch;
- official observation missing/malformed;
- delete failure/UNKNOWN;

and prove controller close ownership is finite with no duplicate delete/RPC.

## 5. Persist safe parent terminal containment authority

P7.C15 ledger recovery must retain enough SAFE parent facts to classify a consumed run without reconstructing ephemeral process-group state later.

At minimum persist in terminal recovery:

- `watchdog_status`;
- `child_result_valid`;
- `child_status` when available;
- `child_verdict` when available;
- `runtime_child_quiescent` when available;
- `exact_effect_gate` boolean when child result available;
- `owned_group_active` integer;
- `owned_group_zombies` integer;
- `group_scan_errors` integer;
- `signals_sent_count` integer;
- bounded signal-class list or safe integer tuple if desired;
- `child_count`;
- `retry_count`;
- existing safe last-confirmed-stage authority;
- safe child-result authority hash/class.

Do NOT persist raw thread/Turn IDs, prompts, responses, wire plaintext or tokens.

For COMPLETED, the persisted values must independently agree with the parent PASS predicate:

- watchdog COMPLETED;
- valid child result;
- child PASS/verdict true;
- runtime-child quiescent true;
- exact effect gate true;
- active=0;
- zombies=0;
- scan errors=0;
- child_count=1;
- retry_count=0.

For FAIL/TIMEOUT/UNKNOWN/CONFIRMED_PENDING, persist the actual observed safe parent containment facts without reclassifying them as success.

## 6. Do not regress accepted Repair-3 behavior

Preserve exactly:

- real-client-shaped approval authority;
- no fake response counters;
- one second-request observer and no second response;
- fresh Turn-1/Turn-2 markers and message proof;
- authenticated selected model/reasoning effort;
- one model/list total;
- generation rebound;
- private umask;
- root-owned 0600 target proof;
- bounded stage operations;
- real Turn-3/Turn-4/controller/delete continuation;
- canonical `DialogueDeleteService.delete()` exactly once;
- independent official observation;
- UNKNOWN / CONFIRMED_PENDING no-retry mapping;
- separate persistent/isolated post-delete proof;
- derived unrelated-removal fact;
- isolation-envelope validation;
- post-delete schema v4 re-read;
- runtime-child quiescence;
- exact effect parent PASS gate;
- P7.C14 orphan isolation.

## 7. Static anti-regression gates

Fail focused preparation if production source again contains equivalent behavior to:

- run-parent `mkdir` before ledger reserve;
- inherited P7.C13 hard deadline without P7.C15 invocation-plan proof;
- pre-join-only Turn-3 request classification;
- direct unbounded production `await storage.close()`;
- terminal ledger recovery lacking parent group scan facts;
- fake-only approval counters;
- synthetic post-Turn-2 continuation;
- fixed production clocks;
- hard-coded parent group zeroes in child post-delete proof;
- second delete/retry.

## 8. File scope

Allowed tracked modifications only:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`.

Optional one P7.C15-only helper under `tests/real/` only if strictly necessary.

Forbidden:

- `src/**`;
- P7.C14 launcher;
- P7.C13 harness;
- P7.C12 matcher;
- historical P7.C6-P7.C14 evidence/source;
- package markers;
- migrations/deployment/Telegram/P8/P9.

## 9. Required validation

Run:

- focused P7.C15 Repair-4;
- pre-ledger mutation ordering matrix;
- watchdog invocation-plan proof;
- deterministic Turn-3 late-window observer race;
- bounded controller-close negative matrix;
- parent recovery persistence matrix;
- complete Repair-3 positive + negative production-shaped suite;
- P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 non-real regressions;
- complete non-real pytest with every real gate unset;
- unittest discovery with every real gate unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## 10. Gate-disabled smoke

With all P7.C15 real authority variables unset:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c15_final_hard_delete_successor --p7c15-real-run`

must:

- exit `2`;
- leave `/root/.codexcontrol/p7c15-one-shot.json` absent;
- create no P7.C15 run parents;
- start no Codex/app-server process;
- touch no P7.C14/P7.C13 authority.

## 11. Evidence

Update:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`

Record:

- `P7C15_REPAIR4_BASE_HEAD=84b901f7af208ecde240b0ba0ed13188376b4104`;
- `P7C15_REPAIR4_BASE_TREE=31c2c22b5d11dafdcd06b8fb96e5dd0e880fc1ce`;
- `PRIOR_P7C15_LAUNCHER_BLOB=5e964d9408413b968b03e334759037f906174ffd`;
- `PRIOR_P7C15_EVIDENCE_BLOB=2cc14317db626d58d62189cc2669c9a7c78cb07d`;
- final launcher/evidence/helper blobs;
- pre-ledger ordering proof;
- actual P7.C15 internal timeout-plan total and production watchdog deadline;
- Turn-3 final post-join classification proof;
- bounded controller-close proof;
- safe parent terminal recovery examples for PASS, FAIL and TIMEOUT/non-PASS;
- full validation totals;
- zero-real-effect accounting.

Required final lines:

`P7C15_REPAIR4_LEDGER_BEFORE_RUN_MUTATION=PASS|FAIL`

`P7C15_REPAIR4_WATCHDOG_COVERS_ACTUAL_STAGE_PLAN=PASS|FAIL`

`P7C15_REPAIR4_TURN3_POST_JOIN_REQUEST_CLASSIFICATION=PASS|FAIL`

`P7C15_REPAIR4_BOUNDED_CONTROLLER_CLOSE=PASS|FAIL`

`P7C15_REPAIR4_PARENT_TERMINAL_RECOVERY_AUTHORITY=PASS|FAIL`

`P7C15_REPAIR4_REPAIR3_NO_REGRESSION=PASS|FAIL`

`P7C15_PREP_READY=YES|NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c15-hard-delete-successor-repair4-2026-09-13`

created from exact Repair-3 candidate `84b901f7af208ecde240b0ba0ed13188376b4104`.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect acceptance remains required before any P7.C15 real token or one-shot execution contract exists.
