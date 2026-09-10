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

- [DONE] **P7.C3 — dedicated profile + isolated state-root runtime authority.** Accepted `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`, tree `13eea89362694da594bb2b717c037980b0df446f`.

- [DONE] **P7.C4 — confirmed cleanup + DELETE_UNKNOWN local containment.** Accepted final `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`. Schema v4 adds bounded UNKNOWN containment metadata; confirmed finalization requires reservation/quiescence, crash-resumable isolated reset and persistent exact-thread gate; UNKNOWN remains official UNKNOWN and quarantined.

- [DONE] **P7.C5 — corrected fake hard-delete acceptance.** Accepted final proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`. Historical stop `581a31e9a450230eed50bad6c247159898d72f7f` was an architect-contract defect, not production. Corrected C5 separates the production exact-thread gate from a test-only marker oracle and proves isolated storage-family cleanup, persistent blockers, UNKNOWN containment, crash/restart, concurrency/cancellation, no-P1 replay, controller authority and unrelated session/history baselines. Final full regression: 1065, zero skipped/failures/errors. Acceptance: `docs/evidence/p7c5/P7C5_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

- [NEXT / REAL-EFFECT ONE-SHOT CONTRACT FROZEN] **P7.C6 — renewed isolated real T3 + corrected hard-delete acceptance.** Contract: `docs/evidence/p7c6/P7C6_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`.

  C6 may use exactly one new disposable real thread and one official `thread/delete`. It must use an explicitly designated already-authenticated CodexControl-dedicated persistent home plus a fresh isolated state root and separate run-owned controller DB. It must exercise real persisted multi-turn across runtime restart, one approval ALLOW path, one interrupt, pre-delete physical observation, then the complete C2/C3/C4 application delete path.

  PASS requires exact real `DELETE_CONFIRMED`, final local `DELETED`/tombstone, zero target thread-ID residual, zero known synthetic marker residual across measured dialogue-bearing persistent/isolated families, preserved unrelated baseline, mount/alias preflight PASS and green ordinary regression. `DELETE_UNKNOWN`, residual, inconclusive proof, profile-authority failure or mount-alias uncertainty blocks acceptance and is never retried automatically.

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
