# Current work authority

Date: 2026-09-07

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; isolated real-Codex T3 remains deferred to P7.
- P2 historical final acceptance: `9db97f0dda109b4d0c0ecfa5f167733905df2766`; P2.C1 accepted at `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`.
- Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- P3.1 accepted at `9e0a86b311bb63d6a36a4641cb588321987e1550`; full suite 543.
- P3.2 accepted at `c484c56db007569170363b3d08c24766148c3e30`; full suite 566.
- P3.3 accepted at `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`; full suite 596.
- P3.4 accepted after one repair at `6460a449f861b7b86ab664e5ff877c108715082d`; full suite 633.
- P3.5 hard-delete/final-recovery application layer is architect-accepted after four repair reviews at `6145d262787465ac6b4a17327114211cd86e8104`; final full suite authority 671.
- P3.5 acceptance authority: `docs/evidence/p3/P3_5_ARCHITECT_ACCEPTANCE_2026-09-07.md`.
- ADR-0026/0027/0028/0029/0030/0031 remain binding accepted P3 authority.
- P3 dialogue application service is complete at the fake/application boundary.

## Accepted P3 application boundary

Existing dialogue prompt:

`duplicate/static -> existing-dialogue preflight -> claim_ingress -> claim_turn -> CODEX_STARTING -> P1 turn/start -> CODEX_RUNNING -> P1 wait -> finish_codex`

No-dialogue first prompt:

`duplicate/static -> settings/model/workdir preflight -> tombstone guard -> guarded CREATING -> first JOB/RECEIVED/INPUT -> thread/start -> confirm IDLE -> same admitted job -> accepted turn runner`

Settings selection is linearized with first-dialogue creation. Already-admitted profile/model/effort snapshots remain immutable.

Interrupt:

`exact version/job preflight -> exact ActiveTurnRegistry binding -> durable INTERRUPTING -> P1.8 interrupt/reconcile -> exact restore/terminal outcome`

P3.4 requires exact in-memory `TurnBinding` identity, commits INTERRUPTING before P1 interrupt, never blindly retries, reconciles natural-terminal races, and makes pre-existing INTERRUPTING restart recovery zero-P1/UNKNOWN.

Hard delete:

`exact request/tombstone/version preflight -> canonical state validation -> optional exact P3.4 interrupt/quiescence -> P2.5 DELETE_PENDING -> P2.5 DELETING -> one P1.9 thread/delete -> confirmed finalize / DELETE_UNKNOWN / ERROR`

P3.5 never blind-retries delete. Current DELETE_PENDING may continue only from a fresh exact-version explicit request. DELETING and DELETE_UNKNOWN never redispatch. Only exact P1.9 DELETE_CONFIRMED with exact supplied binding identity permits local purge+tombstone.

Running-delete composition captures and arms the exact active registry generation before P3.4. After a definitive exact P3.4 terminal result, P3.5 waits for the original admitted runner to retire its exact lease. Any replacement publication before watcher completion supersedes the old watch, including transient replacements that retire before the old watch resumes. Registry bookkeeping is bounded to active entries plus live watchers; completed turns leave no historical binding archive.

Final startup recovery:

- CREATING -> CREATE_UNKNOWN / CODEX_AMBIGUOUS, zero P1;
- INTERRUPTING -> owning job UNKNOWN + dialogue TURN_UNKNOWN / CODEX_AMBIGUOUS, zero P1;
- DELETING -> DELETE_UNKNOWN / DELETE_UNKNOWN, zero P1;
- DELETE_PENDING -> held unchanged, NO_ACTION;
- IDLE + exact stranded RECEIVED -> job FAILED / CODEX_PROCESS, dialogue remains IDLE;
- TURN_RUNNING + exact CLAIMED -> job FAILED / CODEX_PROCESS, dialogue IDLE;
- TURN_RUNNING + CODEX_STARTING/CODEX_RUNNING -> job UNKNOWN + dialogue TURN_UNKNOWN / CODEX_AMBIGUOUS;
- already terminal/unknown/error states -> NO_ACTION only when the full persisted shape is canonical.

`DialogueRecoveryService.recover_startup()` has no P1/Codex/Telegram port and never replays thread/start, turn/start, interrupt, delete, output generation or delayed prompt work.

## P3 final acceptance facts

P3.5 final focused counts:

- unit: 12;
- integration: 25;
- final fake/application acceptance: 1.

Accepted pre-P3.5 full count was 633. Final P3 full suite authority is:

`633 + 12 + 25 + 1 = 671`.

Executor full discovery reported 671 passing tests and all required accepted P3/P2/P1 focused regressions at their frozen counts. GitHub has no CI/status checks attached to the accepted implementation SHA; architect acceptance is based on exact GitHub code/test/evidence review plus executor regression evidence, consistent with P3.4 acceptance.

Known P1.6 pending-task warning remains pre-existing.

## P3 split

- **P3.1** — DONE, accepted `9e0a86b311bb63d6a36a4641cb588321987e1550`.
- **P3.2** — DONE, accepted `c484c56db007569170363b3d08c24766148c3e30`.
- **P3.3** — DONE, accepted `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`.
- **P3.4** — DONE, accepted `6460a449f861b7b86ab664e5ff877c108715082d`.
- **P3.5** — DONE, accepted `6145d262787465ac6b4a17327114211cd86e8104`.
- **P3** — COMPLETE.

## Next architect phase

P4 — Telegram private management.

P4 implementation is NOT authorized by this file alone. Before Codex execution, the architect must separately freeze the P4 slice against the accepted P3.5/main authority, including exact private authorization edge, panel/callback contracts, settings/status/delete/interrupt behavior, Telegram ambiguity/replay boundaries, storage interactions, tests and execution scope.

No P4 production implementation has started.

## Later roadmap boundaries

P5 remains Telegram group/fleet routing. P6 remains response delivery/full local orchestration. P7 remains isolated real-Codex acceptance including empirical hard-delete storage measurement. P8+ remain deployment/live/multi-server/final-security phases.

## Execution authority

Codex must not self-start work from this document.

No P4 implementation may begin until a separate architect-owned P4 authority record, issue/branch/base and explicit executor prompt are created.
