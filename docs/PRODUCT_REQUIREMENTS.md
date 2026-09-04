# Product requirements — V1

## Goal
The authorized operator can use Telegram to select one server controller, hold a real multi-turn Codex dialogue on that server, diagnose/repair services, manage account/model/reasoning settings under deterministic rules, interrupt work, and hard-delete finished task context.

## Topology MUST
- One autonomous controller and one Telegram token per physical server.
- Common private supergroup for operations; private chat with each bot for settings.
- No mandatory central coordinator/database; one server failure must not disable another.
- Future server-N addition is configuration/deployment only, not a source-code fork.

## Group UX MUST
- Persistent tap-driven server keyboard; manual command typing is not normal workflow.
- Controls: activate server, all sleep, status.
- All healthy bots process the same human-originated activation message: target becomes ACTIVE, every non-target/unknown-target controller becomes SLEEP.
- Every process restart starts effective SLEEP and requires a fresh operator activation.
- Only ACTIVE may route ordinary authorized text to Codex.
- Reserved/control-looking text is never allowed to fall through as a Codex prompt.
- SLEEP prompts are terminally ignored and never replayed after activation.

## Private bot UX MUST
Button-led panels for server status, ACTIVE/SLEEP, account/profile, model, reasoning, dialogue, interrupt, hard delete, diagnostics and last sanitized error. Tap-able slash commands may exist only as fallback/menu entry.

## Dialogue MUST
- Real persisted Codex thread identity provides multi-turn context.
- V1 has at most one live dialogue per server.
- If no dialogue exists, first accepted prompt lazily creates a thread and executes the turn.
- Dialogue is bound to exactly one configured CODEX_HOME profile for its lifetime.
- Profile change is blocked while a live dialogue exists; context is not migrated across accounts.
- Model/reasoning may change only between turns and only after authenticated runtime validation for the bound profile.
- Every turn captures immutable server/profile/thread/model/effort/message IDs before Codex invocation.
- Exactly one turn runs at once. A second prompt while busy is rejected; no delayed prompt queue.
- Operator can explicitly interrupt a running turn.

## Model/profile discovery MUST
- Profiles are explicit config; filesystem scanning is diagnostics only.
- Model chooser uses authenticated app-server `model/list`; bundled debug catalog does not prove eligibility.
- Reasoning chooser exposes only efforts advertised for the selected runtime model.
- Missing/ambiguous model eligibility fails closed for selection.

## Approval MUST
- Privileged app-server approval requests are projected to Telegram with explicit allow/deny.
- Approval callbacks bind exact operator/chat/job/request/state/version/expiry through opaque one-time server-side action records.
- Expiry/restart/mismatch fails closed; production does not silently auto-approve privileged side effects by default.

## Delivery MUST
- Accepted work gets prompt acknowledgement/status with safe server/profile/model context.
- User-visible Codex agent messages/final report preserve order.
- Hidden chain-of-thought/raw reasoning and raw command-output floods are not forwarded.
- Telegram length limits are handled deterministically; confirmed chunks are never automatically duplicated.
- Ambiguous outbound message creation becomes DELIVERY_UNKNOWN, not blind resend.

## Hard delete MUST
1. block new turns;
2. if running, interrupt/reconcile first;
3. call installed Codex official hard delete (`thread/delete`) for the exact owning profile/thread;
4. require definitive success or explicit DELETE_UNKNOWN;
5. purge CodexControl-owned prompt/response/delivery payloads, temp jobs and no-longer-needed job/event data;
6. remove live binding only after confirmed delete;
7. retain only bounded non-content tombstone/idempotency metadata;
8. never perform ad-hoc surgery on shared Codex internal DBs without a future accepted ADR.

## Reliability MUST
- Durable Telegram update dedupe before external effects.
- Control-group message processing serialized by chat/message order.
- Durable state before thread/start, turn/start, approval and delete side effects.
- Restart recovery reconciles UNKNOWN rather than replaying side effects.
- SQLite/storage failure prevents new Codex execution.

## Security/operations MUST
- Exact single operator ID and exact chat IDs.
- Separate token per server; secrets outside Git, root-readable only.
- No generic `/shell` endpoint; server actions flow through Codex/approval boundary.
- No public controller/Codex listener.
- No conversation/raw-event/secret content in journald.
- Bounded temp storage/retention and explicit rollback before production.

## SHOULD
- Keep one healthy app-server child for the active dialogue profile; use short-lived children for other profile model discovery.
- Prefer editing a known Telegram status message for progress/final first segment.
- Expose safe DB/temp/disk/app-server diagnostics in private status.
- Keep a non-secret fleet manifest shared by all controllers.

## Out of scope V1
- Multiple human roles/operators.
- Cross-server shared runtime DB/coordinator.
- Cross-profile/cross-server context migration.
- Automatic credential copying/auth migration.
- Arbitrary public groups/users.
- Automatic remediation without operator prompt.
- Telegram media/file inputs until text path is accepted.
- Telegram chat-history deletion as part of Codex hard delete.
