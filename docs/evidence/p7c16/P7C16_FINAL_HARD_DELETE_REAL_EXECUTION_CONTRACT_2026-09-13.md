# P7.C16 final hard-delete real execution contract — 2026-09-13

Status: **ONE-SHOT REAL EXECUTION FROZEN / EXACT SOURCE ONLY / NO RETRY**

## Exact executable authority

- HEAD: `5fb8ed6c2a27da3149476ec8501c533152a19b8f`
- tree: `251ec8d3971460dafd57429112a357b1b53e9b50`
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`
- P7.C16 preparation evidence blob: `aceb4474b66cc2bb6277b0ebe96f6d50ff99a2a4`
- consumed P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`

The execution branch must begin exactly from this HEAD/tree. No source edit, merge, rebase or squash is permitted before the single parent invocation.

## Replay barrier

The distinct replay barrier is `/root/.codexcontrol/p7c16-one-shot.json` and must be absent before execution. Once successfully reserved, P7.C16 is permanently consumed for every terminal or partial outcome. The barrier must never be reset, removed, replaced or bypassed. There is no second child and no retry.

P7.C15, P7.C14 and P7.C13 remain permanently non-retryable.

## Pre-consumption gates

Before enabling the one-shot gate, require all of the following without starting Codex or reserving the replay barrier:

1. exact HEAD/tree and protected blobs above;
2. clean tracked worktree and index and no unexplained source drift;
3. P7.C16 replay barrier absent;
4. `/usr/bin/python` reports Python 3.12.3;
5. deterministic import authority is `/root/CodexControl/src:/root/CodexControl`;
6. repository-local imports succeed for `codex_control`, `tests`, `tests.real`, P7.C12, P7.C13, P7.C14, P7.C15 and P7.C16;
7. gate-disabled P7.C16 parent smoke exits `2`, leaves the replay barrier absent and creates no P7.C16 run authority;
8. installed Codex is exactly `codex-cli 0.144.6`;
9. installed schema aggregate SHA-256 is `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
10. `/root/.codex_second` and `/root/.codexcontrol` satisfy the accepted root-owned storage authority;
11. the P7.C16 read-only source-bundle gate passes before executor construction.

The one-shot gate value and its digest are supplied out of band by the architect execution prompt and are never committed to this repository document.

## Exact parent command

Run exactly once with deterministic import authority:

`/usr/bin/python -m tests.real.test_p7_c16_final_hard_delete_successor --p7c16-real-run`

Production owns one child, a `1600.0s` hard watchdog deadline plus accepted TERM/KILL grace, bounded per-stage waits and bounded late-failure convergence.

## PASS-exact effect authority

- new threads `1`
- model/list `1`
- thread/start `1`
- thread/resume `1`
- turn/start `4`
- approval responses `1`
- ALLOW `1`
- DENY `0`
- turn/interrupt `1`
- thread/delete `1`
- thread/read `0`
- thread/list `0`
- second child `0`
- real retry `0`
- Telegram `0`

## Acceptance sequence

The single child must prove installed/authenticated runtime authority, one model/list, fresh thread and Turn-1 marker proof, generation restart/resume, Turn-2 memory proof, exact Turn-3 approval path, exact Turn-4 active/interrupt path, pre-delete physical proof, schema-v4 controller binding, P7.C16 late-bound exact controller-storage authority, real cleanup coordinator and real delete service readiness, exactly one canonical delete, independent official delete observation, correct UNKNOWN/CONFIRMED_PENDING behavior, post-delete storage/physical proofs, runtime-child quiescence, clean owned process group and exact effect counts.

Safe successor stages are ordered as reached:

`CONTROLLER_BINDING -> DELETE_CLEANUP_AUTHORITY_CONFIRMED -> DELETE_CHAIN_READY -> THREAD_DELETE_DISPATCH -> THREAD_DELETE_RESULT -> APPLICATION_DELETE_RESULT`.

Known controller-storage mismatch is retained only as the finite category `controller_storage_mismatch`, without raw paths.

## Terminal mapping

Only complete verified success maps to ledger `COMPLETED` and parent exit `0`.

Official `DELETE_UNKNOWN` maps to `UNKNOWN`, nonzero exit and no retry/read/list/manual cleanup inference.

Official confirmed delete plus application `CONFIRMED_PENDING_STORAGE` maps to `CONFIRMED_PENDING`, nonzero exit and no second external delete.

Watchdog timeout maps to `TIMEOUT`. Other failures map to `FAILED`. No terminal state is retryable.

## Post-run evidence

After the one-shot parent exits, never rerun. Read only the retained P7.C16 ledger and current-run bound authorities and create only:

`docs/evidence/p7c16/P7C16_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-13.md`

The evidence must remain sanitized: source/hash authority, parent/ledger/watchdog/child classes, safe stages/categories, effect counts, approval/interrupt/delete classes, residual/proof classes, runtime-child and process-group facts, child/retry counts and final verdict. Do not record raw runtime identifiers, prompts, responses, wire plaintext or secrets.

Required final flags:

`P7C16_REAL_RUN_CONSUMED=YES`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C16_REAL_PARENT_EXIT=<actual>`

`P7C16_REAL_LEDGER_STATE=<actual>`

`P7C16_REAL_CHILD_STATUS=<actual>`

`P7C16_REAL_OFFICIAL_DELETE=<actual>`

`P7C16_REAL_APPLICATION_DELETE=<actual>`

`P7C16_REAL_FINAL_VERDICT=<PASS|FAIL|UNKNOWN|CONFIRMED_PENDING|TIMEOUT>`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

Only the sanitized post-run evidence file may be committed to the dedicated real-execution branch after the source-gated run. Independent architect review remains mandatory before P8 or P9.
