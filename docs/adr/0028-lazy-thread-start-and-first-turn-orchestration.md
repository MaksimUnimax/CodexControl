# ADR-0028 — Lazy thread/start and first-turn orchestration

Status: accepted
Date: 2026-09-06

## Context

P3.1 is architect-accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550` and owns one prompt against an already-existing canonical IDLE dialogue. It deliberately returns `BLOCKED / NO_DIALOGUE` when no live dialogue exists.

P3.2 adds the missing lazy first-dialogue path. It must create the local dialogue intent, durably admit the first prompt, perform exactly one P1.5 `thread/start`, persist the confirmed thread identity, then run the already-accepted first-turn orchestration without creating a second job or second prompt ingress.

P3.2 must also define the fail-closed restart boundary for a pre-existing `CREATING` dialogue. Schema-v1 has no separate durable `THREAD_STARTING` marker: the same durable CREATING shape can exist immediately before external dispatch or after an ambiguous process crash during/after `thread/start`. Therefore restart code must never infer that a pre-existing CREATING state is safe to dispatch again.

## Accepted dependencies

P3.2 depends on:

- accepted P3.1 application contracts and internal admitted-turn behavior;
- ADR-0027 retention-compatible JOB replay;
- accepted P2 `DialogueRepository` create-intent/confirm/error/unknown methods;
- accepted P2 `TurnJobRepository.claim_ingress` behavior for a `CREATING` dialogue with `thread_id=NULL`;
- accepted P2 `claim_turn`, which may bind a previously NULL RECEIVED-job thread ID once the owning dialogue is IDLE with the confirmed thread;
- accepted P1.5 `thread/start` ambiguity-safe result contract;
- the same authenticated model catalog and trusted-working-directory authorities used by P3.1.

No schema or migration change is authorized.

## Layering

P3.2 may add new files under `src/codex_control/application/` and may narrowly refactor P3.1 private/internal application helpers so both P3.1 and P3.2 reuse one selection/admitted-turn implementation.

P3.1 public types, public service surface and accepted behavior must remain unchanged.

P3.2 does not modify accepted P1 adapter source or accepted P2 storage/repository source.

## Unified higher-level service

P3.2 exposes a new Telegram-agnostic higher-level service:

`DialogueTurnService`

Its exact public callable surface is:

- `execute`;
- `recover_preexisting_creation`.

`DialogueTurnService.execute` accepts the already accepted `ExistingDialoguePromptRequest` and returns the already accepted `ExistingDialogueTurnResult`.

The service wraps/reuses `ExistingDialogueTurnService` for every path that already has durable ingress or a live dialogue. It only enters lazy creation when the accepted existing-dialogue service returns exactly:

- status `BLOCKED`;
- reason `NO_DIALOGUE`;
- no durable job.

No P3.1 result type is widened or changed.

## Thread lifecycle port

Expose a narrow application protocol:

`ThreadLifecyclePort`

with exact semantic method:

`async start(profile_id, *, model_id, reasoning_effort, working_directory) -> ThreadOperationResult`.

P3.2 does not expose or call thread resume/delete.

## Creation recovery result

Expose:

`CreationRecoveryStatus` exactly:

- `NO_ACTION`;
- `MARKED_UNKNOWN`.

Expose frozen:

`CreationRecoveryResult`

with exact fields:

- `status`;
- `dialogue` (`DialogueRecord | None`).

No content, exception text or external thread identity beyond the dialogue's accepted public record is added.

## No-dialogue preflight

Lazy creation begins only after P3.1 has already performed static request validation and durable duplicate-first lookup and has returned `BLOCKED / NO_DIALOGUE`.

Before any new durable mutation or `thread/start`, P3.2 requires:

1. durable settings exist;
2. `settings.profile_id` is non-NULL;
3. that profile exists in the explicit configured `tuple[CodexProfile, ...]`;
4. `settings.model_id` is non-NULL;
5. authenticated catalog belongs to that exact profile;
6. the selected logical model descriptor exists and is not hidden;
7. concrete reasoning effort is resolved through the authenticated catalog; a NULL settings effort becomes the catalog default;
8. trusted working directory resolves to exact `TrustedWorkingDirectory`.

Missing settings returns `BLOCKED / SETTINGS_MISSING`.

NULL/unconfigured profile returns `BLOCKED / PROFILE_NOT_CONFIGURED`.

Missing model returns `BLOCKED / MODEL_NOT_CONFIGURED`.

Catalog/model/hidden/effort failure returns `BLOCKED / MODEL_UNAVAILABLE`.

Working-directory failure returns `BLOCKED / WORKING_DIRECTORY_UNAVAILABLE`.

No local dialogue/job/ingress/payload and no P1 effect may exist from a blocked preflight.

## IDs and retention

P3.2 generates exactly the local identifiers needed for the lazy first path:

- dialogue ID;
- job ID;
- INPUT payload ID;
- later OUTPUT ID only if the accepted admitted-turn runner needs it.

Generated identifiers use the same bounded opaque-ID rules as P3.1. A safe UUID-derived default is required. No ID is prompt-derived.

The first INPUT uses accepted P3.1 one-hour retention authority.

P3.2 uses the same injected signed-64 millisecond clock authority as P3.1 and passes it to repositories it constructs.

No ID-collision retry loop exists.

## Cancellation ownership boundary

All no-dialogue preflight remains effect-free and ordinary caller cancellation may propagate.

After preflight succeeds, P3.2 creates exactly one owned lazy-creation task **before submitting `DialogueRepository.create_intent`**. The public call awaits that task through the same shield/loop ownership principle as P3.1.

This deliberately closes the caller-cancellation window between local CREATING persistence and first-prompt admission. Repeated caller cancellation must not detach the owned create/admission/thread-start/first-turn sequence and must never be interpreted as interrupt.

Process crash remains different from caller cancellation and is handled by the explicit recovery boundary below.

## Durable lazy first-prompt order

The owned no-dialogue path order is exactly:

1. `DialogueRepository.create_intent(...)` -> durable `CREATING`, `thread_id=NULL`;
2. `TurnJobRepository.claim_ingress(...)` against that exact CREATING dialogue, with exact first prompt, immutable model/effort snapshot, `thread_id=None` -> durable JOB ingress + RECEIVED + INPUT;
3. only after both commits, call exactly one injected P1.5 `thread_lifecycle.start(...)`;
4. confirmed exact thread binding -> `DialogueRepository.confirm_created(...)` -> IDLE with exact thread ID;
5. reuse the accepted admitted-turn runner for the already-created RECEIVED job; `claim_turn(...)` binds the previously NULL job thread ID to the confirmed dialogue thread and continues the P3.1 effect order.

P3.2 never calls `ExistingDialogueTurnService.execute` on the newly admitted first update to continue it, because that would correctly return DUPLICATE. It must reuse private/internal admitted-turn orchestration instead of creating another ingress/job.

## First-prompt atomic authority

The first prompt must be durably present before `thread/start`:

- exact JOB ingress;
- exact RECEIVED job;
- exact INPUT payload;
- immutable selected profile/model/concrete effort;
- job thread ID NULL while the dialogue is CREATING.

No `thread/start` call is legal before this state commits.

This guarantees same-update replay after the admission boundary is a no-effect duplicate even while thread creation is in progress.

## create_intent race

If `create_intent` returns `ALREADY_EXISTS` because another actor created a live dialogue after the earlier no-dialogue read, P3.2 performs no thread effect.

It delegates/re-evaluates the current request through accepted existing-dialogue semantics exactly once. Depending on durable state this may become DUPLICATE, BUSY or `BLOCKED / DIALOGUE_NOT_READY`.

There is no retry loop and no delayed queue.

## claim_ingress race

If the first-path `claim_ingress` returns DUPLICATE because another actor committed the same update after local CREATING creation, P3.2 performs no `thread/start` and returns/reconstructs the accepted duplicate result under ADR-0027.

A STATE_CONFLICT or other durable race before `thread/start` is normalized through current accepted dialogue/duplicate state without deleting or rewriting another actor's state. No blind retry.

## P1 thread/start call

Call exactly one:

`thread_lifecycle.start(`
`    profile_id=created_dialogue.profile_id,`
`    model_id=immutable_job.model_id,`
`    reasoning_effort=immutable_job.reasoning_effort,`
`    working_directory=trusted_workdir,`
`)`

The model ID and effort are the same immutable logical snapshot already persisted in the RECEIVED job.

No current settings/catalog reread occurs after admission.

## START_CONFIRMED

A confirmed result is usable only if:

- result is exact `ThreadOperationResult`;
- status is `START_CONFIRMED`;
- binding is exact `ThreadBinding`;
- binding.profile_id equals the durable dialogue/job profile;
- returned model ID equals the immutable logical job model ID;
- returned reasoning effort equals the immutable concrete job effort.

Malformed/mismatched confirmed results are treated as ambiguous external creation, never as success and never retried.

For an exact confirmed result:

1. `confirm_created(dialogue_id, expected_version=CREATING.version, thread_id=binding.thread_id)`;
2. on exact IDLE confirmation, invoke the shared admitted-turn runner with the existing RECEIVED job, original request text and already-resolved working directory;
3. the runner performs accepted P3.1 `claim_turn -> CODEX_STARTING -> turn/start -> CODEX_RUNNING -> wait -> finish` semantics.

## Confirm-local persistence failure after confirmed external start

P3.2 never issues another `thread/start` after a confirmed external start.

If `confirm_created` does not return normally, reread the live dialogue once:

- if it is already exact IDLE with the same dialogue/profile/thread binding, treat the local confirmation as durable and continue the first turn;
- if it remains the exact CREATING state that can still be terminalized, attempt `mark_create_unknown(..., error_class="CODEX_AMBIGUOUS")`;
- if it is already CREATE_UNKNOWN, return UNKNOWN;
- any other incompatible shape is finite application INVARIANT/STORAGE and no external retry occurs.

## START_REJECTED

Accepted P1.5 `START_REJECTED` is deterministic no-thread creation authority.

P3.2 performs:

`mark_create_error(..., error_class="CODEX_THREAD_FAILED")`

and returns application status `FAILED`, exact RECEIVED first job, exact ERROR dialogue, no output and no reason.

The RECEIVED job is not rewritten to a false Codex-turn FAILED state because no Codex turn ever existed and accepted P2 FAILED requires a bound thread.

## START_UNKNOWN

For accepted `START_UNKNOWN`, malformed/mismatched confirmed result, or any external-dispatch certainty that cannot be proven:

`mark_create_unknown(..., error_class="CODEX_AMBIGUOUS")`

and return application status `UNKNOWN`, exact RECEIVED first job, exact CREATE_UNKNOWN dialogue, no output and no reason.

No thread-start retry exists.

## Local pre-dispatch thread lifecycle errors

Exact P1.5 local/pre-dispatch categories:

- `THREAD_REQUEST_INVALID`;
- `THREAD_PRECONDITION_CHANGED`;
- `THREAD_OPERATION_BUSY`

are deterministic local failures and map to:

`mark_create_error(..., error_class="CODEX_PROCESS")`

with application status FAILED.

Unexpected exception/uncertain dispatch maps to CREATE_UNKNOWN / `CODEX_AMBIGUOUS`.

Raw adapter exception text is never persisted or rendered.

## Same-update and different-update concurrency

Same update:

- at most one live dialogue is created;
- at most one durable JOB ingress exists;
- at most one P1 thread/start occurs;
- at most one P1 turn/start occurs;
- replay after JOB admission is DUPLICATE with no new thread/turn effect.

Different updates racing no-dialogue state:

- at most one create intent wins the single live slot;
- at most one first prompt is admitted for that CREATING dialogue;
- the other request returns finite blocked/busy state and is not queued;
- it never auto-executes after the winner completes.

No in-memory delayed prompt queue is introduced.

## Pre-existing CREATING restart recovery

`recover_preexisting_creation()` is explicit startup recovery authority and must be called only before the controller begins serving new prompt execution.

It performs no P1 call.

If no live dialogue exists or the live dialogue is not CREATING:

- return `CreationRecoveryStatus.NO_ACTION` and the current dialogue (or None);
- make no mutation.

If a canonical live dialogue is CREATING:

- never call `thread/start` or `thread/resume`;
- atomically call `mark_create_unknown` with exact current version and `CODEX_AMBIGUOUS`;
- return `MARKED_UNKNOWN` plus the exact CREATE_UNKNOWN dialogue.

This rule applies whether a RECEIVED first job exists or not. After process restart the schema cannot prove whether the old thread/start was never dispatched, was dispatched and lost, or succeeded before the crash. Conservatively marking UNKNOWN is therefore the only safe V1 authority.

P3.2 does not provide CREATE_UNKNOWN retry/reset/reconcile.

## Restart boundaries

P3.2 must prove at minimum:

- crash/reopen after CREATING but before known external result -> explicit recovery marks CREATE_UNKNOWN, zero P1 effect;
- crash/reopen with CREATING + RECEIVED + INPUT -> same recovery result, preserving job/ingress/input evidence;
- confirmed local IDLE + RECEIVED crash window remains exact durable state and is NOT treated as a reason to recreate the thread; generic admitted-turn restart recovery remains a later P3 acceptance concern.

P3.2 does not create a background recovery scanner.

## Security

- prompt remains `repr=False` through the accepted request;
- INPUT/OUTPUT contents remain content-owning P2 payload fields only;
- no raw P1 errors, CODEX_HOME, DB path, stdout/stderr, environment or hidden reasoning enters generic application results/errors;
- create/recovery results contain no prompt/output text;
- tests use temporary SQLite and fake thread/catalog/turn/workdir ports only.

## Out of scope

P3.2 does not implement:

- profile/model/reasoning settings mutation;
- thread resume policy;
- CREATE_UNKNOWN reset/retry/reconcile;
- turn restart scanner/recovery policy;
- interrupt;
- hard delete;
- delivery planning/sending;
- approval Telegram UX;
- controller ACTIVE/SLEEP routing;
- Telegram auth/UI;
- real Codex acceptance;
- deployment;
- P3.3+.
