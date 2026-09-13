# P7.C15 hard-delete successor preparation Repair-3 contract — 2026-09-13

Status: **FROZEN / ZERO REAL EFFECT / FINAL PRODUCTION-HARDENING PASS / NO REAL EXECUTION**

## Exact base

Repair-3 starts exactly from:

- commit `52e20e42e451955ba0d417a47d89903cadf142f2`;
- tree `03c555267442b8ce6df5255e08152c2cd112908c`;
- P7.C15 launcher blob `7303cebc8fd157ecef590b4ec9575453ee982176`;
- P7.C15 evidence blob `5cde70aea9e3b7d089deece991b677e6ea61b74e`.

Binding review:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_REPAIR2_ARCHITECT_REVIEW_2026-09-13.md`

Repair-3 is not a redesign. Preserve the accepted source gate, one-shot ledger, fresh P7.C15 paths, root-only boot/result, watchdog transport, generation rebound, one-model-list semantic snapshot, real Turn3/Turn4/controller/delete continuation, live-budget failure accounting, stage journal and terminal mapping.

## Zero-real-effect boundary

During Repair-3:

- real Codex/app-server starts: `0`;
- real model/thread/Turn RPCs: `0`;
- real approval responses: `0`;
- real ALLOW/DENY: `0`;
- real interrupt/delete: `0`;
- P7.C15 production ledger creation: `0`;
- P7.C14/P7.C13 ledger mutation: `0`;
- persistent-home mutation: `0`;
- retained P7.C14 orphan mutation/cleanup: `0`;
- Telegram: `0`;
- real process signals: `0`.

Do not create or set a P7.C15 real authorization token.

## 1. Production-safe approval accounting

Remove all production dependence on fake-only fields such as:

- `client.response_calls`;
- `client.pending_approval_count`;
- test queue size as a production authority.

The real `CodexProtocolClient` does not expose those fields.

After one actual `CodexApprovalBridge.handle_next()` the PASS authority must be derived from production-safe facts:

- `approval.status == ALLOWED`;
- operator request count exactly 1;
- operator allow count exactly 1;
- operator deny count 0;
- operator response-unknown false;
- effect budget `approval_responses == 1`;
- effect budget `allow_responses == 1`;
- exactly one correlated root-only wire authority;
- exactly one response record in the root-only recovery journal.

The bridge itself is the response-dispatch authority; do not invent a second response counter on the real client.

### Second-request observer

A second Turn-3 server request must still fail closed without sending a second response.

Implement one owned observer using the production API:

`client.next_server_request()`

Start it immediately after the first response and keep it owned through Turn-3 terminal convergence.

Rules:

- any second server request => non-PASS;
- response count remains 1;
- no ALLOW/DENY/other response to the second request;
- if terminal and second request become available in the same scheduling slice => fail closed;
- observer must be cancelled/joined/terminalized before Turn 4;
- no detached task.

Use a real-client-shaped offline fake that does NOT expose `response_calls` or `pending_approval_count` and prove the positive path still passes.

## 2. Restore exact Turn-1/Turn-2 memory proof

Generate fresh in-memory current-run markers using the accepted helper or equivalent high-entropy bounded generator:

- `memory_marker`;
- `response_marker`.

Turn 1 prompt must require remembering the memory marker and responding with the response marker.

After actual Turn-1 terminal require:

- terminal status COMPLETED;
- response marker present in the observed completed agent-message text.

After generation-1 shutdown, generation-2 acquire and confirmed resume, Turn 2 must request the exact memory marker.

After actual Turn-2 terminal require:

- terminal status COMPLETED;
- exact memory marker present in the observed completed agent-message text.

Do not persist raw markers to Git evidence or stage journal. Hash classes are allowed if needed.

The production-shaped fake must model the actual marker exchange, not return a generic `synthetic` message for these assertions.

## 3. Reasoning-effort authority must come from the authenticated default model

Do not hard-code `"medium"` in the production child.

From the single authenticated generation-1 catalog:

1. resolve the exact selected default model;
2. derive one accepted reasoning effort with `catalog.validate_reasoning_effort(default_model_id, None)` or an equivalent exact semantic snapshot lookup keyed by the selected default model;
3. preserve that exact reasoning authority across the generation rebound;
4. use the same selected model ID and reasoning effort for thread/start and Turns 1–4.

Do not use `snapshot.default_reasoning_effort[0][1]` unless the first tuple is independently proven to be the selected default model. Prefer an explicit keyed lookup.

Offline matrix must include a catalog where the default model is not the first entry and where its default effort is not `medium`.

PASS must still use the correct selected default model/effort with only one model-list acquisition.

## 4. Private umask before runtime/app-server creation

The P7.C15 future child must install:

`os.umask(0o077)`

before any runtime/app-server process can be created.

Restore the previous umask in `finally` after the child has converged.

This authority must cover the Codex/app-server subprocess so the approved `touch <target>` command creates a private target.

The target metadata gate remains strict:

- root owner (`uid == 0` in real production);
- regular file;
- nlink 1;
- mode `0600`;
- not symlink.

Offline proof must demonstrate target creation under the child/runtime umask and reject an ambient `0644` target.

## 5. Real production watchdog deadlines

Remove the fixed production watchdog values:

- `timeout_seconds=5.0`;
- `term_grace_seconds=0.2`;
- `kill_grace_seconds=0.2`.

Those may exist only as explicit offline injected test parameters.

Production default must use the accepted inherited real bounds:

- `p7c13.REAL_WATCHDOG_HARD_DEADLINE`;
- `p7c13.REAL_WATCHDOG_TERM_GRACE`;
- `p7c13.REAL_WATCHDOG_KILL_GRACE`;

or stricter architect-proven values that remain greater than the sum of internal stage bounds plus margin.

The positive offline production-shaped test must prove it selects real production deadline authority even if the fake child completes immediately.

## 6. Per-stage bounded owned waits

Parent watchdog is final containment, not the only timeout.

Use the accepted `_await_owned` semantics and `REAL_STAGE_TIMEOUTS` (or P7.C15 equivalents no weaker than the accepted P7.C13 bounds) for every potentially blocking production operation, including at minimum:

- runtime generation 1 acquire;
- model catalog acquisition;
- thread/start;
- Turn 1 start and terminal;
- runtime generation 1 shutdown;
- runtime generation 2 acquire;
- thread/resume;
- Turn 2 start and terminal;
- Turn 3 start;
- approval handling + second-request/terminal convergence;
- Turn 3 terminal;
- Turn 4 start;
- accepted Turn-4 active/interrupt convergence;
- shutdown before physical oracle;
- controller open/schema/binding operations;
- canonical application delete;
- final runtime shutdown;
- tombstone/live-binding observations;
- controller close.

No detached task after timeout/cancellation.

Offline timeout tests must prove fail-closed convergence and zero duplicate RPC/delete response.

## 7. Production clocks, not test clocks

Remove fixed production clocks such as:

- `now_ms=lambda: 10`;
- `now_ms=lambda: 20`.

Production defaults must use the normal application/storage clock authority.

Clock injection may exist only through explicit offline test seams/factories and must not be selected by the real default.

Static tests must reject fixed synthetic clocks in the production path.

## 8. Full current-run marker authority for the physical oracle

The current-run target material set must include, at minimum:

- fresh `memory_marker`;
- fresh `response_marker`;
- exact approval target path;
- exact Turn-3 explicit-escalation prompt;
- exact Turn-4 stimulus.

Do not replace those with the generic P7.C15 profile ID.

The pre-delete oracle must be conclusive and target-specific.

Historical P7.C14 material must remain unrelated.

## 9. Separate persistent and isolated post-delete observations

After canonical delete, use separate observed families as in the accepted inherited authority:

- persistent families: sessions/history;
- isolated families: sqlite/logs.

Do not pass one combined `OracleObservation` as both persistent and isolated proof.

PASS requires independently:

- persistent thread residuals 0;
- persistent marker residuals 0;
- isolated thread residuals 0;
- isolated marker residuals 0;
- family scan errors 0.

## 10. Derive unrelated-removal fact

Before delete, take the accepted target metadata snapshot and target-path authority.

After delete, take the corresponding post-delete snapshot.

Derive:

`unrelated_target_specific_removal_detected`

using the accepted helper/equivalent, excluding exact target paths.

PASS requires false.

Do not rely on the default argument or a literal false.

Add a negative case where unrelated target-specific material disappears and PASS is rejected.

## 11. Isolation-envelope revalidation

After delete independently validate the P7.C15 isolation authority/envelope, not only descendant special/symlink counts.

Use the accepted `IsolationPathAuthority` / `IsolatedStateRoot.validate()` semantics or an equivalent current-run authority.

Combine with observed descendant facts:

- sqlite special = 0;
- sqlite symlink = 0;
- logs special = 0;
- logs symlink = 0.

PASS requires the full envelope to be valid.

## 12. Re-read schema v4 after delete

The controller schema must be observed as v4 before binding and independently re-read as v4 after delete before storage close.

Do not infer post-delete schema from the pre-delete value.

Add a negative fake where post-delete schema drifts and PASS is rejected.

## 13. Parent process-group proof remains parent-owned

Do not hard-code child post-delete facts:

- `owned_children=0`;
- `owned_group_active=False`;
- `owned_group_zombies=0`;
- `unrelated_signals=0`.

The child cannot establish final parent process-group quiescence before it exits.

Follow the accepted P7.C13 separation:

- child post-delete oracle receives unknown/not-applicable values for parent-owned process-group facts;
- child result proves runtime-child quiescence;
- parent watchdog independently requires active=0, zombies=0, scan errors=0 and no unrelated signals/effects before ledger COMPLETED.

If `post_delete_acceptance` needs explicit optional values, use the accepted P7.C13 invocation shape rather than fabricated zeros.

## 14. Strengthen parent PASS predicate

Parent `COMPLETED` must require all of:

- owned watchdog status COMPLETED;
- valid root-only child result;
- child status PASS;
- child verdict true;
- child runtime quiescent true;
- exact positive effect counts (not only ceilings):
  - new_threads 1;
  - model/list 1;
  - thread/start 1;
  - thread/resume 1;
  - turn/start 4;
  - approval_responses 1;
  - allow_responses 1;
  - turn/interrupt 1;
  - thread/delete 1;
  - thread/read 0;
  - thread/list 0;
  - second_child 0;
  - real_retry 0;
  - telegram 0;
- parent owned process group active 0;
- zombies 0;
- scan errors 0.

Missing/under-counted required effects must make PASS impossible.

## 15. Complete negative production matrix

Preserve all Repair-2 negative cases and add explicit production-shaped cases for at least:

1. real-client-shaped approval client with no fake counters => positive path still works;
2. second Turn-3 request observer => fail, no second response;
3. non-first default model / non-medium default reasoning effort => correct model/effort used;
4. Turn-1 response marker missing => fail before restart;
5. Turn-2 memory marker missing => fail before Turn 3;
6. target created with non-private mode => fail before Turn 4;
7. production watchdog selects real deadline authority;
8. one internal stage timeout => fail closed, no detached task/retry;
9. live binding remains after delete => fail;
10. unrelated target-specific removal => fail;
11. isolation envelope invalid => fail;
12. post-delete schema not v4 => fail;
13. missing one required positive effect count => parent cannot complete;
14. persistent-only residual => fail;
15. isolated-only residual => fail;
16. existing Repair-2 DELETE_UNKNOWN / CONFIRMED_PENDING / tombstone / scan-error / target-metadata / Turn4 negatives remain passing.

## 16. Static anti-test-leakage gates

Fail the suite if production source depends on equivalent test-only authority:

- `response_calls`;
- `pending_approval_count`;
- fixed five-second production watchdog timeout;
- fixed `0.2` production watchdog grace;
- hard-coded production `"medium"` effort;
- fixed Turn-1/Turn-2 marker text without fresh markers;
- `now_ms=lambda: 10` / `20` or equivalent fixed production clock;
- one combined oracle reused as persistent and isolated proof;
- hard-coded parent process-group zeroes in child acceptance;
- default/literal unrelated-removal false;
- PASS without post-delete schema re-read.

## 17. Preserve already accepted real continuation

Do not regress:

- actual Turn-3 RPC;
- C11 prompt;
- root-only wire/recovery authority;
- P7.C12 matcher;
- one bridge response/ALLOW;
- target proof/cleanup;
- actual Turn-4 observer/interrupt;
- fresh schema-v4 controller IDLE binding;
- one canonical `DialogueDeleteService.delete()`;
- independent official delete observation;
- UNKNOWN / CONFIRMED_PENDING no-retry semantics;
- actual post-delete tombstone/live-binding/residual gate;
- stage/effect coupling;
- live-budget exception accounting;
- parent terminal projection.

## File scope

Allowed tracked modifications only:

- `tests/real/test_p7_c15_final_hard_delete_successor.py`;
- `docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`.

Optional one P7.C15-only helper under `tests/real/` only if strictly necessary.

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

- focused P7.C15 Repair-3;
- complete production-shaped positive full handoff using a real-client-shaped fake;
- complete negative matrix above;
- P7.C14/P7.C13 offline regressions;
- P7.C12 focused;
- relevant P7.C2-P7.C5 regressions;
- complete non-real pytest with all real gates unset;
- unittest discovery with all real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## Gate-disabled smoke

With all P7.C15 real vars unset:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c15_final_hard_delete_successor --p7c15-real-run`

must exit `2`, create no P7.C15 production ledger and start no Codex/app-server process.

## Evidence

Update:

`docs/evidence/p7c15/P7C15_HARD_DELETE_SUCCESSOR_PREP_EVIDENCE_2026-09-12.md`

with:

- `P7C15_REPAIR3_BASE_HEAD=52e20e42e451955ba0d417a47d89903cadf142f2`;
- `P7C15_REPAIR3_BASE_TREE=03c555267442b8ce6df5255e08152c2cd112908c`;
- `PRIOR_P7C15_LAUNCHER_BLOB=7303cebc8fd157ecef590b4ec9575453ee982176`;
- `PRIOR_P7C15_EVIDENCE_BLOB=5cde70aea9e3b7d089deece991b677e6ea61b74e`;
- final launcher/evidence/helper blobs;
- real-client-shaped approval proof;
- exact memory/response marker proof;
- selected default model/reasoning proof;
- umask/target-mode proof;
- production watchdog deadline proof;
- internal stage-timeout ownership proof;
- persistent/isolated family proofs;
- unrelated-removal derivation proof;
- isolation-envelope proof;
- post-delete schema re-read proof;
- exact positive effect-count parent gate;
- full validation totals and zero-real-effect accounting.

Required final lines:

`P7C15_REPAIR3_REAL_CLIENT_APPROVAL_AUTHORITY=PASS|FAIL`

`P7C15_REPAIR3_TURN1_TURN2_MEMORY_PROOF=PASS|FAIL`

`P7C15_REPAIR3_REASONING_AUTHORITY=PASS|FAIL`

`P7C15_REPAIR3_PRIVATE_UMASK_TARGET=PASS|FAIL`

`P7C15_REPAIR3_REAL_WATCHDOG_BOUNDS=PASS|FAIL`

`P7C15_REPAIR3_STAGE_TIMEOUT_OWNERSHIP=PASS|FAIL`

`P7C15_REPAIR3_POST_DELETE_OBSERVED_AUTHORITY=PASS|FAIL`

`P7C15_REPAIR3_EXACT_EFFECT_PASS_GATE=PASS|FAIL`

`P7C15_REPAIR3_PRODUCTION_SHAPED_FULL_HANDOFF=PASS|FAIL`

`P7C15_PREP_READY=YES|NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c15-hard-delete-successor-repair3-2026-09-13`

created from exact Repair-2 candidate `52e20e42e451955ba0d417a47d89903cadf142f2`.

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect acceptance is required before any P7.C15 real token or one-shot execution contract exists.
