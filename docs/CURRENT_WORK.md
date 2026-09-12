# Current work authority

Date: 2026-09-12

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 remains binding: persistent authenticated `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 retained-thread history

P7.C6 is permanently consumed and forensic-only.

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

## P7.C7 DENY-only approval probe

P7.C7 preparation Repair-6 was accepted at `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`. The one-shot real probe executed once and is permanently consumed. Evidence: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`; forensic evidence: `e589eec3c215d192df48a8e252e74dc13c768327`.

Final P7.C7 facts:

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C7_RUNTIME_ACQUIRE_ROOT_CAUSE=NOT_ESTABLISHED`

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

## P7.C8 successor

P7.C8 Repair-1 was architect accepted at `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`. Its one-shot real probe executed exactly once and is permanently consumed. Real evidence: `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.

The durable runtime-acquire result was `RUNTIME_ACQUIRE_SAFE_EXCEPTION`, category `storage_boundary_invalid`, with confirmed cleanup and no fresh thread/Turn/approval. Architect source review established a harness precondition defect: P7.C8 manually created `sqlite/` and `logs/` but omitted the mandatory production `.codexcontrol-state-root-v1` marker. Production isolation correctly rejected that root.

`P7C8_FAILURE_CLASS=HARNESS_PRECONDITION_DEFECT`

`P7C8_ROOT_CAUSE=ISOLATED_STATE_ROOT_NOT_PROVISIONED_BY_PRODUCTION_AUTHORITY`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

## P7.C9 production-provisioned successor

Repair-1 is architect accepted:

- executable commit `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`;
- executable tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`;
- harness blob `44271459c2b4523f97551ade93563aee96def1c3`;
- Repair-1 evidence blob `58d505e7c6e4e49ad01376ce9ceb7626554d9a9f`.

The one-shot real P7.C9 probe executed exactly once and is permanently consumed. Sanitized real evidence commit: `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`. Retained-run forensic evidence head: `462e441cde02f9d21212dd583b8d965a2b1858cc`, blob `de0903e3e2668f79d39b3e44d690bdd016a5115a`.

Exact P7.C9 root cause:

`FAILURE_CLASS=HARNESS_FAILURE`

`ROOT_CAUSE_CLASS=RECOVERY_JOURNAL_STRUCTURAL_EVENT_REJECTED_BY_GENERIC_SECRET_FILTER`

`ROOT_CAUSE_EVENT=TURN_ID_AUTHORITY`

`ROOT_CAUSE_EXCEPTION_CLASS=JOURNAL_VALUE_UNSAFE`

`P7C9_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C9_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_ABORTED`

`P7C9_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

## P7.C10 schema-aware journal successor

P7.C10 zero-effect preparation is architect accepted:

- executable commit `3732134246464df899837a3c499c86c52270b038`;
- executable tree `68be37c8a5d0aa132199f8b2782618638a07b87e`;
- harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.

The one-shot P7.C10 real probe executed exactly once and is permanently consumed. Real evidence commit: `87124ee0d9f921ea9672cebb17e160b46a26a686`, evidence blob `f3ce5635d3ba51697ed99f69c012c9096e695d26`.

Architect-accepted real observational facts:

- parent final result confirmed and child completed;
- state-root provision/validation both `CONFIRMED`, owners `TERMINALIZED`;
- runtime acquire initial/final `CONFIRMED`;
- durable Turn authority proved by normal parent gate;
- model/list=1, thread/start=1, turn/start=1;
- fresh thread and Turn hashes established; both remain evidence-only;
- primary outcome `TURN_TERMINAL_BEFORE_APPROVAL_REQUEST`;
- terminal status `COMPLETED`;
- request count 0, DENY attempts/responses 0, ALLOW 0;
- no wire command authority;
- sentinel present with `EXPECTED_TOUCH`;
- runtime shutdown confirmed;
- child/parent boundary safe, drift none;
- process group quiescent; no TERM/KILL; one child, zero retry;
- resume/interrupt/delete/read/list all zero.

Upstream exact release source `rust-v0.144.6` / commit `5d1fbf26c43abc65a203928b2e31561cb039e06d` explains why this stimulus produced no approval: built-in workspace-write uses `exclude_tmpdir_env_var=false` and `exclude_slash_tmp=false`, so both `$TMPDIR` and `/tmp` are writable by default. The P7.C10 sentinel lived under `/tmp`; its successful touch without approval is expected behavior, not a production defect.

Upstream exact release approval tests establish a source-backed approval route: `AskForApproval::OnRequest` + workspace-write + `SandboxPermissions::RequireEscalated` produces `ExecApproval`; the upstream scenario `workspace_write_on_request_requires_approval_outside_workspace` explicitly exercises this path.

Final P7.C10 classification:

`P7C10_REAL_OBSERVATION=ARCHITECT_ACCEPTED`

`P7C10_APPROVAL_STIMULUS_VERDICT=NOT_APPROVAL_ELICITING__TARGET_INSIDE_DEFAULT_TMP_WRITABLE_ROOT`

`P7C10_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C10_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_COMPLETED`

`P7C10_APPROVAL_DISPOSITION=NO_APPROVAL_REQUEST_PROVED`

`P7C10_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C10_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C10_MATCHER_AUTHORIZED=NO`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## Current executable slice

**P7.C11 source-backed explicit-escalation DENY-only approval-probe preparation — NEXT / ZERO REAL EFFECT.**

P7.C11 is a new successor, not a retry. It must use a new namespace and preserve the complete accepted P7.C10 harness authority while changing only the approval stimulus design.

The new candidate must be source-derived from exact Codex 0.144.6 semantics: request one shell command with `sandbox_permissions=require_escalated` before execution, target a fresh run-owned sentinel outside `/tmp`, `$TMPDIR`, the Turn cwd and all default workspace writable roots, and explicitly forbid a default-sandbox first attempt or alternate command. The operator remains DENY-only, so the target must remain absent if approval routing works.

Before any real P7.C11 execution, a zero-effect harness/preparation pass and independent architect acceptance are required.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 hard-delete acceptance is architect accepted.
