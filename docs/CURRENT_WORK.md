# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema target is version `2` under accepted P2.C2; migration ID `0002_ingress_rejected_disposition`; migration-statement SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796. Acceptance: `docs/evidence/p2/P2_C2_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- P3.1 accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`; full 543.
- P3.2 accepted `c484c56db007569170363b3d08c24766148c3e30`; full 566.
- P3.3 accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full 596.
- P3.4 accepted `6460a449f861b7b86ab664e5ff877c108715082d`; full 633.
- P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P3 is complete at the fake/application boundary.
- P4.1 accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- P4.2 accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P4 is COMPLETE at the fake/application private-management boundary.
- P5.1 accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777. Acceptance: `docs/evidence/p5/P5_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- P5.2 accepted `345c48722c4faa03be19d38b6f07304276075f64`; full 841, failures 0, errors 0, unittest `OK`.
- P5.2 acceptance: `docs/evidence/p5/P5_2_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- No live Telegram/network acceptance has occurred.

## Current slice

**P5.3 — NEXT / AUTHORITY FROZEN under ADR-0038.**

P5.3 closes the fake/application P5 milestone with:

1. deterministic local fleet-status identity/projection;
2. human-visible fleet-version/manifest mismatch diagnostics;
3. final fake multi-controller group-routing acceptance.

P5.3 does not add a coordinator, peer RPC or shared runtime database.

## Fleet status identity

Every exact accepted `FleetManifest` has a deterministic lowercase SHA-256 identity over the NUL-separated canonical sequence:

`codex-control-fleet-v1`, exact `fleet_version`, decimal member count, then each exact `server_id` and `display_name` in manifest order.

This fingerprint is diagnostic metadata only. It never authorizes activation or any external effect.

P5.3 status exposes both:

- exact configured `fleet_version`;
- full manifest SHA-256 identity.

Therefore mismatch is visible even when two controllers accidentally reuse the same `fleet_version` string with different member lists/order/labels.

## Status projection

P5.3 adds pure `FleetStatusService` over an exact P5.2 STATUS result.

Frozen `FleetStatusProjection` fields exactly:

`server_id, display_name, effective_mode, fleet_version, manifest_fingerprint_sha256, member_count, boot_generation, last_control_epoch`.

The service requires the P5.2 STATUS snapshot to match its configured local server and manifest version. Malformed/mismatched local composition fails `INVARIANT`.

No storage read, clock read, mode mutation or network action occurs in status projection.

Pure `TelegramFleetStatusRenderer` returns only `{"text": ...}`. The text includes local display/server identity, ACTIVE/SLEEP, fleet version, member count, first 16 manifest-fingerprint hex characters, boot generation and control epoch. No parse mode, callbacks or send/edit action.

## Version-mismatch safety

P5.3 does not attempt distributed peer compatibility decisions.

Runtime safety remains accepted P5.1 reserved activation parsing:

- a new controller that knows a new server label parses exact ACTIVATE target=new server;
- an old controller whose manifest does not contain that label still sees the reserved `🖥 ` prefix and parses ACTIVATE target=None;
- the old controller therefore applies local SLEEP;
- neither controller may treat the activation-looking text as a Codex prompt.

Status responses make the different fleet version/fingerprint visible to the operator.

## Final fake multi-controller acceptance

The final P5 acceptance must compose separate temporary SQLite/controller stacks with the real accepted group adapter, keyboard, P5.1 control service, P5.2 routing facade, status projection/renderer and accepted P3 orchestration with fake local P1 lifecycle ports.

For matching manifests it proves:

- all controllers boot effective SLEEP;
- identical persistent keyboards;
- exact target activation makes target ACTIVE and non-target SLEEP;
- ordinary prompt executes only on ACTIVE target and is terminally SLEEP-ignored elsewhere;
- switching activation moves routing authority;
- all-sleep sleeps all controllers;
- STATUS is read-only and produces matching fleet identity values;
- restart after historical ACTIVE returns effective SLEEP and no local P5.2 queue/marker is restored;
- no prompt executes after restart until a fresh current-boot activation is processed.

For mismatched old/new manifests it proves:

- fleet version/fingerprint difference is visible;
- new-server activation is exact on the new controller;
- old controller treats it as reserved unknown activation and sleeps;
- old controller performs zero P3 prompt execution from that control text;
- all-sleep and STATUS remain common safe controls.

## Offline/restart boundary

P5.3 proves the accepted local application restart invariant only. It does not claim to distinguish a Telegram message sent before restart but delivered only afterwards from a genuinely fresh operator message. Live polling offset/backlog behavior remains later P9/P11 acceptance authority.

## P5 split

- **P5.1 — DONE:** accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- **P5.2 — DONE:** accepted `345c48722c4faa03be19d38b6f07304276075f64`; full 841.
- **P5.3 — NEXT / AUTHORITY FROZEN:** ADR-0038 fleet status identity/version-mismatch visibility + final fake multi-controller routing acceptance.

## Current non-goals

Do not start:

- P6 response delivery/approval-response orchestration;
- Telegram HTTP/polling/webhook/token loading;
- production config/secrets/systemd;
- live backlog/offset acceptance;
- real Codex/network effects;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
