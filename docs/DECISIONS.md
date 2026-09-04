# Decisions

Append-only ADR-like record.

- D001 — bot-per-server; no mandatory central controller.
- D002 — common private Telegram supergroup.
- D003 — ACTIVE/SLEEP controls ordinary-message routing.
- D004 — separate private settings surface.
- D005 — explicit `CODEX_HOME` profile selection.
- D006 — real persistent Codex dialogue/thread.
- D007 — mandatory hard-delete lifecycle.
- D008 — no conversation contents in journald.
- D009 — no public Codex listener; prefer stdio.
- D010 — configuration-driven server-N extensibility.
- D011 — Codex 0.144.6 app-server is the primary adapter because its installed schema exposes thread deletion and runtime model metadata; `codex exec` is not sufficient proof for hard deletion.
