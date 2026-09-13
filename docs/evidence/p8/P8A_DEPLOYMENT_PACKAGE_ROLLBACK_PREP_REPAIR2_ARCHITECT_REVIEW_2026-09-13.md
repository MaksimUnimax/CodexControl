# P8.A deployment package + rollback preparation Repair-2 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / MAJOR REPAIR-2 AUTHORITIES ACCEPTED FOR REUSE / THREE TRANSACTIONAL BLOCKERS + ONE CLI BOUNDARY REMAIN / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Binding candidate

- branch: `impl-p8a-deployment-package-rollback-repair2-2026-09-13`;
- candidate HEAD: `5ef7d19131335863f9c104f2ea363d6ed014cf82`;
- candidate tree: `dd66eb9e353049cd8749a2f7d40789fc10cbda92`;
- exact Repair-2 base: `09214a2a0a0ce92a2847dda24c3512447c822f1c`;
- candidate is six linear commits ahead of Repair-2 base, zero behind, merge-base exact Repair-2 base;
- changed paths are restricted to the P8.A deployment/service/Telegram/test/evidence surface;
- `origin/main` remained the frozen Repair-2 authority during execution.

## Accepted Repair-2 work

Independent source review accepts for reuse:

- real bounded installed-Codex preflight via `CodexVersionProbe` / `probe_supported_manifest` / exact manifest and storage-capability authority;
- shared serve/validate preflight before writable SQLite open and Telegram polling for existing deployments;
- ordinary serve requiring an existing schema-v4 DB;
- Telegram long-poll positive deadline margin;
- explicit `DeploymentRootAuthority`, with `/` rejected by default and available only under explicit authority;
- exact Git commit/tree binding and `git archive` tracked-source export;
- release manifest source commit/tree authority;
- private same-filesystem staging and atomic final release publication;
- release-local `.venv/bin/codex-control` executable surface;
- separation of caller-fact rehearsal primitives from production-shaped transaction functions;
- finite deployment health states where missing health evidence is not success;
- actual DB `PRAGMA user_version` use in production preflight/rollback;
- actual installed-Codex authority in verification;
- Repair-2 branch publication authority and focused regression suite.

These authorities must be preserved in Repair-3.

## Remaining blocking defects

### A. Explicit first-install state initialization fails for the canonical layout

`_initialize_controller_state()` correctly uses the shared preflight with `require_existing_db=False`, but that preflight still validates the configured `state_root` as an existing safe directory. The initializer then executes `Path(controller_db_path).parent.mkdir(..., exist_ok=False)`.

In the canonical configuration, `controller_db_path=/var/lib/codex-control/controller.sqlite3` and `state_root=/var/lib/codex-control`, so the database parent is the already-existing state root. The initializer therefore raises `FileExistsError`, maps it to `state_initialization_failed`, and cannot create the first schema-v4 controller DB.

No focused Repair-2 test invokes `initialize_controller_state()` with the canonical same-parent layout.

Required repair: accept an already-existing validated state/database parent, create only the missing DB through accepted schema-v4 storage authority, fail closed if DB already exists/symlink/unsafe, and prove an ordinary `serve` still never creates a missing DB.

### B. Staged executable validation occurs after final release publication

Production `install_upgrade()` performs `stage_release(...)`, which completes private export/build/manifest validation and atomically publishes `releases/<sha>`. Only after that final publication does `install_upgrade()` call `_run_staged_validate(target/.venv/bin/codex-control, ...)`.

Therefore a failing staged `codex-control validate` leaves a final immutable release directory present even though the deployment pre-switch validation failed. This violates the frozen requirement that the staged executable/config/secrets/DB/runtime authority must pass before final release publication for the production transaction.

Required repair: the production transaction must validate the executable while it is still in private staging, or stage into a transaction-private prepared release which is atomically published only after staged executable validation succeeds. A failed staged validation must leave the final release absent or preserve an already-existing validated release unchanged.

### C. `current` can switch before durable previous-release authority is committed

`rehearsal_switch_current()` prepares `.previous.next`, atomically replaces `current`, and only then replaces the durable `previous` record. If `current` replacement succeeds but `previous` replacement fails, the function raises `previous_record_failed` while the new current release is already selected. On the first upgrade there may be no durable `previous` record at all; on later upgrades it may be stale.

The focused test only injects failure at the first `os.replace` (current replacement), which proves no fabricated previous record when current fails. It does not test the inverse crash/failure boundary after current succeeds.

Required repair: retain a crash-recoverable pending previous authority or use an equivalent journal/transaction marker so that after a successful current switch the exact old current remains recoverable even if durable previous finalization fails. Production rollback/recovery must understand the pending state. Do not delete the only old-current authority after a partial switch.

### D. Production deployment CLI still exposes a hidden test-only bypass

`deploy/codex_control_deploy.py upgrade` accepts hidden `--test-only-authority` and passes it into the production-shaped transaction. That relaxes production root-owner/permission checks on config/secrets and is inappropriate on the future P8.B command surface.

Required repair: keep test-only authority injection in Python/offline test seams only. Remove the test-only bypass from production deployment CLI commands. P8.A tests can call Python APIs directly.

## Architect verdict

`P8A_REPAIR2_MAJOR_AUTHORITIES=ACCEPTED_FOR_REUSE`

`P8A_REPAIR2_FIRST_INSTALL_STATE=REWORK_REQUIRED`

`P8A_REPAIR2_STAGED_VALIDATE_BEFORE_PUBLICATION=REWORK_REQUIRED`

`P8A_REPAIR2_PREVIOUS_CURRENT_CRASH_SAFETY=REWORK_REQUIRED`

`P8A_REPAIR2_PRODUCTION_CLI_TEST_BYPASS=REWORK_REQUIRED`

`P8A_REPAIR2_ARCHITECT_ACCEPTED=NO`

`P8A_PREP_READY=NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

P8.A Repair-3 must start from exact candidate `5ef7d19131335863f9c104f2ea363d6ed014cf82`, preserve all accepted Repair-2 work, and repair only the four bounded defects above.