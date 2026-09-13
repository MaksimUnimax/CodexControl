# P7.C17 final hard-delete real execution contract — 2026-09-13

Status: **ONE-SHOT REAL EXECUTION FROZEN / EXACT SOURCE ONLY / NO RETRY**

## Exact executable authority

- HEAD: `3da1817172f7f197276ec388c94e399fa0d31640`
- tree: `70effe87dd31acd92cd2e2984e65e0d114e2451b`
- P7.C17 launcher blob: `66718dd22467e13d741b26759f295836c3aa369f`
- actual final P7.C17 preparation evidence blob: `6b2b8530b0c13e36190517b19480dc38e3dde959`
- P7.C16 forensic evidence blob: `fb3ca5366f38e9374b6175c8b35b9a392a2a8249`
- P7.C16 launcher blob: `2c500d7d5787a7eda71c1e3e3591d8034dded590`
- P7.C15 launcher blob: `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`
- P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- `tests/__init__.py`: `080243830be797f87d23b459dbfd12c142a9d49a`
- `tests/real/__init__.py`: `23d73d7648ed14ef6857ee665784b87f57fde9f3`

The execution branch must begin exactly at this HEAD/tree. No source edit, merge, rebase or squash is permitted before the one parent invocation.

## Replay barrier

The distinct replay barrier is:

`/root/.codexcontrol/p7c17-one-shot.json`

It must be absent before execution. Once successfully reserved, P7.C17 is permanently consumed for every terminal or partial outcome. The barrier must never be reset, removed, replaced or bypassed. There is no second child and no retry.

P7.C16, P7.C15, P7.C14 and P7.C13 remain permanently non-retryable.

## Pre-consumption gates

Before enabling the one-shot gate require, without starting Codex or reserving the replay barrier:

1. exact HEAD/tree and protected blobs above;
2. clean tracked worktree and index and no unexplained source drift;
3. P7.C17 replay barrier absent;
4. `/usr/bin/python` exactly Python 3.12.3;
5. deterministic `PYTHONPATH=/root/CodexControl/src:/root/CodexControl`;
6. repository-local imports for `codex_control`, `tests`, `tests.real`, P7.C12, P7.C13, P7.C14, P7.C15, P7.C16 and P7.C17;
7. gate-disabled P7.C17 parent smoke exits `2`, leaves the replay barrier absent and creates no P7.C17 run authority;
8. installed Codex exactly `codex-cli 0.144.6`;
9. installed schema aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
10. `/root/.codex_second` and `/root/.codexcontrol` satisfy accepted root/private authority;
11. P7.C17 read-only source-bundle gate passes before executor construction.

The one-shot gate value and digest are supplied out of band by the architect execution prompt and must never be committed.

## Exact parent command

Run exactly once with deterministic import authority:

`/usr/bin/python -m tests.real.test_p7_c17_final_hard_delete_successor --p7c17-real-run`

Production watchdog hard deadline is `1660.0s` plus accepted TERM/KILL grace. No external timeout may be shorter than that deadline plus termination/reaping margin.

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

## Corrected marker authority

Global residual identity may use only the P7.C17 fresh/run-unique marker policy:

- fresh memory marker;
- fresh response marker;
- exact run-unique approval target;
- exact run-unique Turn-3 prompt containing that target.

Fixed `TURN4_STIMULUS` / `sleep 120` remains the behavioral Turn-4 stimulus but is forbidden from residual identity. Unrelated retained sessions containing `sleep 120` must not cause marker-residual failure.

## Acceptance sequence

The one child must prove the accepted P7.C16/P7.C15 lifecycle/delete chain: installed/authenticated runtime authority, one model/list, fresh thread, Turn-1 marker proof, generation restart/resume, Turn-2 memory proof, exact Turn-3 approval path, exact Turn-4 active/interrupt path, pre-delete target proof, schema-v4 controller binding, late-bound exact controller storage, real cleanup coordinator and real delete service, one canonical delete, independent official delete observation, correct UNKNOWN/CONFIRMED_PENDING semantics, final runtime convergence and post-delete observations.

Before final success, P7.C17 must additionally persist and validate:

- bounded root-only unrelated-removal attribution authority;
- bounded root-only complete oracle-facts authority;
- actual post-delete schema observation;
- independent isolation-envelope class;
- persistent/isolated thread, marker and scan counts;
- descendant regular/special/symlink/error counts;
- recovery and budget class;
- runtime-child quiescence;
- exact P7.C17 marker-policy class/version/hashes;
- exact failed/unavailable predicate sets.

The parent independently re-reads facts and attribution, verifies source/run/boot correlation and both digests, replays the unrelated-removal boolean, evaluates the facts vector, verifies child counts, exact effects and process-group facts, and only then maps durable state to `COMPLETED`.

## Terminal mapping

Only complete verified success maps to ledger `COMPLETED` and parent exit `0`.

Watchdog timeout maps to `TIMEOUT`.

Official `DELETE_UNKNOWN` maps to `UNKNOWN`, nonzero exit and no retry/read/list/manual success inference.

Official confirmed delete plus application `CONFIRMED_PENDING_STORAGE` maps to `CONFIRMED_PENDING`, nonzero exit and no second external delete.

Every other non-pass condition maps to `FAILED`.

No terminal state is retryable.

## Parent PASS authority

`COMPLETED` additionally requires:

- watchdog `COMPLETED`;
- watchdog child-result-valid true;
- valid root-only child result;
- child PASS/verdict true;
- runtime-child quiescent true;
- exact effect gate true;
- child count 1;
- retry count 0 and retry false;
- owned group active 0;
- zombies 0;
- group scan errors 0;
- valid correlated oracle facts;
- valid correlated unrelated-removal authority;
- facts digest agrees with child result;
- attribution digest and boolean agree with facts;
- failed predicate count 0;
- unavailable predicate count 0;
- child predicate counts agree with parent evaluation;
- exact marker-policy authority valid.

CLI success must follow the final durable P7.C17 state, not watchdog completion alone.

## Post-run evidence

After the one-shot parent exits, never rerun. Read only retained P7.C17 ledger/run-bound authorities and create only:

`docs/evidence/p7c17/P7C17_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-13.md`

Sanitized evidence must record source/hash authority, parent/ledger/watchdog/child classes, safe stage/category, exact effects, approval/interrupt/delete classes, runtime/process-group facts, oracle-facts digest/class, failed/unavailable predicate counts, attribution digest/boolean class and final verdict. Do not record raw runtime identifiers, prompts, responses, marker plaintext, wire plaintext, raw paths containing runtime IDs or secrets.

Required terminal flags after replay reservation:

`P7C17_REAL_RUN_CONSUMED=YES`

`P7C17_REAL_RETRY_AUTHORIZED=NO`

`P7C17_REAL_PARENT_EXIT=<actual>`

`P7C17_REAL_LEDGER_STATE=<actual>`

`P7C17_REAL_CHILD_STATUS=<actual>`

`P7C17_REAL_OFFICIAL_DELETE=<actual>`

`P7C17_REAL_APPLICATION_DELETE=<actual>`

`P7C17_REAL_FINAL_VERDICT=<PASS|FAIL|UNKNOWN|CONFIRMED_PENDING|TIMEOUT>`

`P7C16_REAL_RETRY_AUTHORIZED=NO`

`P7C15_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

Only the sanitized post-run evidence file may be committed to the dedicated real-execution branch after the source-gated run. Independent architect review remains mandatory before P8 or P9.
