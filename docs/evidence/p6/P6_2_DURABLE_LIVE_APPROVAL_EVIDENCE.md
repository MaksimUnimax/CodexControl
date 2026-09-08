# P6.2 durable live approval operator evidence

This is factual executor evidence for Issue #36. It does not claim architect acceptance.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `a7b5fa15713c6ff7138434215e9ac7ea25b38c79`
- Branch: `impl-p6-2-durable-live-approval-2026-09-08`
- Issue: `#36`
- Binding ADR: ADR-0040
- Accepted P6.1: `51902dcbd743cd91ad209cd96879b4ad45a26a9e`, reported full count 900
- Accepted P1.7: `bbd7445087dfb59185d49787d562637e282ba5aa`
- Accepted P4.3: `d053f24061e20aa44e07e5b92c9b92c6506647fd`

## Production paths

- `src/codex_control/application/live_approval.py`
- `src/codex_control/application/__init__.py`
- `src/codex_control/storage/approval_repositories.py`

P1.7 adapter/protocol, P4.3 private control, P3, P6.1, delivery and schema production files were not changed.

## Durable terminalization

`ApprovalRepository.terminalize_pending` is the sole additive repository method. It validates the approval ID and exact `EXPIRED`/`CANCELLED` target before SQL, materializes the canonical record, returns existing terminal records unchanged without a clock, uses one bounded clock for PENDING, applies the due-time guard for `EXPIRED`, permits live-running `CANCELLED`, and performs one PENDING-state CAS. It does not consume callback actions or mutate jobs/dialogues.

Focused integration evidence covers due expiry, not-due `STATE_CONFLICT`, live cancellation, already-APPROVED and already-DENIED zero-clock behavior, callback non-consumption by the terminalizer, and non-resurrection after terminalization.

## Application contract

- `P62_APPROVAL_TTL_MS = 900000`
- `P62_APPROVAL_PAYLOAD_RETENTION_MS = 900000`
- `ApprovalTurnBinding` is frozen, bounded, NUL-free and repr-redacted.
- `ApprovalDecisionSignal.notify()` is process-local, content-free and wake-only; durable state is re-read after wakes.
- The operator validates exact normalized P1.7 `ApprovalRequest` values and exact modern/legacy turn-binding rules.
- The exact current `CODEX_RUNNING` job/profile/thread/Codex-turn binding is read before publication.
- Waiter registration precedes application-clock read and PENDING publication.
- The common 900000 ms expiry is used for approval and optional APPROVAL payload.
- Context projection is only the exact bounded `context_lines` joined with `"\n"` and strict UTF-8 encoded. Empty context creates no payload.
- ID factory labels are `approval` and, only when needed, `approval_payload`; malformed IDs and collisions do not retry.
- Durable `APPROVED` maps to ALLOW. Durable `DENIED`, `EXPIRED` and `CANCELLED` map to DENY.
- Post-PENDING storage/read failures remain fail-closed waiting state; they do not fabricate DENY.

## P1.7 ownership and composition

`OwnedApprovalResponseService` accepts only an exact request object still owned by the configured exact `CodexProtocolClient`. It uses one persistent accepted `CodexApprovalBridge`, shields ordinary outer cancellation, validates the finite P1.7 result, and never retries a response.

Temporary SQLite and fake line transport integration covers:

- real P4.3 Allow -> durable APPROVED -> exact command ALLOW response once;
- real P4.3 Deny -> durable DENIED -> exact command DENY response once;
- pre-decision notification does not produce a response;
- fast decision notification is not lost;
- expiry produces durable EXPIRED and one DENY response;
- terminal winner ordering is preserved and later callbacks cannot revive;
- outer cancellation is deferred and later Allow produces one ALLOW;
- protocol terminal produces `RESPONSE_UNKNOWN`, zero response sends, and best-effort `CANCELLED` cleanup;
- same-value reconstructed requests on a new client are rejected before the bridge with zero replay.

Existing P1.7 focused tests continue to cover all five method mappings and ADR-0014 empty-grant DENY semantics.

## Effects and security boundary

Tests used temporary SQLite, fake Codex line transport, real transport-independent P1.7 protocol/bridge code and accepted P4.3 application callbacks. No Telegram, HTTP, network, Codex process, delivery effect, production database, production state root, service or secret was used. Stored approval details were synthetic bounded context only; raw protocol parameters, patch bodies, reasoning, environment, credentials and wire/approval/callback identifiers were not added to production logs or evidence.

## Verification

- P6.2 focused tests: 4 unit / 12 integration
- Focused regression command: 101 tests, `OK`
- Prior accepted full suite: 900
- Full command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- Observed full suite: 916 tests, failures 0, errors 0, `OK`
- Formula: `900 + 4 + 12 = 916`
- P1.6 pending-task warning observed: NO
- P1.6 warning introduced by P6.2: NO
- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS
- P6.2 import smoke: `P6_2_IMPORT_PASS`
- `git diff --check`: PASS
- Schema version: 2
- Historical v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`
- Schema-v2 migration SHA-256: `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`

Prior regression counts supplied by the accepted baseline were retained: P6.1 20/20; P5.3 11/6/2; P5.2 11/34; P2.C2 5/13/1; P5.1 7/8; P4.3 7/26/1; P4.2 5/29; P4.1 8/15; P3.5 12/25/1; P3.4 6/31; P3.3 5/25; P3.2 2/21; P3.1 11/26; P2.C1 5/1; P2.6b 5/12/8/3; P2.6a 4/28; P2.5 4/18; P2.4b 6/25; P2.4a 8/31; P2.3 7/28; P2.2 6/20; P2.1 8/31; P1.9 15; P1.8 28; P1.7 approval focused 22; P1.10 6/1/4.

Durable approval metadata is not P1.7 wire-response authority. Restart/new-client evidence confirms that old wire ownership is never reconstructed and no response is replayed from an ApprovalRecord.

## Architect first repair

This is factual executor evidence for the first repair pass. It does not claim architect acceptance.

- Rejected candidate: `4d7e2e1edf3255cd91a18c974e4cfec5d557fcd1`
- Architect review: `5580627914`
- Repair parent: `4d7e2e1edf3255cd91a18c974e4cfec5d557fcd1`

The repair gives each `_SignalWaiter.wait()` helper exact finite ownership. Every loop iteration observes or cancels and joins its wake task in `finally`; public operator cancellation therefore cancels and joins the wake helper while preserving `CancelledError`. The strengthened protocol-terminal proof captures a genuinely pending wake helper before terminating the exact client, then observes `RESPONSE_UNKNOWN`, zero wire responses, durable `CANCELLED` cleanup, an empty signal registry, a done wake helper, a done expiry helper, and no remaining P6.2 task. `P6_2_PROTOCOL_TERMINAL_WAKE_TASK_LEAK=NO`.

The injected expiry seam now requires an actual async callable, including an async `__call__` object. Synchronous lambdas, normal functions returning `None`, synchronous callable objects, and non-callable values are rejected with `INVALID_ARGUMENT` before storage access. The matrix records zero storage reads, zero storage writes, and zero approval rows for each rejected value. The malformed synchronous seam cannot publish PENDING or consume an expiry opportunity. The first-repair `_sleep_expiry()` awaited exactly `self._sleep(900.0)`, but its runtime-exception path still returned normally; the second repair below adds the required non-authority distinction.

The restart proof now feeds a supported approval envelope through a real old `CodexProtocolClient`, obtains the exact request, proves old ownership true, starts owned handling, proves the exact approval is durably PENDING with metadata, closes the old client before a decision, and observes canonical `RESPONSE_UNKNOWN` with zero old wire responses and durable `CANCELLED` cleanup. After close/reopen SQLite, the metadata persists independently of the wire object. A new client owns neither the stale old object nor a reconstructed `InboundServerRequest` carrying the same wire ID; both are rejected before the bridge and new-client response calls for that ID remain zero. Wire-value equality is not ownership.

Existing real P4.3 Allow/Deny, exact method-specific one-attempt P1.7 responses, duplicate/sibling protection, expiry and durable race winner, outer cancellation followed by later Allow, protocol-terminal cleanup, storage-after-PENDING fail-closed behavior, safe payload projection, and empty-context deny-only behavior remain covered. Focused counts are 6 unit tests and 13 integration tests.

Verification for this repair used temporary SQLite and fake transport only. No Telegram, HTTP/network, Codex process, model/list, thread/start, turn/start, interrupt, delete, delivery, production database, production state root, service, or secret effect was used. Schema remains version 2 with the historical v1 DDL SHA-256 `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c` and v2 migration SHA-256 `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`. The full suite observed 919 tests with zero failures and zero errors, matching `900 + 6 + 13 = 919`.

The full-suite run showed the known historical P1.6 pending-task warning from turn-lifecycle tests; no P6.2 pending-task warning was observed, and no P1.6 warning was introduced by this repair. The repair changes only `src/codex_control/application/live_approval.py`, the focused unit/integration tests, and this evidence file. Architect-owned files, schema, P1.7, P2.4b, P4.3, P3, P5, and P6.1 production paths were not changed.

## Architect second repair

This is factual executor evidence for the second repair pass. It does not claim architect acceptance.

- Initial candidate: `4d7e2e1edf3255cd91a18c974e4cfec5d557fcd1`
- First repair: `90fee925f192f96f2ef72fcdc0bf2ec1e9358ad2`
- Second architect review: `5580866202`
- Repair parent for this section: `90fee925f192f96f2ef72fcdc0bf2ec1e9358ad2`

`_sleep_expiry()` now returns the private finite result `True` only after the exact `await self._sleep(900.0)` completes successfully, and `False` when the valid async seam raises a runtime exception. `_wait_for_decision()` observes that result once and invokes `terminalize_pending(..., EXPIRED)` only for exact `True`. A failed async timer is therefore not expiry authority: it does not terminalize, retry, poll, fabricate ALLOW/DENY, or produce an unobserved task exception. Its one timer opportunity is consumed while the operator remains fail-closed waiting for a durable signal or protocol-terminal cancellation.

The deterministic failing-sleeper integration proof uses `async def failing_sleeper(delay)` with exact delay `900.0` and synthetic failure. Before any durable callback decision, the approval remains exact `PENDING`, the P6.2-local EXPIRED terminalizer call count is `0`, and wire response calls are `0`. A real P4.3 Allow followed by `signal.notify()` produces durable `APPROVED`, exactly one P1.7 ALLOW response, no replacement DENY, and no pending P6.2 helper task. A separate failing-timer protocol-terminal proof produces `RESPONSE_UNKNOWN`, best-effort durable `CANCELLED`, zero response sends, an empty waiter registry, and zero P6.2 task leak.

The direct unit proof records successful async timer authority as `True` and failed async timer authority as `False` without exposing the runtime exception. First-repair wake-task ownership, protocol-terminal cleanup, strict async-sleep constructor validation, real old-client ownership/restart boundary, and new-client zero replay proofs remain unchanged.

Focused counts for this second repair are 7 unit tests and 15 integration tests. The accepted full baseline remains 900; the expected full count is `900 + 7 + 15 = 922`. The full suite observed 922 tests with zero failures and zero errors, `OK`; compileall, P6.2 import smoke, `git diff --check`, schema-version/hash verification, and the changed-code/test secret scan all passed. The known historical P1.6 pending-task warning was observed; no P6.2 pending-task warning was observed and no P1.6 warning was introduced by this repair. No schema, P1.7, P2.4b, P4.3, P3, P5, P6.1, production state root, service, Telegram, network, Codex, delivery, or architect-owned file was changed. Issue #36 remains open and P6.3/P7 were not started.
