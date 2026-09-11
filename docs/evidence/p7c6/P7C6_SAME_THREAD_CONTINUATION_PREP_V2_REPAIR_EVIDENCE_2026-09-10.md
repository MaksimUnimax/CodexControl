# CODEXCONTROL P7.C6 SAME-THREAD CONTINUATION PREP-V2 REPAIR EVIDENCE

Status: ZERO-REAL-EFFECT / REPAIR-ONLY / REAL CONTINUATION NOT AUTHORIZED

ARCHITECT_BASE_SHA=c4ebe5fa2d069524e921f3a15148e85aa3423216
ARCHITECT_BASE_TREE=a6880f388f498b48abe0926e7abc13e75bb54e21
REVIEWED_CANDIDATE=1c9b03108bb2493fd6547a92c807397bb4c0868c

REAL_EFFECTS_DURING_REPAIR=0
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

SOURCE_AUTHORITY_GATE_TESTS=1 method covering exact head/tree pass, wrong head, wrong tree and dirty worktree
MOUNT_ALIAS_PREFLIGHT_TESTS=2
CONTROLLER_ACTUAL_SCHEMA_TESTS=2 methods covering actual v4, wrong actual version, live dialogue and tombstone conflict
UNRELATED_BASELINE_TESTS=1
SAFE_MARKER_ORACLE_TESTS=4 methods covering ordinary/chunk-boundary, symlink, hardlink, read failure, inode substitution, special file and all limits
STRUCTURAL_MATCHER_ALLOW_CASES=13
STRUCTURAL_MATCHER_DENY_CASES=18
CONTINUATION_LATCH_TESTS=2
DYNAMIC_BUDGET_TESTS=2
INTERRUPT_NO_REACQUIRE_TESTS=1 helper gate plus regression assertions
OFFICIAL_DELETE_OBSERVER_TESTS=2
RECOVERY_JOURNAL_TESTS=1
SUCCESS_SANITIZATION_TESTS=2
FAILURE_EVIDENCE_RETENTION_TESTS=2

CONTINUATION_NEW_THREAD_PATH_PRESENT=NO
REAL_METHOD_GATE_DISABLED=PASS

EXPLICIT_REAL_FILE_TESTS=24
EXPLICIT_REAL_FILE_SKIPPED=1
EXPLICIT_REAL_FILE_FAILURES=0
EXPLICIT_REAL_FILE_ERRORS=0

FOCUSED_TESTS=106
FOCUSED_SKIPPED=0
FOCUSED_FAILURES=0
FOCUSED_ERRORS=0

FULL_TESTS=1065
FULL_SKIPPED=0
FULL_FAILURES=0
FULL_ERRORS=0

PERSISTENT_HOME_MODE=SHARED_AUTHENTICATED
UNRELATED_SHARED_HOME_PROCESSES_ALLOWED=YES
UNRELATED_PROCESS_TERMINATION_CALLS=0
P7C6_REAL_CONTINUATION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO

The continuation method requires architect-supplied exact accepted HEAD and
tree authorities, a clean repository, the unchanged accepted Run-1 latch and
retained-thread hash before creating its exclusive continuation latch. The
latch stores only accepted source SHA/tree, retained-thread SHA-256, status and
continuation identity. A root-only exclusive recovery journal is created
before resume and updated with finite progress; ambiguous approval, turn,
interrupt or delete paths retain forensic authority.

The acceptance-only marker oracle uses bounded descriptor/no-follow reads,
owner/mode/link and inode checks, chunk carry, file and byte limits, and
fail-closed error/limit fields. The unrelated baseline stores only safe
relative categories and device/inode identities. Actual controller
``PRAGMA user_version`` and live/tombstone/idempotency state are checked
through the storage read boundary. Official delete status is observed from
the exact lifecycle result, and success-only sanitization occurs after all
post-delete and budget gates.

No raw thread IDs, marker plaintext, commands, prompts, responses,
credentials, tokens or root-only recovery contents are stored in Git evidence.
