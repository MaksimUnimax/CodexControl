# ADR-0016 — Thread delete response is authority; dispatched non-success is UNKNOWN

Status: accepted
Date: 2026-09-04

## Context

P1.9 implements installed Codex 0.144.6 `thread/delete` only.

Exact installed/exact-version facts:

- `ThreadDeleteParams` is an object with required string `threadId` and no schema `minLength`.
- `ThreadDeleteResponse` is an object with no declared fields.
- Both draft-07 schemas omit `additionalProperties`, so additional properties are allowed.
- Exact Codex 0.144.6 deletion computes the stored spawn subtree, prepares loaded threads for removal, deletes descendants then the root from the thread store, strictly deletes corresponding app-server state DB rows when present, then constructs `ThreadDeleteResponse {}`.
- The response is sent only after that delete routine succeeds. `thread/deleted` notifications are emitted after the response.
- Deletion is not transactionally all-or-nothing across every step. A later child/root store deletion or state DB operation can fail after earlier destructive steps already succeeded. Active loaded threads are also removed/shutdown during preparation, and shutdown submit failure/timeout does not prevent the delete routine from proceeding.

Therefore a dispatched error response does not prove that no deletion side effect happened.

## Decision

1. P1.9 accepts a profile-bound durable `ThreadBinding` and sends exactly one `thread/delete` request using only its `threadId`.
2. Delete may acquire the current runtime for the binding's profile. Unlike active-turn interrupt, deletion targets persisted profile-owned thread identity rather than the runtime generation that originally created/resumed it. The acquired runtime must report the exact profile ID.
3. P1.9 serializes delete with existing P1.5 thread start/resume operations through the same per-profile lifecycle reservation. It does not queue a second operation.
4. P1.9 does not autonomously interrupt a running turn. Application-level state-machine orchestration remains responsible for `TURN_RUNNING -> INTERRUPTING -> DELETE_PENDING/DELETING` before invoking the delete port.
5. A schema-valid successful `ThreadDeleteResponse` is `DELETE_CONFIRMED`. It is the P1.9 external deletion authority because exact Codex sends it only after the official delete routine succeeds.
6. Any non-success outcome after request dispatch is `DELETE_UNKNOWN`, including `ProtocolRemoteError`, protocol/transport/process failure, inner request cancellation, or schema-invalid successful payload. No `DELETE_REJECTED` product status is exposed after dispatch because exact-version deletion may already have partially mutated storage/runtime state before returning an error.
7. A safe numeric remote error code may be retained diagnostically inside `THREAD_DELETE_UNKNOWN`; arbitrary remote text/data is discarded.
8. Public cancellation before side-effect dispatch may propagate and sends zero delete RPC. After dispatch, repeated caller cancellation cannot detach/cancel the one owned delete request; the same invocation returns CONFIRMED or UNKNOWN.
9. P1.9 does not retry `thread/delete`, does not call `thread/read` or any other read to guess reconciliation, and does not send a second delete after ambiguity.
10. P1.9 does not consume `thread/deleted` from the shared notification queue. Exact-version notification order is response first, notification second; adding a competing generic notification consumer would violate existing P1.6 ownership. A lost/error response therefore remains UNKNOWN in P1.9.
11. `ThreadOperationResult` retains the exact `ThreadBinding` for DELETE_CONFIRMED and DELETE_UNKNOWN so later application/durable-state layers can preserve reconciliation identity. P1.9 itself does not clear durable bindings, purge local controller data, or retain an unbounded tombstone registry.
12. Official API success does not claim that every physical Codex log/history artifact has been proven erased. P7 remains the required disposable-thread storage measurement and architecture gate before production hard-delete claims.

## Consequences

- Successful official delete can safely authorize later local purge orchestration.
- Any dispatched error/lost response blocks blind continuation as DELETE_UNKNOWN, even if the remote error appears deterministic.
- Partial destructive side effects cannot be mislabeled as a harmless rejection.
- The adapter remains single-request and notification-consumer safe.
- Real storage erasure guarantees remain deferred to P7 measurement rather than inferred from API shape alone.
