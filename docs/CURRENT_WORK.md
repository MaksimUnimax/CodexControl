# Current work authority

Date: 2026-09-11

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 remains binding: persistent authenticated `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 retained-thread history

The P7.C6 retained thread is permanently forensic-only. The consumed real continuation was architect-reviewed as a harness approval-stimulus failure: Turn-4 completed with exact sentinel proof but emitted no approval request; Turn-5 and official delete were never reached.

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

Accepted P7.C6 prep authority remains Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.

## P7.C7 approval-stimulus authority

Evidence lineage `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` -> `e00392fbff6894e1857eb4c8f1e1937a88ca1e96` is architect accepted as a correct fail-closed result.

Exact upstream `rust-v0.144.6` release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d` proves internal command vector -> approval event -> app-server `shlex_join` projection, but preserved/offline evidence does not establish which concrete vector a future model turn will generate.

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

## P7.C7 DENY-only approval-probe preparation

Initial prep and Repair-1 through Repair-5 are historical REWORK_REQUIRED harness-only candidates.

Repair-6 is architect accepted:

`320ae3ba1265608a92ebfe82992068d4b12ebcd9`

Accepted Repair-6 executable tree:

`eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`

Accepted harness blob:

`b2bf5f91250b8881050ce3afcbd3e86874b15e5e`

Repair-6 evidence:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR6_EVIDENCE_2026-09-11.md`

Architect acceptance:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`

Repair-6 closes the final normal-result truthfulness defect. Normal child and parent-final observational authority require exact `model/list=1`, `thread/start=1`, `turn/start=1`, valid fresh thread and Turn SHA-256 identities, zero forbidden lifecycle calls, zero ALLOW, bounded DENY accounting, owner terminalization, exact process-group authority, safe child/parent boundaries and exact accepted source authority.

All accepted Repair-5 durable-evidence properties remain binding: measured parent outcome facts; narrow child execution classes; semantic parent outcome matrix; bounded child-result discovery; immutable RecoveryJournal creation-time device/inode; no later journal `O_CREAT`; replacement/unlink/mode/hardlink fail-closed behavior.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR6=ARCHITECT_ACCEPTED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

## Current executable slice

**P7.C7 one-shot real DENY-only approval probe — AUTHORIZED under exact frozen gate.**

Binding execution contract:

`docs/evidence/p7c7/P7C7_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-11.md`

The real probe must execute from the detached accepted snapshot:

- HEAD `320ae3ba1265608a92ebfe82992068d4b12ebcd9`;
- tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.

The probe is observational only. It may create exactly one fresh disposable thread and one primary Turn, may send at most three DENY responses, and has no ALLOW/resume/interrupt/delete/read/list path.

Once the real invocation starts it is consumed under every outcome. No rerun is authorized.

The resulting fresh thread is evidence-only until architect review. The probe result does not automatically authorize matcher construction, hard-delete execution, P8, or P9.

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C7_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C7 real acceptance is architect accepted.
