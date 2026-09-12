# P7.C10 one-shot real DENY-only approval probe execution contract — 2026-09-12

Status: **FROZEN / ONE-SHOT REAL PROBE AUTHORIZED ONLY UNDER EXACT EXECUTION GATE**

## Exact executable authority

The real probe must execute only from the detached architect-accepted snapshot:

- HEAD: `3732134246464df899837a3c499c86c52270b038`
- tree: `68be37c8a5d0aa132199f8b2782618638a07b87e`
- harness blob: `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`

Later governance commits must not be used as the executable snapshot.

## Authorization

Exactly one invocation may be started with token:

`AUTHORIZED_P7C10_DENY_ONLY_APPROVAL_PROBE_2026_09_12`

and exact source variables:

`CODEXCONTROL_P7C10_PROBE_EXPECTED_HEAD=3732134246464df899837a3c499c86c52270b038`

`CODEXCONTROL_P7C10_PROBE_EXPECTED_TREE=68be37c8a5d0aa132199f8b2782618638a07b87e`

The token exists only in that single process environment. Once the real command starts, P7.C10 is permanently consumed under every outcome. No rerun is authorized.

## One-shot authorities

Before launch require absent:

- `/root/.codexcontrol/p7c10-deny-only-approval-probe-ledger.json`
- `/root/.codexcontrol/p7c10-deny-only-approval-probe-result.json`
- `/root/.codexcontrol/p7c10-deny-only-approval-probe-outcome.json`

P7.C7/P7.C8/P7.C9 retained authorities remain untouched and do not block P7.C10 merely by existing.

## RecoveryJournal authority

The future run uses the accepted schema-aware RecoveryJournal.

Structural harness-owned events are validated through a finite allowlist and are not treated as raw protocol payload. In particular the exact record:

`{"event":"TURN_ID_AUTHORITY","result":"ESTABLISHED"}`

is a valid structural authority.

Raw thread IDs, Turn IDs, sentinel paths, wire commands/plaintext, prompts/responses, session content, credentials and tokens remain forbidden in the journal.

Future normal ordering is binding:

1. production `turn/start` returns `CONFIRMED` with non-null `TurnBinding`;
2. exact in-memory Turn authority is set;
3. durable `TURN_ID_AUTHORITY=ESTABLISHED` is appended;
4. durable `APPROVAL_OBSERVER_ARMED=YES` is appended;
5. approval/terminal observation may begin.

Normal child and parent success require exact retained-journal chronology.

## Production state-root authority

The fresh P7.C10 isolated state root must be absent before provisioning. The child reserves the global latch and then uses production `IsolatedStateRoot(authority).provision(profile)` followed immediately by `validate(profile)`.

No manual marker/sqlite/logs creation is allowed.

Normal continuation requires provision and validation both `CONFIRMED` with worker owner `TERMINALIZED`. Failure/nonconvergence forbids runtime acquisition and downstream RPCs.

## Runtime acquisition authority

After confirmed state-root authority, runtime acquisition uses the accepted bounded authority:

- acquire ceiling 45s;
- distinct initial/final acquire classes;
- at most one failed-acquire `shutdown_profile()` containment attempt bounded by 12s plus 1s cancel/join;
- safe categorized error projection only;
- parent recovery fails closed with `RUNTIME_ACQUIRE_NOT_ESTABLISHED` for missing/unsafe/conflicting evidence.

## Real effect budget

Maximum:

- one owned app-server runtime generation;
- model/list <= 1;
- fresh thread/start <= 1;
- primary turn/start <= 1;
- approval DENY attempts 0..3;
- approval ALLOW attempts 0;
- thread/resume 0;
- turn/interrupt 0;
- thread/delete 0;
- thread/read 0;
- thread/list 0;
- Telegram 0;
- unknown RPC 0;
- one parent child and zero retries.

## Stimulus and DENY-only invariant

The primary Turn requests exactly one 30-second sleep followed by one exact high-entropy P7.C10 run-owned sentinel touch outside the Turn workdir but inside the fresh run root.

Every owned approval request is DENY. ALLOW is impossible. DENY ambiguity consumes its attempt. No fourth approval response is permitted. If denied, stop without an alternative command/tool or retry.

## Observation / process authority

Approval/terminal observation: 100s.

Parent hard watchdog: 207.001s.

Exactly one dedicated Python child is started with `start_new_session=True`; child PID=PGID=SID. Parent may target only that process group, with at most one SIGTERM and one SIGKILL. No second child and no retry.

## Normal final authority

A normal final observation requires, among the existing source/process/boundary gates:

- production state-root provision `CONFIRMED`, owner `TERMINALIZED`, no error category;
- production state-root validation `CONFIRMED`, owner `TERMINALIZED`, no error category;
- runtime acquire initial/final `CONFIRMED`, no acquire error/cleanup facts;
- durable Turn chronology exactly confirmed-start -> Turn authority -> observer armed;
- model/list=1, thread/start=1, turn/start=1;
- valid fresh thread/Turn SHA-256;
- resume/interrupt/delete/read/list=0;
- ALLOW=0; DENY counters reconciled and <=3;
- observer owners terminalized;
- finite runtime shutdown;
- child and parent boundaries safe with no drift;
- process group quiescent with zero scan errors;
- one child, zero retry;
- exact accepted HEAD/tree.

Failure or ambiguity never authorizes rerun, cleanup to manufacture success, matcher authority or hard-delete execution.

## Post-run disposition

Any fresh thread/Turn established becomes evidence-only pending architect review. The probe never deletes it.

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C10_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

P8/P9 remain blocked.
