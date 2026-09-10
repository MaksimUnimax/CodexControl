# Current work authority

Date: 2026-09-10

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority remains `codex-cli 0.144.6`; generated app-server schema SHA-256 remains `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete at their accepted boundaries. P6 final accepted commit remains `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Historical schema-v1/v2/v3 authorities remain immutable. Current schema is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- No live Telegram/deployment acceptance has occurred.

## Rejected original P7

Original real P7 under ADR-0042 remains **REJECTED / ARCHITECTURE BLOCKED historical evidence**. Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; it was not retried/read/list-reconciled. Final forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL` with five synthetic marker matches. Issue #38 remains historical blocker evidence. The historical rejected thread must never be touched again by the correction lane.

## P7.C1–P7.C5 — COMPLETE / architect accepted

- P7.C1 accepted discovery: `a9900471d0599be21b1a1834301c4421d95acb29`.
- P7.C2 accepted implementation: `80673db644962b0cc5b1a388d64cb5902bd4f46c`.
- P7.C3 accepted final implementation: `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`, tree `13eea89362694da594bb2b717c037980b0df446f`.
- P7.C4 accepted final implementation: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`, tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.
- P7.C5 accepted final proof: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`, tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`.

C2 adds durable `DELETE_CONFIRMED_PENDING_STORAGE`. C3 owns configured persistent `CODEX_HOME` plus a distinct CodexControl-owned isolated state root, exact per-generation capability validation and process-local reservation/quiescence. C4 composes confirmed cleanup and durable UNKNOWN local containment. C5 proves the corrected fake hard-delete lifecycle, production exact-thread gate, independent marker oracle, crash/restart/concurrency/cancellation, controller authority and unrelated session/history preservation.

## ADR-0045 — shared persistent CODEX_HOME correction

ADR-0045 supersedes only the earlier mistaken persistent-home exclusivity interpretation. A configured authenticated persistent `CODEX_HOME` may be concurrently shared by independent Codex processes/applications. CodexControl owns only its own app-server child/generation, isolated state root, controller SQLite and process-local reservation. Other processes sharing `/root/.codex_second` are allowed and are not killed/stopped/signaled merely to make the home quiet.

## P7.C6 Run 1 — REAL RUN EXECUTED / REJECTED

Run-1 evidence commit: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

Architect review: `docs/evidence/p7c6/P7C6_RUN1_ARCHITECT_REVIEW_2026-09-10.md`.

Run 1 used `/root/.codex_second` in `SHARED_AUTHENTICATED` mode. It performed one real `model/list`, one new disposable thread, one runtime-generation resume and three turns. Turn 1/2 proved bounded persistence. Turn 3 reached one approval request and the harness stopped at `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No P1.8 interrupt, official delete, thread/read or thread/list occurred.

Independent review established acceptance-harness defects, not production defects: the Run-1 approval matcher was literal/under-bound; the declared host-level one-shot latch was not created by the Run-1 harness; and failure-path recovery did not retain the synthetic marker plaintext needed for the later all-marker erasure oracle. The old Turn-3 approval result remains `RESPONSE_UNKNOWN` and must never be answered/retried/reinterpreted.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

P7.C6 remains **NOT ACCEPTED**.

## P7.C6 retained Turn-3 forensic — COMPLETE / architect accepted

Accepted forensic commit: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.

Evidence: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_FORENSIC_EVIDENCE_2026-09-10.md`.

Architect review: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_ARCHITECT_REVIEW_2026-09-10.md`.

The zero-real-effect forensic proves exact Run-1 Turn 3 is durably terminal `INTERRUPTED`, its single command item is `COMPLETED`, no persisted approval request/decision/response remains, no run-owned delayed process/sentinel remains, and scan/parse errors are zero. The persisted Turn-3 command is outside the historical safe approval grammar (`OTHER/TOKEN_MISMATCH`), so the old approval can never be retroactively accepted. The retained thread is a safe candidate for a new same-thread turn after harness preparation.

## P7.C6 existing Run-1 latch — COMPLETE / architect accepted

Accepted forensic commit: `c308c765d9915844fce97d1d1f6c933e302a75aa`.

Forensic evidence: `docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_FORENSIC_EVIDENCE_2026-09-10.md`.

Architect acceptance: `docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

The existing `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` is accepted as the safe Run-1 consumed replay barrier. The forensic proved parent/file authority, mode `0600`, single link, stable identity, bounded non-empty UTF-8 JSON, exact Run-1 architect-base match, exact retained-thread SHA-256 match, `CONSUMED_OR_NO_RERUN` status semantics, zero secret-risk classes and static proof that the rejected Run-1 harness is blocked by the file.

Accepted latch SHA-256:

`50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

The absence of later Run-1 evidence/Turn-3 forensic commit values from this pre-existing latch is expected and does not weaken its replay-barrier role.

`RUN1_GLOBAL_ONE_SHOT_LATCH=ACCEPTED_EXISTING_SAFE`.

The file must not be overwritten, replaced or normalized merely to match a later representation.

## Current slice — P7.C6 same-thread continuation preparation

Status: **NEXT / ZERO-REAL-EFFECT / RESUME AFTER ACCEPTED LATCH / REAL CONTINUATION NOT AUTHORIZED**.

Frozen preparation contract remains:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_CONTRACT_2026-09-10.md`.

The obsolete step that attempted to create/replace the Run-1 global latch is skipped. Preparation must first re-verify the existing latch read-only for safe authority and exact accepted SHA-256, then continue with all remaining zero-effect requirements:

- recover exactly one `C6_RESPONSE_*`, one `C6_MEMORY_*` and one `C6_INTERRUPT_*` marker from the exact retained target artifact and store plaintext only in a root-owned `0600` recovery supplement outside Git;
- validate reuse of the retained isolated state root/controller path without cleaning it;
- create a new gated same-thread continuation harness while preserving the rejected Run-1 harness unchanged;
- implement/test the strict structural approval matcher with exact thread/new-turn/cwd/marker/sentinel relation and `EXACT_INNER|ONE_SHELL_WRAPPER` grammar;
- implement/test a distinct continuation one-shot latch without consuming it during preparation;
- prove the continuation harness has no new-thread path;
- encode but do not execute the future retained-thread continuation and the still-unused cumulative single official delete path;
- run only gate-disabled/offline/fake regression and publish sanitized preparation evidence.

`P7C6_SAME_THREAD_CONTINUATION_PREP_AUTHORIZED=YES`.

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`.

No real `model/list`, `thread/resume`, new turn, approval response, interrupt or delete may occur until the preparation commit receives independent architect review.

## Remaining lane

Only after preparation is architect-accepted may a separately frozen one-shot same-thread real continuation be authorized. It may not create a new real thread and may never answer the Run-1 Turn-3 approval request.

P8 and P9 remain blocked until P7.C6 is independently accepted.
