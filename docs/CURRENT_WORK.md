# Current work authority

Date: 2026-09-09

## Accepted facts

- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 authority remains `codex-cli 0.144.6`; generated app-server schema SHA-256 remains `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- Current CodexControl storage schema is v2; historical v1 DDL SHA-256 remains `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`; v2 migration SHA-256 remains `a07e05aceda953f295d1ed49f631e2e32936394c4cfa676a33d28d9152d8cd85`.
- P2.C2 accepted `082c6df79a7c3a6d8dd04b73f15563f1668b6c9b`; full 796.
- P3 is COMPLETE; P3.5 accepted `6145d262787465ac6b4a17327114211cd86e8104`; full 671.
- P4 is COMPLETE; P4.3 accepted `d053f24061e20aa44e07e5b92c9b92c6506647fd`; full 762.
- P5 is COMPLETE; P5.3 accepted `c23d9356e7033ce44a62933f7749250433d49f61`; full 860.
- P6 is COMPLETE at the fake/application boundary; P6.3 accepted `0409ad4a0744159aad875a5ddea4deaf1181699e`; final P6 full 954.
- No live Telegram or production deployment acceptance has occurred.

## Rejected P7 real hard-delete result

Original P7 under ADR-0042 is **REJECTED / ARCHITECTURE BLOCKED**.

Exactly one real P7 thread was created and real authenticated multi-turn, approval and interrupt behavior was established. Exactly one official accepted P1.9 `thread/delete` was then dispatched. Its official result was `DELETE_UNKNOWN`, which remains terminal and was never retried or reconciled through `thread/read` / `thread/list`.

Final read-only forensic evidence on the rejected branch is commit:

`5aac49bd1b8a349343db52071520beed7f95592d`

It proved `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL`: five synthetic material-marker matches remained physically after the ambiguous delete, while the P7 session artifact was absent and the unrelated-session baseline remained intact. Issue #38 remains the historical rejection/blocker record.

P1.9 and accepted P3.5 uncertainty semantics remain valid: a dispatched non-success is `DELETE_UNKNOWN`; there is no blind retry or inferred success, and local final purge/tombstone is not allowed for UNKNOWN.

## P7.C1 — COMPLETE / architect accepted

Issue #39 opened the storage-isolation architecture correction.

Binding discovery authority: Issue #39 comment `5597864058`.

Accepted discovery commit:

`a9900471d0599be21b1a1834301c4421d95acb29`

Accepted discovery facts include:

- historical P7 `OTHER` is SQLite sidecar/WAL storage;
- synthetic marker residue is unallocated SQLite main-file data plus WAL frames, not live marker B-tree payload;
- thread-ID residue includes live B-tree rows plus WAL/unallocated bytes;
- exact installed 0.144.6 supports `CODEX_SQLITE_HOME` / `sqlite_home`, `log_dir`, and `history.persistence=none`;
- session/rollout relocation and independently configurable file-auth path were not found for exact installed 0.144.6;
- `codex2` is interactively shared and cannot be a disposable production home;
- no Codex version upgrade is required for the selected correction topology.

P7.C1 architect acceptance:

`docs/evidence/p7c1/P7C1_ARCHITECT_ACCEPTANCE_2026-09-09.md`

## ADR-0043 — ACCEPTED

ADR-0043 freezes the correction topology:

**dedicated CodexControl-only persistent profile home + distinct CodexControl-owned isolated SQLite/log state root per profile.**

The persistent profile home owns auth/config/session-rollout authority and must not be shared with interactive Codex workloads. Credentials are never copied/symlinked/migrated by CodexControl. Production profiles require independent provisioning or another separately approved credential authority.

The isolated state root owns SQLite state/log DBs and WAL/SHM plus configured logs. Root ownership, permissions, canonical paths, non-overlap and runtime exclusivity fail closed. Row-level SQLite surgery remains forbidden; when authorized by the corrected lifecycle, physical erasure is whole isolated-root destruction/recreation after the owning runtime is fully stopped.

`LOG_DB`, `LOG_DB_WAL` and `LOG_DB_SHM` are mandatory hard-delete proof/cleanup scope even though the P7.C1 storage-map table used `NOT_TARGETED` for those families.

ADR-0043 also corrects confirmed-delete ordering. Exact P1.9 confirmation must first become durable as:

`DELETE_CONFIRMED_PENDING_STORAGE`

with exact profile/thread binding retained. Only after isolated-state cleanup plus persistent-profile/session residual gates pass may CodexControl finalize local purge, binding removal and bounded tombstone.

Historical schema-v1/v2 authorities remain immutable. P7.C2 introduces schema v3 for this new durable barrier.

## Current slice

**P7.C2 — NEXT / AUTHORITY FROZEN BY ADR-0043.**

P7.C2 is the schema-v3 confirmed-delete storage barrier only.

Required boundary:

- add schema-v3 migration authority without modifying historical v1/v2 hashes;
- add exact `DELETE_CONFIRMED_PENDING_STORAGE` repository/state semantics;
- preserve `DELETE_UNKNOWN` no-retry behavior;
- exact P1.9 `DELETE_CONFIRMED` must durably enter the confirmed-pending state before any local purge/tombstone;
- startup/restart must distinguish pre-existing `DELETING` (ambiguous -> UNKNOWN) from `DELETE_CONFIRMED_PENDING_STORAGE` (confirmed upstream; local cleanup only, never redispatch);
- do not yet implement isolated root lifecycle/runtime configuration; that is P7.C3;
- no real Codex business effect, no Telegram, no P8/P9.

P7.C2 acceptance requires schema migration/rollback/materialization tests, repository/application state tests, restart/crash/race proofs, full ordinary regression, commit/push and independent architect readback.

## Frozen remaining correction lane

After P7.C2 architect acceptance only:

1. **P7.C3** — dedicated profile + isolated state-root runtime authority.
2. **P7.C4** — confirmed cleanup + `DELETE_UNKNOWN` local-containment orchestration.
3. **P7.C5** — corrected fake hard-delete acceptance.
4. **P7.C6** — renewed separately authorized isolated real Codex T3 + hard-delete acceptance.

P8 and P9 remain blocked until P7.C6 is independently architect-accepted.

## Current non-goals

Do not start P7.C3+, another real P7 thread/delete, live Telegram HTTP/polling/webhook acceptance, production packaging/systemd, server-78 work, P8 or P9 inside P7.C2.

Do not clean or mutate the retained rejected P7 evidence home merely to improve historical results. Do not retry the retained P7 delete. Do not weaken ADR-0008 or ADR-0016.
