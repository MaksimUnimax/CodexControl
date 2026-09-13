# P7.C16 delete-chain authority successor preparation evidence — 2026-09-13

Status: **PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Binding source

- Preparation branch: `prep-p7-c16-delete-chain-authority-successor-2026-09-13`
- Exact preparation base HEAD: `3744cb19fba8ecba53d163b9e77f7adc9a213e6c`
- Exact preparation base tree: `2fd391fb6fff9c3e84bda7d3640155677a42f070`
- Consumed P7.C15 execution source: `17f8907068aa58de85d92800b9d87621e59ad1a3`
- Consumed P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- P7.C15 real evidence blob: `b0f1f2014e23c60cb611c3176ad5f880b50dfc35`
- Inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- Inherited P7.C13 harness blob: `5a1fe8e32d18600fcf7ace6b9aa24067238d6dec7`
- Inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- Frozen architect contract: `origin/architect-p7-c16-authority-2026-09-13`, commit `98357f12f1ed940f5ffa31c8c17a63d37d49a9aa`

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

The P7.C16 facade preserves generation tracking, reservation token identity,
bounded shutdown, profile lookup and isolated-root recreation. The positive
handoff composes the consumed P7.C15 lifecycle flow but routes the local chain
through the real `DeleteStorageCleanupCoordinator` and real
`DialogueDeleteService`.

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
rejection. All block before the delete chain.

The forced delete-operation failure is classified as official UNKNOWN by the
accepted service semantics. It performs one delete dispatch, no retry, and
the successor convergence attempt leaves the child quiescent. Coordinator,
service, exact-path, reservation, and isolated-root recreation failures remain
non-PASS and do not authorize another child or destructive effect.

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
P7C16 focused unittest: 6 passed
P7C15/P7C14/P7C13 offline unittest: 83 passed
P7C12 focused unittest: 13 passed
P7C2 integration: 10 passed, 15 subtests passed
P7C3/P7C4/P7C5 pytest: 96 passed, 39 subtests passed
complete non-real pytest: 1899 passed, 7 skipped, 8 historical failures
unittest discovery: 1914 tests, 7 skipped, 6 historical failures, 1 historical authority error
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
P7C16_LAUNCHER_BLOB=d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab
P7C16_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
P7C16_HELPER_BLOB=NONE
```

P7C16_PREP_P7C15_CONTROLLER_AUTHORITY_ROOT_CAUSE_REPRODUCED=PASS

P7C16_PREP_LATE_BOUND_EXACT_CONTROLLER_AUTHORITY=PASS

P7C16_PREP_REAL_DELETE_STORAGE_CLEANUP_COORDINATOR=PASS

P7C16_PREP_SAME_RUNTIME_MANAGER_NO_SECOND_MODEL_LIST=PASS

P7C16_PREP_LATE_FAILURE_RUNTIME_CONVERGENCE=PASS

P7C16_PREP_FULL_PRODUCTION_SHAPED_HANDOFF=PASS

P7C16_PREP_READY=YES

P7C16_REAL_EXECUTION_AUTHORIZED=NO

P7C15_REAL_RETRY_AUTHORIZED=NO

P7C14_REAL_RETRY_AUTHORIZED=NO

P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO

P9_STARTED=NO
