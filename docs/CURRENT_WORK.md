# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema is version `2`; migration ID `0002_ingress_rejected_disposition`; migration SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.
- P3 is COMPLETE at the fake/application dialogue boundary; P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P4 is COMPLETE at the fake/application private-management boundary; P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P5 is COMPLETE at the fake/application group-routing boundary; P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; final P5 full 860.
- P6.1 accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900. Acceptance: `docs/evidence/p6/P6_1_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- P6.2 accepted `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`; full 922. Acceptance: `docs/evidence/p6/P6_2_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- No live Telegram/network acceptance has occurred.

## P6.2 accepted authority

P6.2 closes the fake/application live-approval boundary under ADR-0040:

- exact live P1.7 `InboundServerRequest` identity remains sole wire-response authority;
- durable P2.4b `ApprovalRecord.state` remains sole ALLOW/DENY decision authority;
- `ApprovalRepository.terminalize_pending(... EXPIRED|CANCELLED)` is the only additive approval transition;
- `ApprovalDecisionSignal.notify()` is process-local wake-only coordination;
- PENDING is durable before waiting;
- real P4.3 Allow/Deny can wake the accepted P6.2 operator and produce one exact P1.7 response;
- every private wake/timer task is owned and joined;
- failed async expiry infrastructure is not expiry authority and cannot fabricate a decision;
- protocol terminal yields `RESPONSE_UNKNOWN` plus best-effort CANCELLED cleanup;
- process/client restart destroys old wire ownership; durable approval metadata never replays an old response.

## Current slice

**P6.3 — NEXT / AUTHORITY FROZEN under ADR-0041.**

P6.3 is the final P6 slice. It composes already-accepted authorities without adding durable state:

- approval-aware P1.6 turn lifecycle that captures the exact runtime object used by `turn/start` and pumps exact P1.7 server requests while the same turn is running;
- one-attempt, process-local safe work-status hint that may become P6.1's first-EDIT target only after final delivery planning;
- private P4.3 callback composition that only pulses the shared P6.2 wake signal;
- successful P3 terminal results into accepted P6.1 final delivery;
- FAILED/UNKNOWN live turns into one-attempt safe non-success status only, never P6.1 output delivery;
- narrow read-only `TurnJobRepository.list_delivery_candidates(*, limit)` for startup successful-delivery recovery;
- accepted P3.5 startup recovery before bounded oldest-first P6.1 recovery;
- final `LocalControllerOrchestrator` facade and fake P6 acceptance.

The early work-status message is intentionally non-durable and is never replayed after restart. A confirmed status message ID becomes durable only indirectly if accepted P6.1 later commits it into the immutable first-segment EDIT plan.

P6.3 startup recovery processes at most 256 delivery candidates per explicit pass and returns LIMIT_REACHED if more remain. It does not start a background worker. Later live Telegram wiring must not enable ingestion until startup recovery is ready.

If a turn terminal races a still-live approval, P6.3 does not guess ALLOW/DENY: it terminates the exact captured runtime, joins accepted P6.2/P1.7 to `RESPONSE_UNKNOWN`, best-effort cleans the pending approval and projects the turn UNKNOWN.

## P6 split

- **P6.1 — DONE:** durable successful-response delivery. Accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900.
- **P6.2 — DONE:** durable live approval operator + owned P1.7 response. Accepted `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`; full 922.
- **P6.3 — NEXT / AUTHORITY FROZEN:** final local orchestration, acknowledgement/status hint, approval pump, startup delivery recovery and final fake P6 acceptance under ADR-0041.

P6 is NOT complete until P6.3 is independently architect-accepted.

## Current non-goals

Do not start live Telegram HTTP/polling/webhook/token loading, production config/secrets/systemd, live backlog/offset acceptance, real Codex/network effects, P7 or later work inside P6.3.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
