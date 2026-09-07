# ADR-0032 — Private Telegram trust edge and settings management

Status: Accepted
Date: 2026-09-07

## Context

P3 is architect-accepted and complete at the fake/application boundary. P4 introduces Telegram private management. Live Telegram/network acceptance remains T4/P9; P4 uses normalized/fake Telegram boundaries and must not perform production polling or network effects.

The V1 product requires exact single-operator private administration, button-led settings management, opaque one-time callbacks, no generic shell, no prompt routing from private chat, and no secret/content leakage. Accepted schema-v1 already contains `ingress_updates` and `callback_actions`, so P4.1 must not add DDL.

Fleet activation remains a group-only user-originated control under ADR-0002/0003. A private inline callback is visible to only one bot and therefore cannot safely activate one controller while making every other controller sleep.

## P4 split

P4 is split into architect-owned slices:

- **P4.1** — private Telegram normalization/authentication + durable private-menu dedupe + opaque callback/panel machinery + profile/model/reasoning settings management over accepted P3.3;
- **P4.2** — private server/dialogue status plus interrupt/hard-delete controls over accepted P3.4/P3.5 with explicit destructive confirmation;
- **P4.3** — private diagnostics/last sanitized error, approval projection/callback composition and final fake private-management acceptance.

P5 remains group/fleet routing. P6 remains response delivery/full local orchestration. Live Telegram acceptance remains P9.

## P4.1 non-goals

P4.1 does not implement:

- Telegram HTTP polling/webhook/network transport;
- production bot-token loading;
- group routing or fleet activation;
- private ACTIVE mutation;
- interrupt/delete/destructive actions;
- approvals;
- response delivery/outbox;
- diagnostics beyond settings/dialogue state needed for the settings panel;
- schema/DDL changes;
- P5+ work.

## Private authorization

The private Telegram adapter is configured with exactly one positive `operator_user_id`.

An authorized private message requires all of:

- schema-valid nonnegative Telegram `update_id`;
- `message.from.id == operator_user_id`;
- `message.from.is_bot is False`;
- `message.chat.id == operator_user_id`;
- `message.chat.type == "private"`;
- exact supported command text.

Supported command text is exactly:

- `/start` -> `MENU`;
- `/menu` -> `MENU`;
- `/settings` -> `SETTINGS`.

No arguments, suffixes or command-like arbitrary text are accepted. Unknown authorized private text is `UNSUPPORTED` and never becomes a Codex prompt.

An authorized callback requires all of:

- schema-valid nonnegative Telegram `update_id`;
- `callback_query.from.id == operator_user_id`;
- `callback_query.from.is_bot is False`;
- callback has a normal message, not inline-message-only form;
- callback message chat ID equals `operator_user_id`;
- callback message chat type is exactly `private`;
- callback query ID is a bounded nonempty opaque identifier;
- callback data is the exact P4 opaque-token grammar below.

Wrong user/chat/type/bot sender is `UNAUTHORIZED`. Structurally invalid input is `MALFORMED`. Unsupported authorized private text is `UNSUPPORTED`. These outcomes carry no raw text or callback token in generic representations.

## Normalized private update contract

P4.1 adds a pure Telegram adapter that maps raw untrusted Telegram dictionaries into one immutable normalized private-update record. Application code never receives raw Telegram JSON.

`PrivateInboundKind` exactly:

`COMMAND | CALLBACK | UNAUTHORIZED | UNSUPPORTED | MALFORMED`

Normalized fields are limited to:

`kind, update_id, user_id, chat_id, command, callback_query_id, callback_token`

Only authorized COMMAND/CALLBACK records contain principal/action material. Unauthorized/unsupported/malformed records must not retain arbitrary input text. Generic repr must redact the callback token.

## Private commands and private activation

Private chat is administration only; it is never a Codex prompt ingress.

P4.1 does not provide a private ACTIVE action. Fleet activation remains group-only because ADR-0002 requires the same human-originated group message to be observed by all controllers. P4.2 may display effective mode/status and may separately consider a safe local SLEEP-only control, but private ACTIVE remains forbidden unless a future ADR replaces the fleet ordering model.

## Durable private-menu ingress

Add one narrow schema-v1 repository for authorized private command dedupe. It inserts `ingress_updates.disposition = CONTROL` without mutating `controller_runtime`.

Exact semantics:

- new authorized command update -> insert one completed `CONTROL` ingress record;
- existing update ID -> return duplicate with the exact existing ingress and zero mutation/clock;
- no raw command text is stored;
- no controller mode/epoch mutation occurs.

Unauthorized message updates use accepted `IngressUpdateRepository.claim_ignored(..., IGNORED_UNAUTHORIZED)` so no unauthorized text is retained.

Callbacks are not deduped through `ingress_updates`; their server-side opaque `callback_actions` token is the one-time idempotency authority. This avoids a crash window where update-ID dedupe could commit before callback consumption and permanently suppress the action.

## Opaque callback data

Telegram callback data carries no trusted business parameter.

Exact callback-data grammar:

`cc1:<token>`

where `<token>` is exactly 32 URL-safe base64 characters `[A-Za-z0-9_-]{32}`. Default generation uses `secrets.token_urlsafe(24)`. Total callback data length is 36 bytes, below Telegram's 64-byte limit.

Persist only `sha256(token UTF-8).hexdigest()` in `callback_actions`. Generic logs/reprs/evidence never contain the raw token. A generated-token hash collision with an existing callback row fails `INVARIANT`; P4.1 does not retry silently.

`P4_PRIVATE_CALLBACK_TTL_MS = 900000` (15 minutes).

Application code reads its clock once for a render batch and constructs callback records with a repository clock pinned to that validated timestamp, so callback expiry is deterministic and cannot become caller `INVALID_ARGUMENT` because of a second stepped clock read.

## Callback action vocabulary

P4.1 creates only these `callback_actions.action` values:

- `OPEN_ROOT`
- `OPEN_PROFILES`
- `OPEN_MODELS`
- `OPEN_REASONING`
- `SELECT_PROFILE`
- `SELECT_MODEL`
- `SELECT_REASONING`

Exact `subject_type` values:

- navigation: `panel`;
- profile choice: `profile_choice`;
- model choice: `model_choice`;
- reasoning choice: `reasoning_choice`.

Navigation `subject_id` is a bounded decimal page index.

Choice `subject_id` is `sha256(target UTF-8).hexdigest()`. This is required for all choices, including models, because accepted model IDs may be up to 256 characters while schema-v1 callback subject IDs are 128 characters. On callback, the service re-resolves the current authorized option set and requires exactly one option whose target fingerprint matches. It never reconstructs a trusted target from callback data.

## Expected version/state binding

Every rendered callback is bound to the current settings version and current dialogue state snapshot.

`expected_state` is exactly:

- `NO_DIALOGUE` when there is no live dialogue; otherwise
- the exact `DialogueState.value`.

Selection callback creation rules:

- profile selection callbacks exist only in `NO_DIALOGUE`;
- model/reasoning selection callbacks exist only in `NO_DIALOGUE` or exact `IDLE`;
- no selection callback is emitted while create/run/interrupt/delete/unknown/error state forbids the underlying P3.3 mutation.

After one-time callback claim, P4.1 obtains a fresh settings view and requires exact settings version plus dialogue state equality before business mutation. A mismatch is `STALE`, with zero settings mutation. The callback remains consumed because stale one-time actions must not become replayable.

## P3.3 composition

P4.1 is only UI/orchestration over accepted `SettingsSelectionService`; it never reproduces settings/codex-catalog locking rules.

Target resolution is followed by exactly one corresponding call:

- `select_profile(target, expected_version=record.expected_version)`;
- `select_model(target, expected_version=record.expected_version)`;
- `select_reasoning_effort(target, expected_version=record.expected_version)`.

P3.3 remains final mutation authority, including authenticated fresh catalog validation and dialogue/profile/model/reasoning locks.

Mapping:

- P3.3 `UPDATED` -> P4.1 `UPDATED`;
- `NO_CHANGE` -> `NO_CHANGE`;
- `CONFLICT` -> `STALE`;
- `BLOCKED` -> `BLOCKED` with the exact finite P3.3 mutation reason projected safely;
- P3.3 `STORAGE` -> P4.1 `STORAGE` error;
- P3.3 `INVALID_ARGUMENT` or `INVARIANT` from P4-owned validated values -> P4.1 `INVARIANT`.

## Callback claim mapping

Use accepted `CallbackActionRepository.claim` before any settings mutation.

- `CLAIMED` -> validate exact P4 action/subject/version/state then continue;
- `NOT_FOUND` -> `STALE` / `CALLBACK_NOT_FOUND`;
- `UNAUTHORIZED` -> `UNAUTHORIZED`, no panel, token remains unconsumed by accepted P2.3 authority;
- `EXPIRED` -> `EXPIRED`;
- `ALREADY_CONSUMED` -> `ALREADY_USED`.

Malformed/corrupt claimed callback records fail `INVARIANT` without mutation.

## Panel model

P4.1 adds a Telegram-independent semantic settings panel plus a pure Telegram renderer.

`PrivatePanelSection` exactly:

`ROOT | PROFILES | MODELS | REASONING`

`P4_PRIVATE_PAGE_SIZE = 8`.

A panel may expose only safe operator-visible values:

- configured server display name/ID;
- selected profile display name/ID;
- selected model display name/ID;
- reasoning effort;
- live dialogue state (`NO_DIALOGUE` or enum value);
- authenticated catalog availability.

It must not display/store:

- CODEX_HOME;
- raw thread ID;
- Codex turn ID;
- prompts/outputs;
- raw Telegram update JSON;
- tokens/hashes;
- raw exception bodies.

Choice lists are deterministic and paginated at eight options per page. Button labels are plain-text normalized to one line and bounded to 64 characters. Telegram rendering uses no HTML/Markdown parse mode. Panel text is bounded to 3500 characters. Callback data is always opaque `cc1:<token>`.

Generic button/panel repr must redact callback data.

## Public application surface

Add `PrivateSettingsManagementService` with exactly:

- `handle_command(request)`
- `handle_callback(request)`

Public request/result records are frozen and payload-safe.

`PrivateAdminStatus` exactly:

`RENDERED | UPDATED | NO_CHANGE | BLOCKED | STALE | EXPIRED | ALREADY_USED | DUPLICATE | UNAUTHORIZED | UNSUPPORTED`

`PrivateAdminErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`

Unauthorized results contain no panel. Duplicate command updates create no new callback rows and return no duplicate panel/send authority.

## Navigation and refresh

Navigation callbacks are also one-time and version/state-bound. If a navigation callback is stale, return `STALE`; an authorized stale result may include a newly rendered fresh ROOT panel so the operator can continue safely. Rendering that fresh panel creates a new bounded callback set.

No business mutation is performed by navigation.

## Security and cancellation

P4.1 performs no Telegram/Codex/network external effect. Callback consumption is durable before settings mutation. If the caller is cancelled after callback consumption but before mutation, the action remains consumed; no automatic retry occurs. The operator may open a fresh panel and choose again.

No private command or callback can create a turn/job/dialogue, call Codex, activate routing, interrupt, delete, approve, or send Telegram traffic in P4.1.

## Acceptance

P4.1 must prove at least:

- raw Telegram parsing/auth fail-closed for wrong user/chat/type/bot sender/malformed shapes;
- unauthorized/unsupported records retain no raw text/token;
- private commands never become prompt/JOB ingress;
- authorized menu command creates exactly one durable CONTROL ingress; duplicate creates no new callback actions;
- unauthorized message records IGNORED_UNAUTHORIZED with no content;
- opaque callback grammar <=64 bytes and contains no action/target;
- callback token hash only is durable;
- wrong callback user/chat cannot consume the operator token;
- expired/already-used/not-found mapping;
- exact settings version/dialogue state stale protection;
- profile mutation through real P3.3 with NO_DIALOGUE only;
- model/reasoning mutation through real P3.3 with authenticated catalog and IDLE/no-dialogue locks;
- 256-character model target resolves through fingerprint without schema change;
- hidden/unavailable model and unsupported effort never receive a valid mutation action;
- page size/label/text bounds;
- renderer contains no parse mode/CODEX_HOME/thread/token leakage;
- corruption/redaction fail closed;
- no real Telegram/Codex/network effect;
- all accepted P3/P2/P1 regressions and exact schema-v1 DDL hash remain unchanged.

Final P4 private-management acceptance is later P4.3; P4.1 does not claim P4 complete.
