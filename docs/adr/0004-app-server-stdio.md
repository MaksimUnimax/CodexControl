# ADR-0004 — Codex app-server over stdio

Status: Accepted

Installed Codex 0.144.6 app-server is V1 primary integration because it exposes model discovery, persistent thread lifecycle, turn events/interrupt and hard thread delete. Controller owns stdio children keyed by explicit profile; no public app-server listener/WebSocket dependency.
