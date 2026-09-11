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

Initial prep `9297395efb678356255d91aa8d90001a5fc768e0` was architect reviewed as `REWORK_REQUIRED` because acquisition containment/evidence still had unbounded cleanup join, optimistic parent `CONFIRMED`, lost post-containment classification, an invalid cleanup-category journal route, incomplete safe category authority and a non-authoritative journal reader.

Repair-1 is architect accepted:

- executable commit `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`;
- executable tree `787e083077b7386a8b05968f2193c611d8182d9d`;
- harness blob `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`;
- Repair-1 evidence blob `c3c4dc55e4afe75b96c6a15919e4492e0b57cb4f`.

Architect acceptance:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_ARCHITECT_ACCEPTANCE_2026-09-11.md`

Accepted acquisition authority:

- 45-second runtime-acquire ceiling;
- distinct initial and final acquisition classes;
- 12-second failed-acquire `shutdown_profile()` containment;
- 1-second bounded cleanup cancellation/join;
- post-containment escalation to `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` is preserved;
- parent acquisition reconstruction is fail-closed with `RUNTIME_ACQUIRE_NOT_ESTABLISHED`, never optimistic `CONFIRMED`;
- parent acquisition journal read is bounded/no-follow/stable-identity JSONL;
- recognized production `RuntimeErrorSafe.category` values are retained safely; unrecognized values become fixed `SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED`;
- failed acquisition has zero downstream model/list/thread/Turn/approval effects;
- normal success requires acquisition initial/final `CONFIRMED` and no acquisition cleanup/error facts.

All accepted DENY/process/journal/result gates remain present: ALLOW=0, max three DENY attempts, one child/no retry, exact process-group ownership, immutable recovery journal, exact normal `1/1/1` effect ledger, zero resume/interrupt/delete/read/list, child/parent boundary proof and separate normal result/outcome authority.

## Current executable slice

**P7.C8 one-shot real DENY-only approval probe — AUTHORIZED UNDER EXACT SNAPSHOT ONLY.**

Binding execution contract:

`docs/evidence/p7c8/P7C8_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-11.md`

The real probe must execute only from detached HEAD `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`, tree `787e083077b7386a8b05968f2193c611d8182d9d`.

It may perform at most one owned runtime generation, one model/list, one fresh thread/start, one primary turn/start and 0..3 DENY attempts. ALLOW/resume/interrupt/delete/read/list remain zero.

The real invocation is one-shot and becomes permanently consumed once started under any success/failure/timeout/ambiguity outcome. It is observational only and never authorizes hard delete automatically.

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=YES_ONE_SHOT_EXACT_GATE_ONLY`

`P7C8_REAL_EXECUTION_AUTHORIZED=PROBE_ONLY`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 acceptance is architect accepted.
