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

- [REJECTED / HISTORICAL] Original P7: one official P1.9 `DELETE_UNKNOWN`; forensic `5aac49bd1b8a349343db52071520beed7f95592d`.
- [DONE] P7.C1 storage-isolation discovery — `a9900471d0599be21b1a1834301c4421d95acb29`.
- [DONE] P7.C2 confirmed-delete storage barrier — `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- [DONE] P7.C3 persistent profile + isolated state-root runtime authority — `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`.
- [DONE] P7.C4 confirmed cleanup + DELETE_UNKNOWN containment — `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`.
- [DONE] P7.C5 corrected fake hard-delete acceptance — `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- [ACCEPTED CORRECTION] ADR-0045 shared persistent CODEX_HOME semantics.

### P7.C6 preparation

- [REWORK_REQUIRED / ZERO EFFECT] Prep-v2 through Repair-5.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.

### P7.C6 one-shot real continuation

- [CONSUMED / FAILURE OR AMBIGUITY] The one authorized real command executed exactly once and returned `RC=1`.
- Evidence commit: `9b45d27a9d55d7d0695351ca57f71a75a4cd7971`.
- Process-group authority/status passed and final active continuation members are zero.
- Consumed continuation latch exists.
- Final PASS process-result is absent.
- Exact failure stage, effect counts and official P1.9 delete status are not yet established.
- **NO RERUN IS AUTHORIZED.**

Architect review:

`docs/evidence/p7c6/P7C6_ONE_SHOT_REAL_CONTINUATION_ARCHITECT_REVIEW_2026-09-11.md`

Frozen forensic:

`docs/evidence/p7c6/P7C6_ONE_SHOT_REAL_CONTINUATION_FORENSIC_CONTRACT_2026-09-11.md`

- [NEXT / ZERO REAL EFFECT] **Consumed one-shot forensic.** Reconcile durable journal, controller DB, exact retained target-session structure, continuation markers, physical residuals and isolated metadata/logs. No Codex/app-server/model/thread/turn/approval/interrupt/delete/read/list/Telegram effects and no retained-state mutation.
- [BLOCKED] P7.C6 final acceptance until forensic architect review.

## P8 — deployment packaging/rollback

[BLOCKED BY P7.C6 FORENSIC]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7.C6 FORENSIC]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture after P7 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
