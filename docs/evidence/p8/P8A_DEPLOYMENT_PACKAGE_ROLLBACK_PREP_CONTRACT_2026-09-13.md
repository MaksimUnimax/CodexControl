# P8.A deployment package + rollback preparation contract — 2026-09-13

Status: **FROZEN / IMPLEMENTATION + OFFLINE ACCEPTANCE ONLY / ZERO PRODUCTION EFFECT / P9 NOT STARTED**

## Entry authority

P7 hard-delete correction is complete and architect accepted by:

`docs/evidence/p7c17/P7C17_FINAL_HARD_DELETE_REAL_ARCHITECT_ACCEPTANCE_2026-09-13.md`

P7.C17 accepted real evidence:

- evidence commit `cd793ffcc3afac6aaf83d14e1baba6599ecc25a9`;
- evidence blob `79271d70c52f5aa6239c21dbf65668321ff8490d`;
- accepted execution source `3da1817172f7f197276ec388c94e399fa0d31640`.

P7.C17/P7.C16/P7.C15/P7.C14/P7.C13 remain permanently non-retryable.

Roadmap next phase is P8 deployment packaging/rollback. P9 live Telegram acceptance must not start in P8.A.

## Why P8.A includes production assembly

The repository currently has accepted application orchestration but no deployable V1 process surface:

- no production `codex-control` console entrypoint;
- no `codex_control.__main__` / service lifecycle module;
- no concrete Telegram Bot API long-poll gateway;
- `pyproject.toml` defines no console script;
- `deploy/systemd` contains only a placeholder README.

P8.A must therefore materialize the smallest production assembly required for a valid deployment package while preserving all accepted P0–P7 application/storage/Codex semantics. This is not a redesign of those layers.

## Absolute production-effect boundary

During P8.A Codex MUST NOT:

- install anything under real `/etc/codex-control`, `/opt/codex-control`, `/var/lib/codex-control` or `/etc/systemd/system`;
- call `systemctl`, `service`, `daemon-reload`, `enable`, `start`, `stop`, `restart` or `reload` against the real host;
- write or alter a real production SQLite DB;
- mutate `/root/.codex*` homes;
- start installed Codex/app-server for a real profile;
- make real Telegram HTTP calls;
- use a live Telegram token;
- send/receive a live Telegram update;
- make real thread/turn/approval/delete RPCs;
- alter P7 ledgers/evidence/retained material;
- deploy to server-80;
- start P9.

All install/upgrade/rollback/service-lifecycle testing must use temporary roots, fake HTTP, fake Codex/runtime boundaries and temporary SQLite.

## Binding architecture/security

Obey in full:

- `AGENTS.md`;
- `docs/ARCHITECTURE_BASELINE.md`;
- `docs/PRODUCT_REQUIREMENTS.md`;
- `docs/ARCHITECTURE.md`;
- `docs/SECURITY_MODEL.md`;
- `docs/CONFIGURATION_CONTRACT.md`;
- `docs/DEVELOPMENT_GOVERNANCE.md`;
- `docs/ROADMAP.md`;
- `docs/CURRENT_WORK.md`;
- accepted P6.3 and P7.C17 architect acceptance evidence.

Production remains a root-equivalent Telegram administration channel. No inbound listener may be introduced.

## P8.A deliverable 1 — real executable surface

Add an explicit production console entrypoint:

`codex-control`

with at minimum:

- `validate` — performs startup/config/runtime-authority validation only; no polling and no external side effects;
- `serve` — runs the V1 controller lifecycle.

Add the console script through `pyproject.toml` and a production module under `src/codex_control/` or a dedicated `infrastructure/` package.

`python -m codex_control` may be supported as an exact equivalent but is not required if the console entrypoint is deterministic and tested.

Exit behavior must be finite and safe:

- validation success `0`;
- malformed/unsafe config, missing secret, unsafe storage/profile/runtime authority: nonzero with allowlisted safe category only;
- no raw token, environment dump, Codex exception text, prompt/response or Telegram update content in stderr/logging.

## P8.A deliverable 2 — production configuration closure

Bring executable configuration into agreement with the accepted configuration contract without breaking accepted P7 profile/isolation authority.

Production configuration must provide/validate at minimum:

- own `server_id` and `display_name`;
- exact operator user ID;
- exact control supergroup ID;
- fleet version and ordered server/display manifest;
- runtime state root;
- controller SQLite path or deterministic path under state root;
- working directory;
- Telegram text limit;
- explicit profiles with profile ID/display name/CODEX_HOME/isolated state root;
- repository root/protected-root authority required by accepted P7 storage containment.

Secrets are loaded separately from root-only secrets authority. At minimum the Telegram bot token must not be accepted from committed TOML/examples.

Production paths remain explicit; do not auto-discover `/root/.codex*` profiles.

## P8.A deliverable 3 — secrets authority

Production expected locations remain:

- `/etc/codex-control/server.toml` — root-owned non-secret configuration;
- `/etc/codex-control/secrets.env` — root-owned mode `0600` secrets.

Implement a bounded parser/loader for secrets that:

- requires the expected Telegram token key;
- rejects duplicate keys, NUL/newline injection and malformed assignments;
- does not accept shell execution/substitution semantics;
- never logs the secret value;
- validates root ownership/mode in production mode;
- supports explicit test-only temporary authority in offline tests.

Repository examples contain placeholders only and no working credential.

## P8.A deliverable 4 — concrete Telegram Bot API transport

Materialize the concrete outbound/long-poll transport required by the accepted Telegram/application interfaces.

It must support only the exact Bot API operations required by existing accepted P4–P6 behavior, derived from existing interfaces/tests. Do not invent new UX or commands.

Required transport properties:

- HTTPS Telegram Bot API only;
- no inbound webhook/listener;
- bounded connect/read/poll/request timeouts;
- long polling with explicit update offset progression;
- response JSON schema/type validation;
- Telegram/network errors normalized to safe allowlisted classes;
- token never appears in URL logs, exception messages, repr or evidence;
- test seam for deterministic fake HTTP with zero live network;
- no blind retry of ambiguous externally mutating Telegram sends/edits beyond already accepted delivery semantics.

Use the standard library or an explicitly declared minimal dependency only. Do not add a dependency merely for convenience if it broadens the trust/deployment surface without need. Any new dependency must be pinned/bounded by the package metadata and justified in evidence.

## P8.A deliverable 5 — production composition/lifecycle

Create a production assembly layer that composes the already accepted implementations rather than duplicating them.

It must wire at minimum:

- parsed V1 server/fleet/profile/runtime configuration;
- root-only secrets;
- schema-v4 SQLite storage/repositories;
- accepted `CodexRuntimeManager` with explicit profiles/isolation authority;
- accepted `LocalControllerOrchestrator` and its accepted P3–P6 dependencies;
- accepted Telegram group/private update adapters/renderers/delivery gateway;
- concrete Telegram transport;
- accepted startup recovery before ordinary polling;
- graceful shutdown of polling, active owned CodexControl runtimes and SQLite.

Startup must fail closed before Telegram polling or Codex effects if configuration/storage/runtime authority is invalid.

Every process start must force effective controller mode to `SLEEP` and require fresh operator activation, as accepted architecture requires.

Do not introduce a background prompt queue or a central coordinator.

## P8.A deliverable 6 — signal/service lifecycle

`serve` must have bounded, testable lifecycle handling for SIGTERM/SIGINT:

1. stop accepting/polling new updates;
2. stop dispatching new application work;
3. perform accepted bounded local shutdown/convergence only;
4. close owned CodexControl runtimes;
5. close SQLite;
6. exit finite.

Do not kill unrelated Codex processes sharing CODEX_HOME.

Do not perform hard-delete automatically on service shutdown.

## P8.A deliverable 7 — systemd unit

Create a production systemd unit template/source under `deploy/systemd/`.

Canonical service name:

`codex-control.service`

Required characteristics:

- runs as root because V1 root privilege is accepted architecture;
- no public network listener;
- deterministic exact executable path under the current release;
- explicit config and secrets paths;
- deterministic working directory;
- `Restart=on-failure` with bounded restart delay;
- `KillMode=control-group`;
- bounded stop timeout sufficient for graceful controller/runtime shutdown;
- journald receives only the application's redacted safe logs;
- no `Environment=` value containing the token in the unit file;
- `EnvironmentFile=/etc/codex-control/secrets.env` or an equivalently root-only secrets mechanism;
- no systemd hardening directive may make configured root-owned CODEX_HOME, `/var/lib/codex-control`, working directory or required local files inaccessible.

Do not install/enable/start this unit in P8.A.

## P8.A deliverable 8 — immutable release layout

Freeze the production release layout:

- `/opt/codex-control/releases/<FULL_GIT_SHA>/` — immutable code/venv/package release;
- `/opt/codex-control/current` — symlink to exactly one accepted release;
- `/etc/codex-control/` — configuration/secrets, not version-swapped with code;
- `/var/lib/codex-control/` — durable controller state/database, not version-swapped with code.

Production deployment must use an exact architect-accepted SHA. Never use blind `git pull` of a moving branch as the deploy mechanism.

P8.A must provide material/scripts capable of staging this layout under an explicit temporary root for tests.

## P8.A deliverable 9 — install/upgrade transaction

Provide deterministic deployment material/runbook implementing this future transaction:

1. preflight exact release SHA/package;
2. verify Python/Codex/runtime/config/secrets/state authority;
3. stage a new immutable release without modifying `current`;
4. build/install release environment;
5. run offline `codex-control validate` against target config/secrets/state authority;
6. preserve a record of the previous `current` release;
7. atomically switch `current` symlink;
8. future production prompt performs daemon-reload/restart;
9. post-start health gate must pass before deployment is accepted.

P8.A rehearses steps only inside temporary roots and fake systemd/process seams.

No real service change is authorized.

## P8.A deliverable 10 — rollback

Rollback must be executable and independently testable.

Rollback changes only executable release selection and service lifecycle. It MUST NOT roll back or delete:

- `/etc/codex-control/server.toml` automatically;
- `/etc/codex-control/secrets.env` automatically;
- `/var/lib/codex-control` DB/state automatically;
- any configured CODEX_HOME;
- P7 retained evidence/ledgers.

Rollback prerequisites:

- previous release exists and is validated;
- schema compatibility is explicitly checked before switching back;
- if previous binary cannot safely open current DB schema, rollback MUST fail closed rather than attempt destructive DB downgrade;
- `current` symlink switch is atomic;
- future service restart is separate and observable;
- rollback evidence records source/target release SHA and safe state classes only.

P8.A must test install -> upgrade -> failed health -> rollback and prove durable state/config/secrets survive byte-for-byte where expected.

## P8.A deliverable 11 — database/migration safety

Current controller schema authority is v4. P8.A does not create a new application schema unless deployment work proves one is absolutely required; that would require architect review.

Deployment validation must identify DB user_version and refuse unsupported forward/backward combinations.

Never copy or restore a SQLite file over a running controller.

No automatic downgrade migration is permitted.

## P8.A deliverable 12 — package/build reproducibility

The accepted SHA must be recoverable from installed release metadata without relying on Git metadata at runtime.

Include a build/release manifest containing at minimum:

- product name/version;
- exact Git SHA;
- Python requirement;
- expected installed Codex version/capability manifest identity;
- supported controller schema version;
- package artifact digest(s).

Do not include secrets, environment dumps or machine-specific thread/session IDs.

Build two times from the same source under the controlled test path and verify deterministic manifest authority; if wheel bytes are not reproducible due standard build timestamps, manifest/source/artifact digest semantics must be explicit and not falsely claim byte reproducibility.

## P8.A deliverable 13 — deployment verification command

Provide a zero-external-effect verification surface/runbook that can prove before production restart:

- executable release SHA;
- config/secrets ownership/mode classes;
- controller DB schema compatibility;
- explicit profiles/CODEX_HOME authority;
- installed Codex version/capability authority;
- service unit source digest;
- release manifest digest;
- `current` symlink points to expected immutable release.

It must not call Telegram or create a Codex thread/turn.

## P8.A tests

At minimum add/extend tests for:

### Configuration/secrets

- valid complete V1 config;
- missing operator/control/fleet/runtime/profile fields;
- duplicate fleet/profile labels/IDs;
- unsafe/relative/symlink/overlapping paths;
- missing/malformed/duplicate secret;
- wrong secrets mode/owner fixture where feasible;
- secret redaction.

### Telegram transport

- getUpdates offset progression;
- malformed/non-JSON/Telegram error normalization;
- bounded timeout handling;
- send/edit/callback exact request projection;
- ambiguous send/edit failure is surfaced, not blindly retried;
- token redaction in repr/errors/log fixtures;
- no real network.

### Production service assembly

- fail before poll on bad config/secrets/storage/runtime authority;
- boot effective SLEEP;
- startup recovery occurs before first ordinary update dispatch;
- exact group/private update projection through accepted orchestrator;
- graceful SIGTERM/SIGINT shutdown;
- no unrelated Codex process ownership;
- no prompt queue introduced.

### Packaging/install/rollback

- exact-SHA immutable release staging;
- `current` atomic switch;
- second install/idempotent preflight behavior;
- state/config/secrets preserved;
- failed validation prevents switch;
- simulated failed post-switch health triggers explicit rollback procedure;
- rollback to previous compatible release;
- incompatible schema rollback blocked;
- missing previous release blocked;
- symlink/path traversal attacks blocked;
- no writes outside temporary deployment root in tests.

### systemd

- unit parses expected directives;
- exact ExecStart/EnvironmentFile/WorkingDirectory authority;
- no token literal;
- root service identity;
- Restart/KillMode/TimeoutStopSec bounded policy;
- no public listener directive.

### regressions

Run all safe P0–P7 non-real suites. Historical consumed-latch failures are reported separately and never repaired/reset for P8.A.

## P8.A allowed tracked scope

Allowed production changes are limited to the deployment/runtime assembly surface needed by this contract, including:

- `src/codex_control/config.py`;
- new `src/codex_control/service.py` or a narrowly named infrastructure package;
- new `src/codex_control/__main__.py` if used;
- new concrete Telegram transport module(s) under `src/codex_control/adapters/telegram/` and minimal export edits;
- `pyproject.toml`;
- `config/examples/**` and/or the existing non-secret server example;
- `deploy/systemd/**`;
- a narrowly scoped `deploy/` install/rollback/verification helper surface;
- tests required for P8.A;
- `docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md`.

Do not modify accepted application/domain/storage/Codex semantics unless a directly demonstrated composition defect makes that unavoidable. If such a defect appears, stop that part and report `ARCHITECTURE_DECISION_REQUIRED` with evidence rather than silently broadening the patch.

Forbidden:

- P7 historical harness/evidence/ledgers;
- `docs/ROADMAP.md`, `docs/CURRENT_WORK.md` or other architect authority files;
- migrations unless separately authorized;
- live credentials;
- production filesystem/service mutation;
- P9 live Telegram acceptance.

## P8.A preparation evidence

Create:

`docs/evidence/p8/P8A_DEPLOYMENT_PACKAGE_ROLLBACK_PREP_EVIDENCE_2026-09-13.md`

Record exact base/head/tree, changed files, artifact/unit/manifest digests, tests, install/upgrade/rollback rehearsal results, redaction checks and zero-production-effect accounting.

End with:

`P8A_PRODUCTION_ENTRYPOINT=PASS|FAIL`

`P8A_CONFIGURATION_AND_SECRETS_AUTHORITY=PASS|FAIL`

`P8A_TELEGRAM_TRANSPORT_OFFLINE=PASS|FAIL`

`P8A_PRODUCTION_ASSEMBLY_OFFLINE=PASS|FAIL`

`P8A_SYSTEMD_PACKAGE=PASS|FAIL`

`P8A_IMMUTABLE_RELEASE_LAYOUT=PASS|FAIL`

`P8A_INSTALL_UPGRADE_REHEARSAL=PASS|FAIL`

`P8A_ROLLBACK_REHEARSAL=PASS|FAIL`

`P8A_SCHEMA_COMPATIBILITY_GATE=PASS|FAIL`

`P8A_RELEASE_MANIFEST=PASS|FAIL`

`P8A_SECRET_LEAKAGE_SCAN=PASS|FAIL`

`P8A_PRODUCTION_EFFECTS=0`

`P8A_PREP_READY=YES|NO`

`P8_REAL_DEPLOYMENT_AUTHORIZED=NO`

`P9_STARTED=NO`

## Publication

Implementation branch:

`impl-p8a-deployment-package-rollback-2026-09-13`

It must start from the exact architect main carrying this contract. Codex pushes but does not merge. No force push. After remote readback stop for independent architect review.

A later separate P8.B production deployment/rollback acceptance prompt is required after P8.A architect acceptance. P9 remains blocked until P8 deployment acceptance is complete.
