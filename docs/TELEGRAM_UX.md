# Telegram UX

The configured private supergroup is **CODEX CONTROL**. Its server chooser is configuration-driven: `[SERVER-80] [SERVER-78] [future servers…] [ALL SLEEP] [STATUS]`. Controllers act only on their own signed/validated activation actions. Ordinary messages are accepted only by the selected ACTIVE server.

Private chat with each server bot is the primary management surface: `[ACCOUNT] [MODEL] [REASONING] [DIALOGUE] [STATUS]`, with clear current values. Dialogue offers `[NEW DIALOGUE]` and `[DELETE DIALOGUE]`; delete requires a confirmation button with fresh callback state. Buttons, not typed commands, are normal operation. Slash commands are diagnostics/fallback only.
