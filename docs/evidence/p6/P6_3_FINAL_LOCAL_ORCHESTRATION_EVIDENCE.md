# P6.3 final local orchestration evidence

This record is for Issue #37 and ADR-0041 on branch
`impl-p6-3-final-local-orchestration-2026-09-08`.

## Scope and base

- Architect base: `6dd277b11c10f16e3955b452f1abe7163a1846f5`.
- ADR: `docs/adr/0041-final-local-orchestration-and-fake-p6-acceptance.md`.
- Accepted authorities: P6.2 `51a681b09cf2eb2e75fbd2663f88b7a96077a39d`, P6.1 `51902dcbd743cd91ad209cd96879b4ad45a26a9e`, P5.3 `c23d9356e7033ce44a62933f7749250433d49f61`, and P3.5 `6145d262787465ac6b4a17327114211cd86e8104`.
- Production changes are limited to `application/local_orchestration.py`, `application/__init__.py`, and the authorized delivery-discovery method in `storage/turn_job_repositories.py`.
- No schema, accepted prior-slice production state machine, Telegram transport, Codex process, deployment, or P7+ change was made.

## Composition evidence

The lifecycle wrapper uses one accepted P1.6 adapter. A capture proxy delegates one runtime acquisition during start, returns that same object to P1.6, retains its identity on confirmed start, and does not reacquire it for wait or interrupt. A concurrent start fails busy without queuing. The CODEX_STARTING recovery preflight completes before the single bounded work-status CREATE attempt.

The work-status texts are the exact Russian acknowledgement, failure, and uncertainty forms required by ADR-0041. They contain only server, profile, model, and reasoning metadata and are bounded at 1024 characters. The acknowledgement is process-local, one-attempt, and absent from startup recovery; a confirmed hint is used only as the P6.1 first-segment EDIT target.

The wait path owns the turn wait, one request dequeue, and one P6.2 handler at a time. Sequential approvals are supported. Accepted P4.3 callback outcomes wake the shared signal exactly once; the durable callback result remains separate from the P1.7 wire decision. The real fake acceptance exercises Allow and P1.7's method-specific single response.

Turn/request races are fail-closed: a captured request receives one immediate method-specific deny, a live approval is allowed to finish under one runtime shutdown and projects RESPONSE_UNKNOWN, and no approval wire response is fabricated after terminal ownership. The confirmed-start/unconsumed-lease path shuts down the captured runtime once and clears the process-local lease.

## Delivery and startup evidence

`list_delivery_candidates(limit=...)` is the only new repository surface. It validates an exact non-boolean integer from 1 through 4096, performs one read-only callback, uses no clock and no write, selects only CODEX_COMPLETED, DELIVERY_PENDING, and DELIVERING, and orders by created time then job ID.

Startup invokes accepted P3.5 recovery first, cancels pending approvals only when that recovery terminalized the active job, and then performs bounded P6.1 delivery recovery with `status_message_id=None`. It processes at most 256 candidates, performs the final discovery read, and returns READY or LIMIT_REACHED. CODEX_COMPLETED, stranded SENDING, and confirmed-prefix cases remain governed by P6.1, including no resend of a confirmed segment and zero Telegram calls for stranded SENDING.

## Test evidence

The final fake acceptance uses temporary SQLite, a fake Telegram port, a fake runtime manager, the real transport-independent Codex protocol client, and real accepted P3/P4.3/P5/P6.1/P6.2 application boundaries. It verifies raw adapter normalization, acknowledgement-before-turn/start, approval dequeue and Allow, ordered multi-segment output, P6.1 EDIT then CREATE delivery, final DELIVERED state, no duplicate segment, and no P6.3 helper leak.

Focused P6.3 counts are 4 unit tests, 2 integration tests, and 9 final acceptance tests. The full suite observed 937 tests: `922 + 4 + 2 + 9`, with zero failures and zero errors. Compileall, public import smoke, and `git diff --check` passed.

The full run showed the known historical P1.6 pending collector warning. No P6.3 pending-task warning was observed. No real Telegram call, network effect, Codex process call, delivery service outside the fake, production database, production state root, credentials, or environment content was used.

## Schema and security facts

- `SCHEMA_VERSION=2`.
- Historical v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Schema-v2 migration SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- Public result reprs and local errors redact IDs, content, payloads, raw exceptions, and runtime details.
- Secret scan found no credentials, tokens, CODEX_HOME value, or production paths in the P6.3 production/evidence changes.

This evidence does not claim architect acceptance, close Issue #37, or mark P6 complete.

## Architect first repair

This section records the first repair above rejected candidate
`94238289602d0f52677bc21a5e847da3f1a97425`, against architect reviews
`5583120656` and `5583148103`. It is repair evidence only and does not claim
architect acceptance.

### Repair closure

- The constructor now requires the exact shared `ApprovalDecisionSignal`
  instance owned by `ApprovalAwareTurnLifecycle`; a mismatched signal is
  rejected before storage or external effects.
- A terminal `wait_turn` retires the exact live turn lease after joining its
  P6.3 helpers. The ACK hint remains independently available until final
  delivery or terminal safe-status handling, then is cleared.
- With the first final Telegram effect event-blocked, a second fresh prompt is
  admitted, reaches `CODEX_RUNNING`, receives a distinct binding and hint, and
  does not receive a false `TURN_OPERATION_BUSY`.
- Wait-pump setup failure and cancellation after wait ownership each shut down
  the captured runtime at most once, retire the exact lease, preserve the hint
  for the UNKNOWN path, and leave no helper task or approval response.
- Direct discovery covers CODEX_COMPLETED, DELIVERY_PENDING, and DELIVERING;
  it excludes RECEIVED, CLAIMED, CODEX_STARTING, CODEX_RUNNING, DELIVERED,
  FAILED, UNKNOWN, and DELIVERY_UNKNOWN. Ordering is `created_at_ms ASC,
  job_id ASC`, limit is exact, invalid bool/0/4097 values are rejected, and
  discovery performs zero clock calls and zero writes.

### Startup, status, and approval matrix

- The main fake path proves effective SLEEP, `recover_startup()` READY, then
  ACTIVE and live input; P6.3 does not start polling.
- Stranded SENDING is not resent: Telegram calls are zero and the job becomes
  DELIVERY_UNKNOWN with accepted Telegram recovery ambiguity.
- A confirmed prefix is not replayed; startup resumes at the pending suffix.
- A recovered active job is marked UNKNOWN and its dialogue TURN_UNKNOWN before
  its durable pending approval is cancelled; no old approval response or ACK is
  replayed. Delivery recovery is bounded at 256 candidates, performs one final
  probe, returns LIMIT_REACHED, has no background continuation, and a later
  explicit recovery can continue.
- Raw authorized group STATUS is a pure fleet projection with payload exactly
  `{"text": <str>}` and zero Telegram/P3/job/mode/epoch mutation.
- FAILED and UNKNOWN live outcomes each avoid P6.1 and make at most one exact
  safe terminal status effect, without raw error content, retry, or durable
  delivery plan; hints clear after handling.
- Two sequential approvals use one captured runtime/client/binding and produce
  exactly one Allow and one Deny response, with no runtime reacquisition.

### Identity and race proofs

- Clean terminal/request-get and captured-request races are both covered. The
  clean race preserves the terminal result; the captured anomaly creates no
  durable pending approval, makes one method-specific deny, shuts down once,
  and projects UNKNOWN.
- An equal-but-reconstructed `TurnBinding` is rejected for both wait and
  interrupt. Concurrent direct start reserves once and the second call fails
  immediately with TURN_OPERATION_BUSY without queueing or external effects.
- Main Allow and Deny paths begin with raw Telegram-like private updates and
  pass through `TelegramPrivateUpdateAdapter` before accepted application
  requests are constructed.
- The focused acceptance suite observes zero P6.3 helper-task leaks.

### Final verification

- Final focused counts: 6 unit, 3 integration, and 23 acceptance tests.
- Full discovery: `954 = 922 + 6 + 3 + 23`, zero failures, zero errors, `OK`.
- Required prior regression boundaries were rerun green, including P6.2,
  P6.1, P5.3/P5.2, P4.3, P3.5/P3.4, P1.7 approvals, and P1.10; additional
  Codex runtime/version checks were also green.
- `SCHEMA_VERSION=2` and the historical v1 and v2 migration SHA-256 values
  remain unchanged. Compileall, P6.3 import smoke, `git diff --check`, and the
  repair-code/test secret scan passed. The known P1.6 warning remains
  pre-existing; no P6.3 pending-task warning was observed.
