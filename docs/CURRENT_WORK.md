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

Run 1 created one disposable real thread, one runtime-generation resume and three turns. Turn 1/2 proved persistence. Turn 3 reached approval and stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No interrupt, official delete, thread/read or thread/list occurred. The old approval remains `RESPONSE_UNKNOWN` and is permanently non-retryable.

Accepted retained recovery authorities:

- Turn-3 forensic `e6835e7eaff21ce6a452c24f3309269df67c82ba`: exact Turn 3 terminal `INTERRUPTED`, command completed, no pending persisted approval, no delayed process/sentinel.
- Existing Run-1 latch forensic `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` is accepted as the consumed Run-1 replay barrier, SHA-256 `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.
- The retained thread may be used only by a separately architect-authorized same-thread continuation. No new real thread is allowed.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

## P7.C6 continuation preparation lineage

- Prep-v2 inert candidate: `1c9b03108bb2493fd6547a92c807397bb4c0868c` — REWORK_REQUIRED.
- Repair-1 candidate: `821be881f1e6b04d3905080191cc0f1141799923` — REWORK_REQUIRED.
- Repair-2 candidate: `4d98e2b6170e76534fa18274236605f77440f740` — REWORK_REQUIRED.
- Repair-3 candidate: `2b38969c1c9a8232cb1c68efc953dae125e0e18c` — **REWORK_REQUIRED** after independent architect review.

Repair-3 architect review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR3_ARCHITECT_REVIEW_2026-09-11.md`

Frozen Repair-4 contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR4_CONTRACT_2026-09-11.md`

Repair-3 correctly closes the prior helper-level Repair-3 defects: bounded primary/secondary/final observations, explicit owned-task modeling, exact Turn-4 sentinel bytes, descriptor-coupled unrelated baseline identity, and safe-file post-delete reconciliation. It preserves the earlier source authority, topology/local-path gates, fail-closed journal updates, controller proof, bounded marker oracle, structural matcher, dynamic budget, no-new-thread path, official delete observer, DELETE_UNKNOWN no-retry semantics and success-only sanitization.

It is still not accepted as the one-shot real executable because independent review found three final harness-only failure-edge defects:

1. a FINAL_NONCONVERGENCE raises finitely but intentionally leaves the underlying cancellation-resistant asyncio task alive; the owner map is local to the real coroutine, so the full test process/event-loop teardown can still hang or allow the already-dispatched task to continue later;
2. Turn-5 start nonconvergence is not wrapped in an ambiguity handler that sets `forensic_retained`, so outer cleanup may remove the workdir while a still-live Turn-5 start task can later converge;
3. Turn-4 start failure swallows approval-bridge cancellation nonconvergence; a cancellation-resistant bridge therefore lacks an immediate runtime-shutdown/process-terminal authority strong enough to exclude a late ALLOW.

These are acceptance-harness defects only. No production `src/**` change is authorized or required.

`P7C6_CONTINUATION_PREP_V2_REPAIR3=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

## Disk maintenance — COMPLETE / SAFE

Owner-requested server-80 conservative cleanup completed safely before Repair-3. Exactly `945344512` bytes (`0.880421 GiB`) were reclaimed. P7.C6 protected state remained present, Git remained unchanged during cleanup, and no real Codex effects occurred.

## Current executable slice

**P7.C6 same-thread continuation prep-v2 Repair-4 — NEXT / ZERO REAL EFFECT.**

Binding contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR4_CONTRACT_2026-09-11.md`

Repair-4 is the final harness failure-edge repair: add process-level hard watchdog authority for cancellation-resistant tasks, retain forensic state on ambiguous Turn-5 start, and fail closed on nonconverging Turn-4 approval cancellation. Preserve all accepted Repair-3/Repair-2 authorities.

No production `src/**` change and no real Codex/app-server/business RPC effect is authorized.

`P7C6_REPAIR4_AUTHORIZED=YES`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C6 is independently accepted.
