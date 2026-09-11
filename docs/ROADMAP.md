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

#### Approval-stimulus authority

- [DONE / ZERO EFFECT / FAIL-CLOSED] Future concrete approval wire grammar not established offline.
- Exact upstream `rust-v0.144.6` source establishes internal vector -> app-server `shlex_join` projection and conditional approval routing.
- `P7C7_MATCHER_AUTHORIZED=NO`.

#### DENY-only approval probe preparation

- [REWORK_REQUIRED / HISTORICAL / ZERO EFFECT] Initial prep through Repair-5.
- [DONE / ARCHITECT ACCEPTED / ZERO EFFECT] Repair-6 `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`, harness blob `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.

#### One-shot real DENY-only approval probe

- [CONSUMED / NO RERUN] Executed exactly once; real evidence commit `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.
- [DONE / ZERO EFFECT FORENSIC] Forensic evidence commit `e589eec3c215d192df48a8e252e74dc13c768327`.
- Unique retained run established.
- Journal: `SOURCE_GATE`, `GLOBAL_LATCH_RESERVED`, `RUNTIME_ACQUIRE_INTENT`, `RUNTIME_ACQUIRE_RESULT=NONCONVERGED`, `BOUNDARY_PROOF_RESULT=DEFERRED_TO_PARENT`.
- No model/list stage recorded; no fresh thread; no Turn; approval not reached; no wire authority; workdir empty; sentinel absent.
- `LAST_DURABLY_ESTABLISHED_STAGE=RUNTIME_ACQUIRE_INTENT`.
- `FAILURE_CLASS=RUNTIME_ACQUIRE_FAILURE`.
- Exact runtime-acquire root cause remains `NOT_ESTABLISHED` because the accepted P7.C7 wrapper collapsed timeout and exception into one `NONCONVERGED` result.
- Architect source review establishes a harness defect: outer runtime-acquire timeout 5s did not dominate named production startup bounds, and error category was discarded.
- `P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`.
- [CLOSED] P7.C7 remains permanently consumed.

Architect forensic review:

`docs/evidence/p7c7/P7C7_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_ARCHITECT_REVIEW_2026-09-11.md`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

### P7.C8 fresh DENY-only successor

Initial prep candidate:

- [REWORK_REQUIRED / ZERO EFFECT] `9297395efb678356255d91aa8d90001a5fc768e0`, tree `291fddbbef8a67dc918a730d363c086cbb910db3`.
- Candidate correctly introduces a new P7.C8 namespace, dedicated runtime-acquire observer, 45-second acquire horizon, 12-second failed-acquire cleanup horizon, 100-second observation horizon and 205-second process watchdog.

Architect review:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-11.md`

Blocking Repair-1 defects:

- [FIX] remove unbounded `asyncio.gather()` after cleanup timeout; cancellation/join must have its own finite bound;
- [FIX] retain and durably publish the post-containment acquisition classification instead of discarding the returned `AcquireObservation`;
- [FIX] parent acquisition authority must never default missing/unreadable evidence to `CONFIRMED`; introduce explicit fail-closed `NOT_ESTABLISHED`;
- [FIX] cleanup safe-category persistence must not call an unsupported `RecoveryJournal.result(..., category=...)` signature;
- [FIX] freeze the complete finite production `RuntimeErrorSafe.category` set reachable from acquire/start/cleanup and never silently drop a safe categorized failure;
- [FIX] parent acquisition journal recovery must use bounded no-follow stable-identity JSONL reading instead of ordinary `Path.read_text()`.

Binding Repair-1 contract:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_CONTRACT_2026-09-11.md`

- [NEXT / ZERO REAL EFFECT] **P7.C8 prep Repair-1:** repair only runtime-acquire containment and durable acquisition authority while preserving every already-correct DENY/process/journal/result gate.
- [BLOCKED] Any P7.C8 real probe until Repair-1 is independently architect accepted and an exact executable SHA/tree is frozen.
- [BLOCKED] Matcher authority and full hard-delete acceptance until a separately authorized P7.C8 real probe succeeds and is architect reviewed.

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

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
