# P7.C3 isolated state runtime evidence

Date: 2026-09-09
Branch: `impl-p7-c3-isolated-state-runtime-2026-09-09`

## Lineage and authority

- Architect base SHA: `0637643518bfe45e471a0d777d2995b833e6bcb8`
- Architect base tree: `9f9c8a5ffa02098a8c9af15b904f0a6ede750493`
- Accepted predecessor: P7.C2 schema v3, migration `0003_confirmed_pending_storage`
- Accepted P7.C2 migration SHA-256: `cc4fe584962da3bdc13023d6361517cb858b64e16c2d0d38c3459741843b5eb4`
- Current schema remains `3`.
- Exact Codex authority remains `0.144.6`.
- Exact app-server schema authority remains
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.

ADR-0043 and all architect-owned authority files were left unchanged. This
slice does not implement P7.C4 cleanup or finalization composition.

## Architect repair

`INITIAL_CANDIDATE=0654ee1cbd70d4d6a6d5a317e948d2f08b2c081f`.
`INITIAL_ARCHITECT_VERDICT=REWORK_REQUIRED`.

`ARCHITECT_DEFECT_A=CLIENT_VERSION_CONFLATED_WITH_INSTALLED_CODEX_VERSION`.
`ARCHITECT_DEFECT_B=RECREATE_NOT_BOUND_TO_CONFIGURED_PROFILE_ROOT_AND_EXACT_MANAGER`.
`ARCHITECT_DEFECT_C=NESTED_PERMISSION_POLICY_REJECTED_ACCEPTED_EXACT_0_144_6_0644_STATE_FILES`.

The repair restores `client_version` as the independent CodexControl protocol
client identity. Runtime startup now validates the exact selected executable
through the injected testable version/installed-authority seam (the production
default is `CodexVersionProbe` bound to that executable), then binds the
accepted version-labelled manifest/schema to the static storage capability
authority. Startup fails before the app-server process factory for unavailable,
wrong-version, wrong-schema, or missing storage controls. Regression launch
tests use `client_version="0.1.0-test"` and prove that value is sent unchanged
in `initialize.params.clientInfo.version`; no real version process is used.

All state-root operations bind supplied profiles to the configured canonical
home/root pair. Destructive recreation is manager-owned: the exact manager
reservation token is checked under that manager's lock, quiescence is proven
for that manager, and only its configured root is passed to the descriptor-
relative filesystem primitive. Same-ID forged profiles, foreign managers,
released reservations, and active/starting/unresolved runtimes are rejected
without outside-root mutation.

Permission validation now distinguishes layers. Persistent homes reject only
group/world write (so root-owned `0755` is accepted and `0775`/`0777` are
rejected); the isolated root, `sqlite/`, `logs/`, and marker retain exact
`0700`/`0600` modes. Nested root-owned regular files and directories reject
group/world write but permit read bits. This explicitly preserves the accepted
P7.C1 physical evidence for exact installed `0.144.6`: `STATE_MAIN_SQLITE`,
`LOG_MAIN_SQLITE`, `LOG_SQLITE_WAL`, and `STATE_SQLITE_WAL` were each observed
as uid `0`, mode `0644`. Permanent regressions cover nested `0600`/`0644`,
rejection of `0664`/`0666`, and the top-level gates.

## Profile/configuration authority

`CodexProfile` now carries an explicit `isolated_state_root` in addition to
the persistent `codex_home`. Both paths are redacted in profile and server
configuration representations. Configuration rejects missing roots, malformed
or relative paths, NULs, duplicate canonical homes/roots, home/root equality,
ancestor-descendant overlap, cross-profile overlap, protected repository and
controller paths, and existing symlink aliases. No root is inferred from a
profile ID or current working directory, and no legacy configuration is
silently migrated.

Configured global protected paths are explicit: controller database path/root,
repository root, and additional protected roots. The runtime path authority
requires an explicit protected-root set before production child startup.

## Path/ownership and isolated-root authority

`IsolationPathAuthority` uses canonical absolute lexical paths and rejects
symlink components before metadata validation. Persistent homes must already
exist as root-owned private directories and are never created by runtime
acquire. They are checked without opening credential files or reading their
contents. Equality, ancestor, and descendant overlap is rejected across
profile home/root pairs and explicit protected paths.

The product-owned root is provisioned and validated as:

```text
<isolated_state_root>/
    .codexcontrol-state-root-v1
    sqlite/
    logs/
```

The root and both directories are root-owned, non-symlink, mode `0700`. The
marker is a bounded regular root-owned mode `0600` file containing only the
format version and safe profile identity. It contains no dialogue, thread,
prompt, response, credential, or environment data.

Root-level entries are exact. Recursive validation rejects symlinks, path
escape, foreign ownership, group/world writable entries, special files,
sockets, FIFOs, devices, malformed markers, and marker profile mismatch.
Regular Codex-created files/directories inside `sqlite/` and `logs/` are
accepted without requiring a future SQLite filename allowlist.

Provisioning, validation, and recreation are exposed by `IsolatedStateRoot`.
Recreation uses an opened directory descriptor with no-follow opens,
directory-relative unlink/rmdir operations, inode revalidation, and bounded
failure handling. It clears only the validated isolated root and restores the
marker/sqlite/log layout. It does not use unchecked recursive pathname
deletion and preserves parent, sibling, persistent-home, controller,
repository, and protected-root baselines.

Recreation requires the exact profile identity, an exclusive runtime
reservation, a positive quiescence proof, and a fresh full validation. It is
not connected to any dialogue state, `DELETE_CONFIRMED_PENDING_STORAGE`,
`DELETE_UNKNOWN`, finalizer, tombstone, residual scan, or startup delete
cleanup.

## Child routing and capability authority

The child environment preserves only the existing safe process allowlist plus
explicit product values:

- `CODEX_HOME` is the canonical persistent profile home;
- `CODEX_SQLITE_HOME` is the canonical isolated `sqlite/` directory.

Parent home/sqlite variables, logging controls, API keys, tokens, and unrelated
environment values cannot override or enter the child. The stdio app-server
launch uses deterministic `-c` overrides for `sqlite_home` equal to
`CODEX_SQLITE_HOME`, `log_dir` inside the isolated root, and
`history.persistence="none"`. No port, persistent user-config edit, or
credential-bearing config file is used.

`StorageRuntimeCapabilities` is distinct from the wire-RPC capability enum.
Runtime acquire fails before process-factory invocation unless the same exact
version/schema authority proves `CODEX_SQLITE_HOME`, `sqlite_home`, `log_dir`,
and `history.persistence=none`. Version mismatch, schema mismatch, and each
individual storage-control absence fail closed. No real capability probe was
executed in this slice.

Every production-enabled child launch explicitly sets
`history.persistence="none"`. There is no inherit/fallback mode. This does
not claim to disable session/rollout persistence; those artifacts remain in
later storage-proof scope.

## Runtime reservation and quiescence

`CodexRuntimeManager` owns opaque per-profile reservation objects under the
same manager lock that owns acquire/start, READY publication, shutdown, and
unresolved-process ownership.

- Reservation before acquire returns `profile_reserved` with zero spawn.
- A READY runtime may be reserved without being silently destroyed; new
  acquire attempts are blocked while explicit shutdown remains legal.
- READY publication rechecks reservation under the manager lock. A startup
  that loses to reservation is cleaned and reaped without READY publication.
- Concurrent reservation has one owner. Wrong or stale release tokens leave
  the live reservation unchanged.
- Valid release is non-starting; a later explicit acquire is required.
- `RuntimeQuiescenceProof` exposes only reserved/starting/ready/unresolved
  state booleans and reports quiescent only when all child ownership classes
  are absent.
- Shutdown-all includes reserved profiles and does not leak owned processes.

No dialogue or storage state is changed by reservation or release.

## Credential safety and effect accounting

P7.C3 does not provision authentication, copy or migrate credentials, create
auth symlinks, inspect credential contents, access keyrings, or place secrets
under the isolated root. All filesystem tests use temporary synthetic roots.
All launch tests use fake process factories. No real Codex process, model,
app-server business RPC, thread, turn, approval, interrupt, delete, read,
list, or Telegram operation was run.

```text
REAL_CODEX_VERSION_PROCESS_CALLS=0
REAL_CODEX_APP_SERVER_STARTS=0
REAL_CODEX_BUSINESS_RPC=0
MODEL_LIST_CALLS=0
THREAD_START_CALLS=0
THREAD_RESUME_CALLS=0
THREAD_DELETE_CALLS=0
THREAD_READ_CALLS=0
THREAD_LIST_CALLS=0
TURN_START_CALLS=0
INTERRUPT_CALLS=0
APPROVAL_RESPONSE_CALLS=0
TELEGRAM_CALLS=0
REAL_CODEX_HOME_MUTATION=0
REAL_ISOLATED_STATE_ROOT_MUTATION=0
REAL_CODEX_STORAGE_MUTATION=0
CREDENTIAL_CONTENT_READ=0
CREDENTIAL_COPY=0
CREDENTIAL_SYMLINK=0
PRODUCTION_PROCESS_MUTATION=0
```

## P7.C2 non-regression

The P7.C2 schema-v3 barrier and historical `DELETE_UNKNOWN` semantics remain
unchanged. Focused P7.C2 tests prove confirmed-pending retention, no local
purge/tombstone before later cleanup, zero external retry on replay, and
terminal no-retry `DELETE_UNKNOWN` recovery. C3 adds no state and does not
call any delete or finalization path.

## Tests

Focused C3/runtime: `59 tests, 0 skipped, 0 failures, 0 errors`.

Focused P7.C2 compatibility: `20 tests, 0 skipped, 0 failures, 0 errors`.

Repair-specific capability, version-probe, foundation, and permission/root
matrices also pass with zero failures or errors. The full repair regression is
`999 tests, 0 skipped, 0 failures, 0 errors`.

Required checks:

```text
PYTHONPATH=src python3 -m compileall -q src tests       PASS
git diff --check                                        PASS
```

Final ordinary full suite:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
    999 tests, 0 skipped, 0 failures, 0 errors
```

## Changed files

Production:

- `src/codex_control/domain.py`
- `src/codex_control/config.py`
- `src/codex_control/adapters/codex/capabilities.py`
- `src/codex_control/adapters/codex/runtime.py`
- `src/codex_control/adapters/codex/isolation.py`
- `src/codex_control/adapters/codex/__init__.py`

Tests:

- `tests/unit/test_p7_c3_isolated_state_runtime.py`

- `tests/unit/test_codex_runtime.py`
- existing fake/application test constructors updated to provide explicit
  synthetic isolated roots.

Evidence:

- `docs/evidence/p7c3/P7C3_ISOLATED_STATE_RUNTIME_EVIDENCE.md`

No architect authority, P7.C2 production/storage file, deployment file,
credential, real acceptance artifact, or unrelated product file was added.

## Second architect repair

`SECOND_ARCHITECT_REVIEW=REWORK_REQUIRED`.
`FIRST_REPAIR=a549e6f1f295a37f14a7833ede0233d94745555a`.

`ARCHITECT_DEFECT_D=SUCCESSFUL_INSTALLED_AUTHORITY_CACHED_ACROSS_RUNTIME_GENERATIONS`.
`ARCHITECT_DEFECT_E=STATE_ROOT_OPEN_AND_PROVISION_NOT_FULLY_DESCRIPTOR_ANCHORED_AGAINST_ANCESTOR_SUBSTITUTION`.

Installed authority is now probed and validated for every new app-server child
generation. A READY runtime is returned without reprobe; after complete
shutdown, the next generation reprobes the exact installed authority. Version
or schema drift therefore fails before the second app-server factory call.
The last successful manifest remains available only as sanitized diagnostic
state and never suppresses later validation. The storage capability source is
an immutable manager-owned `StorageRuntimeCapabilities` value.

`DEAD_SCHEMA_SHA256_CONSTRUCTOR_AUTHORITY=REMOVED`.
`CALLER_SCHEMA_STRING_CAN_CREATE_AUTHORITY=NO`.
The only production schema authority path is the installed exact-version probe,
the version-labelled accepted manifest, and `manifest.schema_sha256`.

Root, parent, and persistent-home validation now uses component-by-component
directory-descriptor traversal from `/` with `O_DIRECTORY`, `O_NOFOLLOW`, and
`O_CLOEXEC` where available. Provisioning uses mkdirat/openat-style
descriptor-relative operations. Recreate retains the manager reservation and
lock, validates the opened root and parent-entry inode binding before and after
mutation, and clears only through descriptor-relative no-follow operations.
Deterministic ancestor, root-leaf, and provision substitution regressions
reject replacement without mutating the foreign tree.

Second-repair focused results:

```text
FOCUSED_TESTS=128
FOCUSED_SKIPPED=0
FOCUSED_FAILURES=0
FOCUSED_ERRORS=0
PYTHONPATH=src python3 -m compileall -q src tests       PASS
git diff --check                                        PASS
FULL_TESTS=1008
FULL_SKIPPED=0
FULL_FAILURES=0
FULL_ERRORS=0
```

The one ordinary full regression was run as:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

All installed-authority tests use injected fake manifests and all runtime
launch tests use fake process factories. No real Codex process, app-server
business RPC, thread/delete operation, Telegram call, credential read/copy/
symlink, or production process mutation occurred. P7.C2 schema version,
migration hashes, delete orchestration, and finalization files remain
unchanged.
