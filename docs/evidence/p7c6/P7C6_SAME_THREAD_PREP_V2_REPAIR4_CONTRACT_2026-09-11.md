# P7.C6 same-thread prep-v2 Repair-4 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / FINAL HARNESS FAILURE-EDGE REPAIR**

Predecessor: `2b38969c1c9a8232cb1c68efc953dae125e0e18c`.

Binding review: `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR3_ARCHITECT_REVIEW_2026-09-11.md`.

Repair-4 may modify only the gated acceptance harness/tests/evidence. No production `src/**` change is authorized.

## Required corrections

### 1. Process-finite nonconvergence authority

Helper-level finite return is not enough if an asyncio task remains cancellation-resistant and can keep the test event loop alive.

The real continuation must have a **process-level hard wall-clock owner** in addition to coroutine-level bounds.

Required design:

- keep the gated real continuation in the existing test module;
- add an explicit execution entrypoint suitable for a dedicated subprocess;
- real execution is run only in that dedicated child process;
- parent/launcher owns a finite hard deadline plus finite kill grace;
- on hard deadline the child is terminated; no second child/continuation is started because the durable continuation latch has already been consumed;
- root-only journal/latch remain the recovery authority;
- parent returns a finite `PROCESS_WATCHDOG_TIMEOUT` result rather than hanging;
- the launcher must not create any second business operation after watchdog timeout.

Offline/fake tests must prove a child containing a cancellation-resistant task is terminated within the hard bound and the controlling test/process returns finitely.

### 2. Turn-5 start ambiguity retention

Wrap Turn-5 start in an explicit failure/nonconvergence handler.

On any Turn-5 start timeout, nonconvergence, exception or non-CONFIRMED result after dispatch:

- set `forensic_retained = True` before leaving the edge;
- persist finite failure stage;
- boundedly shutdown the owned runtime;
- do not remove workdir/supplement/journal/sentinel recovery authority;
- do not retry Turn-5 start.

Behavioral test: a synthetic nonconverging Turn-5 start leaves forensic paths present and produces zero second start dispatch.

### 3. Turn-4 approval cancellation nonconvergence

Do not swallow `_cancel_owned_approval` nonconvergence.

If Turn-4 start fails and approval bridge cancellation does not converge:

- set forensic retention;
- persist `APPROVAL_BRIDGE_NONCONVERGED`;
- immediately run bounded owned-runtime shutdown;
- allow the process watchdog to be the final authority if the Python task still refuses cancellation;
- no late ALLOW may be emitted after the runtime is shut down;
- no Turn-4 retry.

Behavioral test must use a cancellation-resistant approval task and prove the process-level owner terminates it finitely with zero emitted ALLOW.

## Preserve all Repair-3 successes

Do not weaken source HEAD/tree/clean gate, retained authorities, topology/local-path checks, journal fail-closed semantics, exact sentinel equality, descriptor-safe scanner, baseline identity atomicity, post-delete safe envelope, structural matcher, dynamic budget, unknown-RPC rejection, actual controller proof, no-new-thread path, Turn-5 no-reacquire, official delete observer, DELETE_UNKNOWN no-retry, success-only sanitization, or shared CODEX_HOME semantics.

Repair-4 itself performs zero real Codex/app-server/business RPC effects. All real gates remain unset. The resulting candidate must stop for architect review.

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`
