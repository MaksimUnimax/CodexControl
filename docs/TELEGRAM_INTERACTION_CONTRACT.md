# Telegram interaction contract — V1

## Surfaces
1. Configured private supergroup `CODEX CONTROL`: fleet selection and actual Codex conversation.
2. Private chat with each server bot: settings, dialogue administration, diagnostics.
Only the exact configured operator is supported.

## Group message visibility
Deployment must configure each bot to receive authorized ordinary supergroup messages (privacy disabled or administrator as appropriate) and acceptance must prove it.

## Persistent fleet keyboard
Use persistent ReplyKeyboardMarkup because presses become human-user messages observable by all bots. All controllers render the same non-secret fleet manifest.

Conceptual keyboard: `[🖥 SERVER-80] [🖥 SERVER-78] [...]` then `[💤 ВСЕ СПАТЬ] [📊 СТАТУС]`.

Activation prefix family is reserved. Any authorized activation-looking message is control, never Codex prompt. Exact self label -> ACTIVE; any other/unknown target -> SLEEP. All-sleep -> SLEEP. Status -> no mutation. Process restart -> SLEEP until new self activation.

## Ordering
Configured control-chat messages are routed through one local P5 group facade. A short application lock serializes each control/TEXT admission decision, but it is not held while Codex executes a turn.

Do not enable a competing group handler that bypasses this facade and can run the same stream directly through P5.1/P3.

The durable control epoch is the accepted supergroup message ID of the last applied control. A prompt is eligible only when its `message_id` is strictly greater than `last_control_epoch`. A prompt at or below the current durable control epoch is terminally `IGNORED_REJECTED` and never Codex work.

A control accepted after a prompt has already been logically admitted does not retroactively cancel that turn. It governs subsequent prompt admissions. Explicit STOP remains private interrupt authority.

## Ordinary prompt eligibility
A prompt must be:

- unique update or the still-owned first delivery of the same local in-flight update;
- exact operator;
- exact configured supergroup;
- human-originated ordinary text;
- not command/control/service content;
- newer than the current durable control epoch;
- effective ACTIVE;
- not blocked by another locally admitted prompt;
- acceptable to accepted P3 request validation;
- admitted by accepted P3 durable dialogue/JOB authority.

SLEEP -> terminal content-free `IGNORED_SLEEP`, no P3.

Different prompt while a local P3 prompt is still in flight -> BUSY + terminal content-free `IGNORED_REJECTED`, not queue.

Accepted P3 BUSY/BLOCKED before JOB -> terminal content-free `IGNORED_REJECTED` before successful P5.2 return.

A replay of a durable SLEEP/rejected/JOB/control/unauthorized update returns duplicate authority and never changes classification.

The same update redelivered while its original P5.2 P3 invocation is still locally in flight must not be claimed rejected, because that could suppress the original first execution. It is an in-flight duplicate with zero redispatch; the original invocation continues.

P3 COMPLETED/FAILED/UNKNOWN after JOB remains admitted JOB work and is never rewritten as rejected.

No prompt text or rejection prose is stored in ignored/rejected ingress metadata.

## No queue / control responsiveness
P5.2 never holds the group routing lock across the full P3 turn. Therefore a second prompt is rejected immediately rather than waiting for idle, and SLEEP/ALL_SLEEP/STATUS controls remain processable while a turn is running.

The process-local P5.2 prompt marker is conservative coordination only; it is non-content, non-durable and not restored after restart. Durable P3 recovery/state remains authority after crash/restart.

## Work status
Accepted prompt creates/identifies a status projection with safe server/profile/model/effort and short job ID. Prefer editing this known message for progress/final first segment to reduce ambiguous creation.

## Response segmentation
Use conservative configured text limit; preserve Unicode/order and split by semantic boundaries where possible. Delivery durable per segment. Confirmed segment never recreated; ambiguous creation -> DELIVERY_UNKNOWN.

## Private panel
Private chat requires exact operator and private chat identity. Main panel shows safe mode/profile/model/reasoning/dialogue/app-server/diagnostic state. Buttons: account, model, reasoning, dialogue, status.

Profile chooser is blocked while live dialogue exists. Model/reasoning changes are blocked while turn runs and runtime-validated.

Dialogue buttons: NEW DIALOGUE, DELETE DIALOGUE, and STOP TURN only while running. NEW with no dialogue merely readies lazy creation; it never abandons a live thread.

## Destructive callbacks
Callback payload carries an opaque token, not trusted business parameters. Durable record binds operator/chat/action/entity/version/state/expiry and is atomically consumed before effect. Delete uses explicit second confirmation. Double/stale clicks produce no repeat effect.

## Approval UI
Blocking Codex approval shows only necessary sanitized context with explicit Allow/Deny buttons bound to exact request/job and expiry.

## Commands/menu
Tap-able `/panel`, `/status`, `/help` may exist as fallback. Normal operation must not require manual command typing.