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

The old Run-1 Turn-3 approval remains `RESPONSE_UNKNOWN` and permanently non-retryable.

Accepted retained authorities:

- Turn-3 forensic: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.
- Existing Run-1 latch forensic: `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- Retained-thread SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`.
- Accepted Run-1 latch SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.
- No new real thread is allowed.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

## Disk maintenance — COMPLETE / SAFE

Conservative server-80 cleanup reclaimed exactly `945344512` bytes (`0.880421 GiB`). P7.C6 protected state remained present; no Git/Codex state or real Codex effects were touched.

## P7.C6 continuation preparation lineage

- Prep-v2 `1c9b03108bb2493fd6547a92c807397bb4c0868c` — REWORK_REQUIRED.
- Repair-1 `821be881f1e6b04d3905080191cc0f1141799923` — REWORK_REQUIRED.
- Repair-2 `4d98e2b6170e76534fa18274236605f77440f740` — REWORK_REQUIRED.
- Repair-3 `2b38969c1c9a8232cb1c68efc953dae125e0e18c` — REWORK_REQUIRED.
- Repair-4 `a55a765cdfb0d51e956045a238d4ecb5a237a5fe` — REWORK_REQUIRED.
- Repair-5 `01994403110f19e323dffd693f226b18bdcb73c7` — REWORK_REQUIRED.
- Repair-6 `76a7aa24e3cfdfb12c3314a7e01691d4a943b551` — **ARCHITECT ACCEPTED**.

Accepted executable Repair-6 tree:

`92abebdfb3390d4c58f4aefc00aa84b83841e99e`

Architect acceptance:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`

Independent review confirmed the accepted harness now owns the full continuation process tree: one top-level child is launched with `start_new_session=True`; `PID=PGID=SID` authority is proved; watchdog signals only the exact continuation PGID; timeout converges the leader/descendant/grandchild tree to zero active members; normal child exit is rejected if continuation descendants remain; an unrelated separate-session process survives untouched. The Repair-5 real watchdog/result authority and all prior lifecycle/storage/budget/erasure gates remain intact.

`P7C6_PREPARATION=ACCEPTED`

## Current executable slice

**P7.C6 ONE-SHOT REAL SAME-THREAD CONTINUATION — AUTHORIZED.**

Binding execution contract:

`docs/evidence/p7c6/P7C6_REAL_SAME_THREAD_CONTINUATION_EXECUTION_CONTRACT_2026-09-11.md`

The real run MUST execute the exact accepted source snapshot:

- HEAD `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`
- tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`

The authorization is one-shot. Once the single real command starts, no rerun is allowed for PASS, FAIL, timeout, signal termination or ambiguity.

Successful effect budget: no new thread; one `model/list`; one retained `thread/resume`; two `turn/start`; one Turn-4 approval response; one Turn-5 interrupt; one official `thread/delete`; zero `thread/read`/`thread/list`; zero Telegram effects.

`P7C6_REAL_CONTINUATION_AUTHORIZED=YES_ONE_SHOT_EXACT_ACCEPTED_SNAPSHOT`

P8/P9 remain blocked until the resulting real evidence is independently reviewed and P7.C6 is marked DONE.
