# Current work authority

Date: 2026-09-11

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 is binding: authenticated persistent `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 history

Run-1 evidence: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

Run 1 created one real disposable thread, performed one runtime-generation resume and three turns. Turn 1/2 proved persistence. Turn 3 reached approval and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No interrupt, official delete, thread/read or thread/list occurred. Run-1 approval remains `RESPONSE_UNKNOWN` and is permanently non-retryable.

Independent review established Run-1 harness/recovery defects, not production defects.

Retained recovery authorities:

- Turn-3 forensic accepted: `e6835e7eaff21ce6a452c24f3309269df67c82ba` — exact Turn 3 terminal `INTERRUPTED`, command item `COMPLETED`, no persisted pending approval, no delayed process/sentinel.
- Existing Run-1 latch forensic accepted: `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- Existing `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` is accepted as the Run-1 consumed replay barrier; SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.
- The retained thread may only be used by a separately architect-authorized same-thread continuation; no new real thread is allowed.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

## P7.C6 same-thread continuation prep lineage

Prep-v2 inert candidate: `1c9b03108bb2493fd6547a92c807397bb4c0868c`.

Prep-v2 Repair-1 candidate: `821be881f1e6b04d3905080191cc0f1141799923`.

Repair-1 architect review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR_ARCHITECT_REVIEW_2026-09-11.md`

Binding Repair-2 contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_CONTRACT_2026-09-11.md`

Useful parts already present and to be preserved:

- source HEAD/tree/clean-worktree gate;
- accepted Run-1 latch/thread authorities;
- strict structural approval matcher with 13 accepted wrapper/exact cases;
- no new-thread path;
- actual controller `PRAGMA user_version` proof concept;
- actual official delete observer;
- success-only sanitization concept;
- bounded target marker oracle concept;
- explicit gated-real-file offline testing.

However Repair-1 is **REWORK_REQUIRED** and is not executable real authority. Independent review found these remaining acceptance-harness defects:

1. real mount/alias preflight self-rejects legitimate retained nesting (`run_root` contains isolated/controller descendants) and blocks repository users too broadly;
2. continuation local paths/sentinel/supplement are not all proven absent/safe before first real RPC;
3. recovery-journal progress is fail-open because journal write failures are swallowed;
4. shielded timeout paths can abandon live approval/turn/interrupt/delete tasks; destructive delete orchestration must remain owned through convergence and never be redispatched;
5. marker scanner does not re-`lstat` the pathname after descriptor read, leaving pathname replacement false-pass risk;
6. unrelated baseline accepts an aggregate-byte limit but does not enforce it;
7. unrelated reconciliation records path/device/inode but verifies only device/inode, allowing rename/replacement false pass;
8. final dynamic budget does not reject unexpected additional request methods;
9. several offline tests prove strings/helpers rather than the exact real failure behavior, including missing explicit `DELETE_UNKNOWN`, journal-failure stop and real-shaped topology tests.

No production `src/**` repair is authorized or required by these findings.

## Current executable slice

**P7.C6 same-thread continuation prep-v2 Repair-2 — ZERO REAL EFFECT ONLY.**

Repair the published gated harness according to:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_CONTRACT_2026-09-11.md`

Then run only offline/gate-disabled/fake regression, publish sanitized Repair-2 evidence and stop for independent architect review.

Current authority:

`P7C6_CONTINUATION_PREP_V2_REPAIR=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

No real model/list, thread/resume, turn, approval response, interrupt, delete, thread/read or thread/list is authorized during Repair-2.

P8/P9 remain blocked until P7.C6 is independently accepted.
