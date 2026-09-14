# P8.B server-80 production deployment + rollback evidence — Resume-1 — 2026-09-14

Status: **BLOCKED_PRE_MUTATION**

## Authority readback

- Current live `origin/main` HEAD: `83729747004434e47d0a662d0229266615314866`.
- Current live `origin/main` tree: `dc4822a4f0123ebd244b53edb37a71766254d18a`.
- Execution branch: `real-p8b-server80-deployment-resume1-2026-09-14`.
- Execution base HEAD/tree: `1273b273ed7f58ba235b35cbce485b623c340b8d` / `8def3b3e8591e82f77f0cea8c5f9f690949979f5`.
- Rollback base A/tree: `6ffd5193962115d6e07114369e4d442ea25c34d1` / `0c16a336f70008461daa002e0f4af87f7ca70656`.
- Final release B/tree: `1273b273ed7f58ba235b35cbce485b623c340b8d` / `8def3b3e8591e82f77f0cea8c5f9f690949979f5`.
- Binding authority was read from current `origin/main`: CURRENT_WORK, the superseded-initial-prompt notice, Resume-1 execution authority V2, owner-authority resume contract, server-80 deployment/rollback contract, and P8.A final architect acceptance.
- P8.A remains accepted; P8.B Resume-1 remains current; release B remains unchanged; old-main restoration and historical blocked-branch reset remain forbidden; P9 remains not started.

## Pre-mutation gates

- Exact A and B commit/tree checks: PASS.
- `/usr/bin/python --version`: `Python 3.12.3` — PASS.
- `/usr/local/bin/codex --version`: `codex-cli 0.144.6` — PASS.
- Accepted capability schema: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466` — PASS.
- Existing intended CODEX_HOME roots were inspected read-only and not modified: `/root/.codex`, `/root/.codex_second`, `/root/.codex_third`; all were present and root-owned.
- Pre-existing deployment classification: `/etc/codex-control` absent; `/var/lib/codex-control` absent; `/opt/codex-control/releases` absent; `/etc/systemd/system/codex-control.service` absent. The separate `/opt/codex-control` source checkout was not altered.
- Pre-existing service state: systemd `LoadState=not-found`, `ActiveState=inactive`, `is-enabled=not-found`; no exact `codex-control` process.
- Owner routing authority (`operator_user_id`, `control_chat_id`): **ABSENT / NOT VALIDATED**.
- Owner secret authority (`TELEGRAM_BOT_TOKEN`): **ABSENT / NOT VALIDATED**. No token was printed, recovered, copied, hashed, or committed.

## Result

The required explicit root-only owner-provided authority was unavailable before the first production mutation. The repository example IDs were not used and no routing ID or secret was invented or recovered from logs/history.

No release was staged. No production config, secret, deployment directory, state directory or database was created. No systemd unit was installed, reloaded, enabled, started, stopped or restarted. No release switch or rollback was attempted. No production validation was run.

`P8B_BLOCKED_OWNER_ROUTING_AUTHORITY_REQUIRED`

`P8B_BLOCKED_OWNER_SECRET_AUTHORITY_REQUIRED`

`P8B_PRODUCTION_MUTATIONS=0`

`P8B_TELEGRAM_HTTP_CALLS=0`

`P8B_TELEGRAM_MESSAGES=0`

`P8B_CODEX_APP_SERVER_STARTS=0`

`P8B_CODEX_RPC_CALLS=0`

`P8B_P7_LEDGER_MUTATIONS=0`

`P8B_SERVICE_ACTIVE=NO`

`P8B_SERVICE_ENABLED=NO`

`P9_STARTED=NO`

`P8B_FINAL_VERDICT=BLOCKED_PRE_MUTATION`
