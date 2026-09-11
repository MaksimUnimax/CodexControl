# P7.C9 one-shot real DENY-only approval probe execution contract — 2026-09-11

Status: **FROZEN / ONE-SHOT REAL PROBE AUTHORIZED ONLY UNDER EXACT EXECUTION GATE**

## Exact executable authority

The real run must execute from the detached accepted snapshot:

- HEAD: `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`
- tree: `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`
- harness blob: `44271459c2b4523f97551ade93563aee96def1c3`

Later governance commits must not be used as the executable snapshot.

## Authorization

Exactly one invocation may be started with:

`AUTHORIZED_P7C9_DENY_ONLY_APPROVAL_PROBE_2026_09_11`

and exact source variables:

`CODEXCONTROL_P7C9_PROBE_EXPECTED_HEAD=6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`

`CODEXCONTROL_P7C9_PROBE_EXPECTED_TREE=1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`

The token exists only in the environment of that single invocation. Once the command starts, P7.C9 is consumed under every outcome and no rerun is authorized.

## One-shot authorities

Before launch require absent:

- `/root/.codexcontrol/p7c9-deny-only-approval-probe-ledger.json`
- `/root/.codexcontrol/p7c9-deny-only-approval-probe-result.json`
- `/root/.codexcontrol/p7c9-deny-only-approval-probe-outcome.json`

P7.C7/P7.C8 retained authorities remain untouched and do not block P7.C9 merely by existing.

## Production state-root authority

The fresh P7.C9 state root must be absent before provisioning. The child reserves the global P7.C9 latch before state-root provisioning, then calls production `IsolatedStateRoot(authority).provision(profile)` followed immediately by production `validate(profile)`.

The harness does not manually create the marker, `sqlite/`, or `logs/` layout.

Normal continuation requires provision result `CONFIRMED`, provision owner `TERMINALIZED`, validation result `CONFIRMED`, and validation owner `TERMINALIZED`.

A state-root failure/nonconvergence forbids runtime acquire and every downstream model/list/thread/Turn/approval effect. Worker timeout/nonconvergence is explicit durable authority; the parent process-group watchdog remains final child-process owner.

## Runtime acquisition authority

After confirmed state-root provisioning/validation, runtime acquisition uses the accepted P7.C8 authority: 45-second acquire ceiling; distinct initial/final acquisition classes; at most one 12-second `shutdown_profile()` containment attempt plus 1-second cancel/join; safe categorized errors only; fail-closed parent reconstruction with `RUNTIME_ACQUIRE_NOT_ESTABLISHED` for missing/unsafe/conflicting evidence.

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

The fresh primary Turn requests exactly one 30-second sleep followed by one exact high-entropy run-owned sentinel touch outside the Turn workdir but inside the P7.C9 run root. If an approval is produced, every owned request is DENY. There is no ALLOW path. A DENY ambiguity consumes its attempt and is not retried. No fourth approval response is permitted.

## Observation / process authority

Approval/terminal observation: 100 seconds.

Parent hard watchdog: 207.001 seconds.

Exactly one dedicated Python child is started with `start_new_session=True`; child PID=PGID=SID. Parent may target only that exact process group, with at most one SIGTERM and at most one SIGKILL. No retry or second child.

## Normal authority

A normal final observation requires, among the accepted source/process/boundary gates:

- state-root provision `CONFIRMED`, owner `TERMINALIZED`, no provision error category;
- state-root validate `CONFIRMED`, owner `TERMINALIZED`, no validate error category;
- runtime acquire initial/final `CONFIRMED`, no acquire error/cleanup facts;
- model/list=1, thread/start=1, turn/start=1;
- valid fresh thread/Turn SHA-256;
- resume/interrupt/delete/read/list=0;
- ALLOW=0; DENY counters reconciled and <=3;
- owned observers terminalized;
- finite runtime shutdown;
- child and parent boundaries safe, drift none;
- process group quiescent with zero scan errors;
- one child, zero retry;
- exact accepted HEAD/tree.

Failure/ambiguity never authorizes rerun, cleanup to manufacture success, matcher authority, or hard delete.

## Post-run disposition

Any fresh thread established becomes evidence-only pending architect review. The probe itself never deletes it.

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C9_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

P8/P9 remain blocked.
