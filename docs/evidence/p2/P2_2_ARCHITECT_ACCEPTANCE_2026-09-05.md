# P2.2 architect acceptance — 2026-09-05

Status: ACCEPTED

Accepted cumulative implementation/proof HEAD: `5187c080a7188a59989013defe7d07075662d007`.
Architect base: `b1d3b15f098dab4da1f60b168d2b324abeaa193e`.
Issue: #12.

## Review history

- Initial implementation `be2d2f527ad6160cd6ac1bfbbe10cdf79be1e8cf` was directionally consistent with ADR-0019 and no production defect was found, but architect acceptance was withheld because several reported PASS markers were not yet backed by committed deterministic proofs.
- Proof repair `5187c080a7188a59989013defe7d07075662d007` changed only P2.2 tests/evidence, exposed no production defect, and closed the remaining proof gaps.

## Accepted repository contract

- P2.2 uses only the accepted P2.1 `SqliteStorage.read/write` boundary; P2.1 kernel/schema/DDL are unchanged.
- Semantic repository diagnostics are finite/redacted and remain distinct from `StorageError`, which propagates unchanged.
- Repository clocks are injected/testable, finite, redacted on failure, called only after semantic preconditions that actually require a mutation, and use monotonic `max(now, previous.updated_at_ms)` update timestamps.
- Stored integer/version/timestamp values are validated as non-negative signed-64 integers; optimistic version/generation overflow fails closed without wrap or an unnecessary clock call.
- Materialized records are immutable; repository reads validate persisted values and fail `INVARIANT_VIOLATION` on noncanonical schema-valid corruption.

## Controller runtime

- Public semantic surface is only `get()` and `begin_boot()`.
- First boot creates epoch 0, requested SLEEP, generation 1.
- Repeated boot preserves historical control epoch/requested mode, increments generation once and returns effective mode SLEEP unconditionally.
- Historical persisted ACTIVE never restores ACTIVE after restart.
- P2.2 exposes no control-epoch or ACTIVE/SLEEP mutation API; that remains P2.3 authority.

## Settings

- `initialize_if_absent` creates version 0 only when absent; otherwise durable settings win over new fallback values and no mutation clock is called.
- `replace` is full-record optimistic CAS, requires the exact expected version, increments exactly once even for same-value replacement, and performs no retry/merge.
- Concurrent same-version replacement has exactly one winner and final durable version N+1.

## Dialogue create-intent boundary

- `DialogueState` materializes all ten schema-v1 states, but P2.2 write APIs can produce only CREATING, IDLE, CREATE_UNKNOWN and ERROR.
- `create_intent` atomically claims the empty live-dialogue slot as CREATING/version 0; every retained row, including identical replay, is ALREADY_EXISTS.
- Create terminal claims are exactly `confirm_created`, `mark_create_unknown`, and `mark_create_error` with conflict precedence NOT_FOUND -> VERSION_CONFLICT -> STATE_CONFLICT.
- Thread binding is written once; dialogue/server/profile identities are immutable; create terminal outcomes are mutually exclusive.
- No generic dialogue transition/delete or turn/interrupt/delete state mutation API exists in P2.2.

## Proof/acceptance evidence

Final committed P2.2 tests prove:

- all ten dialogue states materialize through `DialogueRepository.get_live()`;
- real raising-clock mutation paths normalize/redact CLOCK_INVALID with rollback/no mutation;
- bool/non-int/negative/overflow clock values fail closed while 0 and signed-64 MAX are accepted;
- exact public repository callable surfaces;
- controller/settings/dialogue increment overflow behavior;
- exact public string/version input boundaries including empty/NUL rejection;
- controller/settings/dialogue corrupt-row fail-closed materialization;
- exact controller/settings/confirmed-dialogue equality after close/reopen;
- repository error/repr redaction and absence of embedded retry-policy fields.

Final counts reported and structurally consistent with committed tests:

- P2.2 unit: 6.
- P2.2 integration: 20.
- Accepted pre-P2.2 full suite: 287.
- Final full suite: `287 + 6 + 20 = 313`.
- P2.1 schema/integration remained 8 / 31 with DDL SHA `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c` unchanged.
- P1.10 T0/T1/T2 remained 6 / 1 / 4; required P1 focused regressions, compile/import, diff and security checks passed.
- No runtime dependency, production DB/state, service or architecture-file changes were made by the P2.2 implementation/proof pass.

The known P1.6 pending-task warning remains pre-existing test-hygiene debt and was not introduced by P2.2.

P2.2 is architect-accepted. Later P2.3+ durable mutations require separate architect-owned authority.