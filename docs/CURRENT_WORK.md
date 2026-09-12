# Current work authority

Date: 2026-09-12

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 remains binding: persistent authenticated `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## Permanently consumed real-probe history

### P7.C6

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

### P7.C7

Prep Repair-6 accepted at `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`. Real evidence `4629cff73d981ee9c2abafa24c97ba7ca340f87c`; forensic evidence `e589eec3c215d192df48a8e252e74dc13c768327`.

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

### P7.C8

Repair-1 accepted at `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`. Real evidence `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.

`P7C8_FAILURE_CLASS=HARNESS_PRECONDITION_DEFECT`

`P7C8_ROOT_CAUSE=ISOLATED_STATE_ROOT_NOT_PROVISIONED_BY_PRODUCTION_AUTHORITY`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

### P7.C9

Repair-1 accepted executable `6cefa7772f00f6b1d67b9c6ecfd3770009d77c7f`, tree `1fd13ed5964f7c18ac5c5cfc799ee4670c719ab2`, harness blob `44271459c2b4523f97551ade93563aee96def1c3`. Real evidence `bf7f870c6df640bb26e51fa9c05a2b55e44e5489`; retained-run forensic head `462e441cde02f9d21212dd583b8d965a2b1858cc`, blob `de0903e3e2668f79d39b3e44d690bdd016a5115a`.

Production state-root provision/validate, runtime acquire, model/list, fresh thread/start and fresh Turn/start were all proved. P7.C9 then failed in the harness because generic RecoveryJournal secret filtering rejected structural event `TURN_ID_AUTHORITY` as `JOURNAL_VALUE_UNSAFE`.

`FAILURE_CLASS=HARNESS_FAILURE`

`ROOT_CAUSE_CLASS=RECOVERY_JOURNAL_STRUCTURAL_EVENT_REJECTED_BY_GENERIC_SECRET_FILTER`

`P7C9_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C9_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_ABORTED`

`P7C9_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

### P7.C10

Zero-effect prep accepted executable `3732134246464df899837a3c499c86c52270b038`, tree `68be37c8a5d0aa132199f8b2782618638a07b87e`, harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.

The P7.C10 one-shot real probe executed exactly once and is permanently consumed. Evidence commit `87124ee0d9f921ea9672cebb17e160b46a26a686`, blob `f3ce5635d3ba51697ed99f69c012c9096e695d26`.

Architect-accepted facts:

- parent final confirmed; child completed;
- state-root provision/validate confirmed and terminalized;
- runtime acquire initial/final confirmed;
- durable Turn authority proved;
- model/list=1, thread/start=1, turn/start=1;
- fresh thread/Turn evidence-only;
- terminal `COMPLETED` before any approval request;
- request count=0, DENY=0, ALLOW=0;
- sentinel present with expected touch;
- runtime shutdown confirmed;
- boundary safe, group quiescent, one child, zero retry;
- resume/interrupt/delete/read/list all zero.

Exact Codex 0.144.6 source explains the zero-approval result: workspace-write grants write access to `$TMPDIR` and `/tmp` by default, and P7.C10 target was under `/tmp`.

`P7C10_REAL_OBSERVATION=ARCHITECT_ACCEPTED`

`P7C10_APPROVAL_STIMULUS_VERDICT=NOT_APPROVAL_ELICITING__TARGET_INSIDE_DEFAULT_TMP_WRITABLE_ROOT`

`P7C10_APPROVAL_DISPOSITION=NO_APPROVAL_REQUEST_PROVED`

`P7C10_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C10_REAL_PROBE_RERUN_AUTHORIZED=NO`

## P7.C11 source-backed explicit-escalation successor

Binding source/stimulus contract:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-12.md`

Initial candidate `52d5a4d3a3e716dce32069afbb6b6bdf0fa4a07e` established the correct source-backed `/root` target and first-and-only explicit `sandbox_permissions=require_escalated` stimulus, but architect review rejected its command-approval success projection as over-broad.

Repair-1 is architect accepted:

- executable commit `be98542b9bcbf99508784f229057698d85784367`;
- executable tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`;
- harness blob `fc67299d80c3d617280975182c097a92cb863b92`;
- Repair-1 evidence blob `febfb3e94b1b963956520f80d9fb1ff371f16c49`.

Repair-1 accepted authority:

- root-only first-capture wire authority is correlated to exactly one observed command request by local sequence and wire SHA-256;
- preferred success requires exact COMMAND_EXECUTION thread/Turn/cwd identity;
- DENY intent/result carries that request's ordinal and the authoritative request must resolve to `DENIED_CONFIRMED`;
- `RESPONSE_UNKNOWN`, wrong identity/kind, missing wire authority or non-exact target reference cannot become preferred success;
- preferred command success requires exact target-token authority, established wire-vector reconstruction, ALLOW=0, terminalized owners and absent target;
- child authority exposes only sanitized command-correlation facts;
- parent independently hashes its selected external target, binds it to the child target SHA-256 and re-observes exact target absence;
- zero-request/non-success outcomes remain finite observations and are not silently promoted to command-approval success.

Architect acceptance:

`docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_ARCHITECT_ACCEPTANCE_2026-09-12.md`

The repository-wide test attempt still encounters historical P7.C7–P7.C10 static checks because their consumed one-shot latch files correctly remain present. Those immutable latches must not be deleted or rewritten to manufacture green historical tests. P7.C11 itself passed its focused suite and the complete non-real regression suite.

## Current executable slice

**P7.C11 one-shot real source-backed explicit-escalation DENY-only approval probe — AUTHORIZED UNDER EXACT SNAPSHOT ONLY.**

Binding execution contract:

`docs/evidence/p7c11/P7C11_ONE_SHOT_REAL_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-12.md`

Executable snapshot:

`HEAD=be98542b9bcbf99508784f229057698d85784367`

`TREE=ec6433f02f9293273979fd5dfc3f3eff70f16fa4`

`HARNESS_BLOB=fc67299d80c3d617280975182c097a92cb863b92`

The real probe is one-shot. It asks for exactly one `touch <external-target>` shell command with `sandbox_permissions=require_escalated`; every approval is DENY; the external target must remain absent. A zero-request or other finite empirical outcome remains valid evidence but is not command-approval acceptance.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C11_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until architect-accepted hard-delete acceptance.
