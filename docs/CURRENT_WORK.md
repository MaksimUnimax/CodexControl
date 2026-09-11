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

Run-1 evidence: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

The retained P7.C6 thread is permanently forensic-only. Accepted forensic authorities include Turn-3 evidence `e6835e7eaff21ce6a452c24f3309269df67c82ba`, Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`, retained-thread SHA-256 `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`, and Run-1 latch SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

P7.C6 Repair-6 preparation is architect accepted at `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`, tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`.

The one-shot same-thread real continuation executed once, was consumed, and may never be rerun. Architect forensic review establishes:

- model/list and retained-thread resume completed;
- Turn-4 start confirmed and Turn-4 persisted terminal `COMPLETED` with exact sentinel proof;
- approval bridge observed zero approval requests/responses and timed out;
- Turn-5 was not reached;
- official P1.9 delete was not dispatched;
- root cause is a harness acceptance-stimulus defect, not a production lifecycle/delete defect.

Final P7.C6 classifications:

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

## P7.C7 approval-stimulus authority

Authority evidence lineage:

- `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` — initial evidence;
- `e00392fbff6894e1857eb4c8f1e1937a88ca1e96` — final count correction.

Architect accepted the zero-effect result as correctly fail-closed:

- exact upstream `rust-v0.144.6` release commit is `5d1fbf26c43abc65a203928b2e31561cb039e06d`;
- internal command vector -> app-server `shlex_join` wire mapping is established;
- approval routing is conditional;
- future model-generated concrete command vector/wire grammar is not established offline;
- no ALLOW matcher is authorized from persisted Run-1 command data.

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

## P7.C7 DENY-only approval-probe preparation

Initial prep candidate:

`e4bcdf43ba3f5c50a65f7f1085781eec41770ede`

Architect review:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-11.md`

The candidate preserves the central DENY-only idea and concurrent approval/terminal observation, but it is **REWORK_REQUIRED** before any real fresh thread can be authorized.

Blocking harness-only defects:

- raw wire authority can be consumed by the first identity-mismatched request;
- sentinel identity uses unsafe substring matching;
- same-tick approval/terminal race is not deterministically classified;
- future effect budget omits real DENY-response accounting;
- process-group helper has silent scan errors and clamped/unaccounted signal paths;
- command-boundary scanner would false-fail normal isolated runtime payload and under-validates exact touch sentinel semantics;
- root-only wire record lacks exact schema/hash-consistency validation;
- gated real probe method remains intentionally inert rather than fully materialized.

No production `src/**` defect is established.

Binding Repair-1 contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C7 DENY-only approval-probe prep Repair-1 — NEXT / ZERO REAL EFFECT.**

Repair-1 is harness/tests/evidence only. It must close the reviewed evidence-authority/race/budget/watchdog/boundary defects and materialize the complete future real probe path under a disabled gate. No fresh thread, app-server or approval response is authorized during Repair-1.

`P7C7_DENY_ONLY_PROBE_PREPARATION=REWORK_REQUIRED`

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR1=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C7 real acceptance is architect accepted.
