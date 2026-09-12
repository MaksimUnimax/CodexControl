# P7.C14 launcher recovery preparation — architect review — 2026-09-12

Status: **REWORK_REQUIRED / ONE SUCCESSOR-EXECUTOR INTERFACE BLOCKER / ZERO REAL EFFECT**

## Candidate reviewed

- final candidate commit: `33f27a2ecba5f81d20651e6456bd2e137a4f5274`;
- final tree: `04c0733eabea2763731bf99c765fc16fd95fec31`;
- base: `e4e57156532cf7f124e104867c29c8573b968e87`;
- P7.C14 launcher blob: `c2b9643e92206f194abdfd35ad08de3783801afe`;
- package marker blobs: `080243830be797f87d23b459dbfd12c142a9d49a` and `23d73d7648ed14ef6857ee665784b87f57fde9f3`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Lineage and file scope are accepted: two linear commits from the consumed P7.C13 evidence head and only the two package markers, P7.C14 launcher and P7.C14 preparation evidence changed.

## Accepted preparation material

The launcher/import recovery itself is accepted:

- deterministic future import roots are `/root/CodexControl/src:/root/CodexControl`;
- repository `tests` and `tests.real` are now tracked packages;
- `codex_control`, P7.C12 and P7.C13 import smokes succeed under the future import authority;
- P7.C14 uses a distinct gate and `/root/.codexcontrol/p7c14-one-shot.json`;
- P7.C13 retry remains forbidden;
- gate-disabled P7.C14 parent smoke is zero effect;
- wrong-authority cases block before executor selection;
- inherited P7.C13 harness/matcher remain immutable.

## Sole blocker

`P7C14PreparedFutureRealExecutor` inherits `p7c13.PreparedFutureRealExecutor.run()` but `P7C14ArchitectContract` is not interface-compatible with the inherited method.

The inherited P7.C13 `run(contract=...)` reads:

- `contract.expected_head`;
- `contract.expected_tree`;
- `contract.expected_harness_blob`.

The P7.C14 contract defines:

- `expected_head`;
- `expected_tree`;
- `expected_launcher_blob`;
- `expected_p7c13_harness_blob`;
- no `expected_harness_blob`.

The production P7.C14 entrypoint therefore selects `P7C14PreparedFutureRealExecutor.production(selected_contract)` and then calls `selected.run(contract=selected_contract)`. With the current source, the inherited method will raise `AttributeError` when it evaluates `contract.expected_harness_blob`.

This occurs before `ledger.reserve()` in the inherited method, so the identified defect does not itself consume P7.C14. Nevertheless, a real P7.C14 execution is guaranteed to fail before child execution and therefore cannot be authorized.

## Why existing tests did not catch it

The focused suite verifies:

- gate-disabled parent import;
- wrong-authority rejection using an injected mock executor;
- P7.C14 production constructor/ledger path;
- temporary ledger semantics.

It does **not** execute the successful P7.C14 source gate followed by the real P7.C14 executor contract handoff using temporary/synthetic effects. Consequently the successor-to-inherited-executor interface was never exercised.

The preparation evidence statement `P7C14_PREP_READY=YES` is therefore not architect-accepted yet.

## Required Repair-1

Repair-1 is narrow:

1. add an explicit, deterministic adaptation from `P7C14ArchitectContract` to the frozen inherited P7.C13 executor contract interface, or equivalently override the P7.C14 executor `run()` boundary;
2. keep P7.C14 source-gate authority separate: launcher/package/import blobs remain checked by P7.C14 before executor selection;
3. inherited child boot authority must continue to bind the P7.C14 HEAD/tree and the accepted P7.C13 harness blob;
4. do not mutate P7.C13 source;
5. add a full zero-effect synthetic **authorized** parent handoff test that passes the P7.C14 gate, enters the P7.C14 executor, reserves only a temporary P7.C14 ledger, builds a temporary boot/result authority and uses a fake watchdog/child result; this test must prove the exact contract adaptation does not raise and never references the P7.C13 global ledger;
6. add explicit negative tests proving wrong inherited harness mapping fails before temporary child dispatch;
7. re-run gate-disabled exact module smoke after the repair.

No real token, Codex process, real ledger, child, RPC, approval, interrupt or delete is authorized.

## Verdict

`P7C14_PREP_IMPORT_AUTHORITY=ACCEPTED`

`P7C14_PREP_PACKAGE_AUTHORITY=ACCEPTED`

`P7C14_PREP_DISTINCT_GATE_LEDGER=ACCEPTED`

`P7C14_PREP_GATE_DISABLED_SMOKE=ACCEPTED`

`P7C14_PREP_SUCCESSOR_EXECUTOR_HANDOFF=REWORK_REQUIRED`

`P7C14_PREP_ARCHITECT_ACCEPTED=NO`

`P7C14_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
