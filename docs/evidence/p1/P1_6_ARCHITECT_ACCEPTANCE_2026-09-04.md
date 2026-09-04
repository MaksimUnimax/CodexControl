# P1.6 architect acceptance — 2026-09-04

Status: ACCEPTED.

Accepted implementation HEAD:

`de36b3ef3657a464b29ff2d17692fce5fc2b2388`

Original P1.6 architect base:

`cd044c737fef1d67981bb3d896124787b554b10b`

Implementation branch:

`impl-p1-6-turn-lifecycle-2026-09-04`

## Review history

The initial candidate `d04112caa911d6ef8edaff5ce8112b911b3b061f` was rejected because the required acceptance matrix was incomplete and review identified lifecycle defects including inner post-dispatch request cancellation hanging and completed collector results being removed too early for a true late waiter.

The first repair `976aa13de2677ee0dbc8c5bce6258c96a0a12feb` repaired inner request cancellation, late waiter retention, recognized-event routing, and remote-content validation, but was not accepted because completed-result retention still had a publication race and required boundary/routing proofs remained incomplete.

The second repair `de36b3ef3657a464b29ff2d17692fce5fc2b2388` was independently reviewed against the original architect base and accepted.

## Independently verified acceptance facts

- Cumulative implementation diff from the architect base contains only P1.6-allowed adapter, test, fixture, manifest/error, and evidence paths; foundation/domain/session and architect-owned contract documents were not changed by Codex.
- Installed authority remains `codex-cli 0.144.6` with app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Exact `turn/start` request/result and notification facts are frozen by version/SHA-bound fixtures.
- Exact typed turn selection is `model` plus `effort`; no opaque reasoning/config key is guessed. ADR-0013 is satisfied.
- Turn start uses one captured runtime and generation-matched P1.4 catalog; no lifecycle reacquire/rebase or automatic retry exists.
- Pre-dispatch cancellation sends zero turn RPC. Post-dispatch repeated caller cancellation preserves ownership until the same public invocation reaches CONFIRMED/REJECTED/UNKNOWN. Inner request cancellation is TURN_START_UNKNOWN and cannot spin indefinitely.
- Remote rejection preserves only safe numeric remote code. Protocol/transport/malformed-success ambiguity is TURN_START_UNKNOWN.
- Exact bounded opaque turn identity is retained; malformed successful turn IDs become UNKNOWN after exactly one side-effect request.
- Only completed agent-message items become canonical user-visible output. Delta text is transient, and non-agent command/file-change/reasoning output is excluded.
- Completed-message arrival order is preserved. Item IDs are bounded and duplicate completed-agent-message IDs fail closed.
- Per-message, message-count, total-content, and notification-count bounds are enforced at exact acceptance boundaries without truncation.
- Recognized malformed delta/completed/terminal events fail closed; well-formed unrelated turn/thread events are ignored.
- Terminal status mapping is exact to installed schema: completed -> COMPLETED; failed/interrupted -> definitive FAILED; invalid/inProgress terminal state -> stream UNKNOWN.
- Collector races notification availability with protocol terminal state and deterministically consumes already-queued matching terminal notifications where safely possible.
- Read-only waiter cancellation does not cancel the collector; later waiter retrieval is supported while the exact result remains retained.
- Active collectors and completed terminal results are separated. Terminal publication is exact-token and lock protected. At most one completed result is retained per profile/thread key; newer confirmed turn supersedes it atomically; stale terminal publication cannot remove or overwrite replacement state.
- Late old-turn events cannot mutate an already returned immutable result or contaminate a newer turn.
- Independent profile runtimes/clients remain isolated.
- Turn lifecycle errors normalize to finite safe categories with no arbitrary payload text and no retry decision fields.
- Capability readiness after P1.6 is exactly: MODEL_LIST, THREAD_START, THREAD_RESUME, TURN_START, AGENT_MESSAGE_EVENTS, TURN_TERMINAL_EVENTS = IMPLEMENTED; THREAD_DELETE, TURN_INTERRUPT, APPROVAL_SERVER_REQUESTS, APPROVAL_RESPONSE_SCHEMA = NOT_IMPLEMENTED.
- Reported direct P1.6 tests: 17 passed; error tests: 14 passed; capability tests: 17 passed; full discovery: 157 passed; compile/import passed.
- No real production `turn/start`, production `CODEX_HOME`, Telegram, SQLite, service mutation, or production deployment occurred.

## Architect decision

P1.6 is complete and may be used as the accepted base for P1.7.

P1.7 is the only next authorized P1 slice. P1.7 must implement the previously deferred bidirectional server-request envelope and exact installed approval request/response port using fake/simulated operator behavior only. Real Telegram approval UI and real production approvals remain forbidden until later phases.
