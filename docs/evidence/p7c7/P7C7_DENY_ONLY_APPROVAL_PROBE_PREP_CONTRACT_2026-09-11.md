# P7.C7 DENY-only approval-probe preparation contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / PREPARATION ONLY / REAL PROBE NOT AUTHORIZED**

## Purpose

The zero-effect P7.C7 approval-stimulus authority correctly ended with `P7C7_APPROVAL_REQUEST_GRAMMAR=NOT_ESTABLISHED`. Exact Codex 0.144.6 source proves the mapping from an already-existing internal command vector to app-server `params.command`, but not the command vector a future model turn will generate from a natural-language stimulus.

The next safe step is therefore to prepare, but not execute, one future empirical fresh-thread approval probe whose approval operator can never ALLOW. The probe exists only to observe the real app-server approval-request grammar and routing outcome without permitting the unknown command to execute through an approval response.

## Absolute boundary

This preparation slice has zero real effects. It may not start Codex/app-server, create/resume/read/list/delete a thread, start/interrupt a turn, answer an approval, call Telegram, signal a real Codex process, mutate P7.C6 forensic state, or mutate persistent/session/controller/isolated state.

Production `src/**` is frozen. P7.C6 retained state is forensic-only and must not be reused as an execution target.

## Future probe design authority

The prepared harness must use one future fresh disposable P7.C7 thread only after separate architect authorization.

The future probe budget is not authorized by this document, but the prepared harness must be capable of enforcing the following maximum design:

- one `model/list`;
- one `thread/start` creating one fresh disposable thread;
- zero `thread/resume`;
- one primary probe `turn/start`;
- zero ALLOW approval responses, ever;
- any observed approval request response must be `DENY` only;
- no `thread/delete` during the probe;
- zero `thread/read` / `thread/list`;
- zero Telegram effects.

No production hard-delete conclusion may be drawn from the probe itself.

## Fresh run-owned boundaries

The harness must prepare a fresh root-owned 0700 run root under `/tmp` with independent:

- isolated state root;
- isolated sqlite/log roots;
- empty probe workdir;
- exact high-entropy outside-workdir sentinel path that remains inside the fresh probe run root;
- root-only 0600 probe ledger;
- root-only 0600 wire-command recovery record;
- root-only one-shot probe latch.

The persistent authenticated home remains `/root/.codex_second` and is shared under ADR-0045. The harness may own only its own child/generation and fresh isolated/controller/run boundaries.

No P7.C6 latch/recovery/session file may be modified or used as the future probe thread.

## Candidate stimulus

The prepared probe stimulus must remain the empirically motivated bounded semantic class:

- one finite sleep of exactly 30 seconds;
- then one touch of the exact fresh run-owned sentinel outside the turn workdir;
- no other requested operation;
- if an approval is denied, the prompt instructs the model to stop and perform no alternative operation.

The prompt must not claim approval is guaranteed.

The sentinel path must be dynamic/high-entropy and unavailable before the fresh run is materialized.

## DENY-only operator invariant

The probe operator must have no code path that returns `ALLOW`.

This must be structurally and behaviorally testable.

For every normalized approval request it observes, it may capture finite identity/grammar evidence locally, but its decision is always `DENY`.

It must record locally, root-only:

- request count;
- request kind;
- thread/turn/cwd identity match booleans;
- wire command SHA-256 if a finite command projection exists;
- bounded structural grammar decomposition of the wire command;
- raw wire command only in the root-only recovery record, never Git;
- parsed command metadata only in bounded sanitized form;
- response dispatch/result status.

No raw command, raw thread ID, raw turn ID, raw sentinel path, prompt or response may enter Git.

## Exact identity validation

The operator must be parameterized by the future fresh thread ID, exact turn ID, exact workdir and exact sentinel authority.

The turn ID may be supplied via a future resolved after `turn/start` confirmation, but the operator must fail closed if the request arrives with mismatched or absent identity.

Identity mismatch still receives `DENY` if a response is safely owned. It can never become ALLOW.

## Race model: approval request versus turn terminal

The P7.C6 mistake must not be repeated.

The probe must observe approval and turn terminal concurrently after `turn/start` confirmation. It must not assume an approval request will exist and must not wait for approval before observing terminal state.

The future probe needs finite classifications for at least:

- `APPROVAL_REQUEST_OBSERVED_BEFORE_TERMINAL`;
- `TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`;
- `APPROVAL_AND_TERMINAL_RACE_AMBIGUOUS`;
- protocol/runtime terminal;
- watchdog timeout.

A turn completing without approval is a valid empirical probe outcome, not a harness timeout defect.

## Approval observed path

If exactly one approval request is observed:

1. capture the normalized request and wire command into root-only authority;
2. respond exactly `DENY`;
3. record response result;
4. do not approve any command;
5. continue finite observation of the exact turn to a terminal state or a separately frozen containment action.

The preparation harness must not infer future ALLOW matcher authority automatically. Architect review of probe evidence is required first.

## Additional approval request safety

The harness must not silently leave later approval requests unanswered while continuing the probe.

Preparation must define a fail-closed policy for any second or later request. Preferred design: a bounded deny-only drain that may respond `DENY` to additional requests up to a small frozen maximum while the exact probe turn remains active, with every response counted and no ALLOW path.

If the maximum is exceeded, the probe is not PASS. The later real execution contract must define how the exact turn/runtime is finitely contained without reusing or deleting the thread.

This preparation slice must test that all response paths are DENY-only.

## No-approval execution path

If the probe command executes without an approval request, its only intended mutation is the exact fresh sentinel. Preparation must include post-run boundary checks capable of detecting unexpected files/processes under the fresh run root/workdir.

The future probe is not allowed to treat sentinel creation as approval evidence. It records only that the bounded candidate stimulus executed without approval.

## Process ownership

Reuse the accepted P7.C6 dedicated child process-group watchdog design conceptually, but do not copy raw P7.C6 one-shot state.

The future probe executor must run in its own session/process group; watchdog termination must target only that exact group; normal exit requires group quiescence; unrelated shared-home processes must survive untouched.

Preparation tests must be synthetic only.

## Probe replay barrier

The future real probe must be one-shot once separately authorized.

Preparation must define a fresh P7.C7 probe latch under `/root/.codexcontrol` or another architect-approved root-only authority. The latch is exclusive-create before the first real P7.C7 RPC and is never overwritten to permit rerun.

The preparation tests use temporary synthetic latch paths only.

## Offline test requirements

At minimum prove:

- operator source/behavior has zero ALLOW path;
- exact command-execution request with matching identity is captured then DENIED;
- wrong thread is DENIED;
- missing thread is DENIED;
- wrong turn is DENIED;
- missing turn is DENIED;
- wrong cwd is DENIED;
- unsupported approval kind is DENIED;
- malformed request is DENIED/fail-closed according to production bridge behavior;
- zero approval request + terminal turn is a finite valid outcome;
- approval request before terminal is captured and denied;
- terminal/approval race is finite;
- multiple requests are all denied up to the frozen maximum;
- no response counter can record an ALLOW;
- raw wire command remains only in synthetic root-only record;
- sanitized evidence contains only hashes/grammar labels;
- synthetic watchdog owns descendants and leaves unrelated process alive;
- no P7.C6 retained path is used as synthetic execution state;
- ordinary real gate remains disabled.

## Allowed repository changes

Preparation may add only:

- a new gated/test harness under `tests/real/` or a dedicated test-only helper under `tests/**` for the future P7.C7 probe;
- offline unit tests under `tests/**`;
- `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, CURRENT_WORK, ROADMAP, config or deployment change is allowed in the executor branch.

## Completion criterion

Preparation passes only if architect can independently verify:

1. future probe cannot emit ALLOW under any request shape;
2. approval/terminal are observed concurrently rather than approval being assumed;
3. exact real wire command can be captured root-only and published only as hash/structural labels;
4. later requests are also fail-closed DENY-only;
5. probe run root/process tree is bounded and isolated;
6. one-shot replay barrier exists;
7. real gate is disabled during preparation;
8. no production source changed and no real Codex effect occurred.

Passing preparation does not authorize the fresh thread. Architect must separately accept the harness and freeze a one-shot real probe execution contract.

`P7C7_DENY_ONLY_PROBE_PREPARATION=NOT_YET_ACCEPTED`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
