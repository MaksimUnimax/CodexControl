# CodexControl

CodexControl is a high-privilege Telegram control plane for operating Codex agents on Linux servers when the operator is away from a computer.

Each server runs an autonomous controller with its own Telegram bot token, local durable state and explicit Codex account profiles. Multiple server bots share one private Telegram supergroup. A persistent user keyboard selects the active server; non-target controllers sleep. No central runtime is required.

One maintenance task uses one real Codex thread. The operator can continue the dialogue across Telegram messages, use validated model/reasoning settings, interrupt work, approve privileged operations and finally hard-delete the dialogue. Hard delete uses official Codex thread deletion and purges CodexControl-owned conversational payloads/temp data. Conversation content is forbidden in journald.

## Current status
V1 architecture/governance is established on branch `architecture-v1-baseline-2026-09-04` above verified foundation commit `626bcd48f8719b467a565de601564a4550ead83b`. No production Telegram controller is deployed.

## Read first
- `AGENTS.md` — binding executor rules.
- `docs/ARCHITECTURE_BASELINE.md` — frozen invariants/document authority.
- `docs/PRODUCT_REQUIREMENTS.md` and `docs/ARCHITECTURE.md`.
- `docs/STATE_MACHINES.md` and `docs/DATA_MODEL.md`.
- `docs/SECURITY_MODEL.md` and `docs/THREAT_MODEL.md`.
- `docs/ROADMAP.md` and `docs/CURRENT_WORK.md`.

Repository must never contain Telegram tokens, Codex credentials/cookies, private keys or live conversation content.
