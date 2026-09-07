# ADR-0035 — P5.1 fleet manifest, group normalization and current-boot control routing

Status: Accepted
Date: 2026-09-07

## Context

P4 is complete at the fake/application private-management boundary. P5 now owns the group surface described by ADR-0002, ADR-0003 and ADR-0010: every configured bot must observe the same human-originated supergroup control message, use the supergroup message ID as the fleet control epoch, start every process effectively SLEEP, activate only itself on its exact server button, sleep on another or unknown activation target, and never let control-looking text fall through as a Codex prompt.

P2.3 already owns the durable atomic primitive `ControlIngressRepository.claim_control(update_id, control_epoch, requested_mode)`. P5.1 must compose that accepted primitive without changing schema or starting Codex prompt execution. Ordinary group prompt admission, BUSY and SLEEP prompt disposition are P5.2. Fleet status/version mismatch acceptance is P5.3. Live Telegram transport remains P9.

## Slice boundary

P5.1 owns only:

1. an immutable shared non-secret fleet manifest;
2. a pure persistent Telegram reply-keyboard renderer;
3. fail-closed normalization/classification of untrusted Telegram-like group messages;
4. exact operator/control-supergroup authorization;
5. durable activation/all-sleep routing over accepted P2.3 control claims;
6. current-boot effective-mode projection that cannot restore historical ACTIVE;
7. serialized local control handling;
8. read-only STATUS classification/projection sufficient for later P5.3 composition.

P5.1 does NOT own:

- Telegram HTTP, polling, webhook or bot-token loading;
- private Telegram surfaces;
- ordinary prompt admission/JOB creation/P3 invocation;
- BUSY or response delivery;
- fleet-wide status delivery or peer communication;
- approval orchestration;
- live Codex effects;
- deployment TOML/secrets wiring;
- P5.2/P5.3/P6+.

No schema/DDL change is allowed.

## P5 split

P5 is frozen as three architect slices:

- **P5.1:** manifest + reply keyboard + group normalization + current-boot durable control routing.
- **P5.2:** serialized group prompt admission: SLEEP terminal ignore, ACTIVE P3 turn admission, duplicate/no-queue/BUSY behavior.
- **P5.3:** fleet status/version safeguards and final fake multi-controller group-routing acceptance.

P5.1 must not start P5.2/P5.3.

## Constants and bounds

P5.1 freezes:

- `P5_ACTIVATION_PREFIX = "🖥 "`
- `P5_ALL_SLEEP_LABEL = "💤 ВСЕ СПАТЬ"`
- `P5_STATUS_LABEL = "📊 СТАТУС"`
- `P5_FLEET_MAX_MEMBERS = 32`
- `P5_SERVER_ID_MAX_CHARS = 128`
- `P5_DISPLAY_NAME_MAX_CHARS = 64`
- `P5_FLEET_VERSION_MAX_CHARS = 128`
- `P5_GROUP_TEXT_MAX_CHARS = 4096`

Server IDs and fleet versions are nonempty ASCII identifiers using only letters, digits, `_ . : -`. Display names preserve useful Unicode but must be one-line, nonempty, <=64 characters, contain no control characters, have no leading/trailing whitespace and already be whitespace-collapsed. Member server IDs and display names are each unique.

## Fleet manifest

Add frozen:

`FleetMember(server_id, display_name)`

and:

`FleetManifest(fleet_version, members)`

where `members` is an ordered tuple of 1..32 exact `FleetMember` values.

The manifest contains no token, CODEX_HOME, chat ID, operator ID, host path or other secret. Adding server-N changes manifest/configuration data, not routing source.

A service may start only when its exact `server_id` appears exactly once in the manifest and the boot record's `fleet_version` exactly equals the manifest `fleet_version`.

P5.1 does not extend `ServerConfiguration`/`parse_server_configuration`; production deployment/config-file materialization belongs to later deployment composition. Tests construct the manifest explicitly.

## Persistent fleet keyboard

Add pure `TelegramFleetKeyboardRenderer.render(manifest)`.

It returns only a Telegram-like `ReplyKeyboardMarkup` dictionary:

- activation buttons in manifest order, two per row;
- button text is exactly `P5_ACTIVATION_PREFIX + member.display_name`;
- final row contains exact `P5_ALL_SLEEP_LABEL`, then exact `P5_STATUS_LABEL`;
- `resize_keyboard = True`;
- `is_persistent = True`.

Each button is represented only by its text. No callback data, URL, web_app, request-contact/location, selective targeting, send call or network action exists.

The same manifest must render byte-semantically equivalent keyboard data on every controller regardless of which member is local.

## Group normalized contracts

`GroupInboundKind` exactly:

`CONTROL | TEXT | UNAUTHORIZED | UNSUPPORTED | MALFORMED`

`GroupControlKind` exactly:

`ACTIVATE | ALL_SLEEP | STATUS`

Add frozen repr-safe:

`GroupInboundUpdate(kind, update_id, message_id, user_id, chat_id, control, target_server_id, text)`.

Only authorized ordinary `TEXT` may retain its text in memory. Its repr always shows the text as `[REDACTED]`. CONTROL never retains raw label text. UNAUTHORIZED/UNSUPPORTED/MALFORMED retain no text/control target material beyond safe parsed numeric metadata needed by the application.

Shape rules:

- CONTROL/ACTIVATE: valid IDs/principal, `control=ACTIVATE`, `target_server_id` is a known manifest server ID or `None`, `text=None`.
- CONTROL/ALL_SLEEP or STATUS: valid IDs/principal, no target, no text.
- TEXT: valid IDs/principal, no control/target, nonempty bounded text.
- UNAUTHORIZED: no text/control/target.
- UNSUPPORTED: no text/control/target.
- MALFORMED: no text/control/target; numeric metadata may be absent when it could not be validated.

## Pure group adapter

Add:

`TelegramGroupUpdateAdapter(manifest, operator_user_id, control_chat_id)`

with one public method:

`normalize(raw_update) -> GroupInboundUpdate`.

It receives raw Telegram-like dictionaries only at the adapter boundary. Application code never receives raw JSON.

A potentially authorized group message requires:

- valid nonnegative signed-64 `update_id`;
- exactly one ordinary `message` surface for this adapter;
- valid positive signed-64 `message.message_id`;
- `message.from` and `message.chat` dictionaries;
- positive exact sender ID;
- nonzero signed-64 chat ID;
- `from.is_bot` exactly `False`;
- no non-NULL `sender_chat` anonymous/channel-origin authority;
- sender ID exactly configured operator;
- chat ID exactly configured control chat;
- `chat.type` exactly `supergroup`.

`control_chat_id` itself is configured as an exact negative signed-64 ID. The adapter checks principal/chat/user-origin authority before inspecting or retaining `message.text`.

Wrong sender, bot sender, anonymous/channel-origin message, wrong chat ID or wrong chat type => UNAUTHORIZED. Structurally invalid fields => MALFORMED. An authenticated non-text message => UNSUPPORTED.

## Text/control classification order

After authorization only:

1. exact known activation label => CONTROL/ACTIVATE with the exact known server ID;
2. any other text beginning exact `P5_ACTIVATION_PREFIX` => CONTROL/ACTIVATE with `target_server_id=None`;
3. exact `P5_ALL_SLEEP_LABEL` => CONTROL/ALL_SLEEP;
4. exact `P5_STATUS_LABEL` => CONTROL/STATUS;
5. slash-command-looking text (`/…`) => UNSUPPORTED;
6. other control-looking emoji-prefix variants beginning, after left trim, `🖥`, `💤` or `📊` => UNSUPPORTED;
7. empty text, text containing NUL, or text longer than `P5_GROUP_TEXT_MAX_CHARS` => UNSUPPORTED/MALFORMED fail-closed with no retained text;
8. otherwise => TEXT with exact original text retained only in the immutable normalized object.

Exact button text is required to activate a known server. Near-miss/control-looking text never becomes a prompt. The only unknown activation family that mutates mode is the exact reserved `P5_ACTIVATION_PREFIX` family, and it always maps the local controller to SLEEP.

## Current-boot mode authority

Historical persisted `requested_mode=ACTIVE` is not effective-mode authority after restart.

`FleetControlService` constructor receives the exact accepted `ControllerBootResult` returned by the current process's `ControllerRuntimeRepository.begin_boot(manifest.fleet_version)`.

Constructor freezes:

- `boot_generation = boot.record.boot_generation`;
- `boot_baseline_control_epoch = boot.record.last_control_epoch`.

It requires:

- `boot.effective_mode is ControllerMode.SLEEP`;
- boot record fleet version equals manifest fleet version;
- exact local server exists in manifest;
- valid operator/control-chat IDs.

Every authorized control/read path re-reads `ControllerRuntimeRepository.get()` and fails INVARIANT if:

- the row is missing/corrupt;
- `boot_generation` differs from captured generation;
- fleet version differs from captured manifest version;
- `last_control_epoch < boot_baseline_control_epoch`.

Effective mode is derived only as:

```text
if current.last_control_epoch <= boot_baseline_control_epoch:
    SLEEP
else:
    current.requested_mode
```

Thus persisted historical ACTIVE at the captured baseline is diagnostics/history only. A fresh current-boot control with a strictly newer epoch is required before ACTIVE can become effective.

No process-local boolean is accepted as mode authority.

## Mode snapshot

Add frozen repr-safe:

`FleetModeSnapshot(server_id, effective_mode, boot_generation, last_control_epoch, fleet_version)`.

It contains no requested historical mode, path, token or content.

## Fleet control service

Add:

`FleetControlService(storage, manifest, server_id, operator_user_id, control_chat_id, boot_result, now_ms=None)`.

Public methods exactly:

- `handle(update)`
- `current_mode()`

Both are async. One application-level `asyncio.Lock` serializes local group control handling/current-mode reads. The service does no background work and creates no tasks for retry.

`FleetControlStatus` exactly:

`APPLIED | STALE | DUPLICATE | STATUS | TEXT | UNAUTHORIZED | UNSUPPORTED | MALFORMED`

`FleetControlResult(status, snapshot)` is frozen and content-free. Snapshot is required for APPLIED/STALE/DUPLICATE/STATUS/TEXT and absent for UNAUTHORIZED/UNSUPPORTED/MALFORMED.

`FleetControlErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`

with finite content-free `FleetControlError`.

## Authorization at application boundary

The service accepts only exact `GroupInboundUpdate`. It does not trust a caller merely because the adapter normally creates the record.

Any CONTROL/TEXT record whose user/chat do not equal configured operator/control chat is handled as unauthorized. Adapter-marked UNAUTHORIZED remains unauthorized even if some numeric fields happen to match. No snapshot/status detail is returned to unauthorized callers.

For a valid UNAUTHORIZED update with a durable update ID, call accepted:

`IngressUpdateRepository.claim_ignored(update_id, IGNORED_UNAUTHORIZED)`

and return UNAUTHORIZED regardless of duplicate disposition. This stores no message content and never changes mode.

MALFORMED and UNSUPPORTED perform no mode mutation and no prompt/JOB creation.

## Control routing

Before any authorized mutating control claim, the service validates the captured current-boot authority by reading the current mode snapshot.

Mapping:

- ACTIVATE target == local server -> requested ACTIVE;
- ACTIVATE target != local server, including `None` unknown -> requested SLEEP;
- ALL_SLEEP -> requested SLEEP;
- STATUS -> no `claim_control`, no ingress/mode mutation.

For ACTIVATE/ALL_SLEEP call accepted P2.3 exactly once:

`ControlIngressRepository.claim_control(update_id=update.update_id, control_epoch=update.message_id, requested_mode=...)`.

The service does not duplicate P2.3 SQL or parse labels at repository level.

Map exact P2.3 result:

- APPLIED -> `FleetControlStatus.APPLIED`;
- STALE -> `FleetControlStatus.STALE`;
- DUPLICATE -> `FleetControlStatus.DUPLICATE`.

After the durable claim returns, re-read the current-boot mode snapshot and return it. APPLIED/STALE controller records from P2.3 must be canonical and compatible with the captured boot/fleet authority; impossible result shapes fail INVARIANT.

A fresh self activation while already ACTIVE still advances epoch and returns APPLIED/ACTIVE. Another/unknown activation and ALL_SLEEP return/leave SLEEP when applied.

STATUS only returns `FleetControlStatus.STATUS` plus a current snapshot. It never calls `claim_control` and never advances epoch.

## Ordinary TEXT boundary

P5.1 does not decide SLEEP ignore, ACTIVE JOB admission or BUSY.

For an authorized TEXT record:

- re-read/return the current `FleetModeSnapshot`;
- return `FleetControlStatus.TEXT`;
- insert no ingress row;
- create no JOB/transient payload;
- call no P3/Codex service;
- persist no text.

P5.2 will consume the original normalized TEXT under the final group-ingress sequencing/admission authority.

## Cancellation/restart safety

P2.1/P2.3 own transaction completion under coroutine cancellation. P5.1 must not cache mode as a correctness requirement.

If a control transaction commits and the application coroutine is cancelled before it can return, a later `current_mode()` or `handle()` derives the committed current-boot mode from durable controller state relative to the captured baseline. No replay is needed.

Tests must deterministically prove both committed ACTIVE and committed SLEEP remain observable after an injected post-commit cancellation.

A service instance from an older boot generation fails closed when its next authorized current-mode/control path observes a different boot generation. Operationally the process-locked SQLite lifecycle prevents two live controller processes from sharing one state DB; no new cross-process coordinator is introduced.

## Serialization

P5.1 serializes local `handle`/mode reads with one lock so two group controls cannot race within one controller process. P2.3 epoch CAS remains durable authority.

P5.1 does not yet hold a lock across P3 turn execution; prompt/control sequencing beyond control classification belongs to P5.2.

No positive sleeps are allowed in concurrency tests.

## Security/redaction

P5.1 never persists or logs raw group text, raw update JSON or credentials. `GroupInboundUpdate.__repr__` redacts TEXT. Result/error/snapshot reprs are content-free.

No CODEX_HOME, prompt, callback token, thread/job/turn IDs, raw errors, environment or bot token appear in P5.1 output/evidence.

## Acceptance

P5.1 focused tests must prove at least:

- exact enums/records/bounds and frozen reprs;
- manifest uniqueness/validation and local-member requirement;
- identical persistent keyboard for the same manifest;
- group authorization matrix and auth-before-text retention;
- known self/other/unknown activation parsing;
- control-looking and command-looking text never becomes TEXT;
- restart with persisted historical ACTIVE starts effective SLEEP;
- fresh self activation -> ACTIVE;
- other/unknown/all-sleep -> SLEEP;
- fresh same-mode control advances epoch;
- stale epoch cannot mutate mode;
- duplicate update cannot mutate mode or call clock;
- STATUS does not call control claim or advance epoch;
- TEXT creates no ingress/JOB/P3 effect;
- unauthorized message stores only IGNORED_UNAUTHORIZED with no text;
- post-commit cancellation is healed by durable-derived mode for both ACTIVE and SLEEP;
- old boot-generation service fails closed;
- frozen DDL and all accepted P4/P3/P2/P1 regressions remain green;
- no real Telegram/network/Codex/production effect.

No final P5 multi-controller acceptance occurs in P5.1; that belongs to P5.3.
