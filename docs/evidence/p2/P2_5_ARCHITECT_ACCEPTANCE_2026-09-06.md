# P2.5 architect acceptance — 2026-09-06

Architect acceptance authority for P2.5.

## Accepted implementation

- Original architect base: `521453dbd73aab6c6f52defe770af3bd2e265a95`
- Initial candidate: `24e76e9913069b0b38e92ac33aedb0aceace0c24`
- Accepted implementation/proof HEAD after one repair: `87ef37cf245d79f6d20b507b13c0f36014c1580f`
- Branch: `impl-p2-5-delete-tombstones-errors-2026-09-06`
- Issue: #16
- Binding ADR: ADR-0023

The initial candidate was rejected after independent review found that terminal delete readiness trusted turn-job state without validating accepted P2.4b delivery-plan coherence, pre-existing tombstone collision was detected only after the future external delete boundary, and error-fingerprint semantic lookup could hide case-alias corruption. The repair closes those findings and adds deterministic proof for the affected boundaries.

## Accepted durable boundary

- `DELETE_PENDING`, `DELETING` and `DELETE_UNKNOWN` are globally canonical dialogue shapes: delete-pending/deleting retain a bound thread and no error; delete-unknown retains the exact binding plus a sanitized error class.
- `claim_delete_intent` accepts only canonical `IDLE`, exact version, bound thread, no tombstone collision, no pending approval, and only terminal-safe retained jobs. `DELIVERED` requires a canonical non-empty all-CONFIRMED delivery plan; Codex-level `FAILED` may have no delivery rows; delivery-owned `FAILED` requires exact `C*FP*` delivery coherence. Corrupt terminal history is `INVARIANT_VIOLATION`, not a safe delete source.
- `claim_deleting` rechecks tombstone collision and the same terminal-safe readiness before exposing the durable DELETING profile/thread binding for any later external P1.9 effect.
- `mark_delete_unknown` and deterministic `mark_delete_error` retain the exact binding, increment once and have no retry/reconciliation API in P2.5.
- `finalize_confirmed` is local finalization only after higher-layer definitive external delete confirmation. In one transaction it computes SHA-256 of the exact raw thread identity, records the current DELETING version as stale generation, inserts a content-free tombstone, deletes the exact dialogue state/version row and relies on accepted FK cascades to purge dialogue-owned jobs, transient payloads, delivery segments and approvals.
- Finalization preserves non-content `ingress_updates`, `callback_actions`, tombstones and sanitized error fingerprints; error entity references are cleared by FK while fingerprint/count/timestamps remain.
- Tombstones never retain the raw thread ID and require expiry strictly later than deleted time.
- Error fingerprints accept only canonical lowercase SHA-256 plus sanitized class and optional coherent entity references. Semantic case aliases are fail-closed: uppercase-only or dual-case physical rows are `INVARIANT_VIOLATION`; no row is silently selected. Exact duplicates increment once with monotonic last-seen time; mismatched class/entity bindings never merge.
- No Codex `thread/delete`, Telegram/network effect, retry, tombstone cleanup, metadata-retention sweep, P2.6 recovery orchestration, P3 service or production state is part of P2.5.

## Acceptance proof

Final focused counts reported and independently reviewed:

- P2.5 unit: 4
- P2.5 integration: 18
- Accepted pre-P2.5 full suite: 418
- Expected/observed full suite: `418 + 4 + 18 = 440`
- P2.4b unit/integration: 6 / 25
- P2.4a unit/integration: 8 / 31
- P2.3 unit/integration: 7 / 28
- P2.2 unit/integration: 6 / 20
- P2.1 unit/integration: 8 / 31
- P1.10 T0/T1/T2: 6 / 1 / 4

Repair proof includes canonical DELIVERED and delivery-owned FAILED readiness, impossible terminal-plan rejection with zero clock/mutation, pre-effect tombstone collision blocking at both intent and deleting claims, dual-case error-fingerprint alias rejection, exact/MAX stale-generation finalization, wrong-state/version no-clock finalization, deletion version overflow, entity-binding collision, timestamp-order corruption and deterministic repeated-cancellation ownership without positive-duration polling sleeps.

The known pre-existing P1.6 pending-task warning was observed in the final executor run and was not introduced by P2.5.

## Security / scope

- Schema-v1 DDL SHA remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- The only prior-slice production edit is the ADR-0023-authorized global materialization of DELETE_PENDING/DELETING/DELETE_UNKNOWN dialogue shapes.
- No runtime dependency was added.
- No production database/state root, credentials, service, network, real Codex call, real thread/delete or Telegram call was used.

P2.5 is architect-accepted at `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
