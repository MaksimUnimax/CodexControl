# Architecture baseline — V1

Status: **AUTHORITATIVE / FROZEN FOR IMPLEMENTATION**  
Date: 2026-09-04  
Foundation parent: `626bcd48f8719b467a565de601564a4550ead83b`

## Authority
Architect-owned normative documents are product requirements, architecture, domain/state/data contracts, Codex/Telegram contracts, security/threat/session/retention/config/testing/governance, ADRs, roadmap and current-work authority. Codex implements them; it does not amend or advance them.

## Frozen V1 invariants
1. One autonomous controller/bot token per physical server; no mandatory central runtime.
2. Common private supergroup for work; private chat with each bot for settings.
3. Fleet selection uses human-originated group controls visible to all controllers.
4. Every process start/restart comes up effective `SLEEP`; saved `ACTIVE` is never auto-restored.
5. Exact operator and chat allowlists fail closed.
6. One active dialogue and one running turn per controller in V1.
7. Dialogue `CODEX_HOME` profile is immutable for its lifetime.
8. Model/reasoning may change only between turns; every turn captures an immutable execution snapshot.
9. Prompts received while busy are rejected, never silently queued.
10. Codex app-server over stdio is primary; no public Codex listener.
11. V1 controller intentionally runs as root because the product performs root maintenance and existing profiles are root-owned.
12. Codex approval requests must be bridged to the operator; blanket silent privileged approval is not the production default.
13. Control-group updates are serialized by Telegram chat/message order.
14. `SLEEP` ordinary messages are terminally ignored/deduplicated and can never execute after later activation.
15. Ambiguous external effects are `UNKNOWN`; no blind retry.
16. Conversation content never enters journald/system logs.
17. Hard delete means official Codex thread deletion plus CodexControl content/job/temp purge; archive/forget alone is insufficient.
18. Hard-delete storage behaviour must be measured in an isolated acceptance before server-80 production acceptance.
19. Adding/removing server-N is configuration-driven, not a source fork.
20. Any implementation violating an invariant fails acceptance even if tests otherwise pass.
