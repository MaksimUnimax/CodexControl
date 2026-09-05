# P2.3 architect acceptance — 2026-09-05

Status: ACCEPTED

Accepted cumulative implementation/repair HEAD: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`.
Architect base: `0bd0c7b106cd5f874d9b49f9f4b16902a4335517`.
Issue: #13.

## Review history

- Initial candidate `7068cca5632548cb4cd58ad88ad94ed5e7de70ef` was rejected after independent review found a real atomicity defect: `IngressUpdateRepository.claim_ignored` accepted `IngressDispositionKind.CONTROL`, permitting a CONTROL ingress row without the required atomic controller epoch/mode mutation. Review also found incomplete expiry input validation, persisted-controller error normalization drift, post-precheck CAS mismatch misclassification, an incorrect JOB suffix bound, and missing/weak proofs.
- Repair `0d8f34beaa35a2bc02b349abba9507ebb9bc3802` closed those blockers and expanded deterministic acceptance coverage without changing accepted P2.1/P2.2 implementation files.

## Accepted ingress boundary

- `IngressDispositionKind` is exactly CONTROL / IGNORED_SLEEP / IGNORED_UNAUTHORIZED / JOB.
- `IngressUpdateRepository` exposes only `get` and `claim_ignored`.
- `claim_ignored` accepts only the two exact ignored enum objects. CONTROL, JOB and plain strings fail before SQL/clock execution, so the control atomicity path cannot be bypassed.
- A fresh ignored update writes one terminal row with equal received/completed timestamps. A duplicate returns the exact durable existing record unchanged, performs no reclassification and does not call the clock.
- P2.3 materializes `JOB:<id>` for forward compatibility only; P2.3 exposes no JOB-creation claim. The accepted suffix bound is 128 characters.

## Accepted control claim boundary

- Accepted P2.2 `ControllerRuntimeRepository` remains exactly `get` + `begin_boot`. P2.3 uses a separate `ControlIngressRepository`.
- Control outcomes are exactly APPLIED / STALE / DUPLICATE and `ControlClaimResult` contains no effective-mode authority.
- Duplicate ingress is checked first and returns `controller=None`, with no clock and no controller mutation.
- A new control requires an initialized canonical controller row. Missing bootstrap is NOT_FOUND with no ingress record/clock.
- A new stale epoch writes a terminal CONTROL ingress row and leaves controller state unchanged.
- A fresh epoch atomically writes CONTROL ingress plus `last_control_epoch`, historical `requested_mode` and monotonic timestamp in one P2.1 write transaction. Fresh same-mode control still advances the epoch.
- Fresh CAS mismatch is fail-closed INVARIANT_VIOLATION and rolls the transaction back; it is not reconciled as STALE.
- Concurrent ordering proves the greatest accepted epoch is final authority. Same-epoch competition has one APPLIED and one STALE with final mode equal to the applied winner.
- Restart still obtains effective SLEEP from P2.2 `begin_boot`; replay of an already-deduped activation is DUPLICATE and cannot restore ACTIVE. A genuinely new control update/epoch is required.

## Accepted callback-action boundary

- Public callback storage accepts only canonical lower-case SHA-256 token hashes; no raw callback token field/API was introduced.
- Callback action records bind action/subject/version/state plus exact user/chat identity and bounded timestamps; identifiers/numerics are validated against ADR-0020.
- Create is insert-only. Existing hash is ALREADY_EXISTS without clock/overwrite. `expires_at_ms` is exact non-bool signed-64 and must be strictly later than creation time.
- Claim order is lookup -> identity -> consumed state -> clock/expiry. Unauthorized user/chat receives only UNAUTHORIZED with `record=None`, before consumed/expiry state is exposed.
- Fresh authorized claim uses `effective_now=max(clock_now,created_at_ms)` and atomically writes one consumed timestamp.
- Authorized first observation of expiry durably terminalizes the token by writing `consumed_at_ms=expires_at_ms`; exact expiry is EXPIRED. Later clock rollback/restart cannot resurrect it and returns ALREADY_CONSUMED without re-evaluating freshness.
- Fresh/expired callback CAS mismatch after the exact unconsumed precheck is INVARIANT_VIOLATION, not a normal ALREADY_CONSUMED reconciliation path.
- Concurrent fresh claims produce one CLAIMED and one later ALREADY_CONSUMED; concurrent expired claims produce one EXPIRED and one later ALREADY_CONSUMED.
- Submitted claim ownership remains attached through repeated public cancellation by accepted P2.1 transaction ownership.
- P2.3 performs no subject-specific business mutation or external effect.

## Corruption, security and proof facts

- P2.3 reuses accepted P2.2 controller materialization so persisted noncanonical controller state is INVARIANT_VIOLATION, not caller-input INVALID_ARGUMENT.
- Ingress/callback schema-valid but repository-noncanonical rows fail closed with redacted diagnostics.
- Callback hash/type/identifier/numeric/expiry boundaries and control enum/epoch boundaries are covered deterministically.
- No P2.1 kernel/schema or P2.2 production file changed. Canonical DDL SHA remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- No Telegram SDK/business parsing, raw Telegram content, raw callback token, turn-job creation, external Codex/Telegram effect, production DB/state root, service change or runtime dependency was introduced.

## Acceptance evidence

Final committed counts reported and structurally consistent with the committed modules:

- P2.3 unit: 7.
- P2.3 integration: 28.
- Accepted pre-P2.3 full suite: 313.
- Final full suite: `313 + 7 + 28 = 348`.
- P2.2 unit/integration: 6 / 20.
- P2.1 unit/integration: 8 / 31.
- P1.10 T0/T1/T2: 6 / 1 / 4.
- Required P1 focused regressions, compile/import, diff and security checks passed.
- The pre-existing P1.6 pending-task warning was not observed in this particular run; no P2.3-owned task leak was introduced.

Executor evidence contains one documentation-only typo in its introductory P2.2 SHA line (`5187c080a7188a59989013fdefe7d07075662d007`); the correct architect-accepted P2.2 HEAD is `5187c080a7188a59989013defe7d07075662d007`. This typo did not affect code, tests, topology or acceptance.

P2.3 is architect-accepted. Later P2.4+ durable repositories require separate architect-owned authority.