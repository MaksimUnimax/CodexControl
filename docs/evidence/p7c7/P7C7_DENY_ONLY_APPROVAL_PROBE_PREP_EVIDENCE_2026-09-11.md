# P7.C7 deny-only approval-probe preparation evidence — 2026-09-11

Status: **ZERO-REAL-EFFECT / PREPARATION-ONLY / REAL PROBE DISABLED**

This evidence records the offline preparation result. It does not authorize a
fresh thread, an app-server runtime, an approval response, an interrupt, a
delete, or any P7.C6 recovery action.

ARCHITECT_BASE_SHA=7e0654bbc9e2798ea49e16eca3aa6e2d90d1592a
ARCHITECT_BASE_TREE=e3281cc5dd5a0a06e92e5f87feb340a679cffcf2
ACCEPTED_P7C7_AUTHORITY_EVIDENCE=e00392fbff6894e1857eb4c8f1e1937a88ca1e96
UPSTREAM_TAG=rust-v0.144.6
UPSTREAM_RELEASE_COMMIT=5d1fbf26c43abc65a203928b2e31561cb039e06d
REAL_EFFECTS_DURING_PREP=0

DENY_ONLY_OPERATOR=PASS
ALLOW_DECISION_PATHS=0
APPROVAL_TERMINAL_CONCURRENT_RACE=PASS
TERMINAL_FIRST_FINITE=PASS
APPROVAL_FIRST_DENIED=PASS
SIMULTANEOUS_RACE_FINITE=PASS
MULTIPLE_REQUEST_DENY_BOUND=PASS
MAX_PROBE_APPROVAL_REQUESTS=3

RAW_WIRE_ROOT_ONLY_AUTHORITY=PASS
RAW_WIRE_EXCLUSIVE_CREATE=PASS
RAW_WIRE_BOUNDED_READER=PASS
SHLEX_VECTOR_RECONSTRUCTION=PASS
SANITIZED_RESULT_EXCLUDES_RAW_COMMAND=PASS
FRESH_RUN_BOUNDARY=PASS
BOUNDARY_MUTATION_CHECK=PASS
PROCESS_GROUP_WATCHDOG=PASS
UNRELATED_PROCESS_SURVIVAL=PASS
PROBE_ONE_SHOT_LATCH=PASS
P7C6_PATH_REUSE=NO
REAL_METHOD_GATE_DISABLED=PASS

The preparation uses the production `CodexApprovalBridge` and production
`ApprovalRequest` projection. Every synthetic normalized request is captured
with finite sequence, kind, thread, turn, cwd, request-count and
response-count metadata. Raw wire text is used only in memory and in a
temporary root-only synthetic recovery record. The persisted result schema
contains hashes, bounded structural labels and counters only.

The candidate prompt is dynamic and run-owned: sleep exactly 30 seconds, then
touch exactly one outside-workdir sentinel. It explicitly forbids alternatives
and retries after denial and makes no approval guarantee. The future turn ID is
represented by a value resolved only after start confirmation; unresolved or
mismatched identity remains DENY.

Approval and exact-turn terminal waiters are created together after the
future start-confirmation boundary. The offline matrix covers terminal-first,
approval-first, same-tick ambiguity, protocol terminal, bounded observer
nonconvergence and successful task joining. No approval request is required for
a finite terminal result. The three-request drain is DENY-only and has no
fourth response path.

The future run layout is materialized only under temporary test roots with
root-owned 0700 directories and 0600 authority files. The real one-shot latch
path under `/root/.codexcontrol` was not created. The future call budget is
model/list=1, thread/start=1, resume=0, primary turn/start=1, delete/read/list=0,
and allow responses=0; this budget is not executed in preparation.

The synthetic watchdog starts one child with a new session, verifies
PID=PGID=SID, bounds group observation, permits at most one group termination
and one group kill, requires quiescence on normal exit, and leaves a separate
synthetic session alive.

EXPLICIT_PROBE_FILE_TESTS=29
EXPLICIT_PROBE_FILE_SKIPPED=1
EXPLICIT_PROBE_FILE_FAILURES=0
EXPLICIT_PROBE_FILE_ERRORS=0

FOCUSED_TESTS=88
FOCUSED_FAILURES=0
FOCUSED_ERRORS=0

FULL_TESTS=1065
FULL_FAILURES=0
FULL_ERRORS=0

PRODUCTION_SOURCE_CHANGED=NO
P7C6_REAL_RERUN_PERFORMED=NO
P7C7_REAL_THREAD_CREATED=NO
P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO
P7C7_REAL_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO

No raw thread ID, Turn ID, command, sentinel path, prompt, model response,
credential, token, or session content is included in this evidence.
