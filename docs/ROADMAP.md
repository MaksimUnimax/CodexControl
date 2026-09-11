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

- [RUN 1 REJECTED / HARNESS DEFECT] Evidence `785a82e2e9bc392173ea1e910b490f84cfa590b2`. One thread, one resume, three turns. Turn 1/2 passed persistence. Turn 3 stopped at approval. No interrupt/delete/read/list. Old approval remains `RESPONSE_UNKNOWN` and non-retryable.
- [DONE / ZERO EFFECT] Retained Turn-3 forensic `e6835e7eaff21ce6a452c24f3309269df67c82ba`: exact terminal `INTERRUPTED`, command completed, no pending persisted approval, no delayed process/sentinel.
- [DONE / ZERO EFFECT] Existing Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`: existing latch accepted as replay barrier; SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

### P7.C6 same-thread continuation preparation

- [REWORK_REQUIRED / ZERO EFFECT] Prep-v2 inert candidate `1c9b03108bb2493fd6547a92c807397bb4c0868c`.
- [REWORK_REQUIRED / ZERO EFFECT] Prep-v2 Repair-1 candidate `821be881f1e6b04d3905080191cc0f1141799923`.

Repair-1 review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR_ARCHITECT_REVIEW_2026-09-11.md`

Binding Repair-2 contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_CONTRACT_2026-09-11.md`

Repair-1 closed many earlier gaps, including source authority, structural matcher, continuation latch source binding, actual schema checks, official delete observation, success-only sanitization and explicit real-file tests. It is still not real-executable because review found remaining harness defects: legitimate retained topology is self-rejected by preflight, external-user scope is overbroad, local continuation paths are not all preflighted before first RPC, recovery journal is fail-open, timeout-sensitive tasks are not always owned through convergence, marker scanning lacks pathname revalidation, unrelated baseline is not aggregate-bounded and reconciliation ignores exact path, dynamic budget ignores unknown methods, and several critical behavioral tests are incomplete.

- [NEXT / ZERO-REAL-EFFECT] **P7.C6 prep-v2 Repair-2.** Harness/evidence only, no `src/**`, no real Codex effects. Publish the repaired candidate and stop for architect review.
- [BLOCKED] P7.C6 real same-thread continuation. No authorization until Repair-2 is independently accepted.

## P8 — deployment packaging/rollback

[BLOCKED BY P7.C6]

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
