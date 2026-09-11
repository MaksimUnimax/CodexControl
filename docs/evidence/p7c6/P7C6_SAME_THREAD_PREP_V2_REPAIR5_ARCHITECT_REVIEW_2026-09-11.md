# P7.C6 same-thread prep-v2 Repair-5 architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE / REAL CONTINUATION NOT AUTHORIZED**

Reviewed candidate: `01994403110f19e323dffd693f226b18bdcb73c7`.

## Scope verification

The candidate is one commit ahead of the architect base and changes only:

- `tests/real/test_p7_c6_same_thread_continuation.py`
- `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR5_EVIDENCE_2026-09-11.md`

No production `src/**` change is present.

## Accepted Repair-5 work

Independent readback confirms that Repair-5 closes the two defects frozen by Repair-5:

1. real watchdog authority is separated from synthetic watchdog authority;
2. named real internal wait authorities are summed into a conservative `REAL_INTERNAL_WORST_CASE_SECONDS` and the real watchdog deadline dominates that value plus margin;
3. real mode cannot accidentally use the five-second synthetic watchdog authority;
4. `/root/.codexcontrol/p7c6-same-thread-continuation-process-result.json` is an exclusive root-only process-result authority;
5. child PASS result uses an exact finite schema and is written only after `_run_real_continuation()` returns through its full PASS gates;
6. parent re-reads the result with bounded/no-follow identity checks and revalidates exact source SHA/tree, retained-thread hash, delete/app status, residual/scan/limit gates and dynamic effect counts;
7. a pre-existing result file blocks a new real launch;
8. Repair-3 authorities remain present: no new thread path, structural approval matcher, exact sentinel equality, baseline scan identity atomicity, post-delete unrelated authority, actual delete observation, no-retry DELETE_UNKNOWN semantics, success-only sanitization and all-owned-task success gate.

## Remaining blocker — watchdog owns only the Python child, not the continuation process tree

The Repair-5 launcher currently uses ordinary `subprocess.Popen(...)` and on watchdog expiry calls `child.terminate()` / `child.kill()` on that one Python process.

Production `CodexRuntimeManager` starts `codex app-server` through ordinary `asyncio.create_subprocess_exec(...)` without `start_new_session=True`, a dedicated process group or parent-death signal authority.

Therefore the acceptance watchdog has not proved that killing the Python continuation child also terminates its spawned Codex app-server and any command descendants. A watchdog timeout could return finitely while continuation-owned descendants survive/reparent and continue real effects.

This is a harness/process-ownership defect, not a production lifecycle defect.

## Required correction

The real/synthetic dedicated continuation child must be launched in a dedicated OS session/process group owned by the watchdog. On timeout, the parent must terminate/kill that exact isolated process group rather than only the Python PID. Synthetic tests must include at least one descendant/grandchild and prove the whole group is gone after watchdog completion.

The correction must not kill unrelated Codex processes sharing `/root/.codex_second`.

No production `src/**` change is authorized or required.

`P7C6_REPAIR5=REWORK_REQUIRED`

`P7C6_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

P8/P9 remain blocked.
