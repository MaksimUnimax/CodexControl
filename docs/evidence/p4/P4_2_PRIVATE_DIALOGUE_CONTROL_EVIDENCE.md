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
- `tests/integration/test_private_dialogue_control.py`: 14 tests in the
  candidate-era evidence; the final first-repair count is recorded below.
- Focused P4.2 total: 19 tests in the candidate-era evidence.

The focused tests cover frozen/redacted public records, exact unchanged P4.1
enums, renderer bounds, no-dialogue authority, the full requested status
matrix, peek semantics, P4.1 non-consumption, real P3.4 interrupt composition,
real P3.5 IDLE delete, DELETE_PENDING continuation, stale callbacks, replay,
wrong owner, collision/no-retry, and refresh-only terminal delete states.

Selected prior-slice regression run: 495 tests, `OK`. The candidate-era
full-discovery count and arithmetic were superseded by the first-repair
verification recorded below; this section intentionally has no final full
count of its own.

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

## Architect first repair

This section records factual first-repair evidence only. It does not claim
architect acceptance, close Issue #29, change main, or authorize P4.3/P5.

### Authority and scope

- Rejected candidate: `41e94a1aefd20b86c9f4f4d994c9bde6947b3986`.
- Architect review/addendum comment: `5568089991`.
- Repair parent remained the rejected candidate exactly; no reset, rebase,
  merge, force-push, main change, ADR change, schema/DDL change, or accepted
  prior-slice production rewrite was made.
- Changed paths are the P4.2 application mapper, the additive private-management
  storage operation and export, and the P4.2 integration proofs. The pure
  renderer, accepted P4.1 settings service, accepted P3.4/P3.5 services and
  all earlier production paths remain unchanged.

### Cancellation and confirmation authority

`P42_CANCEL_DELETE` now claims its own callback, revalidates the canonical
dialogue version/state/delete fingerprint, and then performs one SQLite writer
transaction over callback metadata. The transaction materializes every exact
matching `P42_CONFIRM_DELETE` row for the subject fingerprint, version/state,
operator and private chat before changing anything. If a matching confirmation
was claimed before expiry it returns `CONFIRM_ALREADY_CLAIMED`, so Cancel maps
to `STALE / STALE_ACTION` with no delete or interrupt call. Otherwise every
unconsumed matching confirmation is revoked using a canonical consumed time
clamped to its own `[created_at_ms, expires_at_ms]` interval. Expired unclaimed
confirmations do not block cancellation.

The focused proofs establish successful Cancel revokes all same-context
confirmation panels, old confirms replay as `ALREADY_USED`, a claimed-confirm
race returns stale while the already-started injected delete remains the sole
possible delete call, expired unclaimed confirmation does not block, and a
different generation/context remains unconsumed by the current cancellation.
The stale-confirm proof changes an IDLE dialogue through the accepted
`DeletionRepository` transition and proves zero delete calls followed by
`ALREADY_USED` replay. The running-delete proof asserts the exact
`DialogueDeleteRequest` from the canonical snapshot, with no local interrupt.

### Strict P3 result-shape validation

Before mapping injected P3 results, P4.2 now requires the exact accepted
status/reason relations. P3.4 accepts reason `None` for CONFIRMED, RECONCILED,
UNKNOWN and REJECTED; exactly STALE_REQUEST for CONFLICT; and only the five
canonical blocked reasons for BLOCKED. P3.5 accepts reason `None` for DELETED,
FAILED and UNKNOWN; exactly STALE_REQUEST for CONFLICT; and only the six
canonical blocked reasons for BLOCKED. Impossible finite pairs fail closed as
`PrivateDialogueError(INVARIANT)` without a panel or destructive duplicate
call. Focused tests cover malformed BLOCKED/REJECTED pairs and canonical
REJECTED, BLOCKED, and CONFLICT mappings for both services.

### Authentication, identity and existing behavior proofs

A direct real P4.2 token proof invokes a live P42 token from the wrong private
principal first, observes `UNAUTHORIZED`, verifies `consumed_at_ms IS NULL`,
then invokes it with the correct principal successfully. The real accepted
P3.4 proof now requires exact binding identity (`is`), and the P4.1 token sent
to P4.2 remains `ACTION_UNAVAILABLE`, unconsumed, and usable by P4.1. Existing
P4.2 proofs remain green for no-dialogue zero authority, canonical inspect,
action availability, opaque hashes/TTL, exact fingerprints, BEGIN_DELETE
zero-effect, IDLE delete, DELETE_PENDING continuation, refresh-only
DELETING/DELETE_UNKNOWN, and no private ACTIVE/group routing.

### Verification and regression counts

- Final P4.2 focused counts: unit `5`, integration `27`; total `32`.
- Accepted pre-P4.2 full baseline: `694`.
- Required full command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- Final observed full result: `726` tests, `OK`.
- Exact arithmetic: `EXPECTED_FULL_TESTS = 694 + 5 + 27 = 726` and
  `OBSERVED_FULL_TESTS = 726`; the formula matches.
- Prior focused regressions passed at the required authority counts: P4.1
  `8/15`; P3.5 `12/25/1`; P3.4 `6/31`; P3.3 `5/25`; P3.2 `2/21`; P3.1
  `11/26`; P2.C1 `5/1`; P2.6b `5/12/8/3`; P2.6a `4/28`; P2.5 `4/18`;
  P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`; P2.2 `6/20`; P2.1 `8/31`;
  P1.9 `15`; P1.8 `28`; P1.10 `6/1/4`.
- The known P1.6 pending-task warning was observed during full discovery;
  no P4.2-owned task leak was observed or introduced.
- Compileall, P4.2 import smoke, `git diff --check`, exact DDL hash check,
  changed-file boundary checks and secret/effect scans passed.
- DDL SHA-256 remains
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

All repair tests used temporary SQLite and fake local lifecycle/effect ports.
No real Telegram, network, Codex, thread start, turn start, interrupt,
thread/delete, approval, delivery, production database, production state root,
service, credential or secret effect occurred. No raw callback token/hash,
thread/job/turn ID, prompt/output, environment, credential or raw exception
body was added to evidence or generic diagnostics. P4.2 remains not
architect-accepted.
