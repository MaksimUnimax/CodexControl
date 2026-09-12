# P7.C11 one-shot real explicit-escalation DENY-only approval probe — preliminary architect review — 2026-09-12

Status: **REAL PROBE CONSUMED / NO RERUN / REPORTED NORMAL FINALIZATION / COMMAND APPROVAL ROUTE ESTABLISHED / PREFERRED EXACT-TARGET CLASS NOT ESTABLISHED / DURABLE EVIDENCE + WIRE FORENSIC REQUIRED**

## Frozen executable authority

The separately authorized one-shot P7.C11 execution authority was:

- HEAD `be98542b9bcbf99508784f229057698d85784367`;
- tree `ec6433f02f9293273979fd5dfc3f3eff70f16fa4`;
- harness blob `fc67299d80c3d617280975182c097a92cb863b92`.

The execution contract was published before the run at:

`docs/evidence/p7c11/P7C11_ONE_SHOT_REAL_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_EXECUTION_CONTRACT_2026-09-12.md`

P7.C11 has now been started exactly once and is permanently consumed. No rerun is authorized under any outcome.

## User-reported durable authority

The post-run report states:

- `REAL_COMMAND_RC=0`;
- `PARENT_EXECUTION_CLASS=PARENT_FINAL_RESULT_CONFIRMED`;
- `WATCHDOG_STATUS=PROCESS_COMPLETED`;
- child completed; child result present and valid;
- state-root provision and validation confirmed;
- runtime acquire confirmed;
- parent boundary `BOUNDARY_ONLY_EXPECTED_MUTATION`, drift none;
- process group quiescent, no TERM/KILL, one child, zero retry;
- normal result status `OBSERVATION_ONLY`;
- request count 1;
- command approval request count 1;
- DENY attempts 1, confirmed 1, unknown/failed 0;
- ALLOW 0;
- authoritative command capture established;
- authoritative kind `command_execution`;
- authoritative thread/Turn/cwd identity all true;
- authoritative DENY status `DENIED_CONFIRMED`;
- vector reconstruction established, length 3;
- target class `OUTSIDE_DEFAULT_WORKSPACE_WRITABLE_ROOTS`;
- external target absent;
- parent/child target-reference SHA authority matches;
- runtime shutdown confirmed;
- observer owners terminalized; no owner nonconvergence.

Reported global authority hashes:

- latch SHA-256 `247512f8f842c0005a7348d052f7c6794c0664ff06c083fe14171d4ee347205d`;
- result SHA-256 `363b4685856257f13219123cbb6fdd92aeb670c41504e4034124f9f87c8870b8`;
- parent outcome SHA-256 `a92ea3c3ae53a2ee86f902e4927ea2995bdf31c0f9a4bab54f58366932f3dcac`.

These hashes and safe fields still require independent retained-state readback before final architect acceptance.

## What P7.C11 already establishes, subject to readback

The reported observation materially establishes the approval route itself:

- one real `COMMAND_EXECUTION` approval request was observed;
- the request was correlated to the immutable root-only wire authority;
- exact thread/Turn/cwd identity matched;
- the response for that same authoritative request was durably `DENIED_CONFIRMED`;
- ALLOW remained zero;
- the external target remained absent;
- the process/evidence path finalized normally.

Therefore the result is not a failed approval stimulus. The source-backed `RequireEscalated -> ExecApproval -> DENY` route was reached.

## Why the preferred class was not emitted

The accepted Repair-1 contract deliberately required `EXACT_ARG_TOKEN` for the preferred class `COMMAND_APPROVAL_OBSERVED_AND_DENIED`.

The real observation instead reports:

`AUTHORITATIVE_COMMAND_TARGET_REFERENCE_CLASS=EMBEDDED_OCCURRENCE`

with:

`WIRE_VECTOR_RECONSTRUCTION_CLASS=ESTABLISHED`

and:

`WIRE_VECTOR_LENGTH=3`.

This is a finite non-success classification under the frozen contract, not by itself a production failure.

The most plausible source-compatible explanation is a shell-wrapper outer vector where the exact touch operation is carried inside one shell-script argv token. That explanation is NOT yet architect authority and must be established from the retained root-only wire record without another real Codex operation.

## Next required slice

Perform a zero-real-effect retained-wire forensic on the already-consumed P7.C11 run.

The forensic must determine whether the canonical 3-token wire vector is structurally equivalent to:

- a recognized shell executable token;
- an exact shell execution option such as `-lc`;
- one script token that is exactly `touch <the exact external target>` and contains no extra command, redirect, pipe, expansion or retry.

The raw wire command and raw target path remain root-only and may never be published.

If and only if the retained wire proves that exact shell-wrapper semantic shape, the architect may classify the `EMBEDDED_OCCURRENCE` as an outer-wrapper representation of an exact inner target argument and may separately authorize matcher construction. No new real approval probe is needed merely to change the representation class.

## Disposition

`P7C11_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO_CONSUMED`

`P7C11_APPROVAL_ROUTE_REPORTED_ESTABLISHED=YES`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`NEXT=P7C11_CONSUMED_REAL_RETAINED_WIRE_ZERO_EFFECT_FORENSIC`

P8/P9 remain blocked pending architect-accepted hard-delete acceptance.
