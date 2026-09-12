# P7.C14 launcher recovery preparation contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / DISTINCT SUCCESSOR / P7.C13 RETRY FORBIDDEN**

## Purpose

P7.C14 is a distinct successor acceptance slice created because consumed P7.C13 failed before harness import. P7.C13 MUST NOT be rerun.

P7.C14 preparation has two purposes only:

1. prove and repair the exact Python launcher/import authority that P7.C13 failed to prove;
2. prepare a distinct P7.C14 parent gate and one-shot authority that reuses the accepted P7.C13 hard-delete implementation as library code without invoking the P7.C13 parent command.

No real Codex/app-server/RPC/thread/Turn/approval/interrupt/delete effect is authorized by this preparation contract.

## Historical authority

Consumed P7.C13 real evidence branch head:

`e4e57156532cf7f124e104867c29c8573b968e87`

Accepted P7.C13 hard-delete implementation source:

- commit `a347a72bdc8235e31ff6165ca3dd830c1adae9e5`;
- tree `0d4fef93c99a57fd93a2065280555c5cb06104c3`;
- harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Binding review:

`docs/evidence/p7c13/P7C13_REAL_EXECUTION_ARCHITECT_REVIEW_2026-09-12.md`

P7.C13 remains:

- consumed;
- final verdict FAIL;
- retry unauthorized;
- hard-delete behavior not exercised.

## Exact preparation base

The P7.C14 preparation branch MUST start from the consumed P7.C13 real evidence branch head:

`e4e57156532cf7f124e104867c29c8573b968e87`

This preserves both the accepted harness and the immutable sanitized P7.C13 failure evidence.

## A. Zero-effect launcher forensics

Before changing source, inspect the exact server interpreter/runtime read-only:

- `command -v python`;
- `python --version`;
- `sys.executable`;
- bounded `sys.path` classes/paths;
- `importlib`/PathFinder authority for `tests`, `tests.real`, `tests.real.test_p7_c13_final_hard_delete_acceptance`, and `codex_control`;
- origin path/class of any externally installed `tests` package;
- whether the repository `src/` directory is importable under the exact real-command environment;
- whether the project is installed into that interpreter and, if so, from which safe path/class.

Do not publish sensitive environment values. Publish only safe path classes, module names, booleans and hashes where appropriate.

The exact raw missing-module text from P7.C13 may be recovered from local shell/session output if available, but must be sanitized before Git evidence.

## B. Deterministic repository package authority

The accepted source has no tracked `tests/__init__.py` and no tracked `tests/real/__init__.py`.

P7.C14 preparation must make the real module entry deterministic and independent of third-party `tests` packages.

Required tracked package markers:

- `tests/__init__.py`;
- `tests/real/__init__.py`.

If a pre-existing untracked `tests/real/__init__.py` exists locally, inspect it before staging. If it is empty or a benign package marker equivalent to the canonical tracked file, materialize it as the tracked canonical package marker. If it contains any other substantive content, STOP and report owner review required; do not overwrite it silently.

The exact future launcher environment must include repository import authority for both:

- `/root/CodexControl/src`;
- `/root/CodexControl`.

Prefer exact deterministic future `PYTHONPATH`:

`/root/CodexControl/src:/root/CodexControl`

Do not depend on pytest path injection, current editable installation, or an unrelated site-packages `tests` package.

## C. Exact zero-effect import smoke proof

Using the same `python` executable that a future real parent would use and the exact deterministic future `PYTHONPATH`, prove without invoking any real gate:

- `import codex_control` succeeds from repository `src` authority;
- `import tests` resolves to repository authority;
- `import tests.real` resolves to repository authority;
- `import tests.real.test_p7_c12_strict_approval_matcher` succeeds;
- `import tests.real.test_p7_c13_final_hard_delete_acceptance` succeeds;
- no P7.C13 ledger/boot/result/wire/journal is created by import;
- no app-server/Codex process starts by import.

Do NOT execute the P7.C13 `--p7c13-real-run` parent command even with its gate unset. P7.C13 retry prohibition is absolute.

## D. Distinct P7.C14 launcher

Create:

`tests/real/test_p7_c14_final_hard_delete_recovery.py`

It MUST be a thin successor launcher around the accepted P7.C13 implementation, not a copy/rewrite of the large hard-delete harness.

The P7.C14 launcher must have distinct authority:

- gate environment `P7C14_FUTURE_REAL_GATE`;
- exact expected source environment names under the `P7C14_` prefix;
- CLI parent mode `--p7c14-real-run`;
- global one-shot ledger `/root/.codexcontrol/p7c14-one-shot.json`;
- distinct authorization token in a later contract;
- fresh run identity/thread;
- no call to the P7.C13 parent `--p7c13-real-run` path.

It may import and reuse the accepted P7.C13 classes/functions as library authority.

## E. New one-shot authority must be truly distinct

P7.C14 MUST NOT use `/root/.codexcontrol/p7c13-one-shot.json` as its replay barrier.

Its authoritative replay barrier is only:

`/root/.codexcontrol/p7c14-one-shot.json`

P7.C14 preparation must prove offline:

- P7.C13 ledger path is never created, deleted, modified or consulted as P7.C14 replay authority;
- P7.C14 first reservation is exclusive;
- P7.C14 second reservation fails;
- PASS/FAIL/TIMEOUT/UNKNOWN/CONFIRMED_PENDING all permanently consume P7.C14 after reservation;
- no retry/second child path exists.

Internal inherited schema labels or helper names from P7.C13 are not execution authorization. The P7.C14 gate, ledger and parent entrypoint are the successor authority.

## F. Source-bundle binding

The P7.C14 parent gate must bind at minimum:

- exact current HEAD;
- exact tree;
- P7.C14 launcher blob;
- accepted inherited P7.C13 harness blob;
- accepted P7.C12 matcher blob;
- tracked source/index clean state;
- deterministic package marker blobs;
- deterministic import-root authority.

Any mismatch blocks before P7.C14 ledger creation.

## G. Future child import authority

The future P7.C14 parent may reuse the accepted P7.C13 child mode as implementation library authority, but its child subprocess must inherit or receive the exact deterministic repository import environment.

Preparation must prove with a harmless subprocess that the exact child module import works under the future environment without setting any real gate and without starting Codex.

Do not directly invoke the real child mode against root-only production boot authority during preparation.

## H. P7.C14 gate-disabled parent smoke

After the P7.C14 launcher exists, execute its parent CLI with ALL P7.C14 authorization variables unset under the exact future Python/PYTHONPATH environment.

Expected:

- launcher imports successfully;
- source/import preflight executes only read-only work;
- P7.C14 gate is disabled;
- exit is a finite disabled/non-authorized code;
- `/root/.codexcontrol/p7c14-one-shot.json` remains absent;
- no boot/result authority is created;
- no Codex/app-server/process group is created;
- no P7.C13 authority is touched.

This gate-disabled smoke is required before any future real authorization.

## I. Zero-real-effect boundary

During all P7.C14 preparation:

`REAL_CODEX_PROCESS_STARTS=0`

`APP_SERVER_STARTS=0`

`MODEL_LIST_CALLS=0`

`THREAD_START_CALLS=0`

`THREAD_RESUME_CALLS=0`

`TURN_START_CALLS=0`

`APPROVAL_RESPONSES=0`

`ALLOW_RESPONSES=0`

`DENY_RESPONSES=0`

`TURN_INTERRUPT_CALLS=0`

`THREAD_DELETE_CALLS=0`

`P7C13_LEDGER_MUTATIONS=0`

`P7C14_REAL_LEDGER_CREATIONS=0`

`TELEGRAM_CALLS=0`

No future P7.C14 token may be invented or set during preparation.

## J. Allowed tracked changes

Allowed:

- `tests/__init__.py`;
- `tests/real/__init__.py`;
- `tests/real/test_p7_c14_final_hard_delete_recovery.py`;
- `docs/evidence/p7c14/P7C14_LAUNCHER_RECOVERY_PREP_EVIDENCE_2026-09-12.md`.

If strictly required, one P7.C14-only test helper under `tests/real/` may be added, but prefer keeping the successor launcher self-contained.

Forbidden:

- `src/**`;
- accepted P7.C13 harness modification;
- accepted P7.C12 matcher modification;
- P7.C6-P7.C13 historical evidence/source mutation;
- migrations;
- deployment;
- Telegram;
- P8/P9 work.

## K. Required tests

At minimum prove offline:

1. exact interpreter identity is recorded safely;
2. pre-repair module-resolution root cause is classified;
3. repository `tests` package wins over any external `tests` package after repair;
4. repository `codex_control` import resolves under exact deterministic future import roots;
5. P7.C12 import succeeds;
6. P7.C13 harness import succeeds with zero effects;
7. import-only smoke creates no P7.C13/P7.C14 ledger;
8. P7.C14 parent gate unset imports and exits disabled without ledger;
9. wrong token/head/tree/launcher/harness/matcher/package-marker authority blocks before ledger;
10. P7.C14 ledger path is distinct from P7.C13;
11. P7.C14 second reservation fails in temp/offline authority;
12. P7.C14 parent never invokes P7.C13 `--p7c13-real-run`;
13. exact future child module import succeeds under deterministic environment;
14. gate-disabled parent starts no Codex/app-server;
15. no source path outside allowed scope changes.

## L. Validation

Run focused P7.C14 tests, accepted P7.C13/P7.C12 offline suites needed for regression, relevant C2-C5 fake/non-real suites, complete non-real pytest, unittest discovery, compileall, `git diff --check`, leakage/security scan and exact scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## M. Evidence

Create:

`docs/evidence/p7c14/P7C14_LAUNCHER_RECOVERY_PREP_EVIDENCE_2026-09-12.md`

Record sanitized safe facts only:

- preparation base HEAD/tree;
- consumed P7.C13 evidence blob;
- pre-repair interpreter/import classification;
- package-marker blobs;
- P7.C14 launcher blob;
- inherited P7.C13 harness blob;
- inherited P7.C12 matcher blob;
- exact future import-root class/hash;
- exact dry-import results;
- gate-disabled parent smoke result;
- P7.C13 ledger untouched/absent status;
- P7.C14 real ledger absent status;
- validation counts;
- zero-real-effect accounting.

Required final lines:

`P7C14_PREP_IMPORT_AUTHORITY=PASS|FAIL`

`P7C14_PREP_PACKAGE_AUTHORITY=PASS|FAIL`

`P7C14_PREP_DISTINCT_GATE_LEDGER=PASS|FAIL`

`P7C14_PREP_GATE_DISABLED_SMOKE=PASS|FAIL`

`P7C14_PREP_INHERITED_HARNESS_BINDING=PASS|FAIL`

`P7C14_PREP_READY=YES|NO`

`P7C14_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## N. Publication

Use branch:

`prep-p7-c14-launcher-recovery-2026-09-12`

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect review is required before any P7.C14 real token or one-shot execution contract exists.
