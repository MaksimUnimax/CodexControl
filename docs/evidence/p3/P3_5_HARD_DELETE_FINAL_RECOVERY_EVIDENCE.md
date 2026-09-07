# P3.5 hard-delete and final recovery implementation evidence

This is factual implementation evidence for Issue #27. It does not claim
architect acceptance, mark P3 complete, close the issue, or authorize P4.

## Base and scope

- Repository: `MaksimUnimax/CodexControl`
- Issue: `#27 — P3.5 — hard-delete orchestration + final P3 startup recovery`
- Base: `3e19f1028916613f7d89b254fdd7bf04505a2fb5`
- Branch: `impl-p3-5-hard-delete-final-recovery-2026-09-07`
- Governing ADR: `docs/adr/0031-hard-delete-orchestration-and-final-p3-recovery.md`
- Issue history read: issue body; no issue comments were present at implementation time.
- No architect-owned authority file was edited.

## Production implementation

Added:

- `src/codex_control/application/dialogue_delete.py`
- `src/codex_control/application/dialogue_recovery.py`
- `src/codex_control/storage/application_recovery.py`

Updated only for exports:

- `src/codex_control/application/__init__.py`

The storage coordinator uses existing schema-v1 tables and materializers. No
DDL, schema statement, accepted P1 adapter, P2.5 repository, P3.3 settings
lock, P3.1/P3.2 prompt semantics, or P3.4 implementation was changed.

## Delete contract and composition

`DialogueDeleteRequest`, `DialogueDeleteResult`, the exact delete statuses and
reasons, and finite `DialogueDeleteError` categories are frozen dataclasses or
enums with payload-free generic rendering. The only public service callable is
`delete(request)`.

The service reads tombstone and live dialogue before any mutation. Confirmed
tombstone replay returns the exact tombstone with zero clock, mutation, or P1
calls. Missing dialogue is `BLOCKED / NO_DIALOGUE`; stale IDs/versions are
`CONFLICT / STALE_REQUEST`; unknown and in-progress durable states remain
terminal/in-progress and do not redispatch effects.

For matching IDLE state, accepted P2.5 readiness is the sole gate. A
`CODEX_COMPLETED` job that is not delivery-safe therefore returns
`BLOCKED / DELETE_NOT_READY` with zero delete calls. The application performs
`claim_delete_intent`, then exact `claim_deleting`, and only calls the injected
P1.9 delete port after durable `DELETING`.

Running-turn delete uses an exact active durable job and constructs an internal
P3.4 `DialogueInterruptRequest`. It never reconstructs a P1.8 `TurnBinding`.
Only definitive P3.4 `CONFIRMED`/`RECONCILED` plus exact IDLE continuation
re-enters P2.5 readiness. Rejected/unknown or unresolved interrupt outcomes
produce `BLOCKED / INTERRUPT_UNRESOLVED`; interrupt-in-progress is preserved;
conflict is stale. CLAIMED and CODEX_STARTING are blocked without interrupt.

The P1.9 call receives `ThreadBinding` reconstructed from the exact durable
DELETING row. The result binding must be the same object as the supplied
binding. A cloned/equal binding, malformed result, exception uncertainty, or
`DELETE_UNKNOWN` becomes durable `DELETE_UNKNOWN`; no retry exists. The three
accepted local pre-effect categories become durable `ERROR / CODEX_PROCESS`
and application `FAILED`.

Exact `DELETE_CONFIRMED` alone permits local finalization. The application
retention target is `604800000` ms. Confirmed finalization leaves the accepted
content-free SHA-256 tombstone and purges live dialogue, jobs, owned transient
payloads, delivery segments, approvals and cascade-owned rows. Accepted
ingress/callback/error metadata remains under P2.5/P2.6 rules, with error
foreign keys cleared by existing cascade/set-null behavior. A clock or local
finalize failure after external confirmation raises finite STORAGE/INVARIANT,
does not issue another delete, and leaves DELETING evidence for startup
recovery.

Owned asyncio tasks defer cancellation after destructive orchestration begins.
Concurrent same-generation requests serialize through durable P2.5 claims;
focused tests observe one owner, at most one fake delete, and one tombstone.
There is no delayed prompt queue.

## Final startup recovery

`DialogueRecoveryService` has no P1, Codex, or Telegram lifecycle port and
exposes only `recover_startup()`. Its exact finite statuses and frozen result
fields are implemented with redacted generic rendering.

The narrow coordinator reads one canonical live dialogue and active/nonterminal
job set, then performs at most one atomic recovery transition:

- no dialogue, normal terminal states, and normal IDLE have `NO_ACTION`;
- CREATING becomes CREATE_UNKNOWN without thread/start;
- INTERRUPTING uses accepted P3.4 recovery and becomes TURN_UNKNOWN;
- DELETING becomes DELETE_UNKNOWN with `DELETE_UNKNOWN` error;
- DELETE_PENDING is held unchanged with no clock/effect;
- IDLE plus RECEIVED becomes FAILED/CODEX_PROCESS with job version +1;
- TURN_RUNNING plus CLAIMED becomes FAILED/CODEX_PROCESS and IDLE, both versions +1;
- TURN_RUNNING plus CODEX_STARTING or CODEX_RUNNING becomes UNKNOWN/
  TURN_UNKNOWN with CODEX_AMBIGUOUS, both versions +1.

Recovery does not call P1, create tasks, replay prompts, generate output, or
run a sweeper. Missing/multiple active jobs, owner mismatches, wrong states,
missing required identities/input/ingress, malformed rows, and signed-64
version overflow fail closed before clock or partial mutation. Repeated
recovery is `NO_ACTION` after the first durable terminal transition.

## Tests and acceptance

New focused tests:

- P3.5 unit: `4`
- P3.5 integration: `14`
- final fake/application acceptance: `1`

The focused coverage includes public surfaces, validation/redaction, IDLE
readiness, durable-before-P1 ordering, tombstone replay, local and ambiguous
P1 outcomes, cloned bindings, pending continuation/restart, DELETING restart,
running P3.4 composition, prompt/delete busy boundaries, concurrency,
recovery states, corruption/overflow, settings mutability after deletion, and
fake first/later turns with exact registry binding.

The final fake acceptance uses temporary SQLite and fake thread/turn/interrupt/
delete ports. It proves settings initialization, lazy first dialogue, same
thread later turn, running settings lock, exact registry binding, explicit
interrupt, no queue while busy/delete, durable DELETING, confirmed purge with
terminal job/display/delivery/approval/ingress/callback/error fixtures,
tombstone replay, profile mutation after deletion, and no startup external
effect.

## Regression and verification results

The accepted prior full suite contained `633` tests. After adding
`4 + 14 + 1` P3.5/final-acceptance tests, the required full discovery result
was `652` tests, all passing. The requested focused regression counts were
run at the accepted authority sizes:

- P3.4: `6/31`
- P3.3: `5/25`
- P3.2: `2/21`
- P3.1: `11/26`
- P2.C1: `5/1`
- P2.6b: `5/12/8/3`
- P2.6a: `4/28`
- P2.5: `4/18`
- P2.4b: `6/25`
- P2.4a: `8/31`
- P2.3: `7/28`
- P2.2: `6/20`
- P2.1: `8/31`
- P1.9: `15`
- P1.8: `28`
- P1.10: `6/1/4`

Commands passed:

```text
PYTHONPATH=src python3 -m compileall -q src tests
PYTHONPATH=src python3 -c '...required P3_5_IMPORT_PASS import...'
PYTHONPATH=src python3 -m unittest discover -s tests -v
git diff --check
```

The frozen schema-v1 DDL SHA remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

The known P1.6 pending-task warning was observed during the required suite:
`P1_6_PENDING_TASK_WARNING_OBSERVED=YES` and
`P1_6_WARNING_INTRODUCED_BY_P3_5=NO`.

## Security and effects

Tests used temporary SQLite only. No real Codex, thread/delete, interrupt,
Telegram, network, service, production database, production state root,
`auth.json`, or `secrets.env` was opened or changed. No credentials, tokens,
private keys, raw Telegram JSON, raw prompts/outputs in production diagnostics,
hidden reasoning, raw adapter exceptions, environment dumps, or production
paths were added. Test-only fake data and temporary paths are confined to test
fixtures. No P4 or later work was started.
