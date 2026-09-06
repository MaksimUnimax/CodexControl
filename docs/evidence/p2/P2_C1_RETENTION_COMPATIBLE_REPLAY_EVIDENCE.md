# P2.C1 retention-compatible JOB replay evidence

Date: 2026-09-06

## Authority and base

- Architect base: `166a78ea42c17905c8ef9b0b39693fac43884526`
- Issue: #20
- Binding authority: ADR-0027, `docs/adr/0027-retention-compatible-job-replay.md`
- Historical final P2: `9db97f0dda109b4d0c0ecfa5f167733905df2766`
- Blocked review authority: Issue #19 comment `5557727431`

P3.1 remains blocked. This evidence does not claim architect acceptance and
does not begin P3.1 or P3.2 work.

## Defect sequence

The prior duplicate JOB replay path required exactly one canonical INPUT and
classified a missing row as `INVARIANT_VIOLATION`. Accepted P2.4b retention
legally deletes expired INPUT after a job leaves the four active turn states,
while accepted P2.6a retains terminal job and JOB-ingress metadata. Thus a
same-update replay could reach an exact retained job and ingress with no INPUT
content and fail incorrectly.

## Correction

Production file changed only:

`src/codex_control/storage/turn_job_repositories.py`

The existing JOB-ingress duplicate branch now uses a private retention-aware
INPUT materializer. It reads all INPUT rows for the exact job, rejects more
than one row, materializes one row through `_materialize_payload`, and checks
kind, job owner, dialogue owner and the job input hash. With zero rows it
rejects exactly the four INPUT-required states and returns `None` exactly for
the seven ADR-0027 INPUT-optional states. It never synthesizes content.

Required states exactly:

`RECEIVED`, `CLAIMED`, `CODEX_STARTING`, `CODEX_RUNNING`

Optional states exactly:

`CODEX_COMPLETED`, `FAILED`, `UNKNOWN`, `DELIVERY_PENDING`, `DELIVERING`,
`DELIVERED`, `DELIVERY_UNKNOWN`

The result remains `DUPLICATE` with the exact durable ingress and job. Missing
INPUT is represented as `input_payload=None` only in the optional states.

## Cross-slice retention proof

The dedicated temporary-SQLite integration test creates a canonical IDLE
dialogue, claims a JOB ingress, claims the turn, advances through
`CODEX_STARTING` and `CODEX_RUNNING`, finishes `CODEX_COMPLETED`, makes INPUT
expired, and deletes it through the accepted `RetentionRepository.sweep`.
The exact job and JOB ingress remain. Replaying the same update with different
caller IDs, source metadata, model/effort and payload/content arguments returns
`DUPLICATE`, the exact original job and ingress, and `input_payload=None`.

The acceptance supplement binds the same sequence at P2 acceptance level and
proves one durable job, one JOB ingress, zero INPUT rows, no replacement job,
no replacement payload and no second effect claim.

## Matrix and regressions

- Optional-state matrix: all 7 states pass with legal missing INPUT and
  `input_payload=None`.
- Active-state matrix: all 4 states pass with missing INPUT as
  `INVARIANT_VIOLATION`.
- Existing canonical INPUT is returned exactly on duplicate.
- Content/hash mismatch, owner mismatch and multiple INPUT rows fail closed
  as `INVARIANT_VIOLATION`.
- `TransientPayloadRepository.get_input_for_job` remains unchanged: legal
  retention deletion returns `NOT_FOUND`; corruption remains invariant.
- `claim_turn` remains unchanged: RECEIVED with missing INPUT is invariant,
  with the job still RECEIVED and dialogue still IDLE.
- Duplicate paths call the clock zero times and perform no mutation.

## Gates

Frozen DDL SHA remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

Focused tests passed at the required counts:

- P2.6b acceptance: 5 contract, 12 restart, 8 replay, 3 abrupt-process.
- P2.6a: 4 unit / 28 integration.
- P2.5: 4 unit / 18 integration.
- P2.4b: 6 unit / 25 integration.
- P2.4a: 8 unit / 31 integration.
- P2.3: 7 unit / 28 integration.
- P2.2: 6 unit / 20 integration.
- P2.1: 8 unit / 31 integration.
- P1.10: T0 6 / T1 1 / T2 4.
- New P2.C1 tests: 5 integration / 1 acceptance.

Compile and schema import checks passed. Full discovery passed with:

`500 + 6 = 506`

Observed: 506 passing tests.

## Security and effects

All correction tests use temporary SQLite and deterministic harmless labels.
There was no real Codex call, Telegram call, network/business effect,
production database or production state-root access, service change, secret,
credential or raw production content. No schema, DDL, retention policy,
public API, adapter, application or P3 source was changed.

The known pre-existing P1.6 pending-task warning was observed during the
focused P1 adapter run; no new leak was attributed to P2.C1.
