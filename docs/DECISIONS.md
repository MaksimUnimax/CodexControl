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
- ADR-0014 Codex 0.144.6 permissions approval DENY is an empty `GrantedPermissionProfile` with turn scope; ALLOW echoes only exact validated request-derived permissions with turn scope, never session-wide/broader grants.
- ADR-0015 P1.8 `turn/interrupt` targets only the exact active P1.6 turn on its captured runtime, reuses the existing terminal collector, and resolves ambiguity only from exact terminal reconciliation; no reacquire or blind retry.
- ADR-0016 P1.9 `thread/delete` treats only schema-valid success as confirmed external deletion authority; every dispatched non-success is DELETE_UNKNOWN because exact Codex deletion can partially mutate thread-store/state before an error. No retry/read guessing or competing `thread/deleted` notification consumer.
