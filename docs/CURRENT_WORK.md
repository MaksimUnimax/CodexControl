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

Run-1 evidence: `785a82e2e9bc392173ea1e910b490f84cfa590b2`.

The old Run-1 Turn-3 approval remains `RESPONSE_UNKNOWN` and permanently non-retryable.

Accepted retained authorities:

- Turn-3 forensic: `e6835e7eaff21ce6a452c24f3309269df67c82ba`.
- Existing Run-1 latch forensic: `c308c765d9915844fce97d1d1f6c933e302a75aa`.
- Retained-thread SHA-256: `9be5e1f196c868df772e6971186905ee81f9ba02fe9f4cf0f72f13a2e55e41f6`.
- Accepted Run-1 latch SHA-256: `50616410354022747284c1ce61bd02b8ecd1eb2636657eac502092fde800d55e`.

The P7.C6 retained thread is now permanently forensic-only. No same-thread real rerun is allowed.

## P7.C6 continuation preparation

Prep-v2 through Repair-5 were REWORK_REQUIRED. Repair-6 is architect accepted:

- accepted commit `76a7aa24e3cfdfb12c3314a7e01691d4a943b551`;
- accepted tree `92abebdfb3390d4c58f4aefc00aa84b83841e99e`;
- architect acceptance `docs/evidence/p7c6/P7C6_SAME_THREAD_PREP_V2_REPAIR6_ARCHITECT_ACCEPTANCE_2026-09-11.md`.

Preparation proved exact source/latch/topology/controller/budget gates, strict approval matching, exact sentinel proof, retained-state scanning, one-delete semantics, success-only sanitization, finite owned-task convergence, process-level watchdog, sanitized child-to-parent result authority and full continuation process-group ownership.

`P7C6_PREPARATION=ACCEPTED`

## P7.C6 one-shot real continuation — consumed / architect-reviewed

Binding execution contract:

`docs/evidence/p7c6/P7C6_REAL_SAME_THREAD_CONTINUATION_EXECUTION_CONTRACT_2026-09-11.md`

The single authorized command executed exactly once from the accepted Repair-6 snapshot and returned `RC=1`. No rerun occurred or is allowed.

Executor one-shot evidence commit:

`9b45d27a9d55d7d0695351ca57f71a75a4cd7971`

Consumed-run forensic commit:

`cf716ebb6c90e09fe927bccf36fdc08c776537b3`

Architect forensic review:

`docs/evidence/p7c6/P7C6_CONSUMED_REAL_CONTINUATION_ARCHITECT_REVIEW_2026-09-11.md`

Architect-accepted final interpretation:

- model/list completed once;
- retained-thread resume completed with `RESUME_CONFIRMED`;
- Turn-4 start completed with `TURN_START_CONFIRMED`;
- approval bridge observed `0` approval requests and sent `0` approval responses, then timed out;
- Turn-4 nevertheless persisted terminal `COMPLETED` and created the exact run-owned sentinel;
- no Turn-5 continuation turn exists and the Turn-5 marker is absent;
- controller DB remained untouched at user_version `0`, with no synthetic dialogue, tombstone, containment or pending-storage state;
- process-result authority was never created;
- official P1.9 delete was not dispatched;
- no production lifecycle/delete defect is established.

Final P7.C6 classifications:

`LAST_DURABLY_ESTABLISHED_STAGE=TURN4_COMPLETED_SENTINEL_PROVED`

`OFFICIAL_P1_DELETE_CLASS=NOT_DISPATCHED_PROVED`

`FAILURE_CLASS=TURN4_APPROVAL_FAILURE__NO_APPROVAL_REQUEST`

`ROOT_CAUSE_CLASS=HARNESS_ACCEPTANCE_STIMULUS_DEFECT`

`PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C6_REAL_RERUN_AUTHORIZED=NO`

P7.C6 is closed as a consumed real-acceptance failure before Turn-5/delete. It is not a P7 PASS and not a production hard-delete failure.

## P7.C7 approval-stimulus authority — architect reviewed

Executor authority lineage:

- `5ec38a38cef6363bb3709aefe57c0dedae5f5e13` — initial zero-effect evidence;
- `e00392fbff6894e1857eb4c8f1e1937a88ca1e96` — final evidence count correction.

Evidence:

`docs/evidence/p7c7/P7C7_APPROVAL_STIMULUS_AUTHORITY_EVIDENCE_2026-09-11.md`

Architect review:

`docs/evidence/p7c7/P7C7_APPROVAL_STIMULUS_AUTHORITY_ARCHITECT_REVIEW_2026-09-11.md`

Accepted findings:

- exact upstream authority is `rust-v0.144.6`, release commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`;
- Run-1 retained Turn-3/session hashes match accepted authority;
- historical persisted command remains `OTHER / TOKEN_MISMATCH` and is not used as wire-command authority;
- exact release proves internal `Vec<String>` -> approval event -> app-server `shlex_join` -> `CommandExecutionRequestApprovalParams.command`;
- exact release also proves approval routing is conditional;
- preserved/offline evidence does **not** establish which internal command vector a future model turn will generate from the proposed natural-language stimulus;
- therefore future concrete approval-request wire grammar is not established and no ALLOW matcher may be frozen offline.

Architect classification:

`P7C7_APPROVAL_STIMULUS_AUTHORITY=ACCEPTED_AS_NOT_ESTABLISHED`

`P7C7_APPROVAL_REQUEST_WIRE_MAPPING=ESTABLISHED`

`P7C7_FUTURE_CONCRETE_WIRE_GRAMMAR=NOT_ESTABLISHED`

`P7C7_MATCHER_AUTHORIZED=NO`

This is a successful fail-closed authority result, not a production defect.

## Current executable slice

**P7.C7 DENY-only approval-probe preparation — NEXT / ZERO REAL EFFECT.**

Binding preparation contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_CONTRACT_2026-09-11.md`

The preparation slice must build/test a future fresh-thread probe harness whose approval operator has no ALLOW path, observes approval and turn-terminal concurrently, captures real wire grammar only into root-only authority, denies every observed approval request, owns a fresh isolated run/process-group boundary, and remains gated/inert during ordinary tests.

No fresh real thread is authorized by this preparation slice. After executor completion, architect must independently review the harness before freezing any one-shot real approval-probe contract.

`P7C7_DENY_ONLY_PROBE_PREPARATION=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until a fresh disposable-thread P7.C7 real hard-delete acceptance is separately prepared, authorized and architect-accepted.
