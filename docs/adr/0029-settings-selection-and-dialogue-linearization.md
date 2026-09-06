# ADR-0029 — Settings selection and dialogue linearization

Status: accepted
Date: 2026-09-06

## Context

P3.2 is architect-accepted at `c484c56db007569170363b3d08c24766148c3e30` and provides lazy first-dialogue creation plus accepted existing-dialogue execution.

V1 now needs the Telegram-agnostic application service that will later back the private profile/model/reasoning UI.

The frozen product rules are:

- configured profiles are explicit non-secret configuration, never production filesystem discovery;
- a live dialogue is permanently bound to one profile for its lifetime;
- profile change is allowed only when there is no live dialogue;
- model/reasoning are next-turn settings and may change only with no dialogue or while the live dialogue is exactly IDLE;
- model/reasoning selection must be validated against authenticated app-server `model/list` for the exact profile;
- every admitted turn keeps its immutable profile/model/effort snapshot even if durable next-turn settings change later;
- no automatic retry/queue is introduced by settings mutation.

P2.2 already exposes `SettingsRepository.get/initialize_if_absent/replace`, but `get_live()` followed by `SettingsRepository.replace()` is not enough to enforce the dialogue lock. Another operation can change dialogue state between those two transactions.

There is also a more important first-dialogue race. A lazy P3.2 request can read settings for profile A and pause before `create_intent`. If settings are then changed to profile B while no dialogue exists, the old P3.2 invocation could otherwise create a live dialogue permanently bound to A while durable settings already say B. That mismatch is not an acceptable linearization.

Therefore P3.3 needs one narrow additive storage coordination primitive. No schema or migration change is required.

## Scope

P3.3 owns:

1. safe settings/profile/model/reasoning read projection for later private Telegram UI;
2. profile mutation with the no-live-dialogue lock;
3. model mutation with authenticated catalog validation and the no-dialogue/IDLE lock;
4. reasoning-effort mutation with authenticated catalog validation and the same lock;
5. optimistic settings-version conflict handling;
6. atomic SQLite linearization between profile mutation and P3.2 first-dialogue creation.

P3.3 does not implement Telegram, ACTIVE/SLEEP routing, thread resume, interrupt, delete, delivery, CREATE_UNKNOWN reset, real Codex acceptance or deployment.

## Public application surface

Add Telegram-agnostic `SettingsSelectionService` with exact public callable surface:

- `get_view(*, refresh: bool = False)`;
- `select_profile(profile_id, *, expected_version)`;
- `select_model(model_id, *, expected_version)`;
- `select_reasoning_effort(reasoning_effort, *, expected_version)`.

Public application records are frozen and content/secret free.

### SettingsProfileOption

Exact fields:

- `profile_id`;
- `display_name`.

`codex_home` is deliberately absent.

### SettingsModelOption

Exact fields:

- `model_id` — logical authenticated model ID;
- `display_name`;
- `supported_reasoning_efforts`;
- `default_reasoning_effort`;
- `is_default`.

The wire model is deliberately absent.

### SettingsSelectionView

Exact fields:

- `settings` (`SettingsRecord | None`);
- `dialogue_state` (`DialogueState | None`);
- `dialogue_profile_id` (`str | None`);
- `profiles` (`tuple[SettingsProfileOption, ...]`);
- `models` (`tuple[SettingsModelOption, ...]`);
- `catalog_available` (`bool`).

The view does not expose thread ID, CODEX_HOME, wire model, raw catalog/runtime errors, prompt/output content or credentials.

### SettingsMutationStatus

Exactly:

- `UPDATED`;
- `NO_CHANGE`;
- `BLOCKED`;
- `CONFLICT`.

### SettingsMutationReason

Exactly:

- `SETTINGS_MISSING`;
- `PROFILE_NOT_CONFIGURED`;
- `PROFILE_LOCKED`;
- `DIALOGUE_NOT_IDLE`;
- `MODEL_NOT_CONFIGURED`;
- `MODEL_UNAVAILABLE`;
- `REASONING_EFFORT_UNSUPPORTED`;
- `STALE_SETTINGS`.

### SettingsMutationResult

Frozen exact fields:

- `status`;
- `settings` (`SettingsRecord | None`);
- `reason` (`SettingsMutationReason | None`).

### SettingsSelectionError

Finite payload-free application error with exact categories:

- `INVALID_ARGUMENT`;
- `STORAGE`;
- `INVARIANT`.

Raw repository/catalog/runtime/config path text is never rendered.

## Read projection

`get_view()` reads the durable settings and current live dialogue.

Profile options come only from the explicit configured `tuple[CodexProfile, ...]`, preserving configured order. Each option contains only `profile_id` and `display_name`.

The effective profile used for model discovery is:

- the live dialogue profile if a live dialogue exists;
- otherwise the durable settings profile;
- otherwise no effective profile.

If a live dialogue exists and its server/profile shape conflicts with the explicit controller/config authority, fail closed with application `INVARIANT`.

If the effective profile is not explicitly configured, do not probe arbitrary paths; return `catalog_available=False` and no model options.

For an explicitly configured effective profile, query the authenticated model catalog using the injected P1.4-compatible `ModelCatalogPort`, honoring the caller's `refresh` flag.

Only exact visible normalized descriptors become `SettingsModelOption` values. A catalog failure, malformed catalog, profile mismatch or otherwise unavailable catalog produces:

- `catalog_available=False`;
- `models=()`;
- no raw exception text.

The read view does not mutate settings/dialogue state.

## Settings bootstrap boundary

P3.3 does not own startup initialization.

If the durable settings singleton is absent, mutations return `BLOCKED / SETTINGS_MISSING`. The accepted P2.2 `initialize_if_absent` remains startup/config bootstrap authority.

## Expected-version authority

Every mutation requires an exact non-negative signed-64 `expected_version` supplied from the caller's current settings view.

A version mismatch returns:

`CONFLICT / STALE_SETTINGS`.

No merge, refresh-and-retry or automatic second mutation exists.

A successful mutation increments the durable settings version exactly once. A true no-change result performs no write, no version increment and no mutation clock call.

## Profile selection

`select_profile(profile_id, expected_version=...)` accepts only an exact explicitly configured profile ID.

Unknown/unconfigured profile:

`BLOCKED / PROFILE_NOT_CONFIGURED`.

Profile selection itself is configuration authority and does not require a successful model-list call. Authenticated model eligibility is established when reading/selecting model/reasoning and again before turn execution.

If the requested profile equals the current settings profile, return `NO_CHANGE` with the current settings after exact expected-version validation. Existing model/reasoning values are preserved.

If the profile differs, the mutation is legal only when there is no live dialogue at the exact SQLite commit point.

A successful profile change writes:

- `profile_id = requested profile`;
- `model_id = NULL`;
- `reasoning_effort = NULL`.

Old model/reasoning values are not carried across profiles.

Any live dialogue in any canonical state blocks an actual profile change:

`BLOCKED / PROFILE_LOCKED`.

No dialogue is deleted, migrated, resumed or rewritten.

## Model selection

`select_model(model_id, expected_version=...)` requires:

- durable settings exist;
- settings profile is non-NULL and explicitly configured;
- authenticated refreshed catalog belongs to that exact profile;
- requested logical model exists and is visible;
- descriptor default reasoning effort is canonical and advertised.

Catalog/model failure returns:

`BLOCKED / MODEL_UNAVAILABLE`.

The model mutation is legal only when, at the exact SQLite commit point:

- no live dialogue exists; or
- the live dialogue is exactly `IDLE`, belongs to this server, and its immutable profile equals the settings profile.

Any other live dialogue state returns:

`BLOCKED / DIALOGUE_NOT_IDLE`.

A live dialogue/settings profile mismatch is application/storage invariant corruption, not a mutation opportunity.

A successful model selection writes the requested logical model ID and resets reasoning to that authenticated descriptor's exact default reasoning effort. This deterministic reset avoids carrying a stale effort across models.

If model and resulting default effort already equal the durable settings tuple, return `NO_CHANGE` after exact expected-version validation.

No Codex thread/turn effect occurs.

## Reasoning selection

`select_reasoning_effort(reasoning_effort, expected_version=...)` requires:

- durable settings and configured profile;
- non-NULL current model;
- authenticated refreshed catalog for the exact profile;
- exact current model is visible;
- requested concrete non-NULL effort is advertised for that model.

Missing current model returns:

`BLOCKED / MODEL_NOT_CONFIGURED`.

Unavailable catalog/model returns:

`BLOCKED / MODEL_UNAVAILABLE`.

Unsupported effort returns:

`BLOCKED / REASONING_EFFORT_UNSUPPORTED`.

The same no-dialogue-or-exact-IDLE atomic dialogue guard as model selection applies.

If the requested effort already equals durable settings effort, return `NO_CHANGE` after exact expected-version validation.

No Codex thread/turn effect occurs.

## Atomic storage coordination

Add one narrow repository/module under `src/codex_control/storage/` for cross-table settings/dialogue guards. It must use the accepted `SqliteStorage.write` transaction primitive and existing schema only.

Do not change the semantics of accepted `SettingsRepository.replace` or `DialogueRepository.create_intent`.

The new storage authority exposes exact semantic operations equivalent to:

1. `replace_profile_no_dialogue(...)`
   - exact settings row/version;
   - reject any live dialogue;
   - atomically replace profile and clear model/effort.

2. `replace_selection_idle_or_no_dialogue(...)`
   - exact settings row/version/profile;
   - allow no dialogue or exact IDLE dialogue with matching server/profile;
   - reject every create/run/interrupt/delete/unknown/error state;
   - atomically replace model/effort while preserving profile.

3. `create_dialogue_if_settings_current(...)`
   - exact settings row/version and exact preflight profile/model/stored reasoning tuple must still match;
   - live dialogue slot must still be empty;
   - then atomically insert the same canonical CREATING dialogue shape as accepted `create_intent`.

Use existing finite `RepositoryErrorCategory` values. Expected mappings:

- missing settings -> `NOT_FOUND`;
- stale settings snapshot -> `VERSION_CONFLICT`;
- illegal dialogue state for setting mutation -> `STATE_CONFLICT`;
- existing live dialogue on guarded create -> `ALREADY_EXISTS`;
- noncanonical stored cross-table shape -> `INVARIANT_VIOLATION`.

No schema/DDL, retry policy or background lock is introduced.

## P3.2 first-create compatibility guard

P3.2 must be narrowly hardened because P3.3 introduces concurrent profile mutation.

During lazy preflight P3.2 already reads the exact `SettingsRecord`. It must retain:

- `settings.version`;
- `settings.profile_id`;
- `settings.model_id`;
- the stored `settings.reasoning_effort` value, separately from the concrete catalog-resolved effort persisted into the job.

The owned create path must use `create_dialogue_if_settings_current(...)` instead of an unguarded first-dialogue insert.

Linearization rule:

- if P3.2 guarded create commits first, a concurrent different-profile mutation sees the live dialogue and returns `PROFILE_LOCKED`;
- if profile/settings mutation commits first, the stale P3.2 create fails before creating a dialogue, job, ingress, INPUT or P1 effect.

A stale P3.2 settings snapshot returns the existing P3 turn-result shape:

- status `BLOCKED`;
- new additive reason `SETTINGS_CHANGED`;
- no durable job/dialogue created by that invocation;
- no retry and no queue.

Add `SETTINGS_CHANGED` as an additive `ExistingDialogueTurnReason` member. Existing P3.1 statuses/reasons/behavior remain unchanged.

The accepted P3.2 `ALREADY_EXISTS` and no-queue race-loss semantics remain unchanged and still use read-only reconstruction.

## In-flight existing-dialogue prompt semantics

P3.3 does not retarget an already-running application invocation.

An existing-dialogue prompt may have read a valid settings snapshot immediately before a concurrent model/reasoning mutation. If that prompt is subsequently admitted, its durable job snapshot remains authoritative for that invocation. The settings mutation affects later selection only.

Once a job is admitted, later settings changes never rewrite its profile/model/effort.

This is intentional and does not create a delayed prompt queue.

Profile differs: because dialogue profile is immutable, profile mutation is never allowed while that live dialogue exists.

## Cancellation

Settings reads and pre-validation have no business side effect and ordinary cancellation may propagate.

The SQLite setting mutation itself is one accepted owned transaction. P3.3 introduces no external side-effect ownership problem because model-list is read-only and no Codex thread/turn mutation exists.

No automatic retry follows cancellation or repository conflict.

## Security

- no CODEX_HOME in generic public view/result/error repr;
- no wire model in public view/result/error repr;
- no thread ID in settings view;
- no auth material, raw model-list response, raw adapter exception, DB path or environment dump;
- explicit profile display names and logical model metadata are allowed UI data;
- all mutation/result types are content-free.

## Required acceptance focus

P3.3 tests must materially prove:

- public type/callable surface and frozen records;
- explicit profile-only projection and CODEX_HOME redaction;
- authenticated visible model projection and wire-model redaction;
- missing/unavailable catalog behavior;
- expected-version conflict/no retry;
- profile same-value NO_CHANGE;
- profile change clears model/effort;
- profile change blocked by every live dialogue state;
- model/reasoning allowed with no dialogue and exact IDLE;
- model/reasoning blocked by every other live dialogue state;
- live settings/dialogue profile mismatch fails closed;
- model selection resets to authenticated default effort;
- unsupported effort blocked;
- one mutation clock and one version increment only on actual update;
- concurrent same-version mutation has one winner;
- model/reasoning mutation versus claim-turn has a deterministic SQLite ordering and never changes an admitted immutable job snapshot;
- P3.2 stale-settings create race in both orders;
- no stale-profile dialogue can be created after a winning profile mutation;
- no profile mutation can commit after a winning live-dialogue create;
- P3.2 accepted no-queue races remain green;
- no P1 thread/turn side effect from settings service;
- no schema/DDL drift and all prior P1/P2/P3.1/P3.2 regressions remain green.

## Out of scope

No Telegram UI/callback token wiring, controller routing, interrupt, hard delete, delivery, profile filesystem scanning, credential mutation/copy, thread resume, CREATE_UNKNOWN retry/reset, real Codex side effect, service/deployment change or P3.4+ work is authorized.