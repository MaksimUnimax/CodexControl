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
- P4.2 accepted after two architect repairs at `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full suite 728.
- P4.2 acceptance authority: `docs/evidence/p4/P4_2_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- ADR-0032 remains binding accepted P4.1 authority.
- ADR-0033 plus architect addenda `5568089991` and `5568879298` remain binding accepted P4.2 authority.

## Accepted P4.1/P4.2 boundary consumed by P4.3

P4.1 owns exact private Telegram normalization/settings enums and action vocabulary. P4.2 owns the separate dialogue-control surface. P4.3 must compose these accepted private surfaces without weakening either one's one-time callback authority.

P4.1 provides exact private principal checking, accepted `PrivateCallbackRequest`, opaque `cc1:<32-char token>` grammar, one-time P2.3 callback claims, callback batch storage, hash-only token persistence, 900000 ms TTL and content-safe buttons/rendering.

P4.2 adds canonical private dialogue status over `ApplicationRecoveryRepository.inspect()`, exact P3.4 interrupt delegation, mandatory two-step P3.5 hard delete, read-only callback ownership peek, and context-wide destructive-confirm cancellation. A P4.1 token routed to P4.2 remains unconsumed; final P4.3 dispatcher must route by non-consuming durable action authority before any sub-service claims the token.

Private ACTIVE remains forbidden. Group/fleet routing remains P5 authority.

## P4 split

- **P4.1 — DONE:** private Telegram trust edge + settings management. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- **P4.2 — DONE:** private server/dialogue status + exact P3.4 interrupt + two-step confirmed P3.5 hard delete under ADR-0033 and two architect repair addenda. Accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full suite 728.
- **P4.3 — NEXT / NOT YET FROZEN:** private root/menu composition, diagnostics/last sanitized error, approval projection/callback composition and final fake private-management acceptance. Requires a separate architect authority freeze before implementation.

P5 group routing and P6 response delivery remain separate. Live Telegram acceptance remains later roadmap authority.

## Accepted P4.2 public boundary

`PrivateDialogueManagementService` exposes exactly:

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

## Accepted P4.2 status and action authority

Dialogue/active-job status is read only through accepted `ApplicationRecoveryRepository.inspect()`. Corrupt persisted state is INVARIANT. No dialogue yields a static `RENDERED / NO_DIALOGUE` panel with zero callback authority and no fabricated dialogue version.

For a live dialogue, safe display may include server identity, optional read-only effective mode, dialogue state, profile ID, active job state/model/reasoning. Raw thread/job/turn IDs, CODEX_HOME, prompt/output, callback token/hash and raw error bodies remain forbidden.

P4.2 actions exactly:

`P42_REFRESH | P42_INTERRUPT | P42_BEGIN_DELETE | P42_CONFIRM_DELETE | P42_CANCEL_DELETE`.

Every P42 action binds exact current dialogue version/state and SHA-256 context fingerprint. `P42_INTERRUPT` exists only for `TURN_RUNNING` plus exactly one `CODEX_RUNNING` active job and delegates exactly one accepted P3.4 request. `P42_BEGIN_DELETE` exists only for accepted IDLE/TURN_RUNNING/DELETE_PENDING cases and has zero destructive effect. Only `P42_CONFIRM_DELETE` may call accepted P3.5 exactly once. DELETING and DELETE_UNKNOWN expose no second-delete authority.

## Accepted cross-surface callback dispatch

P4.1 and P4.2 share the same opaque `cc1:<token>` grammar and callback table. Final routing must not be implemented by trying one sub-service's one-time claim first.

Accepted P4.2 provides:

`PrivateManagementRepository.peek_callback(token_hash_sha256) -> CallbackActionRecord | None`

as a read-only, zero-consumption durable action lookup. P4.2 callback order is auth -> token hash -> peek -> action-family decision -> claim only if action is `P42_*`.

- missing row -> `STALE / CALLBACK_NOT_FOUND`;
- existing non-P42/P4.1 row -> `BLOCKED / ACTION_UNAVAILABLE` and remains unconsumed;
- exact P42 row -> accepted P2.3 claim/expiry/replay flow.

P4.3 final composition must use this same non-consuming durable routing authority or an architect-equivalent mechanism before choosing the sub-service that will consume the callback.

## Accepted destructive confirmation/cancellation

Hard delete remains mandatory two-step:

`status -> BEGIN_DELETE(no effect) -> new CONFIRM_DELETE callback -> exact P3.5 delete`.

Confirmation is bound to exact current dialogue version/state/delete fingerprint. Version/state/context drift before confirmation is STALE with zero delete effect. Confirmation text must not claim empirical erasure of all Codex internal traces; P7 remains the storage-measurement gate.

A successful `P42_CANCEL_DELETE` atomically revokes every still-outstanding same-context confirmation for the exact version/state/fingerprint/principal. Revoked and expired no-effect confirmations use exact durable sentinel:

`consumed_at_ms == expires_at_ms`.

A genuinely claimed confirm remains:

`consumed_at_ms < expires_at_ms`.

If any matching confirm has actually been claimed, Cancel returns `STALE / STALE_ACTION` rather than falsely claiming cancellation. Repeated Cancel in the same unchanged dialogue generation remains valid and leaves zero destructive authority.

## Accepted P4.2 service mapping

P3.4 canonical status/reason relations are validated strictly before mapping. CONFIRMED/RECONCILED -> INTERRUPTED; UNKNOWN -> UNKNOWN/INTERRUPT_UNRESOLVED; CONFLICT+STALE_REQUEST -> STALE; REJECTED+None -> BLOCKED; only canonical blocked reasons map to BLOCKED. Impossible pairs are INVARIANT.

P3.5 canonical status/reason relations are validated strictly before mapping. DELETED -> DELETED; FAILED -> FAILED; UNKNOWN -> UNKNOWN/DELETE_UNKNOWN; CONFLICT+STALE_REQUEST -> STALE; only canonical blocked reasons map to BLOCKED. Impossible pairs are INVARIANT.

No mandatory follow-up render occurs after a committed interrupt/delete effect; rendering failure must not disguise an already completed effect.

Accepted final P4.2 full suite authority is 728 (`694 + 5 unit + 29 integration`).

## Out of scope / next gate

No private ACTIVE or group routing; no live Telegram transport; no response delivery; no real Codex/production effects; no schema/DDL change. P4.3 diagnostics/last sanitized error, approval projection/callback composition and final fake private root/menu composition remain unimplemented.

## Execution authority

P4.2 is complete and architect-accepted. P4.3 is the next roadmap slice, but it is NOT implementation-authorized yet. The architect must first research and freeze a separate P4.3 authority/ADR or binding architecture record, create the exact implementation branch/issue from that authority commit, and only then issue an explicit executor prompt. Codex must not self-start P4.3/P5.
