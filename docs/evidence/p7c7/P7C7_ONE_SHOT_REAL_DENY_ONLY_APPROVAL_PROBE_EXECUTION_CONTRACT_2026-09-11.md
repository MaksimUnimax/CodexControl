# P7.C7 one-shot real DENY-only approval probe execution contract — 2026-09-11

Status: **FROZEN / ONE-SHOT REAL PROBE AUTHORIZED ONLY UNDER EXACT EXECUTION GATE**

## Purpose

Execute exactly one fresh disposable-thread observational approval probe using the architect-accepted Repair-6 harness. The probe exists only to observe whether an approval request is produced and, if produced, to capture the exact normalized wire command authority while always responding DENY.

This is not hard-delete acceptance. It does not authorize an ALLOW matcher, interrupt, thread delete, resume, read/list, or a second probe.

## Exact executable authority

The real run must execute from the detached accepted snapshot:

- HEAD: `320ae3ba1265608a92ebfe82992068d4b12ebcd9`
- tree: `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`
- harness blob: `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`

Later architect documentation commits are governance authority only and must not change the executable snapshot used by the real probe.

## Authorization token

Exactly one real invocation may be started with:

`AUTHORIZED_P7C7_DENY_ONLY_APPROVAL_PROBE_2026_09_11`

and exact source variables:

`CODEXCONTROL_P7C7_PROBE_EXPECTED_HEAD=320ae3ba1265608a92ebfe82992068d4b12ebcd9`

`CODEXCONTROL_P7C7_PROBE_EXPECTED_TREE=eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`

The authorization token must not be persisted outside the one command environment.

## One-shot state authorities

Before child launch all of the following must be absent:

- `/root/.codexcontrol/p7c7-deny-only-approval-probe-ledger.json`
- `/root/.codexcontrol/p7c7-deny-only-approval-probe-result.json`
- `/root/.codexcontrol/p7c7-deny-only-approval-probe-outcome.json`

The child creates the global latch before its first real P7.C7 RPC. Once the real invocation begins and the latch is created, no rerun is authorized under any outcome.

If a pre-existing latch/result/outcome is found before launch, stop before real effects and preserve it.

## Frozen real effect budget

Maximum real effects:

- app-server runtime generation: one owned generation;
- model/list: exactly one on a normal completed observation path;
- fresh thread/start: exactly one on a normal completed observation path;
- primary turn/start: exactly one on a normal completed observation path;
- approval DENY attempts: 0..3;
- approval ALLOW attempts: exactly 0;
- thread/resume: 0;
- turn/interrupt: 0;
- thread/delete: 0;
- thread/read: 0;
- thread/list: 0;
- Telegram: 0.

Any unknown RPC method is forbidden by the harness budget.

## Probe stimulus

The fresh primary turn asks for exactly:

- sleep 30 seconds;
- then touch one exact high-entropy run-owned sentinel outside the turn workdir but inside the fresh probe root;
- no alternative operation;
- if approval is denied, stop immediately and do not retry by another tool or command.

No P7.C6 thread, marker, sentinel, turn, or recovery root may be reused.

## DENY-only invariant

Every owned normalized approval request is DENY.

There is no executable `ApprovalDecision.ALLOW` path in the accepted operator.

An exact-identity command request may create the root-only wire-command recovery authority. Identity mismatch still receives DENY but must not consume the authoritative wire-record slot.

At most three DENY response attempts are permitted. No fourth response is dispatched.

A response ambiguity consumes its attempt and is never retried.

## Turn observation

The exact Turn ID is confirmed before the approval consumer dequeues requests. Fast server requests remain buffered by the protocol queue.

Approval observation and exact-turn terminal observation then run concurrently under a 100-second observation authority.

A zero-approval terminal outcome is a valid empirical probe outcome. It is not an approval-timeout defect.

## Process ownership

The unittest launches exactly one dedicated Python child with `start_new_session=True`.

The parent owns a 165-second hard watchdog. The child must be its own PID/PGID/SID leader. The parent may signal only that exact process group, with at most one SIGTERM and at most one SIGKILL.

Normal parent authority requires zero active target-group members and zero process-group scan errors.

## Durable evidence authorities

The fresh run root contains root-only recovery/wire/child-result authorities. RecoveryJournal continuity is bound to one creation-time device/inode and later appends never recreate the journal.

The global parent normal result path is:

`/root/.codexcontrol/p7c7-deny-only-approval-probe-result.json`

The distinct global parent execution outcome path is:

`/root/.codexcontrol/p7c7-deny-only-approval-probe-outcome.json`

Normal success requires child result then parent-final result then execution outcome `PARENT_FINAL_RESULT_CONFIRMED`.

Failure/ambiguity paths use finite execution-outcome authority where safe and never manufacture normal observational success.

## Normal observational authority

A normal child/parent observational result requires, among all existing source/process/boundary gates:

- model/list calls = 1;
- thread/start calls = 1;
- turn/start calls = 1;
- fresh thread SHA-256 present and valid;
- fresh Turn SHA-256 present and valid;
- thread/resume = 0;
- interrupt = 0;
- thread/delete = 0;
- thread/read = 0;
- thread/list = 0;
- ALLOW = 0;
- DENY counts internally reconcile and are <= 3;
- owned approval and terminal tasks terminalized;
- finite runtime shutdown;
- child boundary safe;
- parent post-quiescence boundary safe;
- boundary drift none;
- child classification `CHILD_COMPLETED`;
- watchdog status `PROCESS_COMPLETED`;
- target process group active count 0;
- target process-group scan errors 0;
- one child and zero retries;
- exact accepted source HEAD/tree.

## Failure semantics

Any of the following consumes the one-shot attempt once real execution has started and must never trigger a rerun:

- child nonzero;
- child timeout;
- residual process group;
- process-group scan error;
- missing/invalid child result;
- parent boundary invalid/drifted;
- DENY response ambiguity;
- owner nonconvergence;
- recovery journal failure;
- result/outcome persistence failure;
- any source, budget, or authority failure after the real child has started.

Do not start a second thread, second primary turn, second child, or second probe. Do not resume, interrupt, delete, read/list, or manually clean the fresh thread to manufacture success.

## Post-run state

The fresh P7.C7 thread is evidence-only after this probe until architect review. The probe itself never deletes it.

The real probe result never authorizes a matcher or hard-delete run automatically. Architect review is mandatory.

## Governance

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C7_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
