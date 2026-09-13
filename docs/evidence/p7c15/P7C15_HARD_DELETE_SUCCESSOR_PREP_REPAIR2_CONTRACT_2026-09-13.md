# P7.C15 hard-delete successor preparation Repair-2 contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / REAL HARD-DELETE CONTINUATION INTEGRATION / NO REAL EXECUTION**

## Exact base

Repair-2 starts exactly from:

- commit `3dc12289fc34b4beac67e7139d740852c5caa2dc`;
- tree `09446141fcb30875f0b8d081bd68b66ac6e73899`;
- P7.C15 launcher blob `c129ac0820104b9860e50938a6529b3522773dbe`;
- P7.C15 evidence blob `0b9c0780fdf541e3642a044de7eb7c6099541b1f`.

Binding review:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_REPAIR1_ARCHITECT_REVIEW_2026-09-13.md`

Binding prior contracts/authority:

- P7.C15 initial preparation contract;
- P7.C14 retained forensic architect acceptance;
- accepted P7.C13 hard-delete harness and P7.C12 strict matcher.

## Scope

Repair-2 is only the missing post-Turn-2 production continuation.

Preserve the accepted Repair-1 infrastructure:

- source gate;
- P7.C15 ledger/fresh paths;
- root-only boot/result;
- owned watchdog/process group;
- real child dispatcher;
- generation tracking/rebound and one-model-list policy;
- stage journal format;
- live-budget exception accounting;
- parent terminal/exit projection.

Do not redesign those accepted components unless required by a direct continuation integration defect.

## Absolute zero-real-effect boundary

During Repair-2:

- real Codex/app-server starts: `0`;
- real model/thread/Turn RPCs: `0`;
- real approval responses: `0`;
- real ALLOW/DENY: `0`;
- real interrupt/delete: `0`;
- P7.C15 production ledger creations: `0`;
- P7.C14/P7.C13 ledger mutations: `0`;
- persistent-home mutations: `0`;
- P7.C14 orphan mutations/cleanup: `0`;
- Telegram calls: `0`;
- process signals against real Codex/unrelated processes: `0`.

Do not create or set a future P7.C15 real token.

## Remove the synthetic continuation

Production `P7C15ProductionChildOrchestrator.run_async()` MUST NOT contain a stage-only loop or equivalent that fabricates post-Turn-2 progress.

Forbidden production behavior includes any equivalent of:

- incrementing `turn/start`, approval, interrupt or delete budgets without invoking the corresponding accepted effect seam;
- writing `CONTROLLER_BINDING`, `THREAD_DELETE_*`, or `APPLICATION_DELETE_RESULT` only as journal labels;
- returning PASS with `delete=OBSERVED` without a real/fake-injected `DialogueDeleteService.delete()` result and independent official delete observation;
- comments or branches that say real adapters will be supplied later while production currently returns PASS.

Static tests must fail if this pattern reappears.

## Actual Turn-3 continuation

After corrected Turn-2 terminal, production P7.C15 must use the actual generation-2 runtime/client and exact current thread binding.

Turn 3 must:

1. derive the exact fresh P7.C15 approval target from boot;
2. prove target absent;
3. create root-only P7.C15 wire and approval-journal authorities at boot-bound paths;
4. build the C11 explicit escalation prompt using the exact target;
5. reserve/record one `turn/start` before dispatch;
6. call the real `CodexTurnLifecycleAdapter.start_turn()` for Turn 3;
7. bind the actual returned Turn-3 binding into the approval operator;
8. use `CodexApprovalBridge` as the sole protocol response path;
9. correlate actual request ordinal/local sequence/kind/thread/Turn/cwd/command through the root-only wire authority;
10. invoke the accepted P7.C12 strict matcher against the correlated immutable command authority;
11. send exactly one protocol response;
12. PASS path requires exactly one ALLOW, zero DENY, zero RESPONSE_UNKNOWN and one approval request;
13. wait for definitive Turn-3 completion;
14. prove exact target exists as a root-owned regular file, nlink 1, private mode, no symlink;
15. cleanup only that exact target before continuing.

The P7.C15 implementation may reuse accepted P7.C13 classes/helpers by composition, but P7.C15 wire/journal paths and stage records must remain P7.C15-prefixed/current-run bound.

## Turn-4 continuation

Use accepted Turn-4 semantics from P7.C13:

- stimulus exactly `sleep 120`;
- distinct actual Turn-4 binding;
- no approval response expected/allowed;
- one owned terminal waiter;
- one owned unexpected-server-request observer;
- active/nonterminal proof before interrupt;
- request+terminal same scheduling slice => fail closed;
- observer remains active through interrupt/terminal convergence;
- reserve interrupt budget before `interrupt_turn()`;
- exactly one interrupt;
- definitive interrupted/failed terminal required;
- any unexpected server request => non-PASS and no second response;
- both tasks joined/terminalized before continuation.

Stage journal must record actual Turn-4 observation/interrupt facts, not predeclare them.

## Pre-delete runtime shutdown and oracle

After accepted Turn-4 convergence:

- shutdown current P7.C15 runtime generation using the accepted bounded shutdown path;
- require child runtime quiescence before storage proof;
- construct target-specific `BoundedTargetOracle` using the exact current P7.C15 thread and only current-run markers/material;
- pre-delete observation must be conclusive and contain observed target material;
- P7.C14 historical orphan/session material must remain unrelated and must not cause false target matches.

No thread/read/list inference is allowed.

## Schema-v4 controller binding

Use a fresh P7.C15 controller DB from boot.

Actually execute the accepted application storage path:

- `SqliteStorage.open()`;
- schema version observation = v4;
- create one P7.C15 dialogue intent bound to the exact profile;
- confirm exact actual thread binding;
- durable live dialogue must be exact `IDLE` binding before delete.

Stage journal `CONTROLLER_BINDING` may be marked confirmed only after durable re-read proves it.

## Canonical delete chain

Assemble the accepted production delete chain using actual current P7.C15 storage/runtime/catalog/thread lifecycle authority.

Exactly one destructive application call is authorized in a future real run:

`DialogueDeleteService.delete(...)`

No raw/manual `thread/delete` fallback.

Before invoking the service in future production:

- reserve P7.C15 `thread/delete` effect count exactly once;
- append `THREAD_DELETE_DISPATCH` immediately before the canonical service call.

Use an independent `OfficialDeleteObservation`/accepted equivalent around the actual lifecycle delete so official Codex deletion is observed separately from application status.

## Delete terminal classes

Preserve accepted semantics:

- official `DELETE_CONFIRMED` + application `DELETED` may continue to final proof;
- official `DELETE_UNKNOWN` => terminal `UNKNOWN`; no retry/read/list/manual cleanup/finalization inference;
- confirmed external delete + local storage pending => `CONFIRMED_PENDING`; no second external delete;
- all other invalid/failure classes => non-PASS.

No second delete or retry is ever allowed.

## Post-delete observed proof

For PASS, production must independently observe actual facts:

- official lifecycle `DELETE_CONFIRMED`;
- application `DELETED`;
- schema remains v4;
- tombstone exists and is bounded to exact dialogue/thread identity hash;
- live dialogue binding absent;
- isolation envelope valid;
- isolated sqlite descendants = 0;
- isolated logs descendants = 0;
- target-specific persistent thread residuals = 0;
- target-specific persistent marker residuals = 0;
- target-specific isolated thread residuals = 0;
- target-specific isolated marker residuals = 0;
- scan/proof errors = 0;
- unrelated target-specific removal = false;
- runtime child quiescent;
- effect ceilings obeyed.

No constant/fabricated post-delete facts.

## Production stage journal coupling

Every accepted stage record must be coupled to the actual operation result.

Examples:

- `TURN3_START_DISPATCH` immediately before actual `start_turn` call;
- `TURN3_START_CONFIRMED` only after actual confirmed binding;
- `APPROVAL_REQUEST` only after the bridge/operator actually receives/correlates the request;
- `APPROVAL_RESPONSE` only after the one bridge response result is known;
- `TURN4_INTERRUPT` only after actual interrupt result;
- `CONTROLLER_BINDING` only after durable IDLE re-read;
- `THREAD_DELETE_DISPATCH` immediately before canonical service delete;
- `THREAD_DELETE_RESULT` from independent official status;
- `APPLICATION_DELETE_RESULT` from actual service result;
- `POST_DELETE_ORACLE` only after observed post-delete acceptance facts.

The journal is evidence of effects; it is never a substitute for them.

## Effect accounting coupling

P7.C15 budget counts must be incremented immediately before the corresponding actual future effect dispatch, not in a later synthetic summary loop.

At minimum bind actual counts for:

- new thread;
- model/list;
- thread/start;
- thread/resume;
- four turn/start operations;
- approval response;
- ALLOW;
- turn/interrupt;
- thread/delete.

Forbidden effects remain zero.

## Production-shaped positive offline continuation test

Mandatory: traverse the actual production parent/boot/watchdog/child/orchestrator through the entire hard-delete continuation using fake adapters/clients/storage/oracle boundaries.

Injection is allowed only at external-effect boundaries, not by replacing the P7.C15 executor/orchestrator with a mock.

The fake environment must exercise actual P7.C15 production code and prove:

- one fake model/list total;
- one fake thread/start;
- one fake thread/resume;
- four fake turn/start dispatches;
- Turn 2 uses generation rebound;
- one fake Turn-3 approval request;
- one P7.C12 exact matcher PASS;
- one protocol response;
- one ALLOW, zero DENY;
- one Turn-4 interrupt;
- one durable controller IDLE binding;
- one canonical `DialogueDeleteService.delete()` invocation;
- one independent official delete observation;
- actual application result `DELETED`;
- actual fake tombstone/live-binding transition;
- observed post-delete oracle accepts only clean state;
- P7.C15 stage journal corresponds to those actual fake effects;
- P7.C15 child result PASS and parent ledger COMPLETED;
- parent exit projection = 0;
- P7.C14/P7.C13 ledger access = 0;
- real Codex effects = 0.

## Negative continuation matrix

At minimum include production-shaped fake cases for:

1. Turn-3 matcher non-exact => no ALLOW/PASS;
2. unexpected second approval => fail closed;
3. Turn-3 target metadata invalid => no controller/delete;
4. Turn-4 unexpected request => no controller/delete;
5. Turn-4 terminal before active proof => no delete;
6. pre-delete oracle inconclusive => no controller/delete;
7. controller durable binding mismatch => no delete;
8. official `DELETE_UNKNOWN` => child `UNKNOWN`, one delete dispatch max, no retry;
9. application `CONFIRMED_PENDING_STORAGE` after official confirmed => child `CONFIRMED_PENDING`, no external retry;
10. post-delete residual/scan error => FAILED;
11. malformed/missing tombstone => FAILED;
12. live binding remains => FAILED;
13. P7.C14 orphan material unrelated to current P7.C15 target does not create a false residual;
14. any missing required fake effect means positive PASS is impossible.

## Child result and parent terminal mapping

Keep accepted P7.C15 root-only child-result authority and Repair-1 parent/watchdog path.

PASS requires actual continuation facts, not only status strings.

Map exact safe terminal classes:

- valid full PASS => child PASS / ledger COMPLETED / parent exit 0;
- normal failure => child FAILED / ledger FAILED / exit nonzero;
- delete unknown => child UNKNOWN / ledger UNKNOWN / exit nonzero;
- confirmed-pending => child CONFIRMED_PENDING / ledger CONFIRMED_PENDING / exit nonzero;
- timeout => TIMEOUT / ledger TIMEOUT / exit nonzero.

## Static anti-simulation gates

Repair-2 must include static/source tests rejecting production equivalents of:

- stage-only post-Turn-2 continuation loops;
- PASS payload containing `delete=OBSERVED` without actual delete chain;
- journal-only controller/delete stages;
- fake fixed official/application delete values;
- raw `thread/delete` fallback;
- second model/list acquisition after generation transition;
- second approval response;
- second delete/retry.

## File scope

Allowed tracked modifications only:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`.

Optional one P7.C15-only test helper under `tests/real/` only if strictly necessary.

Forbidden:

- `src/**`;
- P7.C14 launcher;
- P7.C13 harness;
- P7.C12 matcher;
- historical P7.C6-P7.C14 evidence/source;
- package markers;
- migrations/deployment/Telegram/P8/P9.

## Validation

Run:

- focused P7.C15 Repair-2;
- production-shaped positive hard-delete continuation test;
- all required negative continuation cases;
- P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 fake/non-real regressions;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## Evidence

Update the existing P7.C15 preparation evidence with:

`P7C15_REPAIR2_BASE_HEAD=3dc12289fc34b4beac67e7139d740852c5caa2dc`

`P7C15_REPAIR2_BASE_TREE=09446141fcb30875f0b8d081bd68b66ac6e73899`

`PRIOR_P7C15_LAUNCHER_BLOB=c129ac0820104b9860e50938a6529b3522773dbe`

`PRIOR_P7C15_EVIDENCE_BLOB=0b9c0780fdf541e3642a044de7eb7c6099541b1f`

Record final launcher/evidence/helper blobs and the actual fake effect counts/terminal matrix.

Required final lines:

`P7C15_REPAIR2_REAL_TURN3_APPROVAL_PATH=PASS|FAIL`

`P7C15_REPAIR2_REAL_TURN4_INTERRUPT_PATH=PASS|FAIL`

`P7C15_REPAIR2_REAL_CONTROLLER_BINDING=PASS|FAIL`

`P7C15_REPAIR2_CANONICAL_DELETE_CHAIN=PASS|FAIL`

`P7C15_REPAIR2_OFFICIAL_APPLICATION_DELETE_SEPARATION=PASS|FAIL`

`P7C15_REPAIR2_REAL_POST_DELETE_ORACLE=PASS|FAIL`

`P7C15_REPAIR2_STAGE_EFFECT_COUPLING=PASS|FAIL`

`P7C15_REPAIR2_PRODUCTION_SHAPED_FULL_HANDOFF=PASS|FAIL`

`P7C15_PREP_READY=YES|NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c15-hard-delete-successor-repair2-2026-09-13`

created from exact Repair-1 candidate `3dc12289fc34b4beac67e7139d740852c5caa2dc`.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect acceptance is required before any P7.C15 real token or one-shot execution contract exists.
