# P7.C12 Repair-2 contract — independent child capture binding — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / NARROW PROOF REPAIR ONLY**

## Base candidate

Repair-2 starts from exact Repair-1 candidate:

`a2281b3839c4dcb7f85218e95034510c25c80956`

Matcher grammar accepted in Repair-1 must not be weakened or redesigned.

## Required correction

Before retained matcher inputs are projected, require the accepted P7.C11 sanitized child result to independently agree with journal and wire authority.

Require all of:

1. `authoritative_command_capture_established is True`;
2. child `authoritative_command_request_ordinal` equals the unique journal request ordinal;
3. child `authoritative_command_local_sequence` equals wire `local_request_sequence`;
4. child `authoritative_command_kind == command_execution` and agrees with journal/wire kind;
5. child `authoritative_command_thread_match is True`;
6. child `authoritative_command_turn_match is True`;
7. child `authoritative_command_cwd_match is True`;
8. child `authoritative_command_wire_sha256` equals the journal request wire SHA and root-only wire SHA;
9. child `authoritative_command_deny_status == DENIED_CONFIRMED`;
10. existing journal DENY chronology remains independently valid.

Only after these gates pass may wire identity hashes and local sequence be projected into `CapturedRequest`, `ExpectedAuthority`, and `CorrelatedWireRecord`.

## Negative matrix additions

Add fail-closed cases for at least:

- child capture established = false;
- child request ordinal wrong;
- child local sequence wrong;
- child kind wrong;
- child thread-match false;
- child Turn-match false;
- child cwd-match false;
- child authoritative wire SHA wrong;
- child DENY status RESPONSE_UNKNOWN / not confirmed.

Every corruption must fail before matcher MATCH.

## Existing accepted proof to preserve

Preserve without weakening:

- exact command grammar;
- journal request uniqueness/kind/identity flags;
- journal↔wire SHA binding;
- DENY chronology;
- target SHA binding across wire/child/parent;
- 16-case Repair-1 independent-authority matrix;
- retained C11 golden replay;
- zero-real-effect/security boundary.

## Scope

Allowed changes only:

- `tests/real/test_p7_c12_strict_approval_matcher.py`;
- `docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, historical P7.C6-P7.C11, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP changes.

## Required evidence lines

`P7C12_REPAIR2_CHILD_CAPTURE_BINDING=PASS|FAIL`

`P7C12_REPAIR2_LOCAL_SEQUENCE_BINDING=PASS|FAIL`

`P7C12_REPAIR2_CHILD_WIRE_SHA_BINDING=PASS|FAIL`

`P7C12_REPAIR2_CHILD_DENY_STATUS_BINDING=PASS|FAIL`

`P7C12_REPAIR2_GOLDEN_REPLAY=PASS|FAIL`

`P7C12_MATCHER_OFFLINE_PROOF=PASS|FAIL`

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.

## Publication

Use a new Repair-2 branch from exact candidate `a2281b3839c4dcb7f85218e95034510c25c80956`, commit clearly, push normally, and prove remote readback. No force push.
