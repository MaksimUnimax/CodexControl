# P7.C15 hard-delete successor preparation contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / DISTINCT SUCCESSOR / NO REAL EXECUTION**

## Purpose

P7.C15 is a distinct successor to permanently consumed P7.C14. It exists to correct the uniquely established generation-transition lifecycle defect and the two accepted failure-evidence defects before any new real acceptance may be considered.

P7.C14 MUST NOT be rerun. P7.C13 MUST NOT be rerun.

No real Codex/app-server/RPC/approval/interrupt/delete effect is authorized by this preparation contract.

## Binding authority

Accepted retained forensic:

- forensic commit `98e168c82f7fd9d8f50c491017323e97d3ed396f`;
- forensic base `2676e4c9eeb3f343112d41c3307948599fc81837`;
- P7.C14 execution HEAD `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- execution tree `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- P7.C14 launcher blob `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- package markers `080243830be797f87d23b459dbfd12c142a9d49a` and `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

Binding architect acceptance:

`docs/evidence/p7c14/P7C14_RETAINED_FORENSIC_ARCHITECT_ACCEPTANCE_2026-09-12.md`

## Exact preparation base

The P7.C15 preparation branch MUST start exactly from the retained forensic head:

`98e168c82f7fd9d8f50c491017323e97d3ed396f`

This preserves the consumed P7.C14 real evidence and retained forensic authority.

## Accepted root cause to reproduce

The preparation must first reproduce the P7.C14 defect offline:

1. one authenticated catalog snapshot is bound to runtime generation 1;
2. runtime generation 1 is shut down;
3. runtime generation 2 is acquired;
4. thread/resume is confirmed;
5. a `CodexTurnLifecycleAdapter` is given the stale generation-1 pinned catalog;
6. `start_turn()` raises `TurnLifecycleError(TURN_PRECONDITION_CHANGED)` before `turn/start` RPC dispatch because `runtime.generation != catalog.runtime_generation`.

The reproduction must prove the fake `turn/start` client request count remains zero.

## Generation-transition catalog correction

Do NOT weaken or modify `CodexTurnLifecycleAdapter` generation checks.

Do NOT make a second real `model/list` call.

P7.C15 must preserve the one authenticated model-list semantic snapshot while rebinding only its runtime-generation authority after the confirmed generation transition.

Preferred design:

- a generation-tracking runtime-manager wrapper around the accepted `CodexRuntimeManager`;
- one real `CodexModelCatalogAdapter` acquisition in generation 1;
- a bounded immutable semantic catalog view/proxy containing the exact generation-1 model descriptors, default model, wire model identities and reasoning-effort authority;
- the view exposes `runtime_generation` equal to the currently confirmed runtime generation recorded by the tracking manager;
- profile identity remains exact;
- no model descriptors/default/reasoning/wire values may change during generation rebinding;
- the second-generation `turn/start` remains guarded by the unmodified adapter equality check and must fail closed if generation authority drifts again.

Equivalent design is allowed only if it proves all the same invariants and no second model-list dispatch.

## Required generation-transition tests

At minimum prove offline:

1. stale static generation-1 catalog + generation-2 runtime => `TURN_PRECONDITION_CHANGED` and zero `turn/start` RPC;
2. generation-rebound semantic view + generation-2 runtime => adapter reaches exactly one fake `turn/start` RPC;
3. semantic models tuple is identical to the authenticated generation-1 snapshot;
4. default model identity unchanged;
5. wire model identity unchanged;
6. supported/default reasoning efforts unchanged;
7. only runtime-generation authority changes;
8. second underlying model-list acquisition is impossible/fail-closed;
9. generation regression/profile mismatch is fail-closed;
10. restart/resume + Turn-2 synthetic path succeeds with total model-list dispatch count exactly one.

## P7.C15 successor module

Create:

`tests/real/test_p7_c15_final_hard_delete_successor.py`

It must be a distinct parent/child successor and may import accepted P7.C13/P7.C14 helpers as frozen library authority.

Distinct authority:

- gate env `P7C15_FUTURE_REAL_GATE`;
- P7.C15-prefixed expected-source env names;
- parent CLI `--p7c15-real-run`;
- child CLI `--p7c15-future-child`;
- replay ledger `/root/.codexcontrol/p7c15-one-shot.json`;
- distinct fresh run/path prefixes `p7c15-*` for isolated/controller/work/approval/boot/result/wire/journal/stage authorities;
- no call to P7.C14 or P7.C13 real parent entrypoints.

## P7.C15 parent source gate

Before ledger reservation bind at minimum:

- exact P7.C15 HEAD;
- tree;
- P7.C15 launcher blob;
- inherited P7.C14 launcher blob if reused by parent code;
- inherited P7.C13 harness blob;
- P7.C12 matcher blob;
- package-marker blobs;
- deterministic import roots `/root/CodexControl/src:/root/CodexControl`;
- tracked worktree clean;
- tracked index clean.

Any mismatch blocks before ledger/child/Codex effects.

## Distinct parent/boot authority

P7.C15 replay authority is only:

`/root/.codexcontrol/p7c15-one-shot.json`

It MUST NOT consult P7.C14/P7.C13 ledgers as replay state.

The inherited boot/result schema may be reused, but production P7.C15 parent must use P7.C15-prefixed fresh paths and a P7.C15 profile identifier. Boot `harness_blob` must bind the P7.C15 successor module blob because that is the executable child authority. The source gate separately binds inherited P7.C13/P7.C12/P7.C14 library blobs.

## Accurate failure-path effect accounting

The P7.C14 exception-path zero-budget defect MUST be corrected.

P7.C15 child execution must retain a reference to the live production child/orchestrator budget and serialize that actual budget on every terminal path, including exceptions.

Required tests:

- mutate a fake live child budget before raising;
- exception child-result persists those exact counts;
- outer/default zero budget is not serialized when a live child exists;
- failure before child construction uses only the outer pre-child budget and is classified separately;
- no effect count may exceed the frozen ceilings.

## Root-only stage journal

Before real business effects, P7.C15 child must create one bounded root-only stage journal derived from the current run hash, e.g. under `/root/.codexcontrol/p7c15-stage-*`.

Properties:

- regular root-owned mode `0600`, nlink 1, no symlink;
- bounded file size/record count;
- duplicate/invalid records rejected;
- no raw thread IDs, Turn IDs, prompt/response, wire plaintext or token;
- safe stage enum and state only;
- safe effect-count snapshot/hash classes permitted;
- terminal failure record contains exception class and safe category where available.

The production protocol/runtime graph must record enough safe milestones to recover, without guessing, at least:

- runtime generation acquire confirmations;
- model/list dispatch/confirmation;
- thread/start dispatch/confirmation;
- each turn/start dispatch/confirmation;
- turn terminal classes;
- runtime shutdown/reacquire;
- thread/resume dispatch/confirmation;
- approval request/response class;
- interrupt dispatch/result;
- controller binding;
- delete dispatch/result;
- terminal exception category and last-confirmed stage.

A protocol-client/runtime wrapper is preferred to invasive changes in `src/**` or monkeypatching accepted historical modules.

## TurnLifecycleError category persistence

On exception, if the error is `TurnLifecycleError`, persist its public safe category value in the child result/journal, for example `TURN_PRECONDITION_CHANGED`.

Other known adapter exception categories may be persisted similarly using finite safe enums.

Do not persist raw exception text.

## Parent CLI exit projection

P7.C15 module exit codes must represent the final parent result:

- gate disabled/source mismatch: finite disabled code `2`;
- successful parent/watchdog/child/ledger PASS: `0`;
- any executed failed watchdog/child/ledger state: nonzero failure code `1`;
- UNKNOWN/CONFIRMED_PENDING/TIMEOUT: nonzero.

A returned failed `WatchdogResult` MUST NOT fall through to exit `0`.

Offline tests must exercise these projections.

## Exact authorized synthetic parent-child proof

Preparation must include a full zero-effect authorized synthetic handoff:

`P7.C15 source gate -> P7.C15 executor -> temp P7.C15 ledger -> temp boot -> P7.C15 child entry -> corrected generation transition -> synthetic child result -> parent validation`.

No mock executor at the source gate for the positive proof.

Use temporary authorities/fake clients only. Prove:

- exactly one temp P7.C15 ledger reservation;
- zero P7.C14/P7.C13 ledger access/mutation;
- one synthetic model-list only;
- generation-2 Turn 2 reaches fake `turn/start` after confirmed resume;
- actual live failure budget is retained in a forced failure case;
- stage journal records the forced category/stage;
- no real child/Codex/RPC effect.

## P7.C14 orphan material

The retained P7.C14 persistent session and isolated material are historical evidence.

Do NOT clean or modify them in P7.C15 preparation.

P7.C15 scanners/acceptance must remain target-specific to the fresh P7.C15 thread/run and must not treat unrelated P7.C14 historical residue as target material.

## Zero-real-effect boundary

During all P7.C15 preparation:

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

`P7C14_LEDGER_MUTATIONS=0`

`P7C15_REAL_LEDGER_CREATIONS=0`

`PERSISTENT_HOME_MUTATIONS=0`

`P7C14_ORPHAN_MUTATIONS=0`

`TELEGRAM_CALLS=0`

`PROCESS_SIGNALS=0`

No real P7.C15 token may be invented or set.

## Allowed tracked changes

Allowed:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`.

Optional one P7.C15-only helper under `tests/real/` only if strictly necessary.

Package markers remain unchanged.

Forbidden:

- `src/**`;
- P7.C13 harness;
- P7.C14 launcher;
- P7.C12 matcher;
- P7.C6-P7.C14 historical evidence/source;
- migrations/deployment/Telegram/P8/P9.

## Required validation

Run:

- focused P7.C15 suite;
- targeted P7.C14 failure reproduction suite;
- P7.C14/P7.C13 offline-only regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 fake/non-real suites;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## Gate-disabled import/parent smoke

Under exact deterministic import authority:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl`

run import-only smoke for P7.C15 and exact parent module with all P7.C15 authorization vars unset.

Expected:

- import succeeds;
- disabled parent exits `2`;
- P7.C15 real ledger remains absent;
- no P7.C14/P7.C13 authority touched;
- no Codex/app-server starts.

## Preparation evidence

Create:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`

Record safe facts only:

- preparation base HEAD/tree;
- accepted P7.C14 forensic commit/blob;
- P7.C15 launcher blob;
- inherited library blobs;
- root-cause reproduction proof;
- generation-rebound catalog invariants;
- one-model-list proof;
- exact authorized synthetic handoff;
- actual failure-budget persistence proof;
- stage-journal/category proof;
- parent-exit projection matrix;
- distinct gate/ledger/path proof;
- P7.C14 orphan untouched proof;
- validation counts;
- zero-real-effect accounting.

Required final lines:

`P7C15_PREP_P7C14_ROOT_CAUSE_REPRODUCTION=PASS|FAIL`

`P7C15_PREP_GENERATION_REBOUND_CATALOG=PASS|FAIL`

`P7C15_PREP_SINGLE_MODEL_LIST=PASS|FAIL`

`P7C15_PREP_FAILURE_ACCOUNTING=PASS|FAIL`

`P7C15_PREP_STAGE_CATEGORY_JOURNAL=PASS|FAIL`

`P7C15_PREP_PARENT_EXIT_PROJECTION=PASS|FAIL`

`P7C15_PREP_DISTINCT_GATE_LEDGER=PASS|FAIL`

`P7C15_PREP_EXACT_AUTHORIZED_SYNTHETIC_HANDOFF=PASS|FAIL`

`P7C15_PREP_READY=YES|NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only on:

`prep-p7-c15-hard-delete-successor-2026-09-12`

created from exact forensic commit `98e168c82f7fd9d8f50c491017323e97d3ed396f`.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect review is required before any P7.C15 real token or one-shot execution contract exists.
