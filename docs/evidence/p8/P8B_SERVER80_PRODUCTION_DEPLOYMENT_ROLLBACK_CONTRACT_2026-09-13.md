# P8.B server-80 production deployment + rollback acceptance contract — 2026-09-13

Status: **FROZEN / REAL PRODUCTION FILESYSTEM + SYSTEMD INSTALL AUTHORIZED / SERVICE MUST REMAIN STOPPED / NO TELEGRAM TRAFFIC / NO CODEX APP-SERVER RPC / P9 NOT STARTED**

## 1. Exact accepted release authority

Final operational release B MUST be exact Git commit:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

with tree:

`8def3b3e8591e82f77f0cea8c5f9f690949979f5`

Accepted final production-code checkpoint A for real rollback acceptance only:

`6ffd5193962115d6e07114369e4d442ea25c34d1`

with tree:

`0c16a336f70008461daa002e0f4af87f7ca70656`

A and B contain the same accepted production implementation; B adds only later P8.A evidence commits. A is authorized only as the temporary immediately-previous release used to prove real production rollback. The final operational `current` MUST be B.

Source repository:

`/root/CodexControl`

Repository remote:

`MaksimUnimax/CodexControl`

## 2. P8.B boundary

P8.B authorizes real server-80 mutations only for:

- `/opt/codex-control/releases/...` and `/opt/codex-control/current|previous|pending` deployment authority;
- `/etc/codex-control/server.toml`;
- `/etc/codex-control/secrets.env` only from an already owner-supplied local secret authority;
- `/var/lib/codex-control` controller state;
- configured P8.A isolated state roots under `/var/lib`;
- `/etc/systemd/system/codex-control.service`;
- `systemctl daemon-reload` and read-only systemd inspection.

P8.B DOES NOT authorize:

- starting/restarting `codex-control.service`;
- enabling the service for boot;
- any Telegram HTTP request;
- any Telegram send/edit/callback effect;
- any Codex app-server start;
- `model/list`, thread, turn, approval, interrupt, delete/read/list RPC;
- any P7 real-run retry or ledger mutation;
- P9.

The service must remain `inactive` and `disabled` throughout P8.B. The first live service start/poll belongs to P9.

## 3. Owner-specific config and secret stop gates

The repository example values `operator_user_id=123456789` and `control_chat_id=-1001234567890` are placeholders and MUST NEVER be deployed.

Before the first production mutation, resolve a pre-existing owner-approved local authority for the real:

- `operator_user_id`;
- `control_chat_id`;
- Telegram bot token.

Allowed authorities are an already-existing root-owned production config/secret file or another explicit local owner-provided secret/config artifact whose provenance is recorded without printing its contents.

If real routing IDs cannot be resolved, stop before production mutation with:

`P8B_BLOCKED_OWNER_ROUTING_AUTHORITY_REQUIRED`

If the bot token cannot be resolved without inventing/copying from logs/history, stop before production mutation with:

`P8B_BLOCKED_OWNER_SECRET_AUTHORITY_REQUIRED`

Never print, commit, hash-as-a-secret-substitute, or expose the plaintext token.

## 4. Exact preflight before production mutation

Require:

- current repository has fetched commits A and B;
- `git cat-file -e <sha>^{commit}` and exact tree checks pass for A/B;
- `/usr/bin/python` is accepted CPython 3.12.3 authority where still required by project baseline;
- `/usr/local/bin/codex --version` is exactly `codex-cli 0.144.6`;
- accepted generated schema aggregate SHA-256 is `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- expected explicit persistent CODEX_HOME roots exist and are root-owned/private before including them in production config;
- no unrecognized existing `codex-control.service` is active;
- no existing deployment/state/config authority is overwritten without bounded readback and rollback-safe classification.

If an existing production-like CodexControl deployment is discovered, do not blindly replace it. Record safe metadata and either prove it is this accepted lineage or stop for architect review.

## 5. Explicit profile authority

Do not auto-discover profiles.

Expected V1 server-80 profile authority from the accepted P8.A configuration surface is:

- `codex1` -> `/root/.codex` -> `/var/lib/codex-control-profile-codex1`;
- `codex2` -> `/root/.codex_second` -> `/var/lib/codex-control-profile-codex2`;
- `codex3` -> `/root/.codex_third` -> `/var/lib/codex-control-profile-codex3`.

Before writing production config, require every configured CODEX_HOME actually exists as the expected private root-owned directory. Do not create an authenticated CODEX_HOME and do not invent a profile.

If an expected accepted profile is absent or authority conflicts, stop for architect review rather than silently changing the profile set.

## 6. Production configuration

Create `/etc/codex-control` root-owned and private.

Materialize `/etc/codex-control/server.toml` with actual owner routing IDs and exact values:

- `server_id="server-80"`;
- `display_name="SERVER-80"`;
- `fleet_version="v1"`;
- one fleet member server-80;
- `state_root="/var/lib/codex-control"`;
- `working_directory="/root"`;
- `repository_root="/opt/codex-control/releases/1273b273ed7f58ba235b35cbce485b623c340b8d"`;
- `telegram_text_limit=3800`;
- `controller_db_path="/var/lib/codex-control/controller.sqlite3"`;
- `controller_db_root="/var/lib/codex-control"`;
- `codex_executable="/usr/local/bin/codex"`;
- expected Codex version `0.144.6` where schema accepts it;
- the explicit accepted profiles above.

Use mode 0600 or no-weaker root-owned non-group/world-writable mode.

Materialize `/etc/codex-control/secrets.env` from the already owner-provided secret authority only. It must contain exactly the accepted secret key surface and be root-owned mode 0600. Do not use shell `source`/`eval` to parse it.

## 7. Production directories

Create only the accepted deployment/state paths with root ownership and private/safe modes:

- `/opt/codex-control/releases`;
- `/var/lib/codex-control`;
- `/var/lib/codex-control-profile-codex1`;
- `/var/lib/codex-control-profile-codex2`;
- `/var/lib/codex-control-profile-codex3`.

Do not alter authenticated persistent CODEX_HOME contents.

## 8. Exact release staging

Use the accepted P8.A production deployment APIs / helper against explicit production-root authority. No moving branch checkout may become release identity.

Stage both exact releases A and B from Git object authority under:

`/opt/codex-control/releases/<FULL_SHA>`

Each must prove:

- exact source commit and tree;
- private stage before publication;
- release-local `.venv/bin/codex-control` regular executable;
- manifest/artifact digest validation;
- systemd-unit digest authority;
- no network package download.

Do not switch current until config, secrets, DB and installed-Codex authority exist.

## 9. Explicit controller DB initialization

If `/var/lib/codex-control/controller.sqlite3` is absent, initialize it exactly once through the accepted `initialize_controller_state` authority using production config/secrets and real installed-Codex preflight.

Require readback:

`PRAGMA user_version = 4`

If a DB already exists, never recreate/overwrite it. Validate it read-only and require schema v4; otherwise stop.

No P7 retained DB/ledger is to be imported or reset.

## 10. Real rollback acceptance while service is stopped

The service MUST be inactive before the first switch and remain inactive.

Execute real production-shaped deployment sequence:

1. switch/install A as current using full config/secrets/actual DB/installed-Codex preflight;
2. verify current=A, manifest/tree/executable/config/secrets/schema/Codex authority;
3. deploy B through the same production transaction;
4. require result `SWITCHED_AWAITING_SERVICE_HEALTH` because P8.B supplies no service-health success;
5. verify current=B and immediate previous=A;
6. execute production rollback using actual DB schema authority;
7. verify current=A and previous/current journal is consistent;
8. deploy B again through the production transaction;
9. verify final current=B and previous=A.

No service-health callback may be forged as PASS. The service remains stopped, so the accepted P8.A state `SWITCHED_AWAITING_SERVICE_HEALTH` is expected and not a deployment failure for P8.B.

## 11. Systemd install without start

Install exact accepted unit source as:

`/etc/systemd/system/codex-control.service`

Require unit digest:

`7df63042b9fcf9763c33cff980c9e4c3fadb25cef3d96c6dbe97532d3ad10870`

Set root ownership and normal unit-file mode.

Run:

- `systemd-analyze verify` where supported;
- `systemctl daemon-reload`;
- read-only `systemctl show/status/is-enabled/is-active` checks.

DO NOT run start/restart/enable.

Final required systemd state:

- unit loaded;
- `is-active` = inactive;
- `is-enabled` = disabled (or equivalent not-enabled state);
- no process belonging to CodexControl service.

If the unit was unexpectedly already active, stop before altering it unless exact accepted-lineage authority and explicit contract-safe convergence can be proven.

## 12. No live external effects

P8.B requires:

- Telegram HTTP calls = 0;
- Telegram messages = 0;
- Codex app-server starts = 0;
- Codex RPC calls = 0;
- P7 ledger mutations = 0.

A bounded local `/usr/local/bin/codex --version` subprocess is allowed and is not an app-server start.

## 13. Production verification

Run accepted production `codex-control validate` from final release B against real config/secrets while service is stopped.

Run accepted deployment verification against production root and require:

- installed release SHA = B;
- source tree = B tree;
- manifest valid;
- release executable valid;
- actual installed Codex = 0.144.6;
- accepted capability schema matches;
- controller DB schema=4;
- explicit profile/CODEX_HOME authority matches config;
- service unit digest exact;
- config/secrets authority valid.

No Telegram or app-server effect may be triggered by validation.

## 14. Evidence

Create only sanitized production evidence:

`docs/evidence/p8/P8B_SERVER80_PRODUCTION_DEPLOYMENT_ROLLBACK_EVIDENCE_2026-09-13.md`

Record:

- execution source branch/head/tree;
- architect contract authority;
- safe pre-existing deployment state classification;
- resolved routing authority PRESENT/ABSENT but not secret token;
- profile authority classes;
- exact A/B source/tree/manifests;
- config/secrets ownership/mode classes;
- DB initialization/existing classification and schema;
- A→B→A→B switch/rollback results;
- pending/previous journal safe classes;
- final current=B;
- systemd unit digest and inactive/disabled status;
- exact validation results;
- zero Telegram/Codex/P7 effects.

Do not include plaintext token, raw Telegram update/chat contents, Codex auth, cookies, prompts, thread/turn IDs or environment dump.

## 15. Evidence branch

Use evidence branch:

`real-p8b-server80-deployment-2026-09-13`

created from exact accepted final P8.A HEAD B:

`1273b273ed7f58ba235b35cbce485b623c340b8d`

After production actions, commit only the sanitized P8.B evidence file to that branch and push without force.

## 16. Required final flags

Successful P8.B evidence ends with:

`P8B_RELEASE_A_ROLLBACK_BASE=6ffd5193962115d6e07114369e4d442ea25c34d1`

`P8B_FINAL_RELEASE=1273b273ed7f58ba235b35cbce485b623c340b8d`

`P8B_CONTROLLER_SCHEMA=4`

`P8B_REAL_ROLLBACK_ACCEPTANCE=PASS`

`P8B_FINAL_CURRENT_RELEASE=1273b273ed7f58ba235b35cbce485b623c340b8d`

`P8B_SYSTEMD_UNIT_INSTALLED=YES`

`P8B_SERVICE_ACTIVE=NO`

`P8B_SERVICE_ENABLED=NO`

`P8B_TELEGRAM_HTTP_CALLS=0`

`P8B_TELEGRAM_MESSAGES=0`

`P8B_CODEX_APP_SERVER_STARTS=0`

`P8B_CODEX_RPC_CALLS=0`

`P8B_P7_LEDGER_MUTATIONS=0`

`P8B_FINAL_VERDICT=PASS`

`P9_STARTED=NO`

If owner routing/secret/profile authority is unavailable, produce a sanitized blocked preflight report only if no production mutation occurred, and stop. Do not improvise missing production identity.

## 17. P9 boundary

P8.B success does not start P9 automatically.

P9 requires a separate architect contract for first service start, Telegram polling, operator authentication, user-visible routing/delivery/approval/interrupt/delete and restart/recovery acceptance.
