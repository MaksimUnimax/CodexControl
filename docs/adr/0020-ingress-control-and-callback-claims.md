# ADR-0020 — Ingress dedupe, control epoch and opaque callback claims

Status: accepted
Date: 2026-09-05

## Context

P2.1 established the secure SQLite kernel and schema-v1. P2.2 established controller boot state, settings CAS and dialogue create-intent repositories. P2.3 now owns the durable idempotency primitives needed before Telegram application/routing layers exist: ingress update dedupe, atomic control-message epoch/mode claims, and opaque one-time callback-action claims.

This slice must not introduce Telegram networking, turn jobs, approval orchestration or P3 application state machines.

## Decision — common authority

1. P2.3 uses only accepted `SqliteStorage.read/write` transactions and the existing schema-v1 tables. No DDL/migration change is allowed.
2. Existing P2.2 `RepositoryErrorCategory` remains unchanged. Invalid arguments, missing controller bootstrap and persisted corruption use the existing finite semantic categories; operational dedupe/callback outcomes use finite result-status enums rather than expanding the error taxonomy.
3. All public numeric IDs/timestamps use exact Python integers, never bool, within signed-64 SQLite bounds. Telegram update/control epochs are non-negative. Telegram user ID is positive signed-64; chat ID is non-zero signed-64 because group chat IDs may be negative.
4. Repository clocks use the accepted P2.2 validation/redaction/monotonic policy and are called only after semantic preconditions prove that the current invocation needs a timestamp.
5. No raw Telegram update JSON/text, callback token plaintext, secret, prompt/response, command output or arbitrary exception text is stored.
6. Accepted P2.2 public repository surfaces remain backward-compatible. In particular `ControllerRuntimeRepository` remains exactly `get` + `begin_boot`; P2.3 control handling is a separate repository boundary rather than extending that class.

## Decision — ingress record

`IngressDispositionKind` freezes four materialized kinds: `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`, `JOB`.

`IngressUpdateRecord` contains: `update_id`, `received_at_ms`, nullable `completed_at_ms`, `disposition`, nullable `job_id`.

Materialization rules:

- exact `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED` => corresponding kind and `job_id=None`;
- `JOB:<id>` => kind `JOB` and a non-empty/NUL-free job ID of length <=128;
- any other persisted disposition, invalid timestamp/type or invalid JOB suffix => `INVARIANT_VIOLATION`.

P2.3 exposes `IngressUpdateRepository.get(update_id)` and `claim_ignored(update_id, disposition)`.

`claim_ignored` accepts only `IGNORED_SLEEP` or `IGNORED_UNAUTHORIZED`. For a new update it calls the clock once and inserts received/completed timestamps equal to that value. For an already-known update ID it returns the exact existing durable record unchanged with `duplicate=True`, regardless of the newly requested classification, and calls no clock. This is durable dedupe: a duplicate is never reclassified.

P2.3 does not expose a JOB-claim method; P2.4 will atomically create turn jobs and `JOB:<id>` ingress disposition.

## Decision — control ingress + epoch/mode transaction

Controller control-message mutation is deliberately combined with ingress dedupe in ONE P2.1 write transaction.

P2.3 exposes a separate `ControlIngressRepository` with one semantic method equivalent to:

`claim_control(update_id, control_epoch, requested_mode) -> ControlClaimResult`.

This separate class is deliberate: accepted P2.2 `ControllerRuntimeRepository` remains `get` + `begin_boot` only.

`requested_mode` must be the accepted `ControllerMode` enum. Higher routing layers decide whether a human control maps to ACTIVE or SLEEP; the repository does not parse labels/messages.

`ControlClaimStatus` is exactly: `APPLIED`, `STALE`, `DUPLICATE`.

`ControlClaimResult` contains: status, exact ingress record, and nullable controller record. It intentionally contains no `effective_mode` field.

Transaction semantics:

1. Validate arguments before SQL.
2. If `ingress_updates.update_id` already exists, materialize it and return `DUPLICATE`; do not call the clock, do not mutate controller mode/epoch, and return no newly-authoritative effective mode.
3. Otherwise require the `controller_runtime` singleton to exist and materialize canonically. Missing row => `NOT_FOUND`, no ingress record, no clock.
4. Call the repository clock exactly once for this new control update.
5. If `control_epoch <= last_control_epoch`, insert a terminal `CONTROL` ingress record with received/completed timestamps, leave controller row byte-semantically unchanged, and return `STALE` plus the current controller record.
6. If `control_epoch > last_control_epoch`, atomically update `last_control_epoch`, `requested_mode` and monotonic `updated_at_ms`, preserving boot generation, fleet version and creation time; insert the terminal `CONTROL` ingress record in the same transaction; return `APPLIED` plus the updated controller record.
7. No retry/merge. Unexpected CAS row-count mismatch is fail-closed `INVARIANT_VIOLATION`.

A fresh control with the same requested mode still advances the epoch. Signed-64 MAX epoch is valid.

Critical restart rule: persisted historical `requested_mode=ACTIVE` does not itself restore ACTIVE. `begin_boot()` still returns effective SLEEP. A replayed previously-deduped activation returns `DUPLICATE` and performs no mode mutation, so restart requires a genuinely new control update/epoch. Higher application routing changes its in-memory effective mode only from a fresh `APPLIED` result.

STATUS is not a mode mutation and will not call `claim_control` in later routing layers.

## Decision — callback action record

`CallbackActionRecord` contains the exact schema-v1 fields: token hash, action, subject type/id, expected version/state, authorized user/chat, created/expires/consumed timestamps.

P2.3 never accepts or stores callback token plaintext. Its API accepts only a canonical lower-case SHA-256 hex digest matching `^[0-9a-f]{64}$`. Token generation and hashing remain the future Telegram UI layer's responsibility.

`action`, `subject_type` and `expected_state` are sanitized identifiers using ASCII letters/digits plus `_ . : -` within their schema bounds. `subject_id` is non-empty/NUL-free and <=128. `expected_version` is non-negative signed-64. User/chat IDs follow the common numeric rules above.

`CallbackActionRepository` exposes only semantic create/claim operations and no generic arbitrary update/delete API.

Create semantics:

- if token hash already exists => `ALREADY_EXISTS`, no clock/mutation;
- otherwise call the clock, require supplied `expires_at_ms` to be a valid signed-64 integer strictly greater than creation time, and insert `consumed_at_ms=NULL`;
- no overwrite/reissue of an existing token hash.

## Decision — callback one-time claim

`CallbackClaimStatus` is exactly: `CLAIMED`, `NOT_FOUND`, `UNAUTHORIZED`, `EXPIRED`, `ALREADY_CONSUMED`.

`CallbackClaimResult` contains the status and an optional `CallbackActionRecord`. Only `CLAIMED` exposes the action record; all non-claimed statuses return no action metadata.

Claim order inside one write transaction:

1. validate canonical token hash and caller user/chat IDs before SQL;
2. missing hash => `NOT_FOUND`, no clock;
3. authorized user/chat mismatch => `UNAUTHORIZED`, no clock and no action metadata;
4. already-consumed row => `ALREADY_CONSUMED`, no clock and no action metadata;
5. call clock; effective claim time is `max(clock_now, created_at_ms)`;
6. if effective claim time >= `expires_at_ms` => `EXPIRED`, no mutation/action metadata;
7. otherwise set `consumed_at_ms` exactly once with `WHERE token_hash_sha256=? AND consumed_at_ms IS NULL`; row-count mismatch after the precheck is `INVARIANT_VIOLATION`;
8. return `CLAIMED` with the immutable consumed record.

No retry. Double/concurrent claims have exactly one `CLAIMED`; every later authorized claim is `ALREADY_CONSUMED`. Claim survives public coroutine cancellation according to P2.1 owned-transaction semantics.

The callback record's bound `action/subject/version/state` metadata is returned only after successful one-time claim. P2.3 itself performs NO external effect and does not implement subject-specific state mutation. Later application/storage slices must complete any required subject claim before external effect; a standalone P2.3 claim is never evidence that the subject mutation/effect occurred.

## Restart and retention

Ingress dedupe, control epoch and callback consumed state are durable across storage close/reopen. Unconsumed callback expiry is evaluated against the injected clock after restart. P2.3 does not delete old ingress/callback rows; bounded retention is a later architect-owned slice.

## Out of scope

No Telegram API/client/handlers, fleet label parsing, STATUS handling, turn-job creation, `JOB:<id>` creation, transient payload/delivery/approval repositories, callback token generation, subject-specific callback business mutations, retention cleaner, hard delete, P3 orchestration or deployment.