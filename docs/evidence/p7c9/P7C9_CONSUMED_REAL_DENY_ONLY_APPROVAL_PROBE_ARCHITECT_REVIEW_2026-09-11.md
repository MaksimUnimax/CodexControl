# P7.C9 consumed real DENY-only approval probe — architect review — 2026-09-11

Status: **REAL PROBE CONSUMED / GLOBAL EVIDENCE ACCEPTED / POST-ACQUIRE FAILURE STAGE NOT YET ESTABLISHED / ZERO-EFFECT FORENSIC REQUIRED**

## Accepted real evidence

Execution snapshot:

- HEAD `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`;
- tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`;
- harness blob `44271459c2b4523f97551ade93563aee96def1c3`.

Sanitized real evidence commit: `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`.

The evidence branch is exactly one commit ahead of the pre-run governance main and adds only `docs/evidence/p7c9/P7C9_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_EVIDENCE_2026-09-11.md`.

## Established facts

- `REAL_PROBE_ATTEMPTS=1` and rerun is permanently forbidden.
- Global latch exists.
- Normal result is absent.
- Parent outcome exists and validates.
- Parent execution class is `CHILD_NONZERO` under `WATCHDOG_STATUS=PROCESS_COMPLETED`.
- Process group is quiescent: active=0, zombie=0, scan errors=0; no TERM/KILL was required.
- Exactly one child was started; zero retries.
- Production state-root provisioning was `CONFIRMED`, owner `TERMINALIZED`.
- Production state-root validation was `CONFIRMED`, owner `TERMINALIZED`.
- Runtime acquire initial/final result was `RUNTIME_ACQUIRE_CONFIRMED` with no acquire error or cleanup authority.
- Child result is absent.
- Parent boundary was not proved and drift is conservatively `BOUNDARY_DRIFT_DETECTED` because the child did not reach normal result authority.

## What is not established

The global parent outcome does not establish which post-acquire stage failed. In the accepted child control-flow, post-acquire stages are durably journaled in this order:

1. model/list wire dispatch/result and `MODEL_CATALOG` result;
2. thread/start wire dispatch/result and `THREAD_START_ADAPTER` result;
3. turn/start wire dispatch/result and `TURN_START_ADAPTER` result;
4. `TURN_ID_AUTHORITY`;
5. `APPROVAL_OBSERVER_ARMED` and approval/terminal observation;
6. `RUNTIME_SHUTDOWN`;
7. `BOUNDARY_PROOF`;
8. `CHILD_RESULT_WRITE`.

Therefore no fresh-thread, Turn, approval, wire-command, sentinel or downstream effect fact may be inferred merely from the missing normal result.

## Disposition

`P7C9_REAL_PROBE_RESULT=FAILURE_OR_AMBIGUITY_ARCHITECT_REVIEW_REQUIRED`

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C9_FRESH_THREAD_DISPOSITION=NOT_ESTABLISHED`

`P7C9_MATCHER_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO_NOT_YET_EVALUATED_POST_ACQUIRE`

Next slice: zero-real-effect retained-run forensic only. No app-server startup, no thread read/list, no new RPC, no signal and no retained-state cleanup.

P8/P9 remain blocked.
