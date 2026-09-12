# P7.C13 preparation Repair-3 evidence — 2026-09-12

Status: **PREPARATION COMPLETE / ZERO REAL EFFECT / NO REAL EXECUTION**

## Lineage and scope

`REPAIR3_BASE_HEAD=aae95407650c10b16387bbe4a27cec8bd96efe2b`

`REPAIR3_BASE_TREE=ea1c626fbf8c7884c8ea4f23bfbd45b33ff2d984`

`PRIOR_HARNESS_BLOB=10ba4084a086a597c892a2fef8409d6c46986062`

`P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

`ARCHITECT_MAIN_HEAD=62b2564029b1de87eb7518a6042613a4b9767439`

`ARCHITECT_MAIN_TREE=a55035bf7889113393ccbcf708223f2e2ed9e72d`

Only this evidence file and `tests/real/test_p7_c13_final_hard_delete_acceptance.py` are tracked Repair-3 changes. No helper was added; the pre-existing untracked `tests/real/__init__.py` was preserved and unstaged. No `src/**`, matcher, historical P7.C6–P7.C12 file, schema, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP file changed.

The final harness and evidence blobs are reported by the post-commit remote readback; the evidence blob is necessarily computed from this final evidence content.

`FINAL_HARNESS_BLOB=4e92eac9789b908e08411801276822113d10663a`

`HELPER_BLOB=NONE`

## Repair-3 implementation proof

- The direct `--p7c13-real-run` parent derives HEAD, tree and harness blob from the checkout, rejects tracked drift, requires all future authority environment values, and calls the prepared executor once only after an exact match.
- Parent order is source gate, fixed O_EXCL ledger reserve, fresh run-owned path selection/preflight, root-only boot, one watchdog child, strict final child result, process-group quiescence and terminal ledger update.
- Production path selection calls the explicit `build_production_real_seam_factory`; `_future_child_main()` cannot resolve `_default_child_seams` or a synthetic thread ID. Synthetic seams require explicit injected test arguments.
- Production wiring includes `CodexRuntimeManager`, `CodexModelCatalogAdapter`, pinned one-call catalog authority, `CodexThreadLifecycleAdapter`, `CodexTurnLifecycleAdapter`, `CodexApprovalBridge`, `IsolationPathAuthority`, `IsolatedStateRoot`, `BoundedTargetOracle`, `SqliteStorage`, repositories, `DeleteStorageCleanupCoordinator`, and `DialogueDeleteService`.
- Fresh isolated root, controller DB, workdir, boot/result paths and high-entropy direct-child `/root` approval target are selected after ledger reservation. Read-only existence, canonical-path and boundary-alias checks run before child creation. Shared `/root/.codex_second` is allowed; unrelated shared-home processes are not signalled.
- Future child umask is `077`; Turn 3 remains exactly `touch <selected target>` with no chmod/chown. Metadata is checked before removing only the exact target.
- Actual adapter-returned thread and Turn bindings are the production authority. Turn 1 output and Turn 2 memory are observed, not fabricated. A new runtime generation resumes the actual fresh thread without a second model/list.
- Approval success reserves total approval-response and ALLOW accounting before one `CodexApprovalBridge` protocol callback. No separate real ALLOW callback exists. C12 strict matcher, independent thread/Turn/cwd/sequence/target hashes, target absence and one-wire cardinality gate success.
- Turn 4 uses the actual distinct binding, `sleep 120`, pre-reserved interrupt accounting and definitive failed/interrupted terminal. No second approval response route exists.
- Runtime shutdown precedes both physical scans. The bounded oracle uses actual raw thread ID and in-memory marker bytes and requires a conclusive pre-delete observation and clean post-delete residual result.
- Fresh schema-v4 storage is opened through `SqliteStorage`; `DialogueRepository` persists and rereads one actual IDLE binding. The only application delete is one budgeted `DialogueDeleteService.delete(DialogueDeleteRequest(...))`; UNKNOWN and confirmed-pending remain terminal/no external retry.
- Watchdog and parent use the same boot-bound `p7c13-repair3-child-result-v1` validator. The old `p7c13-child-result-v1` schema is rejected. Parent PASS requires PASS/true, exact source/run authority, bounded effects with forbidden zeros, zero residuals and process-group quiescence.

## Offline validation

- Focused Repair-3: `53 passed`.
- P7.C12 plus C2/C3/C4/C5 focused: `119 passed, 133 subtests`.
- Focused P7.C13 plus P7.C12 final rerun: `66 passed, 101 subtests`.
- Complete pytest with every real gate unset: `1829 passed, 7 skipped, 6 failures`; all six failures are preserved historical P7.C7–P7.C11 consumed-latch/absence assertions, not Repair-3 failures. They were not modified or cleaned. The non-historical complete suite is rerun with those historical absence assertions excluded.
- Ordinary unittest discovery with every real gate unset: `1842 run, 5 failures, 1 error, 7 skipped`; the same six preserved historical P7.C7–P7.C11 consumed-latch/absence assertions account for all non-green outcomes. Historical consumed authorities remain untouched.
- `compileall`: PASS. `git diff --check`: PASS.
- Leakage/security review: no future authorization token, raw thread IDs, prompts/responses, wire plaintext, credentials, Telegram calls or root-only result contents are written to evidence.

## Zero-real-effect accounting

`REAL_CODEX_PROCESS_STARTS=0`

`APP_SERVER_STARTS=0`

`REAL_MODEL_LIST_CALLS=0`

`REAL_THREAD_START_CALLS=0`

`REAL_THREAD_RESUME_CALLS=0`

`REAL_THREAD_READ_CALLS=0`

`REAL_THREAD_LIST_CALLS=0`

`REAL_THREAD_DELETE_CALLS=0`

`REAL_TURN_START_CALLS=0`

`REAL_TURN_INTERRUPT_CALLS=0`

`REAL_APPROVAL_RESPONSES=0`

`REAL_ALLOW_RESPONSES=0`

`REAL_DENY_RESPONSES=0`

`REAL_PERSISTENT_HOME_MUTATIONS=0`

`REAL_ISOLATED_ROOT_MUTATIONS=0`

`REAL_CONTROLLER_DB_MUTATIONS=0`

`REAL_APPROVAL_TARGET_MUTATIONS=0`

`REAL_P7C13_LEDGER_CREATIONS=0`

`REAL_P7C13_BOOT_CREATIONS=0`

`REAL_P7C13_RESULT_CREATIONS=0`

`TELEGRAM_CALLS=0`

`REAL_CODEX_PROCESS_SIGNALS=0`

`HISTORICAL_AUTHORITY_MUTATIONS=0`

All execution tests used injected adapters, temporary files/SQLite, or harmless subprocesses only. The future authorization token was never set or invented. P8 and P9 were not started.

P7C13_REPAIR3_PRODUCTION_PARENT_ENTRY=PASS
P7C13_REPAIR3_PRODUCTION_ADAPTER_WIRING=PASS
P7C13_REPAIR3_REAL_THREAD_TURN_BINDINGS=PASS
P7C13_REPAIR3_SINGLE_PROTOCOL_ALLOW=PASS
P7C13_REPAIR3_REAL_PHYSICAL_ORACLE_WIRING=PASS
P7C13_REPAIR3_REAL_CONTROLLER_DELETE_WIRING=PASS
P7C13_REPAIR3_UNIFIED_CHILD_RESULT_AUTHORITY=PASS
P7C13_REPAIR3_NO_SYNTHETIC_PRODUCTION_DEFAULT=PASS
P7C13_PREP_HARNESS_READY=YES

P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO

P8_STARTED=NO
P9_STARTED=NO
