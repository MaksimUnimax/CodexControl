# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0 — Repository, architecture and governance
- [DONE] P0.1–P0.5 repository foundation, server-80 discovery, installed 0.144.6 authority, V1 architecture/security and architect/Codex governance.

## P1 — Codex app-server adapter
- [DONE] P1.1–P1.10 exact 0.144.6 stdio protocol, runtime manager, capability gate, model/list, thread start/resume, turns, approvals, interrupt, ambiguity-safe thread/delete and adapter acceptance.

## P2 — Durable local state/idempotency
- [DONE] P2.1–P2.6b plus P2.C1/P2.C2: secure SQLite kernel, schema authorities, repositories, ingress/idempotency, turn jobs, delivery/approval, deletion/tombstones, retention and crash/restart acceptance.

## P3 — Dialogue application service
- [DONE] P3.1–P3.5 existing/lazy dialogue orchestration, settings, interrupt and hard-delete application semantics. ADR-0043/0044 later supersede confirmed-delete storage ordering while preserving P1.9 UNKNOWN semantics.

## P4 — Telegram private management
- [DONE] P4.1–P4.3 private auth/menu/settings, dialogue control and final private facade/approval projection.

## P5 — Telegram group routing
- [DONE] P5.1–P5.3 fleet activation/routing, serialized TEXT admission and final fake fleet-status acceptance.

## P6 — Response delivery/full local orchestration
- [DONE] P6.1–P6.3 deterministic response delivery, durable live approval operator and final local orchestration/fake P6 acceptance. Accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — Real Codex acceptance and hard-delete correction lane

- [REJECTED / HISTORICAL BLOCKER] **Original P7 under ADR-0042.** Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved material residual. Historical thread is never reused.

- [DONE] **P7.C1 — storage-isolation discovery.** Accepted `a9900471d0599be21b1a1834301c4421d95acb29`.
- [DONE] **P7.C2 — schema-v3 confirmed-delete storage barrier.** Accepted `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- [DONE] **P7.C3 — configured persistent profile + isolated state-root runtime authority.** Accepted `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`, tree `13eea89362694da594bb2b717c037980b0df446f`.
- [DONE] **P7.C4 — confirmed cleanup + DELETE_UNKNOWN local containment.** Accepted `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.
- [DONE] **P7.C5 — corrected fake hard-delete acceptance.** Accepted `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`; full regression 1065, zero failures/errors.

- [ACCEPTED CORRECTION] **ADR-0045 — shared persistent CODEX_HOME.** Existing authenticated persistent `CODEX_HOME` may be concurrently shared. CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation; unrelated shared-home processes are not stopped.

- [RUN 1 REJECTED / HARNESS DEFECT] **P7.C6 real Run 1.** Evidence `785a82e2e9bc392173ea1e910b490f84cfa590b2`. One real thread, one resume and three turns occurred. Turn 1/2 proved persistence; Turn 3 reached one approval request and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No P1.8 interrupt, delete, thread/read or thread/list occurred. Run-1 approval result remains `RESPONSE_UNKNOWN`; the old request is permanently non-retryable. Architect review established harness/recovery defects but no production defect.

- [DONE / ZERO-REAL-EFFECT FORENSIC] **P7.C6 retained Turn-3 forensic.** Accepted `e6835e7eaff21ce6a452c24f3309269df67c82ba`. Exact Turn 3 is durably terminal `INTERRUPTED`; its command item is `COMPLETED`; no persisted approval request/decision/response remains; no delayed process or sentinel remains. Old Turn-3 approval remains closed.

- [DONE / ZERO-REAL-EFFECT FORENSIC] **P7.C6 existing Run-1 latch forensic.** Accepted `c308c765d9915844fce97d1d1f6c933e302a75aa`. Existing `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` is architect-accepted as the safe Run-1 consumed replay barrier. Accepted SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`. It must not be overwritten or normalized. `RUN1_GLOBAL_ONE_SHOT_LATCH=ACCEPTED_EXISTING_SAFE`.

- [NEXT / ZERO-REAL-EFFECT] **P7.C6 same-thread continuation preparation resumes after accepted latch.** Base preparation contract remains `docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_CONTRACT_2026-09-10.md` plus architect latch acceptance `docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

  Skip only the obsolete Run-1 latch-create/replace step. Preparation must re-check the accepted latch read-only, recover exactly the three Run-1 markers into root-only recovery supplement, validate retained isolated/controller topology, build a new gated same-thread harness, implement/test strict structural approval matching and a distinct continuation latch, prove zero new-thread path, and run only gate-disabled/offline/fake regression.

  `P7C6_SAME_THREAD_CONTINUATION_PREP_AUTHORIZED=YES`.

  `P7C6_REAL_CONTINUATION_AUTHORIZED=NO` until the preparation commit receives independent architect review.

## P8 — Deployment packaging/rollback
[BLOCKED BY P7.C6] Reopens only after architect-accepted C6.

## P9 — server-80 live Telegram acceptance
[BLOCKED BY P7.C6] Reopens only after architect-accepted C6.

## P10 — server-78 discovery/deployment
Repeat discovery/profile/storage/capability; dedicated deploy key/token/config; same source architecture, no fork.

## P11 — Multi-bot shared-group acceptance
Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle
Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — Final security/recovery acceptance
Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
