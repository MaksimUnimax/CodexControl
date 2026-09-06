# P2.C1 architect acceptance — 2026-09-06

Architect-owned acceptance record.

## Accepted correction

Accepted P2.C1 implementation:

`4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`

Architect base:

`166a78ea42c17905c8ef9b0b39693fac43884526`

Issue: #20.

Binding authority: ADR-0027.

## Defect closed

Historical P2.4a duplicate reconstruction required an exact retained INPUT for every JOB replay, while accepted P2.4b retention legally removes expired INPUT once a job leaves `RECEIVED|CLAIMED|CODEX_STARTING|CODEX_RUNNING`. Terminal job and JOB-ingress metadata may remain longer under P2.6a. That made a legal same-update replay fail as `INVARIANT_VIOLATION` after transient content retention.

P2.C1 corrects only the duplicate reconstruction rule.

## Accepted semantics

INPUT remains mandatory for duplicate reconstruction in exactly:

- `RECEIVED`
- `CLAIMED`
- `CODEX_STARTING`
- `CODEX_RUNNING`

Missing INPUT is retention-compatible in exactly:

- `CODEX_COMPLETED`
- `FAILED`
- `UNKNOWN`
- `DELIVERY_PENDING`
- `DELIVERING`
- `DELIVERED`
- `DELIVERY_UNKNOWN`

For those optional states, `TurnJobRepository.claim_ingress(...)` may return the exact durable `DUPLICATE` job/ingress with `input_payload=None`. It performs no clock call, no mutation, no reconstruction and no second job creation.

If an INPUT is still present in any state, it remains strict: exactly one canonical INPUT with exact job/dialogue ownership and exact stored job hash. Multiple/corrupt/mismatched INPUT remains `INVARIANT_VIOLATION`.

`TransientPayloadRepository.get_input_for_job()` remains unchanged: missing retained INPUT is `NOT_FOUND`. `claim_turn()` remains unchanged: `RECEIVED` with missing INPUT is invariant.

## Independent review

The candidate diff from the exact architect base is one commit and changes only:

- `src/codex_control/storage/turn_job_repositories.py`;
- new P2.C1 integration/acceptance tests;
- factual P2.C1 evidence.

The production helper uses exact required/optional `TurnJobState` sets, returns `None` only when no INPUT exists in an optional state, and still materializes/validates an existing INPUT through accepted payload authority.

The primary cross-slice test performs a real `RetentionRepository.sweep`, proves INPUT deletion while the exact job and JOB ingress remain, then replays the same update with different caller fields and obtains `DUPLICATE`, the exact original job/ingress and `input_payload=None` with a raising clock untouched. The suite also proves all 7 optional states, all 4 required states, canonical/corrupt/multiple INPUT behavior, unchanged `get_input_for_job`, and unchanged `claim_turn` strictness.

## Test authority

New correction tests:

- P2.C1 integration: 5
- P2.C1 acceptance: 1

Historical accepted full suite: 500.

Corrected full suite:

`500 + 5 + 1 = 506`

Observed: 506 passing tests.

All accepted P2.1–P2.6b and P1 focused regressions remained green at their accepted counts. Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Security and effects

No real Codex, Telegram or network effect; temporary SQLite only; no production DB/state/service; no schema/DDL/public repository API/retention-policy change; no P3 source change.

## Architect result

`P2_C1_ARCHITECT_ACCEPTANCE=PASS`

P2 durable authority is now the historical final P2 acceptance plus this accepted ADR-0027 correction. P3.1 may resume only from an architect base containing P2.C1; rejected P3.1 candidate `05a268781b4b7189271b64f55a3b21f30c259269` remains reference material only and is not merged.