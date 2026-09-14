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

## P8.B blocked history

The original P8.B attempt stopped correctly before production mutation because owner routing/Telegram secret authority was absent.

Historical branch/evidence:

`real-p8b-server80-deployment-2026-09-13`

`7985bb0cc740af2c29f4daac7556f18c5ef2c501`

Resume-1 then used the corrected drift-safe architect authority and again reached the real owner-authority gate. It also stopped correctly with zero production mutations.

Historical Resume-1 branch/evidence:

`real-p8b-server80-deployment-resume1-2026-09-14`

`8589c174dff16a189004457fd1c7ec7a69a7f96f`

Both branches are immutable historical evidence and MUST NOT be reset to release B or reused for a later successful deployment.

Resume-1 architect review:

`docs/evidence/p8/P8B_RESUME1_BLOCKED_OWNER_AUTHORITY_ARCHITECT_REVIEW_2026-09-14.md`

`P8B_IMPLEMENTATION_REPAIR_REQUIRED=NO`

`P8B_PRODUCTION_MUTATIONS=0`

## Superseded SHA gates

The initial P8.B hard-coded architect-main SHA gates are **SUPERSEDED**. Do not restore `main` to an older SHA and do not reset historical evidence branches.

Binding notices:

`docs/evidence/p8/P8B_INITIAL_PROMPT_SUPERSEDED_NOTICE_2026-09-14.md`

`docs/evidence/p8/P8B_RESUME1_EXECUTION_AUTHORITY_V2_2026-09-14.md`

Future P8.B execution reads current live `origin/main` authority documents and hard-gates only the accepted A/B release objects plus material execution boundaries.

## Current executable slice — owner provisioning before P8.B Resume-2

P8.B remains the current roadmap stage but **must not be executed again until owner authority has actually been provisioned on server-80**.

Required local root-only authority files:

- `/root/.codexcontrol-owner/p8b-routing.env`;
- `/root/.codexcontrol-owner/p8b-secrets.env`.

Owner provisioning runbook:

`docs/evidence/p8/P8B_OWNER_PROVISIONING_RUNBOOK_2026-09-14.md`

Only after both files exist and pass owner/mode/type/bounded-parser validation may Resume-2 execute.

Binding Resume-2 contract:

`docs/evidence/p8/P8B_OWNER_AUTHORITY_RESUME2_CONTRACT_2026-09-14.md`

Fresh Resume-2 evidence branch:

`real-p8b-server80-deployment-resume2-2026-09-14`

Required Resume-2 base remains exact release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

P8.B remains stopped-service acceptance:

- service inactive;
- service disabled;
- no Telegram HTTP/message effects;
- no Codex app-server/RPC effects;
- no P7 mutation;
- no P9.

After provisioning and all pre-mutation gates pass, Resume-2 performs the accepted real A→B→A→B deployment/rollback sequence with final current=B and service still stopped/disabled.

`P8B_OWNER_PROVISIONING_REQUIRED=YES`

`P8B_RESUME1_BRANCH_RESET_AUTHORIZED=NO`

`P8B_RESUME2_AUTHORIZED_ONLY_AFTER_OWNER_PROVISIONING=YES`

`P8B_SERVICE_ACTIVE=NO`

`P8B_SERVICE_ENABLED=NO`

`P9_STARTED=NO`

## After P8.B

Only independent architect acceptance of a successful P8.B Resume-2 (or later explicitly authorized fresh attempt) may unblock P9. P9 owns the first live service start, Telegram polling and user-visible real workflow acceptance.
