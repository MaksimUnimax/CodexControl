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

## Repair-4 pending-journal crash atomicity evidence

Repair-4 was executed from the exact required base:

P8A_REPAIR4_BASE_HEAD=3bb4cff0436103e75567a4ebdccee51c537a2b63

P8A_REPAIR4_BASE_TREE=fc3818c5805ca21e785c1f2c0d3d87e381bed6d2

The implementation commit is:

P8A_REPAIR4_IMPLEMENTATION_HEAD=6ffd5193962115d6e07114369e4d442ea25c34d1

P8A_REPAIR4_IMPLEMENTATION_TREE=0c16a336f70008461daa002e0f4af87f7ca70656

The final evidence publication is a later linear commit on the same branch;
the implementation HEAD/tree above are the exact code release objects used as
temporary-root rehearsal B. No merge, rebase, squash or force push was used.

### Changed paths

From the exact Repair-4 base, the authorized changes are limited to:

```text
src/codex_control/deployment.py
tests/unit/test_p8a_repair4_authority.py
docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md
```

No service.py, Telegram/config/secrets, P7 material, migrations,
ROADMAP.md, CURRENT_WORK.md, P8.B or P9 file was changed. No secret or user
content was added.

The prompt-specified filenames
`P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_REPAIR3_ARCHITECT_REVIEW_2026-09-13.md`
and `P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_REPAIR4_CONTRACT_2026-09-13.md`
were absent from the fetched repository. The existing
`P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_CONTRACT_2026-09-13.md`, prior P8.A
evidence, and repository history were used as the available binding
authority; no authority document was modified.

### Old-defect reproduction

Before the repair, a temporary-root first-upgrade reproduction created valid
release A as current with no durable previous, wrote durable
`PREPARED(A,B)`, replaced current with B, and stopped before the journal state
update. Repair-3 recovery observed `current=B` with `PREPARED(A,B)` and
rejected it as:

```text
recovery_result=REJECTED
error_category=pending_current_disagreement
```

The reproduction used only a generated temporary root and did not modify
production paths.

### Atomic journal algorithm

`_write_pending()` validates the canonical absolute
`opt/codex-control/.previous.next` shape and rejects symlink/special-file
authority. It serializes exactly three keys (`old_current_sha`,
`new_target_sha`, `state`) with bounded ASCII JSON and a 512-byte maximum.
Each attempt creates a same-directory private `.previous.next.<uuid>.tmp`
using `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600; writes the complete record,
fsyncs and closes it, atomically replaces the canonical pending file, then
fsyncs the containing directory. Pre-replace failures remove only the temp
created by that attempt and preserve the prior canonical bytes. Post-replace
directory durability failure retains the new valid canonical record and fails
closed. There is no direct `O_TRUNC` write to canonical pending authority.

Reads require a regular non-symlink bounded file, use `O_NOFOLLOW`, reject
malformed JSON, unexpected keys, invalid SHA shapes, and non-enum states.
Temp collision, symlink and special-file cases fail closed without deleting
the prior pending record.

### PREPARED/current recovery matrix

For valid `PREPARED(old,new)`:

```text
old != None and current == old  -> validate old/current, remove pending,
                                   leave durable previous unchanged
old == None and current == None -> remove pending; no switch occurred
current == new                   -> validate new and old when present,
                                   durably continue CURRENT_SWITCHED, promote
                                   exact old to previous, finalize where possible
otherwise                        -> fail closed: pending_current_disagreement
```

The `current==new` path also covers an interrupted first upgrade where no
previous file existed before the switch. It promotes the exact retained old
current before rollback consumes it. `CURRENT_SWITCHED` requires current=new
and validates the exact old release before finalization. `FINALIZED` requires
the committed previous to match old (or no old authority) before pending is
removed. Recovery never falls back to a stale unrelated previous file.

### Focused failure transitions

The injected failure between current replacement and the
`CURRENT_SWITCHED` journal replacement left the canonical file byte-for-byte
as complete `PREPARED(A,B)`, neither empty, partial, malformed nor deleted.
Restart recovery observed `current=B`, promoted exact A to durable previous,
and rollback returned `current=A`.

The mandatory first-upgrade case (`current=A`, previous absent, interrupted
`A->B`) passed: recovery created previous=A before rollback, and rollback
returned current=A without stale authority. A failure of the FINALIZED journal
replacement left durable previous=A and a complete CURRENT_SWITCHED record;
restart recovery converged and rollback remained able to return current=A.
Current replacement failure and previous finalization failure retained their
Repair-3 truthful authority behavior.

### Temporary-root rehearsal and digests

The additional exact-object rehearsal used:

```text
A commit/tree = 3bb4cff0436103e75567a4ebdccee51c537a2b63 /
                fc3818c5805ca21e785c1f2c0d3d87e381bed6d2
B commit/tree = 6ffd5193962115d6e07114369e4d442ea25c34d1 /
                0c16a336f70008461daa002e0f4af87f7ca70656
A manifest sha256 = a4bdf113cf0ad2ea089dcb2527082f4d9913eac30b77601d3c801c0749bdf801
B manifest sha256 = 4ae150ca29a2cca62f0f6ce3dc5d4857c1871c3870033b4eb513b64f32053f95
```

The rehearsal performed explicit first-install schema-v4 initialization,
readback, exact Git A private stage/build/validate/publication, current A,
exact Git B private stage/build/validate/publication, PREPARED(A,B), current
B, explicit failed health, and actual-schema rollback to A. It also exercised
current replacement failure, previous finalization failure,
PREPARED-to-CURRENT_SWITCHED journal-write failure, restart after that
failure, and FINALIZED journal-write failure. Config, secrets and SQLite DB
bytes were unchanged after the explicit first-install fixture. All filesystem
work was beneath generated temporary roots; no Telegram, systemd, live Codex
app-server or real Codex RPC was used.

Current implementation digests:

```text
src/codex_control/deployment.py = b33888191d4fcca119268a5b43c15d51f57ad3287151f9a8d0343485612e0951
tests/unit/test_p8a_repair4_authority.py = 9cc2c585240069865e58375bca2c353b04fcef98740c20c90d9507f1c96b88ce
src/codex_control/service.py = b4ad4e45846c7bbe93e03d36b0501e606ce38f465cd5d3ae467517112181fb41
service unit = 7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870
installed capability schema = 40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466
```

### Validation totals and zero-effect accounting

Focused Repair-4, Repair-3, Repair-2, P8.A configuration/transport and P8.A
offline acceptance tests passed before publication. Repair-3 accepted
first-install, missing-DB serve, staged validation before publication,
current-switch failure, previous-finalization failure, restart recovery and
production CLI no-test-bypass authorities all passed. Repair-2 authority tests
also passed. All P7 real gates remained unset and no consumed latch was
touched.

The final safe aggregate was 1109 passed, 653 subtests, and 2 pre-existing
warnings. The final focused P8.A aggregate was 48 passed and 6 subtests.
Warnings were the existing pytest collection and unraisable-coroutine
warnings; no test failed.

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

P8A_REPAIR4_PENDING_JOURNAL_ATOMIC_WRITE=PASS
P8A_REPAIR4_PREPARED_AFTER_SWITCH_RECOVERY=PASS
P8A_REPAIR4_FIRST_UPGRADE_OLD_CURRENT_RECOVERY=PASS
P8A_REPAIR4_FINALIZED_TRANSITION_RECOVERY=PASS
P8A_REPAIR3_ACCEPTED_AUTHORITIES_REGRESSION=PASS

P8A_PRODUCTION_EFFECTS=0
P8A_PREP_READY=YES

P8_REAL_DEPLOYMENT_AUTHORIZED=NO
P9_STARTED=NO

## Repair-3 final transaction repair evidence

Repair-3 was executed from the exact required base:

P8A_REPAIR3_BASE_HEAD=5ef7d19131335863f9c104f2ea363d6ed014cf82

P8A_REPAIR3_BASE_TREE=dd66eb9e353049cd8749a2f7d40789fc10cbda92

The implementation transaction is the linear commit
`a3416c746ec59ecec19c745c2cb792aa60e2dea4` with tree
`081f23ce6cd00c94d836eb785538172af3094fbc`. The evidence update is a
follow-up linear commit; the final branch HEAD/tree are recorded in the
handoff report. `origin/main` was unchanged at
`674ea22b488cb8d4064aff504aebb62cd0516e7d` / tree
`86329f2ce8b40e0ae81f1197ea9910e8b1bd36b2`.

Changed files from the exact Repair-3 base are limited to:

```text
deploy/codex_control_deploy.py
src/codex_control/deployment.py
src/codex_control/service.py
tests/unit/test_p8a_repair3_authority.py
docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md
```

No P7 material, ROADMAP.md, CURRENT_WORK.md, migrations, P8.B or P9 files
changed. No secret was added.

### First-install state

The initializer now performs config/secrets parsing, filesystem/profile/runtime
authority validation, installed Codex capability validation, absent-leaf and
safe-parent checks, explicit subordinate-parent creation only beneath the
configured controller DB root, SqliteStorage schema-v4 creation and close, and
PRAGMA `user_version=4` readback. Canonical `state_root/controller.sqlite3`
with an existing state root passes; a second attempt returns
`database_already_initialized`. Symlink DB paths, existing special DB files,
unsafe parents and missing-DB ordinary serve are rejected without DB creation.

### Private-stage validation and publication

Production `install_upgrade` now performs exact Git export, private executable
build, private manifest/artifact validation, private staged executable
`codex-control validate` against the target config/secrets/existing schema-v4
DB/installed Codex authority, atomic publication to `releases/<sha>`, final
release validation, and only then current switching. The staged command has no
test-only authority argument. Injected staged validation failure leaves the
new final release absent and current unchanged. A pre-existing valid identical
release remains intact under failed revalidation. Successful private-stage
validation published an exact source commit/tree manifest and a regular
release-local `.venv/bin/codex-control` executable.

Repair-3 implementation digests:

```text
deploy/codex_control_deploy.py = e607e94433fe5cf448b49bc0a91968504cf2958fef6664f66ae2e1895f1093f6
src/codex_control/deployment.py = a363e9abb0aaaafa3ba36fb238ac35e12152b7386a79f107794e4bf701cb165f
src/codex_control/service.py = b4ad4e45846c7bbe93e03d36b0501e606ce38f465cd5d3ae467517112181fb41
tests/unit/test_p8a_repair3_authority.py = 4cf12c7139d4684709013d130bd9ba9e0971993661eb37641050470d4a20ad5b
service unit = 7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870
exact-base temporary release manifest = b3e1a92e759d0c2f8493267c7213589d57f05e7b93e2047cd382ca291286632d
```

### Previous/current crash recovery

`.previous.next` is now a durable, mode-0600 pending transaction record bound
to `old_current_sha`, `new_target_sha` and one of `PREPARED`,
`CURRENT_SWITCHED`, or `FINALIZED`. It is persisted before current switching,
retained after a successful current switch until previous finalization is
durable, and removed only after FINALIZED. Current replacement failure removes
the pending record and leaves current/durable previous unchanged. Previous
finalization failure leaves current on the new release and retains the exact
immediate old release in pending authority. Restart recovery validates both
release manifests, promotes that pending old release to durable previous, and
then rollback uses it instead of stale previous data. Malformed records,
wrong old/new SHAs, missing releases, manifest mismatches, current disagreement
and ambiguous authority fail closed. The first-upgrade A(no previous)->B case
was explicitly tested and recovers exact A.

### CLI boundary

`deploy/codex_control_deploy.py` no longer defines or reads
`--test-only-authority`; argparse rejects that flag. Production `stage`,
`upgrade`, `rollback` and `verify` continue to require their production
authority inputs. Offline tests use explicit Python-level `test_only=True` or
injected seams only.

### Test and rehearsal record

Repair-3 focused suite, including all required named tests:

```text
PYTHONPATH=src python -m pytest -q tests/unit/test_p8a_repair3_authority.py tests/unit/test_p8a_repair2_authority.py tests/unit/test_p8a_configuration_transport.py tests/acceptance/test_p8a_deployment_offline.py
41 passed, 3 subtests passed
```

Repair-2 focused authorities were re-run in that suite; the prior Repair-2
focused baseline remains `28 passed, 3 subtests passed`. The complete safe
non-real regression suite was re-run:

```text
PYTHONPATH=src python -m pytest -q tests/unit tests/integration tests/acceptance --ignore=tests/real
1102 passed, 2 warnings, 650 subtests passed
```

The warnings are the existing pytest collection/unraisable coroutine warnings;
no test failed. Historical real P7 gates were not run or reset.

The temporary-root rehearsal passed: existing safe state root -> explicit
first-install -> schema-v4 readback -> ordinary preflight eligibility; exact
Git-object A private stage/build/validate/publication -> current A; exact
Git-object B private stage/validate/publication -> A-to-B switch and previous
authority; explicit fake health failure -> actual-schema rollback to A. It
also injected staged validation failure before publication, current replacement
failure, previous finalization failure, and restart recovery. Config, secrets
and DB bytes were unchanged after first-install fixture creation. No network,
systemd, live Telegram, Codex app-server/RPC or P7 surface was used.

Final validation commands passed:

```text
python -m compileall -q src tests
git diff --check
tracked secret/leakage scan: no live secret material
changed-path scope check: P8.A implementation/tests/evidence only
```

Zero-effect accounting:

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

P8A_REPAIR3_FIRST_INSTALL_STATE=PASS
P8A_REPAIR3_STAGED_VALIDATE_BEFORE_PUBLICATION=PASS
P8A_REPAIR3_PREVIOUS_CURRENT_CRASH_RECOVERY=PASS
P8A_REPAIR3_PRODUCTION_CLI_NO_TEST_BYPASS=PASS
P8A_REPAIR2_MAJOR_AUTHORITIES_REGRESSION=PASS

P8A_PRODUCTION_EFFECTS=0
P8A_PREP_READY=YES

P8_REAL_DEPLOYMENT_AUTHORIZED=NO
P9_STARTED=NO
