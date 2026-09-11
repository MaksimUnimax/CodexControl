# Current work authority

Date: 2026-09-11

## Accepted baseline

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority: `codex-cli 0.144.6`; generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P0–P6 are complete. P6 accepted commit: `0409ad4a0744159aad875a5ddea4deaf1181699e`.
- Controller schema authority is v4 with migration `0004_delete_local_containment`, SHA-256 `400a475cb074da6b82238af105412d8299b45816273136bfd54a2cbd2308e059`.
- P7.C1–P7.C5 are architect accepted; P7.C5 accepted proof `946ddf7ac6f7c3539bc3f344c6edf21d6ffce528`.
- ADR-0045 remains binding: persistent authenticated `CODEX_HOME` may be shared; CodexControl owns only its own child/generation, isolated state root, controller SQLite and process-local reservation/quiescence.

## P7.C6 disposition

P7.C6 is permanently consumed and forensic-only. Architect review established that Turn-4 completed with exact sentinel proof but produced no approval request; the harness approval wait timed out before Turn-5/delete. Official P1.9 delete was not dispatched. Root cause is `HARNESS_ACCEPTANCE_STIMULUS_DEFECT`; no production lifecycle/delete defect is established. No P7.C6 rerun/resume/interrupt/delete/read/list is authorized.

## P7.C7 approval-stimulus authority

The zero-effect approval-stimulus authority was architect accepted as correctly fail-closed: exact Codex `rust-v0.144.6` source proves internal command-vector -> app-server `shlex_join` projection and conditional approval routing, but preserved/offline evidence cannot establish a future model-generated concrete wire grammar. No ALLOW matcher is authorized.

## P7.C7 DENY-only approval-probe preparation

Initial prep `e4bcdf43ba3f5c50a65f7f1085781eec41770ede` and Repair-1 `bffe4d05340545edd44d503c9a16f1128c65ca7d` are REWORK_REQUIRED harness-only candidates.

Repair-2 candidate:

`388b1a1bf46b56bc1734bbf2e3eb630266b822a7`

Repair-2 materially improves the future disabled real path: exact Turn authority precedes approval dequeue, queued-request capture is test-covered, DENY attempts are counted, a recovery journal exists, inner waits are named/finite, a dedicated parent/child watchdog exists, child/parent result schemas are separated, and `/proc` churn semantics are improved.

Independent architect review still finds Repair-2 **REWORK_REQUIRED** before any real fresh thread can be authorized.

Remaining harness-only blockers:

1. Parent final-result materialization calls the child-schema writer `write_sanitized_result(...)`; that writer exact-validates the child schema and therefore rejects the extended parent schema. A healthy real probe cannot persist its final global result.
2. Durable approval chronology is reversed/incomplete: `APPROVAL_REQUEST_<N>_OBSERVED` is appended only after the complete race returns, although a DENY response may already have been dispatched. Request-observed authority must precede DENY dispatch intent.
3. `MODEL_LIST_RESULT` / `THREAD_START_RESULT` / `TURN_START_RESULT` semantics are conflated between raw wire return and adapter-level validation. In particular thread/turn result rows can be duplicated and disagree after malformed/semantically rejected responses. Wire-result and adapter-result authorities must be distinct.
4. Child-local command-boundary proof occurs before parent process-group quiescence. A surviving descendant can mutate sentinel/workdir after the child scan but before parent TERM/KILL convergence. Parent must perform a final read-only command-boundary recheck after group quiescence before publishing final authority.
5. Parent does not preserve watchdog-timeout classification in the final result: `CHILD_RETURN_TIMEOUT` exists but timeout can be collapsed to generic `CHILD_NONZERO` if a child result exists. Final authority must state timeout/residual/scan-error classifications exactly.
6. Child result does not require all approval/terminal owner tasks to be terminalized. `ProbeObservation.observer_joined` can be false while a child-local result is still built; nonconverged owner state must block normal child-result success or be explicitly classified.

No production `src/**` defect is established.

Binding Repair-2 architect review:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR2_ARCHITECT_REVIEW_2026-09-11.md`

Binding Repair-3 contract:

`docs/evidence/p7c7/P7C7_DENY_ONLY_APPROVAL_PROBE_PREP_REPAIR3_CONTRACT_2026-09-11.md`

## Current executable slice

**P7.C7 DENY-only approval-probe prep Repair-3 — NEXT / ZERO REAL EFFECT.**

Repair-3 is harness/tests/evidence only. It must close the six remaining execution/evidence-authority defects while preserving every accepted Repair-2 safeguard. No real P7.C7 thread, app-server, approval response or root global probe authority is authorized during Repair-3.

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR2=REWORK_REQUIRED`

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR3=NEXT_ZERO_REAL_EFFECT`

`P7C7_REAL_APPROVAL_PROBE_AUTHORIZED=NO`

`P7C7_REAL_EXECUTION_AUTHORIZED=NO`

P8/P9 remain blocked until P7.C7 real acceptance is architect accepted.
