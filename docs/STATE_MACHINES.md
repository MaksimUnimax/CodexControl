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

Durable approval state remains:

```text
PENDING -> APPROVED | DENIED | EXPIRED | CANCELLED
```

P4.3 Allow/Deny is an atomic PENDING-only transition bound to the exact running job/version and exact operator/chat. Terminal approval states never transition back to PENDING and are never overwritten by another terminal decision.

P6.2 live approval coordination adds no durable state. Its exact flow is:

```text
exact P1.7 InboundServerRequest already owned by current client
  -> normalize/bind to exact CODEX_RUNNING job/turn
  -> register process-local wake waiter
  -> publish durable PENDING approval
  -> P4.3 callback OR expiry/lost-request terminalizer wins one durable terminal state
  -> operator re-reads exact approval
  -> APPROVED => ALLOW
  -> DENIED|EXPIRED|CANCELLED => DENY
  -> accepted P1.7 performs exactly one response attempt
```

The process-local decision signal is wake-only and is never decision authority. A notification while the approval remains PENDING causes only another durable read; it cannot grant ALLOW.

P6.2 per-approval terminalization is:

```text
PENDING + due expiry -> EXPIRED
PENDING + exact live P1.7 ownership lost/protocol terminal -> CANCELLED
already terminal + terminalize request -> unchanged terminal record
```

Expiry and P4.3 callback decisions race through SQLite; exactly one terminal state wins. `CANCELLED`/`EXPIRED` never consume or revive an Allow/Deny callback; later callbacks become stale/terminal under accepted P2.4b/P4.3 authority.

After a PENDING approval exists, transient storage/read failure is not authority to fabricate DENY while the row may still be actionable. Safety wins over liveness: remain waiting for durable terminal authority or exact P1.7 protocol terminal.

Process restart destroys old P1.7 wire ownership:

```text
old InboundServerRequest / old CodexProtocolClient ownership -> GONE
persisted APPROVED|DENIED|EXPIRED|CANCELLED/PENDING metadata -> never reconstruct old wire request
new client + reconstructed same wire ID -> no response authority
```

P3/P6.3 startup recovery may later terminalize the job and use existing post-turn approval cleanup. No old approval response is replayed after restart.

## P6.3 final local orchestration

P6.3 adds no durable state. It composes the accepted turn, approval and delivery state machines.

Live execution is:

```text
P3 persists CODEX_STARTING
  -> one process-local safe work-status CREATE attempt
  -> accepted P1.6 turn/start on exact captured runtime
  -> P3 persists CODEX_RUNNING
  -> P6.3 waits for turn terminal while pumping exact P1.7 server requests
  -> P6.2 publishes/awaits durable approvals as needed
  -> accepted P1.6 terminal
  -> P3 durable CODEX_COMPLETED | FAILED | UNKNOWN
  -> COMPLETED: accepted P6.1 final delivery
  -> FAILED|UNKNOWN: one live non-durable safe status attempt only
```

The work-status message ID is not durable P6.3 state. A confirmed live ID may be supplied to P6.1 as the initial first-EDIT hint. Only the immutable P2.4b delivery plan makes that target durable. Process restart restores no work-status hint and never replays acknowledgement/status CREATE.

Turn/approval concurrency is fail-closed:

```text
turn terminal while only waiting for next server request
  -> cancel/join request-get
  -> no captured request => original terminal stands
  -> captured exact owned request in race => one DENY response, runtime shutdown, projected UNKNOWN

turn terminal while live P6.2 approval is pending
  -> do not guess/cancel approval handler
  -> shutdown exact captured profile runtime
  -> P1.7/P6.2 => RESPONSE_UNKNOWN + best-effort CANCELLED
  -> projected turn UNKNOWN
```

Every turn-terminal/request-get/approval-handler helper is owned and joined. There is no delayed approval queue and no runtime reacquire to recreate ownership.

P6.3 startup composition is:

```text
accepted P3.5 DialogueRecoveryService.recover_startup()
  -> cancel leftover PENDING approvals only after their recovered job is no longer CODEX_RUNNING
  -> discover oldest CODEX_COMPLETED|DELIVERY_PENDING|DELIVERING job
  -> accepted P6.1 with status_message_id=None
  -> repeat up to 256 candidates
  -> no remaining candidate => READY
  -> candidates still remain => LIMIT_REACHED
```

A startup `CODEX_COMPLETED` job creates an all-CREATE final plan because process-local status hints are never restored. A stranded durable SENDING segment follows accepted P6.1 zero-resend recovery to DELIVERY_UNKNOWN. Confirmed-prefix/PENDING resumes only at the first pending segment. P6.3 creates no background recovery worker.

Later live update ingestion must not start until explicit startup recovery returns READY. Controller effective mode still boots SLEEP under accepted P5.1.

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
