# Canonical state machines — V1

Unlisted success transitions are invalid.

## Controller routing
```text
BOOT -> SLEEP
SLEEP --ACTIVATE_SELF(newer M)--> ACTIVE
ACTIVE --ACTIVATE_SELF(newer M)--> ACTIVE
ACTIVE|SLEEP --ACTIVATE_OTHER_OR_UNKNOWN(newer M)--> SLEEP
ACTIVE|SLEEP --ALL_SLEEP(newer M)--> SLEEP
any --STALE_CONTROL(M<=last_epoch)--> no mutation
```
STATUS has no mode mutation. SLEEP ordinary text -> terminal IGNORED_SLEEP ingress disposition, no content retention.

## Dialogue
```text
NO_DIALOGUE -> CREATING                 first accepted prompt
CREATING -> IDLE                        thread/start confirmed + binding persisted
CREATING -> CREATE_UNKNOWN              ambiguous result
CREATING -> ERROR                       deterministic failure
IDLE -> TURN_RUNNING                    job claimed/turn accepted
IDLE -> DELETE_PENDING                  confirmed delete intent
TURN_RUNNING -> IDLE                    terminal result captured
TURN_RUNNING -> INTERRUPTING             operator interrupt/delete requires stop
TURN_RUNNING -> TURN_UNKNOWN             ambiguous process/protocol outcome
TURN_RUNNING -> ERROR                    deterministic terminal failure
INTERRUPTING -> IDLE                     terminal/reconciled
INTERRUPTING -> TURN_UNKNOWN             cannot prove terminal state
DELETE_PENDING -> DELETING               no running turn
DELETE_PENDING -> INTERRUPTING            running turn first
DELETING -> NO_DIALOGUE                  thread/delete + local purge confirmed
DELETING -> DELETE_UNKNOWN               ambiguous deletion
DELETING -> ERROR                        confirmed failure; binding frozen/retained
```
CREATE_UNKNOWN/TURN_UNKNOWN/DELETE_UNKNOWN permit only architect-defined read/reconciliation transitions; no new prompt starts there.

### Startup recovery authority

Startup recovery never replays an external Codex effect.

```text
CREATING -> CREATE_UNKNOWN               P3.2/P3.5 startup, no thread/start replay
INTERRUPTING -> TURN_UNKNOWN              P3.4/P3.5 startup, no interrupt replay
DELETING -> DELETE_UNKNOWN                P3.5 startup, no thread/delete replay
DELETE_PENDING -> DELETE_PENDING          startup holds durable pre-effect intent; fresh explicit delete may continue
IDLE + outstanding RECEIVED job           job -> FAILED(CODEX_PROCESS), dialogue remains IDLE
TURN_RUNNING + CLAIMED job                job -> FAILED(CODEX_PROCESS), dialogue -> IDLE
TURN_RUNNING + CODEX_STARTING job         job -> UNKNOWN(CODEX_AMBIGUOUS), dialogue -> TURN_UNKNOWN
TURN_RUNNING + CODEX_RUNNING job          job -> UNKNOWN(CODEX_AMBIGUOUS), dialogue -> TURN_UNKNOWN
```

`RECEIVED` and `CLAIMED` are deterministic pre-effect states because `CODEX_STARTING` is durably persisted before P1 `turn/start`. `CODEX_STARTING` and `CODEX_RUNNING` are effect-possible and therefore recover only to UNKNOWN. Recovery preserves ingress/input/identity evidence and never executes a delayed prompt.

## Turn job
```text
RECEIVED -> CLAIMED -> CODEX_STARTING -> CODEX_RUNNING
CODEX_RUNNING -> CODEX_COMPLETED | FAILED | UNKNOWN
CODEX_COMPLETED -> DELIVERY_PENDING -> DELIVERING
DELIVERING -> DELIVERED | DELIVERY_UNKNOWN | FAILED
```
The startup-only recovery exceptions above may terminalize stranded `RECEIVED`/`CLAIMED` jobs without passing through effect-intent states. UNKNOWN/DELIVERY_UNKNOWN are not automatic retry sources. Duplicate update returns existing disposition/job.

## Setting mutations
Profile change: only NO_DIALOGUE. Model/reasoning: NO_DIALOGUE defaults or IDLE after runtime validation; rejected during create/run/interrupt/delete/unknown states.

## Approval
`PENDING -> APPROVED | DENIED | EXPIRED | CANCELLED`. Only fresh PENDING record matching running job and exact operator/chat may mutate. EXPIRED fails closed.

## Hard-delete ordering
Do not purge reconciliation identifiers before external delete is definitive. Do not clear binding before confirmed hard delete. DELETE_UNKNOWN blocks new work and retains minimum exact identifiers needed to reconcile.

Hard-delete application ordering is:

```text
IDLE -> DELETE_PENDING -> DELETING -> exactly one P1 thread/delete attempt
DELETE_CONFIRMED -> local finalize -> NO_DIALOGUE + tombstone
DELETE_UNKNOWN/uncertain result -> DELETE_UNKNOWN
local deterministic pre-dispatch failure -> ERROR
```

A current `DELETE_PENDING` may be continued only by a fresh explicit request bound to that exact version, because no external delete has yet been exposed. A `DELETING` or `DELETE_UNKNOWN` row must never cause a second `thread/delete` call.