# Current work authority

Date: 2026-09-10

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Current controller schema authority is v4; migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted. P7.C5 accepted proof: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 is binding: persistent `CODEX_HOME` may be shared; CodexControl owns only its own app-server generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## Original P7 and P7.C6 Run 1

Original P7 remains rejected historical evidence after one P1.9 `DELETE_UNKNOWN`; the historical thread is never reused.

P7.C6 Run 1 evidence commit: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

Run 1 used `/root/.codex_second` in `SHARED_AUTHENTICATED` mode and performed one model/list, one disposable thread, one runtime-generation resume and three turns. Turn 1/2 proved persistence. Turn 3 reached one approval request and the Run-1 harness stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No P1.8 interrupt, official delete, thread/read or thread/list occurred.

Architect review established Run-1 harness/recovery defects, not production defects: literal/under-bound approval matcher, missing materialized global latch in the Run-1 harness, and loss of Run-1 marker plaintext from failure recovery. The old Turn-3 approval result remains `RESPONSE_UNKNOWN` and is permanently non-retryable.

## Retained-thread recovery authorities

- Retained Turn-3 forensic accepted: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.
- Turn 3 is exact and durably terminal `INTERRUPTED`; its command item is `COMPLETED`; no persisted approval request/decision/response remains; no delayed process or sentinel remains.
- Existing Run-1 latch forensic accepted: `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- Existing `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` is accepted as the Run-1 consumed replay barrier. Accepted SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`. It must not be overwritten or normalized.
- The retained thread is eligible only for a separately accepted same-thread continuation; no new real thread is allowed.

## P7.C6 same-thread continuation prep v2 — REWORK REQUIRED

Candidate preserved on main as inert reviewed preparation evidence/harness:

`1c9b03108bb2493fd6547a92c807397bb4c0868c`

Architect review:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_ARCHITECT_REVIEW_2026-09-10.md`

Binding repair contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_V2_REPAIR_CONTRACT_2026-09-10.md`

Accepted useful prep facts from the candidate:

- zero real effects;
- Run-1 accepted latch SHA recheck passed;
- one retained recovery identity and target session artifact;
- exactly three Run-1 marker families recovered into a root-only mode-0600 supplement;
- retained isolated/controller boundaries safe with zero external users;
- structural matcher offline matrix: 13 ALLOW / 18 DENY;
- continuation latch helper tests passed on synthetic paths;
- no intended new-thread path;
- real continuation method remains gated.

However the candidate is **not accepted for real execution**. The architect review found acceptance-critical gaps requiring one zero-effect repair:

1. bind future execution to architect-supplied exact accepted `HEAD`/tree and clean worktree; latch must store that accepted source, not pre-prep base;
2. repeat read-only mount/alias/protected-boundary preflight immediately before real runtime;
3. verify actual controller `PRAGMA user_version == 4`, no live dialogue and no conflicting tombstone before synthetic binding;
4. capture and reconcile content-free unrelated persistent baseline across delete;
5. replace unbounded `Path.read_bytes()` marker oracle with bounded descriptor/no-follow/inode-stable fail-closed scanning;
6. make the complete real-effect budget an explicit PASS gate;
7. dynamically prove no runtime reacquire during Turn-5 interrupt;
8. capture actual official P1.9 `ThreadOperationResult.status`, not a hardcoded report label;
9. revalidate post-delete isolated envelope and descendant scan errors/counts;
10. sanitize retained raw recovery/thread/marker plaintext only after complete PASS;
11. durably persist finite continuation recovery diagnostics after each effect and preserve ambiguous forensic state instead of cosmetic cleanup;
12. use finite waits and explicit Turn-4 approval-bridge arming.

`P7C6_CONTINUATION_PREP_V2=REWORK_REQUIRED`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

No production defect is established. No production `src/**` change is authorized by this repair.

## Next executable slice

**P7.C6 same-thread continuation prep-v2 zero-effect repair only.**

Repair the published gated harness according to `P7C6_SAME_THREAD_CONTINUATION_PREP_V2_REPAIR_CONTRACT_2026-09-10.md`, run only offline/gate-disabled/fake tests, publish sanitized repair evidence, and stop for architect review.

No real model/list, thread/resume, turn, approval response, interrupt, delete, thread/read or thread/list is authorized during repair.

P8 and P9 remain blocked until P7.C6 is independently accepted.