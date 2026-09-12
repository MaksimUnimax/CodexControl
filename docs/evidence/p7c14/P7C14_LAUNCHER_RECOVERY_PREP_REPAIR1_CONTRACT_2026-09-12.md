# P7.C14 launcher recovery preparation Repair-1 contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / SUCCESSOR-EXECUTOR INTERFACE REPAIR / NO REAL EXECUTION**

## Exact base

Repair-1 starts from exact candidate:

- commit `33f27a2ecba5f81d20651e6456bd2e137a4f5274`;
- tree `04c0733eabea2763731bf99c765fc16fd95fec31`;
- launcher blob `c2b9643e92206f194abdfd35ad08de3783801afe`;
- preparation evidence blob `7e2ad8d0266fe9fbbb8c9f5d5079c0d6b512c8f5`.

Binding review:

`docs/evidence/p7c14/P7C14_LAUNCHER_RECOVERY_PREP_ARCHITECT_REVIEW_2026-09-12.md`

## Scope

Repair only the P7.C14 contract -> inherited P7.C13 executor handoff and the missing exact-authorized synthetic proof.

Do not redesign import/package recovery, P7.C13 hard-delete implementation, approval/delete semantics or P7.C14 replay policy.

## Zero-real-effect boundary

All real effects remain zero:

- Codex/app-server starts `0`;
- model/thread/Turn RPCs `0`;
- approval responses/ALLOW/DENY `0`;
- interrupt/delete `0`;
- P7.C13 ledger mutations `0`;
- P7.C14 real ledger creation `0`;
- Telegram/process signals `0`.

Do not create or set any real P7.C14 authorization token.

## Required interface adaptation

The P7.C14 source gate remains authoritative for:

- P7.C14 authorization token;
- HEAD/tree;
- P7.C14 launcher blob;
- inherited P7.C13 harness blob;
- P7.C12 matcher blob;
- package marker blobs;
- import-root authority;
- tracked source/index clean state.

After that gate passes, adapt `P7C14ArchitectContract` to the frozen inherited executor input explicitly.

Preferred implementation:

- override `P7C14PreparedFutureRealExecutor.run(*, contract: P7C14ArchitectContract | None)`;
- require a non-null valid P7.C14 contract;
- construct a `p7c13.FutureArchitectContract` whose:
  - authorization token is the P7.C14 token only as an inert inherited field;
  - expected head = P7.C14 expected head;
  - expected tree = P7.C14 expected tree;
  - expected harness blob = P7.C14 `expected_p7c13_harness_blob`;
- call `super().run(contract=<adapted inherited contract>)` exactly once.

Equivalent explicit adaptation is allowed only if it is equally narrow and preserves all frozen source/harness authority.

Do not weaken the P7.C14 source gate by aliasing the P7.C14 launcher blob to the inherited harness blob.

## Boot/result authority expectations

After adaptation, inherited P7.C13 child authority must use:

- source HEAD = exact P7.C14 execution HEAD;
- source TREE = exact P7.C14 execution tree;
- harness blob = accepted inherited P7.C13 harness blob;
- ledger path = `/root/.codexcontrol/p7c14-one-shot.json`;
- deterministic child import authority = `/root/CodexControl/src:/root/CodexControl`.

The P7.C14 launcher blob remains a parent source-gate fact and is not substituted for the inherited child harness blob.

## Mandatory exact-authorized synthetic handoff proof

Add an offline test that exercises the successful path missing from the initial preparation.

It must:

1. create an exact synthetic `P7C14ArchitectContract`;
2. pass the full P7.C14 source-bundle gate;
3. construct a P7.C14 executor using **temporary** ledger/boot/result paths and a fake watchdog/child authority;
4. call `p7c14_real_entrypoint(...)` with that executor and contract;
5. prove the P7.C14 -> inherited contract adaptation succeeds without `AttributeError` or missing contract fields;
6. prove the temporary ledger is the only ledger reserved;
7. prove P7.C13 global ledger calls/mutations = `0`;
8. prove child dispatch is fake/harmless and Codex calls = `0`;
9. prove the boot record binds synthetic P7.C14 head/tree and inherited P7.C13 harness blob;
10. prove a valid synthetic child result can be accepted by the inherited parent result authority.

The test must actually traverse `P7C14PreparedFutureRealExecutor.run()`. A mock executor at `p7c14_real_entrypoint()` is insufficient.

## Negative matrix additions

At minimum test:

- missing P7.C14 contract at executor run => fail before temp ledger;
- wrong P7.C13 harness mapping => fail before child dispatch;
- P7.C14 launcher blob mismatch remains source-gate failure before executor;
- P7.C14 ledger and P7.C13 ledger remain distinct;
- adapted inherited contract never carries P7.C14 launcher blob as `expected_harness_blob`.

## Gate-disabled smoke

Re-run the exact P7.C14 module shape with all P7.C14 real authorization variables unset under deterministic `PYTHONPATH`.

It must still:

- import successfully;
- exit finite disabled code;
- create no P7.C14 real ledger;
- touch no P7.C13 authority;
- start no Codex/app-server process.

## Allowed tracked changes

Allowed:

- `tests/real/test_p7_c14_final_hard_delete_recovery.py`;
- `docs/evidence/p7c14/P7C14_LAUNCHER_RECOVERY_PREP_EVIDENCE_2026-09-12.md`.

Package markers may remain unchanged but must not be rewritten without necessity.

Forbidden:

- `src/**`;
- P7.C13 harness;
- P7.C12 matcher;
- P7.C6-P7.C13 historical evidence/source;
- migrations/deployment/Telegram/P8/P9.

## Validation

Run:

- focused P7.C14 Repair-1;
- P7.C13 offline suite only;
- P7.C12 focused suite;
- relevant C2-C5 fake/non-real regressions;
- complete non-real pytest with real gates unset;
- unittest discovery with real gates unset;
- compileall;
- `git diff --check`;
- leakage/security scan;
- exact changed-path scope check.

Historical consumed-latch failures remain immutable and are reported separately.

## Evidence

Update the existing P7.C14 preparation evidence.

Record:

`P7C14_REPAIR1_BASE_HEAD=33f27a2ecba5f81d20651e6456bd2e137a4f5274`

`P7C14_REPAIR1_BASE_TREE=04c0733eabea2763731bf99c765fc16fd95fec31`

`PRIOR_P7C14_LAUNCHER_BLOB=c2b9643e92206f194abdfd35ad08de3783801afe`

and final launcher/evidence blobs plus exact-authorized synthetic handoff facts.

Required final lines:

`P7C14_REPAIR1_CONTRACT_ADAPTATION=PASS|FAIL`

`P7C14_REPAIR1_EXACT_AUTHORIZED_SYNTHETIC_HANDOFF=PASS|FAIL`

`P7C14_REPAIR1_TEMP_LEDGER_ONLY=PASS|FAIL`

`P7C14_REPAIR1_INHERITED_BOOT_BINDING=PASS|FAIL`

`P7C14_REPAIR1_GATE_DISABLED_SMOKE=PASS|FAIL`

`P7C14_PREP_READY=YES|NO`

`P7C14_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Publish only to:

`prep-p7-c14-launcher-recovery-repair1-2026-09-12`

No force, no rebase, no main mutation by executor.

After remote readback STOP. Independent architect acceptance is required before any real P7.C14 token or execution contract exists.
