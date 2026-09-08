# P6.3 architect acceptance — 2026-09-08

## Verdict

ACCEPTED.

Accepted implementation lineage:

- architect base: `6dd277b11c10f16e3955b452f1abe7163a1846f5`
- initial candidate: `94238289602d0f52677bc21a5e847da3f1a97425`
- first repair: `3d4668a7c3627a269b5ce40ee53ff71a99ce8052`
- accepted second repair: `0409ad4a0744159aad875a5ddea4deaf1181699e`

Issue: #37.
Binding authority: ADR-0041.

## Independent GitHub verification

Verified independently from the remote repository:

- accepted candidate exists in GitHub;
- implementation branch HEAD is exactly `0409ad4a0744159aad875a5ddea4deaf1181699e`;
- architect base -> accepted candidate is exactly 3 commits ahead, 0 behind, merge-base exact architect base;
- second repair is exactly one test/evidence-only commit above first repair;
- cumulative production changes remain restricted to the P6.3-authorized local-orchestration surface plus the narrow read-only delivery-candidate repository method;
- schema remains v2 and accepted prior P1/P3/P4/P5/P6.1/P6.2 production authority is unchanged;
- no GitHub combined status checks or workflow runs were present for the accepted SHA.

## Accepted production behavior

Independent code review confirms:

- `TurnJobRepository.list_delivery_candidates(*, limit)` is bounded, oldest-first, read-only and zero-clock, selecting only `CODEX_COMPLETED`, `DELIVERY_PENDING`, and `DELIVERING`;
- `ApprovalAwareTurnLifecycle` captures the exact runtime used by accepted P1.6 and does not reacquire it for approval or interrupt handling;
- the exact live turn lease is retired when `wait_turn()` resolves while the process-local ACK hint remains separately available for final delivery/status handling;
- a second turn can be admitted while the previous turn's final Telegram delivery remains in progress, without false `TURN_OPERATION_BUSY`;
- the orchestrator requires the exact same `ApprovalDecisionSignal` instance used by the approval-aware lifecycle;
- wait-pump setup failure owns the exact runtime, shuts it down once, retires the lease, and fails closed to UNKNOWN;
- live P1.7 approvals are dequeued from the exact captured client and delegated to accepted P6.2;
- private P4.3 callback handling only pulses the shared wake signal; durable approval state remains sole decision authority;
- successful output delivery remains accepted P6.1 authority, including first-segment EDIT hint and durable one-attempt/no-resend behavior;
- live FAILED/UNKNOWN use only one safe non-durable status attempt and do not enter P6.1;
- startup recovery runs accepted P3.5 first, cancels leftover pending approvals for recovered terminalized jobs, then performs bounded P6.1 delivery recovery with no ACK replay;
- stranded `SENDING` recovers to `DELIVERY_UNKNOWN` with zero resend and confirmed prefixes resume without replay;
- startup processing is bounded to 256 candidates per explicit invocation with explicit `LIMIT_REACHED` and no background worker.

## Final fake P6 acceptance

The final acceptance composition uses temporary SQLite, fake Telegram effects and a transport-independent real `CodexProtocolClient`, while exercising accepted P1.6/P1.7/P3/P4/P5/P6.1/P6.2 application boundaries.

The final repair additionally proves the complete private interrupt chain:

raw private Telegram-like update -> `TelegramPrivateUpdateAdapter` -> `LocalControllerOrchestrator` -> real `PrivateControlService` -> real P3.4 `DialogueInterruptService` -> shared `ActiveTurnRegistry` -> same exact `ApprovalAwareTurnLifecycle` / accepted P1.6 binding.

The test observes durable `INTERRUPTING` around the one exact `turn/interrupt` effect, no runtime reacquire, finite terminal reconciliation, registry retirement and no second interrupt effect.

P6.3 tests contain no positive-duration `asyncio.sleep(...)`; scheduling uses explicit events, bounded state observation and `asyncio.sleep(0)` only.

## Test evidence

Executor full evidence accepted after independent code/test-source review:

- P6.3 unit: 6
- P6.3 integration: 3
- final P6 fake acceptance: 23
- accepted pre-P6.3 baseline: 922
- expected/observed full suite: `922 + 6 + 3 + 23 = 954`
- failures: 0
- errors: 0
- final status: OK

The known historical P1.6 pending-task warning remains pre-existing test-hygiene debt. No new P6.3 pending-task leak was found.

## Security / effect boundary

No real Telegram HTTP/network, real Codex process, production database/state root, service/deployment or credential effect is accepted by P6.3. Evidence and generic result/error representations remain content/redaction safe.

## Phase result

P6.1, P6.2 and P6.3 are all architect-accepted.

P6 is COMPLETE at the fake/application boundary.

Live Codex/T3 and live Telegram/deployment remain later phases.