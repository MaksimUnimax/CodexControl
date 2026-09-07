# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- P3.1 accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`; full 543.
- P3.2 accepted `c484c56db007569170363b3d08c24766148c3e30`; full 566.
- P3.3 accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full 596.
- P3.4 accepted `6460a449f861b7b86ab664e5ff877c108715082d`; full 633.
- P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P3 is complete at the fake/application boundary.
- P4.1 accepted after one repair at `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- P4.2 accepted after two repairs at `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- P4.3 accepted after one proof/contract repair at `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762, failures 0, errors 0, unittest `OK`.
- P4.3 acceptance authority: `docs/evidence/p4/P4_3_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P4.1/P4.2/P4.3 are accepted. **P4 is COMPLETE at the fake/application private-management boundary.**
- No live Telegram/network acceptance has occurred; live T4/T5 remains later roadmap authority.

## Current slice

**P5.1 — NEXT / AUTHORITY FROZEN under ADR-0035.**

P5.1 owns only the group/fleet control-plane foundation:

- shared immutable non-secret fleet manifest;
- pure persistent Telegram reply-keyboard rendering;
- fail-closed group update normalization and exact group/operator authorization;
- activation/all-sleep parsing before any prompt classification;
- unknown activation-prefix fail-safe local SLEEP;
- serialized durable control claims over accepted P2.3;
- current-boot effective-mode projection that never restores historical ACTIVE;
- STATUS as read-only/no control-epoch mutation;
- TEXT classification only, with no ingress/JOB/P3/Codex effect in P5.1.

P5.2 later owns ACTIVE/SLEEP ordinary text admission, BUSY/no queue and P3 turn composition. P5.3 later owns fleet status/version safeguards and final fake multi-controller group-routing acceptance. P6 remains response delivery/full orchestration including live P1.7 approval-response coordination.

## Binding existing fleet decisions

ADR-0002: persistent reply-keyboard server presses are human messages visible to all bots; self activation -> ACTIVE, other/unknown activation -> SLEEP; inline callbacks cannot provide fleet-wide routing.

ADR-0003: every boot is effectively SLEEP; historical persisted ACTIVE is never restored; ordered supergroup `message_id` is control epoch; stale control cannot override newer control; local group processing is serialized.

ADR-0010: fleet identity/display labels/version are shared non-secret configuration; server-N addition is config/deployment only; activation prefix remains fail-safe across mismatch.

ADR-0020: accepted P2.3 `ControlIngressRepository.claim_control(update_id, control_epoch, requested_mode)` is the only durable control mutation primitive consumed by P5.1. STATUS never calls it.

## P5.1 frozen manifest/keyboard

Constants:

- `P5_ACTIVATION_PREFIX = "🖥 "`
- `P5_ALL_SLEEP_LABEL = "💤 ВСЕ СПАТЬ"`
- `P5_STATUS_LABEL = "📊 СТАТУС"`
- max fleet members 32
- server ID max 128
- display name max 64
- fleet version max 128
- group text max 4096

Public immutable values:

- `FleetMember(server_id, display_name)`
- `FleetManifest(fleet_version, members)`

Manifest server IDs and display names are unique. Server IDs/fleet version are sanitized non-secret identifiers. Display names are one-line normalized Unicode. Local server must occur exactly once and boot fleet version must equal manifest fleet version.

`TelegramFleetKeyboardRenderer.render(manifest)` renders activation buttons in manifest order, two per row, plus final `[💤 ВСЕ СПАТЬ] [📊 СТАТУС]`, with `resize_keyboard=True` and `is_persistent=True`. It performs no Telegram/network effect.

P5.1 deliberately does not extend `ServerConfiguration`/production TOML parsing; deployment/config-file composition remains later authority.

## P5.1 group normalization

`GroupInboundKind` exactly:

`CONTROL | TEXT | UNAUTHORIZED | UNSUPPORTED | MALFORMED`.

`GroupControlKind` exactly:

`ACTIVATE | ALL_SLEEP | STATUS`.

Frozen `GroupInboundUpdate` fields exactly:

`kind, update_id, message_id, user_id, chat_id, control, target_server_id, text`.

TEXT is repr-redacted. CONTROL retains no raw label. Unauthorized/unsupported/malformed records retain no text/action target material.

`TelegramGroupUpdateAdapter(manifest, operator_user_id, control_chat_id).normalize(raw)` is pure and requires for authorized input:

- valid update ID and positive message ID;
- exact operator `from.id`;
- `from.is_bot is False`;
- no anonymous/channel `sender_chat`;
- exact configured negative control chat;
- `chat.type == "supergroup"`;
- ordinary message surface.

Authorization is resolved before text inspection/retention.

Classification order after auth:

1. exact known activation label -> ACTIVATE known server;
2. other exact activation-prefix text -> ACTIVATE unknown target (`None`), therefore later local SLEEP;
3. exact all-sleep;
4. exact status;
5. slash command -> UNSUPPORTED;
6. other control-looking `🖥`/`💤`/`📊` variants -> UNSUPPORTED;
7. invalid/empty/oversize text -> fail closed;
8. otherwise TEXT.

Control-looking content never becomes a Codex prompt.

## P5.1 current-boot effective mode

`FleetControlService` receives the exact current `ControllerBootResult` returned from `ControllerRuntimeRepository.begin_boot(manifest.fleet_version)`.

It captures:

- `boot_generation`;
- `boot_baseline_control_epoch = boot.record.last_control_epoch`.

It requires `boot.effective_mode == SLEEP`.

Every authorized read/control path re-reads `controller_runtime` and requires same captured boot generation/fleet version and `last_control_epoch >= baseline`.

Effective mode is derived only as:

```text
last_control_epoch <= boot_baseline_control_epoch -> SLEEP
last_control_epoch >  boot_baseline_control_epoch -> current requested_mode
```

Therefore a persisted ACTIVE at boot baseline remains historical only. No process-local ACTIVE boolean is correctness authority.

Public frozen `FleetModeSnapshot` fields:

`server_id, effective_mode, boot_generation, last_control_epoch, fleet_version`.

## P5.1 service

`FleetControlService` public async methods exactly:

- `handle(update)`
- `current_mode()`

`FleetControlStatus` exactly:

`APPLIED | STALE | DUPLICATE | STATUS | TEXT | UNAUTHORIZED | UNSUPPORTED | MALFORMED`.

Frozen `FleetControlResult(status, snapshot)` contains no content.

`FleetControlErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

One application lock serializes local group control handling/mode reads.

Control mapping:

- ACTIVATE self -> P2.3 requested ACTIVE;
- ACTIVATE other/unknown -> SLEEP;
- ALL_SLEEP -> SLEEP;
- STATUS -> no `claim_control`, no epoch/mode mutation.

P2.3 `APPLIED/STALE/DUPLICATE` map directly to P5.1 statuses and then the service re-reads current durable mode snapshot.

Unauthorized valid update IDs may be durably recorded only as `IGNORED_UNAUTHORIZED`, with no content/mode mutation.

TEXT returns current mode snapshot only. It inserts no ingress, creates no JOB/payload and calls no P3/Codex service. P5.2 owns text execution policy.

## Cancellation/restart rule

P5.1 never depends on a process-local mode cache for correctness. If P2.3 commits a control and the caller is cancelled before P5.1 returns, the next mode read derives the committed mode from durable state relative to boot baseline. Tests must prove both ACTIVE and SLEEP post-commit cancellation cases.

A service instance observing a different boot generation fails closed. No background retry or replay.

## Current non-goals

Do not start:

- P5.2 prompt admission/BUSY;
- P5.3 fleet status/final multi-controller acceptance;
- P6 delivery/approval response orchestration;
- live Telegram transport;
- production config/secrets/systemd;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
