# P7.C17 post-delete oracle successor preparation contract — 2026-09-13

Status: **FROZEN / PREPARATION ONLY / ZERO REAL EFFECT / REAL EXECUTION NOT AUTHORIZED**

## Purpose

Prepare a new one-shot successor that preserves the accepted P7.C16 real lifecycle/delete chain while correcting the post-delete physical proof oracle that falsely rejected a successful delete because a fixed non-unique `TURN4_STIMULUS` string existed in unrelated retained persistent-session material.

This is not a P7.C16 retry. P7.C16, P7.C15, P7.C14 and P7.C13 remain permanently consumed/non-retryable.

## Binding forensic authority

- P7.C16 forensic evidence commit: `d0a7c7dbda94c28c2f6a0eb011453fb0692696de`;
- forensic tree: `61d6591879a66d93dc2f8959ba3a17b8470a34a7`;
- forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`;
- consumed P7.C16 real evidence commit: `fc1e6c3e65dd404edc8fb4dc45aeb95e8f4d400a`;
- consumed execution source: `5fb8ed6c2a27da3149476ec8501c533152a19b8f`;
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

## Proven root cause

`P7C16_ROOT_CAUSE=SHARED_PERSISTENT_ORACLE_NON_UNIQUE_STATIC_MARKER_FALSE_POSITIVE`

The P7.C16 persistent oracle counted a fixed common marker (`TURN4_STIMULUS`, `sleep 120`) across all regular files in the shared persistent session family. At least three occurrences existed in one unrelated retained session file. This single predicate was enough to make `post_delete_acceptance(...)` false even though official/application delete, tombstone, live binding, isolated descendants, runtime convergence, effect counts and process-group facts were clean.

## Required successor design

Create a thin P7.C17 successor under `tests/real` that composes the accepted P7.C16/P7.C15 lifecycle/delete chain and changes only the proof/oracle boundary needed to remove the false positive and retain complete sanitized oracle evidence.

Do not patch consumed P7.C16 source.

### Marker authority

For global persistent residual scanning, marker authority MUST contain only fresh current-run high-entropy/non-secret or run-unique values.

At minimum eligible markers:

- fresh `memory_marker`;
- fresh `response_marker`.

May also include when run-unique:

- exact fresh approval-target string/path;
- exact Turn-3 escalation prompt containing the fresh approval target.

Forbidden from global residual marker authority:

- `TURN4_STIMULUS` / `sleep 120`;
- fixed prompt fragments;
- fixed model/profile/server strings;
- any common static text that may appear in unrelated retained sessions.

The exact Turn-4 lifecycle stimulus remains unchanged for behavior testing. It is simply not a residual-identity marker.

### Marker tests

Preparation MUST prove:

1. an unrelated retained session containing `sleep 120` does not increase the P7.C17 current-run persistent marker residual count;
2. unrelated retained sessions containing generic Turn-3/Turn-4 wording do not count unless they contain an exact current-run high-entropy/run-unique marker;
3. a true residual file containing the fresh current-run memory marker fails;
4. a true residual containing the fresh response marker fails;
5. a residual containing the fresh approval-target or exact run-unique Turn-3 prompt fails if those markers are enabled;
6. markers from consumed P7.C16/P7.C15 historical runs do not satisfy fresh P7.C17 marker identity.

### Thread residual authority

Preserve independent thread residual checks. The successor must measure and retain sanitized:

- persistent thread_count;
- persistent thread_filename_count;
- persistent thread_directory_count;
- isolated thread_count.

Do not weaken thread-specific residual checks merely because marker semantics are corrected.

### Complete oracle-facts authority

Before the final `post_delete_acceptance(...)` decision, materialize a new root-only bounded P7.C17 oracle-facts authority containing only sanitized values/classes, sufficient to reconstruct the exact final predicate vector after any failure.

It must bind to exact source/run/boot authority and include at minimum:

- official delete class;
- application delete class;
- tombstone_bounded;
- live_binding_present boolean;
- post-delete schema version/class;
- isolation-envelope class;
- isolated sqlite regular/special/symlink/scan counts;
- isolated logs regular/special/symlink/scan counts;
- persistent thread_count;
- persistent thread_filename_count;
- persistent thread_directory_count;
- persistent marker_count;
- persistent scan_errors;
- isolated thread_count;
- isolated marker_count;
- isolated scan_errors;
- combined scan_errors;
- unrelated_target_specific_removal_detected;
- recovery class;
- budgets_ok;
- runtime-child-quiescent snapshot when available;
- exact marker-policy class/version;
- safe hashes/classes of enabled current-run marker authorities, never plaintext markers.

Write once or atomically update through an accepted root-only authority before final acceptance evaluation. No raw thread IDs, Turn IDs, marker plaintext, prompts, token or raw paths.

### Unrelated-removal authority

The P7.C16 forensic proved the historical boolean was not recoverable because pre-delete metadata was ephemeral.

P7.C17 must retain enough sanitized bounded pre-delete attribution state to replay the final unrelated-removal boolean without raw paths. Use hashed path identities and safe metadata classes/counts as needed.

The successor preparation must test the structurally possible false-positive class noted by P7.C16 forensic. Do not weaken unrelated-removal protection: truly unrelated removed regular files must still fail.

### Failure evidence

If the post-delete oracle rejects, the child result/stage authority must record a finite safe class and the root-only oracle-facts authority must make the exact false predicate set reconstructible without another inference-only forensic pass.

## Preserve accepted P7.C16 chain

Do not redesign accepted:

- source/package/import authority;
- authenticated `/root/.codex_second` home;
- installed Codex preflight;
- distinct one-shot parent/child/watchdog pattern;
- one model/list;
- Turn-1/Turn-2 memory proof;
- generation rebound;
- Turn-3 strict approval path;
- one response/ALLOW;
- Turn-4 active/interrupt path;
- schema-v4 controller binding;
- P7.C16 late-bound exact controller-storage authority;
- real `DeleteStorageCleanupCoordinator`;
- real `DialogueDeleteService`;
- independent official delete observation;
- UNKNOWN / CONFIRMED_PENDING terminal semantics;
- exact effect matrix;
- runtime-child and process-group convergence;
- root-only ledger/boot/child-result safety.

## Distinct P7.C17 authority

Define a distinct future P7.C17 gate/ledger/CLI namespace, including:

- `P7C17_FUTURE_REAL_GATE`;
- exact expected HEAD/tree/launcher/protected blobs/package markers;
- parent CLI `--p7c17-real-run`;
- child CLI `--p7c17-future-child` if required;
- replay barrier `/root/.codexcontrol/p7c17-one-shot.json`.

Preparation uses TEMP ledgers only. No real P7.C17 ledger may be created.

Ledger reservation must still precede all run-specific filesystem mutation.

## Production-shaped positive preparation

A mandatory full zero-real-effect handoff must traverse the default P7.C17 source gate and default real entrypoint into its production executor, owned child seam and composed lifecycle/delete chain through fake external boundaries, then:

- create unrelated retained session material containing fixed `sleep 120`;
- prove this unrelated static text is ignored by current-run marker authority;
- execute one canonical fake external delete through the real application delete service/coordinator;
- collect post-delete facts;
- persist the complete sanitized oracle-facts authority;
- evaluate the corrected final oracle;
- obtain child PASS;
- satisfy exact effect matrix;
- obtain temp ledger COMPLETED and parent exit projection 0.

The positive path must use the real corrected oracle implementation, not a hard-coded PASS or monkeypatched acceptance result.

## Required negative matrix

At minimum:

1. unrelated historical `sleep 120` only -> PASS eligibility;
2. unrelated fixed generic prompt text only -> PASS eligibility;
3. fresh current-run memory marker residual -> FAIL;
4. fresh current-run response marker residual -> FAIL;
5. current-run run-unique Turn-3/approval marker residual -> FAIL when enabled;
6. persistent thread residual -> FAIL;
7. persistent filename residual -> FAIL;
8. persistent directory residual -> FAIL;
9. isolated residual -> FAIL;
10. scan error -> FAIL;
11. invalid isolation envelope -> FAIL;
12. unrelated removed file -> FAIL;
13. DELETE_UNKNOWN -> UNKNOWN / no retry;
14. CONFIRMED_PENDING_STORAGE -> CONFIRMED_PENDING / no second delete;
15. exact effect under/over-count -> parent not COMPLETED;
16. malformed/missing oracle-facts authority -> parent not COMPLETED;
17. oracle-facts source/run mismatch -> parent not COMPLETED;
18. failure after facts collection proves exact failed-predicate set is recoverable;
19. consumed P7.C16/P7.C15 historical markers do not match fresh P7.C17 marker policy;
20. second child/delete/retry remains forbidden.

## File scope

Allowed tracked changes only:

- `tests/real/test_p7_c17_final_hard_delete_successor.py`;
- `docs/evidence/p7c17/P7C17_POST_DELETE_ORACLE_SUCCESSOR_PREP_EVIDENCE_2026-09-13.md`;
- optional one P7.C17-only helper under `tests/real` if strictly necessary.

Forbidden:

- `src/**`;
- P7.C16/P7.C15/P7.C14/P7.C13/P7.C12 source modification;
- historical evidence modification;
- package marker modification;
- migrations/deployment/Telegram/P8/P9.

## Zero-real-effect preparation

During preparation:

- real Codex/app-server starts = 0;
- real model/thread/turn/approval/interrupt/delete RPCs = 0;
- real P7.C17 ledger creations = 0;
- historical ledger mutations = 0;
- persistent-home mutations = 0;
- consumed retained cleanup = 0;
- process signals = 0;
- Telegram = 0.

## Validation

Required:

- focused P7.C17 suite;
- P7.C16 root-cause reproduction fixture proving old policy fails on unrelated `sleep 120`;
- corrected marker-policy matrix;
- complete oracle-facts authority safety/correlation tests;
- unrelated-removal retained-attribution tests;
- full default-entrypoint production-shaped handoff;
- P7.C16/P7.C15/P7.C14/P7.C13 offline regressions where safe;
- P7.C12 focused;
- relevant P7.C2-P7.C5 non-real regressions;
- complete non-real pytest with real gates unset;
- unittest discovery with real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check;
- gate-disabled P7.C17 smoke exits disabled without ledger/run/process effects.

Historical consumed-latch failures must be reported separately and not repaired here.

## Evidence requirements

Preparation evidence must bind exact base/forensic authorities and final launcher/evidence/helper blobs and report:

- old static-marker false-positive reproduction;
- corrected fresh-marker policy;
- unrelated `sleep 120` immunity;
- true fresh-marker residual rejection;
- complete oracle-facts persistence proof;
- exact failed-predicate reconstruction test;
- unrelated-removal replay authority;
- full production-shaped handoff counts;
- zero-real-effect accounting;
- validation totals.

End with:

`P7C17_PREP_STATIC_MARKER_FALSE_POSITIVE_REPRODUCED=PASS|FAIL`

`P7C17_PREP_CURRENT_RUN_MARKER_POLICY=PASS|FAIL`

`P7C17_PREP_UNRELATED_STATIC_TEXT_IMMUNITY=PASS|FAIL`

`P7C17_PREP_TRUE_MARKER_RESIDUAL_REJECTION=PASS|FAIL`

`P7C17_PREP_COMPLETE_ORACLE_FACTS_AUTHORITY=PASS|FAIL`

`P7C17_PREP_UNRELATED_REMOVAL_REPLAY_AUTHORITY=PASS|FAIL`

`P7C17_PREP_DEFAULT_ENTRYPOINT_FULL_HANDOFF=PASS|FAIL`

`P7C17_PREP_READY=YES|NO`

`P7C17_REAL_EXECUTION_AUTHORIZED=NO`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Use preparation branch `prep-p7-c17-post-delete-oracle-successor-2026-09-13`, based exactly on forensic evidence commit `d0a7c7dbda94c28c2f6a0eb011453fb0692696de`.

No rebase. No force. Only allowed P7.C17 preparation files may be added/changed. Stop after remote readback for independent architect review.
