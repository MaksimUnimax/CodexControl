# Architecture

Each physical server hosts the same configuration-driven controller code, its own Telegram bot token, local durable state, and explicit configured Codex profiles. Bots share a private supergroup but remain independent: server failure affects only its bot.

Group routing is local: an ACTIVE controller accepts an authorized ordinary group message and submits it to its captured local Codex thread; SLEEP discards ordinary prompts. A private chat with each bot provides settings. Server buttons identify configured server IDs and never imply a fixed two-server topology.

The Codex adapter owns app-server stdio (preferred), profile-scoped process environment, runtime model discovery, threads, and turn events. The state store owns idempotency, job state, delivery cursor, and minimal audit metadata. Telegram and Codex adapters must not log message content.

Profile, model, effort, and thread are explicit immutable bindings. A setting change applies only to a subsequent captured binding. No controller requires another controller to be alive.
