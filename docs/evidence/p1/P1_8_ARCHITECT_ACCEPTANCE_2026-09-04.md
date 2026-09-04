# P1.8 architect acceptance — 2026-09-04

Status: ACCEPTED.

Accepted implementation HEAD:

`6d8a07b5b95ef377cf60762f4475128bdf810b22`

Original P1.8 architect base:

`ffab0ed71112f7c51fc4453eabb3a3fe17bb8452`

Implementation branch:

`impl-p1-8-turn-interrupt-2026-09-04`

ADR authority: `docs/adr/0015-turn-interrupt-reconciliation.md`.

## Review history

Initial candidate `b99f2476e446bb487a048a33c9912f5210f95e25` was rejected because a cancelled existing P1.6 collector could spin forever in interrupt reconciliation and private active-runtime metadata was not redacted from dataclass repr. Its focused acceptance matrix was also incomplete.

The repair run was interrupted by executor model usage limits before commit/push. Remote branch remained on `b99f247...`; the local dirty worktree was recovered without resetting. Recovered repair `6d8a07b5b95ef377cf60762f4475128bdf810b22` was independently reviewed and accepted.

## Independently verified acceptance facts

- Cumulative P1.8 diff is limited to allowed Codex adapter, tests, fixture, manifest/error and evidence paths.
- Installed authority remains `codex-cli 0.144.6` and schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Exact installed `turn/interrupt` request is object `TurnInterruptParams` with required string `threadId` and `turnId`; neither has schema `minLength`. Exact `TurnInterruptResponse` is an object with no declared fields. Both schemas omit `additionalProperties`, therefore additional properties are allowed under draft-07 semantics.
- CodexControl does not expose the upstream empty-turn-id startup-interrupt path.
- Interrupt accepts only the exact active external `TurnBinding`; reconstructed, completed, stale and foreign bindings fail before dispatch.
- Exact runtime/client captured by `turn/start` is retained privately and used for interrupt; interrupt never reacquires or rebases runtime generation.
- Private active runtime/token fields are excluded from repr/compare diagnostics.
- At most one interrupt operation is in flight per profile/thread key; different profile/runtime keys remain independent.
- Exactly one `turn/interrupt` RPC is sent per invocation with only `threadId` and `turnId`; no automatic retry exists.
- Existing P1.6 collector is the only terminal evidence and notification consumer. `wait_turn` and interrupt may await the same collector without duplicate consumption.
- Schema-valid interrupt response plus definitive P1.6 COMPLETED/FAILED terminal result is CONFIRMED.
- Ambiguous wire outcome plus definitive target terminal result is RECONCILED; ambiguous outcome with non-definitive/cancelled/exceptional collector is UNKNOWN.
- Definitive remote rejection with no already-definitive collector is REJECTED and retains only the safe numeric remote code; already-definitive COMPLETED/FAILED reconciles.
- Pre-dispatch public cancellation sends zero interrupt RPC and releases the guard. After dispatch, repeated public cancellation does not detach/cancel the one owned request or shared collector.
- Cancelled collector is distinguished from caller cancellation and cannot spin indefinitely.
- RPC-first and terminal-first orderings retain ownership until both required pieces are resolved.
- Interrupt guard cleanup is exact-token safe; stale cleanup cannot remove a replacement reservation or newer turn ownership.
- Finite interrupt errors normalize exactly and contain no retry-decision fields or arbitrary source text.
- Capability readiness after P1.8 is: MODEL_LIST, THREAD_START, THREAD_RESUME, TURN_START, TURN_INTERRUPT, AGENT_MESSAGE_EVENTS, TURN_TERMINAL_EVENTS, APPROVAL_SERVER_REQUESTS and APPROVAL_RESPONSE_SCHEMA = IMPLEMENTED; THREAD_DELETE = NOT_IMPLEMENTED.
- Recovered focused P1.8 suite reports 28 tests; P1.6 17; P1.7 protocol 28; P1.7 approvals 22; errors 16; capabilities 18; full discovery 222; compile/import passed.
- The previously observed P1.6 pending-task warning remained unchanged and was not introduced by P1.8.
- No real interrupt, production CODEX_HOME, service mutation, Telegram, SQLite or production deployment occurred.

## Architect decision

P1.8 is complete. The accepted implementation may be used as the base for P1.9. P1.9 owns exact installed `thread/delete` adapter semantics and ambiguity handling only; durable application/database hard-delete orchestration remains later work.