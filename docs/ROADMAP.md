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

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Preparation Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.
- [CONSUMED / REAL ACCEPTANCE FAILURE / NO RERUN] One-shot same-thread continuation executed once and failed before Turn-5/delete.
- Final architect classification: Turn-4 completed with exact sentinel but emitted no approval request; approval wait timed out; `OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`; `ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`; production defect `NO`.
- Retained P7.C6 thread is permanently forensic-only.

### P7.C7 fresh disposable-thread successor

#### Approval-stimulus authority

- [DONE / ZERO EFFECT / FAIL-CLOSED] Evidence lineage `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` -> `e00392fbff6894e1857eb4c8f1e1937a88ca1e96`.
- Exact upstream `rust-v0.144.6` source proves internal command vector -> app-server `shlex_join` mapping and conditional approval routing.
- Future concrete model-generated wire grammar is not established offline.
- `P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`.
- No ALLOW matcher is authorized.

#### DENY-only approval probe preparation

- [REWORK_REQUIRED / ZERO EFFECT] Initial prep candidate `e4bcdf43ba3f5c50a65f7f1085781eec41770ede`.
- Architect review: `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-11.md`.
- Candidate correctly has no operator ALLOW path and introduces concurrent approval/terminal observation, root-only wire capture, fresh-run boundaries and synthetic process ownership.
- Remaining harness defects: identity-mismatched request can poison raw wire authority; sentinel identity is substring-based; simultaneous race is nondeterministic; DENY effects are not budgeted; watchdog signal/scan accounting is weaker than accepted P7.C6 authority; boundary scanner mishandles normal isolated runtime payload and exact touch semantics; wire-record schema is not fully validated; real probe path is still inert.
- Binding Repair-1: `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_CONTRACT_2026-09-11.md`.
- [NEXT / ZERO REAL EFFECT] **Repair-1:** close all reviewed harness/evidence defects and materialize the complete future real probe path under a disabled gate. No production changes and no real Codex effects.
- [BLOCKED] One-shot real P7.C7 DENY-only approval probe until Repair-1 is independently architect accepted and exact source/tree are frozen.
- [BLOCKED] P7.C7 matcher authority until accepted real probe evidence establishes a safe concrete wire grammar.
- [BLOCKED] P7.C7 full fresh-thread hard-delete acceptance until probe/matcher/full harness are separately accepted and explicitly authorized.

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
