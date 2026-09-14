# CodexControl project freeze checkpoint — 2026-09-14

Status: **FROZEN BY OWNER / SAFE STOP / NO PRODUCTION DEPLOYMENT STARTED / P9 NOT STARTED**

## Frozen point

The project is intentionally paused by the owner.

Accepted completed authority:

- P0–P6: architect complete;
- P7: COMPLETE / ARCHITECT_ACCEPTED; all consumed real probes remain immutable and non-retryable;
- P8.A: COMPLETE / ARCHITECT_ACCEPTED.

Final accepted P8.A release B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

Tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Accepted rollback-base release A:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

Tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

## P8.B state at freeze

P8.B has NOT crossed the production-mutation gate.

Both prior attempts stopped correctly before production mutation because explicit owner routing / Telegram secret authority was absent.

Historical immutable evidence:

- initial P8.B blocked branch: `real-p8b-server80-deployment-2026-09-13` at `7985bb0cc740af2c29f4daac7556f18c5ef2c501`;
- Resume-1 blocked branch: `real-p8b-server80-deployment-resume1-2026-09-14` at `8589c174dff16a189004457fd1c7ec7a69a7f96f`.

Do not reset or reuse those branches.

Fresh Resume-2 branch prepared for future continuation:

`real-p8b-server80-deployment-resume2-2026-09-14`

It was created from exact release B and must remain untouched while the project is frozen unless a future architect explicitly advances the authority.

## Real production effects at freeze

No successful P8.B production deployment has occurred.

Frozen state:

- no CodexControl production release switch performed;
- no production `/etc/codex-control` configuration installed by P8.B;
- no production controller DB initialized by P8.B;
- no CodexControl systemd unit installed/reloaded by successful P8.B;
- CodexControl service not started/enabled;
- Telegram HTTP/messages = 0;
- Codex app-server/RPC effects = 0;
- P7 mutation = 0;
- P9 not started.

## Exact blocker

The remaining P8.B blocker is external owner provisioning, not implementation.

Before P8.B may resume, server-80 must have explicit root-only owner-provided authority for:

- real Telegram `operator_user_id`;
- real Telegram `control_chat_id`;
- real `TELEGRAM_BOT_TOKEN`.

Expected local authority paths are documented as:

- `/root/.codexcontrol-owner/p8b-routing.env`;
- `/root/.codexcontrol-owner/p8b-secrets.env`.

Do not place the Telegram token in chat, Git, evidence, logs, or prompts.

## Resume protocol

When the owner returns to the project:

1. fetch current live `origin/main`;
2. read `docs/CURRENT_WORK.md` and this freeze checkpoint in full;
3. verify P8.A release B / A authority is still unchanged;
4. verify the historical blocked branches remain immutable;
5. verify whether the prepared Resume-2 branch is still exact release B or whether newer architect authority supersedes it;
6. provision/validate the owner routing and secret authority locally on server-80;
7. only then resume P8.B stopped-service deployment/rollback acceptance;
8. keep the service inactive/disabled throughout P8.B;
9. only independent architect acceptance of successful P8.B may unblock P9.

Do not restart old P8.B prompts with superseded hard-coded main SHA gates.

## Freeze flags

`PROJECT_FROZEN_BY_OWNER=YES`

`FROZEN_STAGE=P8B_OWNER_PROVISIONING_BEFORE_RESUME2`

`P8A_COMPLETE=YES`

`P8B_PRODUCTION_DEPLOYMENT_COMPLETE=NO`

`P8B_PRODUCTION_MUTATIONS_ACCEPTED=0`

`P8B_IMPLEMENTATION_REPAIR_REQUIRED=NO`

`P8B_OWNER_PROVISIONING_REQUIRED=YES`

`P9_STARTED=NO`
