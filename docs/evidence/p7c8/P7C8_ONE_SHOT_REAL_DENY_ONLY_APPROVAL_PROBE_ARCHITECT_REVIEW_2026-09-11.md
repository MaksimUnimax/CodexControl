# P7.C8 one-shot real DENY-only approval probe — architect review — 2026-09-11

Status: **REAL PROBE CONSUMED / ROOT CAUSE ESTABLISHED / HARNESS PRECONDITION DEFECT / NO RERUN**

## Reviewed authorities

- Governance base before evidence: `733479251fe26159f0a40e04529d29a1ce82d2a1`, tree `ccb22edd1530e506c6712730d793948772914f7f`.
- Executed snapshot: `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`.
- Harness blob: `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`.
- Published real evidence commit: `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.
- Real evidence branch is exactly one evidence-only commit ahead of the governance base.

## Established real facts

The P7.C8 one-shot command started exactly once and is permanently consumed.

Published parent authority establishes:

- global P7.C8 latch present;
- normal result absent;
- parent outcome present and valid;
- `PARENT_EXECUTION_CLASS=CHILD_NONZERO`;
- `WATCHDOG_STATUS=PROCESS_COMPLETED`;
- `CHILD_RETURNCODE_CLASS=CHILD_NONZERO`;
- `RUNTIME_ACQUIRE_INITIAL_RESULT=RUNTIME_ACQUIRE_SAFE_EXCEPTION`;
- `RUNTIME_ACQUIRE_RESULT=RUNTIME_ACQUIRE_SAFE_EXCEPTION`;
- `RUNTIME_ACQUIRE_ERROR_CATEGORY=storage_boundary_invalid`;
- `RUNTIME_ACQUIRE_CLEANUP_RESULT=CONFIRMED`;
- no child result;
- active process-group members `0`;
- process-group scan errors `0`;
- no TERM/KILL;
- exactly one child and zero retries.

The final acquire class is a safe categorized production exception, not a timeout or ambiguous `NONCONVERGED` state. This validates the P7.C8 acquisition-observability repair.

## Exact root cause

The accepted P7.C8 harness constructs the fresh isolated state root manually. `FreshProbeRun.materialize()` creates:

- `state-parent/p7c8-isolated-state/`;
- `sqlite/`;
- `logs/`.

It does **not** create the production state-root marker `.codexcontrol-state-root-v1`.

Production `IsolatedStateRoot.validate()` delegates to `_validate_layout()`, which requires the exact entry set:

`{.codexcontrol-state-root-v1, sqlite, logs}`

and validates the marker as a root-owned `0600` regular file with exact content derived from the profile ID.

Therefore the manually-created P7.C8 isolated state root is structurally invalid under the production contract. `CodexRuntimeManager._start()` catches the resulting `IsolationError` and correctly exposes only the safe external category `RuntimeErrorSafe("storage_boundary_invalid", profile_id)`.

This directly explains the real P7.C8 outcome before app-server initialization, model/list, thread/start, turn/start or approval observation.

## Classification

`P7C8_FAILURE_CLASS=HARNESS_PRECONDITION_DEFECT`

`P7C8_ROOT_CAUSE=ISOLATED_STATE_ROOT_NOT_PROVISIONED_BY_PRODUCTION_AUTHORITY`

`P7C8_RUNTIME_ACQUIRE_RESULT=RUNTIME_ACQUIRE_SAFE_EXCEPTION`

`P7C8_RUNTIME_ACQUIRE_ERROR_CATEGORY=storage_boundary_invalid`

`P7C8_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C8_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

## Correct successor requirement

P7.C8 must not be rerun.

The next successor is P7.C9. It must use a new one-shot namespace and must create the fresh isolated state root through the production `IsolatedStateRoot.provision(profile)` authority rather than manually creating the state-root layout.

The P7.C9 preparation must prove offline that:

1. before provisioning the state root does not exist;
2. `IsolatedStateRoot.provision(profile)` creates the exact marker/sqlite/logs layout;
3. `IsolatedStateRoot.validate(profile)` passes immediately afterward;
4. manual marker fabrication is not used;
5. provisioning occurs before runtime acquire and before any Codex RPC;
6. a provisioning failure prevents runtime acquire and all downstream effects;
7. P7.C8 global/root evidence remains untouched.

## Binding prohibitions

- no P7.C8 rerun;
- no P7.C8 thread/Turn creation;
- no approval response;
- no cleanup or rewriting of P7.C8 retained evidence;
- no P7.C7 rerun or mutation;
- no hard-delete execution;
- no matcher authorization.

## Disposition

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_MATCHER_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`NEXT=P7C9_DENY_ONLY_APPROVAL_PROBE_PREPARATION`

P8/P9 remain blocked.
