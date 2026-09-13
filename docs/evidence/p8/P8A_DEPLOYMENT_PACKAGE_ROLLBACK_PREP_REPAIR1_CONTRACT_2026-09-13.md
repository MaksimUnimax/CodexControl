# P8.A deployment package + rollback preparation — Repair-1 contract — 2026-09-13

Status: **FROZEN / ZERO PRODUCTION EFFECT / REPAIR ONLY / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Exact repair base

Repair only candidate:

- HEAD `c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de`;
- tree `d78533eedee7495adb682ccbeab90eb374b9c808`.

Do not redesign accepted P0-P7 behavior or the accepted P8.A concepts. Repair only the production/deployment gaps identified by the architect review.

## Preserve accepted work

Preserve unless directly required by this repair:

- strict V1 config parser and explicit profile/fleet/path model;
- non-shell root-only secrets authority;
- Telegram safe error/redaction and accepted P6 mutating-effect semantics;
- accepted P3-P7 application composition;
- restart SLEEP and recovery-before-poll ordering;
- root systemd service shape and external config/secrets/state;
- immutable release/current layout concept;
- schema-gated rollback concept;
- zero-production-effect temporary-root testing.

## 1. Real installed-Codex preflight

Add a production preflight that reuses the accepted bounded `CodexVersionProbe` + exact supported manifest/storage-capability authority.

It must execute only the bounded read-only `codex --version` probe; it must not start app-server or make model/thread/turn RPCs.

`codex-control validate` must compare actual installed version/capability authority to exact expected 0.144.6/schema authority and fail safe on mismatch.

`serve` must execute equivalent installed-runtime preflight before ordinary Telegram polling and before any Codex app-server acquisition.

Provide an explicit offline injected probe seam. A fake executable that merely exits 0 must NOT pass unless the injected test authority returns the exact accepted installed manifest.

## 2. Startup preflight ordering

Before ordinary polling, production `serve` must prove:

config -> secrets -> filesystem/profile authority -> DB schema compatibility -> installed Codex authority -> assembly -> startup recovery -> poll.

Do not rely on first user prompt/runtime acquire to discover version mismatch.

Existing DB schema mismatch must fail before `SqliteStorage.open()` can silently migrate it in the production serve path.

If initial DB creation is supported, make it an explicit deployment/state-initialization transaction, not an accidental side effect of ordinary `serve` preflight.

## 3. Long-poll deadline repair

The default HTTP deadline for Telegram long polling must be strictly greater than the Telegram server-side poll timeout by a bounded positive response/transport margin.

Do not clamp a requested `poll_timeout + margin` back to `poll_timeout`.

Keep all deadlines bounded. Test normal empty long-poll completion at the configured server timeout without spurious `NETWORK_AMBIGUOUS`.

## 4. Production-root deployment authority

Keep alternate-root safety as the default for P8.A tests.

Add an explicit production-root authority mode capable of targeting real `/` only when a distinct production flag/authority is supplied by a later P8.B invocation.

Without that explicit mode, `/` remains rejected.

No P8.A test may write to real `/opt/codex-control`, `/etc/codex-control`, `/var/lib/codex-control` or systemd paths.

## 5. Exact source-to-SHA binding

A release published as `<FULL_GIT_SHA>` must be proven to derive from that exact source commit/tree.

Preferred authority: export/build from the exact Git commit using a deterministic `git archive`/object authority or require a clean exact repository HEAD/tree and build only tracked content. Untracked/modified source must not be silently included under the accepted SHA.

Persist safe source commit/tree authority in the release manifest.

Negative tests: wrong SHA, dirty tracked source, untracked injection if the chosen build path could include it, wrong tree/source manifest.

## 6. Executable release build

A staged release must contain the executable referenced by systemd before final publication.

Canonical current unit expects:

`<release>/.venv/bin/codex-control`

Build the release environment without live application/network effects. Do not fetch arbitrary dependencies from the network during production staging; use an explicit offline/no-deps/no-build-isolation strategy compatible with the repository's dependency surface, or freeze an equally deterministic packaged executable layout and update the unit consistently.

Run the staged executable's `codex-control validate` in offline pre-switch mode against the target config/secrets/state/runtime authority.

A release lacking its executable must fail staging/validation.

## 7. Atomic staging publication

Never copy/build directly into final `releases/<sha>`.

Use a private same-filesystem temporary sibling, fully export/build/manifest/validate there, fsync/close as practical, then atomically rename/publish to `releases/<sha>`.

On failure, final release path must remain absent or an already-valid immutable release must remain unchanged. No partial final directory may be accepted as a release.

## 8. Real pre-switch transaction

Future production switch/upgrade must require actual authority, not caller defaults:

- exact source/tree and release manifest;
- executable present;
- config authority;
- secrets authority;
- actual controller DB `PRAGMA user_version` read from the configured database;
- schema compatibility with target release;
- actual installed Codex authority;
- staged executable `codex-control validate` success;
- current target/previous target authority.

Do not let the production CLI switch using a default integer `current_db_schema=4` without reading the database.

A rehearsal-only pure function may accept injected schema/health facts, but production-mode commands must derive them from real bounded authorities.

## 9. Health semantics

Do not interpret absence of a health probe as production health success.

P8.A may keep service restart out of scope, but the deployment material must distinguish:

- PRE_SWITCH_VALIDATED;
- SWITCHED_AWAITING_SERVICE_HEALTH;
- HEALTH_CONFIRMED;
- HEALTH_FAILED_ROLLBACK_REQUIRED/ROLLED_BACK.

The later P8.B prompt will own systemd restart/health observation.

Offline A->B->failed health->A rollback rehearsal remains required.

## 10. Truthful deployment verification

`verify_installation` must probe and report actual installed Codex authority, not copy expected version from the release manifest.

It must verify:

- current exact release SHA/tree/manifest;
- staged executable exists;
- actual config/secrets authority;
- actual DB schema;
- explicit profiles/CODEX_HOME authority;
- actual installed Codex version/capability authority;
- unit digest and release manifest digest.

Mismatch must fail closed.

## 11. Initial-state authority

Define a safe explicit initial-install state path if the production DB is absent. Ordinary `serve` must not silently reinterpret a missing historical DB as a normal compatible upgrade.

An explicit deployment initialization helper/command is allowed if it creates only the configured controller state under an authorized production root and uses accepted schema-v4 storage authority. It remains offline-tested only in P8.A.

## 12. Rollback

Rollback continues to change only executable release selection/service lifecycle.

Never restore or downgrade DB/config/secrets/CODEX_HOME automatically.

Rollback must read the actual current DB schema and validate the previous release's declared compatibility before atomic switch.

Previous-release record publication should be crash-safe/atomic enough that a failed switch cannot fabricate a different rollback target.

## 13. Test matrix additions

Add at minimum:

- wrong real Codex version fails validate before polling;
- injected exact installed authority passes offline without app-server;
- serve ordering proves runtime probe before SQLite mutation/poll where applicable;
- normal empty long poll has HTTP deadline > server poll timeout;
- production `/` rejected without explicit production authority and accepted only in a fully intercepted temporary/mounted-path test seam;
- arbitrary source cannot be labelled an unrelated accepted SHA;
- dirty source and wrong tree rejected;
- staged release contains working `.venv/bin/codex-control`;
- missing executable blocks publication/switch;
- build failure leaves final release absent;
- repeated exact stage remains idempotent;
- actual DB schema is read, not assumed;
- wrong actual schema blocks switch/rollback;
- production upgrade command cannot omit preflight authority;
- no-health-probe does not become HEALTH_CONFIRMED;
- verification catches wrong installed Codex version;
- A->B health fail->A rollback preserves config/secrets/state;
- all production effects remain zero.

## 14. File scope

Continue using the existing P8.A allowed production/deployment/test/evidence surface only.

No P7 source/evidence/ledger changes. No roadmap/current-work edits by Codex. No migrations without architect decision. No live systemd/Telegram/Codex effects. No P8.B/P9.

## 15. Validation

Run focused Repair-1 tests, then complete safe unit/integration/acceptance and P0-P7 non-real regressions with real gates unset. Preserve immutable historical blockers.

Run compileall, `git diff --check`, secret/leakage scan, exact changed-path scope and temporary-root end-to-end install/upgrade/rollback rehearsal.

Where `systemd-analyze verify` is available, the repaired staged executable path must eliminate the previous missing-ExecStart warning when verified against a fully staged temporary release using an appropriate path-substitution/test unit; do not install the real unit.

## 16. Evidence flags

Update `docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md` and end with:

`P8A_REPAIR1_INSTALLED_CODEX_PREFLIGHT=PASS|FAIL`

`P8A_REPAIR1_SERVE_PREFLIGHT_ORDER=PASS|FAIL`

`P8A_REPAIR1_LONG_POLL_DEADLINE=PASS|FAIL`

`P8A_REPAIR1_PRODUCTION_ROOT_AUTHORITY=PASS|FAIL`

`P8A_REPAIR1_EXACT_SOURCE_SHA_BINDING=PASS|FAIL`

`P8A_REPAIR1_EXECUTABLE_RELEASE_BUILD=PASS|FAIL`

`P8A_REPAIR1_ATOMIC_STAGE_PUBLICATION=PASS|FAIL`

`P8A_REPAIR1_TRANSACTION_PREFLIGHT=PASS|FAIL`

`P8A_REPAIR1_HEALTH_STATE_AUTHORITY=PASS|FAIL`

`P8A_REPAIR1_TRUTHFUL_DEPLOYMENT_VERIFY=PASS|FAIL`

`P8A_REPAIR1_ROLLBACK_ACTUAL_SCHEMA_GATE=PASS|FAIL`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_PREP_READY=YES|NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

## 17. Publication

Use branch `impl-p8a-deployment-package-rollback-repair1-2026-09-13`, based exactly on candidate `c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de`.

No rebase. No force. Stop after remote readback for independent architect review. P8.B and P9 remain unauthorized.
