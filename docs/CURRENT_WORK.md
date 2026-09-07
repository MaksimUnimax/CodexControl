# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; full suite 543.
- P3.2 accepted at `c484c56db007569170363b3d08c24766148c3e30`; full suite 566.
- P3.3 accepted at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full suite 596.
- P3.4 durable interrupt orchestration/recovery is architect-accepted after one repair at `6460a449f861b7b86ab664e5ff877c108715082d`; full suite 633.
- P3.4 acceptance authority: `docs/evidence/p3/P3_4_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- ADR-0026/0027/0028/0029/0030 remain binding accepted P3.1–P3.4 authority.
- ADR-0031 is binding P3.5 authority.

## Accepted P3 application boundary

Existing dialogue prompt:

`duplicate/static -> existing-dialogue preflight -> claim_ingress -> claim_turn -> CODEX_STARTING -> P1 turn/start -> CODEX_RUNNING -> P1 wait -> finish_codex`

No-dialogue first prompt:

`duplicate/static -> settings/model/workdir preflight -> tombstone guard -> guarded CREATING -> first JOB/RECEIVED/INPUT -> thread/start -> confirm IDLE -> same admitted job -> accepted turn runner`

Settings selection is linearized with first-dialogue creation. Already-admitted profile/model/effort snapshots remain immutable.

Interrupt:

`exact version/job preflight -> exact ActiveTurnRegistry binding -> durable INTERRUPTING -> P1.8 interrupt/reconcile -> exact restore/terminal outcome`

P3.4 requires exact in-memory `TurnBinding` identity, commits INTERRUPTING before P1 interrupt, never blindly retries, reconciles natural terminal races, and makes pre-existing INTERRUPTING restart recovery zero-P1/UNKNOWN.

## P3.5 objective

P3.5 completes the dialogue application layer with:

1. hard-delete orchestration over accepted P1.9 + P2.5;
2. composition with P3.4 when delete is requested during an exact running turn;
3. safe explicit continuation from DELETE_PENDING but never blind replay from DELETING/DELETE_UNKNOWN;
4. confirmed local purge+tombstone only after exact P1.9 DELETE_CONFIRMED;
5. final no-P1 startup recovery for stranded admitted/running/delete states;
6. final P3 fake/application acceptance before Telegram P4.

## P1.9 delete authority

Accepted P1.9: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.

Exact facts:

- official external method is `thread/delete` with only exact `threadId`;
- profile/thread binding is exact durable authority;
- exactly one RPC per invocation;
- schema-valid object response is the sole `DELETE_CONFIRMED` authority;
- every dispatched non-success is `DELETE_UNKNOWN`;
- no DELETE_REJECTED, no automatic second delete, no thread/read/list guessing, no notification inference;
- pre-dispatch cancellation has zero effect; post-dispatch caller cancellation stays attached to the owned RPC.

P3.5 consumes this contract; it does not modify adapter semantics.

## P2.5 delete authority

Accepted P2.5: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.

Exact durable sequence:

`IDLE -> DELETE_PENDING -> DELETING -> confirmed finalization / DELETE_UNKNOWN / ERROR`.

P2.5 remains sole local readiness/finalization authority:

- claim_delete_intent requires exact IDLE/version/thread, no tombstone, no pending approval, and terminal-safe retained jobs;
- DELIVERED requires canonical all-confirmed delivery; FAILED history must be canonical;
- claim_deleting rechecks the same safeguards before any external effect;
- finalize_confirmed hashes the thread identity, records a bounded content-free tombstone, removes the exact live dialogue and cascades dialogue-owned jobs/payloads/delivery/approvals;
- non-content ingress/callback/tombstone/error metadata remains according to accepted retention authority;
- DELETE_UNKNOWN has no retry surface.

P3.5 must not weaken this readiness boundary. A normal CODEX_COMPLETED turn that has not reached safe delivery remains DELETE_NOT_READY.

## P3.5 public hard-delete authority

Add `DialogueDeleteService.delete(DialogueDeleteRequest)`.

Request exact fields:

`dialogue_id, expected_dialogue_version`.

Status exactly:

`DELETED | FAILED | UNKNOWN | BLOCKED | CONFLICT`.

Reason exactly:

`NO_DIALOGUE | DIALOGUE_NOT_READY | DELETE_NOT_READY | INTERRUPT_IN_PROGRESS | INTERRUPT_UNRESOLVED | DELETE_IN_PROGRESS | STALE_REQUEST`.

Result exact fields:

`status, dialogue, tombstone, reason`.

Error categories exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

No caller-supplied profile/thread identity.

## Hard-delete behavior

Tombstone replay with no live dialogue returns DELETED with zero effect. Tombstone/live collision is invariant corruption.

Matching IDLE:

`claim_delete_intent -> claim_deleting -> P1.9 delete -> finalize/unknown/error`.

Matching exact DELETE_PENDING may continue only from its CURRENT version:

`claim_deleting -> P1.9 delete -> finalize/unknown/error`.

DELETE_PENDING is never automatically resumed at startup. An old pre-intent version is stale.

DELETING never triggers a second delete invocation. A concurrent/repeated caller gets DELETE_IN_PROGRESS; after restart it becomes DELETE_UNKNOWN with zero P1.

DELETE_UNKNOWN is terminal uncertainty for P3.5 and has no retry.

TURN_RUNNING must compose with accepted P3.4 first. Only exact CODEX_RUNNING is interruptible. Definitive P3.4 reconciliation to IDLE re-enters P2.5 readiness; rejected/unknown interrupt does not proceed to delete. If the reconciled job is CODEX_COMPLETED but delivery is not terminal-safe, P2.5 blocks deletion and P3.5 reports DELETE_NOT_READY.

P1.9 is invoked only after durable DELETING. DELETE_CONFIRMED alone permits finalize_confirmed. DELETE_UNKNOWN/malformed/mismatched/uncertain result becomes durable DELETE_UNKNOWN. Deterministic local pre-dispatch request/precondition/busy failures become ERROR/CODEX_PROCESS. No retry.

Tombstone target is exactly seven days (`604800000` ms); P2.6a remains cleanup authority.

## Final P3 startup recovery

Add `DialogueRecoveryService.recover_startup()` with no P1/Codex/Telegram port.

Statuses exactly:

`NO_ACTION | CREATE_MARKED_UNKNOWN | PRE_EFFECT_FAILED | TURN_MARKED_UNKNOWN | INTERRUPT_MARKED_UNKNOWN | DELETE_MARKED_UNKNOWN`.

Recovery rules:

- CREATING -> CREATE_UNKNOWN / CODEX_AMBIGUOUS, same P3.2 semantics;
- INTERRUPTING -> owning running job UNKNOWN + dialogue TURN_UNKNOWN / CODEX_AMBIGUOUS, same P3.4 semantics;
- DELETING -> DELETE_UNKNOWN / DELETE_UNKNOWN, zero P1;
- DELETE_PENDING -> preserve and NO_ACTION; only fresh explicit delete may continue;
- IDLE + exact outstanding RECEIVED -> job FAILED / CODEX_PROCESS, dialogue stays IDLE;
- TURN_RUNNING + exact CLAIMED -> job FAILED / CODEX_PROCESS and dialogue IDLE;
- TURN_RUNNING + CODEX_STARTING or CODEX_RUNNING -> job UNKNOWN + dialogue TURN_UNKNOWN / CODEX_AMBIGUOUS;
- already unknown/error/normal terminal states -> NO_ACTION unless persisted shape is corrupt.

RECEIVED and CLAIMED are provably pre-effect because accepted runner persists CODEX_STARTING before P1 turn/start. CODEX_STARTING and CODEX_RUNNING are effect-possible and therefore UNKNOWN.

Recovery performs no delayed prompt execution, no external interrupt, no thread/delete, no output generation and no deletion of ingress/input evidence. Repeated recovery is idempotent.

A narrow additive schema-v1 storage coordinator may atomically implement the pre-effect/turn recovery transitions. No DDL change.

## P3.5 acceptance focus

Must prove:

- exact public surface/redaction;
- tombstone idempotent replay;
- stale generation cannot delete a newer/different live dialogue;
- IDLE readiness delegated to P2.5;
- prompt-admission/delete-intent races both orderings;
- exact P3.4 composition for running delete;
- no delete after unresolved interrupt;
- explicit DELETE_PENDING continuation after reopen and stale old-version rejection;
- DELETING/DELETE_UNKNOWN no second P1 effect;
- DELETING committed before P1.9 call;
- confirmed delete -> one finalize + exact tombstone/local purge;
- uncertain/malformed -> DELETE_UNKNOWN; deterministic local pre-effect failure -> ERROR;
- cancellation/concurrency one-effect maximum;
- final recovery matrix and zero external recovery effects;
- accepted P3.1–P3.4 and P1/P2 regressions; schema unchanged;
- final fake/application P3 acceptance before P4.

## P3 split

- **P3.1** — DONE.
- **P3.2** — DONE.
- **P3.3** — DONE.
- **P3.4** — DONE, accepted `6460a449f861b7b86ab664e5ff877c108715082d`.
- **P3.5** — NEXT, hard-delete orchestration + final P3 startup/application acceptance under ADR-0031.

## Out of scope for P3.5

No Telegram UI/callback wiring, group routing, delivery execution, live Codex/thread-delete call, physical Codex internal storage-erasure proof, production state, service/deployment work, P4+.

P7 remains authority for real disposable thread/delete storage measurement.

## Execution authority

Codex must not self-start work from this document.

Only P3.5 may be implemented from the next explicit architect prompt.