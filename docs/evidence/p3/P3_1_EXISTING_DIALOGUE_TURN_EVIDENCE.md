# P3.1 existing-dialogue turn application evidence

This is factual executor evidence for Issue #19. It does not claim architect
acceptance.

## Scope and base

- Repository: `MaksimUnimax/CodexControl`
- Issue: `#19 — P3.1 — existing-dialogue turn application service`
- Branch: `impl-p3-1-existing-dialogue-turn-service-2026-09-06`
- Base SHA: `2e4504d98cf39ca42b34090f069f640f3e0bc3ad`
- Final accepted P2 HEAD: `9db97f0dda109b4d0c0ecfa5f167733905df2766`
- Binding ADR: `docs/adr/0026-existing-dialogue-turn-application-service.md`

## Production implementation

New production files only:

- `src/codex_control/application/__init__.py`
- `src/codex_control/application/existing_dialogue_turn.py`

The package exposes the three fixed retention constants, frozen request/result
records, exact StrEnums, finite redacted application errors, the three narrow
ports, and `ExistingDialogueTurnService.execute`. No accepted P1/P2 production
file, schema, dependency, or configuration file was changed.

The service validates request shapes before any storage operation. Its duplicate
lookup is the first operation after validation. Existing non-JOB ingress returns
`DUPLICATE_NON_JOB`; an existing canonical JOB returns the durable job after the
canonical INPUT proof; a missing referenced job returns
`DUPLICATE_ORPHAN_JOB` only when no live dialogue remains, and is an invariant
when a live dialogue remains. Replay performs no catalog, working-directory,
clock, ID-factory, or turn effect.

For a new update, the service selects only an existing canonical IDLE dialogue,
requires the explicit configured profile and matching durable settings, resolves
the authenticated catalog model and concrete default effort, and resolves the
trusted working directory before admission. Missing dialogue, busy/non-IDLE
state, settings/profile/model/catalog/working-directory failures return the
finite blocked/busy results without ingress, job, INPUT, or P1 effect.

The durable effect order is:

`claim_ingress -> reread dialogue -> claim_turn -> mark_codex_starting -> start_turn -> mark_codex_running -> wait_turn -> finish_codex`

The admitted job stores the logical settings model and concrete reasoning effort.
The confirmed P1 binding is checked against the immutable job/dialogue binding,
the same binding is passed to `wait_turn`, and no start retry exists. Rejected
start becomes FAILED/CODEX_TURN_FAILED; unknown, ambiguous, binding mismatch,
and unexpected wait outcomes become UNKNOWN/CODEX_AMBIGUOUS. Local pre-effect
turn lifecycle errors become FAILED/CODEX_PROCESS.

Terminal agent messages retain P1 tuple order and are encoded with double-newline
separators. One all-or-none OUTPUT bundle is passed to `finish_codex`; completed
output targets one hour and failed/unknown partial output targets 24 hours.
Empty output creates no OUTPUT row. The P1 bound proves

`2,000,000 * 4 + 255 * 2 = 8,000,510 < 8,388,608`.

After CREATED admission, one owned orchestration task is shielded from repeated
public cancellation until the durable terminal boundary. There is no delayed
second prompt queue.

## Verification

Focused P3.1 commands:

- unit: `9 passed`
- integration: `9 passed`
- combined P3.1 focused count: `18 passed`

The focused coverage includes public contract/static validation, no-dialogue
blocking, duplicate-first no-effect replay, authenticated default-effort
snapshotting, catalog failure, start rejected/unknown/binding mismatch,
terminal partial output, different-update no-queue, and post-admission repeated
cancellation ownership.

Accepted P2.6b regressions:

- contract snapshot: `5 passed`
- restart matrix: `12 passed`
- replay matrix: `8 passed`
- abrupt process probes: `3 passed`

Accepted P2 focused counts all passed: P2.6a `4/28`, P2.5 `4/18`, P2.4b
`6/25`, P2.4a `8/31`, P2.3 `7/28`, P2.2 `6/20`, and P2.1 `8/31`.
P1.10 T0/T1/T2 passed `6/1/4`; all existing focused P1 unit suites passed
`233` tests.

Full discovery passed `518` tests with the exact arithmetic
`500 + 9 + 9 = 518`.

`compileall` and the explicit application import proof passed. `git diff --check`
passed. The frozen schema DDL SHA remained
`b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.

Security inspection found no credentials, private keys, production database
paths, CODEX_HOME leakage, prompt/output logging, raw adapter/repository error
bodies, tracebacks, stdout/stderr dumps, or environment dumps in new files.
Request text and payload content remain excluded from generic repr; service and
application errors expose only safe diagnostics. Tests used temporary SQLite,
fake catalog/turn/resolver ports, and no real Codex, Telegram, network,
production database, production state root, or service control.

The known P1.6 pending-task warning was observed in the full/unchanged P1.6
coverage. No new P3.1-specific warning was observed in the focused P3.1 runs;
the warning was not introduced by P3.1.

P3.2 was not started. No lazy thread creation, settings mutation, interrupt,
hard-delete orchestration, restart scanner, delivery, Telegram, or P4+ work was
implemented.
