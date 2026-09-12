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
- `git diff --check`: PASS after the final evidence edit.
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

## Repair-1 execution record

The architect review identified the prior `P7C14_PREP_READY=YES` statement as
superseded: the successor executor inherited a P7.C13 `run()` interface that
required `expected_harness_blob`, while the P7.C14 contract exposes the
accepted inherited value as `expected_p7c13_harness_blob`. Repair-1 changes
only the P7.C14 launcher and this evidence file.

`P7C14_REPAIR1_BASE_HEAD=33f27a2ecba5f81d20651e6456bd2e137a4f5274`

`P7C14_REPAIR1_BASE_TREE=04c0733eabea2763731bf99c765fc16fd95fec31`

`PRIOR_P7C14_LAUNCHER_BLOB=c2b9643e92206f194abdfd35ad08de3783801afe`

`PRIOR_P7C14_EVIDENCE_BLOB=7e2ad8d0266fe9fbbb8c9f5d5079c0d6b512c8f5`

`P7C14_REPAIR1_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8`

The final evidence blob is the Git blob ID of this completed file and is
reported by the final commit/remote readback; it cannot be self-embedded in
its own content without changing that blob ID.

### Contract adaptation

`P7C14_CONTRACT_ADAPTATION_CLASS=P7C14PreparedFutureRealExecutor.run`

`P7C14_CONTRACT_ADAPTATION_TARGET=p7c13.FutureArchitectContract`

`P7C14_CONTRACT_ADAPTATION_FIELDS=authorization_token(P7.C14 inert),expected_head(P7.C14),expected_tree(P7.C14),expected_harness_blob(accepted P7.C13 harness)`

`P7C14_CONTRACT_ADAPTATION_LAUNCHER_AS_HARNESS=NO`

The override rejects null, non-P7.C14 and malformed contracts before ledger
reservation, constructs exactly the inherited four-field contract, and calls
the inherited executor once. Synthetic fixtures distinguish the launcher
blob (`synthetic-p7c14-launcher`) from the inherited harness blob
(`synthetic-p7c13-harness`).

### Exact-authorized synthetic handoff

The positive test passed the complete P7.C14 source-bundle gate and traversed
the production-shaped `p7c14_real_entrypoint`, the concrete
`P7C14PreparedFutureRealExecutor.run` override and the inherited
`p7c13.PreparedFutureRealExecutor.run` implementation. It used only temporary
ledger, boot and result paths, a counting temporary ledger, a harmless child
command descriptor and a fake watchdog. The watchdog wrote a bounded,
boot-bound synthetic PASS result; no child process was started.

`P7C14_SOURCE_GATE=PASS`

`P7C14_EXECUTOR_CALLS=1`

`P7C14_CONTRACT_ADAPTATION=PASS`

`TEMP_P7C14_LEDGER_RESERVATIONS=1`

`P7C13_GLOBAL_LEDGER_MUTATIONS=0`

`P7C13_GLOBAL_LEDGER_ACCESS=0`

`REAL_CODEX_CALLS=0`

`REAL_CHILD_CALLS=0`

`FAKE_CHILD_DISPATCHES=1`

`BOOT_SOURCE_HEAD=synthetic-p7c14-head`

`BOOT_SOURCE_TREE=synthetic-p7c14-tree`

`BOOT_HARNESS_BLOB=synthetic-p7c13-harness`

`PARENT_SYNTHETIC_RESULT=accepted finite PASS`

`P7C14_TEMP_LEDGER_PATH != P7C13_GLOBAL_LEDGER_PATH=PASS`

No `AttributeError`, missing contract field, real ledger reservation, real
child, Codex call, RPC, approval response, interrupt, delete or signal
occurred. Production construction remains bound to
`/root/.codexcontrol/p7c14-one-shot.json`; the inherited P7.C13 ledger path
was not used as P7.C14 replay authority.

### Negative matrix and validation

The focused matrix blocks wrong token, HEAD, tree, P7.C14 launcher, inherited
P7.C13 harness, matcher, package markers, import roots and tracked-clean
authority before executor selection. Direct executor tests block null and
non-P7.C14 contracts before temporary ledger reservation. The adaptation
test proves `expected_harness_blob` equals only the accepted inherited P7.C13
harness and not the P7.C14 launcher. The temporary latch test proves the
exclusive reservation and terminal consumption states.

The exact gate-disabled command with all P7.C14 authorization variables unset
returned finite exit `2`; P7.C14 and P7.C13 production ledgers remained
absent, with zero Codex/RPC effect.

- P7.C14 Repair-1 focused: `8 passed`.
- P7.C13 offline-only: `71 passed`.
- P7.C12 focused: `13 passed`.
- P7.C2/C3/C4/C5 fake/non-real: `106 passed`.
- Full non-real pytest: `1859 passed`, `7 skipped`, `1541 subtests`, `6
  immutable historical consumed-latch failures`.
- Unittest discovery: `1872 tests`, `7 skipped`, `5 immutable historical
  consumed-latch failures`, `1 immutable historical consumed-latch error`.
- compileall: PASS.
- `git diff --check`: PASS.
- leakage/security scan: PASS.

The six pytest failures and five unittest failures plus one error are the
pre-existing consumed-latch/authority-presence failures in P7.C7 through
P7.C11. No historical source or evidence was changed to affect them.

### Repair-1 zero-real-effect accounting

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

`REAL_ISOLATED_MUTATIONS=0`

`REAL_CONTROLLER_MUTATIONS=0`

`REAL_APPROVAL_TARGET_MUTATIONS=0`

`TELEGRAM_CALLS=0`

`REAL_CODEX_PROCESS_SIGNALS=0`

`P7C14_REPAIR1_CONTRACT_ADAPTATION=PASS`
`P7C14_REPAIR1_EXACT_AUTHORIZED_SYNTHETIC_HANDOFF=PASS`
`P7C14_REPAIR1_TEMP_LEDGER_ONLY=PASS`
`P7C14_REPAIR1_INHERITED_BOOT_BINDING=PASS`
`P7C14_REPAIR1_GATE_DISABLED_SMOKE=PASS`
`P7C14_PREP_READY=YES`

`P7C14_REAL_EXECUTION_AUTHORIZED=NO`
`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`
`P9_STARTED=NO`
