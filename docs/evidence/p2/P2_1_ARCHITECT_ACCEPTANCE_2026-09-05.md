# P2.1 architect acceptance — 2026-09-05

Status: ACCEPTED

Accepted cumulative implementation HEAD: `61301fd25ff7253693f367664ce99e13dfc88446`.
Architect base: `f9f71f161ba61508e8bd648ea835e63278377a03`.
Issue: #11.

## Review history

- Initial candidate `08eb22b413cfec464170dd67b63541f7031be9e9` was rejected after independent review found that integration tests were omitted from full discovery, lazy/async callback results could escape the DB-worker boundary, callbacks could take over transaction control, migration-clock errors were not safely normalized, and several proofs were incomplete.
- First repair `db1f2d212a59f1b808fc303c9ec64d6eed108af6` fixed those findings but was rejected after review showed that a read callback could disable `query_only`, callback PRAGMA mutations could persist, ATTACH/DETACH could escape the single secured database boundary, normal callback DDL/migration authority was insufficiently protected, connection attributes could drift, and nested SQLite/lazy results could escape.
- Second repair `61301fd25ff7253693f367664ce99e13dfc88446` closed the remaining confirmed blockers and preserved the frozen schema.

## Accepted storage-kernel facts

- Standard-library `sqlite3` only; no runtime DB dependency added.
- One `SqliteStorage` owns one persistent connection on one dedicated `ThreadPoolExecutor(max_workers=1)` thread. Connection create/configure/migrate/use/close stays on that worker with default `check_same_thread=True`.
- Absolute/NUL-free path, real secure parent, effective-UID ownership, exact `0600` DB/lock files, symlink rejection and non-blocking lifetime `flock` are enforced fail-closed.
- Required connection authority is verified: foreign keys ON, WAL, 5000ms busy timeout, synchronous FULL, trusted schema OFF, manual transactions and `sqlite3.Row` rows.
- Reads use explicit DEFERRED transaction plus `query_only`; writes use IMMEDIATE. Submitted work remains owned through repeated public cancellation; there is no automatic retry. Close is owned/idempotent and releases connection, worker and flock.
- Callback SQL authority prevents transaction/savepoint takeover, read DML, callback PRAGMA setters, ATTACH/DETACH, normal callback DDL and mutation of `schema_migrations`; row-factory/isolation invariants are checked/restored.
- Callback result validation rejects direct and nested connection-bound SQLite resources plus lazy/awaitable iterator results while accepting ordinary materialized built-in values.
- Storage diagnostics are finite and content/path/SQL redacted.

## Accepted schema-v1 facts

- `SCHEMA_VERSION=1`.
- Migration ID `0001_initial_state`.
- Canonical DDL SHA-256 `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Physical DDL, 12 user-table set and 14 explicit-index set match ADR-0018.
- Bootstrap accepts only an empty version-0 database, applies one explicit migration transaction, writes the exact migration-history row and `user_version=1`, and uses an injected millisecond clock only when migration is actually applied.
- Reopen is idempotent and verifies migration ID/hash/timestamp, exact object sets and canonical `sqlite_master.sql`; future/unversioned-nonempty/missing/extra/drifted schema fails closed without repair.
- Foreign keys, schema CHECKs, one-dialogue live slot, reusable approval wire IDs and content-boundary constraints are proven with temporary databases only.

## Acceptance evidence

Final focused counts reported and structurally consistent with committed tests:

- P2.1 schema/unit: 8.
- P2.1 integration: 31.
- P1.10 T0/T1/T2: 6 / 1 / 4.
- Base accepted pre-P2.1 full suite: 248.
- Final full suite: `248 + 8 + 31 = 287`.
- Integration package is included in `unittest discover`.
- Compile/import, diff and security checks passed.
- No production DB/state root, secrets, services or architecture files were changed by the implementation.

The previously known P1.6 pending-task warning remains test-hygiene debt and was not introduced by P2.1.

P2.1 is architect-accepted. This acceptance does not authorize later P2 repository/application work except through a new explicit architect-owned slice.