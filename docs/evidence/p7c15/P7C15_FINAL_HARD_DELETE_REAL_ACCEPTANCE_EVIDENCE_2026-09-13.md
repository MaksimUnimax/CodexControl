# P7.C15 final hard-delete real acceptance evidence — 2026-09-13

## Sanitized execution authority

- Execution branch: `real-p7-c15-final-hard-delete-acceptance-2026-09-13`
- Execution HEAD: `17f8907068aa58de85d92800b9d87621e59ad1a3`
- Execution tree: `993f094a50e062459908f1ddd373c48de478d7a1`
- P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- P7.C15 preparation evidence blob: `4faca2df650917cb1e6c1de529bc658a4fa51286`
- Protected P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- Protected P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- Protected P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`
- Architect main contract HEAD: `8a7519caecd5eebf868f9b52a8171c4a1c61425a`
- Authorization token SHA-256: `cceea732112073baede130f2ae557d86ff7379a481c645ebc70e46d75c75efef`

The exact interpreter was Python 3.12.3. Installed Codex authority was
`codex-cli 0.144.6`; the read-only generated schema aggregate SHA-256 was
`40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
Import authority was `/root/CodexControl/src:/root/CodexControl`. The
gate-disabled smoke returned exit 2, created no P7.C15 parent state/work
directories, and left the replay ledger absent. The read-only source-bundle
gate passed. Historical P7.C13/P7.C14 real gates were unset.

The tracked worktree and index were clean immediately before the real
invocation and the protected source blobs were unchanged after it. The
P7.C15 ledger was absent before authorization and is retained at its required
root-owned regular-file 0600 authority after reservation.

## Sanitized retained result

- Parent exit code: `1`
- Ledger state: `FAILED`
- Watchdog status: `CHILD_FAILURE`
- Child result valid: `true`
- Child status: `FAILED`
- Child verdict: `false`
- Last confirmed stage: `CONTROLLER_BINDING`
- Child terminal exception class: `ValueError`
- Child terminal error category: unavailable
- Runtime child quiescent: `false`
- Exact effect gate: `false`
- Owned group active: `0`
- Owned group zombies: `0`
- Group scan errors: `0`
- Signals sent: `0`
- Child count: `1`
- Retry count: `0`

Safe recovery-field extraction:

```text
PARENT_EXIT_CODE=1
LEDGER_STATE=FAILED
WATCHDOG_STATUS=CHILD_FAILURE
CHILD_RESULT_VALID=true
CHILD_STATUS=FAILED
CHILD_VERDICT=false
LAST_CONFIRMED_STAGE=CONTROLLER_BINDING
RUNTIME_CHILD_QUIESCENT=false
EXACT_EFFECT_GATE=false
OWNED_GROUP_ACTIVE=0
OWNED_GROUP_ZOMBIES=0
GROUP_SCAN_ERRORS=0
SIGNALS_SENT_COUNT=0
CHILD_COUNT=1
RETRY_COUNT=0
MODEL_LIST_COUNT=1
THREAD_START_COUNT=1
THREAD_RESUME_COUNT=1
TURN_START_COUNT=4
APPROVAL_REQUEST_COUNT=1
APPROVAL_RESPONSE_COUNT=1
ALLOW_COUNT=1
DENY_COUNT=0
TURN_INTERRUPT_COUNT=1
THREAD_DELETE_COUNT=0
OFFICIAL_DELETE_CLASS=NOT_CALLED
APPLICATION_DELETE_CLASS=NOT_CALLED
PERSISTENT_THREAD_RESIDUALS=NOT_OBSERVED
PERSISTENT_MARKER_RESIDUALS=NOT_OBSERVED
ISOLATED_THREAD_RESIDUALS=NOT_OBSERVED
ISOLATED_MARKER_RESIDUALS=NOT_OBSERVED
SCAN_ERROR_COUNT=NOT_OBSERVED
POST_DELETE_SCHEMA_CLASS=NOT_OBSERVED
TOMBSTONE_CLASS=NOT_OBSERVED
LIVE_BINDING_CLASS=NOT_OBSERVED
UNRELATED_REMOVAL_CLASS=NOT_OBSERVED
```

The retained stage journal confirmed installed authority, generation 1 and 2
runtime acquisition, one model/list, thread start/resume, completed Turns 1
and 2, Turn 3 completion, Turn 4 interrupt/terminal, runtime shutdown before
the oracle, and schema-v4 controller binding. Marker plaintext and runtime
identifiers are not retained here.

The root-only wire authority was captured. The approval recovery journal had
three events: one approval request, one ALLOW, and one protocol response. No
wire plaintext is reproduced. The accepted approval path reached Turn 3
completion; no Turn 4 unexpected-request failure was recorded.

## Effect counts

| Effect | Count |
|---|---:|
| new_threads | 1 |
| model/list | 1 |
| thread/start | 1 |
| thread/resume | 1 |
| turn/start | 4 |
| approval_requests | 1 |
| approval_responses | 1 |
| allow_responses | 1 |
| deny_responses | 0 |
| turn/interrupt | 1 |
| thread/delete | 0 |
| thread/read | 0 |
| thread/list | 0 |
| second_child | 0 |
| real_retry | 0 |
| telegram | 0 |

## Delete and physical proof classification

Failure occurred after the schema-v4 controller binding and before the
canonical delete dispatch. Therefore the official delete was `NOT_CALLED`,
the application delete was `NOT_CALLED`, and no external delete retry or
manual cleanup was performed.

The post-delete physical acceptance oracle was not reached. Accordingly,
target-specific persistent thread residuals, persistent marker residuals,
isolated thread residuals, isolated marker residuals, post-delete scan-error
count, post-delete schema, tombstone, live-binding, and unrelated-removal
classes are `NOT_OBSERVED` rather than inferred. A bounded read-only check of
the bound isolated roots after failure found sqlite descendants
`regular=4,special=0,symlinks=0,scan_errors=0` and logs descendants
`regular=0,special=0,symlinks=0,scan_errors=0`; these are not post-delete
acceptance results.

## Required flags

P7C15_REAL_RUN_CONSUMED=YES

P7C15_REAL_RETRY_AUTHORIZED=NO

P7C15_REAL_PARENT_EXIT=1

P7C15_REAL_LEDGER_STATE=FAILED

P7C15_REAL_CHILD_STATUS=FAILED

P7C15_REAL_OFFICIAL_DELETE=NOT_CALLED

P7C15_REAL_APPLICATION_DELETE=NOT_CALLED

P7C15_REAL_FINAL_VERDICT=FAIL

P7C14_REAL_RETRY_AUTHORIZED=NO

P7C13_REAL_RETRY_AUTHORIZED=NO

P8_STARTED=NO

P9_STARTED=NO
