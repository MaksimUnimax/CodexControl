# P7.C15 hard-delete successor preparation Repair-1 contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / PRODUCTION-INTEGRATION REPAIR / NO REAL EXECUTION**

## Exact base

Repair-1 starts exactly from:

- HEAD `11ea49d1bf6369b27f293ff58a9ba62ad52333a1`;
- tree `faa3c889860832a56ffbd2332760d4b90673b8ef`;
- launcher blob `37b5926ad998fb146bba154546059d9d1439bb38`;
- evidence blob `508000c76ede6373455dec70e910becc5b0b4b6b`.

Binding review:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_ARCHITECT_REVIEW_2026-09-12.md`

## Scope

Repair only the missing future production parent/boot/owned-child/result wiring.

Preserve the already accepted P7.C15 algorithms:

- generation mismatch reproduction;
- generation tracker;
- immutable semantic snapshot;
- generation rebound catalog;
- one semantic model-list acquisition;
- stage journal schema;
- live-budget failure payload selection;
- parent exit projection;
- distinct P7.C15 source gate/ledger/profile/path namespace.

Do not redesign the hard-delete behavior or modify `src/**`.

## Zero-real-effect boundary

All real effects remain zero during Repair-1:

- Codex/app-server starts `0`;
- model/thread/Turn RPCs `0`;
- approval responses `0`;
- interrupt/delete `0`;
- P7.C13/P7.C14 ledger mutations `0`;
- P7.C15 real-ledger creation `0`;
- persistent/orphan/controller mutations `0`;
- Telegram/process signals `0`.

No P7.C15 real token may be created/set.

## 1. Real production parent executor

`P7C15PreparedFutureExecutor.production()` must return a genuinely real-capable future executor, not a synthetic callback.

It must use exactly one distinct replay barrier:

`/root/.codexcontrol/p7c15-one-shot.json`

It must generate one fresh high-entropy run identity and one fresh `p7c15-*` authority set using the accepted path policy.

The computed fresh paths must actually be used; they must not be discarded.

The production parent order is:

source gate -> ledger reserve -> fresh-path validation -> root-only boot creation -> one owned child -> strict result validation -> owned process-group quiescence -> terminal ledger update.

No retry or second child.

## 2. Production boot authority

Do not use `_synthetic_boot()` in production.

Create one production boot builder whose record binds at minimum:

- P7.C15 boot schema;
- source HEAD/tree;
- P7.C15 launcher blob as executable child authority;
- safe run hash;
- `P7C15_PROFILE_ID`;
- `/root/.codex_second` shared persistent home if inherited child helpers need it;
- exact P7.C15 ledger path;
- exact boot path;
- child-result path;
- isolated root/sqlite/logs authority;
- controller DB;
- workdir;
- approval target;
- wire path;
- approval-journal path;
- stage-journal path;
- frozen effect ceiling;
- deterministic import-root authority/class.

Validate all production paths:

- absolute;
- expected `p7c15-*` namespace;
- mutually non-aliasing except explicitly allowed nesting;
- no symlink;
- fresh/absent where required;
- bounded strings;
- actual ledger path equals `/root/.codexcontrol/p7c15-one-shot.json`.

Root-only boot remains regular root-owned `0600`, nlink 1, exclusive create, bounded size, no duplicate keys.

## 3. Owned child subprocess / watchdog

Use one owned child subprocess and dedicated process group.

Reusing the accepted P7.C13 `OwnedParentChildWatchdog` is preferred if its result validator is bound to the exact P7.C15 boot/result authority.

Requirements:

- one child only;
- finite hard deadline;
- bounded TERM/KILL only for the exact owned group on timeout;
- no unrelated process signaling;
- active/zombie/scan-error proof before parent PASS;
- no retry.

The exact child command must use deterministic import authority and pass the **boot-authority path**, never the child-result path:

`/usr/bin/env PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c15_final_hard_delete_successor --p7c15-future-child --boot-authority <actual-boot-path>`

## 4. Real child CLI dispatcher

`--p7c15-future-child` must be an actual dispatcher.

It must:

1. require one boot-authority path;
2. read/validate exact root-only P7.C15 boot authority;
3. enter the production-capable P7.C15 child main exactly once;
4. return `0` only for a valid PASS child result;
5. return nonzero for FAIL/UNKNOWN/CONFIRMED_PENDING/TIMEOUT or malformed authority.

It must not unconditionally return `1` and must not invoke P7.C14/P7.C13 real parent entrypoints.

## 5. Production generation-transition correction

The real child must actually use the accepted correction:

- wrap the accepted `CodexRuntimeManager` in `GenerationTrackingRuntimeManager`;
- obtain exactly one authenticated `CodexModelCatalogAdapter` snapshot in generation 1;
- materialize `ImmutableSemanticCatalogSnapshot`;
- use `GenerationReboundCatalogView` for lifecycle adapters that operate after runtime-generation transition;
- after generation-1 shutdown and confirmed generation-2 acquire/resume, Turn 2 must see rebound generation 2 while preserving semantic snapshot identity;
- no second real `model/list` call.

Do not weaken `CodexTurnLifecycleAdapter` generation checks.

The production stage journal must prove one model-list and the generation transition.

## 6. Production hard-delete flow

The P7.C15 production child must execute the accepted P7.C13 hard-delete behavior with the P7.C15 generation correction and P7.C15 run authorities.

It must retain the already accepted boundaries:

- fresh thread/start;
- Turn 1 marker proof;
- generation shutdown/restart;
- exact thread/resume;
- Turn 2 memory proof;
- Turn 3 C11 explicit escalation + root-only wire + accepted C12 matcher + one protocol response/ALLOW;
- Turn 3 target proof/cleanup;
- distinct Turn 4 active proof + unexpected-request observer + one interrupt + post-join classification;
- runtime shutdown before physical pre-delete scan;
- schema-v4 controller IDLE binding;
- exactly one canonical `DialogueDeleteService.delete()`;
- independent official delete observation;
- tombstone/live-binding/isolation/residual proof;
- child runtime quiescence.

Reuse frozen P7.C13 helpers by composition where safe; do not call P7.C13/P7.C14 real parent modes.

## 7. Production stage journal

Create the P7.C15 stage journal before business effects.

Use it in the real child, not only tests.

Persist finite safe milestones around each effect boundary. At minimum:

- runtime generation acquisitions;
- model/list dispatched/confirmed;
- thread/start dispatched/confirmed;
- Turn start dispatched/confirmed and terminal classes for Turns 1-4;
- runtime shutdown/reacquire;
- thread/resume dispatched/confirmed;
- approval request/response class;
- interrupt dispatch/result;
- controller binding;
- delete dispatch/result;
- terminal exception class/category;
- last-confirmed-stage;
- safe effect-count snapshot class/hash.

No raw thread/Turn/prompt/response/wire/token material.

The child result must carry `stage_journal_sha256` and safe terminal category/stage.

## 8. Accurate failure-path effect accounting

The real child main must keep a reference to the actual constructed production child/orchestrator.

On every exception:

`actual_budget = child.budget if child is not None else pre_child_budget`

Serialize exactly that budget.

This must be the actual production exception path, not a synthetic helper only.

Known finite adapter error category must be persisted safely; raw exception text is forbidden.

## 9. Root-only child-result authority

Implement bounded root-only P7.C15 child-result write/read/validation.

Requirements:

- P7.C15 child-result schema;
- root-owned regular `0600`, nlink 1, no symlink;
- exclusive create;
- bounded bytes/keys;
- duplicate keys rejected;
- source HEAD/tree/launcher/run hash must match boot;
- effect counts bounded by frozen ceilings;
- safe finite status only: PASS/FAILED/UNKNOWN/CONFIRMED_PENDING/TIMEOUT;
- terminal error category/stage/journal hash finite and sanitized;
- runtime-child quiescence recorded;
- no raw identities.

Parent PASS must require strict child-result PASS + verdict true + effect/oracle/quiescence gates.

## 10. Parent terminal mapping / CLI exit

After watchdog:

- PASS child + clean group -> ledger `COMPLETED`, parent result PASS;
- failed child/watchdog -> ledger `FAILED`;
- child `UNKNOWN` -> ledger `UNKNOWN`;
- child `CONFIRMED_PENDING` -> ledger `CONFIRMED_PENDING`;
- timeout -> ledger `TIMEOUT`.

The CLI must project:

- disabled/source mismatch -> `2`;
- PASS -> `0`;
- every executed non-PASS state -> `1` (or another explicitly frozen nonzero code, but never zero).

## 11. No synthetic production residue

Add source/AST tests that fail if production path contains any of the following behavior:

- `future=NOT_RUN` synthetic return;
- `del command, fresh_paths` or equivalent discarded production paths;
- `_synthetic_boot()` called from production;
- fixed `p7c15-boot-synthetic`/`ledger.json`/`result.json` production authorities;
- child CLI unconditional `return 1` after only `lstat`;
- `--boot-authority` supplied `child_result_path`;
- no owned subprocess/watchdog;
- production path not referencing generation tracker/rebound view;
- production path not referencing stage journal/live-budget child-result writer.

## 12. Mandatory production-shaped offline integration proof

Build one exact-authorized zero-effect proof that traverses the actual production classes:

P7.C15 source gate -> production P7.C15 executor configured with TEMP authority root -> temp ledger -> production boot builder -> owned-child/watchdog seam -> P7.C15 child dispatcher/main -> fake runtime/client adapters -> corrected generation transition -> bounded root-only child result -> parent validator -> terminal temp ledger.

The positive proof must not inject a mock executor at the source gate and must not bypass the real production boot/result builders.

It may inject fake runtime/client/process factories so no Codex/app-server process starts.

Prove:

- one temp P7.C15 reservation;
- one owned fake child dispatch;
- exact boot path supplied to child;
- fresh P7.C15 production-shaped paths used;
- model/list count exactly 1;
- Turn 2 dispatch count exactly 1 after restart/resume;
- P7.C14/P7.C13 ledger access 0;
- valid PASS child result accepted;
- parent terminal state `COMPLETED`;
- no real effects.

## 13. Mandatory production-shaped forced-failure proof

Use the same actual production child entry and builders with fake adapters.

Force a `TurnLifecycleError` after recorded fake effects.

Prove:

- live budget counts survive in the root-only child result;
- terminal category survives;
- last-confirmed stage survives;
- stage-journal digest validates;
- parent sees non-PASS;
- temp ledger terminal state non-PASS;
- CLI projection nonzero;
- no second child/retry.

## 14. Historical P7.C14 orphan isolation

Do not touch retained P7.C14 thread/session/isolated material.

P7.C15 production target/oracle paths must use fresh P7.C15 run identity and target-specific scanning only.

Offline prove unrelated P7.C14 residual material is ignored as unrelated rather than treated as P7.C15 target material.

## 15. Allowed tracked changes

Allowed only:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`.

Optional one P7.C15-only helper under `tests/real/` if strictly required.

Forbidden:

- `src/**`;
- P7.C14 launcher;
- P7.C13 harness;
- P7.C12 matcher;
- P7.C6-P7.C14 historical evidence/source;
- package markers;
- migrations/deployment/Telegram/P8/P9.

## 16. Validation

Run:

- focused P7.C15 Repair-1;
- targeted P7.C14 mismatch reproduction;
- P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 fake/non-real suites;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact scope check.

Historical consumed-latch failures remain immutable and are reported separately.

Re-run gate-disabled P7.C15 exact module smoke after final source edits and prove real P7.C15 ledger absent.

## 17. Evidence

Update existing P7.C15 preparation evidence.

Record:

`P7C15_REPAIR1_BASE_HEAD=11ea49d1bf6369b27f293ff58a9ba62ad52333a1`

`P7C15_REPAIR1_BASE_TREE=faa3c889860832a56ffbd2332760d4b90673b8ef`

`PRIOR_P7C15_LAUNCHER_BLOB=37b5926ad998fb146bba154546059d9d1439bb38`

`PRIOR_P7C15_EVIDENCE_BLOB=508000c76ede6373455dec70e910becc5b0b4b6b`

and final launcher/evidence/helper blobs.

Required final lines:

`P7C15_REPAIR1_PRODUCTION_PARENT_CHILD_PATH=PASS|FAIL`

`P7C15_REPAIR1_REAL_CHILD_DISPATCHER_PREPARED=PASS|FAIL`

`P7C15_REPAIR1_FRESH_BOOT_RESULT_AUTHORITY=PASS|FAIL`

`P7C15_REPAIR1_PRODUCTION_GENERATION_REBOUND=PASS|FAIL`

`P7C15_REPAIR1_PRODUCTION_FAILURE_ACCOUNTING=PASS|FAIL`

`P7C15_REPAIR1_PRODUCTION_STAGE_JOURNAL=PASS|FAIL`

`P7C15_REPAIR1_PARENT_TERMINAL_PROJECTION=PASS|FAIL`

`P7C15_REPAIR1_EXACT_AUTHORIZED_PRODUCTION_SHAPED_HANDOFF=PASS|FAIL`

`P7C15_PREP_READY=YES|NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c15-hard-delete-successor-repair1-2026-09-12`

from exact candidate HEAD `11ea49d1bf6369b27f293ff58a9ba62ad52333a1`.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect acceptance is required before any P7.C15 real token or one-shot execution contract exists.
