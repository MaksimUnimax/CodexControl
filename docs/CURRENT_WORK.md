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

Consumed-probe forensic evidence commit: `e589eec3c215d192df48a8e252e74dc13c768327`.

Accepted factual classifications:

`JOURNAL_LAST_DURABLE_MILESTONE=RUNTIME_ACQUIRE_RESULT`

`JOURNAL_LAST_DURABLE_RESULT=NONCONVERGED`

`LAST_DURABLY_ESTABLISHED_STAGE=RUNTIME_ACQUIRE_INTENT`

`FAILURE_CLASS=RUNTIME_ACQUIRE_FAILURE`

`P7C7_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C7_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C7_RUNTIME_ACQUIRE_ROOT_CAUSE=NOT_ESTABLISHED`

`P7C7_HARNESS_OBSERVABILITY_DEFECT_ESTABLISHED=YES`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

P7.C7 used a 5-second outer acquire timeout around a production startup path containing a 15-second initialize bound plus separate version-probe bounds, and its generic helper collapsed timeout and exceptions into one `NONCONVERGED` result. P7.C7 is never rerun.

`P7C7_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C7_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P7.C8 successor

Initial prep `9297395efb678356255d91aa8d90001a5fc768e0` was architect reviewed as `REWORK_REQUIRED` because acquisition containment/evidence still had unbounded cleanup join, optimistic parent `CONFIRMED`, lost post-containment classification, an invalid cleanup-category journal route, incomplete safe category authority and a non-authoritative journal reader.

Repair-1 was architect accepted:

- executable commit `070bcd0caa336d6df1ed24ee05d31dcce3d2cd95`;
- executable tree `787e083077b7386a8b05968f2193c611d8182d9d`;
- harness blob `53e70ba37803bb6a88e3e8ab4b7f499db1e28df8`.

The one-shot P7.C8 real probe executed exactly once and is permanently consumed. Real evidence commit: `21d3c3f6dbcb0c77047121c75b70a0d0f0814bea`.

Durable parent authority:

- `PARENT_EXECUTION_CLASS=CHILD_NONZERO`;
- `WATCHDOG_STATUS=PROCESS_COMPLETED`;
- `RUNTIME_ACQUIRE_INITIAL_RESULT=RUNTIME_ACQUIRE_SAFE_EXCEPTION`;
- `RUNTIME_ACQUIRE_RESULT=RUNTIME_ACQUIRE_SAFE_EXCEPTION`;
- `RUNTIME_ACQUIRE_ERROR_CATEGORY=storage_boundary_invalid`;
- `RUNTIME_ACQUIRE_CLEANUP_RESULT=CONFIRMED`;
- normal result absent;
- child result absent;
- active process-group count 0, scan errors 0, no TERM/KILL;
- one child, zero retries.

Architect source review establishes the exact root cause: the P7.C8 test harness manually created `isolated_state/sqlite` and `isolated_state/logs` but omitted the production `.codexcontrol-state-root-v1` marker. Production `IsolatedStateRoot.validate()` requires the exact marker/sqlite/logs layout and correctly rejected the manual state root as `storage_boundary_invalid` before app-server/model/list/thread/start.

Architect review:

`docs/evidence/p7c8/P7C8_ONE_SHOT_REAL_DENY_ONLY_APPROVAL_PROBE_ARCHITECT_REVIEW_2026-09-11.md`

Final P7.C8 classification:

`P7C8_FAILURE_CLASS=HARNESS_PRECONDITION_DEFECT`

`P7C8_ROOT_CAUSE=ISOLATED_STATE_ROOT_NOT_PROVISIONED_BY_PRODUCTION_AUTHORITY`

`P7C8_FRESH_THREAD_DISPOSITION=NO_FRESH_THREAD_PROVED`

`P7C8_APPROVAL_DISPOSITION=APPROVAL_NOT_REACHED_PROVED`

`P7C8_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C8_REAL_PROBE_RERUN_AUTHORIZED=NO`

`P7C8_REAL_APPROVAL_PROBE_AUTHORIZED=NO_CONSUMED`

`P7C8_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

## P7.C9 production-provisioned successor

Initial zero-effect P7.C9 prep candidate:

- commit `097c8809a90eaca5d7d2074b35dc5e73ae9762c1`;
- tree `c099c3a35acde82674f70413f55121c9345c82ba`;
- harness blob `0bccd8e80b362dd283773d6fea18a4a094018042`;
- scope limited to the new P7.C9 harness and prep evidence;
- reported real effects `0`.

The candidate correctly uses production `IsolatedStateRoot.provision(profile)` followed by `validate(profile)` before runtime acquisition and does not manually create the state root, marker, `sqlite/`, or `logs/`. Failed provision/validate blocks downstream runtime/model/thread/Turn/approval effects, and the accepted P7.C8 acquisition/DENY/process/journal/result gates remain present.

Architect review:

`docs/evidence/p7c9/P7C9_DENY_ONLY_APPROVAL_PROBE_PREP_ARCHITECT_REVIEW_2026-09-11.md`

Disposition: **REWORK_REQUIRED** before any real P7.C9 execution.

Blocking defects:

- `validate_parent_execution_outcome()` shadows `runtime_acquire_error_category` with a state-root category variable before the `RUNTIME_ACQUIRE_NOT_ESTABLISHED` consistency check, so contradictory failure evidence can evade the intended validator gate;
- the state-root bounded seam returns `TIMEOUT` while its daemon worker may still be running and mutating the fresh state root; worker terminalization/nonconvergence is not durably represented.

Binding Repair-1 contract:

`docs/evidence/p7c9/P7C9_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR1_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C9 DENY-only approval-probe prep Repair-1 — NEXT / ZERO REAL EFFECT.**

Repair-1 is limited to parent evidence fact separation and truthful bounded state-root worker ownership. Production provisioning remains mandatory and all accepted acquisition/DENY/process/journal/result gates must remain unchanged.

`P7C9_DENY_ONLY_APPROVAL_PROBE_PREP=REWORK_REQUIRED`

`P7C9_PREP_REPAIR1=NEXT_ZERO_REAL_EFFECT`

`P7C9_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C9_REAL_EXECUTION_AUTHORIZED=NO`

`P7C9_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until real P7 acceptance is architect accepted.
