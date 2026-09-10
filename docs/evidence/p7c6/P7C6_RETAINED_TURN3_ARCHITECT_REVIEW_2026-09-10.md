# P7.C6 retained Turn-3 architect review — 2026-09-10

Status: **FORENSIC_ACCEPTED / SAME-THREAD CONTINUATION PREPARATION AUTHORIZED / REAL CONTINUATION NOT YET AUTHORIZED**

Repository: `MaksimUnimax/CodexControl`.

## Reviewed lineage

- prior architect main: `f2de26426bc09423745357c55fc69b5f2c08791f`;
- prior tree: `48c22ee6fd400bbb5adc7676dc5641feb428dd39`;
- retained-Turn-3 forensic commit: `e6835e7eaff21ce6a452c24f3309269df67c82ba`;
- Run-1 evidence commit: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

The forensic commit is exactly one evidence-only commit above the frozen architect base and adds only `docs/evidence/p7c6/P7C6_RETAINED_TURN3_FORENSIC_EVIDENCE_2026-09-10.md`. It performed zero real Codex effects.

## Accepted retained state

The forensic established exactly one retained root-only recovery ledger, mode `0600`, with the target thread SHA-256 matching Run 1. Exactly one target session artifact was found with zero scan/parse errors.

Run-1 Turn 3 is identified exactly. Its durable terminal is persisted as `INTERRUPTED`. The terminal was not produced by the zero-effect forensic.

No approval request/decision/response record remains structurally persisted for Turn 3. The published Run-1 `C6_APPROVAL_HANDLING_RESULT=RESPONSE_UNKNOWN` remains authoritative and is not reinterpreted.

One Turn-3 command item is persisted and is terminal `COMPLETED`. No run-owned delayed process remains, the run-owned sentinel is absent, and the retained isolated/controller boundaries have no external users.

Therefore:

`RETAINED_TURN3_STATE=TERMINAL_SAFE_FOR_ARCHITECT_REVIEW` is accepted.

## Old approval is permanently closed

The forensic classifies the persisted Turn-3 command against the historical accepted safe grammar as `OTHER` with `TOKEN_MISMATCH`.

This does not prove what exact Run-1 wire approval decision was sent because the live approval result remains `RESPONSE_UNKNOWN`. It does prove that the retained Turn-3 command is not eligible for retroactive acceptance under the historical safe grammar.

The old Turn-3 approval request must never be answered, resent, retried, reconstructed as an ALLOW, or used as authority for a new response.

## Same-thread continuation eligibility

Because the exact retained turn is durably terminal, no command/approval state is pending, no delayed process remains, and the sentinel is absent, a **new turn on the same retained thread** may be considered without retrying any old effect.

This does not authorize a new real thread. Run 1 already consumed the one-new-thread budget.

The only permissible future real continuation, if separately authorized after harness preparation review, is a same-thread recovery continuation using the retained thread identity and retained run-owned isolated/controller boundaries.

## Additional Run-1 harness defect — marker recovery durability

Independent architect review of the published Run-1 harness found that its failure-path `_ledger(...)` rewrite retains the raw thread ID but does not retain the generated Run-1 synthetic marker values. The Run-1 evidence prose states that marker values were retained in the recovery ledger, but the published failure-path code does not do so.

The final C6 hard-delete acceptance still requires a zero-residual oracle for all known Run-1 target markers. Therefore no real continuation/delete may be authorized until a zero-effect preparation step reconstructs the exact Run-1 synthetic markers from the exact target session artifact and stores them only in a root-owned `0600` recovery supplement outside Git.

Required unique marker families are:

- `C6_RESPONSE_<48 lowercase hex>`;
- `C6_MEMORY_<48 lowercase hex>`;
- `C6_INTERRUPT_<48 lowercase hex>`.

The preparation must recover exactly one unique value for each family from the exact target artifact. Git evidence stores only SHA-256 values and counts, never marker plaintext.

If this reconstruction is not exact, final marker-erasure proof is impossible and same-thread real continuation remains blocked.

## One-shot correction requirement

Run-1 architect review already established that the declared host-level `ONE_SHOT_LEDGER` was checked but never materialized by the Run-1 harness.

Before any future real continuation, preparation must create a root-owned `0600` host-level Run-1 consumed latch at the originally declared path, without raw thread/marker content, so the historical Run-1 harness cannot accidentally execute again.

A separate continuation-specific durable latch must be implemented and tested before any future `thread/resume`. It must be created atomically before the first continuation business RPC and retained on every post-dispatch failure so the continuation itself cannot be blindly repeated.

## Continuation proof shape to prepare

The preparation harness must support, but must **not yet execute**, the following future same-thread sequence:

1. reuse the exact retained Run-1 thread, shared authenticated `CODEX_HOME`, retained isolated state root and retained synthetic controller DB boundary;
2. one fresh model catalog validation and one exact `thread/resume` of the retained binding;
3. one new approval-proof turn using a new run-owned marker/sentinel and the historical structural matcher with exact thread, exact new turn, exact cwd, exact marker, exact sentinel, exactly one `COMMAND_EXECUTION` request and grammar only `EXACT_INNER` or `ONE_SHELL_WRAPPER`;
4. wait for that approval turn to complete and prove exact sentinel content, then remove only the run-owned sentinel;
5. one new interrupt-proof turn, with no approval response authorized for that turn; prove the turn remains active before sending exactly one P1.8 interrupt and require `CONFIRMED|RECONCILED` plus definitive `FAILED` terminal;
6. shutdown/reap only continuation-owned runtime children;
7. pre-delete physical proof using exact target thread plus all recovered Run-1 markers and all new continuation markers;
8. create/use schema-v4 synthetic controller binding for the retained thread;
9. exactly one still-unused official `thread/delete` through `DialogueDeleteService` and accepted C4 local cleanup;
10. post-delete oracle requires zero exact target thread and zero all-known-marker residual across shared persistent sessions/history and the retained isolated state/log root, with zero scan errors and zero isolated payload descendants.

The separate future real continuation may extend the historical Run-1 turn count by at most two new turns. It may authorize at most one **new, distinct** approval response for the new approval-proof turn. This is not a retry of the Run-1 `RESPONSE_UNKNOWN` request.

No second approval response is authorized for the interrupt-proof turn. If such a request appears, it is not answered; any continuation contract must fail/interrupt safely without granting it.

## Current authority

Real continuation remains blocked pending preparation-harness review:

`P7C6_REAL_CONTINUATION_AUTHORIZED=NO`

Authorized now:

`P7C6_SAME_THREAD_CONTINUATION_PREP_AUTHORIZED=YES`

The preparation performs zero Codex business RPCs and may change only gated test/evidence plus root-only recovery/latch metadata explicitly described in the preparation contract.

P7.C6 remains **NOT ACCEPTED**. P8/P9 remain blocked.
