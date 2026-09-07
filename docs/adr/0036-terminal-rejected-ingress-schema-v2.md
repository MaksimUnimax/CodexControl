# ADR-0036 — P2.C2 terminal rejected prompt ingress and schema-v2

Status: Accepted
Date: 2026-09-07

## Context

P5.1 is accepted at `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3` with full suite 777. P5.2 is intended to consume authorized ordinary group TEXT: SLEEP must be terminally ignored, ACTIVE may delegate to accepted P3, and a second prompt while busy must be rejected with no queue.

Independent architect research found a durable replay gap in the existing schema-v1 vocabulary. Accepted P3.1/P3.2 returns `BUSY` and several pre-admission `BLOCKED` results before any `ingress_updates` or JOB row is created. If the same Telegram update is replayed after the blocking condition changes, P3 can later admit it. This violates the V1 rule that a busy/rejected prompt is discarded rather than delayed/replayed.

Schema-v1 `ingress_updates.disposition` supports only `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, and `JOB:<id>`. Reusing `IGNORED_SLEEP` or `CONTROL` for BUSY/BLOCKED would deliberately lie about the durable classification and is rejected.

Therefore P5.2 is gated on one narrow P2 correction.

## Decision

Insert architect correction slice **P2.C2** before P5.2.

P2.C2 owns only:

1. schema version 2 migration that widens `ingress_updates.disposition` with one new terminal non-content value `IGNORED_REJECTED`;
2. `IngressDispositionKind.IGNORED_REJECTED`;
3. accepted ingress materialization for that value;
4. `IngressUpdateRepository.claim_ignored` accepting the new value in addition to the existing sleep/unauthorized values;
5. exact migration/restart/backward-compatibility proofs and updates to frozen schema/enum expectation tests.

P2.C2 does NOT implement P5.2 routing, BUSY UI, Telegram networking, JOB creation, P3 behavior changes, delivery, or any Codex effect.

## Semantic meaning

`IGNORED_REJECTED` means:

> an authorized ordinary prompt update was terminally rejected before any JOB/external effect, for an application reason such as BUSY, blocked/not-ready state, or a fail-closed stale ordering decision.

It stores no prompt text and no reason prose. P5.2 may preserve a finite immediate application status/reason in memory, but durable duplicate replay needs only the fact that the update is terminal non-JOB and must never execute later.

It MUST NOT be used for:

- SLEEP (`IGNORED_SLEEP` remains exact);
- unauthorized (`IGNORED_UNAUTHORIZED` remains exact);
- control/private command (`CONTROL` remains exact);
- admitted work (`JOB:<id>` remains exact).

## Schema versioning

The historical schema-v1 authority remains immutable:

- schema version: 1
- migration ID: `0001_initial_state`
- schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

P2.C2 MUST NOT edit the bytes/meaning of `SCHEMA_V1_STATEMENTS` or `SCHEMA_V1_DDL_SHA256`.

Current schema version becomes 2.

Add exact migration identity:

`SCHEMA_V2_MIGRATION_ID = "0002_ingress_rejected_disposition"`

Migration statements are canonically these four operations, in order:

```sql
ALTER TABLE ingress_updates RENAME TO ingress_updates_v1;

CREATE TABLE ingress_updates (
    update_id INTEGER PRIMARY KEY CHECK (update_id >= 0),
    received_at_ms INTEGER NOT NULL CHECK (received_at_ms >= 0),
    completed_at_ms INTEGER CHECK (completed_at_ms IS NULL OR completed_at_ms >= received_at_ms),
    disposition TEXT NOT NULL CHECK (
        disposition IN ('CONTROL','IGNORED_SLEEP','IGNORED_UNAUTHORIZED','IGNORED_REJECTED')
        OR (substr(disposition, 1, 4) = 'JOB:' AND length(disposition) > 4)
    )
);

INSERT INTO ingress_updates(update_id, received_at_ms, completed_at_ms, disposition)
SELECT update_id, received_at_ms, completed_at_ms, disposition FROM ingress_updates_v1;

DROP TABLE ingress_updates_v1;
```

Using the accepted `canonicalize_sql` rule, the exact migration-statement SHA-256 is:

`a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

Expose this as:

`SCHEMA_V2_MIGRATION_SHA256`

No other table, column, index, FK, check, or object set changes.

## Migration ledger

After successful schema-v2 migration, `schema_migrations` contains exactly two canonical rows:

1. historical v1 row with exact historical ID/hash;
2. version 2 row with migration ID `0002_ingress_rejected_disposition` and hash `a07e05ac...`.

The v2 migration calls the supplied migration clock exactly once for the version-2 ledger row, validates nonnegative signed-64 time, and sets `PRAGMA user_version = 2` only inside the successful migration transaction.

## Open/bootstrap behavior

`SqliteStorage.open` supports exactly user versions 0, 1, and 2:

- version 0 with no user objects: create/validate v1 using accepted v1 authority, then migrate/validate v2 before returning OPEN;
- version 1: validate exact v1 first, migrate to v2, validate exact v2, then return OPEN;
- version 2: validate exact v2 and return OPEN;
- any other version: `SCHEMA_UNSUPPORTED`.

A failed v2 migration must never leave a partially migrated schema. Transaction rollback leaves the database as valid v1. A later open may retry the migration. Cancellation of `open` retains accepted owned-worker semantics and never exposes a half-migrated database.

## Exact v2 validation

`_validate_v2` must require:

- the same final table/index sets as v1;
- no extra view/trigger/temp migration table;
- exact current SQL for every object;
- all v1 object SQL unchanged except the `ingress_updates` CHECK including `IGNORED_REJECTED`;
- exactly two migration ledger rows with exact versions, IDs and hashes;
- valid nonnegative migration timestamps;
- `PRAGMA user_version == 2` at open authority.

A database claiming v2 but retaining v1 ingress SQL, missing migration ledger row, wrong migration hash, extra backup table, altered unrelated SQL, or corrupt disposition fails `SCHEMA_INVALID`.

## Row-preservation migration proof

Migration from populated v1 must preserve byte-semantic values for every existing ingress row:

- update_id;
- received_at_ms;
- completed_at_ms;
- disposition.

Proof fixtures must include each existing legal class:

- CONTROL;
- IGNORED_SLEEP;
- IGNORED_UNAUTHORIZED;
- JOB:<id> with its coherent turn job.

No row may be lost, duplicated, re-timestamped, reclassified, or attached to a different job.

## New disposition materialization

`IngressDispositionKind` becomes exactly:

`CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | IGNORED_REJECTED | JOB`

Persisted exact `IGNORED_REJECTED` materializes as:

- disposition `IngressDispositionKind.IGNORED_REJECTED`;
- `job_id = None`.

Any near-miss/unknown disposition remains INVARIANT.

## claim_ignored

`IngressUpdateRepository.claim_ignored` accepts exactly:

- IGNORED_SLEEP;
- IGNORED_UNAUTHORIZED;
- IGNORED_REJECTED.

Fresh claim semantics remain unchanged: one owned SQLite write transaction, one validated clock, received/completed timestamps equal, no content.

Duplicate semantics remain unchanged: existing exact durable ingress is returned unchanged with `duplicate=True`, no clock and no reclassification regardless of requested ignored kind.

This is critical for future P5.2 races: a repeated BUSY/BLOCKED update cannot be reclassified after conditions change.

## Existing repository/application compatibility

Accepted P2.3/P2.4/P3 duplicate semantics continue to treat any non-JOB ingress as terminal duplicate/no new work. No P3 production code changes are authorized in P2.C2.

Retention must continue to treat `IGNORED_REJECTED` as ordinary terminal non-content ingress metadata under the same bounded ingress retention policy. If an exact existing retention query enumerates ignored values instead of treating non-JOB rows generically, P2.C2 may make the narrow required update; no retention interval/policy change is allowed.

P4/P5.1 code does not need semantic changes. Their existing CONTROL/SLEEP/UNAUTHORIZED behavior remains exact.

## Public/hash compatibility

Historical exports remain available:

- `SCHEMA_V1_STATEMENTS`
- `SCHEMA_V1_DDL_SHA256`
- historical migration ID authority.

Add current/version-2 exports without renaming historical ones. Exact export names may follow the existing package organization, but tests must distinguish historical v1 hash from current v2 migration authority.

Do not silently repurpose `SCHEMA_V1_DDL_SHA256` as a v2 hash.

## Security/effect boundary

P2.C2 stores no content and adds no external effect. No Telegram/Codex/network/production database is used in implementation tests. Migration tests use temporary synthetic SQLite files only.

## Acceptance

P2.C2 must prove at least:

- exact new enum and materializer behavior;
- fresh/duplicate `IGNORED_REJECTED` claim;
- duplicate requested rejected over existing JOB/SLEEP/CONTROL remains original durable record with zero clock;
- new empty DB opens as exact v2;
- populated valid v1 auto-migrates to v2 preserving all rows;
- v1 migration ledger row remains exact;
- v2 ledger row exact ID/hash;
- v2 reopen is idempotent and performs no migration clock call;
- malformed v1 fails before migration;
- malformed/forged v2 fails closed;
- failed v2 migration rolls back to valid v1 with no backup table;
- no extra objects after migration;
- retention covers `IGNORED_REJECTED` under existing policy;
- all P1–P5.1 regressions remain green;
- no production filesystem/network/effect.

Accepted pre-P2.C2 full-suite baseline is 777.

## P5.2 gate

P5.2 MUST NOT start until P2.C2 is architect-accepted. After acceptance, P5.2 may use `IGNORED_REJECTED` to terminalize BUSY/BLOCKED/stale authorized prompt updates before they can later replay into a JOB.
