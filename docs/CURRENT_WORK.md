# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; full suite 543.
- P3.2 accepted at `c484c56db007569170363b3d08c24766148c3e30`; full suite 566.
- P3.3 accepted at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full suite 596.
- P3.4 accepted at `6460a449f861b7b86ab664e5ff877c108715082d`; full suite 633.
- P3.5 accepted at `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full suite authority 671.
- P3 acceptance authority: `docs/evidence/p3/P3_5_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P3 is complete at the fake/application boundary.
- P4.1 accepted after one repair at `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- P4.1 acceptance authority: `docs/evidence/p4/P4_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- ADR-0032 remains binding accepted P4.1 authority.
- ADR-0033 is binding P4.2 authority.

## Accepted P4.1 boundary consumed by P4.2

P4.1 owns exact private Telegram normalization/settings enums and action vocabulary. P4.2 must not add values to accepted `PrivateCommand`, `PrivatePanelSection` or P4.1 action enums. Final root/menu composition remains P4.3.

P4.1 provides exact private principal checking, accepted `PrivateCallbackRequest`, opaque `cc1:<32-char token>` grammar, one-time P2.3 callback claims, callback batch storage, hash-only token persistence, 900000 ms TTL and content-safe buttons/rendering. P4.2 reuses these semantics but defines a separate dialogue-control surface.

Private ACTIVE remains forbidden. Group/fleet routing remains P5 authority.

## P4 split

- **P4.1 — DONE:** private Telegram trust edge + settings management. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- **P4.2 — NEXT / FROZEN:** private server/dialogue status + exact P3.4 interrupt + two-step confirmed P3.5 hard delete under ADR-0033.
- **P4.3 — LATER:** private root/menu composition, diagnostics/last sanitized error, approval projection/callback composition and final fake private-management acceptance.

P5 group routing and P6 response delivery remain separate. Live Telegram acceptance remains later roadmap authority.

## P4.2 public boundary

Add separate `PrivateDialogueManagementService` with exactly:

- `open_status(request)`
- `handle_callback(request)`.

P4.2 reuses accepted P4.1 `PrivateCallbackRequest` and opaque callback grammar.

`PrivateDialogueStatus` exactly:

`RENDERED | CONFIRM_REQUIRED | INTERRUPTED | DELETED | BLOCKED | STALE | UNKNOWN | FAILED | EXPIRED | ALREADY_USED | UNAUTHORIZED`.

`PrivateDialogueReason` exactly:

`CALLBACK_NOT_FOUND | STALE_ACTION | NO_DIALOGUE | DIALOGUE_NOT_RUNNING | JOB_NOT_RUNNING | ACTIVE_BINDING_UNAVAILABLE | INTERRUPT_IN_PROGRESS | INTERRUPT_UNRESOLVED | DIALOGUE_NOT_READY | DELETE_NOT_READY | DELETE_IN_PROGRESS | DELETE_UNKNOWN | ACTION_UNAVAILABLE`.

`PrivateDialogueErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

Panel sections exactly:

`STATUS | DELETE_CONFIRM`.

## P4.2 status authority

Read dialogue/active-job status only through accepted `ApplicationRecoveryRepository.inspect()`, which is the P3.5 canonical cross-table authority. Corrupt persisted state is INVARIANT.

No dialogue -> static RENDERED/NO_DIALOGUE panel with zero callbacks. Never fabricate a dialogue version.

For a live dialogue, safe display may include server identity, optional read-only effective mode, dialogue state, profile ID, active job state/model/reasoning. Never display raw thread/job/turn IDs, CODEX_HOME, prompt/output, callback token/hash or raw error body.

## P4.2 actions

Actions exactly:

`P42_REFRESH | P42_INTERRUPT | P42_BEGIN_DELETE | P42_CONFIRM_DELETE | P42_CANCEL_DELETE`.

All actions bind exact current dialogue version/state. Trusted context is SHA-256 fingerprinted server-side in callback subject IDs; Telegram callback data remains opaque.

Interrupt button exists only for TURN_RUNNING + exactly one CODEX_RUNNING active job. It calls accepted `DialogueInterruptService.interrupt()` exactly once from current canonical IDs/versions.

Delete begin exists only for IDLE with no active job, TURN_RUNNING + exact CODEX_RUNNING, or DELETE_PENDING. It performs no P3 effect and renders a distinct DELETE_CONFIRM panel with new one-time CONFIRM/CANCEL callbacks.

Only `P42_CONFIRM_DELETE` may call accepted `DialogueDeleteService.delete()` exactly once. DELETE_PENDING confirmation uses the exact current version, preserving P3.5 fresh-explicit-continuation authority. DELETING/DELETE_UNKNOWN expose no second-delete authority.

## Cross-surface callback dispatch

P4.1 and P4.2 share the same opaque `cc1:<token>` callback grammar and callback table, so final routing cannot safely be implemented by trying one service's one-time claim first.

P4.2 adds one read-only schema-v1 helper on the accepted private-management storage surface:

`peek_callback(token_hash_sha256) -> CallbackActionRecord | None`.

It materializes the existing callback row without mutation/consumption.

P4.2 callback order is exact auth -> token hash -> peek -> action-family decision -> claim only if action is `P42_*`.

- missing row -> STALE/CALLBACK_NOT_FOUND;
- existing non-P42/P4.1 row -> BLOCKED/ACTION_UNAVAILABLE and remains unconsumed;
- exact P42 row -> accepted P2.3 claim/expiry/replay flow.

This preserves P4.1 token authority if a token is accidentally dispatched to P4.2. P4.1 handler remains unchanged. P4.3 final composition must use the same non-consuming durable action lookup, or architect-equivalent routing authority, before choosing the private sub-service that will consume a token.

## Destructive confirmation

Hard delete is always two-step:

`status -> BEGIN_DELETE(no effect) -> new CONFIRM_DELETE callback -> exact P3.5 delete`.

Confirmation is bound to the same exact current dialogue version/state/delete-context fingerprint. Any version/state/context drift before confirmation is STALE with zero delete effect. Confirmation text must not claim empirical erasure of all Codex internal traces; P7 remains the storage-measurement gate.

Callback claim occurs before interrupt/delete. Cancellation/replay never causes P4 retry.

## P4.2 accepted-service mapping

P3.4 CONFIRMED/RECONCILED -> INTERRUPTED; UNKNOWN -> UNKNOWN/INTERRUPT_UNRESOLVED; CONFLICT -> STALE; finite blocked/rejected reasons map safely. P3.4 STORAGE -> P4.2 STORAGE, internally impossible INVALID_ARGUMENT/INVARIANT -> INVARIANT.

P3.5 DELETED -> DELETED; FAILED -> FAILED; UNKNOWN -> UNKNOWN/DELETE_UNKNOWN; CONFLICT -> STALE; finite BLOCKED reasons map safely. P3.5 STORAGE -> P4.2 STORAGE, internally impossible INVALID_ARGUMENT/INVARIANT -> INVARIANT.

No mandatory follow-up render after a committed interrupt/delete effect; rendering failure must not disguise an already completed effect.

## P4.2 acceptance focus

Must prove exact public contracts/redaction, canonical status inspection, no-dialogue zero callbacks, action matrix, exact context fingerprints, wrong-auth non-consumption, non-P42 token non-consumption, expiry/replay/stale handling, real accepted P3.4 one-interrupt composition, two-step delete confirmation, stale confirm zero effect, real accepted P3.5 IDLE delete, explicit DELETE_PENDING continuation, no delete authority in DELETING/DELETE_UNKNOWN, callback collision invariant/no retry, cancellation/replay no second effect, zero real Telegram/network/production effects, full P4.1/P3/P2/P1 regressions and unchanged DDL hash.

Accepted pre-P4.2 full suite authority is 694.

## Out of scope

No changes to accepted P4.1 exact enums/root settings service; no group routing/private ACTIVE; no P4.3 diagnostics/approvals/root composition; no response delivery; no real Telegram/network/production work; no schema/DDL; no P5+.

## Execution authority

Only P4.2 may be implemented from the next explicit architect prompt, on the architect-created branch/issue from the exact authority commit containing ADR-0033. Codex must not self-start P4.3/P5.
