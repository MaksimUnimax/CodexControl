# P7.C9 consumed real DENY-only approval probe — zero-effect retained-run forensic contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / NO RERUN / NO APP-SERVER READ-LIST**

## Purpose

Determine the exact last durable stage reached by the permanently consumed P7.C9 real probe after state-root provision/validate and runtime acquisition were confirmed.

This is a read-only forensic task. It does not authorize a new Codex process, app-server process, RPC, approval response, signal or cleanup.

## Binding facts

- execution HEAD `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`;
- tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`;
- real evidence commit `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`;
- state-root provision `CONFIRMED/TERMINALIZED`;
- state-root validation `CONFIRMED/TERMINALIZED`;
- runtime acquire initial/final `CONFIRMED`;
- parent class `CHILD_NONZERO`, watchdog `PROCESS_COMPLETED`;
- group active=0, scan errors=0, no TERM/KILL;
- normal result absent; child result absent;
- exactly one child, zero retries.

## Absolute prohibitions

Zero new Codex effects. Do not start Codex/app-server; do not call model/list, thread/start/resume/read/list/delete, turn/start/interrupt, approval response; do not signal processes; do not mutate global P7.C9 latch/result/outcome, run root, state root, journal, wire authority, persistent session/history or P7.C7/P7.C8 retained evidence.

## Primary authority

Use the retained P7.C9 `probe-recovery.json` as primary stage chronology. Locate the unique retained run by exact source SHA/tree plus P7.C9 global latch/run structure, never timestamp alone. Read the journal boundedly, no-follow, root-only, stable identity, JSONL schema-valid.

Relevant accepted post-acquire milestones include:

- `MODEL_LIST_WIRE_DISPATCH_INTENT` / `MODEL_LIST_WIRE_RESULT`;
- `MODEL_CATALOG_RESULT` or harness `MODEL_CATALOG` result;
- `THREAD_START_WIRE_DISPATCH_INTENT` / `THREAD_START_WIRE_RESULT`;
- `THREAD_START_ADAPTER_RESULT` or `THREAD_START_ADAPTER`;
- `TURN_START_WIRE_DISPATCH_INTENT` / `TURN_START_WIRE_RESULT`;
- `TURN_START_ADAPTER_RESULT` or `TURN_START_ADAPTER`;
- `TURN_ID_AUTHORITY`;
- `APPROVAL_OBSERVER_ARMED`;
- approval-request and DENY-response events if any;
- `TERMINAL_OBSERVATION_RESULT` or `TERMINAL_OBSERVATION`;
- `OWNER_NONCONVERGED` if any;
- `RUNTIME_SHUTDOWN_INTENT` / `RUNTIME_SHUTDOWN_RESULT`;
- `BOUNDARY_PROOF_RESULT` or `BOUNDARY_PROOF`;
- `CHILD_RESULT_WRITE_INTENT` / `CHILD_RESULT_WRITE_RESULT`.

Intent is not completion. Do not advance past direct durable evidence.

## Corroborating authority

Read-only inspect:

- P7.C9 run-root filesystem;
- production-provisioned isolated `sqlite/` and `logs/` roots;
- exact structured logs only where parsable without guessing;
- persistent `/root/.codex_second` session/history filesystem using exact P7.C9 workdir/sentinel/prompt correlation needles in process memory only;
- `/proc` only to prove no current retained-root users; never signal.

Do not use app-server `thread/read` or `thread/list`.

## Required classifications

Establish the last durable stage from a finite enum, including at least:

`RUNTIME_ACQUIRE_CONFIRMED`, `MODEL_LIST_DISPATCHED_STATUS_UNKNOWN`, `MODEL_LIST_RETURNED`, `MODEL_CATALOG_CONFIRMED`, `MODEL_CATALOG_FAILURE`, `THREAD_START_DISPATCHED_STATUS_UNKNOWN`, `THREAD_START_RETURNED`, `THREAD_START_CONFIRMED`, `THREAD_START_FAILURE`, `TURN_START_DISPATCHED_STATUS_UNKNOWN`, `TURN_START_RETURNED`, `TURN_START_CONFIRMED`, `TURN_START_FAILURE`, `TURN_ID_AUTHORITY_ESTABLISHED`, `APPROVAL_OBSERVER_ARMED`, `APPROVAL_REQUEST_OBSERVED`, `DENY_RESPONSE_DISPATCHED_STATUS_UNKNOWN`, `DENY_RESPONSE_CONFIRMED`, `TERMINAL_OBSERVATION_RECORDED`, `OWNER_NONCONVERGED`, `RUNTIME_SHUTDOWN_CONFIRMED`, `BOUNDARY_PROOF_RECORDED`, `CHILD_RESULT_WRITE_DISPATCHED_STATUS_UNKNOWN`, `CHILD_RESULT_WRITE_CONFIRMED`, `UNKNOWN_NOT_ESTABLISHED`.

Classify fresh-thread disposition as exactly one of:

`NO_FRESH_THREAD_PROVED`, `FRESH_THREAD_START_DISPATCHED_STATUS_UNKNOWN`, `FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`, `UNKNOWN_NOT_ESTABLISHED`.

Classify approval disposition as exactly one of:

`APPROVAL_NOT_REACHED_PROVED`, `APPROVAL_OBSERVER_ARMED_NO_REQUEST_PROVED`, `APPROVAL_REQUEST_OBSERVED_DENY_STATUS_UNKNOWN`, `APPROVAL_REQUEST_OBSERVED_DENIED`, `WIRE_AUTHORITY_CAPTURED`, `UNKNOWN_NOT_ESTABLISHED`.

Classify failure only where directly established: model catalog, thread start, turn start, approval observation, DENY response ambiguity/failure, owner nonconvergence, runtime shutdown, boundary, child-result build/write, harness/environment, production defect, or unknown.

`PRODUCTION_DEFECT_ESTABLISHED=YES` only with direct evidence that accepted production code violated a frozen production contract. Harness/test assumptions are not production defects.

## Publication

Publish one sanitized forensic evidence Markdown file only on a new branch. No source/test/governance edits by executor. No raw thread/Turn IDs, raw commands, paths, session lines, prompt/model response, credentials/tokens or root-only JSON content in Git.

P7.C9 remains consumed regardless of forensic result. Matcher and hard delete remain unauthorized pending architect review.
