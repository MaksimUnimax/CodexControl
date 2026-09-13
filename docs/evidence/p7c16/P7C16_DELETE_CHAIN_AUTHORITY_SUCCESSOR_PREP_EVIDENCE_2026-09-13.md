# P7.C16 delete-chain authority successor preparation evidence — 2026-09-13

Status: **PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Binding source

- Preparation branch: `prep-p7-c16-delete-chain-authority-successor-repair1-2026-09-13`
- Repair-1 base HEAD: `4f477e313192350414b1c157b6e1789135d11600`
- Repair-1 base tree: `67a5276b34481ae3d118cbcb09dd73d2a6224973`
- Prior P7.C16 launcher blob: `d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab`
- Prior P7.C16 evidence blob: `3bbcd3e2a70c4f6b1105723554c0b932fa42a010`
- Consumed P7.C15 execution source: `17f8907068aa58de85d92800b9d87621e59ad1a3`
- Consumed P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- P7.C15 real evidence blob: `b0f1f2014e23c60cb611c3176ad5f880b50dfc35`
- Inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- Inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- Inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`
- Binding architect main: `eb0ba26b145071e6cc54d1c30d0a3970c71e5921`, tree `9e4b1c3c375f49747ce584cd77d1bfcde15eb93b`

Tracked changes are restricted to the P7.C16 successor module and this factual
evidence file. P7.C15, P7.C14, P7.C13 and P7.C12 source/evidence blobs were
not edited.

## Root-cause reproduction

`reproduce_p7c15_controller_authority_root_cause()` opens a temporary real
schema-v4 `SqliteStorage`, supplies a real `DeleteStorageCleanupCoordinator`
with an early root-only `IsolationPathAuthority`, and requires the exact safe
`ValueError("controller_storage_mismatch")`. The reproduction returned:

```text
P7C16_PREP_P7C15_CONTROLLER_AUTHORITY_ROOT_CAUSE_REPRODUCED=PASS
coordinator_delete_calls=0
thread_delete_dispatches=0
runtime_manager_effect_calls=()
```

## Successor correction

`P7C16LateBoundControllerRuntimeView` retains the same underlying runtime
manager and its early root authority. Once the fresh P7.C16 controller DB
exists, it validates an absolute regular root-owned private non-symlink file,
the exact parent/profile/repository envelope, `IsolationPathAuthority`, and
`storage.matches_database_path()` before the real cleanup coordinator is
constructed. The underlying manager authority is not mutated in place.

The P7.C16 facade preserves generation tracking while delegating the underlying
reservation token, release, profile lookup, shutdown and isolated-root
recreation to the same manager. It exposes only the late-bound exact
`IsolationPathAuthority`. The effective engine profile is
`P7C16_ENGINE_PROFILE_ID=p7c15-successor-profile`; P7.C16 uniqueness is in the
gate, fresh hash/paths/thread and distinct ledger. The positive handoff
composes the consumed P7.C15 lifecycle flow but routes the local chain through
the real `DeleteStorageCleanupCoordinator` and real `DialogueDeleteService`.

## Full production-shaped positive handoff

The focused handoff used temporary authorities and the P7.C15 fake only at the
external runtime/protocol boundary. It did not invoke Codex or an external
provider. Real application cleanup classes executed.

```text
real_cleanup_coordinator_constructor_count=1
canonical_delete_service_invocations=1
official_lifecycle_delete_calls=1
same_underlying_runtime_manager=YES
second_runtime_manager=0
model/list_dispatches=1
cleanup_reservations=1
isolated_root_recreates=1
underlying_reservation_release=1
facade_owned_synthetic_reservations=0
thread/delete_dispatches=1
second_delete=0
retry=0
child_status=PASS
runtime_child_quiescent=true
```

Exact child effect matrix:

| Effect | Count |
|---|---:|
| new_threads | 1 |
| model/list | 1 |
| thread/start | 1 |
| thread/resume | 1 |
| turn/start | 4 |
| approval_responses | 1 |
| allow_responses | 1 |
| turn/interrupt | 1 |
| thread/delete | 1 |
| thread/read | 0 |
| thread/list | 0 |
| second_child | 0 |
| real_retry | 0 |
| telegram | 0 |

## Authority negatives and convergence

The focused suite covers the consumed `controller_db_path=None` defect,
missing/different controller DB, symlink authority, exact storage mismatch,
fresh exact-path binding only after DB creation, and historical-path namespace
rejection. The source gate hashes the live P7.C15/P7.C14/P7.C13/P7.C12 and
package-marker files and checks repository-origin imports plus clean worktree
and index. All mismatches block before ledger reservation/run mkdir/child.

The forced delete-operation failure is classified as official UNKNOWN by the
accepted service semantics. It performs one delete dispatch, no retry, and
the successor convergence attempt leaves the child quiescent. Coordinator,
service, exact-path, reservation, and isolated-root recreation failures remain
non-PASS and do not authorize another child or destructive effect.

The parent maps valid PASS to `COMPLETED`/exit `0`; FAILED, UNKNOWN,
CONFIRMED_PENDING and TIMEOUT remain nonzero; disabled or source-gated entry
returns exit `2`. Root-only ledger, boot and child-result authorities reject
malformed JSON, duplicate keys, symlinks, hardlinks, wrong mode/owner,
replacement identity drift, wrong source, wrong run hash and wrong boot
correlation. Terminal ledger updates use the reserved descriptor identity and
retain the consumed state.

The production constructor statically binds `/root/.codex_second` and the
exact command `/usr/bin/env PYTHONPATH=/root/CodexControl/src:/root/CodexControl
/usr/bin/python -m tests.real.test_p7_c16_final_hard_delete_successor
--p7c16-future-child --boot-authority <exact-current-run-boot>`. The real child
performs installed Codex authority verification before selecting the default
runtime factory; only an explicit fake-runtime test seam disables that check.

## Zero-real-effect accounting

```text
real Codex/app-server starts=0
real model/thread/Turn RPCs=0
real approval responses/ALLOW/DENY=0
real interrupt=0
real delete=0
P7C16 real ledger creation=0
P7C15/P7C14/P7C13 ledger mutation=0
persistent-home mutation=0
retained historical cleanup=0
Telegram=0
real process signals=0
P7.C15 retry=0
P7.C14 retry=0
P7.C13 retry=0
P8=NOT_STARTED
P9=NOT_STARTED
```

Temporary ledgers and fresh temporary test paths were removed by their bounded
test contexts. No `/root/.codexcontrol/p7c16-one-shot.json` authorization
ledger or real token was created.

## Validation

Final validation totals:

```text
P7C16 focused unittest: 7 passed
P7C15 consumed offline regression: 23 passed, 1 immutable historical failure
P7C14/P7C13/P7C12 offline regression: 96 passed, 128 subtests passed
P7C2/P7C3/P7C4/P7C5 regression: 106 passed, 54 subtests passed
complete non-real pytest (excluding tests/real): 1065 passed, 2 warnings, 647 subtests passed
unittest discovery with all real gates unset: completed; known repository timeout/resource diagnostics only
compileall: PASS
git diff --check: PASS
changed-path scope: PASS
P7C16 gate-disabled smoke: exit 2, no P7C16 ledger, no Codex process
```

The complete-suite failures are retained historical P7.C7–P7.C11 latch
state, one consumed P7.C15 positive-path expectation, and one existing runtime
test. The unittest error is the retained P7.C11 pre-existing authority state.
They are immutable and were not repaired here.

Final successor blobs are computed after the final evidence edit:

```text
P7C16_LAUNCHER_BLOB=08e6be10f4f7444c87a2e72572e4a8107ed7a3b2
P7C16_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
P7C16_HELPER_BLOB=NONE
```

P7C16_REPAIR1_BASE_HEAD=4f477e313192350414b1c157b6e1789135d11600
P7C16_REPAIR1_BASE_TREE=67a5276b34481ae3d118cbcb09dd73d2a6224973
PRIOR_P7C16_LAUNCHER_BLOB=d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab
PRIOR_P7C16_EVIDENCE_BLOB=3bbcd3e2a70c4f6b1105723554c0b932fa42a010
P7C16_ENGINE_PROFILE_ID=p7c15-successor-profile
P7C16_AUTHENTICATED_PRODUCTION_HOME=/root/.codex_second
P7C16_REAL_WATCHDOG_HARD_DEADLINE=1600.0_SECONDS

P7C16_REPAIR1_PROTECTED_SOURCE_BUNDLE=PASS
P7C16_REPAIR1_UNDERLYING_RESERVATION_OWNERSHIP=PASS
P7C16_REPAIR1_ENGINE_PROFILE_AND_CONVERGENCE=PASS
P7C16_REPAIR1_REAL_PARENT_CHILD_WATCHDOG_PATH=PASS
P7C16_REPAIR1_ROOT_ONLY_LEDGER_BOOT_RESULT=PASS
P7C16_REPAIR1_AUTHENTICATED_PRODUCTION_HOME=PASS
P7C16_REPAIR1_PARENT_TERMINAL_EXIT_PROJECTION=PASS
P7C16_REPAIR1_REAL_COORDINATOR_FULL_HANDOFF=PASS
P7C16_PREP_READY=YES

P7C16_PREP_P7C15_CONTROLLER_AUTHORITY_ROOT_CAUSE_REPRODUCED=PASS
P7C16_PREP_LATE_BOUND_EXACT_CONTROLLER_AUTHORITY=PASS
P7C16_PREP_REAL_DELETE_STORAGE_CLEANUP_COORDINATOR=PASS
P7C16_PREP_SAME_RUNTIME_MANAGER_NO_SECOND_MODEL_LIST=PASS
P7C16_PREP_LATE_FAILURE_RUNTIME_CONVERGENCE=PASS
P7C16_PREP_FULL_PRODUCTION_SHAPED_HANDOFF=PASS
P7C16_PREP_READY=YES

P7C16_REPAIR1_PROTECTED_SOURCE_BUNDLE=PASS
P7C16_REPAIR1_UNDERLYING_RESERVATION_OWNERSHIP=PASS
P7C16_REPAIR1_ENGINE_PROFILE_AND_CONVERGENCE=PASS
P7C16_REPAIR1_REAL_PARENT_CHILD_WATCHDOG_PATH=PASS
P7C16_REPAIR1_ROOT_ONLY_LEDGER_BOOT_RESULT=PASS
P7C16_REPAIR1_AUTHENTICATED_PRODUCTION_HOME=PASS
P7C16_REPAIR1_PARENT_TERMINAL_EXIT_PROJECTION=PASS
P7C16_REPAIR1_REAL_COORDINATOR_FULL_HANDOFF=PASS
P7C16_PREP_READY=YES

P7C16_REAL_EXECUTION_AUTHORIZED=NO
P7C15_REAL_RETRY_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
