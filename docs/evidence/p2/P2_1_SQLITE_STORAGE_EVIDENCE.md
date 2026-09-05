# P2.1 SQLite storage evidence

Date: 2026-09-05

This is factual implementation evidence for Issue #11. It is not architect acceptance.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Base SHA: `f9f71f161ba61508e8bd648ea835e63278377a03`
- Branch: `impl-p2-1-sqlite-storage-kernel-2026-09-05`
- Issue: #11
- Binding ADRs: ADR-0017 and ADR-0018
- Production dependency delta: none
- Python: `3.12.3`
- Python sqlite3 module: `2.6.0`
- SQLite runtime: `3.45.1`

## Runtime kernel

`codex_control.storage.SqliteStorage` accepts an absolute, NUL-free string path with an existing real parent directory. The parent is checked for symlink traversal, effective-UID ownership, directory type and group/other writability. Database and sibling `.lock` paths are opened with `O_NOFOLLOW` where available; new files are mode `0600`, and existing files must be regular, effective-UID-owned and exactly mode `0600`.

The lock is an exclusive non-blocking `flock` held for the storage lifetime. A second owner returns `LOCKED`; failed opens release the lock. One `ThreadPoolExecutor(max_workers=1)` owns one persistent `sqlite3.Connection`, created/configured/migrated/used/closed on that worker with default `check_same_thread=True`.

The verified connection contract is: `foreign_keys=1`, `journal_mode=wal`, `busy_timeout=5000`, `synchronous=FULL` (2), `trusted_schema=0`, `isolation_level=None`, and `sqlite3.Row` row factory. Reads use `PRAGMA query_only=ON`, `BEGIN DEFERRED`, callback, `COMMIT`, then restore query-only off. Writes use `BEGIN IMMEDIATE`, callback, `COMMIT`; failures roll back without retry. SQLite failures are normalized; arbitrary callback exceptions propagate exactly. Connection/cursor/row callback results are rejected.

Submitted executor work remains owned after public coroutine cancellation. Close admission is serialized behind already-submitted work, rejects new operations as `CLOSED`, closes the connection on the worker, releases the flock, shuts down the executor, and is idempotent/convergent across callers.

## Schema authority

- `SCHEMA_VERSION`: `1`
- Migration ID: `0001_initial_state`
- `SCHEMA_V1_DDL_SHA256`: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- User tables: `schema_migrations`, `controller_runtime`, `settings`, `dialogues`, `turn_jobs`, `transient_payloads`, `delivery_segments`, `ingress_updates`, `callback_actions`, `approvals`, `deletion_tombstones`, `errors`
- Explicit indexes: `idx_turn_jobs_dialogue_state`, `idx_transient_payloads_expires`, `idx_transient_payloads_dialogue`, `idx_transient_payloads_job`, `idx_delivery_segments_state`, `idx_delivery_segments_payload`, `idx_callback_actions_expiry`, `idx_approvals_job_state_expiry`, `idx_approvals_wire_request`, `idx_approvals_display_payload`, `idx_deletion_tombstones_expiry`, `idx_errors_last_seen`, `idx_errors_dialogue`, `idx_errors_job`

The ordered DDL constant contains all 26 ADR-0018 statements. Its canonical hash was independently recomputed from the ADR SQL block. Bootstrap accepts only empty `user_version=0`, runs one explicit migration transaction, inserts the exact history row, and sets `user_version=1` within that transaction. Reopen validates the migration row, hash, exact object sets, absence of views/triggers, and canonicalized `sqlite_master` SQL for every frozen table/index. It does not repair drift or seed rows.

The injected migration clock test records `1234567890`; reopen with a clock that raises passes without calling it. Fresh bootstrap leaves every business table empty. Raw schema tests prove the live dialogue unique slot, foreign-key actions, approval wire-ID reuse, required check constraints, and that `transient_payloads.content` is the only intentional content payload column. `callback_actions` has only `token_hash_sha256` for callback-token storage.

## Tests and checks

- P2.1 schema/unit: 8 tests, pass
- P2.1 storage integration: 19 tests, pass
- P1.10 T0/T1/T2: 6/1/4 tests, pass
- Focused P1 protocol/runtime/version/capability/catalog/thread/turn/approval/interrupt/delete/error: 28/27/22/18/18/22/17/22/28/15/16 tests, all pass
- Candidate full discovery: 256 tests, pass as reported; this run omitted the integration package and therefore did not include the 19 P2.1 integration tests.
- Compile/import: pass (`P2_1_IMPORT_PASS`)
- Diff check: pass
- Security scan: pass; only explicit fake redaction sentinels matched

The pre-existing P1.6 pending-task warning was observed during P1 turn-lifecycle/full regression. No new P2.1 task warning was introduced.

## Production effects

No production database was opened or created. `/var/lib/codex-control`, `/etc/codex-control`, secrets, auth files, services, and global SSH configuration were not touched. No application/repository/business API, Telegram integration, P2.2+ work, runtime dependency, or seed state was added.

## Architect first repair pass

This is factual repair evidence only. P2.1 is not architect-accepted, and no P2.2 or later work was started.

- Rejected candidate repaired: `08eb22b413cfec464170dd67b63541f7031be9e9`
- Original architect P2.1 base: `f9f71f161ba61508e8bd648ea835e63278377a03`
- Added minimal `tests/integration/__init__.py`; full unittest discovery now imports `tests.integration.test_sqlite_storage_kernel`.
- Repaired the async/lazy callback connection-escape defect. Obvious coroutine/async-generator/generator callback functions fail with `TRANSACTION_FAILED`; awaitable, generator, async-generator and ordinary iterator results are rejected before commit. Synchronous coroutine/generator disposal is performed where available, and tests prove no coroutine escapes or `RuntimeWarning` is emitted.
- Reserved callback transaction ownership with a temporary SQLite authorizer denying `SQLITE_TRANSACTION` and `SQLITE_SAVEPOINT`, removed before kernel commit/rollback. Tests cover connection and explicit COMMIT/ROLLBACK, SAVEPOINT/RELEASE/ROLLBACK TO, and nested BEGIN attempts; each rolls back the preceding insert, invokes the callback once, leaves the connection usable, and performs no retry.
- Normalized an ordinary injected migration-clock exception to redacted `OPEN_FAILED`; the migration rolls back, leaves version 0 with no migration row, releases the lifetime lock, and the same path reopens successfully with a valid clock.
- Replaced the serialization test's elapsed `asyncio.sleep(0.05)` ownership proof with executor-submit instrumentation and event gating.
- Added separate existing lock-file and database-file effective-UID mismatch tests using test-only `fstat` metadata substitution. Each rejects before SQLite connect; a later valid open succeeds and the acquired lock is released.
- Strengthened redaction proof to use an actual `SqliteStorage` instance opened at a sentinel-containing temporary path.
- Schema unchanged: `SCHEMA_V1_DDL_SHA256` remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

Repair test counts:

- P2.1 unit tests: `8`
- P2.1 integration tests: `24`
- Expected full count: `248 + 8 + 24 = 280`
- Observed full discovery: `280` tests, pass
- Full discovery visibly included `test_pragma_contract_and_connection_thread_ownership`, `test_post_submission_write_cancellation_stays_attached_once`, `test_second_owner_locked_then_reopens_after_close`, and `test_fk_cascade_set_null_and_reusable_wire_ids` from `tests.integration.test_sqlite_storage_kernel`.
- P1.10 counts remained `T0=6`, `T1=1`, `T2=4`; the focused P1 regression commands all passed.
- The pre-existing P1.6 pending-task warning remained observable during turn-lifecycle/full regression; this repair did not introduce it.

## Architect second repair pass

This is factual second-repair evidence only. P2.1 remains not architect-accepted.

- Candidate entering this repair: `db1f2d212a59f1b808fc303c9ec64d6eed108af6`.
- The read transaction callback authorizer now carries read/write mode. Read callbacks retain `query_only=ON` and deny query-only bypasses plus INSERT/UPDATE/DELETE action codes.
- Normal callbacks deny PRAGMA setters and allow only the required contract/schema inspection forms. Frozen connection PRAGMA values remain `foreign_keys=1`, `journal_mode=wal`, `busy_timeout=5000`, `synchronous=2`, `trusted_schema=0`, `user_version=1`.
- Normal callbacks deny ATTACH/DETACH, schema DDL/reindex/analyze action codes, and INSERT/UPDATE/DELETE targeting `schema_migrations`. Migration/bootstrap remains outside this callback authorizer.
- Successful callback results are checked for the kernel-owned `isolation_level=None` and `sqlite3.Row` connection contract. Rejected callbacks restore those attributes after rollback.
- Callback-result validation traverses built-in tuple/list/dict/set/frozenset containers cycle-safely and rejects nested SQLite connection/cursor/row/blob and awaitable/generator/iterator resources. Synchronously closable discovered cursor/blob/lazy resources are disposed.
- P2.1 focused tests: `8` unit and `31` integration, all pass. Full discovery: `287` tests, pass, with `31` `integration.test_sqlite_storage_kernel` tests included. Formula: `248 + 8 + 31 = 287`.
- `SCHEMA_V1_DDL_SHA256` remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`; no schema/DDL change was made.
