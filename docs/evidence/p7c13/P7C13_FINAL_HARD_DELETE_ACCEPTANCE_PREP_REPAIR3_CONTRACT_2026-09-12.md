# P7.C13 preparation Repair-3 contract — production adapter wiring and final exact real harness — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / FINAL INTEGRATION REPAIR / NO REAL EXECUTION**

## Purpose

Repair-3 is the final preparation repair required before architect may issue the one-shot real P7.C13 execution contract.

Repair-3 must convert the already accepted Repair-2 infrastructure from a synthetic default child into the exact future real acceptance harness. After Repair-3 acceptance, no further code implementation may be required: the next architect action must be only a separate one-shot execution contract with exact source SHA/tree/harness blob/token and one direct real invocation.

## Exact base

Repair-3 starts from exact Repair-2 candidate:

- commit: `aae95407650c10b16387bbe4a27cec8bd96efe2b`;
- tree: `ea1c626fbf8c7884c8ea4f23bfbd45b33ff2d984`;
- harness blob: `10ba4084a086a597c892a2fef8409d6c46986062`;
- evidence blob: `e9da4b0d19903fbffbb46448afe062ec5d9c58e3`.

The accepted P7.C12 matcher blob remains immutable:

`f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

## Binding architect review

Repair-3 must obey in full:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_REPAIR2_ARCHITECT_REVIEW_2026-09-12.md`.

Preserve every Repair-1/Repair-2 component accepted there. Do not weaken durable ledger, boot authority, source gate, watchdog, effect ceilings, owned Turn checks, physical residual oracle, shared-home rules, UNKNOWN/confirmed-pending semantics, or canonical-delete requirement.

## Historical real wiring authority to reuse

Do not invent new Codex protocol semantics.

Use the already exercised patterns from:

- accepted P7.C6 real continuation harness for `CodexModelCatalogAdapter`, `CodexThreadLifecycleAdapter`, `CodexTurnLifecycleAdapter`, `CodexApprovalBridge`, terminal waiting, interrupt, runtime shutdown/reacquire and canonical delete;
- accepted P7.C11 fresh-thread/root-only wire authority and authoritative approval-capture pattern;
- accepted P7.C12 strict matcher;
- P7.C4/P7.C5 `DialogueDeleteService` / `DeleteStorageCleanupCoordinator` semantics;
- ADR-0045 shared persistent `CODEX_HOME` correction.

Historical latches/threads/results are read-only authority only. Repair-3 must never execute, mutate or reconcile a historical P7.C6-P7.C12 run.

## Absolute zero-real-effect boundary

Repair-3 implementation/tests must perform:

- real Codex process starts: `0`;
- app-server starts: `0`;
- real `model/list`: `0`;
- real thread start/resume/read/list/delete: `0`;
- real Turn start/interrupt: `0`;
- real approval responses/ALLOW/DENY: `0`;
- real persistent-home mutation: `0`;
- real isolated/controller/approval-target mutation: `0`;
- real P7.C13 ledger/boot/result creation under `/root/.codexcontrol`: `0`;
- Telegram: `0`;
- signals to real Codex/unrelated processes: `0`;
- historical authority mutation: `0`.

All Repair-3 execution tests must use injected synthetic adapters/temp paths/harmless child processes only.

Do not set the future architect authorization token.

## Repair A — production parent entrypoint must be direct and exact

Keep child CLI mode, and add/finish one exact future parent real mode, for example:

`--p7c13-real-run`

Ordinary module invocation remains unittest-only and cannot enter the real path.

Future parent mode must:

1. require the future authorization token and exact expected SHA/tree/harness blob from the environment fixed by the later architect execution contract;
2. derive current repository HEAD and tree from the actual checkout;
3. derive current harness blob from the tracked harness file;
4. require exact equality before any real ledger/boot/child creation;
5. require no tracked source drift;
6. call `future_real_entrypoint()` exactly once;
7. never synthesize its own authorization token;
8. never fall back to unittest or a second run after the one-shot path begins.

Tests must prove parent CLI wrong/unset token, SHA, tree, harness, or tracked-source drift yields zero ledger/boot/child/effect calls.

## Repair B — fresh run-owned real boundaries

The fixed synthetic/future mutable paths in Repair-2 are not acceptable production defaults.

The production parent must generate one fresh high-entropy run identity and fresh absent paths for:

- isolated state root;
- controller DB;
- working directory;
- approval target;
- boot/result supporting run paths where not globally fixed.

The global one-shot ledger path may remain a fixed P7.C13 replay barrier.

Approval target must be one high-entropy direct child of `/root` and satisfy all frozen exclusions.

Before child start, read-only/lstat/physical-identity preflight must prove mutable run-owned paths do not alias protected roots or each other and are absent/fresh as required.

Use a private future child umask (`077`) or equivalent deterministic authority before app-server creation so exact `touch <approval-target>` produces accepted non-group/world-writable metadata without changing the exact command.

## Repair C — remove synthetic default business seams from production

`_default_child_seams()` or any equivalent synthetic seam may exist only for explicitly injected tests.

The production call from `_future_child_main()` must never default to:

- `lambda: True` for model/thread/runtime/Turn effects;
- fabricated Turn output;
- synthetic `ApprovalAuthorityCapture`;
- fabricated pre-delete `OracleObservation`;
- synthetic `FreshSchemaV4ControllerBinding`;
- literal `"DELETED"` delete result.

There must be an explicit production seam factory/real orchestrator path. Static/AST tests must prove production child selection cannot resolve to the synthetic default seam.

## Repair D — real model catalog and fresh thread binding

Production child must:

1. validate installed Codex authority;
2. provision/validate exact fresh isolated root via accepted isolation authority;
3. create/acquire real `CodexRuntimeManager` generation;
4. call `CodexModelCatalogAdapter.get_catalog(profile_id)` exactly once;
5. require nonempty canonical catalog and exactly one visible default model;
6. use advertised default reasoning effort;
7. construct real `CodexThreadLifecycleAdapter` and `CodexTurnLifecycleAdapter`;
8. call real `thread/start` exactly once in the fresh workdir;
9. require `START_CONFIRMED`;
10. use the actual returned `ThreadBinding` as the sole thread authority thereafter.

No literal/synthetic thread ID may exist in the production default path.

## Repair E — real Turn 1 persistence establishment

Generate fresh in-memory memory/response markers.

Use real `CodexTurnLifecycleAdapter.start_turn()` on the actual fresh thread binding.

Use a bounded deterministic prompt that establishes the memory marker and requires the response marker.

Require real Turn start `CONFIRMED` and save the actual Turn-1 binding/ID.

Use the accepted bounded terminal wait path (`wait_turn` or exact current adapter authority) and require definitive `COMPLETED` plus actual observed output proving the response marker.

Do not fabricate output text.

Then fully stop/reap the owned runtime generation using accepted runtime shutdown logic.

## Repair F — real restart/resume and Turn 2 memory proof

Acquire a new owned runtime generation against the same profile/isolated root.

Reconstruct catalog/lifecycle authority as needed without a second model-list if the accepted pinned-catalog pattern supports it; total real `model/list` remains exactly one.

Call real `thread/resume` exactly once for the actual fresh thread and require `RESUME_CONFIRMED`.

Start real Turn 2 with a distinct actual Turn ID and require completed terminal/output containing the exact Turn-1 memory marker.

No fabricated output and no retained/historical thread selection.

## Repair G — one real approval bridge response, not two callbacks

Production success uses one `CodexApprovalBridge` protocol response.

Before Turn 3, independently select and lstat-prove the exact fresh target absent.

Arm accepted C11-style root-only wire capture / request chronology for the actual fresh thread, future Turn-3 authority, cwd and local sequence.

Start real Turn 3 with exact stimulus requiring the first-and-only escalated shell operation:

`touch <selected target>`

with `sandbox_permissions=require_escalated` and no default attempt / alternate command / retry.

The production approval operator must:

- validate exact request kind/thread/Turn/cwd/local-sequence/wire cardinality/SHA;
- project through the accepted P7.C12 strict matcher;
- validate selected target and target SHA;
- lstat-prove target still absent immediately before response;
- fail closed on any mismatch.

For an ALLOW candidate, reserve **both** accounting slots (`approval_responses` total and `allow_responses`) atomically before returning `ApprovalDecision.ALLOW` to the bridge.

`CodexApprovalBridge.handle_next()` then sends exactly one supported protocol response.

There must not be separate real `approval_response()` and `allow_response()` network callbacks.

Success requires exactly one request, one bridge result `ALLOWED`, one ALLOW, zero DENY, and no response-unknown.

If a DENY is used on an unexpected request for safe termination, it consumes the sole total approval-response slot, does not consume ALLOW, and the acceptance run cannot PASS.

## Repair H — real Turn-3 result and exact target postcondition

Use the actual Turn-3 binding returned by `start_turn`; it must be distinct from Turn 1/2 and owned by the same fresh thread/cwd.

After one confirmed ALLOW, wait for a definitive Turn-3 completed terminal.

Then lstat exact selected target and require safe root-owned regular-file metadata with no symlink/nlink ambiguity and private/no-group-world-write mode as frozen by the final harness.

Remove only that exact run-owned approval target after proof.

## Repair I — real Turn 4 active interrupt

Start real Turn 4 on the same actual fresh thread with exact bounded stimulus:

`sleep 120`

No write sentinel and no approval-response path.

Use the actual Turn-4 binding/ID and prove it is distinct from Turns 1/2/3.

Establish active/nonterminal state using the accepted bounded C6 continuation pattern.

Reserve the sole `turn/interrupt` slot **before** calling real `CodexTurnLifecycleAdapter.interrupt_turn(actual_turn4_binding)`.

Require accepted interrupt result and definitive interrupted/failed terminal, never UNKNOWN.

If another approval request appears, do not send a second response. Fail the acceptance path.

## Repair J — real runtime shutdown before physical oracle

After Turn 4, fully stop/reap the owned runtime generation before pre-delete scanning.

No C13-owned app-server child may remain active when storage measurement begins.

## Repair K — production physical pre-delete observation

Instantiate `BoundedTargetOracle` with the actual raw fresh thread ID and actual in-memory marker bytes.

Scan the real target-specific families required by the frozen contract.

Require zero scan/proof errors and at least one real target thread/marker occurrence before delete eligibility.

Do not fabricate `OracleObservation` in production mode.

Record only hashes/counts/classes in child/Git-safe evidence.

## Repair L — real fresh schema-v4 controller binding

Create/open the exact fresh protected controller DB and require schema v4.

Persist one canonical IDLE dialogue bound to the actual fresh P7.C13 thread/profile; no active job remains.

No fabricated `FreshSchemaV4ControllerBinding` is sufficient in production mode: the production path must use `SqliteStorage` / repositories and then re-read the durable binding.

## Repair M — canonical real delete exactly once

Assemble production:

- `CodexThreadLifecycleAdapter`;
- `DeleteStorageCleanupCoordinator`;
- accepted runtime manager;
- isolated authority;
- `DialogueDeleteService`.

The only destructive application call is exactly one:

`DialogueDeleteService.delete(DialogueDeleteRequest(...))`.

Reserve the frozen delete effect slot before this call can reach the external lifecycle adapter.

Do not add a raw `thread/delete` fallback.

Preserve exact UNKNOWN and confirmed-pending semantics.

## Repair N — production post-delete oracle

After the application result, ensure owned runtime/process authority is quiescent and run the real target-specific oracle again.

PASS requires every frozen post-delete gate including:

- official lifecycle result `DELETE_CONFIRMED`;
- application `DELETED`;
- exact bounded tombstone;
- no live binding;
- valid isolated envelope;
- zero isolated descendants;
- zero persistent thread content/filename/directory/history residual;
- zero persistent marker residual;
- zero isolated thread/marker residual;
- zero scan/proof error;
- unrelated target-specific removal detected = false;
- no owned app-server child/process-group residual;
- no unrelated process signal;
- exact budget accounting.

## Repair O — unify child-result authority

Delete/retire the old split validator semantics.

There must be one final child-result schema only (the Repair-3/final version).

The watchdog and parent strict readback must use the same authority definition, or the watchdog must defer validity to one injected strict validator bound to the exact boot record.

A correct final child result must never be rejected merely because an older schema checker runs first.

Parent PASS requires at minimum:

- safe regular root-only result authority;
- exact source HEAD/tree/harness/run binding;
- final schema;
- `status=PASS`;
- `verdict=true`;
- effect counts exactly within ceilings and forbidden counts zero;
- finite expected Turn/approval/interrupt/delete classes;
- residual counts zero where required;
- process-group quiescence true.

A syntactically valid `FAILED`/`UNKNOWN` child result cannot produce parent PASS.

## Repair P — parent/child ordering and terminal one-shot state

Future parent ordering remains strictly:

`source gate -> ledger O_EXCL reserve -> fresh boot authority -> one child -> strict child result -> process-group quiescence -> terminal ledger update`.

No second child, retry, or automatic rerun.

If child outcome is UNKNOWN/confirmed-pending/incomplete, preserve recovery identity and terminal consumed ledger semantics without manufacturing COMPLETED/PASS.

## Required static gates

Repair-3 tests must inspect the final harness AST/source and fail if the production default path:

- calls `_default_child_seams` / synthetic seam factory;
- contains a literal synthetic thread binding;
- uses literal `"DELETED"` as production delete authority;
- fabricates Turn output in the production path;
- provides separate two-response ALLOW callbacks;
- bypasses `CodexModelCatalogAdapter`, `CodexThreadLifecycleAdapter`, `CodexTurnLifecycleAdapter`, `CodexApprovalBridge`, or `DialogueDeleteService` in the production path;
- contains raw `thread/read` or `thread/list` success inference;
- contains a second/raw delete fallback.

Synthetic injected test paths are permitted but must be unmistakably non-production and inaccessible from production default selection.

## Required Repair-3 offline tests

At minimum, with all real effects mocked/injected:

1. parent real CLI unset token -> zero ledger/boot/child;
2. exact synthetic future token/source -> parent enters prepared executor once;
3. source SHA/tree/harness/tracked-drift mismatch -> zero child;
4. production child factory selects real seam factory, never synthetic default;
5. real-factory model catalog called once;
6. exactly one default model required;
7. real-factory thread start result becomes owned binding;
8. start rejected/unknown fails;
9. Turn-1 actual fake adapter binding/output drives proof;
10. missing/wrong Turn-1 output marker fails;
11. runtime shutdown/reacquire ordering proven;
12. thread resume exact fresh binding once;
13. Turn-2 actual fake adapter output memory proof;
14. Turn IDs derive from fake adapter results and are pairwise distinct;
15. C11-style capture from fake approval request binds actual fake thread/Turn/cwd/sequence;
16. exact matcher => operator reserves total-response+ALLOW before one bridge response;
17. unexpected request cannot ALLOW;
18. one ALLOW produces one protocol response callback, not two;
19. response unknown fails;
20. target absent-before / safe-present-after / exact cleanup gates;
21. Turn-4 actual fake binding distinct;
22. active-before-interrupt required;
23. interrupt slot reserved before fake interrupt callback;
24. second approval during Turn 4 gets no second response;
25. runtime shutdown before pre-delete scanner;
26. pre-delete scanner gets actual fake thread ID/marker bytes;
27. empty pre-delete observation blocks delete;
28. controller schema-v4 DB durable IDLE binding uses actual fake thread;
29. canonical `DialogueDeleteService.delete()` fake called exactly once;
30. delete budget exhausted prevents second service call before entry;
31. DELETE_UNKNOWN remains terminal/no retry;
32. confirmed-pending remains no external retry;
33. post-delete scanner actual binding/residual gates;
34. filename/directory/history/marker residuals fail;
35. unrelated-removal gate fails;
36. watchdog validates the final child-result schema, not old schema;
37. valid FAILED child result cannot parent-PASS;
38. valid PASS result with wrong source/run cannot PASS;
39. one-shot ledger remains consumed after failure/UNKNOWN;
40. fresh run-owned mutable paths are unique/absent/non-aliased;
41. production child private umask / approval-target mode contract is deterministic;
42. static AST production-path anti-synthetic gates all pass.

No real Codex/app-server calls may occur in these tests.

## Validation

Run both:

1. focused Repair-3 P7.C13 suite plus P7.C12 and relevant C2/C3/C4/C5 suites;
2. complete non-real pytest regression with every real authorization gate unset;
3. ordinary `unittest discover` with every real authorization gate unset.

Also run compileall, `git diff --check`, leakage/security scan and exact changed-file scope check.

Historical consumed-latch tests may remain separately deselected/skipped where their absence premise conflicts with preserved consumed authority; never rewrite/delete latches.

## Allowed repository scope

Allowed tracked changes only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`;
- optionally one P7.C13-only helper under `tests/real/` if strictly necessary.

No `src/**`, P7.C12 matcher, historical P7.C6-P7.C12, schema migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP change.

## Required final evidence lines

`P7C13_REPAIR3_PRODUCTION_PARENT_ENTRY=PASS|FAIL`

`P7C13_REPAIR3_PRODUCTION_ADAPTER_WIRING=PASS|FAIL`

`P7C13_REPAIR3_REAL_THREAD_TURN_BINDINGS=PASS|FAIL`

`P7C13_REPAIR3_SINGLE_PROTOCOL_ALLOW=PASS|FAIL`

`P7C13_REPAIR3_REAL_PHYSICAL_ORACLE_WIRING=PASS|FAIL`

`P7C13_REPAIR3_REAL_CONTROLLER_DELETE_WIRING=PASS|FAIL`

`P7C13_REPAIR3_UNIFIED_CHILD_RESULT_AUTHORITY=PASS|FAIL`

`P7C13_REPAIR3_NO_SYNTHETIC_PRODUCTION_DEFAULT=PASS|FAIL`

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Acceptance consequence

If Repair-3 passes independent architect review, architect shall not request another implementation pass. Architect will freeze a separate P7.C13 one-shot real execution contract against the exact accepted Repair-3 SHA/tree/harness blob and one-time token.

Until then all real P7.C13 effects remain forbidden and P8/P9 remain blocked.
