# ADR-0017 — SQLite storage kernel and schema-v1 boundary

Status: accepted
Date: 2026-09-05

## Context

P1 is complete. P2 introduces the controller-owned durable state described by `DATA_MODEL.md`, but application orchestration remains P3. P2.1 must establish a small, deterministic SQLite kernel and the version-1 physical schema without also implementing repositories, Telegram ingress, dialogue transitions, retention policy execution, or hard-delete orchestration.

The controller is an async process running as the configured OS user (root in V1). Blocking SQLite calls, migration guesses, permissive file ownership, competing controller writers, and caller cancellation that abandons a local commit are unacceptable.

## Decision — runtime kernel

1. P2.1 uses Python standard-library `sqlite3`; no new runtime dependency is introduced.
2. One `SqliteStorage` instance owns one persistent SQLite connection on one dedicated `ThreadPoolExecutor(max_workers=1)` worker thread. The connection is created, configured, used, migrated and closed only on that worker. No `sqlite3.Connection` or cursor is exposed as a long-lived public object.
3. The configured database path must be absolute, NUL-free and have an existing real directory parent. The parent, database path and lock path must not be symlinks. Existing database/lock files must be regular files owned by the effective UID and must have no group/other permission bits. A new DB/lock file is securely created with mode `0600` before SQLite/locking use.
4. A sibling lock file `<database-path>.lock` is held with non-blocking exclusive `fcntl.flock` for the storage lifetime. A second controller/storage owner for the same DB fails closed; it does not wait indefinitely or open a competing writer.
5. Connection contract: `foreign_keys=ON`, `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=FULL`, `trusted_schema=OFF`, manual transaction control (`isolation_level=None`) and `sqlite3.Row` row factory. Required PRAGMA results are verified during open.
6. P2.1 does not use a production DB path in tests. All storage tests use temporary directories/files only.

## Decision — async ownership and transactions

1. Storage offers async execution primitives over synchronous callbacks that execute only on the dedicated DB worker.
2. Read transactions use explicit `BEGIN DEFERRED`; write transactions use explicit `BEGIN IMMEDIATE`. Every successful callback commits; every exception/cancellation inside the worker transaction rolls back before propagation/normalization.
3. Once an operation has been submitted to the DB worker, public coroutine cancellation does not detach or cancel that owned DB operation. Repeated caller cancellation is deferred until the exact submitted operation reaches a definitive committed/rolled-back result. A coroutine cancelled before it ever submits work may cancel normally.
4. Storage serializes all DB callbacks through its one worker. P2.1 adds no second writer queue and no automatic retry loop.
5. Close is idempotent. Once close ownership begins, new operations fail as CLOSED; close waits for prior submitted work, closes the connection on the worker, releases the file lock and shuts down the worker. Caller cancellation does not leave an unknown live connection/lock.
6. Callback code may return ordinary immutable/materialized values but must not return/retain a SQLite connection or cursor. P2 repositories will convert rows to domain/storage records inside the worker callback.

## Decision — safe storage errors

P2.1 introduces a finite storage diagnostic taxonomy equivalent to:

- `INVALID_PATH`
- `INSECURE_PATH`
- `LOCKED`
- `OPEN_FAILED`
- `SCHEMA_UNSUPPORTED`
- `SCHEMA_INVALID`
- `CLOSED`
- `TRANSACTION_FAILED`

Storage error rendering contains only the finite category. It never embeds the DB path, SQL text, values, exception body, environment or content. Arbitrary callback/domain exceptions are rolled back and may propagate to their owning higher layer; raw `sqlite3` infrastructure failures are normalized to finite storage errors.

## Decision — schema migration authority

1. `SCHEMA_VERSION = 1`.
2. Migration history is durable in `schema_migrations(version INTEGER PRIMARY KEY, migration_id TEXT NOT NULL UNIQUE, ddl_sha256 TEXT NOT NULL, applied_at_ms INTEGER NOT NULL CHECK(applied_at_ms>=0))` and mirrored by `PRAGMA user_version`.
3. Version 0 is accepted only for a new/empty database. A non-empty unversioned DB is `SCHEMA_INVALID`; P2.1 never guesses ownership or destructively adopts it.
4. A DB with `user_version` greater than the code's supported version is `SCHEMA_UNSUPPORTED`.
5. Opening version 1 verifies the expected migration ID/hash and the exact required user-table/index names. Missing/mismatched schema authority fails closed; P2.1 does not auto-repair or drop objects.
6. Bootstrap/migration executes in one explicit migration transaction; `user_version` advances only after the version-1 DDL and migration-history row are successfully installed.
7. Migration timestamps use an injected/testable millisecond clock; tests do not depend on wall-clock timing.

## Decision — schema v1 tables

All timestamps are signed SQLite INTEGER epoch milliseconds and must be non-negative where present. Version/count/sequence/generation values are non-negative unless a later architect decision says otherwise. Content-bearing payload is isolated in `transient_payloads`; long-lived tables contain IDs/hashes/sanitized error classes rather than transcripts.

### `controller_runtime`
Singleton (`singleton=1`): `last_control_epoch`, diagnostic `requested_mode` (`ACTIVE|SLEEP`), `boot_generation`, `fleet_version`, `created_at_ms`, `updated_at_ms`. Stored requested mode never overrides the architectural boot rule: effective mode still starts SLEEP.

### `settings`
Singleton (`singleton=1`): nullable default `profile_id`, `model_id`, `reasoning_effort`, optimistic `version`, `created_at_ms`, `updated_at_ms`. No secrets.

### `dialogues`
`dialogue_id` primary key, constant unique `live_slot=1`, `server_id`, immutable `profile_id`, nullable `thread_id`, canonical dialogue `state`, optimistic `version`, timestamps, nullable sanitized `last_error_class`. Because `NO_DIALOGUE` is represented by absence of a dialogue row and every retained dialogue state still owns/reconciles the live binding, the unique live slot enforces at most one retained/live dialogue row in V1.

Allowed stored states are exactly: `CREATING`, `IDLE`, `CREATE_UNKNOWN`, `ERROR`, `TURN_RUNNING`, `INTERRUPTING`, `TURN_UNKNOWN`, `DELETE_PENDING`, `DELETING`, `DELETE_UNKNOWN`.

### `turn_jobs`
`job_id` primary key; unique `telegram_update_id`; source chat/message IDs; `dialogue_id` FK; captured `server_id`, `profile_id`, nullable `thread_id`, nullable `model_id`, nullable `reasoning_effort`; required input SHA-256; nullable Codex turn ID; canonical job state; optimistic `version`; timestamps; nullable sanitized `error_class`. Schema permits nullable captured thread/model/effort so later repository/application transactions can represent the first-prompt/create boundary without inventing an identity before Codex confirms it.

Allowed job states: `RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`, `CODEX_COMPLETED`, `FAILED`, `UNKNOWN`, `DELIVERY_PENDING`, `DELIVERING`, `DELIVERED`, `DELIVERY_UNKNOWN`.

### `transient_payloads`
`payload_id` primary key; nullable dialogue/job ownership FKs with a check that at least one owner exists; finite kind `INPUT|OUTPUT|APPROVAL|DISPLAY`; `content` BLOB; SHA-256; byte length; `created_at_ms`; `expires_at_ms`. Dialogue/job deletion cascades transient content. No permanent transcript table is introduced.

### `delivery_segments`
Primary key `(job_id, sequence)` with `sequence>=1`; operation `CREATE|EDIT`; nullable target Telegram message ID; nullable payload FK with `ON DELETE SET NULL`; required payload SHA-256; state; `attempt_count`; nullable confirmed message ID; timestamps. Allowed states: `PENDING`, `SENDING`, `CONFIRMED`, `UNKNOWN`, `FAILED`.

### `ingress_updates`
Primary key Telegram `update_id`; `received_at_ms`; nullable `completed_at_ms`; non-null disposition. Disposition must be one of `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, or the `JOB:<opaque-job-id>` form. No raw update JSON or message text column exists.

### `callback_actions`
Primary key `token_hash_sha256`; `action`; `subject_type`; `subject_id`; required expected version/state; authorized user/chat IDs; `created_at_ms`; `expires_at_ms`; nullable `consumed_at_ms`. Only the hash of the opaque callback token is stored.

### `approvals`
`approval_id` primary key; `profile_id`; exact wire request ID represented as `(wire_request_id_type, wire_request_id)` where type is `INTEGER|STRING`; `job_id` FK; finite approval kind; nullable display payload FK with `ON DELETE SET NULL`; state; `created_at_ms`; `updated_at_ms`; `expires_at_ms`. Allowed states: `PENDING`, `APPROVED`, `DENIED`, `EXPIRED`, `CANCELLED`. Wire request IDs are not globally unique because P1.7 permits later reuse after terminal handling; `approval_id` is the durable local identity.

### `deletion_tombstones`
Primary key `dialogue_id`; SHA-256 of the deleted thread identity; `stale_generation`; `deleted_at_ms`; `expires_at_ms`. No prompt/response and no raw thread ID is required once finalization no longer needs it.

### `errors`
Primary key SHA-256 fingerprint; sanitized `error_class`; `count`; `first_seen_at_ms`; `last_seen_at_ms`; nullable dialogue/job references using `ON DELETE SET NULL`. No arbitrary error body, stderr, prompt, response, environment or auth material.

## Decision — indexes and foreign keys

Schema v1 includes deterministic indexes supporting the next P2 slices: job dialogue/state; transient expiry; delivery state; callback expiry/consumed status; approval job/state/expiry; tombstone expiry; error last-seen time. Foreign keys are explicit. Dialogue-owned jobs/content cascade only when a later architect-authorized local purge transaction deletes the dialogue; error metadata references are set null rather than forcing content retention.

P2.1 itself does not expose repository methods that delete dialogues or payloads.

## Out of scope

P2.1 does not implement controller/settings/dialogue repository operations, legal state-transition methods, Telegram ingress dedupe, callbacks, turn-job claims, retention cleanup, approvals repository behavior, deletion finalization, crash recovery, SQLite backup/restore, P3 application services, Telegram, deployment, or production DB creation.
