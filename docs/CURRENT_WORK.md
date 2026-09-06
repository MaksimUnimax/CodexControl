# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- P2.4a accepted: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- P2.4b accepted: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- P2.5 accepted after one repair: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0023 remain accepted authority for storage/core/idempotency/turn/delivery/approval/delete/error semantics.
- ADR-0024 is binding P2.6a bounded metadata-retention authority.

## Accepted P2.5 facts
- Hard-delete intent is durable before external effect: only canonical IDLE with exact version, bound thread, no tombstone collision, no pending approval and terminal-safe retained job history may enter DELETE_PENDING.
- Terminal-safe history is fail-closed against accepted P2.4b delivery coherence: DELIVERED requires non-empty all-CONFIRMED delivery rows; Codex FAILED may have no delivery rows; delivery-owned FAILED requires exact `C*FP*`.
- DELETE_PENDING->DELETING rechecks readiness and tombstone collision before exposing the exact durable profile/thread binding for later P1.9 use.
- DELETE_UNKNOWN/ERROR retain the exact binding and sanitized class; P2.5 has no retry/reconciliation API.
- Confirmed local finalization computes SHA-256 from the raw thread ID, records current DELETING version as stale generation, inserts a content-free tombstone, deletes the exact live dialogue and cascades jobs/payloads/delivery/approvals in one transaction.
- Ingress/callback idempotency rows and sanitized errors remain after hard delete; error entity references clear through FK.
- Error-fingerprint semantic aliases are fail-closed; exact duplicates increment once, mismatched class/entity bindings do not merge.
- Final P2.5 proof: unit 4, integration 18, full `418 + 4 + 18 = 440`; prior regressions/security/scope checks passed.

## P2.6 split
The remaining P2 work is split into two architect-owned slices for reviewability:

- **P2.6a** — bounded non-content metadata retention/hygiene.
- **P2.6b** — crash/restart/idempotency harness and final P2 acceptance.

P2.6b does not start until P2.6a is independently accepted.

## P2.6a exact architect authority
P2.6a implements only **explicit bounded cleanup of old terminal metadata that intentionally survived earlier P2 slices**.

Binding source: `docs/adr/0024-bounded-metadata-retention.md` plus accepted ADR-0017..0023, `docs/OBSERVABILITY_AND_RETENTION.md`, `docs/DATA_MODEL.md`, `docs/STATE_MACHINES.md` and security/test authority.

### Retention horizon
- `METADATA_RETENTION_MS = 604800000` (seven days).
- One validated repository clock per successful sweep.
- For non-explicit-expiry metadata: `cutoff=max(0, now-METADATA_RETENTION_MS)`.
- Tombstones use their explicit `expires_at_ms` directly.

### Repository surface
- New `MetadataRetentionRepository.sweep(limit)` only.
- `limit` is exact non-bool integer `1..1000`.
- The same limit is an independent per-category root budget for terminal job groups, standalone ingress, callbacks, tombstones and errors.
- One sweep is one SQLite write transaction. Any corruption/storage failure rolls back all categories.

### Terminal job groups
- Only canonical `DELIVERED|FAILED` jobs are eligible.
- Job and exact JOB ingress must both be at least seven days old.
- DELIVERED requires accepted all-CONFIRMED delivery coherence.
- Codex FAILED may have zero delivery rows; delivery-owned FAILED requires exact `C*FP*`.
- No PENDING approval may remain.
- Existing job without exact `JOB:<job_id>` ingress/update identity is corruption.
- Eligible cleanup deletes exact job+JOB ingress together; job FK cascades may remove remaining terminal payload/delivery/approval rows while the live dialogue remains.
- Error rows survive with entity refs nulled.

### Standalone ingress
- Completed CONTROL/IGNORED rows older than cutoff may be deleted.
- Old JOB ingress may be deleted only when its job no longer exists, e.g. after confirmed hard delete.
- JOB ingress for an existing job is never deleted standalone.
- `completed_at_ms IS NULL` is recovery-critical and protected.

### Callback actions
- Delete only when declared `expires_at_ms <= cutoff`.
- Consumed or unconsumed expired rows are then eligible.
- Fresh/unexpired callbacks remain.
- Later replay becoming NOT_FOUND is fail-closed.

### Tombstones
- Delete canonical tombstones only when `expires_at_ms <= now`.
- A live dialogue with the same dialogue ID is corruption and blocks tombstone cleanup.

### Error fingerprints
- Delete canonical error rows when `last_seen_at_ms <= cutoff`.
- Live or NULL entity references are both allowed; fingerprint rows are diagnostics, not recovery authority.
- Semantic case-alias corruption remains fail-closed.

### Forbidden P2.6a scope
No P2.6b crash harness, UNKNOWN reconciliation, P3 policy, Codex/Telegram effects, production scheduling, filesystem temp-store implementation, schema migration or production state.

## Execution authority
Codex must not self-start work from this document.

Only **P2.6a — bounded metadata retention** is eligible for the next explicit implementation prompt.
