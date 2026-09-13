# P7.C15 hard-delete successor preparation Repair-1 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / PARENT-CHILD TRANSPORT ACCEPTED / HARD-DELETE CONTINUATION STILL SYNTHETIC / ZERO REAL EFFECT**

## Candidate reviewed

- candidate commit: `3dc12289fc34b4beac67e7139d740852c5caa2dc`;
- tree: `09446141fcb30875f0b8d081bd68b66ac6e73899`;
- parent/base: `11ea49d1bf6369b27f293ff58a9ba62ad52333a1`;
- launcher blob: `c129ac0820104b9860e50938a6529b3522773dbe`;
- evidence blob: `0b9c0780fdf541e3642a044de7eb7c6099541b1f`.

Lineage/scope are accepted: one linear Repair-1 commit over the frozen candidate and only the P7.C15 successor launcher plus P7.C15 preparation evidence changed. No `src/**`, historical P7.C14/P7.C13/P7.C12 source, package marker, migration, deployment, Telegram, P8 or P9 path changed.

## Accepted Repair-1 material

The following Repair-1 work is architect-accepted for reuse and must not be redesigned without a new defect:

- production P7.C15 ledger and fresh `p7c15-*` path construction;
- production root-only boot authority and boot-path child command;
- owned child/process-group watchdog wiring;
- actual `--p7c15-future-child` dispatcher and bounded P7.C15 child-result authority;
- production use of `GenerationTrackingRuntimeManager`, immutable semantic snapshot and `GenerationReboundCatalogView`;
- single-model-list generation transition through Turn 2;
- production stage journal construction;
- live-child-budget selection for exception-path accounting;
- safe `TurnLifecycleError.category`/last-stage fields;
- parent terminal-state and nonzero failure projection;
- positive and forced-failure production-shaped offline parent/child traversal.

## Sole remaining blocker: synthetic hard-delete continuation

`P7C15ProductionChildOrchestrator.run_async()` performs real-capable orchestration only through the corrected Turn-2 terminal boundary.

After Turn 2 it does **not** execute the accepted hard-delete continuation.

Instead the production source contains a loop that merely records/budgets named stages such as:

- `TURN3_START`;
- `APPROVAL_REQUEST`;
- `APPROVAL_RESPONSE`;
- `ALLOW`;
- `TURN3_TERMINAL`;
- `TURN4_START`;
- `TURN4_INTERRUPT`;
- `CONTROLLER_BINDING`;
- `THREAD_DELETE_DISPATCH`;
- `THREAD_DELETE_RESULT`;
- `APPLICATION_DELETE_RESULT`.

It then shuts down the tracker and returns a synthetic PASS payload containing `delete=OBSERVED`.

No actual Turn-3 RPC, approval request, C11 wire capture, C12 matcher, protocol ALLOW response, Turn-4 observer/interrupt, schema-v4 controller binding, `DialogueDeleteService.delete()`, official delete observation, tombstone/live-binding check, target-specific physical oracle or post-delete residual proof occurs in that production path.

The source comment itself says offline tests stop at this seam. Therefore a future real P7.C15 run could reserve the one-shot ledger, complete Turn 1/2, and then falsely report PASS without ever testing hard delete.

This is a hard blocker. `P7C15_PREP_READY=YES` is not architect-accepted yet.

## Required Repair-2

Repair-2 is an integration-only completion pass. It must keep all accepted Repair-1 parent/boot/watchdog/generation/accounting infrastructure and replace the synthetic post-Turn-2 stage loop with the already accepted real-capable continuation pattern from the frozen P7.C13 harness.

The P7.C15 production child after Turn 2 must actually execute:

1. Turn 3 using the exact C11 explicit-escalation stimulus;
2. root-only immutable wire capture/correlation;
3. accepted P7.C12 strict matcher;
4. one `CodexApprovalBridge` protocol response and one ALLOW only;
5. definitive Turn-3 completion and target metadata proof/cleanup;
6. distinct Turn 4 `sleep 120`, active/nonterminal proof, unexpected-request observer, one interrupt and definitive terminal;
7. runtime shutdown before physical oracle;
8. conclusive target-specific pre-delete physical observation;
9. fresh schema-v4 controller IDLE binding for the exact P7.C15 thread/profile;
10. exactly one canonical `DialogueDeleteService.delete()`;
11. independent official lifecycle delete observation;
12. correct UNKNOWN / CONFIRMED_PENDING handling with no retry/inference;
13. tombstone/live-binding/isolation/descendant/residual proof;
14. target-specific post-delete physical oracle;
15. runtime-child quiescence and accepted parent-group quiescence.

The production stage journal must surround the actual dispatch/confirmation boundaries, not substitute for the effects.

## Required offline proof

A production-shaped zero-real-effect positive test must traverse the same production continuation after Turn 2 using fake protocol/runtime/storage boundaries and demonstrate actual callback/RPC seams for Turn 3, approval, Turn 4, controller/delete and post-delete validation.

A mere stage-record loop is forbidden.

At minimum the test must prove:

- exactly one fake Turn-3 start dispatch;
- exactly one fake approval request and one protocol response;
- exactly one ALLOW and zero DENY on PASS;
- C12 exact matcher authority used;
- exactly one Turn-4 start and one interrupt;
- exactly one controller binding sequence;
- exactly one canonical delete-service invocation;
- exactly one independent official delete observation;
- post-delete acceptance uses observed facts;
- PASS is impossible when any required continuation fact is missing or wrong;
- P7.C15 effect budget/stage journal reflect actual fake dispatches rather than fabricated stage names.

A forced UNKNOWN/CONFIRMED_PENDING fake delete case must prove terminal non-PASS and no second delete/retry.

## Verdict

`P7C15_REPAIR1_PARENT_CHILD_TRANSPORT=ACCEPTED`

`P7C15_REPAIR1_GENERATION_REBOUND=ACCEPTED`

`P7C15_REPAIR1_FAILURE_ACCOUNTING=ACCEPTED`

`P7C15_REPAIR1_STAGE_JOURNAL=ACCEPTED`

`P7C15_REPAIR1_PARENT_EXIT_PROJECTION=ACCEPTED`

`P7C15_REPAIR1_REAL_HARD_DELETE_CONTINUATION=REWORK_REQUIRED`

`P7C15_PREP_ARCHITECT_ACCEPTED=NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
