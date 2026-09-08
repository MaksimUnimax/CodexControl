# ADR-0041 — P6.3 final local orchestration and fake P6 acceptance

Status: Accepted
Date: 2026-09-08

## Context

P6.1 accepted durable successful-response delivery over P2.4b. P6.2 accepted durable live approval decisions and exact P1.7 response ownership. P5 already owns group routing; P4 owns private management; P3 owns durable dialogue/turn state and startup reconciliation.

The remaining P6 work is composition. It must make a real local turn concurrently service Codex approval server requests, create a safe live status hint, deliver successful terminal output, wake approval waiters after private callbacks, recover stranded successful delivery on startup and prove the complete fake/application path without introducing Telegram HTTP or real Codex effects.

No schema change is required.

## Lower authority remains unchanged

- P1.6 remains sole `turn/start`, turn-notification collector and interrupt wire authority.
- P1.7 remains sole exact server-request dequeue/response protocol authority.
- P2/P3 remain sole durable dialogue/job/recovery authority.
- P4.3 remains sole private approval callback mutation authority.
- P5.2 remains sole group admission/BUSY/no-queue authority.
- P6.1 remains sole durable successful final-response delivery authority.
- P6.2 remains sole durable live approval decision operator authority.

P6.3 may compose these authorities but may not recreate their state machines.

## Scope

P6.3 owns:

1. an approval-aware P1.6 turn-lifecycle wrapper that captures the exact runtime used by `turn/start` and pumps P1.7 requests while waiting for the exact turn terminal;
2. one best-effort, one-attempt live work-status message used as an optional P6.1 first-EDIT hint;
3. a final local group/private orchestration facade;
4. wake-only P6.2 signal composition after accepted private callbacks;
5. bounded startup successful-delivery discovery and composition after accepted P3.5 startup recovery;
6. final fake P6 acceptance across group prompt, live approval, final delivery, cancellation and restart.

No Telegram HTTP/polling/webhook, real Codex process, production config, systemd, live backlog or deployment is included.

## Constants

Exactly:

- `P63_STARTUP_DELIVERY_MAX_JOBS = 256`
- `P63_WORK_STATUS_TEXT_MAX_CHARS = 1024`

## Work status is deliberately non-durable

The early work-status message is UX metadata, not final response/outbox authority.

For a newly admitted job already durably in `CODEX_STARTING`, P6.3 attempts exactly one plain-text CREATE containing only bounded non-secret job metadata:

```text
⏳ Выполняю запрос
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

The prompt, output, thread ID, turn ID, job ID and raw errors never appear.

The attempt uses the accepted P6.1 `TelegramDeliveryPort` but does not create a P2.4b delivery plan. It is never automatically retried.

- CONFIRMED -> keep the exact returned message ID only in process memory as the job's status hint.
- FAILED -> no hint; continue the Codex turn.
- UNKNOWN, malformed result or effect exception -> no hint; never retry; continue the turn.

A status hint is never durable merely because its CREATE was confirmed. If the process dies before P6.1 creates a final delivery plan, the hint is forgotten and startup final delivery uses CREATE. A stale live `⏳` message may therefore remain after a crash. This is the intentional fail-safe tradeoff that avoids a new durable status-message state machine.

Once accepted P6.1 creates an immutable final plan with the confirmed hint as first-segment EDIT target, that target is durable P2.4b authority and normal P6.1 restart semantics apply.

P6.3 never replays the early status CREATE after restart.

## Non-success live status

For a live P3 FAILED or UNKNOWN result, P6.3 makes at most one safe status attempt:

FAILED:

```text
❌ Выполнение завершилось с ошибкой
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

UNKNOWN:

```text
⚠️ Результат выполнения не подтверждён
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

If a confirmed live status hint exists, use one EDIT to that exact ID; otherwise use one CREATE. No retry and no startup replay. A malformed/ambiguous status effect is local UNKNOWN only; it never changes the already-durable P3 terminal job state.

P6.1 remains successful-output-only.

## ApprovalAwareTurnLifecycle

Add an application component implementing the accepted P3/P3.4 lifecycle surfaces:

- `start_turn(...) -> TurnStartResult`
- `wait_turn(binding) -> TurnTerminalResult`
- `interrupt_turn(binding) -> TurnInterruptResult`

It internally delegates exact wire behavior to one accepted `CodexTurnLifecycleAdapter`.

The wrapper receives:

- exact local `SqliteStorage`;
- a runtime-manager port exposing async `acquire(profile_id)` and `shutdown_profile(profile_id)`;
- the accepted model-catalog port used by P1.6;
- accepted `TelegramDeliveryPort` for the live work-status attempt;
- the shared accepted P6.2 `ApprovalDecisionSignal`;
- bounded clock/ID seams.

No new turn state is added.

## Exact runtime capture

P6.3 must never reacquire a runtime later and assume it is the runtime that owns the active server request.

The wrapper injects a private capture-manager proxy into the accepted `CodexTurnLifecycleAdapter`. During one reserved `start_turn` invocation, the proxy delegates `acquire(profile_id)` to the configured runtime manager and captures the exact runtime object returned to P1.6.

Concurrent direct `start_turn` calls do not queue behind this capture reservation; the second call fails with accepted TURN_OPERATION_BUSY semantics.

On confirmed start, P6.3 binds by object identity:

`exact TurnBinding object -> exact captured runtime object + exact durable job ID`.

`wait_turn` and `interrupt_turn` reject reconstructed/equal-but-not-identical bindings.

No runtime/client/thread/turn identity is serialized by P6.3.

## CODEX_STARTING job discovery

Immediately before delegating `turn/start`, P3 has already persisted the job as `CODEX_STARTING` and dialogue as TURN_RUNNING.

P6.3 uses accepted `ApplicationRecoveryRepository.inspect()` as a read-only canonical snapshot and requires exactly one active job with:

- state `CODEX_STARTING`;
- exact profile/thread matching the `ThreadBinding`;
- exact model/reasoning matching the P1.6 start request;
- no Codex turn ID yet.

This supplies the exact job/chat metadata for the work-status attempt without modifying P3 or adding a storage query.

Any mismatch fails closed before delegating `turn/start`.

## Approval pump during wait_turn

After P3 marks the same job `CODEX_RUNNING`, `wait_turn(binding)` validates the exact durable job/profile/thread/Codex-turn relation and creates an exact P6.2 `ApprovalTurnBinding`.

It then owns concurrently:

- accepted P1.6 `delegate.wait_turn(binding)`;
- at most one `client.next_server_request()` task;
- at most one accepted P6.2 `OwnedApprovalResponseService.handle_owned(inbound)` task.

There is no application queue and no periodic polling.

For every exact dequeued server request, the request must still be owned by the exact captured runtime client by object identity before P6.2 handles it.

After ALLOWED or DENIED, the pump may await the next request. `RESPONSE_UNKNOWN` is terminal approval ambiguity and forces the P6.3 projected turn result to UNKNOWN even if a competing turn terminal looked successful.

Multiple sequential approvals in one turn are supported; they are handled one at a time.

## Turn terminal versus request dequeue

If the turn terminal wins while P6.3 is merely waiting on `next_server_request`, P6.3 cancels and joins that exact queue-get task.

If the cancellation race nevertheless returns an exact owned request, the turn is already terminal and that request is answered once with accepted P1.7 method-specific DENY through a local immediate-deny operator; no durable PENDING approval is published. This anomalous ordering forces the overall projected turn result to UNKNOWN and the profile runtime is shut down to invalidate any additional unresolved server requests.

If the queue-get cancels cleanly with no request ownership, the original turn terminal remains authoritative.

## Turn terminal while an approval is already live

A turn terminal arriving while an accepted P6.2 owned approval task is still waiting is an anomalous ownership conflict.

P6.3 does not cancel `handle_owned` and does not substitute a guessed DENY. It invokes the configured runtime manager's exact `shutdown_profile(profile_id)` to make the protocol terminal, then joins the P6.2 task. Accepted P6.2/P1.7 therefore yields RESPONSE_UNKNOWN and best-effort CANCELLED cleanup of a still-PENDING approval without a replacement response.

The P6.3 projected turn result is UNKNOWN regardless of the competing P1.6 terminal value.

No automatic runtime restart is performed by P6.3.

## Approval pump task ownership

Every request-get, approval-handler and turn-terminal helper is owned, observed, cancelled/joined on every exit. No P6.3 helper may remain pending after `wait_turn` returns.

Caller cancellation does not abandon an already-owned turn/approval/wire effect. Existing P3 and P6.2 ownership semantics remain binding.

## Interrupt delegation

`interrupt_turn(binding)` requires the exact live P6.3 binding lease and delegates exactly once to the same accepted P1.6 lifecycle instance that started that turn. It never reacquires another runtime or reconstructs a binding.

P3.4 remains durable interrupt authority.

## Private approval wake composition

P6.3 wraps accepted `PrivateControlService` without changing it.

Public private-callback handling owns the accepted P4.3 callback invocation through completion. After a normal authorized/non-UNAUTHORIZED callback result that may change or stale an approval, P6.3 calls the shared `ApprovalDecisionSignal.notify()` exactly once.

At minimum `APPROVED`, `DENIED`, `EXPIRED`, `STALE` and `ALREADY_USED` wake the signal. The signal remains wake-only; the P6.2 operator re-reads durable state.

No callback result itself becomes ALLOW/DENY wire authority.

## Successful final delivery composition

P6.3 wraps accepted `FleetGroupRoutingService`.

For the first invocation that returns exact P5.2 PROMPT with P3 COMPLETED and a canonical durable job, P6.3 invokes accepted P6.1 exactly once:

`TurnDeliveryRequest(job_id, status_message_id=<confirmed live hint or None>)`.

P6.1 remains sole final response delivery authority.

DUPLICATE routing never starts another delivery invocation. If the original process dies before immediate delivery, startup discovery owns recovery.

FAILED/UNKNOWN P3 results never enter P6.1; only the one-attempt non-success status behavior above applies.

The overall group orchestration task is owned through prompt terminalization and final delivery/status handling; outer caller cancellation never causes a second P3 or Telegram effect.

## Fleet STATUS composition

Exact P5.2 STATUS is projected through accepted `FleetStatusService` and `TelegramFleetStatusRenderer` and returned as the pure one-key `{"text": ...}` payload for the future Telegram transport layer. P6.3 does not send a durable STATUS message.

## TurnJobRepository delivery discovery

Add exactly one narrow read-only public method:

`list_delivery_candidates(*, limit) -> tuple[TurnJobRecord, ...]`

Input `limit` is an exact non-bool integer 1..4096.

It performs one read-only callback, zero clock and zero writes, selecting only exact states:

- `CODEX_COMPLETED`
- `DELIVERY_PENDING`
- `DELIVERING`

ordered by:

`created_at_ms ASC, job_id ASC`

and limited by the exact caller limit.

Every row is materialized through accepted canonical job materialization.

No generic job listing/search API is added.

## Startup composition

Add a final local startup method. It must run before live Telegram polling is enabled by later deployment work.

Ordering:

1. accepted `DialogueRecoveryService.recover_startup()` exactly once;
2. if that recovery terminalized an old active job, call accepted `ApprovalRepository.cancel_pending_for_job(job_id)` after the job is no longer CODEX_RUNNING;
3. repeatedly discover the oldest successful delivery candidate and invoke accepted P6.1 with `status_message_id=None`;
4. process at most `P63_STARTUP_DELIVERY_MAX_JOBS` candidates in one invocation;
5. after the bound, perform one final read to determine whether backlog remains.

Every successfully handled candidate must leave the discovery state set (`CODEX_COMPLETED|DELIVERY_PENDING|DELIVERING`) as DELIVERED, FAILED or DELIVERY_UNKNOWN before the next candidate is selected.

A stranded SENDING candidate therefore follows accepted P6.1 zero-resend recovery to DELIVERY_UNKNOWN. A confirmed-prefix candidate resumes from its first pending segment. A CODEX_COMPLETED candidate creates a new final plan with all CREATE because process-local work-status hints are never restored.

If more candidates remain after 256, startup returns an explicit LIMIT_REACHED result and later live-input wiring must not begin until an explicit subsequent recovery pass succeeds. P6.3 itself does not create a background recovery worker.

## LocalControllerOrchestrator

Add one final application facade with exactly these public business methods:

- `handle_group(update)`
- `handle_private_command(request)`
- `handle_private_callback(request)`
- `recover_startup()`

It composes accepted P4/P5/P6 services and the exact shared `ApprovalAwareTurnLifecycle`/signal. It does not normalize raw Telegram JSON; accepted Telegram adapters remain transport-boundary normalization authority.

Group results are repr-redacted and contain only accepted routing/delivery objects, pure STATUS payload and finite work-status outcomes. No prompt/output/message IDs appear in generic repr.

## Startup readiness boundary

P6.3 does not start Telegram polling. Later P8/P9 wiring MUST call `recover_startup()` to a non-LIMIT_REACHED successful result before enabling live update ingestion.

The controller still boots effective SLEEP under accepted P5.1 regardless of recovery outcome.

## Final fake P6 acceptance

P6.3 final acceptance must use temporary SQLite, exact transport-independent `CodexProtocolClient`, accepted P1.6/P1.7/P3/P4/P5/P6.1/P6.2 components and fake Telegram effects only.

It must prove at least:

1. boot/recovery before input and effective SLEEP;
2. authorized raw group activation via accepted group adapter;
3. raw group prompt enters accepted P5.2/P3 lazy/existing dialogue flow;
4. durable CODEX_STARTING exists before the one work-status CREATE;
5. confirmed work-status ID becomes only a process-local hint;
6. exact runtime captured by the P1.6 start call is the runtime whose client owns approval requests;
7. a real P1.7 approval server request is dequeued while P1.6 wait_turn is still pending;
8. real private P4.3 Allow through P6.3 private wrapper wakes P6.2 automatically and produces exactly one P1.7 ALLOW response;
9. Deny path produces exactly one DENY response;
10. turn completes, P3 captures ordered OUTPUT, and P6.1 first final segment EDITs the confirmed status ID while later chunks CREATE in order;
11. no confirmed final segment is duplicated;
12. sequential second turn preserves thread context/binding and receives independent status/delivery;
13. outer group-handler cancellation does not cancel/redeliver owned P3/approval/final delivery;
14. explicit P3.4 interrupt delegates to the exact same P1.6 lifecycle/binding;
15. anomalous turn-terminal-with-live-approval causes runtime shutdown + RESPONSE_UNKNOWN + projected UNKNOWN, never guessed ALLOW/DENY;
16. process restart restores no work-status hint and sends no acknowledgement replay;
17. startup CODEX_COMPLETED recovery uses P6.1 all-CREATE final delivery;
18. startup stranded SENDING performs zero resend and becomes DELIVERY_UNKNOWN;
19. startup recovered old active job cancels leftover PENDING approval with zero old P1.7 response;
20. delivery discovery is oldest-first, bounded, zero-clock/read-only;
21. private callback signal remains wake-only;
22. no raw prompt/reasoning/patch/environment/secrets in status/evidence/logs;
23. no real Telegram/network/Codex process/production DB/service effect.

## Non-goals

P6.3 does not implement:

- Telegram Bot API HTTP;
- polling/webhook/offset/backlog;
- bot-token/config loading;
- systemd/deployment;
- real Codex process acceptance;
- real hard-delete measurement;
- Telegram live acceptance;
- multi-server live acceptance;
- P7+.

After architect acceptance of P6.3, P6 is complete at the fake/application boundary and P7 becomes the next phase.
