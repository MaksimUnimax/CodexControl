# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema target is version `2` under accepted P2.C2; migration ID `0002_ingress_rejected_disposition`; migration-statement SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.
- P3 is COMPLETE at the fake/application dialogue boundary; P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P4 is COMPLETE at the fake/application private-management boundary; P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P5 is COMPLETE at the fake/application group-routing boundary; P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; final P5 full 860.
- P6.1 accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900, failures 0, errors 0, unittest `OK`.
- P6.1 acceptance: `docs/evidence/p6/P6_1_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- No live Telegram/network acceptance has occurred.

## P6.1 accepted response-delivery authority

Accepted P2.4b remains the sole durable delivery outbox authority. P6.1 adds only the application composition needed to turn one successful P3 OUTPUT into an immutable DISPLAY delivery plan and execute it one attempt at a time.

Accepted P6.1 invariants include:

- exact successful OUTPUT lookup through additive read-only `TransientPayloadRepository.get_output_for_job(job_id)`;
- exact fallback `✅ Выполнено` when a successful completed job has no OUTPUT;
- deterministic exact-preserving segmentation with configured 512..4096 character limit;
- preferred paragraph/line/space/hard-cut boundaries, but deterministic hard-cut fallback if the preferred pass would exceed P2.4b's 4096-segment bound;
- input fails closed if even hard-cut segmentation would exceed 4096 segments;
- one transient DISPLAY payload per chunk;
- initial all-CREATE plan or first-EDIT plan when an already-known status message ID is supplied;
- durable `SENDING/attempt1` before every Telegram delivery effect;
- at most one CREATE/EDIT effect attempt per segment;
- confirmed prefix is never resent;
- already durable SENDING is never retried and becomes `DELIVERY_UNKNOWN/TELEGRAM_RECOVERY_AMBIGUOUS` with zero new Telegram effect;
- caller cancellation does not cancel or redispatch an owned Telegram effect;
- storage failure after an external effect never causes immediate resend;
- Codex FAILED/UNKNOWN jobs are outside P6.1 successful-response delivery;
- P2.5 delete readiness remains unchanged and blocks hard delete while delivery is incomplete/ambiguous.

## Current slice

**P6.2 — NEXT / ARCHITECT RESEARCH.**

P6.2 must connect accepted P1.7 bidirectional approval-request ownership to accepted P2.4b/P4.3 durable operator decision authority and then return the exact ALLOW/DENY response to the still-owned P1.7 request.

The architecture is not frozen until the exact ownership, cancellation, timeout, duplicate-decision and restart boundaries are independently re-read from current P1.7/P2.4b/P4.3 production and tests.

## P6 split

- **P6.1 — DONE:** successful completed-job response segmentation + durable one-attempt delivery. Accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900.
- **P6.2 — NEXT / RESEARCH:** live approval request persistence/wait/decision/response coordination at the fake/application boundary.
- **P6.3 — LATER:** acknowledgement/progress composition, startup delivery discovery, full local fake orchestration/recovery and final P6 acceptance.

## Current non-goals

Do not start implementation of P6.2 until architect authority is frozen.

Do not start:

- P6.3 full local orchestration;
- live Telegram HTTP/polling/webhook/token loading;
- production config/secrets/systemd;
- live backlog/offset acceptance;
- real Codex/network effects;
- P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
