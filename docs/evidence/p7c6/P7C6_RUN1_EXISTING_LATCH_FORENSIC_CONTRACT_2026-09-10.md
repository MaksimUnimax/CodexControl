# P7.C6 Run-1 existing latch forensic contract — 2026-09-10

Status: **FROZEN / ZERO-REAL-EFFECT / READ-ONLY LATCH FORENSIC**

## Context

The accepted same-thread continuation preparation contract required materialization of `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` using an exact new safe format. The preparation correctly stopped because that path already exists, is root-owned and mode `0600`, but its content does not exactly match the newly frozen format. Overwrite is forbidden.

The exact byte format is not itself the historical Run-1 replay barrier. The rejected Run-1 harness checks only whether `ONE_SHOT_LEDGER` exists and is non-empty before refusing a repeated Run-1 invocation. Therefore an already-existing safe CodexControl latch may be semantically sufficient even if its representation predates the new preparation format. Conversely, a root-owned `0600` file at the path must not be assumed to be ours merely because it is non-empty.

This contract resolves only that ambiguity. It does not authorize continuation preparation beyond the latch gate and performs no Codex effect.

## Absolute zero-real-effect boundary

This forensic must perform zero:

- Codex/app-server process starts;
- `model/list`;
- `thread/start`;
- `thread/resume`;
- `turn/start`;
- approval responses;
- interrupts;
- `thread/delete`;
- `thread/read`;
- `thread/list`;
- Telegram calls;
- process signals/termination;
- mutation of the existing latch, recovery ledger, marker supplement, persistent home, isolated state, or controller DB.

All real authorization environment variables remain unset.

## File authority to inspect

Exact path:

`/root/.codexcontrol/p7c6-real-one-shot-ledger.json`

The forensic must open it read-only with no-follow semantics and first prove:

- parent `/root/.codexcontrol` is an actual directory, root-owned, non-symlink, mode `0700`;
- latch is a regular file, root-owned, non-symlink, mode `0600`;
- `st_nlink == 1`;
- file identity `(st_dev, st_ino)` is stable across the bounded read;
- size is non-zero and bounded to at most 16384 bytes;
- no path/inode substitution is observed.

Any failure yields `RUN1_EXISTING_LATCH_FORENSIC=UNSAFE_OR_AMBIGUOUS` and no further interpretation.

## Content confidentiality

The content may be read only to classify the latch. Do not print, log, commit, quote or expose the raw file or any unapproved value.

Git evidence may contain:

- file SHA-256;
- byte length;
- UTF-8 yes/no;
- JSON-object yes/no;
- exact JSON key names only, if valid JSON and key names themselves pass the safe-key grammar below;
- finite value classifications;
- booleans for matching known public authorities.

Never persist:

- raw thread IDs;
- marker plaintext;
- prompts/responses/commands;
- credentials/tokens;
- arbitrary unknown string values;
- environment dumps;
- recovery-ledger content.

## Safe JSON-key grammar

If the file is JSON, key names may be reported only when every key is an ASCII identifier matching `[A-Za-z0-9_.-]{1,64}`. Otherwise report `LATCH_KEYS=UNSAFE_OR_UNREPORTABLE` and do not emit key text.

Nested structures are allowed for forensic classification but their raw values must never be emitted. Report only top-level key names and finite type/classes.

## Known-authority comparisons

Without exposing raw values, compare any scalar values present against these public/safe authorities where type-compatible:

- Run-1 architect base: `32153c3d63bf6b45a8b16478566997c09e8e0cac`;
- Run-1 evidence commit: `785a82e2e9bc392173ea1e910b490f84cfa590b2`;
- retained target thread SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`;
- accepted Turn-3 forensic commit: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.

For every known authority report only whether an exact scalar match appears anywhere in the parsed object:

- `MATCH_RUN1_ARCHITECT_BASE=YES|NO`;
- `MATCH_RUN1_EVIDENCE_COMMIT=YES|NO`;
- `MATCH_RETAINED_THREAD_SHA256=YES|NO`;
- `MATCH_TURN3_FORENSIC_COMMIT=YES|NO`.

Do not report other scalar values.

## Status semantic classification

If a top-level key semantically named `status`, `state`, `result`, `disposition`, `phase` or equivalent exists, classify its string value without quoting it into exactly one of:

- `CONSUMED_OR_NO_RERUN` — clearly denotes consumed/completed/rejected/failed/aborted/recovery-only and prevents a fresh Run-1 attempt;
- `IN_PROGRESS` — denotes an in-progress/armed/started authority;
- `EMPTY_OR_UNUSED` — denotes unused/available/not-started;
- `UNKNOWN_SAFE_STRING` — safe bounded string but semantics not proven;
- `NOT_PRESENT`;
- `UNSAFE_OR_UNPARSEABLE`.

This classification is observational only. It does not itself establish acceptance.

## Secret-risk classification

Inspect key names and value shapes for obvious forbidden secret-bearing classes without exposing values.

Report counts only:

- `RAW_THREAD_ID_LIKE_VALUE_COUNT` — values structurally matching a raw thread identifier where distinguishable from the known 64-hex SHA;
- `MARKER_PLAINTEXT_LIKE_VALUE_COUNT` — strings matching known C6 marker prefixes (`C6_RESPONSE_`, `C6_MEMORY_`, `C6_INTERRUPT_`) or continuation marker prefixes;
- `TOKEN_OR_CREDENTIAL_KEY_COUNT` — key names containing obvious credential/token/password/secret/auth-material semantics;
- `ABSOLUTE_PATH_VALUE_COUNT` — absolute path strings;
- `UNKNOWN_LONG_STRING_COUNT` — strings over 512 characters not equal to known public authorities.

If any credential/token/secret-bearing value is plausibly present, report `LATCH_CONTENT_SAFETY=SECRET_RISK` and do not create Git evidence containing any raw value.

Absolute paths alone are not secret, but their raw values must not be emitted.

## Replay-barrier proof

Independently prove against the published Run-1 harness logic that the existing file, as currently present, causes the historical Run-1 one-shot precondition to reject a new Run-1 invocation solely because the file exists and is non-empty.

Do this statically/offline; do not execute the real harness with authorization set.

Report:

`RUN1_HISTORICAL_HARNESS_BLOCKED_BY_EXISTING_LATCH=YES|NO`.

## Final forensic classification

Return one of:

### `SAFE_REPLAY_BARRIER_CANDIDATE`
Only if:

- filesystem authority is safe;
- file is non-empty;
- content read succeeds without substitution;
- no secret-risk class is detected;
- historical harness is definitely blocked by the file;
- content is valid bounded UTF-8/JSON or another safely classifiable finite representation.

This classification means only that architect may consider the existing file as the Run-1 consumed latch. It does not authorize prep continuation.

### `SAFE_BUT_SEMANTICALLY_UNKNOWN`
Use when filesystem/content safety passes and replay blocking is proven, but content cannot be attributed/understood enough to adopt as CodexControl authority.

### `UNSAFE_OR_AMBIGUOUS`
Use for unsafe filesystem authority, secret risk, substitution, unbounded/unparseable content that cannot be safely classified, empty file, or inability to prove replay blocking.

## Evidence

Create only:

`docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_FORENSIC_EVIDENCE_2026-09-10.md`

The evidence must contain no raw latch values beyond explicitly allowed public hashes/commit SHAs and safe key names.

## Repository scope

Allowed normal change: the single evidence file above.

Do not change:

- `src/**`;
- real harnesses;
- ADRs;
- `CURRENT_WORK`/`ROADMAP`/`DECISIONS`;
- configuration/deployment.

## Acceptance consequence

For every result:

`P7C6_SAME_THREAD_PREP_CONTINUATION_AUTHORIZED=NO`.

Only architect review may decide whether the existing file satisfies the Run-1 global latch requirement or whether the prep remains blocked.
