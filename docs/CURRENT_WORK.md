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

Final P7.C6 classifications:

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

Initial prep `e4bcdf43ba3f5c50a65f7f1085781eec41770ede` and Repair-1 `bffe4d05340545edd44d503c9a16f1128c65ca7d` are architect-reviewed REWORK_REQUIRED harness-only candidates.

Repair-2 candidate:

`388b1a1bf46b56bc1734bbf2e3eb630266b822a7`

Repair-2 candidate tree:

`45cfb17776d70d41cef9b1b503ffd7dbf6bed088`

Repair-2 evidence:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR2_EVIDENCE_2026-09-11.md`

Architect review:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR2_ARCHITECT_REVIEW_2026-09-11.md`

Repair-2 useful improvements are retained: zero ALLOW paths, exact Turn authority before approval dequeue, queued request capture after Turn confirmation, exact-identity wire capture, mismatch not consuming wire authority, exact wire schema, DENY attempt accounting, deterministic race classes, root-only recovery journal, named finite waits, auditable watchdog budget, dedicated parent/child process-group ownership, child/parent result schema separation, `/proc` disappearance semantics, runtime-vs-command state separation, and exact zero-length touch authority.

Repair-2 is still **REWORK_REQUIRED** before any real fresh thread can be authorized.

Remaining harness-only blockers:

- parent final result is passed through the child-schema writer, so the extended parent schema is rejected and final global result materialization cannot succeed;
- approval-request observation is journaled only after the race returns, later than a possible DENY response dispatch;
- wire-level and adapter-level model/thread/turn results are conflated under duplicate stage names;
- child boundary proof can become stale before parent process-group quiescence if a surviving descendant mutates command-owned state;
- watchdog hard-timeout can be collapsed into generic child nonzero instead of its exact timeout classification;
- normal child-result publication does not require all approval/terminal owner tasks to have terminalized.

No production `src/**` defect is established.

Binding Repair-3 contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR3_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C7 DENY-only approval-probe prep Repair-3 — NEXT / ZERO REAL EFFECT.**

Repair-3 is harness/tests/evidence only. It must preserve all Repair-2 safety properties while fixing parent-result persistence, durable request-before-response chronology, separate wire/adapter semantic results, parent post-quiescence boundary recheck, exact watchdog outcome classification and owned-task terminalization authority.

No fresh real thread, app-server, approval response or real P7.C7 latch/result is authorized during Repair-3.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR2=REWORK_REQUIRED`

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR3=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C7 real acceptance is architect accepted.
