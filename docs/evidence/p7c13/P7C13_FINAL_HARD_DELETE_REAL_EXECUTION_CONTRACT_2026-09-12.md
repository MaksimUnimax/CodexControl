# P7.C13 final hard-delete acceptance — one-shot real execution contract — 2026-09-12

Status: **FROZEN / ONE-SHOT REAL EXECUTION AUTHORIZED ONLY UNDER THIS EXACT CONTRACT**

## Purpose

This contract authorizes exactly one real P7.C13 acceptance run using the already accepted harness. It authorizes no implementation change, retry, second child, second approval response, second delete, P8, or P9.

## Exact executable source authority

The real run MUST execute from exactly:

- commit: `a347a72bdc8235e31ff6165ca3dd830c1adae9e5`;
- tree: `0d4fef93c99a57fd93a2065280555c5cb06104c3`;
- harness blob: `5a1fe8e32cd985b1e1845d73266211632e33950c`;
- preparation evidence blob: `64d3f41313d0b001538cf51e57df231f40394c09`;
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`.

The accepted harness path is:

`tests/real/test_p7_c13_final_hard_delete_acceptance.py`

Tracked worktree and index must be clean. Untracked `tests/real/__init__.py` is tolerated if unchanged and unstaged.

## Out-of-band authorization token

The raw one-shot token MUST NOT be committed to Git.

Architect-authorized raw token is delivered out of band. Its required SHA-256 is:

`d658b7d3b283309b45e6002923280b767cdc86c79c8ee786e4a4291c92bf1914`

Executor must verify the raw token SHA-256 before exporting it. Any mismatch means no run.

## Permanent consumption semantics

The real run uses global root-only one-shot ledger:

`/root/.codexcontrol/p7c13-one-shot.json`

Before execution, this path MUST be absent. If it exists for any reason, do not delete, rename, replace, truncate, repair or bypass it. Stop and report `P7C13_ALREADY_CONSUMED_OR_RECOVERY_REQUIRED`.

Once the real command begins and the ledger is successfully reserved, the P7.C13 run is permanently consumed regardless of PASS, FAIL, TIMEOUT, UNKNOWN or CONFIRMED_PENDING.

No retry is authorized.

## Read-only pre-execution checks

Before the one-shot command, executor may perform only read-only checks necessary to prove exact authority, including:

- fetch remote refs;
- exact checkout/HEAD/tree/blob verification;
- tracked worktree/index clean proof;
- accepted matcher blob proof;
- global ledger absence proof;
- `/usr/local/bin/codex --version` exactly `codex-cli 0.144.6`;
- schema authority exactly `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466` using the accepted local capability authority;
- `/root/.codex_second` and `/root/.codexcontrol` existence/ownership/mode read-only checks.

Do not start app-server/model/thread/Turn during these checks.

If any pre-execution check fails, do not consume the ledger and do not run.

## Exact environment authorization

For the one real parent invocation export exactly:

- `P7C13_FUTURE_REAL_GATE=<raw out-of-band token>`;
- `P7C13_EXPECTED_HEAD=a347a72bdc8235e31ff6165ca3dd830c1adae9e5`;
- `P7C13_EXPECTED_TREE=0d4fef93c99a57fd93a2065280555c5cb06104c3`;
- `P7C13_EXPECTED_HARNESS_BLOB=5a1fe8e32cd985b1e1845d73266211632e33950c`.

No other authorization token is accepted by this architect contract.

## Exact one-shot invocation

Invoke exactly once:

`python -m tests.real.test_p7_c13_final_hard_delete_acceptance --p7c13-real-run`

Do not invoke the child directly.

Do not use an ad-hoc Python wrapper.

Do not rerun the parent after any result.

## Frozen real effect ceilings

The accepted harness must enforce:

- new threads: 1;
- model/list: 1;
- thread/start: 1;
- thread/resume: 1;
- turn/start: 4;
- approval protocol responses: 1;
- ALLOW responses: 1;
- DENY responses on PASS: 0;
- turn/interrupt: 1;
- official thread/delete: 1;
- thread/read: 0;
- thread/list: 0;
- second child: 0;
- real retry: 0;
- Telegram: 0.

## Required real path

The accepted harness must execute the previously frozen flow:

1. source gate;
2. permanent one-shot ledger reserve;
3. fresh run-owned boundaries and root-only boot authority;
4. one owned child/process group;
5. installed Codex authority;
6. one model catalog acquisition;
7. one fresh thread/start;
8. Turn 1 response marker persistence;
9. owned runtime shutdown;
10. new generation + exact thread/resume;
11. Turn 2 remembered marker proof;
12. Turn 3 C11 explicit escalation and root-only wire authority;
13. accepted C12 strict matcher;
14. one protocol ALLOW response only;
15. Turn 3 completed + exact target metadata proof/cleanup;
16. distinct Turn 4 `sleep 120` active proof, unexpected-request observer, one interrupt, definitive failed/interrupted terminal;
17. runtime shutdown;
18. conclusive pre-delete physical target oracle;
19. fresh schema-v4 controller IDLE binding;
20. exactly one canonical `DialogueDeleteService.delete()`;
21. independent official lifecycle delete observation;
22. real tombstone/live-binding/isolation/descendant/residual oracle;
23. child runtime quiescence;
24. parent exact process-group quiescence;
25. terminal one-shot ledger update.

## PASS requirements

PASS requires all of the following, with no inference from a weaker state:

- parent command exit success;
- ledger terminal state `COMPLETED`;
- strict final child result `status=PASS`, `verdict=true`;
- Turn 1 completed with exact response marker;
- restart/resume and Turn 2 exact memory proof;
- exactly one accepted Turn-3 approval request;
- exactly one protocol response;
- ALLOW count 1, DENY count 0;
- C12 matcher exact match;
- Turn 3 completed and exact target proof passed;
- Turn 4 active proof passed;
- Turn 4 unexpected request count 0;
- exactly one interrupt and definitive accepted terminal;
- conclusive pre-delete target material observed;
- official lifecycle status `DELETE_CONFIRMED`;
- application status `DELETED`;
- exact tombstone proof;
- no live controller binding;
- valid isolated envelope;
- isolated sqlite descendants 0;
- isolated logs descendants 0;
- persistent target thread content residual 0;
- persistent target filename residual 0;
- persistent target directory residual 0;
- persistent marker residual 0;
- isolated thread residual 0;
- isolated marker residual 0;
- scan/proof errors 0;
- unrelated target-specific removal detected false;
- child runtime quiescent;
- parent process-group active 0;
- parent process-group zombies 0;
- parent process-group scan errors 0;
- all effect ceilings exact.

## Non-PASS terminal handling

If official delete is `DELETE_UNKNOWN`, preserve `UNKNOWN`; do not retry, read, list, manually clean persistent authority, finalize or tombstone.

If official delete is confirmed but local storage proof remains pending, preserve `CONFIRMED_PENDING`; do not externally retry.

Any ordinary failure is terminal consumed `FAILED`.

Timeout/nonconvergence is terminal consumed. No automatic second child or rerun is permitted.

## Post-run evidence

After the one-shot process exits, executor may perform read-only inspection of the P7.C13 root-only ledger/boot/result/wire/journal authorities and must publish only sanitized hashes/classes/counts.

Never publish raw:

- thread ID;
- Turn IDs;
- approval target path;
- raw prompts/responses;
- raw wire command authority;
- raw root-only JSON;
- credentials or authorization token.

Create a sanitized real-execution evidence file:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_REAL_ACCEPTANCE_EVIDENCE_2026-09-12.md`

The evidence must state the exact source authority, parent exit class, ledger terminal state, child-result class, effect counts, safe Turn classes, approval/interrupt/delete classes, residual counts, quiescence counts and final verdict.

If the run is non-PASS, publish the safe terminal class and STOP. Do not retry.

## Publication

Sanitized post-run evidence must be committed and pushed to:

`real-p7-c13-final-hard-delete-acceptance-2026-09-12`

No source implementation changes are authorized on that branch.

## Authorization

`P7C13_PREP_ARCHITECT_ACCEPTED=YES`

`P7C13_ONE_SHOT_REAL_EXECUTION_AUTHORIZED=YES`

`P7C13_ONE_SHOT_REAL_ALLOW_AUTHORIZED=YES`

`P7C13_ONE_SHOT_HARD_DELETE_EXECUTION_AUTHORIZED=YES`

`P7C13_REAL_RETRY_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
