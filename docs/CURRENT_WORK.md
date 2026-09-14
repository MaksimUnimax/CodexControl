# Current work authority

Date: 2026-09-14

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are architect complete.
- P7 hard-delete correction is COMPLETE / ARCHITECT_ACCEPTED. All consumed P7 real probes/successors remain immutable and non-retryable.
- Controller schema authority is v4 with migration `0004_delete_local_containment`.

## P8.A final authority

P8.A is **COMPLETE / ARCHITECT_ACCEPTED**.

Final accepted release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Accepted-code rollback base A:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

Tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

Architect acceptance:

`docs/evidence/p8/P8A_FINAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`

`P8A_COMPLETE=YES`

## P8.B first attempt

The first P8.B attempt stopped correctly before any production mutation because owner-specific routing and Telegram secret authority were absent.

Historical blocked evidence commit:

`7985bb0cc740af2c29f4daac7556f18c5ef2c501`

Historical branch:

`real-p8b-server80-deployment-2026-09-13`

This branch is immutable historical evidence and MUST NOT be reset to release B.

Architect review:

`docs/evidence/p8/P8B_BLOCKED_PREMUTATION_ARCHITECT_REVIEW_2026-09-14.md`

`P8B_PRODUCTION_MUTATIONS=0`

`P8B_IMPLEMENTATION_REPAIR_REQUIRED=NO`

## Superseded initial prompt authority

The original P8.B prompt SHA gates are **SUPERSEDED**.

In particular, executors MUST NOT require:

- architect `origin/main=0074c7f820f328d4eae913529ba7e3f4658e965d`;
- historical branch `real-p8b-server80-deployment-2026-09-13` to equal release B.

Do NOT restore `main` to the old SHA.
Do NOT reset the historical evidence branch.

Binding supersession notice:

`docs/evidence/p8/P8B_INITIAL_PROMPT_SUPERSEDED_NOTICE_2026-09-14.md`

## Current executable slice — P8.B Resume-1

P8.B remains the current slice, but execution must use the Resume-1 authority.

Binding resume contract:

`docs/evidence/p8/P8B_OWNER_AUTHORITY_RESUME_CONTRACT_2026-09-14.md`

Fresh evidence branch:

`real-p8b-server80-deployment-resume1-2026-09-14`

Required Resume-1 base:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Resume-1 is authorized only after explicit root-only owner-provided local authority exists for:

- real `operator_user_id`;
- real `control_chat_id`;
- real `TELEGRAM_BOT_TOKEN`.

Repository example IDs are placeholders and never production authority.

All original stopped-service P8.B restrictions remain binding:

- service remains inactive;
- service remains disabled;
- no Telegram HTTP/message effects;
- no Codex app-server/RPC effects;
- no P7 mutation;
- no P9.

After owner authority exists, Resume-1 must rerun every pre-mutation gate and then perform the accepted real A→B→A→B deployment/rollback acceptance with final current=B and service still stopped/disabled.

`P8B_INITIAL_PROMPT_SUPERSEDED=YES`

`P8B_OLD_MAIN_RESTORE_AUTHORIZED=NO`

`P8B_HISTORICAL_BRANCH_RESET_AUTHORIZED=NO`

`P8B_RESUME1_BRANCH_REQUIRED=YES`

`P8B_SERVICE_ACTIVE=NO`

`P8B_SERVICE_ENABLED=NO`

`P9_STARTED=NO`

## After P8.B

Only independent architect acceptance of exact successful P8.B Resume-1 evidence may unblock P9. P9 owns the first live service start, Telegram polling and user-visible real workflow acceptance.
