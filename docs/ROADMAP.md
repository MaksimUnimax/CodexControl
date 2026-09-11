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

- [DONE / ZERO EFFECT / FAIL-CLOSED] Exact upstream `rust-v0.144.6` source proves internal command vector -> app-server `shlex_join` mapping and conditional approval routing.
- Future concrete model-generated wire grammar is not established offline.
- `P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`.
- No ALLOW matcher is authorized.

#### DENY-only approval probe preparation

- [REWORK_REQUIRED / ZERO EFFECT] Initial prep `e4bcdf43ba3f5c50a65f7f1085781eec41770ede`.
- [REWORK_REQUIRED / ZERO EFFECT] Repair-1 `bffe4d05340545edd44d503c9a16f1128c65ca7d`.
- [REWORK_REQUIRED / ZERO EFFECT] Repair-2 `388b1a1bf46b56bc1734bbf2e3eb630266b822a7`.

Repair-2 materially improves the disabled future real path: exact Turn authority precedes approval dequeue, a queued request can be captured after Turn confirmation, durable journal and DENY attempt accounting exist, finite stage timeouts and a dedicated parent/child process-group watchdog exist, child/final result schemas are separated, runtime-owned sqlite/log state is separated from command-owned mutation surface, and `/proc` disappearance semantics are improved.

Independent architect review still blocks real execution because:

1. parent final result is written through the child-schema writer, so the extended parent schema is rejected and the global final result can never be materialized;
2. approval-request observation is durably journaled only after the race returns, which is later than possible DENY dispatch;
3. wire-return and adapter-level result semantics for model/thread/turn are conflated/duplicated in the journal;
4. command-boundary proof is child-local before parent process-group quiescence, so late descendant mutation can make the final boundary claim stale;
5. watchdog timeout classification can collapse into generic child nonzero even though a dedicated timeout class exists;
6. nonconverged approval/terminal owner state does not block child-result publication.

Binding architect review:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR2_ARCHITECT_REVIEW_2026-09-11.md`

Binding Repair-3 contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR3_CONTRACT_2026-09-11.md`

- [NEXT / ZERO REAL EFFECT] **Repair-3:** close the six remaining execution/evidence-authority defects while preserving all Repair-2 safety gates.
- [BLOCKED] One-shot real P7.C7 DENY-only approval probe until Repair-3 is independently architect accepted and exact executable SHA/tree are frozen.
- [BLOCKED] P7.C7 matcher authority until accepted real DENY-only probe evidence establishes a safe concrete wire grammar.
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
