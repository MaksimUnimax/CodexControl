# P7.C8 DENY-only approval-probe preparation — architect review — 2026-09-11

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL P7.C8 PROBE NOT AUTHORIZED**

## Reviewed candidate

- Candidate commit: `9297395efb678356255d91aa8d90001a5fc768e0`.
- Candidate tree: `291fddbbef8a67dc918a730d363c086cbb910db3`.
- Architect base: `9d3fcc959794f6c7f5461b5d7d60dc55bc2658df`, tree `f271545b08a0a3be41d346a00d0242c368f81057`.
- Candidate is exactly one commit ahead of the architect base.
- Changed scope is limited to `tests/real/test_p7_c8_deny_only_approval_probe.py` plus the P7.C8 prep evidence file; no `src/**` change occurred.
- Reported preparation effects are zero and the future real method remains gated/disabled.

## Useful improvements accepted as candidate work

The candidate correctly creates a new P7.C8 namespace rather than reusing P7.C7 and carries forward the DENY-only/process/journal/result architecture. In particular it introduces a dedicated runtime-acquire observer, separates `TIMEOUT`, `SAFE_EXCEPTION`, `UNEXPECTED_EXCEPTION`, and `CANCELLATION_NONCONVERGENT`, uses a 45-second acquire ceiling instead of P7.C7's 5-second wrapper, introduces bounded failed-acquire cleanup authority, keeps the 100-second observation window, and moves the parent watchdog to 205 seconds.

The P7.C7 one-shot probe remains permanently consumed and is not reusable.

## Blocking defects

### A. Failed-acquire cleanup contains an unbounded post-cancel wait

On cleanup timeout the candidate performs:

`cleanup_task.cancel()` followed by an unbounded `await asyncio.gather(cleanup_task, return_exceptions=True)`.

A cancellation-resistant `shutdown_profile()` task can therefore outlive the nominal 12-second cleanup authority and hold the child until the outer process watchdog terminates it. This violates the frozen requirement that failed-acquire containment itself be finite and explicitly classified.

Repair requirement: after cleanup timeout, cancellation/join must have its own finite bound. If the cleanup task still does not terminalize, persist `NONCONVERGENT` and return/raise without an unbounded await. The parent process-group watchdog remains the final process owner.

### B. Real child discards the post-containment acquisition classification

`RuntimeAcquireObserver.contain()` may escalate an original timeout/safe/unexpected acquisition result to `RUNTIME_ACQUIRE_CANCELLATION_NONCONVERGENT` when the acquire owner does not terminalize or cleanup is nonconvergent.

The real child currently calls `await acquire_observer.contain(...)` and discards the returned `AcquireObservation`. The durable `RUNTIME_ACQUIRE_RESULT` was already written before containment and is never corrected/finalized.

Repair requirement: retain the containment result and persist a separate immutable final acquisition classification after cleanup, e.g. `RUNTIME_ACQUIRE_FINAL_RESULT`. The parent must use this final authority, not infer it from the pre-containment result.

### C. Parent acquisition authority defaults missing evidence to `CONFIRMED`

`run_future_real_probe_parent().acquisition_authority()` currently returns `RUNTIME_ACQUIRE_CONFIRMED` when no child run is discoverable and also defaults a missing/invalid `RUNTIME_ACQUIRE_RESULT` record to `CONFIRMED`.

That is optimistic evidence fabrication. Missing or unreadable acquisition evidence can never establish successful acquisition.

Repair requirement: introduce a fail-closed parent-only `RUNTIME_ACQUIRE_NOT_ESTABLISHED` class (or equivalent explicit finite unknown authority). Missing run, unreadable journal, missing acquire result, duplicate/conflicting result, or missing final acquisition classification must resolve to `NOT_ESTABLISHED`, never `CONFIRMED`.

### D. Cleanup safe-category persistence call is not compatible with `RecoveryJournal.result()`

`RecoveryJournal.result()` accepts `attempt` and `request_count`, but the cleanup path calls it with `category=cleanup_category` for a `RuntimeErrorSafe` cleanup failure. That raises `TypeError` exactly on the safe categorized cleanup path and prevents its required durable result.

Repair requirement: use a separate sanitized journal event such as `RUNTIME_ACQUIRE_CLEANUP_ERROR_CATEGORY`, or explicitly extend and test the journal API. Raw exception text remains forbidden.

### E. Safe RuntimeError category authority is incomplete

The candidate finite `SAFE_RUNTIME_CATEGORIES` contains only:

- `capability_mismatch`;
- `storage_boundary_invalid`;
- `initialize_timeout`;
- `executable_invalid`.

The production runtime can emit other safe `RuntimeErrorSafe.category` values on acquire/start/containment paths, including `manager_shutting_down`, `unknown_profile`, `profile_reserved`, `profile_stopping`, `unresolved_process`, `process_streams_missing`, `initialize_failed`, `startup_failed`, and `kill_reap_timeout` where ownership cleanup fails.

The observer classifies any `RuntimeErrorSafe` as `SAFE_EXCEPTION`, but the parent projection currently drops categories outside its four-value set to `None`. That recreates the diagnostic loss P7.C8 was designed to remove.

Repair requirement: freeze a complete finite allowlist of production runtime categories reachable from `CodexRuntimeManager.acquire/_start/shutdown_profile` for this harness, validate strict token grammar, and preserve the exact allowed category. Unknown categories must not be published as raw text; classify them with a fixed safe class such as `SAFE_EXCEPTION_CATEGORY_UNRECOGNIZED` while retaining no raw message.

### F. Parent reads acquisition journal through a non-authoritative convenience reader

The parent acquisition projection uses `read_journal_records()`, which calls ordinary `Path.read_text()` and does not apply the retained journal's no-follow/bounded/stable-identity authority.

Repair requirement: parent acquisition fact recovery must use a bounded `O_NOFOLLOW` stable-identity JSONL reader and validate the accepted journal schema before treating records as durable authority. A read/identity/schema failure resolves to `RUNTIME_ACQUIRE_NOT_ESTABLISHED`.

## Disposition

No production defect is established by these findings. They are P7.C8 test-harness / durable-evidence authority defects.

`P7C8_DENY_ONLY_APPROVAL_PROBE_PREP=REWORK_REQUIRED`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

Next slice is **P7.C8 DENY-only approval-probe prep Repair-1**, zero real effect only.

P8/P9 remain blocked.