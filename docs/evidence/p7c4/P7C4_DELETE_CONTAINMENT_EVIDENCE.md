# P7.C4 Delete Containment Evidence

## Lineage

- Architect base commit: `7572df1e95e79f3292489b096e8b0a22789df1e5`
- Architect base tree: `2584147b1bd8190cccee9907876abe9034f66005`
- Branch: `impl-p7-c4-delete-containment-2026-09-10`
- Scope: application/storage proof only. No real Codex acceptance experiment was run.

## Schema v4

Schema version is 4. Migration ID is `0004_delete_local_containment`.
The migration contains exactly one DDL statement, creates no v4 index, and
its independently recomputed canonical SHA-256 is
`400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
The table is FK-linked to the live dialogue with `ON DELETE CASCADE` and
contains only bounded, content-free UNKNOWN containment metadata.

Historical v1, v2, and v3 statement constants, canonical SQL, and hashes are
unchanged. Historical validators retain their historical object sets; v4 has
separate table/index authorities. Migration paths are v0/v1/v2/v3 through v4,
with v4 reopen validation and no migration-clock call. v4 rollback leaves the
valid v3 ledger/object set and permits a later retry.

## UNKNOWN containment

`DeleteStorageContainmentRecord` is immutable and content-safe. It stores the
dialogue/profile identity, SHA-256 of the exact retained thread identity,
dialogue version, the fixed official value `UNKNOWN`, the fixed local value
`COMPLETED`, and a bounded timestamp. It never stores raw thread identity,
prompt, response, path, credentials, or environment data.

`DeleteStorageContainmentRepository.mark_unknown_contained` transactionally
requires the exact live dialogue/version, canonical `DELETE_UNKNOWN` state,
the exact UNKNOWN error class, a retained binding, no active turn job, no
tombstone, and no conflicting row. It inserts without changing dialogue
version/state/binding/jobs. Exact duplicates return the immutable existing row
without changing its timestamp. Mismatched, orphaned, forged, tombstoned, or
non-UNKNOWN attachments fail closed. `finalize_confirmed` rejects any
containment collision as an invariant violation.

## Local cleanup order and quarantine

For confirmed pending storage, the coordinator executes:

`reserve -> shutdown -> quiescence proof -> recreate isolated root -> persistent residual scan -> finalize -> release`

The reservation remains held through scan and the committed finalizer result;
it is released only after finalization is validated. Any pre-finalizer failure
returns a finite pending result, preserves the live pending dialogue and
binding, creates no tombstone, and retains the reservation.

For UNKNOWN, the order is:

`validate UNKNOWN -> reserve -> shutdown -> quiescence proof -> recreate isolated root -> durable containment insert`

The reservation remains held on both success and failure. A same-process
replay with a valid held quarantine and exact durable row is idempotent. A
fresh coordinator re-acquires quarantine and recreates/revalidates the root;
the durable row remains unchanged. UNKNOWN is never promoted to DELETED and
never reaches the confirmed finalizer.

## Persistent profile residual gate

The descriptor-relative, no-follow scanner uses the accepted C3
`IsolationPathAuthority` and scans exactly `sessions/**` plus optional
`history.jsonl`. It checks relative entry names and regular-file bytes for the
exact UTF-8 thread identity, including chunk-boundary matches. It rejects
symlinks, special files, foreign ownership, group/world writable scanned
entries, I/O errors, file-count overflow, and byte-count overflow.

Scanner results and diagnostics contain only aggregate counters and finite
flags. Synthetic tests place a credential sentinel in `auth.json` and a
configuration sentinel outside the scan scope; the scanner does not open or
read either. No persistent profile file is mutated.

## Delete/recovery composition

The optional local-cleanup port preserves the predecessor behavior when
absent. With the port, confirmed upstream success is durably persisted as
`DELETE_CONFIRMED_PENDING_STORAGE` before local cleanup; clean local storage
returns `DELETED` with the accepted tombstone, while residuals or local
failures remain pending. Ambiguous/non-success is durably persisted as
`DELETE_UNKNOWN` before optional containment and always returns UNKNOWN.

Startup recovery performs no external delete call: stranded DELETING first
becomes UNKNOWN, confirmed-pending resumes local cleanup/finalization, and
UNKNOWN re-establishes quarantine/containment. Private management retains its
existing truthful projections and emits no second destructive action for
pending or UNKNOWN states.

## Crash/restart and concurrency evidence

SQLite migration and repository writes are transactional. Synthetic coverage
exercises v4 rollback/retry, clean confirmed finalization, persistent residual
blocking, UNKNOWN containment, same-process idempotent replay, ambiguous
delete composition, and confirmed-pending recovery. Every failure path before
finalization preserves pending state and quarantine; every UNKNOWN path
preserves UNKNOWN state, binding, and absence of tombstone/finalizer effect.
Owned coordinator tasks are cancellation-safe and coalesce concurrent calls
per dialogue, preventing duplicate root recreation, containment insertion,
finalization, or release.

## Non-regression and effect accounting

P7.C2 exact upstream confirmation remains the only confirmed authority and is
persisted before local cleanup. P7.C2 post-confirm database failure remains
finite and non-retrying; DELETE_UNKNOWN remains terminal/non-retrying. P7.C3
profile isolation, child routing, generation gates, descriptor path authority,
reservation races, and root substitution defenses remain covered by the
predecessor suites.

No real Codex process, app server, business RPC, model call, thread call,
Telegram call, production process mutation, real profile-home mutation, or
real isolated-root mutation was performed. Synthetic temporary filesystem
mutation was limited to test fixtures. Credential content was neither read,
copied, nor symlinked.

## Tests

- Focused affected suites: 214 tests, 0 skipped, 0 failures, 0 errors.
- Full command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Full result: 1,029 tests, 0 skipped, 0 failures, 0 errors.
- `PYTHONPATH=src python3 -m compileall -q src tests`: passed.
- `git diff --check`: passed.

## Changed files

Production:

- `src/codex_control/adapters/codex/__init__.py`
- `src/codex_control/adapters/codex/persistent_scanner.py`
- `src/codex_control/adapters/codex/runtime.py`
- `src/codex_control/application/__init__.py`
- `src/codex_control/application/delete_storage_cleanup.py`
- `src/codex_control/application/dialogue_delete.py`
- `src/codex_control/application/dialogue_recovery.py`
- `src/codex_control/storage/__init__.py`
- `src/codex_control/storage/application_recovery.py`
- `src/codex_control/storage/containment_records.py`
- `src/codex_control/storage/containment_repositories.py`
- `src/codex_control/storage/deletion_repositories.py`
- `src/codex_control/storage/schema.py`
- `src/codex_control/storage/sqlite.py`

Tests:

- `tests/unit/test_p7_c4_delete_containment.py`
- v4 expectation/authority updates in the existing schema and P7.C2 tests:
  `tests/acceptance/test_p2_6b_contract_snapshot.py`,
  `tests/acceptance/test_p2_c2_rejected_ingress_schema_v2.py`,
  `tests/integration/test_p7_c2_schema_v3_storage_barrier.py`,
  `tests/integration/test_rejected_ingress_schema_v2.py`,
  `tests/integration/test_sqlite_storage_kernel.py`,
  `tests/unit/test_rejected_ingress_schema_v2.py`, and
  `tests/unit/test_sqlite_schema_v1.py`.

This evidence file is the only P7.C4 evidence artifact. No architect
authority document, predecessor acceptance artifact, P7.C5/P7.C6 artifact, or
real-P7 artifact was edited or created.

## First architect repair

INITIAL_CANDIDATE=
70cdf0edc3f319c0254313eabc5d3c56c2f9ef16

INITIAL_ARCHITECT_VERDICT=
REWORK_REQUIRED

ARCHITECT_DEFECT_A=
RECOVERY_OUTCOMES_COLLAPSED_BY_ENUM_ALIASES

ARCHITECT_DEFECT_B=
COMMITTED_FINALIZER_COULD_BE_REPORTED_PENDING_AND_LEAK_RESERVATION

ARCHITECT_DEFECT_C=
V4_SCHEMA_OPEN_DID_NOT_REJECT_CONTAINMENT_TOMBSTONE_OR_ACTIVE_JOB_COLLISION

ARCHITECT_DEFECT_D=
SCANNER_DID_NOT_REVALIDATE_OPENED_REGULAR_FILE_IDENTITY_BEFORE_CONTENT_READ

ARCHITECT_DEFECT_E=
MANDATORY_CRASH_RESTART_CONCURRENCY_MATRIX_NOT_ACTUALLY_PROVED

The first repair makes all three C4 recovery outcomes distinct, validates the
exact committed `DeletionFinalizeResult` and its tombstone/count authority,
removes the post-commit downgrade read, preserves a truthful finalized result
when reservation release fails, and accepts only exact local tombstone replay
identity. V4 open validation rejects containment/tombstone and
containment/active-job collisions while retaining the unchanged v4 DDL and
hash. The scanner now validates pre-open metadata, post-open metadata, and
descriptor identity before reading any regular file.

Repair regression coverage includes:

- distinct finalized, UNKNOWN-contained, and UNKNOWN-pending recovery status
  values and the complete local cleanup result matrix;
- committed-finalizer post-verification failure, reservation-release failure,
  exact concurrent tombstone replay, stale-generation rejection, and
  mismatched-thread-hash rejection;
- direct forged v4 reopen rejection and forged application-recovery invariant
  rejection;
- deterministic regular-file substitution, history symlink/ownership/mode,
  scanner I/O fail-closed, path/chunk matching, and credential/configuration
  non-read checks;
- confirmed and UNKNOWN concurrent async ownership, caller cancellation,
  containment quarantine retention, and no duplicate root/finalizer/insert;
- startup/delete recovery replay with no external thread-delete effect.

The repair focused suite passed with 22 tests, 0 skipped, 0 failures, and
0 errors. The required compile, diff, compatibility, and full regression
results are recorded below after execution.
