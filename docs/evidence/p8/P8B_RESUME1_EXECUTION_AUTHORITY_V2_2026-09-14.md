# P8.B Resume-1 execution authority V2 — 2026-09-14

Status: **BINDING / DRIFT-SAFE ARCHITECT MAIN READBACK / EXACT RELEASE AUTHORITY FROZEN / RESUME BRANCH REQUIRED / P9 NOT STARTED**

## Why V2 exists

Two safe P8.B invocations stopped before mutation because an executor used superseded hard-coded architect-main / historical-evidence-branch SHA requirements from the original P8.B prompt.

Those requirements are no longer valid and MUST NOT be restored.

## Architect-main rule

Do not hard-code a required `origin/main` SHA for Resume-1.

At execution time:

1. `git fetch origin --prune`;
2. record the current live `origin/main` HEAD and tree;
3. read current `origin/main:docs/CURRENT_WORK.md` in full;
4. read current `origin/main:docs/evidence/p8/P8B_INITIAL_PROMPT_SUPERSEDED_NOTICE_2026-09-14.md` in full;
5. read this V2 authority and the owner-authority resume contract from current `origin/main` in full;
6. require those documents still state that P8.A is accepted, P8.B Resume-1 is current, old main restoration is forbidden, historical blocked branch reset is forbidden, release B is unchanged, and P9 is not started.

If current main changes only because architect authority/evidence advances while these invariant facts remain unchanged, that is NOT execution drift and is NOT a reason to restore an older `main`.

If current main changes the accepted release B/tree, P8.B execution boundary, profile authority, or P9 state, stop for architect review.

## Frozen release authority

Rollback base A remains:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

Tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

Final release B remains:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`.

These A/B objects are hard gates.

## Historical blocked branch

`real-p8b-server80-deployment-2026-09-13`

is immutable historical blocked evidence. Its accepted blocked-evidence commit is:

`7985bb0cc740af2c29f4daac7556f18c5ef2c501`.

Do not reset, rewrite, or execute Resume-1 on it.

## Resume branch

Use only:

`real-p8b-server80-deployment-resume1-2026-09-14`

Before any Resume-1 evidence is committed, it must be exact release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

with tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`.

If a prior Resume-1 blocked-evidence commit is later added to this branch, a further resumed attempt requires a fresh architect-authorized evidence branch; do not reset it.

## Owner authority

Production mutation remains forbidden until valid root-only owner-provided local authority exists for the real routing IDs and Telegram token.

The secret must not be printed, committed, or included in evidence.

## Execution boundary

All stopped-service P8.B restrictions remain binding. Service remains inactive and disabled. Telegram HTTP/messages = 0. Codex app-server/RPC = 0. P7 mutation = 0. P9 = not started.

After all owner and pre-mutation gates pass, continue the original P8.B A→B→A→B production deployment/rollback acceptance. Final current must be B.

`P8B_RESUME1_V2_ACTIVE=YES`

`P8B_ARCHITECT_MAIN_HARDCODED_SHA_REQUIRED=NO`

`P8B_RELEASE_AB_HARD_GATES=YES`

`P8B_HISTORICAL_BRANCH_RESET_AUTHORIZED=NO`

`P8B_OLD_MAIN_RESTORE_AUTHORIZED=NO`

`P9_STARTED=NO`
