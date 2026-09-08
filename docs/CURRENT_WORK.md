# Current work authority

Date: 2026-09-08

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Historical schema-v1 DDL SHA-256 remains immutable: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Current schema target is version `2`; migration ID `0002_ingress_rejected_disposition`; migration SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.
- P3 is COMPLETE at the fake/application dialogue boundary; P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; final P3 full 671.
- P4 is COMPLETE at the fake/application private-management boundary; P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final P4 full 762.
- P5 is COMPLETE at the fake/application group-routing boundary; P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; final P5 full 860.
- P6.1 accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900. Acceptance: `docs/evidence/p6/P6_1_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- No live Telegram/network acceptance has occurred.

## Current slice

**P6.2 — NEXT / AUTHORITY FROZEN under ADR-0040.**

P6.2 connects exact live P1.7 approval request ownership to durable P2.4b/P4.3 operator decisions and back to exactly one P1.7 response attempt, without live Telegram HTTP and without reconstructing wire authority after restart.

## Frozen P6.2 authority

P1.7 remains sole wire authority. An old `InboundServerRequest` cannot be reconstructed from durable approval metadata after process/client restart.

P2.4b remains sole durable decision authority. P6.2 adds exactly one narrow repository method:

`ApprovalRepository.terminalize_pending(approval_id, *, target_state)`

where target state is only `EXPIRED` or `CANCELLED`. Existing terminal decisions are returned unchanged; expiry is due-time guarded; CANCELLED may close a still-PENDING live approval when exact P1.7 request ownership is lost. No callback token is consumed by this method.

`ApprovalDecisionSignal` is process-local wake-only coordination. `notify()` grants nothing; every waiter re-reads its durable approval state. Waiter registration precedes publication of PENDING state so a fast callback cannot be missed.

`DurableApprovalOperator` is bound to one exact running job/profile/thread/Codex turn. It validates normalized P1.7 requests against that binding, creates optional transient APPROVAL details from the already-bounded P1.7 context, persists PENDING before waiting, and returns only from durable terminal state:

- APPROVED -> P1.7 ALLOW;
- DENIED/EXPIRED/CANCELLED -> P1.7 DENY.

Approval TTL and APPROVAL payload retention are both exactly 900000 ms.

After a PENDING approval exists, storage/read failure must never be turned into a fabricated DENY while the row remains actionable. Safety wins over liveness: the operator remains waiting for durable authority or protocol terminal rather than creating a contradictory wire decision.

`OwnedApprovalResponseService` accepts only an already-owned exact `InboundServerRequest`, internally uses accepted `CodexApprovalBridge.handle_request`, and shields the owned bridge task from ordinary caller cancellation. This prevents an outer cancellation from replacing a durable Allow with P1.7's cancellation-path Deny. P6.2 does not dequeue requests; P6.3 owns that full turn/request concurrency.

On protocol terminal the operator best-effort terminalizes still-PENDING state as CANCELLED and P1.7 returns RESPONSE_UNKNOWN/no retry. On process restart old wire response authority is gone permanently; approval metadata is never replayed into a new client.

P6.2 does not modify accepted P4.3. P6.3 later pulses `ApprovalDecisionSignal.notify()` after private callback processing. P6.2 fake integration proves real P4.3 Allow/Deny mutation followed by signal wake and real P1.7 method-specific response mapping.

## P6 split

- **P6.1 — DONE:** accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900.
- **P6.2 — NEXT / AUTHORITY FROZEN:** durable live approval operator + owned P1.7 response under ADR-0040.
- **P6.3 — LATER:** request dequeue/turn concurrency, acknowledgement/progress, startup delivery discovery, full local fake orchestration/recovery and final P6 acceptance.

## Current non-goals

Do not start P6.3, live Telegram HTTP/polling/webhook/token loading, production config/secrets/systemd, live backlog/offset acceptance, real Codex/network effects, or P7+.

Known P1.6 pending-task warning remains pre-existing test hygiene debt unless a new leak is independently proven.
