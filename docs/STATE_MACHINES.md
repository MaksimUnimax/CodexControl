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

## Turn job
```text
RECEIVED -> CLAIMED -> CODEX_STARTING -> CODEX_RUNNING
CODEX_RUNNING -> CODEX_COMPLETED | FAILED | UNKNOWN
CODEX_COMPLETED -> DELIVERY_PENDING -> DELIVERING
DELIVERING -> DELIVERED | DELIVERY_UNKNOWN | FAILED
```
UNKNOWN/DELIVERY_UNKNOWN are not automatic retry sources. Duplicate update returns existing disposition/job.

## Setting mutations
Profile change: only NO_DIALOGUE. Model/reasoning: NO_DIALOGUE defaults or IDLE after runtime validation; rejected during create/run/interrupt/delete/unknown states.

## Approval
`PENDING -> APPROVED | DENIED | EXPIRED | CANCELLED`. Only fresh PENDING record matching running job and exact operator/chat may mutate. EXPIRED fails closed.

## Hard-delete ordering
Do not purge reconciliation identifiers before external delete is definitive. Do not clear binding before confirmed hard delete. DELETE_UNKNOWN blocks new work and retains minimum exact identifiers needed to reconcile.
