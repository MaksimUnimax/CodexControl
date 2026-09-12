# P7.C9 consumed real DENY-only approval probe — forensic architect review — 2026-09-12

Status: **FORENSIC ACCEPTED WITH ARCHITECT ROOT-CAUSE CORRECTION / P7.C9 PERMANENTLY CONSUMED / PRODUCTION DEFECT NOT ESTABLISHED**

## Reviewed authority

- Governance/forensic base: `f63dbfdb774d9154a31c73c4e43ae4214bfac341`, tree `01f825809c3404ca25b1919c12ce2e42c116b9ac`.
- Consumed executable: `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`, tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`.
- Real evidence commit: `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`.
- Forensic evidence head: `462e441cde02f9d21212dd583b8d965a2b1858cc`.
- Forensic evidence blob: `de0903e3e2668f79d39b3e44d690bdd016a5115a`.
- Forensic branch is evidence-only relative to the requested base: no source or test files changed.

## Accepted forensic facts

The retained run is uniquely established and the recovery journal is internally parseable with zero parse/schema errors.

Durable and corroborated facts:

- production state-root provision `CONFIRMED`, owner `TERMINALIZED`;
- production state-root validation `CONFIRMED`, owner `TERMINALIZED`;
- runtime acquire initial/final `RUNTIME_ACQUIRE_CONFIRMED`;
- model/list returned and model catalog was confirmed;
- fresh thread/start was confirmed;
- fresh primary turn/start was confirmed;
- persistent-session evidence establishes exactly one fresh P7.C9 Turn;
- the fresh Turn terminal status is `ABORTED`;
- command item count is `0`;
- structural approval request/decision/response counts are all `0`;
- no wire-command authority exists;
- workdir is empty and sentinel is absent;
- runtime shutdown was confirmed;
- boundary proof was durably recorded;
- child-result write was never reached;
- process group is quiescent and no TERM/KILL was used;
- fresh thread remains evidence-only and must not be resumed/read/listed/deleted by this lane.

The forensic report's chronological `JOURNAL_LAST_DURABLE_MILESTONE=BOUNDARY_PROOF_RECORDED` is retained. The business/control-flow stage immediately before the triggering failure is `TURN_START_CONFIRMED`.

## Exact root cause

The accepted P7.C9 harness calls:

`journal._append({"event": "TURN_ID_AUTHORITY", "result": "ESTABLISHED"})`

after the production turn adapter has returned `TurnStartStatus.CONFIRMED` and after the in-memory Turn future is set.

`RecoveryJournal._append()` applies `RecoveryJournal._safe()` to every record value. `_safe()` lowercases strings and rejects any string containing the marker `turn_id`.

Therefore the structural event value:

`TURN_ID_AUTHORITY`

is deterministically rejected as `JOURNAL_VALUE_UNSAFE` because its lowercase form contains `turn_id`.

This exactly explains the retained chronology:

1. `TURN_START_ADAPTER_RESULT=CONFIRMED` is durable;
2. no `TURN_ID_AUTHORITY` record exists;
3. no `APPROVAL_OBSERVER_ARMED` record exists;
4. the exception transfers control to `finally`;
5. runtime shutdown is confirmed;
6. boundary proof is recorded;
7. no child-result write is attempted;
8. persistent-session evidence shows the already-created Turn as `ABORTED`, with zero command/approval structures.

The production `CodexTurnLifecycleAdapter` does not provide a `CONFIRMED` result without a Turn binding: its confirmed return path constructs a `TurnBinding`, asserts non-null binding before publication, and then returns the confirmed result. The failure is therefore not a production turn-binding defect.

## Classification correction

The executor forensic report used:

`FAILURE_CLASS=UNKNOWN_NOT_ESTABLISHED`

Architect review can now narrow it deterministically to:

`FAILURE_CLASS=HARNESS_FAILURE`

`ROOT_CAUSE_CLASS=RECOVERY_JOURNAL_STRUCTURAL_EVENT_REJECTED_BY_GENERIC_SECRET_FILTER`

`ROOT_CAUSE_EVENT=TURN_ID_AUTHORITY`

`ROOT_CAUSE_EXCEPTION_CLASS=JOURNAL_VALUE_UNSAFE`

`P7C9_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C9_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_ABORTED`

`P7C9_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

## Disposition

P7.C9 is permanently consumed and must never be rerun.

No matcher is authorized. No hard-delete execution is authorized. The fresh P7.C9 thread/Turn remain evidence-only.

The next successor, if executed later, must use a new P7.C10 namespace and a schema-aware recovery-journal validator that permits the exact structural event `TURN_ID_AUTHORITY` while continuing to forbid raw thread/Turn identifiers and other protected payloads.

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C9_MATCHER_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked pending architect-accepted real P7 completion.
