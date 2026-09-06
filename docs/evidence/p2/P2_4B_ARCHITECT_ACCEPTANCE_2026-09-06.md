# P2.4b architect acceptance — 2026-09-06

Architect acceptance authority for P2.4b.

## Accepted implementation

- Original architect base: `7f9c84fc1dfe77e07db3f78568c15a58e6370cf9`
- Initial candidate: `e52bd9c4eb6a7c87ecd7fbb1b84297e4421ddf29`
- First repair: `5355d88c44f02abe03a93bfb87d3c0eb571341a2`
- Accepted implementation/proof HEAD after second repair: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`
- Branch: `impl-p2-4b-delivery-approval-retention-2026-09-05`
- Issue: #15
- Binding ADR: ADR-0022

The initial candidate and first repair were independently rejected until delivery state-shapes, UNKNOWN payload authority, retention progress/protection, approval corruption classification, exact reachable delivery plan shapes and global live approval wire identity were all fail-closed and deterministically proven.

## Accepted durable boundary

- Delivery planning atomically creates the bounded ordered PENDING plan and moves `CODEX_COMPLETED -> DELIVERY_PENDING` before any transport effect.
- `claim_next` commits exactly one `PENDING -> SENDING` attempt (`attempt_count=1`) plus the corresponding job version/state before a future Telegram send/edit. There is no blind resend from UNKNOWN/FAILED.
- Delivery terminal capture is exact: CONFIRMED advances through the remaining plan and ends in DELIVERED; UNKNOWN becomes `DELIVERY_UNKNOWN`; deterministic delivery failure becomes FAILED.
- Delivery job/segment materialization is globally fail-closed. Reachable plan patterns are exact: `P+` for DELIVERY_PENDING, `C*SP*` or `C+P+` for DELIVERING, `C+` for DELIVERED, `C*UP*` for DELIVERY_UNKNOWN, and `C*FP*` for delivery-owned FAILED.
- PENDING/SENDING/UNKNOWN delivery segments require a canonical DISPLAY payload with exact hash/job/dialogue ownership. CONFIRMED/FAILED may retain only the durable hash after safe payload retention.
- Approval records use the exact accepted P1.7 kind and INTEGER-or-STRING wire request identity. At most one PENDING approval may exist for one exact `(profile, typed wire identity)`; any number of terminal historical rows may coexist and the identity may be reused after terminalization.
- `claim_callback` consumes the opaque callback and claims the bound approval subject in one SQLite transaction. Authorization privacy precedes subject/expiry disclosure; stale callbacks are consumed once; expiry is fail-closed; only fresh exact bindings become APPROVED or DENIED.
- `cancel_pending_for_job` only terminalizes pending approvals after the job is no longer CODEX_RUNNING and performs no external response.
- `RetentionRepository.sweep(limit)` is explicit, one-clock and bounded. Protection predicates are applied before LIMIT so permanently protected old rows cannot starve later eligible payloads. Active/reconciliation-critical INPUT/OUTPUT, PENDING/SENDING/UNKNOWN delivery payloads and PENDING approval payloads are preserved; terminal-safe content may be deleted while metadata rows remain.
- No retry loop, Telegram/Codex effect, schema migration, deletion workflow, tombstone/error repository, P3 application policy or production state is part of P2.4b.

## Acceptance proof

Final focused counts reported and independently reviewed:

- P2.4b unit: 6
- P2.4b integration: 25
- Accepted pre-P2.4b full suite: 387
- Expected/observed full suite: `387 + 6 + 25 = 418`
- P2.4a unit/integration: 8 / 31
- P2.3 unit/integration: 7 / 28
- P2.2 unit/integration: 6 / 20
- P2.1 unit/integration: 8 / 31
- P1.10 T0/T1/T2: 6 / 1 / 4

Repair proof includes global delivery-state materialization, exact reachable segment patterns, read-path corruption rejection, UNKNOWN payload retention, delivery FAILED/no-retry and EDIT confirmation mismatch, version overflow/no-clock preconditions, complete retention protection matrix and anti-starvation progress, INTEGER/STRING live-wire duplicate handling, wire reuse after terminal history, fresh DENIED and callback expiry/privacy paths, duplicate-live corruption rollback for both callback and retention transactions, cancellation ownership, corruption redaction and exact full-count arithmetic.

The known pre-existing P1.6 pending-task warning was observed in the final executor run and was not introduced by P2.4b.

## Security / scope

- Schema-v1 DDL SHA remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- No runtime dependency was added.
- No production database/state root, secrets, services, real Telegram calls or real Codex calls were used.
- The only accepted prior-slice source change is the ADR-0022-authorized global materialization of now-owned delivery job state shapes.

P2.4b is architect-accepted at `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
