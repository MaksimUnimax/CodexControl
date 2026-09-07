# P4.1 private Telegram settings implementation evidence

Status: implementation evidence only; this document does not claim architect acceptance or mark P4.1 complete.

## Authority and boundary

- Repository: `MaksimUnimax/CodexControl`
- Issue: `#28 — P4.1 — private Telegram auth + settings panel`
- Architect base: `7778ba0fa1f4d5334de3edf38b8539f4a9eeb9ff`
- Branch: `impl-p4-1-private-settings-ui-2026-09-07`
- Binding ADR: `docs/adr/0032-private-telegram-settings-management.md`
- Accepted P3.5: `6145d262787465ac6b4a17327114211cd86e8104`
- Production paths: `adapters/telegram/private_updates.py`, `adapters/telegram/private_render.py`, `application/private_settings.py`, and `storage/private_management.py`, with narrow package exports.

The implementation uses only the fake Telegram-shaped boundary, temporary SQLite in tests, and fake authenticated catalogs. It contains no Telegram transport, polling, webhook, HTTP, token loading, Codex/process/network effect, production configuration/state/service change, schema change, group routing, ACTIVE control, interrupt, delete, approval, diagnostics, delivery, or P4.2/P4.3/P5 work.

## Contracts and authorization

`PrivateInboundKind`, `PrivateCommand`, and the frozen `PrivateInboundUpdate` implement the exact normalized adapter surface. The adapter accepts only a positive configured operator ID, exact supported `/start`, `/menu`, and `/settings` text, exact private operator chat, non-bot sender, and the exact callback envelope. Wrong user/chat/type or bot sender is `UNAUTHORIZED`; malformed IDs/shapes and inline-only callbacks are `MALFORMED`; authorized unknown/non-text messages are `UNSUPPORTED`. Raw private text, raw Telegram dictionaries, and wrong-principal callback data are not retained in normalized records or generic representations.

`PrivateCommandRequest` and `PrivateCallbackRequest` are frozen. Callback request, button, panel, and result representations redact callback tokens; panel/button representations do not emit callback data. Display strings are one-line normalized and bounded to 64-character labels and 3500-character panel text. The renderer returns only `text`, `reply_markup.inline_keyboard`, button `text`, and opaque `callback_data`; it emits no parse mode or other Telegram fields.

## Durable ingress and callbacks

`PrivateManagementRepository.claim_private_command` inserts one completed `CONTROL` ingress row with the same validated received/completed timestamp and does not touch `controller_runtime`. Existing update IDs return duplicate without a clock read or mutation. Unauthorized command requests use accepted `IGNORED_UNAUTHORIZED` ingress and no content; unsupported authorized text creates no ingress, job, payload, or callback.

Rendered callback data is exactly `cc1:<32-character [A-Za-z0-9_-] token>` and is 36 bytes. The default token factory is `secrets.token_urlsafe(24)`. Only the SHA-256 token digest is sent to SQLite. A render batch reads the application clock once, validates `0..MAX_SQLITE_INT`, uses exactly `900000` ms TTL, and atomically inserts the complete callback set with one created/expiry pair. Hash collisions fail closed and are not retried; transaction failure rolls back the whole batch. Callback actions are limited to `OPEN_ROOT`, `OPEN_PROFILES`, `OPEN_MODELS`, `OPEN_REASONING`, `SELECT_PROFILE`, `SELECT_MODEL`, and `SELECT_REASONING`.

Callbacks are authorized before token grammar/hash/claim processing. Existing P2.3 claim mapping is preserved: claimed continues, missing is `STALE/CALLBACK_NOT_FOUND`, wrong principal is `UNAUTHORIZED` without consumption, expired is `EXPIRED`, and replay is `ALREADY_USED`. Claimed actions bind exact settings version and `NO_DIALOGUE` or exact dialogue state. Version/state mismatch consumes the callback and returns `STALE/STALE_ACTION` without settings mutation.

## Settings composition

Panels expose only safe server/profile/model/reasoning/dialogue/catalog values. Profiles and authenticated visible model options use deterministic P3.3 projections and eight-option pages; navigation is server-side page subjects. Choice subjects are SHA-256 fingerprints, including the full 256-character model-ID case. Callback handling re-resolves current authorized options, requires exactly one fingerprint match, and never trusts a target encoded in callback data.

Profile, model, and reasoning mutations call the accepted `SettingsSelectionService` exactly once per selection. Profile callbacks are emitted only for `NO_DIALOGUE`; model/reasoning callbacks only for `NO_DIALOGUE` or `IDLE`. P3.3 finite outcomes map to the P4.1 finite result/error contract, including settings-missing, profile lock/configuration, dialogue lock, model, effort, stale, storage, and invariant outcomes. Successful selection returns `UPDATED`/`NO_CHANGE` without requiring a second panel render.

Callback claim precedes any possible P3.3 mutation. Cancellation after claim leaves the action consumed and does not trigger a retry. Corrupt claimed action material fails closed as `INVARIANT` with no raw sentinel, token, hash, catalog error, thread/turn ID, prompt/output, environment, or exception body in generic errors.

## Verification

- P4.1 focused unit tests: 8 (`tests/unit/test_private_telegram_settings.py`).
- P4.1 focused integration tests: 12 (`tests/integration/test_private_telegram_settings.py`).
- Focused P4.1 total: 20.
- Explicit prior-slice regression command: 358 tests, `OK`.
- Accepted pre-P4 full count: 671.
- Full discovery command: 691 tests, `OK`.
- Full arithmetic: `671 + 8 + 12 = 691`.
- Frozen DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- Required public import smoke: `P4_1_IMPORT_PASS`.
- `git diff --check`: passed before final commit.
- Secret/effect scan: no credentials, bot tokens, private keys, production paths, raw callback token/hash persistence, raw Telegram JSON, content, environment dump, or external-effect path found in P4.1 production files. Test-only synthetic identifiers are isolated fixtures.

The known P1.6 pending-task warning was observed during full discovery; it is pre-existing and no new P4.1 leak was identified. Prior regression counts remain the required authority: P3.5 `12/25/1`; P3.4 `6/31`; P3.3 `5/25`; P3.2 `2/21`; P3.1 `11/26`; P2.C1 `5/1`; P2.6b `5/12/8/3`; P2.6a `4/28`; P2.5 `4/18`; P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`; P2.2 `6/20`; P2.1 `8/31`; P1.9 `15`; P1.8 `28`; P1.10 `6/1/4`. No architect acceptance is claimed.
