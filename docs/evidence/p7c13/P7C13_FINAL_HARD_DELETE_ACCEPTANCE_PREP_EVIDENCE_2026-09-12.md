# P7.C13 final hard-delete acceptance preparation — Repair-1 evidence

Status: REPAIR-1 PREPARATION ONLY / ZERO REAL EFFECT / NO REAL AUTHORIZATION

## Lineage and authority

- branch: `prep-p7-c13-final-hard-delete-acceptance-repair1-2026-09-12`
- `REPAIR1_BASE_HEAD=8fa749856c678cb1ae120f7802c6c553c1272e34`
- rejected candidate parent: `a5c66a778800d1c5ee5811d97d961fe0dccd677c`
- `ORIGINAL_HARNESS_BLOB=a6962a14ffd4c10d6e4ff072cd24622077f839c2`
- `NEW_HARNESS_BLOB=82a7f3c1e31456205fb316eb4e692973dc3d0361`
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1` (unchanged)
- architect `origin/main`: `47f93f2f571a053f3fafed1e6734a9297e198974`
- architect `origin/main` tree: `cda745886541a71b1639440383a08b163ef9bc05`
- helper: none
- changed tracked paths: this evidence file and `tests/real/test_p7_c13_final_hard_delete_acceptance.py` only

No `src/**`, accepted P7.C12 matcher, historical P7.C6–P7.C12 files, controller migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP changed.

## Future-real path and gate

`FutureArchitectContract` now requires authorization token, expected HEAD, expected TREE and expected harness blob. `future_real_gate()` requires exact agreement across the contract, explicit environment, current HEAD, current TREE and current harness blob. Any unset or mismatched value returns before executor selection. Exact synthetic agreement invokes the prepared parent executor once; no current value is an architect authorization value.

`PreparedFutureRealExecutor` reserves the durable ledger before its one-child watchdog, passes the exact contract source values into the recovery record, validates the bounded child result, and records a terminal consumed state. `FutureRealChildPath` verifies installed authority and accepted runtime routing before constructing the runtime/business path. The child business path uses the budgeted effect bridge and the accepted `DialogueDeleteService` chain; no `thread/read` or `thread/list` dispatch method exists.

`FUTURE_REAL_EXECUTOR_PREPARED=YES`
`P7C13_REPAIR1_REAL_EXECUTOR_PREPARED=YES`
`GATE_TO_EXECUTOR_SYNTHETIC_PROOF=PASS` — exact gate executor calls `1`; unset, wrong token, HEAD, TREE or harness blob calls `0`.

Installed authority is fixed to `/usr/local/bin/codex`, `codex-cli 0.144.6`, schema SHA `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`. Synthetic probes cover version/schema drift before runtime/business callbacks. Future routing uses shared authenticated `/root/.codex_second`, isolated `sqlite` and `logs`, and `history.persistence="none"`. Shared-home users are allowed; unrelated shared-home processes are never signalled.

## Durable one-shot and watchdog

`DurableOneShotLedger` uses exclusive creation before the first future thread effect, root ownership, mode `0600`, regular-file/no-symlink/nlink-one checks, bounded duplicate-key-rejecting JSON, stable `(st_dev, st_ino)` identity and terminal consumed states. Recovery fields remain root-only in the future ledger; Git evidence contains no recovery JSON or raw run identities.

`DURABLE_ONE_SHOT_LEDGER_PREPARED=YES` — synthetic first reserve, restart read, completed/incomplete rerun blocking, malformed/duplicate JSON, symlink, wrong mode, nlink and replacement/identity drift all fail closed.

`OwnedParentChildWatchdog` creates one dedicated session/process group, records the exact child PID/PGID, has no second-child/retry path, and applies bounded TERM then KILL only after rechecking the owned PGID. Synthetic normal, nonzero, timeout, TERM/KILL, residual-group, cancellation/error, malformed/missing-result, second-child, retry and wrong-PGID cases are covered.

`PARENT_CHILD_WATCHDOG_PREPARED=YES`
`INSTALLED_RUNTIME_GATE_PREPARED=YES`

## Future turn and approval authority

Markers are generated with fresh high entropy in memory; only hashes are reportable. Turn 1 requires observed `START_CONFIRMED`, definitive `COMPLETED`, and the exact response marker. Turn 2 resumes the exact fresh thread after a new runtime generation and requires the exact Turn-1 memory marker in observed completed output.

`TURN1_RESPONSE_MARKER_PROOF=PASS`
`TURN2_MEMORY_MARKER_PROOF=PASS`
`DISTINCT_TURN_IDS_PROOF=PASS` — separate Turn-1/2/3/4 authorities are present, pairwise distinct, and bound to the same thread/profile/cwd; reused IDs fail closed.
`OWNED_TURN3_THREAD_BINDING=PASS`
`OWNED_TURN3_TURN_BINDING=PASS`
`OWNED_TURN3_CWD_BINDING=PASS`
`OWNED_TURN3_SEQUENCE_BINDING=PASS`
`OWNED_TURN3_SELECTED_TARGET_BINDING=PASS`

Turn 3 independently selects one fresh high-entropy direct child of `/root`; exact-path lstat absence is required. The only accepted stimulus is `/bin/bash -lc 'touch <selected target>'` with `sandbox_permissions=require_escalated`. Before ALLOW, owned thread/Turn/cwd hashes, sequence, exact target, target SHA and one-wire identity must agree independently with the accepted P7.C12 matcher. Mutually self-consistent wrong thread, Turn, cwd, sequence and target tuples do not allow. Post-ALLOW exact-path regular/root-owned/0600/nlink-one metadata is required; missing or unsafe target fails.

Turn 4 is a distinct active `sleep 120` turn with no write sentinel and no second approval response. Exactly one interrupt is allowed for the exact active Turn-4 binding; wrong binding, terminal-before-interrupt, second interrupt, reused ID, UNKNOWN and unexpected approval fail closed.

`TURN4_ACTIVE_BINDING_PROOF=PASS`

## Physical residual and unrelated-removal oracle

`BoundedTargetOracle` performs bounded no-follow scans over persistent sessions/history and isolated sqlite/log families. It counts exact target-thread content plus exact target-thread bytes in persistent session filenames and directory components, and reports only counts/classes/hashes. Symlink, special-file, read, size and traversal ambiguity is fail closed. Filename-only and directory-name-only residual tests are present. Empty pre-delete observation is inconclusive; marker-only residual remains an independent acceptance failure.

`SESSION_CONTENT_RESIDUAL_ORACLE=PASS`
`SESSION_FILENAME_RESIDUAL_ORACLE=PASS`
`SESSION_DIRECTORY_RESIDUAL_ORACLE=PASS`
`SESSION_CONTENT_RESIDUAL_ORACLE=PASS`
`UNRELATED_TARGET_SPECIFIC_REMOVAL_GATE=PASS` — explicit `unrelated_target_specific_removal_detected == False` gate; unrelated shared-home activity alone is not attributed or blocked.

## Production delete-chain preparation

Existing synthetic schema-v4 `DialogueDeleteService` coverage is preserved: one official confirmed delete reaches confirmed-pending, reserve, shutdown/reap, quiescence, isolated payload reset, persistent scan, finalization, bounded tombstone and release; `DELETE_UNKNOWN` is terminal with no retry/read/list/finalizer/tombstone; confirmed-pending local failure has no external retry; marker-only residual rejects final acceptance despite zero exact-thread attribution.

`PRODUCTION_DELETE_CHAIN_PREPARED=PASS`

Future PASS requires official `DELETE_CONFIRMED`, application `DELETED`, bounded tombstone, no live binding, valid isolated ownership, zero isolated sqlite/log descendants, zero content/filename/directory/marker residuals, zero scan errors, no unrelated target-specific removal, zero owned children/group zombies, exact effect budget, valid child result and consumed ledger state.

`POST_DELETE_ORACLE=PASS`

## Validation

- focused repaired P7.C13: `37 passed`
- accepted focused P7.C12 matcher: `13 passed`
- C2/C3/C4/C5 focused: `10 / 49 / 32 / 15 passed`
- complete non-real regression, all real gates unset: `1813 passed, 7 skipped, 6 deselected`
- deselected historical checks are only retained-latch absence/preflight assertions; no historical latch was removed, rewritten or otherwise mutated
- compileall: PASS
- `git diff --check`: PASS
- leakage scan: PASS; no raw retained thread/Turn IDs, prior target paths, prompt/response/wire plaintext, credentials, authorization token, root-only JSON or real effect call was committed

## Zero-real-effect accounting

All values observed during Repair-1 are zero:

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
`REAL_PERSISTENT_HOME_MUTATIONS=0`
`REAL_ISOLATED_ROOT_MUTATIONS=0`
`REAL_CONTROLLER_DB_MUTATIONS=0`
`REAL_APPROVAL_TARGET_MUTATIONS=0`
`REAL_CODEX_PROCESS_SIGNALS=0`
`TELEGRAM_CALLS=0`
`HISTORICAL_AUTHORITY_MUTATIONS=0`

Temporary SQLite/files and harmless synthetic child processes were test-owned fixtures only. The untracked `tests/real/__init__.py` was preserved and not staged. No real P7.C13 ledger was created. P8/P9 were not started.

P7C13_REPAIR1_REAL_EXECUTOR_PREPARED=YES
P7C13_REPAIR1_DURABLE_ONE_SHOT_PREPARED=YES
P7C13_REPAIR1_OWNED_APPROVAL_BINDING=PASS
P7C13_REPAIR1_DISTINCT_INTERRUPT_BINDING=PASS
P7C13_REPAIR1_PERSISTENCE_PROOF=PASS
P7C13_REPAIR1_COMPLETE_RESIDUAL_ORACLE=PASS
P7C13_PREP_HARNESS_READY=YES
P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
