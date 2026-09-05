# P2.4a turn jobs and transient payloads evidence

Date: 2026-09-05

## Authority and base

- Base SHA: 02be2fb3c3e2fb6f1895ca21f6a469d0c5d20790
- Branch: impl-p2-4a-turn-jobs-payloads-2026-09-05
- Issue: #14
- Binding ADR: ADR-0021
- Accepted P2.1 head: 61301fd25ff7253693f367664ce99e13dfc88446
- Accepted P2.2 head: 5187c080a7188a59989013defe7d07075662d007
- Accepted P2.3 head: 0d8f34beaa35a2bc02b349abba9507ebb9bc3802
- Schema-v1 DDL SHA-256: b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c

Issue #14 was read through the GitHub issue API. It had zero comments at implementation time.

## Production implementation

- src/codex_control/storage/turn_job_records.py
- src/codex_control/storage/turn_job_repositories.py
- src/codex_control/storage/transient_payloads.py
- src/codex_control/storage/__init__.py (exports only)

No schema, SQLite kernel, accepted P2.2/P2.3 production file, P1 code, application layer, delivery, approval, retention, interrupt/delete, Telegram, Codex, or deployment file was changed.

## Records, enums, and public surfaces

TurnJobState materializes exactly all 11 schema-v1 job states. P2.4a writes only RECEIVED, CLAIMED, CODEX_STARTING, CODEX_RUNNING, CODEX_COMPLETED, FAILED, and UNKNOWN.

TurnIngressClaimStatus is exactly CREATED / DUPLICATE.
TurnTerminalOutcome is exactly COMPLETED / FAILED / UNKNOWN.
TransientPayloadKind is exactly INPUT / OUTPUT / APPROVAL / DISPLAY.

TurnJobRepository exposes exactly get, claim_ingress, claim_turn, mark_codex_starting, mark_codex_running, and finish_codex.
TransientPayloadRepository exposes exactly get, get_input_for_job, and create.
No delete, purge, cleanup, retention, retry, requeue, delivery, approval-decision, interrupt, or generic transition API was added.

Records are frozen dataclasses. Job records contain identifiers, immutable snapshots, hashes, state/version/timestamps and sanitized error class only. Payload content is exact bytes and repr=False.

## Atomic ingress and input persistence

claim_ingress validates all static arguments before SQL and performs duplicate lookup first. A new claim atomically writes one turn_jobs(RECEIVED, version=0), one INPUT transient BLOB, and terminal ingress_updates(JOB:<job_id>), using one timestamp and one transaction. SHA-256 and byte length are computed internally. Failure rolls all three writes back.

Covered proofs include new ingress, duplicate JOB reconstruction, duplicate non-JOB no-reclassification, job/payload ID collisions, CREATING and IDLE dialogue paths, exact server/profile/thread authority, no second outstanding RECEIVED job, same/different update concurrency, clock failure rollback, restart duplicate authority, and accepted storage cancellation ownership.

## Turn execution claims

claim_turn atomically performs RECEIVED -> CLAIMED and IDLE -> TURN_RUNNING, binds the immutable thread once, checks both expected versions, validates server/profile/thread identity, and verifies durable JOB:<id> ingress plus exactly one coherent INPUT payload.

mark_codex_starting durably commits CLAIMED -> CODEX_STARTING before any future external turn/start effect.
mark_codex_running binds a non-empty bounded Codex turn ID exactly once and performs CODEX_STARTING -> CODEX_RUNNING.

## Terminal capture

finish_codex atomically captures:

- COMPLETED: job CODEX_COMPLETED, dialogue IDLE, cleared error classes;
- FAILED: job FAILED, dialogue ERROR, shared sanitized error class;
- UNKNOWN: job UNKNOWN, dialogue TURN_UNKNOWN, shared sanitized error class.

COMPLETED requires CODEX_RUNNING; FAILED and UNKNOWN accept CODEX_STARTING or CODEX_RUNNING. Expected-version and state conflict precedence is enforced before the mutation clock.

An optional all-or-none OUTPUT bundle is inserted in the same transaction, linked to the exact dialogue/job, with internally computed SHA-256 and byte length. Output collision, expiry, clock, insert, and subsequent update failures roll back the complete terminal transaction. Restart persistence of terminal state and output was tested.

## Transient payloads

The repository ceiling is exactly 8,388,608 bytes. It accepts exact immutable bytes of length 1 through the ceiling and rejects empty, oversized, bytearray, memoryview, str, and None content without coercion.

Generic creation accepts only OUTPUT, APPROVAL, and DISPLAY, requires at least one canonical owner, validates owner agreement, rejects INPUT creation, computes hash/length internally, and is insert-only. get_input_for_job requires exactly one coherent INPUT payload and verifies owner, kind, job hash, actual hash, and byte length.

Schema-valid corruption proofs cover noncanonical job hash/error/version values, payload hash/content mismatch, and redacted invariant errors. Sentinel payload bytes do not occur in record repr or repository errors.

## Tests and validation

Focused P2.4a:

- unit: 8
- integration: 22

Accepted prior-slice counts:

- P2.1: 8 unit / 31 integration
- P2.2: 6 unit / 20 integration
- P2.3: 7 unit / 28 integration
- P1.10: 6 / 1 / 4

Full-suite arithmetic:

BASE_ACCEPTED_FULL_TESTS=348
EXPECTED_FULL_TESTS=348 + 8 + 22 = 378
OBSERVED_FULL_TESTS=378

The full suite passed. The P1.6 pending-task warning was not observed; no P2.4a warning was introduced.

Commands also passed:

- mandated P2.4a focused unit/integration modules;
- mandated P2.3, P2.2, and P2.1 regressions;
- P1.10 T0/T1/T2;
- all named P1 focus suites;
- PYTHONPATH=src python3 -m compileall -q src tests;
- public import check;
- git diff --check;
- DDL SHA verification;
- changed-file secret/security scan.

## Production effects

All tests used temporary SQLite directories. No production DB or state root was opened or touched, no auth.json or secrets file was read, no real Codex or Telegram call was made, no service was changed, and no runtime dependency was added.

This is implementation evidence only and does not claim architect acceptance.
