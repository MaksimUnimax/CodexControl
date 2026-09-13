# P7.C15 hard-delete successor preparation Repair-3 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / REAL HARD-DELETE SEMANTICS ACCEPTED / ONE-SHOT CONTAINMENT MICRO-REPAIR REQUIRED / ZERO REAL EFFECT**

## Candidate reviewed

- candidate HEAD: `84b901f7af208ecde240b0ba0ed13188376b4104`;
- candidate tree reported/verified on branch: `094?` is historical; final Repair-3 remote authority is the exact branch HEAD above and launcher blob below;
- Repair-3 base: `52e20e42e451955ba0d417a47d89903cadf142f2`;
- Repair-3 base tree: `03c555267442b8ce6df5255e08152c2cd112908c`;
- launcher blob: `5e964d9408413b968b03e334759037f906174ffd`;
- evidence blob: `2cc14317db626d58d62189cc2669c9a7c78cb07d`.

Lineage/scope are accepted: the candidate is two linear commits ahead of the frozen Repair-2 base, and only the P7.C15 launcher and preparation evidence changed. No `src/**`, P7.C12/P7.C13/P7.C14 source, package marker, migration, deployment, Telegram, P8 or P9 path changed.

## Architect-accepted Repair-3 material

Repair-3 closes the previously frozen production-hardening defects and this material is accepted for reuse:

- production approval no longer depends on fake-only `response_calls` or `pending_approval_count`;
- one production-surface `next_server_request()` observer protects against a second Turn-3 server request without sending a second response;
- fresh Turn-1 memory/response markers and exact Turn-1/Turn-2 message proof are restored;
- selected default model/reasoning authority is keyed to the authenticated catalog and survives generation rebound without a second model/list;
- child installs private `umask(0o077)` before runtime creation and restores it in `finally`;
- Turn-3 target remains root-owned regular `0600`, nlink 1, non-symlink;
- production uses inherited real watchdog grace constants rather than the Repair-2 five-second offline watchdog values;
- production stages use bounded owned waits;
- fixed production clocks were removed;
- pre-delete markers include current-run memory/response/target/Turn-3/Turn-4 material;
- persistent and isolated post-delete observations are separated;
- unrelated-removal fact is derived from before/after metadata authority;
- isolation authority and post-delete schema v4 are revalidated;
- child keeps parent-owned process-group facts unknown;
- parent PASS requires exact positive/forbidden effect counts, child runtime quiescence, one child, zero retry and clean watchdog group facts;
- actual Turn3/approval/Turn4/controller/canonical delete/official observation/post-delete semantics from Repair-2 remain intact.

## Remaining blocker A — filesystem mutation before durable one-shot reservation

`P7C15PreparedFutureExecutor._production_with_authority()` currently creates the run-specific state/work parent directories with `mkdir(...)` before `P7C15DurableOneShotLedger.reserve()` is called in `_run_production()`.

Therefore an authorized parent invocation can mutate run-local filesystem authority before the durable replay barrier exists. If construction fails after one parent directory is created but before ledger reservation, the command has produced a current-run mutation without a durable consumed record. This recreates the class of pre-ledger ambiguity that P7.C15 is intended to eliminate.

Required correction: production construction may compute random run/path strings before reserve, but must not create any run-specific directory/file. The exact P7.C15 ledger must be reserved first; only after successful reservation may the private state/work parents and boot/result authorities be materialized. Any failure after reserve remains permanently consumed.

## Remaining blocker B — inherited watchdog hard deadline is smaller than the actual P7.C15 internal timeout plan

Repair-3 correctly removed fixed `5.0 / 0.2 / 0.2` production watchdog bounds, but production now uses `p7c13.REAL_WATCHDOG_HARD_DEADLINE` (`sum(unique REAL_STAGE_TIMEOUTS)+margin`).

P7.C15 invokes several timeout buckets more than once sequentially: Turn-1 start and terminal, Turn-2 start and terminal, Turn-3 start/approval/request-observer convergence, multiple controller operations, final shutdown/tombstone/live/schema/close, and Turn-4 active/interrupt/join windows. Consequently the sum of the actual P7.C15 allowed internal waits is materially greater than the inherited 670-second parent deadline.

The current test only proves the inherited deadline is greater than `sum(REAL_STAGE_TIMEOUTS.values())`; it does not prove it exceeds the P7.C15 invocation plan. A correct child could therefore be terminated by the parent watchdog while still inside individually permitted stage deadlines.

Required correction: define a P7.C15-specific hard deadline from a frozen explicit internal timeout invocation plan (including repeated keys and observer/join windows) plus safety margin. Production must use that value. Offline tests may still inject short bounds.

## Remaining blocker C — Turn-3 post-response observer has a post-join request race

`_observe_turn3_request_after_response()` checks `request_task.done()` before the final ownership/join block. A second server request can complete after the last preliminary check but before/during join. In that case `next_server_request()` has already consumed the request, the task may be joined successfully, yet `second_request` can remain false.

This is the same class of post-join fact-loss race previously repaired for Turn 4. A consumed second request must never disappear from the final Turn-3 gate.

Required correction: after both owned tasks have terminalized/joined, classify the final request-task terminal state. Any normal request result at any point before observer ownership ends => second request observed => non-PASS. Harness-owned cancellation without a delivered request is the only no-request cancellation class. Observer exception/ambiguous state => fail closed. Add a deterministic scheduling test for the former late-window race.

## Remaining blocker D — bounded error-path close + retained parent terminal facts

The normal controller close is bounded, but several early controller/schema/binding failure branches still call `await storage.close()` directly. Repair-3 contract required every potentially blocking controller close to be owned and finite. Replace all direct production closes with the same bounded close authority, preferably by one `try/finally` structure.

Also persist safe parent terminal facts in the P7.C15 ledger recovery record. At minimum record watchdog status, owned-group active count, zombie count, group-scan-error count, signal count/class, child status/verdict/runtime-quiescence when available, exact-effect-gate result, child count and retry count. These facts are safe and prevent a future consumed FAIL from requiring reconstruction of parent containment state after the fact.

## Verdict

`P7C15_REPAIR3_REAL_CLIENT_APPROVAL=ACCEPTED`

`P7C15_REPAIR3_MEMORY_REASONING_UMASK=ACCEPTED`

`P7C15_REPAIR3_REAL_HARD_DELETE_CONTINUATION=ACCEPTED`

`P7C15_REPAIR3_POST_DELETE_AUTHORITY=ACCEPTED`

`P7C15_REPAIR3_EXACT_EFFECT_PARENT_GATE=ACCEPTED`

`P7C15_REPAIR3_ONE_SHOT_CONTAINMENT=REWORK_REQUIRED`

`P7C15_PREP_ARCHITECT_ACCEPTED=NO`

`P7C15_REAL_EXECUTION_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
