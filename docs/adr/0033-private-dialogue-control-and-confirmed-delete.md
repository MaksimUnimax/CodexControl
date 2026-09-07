# ADR-0033 — Private dialogue status, interrupt and confirmed hard delete

Status: Accepted
Date: 2026-09-07

## Context

P4.1 is architect-accepted at `5a7db46c6e06662c379149c454c06003d48feb30`. It froze the exact private Telegram normalization/settings surface under ADR-0032. P4.2 adds private server/dialogue control over accepted P3.4/P3.5 without changing the accepted P4.1 exact enums or callback action vocabulary.

Live Telegram transport remains out of scope. P4.2 is a fake/application layer that consumes normalized trusted principal data and the accepted durable `callback_actions` table. P4.3 will compose the final private root/menu and approval/diagnostic surfaces.

## Non-goals

P4.2 does not:

- add Telegram HTTP/polling/webhook/token loading;
- change `PrivateCommand`, `PrivatePanelSection`, P4.1 action values or P4.1 settings semantics;
- implement group/fleet routing or private ACTIVE;
- implement approvals/diagnostics/last-error UI;
- implement response delivery;
- change schema/DDL;
- perform real Codex/network/production effects in acceptance tests;
- claim empirical full Codex storage erasure, which remains P7.

## Public application surface

Add `PrivateDialogueManagementService` with exactly:

- `open_status(request)`
- `handle_callback(request)`

`PrivateDialogueOpenRequest` exact fields:

`user_id, chat_id`.

P4.2 reuses the accepted P4.1 `PrivateCallbackRequest` for callback handling and the accepted opaque `cc1:<32-char token>` grammar.

`PrivateDialogueStatus` exactly:

`RENDERED | CONFIRM_REQUIRED | INTERRUPTED | DELETED | BLOCKED | STALE | UNKNOWN | FAILED | EXPIRED | ALREADY_USED | UNAUTHORIZED`.

`PrivateDialogueReason` exactly:

`CALLBACK_NOT_FOUND | STALE_ACTION | NO_DIALOGUE | DIALOGUE_NOT_RUNNING | JOB_NOT_RUNNING | ACTIVE_BINDING_UNAVAILABLE | INTERRUPT_IN_PROGRESS | INTERRUPT_UNRESOLVED | DIALOGUE_NOT_READY | DELETE_NOT_READY | DELETE_IN_PROGRESS | DELETE_UNKNOWN | ACTION_UNAVAILABLE`.

`PrivateDialogueErrorCategory` exactly:

`INVALID_ARGUMENT | STORAGE | INVARIANT`.

Add frozen repr-safe:

`PrivateDialogueResult(status, panel, reason)`.

## Panel model

`PrivateDialoguePanelSection` exactly:

`STATUS | DELETE_CONFIRM`.

Add frozen repr-safe:

`PrivateDialoguePanel(section, text, rows)`.

Rows may reuse accepted P4.1 `PrivateAdminButton`, preserving exact opaque callback validation/redaction. Add a pure `TelegramPrivateDialoguePanelRenderer` that returns only plain text plus minimal inline keyboard dicts and performs no send/edit/network action.

Safe status text may expose only:

- server display name/ID;
- effective mode if supplied by a trusted local `mode_provider`, otherwise `UNAVAILABLE`;
- live dialogue state;
- safe profile ID;
- active job state, model ID and reasoning effort where canonical.

Never display raw thread ID, job ID, Codex turn ID, tombstone thread hash, prompt/output, callback token/hash, raw exception body or CODEX_HOME. P4.3 owns diagnostics/last sanitized error.

## Canonical status authority

P4.2 reads current dialogue/active-job status only through accepted `ApplicationRecoveryRepository.inspect()`. This gives the complete P3.5 canonical cross-table shape and fails invariant on corruption. P4.2 must not reproduce a weaker dialogue/job coherence reader.

No-dialogue status is `RENDERED` with reason `NO_DIALOGUE`, a static panel and zero callback rows. There is no fabricated dialogue version for no-dialogue navigation.

A live-dialogue panel may create callbacks only after exact current dialogue version/state exists.

## Optional mode provider

Constructor may receive `mode_provider: Callable[[], ControllerMode] | None`.

If absent, display mode `UNAVAILABLE`. If present, it is a read-only local projection and must return an exact `ControllerMode`; wrong type/exception is P4.2 `INVARIANT`. P4.2 never mutates controller mode. P5 remains routing authority.

## Callback authority

Reuse accepted P2.3 one-time callback claims and P4.1 callback batch storage. P4.2 uses the same 900000 ms TTL, one validated clock read per render batch, SHA-256-only token persistence, all-or-none batch insertion and no collision retry. Existing/new hash collision from P4-owned generation is `INVARIANT`.

Wrong user/chat is rejected before token claim and cannot consume the operator callback. Callback consumption occurs before any interrupt/delete effect. Cancellation after consumption never causes P4 retry.

P4.2 callback actions exactly:

- `P42_REFRESH`
- `P42_INTERRUPT`
- `P42_BEGIN_DELETE`
- `P42_CONFIRM_DELETE`
- `P42_CANCEL_DELETE`

Subject types exactly:

- `p42_status`
- `p42_interrupt`
- `p42_delete`

`expected_version` is always the exact current dialogue version. `expected_state` is always the exact current `DialogueState.value`.

## Context fingerprints

Telegram callback data contains no target/action parameter; trusted action/context lives only in the durable callback row.

Status subject ID:

`sha256(dialogue_id UTF-8).hexdigest()`.

Interrupt subject ID:

`sha256(dialogue_id + NUL + job_id + NUL + decimal job.version).hexdigest()`.

Delete subject ID:

`sha256(dialogue_id + NUL + dialogue.state.value + NUL + active_job_id_or_dash + NUL + active_job_version_or_dash).hexdigest()`.

On callback claim, P4.2 re-inspects canonical current state and recomputes the exact expected fingerprint. Zero/mismatch is `STALE`, not effect authority.

## Status action availability

For every live dialogue, `P42_REFRESH` is allowed.

`P42_INTERRUPT` exists only for exact:

- dialogue `TURN_RUNNING`;
- exactly one active job;
- active job `CODEX_RUNNING`.

It is not emitted for RECEIVED/CLAIMED/CODEX_STARTING/INTERRUPTING/unknown/delete/error states.

`P42_BEGIN_DELETE` exists only for:

- exact IDLE with no active job;
- TURN_RUNNING with exact CODEX_RUNNING active job;
- DELETE_PENDING.

It is omitted for CREATING, CREATE_UNKNOWN, IDLE+RECEIVED, TURN_RUNNING+CLAIMED/CODEX_STARTING, INTERRUPTING, TURN_UNKNOWN, DELETING, DELETE_UNKNOWN and ERROR.

P3.5 remains final readiness authority, so even an offered delete may later return `DELETE_NOT_READY` because delivery/approval state changed or was not visible in the status snapshot.

## Interrupt composition

After a claimed exact-current `P42_INTERRUPT` callback, P4.2 constructs exactly one internal `DialogueInterruptRequest` from the current canonical dialogue/job IDs and versions and calls accepted `DialogueInterruptService.interrupt()` exactly once.

Mapping:

- `CONFIRMED | RECONCILED` -> `INTERRUPTED`;
- `REJECTED` -> `BLOCKED` with safe mapped reason;
- `UNKNOWN` -> `UNKNOWN / INTERRUPT_UNRESOLVED`;
- `BLOCKED` -> `BLOCKED` with safe mapped reason;
- `CONFLICT` -> `STALE / STALE_ACTION`.

P3.4 `STORAGE` -> P4.2 `STORAGE`; P3.4 `INVALID_ARGUMENT`/`INVARIANT` from P4-owned validated internal data -> P4.2 `INVARIANT`.

Do not render a mandatory follow-up panel after an interrupt effect; a rendering/storage failure must not disguise an already completed interrupt.

## Hard-delete confirmation

Hard delete is always two-step in P4.2.

A status-panel `P42_BEGIN_DELETE` callback performs no interrupt/delete effect. After one-time claim and exact current context revalidation, it renders `DELETE_CONFIRM` and creates a NEW pair of one-time callbacks:

- `P42_CONFIRM_DELETE`
- `P42_CANCEL_DELETE`

Both bind the same exact current dialogue version/state/delete-context fingerprint.

The confirmation panel must clearly state that the action requests official Codex thread deletion and, only after definitive confirmation, purges CodexControl-owned dialogue content. It must not claim empirical erasure of every Codex internal trace; P7 remains that measurement gate. For a running turn it states that accepted P3.5 may interrupt/reconcile first.

`P42_CANCEL_DELETE` performs no P3 effect and returns a fresh status panel only if the same generation is still current; otherwise STALE.

`P42_CONFIRM_DELETE` is the sole P4.2 callback allowed to call accepted `DialogueDeleteService.delete()`. It constructs exactly one `DialogueDeleteRequest(dialogue_id, expected_dialogue_version)` from current canonical authority.

Mapping:

- `DELETED` -> `DELETED`;
- `FAILED` -> `FAILED`;
- `UNKNOWN` -> `UNKNOWN / DELETE_UNKNOWN`;
- `BLOCKED` -> `BLOCKED` with exact safe reason mapping;
- `CONFLICT` -> `STALE / STALE_ACTION`.

P3.5 `STORAGE` -> P4.2 `STORAGE`; P3.5 `INVALID_ARGUMENT`/`INVARIANT` from P4-owned validated internal data -> P4.2 `INVARIANT`.

No retry, alternate delete path or second `thread/delete` call exists in P4.2. After `DELETED`, no mandatory follow-up panel is rendered.

## DELETE_PENDING

A canonical `DELETE_PENDING` dialogue may offer `P42_BEGIN_DELETE`. After explicit second-step confirmation, P4.2 calls P3.5 using the exact current DELETE_PENDING version. This preserves P3.5 authority that only a fresh explicit request may continue a pre-effect delete intent after restart.

DELETING and DELETE_UNKNOWN never expose confirm/delete callbacks.

## Security and restart

All destructive callback authority is durable in existing `callback_actions`; restart does not create a new action or replay an effect. Expired/already-used/not-found map finitely. Stale version/state/context after claim produces STALE with zero P3 effect and the callback remains consumed.

No hard-delete confirmation state table or schema change is required: the second one-time confirm callback itself is the durable confirmation authority.

## P4.2 acceptance

Must prove at least:

- exact public contracts/redaction;
- no-dialogue static status with zero callbacks;
- canonical snapshot corruption -> INVARIANT;
- safe status fields and no thread/job/turn/CODEX_HOME leakage;
- action availability matrix for every relevant dialogue/active-job state;
- wrong callback principal cannot consume token;
- not-found/expired/replay/stale mapping;
- context fingerprints bind exact job/version/dialogue generation;
- interrupt callback calls real accepted P3.4 exactly once and maps finite outcomes;
- stale interrupt callback has zero P3.4 effect;
- BEGIN_DELETE has zero P3.5/P1 effect and only produces separate confirm/cancel callbacks;
- stale confirmation has zero delete effect;
- confirmed IDLE delete composes with real P3.5 and one fake P1.9 effect maximum;
- DELETE_PENDING explicit continuation composes with real P3.5;
- running-delete P4 mapping preserves P3.5 authority without reproducing its quiescence logic;
- DELETING/DELETE_UNKNOWN never expose second-delete authority;
- cancellation/replay cannot retry interrupt/delete;
- callback collision is invariant/no retry/atomic;
- no real Telegram/network/Codex/production effect;
- accepted P4.1/P3/P2/P1 regressions and exact schema-v1 DDL hash unchanged.

P4.3 remains final private-management composition; P4.2 does not modify the accepted P4.1 root/menu enums or claim P4 complete.
