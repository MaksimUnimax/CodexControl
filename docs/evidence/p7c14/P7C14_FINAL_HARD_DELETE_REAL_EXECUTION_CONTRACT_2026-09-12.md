# P7.C14 final hard-delete acceptance — one-shot real execution contract — 2026-09-12

Status: **FROZEN / DISTINCT ONE-SHOT REAL EXECUTION AUTHORIZED ONLY UNDER THIS EXACT CONTRACT**

## Purpose

This contract authorizes exactly one real P7.C14 successor acceptance run using the accepted P7.C14 launcher and inherited P7.C13 hard-delete implementation. It does not authorize a P7.C13 retry, implementation changes, a second P7.C14 child, retry, second approval response, second delete, P8 or P9.

## Exact executable source authority

The real run MUST execute from exactly:

- HEAD: `e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- tree: `7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- P7.C14 launcher blob: `fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- P7.C14 preparation evidence blob: `09bd9a1e2ab3c9518ec3b6039a460513e5f64f7c`;
- `tests/__init__.py` blob: `080243830be797f87d23b459dbfd12c142a9d49a`;
- `tests/real/__init__.py` blob: `23d73d7648ed14ef6857ee665784b87f57fde9f3`;
- inherited P7.C13 harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- inherited P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

Deterministic launcher authority:

- interpreter: `/usr/bin/python`;
- accepted interpreter version: CPython 3.12.3;
- exact `PYTHONPATH`: `/root/CodexControl/src:/root/CodexControl`.

Tracked worktree and index must be clean before any P7.C14 ledger reservation.

## Distinct successor replay authority

P7.C14 replay barrier is only:

`/root/.codexcontrol/p7c14-one-shot.json`

Before real execution this path MUST be absent. If it exists for any reason, do not delete, rename, repair, truncate, replace or bypass it. Stop and report:

`P7C14_ALREADY_CONSUMED_OR_RECOVERY_REQUIRED`

Once the P7.C14 ledger is successfully reserved, the P7.C14 run is permanently consumed regardless of PASS, FAIL, TIMEOUT, UNKNOWN, CONFIRMED_PENDING or exception. No retry is authorized.

The historical P7.C13 parent command and P7.C13 gate/token remain forbidden. The P7.C13 ledger is not P7.C14 replay authority.

## Out-of-band P7.C14 token

The raw token MUST NOT be committed or written to evidence.

Required raw-token SHA-256:

`dbec40568d5ced50b17449795c79b980b98289f9effb44d9114e8547be490c79`

Any mismatch means no run.

## Mandatory zero-effect pre-token launcher proof

Before setting the P7.C14 token, from the exact execution checkout and exact deterministic `PYTHONPATH`, perform read-only/zero-effect proofs:

1. exact HEAD/tree/blobs/package markers and tracked clean state;
2. `/usr/bin/python --version` is Python 3.12.3;
3. import-only smoke succeeds for `codex_control`, `tests`, `tests.real`, P7.C12, inherited P7.C13 harness and P7.C14 launcher;
4. import origins resolve to repository `/root/CodexControl/src` and `/root/CodexControl` authorities;
5. P7.C14 ledger remains absent after import smoke;
6. exact gate-disabled parent module invocation with all P7.C14 authorization variables unset exits finite disabled code `2`;
7. P7.C14 ledger remains absent after gate-disabled parent smoke;
8. no Codex/app-server/model/thread/Turn/approval/interrupt/delete effect occurs.

If any proof fails, stop before token export and before ledger reservation.

## Mandatory zero-effect exact source-bundle gate proof

After the raw token hash is verified and exact P7.C14 environment values are set, but before invoking the real parent, run one read-only source-bundle gate evaluation only. It must call P7.C14 source authority/gate functions and MUST NOT select or call the executor.

It must return PASS for exact token/HEAD/tree/launcher/inherited harness/matcher/package-marker/import-root/clean-state authority.

Immediately re-check that `/root/.codexcontrol/p7c14-one-shot.json` is still absent.

If the read-only source gate fails or the ledger appears, do not invoke the real parent.

## Exact environment authority

For the one real invocation provide exactly:

- `PYTHONPATH=/root/CodexControl/src:/root/CodexControl`;
- `P7C14_FUTURE_REAL_GATE=<raw out-of-band token>`;
- `P7C14_EXPECTED_HEAD=e4a906aa7112e61b072c12ba9ee0dcd4feee4ae1`;
- `P7C14_EXPECTED_TREE=7139a60357cae952c9f0da7b1c47d35cdd00b5bd`;
- `P7C14_EXPECTED_LAUNCHER_BLOB=fcce1352d581522b4c4ab0e5235d0b927d2eceb8`;
- `P7C14_EXPECTED_P7C13_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c`;
- `P7C14_EXPECTED_P7C12_MATCHER_BLOB=f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- `P7C14_EXPECTED_TESTS_INIT_BLOB=080243830be797f87d23b459dbfd12c142a9d49a`;
- `P7C14_EXPECTED_TESTS_REAL_INIT_BLOB=23d73d7648ed14ef6857ee665784b87f57fde9f3`.

No P7.C13 real gate/token may be set.

## Exact one-shot parent invocation

Invoke exactly once:

`/usr/bin/python -m tests.real.test_p7_c14_final_hard_delete_recovery --p7c14-real-run`

Do not invoke P7.C13 `--p7c13-real-run`.

Do not directly invoke the inherited child mode.

Do not use a wrapper to rerun after failure.

## Frozen real effect ceilings

The inherited accepted hard-delete implementation remains bounded to:

- new thread: 1;
- model/list: 1;
- thread/start: 1;
- thread/resume: 1;
- turn/start: 4;
- approval protocol responses: 1;
- ALLOW: 1;
- DENY on PASS: 0;
- turn/interrupt: 1;
- official thread/delete: 1;
- thread/read: 0;
- thread/list: 0;
- second child: 0;
- retry: 0;
- Telegram: 0.

P7.C14 source gate and ledger are distinct successor authority; the child hard-delete behavior remains the accepted inherited P7.C13 implementation.

## Required real path

The accepted path is:

1. P7.C14 exact source/import gate;
2. P7.C14 global one-shot ledger reserve;
3. inherited fresh run-owned boundaries and root-only boot authority;
4. one owned child/process group with deterministic repository import authority;
5. installed Codex authority;
6. one model catalog acquisition;
7. one fresh thread/start;
8. Turn 1 response-marker persistence;
9. owned runtime shutdown;
10. new generation and exact thread/resume;
11. Turn 2 remembered-marker proof;
12. Turn 3 C11 explicit escalation and immutable root-only wire authority;
13. accepted C12 strict matcher;
14. one protocol ALLOW response only;
15. Turn 3 completed and target metadata proof/cleanup;
16. distinct Turn 4 active/nonterminal proof, unexpected-request observer, one interrupt and post-join request classification;
17. runtime shutdown;
18. conclusive pre-delete physical oracle;
19. schema-v4 controller IDLE binding;
20. exactly one canonical `DialogueDeleteService.delete()`;
21. independent official lifecycle delete observation;
22. tombstone/live-binding/isolation/descendant/residual proof;
23. child runtime quiescence;
24. parent owned process-group quiescence;
25. terminal P7.C14 ledger update.

## PASS requirements

PASS requires all frozen inherited hard-delete acceptance gates, including:

- parent exit success;
- P7.C14 ledger state `COMPLETED`;
- child status `PASS` and verdict true;
- Turn 1 exact response-marker proof;
- restart/resume and Turn 2 exact memory proof;
- exactly one Turn-3 approval request;
- exactly one protocol response;
- ALLOW 1, DENY 0;
- C12 exact matcher result;
- Turn 3 completion and target proof;
- Turn 4 active proof;
- Turn 4 unexpected request count 0;
- one interrupt and definitive accepted terminal;
- conclusive pre-delete target observation;
- official delete `DELETE_CONFIRMED`;
- application delete `DELETED`;
- exact tombstone proof;
- no live controller binding;
- valid isolated envelope;
- isolated sqlite descendants 0;
- isolated logs descendants 0;
- all persistent/isolated target-thread and marker residuals 0;
- scan/proof errors 0;
- unrelated target-specific removal false;
- child runtime quiescent;
- parent process-group active 0, zombies 0, scan errors 0;
- effect ceilings obeyed exactly;
- second child 0;
- retry 0.

No weaker state may be called PASS.

## Non-PASS terminal handling

`DELETE_UNKNOWN` remains terminal UNKNOWN with no retry/read/list/manual persistent cleanup/finalization/tombstone inference.

Confirmed external delete with local storage proof pending remains `CONFIRMED_PENDING`, with no external retry.

Any pre-delete failure remains consumed FAIL after ledger reservation.

No outcome authorizes a second P7.C14 run.

## Sanitized post-run evidence

After the one-shot parent exits, do not rerun. Read only the P7.C14 ledger and uniquely correlated inherited boot/result/wire/journal authorities needed for classification. Do not publish raw thread IDs, Turn IDs, approval target, prompt/response, wire plaintext, raw root-only JSON or raw token.

Create exactly:

`docs/evidence/p7c14/P7C14_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-12.md`

Record safe hashes/classes/counts only, including source authority, token SHA only, parent exit, P7.C14 ledger state, child status/verdict, Turn classes, approval counts/class, interrupt count/class, official/application delete classes, residual counts, scan errors, runtime child quiescence, parent process-group counts, second-child/retry counts and final verdict.

Required final fields:

`P7C14_REAL_RUN_CONSUMED=YES`

`P7C14_REAL_RETRY_AUTHORIZED=NO`

`P7C14_REAL_PARENT_EXIT=<integer>`

`P7C14_REAL_LEDGER_STATE=<actual exact state>`

`P7C14_REAL_CHILD_STATUS=<actual exact class>`

`P7C14_REAL_OFFICIAL_DELETE=<actual exact class>`

`P7C14_REAL_APPLICATION_DELETE=<actual exact class>`

`P7C14_REAL_FINAL_VERDICT=<PASS|FAIL|UNKNOWN|CONFIRMED_PENDING|TIMEOUT>`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Commit only sanitized real P7.C14 evidence after the run to a dedicated real-evidence branch created from the accepted executable source. No source/harness/package-marker modification is allowed before or during execution.

Independent architect review is required after the one-shot result before P8 may start.
