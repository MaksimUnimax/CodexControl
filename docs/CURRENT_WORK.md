# Current work authority

Date: 2026-09-06

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`; app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1 is complete through accepted P1.10 T0/T1/T2; real-Codex T3 remains deferred to P7.
- P2.1 accepted: `61301fd25ff7253693f367664ce99e13dfc88446`.
- P2.2 accepted: `5187c080a7188a59989013defe7d07075662d007`.
- P2.3 accepted: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
- P2.4a accepted: `ca5b5cc19ac9278377b96abec46c523603b2ff47`.
- P2.4b accepted: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`.
- P2.5 accepted: `87ef37cf245d79f6d20b507b13c0f36014c1580f`.
- P2.6a accepted: `e6f59739b3091d00894d3434abb5a99e2af72885`.
- P2.6b/final P2 accepted after one proof-only repair: `9db97f0dda109b4d0c0ecfa5f167733905df2766`.
- Final P2 full suite: `500` passing tests.
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- `docs/evidence/p2/P2_FINAL_ARCHITECT_ACCEPTANCE_2026-09-06.md` is final P2 architect acceptance authority.
- ADR-0017..0025 remain accepted P2 authority.
- ADR-0026 is binding P3.1 application-orchestration authority.

## Final P2 acceptance facts
- P2.6b changed tests/evidence only; accepted production source remained byte-unchanged from the P2.6a architect base.
- Restart-SLEEP, durable update/callback dedupe, CREATING/turn/delivery/approval/delete/retention/error restart states and no-blind-effect replay were proven on temporary SQLite databases.
- Same update remains exactly one job/INPUT/ingress; a second outstanding prompt is not queued.
- SENDING and DELIVERY_UNKNOWN cannot create a blind resend; DELETE_UNKNOWN has no retry/reconcile storage surface.
- Confirmed hard delete preserves only accepted tombstone/idempotency/error metadata and removes live dialogue/job/content/delivery/approval state.
- Abrupt-process probes proved a successfully returned repository commit survives `os._exit`, while process exit from inside a write callback before kernel COMMIT leaves no partial transaction.
- No deterministic accepted-production defect was found by the final P2 acceptance harness.

## P3 split
P3 is split for reviewability:

- **P3.1** — existing-dialogue prompt execution and terminal capture.
- **P3.2** — lazy `thread/start` + first-turn orchestration and create-failure/recovery boundary.
- **P3.3** — profile/model/reasoning settings service with authenticated catalog validation and dialogue locks.
- **P3.4** — durable interrupt orchestration over P1.8 plus required `INTERRUPTING` transition/recovery authority.
- **P3.5** — hard-delete orchestration over P1.9 + final P3 recovery/application acceptance.

Only P3.1 is eligible for the next implementation prompt.

## P3.1 exact architect authority
Binding source: `docs/adr/0026-existing-dialogue-turn-application-service.md` plus accepted P1/P2 authority, product/state/security/retention contracts.

### Scope
P3.1 implements a Telegram-agnostic application service for an already-existing dialogue. For a NEW update, the dialogue must be canonical IDLE. Existing durable ingress is handled before current configuration so replay never depends on today's settings/catalog.

Required application order:

1. validate only static request shapes;
2. read `IngressUpdateRepository.get(update_id)` FIRST;
3. if ingress already exists, return durable DUPLICATE without catalog/working-directory/ID-factory/turn calls:
   - existing JOB + existing canonical job/INPUT -> exact duplicate job;
   - existing non-JOB -> `DUPLICATE_NON_JOB`;
   - orphan JOB + no live dialogue (accepted post-hard-delete shape) -> `DUPLICATE_ORPHAN_JOB`;
   - orphan JOB while a live dialogue exists -> finite application INVARIANT;
4. only for an unseen update, read live dialogue + durable settings;
5. require service server ID == dialogue server ID;
6. require settings profile == immutable dialogue profile and configured profile exists explicitly;
7. require a configured model and resolve it through authenticated P1 model catalog;
8. resolve NULL settings reasoning effort to the catalog's explicit default BEFORE durable job creation;
9. resolve an explicit trusted working directory through an injected port;
10. atomically claim P2 JOB ingress + RECEIVED job + INPUT before any `turn/start` effect;
11. if the atomic claim races and returns DUPLICATE, return it without a turn call;
12. preserve V1 BUSY/no-queue semantics for racing/new prompts;
13. after CREATED, reread exact current dialogue, then atomically `claim_turn` and `mark_codex_starting` before exactly one P1.6 `start_turn` call;
14. bind a confirmed Codex turn ID exactly once through `mark_codex_running`;
15. wait exactly once for the exact P1 turn binding;
16. map COMPLETED/FAILED/UNKNOWN to accepted P2 terminal capture without blind retry;
17. persist ordered user-visible agent messages as one transient OUTPUT payload in the same P2 terminal transaction when non-empty;
18. own post-admission caller cancellation so cancellation does not detach/restart the accepted prompt.

### Public application contract
- `ExistingDialoguePromptRequest`: update ID, source chat ID, source message ID, `text` with `repr=False`.
- `ExistingDialogueTurnStatus`: COMPLETED / FAILED / UNKNOWN / DUPLICATE / BUSY / BLOCKED.
- `ExistingDialogueTurnReason` exact values are frozen in ADR-0026, including `DUPLICATE_NON_JOB` and `DUPLICATE_ORPHAN_JOB`.
- immutable `ExistingDialogueTurnResult`: status, nullable job/dialogue/output payload/reason.
- `DialogueApplicationErrorCategory`: INVALID_ARGUMENT / STORAGE / CODEX / INVARIANT only; raw repository/adapter exception text never escapes.

### Retention
- INPUT absolute expiry target: 1 hour.
- COMPLETED OUTPUT: 1 hour.
- FAILED/UNKNOWN partial OUTPUT: 24 hours.
- no content is logged or put in generic repr.

### New-effect ordering
For a newly accepted existing-dialogue prompt:

`claim_ingress -> reread dialogue -> claim_turn -> mark_codex_starting -> P1 start_turn -> mark_codex_running -> P1 wait_turn -> finish_codex`

No `start_turn` happens before CODEX_STARTING commits.
No one job causes two starts.
Same-update duplicate never reaches P1.

### Out of scope
No lazy thread creation, settings mutation, interrupt, hard delete, restart reconciliation, approval Telegram UX, delivery planning/sending, controller ACTIVE/SLEEP routing, Telegram auth/UI, P4+, real Codex or production state.

## Execution authority
Codex must not self-start work from this document.

Only **P3.1 — existing-dialogue prompt application service** may be implemented from the next explicit architect prompt.
