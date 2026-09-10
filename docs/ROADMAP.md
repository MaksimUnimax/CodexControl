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
- [DONE] P2.3 ingress dedupe + atomic control epoch/mode claims + opaque callback claims. Accepted `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- [DONE] P2.4a atomic JOB ingress + turn-job execution claims + transient payloads. Accepted `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- [DONE] P2.4b delivery/approval/transient-retention authority. Accepted `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- [DONE] P2.5 deletion claims/tombstones/error fingerprints/confirmed local purge. Accepted `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- [DONE] P2.6a bounded non-content metadata retention. Accepted `e6f59739b3091d00894d3434abb5a99e2af72885`.
- [DONE] P2.6b final historical P2 crash/restart/idempotency acceptance. Accepted `9db97f0dda109b4d0c0ecfa5f167733905df2766`.
- [DONE] P2.C1 retention-compatible JOB duplicate replay correction. Accepted `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- [DONE] P2.C2 schema-v2 terminal pre-JOB rejection correction. Accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`.

## P3 — Dialogue application service
- [DONE] P3.1 existing-dialogue orchestration. Accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`.
- [DONE] P3.2 lazy thread creation. Accepted `c484c56db007569170363b3d08c24766148c3e30`.
- [DONE] P3.3 settings selection. Accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`.
- [DONE] P3.4 durable interrupt. Accepted `6460a449f861b7b86ab664e5ff877c108715082d`.
- [DONE] P3.5 hard-delete orchestration/fake P3 acceptance. Accepted `6145d262787465ac6b4a17327114211cd86e8104`.

## P4 — Telegram private management
- [DONE] P4.1 private auth/menu/settings. Accepted `5a7db46c6e06662c379149c454c06003d48feb30`.
- [DONE] P4.2 dialogue control + two-step delete confirmation. Accepted `a5a8ee6773936b1dcbb777e36ffa33519cd8ab39`.
- [DONE] P4.3 final private facade/approval projection. Accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`.

## P5 — Telegram group routing
- [DONE] P5.1 fleet manifest/activation routing. Accepted `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`.
- [DONE] P5.2 serialized ordinary TEXT admission. Accepted `345c48722c4faa03be19d38b6f07304276075f64`.
- [DONE] P5.3 fleet-status/final fake P5 acceptance. Accepted `c23d9356e7033ce44a62933f7749250433d49f61`.

## P6 — Response delivery/full local orchestration
- [DONE] P6.1 deterministic response delivery. Accepted `51902dcbd743cd91ad209cd96879b4ad45a26a9e`.
- [DONE] P6.2 durable live approval operator. Accepted `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`.
- [DONE] P6.3 final local orchestration/fake P6 acceptance. Accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — Real Codex acceptance and hard-delete correction lane

- [REJECTED / ARCHITECTURE BLOCKED] **Original P7 under ADR-0042.** One official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved material residual. No retry/read/list/manual repair occurred.

- [DONE] **P7.C1 — storage-isolation discovery.** Accepted `a9900471d0599be21b1a1834301c4421d95acb29`.

- [DONE] **P7.C2 — schema-v3 confirmed-delete storage barrier.** Accepted candidate/repair `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc` -> `80673db644962b0cc5b1a388d64cb5902bd4f46c`; exact confirmation becomes `DELETE_CONFIRMED_PENDING_STORAGE` before purge/tombstone.

- [DONE] **P7.C3 — dedicated profile + isolated state-root runtime authority.** Accepted final `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`; exact 0.144.6 routing/capability gate, descriptor path authority, profile reservation/quiescence and bounded root lifecycle.

- [DONE] **P7.C4 — confirmed cleanup + DELETE_UNKNOWN local containment.** Accepted lineage `70cdf0edc3f319c0254313eabc5d3c56c2f9ef16` -> `fe646af1487d13571337e605641ecc86dbb1f6c7` -> final `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`. Schema v4 adds bounded UNKNOWN containment metadata. Confirmed finalization requires exact reservation/quiescence, crash-resumable isolated payload reset, persistent sessions/history gate, then finalizer. UNKNOWN remains official UNKNOWN, retains binding/tombstone absence and quarantines the profile. C4 coordinator is bound to the actual protected controller SQLite. Final executor regression: 1050, 0 skipped/failures/errors. Acceptance: `docs/evidence/p7c4/P7C4_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

- [NEXT / CONTRACT FROZEN] **P7.C5 — corrected fake hard-delete acceptance.** Proof-only tests/evidence across accepted C2/C3/C4: complete synthetic marker/path-family coverage, confirmed/UNKNOWN matrices, both isolated-subtree crash points, restart/replay/no-P1 duplication, cancellation/concurrency, unrelated-baseline/controller preservation, scanner credential/alias defenses and bounded mount/namespace risk analysis. Contract: `docs/evidence/p7c5/P7C5_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`. A production defect causes STOP; normal C5 does not edit production source.

- [BLOCKED BY C5] **P7.C6 — renewed isolated real T3 + one-delete hard-delete acceptance.** Must be separately authorized after C5 architect acceptance. PASS requires exact real `DELETE_CONFIRMED`, complete corrected local cleanup, zero synthetic material/active thread residual, preserved unrelated baseline and green ordinary regression.

## P8 — Deployment packaging/rollback
[BLOCKED BY P7.C6] Root-owned config/secrets, systemd, install/upgrade/rollback runbooks, resource/retention guards; production configuration is wired only after renewed P7 acceptance.

## P9 — server-80 live Telegram acceptance
[BLOCKED BY P7.C6] Dedicated token/private test group; T4/T5 UX/auth/restart/delete/rollback; promote only an exact accepted post-P7 SHA.

## P10 — server-78 discovery/deployment
Repeat discovery/profile/storage/capability; dedicated deploy key/token/config; same source architecture, no fork.

## P11 — Multi-bot shared-group acceptance
Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle
Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — Final security/recovery acceptance
Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, V1 checkpoint.