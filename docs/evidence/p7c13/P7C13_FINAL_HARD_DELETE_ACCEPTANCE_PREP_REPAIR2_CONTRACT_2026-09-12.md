# P7.C13 preparation Repair-2 contract — complete future child integration — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / FINAL PREPARATION REPAIR / NO REAL AUTHORIZATION**

## Base

Repair-2 starts from exact Repair-1 candidate:

`e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`

Repair-1 harness blob:

`82a7f3c1e31456205fb316eb4e692973dc3d0361`

Preserve the accepted Repair-1 pieces listed in the architect review. Do not redesign the matcher, durable-ledger model, Turn authority model, residual oracle or production delete semantics merely to satisfy this repair.

## Absolute boundary

Repair-2 remains preparation-only. During implementation and validation:

- real Codex process starts = 0;
- app-server starts = 0;
- authenticated business RPCs = 0;
- thread/turn/approval/interrupt/delete real effects = 0;
- real P7.C13 ledger = absent;
- real persistent home / isolated root / controller / approval-target mutation = 0;
- historical authority mutation = 0;
- P8/P9 = not started.

All execution-path tests must use injected fake/synthetic seams or harmless test-owned subprocesses. No architect authorization token exists in this repair.

## Required correction 1 — exact CLI/child dispatcher

The exact harness must contain the future child mode now.

When invoked with the dedicated future-child argument, the module must dispatch to a bounded `_future_child_main(...)` (or equivalent) instead of `unittest.main()`.

Ordinary test invocation/discovery must continue to use unittest and must never enter child mode.

The future child mode must require a root-only boot-authority file path or equivalent root-only descriptor supplied by the gated parent. It must not receive raw recovery identities on argv or in Git-tracked/static constants.

The child mode must fail closed on missing/malformed/unsafe boot authority before any installed/runtime/business effect.

## Required correction 2 — root-only boot authority

Prepare a bounded schema for the future root-only child boot record. It must include enough exact authority to assemble the already-frozen run without another code change, including at minimum:

- schema/version;
- source HEAD;
- source TREE;
- accepted harness blob;
- run identifier/hash plus raw current-run recovery identity only in root-only storage when necessary;
- profile identity and exact shared persistent-home authority;
- fresh isolated-root path;
- controller DB path;
- workdir;
- approval target;
- one-shot ledger path;
- child-result path;
- parent/source contract hash/identity;
- future effect-budget ceiling authority.

Requirements:

- regular root-owned mode-0600 nlink-one file;
- no symlink/follow;
- bounded bytes;
- duplicate-key rejection;
- stable dev/inode while read;
- exact path/boundary validation;
- source HEAD/TREE/harness values must agree with the architect gate/ledger before effects.

Repair tests use only temp root-equivalent synthetic files.

## Required correction 3 — production child assembly exists in exact source

`_future_child_main()` (or equivalent) must assemble the actual future child path now, using dependency-injectable construction so it can be proved offline.

The production branch must be capable of assembling:

1. boot authority reader/validator;
2. installed runtime authority;
3. `CodexProfile` with `CODEX_HOME=/root/.codex_second` and fresh isolated root;
4. `IsolationPathAuthority` / `IsolatedStateRoot`;
5. accepted `CodexRuntimeManager` path;
6. model catalog selection once;
7. fresh thread lifecycle start;
8. Turn 1 marker establishment;
9. owned runtime shutdown/reap;
10. new generation and exact `thread/resume`;
11. Turn 2 marker memory proof;
12. Turn 3 authoritative approval capture + accepted P7.C12 matcher + one approval response;
13. Turn 3 target postcondition/cleanup;
14. Turn 4 distinct long-running turn + one exact interrupt;
15. full owned runtime shutdown/reap;
16. pre-delete bounded physical observation;
17. fresh schema-v4 controller DB + exact IDLE binding;
18. production `DialogueDeleteService` using real `CodexThreadLifecycleAdapter`, accepted `DeleteStorageCleanupCoordinator`, runtime manager and isolation authority;
19. one and only one `DialogueDeleteService.delete()` call;
20. post-delete acceptance oracle;
21. bounded child-result write.

The child implementation may factor helpers inside the allowed P7.C13 test module/helper, but no `src/**` change is authorized.

## Required correction 4 — no placeholder production stop

The exact accepted harness must contain no unconditional production placeholder such as:

`raise ... requires architect root-only boot configuration`

on the successfully gated, correctly bootstrapped future-real path.

Failures are permitted only when a real safety/authority gate actually fails.

An offline synthetic exact boot + fully fake dependencies must be able to traverse the complete child orchestrator and produce a bounded PASS child result without Codex.

## Required correction 5 — budget reservation before real effect callbacks

The future effect budget is a pre-dispatch authority.

For every effect-capable callback, reserve/check its slot before callback invocation.

Specifically:

- approval response slot before approval-response callback;
- ALLOW slot before ALLOW callback/decision dispatch;
- DENY, if implemented for safe unexpected first approval, remains within the single approval-response total and success requires DENY=0;
- interrupt slot before `turn/interrupt` callback;
- thread delete external effect must be accounted before the one production `DialogueDeleteService.delete()` path can reach lifecycle delete;
- turn/start, thread/start/resume/model-list likewise pre-reserved;
- forbidden read/list have zero dispatch paths.

Add tests with callbacks that increment counters and prove over-budget rejection occurs before callback entry.

Do not create an extra raw `thread/delete` dispatcher separate from `DialogueDeleteService` merely to satisfy accounting. The accounting seam must wrap/guard the canonical application delete invocation.

## Required correction 6 — parent produces root-only boot record before child spawn

The gated parent executor must, after durable one-shot reservation and before child spawn:

- create/materialize the exact run-owned root-only boot authority safely;
- bind it to source HEAD/TREE/harness/ledger/run boundaries;
- pass only a safe path/descriptor reference to the one child;
- preserve it on failure/UNKNOWN/pending for recovery;
- sanitize/remove only under explicitly safe complete-PASS semantics if the frozen evidence/recovery policy allows;
- never place raw boot contents in Git evidence or argv.

The parent must still spawn exactly one child in one owned session/process group and never retry.

## Required correction 7 — bounded child result is actually written by child

On every terminal child path where safe reporting is possible, write one root-only bounded child-result record consumed by the parent watchdog.

At minimum safe fields may include:

- schema;
- source/hash authority;
- finite status/verdict;
- effect counts;
- finite Turn 1-4 outcomes;
- matcher/approval/interrupt classes;
- official/application delete classes;
- residual counts/classes;
- scan error counts;
- owned process/runtime counts;
- final oracle result.

Do not expose raw thread/Turn/target/prompt/response/wire/credential data.

Malformed/missing child result prevents PASS.

## Required correction 8 — exact future gate invokes the real parent path

Preserve exact contract/environment/current HEAD/TREE/harness matching.

Offline prove:

- exact gate invokes prepared production parent factory/executor exactly once;
- all mismatches invoke zero;
- successful synthetic parent+child complete path can return a valid parent classification;
- second invocation is blocked by durable consumed authority.

## Required correction 9 — preserve independent owned Turn authorities

The actual child assembly must use distinct real Turn IDs and independent run authority, not only the offline `OfflineFutureFlow` model.

Before future Turn-3 ALLOW, bind the captured P7.C12 inputs to the actual owned current run:

- exact fresh thread;
- exact Turn-3 ID;
- exact cwd;
- exact local request sequence;
- exact independently selected target;
- exact command SHA;
- exactly one authoritative wire;
- target absent immediately before response.

Before future Turn-4 interrupt, bind to actual distinct Turn-4 ID and prove active/nonterminal state.

## Required correction 10 — actual persistence observation path

The production-capable Turn-1/Turn-2 orchestration must evaluate actual terminal/output observations against the generated markers. It must not use only synthetic booleans/default strings in the real path.

Tests must inject observed fake terminal payloads through the same parsing/evaluation seam used by production child assembly.

## Required correction 11 — actual pre/post storage oracle path

The production-capable child must actually invoke the accepted bounded oracle with the current-run raw thread ID and marker bytes held only in memory/root-only state.

Persistent exact-thread residual classes include content, session filename and directory component. Marker residual and isolated residual remain independent failures.

The explicit unrelated-target-specific-removal gate must be part of the final production child oracle input.

## Required correction 12 — DELETE_UNKNOWN / confirmed-pending remains canonical

Preserve accepted application behavior:

- exactly one canonical `DialogueDeleteService.delete()` attempt;
- DELETE_UNKNOWN terminal, no retry/read/list/finalizer/tombstone/manual persistent cleanup;
- confirmed-pending local failure, no external delete retry;
- only complete confirmed+clean proof may produce DELETED/PASS.

No direct raw delete fallback is authorized.

## Required offline additions

At minimum add tests proving:

1. module child-mode dispatch reaches injected `_future_child_main` equivalent, not unittest;
2. ordinary unittest path never invokes child mode;
3. missing boot authority fails before installed/runtime/business effects;
4. malformed boot authority fails before effects;
5. symlink/wrong-mode/identity-drift boot file fails closed;
6. source HEAD mismatch fails before effects;
7. source TREE mismatch fails before effects;
8. harness blob mismatch fails before effects;
9. ledger/boot run-binding mismatch fails before effects;
10. synthetic exact boot assembles complete child orchestrator;
11. synthetic complete child PASS writes one valid bounded child result;
12. child failure writes bounded non-PASS result where safe;
13. missing result blocks parent PASS;
14. malformed result blocks parent PASS;
15. approval budget reserves before approval callback;
16. ALLOW budget reserves before ALLOW callback;
17. interrupt budget reserves before interrupt callback;
18. over-budget approval callback count stays zero;
19. over-budget interrupt callback count stays zero;
20. delete budget/application guard prevents second canonical delete call;
21. no raw thread-delete fallback exists/reachable;
22. actual fake Turn-1 observed marker seam passes/fails correctly;
23. actual fake Turn-2 observed memory seam passes/fails correctly;
24. actual fake Turn-3 owned binding mismatch blocks response dispatch;
25. actual fake Turn-4 inactive/wrong binding blocks interrupt dispatch;
26. actual fake pre-delete oracle must be conclusive before controller delete path;
27. actual fake post-delete marker/thread/file/directory residual blocks PASS;
28. unrelated-removal flag blocks PASS;
29. synthetic exact parent creates ledger + boot before child factory invocation;
30. synthetic second parent invocation/consumed ledger spawns zero second child.

Preserve existing Repair-1 tests unless a test must be corrected because it asserted an overclaim.

## Allowed files

Repair-2 may change only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- existing P7.C13 preparation evidence;
- optionally one new P7.C13-only helper under `tests/real/` if strictly needed.

No production `src/**`, P7.C12 matcher, historical P7.C6-P7.C12, schema/migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP executor changes.

## Required evidence correction

Update the P7.C13 preparation evidence truthfully with:

- Repair-2 base `e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`;
- prior harness blob `82a7f3c1e31456205fb316eb4e692973dc3d0361`;
- new harness blob;
- root-only boot-authority prep result;
- exact child CLI dispatch prep result;
- complete child orchestration prep result;
- pre-dispatch approval/ALLOW/interrupt/delete budget proof;
- parent ledger -> boot -> child ordering proof;
- bounded child-result write/read proof;
- actual fake Turn 1/2/3/4 production-seam proof;
- actual fake pre/post physical oracle proof;
- canonical delete-only proof;
- focused/regression counts;
- leakage and zero-effect accounting.

Required final lines:

`P7C13_REPAIR2_CHILD_DISPATCH_PREPARED=YES|NO`

`P7C13_REPAIR2_BOOT_AUTHORITY_PREPARED=YES|NO`

`P7C13_REPAIR2_COMPLETE_CHILD_ORCHESTRATOR=PASS|FAIL`

`P7C13_REPAIR2_PRE_DISPATCH_BUDGET_GATES=PASS|FAIL`

`P7C13_REPAIR2_CHILD_RESULT_AUTHORITY=PASS|FAIL`

`P7C13_REPAIR2_CANONICAL_DELETE_ONLY=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Validation

Run focused P7.C13 repaired tests, accepted P7.C12 matcher tests, relevant C2/C3/C4/C5 non-real regression, complete non-real regression with all real gates unset, compileall, `git diff --check`, leakage/security scan.

Historical consumed real probes remain untouched/unexecuted. Historical latch-absence static checks may remain separately deselected/reported.

## Publication

Use a new Repair-2 branch from exact candidate `e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`.

No rebase. No force.

Remote readback must prove exact lineage, allowed-file scope, accepted P7.C12 matcher unchanged, no `src/**`, no historical mutation, final harness/evidence blobs, and architect main unchanged by executor.

## Acceptance consequence

Only after independent architect acceptance of Repair-2 may a separate P7.C13 one-shot real execution contract be frozen.

That later execution contract must not require any further code implementation. It may only name exact accepted source HEAD/TREE/harness blob, authorization token, direct command/environment and one-shot execution/evidence procedure.

P8/P9 remain blocked until the subsequent real hard-delete acceptance itself is independently accepted.