# Architecture decisions index

Architect-owned; individual records under `docs/adr/`.

- ADR-0001 autonomous controller/bot per server; no mandatory central runtime.
- ADR-0002 human-originated persistent group keyboard routes fleet.
- ADR-0003 restart always SLEEP; group message order is control epoch.
- ADR-0004 app-server stdio primary; one child per profile max.
- ADR-0005 dialogue profile immutable; model/effort only between turns.
- ADR-0006 V1 root controller; Telegram approval bridge compensates privileged execution.
- ADR-0007 local SQLite metadata/state; minimize duplicate conversation content.
- ADR-0008 hard delete = official thread/delete + local purge + measured storage proof.
- ADR-0009 no content in journald; ambiguous effects UNKNOWN/no blind retry.
- ADR-0010 configuration-driven fleet/server-N.
- ADR-0011 one live dialogue/one running turn; no delayed prompt queue.
- ADR-0012 architect-led development; Codex implementation executor only.
- ADR-0013 P1.5 validates reasoning effort but never guesses an opaque `thread/start.config` key; exact effort becomes a wire input at P1.6 `turn/start`.
