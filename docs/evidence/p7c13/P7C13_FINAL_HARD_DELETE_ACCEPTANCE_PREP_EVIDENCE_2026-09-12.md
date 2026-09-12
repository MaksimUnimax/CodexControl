# P7.C13 final hard-delete acceptance preparation evidence — 2026-09-12

Status: PREPARATION ONLY / ZERO REAL EFFECT / NO REAL AUTHORIZATION

## Authority and scope

- Preparation branch: `prep-p7-c13-final-hard-delete-acceptance-2026-09-12`.
- Exact accepted P7.C12 base: `a5c66a778800d1c5ee5811d97d961fe0dccd677c`.
- Exact accepted P7.C12 tree: `e6a46445d11d660a50891eabf412b01aef883fca`.
- Exact accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.
- Architect `origin/main`: `ddc3cb48cbe82bcee6d2b5387774287b66d582fb`.
- Architect `origin/main` tree: `c6288dfefecce00bbca7e6ff84aacda4b20fce8d`.
- Harness blob before commit: `a6962a14ffd4c10d6e4ff072cd24622077f839c2`.
- Helper: none.
- Changed paths are limited to this evidence file and `tests/real/test_p7_c13_final_hard_delete_acceptance.py`.
- No `src/**`, controller schema/migration, ADR, Telegram, deployment, CURRENT_WORK, ROADMAP, or historical P7.C6–P7.C12 file was changed.

## Future-real gate and routing

`P7C13_FUTURE_REAL_GATE=DISABLED`. The entry point requires an absent architect contract object containing an authorization token, expected HEAD, and expected TREE, plus matching explicit environment values. Ordinary discovery and direct execution therefore reach no runtime, process, RPC, approval, interrupt, or delete operation. No future authorization environment, latch, recovery ledger, credential, target, or real state root was created.

Future routing is frozen as assertions only: executable `/usr/local/bin/codex`, version `codex-cli 0.144.6`, schema aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`, shared authenticated `CODEX_HOME=/root/.codex_second`, isolated `CODEX_SQLITE_HOME=<fresh>/sqlite`, `sqlite_home=<same>`, `log_dir=<fresh>/logs`, and `history.persistence=none`.

The shared-home correction is carried forward: concurrent users/processes of `/root/.codex_second` are allowed; only the exact P7.C13 isolated root, sqlite/logs, controller DB, ledger, workdir, approval target, and children created by the future run may be reserved or signalled. Unrelated shared-home termination calls are fixed at zero.

## Frozen future effect budget

| Effect | Maximum |
|---|---:|
| New thread / `thread/start` / `thread/resume` | 1 / 1 / 1 |
| `model/list` | 1 |
| `turn/start` | 4 |
| approval responses / ALLOW responses | 1 / 1 |
| `turn/interrupt` / official `thread/delete` | 1 / 1 |
| `thread/read` / `thread/list` | 0 / 0 |
| second child / real retry / Telegram | 0 / 0 / 0 |

The offline `EffectBudget` rejects an over-budget operation. Preparation observed zero real calls in every category.

## Offline proof results

The focused P7.C13 preparation suite passed `17` tests.

- Turn 1/Turn 2: exact fresh binding, START_CONFIRMED model, one start, one generation restart, one resume, remembered marker, definitive completion, no historical selection.
- Turn 3: exact `/bin/bash -lc 'touch <target>'` projection through the accepted P7.C12 matcher; explicit `sandbox_permissions=require_escalated`; one ALLOW candidate only; all non-match, identity, sequence, SHA, target, pre-existing-target, second-approval, and missing-target-existence cases fail closed.
- Turn 4: independent exact `sleep 120` stimulus; no approval reuse; exact binding; one interrupt; UNKNOWN, second interrupt, and unexpected approval fail closed.
- Delete eligibility: unreachable until all four turn gates, pre-delete material observation, and exact IDLE binding pass.
- Pre-delete oracle: bounded no-follow scans cover persistent `sessions/**`, optional history, isolated `sqlite/**`, and isolated `logs/**`; evidence shape is marker hash/count/class only; an empty observation is inconclusive.
- Post-delete oracle: exact official/application statuses, bounded tombstone, no live binding, valid envelope, zero isolated descendants, zero target thread/marker residuals, zero scan/proof errors, owned-group quiescence, no unrelated signals, and budget compliance. Thread-only, marker-only, isolated, and scan-error residuals each fail independently.
- Boundary safety: read-only mount/identity seam and exact owned-boundary external-user block are covered; shared-home process presence alone is allowed.
- One-shot/watchdog: normal completion, timeout, residual group, cancellation/error, latch reuse, second-child, and retry cases are covered; all unsafe cases fail closed.

## Synthetic production delete-chain results

The suite used a fresh synthetic schema-v4 controller database, `IsolationPathAuthority`, `IsolatedStateRoot`, the accepted `DeleteStorageCleanupCoordinator`, and production `DialogueDeleteService`. No real adapter or runtime generation was acquired.

- Confirmed success: one synthetic official delete, durable confirmed-pending transition, owned shutdown/quiescence/reset, persistent target scan, finalize, bounded tombstone, release, and `DELETED`; isolated payload descendants and target material become zero.
- `DELETE_UNKNOWN`: terminal UNKNOWN, local isolated containment only, no external retry, no read/list, no finalizer, no tombstone, and retained dialogue authority.
- Confirmed-pending scan failure: confirmed-pending remains durable and external delete is not retried.
- Marker-only residual: production exact-thread attribution can be zero while the independent acceptance oracle rejects the result.

## Validation record

- Focused P7.C13: `17 passed`.
- Focused accepted P7.C12 matcher: `13 passed`; matcher blob remained unchanged.
- Relevant P7.C2/C3/C4/C5 fake/non-real regression: `106 passed`.
- Complete non-real regression with all real gates unset: `1793 passed, 7 skipped, 6 deselected`; historical consumed-latch checks remain unchanged and are reported separately.
- `compileall`: PASS; no real process path is reachable.
- `git diff --check`: PASS.
- Leakage/security AST and text scan: PASS; no raw retained IDs, prior target paths, raw wire/prompt/output, credentials/tokens, root-only recovery JSON, or effect call surface was introduced.

Historical consumed-latch handling: the retained P7.C7/P7.C8/P7.C9/P7.C10/P7.C11 latch/preflight assertions were deselected because their expected absence contradicts the binding instruction to preserve consumed historical latches. No latch was deleted, rewritten, or otherwise mutated.

## Zero-real-effect accounting

| Category | Observed |
|---|---:|
| Real Codex process / app-server starts | 0 / 0 |
| Model list / thread start / resume / read / list / delete | 0 / 0 / 0 / 0 / 0 / 0 |
| Turn start / interrupt | 0 / 0 |
| Approval / ALLOW / DENY responses | 0 / 0 / 0 |
| Real persistent-home / isolated-root / controller DB / approval-target mutations | 0 / 0 / 0 / 0 |
| Telegram / real Codex signals | 0 / 0 |
| Historical authority mutations | 0 |

Temporary directories and SQLite files created by offline tests were synthetic test-owned fixtures only and were removed by test teardown. The pre-existing untracked `tests/real/__init__.py` was preserved and not staged.

P7C13_PREP_HARNESS_READY=YES
P7C13_PREP_APPROVAL_MATCHER_GATE=PASS
P7C13_PREP_INTERRUPT_GATE=PASS
P7C13_PREP_DELETE_CHAIN_GATE=PASS
P7C13_PREP_POST_DELETE_ORACLE=PASS
P7C13_PREP_ONE_SHOT_GATE=PASS
P7C13_REAL_EXECUTION_AUTHORIZED=NO
P7C13_REAL_ALLOW_AUTHORIZED=NO
P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO
P8_STARTED=NO
P9_STARTED=NO
