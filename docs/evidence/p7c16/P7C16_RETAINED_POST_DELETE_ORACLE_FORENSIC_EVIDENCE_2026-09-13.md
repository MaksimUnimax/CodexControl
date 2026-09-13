# P7.C16 retained post-delete oracle forensic evidence — 2026-09-13

Status: **READ-ONLY FORENSIC / REAL RUN CONSUMED / RETRY FORBIDDEN**

## Binding

The forensic worktree was checked out at the required consumed real-evidence
commit and was not merged, rebased, squashed, or source-edited.

```text
FORENSIC_BASE_HEAD=fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a
FORENSIC_BASE_TREE=569d2d9707e718975a54a52a4f1538fb8e3ef0d0
REAL_EVIDENCE_COMMIT=fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a
REAL_EVIDENCE_BLOB=071643cfbeb73341c0c863058288f7c16a95c4ca
EXECUTION_SOURCE=5fb8ed6c2a27da3149476ec8501c533152a19b8f
EXECUTION_TREE=251ec8d3971460dafd57429112a357b1b53e9b50
P7C16_LAUNCHER_BLOB=2c500d7d5787a7eda71c1e3e3591d8034dded590
ARCHITECT_MAIN=0b4b7ed1d7070b573d4fde4b8f920c6b0d6756f1
ARCHITECT_MAIN_TREE=746edce7e256cdc1161ae106487260ca13259b55
```

The authoritative documents were read in full directly from `origin/main`:

- `P7C16_REAL_FAILURE_ARCHITECT_REVIEW_2026-09-13.md`;
- `P7C16_RETAINED_POST_DELETE_ORACLE_FORENSIC_CONTRACT_2026-09-13.md`;
- `P7C16_RETAINED_POST_DELETE_ORACLE_FORENSIC_AUTHORITY_2026-09-13.md`.

The exact final real-acceptance evidence was read in full from the forensic
base. `origin/main` was verified before and after the forensic work as
`0b4b7ed1d7070b573d4fde4b8f920c6b0d6756f1` with tree
`746edce7e256cdc1161ae106487260ca13259b55`.

## Absolute zero-effect statement

This pass performed no Codex run, app-server start, provider call, RPC,
approval, delete, cleanup, retry, signal, or Telegram operation. No historical
real token was set. No P7.C16/P7.C15/P7.C14/P7.C13 retained authority was
modified.

```text
CODEX_PROCESS_STARTS=0
APP_SERVER_STARTS=0
MODEL_LIST_CALLS=0
THREAD_START_CALLS=0
THREAD_RESUME_CALLS=0
THREAD_READ_CALLS=0
THREAD_LIST_CALLS=0
THREAD_DELETE_CALLS=0
TURN_START_CALLS=0
TURN_INTERRUPT_CALLS=0
APPROVAL_RESPONSES=0
ALLOW_RESPONSES=0
DENY_RESPONSES=0
P7C16_LEDGER_MUTATIONS=0
P7C15_LEDGER_MUTATIONS=0
P7C14_LEDGER_MUTATIONS=0
P7C13_LEDGER_MUTATIONS=0
CONTROLLER_DB_MUTATIONS=0
PERSISTENT_HOME_MUTATIONS=0
ISOLATED_STATE_MUTATIONS=0
HISTORICAL_CLEANUP=0
PROCESS_SIGNALS=0
TELEGRAM=0
```

## Retained-run binding and result

Only the P7.C16 ledger was used as the durable run selector. It is a root-owned
regular file, mode `0600`, link count `1`, not a symlink, and bounded JSON.
Its source head/tree/launcher binding matches the consumed execution source.
The ledger-bound boot authority, child result, stage journal, wire authority,
approval recovery journal, and controller database all match the same run
binding. Raw run, thread, turn, token, path-suffix, command, and marker values
are intentionally not reproduced here.

Independent retained-authority readback proves:

```text
P7C16_REAL_RUN_CONSUMED=YES
P7C16_REAL_RETRY_AUTHORIZED=NO
P7C16_REAL_LEDGER_STATE=FAILED
P7C16_REAL_WATCHDOG_STATUS=CHILD_FAILURE
P7C16_REAL_CHILD_STATUS=FAILED
P7C16_REAL_LAST_CONFIRMED_STAGE=RUNTIME_SHUTDOWN_FINAL
P7C16_REAL_TERMINAL_EXCEPTION_CLASS=P7C15PreparationError
P7C16_REAL_RUNTIME_CHILD_QUIESCENT=TRUE
P7C16_REAL_THREAD_DELETE_DISPATCH_COUNT=1
P7C16_REAL_OFFICIAL_DELETE=DELETE_CONFIRMED
P7C16_REAL_APPLICATION_DELETE=DELETED
```

The stage journal contains `RUNTIME_SHUTDOWN_FINAL`, contains no
`POST_DELETE_ORACLE`, and ends with one `TERMINAL_EXCEPTION` carrying the
`P7C15PreparationError` class. The child result is therefore the retained
source-compatible `post-delete observed oracle failed` path.

The exact effect matrix is:

```text
new_threads=1
model/list=1
thread/start=1
thread/resume=1
turn/start=4
approval_responses=1
allow_responses=1
turn/interrupt=1
thread/delete=1
thread/read=0
thread/list=0
second_child=0
real_retry=0
telegram=0
```

## Source reconstruction

The exact consumed source files were inspected from execution source
`5fb8ed6c2a27da3149476ec8501c533152a19b8f`:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `tests/real/test_p7_c16_final_hard_delete_successor.py`.

The P7.C16 child composes the consumed P7.C15 `run_async` continuation. After
`RUNTIME_SHUTDOWN_FINAL`, the source sequence is:

1. tombstone read;
2. post-delete live-binding read;
3. post-delete schema read;
4. bounded controller close in the `finally` path;
5. persistent observation;
6. isolated observation;
7. unrelated-removal derivation;
8. isolation-envelope validation;
9. isolated SQLite/log descendant scan;
10. recovery-class derivation;
11. `post_delete_acceptance(...)`.

`POST_DELETE_ORACLE` is marked only after that call returns true. The source
call raises `P7C15PreparationError("post-delete observed oracle failed")` when
the call returns false. With the retained terminal exception,
`runtime_child_quiescent=true`, and no `POST_DELETE_ORACLE` mark, the exact
failure gate is reconstructed as:

```text
P7C16_FORENSIC_FAILURE_GATE=POST_DELETE_ACCEPTANCE_REJECTED
```

The frozen oracle implementation is the `all(...)` predicate in
`test_p7_c13_final_hard_delete_acceptance.py`. It checks every predicate below;
marker residuals are not ignored and parent-owned `None` values are explicitly
non-blocking.

## Read-only controller authority

The exact ledger-bound controller database was opened only through an
immutable read-only URI equivalent to
`file:<ledger-bound-controller-db>?mode=ro&immutable=1`. No ordinary writable
storage wrapper, transaction, checkpoint, WAL operation, VACUUM, or schema
operation was used.

```text
PRAGMA user_version=4
live_dialogues=0
deletion_tombstone_rows=1
delete_storage_containment_rows=0
approvals=0
callback_actions=0
controller_runtime=0
delivery_segments=0
errors=0
ingress_updates=0
settings=0
transient_payloads=0
turn_jobs=0
tombstone_dialogue_id=bounded-string-class-only
tombstone_thread_identity=64-byte-sha256-class-only
tombstone_stale_generation=4
tombstone_expiry_order=VALID
wire_tombstone_thread_hash_agreement=PASS
```

Thus the live binding is absent, the tombstone is one bounded deletion
record, and the controller post-delete residual class is zero.

## Oracle observations

All filesystem observations below used bounded no-follow traversal. Regular
files were opened read-only with no-follow flags and bounded reads. The exact
P7.C16 isolated root was taken only from the ledger-bound boot authority; no
retained P7.C15/P7.C14 root was included.

Current persistent tree readback, including unrelated retained material:

```text
persistent_session_regular_files=9
persistent_session_directories=40
persistent_session_symlinks=0
persistent_session_special_files=0
persistent_session_scan_errors=0
persistent_history_regular_files=1
persistent_history_scan_errors=0
```

Exact isolated-root readback:

```text
isolated_sqlite_regular_descendants=0
isolated_sqlite_special_descendants=0
isolated_sqlite_symlinks=0
isolated_sqlite_scan_errors=0
isolated_logs_regular_descendants=0
isolated_logs_special_descendants=0
isolated_logs_symlinks=0
isolated_logs_scan_errors=0
```

The same source-equivalent isolation envelope validation returned the safe
class `VALID`: the bound root and parents are root-owned and non-writable by
group/world; the root is private; the required marker, `sqlite`, and `logs`
entries are present; the marker and nested tree entries satisfy the required
regular-file/directory, ownership, and mode checks; and no symlink or special
entry was found.

### Predicate matrix

`UNRECOVERABLE` means the exact historical input was not persisted and was not
guessed. It is not included in `FAILED_PREDICATES`. `ORIGINAL_EVIDENCE` means
the value was already present in the consumed evidence; `FORENSIC_READBACK`
means it was independently measured now; `STATIC_SOURCE_ONLY` means source
semantics were reconstructed but no historical value was claimed.

| Predicate input | Observed sanitized value | Result | Authority source | Evidence class |
|---|---:|---|---|---|
| `official_delete == DELETE_CONFIRMED` | `DELETE_CONFIRMED` | PASS | child result and real evidence | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `application_result == DELETED` | `DELETED` | PASS | child result and real evidence | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `tombstone_bounded` | `true` | PASS | immutable controller tombstone; hash agreement; expiry order | FORENSIC_READBACK |
| `live_binding == false` | `false` | PASS | immutable controller: no live dialogue rows | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `envelope_valid` | `true`, safe class `VALID` | PASS | exact isolated-root read-only validation | FORENSIC_READBACK |
| `post_delete_schema == 4` | `4` | PASS | immutable `PRAGMA user_version` | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `isolated_sqlite_descendants == 0` | `0` regular descendants | PASS | exact isolated sqlite scan | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `isolated_logs_descendants == 0` | `0` regular descendants | PASS | exact isolated logs scan | ORIGINAL_EVIDENCE / FORENSIC_READBACK |
| `persistent.thread_count == 0` | `UNRECOVERABLE_FROM_RETAINED_STATE` | UNRECOVERABLE | exact thread value not retained; target hash candidate replay found no match | FORENSIC_READBACK |
| `persistent.thread_filename_count == 0` | `UNRECOVERABLE_FROM_RETAINED_STATE` | UNRECOVERABLE | exact thread value not retained | FORENSIC_READBACK |
| `persistent.thread_directory_count == 0` | `UNRECOVERABLE_FROM_RETAINED_STATE` | UNRECOVERABLE | exact thread value not retained | FORENSIC_READBACK |
| `persistent.marker_count == 0` | `at least 3` known `TURN4_STIMULUS` residuals; exact total may be higher | FAIL | persistent no-follow scan of sessions/history | FORENSIC_READBACK |
| `isolated.thread_count == 0` | `0` files to inspect | PASS | exact isolated sqlite/log tree | FORENSIC_READBACK |
| `isolated.marker_count == 0` | `0` files to inspect | PASS | exact isolated sqlite/log tree | FORENSIC_READBACK |
| `persistent.scan_errors == 0` | `0` | PASS | persistent no-follow scan | FORENSIC_READBACK |
| `isolated.scan_errors == 0` | `0` | PASS | exact isolated no-follow scan | FORENSIC_READBACK |
| combined `scan_errors == 0` | `0` (`sqlite_errors + logs_errors`) | PASS | exact isolated descendant scans | FORENSIC_READBACK |
| `owned_children is None or 0` | `None` in child oracle invocation | PASS | exact source call; parent-owned | STATIC_SOURCE_ONLY |
| `owned_group_active is None or false` | `None` in child oracle invocation | PASS | exact source call; parent-owned | STATIC_SOURCE_ONLY |
| `owned_group_zombies is None or 0` | `None` in child oracle invocation | PASS | exact source call; parent-owned | STATIC_SOURCE_ONLY |
| `unrelated_signals is None or 0` | `None` in child oracle invocation | PASS | exact source call; parent-owned | STATIC_SOURCE_ONLY |
| `unrelated_target_specific_removal_detected == false` | `UNRECOVERABLE_FROM_RETAINED_STATE` | UNRECOVERABLE | pre-delete metadata snapshot not persisted | FORENSIC_READBACK / STATIC_SOURCE_ONLY |
| `budgets_ok == true` | `true`; recovery class `COMPLETED` | PASS | exact frozen recovery mapping and effect matrix | ORIGINAL_EVIDENCE / STATIC_SOURCE_ONLY |

The marker failure is definite even though the exact total marker count is not
recoverable: the source's marker set always includes the fixed
`TURN4_STIMULUS`, and three occurrences were read in the persistent session
root. The source scanner counts marker occurrences in every regular file under
the selected persistent roots, not only in files containing the target thread.

## Marker analysis

The exact consumed-run random memory/response marker pair was not recoverable
from the ledger, boot, child result, stage, wire, approval, or controller
authorities. A random pair found in one pre-existing persistent session file
was rejected as consumed-run evidence: its retained session material predates
the P7.C16 authority timestamps and its session identity does not match the
retained P7.C16 target hash. It is classified as unrelated retained material.

```text
MEMORY_MARKER
  family=persistent_sessions
  matching_files=1
  count=7
  safe_marker_hash=21621a35d72b669d7b82189aad175d0aa55a3e471ba11b5f435e2764cd2b3f4e
  classification=UNRELATED_RETAINED_SESSION_MATERIAL

RESPONSE_MARKER
  family=persistent_sessions
  matching_files=1
  count=5
  safe_marker_hash=abf01ec747d8fdbfd7676273a548d807c91d380cdd10a0b43f827afcf5e4681f
  classification=UNRELATED_RETAINED_SESSION_MATERIAL

TURN4_STIMULUS
  family=persistent_sessions
  matching_files=1
  count=3
  safe_marker_hash=2fb7d1ee472b031c6052d6256fbf8107ddcf84ad81f9bc3d6715ecb521c69890
  classification=UNRELATED_RETAINED_SESSION_MATERIAL; ALSO THE CURRENT-RUN STATIC MARKER
```

The current-run random marker families are therefore
`UNRECOVERABLE_FROM_RETAINED_STATE`; no plaintext marker was published.
The fixed `TURN4_STIMULUS` residual is independently sufficient for the
failed persistent marker predicate.

## Unrelated-removal analysis

Exact source semantics:

- `target_metadata_snapshot(...)` traverses `codex_home/sessions` and the
  `history.jsonl` regular-file root, with a 4096 regular-file bound;
- it records `(st_dev, st_ino)` only for regular files;
- `target_paths` contains only recorded regular-file paths whose full path
  contains the exact thread ID;
- directories are traversed but are not themselves recorded;
- `derived_unrelated_removal_fact(...)` returns true when a path in the
  pre-delete regular-file snapshot is absent afterward and is not in
  `target_paths`.

No exact `unrelated_before`, `target_paths`, or `unrelated_after` snapshot was
persisted in the retained P7.C16 authorities. Exact replay is consequently:

```text
UNRELATED_REMOVAL_EXACT_REPLAY=NOT_PERSISTED
```

The static/current-state causality audit establishes a structurally possible
false-positive class. A removed regular file that does not contain the thread
ID in its path, including the fixed history-file path or a regular ancestor/
session-container artifact, would be in `before`, absent from `after`, absent
from `target_paths`, and therefore classified as unrelated. A directory-only
ancestor is not recorded by this function. There is no retained evidence that
such a removal occurred during P7.C16, so it is not promoted to the root cause.

```text
UNRELATED_REMOVAL_FALSE_POSITIVE_CLASS=POSSIBLE
UNRELATED_REMOVAL_ROOT_CAUSE_PROMOTED=NO
```

## Recovery and budget audit

Using the frozen source mapping:

```text
official_status=DELETE_CONFIRMED
application_status=DELETED
map_terminal_recovery_class=COMPLETED
budgets_ok=true
```

The exact positive effect matrix matches the frozen budget. There is no
recovery-class mismatch.

## Failed predicate set and root-cause verdict

The directly proven failed set contains exactly one predicate:

```text
FAILED_PREDICATES={persistent.marker_count == 0}
FAILED_PREDICATE_COUNT=1
PRIMARY_FAILED_PREDICATE=PERSISTENT_MARKER_RESIDUAL
```

Persistent thread count, persistent filename count, persistent directory count,
and unrelated-removal status remain unrecoverable historical inputs. They are
not included in the failed set. The isolated counts, scan counts, envelope,
controller state, delete classes, recovery class, parent-owned `None` values,
and budgets are directly clean or non-blocking.

Root cause is declared only for the predicate directly established by source
semantics plus retained evidence plus readback: the shared persistent oracle
counted three occurrences of the current-run static `TURN4_STIMULUS` in one
unrelated retained session file. This uniquely suffices to make
`post_delete_acceptance(...)` false and explains the retained fail-closed
exception. The safe root-cause class is:

```text
P7C16_FORENSIC_ROOT_CAUSE=PERSISTENT_MARKER_RESIDUAL
```

No successor design, P7.C16 patch, P7.C17 preparation, P8 work, or P9 work is
authorized by this evidence.

## Retained-state mutation proof

Before and after the forensic reads, safe metadata identities and internal file
digests were captured for the P7.C16 ledger, ledger-bound boot authority, child
result, stage journal, wire authority, approval recovery journal, controller
database, controller sidecar state, exact isolated-root metadata, persistent
home root, sessions tree, and history file. Every before/after identity and
digest comparison was equal. No secret-bearing digest is published.

```text
P7C16_LEDGER_RETAINED_EQUALITY=PASS
BOOT_AUTHORITY_RETAINED_EQUALITY=PASS
CHILD_RESULT_RETAINED_EQUALITY=PASS
STAGE_JOURNAL_RETAINED_EQUALITY=PASS
WIRE_AUTHORITY_RETAINED_EQUALITY=PASS
APPROVAL_RECOVERY_JOURNAL_RETAINED_EQUALITY=PASS
CONTROLLER_DB_RETAINED_EQUALITY=PASS
CONTROLLER_SIDECARS_RETAINED_EQUALITY=PASS
ISOLATED_ROOT_RETAINED_EQUALITY=PASS
PERSISTENT_HOME_RETAINED_EQUALITY=PASS
P7C16_FORENSIC_RETAINED_MUTATIONS=0
```

P7C16_FORENSIC_REAL_EFFECTS=0

P7C16_FORENSIC_RETAINED_MUTATIONS=0

P7C16_FORENSIC_POST_DELETE_GATE_RECONSTRUCTED=PASS

P7C16_FORENSIC_FAILED_PREDICATE_COUNT=1

P7C16_FORENSIC_PRIMARY_FAILED_PREDICATE=PERSISTENT_MARKER_RESIDUAL

P7C16_FORENSIC_ROOT_CAUSE=PERSISTENT_MARKER_RESIDUAL

P7C16_REAL_RUN_CONSUMED=YES

P7C16_REAL_RETRY_AUTHORIZED=NO

P7C17_PREPARATION_AUTHORIZED=NO

P7C15_REAL_RETRY_AUTHORIZED=NO

P7C14_REAL_RETRY_AUTHORIZED=NO

P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO

P9_STARTED=NO
