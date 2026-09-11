# Current work authority

Date: 2026-09-11

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 is binding: authenticated persistent `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 retained-thread authority

Run-1 evidence: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

The old Run-1 Turn-3 approval remains `RESPONSE_UNKNOWN` and permanently non-retryable. Accepted retained authorities remain the Turn-3 forensic `e6835e7eaff21ce6a452c24f3309269df67c82ba`, existing Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`, retained-thread SHA-256 `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`, and Run-1 latch SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

No new real thread is allowed.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

## Disk maintenance — COMPLETE / SAFE

Conservative server-80 cleanup reclaimed exactly `945344512` bytes (`0.880421 GiB`). P7.C6 protected state remained present; no Git/Codex state or real Codex effects were touched.

## P7.C6 continuation preparation lineage

- Prep-v2: `1c9b03108bb2493fd6547a92c807397bb4c0868c` — REWORK_REQUIRED.
- Repair-1: `821be881f1e6b04d3905080191cc0f1141799923` — REWORK_REQUIRED.
- Repair-2: `4d98e2b6170e76534fa18274236605f77440f740` — REWORK_REQUIRED.
- Repair-3: `2b38969c1c9a8232cb1c68efc953dae125e0e18c` — REWORK_REQUIRED.
- Repair-4: `a55a765cdfb0d51e956045a238d4ecb5a237a5fe` — REWORK_REQUIRED.
- Repair-5: `01994403110f19e323dffd693f226b18bdcb73c7` — **REWORK_REQUIRED** after independent architect review.

Repair-5 review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR5_ARCHITECT_REVIEW_2026-09-11.md`

Binding Repair-6 contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR6_CONTRACT_2026-09-11.md`

Repair-5 successfully closes the frozen watchdog-time-budget and child-to-parent result-authority defects: real/synthetic watchdog timing is separated; the real watchdog dominates the named internal finite-wait budget plus margin; a bounded exclusive root-only process-result file is written only after inner PASS; parent PASS revalidates exact source/tree, retained-thread hash, lifecycle statuses, residuals, scan/limit gates and dynamic effect counts.

It is still not real-executable because the watchdog currently owns only the dedicated Python child PID. The acceptance child launches `codex app-server` through production `asyncio.create_subprocess_exec(...)` without a dedicated process group/session. Therefore killing the Python watchdog child does not itself prove termination of the continuation-owned app-server/command process tree. A watchdog timeout could return while real descendants survive.

This is a harness/process-ownership defect only. No production `src/**` change is authorized or required.

`P7C6_REPAIR5=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

## Current executable slice

**P7.C6 same-thread continuation prep-v2 Repair-6 — NEXT / ZERO REAL EFFECT.**

Repair-6 may modify only the gated acceptance harness/tests/evidence. It must launch the dedicated continuation child in its own OS session/process group, signal the whole exact continuation group on watchdog timeout, prove a descendant/grandchild cannot survive, and prove an unrelated external process receives no signal. Preserve all Repair-5 lifecycle/result/watchdog authorities.

No production `src/**` changes and no real Codex/app-server/business RPC effects are authorized.

P8/P9 remain blocked until P7.C6 is independently accepted.
