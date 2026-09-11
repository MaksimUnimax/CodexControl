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

### P7.C6 retained-thread continuation

- [REWORK_REQUIRED / ZERO EFFECT] Prep-v2 through Repair-5.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.
- [CONSUMED / REAL ACCEPTANCE FAILURE / NO RERUN] One-shot same-thread continuation executed exactly once and returned `RC=1`.
- One-shot evidence: `9b45d27a9d55d7d0695351ca57f71a75a4cd7971`.
- Zero-effect consumed-run forensic: `cf716ebb6c90e09fe927bccf36fdc08c776537b3`.
- Architect review: `docs/evidence/p7c6/P7C6_CONSUMED_REAL_CONTINUATION_ARCHITECT_REVIEW_2026-09-11.md`.
- Final classification: Turn-4 completed with exact sentinel but emitted no approval request; harness approval wait timed out before Turn-5/delete.
- `OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`.
- `ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`.
- `PRODUCTION_DEFECT_ESTABLISHED=NO`.
- Retained P7.C6 thread is permanently forensic-only; no same-thread rerun is authorized.

### P7.C7 fresh disposable-thread successor

P7.C7 is the successor path for the still-missing real approval + interrupt + official delete + post-delete acceptance.

#### Approval-stimulus authority

- [DONE / ZERO EFFECT / FAIL-CLOSED] Authority evidence lineage `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` -> `e00392fbff6894e1857eb4c8f1e1937a88ca1e96`.
- Architect review: `docs/evidence/p7c7/P7C7_APPROVAL_STIMULUS_AUTHORITY_ARCHITECT_REVIEW_2026-09-11.md`.
- Exact upstream `rust-v0.144.6` source proves internal command vector -> app-server `shlex_join` wire mapping and conditional approval routing.
- Future model-generated internal command vector is not deterministically knowable from preserved/offline evidence.
- Therefore `P7C7_APPROVAL_REQUEST_GRAMMAR=NOT_ESTABLISHED` is architect accepted as the correct fail-closed conclusion.
- No ALLOW matcher is authorized from persisted Run-1 command data.

#### DENY-only approval probe preparation

Binding contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-11.md`

- [NEXT / ZERO REAL EFFECT] Build/test a gated future fresh-thread approval probe with an operator that can never ALLOW, concurrently observes approval and turn terminal, captures raw wire grammar root-only, denies every observed approval request, has a bounded multiple-request policy, uses fresh isolated/process-group authority, and remains inert during ordinary tests.
- [BLOCKED] One-shot real P7.C7 approval probe until preparation is independently architect accepted.
- [BLOCKED] P7.C7 matcher authority until a real DENY-only probe yields safe wire-command evidence or another direct authority closes the grammar gap.
- [BLOCKED] P7.C7 full fresh-thread hard-delete acceptance until probe/matcher/harness are separately accepted and explicitly authorized.

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

## P8 — deployment packaging/rollback

[BLOCKED BY P7.C7 REAL ACCEPTANCE]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7.C7 REAL ACCEPTANCE]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture after P7 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
