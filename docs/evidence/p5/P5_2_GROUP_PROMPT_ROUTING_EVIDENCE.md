# P5.2 group prompt routing implementation evidence

Status: implementation evidence only; no architect acceptance is claimed.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `d325260034650d11743ef8ed96a9b8c70d699349`
- Branch: `impl-p5-2-group-prompt-routing-2026-09-08`
- Issue: `#33`
- Binding authority: ADR-0037
- Accepted P2.C2: `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`
- Accepted P5.1: `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`
- Accepted P3.2: `c484c56db007569170363b3d08c24766148c3e30`

## Implementation

Production paths are limited to:

- `src/codex_control/application/fleet_group_routing.py`
- `src/codex_control/application/__init__.py`

The facade exposes exact async `FleetControlPort` and `DialogueTurnPort` seams,
the frozen group-routing statuses/reasons/error categories/result, and
`FleetGroupRoutingService.handle(update)`. It accepts only exact normalized
`GroupInboundUpdate` values and validates exact P5.1, P2.C2 and P3 result
shapes. Nested control/turn results are repr-redacted and errors contain only
finite categories.

## Routing and admission facts

- One process-local `asyncio.Lock` covers P5.1 handling, TEXT snapshot and
  duplicate/mode/marker decisions only.
- The lock is released before the owned P3 task is awaited; controls remain
  responsive while P3 runs.
- One private non-content marker stores only the exact update ID and an opaque
  owner token. It is process-local, non-durable, not restored and is not JOB,
  dialogue or external-effect authority.
- Durable ingress is read only after successful P5.1 TEXT reauthorization and
  current-mode projection.
- Existing ingress returns DUPLICATE with its exact original disposition,
  without reclassification or P3 invocation.
- Same-update delivery while its marker is owned returns DUPLICATE with
  `IN_FLIGHT_DUPLICATE`, no disposition claim and no second P3 invocation.
- A prompt at or below the P5.1 control epoch claims exactly
  `IGNORED_REJECTED` and returns `REJECTED/STALE_PROMPT`.
- A newer prompt in SLEEP claims exactly `IGNORED_SLEEP`, stores no text and
  never calls P3.
- A different newer prompt during local marker ownership claims exactly
  `IGNORED_REJECTED` and returns local BUSY with zero P3 calls.
- Eligible ACTIVE text is constructed as the exact P3 request and delegated
  once through `DialogueTurnPort` outside the routing lock.
- Accepted P3 BUSY/BLOCKED results are validated and terminalized with one
  `IGNORED_REJECTED` claim. Durable duplicate races preserve the existing
  disposition.
- P3 COMPLETED, FAILED and UNKNOWN results retain verified JOB authority and
  are returned as PROMPT; no rejected claim is made after admitted work.
- P3 exceptions map only to finite STORAGE/CODEX/INVARIANT errors as accepted;
  P5.2 does not blindly create a rejection after an exception.
- Caller cancellation is shielded from the owned P3 task. The marker is
  cleared only by the exact owner in `finally`, after any required durable
  rejection claim or JOB verification.

## Focused proofs

The focused modules are:

- Unit: `tests/unit/test_fleet_group_routing.py` — `8` tests.
- Integration: `tests/integration/test_fleet_group_routing.py` — `19` tests.

They cover public contract ordering/redaction, exact input and result
validation, P5.1 control/status/unauthorized delegation, durable duplicate
precheck, stale equal/older epochs, SLEEP replay, local pre-JOB BUSY,
same-update in-flight duplicate, accepted P3 BUSY/BLOCKED replay protection,
terminal COMPLETED/FAILED/UNKNOWN JOB preservation, running-control
responsiveness, cancellation ownership, restart marker absence, invalid text,
malformed P3 results, accepted real P3 existing-dialogue composition, accepted
real P3 lazy-first-dialogue composition, duplicate race preservation and
finite P3 error mapping.

The tests use temporary SQLite, normalized synthetic updates, fake lifecycle
ports, deterministic clocks and local accepted application services only.
There is no Telegram delivery/network effect, Codex process, production
database/state root, thread/start, turn/start, interrupt, delete or approval
response effect.

## Regression and invariant checks

- Accepted pre-P5.2 full baseline: `796`.
- P5.2 arithmetic: `796 + 8 + 19 = 823`.
- Observed full discovery: `823` tests, `0` failures, `0` errors, final
  unittest status `OK`.
- The known historical P1.6 pending-task warning was observed during full
  discovery and was not introduced by P5.2.
- P2.C2 `5/13/1`; P5.1 `7/8`; P4.3 `7/26/1`; P4.2 `5/29`; P4.1 `8/15`;
  P3.5 `12/25/1`; P3.4 `6/31`; P3.3 `5/25`; P3.2 `2/21`; P3.1 `11/26`;
  P2.C1 `5/1`; P2.6b `5/12/8/3`; P2.6a `4/28`; P2.5 `4/18`;
  P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`; P2.2 `6/20`; P2.1 `8/31`;
  P1.9 `15`; P1.8 `28`; P1.10 `6/1/4`.

- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS.
- Public import smoke: PASS (`P5_2_IMPORT_PASS`).
- `git diff --check`: PASS.
- Schema version remains `2`.
- Historical v1 DDL SHA-256 remains
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Schema-v2 migration SHA-256 remains
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- No schema/DDL, P5.1, P3 or P2 production file was changed.
- Changed-file secret/effect review found no credentials, raw Telegram,
  production prompt/output, private runtime path, raw exception, production ID or
  environment material in production/evidence surfaces.

P5.3, P6 and later slices were not started. Issue #33 remains open and this
evidence does not claim architect acceptance.

## Architect first repair

This section is implementation evidence for the first repair pass. It does
not claim architect acceptance.

- Rejected candidate: `428fb93056358b898d2e7cc95d94ae61de8617de`.
- Architect review: `5578312547`.
- Repair parent remains the rejected candidate above; the original architect
  base remains `d325260034650d11743ef8ed96a9b8c70d699349`.
- `PROMPT` now requires an exact `FleetModeSnapshot` whose effective mode is
  `ACTIVE`. Direct public construction with an absent snapshot or a `SLEEP`
  snapshot fails `INVARIANT`; a canonical ACTIVE snapshot passes.
- P3 `DUPLICATE` validation now accepts only the exact non-JOB reasons with no
  job, or an exact `TurnJobRecord` with no reason. Impossible job/reason
  combinations fail before any durable ingress reread.
- Canonical non-JOB and durable JOB duplicate races preserve their durable
  disposition with no new P3 effect. A malformed duplicate cannot be masked
  by the durable reread.
- The malformed-P3 matrix independently covers invalid BUSY reason/job,
  invalid BLOCKED reason/job/output, all required duplicate relations,
  terminal results missing or mismatching durable JOB authority, and a
  duck-typed result. Every malformed result fails `INVARIANT` without a blind
  `IGNORED_REJECTED` claim.
- Original P5.2 routing, no-queue, control-responsiveness, cancellation and
  restart-marker proofs remain green.
- Final focused counts: `11` unit and `34` integration tests.
- Full-suite arithmetic: `796 + 11 + 34 = 841`.
- Full discovery: `841` tests, `0` failures, `0` errors, unittest status `OK`.
- The known P1.6 pending-task warning was observed during full discovery and
  was not introduced by this repair.
- Schema version remains `2`; the historical v1 DDL hash and schema-v2
  migration hash remain unchanged:
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c` and
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- Compile/import, diff, and security/effect checks pass. No real Telegram,
  network, Codex, production database/state-root or service effect occurred.
- No architecture, schema, P5.1, P3 or P2 production source was changed;
  P5.3 and P6 were not started; Issue #33 remains open.
