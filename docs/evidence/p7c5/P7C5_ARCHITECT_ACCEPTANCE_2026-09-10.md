# P7.C5 architect acceptance — 2026-09-10

Status: **ARCHITECT_ACCEPTED**

Repository: `MaksimUnimax/CodexControl`

## Accepted lineage

- corrected architect base: `44dcb874659940998734fdfe76fb8683250be05d`
- corrected architect base tree: `471bae46bf36592a7502298b863d8774f04cb013`
- corrected proof candidate: `d963a4982382d28a90ed18ac9d6384ba424f7dc0`
- architect proof-review correction: `29448176312d47a51b7b321a6268398eff724c4a`
- final proof repair / accepted P7.C5 implementation: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`
- accepted P7.C5 tree: `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`

Historical stopped proof `581a31e9a450230eed50bad6c247159898d72f7f` remains rejected historical evidence. Its marker-only failure was an architect-contract defect, not a P7.C4 production defect.

## Independent architect review

The accepted base-to-head C5 diff contains only:

- `tests/acceptance/test_p7_c5_fake_hard_delete_acceptance.py`;
- `docs/evidence/p7c5/P7C5_FAKE_HARD_DELETE_ACCEPTANCE_EVIDENCE.md`;
- architect-owned `docs/evidence/p7c5/P7C5_ARCHITECT_REVIEW_CORRECTION_2026-09-10.md`.

No `src/**`, configuration, ADR, deployment or Telegram code changed.

The corrected harness preserves the accepted P7.C4 production contract: `PersistentProfileResidualScanner` remains exact-thread-only. A separate test-only marker oracle measures synthetic marker residuals without widening production attribution logic. Marker-only dirty fixtures are rejected by the acceptance oracle, while exact-thread and exact-thread-plus-marker persistent residuals correctly block confirmed finalization.

## Accepted confirmed-delete proof

The fake confirmed path models the upstream effect before local cleanup: a fake P1 delete seam removes only the target-owned persistent session artifact and returns `DELETE_CONFIRMED`. The accepted application path then persists `DELETE_CONFIRMED_PENDING_STORAGE`, reserves the exact profile, shuts down/reaps, proves quiescence, empties isolated `sqlite/**` and `logs/**`, runs the production exact-thread persistent gate, calls `finalize_confirmed()` once, creates the exact tombstone and releases the reservation.

The isolated storage matrix included state main/WAL/SHM, log DB main/WAL/SHM, configured text logs, nested cache/temp/other files and multiple nested descendants. The ownership envelope remained intact and all isolated payload descendants were removed.

Exact target thread residuals in sessions content, sessions filename, sessions directory and history content blocked finalization. Exact-thread-plus-marker variants also blocked. Scanner failure classes remained fail-closed.

## Accepted DELETE_UNKNOWN proof

`DELETE_UNKNOWN` remains official UNKNOWN. Local isolated containment may complete and create the exact schema-v4 containment row, but dialogue state/version/raw binding remain retained, persistent session/history material is not manually removed, tombstone/finalizer calls remain zero and the profile stays quarantined.

Same-process and fresh-process replay/quarantine semantics remain covered by the accepted C4/C5 matrices.

## Crash, concurrency and cancellation proof

C5 exercised retryable interruption during both `sqlite/` and `logs/` descendant clearing and confirmed that a fresh manager can resume local cleanup without an external delete replay.

The accepted predecessor and C5 matrices cover pre-finalizer failures, committed-finalizer exception/malformed-return handling, post-commit reservation-release failure, concurrent confirmed cleanup, concurrent UNKNOWN containment and caller cancellation after owned work begins.

`DialogueDeleteService` confirmed-pending and UNKNOWN replay invoke fake `thread/delete` zero times. The final proof repair also executes `DialogueRecoveryService.recover_startup()` on independent `DELETING`, `DELETE_CONFIRMED_PENDING_STORAGE` and `DELETE_UNKNOWN` fixtures. The recovery service has no P1 lifecycle port; all three paths are local-only.

## Controller and unrelated-baseline proof

The final proof correctly treats the actual controller SQLite as mutable durable authority, not a byte-for-byte immutable baseline. Across isolated-root cleanup it remains the exact bound file (`st_dev`/`st_ino` unchanged), remains open/readable with schema v4, and contains the expected durable transition/tombstone/containment state.

Confirmed-success proof places an unrelated session artifact inside `CODEX_HOME/sessions/**` and unrelated history bytes in `history.jsonl`; the fake upstream delete removes only the target session. The unrelated session and history bytes remain unchanged through local cleanup/finalization. Repository, parent/sibling and auth/config synthetic baselines are also preserved.

## Schema and security authority

Schema remains v4. Historical v1/v2/v3 hashes remain unchanged. V4 migration remains `0004_delete_local_containment` with SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.

No real Codex version process, app-server, business RPC, thread/delete/read/list call, Telegram call, credential content read/copy/symlink or production storage/process mutation occurred in C5.

The final executor report records:

- dedicated C5 tests: `15`;
- focused tests: `248`, zero skipped/failures/errors;
- full ordinary regression: `1065`, zero skipped/failures/errors.

The dynamic mount/namespace test remains `NOT_RUN__SAFETY_BOUNDARY`; no privileged host mount mutation was performed. This bounded environment risk is carried into P7.C6/P13 and must not be silently treated as tested.

## Acceptance consequence

P7.C5 is complete. **P7.C6 is the sole next executable slice.**

P7.C6 is a separately authorized, one-shot real Codex acceptance. It must use a genuinely CodexControl-dedicated authenticated persistent profile home plus a fresh distinct isolated state root and synthetic controller DB. It may create exactly one new disposable thread and issue exactly one official `thread/delete`. It must never touch or reconcile the historical rejected P7 thread.

P8/P9 remain blocked until P7.C6 is independently architect accepted.
