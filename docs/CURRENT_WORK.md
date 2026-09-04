# Current work authority

Date: 2026-09-04

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Codex foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`.
- Architect V1 baseline before implementation: `74c2950c0b22b2f0be1b61d50907eda846a7804d`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- P1.5 accepted: `e7851d813944d3326b7fd9317da9e21f216557fa`.
- P1.6 accepted: `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.
- P1.7 accepted/proof HEAD: `bbd7445087dfb59185d49787d562637e282ba5aa`.
- P1.8 accepted after recovered repair: `6d8a07b5b95ef377cf60762f4475128bdf810b22`.
- ADR-0014 defines permissions approval semantics.
- ADR-0015 defines active-turn interrupt ownership/reconciliation.
- ADR-0016 defines thread/delete response authority and partial-failure ambiguity.

## P1.8 accepted interrupt facts
- Installed `turn/interrupt` request is `TurnInterruptParams` with required string `threadId` and `turnId`; response is object `TurnInterruptResponse`. Both schemas omit `additionalProperties:false` and have no ID `minLength`.
- Product does not expose the upstream empty-turn-id startup interrupt path.
- Interrupt accepts only the exact active P1.6 `TurnBinding` and uses the exact runtime/client captured by the original `turn/start`; manager reacquire/rebase is forbidden.
- The existing P1.6 collector is the sole terminal evidence and notification consumer. `wait_turn` and interrupt may await the same collector.
- One interrupt reservation exists per profile/thread key; different profile/runtime keys are independent.
- Exactly one `turn/interrupt` request is sent; there is no automatic retry.
- Schema-valid RPC success plus definitive P1.6 COMPLETED/FAILED terminal evidence is CONFIRMED.
- Ambiguous wire outcome plus definitive exact target terminal evidence is RECONCILED; non-definitive/cancelled/exceptional collector is UNKNOWN.
- Definitive remote rejection with no already-definitive target is REJECTED with safe numeric remote code only; already-definitive target reconciles.
- Pre-dispatch caller cancellation sends zero interrupt RPC; after dispatch repeated cancellation remains attached to the exact RPC and collector.
- Cancelled collector is distinguished from caller cancellation and cannot spin indefinitely.
- Private active runtime/token metadata is excluded from repr diagnostics.
- Capability readiness now has MODEL_LIST, THREAD_START, THREAD_RESUME, TURN_START, TURN_INTERRUPT, AGENT_MESSAGE_EVENTS, TURN_TERMINAL_EVENTS, APPROVAL_SERVER_REQUESTS and APPROVAL_RESPONSE_SCHEMA IMPLEMENTED. THREAD_DELETE remains NOT_IMPLEMENTED.
- Accepted recovered proof suite reported P1.8 28, P1.6 17, P1.7 protocol 28, P1.7 approvals 22, errors 16, capabilities 18, full 222; compile/import passed.
- The established P1.6 pending-task warning remains test-hygiene debt and was not introduced by P1.8.

## P1.9 exact architect authority
P1.9 implements installed Codex 0.144.6 `thread/delete` adapter semantics only.

Exact installed/exact-version facts:
- method: `thread/delete`;
- request schema: `ThreadDeleteParams` object with required string `threadId` only;
- response schema: `ThreadDeleteResponse` object with no declared fields;
- both draft-07 schemas omit `additionalProperties`, so additional properties are allowed;
- exact delete computes a persisted spawn subtree, prepares loaded threads for removal, deletes descendants then root from the thread store, deletes corresponding app-server state DB rows when configured, then creates the response;
- schema-valid response is sent only after the official delete routine succeeds;
- `thread/deleted` notifications are emitted after the response;
- active-thread shutdown submit failure/timeout does not prevent the delete routine from proceeding;
- deletion can fail after earlier destructive steps have already succeeded, so a dispatched error response does not prove absence of side effects.

Binding decisions from ADR-0016:
- public input is a profile-bound durable `ThreadBinding`; value reconstruction from durable state is allowed and expected;
- delete may acquire the current runtime for `binding.profile_id` and must verify `runtime.profile_id` exactly. It does not need the runtime generation that originally created/resumed the persisted thread;
- delete is serialized with P1.5 start/resume through the same per-profile thread-lifecycle reservation;
- P1.9 does NOT auto-interrupt a running turn. Application/P3 state-machine orchestration owns interrupt-before-delete ordering;
- exactly one `thread/delete` RPC is allowed per invocation;
- schema-valid successful response => DELETE_CONFIRMED and is the P1.9 external deletion authority;
- every non-success after dispatch => DELETE_UNKNOWN, including ProtocolRemoteError, protocol/transport/process failure, inner request cancellation, and schema-invalid successful payload. There is no DELETE_REJECTED status after dispatch because partial destructive effects are possible;
- a safe numeric remote code may be retained inside THREAD_DELETE_UNKNOWN for diagnostics, but remote text/data is discarded;
- pre-dispatch public cancellation may propagate with zero RPC; after dispatch repeated cancellation stays attached to the one owned request;
- no retry, no `thread/read` guessing, no second delete, and no `thread/deleted` notification consumer in P1.9;
- DELETE_CONFIRMED/DELETE_UNKNOWN retain the exact ThreadBinding so later durable/application layers keep reconciliation identity;
- P1.9 does not clear durable binding, purge local controller content, or claim measured physical storage erasure. P7 remains the storage-deletion proof gate;
- only THREAD_DELETE may newly become IMPLEMENTED after acceptance.

## Execution authority
Codex must not self-start work from this document.

Only **P1.9 — exact `thread/delete` + ambiguity-safe external deletion authority** is eligible for the next explicit implementation prompt.

P1.9 does not authorize P1.10 acceptance, SQLite/local purge orchestration, Telegram, systemd, production deployment, real production deletion, or storage-erasure claims.