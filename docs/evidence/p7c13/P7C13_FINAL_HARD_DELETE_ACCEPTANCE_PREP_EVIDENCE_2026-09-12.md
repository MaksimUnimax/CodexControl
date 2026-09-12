# P7.C13 final hard-delete acceptance preparation — Repair-2 evidence

Status: **REPAIR-2 PREPARATION ONLY / ZERO REAL EFFECT / NO REAL AUTHORIZATION**

## Lineage and scope

- branch: `prep-p7-c13-final-hard-delete-acceptance-repair2-2026-09-12`
- `REPAIR2_BASE_HEAD=e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`
- Repair-1 harness blob: `82a7f3c1e31456205fb316eb4e692973dc3d0361`
- Repair-2 harness blob before commit: `10ba4084a086a597c892a2fef8409d6c46986062`
- Repair-2 evidence blob: recorded by final remote readback
- base tree: `9277d950691e9e2186f82b8ab4111885372e9f2d`
- architect `origin/main`: `d425b1e1512d9a579df0d4a304fe9c6bf51da21f`
- architect `origin/main` tree: `80f7bfeb5737016195e8f9a06059b5cefe71e8dd`
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1` (unchanged)
- helper: none
- changed tracked paths: this evidence file and `tests/real/test_p7_c13_final_hard_delete_acceptance.py` only

No `src/**`, P7.C12 matcher, historical P7.C6–P7.C12 file, schema/migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP file changed. The pre-existing untracked `tests/real/__init__.py` was preserved and not staged.

## Child dispatch and boot authority

The module now has a dedicated `--p7c13-future-child --boot-authority <path>` dispatcher. That path calls `_future_child_main()` and never enters unittest. Ordinary unittest invocation calls unittest and cannot enter the child dispatcher. Missing boot path is a finite failure before installed/runtime/business construction.

`RootOnlyBootAuthority` uses a bounded `p7c13-repair2-boot-v1` schema, exclusive creation, regular root-owned mode `0600`, nlink-one/no-symlink checks, duplicate-key rejection, no-follow reads, stable device/inode validation and bounded field/effect-ceiling validation. The record binds source HEAD/TREE, accepted harness blob, run hash, shared `/root/.codex_second`, fresh isolated root, controller DB, workdir, approval target, ledger, child result, contract hash and exact frozen effect ceilings. Synthetic tests cover missing, malformed, duplicate-key, symlink, mode, identity drift and source-authority mismatch before effects.

`P7C13_REPAIR2_CHILD_DISPATCH_PREPARED=YES`
`P7C13_REPAIR2_BOOT_AUTHORITY_PREPARED=YES`

## Parent and child authority

The exact future parent order is proven as:

`exact gate PASS -> exclusive durable ledger reservation -> root-only boot creation/readback -> child factory/watchdog`

The parent passes only the boot path/descriptor reference to its one child. A consumed ledger rejects a second invocation before child factory/watchdog entry. The parent-owned watchdog uses one dedicated session/process group and bounded owned-group termination; it has no retry or second-child path.

`_future_child_main()` reads and validates boot authority, constructs the bound `CodexProfile` and shared-home/isolated routing, verifies installed version/schema authority, constructs the runtime seam, and then executes `CompleteFutureChildOrchestrator`. The complete synthetic traversal is present in exact source:

`model/list -> thread/start -> Turn 1 observed response marker -> owned shutdown -> new generation/thread resume -> Turn 2 observed memory marker -> Turn 3 capture and P7.C12 exact matcher -> one response/ALLOW -> target postcondition and exact cleanup -> Turn 4 active sleep/interrupt -> owned shutdown -> pre-delete physical observation -> fresh schema-v4 IDLE binding -> one budgeted canonical DialogueDeleteService.delete() callback -> post-delete oracle -> bounded child result`.

The production assembly seam names and constructs `CodexThreadLifecycleAdapter`, `DeleteStorageCleanupCoordinator`, `CodexRuntimeManager`, `IsolationPathAuthority` and `DialogueDeleteService`. `CanonicalDeleteGuard` permits one `DialogueDeleteService.delete()` call and provides no raw delete fallback. `thread/read` and `thread/list` have no callable dispatch route.

`P7C13_REPAIR2_COMPLETE_CHILD_ORCHESTRATOR=PASS`
`P7C13_REPAIR2_CHILD_RESULT_AUTHORITY=PASS`
`P7C13_REPAIR2_CANONICAL_DELETE_ONLY=PASS`

## Pre-dispatch budget gates

`FutureRealEffectBridge` reserves the exact slot before invoking every effect callback. This covers model/list, thread start/resume, turn start, approval response, ALLOW, interrupt and the canonical delete service. The zero-ceiling forbidden read/list routes reject before any callback. Synthetic callbacks prove that over-budget approval, ALLOW, interrupt and delete callbacks are not entered. The one canonical delete budget prevents a second service invocation.

`P7C13_REPAIR2_PRE_DISPATCH_BUDGET_GATES=PASS`

## Turn and matcher seams

- Turn 1 uses the actual observed terminal/output seam and requires `START_CONFIRMED`, definitive `COMPLETED` and the exact in-memory response marker.
- Turn 2 uses the new-generation resume seam and actual observed output, requiring the exact in-memory memory marker.
- Turn 3 uses independent owned thread/Turn/cwd/sequence/target/wire SHA authority and exactly one accepted P7.C12 matcher result. Wrong owned bindings prevent both response callbacks.
- Turn 4 uses a distinct `turn-4` binding, `sleep 120`, active/nonterminal state and one pre-reserved interrupt. Inactive or wrong binding prevents interrupt entry; UNKNOWN and a second interrupt fail closed. Turn 4 has no approval response path.

The synthetic tests cover actual fake Turn 1/2 output parsing, Turn 3 wrong-owned binding, Turn 4 inactive/wrong binding, target absence before response, target metadata after ALLOW and exact target cleanup.

## Physical oracle and delete chain

`BoundedTargetOracle` is the production-capable no-follow bounded observation seam. It scans persistent session content, session filename, session directory components and history content, plus isolated sqlite/log files, for the current in-memory raw thread ID and marker bytes. Symlink, special-file, read, size and traversal ambiguity fails closed. Pre-delete acceptance requires target material to be physically observed and scan-conclusive. Post-delete acceptance requires zero content, filename, directory, marker, isolated and scan residuals, valid ownership envelope, quiescent owned group, and `unrelated_target_specific_removal_detected == False`.

The synthetic production chain uses a fresh schema-v4 controller database with one canonical IDLE dialogue binding. Confirmed success reaches `DELETE_CONFIRMED -> DELETE_CONFIRMED_PENDING_STORAGE -> local cleanup -> finalize/tombstone -> DELETED`; `DELETE_UNKNOWN` is terminal with no retry/read/list/finalizer/tombstone; confirmed-pending local failure has no external retry. Marker-only, filename-only, directory-only, isolated and unrelated-removal residuals fail the acceptance oracle.

`P7C13_PREP_PHYSICAL_ORACLE=PASS`
`P7C13_PREP_DELETE_CHAIN=PASS`

## Child result authority

The child writes one exclusive bounded root-only `p7c13-repair2-child-result-v1` record with finite status/verdict, source/run authority, effect counts, finite Turn outcomes, matcher/delete classes, residual counts and process-group quiescence. The parent performs strict source/effect/schema/ownership/identity validation; missing or malformed result cannot produce a parent PASS. Safe child failure paths publish bounded non-PASS authority. Raw thread IDs, targets, prompt/response/wire contents and credentials are not written.

## Validation

- focused repaired P7.C13: `45 passed`
- accepted focused P7.C12 matcher: `13 passed`
- C2/C3/C4/C5 focused: `10 / 49 / 32 / 15 passed`
- complete non-real regression with all real gates unset: `1065 passed, 2 warnings`
- compileall: PASS (`PYTHONPATH=src python -m compileall -q src tests`)
- `git diff --check`: PASS
- leakage/security scan: PASS; no raw retained recovery IDs, prior target paths, prompt/response/wire plaintext, credentials, authorization token or root-only JSON committed
- no historical consumed real test was executed

## Zero-effect accounting

All Repair-2 implementation and validation paths were offline or synthetic. No real future authorization token was created or set.

`REAL_CODEX_PROCESS_STARTS=0`
`APP_SERVER_STARTS=0`
`MODEL_LIST_CALLS=0`
`THREAD_START_CALLS=0`
`THREAD_RESUME_CALLS=0`
`THREAD_READ_CALLS=0`
`THREAD_LIST_CALLS=0`
`THREAD_DELETE_CALLS=0`
`TURN_START_CALLS=0`
`TURN_INTERRUPT_CALLS=0`
`APPROVAL_RESPONSES=0`
`ALLOW_RESPONSES=0`
`DENY_RESPONSES=0`
`REAL_LEDGER_CREATIONS=0`
`REAL_BOOT_AUTHORITY_CREATIONS=0`
`REAL_CONTROLLER_MUTATIONS=0`
`REAL_ISOLATED_MUTATIONS=0`
`REAL_PERSISTENT_HOME_MUTATIONS=0`
`REAL_APPROVAL_TARGET_MUTATIONS=0`
`TELEGRAM_CALLS=0`
`REAL_CODEX_SIGNALS=0`
`HISTORICAL_AUTHORITY_MUTATIONS=0`

Synthetic temporary SQLite/files and harmless owned subprocess watchdog tests were test-owned only. P8/P9 were not started.

P7C13_REPAIR2_CHILD_DISPATCH_PREPARED=YES
P7C13_REPAIR2_BOOT_AUTHORITY_PREPARED=YES
P7C13_REPAIR2_COMPLETE_CHILD_ORCHESTRATOR=PASS
P7C13_REPAIR2_PRE_DISPATCH_BUDGET_GATES=PASS
P7C13_REPAIR2_CHILD_RESULT_AUTHORITY=PASS
P7C13_REPAIR2_CANONICAL_DELETE_ONLY=PASS
P7C13_PREP_HARNESS_READY=YES
P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
