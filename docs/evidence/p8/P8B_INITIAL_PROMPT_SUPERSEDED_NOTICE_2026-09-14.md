# P8.B initial prompt superseded notice — 2026-09-14

Status: **BINDING / INITIAL P8.B SHA GATES SUPERSEDED / DO NOT RESTORE OLD REFS / RESUME-1 ONLY**

The original P8.B execution prompt that required architect `origin/main=0074c7f820f328d4eae913529ba7e3f4658e965d` and required `real-p8b-server80-deployment-2026-09-13` to start at release B is superseded.

Do **not** restore, reset, force-update, or otherwise move current architect `main` back to `0074c7f...`.

Do **not** reset the historical evidence branch `real-p8b-server80-deployment-2026-09-13` from its accepted blocked-evidence commit `7985bb0cc740af2c29f4daac7556f18c5ef2c501` back to release B.

The blocked branch is immutable historical evidence of a correct zero-mutation fail-closed stop.

The only branch authorized for continued P8.B execution is:

`real-p8b-server80-deployment-resume1-2026-09-14`

which must start from exact accepted release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

with tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`.

The binding resume contract is:

`docs/evidence/p8/P8B_OWNER_AUTHORITY_RESUME_CONTRACT_2026-09-14.md`.

A resumed executor must fetch current `origin/main` and read the resume contract from `origin/main`; it must not compare the live repository to the superseded initial prompt SHA gates.

Resume is allowed only after explicit local owner routing and secret authority exists. If owner authority is still absent, stop before production mutation again.

`P8B_INITIAL_PROMPT_SUPERSEDED=YES`

`P8B_OLD_MAIN_RESTORE_AUTHORIZED=NO`

`P8B_HISTORICAL_BRANCH_RESET_AUTHORIZED=NO`

`P8B_RESUME1_BRANCH_REQUIRED=YES`

`P9_STARTED=NO`
