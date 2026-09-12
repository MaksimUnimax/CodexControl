# P7.C13 final hard-delete acceptance harness preparation contract — 2026-09-12

Status: **FROZEN / ZERO REAL EFFECT / PREPARATION ONLY / NO REAL ALLOW / NO REAL DELETE**

## Purpose

P7.C13 prepares the final fresh one-shot real hard-delete acceptance harness after architect acceptance of P7.C12.

P7.C13 preparation does **not** start Codex, does not start app-server, does not create a real thread, does not send an approval response, does not interrupt a real turn and does not dispatch `thread/delete`.

A later architect review must accept the exact prepared harness before a separate one-shot execution contract may authorize any real effect.

## Accepted predecessor authority

P7.C12 final accepted candidate:

- final commit: `a5c66a778800d1c5ee5811d97d961fe0dccd677c`;
- final tree: `e6a46445d11d660a50891eabf412b01aef883fca`;
- strict matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`;
- P7.C12 evidence blob: `5c854e09d5ef3c22941c7927cd20a8777b0216e8`.

P7.C12 architect acceptance:

`docs/evidence/p7c12/P7C12_STRICT_APPROVAL_MATCHER_PREP_REPAIR2_ARCHITECT_ACCEPTANCE_2026-09-12.md`

Accepted production hard-delete architecture remains P7.C2/P7.C3/P7.C4 with P7.C5 fake acceptance.

Use as binding historical hard-delete oracle, except where later corrections below supersede it:

- `docs/evidence/p7c6/P7C6_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`;
- `docs/evidence/p7c6/P7C6_ARCHITECT_CONTRACT_CORRECTION_SHARED_HOME_2026-09-10.md`;
- `docs/evidence/p7c5/P7C5_ARCHITECT_ACCEPTANCE_2026-09-10.md`.

The shared-home correction / ADR-0045 takes precedence over the original C6 exclusive-home clauses.

## Exact preparation base

The executor must use a preparation branch from exact accepted P7.C12 candidate:

`a5c66a778800d1c5ee5811d97d961fe0dccd677c`

This is required because the accepted P7.C12 matcher is test-only and lives on that accepted candidate lineage.

The executor must separately fetch/read current architect `origin/main` for this contract and architect acceptance authority. Do not merge architect-main governance commits into the preparation branch merely to read them.

## Absolute zero-real-effect boundary

During P7.C13 preparation:

- real Codex process starts = 0;
- app-server starts = 0;
- `model/list` = 0;
- `thread/start/resume/read/list/delete` = 0;
- `turn/start/interrupt` = 0;
- approval responses = 0;
- ALLOW responses = 0;
- DENY responses = 0;
- Telegram = 0;
- process signals to real Codex = 0;
- real persistent-home mutation = 0;
- real isolated-root mutation = 0;
- real controller DB mutation = 0;
- real approval sentinel mutation = 0;
- historical P7.C6-P7.C12 retained-authority mutation = 0.

Do not create/set a real-run authorization environment variable during preparation.

Do not execute any historical one-shot real test.

Synthetic temporary fixtures used by offline tests are permitted only under test-owned temporary paths and must not impersonate retained real authority.

## Preparation implementation scope

P7.C13 is test-only preparation.

Allowed tracked changes:

- one new gated harness: `tests/real/test_p7_c13_final_hard_delete_acceptance.py`;
- optionally one new P7.C13-only helper under `tests/real/` if genuinely needed;
- one evidence file: `docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`.

Forbidden:

- `src/**` changes;
- P7.C6-P7.C12 historical test/evidence mutation;
- controller schema/migration changes;
- ADR/config/deployment/Telegram changes;
- CURRENT_WORK/ROADMAP changes by executor.

The existing P7.C12 matcher file is accepted authority and must not be edited in P7.C13.

## Installed/runtime authority for future real mode

The prepared future-real path must fail closed unless it can prove:

- executable `/usr/local/bin/codex`;
- exact version `codex-cli 0.144.6`;
- exact generated app-server schema aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

Use the accepted `CodexRuntimeManager`/installed-authority path.

Future real routing is fixed:

- persistent authenticated `CODEX_HOME=/root/.codex_second`;
- `CODEX_SQLITE_HOME=<fresh P7.C13 isolated root>/sqlite`;
- `sqlite_home=<same>`;
- `log_dir=<fresh P7.C13 isolated root>/logs`;
- `history.persistence=none`.

The persistent home is **shared authenticated authority**. Other processes using `/root/.codex_second` are not a failure by themselves and must never be killed/signalled for exclusivity.

Future quiescence/destructive ownership applies only to the exact P7.C13-owned isolated root, controller DB, working directory, one-shot ledger and app-server children.

## Read-only boundary preflight for future real mode

The harness must prepare fail-closed read-only checks for:

- mount/alias ambiguity via `/proc/self/mountinfo` and filesystem identity;
- persistent home path safety;
- fresh isolated-root parent/root safety;
- controller DB parent/path safety;
- repository boundary safety;
- exact run-owned working directory and approval-target parent;
- external users of P7.C13-owned destructive boundaries.

No privileged mount/namespace mutation is authorized.

No unrelated process termination is authorized.

## Future one-shot effect budget — frozen but NOT YET authorized

The prepared harness must enforce a single future real attempt with a hard maximum of:

- new real threads: `1`;
- `model/list`: `1`;
- `thread/start`: `1`;
- `thread/resume`: `1` after deliberate owned runtime-generation restart;
- `turn/start`: `4`;
- supported approval responses: maximum `1` total;
- successful ALLOW responses: maximum `1` total;
- `turn/interrupt`: maximum `1`;
- official `thread/delete`: maximum `1`;
- `thread/read`: `0`;
- `thread/list`: `0`;
- Telegram: `0`;
- second child/run retry: `0`.

A later real execution is permanently consumed once its real command begins, regardless of outcome. Preparation must include one-shot latch/recovery semantics but must not create the real latch now.

## Future Turn 1 — persistence marker establishment

The future real harness will create one fresh disposable thread in a fresh run-owned working directory and require `START_CONFIRMED`.

Generate high-entropy non-secret markers in memory; Git evidence may contain only hashes/classes/counts.

Turn 1 must produce a bounded deterministic completion that establishes a memory marker and a response marker.

Require definitive completed terminal output.

Then fully stop/reap only the owned app-server generation.

## Runtime restart / resume

Reacquire a new accepted generation using the same persistent home and exact P7.C13 isolated root.

Resume the exact fresh P7.C13 binding once and require `RESUME_CONFIRMED`.

No retained historical thread may be resumed.

## Future Turn 2 — persisted context proof

Turn 2 asks for the Turn-1 memory marker and must definitively complete with the expected remembered value.

This proves same-thread persistence across app-server generations under corrected storage routing.

## Future Turn 3 — exact approval ALLOW proof

Approval and interrupt are deliberately separated.

Create one fresh run-owned approval target as a direct child of `/root`, with a unique name such as a P7.C13-specific random target. It must be:

- outside `/tmp` and `$TMPDIR`;
- outside cwd/workdir/repository;
- outside persistent `CODEX_HOME`;
- outside isolated state/controller roots;
- outside `/root/.codexcontrol` directory;
- absent before the turn.

The Turn-3 stimulus must request first-and-only shell execution of exactly:

`touch <exact P7.C13 approval target>`

with explicit `sandbox_permissions=require_escalated` and no default attempt first, no alternate tool/path/network command and no retry.

The harness must capture the authoritative command request through the accepted P7.C11 root-only wire/correlation pattern and classify it through the accepted P7.C12 strict matcher.

The live approval operator may return ALLOW **only** if all of the following are true:

- this is the first and only approval response budget slot;
- exact owned thread/Turn/cwd identity is established;
- one authoritative wire capture exists for the same local sequence/request;
- command SHA binding is exact;
- the P7.C12 matcher result is exactly `MATCH_EXACT_P7_APPROVAL_COMMAND`;
- target is the exact run-owned target and was absent immediately before approval;
- no prior approval response was sent.

Any non-match or ambiguity must fail closed. The future harness may send at most one DENY instead of ALLOW on the first unexpected owned approval if that is necessary to terminate safely, but success requires exactly one ALLOW and zero DENY.

Turn 3 success additionally requires:

- exactly one approval request;
- exactly one confirmed ALLOW response;
- definitive Turn completion;
- exact approval target exists afterward with safe run-owned metadata;
- no alternate command/tool request.

The run-owned approval target may then be removed by exact-path cleanup; its existence is an approval proof, not hard-delete storage authority.

## Future Turn 4 — independent interrupt proof

Turn 4 must not reuse the Turn-3 approval command.

Use the accepted bounded long-running no-write stimulus from the C6 continuation design: request exactly one `sleep 120` shell command and no other work.

Success requires:

- Turn 4 start confirmed on the exact same thread binding;
- no approval response is sent for Turn 4;
- no unexpected second approval request is accepted;
- the turn remains nonterminal long enough to establish an active interrupt target;
- exactly one accepted P1.8 `turn/interrupt` is dispatched for the exact Turn-4 binding;
- definitive interrupted/failed terminal result, never UNKNOWN;
- no write sentinel is used by Turn 4.

If an unexpected approval request appears after the Turn-3 ALLOW, do not send a second approval response merely to keep the test moving. Fail closed, use only the already-budgeted interrupt if safe/needed for the exact owned Turn, then stop the acceptance path.

## Pre-delete physical observation

Only after all four future-turn gates succeed, fully stop/reap the owned runtime before storage measurement.

Prepare bounded no-follow exact-byte scanners/oracles for target-specific dialogue-bearing families:

Persistent shared-home target families:

- `CODEX_HOME/sessions/**`;
- optional `CODEX_HOME/history.jsonl`.

Isolated run-owned families:

- every regular file under isolated `sqlite/**`;
- every regular file under isolated `logs/**`.

Search exact bytes for:

- exact target thread ID;
- all known P7.C13 synthetic dialogue markers.

Git evidence stores only hashes/counts/family classes, never matched content.

Pre-delete proof is conclusive only if at least one exact target thread-ID or known material-marker occurrence is physically observed in a dialogue-bearing family.

Because the persistent home is shared, unrelated background changes are not blockers by themselves. Do not require global shared-home metadata stability. Record unrelated baselines only where attribution is target-specific and safe.

## Synthetic controller binding

After turns and pre-delete observation, create a fresh schema-v4 P7.C13-owned controller DB at the exact protected controller path and persist one canonical IDLE dialogue bound to the exact real P7.C13 thread/profile.

No active turn job may remain.

Use production `DialogueDeleteService` with:

- real P1.9 `CodexThreadLifecycleAdapter`;
- accepted C4 `DeleteStorageCleanupCoordinator`;
- accepted real runtime manager;
- accepted isolated state authority.

The harness must exercise the complete corrected application chain. Direct raw `thread/delete` followed by manual cleanup is forbidden.

## One official delete only

The future harness may call `DialogueDeleteService.delete()` once for the exact IDLE P7.C13 dialogue.

Instrument only enough to record safe official P1.9 and application outcome classes.

Required PASS chain remains:

`P1.9 DELETE_CONFIRMED -> durable DELETE_CONFIRMED_PENDING_STORAGE -> reserve -> shutdown/reap -> quiescence -> isolated payload reset -> persistent exact-thread scan -> finalize_confirmed -> tombstone -> release`.

Exactly one official `thread/delete` dispatch is permitted.

`DELETE_UNKNOWN` is terminal: no retry, no read/list, no inference, no manual persistent cleanup. C4 UNKNOWN local isolated containment may occur only under accepted production semantics.

If official delete is confirmed but local proof/finalization is incomplete, state remains `DELETE_CONFIRMED_PENDING_STORAGE`; never redispatch external delete.

## Post-delete acceptance oracle

A later real PASS must require all of:

- official P1.9 exactly `DELETE_CONFIRMED`;
- application result exactly `DELETED`;
- exact bounded tombstone present;
- no live controller dialogue/binding remains;
- isolated ownership envelope valid;
- zero descendants under isolated `sqlite/`;
- zero descendants under isolated `logs/`;
- zero target thread-ID residual in persistent sessions/history;
- zero known P7.C13 material-marker residual in persistent sessions/history;
- zero target thread/marker residual in isolated families;
- zero scan/proof errors;
- no P7.C13-owned app-server child alive;
- P7.C13 process group quiescent;
- exact run effect budget respected;
- unrelated shared-home processes not terminated;
- no target-specific evidence that unrelated persistent material was removed.

Any target residual or inconclusive target scan is a hard-delete acceptance blocker.

Marker-only residual remains an independent acceptance-oracle failure and does not authorize widening production scanner behavior inside the run.

## Failure / recovery semantics

Any future real failure, timeout, signal termination or ambiguity is terminal for that one-shot run.

Never automatically:

- rerun the P7.C13 real harness;
- start a second thread;
- resume twice;
- send a second approval response;
- interrupt twice;
- delete twice;
- use `thread/read` or `thread/list` to infer success;
- manually remove persistent Codex session/history artifacts;
- delete/rewrite the latch/recovery record to manufacture PASS.

The future real harness must create a root-only one-shot/recovery ledger before the first thread effect. On incomplete/UNKNOWN/confirmed-pending outcomes it must preserve exact local recovery identity outside Git.

It may clean only exact run-owned temporary workdir/approval sentinel and owned child processes according to safe failure handling; it must never signal unrelated shared-home processes.

## Parent watchdog / process-group safety

Prepare a dedicated parent/child real executor pattern with a bounded watchdog.

Future real execution must prove:

- exactly one child process for the real harness;
- no second child/retry;
- dedicated process group/session;
- parent can terminalize only its owned child group on timeout;
- unrelated processes are never signalled;
- PASS requires child result valid and owned process group quiescent.

Preparation tests must cover completed, timeout, residual-process and cancellation/error classifications synthetically without starting Codex.

## Real trigger must remain disabled in preparation

The new P7.C13 harness must skip/fail closed under ordinary test discovery and ordinary direct execution unless a future architect contract supplies all exact one-shot values, including expected HEAD/tree and one-time authorization token.

Preparation must verify that no currently available environment value can accidentally satisfy the future-real gate.

Do not invent/set the future authorization value during P7.C13 preparation.

## Required offline proof matrix

At minimum test synthetically:

1. exact Turn-3 approval request + accepted P7.C12 matcher => one ALLOW decision candidate;
2. every matcher non-MATCH => no ALLOW;
3. second approval request after budget consumed => no second response / fail closed;
4. wrong thread/Turn/cwd/local sequence/wire SHA/target => no ALLOW;
5. target already present before approval => no ALLOW;
6. Turn-3 ALLOW completion requires target existence;
7. Turn-4 unexpected approval cannot become a second ALLOW/response;
8. Turn-4 interrupt exactly once and only exact active binding;
9. interrupt UNKNOWN => fail;
10. delete path unreachable unless persistence, approval, interrupt, pre-delete observation and IDLE binding gates all pass;
11. `DELETE_UNKNOWN` => zero retry/read/list/finalize/tombstone;
12. confirmed-pending local failure => zero external delete retry;
13. confirmed success follows production C4 finalization/tombstone chain;
14. target thread residual => fail;
15. marker-only residual => acceptance-oracle fail;
16. isolated residual => fail;
17. scan/proof error => fail;
18. unrelated shared-home process presence alone => not fail and never signalled;
19. external user of exact P7.C13 isolated/controller boundary => fail before destructive cleanup;
20. one-shot/recovery latch blocks accidental second invocation;
21. real gate unset => no Codex/runtime/RPC reachable;
22. watchdog second-child/retry budget => fail closed.

Reuse accepted C5 fake hard-delete seams where practical. Do not copy production delete logic into the harness.

## Validation

Run:

- focused P7.C13 offline/preparation suite;
- P7.C12 matcher focused suite;
- relevant C2/C3/C4/C5 fake/integration regressions;
- complete non-real regression with all real authorization gates unset;
- compileall;
- `git diff --check`;
- leakage scan.

Historical consumed-latch static/preflight tests may be reported separately; never delete/rewrite retained latches to make them green.

No real Codex command is authorized during this validation.

## Security / evidence boundary

Committed preparation source/evidence must contain zero:

- raw retained thread IDs;
- raw retained target paths from prior runs;
- raw wire commands from prior runs;
- raw prompts/responses/tool output;
- credentials/tokens/auth data;
- raw root-only recovery JSON.

Synthetic obvious fixture values are permitted.

The future real harness may hold raw current-run values only in root-only memory/files outside Git; committed real evidence later must contain only hashes/classes/counts.

## Required preparation evidence

Create:

`docs/evidence/p7c13/P7C13_FINAL_HARD_DELETE_ACCEPTANCE_PREP_EVIDENCE_2026-09-12.md`

Record at minimum:

- exact accepted P7.C12 base SHA/tree/matcher blob;
- harness blob;
- helper blob if any;
- future-real gate status `DISABLED`;
- frozen effect-budget assertions;
- shared-home correction carried forward;
- Turn 1/2 persistence-plan tests;
- Turn-3 matcher/ALLOW budget tests;
- Turn-4 interrupt/no-second-approval tests;
- pre-delete physical-oracle tests;
- schema-v4 controller/delete-service chain tests;
- DELETE_UNKNOWN/confirmed-pending/confirmed-success matrices;
- post-delete target-marker/thread/isolated oracle tests;
- one-shot/watchdog tests;
- focused/regression counts;
- compileall/diff/leakage results;
- zero-real-effect accounting.

Required final lines:

`P7C13_PREP_HARNESS_READY=YES|NO`

`P7C13_PREP_APPROVAL_MATCHER_GATE=PASS|FAIL`

`P7C13_PREP_INTERRUPT_GATE=PASS|FAIL`

`P7C13_PREP_DELETE_CHAIN_GATE=PASS|FAIL`

`P7C13_PREP_POST_DELETE_ORACLE=PASS|FAIL`

`P7C13_PREP_ONE_SHOT_GATE=PASS|FAIL`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`

## Publication

Use a preparation branch from exact accepted P7.C12 candidate `a5c66a778800d1c5ee5811d97d961fe0dccd677c`.

Commit clearly and push normally, no force.

Remote readback must prove:

- exact base lineage;
- only allowed P7.C13 test/evidence paths changed;
- no `src/**`;
- no P7.C6-P7.C12 historical mutation;
- no executor mutation of architect `main`.

## Acceptance consequence

Successful executor preparation does not authorize any real effect.

Independent architect review must inspect the exact harness and evidence. Only after that review may architect freeze a separate one-shot P7.C13 real execution contract with exact HEAD/tree/harness blob and exact authorization token.

P8/P9 remain blocked until the subsequent real hard-delete acceptance itself is independently architect accepted.
