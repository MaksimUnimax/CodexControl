# ADR-0023 — Hard-delete claims, tombstones and error fingerprints

Status: accepted
Date: 2026-09-06

## Context

P2.1–P2.4b now durably own storage, dialogue/turn state, idempotency, delivery, approvals and transient retention. P2.5 must add the local durable boundary around the already accepted P1.9 official `thread/delete` effect, plus bounded non-content deletion tombstones and sanitized error fingerprints. No repository in this slice calls Codex or Telegram.

## Common authority

1. Use only accepted `SqliteStorage.read/write` and frozen schema-v1. No migration/DDL change.
2. Existing finite `RepositoryError` taxonomy remains authoritative. Clocks, signed-64 integers, optimistic versions, redaction and no-clock-on-failed-precondition rules follow accepted P2.2–P2.4b behavior.
3. No automatic retry/background task. `DELETE_UNKNOWN` is not a retry source.
4. The raw Codex thread ID remains in the live dialogue until official external delete is definitive. It is never stored in `deletion_tombstones`; tombstones store only SHA-256 of the exact UTF-8 thread ID.
5. The repository commits delete intent before the future P1.9 external effect and purges controller-owned dialogue state only after confirmed external deletion.

## Global dialogue deletion shapes

ADR-0023 now owns these persisted `DialogueState` shapes globally:

- `DELETE_PENDING`: thread ID non-NULL; `last_error_class` NULL.
- `DELETING`: thread ID non-NULL; `last_error_class` NULL.
- `DELETE_UNKNOWN`: thread ID non-NULL; sanitized non-NULL `last_error_class`.

These rules apply to ordinary `DialogueRepository` materialization as well as the deletion repository. Existing P2.2/P2.4a-owned dialogue shapes are otherwise unchanged.

## Delete readiness

A new hard-delete intent may be claimed only from canonical `IDLE` with a bound thread ID and exact expected dialogue version.

Before the intent is accepted, every retained turn job for that dialogue must be canonical and terminal-safe: only `DELIVERED` or `FAILED` are allowed. Any `RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`, `CODEX_COMPLETED`, `UNKNOWN`, `DELIVERY_PENDING`, `DELIVERING` or `DELIVERY_UNKNOWN` job blocks deletion with `STATE_CONFLICT`.

Any remaining `PENDING` approval for a job owned by that dialogue also blocks deletion with `STATE_CONFLICT`; the application may first use the accepted P2.4b cancellation boundary after the job is no longer running.

Zero-job IDLE dialogues are allowed.

## Deletion repository

`DeletionRepository` exposes only:

- `get_tombstone(dialogue_id)`;
- `claim_delete_intent(dialogue_id, expected_version)`;
- `claim_deleting(dialogue_id, expected_version)`;
- `mark_delete_unknown(dialogue_id, expected_version, error_class)`;
- `mark_delete_error(dialogue_id, expected_version, error_class)`;
- `finalize_confirmed(dialogue_id, expected_version, tombstone_expires_at_ms)`.

No retry, reconciliation, interrupt, thread-delete call, tombstone cleanup or arbitrary transition API is part of P2.5.

## Intent claim

`claim_delete_intent` is one write transaction. Missing dialogue is `NOT_FOUND`; stale version is `VERSION_CONFLICT`; wrong dialogue/readiness state is `STATE_CONFLICT`. It checks version incrementability before clock, calls the clock once, and atomically changes:

`IDLE -> DELETE_PENDING`

with version +1, monotonic `updated_at_ms`, unchanged dialogue/server/profile/thread identity and NULL `last_error_class`.

This durable state blocks new turns before any future external delete work.

## Deleting claim

`claim_deleting` requires exact `DELETE_PENDING`, exact version and the same readiness invariants. It atomically changes:

`DELETE_PENDING -> DELETING`

with version +1 and one clock. The returned exact `DialogueRecord` is the binding used later by application code to invoke P1.9 with the exact profile/thread. The repository itself performs no external call.

## External non-confirmation capture

After a `DELETING` row exists:

- ambiguous/dispatched non-confirmation is captured by `mark_delete_unknown`: `DELETING -> DELETE_UNKNOWN`, version +1, sanitized error class retained, binding retained;
- a deterministic local/pre-dispatch failure that is known not to have performed the external effect may be captured by `mark_delete_error`: `DELETING -> ERROR`, version +1, sanitized error class retained, binding retained.

Neither state is a P2.5 retry source. Reconciliation policy remains later application/recovery authority.

## Confirmed finalization

`finalize_confirmed` is called only after P1.9 has returned definitive `DELETE_CONFIRMED` for the exact DELETING binding. In one SQLite write transaction it requires:

- dialogue exists and is canonical `DELETING`;
- exact expected dialogue version;
- bound thread ID exists;
- no pre-existing tombstone for the same dialogue ID;
- delete readiness remains terminal-safe;
- `tombstone_expires_at_ms` is an exact non-bool non-negative signed-64 integer and, after the clock is read, is strictly later than the effective delete timestamp.

It computes:

- `thread_identity_sha256 = sha256(thread_id.encode('utf-8')).hexdigest()`;
- `stale_generation = current DELETING dialogue.version`;
- `deleted_at_ms = max(validated_clock_now, dialogue.updated_at_ms)`.

The same transaction inserts the tombstone and deletes the dialogue row with an exact state/version guard. Existing schema FKs then purge dialogue-owned controller state:

- `turn_jobs`;
- `transient_payloads`;
- `delivery_segments`;
- `approvals`.

`errors` rows are retained as non-content fingerprints and their dialogue/job references become NULL through schema `ON DELETE SET NULL`.

`ingress_updates` and `callback_actions` are deliberately retained in P2.5 as bounded non-content idempotency/replay metadata; broader metadata retention is P2.6. No raw prompt/output/thread identity is retained in the tombstone.

Finalization returns an immutable factual result containing the tombstone plus counts of purged jobs, transient payloads, delivery segments and approvals. The deleted live binding is absent after commit.

Any failure rolls back tombstone insertion and local purge together.

## Tombstones

`DeletionTombstoneRecord` mirrors schema-v1:

- dialogue ID;
- canonical lower-case thread identity SHA-256;
- non-negative signed-64 stale generation;
- deleted timestamp;
- expiry timestamp strictly greater than deleted timestamp.

P2.5 can read tombstones but does not delete expired tombstones. Bounded tombstone/metadata retention belongs to P2.6.

## Error fingerprints

`ErrorFingerprintRepository` exposes only:

- `get(fingerprint_sha256)`;
- `record(fingerprint_sha256, error_class, dialogue_id=None, job_id=None)`.

`fingerprint_sha256` is canonical lower-case 64-char hex. `error_class` is sanitized `^[A-Za-z0-9_.:-]{1,128}$`. There is no API parameter for raw exception text, traceback, stderr, prompt, response, environment or secrets.

Optional dialogue/job IDs are canonical IDs. When supplied they must reference existing canonical rows; when both are supplied, the job must belong to the dialogue. Neither reference is required for controller-wide errors.

First record inserts count 1 and first/last timestamps from one clock. Existing fingerprint materialization must be canonical. A repeat is valid only when error class and optional entity references exactly equal the existing record; otherwise it is `INVARIANT_VIOLATION` rather than merging unrelated errors. A valid repeat increments count exactly once, preserves first timestamp, updates last timestamp monotonically, checks signed-64 overflow before clock and never retries.

After hard delete, FK `SET NULL` may clear error entity references while preserving the sanitized fingerprint/count/timestamps.

## Out of scope

No P1.9 invocation, Telegram, interrupt orchestration, DELETE_UNKNOWN reconciliation/retry, callback/ingress metadata cleanup, tombstone expiry cleanup, broad job/error retention, filesystem temp-store deletion, P2.6 crash/restart acceptance, P3 application service or production state.
