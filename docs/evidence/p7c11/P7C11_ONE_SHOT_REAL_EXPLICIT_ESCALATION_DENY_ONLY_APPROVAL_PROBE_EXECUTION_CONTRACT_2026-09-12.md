# P7.C11 one-shot real explicit-escalation DENY-only approval-probe execution contract — 2026-09-12

Status: **FROZEN / ONE-SHOT REAL PROBE AUTHORIZED ONLY UNDER EXACT EXECUTION GATE / NOT HARD-DELETE ACCEPTANCE**

## Exact executable authority

The real probe may execute only from the detached architect-accepted snapshot:

- HEAD: `be98542b9bcbf99508784f229057698d85784367`;
- tree: `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`;
- harness blob: `fc67299d80c3d617280975182c097a92cb863b92`.

Later governance commits are not executable authority.

## Authorization

Exactly one invocation may be started with:

`AUTHORIZED_P7C11_DENY_ONLY_APPROVAL_PROBE_2026_09_12=AUTHORIZED_P7C11_DENY_ONLY_APPROVAL_PROBE_2026_09_12`

and exact source vars:

`CODEXCONTROL_P7C11_PROBE_EXPECTED_HEAD=be98542b9bcbf99508784f229057698d85784367`

`CODEXCONTROL_P7C11_PROBE_EXPECTED_TREE=ec6433f02f9293273979fd5dfc3f3eff70f16fa4`

The auth values exist only in the single child-launch process environment. Once the real command starts, P7.C11 is permanently consumed under every outcome. No rerun is authorized.

## One-shot global authorities

Before launch require absent:

- `/root/.codexcontrol/p7c11-deny-only-approval-probe-ledger.json`;
- `/root/.codexcontrol/p7c11-deny-only-approval-probe-result.json`;
- `/root/.codexcontrol/p7c11-deny-only-approval-probe-outcome.json`.

Existing P7.C7–P7.C10 authorities are historical and do not block P7.C11 merely by existing. They must remain untouched.

## Source-backed approval target

The parent generates exactly one high-entropy target directly under `/root` with grammar:

`^\.codexcontrol-p7c11-escalation-probe-[0-9a-f]{32}$`

It must be absent before child launch and remain outside `/tmp`, resolved `$TMPDIR`, Turn cwd, run root, repository root, persistent Codex home, isolated state root, controller root and `/root/.codexcontrol`.

The target is not pre-created. The real probe never cleans it. If it unexpectedly exists, preserve it for evidence and do not retry.

The raw target path is local-only authority. Git-visible evidence may contain only SHA-256, finite location class and safe exact-path metadata.

## Source-backed stimulus

The primary Turn instructs the model to perform exactly one shell-command tool call whose command is exactly:

`touch <exact-external-target>`

The first and only shell-command tool call must request:

`sandbox_permissions=require_escalated`

before execution and include a short justification.

The instruction forbids:

- default-sandbox first attempt;
- alternate command;
- alternate path;
- apply_patch;
- Python/file-edit emulation;
- network;
- second tool call;
- retry after DENY.

This route is source-backed by Codex `rust-v0.144.6`, peeled commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`, whose approval integration tests establish `OnRequest + workspace-write + RequireEscalated -> ExecApproval`.

The future model is still observational; compliance is not assumed.

## DENY-only authority

Every owned approval request is DENY.

- ALLOW paths = 0;
- DENY attempts <= 3;
- no fourth response;
- `RESPONSE_UNKNOWN` consumes its attempt;
- request observation is durable before DENY dispatch intent;
- wrong kind/identity remains DENY but cannot consume authoritative command-wire capture;
- no retry after DENY.

## Preferred authoritative command-approval observation

Preferred empirical success class:

`COMMAND_APPROVAL_OBSERVED_AND_DENIED`

It may be projected only when all accepted Repair-1 authorities hold:

- external target remains absent;
- one root-only authoritative command capture is established;
- authoritative kind is `COMMAND_EXECUTION`;
- exact thread/Turn/cwd identity is true;
- root-only wire authority validates;
- wire vector reconstruction is established;
- authoritative target reference class is `EXACT_ARG_TOKEN`;
- durable DENY chronology for that same request resolves to `DENIED_CONFIRMED`;
- ALLOW=0;
- approval and terminal owners are terminalized and owner nonconvergence is false.

`RESPONSE_UNKNOWN`, missing correlation, wrong request, non-command request or non-exact target reference can never be preferred success.

Zero-request or other finite outcomes remain valid observations but do not authorize matcher/hard delete.

## Parent target binding

The parent retains the exact raw target path in memory, re-observes that exact path after child quiescence, computes its own SHA-256 and requires equality with the child target SHA-256.

A target-hash mismatch or target presence prevents normal command-approval success.

No raw target path is persisted in Git evidence.

## Production state/runtime authority

Carry forward the accepted exact gates:

- production `IsolatedStateRoot.provision(profile)` then `validate(profile)`;
- provision/validate owner must be `TERMINALIZED` for normal continuation;
- runtime acquire ceiling 45s;
- failed-acquire containment at most one `shutdown_profile()` attempt, 12s plus 1s cancel/join;
- model/list <=1;
- fresh thread/start <=1;
- primary turn/start <=1;
- resume/interrupt/delete/read/list=0;
- Telegram=0;
- unknown RPC=0.

## Process authority

One dedicated Python child only, `start_new_session=True`, child PID=PGID=SID.

Zero retries.

Parent may target only the exact child process group with at most one SIGTERM and one SIGKILL.

P7.C11 uses the accepted 207.001s hard watchdog and accepted internal stage bounds.

## RecoveryJournal / wire authority

The accepted P7.C10 schema-aware RecoveryJournal remains binding:

- finite event allowlist;
- field-specific validation;
- durable Turn authority before observer arming;
- immutable dev/inode;
- no journal recreation;
- bounded/no-follow reader;
- no raw thread/Turn/path/command/prompt/response in journal.

Repair-1 additionally binds DENY intent/result `request_count` to the observed request ordinal and requires exact request chronology for authoritative DENY reconstruction.

Raw wire plaintext remains root-only and never Git-visible.

## Normal lifecycle/result authority

Any normal observational child result requires exact model/list=1, thread/start=1, turn/start=1, valid fresh-thread/fresh-Turn hashes, zero forbidden lifecycle calls, owner convergence, finite shutdown and safe child boundary.

Parent final authority separately validates child authority, durable Turn chronology, post-quiescence boundary, external-target absence/hash binding, process group quiescence, one child, zero retry and exact executable HEAD/tree.

`PARENT_FINAL_RESULT_CONFIRMED` is process/evidence finalization and is not automatically synonymous with command-approval stimulus success.

## Post-run disposition

Any fresh thread/Turn becomes evidence-only pending architect review.

The probe never resumes, interrupts, reads/lists or deletes it.

The probe never executes hard delete.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C11_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P7.C7–P7.C10 remain permanently consumed. P8/P9 remain blocked pending architect-accepted hard-delete acceptance.
