# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema target is version `2` under accepted P2.C2; exact v2 migration ID `0002_ingress_rejected_disposition`, migration-statement SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796, failures 0, errors 0, unittest `OK`.
- P2.C2 acceptance authority: `docs/evidence/p2/P2_C2_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
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
- P5.1 accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- P5.1 acceptance authority: `docs/evidence/p5/P5_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- No live Telegram/network acceptance has occurred.

## Current slice

**P5.2 — NEXT / architect research + freeze.**

P5.2 owns serialized ordinary authorized group TEXT admission only:

- preserve P5.1 exact group/operator trust edge and control classification;
- SLEEP prompt -> terminal content-free `IGNORED_SLEEP`;
- ACTIVE prompt -> delegate to accepted P3 dialogue-turn application authority;
- BUSY and other pre-JOB rejected prompt outcomes -> terminal content-free `IGNORED_REJECTED` from accepted P2.C2;
- duplicate updates never later execute;
- no queue;
- control-before-prompt ordering under one local group-ingress serialization boundary;
- no second prompt/job state machine on top of P3;
- no direct Codex protocol/lifecycle calls outside accepted P3.

P5.3 later owns fleet status/version mismatch safeguards and final fake multi-controller group-routing acceptance. P6 owns delivery/full orchestration and live P1.7 approval-response coordination.

## Binding accepted P5.1 authority consumed by P5.2

P5.1 freezes:

- immutable `FleetMember` / `FleetManifest`;
- persistent fleet reply keyboard;
- exact operator + exact negative control-supergroup + human-origin trust edge;
- authorization before raw message text access;
- reserved activation/control-looking namespace before ordinary TEXT;
- self activation -> ACTIVE; other/unknown activation -> SLEEP; all-sleep -> SLEEP;
- STATUS read-only/no control epoch mutation;
- current-boot effective mode from durable controller epoch relative to captured boot baseline;
- historical persisted ACTIVE is effectively SLEEP after restart until a fresh current-boot self activation;
- old boot service fails closed;
- P5.1 TEXT itself creates no ingress/JOB/payload/P3/Codex effect.

## Binding accepted P2.C2 replay guard

`IngressDispositionKind` exact current order:

`CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | IGNORED_REJECTED | JOB`.

`IGNORED_REJECTED` means an authorized ordinary prompt update was terminally rejected before JOB/external effect. It stores no prompt text and no reason prose.

Duplicate `claim_ignored` is clock-free and never reclassifies the original durable ingress. Therefore once P5.2 terminalizes a BUSY/BLOCKED update as `IGNORED_REJECTED`, the same Telegram update can never later execute after state changes.

## P5.2 non-goals

Do not start:

- P5.3 fleet-status/final multi-controller acceptance;
- response delivery/P6;
- live approval response/waiter;
- Telegram HTTP/polling/webhook/token loading;
- production config/secrets/systemd;
- real Codex/network effects;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.