# P7.C8 DENY-only approval-probe preparation Repair-1 — architect acceptance — 2026-09-11

Status: **ARCHITECT ACCEPTED / ZERO-REAL-EFFECT PREPARATION COMPLETE / REAL PROBE MAY BE SEPARATELY AUTHORIZED**

## Accepted executable authority

- Repair-1 commit: `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`.
- Repair-1 tree: `787e083077b7386a8b05968f2193c611d8182d9d`.
- P7.C8 harness blob: `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`.
- Repair-1 evidence blob: `c3c4dc55e4afe75b96c6a15919e4492e0b57cb4f`.
- Architect base: `2b6e514f419e263af62530232f8220cd4079f953`, tree `6d774ecf66e38f82b1b5ac530205919c2850780f`.
- Candidate is exactly one commit ahead of the base and changes only the allowed P7.C8 harness and Repair-1 evidence file. No `src/**` change occurred.

## Independent acceptance findings

Repair-1 closes the acquisition-authority blockers found in the initial P7.C8 prep:

- failed-acquire cleanup owns exactly one `shutdown_profile()` task;
- cleanup timeout is bounded at 12 seconds and cancellation/join is separately bounded at 1 second;
- cancellation-resistant cleanup is classified `NONCONVERGENT` rather than awaited without bound;
- acquisition has distinct durable initial and final authorities (`RUNTIME_ACQUIRE_RESULT` and `RUNTIME_ACQUIRE_FINAL_RESULT`);
- the child uses the post-containment `AcquireObservation`, so escalation to `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` is retained;
- parent reconstruction never defaults missing/unsafe acquisition evidence to `CONFIRMED`; it uses `RUNTIME_ACQUIRE_NOT_ESTABLISHED`;
- parent acquisition evidence is read through a bounded no-follow stable-identity JSONL reader rather than ordinary `Path.read_text()`;
- cleanup safe categories are persisted in a separate `RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY` event and no invalid keyword route remains through `RecoveryJournal.result()`;
- the finite safe category set covers the reviewed production `RuntimeErrorSafe` categories reachable through `CodexRuntimeManager.acquire()`, `_start()` and failed-acquire `shutdown_profile()` containment;
- an unrecognized syntactically safe category is replaced by the fixed safe classification `SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED`, never raw text;
- failed acquisition has zero downstream model/list, thread/start, turn/start, approval, resume, interrupt, delete, read or list effects;
- normal parent success requires acquisition initial/final `CONFIRMED`, no acquisition error category and no acquire-cleanup result/category;
- missing, unsafe, duplicate, conflicting or inconsistent acquisition journal authority is rejected from normal success.

The carried P7.C8 safety design remains present: DENY-only operator, zero ALLOW path, maximum three DENY attempts, exact Turn authority before dequeue, exact thread/Turn/cwd wire-capture identity, immutable recovery-journal identity, one child/no retry, exact process-group signal authority, exact normal `1/1/1` lifecycle ledger, child/parent result separation and post-quiescence boundary proof.

## Time authority

Frozen future-real values in the accepted snapshot:

- runtime acquire ceiling: 45s;
- failed-acquire cleanup: 12s;
- cleanup cancel/join: 1s;
- candidate sleep: 30s;
- approval/terminal observation: 100s;
- normal-path internal budget: 186s;
- failed-acquire bounded main-coroutine budget: 64s;
- watchdog margin: 15s;
- parent hard watchdog: 205s.

The dedicated parent process-group watchdog remains the final process owner if an internal cleanup task is cancellation-resistant and prevents the child interpreter from exiting normally.

## P7.C7 boundary

P7.C7 remains permanently consumed and forensic-only. P7.C8 uses a new auth token, profile, parent/run namespace and global latch/result/outcome files. No P7.C7 rerun or state reuse is authorized.

## Disposition

`P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1=ARCHITECT_ACCEPTED`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_REAL_APPROVAL_PROBE_PREPARATION=COMPLETE`

The preparation itself authorizes no real effect. A separate exact-snapshot one-shot execution contract is required before real P7.C8 execution.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

P8/P9 remain blocked.
