# P7.C12 Repair-1 architect review — 2026-09-12

Status: **REWORK_REQUIRED / MATCHER GRAMMAR ACCEPTED / ONE RESIDUAL AUTHORITY GAP**

## Reviewed candidate

- Repair-1 commit: `a2281b3839c4dcb7f85218e95034510c25c80956`.
- Parent: `4d57b95650c972d26baa33c51f80a85a70b17564`.
- Matcher blob: `e3a94659dd6765f5d6fe5d35aa6b5e65172720f1`.
- Evidence blob: `2cb374cdbf1a463b931e9629b35f3f7fbe3ffdf3`.
- Repair diff changes only the P7.C12 matcher test and P7.C12 evidence.

## Accepted Repair-1 corrections

Repair-1 successfully removes the synthetic free-form `correlation_key` authority. The strict command grammar remains fail-closed and unchanged in substance: exact `COMMAND_EXECUTION`, exact `/bin/bash`, exact `-lc`, canonical three-token outer vector, literal two-token `touch <target>` inner command, exact command SHA, one target occurrence, and rejection of alternate/compound/wrapper/redirect/expansion/retry representations.

The retained projection now independently requires the RecoveryJournal request record, journal-to-wire command SHA equality, exact identity-match flags, one DENY intent followed by one `DENIED_CONFIRMED`, and wire/child/parent target SHA equality. The 16-case independent-authority corruption matrix materially covers those gates.

## Residual blocker

`project_retained_authority()` still derives `local_sequence` only from the root-only wire record (`local_request_sequence`) and then copies that same value into `CapturedRequest`, `ExpectedAuthority`, and `CorrelatedWireRecord`.

That does not independently establish the claimed `LOCAL_SEQUENCE` correlation field.

The accepted P7.C11 sanitized child result already contains independently materialized and schema-validated authority for:

- `authoritative_command_capture_established`;
- `authoritative_command_request_ordinal`;
- `authoritative_command_local_sequence`;
- `authoritative_command_kind`;
- `authoritative_command_thread_match`;
- `authoritative_command_turn_match`;
- `authoritative_command_cwd_match`;
- `authoritative_command_wire_sha256`;
- `authoritative_command_deny_status`.

Repair-2 must bind these child-result facts to the journal and wire before constructing matcher inputs. In particular, child `authoritative_command_local_sequence` must equal wire `local_request_sequence`; child ordinal/kind/wire SHA and identity flags must agree with the journal/wire authority; child DENY status must be `DENIED_CONFIRMED`.

No command-matcher redesign is required.

## Verdict

- strict matcher grammar: **ACCEPTED**;
- Repair-1 journal→wire SHA gate: **ACCEPTED**;
- Repair-1 DENY chronology: **ACCEPTED**;
- Repair-1 wire/child/parent target binding: **ACCEPTED**;
- independent local-sequence/capture binding: **NOT YET ESTABLISHED**;
- P7.C12 overall: **REWORK_REQUIRED**.

`P7C12_REAL_EXECUTION_AUTHORIZED=NO`

`P7C12_REAL_ALLOW_AUTHORIZED=NO`

`P7C12_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.