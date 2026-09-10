# P7.C6 Run 1 architect review — 2026-09-10

Status: **RUN_1_REJECTED / HARNESS_DEFECT / RETAINED_THREAD_FORENSIC_REQUIRED**

Repository: `MaksimUnimax/CodexControl`.

## Reviewed real-run lineage

- architect base: `32153c3d63bf6b45a8b16478566997c09e8e0cac`;
- architect base tree: `2dd760ba3fe7ea880c6c65db3eb6c0673d70ed75`;
- real-run / failure-evidence commit: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

The failure commit is exactly one commit above the architect base and adds only:

- `tests/real/test_p7_c6_real_hard_delete.py`;
- `docs/evidence/p7c6/P7C6_REAL_RUN_FAILURE_EVIDENCE_2026-09-10.md`.

No production `src/**`, deployment, Telegram, ADR, roadmap or controller configuration changed in the executor commit.

## Accepted factual outcome of Run 1

The single authorized real run reached real effects and therefore consumed the original Run-1 authorization. It used the corrected shared authenticated persistent home model and did not stop or signal unrelated Codex processes.

Safe observed effect accounting from the executor evidence:

- one authenticated `model/list`;
- one new real disposable thread;
- one `thread/resume` after runtime-generation restart;
- three real turn starts;
- Turn 1 and Turn 2 passed their bounded persistence checks;
- exactly one approval request was observed at Turn 3;
- no interrupt was performed;
- no official `thread/delete` was dispatched;
- no `thread/read` or `thread/list` was dispatched;
- the target recovery identity remains in a root-only local recovery ledger;
- P8/P9 remain blocked.

The executor forensic performed zero additional real Codex effects.

## Harness defect 1 — literal approval matcher

The P7.C6 harness implemented `_ExactApprovalOperator` as a literal string-membership matcher over three manually enumerated command strings.

That is not the already-established safe real-Codex approval grammar used in the historical P7 continuation. The historical `_FinalAllowOperator` tokenized the normalized command with `shlex` and admitted only:

1. `EXACT_INNER`; or
2. exactly one shell wrapper from `sh`, `/bin/sh`, `/usr/bin/sh`, `bash`, `/bin/bash`, `/usr/bin/bash` with only `-c` or `-lc`, whose inner token sequence exactly equals the expected bounded command.

The historical operator also required exact thread, turn, working directory, marker, sentinel, supported request kind and request count before ALLOW.

The C6 operator instead:

- compares the normalized `command:` line literally;
- manually guesses three textual renderings;
- accepts `request.thread_id is None` rather than requiring the target identity;
- does not verify the exact Turn-3 ID;
- does not verify the normalized working directory;
- does not persist finite mismatch diagnostics.

Therefore the C6 approval acceptance gate was invalid even independent of the unavailable concrete wire command. A Run-1 failure at that gate cannot establish a P1.7 production defect.

Classification:

`P7C6_RUN1_APPROVAL_GATE_CLASS=HARNESS_MATCHER_DEFECT`

This classification does **not** assert that the actual request was safely equivalent. The prior zero-effect forensic correctly reported insufficient local evidence for that narrower runtime fact.

## Harness defect 2 — one-shot latch is not materialized by the harness

The harness declares:

`/root/.codexcontrol/p7c6-real-one-shot-ledger.json`

as `ONE_SHOT_LEDGER` and checks whether a nonempty file already exists.

However the harness does not create or write that path when the authorized run starts. It instead creates a fresh per-run `recovery-ledger.json` under a newly allocated `/tmp/codexcontrol-p7c6-*` root.

Therefore the harness itself does not implement the frozen durable host-level one-shot latch promised by the C6 contract. Operator/executor discipline prevented an actual duplicate real run, so no duplicate real effect occurred, but the harness gate is defective.

Classification:

`P7C6_RUN1_ONE_SHOT_CLASS=HARNESS_LATCH_DEFECT`

## Approval response ambiguity

The published failure forensic records:

`C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN`

and cannot reconstruct the normalized request, operator decision, exact thread/turn/cwd relation or command grammar from existing stored diagnostics.

`RESPONSE_UNKNOWN` must not be re-sent or reinterpreted. No continuation may answer the old Turn-3 approval request again.

Before any same-thread continuation can be considered, a zero-real-effect retained-thread forensic must establish the durable terminal state of Run-1 Turn 3 from already existing local persistence only.

## Required retained Turn-3 forensic

The next executable action is proof-only and performs **zero Codex RPCs**.

It must use the root-only retained raw thread identity locally to locate the exact target session/rollout artifact and classify the latest Run-1 Turn-3 records without exposing raw thread/turn IDs, prompts, responses, approval command, marker or content.

It must determine whether Turn 3 has a durable terminal record and whether any approval/command item remains structurally pending.

Required finite classifications include:

- exact target session artifact count and scan errors;
- latest target turn identity as SHA-256 only;
- `TURN3_TERMINAL_PERSISTED=YES|NO|AMBIGUOUS`;
- terminal class `COMPLETED|FAILED|INTERRUPTED|CANCELLED|OTHER|NONE|AMBIGUOUS`;
- approval request persisted `YES|NO|AMBIGUOUS`;
- approval decision/response persisted `ALLOW|DENY|UNKNOWN|NONE|AMBIGUOUS`;
- command/tool item state `NONE|CREATED|PENDING_APPROVAL|RUNNING|COMPLETED|FAILED|OTHER|AMBIGUOUS`;
- any C6-owned delayed process or sentinel state by safe metadata only.

No app-server startup, resume, turn, approval, interrupt, delete, read or list is allowed for this forensic.

## Continuation authority

Current authority:

`P7C6_CONTINUATION_AUTHORIZED=NO`

A same-thread recovery continuation may be considered only if the retained Turn-3 forensic independently proves a safe finite boundary: no unresolved/pending Turn-3 approval or command effect and a terminal prior turn state compatible with starting a new bounded recovery turn.

Even then, continuation must use a repaired gated harness with:

- a real durable one-shot/recovery continuation latch;
- the historical structural approval matcher or an equally strict proven equivalent;
- no resend/retry of the old approval request;
- no new real thread;
- no `thread/read` or `thread/list`;
- the original still-unused single official `thread/delete` budget.

If retained Turn-3 state is ambiguous or still pending, no same-thread continuation is authorized and the architect must choose a different recovery/disposition path.

## Production classification

No P1.7, P1.8, P1.9, C3, C4 or C5 production defect is established by Run 1.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

P7.C6 remains **NOT ACCEPTED**.

P8 and P9 remain blocked.
