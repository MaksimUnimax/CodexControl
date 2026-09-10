# P7.C6 real-run failure evidence — 2026-09-10

Status: **FAILED / ONE-SHOT CONSUMED / RECOVERY REQUIRED**

The run used architect main `32153c3d63bf6b45a8b16478566997c09e8e0cac` and
tree `2dd760ba3fe7ea880c6c65db3eb6c0673d70ed75`.

## Authority and boundary

- `PERSISTENT_HOME_MODE=SHARED_AUTHENTICATED`
- `UNRELATED_SHARED_HOME_PROCESSES_ALLOWED=YES`
- Existing authenticated home: `/root/.codex_second`
- Selected profile ID: `server-80-codexcontrol`
- Installed authority: `/usr/local/bin/codex`, `codex-cli 0.144.6`
- Schema SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`
- Read-only mount/alias preflight: `PASS`
- Shared-home processes observed during preflight: `8`; allowed under ADR-0045
- `ISOLATED_ROOT_EXTERNAL_USERS=0`
- `CONTROLLER_DB_EXTERNAL_USERS=0`
- `UNRELATED_PROCESS_TERMINATION_CALLS=0`
- `MANUAL_PERSISTENT_HOME_CLEANUP=0`

The fresh isolated root and synthetic controller database were root-owned and
private. The isolated root and recovery identity remain outside Git for
bounded recovery. The temporary working directory and delayed sentinel were
removed. No historical rejected P7 thread was touched.

## One-shot outcome

The real run created one new disposable thread and reached the third-turn
approval stage. The exact approval/ALLOW proof did not satisfy the frozen
acceptance condition and stopped with `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`.
The run therefore performed no interrupt and no official delete.

Safe identity hashes:

- target thread ID SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`
- marker values: retained only in the run-owned recovery ledger; not persisted
  in Git because no acceptance proof was completed

Real-effect counts reached before the terminal stop:

- `MODEL_LIST_CALLS=1`
- `THREAD_START_CALLS=1`
- `THREAD_RESUME_CALLS=1`
- `TURN_CALLS=3`
- `APPROVAL_ALLOW_RESPONSES<=1`
- `INTERRUPT_CALLS=0`
- `THREAD_DELETE_CALLS=0`
- `THREAD_READ_CALLS=0`
- `THREAD_LIST_CALLS=0`
- `TELEGRAM_CALLS=0`

The exact raw thread ID and selected run paths are retained only in the
root-only recovery ledger. A separate root-only one-shot ledger prevents an
automatic rerun of this authorization.

## Regression

- Corrected C2–C5 focused preflight: `106` tests, `OK`.
- Ordinary full `unittest discover -s tests` with real authorization unset:
  `1066` tests, `OK`, `1` expected gated skip, zero failures/errors.

## Acceptance disposition

This is not a P7.C6 PASS. The required delete and post-delete gates are not
established:

- `OFFICIAL_P1_DELETE_STATUS=NOT_DISPATCHED`
- `APPLICATION_DELETE_STATUS=NOT_REACHED`
- `POSTDELETE_PERSISTENT_THREAD_RESIDUALS=NOT_MEASURED`
- `POSTDELETE_PERSISTENT_MARKER_RESIDUALS=NOT_MEASURED`
- `POSTDELETE_ISOLATED_THREAD_RESIDUALS=NOT_MEASURED`
- `POSTDELETE_ISOLATED_MARKER_RESIDUALS=NOT_MEASURED`
- `POSTDELETE_SQLITE_DESCENDANTS=NOT_APPLICABLE_BEFORE_DELETE`
- `POSTDELETE_LOGS_DESCENDANTS=NOT_APPLICABLE_BEFORE_DELETE`
- `OWNERSHIP_ENVELOPE_VALID=PASS`

P8 and P9 remain blocked. No retry, read, list, manual persistent-home
mutation, or unrelated-process termination is authorized by this evidence.

## Approval failure forensic

This section is a read-only forensic supplement to the already executed
one-shot result. It does not authorize continuation, retry, approval, read,
list, interrupt, or delete.

The run-owned recovery ledger was present and mode `0600`; its raw thread ID
remains retained only there. Exactly one matching Codex-owned session-history
artifact was found by that retained ID. The run-owned logs and session record
contain no persisted normalized approval-request payload or process-local
operator diagnostics. The recorded `AssertionError` shows that the harness
reached its post-`handle_next()` approval assertion; payload-dependent fields
below therefore remain fail-closed where they cannot be proven locally.

```text
C6_APPROVAL_REQUEST_OBSERVED=YES
C6_APPROVAL_REQUEST_COUNT=1
C6_APPROVAL_KIND=COMMAND_EXECUTION
C6_APPROVAL_BRIDGE_NORMALIZATION=UNKNOWN
C6_OPERATOR_DECISION=UNKNOWN
C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN

C6_EXPECTED_THREAD_MATCH=UNKNOWN
C6_EXPECTED_TURN_MATCH=UNKNOWN
C6_EXPECTED_CWD_MATCH=UNKNOWN

C6_EXPECTED_MARKER_PRESENT=UNKNOWN
C6_EXPECTED_SENTINEL_PRESENT=UNKNOWN

C6_CURRENT_MATCHER_CLASS=LITERAL_EXACT
C6_CURRENT_MATCHER_FAILURE_FLAGS=LOCAL_REQUEST_DIAGNOSTICS_UNAVAILABLE

C6_HISTORICAL_SAFE_GRAMMAR_CLASS=UNAVAILABLE
C6_OBSERVED_COMMAND_SHA256=UNAVAILABLE

C6_APPROVAL_FAILURE_CLASS=INSUFFICIENT_LOCAL_EVIDENCE

C6_OUTSIDE_SENTINEL_PRESENT=NO
C6_RUN_OWNED_DELAYED_PROCESS_PRESENT=NO

RECOVERY_LEDGER_PRESENT=YES
RECOVERY_LEDGER_RAW_THREAD_ID_RETAINED_LOCALLY=YES

OFFICIAL_DELETE_STATUS=NOT_RUN
REAL_THREAD_DELETE_CALLS=0
REAL_THREAD_READ_CALLS=0
REAL_THREAD_LIST_CALLS=0

P7C6_ACCEPTANCE_VERDICT=FAIL_T3_APPROVAL_GATE
RECOVERY_LEDGER_DISPOSITION=RETAINED_FOR_RECOVERY

P8_STARTED=NO
P9_STARTED=NO
```

The historical `_FinalAllowOperator` is structural: it requires exact thread,
turn, cwd, marker, sentinel, request-count, supported
`COMMAND_EXECUTION`, and either `EXACT_INNER` or `ONE_SHELL_WRAPPER` grammar.
The current C6 operator is a literal command-set matcher and does not persist
the request diagnostics needed to establish whether it rejected a safe
structural equivalent. Accordingly, this forensic pass does not classify the
failure as a harness matcher defect or as a production approval-normalization
defect.

No potentially C6-owned delayed process was found, and the outside sentinel
was absent. No process was killed, signalled, interrupted, or otherwise
mutated during this forensic pass. No persistent session/history cleanup was
performed.
