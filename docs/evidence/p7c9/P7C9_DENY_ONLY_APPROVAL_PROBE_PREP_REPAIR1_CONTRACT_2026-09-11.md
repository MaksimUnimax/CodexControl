# P7.C9 DENY-only approval-probe prep Repair-1 contract — 2026-09-11

Status: **FROZEN / ZERO REAL EFFECT / REAL EXECUTION FORBIDDEN**

## Scope

Repair only the two architect-reviewed P7.C9 preparation defects. Preserve the production-provisioned state-root design and every accepted P7.C8/P7.C9 DENY/process/journal/result invariant.

Allowed repository changes:

- `tests/real/test_p7_c9_deny_only_approval_probe.py`;
- optional P7.C9-only offline helpers under `tests/**`;
- `docs/evidence/p7c9/P7C9_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_EVIDENCE_2026-09-11.md`.

No `src/**`, ADR, config, deployment, P7.C7 or P7.C8 harness/evidence changes are authorized.

## Repair A — validator fact separation

`validate_parent_execution_outcome()` must use distinct immutable local names for:

- runtime acquire error category;
- runtime acquire cleanup category;
- state-root provision category;
- state-root validate category.

No category variable may be reused across authority domains.

For `runtime_acquire_result=RUNTIME_ACQUIRE_NOT_ESTABLISHED`, require exactly:

- `runtime_acquire_initial_result is None`;
- `runtime_acquire_error_category is None`;
- `runtime_acquire_cleanup_result is None`;
- `runtime_acquire_cleanup_error_category is None`.

State-root categories must not influence that check.

Add negative tests proving each forbidden runtime-acquire field independently causes rejection even when both state-root categories are null.

Normal `PARENT_FINAL_RESULT_CONFIRMED` must continue to require provision/validate and runtime acquisition all confirmed with all error/cleanup categories null.

## Repair B — bounded state-root worker ownership

The provision/validate timeout seam must expose worker ownership truthfully.

Freeze a finite owner join bound, suggested:

`P7C9_STATE_ROOT_WORKER_JOIN_SECONDS=1.0`.

Each state-root operation must return an observation containing at least:

- operation result;
- safe error category or null;
- worker terminalized boolean.

Required behavior:

- completion before the 5s combined provision+validate deadline -> terminalized true;
- deadline exceeded -> perform at most one bounded worker join observation;
- if worker becomes terminal within the owner-join bound, retain `TIMEOUT` and `worker_terminalized=true`;
- if worker remains alive after the join bound, classify the operation as finite nonconvergence authority and `worker_terminalized=false`;
- no validation step may start after a provision worker timeout/nonconvergence;
- no runtime acquisition may start unless both provision and validate are confirmed and both workers terminalized;
- no normal child result may be published while either state-root worker is nonterminal;
- the dedicated parent child-process watchdog remains final process owner; no second probe/process/thread retry is authorized.

The worker may remain daemon-owned until the failed child exits, but durable evidence must never call such a state `CONFIRMED` or an ordinary converged timeout.

Introduce a narrow state-root nonconvergence class or a separate owner-terminalization field. Parent recovery must reconstruct it fail-closed.

## State-root parent authority

Parent state-root reconstruction must require exact journal chronology and explicit ownership facts. Missing, unreadable, duplicate, conflicting, unsafe or owner-ambiguous evidence becomes `NOT_ESTABLISHED`, never `CONFIRMED`.

A normal parent result/outcome requires:

- provision result `CONFIRMED`;
- provision worker terminalized `true`;
- validate result `CONFIRMED`;
- validate worker terminalized `true`;
- no provision/validate error category.

## Preserve production provisioning

Future real path remains:

source/source-tree gate -> process-group gate -> fresh run skeleton -> journal -> global latch -> production `IsolatedStateRoot.provision(profile)` -> production `IsolatedStateRoot.validate(profile)` -> runtime acquire.

The harness must not manually create the isolated state root, marker, `sqlite/`, or `logs/`.

## Preserve acquisition and approval authority

Unchanged:

- runtime acquire 45s;
- failed-acquire cleanup 12s;
- acquire cleanup cancel/join 1s;
- initial/final acquisition classes and `NOT_ESTABLISHED` parent recovery;
- DENY only, ALLOW=0;
- at most three DENY attempts and no fourth response;
- exact Turn authority before dequeue;
- exact thread/Turn/cwd wire capture;
- normal lifecycle model/list=1, thread/start=1, turn/start=1;
- resume/interrupt/delete/read/list=0;
- immutable recovery-journal inode and no recreation;
- one child/no retry/exact process-group signaling;
- 30s stimulus and 100s observation;
- separate child result, parent final result and parent execution outcome.

## Time budget

Recalculate all path budgets after adding the state-root owner-join bound. The parent hard watchdog must be strictly greater than every internal path plus the frozen 15s watchdog margin. Do not shorten existing stage ceilings merely to preserve the old watchdog value.

## Required offline tests

At minimum:

1. runtime-acquire `NOT_ESTABLISHED` rejects non-null acquire error category with state-root categories null;
2. same for cleanup result and cleanup category;
3. state-root category checks remain independent;
4. provision completes normally -> confirmed/terminalized;
5. validate completes normally -> confirmed/terminalized;
6. provision exceeds deadline but terminalizes within owner join -> timeout/terminalized, validate not started, acquire count 0;
7. provision ignores owner join -> nonconvergent/nonterminal, validate not started, acquire count 0;
8. validate exceeds deadline but terminalizes within owner join -> timeout/terminalized, acquire count 0;
9. validate ignores owner join -> nonconvergent/nonterminal, acquire count 0;
10. normal result validator rejects either worker terminalized=false;
11. parent recovery maps missing/duplicate/conflicting ownership authority to NOT_ESTABLISHED;
12. production provision/validate layout tests remain passing;
13. all P7.C8 acquisition authority tests remain passing;
14. DENY/process/journal/boundary/1-1-1 tests remain passing;
15. exactly one future real P7.C9 unittest remains skipped with all auth vars unset.

## Zero-effect rule

During Repair-1:

- no Codex or app-server start;
- no model/list, thread/start, turn/start or approval response;
- no resume/interrupt/delete/read/list;
- no real P7.C9 latch/result/outcome creation;
- no P7.C7/P7.C8 rerun or state mutation.

## Disposition target

Only after independent architect review may Repair-1 be accepted and an exact P7.C9 executable SHA/tree be frozen for a separate one-shot real authorization.

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`
