# P7.C7 consumed real DENY-only approval probe zero-effect forensic contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / FORENSIC ONLY / NO RERUN**

## Purpose

Reconstruct the exact stage reached by the already-consumed one-shot P7.C7 DENY-only approval probe using retained durable evidence only.

This contract authorizes no new Codex/app-server operation.

## Frozen source/evidence authorities

- Executed HEAD: `320ae3ba1265608a92ebfe82992068d4b12ebcd9`.
- Executed tree: `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.
- Harness blob: `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.
- Real evidence commit: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- Global latch SHA-256: `e02653fc71e3f6e579613858b812fb39d8a1ccb4205cd4fa3b3afd55987b70e0`.
- Parent outcome SHA-256: `78d590379167197c548ad5b8abed461d97da10721b9cc3b870d0e57ddfa7dd45`.

## Absolute zero-effect boundary

Forbidden:

- starting Codex or app-server;
- model/list;
- thread/start/resume/read/list/delete;
- turn/start/interrupt;
- approval response;
- Telegram;
- process signalling;
- rerun of the probe parent or child;
- mutation of `/root/.codex_second`;
- mutation of any P7.C7 run root;
- deletion/rename/truncation/chmod/chown of latch/result/outcome/journal/wire/session/log evidence;
- SQLite migration/checkpoint/VACUUM/write transaction;
- reuse or mutation of P7.C6 state.

## Run-root discovery

Locate `/tmp/codexcontrol-p7c7-parent-*` candidates read-only.

Do not select by newest timestamp alone. For each candidate inspect only safe metadata and child-root structure. The authoritative retained candidate must be uniquely correlated to the consumed run using the exact expected run layout and source/recovery authority.

Report raw parent/run basenames only as SHA-256, never as plaintext in Git evidence.

If unique attribution cannot be established, classify `P7C7_FORENSIC_RUN_ROOT_NOT_UNIQUELY_ESTABLISHED` and stop interpretation without guessing.

## Global authority verification

Read-only verify latch and parent outcome metadata/hashes. The normal result is expected absent from published evidence; if current state differs, record drift and do not modify it.

No global authority may be recreated.

## Recovery journal

The retained run's `probe-recovery.json` is primary chronology authority.

Read it with bounded no-follow stable-identity semantics. It is JSONL, not ordinary single-object JSON.

Validate every record against the accepted harness's finite safe journal schema. Do not print raw complete journal lines.

Publish only sanitized event names, finite result/status/class values, bounded counts and SHA fields already safe by schema.

Reconstruct ordered durable milestones including, where present:

- `SOURCE_GATE`;
- `GLOBAL_LATCH_RESERVED`;
- `RUNTIME_ACQUIRE_INTENT/RESULT`;
- `MODEL_LIST_WIRE_DISPATCH_INTENT/RESULT`;
- `MODEL_CATALOG_RESULT`;
- `THREAD_START_WIRE_DISPATCH_INTENT/RESULT`;
- `THREAD_START_ADAPTER_RESULT`;
- `TURN_START_WIRE_DISPATCH_INTENT/RESULT`;
- `TURN_START_ADAPTER_RESULT`;
- `TURN_ID_AUTHORITY`;
- `APPROVAL_OBSERVER_ARMED`;
- `APPROVAL_REQUEST_N_OBSERVED`;
- `DENY_RESPONSE_N_DISPATCH_INTENT/RESULT`;
- `TERMINAL_OBSERVATION_RESULT`;
- `REQUEST_LIMIT_RESULT`;
- `OWNER_NONCONVERGED`;
- `RUNTIME_SHUTDOWN_INTENT/RESULT`;
- `BOUNDARY_PROOF_RESULT`;
- `CHILD_RESULT_WRITE_INTENT/RESULT`.

For each stage distinguish:

`NOT_RECORDED`

`INTENT_RECORDED`

`RESULT_RECORDED`.

Intent never equals completion.

Record `JOURNAL_LAST_DURABLE_MILESTONE`.

## Wire-command authority

If `wire-command-recovery.json` exists, it may contain raw wire command plaintext. Read it locally only through the accepted root-only authority validator.

Never publish plaintext.

Publish only:

- presence;
- safe metadata/hash;
- request kind;
- local sequence;
- wire command SHA-256;
- recovered vector length/class if exact round-trip succeeds;
- token classes/hashes only where useful;
- sentinel reference class;
- thread/Turn/cwd hash consistency against any independently reconstructed identities.

If absent, record absence only. Absence does not prove no approval request unless journal/order evidence proves the run stopped before approval observation.

## Isolated runtime evidence

Inspect retained run `state-parent/p7c7-isolated-state/sqlite` and `logs` read-only.

Do not mutate SQLite. No migration/checkpoint/VACUUM.

Where logs permit safe exact parsing, report method counts for:

- model/list;
- thread/start;
- turn/start;
- approval responses;
- thread/resume;
- turn/interrupt;
- thread/delete;
- thread/read;
- thread/list.

If format does not safely support exact counts, use `NOT_ESTABLISHED`.

Do not publish raw protocol log lines.

## Persistent-session offline correlation

Do not use app-server `thread/read` or `thread/list`.

Use filesystem evidence only under the persistent authenticated home.

The fresh run-owned workdir and sentinel path are known locally from the unique retained run root. They may be used only in memory as correlation needles.

Search boundedly for exact target session artifacts referencing the fresh workdir/sentinel/prompt authority.

Never publish raw path, thread ID, Turn ID, prompt, response or session content.

If exactly one persistent target session is established, publish only:

- artifact count;
- scan errors/limit state;
- fresh thread ID SHA-256;
- structural turn-start count;
- structural Turn ID SHA-256 for the fresh probe turn if established;
- terminal status if structurally established;
- command item count/hash only;
- approval request/decision/response structural counts where directly represented.

If correlation is ambiguous, do not invent a fresh thread disposition.

## Sentinel/workdir physical state

Inspect read-only:

- fresh workdir;
- run-owned sentinel;
- unexpected run-root siblings.

Report only safe structural facts:

- workdir empty/nonempty and entry count;
- sentinel absent or exact-safe zero-length touch or unsafe/unexpected;
- hashes of basenames if needed;
- no raw paths.

Physical state is corroboration, not proof of RPC completion by itself.

## Current process state

Read-only `/proc` inspection may establish whether any active process still references the retained P7.C7 root/controller/workdir.

Do not signal any process.

Report counts only.

## Last durable stage

Choose exactly one from:

`GLOBAL_LATCH_RESERVED`

`RUNTIME_ACQUIRE_INTENT`

`RUNTIME_ACQUIRE_CONFIRMED`

`MODEL_LIST_DISPATCHED_STATUS_UNKNOWN`

`MODEL_LIST_RETURNED`

`MODEL_CATALOG_CONFIRMED`

`THREAD_START_DISPATCHED_STATUS_UNKNOWN`

`THREAD_START_RETURNED`

`THREAD_START_CONFIRMED`

`TURN_START_DISPATCHED_STATUS_UNKNOWN`

`TURN_START_RETURNED`

`TURN_START_CONFIRMED`

`TURN_ID_AUTHORITY_ESTABLISHED`

`APPROVAL_OBSERVER_ARMED`

`APPROVAL_REQUEST_OBSERVED`

`DENY_RESPONSE_DISPATCHED_STATUS_UNKNOWN`

`DENY_RESPONSE_CONFIRMED`

`TERMINAL_OBSERVATION_RECORDED`

`OWNER_NONCONVERGED`

`RUNTIME_SHUTDOWN_DISPATCHED_STATUS_UNKNOWN`

`RUNTIME_SHUTDOWN_CONFIRMED`

`BOUNDARY_PROOF_RECORDED`

`CHILD_RESULT_WRITE_DISPATCHED_STATUS_UNKNOWN`

`CHILD_RESULT_WRITE_CONFIRMED`

`UNKNOWN_NOT_ESTABLISHED`.

Use the latest directly supported durable milestone only.

## Failure class

Choose exactly one if proven:

`PRE_RUNTIME_LOCAL_FAILURE`

`RUNTIME_ACQUIRE_FAILURE`

`MODEL_LIST_FAILURE`

`MODEL_CATALOG_FAILURE`

`THREAD_START_FAILURE`

`TURN_START_FAILURE`

`APPROVAL_OBSERVATION_FAILURE`

`DENY_RESPONSE_FAILURE_OR_AMBIGUITY`

`OWNER_NONCONVERGENCE`

`RUNTIME_SHUTDOWN_FAILURE`

`BOUNDARY_FAILURE`

`CHILD_RESULT_BUILD_FAILURE`

`CHILD_RESULT_WRITE_FAILURE`

`HARNESS_FAILURE`

`ENVIRONMENT_OR_PRECONDITION_FAILURE`

`PRODUCTION_DEFECT`

`UNKNOWN_NOT_ESTABLISHED`.

Set `PRODUCTION_DEFECT_ESTABLISHED=YES` only if direct evidence shows accepted production code violated a frozen production contract. A harness/precondition/timeout/evidence defect remains `NO`.

## Fresh thread disposition

Choose exactly one:

`NO_FRESH_THREAD_PROVED`

`FRESH_THREAD_START_DISPATCHED_STATUS_UNKNOWN`

`FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`UNKNOWN_NOT_ESTABLISHED`.

A confirmed fresh thread remains evidence-only. No resume/delete/read/list is authorized.

## Approval/wire disposition

Choose exactly one:

`APPROVAL_NOT_REACHED_PROVED`

`APPROVAL_OBSERVER_ARMED_NO_REQUEST_PROVED`

`APPROVAL_REQUEST_OBSERVED_DENY_STATUS_UNKNOWN`

`APPROVAL_REQUEST_OBSERVED_DENIED`

`WIRE_AUTHORITY_CAPTURED`

`UNKNOWN_NOT_ESTABLISHED`.

Do not authorize an ALLOW matcher from forensic evidence automatically.

## Repository publication

Publish only one sanitized forensic evidence file on a new branch from then-current `origin/main`:

`docs/evidence/p7c7/P7C7_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_EVIDENCE_2026-09-11.md`

No `src/**`, tests, CURRENT_WORK, ROADMAP or ADR changes on the executor forensic branch.

## Final binding state

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
