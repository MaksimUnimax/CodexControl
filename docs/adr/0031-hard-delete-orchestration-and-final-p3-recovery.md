# ADR-0031 — Hard-delete orchestration and final P3 startup recovery

Status: accepted
Date: 2026-09-07

## Context

P3.4 is architect-accepted at `6460a449f861b7b86ab664e5ff877c108715082d`; its acceptance record is `docs/evidence/p3/P3_4_ARCHITECT_ACCEPTANCE_2026-09-07.md`.

P1.9 already owns the only accepted external Codex deletion effect: exact profile-bound `thread/delete`. A schema-valid object response is the sole `DELETE_CONFIRMED` authority. Every dispatched non-success is `DELETE_UNKNOWN`; there is no delete retry, `thread/read` inference, second delete, or notification-based guessing.

P2.5 already owns the durable local deletion state machine and confirmed local finalization: `IDLE -> DELETE_PENDING -> DELETING`, deterministic `ERROR`, ambiguous `DELETE_UNKNOWN`, and exact confirmed purge+tombstone. It deliberately performs no external delete effect.

P3 still lacks the application orchestration joining those two authorities. P3 also still has final startup gaps: a crash may leave a pre-effect admitted job (`RECEIVED` or `CLAIMED`), an effect-possible turn (`CODEX_STARTING` or `CODEX_RUNNING`), or an in-progress delete (`DELETING`). V1 reliability requires fail-closed reconciliation rather than delayed execution or blind replay.

P3.5 closes the application layer. It does not prove physical erasure from every Codex internal store; that empirical gate remains P7.

## Scope

P3.5 owns:

1. Telegram-agnostic hard-delete application orchestration over accepted P1.9 + P2.5;
2. composition with accepted P3.4 when the operator requests delete during `TURN_RUNNING`;
3. safe explicit continuation from durable `DELETE_PENDING` only;
4. one external `thread/delete` maximum after durable `DELETING` authority;
5. exact confirmed local purge+tombstone finalization;
6. fail-closed `DELETE_UNKNOWN` / deterministic local failure mapping;
7. final no-P1 startup recovery for pre-effect and effect-possible turn states plus pre-existing `DELETING`;
8. final fake/application-level P3 acceptance and regression proof.

P3.5 does not implement Telegram UI, delivery execution, real Codex acceptance, physical Codex storage-erasure proof, production state, deployment, or P4+.

## Public hard-delete surface

Add `DialogueDeleteService` with exact public callable surface:

- `delete(request)`.

Add frozen:

`DialogueDeleteRequest(dialogue_id, expected_dialogue_version)`.

Caller input contains no profile or thread ID. Profile/thread are durable internal authority.

Add `DialogueDeleteStatus` exactly:

- `DELETED`;
- `FAILED`;
- `UNKNOWN`;
- `BLOCKED`;
- `CONFLICT`.

Add `DialogueDeleteReason` exactly:

- `NO_DIALOGUE`;
- `DIALOGUE_NOT_READY`;
- `DELETE_NOT_READY`;
- `INTERRUPT_IN_PROGRESS`;
- `INTERRUPT_UNRESOLVED`;
- `DELETE_IN_PROGRESS`;
- `STALE_REQUEST`.

Add frozen:

`DialogueDeleteResult(status, dialogue, tombstone, reason)`

where `dialogue` is `DialogueRecord | None` and `tombstone` is `DeletionTombstoneRecord | None`.

Add finite payload-free `DialogueDeleteError` categories exactly:

- `INVALID_ARGUMENT`;
- `STORAGE`;
- `INVARIANT`.

Generic request/result/error repr must not expose raw thread identity, CODEX_HOME, prompt/output content, DB path, credentials or raw adapter/repository error bodies.

## Dependency ports

The delete application consumes:

- accepted P3.4 interrupt application authority through an injected port equivalent to `interrupt(DialogueInterruptRequest) -> DialogueInterruptResult`;
- accepted P1.9 delete authority through an injected port equivalent to `delete(*, binding: ThreadBinding) -> ThreadOperationResult`.

P3.5 must not duplicate P1.8 or P1.9 wire/protocol logic.

A `ThreadBinding` for delete may be reconstructed from the exact durable deletion row because P1.9 `ThreadBinding` is durable profile/thread identity. This is different from P1.8 `TurnBinding`, whose interrupt authority requires exact in-memory object identity.

## Delete preflight and idempotent replay

After static validation:

1. read the exact tombstone and live dialogue;
2. tombstone + same live dialogue is corruption -> `INVARIANT`;
3. tombstone + no live dialogue -> `DELETED`, exact tombstone, zero P1/clock/mutation;
4. no live dialogue/tombstone -> `BLOCKED / NO_DIALOGUE`;
5. live dialogue ID mismatch -> `CONFLICT / STALE_REQUEST`;
6. live dialogue version mismatch -> `CONFLICT / STALE_REQUEST`;
7. server mismatch/corrupt durable ownership -> `INVARIANT`.

A confirmed-delete replay is therefore idempotent while its tombstone is retained. After tombstone retention expires, an old request with no live dialogue is only `NO_DIALOGUE`; no deleted history is recreated.

## State handling before delete

### IDLE

A matching `IDLE` request starts the durable P2.5 delete sequence.

`claim_delete_intent` remains the exact readiness authority. P3.5 must not weaken it.

If P2.5 reports terminal/readiness state conflict (for example CODEX_COMPLETED not yet delivered, pending approval, nonterminal job, or concurrent prompt admission), return `BLOCKED / DELETE_NOT_READY` after factual re-read. Do not call P1 delete.

### TURN_RUNNING

Deletion must interrupt/reconcile first.

P3.5 obtains the exact currently active durable job through a narrow additive read/coherence repository. Only exact `CODEX_RUNNING` can be handed to P3.4 interrupt. `CLAIMED`/`CODEX_STARTING` are transient not-yet-interruptible application states and return `BLOCKED / DIALOGUE_NOT_READY`; there is no wait/queue.

Construct an internal exact `DialogueInterruptRequest` from the current durable dialogue/job IDs and versions and call accepted P3.4 once.

- P3.4 `CONFIRMED`/`RECONCILED` with exact resulting `IDLE` dialogue -> re-enter delete readiness using that exact new dialogue version;
- P3.4 `REJECTED` or `UNKNOWN` -> `BLOCKED / INTERRUPT_UNRESOLVED`;
- P3.4 `BLOCKED / INTERRUPT_IN_PROGRESS` -> `BLOCKED / INTERRUPT_IN_PROGRESS`;
- other P3.4 blocked/active-binding-unavailable outcomes -> `BLOCKED / INTERRUPT_UNRESOLVED`;
- P3.4 conflict -> `CONFLICT / STALE_REQUEST`;
- malformed/mismatched interrupt result -> `INVARIANT`.

If an interrupted turn completes as `CODEX_COMPLETED`, P2.5 may still reject deletion until delivery becomes terminal-safe. P3.5 must return `DELETE_NOT_READY`; it must not invent delivery completion or weaken P2.5.

### DELETE_PENDING

`DELETE_PENDING` proves that application delete intent is durable and P1.9 delete has not yet been exposed: P2.5 requires a separate `claim_deleting` before any external effect.

A NEW explicit delete request bound to the exact current `DELETE_PENDING` version may safely continue with `claim_deleting` and then one P1.9 delete attempt.

P3.5 performs no automatic startup continuation from `DELETE_PENDING`.

An old request carrying the pre-intent version is stale and must not silently resume after restart.

### DELETING

`DELETING` means an external delete may already have been dispatched. A second application invocation must never call P1.9 again.

Return `BLOCKED / DELETE_IN_PROGRESS` while the in-process owner exists. After process restart, startup recovery converts pre-existing `DELETING` to `DELETE_UNKNOWN` with zero P1 effect.

### DELETE_UNKNOWN

Return application `UNKNOWN` with the durable `DELETE_UNKNOWN` dialogue. No retry or second delete surface exists.

### Other states

`INTERRUPTING` -> `BLOCKED / INTERRUPT_IN_PROGRESS`.

`CREATING`, `CREATE_UNKNOWN`, `TURN_UNKNOWN`, `ERROR`, `DELETE_UNKNOWN` (except exact UNKNOWN reporting), and other non-ready states do not start delete and remain fail-closed.

## Durable delete ownership and cancellation

After an exact eligible IDLE/DELETE_PENDING/running-delete request has been accepted for orchestration, create one owned application task before the first P3.5-owned durable/effect-capable transition.

Caller cancellation is deferred through the owned sequence. Repeated cancellation must not create a second interrupt or delete effect and must not detach after P1.9 dispatch.

Concurrent same-generation delete requests have one owner. Losers return finite `CONFLICT`/`BLOCKED` states after re-read. There is never a queue.

## Exact delete sequence

For IDLE:

`claim_delete_intent -> DELETE_PENDING -> claim_deleting -> DELETING -> P1.9 delete -> finalize/unknown/error`

For exact current DELETE_PENDING:

`claim_deleting -> DELETING -> P1.9 delete -> finalize/unknown/error`

P1.9 is never called before durable `DELETING` is committed.

The application creates one `ThreadBinding(deleting.profile_id, deleting.thread_id)` from the exact durable DELETING row and passes that exact object to P1.9.

## P1.9 result mapping

Require exact `ThreadOperationResult`, exact `ThreadOperationStatus`, and for statuses carrying binding authority require the returned binding to be the exact supplied delete binding object.

### DELETE_CONFIRMED

Only exact `DELETE_CONFIRMED` permits local finalization.

Compute a bounded seven-day tombstone expiry using the application clock and overflow checks, then call accepted `DeletionRepository.finalize_confirmed` with the exact DELETING version.

On success:

- live dialogue is gone;
- owned jobs/payloads/delivery/approvals are purged by accepted P2.5/FK behavior;
- bounded content-free tombstone remains;
- return `DELETED` with exact tombstone.

If external delete is confirmed but local finalization fails, do not issue another delete. Preserve the durable DELETING evidence and surface finite STORAGE/INVARIANT. Restart recovery later makes it DELETE_UNKNOWN rather than redispatching.

### DELETE_UNKNOWN / malformed / uncertain exception

Never retry.

Atomically `DELETING -> DELETE_UNKNOWN` with sanitized exact error class `DELETE_UNKNOWN`, preserving profile/thread binding, and return application `UNKNOWN`.

A malformed result or returned binding mismatch is uncertainty, not confirmation.

### Deterministic local pre-dispatch failure

`THREAD_REQUEST_INVALID`, `THREAD_PRECONDITION_CHANGED`, and `THREAD_OPERATION_BUSY` are local/pre-effect failures under accepted P1.9 semantics. They perform no second call and terminalize the exact DELETING row as `ERROR` with sanitized `CODEX_PROCESS`, returning application `FAILED`.

Raw adapter details are never persisted/rendered.

## Tombstone retention

P3.5 freezes the application tombstone target at exactly seven days:

`P3_DELETE_TOMBSTONE_RETENTION_MS = 604800000`.

P2.6a remains cleanup authority. P3.5 does not add another tombstone sweeper.

## Final P3 startup recovery

Add `DialogueRecoveryService` with exact public callable surface:

- `recover_startup()`.

It has no P1/Codex/Telegram port and therefore cannot replay an external effect.

Add `DialogueRecoveryStatus` exactly:

- `NO_ACTION`;
- `CREATE_MARKED_UNKNOWN`;
- `PRE_EFFECT_FAILED`;
- `TURN_MARKED_UNKNOWN`;
- `INTERRUPT_MARKED_UNKNOWN`;
- `DELETE_MARKED_UNKNOWN`.

Add frozen:

`DialogueRecoveryResult(status, job, dialogue)`.

Add finite payload-free `DialogueRecoveryError` categories exactly:

- `STORAGE`;
- `INVARIANT`.

### Recovery precedence

At startup, inspect one canonical live dialogue and apply at most one recovery action.

1. no live dialogue -> `NO_ACTION`;
2. `CREATING` -> accepted P3.2 semantics: `CREATE_UNKNOWN / CODEX_AMBIGUOUS`, zero P1;
3. `INTERRUPTING` -> accepted P3.4 storage semantics: owning running job `UNKNOWN`, dialogue `TURN_UNKNOWN`, `CODEX_AMBIGUOUS`, zero P1;
4. `DELETING` -> accepted P2.5 `mark_delete_unknown(..., "DELETE_UNKNOWN")`, zero P1;
5. `DELETE_PENDING` -> `NO_ACTION`, preserve exact pending intent, zero P1; only a new explicit matching delete request may continue it;
6. `IDLE` with one canonical outstanding `RECEIVED` job -> deterministic pre-effect recovery: job `FAILED / CODEX_PROCESS`, version +1; dialogue remains exact IDLE and unchanged; ingress/input evidence remains;
7. `TURN_RUNNING` with exact owning `CLAIMED` job -> deterministic pre-effect recovery: job `FAILED / CODEX_PROCESS`, job version +1; dialogue -> `IDLE`, dialogue version +1, no dialogue error;
8. `TURN_RUNNING` with exact owning `CODEX_STARTING` or `CODEX_RUNNING` job -> effect may have occurred: job -> `UNKNOWN / CODEX_AMBIGUOUS`, dialogue -> `TURN_UNKNOWN / CODEX_AMBIGUOUS`, versions +1;
9. already `CREATE_UNKNOWN`, `TURN_UNKNOWN`, `DELETE_UNKNOWN`, `ERROR`, normal `IDLE`, or other already-terminal non-recovery state -> `NO_ACTION` unless the persisted cross-table shape is corrupt.

The `RECEIVED` and `CLAIMED` recovery cases are deterministic because accepted P3 persists `CODEX_STARTING` before invoking P1 turn/start. Therefore those states prove that no turn/start effect was dispatched.

`CODEX_STARTING` is ambiguous because a crash can occur before or after P1 start dispatch/confirmation but before durable `CODEX_RUNNING`.

Recovery does not generate output, does not delete INPUT evidence, does not consume ingress, and does not execute delayed user prompts.

A narrow additive schema-v1 storage coordination repository may implement the atomic pre-effect/turn recovery transitions. It must use existing `SqliteStorage.write`, exact canonical materialization, exact +1 versions, one clock only after all guards, overflow-before-clock, no retry and no schema change.

Repeated recovery is idempotent: after one recovery transition the next call returns `NO_ACTION`.

## Final P3 acceptance focus

P3.5 acceptance must materially prove:

- exact public records/enums/errors/redaction;
- tombstone replay is zero-effect idempotent;
- stale delete request cannot target a newer/different dialogue generation;
- IDLE delete readiness is delegated to P2.5, including pending-approval and terminal-delivery safeguards;
- prompt-admission vs delete-intent race in both orderings has one winner and no delayed work;
- TURN_RUNNING delete composes with exact P3.4 interrupt and never bypasses registry/interrupt authority;
- CODEX_COMPLETED after interrupt remains DELETE_NOT_READY until P2.5 readiness is satisfied;
- exact DELETE_PENDING explicit continuation is safe after reopen;
- old-version DELETE_PENDING request is stale;
- DELETING never causes a second P1.9 call;
- durable DELETING exists before P1.9 effect;
- P1.9 exact confirmed result causes one local finalize and exact seven-day tombstone;
- DELETE_UNKNOWN/malformed/uncertain result yields durable DELETE_UNKNOWN and no retry;
- deterministic local pre-effect delete failure yields ERROR and no retry;
- post-ownership repeated cancellation still yields one interrupt/delete maximum;
- concurrent delete requests have one owner;
- confirmed purge removes exact dialogue-owned content/execution roots and preserves accepted non-content ingress/callback/tombstone/error metadata;
- settings profile becomes mutable again only after confirmed no-dialogue finalization;
- recovery matrix for CREATING, IDLE+RECEIVED, TURN_RUNNING+CLAIMED, CODEX_STARTING, CODEX_RUNNING, INTERRUPTING, DELETE_PENDING, DELETING and already-UNKNOWN states;
- recovery makes zero P1/Telegram/network effects and never executes a delayed prompt/delete;
- P3.1/P3.2/P3.3/P3.4 behavior remains accepted;
- P2/P1 regressions remain green and DDL/schema unchanged;
- full fake/application P3 acceptance passes before P4.

## Out of scope

No Telegram private panel/callback wiring, group routing, response delivery execution, live token, real Codex thread deletion, empirical internal Codex storage-erasure proof, service/deployment work, production database/state root, P4 or later implementation.

P7 remains the authority for disposable real-thread `thread/delete` storage measurement and the architecture gate on residual Codex-owned storage.