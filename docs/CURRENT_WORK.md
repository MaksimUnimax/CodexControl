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

## Accepted P4.1 boundary

P4.1 consumes accepted `SettingsSelectionService` only; it does not change P3 semantics.

The private Telegram-shaped trust edge is pure/fake: no Telegram HTTP, polling, webhook, token loading or network effect. Only the exact configured operator in exact private chat may become authorized COMMAND/CALLBACK input. Arbitrary authorized private text is UNSUPPORTED and never becomes a Codex prompt. Wrong principal/chat/type is fail-closed and raw Telegram content is not retained.

Authorized private menu commands durably claim one completed `CONTROL` ingress without controller mode/epoch mutation. Duplicate update IDs create no new callback authority. Unauthorized private messages use the accepted no-content `IGNORED_UNAUTHORIZED` path.

Opaque callbacks use exact `cc1:<32-char token>` data, SHA-256-only durable token hashes, exact 900000 ms TTL and one-time P2.3 callback claims. Business targets are server-side fingerprints, including 256-character model IDs. Wrong principal cannot consume the operator token; expired/replayed/stale actions are finite and non-retrying.

Every actionable callback is bound to an exact existing settings version and exact dialogue-state snapshot. Missing settings return `BLOCKED / SETTINGS_MISSING` with no callback rows, so no fabricated version authority exists. Existing durable token-hash collision is an application invariant, not storage/caller failure.

Profile/model/reasoning mutation delegates exactly once to accepted P3.3. Profile requires no live dialogue; model/reasoning require no dialogue or exact IDLE plus authenticated catalog authority.

Private chat still cannot activate a controller. ADR-0002/0003 keep ACTIVE activation group-only because the same user-originated group message must force every non-target controller to SLEEP.

## P4 architecture split

- **P4.1 — DONE:** private Telegram trust edge + normalized private updates + durable private-menu dedupe + opaque one-time callbacks + profile/model/reasoning settings panel. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full suite 694.
- **P4.2 — NEXT ARCHITECTURE WORK:** private server/dialogue status plus interrupt/hard-delete controls over accepted P3.4/P3.5, with explicit destructive confirmation.
- **P4.3 — LATER:** private diagnostics/last sanitized error, approval projection/callback composition and final fake private-management acceptance.

P5 group routing remains separate. Live Telegram acceptance remains later roadmap authority.

## P4.2 boundary known before freeze

P4.2 must consume accepted P3.4/P3.5 rather than reproduce interrupt/delete semantics. Destructive callback authority must remain opaque, one-time, exact-user/chat/version/state bound, and hard delete must require an explicit confirmation step distinct from merely opening the dialogue/status panel.

Private ACTIVE remains forbidden under existing fleet ordering authority. P4.2 may display effective/requested mode and may only add any local mode control if separately architect-frozen without violating ADR-0002/0003.

No P4.2 implementation contract is frozen by this document yet. Exact public surfaces, status projection, destructive-confirmation state binding, refresh behavior, callback actions and tests require a separate architect ADR/authority commit before executor work.

## Accepted P4.1 acceptance facts

Focused P4.1 counts after repair: 8 unit / 15 integration. Accepted pre-P4 baseline was 671; final expected/observed full discovery is 694.

Frozen DDL SHA remains unchanged. Known P1.6 pending-task warning remains pre-existing. GitHub has no attached CI/status checks for the accepted P4.1 SHA; acceptance used independent GitHub review plus executor focused/full-regression evidence under project governance.

## Out of scope until separately authorized

No group routing/fleet keyboard, private ACTIVE mutation, P4.2 interrupt/delete, P4.3 approvals/diagnostics, response delivery, real Telegram API, production config/secrets/service work or P5+.

## Execution authority

Codex must not self-start P4.2 from this document.

P4.1 is architect-accepted. The next task is architect research/freeze of P4.2 authority. No P4.2 implementation is authorized until a separate architect-owned authority commit, branch/issue and explicit executor prompt exist.
