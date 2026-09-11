# P7.C7 approval-stimulus authority — architect review — 2026-09-11

Status: **ACCEPTED AS NOT ESTABLISHED / FAIL-CLOSED / NEXT = DENY-ONLY PROBE PREPARATION / NO REAL THREAD AUTHORIZED**

## Reviewed authority

- Architect base: `94094d3fd199407572dbccfc0da35b55dc5c974a`, tree `8930b59b61af65ce310f50591e185e567fa0d62d`.
- Evidence lineage: `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` then evidence-count correction `e00392fbff6894e1857eb4c8f1e1937a88ca1e96`.
- Final evidence file: `docs/evidence/p7c7/P7C7_APPROVAL_STIMULUS_AUTHORITY_EVIDENCE_2026-09-11.md`.
- The executor branch is two commits ahead of the architect base but changes only that evidence file. No production `src/**`, real harness, ADR, CURRENT_WORK, ROADMAP, config or deployment content changed.
- Real effects during the slice: zero.

## Accepted findings

The evidence correctly reconstructs the retained Run-1 Turn-3 identity and persisted command in local memory only and matches the previously accepted hashes. It correctly preserves the historical `OTHER / TOKEN_MISMATCH` classification without publishing raw command or path data.

The exact installed upstream release authority is correctly bound to OpenAI Codex tag `rust-v0.144.6`, release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`.

Independent source readback confirms the material projection chain:

1. core approval events carry an internal command vector;
2. app-server non-network approval projection applies `shlex_join(&command)`;
3. that string becomes `CommandExecutionRequestApprovalParams.command`;
4. CodexControl approval normalization exposes that wire string only after a real approval request exists.

Exact-release source also confirms approval routing is conditional. `on-request` and restricted workspace-write state may lead to `NeedsApproval`, but tool-specific approval requirements, cached approvals, guardian/strict auto-review, permission hooks and sandbox/retry routing can alter whether the normal app-server manual approval request is actually emitted.

## Architect decision: grammar is genuinely not established offline

The executor correctly stopped at:

`P7C7_APPROVAL_REQUEST_GRAMMAR=NOT_ESTABLISHED`

The source mapping from an already-existing internal command vector to wire `params.command` is deterministic, but preserved evidence does not establish the future model-generated internal command vector for the proposed natural-language fresh-thread stimulus.

The retained persisted Run-1 custom-tool input is not the same authority as the app-server approval request command. Reusing it as a matcher fixture would repeat the original class of harness error.

Accordingly:

- no strict ALLOW matcher is accepted;
- no real approval response is authorized;
- no fresh P7.C7 thread is authorized from this slice;
- no production defect is established.

This is a successful fail-closed authority result, not a failed investigation.

## Next safe step

The only safe way to obtain the missing wire grammar is an empirical fresh-thread approval probe whose operator can never ALLOW.

Before any such real probe, a separate zero-effect preparation slice must build and test a harness with the following invariant:

- any observed approval request is captured only into root-only recovery authority;
- the operator response is always `DENY` regardless of command grammar;
- zero approval request is also a valid finite probe outcome;
- no command request may be approved by the probe;
- any command that executes without asking approval must be independently bounded to the exact harmless candidate stimulus boundary;
- the probe uses one fresh disposable thread only after later explicit architect authorization;
- no delete is performed by the probe;
- no P7.C6 retained thread is touched;
- no matcher/ALLOW authority is inferred until the probe evidence is independently reviewed.

A DENY-only probe does not need to predict the wire grammar in order to remain safe. Its purpose is observation, not acceptance.

## Current classifications

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_APPROVAL_REQUEST_WIRE_MAPPING=ESTABLISHED`

`P7C7_FUTURE_CONCRETE_WIRE_GRAMMAR=NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
