# CODEXCONTROL P7.C6 SAME-THREAD PREP-V2 REPAIR-3 EVIDENCE

Status: ZERO-REAL-EFFECT / REPAIR-ONLY / REAL CONTINUATION NOT AUTHORIZED

ARCHITECT_BASE_SHA=de398808cfce7d4c42da3d08109e5a166078cd34
ARCHITECT_BASE_TREE=1d5166d53b80a30afe0d4b89651a53648e9702a4
REPAIR2_CANDIDATE=4d98e2b6170e76534fa18274236605f77440f740

REAL_EFFECTS_DURING_REPAIR3=0

FINAL_TIMEOUT_PATHS_BOUNDED=PASS
TASK_TERMINALIZATION_MATRIX=PASS
TURN4_APPROVAL_SIBLING_FAILURE_GATE=PASS
TURN5_WAITER_SIBLING_FAILURE_GATE=PASS
DELETE_SINGLE_TASK_OWNERSHIP=PASS

EXACT_SENTINEL_EQUALITY=PASS
BASELINE_SCAN_IDENTITY_ATOMICITY=PASS
POSTDELETE_UNRELATED_SAFE_AUTHORITY=PASS

SOURCE_AUTHORITY_GATE=PASS
REAL_TOPOLOGY_MATRIX=PASS
LOCAL_PRE_EFFECT_PATH_GATE=PASS
RECOVERY_JOURNAL_FAIL_CLOSED=PASS
SAFE_MARKER_ORACLE=PASS
UNRELATED_BASELINE_BOUNDS=PASS
UNRELATED_EXACT_IDENTITY=PASS
DYNAMIC_BUDGET_GATE=PASS
UNKNOWN_RPC_REJECTION=PASS
CONTROLLER_PATH_AUTHORITY=PASS
OFFICIAL_DELETE_OBSERVER=PASS
OFFICIAL_DELETE_UNKNOWN=PASS
SUCCESS_ONLY_SANITIZATION=PASS

STRUCTURAL_MATCHER=PASS
STRUCTURAL_MATCHER_ALLOW_CASES=13
STRUCTURAL_MATCHER_DENY_CASES=18

CONTINUATION_NEW_THREAD_PATH_PRESENT=NO
REAL_METHOD_GATE_DISABLED=PASS

EXPLICIT_REAL_FILE_TESTS=52
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

P7C6_REAL_CONTINUATION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO

Repair-3 adds finite primary/secondary/final task observations with explicit
owned-task state, preserves the same delete task after uncertainty, and
terminalizes sibling approval and terminal-waiter tasks on their failure
edges. The sentinel proof now requires safe metadata, stable descriptor and
pathname identity, exact length, exact read count and exact bytes. Baseline
entries retain the identity returned by the same descriptor-safe scan, and
post-delete reconciliation revalidates safe regular-file owner, mode, link
and pathname-component authority.

Behavioral fixtures cover normal completion, secondary convergence, delayed
cancellation convergence, finite final nonconvergence, no redispatch, Turn-4
approval cancellation, Turn-5 waiter cancellation after owned shutdown, and
single-task delete uncertainty. Synthetic sentinel fixtures cover exact,
prefix, suffix, newline, repeated, empty, same-length wrong, symlink,
hardlink, pathname-replacement and mutation cases. Synthetic baseline fixtures
cover scan-time pathname replacement and every required post-delete authority
mutation. No raw protected values, thread identifiers, marker plaintext,
prompts, commands, credentials, tokens or root-only recovery content are
stored here.
