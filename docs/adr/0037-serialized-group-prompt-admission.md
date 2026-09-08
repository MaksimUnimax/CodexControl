# ADR-0037 — P5.2 serialized group prompt admission and no-queue routing

Status: Accepted
Date: 2026-09-08

## Context

P5.1 established the group/fleet control plane: exact operator/control-supergroup authorization, reserved control classification, persistent fleet keyboard, current-boot SLEEP authority and durable activation/all-sleep control epochs. P2.C2 then added exact terminal content-free `IGNORED_REJECTED` so an authorized prompt rejected before JOB/effect cannot later execute when the same Telegram update is replayed.

P5.2 now owns ordinary authorized group TEXT routing into accepted P3. The design must satisfy simultaneously:

- SLEEP prompt is terminally ignored;
- ACTIVE prompt may execute through accepted P3 only;
- BUSY means immediate rejection, never queue;
- pre-JOB P3 BLOCKED/BUSY/stale decisions become durable `IGNORED_REJECTED`;
- a duplicate update never later executes;
- control processing must remain responsive while a Codex turn runs;
- an old prompt must not execute after a newer control epoch;
- P5.2 must not create a second durable dialogue/JOB/turn state machine.

Holding one group lock across the entire `DialogueTurnService.execute()` call is forbidden: P3 waits until the turn reaches a terminal result, so such a lock would delay second prompts until the first turn completes (creating an implicit queue) and would prevent SLEEP/ALL_SLEEP controls from being applied while a turn runs.

## Decision

Add a final P5.2 application facade:

`FleetGroupRoutingService`

with one public async method:

`handle(update)`.

It consumes only exact accepted P5.1 `GroupInboundUpdate` values. Raw Telegram dictionaries remain solely at `TelegramGroupUpdateAdapter`.

The facade composes:

1. accepted P5.1 fleet-control routing;
2. accepted P2.C2 ingress terminal dispositions;
3. accepted P3.2 `DialogueTurnService` prompt orchestration.

P5.2 adds no schema and changes no accepted P3/P5.1 production contract.

## Public ports

Define a narrow async `FleetControlPort` with:

`handle(update) -> FleetControlResult`.

Accepted `FleetControlService` is the production implementation.

Define a narrow async `DialogueTurnPort` with:

`execute(request) -> ExistingDialogueTurnResult`.

Accepted `DialogueTurnService` is the production implementation.

Ports exist only for application composition/testing. Returned values are strictly validated; malformed port results fail INVARIANT.

## Public result

`GroupRoutingStatus` exactly:

- `CONTROL`
- `STATUS`
- `PROMPT`
- `DUPLICATE`
- `BUSY`
- `BLOCKED`
- `IGNORED_SLEEP`
- `REJECTED`
- `UNAUTHORIZED`
- `UNSUPPORTED`
- `MALFORMED`

`GroupRoutingReason` exactly:

- `STALE_PROMPT`
- `LOCAL_PROMPT_IN_FLIGHT`
- `IN_FLIGHT_DUPLICATE`
- `INVALID_PROMPT`

`GroupRoutingErrorCategory` exactly:

- `INVALID_ARGUMENT`
- `STORAGE`
- `CODEX`
- `INVARIANT`

Add finite content-free `GroupRoutingError`.

Add frozen repr-redacted:

`GroupRoutingResult(status, snapshot, control_result, turn_result, disposition, reason)`.

`control_result` and `turn_result` are excluded from repr. No prompt/output/thread/job/turn identifiers may appear in the generic result repr.

The result is an internal application handoff. P6 may later consume the nested accepted P3 result for delivery; P5.2 sends nothing to Telegram.

## Result relations

`CONTROL`:

- exact P5.1 `control_result` required;
- its status is APPLIED, STALE or DUPLICATE;
- no P3 turn result;
- no P5.2 disposition/reason.

`STATUS`:

- exact P5.1 STATUS result required;
- no P3 turn result or P5.2 disposition.

`PROMPT`:

- accepted P3 turn result required with status COMPLETED, FAILED or UNKNOWN;
- exact durable ingress for the update must be `JOB` and match the P3 job identity;
- `disposition=JOB`;
- snapshot is the ACTIVE admission snapshot;
- no P5.2 reason.

`DUPLICATE`:

- no new effect;
- for a durable duplicate, disposition is the existing exact durable disposition;
- for the special same-update local in-flight duplicate, disposition is `None` and reason is `IN_FLIGHT_DUPLICATE`.

`BUSY`:

- different update while a P5.2 prompt marker exists, or exact accepted P3 BUSY;
- fresh decision is terminalized as `IGNORED_REJECTED` before successful return;
- local-marker BUSY uses reason `LOCAL_PROMPT_IN_FLIGHT`;
- P3 BUSY retains its accepted turn result with no added P5.2 reason.

`BLOCKED`:

- only accepted P3 pre-JOB BLOCKED;
- fresh decision is terminalized as `IGNORED_REJECTED` before return;
- accepted P3 BLOCKED reason remains in the nested turn result.

`IGNORED_SLEEP`:

- terminal exact `IGNORED_SLEEP`;
- snapshot effective mode SLEEP.

`REJECTED`:

- terminal exact `IGNORED_REJECTED`;
- reason is `STALE_PROMPT` or `INVALID_PROMPT`.

UNAUTHORIZED/UNSUPPORTED/MALFORMED map exact P5.1 results and have no prompt result/content.

Impossible relation => INVARIANT.

## Constructor and coherence

`FleetGroupRoutingService(storage, *, fleet_control, dialogue_turn, now_ms=None)`.

Require exact accepted `SqliteStorage`, async-compatible fleet-control port, async-compatible dialogue-turn port and optional clock callable.

The production composition MUST provide ports bound to the same local controller/storage/profile/runtime composition. P5.2 does not inspect private attributes of accepted sub-services.

The final process must route group updates through `FleetGroupRoutingService`; it must not bypass the facade and independently dispatch the same group stream to `FleetControlService` or P3. P5.3 final composition acceptance will prove this wiring.

## One short routing lock

P5.2 owns one `asyncio.Lock` for local group routing decisions.

The lock protects only:

- one P5.1 control/status/authorization operation;
- TEXT current-mode projection;
- durable duplicate precheck;
- stale/SLEEP/local-busy terminal claim;
- construction and publication of the one local prompt marker.

The lock is NOT held while P3 executes the Codex turn.

Thus controls remain processable while a turn is running and a second prompt is never delayed until the turn becomes idle.

## Local prompt marker

P5.2 owns at most one process-local marker for a prompt that has been logically admitted by the group facade and whose P3 call is still in flight.

The marker stores only bounded non-content coordination identity sufficient to distinguish the exact Telegram update and one private object/token identity. It stores no prompt text, no model output and no durable business state.

The marker is NOT:

- durable job authority;
- dialogue state authority;
- restored on restart;
- a queue;
- permission to retry an external effect.

Accepted P3/P2 remain the only durable JOB/turn authority.

The marker closes the race before P3 has persisted TURN_RUNNING/JOB. A different prompt update seeing the marker is BUSY and is immediately terminalized as `IGNORED_REJECTED` without calling P3.

## Same-update in-flight duplicate

A duplicate delivery of the SAME update ID while that exact update owns the local marker must not call `claim_ignored(IGNORED_REJECTED)`, because doing so could consume the update before the original P3 invocation creates its JOB and suppress a valid first execution.

Instead return:

- `DUPLICATE`
- reason `IN_FLIGHT_DUPLICATE`
- no durable disposition yet
- zero P3 redispatch.

The original owned P3 invocation continues. If the process crashes before any durable ingress/effect, later replay is allowed to re-attempt because no durable processing occurred. Once P3 creates JOB or P5.2 creates a terminal ignored/rejected row, subsequent duplicates use that durable authority.

## TEXT routing order

For exact `GroupInboundKind.TEXT`, under the routing lock:

1. delegate the exact normalized update to P5.1 fleet control and require `FleetControlStatus.TEXT` plus an exact snapshot; this re-validates current boot and exact principal/chat;
2. read `IngressUpdateRepository.get(update_id)`;
3. if an ingress already exists -> `DUPLICATE`, no P3 and no reclassification;
4. if the local marker is owned by the same update ID -> in-flight `DUPLICATE`, no durable claim and no P3 redispatch;
5. if `message_id <= snapshot.last_control_epoch` -> terminal `IGNORED_REJECTED`, status REJECTED, reason STALE_PROMPT;
6. if snapshot effective mode is SLEEP -> terminal `IGNORED_SLEEP`;
7. if snapshot effective mode is not exact ACTIVE/SLEEP -> INVARIANT;
8. if another update owns the local marker -> terminal `IGNORED_REJECTED`, status BUSY, reason LOCAL_PROMPT_IN_FLIGHT;
9. construct exact accepted `ExistingDialoguePromptRequest` from update ID/chat ID/message ID/text;
10. if request construction fails only because the authorized TEXT is not acceptable to P3 (for example invalid UTF-8 scalar content), terminalize as `IGNORED_REJECTED`, status REJECTED, reason INVALID_PROMPT;
11. publish the local marker and create exactly one owned P3 task;
12. release the routing lock;
13. await the owned P3 task without cancelling it because the caller is cancelled.

No prompt text is copied into the marker/result/evidence/logging.

## Stale prompt ordering

A prompt is eligible only if:

`source_message_id > current last_control_epoch`.

`message_id <= last_control_epoch` is a fail-closed stale ordering decision and MUST be terminal `IGNORED_REJECTED`, regardless of whether current effective mode is ACTIVE or SLEEP.

This prevents an old/backlogged group message from executing after a newer activation/sleep control has already become durable.

P5.2 does not create a second durable global message epoch; P5.1 control epoch remains the durable fleet ordering authority.

## SLEEP prompt

For a fresh eligible TEXT whose current effective mode is SLEEP:

call exactly once:

`IngressUpdateRepository.claim_ignored(update_id, IGNORED_SLEEP)`.

Fresh result must be exact content-free terminal SLEEP ingress.

If the claim reports duplicate because another durable classification already won, return DUPLICATE using the original record; never reclassify.

No P3 call, JOB, payload or Codex effect.

## Local BUSY prompt

For a different fresh update while another P5.2 prompt marker exists and current mode remains ACTIVE:

call exactly once:

`claim_ignored(update_id, IGNORED_REJECTED)`.

Fresh result -> BUSY/LOCAL_PROMPT_IN_FLIGHT.

Duplicate result -> DUPLICATE preserving the original disposition.

No P3 call and no queue.

Controls are still allowed through the routing lock while the first P3 task runs.

## ACTIVE P3 delegation

A fresh, non-stale, valid ACTIVE prompt with no competing marker creates exactly one owned task calling accepted:

`DialogueTurnService.execute(ExistingDialoguePromptRequest(...))`.

P5.2 does not call:

- TurnJobRepository.claim_ingress;
- P1 thread/start;
- P1 turn/start;
- ActiveTurnRegistry directly;
- model catalog or settings selection directly.

All selection, lazy dialogue creation, JOB/INPUT admission, turn execution and terminal output capture remain accepted P3 authority.

## Mapping P3 BUSY/BLOCKED

Accepted P3 BUSY/BLOCKED are pre-JOB results only when:

- `job is None`;
- `output_payload is None`;
- BUSY reason is None;
- BLOCKED reason is one of accepted pre-admission reasons:
  - NO_DIALOGUE
  - DIALOGUE_NOT_READY
  - SETTINGS_MISSING
  - SETTINGS_PROFILE_MISMATCH
  - PROFILE_NOT_CONFIGURED
  - MODEL_NOT_CONFIGURED
  - MODEL_UNAVAILABLE
  - WORKING_DIRECTORY_UNAVAILABLE
  - SETTINGS_CHANGED.

Malformed shapes fail INVARIANT.

Before returning BUSY or BLOCKED, P5.2 calls `claim_ignored(..., IGNORED_REJECTED)` exactly once.

If that claim is fresh, return BUSY/BLOCKED with durable rejected disposition.

If another durable ingress already won meanwhile, return DUPLICATE and preserve the original classification. In particular, never overwrite a JOB with IGNORED_REJECTED.

## Mapping P3 DUPLICATE

If P3 returns DUPLICATE after the initial P5.2 duplicate precheck lost a race, P5.2 re-reads exact ingress for the update.

A canonical durable ingress must exist. Return DUPLICATE using its exact disposition. No new ignored/rejected claim and no P3 redispatch.

## Mapping P3 terminal work

For P3 COMPLETED/FAILED/UNKNOWN:

- exact job must be present;
- reason must be None;
- durable ingress for the update must be JOB;
- ingress job ID must equal the returned job ID;
- no rejected/sleep claim is permitted.

Return top-level PROMPT with the exact nested P3 result and disposition JOB.

P3 failure/unknown after JOB is still admitted work; it must never be rewritten as `IGNORED_REJECTED`.

## P3 exceptions

Finite accepted `DialogueApplicationError` maps to P5.2 finite error category. P5.2 does not blindly create `IGNORED_REJECTED` after an exception because it may be impossible to prove whether JOB/effect authority already exists.

No blind retry.

Before any later explicit replay, accepted durable ingress/P3 recovery remains authority.

## Marker clearing

The marker is cleared only by the exact owned P3 task identity in a `finally` path under the routing lock.

A stale/other task must never clear a newer marker.

BUSY/BLOCKED terminal rejection is committed before the marker is cleared.

Caller cancellation does not cancel the owned P3 task. No automatic P3 redispatch occurs.

## Controls during a running prompt

CONTROL/STATUS/UNAUTHORIZED/UNSUPPORTED/MALFORMED continue to delegate to accepted P5.1 under the short routing lock even while a P3 task is running.

A newer SLEEP/ALL_SLEEP control does not retroactively cancel a prompt already logically admitted by P5.2. It changes durable mode for subsequent prompt admissions.

A later prompt therefore observes the newer control epoch/mode and is ignored/rejected as appropriate.

Interrupt remains explicit private P3.4/P4 authority, not a side effect of SLEEP.

## Restart behavior

The local prompt marker is not restored.

After restart, P5.1 again starts effective SLEEP until fresh self activation. Durable P3 recovery/state remains authority for any pre-crash JOB/turn. A later ACTIVE prompt encountering durable TURN_RUNNING/unknown/not-ready state is rejected through accepted P3 BUSY/BLOCKED and terminal P2.C2 rejection.

No delayed local queue survives restart.

## Security/content boundary

P5.2 persists only accepted ingress/JOB/transient content through existing repositories. It adds no new content store.

SLEEP/BUSY/BLOCKED/stale/invalid pre-JOB decisions store only exact finite disposition strings. No prompt text or reason prose is stored in ingress metadata.

Generic P5.2 result/error repr never exposes prompt/output, CODEX_HOME, raw Telegram JSON, thread/job/turn IDs, transient payload content or raw exceptions.

## Non-goals

P5.2 does not implement:

- Telegram HTTP/polling/webhook/token loading;
- response send/edit/chunking/delivery;
- P1.7 approval-response coordination;
- fleet peer communication;
- fleet-version/status final acceptance;
- production config/secrets/systemd;
- private mode mutation;
- P5.3/P6+.

No schema/DDL change.

## Acceptance

P5.2 focused tests must prove at least:

- exact public enums/records/repr redaction;
- non-TEXT exact P5.1 delegation;
- durable duplicate precheck before any P3 effect;
- SLEEP -> fresh IGNORED_SLEEP and replay duplicate;
- stale prompt `message_id <= last_control_epoch` -> IGNORED_REJECTED and never P3;
- ACTIVE prompt -> exactly one accepted P3 call;
- existing-dialogue and lazy-first-dialogue P3 composition;
- P3 BUSY -> durable IGNORED_REJECTED; replay after state becomes idle remains duplicate and never executes;
- P3 BLOCKED -> durable IGNORED_REJECTED; replay after configuration/state repair remains duplicate;
- local different-update marker BUSY -> durable rejected with zero P3 call;
- same-update in-flight duplicate does not consume/reject the original update;
- second prompt is not delayed until first terminal result;
- SLEEP/ALL_SLEEP control is processed while first turn is still blocked/running;
- next prompt after that control is SLEEP-ignored;
- P3 FAILED/UNKNOWN after JOB remains JOB, never rejected;
- malformed P3 result fails INVARIANT;
- caller cancellation does not cancel/retry the owned P3 call;
- restart has no local queue/marker authority;
- full accepted P1–P5.1/P2.C2 regressions remain green;
- no real Telegram/network/Codex/production effect in tests.

P5.3 remains responsible for final fake multi-controller fleet acceptance and fleet status/version safeguards.