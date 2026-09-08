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
A prompt must be unique, exact-operator, exact-control-supergroup, human-originated ordinary text, newer than the current durable control epoch, effective ACTIVE, locally unblocked, P3-valid and durably admitted by accepted P3.

SLEEP -> terminal content-free `IGNORED_SLEEP`, no P3.

Different prompt while a local P3 prompt is still in flight -> BUSY + terminal content-free `IGNORED_REJECTED`, not queue.

Accepted P3 BUSY/BLOCKED before JOB -> terminal content-free `IGNORED_REJECTED` before successful P5.2 return.

A replay of a durable SLEEP/rejected/JOB/control/unauthorized update returns duplicate authority and never changes classification.

The same update redelivered while its original P5.2 P3 invocation is still locally in flight is an in-flight duplicate with zero redispatch; the original invocation continues.

P3 COMPLETED/FAILED/UNKNOWN after JOB remains admitted JOB work and is never rewritten as rejected. No prompt text or rejection prose is stored in ignored/rejected ingress metadata.

## No queue / control responsiveness
P5.2 never holds the group routing lock across the full P3 turn. A second prompt is rejected immediately rather than waiting for idle, and SLEEP/ALL_SLEEP/STATUS controls remain processable while a turn is running.

The process-local P5.2 prompt marker is conservative coordination only; it is non-content, non-durable and not restored after restart. Durable P3 recovery/state remains authority after crash/restart.

## Fleet STATUS / manifest mismatch visibility
Exact `📊 СТАТУС` remains a read-only group control. Each healthy controller projects its own accepted P5.1/P5.2 STATUS snapshot through accepted P5.3.

The projection exposes only non-secret local fleet metadata: local display/server ID, ACTIVE/SLEEP, fleet version, member count, complete ordered-manifest SHA-256 identity, boot generation and last control epoch. The renderer shows the first 16 hex characters; the full hash remains diagnostic only and never grants routing authority.

There is no peer compatibility RPC or local distributed MATCH decision. Different fleet versions/fingerprints make mismatch visible to the operator. Unknown reserved `🖥 ...` activation still makes an old controller SLEEP, never prompt.

Telegram polling backlog/offset freshness remains later P9/P11 live acceptance.

## P6.1 final-response delivery
P6.1 delivers only accepted successful P3 user-visible OUTPUT, or exact fallback `✅ Выполнено` when successful work has no OUTPUT. Raw reasoning, command-event floods, stderr, environment and raw protocol events are never delivered.

Configured text limit is 512..4096 Unicode code points. Segmentation preserves source exactly; preferred cuts are paragraph, line, ASCII space, then hard cut. If the preferred pass exceeds P2.4b's 4096-plan bound, exact hard-cut fallback is used; if even that exceeds 4096, delivery fails closed.

Before any final response effect, P6.1 creates transient DISPLAY chunks and immutable accepted P2.4b delivery plan. Each segment is durably `SENDING/attempt1` before exactly one CREATE/EDIT attempt. CONFIRMED is never recreated; UNKNOWN/FAILED is never automatically retried. Existing durable SENDING recovers with zero new effect to `DELIVERY_UNKNOWN/TELEGRAM_RECOVERY_AMBIGUOUS`.

## P6.3 work-status hint
P6.3 owns a one-attempt, process-local work-status hint for a newly admitted live turn. It is intentionally not a durable outbox.

Exact running text:

```text
⏳ Выполняю запрос
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

Only bounded non-secret durable job metadata is included. No prompt, output, thread/turn/job ID or raw error appears.

P6.3 performs exactly one plain CREATE attempt. CONFIRMED stores the returned message ID only in process memory as a possible final-delivery hint. FAILED/UNKNOWN/malformed/exception means no hint and no retry; the Codex turn continues.

If the process dies before P6.1 commits a final plan, this message ID is forgotten and no acknowledgement is replayed. A stale `⏳` message may remain in Telegram. Startup successful delivery therefore uses CREATE. Only when accepted P6.1 later commits the confirmed hint into the immutable first-segment EDIT plan does that target become durable P2.4b authority.

For a live P3 FAILED result, P6.3 makes at most one safe status attempt using:

```text
❌ Выполнение завершилось с ошибкой
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

For live P3 UNKNOWN:

```text
⚠️ Результат выполнения не подтверждён
Сервер: <server_id>
Профиль: <profile_id>
Модель: <model_id>
Рассуждение: <reasoning_effort>
```

If the live confirmed work-status ID exists, use one EDIT; otherwise one CREATE. There is no retry and no startup replay. These status effects never alter the already-durable P3 terminal job state.

## Private panel
Private chat requires exact operator and private chat identity. Main panel shows safe mode/profile/model/reasoning/dialogue/app-server/diagnostic state. Buttons cover account, model, reasoning, dialogue and status. Profile changes are blocked with live dialogue; model/reasoning changes are only between turns. STOP TURN and hard-delete remain explicit private authority.

## Destructive callbacks
Callback payload carries an opaque token, not trusted business parameters. Durable record binds operator/chat/action/entity/version/state/expiry and is atomically consumed before effect. Delete uses explicit second confirmation. Double/stale clicks produce no repeat effect.

## Approval UI and P6.2 live decision bridge
A blocking Codex approval exposes only P1.7's bounded/sanitized operator context. P6.2 publishes durable P2.4b PENDING before waiting. Safe details may exist only as bounded transient APPROVAL payload; absent safe details keeps accepted P4.3 deny-only.

P4.3 owns private Allow/Deny UI and atomic durable callback decision. It sends no Codex response itself.

P6.2 composition is:

1. exact current P1.7 request is already owned by the current client;
2. P6.2 binds exact running job/profile/thread/Codex turn;
3. wake waiter registers before PENDING publication;
4. PENDING commits with exact 900000 ms deadline;
5. P4.3 Allow/Deny or P6.2 EXPIRED/CANCELLED terminalizer wins durable state;
6. P6.3 private composition pulses `ApprovalDecisionSignal.notify()` after relevant private callback handling;
7. waiter re-reads exact durable record;
8. APPROVED -> ALLOW; DENIED/EXPIRED/CANCELLED -> DENY;
9. accepted P1.7 makes exactly one method-specific response attempt.

The signal is wake-only. It contains no decision and cannot grant ALLOW. Duplicate/sibling clicks cannot send a second response.

Ordinary outer cancellation of an already-owned P6.2 response is shielded. Exact Codex protocol terminal yields RESPONSE_UNKNOWN/no retry and best-effort CANCELLED of still-PENDING state.

Durable approval metadata is never old wire-response authority. Restart loses the exact old `InboundServerRequest`; a new client cannot reconstruct/respond from saved wire ID or decision metadata.

## P6.3 turn/approval concurrency
P6.3 captures the exact runtime object used by accepted P1.6 `turn/start`; it does not reacquire later and guess runtime identity.

While the same turn terminal is pending, P6.3 concurrently services at most one exact P1.7 server request at a time through accepted P6.2. Sequential approvals are allowed; there is no delayed approval queue.

If the turn terminal wins while no approval request has been transferred, the pending request-get is cancelled/joined and the terminal stands. If an exact owned request is nevertheless captured in the cancellation race, it is answered once DENY, the exact profile runtime is shut down, and the turn is projected UNKNOWN.

If the turn terminal wins while a live P6.2 approval is already waiting, P6.3 does not cancel it or guess DENY. It shuts down the exact captured profile runtime so accepted P1.7/P6.2 resolves `RESPONSE_UNKNOWN` and best-effort CANCELLED; the turn is projected UNKNOWN.

Every turn/request/approval helper is owned and joined. Interrupt delegates to the same accepted P1.6 lifecycle and exact binding; P3.4 remains durable interrupt authority.

## P6.3 group/private final composition
P6.3 wraps accepted P5 group routing and P4 private management; it does not replace their normalization/auth/dedupe rules.

- P5 PROMPT + P3 COMPLETED -> accepted P6.1 exactly once, using live status ID only as initial hint.
- P5 PROMPT + P3 FAILED/UNKNOWN -> no P6.1; one live non-success status attempt only.
- P5 DUPLICATE -> no new acknowledgement, P3 or final-delivery effect.
- P5 STATUS -> accepted P5.3 pure status projection/renderer only.
- relevant P4 approval callback results (`APPROVED`, `DENIED`, `EXPIRED`, `STALE`, `ALREADY_USED`) pulse the shared wake signal once; callback result itself is not wire decision authority.

Outer group-handler cancellation cannot create a second P3, approval response, acknowledgement or final-delivery effect.

## P6.3 startup recovery boundary
Before later live polling/ingestion, P6.3 must run accepted P3.5 startup recovery, clean leftover pending approvals only after their job is no longer CODEX_RUNNING, then process oldest successful delivery candidates (`CODEX_COMPLETED|DELIVERY_PENDING|DELIVERING`) through accepted P6.1 with no status hint.

At most 256 candidates are processed per explicit recovery pass. Remaining backlog returns `LIMIT_REACHED`; P6.3 creates no background worker. Live ingestion must not begin until an explicit pass returns READY.

Startup never recreates the early work-status message. `CODEX_COMPLETED` therefore plans all CREATE; stranded SENDING performs zero resend and becomes DELIVERY_UNKNOWN; confirmed-prefix delivery resumes only at first pending.

P6.3 remains fake/application only. Live Telegram HTTP/polling/webhook, offsets/backlog, bot tokens, deployment and real Codex acceptance are later milestones.

## Commands/menu
Tap-able `/panel`, `/status`, `/help` may exist as fallback. Normal operation must not require manual command typing.
