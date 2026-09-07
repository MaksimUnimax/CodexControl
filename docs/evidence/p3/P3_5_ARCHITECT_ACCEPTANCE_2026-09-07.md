# P3.5 architect acceptance

Date: 2026-09-07
Status: ARCHITECT_ACCEPTED

Accepted implementation/proof HEAD: `6145d262787465ac6b4a17327114211cd86e8104`.
Original architect base: `3e19f1028916613f7d89b254fdd7bf04505a2fb5`.
Initial rejected candidate: `4e5cbbf6cc4df1ffc33df9c06be4cea7d3a11494`.
First repair: `bcc84e6941752b7832b5f7608b44cab372b174e8`.
Second repair: `12f024f9900cadbf9f98724a7247418621d4f410`.
Third repair: `d9d1336f4cfd72e5d3d47db391fcac4bd43506d4`.
Fourth/final repair and accepted HEAD: `6145d262787465ac6b4a17327114211cd86e8104`.
Issue: #27.
Architect review comments: `5564792583`, `5565047063`, `5565286591`, `5565728116`.
Binding authority: ADR-0031 plus accepted P1.9, P2.5 and P3.1-P3.4 authority.

Independent GitHub review confirmed a linear five-commit P3.5 implementation history above the exact architect base, with no divergence. The cumulative diff is limited to P3.5 application/storage coordination, the architect-authorized additive `ActiveTurnRegistry` quiescence surface, P3.5 exports, focused unit/integration/final fake-acceptance tests, and P3.5 implementation evidence. No schema/DDL, ADR, P1/P2 production or unrelated accepted P3 production was changed.

The hard-delete application boundary is accepted. `DialogueDeleteService.delete(DialogueDeleteRequest)` uses only dialogue ID plus optimistic dialogue version from the caller, delegates local delete readiness/finalization to accepted P2.5, reaches P1.9 only after durable `DELETING`, treats only exact `DELETE_CONFIRMED` with the exact supplied `ThreadBinding` identity as external confirmation, never blind-retries `thread/delete`, and makes `DELETE_UNKNOWN` terminal uncertainty for P3.5.

Tombstone replay is idempotent and effect-free. A confirmed local finalize purges the live dialogue-owned job/payload/delivery/approval state and retains the bounded content-free tombstone and accepted non-content metadata. The tombstone target remains exactly seven days (`604800000` ms), with P2.6a retaining cleanup authority. Confirmed external deletion followed by an internal finalize failure never retries delete; semantic post-confirmation failures are internal `INVARIANT`, storage/clock failures remain `STORAGE`, and durable `DELETING` evidence is preserved for no-P1 startup conversion to `DELETE_UNKNOWN`.

Optimistic delete precedence is accepted: after tombstone/live-ID checks, a matching live dialogue version mismatch is `CONFLICT / STALE_REQUEST` before current-state reporting. Current `DELETING` never emits a second delete and reports `DELETE_IN_PROGRESS`; current `DELETE_UNKNOWN` reports `UNKNOWN`; only a fresh explicit request bound to the current `DELETE_PENDING` version may continue to one `thread/delete` effect. Startup recovery never auto-continues `DELETE_PENDING`.

Running-delete composition with accepted P3.4 is accepted. Only the exact active `CODEX_RUNNING` job and exact shared registry-owned `TurnBinding` can authorize the interrupt path. Definitive P3.4 continuation requires exact original job/update/server/profile/thread/turn/model/effort/input identity, job version `K+1`, exact terminal state/error semantics, exact IDLE dialogue version `V+2`, matching owner/thread, no dialogue error, no result reason, and coherent optional OUTPUT ownership. Synthetic `V+3`, cloned/mismatched jobs, wrong owner/thread/turn/state/error/version or malformed results fail `INVARIANT` before deletion.

The final runner/quiescence boundary is accepted. P3.5 synchronously arms a retirement watch against the exact active registry generation before invoking P3.4. The admitted runner must complete its accepted P3.4 natural-terminal reconciliation and retire its exact lease before P3.5 can enter P2.5 delete intent. Registry bookkeeping is bounded to active entries plus currently live watches; there is no permanent retired-binding archive. Any replacement publication for the same job before an old watch completes permanently supersedes that watch, including transient A-retire -> B-publish -> B-retire and multiple-replacement races. Successful, failed, cancelled and disposed watches unregister, so normal completed turns retain zero historical registry ownership.

The final startup recovery boundary is accepted. `DialogueRecoveryService.recover_startup()` has no P1/Codex/Telegram port and performs at most one local recovery transition: `CREATING -> CREATE_UNKNOWN`, `INTERRUPTING -> TURN_UNKNOWN`, `DELETING -> DELETE_UNKNOWN`, stranded `RECEIVED/CLAIMED` -> deterministic pre-effect failure, and `CODEX_STARTING/CODEX_RUNNING` -> UNKNOWN. `DELETE_PENDING` is held. Already terminal/unknown/error states are `NO_ACTION` only when the complete cross-table dialogue/job/ingress/INPUT shape is canonical; schema-valid semantic corruption fails closed as `INVARIANT`.

Cross-slice final fake/application acceptance materially covers settings initialization, lazy first dialogue, later turn, IDLE settings lock behavior, exact active registry ownership, real P3.4 interrupt composition, no delayed prompt queue, runner retirement before delete, durable `DELETING` before fake P1.9, confirmed purge+tombstone, idempotent tombstone replay, post-delete profile mutation, and no-P1 startup recovery. The original runner returns a finite accepted terminal result; no `DialogueApplicationError` is swallowed by the acceptance proof.

Executor-reported final focused counts are P3.5 `12 unit / 25 integration / 1 final fake acceptance`. Required prior focused regressions were reported green at their accepted counts, including P3.4 `6/31`, P3.3 `5/25`, P3.2 `2/21`, P3.1 `11/26`, P2.C1 `5/1`, P2.6b `5/12/8/3`, P2.6a `4/28`, P2.5 `4/18`, P2.4b `6/25`, P2.4a `8/31`, P2.3 `7/28`, P2.2 `6/20`, P2.1 `8/31`, P1.9 `15`, P1.8 `28`, and P1.10 `6/1/4`.

Accepted pre-P3.5 full count was `633`. Final arithmetic is `633 + 12 + 25 + 1 = 671`; executor full discovery reported `671` passing tests. Compile/import, `git diff --check`, DDL hash and secret/effect scans were also reported passing. GitHub has no CI/status checks attached to the accepted SHA, so the architect did not treat CI as independent test execution; acceptance is based on exact GitHub code/test/evidence review plus the executor's complete regression evidence, consistent with the P3.4 acceptance method.

Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

The known P1.6 pending-task warning remains pre-existing and was not introduced by P3.5.

P3.5 is complete and architect-accepted. P3 dialogue application service is therefore complete at the fake/application boundary. No P4 implementation is accepted or authorized by this record; P4 requires separate architect-frozen authority before execution.
