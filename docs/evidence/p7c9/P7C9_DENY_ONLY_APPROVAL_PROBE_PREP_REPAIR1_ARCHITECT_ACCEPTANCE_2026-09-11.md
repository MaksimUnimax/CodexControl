# P7.C9 DENY-only approval-probe preparation Repair-1 — architect acceptance — 2026-09-11

Status: **ARCHITECT ACCEPTED / ZERO-REAL-EFFECT PREPARATION COMPLETE / REAL PROBE MAY BE SEPARATELY AUTHORIZED**

## Accepted executable authority

- Repair-1 commit: `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`.
- Repair-1 tree: `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`.
- P7.C9 harness blob: `44271459c2b4523f97551ade93563aee96def1c3`.
- Repair-1 evidence blob: `58d505e7c6e4e49ad01376ce9ceb7626554d9a9f`.
- Architect base: `48fb5755d89722bfac4f18d6dcde9c29f7b3e459`, tree `14e736ccbdfc06879e875a9dc6469537b20b4dcc`.
- Candidate is exactly one commit ahead of the base and changes only the allowed P7.C9 harness and Repair-1 evidence file. No `src/**` change occurred.

## Independent acceptance findings

Repair-1 closes both blockers from the initial P7.C9 prep:

- runtime-acquire, runtime-cleanup, state-root-provision and state-root-validation categories are kept in distinct authority locals; `RUNTIME_ACQUIRE_NOT_ESTABLISHED` checks the exact runtime fields directly;
- each state-root operation has explicit owner authority: `TERMINALIZED`, `NONCONVERGENT`, or `NOT_STARTED`;
- the state-root worker has a separate bounded 1-second join after the 5-second provision/validate ceiling;
- a timed-out nonterminal provision worker blocks validation and runtime acquisition;
- a timed-out nonterminal validation worker blocks runtime acquisition;
- normal child result rejects any nonterminal state-root owner;
- parent state-root reconstruction requires exact provision/validate result and owner chronology and fails closed for missing, duplicate, conflicting, unsafe, or invalid owner authority;
- normal parent success requires both provision and validation `CONFIRMED` and both owners `TERMINALIZED`;
- the real parent persists the fail-closed reconstructed state-root facts, including owner facts, into the execution outcome;
- production `IsolatedStateRoot.provision(profile)` and immediate `validate(profile)` remain the sole future-real state-root creation/validation path;
- the P7.C8 runtime-acquire authority, DENY-only handling, immutable recovery journal, exact normal `1/1/1` lifecycle ledger, one child/no retry, exact process-group authority, zero resume/interrupt/delete/read/list and boundary gates remain present.

## Time authority

Frozen future-real values in the accepted snapshot:

- state-root provision+validate ceiling: 5s;
- state-root worker join: 1s;
- runtime acquire: 45s;
- failed-acquire cleanup: 12s;
- acquire-cleanup cancel/join: 1s;
- observation: 100s;
- normal-path internal budget: 192s;
- failed-provision path: 12s;
- failed-acquire path: 70s;
- watchdog margin: 15s;
- parent hard watchdog: 207.001s.

## Disposition

`P7C9_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1=ARCHITECT_ACCEPTED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C9_REAL_APPROVAL_PROBE_PREPARATION=COMPLETE`

The preparation itself authorizes no real effect. A separate exact-snapshot one-shot execution contract is required before real P7.C9 execution.

P7.C7 and P7.C8 remain permanently consumed. P8/P9 remain blocked.
