# P7.C9 DENY-only approval-probe preparation — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE PRESERVED / REAL EXECUTION NOT AUTHORIZED**

## Reviewed authority

- Architect base: `7b3185874bc544fc28eb334aba70e4c74935cadc`, tree `7b27cf964c01d550273f5a35b97157d2be60d3cf`.
- Candidate: `097c8809a90eaca5d7d2074b35dc5e73ae9762c1`.
- Candidate tree: `c099c3a35acde82674f70413f55121c9345c82ba`.
- Harness blob: `0bccd8e80b362dd283773d6fea18a4a094018042`.
- Candidate is exactly one commit ahead of the architect base and changes only `tests/real/test_p7_c9_deny_only_approval_probe.py` plus the P7.C9 prep evidence file.
- Reported real effects: zero. No `src/**` change occurred.

## Correctly implemented and preserved

The P7.C9 candidate correctly fixes the P7.C8 state-root precondition defect:

- future real `FreshProbeRun.skeleton()` creates only the run root, state parent, controller and workdir; it does not create the isolated state root or marker/sqlite/logs;
- global P7.C9 latch reservation occurs before state-root provisioning;
- the future real route calls production `IsolatedStateRoot.provision(profile)` followed by production `IsolatedStateRoot.validate(profile)` before constructing/using the runtime manager;
- failed provision or validation blocks runtime acquisition and all model/list/thread/Turn/approval effects;
- the boundary scanner accepts the production-provisioned marker/sqlite/logs authority and re-validates it through production `IsolatedStateRoot.validate()`;
- parent state-root reconstruction is fail-closed for missing, unsafe, duplicate, conflicting and invalid chronology;
- P7.C8 runtime-acquire initial/final authority, bounded failed-acquire cleanup, DENY-only approval handling, exact 1/1/1 normal lifecycle ledger, immutable recovery journal, one-child/no-retry process-group authority and zero resume/interrupt/delete/read/list remain present;
- normal parent success requires state-root provision and validation both `CONFIRMED` with no state-root error categories.

## Blocking defect A — parent validator shadows runtime-acquire category

`validate_parent_execution_outcome()` first stores:

`category = value["runtime_acquire_error_category"]`

but later reuses the same local variable inside the state-root result/category loop:

`category = value[category_key]`

The subsequent `RUNTIME_ACQUIRE_NOT_ESTABLISHED` consistency gate tests that shadowed state-root category rather than the actual runtime-acquire category.

Therefore a contradictory failure outcome can carry:

- `runtime_acquire_result=RUNTIME_ACQUIRE_NOT_ESTABLISHED`,
- non-null `runtime_acquire_error_category`,
- null final state-root category,

and evade the intended `PARENT_OUTCOME_NOT_ESTABLISHED_FACTS_INVALID` check.

This does not authorize normal success, but it makes durable failure evidence semantically untrustworthy. A one-shot real probe cannot be authorized with that validator defect.

## Blocking defect B — state-root timeout does not establish worker terminalization

`bounded_state_root_operation()` starts a daemon `threading.Thread`, polls a `threading.Event`, and on deadline simply returns `("TIMEOUT", None)`.

It does not retain/join the worker thread or record whether the production filesystem operation actually terminalized. The timed-out worker can therefore continue running and mutating the fresh state-root after the durable `TIMEOUT` result has been recorded, until the child interpreter exits.

The parent process-group watchdog ultimately bounds the child process, but the harness currently lacks truthful per-operation ownership authority for state-root provisioning/validation timeout. The prep contract required a bounded owned child-side seam, not only a wall-clock classification.

Repair must make worker terminalization/nonconvergence explicit and must never allow a timed-out still-running state-root worker to coexist with normal continuation.

## Disposition

`P7C9_DENY_ONLY_APPROVAL_PROBE_PREP=REWORK_REQUIRED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C9_PREP_REPAIR1=REQUIRED_ZERO_REAL_EFFECT`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P7.C7 and P7.C8 remain permanently consumed. P8/P9 remain blocked.
