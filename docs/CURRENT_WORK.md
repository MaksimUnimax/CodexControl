# Current work authority

Date: 2026-09-05

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- P2.4a accepted after one repair: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0021 remain accepted authority for the existing storage kernel/core/idempotency/turn-job boundaries.
- ADR-0022 is the binding P2.4b delivery/approval/retention authority.

## Accepted P2.4a facts
- Atomic prompt acceptance durably writes one RECEIVED turn job, one INPUT payload and one `JOB:<id>` ingress before external effect; no second outstanding RECEIVED job for the dialogue is permitted.
- Duplicate JOB reconstruction and `claim_turn` require canonical durable ingress plus exactly one matching INPUT; internal missing/corrupt INPUT is `INVARIANT_VIOLATION`, while public missing input remains `NOT_FOUND`.
- `claim_turn` atomically moves RECEIVED->CLAIMED and IDLE->TURN_RUNNING and binds a first-dialogue thread once. `mark_codex_starting` is pre-wire durable intent; `mark_codex_running` binds the Codex turn ID once.
- `finish_codex` atomically captures COMPLETED/FAILED/UNKNOWN and may persist one OUTPUT payload in the same transaction.
- Payload content is exact bytes only, 1..8,388,608 bytes, repr-redacted and transient; long-lived job state stores hashes/metadata only.
- Final P2.4a proof: unit 8, integration 31, full `348 + 8 + 31 = 387`; prior P2/P1 regressions and security/scope checks passed.

## P2.4b exact architect authority
P2.4b implements only **delivery-segment durable send claims, approval persistence with atomic callback+approval subject claims, and bounded safe transient-content retention**.

Binding source: `docs/adr/0022-delivery-approval-and-retention-claims.md` plus accepted ADR-0017..0021, `docs/DATA_MODEL.md`, `docs/STATE_MACHINES.md`, `docs/PRODUCT_REQUIREMENTS.md`, `docs/TELEGRAM_INTERACTION_CONTRACT.md` and retention/security docs.

### Delivery
- Delivery operations are CREATE/EDIT; states are PENDING/SENDING/CONFIRMED/UNKNOWN/FAILED.
- `plan` atomically validates 1..4096 ordered DISPLAY payload-backed segments and moves job CODEX_COMPLETED->DELIVERY_PENDING.
- `claim_next` durably moves only the lowest eligible PENDING segment to SENDING/attempt1 and job to/remains DELIVERING before any future Telegram send/edit.
- `finish_sending` captures CONFIRMED, UNKNOWN or FAILED. Confirmed segments are never recreated; UNKNOWN moves job to DELIVERY_UNKNOWN and has no automatic retry; deterministic failure moves job to FAILED.
- Delivery state-shapes and active payload/hash/owner coherence fail closed.

### Approvals
- Approval records materialize exact PENDING/APPROVED/DENIED/EXPIRED/CANCELLED states and exact P1.7 wire-ID forms/kinds.
- `create_pending` requires exact CODEX_RUNNING job/version/profile and prevents a second live PENDING approval for the same profile+wire identity while allowing wire-ID reuse after terminal state.
- Production approval callbacks are NOT `CallbackActionRepository.claim()` followed by a separate approval mutation. P2.4b performs one SQLite transaction that preserves P2.3 callback privacy/expiry/one-time rules and atomically claims the bound approval subject before any external P1.7 approval response.
- Approval callback binding is `subject_type=approval`, `expected_state=PENDING`, action `approval_allow|approval_deny`, and callback expected_version equals current job version.
- Stale authorized callbacks are consumed once; expired callbacks/approvals terminalize fail-closed; only APPROVED/DENIED return approval metadata.

### Retention
- `RetentionRepository.sweep(limit)` is explicit/bounded, no background loop; limit 1..1000 and one clock per sweep.
- It may expire due PENDING approvals and delete only expired transient payload content that is not required by unfinished delivery, pending approvals or active/reconciliation-critical job states defined by ADR-0022.
- It never deletes jobs, delivery rows, approval rows, ingress, callbacks, tombstones or errors in P2.4b. Broader metadata retention/recovery remains P2.6; hard-delete purge remains P2.5.

### Forbidden P2.4b scope
No Telegram API/client/send/edit, no P1 approval response, no token generation, no interrupt/delete state machine, no tombstones/errors/hard-delete purge, no P3 application service and no production state.

## Execution authority
Codex must not self-start work from this document.

Only **P2.4b — delivery + atomic approval-subject claims + bounded transient retention** is eligible for the next explicit implementation prompt.
