# P7.C12 strict approval matcher construction — zero-effect preparation contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / MATCHER CONSTRUCTION ONLY / NO REAL ALLOW / NO HARD DELETE**

## Purpose

P7.C11 established, from one consumed real request plus retained-wire forensic, that exact Codex 0.144.6 emitted one authoritative `COMMAND_EXECUTION` approval request whose canonical command representation was:

- vector length exactly `3`;
- outer token 0 class `BASH_ABSOLUTE` and exact retained token SHA-256 corresponding to `/bin/bash`;
- outer token 1 exactly `-lc`;
- outer token 2 exactly one script containing exactly `touch <the expected external target>`;
- no second command, control operator, redirect, expansion/substitution, wildcard or retry;
- exact thread/Turn/cwd identity correlation;
- exact target SHA agreement across wire, child/result and parent;
- one correlated `DENIED_CONFIRMED` and `ALLOW=0`;
- target absent.

P7.C12 converts that accepted representation authority into a reusable **test-only, fail-closed approval matcher** and proves it offline.

P7.C12 does not execute Codex and does not itself authorize any future ALLOW or hard delete.

## Architect base

Executor must fetch current `origin/main` and use the exact main HEAD named in the architect execution prompt as branch base.

The accepted P7.C11 forensic authorities are:

- forensic commit `5f1bef2045dd526e22f9b3fb24d42c9f4827962a`;
- evidence blob `4e56f592f99f16182169b0fb6ec68f304b506be5`;
- architect acceptance file `docs/evidence/p7c11/P7C11_CONSUMED_REAL_EXPLICIT_ESCALATION_RETAINED_WIRE_FORENSIC_ARCHITECT_ACCEPTANCE_2026-09-12.md`.

Consumed P7.C11 executable authority remains immutable:

- HEAD `be98542b9bcbf99508784f229057698d85784367`;
- tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`;
- harness blob `fc67299d80c3d617280975182c097a92cb863b92`.

## Absolute effect boundary

During P7.C12:

- real Codex process starts = 0;
- app-server starts = 0;
- model/list = 0;
- thread/start/resume/read/list/delete = 0;
- turn/start/interrupt = 0;
- approval responses = 0;
- ALLOW responses = 0;
- DENY responses = 0;
- Telegram = 0;
- process signals = 0;
- target filesystem mutation = 0;
- retained P7.C7-P7.C11 authority mutation = 0;
- retained SQLite writes/checkpoints/VACUUM/migrations = 0.

Do not create any authorization environment variable for a real probe.

Do not execute any historical consumed real test.

## Implementation boundary

P7.C12 is test-only.

Allowed implementation scope:

- one new P7.C12 test/preparation module under `tests/real/`;
- optionally one new test-only helper module under `tests/real/` if the executor proves the helper is needed to avoid copying matcher logic;
- one P7.C12 evidence file under `docs/evidence/p7c12/`.

Production `src/**` changes are forbidden.

Historical P7.C6-P7.C11 test files are immutable and must not be edited.

ADR, deployment, Telegram and production configuration changes are forbidden.

## Matcher inputs

The matcher must operate only on explicit expected authority supplied by its caller and on one correlated captured request/wire record.

At minimum the caller must provide:

- expected profile identity or profile binding where applicable;
- expected thread identity/hash authority;
- expected Turn identity/hash authority;
- expected cwd identity/hash authority;
- expected exact target string in private in-memory form;
- expected request ordinal/local sequence;
- the correlated wire record for that exact request.

Raw target/thread/Turn/cwd values must never be emitted into evidence or assertion messages.

## Exact positive matcher grammar

The matcher may return MATCH only when **all** of the following are true:

1. request kind is exactly `COMMAND_EXECUTION`;
2. request ordinal/local sequence equals the expected owned request;
3. request thread identity equals the expected thread authority;
4. request Turn identity equals the expected Turn authority;
5. request cwd identity equals the expected cwd authority;
6. exactly one correlated wire record exists for the same request;
7. wire/request identity hashes agree;
8. canonical wire command reconstruction succeeds through `shlex` round-trip authority;
9. vector length is exactly `3`;
10. outer token 0 is exactly `/bin/bash`;
11. outer token 1 is exactly `-lc`;
12. outer token 2 is exactly the literal string `touch <expected-target>`;
13. the expected target is one semantic shell token after `touch`;
14. there are exactly two inner semantic tokens;
15. candidate-target occurrence count is exactly `1`;
16. candidate target equals the exact expected target, not merely a prefix/suffix/substring;
17. no leading or trailing extra command text exists;
18. no newline exists;
19. no semicolon exists;
20. no `&&` or `||` exists;
21. no pipe exists;
22. no redirect exists;
23. no command substitution exists;
24. no variable expansion exists;
25. no wildcard exists;
26. no retry or second command exists;
27. wire-command SHA-256 is bound to the request capture and stable for the matcher invocation.

The matcher must not accept an alternate semantic representation merely because it would produce the same filesystem effect.

The observed representation is the authority.

## Required finite matcher result classes

Use a finite result enum or equivalent closed classification.

At minimum distinguish:

- `MATCH_EXACT_P7_APPROVAL_COMMAND`;
- `NO_MATCH_KIND`;
- `NO_MATCH_REQUEST_IDENTITY`;
- `NO_MATCH_WIRE_AUTHORITY`;
- `NO_MATCH_VECTOR`;
- `NO_MATCH_SHELL_EXECUTABLE`;
- `NO_MATCH_SHELL_OPTION`;
- `NO_MATCH_INNER_COMMAND`;
- `NO_MATCH_TARGET`;
- `NO_MATCH_EXTRA_OPERATION`;
- `NO_MATCH_AMBIGUOUS_OR_MULTIPLE`.

Malformed input must fail closed to a finite no-match class or a bounded test-only validation exception; it must never become MATCH.

## Negative matrix

Offline tests must prove rejection of at least:

- request kind other than COMMAND_EXECUTION;
- wrong request ordinal;
- wrong local sequence;
- wrong thread;
- wrong Turn;
- wrong cwd;
- missing wire authority;
- multiple candidate wire records;
- wire hash mismatch;
- malformed shlex command;
- vector length 0, 1, 2, 4+;
- `bash` PATH lookup instead of exact `/bin/bash`;
- `/usr/bin/bash`;
- `/bin/sh`;
- `/bin/zsh`;
- `/bin/bash -c`;
- `/bin/bash --`;
- exact target as an outer argv token instead of the accepted inner-script representation;
- `touch` with no target;
- `touch` with a different target;
- target prefix;
- target suffix;
- target embedded inside a larger token;
- two target occurrences;
- leading whitespace before the script;
- trailing whitespace after the script;
- doubled/interposed shell whitespace that breaks exact literal equality;
- quoted or escaped alternate target spelling;
- extra positional argument;
- newline;
- semicolon;
- `&&`;
- `||`;
- pipe;
- stdout/stderr redirect;
- command substitution;
- variable expansion;
- wildcard/glob;
- `env`, `sudo`, `command`, `exec`, `timeout` or another wrapper;
- a second `touch`;
- retry loop;
- equivalent filesystem operation through another executable.

Tests must explicitly prove substring matching cannot produce MATCH.

## Positive matrix

At minimum prove:

1. one synthetic exact request + exact wire vector `/bin/bash`, `-lc`, exact `touch <target>` => MATCH;
2. the same semantic representation reconstructed through the accepted `shlex` round-trip => MATCH;
3. repeated pure matcher invocation is deterministic and side-effect free;
4. changing any single identity or command component causes no-match.

## Retained P7.C11 golden replay

As a zero-real-effect executor-only proof, read the already-retained P7.C11 root-only wire authority with the accepted bounded/no-follow parser and run it through the newly constructed matcher in memory.

Requirements:

- no Codex process/RPC;
- no approval response;
- no target mutation;
- no retained file mutation;
- no raw wire/target/thread/Turn/cwd publication.

Required evidence result:

`P7C11_RETAINED_WIRE_GOLDEN_MATCH=MATCH_EXACT_P7_APPROVAL_COMMAND`

If the retained authoritative request cannot be matched exactly by the new matcher, P7.C12 fails.

## Decision boundary

The P7.C12 matcher returns only classification.

It must not itself send an approval decision.

It must not contain a real-execution gate.

It must not implement an operator that automatically ALLOWs a live request.

Synthetic unit tests may assert how a later caller could branch on the finite matcher result, but no live protocol response is permitted in P7.C12.

## Security boundary

Committed test/evidence material must contain zero:

- raw retained wire command;
- raw retained target path;
- raw retained thread ID;
- raw retained Turn ID;
- raw retained cwd;
- prompt/model output;
- credentials/tokens/auth values;
- raw root-only JSON.

Synthetic fixture paths/IDs are permitted only when obviously synthetic and not copied from retained authorities.

Safe hashes, finite classes and counts are permitted.

## Required evidence

Create:

`docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_EVIDENCE_2026-09-12.md`

It must include at minimum:

- architect base SHA/tree;
- accepted P7.C11 forensic commit/blob;
- changed-file list;
- matcher implementation blob SHA;
- helper blob SHA if a helper is used;
- positive test count/result;
- negative test count/result;
- exact-shell/option/inner-command gates;
- identity-correlation gates;
- substring/compound-command rejection proof;
- malformed-input fail-closed proof;
- retained P7.C11 golden replay result;
- leakage scan result;
- focused suite result;
- complete non-real regression result;
- historical consumed-latch test handling without deletion/rewriting;
- zero-real-effect accounting.

Required final lines:

`P7C12_MATCHER_CONSTRUCTED=YES|NO`

`P7C12_MATCHER_OFFLINE_PROOF=PASS|FAIL`

`P7C12_RETAINED_C11_GOLDEN_REPLAY=PASS|FAIL`

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Validation

Run focused pure/offline matcher tests.

Run the complete non-real regression suite.

Historical static tests whose sole failure is the intentional presence of consumed P7.C7-P7.C11 one-shot latch files must not be made green by deleting or rewriting those authorities. Report them separately if repository-wide collection includes them.

Run `compileall` and `git diff --check`.

Do not execute any consumed real test.

## Publication

Use a new implementation/preparation branch from the exact architect main named in the execution prompt.

Commit matcher/test implementation and P7.C12 evidence with clear material commits. No force push.

Remote readback must prove:

- branch lineage from exact architect base;
- only allowed test-only/evidence paths changed;
- no `src/**` change;
- no historical P7.C6-P7.C11 mutation;
- no main mutation by the executor.

## Acceptance consequence

Successful P7.C12 executor output does not itself authorize any real effect.

After executor publication, an independent architect review must decide whether the matcher is accepted.

Only a later architect-owned contract may authorize a fresh one-shot real successor and any real ALLOW/hard-delete action.

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
