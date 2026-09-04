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
- P1.7 accepted implementation/proof HEAD after iterative repair review: `bbd7445087dfb59185d49787d562637e282ba5aa`.
- ADR-0014 defines exact permissions approval semantics.
- ADR-0015 defines exact P1.8 interrupt ownership/reconciliation semantics.

## P1.7 accepted approval/protocol facts
- P1.1 bidirectional framing is now extended safely: client responses, server requests and notifications are mutually exclusive; mixed envelopes fail closed.
- Exact accepted approval server-request methods are `item/commandExecution/requestApproval`, `item/fileChange/requestApproval`, `item/permissions/requestApproval`, `applyPatchApproval`, and `execCommandApproval`.
- Server-request IDs are exact directional identities: signed-64 integers or non-empty NUL-free strings <=256; client/server request-ID namespaces are independent even when values are equal.
- At most 64 server requests may remain pending. Duplicate pending IDs and request 65 fault safely.
- `InboundServerRequest` is immutable/redacted and each response requires the exact live request instance. A later new request may reuse a completed wire ID with a new local sequence; stale/reconstructed instances cannot respond.
- Server response wire shape is exact `{id, result}` with no `jsonrpc`, `method`, or `params`.
- Response send is one-attempt. Transport exception/cancellation or protocol terminal during send is response UNKNOWN; there is no blind retry or replacement response.
- `CodexApprovalBridge` is bound to one exact profile/client and serializes approvals for that runtime; independent bridge/runtime pairs remain independent.
- Cancellation before request ownership cleans helper tasks. After ownership, public cancellation cannot abandon the request: before response-send it fails closed to DENY; after response-send it remains attached to the one owned response task.
- Operator context is finite/allowlisted and bounded to 32 lines, 2,048 chars/line, 8,192 total. Raw server params, patch contents/diffs, command output, environment/auth material and hidden reasoning are not generic log/repr payloads.
- Product decision model is `ALLOW | DENY`. Command/file-change use `accept`/`decline`; legacy apply-patch/exec-command use `approved`/`denied`; session/persistent alternatives are never selected.
- ADR-0014 permissions DENY is `{"permissions":{},"scope":"turn"}`. ALLOW is only a validated reconstructed request-derived permission grant with turn scope; no privilege broadening/session grant.
- `MODEL_LIST`, `THREAD_START`, `THREAD_RESUME`, `TURN_START`, `AGENT_MESSAGE_EVENTS`, `TURN_TERMINAL_EVENTS`, `APPROVAL_SERVER_REQUESTS`, and `APPROVAL_RESPONSE_SCHEMA` are locally IMPLEMENTED. `TURN_INTERRUPT` and `THREAD_DELETE` remain NOT_IMPLEMENTED.
- Final P1.7 proof suites reported protocol 28, approvals 22, errors 15, capabilities 17, full 192; compile/import and fresh-process approval normalization passed.
- A pre-existing pending-task warning was observed from an accepted P1.6 test path during the P1.7 full suite. P1.7 did not modify that code/test path, so it is non-blocking test-hygiene debt rather than a P1.7 regression.

## P1.8 exact architect authority
P1.8 implements installed Codex 0.144.6 `turn/interrupt` only.

Exact installed/exact-version facts already established for planning:
- method: `turn/interrupt`;
- request params: exact `threadId` and `turnId` only;
- response type: empty `TurnInterruptResponse` object;
- normal turn interrupts are recorded as pending and the app-server replies when the target turn reaches a terminal core event; pending interrupt responses are released on both aborted and naturally completed turns;
- the same terminal path emits normal `turn/completed` evidence consumed by accepted P1.6.

Binding design from ADR-0015:
- public interrupt input is only an exact active P1.6 `TurnBinding`; arbitrary IDs and empty-turn-id startup interrupt are forbidden product paths;
- P1.6 privately retains exact active runtime/client metadata captured at `turn/start` so P1.8 can use that same runtime. P1.8 must not call runtime-manager acquire/rebase for the interrupt;
- interrupt lives inside the P1.6 turn-lifecycle ownership boundary and reuses the existing collector task. It must never consume notifications independently;
- at most one interrupt may be in flight per profile/thread key; same-key duplicate is BUSY before dispatch, different runtime keys are independent;
- exactly one interrupt RPC; no automatic retry;
- pre-dispatch public cancellation may propagate with zero RPC; after dispatch repeated public cancellation remains attached to the one exact interrupt request;
- definitive remote rejection with no already-proven terminal target is `TURN_INTERRUPT_REJECTED` and retains only safe numeric remote code;
- successful RPC plus definitive target collector terminal is `TURN_INTERRUPT_CONFIRMED`;
- ambiguous/rejected RPC plus already/provably terminal exact target may resolve as `TURN_INTERRUPT_RECONCILED` using only the existing collector evidence;
- ambiguous RPC plus non-definitive/UNKNOWN target state is `TURN_INTERRUPT_UNKNOWN`;
- do not wait indefinitely for natural completion after a definitive remote rejection; only an already-completed definitive collector may override rejection into reconciliation;
- malformed successful interrupt response is ambiguous and raw response data is discarded;
- capability readiness after accepted P1.8 may change only `TURN_INTERRUPT` to IMPLEMENTED; `THREAD_DELETE` remains NOT_IMPLEMENTED.

## Execution authority
Codex must not self-start work from this document.

Only **P1.8 — exact active-turn interrupt + terminal reconciliation** is eligible for the next explicit implementation prompt.

P1.8 does not authorize thread deletion, Telegram, SQLite, systemd, production deployment, real production interruption, or application-level approval-state orchestration.
