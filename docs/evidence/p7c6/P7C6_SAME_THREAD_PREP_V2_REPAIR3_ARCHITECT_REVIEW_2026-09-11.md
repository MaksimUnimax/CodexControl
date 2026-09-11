# P7.C6 same-thread prep-v2 Repair-3 architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT / NO PRODUCTION DEFECT ESTABLISHED**

Reviewed candidate: `2b38969c1c9a8232cb1c68efc953dae125e0e18c`.

Base: `de398808cfce7d4c42da3d08109e5a166078cd34`, tree `1d5166d53b80a30afe0d4b89651a53648e9702a4`.

Scope review passed: candidate is one commit ahead and changes only the gated continuation harness plus sanitized Repair-3 evidence. No `src/**`, deployment or configuration changes were introduced.

Repair-3 correctly closes the five frozen Repair-3 defects at the helper level:

- bounded primary/secondary/final observations replace unbounded gather/join;
- sibling-task cancellation/ownership is explicitly modeled;
- Turn-4 sentinel proof now requires exact stable bytes;
- unrelated baseline identity is returned from the same descriptor-safe scan;
- post-delete unrelated reconciliation requires the safe regular-file envelope.

The structural matcher, source authority, Run-1 latch/thread authorities, topology/local-path gates, actual controller proof, marker oracle, dynamic budget, unknown-RPC rejection, no-new-thread path, official delete observer and success-only sanitization remain present.

However the candidate is **not yet safe as the one-shot real executable**. Independent review found remaining harness-only failure-edge defects:

1. **Final nonconvergence still leaves a live asyncio task.** `TaskNonconvergedError` is raised finitely, but the underlying task intentionally remains pending. The `OwnedTask` map is local to `_run_real_continuation`; after the coroutine exits there is no durable runtime owner for that Python task. A pending task may continue the already-dispatched operation, and `IsolatedAsyncioTestCase` loop teardown may itself wait indefinitely on a cancellation-resistant task. Repair-3 tests prove only that the helper returns finitely and then manually release the synthetic task; they do not prove the full real-test process terminates finitely with the task still nonconverged.
2. **Turn-5 start nonconvergence does not set `forensic_retained`.** `turn5_task` is awaited directly through `_await_owned_task` without a sibling failure wrapper. If it reaches FINAL_NONCONVERGENCE after successful Turn 4, the outer `finally` sees `forensic_retained == False` and may remove the continuation workdir while the still-live Turn-5 start task can later converge and use that path.
3. **Turn-4 start failure can swallow approval-task nonconvergence.** The start-failure handler catches every exception from `_cancel_owned_approval(... )` and ignores it. If the approval bridge is cancellation-resistant, the harness immediately re-raises the start failure and only later enters generic `finally` shutdown. The frozen safety goal is stronger: a nonterminal approval bridge must force immediate owned-runtime shutdown and a finite process-level terminal outcome so no late ALLOW can be emitted.

These are acceptance-harness defects only. No production `src/**` defect is established or authorized for repair.

`P7C6_CONTINUATION_PREP_V2_REPAIR3=REWORK_REQUIRED`

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

P8/P9 remain blocked.
