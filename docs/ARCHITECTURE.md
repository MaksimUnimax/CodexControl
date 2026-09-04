# Architecture — V1

## System topology
```text
Private supergroup CODEX CONTROL
   | human controls + prompts
   +----------------------+-------------------+ ...
   v                      v
server-80 bot          server-78 bot
root controller        root controller
   | Telegram poller       |
   | local SQLite          | local SQLite
   | application layer     |
   v                       v
CodexRuntimeManager   CodexRuntimeManager
   | stdio children         | stdio children
   v                        v
explicit CODEX_HOME profiles
```
Controllers share semantics/config, not a mandatory runtime RPC/database.

## Per-server process
One systemd-managed Python process owns Telegram long polling, serialized control-chat ingress, private callbacks, local SQLite, application state machines, profile-keyed Codex app-server children over stdio, delivery and retention. No inbound TCP listener is required.

## Target layering
```text
codex_control.domain         immutable IDs/value objects/states/errors
codex_control.application    routing/settings/dialogue/turn/approval/delivery/recovery/retention
codex_control.ports          StateRepository, CodexAdapter, TelegramGateway, Clock, IdGenerator
codex_control.adapters.codex stdio process/JSON-RPC/models/thread/turn/approval mapping
codex_control.adapters.telegram auth/group router/private UI/render/delivery
codex_control.adapters.persistence SQLite schema/repositories
codex_control.infrastructure config/logging/process/service lifecycle
```
Domain/application must not depend on Telegram or Codex concrete types.

## Fleet routing without coordinator
Group selection uses persistent ReplyKeyboardMarkup because a button press becomes a human-user message observable by all bots. Each controller parses control before prompt routing.

For authorized group message M:
- activation label for self -> ACTIVE with control epoch M;
- activation-looking label for another or unknown server -> SLEEP with epoch M;
- all-sleep -> SLEEP;
- status -> local status only;
- ordinary text -> eligible only when ACTIVE and state permits.

Activation prefix is reserved even across fleet-version mismatch, so an old controller sleeps rather than sending a new server button text to Codex. Control chat processing is sequential; stale lower/equal epochs cannot override newer state.

## Restart fail-closed
Every process start sets effective mode SLEEP. Historical persisted ACTIVE is diagnostics only. A fresh human activation is required after restart/redeploy.

## Dialogue/selection
One live dialogue max. It binds server/profile/CODEX_HOME/thread. Profile is immutable. To use another account, delete current dialogue first.

Model/reasoning are next-turn settings for the same bound profile. They may change only while idle and after authenticated runtime validation. TurnExecutionSnapshot captures their values before Codex invocation.

No dialogue + accepted prompt -> durable create intent -> thread/start -> persist exact binding -> turn/start. Ambiguous thread creation is reconciled, never repeated blindly.

## Codex app-server lifecycle
Primary transport is child stdio. RuntimeManager is keyed by profile; at most one CodexControl child per profile. It sets exact CODEX_HOME, performs initialize/initialized handshake and capability probe. Active-dialogue child may stay alive; other profiles may use short-lived model-list children. Child crash after possible side effect enters reconciliation/UNKNOWN.

Existing non-CodexControl processes using the same CODEX_HOME are an environmental risk; controller never edits their internal state to resolve it.

## Root privilege
V1 intentionally runs controller/Codex as root: existing profiles are root-owned and product purpose is root-level service maintenance. A sudo-enabled non-root user preserves nearly the same power with more migration complexity. Therefore Telegram/operator/token boundary is a root-equivalent trust boundary; exact auth, no inbound listener, one-time destructive callbacks, approvals and root-only secrets are mandatory.

## Turn execution
`authorized ACTIVE text -> durable ingress -> immutable snapshot/claim -> turn/start -> normalized events -> terminal Codex result -> durable Telegram delivery -> metadata finalization/transient purge`.

Only one running turn. Additional prompt is BUSY and discarded from execution, not queued. User-visible AgentMessage content is allowed; raw reasoning/internal events/command-output floods are not forwarded directly.

## Delivery
Prefer a known status message ID and edit for progress/final first segment. Long final output is deterministically segmented with durable sequence state. Confirmed segments are never recreated. Ambiguous message creation becomes DELIVERY_UNKNOWN.

## Persistence authority
SQLite owns controller settings/mode epochs/dialogue/job/callback/outbox metadata. Codex owns conversation thread history. Controller stores conversation content only transiently when required for crash-safe execution/delivery; it does not intentionally keep a second permanent transcript.

## Failure domains
Telegram outage blocks new remote input; completed Codex output waits for delivery. Codex child outage leaves bot/settings alive. One server outage does not disable another. SQLite failure fails closed before Codex effects. Fleet mismatch is visible in status while reserved activation remains safe.

## Target repository structure
```text
src/codex_control/{domain,application,ports,adapters/{codex,telegram,persistence},infrastructure}
tests/{unit,integration,acceptance}
config/examples
deploy/systemd
docs/{adr,contracts,acceptance,evidence,runbooks}
```
Current flat foundation is migrated only by an assigned implementation step.
