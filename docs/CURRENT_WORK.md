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

Accepted forensic facts:

- production state-root provision `CONFIRMED`, owner `TERMINALIZED`;
- production state-root validation `CONFIRMED`, owner `TERMINALIZED`;
- runtime acquire initial/final `RUNTIME_ACQUIRE_CONFIRMED`;
- model/list returned and model catalog confirmed;
- fresh thread/start confirmed;
- fresh primary turn/start confirmed;
- persistent-session evidence confirms exactly one fresh P7.C9 Turn;
- fresh Turn terminal status `ABORTED`;
- command item count `0`;
- approval request/decision/response structural counts all `0`;
- no wire authority, workdir empty, sentinel absent;
- runtime shutdown confirmed and boundary proof durably recorded;
- child-result write not reached;
- process group quiescent, no TERM/KILL, one child, zero retries.

Architect root-cause review:

`docs/evidence/p7c9/P7C9_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_ARCHITECT_REVIEW_2026-09-12.md`

Exact P7.C9 root cause:

`FAILURE_CLASS=HARNESS_FAILURE`

`ROOT_CAUSE_CLASS=RECOVERY_JOURNAL_STRUCTURAL_EVENT_REJECTED_BY_GENERIC_SECRET_FILTER`

`ROOT_CAUSE_EVENT=TURN_ID_AUTHORITY`

`ROOT_CAUSE_EXCEPTION_CLASS=JOURNAL_VALUE_UNSAFE`

The generic `RecoveryJournal._safe()` filter rejects strings containing `turn_id`; the harness attempted to append structural event `TURN_ID_AUTHORITY`, so the structural event token was rejected even though no raw Turn ID was present. The exception occurred after turn/start confirmation and before approval observer arming, then the `finally` path shut down the runtime and recorded boundary proof. Production defect is not established.

`P7C9_FRESH_THREAD_DISPOSITION=FRESH_THREAD_CONFIRMED_EVIDENCE_ONLY`

`P7C9_FRESH_TURN_DISPOSITION=FRESH_TURN_CONFIRMED_EVIDENCE_ONLY_ABORTED`

`P7C9_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C9_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C9_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C9_MATCHER_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P7.C10 schema-aware journal successor

Preparation is architect accepted:

- executable commit `3732134246464df899837a3c499c86c52270b038`;
- executable tree `68be37c8a5d0aa132199f8b2782618638a07b87e`;
- harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.

Architect acceptance:

`docs/evidence/p7c10/P7C10_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_ACCEPTANCE_2026-09-12.md`

Accepted P7.C10 authority includes:

- field-aware RecoveryJournal writer/reader validation with a finite exact structural event allowlist;
- exact structural `TURN_ID_AUTHORITY=ESTABLISHED` accepted while raw thread/Turn IDs, paths, wire plaintext and prompt/response routes remain closed;
- future real ordering confirmed Turn -> in-memory Turn authority -> durable Turn authority -> durable observer-armed record -> observer use;
- normal child and parent success independently require exact durable Turn chronology;
- all accepted P7.C9 state-root worker/provisioning, P7.C8 runtime-acquisition containment, DENY-only, immutable journal, exact `1/1/1`, zero resume/interrupt/delete/read/list, one-child/no-retry, process-group and boundary gates remain binding.

## Current executable slice

**P7.C10 one-shot real DENY-only approval probe — AUTHORIZED UNDER EXACT SNAPSHOT ONLY.**

Binding execution contract:

`docs/evidence/p7c10/P7C10_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-12.md`

The real probe may execute only from detached HEAD `3732134246464df899837a3c499c86c52270b038`, tree `68be37c8a5d0aa132199f8b2782618638a07b87e`, harness blob `0a8611e72e8a7f0d368a3b391f2025e05790d3f5`.

Once started, P7.C10 is consumed under every outcome. The probe remains observational and never automatically authorizes matcher or hard-delete execution.

`P7C10_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C10_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C10_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 acceptance is architect accepted.
