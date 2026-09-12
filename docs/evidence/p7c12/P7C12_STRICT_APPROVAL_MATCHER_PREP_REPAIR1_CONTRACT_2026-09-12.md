# P7.C12 strict approval matcher preparation — Repair-1 contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / GOLDEN-REPLAY AUTHORITY REPAIR ONLY**

## Base candidate

Repair applies to candidate HEAD:

`4d57b95650c972d26baa33c51f80a85a70b17564`

with matcher blob:

`00ba41a13ad492179989d97c7b5dc59f671b4883`

Architect review authority:

`docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_ARCHITECT_REVIEW_2026-09-12.md`

## Scope

Repair only the retained P7.C11 golden-replay authority and evidence overclaims identified by architect review.

No real Codex effect is authorized.

No production `src/**` change is authorized.

Historical P7.C6–P7.C11 files remain immutable.

## Required repair

1. Retained replay must use RecoveryJournal request observation as independent request-side authority, not reconstruct both request and wire sides from `wire-command-recovery.json`.
2. Require exactly one `APPROVAL_REQUEST_1_OBSERVED` (or the exact authoritative ordinal) with:
   - exact request count/ordinal;
   - kind `command_execution`;
   - `thread_match=true`;
   - `turn_match=true`;
   - `cwd_match=true`;
   - journal `wire_command_sha256` equal to the root-only wire command SHA;
   - the accepted sentinel-reference class for the consumed observation.
3. Require one exact correlated `DENY_RESPONSE_n_DISPATCH_INTENT` and one later `DENY_RESPONSE_n_RESULT=DENIED_CONFIRMED` for the same request ordinal/attempt.
4. Root-only wire remains independent wire-side authority. Validate it with the accepted C11 reader.
5. Candidate target plaintext may be reconstructed only in private memory from the validated wire grammar. Require exactly one candidate.
6. Require candidate target SHA equality with every available retained target authority:
   - wire `expected_sentinel_path_sha256`;
   - child/result `target_sentinel_path_sha256`;
   - parent/global target SHA authority (`parent_target_sentinel_path_sha256` where present).
7. Do not publish raw target/wire/thread/Turn/cwd.
8. Remove the free-form invented `correlation_key` from authority semantics, or replace it with a deterministic binding derived only from independently established retained fields. A caller-selected identical string cannot be used as proof of correlation.
9. Add offline negative tests that individually corrupt:
   - journal wire SHA;
   - journal request kind;
   - journal request ordinal/count;
   - journal thread-match flag;
   - journal Turn-match flag;
   - journal cwd-match flag;
   - DENY request ordinal/attempt/result;
   - child target SHA;
   - parent target SHA;
   - wire target SHA;
   and prove no retained golden MATCH can be established.
10. Preserve all existing strict command negative tests and synthetic exact-command positives.

## Evidence

Update only the P7.C12 evidence as necessary and record:

- repair commit/blob authority;
- independent journal-to-wire SHA binding result;
- independent request identity-match flag result;
- DENY chronology binding result;
- wire/child/parent target SHA agreement result;
- negative authority-corruption matrix count/result;
- corrected focused/subtest counts;
- non-real regression;
- compileall/diff check/leakage scan;
- zero-real-effect accounting.

Required final lines:

`P7C12_REPAIR1_REQUEST_WIRE_INDEPENDENT_BINDING=PASS|FAIL`

`P7C12_REPAIR1_TARGET_MULTI_AUTHORITY_BINDING=PASS|FAIL`

`P7C12_REPAIR1_GOLDEN_REPLAY=PASS|FAIL`

`P7C12_MATCHER_OFFLINE_PROOF=PASS|FAIL`

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Use a Repair-1 branch based on exact candidate HEAD `4d57b95650c972d26baa33c51f80a85a70b17564`.

No force push. After publication, architect independently reviews the complete candidate+repair range.
