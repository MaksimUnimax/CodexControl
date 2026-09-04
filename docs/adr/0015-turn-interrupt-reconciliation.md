# ADR-0015 — Turn interrupt uses the active runtime and existing terminal collector

Status: accepted
Date: 2026-09-04

## Context

P1.8 implements installed Codex 0.144.6 `turn/interrupt` only.

The installed/exact-version protocol defines `TurnInterruptParams` as exactly `threadId` plus `turnId` and `TurnInterruptResponse` as an empty response object. Exact Codex 0.144.6 behavior records normal turn interrupts as pending and replies only when the target turn reaches a terminal core event; pending interrupt responses are emitted for both aborted and naturally completed turns. The same terminal event path also emits the normal `turn/completed` notification consumed by accepted P1.6.

The product state machine requires `INTERRUPTING -> IDLE` only after terminal/reconciled state. A lost interrupt response must never cause a blind retry.

## Decision

1. P1.8 accepts only an exact active P1.6 `TurnBinding`. Arbitrary thread/turn strings and the upstream empty-turn-id startup interrupt path are not product APIs.
2. P1.6 retains private active-turn runtime metadata sufficient for P1.8 to use the exact runtime/client captured by `turn/start`. P1.8 does not call the runtime manager again, rebase generations, or move the interrupt to a replacement runtime.
3. Interrupt handling remains inside the P1.6 turn-lifecycle ownership boundary. It reuses the exact existing collector task for the target turn and never creates a second notification consumer.
4. At most one interrupt operation may be in flight per profile/thread key. A second same-key interrupt fails before dispatch as BUSY. Different profile/runtime keys remain independent.
5. Exactly one `turn/interrupt` RPC is sent. No automatic retry is permitted after dispatch.
6. Public cancellation before side-effect dispatch may cancel normally and sends zero interrupt RPC. After dispatch, repeated public cancellation cannot detach or cancel the owned interrupt request; the same public invocation remains attached until a finite interrupt outcome is known.
7. Definitive remote rejection with no already-proven terminal target is `TURN_INTERRUPT_REJECTED` and retains only a safe numeric remote code.
8. A successful interrupt response is not sufficient by itself for product IDLE. The adapter also requires the existing P1.6 collector to reach a definitive target-turn terminal result. This yields `TURN_INTERRUPT_CONFIRMED`.
9. If the interrupt RPC is ambiguous or rejected but the exact existing P1.6 collector proves the target turn terminal, the operation yields `TURN_INTERRUPT_RECONCILED`. No additional read RPC or notification consumer is introduced.
10. If the RPC is ambiguous and the target collector cannot prove a definitive terminal state, the operation is `TURN_INTERRUPT_UNKNOWN`.
11. The adapter never waits indefinitely for a naturally terminal turn after a definitive remote rejection. It may use an already-completed definitive collector result for reconciliation; otherwise it returns REJECTED.
12. Malformed successful interrupt responses are ambiguous. Raw response payloads are discarded and never enter normalized errors/logs.
13. P1.8 does not implement application-level coordination with approval UI/state, Telegram, SQLite, delete, or restart recovery. Those remain later orchestration concerns.

## Consequences

- Interrupt cannot accidentally target a replacement Codex runtime after a process/generation change.
- There is still one notification consumer per active turn.
- Ambiguous interrupt wire outcomes can safely converge to IDLE only from already-owned terminal evidence.
- Startup interruption and thread deletion remain outside P1.8.
