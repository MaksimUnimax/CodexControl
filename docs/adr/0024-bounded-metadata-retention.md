# ADR-0024 — Bounded metadata retention after terminal durable state

Status: accepted
Date: 2026-09-06

## Context

P2.1–P2.5 now own the durable SQLite kernel, core/controller state, ingress and callbacks, turn jobs/transient content, delivery/approvals/content retention, and confirmed hard-delete local finalization. The remaining storage-production gap before final P2 crash/restart acceptance is bounded cleanup of non-content metadata that deliberately survived earlier slices.

This ADR defines P2.6a only. P2.6b remains a later proof/acceptance harness over the accepted P2 durable surface.

## Common authority

1. Use frozen schema-v1 and accepted `SqliteStorage.read/write`; no migration or DDL change.
2. P2.6a performs only local metadata cleanup. No Telegram, Codex, filesystem temp-store, external effect or application orchestration.
3. Cleanup is explicit and caller-invoked; no background loop, retry or scheduler.
4. Persisted corruption fails the entire sweep as `INVARIANT_VIOLATION`; the transaction rolls back rather than normalizing corrupt history.
5. Content safety remains owned by P2.4b/P2.5. P2.6a may cascade-delete content only as a consequence of deleting a fully terminal-safe old job group.
6. P2.6a never deletes controller/runtime/settings/live dialogue rows.

## Retention horizon

Initial V1 metadata horizon is frozen to seven days:

`METADATA_RETENTION_MS = 604_800_000`

For timestamps without their own explicit expiry, the sweep computes:

`cutoff = max(0, now_ms - METADATA_RETENTION_MS)`

The repository clock is called exactly once per successful sweep.

Tombstones already carry their own explicit `expires_at_ms`; they are eligible when `expires_at_ms <= now_ms` and do not receive an additional seven-day delay.

## Public repository

P2.6a exposes only:

`MetadataRetentionRepository.sweep(limit)`

`limit` is an exact non-bool integer in `1..1000`.

The same `limit` is an independent maximum for each root cleanup category in one sweep:

- terminal job groups;
- standalone ingress rows;
- callback-action rows;
- deletion tombstones;
- error fingerprints.

This bounds each category and avoids one large category starving all others. Cascaded child rows from a selected terminal job group are counted factually but are not separate root-budget units.

## Sweep result

`MetadataRetentionSweepResult` is immutable and contains exact counts:

- `terminal_jobs_deleted`;
- `payloads_deleted`;
- `delivery_segments_deleted`;
- `approvals_deleted`;
- `ingress_deleted`;
- `callback_actions_deleted`;
- `tombstones_deleted`;
- `errors_deleted`.

No content or raw identifiers beyond ordinary safe record IDs are returned.

## Terminal job-group cleanup

Only turn jobs in `DELIVERED` or `FAILED` may be removed.

Eligibility requires all of the following:

1. canonical job materialization and exact live dialogue/server/profile/thread binding;
2. job `updated_at_ms <= cutoff`;
3. exact accepted P2.5 terminal-delivery coherence:
   - `DELIVERED` has a non-empty all-CONFIRMED delivery plan;
   - Codex-level `FAILED` may have zero delivery rows;
   - delivery-owned `FAILED` has exact `C*FP*` delivery rows;
4. no PENDING approval for the job;
5. the job's exact `ingress_updates` row exists, materializes as `JOB:<job_id>`, has `update_id == job.telegram_update_id`, has terminal `completed_at_ms`, and `completed_at_ms <= cutoff`.

If an existing job lacks or mismatches its required JOB ingress, the database is corrupt and the sweep fails `INVARIANT_VIOLATION`.

For each selected eligible job group, the same transaction counts and then deletes the exact corresponding JOB ingress and the job row. Schema cascades may remove that job's remaining transient payloads, delivery segments and approvals. Error rows survive with FK references cleared. The live dialogue remains.

Deleting job+ingress together intentionally defines the finite seven-day duplicate-replay horizon for completed work; P2.6a never leaves an old `JOB:<id>` ingress pointing at a job it itself removed.

## Standalone ingress cleanup

After terminal job-group deletions, P2.6a may delete up to `limit` additional terminal ingress rows with `completed_at_ms <= cutoff`:

- `CONTROL`;
- `IGNORED_SLEEP`;
- `IGNORED_UNAUTHORIZED`;
- `JOB:<id>` only when the referenced job no longer exists, as expected after confirmed hard delete or a prior accepted terminal job-group cleanup.

If a JOB ingress references an existing job, it is not deleted by the standalone phase. If it references an existing job but disagrees with that job's `telegram_update_id`/job identity, fail `INVARIANT_VIOLATION`.

Rows with `completed_at_ms IS NULL` are recovery-critical and are never deleted.

Control safety does not depend on retained old CONTROL ingress because `controller_runtime.last_control_epoch` remains authoritative; replay after the retention horizon is still stale by epoch.

## Callback-action cleanup

A callback row is eligible only when its declared `expires_at_ms <= cutoff`.

Both consumed and never-consumed expired callbacks may then be deleted. Keeping them for the full seven-day horizon after declared expiry prevents early hash reuse while an old callback could still be considered within its declared lifetime.

Fresh/unexpired callbacks are never deleted.

Before deletion every selected callback row must materialize canonically under accepted P2.3 rules; corrupt rows fail the whole sweep.

Deleting an old callback changes later replay from EXPIRED/ALREADY_CONSUMED to NOT_FOUND, which remains fail-closed and performs no subject effect.

## Deletion tombstone cleanup

A canonical tombstone is eligible when:

`expires_at_ms <= now_ms`.

P2.6a may delete at most `limit` expired tombstones per sweep in deterministic order `(expires_at_ms, dialogue_id)`.

Live dialogue rows with the same dialogue ID are impossible under accepted P2.5 history; if one exists alongside a tombstone, fail `INVARIANT_VIOLATION` rather than deleting evidence of corruption.

## Error fingerprint cleanup

A canonical error row is eligible when:

`last_seen_at_ms <= cutoff`.

It may be deleted whether entity references are NULL or still point to canonical live entities; errors are diagnostic metadata and are not recovery authority. The state rows themselves retain their sanitized error classes where needed.

Semantic case-alias corruption remains fail-closed: candidate lookup/materialization must not silently choose one case variant.

At most `limit` error rows are removed per sweep in deterministic order `(last_seen_at_ms, fingerprint_sha256)`.

## Deterministic ordering and atomicity

Each root category uses deterministic oldest-first ordering and applies its own `LIMIT` only after eligibility/protection predicates.

The entire multi-category sweep is one SQLite write transaction and one clock. Any invariant/storage failure rolls back every deletion/count in that sweep.

Repeated cancellation after transaction submission remains attached under accepted P2.1 ownership and must not create a second sweep.

## Restart semantics

There is no authoritative retention cache. Close/reopen between sweeps must preserve exact remaining rows and a later sweep continues from durable state only.

## Out of scope

P2.6a does not implement:

- crash/restart/idempotency acceptance harness across all state-machine windows (P2.6b);
- DELETE_UNKNOWN/TURN_UNKNOWN reconciliation;
- Telegram/Codex application service;
- filesystem temp-store implementation;
- real production retention scheduling;
- schema migration;
- P3 or later orchestration.
