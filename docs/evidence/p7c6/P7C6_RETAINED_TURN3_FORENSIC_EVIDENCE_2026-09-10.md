# P7.C6 retained Turn-3 forensic evidence — 2026-09-10

Status: **ZERO-REAL-EFFECT / RETAINED TURN 3 / ARCHITECT REVIEW REQUIRED**

This report is a read-only forensic record. It is not a P7.C6 rerun, same-thread
continuation, harness repair, approval response, interrupt, delete, thread
read/list operation, or continuation authorization.

## Authority and boundary

```text
FORENSIC_BASE_SHA=f2de26426bc09423745357c55fc69b5f2c08791f
FORENSIC_BASE_TREE=48c22ee6fd400bbb5adc7676dc5641feb428dd39
RUN1_EVIDENCE_COMMIT=785a82e2e9bc392173ea1e910b490f84cfa590b2
PERSISTENT_HOME_MODE=SHARED_AUTHENTICATED
UNRELATED_SHARED_HOME_PROCESSES_ALLOWED=YES
REAL_EFFECTS_DURING_FORENSIC=0
```

No real Codex process or app-server was started. No Codex RPC, Telegram call,
filesystem mutation, process signal, persistent-home mutation, ledger mutation,
session-file mutation, isolated-state mutation, or controller mutation occurred.

## Retained recovery identity

The scan found exactly one root-owned recovery ledger satisfying the retained
Run-1 authority conditions. The ledger was not modified, moved, reconstructed,
or committed. The raw identity was used only in process memory.

```text
RECOVERY_LEDGER_MATCHES=1
RECOVERY_LEDGER_MODE=0600
RECOVERY_LEDGER_THREAD_ID_PRESENT=YES
THREAD_ID_SHA256=9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6
```

## Target artifact accounting

Only the persistent session tree was inspected for the retained identity. The
exact target artifact was then parsed as JSONL without emitting content.

```text
TARGET_SESSION_ARTIFACT_COUNT=1
TARGET_SESSION_SCAN_ERRORS=0
TARGET_SESSION_PARSE_ERRORS=0
STRUCTURAL_RECORD_COUNT=39
```

The following table is the complete structural record accounting. Record and
item classes are sanitized structural labels; no record payload, prompt,
response, command, marker, or opaque ID is included.

| Ordinal | Record class | Item class | Item state | Approval-related | Terminal-related | Timestamp |
|---:|---|---|---|---|---|---|
| 1 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 2 | TURN_START | NONE | NONE | NO | NO | YES |
| 3 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 4 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 5 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 6 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 7 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 8 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 9 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 10 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 11 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 12 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 13 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 14 | TURN_TERMINAL | NONE | NONE | NO | YES | YES |
| 15 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 16 | TURN_START | NONE | NONE | NO | NO | YES |
| 17 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 18 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 19 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 20 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 21 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 22 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 23 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 24 | TURN_TERMINAL | NONE | NONE | NO | YES | YES |
| 25 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 26 | TURN_START | NONE | NONE | NO | NO | YES |
| 27 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 28 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 29 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 30 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 31 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 32 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 33 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 34 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 35 | COMMAND_ITEM | COMMAND_EXECUTION | COMPLETED | NO | NO | YES |
| 36 | TOOL_OUTPUT | TOOL_OUTPUT | OUTPUT | NO | NO | YES |
| 37 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 38 | STRUCTURAL | NONE | NONE | NO | NO | YES |
| 39 | TURN_TERMINAL | NONE | NONE | NO | YES | YES |

## Run-1 Turn 3 identity and terminal state

Run-1 Turn 1 and Turn 2 were already definitively completed. The artifact has
three unique ordered turn-start records at ordinals 2, 16, and 26, so the next
unique started turn is exact Run-1 Turn 3.

```text
TURN3_IDENTITY=EXACT
TURN3_ID_SHA256=5fa4626db6882a6023986504838ca23e337717fdf3dc4fd407e41f0aa6f7376a
TURN3_TERMINAL_PERSISTED=YES
TURN3_TERMINAL_CLASS=INTERRUPTED
TURN3_TERMINAL_STATUS_SHA256=d512d96ea31ab0b9bb9b66da70c4d675f7db657518f4b6c0cc6d5823e6da5509
TURN3_TERMINAL_RECORD_COUNT=1
TURN3_TERMINAL_RELATED_RECORD_COUNT=1
```

The `INTERRUPTED` classification is based on the persisted Turn-3 terminal
record. It does not imply that this forensic issued an interrupt.

## Approval state

No approval request, approval decision, or approval response was persisted as a
structural approval-protocol record in the target artifact. Configuration
records containing permission-profile settings were not counted as approval
events.

```text
TURN3_APPROVAL_REQUEST_PERSISTED=NO
TURN3_APPROVAL_DECISION_PERSISTED=NONE
TURN3_APPROVAL_RESPONSE_PERSISTED=NO
TURN3_APPROVAL_RELATED_RECORD_COUNT=0
C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN
```

The published runtime result remains `RESPONSE_UNKNOWN`; this forensic does not
reinterpret it and did not answer or retry the old approval request.

## Command/tool item state

There is one persisted command item. Its structural item status is
`COMPLETED`; the associated tool-output record is not a second command item.

```text
TURN3_COMMAND_ITEM_COUNT=1
TURN3_COMMAND_ITEM_STATE=COMPLETED
```

## Optional historical grammar forensic

The persisted command input was reconstructable in memory. Its plaintext is
not recorded. Against the historical safe matcher, it is not an exact inner
command or a single approved shell wrapper around the expected bounded Run-1
command.

```text
TURN3_HISTORICAL_SAFE_GRAMMAR_CLASS=OTHER
OBSERVED_APPROVAL_COMMAND_SHA256=69da337831d6b9729c7710a063af5133cebd0a32459d428e9309d7f9caf42b0a
TURN3_COMMAND_MISMATCH_FLAGS=TOKEN_MISMATCH
```

This classification is observational only and does not authorize retroactive
ALLOW, response, retry, continuation, interrupt, or delete.

## Run-owned process and sentinel forensic

The retained run-owned boundary was inspected using read-only filesystem
metadata and `/proc` references. No other process referenced the retained root,
isolated state, isolated SQLite/log subtrees, controller boundary, ledger,
workdir, or sentinel boundary. The run-owned sentinel path was absent.

```text
ISOLATED_ROOT_EXTERNAL_USERS=0
CONTROLLER_DB_EXTERNAL_USERS=0
UNRELATED_PROCESS_TERMINATION_CALLS=0
PROCESS_FORENSIC_SCAN_ERRORS=0
C6_RUN1_DELAYED_PROCESS_PRESENT=NO
C6_RUN1_SENTINEL_PRESENT=NO
```

## Final retained state

The exact target artifact, exact Turn-3 identity, durable terminal, non-pending
command item, non-persisted approval state, absent delayed process, absent
sentinel, and zero scan/parse errors establish a finite terminal boundary for
architect review. This report itself grants no continuation authority.

```text
RETAINED_TURN3_STATE=TERMINAL_SAFE_FOR_ARCHITECT_REVIEW
P7C6_CONTINUATION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
```

## Real-effect accounting

```text
REAL_CODEX_PROCESS_STARTS=0
REAL_APP_SERVER_STARTS=0
MODEL_LIST_CALLS=0
THREAD_START_CALLS=0
THREAD_RESUME_CALLS=0
TURN_START_CALLS=0
APPROVAL_RESPONSES=0
INTERRUPT_CALLS=0
THREAD_DELETE_CALLS=0
THREAD_READ_CALLS=0
THREAD_LIST_CALLS=0
TELEGRAM_CALLS=0
PROCESS_SIGNAL_CALLS=0
```

No raw thread ID, turn ID, request ID, command, prompt, response, marker,
session line, credential, token, or environment dump is included in this file.
