# ADR-0001 — Autonomous controller per server

Status: Accepted

Each physical server runs the same controller code with its own Telegram bot token and local state. No mandatory central runtime/shared DB exists. Failure of one server must not disable another. Cross-server selection uses human Telegram controls/shared configuration, not RPC.
