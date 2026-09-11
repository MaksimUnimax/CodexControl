# P7.C6 same-thread prep-v2 Repair-6 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / FINAL PROCESS-TREE OWNERSHIP REPAIR**

Predecessor candidate: `01994403110f19e323dffd693f226b18bdcb73c7`.

Binding review: `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR5_ARCHITECT_REVIEW_2026-09-11.md`.

Repair-6 is harness/tests/evidence only. No production `src/**` change is authorized.

## Required correction

1. Launch the dedicated continuation Python child in a new OS session/process group (`start_new_session=True` or an equivalently explicit, testable boundary).
2. Before accepting the launch, prove the watchdog child is the process-group/session leader or otherwise has one exact isolated process-group authority.
3. On watchdog timeout, send SIGTERM to the dedicated continuation process group, not only the Python child PID.
4. Wait a finite terminate grace. If the process group remains alive, send SIGKILL to the same process group and wait a finite kill/reap grace.
5. Never signal the caller's process group and never signal unrelated Codex processes using the shared persistent `CODEX_HOME`.
6. Do not start a second child or retry any business operation.
7. Preserve continuation latch/journal/result/recovery evidence exactly as already frozen; watchdog timeout can never be PASS.
8. Synthetic proof must create at least one child descendant/grandchild which would outlive a plain parent-PID kill, then prove no member of the isolated group remains after watchdog completion.
9. Synthetic proof must also establish that an unrelated process outside the dedicated group remains alive and receives no signal.
10. Normal synthetic completion and all Repair-5 watchdog/result-channel tests must continue to pass.
11. The real continuation test remains skipped during Repair-6. All real authorization variables remain unset.

## Acceptance

Repair-6 PASS requires zero real Codex effects, all explicit real-file offline tests passing with exactly one gated real skip, focused regressions passing, full discovery passing, allowed diff only, sanitized evidence and remote readback.

If accepted, the architect may then freeze exact accepted HEAD/tree and issue the one-shot real same-thread continuation authority.

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`
