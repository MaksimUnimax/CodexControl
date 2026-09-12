# P7.C14 launcher recovery preparation evidence — 2026-09-12

Status: **PREPARATION ONLY / ZERO REAL EFFECT / P7.C13 RETRY FORBIDDEN**

## Binding base and inherited authority

`P7C14_PREP_BASE_HEAD=e4e57156532cf7f124e104867c29c8573b968e87`

`P7C14_PREP_BASE_TREE=91537738651a688e46b224dcd632a1d35e755a07`

`P7C13_REAL_EVIDENCE_BLOB=691b7dbd139844541def7231bf4c302cebb138bd`

`INHERITED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c`

`INHERITED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

The branch starts exactly at the consumed P7.C13 evidence head. No merge,
rebase, history rewrite, P7.C13 retry, P7.C14 real acceptance, P8 or P9 was
performed. The accepted P7.C13 harness, P7.C12 matcher and consumed P7.C13
evidence are unchanged.

## Pre-repair launcher forensics

The exact server interpreter was `/usr/bin/python`, CPython 3.12.3, with
`sys.executable=/usr/bin/python`.

Before package/import repair, with the repository only available through the
working-directory accident, bounded resolution reported:

- `tests`: namespace package, `origin=None`, no loader;
- `tests.real`: repository path through the pre-existing benign local marker;
- `tests.real.test_p7_c13_final_hard_delete_acceptance`: repository path;
- `codex_control`: missing;
- `/root/CodexControl/src` and `/root/CodexControl`: absent from effective
  import search.

`MISSING_MODULE_CLASS=NOT_RECOVERABLE_FROM_SANITIZED_AUTHORITY`

No external top-level installed package named `tests` was found when the
repository roots were excluded. Nested `*/tests` directories belonging to
other packages were not classified as a top-level shadowing package:

`EXTERNAL_TESTS_PACKAGE_CLASS=NONE_FOUND_TOP_LEVEL_TESTS_PACKAGE`

The pre-existing `tests/real/__init__.py` contained only a harmless docstring
and was materialized as the tracked canonical marker without semantic change.

## Package and launcher authority

`TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a`

`TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3`

`P7C14_LAUNCHER_BLOB=c2b9643e92206f194abdfd35ad08de3783801afe`

`DETERMINISTIC_IMPORT_ROOTS=/root/CodexControl/src:/root/CodexControl`

`CODEX_CONTROL_IMPORT_AUTHORITY=/root/CodexControl/src/codex_control/__init__.py`

The launcher binds exact HEAD, tree, launcher, inherited P7.C13 harness,
P7.C12 matcher, package-marker blobs, deterministic import roots, and clean
tracked worktree/index before selecting any executor. The P7.C14 gate is
`P7C14_FUTURE_REAL_GATE` and the P7.C14 replay barrier is exclusively
`/root/.codexcontrol/p7c14-one-shot.json`.

## Zero-effect import and parent/child smoke

Under `/usr/bin/python` and the exact deterministic `PYTHONPATH`:

- `import codex_control` resolved to repository `src` authority;
- `import tests` resolved to `/root/CodexControl/tests/__init__.py`;
- `import tests.real` resolved to `/root/CodexControl/tests/real/__init__.py`;
- P7.C12 matcher import succeeded;
- accepted P7.C13 harness import succeeded;
- harmless child import subprocess of the accepted P7.C13 future-child module
  succeeded with exit `0` and no child boot argument;
- import-only and child-import smokes created no P7.C13/P7.C14 ledger, boot,
  result, wire or approval authority and started no Codex/app-server process.

The exact P7.C14 parent shape with all P7.C14 authorization variables unset
returned finite disabled exit code `2` (`P7C14PreparationGateError`). The
P7.C14 and P7.C13 one-shot paths remained absent.

## Wrong-authority and one-shot proofs

The injected offline matrix blocked before executor selection for: wrong token,
wrong HEAD, wrong TREE, wrong P7.C14 launcher blob, wrong inherited P7.C13
harness blob, wrong P7.C12 matcher blob, wrong `tests/__init__.py` blob, wrong
`tests/real/__init__.py` blob, wrong import-root authority, tracked worktree
drift and tracked index drift. Every case recorded:

`P7C14_LEDGER_CALLS=0`

`CHILD_CALLS=0`

`CODEX_CALLS=0`

The offline temporary one-shot matrix proved first reservation succeeds,
second reservation fails, and `RESERVED`, `COMPLETED`, `FAILED`, `UNKNOWN` and
`CONFIRMED_PENDING` remain consumed. No production ledger was created and no
second child or retry was attempted.

`P7C14_LEDGER_PATH=/root/.codexcontrol/p7c14-one-shot.json`

`P7C13_LEDGER_PATH=/root/.codexcontrol/p7c13-one-shot.json`

`P7C14_LEDGER_PATH != P7C13_LEDGER_PATH=PASS`

The P7.C14 executor is a distinct subclass whose production constructor binds
the P7.C14 ledger and whose child factory explicitly supplies the deterministic
repository import roots. It does not invoke the P7.C13 parent entrypoint.

## Validation

- P7.C14 focused: `5 passed`.
- P7.C13 offline only: `75 passed`.
- P7.C12 focused: `13 passed`.
- P7.C2/C3/C4/C5 fake/non-real regressions: `106 passed`, `54 subtests passed`.
- Full non-real pytest with gates unset: `1856 passed`, `7 skipped`, `1539
  subtests`, `6 historical consumed-latch failures`.
- Unittest discovery with gates unset: `1869 tests`, `7 skipped`, `5 historical
  consumed-latch failures`, `1 historical consumed-latch error`.
- `compileall -q src tests`: PASS.
- `git diff --check`: PASS before this evidence file; rerun required after it.
- leakage/security scan: PASS; no future P7.C14 token or raw P7.C13 token was
  created or published.
- changed-path scope: the two package markers, P7.C14 launcher and this P7.C14
  evidence file only; no `src/**`, P7.C13/P7.C12 source, historical evidence,
  migrations, deployment, Telegram, P8 or P9 path changed.

## Zero-real-effect accounting

All preparation commands were import-only, offline, synthetic, or validation
commands. Production authority paths were not opened and no real flags were
used.

`REAL_CODEX_PROCESS_STARTS=0`

`APP_SERVER_STARTS=0`

`MODEL_LIST_CALLS=0`

`THREAD_START_CALLS=0`

`THREAD_RESUME_CALLS=0`

`THREAD_READ_CALLS=0`

`THREAD_LIST_CALLS=0`

`THREAD_DELETE_CALLS=0`

`TURN_START_CALLS=0`

`TURN_INTERRUPT_CALLS=0`

`APPROVAL_RESPONSES=0`

`ALLOW_RESPONSES=0`

`DENY_RESPONSES=0`

`P7C13_LEDGER_MUTATIONS=0`

`P7C14_REAL_LEDGER_CREATIONS=0`

`REAL_PERSISTENT_HOME_MUTATIONS=0`

`REAL_ISOLATED_ROOT_MUTATIONS=0`

`REAL_CONTROLLER_MUTATIONS=0`

`REAL_APPROVAL_TARGET_MUTATIONS=0`

`TELEGRAM_CALLS=0`

`REAL_CODEX_PROCESS_SIGNALS=0`

`P7C14_PREP_IMPORT_AUTHORITY=PASS`
`P7C14_PREP_PACKAGE_AUTHORITY=PASS`
`P7C14_PREP_DISTINCT_GATE_LEDGER=PASS`
`P7C14_PREP_GATE_DISABLED_SMOKE=PASS`
`P7C14_PREP_INHERITED_HARNESS_BINDING=PASS`
`P7C14_PREP_READY=YES`

`P7C14_REAL_EXECUTION_AUTHORIZED=NO`
`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`
`P9_STARTED=NO`
