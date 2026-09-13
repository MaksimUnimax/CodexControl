# P7.C16 delete-chain authority successor preparation Repair-1 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / MOST REPAIR-1 AUTHORITY ACCEPTED / DEFAULT REAL ENTRY + QUIESCENCE AUTHORITY STILL BROKEN / ZERO REAL EFFECT**

## Candidate reviewed

- candidate HEAD: `aaccc8fddc4df763e7412524be85d83134f5bd64`;
- candidate tree: remote branch authority from exact commit above;
- exact Repair-1 base: `4f477e313192350414b1c157b6e1789135d11600`;
- base tree: `67a5276b34481ae3d118cbcb09dd73d2a6224973`;
- launcher blob: `08e6be10f4f7444c87a2e72572e4a8107ed7a3b2`;
- evidence blob: `4f0caaf4e3c795bc8ca1dc8d052b663f8a644d47`.

Lineage/scope are accepted: one linear commit over the frozen Repair-1 base and only the P7.C16 successor module and preparation evidence changed. No `src/**`, consumed P7.C15 source/evidence, P7.C14/P7.C13/P7.C12 source, package markers, migration, deployment, Telegram, P8 or P9 path changed.

## Architect-accepted Repair-1 material

The following Repair-1 corrections are accepted for reuse:

- the protected P7.C13 harness blob is corrected to `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- the source bundle now binds `tests/__init__.py` and `tests/real/__init__.py` blobs;
- source authority hashes the live protected files and checks clean tracked worktree/index plus repository import authority;
- the late-bound controller-storage concept remains accepted;
- cleanup-facing `reserve`, `shutdown_profile`, `recreate_isolated_state_root` and `profile` delegate to the underlying manager rather than a facade-owned reservation implementation;
- the effective inherited engine profile is explicitly `p7c15-successor-profile`;
- the production boot uses authenticated `/root/.codex_second` by default;
- a P7.C16 production executor implementation, owned-child command, watchdog seam, P7.C16 watchdog deadline, installed-runtime preflight, root-only boot/result and stronger durable ledger authority are now present;
- parent terminal mapping contains exact-effect, child, watchdog and process-group predicates;
- the production-shaped child still uses real `DeleteStorageCleanupCoordinator` and `DialogueDeleteService` with the late-bound exact controller path.

These parts must not be redesigned in Repair-2 unless a direct regression test demonstrates a defect.

## Blocker A — default real entrypoint does not select the production executor

The candidate defines:

`P7C16PreparedFutureExecutor.production(contract)`

and `_production_with_authority(...)` now contains the intended ledger -> fresh paths -> boot -> owned child/watchdog path.

However `p7c16_real_entrypoint()` still returns:

`(executor or P7C16PreparedFutureExecutor(P7C16DurableOneShotLedger(P7C16_LEDGER_PATH))).run(contract)`

The default executor created here has no watchdog and no child. Its `run()` therefore raises `P7C16PreparationError("P7.C16 production child missing")` instead of invoking the production executor.

Consequences for a future exact authorized CLI run:

- the source gate could pass;
- `P7C16PreparedFutureExecutor.production(contract)` would never be selected;
- the prepared parent -> boot -> owned child path would never execute;
- `_module_main()` would catch the preparation error and return disabled-style exit `2`.

This is a hard blocker. Repair-2 must select `P7C16PreparedFutureExecutor.production(contract)` whenever no executor is explicitly injected.

## Blocker B — real runtime quiescence is always reported false by the facade

`P7C16RuntimeManagerView.runtime_quiescent` currently returns:

`bool(getattr(self.underlying, "runtime_quiescent", False))`

The real `CodexRuntimeManager` has no `runtime_quiescent` property. Its accepted runtime ownership authority is represented by `_runtimes`, `_starting`, `_unresolved` and reservation/quiescence proof methods.

Therefore, against the real underlying manager, the facade property returns `False` even after a successful shutdown and cleanup.

The frozen P7.C15 child logic first checks a `runtime_quiescent` property when present. Because P7.C16 supplies the broken property, it prevents the accepted fallback from examining `_runtimes/_starting/_unresolved` through delegation.

A valid hard-delete run could therefore reach clean post-delete state but still fail `runtime_child_quiescent` and never PASS.

Repair-2 must either:

- remove the facade property so the inherited accepted fallback resolves delegated underlying runtime maps; or
- implement the accepted equivalent exactly: quiescent iff the underlying manager has no active `_runtimes`, `_starting` or `_unresolved` ownership for the effective profile/run.

It must not use the absence of a non-existent property as proof of non-quiescence.

## Blocker C — full positive test bypasses the actual default real entrypoint

The new positive parent test exercises `P7C16PreparedFutureExecutor._production_with_authority(...)` directly. This proves the production executor class can work through the offline child seam, but it does not prove:

source gate -> `p7c16_real_entrypoint()` -> default executor selection -> production executor -> owned child.

That omission is why Blocker A survived while the focused suite passed.

Repair-2 needs one exact authorized synthetic handoff that invokes the real P7.C16 entrypoint with a fully matching synthetic `P7C16SourceAuthority` and environment, while injecting only the production executor's process/runtime external seams. No mock executor may be supplied to `p7c16_real_entrypoint()` for this positive traversal.

The test must fail if the default entrypoint ever stops selecting `.production(contract)`.

## Blocker D — late failure convergence should use the accepted owned wait and retain a finite controller-authority stage/category

Repair-1 corrected the profile identity and removed the two-second literal, but the exception convergence path still calls `asyncio.wait_for(manager.shutdown_profile(...))` directly.

Use the accepted owned bounded helper (`p7c13._await_owned` or equivalent) so cancellation/convergence ownership is consistent with the rest of the child graph.

Also, the P7.C16 journal defines safe successor stages such as `DELETE_CLEANUP_AUTHORITY_CONFIRMED` and `DELETE_CHAIN_READY`, but the composed production path does not emit them. At the exact boundary fixed by P7.C16, a local authority mismatch can still collapse to generic `ValueError` with no safe category.

Repair-2 must add a production-safe hook around the late-bound controller-authority/coordinator construction boundary so retained evidence can distinguish at least:

- `CONTROLLER_BINDING`;
- `DELETE_CLEANUP_AUTHORITY_CONFIRMED`;
- `DELETE_CHAIN_READY`;
- `THREAD_DELETE_DISPATCH`.

Known current-run controller authority failures should retain the finite safe category `controller_storage_mismatch` without persisting raw paths.

This hook must not fake or bypass `DeleteStorageCleanupCoordinator`; the real coordinator remains mandatory.

## Verification note

The candidate evidence says `P7C16_REPAIR1_REAL_PARENT_CHILD_WATCHDOG_PATH=PASS`, but that statement is only true for direct `_production_with_authority()` testing, not for the actual default `p7c16_real_entrypoint()` path. Therefore `P7C16_PREP_READY=YES` is not architect-accepted.

## Verdict

`P7C16_REPAIR1_PROTECTED_SOURCE_BUNDLE=ACCEPTED`

`P7C16_REPAIR1_UNDERLYING_RESERVATION_OWNERSHIP=ACCEPTED`

`P7C16_REPAIR1_AUTHENTICATED_HOME=ACCEPTED`

`P7C16_REPAIR1_ROOT_ONLY_LEDGER_BOOT_RESULT=ACCEPTED`

`P7C16_REPAIR1_INSTALLED_AUTHORITY=ACCEPTED`

`P7C16_REPAIR1_DEFAULT_REAL_ENTRYPOINT=REWORK_REQUIRED`

`P7C16_REPAIR1_REAL_RUNTIME_QUIESCENCE=REWORK_REQUIRED`

`P7C16_REPAIR1_SUCCESSOR_STAGE_AUTHORITY=REWORK_REQUIRED`

`P7C16_PREP_ARCHITECT_ACCEPTED=NO`

`P7C16_REAL_EXECUTION_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
