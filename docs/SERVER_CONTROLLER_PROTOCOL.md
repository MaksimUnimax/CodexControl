# Shared server-controller semantic protocol

V1 has no mandatory cross-server RPC. Every controller independently implements the same Telegram/fleet semantics.

## Group event classification
Authorized user message is exactly one of: ACTIVATE_SERVER(display_label,message_id), ALL_SLEEP(message_id), STATUS(message_id), ORDINARY_PROMPT(update_id,message_id,text), RESERVED_COMMAND_UNSUPPORTED.

Every controller applies activation locally. Exact self -> ACTIVE; other or unknown activation target -> SLEEP. Human reply-keyboard origin is essential: no bot-to-bot messaging dependency.

## Local in-process ports
`StateRepository` transactional state; `CodexAdapter` model/thread/turn/approval/interrupt/delete; `TelegramGateway` authorized ingress/ordered delivery; `Clock` and `IdGenerator` deterministic testing. Domain/application cannot bypass ports to concrete SQLite/Codex/Telegram effects.

## Compatibility
Status includes fleet manifest version. Transient different versions are allowed, but reserved activation prefix always classifies as control so an older controller cannot execute a new-server button as Codex prompt.
