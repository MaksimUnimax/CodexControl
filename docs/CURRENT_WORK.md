# Current work authority

Date: 2026-09-10

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority remains `codex-cli 0.144.6`; generated app-server schema SHA-256 remains `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete at their accepted boundaries. P6 final accepted commit remains `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Historical schema-v1/v2/v3 authorities remain immutable. Current schema is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- No live Telegram/deployment acceptance has occurred.

## Rejected original P7

Original real P7 under ADR-0042 remains **REJECTED / ARCHITECTURE BLOCKED historical evidence**. Exactly one official P1.9 `thread/delete` returned terminal `DELETE_UNKNOWN`; it was not retried/read/list-reconciled. Final forensic commit `5aac49bd1b8a349343db52071520beed7f95592d` proved `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL` with five synthetic marker matches. Issue #38 remains historical blocker evidence.

The historical rejected thread must never be touched again by the correction lane.

## P7.C1 — COMPLETE / architect accepted

Accepted discovery: `a9900471d0599be21b1a1834301c4421d95acb29`.

C1 proved the physical residual families and exact 0.144.6 routing controls used by the correction lane: `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, `history.persistence=none`; sessions/rollouts remain under persistent `CODEX_HOME`.

## P7.C2 — COMPLETE / architect accepted

Accepted implementation: `80673db644962b0cc5b1a388d64cb5902bd4f46c` after initial candidate `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc`.

Exact upstream confirmation first becomes durable `DELETE_CONFIRMED_PENDING_STORAGE` with full binding retained and no premature tombstone/purge. `DELETING` restart remains ambiguity -> `DELETE_UNKNOWN`; confirmed-pending and UNKNOWN never redispatch delete.

## P7.C3 — COMPLETE / architect accepted

Accepted final implementation: `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`; accepted tree `13eea89362694da594bb2b717c037980b0df446f`.

C3 owns explicit configured persistent `CODEX_HOME` plus a distinct CodexControl-owned isolated state root, exact per-generation 0.144.6 capability authority, descriptor/no-follow protected-path checks, exact SQLite/log/history routing, CodexControl-local profile reservation/quiescence and manager-owned bounded root lifecycle.

ADR-0045 supersedes the earlier mistaken interpretation that the persistent `CODEX_HOME` itself must be exclusive to CodexControl. The accepted runtime reservation already scopes itself to CodexControl-managed children; it is not a host-wide lock on the persistent home.

## P7.C4 — COMPLETE / architect accepted

Accepted final implementation: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`; accepted tree `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.

C4 adds schema-v4 UNKNOWN containment metadata and composes the corrected local hard-delete lifecycle. Confirmed cleanup is `reserve -> shutdown -> quiesce -> isolated payload reset -> persistent exact-thread scan -> finalize -> release`. UNKNOWN remains official UNKNOWN, retains binding and no tombstone/finalizer, while isolated local containment may be recorded separately. Isolated reset is crash-resumable and the cleanup coordinator is bound to the actual protected controller SQLite.

Under ADR-0045, C4 shutdown/quiescence applies only to CodexControl-owned children that can use the exact isolated state root. It does not authorize stopping unrelated Codex processes that merely share the persistent `CODEX_HOME`.

## P7.C5 — COMPLETE / architect accepted

Accepted final proof: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`; accepted tree `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`.

C5 proves the complete fake hard-delete acceptance across accepted C2/C3/C4: production exact-thread gate, independent test-only marker oracle, full isolated state/log family cleanup, persistent residual blockers, UNKNOWN containment, both isolated-subtree crash/retry paths, concurrency/cancellation, no-P1 replay, actual controller DB identity/schema authority and unrelated session/history baseline preservation.

Final executor evidence: dedicated C5 tests `15`; focused `248`; ordinary full regression `1065`; zero skipped/failures/errors. Production source changed: no. All real Codex/Telegram/credential/production-effect counters: zero.

## ADR-0045 — shared persistent CODEX_HOME correction

ADR-0045 is binding and supersedes only the persistent-home exclusivity clauses of ADR-0043 and downstream C6 wording derived from them.

A configured authenticated persistent `CODEX_HOME` may be concurrently shared by independent Codex processes/applications. CodexControl owns only its own app-server child/generation, its own isolated `sqlite/logs` state root, its controller SQLite and its process-local reservation/quiescence authority.

Other Codex processes using the same persistent home are allowed and must not be killed/stopped/signaled merely to make the home quiet. They are a blocker only if they use or ambiguously alias the exact CodexControl-owned isolated state root/controller boundary.

## P7.C6 Run 1 — REAL RUN EXECUTED / REJECTED

Run-1 failure/evidence commit:

`785a82e2e9bc392173ea1e910b490f84cfa590b2`

Architect review:

`docs/evidence/p7c6/P7C6_RUN1_ARCHITECT_REVIEW_2026-09-10.md`

Run 1 used `/root/.codex_second` in the accepted `SHARED_AUTHENTICATED` mode. Shared-home process presence was allowed; isolated-root/controller external users were zero; unrelated-process termination and manual persistent-home cleanup were zero.

The single authorized real run performed one `model/list`, one new disposable thread, one runtime-generation resume and three turns. Turn 1 and Turn 2 passed their bounded persistence proof. Run 1 then stopped at the Turn-3 approval gate with `P7C6_APPROVAL_NOT_EXACTLY_ALLOWED`. No interrupt, official delete, thread/read or thread/list occurred. The raw target thread identity remains only in the root-owned retained recovery ledger.

The zero-effect forensic could not reconstruct the exact normalized approval request and recorded `C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN`; therefore the old approval request must never be answered/retried or reinterpreted.

Independent architect code review establishes two C6 harness defects:

1. `_ExactApprovalOperator` used literal membership against three guessed command strings instead of the previously proven structural `EXACT_INNER|ONE_SHELL_WRAPPER` grammar and did not enforce exact Turn-3/cwd identity.
2. The declared host-level `ONE_SHOT_LEDGER` is only checked and is never materialized by the harness; the actual recovery ledger is a fresh per-run file under `/tmp`.

These are acceptance-harness defects, not established P1.7/P1.8/P1.9/C3/C4/C5 production defects. Operator discipline prevented a duplicate real run.

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`.

P7.C6 remains **NOT ACCEPTED**.

## Current slice — retained Turn-3 forensic

The sole next executable action is a **zero-real-effect retained Turn-3 forensic**.

Frozen contract:

`docs/evidence/p7c6/P7C6_RETAINED_TURN3_FORENSIC_CONTRACT_2026-09-10.md`

It may read the retained root-only recovery identity and the exact already-persisted target session/rollout artifact locally, but may perform zero Codex process/app-server starts and zero Codex business RPCs.

It must determine whether Run-1 Turn 3 has a durable terminal record, whether any approval/command item remains pending/running/ambiguous, and whether any run-owned delayed process/sentinel remains. Raw IDs, prompts, responses, command content and markers must not enter Git evidence.

Current authority:

`P7C6_CONTINUATION_AUTHORIZED=NO`.

No new thread, resume, turn, approval response, interrupt, delete, read or list is authorized until this forensic receives architect review.

## Remaining lane

Only after a safe retained-Turn-3 boundary is independently established may the architect decide whether to authorize a tightly bounded same-thread continuation with a repaired harness. Any continuation must not create a new real thread and must never resend the Run-1 approval request.

P8 and P9 remain blocked until P7.C6 is independently accepted.
