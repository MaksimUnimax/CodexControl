# P7.C7 consumed real DENY-only approval probe forensic — architect review — 2026-09-11

Status: **ARCHITECT ACCEPTED WITH CORRECTION / P7.C7 CONSUMED / NO RERUN / PRODUCTION DEFECT NOT ESTABLISHED**

## Reviewed authority

- Forensic base: `4b650ed5b43be62acf8aad86d790a817cf72854c`, tree `91f3f2dbda94021245ab534fe7bfe738e4617a22`.
- Forensic evidence commit: `e589eec3c215d192df48a8e252e74dc13c768327`.
- Evidence blob: `563c9c6398b542ba27644175fa40b125ce824351`.
- Consumed execution source: `320ae3ba1265608a92ebfe82992068d4b12ebcd9`, tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.

The forensic branch is exactly one commit ahead of the frozen base and adds only the sanitized forensic evidence file.

## Accepted durable findings

The authoritative retained run was uniquely established. The root-only journal contains five valid records with no parse/schema errors:

1. `SOURCE_GATE=PASS`
2. `GLOBAL_LATCH_RESERVED=YES`
3. `RUNTIME_ACQUIRE_INTENT`
4. `RUNTIME_ACQUIRE_RESULT=NONCONVERGED`
5. `BOUNDARY_PROOF_RESULT=DEFERRED_TO_PARENT`

No later probe stage was durably recorded.

The retained physical/offline evidence is consistent with an early runtime-acquire failure:

- no wire-command authority;
- empty workdir;
- sentinel absent;
- isolated sqlite/log roots present but with zero descendants;
- no correlated persistent session;
- no fresh thread hash;
- no fresh Turn;
- no current users of the retained parent/run/controller/workdir/isolated roots.

Parent outcome still establishes one child, zero retries, clean process-group convergence, no TERM/KILL, and `CHILD_NONZERO`.

## Final P7.C7 forensic classification

`JOURNAL_LAST_DURABLE_MILESTONE=RUNTIME_ACQUIRE_RESULT`

`JOURNAL_LAST_DURABLE_RESULT=NONCONVERGED`

The frozen stage enum contains no `RUNTIME_ACQUIRE_FAILED` value. Because runtime acquisition was not confirmed, the latest directly supported positive stage remains:

`LAST_DURABLY_ESTABLISHED_STAGE=RUNTIME_ACQUIRE_INTENT`

`FAILURE_CLASS=RUNTIME_ACQUIRE_FAILURE`

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

## Root cause remains unproved

The exact cause of `manager.acquire()` failure is **not established** by retained evidence.

The accepted P7.C7 helper `_finite_await(...)` maps both timeout and arbitrary exception to a generic `(False, value)` shape. The caller then records only `RUNTIME_ACQUIRE_RESULT=NONCONVERGED`, discarding whether the cause was:

- outer timeout;
- `RuntimeErrorSafe` / isolation/precondition failure;
- capability/version failure;
- another startup exception.

Therefore:

`P7C7_RUNTIME_ACQUIRE_ROOT_CAUSE=NOT_ESTABLISHED`

## Architect-established harness defect

A harness-observability/time-budget defect is independently established from accepted source even though the specific real trigger remains unknown.

P7.C7 used:

`PROBE_RUNTIME_ACQUIRE_TIMEOUT=5.0`

around the complete `CodexRuntimeManager.acquire()` operation.

Production runtime has its own app-server initialize timeout of 15 seconds. Runtime acquisition also performs the installed-version authority probe before app-server initialization. The version probe has separate 3-second spawn, 3-second output and 3-second wait bounds. Thus the P7.C7 outer 5-second runtime-acquire horizon does not dominate even the named bounded startup stages inside the production runtime path.

Separately, `_finite_await(...)` collapses timeout and exception into the same caller result and the P7.C7 journal records only `NONCONVERGED`, preventing exact post-mortem classification.

These are test-harness defects. They do not establish a defect in production runtime code.

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

## Governance correction

The executor forensic evidence states that the architect review and forensic contract filenames were absent from base `4b650ed5b43be62acf8aad86d790a817cf72854c`.

That statement is false. Independent GitHub readback at the exact base confirms both files exist:

- `docs/evidence/p7c7/P7C7_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-11.md`
- `docs/evidence/p7c7/P7C7_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_CONTRACT_2026-09-11.md`

This is a forensic-report governance/readback defect, not a runtime finding. The sanitized runtime evidence above remains usable and is architect-reconciled here.

## P7.C7 closure

P7.C7 remains permanently consumed.

No P7.C7 retry, second thread, second Turn, approval response, resume, interrupt, delete, read/list or cleanup is authorized.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## Successor

The next lane is a new P7.C8 successor, not a P7.C7 retry.

P7.C8 must first prepare a zero-real-effect fresh probe harness with:

- entirely new one-shot latch/result/outcome namespace;
- a runtime-acquire horizon that exceeds the named bounded version/initialize stages with explicit margin;
- distinct durable acquisition outcomes for confirmed, timeout, categorized safe exception and cancellation/nonconvergence;
- preservation of `RuntimeErrorSafe.category` where safe instead of collapsing all errors into `NONCONVERGED`;
- the already accepted DENY-only, one-child, no-retry, exact-process-group, immutable-journal, measured-outcome and `1/1/1` normal result authorities.

No P7.C8 real execution is authorized by this review.

P8/P9 remain blocked.
