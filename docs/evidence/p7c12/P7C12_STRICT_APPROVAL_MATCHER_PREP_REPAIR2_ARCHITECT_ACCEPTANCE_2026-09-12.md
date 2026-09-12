# P7.C12 Repair-2 architect acceptance — 2026-09-12

Status: **ARCHITECT_ACCEPTED / P7.C12 COMPLETE / ZERO REAL EFFECT**

## Accepted candidate

- Repair-2 base: `a2281b3839c4dcb7f85218e95034510c25c80956`.
- Repair-2 implementation: `1aea99f173b51d20b3f6e0c893d9c7e2bd71bb60`.
- Repair-2 evidence correction / final candidate: `a5c66a778800d1c5ee5811d97d961fe0dccd677c`.
- Final tree: `e6a46445d11d660a50891eabf412b01aef883fca`.
- Final matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.
- Final evidence blob: `5c854e09d5ef3c22941c7927cd20a8777b0216e8`.

The base-to-head lineage is linear, two commits, and changes only:

- `tests/real/test_p7_c12_strict_approval_matcher.py`;
- `docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, historical P7.C6-P7.C11, ADR, deployment, Telegram, controller schema, CURRENT_WORK or ROADMAP change is part of Repair-2.

## Accepted matcher grammar

`strict_p7c12_match()` remains pure, test-only and classification-only. It cannot send an approval response or execute a command.

MATCH is fail-closed on all accepted dimensions:

- request kind exactly `COMMAND_EXECUTION`;
- exact request ordinal and exact local sequence;
- exact thread / Turn / cwd authority;
- exactly one correlated wire record;
- stable command SHA equality across expected/request/wire;
- canonical `shlex` round trip;
- exactly three outer tokens;
- exact `/bin/bash`;
- exact `-lc`;
- exact literal inner script `touch <expected-target>`;
- exactly one target occurrence;
- exactly two inner semantic tokens;
- no alternate shell representation, substring match, wrapper, compound command, redirect, substitution, expansion, wildcard, retry, second command or equivalent executable.

## Accepted independent retained-authority proof

Repair-1 removed the synthetic free-form `correlation_key` and established independent RecoveryJournal -> root-only wire -> child/parent target binding.

Repair-2 closes the final residual local-sequence/capture gap before matcher projection. The accepted projection now requires the sanitized child result to independently establish and agree on:

- `authoritative_command_capture_established=True`;
- request ordinal;
- local sequence;
- command kind;
- thread/Turn/cwd match flags;
- authoritative wire SHA;
- `DENIED_CONFIRMED` status.

Those child facts must agree with the unique RecoveryJournal request and root-only wire before wire identity hashes, local sequence or command SHA are projected into matcher inputs.

The existing journal request uniqueness, journal->wire SHA equality, exact DENY chronology, target SHA binding across wire/child/parent, and parent-final authority remain required.

## Negative authority matrix

Accepted matrices:

- Repair-1 independent-authority corruption matrix: `16/16` fail closed before MATCH;
- Repair-2 child-capture corruption matrix: `12/12` fail closed before MATCH;
- command/identity negative matrix remains fail closed, including substring, compound, redirect, expansion, wrapper, retry and alternate executable variants.

## Retained golden replay

The consumed P7.C11 retained authority is independently reconciled from:

- RecoveryJournal request/chronology;
- root-only wire authority;
- sanitized child result;
- global parent result;
- global parent outcome.

Only after reconciliation does the pure matcher receive projected inputs.

Accepted result:

`P7C11_RETAINED_WIRE_GOLDEN_MATCH=MATCH_EXACT_P7_APPROVAL_COMMAND`

`P7C12_REPAIR2_CHILD_CAPTURE_BINDING=PASS`

`P7C12_REPAIR2_LOCAL_SEQUENCE_BINDING=PASS`

`P7C12_REPAIR2_CHILD_WIRE_SHA_BINDING=PASS`

`P7C12_REPAIR2_CHILD_DENY_STATUS_BINDING=PASS`

`P7C12_REPAIR2_GOLDEN_REPLAY=PASS`

## Validation authority

Final reported validation:

- focused P7.C12: `13 passed`, `79` subtests;
- complete non-real regression: `1776 passed`, `7 skipped`, `6 deselected` historical consumed-latch/static checks;
- compileall: PASS;
- `git diff --check`: PASS;
- leakage scan: PASS;
- real Codex/app-server/RPC/approval/delete effects: `0`.

Historical consumed latches remain intact and were not deleted or rewritten.

## Verdict and consequence

P7.C12 is **COMPLETE / ARCHITECT ACCEPTED**.

This acceptance proves only a strict test-only matcher and its retained-authority projection. It does not itself authorize a real ALLOW, a real approval response, a real thread effect, or hard delete.

The next slice is **P7.C13 zero-effect preparation** for a fresh final hard-delete acceptance harness. P7.C13 preparation must separate the approval proof from the interrupt proof: the accepted matcher authorizes only the exact observed `touch <target>` representation, while the interrupt proof must use a separately bounded long-running turn and must not weaken the approval matcher.

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C13_PREPARATION_AUTHORIZED=YES_ZERO_EFFECT_ONLY`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked pending independently architect-accepted real hard-delete acceptance.
