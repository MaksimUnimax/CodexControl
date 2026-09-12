# P7.C13 preparation Repair-4 evidence — 2026-09-12

Status: **REPAIR-4 PREPARATION READY / ZERO REAL EFFECT / NO REAL EXECUTION**

## Authority, lineage and scope

`REPAIR4_BASE_HEAD=75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`

`REPAIR4_BASE_TREE=2c240993be4d7998c94b455c347c2065176adbd7`

`PRIOR_HARNESS_BLOB=b60a38c90317ec83063f314eb189af9c66e735cb`

`P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

`ARCHITECT_MAIN_HEAD=4f0ab1232d00df44b732f7f741e201b457391577`

`ARCHITECT_MAIN_TREE=79f33b80b9f507217f1d79a099809f9277e4e116`

`FINAL_HARNESS_BLOB=61853860ed0955df6119edb288d22573299cd1b3`

`FINAL_EVIDENCE_BLOB=DERIVED_BY_FINAL_REMOTE_READBACK`

`HELPER_BLOB=NONE`

The branch began exactly at Repair-3 final candidate `75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`; no merge, rebase, squash or history rewrite was used. The only tracked Repair-4 files are this evidence file and `tests/real/test_p7_c13_final_hard_delete_acceptance.py`. The tolerated untracked `tests/real/__init__.py` was preserved. No `src/**`, accepted matcher, historical P7.C6–P7.C12 file, schema/migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP file changed.

## Repair-4 implementation authority

- Source gate derives exact HEAD, tree and harness blob and requires both `git diff --quiet HEAD -- .` and `git diff --cached --quiet HEAD -- .`; staged tracked drift is blocked before ledger reservation.
- Production topology uses `/root/.codex_second` only as shared authenticated profile home, the actual repository root as repository authority, a pre-existing private controller-root directory, and a fresh isolated root outside repository/profile/controller boundaries. The isolated root and workdir are fresh direct `/root` children; controller DB/ledger/boot/result remain under the private controller root.
- Production preflight is read-only and covers `/proc/self/mountinfo`, persistent home, repository, isolated root plus `sqlite`/`logs`, controller root/DB, workdir, approval target, ledger, boot and result. It checks physical aliases, root ownership, exact owned external users, and allows shared-home-only processes. No mount or namespace mutation and no unrelated process signal is used.
- `create_fresh_private_workdir()` creates the absent workdir exactly once before `thread/start`, then proves root ownership, mode `0700`, non-symlink identity and stable `(st_dev, st_ino)` across turns.
- Named finite internal waits are: runtime acquire generations 1/2 `30s` each; model list `20s`; thread start/resume `30s` each; Turn 1/2 start and terminal `60s` each; Turn 3 start/approval/terminal `90s`; Turn 4 start `30s`, active observation `5s`, interrupt/terminal `45s`; runtime shutdowns `30s`; controller open/binding `30s`; canonical application delete `60s`; final convergence `30s`. Every potentially blocking production-capable await is owned and bounded.
- The parent watchdog hard deadline is `670.0s`, derived from `610.0s` named stages plus `60.0s` margin, with TERM grace `5.0s` and KILL grace `5.0s`. Active/zombie/error probes inspect only the exact owned PGID via bounded `/proc` reads; scan errors fail closed. The parent can signal only that PGID.

## C11/C12 approval authority

- Turn 3 uses the explicit C11-shaped prompt: first and only shell-command tool call; exact `touch <selected target>` operation; explicit `sandbox_permissions=require_escalated`; short justification; no default-sandbox attempt; no alternate path/tool/network operation; no second call; no retry.
- A run-owned root-only wire record and root-only bounded approval journal are separate from the C12 matcher. The wire record captures once from the actual request and records actual kind, request ordinal, independent local sequence, thread, Turn, normalized cwd, target hash and command SHA/plaintext. A second capture fails closed.
- Correlation requires exactly one in-memory capture against the immutable record. Only after kind, ordinal, local sequence, thread, Turn, cwd, target hash/SHA, command SHA and target absence are validated are C12 `CapturedRequest`, `ExpectedAuthority` and `CorrelatedWireRecord` projected. `command_plaintext` comes from the validated wire record. The accepted matcher blob is unchanged.
- The single bridge route reserves total response budget before either ALLOW or DENY; ALLOW additionally reserves the ALLOW slot before the bridge callback. PASS requires request ordinal `1`, request count `1`, response count `1`, ALLOW `1`, DENY `0`, bridge `ALLOWED`, no response-unknown and exact C12 match. Mismatch DENY consumes only the total-response slot; a second response is blocked.

## Turn, delete and oracle authority

- Turn 1/2 use observed terminal outputs and memory markers across a deliberate runtime-generation restart/resume. Turn 4 uses only `sleep 120`; an owned terminal waiter must lose a bounded active observation window before the single interrupt slot is reserved. Terminal-before-active yields zero interrupt; UNKNOWN is never accepted.
- The canonical chain remains `DialogueDeleteService` -> instrumented real `CodexThreadLifecycleAdapter` -> `DeleteStorageCleanupCoordinator` -> `CodexRuntimeManager`/isolated authority. There is no raw delete fallback and exactly one application delete call. The official P1.9 status is recorded independently from application status.
- Controller proof derives schema `PRAGMA user_version == 4`, the durable IDLE binding before delete, post-delete live binding absence and exact bounded tombstone identity/expiry. Official `DELETE_UNKNOWN` remains `UNKNOWN`; confirmed external delete with local proof pending remains `CONFIRMED_PENDING_STORAGE` and maps to terminal `CONFIRMED_PENDING`; neither retries or becomes PASS.
- Post-delete proof derives the isolated ownership envelope through `IsolatedStateRoot.validate()`, regular/special/symlink/scan counts, and actual descendant counts under isolated `sqlite/` and `logs/`. The persistent and isolated bounded no-follow oracles are separate and include target thread ID plus memory, response, approval-prompt/target and Turn-4 markers. Filename, directory, history, content and marker residuals are independently blocking.
- Unrelated-removal is derived from content-free pre/post metadata and target-path attribution, not a literal success constant. Shared-home background changes are not attributed without exact target evidence.
- Child result publishes derived runtime-owned-child quiescence and leaves parent process-group quiescence to the parent watchdog. Parent PASS requires child runtime quiescence plus active `0`, zombie `0`, scan errors `0`, one child and retry `0` from its own exact-PGID probes.

## Validation

- Focused Repair-4: `63 passed, 22 subtests`.
- Accepted P7.C12 plus relevant C2/C3/C4/C5 fake/non-real regressions: `119 passed, 133 subtests`.
- Complete non-real pytest with all real gates unset: `1839 passed, 7 skipped, 6 failures, 1514 subtests`; all six failures are preserved historical consumed-latch/absence authorities from P7.C7–P7.C11, including the existing P7.C11 preflight error. No historical latch was removed or rewritten.
- Ordinary unittest discovery with all real gates unset: `1852 run, 5 failures, 1 error, 7 skipped`; the six non-green outcomes are the same preserved historical consumed-latch/absence authorities. The initial repository-root discovery form ran zero tests and was not used as the discovery result.
- `compileall`: required after evidence update; result recorded by final handoff.
- `git diff --check`: PASS before evidence publication; rerun required after evidence update.
- Leakage/security scan: source/evidence review found no future authorization token, raw real thread ID, credential content, raw prompt/response, wire plaintext, Telegram call or real-process signal. Temporary fixtures remained test-owned and no future real mode was invoked.

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

No authorization token was set or invented. `--p7c13-real-run` was not executed. No real Codex dependency was started. P8 and P9 were not started.

P7C13_REPAIR4_SOURCE_GATE=PASS
P7C13_REPAIR4_ISOLATION_BOUNDARY_GATE=PASS
P7C13_REPAIR4_REAL_WATCHDOG_GATE=PASS
P7C13_REPAIR4_C11_WIRE_AUTHORITY_GATE=PASS
P7C13_REPAIR4_EXPLICIT_ESCALATION_GATE=PASS
P7C13_REPAIR4_SINGLE_PROTOCOL_RESPONSE_GATE=PASS
P7C13_REPAIR4_TURN4_ACTIVE_INTERRUPT_GATE=PASS
P7C13_REPAIR4_OFFICIAL_DELETE_OBSERVATION=PASS
P7C13_REPAIR4_REAL_POST_DELETE_ORACLE=PASS
P7C13_REPAIR4_TERMINAL_RECOVERY_CLASSES=PASS
P7C13_REPAIR4_CHILD_PARENT_QUIESCENCE=PASS
P7C13_PREP_HARNESS_READY=YES
P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
