# CODEXCONTROL P7.C1 STORAGE ISOLATION DISCOVERY REPORT

Discovery date: 2026-09-09
Repository: `MaksimUnimax/CodexControl`
Issue: `#39` (OPEN)
Binding authority: Issue #39 comment `5597864058`
Architecture branch: `arch-p7-c1-storage-isolation-2026-09-09`
Frozen base / `origin/main`: `66f094f3592467d16382482f133b288d521c4873`
P7.C1 class: read-only architecture/discovery only

## 1. Scope and frozen predecessor

Issue #38 remains OPEN and P7 remains NOT ACCEPTED. The rejected predecessor
commit is `5aac49bd1b8a349343db52071520beed7f95592d`. The frozen predecessor
facts are preserved exactly:

- exactly one official P1.9 `thread/delete` was dispatched;
- `OFFICIAL_DELETE_STATUS=DELETE_UNKNOWN`;
- post-unknown physical classification is
  `DELETE_UNKNOWN_WITH_MATERIAL_RESIDUAL`;
- pre-delete synthetic marker matches were 8 and post-unknown material
  matches were 5;
- the P7 session/history artifact is absent and the unrelated-session
  baseline remains preserved;
- no retry, read/list reconciliation, notification guessing, or manual Codex
  store surgery occurred.

This report refines physical provenance and capability boundaries only. It
does not reconcile `DELETE_UNKNOWN`, reinterpret it as success, or weaken
ADR-0008, ADR-0016, ADR-0042, or accepted P3.5 semantics. ADR-0043 is not
created here.

## 2. Safety boundaries

All inspection in this slice was read-only. The retained P7 recovery record
was used only in memory to obtain the thread identity and recover the two
marker byte strings by their already frozen SHA-256 values. No credential
contents were read or emitted. The Codex homes were not changed.

The installed authority checks were:

- `/usr/local/bin/codex` resolves to a root-owned, mode-0755 native executable;
- installed version: `codex-cli 0.144.6`;
- fresh synthetic-home `app-server generate-json-schema` succeeded;
- generated aggregate schema SHA-256:
  `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- installed native binary SHA-256:
  `a31ae9450a26216eb1e7c53102fd42123dd675974310b0e2ca3aa4cb622a2c15`.

No real app-server was started. No normal writable SQLite connection was
used. SQLite logical inspection used `immutable=1`, `mode=ro`, and
`PRAGMA query_only=1`; byte-level classification was performed independently
from raw main-file and WAL bytes. The exact upstream release tag
`rust-v0.144.6` (commit `5d1fbf26c43abc65a203928b2e31561cb039e06d`) was used
only to interpret installed static evidence, never as a substitute for the
installed binary.

## 3. Residual provenance

The selected retained profile is represented below as `CODEX3_HOME`; raw
absolute paths and raw basenames are intentionally omitted. The scanner
visited 7,909 regular files under that home, followed no symlinks, and had
`SCAN_ERRORS=0`. Four regular files contained the retained thread identity or
one of the frozen markers. Each path hash is SHA-256 of the relative path
string under `CODEX3_HOME`.

| path SHA-256 | size | uid/mode | link/type | path-shape enum | physical family | matches |
|---|---:|---|---|---|---|---|
| `068369c755ebd6bda244cb0d41585a1a2fec055c76a3f41b9e4c2fc1e182e9b4` | 1,400,832 | 0 / 0644 | regular | `STATE_MAIN_SQLITE` | SQLite main file | thread ID ×14 |
| `b732fe159f1de2357b45ea573986506020451db3bfd945d195d79a6c7cc008b3` | 59,977,728 | 0 / 0644 | regular | `LOG_MAIN_SQLITE` | SQLite main file | thread ID ×753; marker 1 ×1; marker 2 ×1 |
| `3564bd89c49138e3cfc99f836d8477286505adbfcda7693152691cd17417d293` | 1,273,112 | 0 / 0644 | regular | `LOG_SQLITE_WAL` | SQLite sidecar | thread ID ×1,682; marker 1 ×2; marker 2 ×1 |
| `09aaadbdfcdd9fc0ca65136e94062a23bbd40cde73c1a3344700f6d793ef0a12` | 1,376,112 | 0 / 0644 | regular | `STATE_SQLITE_WAL` | SQLite sidecar | thread ID ×246 |

No matching `STATE_SQLITE_SHM`, `LOG_SQLITE_SHM`, `SESSION_ROLLOUT`,
`JSONL_HISTORY`, `CACHE_FILE`, symlink, or unknown regular file was found.
The P7 session/history artifact remains absent.

### Historical `OTHER` classification

`OTHER` is **`SQLITE_SIDECAR`**, not a distinct logical store. All 1,928
historical `OTHER` thread-ID matches and all three historical `OTHER` marker
matches are accounted for by the two `*-sqlite-wal` physical sidecars above.
The predecessor classifier used `Path.suffix`, so SQLite sidecars were not
recognized as state/log database families. The two marker matches previously
reported in `STATE_DB` are physically in the SQLite main file classified above
as `LOG_MAIN_SQLITE`; the frozen historical category remains true as a
classifier observation and is not being reinterpreted as delete success.

## 4. SQLite live/free/WAL classification

The two marker byte strings were recovered only by matching their frozen
hashes:

- marker 1: expected hash
  `3dfc371b18783c1bd53f140ea7c07b203a809dc19a45983410491afe024b395e`;
- marker 2: expected hash
  `4b81a69358ebb2ae8d1bc6c5bff68d2fa80910819526461254a7a0357eee12bc`.

Raw SQLite page parsing found both markers in one `LOG_MAIN_SQLITE` page of
the main database, in the page's unallocated region, not in a live B-tree
cell. The same marker bytes also occur in WAL frames. No marker was found in
freelist or SHM metadata.

| byte class | marker 1 | marker 2 | classification |
|---|---:|---:|---|
| main-file unallocated page region | 1 | 1 | `UNALLOCATED_PAGE_REGION` |
| WAL frame for the retained page/other page | 2 | 1 | `WAL_FRAME` |
| live B-tree payload | 0 | 0 | not proven / not present |
| freelist page | 0 | 0 | not present |
| SHM metadata | 0 | 0 | not present |

The thread-ID bytes have a different physical distribution:

| file family | total | `LIVE_B_TREE_PAYLOAD` | `UNALLOCATED_PAGE_REGION` | `FREELIST_PAGE` | `WAL_FRAME` |
|---|---:|---:|---:|---:|---:|
| state main SQLite | 14 | 12 | 2 | 0 | 0 |
| log main SQLite | 753 | 315 | 437 | 1 | 0 |
| state WAL | 246 | 0 | 0 | 0 | 246 |
| log WAL | 1,682 | 0 | 0 | 0 | 1,682 |

The immutable SQLite inspection structurally proved live rows without
emitting values. In the state database, one table had one exact thread-ID row
and a second text column in that table also contained the identity; table and
column hashes were recorded only as:

- table hash `4cc500db62ede737f8f7a8c83c02b5fc5cbcebf26bffc48fb49b4540ffc67306`;
- exact-match column hash
  `a56145270ce6b3bebd1dd012b73948677dd618d496488bc608a3cb43ce3547dd`;
- second containing-column hash
  `421370620edb21f71d7253922086cc4c625cdb86bb5a45605457c5c3978aaff7`;
- aggregate table row count: 37.

In the log database, one table contained eight rows with the thread identity
embedded in a text value; table hash
`98f38f12db221a8cf8ca7aadfdcd759b01d52eb4ebb3eedbb2d97e92805c6960` and
column hash `1d64f59415ee5af9fbc6724ad46d5a3dd3f279654590cd2f4243164fbf3e8780`.
This proves live identifier metadata exists in SQLite B-tree payload. It does
not prove that marker content is live logical data: the marker bytes were
found only in unallocated page bytes and WAL frames.

## 5. Installed 0.144.6 storage capabilities

The installed binary contains the exact configuration vocabulary
`CODEX_SQLITE_HOME`, `sqlite_home`, `log_dir`, and `history`. Fresh synthetic
home probes of the installed binary accepted `sqlite_home`, `log_dir`, and
`history.persistence="none"` with exit 0. Exact installed release source
inspection was used only as supplementary interpretation; the local binary
and local probes are the authority.

| capability | exact installed result | evidence class | finding |
|---|---|---|---|
| `CODEX_SQLITE_HOME` | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Environment-selected SQLite root is present in the installed config/runtime vocabulary and accepted in a fresh-home probe. |
| `sqlite_home` | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Configurable SQLite state root; current state DB families are under this root. |
| state DB path control | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | `sqlite_home` controls the SQLite state runtime. |
| `log_dir` / log-file path control | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Text/TUI log directory is configurable; this is distinct from the SQLite `logs_*` database, which follows the SQLite state root. |
| independent log-DB root | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | The independent control is the shared `sqlite_home` root, not a separate log-DB knob. |
| session/rollout path control | `NOT_FOUND_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | No installed path control was found for the rollout/session tree; rollout files remain under `CODEX_HOME/sessions`. |
| history persistence disable | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | `history.persistence=none` is supported for `history.jsonl`. This does not disable dialogue rollout persistence. |
| log persistence disable | `NOT_FOUND_EXACT_0_144_6` | `BINARY_STRING` | No exact installed disable switch for SQLite/text log persistence was found. `log_dir` relocates logs; it is not a disable control. |

Consequently, 0.144.6 can separate SQLite/log state from profile/auth
configuration, but cannot independently relocate the dialogue-bearing
session/rollout tree. `history.persistence=none` reduces global composer
history only; it is not a hard-delete substitute.

## 6. Installed 0.144.6 auth capabilities

The installed `codex login --help` exposes `--with-api-key` and
`--with-access-token`. The installed binary exposes
`cli_auth_credentials_store`, keyring, ephemeral storage, and external
bearer-token vocabulary. The current `codex2` config declares the non-secret
mode `file`; no auth file contents were read.

| capability | exact installed result | evidence class | finding |
|---|---|---|---|
| `auth_credentials_store` | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `STATIC_HELP` | Configurable CLI auth storage mode is installed. |
| file auth mode | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Stores auth at `CODEX_HOME/auth.json`; the current codex2 mode is `file`. |
| keyring auth mode | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Direct keyring and encrypted-secrets/keyring-backed forms are present. |
| auto auth mode | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | Keyring when available, with file fallback. |
| ephemeral auth mode | `SUPPORTED_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | In-memory current-process storage; restart requires fresh provisioning. |
| external token/API-key authentication | `SUPPORTED_EXACT_0_144_6` | `STATIC_HELP` + `BINARY_STRING` | API-key and access-token login inputs are supported; bearer-provider vocabulary is also installed. |
| independently configurable auth path | `NOT_FOUND_EXACT_0_144_6` | `BINARY_STRING` + `OTHER_STATIC` | File auth is fixed below `CODEX_HOME`. Keyring identity is derived from the canonical `CODEX_HOME` path, so a new home is a different auth identity. |

The safe auth conclusion is therefore: a dedicated profile home cannot assume
credential sharing with another home. It requires independent provisioning,
an external secure credential authority, or an explicitly approved keyring
identity policy. Credential copying, symlinking, and migration are not safe
or authorized correction mechanisms. The API-key/access-token login flags
read their input from stdin; they do not by themselves promise non-persistence.
Selecting the installed `ephemeral` mode keeps the credential in process
memory and requires reprovisioning after restart. The installed external
bearer-provider mechanism can obtain a token from an environment/provider
command without placing that token in the dialogue-bearing storage root, but
it is not an independently configurable auth path and no token value was read.

## 7. Exact storage path map

Path hashes below hash the actual sanitized path string; the absolute host
prefix is never emitted. `THREAD_DELETE_TARGET` means the family must be in
the measured deletion proof, not that every file is independently deleted by
the official RPC.

| family | root source | path hash | basename/path shape | sensitivity | delete scope |
|---|---|---|---|---|---|
| AUTH | `CODEX_HOME` | `11251eb7d6e48589dd280d33b269178cd0fd5b4ff402b4551941782cb2d98db6` | `AUTH_JSON` | `AUTH_SECRET` | `NOT_TARGETED` |
| CONFIG | `CODEX_HOME` | `4d302b6565d42a457bd8c50ae3d47f40246de1872d54272fec52467f6d7c0048` | `CONFIG_TOML` | `UNKNOWN` | `NOT_TARGETED` |
| SESSION_ROLLOUT | `CODEX_HOME` | `cbd50f6c05f2c0b6a4373a5c24de476b103ee460cd7253f0dcb298adb6773b37` | `SESSION_ROLLOUT` | `DIALOGUE_CONTENT` | `THREAD_DELETE_TARGET` |
| HISTORY_INDEX | `CODEX_HOME` | `a0d2157c528b868e01d3b17d49dcaa31f5ddf519a9dd916e305d883a3512c6b1` | `JSONL_HISTORY` | `DIALOGUE_CONTENT` | `NOT_TARGETED` |
| STATE_DB | `SQLITE_HOME` (defaults to `CODEX_HOME`) | `c656161a811c41e1fbb943e84269a547be69f08df7aa7162ec4096eb360c841f` | `STATE_MAIN_SQLITE` | `IDENTIFIER_METADATA` | `THREAD_DELETE_TARGET` |
| STATE_DB_WAL | `SQLITE_HOME` | `1268eb16292d277121356f26775954f4a1f79fe7d36454aa0b79b9bbf6094228` | `STATE_SQLITE_WAL` | `IDENTIFIER_METADATA` | `THREAD_DELETE_TARGET` |
| STATE_DB_SHM | `SQLITE_HOME` | `78c476e01b62c09bb5862b8b517453897dd51eb50f5b5e74f3aab8232b7ab924` | `STATE_SQLITE_SHM` | `IDENTIFIER_METADATA` | `THREAD_DELETE_TARGET` |
| LOG_DB | `SQLITE_HOME` | `db01ced79a13150c38e63334b31e5c9b1c961837dd844a48a533f680b9472515` | `LOG_MAIN_SQLITE` | `DIALOGUE_CONTENT` | `NOT_TARGETED` |
| LOG_DB_WAL | `SQLITE_HOME` | `183f8cc5bde7d868dfb11c0cdd1a69a5e79a81a0fe1eb6a87f318ed274cd9f30` | `LOG_SQLITE_WAL` | `DIALOGUE_CONTENT` | `NOT_TARGETED` |
| LOG_DB_SHM | `SQLITE_HOME` | `020c2b7a60f63e24c453099756b430edb013bd7b8499f5c9628d546ded1fe864` | `LOG_SQLITE_SHM` | `DIALOGUE_CONTENT` | `NOT_TARGETED` |
| CACHE | `CODEX_HOME` | `b2501ca730315b1d9d0131e9f2d893acc7b55943a837f6179eeb5b406f5c8c40` | `CACHE_FILE` | `UNKNOWN` | `NOT_TARGETED` |
| OTHER_PERSISTENT | `CODEX_HOME` | `78ab9e5221a93af73759d3e24e8d52a8fa3bf2538d3254a4c852ce5c7192c9bd` | `UNKNOWN_REGULAR` | `UNKNOWN` | `UNKNOWN` |

The exact P7 residual matched no session, history, cache, or SHM file. That
absence is evidence about this retained run only; it is not a general claim
that those families are safe to omit from a future proof.

## 8. Current profile sharing risk

The safe metadata classification is:

| profile alias | classification | metadata basis | risk |
|---|---|---|---|
| `codex2` | `INTERACTIVE_SHARED` | 3 session-rollout files, 4,996,343-byte global history, 16 SQLite-family files, and live exact-home Codex owners | High. Whole-root destruction could affect unrelated dialogue/auth material. P7 must not use it while ownership is ambiguous. |
| `codex3` | `CODEXCONTROL_DEDICATED` | 0 session-rollout files, no live exact-home owner, retained P7 state/log families, and the selected P7 recovery identity | Lower current sharing evidence, but not a proof of permanent exclusive ownership. Future runtime must enforce product ownership and fail closed on any unexpected owner. |

No session was attributed to a person. The `codex2` live-owner result is also
why it is not a safe volatile-root candidate. The residual in `codex3` proves
that “dedicated” must mean a separately owned topology, not merely a different
directory name.

## 9. Candidate topology matrix

| topology | storage/auth shape | `DELETE_CONFIRMED` viability | `DELETE_UNKNOWN` behavior | disposition |
|---|---|---|---|---|
| A. Shared existing profile home | Existing profile, SQLite, logs, sessions, and auth remain shared | Unsafe to claim whole-root proof; unrelated material cannot be bounded | Cannot destroy or repair shared storage; retain UNKNOWN and residual | Reject for production hard delete |
| B. Dedicated CodexControl profile home + separate disposable SQLite/log root | Persistent dedicated profile/auth/config; `sqlite_home` and `log_dir` point to product-owned volatile state | Viable conditionally: official confirmation, session scan, local purge, and bounded volatile-root cleanup must all pass | Volatile-root containment may be completed only under the whole-root rule; official authority remains UNKNOWN and profile-session residual remains unresolved | Viable conditional topology |
| C. Per-dialogue disposable `CODEX_HOME` | New home for every dialogue; auth identity changes with home | Requires independent credential provisioning or external auth; no credential copying is allowed | Root containment can be bounded, but UNKNOWN remains UNKNOWN and restart/auth overhead is high | Not selected under current authority |
| D. Crypto-erasure/encrypted dialogue state | Encryption/crypto-erasure layer not supplied by installed 0.144.6 controls | Architecture-only; key destruction is not currently measured Codex deletion proof | Could be containment only, never automatic reconciliation | Insufficient evidence; no installation now |
| E. Product semantic downgrade | Treats residual/UNKNOWN as success or weakens ADR-0008 | `CONFLICTS_ADR_0008=YES` | Violates frozen safety state machine | Forbidden |
| F. Codex version upgrade | Change installed authority before redesign | No upgrade is required by the discovered controls | Upgrade cannot be used to reinterpret this UNKNOWN result | Not required; retain capability gate |

## 10. `DELETE_CONFIRMED` lifecycle

The future design for topology B must keep the official and local authorities
separate:

1. Admit deletion only from accepted P3.5 readiness and record the exact
   profile/thread binding.
2. Quiesce only the product-owned CodexControl runtime and app-server, with
   an ownership check; do not touch unrelated processes.
3. Dispatch exactly one official `thread/delete` and require the schema-valid
   success response. This is the only `OFFICIAL_DELETE_AUTHORITY`.
4. On `DELETE_CONFIRMED`, purge CodexControl transient dialogue/job/delivery
   state and remove the binding through accepted P2.5/P3.5 semantics.
5. Scan the dedicated profile's session/rollout and all volatile SQLite,
   WAL/SHM, log, cache, and other persistent families for content and active
   identifiers. Require zero scan errors, zero material residual, and no
   unrelated pre-existing artifact removal.
6. Destroy and recreate a volatile SQLite/log root only when it is provably
   CodexControl-owned, contains no unrelated thread/dialogue/application,
   contains no credential that must survive, has no global profile authority,
   is fully stopped, and is bounded to the exact root. This is cleanup after
   confirmation, not the source of confirmation.
7. Retain only the accepted bounded non-content controller tombstone and
   sanitized error metadata. Do not create a second permanent transcript.
8. Remove the root-only recovery identity only after all gates pass.

The persistent dedicated profile/auth/config root survives this lifecycle
unless a separately approved profile decommission operation proves that it is
also product-owned and credential-safe to destroy.

## 11. `DELETE_UNKNOWN` lifecycle

For every dispatched non-success, including the frozen P7 result:

- `OFFICIAL_DELETE_AUTHORITY=UNKNOWN` remains durable;
- no retry, second delete, `thread/read`, `thread/list`, notification guess,
  or local purge is allowed;
- the binding and recovery identity remain retained;
- physical scanning is forensic/containment evidence only and cannot promote
  the result to `DELETE_CONFIRMED`.

Topology B may, in a future separately authorized recovery path, stop the
product-owned runtime and destroy/recreate only the exact volatile SQLite/log
root if every whole-root destruction condition is proven. If so, report the
separate fact:

`LOCAL_ISOLATED_STORAGE_CONTAINMENT=COMPLETED`

That fact must coexist with:

`OFFICIAL_DELETE_AUTHORITY=UNKNOWN`

It is not reconciliation, does not permit local tombstone finalization, and
does not erase session/rollout material that remains in the persistent
profile root. A crash or restart must recreate the volatile root without
redispatching delete and without executing delayed work.

## 12. Version-upgrade analysis

`UPGRADE_REQUIRED=NO` for the selected conditional topology. Installed
0.144.6 already proves the minimum storage controls needed for the proposed
correction: `CODEX_SQLITE_HOME`/`sqlite_home`, `log_dir`, and
`history.persistence=none`, plus the required auth modes and external token
inputs.

The version gate remains mandatory. A future implementation must fail closed
unless the exact installed version independently proves:

- an independently owned SQLite state/log root;
- explicit log relocation;
- a documented choice for global history persistence;
- persistent profile/auth ownership separate from the volatile root;
- official delete confirmation and a measurable residual gate.

No invented minimum upgrade version is proposed. Upgrade is required only if
one of those capabilities is absent or behavior changes in the exact binary
selected for implementation.

## 13. Recommended topology

The one permitted final architecture recommendation is:

`RECOMMEND_DEDICATED_HOME_AND_ISOLATED_STATE_ROOT`

Use a dedicated CodexControl-only profile home, never shared with interactive
CLI/Desktop workloads, with credentials/configuration kept in that persistent
profile authority and `sqlite_home`/`CODEX_SQLITE_HOME` plus `log_dir` directed
to a separately owned disposable state/log root. Disable global
`history.jsonl` persistence where product-compatible, but continue to measure
the session/rollout tree because that control does not move or disable it.

This recommendation is conditional on the ADR-0043 freeze defining the exact
ownership, crash, confirmation, UNKNOWN-containment, and evidence gates. It is
not implemented by P7.C1.

## 14. Proposed correction slices

These are proposals only; none was executed.

| slice | production paths | test scope | migration | real-effect requirement | acceptance gate |
|---|---|---|---|---|---|
| P7.C2 profile/configuration model | Codex runtime/profile configuration and fail-closed capability gate | Fake config resolution; reject shared/ambiguous homes; verify exact 0.144.6 knobs | No credential migration or data migration; existing homes remain outside the new path | None | Architect-frozen topology and exact capability manifest |
| P7.C3 state-root lifecycle/ownership | Root creation, ownership manifest, `sqlite_home`/`log_dir` binding, crash-safe recreation | Fake ownership, crash, restart, foreign-file, and root-boundary cases | New product-owned root only; no copying/symlinking credentials | None | Exact-root destruction predicates proven without mutation of existing homes |
| P7.C4 delete containment/recovery | Confirmed/unknown orchestration around P3.5/P1.9 and volatile-root containment | Separate confirmed and unknown state-machine matrices; no retry/read/list; recovery after crash | Preserve durable UNKNOWN and bindings; no local purge on unknown | None in fake tests | Architect approval of evidence gate and containment labels |
| P7.C5 fake hard-delete acceptance | Application/storage proof adapter boundary | Marker/path-family residual matrix, WAL/SHM, unrelated baseline, auth separation, no duplicate transcript | No migration | None | Full fake acceptance green with real gates disabled |
| P7.C6 renewed isolated real T3 | Opt-in acceptance harness only; no production source change unless separately opened | One new isolated thread, exact confirmation, full before/after scan | No credential copy; independent provisioning only | Exactly one separately authorized real proof | `DELETE_CONFIRMED`, zero material/active-store residual, baseline preserved, architect review |

P8 remains blocked until P7.C6 is independently accepted under the frozen
architecture. P9 is also not started.

## 15. Remaining unknowns

- The exact internal reason for the retained P1.9 `DELETE_UNKNOWN` was not
  persisted as a safe numeric/error diagnostic; this report does not infer it.
- The current scan proves physical byte classes, but does not reconstruct or
  emit the marker-bearing log records.
- The full installed behavior of every future `sqlite_home`/`log_dir`
  combination was not exercised against a real app-server; no real Codex
  business effect was authorized in this slice.
- Session/rollout relocation and log-persistence disabling controls were not
  found in exact installed 0.144.6 static capability evidence.
- Keyring availability and OS policy on a future dedicated home were not
  tested; no keyring was accessed.
- `codex3` has no current session-rollout files and no exact-home live owner,
  but permanent exclusive ownership still requires a future runtime gate.
- No conclusion is made about crypto-erasure, filesystem snapshots, backups,
  or storage outside the selected profile root.

## 16. Security/read-only attestation

The following accounting is exact for this P7.C1 run:

```text
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
CODEX_STORAGE_MUTATION=0
CREDENTIAL_CONTENT_READ=0
CREDENTIAL_COPY=0
PROCESS_MUTATION=0
P8_STARTED=NO
P9_STARTED=NO
```

No production source, `tests/**`, ADR, roadmap, current-work, decisions,
configuration, deployment file, or retained Codex store was modified. The
only intended repository output is this evidence file. The evidence-only
commit SHA and remote read-back are recorded by the final Git handoff because
the SHA cannot be embedded in its own content without creating a second
commit.
