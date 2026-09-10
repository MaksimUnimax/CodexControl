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
- [DONE] P3.5 hard-delete orchestration/fake P3 acceptance. ADR-0043/0044 later supersede the confirmed-delete storage ordering while preserving P1.9 UNKNOWN semantics.

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

- [REJECTED / HISTORICAL BLOCKER] **Original P7 under ADR-0042.** Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved material residual. No retry/read/list/manual repair occurred. The historical thread is never reused.

- [DONE] **P7.C1 — storage-isolation discovery.** Accepted `a9900471d0599be21b1a1834301c4421d95acb29`.

- [DONE] **P7.C2 — schema-v3 confirmed-delete storage barrier.** Accepted repair `80673db644962b0cc5b1a388d64cb5902bd4f46c`. Exact confirmation becomes durable `DELETE_CONFIRMED_PENDING_STORAGE` before local purge/tombstone.

- [DONE] **P7.C3 — configured persistent profile + isolated state-root runtime authority.** Accepted `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`, tree `13eea89362694da594bb2b717c037980b0df446f`. ADR-0045 supersedes only the mistaken persistent-home exclusivity interpretation; C3 isolated-root/runtime-manager ownership remains accepted.

- [DONE] **P7.C4 — confirmed cleanup + DELETE_UNKNOWN local containment.** Accepted final `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`. Schema v4 adds bounded UNKNOWN containment metadata; confirmed finalization requires CodexControl-local reservation/quiescence, crash-resumable isolated reset and persistent exact-thread gate; UNKNOWN remains official UNKNOWN and quarantined.

- [DONE] **P7.C5 — corrected fake hard-delete acceptance.** Accepted final proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`. Final full regression: 1065, zero skipped/failures/errors. Acceptance: `docs/evidence/p7c5/P7C5_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

- [ACCEPTED CORRECTION] **ADR-0045 — shared persistent CODEX_HOME with isolated CodexControl mutable state.** Existing authenticated `CODEX_HOME` may be concurrently shared by other Codex processes/applications. CodexControl owns only its own app-server child/generation, isolated state root, controller SQLite and process-local reservation. No unrelated process is killed/stopped merely because it shares the persistent home.

- [RUN 1 REJECTED / HARNESS DEFECT] **P7.C6 — renewed real T3 + corrected hard-delete acceptance.** Run-1 evidence commit `785a82e2e9bc392173ea1e910b490f84cfa590b2`; architect review: `docs/evidence/p7c6/P7C6_RUN1_ARCHITECT_REVIEW_2026-09-10.md`.

  Run 1 used `/root/.codex_second` in `SHARED_AUTHENTICATED` mode and safely reached one thread, one generation restart/resume and three turns. Turn 1/2 passed persistence proof. Turn 3 reached one approval request and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`; no interrupt, delete, thread/read or thread/list occurred. Recovery identity is retained outside Git.

  Independent review establishes two acceptance-harness defects: the C6 operator used a literal guessed-command matcher instead of the previously proven structural `EXACT_INNER|ONE_SHELL_WRAPPER` matcher with exact thread/turn/cwd/marker/sentinel relations, and the declared global one-shot ledger was only checked rather than materialized. No production P1.7/P1.8/P1.9/C3/C4/C5 defect is established.

  Published zero-effect forensic records `C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN`, so the old approval request may never be resent or reinterpreted.

- [NEXT / ZERO-REAL-EFFECT] **P7.C6 retained Turn-3 forensic.** Contract: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_FORENSIC_CONTRACT_2026-09-10.md`.

  This forensic may inspect only existing local recovery/session/process metadata and must perform zero Codex/app-server/business RPC effects. It must determine whether Run-1 Turn 3 has a durable terminal record and whether any approval/command state remains pending/running/ambiguous. `P7C6_CONTINUATION_AUTHORIZED=NO` until independent architect review of this forensic.

  Only if a safe terminal boundary is proven may the architect consider a separately frozen same-thread continuation. Any such continuation would use no new real thread, never resend the Run-1 approval request, repair the approval matcher and durable latch, and retain the still-unused single official `thread/delete` budget.

## P8 — Deployment packaging/rollback
[BLOCKED BY P7.C6] Root-owned config/secrets, systemd, install/upgrade/rollback runbooks, resource/retention guards. Reopens only after architect-accepted C6.

## P9 — server-80 live Telegram acceptance
[BLOCKED BY P7.C6] Dedicated token/private test group; T4/T5 UX/auth/restart/delete/rollback. Reopens only after architect-accepted C6.

## P10 — server-78 discovery/deployment
Repeat discovery/profile/storage/capability; dedicated deploy key/token/config; same source architecture, no fork.

## P11 — Multi-bot shared-group acceptance
Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle
Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — Final security/recovery acceptance
Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
