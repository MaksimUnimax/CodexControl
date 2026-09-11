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

Initial prep through Repair-4 are architect-reviewed REWORK_REQUIRED harness-only candidates.

Repair-5 candidate:

`b78b9fe93423c456e4557926745f9109e3992ea8`

Repair-5 tree:

`d395857adabf8e19c7524566258614c4180bdd4b`

Repair-5 evidence:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR5_EVIDENCE_2026-09-11.md`

Repair-5 architect review:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR5_ARCHITECT_REVIEW_2026-09-11.md`

Repair-5 materially fixes the Repair-4 durable-authority defects: parent outcome facts are measured rather than optimistically defaulted; child-result discovery is factful across failure classes; child execution classes and parent outcome combinations are narrowed; and RecoveryJournal binds later appends to one retained creation identity and fails closed on replacement/unlink/mode/hardlink drift.

Repair-5 remains **REWORK_REQUIRED** before any real fresh thread can be authorized because the normal child result still emits false zero counts for `model_list_calls`, `thread_start_calls`, and `turn_start_calls` instead of the already-authoritative `FutureProbeBudget` counts. The normal parent-final validator also accepts those zeroes because it only rejects values greater than one.

No production `src/**` defect is established.

Binding Repair-6 contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR6_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C7 DENY-only approval-probe prep Repair-6 — NEXT / ZERO REAL EFFECT.**

Repair-6 is limited to normal child/final effect-ledger truthfulness. It must project the authoritative budget into the durable child result, require exact `model/list=1`, `thread/start=1`, `turn/start=1` plus non-null thread/Turn hashes for normal observational authority, preserve every Repair-5 outcome/journal/process safety gate, and perform zero real effects.

No fresh real thread, app-server, approval response or real P7.C7 latch/result/outcome authority is authorized during Repair-6.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR5=REWORK_REQUIRED`

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR6=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C7 real acceptance is architect accepted.
