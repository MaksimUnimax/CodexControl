# CODEXCONTROL P7.C6 SAME-THREAD PREP-V2 REPAIR-2 EVIDENCE

Status: ZERO-REAL-EFFECT / REPAIR-ONLY / REAL CONTINUATION NOT AUTHORIZED

ARCHITECT_BASE_SHA=5cc500be0087732518eb16bee0dc71dc21f786c0
ARCHITECT_BASE_TREE=d8b03629a47c6803d3ac118720acb74e453d67c5
REPAIR1_CANDIDATE=821be881f1e6b04d3905080191cc0f1141799923

REAL_EFFECTS_DURING_REPAIR2=0
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

REAL_TOPOLOGY_MATRIX_TESTS=1
EXTERNAL_USER_SCOPE_TESTS=2
LOCAL_PRE_EFFECT_PATH_TESTS=2

JOURNAL_FAIL_CLOSED_TESTS=1
ASYNC_TASK_OWNERSHIP_TESTS=3

SAFE_MARKER_ORACLE_TESTS=6
PATHNAME_REPLACEMENT_TESTS=1

UNRELATED_BASELINE_BOUND_TESTS=1
UNRELATED_EXACT_IDENTITY_TESTS=2

DYNAMIC_BUDGET_TESTS=3
UNKNOWN_RPC_REJECTION_TESTS=1

CONTROLLER_PATH_AUTHORITY_TESTS=1

OFFICIAL_DELETE_OBSERVER_TESTS=2
OFFICIAL_DELETE_UNKNOWN_TESTS=1

FAILURE_RETENTION_BEHAVIOR_TESTS=7
SUCCESS_SANITIZATION_TESTS=4

STRUCTURAL_MATCHER_ALLOW_CASES=13
STRUCTURAL_MATCHER_DENY_CASES=18
CONTINUATION_NEW_THREAD_PATH_PRESENT=NO
REAL_METHOD_GATE_DISABLED=PASS

EXPLICIT_REAL_FILE_TESTS=41
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

The Repair-2 harness admits the complete retained run topology only through
the frozen nested-containment matrix and still rejects unexpected overlap,
same-inode aliasing, symlink components and exact mountpoints. Repository use
is not treated as a continuation-owned process boundary; isolated, controller
and recovery boundaries remain owned and fail closed on ambiguity.

All continuation local paths are derived before reservation, including a
high-entropy run-owned sentinel, and are proven absent, non-overlapping and
safe before any real effect. Required journal updates persist dispatch intent
before each material effect and finite observation afterward; a failed update
blocks the next effect.

The acceptance-only marker oracle uses bounded descriptor/no-follow reads,
chunk carry, pathname and descriptor identity revalidation, mutation-sensitive
metadata checks, and explicit scan/limit accounting. The unrelated baseline
records exact relative path/category/device/inode identity while allowing size,
mtime and new-artifact changes.

Offline fakes prove timeout shutdown/convergence ownership of the same task,
approval cancellation with no late allow, delete uncertainty with no retry,
DELETE_UNKNOWN propagation, controller database path authority, unknown RPC
rejection, forensic retention on ambiguity, and success-only sanitization.

No raw thread IDs, marker plaintext, prompts, responses, runtime commands,
credentials, tokens or root-only recovery contents are stored in this evidence.
