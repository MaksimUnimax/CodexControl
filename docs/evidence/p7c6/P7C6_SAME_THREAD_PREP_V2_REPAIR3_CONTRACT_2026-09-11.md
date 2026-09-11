# P7.C6 same-thread prep-v2 Repair-3 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / DEFERRED UNTIL AFTER OWNER DISK-MAINTENANCE REVIEW**

Predecessor candidate: `4d98e2b6170e76534fa18274236605f77440f740`.

Binding architect review: `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_ARCHITECT_REVIEW_2026-09-11.md`.

Repair-3 may modify only the gated acceptance harness/tests/evidence. No production `src/**` change is authorized by the reviewed defects.

Required corrections before any real continuation can be authorized:

1. **Truly finite task ownership.** `_await_owned_task`, `_cancel_owned_approval`, `_bounded_shutdown`, and every real-flow task owner must have a finite second/final bound. No unbounded `gather()` or join may remain after timeout. If a task cannot converge within the final bound, retain recovery authority, report finite uncertainty and return/raise without retrying the operation.
2. **All spawned tasks terminalized on every exit edge.** In particular, Turn-4 approval bridge must be cancelled/joined if Turn-4 start fails before approval wait; Turn-5 terminal waiter must be terminalized if interrupt path fails; delete task must remain single-owned and never be redispatched.
3. **Exact sentinel equality.** The Turn-4 sentinel proof must use a safe descriptor/no-follow/inode-stable bounded read and require exact byte length and exact byte equality to the allow marker. One substring occurrence is insufficient. Prefix/suffix fixtures must fail.
4. **Baseline scan-to-identity atomicity.** When an unrelated file is admitted to the pre-delete baseline, the recorded path/device/inode must be the same verified identity whose bytes were scanned to prove target-thread absence. No scan-then-unrelated-lstat race is allowed.
5. **Baseline post-delete safe authority.** Exact path/category/device/inode must remain, and each preserved path must still be a safe regular file with root ownership, accepted mode constraints, non-symlink state and `st_nlink == 1`. Hardlink/unsafe-mode/owner replacement must fail reconciliation.

Preserve all successful Repair-2 authorities: source HEAD/tree/clean gate, accepted Run-1 latch/thread identity, corrected retained topology, local pre-effect path reservation, strict structural approval matcher, actual controller path/schema/live-state checks, bounded all-marker oracle, bounded exact-path unrelated baseline, unknown-RPC budget rejection, no-new-thread path, no-reacquire interrupt proof, official P1.9 observer, root-only recovery journal, success-only sanitization, and shared-CODEX_HOME semantics.

Repair-3 itself performs zero Codex/app-server/business RPC effects. All real gates remain unset. `P7C6_REAL_CONTINUATION_AUTHORIZED=NO` until the resulting commit is independently reviewed.
