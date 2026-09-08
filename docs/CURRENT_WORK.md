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
- P3 is COMPLETE at the fake/application dialogue boundary.
- P4.1 accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- P4.2 accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P4 is COMPLETE at the fake/application private-management boundary.
- P5.1 accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- P5.2 accepted `345c48722c4faa03be19d38b6f07304276075f64`; full 841.
- P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; final P5 full 860.
- P5.3 acceptance: `docs/evidence/p5/P5_3_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- P5 is COMPLETE at the fake/application group-routing boundary.
- No live Telegram/network acceptance has occurred.

## Current slice

**P6.1 — NEXT / AUTHORITY FROZEN under ADR-0039.**

P6 is split into three architecture slices:

- **P6.1 — NEXT:** successful completed-job response segmentation + durable one-attempt delivery over accepted P2.4b and a fake/application Telegram delivery port;
- **P6.2 — LATER:** durable approval operator coordination from accepted P1.7 request ownership through P2.4b/P4.3 decision state back to the P1.7 response owner;
- **P6.3 — LATER:** full local fake orchestration/recovery, acknowledgement/progress composition, startup delivery discovery and final P6 acceptance.

## P6.1 content authority

Accepted P3 remains the only Codex output projection authority. P6.1 may deliver only:

- the exact accepted P3 transient `OUTPUT` bytes for a successful `CODEX_COMPLETED` job, decoded strict UTF-8; or
- exact fallback `✅ Выполнено` when the successful job has no OUTPUT payload.

P6.1 does not deliver Codex FAILED/UNKNOWN jobs; later P6.3 owns safe failure/status UX.

A narrow additive read-only `TransientPayloadRepository.get_output_for_job(job_id)` is authorized so an explicit delivery invocation after restart can recover an unplanned successful output without duplicating persistence SQL/materialization. It adds no schema or new durable state.

## P6.1 segmentation authority

Configured text limit is exact 512..4096 characters. Deterministic segmentation preserves the source exactly and prefers, in order, the farthest paragraph boundary, line boundary, ASCII-space boundary, then a hard Unicode code-point cut. No Markdown/HTML parse mode or text normalization is used.

The 512 lower bound ensures the accepted maximum P3 projected output fits within P2.4b's maximum 4096 delivery segments.

## P6.1 durable one-attempt authority

Accepted P2.4b remains sole outbox state authority:

`CODEX_COMPLETED -> DELIVERY_PENDING -> DELIVERING -> DELIVERED | DELIVERY_UNKNOWN | FAILED`.

P6.1 creates transient `DISPLAY` chunks, creates one immutable P2.4b plan, then for each pending segment:

1. commits accepted `claim_next` so the exact segment is durable `SENDING/attempt1` before external effect;
2. invokes exactly one fake/application Telegram CREATE or EDIT effect;
3. commits accepted `finish_sending` with CONFIRMED/UNKNOWN/FAILED.

Confirmed segments are never recreated. UNKNOWN and delivery FAILED are terminal and never automatically retried.

If a new delivery invocation observes an already `SENDING` segment, it performs **zero Telegram effect** and terminalizes that exact segment as `UNKNOWN/TELEGRAM_RECOVERY_AMBIGUOUS`. This is the restart/crash no-blind-resend rule.

A confirmed prefix followed only by pending segments is safe to resume from the first pending segment.

## Existing-status edit boundary

`TurnDeliveryRequest` may optionally carry an already-known status message ID. Only when creating the initial durable plan, segment 1 becomes EDIT to that exact message and later segments are CREATE. Without a status message ID all segments are CREATE.

P6.1 does not create the initial acknowledgement/progress message; P6.3 owns that composition. Once a durable plan exists, it is sole authority and a later request hint cannot rewrite it.

## Cancellation/error boundary

P6.1 owns one local delivery task and shields an already-owned Telegram effect from caller cancellation. It never redispatches an effect because a caller was cancelled.

Malformed/exception/ambiguous port results after durable SENDING are captured as DELIVERY_UNKNOWN, not retried. A storage failure after a possible external effect does not cause immediate resend; a later invocation sees stranded SENDING and applies recovery UNKNOWN.

## Current non-goals

Do not start:

- P6.2 approval-response coordination;
- P6.3 full local orchestration;
- live Telegram HTTP/polling/webhook/token loading;
- live backlog/offset acceptance;
- production config/secrets/systemd;
- real Codex/network effects;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
