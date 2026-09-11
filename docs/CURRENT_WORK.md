# Current work authority

Date: 2026-09-11

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 remains binding: persistent authenticated `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 retained-thread history

P7.C6 is permanently consumed and forensic-only.

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

## P7.C7 approval-stimulus authority

Exact upstream `rust-v0.144.6` release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d` proves the internal command-vector -> app-server `shlex_join` mapping, but offline evidence did not establish the future concrete model-generated wire grammar.

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

## P7.C7 DENY-only approval probe

Repair-6 preparation was architect accepted:

- executable commit `320ae3ba1265608a92ebfe82992068d4b12ebcd9`;
- tree `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`;
- harness blob `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.

The one-shot P7.C7 real probe executed exactly once and is permanently consumed. Real evidence commit: `4629cff73d981ee9c2abafa24c97ba7ca340f87c`.

Consumed-probe forensic evidence commit:

`e589eec3c215d192df48a8e252e74dc13c768327`

Forensic evidence establishes:

- unique retained P7.C7 run root;
- global latch present;
- normal result absent;
- parent outcome `CHILD_NONZERO` with clean process-group convergence;
- recovery journal has five valid records;
- `RUNTIME_ACQUIRE_RESULT=NONCONVERGED`;
- no model/list stage recorded;
- no fresh thread or Turn;
- approval path not reached;
- no wire authority;
- workdir empty and sentinel absent;
- production defect not established.

Final factual classifications:

`JOURNAL_LAST_DURABLE_MILESTONE=RUNTIME_ACQUIRE_RESULT`

`JOURNAL_LAST_DURABLE_RESULT=NONCONVERGED`

`LAST_DURABLY_ESTABLISHED_STAGE=RUNTIME_ACQUIRE_INTENT`

`FAILURE_CLASS=RUNTIME_ACQUIRE_FAILURE`

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C7_RUNTIME_ACQUIRE_ROOT_CAUSE=NOT_ESTABLISHED`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

Architect forensic review:

`docs/evidence/p7c7/P7C7_CONSUMED_REAL_DENY_ONLY_APPROVAL_PROBE_FORENSIC_ARCHITECT_REVIEW_2026-09-11.md`

The architect review also establishes a P7.C7 harness defect: the probe used a 5-second outer timeout around the complete runtime acquire path even though production has a 15-second initialize bound and version probing contains separate 3-second spawn/output/wait bounds. The generic helper also collapsed timeout and arbitrary exception into one `NONCONVERGED` durable result, preventing exact root-cause reconstruction.

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

The executor forensic evidence incorrectly stated that the architect review and forensic contract files were absent from base `4b650ed5b43be62acf8aad86d790a817cf72854c`; independent GitHub readback proves both files were present. This is an executor governance/readback defect and does not alter the accepted runtime findings.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## Current executable slice

**P7.C8 DENY-only approval-probe preparation — NEXT / ZERO REAL EFFECT.**

P7.C8 is a new successor, not a retry of P7.C7. It must use a new auth token, fresh profile/run namespace and new global latch/result/outcome paths. The preparation must preserve all accepted P7.C7 DENY-only/process/journal/outcome safety while fixing runtime-acquire observability and timeout authority.

Binding contract:

`docs/evidence/p7c8/P7C8_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-11.md`

Preparation target runtime authority:

- acquire timeout 45s;
- failed-acquire cleanup timeout 12s;
- candidate sleep 30s;
- observation timeout 100s;
- normal internal budget 186s;
- watchdog margin 15s;
- hard watchdog 205s;
- timeout and safe runtime exception must remain distinct durable outcomes;
- `RuntimeErrorSafe.category` may be retained as the safe categorized error authority;
- no P7.C8 real effect is authorized in preparation.

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C8_REAL_EXECUTION_AUTHORIZED=NO`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 acceptance is architect accepted.
