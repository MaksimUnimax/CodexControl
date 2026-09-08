# P5.3 fleet status and final fake acceptance implementation evidence

Status: implementation evidence only; no architect acceptance is claimed.

## Authority and base

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `10c828ae2dabb1ec8b52e2d0daf7923d57bec73d`
- Branch: `impl-p5-3-fleet-status-acceptance-2026-09-08`
- Issue: `#34`
- Binding authority: ADR-0038
- Accepted P5.2: `345c48722c4faa03be19d38b6f07304276075f64`
- Accepted P5.1: `0d1e530a1b9fdc70fc36ca985ef1cdcbf41688d3`
- Accepted P2.C2: `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`

## Production paths

- `src/codex_control/application/fleet_status.py`
- `src/codex_control/application/__init__.py`
- `src/codex_control/adapters/telegram/fleet_status_render.py`
- `src/codex_control/adapters/telegram/__init__.py`

Accepted P5.1, P5.2, P3, P2 and schema production files were not changed.

## Manifest fingerprint authority

`fleet_manifest_fingerprint_sha256` accepts only an exact `FleetManifest` and
hashes the strict-UTF-8 encoding of the exact NUL-separated sequence:

`codex-control-fleet-v1`, exact fleet version, decimal member count, then each
ordered member server ID and display name. There is no JSON, repr, sorting,
normalization, dictionary ordering, trailing NUL or newline. The result is
lowercase 64-character SHA-256 hexadecimal.

The independent vector for `fleet-v1`, ordered `server-80/SERVER-80` then
`server-78/SERVER-78` is:

`be743c8df35550e3b1ab11f945e573a151cdc80dad8e6db16435165a1fb0974e`

Tests directly cover version, member count, order, server ID and display name
sensitivity, deterministic repeatability, and independence from local server,
mode, boot generation and control epoch. An accepted P5.1 manifest containing
an isolated surrogate fails closed as finite `FleetStatusError(INVARIANT)`.

## Fleet status projection

`FleetStatusProjection` is frozen and has exactly:

`server_id, display_name, effective_mode, fleet_version,
manifest_fingerprint_sha256, member_count, boot_generation,
last_control_epoch`.

`FleetStatusService(manifest, *, server_id)` stores only the exact manifest,
the exact local member and the precomputed full fingerprint. It projects only an
exact P5.2 `STATUS` result. It requires exact nested P5.1 STATUS status, exact
outer/nested snapshot object identity, local server identity and configured
fleet-version coherence. Other routing statuses, wrong local server/version,
malformed counters and malformed nesting fail closed as `INVARIANT`.

The service has no storage, clock, network, mode mutation or callback path.

## Pure status renderer

`TelegramFleetStatusRenderer.render` accepts only an exact projection and
returns exactly `{"text": <plain string>}`. The eight lines are local display
name, server ID, effective mode, fleet version, member count, the first 16
lowercase fingerprint characters, boot generation and control epoch. There is
no trailing newline, parse mode, keyboard, callback, URL, send/edit or network
operation. The full fingerprint remains in the projection and the short prefix
is display-only.

## Status read-only/coherence proof

Real P5.1 `FleetControlService` and real P5.2 `FleetGroupRoutingService` were
used with temporary SQLite. A normalized `📊 СТАТУС` update produced exact
`GroupRoutingStatus.STATUS`; before/after checks preserved the runtime row,
requested mode, control epoch, boot generation, ingress count, turn-job count
and transient-payload count. A fake P3 port was never called. Matching
manifests produced identical version/full fingerprint/member count and distinct
local identity. Same-version changed manifests produced different fingerprints.

## Matching-manifest final fake acceptance

`tests/acceptance/test_p5_fleet_group_fake.py` uses two independent temporary
SQLite files and the real group adapter, keyboard renderer, P5.1 control
service, P5.2 routing service, status service/renderer, repositories and
accepted `DialogueTurnService`, with fake local P1 thread/turn lifecycle ports.
The same synthetic human-originated group message is normalized separately by
both adapters for each step.

The matching scenario proved:

- both boots are effective SLEEP and keyboards are equal with the exact final
  all-sleep/status row;
- activation A makes A ACTIVE, B SLEEP, and remains CONTROL with zero P3 call;
- prompt A produces one real P5.2 PROMPT/JOB and one accepted P3 call only on A;
- activation B switches authority; prompt B produces PROMPT/JOB only on B;
- all-sleep returns both controllers to SLEEP;
- STATUS is read-only and renders matching fleet identity with distinct local
  identity;
- historical requested ACTIVE survives as diagnostics, but a new boot is
  effective SLEEP with a new boot generation;
- a prompt newer than the historical control epoch before fresh activation is
  `IGNORED_SLEEP`, creates no JOB and invokes no P3;
- a fresh current-boot self activation restores exact local authority, after
  which a newer prompt is admitted normally.

## Mismatched-manifest rollout safety

The mismatch scenario uses independent old (`fleet-v1`, `server-old/OLD`) and
new (`fleet-v2`, `server-old/OLD` plus `server-new/NEW`) controller stacks.
Status renders expose both the version and full-fingerprint difference.

The shared raw `🖥 NEW` message is CONTROL/ACTIVATE with exact target
`server-new` on the new adapter and CONTROL/ACTIVATE with target `None` on the
old adapter. The old controller becomes/remains SLEEP, invokes zero P3 calls
and creates no JOB from the activation text. Common all-sleep and STATUS
controls remain safe on both versions.

No controller reads another controller's SQLite, process state, mode or service
instance. There is no peer RPC, coordinator or shared fleet database.

## Offline/backlog boundary

P5.3 proves only the local application restart invariant: a newly constructed
controller boot is effective SLEEP until a fresh current-boot activation is
processed. P5.3 does **not** prove live Telegram backlog safety, polling-offset
replay behavior or identification of whether an undelivered update was sent
before or after restart. Those are later live transport acceptance concerns.

## Test and regression record

- Focused P5.3 unit tests: `11`
- Focused P5.3 integration tests: `6`
- Final P5 fake acceptance tests: `2`
- Accepted pre-P5.3 full baseline: `841`
- Full arithmetic: `841 + 11 + 6 + 2 = 860`
- Prior regression groups: P5.2 `11/34`; P2.C2 `5/13/1`; P5.1 `7/8`;
  P4.3 `7/26/1`; P4.2 `5/29`; P4.1 `8/15`; P3.5 `12/25/1`; P3.4 `6/31`;
  P3.3 `5/25`; P3.2 `2/21`; P3.1 `11/26`; P2.C1 `5/1`; P2.6b `5/12/8/3`;
  P2.6a `4/28`; P2.5 `4/18`; P2.4b `6/25`; P2.4a `8/31`; P2.3 `7/28`;
  P2.2 `6/20`; P2.1 `8/31`; P1.9 `15`; P1.8 `28`; P1.10 `6/1/4`.

Validation commands and results:

- focused unit/integration/acceptance discovery: PASS;
- `PYTHONPATH=src python3 -m compileall -q src tests`: PASS;
- public P5.3 import/vector smoke: PASS (`P5_3_IMPORT_PASS`);
- `git diff --check`: PASS;
- schema version remains `2`;
- historical v1 DDL SHA-256 remains
  `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`;
- schema-v2 migration SHA-256 remains
  `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`;
- no schema/migration statement change;
- no credentials, raw Telegram JSON, prompt/output content, thread/job/turn
  identifiers, private profile paths, environment data or raw exceptions are
  written to production or evidence surfaces.

The known P1.6 pending-task warning is an inherited test-hygiene warning and
was not introduced by P5.3. No real Telegram, network, bot token, Codex,
production database, production state root, service, thread, turn, interrupt,
delete, approval response or delivery effect was used.

P6 and P7 were not started. Issue #34 remains open. This evidence does not
claim P5.3 architect acceptance or P5 completion.
