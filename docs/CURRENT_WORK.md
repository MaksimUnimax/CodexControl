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
- P2.4b accepted after two repair reviews: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- ADR-0017..0022 remain accepted authority for the existing storage/core/idempotency/turn/delivery/approval/retention boundaries.
- ADR-0023 is the binding P2.5 hard-delete/tombstone/error authority.

## Accepted P2.4b facts
- Delivery planning/claim/terminal capture is durable before future transport effect; each segment has at most one send attempt and UNKNOWN is never a blind retry source.
- Reachable delivery shapes are fail-closed and exact: DELIVERY_PENDING=`P+`; DELIVERING=`C*SP*` or `C+P+`; DELIVERED=`C+`; DELIVERY_UNKNOWN=`C*UP*`; delivery-owned FAILED=`C*FP*`.
- PENDING/SENDING/UNKNOWN delivery payloads remain required and protected; terminal CONFIRMED/FAILED metadata survives safe payload deletion through durable hashes.
- Approval callbacks consume the callback and claim the exact bound approval subject in one transaction with authorization privacy, expiry/stale one-time semantics and typed wire identity.
- At most one PENDING approval exists for one exact profile + typed wire identity; terminal history may coexist and wire IDs may be reused after terminalization.
- Retention applies protection predicates before LIMIT, so protected old rows cannot starve later eligible payloads.
- Final P2.4b proof: unit 6, integration 25, full `387 + 6 + 25 = 418`; prior regressions/security/scope checks passed.

## P2.5 exact architect authority
P2.5 implements only **durable delete-state claims, confirmed hard-delete local purge/finalization, deletion tombstones and sanitized error fingerprints**.

Binding source: `docs/adr/0023-hard-delete-tombstones-and-error-fingerprints.md` plus accepted ADR-0017..0022, `docs/DATA_MODEL.md`, `docs/STATE_MACHINES.md`, `docs/PRODUCT_REQUIREMENTS.md` and observability/security authority.

### Dialogue delete states
- ADR-0023 globally owns DELETE_PENDING, DELETING and DELETE_UNKNOWN state-shapes.
- Hard-delete intent is accepted only from canonical IDLE with a bound thread, exact version, only terminal-safe retained jobs (`DELIVERED|FAILED`) and no remaining PENDING approvals.
- `claim_delete_intent` atomically moves IDLE->DELETE_PENDING before any future external delete operation.
- `claim_deleting` atomically moves DELETE_PENDING->DELETING and returns the exact profile/thread binding to be used later by application code with P1.9.
- P2.5 performs no P1.9 invocation. Ambiguous dispatched non-confirmation is recorded as DELETE_UNKNOWN; deterministic local/pre-dispatch failure may be ERROR. Neither is retried by P2.5.

### Confirmed finalization
- `finalize_confirmed` is legal only after definitive external `DELETE_CONFIRMED` for the exact DELETING binding.
- One SQLite transaction computes SHA-256 of the exact raw thread ID, inserts a non-content tombstone, and deletes the live dialogue under exact state/version guard.
- `stale_generation` is the current DELETING dialogue version; `deleted_at_ms=max(clock, dialogue.updated_at_ms)`; tombstone expiry must be strictly later.
- FK cascade purges dialogue-owned turn jobs, transient payloads, delivery segments and approvals. Error fingerprints remain with entity refs nulled by FK.
- `ingress_updates` and `callback_actions` remain as bounded non-content replay/idempotency metadata in P2.5; their age-based cleanup belongs to P2.6.
- No raw thread ID is stored in the tombstone and no controller-owned live binding remains after commit.

### Error fingerprints
- Only canonical SHA-256 fingerprint + sanitized error class + optional canonical dialogue/job references may be recorded; there is no raw exception/trace/stderr/content API.
- First occurrence inserts count 1. Exact duplicate occurrence increments count once with monotonic last-seen time.
- Reusing one fingerprint with a different error class or different entity references is an invariant violation, not a merge.
- Hard delete may clear entity refs through FK while retaining the non-content fingerprint/count history.

### Forbidden P2.5 scope
No Codex/Telegram effect, no interrupt orchestration, no DELETE_UNKNOWN retry/reconciliation, no tombstone expiry cleanup, no callback/ingress metadata retention sweep, no broad P2.6 recovery harness, no P3 application service and no production state.

## Execution authority
Codex must not self-start work from this document.

Only **P2.5 — delete claims + tombstones + error fingerprints + confirmed local finalization** is eligible for the next explicit implementation prompt.
