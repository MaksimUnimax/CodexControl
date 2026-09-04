# Telegram UX summary

Normative details: `TELEGRAM_INTERACTION_CONTRACT.md`.

## Shared group
Private supergroup `CODEX CONTROL` has persistent reply keyboard with configured server buttons, ALL SLEEP and STATUS. A server tap is a human message seen by all controllers: target activates, others sleep. Active server handles later ordinary text as Codex prompts.

## Private bot
Management card exposes account/profile, model, reasoning, dialogue and status with buttons. Profile change is blocked while dialogue exists. Model/reasoning changes are allowed only while no turn runs and after runtime validation. Delete is explicitly confirmed and hard-deletes Codex thread before local unbinding. Manual slash-command typing is not required.
