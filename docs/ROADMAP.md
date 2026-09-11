# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0–P6

- [DONE] P0 foundation/discovery/security baseline.
- [DONE] P1 exact Codex 0.144.6 app-server adapter through hard delete.
- [DONE] P2 durable SQLite/idempotency/recovery kernel.
- [DONE] P3 dialogue application orchestration.
- [DONE] P4 Telegram private management.
- [DONE] P5 Telegram group routing.
- [DONE] P6 response delivery/full local orchestration — `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — real Codex acceptance / hard-delete correction

- [REJECTED / HISTORICAL] Original P7: one official P1.9 `DELETE_UNKNOWN`; forensic `5aac49bd1b8a349343db52071520beed7f95592d`. Historical thread never reused.
- [DONE] P7.C1 storage-isolation discovery — `a9900471d0599be21b1a1834301c4421d95acb29`.
- [DONE] P7.C2 confirmed-delete storage barrier — `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- [DONE] P7.C3 persistent profile + isolated state-root runtime authority — `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`.
- [DONE] P7.C4 confirmed cleanup + DELETE_UNKNOWN containment — `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`.
- [DONE] P7.C5 corrected fake hard-delete acceptance — `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- [ACCEPTED CORRECTION] ADR-0045: authenticated persistent `CODEX_HOME` may be shared; isolated mutable state/controller remain CodexControl-owned.

### P7.C6 retained-thread correction history

- [RUN 1 REJECTED / HARNESS DEFECT] `785a82e2e9bc392173ea1e910b490f84cfa590b2`: old Turn-3 approval remains `RESPONSE_UNKNOWN` and permanently non-retryable.
- [DONE / ZERO EFFECT] Turn-3 forensic `e6835e7eaff21ce6a452c24f3309269df67c82ba`.
- [DONE / ZERO EFFECT] Existing Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`.

### P7.C6 same-thread continuation preparation

- [REWORK_REQUIRED] Prep-v2 `1c9b03108bb2493fd6547a92c807397bb4c0868c`.
- [REWORK_REQUIRED] Repair-1 `821be881f1e6b04d3905080191cc0f1141799923`.
- [REWORK_REQUIRED] Repair-2 `4d98e2b6170e76534fa18274236605f77440f740`.
- [REWORK_REQUIRED] Repair-3 `2b38969c1c9a8232cb1c68efc953dae125e0e18c`.
- [REWORK_REQUIRED] Repair-4 `a55a765cdfb0d51e956045a238d4ecb5a237a5fe`.
- [REWORK_REQUIRED] Repair-5 `01994403110f19e323dffd693f226b18bdcb73c7`.
- [DONE / PREPARATION ACCEPTED] Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.

Architect acceptance:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`

One-shot execution contract:

`docs/evidence/p7c6/P7C6_REAL_SAME_THREAD_CONTINUATION_EXECUTION_CONTRACT_2026-09-11.md`

Repair-6 closes the final preparation blocker by owning the complete continuation process tree in an isolated OS session/process group and proving exact group termination/quiescence, descendant/grandchild convergence and unrelated-process survival. All prior source, latch, marker, approval, interrupt, controller, budget, delete, residual, result-channel and success-only sanitization authorities remain binding.

- [DONE / SERVER MAINTENANCE] Conservative disk cleanup reclaimed `945344512` bytes (`0.880421 GiB`) without touching P7.C6 state.
- [NEXT / AUTHORIZED ONE SHOT] **P7.C6 real same-thread continuation.** Execute exactly accepted HEAD `76a7aa24e3cfdfb12c3314a7e01691d4a943b551` / tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`. One real attempt only: retained resume → Turn 4 exact approval proof → Turn 5 exact interrupt proof → one official P1.9 delete → physical erasure and safe process-result proof. No rerun after dispatch under any outcome.
- [BLOCKED] P8 until P7.C6 real evidence is independently accepted.

## P8 — deployment packaging/rollback

[BLOCKED BY P7.C6 REAL ACCEPTANCE]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7.C6]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
