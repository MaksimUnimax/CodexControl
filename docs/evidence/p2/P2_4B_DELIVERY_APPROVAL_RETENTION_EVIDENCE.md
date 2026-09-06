# P2.4b delivery, approval and bounded-retention implementation evidence

Date: 2026-09-06

This is factual implementation evidence for Issue #15. It does not claim
architect acceptance and does not authorize or recommend a later roadmap slice.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Base SHA: `7f9c84fc1dfe77e07db3f78568c15a58e6370cf9`
- Branch: `impl-p2-4b-delivery-approval-retention-2026-09-05`
- Issue: `#15` (body read through the GitHub API; zero comments were returned)
- Binding ADR: `docs/adr/0022-delivery-approval-and-retention-claims.md`
- Accepted P2.1: `61301fd25ff7253693f367664ce99e13dfc88446`
- Accepted P2.2: `5187c080a7188a59989013defe7d07075662d007`
- Accepted P2.3: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`
- Accepted P2.4a: `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Production implementation files

- `src/codex_control/storage/delivery_records.py`
- `src/codex_control/storage/delivery_repositories.py`
- `src/codex_control/storage/approval_records.py`
- `src/codex_control/storage/approval_repositories.py`
- `src/codex_control/storage/retention.py`
- `src/codex_control/storage/__init__.py` (exports only)
- `src/codex_control/storage/turn_job_repositories.py` (narrow ADR-0022 delivery-shape materialization mode only)

No schema/DDL, SQLite kernel, errors, core, idempotency, transient-payload,
Telegram, Codex, application, deployment or production-state implementation
file was otherwise changed.

## Delivery evidence

- Exact CREATE/EDIT operations, PENDING/SENDING/CONFIRMED/UNKNOWN/FAILED
  states, immutable segment records and immutable plan items are exported.
- `plan` validates 1..4096 DISPLAY payload-backed items, assigns sequences,
  inserts all PENDING/attempt-0 rows and atomically advances the job to
  DELIVERY_PENDING/version+1.
- `claim_next` selects only the lowest eligible PENDING segment after checking
  earlier confirmation and rejecting SENDING/UNKNOWN/FAILED work. It commits
  PENDING->SENDING/attempt-1 and job->DELIVERING/version+1 in one write before
  any future transport effect.
- `finish_sending` captures CONFIRMED, UNKNOWN or FAILED exactly once. The
  final confirmation advances the job to DELIVERED; UNKNOWN advances it to
  DELIVERY_UNKNOWN and FAILED advances it to FAILED. There is no resend,
  retry, reopen or unknown-to-pending transition.
- Active payload owner/dialogue/hash coherence and delivery-aware job shapes
  fail closed. Terminal segment hashes remain durable while payload references
  may be NULL after safe deletion.
- Tests cover exact 4096, invalid 0/4097, plan coherence, restart, concurrent
  claims, confirmation, unknown/no-retry and corruption redaction.

## Approval evidence

- `ApprovalKind` is the exact accepted P1.7 enum; no competing kind enum is
  introduced. Public records expose one `wire_request_id` as signed-64 integer
  or bounded NUL-free string, not split database columns.
- `create_pending` requires a canonical CODEX_RUNNING job, exact job version
  and profile, validates optional canonical APPROVAL display ownership, blocks
  duplicate live profile+wire identity and permits reuse after terminal state.
- Approval state is PENDING/APPROVED/DENIED/EXPIRED/CANCELLED. Public methods
  are only get, create_pending, claim_callback and cancel_pending_for_job.
- `claim_callback` directly uses one `SqliteStorage.write` transaction. It
  checks callback existence, exact authorization and consumed state before
  subject inspection; it consumes stale/expired callbacks and atomically moves
  a fresh approval to APPROVED or DENIED. It never calls the P2.3 callback
  repository claim followed by a second approval transaction.
- Exact approval callback binding is approval subject, exact approval ID,
  PENDING expected state, approval_allow/approval_deny action and current job
  version. Only APPROVED/DENIED return an ApprovalRecord.
- Tests cover integer/string wire forms, live uniqueness, terminal reuse,
  atomic allow, privacy, stale consumption/replay, cancellation, due expiry,
  concurrent callback claims and redacted corruption.

## Retention evidence

- `RetentionRepository.sweep(limit)` is explicit and has no background loop;
  limit is exactly 1..1000 and each successful sweep uses one validated clock.
- Due PENDING approvals are first moved to EXPIRED without deleting approval
  rows. Payload candidates are deterministic by expiry then ID and at most the
  requested limit is selected/deleted.
- Delivery PENDING/SENDING/UNKNOWN payloads, pending approval payloads, active
  INPUT payloads (RECEIVED/CLAIMED/CODEX_STARTING/CODEX_RUNNING), and recovery-
  relevant OUTPUT payloads (CODEX_COMPLETED/DELIVERY_PENDING/DELIVERING/
  DELIVERY_UNKNOWN) are protected. Terminal-safe references may be deleted;
  SQLite SET NULL effects are limited to delivery/approval payload references.
- No jobs, delivery rows, approvals, ingress, callbacks, dialogues, tombstones
  or error metadata are deleted.
- Tests cover due approval expiry, bounded unreferenced deletion, future
  retention, terminal state safety, limit validation and restart persistence.

## Validation and regressions

- P2.4b unit: `6` tests.
- P2.4b integration: `10` tests.
- P2.4a: `8 / 31`.
- P2.3: `7 / 28`.
- P2.2: `6 / 20`.
- P2.1: `8 / 31`.
- P1.10 T0/T1/T2: `6 / 1 / 4`.
- Accepted pre-P2.4b full suite: `387`.
- Full-count formula: `387 + 6 + 10 = 403`.
- Observed full discovery: `403`, all passing.
- Required focused suites, compileall, public import check, DDL hash check,
  `git diff --check`, and changed-file security scan passed.

## Security and effects

- Repository diagnostics remain finite/redacted; records exclude raw callback
  token and payload content from repr where applicable. Test-only content and
  synthetic token hashes are confined to explicit temporary-DB tests.
- No credentials, private keys, auth files, raw callback tokens, production DB,
  production state root, environment dump, Telegram text, Codex prompt/output,
  command output or unsanitized exception was added to production code or
  evidence.
- Tests used temporary SQLite databases only. No Telegram API, Codex approval
  response, message send/edit, thread/turn effect, service or deployment effect
  occurred. No runtime dependency was added.
- Known P1.6 pending-task warning: observed in the final verbose discovery
  output; P2.4b introduced no warning.
- The final implementation commit SHA and push result are reported separately
  in the executor report after commit/push.

## Architect first repair pass

Rejected candidate: `e52bd9c4eb6a7c87ecd7fbb1b84297e4421ddf29`.

This is factual repair evidence only. P2.4b remains subject to independent
architect review and acceptance; this section does not claim acceptance and
does not start or recommend P2.5.

Repair and proof coverage:

- Global delivery job-shape repair: `_materialize_job()` now enforces the
  ADR-0022 shapes for every materialization, including ordinary
  `TurnJobRepository.get()` and approval/retention consumers. P2.4a-owned
  states retain their prior shape rules. The deferred DELIVERY_UNKNOWN fixture
  in `test_turn_jobs_payloads.py` was updated only to include its canonical
  sanitized error class.
- UNKNOWN payload invariant: PENDING, SENDING and UNKNOWN delivery segments
  require a canonical DISPLAY payload with exact job/dialogue ownership and
  hash. CONFIRMED and FAILED remain the only delivery terminal states that may
  retain a NULL payload reference after safe deletion.
- Delivery job/segment state coherence: public segment reads and delivery
  mutation claims validate the complete ordered plan. Canonical pre-delivery
  CODEX_RUNNING/CODEX_COMPLETED jobs with no plan return `()`, while delivery
  rows require coherent DELIVERY_PENDING, DELIVERING, DELIVERED,
  DELIVERY_UNKNOWN or delivery-FAILED state relationships.
- Approval corruption classification: create_pending first materializes the
  selected payload canonically. Corrupt content/hash/owner failures remain
  `INVARIANT_VIOLATION`; a canonical DISPLAY payload or canonical payload for
  another job/dialogue returns `STATE_CONFLICT`. Failed preconditions do not
  call the clock.
- Retention starvation repair: the sweep query applies delivery, approval and
  active-job protection predicates before deterministic `LIMIT`, orders by
  `expires_at_ms, payload_id`, and materializes all selected rows before any
  delete. Protected expired rows therefore cannot indefinitely hide eligible
  rows.
- Retention protection matrix: deterministic table-driven tests cover active
  INPUT in RECEIVED/CLAIMED/CODEX_STARTING/CODEX_RUNNING, recovery-relevant
  OUTPUT in CODEX_COMPLETED/DELIVERY_PENDING/DELIVERING/DELIVERY_UNKNOWN,
  DISPLAY referenced by PENDING/SENDING/UNKNOWN, APPROVAL referenced by
  PENDING, and terminal-safe DISPLAY/APPROVAL/OUTPUT deletion with FK
  references set NULL while jobs, delivery rows and approval rows remain.
- Approval proofs: live INTEGER and STRING wire duplicates are blocked while
  PENDING; signed-64 and string-length/NUL boundaries are covered; fresh DENY,
  callback expiry with and without due approval, privacy precedence for wrong
  user/chat over consumed/expired/stale subjects, and persisted payload
  corruption are covered.
- Delivery terminal/no-retry proofs: actual delivery FAILED captures the
  sanitized error, attempt 1 and IDLE dialogue; later claim is a conflict.
  EDIT confirmation mismatch is rejected without clock/mutation; version
  overflow and failed preconditions are checked before clock; UNKNOWN remains
  terminal and its payload is retained.
- Cancellation ownership: delivery claim, atomic approval callback claim and
  retention sweep use blocking-clock cancellation proofs. Repeated task
  cancellation does not escape the submitted DB operation, and each durable
  mutation occurs once.

Validation results for this repair pass:

- P2.4b unit: `6`.
- P2.4b integration: `23`.
- P2.4a unit/integration: `8 / 31`.
- P2.3 unit/integration: `7 / 28`.
- P2.2 unit/integration: `6 / 20`.
- P2.1 unit/integration: `8 / 31`.
- P1.10 T0/T1/T2: `6 / 1 / 4`.
- `BASE_ACCEPTED_FULL_TESTS=387`.
- `EXPECTED_FULL_TESTS=387 + 6 + 23 = 416`.
- `OBSERVED_FULL_TESTS=416`, all passing.
- Compileall, required import, DDL SHA, `git diff --check`, prior-slice
  regressions, T0/T1/T2 and existing focused P1 suites passed.
- The known P1.6 pending-task warning was not observed in this repair pass;
  no P2.4b warning was introduced.
- Tests used temporary SQLite databases only. No production state root,
  production DB, service, Telegram call, Codex call, secret or runtime
  dependency was touched.
