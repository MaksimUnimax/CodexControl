# Security model

CodexControl is high-privilege remote administration. Authorization fails closed: exact configured Telegram operator user ID and control chat ID are required; private administration requires the authorized private user; group work requires the configured private supergroup. Unknown users and chats never become prompts.

Tokens, Codex auth, cookies, private keys, and server-specific secret configuration remain outside Git and are redacted from reprs/logs. Conversation prompts, responses, and raw events never enter journald/system logs. Diagnostics use IDs, state, timestamps, and sanitized error categories only.

Each update has an idempotency key before claim. Each callback is authenticated by chat/user/context, state/version, expiration, and one-time action key; duplicate destructive callbacks are harmless. A SLEEP message is recorded as ignored/deduplicated and is never replayed after activation.

Delete requires an active-turn check/interrupt policy, durable DELETE_PENDING intent, official thread deletion confirmation, content/job/event removal, then unbinding. UNKNOWN work is investigated, never blindly rerun. Codex app-server is stdio or protected local IPC only, never public.
