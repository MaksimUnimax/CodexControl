# P7.C7 DENY-only approval-probe preparation Repair-1 — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `9f2f3c1f1b5913da34e97f4fd23dc8dbf379df70`.
- Base tree: `19f65356540c418c6c7cc911ecc8f95b6d39caa8`.
- Repair-1 candidate: `bffe4d05340545edd44d503c9a16f1128c65ca7d`.
- Candidate tree: `2378c6f0c2b605413cd36c8383d01ee5f0c8f887`.
- Candidate diff is exactly one commit and changes only the P7.C7 test harness plus Repair-1 evidence. No `src/**` change occurred.

## Repair-1 improvements accepted as useful

Independent source review confirms Repair-1 substantially closes the initial preparation defects:

- the approval operator still has no ALLOW path;
- authoritative raw wire capture now requires command-execution kind plus exact thread/Turn/cwd identity;
- wrong thread/Turn/cwd no longer consumes the exclusive wire authority;
- sentinel observation is no longer a substring identity match and distinguishes exact argv token, embedded occurrence, absence and unreconstructable vector;
- wire authority has an exact validated schema and plaintext/hash consistency check;
- race classification is fact-based and the frozen same-tick fixture now has one deterministic class;
- `RESPONSE_UNKNOWN` is explicitly classified as ambiguous;
- DENY response capacity is represented separately from ALLOW capacity;
- runtime-owned sqlite/log payloads are separated conceptually from command-owned mutation surface;
- exact zero-length safe sentinel touch authority exists;
- the synthetic signal helper records exact group signals and prevents a second TERM/KILL of the same kind;
- a full future adapter path is now present behind an unset real gate.

These improvements remain binding for the next repair.

## Remaining blocker A — approval observation is armed before exact Turn authority exists

The future real path creates `_drain_future_approvals(...)` before `turn/start`, then resolves `turn_future` only after `TURN_START_CONFIRMED`.

If a real approval request is dequeued during that interval, the DENY decision is safe, but the operator sees `expected_turn=None`. Exact-identity wire capture therefore intentionally refuses to create the wire authority. A single approval request can consequently be consumed and denied while the only purpose of the probe — authoritative wire-grammar capture — is lost.

Production protocol authority already buffers server requests in `CodexProtocolClient._server_requests`; an approval request may remain queued until `next_server_request()` is called. Repair-2 must therefore establish exact Turn identity first and then start the approval observer and exact-turn terminal waiter together. It must prove a request queued before observer start is still captured and denied after Turn confirmation.

## Remaining blocker B — process-group watchdog is not the future real executor

Repair-1 contains a synthetic `run_synthetic_watchdog(...)`, but `test_future_real_deny_only_approval_probe()` directly awaits `future_real_deny_only_approval_probe()`.

The inner coroutine itself requires the current process to already satisfy `PID=PGID=SID`; an ordinary unittest process is not thereby converted into the accepted dedicated-session execution model. More importantly, the real method has no parent process that owns a hard deadline and exact-group TERM/KILL authority.

The future real acceptance must have exactly one parent launcher which starts exactly one dedicated child with `start_new_session=True`, owns the finite hard deadline, owns exact PGID termination, verifies final group quiescence, and only then validates/publishes the final sanitized result.

## Remaining blocker C — unbounded inner waits and incomplete failure cleanup

The future real coroutine performs runtime acquire/catalog/thread-start/turn-start/`wait_turn()`/approval drain/shutdown without one frozen finite task-ownership model. `wait_turn()` is directly awaited with no finite bound. `manager.shutdown_profile(...)` is only on the happy path rather than a fail-safe failure path.

A process-level watchdog is the final owner, but it does not replace durable finite inner stage classifications. Repair-2 must add named finite waits, bounded task cancellation/observation, and fail-safe runtime shutdown while retaining the outer process-group watchdog as the last-resort owner.

## Remaining blocker D — no durable effect chronology for the one-shot probe

The probe recovery record is created once with `REAL_PROBE_RECOVERY_ARMED` but is not advanced through runtime/model/thread/turn/approval stages.

A future one-shot failure would therefore repeat the P7.C6 problem: effects could have occurred without a durable local record of dispatch intent and finite result.

Repair-2 must use a root-only fail-closed recovery journal. Before each future real effect, persist intent; after completion, persist finite result. At minimum cover runtime acquisition, model/list, thread/start, turn/start, each DENY response dispatch, terminal observation, runtime shutdown, boundary proof and child-result materialization.

No raw command/thread/Turn/sentinel content may be published to Git.

## Remaining blocker E — DENY response accounting is not truthful under ambiguity

The real `counted_response(...)` calls `original_response(...)` before incrementing the budget. If the transport response is dispatched but returns `ProtocolApprovalResponseUnknown`, the wire effect can be ambiguous while the current budget remains unchanged.

In addition, `DenyOnlyApprovalOperator.response_count` is not updated by the real protocol wrapper, yet the child sanitized result derives `deny_response_count` from that operator field.

Repair-2 must reserve/count a DENY attempt before wire dispatch, durably record the intent, and then record finite success/unknown after the production response boundary returns. The sanitized result must use one authoritative counter source and enforce consistency between request count, response-attempt count and successful/unknown DENY results. ALLOW remains exactly zero.

## Remaining blocker F — child result currently invents process-group success

`make_sanitized_result(...)` defaults `process_members=()` and `process_scan_errors=0`. The future real coroutine calls it without a real process-group observation and then writes the global result itself.

Therefore the result can claim zero active group members without parent measurement. This is not acceptable.

Repair-2 must separate child-local sanitized result from parent-final result. The dedicated parent must measure process-group quiescence after child exit and only then create the final global sanitized authority. No default-zero process-group fields may be accepted as evidence.

## Remaining blocker G — /proc churn can false-fail group scans

Repair-1 collapses a vanished `/proc/<pid>/stat` and malformed/unreadable stat into one `None` result, then increments `scan_errors` for every `None`. A process that exits after the finite `/proc` PID snapshot is normal host churn and must not itself be a scan error.

Repair-2 must distinguish benign `FileNotFoundError` after PID snapshot from malformed/permission/other read errors, while still failing closed for real scan errors.

## Remaining blocker H — real path does not actually use the prepared approval/terminal race

The offline helper correctly races approval observation with terminal observation, but the future real coroutine starts an approval drain and then directly awaits `turn_lifecycle.wait_turn(...)`. It does not use the finite race state machine and does not terminate at the frozen three-DENY limit.

Repair-2 must use one real-path race/owner implementation equivalent to the proven offline semantics. After three DENYs with no definitive terminal, classify the request limit and begin finite runtime containment; do not wait forever and do not emit a fourth response.

## Remaining blocker I — command-boundary proof occurs before guaranteed final runtime containment

The current real path scans the run boundary before successful runtime shutdown and does not supply actual command-owned process references. Repair-2 must perform final command-boundary proof after owned runtime shutdown/convergence in the child and then have the parent prove the entire dedicated process group is quiescent.

Normal sqlite/log descendants remain runtime-owned data and are not command mutation by themselves.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR1=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.

The next slice is Repair-2, harness/tests/evidence only and zero real effects.