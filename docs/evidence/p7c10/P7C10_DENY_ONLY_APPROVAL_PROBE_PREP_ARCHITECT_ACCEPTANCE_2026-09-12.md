# P7.C10 DENY-only approval-probe preparation — architect acceptance — 2026-09-12

Status: **ARCHITECT ACCEPTED / ZERO-REAL-EFFECT PREPARATION COMPLETE / REAL PROBE MAY BE SEPARATELY AUTHORIZED**

## Accepted executable authority

- Prep commit: `3732134246464df899837a3c499c86c52270b038`.
- Prep tree: `68be37c8a5d0aa132199f8b2782618638a07b87e`.
- P7.C10 harness blob: `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.
- Architect base: `a6a3a8f221ec62741833c7cbb59e41569c9620f8`, tree `5c473ba2c2a4102c1230824b955584de3a6b42e0`.
- Candidate is exactly one commit ahead of the base and changes only the P7.C10 harness and prep evidence. No `src/**` change occurred.
- Reported real effects during preparation: zero.

## Independent acceptance findings

P7.C10 closes the deterministic P7.C9 RecoveryJournal defect without weakening raw-data protections:

- RecoveryJournal writer and authoritative reader share field-aware schema validation rather than applying the generic payload substring filter to structural tokens;
- journal events are constrained by a finite exact harness-owned allowlist;
- `TURN_ID_AUTHORITY` is explicitly allowed only with result `ESTABLISHED`;
- `APPROVAL_OBSERVER_ARMED` is explicitly allowed only with result `YES`;
- raw `thread_id`, `turn_id`, sentinel path, wire-command plaintext, prompt/response, credentials/tokens and arbitrary extension keys have no journal route;
- source hashes, SHA-256 values, attempts/request counts, booleans, categories/classes/kinds and result tokens are field-specifically validated;
- the actual real path orders confirmed production turn start -> in-memory Turn authority -> durable `TURN_ID_AUTHORITY` -> durable `APPROVAL_OBSERVER_ARMED` -> approval/terminal observation;
- normal child authority re-reads and requires exact durable Turn chronology when an observation is eligible for a normal result;
- normal parent final authority independently re-reads the retained child journal and fails closed if Turn authority is missing, duplicate, conflicting, unsafe or out of order;
- immutable journal identity/no-recreate, production state-root provision/validate, state-root worker ownership, runtime acquisition/failed-acquire containment, DENY-only handling, exact normal `1/1/1`, zero resume/interrupt/delete/read/list, one-child/no-retry process ownership and boundary authority remain present.

## Time authority

Frozen future-real values remain:

- state-root provision+validate ceiling: 5s;
- state-root worker join: 1s;
- runtime acquire: 45s;
- failed-acquire cleanup: 12s;
- cleanup cancel/join: 1s;
- approval/terminal observation: 100s;
- normal path internal worst case: 192s;
- failed provision path: 12s;
- failed acquire path: 70s;
- watchdog margin: 15s;
- parent hard watchdog: 207.001s.

## Test authority

Reported and evidence-recorded:

- explicit P7.C10 tests: 137, skipped 1, failures 0, errors 0;
- focused tests: 293, failures 0, errors 0;
- full tests: 1065, failures 0, errors 0;
- production source changed: NO;
- real P7.C10 thread created: NO.

## Disposition

`P7C10_DENY_ONLY_APPROVAL_PROBE_PREP=ARCHITECT_ACCEPTED`

`P7C10_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C10_REAL_APPROVAL_PROBE_PREPARATION=COMPLETE`

This preparation itself authorizes no real effect. A separate exact-snapshot one-shot execution contract is required before real P7.C10 execution.

P7.C7, P7.C8 and P7.C9 remain permanently consumed. P8/P9 remain blocked.
