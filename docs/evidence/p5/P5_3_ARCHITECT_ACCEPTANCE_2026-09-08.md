# P5.3 architect acceptance — 2026-09-08

Status: **ACCEPTED**

## Accepted implementation

- Repository: `MaksimUnimax/CodexControl`
- Architect base: `10c828ae2dabb1ec8b52e2d0daf7923d57bec73d`
- Implementation branch: `impl-p5-3-fleet-status-acceptance-2026-09-08`
- Issue: `#34`
- Accepted implementation: `c23d9356e7033ce44a62933f7749250433d49f61`
- Implementation commit message: `implement P5.3 fleet status and final fake acceptance`
- Binding ADR: `docs/adr/0038-fleet-status-identity-and-final-fake-acceptance.md`

## Independent topology review

Architect review verified that the accepted candidate is exactly one commit ahead of the frozen P5.3 architect base and zero commits behind. The merge base is exactly `10c828ae2dabb1ec8b52e2d0daf7923d57bec73d`.

The cumulative P5.3 diff is limited to the architect-authorized P5.3 production, package exports, focused tests, final fake acceptance and implementation evidence. Accepted P5.2/P5.1/P3/P2 production and schema authority were not modified.

## Accepted production authority

P5.3 adds only the local fake/application status and fleet-identity boundary:

- deterministic ordered-manifest SHA-256 identity;
- frozen `FleetStatusProjection`;
- pure `FleetStatusService` over exact P5.2 STATUS authority;
- pure minimal `TelegramFleetStatusRenderer`;
- no peer RPC, coordinator or shared fleet database;
- no live Telegram transport or delivery effect.

The manifest fingerprint is the SHA-256 of strict UTF-8 bytes for the NUL-separated sequence:

`codex-control-fleet-v1`, exact fleet version, decimal member count, then every ordered member server ID and display name.

The independently verified known vector remains:

`be743c8df35550e3b1ab11f945e573a151cdc80dad8e6db16435165a1fb0974e`

Status projection requires exact local server/fleet-version coherence and exact outer/nested snapshot object identity. The renderer exposes only the exact bounded status text and a 16-character display prefix of the manifest fingerprint; the full fingerprint remains application diagnostic metadata and the prefix is never routing authority.

## Final fake multi-controller P5 acceptance

Architect review verified the final fake acceptance composition uses:

- independent temporary SQLite state per simulated controller;
- real `TelegramGroupUpdateAdapter`;
- real persistent fleet keyboard renderer;
- real accepted P5.1 `FleetControlService`;
- real accepted P5.2 `FleetGroupRoutingService`;
- real P5.3 status service/renderer;
- accepted `DialogueTurnService` with fake local lifecycle ports only.

The matching-manifest scenario proves:

- both controllers boot effective SLEEP;
- target activation makes only the target ACTIVE and every non-target SLEEP;
- ordinary prompt executes only on the ACTIVE controller and becomes JOB there;
- the non-target records `IGNORED_SLEEP` and invokes no P3 turn;
- switching activation switches prompt authority;
- all-sleep sleeps all controllers;
- STATUS is read-only and both controllers expose the same fleet version/full manifest fingerprint/member count with distinct local identity;
- restart with historical requested ACTIVE still starts effective SLEEP;
- a newer prompt before current-boot reactivation is `IGNORED_SLEEP`, not a stale-prompt artifact;
- a fresh current-boot activation restores prompt authority.

The mismatched-manifest scenario proves:

- fleet-version and full manifest-fingerprint differences are visible;
- a new-server activation is exact target control on the new manifest;
- the same activation is reserved unknown activation control on the old manifest, never TEXT;
- the old controller moves/stays SLEEP and invokes zero P3 calls for that activation;
- common all-sleep and status labels remain safe.

No controller reads peer SQLite/process/mode/service state to make routing decisions.

## Explicit transport boundary

P5.3 does **not** prove live Telegram backlog, polling-offset replay or whether an undelivered update was sent before or after a restart. The accepted claim is application-local only: a newly constructed controller boot is effective SLEEP until a current-boot activation is processed. Live transport/backlog proof remains P9/P11 authority.

## Test evidence

Executor evidence records:

- P5.3 unit: `11`
- P5.3 integration: `6`
- final P5 fake acceptance: `2`
- accepted pre-P5.3 full baseline: `841`
- expected full: `841 + 11 + 6 + 2 = 860`
- observed full: `860`
- failures: `0`
- errors: `0`
- final unittest status: `OK`

Required prior regression groups were reported green, including accepted P5.2 `11/34`, P2.C2 `5/13/1`, P5.1 `7/8`, P4.3 `7/26/1`, P4.2 `5/29`, P4.1 `8/15`, P3.5 `12/25/1`, P3.4 `6/31`, P3.3 `5/25`, P3.2 `2/21`, P3.1 `11/26`, and the requested P2/P1 groups.

The known P1.6 pending-task warning remains inherited test-hygiene debt and was not introduced by P5.3.

## Schema/security/effects

- Current schema remains version `2`.
- Historical schema-v1 SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Schema-v2 migration SHA-256 remains `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- No schema/migration statement changed.
- Compile/import/diff/security checks are recorded PASS.
- No real Telegram/network/Codex/thread/turn/interrupt/delete/approval-response/delivery/production-DB/state-root/service effect occurred.
- No GitHub commit status checks or GitHub Actions workflow runs are attached to the accepted SHA; this acceptance does not claim CI execution.

## Architect verdict

`P5.3 = ACCEPTED`.

`P5 = COMPLETE` at the fake/application group-routing boundary.

The next architecture slice is P6 response delivery/full local orchestration. P6 implementation is not authorized by this acceptance record until its own architect authority is frozen.
