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

C1 proved the physical residual families and exact 0.144.6 routing controls used by ADR-0043: `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, `history.persistence=none`; sessions/rollouts remain under persistent `CODEX_HOME`.

## P7.C2 — COMPLETE / architect accepted

Accepted implementation: `80673db644962b0cc5b1a388d64cb5902bd4f46c` after initial candidate `fbe1ea7d2f55f8f4a24d1c86e6effbbcd04e87bc`.

Exact upstream confirmation first becomes durable `DELETE_CONFIRMED_PENDING_STORAGE` with full binding retained and no premature tombstone/purge. `DELETING` restart remains ambiguity -> `DELETE_UNKNOWN`; confirmed-pending and UNKNOWN never redispatch delete.

## P7.C3 — COMPLETE / architect accepted

Accepted final implementation: `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`; accepted tree `13eea89362694da594bb2b717c037980b0df446f`.

C3 owns dedicated persistent `CODEX_HOME` + distinct isolated state root, exact per-generation 0.144.6 capability authority, descriptor/no-follow protected-path checks, exact SQLite/log/history routing, exclusive profile reservation/quiescence and manager-owned bounded root lifecycle.

## P7.C4 — COMPLETE / architect accepted

Accepted lineage:

- initial: `70cdf0edc3f319c0254313eabc5d3c56c2f9ef16`;
- first repair: `fe646af1487d13571337e605641ecc86dbb1f6c7`;
- final accepted: `df161566cab5f8fa7ccf70f94379c78a9fb02ffe`;
- accepted tree: `be2ea7a5eead9b2d61039a2d98ec4d2b80047526`.

Acceptance: `docs/evidence/p7c4/P7C4_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

C4 adds schema-v4 UNKNOWN containment metadata and composes the corrected local hard-delete lifecycle. Confirmed cleanup is `reserve -> shutdown -> quiesce -> isolated payload reset -> persistent exact-thread scan -> finalize -> release`. UNKNOWN remains official UNKNOWN, retains binding and no tombstone/finalizer, while isolated local containment may be recorded separately. Isolated reset is crash-resumable and the cleanup coordinator is bound to the actual protected controller SQLite.

## P7.C5 — COMPLETE / architect accepted

Accepted corrected proof lineage:

- corrected architect base: `44dcb874659940998734fdfe76fb8683250be05d`;
- proof candidate: `d963a4982382d28a90ed18ac9d6384ba424f7dc0`;
- architect proof-review correction: `29448176312d47a51b7b321a6268398eff724c4a`;
- final accepted proof repair: `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`;
- accepted tree: `c4d5310a2afb05fc4f2f92eea822a1ccc7a8c88c`.

Acceptance: `docs/evidence/p7c5/P7C5_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

Historical stopped C5 proof `581a31e9a450230eed50bad6c247159898d72f7f` remains evidence of a corrected architect-contract mistake, not a production C4 defect.

C5 proves the complete fake hard-delete acceptance across accepted C2/C3/C4: production exact-thread gate, independent test-only marker oracle, full isolated state/log family cleanup, persistent residual blockers, UNKNOWN containment, both isolated-subtree crash/retry paths, concurrency/cancellation, no-P1 replay, actual controller DB identity/schema authority and unrelated session/history baseline preservation.

Final executor evidence: dedicated C5 tests `15`; focused `248`; ordinary full regression `1065`; zero skipped/failures/errors. Production source changed: no. All real Codex/Telegram/credential/production-effect counters: zero.

Dynamic mount/namespace mutation was intentionally not run; the bounded risk is carried to C6/P13.

## Current slice

**P7.C6 — NEXT / REAL-EFFECT ONE-SHOT CONTRACT FROZEN.**

Contract:

`docs/evidence/p7c6/P7C6_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`.

C6 is the first separately authorized real Codex run after the correction lane. It may create exactly one new disposable thread, run the bounded real T3 persistence/approval/interrupt proof, and dispatch exactly one official P1.9 `thread/delete` through the complete corrected application cleanup path.

C6 must use an explicitly designated already-authenticated **CodexControl-dedicated** persistent `CODEX_HOME`; historical `codex1/codex2/codex3` names are not automatically eligible. A fresh run-owned isolated state root and separate synthetic controller DB are mandatory. If no explicit dedicated profile authority exists, stop before authenticated business RPC with `P7C6_PROFILE_AUTHORITY_REQUIRED`; never copy/symlink/migrate credentials or fall back to a shared home.

Before real business RPC, C6 must also perform a read-only mount/alias preflight. Any unresolved bind-mount/namespace ambiguity stops the run; no privileged mount mutation is authorized.

PASS requires exact real `DELETE_CONFIRMED`, complete `DELETE_CONFIRMED_PENDING_STORAGE` local cleanup to `DELETED`, zero exact target thread residual, zero known synthetic marker residual across measured dialogue-bearing persistent/isolated families, preserved unrelated baseline and green ordinary regression.

Any `DELETE_UNKNOWN`, persistent residual, local confirmed-pending failure, profile-authority failure, mount-alias uncertainty, production defect or inconclusive physical proof keeps P8/P9 blocked. No real C6 run is automatically retried.

## Remaining lane

After independent architect acceptance of P7.C6 only:

- P8 deployment packaging/rollback reopens;
- P9 server-80 live Telegram acceptance reopens.

## Current non-goals

Do not touch the historical rejected P7 thread. Do not use a shared/interactively owned Codex home. Do not copy credentials. Do not call `thread/read`/`thread/list`. Do not retry an ambiguous delete. Do not manually delete persistent session/history to manufacture a pass. Do not start P8/P9 before C6 acceptance.
