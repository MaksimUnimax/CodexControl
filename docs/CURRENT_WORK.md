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
- Repair-2 candidate: `4d98e2b6170e76534fa18274236605f77440f740` — **REWORK_REQUIRED** after independent architect review.

Repair-2 architect review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR2_ARCHITECT_REVIEW_2026-09-11.md`

Frozen Repair-3 contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR3_CONTRACT_2026-09-11.md`

Repair-2 successfully preserves/implements many required acceptance guards, including exact source authority, corrected topology nesting, local path preflight, fail-closed principal journal updates, actual controller path/schema/live-state validation, bounded target marker scanning, bounded unrelated baseline, exact path/device/inode reconciliation, unknown-RPC rejection, strict 13-ALLOW structural matcher, official delete observation, no intended new-thread path and success-only sanitization.

It is still **not** accepted for real execution because review found remaining harness-only defects:

1. final timeout/cancellation helpers still use unbounded `gather()` joins after their last timeout, so a supposedly finite one-shot continuation can hang indefinitely;
2. not every spawned task is explicitly terminalized on every sibling-failure edge, notably the Turn-4 approval bridge when Turn-4 start fails and the Turn-5 terminal waiter when interrupt fails;
3. Turn-4 sentinel “exact content” currently proves one marker occurrence, not exact byte-for-byte equality;
4. unrelated baseline capture has a scan-to-recorded-inode race between target-absence scanning and the later pathname `lstat()` used for baseline identity;
5. post-delete unrelated reconciliation checks path/device/inode but does not revalidate the full safe regular-file owner/mode/link envelope.

No production `src/**` change is authorized or required by these findings.

`P7C6_CONTINUATION_PREP_V2_REPAIR2=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

## Owner-requested temporary disk-maintenance pause

The next P7.C6 Repair-3 execution is intentionally **PAUSED** while server-80 disk usage is inventoried and reviewed for safe cleanup.

Disk work is independent of P7.C6 correctness. The disk inventory/cleanup must not delete or mutate any retained P7.C6 latch, recovery ledger, marker supplement, retained isolated state root, controller DB or target Codex profile/session authority.

After disk cleanup is reviewed and completed, resume from the frozen Repair-3 contract above.

P8/P9 remain blocked until P7.C6 is independently accepted.
