# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 retention-compatible replay correction accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 corrected existing-dialogue application service is architect-accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550` after one proof-only repair.
- P3.1 final full suite: `543` passing tests (`506 + 11 unit + 26 integration`).
- P3.1 acceptance authority: `docs/evidence/p3/P3_1_ARCHITECT_ACCEPTANCE_2026-09-06.md`.
- ADR-0026 + ADR-0027 remain binding accepted P3.1/replay authority.
- ADR-0028 is binding P3.2 authority.

## Accepted P3.1 boundary
P3.1 owns an already-existing canonical IDLE dialogue only. Its accepted order is:

`static validation -> ingress duplicate-first -> existing-dialogue preflight -> claim_ingress -> reread dialogue -> claim_turn -> CODEX_STARTING -> P1 turn/start -> CODEX_RUNNING -> P1 wait -> finish_codex`

P3.1 provides no lazy thread creation, no settings mutation, no interrupt, no hard-delete orchestration and no restart scanner.

## P3.2 objective
P3.2 adds the no-dialogue lazy first-prompt path without changing accepted P1/P2 semantics or P3.1 public behavior.

The new higher-level `DialogueTurnService` reuses `ExistingDialogueTurnService` for all already-classified/existing-dialogue paths and enters lazy creation only after the existing service returns exactly `BLOCKED / NO_DIALOGUE`.

P3.2 also owns one explicit startup recovery operation for a pre-existing `CREATING` dialogue. It never retries an old `thread/start` after restart.

## P3.2 exact durable creation order
For a genuinely new first prompt with no live dialogue:

1. P3.1-compatible duplicate/static check has already found no ingress and no dialogue.
2. Resolve durable settings profile/model, explicit configured profile, authenticated non-hidden model + concrete effort, and trusted working directory.
3. Generate bounded opaque dialogue/job/INPUT IDs and one-hour INPUT expiry.
4. Start one cancellation-owned lazy-creation task before submitting the first local mutation.
5. `DialogueRepository.create_intent` -> durable `CREATING`, `thread_id=NULL`.
6. `TurnJobRepository.claim_ingress` against that exact CREATING dialogue with `thread_id=None` -> durable JOB ingress + RECEIVED job + INPUT.
7. Only now call exactly one P1.5 `thread/start` using the immutable job profile/model/effort and resolved workdir.
8. Exact `START_CONFIRMED` binding -> `DialogueRepository.confirm_created` -> IDLE with exact thread ID.
9. Reuse the accepted admitted-turn runner on the already-created RECEIVED job. `claim_turn` binds the formerly NULL job thread ID and continues accepted P3.1 turn semantics.

No second ingress/job is created for the first prompt.

## Thread/start terminal authority
- Exact `START_CONFIRMED` requires exact profile binding and exact returned logical model/concrete effort match. Then confirm the local dialogue and continue the first turn.
- `START_REJECTED` -> `mark_create_error(..., CODEX_THREAD_FAILED)` and application FAILED. The first job remains RECEIVED because no Codex turn existed.
- Exact local/pre-dispatch `THREAD_REQUEST_INVALID`, `THREAD_PRECONDITION_CHANGED`, `THREAD_OPERATION_BUSY` -> `mark_create_error(..., CODEX_PROCESS)` and FAILED.
- `START_UNKNOWN`, malformed/mismatched confirmed result, unexpected/uncertain exception -> `mark_create_unknown(..., CODEX_AMBIGUOUS)` and UNKNOWN.
- No thread-start retry exists.

If external start is confirmed but local confirmation does not return normally, read the dialogue once: exact already-confirmed IDLE may continue; exact remaining CREATING is terminalized to CREATE_UNKNOWN when possible; incompatible durable state is a finite application failure. Never issue a second thread/start.

## P3.2 duplicate/concurrency authority
Same update:
- at most one live dialogue;
- at most one JOB ingress/job/INPUT;
- at most one thread/start;
- at most one first turn/start;
- replay after JOB admission is accepted duplicate with no new effect.

Different updates racing no dialogue:
- at most one create intent / first prompt wins;
- the other returns finite duplicate/busy/blocked state;
- no delayed queue and no later automatic execution.

If `create_intent` loses `ALREADY_EXISTS`, or first-path `claim_ingress` loses a race, P3.2 performs no thread effect and re-evaluates through accepted current-state/duplicate authority once. No retry loop.

## P3.2 restart recovery authority
Schema-v1 has no durable discriminator between a CREATING dialogue immediately before thread/start dispatch and the same CREATING shape after an ambiguous crash during/after dispatch.

Therefore `DialogueTurnService.recover_preexisting_creation()` is explicit startup-only authority:

- no dialogue or non-CREATING dialogue -> `NO_ACTION`, no mutation/effect;
- canonical pre-existing CREATING -> atomically `mark_create_unknown(..., CODEX_AMBIGUOUS)` and return `MARKED_UNKNOWN`;
- never call thread/start, resume or delete during recovery;
- preserve any RECEIVED first job/JOB ingress/INPUT evidence;
- no CREATE_UNKNOWN retry/reset/reconcile in P3.2.

The method must be invoked only before the controller starts serving prompt execution; it is not a background scanner.

## Public P3.2 additions
- `ThreadLifecyclePort` with `start` only.
- `CreationRecoveryStatus`: `NO_ACTION`, `MARKED_UNKNOWN`.
- frozen `CreationRecoveryResult(status, dialogue)`.
- `DialogueTurnService` with exact public callable surface: `execute`, `recover_preexisting_creation`.

P3.2 reuses the accepted `ExistingDialoguePromptRequest`, `ExistingDialogueTurnResult`, status/reason enums and finite `DialogueApplicationError` boundary.

## Internal reuse authority
P3.2 may narrowly refactor private/internal code under `src/codex_control/application/**` so P3.1 and P3.2 share authenticated selection and the admitted-turn runner.

P3.1 public API and all accepted P3.1 behavior/tests must remain unchanged. No P1 adapter or P2 storage/repository production change is authorized.

## P3 split
- **P3.1** — DONE, accepted existing-dialogue prompt execution.
- **P3.2** — NEXT, lazy thread/start + first-turn orchestration + create restart boundary.
- **P3.3** — planned profile/model/reasoning settings service.
- **P3.4** — planned durable interrupt orchestration/recovery.
- **P3.5** — planned hard-delete orchestration + final P3 recovery/application acceptance.

## Out of scope for P3.2
No settings mutation, profile mutation, thread resume policy, CREATE_UNKNOWN reset/retry, generic turn restart scanner, interrupt, hard delete, delivery send, Telegram, controller ACTIVE/SLEEP routing, real Codex acceptance, production state or deployment.

## Execution authority
Codex must not self-start work from this document.

Only **P3.2 — lazy thread/start + first-turn orchestration and create recovery boundary** may be implemented from the next explicit architect prompt.