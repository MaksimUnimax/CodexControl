# Observability and retention

## Logging
Logs answer state/health, not conversation. Allowed: server/profile IDs/aliases, short job/dialogue IDs, state transitions, Codex version, model, durations/counts, Telegram IDs, storage metrics and sanitized error class. Forbidden: prompts, responses, raw events, hidden reasoning, command stdout/stderr, environment dumps, auth/token/cookies/keys and arbitrary unsanitized exception bodies.

## Error taxonomy
Normalize to allowlisted categories such as CONFIG, AUTHZ, TELEGRAM_RATE_LIMIT, TELEGRAM_PERMISSION, TELEGRAM_NETWORK_AMBIGUOUS, CODEX_CAPABILITY, CODEX_AUTH, CODEX_PROCESS, CODEX_PROTOCOL, CODEX_TURN_FAILED, CODEX_AMBIGUOUS, STORAGE, STALE_ACTION, BUSY, DELETE_UNKNOWN.

## Content retention
SLEEP/unauthorized ingress retains no text. Accepted prompt/output is transient durable content only while crash-safe execution/delivery needs it. Codex thread persists while dialogue active. Controller intentionally keeps no second permanent transcript. Hard delete purges remaining dialogue-owned controller content.

Initial configurable targets to test: completed transient payload <=1h; failed/unknown payload <=24h only when needed for reconciliation; non-content job metadata <=7d; deletion tombstone <=7d. Never infinite.

## Temp files
Controller-owned temp lives under state root with opaque per-job dirs, removed on terminal cleanup/delete, and subject to size ceilings before media support.

## Codex internal retention gate
Measure sessions/rollouts/history/state/log stores before/after disposable thread/delete. If unavoidable global logs remain, report exact size/content characteristics. If material per-dialogue content is retained and cannot be officially deleted, production gate stops for architecture decision rather than manipulating shared DBs.

## Safe status metrics
Controller uptime/mode, DB health/size, transient size/count, dialogue state, app-server child state, root disk free %, Codex version/capability age, fleet version and last sanitized error.
