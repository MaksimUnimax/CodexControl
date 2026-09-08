# P5.2 architect acceptance — 2026-09-08

Status: **ACCEPTED**

## Accepted implementation

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `d325260034650d11743ef8ed96a9b8c70d699349`
- Initial implementation candidate: `428fb93056358b898d2e7cc95d94ae61de8617de`
- First-repair commit / accepted implementation: `345c48722c4faa03be19d38b6f07304276075f64`
- Implementation branch: `impl-p5-2-group-prompt-routing-2026-09-08`
- Issue: #33
- Binding architecture: ADR-0037
- Architect rejection/review comment for the initial candidate: `5578312547`

## Independent topology and boundary verification

Independent GitHub readback verified:

- `428fb93056358b898d2e7cc95d94ae61de8617de` was exactly one commit above the architect base;
- `345c48722c4faa03be19d38b6f07304276075f64` is exactly one repair commit above that candidate and zero commits behind it;
- cumulative P5.2 lineage is exactly two implementation commits above `d325260034650d11743ef8ed96a9b8c70d699349` and zero behind;
- repair-only production change is limited to `src/codex_control/application/fleet_group_routing.py` plus focused tests/evidence;
- cumulative production remains limited to the P5.2 facade and narrow application exports;
- accepted P5.1, P3 and P2 production were not modified;
- schema/DDL were not modified.

## Accepted routing semantics

The accepted P5.2 facade preserves the ADR-0037 no-queue boundary:

- one short group-routing lock protects authorization/mode/duplicate/stale/SLEEP/local-marker admission decisions only;
- the lock is released before the full P3 turn is awaited;
- controls remain processable while a prompt turn is running;
- no prompt queue/backlog is implemented;
- the local prompt marker is process-local, non-durable and content-free;
- a different update while the marker is held is terminal `IGNORED_REJECTED` / BUSY without P3 dispatch;
- the same update while its original marker is in flight is returned as `DUPLICATE / IN_FLIGHT_DUPLICATE` without consuming the original authority;
- durable duplicate precheck occurs only after accepted P5.1 reauthorization/current-boot validation;
- stale prompt `message_id <= last_control_epoch` is terminal `IGNORED_REJECTED` and cannot execute later;
- SLEEP prompt is terminal `IGNORED_SLEEP` and cannot execute after later activation;
- fresh ACTIVE eligible prompt delegates exactly once to accepted P3.2 `DialogueTurnService`;
- accepted P3 BUSY/BLOCKED pre-JOB results are terminalized as `IGNORED_REJECTED` before successful return;
- COMPLETED/FAILED/UNKNOWN after durable admission remain `JOB` and are never reclassified as rejected;
- caller cancellation does not cancel or redispatch the owned P3 task;
- restart restores no local marker/queue authority.

## First-repair closure

Independent review of the first repair verified closure of both rejected-candidate blockers:

1. `GroupRoutingStatus.PROMPT` now requires an exact `FleetModeSnapshot` whose `effective_mode` is `ACTIVE`; public construction with `snapshot=None` or a SLEEP snapshot fails `INVARIANT`.
2. P3 `DUPLICATE` validation now accepts only canonical finite relations: no-job with exact duplicate reason, or exact job with `reason=None`.
3. Malformed BUSY/BLOCKED/DUPLICATE/terminal result cases fail `INVARIANT` before durable state can mask the malformed port result.
4. No malformed P3 result causes a blind rejected claim.
5. The original stale/SLEEP/local-BUSY/same-update/P3 BUSY/P3 BLOCKED/terminal-JOB/no-queue/control-responsiveness/cancellation/restart proofs remain green.

## Tests and evidence

Final focused P5.2 counts:

- unit: `11`
- integration: `34`

Accepted pre-P5.2 baseline: `796`.

Exact full-suite arithmetic:

`796 + 11 + 34 = 841`

Executor isolated regression evidence reports:

- observed full discovery: `841` tests;
- failures: `0`;
- errors: `0`;
- unittest status: `OK`.

Required prior P2.C2/P5.1/P4/P3/P2/P1 focused regression groups were also reported green at their accepted counts. The known P1.6 pending-task warning remains inherited test-hygiene debt and was not introduced by P5.2.

GitHub exposed no commit status checks or pull-request workflow runs for the accepted SHA. This acceptance therefore does **not** claim GitHub CI; it is based on independent GitHub topology/code/diff review together with the isolated executor regression evidence above.

## Security / effect boundary

Accepted P5.2 adds no live Telegram or delivery transport and no production configuration/deployment effects. Review found no real:

- Telegram/network call;
- Codex process/thread/turn call in P5.2 tests;
- interrupt/delete/approval-response/delivery call;
- production database/state-root/service mutation.

The final P5.2 generic result/error surfaces remain content-redacted and do not expose prompt/output or production thread/job/turn identifiers.

## Schema authority

Current schema remains version `2`.

Historical schema-v1 DDL SHA-256 remains immutable:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

Schema-v2 migration-statement SHA-256 remains:

`a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

## Architect verdict

**P5.2 ACCEPTED.**

P5.2 is complete at the local fake/application group-prompt-routing boundary. P5.3 may now proceed to fleet status/version-mismatch safeguards and final fake multi-controller group-routing acceptance. P6 and live Telegram transport remain later slices.
