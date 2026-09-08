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

## Fleet STATUS / manifest mismatch visibility
Exact `📊 СТАТУС` remains a read-only group control. Each healthy controller projects its own accepted P5.1/P5.2 STATUS snapshot and may later send the pure P5.3 rendered text through the Telegram transport layer.

The P5.3 status projection exposes only non-secret local fleet metadata:

- local display name/server ID;
- effective ACTIVE/SLEEP;
- exact configured `fleet_version`;
- member count;
- deterministic SHA-256 identity of the complete ordered fleet manifest;
- boot generation;
- last applied control epoch.

The renderer displays the first 16 hexadecimal characters of the manifest identity while the full 64-character value remains available in the local projection. The fingerprint is diagnostic only and never grants routing/effect authority.

There is no peer compatibility RPC or local distributed MATCH decision. Different `fleet_version` values or different manifest fingerprints in the bots' STATUS responses make rollout/configuration mismatch visible to the operator.

During manifest mismatch the reserved activation namespace remains the safety rule: a controller that does not know a newly added `🖥 ...` label must still parse it as ACTIVATE with unknown target and become/remain SLEEP, never treat it as a prompt.

P5 fake acceptance proves local restart SLEEP/no restored prompt queue. Telegram polling backlog/offset freshness is a later live P9/P11 transport acceptance concern and is not inferred from application-only STATUS data.

## Work status / acknowledgement boundary
An accepted prompt should eventually create or identify a safe Telegram status message containing bounded server/profile/model/effort context. P6.3 owns that acknowledgement/progress orchestration.

P6.1 does not create acknowledgement/status messages. If P6.3 or another accepted caller already knows a status message ID, P6.1 may bind the **first final response segment** as EDIT to that exact message. Every later response segment is CREATE. If no status message ID is supplied, every final response segment is CREATE.

Once a durable delivery plan exists, that plan is sole authority; a later request cannot rewrite CREATE/EDIT targets.

## P6.1 response segmentation and durable delivery
P6.1 delivers only accepted successful P3 user-visible OUTPUT content, or exact fallback `✅ Выполнено` when successful work has no OUTPUT payload. It does not deliver raw reasoning, raw command-event floods, stderr, environment or raw Codex protocol events.

Configured P6.1 text limit is 512..4096 Unicode code points. Segmentation preserves the source exactly. Preferred cuts are paragraph (`\n\n`), then line (`\n`), then ASCII space, then hard cut. If that semantic pass would exceed accepted P2.4b's 4096-segment plan bound, P6.1 deterministically falls back to exact hard chunks; if even hard chunks would exceed 4096, it fails closed. No Markdown/HTML parse mode is used.

Before any final Telegram message effect, P6.1 creates transient DISPLAY chunks and an immutable accepted P2.4b delivery plan. For each segment:

1. durable P2.4b `claim_next` commits that exact segment as `SENDING/attempt1` before the effect;
2. exactly one application `TelegramDeliveryPort` CREATE or EDIT attempt is owned;
3. P2.4b `finish_sending` records CONFIRMED, UNKNOWN or FAILED.

Confirmed segments are never recreated. UNKNOWN/FAILED are not automatically retried.

If a later delivery invocation finds an already durable SENDING segment, it sends **nothing** for that segment and converts it to `DELIVERY_UNKNOWN` with sanitized recovery-ambiguity authority. A confirmed prefix followed by untouched PENDING segments may safely resume from the first pending segment.

A storage failure after a possible Telegram effect never causes an immediate resend. The durable SENDING record remains the fail-closed evidence and a later invocation follows the same recovery-to-UNKNOWN rule.

P6.1 is application/fake only; no actual Telegram HTTP implementation is accepted in this slice.

## Private panel
Private chat requires exact operator and private chat identity. Main panel shows safe mode/profile/model/reasoning/dialogue/app-server/diagnostic state. Buttons: account, model, reasoning, dialogue, status.

Profile chooser is blocked while live dialogue exists. Model/reasoning changes are blocked while turn runs and runtime-validated.

Dialogue buttons: NEW DIALOGUE, DELETE DIALOGUE, and STOP TURN only while running. NEW with no dialogue merely readies lazy creation; it never abandons a live thread.

## Destructive callbacks
Callback payload carries an opaque token, not trusted business parameters. Durable record binds operator/chat/action/entity/version/state/expiry and is atomically consumed before effect. Delete uses explicit second confirmation. Double/stale clicks produce no repeat effect.

## Approval UI and P6.2 live decision bridge
A blocking Codex approval exposes only P1.7's bounded/sanitized operator context. P6.2 publishes a durable P2.4b PENDING approval before waiting for the operator. If safe context exists it may be stored only as a bounded transient APPROVAL payload; if no safe detail payload exists, accepted P4.3 remains deny-only.

P4.3 continues to own the private Allow/Deny UI and its atomic durable callback decision. P4.3 itself still sends no Codex response.

P6.2 composition is:

1. exact current P1.7 server request is already owned by the current Codex protocol client;
2. P6.2 binds it to the exact running job/profile/thread/Codex turn;
3. a content-free process-local decision waiter is registered before PENDING publication;
4. P2.4b PENDING approval commits with an exact 900000 ms deadline;
5. P4.3 Allow/Deny callback atomically commits APPROVED/DENIED, or P6.2 terminalizes due/lost ownership to EXPIRED/CANCELLED;
6. composition pulses `ApprovalDecisionSignal.notify()` after private callback handling;
7. the waiter re-reads the exact durable ApprovalRecord;
8. APPROVED -> P1.7 ALLOW; DENIED/EXPIRED/CANCELLED -> P1.7 DENY;
9. accepted P1.7 performs exactly one method-specific response attempt.

The signal is wake-only. It contains no approval decision and `notify()` can never grant ALLOW. A notification before a durable decision only wakes a waiter that sees PENDING and keeps waiting.

Expiry and Allow/Deny callbacks race through the same durable approval state; one terminal state wins. Duplicate/sibling clicks cannot send a second Codex response.

Once P6.2 owns an exact server request, ordinary outer caller cancellation is shielded from the P1.7 bridge so a durable Allow cannot be replaced by P1.7's cancellation-path Deny. If the exact Codex protocol becomes terminal, no safe response can be sent; P6.2 best-effort marks a still-PENDING approval CANCELLED and P1.7 returns RESPONSE_UNKNOWN/no retry.

Durable approval metadata is **not** wire-response authority. After process/client restart the old exact `InboundServerRequest` identity is gone permanently. A new client must never reconstruct or answer the old request from a saved wire ID or APPROVED/DENIED record. P6.3 startup recovery may clean up the old job/approval state, but old wire response replay is forbidden.

P6.2 remains application/fake only. Live Telegram HTTP/polling/webhook delivery and live Codex acceptance remain later milestones.

## Commands/menu
Tap-able `/panel`, `/status`, `/help` may exist as fallback. Normal operation must not require manual command typing.
