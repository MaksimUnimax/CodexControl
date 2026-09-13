# P8.A deployment package + rollback preparation evidence — 2026-09-13

Status: implementation and offline acceptance only. No production deployment,
real systemd mutation, live Telegram call, or real Codex acceptance was run.

## Authority and history

P8A_BASE_HEAD=6234a2fd8ff3cbb7f632558891065ac9d477bece

P8A_BASE_TREE=4d8595c70c635122ee3764161983bd0ea0d8195a

The implementation checkpoint before this evidence commit is:

P8A_IMPLEMENTATION_HEAD=109d9a39fc271af11c97fbd1c1d79375d6c678ab

P8A_IMPLEMENTATION_TREE=8536361679d1fdf36baa90adce7c9f541ce2c6c1

The branch is linear from the required base. P8.A commits, in order:

```text
9faff36993ebafe6c10115eacdc9173a10987584 Implement P8A offline production assembly and rollback package
fc5787e7d840924aece5e8d4c3fd1df8dd8cbe90 Record P8A offline deployment and rollback evidence
acb1c261735a89376e5f0e522b19fce1bf192a40 Keep offline polling loop alive across empty polls
c47a53dedb10ecd6d4494e86e1d2a8ad2f8349de Refresh P8A evidence for final offline lifecycle checks
109d9a39fc271af11c97fbd1c1d79375d6c678ab Harden P8A offline deployment and service authorities
```

## Changed paths

```text
config/examples/README.md
config/examples/server.toml
config/server-80.example.toml
deploy/codex_control_deploy.py
deploy/systemd/README.md
deploy/systemd/codex-control.service
docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md
pyproject.toml
src/codex_control/__main__.py
src/codex_control/adapters/telegram/__init__.py
src/codex_control/adapters/telegram/bot_api.py
src/codex_control/config.py
src/codex_control/deployment.py
src/codex_control/secrets.py
src/codex_control/service.py
tests/acceptance/test_p8a_deployment_offline.py
tests/unit/test_p8a_configuration_transport.py
```

P7 historical harnesses, ledgers, retained evidence, `docs/ROADMAP.md`, and
`docs/CURRENT_WORK.md` are unchanged.

## Deliverables

- `pyproject.toml` declares `codex-control = codex_control.__main__:main`.
  `validate` is finite static preflight; `serve` owns the assembled lifecycle.
- `config.py` strictly models the V1 server, operator, control chat, ordered
  fleet, runtime, controller DB, repository/protected roots, and explicit
  profile/CODEX_HOME/isolation authorities. No profile discovery is used.
- `secrets.py` is a bounded non-shell parser. It rejects duplicates,
  malformed/unsafe assignments, NUL/control injection and unexpected keys;
  production files require root ownership and mode 0600. Secret repr/errors
  are redacted.
- `bot_api.py` provides HTTPS Bot API polling, monotonic offsets, validated
  JSON/result shapes, send/edit/callback projection, bounded timeouts and
  normalized safe errors. `HttpClient` is injectable; all tests use fake HTTP.
  Ambiguous mutating failures are surfaced as UNKNOWN with no blind retry.
- `service.py` composes schema-v4 SQLite, explicit isolation, accepted runtime,
  model/thread/turn/approval/recovery/orchestration/delivery components and
  group/private adapters/renderers. Startup forces effective SLEEP and awaits
  recovery before the first poll. Private updates are routed privately.
  Shutdown stops ingress/polling, closes owned runtimes, then SQLite.
- `deploy/systemd/codex-control.service` is uninstalled source material with
  root identity, current-release executable, external config/secrets/state,
  restart-on-failure, control-group shutdown and bounded timeout. No unit
  activation or systemd mutation occurred.
- `deployment.py` and `deploy/codex_control_deploy.py` provide explicit-root
  exact-SHA immutable staging, manifest authority, atomic `current` switching,
  prechecks, health-gated upgrade, schema-gated rollback, path/symlink checks,
  idempotent restaging and zero-effect verification.

## Digests and manifest authority

```text
systemd unit sha256 = 7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870
deployment helper sha256 = 0ee75a9603fdd5d7e7f8fc162d33fb24208514e8e6ffeb66dad39b2d0a2e00ff
deployment module sha256 = ddf0736e2e032d7ac10923d77835a552ab15f08ad59f58c795d14bac20224787
service module sha256 = 576742af6b29be424b62dcb8237660656d9d696e1345378e21e4d059c48607b0
Telegram transport sha256 = d0c155211542fce57200ab63d2bfe7d98c52d5a1f7df2470a9a881dbedab60e4
secrets module sha256 = 6556a0b8e062ff479feedfb055bff1ff0839dcf81611e5ed1a951a949af29c2f
```

The final handoff command is the authority for all listed file digests. The
release manifest contains product,
package version, exact supplied Git SHA, Python requirement, Codex 0.144.6
capability-schema SHA, controller schema 4, artifact digests, and optional
service-unit digest. It excludes tokens, cookies, IDs, prompts and environment
data. Manifest/source authority is deterministic; wheel-byte reproducibility
is not claimed.

## Tests and validation

```text
PYTHONPATH=.:src pytest -q tests/unit/test_p8a_configuration_transport.py tests/acceptance/test_p8a_deployment_offline.py
14 passed

PYTHONPATH=.:src pytest -q --ignore=tests/real
1079 passed, 647 subtests passed, 2 warnings

python -m compileall -q src tests
git diff --check
```

The focused matrix covers complete/missing/duplicate/overlap/control-character
configuration, secret duplicate/malformed/shell-like/unknown-key cases,
redacted errors/repr, polling/order/offset/timeout/result errors, send/edit/
callback projection and no retry, private-vs-group routing, SLEEP boot,
startup recovery ordering, temporary SQLite, exact-SHA manifests, atomic
switching, schema refusal, health failure rollback, preserved state/config/
secrets, idempotent restage and path/symlink attacks. The broad run is the
safe P0–P7 non-real regression set. P7 real tests were deliberately not run.

## Systemd verification

Deterministic assertions passed for service name, `User=root`, exact
`/opt/codex-control/current/.venv/bin/codex-control` strategy, config path,
root-only `EnvironmentFile`, working directory, `Restart=on-failure`, bounded
`RestartSec=5s`/`TimeoutStopSec=30s`, `KillMode=control-group`, no token
literal, no webhook/listener, and no unsafe shell interpolation.

`systemd-analyze verify` was run read-only against the source/temp-root unit;
the source-only invocation reports the expected absent future executable, and
the temp-root invocation reports only the absent boot target in the isolated
root. No `systemctl`, `service`, daemon-reload, install, enable, start, stop,
restart or reload was called.

## Temporary-root install/upgrade/rollback rehearsal

The rehearsal used a newly-created temporary root and temporary A/B artifacts:

1. staged A and atomically selected A;
2. validated A's manifest and recovered its exact supplied SHA;
3. staged B and validated its manifest;
4. atomically selected B;
5. returned `healthy=False` from the simulated post-switch health gate;
6. explicitly rolled back to compatible A and verified `current=A`;
7. preserved config, secret and v4 SQLite bytes in the pytest fixture;
8. rejected schema mismatch, missing/invalid previous release, traversal and
   symlink authorities, with all writes confined to the explicit temp root.

The direct rehearsal recovered manifest SHA-256 values:

```text
manifest A = a8dab05c93e46a09f1b57d466ea652b37cf3291ccc6816ee6d3e8106059dc8c1
manifest B = e3da30ddac61b8d2744a1fb7a3db6f98499d6ea890893ccf0e0ea93c1405c713
result = healthy:false, rolled_back:true, current:A
```

Rehearsal result: PASS.

## Secret/leakage scan

Tracked implementation/deployment paths were scanned for Telegram-like bot
tokens, private-key material, auth/cookie headers, shell secret evaluation,
environment dumps and prompt/response fixture leakage. No live credential or
private key was found. The only token assignments are explicit offline test
fixtures. No token, cookie, conversation content or environment dump is in
the release manifest, unit or deployment output. Secret scan: PASS.

## Historical immutable blockers

P7.C13, P7.C14, P7.C15, P7.C16 and P7.C17 remain consumed immutable one-shot
authorities and permanently non-retryable. Their ledgers/evidence/retained
material were not read for mutation, reset, deleted or rerun. This is reported
separately from P8.A tests.

## Zero-production-effect accounting

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

P8A_PRODUCTION_ENTRYPOINT=PASS

P8A_CONFIGURATION_AND_SECRETS_AUTHORITY=PASS

P8A_TELEGRAM_TRANSPORT_OFFLINE=PASS

P8A_PRODUCTION_ASSEMBLY_OFFLINE=PASS

P8A_SYSTEMD_PACKAGE=PASS

P8A_IMMUTABLE_RELEASE_LAYOUT=PASS

P8A_INSTALL_UPGRADE_REHEARSAL=PASS

P8A_ROLLBACK_REHEARSAL=PASS

P8A_SCHEMA_COMPATIBILITY_GATE=PASS

P8A_RELEASE_MANIFEST=PASS

P8A_SECRET_LEAKAGE_SCAN=PASS

P8A_PRODUCTION_EFFECTS=0

P8A_PREP_READY=YES

P8_REAL_DEPLOYMENT_AUTHORIZED=NO

P9_STARTED=NO
