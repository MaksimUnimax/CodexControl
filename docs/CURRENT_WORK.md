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

P7.C6 is permanently consumed and forensic-only.

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

## P7.C7 approval-stimulus authority

Exact upstream `rust-v0.144.6` release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d` proves the internal command-vector -> app-server `shlex_join` mapping, but offline evidence did not establish the future concrete model-generated wire grammar.

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

## P7.C7 DENY-only approval probe

Repair-6 preparation was architect accepted:

- executable commit `320ae3ba1265608a92ebfe82992068d4b12ebcd9`;
- tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`;
- harness blob `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.

The one-shot P7.C7 real probe executed exactly once and is permanently consumed. Real evidence commit: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.

Consumed-probe forensic evidence commit: `e589eec3c215d192df48a8e252e74dc13c768327`.

Accepted factual classifications:

`JOURNAL_LAST_DURABLE_MILESTONE=RUNTIME_ACQUIRE_RESULT`

`JOURNAL_LAST_DURABLE_RESULT=NONCONVERGED`

`LAST_DURABLY_ESTABLISHED_STAGE=RUNTIME_ACQUIRE_INTENT`

`FAILURE_CLASS=RUNTIME_ACQUIRE_FAILURE`

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C7_RUNTIME_ACQUIRE_ROOT_CAUSE=NOT_ESTABLISHED`

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

P7.C7 used a 5-second outer acquire timeout around a production startup path containing a 15-second initialize bound plus separate version-probe bounds, and its generic helper collapsed timeout and exceptions into one `NONCONVERGED` result. P7.C7 is never rerun.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P7.C8 successor

P7.C8 is a new successor namespace, not a retry of P7.C7.

Initial P7.C8 zero-effect prep candidate:

- commit `9297395efb678356255d91aa8d90001a5fc768e0`;
- tree `291fddbbef8a67dc918a730d363c086cbb910db3`;
- scope limited to the new P7.C8 harness plus prep evidence;
- reported real effects `0`.

Architect review:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-11.md`

The candidate correctly introduces a dedicated acquisition observer and the new P7.C8 namespace, but remains **REWORK_REQUIRED** before any real execution.

Blocking harness/evidence defects:

- failed-acquire cleanup cancels its cleanup task and then waits through an unbounded `asyncio.gather`, violating the 12-second containment authority for cancellation-resistant cleanup;
- the real child discards the `AcquireObservation` returned by containment, so a post-cleanup escalation to `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` is not durably finalized;
- parent acquisition recovery defaults absent/missing acquisition evidence to `RUNTIME_ACQUIRE_CONFIRMED`, which is not fail-closed;
- cleanup safe-category persistence calls `RecoveryJournal.result(..., category=...)` even though that method does not accept `category`, so the categorized cleanup path raises `TypeError`;
- the frozen safe runtime-category set is incomplete relative to production `RuntimeErrorSafe.category` values reachable from acquire/start/cleanup;
- parent acquisition recovery uses ordinary `Path.read_text()` rather than bounded no-follow stable-identity journal reading.

No production `src/**` defect is established.

Binding Repair-1 contract:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C8 DENY-only approval-probe prep Repair-1 — NEXT / ZERO REAL EFFECT.**

Repair-1 is limited to bounded failed-acquire containment and truthful durable acquisition authority. It must preserve every already-correct P7.C8 DENY/process/journal/result gate and must perform zero real Codex effects.

`P7C8_DENY_ONLY_APPROVAL_PROBE_PREP=REWORK_REQUIRED`

`P7C8_PREP_REPAIR1=NEXT_ZERO_REAL_EFFECT`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 acceptance is architect accepted.
