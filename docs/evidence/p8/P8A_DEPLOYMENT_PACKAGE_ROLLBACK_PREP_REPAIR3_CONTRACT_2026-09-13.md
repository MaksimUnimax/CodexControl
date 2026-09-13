# P8.A deployment package + rollback preparation — Repair-3 contract — 2026-09-13

Status: **FROZEN / ZERO PRODUCTION EFFECT / NARROW FINAL TRANSACTION REPAIR / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Exact Repair-3 base

Repair-3 must start from exactly:

- HEAD `5ef7d19131335863f9c104f2ea363d6ed014cf82`;
- tree `dd66eb9e353049cd8749a2f7d40789fc10cbda92`.

Use only branch:

`impl-p8a-deployment-package-rollback-repair3-2026-09-13`

No merge, rebase, squash or force push.

## Preserve accepted Repair-2 authorities

Do not redesign the accepted Repair-2 work: installed Codex probe, preflight ordering for existing DBs, long-poll margin, exact Git-object export/tree manifest, explicit production-root authority, private stage/final atomic publication, executable release, production/rehearsal API separation, actual DB-schema gates, health-state model, truthful installed verification, P0-P7 composition and zero-production-effect boundary.

## 1. Fix explicit first-install state initialization

The canonical state root may already exist and normally is the controller DB parent. `initialize_controller_state` must not attempt to recreate an existing validated parent with `exist_ok=False`.

Required sequence:

1. parse config/secrets;
2. validate filesystem/profile/runtime authority and installed Codex authority without requiring DB existence;
3. require configured DB path absent (`lexists` false) and non-symlink path authority;
4. require its parent is the expected safe configured state/controller root or safely create only missing subordinate directories under that authority;
5. create schema-v4 DB using accepted `SqliteStorage` authority;
6. close it;
7. read back `PRAGMA user_version == 4`;
8. second initialization attempt fails deterministically as already initialized.

Ordinary `serve` must continue to reject a missing DB and must never initialize it implicitly.

Add focused canonical-layout tests with `controller_db_path = state_root/controller.sqlite3`.

## 2. Staged executable validation must precede final publication

Production transaction authority must not publish a new final `releases/<sha>` before the staged executable has passed `codex-control validate` against target config/secrets/existing DB/installed runtime authority.

Refactor as necessary so production upgrade can:

- export exact Git object into private stage;
- build release executable;
- create preliminary/final manifest authority;
- validate release artifacts in the private stage;
- run the private-stage executable validation;
- only after all above succeed atomically publish final `releases/<sha>`;
- then switch `current`.

A generic package-only staging primitive may remain, but the production transaction must use the stronger prepare+validate+publish path.

Required negative: inject staged executable validation failure and prove final `releases/<sha>` absent and current unchanged. Also prove an already-existing valid identical release remains unchanged.

## 3. Make previous/current switch crash-recoverable

The old current release must remain recoverable across all switch boundaries.

Use a bounded pending transaction authority such as `.previous.next` / deployment journal, but do not discard it after current has changed until durable `previous` is committed.

Required semantics:

- before current switch, persist exact old-current pending authority;
- if current switch fails, remove/abort pending and leave current + durable previous unchanged;
- if current switch succeeds but previous finalization fails/crashes, retain a recoverable pending record identifying the exact old current;
- rollback/verification/recovery must reject ambiguity or deterministically promote/use the pending record only when it is consistent with current and release manifests;
- after successful previous finalization, remove pending authority;
- no stale previous record may silently select a release older than the immediate prior current after a partial switch.

Add tests for failure at both replacement boundaries and a simulated restart/recovery after current-success/previous-failure.

## 4. Remove production CLI test-only bypass

Remove `--test-only-authority` from production deployment CLI (`deploy/codex_control_deploy.py`) upgrade/rollback/verify/stage surfaces.

Production CLI must always use production owner/mode/runtime authority. Test-only injection remains available only via explicit Python APIs/factories used by offline tests.

Do not expose an environment variable that enables test authority.

## 5. Focused tests

Add/extend tests for at least:

- `test_initialize_controller_state_canonical_existing_state_root`;
- `test_initialize_controller_state_second_attempt_blocked`;
- `test_serve_missing_db_does_not_initialize`;
- `test_staged_validate_failure_never_publishes_final_release`;
- `test_staged_validate_failure_keeps_current_unchanged`;
- `test_current_failure_keeps_previous_truthful`;
- `test_previous_finalize_failure_retains_recoverable_old_current`;
- `test_restart_recovery_resolves_pending_previous_authority`;
- `test_production_deploy_cli_has_no_test_only_authority_flag`.

Equivalent names are acceptable only with one-to-one evidence mapping.

## 6. Zero-effect boundary

No real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control`, `/etc/systemd/system` writes; no real systemd commands; no live Telegram; no Codex app-server/RPC; no P7 mutation; no P8.B/P9.

`P8A_PRODUCTION_EFFECTS=0` mandatory.

## 7. Validation

Run focused Repair-3 tests, then complete safe unit/integration/acceptance and P0-P7 non-real regressions with all real gates unset. Run compileall, `git diff --check`, secret/leakage scan and exact changed-path scope.

Re-run a full temporary-root exact-Git A -> B -> explicit failed health -> schema-compatible rollback rehearsal, including first-install initialization, staged validation-before-publication and pending-previous recovery boundaries. Config/secrets/state bytes must remain unchanged except the explicitly initialized temporary state on the first-install fixture.

## 8. Evidence

Update:

`docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md`

Record exact Repair-3 base/head/tree, changed paths, test mapping/results, new digests and zero-effect accounting.

End exactly:

`P8A_REPAIR3_FIRST_INSTALL_STATE=PASS|FAIL`

`P8A_REPAIR3_STAGED_VALIDATE_BEFORE_PUBLICATION=PASS|FAIL`

`P8A_REPAIR3_PREVIOUS_CURRENT_CRASH_RECOVERY=PASS|FAIL`

`P8A_REPAIR3_PRODUCTION_CLI_NO_TEST_BYPASS=PASS|FAIL`

`P8A_REPAIR2_MAJOR_AUTHORITIES_REGRESSION=PASS|FAIL`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_PREP_READY=YES|NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

## 9. Stop

Push only `impl-p8a-deployment-package-rollback-repair3-2026-09-13` and stop for independent architect review. Do not deploy, start P8.B/P9, mutate main or touch P7 historical material.