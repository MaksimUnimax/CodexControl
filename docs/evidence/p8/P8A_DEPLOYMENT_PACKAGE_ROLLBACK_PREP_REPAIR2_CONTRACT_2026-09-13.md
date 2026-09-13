# P8.A deployment package + rollback preparation — Repair-2 contract — 2026-09-13

Status: **FROZEN / ZERO PRODUCTION EFFECT / EXECUTE UNFINISHED REPAIR-1 REQUIREMENTS / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Exact Repair-2 base

P8.A Repair-2 must start from exactly:

- HEAD `09214a2a0a0ce92a2847dda24c3512447c822f1c`;
- tree `56ac091de95ad809df9408a3da91fb4c00baa6f3`;
- evidence blob `5ee4362a1d3aa22b6e3a3b4294d689296a260a99`.

This commit is source-reviewable and exactly two linear commits ahead of the prior Repair-1 base `c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de`.

The prior repaired source was mistakenly pushed to `impl-p8a-deployment-package-rollback-2026-09-13`. Repair-2 publication must use only:

`impl-p8a-deployment-package-rollback-repair2-2026-09-13`

No rebase, merge, squash or force push.

## Zero-production-effect boundary

Repair-2 remains offline implementation/acceptance only. It must not write real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control`, `/etc/systemd/system`; must not invoke production systemctl/service/daemon-reload; must not use a live Telegram token/network; must not start real Codex app-server or make real Codex RPCs; must not mutate P7 retained material; must not start P8.B or P9.

`P8A_PRODUCTION_EFFECTS=0` remains mandatory.

## Preserve accepted work

Preserve the accepted P8.A surfaces unless directly required by the repairs below:

- complete V1 config parser;
- non-shell root-only secrets parser;
- group/private routing correction;
- service shutdown ordering;
- existing Telegram response/error validation;
- application/storage/runtime composition;
- SLEEP-on-start and recovery-before-poll semantics;
- systemd unit policy shape;
- immutable release/current/config/state layout concept;
- release manifest and non-destructive rollback concepts;
- temporary-root rehearsal framework.

Do not redesign P0-P7 semantics.

## 1. Implement actual installed-Codex preflight

Create one reusable asynchronous production preflight authority that uses the accepted bounded installed authority:

- `CodexVersionProbe(config.codex_executable)`;
- `probe_supported_manifest(probe)`;
- `validate_manifest_authority(...)` / `StorageRuntimeCapabilities.validate(...)` as applicable;
- exact `codex-cli 0.144.6` and exact accepted schema SHA authority.

The production preflight may only spawn the bounded `codex --version` process. It must not start app-server or issue model/thread/turn RPCs.

`codex-control validate` must invoke this actual probe.

`serve` must invoke the same actual probe before storage/application assembly can reach startup recovery or Telegram polling.

Because the accepted probe is async, the CLI may make `validate` run through an async wrapper. Do not duplicate probe logic in multiple places.

Provide an explicit test-only installed-authority seam/factory. A fake executable that prints nothing and exits 0 must fail the default production authority. A deterministic injected exact accepted authority may pass offline tests without real Codex effects.

## 2. Enforce serve preflight before mutable storage open

For an existing deployment, ordering must be:

config -> secrets -> filesystem/profile authority -> read-only DB schema check -> installed Codex probe -> writable `SqliteStorage.open()` -> boot/application assembly -> startup recovery -> polling.

An existing wrong DB schema must fail before writable storage open/migration.

A wrong installed Codex authority must fail before writable storage open, boot epoch mutation, recovery and polling.

A missing DB is not ordinary serve authority. Add an explicit deployment initialization action for first install; ordinary serve should require the configured DB already exists and is compatible.

The explicit initialization helper may create only the configured controller DB/state authority under an authorized deployment root and must create current schema v4 safely. It remains offline-tested only.

## 3. Fix Telegram long-poll timeout relationship

Freeze a positive bounded response margin, e.g. `POLL_HTTP_MARGIN_SECONDS = 5.0`.

For default `poll_timeout=30`, the actual HTTP socket deadline used by `UrlLibHttpClient` for `getUpdates` must be strictly greater than 30 (normally 35), not clamped back to 30.

Do not use one client-wide timeout cap that truncates polling to the server timeout. Either construct the default HTTP client with a cap at least `max(request_timeout, poll_timeout + margin)` or let per-request timeout be authoritative within a bounded max.

Tests must inspect the actual timeout received by the HTTP seam and prove `http_timeout > telegram_payload_timeout`.

## 4. Add explicit production-root deployment authority

Refactor layout authority so safe alternate roots remain the default, while a distinct immutable/explicit production-root flag permits `root='/'` for later P8.B.

For example, use a `DeploymentRootAuthority` value or explicit `allow_production_root=False` argument propagated through all path-calculating deployment operations.

Rules:

- `/` rejected by default;
- `/` accepted only when explicit production authority is true;
- P8.A tests must never perform actual writes under `/`; production-root tests may validate path computation through pure functions/mocked filesystem seams only;
- no implicit environment-variable switch to production mode.

## 5. Bind release source to exact Git commit and tree

Extend `ReleaseManifest` with exact source authority including at least:

- `source_git_sha` (or make existing `git_sha` explicitly source SHA);
- `source_tree_sha`.

Production staging must derive tracked source bytes from the exact Git object rather than trusting arbitrary caller directory contents.

Preferred implementation:

- repository path must be a Git worktree/repository;
- verify requested commit exists;
- obtain exact tree SHA with Git object plumbing;
- export the exact commit with `git archive <sha>` into private staging;
- do not copy arbitrary untracked/dirty working-tree files;
- persist exact commit/tree in manifest.

An equally strong object-store export is acceptable.

Test-only synthetic release fixtures may use a separate clearly named artifact-authority constructor, but the production stage path must not accept arbitrary source directory + caller SHA as sufficient proof.

Required negatives:

- arbitrary non-Git directory cannot be staged as accepted production SHA;
- wrong/nonexistent SHA fails;
- manifest wrong tree fails;
- dirty/untracked worktree cannot alter exported release bytes;
- exported tracked bytes match exact commit authority.

## 6. Build a genuinely executable release

The immutable staged release must include the executable used by the systemd unit:

`<release>/.venv/bin/codex-control`

Build within the private staging directory before publication.

Use offline/no-network installation semantics. With the current dependency surface, acceptable pattern is equivalent to:

- `/usr/bin/python -m venv <staging>/.venv`;
- `<venv>/bin/python -m pip install --no-deps --no-build-isolation <exported-source>`;

provided the build dependencies required by `pyproject.toml` are already available locally and no index/network access is attempted. Set environment/options to prevent index access. If offline build prerequisites are unavailable, fail closed.

Validate executable is regular, executable, resolves inside staging, and `codex-control --help` / parser invocation is finite without live effects.

Before final publication, run staged `codex-control validate` through an explicit offline preflight injection/harness against temporary config/secrets/DB/runtime authority. Do not introduce a production CLI flag that bypasses installed authority on a real host.

## 7. Make stage publication atomic

Use a private same-filesystem sibling such as `.stage-<sha>-<nonce>` under releases parent.

Perform exact export, executable build, manifest write, chmod/immutability setup and complete `validate_release` against that private directory.

Only after full success atomically rename private staging to final `releases/<sha>`.

On any failure:

- clean only the private staging path created by the attempt;
- final target remains absent, or an existing previously valid release remains unchanged;
- never treat a partial final directory as idempotent success.

Tests must inject export/build/manifest/validation failures and prove final target absence/unchanged existing release.

## 8. Strengthen validate_release

Require manifest source SHA/tree shapes and exact artifact digest match.

Require `.venv/bin/codex-control` exists, is regular, non-symlink and executable, and is included in artifact digests.

If a service-unit digest is required by production contract, validate against the supplied/frozen unit authority rather than merely accepting any well-formed SHA string.

## 9. Split rehearsal APIs from production transaction APIs

Current `switch_current(root, sha, current_db_schema=4)` and `rollback(...=4)` are acceptable only as clearly named/pure rehearsal primitives if they remain caller-fact based.

Add production transaction functions/commands that derive authority from actual config/secrets/DB/install state and cannot be invoked without it.

Production-capable switch/upgrade must require/derive:

- explicit deployment root authority;
- target exact release manifest/source tree;
- config path;
- secrets path;
- configured DB path;
- read-only actual DB `PRAGMA user_version`;
- installed Codex preflight;
- staged executable validation;
- current/previous release authority.

The production deploy CLI must not have a command capable of switching `current` with only root + SHA.

Rename unsafe low-level commands to `rehearsal-*` or hide them from production CLI if necessary.

## 10. No-health-evidence is not success

Introduce a finite deployment state/result enum or equivalent, with at least:

- `PRE_SWITCH_VALIDATED`;
- `SWITCHED_AWAITING_SERVICE_HEALTH`;
- `HEALTH_CONFIRMED`;
- `HEALTH_FAILED_ROLLBACK_REQUIRED`;
- `ROLLED_BACK`.

A production switch ends at `SWITCHED_AWAITING_SERVICE_HEALTH` until P8.B supplies an explicit health observation.

`health_check=None` must never yield `healthy=True` or `HEALTH_CONFIRMED`.

The offline rehearsal helper may take an explicit fake health result and exercise rollback.

## 11. Truthful installed verification

Make `verify_installation` asynchronous or provide an async production verifier so it can execute the accepted installed Codex version probe.

Do not populate installed version from manifest.expected value.

Verification must independently derive and compare:

- actual `codex --version` installed authority;
- supported capability/schema manifest authority;
- current exact release SHA/tree;
- release executable;
- actual config/secrets authority;
- actual DB schema;
- configured profiles/CODEX_HOME authority;
- unit digest;
- release manifest digest.

Wrong installed Codex must fail verification.

## 12. Production rollback must read actual DB schema

Production rollback authority must load config, derive controller DB path and read actual `PRAGMA user_version` itself. It must then validate previous release schema support before any symlink switch.

No default/caller integer may substitute for actual production DB schema.

Keep low-level injected-schema rollback only as explicitly rehearsal/test-only API if needed.

## 13. Preserve and strengthen previous/current atomicity

Ensure the previous-release record is updated in an order that cannot claim an uncommitted target if current symlink switch fails.

Tests must inject failure between previous-record preparation and current replacement and prove rollback target remains truthful.

## 14. Branch/publication authority

Repair-2 must be implemented and pushed only to:

`impl-p8a-deployment-package-rollback-repair2-2026-09-13`

which must start at exact candidate `09214a2a0a0ce92a2847dda24c3512447c822f1c`.

Do not continue pushing repair commits to the original P8.A branch.

## 15. Mandatory regression tests for every prior blocker

Add focused tests whose names clearly cover all of:

1. `test_installed_codex_wrong_version_blocks_validate`;
2. `test_installed_codex_wrong_version_blocks_serve_before_storage_and_poll`;
3. `test_long_poll_http_deadline_exceeds_telegram_timeout`;
4. `test_root_requires_explicit_production_authority`;
5. `test_arbitrary_directory_cannot_claim_git_sha`;
6. `test_exact_git_commit_tree_is_exported`;
7. `test_stage_builds_release_local_codex_control_executable`;
8. `test_build_failure_never_publishes_final_release`;
9. `test_production_switch_requires_actual_db_config_secrets_runtime_preflight`;
10. `test_missing_health_evidence_is_not_success`;
11. `test_verify_probes_actual_installed_codex`;
12. `test_production_rollback_reads_actual_db_schema`.

Equivalent names are acceptable only if the evidence maps each blocker to a specific test.

The old 14-test focused suite is insufficient by itself.

## 16. Evidence contract

Update the existing P8.A evidence and include exact Repair-2 base/head/tree, complete changed paths, exact test names/results and all repaired digests.

End exactly with:

`P8A_REPAIR2_INSTALLED_CODEX_PREFLIGHT=PASS|FAIL`

`P8A_REPAIR2_SERVE_PREFLIGHT_ORDER=PASS|FAIL`

`P8A_REPAIR2_LONG_POLL_DEADLINE=PASS|FAIL`

`P8A_REPAIR2_PRODUCTION_ROOT_AUTHORITY=PASS|FAIL`

`P8A_REPAIR2_EXACT_GIT_SOURCE_BINDING=PASS|FAIL`

`P8A_REPAIR2_EXECUTABLE_RELEASE_BUILD=PASS|FAIL`

`P8A_REPAIR2_ATOMIC_STAGE_PUBLICATION=PASS|FAIL`

`P8A_REPAIR2_PRODUCTION_TRANSACTION_PREFLIGHT=PASS|FAIL`

`P8A_REPAIR2_HEALTH_STATE_AUTHORITY=PASS|FAIL`

`P8A_REPAIR2_TRUTHFUL_INSTALLED_VERIFY=PASS|FAIL`

`P8A_REPAIR2_ROLLBACK_ACTUAL_SCHEMA=PASS|FAIL`

`P8A_REPAIR2_BRANCH_AUTHORITY=PASS|FAIL`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_PREP_READY=YES|NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

Do not reuse the original `P8A_PREP_READY=YES` as proof of Repair-2.

## 17. Validation

Run focused Repair-2 tests first, then safe unit/integration/acceptance and P0-P7 non-real regressions with real gates unset. Preserve immutable historical blockers.

Run compileall, git diff --check, secret/leakage scan and exact changed-path scope.

Run a complete temporary-root exact-Git-source A->B rehearsal using the repaired production-shaped staging path: exact object export -> private stage -> offline executable build -> manifest/source-tree validation -> atomic publication -> pre-switch authority -> current A -> B -> explicit fake failed health -> actual-schema-compatible rollback -> A. Prove config/secrets/state bytes unchanged.

No production filesystem/service/network/Codex app-server effects are authorized.

## 18. Stop condition

If implementing actual production-root transaction reveals a need to change accepted P0-P7 application/storage/Codex semantics, stop that portion with `ARCHITECTURE_DECISION_REQUIRED`; do not silently redesign.

P8.B and P9 remain blocked until independent architect acceptance of Repair-2.