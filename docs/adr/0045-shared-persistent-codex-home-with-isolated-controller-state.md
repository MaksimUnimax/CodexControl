# ADR-0045 — Shared persistent CODEX_HOME with CodexControl-isolated mutable state

Status: Accepted
Date: 2026-09-10

## Context

ADR-0043 correctly introduced a separate CodexControl-owned isolated state root for SQLite/log state, but it over-constrained the persistent `CODEX_HOME` by requiring CodexControl-exclusive ownership and by treating concurrent external Codex use of the same authenticated home as disallowed.

That exclusivity is not required by the V1 product contract and is not implemented by the accepted runtime manager. The accepted runtime manager owns only its own app-server children, routes their SQLite/log state into the configured isolated root, and its `ProfileReservation` prevents only CodexControl-managed acquire/start for that profile while local destructive isolated-root work is in progress.

The persistent `CODEX_HOME` remains the authority for authentication, configuration and session/rollout persistence. It is not a disposable storage root and CodexControl does not need exclusive ownership of it in order to own a distinct isolated SQLite/log root.

## Decision

A configured Codex profile may use an existing authenticated persistent `CODEX_HOME` that is concurrently used by other independent Codex processes or applications.

CodexControl does **not** claim exclusive ownership of the persistent home.

The isolation boundary is instead:

- the specific CodexControl-managed app-server child/generation;
- the profile-specific CodexControl-owned `isolated_state_root`;
- the CodexControl controller SQLite database;
- CodexControl process-local reservation/quiescence state.

Other Codex processes may continue using the same persistent `CODEX_HOME` while CodexControl runs, including during P7.C6, provided they do not use or mutate the CodexControl-owned isolated state root or controller database.

## Persistent CODEX_HOME authority

The persistent home must still be:

- explicitly configured;
- absolute and canonical;
- root-owned for the current server authority;
- not a symlink;
- not group/world writable;
- outside the CodexControl isolated state root and controller database boundary.

It may be shared with other Codex processes.

CodexControl must never:

- recursively delete or recreate the persistent home;
- kill, terminate, interrupt or signal unrelated Codex processes merely to obtain profile exclusivity;
- copy, move, symlink, migrate or inspect credential content;
- mutate persistent session/history files manually to manufacture hard-delete success.

The Codex child may naturally read the existing authenticated home through normal Codex behavior.

## Isolated mutable state authority

The `isolated_state_root` remains exclusive to one CodexControl profile/runtime authority and must not be used by another process or application.

For the CodexControl child, runtime routing remains:

- `CODEX_HOME=<configured persistent home>`;
- `CODEX_SQLITE_HOME=<isolated_state_root>/sqlite`;
- `sqlite_home=<isolated_state_root>/sqlite`;
- `log_dir=<isolated_state_root>/logs`;
- `history.persistence="none"` for that child generation.

Only the isolated state root is eligible for CodexControl descriptor-bounded destructive reset.

Before isolated-root reset, CodexControl must prove quiescence only for CodexControl-managed children that could use that exact isolated root. Concurrent unrelated Codex processes using the same persistent home are not part of this quiescence authority and are not stopped.

## Reservation scope

`ProfileReservation` is process-local CodexControl authority. It blocks CodexControl runtime acquire/start for the selected profile while cleanup owns the isolated root.

It is not a host-wide lock on `CODEX_HOME` and must not be interpreted as one.

No `/proc` scan may convert unrelated processes that merely share the persistent home into a reservation failure.

A process is relevant to destructive-root safety only if it can be proven or cannot be ruled out to use the exact CodexControl isolated root or controller storage boundary.

## Persistent residual scanning under sharing

The accepted persistent residual gate remains read-only and target-specific:

- `CODEX_HOME/sessions/**`;
- optional `CODEX_HOME/history.jsonl`;
- exact retained target `thread_id` as production attribution needle;
- test/real acceptance marker oracle remains separate.

Concurrent unrelated processes may create or mutate unrelated persistent-home artifacts while the scan is running. CodexControl must not stop those processes to make the scan quiet.

If concurrent filesystem activity causes a concrete scanner safety error, exact target ambiguity, unsafe symlink/ownership condition or other fail-closed scanner error, the local confirmed path remains pending. The remedy is not to kill unrelated processes or manually edit the shared home.

Ordinary unrelated activity that does not create target residuals or scanner safety errors is permitted.

## Hard-delete semantics under shared persistent home

The official `thread/delete` remains the only external Codex deletion authority for the exact target thread.

CodexControl local cleanup never manually deletes persistent session/history material. After exact `DELETE_CONFIRMED`, the production scanner proves no exact target-thread residual in the shared persistent home before finalization.

P7.C6 additionally uses a known synthetic marker as an acceptance oracle. Any known target marker residual is a P7.C6 failure even if unrelated Codex processes continue using the same home.

Shared-home activity does not weaken:

- one target thread / one delete budget;
- `DELETE_UNKNOWN` no-retry semantics;
- `DELETE_CONFIRMED_PENDING_STORAGE` durability;
- isolated-root physical erasure requirements;
- exact target residual proof.

## P7.C6 correction

P7.C6 may use the already authenticated configured home `/root/.codex_second` while other Codex processes also use that home.

The following are **not** blockers by themselves:

- another live Codex process with `CODEX_HOME=/root/.codex_second`;
- another process holding file descriptors under that persistent home;
- interactive or application use of the same persistent home.

P7.C6 must not kill or request termination of those processes.

The preflight must instead verify that no unrelated process uses the fresh C6-owned `isolated_state_root`, controller SQLite database, one-shot ledger or temporary working directory.

Mount/alias checks remain read-only and apply to exact protected boundaries, not to a requirement for persistent-home exclusivity.

## Baseline semantics under concurrency

P7.C6 must not require the entire shared persistent home to be byte-for-byte or inode-set stable while unrelated Codex processes are active.

The acceptance proof is target-specific:

- exact target thread residuals;
- exact known target marker residuals;
- no CodexControl manual persistent-home mutation;
- no CodexControl signal/kill effect on unrelated processes;
- isolated root and controller boundaries remain protected.

Unrelated persistent-home metadata changes caused by concurrent external activity are recorded as concurrent background activity and are not, by themselves, attributed to CodexControl.

## Supersession

ADR-0045 supersedes only the persistent-home exclusivity clauses of ADR-0043 and any downstream C6 contract language derived from them.

ADR-0043 remains authoritative for:

- isolated state routing;
- root ownership and overlap protection;
- confirmed-delete durability barrier;
- `DELETE_UNKNOWN` semantics;
- isolated-root reset;
- exact-version capability gates.

ADR-0044 and P7.C4 remain authoritative for local cleanup ordering and target residual scanning.

No production source change is required for this correction because the accepted `CodexRuntimeManager` reservation/quiescence authority already scopes itself to manager-owned children rather than all host processes sharing `CODEX_HOME`.
