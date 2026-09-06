# P2.5 implementation evidence — delete tombstones and error fingerprints

Status: implementation evidence only. This document does not claim architect
acceptance and does not select or recommend a later roadmap slice.

## Authority and base

- Base SHA: `521453dbd73aab6c6f52defe770af3bd2e265a95`
- Branch: `impl-p2-5-delete-tombstones-errors-2026-09-06`
- Issue: `#16`
- Binding ADR: `docs/adr/0023-hard-delete-tombstones-and-error-fingerprints.md`
- Accepted P2.1: `61301fd25ff7253693f367664ce99e13dfc88446`
- Accepted P2.2: `5187c080a7188a59989013defe7d07075662d007`
- Accepted P2.3: `0d8f34beaa35a2bc02b349abba9507ebb9bc3802`
- Accepted P2.4a: `ca5b5cc19ac9278377b96abec46c523603b2ff47`
- Accepted P2.4b: `1dedc737ffa3092ba0dbcd8618a57fa6c351b849`
- Frozen schema-v1 DDL SHA: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Production implementation

Added:

- `src/codex_control/storage/deletion_records.py`
- `src/codex_control/storage/deletion_repositories.py`
- `src/codex_control/storage/error_records.py`
- `src/codex_control/storage/error_repositories.py`

Updated only for the assigned surface:

- `src/codex_control/storage/__init__.py`
- `src/codex_control/storage/core_repositories.py` — canonical ADR-0023
  materialization for DELETE_PENDING, DELETING and DELETE_UNKNOWN.

The existing P2.2 integration fixture was narrowed to the ADR-0023 canonical
deletion shapes. No schema, DDL, kernel, error taxonomy, prior repository or
non-storage production file was changed.

## Delete states and readiness

The global materializer now requires:

- DELETE_PENDING: non-null thread and null last error class;
- DELETING: non-null thread and null last error class;
- DELETE_UNKNOWN: non-null thread and sanitized non-null last error class.

`claim_delete_intent` accepts only canonical IDLE with a bound thread. Zero
jobs and DELIVERED/FAILED history are safe. RECEIVED, CLAIMED, CODEX_STARTING,
CODEX_RUNNING, CODEX_COMPLETED, UNKNOWN, DELIVERY_PENDING, DELIVERING and
DELIVERY_UNKNOWN block with STATE_CONFLICT. A PENDING approval on a dialogue
job also blocks. Corrupt canonical rows fail with INVARIANT_VIOLATION before
the mutation clock.

## Claims and outcome capture

The intent and deleting claims each use one write transaction, exact version
CAS, one monotonic timestamp and one version increment. Concurrent same-version
intent calls have one winner. Closing and reopening after each claim preserves
the exact profile/thread binding. `claim_deleting` does not call P1.9 or any
external service.

`mark_delete_unknown` durably captures DELETE_UNKNOWN with a sanitized class,
and `mark_delete_error` durably captures ERROR for deterministic local or
pre-dispatch failure. Both retain the binding, increment once, and have no
retry/reconciliation API.

## Confirmed finalization and purge

`finalize_confirmed` accepts only exact DELETING and exact version. It calls
the repository clock once after all semantic preconditions, derives the
thread identity SHA-256 internally from UTF-8, records the current DELETING
version as stale_generation, and requires strict tombstone expiry after the
effective deletion timestamp.

Within one transaction it counts jobs, dialogue/job-owned payload rows once,
delivery segments and approvals; inserts the content-free tombstone; and
deletes the exact DELETING dialogue CAS row. Schema-v1 cascades purge the
dialogue, jobs, payloads, delivery segments and approvals. Error rows remain
with their dialogue/job foreign keys cleared to NULL. Ingress and callback
idempotency metadata remains present.

The immutable result contains only the tombstone and the four pre-delete row
counts. Tests prove hash authority, no raw thread in the tombstone/result,
restart persistence, strict expiry rollback, collision rollback, clock-failure
rollback, and repeated cancellation ownership through the submitted
transaction.

## Error fingerprints

`ErrorFingerprintRepository` exposes only `get` and `record`. Records contain
the canonical lower-case SHA-256 fingerprint, sanitized error class, count,
first/last timestamps and optional dialogue/job IDs. No message, exception,
traceback, stdout, stderr, prompt, response, token or environment field is
accepted or retained.

First records use one clock and count one. Identical duplicates preserve the
first timestamp, increment exactly once and update last-seen monotonically.
Conflicting class/entity metadata and signed-64 count overflow fail closed
without a clock. Concurrent identical first records serialize to one row with
count two. Entity references require canonical existing rows and coherent
dialogue/job ownership; after hard delete, references clear while the
fingerprint record remains unchanged.

Tombstone and error materialization rejects noncanonical hashes, REAL integer
fields, invalid classes and invalid timestamp ordering with redacted
INVARIANT_VIOLATION diagnostics.

## Tests and validation

Focused counts:

- P2.5 unit: `4`
- P2.5 integration: `11`
- P2.4b: `6 / 25`
- P2.4a: `8 / 31`
- P2.3: `7 / 28`
- P2.2: `6 / 20`
- P2.1: `8 / 31`
- P1.10 T0/T1/T2: `6 / 1 / 4`

Full discovery arithmetic: `418 + 4 + 11 = 433`; observed full discovery:
`433` tests, all passing. Compile, public import, exact DDL hash and
`git diff --check` passed.

The known pre-existing P1.6 pending-task warning was observed during the
focused P1 turn-lifecycle run and full discovery. It was not introduced by
P2.5. No P2.5-owned task warning was observed.

## Scope and security facts

All databases were temporary SQLite databases. No Codex, P1.9 thread/delete,
Telegram, network, service, deployment or production state effect was used.
No credentials, tokens, private keys, production paths, prompt/response
content, raw external error body, traceback, stdout/stderr or environment dump
was added. No architecture/ADR, schema, roadmap or current-work authority
file was edited.

## Architect first repair pass

This is factual repair evidence only. P2.5 remains subject to independent
architect review and acceptance; this section does not claim acceptance and
does not start or recommend P2.6.

- Rejected candidate repaired: `24e76e9913069b0b38e92ac33aedb0aceace0c24`.
- Original architect P2.5 base: `521453dbd73aab6c6f52defe770af3bd2e265a95`.

Repair and proof coverage:

- Delete readiness now reuses accepted P2.4b segment materialization and
  requires a non-empty all-CONFIRMED plan for DELIVERED jobs. A Codex-level
  FAILED job with zero delivery rows remains safe; a delivery-owned FAILED
  job requires exactly `C* F P*` with one FAILED segment. Impossible plans are
  invariant violations before the deletion clock, including after the
  dialogue has entered DELETE_PENDING or DELETING.
- `claim_delete_intent` and `claim_deleting` independently reject any
  pre-existing same-dialogue tombstone before clock use or state mutation.
  Finalization retains its collision guard and does not overwrite tombstones.
- Error `get` and `record` now fetch all ASCII-case-insensitive fingerprint
  aliases, require at most one row, and require the stored row itself to be
  canonical lowercase. Uppercase-only and dual-case aliases fail closed with
  no mutation or clock call.
- Tests bind exact `stale_generation` to the DELETING version, including
  signed-64 MAX finalization without a version increment. Wrong-version,
  wrong-state and missing-dialogue finalization paths prove zero clock,
  tombstone and purge effects.
- Deletion transition overflow is covered for intent, deleting, unknown and
  error claims at signed-64 MAX. Public expected-version and tombstone-expiry
  numeric boundary matrices distinguish static validation from the
  post-clock expiry relation.
- Error entity-binding collision and persisted last-seen-before-first-seen
  corruption are covered with finite/redacted invariant diagnostics.
- Finalization cancellation uses `asyncio.to_thread(started.wait, 2)` event
  synchronization followed only by `asyncio.sleep(0)` loop yields. Repeated
  cancellation remains attached to one owned transaction and produces one
  tombstone and one purge.

Validation results for this repair pass:

- P2.5 unit: `4`.
- P2.5 integration: `18`.
- P2.4b unit/integration: `6 / 25`.
- P2.4a unit/integration: `8 / 31`.
- P2.3 unit/integration: `7 / 28`.
- P2.2 unit/integration: `6 / 20`.
- P2.1 unit/integration: `8 / 31`.
- P1.10 T0/T1/T2: `6 / 1 / 4`.
- `BASE_ACCEPTED_FULL_TESTS=418`.
- `EXPECTED_FULL_TESTS=418 + 4 + 18 = 440`.
- `OBSERVED_FULL_TESTS=440`, all passing.
- Compileall, required public import, frozen DDL SHA, `git diff --check`,
  prior-slice regressions and focused P1 suites passed.
- The known pre-existing P1.6 pending-task warning was observed during the
  focused P1 turn-lifecycle run and was not introduced by P2.5.

Security and effects:

- All repair tests used temporary SQLite databases and test-only SQL fixtures.
- No Codex, Telegram, thread/delete, network, service, deployment,
  production DB/state, secret or runtime dependency effect occurred.
- No schema/DDL, accepted delivery implementation, architecture/ADR, roadmap
  or current-work file was changed.
