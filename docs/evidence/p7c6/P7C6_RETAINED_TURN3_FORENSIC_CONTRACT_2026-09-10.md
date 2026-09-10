# P7.C6 retained Turn-3 forensic contract — 2026-09-10

Status: **FROZEN / ZERO-REAL-EFFECT / NEXT**

This contract follows the rejected P7.C6 Run 1 recorded at `785a82e2e9bc392173ea1e910b490f84cfa590b2` and architect review `docs/evidence/p7c6/P7C6_RUN1_ARCHITECT_REVIEW_2026-09-10.md`.

## Goal

Establish the durable local state of the retained Run-1 Turn 3 after the approval gate returned `RESPONSE_UNKNOWN`, without starting Codex or making any business RPC.

This is not a C6 rerun and not a same-thread continuation.

## Absolute zero-effect boundary

The forensic must perform zero:

- Codex process/app-server starts;
- `model/list`;
- `thread/start`;
- `thread/resume`;
- `turn/start`;
- approval responses;
- `turn/interrupt`;
- `thread/delete`;
- `thread/read`;
- `thread/list`;
- Telegram calls;
- unrelated process signals/termination;
- persistent-home mutation;
- isolated-root/controller mutation except ordinary read-only filesystem metadata access.

Do not set any real-run authorization environment variable.

## Local retained authority

The exact raw target thread ID may be read only from the root-owned retained recovery ledger and used only in process memory to identify the exact persisted target artifact.

Never print, log or commit the raw thread ID.

Git evidence stores only SHA-256 identities and finite structural classifications.

The recovery ledger itself must not be modified, moved or committed.

## Allowed sources

Use existing local state only:

- the retained root-only recovery ledger;
- the exact target `CODEX_HOME=/root/.codex_second` session/rollout artifact located by retained thread ID;
- existing Run-1 isolated logs/state if still present;
- filesystem/process metadata under `/proc` for C6-owned delayed-process classification;
- repository source and historical real-P7 parsing precedent.

Do not use network APIs or Codex RPCs.

## Session parsing rules

Read only the exact target session/rollout artifact identified by retained thread identity. Do not dump raw file content.

Parse records structurally. Record only:

- safe record ordinal/order;
- normalized record class;
- item class/state;
- whether approval-related;
- whether terminal-related;
- presence/absence of timestamp;
- SHA-256 of opaque IDs/status strings when a finite enum cannot be safely named.

Do not persist prompt, response, command, marker, matched line, raw path beyond a safe category, raw turn ID or raw item/request ID.

## Turn-3 identity

Identify Run-1 Turn 3 structurally from the single target thread history:

- Turn 1 and Turn 2 were already definitively completed by Run-1 acceptance assertions;
- the next unique started turn is the Run-1 Turn 3 under review.

If multiple candidates or ordering ambiguity exists, report `TURN3_IDENTITY=AMBIGUOUS` and stop classification there.

Store only `TURN3_ID_SHA256`.

## Required state classification

For the exact Run-1 Turn 3 determine:

`TURN3_TERMINAL_PERSISTED=YES|NO|AMBIGUOUS`

If terminal exists:

`TURN3_TERMINAL_CLASS=COMPLETED|FAILED|INTERRUPTED|CANCELLED|OTHER|AMBIGUOUS`

If no terminal:

`TURN3_TERMINAL_CLASS=NONE`

Determine:

`TURN3_APPROVAL_REQUEST_PERSISTED=YES|NO|AMBIGUOUS`

`TURN3_APPROVAL_DECISION_PERSISTED=ALLOW|DENY|UNKNOWN|NONE|AMBIGUOUS`

`TURN3_APPROVAL_RESPONSE_PERSISTED=YES|NO|AMBIGUOUS`

Determine latest relevant command/tool item state:

`TURN3_COMMAND_ITEM_STATE=NONE|CREATED|PENDING_APPROVAL|RUNNING|COMPLETED|FAILED|OTHER|AMBIGUOUS`

Also report counts:

- command item count;
- approval-related record count;
- terminal-related record count.

## Approval command forensic

If the normalized approval command can be reconstructed from the already persisted target session record without exposing content, classify it against the historical safe grammar:

`EXACT_INNER|ONE_SHELL_WRAPPER|OTHER|UNAVAILABLE`

The accepted historical grammar is exactly:

- expected inner safe command token sequence; or
- one wrapper from `sh`, `/bin/sh`, `/usr/bin/sh`, `bash`, `/bin/bash`, `/usr/bin/bash`;
- wrapper option exactly `-c` or `-lc`;
- inner script token sequence exactly equal to the expected bounded inner command;
- no extra wrapper, prefix, suffix, pipeline, substitution or additional operation.

Record only `OBSERVED_APPROVAL_COMMAND_SHA256` and finite mismatch classes. Never commit the raw command.

This forensic classification does not retroactively authorize ALLOW and must not answer the old approval request.

## Delayed process/sentinel state

Use read-only process inspection to determine whether an exact Run-1 C6-owned delayed shell/sleep process remains attributable by known run-owned workdir/sentinel metadata.

Do not signal it.

Report:

`C6_RUN1_DELAYED_PROCESS_PRESENT=YES|NO|AMBIGUOUS`

`C6_RUN1_SENTINEL_PRESENT=YES|NO|AMBIGUOUS`

If an owned delayed process is still present, same-thread continuation remains blocked regardless of turn-record classification.

## Safe continuation classification

The forensic itself never authorizes continuation. It only returns one of:

`RETAINED_TURN3_STATE=TERMINAL_SAFE_FOR_ARCHITECT_REVIEW`

when all are true:

- exact Turn 3 identity is unambiguous;
- a durable terminal record is present;
- no command item remains pending/running/ambiguous;
- no approval request remains structurally pending/ambiguous;
- no attributable delayed process remains;
- sentinel is absent or safely terminal according to recorded operation semantics.

Otherwise return one of:

- `RETAINED_TURN3_STATE=NONTERMINAL_OR_PENDING`;
- `RETAINED_TURN3_STATE=AMBIGUOUS`;
- `RETAINED_TURN3_STATE=INSUFFICIENT_EVIDENCE`.

Only a later architect authority may authorize any same-thread continuation.

## Repository output

Add sanitized forensic evidence only under:

`docs/evidence/p7c6/`

Suggested file:

`P7C6_RETAINED_TURN3_FORENSIC_EVIDENCE_2026-09-10.md`

No production source change. No harness repair yet. No roadmap/current-work edits by executor.

## Tests

No real test may execute.

Ordinary static/parser/helper tests may be added only if necessary under `tests/**` and must be inert with respect to Codex.

Run `git diff --check` and ordinary regression only with all real-run gates unset.

## Final consequence

P7.C6 remains NOT ACCEPTED. P8/P9 remain blocked. The retained thread must not be resumed, interrupted, deleted, read or listed by RPC during this forensic.
