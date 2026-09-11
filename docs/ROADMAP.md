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
- [CONSUMED / NO RERUN] Real continuation failed before Turn-5/delete; Turn-4 completed without approval request.
- Final classification: `OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`; production defect `NO`.

### P7.C7 fresh disposable-thread successor

- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Final prep Repair-6 `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.
- [CONSUMED / NO RERUN] One-shot real DENY-only probe executed once; evidence `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- [DONE / ZERO EFFECT FORENSIC] Forensic evidence `e589eec3c215d192df48a8e252e74dc13c768327`.
- No fresh thread/Turn/approval was reached; runtime acquire ended `NONCONVERGED` under an ambiguous 5s harness wrapper.
- Root cause not established for that run; harness observability defect established; production defect `NO`.
- [CLOSED] P7.C7 permanently consumed.

### P7.C8 fresh DENY-only successor

#### Preparation

- [REWORK_REQUIRED / HISTORICAL / ZERO EFFECT] Initial prep `9297395efb678356255d91aa8d90001a5fc768e0`.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-1 `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`, harness blob `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`.
- Accepted correction: bounded failed-acquire containment, distinct initial/final acquisition classes, safe RuntimeErrorSafe category authority, fail-closed parent recovery and authoritative journal reader.

#### One-shot real probe

- [CONSUMED / NO RERUN] Executed exactly once; evidence commit `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.
- Parent outcome: `CHILD_NONZERO`, watchdog `PROCESS_COMPLETED`, acquire initial/final `RUNTIME_ACQUIRE_SAFE_EXCEPTION`, category `storage_boundary_invalid`, cleanup `CONFIRMED`, no normal/child result, one child, zero retry, no TERM/KILL.
- [DONE / ARCHITECT ROOT-CAUSE REVIEW] P7.C8 harness manually created the isolated state root with only `sqlite/` and `logs/`, omitting the mandatory production `.codexcontrol-state-root-v1` marker. Production `IsolatedStateRoot.validate()` correctly rejected it before app-server startup.
- `P7C8_FAILURE_CLASS=HARNESS_PRECONDITION_DEFECT`.
- `P7C8_ROOT_CAUSE=ISOLATED_STATE_ROOT_NOT_PROVISIONED_BY_PRODUCTION_AUTHORITY`.
- `P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`.
- [CLOSED] P7.C8 permanently consumed.

Architect review:

`docs/evidence/p7c8/P7C8_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-11.md`

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C8_MATCHER_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

### P7.C9 production-provisioned DENY-only successor

Binding prep contract:

`docs/evidence/p7c9/P7C9_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-11.md`

- [NEXT / ZERO REAL EFFECT] Create a new P7.C9 test-only probe harness with a new token/profile/run/global-authority namespace.
- [FIX] Fresh run must leave configured isolated state root absent, then call production `IsolatedStateRoot(authority).provision(profile)` and immediately `validate(profile)` before runtime acquire.
- [FORBIDDEN] No manual creation of `.codexcontrol-state-root-v1`, `sqlite/`, or `logs/` by the harness.
- [BOUND] Provision/validate failure blocks runtime acquire and all downstream model/list/thread/Turn/approval effects.
- [BOUND] Preserve accepted P7.C8 acquisition authority: 45s acquire, 12s cleanup, 1s cancel/join, exact initial/final classes, safe categories, fail-closed `NOT_ESTABLISHED`.
- [BOUND] Preserve DENY-only, max-three DENY, ALLOW=0, one child/no retry, exact process-group ownership, immutable journal, exact normal `1/1/1`, zero resume/interrupt/delete/read/list and separate child/parent result authority.
- [BLOCKED] Any real P7.C9 probe until zero-effect preparation is independently architect accepted and exact executable SHA/tree are frozen.
- [BLOCKED] Matcher authority and hard-delete acceptance until separately authorized real evidence is accepted.

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P8 — deployment packaging/rollback

[BLOCKED BY P7 REAL ACCEPTANCE]

## P9 — server-80 live Telegram acceptance

[BLOCKED BY P7 REAL ACCEPTANCE]

## P10 — server-78 discovery/deployment

Repeat discovery/profile/storage/capability with same source architecture after P7 acceptance.

## P11 — multi-bot shared-group acceptance

Activation ordering/non-target silence/all-sleep/status; offline/restart/backlog; independent outage.

## P12 — Server-N lifecycle

Add/remove fleet member runbook/config propagation; manifest mismatch safeguards; zero source edits for ordinary server addition.

## P13 — final security/recovery acceptance

Threat audit, secret/log/replay tests, SQLite corruption/restore, Codex child failures, token rotation/decommission runbooks, mount/namespace residual-risk closure and V1 checkpoint.
