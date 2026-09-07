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
- [DONE] P1.8 exact active-turn interrupt + terminal reconciliation through the existing P1.6 collector. Accepted implementation after one recovered repair: `6d8a07b5b95ef377cf60762f4475128bdf810b22`.
- [DONE] P1.9 exact thread/delete + ambiguity-safe external deletion authority. Accepted implementation: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
- [DONE] P1.10 T0/T1/T2 adapter acceptance; no real production conversation. Accepted proof commit: `7b236f95df78a05073d67fe362ac9fff343d7c43`.

## P2 — Durable local state/idempotency
- [DONE] P2.1 secure SQLite storage kernel + exact schema-v1 bootstrap/migration + process lock + owned transaction primitive. Accepted implementation after two repair reviews: `61301fd25ff7253693f367664ce99e13dfc88446`.
- [DONE] P2.2 controller/settings/dialogue core repositories + optimistic versions and create-intent state claims. Accepted implementation/proof HEAD: `5187c080a7188a59989013defe7d07075662d007`.
- [DONE] P2.3 ingress dedupe + atomic control epoch/mode claim + opaque callback-action one-time claims. Accepted implementation after one repair review: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- [DONE] P2.4a atomic JOB ingress + turn-job execution claims + bounded transient payload repository. Accepted implementation after one repair review: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- [DONE] P2.4b delivery segments + atomic approval-subject callback claims + bounded transient retention/sanitization. Accepted implementation after two repair reviews: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- [DONE] P2.5 deletion state claims + deletion tombstones + sanitized error fingerprints + confirmed hard-delete local purge/finalization transaction. Accepted implementation after one repair review: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- [DONE] P2.6a bounded non-content metadata retention for terminal jobs/ingress/callbacks/tombstones/errors. Accepted implementation after one repair review: `e6f59739b3091d00894d3434abb5a99e2af72885`.
- [DONE] P2.6b crash/restart/idempotency harness and final P2 acceptance. Historical accepted proof after one proof-only repair: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; full suite 500.
- [DONE] P2.C1 retention-compatible JOB duplicate replay correction under ADR-0027. Accepted implementation `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`; corrected full suite 506.

## P3 — Dialogue application service
- [DONE] P3.1 existing-dialogue prompt admission + immutable authenticated selection + one-turn Codex orchestration + terminal capture. Accepted after corrected P2.C1 base plus one proof-only repair: `9e0a86b311bb63d6a36a4641cb588321987e1550`; final full suite 543.
- [DONE] P3.2 lazy `thread/start` + first-turn orchestration and fail-closed create/restart boundary under ADR-0028. Accepted after one production repair: `c484c56db007569170363b3d08c24766148c3e30`; final full suite 566.
- [DONE] P3.3 profile/model/reasoning settings selection + authenticated catalog validation + atomic dialogue/settings locks under ADR-0029. Accepted after one repair: `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; final full suite 596.
- [DONE] P3.4 durable interrupt orchestration over P1.8 + exact active-binding registry + interrupt/natural-terminal reconciliation + startup INTERRUPTING recovery under ADR-0030. Accepted after one repair: `6460a449f861b7b86ab664e5ff877c108715082d`; final full suite 633.
- [DONE] P3.5 hard-delete orchestration over P1.9/P2.5 + exact running-turn quiescence + final no-P1 startup recovery + final P3 fake/application acceptance under ADR-0031. Accepted after four architect repair reviews: `6145d262787465ac6b4a17327114211cd86e8104`; final full suite 671.

P3 is complete at the fake/application boundary. Acceptance authority: `docs/evidence/p3/P3_5_ARCHITECT_ACCEPTANCE_2026-09-07.md`.

## P4 — Telegram private management
- [DONE] P4.1 private Telegram auth/normalization + durable private-menu dedupe + opaque callbacks + profile/model/reasoning settings panel under ADR-0032. Accepted after one architect repair: `5a7db46c6e06662c379149c454c06003d48feb30`; final full suite 694. Acceptance authority: `docs/evidence/p4/P4_1_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- [DONE] P4.2 private server/dialogue status + exact P3.4 interrupt + mandatory two-step confirmed P3.5 hard delete under ADR-0033. Accepted after two architect repair reviews: `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; final full suite 728. Acceptance authority: `docs/evidence/p4/P4_2_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- [NEXT / AUTHORITY FROZEN] P4.3 final private facade/root + non-consuming callback-family dispatch + diagnostics/last sanitized error + approval projection/atomic P2.4b decision callbacks + final fake private-management acceptance under ADR-0034. No P1.7 external approval response, delivery, private ACTIVE, group routing or live Telegram belongs to this slice.

No P4 live Telegram/network acceptance occurs here; T4/T5 live validation remains later roadmap authority.

## P5 — Telegram group routing
Persistent fleet keyboard, serialized group updates, activation epoch/restart-SLEEP, SLEEP ignore, ACTIVE prompt ingress, BUSY, fleet status/version safeguards.

## P6 — Response delivery/full local orchestration
Progress/edit path, deterministic chunk/outbox, ambiguous send handling, end-to-end fake recovery, plus live P1.7 approval-request persistence/wait/response coordination over the P4.3 UI decision boundary.

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
