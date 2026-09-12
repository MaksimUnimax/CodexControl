# P7.C12 strict approval matcher preparation — architect review — 2026-09-12

Status: **REWORK_REQUIRED / MATCHER CORE ACCEPTABLE / RETAINED GOLDEN-REPLAY AUTHORITY CIRCULAR**

## Reviewed lineage

- Frozen architect base: `38829736cf91cb4f5375c597e8a011675c796e19`, tree `397c576011b456225f7130600e489020e711b690`.
- Candidate commit 1: `ea8cb182b88dc0954364fc8514c89f61ff001992` (`prepare P7.C12 strict approval matcher`).
- Candidate commit 2 / HEAD: `4d57b95650c972d26baa33c51f80a85a70b17564` (`correct P7.C12 matcher evidence counts`).
- Matcher blob: `00ba41a13ad492179989d97c7b5dc59f671b4883`.
- Evidence blob: `ea50fab6b08f00386ffc9bbf52e7cad0016cf2f1`.

Independent remote comparison proves the candidate is exactly two linear commits above the frozen base and changes only:

- `tests/real/test_p7_c12_strict_approval_matcher.py`;
- `docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, historical P7.C6–P7.C11 test/evidence, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP path changed in the candidate.

## Matcher-core review

The test-only matcher itself is structurally fail-closed and no architect blocker was found in its command grammar:

- finite result enum only;
- no protocol response path;
- no subprocess/filesystem/network operation reachable from the matcher;
- exact `COMMAND_EXECUTION` kind;
- exact request ordinal/local sequence and identity equality;
- exactly one wire record;
- command SHA binding across expected/request/wire objects;
- canonical `shlex` round trip;
- vector length exactly 3;
- token 0 exactly `/bin/bash`;
- token 1 exactly `-lc`;
- token 2 exactly literal `touch <expected-target>`;
- one exact target occurrence;
- exact two-token inner lexical result;
- alternate shells/options/whitespace/quoting/wrappers/compound commands/redirects/substitution/expansion/wildcards/retries/equivalent executables fail closed.

The synthetic positive/negative matrix is consistent with the frozen P7.C12 grammar.

## Architect blocker — circular retained golden replay

The retained C11 golden replay does not independently construct request-side authority.

`_retained_c11_authority()` reads the root-only wire record, then uses that same wire record to populate both sides of several matcher comparisons:

- request local sequence comes from wire;
- request thread SHA comes from wire;
- request Turn SHA comes from wire;
- request cwd SHA comes from wire;
- request command SHA comes from wire;
- wire object is populated from the same wire values;
- `correlation_key` is a newly invented constant copied identically into expected/request/wire objects rather than a retained C11 authority.

The RecoveryJournal is read, but the replay uses it only to establish that one request event and one confirmed DENY result exist. It does not use the journal request record's independently durable `wire_command_sha256`, `kind`, `thread_match`, `turn_match`, `cwd_match`, and sentinel-reference class to bind the projected request to the root-only wire.

This is material because the accepted P7.C11 journal schema intentionally stores those sanitized request-side correlation facts. A golden replay must fail if the journal request observation and wire authority disagree; the current projection can manufacture agreement by taking both matcher sides from wire.

Accordingly the evidence claim:

`RETAINED_C11_REQUEST_WIRE_CORRELATION=PASS`

is not sufficiently established by the committed golden replay.

## Architect blocker — target binding claim is over-stated

The replay reads the child result but does not use the child's independently durable target SHA in matcher preparation or a pre-match gate.

Instead it extracts the target plaintext from the wire command itself and checks that target against the wire record's own expected-target SHA. That proves internal wire consistency, not the full retained C11 target binding claimed in evidence.

The accepted C11 forensic established independent wire/child/parent target-SHA agreement. P7.C12 golden replay must preserve that authority by requiring the extracted candidate target SHA to equal all available independent retained target SHA authorities, at minimum:

- wire `expected_sentinel_path_sha256`;
- child/result `target_sentinel_path_sha256`;
- parent/global result target SHA authority (`parent_target_sentinel_path_sha256` where present).

The current code reads `child` but does not make this comparison. Therefore:

`RETAINED_C11_TARGET_SHA_BINDING=PASS`

is over-claimed by the current executable proof.

## Repair boundary

P7.C12 is not redesigned. Repair-1 must be narrow and zero-effect.

Required correction:

1. Keep the accepted strict command grammar unless a minimal change is needed to remove non-authoritative correlation input.
2. Golden replay must locate exactly one C11 request record and use the RecoveryJournal request record as independent request-side authority for request ordinal/count, kind, durable wire-command SHA and the stored thread/Turn/cwd match facts.
3. The root-only wire remains the independent wire-side authority. Journal wire SHA must equal root-only wire SHA before MATCH can be attempted.
4. Require journal `thread_match=true`, `turn_match=true`, `cwd_match=true` before projecting any identity hashes from the wire into matcher objects.
5. Require the exact correlated `DENIED_CONFIRMED` chronology for that same request ordinal.
6. Extract the one candidate target plaintext only in private memory, then require its SHA to equal the wire, child/result and parent/global target SHA authorities. Do not publish plaintext.
7. The currently free-form synthetic `correlation_key` must not be treated as retained authority. Remove it from the matcher authority model or replace it with a deterministic binding composed solely from established request/wire authorities. An invented identical string on both sides is not correlation proof.
8. Add negative golden-replay-style tests showing that mutating independently supplied journal wire SHA, journal kind/ordinal/match flags, child target SHA, parent target SHA, or wire target SHA blocks the retained-authority projection / MATCH.
9. Correct the evidence claims and counts after executable proof.

## Effect boundary

Repair-1 remains offline/test-only:

- real Codex/app-server starts = 0;
- model/thread/turn RPC = 0;
- approval responses = 0;
- ALLOW = 0;
- DENY = 0;
- target mutation = 0;
- retained authority mutation = 0;
- historical latch mutation = 0;
- `src/**` changes = 0.

## Verdict

`P7C12_ARCHITECT_VERDICT=REWORK_REQUIRED`

`P7C12_MATCHER_CORE_BLOCKER=NO`

`P7C12_GOLDEN_REPLAY_AUTHORITY_BLOCKER=YES`

`P7C12_EVIDENCE_OVERCLAIM_BLOCKER=YES`

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
