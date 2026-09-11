# P7.C7 DENY-only approval-probe prep — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT / REAL PROBE NOT AUTHORIZED**

## Reviewed authority

- Architect base: `7e0654bbc9e2798ea49e16eca3aa6e2d90d1592a`, tree `e3281cc5dd5a0a06e92e5f87feb340a679cffcf2`.
- Candidate: `e4bcdf43ba3f5c50a65f7f1085781eec41770ede`.
- Candidate is exactly one commit ahead of base.
- Changed files are limited to the P7.C7 test harness and preparation evidence; no `src/**` change occurred.
- Executor reports zero real effects, 29 explicit probe-file tests with one expected real-gate skip, 88 focused tests, and 1065 ordinary tests with zero failures/errors.

## What is accepted from the candidate

The candidate establishes useful preparation primitives:

- `DenyOnlyApprovalOperator.decide()` has one decision path and returns `DENY`; no `ALLOW` value exists in the operator body.
- production `CodexApprovalBridge` / `ApprovalRequest` projection is used by offline fixtures;
- approval and terminal observation are started concurrently rather than reproducing the P7.C6 approval-first serial wait;
- the fresh semantic stimulus remains bounded to sleep-30 plus one run-owned outside-workdir sentinel touch;
- raw wire authority is root-only/exclusive/no-follow in synthetic tests;
- future P7.C6 paths are not reused;
- the real method remains disabled and intentionally inert.

These are preserved in Repair-1.

## Blocking defects

### A. Raw wire authority can be poisoned by an identity-mismatched request

`DenyOnlyApprovalOperator.decide()` persists the first finite command whenever the turn future is resolved and the wire file is absent. It does **not** require exact thread, turn, cwd, request kind, or exact command-context cardinality before creating the raw wire authority.

A wrong-thread/wrong-turn/wrong-cwd request can therefore become the exclusive first-capture record and block the later exact probe request. This is fail-closed for execution because the response is still DENY, but it is not fail-closed for the evidence purpose of the probe.

The record also writes the expected `self.cwd` hash rather than proving/storing the actual normalized request cwd as the authority input.

Required repair: all requests remain DENY, but authoritative raw-wire capture may occur only for one exact-identity `COMMAND_EXECUTION` request with exactly one normalized command line and exact thread/turn/cwd. Mismatch evidence may be counted separately but must never occupy the authoritative wire file.

### B. Sentinel identity is a substring test and can false-pass

`sentinel_match = self.sentinel in command` is not an identity proof. A command can contain the expected path as a substring while targeting a different path or embedding it in unrelated script text.

The probe does not yet know the future grammar, so it must not claim semantic sentinel match from substring containment. Use a finite observational classification such as exact recovered argv token / embedded occurrence / absent / reconstruction-not-established, and keep matcher authority for later architect review.

### C. Same-tick approval/terminal race is not deterministically classified

The frozen preparation required a deterministic finite classification for simultaneous approval/terminal completion. The synthetic test currently accepts either `APPROVAL_AND_TERMINAL_RACE_AMBIGUOUS` or `TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`.

The observer also classifies from scheduler completion ordering without making `ApprovalHandlingStatus.RESPONSE_UNKNOWN` an explicit authoritative ambiguity signal.

Required repair: define deterministic precedence from observed facts. A successfully dispatched DENY proves approval-observed; `RESPONSE_UNKNOWN` with terminal concurrence is ambiguous; a definitive terminal with no observed/dequeued request is terminal-first. Synthetic same-tick input must have one expected class.

### D. Future effect budget does not count DENY responses

`FutureProbeBudget` freezes zero ALLOW capacity but has no `approval_deny_responses` counter. The probe explicitly permits up to three real DENY responses; these are real protocol effects and must be budgeted exactly.

Required repair: add bounded DENY-response accounting (`0..3`), total approval-response accounting, and prove `ALLOW=0` while every response increments the correct effect counter.

### E. Process-group watchdog has false accounting / incomplete process observation

The synthetic watchdog is weaker than the accepted P7.C6 process-group authority:

- `/proc` read/parse failures are silently dropped and `scan_errors` never increments;
- zombies are not distinguished from active members;
- `term_count` / `kill_count` are clamped with `min(..., 1)` while additional `os.killpg` calls can still occur;
- the `finally` path can issue an unaccounted `SIGKILL`;
- exact parent-PGID exclusion / `pgid > 1` is not frozen in the signal helper.

Required repair: reuse the accepted exact-group model: child PID=PGID=SID, PGID != parent PGID, PGID > 1, finite active-vs-zombie scan with scan errors, one signal helper that forbids a second TERM/KILL dispatch, and zero unaccounted signal paths.

### F. Fresh-run mutation scanner would false-fail normal real runtime state and under-validates the sentinel

`scan_fresh_run_boundary()` recursively treats any file below the isolated sqlite/log directories as unexpected, but a real app-server is expected to populate those run-owned runtime directories. The future real probe would therefore classify normal isolated runtime payloads as unexpected mutation.

At the same time, an allowed sentinel is accepted merely because it is a regular file; its expected `touch` semantics (stable identity, root ownership, single link, safe mode, zero length) are not proved.

Required repair: separate runtime-owned isolated-state authority from probe-command mutation authority. Validate isolated roots safely without counting normal runtime payload as command mutation; separately prove workdir/root unexpected mutations and exact sentinel touch semantics.

### G. Root-only wire record lacks an exact schema/hash-consistency validator

The bounded reader validates file authority and JSON shape only at the top level. A later sanitized result reads `wire_command_plaintext` and reparses it without first validating the exact wire-record key set and internal hashes/identity fields.

Required repair: exact wire-authority schema validator, internal plaintext/hash consistency, finite hash grammar, exact request kind/sequence grammar and identity-hash fields before any value is projected into sanitized evidence.

### H. Future real path is not materialized

The gated real unittest still intentionally executes `self.fail("P7C7_REAL_PROBE_CONTRACT_NOT_FROZEN")`. This is acceptable for the initial prep candidate but means the next architect-accepted snapshot still cannot be directly authorized for a one-shot probe.

Repair-1 must materialize the complete future real probe path under the disabled gate, using production runtime/model/thread/turn/approval adapters, fresh isolated state, exact source/tree authority, one fresh thread, one primary turn, concurrent approval/terminal observation, zero delete/read/list/resume/interrupt, DENY-only responses, safe result authority and whole-process-group watchdog. It must remain unexecuted during Repair-1.

## Classification

`P7C7_DENY_ONLY_PROBE_PREPARATION=REWORK_REQUIRED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
