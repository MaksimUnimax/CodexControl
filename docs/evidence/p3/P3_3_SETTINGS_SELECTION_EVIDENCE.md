# P3.3 settings selection implementation evidence

Status: implementation evidence only; this document does not claim architect acceptance.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Issue: `#25 — P3.3 — settings selection + authenticated catalog + atomic dialogue locks`
- Architect base: `fc0d57e665f0aad8044934b24396de7d07ee56ef`
- Accepted P3.2: `c484c56db007569170363b3d08c24766148c3e30`
- Binding ADR: `docs/adr/0029-settings-selection-and-dialogue-linearization.md`
- Frozen DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Public application contract

`SettingsSelectionService` is Telegram-agnostic and exposes exactly `get_view`, `select_profile`, `select_model`, and `select_reasoning_effort`. Public frozen records are `SettingsProfileOption`, `SettingsModelOption`, `SettingsSelectionView`, and `SettingsMutationResult`. Statuses are `UPDATED`, `NO_CHANGE`, `BLOCKED`, and `CONFLICT`; mutation reasons are the eight finite ADR-0029 reasons. `SettingsSelectionError` exposes only `INVALID_ARGUMENT`, `STORAGE`, or `INVARIANT`.

Profile options contain only profile ID and display name. The configured profile tuple is the sole profile authority and configured order is preserved. `CODEX_HOME` is not projected. Model options contain only the logical authenticated model ID, display metadata, the exact advertised effort tuple, the advertised default, and default status. Wire model values and raw descriptors are not projected.

`get_view` reads durable settings and the live dialogue without initialization or mutation. It uses the live profile when present, otherwise the durable configured profile, and fails closed for catalog errors, malformed catalogs, profile mismatch, hidden models, or unavailable catalogs. Mutation catalog reads always use `refresh=True`; view reads honor the caller refresh flag.

## Selection and locking semantics

- Missing settings are `BLOCKED / SETTINGS_MISSING`; P3.3 never calls `initialize_if_absent`.
- Every mutation validates an exact non-negative signed-64 expected version before catalog work. Stale versions are `CONFLICT / STALE_SETTINGS` with no retry or merge.
- Same-value profile selection preserves model/reasoning/version and calls no mutation clock. A real profile change is atomically allowed only with no live dialogue and clears model and reasoning while incrementing settings version once.
- Model selection resolves an exact visible logical ID from the refreshed authenticated catalog and stores its advertised default effort. Selecting the same model with its already-stored authenticated default is `NO_CHANGE`; selecting the same model with a non-default effort is a real reset mutation.
- Reasoning selection accepts only an exact advertised effort for the current visible authenticated model. Same-value reasoning selection is `NO_CHANGE`; unsupported efforts and unavailable catalogs are finite blocked results.
- Model/reasoning real mutations are atomically allowed only with no dialogue or an exact matching `IDLE` dialogue. Every other live state is blocked as `DIALOGUE_NOT_IDLE`. Cross-profile settings/dialogue state is an invariant.

Profile mutation is blocked for `CREATING`, `IDLE`, `CREATE_UNKNOWN`, `ERROR`, `TURN_RUNNING`, `INTERRUPTING`, `TURN_UNKNOWN`, `DELETE_PENDING`, `DELETING`, and `DELETE_UNKNOWN`. Model/reasoning mutation is allowed for no dialogue and matching `IDLE`, and blocked for the other nine states.

## Atomic storage guards

The additive `SettingsDialogueGuardRepository` uses one `SqliteStorage.write` transaction and the existing schema only. It provides:

1. `replace_profile_no_dialogue`: checks settings existence/version, proves the live slot is empty, then clocks once and clears model/reasoning while incrementing version once.
2. `replace_selection_idle_or_no_dialogue`: checks settings/version/profile and atomically permits no dialogue or exact server/profile `IDLE`, then clocks once and updates model/reasoning.
3. `create_dialogue_if_settings_current`: checks the exact settings version and preflight tuple, proves the live slot is empty, then inserts the canonical P2.2 `CREATING` row and clocks once.

Repository failures remain finite (`NOT_FOUND`, `VERSION_CONFLICT`, `STATE_CONFLICT`, `ALREADY_EXISTS`, `INVARIANT_VIOLATION`, `INVALID_ARGUMENT`, and `CLOCK_INVALID`) and do not expose SQL or row content.

## P3.2 compatibility and races

P3.2 retains the preflight settings version, profile, model, and stored nullable reasoning value separately from the concrete catalog-resolved effort. Its first create now uses `create_dialogue_if_settings_current`.

- Profile-mutation-wins: the profile update commits version `N+1`, clears model/reasoning, and the paused old create returns `BLOCKED / SETTINGS_CHANGED` before dialogue, ingress, job, INPUT, thread/start, or turn/start effects.
- P3.2-create-wins: the guarded `CREATING` insert commits first, so profile mutation returns `BLOCKED / PROFILE_LOCKED`; normal P3.2 completion then preserves one profile on both settings and dialogue.
- Guarded `ALREADY_EXISTS`, accepted state-conflict, duplicate, and no-queue behavior remain read-only race-loss paths.

An admitted existing-dialogue job retains its old profile/model/effort snapshot when later settings selection legally changes next-turn settings during `IDLE`. The external turn-start fake receives the old snapshot. Once the dialogue is `TURN_RUNNING`, model/reasoning mutation is blocked.

## Effects and security

P3.3 itself calls no thread, turn, interrupt, delete, resume, Telegram, network, authentication-file, production-state, or production-database operation. Public repr/error checks cover `CODEX_HOME`, wire-model, thread ID, catalog-error, clock-error, credential, and content redaction. No schema file or DDL statement changed.

## Verification

- New P3.3 tests: 4 unit and 16 integration.
- P3.2 regression: 2 unit and 21 integration.
- P3.1 regression: 11 unit and 26 integration.
- P2.C1: 5 integration and 1 acceptance.
- P2.6b: 5 contract, 12 restart, 8 replay, 3 abrupt.
- P1.10: 6 T0, 1 T1, 4 T2.
- Full discovery: 586 passed.
- Formula: `566 + 4 + 16 = 586`.
- `compileall`, package import, and `git diff --check` passed.

The P3.2 integration patch boundary was moved from the old unguarded `DialogueRepository.create_intent` boundary to the new guarded-create boundary. The accepted P3.1 enum assertion was updated only to include the required additive `SETTINGS_CHANGED` value; existing P3.1 behavior and count remain unchanged.

Scope is limited to the P3.3 application/storage implementation, the required P3.2 compatibility path, focused tests, and this evidence file. Telegram UI and all later roadmap work remain out of scope.
