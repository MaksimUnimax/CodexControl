# P7.C6 same-thread prep-v2 Repair-2 architect review — 2026-09-11

Status: **REWORK_REQUIRED / REAL CONTINUATION NOT AUTHORIZED**

Reviewed candidate: `4d98e2b6170e76534fa18274236605f77440f740`.

Base: `5cc500be0087732518eb16bee0dc71dc21f786c0`, tree `d8b03629a47c6803d3ac118720acb74e453d67c5`.

The candidate is exactly one commit above the architect base and changes only the gated continuation harness plus sanitized Repair-2 evidence. No production `src/**` change is present. The useful Repair-2 work is preserved as inert test/evidence code, but it is not accepted as real-execution authority.

## Accepted useful repairs

The candidate materially improves the harness: exact source HEAD/tree/clean-worktree authority, corrected retained-topology nesting, pre-effect local path allocation, root-only continuation latch/journal, fail-closed journal calls in the principal real flow, actual controller path/schema/live-state checks, bounded marker scanning with post-read pathname checks, bounded unrelated baseline, exact path/device/inode reconciliation, strict structural approval matching, unknown-RPC budget rejection, official delete observation, success-only sanitization, and no intended new-thread path.

## Remaining blocker 1 — finite timeout helpers are not actually finite

`_await_owned_task()` performs a primary bounded wait and a second bounded convergence wait, but after the second failure it calls `task.cancel()` followed by an unbounded `await asyncio.gather(task, return_exceptions=True)`. `_cancel_owned_approval()` has the same unbounded final gather, and `_bounded_shutdown()` also cancels and joins without a second finite bound.

For operations whose implementation deliberately owns work through caller cancellation — especially `DialogueDeleteService.delete()` — cancellation is not guaranteed to make the outer task terminate immediately. Therefore the current helper can hang indefinitely after its advertised finite timeout.

This violates the frozen one-shot requirement that every wait remain finite and that uncertainty be retained rather than converted into an unbounded harness hang.

## Remaining blocker 2 — not every spawned async task is owned on every sibling failure path

The Turn-4 approval bridge is created before `turn/start`, but if Turn-4 start itself fails before the code enters the approval wait, the outer `finally` shuts down the runtime without explicitly cancelling/joining the exact bridge task.

Likewise, after Turn-5 creates its terminal waiter, a failure in the interrupt path can exit through outer cleanup without an explicit finite join of that exact terminal waiter.

Every task created by the harness must have a single owner and a bounded terminalization path on every exit edge.

## Remaining blocker 3 — Turn-4 sentinel “exact content” is not exact

`_safe_exact_file()` currently delegates to the target scanner and passes when the expected marker occurs exactly once. A file containing prefix/suffix bytes plus one marker occurrence can therefore pass.

The acceptance condition is stronger: the sentinel file bytes must equal the new allow marker exactly, with no prefix/suffix. The safe descriptor/no-follow/inode-stable implementation must also compare exact byte length/content.

## Remaining blocker 4 — unrelated baseline capture still has a scan-to-identity race

`capture_unrelated_baseline()` first scans a file to prove the target thread ID is absent and then performs a separate pathname `lstat()` to capture `(relative_path, st_dev, st_ino)`. A shared-home pathname could be replaced between those operations. The baseline could then record an inode that was not the inode whose content was scanned.

The bounded scanner must return the verified scanned identity, or the subsequent pathname stat must be proven to match that exact scanned identity before it is admitted to the unrelated baseline.

## Remaining blocker 5 — unrelated post-delete reconciliation does not revalidate full safe file authority

Reconciliation checks exact relative path/category/device/inode, which is correct as far as identity goes, but it does not fail if the preserved inode has become an unsafe hardlink, unsafe owner/mode, symlink/special state, or otherwise violates the safe-file envelope used for baseline capture.

The same pre-delete unrelated identity must remain at the same path **and** remain a safe regular file with the accepted owner/mode/link constraints.

## Production classification

No production P1.7/P1.8/P1.9/C3/C4/C5 defect is established by this review.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_CONTINUATION_PREP_V2_REPAIR2=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

P8/P9 remain blocked.

## Owner-requested temporary pause

Per owner instruction, execution of the next harness repair is temporarily paused while server-80 disk usage is inventoried and reviewed for safe cleanup. No disk cleanup may remove the retained P7.C6 recovery/latch/controller/state authorities.
