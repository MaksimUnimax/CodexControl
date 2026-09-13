# P7.C15 final hard-delete real execution contract — 2026-09-13

Status: **ONE-SHOT REAL EXECUTION FROZEN / EXACT SOURCE ONLY / NO RETRY**

## Accepted executable authority

The only authorized executable source is:

- HEAD `17f8907068aa58de85d92800b9d87621e59ad1a3`;
- tree `993f094a50e062459908f1ddd373c48de478d7a1`;
- P7.C15 launcher blob `ebe4ffab2d08494452c1b132fe2fed50f4830a6b`;
- P7.C15 preparation evidence blob `4faca2df650917cb1e6c1de529bc658a4fa51286`;
- P7.C14 launcher blob `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- P7.C13 harness blob `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- P7.C12 matcher blob `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `tests/__init__.py` blob `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob `23d73d7648ed14ef6857ee665784b87f57fde9f3`.

Execution branch must start exactly from that HEAD/tree. No source edit, merge, rebase, squash or evidence edit may occur before the real parent command.

## Replay barrier and one-shot rule

Authoritative replay barrier:

`/root/.codexcontrol/p7c15-one-shot.json`

Before execution it must be absent.

Once the ledger is successfully reserved, P7.C15 is permanently consumed regardless of PASS, FAIL, TIMEOUT, UNKNOWN, CONFIRMED_PENDING, exception, partial progress or parent termination. The ledger must never be deleted, reset, replaced, truncated, renamed or bypassed. No second child, second real run or retry is authorized.

P7.C14 and P7.C13 remain permanently non-retryable.

## Pre-consumption gates

All of the following must pass before the real authorization token is exported and before ledger reservation:

1. current execution branch HEAD/tree exactly match the accepted executable authority;
2. launcher, inherited protected blobs and package-marker blobs match exactly;
3. tracked worktree and index are clean and there is no unexplained untracked source drift;
4. `/root/.codexcontrol/p7c15-one-shot.json` is absent;
5. exact interpreter is `/usr/bin/python` reporting Python 3.12.3;
6. exact deterministic import authority is `PYTHONPATH=/root/CodexControl/src:/root/CodexControl`;
7. import-only smoke succeeds for `codex_control`, `tests`, `tests.real`, P7.C12, P7.C13, P7.C14 and P7.C15 modules and resolves to repository authority;
8. gate-disabled exact P7.C15 parent smoke returns exit `2`, leaves P7.C15 ledger absent, creates no `p7c15-state-parent-*` or `p7c15-work-parent-*`, and starts no Codex/app-server process;
9. `/usr/local/bin/codex --version` is exactly `codex-cli 0.144.6`;
10. installed schema aggregate SHA-256 is exactly `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
11. `/root/.codex_second` and `/root/.codexcontrol` satisfy the accepted root-owned/non-group-world-writable authority;
12. read-only P7.C15 source-bundle gate passes using the future real environment but without invoking `p7c15_real_entrypoint()`, executor construction, ledger reservation, child spawn or Codex.

Any failure before ledger reservation stops the execution without consuming P7.C15.

## Authorization token authority

The real token is supplied out of band and must never be committed or written into evidence.

Required token SHA-256:

`cceea732112073baede130f2ae557d86ff7379a481c645ebc70e46d75c75efef`

The plaintext token must be used only in the execution environment for the single run and then unset.

## Exact environment

The real parent environment must include exactly the accepted deterministic import authority and these P7.C15 values:

- `P7C15_EXPECTED_HEAD=17f8907068aa58de85d92800b9d87621e59ad1a3`
- `P7C15_EXPECTED_TREE=993f094a50e062459908f1ddd373c48de478d7a1`
- `P7C15_EXPECTED_LAUNCHER_BLOB=ebe4ffab2d08494452c1b132fe2fed50f4830a6b`
- `P7C15_EXPECTED_P7C14_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8`
- `P7C15_EXPECTED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c`
- `P7C15_EXPECTED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`
- `P7C15_EXPECTED_TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a`
- `P7C15_EXPECTED_TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3`
- `P7C15_FUTURE_REAL_GATE=<one exact out-of-band token>`.

No P7.C13/P7.C14 real gate variable may be set.

## Exact parent invocation

Execute exactly once:

`PYTHONPATH=/root/CodexControl/src:/root/CodexControl /usr/bin/python -m tests.real.test_p7_c15_final_hard_delete_successor --p7c15-real-run`

P7.C15 production owns:

- ledger reservation before all run-specific mutation;
- one owned child;
- P7.C15-specific `1480.0s` parent watchdog hard deadline plus accepted TERM/KILL grace;
- bounded per-stage child waits;
- no retry and no second child.

## Frozen real effect ceilings

Maximum and PASS-exact effect authority:

- new threads: `1`;
- model/list: `1`;
- thread/start: `1`;
- thread/resume: `1`;
- turn/start: `4`;
- approval protocol responses: `1`;
- ALLOW: `1`;
- DENY on PASS: `0`;
- turn/interrupt: `1`;
- official thread/delete: `1`;
- thread/read: `0`;
- thread/list: `0`;
- second child: `0`;
- real retry: `0`;
- Telegram: `0`.

PASS requires the exact positive/zero matrix, not only ceiling compliance.

## Frozen acceptance sequence

The single real child must prove the complete accepted sequence:

1. installed authority and isolation boundaries;
2. generation-1 runtime acquire;
3. exactly one authenticated model/list and selected default model/reasoning authority;
4. fresh thread/start;
5. Turn 1 with fresh memory/response markers and exact response-marker proof;
6. generation-1 shutdown;
7. generation-2 acquire and thread/resume;
8. Turn 2 exact remembered-marker proof using generation rebound and no second model/list;
9. Turn 3 exact C11 explicit escalation, root-only wire/recovery authority, accepted P7.C12 matcher, one request, one bridge response, one ALLOW, no second request/response, completed Turn 3 and strict private approval-target proof;
10. Turn 4 exact `sleep 120`, active/nonterminal proof, unexpected-request observer, exactly one interrupt and definitive terminal;
11. runtime shutdown before physical proof;
12. conclusive target-specific pre-delete oracle and before-metadata authority;
13. fresh schema-v4 controller IDLE binding;
14. exactly one canonical `DialogueDeleteService.delete()`;
15. independent `OfficialDeleteObservation`;
16. correct UNKNOWN / CONFIRMED_PENDING no-retry semantics;
17. post-delete schema v4 re-read, tombstone/live-binding proof, separate persistent/isolated oracle families, derived unrelated-removal fact, isolation-envelope/descendant proof and runtime-child quiescence;
18. parent watchdog process-group active/zombie/scan proof and exact-effect PASS gate.

## Terminal semantics

Full valid success only:

- child `PASS`, verdict true;
- official `DELETE_CONFIRMED`;
- application `DELETED`;
- runtime child quiescent;
- exact effect matrix;
- owned process-group active `0`, zombies `0`, scan errors `0`;
- one child, zero retry;
- all post-delete observed facts clean;

maps to ledger `COMPLETED` and parent exit `0`.

Official `DELETE_UNKNOWN` maps to child/ledger `UNKNOWN`, nonzero exit and no retry/read/list/manual cleanup/finalization inference.

Confirmed external delete plus application `CONFIRMED_PENDING_STORAGE` maps to child/ledger `CONFIRMED_PENDING`, nonzero exit and no second external delete.

Timeout maps to ledger `TIMEOUT`; normal failures map to `FAILED`. No terminal class is retryable.

## Sanitized post-run evidence

After the one-shot run, never rerun. Read only the P7.C15 ledger, exact current-run boot/child-result/stage/wire/recovery authorities and safe physical facts.

Create exactly:

`docs/evidence/p7c15/P7C15_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-13.md`

The evidence may contain only sanitized authority, including source/tree/blob hashes, token SHA-256 only, parent exit, ledger/child/terminal classes, safe effect counts, safe stage classes, approval/interrupt/delete classes, residual counts/classes, runtime-child quiescence, parent watchdog/group facts, child/retry counts and final verdict.

It must not contain the plaintext token, raw thread/Turn IDs, raw prompt/response, wire plaintext, raw root-only JSON, credentials or secrets.

Required final flags:

- `P7C15_REAL_RUN_CONSUMED=YES`
- `P7C15_REAL_RETRY_AUTHORIZED=NO`
- `P7C15_REAL_PARENT_EXIT=<actual>`
- `P7C15_REAL_LEDGER_STATE=<actual>`
- `P7C15_REAL_CHILD_STATUS=<actual>`
- `P7C15_REAL_OFFICIAL_DELETE=<actual>`
- `P7C15_REAL_APPLICATION_DELETE=<actual>`
- `P7C15_REAL_FINAL_VERDICT=<PASS|FAIL|UNKNOWN|CONFIRMED_PENDING|TIMEOUT>`
- `P7C14_REAL_RETRY_AUTHORIZED=NO`
- `P7C13_REAL_RETRY_AUTHORIZED=NO`
- `P8_STARTED=NO`
- `P9_STARTED=NO`.

## Publication

Post-run evidence only may be committed to the dedicated real execution/evidence branch after the source-gated run. No source/harness change is permitted before or during execution.

Independent architect review of the sanitized real evidence is required before P8 or P9 may start.
