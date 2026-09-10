# ADR-0044 — Durable local containment authority and P7.C4 cleanup orchestration

Status: Accepted
Date: 2026-09-10

## Context

ADR-0043 selected a dedicated persistent Codex profile home plus a distinct disposable SQLite/log state root. P7.C2 added durable `DELETE_CONFIRMED_PENDING_STORAGE`, ensuring exact upstream `DELETE_CONFIRMED` is persisted while the full dialogue/profile/thread binding remains available. P7.C3 added exact profile/storage routing, protected path authority, runtime reservation/quiescence and descriptor-bounded isolated-root recreation.

P7.C4 must now compose those accepted primitives. Two delete outcomes require intentionally different local behavior:

1. `DELETE_CONFIRMED_PENDING_STORAGE`: upstream deletion is known to be confirmed; local finalization is permitted only after all local storage gates succeed.
2. `DELETE_UNKNOWN`: upstream deletion is permanently ambiguous under ADR-0016; local isolated-root containment may improve local security but must never be represented as upstream success or as a deletion tombstone.

Schema v3 has no durable field representing local containment under official UNKNOWN. Reusing `last_error_class`, the dialogue state, or `deletion_tombstones` would collapse distinct authorities and is rejected.

## Decision

P7.C4 adds one additive schema-v4 metadata table and one local cleanup coordinator. P1.9 external delete semantics remain unchanged. No new dialogue state is added.

### Schema-v4 authority

Current schema becomes v4. Historical schema-v1, schema-v2 and schema-v3 SQL/canonical forms/hashes are immutable.

Migration ID:

`0004_delete_local_containment`

The sole v4 DDL statement is:

```sql
CREATE TABLE delete_storage_containment (
    dialogue_id TEXT PRIMARY KEY REFERENCES dialogues(dialogue_id) ON DELETE CASCADE,
    profile_id TEXT NOT NULL CHECK (length(profile_id) BETWEEN 1 AND 128),
    thread_identity_sha256 TEXT NOT NULL CHECK (length(thread_identity_sha256) = 64),
    dialogue_version INTEGER NOT NULL CHECK (dialogue_version >= 0),
    official_delete_authority TEXT NOT NULL CHECK (official_delete_authority = 'UNKNOWN'),
    local_isolated_storage_containment TEXT NOT NULL CHECK (local_isolated_storage_containment = 'COMPLETED'),
    contained_at_ms INTEGER NOT NULL CHECK (contained_at_ms >= 0)
)
```

Using the repository's accepted canonicalization function, the frozen v4 migration SHA-256 is:

`400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`

No index is required for V1's one-live-dialogue invariant. No existing table rebuild is authorized.

Migration requirements:

- v0→v1→v2→v3→v4;
- v1→v2→v3→v4;
- v2→v3→v4;
- v3→v4;
- v4 reopen performs no migration clock call;
- v4 failure rolls back to exact valid v3 and a later retry succeeds;
- forged/malformed v1/v2/v3 authority is rejected before v4 mutation;
- foreign keys remain enabled;
- historical v1/v2/v3 migration hashes and statements remain unchanged.

### Durable UNKNOWN containment record

A `delete_storage_containment` row exists only for a live canonical `DELETE_UNKNOWN` dialogue.

Its exact semantics are:

`OFFICIAL_DELETE_AUTHORITY=UNKNOWN`

and independently:

`LOCAL_ISOLATED_STORAGE_CONTAINMENT=COMPLETED`

The row stores no raw thread identity. `thread_identity_sha256` is SHA-256 of the exact retained `thread_id`; `dialogue_version` and `profile_id` bind the fact to the exact live UNKNOWN generation/profile.

The repository may create the row only after isolated-root recreation has returned success under the accepted P7.C3 reservation/quiescence authority. Before insert it must prove:

- exact dialogue ID/version;
- state is `DELETE_UNKNOWN`;
- exact bound profile/thread exist;
- `last_error_class == "DELETE_UNKNOWN"`;
- no active job;
- no tombstone;
- no conflicting containment row.

An already-present exact row is idempotent replay authority. Any mismatched row is an invariant failure. The dialogue remains `DELETE_UNKNOWN`; its raw binding is retained; no dialogue version increment is required merely to record local containment.

A containment row for any non-`DELETE_UNKNOWN` dialogue is invalid. `finalize_confirmed()` must reject a containment-row collision rather than silently treating an UNKNOWN-containment fact as confirmed cleanup. The row is removed only by its FK cascade if a separately authorized future resolution actually removes the live dialogue.

### Confirmed cleanup sequence

For `DELETE_CONFIRMED_PENDING_STORAGE`, the cleanup coordinator performs no P1.9 method and no external Codex business RPC.

Exact sequence:

1. Resolve the exact live pending dialogue and profile/thread binding from durable storage.
2. Acquire or reuse the coordinator-owned exact P7.C3 profile reservation.
3. Explicitly `shutdown_profile(profile_id)` and require exact quiescence: reserved=yes, STARTING=no, READY/runtime=no, unresolved=no.
4. Recreate the exact configured isolated state root through the accepted manager-owned P7.C3 primitive. This destroys/recreates the complete disposable SQLite/log boundary only.
5. While the reservation remains held, run the read-only persistent-profile residual gate for the exact retained thread identity.
6. The persistent gate scans only dialogue-bearing persistent profile families accepted for C4: `CODEX_HOME/sessions/**` and `CODEX_HOME/history.jsonl` when present. It never opens `auth.json`, credential stores, keyrings or arbitrary config files.
7. Require zero exact thread-identity matches and zero scan/ownership/symlink/special-file/limit errors. `history.persistence="none"` remains the accepted runtime launch policy; this scan does not claim session persistence is disabled.
8. Only after all gates pass invoke accepted `DeletionRepository.finalize_confirmed()` with the exact current pending version and bounded tombstone expiry.
9. Validate the returned tombstone/finalization result, then release the profile reservation.

If any step before finalization fails, the dialogue remains `DELETE_CONFIRMED_PENDING_STORAGE` with full exact binding and no tombstone/purge. The coordinator retains the profile reservation for the remainder of the process so the failed/pending profile cannot be reused. A later local retry or startup recovery may repeat only local cleanup; it never redispatches delete/read/list.

If finalization encounters a concurrent exact tombstone already produced by another accepted local cleanup owner, replay may return the existing tombstone only after proving there is no live dialogue and the tombstone matches the requested dialogue identity. No upstream effect is repeated.

### Persistent profile residual gate

P7.C4 introduces a bounded, content-silent scanner for the exact thread identity.

The scanner:

- resolves the configured persistent home through accepted path authority;
- follows no symlinks;
- reads no credential content;
- scans regular files under `sessions/` and the regular `history.jsonl` file when present;
- checks relative names and file bytes for the exact thread identity, including chunk-boundary matches;
- has finite file-count and byte-count limits and fails closed rather than skipping overflow;
- rejects unsafe ownership, writable/symlink/special entries and any I/O/scan error;
- returns only aggregate safe counts/status, never file contents or raw matched paths.

A confirmed cleanup cannot finalize when a persistent exact-thread residual is found. P7.C4 does not manually delete persistent session/rollout/history files to manufacture a pass.

Full synthetic material-marker proof across all families remains P7.C5/P7.C6 acceptance scope.

### DELETE_UNKNOWN local containment sequence

For live `DELETE_UNKNOWN`, official status remains UNKNOWN forever under this lane. No `thread/delete`, `thread/read`, `thread/list`, notification inference or external reconciliation is allowed.

The local coordinator:

1. resolves the exact UNKNOWN binding;
2. acquires/reuses an exact profile reservation;
3. shuts down the owned runtime and proves quiescence;
4. recreates the exact isolated state root through P7.C3;
5. atomically records the exact v4 containment row;
6. retains the reservation as an in-process quarantine and returns an UNKNOWN result with local containment complete.

It does not scan-and-delete persistent session material, does not finalize the dialogue, does not create a tombstone, and does not remove the binding.

If containment fails, the dialogue remains UNKNOWN without a completed containment row and the acquired reservation remains held. If a completed row already exists after restart, startup still re-establishes profile reservation/quiescence and validates/recreates the isolated root before treating the current process as quarantined; the durable row is historical proof of prior local containment, not permission to run the profile again.

There is no P7.C4 operator action that releases UNKNOWN quarantine. A future operator-resolution design requires separate architect authority.

### Coordinator ownership and concurrency

One process-local cleanup coordinator owns cleanup tasks/reservations for the live dialogue/profile. Concurrent calls for the same dialogue coalesce or one returns a finite busy/pending result; they must not produce duplicate root recreations/finalizers.

A reservation held because of confirmed-pending failure or UNKNOWN quarantine is never silently released by an ordinary retry. Process exit naturally destroys the in-memory token; startup recovery re-establishes it before normal ingress is enabled.

### Dialogue-delete composition

`DialogueDeleteService` may receive the local cleanup coordinator as an optional local-only port.

With the port configured:

- exact external `DELETE_CONFIRMED` is first persisted as `DELETE_CONFIRMED_PENDING_STORAGE`, then local cleanup is attempted; successful local cleanup returns the existing truthful `DELETED`/tombstone shape; cleanup failure returns `CONFIRMED_PENDING_STORAGE` and never UNKNOWN solely because local cleanup failed;
- external ambiguous/non-success is first durably marked `DELETE_UNKNOWN`, then local containment may run; the returned official status remains `UNKNOWN` regardless of whether local containment completed;
- replay from confirmed-pending may resume local cleanup with zero P1 calls;
- replay from UNKNOWN may establish/verify local containment with zero P1 calls and still returns UNKNOWN.

Without the optional C4 port, accepted P7.C2 behavior remains unchanged for lower-level tests.

### Startup recovery composition

`DialogueRecoveryService` may receive the same local cleanup port.

With it configured:

- pre-existing `DELETING` first becomes durable `DELETE_UNKNOWN`, then may run UNKNOWN local containment; zero P1 calls;
- pre-existing `DELETE_CONFIRMED_PENDING_STORAGE` runs local cleanup/finalization only; zero P1 calls;
- pre-existing `DELETE_UNKNOWN` re-establishes quarantine and local isolated-root containment only; zero P1 calls;
- an already finalized tombstone remains final replay authority.

Startup cleanup must complete or reach a finite quarantined/pending result before normal work admission is enabled for that profile.

### Crash boundaries

Required crash/restart semantics:

- crash before root recreation: restart repeats local cleanup only;
- crash during/after root recreation but before confirmed finalizer: pending state survives; restart may idempotently recreate again and never calls P1.9;
- crash after confirmed finalizer commit: tombstone is authoritative; no cleanup/delete replay is required;
- crash after UNKNOWN root recreation but before v4 row insert: restart recreates again, records containment, remains UNKNOWN;
- crash after UNKNOWN containment-row insert: restart re-establishes reservation and local root containment, leaves row/id/binding unchanged;
- no crash point converts UNKNOWN to confirmed/deleted.

### Safety boundaries

P7.C4 performs no real Codex acceptance experiment. All application/runtime/storage proof uses fake ports and synthetic temporary filesystems.

Forbidden in P7.C4:

- real model/thread/turn/delete/read/list/interrupt/approval business effects;
- retry/reconciliation of the retained historical P7 UNKNOWN delete;
- credential content reads/copies/symlinks;
- persistent session deletion;
- manual SQLite row surgery in Codex-owned state databases;
- P7.C5/P7.C6 real/final acceptance;
- P8/P9.

## Acceptance consequence

P7.C3 is architect accepted. P7.C4 is the sole executable next slice. P7.C5/P7.C6 and P8/P9 remain blocked until their respective gates.