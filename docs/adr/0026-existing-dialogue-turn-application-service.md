# ADR-0026 — Existing-dialogue turn application service

Status: accepted
Date: 2026-09-06

## Context

P1 now provides accepted Codex app-server ports for authenticated model catalog, thread lifecycle, turn lifecycle, interrupt and delete. P2 now provides architect-accepted crash-safe local state/idempotency through final P2 acceptance at `9db97f0dda109b4d0c0ecfa5f167733905df2766`.

P3 is the application-orchestration layer between those accepted ports and later Telegram UX/routing. The full P3 scope is deliberately split so first-turn lazy thread creation, settings mutation, interrupt and hard-delete policy are not mixed into one change.

P3.1 proves the simplest complete effect path first: **one prompt against an already-existing canonical IDLE dialogue**. It owns prompt admission, immutable selection capture, durable turn claims, one P1.6 turn effect, terminal capture and application-level no-queue/cancellation behavior. It does not create a Codex thread.

## P3 split

- **P3.1** — existing-dialogue prompt execution and terminal capture over accepted P1/P2 ports.
- **P3.2** — lazy `thread/start` + first-turn orchestration and explicit create-failure/recovery boundary.
- **P3.3** — profile/model/reasoning settings application service with authenticated catalog validation and dialogue locks.
- **P3.4** — durable interrupt orchestration over P1.8, including required application-owned `INTERRUPTING` transition authority.
- **P3.5** — hard-delete orchestration over P1.9 + final P3 recovery/application acceptance.

Later slices may add new application-specific repository classes when durable orchestration requires them, but must not silently change accepted P2 repository semantics.

## Layer and dependency rule

P3.1 creates a new application package under `src/codex_control/application/`.

P3.1 may depend on:

- accepted immutable domain/config profile objects;
- accepted P2 repositories and records;
- accepted P1 model-catalog/turn-lifecycle value types through narrow protocols;
- an explicit working-directory resolver port;
- an injected clock and deterministic ID factories.

P3.1 does **not** modify accepted P1 adapter source or accepted P2 repository source/schema.

Tests use temporary SQLite and fake application ports. No real Codex/Telegram/network effect.

## Public request boundary

Expose immutable `ExistingDialoguePromptRequest` with exactly:

- `update_id: int`;
- `source_chat_id: int`;
- `source_message_id: int`;
- `text: str` with `repr=False`.

Static application validation occurs before storage/effect processing:

- update/message IDs are exact non-bool signed-64 values in the accepted non-negative ranges;
- source chat ID is exact non-bool signed-64 and non-zero;
- text is actual `str`, non-empty, NUL-free and at most P1.6 `MAX_TURN_INPUT_CHARS` (`65536`) characters;
- text must encode as UTF-8 without error.

The application does not accept caller-supplied job/payload IDs, profile, model, reasoning effort, thread ID or Codex turn ID.

## Public result boundary

`ExistingDialogueTurnStatus` is exactly:

- `COMPLETED`
- `FAILED`
- `UNKNOWN`
- `DUPLICATE`
- `BUSY`
- `BLOCKED`

`ExistingDialogueTurnReason` is exactly:

- `NO_DIALOGUE`
- `DIALOGUE_NOT_READY`
- `SETTINGS_MISSING`
- `SETTINGS_PROFILE_MISMATCH`
- `PROFILE_NOT_CONFIGURED`
- `MODEL_NOT_CONFIGURED`
- `MODEL_UNAVAILABLE`
- `WORKING_DIRECTORY_UNAVAILABLE`
- `DUPLICATE_NON_JOB`
- `DUPLICATE_ORPHAN_JOB`

`ExistingDialogueTurnResult` is immutable and contains exactly:

- `status`;
- nullable `job: TurnJobRecord`;
- nullable `dialogue: DialogueRecord`;
- nullable `output_payload: TransientPayloadRecord`;
- nullable `reason`.

No raw prompt is returned or exposed in repr.

## Finite application error

Programming/storage/contract failures that are not normal application outcomes use a finite `DialogueApplicationError` / `DialogueApplicationErrorCategory` boundary. Exact categories are:

- `INVALID_ARGUMENT`
- `STORAGE`
- `CODEX`
- `INVARIANT`

Exception rendering contains only the category. Raw repository/adapter exception text, DB paths, prompt/output content and profile `CODEX_HOME` never enter it.

Normal busy/blocked/duplicate/terminal outcomes return `ExistingDialogueTurnResult` rather than throwing application exceptions.

## Durable duplicate-first short circuit

After static request-shape validation, P3.1 MUST inspect the already-durable ingress for `request.update_id` **before** reading current settings, resolving profile/catalog/model/effort, resolving working directory, generating new IDs or calling any Codex port.

This guarantees replay authority does not depend on today's configuration or catalog availability.

If an ingress row already exists:

### Existing JOB ingress with existing job

- require exact canonical job `job_id == ingress.job_id` and `job.telegram_update_id == ingress.update_id`;
- require exactly one canonical INPUT through accepted `TransientPayloadRepository.get_input_for_job(job_id)`;
- return `DUPLICATE` with the exact durable job;
- current caller text/settings/model/IDs are irrelevant and never rewrite durable state;
- no model-catalog/working-directory/turn port call occurs.

The current live dialogue may be read for factual result context, but its current state does not authorize re-execution.

### Existing non-JOB ingress

Return `DUPLICATE`, `job=None`, reason `DUPLICATE_NON_JOB`, with no external/configuration work.

A prior CONTROL/ignored update is never reclassified as a prompt.

### Existing orphan JOB ingress

An orphan `JOB:<id>` ingress with no job can be legitimate after accepted P2.5 hard-delete finalization until P2.6a metadata retention removes the old ingress.

If no live dialogue exists, return `DUPLICATE`, `job=None`, reason `DUPLICATE_ORPHAN_JOB`; never recreate a job/dialogue or call Codex.

If a live dialogue still exists while the JOB ingress references a missing job, that shape is not produced by accepted P2 history and is an application `INVARIANT` failure.

The duplicate-first read is an optimization/safety short circuit, not the new-update atomic dedupe transaction. For a previously unseen update, accepted `TurnJobRepository.claim_ingress` remains authoritative and handles races where another process commits the same update after this precheck.

## Explicit configured profile authority for NEW updates

Only after proving the update has no existing ingress does P3.1 perform new-prompt preflight.

The service is constructed with the exact server ID and explicit configured `tuple[CodexProfile, ...]`; it never scans the filesystem for profiles.

For an existing dialogue:

1. the durable dialogue `server_id` must equal the service server ID;
2. durable settings must exist;
3. settings `profile_id` must equal the dialogue immutable profile;
4. the profile ID must exist in the explicit configured profile tuple;
5. settings `model_id` must be non-null.

Failure before durable prompt admission is `BLOCKED` with a finite reason and creates no ingress/job/payload or turn effect.

## Authenticated selection capture

For a NEW update only, before creating a prompt job, P3.1 calls the injected authenticated model-catalog port for the exact bound profile.

It resolves settings `model_id` and calls the catalog's accepted reasoning-effort validation. If settings reasoning effort is NULL, the catalog default is resolved to the explicit concrete effort before job creation.

The immutable P2 job snapshot stores:

- exact dialogue server/profile/thread;
- logical model ID selected in durable settings;
- exact resolved concrete reasoning effort.

Thus P2 never stores NULL merely because the P1 adapter later chose a default.

Catalog unavailable/invalid/hidden/missing model or unsupported effort is `BLOCKED` with `MODEL_UNAVAILABLE`; no prompt job/effect is created.

P1.6 independently revalidates the same profile/model/effort at the effect boundary; P3.1 does not bypass that adapter protection.

## Working-directory port

P3.1 receives a narrow resolver equivalent to:

`resolve(profile_id) -> TrustedWorkingDirectory`

The resolver is configuration/application authority, not a filesystem scan.

Resolution happens before durable NEW prompt admission. Missing/invalid resolution returns `BLOCKED / WORKING_DIRECTORY_UNAVAILABLE` with no effect.

Duplicate short-circuit never needs working-directory resolution.

P3.1 does not add deployment/config file format for working directory; P8 owns deployment packaging.

## IDs and transient retention

P3.1 owns opaque local job/payload ID generation through injected deterministic factories in tests and safe UUID-derived defaults in production code.

Generated IDs must satisfy accepted P2 ID bounds and are never based on prompt text.

Application constants:

- `P3_INPUT_PAYLOAD_RETENTION_MS = 3_600_000` (1 hour);
- `P3_COMPLETED_OUTPUT_RETENTION_MS = 3_600_000` (1 hour);
- `P3_UNCERTAIN_OUTPUT_RETENTION_MS = 86_400_000` (24 hours).

The service uses one injected signed-64 millisecond clock to compute absolute expiries and passes the same clock into repositories it constructs for P3.1 mutations. Overflow/invalid clock is a finite application error; it never truncates/wraps.

The duplicate-first path does not need the application clock or ID factory.

Expired active INPUT safety remains owned by accepted P2.4b retention guards.

## Admission state for NEW updates

P3.1 executes a NEW update only against an existing canonical `DialogueState.IDLE` dialogue with non-null thread ID.

- no dialogue -> `BLOCKED / NO_DIALOGUE`;
- `TURN_RUNNING` -> `BUSY`;
- any other non-IDLE dialogue state -> `BLOCKED / DIALOGUE_NOT_READY`.

P3.1 does not synthesize a thread or state transition for CREATING/UNKNOWN/ERROR/delete states.

## Durable NEW prompt admission

After new-update preflight selection/working-directory resolution, call accepted `TurnJobRepository.claim_ingress(...)` with:

- exact Telegram/source IDs from request;
- generated job/input payload IDs;
- exact dialogue/server/profile/thread;
- selected logical model ID;
- resolved concrete reasoning effort;
- exact UTF-8 input bytes;
- one-hour absolute INPUT expiry.

This commit remains the sole atomic new-prompt dedupe boundary before `turn/start`.

A same-update race may cause `claim_ingress` itself to return `DUPLICATE` despite the earlier read finding no row. That result is authoritative and is returned immediately without a turn call.

For a new different update, an outstanding RECEIVED or racing turn conflict preserves V1 no queue. When the canonical live dialogue is still IDLE after the conflict, return `BUSY`; otherwise return the appropriate busy/blocked current-state result. Do not delete or rewrite an accepted job.

After a CREATED claim, reread/materialize the current dialogue before `claim_turn`; use its exact current version and require it is still the same IDLE server/profile/thread binding. Accepted no-queue/delete guards prevent silently moving the newly admitted job under another binding.

## Durable turn-start ordering

For a newly CREATED job:

1. accepted `claim_turn(...)` atomically moves job `RECEIVED -> CLAIMED` and dialogue `IDLE -> TURN_RUNNING`;
2. accepted `mark_codex_starting(...)` commits `CLAIMED -> CODEX_STARTING`;
3. only after that durable commit may P3.1 call the P1.6 turn-start port.

The effect call uses exact:

- `ThreadBinding(dialogue.profile_id, dialogue.thread_id)`;
- immutable job model ID;
- immutable resolved reasoning effort;
- original request text;
- resolved `TrustedWorkingDirectory`.

No second `turn/start` call is made by P3.1 for one CREATED job.

## Turn-start result mapping

P1 `TURN_START_CONFIRMED`:

- binding profile/thread must equal the durable job/dialogue binding;
- persist exact turn ID through `mark_codex_running(...)`;
- then wait on that exact returned `TurnBinding`.

If the returned binding is malformed/mismatched, treat the external result as ambiguous and atomically attempt `finish_codex(... UNKNOWN, error_class="CODEX_AMBIGUOUS")` from CODEX_STARTING. No blind retry.

P1 `TURN_START_REJECTED`:

- do not retry;
- `finish_codex(... FAILED, error_class="CODEX_TURN_FAILED")` from CODEX_STARTING;
- dialogue becomes ERROR.

P1 `TURN_START_UNKNOWN`:

- do not retry;
- `finish_codex(... UNKNOWN, error_class="CODEX_AMBIGUOUS")` from CODEX_STARTING;
- dialogue becomes TURN_UNKNOWN.

Finite P1 lifecycle errors that are provably local/pre-effect may become deterministic FAILED with sanitized `CODEX_PROCESS`; an error whose dispatch status cannot be proven is UNKNOWN. Raw adapter text is never persisted.

If external turn start is confirmed but the durable CODEX_RUNNING binding cannot be committed, P3.1 must not issue another start. It attempts to fail closed to durable UNKNOWN from the still-current CODEX_STARTING state when possible; otherwise it returns finite application STORAGE/INVARIANT failure and leaves existing durable evidence for later P3 recovery.

## Terminal wait mapping

After durable CODEX_RUNNING, wait exactly once for the exact P1 `TurnBinding`.

Map:

- P1 `COMPLETED` -> P2 `COMPLETED`;
- P1 `FAILED` -> P2 `FAILED` with `CODEX_TURN_FAILED`;
- P1 `UNKNOWN` or ambiguous wait failure -> P2 `UNKNOWN` with `CODEX_AMBIGUOUS`.

No terminal result causes another turn start.

## User-visible output encoding

P3.1 persists the already-obtained user-visible P1 agent-message projection before returning terminal success/failure.

Messages are ordered by the P1 collector and encoded as:

`message[0].text + "\n\n" + message[1].text + ...`

then UTF-8 encoded.

This preserves message order and gives P6 a deterministic crash-safe text source without persisting hidden reasoning or command-output floods.

If the resulting bytes are non-empty, P3.1 passes one all-or-none OUTPUT bundle to `finish_codex` in the SAME terminal transaction.

- COMPLETED output expiry: 1 hour;
- FAILED/UNKNOWN partial output expiry: 24 hours.

If there are no non-empty projected bytes, no OUTPUT payload is created.

Accepted P1.6 total message bounds plus UTF-8 maximum width and separators remain below the accepted 8 MiB P2 transient-payload ceiling. P3.1 must test this bound rather than truncate user-visible output.

## Cancellation ownership

Before a new durable `claim_ingress` transaction is submitted, ordinary caller cancellation may propagate with no new job.

Once a new prompt admission returns `CREATED`, the application owns that admitted prompt. Repeated caller cancellation must not detach the orchestration and must not be interpreted as an operator interrupt.

P3.1 runs the post-admission execution in one owned task and awaits it through cancellation shielding/looping so the same call reaches a durable terminal/UNKNOWN/application-failure boundary. It does not launch a second orchestration task.

Explicit turn interruption is P3.4 only.

## Concurrency / no queue

Two different NEW requests racing against one IDLE dialogue:

- at most one may create the outstanding RECEIVED job;
- at most one may perform P1 `start_turn`;
- the other returns BUSY/blocked finite result;
- there is no in-memory delayed queue and no later automatic execution of the rejected prompt.

Same update replay at any point after its durable ingress exists returns DUPLICATE through the duplicate-first or atomic race path and never starts another P1 turn.

## No restart recovery policy in P3.1

P3.1 proves normal single-invocation orchestration only. It does not scan/reconcile pre-existing `CODEX_STARTING`, `CODEX_RUNNING`, `TURN_UNKNOWN`, delivery, create or delete recovery states after process restart.

P3.4/P3.5 own later explicit recovery/read models. P3.1 must not guess that an old effect did or did not happen.

## Security and logging

- request text field is `repr=False`;
- output payload content remains `repr=False` through P2;
- application result/error/service repr never prints prompt/output/CODEX_HOME/storage path/adapter internals;
- no logging of raw prompt, output, terminal messages, callback token, stdout/stderr or arbitrary exception text;
- no real Codex/Telegram/network call in tests.

## P3.1 out of scope

P3.1 does not implement:

- lazy `thread/start` / first dialogue creation;
- thread resume/start recovery;
- profile/model/reasoning mutation;
- approval Telegram projection;
- interrupt / `INTERRUPTING` transitions;
- hard delete / P1.9 orchestration;
- restart reconciliation policy;
- delivery-plan/chunk/Telegram sending;
- controller ACTIVE/SLEEP routing;
- Telegram authorization/UI;
- P4+;
- production deployment.
