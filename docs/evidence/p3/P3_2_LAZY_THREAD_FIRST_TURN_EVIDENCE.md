# P3.2 lazy thread/start and first-turn implementation evidence

Date: 2026-09-06

This is factual executor evidence for Issue #21. It is not architect acceptance.

## Base and authorities

- Base SHA: `6a1182a2db4486124875b1de2a6f11cbd12243e1`
- Branch: `impl-p3-2-lazy-thread-first-turn-2026-09-06`
- Issue: `#21`
- Binding design: ADR-0028
- Existing-dialogue/replay authorities: ADR-0026 and ADR-0027
- Current-work tombstone guard: `docs/CURRENT_WORK.md`
- Accepted P3.1: `9e0a86b311bb63d6a36a4641cb588321987e1550`
- Accepted P2.C1: `4b6d226ce647fbf38a6ada7b82947be7ad3e30c2`
- Frozen DDL SHA-256: `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`

## Production scope

Changed production files are limited to `src/codex_control/application/`:

- `dialogue_turn.py` adds the public P3.2 service, thread-start port, and recovery result/status.
- `_turn_common.py` owns the single shared admitted-turn runner.
- `existing_dialogue_turn.py` delegates its admitted runner to that private helper.
- `__init__.py` exports the four P3.2 public names.

No storage, adapter, domain, configuration, profile, state, session, schema, migration, dependency, or service file changed.

## Contract and orchestration proof

`ThreadLifecyclePort` exposes only `start`. `CreationRecoveryStatus` has exactly `NO_ACTION` and `MARKED_UNKNOWN`; `CreationRecoveryResult` is frozen with exactly `status` and `dialogue`. `DialogueTurnService` exposes exactly `execute` and `recover_preexisting_creation` as class-defined public callables.

`DialogueTurnService.execute` first delegates to the accepted existing-dialogue service with the same dependencies. Existing canonical IDLE and duplicate paths therefore retain P3.1 behavior, with zero P3.2 thread starts. Lazy creation begins only after the exact `BLOCKED / NO_DIALOGUE` result.

No-dialogue preflight validates settings, configured profile, model, authenticated catalog/profile, visible model, concrete reasoning effort, and exact trusted workdir. Blocked paths perform no local admission or P1 effect.

The generated dialogue ID is checked against `DeletionRepository.get_tombstone()` before create intent. A retained or corrupt collision is an application invariant with no retry or effect.

After bounded dialogue/job/input IDs, clock validation, expiry calculation, and the tombstone guard, one cancellation-owned task performs:

1. `CREATING` dialogue intent with null thread;
2. atomic JOB ingress, `RECEIVED` job, and exact INPUT with null job thread;
3. exactly one P1.5 thread start from the immutable admitted model/effort and trusted workdir;
4. exact local thread confirmation to `IDLE`;
5. the shared admitted-turn runner, which binds the first job thread during `claim_turn` and executes the accepted P3.1 turn sequence.

Thread-start invocation is therefore after durable first-prompt admission. Confirmed binding checks profile, model, effort, and thread identity. Rejected/local deterministic errors become `ERROR`; unknown, malformed, mismatched, unexpected, and cancellation-ambiguous results become `CREATE_UNKNOWN`; no thread retry exists.

If local confirmation does not return normally, the service rereads the live dialogue once. An exact committed IDLE binding continues the same first job; exact remaining CREATING is marked `CREATE_UNKNOWN`; existing CREATE_UNKNOWN is returned as UNKNOWN; incompatible state is finite fail-closed application error.

Create-intent ALREADY_EXISTS and first-ingress DUPLICATE races have no thread effect and are re-evaluated once through accepted existing-dialogue authority. Admission ID collisions are invariant failures; after an owned create, `APPLICATION_ADMISSION_FAILED` terminalization is attempted without ID retry.

## Recovery

`recover_preexisting_creation()` uses only the dialogue repository. It does not call model catalog, workdir, thread lifecycle, turn lifecycle, or ID factory. No live or non-CREATING dialogue returns `NO_ACTION` without mutation. A pre-existing CREATING dialogue is marked `CREATE_UNKNOWN / CODEX_AMBIGUOUS`. Existing RECEIVED JOB/ingress/INPUT evidence is preserved. Repeated recovery is idempotent, and confirmed IDLE plus RECEIVED is a no-action state with no thread recreation.

## Tests and regressions

Focused P3.2 tests:

- unit: `2`
- integration: `12`
- combined: `14`

Accepted P3.1 regression:

- unit: `11`
- integration: `26`

P2.C1 regression:

- retention-compatible replay integration: `5`
- acceptance: `1`

P2.6b regression:

- contract: `5`
- restart: `12`
- replay: `8`
- abrupt: `3`

Prior focused counts remained as recorded by the acceptance authority:

- P2.6a: `4 / 28`
- P2.5: `4 / 18`
- P2.4b: `6 / 25`
- P2.4a: `8 / 31`
- P2.3: `7 / 28`
- P2.2: `6 / 20`
- P2.1: `8 / 31`
- P1.10 T0/T1/T2: `6 / 1 / 4`

The accepted pre-P3.2 full count was `543`. With `2 + 12` new focused tests, expected and observed discovery count is `557`.

The focused tests cover existing-dialogue delegation, no-dialogue preflight, tombstone collision, durable ordering, first-turn handoff, rejection/unknown/local/malformed thread outcomes, confirm-local reconciliation, same/different-update no-queue races, admission collision terminalization, cancellation ownership, and startup recovery/idempotency. Tests use temporary SQLite and fake catalog, thread, turn, and workdir ports.

## Security and scope checks

Generic service/result/error representations do not render prompt/output content, CODEX_HOME, database paths, or raw adapter errors. The changed tests use only named non-secret sentinels for redaction assertions. No real Codex, Telegram, network, production database, production state root, or service was touched.

Observed warning: the known pre-existing P1.6 pending-task warning appeared during full discovery. It was not introduced by P3.2.

P3.3 and all later slices were not started.
