# ADR-0038 — P5.3 fleet status identity and final fake multi-controller acceptance

Status: Accepted
Date: 2026-09-08

## Context

P5.1 established the shared fleet manifest, deterministic persistent group keyboard, exact operator/control-supergroup trust edge, reserved activation namespace, durable activation/all-sleep control epochs, STATUS read-only semantics and restart/current-boot SLEEP authority.

P5.2 established the final local group-routing facade: short serialized admission decisions, durable stale/SLEEP/BUSY/BLOCKED replay guards, accepted P3 delegation outside the group lock and no delayed prompt queue.

P5.3 closes the fake/application P5 milestone. It must prove that several independent controller stacks consuming the same human group messages produce the intended fleet behavior without a coordinator, and that fleet configuration mismatch is both visible and routing-safe.

A controller cannot authoritatively know peer configuration without introducing forbidden peer RPC/shared state. Therefore P5.3 does not invent a distributed consensus mechanism. Instead:

1. every local STATUS projection exposes the controller's exact configured `fleet_version`;
2. every projection exposes a deterministic SHA-256 identity of the complete ordered fleet manifest;
3. the final multi-controller acceptance compares those local projections and proves mismatch is visible;
4. accepted P5.1 reserved activation parsing remains the runtime safety mechanism: an activation label unknown to an old manifest is still CONTROL/ACTIVATE with unknown target and makes that controller SLEEP, never prompt.

## Decision

Add a pure P5.3 status projection surface plus a pure Telegram-like renderer. No network/send/edit action is included.

Add application module:

`codex_control.application.fleet_status`

and Telegram adapter module:

`codex_control.adapters.telegram.fleet_status_render`.

P5.3 does not modify accepted P5.1 or P5.2 production semantics.

## Manifest identity

Add public pure function:

`fleet_manifest_fingerprint_sha256(manifest) -> str`.

Input must be exact accepted `FleetManifest`.

Canonical UTF-8 source is exactly the NUL-separated sequence:

1. literal `codex-control-fleet-v1`;
2. exact `manifest.fleet_version`;
3. decimal exact member count;
4. for each member in exact manifest order:
   - exact `server_id`;
   - exact `display_name`.

Equivalent conceptual construction:

```text
parts = [
  "codex-control-fleet-v1",
  fleet_version,
  str(len(members)),
  member1.server_id,
  member1.display_name,
  member2.server_id,
  member2.display_name,
  ...
]
source = "\0".join(parts).encode("utf-8")
fingerprint = sha256(source).hexdigest()
```

The result is exact lowercase 64-character hexadecimal SHA-256.

Fleet member/server/version validators already exclude NUL ambiguity. No JSON serializer, locale or dictionary ordering participates.

Any change to fleet version, member count, member order, server ID or display name changes the identity except for cryptographic collision probability. The fingerprint is diagnostic metadata only; no external effect or activation decision is authorized by it.

## Status projection

Add frozen repr-safe:

`FleetStatusProjection` with exact fields:

- `server_id`
- `display_name`
- `effective_mode`
- `fleet_version`
- `manifest_fingerprint_sha256`
- `member_count`
- `boot_generation`
- `last_control_epoch`

Validation uses the accepted P5.1 bounds/types. `effective_mode` is exact `ControllerMode`. Fingerprint is exact lowercase SHA-256 hex. No prompt/output/thread/job/turn/token/path fields exist.

## Status errors

`FleetStatusErrorCategory` exactly:

- `INVALID_ARGUMENT`
- `INVARIANT`

Add finite content-free `FleetStatusError` whose `str`/`repr` expose only the finite category.

## Status service

Add:

`FleetStatusService(manifest, *, server_id)`

with one public method:

`project(result)`.

Constructor requires exact `FleetManifest`; `server_id` must occur exactly once and obey the accepted identifier rules.

`project(result)` accepts only exact accepted P5.2 `GroupRoutingResult` with:

- status exactly `GroupRoutingStatus.STATUS`;
- exact nested P5.1 `FleetControlResult` status STATUS;
- exact `FleetModeSnapshot`;
- no turn result/disposition/reason beyond the accepted P5.2 STATUS shape.

Projection requires:

- snapshot.server_id == configured local server_id;
- snapshot.fleet_version == manifest.fleet_version;
- exact local display name from the manifest;
- valid nonnegative boot generation/control epoch.

Mismatch or malformed nested status is `FleetStatusError(INVARIANT)`.

The service performs no storage access, clock read, mode mutation or network call. It projects the exact STATUS snapshot already returned by accepted P5.1/P5.2.

## Renderer

Add pure:

`TelegramFleetStatusRenderer.render(projection)`.

Input must be exact `FleetStatusProjection`.

Output exactly a Telegram-like dictionary with only:

`{"text": <plain text>}`.

No parse mode, entities, keyboard, callback, URL, send/edit/network behavior.

The plain text uses exact fields in this order:

```text
🖥 <display_name>
Server: <server_id>
Mode: <ACTIVE|SLEEP>
Fleet: <fleet_version>
Members: <member_count>
Manifest: <first 16 lowercase hex chars>
Boot: <boot_generation>
Control epoch: <last_control_epoch>
```

The full 64-character fingerprint remains in the projection; the 16-character prefix is for compact human-visible comparison only and is never used as an authority decision.

## Fleet mismatch semantics

There is no local `MATCH/MISMATCH` state because a controller has no peer authority.

Mismatch is visible by comparing status responses:

- different `fleet_version` => visible difference;
- same `fleet_version` but different member list/order/labels => different manifest fingerprint.

No controller sleeps or activates merely because another status appears different. Runtime routing safety remains the shared reserved activation namespace.

## Unknown activation during manifest rollout

The final acceptance must model an old controller whose manifest lacks a newly added server and a newer controller that knows it.

For a human group message equal to the new server's activation label:

- new controller normalizes exact ACTIVATE target=new server and makes only that local target ACTIVE;
- old controller normalizes the same reserved-prefix message as ACTIVATE target=None and applies local SLEEP;
- neither controller classifies the message as TEXT;
- old controller never invokes P3 for that activation;
- status projections visibly differ in fleet version/fingerprint.

This is the required version-mismatch fail-safe. No peer RPC or source-code fork is permitted.

## Final fake multi-controller acceptance

Add a final P5 fake/application acceptance using independent temporary SQLite stores per controller and the real accepted:

- `TelegramGroupUpdateAdapter`;
- `TelegramFleetKeyboardRenderer`;
- `FleetControlService`;
- `FleetGroupRoutingService`;
- `FleetStatusService`;
- `TelegramFleetStatusRenderer`;
- accepted controller/ingress/settings/dialogue repositories;
- accepted `DialogueTurnService` where practical with fake local P1 lifecycle ports.

No real Telegram/Codex/network effect.

For two controllers with the same manifest, prove at least:

1. both boot effective SLEEP;
2. both render byte/value-equivalent persistent keyboards;
3. one human self-activation message makes target ACTIVE and non-target SLEEP;
4. subsequent ordinary prompt executes through accepted P3 only on ACTIVE target and is terminal SLEEP-ignored on non-target;
5. activating the other server swaps routing authority;
6. all-sleep makes both SLEEP;
7. STATUS is read-only on both and preserves mode/control epoch;
8. status projections have identical fleet version/full manifest identity and distinct local server/display identity;
9. status renderer is pure/minimal;
10. restart of a controller that historically requested ACTIVE returns effective SLEEP; a prompt before a fresh current-boot activation is ignored and does not execute;
11. a fresh current-boot activation re-enables only the exact target.

For mismatched old/new manifests, prove:

12. version and/or manifest fingerprint differs visibly;
13. new-server activation is exact target on the new controller;
14. the old controller treats the same message as reserved unknown activation and becomes/remains SLEEP;
15. no old-controller P3 prompt execution occurs from that activation text;
16. exact all-sleep and STATUS labels remain safe/common across versions.

## Offline/restart boundary

P5.3 proves only the accepted local application invariant: every new controller boot starts effective SLEEP even when persisted requested mode is ACTIVE, and no process-local P5.2 prompt marker/queue is restored.

Live Telegram polling backlog/offset behavior is not claimed here. Real offline/backlog acceptance remains P11/P9 transport authority. P5.3 must not claim that an application-only test can distinguish a pre-restart Telegram message that was never delivered from a genuinely post-restart operator message.

## Security/content boundary

Status contains only non-secret fleet/controller metadata. It must not contain:

- prompt/output;
- thread/job/turn IDs;
- callback tokens/hashes;
- CODEX_HOME/path/environment;
- raw Telegram JSON;
- raw exception/credentials.

Manifest fingerprint is non-secret diagnostic metadata.

## Non-goals

P5.3 does not implement:

- Telegram HTTP/polling/webhook/token loading;
- outbound send/edit;
- Codex response delivery/chunking;
- P1.7 approval-response orchestration;
- peer RPC/coordinator/shared fleet database;
- production config/TOML materialization;
- systemd/deployment;
- live backlog proof;
- P6+.

No schema/DDL change.

## Acceptance

P5.3 acceptance requires:

- exact manifest fingerprint contract and deterministic vectors;
- exact projection/error/renderer contracts;
- status projection from exact P5.2 STATUS only;
- local snapshot/manifest identity mismatch fails INVARIANT;
- status path performs zero mutation/clock/network;
- matching-manifest multi-controller activation/prompt/all-sleep/status/restart scenario;
- mismatched-manifest unknown-activation safety scenario;
- final fake P5 acceptance module;
- all accepted P2.C2/P5.1/P5.2/P4/P3/P2/P1 regressions green;
- no real external/production effects.

After architect acceptance of P5.3, P5 is complete at the fake/application group-routing boundary. P6 may then begin delivery/full local orchestration.
