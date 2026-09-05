# ADR-0019 — Core durable repository boundary

Status: accepted
Date: 2026-09-05

## Context

P2.1 established the secure SQLite kernel and exact schema-v1. P2.2 introduces the first typed durable repositories, but must not absorb Telegram ingress/idempotency, turn-job/delivery/approval state, retention, delete finalization or P3 application orchestration.

The core tables needed first are `controller_runtime`, `settings` and `dialogues`. Repository methods must preserve durable identity/version invariants, use P2.1 transactions, and expose materialized immutable records only.

## Decision — common repository boundary

1. P2.2 adds immutable typed records/enums and repository classes under `codex_control.storage` (or a narrow subpackage).
2. Repositories use only `SqliteStorage.read/write`; they never access the SQLite file/connection directly outside a storage callback and never expose `sqlite3.Row`, cursor or connection objects.
3. Semantic repository errors are finite and content-free. Required categories are equivalent to: `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `VERSION_CONFLICT`, `STATE_CONFLICT`, `CLOCK_INVALID`, `INVARIANT_VIOLATION`. Underlying `StorageError` remains the storage-kernel error and may propagate unchanged.
4. Repository error repr/str contains only the finite category. No SQL, values, database path, exception body or content.
5. IDs/strings are validated before SQL: non-empty where required, NUL-free, and within the exact schema-v1 length bounds. `last_error_class` is additionally a sanitized identifier consisting only of ASCII letters/digits plus `_ . : -`, length 1..128.
6. Repository clocks are injected/testable millisecond callables. A clock exception, bool, non-integer or negative value becomes finite `CLOCK_INVALID` with no source text. For updates, persisted `updated_at_ms` is `max(clock_now, previous.updated_at_ms)` so a wall-clock step backwards cannot violate durable monotonic timestamps.
7. Versioned records start at version 0 and every successful semantic mutation increments exactly by one. Expected-version mismatch is `VERSION_CONFLICT`; no retry/merge is performed by the repository.
8. SQLite/kernel cancellation ownership remains P2.1 authority. P2.2 creates no background worker/task and no automatic retry.

## Decision — controller_runtime repository

P2.2 exposes only durable boot/read semantics. Control-message epoch/mode mutation is P2.3.

`ControllerRuntimeRecord` contains: `last_control_epoch`, historical `requested_mode`, `boot_generation`, `fleet_version`, `created_at_ms`, `updated_at_ms`.

`begin_boot(fleet_version)` is one write transaction:

- if singleton row is absent, insert `last_control_epoch=0`, `requested_mode=SLEEP`, `boot_generation=1` and the supplied validated fleet version;
- if present, preserve `last_control_epoch` and historical `requested_mode`, increment `boot_generation` by exactly one, replace `fleet_version`, and advance `updated_at_ms` monotonically;
- integer overflow/noncanonical stored values fail `INVARIANT_VIOLATION` rather than wrapping or rewriting unrelated state.

The returned boot result also exposes `effective_mode=SLEEP` unconditionally. Persisted historical `requested_mode=ACTIVE` never restores ACTIVE after process start.

`get_controller_runtime()` returns the materialized record or `None` before the first boot initialization.

No P2.2 method mutates `last_control_epoch` or `requested_mode` after initialization.

## Decision — settings repository

`SettingsRecord` contains optional `profile_id`, `model_id`, `reasoning_effort`, plus `version`, `created_at_ms`, `updated_at_ms`.

`initialize_settings_if_absent(profile_id, model_id, reasoning_effort)`:

- inserts singleton version 0 only if no settings row exists;
- if a row already exists, returns that durable row unchanged even when new config fallback values differ;
- returns a result that indicates whether creation occurred.

This makes durable settings authoritative over later config fallback after the first initialization.

`replace_settings(expected_version, profile_id, model_id, reasoning_effort)`:

- requires an existing row;
- validates the complete replacement values (nullable exactly where schema allows);
- updates only when `version == expected_version`;
- increments version exactly by one and advances time monotonically;
- stale version => `VERSION_CONFLICT`; missing singleton => `NOT_FOUND`.

P2.2 intentionally does NOT enforce whether profile/model/effort is currently allowed by dialogue/turn state. P3 application orchestration owns those product preconditions and runtime validation.

## Decision — dialogue create-intent repository

P2.2 implements only the durable dialogue-creation path required before external `thread/start`. It does not implement turn/interrupt/delete state transitions.

`DialogueState` freezes all schema-v1 values for materialization, but P2.2 write methods use only: `CREATING`, `IDLE`, `CREATE_UNKNOWN`, `ERROR`.

`DialogueRecord` contains: `dialogue_id`, `server_id`, immutable `profile_id`, nullable `thread_id`, `state`, `version`, `created_at_ms`, `updated_at_ms`, nullable sanitized `last_error_class`.

`get_live_dialogue()` returns the sole retained dialogue row or `None`.

`create_dialogue_intent(dialogue_id, server_id, profile_id)`:

- one write transaction;
- requires there is no dialogue row;
- inserts `live_slot=1`, `thread_id=NULL`, `state=CREATING`, `version=0`, no error;
- any retained dialogue row => `ALREADY_EXISTS`;
- it is deliberately not silently idempotent, because duplicate external-create orchestration must be prevented by the higher idempotency/application layers rather than replayed here.

`confirm_dialogue_created(dialogue_id, expected_version, thread_id)`:

- exact row must exist;
- expected version must match;
- state must be `CREATING` and stored thread ID must still be NULL;
- set exact validated thread ID once, state `IDLE`, clear error, increment version exactly once.

`mark_dialogue_create_unknown(dialogue_id, expected_version, error_class)`:

- only `CREATING` with NULL thread ID;
- set `CREATE_UNKNOWN`, keep thread ID NULL, store sanitized error class, increment version.

`mark_dialogue_create_error(dialogue_id, expected_version, error_class)`:

- only `CREATING` with NULL thread ID;
- set `ERROR`, keep thread ID NULL, store sanitized error class, increment version.

For all three terminal create-intent mutations: missing row => `NOT_FOUND`; version mismatch => `VERSION_CONFLICT`; wrong state/thread precondition => `STATE_CONFLICT`.

P2.2 exposes no generic arbitrary-state update and no dialogue DELETE. Profile/server identity is never mutated after intent insertion.

## Decision — concurrency/restart semantics

All methods are atomic P2.1 transactions. Concurrent calls with the same expected version cannot both succeed. Reopening the database reconstructs exactly the same immutable records/versions. No in-memory cache is authoritative.

## Out of scope

P2.2 does not implement control epoch acceptance, ACTIVE/SLEEP routing mutations, Telegram update dedupe, callback tokens, turn jobs, transient payload lifecycle, delivery segments, approvals, retention, error fingerprints, deletion tombstones, local hard-delete purge, crash/restart orchestration, P3 service logic, Telegram or production deployment.