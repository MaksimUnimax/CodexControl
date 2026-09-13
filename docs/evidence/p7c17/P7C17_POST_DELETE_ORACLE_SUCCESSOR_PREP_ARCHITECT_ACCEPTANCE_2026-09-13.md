# P7.C17 post-delete oracle successor preparation — architect acceptance — 2026-09-13

Status: **PREPARATION COMPLETE / ARCHITECT_ACCEPTED / REAL EXECUTION REQUIRES SEPARATE ONE-SHOT CONTRACT**

## Accepted executable authority

- executable source HEAD: `3da1817172f7f197276ec388c94e399fa0d31640`;
- executable source tree: `70effe87dd31acd92cd2e2984e65e0d114e2451b`;
- P7.C17 launcher blob: `66718dd22467e13d741b26759f295836c3aa369f`;
- actual final P7.C17 preparation evidence blob: `6b2b8530b0c13e36190517b19480dc38e3dde959`;
- P7.C16 forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`;
- consumed P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`;
- inherited P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- inherited P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

The candidate is exactly two linear commits ahead of Repair-1 base `95c15bf03d58dddd86229faafe715271996a98ae`; the second commit changes only the evidence metadata. Across both commits, only the P7.C17 launcher and P7.C17 preparation evidence changed. No `src/**`, historical P7.C16/P7.C15/P7.C14/P7.C13/P7.C12 source/evidence, package marker, migration, deployment, Telegram, P8 or P9 path changed.

The embedded preparation-evidence field `P7C17_EVIDENCE_BLOB=c2e799c8d7341175074ea6bb2c5d62b3d1a0aa1f` is a pre-final self-reference value and is **not** accepted as final blob authority. A file cannot stably contain its own final Git blob hash. The external architect authority above binds the actual final blob `6b2b8530b0c13e36190517b19480dc38e3dde959`; no repair is required for this non-executable bookkeeping field.

## Independent architect acceptance

Independent exact-source review accepts the complete P7.C17 successor preparation:

- the P7.C16 false positive from global use of fixed `TURN4_STIMULUS` is reproduced;
- `P7C17CurrentRunMarkerPolicy` validates the frozen five-marker semantic shape and excludes fixed/common Turn-4 stimulus from residual identity;
- fresh memory/response and run-unique approval-target/Turn-3 prompt marker authority remains fail-closed and target-specific;
- unrelated retained `sleep 120` does not count as current-run marker residue;
- true fresh current-run marker residue still rejects acceptance;
- persistent thread/filename/directory and isolated residual checks remain independent and unchanged in authority;
- P7.C17 composes the accepted P7.C16/P7.C15 lifecycle/delete path and does not redesign the real cleanup coordinator, delete service or official delete observation;
- actual post-delete schema is captured from the inherited read, not fabricated; schema drift is retained as `NON_V4` with the observed integer;
- isolation-envelope validity is independently retained instead of being inferred from the combined inherited acceptance flag;
- root-only oracle-facts authority is written before final acceptance, read back, independently evaluated and required to agree with the frozen `post_delete_acceptance(...)` boolean;
- exact failed and unavailable predicate counts are retained in the child result and independently re-evaluated by the parent;
- sanitized unrelated-removal attribution is replayable from retained SHA-256 path identities; its boolean and digest are independently correlated to oracle facts by the parent;
- attribution authority has a dedicated 2 MiB bound and 4096-entry per-list bound with no silent truncation;
- P7.C17 child result projects inherited P7.C16 schema/effect/map/string/quiescence validation and adds facts digest plus failed/unavailable counts;
- parent `COMPLETED` restores every accepted P7.C16 terminal condition and adds P7.C17 facts/attribution/marker-policy proof gates;
- watchdog `TIMEOUT` maps to durable `TIMEOUT`; `UNKNOWN` and `CONFIRMED_PENDING` remain distinct non-retryable terminal states;
- parent recovery retains watchdog/child/effect/group/signal/stage authority plus P7.C17 facts and attribution proof classes;
- CLI exit projection follows the final durable P7.C17 state, so watchdog completion cannot mask parent proof failure;
- P7.C17 production watchdog is frozen at inherited P7.C16 deadline plus a positive 60-second evidence-processing margin;
- default source gate and default real entrypoint select the production executor; the zero-real-effect handoff traversed one owned child, real application cleanup/delete chain, corrected marker policy, facts/attribution persistence, parent proof gate and durable `COMPLETED` projection;
- gate-disabled smoke exits `2` without P7.C17 ledger/run/Codex effects.

## Historical boundaries

P7.C16 is permanently consumed `FAILED`; its real delete was confirmed but its final oracle rejected due the proven shared-persistent static-marker false positive. P7.C15, P7.C14 and P7.C13 also remain permanently non-retryable. No historical ledger/material may be reset, cleaned or used as P7.C17 replay authority.

## One-shot status

`P7C17_PREP_ARCHITECT_ACCEPTED=YES`

`P7C17_PREP_COMPLETE=YES`

`P7C17_REAL_EXECUTION_AUTHORIZED_BY_THIS_DOCUMENT=NO`

A separate exact-source one-shot execution contract is required. It must use distinct replay barrier `/root/.codexcontrol/p7c17-one-shot.json`, a fresh out-of-band token, exact source/tree/blob authority above, pre-consumption source/import/installed/home checks, and no retry after reservation.

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
