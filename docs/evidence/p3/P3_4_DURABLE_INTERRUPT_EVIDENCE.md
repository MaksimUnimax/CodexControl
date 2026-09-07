# P3.4 durable interrupt implementation evidence

Date: 2026-09-06

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Issue: `#26 — P3.4`
- Architect base: `d8f8de0f349217c314c6eacd743132d51bcef279`
- Accepted P3.3: `66a37d8b8065ecd31e17351e8062f9ebf1ee8828`
- Accepted P1.8: `6d8a07b5b95ef377cf60762f4475128bdf810b22`
- Binding ADR: `docs/adr/0030-durable-turn-interrupt-orchestration.md`
- Frozen schema-v1 DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

This is implementation evidence only; it does not claim architect acceptance.

## Implemented boundary

`DialogueInterruptService` exposes the two requested operations:

- `interrupt(DialogueInterruptRequest)`;
- `recover_preexisting_interrupt()`.

The request is frozen and contains only dialogue/job IDs and expected dialogue/job
versions. Status, reason, recovery status, finite error categories, result fields,
and frozen-record semantics are covered by the focused unit tests.

`ActiveTurnRegistry` is process-local and keyed by durable job ID. It retains the
exact P1 `TurnBinding` object and an opaque ownership lease. Lookup returns the
same object identity. Publication rejects incompatible duplicates; retirement is
token/identity-safe, so stale cleanup cannot retire a replacement. The registry
has no background task, exposes no binding IDs in repr, and is empty in a new
process.

The shared admitted-turn runner publishes the exact confirmed binding after P1
turn/start validation and before durable `CODEX_RUNNING` is established. The
lease remains owned through wait and terminalization and is retired in the
runner's final ownership path. `DialogueTurnService` passes the same registry to
its internal existing-dialogue service and runner. No registry is global; absent
injection creates private standalone behavior.

## Durable orchestration

The additive `InterruptCoordinationRepository` uses only `SqliteStorage.write`
and schema-v1. It provides atomic interrupt claim, rejected-interrupt restore,
interrupt terminalization/natural-terminal reconciliation, and startup recovery.
It does not modify `TurnJobRepository.finish_codex` or the schema.

The application validates the request before storage work, performs the required
dialogue/job/version/relationship checks, requires `CODEX_RUNNING` with durable
thread and Codex turn identities, and requires the exact registry binding. The
claim commits `TURN_RUNNING -> INTERRUPTING` with dialogue version +1 while the
job state/version and all identities remain unchanged. P1.8 is called only after
that durable claim.

Terminal versions recognize only the exact accepted shapes: claim at V+1/K,
rejected restore at V+2/K, interrupt terminalization at V+2/K+1, and natural
terminalization after restore at V+3/K+1. Arbitrary drift fails closed.

P1 `CONFIRMED` and `RECONCILED` definitive terminal results are persisted with
their application status. `REJECTED` restores the exact claimed dialogue to
`TURN_RUNNING` without retry; if a definitive natural terminal already won,
the application reconstructs `RECONCILED`. `UNKNOWN`, `BUSY`, `NOT_ACTIVE`,
malformed results, mismatched results, and uncertain exceptions perform one exact
collector reconciliation attempt and otherwise persist `UNKNOWN`/
`TURN_UNKNOWN` with `CODEX_AMBIGUOUS`. No interrupt redispatch occurs.

Definitive interrupted completion maps to `CODEX_COMPLETED`/`IDLE`; definitive
interrupted failure maps to `FAILED` with `CODEX_TURN_FAILED`/`IDLE`; unprovable
terminal state maps to `UNKNOWN`/`TURN_UNKNOWN` with `CODEX_AMBIGUOUS`.

The normal runner calls accepted `finish_codex` first. Only the exact P3.4
interrupt-induced conflict shapes use the additive natural-terminal reconciliation
path. Terminal writes and output materialization are atomic and idempotent, so
the race tests prove no duplicate terminal write or OUTPUT payload. The existing
ordered completed-agent-message projection, separator, byte ceilings, and
completed/uncertain retention durations are reused. Empty projections generate
no output ID.

## Recovery and safety boundaries

Startup recovery makes no P1 calls. It marks one canonical owning pre-existing
`INTERRUPTING` job/dialogue pair as `UNKNOWN`/`TURN_UNKNOWN` with
`CODEX_AMBIGUOUS`, preserving ingress, input, thread, turn, and job evidence.
Repeated recovery is `NO_ACTION`. Missing, multiple, mismatched, or corrupt
owners fail closed as invariant errors without masking corruption.

Approval storage was not redesigned. Existing callback claims still require
`CODEX_RUNNING` and `TURN_RUNNING`, so old approval callbacks cannot become valid
after interrupt claim or terminalization. Existing settings selection continues
to block mutations while dialogue state is `INTERRUPTING`.

Generic errors and result reprs are payload-free/redacted. Tests use temporary
SQLite and fake lifecycle ports only; no Telegram, network, real Codex, production
state root, production database, or production `CODEX_HOME` was opened.

## Tests

Focused P3.4 counts:

- `P3_4_UNIT_TESTS=6`
- `P3_4_INTEGRATION_TESTS=18`

Historical focused counts retained:

- P3.1: 11 unit / 26 integration
- P3.2: 2 unit / 21 integration
- P3.3: 5 unit / 25 integration
- P1.8: 28
- P1.10: 6 / 1 / 4
- P2.C1: 5 integration / 1 acceptance
- P2.6b: 5 contract / 12 restart / 8 replay / 3 abrupt

The accepted pre-P3.4 full suite was 596 tests. Observed full discovery was:

`EXPECTED_FULL_TESTS=596+6+18=620`

`OBSERVED_FULL_TESTS=620`

Compileall, import, and `git diff --check` passed. The P1.6 focused run retained
the pre-existing pending-collector warning recorded by accepted P1.8 evidence;
P3.4 introduced no adapter changes.

## Scope and effects

Changed production paths are limited to the requested application registry,
interrupt service, narrow common runner/output helper, optional registry
injection, additive storage coordination module, and exports. Focused test paths
are the P3.4 unit/integration files. No adapter, domain, schema, SQLite kernel,
core repository, turn-job repository, approval repository, ADR, CURRENT_WORK,
ROADMAP, main branch, Telegram UI, hard-delete flow, generic restart scanner, or
P3.5 work was changed.

Effect assertions:

`REAL_INTERRUPT_CALL=NO`

`REAL_TURN_START_CALL=NO`

`REAL_THREAD_START_CALL=NO`

`REAL_THREAD_DELETE_CALL=NO`

`REAL_MODEL_LIST_CALL=NO`

`REAL_TELEGRAM_CALL=NO`

`REAL_NETWORK_EFFECT=NO`

`PRODUCTION_DB_OPENED=NO`

`PRODUCTION_STATE_ROOT_TOUCHED=NO`

`PRODUCTION_CODEX_HOME_READ=NO`

`PRODUCTION_SERVICES_CHANGED=NO`

## Architect first repair

This section is factual first-repair executor evidence only. P3.4 is not
architect-accepted, Issue #26 remains open, and no P3.5 work was started.

Rejected candidate: `2f63830c2e63e9a3564e1fed18eb7d55e36f8cd8`.

Architect review comments: `5559617303`, `5559630444`.

Repair closure:

- Terminal proof now requires `TurnTerminalResult.binding is binding` for
  direct CONFIRMED/RECONCILED results, rejected carried terminals, collector
  results, and malformed-result fallback collection. Equal-looking cloned
  bindings are rejected; both direct and collector clone tests finish as
  `UNKNOWN` with one interrupt call, one collector call, and no redispatch.
- `TURN_INTERRUPT_NOT_ACTIVE` and `TURN_INTERRUPT_BUSY` use exactly one exact
  collector reconciliation attempt and never retry. `TURN_INTERRUPT_NOT_ACTIVE`
  with an exact completed collector is `RECONCILED`; non-definitive collection
  remains `UNKNOWN`.
- Local `TURN_REQUEST_INVALID`, `TURN_PRECONDITION_CHANGED`, and other
  non-authorized local `TurnLifecycleError` categories fail closed as
  application `INVARIANT`, with no collector call, no output, and durable
  `INTERRUPTING`/`CODEX_RUNNING` state preserved.
- Application output-clock failures retain `STORAGE` classification and redact
  the raw clock exception; invalid output ID generation remains `INVARIANT`.
- Idempotent terminal reconstruction now requires the exact canonical error
  semantics for completed, failed interrupt, failed natural-terminal, and
  unknown shapes. Wrong and mismatched sanitized error classes are rejected as
  `INVARIANT_VIOLATION` without a clock call or corrupt-row normalization.
- Still-running terminalization rejects either job or dialogue version at
  `MAX_SQLITE_INT` as `INVARIANT_VIOLATION` before output collision work,
  clock, increment, or mutation. Exact canonical already-terminal rows remain
  reconstructable at maximum version without a clock or duplicate output.
- The real admitted-turn runner proof publishes the exact P1 start binding into
  the shared registry while `CODEX_RUNNING` and retires it after terminal
  ownership. The real runner/interrupt race proves `finish_codex` is invoked
  first, then the narrow P3.4 reconciliation fallback, with one terminal
  mutation and one OUTPUT payload.
- A real interrupt claim leaves settings profile, model, and reasoning
  mutations blocked under the accepted P3.3 locks. An approval and exact
  callback created while running becomes `STALE` after the interrupt claim,
  is consumed once, leaves approval `PENDING`, and replays as
  `ALREADY_CONSUMED`.
- Completed output preserves the accepted ordered separator projection and
  one-hour retention. Failed and unknown partial output is preserved with
  24-hour uncertain retention. Empty output still creates no output ID.

Final repair focused counts are `6` unit and `31` integration tests. Prior
regressions passed at the requested authority counts: P3.1 `11/26`, P3.2
`2/21`, P3.3 `5/25`; P2.C1 `5/1`; P2.6b `5/12/8/3`; P2.6a `4/28`; P2.5
`4/18`; P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`; P2.2 `6/20`; P2.1
`8/31`; P1.8 `28`; and P1.10 `6/1/4`. Full discovery arithmetic is
`596 + 6 + 31 = 633`, with `633` observed passing tests.

Compile/import, DDL hash, diff-boundary, and security/effect scans were run
for the repair. The known P1.6 pending-task warning was observed during full
discovery and remains pre-existing; `P1_6_WARNING_INTRODUCED_BY_P3_4_REPAIR=NO`.
All tests used temporary SQLite and fake lifecycle/catalog/workdir ports. No
real Codex, Telegram, network business effect, production database/state root,
service mutation, credentials, or raw content diagnostics were used.
