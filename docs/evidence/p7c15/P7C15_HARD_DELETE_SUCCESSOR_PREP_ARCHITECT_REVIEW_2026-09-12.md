# P7.C15 hard-delete successor preparation — architect review — 2026-09-12

Status: **REWORK_REQUIRED / PRODUCTION PARENT-CHILD PATH NOT MATERIALIZED / ZERO REAL EFFECT**

## Candidate reviewed

- candidate HEAD: `11ea49d1bf6369b27f293ff58a9ba62ad52333a1`;
- tree: `faa3c889860832a56ffbd2332760d4b90673b8ef`;
- exact base: `98e168c82f7fd9d8f50c491017323e97d3ed396f`;
- P7.C15 launcher blob: `37b5926ad998fb146bba154546059d9d1439bb38`;
- evidence blob: `508000c76ede6373455dec70e910becc5b0b4b6b`;
- inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Lineage and scope are accepted: two linear commits from the accepted P7.C14 forensic head and only the P7.C15 module/evidence changed.

## Accepted preparation algorithms

The following offline work is accepted for reuse:

- deterministic reproduction of the P7.C14 `TURN_PRECONDITION_CHANGED` generation mismatch;
- strict `CodexTurnLifecycleAdapter` generation check remains untouched;
- `GenerationTrackingRuntimeManager` fail-closed generation/profile authority;
- immutable generation-1 semantic catalog snapshot;
- generation-rebound catalog view that changes only runtime-generation authority;
- single semantic `model/list` acquisition guard;
- synthetic restart/resume -> Turn-2 dispatch proof with one model-list;
- P7.C15 distinct source gate, env names, profile and ledger namespace;
- P7.C15 safe stage-journal data model;
- live-budget child-result selection helper;
- parent exit projection helper;
- temporary ledger terminal-consumption tests;
- zero-real-effect validation and immutable historical authorities.

## Hard blocker: future production path is still synthetic/stubbed

`P7C15PreparedFutureExecutor.production()` does not assemble a real-capable P7.C15 parent/child execution.

It computes `fresh_paths = p7c15_fresh_run_paths(...)`, but the nested `future_child` only constructs a command tuple and then executes `del command, fresh_paths`; it returns a synthetic `FAILED / future=NOT_RUN` mapping. No child subprocess, owned process group, watchdog, root-only child result, or real adapter graph is invoked.

The prepared command is also wrong: `--boot-authority` is given `boot["child_result_path"]` rather than the boot-authority path.

`_module_main(... --p7c15-future-child ...)` merely verifies the supplied path exists and then always returns `1`; there is no P7.C15 real child dispatcher/orchestrator behind this CLI.

Therefore a future exact authorized P7.C15 call would reserve the new one-shot ledger and then deterministically fail without exercising the accepted hard-delete flow.

## Production authority/path blockers

The production executor currently calls `_synthetic_boot(root, contract)`. That helper is test authority and binds fixed synthetic-style names such as `ledger.json`, `result.json`, and `p7c15-boot-synthetic.json`; it does not materialize the computed fresh `p7c15-*` authority set for the real run.

Consequences include:

- the boot ledger path is not the actual `/root/.codexcontrol/p7c15-one-shot.json`;
- boot/result/stage/wire/journal paths are not the fresh production paths computed by `p7c15_fresh_run_paths()`;
- the fixed synthetic boot filename could collide after the real ledger is reserved;
- no production root-only child-result writer/reader/validator exists;
- no production watchdog validates result and owned-process-group quiescence.

## Production correction mechanisms are not wired

The accepted correction components are currently exercised only by fake/synthetic tests:

- `GenerationTrackingRuntimeManager` / `GenerationReboundCatalogView` are not used by a production real child;
- `P7C15StageJournal` is not created or updated by a production real child;
- `_p7c15_child_result_payload()` live-budget selection is not used by a production exception path;
- safe `TurnLifecycleError.category` and last-confirmed-stage persistence are not connected to a real child result.

Thus the evidence claims for generation correction, failure accounting, journal/category persistence and exact authorized synthetic handoff are valid as algorithm-level/offline proofs, but they do not establish a future production execution path.

## Required Repair-1

Repair-1 must be an integration repair only. Preserve the accepted algorithms above and materialize them into the future production path:

1. a real P7.C15 parent executor with the distinct real ledger and fresh `p7c15-*` paths;
2. one root-only bounded P7.C15 boot authority that binds exact source, P7.C15 launcher blob, actual P7.C15 ledger, fresh paths, effect ceiling and stage path;
3. one owned child subprocess/process group with a bounded watchdog and no retry;
4. exact child command with deterministic `PYTHONPATH` and the **boot path** passed to `--p7c15-future-child`;
5. an actual `--p7c15-future-child` dispatcher that reads the boot authority and enters a production-capable P7.C15 child orchestration;
6. production use of generation tracking + one authenticated model-list semantic snapshot + generation-rebound view after restart;
7. production stage-journal updates around real effect boundaries;
8. production exception handling that serializes the actual live child budget/category/last stage;
9. bounded root-only P7.C15 child-result writer/reader/validator;
10. parent ledger terminal mapping from the child result and watchdog, with failed/non-pass states projected nonzero by the CLI;
11. exact-authorized **production-shaped** offline parent -> boot -> child-entry -> fake adapters -> result -> parent validation proof;
12. static anti-stub gates proving the production path contains no `future=NOT_RUN`, no fixed synthetic boot/result names, and no child CLI that unconditionally returns failure.

No real P7.C15 effect is authorized by this review.

## Verdict

`P7C15_PREP_ALGORITHMS_ACCEPTED=YES`

`P7C15_PREP_PRODUCTION_PARENT_CHILD_PATH=REWORK_REQUIRED`

`P7C15_PREP_ARCHITECT_ACCEPTED=NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
