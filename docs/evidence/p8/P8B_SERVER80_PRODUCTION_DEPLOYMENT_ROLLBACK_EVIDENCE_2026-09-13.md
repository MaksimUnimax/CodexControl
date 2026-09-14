# P8.B server-80 production deployment + rollback evidence — 2026-09-13

Status: **BLOCKED PRE-MUTATION**

## Authority readback

- Architect `origin/main` HEAD: `0074c7f820f328d4eae913529ba7e3f4658e965d`.
- Architect `origin/main` tree: `354e13682faed347e15f069f9d694b12b9bd1188`.
- Execution branch: `real-p8b-server80-deployment-2026-09-13`.
- Execution base HEAD: `1273b273ed7f58ba235b35cbce485b623c340b8d`.
- Execution base tree: `8def3b3e8591e82f77f0cea8c5f9f690949979f5`.
- Release A commit/tree: `6ffd5193962115d6e07114369e4d442ea25c34d1` / `0c16a336f70008461daa002e0f4af87f7ca70656`.
- Release B commit/tree: `1273b273ed7f58ba235b35cbce485b623c340b8d` / `8def3b3e8591e82f77f0cea8c5f9f690949979f5`.
- Binding contract: `origin/main:docs/evidence/p8/P8B_SERVER80_PRODUCTION_DEPLOYMENT_ROLLBACK_CONTRACT_2026-09-13.md`.

## Pre-mutation gates

- `/usr/local/bin/codex --version`: `codex-cli 0.144.6`.
- `/usr/bin/python --version`: `Python 3.12.3`.
- Accepted capability schema aggregate: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Pre-existing deployment classification: `/etc/codex-control` absent; `/var/lib/codex-control` absent; `/etc/systemd/system/codex-control.service` absent; `/opt/codex-control` is a separate root-owned source checkout and was not altered.
- Pre-existing service state: inactive; not installed/enabled; no CodexControl service process.
- Explicit profile paths were inspected read-only and were not modified: `/root/.codex`, `/root/.codex_second`, `/root/.codex_third`.
- Owner routing authority (`operator_user_id`, `control_chat_id`): ABSENT.
- Owner secret authority (`TELEGRAM_BOT_TOKEN`): ABSENT.

## Result

The exact owner-approved server-80 routing IDs and Telegram secret authority were unavailable before the first production write. Repository example IDs and unrelated local artifacts were not used. No release was staged, no production config/secrets/state/systemd path was written, no database was initialized, no systemd mutation was performed, and no validation/deployment transaction was run.

P8B_BLOCKED_OWNER_ROUTING_AUTHORITY_REQUIRED
P8B_PRODUCTION_MUTATIONS=0
P9_STARTED=NO
P8B_FINAL_VERDICT=BLOCKED_PRE_MUTATION
