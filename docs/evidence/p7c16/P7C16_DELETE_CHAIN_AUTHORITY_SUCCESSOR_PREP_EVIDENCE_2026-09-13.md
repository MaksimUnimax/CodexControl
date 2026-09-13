# P7.C16 delete-chain authority successor preparation — Repair-2 evidence — 2026-09-13

Status: **PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Binding authority and lineage

```text
BRANCH=prep-p7-c16-delete-chain-authority-successor-repair2-2026-09-13
P7C16_REPAIR2_BASE_HEAD=aaccc8fddc4df763e7412524be85d83134f5bd64
P7C16_REPAIR2_BASE_TREE=1b30963022eeb75cd8dd7e69f771d088f5047f2d
PRIOR_P7C16_LAUNCHER_BLOB=08e6be10f4f7444c87a2e72572e4a8107ed7a3b2
PRIOR_P7C16_EVIDENCE_BLOB=4f0caaf4e3c795bc8ca1dc8d052b663f8a644d47
ORIGIN_MAIN=3e79a33dab71b5ddbb6bcc2dffe539bc3b04f97f
ORIGIN_MAIN_TREE=e3344ad5e8cd89d8b0be644e3f51e8647dd3c12a
P7C16_LAUNCHER_BLOB=2c500d7d5787a7eda71c1e3e3591d8034dded590
P7C16_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
P7C16_HELPER_BLOB=NONE
```

The Repair-2 changes are limited to this evidence file and
`tests/real/test_p7_c16_final_hard_delete_successor.py`. No `src/**`, package
marker, P7.C15/P7.C14/P7.C13/P7.C12 protected file, historical evidence or
historical ledger was changed.

## Repair-2 implementation proof

The real entrypoint now selects `P7C16PreparedFutureExecutor.production(contract)`
when `executor=None`. A module-local test-only production-factory seam supplies
the temporary ledger and offline child/runtime boundary without changing the
real ledger path. The exact synthetic handoff called:

```text
p7c16_source_bundle_gate
-> p7c16_real_entrypoint(executor=None)
-> production factory exactly once
-> temporary durable ledger reserve exactly once
-> two fresh run parents
-> root-only boot
-> one owned child
-> real cleanup coordinator constructor
-> real DialogueDeleteService constructor
-> one canonical delete
-> validated child PASS
-> COMPLETED ledger
```

Observed default-entrypoint proof:

```text
SOURCE_GATE=PASS
DEFAULT_PRODUCTION_SELECTION_COUNT=1
TEMP_LEDGER_RESERVE=1
OWNED_CHILD=1
REAL_CLEANUP_COORDINATOR=1
CANONICAL_DELETE=1
MODEL_LIST=1
THREAD_DELETE=1
RETRY=0
LEDGER=COMPLETED
PARENT_PROJECTION=0
REAL_CODEX_CALLS=0
```

The facade no longer exposes a fake-only `runtime_quiescent` property. The
successor authority computes quiescence only from delegated
`_runtimes`, `_starting` and `_unresolved` ownership maps. The real-shaped
matrix used a manager with no `runtime_quiescent` attribute and proved active
runtime, starting, unresolved, and all-empty-after-shutdown states as
false, false, false, and true respectively. The positive handoff uses this
same authority.

Late failure after delete-generation acquire is owned with
`p7c13._await_owned`, including finite cancellation/convergence joining:

```text
late failure + shutdown success: FAILED / runtime_child_quiescent=true / second child=0 / retry=0 / second delete=0
late failure + shutdown failure: FAILED / runtime_child_quiescent=false / second child=0 / retry=0 / second delete=0
```

The controller-path hook validates exact path/storage agreement before the
real coordinator constructor. After that constructor succeeds it records
`DELETE_CLEANUP_AUTHORITY_CONFIRMED`; after the real delete service constructor
succeeds it records `DELETE_CHAIN_READY`. The observed order is:

```text
CONTROLLER_BINDING
DELETE_CLEANUP_AUTHORITY_CONFIRMED
DELETE_CHAIN_READY
THREAD_DELETE_DISPATCH
THREAD_DELETE_RESULT
APPLICATION_DELETE_RESULT
```

Known controller authority failures translate to the safe finite class and
category without raw path disclosure:

```text
terminal_exception_class=P7C16ControllerStorageMismatch
terminal_error_category=controller_storage_mismatch
thread/delete=0
```

## Required negative and safety proof

The focused Repair-2 suite covers source/package mismatch before ledger,
controller mismatch, real-shaped active/starting/unresolved ownership,
successful and failed late convergence, real coordinator/service handoff,
one-shot second-call rejection, exact effect gating, root-only boot/result and
ledger authority, process-group gates, and disabled CLI projection. Existing
Repair-1 safety tests remain unchanged and continue to cover ledger-before-run
mutation, O_EXCL reservation, identity/mode/link/symlink checks, boot/result
correlation, authenticated production home, installed-runtime preflight, one
child, no retry, and exact effects.

No P7.C16 real token was created. No Codex/app-server, RPC, approval, ALLOW,
interrupt, thread delete, process signal, Telegram, persistent-home, or
historical ledger effect occurred.

```text
REAL_CODEX_PROCESS_STARTS=0
APP_SERVER_STARTS=0
REAL_RPC_CALLS=0
REAL_APPROVAL_RESPONSES=0
REAL_ALLOW=0
REAL_INTERRUPT=0
REAL_THREAD_DELETE=0
P7C16_REAL_LEDGER_CREATIONS=0
P7C15/P7C14/P7C13_LEDGER_MUTATIONS=0
PERSISTENT_HOME_MUTATIONS=0
HISTORICAL_CLEANUP=0
REAL_PROCESS_SIGNALS=0
TELEGRAM=0
```

## Validation

```text
focused P7.C16 Repair-2 unittest: 14 passed
gate-disabled smoke: exit 2; real ledger absent; run parents absent
default-entrypoint CLI projection: COMPLETED=0; FAILED/UNKNOWN/CONFIRMED_PENDING/TIMEOUT=nonzero
P7.C14/P7.C13/P7.C12 offline: 96 passed
P7.C2/P7.C3/P7.C4/P7.C5: 106 passed
complete non-real pytest: 1065 passed, 2 pre-existing warnings, 647 subtests
compileall: PASS
git diff --check: PASS
```

Unittest discovery with all real gates unset completed with:

```text
1921 tests run; 6 immutable historical failures; 1 immutable historical error; 7 skipped
```

The immutable discovery failures are the pre-existing P7.C7/P7.C8/P7.C9/
P7.C10/P7.C11 real-authority latch or parent-authority state, plus the
consumed P7.C15 `test_actual_source_gate_to_production_child_positive_handoff`
failure. No historical material was cleaned or modified.

Security/leakage scan: PASS. No real token, raw controller path, Telegram
effect, P8/P9 marker, or real-run invocation was added by Repair-2.

Changed-path scope: PASS. The final diff contains only the P7.C16 successor
test and this P7.C16 preparation evidence file.

P7C16_REPAIR1_PROTECTED_SOURCE_BUNDLE=PASS
P7C16_REPAIR1_UNDERLYING_RESERVATION_OWNERSHIP=PASS
P7C16_REPAIR1_ENGINE_PROFILE_AND_CONVERGENCE=PASS
P7C16_REPAIR1_REAL_PARENT_CHILD_WATCHDOG_PATH=PASS
P7C16_REPAIR1_ROOT_ONLY_LEDGER_BOOT_RESULT=PASS
P7C16_REPAIR1_AUTHENTICATED_PRODUCTION_HOME=PASS
P7C16_REPAIR1_PARENT_TERMINAL_EXIT_PROJECTION=PASS
P7C16_REPAIR1_REAL_COORDINATOR_FULL_HANDOFF=PASS

P7C16_REPAIR2_DEFAULT_REAL_ENTRYPOINT_PRODUCTION=PASS
P7C16_REPAIR2_REAL_RUNTIME_QUIESCENCE_AUTHORITY=PASS
P7C16_REPAIR2_OWNED_LATE_FAILURE_CONVERGENCE=PASS
P7C16_REPAIR2_SUCCESSOR_STAGE_AUTHORITY=PASS
P7C16_REPAIR2_CONTROLLER_ERROR_CATEGORY=PASS
P7C16_REPAIR2_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS
P7C16_PREP_READY=YES

P7C16_REAL_EXECUTION_AUTHORIZED=NO
P7C15_REAL_RETRY_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
