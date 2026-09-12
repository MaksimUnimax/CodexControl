# P7.C13 preparation Repair-3 architect review — 2026-09-12

Status: **REWORK_REQUIRED / REAL ADAPTER WIRING MATERIAL / REAL EXECUTION STILL NOT AUTHORIZED**

## Reviewed candidate

- Repair-3 base: `aae95407650c10b16387bbe4a27cec8bd96efe2b`.
- Repair-3 implementation: `8d13a3e5c3ddbcf0daf249dc4b404557de9c2e70`.
- Repair-3 final candidate / child-module dispatch correction: `75f1ccbcc839fc49c0602acfb9d9c19c9f587a30`.
- Final tree: `2c240993be4d7998c94b455c347c2065176adbd7`.
- Final harness blob: `b60a38c90317ec83063f314eb189af9c66e735cb`.
- Final evidence blob: `589522b6832102aa76caf756323d235ed4fd3bd8`.

The base-to-head history is linear and changes only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, accepted P7.C12 matcher or historical P7.C6-P7.C12 authority changed.

## Materially accepted Repair-3 progress

Repair-3 materially fixes the prior synthetic-default defect:

- direct `--p7c13-real-run` source gate exists;
- production `_future_child_main()` selects `build_production_real_seam_factory()` by default;
- actual `CodexModelCatalogAdapter`, thread lifecycle, turn lifecycle, approval bridge and `DialogueDeleteService` are present in the production path;
- thread/Turn identities are derived from adapter results rather than a production literal synthetic thread;
- one unified Repair-3 child-result schema is used by strict parent readback;
- fresh run-owned path generation exists;
- one-shot ledger and parent/child topology are retained;
- synthetic default seams are injection-only;
- zero-real-effect Repair-3 execution boundary was preserved.

These corrections are accepted and must not be removed in Repair-4.

## Blocker 1 — approval matcher is not bound to accepted C11 root-only wire authority

`ProductionApprovalOperator.decide()` reconstructs all three C12 matcher objects from the approval request context itself. It builds `CapturedRequest`, `ExpectedAuthority` and `CorrelatedWireRecord` from one `command:` line and expected local values.

It does not use the accepted P7.C11 `WireCommandAuthority` / immutable root-only wire record / exact capture correlation. It does not independently prove one wire record, actual request kind, actual cwd authority, request ordinal versus local sequence, or durable wire SHA from root-only evidence.

The accepted C11 pattern explicitly captures once into root-only authority and correlates an in-memory request to that immutable record before any matcher projection. Repair-3 therefore violates the frozen Repair-3 contract section requiring C11-style root-only wire capture/correlation.

This is a hard safety blocker for real ALLOW.

## Blocker 2 — Turn-3 stimulus lost explicit escalation authority

The production Turn-3 user text is currently only equivalent to:

`Run exactly: touch <target>`.

The accepted C11 source-backed stimulus requires a first-and-only shell tool call, exact `touch <target>`, explicit `sandbox_permissions=require_escalated`, no default-sandbox attempt first, no alternate command/tool/path/network access and no retry.

Without that explicit stimulus the future run can fail to elicit the exact approval path or can follow a different tool sequence. Real ALLOW is not authorized.

## Blocker 3 — request kind/cwd/ordinal are not independently validated

The production operator hardcodes the matcher kind to `COMMAND_EXECUTION` instead of requiring the actual approval request kind. It hashes the expected cwd into all projected matcher objects instead of proving the actual request cwd from one exact context/authority. It also reuses `request.local_sequence` as both request ordinal and local sequence.

A matcher tuple built this way can become internally self-consistent without establishing the exact live request facts required by P7.C12/C11.

Repair-4 must independently establish actual kind, request ordinal, local sequence, thread, Turn, cwd and wire SHA before matcher invocation.

## Blocker 4 — Turn 4 is interrupted without active/nonterminal proof

Production Turn 4 starts `sleep 120`, checks `START_CONFIRMED`, immediately reserves the interrupt slot and dispatches `interrupt_turn()`.

It does not establish the accepted C6 active/nonterminal-before-interrupt fact or race against an already-terminal Turn. The frozen contract requires the real Turn-4 binding to be proven active before the one interrupt.

## Blocker 5 — post-delete acceptance contains asserted constants instead of observations

The production post-delete call currently supplies acceptance facts such as:

- official lifecycle result `DELETE_CONFIRMED`;
- bounded tombstone `True`;
- no live binding `False`/absence as a constant;
- isolated envelope valid `True`;
- isolated sqlite/log descendant counts `0`;
- unrelated-target-specific removal `False`;
- several process/scan values as constants.

Only the target-content oracle itself is materially observed.

This is not a valid hard-delete acceptance oracle. The real run must derive official P1.9 status, tombstone, live dialogue/binding, isolated envelope, descendant counts and attribution-safe unrelated-removal result from actual runtime/storage observations.

## Blocker 6 — official P1.9 result is not independently observed

`DialogueDeleteService.delete()` is called, but the underlying real lifecycle `CodexThreadLifecycleAdapter.delete()` result is not instrumented/recorded independently. The application result `DELETED` is then used together with a hardcoded official `DELETE_CONFIRMED` acceptance value.

The final acceptance must distinguish official P1.9 status from application status and preserve `DELETE_UNKNOWN` exactly.

## Blocker 7 — production isolation authority is internally inconsistent

`build_production_real_seam_factory()` constructs `IsolationPathAuthority` with:

- `controller_db_path=<fresh controller file>` before that file exists;
- `repository_root=<fresh workdir>` before that directory exists;
- `protected_roots` containing the same persistent `CODEX_HOME` that is also the profile home.

Production `IsolationPathAuthority` rejects protected/profile overlap and runtime validation requires protected/controller authorities to exist. The fresh workdir is also not created before `thread/start`.

Repair-4 must use the accepted pattern: actual repository root as repository authority, a safe controller parent/root authority before the DB exists (or create the exact DB safely before runtime if contractually allowed), persistent home as profile home rather than a duplicate protected root, and explicit creation/validation of the private fresh workdir.

## Blocker 8 — required mount/external-user preflight is not on the production path

The candidate retains an offline `read_only_boundary_preflight()` test seam, but the real parent/child path does not establish the frozen `/proc/self/mountinfo`/filesystem alias and exact-owned-boundary external-user gate before real business RPC/destructive cleanup.

Repair-4 must put the accepted read-only safety preflight on the actual future production path.

## Blocker 9 — production watchdog deadline/quiescence probes are still synthetic defaults

`PreparedFutureRealExecutor.production()` constructs `OwnedParentChildWatchdog()` with default active/zombie probes that return zero, and `run()` uses the watchdog's short synthetic default timeout unless overridden.

A real four-turn + delete acceptance cannot be correctly governed by a two-second synthetic deadline, and process-group quiescence cannot be accepted from `lambda: 0` probes.

Repair-4 must use a finite real deadline derived from bounded internal stage authorities and real `/proc`-backed owned-process-group active/zombie observation, while still signalling only the exact owned group.

## Blocker 10 — child process-group PASS field is asserted

The Repair-3 child result publishes `process_group_quiescent=True` as a constructed value rather than a measured child-side fact. Parent process-group quiescence is a separate parent authority and must not be forged by the child.

The final schema must clearly separate child runtime/app-server quiescence from parent OS process-group quiescence, and parent PASS must own the latter measurement.

## Blocker 11 — one-shot terminal state loses UNKNOWN / confirmed-pending classes

The parent currently collapses non-PASS child outcomes into generic `FAILED` ledger state. Production orchestration also raises a generic preparation error for non-`DELETED` application results.

Final P7.C13 must preserve official `DELETE_UNKNOWN` and application `CONFIRMED_PENDING_STORAGE` as finite, terminal, consumed recovery classes. Neither may be rewritten as success or automatically retried.

## Blocker 12 — source cleanliness check misses staged tracked drift

The source gate uses a working-tree `git diff --quiet HEAD -- .` check, which does not prove the index has no staged tracked changes. The future exact source gate must reject any tracked worktree or index drift while still allowing explicitly tolerated untracked files.

## Verdict

- production adapter presence: **ACCEPTED**;
- actual adapter-derived thread/Turn binding direction: **ACCEPTED**;
- direct real parent CLI direction: **ACCEPTED**;
- unified child-result schema direction: **ACCEPTED**;
- real ALLOW authority: **NOT ACCEPTED**;
- real Turn-4 interrupt proof: **NOT ACCEPTED**;
- real post-delete oracle: **NOT ACCEPTED**;
- real isolation/watchdog execution safety: **NOT ACCEPTED**;
- P7.C13 preparation overall: **REWORK_REQUIRED**.

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
