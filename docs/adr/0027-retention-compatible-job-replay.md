# ADR-0027 — Retention-compatible JOB duplicate replay

Status: accepted
Date: 2026-09-06

## Context

Final P2 acceptance at `9db97f0dda109b4d0c0ecfa5f167733905df2766` froze two individually correct but cross-slice-incompatible rules:

1. ADR-0021 / P2.4a required every durable `JOB:<job_id>` duplicate replay to reconstruct exactly one canonical INPUT payload; a missing INPUT was `INVARIANT_VIOLATION`.
2. ADR-0022 / P2.4b later intentionally allowed expired INPUT deletion once the job left `RECEIVED|CLAIMED|CODEX_STARTING|CODEX_RUNNING`, while keeping the job and JOB ingress as non-content replay metadata until P2.6a cleanup.

Therefore a normal accepted state can exist in which a retained terminal/non-turn-active job and exact JOB ingress remain but the INPUT content has been safely deleted. Replaying the same update in that state must remain a duplicate/no-effect outcome rather than becoming corruption.

The defect was discovered during independent review of P3.1 candidate `05a268781b4b7189271b64f55a3b21f30c259269`. P3.1 is paused until this accepted dependency is corrected.

## Scope

This ADR is a narrow correction to accepted duplicate reconstruction semantics only.

No schema/DDL change.
No retention-policy change.
No new repository public method.
No Telegram/Codex effect.
No recovery/retry policy.
No P3.2+ work.

## INPUT-required states

A missing INPUT remains impossible/corrupt while the job is in any state for which accepted P2.4b retention protects INPUT:

- `RECEIVED`
- `CLAIMED`
- `CODEX_STARTING`
- `CODEX_RUNNING`

For a durable JOB duplicate in one of these states:

- zero INPUT rows => `INVARIANT_VIOLATION`;
- more than one INPUT row => `INVARIANT_VIOLATION`;
- one INPUT row must materialize canonically, have exact job/dialogue ownership and match `job.input_sha256`.

`claim_turn` remains unchanged: because it accepts only `RECEIVED`, missing INPUT is still an invariant there.

## Retention-compatible INPUT-optional states

Accepted P2.4b may legally have deleted INPUT content when the retained job is in any of:

- `CODEX_COMPLETED`
- `FAILED`
- `UNKNOWN`
- `DELIVERY_PENDING`
- `DELIVERING`
- `DELIVERED`
- `DELIVERY_UNKNOWN`

For a durable exact JOB duplicate in one of these states:

- if exactly one INPUT row still exists, it must materialize canonically and match ownership/hash;
- if zero INPUT rows exist, this is a canonical retention-compatible duplicate;
- if more than one INPUT row exists, or an existing row is corrupt/mismatched, fail `INVARIANT_VIOLATION`.

No deleted prompt content is reconstructed or synthesized.

## TurnIngressClaimResult

The already-frozen public record permits `input_payload: TransientPayloadRecord | None`.

For `TurnJobRepository.claim_ingress(...)` when an existing exact JOB ingress is replayed:

- active INPUT-required state + canonical INPUT => `DUPLICATE`, exact job, exact INPUT;
- retention-compatible state + canonical INPUT still present => `DUPLICATE`, exact job, exact INPUT;
- retention-compatible state + INPUT already deleted => `DUPLICATE`, exact job, `input_payload=None`.

The duplicate path still performs no clock call and no mutation.

Existing non-JOB duplicate behavior is unchanged.
Orphan JOB behavior remains P2.5/P3 application authority and is not changed here.

## Public get_input_for_job remains unchanged

`TransientPayloadRepository.get_input_for_job(job_id)` keeps its accepted semantics:

- missing job => `NOT_FOUND`;
- job exists but no INPUT => `NOT_FOUND`;
- multiple/mismatch/corruption => `INVARIANT_VIOLATION`.

This public method answers whether INPUT content is currently retained; it is not itself the duplicate-idempotency authority.

## P3.1 application consequence

ADR-0026 duplicate-first behavior is superseded only where it required INPUT to exist for every retained JOB.

For an existing JOB ingress + exact job:

- P3.1 must never recreate or re-execute the prompt;
- if INPUT exists, it may be used to prove canonical coherence;
- if INPUT is `NOT_FOUND` and job state is one of the retention-compatible states above, return `DUPLICATE` with the exact durable job and no external/configuration effect;
- if INPUT is missing in an INPUT-required state, fail application `INVARIANT`;
- multiple/corrupt/mismatched INPUT remains application `INVARIANT`.

For a same-update race that reaches `TurnJobRepository.claim_ingress(...)`, P3.1 must accept a `DUPLICATE` result whose `input_payload` is `None` only when the returned job is in a retention-compatible state.

## Acceptance correction proof

The correction must deterministically prove at least:

1. create a canonical job + JOB ingress + INPUT;
2. move the job to a state where INPUT retention is optional using accepted public repositories where practical;
3. expire and delete INPUT through accepted `RetentionRepository.sweep`;
4. verify job + exact JOB ingress remain;
5. replay the same update through `TurnJobRepository.claim_ingress` with changed caller snapshot values;
6. require `DUPLICATE`, exact durable job, `input_payload=None`, zero clock/mutation and no second job;
7. prove active `RECEIVED` with test-only missing INPUT still fails `INVARIANT_VIOLATION`;
8. prove an existing corrupt/mismatched INPUT still fails invariant;
9. preserve all prior P1/P2 focused/full acceptance and DDL SHA.

A P2 acceptance supplement must record the corrected final P2 HEAD after architect review. Historical final-P2 evidence at `9db97f0d...` remains factual for the earlier gate but is superseded for this one replay rule by the accepted correction.

## Out of scope

No content-retention extension, no seven-day horizon change, no job/ingress cleanup change, no new queue/retry behavior, no P3 application service implementation in the correction slice, no Telegram/Codex/network/production effect.