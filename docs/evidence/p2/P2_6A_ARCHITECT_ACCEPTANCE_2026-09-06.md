# P2.6a architect acceptance — 2026-09-06

Architect acceptance authority for P2.6a.

## Accepted implementation

- Architect base: `6892f8060e2465350c1f4261a88fe6754e3e4b4c`
- Initial candidate: `c01f9b4316ab0a507b15854b6dea1d7ab437ac4b`
- Accepted implementation/proof HEAD after one repair: `e6f59739b3091d00894d3434abb5a99e2af72885`
- Branch: `impl-p2-6a-metadata-retention-2026-09-06`
- Issue: #17
- Binding ADR: ADR-0024

The initial candidate was rejected until generic job-only payload ownership and genuinely bounded root selection were repaired and the missing destructive-retention proofs were committed.

## Accepted durable boundary

- `METADATA_RETENTION_MS` is fixed at `604800000`; `MetadataRetentionRepository.sweep(limit)` is explicit, one-clock and one-transaction, with an exact non-bool `1..1000` independent root limit per cleanup category.
- Terminal metadata cleanup is limited to canonical old `DELIVERED|FAILED` job groups. Job and exact `JOB:<job_id>` ingress are deleted together only after live-dialogue binding, accepted delivery coherence, old completed ingress and no-PENDING-approval protection are satisfied.
- Canonical generic job-owned payloads may have `dialogue_id=NULL`; INPUT ownership remains the accepted P2.4a two-owner/hash contract. Job FK cascades are counted factually and the live dialogue remains.
- Ordinary eligibility/protection is applied in SQL before deterministic root `LIMIT`; root populations are not fetched/materialized unboundedly. Narrow corruption probes return bounded evidence only.
- Standalone old completed CONTROL/ignored/orphan-JOB ingress cleanup is fail-closed on existing-job identity corruption. Incomplete ingress remains recovery authority and controller epoch/mode is never reset by retention.
- Callback cleanup uses declared expiry plus the seven-day horizon and preserves semantic hash case-alias fail-closed behavior. Tombstones use their own explicit expiry and reject live-dialogue collisions. Error fingerprints use their seven-day last-seen horizon and preserve semantic alias/canonical materialization rules.
- All five root categories share one SQLite write transaction. Corruption in a later category rolls back earlier job/ingress/child deletions. Repeated post-submission cancellation remains attached under P2.1 ownership.
- Retention has no authoritative cache; close/reopen continues from durable rows only. It never deletes controller runtime, settings or live dialogues and performs no UNKNOWN reconciliation or external effect.

## Acceptance proof

Final focused counts reviewed:

- P2.6a unit: 4
- P2.6a integration: 28
- Accepted pre-P2.6a full suite: 440
- Expected/observed full suite: `440 + 4 + 28 = 472`
- P2.5 unit/integration: 4 / 18
- P2.4b: 6 / 25
- P2.4a: 8 / 31
- P2.3: 7 / 28
- P2.2: 6 / 20
- P2.1: 8 / 31
- P1.10 T0/T1/T2: 6 / 1 / 4

Repair proof includes bounded SQL selection/materialization, job-only payload cascade counting, delivery-owned FAILED cleanup, accepted P2.5 hard-delete orphan ingress cleanup, missing/mismatched JOB-ingress corruption, incomplete ingress protection, callback consumed/recent/unexpired and dual-case paths, corrupt-tombstone whole-sweep rollback, independent category limits, deterministic oldest-first progress, meaningful repeated-cancellation cleanup, one-clock empty/non-empty sweeps, active/recovery job protection, error FK clearing and controller/settings/dialogue preservation.

The known P1.6 pending-task warning was observed and was not introduced by P2.6a.

## Security / scope

- Schema-v1 DDL SHA remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- No accepted prior production repository was changed.
- No runtime dependency, production database/state root, scheduler, service, secret, real Telegram call, real Codex call or network effect was introduced.
- P2.6b crash/restart/idempotency acceptance was not started by the executor.

P2.6a is architect-accepted at `e6f59739b3091d00894d3434abb5a99e2af72885`.