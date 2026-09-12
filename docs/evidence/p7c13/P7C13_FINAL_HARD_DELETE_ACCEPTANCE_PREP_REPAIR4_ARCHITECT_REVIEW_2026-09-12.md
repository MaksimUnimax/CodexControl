# P7.C13 preparation Repair-4 — architect review — 2026-09-12

Status: **REWORK_REQUIRED / TWO NARROW REMAINING BLOCKERS / NO REAL AUTHORIZATION**

## Candidate reviewed

- branch: `prep-p7-c13-final-hard-delete-acceptance-repair4-2026-09-12`
- commit: `86aa1b7b139b7db3d7d1ab8ed725c4cb25e5562d`
- tree: `2968187b6300e1ed03e336340aa906c199819d48`
- harness blob: `61853860ed0955df6119edb288d22573299cd1b3`
- evidence blob: `fe1d2df4b360c126b2d6d4b5d488caa9d83fbf51`
- accepted P7.C12 matcher blob: `f5ccefd00f4b3cd4c6aebaa89ec6c15132af67a1`

Lineage and tracked scope are accepted: exact Repair-3 parent, one linear commit, only the P7.C13 harness and evidence changed, no `src/**` or historical P7.C6–P7.C12 mutation.

## Accepted Repair-4 material

Independent source review accepts the following material and Repair-5 must preserve it:

- tracked worktree + index source gate;
- valid shared-home / isolated-root / controller-root topology;
- fresh private `0700` workdir;
- finite named internal waits and 670-second parent watchdog authority;
- exact owned-PGID active/zombie/error observation;
- C11-shaped explicit escalation stimulus;
- run-owned root-only immutable wire authority plus separate approval recovery journal;
- request ordinal and `local_sequence` as separate facts;
- actual kind/thread/Turn/cwd/target/wire correlation before the immutable P7.C12 matcher;
- one protocol response route with total-response/ALLOW accounting;
- Turn-4 bounded nonterminal observation before interrupt;
- independent official P1.9 delete observation;
- real schema-v4/tombstone/live-binding proof;
- derived isolated envelope/descendant and target-material residual proof;
- UNKNOWN and CONFIRMED_PENDING terminal consumed classes;
- separate child runtime quiescence and parent OS-process-group quiescence;
- unified Repair-4 child-result authority.

## Blocker A — repository/controller-root users are incorrectly classified as destructive-boundary users

`ProductionRealChildOrchestrator.run_async()` calls `production_read_only_boundary_preflight()` from the real child before authenticated business RPCs.

`_process_users_for_boundaries()` scans other processes' cwd/fds, skipping only the current child PID. `production_read_only_boundary_preflight()` then rejects every nonzero external-user count except `persistent_home`.

That is over-broad.

The future parent process remains alive while waiting for the one watchdog child and inherits/runs from the repository checkout required to execute the module. Therefore the child can observe the parent process cwd under the repository authority. Under the Repair-4 predicate, a nonzero `repository` user is a blocker even though the repository is read-only source authority, not a P7.C13 destructive boundary.

This can consume the global O_EXCL ledger and then fail before `thread/start`, making the one-shot permanently unusable for an expected parent-owned/source-authority condition.

Frozen semantics require blocking external users of the exact P7.C13-owned destructive boundaries, not ordinary users of the shared/read-only source authorities.

Repair-5 must classify boundaries explicitly:

- external users allowed/reported, not blocked: `persistent_home`, `repository`, `controller_root`;
- external users block: exact run-owned destructive authorities including `isolated_root`, `isolated_sqlite`, `isolated_logs`, `controller_db`, `workdir`, `approval_target`, `ledger`, `boot`, and `result`.

Mount/alias/ownership checks still apply to every boundary. This correction must not weaken physical-alias or mount checks.

## Blocker B — production Turn 4 has no unexpected-approval observation

The frozen Repair-4 contract states:

> Turn-4 approval requests receive no second response. Any such request makes acceptance non-PASS.

Repair-4 correctly proves Turn 4 is nonterminal for a bounded active window and then performs one exact interrupt. However the production Turn-4 path owns only the terminal waiter; it does not own/observe the protocol server-request queue during Turn 4.

After the single successful Turn-3 response, an unexpected Turn-4 approval request could therefore remain queued while the harness interrupts Turn 4 and continues toward delete. No second response would be sent, but the required **detection -> non-PASS** fact would be missing.

Repair-5 must add one bounded, owned, no-response unexpected-server-request observer for Turn 4. It must remain active from Turn-4 start through active proof and interrupt/terminal convergence.

Rules:

- any unexpected server request observed during Turn 4 makes the run non-PASS;
- never send a second approval response;
- the already consumed Turn-3 total-response/ALLOW slots remain `1/1`;
- if an unexpected request is observed while Turn 4 is still active, the one permitted interrupt may be used only to terminate the exact owned Turn safely, after which the child fails before controller/delete eligibility;
- request/terminal observer tasks must be finitely owned and joined/cancelled; no detached waiter;
- same-tick request/terminal facts fail closed;
- no delete dispatch after an unexpected Turn-4 request.

## Evidence wording correction

Repair-4 evidence reports final validation from the executor handoff, but some prose still says compileall/diff reruns were required after evidence update. Repair-5 evidence must record the actual final post-edit validation results, not pending wording.

## Architect verdict

`P7C13_REPAIR4_ARCHITECT_ACCEPTANCE=REWORK_REQUIRED`

`P7C13_REPAIR4_ACCEPTED_MATERIAL=PRESERVE`

`P7C13_REPAIR5_SCOPE=EXTERNAL_USER_CLASSIFICATION_PLUS_TURN4_UNEXPECTED_REQUEST_GATE`

`P7C13_REAL_EXECUTION_AUTHORIZED=NO`

`P7C13_REAL_ALLOW_AUTHORIZED=NO`

`P7C13_HARD_DELETE_EXECUTION_AUTHORIZED=NO`

`P8_STARTED=NO`

`P9_STARTED=NO`
