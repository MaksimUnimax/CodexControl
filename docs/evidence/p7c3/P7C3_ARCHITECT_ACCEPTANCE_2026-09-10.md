# P7.C3 architect acceptance — 2026-09-10

Status: **ARCHITECT_ACCEPTED**

Repository: `MaksimUnimax/CodexControl`

Accepted implementation lineage:

- architect base: `0637643518bfe45e471a0d777d2995b833e6bcb8`
- initial candidate: `0654ee1cbd70d4d6a6d5a317e948d2f08b2c081f`
- first architect repair: `a549e6f1f295a37f14a7833ede0233d94745555a`
- second architect repair: `2a6c5d8f2ed0980c4c7bc32cec471002432e1c9d`
- third architect repair / accepted implementation: `f76a32b2d18600fcf7ace6b9aa24067238d6dec7`
- accepted implementation tree: `13eea89362694da594bb2b717c037980b0df446f`

## Independent architect review

P7.C3 was not accepted from executor test counts alone. The complete four-commit candidate was independently reviewed against ADR-0043 and the frozen P7.C3 boundary.

The initial candidate was rejected for three defects: protocol `client_version` had been conflated with installed `codex-cli` version; destructive state-root recreation was not bound to the exact configured profile/root and exact runtime manager; and nested permission validation rejected the root-owned mode-0644 SQLite/WAL files physically observed for exact Codex 0.144.6.

The first repair restored independent protocol-client identity, installed-version authority, manager-owned exact-root recreation, and exact-0.144.6 nested-file compatibility.

The first repair was then rejected for two additional defects: successful installed authority was cached across later child generations, permitting version/schema drift after restart; and state-root provision/open/recreate still relied on a pathname precheck that did not fully anchor mutation against ancestor substitution.

The second repair added per-new-generation installed-authority validation, removed the misleading caller-selectable `schema_sha256` constructor input, and moved state-root authority to descriptor-chain/no-follow traversal and descriptor-relative mutation.

The second repair was then rejected for two final authority gaps: repository/controller/additional protected paths were still primarily lexical authorities; and provision/recreate did not revalidate the current configured parent/root path binding after mutation before returning success.

The third repair closes both gaps. Runtime now requires explicit repository plus controller-storage authority, protected paths are descriptor/no-follow validated, physical endpoint aliases are rejected, and provision/recreate perform final current-path parent/root inode binding checks before success. Post-anchor ancestor and root-leaf substitution tests prove no false success and no foreign-tree mutation.

No remaining architect-blocking defect was found.

## Accepted P7.C3 authority

Every configured production profile now has an explicit persistent `CODEX_HOME` and a distinct explicit `isolated_state_root`. Profile/path representations remain redacted.

Runtime authority requires explicit repository and controller-storage protected boundaries. Profile homes, state roots, repository/controller/additional protected roots, and controller DB metadata are validated fail-closed through canonical path rules plus no-follow descriptor authority. State roots cannot overlap or alias protected product boundaries.

The isolated root layout is:

```text
<isolated_state_root>/
    .codexcontrol-state-root-v1
    sqlite/
    logs/
```

The root and top-level state directories are exact mode 0700, root-owned and non-symlink; the marker is root-owned mode 0600 and contains only bounded format/profile metadata. Nested Codex-created regular files/directories must remain root-owned, contained, non-symlink/non-special and not group/world writable; root-owned 0644 regular files are accepted because the enclosing state boundary is 0700.

Every new app-server child generation independently proves exact installed Codex authority before spawn. `clientInfo.version` remains the independent CodexControl protocol-client version. Exact installed authority remains `codex-cli 0.144.6` with accepted generated app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`. Version/schema/storage-capability drift fails before a new child process is started; reuse of the same already-READY child does not reprobe.

Child launch explicitly routes:

- `CODEX_HOME` to the persistent configured profile home;
- `CODEX_SQLITE_HOME` and `sqlite_home` to `<isolated_state_root>/sqlite`;
- `log_dir` to `<isolated_state_root>/logs`;
- `history.persistence="none"` for every accepted child.

The runtime manager owns opaque per-profile reservations under the same lock as acquire/start/READY publication/shutdown/unresolved ownership. A valid reservation blocks new runtime acquire/start, supports explicit shutdown and exact quiescence proof, and is required for manager-owned state-root recreation. Foreign/stale reservations and forged same-ID profile paths cannot authorize destructive work.

Provision and recreation are descriptor anchored and bounded to the configured root. They do not use unchecked recursive pathname deletion and do not mutate persistent profile homes, repository/controller boundaries, sibling roots, or credentials.

## Regression and effect evidence

Final executor evidence records:

- focused third-repair/C3/P7.C2 compatibility suites: pass;
- ordinary full regression: `1016` tests, `0` skipped, `0` failures, `0` errors;
- `compileall`: pass;
- `git diff --check`: pass;
- real Codex version processes: `0`;
- real app-server starts/business RPCs/thread deletes: `0`;
- Telegram calls: `0`;
- real Codex home/state-root mutations: `0`;
- credential content reads/copies/symlinks: `0`;
- production process mutation: `0`.

P7.C2 schema-v3 and delete/recovery/finalizer semantics were not modified by C3.

## Deferred proof-hardening

A host-level bind-mount-style physical ancestor alias cannot be fully exercised inside the zero-real-host-mutation C3 test boundary. C3 rejects lexical overlap, symlink aliases and exact physical endpoint aliases, and all destructive mutation remains bounded to already opened descriptors. A dedicated mount/namespace alias proof may be included in P7.C5 fake/security hardening if an isolated test namespace is available. This is not a C3 acceptance blocker and does not authorize weaker production configuration.

## P7.C4 next authority

P7.C4 is now the only executable correction slice. Its exact durable containment and cleanup composition is frozen by ADR-0044.

P7.C4 must compose accepted P7.C2 and P7.C3 without changing P1.9 external delete authority. `DELETE_CONFIRMED_PENDING_STORAGE` may finalize only after exact runtime reservation/quiescence, isolated-root recreation and a read-only persistent profile session/history residual gate. `DELETE_UNKNOWN` remains official UNKNOWN forever; local isolated-root containment is recorded separately and never creates a tombstone or authorizes finalization.

P7.C5, P7.C6, P8 and P9 remain blocked.

## Architect verdict

`P7C3_ARCHITECT_ACCEPTED`

Next action: execute P7.C4 only under ADR-0043, ADR-0044 and this acceptance.