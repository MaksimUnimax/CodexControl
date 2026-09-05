# P2.3 Ingress/Control/Callback Claims Evidence

- base: `0bd0c7b106cd5f874d9b49f9f4b16902a4335517`
- branch: `impl-p2-3-ingress-control-callback-claims-2026-09-05`
- issue: `#13`
- ADR-0020 reference: implemented in `src/codex_control/storage/idempotency_records.py`, `src/codex_control/storage/idempotency_repositories.py`, and tests.
- accepted P2.1 head: `61301fd25ff7253693f367664ce99e13dfc88446`
- accepted P2.2 head: `5187c080a7188a59989013fdefe7d07075662d007`

## Source Files

### Updated / added
- `src/codex_control/storage/idempotency_records.py`
- `src/codex_control/storage/idempotency_repositories.py`
- `src/codex_control/storage/__init__.py`
- `tests/unit/test_idempotency_records.py`
- `tests/integration/test_ingress_control_callback_claims.py`
- `docs/evidence/p2/P2_3_INGRESS_CONTROL_CALLBACK_EVIDENCE.md`

## Public Types / API Surface

- `IngressDispositionKind`: `CONTROL | IGNORED_SLEEP | IGNORED_UNAUTHORIZED | JOB`
- `IngressUpdateRecord`
- `IngressClaimResult`
- `ControlClaimStatus`: `APPLIED | STALE | DUPLICATE`
- `ControlClaimResult`
- `CallbackActionRecord`
- `CallbackClaimStatus`: `CLAIMED | NOT_FOUND | UNAUTHORIZED | EXPIRED | ALREADY_CONSUMED`
- `CallbackClaimResult`
- `IngressUpdateRepository`: `get`, `claim_ignored`
- `ControlIngressRepository`: `claim_control`
- `CallbackActionRepository`: `create`, `claim`

## Ingress materialization / control flow

- `IngressUpdateRecord` materialization:
  - `CONTROL` -> `CONTROL`, `job_id=None`
  - `IGNORED_SLEEP` -> `IGNORED_SLEEP`, `job_id=None`
  - `IGNORED_UNAUTHORIZED` -> `IGNORED_UNAUTHORIZED`, `job_id=None`
  - `JOB:<id>` -> `JOB`, extracted `job_id`
- Validation: no NUL, job id non-empty and <=128 chars, disposition parsing, non-negative signed 64-bit times.

## Ingress claims

- `claim_ignored` accepts only `IGNORED_SLEEP`/`IGNORED_UNAUTHORIZED` enum values.
- Duplicate row path:
  - returns existing materialized row
  - `duplicate=True`
  - no clock call
  - no row rewrite
- New ignore path:
  - single clock call
  - `received_at_ms=now`, `completed_at_ms=now`
  - atomic insert with exact disposition.

## Control claims (`ControlIngressRepository.claim_control`)

- Strict input validation before transaction.
- Missing controller runtime: returns `NOT_FOUND` with zero clock and no mutation.
- Duplicate ingress `update_id`: returns `DUPLICATE` with zero clock and no controller mutation.
- Same update concurrency: one `APPLIED`, one `DUPLICATE`.
- New control path:
  - inserts control ingress row once
  - if `control_epoch <= last_control_epoch` -> `STALE` with current controller
  - else CAS update on `last_control_epoch` using `last_control_epoch` guard
  - updates `requested_mode`, `updated_at_ms = max(now, current.updated_at_ms)` while preserving static fields.
- No retry loop and no implicit `begin_boot`.

## Callback claims (`CallbackActionRepository`)

- Public arguments are hash-only (`token_hash_sha256`) and regex-validated to lowercase SHA-256 hex.
- Record fields contain no raw token/secret names.

### Create

- Pre-insert duplicate lookup and `ALREADY_EXISTS` if present.
- One validated clock read per create.
- Rejects `expires_at_ms <= created_at_ms`, `invalid arguments`, and `clock` failures.
- Inserts with `consumed_at_ms=NULL`.

### Claim

- One-row lookup and unauthorized check occurs before expiry/consumption checks.
- Fresh path:
  - `effective_now = max(clock_now, created_at_ms)`
  - CAS consumed update with `consumed_at_ms = effective_now`
  - returns `CLAIMED` with returned record
- Expiry terminalization path:
  - if `effective_now >= expires_at_ms`, set `consumed_at_ms = expires_at_ms` with CAS
  - returns `EXPIRED`
  - subsequent claims -> `ALREADY_CONSUMED`
- `NOT_FOUND` and `UNAUTHORIZED` return `record=None`.
- `clock` is not called for missing or unauthorized.

## Restart / persistence

- Ingress row survives reopen.
- Control epoch/mode persists and restart re-baselines mode to `SLEEP`.
- Callback create/consume state persists across reopen and is authoritative by DB state only.

## Concurrency and cancellation observed

- Duplicate/concurrency assertions passed for:
  - same-update concurrent control claims
  - same-epoch competing control updates
  - fresh/expired concurrent callback claims
- Callback claim cancellation with blocking clock task stays attached through cancellation and consumes/terminalizes exactly once.

## Security / redaction

- No file stores raw callback token or Telegram payload.
- Repository reprs do not expose db path.
- Sentinels used only in tests (`PRIVATE_P2_3_CLOCK_MUST_NOT_LEAK`, etc.) and are not persisted.

## Test summary snapshot

- P2.3 integration module: 16 tests (all passing)
- P2.3 unit module: 6 tests (all passing)
- Required P2.2, P2.1, P1.10, focused P1 unit suites: all passing
- `python3 -m unittest discover -s tests -v`: 335 tests.

## Architect first repair pass

Repair parent / rejected candidate: `7068cca5632548cb4cd58ad88ad94ed5e7de70ef`.
This section records the first repair pass only; P2.3 is not architect-accepted.

The repair closed the independent review findings without changing the accepted
P2.1/P2.2 implementation slices:

- `claim_ignored` now accepts only the exact `IGNORED_SLEEP` and
  `IGNORED_UNAUTHORIZED` enum objects. `CONTROL`, `JOB`, strings, integers and
  `None` fail as `INVALID_ARGUMENT` before SQL/clock execution.
- `expires_at_ms` is validated as an exact non-bool signed-64 integer before
  storage transaction entry. Relation validation remains after duplicate-token
  precheck and the required clock call.
- Control materialization reuses the accepted P2.2 private materializer, so
  schema-valid but repository-noncanonical controller values fail as
  `INVARIANT_VIOLATION`, never caller-input `INVALID_ARGUMENT`.
- Control and callback CAS rowcount mismatches now fail closed as
  `INVARIANT_VIOLATION`; no post-precheck stale/already-consumed
  reconciliation is performed.
- JOB materialization validates the suffix after parsing `JOB:` and permits a
  128-character job ID while rejecting 129 characters.
- Callback corruption assertions were moved outside `assertRaises` bodies;
  uppercase persisted hashes are checked through the private materializer and
  classify as `INVARIANT_VIOLATION`.

Added deterministic proofs cover the CONTROL bypass, expiry type/bounds and
exact boundary, persisted controller corruption, CAS guard, clock-failure
rollback/redaction, ignored/control cross-classification, higher-epoch final
authority, same-epoch final mode, duplicate create zero-clock/no-overwrite,
authorization precedence, numeric and identifier boundaries, enum-only control
mode, repeated cancellation ownership, fresh-after-restart callback claim,
JOB suffix limits, callback corruption and uppercase stored-hash handling.

Observed focused counts after repair:

- P2.3 unit: 7.
- P2.3 integration: 28.
- Accepted pre-P2.3 full suite: 313.
- Formula: `313 + 7 + 28 = 348`.
- Full discovery: 348 tests, all passing.
- P2.2 unit/integration: 6 / 20, all passing.
- P2.1 unit/integration: 8 / 31, all passing.
- P1.10 T0/T1/T2: 6 / 1 / 4, all passing.
- P1 focused suites: all passing.
- P1.6 pending-task warning observed: NO. It was not introduced by P2.3.

The canonical P2.1 DDL SHA remains
`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
Compile, import, `git diff --check`, allowed-path and security/production-scope
checks passed. No production database/state root, secrets, services, Telegram
surface, raw callback token, or conversation content was touched. P2.4 was not
started and Issue #13 remains open pending architect review.
