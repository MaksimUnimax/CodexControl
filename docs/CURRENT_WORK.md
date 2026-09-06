# Current work authority

Date: 2026-09-06

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; full suite 543.
- P3.2 accepted at `c484c56db007569170363b3d08c24766148c3e30`; full suite 566.
- P3.3 settings selection/dialogue linearization is architect-accepted after one repair at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full suite 596.
- P3.3 acceptance authority: `docs/evidence/p3/P3_3_ARCHITECT_ACCEPTANCE_2026-09-06.md`.
- ADR-0026/0027/0028/0029 remain binding accepted P3.1–P3.3 authority.
- ADR-0030 is binding P3.4 authority.

The exact P3.3 architect base was `fc0d57e665f0aad8044934b24396de7d07ee56ef`. Any textual report spelling with an extra trailing character is not authority.

## Accepted P3 application boundary

Existing dialogue prompt:

`duplicate/static -> existing-dialogue preflight -> claim_ingress -> claim_turn -> CODEX_STARTING -> P1 turn/start -> CODEX_RUNNING -> P1 wait -> finish_codex`

No-dialogue first prompt:

`duplicate/static -> settings/model/workdir preflight -> tombstone guard -> guarded CREATING -> first JOB/RECEIVED/INPUT -> thread/start -> confirm IDLE -> same admitted job -> accepted turn runner`

P3.2 first-dialogue create is atomically bound to the exact P3.3 settings snapshot. Stale selection yields `BLOCKED / SETTINGS_CHANGED`, with no delayed execution.

P3.3 profile mutation is legal only with no live dialogue. Model/reasoning real mutation is legal only with no dialogue or an exact matching IDLE dialogue. Already-admitted job snapshots remain immutable.

## P3.4 objective

P3.4 adds durable operator interrupt orchestration over accepted P1.8.

It must establish durable `INTERRUPTING` authority before the external interrupt effect, preserve the exact in-memory P1 `TurnBinding` object required by P1.8 identity checks, reconcile interrupt and natural-terminal races, and define startup recovery for pre-existing `INTERRUPTING` without repeating interrupt.

P3.4 must not weaken accepted P1.8 or P2.4a behavior.

## P1.8 dependency authority

Accepted P1.8 at `6d8a07b5b95ef377cf60762f4475128bdf810b22` owns exact `turn/interrupt` semantics.

Important P1.8 facts:

- interrupt accepts only the exact active `TurnBinding` object retained by the adapter;
- reconstructed equal-looking bindings are rejected before dispatch;
- exactly one interrupt RPC is sent; no retry;
- the existing P1.6 collector is the sole terminal evidence consumer;
- `interrupt_turn` may return `CONFIRMED`, `RECONCILED`, `REJECTED`, or `UNKNOWN`;
- CONFIRMED/RECONCILED can carry the exact definitive terminal result;
- caller cancellation after dispatch remains owned;
- ambiguous interrupt plus definitive collector terminal can reconcile;
- ambiguous/no definitive terminal remains UNKNOWN.

P3.4 must consume this contract rather than duplicate protocol behavior.

## P3.4 public application additions

Add `DialogueInterruptService` with exact public callable surface:

- `interrupt(request)`;
- `recover_preexisting_interrupt()`.

Add frozen:

`DialogueInterruptRequest(dialogue_id, job_id, expected_dialogue_version, expected_job_version)`.

Caller input deliberately contains no thread or turn ID.

Add `DialogueInterruptStatus` exactly:

- `CONFIRMED`;
- `RECONCILED`;
- `REJECTED`;
- `UNKNOWN`;
- `BLOCKED`;
- `CONFLICT`.

Add `DialogueInterruptReason` exactly:

- `NO_DIALOGUE`;
- `DIALOGUE_NOT_RUNNING`;
- `JOB_NOT_RUNNING`;
- `ACTIVE_BINDING_UNAVAILABLE`;
- `INTERRUPT_IN_PROGRESS`;
- `STALE_REQUEST`.

Add frozen:

`DialogueInterruptResult(status, job, dialogue, output_payload, reason)`.

Add `InterruptRecoveryStatus` exactly:

- `NO_ACTION`;
- `MARKED_UNKNOWN`.

Add frozen:

`InterruptRecoveryResult(status, job, dialogue)`.

Add finite payload-free `DialogueInterruptError` with exact categories:

- `INVALID_ARGUMENT`;
- `STORAGE`;
- `INVARIANT`.

No thread/turn identity, CODEX_HOME, DB path, prompt/output content, raw adapter/repository errors or credentials may appear in generic request/error rendering.

## Exact active TurnBinding registry

P1.8 object-identity authority means a `TurnBinding` may not be reconstructed from SQLite for interrupt.

P3.4 adds a shared in-memory `ActiveTurnRegistry` keyed by durable job ID.

Requirements:

- store the exact `TurnBinding` object returned by P1 `start_turn`;
- publish it after exact start confirmation and before durable CODEX_RUNNING becomes externally usable;
- lookup returns the same object identity;
- retire only the exact owned entry;
- stale cleanup cannot remove a replacement;
- no profile/thread/turn values in registry repr;
- registry is empty after restart.

The admitted-turn runner must accept/integrate an optional registry. Existing P3.1/P3.2 service callable surfaces and default behavior remain unchanged.

Future runtime composition must inject the same registry instance into prompt execution and interrupt service.

A durable running job without the exact registry binding is `BLOCKED / ACTIVE_BINDING_UNAVAILABLE`; P3.4 never fabricates a replacement binding.

## Interrupt request authority

`DialogueInterruptRequest` binds the operator action to exact durable job/dialogue IDs and versions.

A stale request must never target a newer turn.

Required semantic precedence after static validation:

1. no live dialogue -> `BLOCKED / NO_DIALOGUE`;
2. dialogue ID or expected dialogue version mismatch -> `CONFLICT / STALE_REQUEST`;
3. dialogue already INTERRUPTING -> `BLOCKED / INTERRUPT_IN_PROGRESS`;
4. dialogue not TURN_RUNNING -> `BLOCKED / DIALOGUE_NOT_RUNNING`;
5. missing/non-running referenced job -> `BLOCKED / JOB_NOT_RUNNING` unless persisted shape is corrupt;
6. job version mismatch -> `CONFLICT / STALE_REQUEST`;
7. job must be exact CODEX_RUNNING and match dialogue server/profile/thread with non-null codex turn ID;
8. exact registry binding must exist and match durable profile/thread/turn;
9. absent registry -> `BLOCKED / ACTIVE_BINDING_UNAVAILABLE`;
10. registry/durable mismatch -> application INVARIANT.

No P1 interrupt occurs before durable interrupt claim.

## Ownership boundary

Preflight is effect-free and caller cancellation may propagate.

After exact eligibility/registry binding is established, create one owned task before the durable interrupt claim. From that point caller cancellation is deferred through:

`claim INTERRUPTING -> P1 interrupt/reconciliation -> durable restore/terminal result`.

Repeated cancellation must not cause duplicate interrupt RPCs.

## Atomic interrupt storage authority

P3.4 may add one narrow storage module/repository using existing `SqliteStorage.write` and schema-v1 only.

Do not modify the semantics of accepted `TurnJobRepository.finish_codex`.

### claim_interrupt

Semantic method equivalent to:

`claim_interrupt(dialogue_id, job_id, expected_dialogue_version, expected_job_version)`.

One transaction must materialize exact dialogue/job, enforce IDs/versions, require dialogue TURN_RUNNING + job CODEX_RUNNING + exact server/profile/thread/turn ownership, then:

- dialogue -> INTERRUPTING;
- dialogue version +1;
- job unchanged;
- one mutation clock after all guards.

### restore_rejected_interrupt

For a definitive P1 REJECTED result where the exact job is still running:

- require exact claimed INTERRUPTING shape;
- dialogue -> TURN_RUNNING;
- dialogue version +1;
- job unchanged;
- no retry.

If natural terminal already won, reconstruct terminal state rather than restoring.

### terminal reconciliation

P3.4 needs additive race-safe terminal coordination. Accepted P2.4a normal `finish_codex` stays first authority for ordinary TURN_RUNNING completion.

Only when normal finish conflicts because the exact interrupt transition raced may the shared turn runner invoke the P3.4 reconciliation primitive.

The coordinator must recognize only exact interrupt-induced version/state shapes, not arbitrary drift.

Conceptual base: runner dialogue version V, job K.

- interrupt claim: INTERRUPTING V+1, job K;
- rejected restore: TURN_RUNNING V+2, job K;
- interrupt terminalization: job K+1, dialogue terminal V+2;
- natural terminal after restore: job K+1, dialogue terminal V+3.

Canonical already-terminal state for the same job/binding may be reconstructed idempotently. Incompatible shape is INVARIANT/conflict, not normalization.

## Terminal mapping after interrupt claim

From durable INTERRUPTING:

- definitive P1 terminal COMPLETED -> job CODEX_COMPLETED, dialogue IDLE;
- definitive P1 terminal FAILED -> job FAILED with `CODEX_TURN_FAILED`, dialogue IDLE;
- unprovable terminal -> job UNKNOWN, dialogue TURN_UNKNOWN, `CODEX_AMBIGUOUS`.

Definitive FAILED returns dialogue IDLE because the accepted state machine says `INTERRUPTING -> IDLE` for definitive terminal/reconciled interrupt. Ordinary non-interrupt failure from TURN_RUNNING still uses accepted P2.4a mapping to dialogue ERROR.

Reuse accepted P3 terminal message projection/output limits and retention. Do not create a second projection contract. Empty projected output creates no OUTPUT payload or ID.

## P1 interrupt result mapping

### CONFIRMED / RECONCILED

Require exact `TurnInterruptResult`, exact same binding identity and exact definitive terminal result. Persist/reconstruct terminal state. Return matching application status.

Malformed/mismatched result is uncertainty, not success.

### REJECTED

If exact running state remains, restore INTERRUPTING -> TURN_RUNNING and return REJECTED. No retry.

If natural terminal already won, reconstruct it and return RECONCILED.

### UNKNOWN / uncertain exception

Never redispatch interrupt.

Use the exact same registry binding to call `wait_turn(binding)` once where collector authority remains available.

Definitive exact COMPLETED/FAILED -> durable reconcile and application RECONCILED.

Otherwise -> job UNKNOWN + dialogue TURN_UNKNOWN and application UNKNOWN.

### Local interrupt errors

`TURN_INTERRUPT_NOT_ACTIVE` and `TURN_INTERRUPT_BUSY` are never retry triggers. Reconcile the exact collector once; definitive terminal -> RECONCILED, otherwise UNKNOWN.

Other impossible/local mismatch paths fail closed. No raw adapter text.

## Natural terminal race

The shared admitted-turn runner remains the owner of ordinary natural terminal capture.

It must publish the exact binding registry object during the active turn and retire it on exact terminal ownership completion.

Normal finish calls existing `TurnJobRepository.finish_codex` first.

If P3.4 has already changed the exact dialogue to INTERRUPTING/restored-turn shape, a narrowly-scoped interrupt-race fallback may finalize/reconstruct through the new coordinator.

This must preserve normal P3.1/P3.2 behavior when no interrupt occurs.

## Restart recovery

`recover_preexisting_interrupt()` is startup-only and makes zero P1 calls.

No live dialogue or non-INTERRUPTING -> `NO_ACTION`, no mutation.

Canonical pre-existing INTERRUPTING must have one exact owning CODEX_RUNNING job. Atomically:

- job -> UNKNOWN;
- dialogue -> TURN_UNKNOWN;
- `CODEX_AMBIGUOUS`;
- preserve durable thread/turn/job/ingress/input evidence;
- return `MARKED_UNKNOWN`.

Registry is empty after restart, therefore never repeat the old interrupt.

Repeated recovery is idempotent.

P3.4 does not auto-recover a generic pre-existing TURN_RUNNING state.

## Approval boundary

No approval storage redesign is required. Existing callback authority requires job CODEX_RUNNING and dialogue TURN_RUNNING; after interrupt claim/terminalization old callbacks fail stale/closed.

Do not add Telegram approval UX in P3.4.

## P3.4 acceptance focus

Tests must prove at minimum:

- exact public surfaces/frozen records/error redaction;
- exact binding object identity registry;
- registry stale-cleanup safety;
- durable INTERRUPTING before P1 dispatch;
- stale request cannot interrupt newer turn;
- one interrupt effect maximum;
- post-claim repeated cancellation ownership;
- CONFIRMED, RECONCILED, REJECTED, UNKNOWN mappings;
- malformed/mismatched P1 result fail-closed;
- rejection restore and no retry;
- natural terminal before interrupt claim and after claim;
- terminal/interrupt/restore race orderings;
- no duplicate job/output terminalization;
- output projection/retention remains accepted;
- startup INTERRUPTING recovery is no-P1, idempotent, preserves evidence;
- settings mutation remains blocked in INTERRUPTING;
- stale approval callbacks do not become valid;
- P3.1/P3.2/P3.3 no-interrupt behavior remains unchanged;
- DDL/schema unchanged and full prior regressions green.

## P3 split

- **P3.1** — DONE.
- **P3.2** — DONE.
- **P3.3** — DONE.
- **P3.4** — NEXT, durable interrupt orchestration/recovery under ADR-0030.
- **P3.5** — planned hard-delete orchestration + final P3 recovery/application acceptance.

## Out of scope for P3.4

No Telegram UI/callback wiring, group routing, hard-delete/thread-delete orchestration, CREATE_UNKNOWN reset, generic TURN_RUNNING restart scanner, delivery, real Codex acceptance, production state or deployment.

## Execution authority

Codex must not self-start work from this document.

Only P3.4 may be implemented from the next explicit architect prompt.