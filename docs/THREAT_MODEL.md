# Threat model — V1

## Assets
Root control, Codex credentials/profiles, Telegram bot tokens, operator/Codex content, production integrity and durable controller state.

## Stolen bot token
Separate token per server limits blast radius; exact user/chat allowlists still gate prompt execution; token is root-only and rotatable. Severe residual risk remains if attacker can also observe/act in authorized chat.

## Operator Telegram account compromise
Effectively root compromise while controller available. V1 cannot distinguish legitimate human after Telegram account takeover. Residual risk accepted; mitigate with Telegram account/device security, explicit server activation, approval UI and rapid token/service revocation.

## Two bots ACTIVE
Mitigate with boot->SLEEP, user-originated total-order activation messages, serialized group ingress and unknown activation prefix -> SLEEP. Disconnected bot does not receive prompts; restart returns SLEEP; backlog is processed in order when applicable.

## Duplicate/replayed update
Durable unique update ID and terminal disposition before external effect.

## Stale/double callback
Opaque one-time token, exact user/chat, expected entity version/state, expiry and atomic consume.

## Prompt injection from server data
Files/logs are evidence, not operator authority. They cannot change controller authorization/architecture. Privileged Codex operations use app-server approval policy where requested.

## Codex child crash after possible effect
UNKNOWN + reconciliation only; no blind prompt replay.

## Telegram timeout after send
Prefer edit of known message; track confirmed segments; ambiguous create not automatically resent.

## Partial Codex hard delete
Measure official thread/delete storage effect before production. If material per-dialogue data remains in shared stores, stop for architect decision; no shared DB surgery.

## Shared CODEX_HOME with other workloads
Use only official APIs and explicit profile process. Detect conflicts where possible. If safe isolation cannot be proven, P7 gate may require dedicated controller homes via new ADR.

## Disk exhaustion
No second permanent transcript, bounded transient payload retention/temp quotas, status metrics and hard delete.

## Malicious/accidental control-looking text
Only exact operator can control; reserved activation prefix is never a Codex prompt, unknown target sleeps bot.

## Accepted residual risk
Telegram is third-party transport; authorized operator can intentionally direct root Codex to destructive work; existing shared Codex retention remains a gate until measured.
