# CODEXCONTROL P7.C5 CORRECTED FAKE HARD-DELETE ACCEPTANCE REPORT

Status: `FAKE_ACCEPTANCE_PASS_PENDING_ARCHITECT_REVIEW`

## Authority and historical correction

- Architect base SHA: `44dcb874659940998734fdfe76fb8683250be05d`
- Architect base tree: `471bae46bf36592a7502298b863d8774f04cb013`
- Accepted P7.C4 SHA: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`
- Accepted P7.C4 tree: `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`
- Branch: `impl-p7-c5-fake-hard-delete-acceptance-v2-2026-09-10`
- Proof commit: recorded in the final handoff after the evidence-only commit.

Historical stop preserved as evidence only:

- `HISTORICAL_STOP_BRANCH=impl-p7-c5-fake-hard-delete-acceptance-2026-09-10`
- `HISTORICAL_STOP_COMMIT=581a31e9a450230eed50bad6c247159898d72f7f`
- `HISTORICAL_STOP_CLASSIFICATION=ARCHITECT_CONTRACT_DEFECT_NOT_PRODUCTION_DEFECT`

The corrected suite does not merge, amend, rebase, reset, cherry-pick or
continue the historical stopped branch. It does not copy its incorrect
marker-only production assertion.

## Production gate versus test-only oracle

`PRODUCTION_EXACT_THREAD_GATE=PASS`.

The accepted production scanner remains exact-thread-only and scans only
`CODEX_HOME/sessions/**` and `CODEX_HOME/history.jsonl`. It checks relative
names and bytes for the exact retained thread identity and fails closed on
scan/path/ownership/symlink/special-file/hard-link/read/limit failures.

`PRODUCTION_MARKER_NEEDLE_ADDED=NO`.

`TEST_ONLY_MARKER_ORACLE=PASS`. The oracle exists only in
`tests/acceptance/test_p7_c5_fake_hard_delete_acceptance.py`; it searches the
synthetic fixture families `persistent_sessions`, `persistent_history`,
`isolated_sqlite`, and `isolated_logs`. It reports only a marker digest,
aggregate counts and safe family labels. It is not imported by production.

The marker-only fixture contained a positive marker-only residual count while
the production exact-thread scan returned zero matches and zero scan errors.
The fake acceptance verdict was therefore:

`MARKER_ONLY_DIRTY_FIXTURE_VERDICT=REJECTED_BY_ACCEPTANCE_ORACLE`

`MARKER_ONLY_RESIDUAL_COUNT_DETECTED=>0`

This is a harness negative-test pass. Production did not infer target
ownership from an unknown marker.

## Acceptance matrix

Confirmed fake success used a fake P1 delete seam that removed target-owned
persistent fixture material before returning `DELETE_CONFIRMED`; local C4
cleanup did not remove persistent material manually. The complete local path
passed through durable confirmed-pending storage, exact reservation,
shutdown/quiescence, isolated reset, exact-thread scan, finalizer and release.
The oracle observed zero marker and exact-thread residuals, zero descendants
under both isolated payload families, a preserved ownership envelope, no live
dialogue, and one exact tombstone.

Separate production-attributed residual cases all remained
`DELETE_CONFIRMED_PENDING_STORAGE`, retained the exact binding, preserved the
persistent file, held quarantine, made no tombstone and called no finalizer:

- sessions file bytes: PASS
- sessions relative filename: PASS
- sessions relative directory: PASS
- history bytes: PASS
- sessions exact thread plus auxiliary marker: PASS
- history exact thread plus auxiliary marker: PASS

`DELETE_UNKNOWN` retained official UNKNOWN, state, version, binding and
`last_error_class=DELETE_UNKNOWN`; isolated containment completed, persistent
UNKNOWN material was unchanged, the v4 containment fact was recorded, no
tombstone/finalizer occurred, and quarantine remained held. PASS.

The isolated matrix included state main/WAL/SHM, SQLite log main/WAL/SHM,
cache/temp/other and nested files under both `sqlite/` and `logs/`. Successful
reset left the ownership marker and top-level directories in place with zero
payload descendants. PASS.

Scanner coverage passed for symlinks, special files, foreign ownership,
group/world writable entries, hard links, post-stat inode substitution,
file-count overflow, byte-count overflow, read failure and chunk-boundary
matching. Credential/configuration paths were outside production scan scope
and were not opened by the scanner. PASS.

The predecessor C3/C4 matrices passed for same-ID forged roots, foreign and
stale reservations, ancestor/root-leaf/post-anchor substitutions, protected
repository/controller aliases, unsafe permissions, scanner hard links and
sessions/history symlinks. Outside-target mutation was zero. PASS.

Deterministic local crash/restart coverage passed for reservation/shutdown/
recreate/scan/finalizer/release boundaries, both sqlite and logs descendant
clears, committed-finalizer truth, confirmed-pending restart retry and UNKNOWN
containment restart/quarantine. C4 predecessor coverage additionally passed
commit-then-exception, malformed finalizer return and post-commit release
failure truth. No external replay occurred.

Deterministic duplicate/concurrency/cancellation coverage passed: confirmed
cleanup coalesced to one reset, one finalizer and one release; UNKNOWN
containment coalesced to one reset and one containment insert; caller
cancellation could not abandon owned cleanup or release quarantine.

## Baselines and schema

Unrelated isolated sibling, isolated parent entry, repository sentinel,
controller SQLite database, persistent files outside accepted scan scope,
auth/configuration sentinels, and unrelated session/history material were
byte-for-byte preserved. PASS.

- `SCHEMA_VERSION=4`
- `SCHEMA_V1_HASH_UNCHANGED=PASS`
- `SCHEMA_V2_HASH_UNCHANGED=PASS`
- `SCHEMA_V3_HASH_UNCHANGED=PASS`
- `SCHEMA_V4_HASH=400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`
- `P7C2_NON_REGRESSION=PASS`
- `P7C3_NON_REGRESSION=PASS`
- `P7C4_NON_REGRESSION=PASS`

`MOUNT_NAMESPACE_DYNAMIC_TEST=NOT_RUN__SAFETY_BOUNDARY`. No privileged host
mount, namespace or production/global mount mutation was attempted. This
bounded risk remains explicitly carried to P7.C6/P13.

## Test and effect accounting

Dedicated corrected acceptance:

- `FOCUSED_TESTS=14`
- `FOCUSED_SKIPPED=0`
- `FOCUSED_FAILURES=0`
- `FOCUSED_ERRORS=0`

Required affected predecessor/compatibility command:

- `FOCUSED_TESTS=303`
- `FOCUSED_SKIPPED=0`
- `FOCUSED_FAILURES=0`
- `FOCUSED_ERRORS=0`

Exactly one ordinary full regression:

- command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- `FULL_TESTS=1064`
- `FULL_SKIPPED=0`
- `FULL_FAILURES=0`
- `FULL_ERRORS=0`

`PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
`git diff --check`: PASS.

All fake counters were process-local synthetic test counters. No real Codex
process, app server, model, thread, turn, delete, read, list, interrupt or
approval RPC was run; no Telegram call occurred; no credential content was
read/copied/symlinked; and no production process or real Codex home,
isolated-root or controller storage was mutated.

- `REAL_CODEX_VERSION_PROCESS_CALLS=0`
- `REAL_CODEX_APP_SERVER_STARTS=0`
- `REAL_CODEX_BUSINESS_RPC=0`
- `REAL_THREAD_DELETE_CALLS=0`
- `REAL_THREAD_READ_CALLS=0`
- `REAL_THREAD_LIST_CALLS=0`
- `TELEGRAM_CALLS=0`
- `REAL_CODEX_HOME_MUTATION=0`
- `REAL_ISOLATED_STATE_ROOT_MUTATION=0`
- `REAL_CONTROLLER_STORAGE_MUTATION=0`
- `CREDENTIAL_CONTENT_READ=0`
- `CREDENTIAL_COPY=0`
- `CREDENTIAL_SYMLINK=0`
- `PRODUCTION_PROCESS_MUTATION=0`

The only changed files are:

- `tests/acceptance/test_p7_c5_fake_hard_delete_acceptance.py`
- `docs/evidence/p7c5/P7C5_FAKE_HARD_DELETE_ACCEPTANCE_EVIDENCE.md`

No `src/**`, configuration, ADR, roadmap, current-work, decision or original
contract/correction file changed.

`P7C6_STARTED=NO`, `P8_STARTED=NO`, `P9_STARTED=NO`.

Remote readback is recorded after the final non-force push:

`REMOTE_READBACK=PASS`

`PRODUCTION_SOURCE_CHANGED=NO`
