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
- ADR-0032 is binding P4.1 authority.

## Accepted P3 boundary consumed by P4

P4.1 consumes accepted `SettingsSelectionService` only; it does not change P3 semantics.

Profile mutation requires no live dialogue. Model/reasoning mutation requires no dialogue or exact IDLE and authenticated fresh catalog validation. Every mutation is optimistic-version bound. P4 must project these finite outcomes rather than duplicating/weakening them.

The accepted P3.4/P3.5 interrupt/delete services remain out of scope until P4.2.

## P4 architecture split

- **P4.1 — NEXT:** private Telegram trust edge + normalized private updates + durable private-menu dedupe + opaque one-time callback tokens + profile/model/reasoning settings panel.
- **P4.2 — LATER:** private server/dialogue status and interrupt/hard-delete controls over accepted P3.4/P3.5, with explicit destructive confirmation.
- **P4.3 — LATER:** private diagnostics/last sanitized error, approval projection/callback composition and final fake private-management acceptance.

P5 group routing remains separate.

## P4.1 trust boundary

Private management authorizes only the exact configured positive operator user ID in exact Telegram private chat `chat.id == operator_user_id`, with `chat.type == private` and non-bot sender. Callback authorization uses exact callback sender plus the callback message's exact private chat. Inline-message-only callbacks are rejected.

Supported private commands are exact `/start`, `/menu`, `/settings`. Unknown authorized private text is not a Codex prompt and is not retained as content.

Private chat cannot activate a controller. ADR-0002/0003 keep ACTIVE activation group-only because the user-originated group message must be seen by all bots to force non-target controllers to SLEEP. P4.1 has no private ACTIVE/SLEEP mutation.

## P4.1 normalized adapter

Add a pure Telegram private update normalizer with finite outcomes:

`COMMAND | CALLBACK | UNAUTHORIZED | UNSUPPORTED | MALFORMED`.

Application receives no raw Telegram JSON. Unauthorized/unsupported/malformed normalized values retain no arbitrary input text; callback tokens are redacted from generic repr.

No Telegram HTTP/network/polling exists in P4.1.

## P4.1 durable command/callback authority

Authorized private command updates are deduped by one additive schema-v1 repository that inserts completed `ingress_updates` with `CONTROL` disposition and never mutates controller mode/epoch. Duplicate update ID produces no new panel callback rows.

Unauthorized message updates use accepted `IGNORED_UNAUTHORIZED` ingress with no text retention.

Callbacks use accepted `callback_actions` as their one-time idempotency authority rather than update-ID dedupe.

Exact callback data:

`cc1:<32-char URL-safe token>`

Default token generation is `secrets.token_urlsafe(24)`; persist only SHA-256 of the token. Callback TTL is 900000 ms. Callback data carries no trusted action/profile/model/reasoning/page parameter.

## P4.1 callback semantics

Actions exactly:

`OPEN_ROOT | OPEN_PROFILES | OPEN_MODELS | OPEN_REASONING | SELECT_PROFILE | SELECT_MODEL | SELECT_REASONING`.

Choice target is stored only as SHA-256 fingerprint in callback `subject_id`; the handler re-resolves current configured/authenticated options and requires exactly one match. This permits accepted model IDs up to 256 characters without schema changes.

Every action binds exact settings version plus exact dialogue-state snapshot (`NO_DIALOGUE` or current `DialogueState.value`). Selection callback creation is omitted when P3.3 says the class of mutation cannot be legal: profile only NO_DIALOGUE; model/reasoning only NO_DIALOGUE or IDLE.

After callback claim, current version/state are rechecked before mutation. Mismatch is STALE and does not mutate settings.

Wrong callback user/chat cannot consume the operator token under accepted P2.3 behavior.

## P4.1 panel

Semantic sections:

`ROOT | PROFILES | MODELS | REASONING`.

Page size: 8. Button label max: 64 characters. Panel text max: 3500 characters. Plain text only; no Telegram parse mode.

Safe display may include server ID/display, profile/model display/ID, reasoning effort, dialogue state and catalog availability. Never expose CODEX_HOME, raw thread/turn IDs, prompt/output, callback token/hash, raw Telegram JSON or raw exception text.

## P4.1 application result

`PrivateSettingsManagementService` public methods exactly:

- `handle_command(request)`
- `handle_callback(request)`

`PrivateAdminStatus` exactly:

`RENDERED | UPDATED | NO_CHANGE | BLOCKED | STALE | EXPIRED | ALREADY_USED | DUPLICATE | UNAUTHORIZED | UNSUPPORTED`.

`PrivateAdminErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

P3.3 result mapping is binding: UPDATED/NO_CHANGE preserve status, CONFLICT -> STALE, BLOCKED -> BLOCKED with finite safe reason, STORAGE -> STORAGE, and unexpected internal INVALID_ARGUMENT/INVARIANT from P4-owned validated values -> INVARIANT.

## P4.1 acceptance focus

Must prove exact auth/malformed handling, no private prompt path, durable CONTROL/IGNORED_UNAUTHORIZED semantics, duplicate command no duplicate callbacks, opaque token/hash-only persistence, callback authorization/expiry/replay/stale handling, real P3.3 profile/model/reasoning composition, 256-char model fingerprint resolution, hidden/unavailable option blocking, UI bounds/redaction, corruption fail-closed, zero real Telegram/Codex/network effects and full accepted regressions with unchanged DDL SHA.

Accepted pre-P4 full suite authority is 671.

## Out of scope

No group routing, fleet keyboard, ACTIVE mutation, private interrupt/delete, approvals, diagnostics, response delivery, real Telegram API, production config/secrets/service work or P5+.

## Execution authority

Codex must not self-start work from this document.

Only P4.1 may be implemented from the next explicit architect prompt, on the architect-created branch/issue from the exact authority commit containing ADR-0032.
