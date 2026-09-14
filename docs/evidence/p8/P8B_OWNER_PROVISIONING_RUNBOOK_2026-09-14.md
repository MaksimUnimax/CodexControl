# P8.B owner provisioning runbook — 2026-09-14

Status: **OWNER ACTION REQUIRED / NO DEPLOYMENT / NO SERVICE START / NO P9**

This runbook creates only local root-only owner authority needed to unblock P8.B. It does not deploy CodexControl and does not authorize service start.

## Required local authority paths

Create exactly:

- `/root/.codexcontrol-owner/p8b-routing.env`
- `/root/.codexcontrol-owner/p8b-secrets.env`

The directory must be root-owned mode `0700`. Both files must be root-owned regular non-symlink files, mode `0600`, with one link where supported.

## Routing authority format

`p8b-routing.env` contains exactly two keys:

```text
OPERATOR_USER_ID=<real Telegram operator user id>
CONTROL_CHAT_ID=<real Telegram control chat id>
```

Values must be owner supplied. Repository examples are not authority.

## Secret authority format

`p8b-secrets.env` contains exactly:

```text
TELEGRAM_BOT_TOKEN=<real owner-provided bot token>
```

Do not commit, print, echo back, hash into evidence, recover from logs/history, or paste the token into ChatGPT/Codex prompts.

## Safe interactive provisioning

Run as root on server-80:

```bash
set -euo pipefail
install -d -o root -g root -m 700 /root/.codexcontrol-owner
umask 077

read -r -p "Real Telegram operator_user_id: " OPERATOR_USER_ID
[[ "$OPERATOR_USER_ID" =~ ^[0-9]+$ ]] || { echo "invalid operator id" >&2; exit 1; }

read -r -p "Real Telegram control_chat_id: " CONTROL_CHAT_ID
[[ "$CONTROL_CHAT_ID" =~ ^-?[0-9]+$ ]] || { echo "invalid control chat id" >&2; exit 1; }

printf 'OPERATOR_USER_ID=%s\nCONTROL_CHAT_ID=%s\n' \
  "$OPERATOR_USER_ID" "$CONTROL_CHAT_ID" \
  > /root/.codexcontrol-owner/p8b-routing.env
unset OPERATOR_USER_ID CONTROL_CHAT_ID

read -r -s -p "Telegram bot token: " TELEGRAM_BOT_TOKEN
printf '\n'
[[ -n "$TELEGRAM_BOT_TOKEN" ]] || { echo "empty token" >&2; unset TELEGRAM_BOT_TOKEN; exit 1; }
printf 'TELEGRAM_BOT_TOKEN=%s\n' "$TELEGRAM_BOT_TOKEN" \
  > /root/.codexcontrol-owner/p8b-secrets.env
unset TELEGRAM_BOT_TOKEN

chown root:root /root/.codexcontrol-owner/p8b-routing.env /root/.codexcontrol-owner/p8b-secrets.env
chmod 600 /root/.codexcontrol-owner/p8b-routing.env /root/.codexcontrol-owner/p8b-secrets.env
stat -c '%U:%G %a %h %F %n' /root/.codexcontrol-owner/p8b-routing.env /root/.codexcontrol-owner/p8b-secrets.env
```

Do not display file contents after creation.

## Resume boundary

Only after both files exist and pass root/mode/type validation may P8.B Resume-2 begin. P8.B remains stopped-service deployment acceptance: service inactive/disabled, Telegram HTTP/messages zero, Codex app-server/RPC zero, P9 not started.
