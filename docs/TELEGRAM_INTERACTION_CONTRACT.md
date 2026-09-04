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
Configured control-chat messages are processed sequentially. Do not enable handler concurrency that can run a prompt ahead of an earlier activation. Store last accepted control epoch/message ID; stale controls no-op.

## Ordinary prompt eligibility
Must be unique update, exact operator, exact group, user-originated ordinary text, not command/control/service content, effective ACTIVE, state permits turn, no running turn, healthy durable storage. SLEEP -> silent no-content ignored disposition. ACTIVE+busy -> BUSY response, not queue.

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
