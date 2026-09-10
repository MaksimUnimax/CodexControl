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

Independent review established acceptance-harness defects, not production defects:

1. Run-1 `_ExactApprovalOperator` used literal guessed command strings instead of the already-proven structural `EXACT_INNER|ONE_SHELL_WRAPPER` relation and did not enforce exact turn/cwd identity.
2. The declared host-level Run-1 one-shot ledger was checked but never materialized by the harness.
3. The Run-1 failure-path recovery ledger retained the raw target thread ID but did not retain the generated synthetic marker plaintext required for a later all-marker erasure oracle.

The Run-1 approval result remains `RESPONSE_UNKNOWN`; the old request must never be answered/retried/reinterpreted.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

P7.C6 remains **NOT ACCEPTED**.

## P7.C6 retained Turn-3 forensic — COMPLETE / architect accepted

Accepted forensic commit: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.

Evidence: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_FORENSIC_EVIDENCE_2026-09-10.md`.

Architect review: `docs/evidence/p7c6/P7C6_RETAINED_TURN3_ARCHITECT_REVIEW_2026-09-10.md`.

The zero-real-effect forensic proves exact Run-1 Turn 3 is durably terminal `INTERRUPTED`, its single command item is `COMPLETED`, no persisted approval request/decision/response remains, no run-owned delayed process/sentinel remains, and scan/parse errors are zero. The persisted Turn-3 command is outside the historical safe approval grammar (`OTHER/TOKEN_MISMATCH`), so the old approval can never be retroactively accepted. The retained thread is a safe candidate for a new same-thread turn after harness preparation.

## P7.C6 same-thread continuation preparation — BLOCKED AT EXISTING RUN-1 LATCH

Preparation contract:

`docs/evidence/p7c6/P7C6_SAME_THREAD_CONTINUATION_PREP_CONTRACT_2026-09-10.md`.

The zero-effect preparation started from its exact architect base and stopped before any repository or Codex effect because `/root/.codexcontrol/p7c6-real-one-shot-ledger.json` already exists. Filesystem ownership/mode were safe, but its bytes did not match the newly prescribed latch representation. Overwrite is forbidden.

This stop does not establish that the existing latch is wrong. The rejected Run-1 harness itself blocks replay whenever this file exists and is non-empty; therefore exact JSON byte/field equality with the later prep format is stronger than the historical replay-barrier requirement. Conversely, a safe-looking file at the path must not be silently adopted as CodexControl authority without classification.

## Current slice — Run-1 existing-latch forensic

Status: **NEXT / ZERO-REAL-EFFECT / READ-ONLY**.

Frozen contract:

`docs/evidence/p7c6/P7C6_RUN1_EXISTING_LATCH_FORENSIC_CONTRACT_2026-09-10.md`.

The forensic may only read and classify the existing latch with bounded no-follow checks. It must not overwrite, rename, delete or otherwise mutate it, and must perform zero Codex/app-server/business RPC effects.

It must establish filesystem identity/safety, bounded content SHA/representation class, safe key/value classes without exposing unknown values, whether known Run-1 authorities are referenced, secret-risk counters, and whether the published Run-1 harness is definitely blocked by the existing non-empty latch.

Possible classifications are `SAFE_REPLAY_BARRIER_CANDIDATE`, `SAFE_BUT_SEMANTICALLY_UNKNOWN`, or `UNSAFE_OR_AMBIGUOUS`.

Current authority:

`P7C6_SAME_THREAD_PREP_CONTINUATION_AUTHORIZED=NO`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

No real `thread/resume`, new turn, approval response, interrupt or delete may occur until the latch forensic receives independent architect review and the continuation preparation itself is later completed and accepted.

## Remaining lane

If the existing latch is architect-accepted as a safe Run-1 replay barrier, continuation preparation may resume from the next zero-effect gate without overwriting it. Preparation must still recover the three Run-1 markers, validate retained topology, build/test the structural approval matcher, implement the separate continuation latch and materialize a new gated same-thread harness. Only after that preparation is independently accepted may any real same-thread continuation be considered.

P8 and P9 remain blocked until P7.C6 is independently accepted.
