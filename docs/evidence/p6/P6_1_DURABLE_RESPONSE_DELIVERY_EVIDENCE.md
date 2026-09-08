# P6.1 durable successful-response delivery — implementation evidence

This is executor evidence for Issue #35. It is not architect acceptance and does not mark P6.1 DONE.

## Scope and authority

- Repository: `MaksimUnimax/CodexControl`
- Base: `48c66a7ae830d2c1b9873bbaa33d8625be9623ee`
- Branch: `impl-p6-1-durable-response-delivery-2026-09-08`
- Issue: `35`
- Binding ADR: `docs/adr/0039-durable-response-delivery.md`
- No P6.2, P6.3, or P7 work was started.

## Implementation paths

- `src/codex_control/application/response_delivery.py`
- `src/codex_control/application/__init__.py`
- `src/codex_control/storage/turn_job_repositories.py`
- `tests/unit/test_response_delivery.py`
- `tests/integration/test_response_delivery.py`
- `tests/acceptance/test_p2_6b_contract_snapshot.py`
- `tests/unit/test_turn_job_records.py` (narrow additive public-surface assertion)

## Deterministic segmentation

The public constants are 512, 4096, 86,400,000 ms, and the exact empty-completion fallback `✅ Выполнено`. The pure segmenter validates exact strings, NUL-free strict UTF-8, and exact non-boolean integer limits. It preserves every source code point and reconstructs the input by concatenation. Boundary selection is farthest paragraph, then line, then ASCII-space, then an exact hard cut. The accepted P3 maximum projected character bound is 2,000,510 characters, requiring at most `ceil(2,000,510 / 512) = 3,908` segments, below the accepted P2.4b maximum of 4,096.

## Restart-safe output and DISPLAY materialization

`TransientPayloadRepository.get_output_for_job(job_id)` is the one authorized additive read. Its callback first requires the canonical job, selects only exact OUTPUT rows for that job, returns `None` for zero rows, rejects multiple rows as an invariant, and materializes/validates the sole row through the accepted materializer. It performs no clock read and no write. A successful job without OUTPUT uses only the exact fallback. Persisted OUTPUT bytes are decoded strictly and are never normalized.

Each final chunk becomes one transient DISPLAY payload with exact job/dialogue ownership, content, hash, byte length, and one common requested 86,400,000 ms expiry. IDs are requested once per chunk; collisions, factory exceptions, and invalid factory values are invariant failures with no Telegram effect and no retry. A pre-plan partial failure can leave only bounded transient orphans; no rollback SQL was added.

## Durable plan and one-attempt effect

Initial plans are all CREATE, or EDIT for the first chunk to the supplied status-message hint followed by CREATE segments. Existing plans are never rewritten by later hints. P2.4b remains the plan, claim, and finish authority. Before every fake/application Telegram call, accepted `claim_next` durably records SENDING/attempt 1 and the job as DELIVERING. Each segment has at most one owned CREATE/EDIT effect task with only the exact chat, target when applicable, and text arguments.

Confirmed multi-segment delivery advances in order and ends in DELIVERED. A confirmed prefix is never resent; restart resume begins at the first pending segment. Already DELIVERED replay performs zero port calls.

## Failure, ambiguity, and cancellation evidence

Canonical request rejection produces FAILED with no retry. Canonical network ambiguity, malformed results, ordinary port exceptions, owned effect-task cancellation, and EDIT returned-ID mismatch produce DELIVERY_UNKNOWN with the corresponding accepted durable error class and no retry. Existing SENDING is recovered with zero port calls and `TELEGRAM_RECOVERY_AMBIGUOUS`. Caller cancellation shields the owned effect and does not redispatch it. A storage failure after an external confirmation raises a finite STORAGE/INVARIANT error without resend; a later invocation recovers the stranded SENDING record to DELIVERY_UNKNOWN with zero new effects.

Codex FAILED and UNKNOWN jobs without a delivery plan are BLOCKED with zero port calls. P2.5 deletion production was not changed; its existing pending/delivering readiness blocks remain in force.

## Checks and counts

- P6.1 focused tests: 12 unit, 19 integration; 31 total; failures 0; errors 0.
- Prior targeted regression set: 102 tests; failures 0; errors 0.
- Full suite: 891 tests = 860 accepted base + 12 unit + 19 integration; failures 0; errors 0.
- Known P1.6 pending-task warning: observed; independently pre-existing and not introduced by P6.1.
- Schema version: 2.
- Historical schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Schema-v2 migration SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.

Temporary SQLite databases and fake Telegram ports were used. No real Telegram, network, Codex, approval-response, production database, production state root, or production service effect was used.
