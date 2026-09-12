# P7.C14 retained real-failure forensic evidence — 2026-09-12

Status: **FORENSIC COMPLETE / REAL RUN CONSUMED / FAIL / READ-ONLY / NO CLEANUP**

## Authority

FORENSIC_BASE_HEAD=2676e4c9eeb3f343112d41c3307948599fc81837

FORENSIC_BASE_TREE=2abd7132c374c829ab683c3c0b4894ea4aa74b02

P7C14_EXECUTION_HEAD=e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1

P7C14_EXECUTION_TREE=7139a60357cae952c9f0da7b1c47d35cdd00b5bd

P7C14_REAL_EVIDENCE_BLOB=f06b469c8ea6afb5d6925a95c7de8f2293500544

INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c

The required `origin/main` commit and tree were verified before checkout. The forensic branch remains based directly on the consumed P7.C14 evidence head; no merge, rebase, or history rewrite was performed.

## Root-only ledger and boot correlation

The root-only P7.C14 ledger was read with bounded, stable-identity, no-follow semantics. It is a stable regular JSON file. Safe facts:

- terminal state: `FAILED`;
- schema class: `p7c13-repair4-v1`;
- source head/tree and inherited harness match the required execution authority;
- run identifier: valid SHA-256 hash class only;
- recovery authority: child-result hash class is SHA-256; parent-group scan error count is zero;
- ledger effect counts: empty exception-path object and not dispatch authority.

Exactly one retained boot authority matched all four binding conditions: execution source head, execution source tree, inherited harness blob, and the root-only ledger binding. Boot correlation is therefore unique and passed. Its derived child result was read read-only with stable identity.

## Child result safe readback

- status: `FAILED`;
- verdict: `false`;
- failure class: `FAIL_CLOSED`;
- terminal exception class: `TurnLifecycleError`;
- source head/tree/harness/run binding: all matched the correlated boot;
- runtime child quiescence: `true`;
- exception-path effect counts: explicitly untrusted.

The authoritative terminal result is ledger `FAILED` plus child `FAILED`; any parent exit-zero observation is not acceptance authority.

## Retained physical and protocol evidence

The exact correlated isolated SQLite authority was opened only in read-only mode. It retained four SQLite databases represented by twelve total descendants, including their journal/WAL sidecars. The isolated logs directory retained zero descendants. The protocol log database contained current-window activity from two runtime process identity hashes and one exact thread identity hash. The exact thread identity hash agreed with the correlated thread row.

The correlated thread row had:

- exact boot workdir binding;
- creation in the boot-to-child-result window;
- regular rollout file;
- persistent-session placement;
- no user-event flag at the thread-table level, while the rollout retained the correlated user/assistant turn record and terminal task event.

The retained rollout had one task-started event, one user message, one assistant message, one task-complete event, and no later P7.C14 turn prompt. Its content matched the first-turn remember/respond stage by safe marker classes only. No raw prompt, response, thread ID, or Turn ID is included here.

The protocol log sequence, reduced to safe facts, was:

1. `model/list` activity in the first runtime process identity;
2. `thread/start` activity in that same process identity;
3. exact thread row and rollout materialization;
4. `turn/start` dispatch and `turn/started` activity;
5. item completion and retained task completion for Turn 1;
6. a distinct second runtime process identity and `thread/resume` activity;
7. no second-generation `turn/start` dispatch before the failed child result.

The source execution order requires a confirmed Turn 1 before generation-1 shutdown, and requires confirmed resume before entering the second-turn start call. The correlated physical records therefore establish the boundary below without using the broken effect counters.

## Reconstructed stage matrix

| Stage | Classification | Safe basis |
|---|---|---|
| `INSTALLED_AUTHORITY_VERIFY` | `CONFIRMED` | Production runtime activity occurred after child authority validation boundary. |
| `RUNTIME_GENERATION_1_START_ACQUIRE` | `CONFIRMED` | First runtime process identity and successful downstream catalog/thread activity. |
| `MODEL_LIST` | `CONFIRMED` | Retained model/list activity and downstream valid catalog use. |
| `THREAD_START` | `CONFIRMED` | Thread/start activity plus exact correlated durable thread row. |
| `FRESH_THREAD_BINDING_MATERIALIZED` | `CONFIRMED` | One exact-workdir thread row, one rollout, and agreeing thread identity hash. |
| `TURN1_START` | `CONFIRMED` | Turn/start dispatch, turn-started activity, and correlated first-turn rollout. |
| `TURN1_TERMINAL` | `CONFIRMED` | Correlated task-complete event and assistant completion before generation change. |
| `RUNTIME_GENERATION_1_SHUTDOWN` | `CONFIRMED` | Second runtime identity appears only after the completed first-turn boundary. |
| `RUNTIME_GENERATION_2_ACQUIRE` | `CONFIRMED` | Distinct second runtime identity and subsequent resume activity. |
| `THREAD_RESUME` | `CONFIRMED` | Resume activity and source-required confirmed-resume predecessor to the second-turn call. |
| `TURN2_START` | `NOT_REACHED` | Second turn entered the adapter precondition boundary but emitted no turn/start RPC. |
| `TURN2_TERMINAL` | `NOT_REACHED` | Turn 2 start was not dispatched. |
| `TURN3_START` | `NOT_REACHED` | Source order places it after Turn 2 terminal. |
| `APPROVAL_REQUEST` | `NOT_REACHED` | Source order places approval construction after Turn 2 terminal; no root wire authority. |
| `APPROVAL_RESPONSE` | `NOT_REACHED` | No approval capture/journal authority and no response. |
| `TURN3_TERMINAL` | `NOT_REACHED` | Turn 3 was not started. |
| `TURN4_START` | `NOT_REACHED` | Source order places it after Turn 3 terminal. |
| `TURN4_INTERRUPT` | `NOT_REACHED` | Turn 4 was not started. |
| `CONTROLLER_DB_BINDING` | `NOT_REACHED` | Correlated controller DB is absent. |
| `OFFICIAL_THREAD_DELETE` | `NOT_REACHED` | No controller binding or official delete predecessor. |
| `APPLICATION_DELETE` | `NOT_REACHED` | No controller binding or delete-chain invocation. |
| `POST_DELETE_ORACLE` | `NOT_REACHED` | No delete stage was reached. |

## TurnLifecycleError recovery

Recovered category:

`TURN_PRECONDITION_CHANGED`

Narrow stage boundary:

`AFTER_THREAD_RESUME_CONFIRMED_BEFORE_TURN2_START_DISPATCH`

The exact execution source at `P7C14_EXECUTION_HEAD` shows that the first catalog is deliberately pinned to runtime generation 1. The second runtime is acquired after generation-1 shutdown. In `CodexTurnLifecycleAdapter.start_turn`, the second-turn pre-dispatch check raises `TurnLifecycleError(TURN_PRECONDITION_CHANGED)` when the acquired runtime generation differs from the pinned catalog generation. The retained two-process sequence, completed Turn 1, confirmed resume predecessor, and absence of a second turn/start dispatch establish this branch.

The remaining lifecycle categories are excluded by the retained boundary: no second turn/start request existed for rejected/unknown start categories; the fresh second adapter had no active turn for busy; valid inherited inputs and the already accepted first-turn binding exclude request-invalid; terminal, stream, and interrupt categories occur later or on a different stage. This is therefore a uniquely established source condition, not a class-name inference.

ROOT_CAUSE_CLASS=TURN_PRECONDITION_CHANGED

## Approval and delete reachability

The root-only current-run approval wire authority is `ABSENT`. The root-only approval recovery journal is `ABSENT`. The exact approval target is `ABSENT`. There was no approval response, no ALLOW, and no DENY.

Approval-related strings in retained application logs are static policy/context material and are not approval capture evidence. The frozen source constructs the approval operator only after Turn 2 terminal. Because the exact boundary is before Turn 2 start dispatch, and because the root authority creation point is later than that boundary, approval capture/journal, response, Turn 3, Turn 4, controller binding, official delete, application delete, and post-delete oracle were not reached.

The correlated controller DB is `ABSENT`; schema version, dialogue binding, dialogue state, and tombstone are consequently unavailable and not inferred.

## Orphan and durable-material matrix

P7C14_THREAD_SESSION=YES

PERSISTENT_SESSION_TARGET_COUNT=1

PERSISTENT_HISTORY_TARGET_COUNT=0

ISOLATED_SQLITE_DESCENDANTS=12

ISOLATED_LOG_DESCENDANTS=0

CONTROLLER_DB=ABSENT

APPROVAL_WIRE=ABSENT

APPROVAL_JOURNAL=ABSENT

APPROVAL_TARGET=ABSENT

OWNED_PROCESS_SURVIVORS=0

The one persistent-session target is correlated by exact workdir, creation-window authority, durable thread identity, and rollout content. It was not cleaned. If an architect later requires cleanup, that is a separate authorized operation; this forensic does not authorize it.

## Process forensic

Only `/proc` was inspected. No process was exactly correlated to the retained P7.C14 boot, isolated root, workdir, child-result authority, or run authority. Shared-home Codex processes were not classified as P7.C14 survivors and no process was signaled.

## Accounting defect proof

At the exact execution source, `ProductionRealChildOrchestrator` owns the live `child.budget`. The production path records effect reservations on that child-owned budget while executing. The normal path explicitly assigns `result_budget = child.budget` before serializing the child result.

The exception path in `_future_child_main()` instead serializes `_child_result_payload(boot, failure, budget)`, where `budget` is the separate outer zero-valued budget created before the production child is built. It does not serialize `child.budget`. Thus exception-path result counters can remain zero after real reservations and cannot establish dispatch history.

P7C14_FORENSIC_ACCOUNTING_DEFECT=CONFIRMED

## Parent exit defect proof

At the exact P7.C14 launcher source, `_module_main()` catches `P7C14PreparationGateError` and returns exit `2`. When the real entrypoint normally returns a failed watchdog result, the launcher falls through to `return 0`; it does not project failed watchdog, ledger, or child state to a nonzero exit.

P7C14_FORENSIC_PARENT_EXIT_DEFECT=CONFIRMED

## Successor requirements

P7.C15 preparation is not authorized by this report, and P7.C15 is not implemented here. Any future preparation must include all of the following:

1. Persist the actual live production child budget on the exception path.
2. Persist an explicit stage journal and last-confirmed-stage authority.
3. Retain the safe `TurnLifecycleError` category.
4. Make the parent CLI return nonzero for failed watchdog, ledger, or child state.
5. Use a distinct P7.C15 token, preparation gate, and ledger.
6. Never retry P7.C14.
7. If the root cause is used for offline preparation, add an exact zero-effect synthetic reproduction of this P7.C14 failure, including the generation-1 pinned catalog versus generation-2 runtime precondition mismatch.

## Zero-new-effect accounting

The forensic performed only fetch, ref verification, worktree checkout, bounded read-only file/protocol inspection, read-only SQLite opens, source inspection, `/proc` reads, and creation of this evidence document. No retained artifact was modified or cleaned.

NEW_CODEX_PROCESS_STARTS=0

APP_SERVER_STARTS=0

MODEL_LIST_CALLS=0

THREAD_START_CALLS=0

THREAD_RESUME_CALLS=0

THREAD_READ_CALLS=0

THREAD_LIST_CALLS=0

THREAD_DELETE_CALLS=0

TURN_START_CALLS=0

TURN_INTERRUPT_CALLS=0

APPROVAL_RESPONSES=0

ALLOW_RESPONSES=0

DENY_RESPONSES=0

TELEGRAM_CALLS=0

PROCESS_SIGNALS=0

PERSISTENT_HOME_MUTATIONS=0

ISOLATED_ROOT_MUTATIONS=0

CONTROLLER_MUTATIONS=0

LEDGER_MUTATIONS=0

BOOT_MUTATIONS=0

RESULT_MUTATIONS=0

WIRE_MUTATIONS=0

JOURNAL_MUTATIONS=0

P7C14_FORENSIC_BOOT_CORRELATION=PASS
P7C14_FORENSIC_REAL_EFFECT_BOUNDARY=ESTABLISHED
P7C14_FORENSIC_TURN_LIFECYCLE_CATEGORY=TURN_PRECONDITION_CHANGED
P7C14_FORENSIC_THREAD_MATERIALIZED=YES
P7C14_FORENSIC_DELETE_REACHED=NO
P7C14_FORENSIC_ACCOUNTING_DEFECT=CONFIRMED
P7C14_FORENSIC_PARENT_EXIT_DEFECT=CONFIRMED
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C15_PREPARATION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
