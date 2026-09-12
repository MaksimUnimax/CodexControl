# P7.C11 source-backed explicit-escalation DENY-only approval-probe preparation — architect review — 2026-09-12

Status: **REWORK_REQUIRED / ZERO-REAL-EFFECT CANDIDATE RETAINED / REAL P7.C11 NOT AUTHORIZED**

## Reviewed authority

- Architect base: `9642b55729b072461b00f6d9af89145bcc3be090`, tree `3c565e2612f64313985ef1df582e1ed63565d2aa`.
- Candidate: `52d5a4d3a3e716dce32069afbb6b6bdf0fa4a07e`.
- Candidate tree: obtained from the candidate commit and frozen by the subsequent Repair-1 contract.
- Harness blob: `dcc6fa05e551f5514ced8993976caa8a6fa1f606`.
- Evidence blob: `960e59ad468868c8290d12312bff266ab520ba66`.
- Candidate is exactly one commit ahead of the architect base and changes only the P7.C11 harness and P7.C11 prep evidence. No `src/**` change occurred.
- Reported real effects during preparation: zero.

## Accepted parts of the candidate

The source-backed stimulus direction is correct and should be preserved:

- exact upstream release authority is frozen to Codex `rust-v0.144.6`, peeled commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`;
- the harness records the upstream facts that workspace-write permits `$TMPDIR` and `/tmp` by default;
- the candidate uses a fresh external target directly under `/root`, with exact high-entropy filename grammar;
- the target is kept outside `/tmp`, resolved `$TMPDIR`, Turn cwd, run root, repository, persistent Codex home, isolated state root, controller root and `/root/.codexcontrol`;
- the target is absent before future execution and is observed only by exact-path metadata after the run;
- the prompt requests exactly one shell command, exact `touch <target>`, explicit `sandbox_permissions=require_escalated`, no default-sandbox first attempt, no alternative tool/path, no network and no retry;
- the DENY-only operator, no-ALLOW invariant, source/state-root/runtime/journal/process/boundary authorities and one-shot namespace are carried forward;
- synthetic wrong-kind and wrong-identity requests do not consume root-only wire authority;
- request observation still durably precedes DENY response dispatch intent.

These areas are not to be redesigned by Repair-1.

## Blocking defect A — false-positive command-approval success classification

The candidate projects `COMMAND_APPROVAL_OBSERVED_AND_DENIED` when it sees:

- any captured `ApprovalKind.COMMAND_EXECUTION` request;
- any DENY attempt;
- zero ALLOW responses;
- target absent.

That is insufficient.

A `COMMAND_EXECUTION` request with the wrong thread, wrong Turn or wrong cwd is intentionally still DENIED, but it does not create authoritative wire capture. The current classifier can nevertheless call that state `COMMAND_APPROVAL_OBSERVED_AND_DENIED`.

Likewise, a command request unrelated to the exact target may be DENIED and still satisfy the aggregate condition even though the target-reference authority is absent.

This violates the frozen P7.C11 objective: the success class must be bound to the **authoritative exact-identity command request**, not merely to the existence of any command-kind request.

## Blocking defect B — DENY attempt is not the same as confirmed DENY

`FutureProbeBudget` correctly distinguishes:

- `approval_deny_confirmed`;
- `approval_deny_unknown_or_failed`.

But the P7.C11 success projection uses only `approval_deny_attempts > 0`.

Therefore a response that ended `RESPONSE_UNKNOWN` can still be projected as `COMMAND_APPROVAL_OBSERVED_AND_DENIED`.

That is an evidence overclaim. A preferred command-approval success must require a confirmed DENY for the same authoritative command request. `RESPONSE_UNKNOWN` needs a separate finite ambiguity class.

## Blocking defect C — success class is not correlated to root-only wire authority / target reference

The root-only `WireCommandAuthority` is the only accepted first-capture authority proving that an exact thread/Turn/cwd command request was observed. The candidate result exposes `wire_command_sha256` and `sentinel_reference_class`, but the success class does not require them.

Repair-1 must make normal command-approval acceptance impossible unless:

- one authoritative exact-identity COMMAND_EXECUTION capture is established;
- the root-only wire record validates;
- the observed command references the external target;
- the response status for that same authoritative request is `DENIED_CONFIRMED`;
- target remains absent;
- ALLOW remains zero.

`EXACT_ARG_TOKEN` is the preferred exact stimulus authority. A non-exact target reference may be recorded as a separate observational class but must not silently become the preferred exact command-approval success.

## Blocking defect D — child target hash is not independently bound to parent target authority

The child result contains `target_sentinel_path_sha256`, and the parent independently owns the generated external target path and re-observes that exact path after child quiescence.

However the current parent final authority does not explicitly require the child-reported target hash to equal an independently computed parent target hash.

Repair-1 must add an explicit parent-side target binding so a normal final result cannot validate against a child result referring to a different target path. No raw target path may enter Git-visible evidence.

## Required Repair-1 direction

Repair-1 is narrow. Preserve the target, prompt and source-backed explicit-escalation design. Correct only the evidence correlation and final success classification.

At minimum add safe authority sufficient to establish:

- authoritative command capture exists;
- authoritative request ordinal/local sequence is finite and correlatable;
- authoritative request is COMMAND_EXECUTION with exact thread/Turn/cwd identity;
- authoritative command references the exact target;
- DENY result for that same request is `DENIED_CONFIRMED`;
- response unknown/failure for that request cannot be called success;
- parent independently binds child target SHA-256 to the parent-selected exact target;
- parent final command-approval success rejects missing/conflicting/malformed authority.

The existing max-three-DENY safety cap remains. Repair-1 must not weaken behavior for non-authoritative requests: they are still DENY and still consume attempts according to existing accounting.

## Disposition

`P7C11_PREP_CANDIDATE=REWORK_REQUIRED`

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`NEXT=P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1`

P8/P9 remain blocked.
