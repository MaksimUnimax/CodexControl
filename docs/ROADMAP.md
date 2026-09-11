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
- Architect classification: Turn-4 completed with exact sentinel but emitted no approval request; `OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`; `ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`; production defect `NO`.
- Retained P7.C6 thread is permanently forensic-only.

### P7.C7 fresh disposable-thread successor

#### Approval-stimulus authority

- [DONE / ZERO EFFECT / FAIL-CLOSED] Evidence lineage `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` -> `e00392fbff6894e1857eb4c8f1e1937a88ca1e96`.
- Exact upstream `rust-v0.144.6` source proves internal command vector -> app-server `shlex_join` mapping and conditional approval routing.
- Future concrete model-generated wire grammar is not established offline.
- `P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`.
- No ALLOW matcher is authorized.

#### DENY-only approval probe preparation

- [REWORK_REQUIRED / HISTORICAL / ZERO EFFECT] Initial prep through Repair-5.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-6 `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`, harness blob `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.
- Repair-6 acceptance: `docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`.

#### One-shot real DENY-only approval probe

- [CONSUMED / FORENSIC REQUIRED / NO RERUN] Executed exactly once from the accepted Repair-6 snapshot.
- Published evidence commit: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- Parent authority: global latch present; normal result absent; parent outcome present; `CHILD_NONZERO`; watchdog `PROCESS_COMPLETED`; active process-group members `0`; scan errors `0`; no TERM/KILL; one child; zero retries.
- `REAL_COMMAND_RC=0` is not observational success; finite child-failure outcomes may return normally through the parent unittest.
- Published evidence does not establish exact child failure stage, fresh thread/Turn existence, approval request, DENY response, wire grammar, terminal or sentinel result.
- [NEXT / ZERO REAL EFFECT] **Consumed-probe forensic:** reconstruct recovery-journal chronology, root-only wire authority, isolated runtime evidence and offline persistent-session correlation without any new app-server RPC or process signal.
- Architect review: `docs/evidence/p7c7/P7C7_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-11.md`.
- Forensic contract: `docs/evidence/p7c7/P7C7_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_CONTRACT_2026-09-11.md`.
- [BLOCKED] Matcher authority until accepted forensic/real evidence establishes safe concrete wire grammar.
- [BLOCKED] Full fresh-thread hard-delete acceptance until probe/forensic/matcher/full harness are separately accepted and explicitly authorized.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

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
