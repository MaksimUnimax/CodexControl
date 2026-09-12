# P7.C15 hard-delete successor preparation evidence — 2026-09-12

Status: **PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Binding source

The preparation branch was fetched and checked out without merge or rebase.

```text
branch=prep-p7-c15-hard-delete-successor-2026-09-12
P7C15_PREP_BASE_HEAD=98e168c82f7fd9d8f50c491017323e97d3ed396f
P7C15_PREP_BASE_TREE=cd2bff744a24019090612c5ed61c70ee11927c3a
origin/main=7ac2bdfe2dea449f8addbff20485bd2ffc17c26f
origin/main_tree=139e93b894f3bd0d5baf04ef5de2016b909182ba
P7C15_LAUNCHER_BLOB=37b5926ad998fb146bba154546059d9d1439bb38
P7C14_FORENSIC_EVIDENCE_BLOB=648a149e4210ae40fdb44d1669d17f5c0e689af4
INHERITED_P7C14_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8
INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c
INHERITED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1
TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a
TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3
```

The two binding documents were read in full directly from `origin/main`:
the retained P7.C14 forensic architect acceptance and the frozen P7.C15
successor preparation contract.

## Root cause and generation correction

The new module reproduces the accepted P7.C14 boundary with fake runtime,
catalog, client, thread resume, and strict turn adapter:

```text
generation 1 acquire -> one authenticated model/list -> generation 1 shutdown
-> generation 2 acquire -> thread/resume confirmed
-> stale generation-1 catalog -> TurnLifecycleError.category=turn_precondition_changed
-> fake turn/start dispatch count=0
```

`src/codex_control/adapters/codex/turn_lifecycle.py` is unchanged.  The
successor uses `GenerationTrackingRuntimeManager`, an immutable
`ImmutableSemanticCatalogSnapshot`, and `GenerationReboundCatalogView`.  The
view changes only `runtime_generation`; models, model IDs, wire IDs, default,
supported efforts, default effort, and profile identity remain the generation-1
snapshot.  Generation regression and profile mismatch fail closed.

The corrected fake restart/resume path reaches exactly one Turn-2 `turn/start`
RPC while total fake `model/list` dispatch remains one.  The explicit
`P7C15SingleCatalogAcquisition` guard blocks a second semantic acquisition.

## Accounting and safe journal

P7.C15 child failure serialization selects the live child budget:

```text
actual_budget = child.budget if child is not None else pre_child_budget
```

The fake forced-failure child records `model/list=1`, `thread/start=1`, and
`turn/start=1`; the serialized failure retains those values and is not all
zeroes.  Pre-child failure uses the outer pre-child budget.  Effect ceilings
are enforced before every recorded effect.

`P7C15StageJournal` creates an exclusive root-only `0600` regular file with
bounded bytes and records, monotonic unique sequences, finite safe fields, and
no raw thread/turn IDs, prompt, response, wire plaintext, or raw token.  The
synthetic positive handoff records 20 safe milestones; forced failure records
the terminal exception class/category and last confirmed stage.  The persisted
category is `turn_precondition_changed`.

## Distinct authorities and synthetic handoff

The successor defines the distinct gate, expected-source variables, parent and
child CLIs, `/root/.codexcontrol/p7c15-one-shot.json` replay barrier, P7.C15
profile, P7.C15 boot schema, P7.C15 ledger schema, and fresh path authorities:

```text
p7c15-isolated-*
p7c15-controller-*
p7c15-work-*
p7c15-approval-*
p7c15-boot-*
p7c15-child-result-*
p7c15-wire-*
p7c15-approval-journal-*
p7c15-stage-*
```

Temporary synthetic proof results:

```text
TEMP_P7C15_LEDGER_RESERVATIONS=1
P7C14_LEDGER_ACCESS=0
P7C13_LEDGER_ACCESS=0
SYNTHETIC_MODEL_LIST_DISPATCHES=1
SYNTHETIC_TURN2_START_DISPATCHES=1
REAL_CODEX_CALLS=0
REAL_CHILD_CALLS=0
positive temporary ledger=COMPLETED
forced-failure temporary ledger=FAILED
second child/retry=0
```

The forced failure has a non-PASS child result, nonzero parent projection,
persisted stage digest/category/last stage, and no retry.  The P7.C15 ledger
tests prove first reservation success and reservation failure after each of
`RESERVED`, `COMPLETED`, `FAILED`, `UNKNOWN`, `CONFIRMED_PENDING`, and
`TIMEOUT`.  Its schema and path are distinct from P7.C14 and P7.C13.

The target-oracle test rejects unrelated historical `p7c14-*` material.  No
P7.C14 orphan, isolated material, historical ledger, or historical evidence
was cleaned or modified.  No P7.C15 real ledger was created.

## Parent projection and smoke

The direct projection is:

```text
gate/source disabled=2
executed PASS=0
executed FAIL=1
UNKNOWN=1
CONFIRMED_PENDING=1
TIMEOUT=1
```

With exact `PYTHONPATH=/root/CodexControl/src:/root/CodexControl`, import smoke
passed and `--p7c15-real-run` with all P7.C15 variables unset returned 2.  No
Codex/app-server process was started and no P7.C15 real ledger was created.

## Validation

```text
focused P7.C15: 14 passed
P7.C14/P7.C13/P7.C12 offline regression: 96 passed, 128 subtests passed
P7.C2/P7.C3/P7.C4/P7.C5 fake/non-real: 106 passed, 54 subtests passed
full pytest: 1873 passed, 7 skipped, 6 retained historical-latch failures
unittest discovery: 1882 tests, 7 skipped, 5 retained historical-latch failures, 1 retained historical-authority error
compileall: PASS
git diff --check: PASS
```

The full pytest and unittest failures are pre-existing consumed P7.C7–P7.C11
latch/static-authority assertions (including retained P7.C11 pre-existing
parent authority).  They were not repaired, removed, or mutated because this
preparation is prohibited from altering historical authorities.  No P7.C14 or
P7.C13 real parent was invoked.

Zero-real-effect accounting for this preparation:

```text
REAL_CODEX_PROCESS_STARTS=0
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
P7C13_LEDGER_MUTATIONS=0
P7C14_LEDGER_MUTATIONS=0
P7C15_REAL_LEDGER_CREATIONS=0
PERSISTENT_HOME_MUTATIONS=0
P7C14_ORPHAN_MUTATIONS=0
TELEGRAM_CALLS=0
PROCESS_SIGNALS=0
```

P7C15_PREP_P7C14_ROOT_CAUSE_REPRODUCTION=PASS
P7C15_PREP_GENERATION_REBOUND_CATALOG=PASS
P7C15_PREP_SINGLE_MODEL_LIST=PASS
P7C15_PREP_FAILURE_ACCOUNTING=PASS
P7C15_PREP_STAGE_CATEGORY_JOURNAL=PASS
P7C15_PREP_PARENT_EXIT_PROJECTION=PASS
P7C15_PREP_DISTINCT_GATE_LEDGER=PASS
P7C15_PREP_EXACT_AUTHORIZED_SYNTHETIC_HANDOFF=PASS
P7C15_PREP_READY=YES

P7C15_REAL_EXECUTION_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO
P9_STARTED=NO
