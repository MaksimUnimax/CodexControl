# P8.A deployment package + rollback preparation — architect review — 2026-09-13

Status: **REWORK_REQUIRED / CORE P8.A CONCEPTS ACCEPTED FOR REUSE / PRODUCTION-CLASS DEPLOYMENT GAPS REMAIN / P8.B NOT AUTHORIZED / P9 NOT STARTED**

## Binding candidate

- branch: `impl-p8a-deployment-package-rollback-2026-09-13`;
- candidate HEAD: `c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de`;
- candidate tree: `d78533eedee7495adb682ccbeab90eb374b9c808`;
- exact base: `6234a2fd8ff3cbb7f632558891065ac9d477bece`;
- base tree: `4d8595c70c635122ee3764161983bd0ea0d8195a`;
- candidate is four linear commits ahead, zero behind, merge-base exact base;
- only the 15 P8.A-authorized implementation/evidence paths changed.

## Accepted for reuse

Independent review accepts for reuse:

- the `codex-control validate|serve` CLI shape and console entrypoint;
- strict complete production configuration parsing as a separate path from the legacy parser;
- root-only non-shell secrets parsing/redaction;
- the narrow Telegram Bot API transport interface/fake HTTP seam and safe mutating-effect UNKNOWN projection;
- composition of accepted P3-P7 application/runtime/storage components rather than reimplementation;
- restart SLEEP and startup-recovery-before-poll intent;
- systemd unit shape: root service, external config/secrets, restart-on-failure, control-group kill and bounded stop;
- immutable release/current/config/state layout concept;
- release-manifest and schema-gated rollback concepts;
- temporary-root upgrade/rollback rehearsal and zero-production-effect boundary.

These pieces should be repaired, not redesigned.

## Blocking defects

### A. Installed Codex authority is not actually probed

`validate_production_authority()` checks that the configured executable exists and loads the bundled fixed capability manifest, but does not run the accepted installed `CodexVersionProbe` / `probe_supported_manifest` authority against the executable. `build_production_assembly()` does not call `validate_production_authority()` before opening storage and assembling the poller.

The accepted offline assembly test proves this gap by supplying a shell script that merely exits 0 as the configured Codex executable; assembly still succeeds.

Result: a host with the wrong installed Codex executable/version can reach service assembly and Telegram polling before fail-closed runtime capability validation.

### B. Long-poll HTTP deadline has no response margin

`TelegramBotApiTransport` defaults `poll_timeout=30`, calls `getUpdates` with Telegram timeout 30 and asks its HTTP seam for 35 seconds, but the default `UrlLibHttpClient` is constructed with a maximum timeout of 30 and clamps the requested 35 seconds back to 30.

A healthy empty long poll can therefore collide with the client deadline and be classified as `NETWORK_AMBIGUOUS` at the normal Telegram server timeout boundary.

### C. Deployment tooling cannot target the real host root

All deployment functions route through `_layout_root()`, which rejects `/`. The CLI requires `--root`, so the package can rehearse only an alternate root and cannot materialize the documented real layout `/opt/codex-control`, `/etc/codex-control`, `/var/lib/codex-control` during future P8.B.

Production-root use must require a separate explicit production-authorized mode while preserving the safe alternate-root default for tests.

### D. Exact Git SHA is only a label, not source authority

`stage_release(source, git_sha=...)` trusts the caller-provided SHA and copies arbitrary source bytes. It does not prove the source is the exact clean Git commit/tree represented by that SHA. A modified arbitrary directory can therefore be staged and later accepted by `validate_release()` under an architect-accepted SHA because the manifest hashes only the supplied directory.

Production staging must bind artifact source to the exact accepted commit/tree (for example via an exact Git archive/clean repository authority or an equivalently strong source-manifest authority) before publishing a release.

### E. Staged release is not executable by the systemd unit

`stage_release()` copies source and writes a manifest but does not create/install `.venv/bin/codex-control`. The systemd unit requires `/opt/codex-control/current/.venv/bin/codex-control`. The reported `systemd-analyze verify` missing-executable warning is therefore a real missing deployment deliverable, not merely a checkout peculiarity.

P8.A must build the immutable executable environment offline without network dependency during the deployment transaction, or freeze an equally deterministic executable layout and make the unit match it.

### F. Upgrade/switch do not enforce the frozen pre-switch transaction

The CLI `upgrade` accepts only root/source/SHA. It does not require production config, secrets, database or unit authority; does not run the staged release's `codex-control validate`; does not read the actual controller DB schema; and `install_upgrade()` treats missing `health_check` as healthy by default.

`switch`/`rollback` use caller/default `current_db_schema=4` rather than deriving the actual DB user_version from the deployment authority.

The future production transaction must not be able to switch `current` unless exact source/build, target release validation, config/secrets authority, actual DB schema compatibility and offline staged-executable validation have all passed.

A post-switch service-health phase remains a distinct P8.B action and must never default to success merely because no health probe was supplied.

### G. Deployment verification reports declared, not installed, Codex authority

`verify_installation()` returns the release manifest's expected Codex version as `codex_version_authority`; it does not probe the installed executable. This can report 0.144.6 when the host binary differs.

Verification must report actual bounded installed-Codex authority using the accepted probe and then compare it to the manifest/contract.

### H. Final release publication is not atomic

`stage_release()` copies directly into the final `releases/<sha>` directory. A mid-copy/build/manifest failure can leave a partial final release which then blocks deterministic restaging. Staging must occur in a private temporary sibling, fully build and validate there, then atomically publish the final immutable release; failed staging must not create a valid-looking final release.

## Architect verdict

`P8A_CORE_CONFIG_SECRETS_CONCEPT=ACCEPTED_FOR_REUSE`

`P8A_TELEGRAM_TRANSPORT_CONCEPT=ACCEPTED_FOR_REUSE`

`P8A_PRODUCTION_COMPOSITION_CONCEPT=ACCEPTED_FOR_REUSE`

`P8A_RELEASE_ROLLBACK_CONCEPT=ACCEPTED_FOR_REUSE`

`P8A_INSTALLED_RUNTIME_PREFLIGHT=REWORK_REQUIRED`

`P8A_TELEGRAM_LONG_POLL_DEADLINE=REWORK_REQUIRED`

`P8A_PRODUCTION_ROOT_DEPLOYMENT=REWORK_REQUIRED`

`P8A_EXACT_SOURCE_SHA_BINDING=REWORK_REQUIRED`

`P8A_EXECUTABLE_RELEASE_BUILD=REWORK_REQUIRED`

`P8A_TRANSACTION_PREFLIGHT_AND_HEALTH=REWORK_REQUIRED`

`P8A_DEPLOYMENT_VERIFICATION=REWORK_REQUIRED`

`P8A_ATOMIC_STAGE_PUBLISH=REWORK_REQUIRED`

`P8A_ARCHITECT_ACCEPTED=NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`
