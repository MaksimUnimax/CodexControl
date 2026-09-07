# P3.4 architect acceptance

Date: 2026-09-07
Status: ARCHITECT_ACCEPTED

Accepted implementation/proof HEAD: `6460a449f861b7b86ab664e5ff877c108715082d`.
Original architect base: `d8f8de0f349217c314c6eacd743132d51bcef279`.
Rejected first candidate: `2f63830c2e63e9a3564e1fed18eb7d55e36f8cd8`.
Issue: #26.
Architect first review: `5559617303`.
Architect review addendum: `5559630444`.
Binding authority: ADR-0030.

Independent GitHub review confirmed that the first repair is exactly one commit on top of the rejected candidate and changes only the two P3.4 production files required by the review, the focused P3.4 integration test module, and implementation evidence. No accepted P1/P2/P3.1/P3.2/P3.3 production authority or schema/DDL was changed by the repair.

The repair closes the exact-binding defect: every P3.4 terminal proof now requires the exact registry-owned `TurnBinding` object by identity (`is`), not frozen-dataclass structural equality. Equal-looking cloned bindings are rejected both for direct interrupt terminal results and collector reconciliation.

Local P1 interrupt error handling now follows ADR-0030. `TURN_INTERRUPT_NOT_ACTIVE` and `TURN_INTERRUPT_BUSY` perform at most one exact collector reconciliation and never redispatch interrupt. Other local request/precondition lifecycle failures fail closed as application `INVARIANT` without a collector retry.

Output preparation preserves the accepted P3 application diagnostic boundary: clock failures remain `STORAGE` and redact the raw clock failure; invalid generated output identity remains `INVARIANT`.

Idempotent interrupt/natural-terminal reconstruction now requires exact canonical terminal error semantics. `CODEX_COMPLETED` is error-free, definitive `FAILED` uses `CODEX_TURN_FAILED` with the accepted IDLE/ERROR dialogue distinction, and `UNKNOWN`/`TURN_UNKNOWN` uses matching `CODEX_AMBIGUOUS`. Persisted mismatched sanitized error shapes fail as invariant corruption rather than being normalized.

Still-running terminalization rejects job-version or dialogue-version exhaustion as `INVARIANT_VIOLATION` before output collision work, clock, increment or mutation. Exact already-terminal canonical rows remain reconstructable at maximum version because no version increment is required.

The strengthened focused integration proof materially exercises the real admitted-turn runner with a shared `ActiveTurnRegistry`: the exact P1 start binding is published before durable `CODEX_RUNNING`, looked up by identity by interrupt orchestration, and retired by the runner's exact terminal ownership path. The runner/interrupt race proves accepted `TurnJobRepository.finish_codex` is attempted first and only the exact interrupt-induced conflict uses the additive P3.4 reconciliation fallback; the final terminal row and OUTPUT are single-owned/idempotent.

Cross-slice proofs use real accepted P3.3/P2.4b surfaces. A legitimate P3.4 `INTERRUPTING` claim keeps profile/model/reasoning mutation blocked, and an approval callback created while the exact job/dialogue was running becomes `STALE`, is consumed once, leaves the approval pending, and replays as `ALREADY_CONSUMED`.

Focused P3.4 output proofs bind the accepted projection and retention rules: COMPLETED output uses completed retention, FAILED/UNKNOWN partial output uses uncertain retention, payload ownership/hash/length remains canonical, repr stays content-safe, and empty output produces no OUTPUT payload ID.

Final executor-reported focused counts: P3.4 `6 unit / 31 integration`; P3.3 `5 / 25`; P3.2 `2 / 21`; P3.1 `11 / 26`; P2.C1 `5 / 1`; P2.6b `5 / 12 / 8 / 3`; P1.8 `28`; P1.10 `6 / 1 / 4`. Expected and observed full discovery: `633` (`596 + 6 + 31`).

Frozen schema-v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

The known P1.6 pending-task warning remains pre-existing and was not introduced by P3.4.

P3.4 is complete and architect-accepted. P3.5 requires separate architect authority; no P3.5 implementation is accepted by this record.
