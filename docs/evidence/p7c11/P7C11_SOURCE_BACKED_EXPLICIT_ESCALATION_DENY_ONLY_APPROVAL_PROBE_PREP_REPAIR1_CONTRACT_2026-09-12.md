# P7.C11 source-backed explicit-escalation DENY-only approval-probe preparation Repair-1 contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / REPAIR ONLY / REAL EXECUTION NOT AUTHORIZED**

## Purpose

Repair only the false-positive acceptance/evidence-correlation defects found in candidate `52d5a4d3a3e716dce32069afbb6b6bdf0fa4a07e`.

Do not redesign the source-backed P7.C11 target or prompt. Do not modify production code.

## Exact reviewed candidate

- reviewed candidate: `52d5a4d3a3e716dce32069afbb6b6bdf0fa4a07e`;
- candidate harness blob: `dcc6fa05e551f5514ced8993976caa8a6fa1f606`;
- candidate evidence blob: `960e59ad468868c8290d12312bff266ab520ba66`.

The Repair-1 branch must start from the architect governance head published after this review, not from the old candidate branch.

## Preserve unchanged

Repair-1 must preserve:

- exact upstream release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`;
- target filename grammar and direct `/root` location;
- exact target exclusions from `/tmp`, `$TMPDIR`, cwd, run root, repository, persistent Codex home, isolated state, controller and `/root/.codexcontrol`;
- target absent before future real execution;
- exact candidate operation `touch <external-target>`;
- explicit first-and-only shell tool call instruction;
- explicit `sandbox_permissions=require_escalated` instruction;
- no default-sandbox first attempt, patch, Python, network, alternate path/command or retry;
- production state-root provision/validate authority;
- state-root worker ownership;
- runtime acquire/failed-acquire containment;
- P7.C10 schema-aware RecoveryJournal and durable Turn authority;
- DENY-only operator and ALLOW=0;
- maximum three DENY attempts;
- immutable first-capture root-only wire authority;
- exact normal model/list=1, thread/start=1, turn/start=1;
- resume/interrupt/delete/read/list=0;
- one child, zero retry and process-group authority;
- child/parent/boundary/source gates.

## Repair A — authoritative command-capture projection

Introduce explicit sanitized authority for the command request that consumed the root-only wire capture.

The authority must be derived from the validated `wire-command-recovery.json` record and the in-memory `ApprovalCapture` sequence, never guessed from aggregate counters.

At minimum project safe fields equivalent to:

- `authoritative_command_capture_established: bool`;
- `authoritative_command_request_ordinal: int | null`;
- `authoritative_command_local_sequence: int | null`;
- `authoritative_command_kind: COMMAND_EXECUTION | null`;
- `authoritative_command_thread_match: bool | null`;
- `authoritative_command_turn_match: bool | null`;
- `authoritative_command_cwd_match: bool | null`;
- `authoritative_command_target_reference_class`;
- `authoritative_command_wire_sha256`.

No raw thread/Turn/cwd/command/target path may be added.

The authoritative capture is established only if exactly one capture matches the root-only wire record's local request sequence and that capture is:

- `ApprovalKind.COMMAND_EXECUTION`;
- exact thread match;
- exact Turn match;
- exact cwd match;
- bounded and schema-valid.

Missing, duplicate or conflicting correlation fails closed.

## Repair B — correlate DENY result to the authoritative request

Aggregate DENY counters are insufficient.

Persist a safe correlation between each DENY response event and the observed request ordinal it answers.

Preferred approach:

- when `counted_response()` receives an `InboundServerRequest`, resolve exactly one prior `ApprovalCapture` using the request's local sequence/owned identity;
- include that safe `request_count` ordinal in `DENY_RESPONSE_N_DISPATCH_INTENT` and `DENY_RESPONSE_N_RESULT` journal records;
- existing `attempt` remains the response-attempt ordinal;
- authoritative journal reader validates bounded `request_count`.

Then derive exactly one authoritative command DENY status:

- `DENIED_CONFIRMED`;
- `RESPONSE_UNKNOWN`;
- `NOT_ESTABLISHED`.

A confirmed DENY for a different request does not satisfy the authoritative command request.

## Repair C — narrow command-approval success class

`COMMAND_APPROVAL_OBSERVED_AND_DENIED` may be emitted only when all of the following hold:

1. external target is absent;
2. authoritative command capture is established;
3. authoritative capture kind is COMMAND_EXECUTION;
4. exact thread/Turn/cwd identity is proven for that capture;
5. validated root-only wire authority exists;
6. wire vector reconstruction is established;
7. target reference for the authoritative command is `EXACT_ARG_TOKEN` for the preferred exact stimulus;
8. the DENY status for that same authoritative request is `DENIED_CONFIRMED`;
9. ALLOW count is zero;
10. owners are terminalized and no owner nonconvergence exists.

Do not classify success from merely:

- `command_approval_request_count > 0`;
- `approval_deny_attempts > 0`;
- aggregate DENY counters.

## Repair D — finite non-success classes

Add finite safe classes sufficient to avoid overclaiming, including equivalents of:

- `EXPLICIT_ESCALATION_STIMULUS_NOT_ESTABLISHED` for zero request;
- `COMMAND_APPROVAL_OBSERVED_WITHOUT_AUTHORITATIVE_CAPTURE`;
- `COMMAND_APPROVAL_AUTHORITATIVE_DENY_STATUS_UNKNOWN`;
- `COMMAND_APPROVAL_AUTHORITATIVE_TARGET_REFERENCE_NONEXACT`;
- `NONCOMMAND_APPROVAL_OBSERVED_DENIED` where useful;
- existing target-created failure class.

These are observational classes only. They do not authorize matcher or hard delete.

## Repair E — exact-target parent binding

The parent chooses the exact external target before launching the child and re-observes the same path after child quiescence.

Normal parent final authority must independently bind the child's reported target hash to the parent-selected target.

Add parent-side safe authority equivalent to:

- `parent_target_sentinel_path_sha256` independently computed from the parent-held raw path;
- require equality with child `target_sentinel_path_sha256`;
- require both hashes valid lowercase SHA-256;
- require parent exact-path observation confirms target absent for command-approval success.

Do not store the raw target path in the final result or Git evidence.

A hash mismatch must fail parent final authority.

## Repair F — child/result outcome-specific validation

`validate_sanitized_result()` / `validate_child_result()` must enforce outcome-specific consistency.

For `COMMAND_APPROVAL_OBSERVED_AND_DENIED`, require at minimum:

- authoritative capture established;
- authoritative command wire SHA-256 present and valid;
- exact identity fields true;
- authoritative target reference `EXACT_ARG_TOKEN`;
- authoritative DENY status `DENIED_CONFIRMED`;
- `approval_deny_confirmed >= 1`;
- `approval_deny_unknown_or_failed` does not stand in for the authoritative DENY;
- target absent;
- ALLOW zero.

For the response-unknown class require authoritative DENY status `RESPONSE_UNKNOWN` and forbid preferred success.

For zero-request class require request count zero, no wire authority and target absent.

For target-created failure require target present and forbid command-approval success.

## Repair G — parent final command-approval validation

Normal parent final result may still be a valid **observational** result for zero-request or other finite empirical outcomes.

But any final result claiming `COMMAND_APPROVAL_OBSERVED_AND_DENIED` must independently satisfy all Repair-C/F facts plus exact parent target binding.

Do not make PARENT_FINAL_RESULT_CONFIRMED synonymous with command-approval success. Keep those concepts separate:

- process/evidence finalization can succeed for a finite non-success empirical outcome;
- command-approval stimulus acceptance requires the narrow success class.

## Repair H — durable journal chronology for authoritative request

For the preferred exact command approval, require a durable sequence equivalent to:

- `APPROVAL_REQUEST_k_OBSERVED` for the authoritative request ordinal `k`;
- `DENY_RESPONSE_n_DISPATCH_INTENT` with `request_count=k`;
- `DENY_RESPONSE_n_RESULT=DENIED_CONFIRMED` with `request_count=k`.

Require strict order:

`APPROVAL_REQUEST_k_OBSERVED < DENY_RESPONSE_n_DISPATCH_INTENT < DENY_RESPONSE_n_RESULT`.

A different request's confirmed DENY cannot satisfy this chronology.

## Required synthetic matrix

Add tests proving:

1. one exact command request + exact target reference + confirmed DENY => `COMMAND_APPROVAL_OBSERVED_AND_DENIED`;
2. wrong-thread command + confirmed DENY => not success;
3. wrong-Turn command + confirmed DENY => not success;
4. wrong-cwd command + confirmed DENY => not success;
5. exact command unrelated to target + confirmed DENY => not success;
6. exact command with target only embedded/non-exact => not preferred exact success;
7. exact command + `RESPONSE_UNKNOWN` => not success, finite ambiguity class;
8. non-command approval + confirmed DENY => not command success;
9. wrong request first, exact request later, both DENIED => authoritative exact request is correctly correlated without requiring all captures to have exact identity;
10. first exact wire capture remains immutable with later requests;
11. authoritative request ordinal/local sequence malformed or ambiguous => fail closed;
12. DENY journal `request_count` missing/duplicate/conflicting => fail closed for command success;
13. parent-selected target SHA mismatch with child target SHA => parent final failure;
14. parent exact target present => parent command-success failure;
15. zero-request terminal-first remains a valid finite observational final result but not command approval success.

## Real method remains disabled

During Repair-1:

- P7.C11 auth env unset;
- exactly one future real P7.C11 test skipped;
- zero real Codex/app-server/thread/Turn/approval effects;
- zero actual `/root` target creation.

## Change scope

Allowed:

- `tests/real/test_p7_c11_deny_only_approval_probe.py`;
- optional P7.C11-only test helpers;
- `docs/evidence/p7c11/P7C11_SOURCE_BACKED_EXPLICIT_ESCALATION_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_EVIDENCE_2026-09-12.md`.

Forbidden:

- `src/**`;
- P7.C7–P7.C10 harnesses/evidence;
- CURRENT_WORK/ROADMAP/DECISIONS;
- ADR/config/deployment.

If production changes appear necessary, stop with `P7C11_REPAIR1_PRODUCTION_CHANGE_REQUIRED`.

## Acceptance target

Repair-1 may be architect accepted only if:

- zero real effects;
- source-backed target/prompt are unchanged in semantics;
- false-positive command-success routes are eliminated;
- authoritative exact request and its DENY result are correlated durably;
- parent binds child target hash to its own target authority;
- all carried-forward P7.C10/P7.C11 safety gates remain passing;
- explicit/focused/full tests pass with exactly one future real P7.C11 test skipped.

No real P7.C11 execution is authorized by this contract.

`P7C11_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C11_REAL_EXECUTION_AUTHORIZED=NO`

`P7C11_MATCHER_AUTHORIZED=NO`

`P7C11_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
