# P2.2 core repository implementation evidence

Status: implementation evidence only; this document does not claim architect acceptance.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Issue: #12
- Branch: `impl-p2-2-core-state-repositories-2026-09-05`
- Base SHA: `b1d3b15f098dab4da1f60b168d2b324abeaa193e`
- Binding ADR: `docs/adr/0019-core-state-repositories.md`
- Accepted P2.1 HEAD: `61301fd25ff7253693f367664ce99e13dfc88446`

## Production implementation

Added:

- `src/codex_control/storage/repository_errors.py`
- `src/codex_control/storage/records.py`
- `src/codex_control/storage/core_repositories.py`

Changed:

- `src/codex_control/storage/__init__.py` to export the approved P2.2 public types.

The implementation uses only `SqliteStorage.read` and `SqliteStorage.write`. It does not
modify the accepted P2.1 kernel, schema, DDL, migration identity, indexes, transaction
policy, callback authorizer, file security, or flock behavior.

## Public contracts

`RepositoryErrorCategory` contains exactly `invalid_argument`, `not_found`,
`already_exists`, `version_conflict`, `state_conflict`, `clock_invalid`, and
`invariant_violation`. `RepositoryError` renders only its finite category and has no
retry policy, SQL, path, input, or exception-body fields.

Immutable records/results are `ControllerRuntimeRecord`, `ControllerBootResult`,
`SettingsRecord`, `SettingsInitializeResult`, and `DialogueRecord`. `DialogueState`
contains exactly the ten schema-v1 dialogue states. `DialogueRecord` does not expose
`live_slot`.

Input strings are validated before SQL against ADR-0018 bounds. Persisted rows are
validated inside storage callbacks, including exact integer/timestamp bounds, enum
values, nullability, lengths, timestamp ordering, canonical live slot, and sanitized
dialogue error classes.

## Clock and versions

Repositories accept an injected millisecond clock. Invalid/raising clocks become
`CLOCK_INVALID` without source text; process-control `BaseException` is not caught.
Failed semantic claims and reads do not call the clock. Mutating timestamps use
`max(clock_now, existing.updated_at_ms)`. Successful versioned mutations increment
exactly once, and signed 64-bit overflow fails as `INVARIANT_VIOLATION` without wrap.

## Controller runtime

`get()` reads the optional singleton. `begin_boot(fleet_version)` creates the first row
with epoch 0, historical requested mode `SLEEP`, generation 1, and equal creation/update
timestamps. Repeated boots preserve epoch, historical requested mode, and creation time;
replace fleet version, increment generation, and update monotonically. Every successful
boot result has effective mode `SLEEP`. No control-epoch or mode mutation API exists.

The historical ACTIVE proof seeds a valid row with epoch 55 and generation 7, then
observes generation 8, preserved ACTIVE/55, the new fleet version, and effective SLEEP.

## Settings

`initialize_if_absent` inserts version 0 only when absent. An existing durable row is
returned unchanged, wins over later fallback values, and does not call the mutation
clock. `replace` requires an existing singleton, checks the expected version, performs a
whole-record replacement with an SQL version predicate, and increments the version even
when values are unchanged. Concurrent calls with one expected version produce one winner,
one `VERSION_CONFLICT`, and final version N+1.

## Dialogue create intent

`get_live` materializes the sole retained row or returns `None`. `create_intent` claims
the empty live slot atomically as `CREATING`, version 0, with no thread/error. Any
retained row, including an identical replay, returns `ALREADY_EXISTS` without a clock
call. Concurrent claims produce one durable row and one winner.

Only the three create-terminal claims are exposed:

- `confirm_created`: `CREATING` with no thread -> `IDLE`, one exact thread binding;
- `mark_create_unknown`: `CREATING` with no thread -> `CREATE_UNKNOWN`;
- `mark_create_error`: `CREATING` with no thread -> `ERROR`.

All increment version once, preserve server/profile/dialogue identity and creation time,
and use monotonic update timestamps. Terminal claims are mutually exclusive; thread,
server, and profile identities have no P2.2 setters. No turn/delete states are written,
and no dialogue delete method exists.

Missing row, stale version, and wrong create precondition are ordered as
`NOT_FOUND`, `VERSION_CONFLICT`, and `STATE_CONFLICT`. Failed preconditions do not call
the clock.

## Restart, errors, and redaction

Temporary-database tests close and reopen storage, then reconstruct fresh repositories
and verify identities, states, versions, and timestamps from durable rows. No
authoritative repository cache exists. Corrupt but schema-valid noncanonical persisted
values fail as `INVARIANT_VIOLATION` without raw values. A closed storage propagates
`StorageError(CLOSED)` unchanged rather than converting it to a repository error.

Repository and record representations contain no database path, SQLite handle, callback
internals, prompt/response content, credentials, environment, or raw exception text.

## Tests and checks

- P2.2 unit: 4 (`tests.unit.test_core_repository_records`)
- P2.2 integration: 13 (`tests.integration.test_core_state_repositories`)
- P2.1 schema/unit: 8
- P2.1 storage integration: 31
- P1.10 T0/T1/T2: 6 / 1 / 4
- P1 focused suites: all passed (28, 27, 22, 18, 18, 22, 17, 22, 28, 15, 16)
- Base accepted full suite: 287
- Expected full suite: `287 + 4 + 13 = 304`
- Observed full discovery: 304 passed
- Compile/import: passed (`compileall`, required P2.2 import marker)
- `git diff --check`: passed
- P2.1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- P1.6 pending-task warning: observed; unchanged and not introduced by P2.2

Security review searched changed files for secrets, credentials, production state paths,
raw content, stdout/stderr, hidden reasoning, and unsanitized exception text. No such
material was added; only explicit fake redaction sentinels occur in temporary tests.

## Production effects

- Production DB opened: no
- Production state root touched: no
- Production services changed: no
- Runtime dependency added: no
- Architecture/ADR files changed: no
- P2.3 or later work started: no

## Architect first proof repair pass

Candidate entering this proof repair pass: `be2d2f527ad6160cd6ac1bfbbe10cdf79be1e8cf`.
This remains implementation evidence only and does not claim architect acceptance.

- Production P2.2 code changed: no. The repair changed only the P2.2 unit/integration tests and this evidence file.
- All-ten-state materialization: PASS. A table-driven integration proof inserts each exact ADR-0018 dialogue state through the low-level test seam and verifies enum state, identities, thread/error nullability or values, version, and timestamps through `get_live()`.
- Actual raising-clock mutation: PASS. Absent-row controller boot, settings initialization, and dialogue create intent each invoke a clock raising `RuntimeError("PRIVATE_REPOSITORY_CLOCK_MUST_NOT_LEAK")`; each returns `CLOCK_INVALID`, redacts the sentinel, calls once, leaves no row, and leaves storage usable.
- Invalid clock matrix: PASS. `True`, `False`, `"123"`, `1.5`, `-1`, and `9223372036854775808` are rejected as `CLOCK_INVALID` with no controller row; `0` and `9223372036854775807` are accepted at valid timestamp boundaries.
- Exact API-surface proof: PASS. Committed unit inspection of class-defined public callables binds controller to `get`/`begin_boot`, settings to `get`/`initialize_if_absent`/`replace`, and dialogue to `get_live`/the four create-intent methods; no control mutation, generic transition, or delete method is present.
- Settings version overflow: PASS. A low-level version-maximum seed makes `replace` return `INVARIANT_VIOLATION` before the injected failing clock; the complete record remains unchanged.
- Dialogue version overflow: PASS. A valid CREATING/null-thread row at version maximum makes a terminal create claim return `INVARIANT_VIOLATION` before the clock; the complete record remains unchanged.
- Exact input boundary matrix: PASS. Required ID/fleet bounds prove 128 accepted and 129/empty/NUL rejected; model 256/257, effort 64/65, thread 512/513, and sanitized error-class length/character boundaries are covered. Expected version proves 0 accepted, maximum semantically reaches overflow handling, and bool/negative/overflow/float values return `INVALID_ARGUMENT` before mutation.
- Controller corruption proof: PASS. Schema-valid `boot_generation=1.5` fails materialization as `INVARIANT_VIOLATION` without the raw value in the error.
- Dialogue corruption proof: PASS. Schema-valid raw-prose `last_error_class` and numeric `version=1.5` each fail `get_live()` as `INVARIANT_VIOLATION` without raw values in the error.
- Exact restart-record equality: PASS. A newly instantiated repository after close/reopen returns the exact captured controller, settings, and confirmed dialogue records, including all dialogue identity/state/version/timestamp/error fields.
- Repository error/repr proof: PASS. Every finite repository category has exact content-free `str`/`repr`; unknown constructor text maps to `INVALID_ARGUMENT`; retry fields are absent; repository reprs redact the temporary DB path/sentinel.
- Final focused counts: P2.2 unit `6`; P2.2 integration `20`.
- Final full count: `313`, matching `287 + 6 + 20`.
- P2.1 regressions: schema/unit `8`; storage/integration `31`; DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P1.10 counts: T0 `6`; T1 `1`; T2 `4`. All required P1 regression suites passed.
- Compile/import and `git diff --check`: passed. The known P1.6 pending-task warning was observed and remains unchanged; it was not introduced by this repair.
