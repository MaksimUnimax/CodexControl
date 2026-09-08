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
STATUS has no mode mutation.

P5.2 ordinary group TEXT admission is:

```text
existing durable ingress(update_id) -> DUPLICATE, no new effect
same-update local in-flight marker -> in-flight DUPLICATE, no rejected claim
message_id <= last_control_epoch -> terminal IGNORED_REJECTED
fresh TEXT + effective SLEEP -> terminal IGNORED_SLEEP
fresh TEXT + ACTIVE + different local prompt marker -> terminal IGNORED_REJECTED/BUSY
fresh TEXT + ACTIVE + no marker -> publish local marker -> accepted P3 execution outside group lock
P3 pre-JOB BUSY/BLOCKED -> terminal IGNORED_REJECTED before return
P3 COMPLETED/FAILED/UNKNOWN after JOB -> preserve JOB; never reclassify rejected
```

The P5.2 local marker is process-local, non-content and non-durable. It is not restored after restart and is never JOB/dialogue authority. Controls remain processable while accepted P3 runs. SLEEP does not implicitly interrupt an already admitted turn; interrupt is explicit P3.4/P4 authority.

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

## P6.1 response delivery

P6.1 composes the accepted P2.4b delivery state machine; it does not add durable states.

Initial successful delivery:

```text
CODEX_COMPLETED + no plan
  -> create bounded DISPLAY chunks
  -> durable immutable delivery plan
  -> DELIVERY_PENDING
```

One segment attempt:

```text
PENDING/attempt0
  -> claim_next commits SENDING/attempt1 + job DELIVERING
  -> exactly one TelegramDeliveryPort effect
  -> CONFIRMED => segment CONFIRMED
  -> UNKNOWN   => segment UNKNOWN + job DELIVERY_UNKNOWN
  -> FAILED    => segment FAILED + job FAILED
```

After CONFIRMED:

```text
confirmed prefix + remaining PENDING -> claim first pending only
all CONFIRMED -> job DELIVERED
```

No confirmed segment is recreated. No UNKNOWN/FAILED segment is retried automatically.

Recovery of effect-possible SENDING is fail-closed:

```text
new explicit delivery invocation
+ job DELIVERING
+ exact existing SENDING/attempt1
  -> ZERO Telegram effect
  -> finish_sending(UNKNOWN, TELEGRAM_RECOVERY_AMBIGUOUS)
  -> DELIVERY_UNKNOWN
```

A durable confirmed prefix followed only by pending segments is safe to resume because no unclassified effect is exposed for the pending suffix.

A storage failure after a possible external message effect may leave SENDING durable. The same recovery rule applies on the next explicit invocation; there is no blind resend.

P6.1 delivers only CODEX_COMPLETED work. Codex FAILED/UNKNOWN without a delivery plan is not promoted into delivery states by P6.1.

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
