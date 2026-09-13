# P7.C16 delete-chain authority successor preparation — architect acceptance — 2026-09-13

Status: **PREPARATION COMPLETE / ARCHITECT_ACCEPTED / REAL EXECUTION REQUIRES SEPARATE ONE-SHOT CONTRACT**

## Accepted executable authority

- executable source HEAD: `5fb8ed6c2a27da3149476ec8501c533152a19b8f`;
- executable source tree: `251ec8d3971460dafd57429112a357b1b53e9b50`;
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- P7.C16 preparation evidence blob: `aceb4474b66cc2bb6277b0ebe96f6d50ff99a2a4`;
- consumed P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The candidate is one linear commit ahead of exact Repair-2 base `aaccc8fddc4df763e7412524be85d83134f5bd64`, and only the P7.C16 successor launcher and P7.C16 preparation evidence changed. No `src/**`, consumed P7.C15 source/evidence, P7.C14/P7.C13/P7.C12 protected source, package marker, migration, deployment, Telegram, P8 or P9 path changed.

## Independent architect acceptance

Independent readback of the exact remote source accepts the complete successor preparation:

- exact P7.C15 root-cause reproduction of `controller_storage_mismatch` using real `SqliteStorage` and real `DeleteStorageCleanupCoordinator`;
- early controller-root authority retained for Codex runtime startup;
- late-bound exact current-run `controller_db_path` authority created only after the controller DB exists and matched to opened storage;
- real `DeleteStorageCleanupCoordinator` and real `DialogueDeleteService` remain the application delete chain; no fake-cleanup positive shortcut remains;
- cleanup-facing reserve/shutdown/recreate/profile operations delegate to the same underlying runtime manager and preserve its reservation-token ownership;
- explicit inherited engine profile identity is used consistently;
- protected P7.C15/P7.C14/P7.C13/P7.C12 blobs and both tracked package markers are source-gated by live hashes;
- repository-local import authority and clean tracked worktree/index are required before replay reservation;
- authenticated production Codex home is `/root/.codex_second`;
- installed Codex/version/schema authority is verified before default real runtime construction;
- default `p7c16_real_entrypoint()` selects `P7C16PreparedFutureExecutor.production(contract)` when no explicit test executor is supplied;
- production ordering remains source gate -> in-memory path plan -> distinct P7.C16 ledger reservation -> run parents -> root-only boot -> one owned child/watchdog -> root-only child result -> process-group gate -> terminal ledger mapping;
- real default child command is the P7.C16 module child with the exact current-run boot path;
- P7.C16 root-only ledger, boot and child-result authorities enforce bounded schema, root/private regular-file authority, nlink 1, no symlink, duplicate-key rejection, stable identity and source/run/boot correlation;
- production watchdog uses the frozen P7.C16 hard-deadline authority rather than short offline bounds;
- exact positive effect counts remain parent PASS authority;
- parent COMPLETED additionally requires valid PASS child, runtime-child quiescence, one child, zero retry and clean owned process-group facts;
- real-shaped runtime quiescence is derived from active `_runtimes`, `_starting` and `_unresolved` ownership maps rather than a fake-only property;
- late failure convergence uses the accepted owned bounded wait and the effective engine profile;
- successor-specific safe stage authority materially records `CONTROLLER_BINDING`, `DELETE_CLEANUP_AUTHORITY_CONFIRMED`, `DELETE_CHAIN_READY`, `THREAD_DELETE_DISPATCH`, `THREAD_DELETE_RESULT` and `APPLICATION_DELETE_RESULT` in actual reached order;
- known current-run controller-storage authority mismatch is retained as finite safe category `controller_storage_mismatch` with no raw path;
- the exact authorized synthetic handoff traversed the default source gate and default real entrypoint, selected the production executor exactly once, reserved only a temporary ledger, dispatched one owned child, executed the real cleanup coordinator and real delete service through fake external boundaries, and reached COMPLETED with zero real Codex effects.

The module-local `P7C16_TEST_ONLY_PRODUCTION_FACTORY` is `None` by default. Its preparation-only injection seam does not replace the frozen production default: the exact source explicitly selects `.production(contract)` whenever the test-only hook is absent. The executable source hash above binds that behavior for any later real run.

## Historical boundaries

P7.C15 remains permanently consumed `FAILED` and non-retryable. P7.C14 and P7.C13 remain permanently non-retryable. Their ledgers, retained evidence and historical material are not P7.C16 replay authority and must not be reset, cleaned or reused as current-run targets.

## One-shot status

`P7C16_PREP_ARCHITECT_ACCEPTED=YES`

`P7C16_PREP_COMPLETE=YES`

`P7C16_REAL_EXECUTION_AUTHORIZED_BY_THIS_DOCUMENT=NO`

A separate exact-source one-shot real execution contract is required. It must use a fresh out-of-band token, the distinct `/root/.codexcontrol/p7c16-one-shot.json` replay barrier, exact source/tree/blob authority above, pre-consumption source/import/installed/runtime-home checks and no retry after reservation.

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
