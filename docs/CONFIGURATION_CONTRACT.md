# Configuration contract — V1

Configuration is explicit and split between non-secret declarative data and root-only secrets.

## Deployment files
- `/etc/codex-control/server.toml`: server/controller/fleet/profile/runtime configuration, root-owned.
- `/etc/codex-control/secrets.env`: Telegram token/future secrets, root 0600.
- repository `config/examples/**`: non-secret examples only.

## Conceptual server config
```toml
[server]
server_id = "server-80"
display_name = "SERVER-80"
control_chat_id = -100123
operator_user_id = 123
fleet_version = "v1"

[runtime]
state_root = "/var/lib/codex-control"
working_directory = "/root"
telegram_text_limit = 3800

[[profiles]]
profile_id = "codex1"
display_name = "Codex account 1"
codex_home = "/root/.codex"
```
Token is never in Git example TOML.

## Fleet manifest
Every controller receives the same ordered non-secret list of server IDs/display labels used for persistent keyboard. Display activation labels are unique. Parser reserves activation prefix; unknown target is control and sleeps non-target controller, never prompt.

## Startup validation
Fail before polling when own server missing from fleet, IDs/display duplicate/invalid, profile IDs duplicate, CODEX_HOME unsafe/nonabsolute/missing, operator/control IDs missing, state paths unsafe, token missing, or security-sensitive config malformed. Do not auto-discover `/root/.codex*` as production profiles.

## Defaults
Profile/model/reasoning defaults are durable settings; config provides initial fallback/policy only. Runtime model/effort selection still requires authenticated validation.

## Root profile policy
V1 expects root-owned existing homes. Dedicated/non-root controller homes require explicit future ADR/migration, never automatic inference.
