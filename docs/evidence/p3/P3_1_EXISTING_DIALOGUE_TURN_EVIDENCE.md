# P3.1 existing-dialogue turn application evidence

Date: 2026-09-06

This is executor evidence for Issue #19. It does not claim architect acceptance
and it does not start P3.2.

## Authority and scope

- corrected base: `cc89b26b8b28077d71e6ae9d0db70edd600f9705`
- branch: `impl-p3-1-existing-dialogue-turn-service-corrected-2026-09-06`
- Issue: `#19`
- binding ADRs: ADR-0026 and ADR-0027
- accepted P2.C1: `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`
- rejected reference candidate: `05a268781b4b7189271b64f55a3b21f30c259269`
- frozen DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Changed files

Production is limited to:

- `src/codex_control/application/__init__.py`
- `src/codex_control/application/existing_dialogue_turn.py`

Tests/evidence are limited to the two requested focused test modules and this
document. No accepted P1/P2 production code, schema, adapter, dependency,
ADR, roadmap or current-work file was changed.

## Contract and replay proof

The service exposes the exact P3.1 status/reason enums, finite redacted error,
frozen request/result records, narrow asynchronous ports, fixed retention
constants and an `execute`-only public service surface. Static request
validation precedes the first storage read.

Existing ingress is inspected first. CONTROL/ignored duplicates are returned
without configuration or effect dependencies. Exact JOB identity and retained
INPUT are validated. ADR-0027 replay is represented in the application by the
exact required/optional state sets: missing INPUT is an invariant in active
states and a no-reconstruction DUPLICATE in optional terminal/delivery states.
Corrupt or multiple retained INPUT remains an invariant. Orphan JOB metadata
returns the accepted post-hard-delete shape only when no live dialogue exists.

The integration suite covers retained-input replay, retention-compatible replay
after accepted `RetentionRepository.sweep`, active missing INPUT, corrupt
retained INPUT, non-JOB duplicate and orphan paths. Duplicate-first tests use
failing catalog/workdir/clock/ID/turn dependencies to prove zero calls.

## Preflight and admission

New updates require the canonical server-bound IDLE dialogue, matching settings,
an explicit configured profile, an authenticated catalog for the bound profile,
an explicitly resolved non-hidden descriptor, concrete reasoning effort and a
trusted working directory. Hidden, missing and unsupported models fail closed.
Blocked/busy matrices prove no ingress, job, INPUT or P1 start.

Admission captures the logical model, concrete effort, immutable dialogue
binding, UTF-8 INPUT and one-hour expiry. Accepted P2 mutation repositories use
the same injected clock. Generated IDs are opaque, bounded and fail closed on
invalid output or collision without retry.

## Durable effect and concurrency

The admitted path rereads the exact dialogue binding, then observes the durable
ordering `RECEIVED -> CLAIMED -> CODEX_STARTING` before calling P1. Confirmed
starts bind the exact returned turn, persist `CODEX_RUNNING`, wait exactly once,
and finish atomically. Start rejected/unknown, local lifecycle errors,
unexpected start failures, binding mismatch, wait failures and terminal binding
mismatch are covered without blind retry.

Same-update concurrency proves one job, one INPUT and at most one start. A
different-update race proves winner accounting from returned durable jobs rather
than assuming which caller loses; the loser is BUSY/blocked and is not queued.
Post-admission repeated caller cancellation is shielded by the single owned
execution task and still reaches terminalization.

## Terminal and security proof

COMPLETED, FAILED and UNKNOWN terminal paths preserve ordered visible messages
as UTF-8 joined by `\n\n`. Completed output targets one hour; failed/unknown
partial output targets 24 hours; empty projected output creates no OUTPUT ID or
payload. The maximum projection arithmetic is `2,000,000 * 4 + 255 * 2 =
8,000,510 < 8,388,608`.

Request/output content, CODEX_HOME, adapter/repository exception bodies,
working-directory details and clock sentinels are absent from generic repr/error
surfaces. Tests use temporary SQLite and fake catalog, workdir and turn ports;
there is no real Codex, Telegram, network or production-state effect.

## Required regression and count record

The focused P3.1 commands are run from the corrected base and their exact
results are recorded below after execution:

- P3.1 unit: 10 tests
- P3.1 integration: 20 tests
- accepted P2.C1 integration: 5 tests
- accepted P2.C1 acceptance: 1 test

Prior authority counts to preserve:

- P2.6b: contract 5, restart 12, replay 8, abrupt 3
- P2.6a: 4 unit / 28 integration
- P2.5: 4 / 18
- P2.4b: 6 / 25
- P2.4a: 8 / 31
- P2.3: 7 / 28
- P2.2: 6 / 20
- P2.1: 8 / 31
- P1.10: 6 / 1 / 4

The accepted corrected pre-P3.1 full count is 506. The expected full count is
`506 + 10 + 20 = 536`, assuming only these two requested test modules are
added.

The known P1.6 pending-task warning was observed during the focused P1 adapter
run and the full suite. It is pre-existing adapter-test behavior; no P3.1
resource leak or warning introduction was established.

P3.2 is not started. No architect acceptance is claimed.
