# P7.C4 architect acceptance — 2026-09-10

Status: **ARCHITECT_ACCEPTED**

Repository: `MaksimUnimax/CodexControl`

## Accepted lineage

- architect base: `7572df1e95e79f3292489b096e8b0a22789df1e5`
- architect base tree: `2584147b1bd8190cccee9907876abe9034f66005`
- initial P7.C4 candidate: `70cdf0edc3f319c0254313eabc5d3c56c2f9ef16`
- first architect repair: `fe646af1487d13571337e605641ecc86dbb1f6c7`
- second architect repair / accepted implementation: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`
- accepted implementation tree: `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`

## Independent architect review

P7.C4 was not accepted from executor test counts alone. The complete three-commit candidate was independently read back from GitHub and reviewed against ADR-0043, ADR-0044, the accepted P7.C2/P7.C3 boundaries, and the frozen P7.C4 execution contract.

The initial candidate established the correct broad architecture but was rejected for five issues: C4 recovery outcomes were collapsed by `StrEnum` aliases; a committed confirmed finalizer could later be reported as pending after a post-commit read failure; schema-v4 open validation did not reject containment/tombstone or containment/active-job contradictions; the persistent scanner did not revalidate the opened regular-file descriptor before content reads; and the executor evidence overclaimed crash/restart/concurrency coverage not yet materialized by committed tests.

The first repair corrected those issues by introducing distinct recovery values, exact post-finalizer tombstone reconciliation, truthful post-commit reservation-release failure handling, v4 collision gates, opened-FD scanner identity/ownership/mode checks, and deterministic concurrency/cancellation tests.

A second independent review then found two production authority gaps plus one proof gap. First, the accepted C3 recreation primitive cleared the entire isolated root, including the ownership marker and top-level `sqlite/` and `logs/` directories, creating a crash interval in which a fresh process could no longer prove ownership and resume local cleanup. Second, the C4 coordinator did not prove that its actual `SqliteStorage` controller database was the same controller path protected by the runtime isolation authority. Third, several failure/restart/scanner/replay claims still lacked executable proof.

The second repair closes those gaps. The content-free ownership envelope now survives local containment: `.codexcontrol-state-root-v1`, `sqlite/`, and `logs/` remain in place while all descendants beneath `sqlite/` and `logs/` are descriptor-relatively removed. This means a process crash during descendant clearing leaves an ownership-valid, retryable isolated root. A fresh manager/reservation can safely repeat local containment with no P1 effect. The C4 coordinator now requires the actual controller `SqliteStorage` database path to equal the exact protected `controller_db_path` before it can reserve or recreate a profile root. Normal C4 tests use one actual controller database rather than a dummy protected file.

The second repair also reconciles malformed post-commit finalizer returns against the exact committed tombstone, rejects scanned hard-linked regular files before reading them, and adds focused failure/restart/scanner tests. No remaining production C4 blocker was found.

## Accepted schema-v4 authority

Current CodexControl storage schema is **v4**.

Historical schema-v1/v2/v3 statement constants, canonical SQL and hashes remain immutable.

The sole v4 migration remains:

- migration ID: `0004_delete_local_containment`
- migration SHA-256: `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`

The v4 table `delete_storage_containment` stores only bounded metadata for a live canonical `DELETE_UNKNOWN` dialogue. It records the exact profile, dialogue version, SHA-256 of the retained thread identity, `OFFICIAL_DELETE_AUTHORITY=UNKNOWN`, `LOCAL_ISOLATED_STORAGE_CONTAINMENT=COMPLETED`, and the containment timestamp. It does not store raw thread identity or conversation content.

A containment row never changes the dialogue state/version/binding, never creates a deletion tombstone, and never authorizes `finalize_confirmed()`. V4 open/recovery authority rejects malformed, orphaned, mismatched, tombstone-colliding and active-job-colliding containment shapes.

## Accepted confirmed cleanup authority

For a live `DELETE_CONFIRMED_PENDING_STORAGE` dialogue, local cleanup is:

`reserve -> shutdown/reap -> quiescence -> isolated payload reset -> persistent sessions/history exact-thread scan -> finalize_confirmed -> release`

The isolated payload reset is descriptor bounded and empties every descendant beneath `sqlite/` and `logs/` while retaining and revalidating the content-free ownership envelope. Any pre-finalizer failure retains the live confirmed-pending binding, creates no tombstone, and keeps the profile reservation quarantined for that process.

The persistent scanner reads only `CODEX_HOME/sessions/**` and optional `CODEX_HOME/history.jsonl`; it never reads `auth.json` or arbitrary configuration. It follows no symlinks, rejects unsafe ownership/modes/special files/hard links, binds pre-open and post-open file identity, enforces finite limits, handles chunk-boundary matches, and reports aggregate counters only.

Once the accepted transactional finalizer has committed an exact tombstone, local deletion truth never regresses to pending. Exact post-commit reconciliation may use only controller-local storage and the retained pre-finalization binding. A reservation-release failure after commit is reported as a finalized outcome with a finite safe release failure and retains quarantine rather than resurrecting the dialogue.

## Accepted DELETE_UNKNOWN authority

`DELETE_UNKNOWN` remains the immutable official external authority. There is no retry of `thread/delete`, no `thread/read`, no `thread/list`, no notification inference and no local promotion to confirmed/deleted.

C4 may reserve the exact profile, stop/reap the local runtime, prove quiescence, reset the isolated payload root and record the separate durable containment fact. The dialogue and raw binding remain retained; no tombstone/finalizer is permitted. The profile reservation remains held as process-local quarantine. A fresh process with an existing containment record must re-establish reservation/quiescence and local root containment before treating the profile as quarantined; the historical row is not permission to resume work.

## Recovery and concurrency

C4 recovery outcomes are distinct: confirmed finalized, confirmed storage pending, UNKNOWN contained and UNKNOWN containment pending are not enum aliases.

Pre-existing `DELETING` becomes durable `DELETE_UNKNOWN` before any local containment and performs zero external delete replay. Pre-existing confirmed-pending and UNKNOWN states run local-only recovery. Owned cleanup tasks coalesce concurrent callers and shield already-owned work from caller cancellation so quarantine/finalization ownership cannot be lost through an outer cancellation.

## Regression and effect evidence

The final executor report records:

- full ordinary regression: `1050` tests;
- skipped: `0`;
- failures: `0`;
- errors: `0`;
- real Codex version processes: `0`;
- real app-server starts/business RPCs: `0`;
- real thread-delete/read/list calls: `0`;
- Telegram calls: `0`;
- real Codex home/state-root/storage mutation: `0`;
- credential content reads/copies/symlinks: `0`;
- production process mutation: `0`.

GitHub remote readback independently confirmed the final repair is exactly one commit `df161566cab5f8fa7ccf70f94379c78a9fb02ffe` on top of `fe646af1487d13571337e605641ecc86dbb1f6c7`, and the full P7.C4 implementation is exactly three commits ahead of the frozen architect base.

No real P7 acceptance experiment occurred in P7.C4.

## Acceptance consequence

P7.C4 is complete. **P7.C5 is the sole next executable slice.**

P7.C5 is proof-only corrected fake hard-delete acceptance over the complete C2/C3/C4 architecture. It must independently exercise the full marker/path-family, crash/restart, unrelated-baseline, duplicate-effect and quarantine matrices. Granular proof permutations not required to establish production C4 correctness are explicitly carried into the frozen C5 acceptance contract rather than silently discarded.

P7.C6 remains blocked until P7.C5 is architect accepted. P8 and P9 remain blocked until P7.C6 is architect accepted.