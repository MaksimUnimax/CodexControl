# P7.C6 same-thread prep-v2 Repair-4 architect review — 2026-09-11

Status: **REWORK_REQUIRED / HARNESS-ONLY / REAL CONTINUATION NOT AUTHORIZED**

Candidate: `a55a765cdfb0d51e956045a238d4ecb5a237a5fe`.

Base: `e7368c68c37ac9499440f3d9d5856496414d0638`.

Independent GitHub compare proves the candidate is one commit ahead and changes only:

- `tests/real/test_p7_c6_same_thread_continuation.py`;
- `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR4_EVIDENCE_2026-09-11.md`.

No production `src/**` change is present.

## Accepted Repair-4 progress

The candidate materially closes the Repair-4 task-lifetime class:

- a dedicated child-process launcher exists;
- the real gated test invokes the dedicated child rather than running the real coroutine in the unittest event loop;
- the launcher creates exactly one child and contains finite wait/terminate/kill stages;
- synthetic stubborn-child fixtures exercise process-level termination;
- Turn-5 start ambiguity is routed through forensic retention and one-dispatch authority;
- Turn-4 approval cancellation nonconvergence has a bounded runtime-shutdown/watchdog path;
- normal success checks all tracked `OwnedTask` entries terminal/nonconverged=false;
- prior exact sentinel, descriptor-safe scans, unrelated-baseline and lifecycle authority gates remain present.

## Blocking defect R4-A — real watchdog is five seconds

The harness defines:

`WATCHDOG_HARD_DEADLINE = 5.0`

and the real acceptance test calls:

`launch_dedicated_continuation_child(mode="real")`

without overriding the watchdog bounds.

The child real flow contains multiple legitimate bounded operations with individual waits up to 90, 120 and 180 seconds, plus finite convergence/shutdown bounds. A five-second parent deadline therefore cannot serve as the real one-shot watchdog. It creates a deterministic or near-deterministic false-stop authority that would terminate a healthy continuation before its frozen workflow can complete.

This is an acceptance-harness defect, not a production lifecycle defect.

## Blocking defect R4-B — process PASS lacks structured lifecycle result authority

`_run_real_continuation()` returns a sanitized result dictionary containing safe source/status/counter evidence. The dedicated child runner currently discards that returned value. The parent real acceptance test receives only:

- `PROCESS_COMPLETED`;
- process return code;
- watchdog metadata.

A successful child exit does imply that the inner coroutine returned, but the final acceptance artifact should bind process PASS to the actual sanitized lifecycle statuses/counters rather than only `exit 0`. Repair-5 must add one bounded safe child-to-parent result channel and validate the expected final statuses/counters before declaring real process PASS.

Raw thread IDs, marker plaintext, prompts, commands, credentials and root-only recovery contents remain forbidden in that channel.

## Verdict

`P7C6_REPAIR4=REWORK_REQUIRED`

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

The next slice is the narrow zero-real-effect Repair-5 defined by `P7C6_SAME_THREAD_PREP_V2_REPAIR5_CONTRACT_2026-09-11.md`.
