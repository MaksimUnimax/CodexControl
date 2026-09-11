# P7.C6 consumed one-shot real continuation forensic contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / READ-ONLY FORENSIC ONLY**

## Purpose

Recover the last durably established stage of the already-consumed P7.C6 real continuation and classify what is known, unknown and impossible to infer without issuing any further Codex provider/lifecycle operation.

This is not a retry, repair or second acceptance run.

## Absolute prohibitions

Do not start Codex/app-server. Do not issue `model/list`, `thread/start`, `thread/resume`, `turn/start`, approval responses, `turn/interrupt`, `thread/delete`, `thread/read`, `thread/list` or Telegram calls. Do not signal unrelated processes. Do not mutate persistent session/history, isolated state, controller DB, continuation latch, recovery journal, marker supplement or process-result path. Do not create a second continuation latch/result. Do not remove forensic workdirs/sentinels. Do not use SQLite write pragmas, migration, checkpoint, vacuum or repair.

The one-shot real invocation is consumed forever.

## Binding authorities

Accepted execution source:

- commit `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`
- tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`

Retained thread SHA-256:

`9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`

Run-1 latch SHA-256:

`50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`

Consumed continuation latch SHA-256:

`fc1f428502b494566ee624f0f9b2ef8490cfd05a11532210a9ef07b09c8c9d7e`

Reported continuation recovery journal SHA-256:

`3564157f6c54ba8dfff673fb26ddceab78c5278e771a7b8afc449774bdc68a1a`

Reported continuation marker recovery record SHA-256:

`a615f475080c97ec76f4e4ad79f808de46439003585bbfe69990e3ab811d8b9d`

Retained recovery root:

`/tmp/codexcontrol-p7c6-nz2ubdeh`

## Required evidence layers

### A. Immutable file authority

Verify without modification:

- Run-1 latch path, owner/mode/nlink/size/SHA-256;
- continuation latch path, owner/mode/nlink/size/SHA-256;
- process-result path present/absent;
- exactly one new continuation recovery journal matching `p7c6-continuation-result-recovery-*.json`;
- exactly one new continuation marker supplement matching `p7c6-continuation-marker-recovery-supplement-*.json`;
- their owner/mode/nlink/size/SHA-256;
- retained isolated root/controller/session authorities.

No raw protected values may be published.

### B. Recovery journal safe read

Read the exact root-only journal locally through bounded no-follow descriptor handling. Raw values may be used transiently for matching but must not be printed or committed.

Extract only finite safe fields when present, including:

- `status`
- `failure_stage`
- accepted source SHA/tree
- retained-thread SHA-256
- model-list dispatch intent/result/call count
- resume dispatch intent/result/status
- Turn-4 start intent/result/status
- bridge armed state
- approval request count/kind, identity-match booleans, grammar class, mismatch flags, operator decision, handling status, approval response count
- Turn-4 terminal status/sentinel proof
- Turn-5 start intent/result/status
- Turn-5 active-before-interrupt proof
- interrupt dispatch/result/status
- Turn-5 terminal status
- runtime-acquire counts before/after interrupt and no-reacquire classification
- pre-delete scan/oracle counts/errors/limits
- controller safe state fields
- delete dispatch intent/result, official delete call count/status, application delete status
- post-delete scan/oracle/isolation/baseline/live/tombstone safe fields
- owned-task states limited to name/phase/terminalized/nonconverged
- any final sanitization status.

Do not publish raw thread/turn/request IDs, markers, commands, prompts, responses or environment values.

Establish the highest **durable journal milestone**. Intent and result are distinct; an intent is not proof of completion.

### C. Controller SQLite read-only forensic

Inspect the retained controller database strictly read-only. Hash/stat DB/WAL/SHM before and after and require no content/size/hash drift caused by the forensic.

Do not use application open paths that can migrate/write. Use a SQLite read-only URI or equivalent read-only mechanism.

Determine safely:

- actual `PRAGMA user_version`;
- whether synthetic dialogue `p7c6-retained-dialogue` exists;
- its safe lifecycle state/version if present;
- if a stored thread binding exists, hash it locally and report only whether its SHA-256 equals the retained-thread authority;
- whether a deletion tombstone exists for that dialogue and its finite status fields if any;
- whether delete containment / confirmed-pending storage authority exists and its finite status, never raw thread ID;
- callback/turn-job/error counts for the synthetic dialogue where schema supports them.

Do not infer official P1.9 delete status merely from controller/tombstone/storage state.

### D. Exact retained target-session offline forensic

Use the raw retained thread ID only locally, recovered from the already-existing Run-1 recovery authority, and prove its SHA-256 equals the accepted retained-thread hash.

Search only the exact target session/history evidence necessary to identify the retained thread. Do not dump conversation content.

Report structural facts only:

- target session artifact count and scan errors;
- total structural turn-start count;
- total terminal count and finite terminal status distribution;
- whether new turns beyond historical Run-1 Turn 1/2/3 are structurally present;
- for any continuation-era turn, safe ordinal/order, hashed turn identity, terminal status, command/tool-item count and hashed command identity only;
- persisted approval request/decision/response structural counts only;
- whether Turn-4/Turn-5 prompt/marker hashes are present, using marker plaintext only locally;
- never quote user/model/tool text.

Historical Run-1 baseline was three turns. Any count beyond that must be proved structurally, not inferred from timestamps.

### E. Continuation marker and physical residual forensic

Read the continuation marker supplement locally and verify marker SHA fields. Never publish marker plaintext.

Using accepted bounded/no-follow scanner logic, count target-thread and marker residuals separately across:

- persistent `/root/.codex_second/sessions/**`;
- optional persistent `history.jsonl`;
- retained isolated `sqlite/**`;
- retained isolated `logs/**`.

Report only counts/errors/limit flags and marker SHA references.

Residual absence/presence is physical storage evidence only. It is not proof of official delete status.

### F. Isolated logs / protocol metadata

If the retained isolated logs contain usable protocol metadata, inspect them read-only and extract only sanitized method/status counts. Do not quote raw lines containing content or IDs.

Allowed method-level evidence includes finite counts for:

- `model/list`
- `thread/resume`
- `turn/start`
- approval response wire action
- `turn/interrupt`
- `thread/delete`
- `thread/read`
- `thread/list`.

Any log evidence must be cross-checked against the journal and target-session/controller evidence. Conflicts remain conflicts; do not reconcile them by guess.

### G. Process / forensic-path state

Prove current continuation process group has zero active members and inspect whether any process references the retained isolated/controller/workdir forensic paths. Do not signal anything.

Record remaining continuation workdir/sentinel existence, owner/mode/size/hash only. Never inspect/print sentinel plaintext unless it is already sanctioned marker data; publish hashes only.

## Classification rules

Produce a finite `LAST_DURABLY_ESTABLISHED_STAGE` from the strongest direct evidence, one of:

- `PRE_RPC_ONLY`
- `MODEL_LIST_DISPATCHED`
- `MODEL_LIST_COMPLETED`
- `RESUME_DISPATCHED_STATUS_UNKNOWN`
- `RESUME_CONFIRMED`
- `TURN4_START_DISPATCHED_STATUS_UNKNOWN`
- `TURN4_START_CONFIRMED`
- `TURN4_APPROVAL_REQUEST_OBSERVED`
- `TURN4_APPROVAL_RESPONSE_DISPATCHED_STATUS_UNKNOWN`
- `TURN4_APPROVAL_ALLOWED`
- `TURN4_COMPLETED_SENTINEL_PROVED`
- `TURN5_START_DISPATCHED_STATUS_UNKNOWN`
- `TURN5_START_CONFIRMED`
- `INTERRUPT_DISPATCHED_STATUS_UNKNOWN`
- `INTERRUPT_CONFIRMED_OR_RECONCILED`
- `TURN5_FAILED_TERMINAL_PROVED`
- `PREDELETE_PROOF_COMPLETE`
- `DELETE_DISPATCHED_STATUS_UNKNOWN`
- `DELETE_CONFIRMED_APPLICATION_PENDING_OR_LATER`
- `APPLICATION_DELETED_POSTDELETE_PENDING_OR_LATER`
- `POSTDELETE_GATES_COMPLETE`
- `SANITIZATION_FAILED_AFTER_CONFIRMED_DELETE`
- `UNKNOWN_NOT_ESTABLISHED`.

Choose only a stage directly supported by durable evidence.

Separately classify:

`OFFICIAL_P1_DELETE_CLASS` as exactly one of:

- `NOT_DISPATCHED_PROVED`
- `DISPATCHED_STATUS_UNKNOWN`
- `DELETE_CONFIRMED`
- `DELETE_UNKNOWN`
- `UNKNOWN_NOT_ESTABLISHED`.

`NOT_DISPATCHED_PROVED` requires positive durable proof that execution terminated before delete dispatch, not mere absence of a tombstone/result.

Classify production defect only if direct evidence shows accepted production code violated its frozen semantics. A harness/local-environment/precondition failure is not a production defect.

## Repository publication

After forensic completion, create an evidence-only branch from the then-current `origin/main` and add only:

`docs/evidence/p7c6/P7C6_CONSUMED_REAL_CONTINUATION_FORENSIC_EVIDENCE_2026-09-11.md`

No source/harness/config/ADR/CURRENT_WORK/ROADMAP changes in the executor branch.

Evidence must be sanitized and contain no raw IDs/markers/prompts/commands/responses/secrets.

## Final authority

No rerun is authorized under any forensic outcome.

P8/P9 remain blocked pending architect review.
