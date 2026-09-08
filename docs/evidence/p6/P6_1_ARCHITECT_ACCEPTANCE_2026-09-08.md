# P6.1 architect acceptance — durable successful-response delivery

Date: 2026-09-08

## Verdict

P6.1 is **ACCEPTED** at the fake/application response-delivery boundary.

Accepted implementation lineage:

- architect base: `48c66a7ae830d2c1b9873bbaa33d8625be9623ee`;
- initial candidate: `8a8db2a792be2015e397f8c55dd7994fd1eba0a3`;
- first repair: `fa5d0f2b0fc19b73fd1499c59c94dda595d8ea73`;
- accepted second repair: `51902dcbd743cd91ad209cd96879b4ad45a26a9e`.

Issue: #35.

Binding authority:

- `docs/adr/0039-durable-response-delivery.md`;
- architect review/addendum comment `5579459223`;
- architect second-review comment `5579738262`.

## Independent GitHub review

The architect independently verified:

- the accepted candidate is exactly three commits ahead of the frozen architect base and zero behind;
- the second repair is exactly one commit above the first repair;
- `main` remained frozen at the architect base until acceptance;
- cumulative production changes are limited to the P6.1 response-delivery facade/export plus the explicitly authorized additive `TransientPayloadRepository.get_output_for_job` read;
- no P2.4b delivery semantics, P2.5 deletion semantics, P3, P4, P5, schema or migration production authority was modified.

The second repair changed only:

- `src/codex_control/application/response_delivery.py`;
- `tests/unit/test_response_delivery.py`;
- `docs/evidence/p6/P6_1_DURABLE_RESPONSE_DELIVERY_EVIDENCE.md`.

## Accepted delivery semantics

The accepted implementation preserves P2.4b as the sole durable outbox authority:

- deterministic successful-output segmentation;
- exact-output restart recovery through `get_output_for_job`;
- transient DISPLAY materialization;
- immutable CREATE/first-EDIT delivery plan;
- durable `SENDING`, attempt 1, committed before every Telegram delivery effect;
- at most one CREATE/EDIT effect attempt per segment;
- CONFIRMED / FAILED / UNKNOWN persisted through accepted P2.4b;
- confirmed prefix is never resent;
- an already durable SENDING segment is never retried and is recovered as `TELEGRAM_RECOVERY_AMBIGUOUS` / `DELIVERY_UNKNOWN` with zero Telegram effect;
- storage failure after an external effect never causes inline resend; a later invocation resolves the stranded SENDING conservatively to UNKNOWN;
- caller cancellation does not cancel or redispatch an owned delivery effect;
- Codex FAILED/UNKNOWN jobs are outside P6.1 delivery and remain BLOCKED;
- accepted P2.5 hard-delete readiness remains unchanged and blocks deletion while response delivery is incomplete/ambiguous.

## Bounded segmentation correction

Independent review found the original ADR-0039 proof `ceil(total_chars / limit)` was insufficient for semantic-boundary segmentation because preferred boundaries can produce more chunks than hard cutting.

Architect comment `5579459223` therefore froze the binding correction:

- preferred paragraph/line/space/hard-cut segmentation remains deterministic;
- private maximum plan size is 4096 segments;
- if preferred segmentation exceeds 4096 while hard cutting can fit, deterministic hard-cut fallback is used;
- if even hard cutting requires more than 4096 segments, input fails closed;
- exact source reconstruction remains mandatory.

The accepted repair proves the pathological 1,053,700-character case would create 4100 preferred chunks but is safely reduced to at most 4096 hard chunks without content loss. The accepted P3 maximum projection remains within the hard-cut bound.

## Public contract strictness

The accepted repair also enforces finite public record invariants:

- `TelegramDeliveryEffectResult` accepts only canonical CONFIRMED / FAILED / UNKNOWN port-result relations;
- `TurnDeliveryResult` accepts only canonical top-level job/status/reason/segment relations;
- P6.1-local segment validation mirrors the relevant accepted P2.4b non-content canonicality: exact type/bounds, operation/target relation, payload-ID retention rules, lowercase SHA-256, timestamps, state/attempt relation, confirmed-message relation and confirmed EDIT identity;
- terminal CONFIRMED/FAILED segments remain compatible with accepted transient retention when `payload_id` has been removed;
- forged impossible public records fail `INVARIANT`.

## Test evidence

Executor evidence reports the accepted final suite:

- P6.1 unit: 20;
- P6.1 integration: 20;
- accepted baseline: 860;
- expected full: 900;
- observed full: 900;
- failures: 0;
- errors: 0;
- unittest result: `OK`.

Independent source review confirmed that the required focused proofs materially exist, including constructor invariants, pathological bounded segmentation, pre-clock ordering, distinguishable multi-segment order, SENDING-before-effect, stranded-SENDING zero-resend recovery, confirmed-prefix resume, cancellation shielding and storage-after-effect no-resend recovery.

No GitHub status checks or workflow runs were attached to `51902dcbd743cd91ad209cd96879b4ad45a26a9e`; no CI claim is made. Acceptance is based on independent GitHub topology/code/test-source review plus the executor's complete green regression evidence.

## Security / effects

No real Telegram/network/Codex/approval-response/production database/production state-root/service effect is accepted in P6.1.

Schema remains version 2.

Historical schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

Schema-v2 migration SHA-256 remains:

`a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

## Milestone transition

P6.1 is DONE.

P6 as a whole is NOT complete.

The next architecture slice is P6.2 only after independent architect research/freeze of the live P1.7 approval-request → durable operator decision → exact P1.7 response boundary.
