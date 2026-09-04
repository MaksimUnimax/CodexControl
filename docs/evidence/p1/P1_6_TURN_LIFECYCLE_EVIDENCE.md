# P1.6 turn lifecycle implementation evidence

Base: `cd044c737fef1d67981bb3d896124787b554b10b`; branch: `impl-p1-6-turn-lifecycle-2026-09-04`.

Installed authority was read-only verified with `/usr/local/bin/codex --version` (`codex-cli 0.144.6`) and `/usr/local/bin/codex app-server generate-json-schema --out <new temporary directory>`. SHA-256 of `codex_app_server_protocol.schemas.json` was `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`, matching the required authority.

Installed `turn/start` requires `input` and `threadId`; its complete properties are `personality`, `approvalPolicy`, `approvalsReviewer`, `clientUserMessageId`, `serviceTier`, `cwd`, `effort`, `threadId`, `input`, `model`, `summary`, `outputSchema`, and `sandboxPolicy`. P1.6 sends only `threadId`, text input (`[{"type":"text","text":...}]`), `model`, direct typed `effort`, trusted `cwd`, `approvalPolicy:"on-request"`, and `sandboxPolicy:{"type":"workspaceWrite"}`. There is no `config` field. Successful turn identity is `turn.id`.

`item/agentMessage/delta` has `threadId`, `turnId`, `itemId`, and `delta`; deltas are validated transiently and are never canonical output. `item/completed` has `threadId`, `turnId`, and `item`; completed user-visible items require `item.type == "agentMessage"`, `item.id`, and `item.text`. `turn/completed` has `threadId` and `turn`; terminal identity is `threadId` + `turn.id`, with `turn.status` enum `completed`, `interrupted`, `failed`, `inProgress`. `completed` maps COMPLETED; `interrupted` and `failed` map definitive FAILED; `inProgress` fails closed UNKNOWN.

Bounds: turn ID 512, item ID 512, input 65536, message 1000000, messages/turn 256, total message characters 2000000, notifications 16384. Runtime is captured before catalog lookup and profile/generation equality is required before dispatch. The start task is cancellation-owned after exact dispatch; no retry occurs. The exact profile/thread active reservation remains through a single collector, and a shielded read-only waiter cannot cancel it. Collector races notification reads with protocol terminal and reports stream UNKNOWN if terminal occurs first. Completed agent messages are ordered by arrival; item IDs detect duplicates; non-agent and reasoning data are never projected.

Only TURN_START, AGENT_MESSAGE_EVENTS, and TURN_TERMINAL_EVENTS are marked IMPLEMENTED; approval server requests, approval responses, interrupt, and delete remain NOT_IMPLEMENTED. No real business RPC, production CODEX_HOME, service, foundation, or architecture file was used or changed.

## Architect first repair pass

Rejected candidate: `d04112caa911d6ef8edaff5ce8112b911b3b061f`.

The owned inner `turn/start` task now returns `TURN_START_UNKNOWN` if it is itself cancelled after dispatch, while public cancellation before dispatch cancels and joins the inner task and public cancellation after dispatch is deferred until its exact terminal start outcome. Completed collector tasks retain one bounded, memory-only terminal result per profile/thread; confirmation of a newer turn evicts the prior retained result. Active reservation is released at terminal.

Recognized delta, completed-item, and terminal notifications validate their complete routing envelope before mismatch filtering; malformed recognized envelopes fail closed as `TURN_STREAM_UNKNOWN`. The installed schema facts recorded in the fixture are that both completed `item.text` and delta have no `minLength`, so empty strings are accepted subject to the existing content bounds.

Focused coverage exercises pre-dispatch validation and cancellation, captured-runtime/generation checks, exact request and effort selection, start-ID/failure and cancellation matrices, active ownership, completed-message ordering/bounds/duplicates, delta and malformed routing, terminal mappings, protocol terminal, notification bounds, late waiter retention/new-turn eviction, late-event isolation, error normalization, and capability readiness. This is repair evidence only; architect acceptance is not claimed.

## Architect second repair pass

Candidate requiring second repair: `976aa13de2677ee0dbc8c5bce6258c96a0a12feb`.

Active collector tasks and completed terminal results are now separate memory-only registries. Terminal publication holds the adapter lock, verifies the exact active token, removes only that active reservation and exact active collector binding, and stores one immutable `(TurnBinding, TurnTerminalResult)` per profile/thread key. A confirmed replacement turn uses that same lock to evict the prior completed result and register its collector. Stale token publication cannot remove a replacement active token or restore/overwrite its state.

Focused tests prove the 256/257 completed-agent-message boundary and the exact 2,000,000/2,000,001 aggregate-content boundary; the complete recognized delta, item/completed, and terminal routing matrices; exclusion of command, file-change, and reasoning sentinels; exact 16,384/16,385 notification handling; deterministic queued notification plus protocol-terminal handling; a true post-completion late-old-turn sequence; profile-independent clients; and runtime-profile mismatch with one acquire and zero RPC.

The fixture now freezes `TurnStartParams.effort` as optional and nullable, with `$ref` `#/definitions/v2/ReasoningEffort`; that definition is JSON string, has no enum, and `minLength: 1`. Tests also freeze exact maximum input acceptance/preservation, remote numeric rejection code retention, and TurnLifecycleError redaction/no-retry fields. Direct focused, error, capability, regression, full, compile, import, diff, and secret-scan results are recorded by the repair executor. This is factual repair evidence only; architect acceptance is not claimed.
