# P3.2 architect acceptance — lazy thread/start and first-turn orchestration

Date: 2026-09-06
Status: ARCHITECT_ACCEPTED

## Accepted implementation

Repository: `MaksimUnimax/CodexControl`

Original architect P3.2 base:

`6a1182a2db4486124875b1de2a6f11cbd12243e1`

Rejected initial P3.2 candidate:

`855722c0f013df7d89e23c30dbd2d1d32ff0ed99`

Accepted P3.2 first-repair HEAD:

`c484c56db007569170363b3d08c24766148c3e30`

Accepted P3.1 dependency:

`9e0a86b311bb63d6a36a4641cb588321987e1550`

Accepted P2.C1 dependency:

`4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`

Issue: #21.

Architect rejection/review comment: `5558625534`.

## Architect verification

Independent GitHub review verified the cumulative P3.2 implementation remains limited to `src/codex_control/application/**`, focused P3.2 tests and factual P3.2 evidence. Accepted P1/P2 production source, schema, DDL, adapter source, dependencies and deployment state were not modified.

The first repair from `855722c0...` to `c484c56...` changes only:

- `src/codex_control/application/dialogue_turn.py`;
- `tests/integration/test_lazy_dialogue_turn_application.py`;
- `docs/evidence/p3/P3_2_LAZY_THREAD_FIRST_TURN_EVIDENCE.md`.

Frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Accepted lazy-creation contract

`DialogueTurnService.execute()` preserves accepted P3.1 behavior for already-classified durable ingress and live-dialogue execution, and enters lazy creation only after exact `BLOCKED / NO_DIALOGUE`.

For a genuinely new first prompt the accepted order is:

1. no-dialogue/static/duplicate-first authority;
2. durable settings/profile/model/effort and trusted-workdir preflight;
3. bounded dialogue/job/INPUT IDs and INPUT retention deadline;
4. generated dialogue-ID deletion-tombstone collision check;
5. one caller-cancellation-owned creation task before the first mutation;
6. `DialogueRepository.create_intent` -> durable `CREATING`, null thread;
7. `TurnJobRepository.claim_ingress` -> durable JOB ingress + `RECEIVED` job + INPUT, still null thread;
8. exactly one P1.5 `thread/start` from the immutable admitted model/effort/workdir;
9. exact confirmed binding -> `confirm_created` -> local `IDLE` with exact thread ID;
10. shared accepted admitted-turn runner -> `claim_turn -> CODEX_STARTING -> turn/start -> CODEX_RUNNING -> wait -> finish_codex`.

No second ingress or second job is created for the first prompt.

## No-queue repair acceptance

The initial candidate was rejected because race-loser paths re-entered the effect-capable `ExistingDialogueTurnService.execute()` after losing the original no-dialogue race. A delayed different-update loser could therefore execute as a later second turn after the winner had already completed and returned the dialogue to `IDLE`.

The accepted repair removes that behavior.

- `create_intent -> ALREADY_EXISTS` uses explicit read-only race-loss reconstruction;
- `claim_ingress -> STATE_CONFLICT` uses the same no-effect reconstruction;
- `claim_ingress -> DUPLICATE` consumes the already-returned durable duplicate through duplicate-only accepted semantics;
- no race-loss helper claims a new job, creates INPUT, calls thread/start, calls turn/start, waits a turn or queues delayed work.

For an unseen race-lost update with no durable ingress:

- current `IDLE` or `TURN_RUNNING` -> `BUSY`;
- current non-ready live state -> `BLOCKED / DIALOGUE_NOT_READY`;
- no live dialogue -> `BLOCKED / NO_DIALOGUE`;
- incompatible/corrupt durable state -> fail-closed finite application invariant.

The deterministic repair proof pauses a different-update loser before `create_intent`, lets the winner fully create the thread, run the first turn and return the dialogue to `IDLE`, then releases the loser. The loser returns `BUSY` with zero ingress/job/INPUT/thread-start/turn-start/wait effects and no delayed execution.

## Thread/start terminal authority

The accepted implementation materially proves actual P1.5 result objects for:

- `START_REJECTED` -> dialogue `ERROR / CODEX_THREAD_FAILED`, application `FAILED`, first job remains `RECEIVED`, no turn effect;
- `START_UNKNOWN` -> dialogue `CREATE_UNKNOWN / CODEX_AMBIGUOUS`, application `UNKNOWN`, first job remains `RECEIVED`, no retry;
- malformed or mismatched `START_CONFIRMED` -> `CREATE_UNKNOWN / CODEX_AMBIGUOUS`, exactly one thread/start and no turn effect;
- exact local `THREAD_REQUEST_INVALID`, `THREAD_PRECONDITION_CHANGED`, `THREAD_OPERATION_BUSY` -> deterministic local `ERROR / CODEX_PROCESS`;
- unexpected/uncertain thread-lifecycle failures -> `CREATE_UNKNOWN / CODEX_AMBIGUOUS`.

A confirmed external thread is never blindly started again after a local confirmation failure. One local dialogue reread is used for exact reconciliation only.

## Tombstone and restart boundaries

Generated dialogue IDs are checked against accepted P2.5 deletion tombstone authority before create intent. Both canonical retained collisions and corrupt tombstone materialization fail closed with no admission, retry or Codex effect.

`recover_preexisting_creation()` remains explicit startup-only authority:

- no dialogue or any non-`CREATING` dialogue -> `NO_ACTION` with no effect;
- canonical pre-existing `CREATING` -> `CREATE_UNKNOWN / CODEX_AMBIGUOUS` through `mark_create_unknown`, zero P1 effect;
- existing JOB ingress / RECEIVED job / INPUT evidence is preserved;
- confirmed `IDLE + RECEIVED` is `NO_ACTION` and is not interpreted as authority to recreate or resume work.

No CREATE_UNKNOWN retry/reset/reconcile is introduced by P3.2.

## Concurrency and cancellation

Same-update concurrency is accepted with one live dialogue, one durable first job, one admitted first prompt and at most one thread/start and first turn effect. Replay after durable JOB admission is duplicate-only.

Different updates racing the no-dialogue path have one winner; the loser returns finite BUSY/BLOCKED/DUPLICATE state and never auto-executes after the winner completes.

After local durable admission, repeated public caller cancellation does not detach the owned orchestration. The accepted proof binds exactly one thread/start, one turn/start, one wait, one durable job and final `CODEX_COMPLETED` state on the successful fake path.

## Final proof counts

Accepted pre-P3.2 full suite: `543`.

P3.2 final focused counts:

- unit: `2`;
- integration: `21`.

Expected full:

`543 + 2 + 21 = 566`

Observed full discovery: `566` passing tests.

Accepted P3.1 regression remains `11 / 26`. Accepted P2.C1 remains `5 / 1`; P2.6b remains `5 / 12 / 8 / 3`; prior P2 focused suites and P1.10 `6 / 1 / 4` remain green as reported by the executor evidence.

The known historical P1.6 pending-task warning remains pre-existing and is not attributed to P3.2.

## Security / external effects

Architect review found no accepted P1/P2 production change, schema/DDL drift, new dependency, credential or secret surface, raw prompt/output logging, production CODEX_HOME access, production DB access, service mutation or deployment effect in P3.2.

Tests use temporary SQLite and fake catalog/thread/turn/workdir ports only. No real Codex, Telegram or production network effect occurred.

## Decision

P3.2 is architect-accepted at:

`c484c56db007569170363b3d08c24766148c3e30`

Issue #21 may be closed completed.

The next eligible roadmap slice is P3.3 — profile/model/reasoning application settings service. P3.3 requires separate architect authority before implementation.