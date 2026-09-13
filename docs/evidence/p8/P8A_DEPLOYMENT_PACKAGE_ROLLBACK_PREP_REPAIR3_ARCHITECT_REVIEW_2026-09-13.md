# P8.A deployment package + rollback preparation Repair-3 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / THREE OF FOUR REPAIR-3 BLOCKERS ACCEPTED / ONE CRASH-JOURNAL BOUNDARY REMAINS / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Binding candidate

- branch: `impl-p8a-deployment-package-rollback-repair3-2026-09-13`;
- candidate HEAD: `3bb4cff0436103e75567a4ebdccee51c537a2b63`;
- candidate tree: `fc3818c5805ca21e785c1f2c0d3d87e381bed6d2`;
- exact Repair-3 base: `5ef7d19131335863f9c104f2ea363d6ed014cf82`;
- candidate is two linear commits ahead of the exact base, zero behind, merge-base exact base;
- only five P8.A-authorized files changed;
- `origin/main` remained `674ea22b488cb8d4064aff504aebb62cd0516e7d` / tree `86329f2ce8b40e0ae81f1197ea9910e8b1bd36b2` during execution.

## Accepted Repair-3 work

Independent source review accepts for reuse:

1. **First-install state initialization.** Canonical existing `state_root == controller_db_path.parent` is now supported. Initialization validates config/secrets/filesystem/runtime authority, requires the DB leaf absent, creates only safe subordinate directories, opens/closes schema-v4 storage explicitly, reads back `PRAGMA user_version == 4`, and blocks the second initialization. Ordinary serve still requires an existing DB.

2. **Private-stage executable validation before final publication.** Production `install_upgrade()` now prepares the exact Git release privately, validates the release-local executable while it is still under `.stage-*`, and only then publishes the final `releases/<sha>` target. A staged validation failure can leave an already-valid identical target untouched but does not publish a new invalid final release or switch current.

3. **Production CLI test bypass removal.** `deploy/codex_control_deploy.py` no longer defines or consumes `--test-only-authority`. Offline test-only seams remain Python-level only.

4. All major Repair-2 authorities remain accepted: installed Codex preflight, serve ordering, Telegram long-poll margin, explicit production-root authority, exact Git commit/tree export, executable release, actual DB schema gates, health-state model, truthful installed verification and zero-production-effect boundaries.

## Remaining blocking defect — pending switch journal is not crash-atomic at the current-switch boundary

Repair-3 adds `.previous.next` with `PREPARED`, `CURRENT_SWITCHED` and `FINALIZED` states. The architectural direction is correct, but the exact persistence/recovery boundary is still unsafe.

### A. Journal state rewrite truncates the only pending authority in place

`_write_pending()` opens the canonical `.previous.next` path with `O_TRUNC` and rewrites it directly. After `current` has already switched from A to B, the transition from `PREPARED` to `CURRENT_SWITCHED` therefore destroys the prior valid pending record before the new record is durably committed.

A crash, ENOSPC, short-write/IO error, or process death during that rewrite can leave `.previous.next` empty or malformed. On a first A→B upgrade there may be no durable `previous` file yet, so this can destroy the only retained authority naming A after B is already current.

The journal state update must use a private sibling + fsync + atomic `os.replace` + directory fsync, not in-place truncation of the authoritative record.

### B. Valid `PREPARED + current == new_target` is currently rejected instead of recovered

Before switching `current`, Repair-3 durably writes:

- `old_current_sha=A`;
- `new_target_sha=B`;
- `state=PREPARED`.

After `current` is atomically switched to B, the code attempts to rewrite the journal to `CURRENT_SWITCHED`. If that rewrite raises before it succeeds, the retained `PREPARED` record still contains exactly A and B and is sufficient to infer that the current switch did occur.

However `_recover_pending_previous()` currently treats `PREPARED` as valid only when `current` still equals the old release. `PREPARED + current=B` is classified as `pending_current_disagreement`.

This means the comment claiming that the retained PREPARED record “still identifies the immediate old current and forces fail-closed recovery” is not yet matched by executable recovery semantics.

Required recovery semantics:

- `PREPARED`, current == old (or old=None and current absent): switch did not occur; remove/abort pending safely;
- `PREPARED`, current == new: switch occurred but state transition was interrupted; validate old/new releases and deterministically promote/finalize the immediate old current as rollback authority;
- any other current value: fail closed as disagreement.

### C. Current focused tests do not cover this boundary

The Repair-3 tests cover:

- failure of the `current` replacement itself; and
- failure of final durable `previous` replacement after `CURRENT_SWITCHED` is already persisted.

They do not inject failure/crash while rewriting the pending journal immediately after successful current replacement, nor do they prove recovery from `PREPARED + current=new` on the first upgrade where no `previous` file exists.

## Architect verdict

`P8A_REPAIR3_FIRST_INSTALL_STATE=ACCEPTED_FOR_REUSE`

`P8A_REPAIR3_STAGED_VALIDATE_BEFORE_PUBLICATION=ACCEPTED_FOR_REUSE`

`P8A_REPAIR3_PRODUCTION_CLI_NO_TEST_BYPASS=ACCEPTED_FOR_REUSE`

`P8A_REPAIR3_PENDING_JOURNAL_CRASH_ATOMICITY=REWORK_REQUIRED`

`P8A_REPAIR3_PREPARED_AFTER_SWITCH_RECOVERY=REWORK_REQUIRED`

`P8A_REPAIR3_ARCHITECT_ACCEPTED=NO`

`P8A_PREP_READY=NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

P8.A Repair-4 must start from exact candidate `3bb4cff0436103e75567a4ebdccee51c537a2b63`, preserve all accepted Repair-2/Repair-3 work, and change only the pending-journal atomic persistence and interrupted-state recovery boundary plus focused regression/evidence.
