# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0 — Repository, architecture and governance
- [DONE] P0.1 server-80 discovery and dedicated deploy key.
- [DONE] P0.2 foundation commit `626bcd48f8719b467a565de601564a4550ead83b` verified in GitHub.
- [DONE] P0.3 installed Codex 0.144.6 capability baseline.
- [DONE] P0.4 architect V1 product/topology/state/data/security/retention/testing/governance baseline.
- [DONE] P0.5 Codex executor authority and documentation structure.

## P1 — Codex app-server adapter (no Telegram/production)
- [DONE] P1.1 exact 0.144.6 stdio protocol fixtures/types + initialize handshake. Accepted `7f013ff2950bc185d6f0991c11960311961e53a7`.
- [DONE] P1.2 child supervisor + per-profile single-flight runtime manager. Accepted `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- [DONE] P1.3 installed capability manifest/version probe + normalized safe errors. Accepted `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- [DONE] P1.4 authenticated `model/list` normalization + generation-scoped in-memory cache. Accepted `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- [DONE] P1.5 thread start/resume + ambiguity-safe profile-bound thread identity. Accepted `e7851d813944d3326b7fd9317da9e21f216557fa`.
- [DONE] P1.6 turn start + ordered completed-agent-message projection + terminal handling. Accepted `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.
- [DONE] P1.7 bidirectional server-request envelope + approval request/response port using fake operator. Accepted `bbd7445087dfb59185d49787d562637e282ba5aa`.
- [DONE] P1.8 exact active-turn interrupt + terminal reconciliation. Accepted `6d8a07b5b95ef377cf60762f4475128bdf810b22`.
- [DONE] P1.9 exact thread/delete + ambiguity-safe external deletion authority. Accepted `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
- [DONE] P1.10 T0/T1/T2 adapter acceptance; no real production conversation. Accepted `7b236f95df78a05073d67fe362ac9fff343d7c43`.

## P2 — Durable local state/idempotency
- [DONE] P2.1 secure SQLite storage kernel + historical schema-v1 bootstrap/migration/process lock. Accepted `61301fd25ff7253693f367664ce99e13dfc88446`.
- [DONE] P2.2 controller/settings/dialogue core repositories. Accepted `5187c080a7188a59989013defe7d07075662d007`.
- [DONE] P2.3 ingress dedupe + atomic control epoch/mode claim + opaque callback claims. Accepted `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- [DONE] P2.4a atomic JOB ingress + turn-job execution claims + transient payloads. Accepted `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- [DONE] P2.4b delivery segments + atomic approval callback/subject claims + bounded transient retention. Accepted `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- [DONE] P2.5 deletion claims/tombstones/error fingerprints/confirmed local purge. Accepted `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- [DONE] P2.6a bounded non-content metadata retention. Accepted `e6f59739b3091d00894d3434abb5a99e2af72885`.
- [DONE] P2.6b crash/restart/idempotency harness and final historical P2 acceptance. Accepted `9db97f0dda109b4d0c0ecfa5f167733905df2766`; full 500.
- [DONE] P2.C1 retention-compatible JOB duplicate replay correction. Accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`; full 506.
- [DONE] P2.C2 terminal authorized pre-JOB rejection + schema-v2 migration under ADR-0036. Accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.

## P3 — Dialogue application service
- [DONE] P3.1 existing-dialogue prompt admission + immutable authenticated selection + one-turn orchestration. Accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`; full 543.
- [DONE] P3.2 lazy `thread/start` + first-turn orchestration/restart fail-closed. Accepted `c484c56db007569170363b3d08c24766148c3e30`; full 566.
- [DONE] P3.3 profile/model/reasoning selection + authenticated catalog validation + settings/dialogue locks. Accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full 596.
- [DONE] P3.4 durable interrupt orchestration over P1.8 + exact active-binding registry. Accepted `6460a449f861b7b86ab664e5ff877c108715082d`; full 633.
- [DONE] P3.5 hard-delete orchestration over P1.9/P2.5 + quiescence + startup recovery + final fake P3 acceptance. Accepted `6145d262787465ac6b4a17327114211cd86e8104`; full 671.

P3 is complete at the fake/application boundary.

## P4 — Telegram private management
- [DONE] P4.1 private Telegram auth/normalization + durable private-menu dedupe + opaque callbacks + settings panel under ADR-0032. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`; full 694.
- [DONE] P4.2 private dialogue status + exact P3.4 interrupt + mandatory two-step hard-delete confirmation under ADR-0033. Accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`; full 728.
- [DONE] P4.3 final private facade/root + callback-family dispatch + diagnostics + approval projection/atomic P2.4b decisions + final fake P4 acceptance under ADR-0034. Accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; final full 762.

P4 is complete at the fake/application private-management boundary.

## P5 — Telegram group routing
- [DONE] P5.1 shared immutable fleet manifest + persistent reply keyboard + fail-closed group normalization/auth + durable activation/all-sleep routing under ADR-0035. Accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`; full 777.
- [DONE] P5.2 serialized ordinary group TEXT admission under ADR-0037 with short lock, no queue, durable stale/SLEEP/BUSY handling and accepted P3 delegation. Accepted `345c48722c4faa03be19d38b6f07304276075f64`; full 841.
- [DONE] P5.3 fleet-status identity/mismatch visibility + final fake multi-controller acceptance under ADR-0038. Accepted `c23d9356e7033ce44a62933f7749250433d49f61`; final P5 full 860.

P5 is complete at the fake/application group-routing boundary.

## P6 — Response delivery/full local orchestration
- [DONE] **P6.1** deterministic successful-response segmentation + transient DISPLAY materialization + accepted P2.4b durable one-attempt delivery under ADR-0039 and architect bounded-segmentation addendum. Accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; full 900. Acceptance: `docs/evidence/p6/P6_1_ARCHITECT_ACCEPTANCE_2026-09-08.md`.
- [NEXT / AUTHORITY FROZEN] **P6.2** durable live approval operator + owned exact P1.7 response under ADR-0040: per-approval EXPIRED/CANCELLED terminalizer, wake-only decision signal, exact running-turn binding, PENDING-before-wait, real P4.3 durable Allow/Deny, and one owned P1.7 response attempt. Restart never reconstructs wire authority. No P3 rewrite/live Telegram.
- [LATER] **P6.3** full local fake orchestration/recovery: server-request dequeue/turn concurrency, acknowledgement/progress composition, delivery-job startup discovery, group/private composition and final P6 acceptance.

P6 is NOT complete until P6.2 and P6.3 are independently accepted.

## P7 — Real Codex isolated acceptance / hard-delete proof
Disposable server-80 thread, authenticated eligibility, multi-turn/interrupt/approval, thread/delete storage measurement across sessions/history/state/logs, architecture gate on shared profiles vs dedicated homes.

## P8 — Deployment packaging/rollback
Root-owned config/secrets, systemd, install/upgrade/rollback runbooks, resource/retention guards; production fleet manifest/TOML materialization is wired here from accepted P5 domain/application contracts.

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
