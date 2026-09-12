# P7.C13 final hard-delete acceptance preparation architect review — 2026-09-12

Status: **REWORK_REQUIRED / ZERO-EFFECT OFFLINE MODEL PARTIALLY ACCEPTED / FUTURE REAL HARNESS NOT YET PREPARED**

## Reviewed candidate

- candidate commit: `8fa749856c678cb1ae120f7802c6c553c1272e34`;
- parent/base: `a5c66a778800d1c5ee5811d97d961fe0dccd677c`;
- candidate tree: `264a62710979173112e385293e4959b37f92a842`;
- harness blob: `a6962a14ffd4c10d6e4ff072cd24622077f839c2`;
- evidence blob: `a91fe2d2737729b7bfd02b80bd853e62fe00c03f`.

The base-to-head diff is one linear commit and changes only:

- `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`.

No `src/**`, historical P7.C6-P7.C12, controller migration, ADR, deployment, Telegram, CURRENT_WORK or ROADMAP mutation is present.

## Accepted preparation work

The candidate correctly preserves zero real effects and the accepted P7.C12 matcher blob. The synthetic schema-v4 `DialogueDeleteService` matrix materially exercises confirmed success, `DELETE_UNKNOWN`, confirmed-pending scan failure and marker-only acceptance failure. The effect-budget constants, shared-home semantics, basic target-boundary model, post-delete target-marker/thread oracle, and ordinary real-gate-disabled behavior are useful preparation evidence.

The accepted P7.C12 matcher remains unmodified.

## Blocking defect A — no future real executor exists behind the gate

The frozen P7.C13 contract requires preparation of the exact harness that a later architect-owned one-shot execution contract can authorize without another implementation pass.

The candidate does not contain that executable future-real path. `future_real_entrypoint()` checks the supplied contract/environment and then, even when the gate succeeds, unconditionally raises:

`P7C13_REAL_EXECUTOR_REQUIRES_SEPARATE_AUTHORIZED_SLICE`

Therefore the candidate is an offline behavioral model, not the final gated real acceptance harness.

The same defect affects the required installed/runtime proof, fresh run materialization, actual `CodexRuntimeManager` generation acquisition, model catalog selection, fresh thread/start, generation restart/resume, real Turn orchestration, live approval bridge, live interrupt, pre/post real storage measurement, real production delete chain, durable root-only recovery ledger and real evidence/result materialization: none is reachable behind the future gate because no future executor is implemented.

P7.C13 cannot be architect accepted while a later real run would require modifying the harness source after this review.

## Blocking defect B — parent/child watchdog and one-shot recovery are only in-memory models

The contract requires a prepared dedicated parent/child real executor pattern with:

- exactly one child;
- dedicated OS session/process group;
- bounded watchdog;
- parent signalling only its exact owned group on timeout;
- no retry/second child;
- valid child result and quiescent group required for PASS;
- a root-only durable one-shot/recovery ledger reserved before the first real thread effect.

The candidate provides only `watchdog_classify()` and an in-memory `OneShotLatch` dataclass. It does not prepare the actual future process/session/group spawn, owned-group identity proof, bounded TERM/KILL path, child-result file schema/validator, exclusive root-only durable latch/recovery write/read, or crash/restart consumed-run semantics.

This does not satisfy the binding preparation contract.

## Blocking defect C — Turn-3 ALLOW authority is not independently bound to the owned live run

`approval_candidate()` accepts a caller-supplied `target`, `CapturedRequest`, `ExpectedAuthority` and `CorrelatedWireRecord`, but it does not prove that:

- the matched thread hash equals the independently owned P7.C13 thread;
- the matched Turn hash equals the actual active Turn-3 ID;
- the matched cwd hash equals the actual run-owned cwd;
- local sequence equals the live approval bridge sequence for that exact request;
- `expected.target` and wire target equal the independently selected run-owned approval target argument;
- the target absence/existence checks refer to that exact selected path rather than caller-supplied booleans.

A self-consistent request/expected/wire tuple for the wrong owned thread/Turn/cwd/target could therefore satisfy the pure P7.C12 matcher in the current offline model.

The frozen contract requires exact owned thread/Turn/cwd identity plus exact selected run-owned target before ALLOW is eligible.

## Blocking defect D — Turn identities are not modeled as distinct authoritative turns

`OfflineFutureFlow.binding` contains a fixed `turn_id="turn-1"` and is reused by Turn 4. `turn4_interrupt()` accepts only `binding == self.binding`, so the preparation does not represent a distinct actual Turn-4 binding/ID.

The contract requires one exact Turn-3 approval binding and a separate exact active Turn-4 binding for the interrupt. Turn 4 must not inherit or reuse the Turn-1/Turn-3 turn ID.

## Blocking defect E — Turn-1/Turn-2 persistence proof is not substantive

`turn2_remembers(expected_marker)` returns success when the supplied marker is merely non-empty and Turn 2 is marked completed. It does not compare an observed Turn-2 result against the exact Turn-1 memory marker, nor does it preserve separate memory/response marker authorities.

The frozen contract requires a real same-thread persisted-context proof across an owned app-server generation restart.

## Blocking defect F — pre-delete persistent oracle misses path-name residual authority

`BoundedTargetOracle` counts target thread/marker bytes only from regular-file contents. It does not inspect safe relative session filename/directory components for exact target-thread bytes.

The binding P7.C5/P7.C6 hard-delete oracle treats exact target-thread residuals in session content, filename and directory structure as blockers. A future real C13 acceptance must not falsely pass if content is clean but a target-owned session filename/directory remains.

Repair may implement this as a bounded no-follow safe relative-name scan without publishing raw names.

## Additional acceptance gap — unrelated target-specific persistent removal

The frozen post-delete PASS matrix requires no target-specific evidence that unrelated persistent material was removed. `post_delete_acceptance()` has no input/gate for this condition.

Shared-home global stability is not required, but the harness must prepare a bounded target-specific safe baseline/oracle and fail if it can positively attribute unrelated removal to the P7.C13 run.

## Evidence correction required

Because the future real executor, durable one-shot/watchdog, owned Turn-3/Turn-4 authority and substantive persistence proof are not yet present, the current evidence overstates:

- `P7C13_PREP_HARNESS_READY=YES`;
- `P7C13_PREP_APPROVAL_MATCHER_GATE=PASS` as an owned-live-run gate;
- `P7C13_PREP_INTERRUPT_GATE=PASS` as an exact distinct Turn-4 gate;
- `P7C13_PREP_ONE_SHOT_GATE=PASS` as durable/process-level one-shot authority.

The synthetic delete-chain and offline oracle tests remain useful and should be preserved rather than redesigned.

## Verdict

- lineage/scope: **PASS**;
- zero-real-effect boundary: **PASS**;
- synthetic production delete-chain matrix: **PASS / PRESERVE**;
- accepted P7.C12 matcher use: **PASS / PRESERVE**;
- final future-real harness executable path: **NOT PREPARED**;
- durable one-shot/process watchdog: **NOT PREPARED**;
- independently owned Turn-3 approval binding: **NOT ESTABLISHED**;
- distinct Turn-4 binding/interrupt authority: **NOT ESTABLISHED**;
- substantive Turn-1/Turn-2 persistence proof: **NOT ESTABLISHED**;
- complete pre/post residual oracle: **NOT ESTABLISHED**;
- P7.C13 preparation overall: **REWORK_REQUIRED**.

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked.
