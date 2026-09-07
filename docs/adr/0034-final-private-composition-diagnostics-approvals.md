# ADR-0034 — Final private management composition, diagnostics and approval UI

Status: Accepted
Date: 2026-09-07

## Context

P4.1 is architect-accepted at `5a7db46c6e06662c379149c454c06003d48feb30` and owns private Telegram normalization/authentication, durable private-menu CONTROL dedupe, opaque one-time callbacks, and settings/profile/model/reasoning UI over P3.3.

P4.2 is architect-accepted at `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39` and owns separate private dialogue status, exact P3.4 interrupt delegation, mandatory two-step P3.5 hard delete, read-only callback ownership peek, and context-wide destructive-confirm cancellation.

P4.3 completes the fake/application private-management boundary by composing those accepted surfaces behind one final private facade, adding content-safe diagnostics/last-sanitized-error projection, and adding private approval projection/callback decisions over accepted P2.4b. Live Telegram transport, group routing, delivery and full live approval orchestration remain later roadmap slices.

## Non-goals

P4.3 does not:

- add Telegram HTTP/polling/webhook/token loading or any network effect;
- change accepted P4.1 `PrivateCommand`, `PrivatePanelSection`, settings action values, settings mutation semantics or `PrivateSettingsManagementService` public methods;
- change accepted P4.2 public enums/actions, interrupt/delete semantics or destructive-confirm authority;
- implement private ACTIVE/SLEEP mutation; effective mode is read-only and group/fleet activation remains P5;
- create a P1.7 server-request approval from Codex, own a process-local approval waiter/Future, send the external P1.7 approval response, or claim wire-response success; those full local orchestration duties remain P6;
- implement response delivery/outbox/send/edit;
- change schema/DDL;
- expose raw exception bodies, fingerprints, callback tokens/hashes, thread/job/turn/wire-request IDs, CODEX_HOME, prompt/output or hidden reasoning;
- start P5+.

## Final private facade

Add `PrivateControlService` with exactly:

- `handle_command(request: PrivateCommandRequest)`;
- `handle_callback(request: PrivateCallbackRequest)`;
- `project_approval(request: PrivateApprovalProjectionRequest)`.

It consumes only the accepted normalized P4.1 request records; raw Telegram JSON never enters this service.

Constructor receives one coherent configuration for the accepted sub-services: storage, server ID/display name, operator user ID, configured profiles, model catalog, accepted interrupt service, accepted delete service, plus optional read-only mode provider, diagnostics provider, clock and token factory. The facade constructs/uses accepted P4.1 and P4.2 services with the same configuration; it does not inspect their private fields or reproduce their business mutation logic.

## Final public result

`PrivateControlStatus` exactly:

`RENDERED | UPDATED | NO_CHANGE | CONFIRM_REQUIRED | INTERRUPTED | DELETED | APPROVED | DENIED | BLOCKED | STALE | UNKNOWN | FAILED | EXPIRED | ALREADY_USED | DUPLICATE | UNAUTHORIZED | UNSUPPORTED`.

`PrivateControlReason` exactly:

`CALLBACK_NOT_FOUND | STALE_ACTION | ACTION_UNAVAILABLE | SETTINGS_MISSING | PROFILE_NOT_CONFIGURED | PROFILE_LOCKED | DIALOGUE_NOT_IDLE | MODEL_NOT_CONFIGURED | MODEL_UNAVAILABLE | REASONING_EFFORT_UNSUPPORTED | CATALOG_UNAVAILABLE | NO_DIALOGUE | DIALOGUE_NOT_RUNNING | JOB_NOT_RUNNING | ACTIVE_BINDING_UNAVAILABLE | INTERRUPT_IN_PROGRESS | INTERRUPT_UNRESOLVED | DIALOGUE_NOT_READY | DELETE_NOT_READY | DELETE_IN_PROGRESS | DELETE_UNKNOWN | NO_PENDING_APPROVAL | DIAGNOSTICS_UNAVAILABLE`.

`PrivateControlErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

Add finite content-free `PrivateControlError` and frozen repr-safe `PrivateControlResult(status, panel, reason)`.

`panel` is only one of:

- accepted `PrivateAdminPanel` from P4.1;
- accepted `PrivateDialoguePanel` from P4.2;
- new P4.3 `PrivateControlPanel`;
- `None`.

Impossible delegated status/reason/panel shapes are `INVARIANT`, not silently normalized.

## P4.3 panel model and renderer

`PrivateControlPanelSection` exactly:

`ROOT | DIAGNOSTICS | APPROVAL`.

Add frozen `PrivateControlPanel(section, text, rows)` using accepted `PrivateAdminButton` rows. Generic repr must redact panel text and callback data; approval display content is operator-visible but must never become generic log/repr content.

Add pure `TelegramPrivateControlRenderer.render(panel)`. It accepts only exact `PrivateAdminPanel`, `PrivateDialoguePanel` or `PrivateControlPanel` and returns the same minimal plain Telegram-like structure used by accepted P4.1/P4.2: `text` plus `reply_markup.inline_keyboard`. No parse mode, URL, web app, send/edit or network action.

Reuse P4.1 bounds unless narrower below:

- callback TTL: `900000` ms;
- panel text max: `3500` chars;
- button label max: `64` chars;
- approval details max: `P43_APPROVAL_DETAILS_MAX_CHARS = 2400`.

## Exact private authorization

Final command/callback authorization remains exactly one configured operator in exact private chat: `user_id == operator_user_id` and `chat_id == operator_user_id`.

For MENU commands the facade mirrors accepted P4.1 behavior: wrong principal uses accepted no-content `IGNORED_UNAUTHORIZED`; authorized unsupported text never becomes a JOB/prompt; fresh MENU uses `PrivateManagementRepository.claim_private_command` and duplicate update IDs return `DUPLICATE` with no new panel/callback authority.

`PrivateCommand.SETTINGS` delegates unchanged to accepted P4.1 `handle_command`, preserving its own CONTROL dedupe and exact result semantics. `PrivateCommand.MENU` renders the new final ROOT. `command=None` is `UNSUPPORTED`.

Private mode mutation is forbidden. Mode may only be displayed through the same optional exact `ControllerMode` provider semantics accepted by P4.2; missing provider displays `UNAVAILABLE`, wrong type/exception is `INVARIANT`.

## Final ROOT authority

The final ROOT is navigation-only. It may display safe server identity, read-only effective mode, configured profile/model/reasoning, current canonical dialogue state and pending-approval count. It never exposes raw thread/job/turn IDs or error fingerprints.

Root construction uses accepted authorities:

- `ControllerRuntimeRepository.get()` for exact current `boot_generation`; missing controller runtime after application boot is `INVARIANT`;
- `ApplicationRecoveryRepository.inspect()` for canonical dialogue/active-job state;
- `SettingsSelectionService.get_view(refresh=False)` configured identically to P4.1 for settings/dialogue/profile coherence; catalog unavailability is a safe display state, not a root failure;
- read-only pending-approval lookup described below.

Root callbacks are created in one atomic P4-owned callback batch with one validated clock and no collision retry. No fabricated settings/dialogue/controller generation is allowed.

Root buttons:

- `Settings` only when a settings row exists;
- `Dialogue` always;
- `Diagnostics` always;
- `Approvals` only when the current canonical active `CODEX_RUNNING` job has at least one PENDING approval;
- `Refresh` always.

There is no private ACTIVE/SLEEP mutation button.

## P4.1-owned Settings navigation from final ROOT

The final `Settings` button is deliberately owned by accepted P4.1 rather than a new P4.3 mutation path.

Its durable callback row is exact P4.1 shape:

- action `OPEN_ROOT`;
- subject_type `panel`;
- subject_id `0`;
- expected_version = exact current `settings.version` from the P3.3 selection view;
- expected_state = exact current P4.1 `NO_DIALOGUE` or `DialogueState.value` from that same view;
- exact operator user/chat.

The Telegram callback remains opaque `cc1:<token>`. On click, the final dispatcher peeks the row, recognizes a P4.1 action and delegates the unchanged `PrivateCallbackRequest` to accepted P4.1, which performs its own one-time claim and fresh validation. P4.3 never calls P3.3 selection methods directly.

If settings are absent, no `OPEN_ROOT` callback is created; there is no fabricated settings version.

## P4.3 navigation callbacks

P4.3 owns exactly these navigation action strings:

- `P43_REFRESH_ROOT`;
- `P43_OPEN_DIALOGUE`;
- `P43_OPEN_DIAGNOSTICS`;
- `P43_OPEN_APPROVALS`.

Every P43 row has:

- subject_type exactly `p43_nav`;
- expected_version = exact current `controller_runtime.boot_generation`;
- expected_state exactly `PRIVATE_ROOT`;
- exact operator user/chat;
- opaque callback data and hash-only durable token.

Subject IDs are lower-case SHA-256 fingerprints of the navigation target:

- REFRESH_ROOT: `sha256("root" + NUL + server_id + NUL + decimal boot_generation)`;
- OPEN_DIALOGUE: `sha256("dialogue" + NUL + dialogue_id_or_dash + NUL + dialogue_version_or_dash)`;
- OPEN_DIAGNOSTICS: `sha256("diagnostics" + NUL + server_id + NUL + decimal boot_generation)`;
- OPEN_APPROVALS: `sha256("approval" + NUL + target_approval_id)`.

Literal `-` is used for missing dialogue ID/version in the dialogue navigation fingerprint.

P43 callback handling generic-claims only after ownership dispatch, then re-reads controller runtime and requires the same boot generation. REFRESH/DIAGNOSTICS fingerprints are recomputed. OPEN_DIALOGUE re-inspects canonical dialogue and requires the same dialogue fingerprint before calling accepted P4.2 `open_status`. OPEN_APPROVALS resolves the fingerprint against the current deterministic pending approvals for the exact current CODEX_RUNNING job and requires exactly one match. Mismatch is `STALE / STALE_ACTION` with zero business effect.

## Final callback dispatcher — non-consuming ownership first

P4.1, P4.2, P4.3 and approval decisions deliberately share the same `cc1:<token>` grammar/table. The final facade MUST call accepted `PrivateManagementRepository.peek_callback(hash)` before any one-time claim.

Exact order:

1. validate `PrivateCallbackRequest` and exact operator/private chat;
2. wrong principal -> `UNAUTHORIZED`, zero hash/peek/claim;
3. validate exact 32-char token and SHA-256 it;
4. read-only `peek_callback(hash)`;
5. missing -> `STALE / CALLBACK_NOT_FOUND`;
6. exact P4.1 action family (`OPEN_ROOT`, `OPEN_PROFILES`, `OPEN_MODELS`, `OPEN_REASONING`, `SELECT_PROFILE`, `SELECT_MODEL`, `SELECT_REASONING`) -> delegate unchanged request to accepted P4.1; P4.3 does not claim first;
7. exact P4.2 action family (`P42_REFRESH`, `P42_INTERRUPT`, `P42_BEGIN_DELETE`, `P42_CONFIRM_DELETE`, `P42_CANCEL_DELETE`) -> delegate unchanged request to accepted P4.2; P4.3 does not claim first;
8. exact approval actions (`approval_allow`, `approval_deny`) -> call `ApprovalRepository.claim_callback` directly; generic P2.3 claim is forbidden because P2.4b atomically owns callback consumption + approval subject mutation;
9. exact P43 action family -> accepted generic `CallbackActionRepository.claim`, then P43 navigation validation;
10. any other action -> `BLOCKED / ACTION_UNAVAILABLE` and DO NOT claim/consume.

A peek/claim race is safe: the owning claim remains authoritative and may return expired/already-used/unauthorized/stale.

## Approval read authority

Add one read-only method to accepted P2.4b storage:

`ApprovalRepository.list_pending_for_job(job_id) -> tuple[ApprovalRecord, ...]`.

It validates the job ID, requires the canonical job to exist, selects only `PENDING` approvals for that exact job, materializes every row through existing P2.4b authority, orders deterministically by `created_at_ms, approval_id`, and performs zero clock/mutation. Corrupt rows/ownership are `INVARIANT`.

P4.3 never scans arbitrary approvals to infer a live job. It first obtains the exact active job from canonical `ApplicationRecoveryRepository.inspect()` and only then asks for pending approvals for that job.

## Approval projection API

Add frozen repr-redacted:

`PrivateApprovalProjectionRequest(approval_id)`.

`PrivateControlService.project_approval(request)` is a local application projection surface intended to be reusable by later P6 when a pending approval needs a Telegram panel. P4.3 itself does not create the pending approval and does not send any external Codex approval response.

Projection requires:

- exact pending approval exists;
- canonical dialogue `TURN_RUNNING`;
- exactly one active job in `CODEX_RUNNING`;
- approval belongs to that exact job/profile;
- approval is not already due at projection clock.

Failure to find/currently own it is `BLOCKED / NO_PENDING_APPROVAL` or `STALE` where an already-issued P43 navigation target drifted; persisted corruption is `INVARIANT`.

## Approval display content

If `display_payload_id` is non-NULL, P4.3 reads it through accepted `TransientPayloadRepository.get()` and requires exact:

- kind `APPROVAL`;
- job ID = exact current approval job;
- dialogue ID = exact current live dialogue;
- canonical payload hash/length from accepted materializer.

Missing referenced payload or ownership/kind mismatch is `INVARIANT` because accepted retention must preserve a PENDING approval payload.

Display bytes must decode strict UTF-8. UI sanitization normalizes controls/whitespace to plain text. `Allow` is permitted only if the complete sanitized details are non-empty and fit entirely within `P43_APPROVAL_DETAILS_MAX_CHARS = 2400` without truncation. Invalid UTF-8, empty details, absent optional display payload, or details exceeding the complete-display budget are treated as `details unavailable`: the panel may still render a safe approval kind/profile notice and a `Deny` button, but MUST NOT render `Allow`.

P4.3 must never approve based on truncated/incomplete details.

Approval panel generic repr redacts its text, so commands/paths shown to the authorized operator are not emitted by generic logging.

## Approval callback creation

For one exact pending approval projection, P4.3 creates:

- `approval_allow` only when complete details are available;
- `approval_deny` always while the approval is current and not due;
- optional P43 previous/next pending-approval navigation buttons;
- P43 back-to-root navigation.

Approval decision callback rows use exact accepted P2.4b shape:

- subject_type `approval`;
- subject_id exact approval ID (server-side only, never Telegram data/UI text);
- expected_version exact current CODEX_RUNNING job version;
- expected_state `PENDING`;
- exact operator user/chat.

One approval panel callback batch uses one validated clock. Expiry is exactly `min(now + 900000, approval.expires_at_ms)`; if it is not strictly later than `now`, no decision authority is created and projection is blocked as no-current-pending approval. Hash collision is `INVARIANT`, no retry, no partial batch.

## Approval decision mapping

The final dispatcher routes approval actions directly to accepted `ApprovalRepository.claim_callback`.

Mapping:

- `APPROVED` -> `PrivateControlStatus.APPROVED`;
- `DENIED` -> `DENIED`;
- `NOT_FOUND` -> `STALE / CALLBACK_NOT_FOUND`;
- `UNAUTHORIZED` -> `UNAUTHORIZED`;
- `EXPIRED` -> `EXPIRED`;
- `ALREADY_CONSUMED` -> `ALREADY_USED`;
- `STALE` -> `STALE / STALE_ACTION`.

Only APPROVED/DENIED may return an `ApprovalRecord`; its state must exactly match the returned status and its action direction must match the durable callback action. Every other status must return no approval record. Impossible combinations are `INVARIANT`.

Sibling approval callbacks are allowed to remain durable; after one decision, accepted P2.4b makes another authorized click stale and consumes it without a second approval state transition.

## Approval/P1.7/P6 boundary

P4.3 approval `APPROVED`/`DENIED` means only that the operator decision was atomically durably recorded by P2.4b. It does NOT mean a P1.7 response was sent or confirmed.

P4.3 creates no process-local waiter/Future and does not call `CodexApprovalBridge`, `AsyncApprovalOperator`, protocol client or any external approval-response method. Later P6 full local orchestration must own: receiving/normalizing a live P1.7 approval request, creating the pending approval/display payload, coordinating the live request with the durable operator decision, sending the exact P1.7 response once under accepted P1.7 semantics, and fail-closed restart/cancellation behavior. A stale approval after recovery remains protected by accepted P2.4b job/dialogue/version checks.

## Diagnostics

Add `ErrorFingerprintRepository.latest() -> ErrorFingerprintRecord | None` as a read-only zero-clock operation. It selects the newest canonical error by deterministic order:

`last_seen_at_ms DESC, fingerprint_sha256 ASC`

and materializes through existing ADR-0023 authority. No list of raw errors is added.

P4.3 diagnostics defines:

`PrivateDiagnosticState` exactly `OK | DEGRADED | UNAVAILABLE`.

Add frozen `PrivateDiagnosticsSnapshot(storage_state, codex_state, database_bytes, transient_payload_bytes, filesystem_free_bytes)`.

Byte fields are nullable exact non-bool integers in signed-64 nonnegative range. A synchronous optional `diagnostics_provider` may return only this exact record. Missing provider projects UNAVAILABLE values; provider exception/wrong type/invalid field is `INVARIANT`. P4.3 does not implement OS/network probing in this slice.

Diagnostics panel may show only:

- server ID/display name;
- read-only mode;
- diagnostic states and byte counts;
- latest sanitized `error_class`;
- error count;
- first/last timestamps;
- error scope label `controller`, `dialogue`, `job`, or `dialogue+job` derived only from whether references exist.

Never display the fingerprint SHA-256 or actual dialogue/job IDs. No raw exception/traceback/stderr/environment/path is available to this UI.

`P43_OPEN_DIAGNOSTICS` and a diagnostics refresh render current data; a back button returns through a fresh P43 root navigation callback.

## Delegated P4.1/P4.2 result mapping

The final facade maps accepted P4.1/P4.2 results into `PrivateControlStatus/Reason` without re-executing their effects. It validates their canonical finite status/reason/panel relations and maps errors:

- accepted STORAGE -> P4.3 STORAGE;
- caller INVALID_ARGUMENT from public P4.3 input -> INVALID_ARGUMENT;
- impossible internal INVALID_ARGUMENT/INVARIANT from P4.3-created internal requests -> INVARIANT.

After accepted P4.1 settings mutation, P4.2 interrupt or P4.2 delete, the facade does not require an additional root render; a later render failure must not disguise an already committed mutation/effect.

## P43 callback batch authority

P43 callback creation reuses accepted `PrivateManagementRepository.create_callback_batch`: one clock per batch, exact 900000 ms default TTL, canonical signed-64 overflow check, hash-only durable tokens, all-or-none insertion and no collision retry. Mixed ROOT/APPROVAL batches may contain accepted P4.1/P2.4b-owned action rows plus P43 navigation rows, each with its own exact expected version/state/subject authority.

## Final fake P4 acceptance

P4.3 must add a final fake/application P4 acceptance test that proves, at minimum:

1. normalized authorized `/menu` -> one durable CONTROL ingress and final ROOT, no JOB/mode mutation;
2. duplicate menu update -> no second callback authority;
3. final ROOT Settings token is exact P4.1 `OPEN_ROOT`, dispatcher delegates without pre-claim and accepted P4.1 panel/settings callback still works;
4. Dialogue navigation delegates to accepted P4.2 and does not consume P4.1/approval tokens;
5. diagnostics shows only safe provider data and latest sanitized error class/count/scope, never fingerprint/entity IDs/raw exception;
6. canonical CODEX_RUNNING job + pending approval + complete APPROVAL display -> approval panel with Allow/Deny, exact P2.4b callback bindings and atomic decision;
7. no/invalid/oversized approval details -> Deny only, never Allow;
8. wrong approval principal is non-consuming; replay after one decision cannot cause a second decision;
9. unknown callback action is not consumed;
10. P4.2 two-step hard-delete/cancel authority remains intact through final dispatch (focused P4.2 regressions remain authoritative; fake final acceptance need not perform a new external delete unless useful);
11. restart/boot-generation drift makes P43 navigation stale without mutating business state;
12. no private ACTIVE, group routing, delivery or external approval response exists;
13. no real Telegram/network/Codex/production effect;
14. accepted P4.2/P4.1/P3/P2/P1 regressions and frozen DDL remain unchanged.

P4.3 acceptance completes P4 only at the fake/application private-management boundary. Live Telegram transport/UX acceptance remains later roadmap authority.

## Out of scope after P4.3

P5 remains group/fleet activation and prompt routing. P6 remains response delivery plus full local orchestration, including live approval-request creation/wait/response coordination. P7 remains real Codex isolated acceptance/storage-erasure measurement. P8+ remain deployment/live fleet work.
