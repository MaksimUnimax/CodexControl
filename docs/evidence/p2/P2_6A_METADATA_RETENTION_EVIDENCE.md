# P2.6a implementation evidence — bounded metadata retention

This is factual implementation evidence only. It does not claim architect
acceptance, close Issue #17, or authorize later roadmap work.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Base SHA: `6892f8060e2465350c1f4261a88fe6754e3e4b4c`
- Branch: `impl-p2-6a-metadata-retention-2026-09-06`
- Issue: `#17`
- Binding ADR: `docs/adr/0024-bounded-metadata-retention.md`
- Accepted P2.1: `61301fd25ff7253693f367664ce99e13dfc88446`
- Accepted P2.2: `5187c080a7188a59989013defe7d07075662d007`
- Accepted P2.3: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`
- Accepted P2.4a: `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- Accepted P2.4b: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`
- Accepted P2.5: `87ef37cf245d79f6d20b507b13c0f36014c1580f`
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Public retention contract

`METADATA_RETENTION_MS` is the fixed value `604800000`.
`MetadataRetentionSweepResult` is a frozen dataclass containing only the eight
specified physical deletion counts. `MetadataRetentionRepository` exposes only
`sweep(limit)` and has a redacted representation. Limits are exact non-bool
integers from 1 through 1000.

Each successful sweep calls its injected clock once, derives
`cutoff=max(0, now-METADATA_RETENTION_MS)`, and uses one SQLite write
transaction. Empty sweeps also use one clock. Clock failures normalize to
`CLOCK_INVALID` without exposing the clock exception.

## Cleanup behavior

- Terminal jobs: canonical `DELIVERED` and `FAILED` roots are selected oldest
  first only when the job and exact canonical `JOB:<job_id>` ingress are at
  least seven days old. Accepted delivery coherence, live dialogue binding,
  child payloads, delivery segments and approvals are materialized before the
  exact guarded job/ingress delete. Codex-level FAILED with no delivery rows
  and delivery-owned `C*FP*` FAILED histories are supported. Recovery-critical
  states are not selected.
- Protection and selection: young jobs/ingresses and canonical PENDING
  approvals retain the job and exact JOB ingress. Eligibility is determined
  before the per-category limit so a protected older root does not starve a
  later eligible root. Child counts are factual FK-cascade counts; the live
  dialogue remains.
- Ingress: completed CONTROL, IGNORED_SLEEP, IGNORED_UNAUTHORIZED and orphan
  JOB rows are cleaned oldest first, while incomplete and existing-job JOB
  rows remain. Existing-job identity mismatches fail closed. Controller epoch
  and requested mode are not mutated.
- Callbacks: both consumed and never-consumed actions are eligible only when
  declared expiry is at or before the seven-day cutoff. Canonical materializer
  and ASCII case-alias checks run before deletion; replay after deletion is
  fail-closed NOT_FOUND.
- Tombstones: canonical rows are selected by `(expires_at_ms, dialogue_id)`
  when their explicit expiry is at or before `now`. A live same-ID dialogue is
  an invariant failure.
- Errors: canonical fingerprints are selected by
  `(last_seen_at_ms, fingerprint_sha256)` at or before cutoff. NULL/live FK
  references are allowed as diagnostic metadata; job deletion leaves retained
  error references NULL. Error class, timestamp, fingerprint and semantic
  case-alias validation remains fail-closed.

The root limit is independent for terminal jobs, standalone ingress, callback
actions, tombstones and errors. The entire ordered sweep rolls back on any
repository/storage/invariant failure, including corruption discovered in a
later category. Reopening the database and constructing a new repository uses
durable state with no retention cache. Submitted sweeps retain SQLite
transaction ownership across repeated caller cancellation.

## Validation

- P2.6a unit: `4`
- P2.6a integration: `10`
- Accepted prior P2.5: `4 / 18`
- Accepted prior P2.4b: `6 / 25`
- Accepted prior P2.4a: `8 / 31`
- Accepted prior P2.3: `7 / 28`
- Accepted prior P2.2: `6 / 20`
- Accepted prior P2.1: `8 / 31`
- P1.10 T0/T1/T2: `6 / 1 / 4`
- `BASE_ACCEPTED_FULL_TESTS=440`
- `EXPECTED_FULL_TESTS=440 + 4 + 10 = 454`
- `OBSERVED_FULL_TESTS=454`, all passing

Focused tests cover terminal DELIVERED/FAILED cleanup and exact child counts,
pending approval and young-ingress protection, anti-starvation, standalone
ingress and control epoch preservation, callback expiry and aliases, tombstone
expiry/live-dialogue collision, error FK/case behavior, independent limits,
whole-sweep rollback, repeated cancellation, clock failure redaction and
restart/no-cache behavior.

Compileall, required public import, frozen DDL hash, `git diff --check`, prior
P2 regressions, P1.10 and existing focused P1 suites passed. The known
pre-existing P1.6 pending-task warning was observed; no P2.6a warning was
observed and `P1_6_WARNING_INTRODUCED_BY_P2_6A=NO`.

## Scope and security facts

Production implementation changes are limited to the new metadata-retention
module and the storage package exports. Focused tests use temporary SQLite
databases. No schema/DDL, accepted prior production repository, architecture
authority file, Telegram/Codex effect, network call, service, deployment,
production DB/state, credential, token, prompt/response, raw event, traceback,
stdout/stderr or environment dump was added. P2.6b is NOT STARTED.
