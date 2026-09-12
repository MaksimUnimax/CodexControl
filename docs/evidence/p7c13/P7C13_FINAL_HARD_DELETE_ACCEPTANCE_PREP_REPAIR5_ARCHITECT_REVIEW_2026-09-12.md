# P7.C13 preparation Repair-5 — architect review — 2026-09-12

Status: **REWORK_REQUIRED / ONE MICRO RACE ONLY / NO REAL EXECUTION**

## Candidate reviewed

- commit: `c09b5b3dfb197a647bd2f732ed343d42bf4aec0e`
- tree: `4ecd65c7a251b5931b579b3b324724731fda785b`
- harness blob: `cb64f44bc71339300e2d697167daa08b0b601f15`
- evidence blob: `d9baf8af54b9b2bc6597ed7c5b2db5933ee7f184`
- parent: `86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`

Lineage/scope are accepted: one linear Repair-5 commit, only the P7.C13 harness and evidence changed, no `src/**`, no accepted P7.C12/historical mutation.

## Accepted Repair-5 material

The external-user classification repair is accepted. `persistent_home`, `repository`, and `controller_root` are report-only/shared/source authorities; the nine exact destructive run-owned boundaries fail closed on nonzero external users. Mount, physical-alias, topology, root-ownership and symlink checks remain fail closed.

The Turn-4 design direction is also accepted: one terminal waiter plus one request observer, no `CodexApprovalBridge` or response call on the Turn-4 observer path, unexpected request blocks controller/delete eligibility, one cleanup interrupt at most, and task ownership is explicit.

All accepted Repair-4 material remains frozen and must not be redesigned.

## Sole remaining blocker

`observe_owned_turn4()` takes a preliminary request-task snapshot in `finally`, then may join the terminal task, then conditionally joins the request task. There is a race where the request task can complete after the preliminary `request_task.done()` check but before/during the later join logic. In that case the request task may already be done when the conditional join is reached, so its result is never reclassified and `unexpected_request_count` can remain `0`.

This violates the frozen requirement that the final fact snapshot after Turn-4 terminal convergence must classify any server request observed before the request observer is closed. A late completed request must never be silently converted into a clean cancellation/join fact.

## Required correction

Repair-6 is limited to making the final request-observer close/join classification atomic/fail-closed at the task-result level:

- after the observer is closed/joined, inspect its terminal state/result exactly once more;
- if it completed with a server request before cancellation took effect, set `unexpected_request_count=1`;
- if it was intentionally cancelled without delivering a request, preserve zero unexpected requests and do not mark an observer fault merely because cancellation was locally requested;
- any observer exception other than the harness-owned cancellation path is non-PASS;
- the final PASS predicate must use this post-join authoritative snapshot;
- no second response route may be introduced;
- controller/delete remains unreachable when the late request fact is positive.

Add a deterministic synthetic test that forces the request to complete specifically between the old pre-join snapshot and final observer join/close. It must be detected as non-PASS with zero response calls and controller/delete unreachable.

No other production behavior is reopened.

## Authorization

`P7C13_REPAIR5_EXTERNAL_USER_CLASSIFICATION=ACCEPTED`

`P7C13_REPAIR5_TURN4_DIRECTION=ACCEPTED_WITH_MICRO_RACE_REPAIR_REQUIRED`

`P7C13_PREP_ARCHITECT_ACCEPTED=NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
