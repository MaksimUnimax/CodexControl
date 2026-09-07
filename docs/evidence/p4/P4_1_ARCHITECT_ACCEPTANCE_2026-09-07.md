# P4.1 architect acceptance

Date: 2026-09-07
Status: ARCHITECT_ACCEPTED

Accepted implementation/proof HEAD: `5a7db46c6e06662c379149c454c06003d48feb30`.
Original architect base: `7778ba0fa1f4d5334de3edf38b8539f4a9eeb9ff`.
Rejected first candidate: `3c4272b469df6a00d6ca4796eef42cb2be13695a`.
Issue: #28.
Architect review: `5567080615`.
Binding authority: ADR-0032.

Independent GitHub review confirmed a linear two-commit P4.1 implementation lineage above the exact architect base: the rejected candidate followed by exactly one repair commit. The cumulative diff contains only P4.1 Telegram-adapter/application/storage surfaces, narrow package exports, focused tests and factual implementation evidence. No accepted P1/P2/P3 production authority, architecture ADR, roadmap authority or schema/DDL was modified by the implementation branch.

The private trust edge is fail-closed. Only the exact configured operator in exact private chat with a non-bot sender can produce authorized COMMAND/CALLBACK records. Exact `/start`, `/menu` and `/settings` are supported; arbitrary private text is UNSUPPORTED and never becomes prompt/JOB ingress. Wrong principal/chat/type is unauthorized, malformed shapes are rejected, raw Telegram payload/text is not retained, and callback tokens are redacted from generic representations.

Authorized private menu commands use the additive schema-v1 private-management repository to persist exactly one completed CONTROL ingress without mutating `controller_runtime`; duplicate update IDs create no new callback rows or panel authority. Unauthorized private-message ingress uses the accepted `IGNORED_UNAUTHORIZED` no-content path. Private ACTIVE/group routing remains absent.

Callback data is the exact opaque `cc1:<32-char URL-safe token>` form. Only SHA-256 token hashes are durable. Callback batches are atomic, share one validated created/expiry timestamp, use the exact 900000 ms TTL, carry no trusted business target in Telegram callback data, and never silently retry a token collision. Choice targets are SHA-256 fingerprints, including accepted 256-character model IDs.

The first repair closes both architect blockers. When the settings singleton is absent, an authorized menu command still claims CONTROL but returns `BLOCKED / SETTINGS_MISSING` with a static ROOT panel containing zero rows, zero callback records and no token/TTL generation. No fabricated settings version exists, so later initialization at real version 0 cannot revive old callback authority. Existing durable callback-hash collisions from callback batch creation now map to P4.1 `INVARIANT`, preserve the pre-existing row, commit no partial new rows and do not regenerate another token.

Callback claims preserve accepted P2.3 one-time semantics: wrong principal cannot consume the operator token; not-found, expired and replay are finite; claimed callbacks bind exact settings version and exact `NO_DIALOGUE`/dialogue state. Version/state mismatch is STALE with zero settings mutation. Callback consumption precedes mutation and cancellation does not cause automatic replay.

Profile, model and reasoning selection delegate to accepted P3.3 `SettingsSelectionService` exactly once. Profile callbacks are actionable only with no live dialogue; model/reasoning only with no dialogue or IDLE. Model choices use authenticated visible catalog projection, hidden/unavailable models do not become valid mutation authority, and reasoning is limited to advertised efforts.

The semantic panel/render boundary is bounded and content-safe: eight options per page, button labels <=64 characters, panel text <=3500 characters, plain Telegram-like dictionaries with no parse mode, no CODEX_HOME, raw thread/turn IDs, prompt/output, callback hash/token or raw exception data.

Executor-reported focused counts after repair: P4.1 `8 unit / 15 integration`. Accepted pre-P4 full suite authority was `671`; expected and observed full discovery are `694` (`671 + 8 + 15`). Required prior focused regressions were reported unchanged, including P3.5 `12/25/1`, P3.4 `6/31`, P3.3 `5/25`, P3.2 `2/21`, P3.1 `11/26`, P2.C1 `5/1`, P2.6b `5/12/8/3`, P2.6a `4/28`, P2.5 `4/18`, P2.4b `6/25`, P2.4a `8/31`, P2.3 `7/28`, P2.2 `6/20`, P2.1 `8/31`, P1.9 `15`, P1.8 `28`, and P1.10 `6/1/4`.

Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`. Compileall, import smoke, diff checks and secret/redaction checks are reported PASS. The known P1.6 pending-task warning remains pre-existing and was not introduced by P4.1.

GitHub exposes no attached commit status checks or pull-request workflow runs for `5a7db46c6e06662c379149c454c06003d48feb30`; acceptance therefore relies on independent exact GitHub code/diff review plus the executor's isolated focused/full-regression evidence, consistent with project governance.

P4.1 performs no real Telegram/network/Codex/thread/turn/interrupt/delete/approval/delivery effect and touches no production database/state/service. Live Telegram acceptance remains later roadmap authority.

P4.1 is complete and architect-accepted. P4.2 requires separate architect authority before implementation; this record does not authorize P4.2 execution.
