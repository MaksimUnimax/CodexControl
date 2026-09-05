# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0 — Repository, architecture and governance
- [DONE] P0.1 server-80 discovery and dedicated deploy key.
- [DONE] P0.2 foundation commit `626bcd48f8719b467a565de601564a4550ead83b` verified in GitHub.
- [DONE] P0.3 installed Codex 0.144.6 capability baseline.
- [DONE] P0.4 architect V1 product/topology/state/data/security/retention/testing/governance baseline.
- [DONE] P0.5 Codex executor authority and documentation structure.

## P1 — Codex app-server adapter (no Telegram/production)
- [DONE] P1.1 exact 0.144.6 stdio protocol fixtures/types + initialize handshake. Accepted implementation: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- [DONE] P1.2 child supervisor + per-profile single-flight runtime manager. Accepted implementation after two repair reviews: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- [DONE] P1.3 installed capability manifest/version probe + normalized safe errors. Accepted implementation after three repair reviews: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- [DONE] P1.4 authenticated `model/list` normalization + generation-scoped in-memory cache. Accepted implementation after one repair review: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- [DONE] P1.5 thread start/resume + ambiguity-safe profile-bound thread identity. Accepted implementation after two repair reviews: `e7851d813944d3326b7fd9317da9e21f216557fa`.
- [DONE] P1.6 turn start + ordered completed-agent-message projection + terminal handling. Accepted implementation after two repair reviews: `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.
- [DONE] P1.7 bidirectional server-request envelope + approval request/response port using fake operator. Accepted implementation/proof HEAD after iterative repair review: `bbd7445087dfb59185d49787d562637e282ba5aa`.
- [DONE] P1.8 exact active-turn interrupt + terminal reconciliation through the existing P1.6 collector. Accepted implementation after one recovered repair: `6d8a07b5b95ef377124c5bff228fad643`.
- [DONE] P1.9 exact thread/delete + ambiguity-safe external deletion authority. Accepted implementation: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
- [DONE] P1.10 T0/T1/T2 adapter acceptance; no real production conversation. Accepted proof commit: `7b236f95df78a05073d67fe362ac9fff343d7c43`.

## P2 — Durable local state/idempotency
- [DONE] P2.1 secure SQLite storage kernel + exact schema-v1 bootstrap/migration + process lock + owned transaction primitive. Accepted implementation after two repair reviews: `61301fd25ff7253693f367664ce99e13dfc88446`.
- [NEXT] P2.2 controller/settings/dialogue core repositories + optimistic versions and create-intent state claims.
- [PLANNED] P2.3 ingress dedupe + control epoch + opaque callback-action atomic claims.
- [PLANNED] P2.4 turn jobs + transient payloads + delivery segments + approvals repositories and bounded retention/sanitization.
- [PLANNED] P2.5 deletion tombstones + error fingerprints + confirmed hard-delete local purge/finalization transaction.
- [PLANNED] P2.6 crash/restart/idempotency harness and P2 acceptance.

## P3 — Dialogue application service
Lazy create, one-dialogue invariant, immutable turn claims; BUSY/no queue; model/effort idle mutation/profile lock; interrupt/recovery; hard-delete orchestration over ports.

## P4 — Telegram private management
Authorization edge, panel, profile/model/reasoning/status, dialogue/delete/interrupt, opaque callbacks, approval UI, tap-able menu fallback.

## P5 — Telegram group routing
Persistent fleet keyboard, serialized group updates, activation epoch/restart-SLEEP, SLEEP ignore, ACTIVE prompt ingress, BUSY, fleet status/version safeguards.

## P6 — Response delivery/full local orchestration
Progress/edit path, deterministic chunk/outbox, ambiguous send handling, end-to-end fake recovery.

## P7 — Real Codex isolated acceptance / hard-delete proof
Disposable server-80 thread, authenticated eligibility, multi-turn/interrupt/approval, thread/delete storage measurement across sessions/history/state/logs, architecture gate on shared profiles vs dedicated homes.

## P8 — Deployment packaging/rollback
Root-owned config/secrets, systemd, install/upgrade/rollback runbooks, resource/retention guards.

## P9 — server-80 live Telegram acceptance
Dedicated token/private test group; T4/T5 UX/auth/restart/delete/rollback; promote exact accepted SHA.

## P10 — server-78 discovery/deployment
Repeat discovery/profile/storage/capability; dedicated deploy key/token/config; same source architecture, no fork.

## P11 — Multi-bot shared-group acceptance
Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle
Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — Final security/recovery acceptance
Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, V1 checkpoint.
