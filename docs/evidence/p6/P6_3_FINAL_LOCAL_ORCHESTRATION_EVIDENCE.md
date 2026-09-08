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
