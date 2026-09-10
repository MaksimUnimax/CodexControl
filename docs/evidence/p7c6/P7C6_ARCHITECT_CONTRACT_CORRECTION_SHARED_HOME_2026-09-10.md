# P7.C6 architect contract correction — shared persistent CODEX_HOME

Status: **BINDING / TAKES PRECEDENCE**
Date: 2026-09-10

This correction supersedes the persistent-home exclusivity and host-wide process-quiescence clauses in `P7C6_ARCHITECT_EXECUTION_CONTRACT_2026-09-10.md`.

Authority: ADR-0045.

## Corrected profile model

P7.C6 SHALL use the existing authenticated configured persistent home:

`/root/.codex_second`

That home is permitted to be concurrently used by other Codex processes/applications.

No CodexControl-exclusive dedication declaration is required.

The following are not blockers by themselves:

- live Codex processes with `CODEX_HOME=/root/.codex_second`;
- open file descriptors under `/root/.codex_second` held by unrelated Codex processes;
- interactive or application activity using the same persistent home.

The prior finite blocker `P7C6_LIVE_OR_AMBIGUOUS_CODEX_HOME_OWNER` is retired as an architectural gate when it is based only on shared persistent-home use.

## No process termination

P7.C6 MUST NOT kill, terminate, interrupt, signal or request the shutdown of unrelated Codex processes in order to make the persistent home exclusive or quiet.

The harness may stop/reap only the app-server children it created and owns through its own `CodexRuntimeManager`.

## Isolation/quiescence gate

The destructive local boundary remains the fresh C6-owned isolated state root, not the persistent home.

Before any isolated-root reset, require that no unrelated process uses the exact C6-owned:

- isolated state root;
- `sqlite/` subtree;
- `logs/` subtree;
- synthetic controller SQLite;
- one-shot/recovery ledger;
- temporary working directory.

CodexControl `ProfileReservation` and quiescence cover only CodexControl-managed app-server children for that exact profile/root.

Concurrent unrelated processes that share `CODEX_HOME` do not violate this gate.

## Installed/runtime routing

Unchanged:

- executable `/usr/local/bin/codex`;
- exact installed version `codex-cli 0.144.6`;
- exact app-server schema SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`;
- child `CODEX_HOME=/root/.codex_second`;
- child `CODEX_SQLITE_HOME=<fresh isolated root>/sqlite`;
- `sqlite_home=<same>`;
- `log_dir=<fresh isolated root>/logs`;
- `history.persistence="none"` for the C6 child.

## Read-only process/mount preflight

Process inspection is diagnostic only for shared-home ownership.

Do not stop because another process uses `/root/.codex_second`.

Stop only when another process can be proven or cannot be ruled out to use a C6-owned destructive/protected boundary listed above, or when path/mount aliasing makes those boundaries unsafe.

Mount inspection remains read-only. No privileged mount/namespace mutation is authorized.

## Persistent-home measurement under concurrency

P7.C6 production exact-thread gate and independent marker oracle remain target-specific.

Measure:

- exact target thread ID;
- known C6 target markers;
- scanner/proof errors.

Do not require the complete shared `sessions/**` tree or `history.jsonl` metadata to remain globally stable while other Codex processes are active.

Unrelated background changes are not attributed to CodexControl merely because they occur during the run.

Hard blockers remain:

- target thread residual after confirmed delete;
- known target marker residual after confirmed delete;
- scan/proof error that prevents safe target conclusion;
- unsafe alias/use of the C6 isolated/controller boundary;
- `DELETE_UNKNOWN` or confirmed-pending final state.

## Real-effect budget

The previous stops consumed zero authenticated business RPCs and therefore consumed none of the one-shot budget.

The existing one-thread/one-delete budget remains unchanged.

## Repository scope

No production source change is authorized by this correction. The accepted runtime already scopes reservation/quiescence to manager-owned children.

P7.C6 may continue from a fresh branch off the architect main containing ADR-0045 and this correction.

## Reporting correction

Final C6 evidence must include:

- `PERSISTENT_HOME_MODE=SHARED_AUTHENTICATED`;
- `UNRELATED_SHARED_HOME_PROCESSES_ALLOWED=YES`;
- `UNRELATED_PROCESS_TERMINATION_CALLS=0`;
- `ISOLATED_ROOT_EXTERNAL_USERS=0`;
- `CONTROLLER_DB_EXTERNAL_USERS=0`;
- exact target thread/marker pre/post residual counts.

It must not report shared-home process presence as a failure by itself.
