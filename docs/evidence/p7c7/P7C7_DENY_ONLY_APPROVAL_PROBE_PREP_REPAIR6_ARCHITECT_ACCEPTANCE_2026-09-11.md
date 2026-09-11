# P7.C7 DENY-only approval-probe preparation Repair-6 — architect acceptance — 2026-09-11

Status: **ARCHITECT ACCEPTED / ZERO-REAL-EFFECT PREPARATION COMPLETE / REAL PROBE MAY BE SEPARATELY AUTHORIZED**

## Accepted executable authority

- Repair-6 commit: `320ae3ba1265608a92ebfe82992068d4b12ebcd9`.
- Repair-6 tree: `eb0381e02b94de1a5f2bc1220c4591536b2ba5b0`.
- Harness blob: `b2bf5f91250b8881050ce3afcbd3e86874b15e5e`.
- Base: `36c03da116f06d03cf7b905670982b3fb7a3938b`.
- Candidate is exactly one commit ahead of the base and changes only `tests/real/test_p7_c7_deny_only_approval_probe.py` plus Repair-6 evidence. No `src/**` change occurred.

## Independent acceptance findings

Repair-6 closes the final frozen normal-result truthfulness defect:

- normal child result projects `model_list_calls`, `thread_start_calls`, and `turn_start_calls` from the authoritative `FutureProbeBudget`;
- normal child authority requires exact `1/1/1` for those lifecycle RPC dispatch attempts;
- normal child authority requires non-null 64-lowercase-hex fresh thread and Turn hashes;
- forbidden lifecycle effects remain exact zero: resume, interrupt, delete, thread/read, thread/list;
- ALLOW remains exact zero;
- normal parent-final authority independently requires exact `1/1/1` and retains the full process-group/source/boundary/result gates;
- the real normal route can reach child-result publication only after confirmed model catalog, confirmed thread/start binding, confirmed turn/start binding, exact Turn-ID authority, bounded observation, budget reconciliation, finite runtime shutdown and child boundary proof.

All accepted Repair-5 authorities remain present: measured parent outcome facts, narrow child execution classes, semantic class-to-facts matrix, bounded child-result discovery, immutable RecoveryJournal creation-time device/inode, no later `O_CREAT`, replacement/unlink/mode/hardlink fail-closed behavior, exact request-before-DENY chronology, truthful DENY ambiguity accounting, dedicated one-child process-group watchdog and source HEAD/tree/clean gate.

## Frozen real-probe boundary

The accepted preparation does **not** authorize ALLOW or hard delete.

The separately authorized real probe is observational only and may perform at most:

- model/list: 1;
- fresh thread/start: 1;
- primary turn/start: 1;
- DENY responses: 0..3;
- ALLOW responses: 0;
- thread/resume: 0;
- turn/interrupt: 0;
- thread/delete: 0;
- thread/read: 0;
- thread/list: 0.

The candidate stimulus remains exactly one finite 30-second sleep followed by one touch of a fresh run-owned sentinel outside the turn workdir but inside the dedicated probe root.

The real observation authority is 100 seconds. The full parent watchdog hard deadline is 165 seconds over a 146-second internal worst-case budget with 15 seconds explicit watchdog margin.

Any future real invocation is one-shot. Once started it is consumed under success, failure, timeout, ambiguity, missing result, parent-outcome failure, or process watchdog termination. No rerun is authorized.

## Disposition

`P7C7_DENY_ONLY_PROBE_PREP_REPAIR6=ARCHITECT_ACCEPTED`

`P7C7_PRODUCTION_DEFECT_ESTABLISHED=NO`

`P7C7_REAL_APPROVAL_PROBE_PREPARATION=COMPLETE`

A separate execution contract is required before real effects.

P8/P9 remain blocked.
