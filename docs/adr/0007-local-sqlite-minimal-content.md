# ADR-0007 — Local SQLite and minimal content

Status: Accepted

Each controller uses local SQLite for exact-once ingress, state machines, callbacks, jobs and delivery. Codex thread is conversation-history authority. Controller stores prompt/response content only transiently for crash-safe execution/delivery and purges it on retention/delete; no second permanent transcript.
