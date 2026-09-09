# ADR-0043 — Dedicated Codex profile + isolated state root hard-delete correction

Status: Accepted
Date: 2026-09-09

## Context

P7 real-Codex acceptance under ADR-0042 is rejected and architecture-blocked.
Exactly one accepted P1.9 `thread/delete` was dispatched for the retained P7
thread and returned `DELETE_UNKNOWN`; no retry, `thread/read`, `thread/list`,
or manual Codex-store surgery occurred. Read-only forensic proof then found
five synthetic material-marker residuals and live thread-identifier residuals.
The frozen official status remains `DELETE_UNKNOWN`.

P7.C1 discovery at
`a9900471d0599be21b1a1834301c4421d95acb29` refined the physical cause:

- historical `OTHER` residuals are SQLite WAL sidecars, not a separate store;
- synthetic marker bytes remain in SQLite main-file unallocated regions and
  WAL frames, not in live marker B-tree payload;
- exact thread-identifier bytes remain both in live SQLite B-tree payload and
  WAL/unallocated regions;
- exact installed `codex-cli 0.144.6` supports `CODEX_SQLITE_HOME` /
  `sqlite_home`, `log_dir`, and `history.persistence=none`;
- exact installed 0.144.6 does not expose an independent session/rollout path
  control or a separate file-auth path independent from `CODEX_HOME`;
- current `codex2` is not safe for whole-root destruction because it is
  interactively shared; current `codex3` has lower sharing evidence but future
  production ownership must still be explicit and enforced.

The V1 product already freezes at most one live dialogue per physical server.
Accepted P1.2 owns at most one READY app-server child per profile. Therefore a
per-profile isolated state root is sufficient for V1 provided roots are never
shared across profiles/applications and ownership is fail-closed.

P7.C1 is accepted as discovery evidence. Its recommended topology is accepted,
but this ADR corrects two lifecycle/proof details before implementation:

1. SQLite `LOG_DB`, `LOG_DB_WAL`, and `LOG_DB_SHM` are dialogue-bearing
   hard-delete proof/cleanup scope even though the discovery storage-map table
   labelled them `NOT_TARGETED`. That label may describe the official
   `thread/delete` RPC's direct target only; it must never exclude those files
   from measured storage proof or containment.
2. Local confirmed purge/tombstone must not happen before the Codex storage
   cleanup gate. Exact upstream confirmation must first become durable while
   the full profile/thread binding is still retained.

## Decision

CodexControl V1 uses **dedicated CodexControl-only persistent profile homes plus
separate CodexControl-owned isolated state roots**.

No Codex version upgrade is required for this correction. Exact installed
0.144.6 capability remains a mandatory runtime/deployment gate.

### Persistent profile authority

Every production-enabled profile has one persistent `CODEX_HOME` that is:

- explicitly configured, absolute, canonical and root-owned;
- dedicated to CodexControl and never shared with interactive CLI/Desktop or
  another application;
- not group/world writable;
- not a symlink and not nested inside the disposable state root;
- the authority for profile configuration, authentication and Codex
  session/rollout persistence.

File credentials may remain below the dedicated profile home when that is the
explicitly provisioned auth mode. CodexControl must never copy, symlink or
migrate credential material from another home. A new dedicated profile is
independently provisioned or uses another separately approved exact-version
credential authority.

`history.persistence=none` is required for a production-enabled dedicated
profile unless a later architect decision proves an equivalent content-safe
configuration. This control does not disable or relocate session/rollout
persistence, so the session tree remains part of the hard-delete proof.

### Isolated state authority

Each configured CodexControl profile has a distinct isolated state root outside
its persistent `CODEX_HOME`.

The exact child/runtime configuration must route:

- SQLite state databases and their WAL/SHM sidecars through
  `CODEX_SQLITE_HOME` / `sqlite_home` into that state root;
- SQLite log databases into the same SQLite root;
- configurable text logs through `log_dir` into that same product-owned state
  boundary.

A state root may not be shared by two profiles, by an interactive Codex
process, by another application, or by the CodexControl controller SQLite DB.
No configured state root may be an ancestor/descendant of its `CODEX_HOME`,
repository, controller state root, credential root, or another profile's root.

Runtime startup fails closed on unknown ownership, unsafe permissions,
symlinks, overlap, unexpected foreign files/owners, version/capability drift,
or inability to prove the exact storage routing.

## Whole-root containment authority

CodexControl never repairs Codex SQLite using row-level `DELETE`, `UPDATE`,
`VACUUM`, checkpoint, WAL truncation or equivalent shared-store surgery.

The isolated state root may be destroyed/recreated only when all are proven:

- exact root is configured for exactly one CodexControl profile;
- the profile is exclusively reserved against runtime acquire/start;
- every CodexControl-owned app-server child using the profile is fully stopped
  and reaped;
- no unrelated dialogue/thread/application can use the root;
- no credential or surviving global profile/config authority is inside it;
- the root is canonical, root-owned, non-symlink, bounded, and passes the
  exact ownership/foreign-entry policy;
- crash recovery can distinguish safe local containment from an external
  Codex delete effect.

Recreation produces a fresh secure empty root before future runtime use.
Whole-root containment is a local storage operation and never changes official
upstream delete authority.

## Confirmed-delete durability barrier

Current schema-v2 finalizes local purge immediately after P1.9
`DELETE_CONFIRMED`. That ordering is insufficient once physical storage cleanup
becomes part of the production hard-delete sequence.

The correction adds one durable dialogue state:

`DELETE_CONFIRMED_PENDING_STORAGE`

Historical schema-v1 and schema-v2 hashes remain immutable. A new schema-v3
migration will extend the live dialogue state authority without rewriting the
historical DDL/migration authority.

Exact corrected sequence:

`DELETE_PENDING -> DELETING -> P1.9 thread/delete`

Then:

- dispatched non-success / uncertainty -> existing durable `DELETE_UNKNOWN`;
- deterministic accepted pre-dispatch failure -> existing deterministic error
  semantics;
- exact schema-valid P1.9 `DELETE_CONFIRMED` -> atomically
  `DELETING -> DELETE_CONFIRMED_PENDING_STORAGE`, preserving exact
  `dialogue_id`, `profile_id`, `thread_id`, version and non-content authority.

No CodexControl payload/job purge, live-binding removal, or tombstone is
allowed at the transition into `DELETE_CONFIRMED_PENDING_STORAGE`.

## `DELETE_CONFIRMED_PENDING_STORAGE` lifecycle

While this state exists:

- new turns, settings/profile mutation and new dialogue creation remain
  blocked;
- no `thread/delete` retry or any other Codex delete/read/list reconciliation
  is permitted;
- runtime acquisition for the owning profile is reserved against new work;
- startup recovery recognizes upstream deletion as already confirmed and must
  never downgrade it to `DELETE_UNKNOWN` merely because local cleanup was not
  finished.

The local cleanup owner then:

1. shuts down/reaps the exact product-owned profile runtime under the exclusive
   profile reservation;
2. proves isolated-root ownership and routing invariants;
3. destroys the complete isolated state/log root, including SQLite main files,
   WAL/SHM sidecars, SQLite log DBs, text logs, cache/temp files inside that
   root, and recreates a fresh secure root;
4. verifies the persistent dedicated `CODEX_HOME` has no session/rollout
   artifact for the exact deleted thread and that the required history policy
   remains content-safe;
5. runs the bounded residual gate required by the implementation/acceptance
   authority with zero scan errors;
6. only after every local storage gate passes invokes the corrected confirmed
   finalization that purges CodexControl-owned jobs/payloads/delivery/approvals,
   removes the live binding and creates the bounded content-free tombstone.

If local storage cleanup fails, the dialogue remains
`DELETE_CONFIRMED_PENDING_STORAGE` with the exact binding retained. It does
not become `DELETED`, does not create a tombstone, and does not start another
Codex effect.

Local isolated-root destruction/recreation is idempotent under the same
exclusive ownership proof. Startup may resume this local cleanup only; it may
not redispatch upstream delete.

## `DELETE_UNKNOWN` lifecycle

ADR-0016 and accepted P3.5 uncertainty semantics remain authoritative:

- `OFFICIAL_DELETE_AUTHORITY=UNKNOWN` remains durable;
- no retry, second delete, `thread/read`, `thread/list`, notification guessing,
  or inferred success exists;
- live dialogue/binding is retained;
- local final purge and deletion tombstone remain forbidden.

After the owning runtime is fully stopped, a future P7.C4 local containment
path may destroy/recreate the exact isolated state root under the whole-root
rules. If it does, the only permitted additional fact is:

`LOCAL_ISOLATED_STORAGE_CONTAINMENT=COMPLETED`

This must coexist with `OFFICIAL_DELETE_AUTHORITY=UNKNOWN`. It is not a
reconciliation result and does not authorize tombstone finalization. Persistent
session/rollout material in `CODEX_HOME` is not manually removed under UNKNOWN.
The profile/dialogue therefore remains blocked until a separately accepted
operator/architecture resolution exists.

Any local containment retry after crash is an idempotent local-root operation,
not a retry of the external Codex effect, and requires the same exclusive
ownership proof before each attempt.

## Crash/restart recovery

Recovery precedence is corrected as follows:

- pre-existing `DELETING` still means an external delete may have been
  dispatched without durable confirmation and therefore becomes
  `DELETE_UNKNOWN` with zero Codex effect;
- pre-existing `DELETE_CONFIRMED_PENDING_STORAGE` means exact upstream
  confirmation was durably recorded; recovery performs only bounded local
  storage cleanup/finalization and never calls P1.9;
- pre-existing `DELETE_UNKNOWN` remains unknown and performs no automatic
  external reconciliation;
- a retained tombstone remains the final idempotent replay authority only
  after the confirmed storage-cleanup gate completed.

The confirmed-pending state must be persisted before any local CodexControl
purge so exact thread/profile identity survives a crash during storage cleanup.

## Hard-delete proof boundary

Production and renewed P7 acceptance treat all dialogue-bearing Codex storage
families as in-scope evidence, including:

- persistent profile `sessions` / rollout artifacts;
- any enabled history/index material;
- SQLite state main/WAL/SHM;
- SQLite log main/WAL/SHM;
- configured text logs;
- cache/temp/other persistent families inside the isolated state root;
- any otherwise unclassified file that can contain the exact thread identity
  or synthetic acceptance material.

For the isolated SQLite/log root, successful whole-root destruction and secure
recreation is the erasure mechanism. Row-level SQLite absence is not accepted
as physical erasure because P7.C1 proved deleted marker bytes can remain in
unallocated pages and WAL frames.

For the persistent profile root, official delete must remove the exact
session/rollout artifact. P7.C6 must again use synthetic high-entropy material
markers and prove zero material residual across both the persistent profile
home and isolated state root after the corrected confirmed lifecycle.

Any material residual, active-store thread identity, scan error, foreign-root
ownership, or unrelated artifact removal blocks P7 acceptance and therefore
P8/P9.

## Auth and provisioning boundary

This ADR does not authorize credential copying or migration.

A dedicated profile used for renewed real P7 proof must already be safely
independently authenticated, or be independently provisioned under a separate
explicit authorization. Existing shared interactive homes are not silently
converted into production homes.

Exact installed auth modes are capability choices, not permission to expose
secrets. Credential content remains outside Git/evidence/logs.

## Exact-version gate

P7.C1 found no Codex upgrade requirement for this topology. Nevertheless every
implementation/deployment/real-acceptance path must fail closed unless the
selected installed executable independently proves the required controls:

- expected executable/version/schema authority;
- isolated SQLite root support;
- required log relocation support;
- required history policy;
- auth/profile ownership model;
- unchanged official delete response authority.

A future version that lacks or changes any required capability reopens
architecture review before production.

## Correction slices

The correction lane is frozen in this order.

### P7.C2 — schema-v3 confirmed-delete storage barrier

Add the schema-v3 migration and repository/application primitives required for
`DELETE_CONFIRMED_PENDING_STORAGE` while preserving historical v1/v2 hashes and
all existing `DELETE_UNKNOWN` no-retry semantics.

No real Codex effect. Acceptance requires migration/rollback/restart/race and
confirmed-vs-unknown state proofs plus full regression.

### P7.C3 — dedicated profile + isolated state-root runtime authority

Extend the profile/config/runtime authority with the isolated state root,
exact installed capability gate, safe child configuration, root ownership and
overlap checks, exclusive profile reservation, secure root create/recreate and
fail-closed foreign-owner semantics.

No credential copying and no real model/thread effect. Fake-process/filesystem
proof plus full regression required.

### P7.C4 — confirmed cleanup + UNKNOWN containment orchestration

Compose P1.9/P3.5 with the confirmed-pending barrier and isolated-root lifecycle.
Prove confirmed cleanup ordering, crash restart without delete redispatch,
local containment labeling under UNKNOWN, session persistent-root gate, and
that local final purge/tombstone occurs only after complete storage proof.

No real Codex business effect in this slice. Full fake/application regression
required.

### P7.C5 — corrected fake hard-delete acceptance

Proof-only fake acceptance across schema/runtime/storage/application boundaries:
confirmed and unknown matrices, root ownership failures, WAL/SHM/log residual
cases, session/history gate, unrelated baseline, crash points and no duplicate
external effects. No production source change unless a separately opened defect
correction is required.

### P7.C6 — renewed isolated real Codex T3 + hard-delete acceptance

Separately authorized proof-only real acceptance using the corrected dedicated
profile/isolated-state topology. One new disposable thread and one official
no-retry delete budget only. PASS requires exact `DELETE_CONFIRMED`, successful
confirmed-pending storage cleanup, zero synthetic material residual, zero active
thread-identity residual, preserved unrelated baseline and ordinary regressions.

P8 and P9 remain blocked until P7.C6 is independently architect-accepted.

## Supersession / compatibility

ADR-0007, ADR-0008, ADR-0009, ADR-0016 and the no-blind-retry portion of
ADR-0031 remain authoritative.

ADR-0043 **partially supersedes ADR-0031 only for confirmed-delete local
finalization and startup recovery after durable upstream confirmation**:
confirmed deletion no longer directly permits immediate local purge/tombstone;
it first enters `DELETE_CONFIRMED_PENDING_STORAGE` and must pass the isolated
storage cleanup gate.

P1.9 external delete response semantics are unchanged.

## Acceptance consequence

P7.C1 discovery is architect-accepted as the basis for this correction.
Original P7 remains rejected. Issue #38 remains historical blocker evidence.
P8/P9 stay blocked. The next executable roadmap slice is P7.C2 only.
