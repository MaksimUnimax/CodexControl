# P8.A deployment package + rollback preparation Repair-1 — architect review — 2026-09-13

Status: **REWORK_REQUIRED / REPAIR-1 CONTRACT NOT SATISFIED / CORE P8.A WORK RETAINED / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Binding candidate

- reported candidate HEAD: `09214a2a0a0ce92a2847dda24c3512447c822f1c`;
- candidate tree: `56ac091de95ad809df9408a3da91fb4c00baa6f3`;
- Repair-1 base: `c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de`;
- Repair-1 base tree: `d78533eedee7495adb682ccbeab90eb374b9c808`;
- candidate is exactly two linear commits ahead of the Repair-1 base, zero behind, merge-base exact Repair-1 base;
- cumulative P8.A lineage remains six commits ahead of original P8.A base `6234a2fd8ff3cbb7f632558891065ac9d477bece`.

The candidate was published to `impl-p8a-deployment-package-rollback-2026-09-13`, not the frozen Repair-1 branch `impl-p8a-deployment-package-rollback-repair1-2026-09-13`. The frozen Repair-1 branch still points to the pre-repair candidate `c47a53d...`. This is a publication-authority defect, although the commit itself remains source-reviewable because its ancestry from the exact Repair-1 base is linear and unambiguous.

## Independent source review

Repair-1 does not satisfy the frozen Repair-1 contract. Several original blockers remain literally present in the final source and are also reflected in the retained tests.

### A. Installed Codex runtime authority remains unprobed

`validate_production_authority()` still checks executable presence and loads the bundled static capability manifest. It does not instantiate/use the accepted `CodexVersionProbe` / `probe_supported_manifest(...)` installed authority. `build_production_assembly()` performs the same static check. `serve()` simply calls assembly.

The acceptance fixture still supplies a fake `#!/bin/sh; exit 0` Codex executable and successfully builds the production assembly. Therefore wrong/malformed installed Codex can still pass service preflight and reach recovery/polling.

`P8A_REPAIR1_INSTALLED_CODEX_PREFLIGHT=FAIL`

`P8A_REPAIR1_SERVE_PREFLIGHT_ORDER=FAIL`

### B. Telegram long-poll deadline remains equal to server poll timeout

`TelegramBotApiTransport(poll_timeout=30)` creates the default `UrlLibHttpClient` with `timeout=max(request_timeout,poll_timeout)=30`. `get_updates()` requests `poll_timeout+5=35`, but `UrlLibHttpClient.request()` clamps with `min(timeout,self._timeout)`, reducing the actual HTTP deadline back to 30.

The required positive transport margin is therefore still absent.

`P8A_REPAIR1_LONG_POLL_DEADLINE=FAIL`

### C. Production-root deployment authority remains absent

`_layout_root()` still rejects `Path('/')` unconditionally. No explicit production-root authority mode exists. Future P8.B therefore still cannot materialize the documented real `/opt`, `/etc` and `/var/lib` layout using the deployment module.

`P8A_REPAIR1_PRODUCTION_ROOT_AUTHORITY=FAIL`

### D. Exact source SHA/tree binding remains label-only

`stage_release(source, git_sha=...)` still accepts an arbitrary directory, copies it, and writes the caller-provided SHA into the manifest. The manifest contains no source tree SHA and staging does not derive bytes from the exact Git object or verify clean exact repository authority.

The offline tests continue staging synthetic directories under invented repeated-character SHAs. Therefore exact-source-to-SHA authority is not proven.

`P8A_REPAIR1_EXACT_SOURCE_SHA_BINDING=FAIL`

### E. Published release remains non-executable for systemd

`stage_release()` still only copies source, writes a manifest and chmods files. It does not create `.venv/bin/codex-control` or an equivalent executable release surface. The systemd unit still requires `/opt/codex-control/current/.venv/bin/codex-control`.

`P8A_REPAIR1_EXECUTABLE_RELEASE_BUILD=FAIL`

### F. Staging is still non-atomic

`stage_release()` still calls `shutil.copytree(source_path, target, ...)` directly into final `releases/<sha>`. A copy/build/manifest failure can still leave a partial final release.

`P8A_REPAIR1_ATOMIC_STAGE_PUBLICATION=FAIL`

### G. Pre-switch transaction still trusts caller/default facts

`switch_current()` and `rollback()` still accept `current_db_schema=4` as a caller/default fact. `install_upgrade()` validates config/secrets only when optional arguments are supplied, can be invoked without them, and compares actual DB schema to the caller-supplied `current_db_schema` rather than deriving production authority end-to-end.

The CLI still permits weak switch/rollback surfaces, and no staged executable `codex-control validate` is required before switch.

`P8A_REPAIR1_TRANSACTION_PREFLIGHT=FAIL`

### H. Absence of health evidence still means success

`install_upgrade()` still computes `healthy=True if health_check is None else ...`. This directly violates the frozen requirement that missing health evidence must not project `HEALTH_CONFIRMED`.

`P8A_REPAIR1_HEALTH_STATE_AUTHORITY=FAIL`

### I. Deployment verification still reports declared Codex authority

`verify_installation()` still initializes `codex_version_authority` from `manifest.expected_codex_version`. It reuses the same static `validate_production_authority()` path, so it does not independently probe the installed Codex executable.

`P8A_REPAIR1_TRUTHFUL_DEPLOYMENT_VERIFY=FAIL`

### J. Rollback production schema authority remains caller-supplied

`rollback(root, current_db_schema=4)` does not derive the schema from the configured controller DB. Previous-release compatibility can therefore be evaluated against a caller default rather than actual production DB authority.

`P8A_REPAIR1_ROLLBACK_ACTUAL_SCHEMA_GATE=FAIL`

### K. Repair-1 evidence contract was not materialized

The final evidence file does not end with the required `P8A_REPAIR1_*` flags from the frozen Repair-1 contract. It retains the original P8.A flags and claims `P8A_PREP_READY=YES` despite the unresolved blockers above.

## Accepted for continued reuse

The following remain useful and should not be redesigned merely because Repair-1 failed:

- strict production config parsing and secret redaction;
- group/private routing correction;
- service shutdown ordering improvements;
- Telegram request/response validation improvements unrelated to the deadline defect;
- systemd unit shape;
- manifest type/key validation hardening;
- previous-release file replacement made more atomic;
- temporary-root rehearsal infrastructure;
- zero-production-effect boundary.

## Verdict

`P8A_REPAIR1_ARCHITECT_ACCEPTED=NO`

`P8A_REPAIR1_CONTRACT_SATISFIED=NO`

`P8A_PREP_READY=NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

P8.A Repair-2 is required. It must start from exact candidate `09214a2a0a0ce92a2847dda24c3512447c822f1c`, preserve accepted work, and actually close the production authority gaps rather than only hardening surrounding validation.