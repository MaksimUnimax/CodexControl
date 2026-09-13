# P7.C15 hard-delete successor preparation evidence — 2026-09-12

Status: **PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Binding source

The preparation branch was fetched and checked out without merge or rebase.

```text
branch=prep-p7-c15-hard-delete-successor-repair3-2026-09-13
P7C15_REPAIR3_BASE_HEAD=52e20e42e451955ba0d417a47d89903cadf142f2
P7C15_REPAIR3_BASE_TREE=03c555267442b8ce6df5255e08152c2cd112908c
PRIOR_P7C15_LAUNCHER_BLOB=7303cebc8fd157ecef590b4ec9575453ee982176
PRIOR_P7C15_EVIDENCE_BLOB=5cde70aea9e3b7d089deece991b677e6ea61b74e
P7C15_REPAIR2_BASE_HEAD=3dc12289fc34b4beac67e7139d740852c5caa2dc
P7C15_REPAIR2_BASE_TREE=09446141fcb30875f0b8d081bd68b66ac6e73899
origin/main=064acac971d825e2bf8593930fda79d7ef5d3559
origin/main_tree=51b86d12404fe616369a5e9394d8b71ef80ee54a
FINAL_P7C15_LAUNCHER_BLOB=5e964d9408413b968b03e334759037f906174ffd
FINAL_P7C15_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
FINAL_P7C15_HELPER_BLOB=NONE
P7C15_REPAIR3_LAUNCHER_BLOB=5e964d9408413b968b03e334759037f906174ffd
P7C15_REPAIR3_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
P7C14_RETAINED_FORENSIC_ACCEPTANCE_BLOB=0624a5d3c2dd784d97d8ab94d612b33f05fcc1b5
INHERITED_P7C14_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8
INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c
INHERITED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1
TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a
TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3
```

Repair-1 production integration is preserved in the successor module.
`P7C15PreparedFutureExecutor.production()` reserves the distinct P7.C15
one-shot ledger, selects one high-entropy `p7c15-*` authority set, creates a
boot-bound root-only authority, starts one owned child/watchdog, validates the
root-only child result, and maps the terminal result into the P7.C15 ledger.
The production command is exactly the deterministic `/usr/bin/env` form and
passes the actual boot authority path, never the child-result path.

The child CLI requires exactly one boot authority, creates the stage journal
before business effects, enters `P7C15ProductionChildOrchestrator` once, and
writes one bounded child result.  Repair-2 now executes the accepted C11/C12
approval, Turn-4 interrupt, schema-v4 controller, canonical
`DialogueDeleteService`, independent official observation, and observed
physical-oracle continuation in that same production child path.  Fakes are
injected only at runtime/client/storage-cleanup boundaries; no real adapter or
external effect was invoked during preparation.

Repair-1 focused proof:

```text
focused P7.C15 Repair-2: 22 passed, 10 subtests passed
production-shaped positive: COMPLETED / PASS / one child / retry=0
production-shaped failure: FAILED / TurnLifecycleError / turn_precondition_changed / retry=0
BOOT_ARG_IS_BOOT_PATH=YES
MODEL_LIST_DISPATCHES=1
TURN2_START_DISPATCHES=1
FAKE_OWNED_CHILD_DISPATCHES=1
TEMP_LEDGER_RESERVATIONS=1
P7C14_LEDGER_ACCESS=0
P7C13_LEDGER_ACCESS=0
REAL_CODEX_CALLS=0
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

## Repair-2 continuation proof

The production-shaped positive test traverses the source gate, actual P7.C15
executor, temporary one-shot ledger, fresh boot authority, owned child/watchdog
seam, child dispatcher, `P7C15ProductionChildOrchestrator`, fake runtime/client,
actual lifecycle adapters, SQLite storage, canonical delete service, official
observer, and observed post-delete gate.  It records these actual fake facts:

```text
TEMP_P7C15_LEDGER_RESERVATIONS=1
OWNED_CHILD_DISPATCHES=1
MODEL_LIST=1
THREAD_START=1
THREAD_RESUME=1
TURN_START=4
TURN3_APPROVAL_REQUEST=1
PROTOCOL_RESPONSE=1
ALLOW=1
DENY=0
TURN4_INTERRUPT=1
CONTROLLER_BINDINGS=1
CANONICAL_DELETE_SERVICE_CALLS=1
OFFICIAL_DELETE_OBSERVATIONS=1
SECOND_DELETE=0
RETRY=0
P7C14_LEDGER_ACCESS=0
P7C13_LEDGER_ACCESS=0
REAL_CODEX_CALLS=0
```

The approval operator is `P7C15ProductionApprovalOperator`, composed from the
accepted `ProductionApprovalOperator` semantics.  It uses root-only
`P7C15`-bound wire and recovery authorities and the accepted strict matcher
`MATCH_EXACT_P7_APPROVAL_COMMAND`.  The fake client receives one actual Turn-3
request, emits one actual bridge response with one ALLOW, and creates the exact
target only after that response.  The target proof checks regular/root-owned,
nlink 1, mode 0600, non-symlink metadata before exact-target cleanup.

Turn 4 uses the accepted one terminal waiter plus one unexpected-request
observer through interrupt convergence.  The exact stimulus is `sleep 120`;
the observer proves active/nonterminal state before reserving and dispatching
one interrupt, remains owned through join, and rejects requests or terminal
before active proof.

The controller proof opens fresh SQLite storage, observes schema version 4,
creates one P7.C15 dialogue intent, confirms its exact thread, and durable
re-reads `IDLE` with the exact current profile/thread before recording
`CONTROLLER_BINDING`.  The canonical `DialogueDeleteService.delete()` is
called once.  `THREAD_DELETE_RESULT` is sourced from one independent
`OfficialDeleteObservation`; `APPLICATION_DELETE_RESULT` is sourced from the
actual service result.  Official UNKNOWN maps to child/ledger UNKNOWN, and
official confirmed plus application CONFIRMED_PENDING_STORAGE maps to
CONFIRMED_PENDING; neither path retries or dispatches a second delete.

The positive post-delete gate observes schema 4, a bounded exact tombstone,
absent live binding, valid isolation, zero isolated descendants, zero
target-specific persistent/isolated thread and marker residuals, zero scan
errors, no unrelated removal, and runtime child quiescence.  It accepts only
those observed facts; missing tombstone, live binding, scan/proof error,
residual material, or missing effect counts fails closed.

The required continuation negatives are production-shaped fake runs for strict
matcher mismatch, second approval request, invalid target metadata, unexpected
Turn-4 request, terminal-before-active, inconclusive pre-delete oracle,
durable controller mismatch, DELETE_UNKNOWN, CONFIRMED_PENDING_STORAGE,
post-delete residual, scan error, and missing tombstone.  They prove no ALLOW
on mismatch, no second response, no controller/delete eligibility before
proof, one delete dispatch maximum, and zero retry.  A separate oracle test
proves retained historical P7.C14 material is unrelated to a fresh P7.C15
thread target.

Stage/effect coupling is explicit: dispatch stages precede actual calls;
confirmation stages follow returned bindings/results; approval request is
recorded from the correlated operator callback before response/ALLOW; the
controller stage follows durable re-read; delete dispatch precedes the actual
service call; official/application result stages follow their independent
facts; and `POST_DELETE_ORACLE` follows the observed acceptance gate.  No
stage-only continuation or synthetic `delete` PASS remains.

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
focused P7.C15 Repair-1: 18 passed
P7.C14/P7.C13/P7.C12 offline regression: 96 passed, 128 subtests passed
P7.C2/P7.C3/P7.C4/P7.C5 fake/non-real: 106 passed, 54 subtests passed
full pytest: 1889 passed, 7 skipped, 6 retained historical P7.C7-P7.C11 failures
unittest discovery: 1902 tests, 7 skipped, 5 retained historical-latch failures, 1 retained historical-authority error
Repair-2 production-shaped full continuation: PASS; positive exact effect counts and 10 negative subtests passed
gate-disabled module smoke: exit 2; P7.C15 production ledger absent; real Codex/app-server starts 0
P7.C2/P7.C3/P7.C4/P7.C5 explicit files: 106 passed, 54 subtests passed
leakage/security scan: PASS; no raw secret/token/prompt leakage or forbidden synthetic delete marker
changed-path scope: PASS; exactly two allowed P7.C15 files
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
P7C15_REPAIR1_PRODUCTION_PARENT_CHILD_PATH=PASS
P7C15_REPAIR1_REAL_CHILD_DISPATCHER_PREPARED=PASS
P7C15_REPAIR1_FRESH_BOOT_RESULT_AUTHORITY=PASS
P7C15_REPAIR1_PRODUCTION_GENERATION_REBOUND=PASS
P7C15_REPAIR1_PRODUCTION_FAILURE_ACCOUNTING=PASS
P7C15_REPAIR1_PRODUCTION_STAGE_JOURNAL=PASS
P7C15_REPAIR1_PARENT_TERMINAL_PROJECTION=PASS
P7C15_REPAIR1_EXACT_AUTHORIZED_PRODUCTION_SHAPED_HANDOFF=PASS

P7C15_REPAIR2_REAL_TURN3_APPROVAL_PATH=PASS
P7C15_REPAIR2_REAL_TURN4_INTERRUPT_PATH=PASS
P7C15_REPAIR2_REAL_CONTROLLER_BINDING=PASS
P7C15_REPAIR2_CANONICAL_DELETE_CHAIN=PASS
P7C15_REPAIR2_OFFICIAL_APPLICATION_DELETE_SEPARATION=PASS
P7C15_REPAIR2_REAL_POST_DELETE_ORACLE=PASS
P7C15_REPAIR2_STAGE_EFFECT_COUPLING=PASS
P7C15_REPAIR2_PRODUCTION_SHAPED_FULL_HANDOFF=PASS
P7C15_PREP_READY=YES

P7C15_REAL_EXECUTION_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO
P9_STARTED=NO

## Repair-3 final production-hardening preparation

Repair-3 was executed from the exact Repair-2 candidate above, without merge,
rebase, squash, history rewrite, historical retry, real authorization token,
real Codex process, app-server, RPC, approval, interrupt, delete, Telegram, or
P7.C14 orphan cleanup. The only tracked changes are this evidence file and
the P7.C15 successor launcher.

The child now derives the selected default model and reasoning effort from the
single authenticated catalog by model identity. Its immutable semantic
snapshot is rebound only to confirmed runtime generation authority. The
non-first-default offline catalog selected `wire-selected` with effort `fast`
for all four turns and dispatched exactly one model/list.

Turn 1 and Turn 2 use fresh bounded in-memory markers. The completed agent
messages were checked for the response marker before generation restart and
the exact memory marker after generation-2 resume. Marker plaintext is not
written to the stage journal or Git evidence. The fake client exposes the
public protocol operations only; it has no response-count or pending-request
test property. After the first bridge response, one owned
`next_server_request()` observer remained live through Turn-3 terminal
convergence. A second request failed closed and left the one response intact;
the observer was joined before Turn 4 and sent no response.

The child installs `umask(0o077)` before runtime construction and restores it
in `finally`. The touch-style fake target was observed as root-owned, regular,
nlink 1, non-symlink, mode `0600`; an ambient `0644` target failed before
Turn 4. Production watchdog construction selects
`p7c13.REAL_WATCHDOG_HARD_DEADLINE`, TERM grace, and KILL grace. The hard
deadline is greater than the sum of `REAL_STAGE_TIMEOUTS` plus margin; short
bounds are available only through an explicit offline injection seam.

Every potentially blocking runtime, lifecycle, approval, observer, storage,
delete, oracle, schema, and close operation is bounded through owned waits.
The injected runtime-acquire timeout completed finitely, cancelled and joined
its owned task, dispatched no later RPC, and recorded retry zero.

Before delete, a conclusive target-specific oracle was followed immediately by
the metadata snapshot `unrelated_before` and `target_paths`. After the single
canonical `DialogueDeleteService.delete()`, persistent and isolated oracles
were independently observed for their respective families. Persistent thread,
marker, and scan residuals were zero; isolated thread, marker, and scan
residuals were zero. `unrelated_after` was collected and the derived
`derived_unrelated_removal_fact(...)` was passed to acceptance. Isolation
authority validation plus sqlite/log special-descendant and symlink counts
passed. `PRAGMA user_version` was independently re-read after delete and was
exactly 4. Live binding absence, bounded tombstone, official delete status,
application status, and runtime-child quiescence were all observed.

Parent-owned process-group facts remain unknown in the child result. The
parent gate independently requires watchdog COMPLETED, valid root-only child
result, child PASS/verdict/quiescence, active group 0, zombies 0, scan errors
0, one child, retry 0, and the exact positive effect matrix:

```text
new_threads=1 model/list=1 thread/start=1 thread/resume=1 turn/start=4
approval_responses=1 allow_responses=1 turn/interrupt=1 thread/delete=1
thread/read=0 thread/list=0 second_child=0 real_retry=0 telegram=0
```

Production-shaped full handoff counts were one child, one model/list, one
thread/start, one thread/resume, four turns, one approval request, one wire
response, one ALLOW, zero DENY, one interrupt, one controller binding, one
canonical delete and one independent official observation. UNKNOWN,
CONFIRMED_PENDING_STORAGE, missing/invalid tombstone, live binding, schema
drift, persistent-only residual, isolated-only residual, scan/proof error,
unrelated removal, invalid isolation envelope, missing marker, invalid target,
second request, and missing required effect all remained non-PASS with no
retry or second destructive effect. Turn-4 unexpected request prevented
controller/delete continuation.

Repair-3 focused totals: 30 tests, 15 negative subtests, all passed. The
historical Repair-2 continuation remains covered by the same focused run.

P7C15_REPAIR3_REAL_CLIENT_APPROVAL_AUTHORITY=PASS
P7C15_REPAIR3_TURN1_TURN2_MEMORY_PROOF=PASS
P7C15_REPAIR3_REASONING_AUTHORITY=PASS
P7C15_REPAIR3_PRIVATE_UMASK_TARGET=PASS
P7C15_REPAIR3_REAL_WATCHDOG_BOUNDS=PASS
P7C15_REPAIR3_STAGE_TIMEOUT_OWNERSHIP=PASS
P7C15_REPAIR3_POST_DELETE_OBSERVED_AUTHORITY=PASS
P7C15_REPAIR3_EXACT_EFFECT_PASS_GATE=PASS
P7C15_REPAIR3_PRODUCTION_SHAPED_FULL_HANDOFF=PASS
P7C15_REPAIR3_FINAL_LAUNCHER_BLOB=5e964d9408413b968b03e334759037f906174ffd
P7C15_REPAIR3_FINAL_EVIDENCE_BLOB=COMPUTED_AFTER_FINAL_EVIDENCE_EDIT
P7C15_REPAIR3_HELPER_BLOB=NONE
P7C15_PREP_READY=YES

P7C15_REPAIR3_REAL_CLIENT_APPROVAL_AUTHORITY=PASS
P7C15_REPAIR3_TURN1_TURN2_MEMORY_PROOF=PASS
P7C15_REPAIR3_REASONING_AUTHORITY=PASS
P7C15_REPAIR3_PRIVATE_UMASK_TARGET=PASS
P7C15_REPAIR3_REAL_WATCHDOG_BOUNDS=PASS
P7C15_REPAIR3_STAGE_TIMEOUT_OWNERSHIP=PASS
P7C15_REPAIR3_POST_DELETE_OBSERVED_AUTHORITY=PASS
P7C15_REPAIR3_EXACT_EFFECT_PASS_GATE=PASS
P7C15_REPAIR3_PRODUCTION_SHAPED_FULL_HANDOFF=PASS
P7C15_PREP_READY=YES

P7C15_REAL_EXECUTION_AUTHORIZED=NO
P7C14_REAL_RETRY_AUTHORIZED=NO
P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO
P9_STARTED=NO
