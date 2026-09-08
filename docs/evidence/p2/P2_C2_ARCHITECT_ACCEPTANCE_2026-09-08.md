# P2.C2 architect acceptance — 2026-09-08

Status: ACCEPTED

## Accepted implementation

- Architect base: `111936f38fdeff1547f6585a70415ab5d0c26b0c`
- Initial implementation: `cdc46ce17ab9c990280c7758ee0a40892ff46c40`
- First repair: `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`
- Branch: `impl-p2-c2-rejected-ingress-schema-v2-2026-09-07`
- Issue: #32
- Binding ADR: ADR-0036
- Architect rejection/review comment: `5577725383`

The accepted P2.C2 lineage is exactly two linear implementation commits above the architect base and zero commits behind it.

## Independent architect review

Independent GitHub review confirmed:

- implementation branch HEAD is exactly `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`;
- repair commit is exactly one commit above rejected candidate `cdc46ce17ab9c990280c7758ee0a40892ff46c40`;
- cumulative P2.C2 diff remains limited to storage schema/kernel/idempotency/retention/package exports, narrow historical expectation updates, focused tests and implementation evidence;
- P3/P4/P5.1 production remains unchanged;
- P5.2/P5.3/P6 were not started.

## Historical schema-v1 authority

Historical schema-v1 remains immutable:

- version: `1`
- migration ID: `0001_initial_state`
- DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

`SCHEMA_V1_STATEMENTS`, canonicalization and the historical DDL hash were not widened with `IGNORED_REJECTED`.

## Accepted schema-v2 authority

Current schema version is `2`.

Exact migration identity:

- migration ID: `0002_ingress_rejected_disposition`
- migration-statement SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

The migration remains the exact four-statement authority from ADR-0036 and changes only the `ingress_updates.disposition` CHECK to permit exact `IGNORED_REJECTED`.

Accepted open behavior:

- empty v0 bootstraps historical v1, validates v1, then migrates/validates v2;
- valid v1 is validated before migration, then migrated once to v2;
- valid v2 validates directly without migration-clock use;
- unsupported versions fail closed;
- failed v2 migration rolls back to valid v1 with no backup table or v2 ledger row.

## First-repair migration-integrity closure

The rejected candidate validated historical v1 schema/ledger but did not validate physical ingress rows before migration. This could legalize a corrupt historical `IGNORED_REJECTED` row under v2 or commit v2 before discovering a historical materializer-invalid JOB suffix.

The accepted repair adds a private read-only historical-v1 ingress migration-eligibility preflight before any v2 DDL or v2 clock. It checks the accepted historical materializer boundary for:

- nonnegative signed-64 `update_id`;
- nonnegative signed-64 received/completed timestamps;
- completed timestamp ordering;
- exact historical non-JOB dispositions `CONTROL`, `IGNORED_SLEEP`, `IGNORED_UNAUTHORIZED`;
- `JOB:` suffix nonempty, NUL-free and at most 128 characters.

Deterministic proofs confirmed:

- forged historical-v1 `IGNORED_REJECTED` -> `SCHEMA_INVALID`, zero v2 clock, user version remains 1, no backup table, no v2 ledger;
- historical-v1 JOB suffix length 129 -> same fail-before-migration result;
- historical-v1 noncanonical REAL timestamp -> same fail-before-migration result;
- exact JOB suffix length 128 migrates and materializes successfully;
- unsupported-version proof asserts exact `SCHEMA_UNSUPPORTED` outside `assertRaises`;
- historical repository materializer proofs are isolated so one corrupt row cannot mask another boundary proof.

## Rejected-ingress semantics

`IngressDispositionKind` now has exact order:

`CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | IGNORED_REJECTED | JOB`.

`IGNORED_REJECTED` is terminal, authorized, pre-JOB, content-free rejection metadata. It stores no prompt/reason prose and is not interchangeable with SLEEP, unauthorized, control or JOB authority.

`IngressUpdateRepository.claim_ignored` accepts it without changing public method surface. Duplicate semantics remain exact: an already-known update returns its original durable classification unchanged and clock-free, including existing JOB/CONTROL/SLEEP/UNAUTHORIZED/REJECTED records.

Metadata retention treats rejected ingress as the same bounded standalone non-content metadata class without changing retention intervals or other retention behavior.

## Test/evidence acceptance

Accepted focused counts:

- P2.C2 unit: 5
- P2.C2 integration: 13
- P2.C2 acceptance: 1

Accepted full arithmetic:

`777 + 5 + 13 + 1 = 796`

Executor evidence reports:

- observed full discovery: 796
- failures: 0
- errors: 0
- final unittest result: `OK`

Required prior regression groups remained green, including accepted P5.1 `7/8`, P4.3 `7/26/1`, P4.2 `5/29`, P4.1 `8/15`, all listed P3/P2/P1 suites.

No GitHub status checks or workflow runs were attached to the accepted repair SHA. Acceptance is based on independent GitHub topology/code/diff review plus executor green regression evidence.

## Security/effect boundary

P2.C2 uses only temporary synthetic SQLite in tests. It adds no Telegram/network/Codex/thread/turn/delete/approval-response/delivery or production-state effect and persists no prompt/reason content.

The known P1.6 pending-task warning remains pre-existing and was not introduced by P2.C2.

## Gate opened

P2.C2 is complete and accepted. P5.2 may now be architect-researched/frozen. P5.2 must consume `IGNORED_REJECTED` as the durable terminal replay guard for authorized prompt updates rejected before JOB/external effect.