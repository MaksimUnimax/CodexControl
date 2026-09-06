# ADR-0030 — Durable turn interrupt orchestration and reconciliation

Status: accepted
Date: 2026-09-06

## Context

P3.3 is architect-accepted at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`. The application can now create or execute one durable dialogue turn and can safely mutate next-turn settings.

P1.8 already owns exact Codex `turn/interrupt` behavior. Its accepted contract is deliberately strict: interrupt accepts only the exact in-memory `TurnBinding` object retained by the P1 lifecycle adapter for the active turn. Reconstructed equal-looking bindings are rejected. P1.8 also reconciles interrupt wire outcome with the existing P1.6 collector and never blindly retries.

The application layer still lacks durable interrupt intent and restart authority. The V1 state machine requires:

- `TURN_RUNNING -> INTERRUPTING` before an operator interrupt effect;
- `INTERRUPTING -> IDLE` when a definitive terminal result is reconciled;
- `INTERRUPTING -> TURN_UNKNOWN` when terminal state cannot be proven;
- no new prompt while interrupt is pending/unknown.

A naive application sequence is unsafe for three reasons:

1. reading a running job and later calling P1.8 can interrupt a newer turn unless the request is bound to exact durable job/dialogue versions;
2. reconstructing a `TurnBinding` from SQLite cannot satisfy P1.8 identity authority;
3. accepted P2.4a `finish_codex` requires dialogue `TURN_RUNNING`, while P3.4 must durably move the dialogue to `INTERRUPTING` before external interrupt dispatch. Natural terminal completion and interrupt intent may therefore race in either order.

P3.4 introduces an application-owned exact-binding registry plus a narrow additive storage coordination primitive. Existing P1.8 and P2.4a semantics remain unchanged.

## Scope

P3.4 owns:

1. an in-memory registry for the exact active `TurnBinding` object returned by P1 turn/start;
2. publication/retirement of that exact object from the shared admitted-turn runner;
3. a version-bound Telegram-agnostic interrupt application service;
4. durable `TURN_RUNNING -> INTERRUPTING` claim before P1.8 dispatch;
5. interrupt/natural-terminal race reconciliation without weakening `TurnJobRepository.finish_codex`;
6. startup-only fail-closed recovery of pre-existing `INTERRUPTING` state.

P3.4 does not implement Telegram UI, callback actions, hard delete, thread resume, delivery, generic `TURN_RUNNING` restart recovery, real Codex acceptance or deployment.

## Public application surface

Add `DialogueInterruptService` with exact public callable surface:

- `interrupt(request)`;
- `recover_preexisting_interrupt()`.

### DialogueInterruptRequest

Frozen exact fields:

- `dialogue_id`;
- `job_id`;
- `expected_dialogue_version`;
- `expected_job_version`.

The request deliberately contains no profile/thread/turn IDs. Those are durable/internal authority, not caller-trusted interrupt targets.

### DialogueInterruptStatus

Exactly:

- `CONFIRMED`;
- `RECONCILED`;
- `REJECTED`;
- `UNKNOWN`;
- `BLOCKED`;
- `CONFLICT`.

### DialogueInterruptReason

Exactly:

- `NO_DIALOGUE`;
- `DIALOGUE_NOT_RUNNING`;
- `JOB_NOT_RUNNING`;
- `ACTIVE_BINDING_UNAVAILABLE`;
- `INTERRUPT_IN_PROGRESS`;
- `STALE_REQUEST`.

### DialogueInterruptResult

Frozen exact fields:

- `status`;
- `job` (`TurnJobRecord | None`);
- `dialogue` (`DialogueRecord | None`);
- `output_payload` (`TransientPayloadRecord | None`);
- `reason` (`DialogueInterruptReason | None`).

### InterruptRecoveryStatus

Exactly:

- `NO_ACTION`;
- `MARKED_UNKNOWN`.

### InterruptRecoveryResult

Frozen exact fields:

- `status`;
- `job` (`TurnJobRecord | None`);
- `dialogue` (`DialogueRecord | None`).

### DialogueInterruptError

Finite payload-free categories exactly:

- `INVALID_ARGUMENT`;
- `STORAGE`;
- `INVARIANT`.

No raw P1/repository text, thread/turn ID, CODEX_HOME, DB path, prompt/output content or credential appears in generic error rendering.

## Interrupt lifecycle port

The application uses one injected P1-compatible port exposing exactly:

- `interrupt_turn(binding: TurnBinding) -> TurnInterruptResult`;
- `wait_turn(binding: TurnBinding) -> TurnTerminalResult`.

P3.4 does not call `turn/start` itself and does not expose a retry method.

## Exact active-binding registry

P1.8 requires object identity, not reconstructed equality. P3.4 therefore adds one shared application-level `ActiveTurnRegistry`.

The registry stores the exact `TurnBinding` object returned by P1 `start_turn` for the active durable job.

Requirements:

- key by durable `job_id`;
- publish only the exact `TurnBinding` returned by P1;
- publication occurs after exact P1 start confirmation and before the corresponding durable `CODEX_RUNNING` state can become externally usable;
- only one binding may be active for one job;
- retire only the exact object/token owned by that execution;
- stale cleanup cannot remove a replacement;
- lookup returns the exact object, never a clone;
- registry repr/debug output does not expose profile/thread/turn IDs;
- registry is in-memory only and empty after process restart.

The same registry instance must be injected into the prompt-turn service and `DialogueInterruptService` by future composition. Existing P3.1/P3.2 constructors may keep optional-registry defaults for backward compatibility; their public callable surfaces remain unchanged.

A running durable job with no exact registry binding is not safe to interrupt. It is a finite blocked state, not a reason to reconstruct a binding.

## Public interrupt preflight

`interrupt(request)` first performs static request validation and then reads the exact live dialogue and exact job.

Required precedence:

1. no live dialogue -> `BLOCKED / NO_DIALOGUE`;
2. dialogue ID mismatch -> `CONFLICT / STALE_REQUEST`;
3. dialogue version mismatch -> `CONFLICT / STALE_REQUEST`;
4. dialogue `INTERRUPTING` -> `BLOCKED / INTERRUPT_IN_PROGRESS`;
5. dialogue state other than `TURN_RUNNING` -> `BLOCKED / DIALOGUE_NOT_RUNNING`;
6. referenced job absent or belongs to another dialogue/server/profile/thread -> finite `INVARIANT` or `BLOCKED / JOB_NOT_RUNNING` according to whether the persisted shape is corrupt versus simply not the active running job;
7. job version mismatch -> `CONFLICT / STALE_REQUEST`;
8. job state must be exact `CODEX_RUNNING` with non-null exact thread ID and Codex turn ID;
9. lookup exact `TurnBinding` from shared registry by job ID;
10. registry absence -> `BLOCKED / ACTIVE_BINDING_UNAVAILABLE`;
11. registry binding fields must exactly match durable profile/thread/turn; mismatch -> `INVARIANT`.

A stale request never retargets whatever turn happens to be current.

No P1 effect occurs before durable interrupt claim.

## Cancellation ownership

Static validation/preflight/registry lookup are effect-free and ordinary caller cancellation may propagate.

After exact interrupt eligibility is established, P3.4 creates one owned orchestration task before submitting the durable interrupt claim. The public invocation remains attached through:

`claim INTERRUPTING -> P1 interrupt/wait reconciliation -> durable terminal/restore outcome`.

Repeated caller cancellation after that ownership boundary is deferred and must not create a duplicate interrupt RPC or detach the exact operation.

Process crash is separate and handled by startup recovery.

## Atomic interrupt claim

Add an additive storage coordination repository under `src/codex_control/storage/` using the existing schema and `SqliteStorage.write` only.

Semantic operation equivalent to:

`claim_interrupt(dialogue_id, job_id, expected_dialogue_version, expected_job_version)`.

One transaction must:

- materialize exact dialogue and job;
- enforce exact IDs/versions;
- require dialogue `TURN_RUNNING`;
- require job `CODEX_RUNNING`;
- require exact server/profile/thread binding and non-null `codex_turn_id`;
- require the job belongs to the dialogue and exact running turn;
- increment dialogue version once;
- set dialogue state to `INTERRUPTING`;
- preserve dialogue thread/profile/server identity;
- preserve job state/version/turn ID unchanged;
- clock exactly once only after all semantic guards pass.

No new table/column is required.

## Rejected interrupt restore

A deterministic P1.8 `REJECTED` means the interrupt RPC was definitively rejected unless the collector already proves a terminal result.

Add atomic semantic operation equivalent to:

`restore_rejected_interrupt(...)`.

It requires the exact claimed `INTERRUPTING` dialogue and still-`CODEX_RUNNING` job and moves only:

`INTERRUPTING -> TURN_RUNNING`

with dialogue version +1. The job remains unchanged.

If the job/dialogue already terminalized due a natural-terminal race, the application reconstructs the terminal state instead of restoring or issuing another interrupt.

No retry of `turn/interrupt` follows rejection.

## Terminal projection

P3.4 reuses the accepted P3.1 terminal-message projection and output retention limits. Do not create a second projection format.

A definitive exact P1 terminal result must be bound to the exact registry binding.

Terminal meaning from `INTERRUPTING` is:

- terminal `COMPLETED` -> job `CODEX_COMPLETED`, dialogue `IDLE`, no error class;
- terminal `FAILED` -> job `FAILED`, dialogue `IDLE`, job error `CODEX_TURN_FAILED`, dialogue error cleared;
- unprovable/UNKNOWN -> job `UNKNOWN`, dialogue `TURN_UNKNOWN`, error `CODEX_AMBIGUOUS`.

The dialogue returns to IDLE for both definitive COMPLETED and FAILED because the state machine authority is `INTERRUPTING -> IDLE` on definitive terminal/reconciliation. This does not rewrite the accepted non-interrupt P2.4a rule where a natural FAILED terminal from `TURN_RUNNING` yields dialogue ERROR.

Partial user-visible agent messages from FAILED/UNKNOWN remain subject to the accepted uncertain-output retention rules. Empty output creates no OUTPUT payload or output ID.

## Natural-terminal / interrupt race

Do not weaken or replace accepted `TurnJobRepository.finish_codex`.

The shared admitted-turn runner keeps its existing normal finish path first.

If normal `finish_codex` succeeds from exact `TURN_RUNNING`, that outcome remains authoritative.

If normal finish receives the exact repository version/state conflict caused by a concurrent P3.4 interrupt transition, it may invoke the new interrupt coordination reconciliation path using the exact original job/dialogue identity and versions.

The new coordinator may recognize only exact interrupt-induced state/version shapes, not arbitrary drift.

Conceptual version progression from runner base dialogue version `V`, job version `K`:

- interrupt claim: dialogue `INTERRUPTING`, version `V+1`; job stays `K`;
- rejected restore: dialogue `TURN_RUNNING`, version `V+2`; job stays `K`;
- interrupt terminalization: job `K+1`, dialogue terminal version `V+2`;
- natural terminal after rejected restore: job `K+1`, dialogue terminal version `V+3`.

Already-terminal canonical state for the same job/binding may be reconstructed idempotently. Any incompatible version/state/identity shape fails closed.

This coordinator prevents a natural collector completion and an operator interrupt from corrupting each other regardless of which SQLite transition wins.

## P1.8 result normalization

### CONFIRMED / RECONCILED

Require exact `TurnInterruptResult`, exact binding identity and a definitive exact terminal result.

Persist/reconstruct the terminal state and return the corresponding application `CONFIRMED` or `RECONCILED` status.

Malformed/mismatched results are uncertainty, never success.

### REJECTED

If no definitive terminal has won:

- restore exact `INTERRUPTING -> TURN_RUNNING`;
- return application `REJECTED` with the still-running job/dialogue;
- no retry.

If the natural collector already terminalized, return `RECONCILED` with that terminal durable outcome.

### UNKNOWN / uncertain exception

Do not retry interrupt.

Use the same exact binding to call `wait_turn(binding)` once as reconciliation authority where the P1 collector is still available.

If exact definitive COMPLETED/FAILED terminal is proven, persist/reconstruct it and return `RECONCILED`.

Otherwise terminalize as job UNKNOWN + dialogue TURN_UNKNOWN and return application `UNKNOWN`.

### Local P1 interrupt errors

- `TURN_INTERRUPT_NOT_ACTIVE`: do not reconstruct or redispatch. Attempt exact collector reconciliation once; definitive terminal -> `RECONCILED`, otherwise `UNKNOWN`.
- `TURN_INTERRUPT_BUSY`: another interrupt effect may already be owned. Do not dispatch again. Attempt exact collector reconciliation once; definitive terminal -> `RECONCILED`, otherwise `UNKNOWN`.
- request-invalid/precondition mismatch attributable to local invariant/configuration fails closed without retry.

Raw adapter text is never persisted/rendered.

## Recovery

Expose startup-only:

`recover_preexisting_interrupt()`.

It performs no P1 call.

If there is no live dialogue or it is not `INTERRUPTING`:

- return `NO_ACTION`;
- no mutation.

If exact canonical pre-existing `INTERRUPTING` exists:

- find/materialize the exact owning `CODEX_RUNNING` job;
- atomically mark job `UNKNOWN` and dialogue `TURN_UNKNOWN` with `CODEX_AMBIGUOUS`;
- preserve thread/turn/job/ingress/input identifiers needed for later diagnosis/reconciliation;
- return `MARKED_UNKNOWN`.

Because the registry is empty after restart, P3.4 never calls interrupt again for that old state.

Repeated recovery is idempotent.

Pre-existing `TURN_RUNNING` is not automatically interrupted or terminalized by P3.4. Generic running-turn restart policy remains later final-P3 authority.

## Approval safety

P3.4 does not need to rewrite approval rows to make stale callbacks safe. Accepted approval callback claims already require job `CODEX_RUNNING` and dialogue `TURN_RUNNING`. Once interrupt claim/terminalization changes dialogue/job state, old callbacks fail stale/closed.

P3.4 must not broaden approval behavior or implement Telegram approval UX.

## Security

- no thread/turn ID in generic interrupt request/result/error repr beyond explicit durable records already accepted for trusted application use;
- no prompt/output content in request/error repr;
- output content remains only in explicit `TransientPayloadRecord.content` and repr-safe accepted payload behavior;
- registry repr is identity-redacted;
- no raw P1 error, CODEX_HOME, DB path, stdout/stderr, environment or credentials in generic diagnostics;
- tests use temporary SQLite and fake lifecycle ports only.

## Required acceptance focus

P3.4 tests must materially prove:

- exact public surfaces/frozen records/redaction;
- exact-binding object identity registry and stale-cleanup safety;
- durable INTERRUPTING before P1 interrupt dispatch;
- stale request cannot target a newer turn;
- one interrupt RPC maximum;
- post-claim cancellation ownership;
- CONFIRMED/RECONCILED/REJECTED/UNKNOWN mappings;
- malformed/mismatched P1 result fail-closed behavior;
- rejection restore without retry;
- natural terminal before claim, after claim, and racing restore/finalize;
- exact output projection/retention and no duplicate OUTPUT;
- P3.1/P3.2 normal turn semantics remain unchanged without interrupt;
- settings mutation remains blocked while INTERRUPTING;
- restart recovery of pre-existing INTERRUPTING is no-P1/idempotent/preserves evidence;
- old approval callback cannot become valid again after interrupt state transition;
- no DDL/schema drift and prior regressions remain green.

## Out of scope

No Telegram private UI/callback wiring, group routing, hard delete, thread delete orchestration, CREATE_UNKNOWN reset, generic TURN_RUNNING restart scanner, delivery, real Codex acceptance, production state or deployment is authorized.