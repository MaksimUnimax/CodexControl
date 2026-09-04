# Product requirements

## MUST

- Run one autonomous controller and one bot token per physical server; support arbitrary configured server IDs, with no mandatory central controller.
- In a configured private supergroup, only ACTIVE controllers route authorized ordinary operator messages to Codex. SLEEP controllers ignore them permanently, while accepting their own validated controls.
- Provide button-led group server selection and private administration for identity, status, ACTIVE/SLEEP, profile, model, reasoning, dialogue creation/deletion, and diagnostics.
- Fail closed on exact operator user ID, exact control chat ID, private-chat, and supergroup checks. Validate callback freshness and deduplicate updates/callbacks.
- Select an explicit `CODEX_HOME`; never merge/copy profile/auth state. `/opt/codex-profiles/codex3` is not an account absent explicit ownership resolution.
- Preserve real Codex thread identity for multi-turn work. Capture server/profile/model/effort/thread before execution; later settings never retarget a running turn.
- Implement durable job states, deterministic ordered Telegram chunk delivery, restart recovery, sanitized errors, and no blind retry of UNKNOWN work.
- Hard deletion must stop active work, use supported Codex thread deletion, remove controller content/jobs/events, unbind the thread, and retain only minimal non-content idempotency/audit metadata.
- Never write conversation contents to journald/system logs. Never expose a public Codex listener.

## SHOULD

- Prefer app-server stdio; use a protected Unix socket only when justified. Discover models and supported reasoning effort at runtime per selected profile.
- Slash commands are diagnostic fallbacks, not the primary UI.

## OUT OF SCOPE for V1

- A mandatory central coordinator, public HTTP endpoint, cross-server shared runtime database, production service installation, and automatic profile/auth migration.
