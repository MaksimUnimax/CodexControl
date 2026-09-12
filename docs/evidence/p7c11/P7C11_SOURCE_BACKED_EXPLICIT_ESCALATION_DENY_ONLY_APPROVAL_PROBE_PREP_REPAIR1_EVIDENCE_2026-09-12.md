# P7.C11 source-backed explicit-escalation DENY-only approval-probe preparation Repair-1 evidence — 2026-09-12

Status: **ZERO REAL EFFECT / REPAIR-1 IMPLEMENTED / REAL P7.C11 NOT AUTHORIZED**

## Repository gate

REPOSITORY=/opt/codex-control
ORIGIN_MAIN_SHA=960daa87c83b00c5bb86b0504d59c799dec268db
ORIGIN_MAIN_TREE=9dc3875d46f6561698de6a17f708d28ea71bcaa3
BRANCH=impl-p7-c11-source-backed-explicit-escalation-deny-only-prep-repair1-2026-09-12
WORKTREE_START_CLEAN=YES
NO_REBASE=YES
NO_FORCE=YES

## Scope

PRODUCTION_SOURCE_CHANGED=NO
P7C7_P7C8_P7C9_P7C10_HARNESS_CHANGED=NO
P7C7_P7C8_P7C9_P7C10_EVIDENCE_CHANGED=NO
CURRENT_WORK_CHANGED=NO
ROADMAP_CHANGED=NO
REAL_P7C11_EXECUTED=NO

The source-backed stimulus remains unchanged in semantic authority:

UPSTREAM_CODEX_RELEASE_COMMIT=5d1fbf26c43abc65a203928b2e31561cb039e06d
TARGET_LOCATION_CLASS=OUTSIDE_DEFAULT_WORKSPACE_WRITABLE_ROOTS
TARGET_FILENAME_GRAMMAR=^\.codexcontrol-p7c11-escalation-probe-[0-9a-f]{32}$
TARGET_PARENT=DIRECT_CHILD_OF_/root
TARGET_PRECREATED=NO
PROMPT_OPERATION=touch_<exact-external-target>
PROMPT_FIRST_AND_ONLY_TOOL_CALL=YES
PROMPT_REQUIRE_ESCALATED=YES
PROMPT_DEFAULT_SANDBOX_FIRST_ATTEMPT_FORBIDDEN=YES
PROMPT_ALTERNATE_TOOL_PATH_NETWORK_RETRY_FORBIDDEN=YES

## Repair-1 authority changes

- Root-only `wire-command-recovery.json` remains immutable first-capture authority.
- Exactly one in-memory `ApprovalCapture` must match its local request sequence, command kind, exact thread/Turn/cwd identity and wire SHA-256.
- Safe child fields now expose authoritative capture status, request ordinal, local sequence, kind, identity flags, target-reference class, wire SHA-256 and authoritative DENY status.
- DENY journal intent/result records carry `request_count`; authoritative status requires the exact request chronology:
  `APPROVAL_REQUEST_k_OBSERVED < DENY_RESPONSE_n_DISPATCH_INTENT < DENY_RESPONSE_n_RESULT`.
- `RESPONSE_UNKNOWN`, missing correlation, duplicate correlation and a DENY for another request cannot become preferred command-approval success.
- The preferred class requires exact target-token authority, established vector reconstruction, confirmed DENY for that request, zero ALLOW, terminalized owners and absent target.
- Parent final authority independently hashes its selected target and requires equality with the child hash; the exact parent target is re-observed absent.
- Finite observational classes cover zero requests, missing authoritative capture, unknown DENY status, nonexact target reference, non-command DENY and target creation.

## Verification

FOCUSED_COMMAND=`PYTHONPATH=src python -m pytest -q tests/real/test_p7_c11_deny_only_approval_probe.py`
FOCUSED_RESULT=150_PASSED_1_SKIPPED_186_SUBTESTS

NONREAL_COMMAND=`PYTHONPATH=src python -m pytest -q tests/unit tests/integration tests/acceptance tests/test_foundation.py`
NONREAL_RESULT=1065_PASSED_2_WARNINGS

STATIC_CHECKS=`PYTHONPATH=src python -m py_compile tests/real/test_p7_c11_deny_only_approval_probe.py; git diff --check`
STATIC_CHECKS_RESULT=PASS

The complete repository command was also attempted. Its only failures were the unchanged historical P7.C7, P7.C8, P7.C9 and P7.C10 static checks finding their pre-existing consumed-probe latch files under `/root/.codexcontrol`; those files were not created, deleted or modified by Repair-1.

## Zero-effect boundary

REAL_CODEX_PROCESS_STARTS=0
REAL_APP_SERVER_STARTS=0
MODEL_LIST_CALLS=0
THREAD_START_CALLS=0
TURN_START_CALLS=0
APPROVAL_RESPONSES=0
THREAD_RESUME_CALLS=0
INTERRUPT_CALLS=0
THREAD_DELETE_CALLS=0
THREAD_READ_CALLS=0
THREAD_LIST_CALLS=0
TELEGRAM_CALLS=0
PROCESS_SIGNAL_CALLS_TO_REAL_CODEX=0
REAL_P7C11_TARGET_CREATION=0

AUTHORIZED_P7C11_DENY_ONLY_APPROVAL_PROBE_2026_09_12=UNSET
CODEXCONTROL_P7C11_PROBE_EXPECTED_HEAD=UNSET
CODEXCONTROL_P7C11_PROBE_EXPECTED_TREE=UNSET

P7C11_LATCH_ABSENT=YES
P7C11_RESULT_ABSENT=YES
P7C11_OUTCOME_ABSENT=YES

P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO
P7C11_REAL_EXECUTION_AUTHORIZED=NO
P7C11_MATCHER_AUTHORIZED=NO
P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO
