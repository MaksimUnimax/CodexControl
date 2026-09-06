# ADR-0025 — P2 crash/restart/idempotency final acceptance

Status: accepted
Date: 2026-09-06

## Context

P2.1–P2.6a now implement the complete V1 local durable-state surface: SQLite ownership/migration, core state, ingress/control/callback idempotency, turn jobs/transient content, delivery/approvals/content retention, hard-delete finalization/tombstones/errors, and bounded metadata retention. Before P3 application orchestration begins, P2.6b must prove that the accepted repository surface behaves correctly across process restart, duplicate replay and representative abrupt-process boundaries.

P2.6b is an **acceptance/proof slice**, not a new production repository feature.

## Production-change rule

1. Normal P2.6b changes are tests and factual evidence only.
2. `src/codex_control/**` must remain byte-unchanged.
3. If a deterministic P2.6b test exposes a production defect, the executor stops and reports `P2_6B_PRODUCTION_DEFECT_STOP`; production is not silently repaired inside the acceptance slice.
4. No schema/DDL/migration change is permitted.

## Environment

- Temporary SQLite files only.
- No production state root, service, Telegram, Codex RPC or network effect.
- No authoritative in-memory cache may be relied on: close/reopen creates new storage/repository instances.
- Test clocks, IDs and payloads are deterministic and fake.

## Contract snapshot acceptance

P2.6b freezes the accepted P2 public storage contract in tests:

- schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`;
- all accepted repository public method surfaces remain exact;
- accepted enums/record field shapes remain exact;
- no P3 orchestration/effect method appears in storage repositories.

## Restart matrix

The harness must close and reopen the same database after committed boundaries and prove exact durable state/replay behavior.

### Controller/control

- persisted historical ACTIVE never restores effective ACTIVE on boot; `begin_boot` returns effective SLEEP after reopen;
- replay of an already-claimed activation update is DUPLICATE and cannot reactivate;
- a new control with an epoch not greater than durable `last_control_epoch` is STALE.

### Ingress/callback

- ignored ingress replay remains duplicate and cannot reclassify;
- callback fresh/consumed/expired terminal state persists across reopen;
- authorized one-time claim remains one-time; unauthorized identity does not learn subject state.

### Dialogue creation

- CREATING persists exactly; restart does not synthesize IDLE;
- confirm-created is exact-version/state bound;
- CREATE_UNKNOWN and ERROR persist as terminal facts until later application policy.

### Turn path

- committed `claim_ingress` persists the exact RECEIVED job + INPUT payload + JOB ingress atomically;
- replay of the same update reconstructs the durable duplicate; a different update remains blocked while the outstanding RECEIVED job exists;
- CLAIMED + TURN_RUNNING persists;
- CODEX_STARTING persists with no turn ID and no automatic external start;
- CODEX_RUNNING persists with its exact one-time turn ID;
- CODEX_COMPLETED/FAILED/UNKNOWN and optional OUTPUT persistence survive restart exactly.

### Delivery

- DELIVERY_PENDING plan persists;
- SENDING persists as an already-dispatched-attempt claim and cannot be blindly claimed again;
- intermediate canonical `C+P+` DELIVERING may resume by an explicit later `claim_next` call;
- DELIVERY_UNKNOWN persists and has no retry/reset API;
- DELIVERED/FAILED terminal history materializes exactly after reopen.

### Approval

- PENDING approval persists;
- callback consumption plus APPROVED/DENIED subject claim remains atomic after reopen;
- stale/expired callback terminalization remains consumed and cannot later become effective.

### Delete

- DELETE_PENDING and DELETING preserve the exact profile/thread binding across reopen;
- repository restart performs no P1.9 call;
- DELETE_UNKNOWN remains terminal/no-retry in P2;
- confirmed finalization persists tombstone + absence of live dialogue/owned rows; replay metadata remains only according to accepted retention authority.

### Retention/errors

- partial bounded metadata sweep followed by reopen continues from durable remaining roots, not cache;
- error fingerprint counts/timestamps and FK clearing survive restart exactly.

## Replay/no-blind-effect acceptance

P2.6b must prove that durable ambiguous/effect-claimed states do not create a second effect claim through repository replay:

- same ingress update never creates a second job;
- outstanding RECEIVED blocks a second different prompt rather than queues it;
- SENDING cannot become a second SENDING attempt;
- DELIVERY_UNKNOWN has no retry/reset surface;
- consumed/stale/expired callbacks cannot mutate a subject again;
- DELETE_UNKNOWN has no retry/reconcile surface;
- metadata cleanup never reconstructs deleted execution state.

P2.6b does not define application recovery decisions for `CODEX_STARTING`, `TURN_UNKNOWN`, `DELIVERY_UNKNOWN` or `DELETE_UNKNOWN`; P3/later layers own orchestration.

## Abrupt-process durability probes

The acceptance harness includes isolated subprocess tests using temporary databases only:

1. **Committed-return durability**: a representative repository transaction returns successfully, then the child exits via `os._exit` without graceful storage close. A fresh parent process/open must observe the committed state exactly.
2. **Uncommitted rollback**: a child enters one `SqliteStorage.write` transaction, performs test-only SQL writes, then exits abruptly from inside the callback before it returns to the kernel COMMIT path. Reopen must show no partial transaction and the database remains usable.

These probes are test-only and do not introduce a production crash API.

## Corruption/redaction acceptance

Representative persisted corruptions from each durable family must still fail closed through accepted materializers/repositories after reopen. Acceptance evidence may record categories/counts only and must not dump conversation content, raw callback tokens, raw external error bodies or secrets.

## Final P2 acceptance

P2 is complete only when:

- P2.6b acceptance modules pass;
- all accepted P2.1–P2.6a focused suites pass at their accepted counts;
- P1.10 and required focused P1 regressions remain green;
- full-discovery arithmetic is exact;
- DDL SHA, compile/import/diff/security checks pass;
- no production source, real external effect or production state was touched;
- the architect independently verifies the GitHub candidate.

After architect acceptance, ROADMAP may mark all P2 complete and move NEXT to P3. Codex must not make that roadmap decision itself.

## Out of scope

No P3 dialogue service, UNKNOWN reconciliation policy, Telegram/Codex effect, real profile/thread, production scheduler, deployment, filesystem temp-store implementation, schema migration or production state.