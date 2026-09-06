# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 retention-compatible replay correction accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 existing-dialogue application service is architect-accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; final full suite 543.
- P3.2 lazy first-dialogue/first-turn service is architect-accepted after one production repair at `c484c56db007569170363b3d08c24766148c3e30`; final full suite 566.
- P3.2 acceptance authority: `docs/evidence/p3/P3_2_ARCHITECT_ACCEPTANCE_2026-09-06.md`.
- ADR-0026, ADR-0027 and ADR-0028 remain binding accepted P3.1/P3.2 authority.
- ADR-0029 is binding P3.3 authority.

## Accepted P3.1/P3.2 application boundary

The accepted higher-level prompt path now supports both an existing canonical dialogue and lazy first-dialogue creation.

Existing dialogue:

`duplicate/static -> existing-dialogue preflight -> claim_ingress -> claim_turn -> CODEX_STARTING -> turn/start -> CODEX_RUNNING -> wait -> finish_codex`

No dialogue:

`duplicate/static -> no-dialogue preflight -> tombstone guard -> CREATING -> first JOB/RECEIVED/INPUT -> thread/start -> confirm IDLE -> same admitted job -> accepted turn runner`

P3.2 recovery converts any pre-existing CREATING dialogue to CREATE_UNKNOWN without repeating thread/start.

Different-update losers of the first-dialogue race are finite no-effect BUSY/BLOCKED results and never execute later as queued work.

## P3.3 objective

P3.3 adds a Telegram-agnostic profile/model/reasoning settings application service for later private management UI.

It must enforce the frozen rules:

- configured profiles come only from explicit configuration;
- profile is immutable for the lifetime of a live dialogue;
- profile mutation is legal only with NO_DIALOGUE;
- model/reasoning mutation is legal with NO_DIALOGUE or exact IDLE dialogue only;
- model/reasoning choices require authenticated model-list validation for the exact profile;
- every admitted job keeps its immutable captured profile/model/effort;
- expected settings version is optimistic concurrency authority;
- no retry/merge/queue exists.

## P3.3 public application additions

Add `SettingsSelectionService` with exact public callable surface:

- `get_view(*, refresh=False)`;
- `select_profile(profile_id, *, expected_version)`;
- `select_model(model_id, *, expected_version)`;
- `select_reasoning_effort(reasoning_effort, *, expected_version)`.

Add the frozen public records/enums defined by ADR-0029:

- `SettingsProfileOption(profile_id, display_name)`;
- `SettingsModelOption(model_id, display_name, supported_reasoning_efforts, default_reasoning_effort, is_default)`;
- `SettingsSelectionView(settings, dialogue_state, dialogue_profile_id, profiles, models, catalog_available)`;
- `SettingsMutationStatus = UPDATED | NO_CHANGE | BLOCKED | CONFLICT`;
- `SettingsMutationReason = SETTINGS_MISSING | PROFILE_NOT_CONFIGURED | PROFILE_LOCKED | DIALOGUE_NOT_IDLE | MODEL_NOT_CONFIGURED | MODEL_UNAVAILABLE | REASONING_EFFORT_UNSUPPORTED | STALE_SETTINGS`;
- `SettingsMutationResult(status, settings, reason)`;
- finite payload-free `SettingsSelectionError = INVALID_ARGUMENT | STORAGE | INVARIANT`.

Public settings projection must not contain CODEX_HOME, thread ID, wire model, raw catalog/runtime errors, credentials or content.

## Read/view authority

Profile options are explicit configured profile ID/display-name pairs only, preserving configuration order.

Effective profile for model discovery:

- live dialogue profile if a live dialogue exists;
- otherwise durable settings profile;
- otherwise none.

Authenticated model catalog is used only for an explicitly configured effective profile. Exact visible logical descriptors become safe model options. Catalog failure/profile mismatch/malformed catalog returns `catalog_available=False` and an empty model list without raw error leakage.

P3.3 does not initialize missing settings. Missing durable settings is a finite blocked mutation state; P2.2 startup bootstrap remains authority.

## Profile mutation authority

Unknown profile -> `BLOCKED / PROFILE_NOT_CONFIGURED`.

Exact same current profile + exact expected settings version -> `NO_CHANGE`; preserve model/reasoning.

A real profile change requires NO_DIALOGUE at the exact SQLite mutation point.

Successful profile change writes:

- requested profile;
- `model_id = NULL`;
- `reasoning_effort = NULL`;
- settings version +1 exactly once.

Any live dialogue in any state -> `BLOCKED / PROFILE_LOCKED`.

No profile change deletes/migrates/resumes a dialogue.

## Model/reasoning mutation authority

Both require the durable settings profile to be explicit configured authority and an authenticated refreshed catalog for that exact profile.

Model selection requires exact visible logical model and resets reasoning to that model's exact authenticated default effort.

Reasoning selection requires a current model and an exact concrete advertised effort.

Mutation is legal only at an atomic commit point with:

- NO_DIALOGUE; or
- exact IDLE live dialogue whose server/profile match this controller/settings profile.

Every other live state -> `BLOCKED / DIALOGUE_NOT_IDLE`.

Live dialogue/settings profile mismatch -> fail closed INVARIANT.

Same resulting tuple -> NO_CHANGE; actual update -> one version increment/one mutation clock.

No thread/start, turn/start, resume or other Codex side effect is part of settings mutation.

## Optimistic conflict authority

Every settings mutation requires the caller's exact expected durable settings version.

Stale version -> `CONFLICT / STALE_SETTINGS`.

No automatic reread-and-retry, merge or second write.

## Atomic SQLite settings/dialogue guard

P2.2 `SettingsRepository.replace` and `DialogueRepository.create_intent` remain accepted and semantically unchanged.

P3.3 may add one new narrow repository/module under `src/codex_control/storage/` using the accepted `SqliteStorage.write` transaction and the existing schema only.

It provides semantic operations equivalent to:

1. `replace_profile_no_dialogue` — exact settings/version, any live dialogue blocks, atomically change profile and clear model/effort;
2. `replace_selection_idle_or_no_dialogue` — exact settings/version/profile, allow no dialogue or exact matching IDLE only, atomically update model/effort;
3. `create_dialogue_if_settings_current` — exact settings version/profile/model/stored-effort snapshot and empty live slot must all still hold before atomically inserting canonical CREATING.

Expected repository conflict mapping follows ADR-0029. No DDL/schema/background lock/retry is authorized.

## P3.2 compatibility hardening required by P3.3

P3.3 introduces profile mutation, so P3.2 first-dialogue creation must now linearize against it.

During P3.2 lazy preflight retain the exact settings version/profile/model/stored reasoning value used for selection.

The owned first create must use the new guarded create primitive rather than an unguarded insert.

Race authority:

- guarded P3.2 create wins first -> concurrent different-profile mutation sees live dialogue and returns PROFILE_LOCKED;
- profile/settings mutation wins first -> stale P3.2 create returns no-effect `BLOCKED / SETTINGS_CHANGED` before dialogue/job/ingress/INPUT/P1 effect.

Add `SETTINGS_CHANGED` as one additive `ExistingDialogueTurnReason` member for this exact P3.2 compatibility result.

No retry/queue. Accepted P3.2 ALREADY_EXISTS no-queue reconstruction remains unchanged.

## Existing-dialogue prompt versus model/reasoning mutation

An already-running application invocation may have read its settings snapshot immediately before a concurrent model/reasoning update. It may continue to admission using that captured selection; once admitted, the durable job snapshot is immutable and remains the authority for that invocation.

The new mutation affects subsequent selection only and never rewrites an existing job.

Profile mutation is different: it can never commit while the live dialogue exists.

## Required P3.3 acceptance focus

Tests must materially prove:

- exact public callable/type surfaces and frozen records;
- CODEX_HOME/wire-model/thread-ID/raw-error redaction;
- explicit profile options and authenticated visible model options;
- catalog unavailable fail-closed view/mutation behavior;
- expected-version conflict and no retry;
- no-change paths do not write/increment/clock;
- profile change clears model/effort and is blocked by every live dialogue state;
- model/reasoning allowed at NO_DIALOGUE and exact IDLE only;
- all create/run/interrupt/delete/unknown/error states block model/reasoning;
- settings/dialogue profile mismatch fails closed;
- model selection resets to authenticated default effort;
- unsupported effort is blocked;
- same-version concurrent settings mutation has one winner;
- deterministic model/reasoning mutation vs turn claim preserves immutable job snapshot;
- deterministic P3.2/profile-mutation race in both orders;
- stale settings can never create a live dialogue on an old profile;
- live-dialogue creation can never be followed by profile mutation;
- accepted P3.2 no-queue repair remains green;
- schema-v1 DDL is unchanged;
- full P1/P2/P3.1/P3.2 regression remains green.

## P3 split

- **P3.1** — DONE, accepted existing-dialogue execution.
- **P3.2** — DONE, accepted lazy thread/start + first-turn orchestration/recovery.
- **P3.3** — NEXT, settings selection + authenticated catalog validation + atomic dialogue locks.
- **P3.4** — planned durable interrupt orchestration/recovery.
- **P3.5** — planned hard-delete orchestration + final P3 recovery/application acceptance.

## Out of scope for P3.3

No Telegram UI/callback wiring, ACTIVE/SLEEP routing, profile filesystem scanning, credential copy/mutation, thread resume, CREATE_UNKNOWN reset/retry, interrupt, hard delete, delivery, real Codex side effect, production state or deployment.

## Execution authority

Codex must not self-start work from this document.

Only **P3.3 — settings selection service + atomic dialogue/settings guards under ADR-0029** may be implemented from the next explicit architect prompt.