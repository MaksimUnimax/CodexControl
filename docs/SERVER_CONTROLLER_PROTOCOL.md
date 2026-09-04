# Server controller protocol

Controllers are autonomous. Shared UI semantics use configuration records (`server_id`, display name, bot identity), not inter-controller RPC.

Core interfaces are: `TelegramGateway` (validated updates/callbacks and ordered sends), `ControllerStateStore` (idempotency, settings, jobs, bindings), `CodexAdapter` (profile-scoped model list, thread start/resume/delete, turn start/interrupt, events), and `DialogueService` (state-machine transitions). Every `TurnRequest` contains an immutable `DialogueBinding` snapshot plus update ID. Adapter events are correlated by thread/turn IDs; only sanitized status crosses to UI logging.
