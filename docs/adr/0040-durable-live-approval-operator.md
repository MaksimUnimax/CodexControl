# ADR-0040 — P6.2 durable live approval operator and owned P1.7 response

Status: Accepted
Date: 2026-09-08

## Context

Accepted P1.7 owns exact live Codex app-server approval server-request identity and the one-attempt wire response. Accepted P2.4b owns durable approval records and atomic Telegram callback decisions. Accepted P4.3 projects one PENDING approval into a private Allow/Deny panel and atomically changes the durable approval state, but deliberately sends no P1.7 response.

P6.2 connects these boundaries without adding live Telegram transport and without reconstructing P1.7 wire identities after restart.

P6.2 is not the full local runtime. P6.3 later owns dequeue/turn concurrency, acknowledgement/progress, startup recovery composition and final fake P6 acceptance.

## Lower authority

P1.7 remains sole wire authority:

- only the exact live `InboundServerRequest` object owned by the exact `CodexProtocolClient` can be answered;
- `CodexApprovalBridge` owns normalization, method-specific ALLOW/DENY mapping and exactly one `respond_server_request` attempt;
- an ambiguous response is terminal `RESPONSE_UNKNOWN` and is never retried;
- process restart destroys the old request object/client ownership; durable metadata never recreates it.

P2.4b remains sole durable operator-decision authority:

- `ApprovalRecord.state` is `PENDING|APPROVED|DENIED|EXPIRED|CANCELLED`;
- `create_pending` requires the exact current `CODEX_RUNNING` job/version/profile and TURN_RUNNING dialogue;
- P4.3 approval callbacks atomically consume the opaque callback and move PENDING to APPROVED/DENIED or terminalize expiry/staleness before any wire effect.

## Scope

P6.2 owns only:

1. one narrow additive per-approval terminalization method for live expiry/lost-request cleanup;
2. a content-free process-local decision wake signal;
3. a durable `AsyncApprovalOperator` implementation bound to one exact running job/turn;
4. an owned wrapper around P1.7 `CodexApprovalBridge.handle_request` for an already-owned server request;
5. fake/application end-to-end proof through real P4.3 durable decision authority and real P1.7 wire mapping.

No schema/DDL, Telegram HTTP, polling, bot token, response delivery, startup job scan, P3 turn rewrite or full process loop is included.

## Constants

Exactly:

- `P62_APPROVAL_TTL_MS = 900_000`
- `P62_APPROVAL_PAYLOAD_RETENTION_MS = 900_000`

The approval deadline and transient APPROVAL payload deadline are the same. P4.3 already caps callback expiry to the earlier of its own 900000 ms TTL and the approval expiry.

## Additive ApprovalRepository authority

Add exactly one public method:

`terminalize_pending(approval_id, *, target_state) -> ApprovalRecord`

`target_state` accepts only exact existing `ApprovalState.EXPIRED` or `ApprovalState.CANCELLED`.

Semantics:

- validate the exact bounded approval ID and exact enum target before SQL;
- missing approval -> `NOT_FOUND`;
- materialize the current canonical approval/job/dialogue relation;
- if current approval is already non-PENDING, return that exact current record unchanged with zero clock and zero mutation;
- if current is PENDING, read one validated repository clock;
- target `EXPIRED` is allowed only when effective current time is at or after `expires_at_ms`; otherwise `STATE_CONFLICT`, no mutation;
- target `CANCELLED` may terminalize a PENDING approval even while its job remains `CODEX_RUNNING`; this is the exact live-request-loss authority P2.4b did not previously need;
- update is one PENDING-state CAS in one storage transaction and returns the exact terminal record;
- it does not consume callback tokens, change the job/dialogue, or perform any external effect.

The existing `cancel_pending_for_job(job_id)` remains unchanged and remains the post-turn bulk cleanup authority. `terminalize_pending` is additive, per-approval and live-request scoped.

A later click on a CANCELLED/EXPIRED approval is handled by accepted P2.4b/P4.3 stale/consumed semantics and can never revive the approval.

## ApprovalTurnBinding

Add frozen repr-redacted `ApprovalTurnBinding` with exact fields:

`job_id, profile_id, thread_id, codex_turn_id`

Every field is an exact non-empty NUL-free string with accepted lower-layer bounds: job/profile <=128, thread/turn <=512. Generic repr exposes no identifiers.

The binding is application composition metadata only. Durable job state remains authority.

## ApprovalDecisionSignal

Add `ApprovalDecisionSignal` as a process-local, content-free wake mechanism.

Public method exactly:

`notify() -> None`

`notify()` grants no decision, stores no decision and performs no durable mutation. It only wakes currently registered P6.2 waiters. Every woken waiter must re-read its own exact durable `ApprovalRecord` before returning a decision.

Waiter registration is private to the P6.2 module. The operator registers before publishing its PENDING approval, so a fast P4.3 decision cannot be lost between durable creation and waiter installation.

Calling `notify()` with no waiter or before any durable decision is a harmless no-op/wake; it can never cause ALLOW.

P6.3 later owns invoking this signal after private callback handling. P6.2 does not modify accepted P4.3 production solely to add a notification hook.

## DurableApprovalOperator

Add an application component implementing accepted P1.7 `AsyncApprovalOperator`:

`DurableApprovalOperator(storage, *, binding, signal, now_ms=None, id_factory=None, sleep=None)`

Public async method exactly:

`decide(request) -> ApprovalDecision`

The optional `sleep` is an async test seam; production default is `asyncio.sleep`.

The operator is bound to exactly one `ApprovalTurnBinding` and is safe for the serialized P1.7 bridge use. It has no Telegram/network dependency.

### Request/binding validation

Before exposing a durable approval, require exact `ApprovalRequest` and re-read the exact bound job.

Require:

- request profile equals binding profile;
- request thread/conversation identity equals binding thread;
- bound job exists and exact job ID/profile/thread/Codex turn match the binding;
- job is exact `CODEX_RUNNING` and the live dialogue is still TURN_RUNNING by accepted `create_pending` preconditions;
- for modern COMMAND_EXECUTION/FILE_CHANGE/PERMISSIONS requests, request turn ID equals binding Codex turn ID;
- for legacy APPLY_PATCH/EXEC_COMMAND, request turn ID is exactly None and the normalized conversation/thread identity still matches;
- request kind/wire ID/context are the already normalized bounded P1.7 values.

A mismatch or invalid pre-publication request fails closed to `ApprovalDecision.DENY` with no PENDING approval and no ALLOW path.

### Operator-safe transient details

P1.7 already bounds and sanitizes the projected `context_lines` and never projects patch contents/raw protocol events.

If context lines are non-empty, P6.2 joins them with exact `"\n"`, strict-UTF8 encodes them, and creates one transient `APPROVAL` payload owned by the exact job/dialogue with the common approval expiry. No additional command/reasoning/protocol content is added.

If context lines are empty, no APPROVAL payload is created. Accepted P4.3 then remains deny-only because it cannot safely present extra approval details.

IDs are generated exactly once per requested object through the injected/default factory. No collision retry. A payload created before a later approval-create failure may remain only as bounded transient content; no wire response has occurred.

### Durable publication order

For a valid request:

1. generate bounded approval/payload IDs as required;
2. privately register the decision waiter;
3. read one validated application clock and compute exact expiry `now + 900000`;
4. create optional APPROVAL payload;
5. call accepted `ApprovalRepository.create_pending` with exact profile, wire request ID, kind, bound job ID, exact current job version and expiry;
6. only after the PENDING record commits may the operator wait for a Telegram-side decision.

This ensures no operator decision can be acted on without durable state.

### Durable decision authority

After PENDING publication, only the exact durable approval state determines the returned P1.7 decision:

- APPROVED -> `ALLOW`;
- DENIED -> `DENY`;
- EXPIRED -> `DENY`;
- CANCELLED -> `DENY`;
- PENDING -> continue waiting.

The process-local signal is never decision authority.

At the exact expiry deadline the operator calls `terminalize_pending(..., EXPIRED)` and maps the returned current state. A callback racing expiry and this terminalizer has one SQLite winner; if APPROVED/DENIED already won, terminalize returns that exact terminal record unchanged and the operator follows it.

No periodic DB polling or background worker is introduced. The operator waits on its content-free signal and the one expiry timer. If a storage/repository read fails after a PENDING approval exists, the operator MUST NOT raise/return a fabricated DENY while that approval remains actionable PENDING. It stays fail-closed waiting for another signal/expiry opportunity or P1.7 protocol terminal. A failed expiry terminalization likewise does not fabricate a decision or spin in a busy retry loop.

Before PENDING publication, a deterministic validation/precondition failure may safely return DENY because no actionable durable approval has been published.

### Cancellation / lost wire ownership

The normal P6.2 owned response path shields public caller cancellation after an exact server request has already been transferred to P6.2, so ordinary caller cancellation does not enter P1.7's pre-send fail-closed DENY path after the operator may have durably approved.

If P1.7 itself cancels `decide()` because the exact protocol/client became terminal, the operator makes one best-effort owned `terminalize_pending(..., CANCELLED)` attempt when a PENDING approval had been published, unregisters its waiter, and then propagates cancellation. If an APPROVED/DENIED/EXPIRED terminal state already won, it is never overwritten. Protocol terminal owns the fact that no new response can safely be sent.

No response is sent by the operator itself.

## OwnedApprovalResponseService

Add:

`OwnedApprovalResponseService(profile_id, client, operator)`

where client is the exact `CodexProtocolClient` and operator is the exact bound `DurableApprovalOperator` for the same profile.

Public async method exactly:

`handle_owned(inbound) -> ApprovalHandlingResult`

This service does not dequeue server requests. P6.3 later owns dequeue/turn concurrency.

`handle_owned` requires:

- exact `InboundServerRequest`;
- exact client still owns that exact object by identity before starting;
- profile consistency with the operator binding.

It constructs/reuses accepted `CodexApprovalBridge` and invokes exactly one `handle_request(inbound)` in an owned task. Once this method is called with already-transferred request ownership, public caller cancellation is deferred with shield/ownership semantics until that exact bridge task reaches its finite result. The outer caller must not cancel the bridge and cause a replacement DENY.

No automatic retry.

Canonical returned P1.7 `ApprovalHandlingResult` must retain exact profile, request ID, kind and finite status. `RESPONSE_UNKNOWN` remains terminal and is never re-sent.

A reconstructed/stale request object is rejected before the bridge and never causes a wire response.

## Restart boundary

P6.2 persists approval decision metadata, not P1.7 wire authority.

After process/client restart:

- the old exact `InboundServerRequest` object is gone;
- a new `CodexProtocolClient` does not own any reconstructed value with the same wire ID;
- P6.2 MUST NOT recreate an old server request or send a response from the durable ApprovalRecord;
- P3/P6.3 startup recovery may terminalize the old job and then use existing bulk cancellation/retention authority for leftover pending approvals;
- an old terminal APPROVED/DENIED record remains an operator-decision fact only, never proof that a response was delivered.

Restart therefore fails closed with zero old-response replay.

## P4.3 composition

P6.2 does not alter accepted P4.3 callback semantics.

Fake integration proves the real flow:

1. exact live P1.7 server request is owned;
2. DurableApprovalOperator publishes PENDING state/details;
3. real P4.3 projects that approval and creates exact opaque Allow/Deny callbacks;
4. real P4.3 callback atomically commits APPROVED or DENIED;
5. the composition invokes `ApprovalDecisionSignal.notify()`;
6. operator re-reads durable state and returns ALLOW/DENY;
7. accepted P1.7 bridge sends exactly one method-specific wire response.

The signal is intentionally outside P4.3; P6.3 later owns the final private-handler composition that pulses it after callback processing.

## Mandatory race/recovery proofs

P6.2 must prove at least:

- ALLOW through real P4.3 -> exact P1.7 ALLOW response once;
- DENY through real P4.3 -> exact P1.7 DENY response once;
- signal notification before a durable decision cannot grant ALLOW;
- duplicate/sibling P4 callbacks cannot create a second wire response;
- expiry -> durable EXPIRED -> DENY once;
- callback-vs-expiry race follows the single durable terminal winner;
- public cancellation of `handle_owned` while waiting does not cancel the bridge/operator or substitute DENY; a later Allow still produces ALLOW once;
- protocol terminal while waiting yields P1.7 RESPONSE_UNKNOWN/no response and best-effort CANCELLED cleanup of still-PENDING approval;
- process restart/new client cannot respond to reconstructed old request even when approval metadata persists;
- no raw patch content, reasoning, environment, credentials, CODEX_HOME or raw protocol payload is stored/projected/logged;
- no real Telegram/network/Codex effect.

## Non-goals

P6.2 does not implement:

- server-request dequeue loop or turn/approval concurrent pump;
- P3 turn lifecycle changes;
- acknowledgement/progress/final response delivery;
- startup delivery-job scanning;
- live Telegram HTTP/polling/webhook;
- production token/config/systemd;
- live backlog/offset behavior;
- real Codex execution;
- P6.3/P7+.

P6.3 owns final local orchestration using this accepted primitive.
