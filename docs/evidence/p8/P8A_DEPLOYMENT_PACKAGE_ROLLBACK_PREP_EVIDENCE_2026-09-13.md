# P8.A deployment package + rollback preparation — Repair-2 evidence — 2026-09-13

Status: offline implementation and rehearsal only. Independent architect review
is still required. No P8.B, P9, live Telegram, real systemd, production path,
production database, Codex app-server or real Codex RPC was used.

## Authority and branch

P8A_REPAIR2_BASE_HEAD=09214a2a0a0ce92a2847dda24c3512447c822f1c

P8A_REPAIR2_BASE_TREE=56ac091de95ad809df9408a3da91fb4c00baa6f3

P8A_REPAIR2_PRIOR_EVIDENCE_BLOB=5ee4362a1d3aa22b6e3a3b4294d689296a260a99

P8A_REPAIR2_CODE_HEAD=8bbbeb9289f03a9888a3c262e4fd60768b2868a3

P8A_REPAIR2_CODE_TREE=8ad06b960d42b985b7069d4b297c28d5fb2961df

The implementation branch is
`impl-p8a-deployment-package-rollback-repair2-2026-09-13`, five linear
commits ahead of the exact Repair-2 base, with no merge or rebase. `origin/main`
remains `ea7f45a2b703bd7b9812e107ce843e4ff6182b57` with tree
`95a5bece8dc57b6d988d7aa86b08378d06d653be`.

## Changed paths

Only these P8.A implementation/test paths changed from the Repair-2 base:

```text
deploy/codex_control_deploy.py
src/codex_control/adapters/telegram/bot_api.py
src/codex_control/deployment.py
src/codex_control/service.py
tests/acceptance/test_p8a_deployment_offline.py
tests/unit/test_p8a_repair2_authority.py
```

No P7 files, ledgers or evidence, no `docs/ROADMAP.md`, and no
`docs/CURRENT_WORK.md` changed. No secret was committed.

## Repaired authority

`service.py` now exposes one shared async preflight. It loads config and
secrets, validates filesystem/profile/isolation authority, performs a read-only
DB schema check, then runs `CodexVersionProbe` through
`probe_supported_manifest`, `validate_manifest_authority`, and
`StorageRuntimeCapabilities`. The only default process invocation is bounded
`codex --version`; app-server/model/thread/turn/approval/delete RPCs are not
reachable from this preflight. An explicit callback is available only through
offline test assembly/verification seams.

The retained fake `#!/bin/sh; exit 0` executable now fails because its version
output is empty. Wrong `codex-cli 0.144.7` fails `validate` and fails assembly
before writable SQLite open or polling. Existing DB schema mismatch is checked
before the installed probe and before `SqliteStorage.open`; missing DB is not
ordinary serve authority. First install has the separate explicit
`initialize_controller_state` helper.

Telegram polling freezes `POLL_HTTP_MARGIN_SECONDS=5.0`; the actual injected
HTTP deadline for payload timeout 30 is 35.0 seconds. The default URL client
cap is at least 35.0 and does not clamp the polling request to 30.

Deployment layout accepts `/` only via explicit
`DeploymentRootAuthority(..., allow_production_root=True)`; default
alternate-root mode rejects it. No root authority test writes to `/`.

Production `stage_release` requires a Git worktree/repository and exact full
commit SHA. It verifies the commit and tree, exports tracked bytes with
`git archive`, records `source_git_sha` and `source_tree_sha`, and ignores
dirty or untracked working-tree content. The separately named
`stage_rehearsal_release` is synthetic-test-only.

Each staged release builds `.venv/bin/codex-control` privately with no-index,
no-deps, no-build-isolation semantics where local wheel prerequisites exist;
the dependency-free project has a deterministic source-relative launcher
fallback when this host lacks wheel. The final executable is regular,
non-symlink and executable. Staged validation disables bytecode writes so
artifact digests remain immutable.

Release publication is exact export -> private same-filesystem stage -> build ->
manifest -> digest/release validation -> immutable modes -> final validation ->
atomic rename. Export, build, manifest and validation failure hooks all leave
the final target absent; an existing valid target is left untouched. The
previous record is not replaced until the current symlink replacement succeeds,
so a failure at that boundary cannot fabricate a rollback target.

Production `install_upgrade`, `production_rollback`, and
`verify_installation` require explicit root authority, config, secrets,
service-unit, actual DB and installed-runtime authority. The old caller/default
schema and root+SHA switch surface is not exposed by the deployment CLI; caller-
fact primitives are clearly named `rehearsal_*`. Missing health evidence
returns `SWITCHED_AWAITING_SERVICE_HEALTH`, never health success. Explicit fake
PASS returns `HEALTH_CONFIRMED`; explicit fake FAIL performs schema-gated
rollback and returns `ROLLED_BACK`.

Verification reports the actual installed version/schema returned by the
bounded probe, alongside current release SHA/tree, executable, config/secrets,
actual DB schema, profiles/CODEX_HOME and unit/manifest digests. It never copies
`manifest.expected_codex_version` into installed authority.

## Digests

```text
service unit sha256 = 7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870
deployment helper sha256 = 0b446b72fc0d1921f9d62c777d637312f207656fd1dcfa0e015d23a515e7707b
deployment module sha256 = 7c75c27e26138a0d5b787e5b241c544c383826d3777ed4ff9ce8af638d1f4187
service module sha256 = da11bc09940d29266b85a4e718fce9fa414c02026ccc2a36f023b294844e4fd5
Telegram transport sha256 = 4dec24454e871e3061990f328d11123f0b9c979a62615aa2bef6ff83531a4995
Repair-2 focused test sha256 = 113dd78e8d7656c103e97e7759a4175264f192413c954ca98b7a4057f0e6463b
installed capability schema sha256 = 40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466
```

Final temporary-root release manifest digests:

```text
A (09214a2a0a0ce92a2847dda24c3512447c822f1c) = faa85754d44632d784ed8dda8a86755f277b124cb11dc6814629cfdb3e217315
B (8bbbeb9289f03a9888a3c262e4fd60768b2868a3) = e667d5d80e2674f372856fcac8c021545561918bf73c9e4ad0f9cf781da56e44
```

## Tests and rehearsal

Focused Repair-2 run first:

```text
PYTHONPATH=src python -m pytest -q tests/unit/test_p8a_repair2_authority.py tests/unit/test_p8a_configuration_transport.py tests/acceptance/test_p8a_deployment_offline.py
28 passed, 3 subtests passed
```

The focused file maps all mandatory blockers to:

```text
test_installed_codex_wrong_version_blocks_validate
test_installed_codex_wrong_version_blocks_serve_before_storage_and_poll
test_long_poll_http_deadline_exceeds_telegram_timeout
test_root_requires_explicit_production_authority
test_arbitrary_directory_cannot_claim_git_sha
test_exact_git_commit_tree_is_exported
test_stage_builds_release_local_codex_control_executable
test_build_failure_never_publishes_final_release
test_production_switch_requires_actual_db_config_secrets_runtime_preflight
test_missing_health_evidence_is_not_success
test_verify_probes_actual_installed_codex
test_production_rollback_reads_actual_db_schema
```

Additional focused coverage injects export/manifest/final-validation failures,
tests previous/current crash safety, untracked export exclusion, executable
regularity and exact source-tree verification.

Safe non-real regression run:

```text
PYTHONPATH=src python -m pytest -q tests/unit tests/integration tests/acceptance --ignore=tests/real
1089 passed, 650 subtests passed, 2 pre-existing warnings
```

P7 real tests were not run. Consumed historical P7 latches/evidence were not
reset, mutated, or retried.

The complete temporary-root rehearsal used exact object A above, then exact
committed object B: private stage/build/manifest/tree validation, atomic A,
production-shaped B preflight, current B, explicit fake health FAIL, actual
PRAGMA `user_version=4` rollback eligibility, and current A. Config, secrets,
and DB bytes were unchanged. The only writes were under the generated
temporary root; no network, systemd, live Telegram, or app-server effect was
used.

## Validation and zero-effect accounting

`python -m compileall -q src tests`, `git diff --check`, exact changed-path
scope review, and tracked secret/leakage review were run. The systemd source
unit was inspected read-only. `systemd-analyze verify` returned 0 for a
temporary path-substituted unit pointing at the fully staged release-local
executable; no unit installation or systemd mutation was performed.

```text
REAL_SYSTEMD_MUTATIONS=0
REAL_ETC_CODEX_CONTROL_WRITES=0
REAL_OPT_CODEX_CONTROL_WRITES=0
REAL_VAR_LIB_CODEX_CONTROL_WRITES=0
REAL_TELEGRAM_HTTP_CALLS=0
REAL_TELEGRAM_MESSAGES=0
REAL_CODEX_PROCESS_STARTS=0
REAL_CODEX_RPC_CALLS=0
REAL_P7_LEDGER_MUTATIONS=0
P8B_STARTED=0
P9_STARTED=0
P8A_PRODUCTION_EFFECTS=0
```

P8A_REPAIR2_INSTALLED_CODEX_PREFLIGHT=PASS
P8A_REPAIR2_SERVE_PREFLIGHT_ORDER=PASS
P8A_REPAIR2_LONG_POLL_DEADLINE=PASS
P8A_REPAIR2_PRODUCTION_ROOT_AUTHORITY=PASS
P8A_REPAIR2_EXACT_GIT_SOURCE_BINDING=PASS
P8A_REPAIR2_EXECUTABLE_RELEASE_BUILD=PASS
P8A_REPAIR2_ATOMIC_STAGE_PUBLICATION=PASS
P8A_REPAIR2_PRODUCTION_TRANSACTION_PREFLIGHT=PASS
P8A_REPAIR2_HEALTH_STATE_AUTHORITY=PASS
P8A_REPAIR2_TRUTHFUL_INSTALLED_VERIFY=PASS
P8A_REPAIR2_ROLLBACK_ACTUAL_SCHEMA=PASS
P8A_REPAIR2_BRANCH_AUTHORITY=PASS

P8A_PRODUCTION_EFFECTS=0
P8A_PREP_READY=YES

P8_REAL_DEPLOYMENT_AUTHORIZED=NO
P9_STARTED=NO
