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
