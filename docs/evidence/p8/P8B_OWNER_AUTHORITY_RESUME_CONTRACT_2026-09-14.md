# P8.B owner-authority resume contract — 2026-09-14

Status: **FROZEN / RESUME ONLY AFTER EXPLICIT OWNER AUTHORITY EXISTS / BLOCKED EVIDENCE RETAINED / P9 NOT STARTED**

## Binding source

Accepted release B remains `1273b273ed7f58ba235b35cbce485b623c340b8d` / tree `8def3b3e8591e82f77f0cea8c5f9f690949979f5`.

Rollback base A remains `6ffd5193962115d6e07114369e4d442ea25c34d1` / tree `0c16a336f70008461daa002e0f4af87f7ca70656`.

The first P8.B attempt ended `BLOCKED_PRE_MUTATION` at evidence commit `7985bb0cc740af2c29f4daac7556f18c5ef2c501` with zero production mutations. That branch/evidence remains immutable historical evidence.

## Resume gate

A resumed attempt is allowed only after explicit root-only owner-provided local authority exists for the real server-80 routing identity and Telegram credential. Repository example values are never authority.

The resumed executor must validate provenance/classification without printing credential contents, then rerun every original pre-mutation gate. If owner authority is still absent or invalid, stop again before any production mutation.

## Fresh evidence branch

Use a fresh branch from exact B:

`real-p8b-server80-deployment-resume1-2026-09-14`

Do not append a successful deployment result onto the historical blocked branch.

## Execution boundary

All original P8.B stopped-service restrictions remain binding. The service must stay inactive and disabled. No Telegram HTTP call, no Codex app-server/RPC, no P7 mutation, and no P9 activity is authorized.

If the owner-authority gate passes, continue the original P8.B A→B→A→B production deployment/rollback contract exactly. Final current must be B and service must remain stopped/disabled.

`P8B_RESUME_AUTHORIZED=YES_AFTER_OWNER_AUTHORITY_EXISTS`

`P8B_SERVICE_ACTIVE_REQUIRED=NO`

`P8B_SERVICE_ENABLED_REQUIRED=NO`

`P9_STARTED=NO`
