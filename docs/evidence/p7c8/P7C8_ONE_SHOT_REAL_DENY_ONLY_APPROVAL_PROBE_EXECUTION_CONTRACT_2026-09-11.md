# P7.C8 one-shot real DENY-only approval probe execution contract — 2026-09-11

Status: **FROZEN / ONE-SHOT REAL PROBE AUTHORIZED ONLY UNDER EXACT EXECUTION GATE**

## Purpose

Execute exactly one fresh disposable-thread observational approval probe using the architect-accepted P7.C8 Repair-1 harness.

This successor is not a P7.C7 retry. P7.C7 remains permanently consumed.

The P7.C8 probe exists only to observe whether an approval request is produced and, if produced, to capture the exact normalized wire-command authority while always responding DENY.

This is not hard-delete acceptance and does not authorize an ALLOW matcher, resume, interrupt, thread delete, thread read/list or a second probe.

## Exact executable authority

The real run must execute from this detached accepted snapshot:

- HEAD: `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`
- tree: `787e083077b7386a8b05968f2193c611d8182d9d`
- harness blob: `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`

Later architect documentation commits are governance authority only and must not change the executable snapshot used by the real probe.

## Authorization token

Exactly one real invocation may be started with:

`AUTHORIZED_P7C8_DENY_ONLY_APPROVAL_PROBE_2026_09_11`

and exact source variables:

`CODEXCONTROL_P7C8_PROBE_EXPECTED_HEAD=070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`

`CODEXCONTROL_P7C8_PROBE_EXPECTED_TREE=787e083077b7386a8b05968f2193c611d8182d9d`

The authorization token must exist only in the environment of the single invocation.

## P7.C8 one-shot state authorities

Before child launch all of the following P7.C8 paths must be absent:

- `/root/.codexcontrol/p7c8-deny-only-approval-probe-ledger.json`
- `/root/.codexcontrol/p7c8-deny-only-approval-probe-result.json`
- `/root/.codexcontrol/p7c8-deny-only-approval-probe-outcome.json`

P7.C7 authorities are expected to remain present and do not block P7.C8. They must not be modified.

The P7.C8 child creates the global latch before its first real P7.C8 RPC. Once the real invocation begins, it is consumed under every outcome. No rerun is authorized.

If any P7.C8 latch/result/outcome already exists before launch, stop before real execution and preserve it.

## Frozen real effect budget

Maximum real effects:

- one owned app-server runtime generation;
- model/list: exactly one on a normal completed observational path;
- fresh thread/start: exactly one on a normal completed observational path;
- primary turn/start: exactly one on a normal completed observational path;
- approval DENY attempts: 0..3;
- approval ALLOW attempts: 0;
- thread/resume: 0;
- turn/interrupt: 0;
- thread/delete: 0;
- thread/read: 0;
- thread/list: 0;
- Telegram: 0.

Unknown RPC methods are forbidden by the harness budget.

## Runtime acquisition authority

P7.C8 corrects the P7.C7 acquisition observability defect.

The runtime-acquire observer has a 45-second external ceiling and distinct initial/final durable classes:

- `RUNTIME_ACQUIRE_CONFIRMED`
- `RUNTIME_ACQUIRE_TIMEOUT`
- `RUNTIME_ACQUIRE_SAFE_EXCEPTION`
- `RUNTIME_ACQUIRE_UNEXPECTED_EXCEPTION`
- `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT`

For recognized `RuntimeErrorSafe`, only a finite safe category may be persisted. Raw exception text, traceback, stderr or environment must never be persisted.

If acquisition is not confirmed, no model/list, thread/start, turn/start or approval step may follow.

Failed acquisition performs at most one `manager.shutdown_profile(profile_id)` containment attempt under a 12-second bound, then at most one 1-second cancellation/join boundary. If ownership cannot converge, final acquisition authority is `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` and the dedicated parent process-group watchdog remains final owner.

The parent must reconstruct acquisition authority fail-closed from the retained journal. Missing, unsafe, duplicate, conflicting or inconsistent acquisition evidence is `RUNTIME_ACQUIRE_NOT_ESTABLISHED`, never optimistic `CONFIRMED`.

## Probe stimulus

The fresh primary turn requests exactly:

- sleep 30 seconds;
- then touch one exact high-entropy run-owned sentinel outside the turn workdir but inside the fresh P7.C8 run root;
- no alternative operation;
- if approval is denied, stop immediately and do not retry via another tool or command.

No P7.C6 or P7.C7 thread, Turn, marker, sentinel, root, recovery record or global authority may be reused.

## DENY-only invariant

Every owned normalized approval request is DENY.

There is no executable `ApprovalDecision.ALLOW` path.

An exact-identity command request may create the root-only raw wire-command authority. Identity mismatch still receives DENY but must not consume the authoritative wire slot.

At most three DENY attempts are permitted. No fourth response is dispatched. A response ambiguity consumes its attempt and is not retried.

## Turn observation

The exact Turn ID must be established before the approval consumer dequeues requests. Fast requests may be buffered by the protocol queue.

Approval observation and exact-turn terminal observation then run concurrently under a 100-second observation authority.

A zero-approval terminal outcome is a valid empirical outcome and is not itself an approval-timeout defect.

## Process ownership

The unittest launches exactly one dedicated Python child with `start_new_session=True`.

The parent owns a 205-second hard watchdog. The child must be its own PID/PGID/SID leader. The parent may signal only that exact process group, with at most one SIGTERM and at most one SIGKILL.

Normal parent authority requires zero active target-group members and zero process-group scan errors.

## Durable evidence authorities

The fresh P7.C8 run root contains root-only recovery/wire/child-result authorities. RecoveryJournal continuity is bound to one creation-time device/inode; later appends never recreate the journal.

The global normal result path is:

`/root/.codexcontrol/p7c8-deny-only-approval-probe-result.json`

The distinct parent execution outcome path is:

`/root/.codexcontrol/p7c8-deny-only-approval-probe-outcome.json`

Normal observation requires child result, parent-final result, then execution outcome `PARENT_FINAL_RESULT_CONFIRMED`.

Failure and ambiguity paths use finite execution-outcome authority where safely reconstructable and never manufacture normal success.

## Normal observational authority

A normal P7.C8 child/parent result requires, among all existing source/process/boundary gates:

- runtime acquire initial result = `RUNTIME_ACQUIRE_CONFIRMED`;
- runtime acquire final result = `RUNTIME_ACQUIRE_CONFIRMED`;
- runtime acquire error category = null;
- runtime acquire cleanup result/category = null;
- model/list calls = 1;
- thread/start calls = 1;
- turn/start calls = 1;
- fresh thread SHA-256 valid;
- fresh Turn SHA-256 valid;
- thread/resume = 0;
- interrupt = 0;
- thread/delete = 0;
- thread/read = 0;
- thread/list = 0;
- ALLOW = 0;
- DENY counters reconcile and are <=3;
- owned approval/terminal tasks terminalized;
- finite runtime shutdown;
- child boundary safe;
- parent post-quiescence boundary safe;
- boundary drift none;
- child classification `CHILD_COMPLETED`;
- watchdog status `PROCESS_COMPLETED`;
- target process-group active count 0;
- target process-group scan errors 0;
- one child, zero retries;
- exact accepted source HEAD/tree.

## Failure semantics

Any real invocation is consumed under success, failure, timeout or ambiguity.

Examples include:

- runtime acquire timeout;
- categorized safe runtime exception;
- unexpected acquire exception;
- acquisition cleanup timeout/nonconvergence;
- child nonzero;
- parent watchdog timeout;
- residual process group;
- process-group scan error;
- missing/invalid child result;
- parent boundary invalid/drifted;
- DENY response ambiguity;
- owner nonconvergence;
- recovery journal failure;
- result/outcome persistence failure;
- any source/budget/authority failure after child launch.

No failure authorizes a retry, second child, second thread, second Turn, resume, interrupt, delete, read/list or manual cleanup to manufacture success.

## Post-run state

Any fresh P7.C8 thread established by the probe becomes evidence-only until architect review. The probe itself never deletes it.

The probe result never automatically authorizes a matcher or hard-delete run.

## Governance

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C8_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

P8/P9 remain blocked.
