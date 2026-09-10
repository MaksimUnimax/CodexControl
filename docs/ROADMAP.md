# CodexControl roadmap

Status authority: architect only. `[DONE]` means architect-verified GitHub evidence plus required acceptance.

## P0–P6

- [DONE] P0 foundation/discovery/security baseline.
- [DONE] P1 exact Codex 0.144.6 app-server adapter through hard delete.
- [DONE] P2 durable SQLite/idempotency/recovery kernel.
- [DONE] P3 dialogue application orchestration.
- [DONE] P4 Telegram private management.
- [DONE] P5 Telegram group routing.
- [DONE] P6 response delivery/full local orchestration. Accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`.

## P7 — real Codex acceptance / hard-delete correction

- [REJECTED / HISTORICAL] Original P7: one official P1.9 `DELETE_UNKNOWN`; forensic `5aac49bd1b8a349343db52071520beed7f95592d`. Historical thread never reused.
- [DONE] P7.C1 storage-isolation discovery — `a9900471d0599be21b1a1834301c4421d95acb29`.
- [DONE] P7.C2 schema-v3 confirmed-delete storage barrier — `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- [DONE] P7.C3 configured persistent profile + isolated state-root runtime authority — `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`.
- [DONE] P7.C4 confirmed cleanup + DELETE_UNKNOWN local containment — `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`.
- [DONE] P7.C5 corrected fake hard-delete acceptance — `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- [ACCEPTED CORRECTION] ADR-0045: persistent authenticated `CODEX_HOME` may be shared; isolated mutable state/controller remain CodexControl-owned.

### P7.C6 history

- [RUN 1 REJECTED / HARNESS DEFECT] Evidence `785a82e2e9bc392173ea1e910b490f84cfa590b2`. One real thread, one resume, three turns. Turn 1/2 passed persistence. Turn 3 reached approval and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No interrupt/delete/read/list. Old approval remains `RESPONSE_UNKNOWN` and non-retryable.
- [DONE / ZERO EFFECT] Retained Turn-3 forensic `e6835e7eaff21ce6a452c24f3309269df67c82ba`: exact terminal `INTERRUPTED`, command `COMPLETED`, no pending persisted approval, no delayed process/sentinel.
- [DONE / ZERO EFFECT] Existing Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`: existing latch accepted as safe replay barrier, SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

### P7.C6 same-thread continuation preparation

- [REWORK_REQUIRED / ZERO EFFECT] Prep-v2 candidate `1c9b03108bb2493fd6547a92c807397bb4c0868c` is preserved as inert reviewed harness/evidence. Useful offline preparation passed: Run-1 marker recovery, retained topology, structural matcher 13 ALLOW / 18 DENY, continuation latch helper tests, no intended new-thread path.

Architect review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_ARCHITECT_REVIEW_2026-09-10.md`

Binding repair:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_REPAIR_CONTRACT_2026-09-10.md`

The repair must close all reviewed acceptance gaps before any real continuation: exact accepted source/clean-tree gate, fresh mount/alias preflight, actual controller schema/live-state proof, unrelated baseline preservation, bounded descriptor-safe all-marker oracle, complete dynamic budget, no-reacquire interrupt proof, measured official P1.9 result, post-delete isolated envelope, success-only recovery sanitization, durable finite failure diagnostics, and finite waits/bridge arming.

- [NEXT / ZERO-REAL-EFFECT] **P7.C6 same-thread continuation prep-v2 repair.** No `src/**` changes and no real Codex effects. Publish repaired gated harness/evidence, then stop for architect review.
- [BLOCKED] P7.C6 real same-thread continuation. No authorization until repaired prep is independently accepted.

## P8 — deployment packaging/rollback

[BLOCKED BY P7.C6]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7.C6]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability; dedicated deploy key/token/config; same source architecture, no fork.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.