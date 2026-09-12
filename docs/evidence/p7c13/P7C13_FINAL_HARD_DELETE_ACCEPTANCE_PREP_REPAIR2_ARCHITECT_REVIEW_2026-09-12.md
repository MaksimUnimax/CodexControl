# P7.C13 preparation Repair-2 architect review — 2026-09-12

Status: **REWORK_REQUIRED / INFRASTRUCTURE ACCEPTED / PRODUCTION CHILD WIRING NOT ESTABLISHED / REAL EXECUTION FORBIDDEN**

## Reviewed candidate

- Repair-2 commit: `aae95407650c10b16387bbe4a27cec8bd96efe2b`.
- Parent/base: `e0e1cd4c3aaaf2a89e1bf4c510a67203865e7247`.
- Harness blob: `10ba4084a086a597c892a2fef8409d6c46986062`.
- Evidence blob: `e9da4b0d19903fbffbb46448afe062ec5d9c58e3`.
- Base-to-head: one linear commit; only the P7.C13 harness and P7.C13 evidence change.
- Accepted P7.C12 matcher remains unchanged.

## Accepted Repair-2 corrections

Repair-2 materially closes several prior preparation defects:

- future-child CLI dispatch exists and does not enter unittest mode;
- root-only boot authority exists with bounded schema/ownership/identity checks;
- durable one-shot ledger precedes boot/child creation;
- parent/child process-group watchdog is prepared;
- pre-dispatch budget bridge exists;
- distinct Turn-1/2/3/4 authority models exist;
- independently owned Turn-3 thread/Turn/cwd/sequence/target checks exist in the synthetic orchestrator;
- Turn-4 distinct active binding is represented;
- persistent session content/filename/directory and marker residual oracle is present;
- unrelated target-specific removal is an explicit acceptance blocker;
- canonical `DialogueDeleteService` fake/integration coverage remains present;
- zero-real-effect boundary was preserved.

These pieces are accepted and must not be weakened in the next repair.

## Blocking defect A — production child defaults to synthetic seams

The future CLI parent now launches the same module with `--p7c13-future-child`, and `_module_main()` correctly routes that mode to `_future_child_main()`.

However, `_future_child_main()` has no production seam assembly. When no test injection is supplied it calls `_default_child_seams(...)`.

Those default seams are synthetic: model-list/thread-start/resume/shutdown return simple booleans, Turn-1/Turn-2 return fabricated strings, Turn-3 returns a synthetic matcher capture, Turn-4 returns a fabricated binding, pre-delete returns a fabricated observation, controller binding is synthetic, and delete returns literal `"DELETED"`.

The future default child therefore does **not** perform the real acceptance workflow even though it constructs a `CodexRuntimeManager` object.

The candidate also has no production use of `CodexModelCatalogAdapter`, `CodexTurnLifecycleAdapter`, or `CodexApprovalBridge` in the future default child path.

A real one-shot execution against this candidate would be a synthetic PASS path, not a real Codex hard-delete acceptance.

## Blocking defect B — real binding is synthetic

The default `_future_child_main()` creates:

`FlowBinding("synthetic-future-thread", "turn-1", boot["workdir"], 1)`.

That value is not the binding returned by a real `thread/start`, and the subsequent Turn authority cannot therefore prove ownership of the actual new real thread/Turns.

The real default path must derive the thread binding from `CodexThreadLifecycleAdapter.start()` and each Turn ID/binding from the corresponding real `CodexTurnLifecycleAdapter.start_turn()` result.

## Blocking defect C — split child-result schemas

Repair-2 introduced the strict `p7c13-repair2-child-result-v1` authority and `read_child_result()` / `_safe_child_result_authority()`.

But `OwnedParentChildWatchdog.run()` still validates the child file through the older `_safe_child_result()` contract for `p7c13-child-result-v1` with the old key set.

Therefore a correctly written Repair-2 child-result can be classified as `MALFORMED_CHILD_RESULT` by the watchdog before the parent strict readback.

There must be exactly one accepted child-result schema/validator shared by watchdog and parent. Parent success must require the new exact source/run authority, `status=PASS`, `verdict=true`, valid effects/residuals and process-group quiescence.

## Blocking defect D — one ALLOW is modeled as two response callbacks

`FutureChildSeams` exposes both `approval_response` and `allow_response`, and the orchestrator invokes both.

A supported Codex ALLOW is one protocol response. The final production operator must reserve both accounting facts (`approval_responses` and `allow_responses`) before returning/sending one `ApprovalDecision.ALLOW`; the bridge then sends exactly one response.

No future production path may send one generic approval response and then a second ALLOW response.

An unexpected request may consume the sole total approval-response slot as DENY only under fail-closed failure handling; success still requires one ALLOW and zero DENY.

## Blocking defect E — fixed non-fresh run paths

The production parent currently prepares fixed isolated/controller/workdir/approval-target names. P7.C13 requires a fresh run-specific isolated root, controller DB, working directory and high-entropy direct-child approval target.

The global one-shot ledger path may remain fixed as the replay barrier, but the run-owned mutable boundaries must be freshly generated, absent and independently preflighted before any real business effect.

The future child should run with a private umask or equivalent deterministic authority so exact `touch <target>` produces metadata accepted by the post-ALLOW gate.

## Blocking defect F — no explicit real parent CLI source gate

Child CLI dispatch now exists, but the exact one-shot parent invocation is still only a Python-callable `future_real_entrypoint()`.

The accepted final harness must expose one gated parent execution entrypoint (CLI or exact gated real unittest) that derives/verifies current HEAD, TREE and harness blob from the worktree, checks the future architect environment/token, and only then enters `future_real_entrypoint()`.

A later execution contract must not need ad-hoc Python code to construct/invoke the parent path.

## Accepted historical real wiring authority

Repair-3 must reuse the already proven patterns rather than inventing new protocol semantics:

- P7.C11 accepted fresh-thread / root-only wire / approval-observation pattern;
- P7.C12 strict matcher and retained-authority projection;
- P7.C6 accepted real model catalog, thread lifecycle, turn lifecycle, approval bridge, interrupt and canonical delete patterns;
- P7.C4/C5 canonical storage cleanup / confirmed-pending / UNKNOWN / tombstone semantics;
- ADR-0045 shared persistent-home correction.

Historical one-shot latches and threads remain immutable and must never be executed or modified by Repair-3.

## Verdict

Repair-2 infrastructure: **PARTIALLY ACCEPTED**.

P7.C13 preparation overall: **REWORK_REQUIRED**.

No real one-shot execution contract is authorized from candidate `aae95407650c10b16387bbe4a27cec8bd96efe2b`.

`P7C13_REPAIR2_ARCHITECT_ACCEPTANCE=NO`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
