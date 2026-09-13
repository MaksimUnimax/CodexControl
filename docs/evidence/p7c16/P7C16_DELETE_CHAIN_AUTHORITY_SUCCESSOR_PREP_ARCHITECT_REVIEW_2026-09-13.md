# P7.C16 delete-chain authority successor preparation — architect review — 2026-09-13

Status: **REWORK_REQUIRED / ROOT-CAUSE CORRECTION ACCEPTED / REAL-EXECUTABLE SUCCESSOR NOT PREPARED / ZERO REAL EFFECT**

## Candidate reviewed

- candidate HEAD: `4f477e313192350414b1c157b6e1789135d11600`;
- candidate tree: `67a5276b34481ae3d118cbcb09dd73d2a6224973`;
- exact base: `3744cb19fba8ecba53d163b9e77f7adc9a213e6c`;
- base tree: `2fd391fb6fff9c3e84bda7d3640155677a42f070`;
- P7.C16 launcher blob: `d336fd46a0e78cd77c4ab4558f99f70ce3d0b2ab`;
- P7.C16 evidence blob: `3bbcd3e2a70c4f6b1105723554c0b932fa42a010`.

Lineage/scope are accepted: one linear commit over the P7.C15 real-evidence head, and only the new P7.C16 successor launcher and P7.C16 preparation evidence were added. No `src/**`, consumed P7.C15 source/evidence, P7.C14/P7.C13/P7.C12 protected source, package marker, migration, deployment, Telegram, P8 or P9 path changed.

## Accepted P7.C16 material

The following preparation results are accepted for reuse:

- exact offline reproduction of the consumed P7.C15 `ValueError("controller_storage_mismatch")` using real `SqliteStorage` and real `DeleteStorageCleanupCoordinator`;
- the architectural requirement that early Codex runtime uses controller-root authority while local cleanup receives a late-bound exact controller DB path only after the DB exists;
- `P7C16LateBoundControllerRuntimeView.bind_exact()` validates a fresh exact controller path and storage-path agreement;
- production-shaped child tests route the P7.C15 lifecycle flow through real `DeleteStorageCleanupCoordinator` and real `DialogueDeleteService` rather than the former `_P7C15FakeStorageCleanup` shortcut;
- current-run `p7c16-*` namespace isolation and retained historical P7.C15/P7.C14 non-cleanup intent;
- zero-real-effect execution boundary.

These results correctly target the P7.C15 root cause.

## Blocker A — incorrect protected P7.C13 harness authority

The candidate hard-codes:

`P7C16_P7C13_HARNESS=5a1fe8e32d18600fcf7ace6b9aa24067238d6dec7`

This is not the accepted P7.C13 harness blob. The frozen protected authority is:

`5a1fe8e32cd985b1e1845d73266211632e33950c`

The preparation evidence repeats the incorrect value. A future source gate using the candidate would therefore bind the wrong historical executable authority.

Repair must correct the constant/evidence and independently hash the actual protected file at source-gate time.

## Blocker B — package/import authority is incomplete

The frozen P7.C16 contract required the source bundle to bind the tracked package markers:

- `tests/__init__.py` = `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` = `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The candidate `P7C16SourceAuthority` / `P7C16ArchitectContract` omit both. Import authority is reduced to a `PYTHONPATH` string equality rather than the accepted repository-origin proof used by P7.C15.

Repair must add both marker blobs, environment fields, exact file hashing and repository-local import origin checks.

## Blocker C — runtime reservation/recreate ownership is simulated in the facade

The frozen contract required cleanup reservation semantics to remain owned by the same underlying runtime manager.

The candidate instead implements its own `_P7C16Reservation`, local `reserve()/release()`, synthetic `RuntimeQuiescenceProof`, and direct `IsolatedStateRoot._recreate_bound()` call.

This does **not** preserve the real `CodexRuntimeManager` reservation token, lock ownership or `recreate_isolated_state_root()` authority. The underlying manager is unaware of the reservation.

Repair must delegate:

- `reserve()` to the underlying manager;
- reservation release through the returned underlying reservation;
- `shutdown_profile()` to the underlying manager;
- `recreate_isolated_state_root()` to the underlying manager with that same underlying reservation token;
- `profile()` to the underlying manager.

The late-bound facade may override only the cleanup-facing exact `isolation_authority`; it must not simulate runtime ownership.

## Blocker D — late-failure convergence uses the wrong profile identity

The composed frozen P7.C15 engine performs runtime acquire/resume/delete-generation operations under `p7c15.P7C15_PROFILE_ID`.

The P7.C16 exception convergence path calls:

`manager.shutdown_profile(P7C16_PROFILE_ID)`

Against a real underlying `CodexRuntimeManager` this profile is not the acquired profile and can fail as `unknown_profile`, recreating the observed non-quiescent failure class.

Repair must bind one explicit effective engine profile identity and use that same identity for acquire/resume/cleanup/convergence. If the thin successor continues to reuse the frozen P7.C15 engine, the effective runtime profile is the frozen P7.C15 profile and the P7.C16 boot/evidence must not pretend otherwise.

## Blocker E — future P7.C16 parent does not launch a child

`p7c16_real_entrypoint()` defaults to:

`P7C16PreparedFutureExecutor(P7C16DurableOneShotLedger(P7C16_LEDGER_PATH))`

with `child=None`.

`P7C16PreparedFutureExecutor.run()` reserves the ledger, creates boot authority and then synthesizes a local `FAILED` result when `child is None`. It does not:

- spawn `/usr/bin/python -m tests.real.test_p7_c16_final_hard_delete_successor --p7c16-future-child`;
- use `OwnedParentChildWatchdog`;
- validate a root-only child result produced by a subprocess;
- observe process-group active/zombie/scan facts;
- apply a real hard deadline.

A future authorized P7.C16 invocation would therefore consume the new ledger and fail without exercising the successor child.

Repair must materialize the actual parent -> boot -> one owned child -> validated result -> terminal ledger path, reusing the accepted P7.C15 watchdog/containment authority where appropriate.

## Blocker F — parent exit projection is not implemented

`_module_main(--p7c16-real-run)` returns `1` after any normally returned executor result. It has no PASS/UNKNOWN/CONFIRMED_PENDING/TIMEOUT terminal projection.

Repair must provide the same finite semantics as the accepted P7.C15 parent:

- disabled/source-gate failure: exit `2`;
- completed valid PASS: exit `0`;
- executed FAILED/UNKNOWN/CONFIRMED_PENDING/TIMEOUT: nonzero.

## Blocker G — future production Codex home is wrong

The current executor builds production boot with:

`codex_home=<ledger-parent>/p7c16-home`

For the real replay barrier this would resolve under `/root/.codexcontrol`, not the authenticated persistent Codex home.

The inherited P7.C15 runtime routing requires the accepted persistent home:

`/root/.codex_second`

A real child using the candidate boot would fail the shared persistent-home authority before useful execution or lack the authenticated state.

Production P7.C16 boot must use the accepted `/root/.codex_second`. Temporary tests may use an explicit isolated fake-home seam only when no real Codex runtime is constructed.

## Blocker H — boot/result/ledger authorities are weaker than accepted one-shot authority

The candidate P7.C16 boot/result/ledger helpers lack several accepted P7.C15 protections:

- read paths do not prove root ownership/private mode/nlink/no-symlink/stable identity;
- child result is not bound to source HEAD/tree/launcher/run hash/boot authority;
- ledger terminal update uses direct `write_text()` and lacks the accepted safe identity/terminal-state validation;
- no parent validates exact effect counts and watchdog/process-group facts before `COMPLETED`.

A distinct successor ledger does not justify weakening the already accepted one-shot containment model.

Repair must adapt/reuse P7.C15 root-only safe-file and terminal-mapping semantics for P7.C16.

## Blocker I — installed runtime preflight is missing from the future child

`p7c16_future_child_main()` directly constructs the production child. Unlike accepted P7.C15, it does not verify installed Codex/version/schema authority before runtime construction on the default production path.

Repair must restore the accepted installed runtime authority check before any real runtime/app-server start.

## Test-gap explanation

The six focused tests validate component behavior but not the future executable parent path. The positive handoff calls `p7c16_future_child_main()` directly with a fake runtime boundary. It therefore does not exercise:

- exact real source gate + default production executor;
- durable P7.C16 replay barrier through an owned subprocess;
- real production boot persistent-home authority;
- installed runtime preflight;
- parent watchdog/result/exit mapping;
- true underlying `CodexRuntimeManager` reservation/recreate ownership.

Accordingly `P7C16_PREP_READY=YES` is not architect-accepted.

## Verdict

`P7C16_ROOT_CAUSE_REPRODUCTION=ACCEPTED`

`P7C16_LATE_BOUND_CONTROLLER_PATH_CONCEPT=ACCEPTED`

`P7C16_REAL_COORDINATOR_CHILD_HANDOFF=ACCEPTED_FOR_REUSE`

`P7C16_RUNTIME_RESERVATION_OWNERSHIP=REWORK_REQUIRED`

`P7C16_SOURCE_BUNDLE_AUTHORITY=REWORK_REQUIRED`

`P7C16_PARENT_CHILD_REAL_PATH=REWORK_REQUIRED`

`P7C16_ONE_SHOT_CONTAINMENT=REWORK_REQUIRED`

`P7C16_PREP_ARCHITECT_ACCEPTED=NO`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
