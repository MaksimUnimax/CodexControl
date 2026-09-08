# P2.C2 rejected ingress schema-v2 implementation evidence

Status: implementation evidence only; no architect acceptance is claimed.

## Authority and scope

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `111936f38fdeff1547f6585a70415ab5d0c26b0c`
- Branch: `impl-p2-c2-rejected-ingress-schema-v2-2026-09-07`
- Issue: #32
- Binding authority: ADR-0036 (`docs/adr/0036-terminal-rejected-ingress-schema-v2.md`)
- Correction reason: accepted pre-JOB BUSY/BLOCKED results had no durable terminal classification, so replay after state changes could later execute the update.
- Scope stayed limited to storage schema/migration, rejected ingress materialization/claim/retention compatibility, narrow expectation updates, and these tests/evidence.

## Historical schema-v1 preservation

- Historical version: `1`
- Historical migration ID: `0001_initial_state`
- Historical DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- `SCHEMA_V1_STATEMENTS`, `SCHEMA_V1_CANONICAL_SQL`, and the historical hash remain unchanged in meaning and value.
- A direct AST comparison of the v1 statement tuple against the architect base passed (`V1_IMMUTABILITY_PASS`).

## Schema-v2 migration authority

- Current schema version: `2`
- Migration ID: `0002_ingress_rejected_disposition`
- Migration-statement SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`
- The canonical four operations, in order, are:
  1. `ALTER TABLE ingress_updates RENAME TO ingress_updates_v1;`
  2. Create the same `ingress_updates` columns with the CHECK widened only by exact `IGNORED_REJECTED`.
  3. Copy `update_id`, `received_at_ms`, `completed_at_ms`, and `disposition` from `ingress_updates_v1`.
  4. `DROP TABLE ingress_updates_v1;`
- The unit proof recomputes the canonical tuple hash and requires the exact architect value.
- Final v2 table/index sets equal v1; there are no views, triggers, backup tables, new tables, columns, indexes, FKs, or other object changes.

## v0/v1/v2 open behavior and ledger

- v0 requires no user objects, bootstraps accepted v1, validates v1, migrates v2, validates v2, and returns with `PRAGMA user_version = 2`.
- Fresh v0 bootstrap consumed exactly two migration-clock calls: one v1 call and one v2 call.
- v1 is validated before any v2 mutation or v2 clock call; valid v1 then migrates once.
- v2 validates directly, performs no migration and no migration-clock call.
- Other versions are `SCHEMA_UNSUPPORTED`.
- Successful v2 ledger has exactly two rows: the unchanged v1 row and the exact v2 ID/hash row. The v1 timestamp is not replaced or retimestamped.

## Migration rollback/retry and fail-closed validation

- A populated exact v1 fixture containing CONTROL, IGNORED_SLEEP, IGNORED_UNAUTHORIZED, and JOB ingress migrated with all rows preserved in ordered `(update_id, received_at_ms, completed_at_ms, disposition)` form.
- The coherent `JOB:job-1` relation remained associated with the same job.
- Invalid v2 migration clock after the four DDL operations caused rollback to user version 1, restored the historical ingress table, left no `ingress_updates_v1`, left no v2 ledger row, and left the exact single v1 ledger row. A later valid open migrated successfully.
- Malformed v1 cases (wrong v1 hash, missing ledger row, missing historical index, extra table, and unrelated SQL drift) failed `SCHEMA_INVALID` before a v2 clock call and created no backup object.
- Forged v2 cases failed `SCHEMA_INVALID`: old v1 ingress SQL, missing v2 row, wrong v2 hash, extra `ingress_updates_v1`, unrelated index SQL drift, and a persisted invalid disposition using SQLite's isolated `ignore_check_constraints` fixture.
- v2 validation checks exact object SQL, exact two-row ledger identity/timestamps, and a bounded persisted-disposition validity probe.

## IGNORED_REJECTED contract

- Exact enum order is `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, `IGNORED_REJECTED`, `JOB`.
- Exact persisted `IGNORED_REJECTED` materializes as `IngressDispositionKind.IGNORED_REJECTED` with `job_id=None`.
- Fresh claim uses one owned write transaction and one validated repository clock; received and completed timestamps are equal, and no content is stored.
- Duplicate rejected claim returns the original record with `duplicate=True` and zero clock calls.
- Requests for rejected over existing CONTROL, SLEEP, UNAUTHORIZED, REJECTED, and `JOB:<same-id>` preserve each original durable record; no reclassification occurs.
- Near-miss materialization values remain `INVARIANT_VIOLATION`.
- Public repository method sets remain unchanged; only the existing `claim_ignored` accepted enum set widened.

## Metadata retention

- The standalone-ingress retention predicate now includes `IGNORED_REJECTED` with CONTROL, IGNORED_SLEEP, and IGNORED_UNAUTHORIZED.
- The existing horizon, limits, ordering, job-coupled deletion, callback/tombstone/error retention, and content policy were not changed.
- Deterministic tests prove an old rejected ingress is deleted and a fresh rejected ingress remains.

## Test and regression results

Focused P2.C2 modules:

- Unit: 5 (`tests/unit/test_rejected_ingress_schema_v2.py`)
- Integration: 9 (`tests/integration/test_rejected_ingress_schema_v2.py`)
- Acceptance: 1 (`tests/acceptance/test_p2_c2_rejected_ingress_schema_v2.py`)
- Focused P2.C2 total: 15, all passing.

The prior regression command groups all passed. Required accepted counts were preserved:

`P5.1 7/8; P4.3 7/26/1; P4.2 5/29; P4.1 8/15; P3.5 12/25/1; P3.4 6/31; P3.3 5/25; P3.2 2/21; P3.1 11/26; P2.C1 5/1; P2.6b 5/12/8/3; P2.6a 4/28; P2.5 4/18; P2.4b 6/25; P2.4a 8/31; P2.3 7/28; P2.2 6/20; P2.1 8/31; P1.9 15; P1.8 28; P1.10 6/1/4`.

- Accepted pre-P2.C2 baseline: 777
- Full formula: `777 + 5 + 9 + 1 = 792`
- Observed full discovery: 792 tests
- Full failures: 0
- Full errors: 0
- Final unittest status: `OK`

## Compile/import/diff/security/effects

- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
- Public P2.C2 import smoke: PASS (`P2_C2_IMPORT_PASS`).
- `git diff --check`: PASS.
- Changed production paths are only storage schema/kernel/idempotency/retention/package export paths. Application, Telegram adapter, and Codex production paths were not changed.
- Secret scan over changed storage and focused-test paths: PASS.
- Tests used temporary synthetic SQLite files, deterministic clocks, and isolated repository calls only.
- No Telegram, network, Codex, thread/start, turn/start, interrupt, thread/delete, approval response, delivery, production database, production state root, or service effect occurred.
- The known P1.6 pending-task warning was observed in prior accepted lifecycle/regression history; no new P2.C2 warning was introduced.

The final implementation commit SHA is reported by the executor after the single commit; this evidence file was prepared before that commit and was not subsequently amended.
