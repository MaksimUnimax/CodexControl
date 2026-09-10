# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0 — Repository, architecture and governance
- [DONE] P0.1 server-80 discovery and dedicated deploy key.
- [DONE] P0.2 foundation.
- [DONE] P0.3 installed Codex 0.144.6 capability baseline.
- [DONE] P0.4 V1 architecture/security baseline.
- [DONE] P0.5 architect/Codex execution governance.

## P1 — Codex app-server adapter
- [DONE] P1.1–P1.10 exact 0.144.6 stdio protocol, runtime manager, capability gate, model/list, thread start/resume, turns, approvals, interrupt, ambiguity-safe thread/delete and adapter acceptance.

## P2 — Durable local state/idempotency
- [DONE] P2.1–P2.6b plus P2.C1/P2.C2: secure SQLite kernel, schema authorities, repositories, ingress/idempotency, turn jobs, delivery/approval, deletion/tombstones, retention and crash/restart acceptance.

## P3 — Dialogue application service
- [DONE] P3.1 existing-dialogue turn orchestration.
- [DONE] P3.2 lazy thread creation.
- [DONE] P3.3 settings selection.
- [DONE] P3.4 durable interrupt.
- [DONE] P3.5 hard-delete orchestration/fake P3 acceptance. ADR-0043/0044 later supersede confirmed-delete storage ordering while preserving P1.9 UNKNOWN semantics.

## P4 — Telegram private management
- [DONE] P4.1 private auth/menu/settings.
- [DONE] P4.2 dialogue control/two-step delete confirmation.
- [DONE] P4.3 final private facade/approval projection.

## P5 — Telegram group routing
- [DONE] P5.1 fleet manifest/activation routing.
- [DONE] P5.2 serialized ordinary TEXT admission.
- [DONE] P5.3 fleet-status/final fake P5 acceptance.

## P6 — Response delivery/full local orchestration
- [DONE] P6.1 deterministic response delivery.
- [DONE] P6.2 durable live approval operator.
- [DONE] P6.3 final local orchestration/fake P6 acceptance. Accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — Real Codex acceptance and hard-delete correction lane

- [REJECTED / HISTORICAL BLOCKER] **Original P7 under ADR-0042.** Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved material residual. No retry/read/list/manual repair occurred. Historical thread never reused.

- [DONE] **P7.C1 — storage-isolation discovery.** Accepted `a9900471d0599be21b1a1834301c4421d95acb29`.

- [DONE] **P7.C2 — schema-v3 confirmed-delete storage barrier.** Accepted `80673db644962b0cc5b1a388d64cb5902bd4f46c`.

- [DONE] **P7.C3 — configured persistent profile + isolated state-root runtime authority.** Accepted `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`, tree `13eea89362694da594bb2b717c037980b0df446f`.

- [DONE] **P7.C4 — confirmed cleanup + DELETE_UNKNOWN local containment.** Accepted `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.

- [DONE] **P7.C5 — corrected fake hard-delete acceptance.** Accepted `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`; full regression 1065, zero failures/errors.

- [ACCEPTED CORRECTION] **ADR-0045 — shared persistent CODEX_HOME.** Existing authenticated persistent `CODEX_HOME` may be concurrently shared. CodexControl owns only its own app-server child/generation, isolated state root, controller SQLite and process-local reservation; unrelated shared-home processes are not stopped.

- [RUN 1 REJECTED / HARNESS DEFECT] **P7.C6 real Run 1.** Evidence `785a82e2e9bc392173ea1e910b490f84cfa590b2`. One real thread, one resume and three turns occurred. Turn 1/2 proved persistence; Turn 3 reached one approval request and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No P1.8 interrupt, delete, thread/read or thread/list occurred. Run-1 approval result remains `RESPONSE_UNKNOWN`; old request is permanently non-retryable.

  Architect review established three harness/recovery defects without establishing any production defect: literal/under-bound approval matcher; declared host-level one-shot latch never materialized; failure-path ledger failed to retain Run-1 synthetic marker plaintext needed for final all-marker erasure proof.

- [DONE / ZERO-REAL-EFFECT FORENSIC] **P7.C6 retained Turn-3 forensic.** Accepted commit `e6835e7eaff21ce6a452c24f3309269df67c82ba`. Exact Turn 3 is durably terminal `INTERRUPTED`; one command item is `COMPLETED`; no persisted approval request/decision/response remains; no delayed process or sentinel remains; zero scan/parse errors. The persisted command is outside the historical safe approval grammar (`OTHER/TOKEN_MISMATCH`), so the old approval can never be retroactively accepted. The retained thread is a safe candidate for a new same-thread turn after harness preparation.

- [NEXT / ZERO-REAL-EFFECT] **P7.C6 same-thread continuation preparation.** Contract: `docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_CONTRACT_2026-09-10.md`.

  Preparation must not perform any Codex business RPC. It closes the Run-1 latch hole, reconstructs exactly the three Run-1 synthetic marker values from the exact retained target artifact into a root-only recovery supplement, validates the retained isolated/controller topology, implements and tests the historical structural approval relation, implements/tests a separate continuation one-shot latch, and materializes a gated same-thread continuation harness.

  The prepared future continuation contains no new-thread path. If later independently authorized, it may add at most one retained-thread resume, two new turns, one new distinct approval response for the new approval-proof turn, one P1.8 interrupt for the interrupt-proof turn, and the still-unused cumulative single official `thread/delete` through the corrected application path.

  `P7C6_REAL_CONTINUATION_AUTHORIZED=NO` until independent architect review of the preparation commit.

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
