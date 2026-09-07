# P4.2 architect acceptance

Date: 2026-09-07
Status: ARCHITECT_ACCEPTED

Accepted implementation/proof HEAD: `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`.
Final P4.2 architect base: `a4ad1f70cf2fa1abdecd8d37900a53de4fbfbe7d`.
Initial superseded freeze: `51a30afd77ba75baabd535d03abbfe0caee1b166`.
Rejected initial candidate: `41e94a1aefd20b86c9f4f4d994c9bde6947b3986`.
Rejected first repair: `e6bb85986835d82e5b4235f83aef33cc10501fbc`.
Issue: #29.
Architect review/addenda: `5568089991`, `5568879298`.
Binding authority: ADR-0033 plus the two recorded architect addenda.

Independent GitHub review confirmed a linear three-commit P4.2 implementation lineage above the exact final architect base: the initial candidate, first repair, and second repair. The cumulative diff contains only P4.2 application/Telegram-render/storage surfaces, narrow package exports, focused tests and factual implementation evidence. No accepted P4.1/P3 production authority, architecture ADR, roadmap authority or schema/DDL was modified by the implementation branch.

P4.2 uses accepted `ApplicationRecoveryRepository.inspect()` as the canonical dialogue/job status authority and fails closed on noncanonical durable state. No-dialogue status is static and creates no callback authority. Safe status projection excludes raw thread/job/turn IDs, CODEX_HOME, prompt/output, callback token/hash and raw exception bodies.

P4.1 and P4.2 share the opaque `cc1:<32-char token>` grammar. The additive read-only `PrivateManagementRepository.peek_callback()` routes ownership without consumption: a P4.1 token sent to P4.2 returns `ACTION_UNAVAILABLE`, remains unconsumed and is still usable by the accepted P4.1 handler. P42 callbacks remain SHA-256-only in durable storage, use the accepted 900000 ms TTL, one-time P2.3 claims, atomic batch insertion and no collision retry.

The P4.2 action matrix is accepted: every live dialogue may refresh; interrupt exists only for exact `TURN_RUNNING` plus one `CODEX_RUNNING` job; delete begin exists only for exact IDLE/no active job, TURN_RUNNING/CODEX_RUNNING, or DELETE_PENDING. CREATING/CREATE_UNKNOWN/IDLE+RECEIVED/CLAIMED/CODEX_STARTING/INTERRUPTING/TURN_UNKNOWN/DELETING/DELETE_UNKNOWN/ERROR do not receive destructive authority beyond the frozen matrix. DELETING and DELETE_UNKNOWN expose refresh only.

Interrupt composition delegates exactly one version-bound `DialogueInterruptRequest` to accepted P3.4 and does not call P1.8 or reconstruct active binding authority locally. The real P3.4 integration proof asserts exact `TurnBinding` object identity. Stale callbacks produce zero P3.4 effect. Impossible P3.4 status/reason pairs fail `INVARIANT`; canonical CONFIRMED/RECONCILED/UNKNOWN/CONFLICT/REJECTED/BLOCKED relations map finitely.

Hard delete is accepted as mandatory two-step authority: `BEGIN_DELETE` performs zero P3.5/P1 effect and creates separate CONFIRM/CANCEL callbacks bound to the same exact dialogue version/state/delete-context fingerprint. Only `CONFIRM_DELETE` may issue exactly one accepted `DialogueDeleteRequest`. Real accepted P3.5 proofs cover IDLE hard delete with one fake external thread/delete maximum plus purge/tombstone, and fresh explicit DELETE_PENDING continuation. Running-delete handling remains delegated to P3.5; P4.2 does not reproduce interrupt/quiescence/P1.9 logic.

The first architect repair closed two blockers. Successful Cancel now performs one context-wide callback-metadata transaction and does not merely consume its own token. Every same-context outstanding confirmation is revoked; if any matching confirmation was already claimed before expiry, Cancel returns `STALE / STALE_ACTION` and does not falsely report success. Stale confirmations perform zero delete, wrong-principal P42 callbacks remain unconsumed, and impossible P3.4/P3.5 status/reason pairs fail closed as `INVARIANT`.

The second architect repair closes the repeatable-cancellation sentinel ambiguity. A confirmation revoked by Cancel is durably encoded exactly as `consumed_at_ms == expires_at_ms`, the same no-effect terminal sentinel used by accepted callback expiry. A genuinely claimed confirmation remains `consumed_at_ms < expires_at_ms`. This makes repeated cancellation in the same unchanged dialogue generation safe: first Cancel and second Cancel both render successfully, both old confirmations replay as `ALREADY_USED`, and total delete calls remain zero. Direct repository proof confirms an older expiry-sentinel row does not block revocation of a newer same-context unconsumed confirmation. The claimed-confirm race still returns STALE with at most one confirm-side delete invocation.

Cross-generation/context isolation is preserved: Cancel matches exact action, subject type/fingerprint, dialogue version/state and operator user/chat. Multiple same-context confirmations are all revoked together; rows from another generation/state/fingerprint/principal are untouched. Revocation requires no new clock read and no schema change.

Executor-reported final focused counts are P4.2 `5 unit / 29 integration`. Accepted pre-P4.2 full suite authority was `694`; expected and observed full discovery are `728` (`694 + 5 + 29`). Required prior focused regressions were reported unchanged, including P4.1 `8/15`, P3.5 `12/25/1`, P3.4 `6/31`, P3.3 `5/25`, P3.2 `2/21`, P3.1 `11/26`, P2.C1 `5/1`, P2.6b `5/12/8/3`, P2.6a `4/28`, P2.5 `4/18`, P2.4b `6/25`, P2.4a `8/31`, P2.3 `7/28`, P2.2 `6/20`, P2.1 `8/31`, P1.9 `15`, P1.8 `28`, and P1.10 `6/1/4`.

Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`. Compileall, import smoke, diff and secret/redaction checks are reported PASS. The known P1.6 pending-task warning remains pre-existing and was not introduced by P4.2.

GitHub exposes no attached commit status checks for `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; acceptance therefore relies on independent exact GitHub code/diff review plus the executor's isolated focused/full-regression evidence, consistent with project governance.

P4.2 performs no real Telegram/network/Codex/thread/turn/interrupt/delete/approval/delivery production effect and touches no production database/state/service. Live Telegram validation remains later roadmap authority.

P4.2 is complete and architect-accepted. P4.3 is next but requires a separate architect authority freeze before any implementation execution; this record does not itself authorize P4.3 implementation.
