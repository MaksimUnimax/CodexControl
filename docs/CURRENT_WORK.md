# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted implementation: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted implementation after two repair reviews: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted implementation after three repair reviews: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted implementation after one repair review: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- P1.5 accepted implementation after two repair reviews: `e7851d813944d3326b7fd9317da9e21f216557fa`.
- P1.6 accepted implementation after two repair reviews: `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.

## P1.6 accepted turn-lifecycle facts
- Installed `turn/start` requires `input` and `threadId`; exact successful turn identity is `turn.id`.
- Plain text input is sent as `[{"type":"text","text":...}]`; product input is bounded to 65,536 characters, NUL-free, and preserved exactly.
- Per-turn exact model selection uses P1.4 `wire_model` through typed `model`; reasoning effort uses exact typed `effort`. ADR-0013 is satisfied without opaque config guessing.
- Installed `TurnStartParams.effort` is optional/nullable and references `#/definitions/v2/ReasoningEffort`; the referenced JSON type is string, no enum is declared, and `minLength` is 1. Accepted P1.4 always supplies a validated non-empty advertised default when caller effort is absent.
- `turn/start` also uses trusted `cwd`, approval policy `on-request`, and `sandboxPolicy: {"type":"workspaceWrite"}`; no arbitrary config/base/developer/provider fields are injected.
- P1.6 captures one runtime before catalog lookup and requires catalog profile/generation to match that exact runtime; there is no lifecycle-level reacquire/rebase or blind retry.
- Pre-dispatch cancellation sends no turn RPC. After dispatch, repeated caller cancellation cannot detach/cancel the exact side-effect request; the same invocation resolves to CONFIRMED, REJECTED, or UNKNOWN. Inner request cancellation after dispatch is TURN_START_UNKNOWN.
- Durable/external turn identity is exact `profile_id + thread_id + turn_id`; turn IDs are opaque, case/whitespace preserving, NUL-free, and bounded to 512 characters.
- A single collector owns the exact active turn notification stream. Canonical user-visible output comes only from completed `item/completed` items whose `item.type == agentMessage`; deltas are transient and never canonical output.
- Completed agent-message item IDs are exact/bounded and duplicates fail closed. Agent text allows empty strings because the installed schema has no minLength; one message is bounded to 1,000,000 characters, at most 256 messages and 2,000,000 total completed user-visible characters are accepted per turn.
- Non-agent command/file-change/reasoning/internal items are never projected as user-visible answer content.
- Recognized malformed delta/completed/terminal envelopes for the active stream fail closed as TURN_STREAM_UNKNOWN; well-formed other-thread/other-turn events are ignored.
- `turn/completed` exact status mapping: `completed` -> COMPLETED; `failed` and `interrupted` -> definitive FAILED; `inProgress` on terminal notification or invalid status -> TURN_STREAM_UNKNOWN.
- Collector observes protocol terminal state and cannot hang waiting only on notifications. Queued matching terminal notifications are processed deterministically before protocol-terminal UNKNOWN where safely available.
- Active-turn notification consumption is bounded to 16,384 notifications.
- Active collector state and completed terminal results are separate. Terminal publication is exact-token/lock protected; active state clears atomically and at most one immutable completed result is retained per profile/thread key. A newer CONFIRMED turn evicts the prior completed result; stale publication cannot overwrite replacement state.
- A cancelled read-only `wait_turn` waiter does not cancel the collector; a later waiter may retrieve the retained exact terminal result while it remains current for that key.
- `MODEL_LIST`, `THREAD_START`, `THREAD_RESUME`, `TURN_START`, `AGENT_MESSAGE_EVENTS`, and `TURN_TERMINAL_EVENTS` are locally `IMPLEMENTED`; `THREAD_DELETE`, `TURN_INTERRUPT`, `APPROVAL_SERVER_REQUESTS`, and `APPROVAL_RESPONSE_SCHEMA` remain `NOT_IMPLEMENTED`.

## Execution authority
Codex must not self-start work from this document.

Only **P1.7 — bidirectional server-request envelope + approval request/response port using a fake operator** is eligible for the next explicit implementation prompt.

P1.7 owns the previously deferred P1.1 inbound `id + method + params` server-request distinction, exact installed approval request parsing, exact response-envelope emission, one-time approval ownership, and fake-operator acceptance tests. It does not authorize real Telegram approval UI, real production approvals, turn interrupt, thread delete, SQLite, systemd, or production deployment.

P1.7 must re-verify the exact installed Codex 0.144.6 schema before implementation. If exact approval request/response shapes or enum values cannot be determined from the installed schema, Codex must stop for architect decision rather than guess.
