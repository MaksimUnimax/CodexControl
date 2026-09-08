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

The public constants are 512, 4096, 86,400,000 ms, and the exact empty-completion fallback `✅ Выполнено`. The pure segmenter validates exact strings, NUL-free strict UTF-8, and exact non-boolean integer limits. It preserves every source code point and reconstructs the input by concatenation. Boundary selection is farthest paragraph, then line, then ASCII-space, then an exact hard cut. The first candidate recorded an invalid worst-case proof that applied `ceil(N / limit)` directly to the preferred semantic pass; the repair retains that pass but adds the binding bounded-fallback rule below.

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
- Rejected candidate full discovery: 891 tests = 860 accepted base + 12 unit + 19 integration; failures 0; errors 0.
- Known P1.6 pending-task warning: observed; independently pre-existing and not introduced by P6.1.
- Schema version: 2.
- Historical schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Schema-v2 migration SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.

Temporary SQLite databases and fake Telegram ports were used. No real Telegram, network, Codex, approval-response, production database, production state root, or production service effect was used.

## Architect first repair

This is factual executor evidence for the first P6.1 repair. It does not claim
architect acceptance and does not close Issue #35.

- Rejected candidate: `8a8db2a792be2015e397f8c55dd7994fd1eba0a3`.
- Architect review/addendum: `5579459223`.
- Repair production/test/evidence paths: `src/codex_control/application/response_delivery.py`,
  `tests/unit/test_response_delivery.py`, `tests/integration/test_response_delivery.py`,
  and this evidence file. No architect-owned file was changed.

### Factual closure

- `TelegramDeliveryEffectResult` now accepts only the three canonical direct
  construction shapes. Invalid effect shapes, including service-only error
  classes, are rejected as `INVALID_ARGUMENT`; repr remains identifier-safe.
- `TurnDeliveryResult` now enforces exact status/tuple/reason types and the
  canonical DELIVERED, ALREADY_DELIVERED, DELIVERY_UNKNOWN, FAILED, and
  BLOCKED relations. Impossible public results raise `INVARIANT`.
- The first candidate's invalid semantic worst-case proof is retained as a
  documented fact. The pathological preferred segmentation counterexample is
  `("\n\n" + ("a" * 512)) * 2050`: length `1,053,700`, preferred count `4,100`
  (`>4096`). The deterministic hard fallback returns at most `4096` exact
  chunks, reconstructs the input exactly, and preserves all content.
- Inputs longer than `limit * 4096` are rejected as `INVALID_ARGUMENT` before
  the preferred list is built. The accepted P3 maximum is `2,000,510`; hard
  fallback at limit `512` gives exactly `ceil(2,000,510 / 512) = 3,908`, so
  accepted P3 output remains within the durable plan bound by fallback.
- Initial planning now performs OUTPUT lookup/decode/fallback and segmentation
  before reading the application clock. The invalid UTF-8 pre-clock proof has
  zero application-clock calls, zero DISPLAY rows, zero delivery segments, and
  zero Telegram calls; a normal valid plan reads the application clock exactly
  once.
- The multi-segment proof uses distinguishable exact texts `A*512`, `B*512`,
  and `C`, verifies sequence `1,2,3`, exactly three port calls, and observes
  durable SENDING/attempt 1 before each effect.
- Existing one-attempt, SENDING-before-port, terminal FAILED/UNKNOWN no-retry,
  malformed-port RESULT_INVALID, stranded-SENDING zero-resend recovery,
  confirmed-prefix resume, caller-cancellation shielding, and
  storage-after-effect no-resend proofs remain green. P2.4b and P2.5 behavior
  is unchanged.

### Validation

- Final focused P6.1 tests: `14` unit and `20` integration; `34` total; all
  passing.
- P2.4b delivery and P2.5 deletion regressions: `53` tests; all passing.
- Full suite: expected/observed `860 + 14 + 20 = 894` tests; failures `0`; errors `0`; final status `OK`.
- Compileall, P6.1 import smoke, schema checks, `git diff --check`, and the
  changed-path secret/effect scan passed. The full discovery output contained
  no P1.6 pending-task warning in this repair pass.
- No schema/DDL, P2.4b, P2.5, P3, P4 or P5 production change was made.
- Schema version remains `2`; historical v1 DDL SHA-256 remains
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c` and
  schema-v2 migration SHA-256 remains
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- No real Telegram, network, Codex, approval response, production database,
  production state root, or production service effect was used.

## Architect second repair

This is factual executor evidence for the second P6.1 repair. It does not
claim architect acceptance and does not close Issue #35.

- First candidate: `8a8db2a792be2015e397f8c55dd7994fd1eba0a3`.
- First repair: `fa5d0f2b0fc19b73fd1499c59c94dda595d8ea73`.
- Second architect review: `5579738262`.
- The second repair production path is
  `src/codex_control/application/response_delivery.py`; direct proof updates
  are in `tests/unit/test_response_delivery.py`. No integration test change,
  P2.4b production change, schema change, ADR change, P2.5 change, or later
  P6/P7 work was made.

### Canonical segment validation closure

The P6.1-local validator used by `_validate_p6_plan()` and public
`TurnDeliveryResult` construction now enforces:

- exact `DeliverySegmentRecord` type, bounded exact job ID, contiguous bounded
  sequence, and first-sequence-only EDIT;
- exact operation/state types, CREATE target absence, and positive exact EDIT
  target IDs;
- bounded payload IDs when present, required payload IDs for PENDING/SENDING/
  UNKNOWN, and terminal CONFIRMED/FAILED payload-null retention compatibility;
- exact lowercase 64-character hexadecimal payload SHA;
- PENDING attempt 0, SENDING/UNKNOWN/FAILED attempt 1, and CONFIRMED attempt
  1 with a positive exact confirmed message ID;
- no confirmed message ID for non-CONFIRMED states;
- confirmed EDIT identity equality between confirmed and target message IDs;
- bounded exact timestamps and `updated_at_ms >= created_at_ms`.

Direct public-constructor proofs reject forged terminal records for all
requested attempt/confirmation relations, confirmed EDIT identity mismatch,
later EDIT, invalid SHA, timestamp ordering, boolean/boundary fields, and
accept canonical CREATE, first EDIT, UNKNOWN, FAILED, and terminal retained
payload-null shapes.

### Regression and safety validation

- Focused P6.1 tests: `20` unit and `20` integration; failures `0`, errors
  `0`.
- Accepted P2.4b delivery and P2.5 deletion focused suites: `53` tests;
  failures `0`, errors `0`.
- Full discovery: `900` tests; expected `860 + 20 + 20 = 900`; failures `0`,
  errors `0`, status `OK`.
- All previous segmentation, pre-clock ordering, SENDING-before-effect,
  multi-segment order, confirmed replay, stranded-SENDING recovery,
  confirmed-prefix resume, cancellation, storage-after-effect no-resend,
  terminal no-retry, Codex blocking, and P2.5 readiness proofs remain green.
- `SCHEMA_VERSION=2`; historical schema-v1 DDL SHA-256 and schema-v2
  migration SHA-256 remain unchanged at the values recorded above.
- Compile/import, `git diff --check`, repair-only/cumulative path checks, and
  secret/effect scans passed. Tests used only temporary SQLite/fakes; no real
  Telegram, network, Codex, approval-response, production DB, production
  state root, or production service effect was used.
- P1.6 pending-task warning observed: `NO`; introduced by P6.1: `NO`.
