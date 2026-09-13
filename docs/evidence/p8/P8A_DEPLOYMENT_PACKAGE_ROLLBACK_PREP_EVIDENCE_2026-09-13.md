# P8.A deployment package + rollback preparation evidence — 2026-09-13

Status: implementation and offline acceptance only. No production deployment,
systemd mutation, Telegram network call, or real Codex acceptance was run.

## Source authority

P8A_BASE_HEAD=6234a2fd8ff3cbb7f632558891065ac9d477bece

P8A_BASE_TREE=4d8595c70c635122ee3764161983bd0ea0d8195a

The implementation commit immediately above that base is:

P8A_IMPLEMENTATION_HEAD=acb1c261735a89376e5f0e522b19fce1bf192a40

P8A_IMPLEMENTATION_TREE=0b1f08b5c41ecd4a4ba97b27679f775d1be4e7a5

The evidence refresh is a linear commit after the implementation above. The
final branch hash/tree are recorded in the handoff report because this file
cannot contain its own future Git object identity.

The implementation history is linear from the required base; no merge,
rebase, squash, force push, or main mutation was used.

## Changed paths

```text
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

No P7 historical file, P7 ledger/evidence, `docs/ROADMAP.md`, or
`docs/CURRENT_WORK.md` was changed.

## Deliverables

- `pyproject.toml` declares `codex-control = codex_control.__main__:main`.
  `validate` performs finite static preflight; `serve` performs the accepted
  assembly and lifecycle.
- `config.py` provides strict complete V1 production loading with explicit
  server/operator/control/fleet/runtime/profile/protected-path authority.
  Legacy `parse_server_configuration` remains for frozen foundation callers;
  production loading does not use it or discover profiles.
- `secrets.py` parses bounded `KEY=value` data without shell evaluation,
  rejects duplicates/injection/unsafe syntax, and redacts the token from
  representation/errors. Production files require root ownership and 0600.
- `bot_api.py` provides HTTPS Bot API long polling, offset progression,
  send/edit/callback operations, response validation, bounded timeouts,
  safe categories, and an injectable `HttpResponse` fake boundary. Mutating
  ambiguous outcomes return UNKNOWN and are never blindly retried.
- `service.py` composes schema-v4 SQLite, explicit isolation authority,
  `CodexRuntimeManager`, model/thread/turn adapters, accepted local
  orchestrator, group/private adapters/renderers, delivery, approval,
  recovery, polling, SLEEP boot, and bounded owned-runtime/database shutdown.
  Recovery is awaited before the first `getUpdates` call.
- `deploy/systemd/codex-control.service` is root-only source material with
  deterministic current-release `ExecStart`, external config/secrets/state,
  restart-on-failure, control-group shutdown, and bounded stop timeout. It
  was not installed or activated.
- `deployment.py` and `deploy/codex_control_deploy.py` implement explicit
  alternate-root immutable exact-SHA staging, manifest validation, atomic
  current switching, upgrade health gating, rollback, schema compatibility,
  path/symlink controls, and zero-effect verification.

## Digests and release authority

```text
systemd unit sha256 = 7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870
deployment helper sha256 = fd94b93fd626c33c7347dd2c27253c747f7a05f7e059b9073f8664fdefe70b00
deployment module sha256 = 805c643fc9fc0ed7ba76cca3a06325be13f03aa44a2c49c5c9d92245ed6f9d4b
service module sha256 = 2259d7ad74323a8a190874e3541052f4468f1f9cf6a2180244f50d3876eff6b0
Telegram transport sha256 = 1e423dafc3697f04d3ac0b70bbb41f51b6d9c5949823e4f95e500ca9408ef0d2
secrets module sha256 = cb5be9fa8929b997f88380515ff4a2ebab5f0393c9cee3d457a79e8bc045c6a7
```

The controlled temporary-root manifest rehearsal recovered the accepted
implementation SHA `acb1c261735a89376e5f0e522b19fce1bf192a40` without Git
metadata. Its manifest SHA-256 was
`10e89edabb6620638d42cf9de8bd88bb6a1c66e7a7ff0889b9b9587e0d0d3f47`, with
schema support 4 and the fixed Codex 0.144.6 capability-schema authority.
Manifest determinism/source authority is asserted; wheel-byte
reproducibility is not claimed.

## Acceptance and regression commands

```text
PYTHONPATH=src:. pytest -q tests/unit/test_p8a_configuration_transport.py tests/acceptance/test_p8a_deployment_offline.py tests/test_foundation.py
14 passed

PYTHONPATH=src:. pytest -q tests/unit tests/integration tests/acceptance --ignore=tests/real
1071 passed, 647 subtests passed, 2 pre-existing warnings

python -m compileall -q src tests
git diff --check
```

Focused P8.A coverage includes the required valid/missing/duplicate/unsafe
config and secret cases, safe repr/error checks, polling/result/error/offset
transport cases, exact send/edit/callback projections, no blind retry,
offline SLEEP boot and recovery ordering, temporary SQLite, exact-SHA
manifest/staging/current switching, pre-switch failure, idempotent restage,
health-failure rollback, unchanged config/secrets/state, schema refusal,
symlink/path traversal blocking, and outside-root protection.

## Systemd verification

The unit was checked by deterministic parser assertions for service name,
root identity, exact current-release executable strategy, config,
EnvironmentFile, working directory, restart policy, bounded RestartSec and
TimeoutStopSec, control-group kill mode, no listener, no token literal, and
no shell interpolation. `systemd-analyze verify` was run read-only against
the uninstalled source unit; it reported only that the future
`/opt/codex-control/current/.venv/bin/codex-control` executable is not present
in this P8.A checkout. No `systemctl`, `service`, daemon-reload, install,
enable, start, stop, restart, or reload was called.

## Temporary-root install/upgrade/rollback rehearsal

The end-to-end rehearsal used a newly created `/tmp/p8a-final-rehearsal-*`
root, temporary A/B release sources, temporary config/secrets, and a
temporary SQLite file with `user_version=4`:

1. release A staged and current atomically switched to A;
2. release A manifest validated and exact accepted SHA recovered;
3. release B staged and switched after manifest/schema validation;
4. simulated B health returned false;
5. explicit rollback selected compatible A and atomically switched current to A;
6. config, secrets, and state SHA-256 values remained byte-for-byte equal;
7. no write escaped the temporary root.

Rehearsal result: PASS. Missing previous release, invalid manifest,
incompatible schema, current target traversal, release traversal, symlink,
outside-root, and same-release behavior were tested or rejected by the helper.

## Secret/leakage scan

Scanned all 14 implementation paths against Telegram-like token, private-key,
auth/cookie, and environment-dump patterns: zero findings. Offline test
authorities are explicit temporary fixtures, not working credentials. No
token, cookie, prompt, response, update payload, or environment dump is in
the release manifest, service unit, helper output, or this evidence.

## Historical immutable blockers

P7.C13, P7.C14, P7.C15, P7.C16, and P7.C17 are consumed immutable one-shot
authorities and remain non-retryable. P7 real tests were not discovered or
run; no latch, ledger, or retained evidence was altered. This is a required
historical separation, not a P8.A implementation failure.

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
