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

The old Run-1 Turn-3 approval remains `RESPONSE_UNKNOWN` and permanently non-retryable.

Accepted retained authorities:

- Turn-3 forensic: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.
- Existing Run-1 latch forensic: `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- Retained-thread SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`.
- Accepted Run-1 latch SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

No new real thread is allowed.

## P7.C6 continuation preparation

Prep-v2 through Repair-5 were REWORK_REQUIRED. Repair-6 is architect accepted:

- accepted commit `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`;
- accepted tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`;
- architect acceptance `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`.

Preparation proved exact source/latch/topology/controller/budget gates, strict approval matching, exact sentinel proof, retained-state scanning, one-delete semantics, success-only sanitization, finite owned-task convergence, process-level watchdog, sanitized child-to-parent result authority and full continuation process-group ownership.

`P7C6_PREPARATION=ACCEPTED`

## P7.C6 one-shot real continuation — CONSUMED

Binding execution contract:

`docs/evidence/p7c6/P7C6_REAL_SAME_THREAD_CONTINUATION_EXECUTION_CONTRACT_2026-09-11.md`

The single authorized command executed once from the exact accepted Repair-6 snapshot.

Executor evidence commit:

`9b45d27a9d55d7d0695351ca57f71a75a4cd7971`

Architect review:

`docs/evidence/p7c6/P7C6_ONE_SHOT_REAL_CONTINUATION_ARCHITECT_REVIEW_2026-09-11.md`

Independently verified safe facts:

- `REAL_COMMAND_ATTEMPTS=1`;
- `REAL_COMMAND_RC=1`;
- continuation process-group authority/status `PASS`;
- final active continuation-group members `0`;
- continuation latch present, SHA-256 `fc1f428502b494566ee624f0f9b2ef8490cfd05a11532210a9ef07b09c8c9d7e`;
- process-result authority absent;
- exactly one continuation recovery journal reported, SHA-256 `3564157f6c54ba8dfff673fb26ddceab78c5278e771a7b8afc449774bdc68a1a`;
- exactly one continuation marker recovery record reported, SHA-256 `a615f475080c97ec76f4e4ad79f808de46439003585bbfe69990e3ab811d8b9d`;
- safe failure stage, effect counters, official P1.9 delete status and application delete status are not yet established;
- no rerun occurred.

The one-shot real authority is permanently consumed. No second invocation is allowed under any outcome.

`P7C6_REAL_ONE_SHOT_CONSUMED=YES`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

## Current executable slice

**P7.C6 consumed one-shot ZERO-EFFECT FORENSIC — NEXT.**

Binding forensic contract:

`docs/evidence/p7c6/P7C6_ONE_SHOT_REAL_CONTINUATION_FORENSIC_CONTRACT_2026-09-11.md`

The forensic may read existing durable local evidence only. It may not start Codex/app-server or issue any model/thread/turn/approval/interrupt/delete/read/list/Telegram operation. It must recover the last durably established stage by reconciling the continuation journal, controller DB, exact retained target-session structure, continuation markers, physical residuals, isolated metadata/logs and process/path state without modifying any retained authority.

P8/P9 remain blocked until the forensic evidence is independently reviewed.
