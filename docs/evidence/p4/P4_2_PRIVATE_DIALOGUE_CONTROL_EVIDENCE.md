# P4.2 private dialogue control implementation evidence

Date: 2026-09-07

This document records implementation evidence only. It does not claim architect
acceptance.

## Authority and scope

- Final architect base: `a4ad1f70cf2fa1abdecd8d37900a53de4fbfbe7d`.
- Initial freeze: `51a30afd77ba75baabd535d03abbfe0caee1b166`.
- Final callback-dispatch addendum: `a4ad1f70cf2fa1abdecd8d37900a53de4fbfbe7d`.
- Branch: `impl-p4-2-private-dialogue-control-2026-09-07`.
- Issue: #29.
- Binding ADR: ADR-0033.
- P4.2 production paths are `application/private_dialogue.py` and
  `adapters/telegram/private_dialogue_render.py`, with narrow exports and the
  additive `PrivateManagementRepository.peek_callback` storage operation.
- No schema, DDL, accepted P4.1 settings contract, accepted P3.4 production,
  or accepted P3.5 production file was changed.

## Dialogue-control surface

The implementation exports the exact frozen P4.2 request, status, reason,
error-category, error, panel-section, panel, result, and management-service
names. `PrivateCallbackRequest` is reused from P4.1. The pure renderer emits
only `text` and `reply_markup.inline_keyboard`; it emits no parse mode, markup,
URL, send, edit, HTTP, or network field. The zero-row representation is an
empty inline keyboard.

Status authority is `ApplicationRecoveryRepository.inspect()`. The status
projection includes only bounded server, mode, dialogue, profile, active-job,
model, and reasoning fields. The optional mode provider is read-only and exact
`ControllerMode` values are required. No private `ACTIVE` or group routing was
implemented.

No dialogue renders `RENDERED / NO_DIALOGUE`, with a static status panel,
`rows == ()`, zero callback rows, zero token-factory calls, and zero callback
TTL clock calls. Canonical schema-valid but noncanonical dialogue/job
corruption fails as P4.2 `INVARIANT`.

The table-driven integration test covers the requested matrix:

| Canonical state | P4.2 actions |
|---|---|
| NO_DIALOGUE | none |
| CREATING, CREATE_UNKNOWN, ERROR | REFRESH |
| IDLE | REFRESH, BEGIN_DELETE |
| IDLE + RECEIVED | REFRESH |
| TURN_RUNNING + CLAIMED/CODEX_STARTING | REFRESH |
| TURN_RUNNING + CODEX_RUNNING | REFRESH, INTERRUPT, BEGIN_DELETE |
| INTERRUPTING, TURN_UNKNOWN | REFRESH |
| DELETE_PENDING | REFRESH, BEGIN_DELETE |
| DELETING, DELETE_UNKNOWN | REFRESH |

## Callback authority and effects

`peek_callback` validates the exact lowercase 64-character SHA-256 hash,
materializes through the accepted callback materializer, and performs a read
with zero clock calls, mutation, claim, and consumption. P4.2 checks principal
authorization before hashing or peeking; non-P42 rows return
`BLOCKED / ACTION_UNAVAILABLE` without claim or consumption. The P4.1 token
continues to work in the accepted P4.1 handler.

P4.2 callback rows use only the exact P42 actions, the opaque 36-byte
`cc1:<32-character token>` grammar, SHA-256 token hashes, 900000 ms TTL, exact
dialogue version/state, and the specified status/interrupt/delete fingerprints.
Batch generation reads the clock once, performs no collision retry, and relies
on the accepted all-or-none storage batch. Existing and intra-batch collisions
map to `INVARIANT` without partial insertion.

After claim, exact action shape, version/state, canonical live snapshot, and
context fingerprint are revalidated. Mismatch returns `STALE / STALE_ACTION`
with no P3 effect, while the callback remains consumed. Missing, expired, and
replayed callbacks map to `CALLBACK_NOT_FOUND`, `EXPIRED`, and `ALREADY_USED`
respectively. Wrong principals return `UNAUTHORIZED` before callback lookup.

Interrupt callbacks construct exactly one `DialogueInterruptRequest` from the
canonical running dialogue/job and call only the injected P3.4 service. The
integration proof uses the real accepted `DialogueInterruptService`, temporary
SQLite, shared `ActiveTurnRegistry`, exact binding, and a fake lifecycle port.
Confirmed and reconciled outcomes map to `INTERRUPTED`; unknown, conflict,
blocked, rejected, and finite P3.4 errors map through the specified safe
categories/reasons.

Hard delete is always two-step. `BEGIN_DELETE` has zero P3.5, interrupt,
thread, and delete effect, then creates exactly new CONFIRM and CANCEL rows
bound to the same generation/context. Confirmation text states official
Codex thread deletion, delayed CodexControl purge, possible accepted P3.5
interrupt/reconciliation, and the absence of an empirical all-trace-erasure
claim. CANCEL has zero P3 effect and renders a fresh status only for the same
generation. Only `CONFIRM_DELETE` calls the injected P3.5 service exactly once.

The real IDLE P3.5 proof records one fake external thread/delete call, local
purge, one tombstone, and no second call on confirmation replay. The real
DELETE_PENDING continuation proof uses a fresh exact pending generation and
also records one fake external delete maximum. DELETING and DELETE_UNKNOWN
render REFRESH only. The running-delete proof uses a strict injected delete
spy: P4.2 delegates one exact request, does not access active-turn state, and
does not perform interrupt/quiescence/P1.9 work.

## Security and test execution

Focused P4.2 tests:

- `tests/unit/test_private_dialogue_control.py`: 5 tests.
- `tests/integration/test_private_dialogue_control.py`: 14 tests.
- Focused P4.2 total: 19 tests.

The focused tests cover frozen/redacted public records, exact unchanged P4.1
enums, renderer bounds, no-dialogue authority, the full requested status
matrix, peek semantics, P4.1 non-consumption, real P3.4 interrupt composition,
real P3.5 IDLE delete, DELETE_PENDING continuation, stale callbacks, replay,
wrong owner, collision/no-retry, and refresh-only terminal delete states.

Selected prior-slice regression run: 495 tests, `OK`. The full required
discovery run was:

`PYTHONPATH=src python3 -m unittest discover -s tests -v`

and returned 710 tests, `OK`.

Full arithmetic:

`EXPECTED_FULL_TESTS = 694 + 5 + 14 = 713`

`OBSERVED_FULL_TESTS = 713`

The inherited P1.6 pending-task warning was observed; no P4.2 task leak was
introduced or observed.

All tests use temporary SQLite and fake local lifecycle/rendering ports. No
real Telegram, network, bot token, Codex process, thread start, turn start,
interrupt, thread delete, approval, delivery, production database, or
production state effect was used.

The frozen schema-v1 DDL SHA-256 remains:

`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

Compile, import smoke, diff-check, and secret/content scans are run as final
handoff checks. No architect acceptance is claimed.
