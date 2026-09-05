# Current work authority

Date: 2026-09-05

## Accepted facts
- Repository: `MaksimUnimax/CodexControl`.
- Installed server-80 Codex authority: `codex-cli 0.144.6`.
- Installed app-server schema authority SHA-256: `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`.
- P1.1 accepted: `7f013ff2950bc185d6f0991c11960311961e53a7`.
- P1.2 accepted: `f3acf2d4cf8c793d0c576ca3cd576eb3d0513ab9`.
- P1.3 accepted: `7568f0b01b204b48676447db9c71ab847a0be5b2`.
- P1.4 accepted: `981b0c359f09e82354c50bb68eb3317d389a9c15`.
- P1.5 accepted: `e7851d813944d3326b7fd9317da9e21f216557fa`.
- P1.6 accepted: `de36b3ef3657a464b29ff2d17692fce5fc2b2388`.
- P1.7 accepted/proof HEAD: `bbd7445087dfb59185d49787d562637e282ba5aa`.
- P1.8 accepted after recovered repair: `6d8a07b5b95ef377cf60762f4475128bdf810b22`.
- P1.9 accepted: `95b2a42e47aaddae6ec9bcbaf9f0f879362d993e`.
- P1.10 accepted proof commit: `7b236f95df78a05073d67fe362ac9fff343d7c43`.
- P1 is complete through T0/T1/T2. T3 real Codex acceptance remains deferred to the later isolated real-Codex phase.
- ADR-0014 defines permissions approval semantics.
- ADR-0015 defines active-turn interrupt ownership/reconciliation.
- ADR-0016 defines destructive thread/delete response authority and partial-failure ambiguity.
- ADR-0017 defines the P2.1 SQLite storage kernel and schema-v1 boundary.

## P1 closing acceptance facts
- P1.10 was proof-only: no production source, version fixture or packaged manifest changed.
- T0 asserted the complete current capability set/readiness, finite status/error contracts, absence of `DELETE_REJECTED`, no embedded retry-policy fields, 512-character thread/turn identity boundaries, startup empty-turn interrupt exclusion and diagnostic redaction.
- T1 composed accepted adapters through `thread/start -> turn/start -> turn/interrupt -> existing P1.6 collector -> thread/delete`. Same-profile runtime acquisition was A, A, B: interrupt reused captured A without manager reacquire; delete later used current same-profile B. Exact request shapes, one notification consumer and one-call/no-retry behavior were asserted.
- T2 used only `/usr/local/bin/codex --version`, `app-server --help`, and fresh JSON-schema generation in isolated temporary HOME/CODEX_HOME. It confirmed `codex-cli 0.144.6`, aggregate SHA-256 `40c67e463e6170a8666b681caa4636a030e303cee94e7f0cc893fa8af7680466`, all ten committed P1 fixtures and the packaged capability manifest against the fresh installed authority.
- Accepted P1.10 executor counts: T0 6, T1 1, T2 4, full 248; compile/import/diff/security passed. No real model/list/thread/turn/approval/interrupt/delete business RPC occurred.
- The established P1.6 pending-task warning remains pre-existing test-hygiene debt. P1.10 introduced no new task leak.

## P2.1 exact architect authority
P2.1 is **SQLite storage kernel + schema-v1 bootstrap/migration + process lock + transaction primitive only**.

Binding source: `docs/adr/0017-sqlite-storage-kernel-and-schema-v1.md` plus `docs/DATA_MODEL.md`.

### Runtime/storage ownership
- Standard-library `sqlite3` only; do not add `aiosqlite` or another DB runtime dependency.
- One storage instance owns one persistent connection on one dedicated `ThreadPoolExecutor(max_workers=1)` worker. Connection creation, PRAGMAs, migrations, transactions and close all occur on that worker.
- Database path must be absolute/NUL-free. Parent must already exist and be a real directory. Parent, DB and sibling `<db>.lock` must not be symlinks.
- Existing DB/lock files must be regular files owned by the effective UID with no group/other permission bits. New DB/lock files are securely created `0600` before SQLite/locking use.
- Hold a non-blocking exclusive `fcntl.flock` on `<db>.lock` for the storage lifetime. A second owner fails closed rather than waiting.
- Connection PRAGMAs must be verified: foreign keys ON, WAL journal, 5000ms busy timeout, synchronous FULL, trusted schema OFF, manual transaction control, `sqlite3.Row` rows.
- Tests use temporary paths only. P2.1 must not create/open `/var/lib/codex-control` or any production state DB.

### Async transaction ownership
- Async storage operations submit synchronous callbacks to the dedicated DB worker.
- Read transaction: explicit `BEGIN DEFERRED`.
- Write transaction: explicit `BEGIN IMMEDIATE`.
- Success commits. Callback/DB failure rolls back before propagation/normalization.
- Once work is submitted to the DB worker, repeated public coroutine cancellation does not detach/cancel that exact DB operation. The same invocation remains attached until the exact commit/rollback result is known.
- No auto retry.
- Close is idempotent, rejects new operations once close ownership begins, waits for owned work, closes on the DB worker, releases `flock`, and cannot leave an unknown live connection because its caller is cancelled.
- Connection/cursor objects must not escape the worker callback API.

### Storage errors
Finite safe storage categories are equivalent to: `INVALID_PATH`, `INSECURE_PATH`, `LOCKED`, `OPEN_FAILED`, `SCHEMA_UNSUPPORTED`, `SCHEMA_INVALID`, `CLOSED`, `TRANSACTION_FAILED`. Generic rendering contains category only; no path, SQL, parameter/content, exception body, environment or secret.

### Schema/migration authority
- `SCHEMA_VERSION=1`.
- Durable `schema_migrations(version, migration_id, ddl_sha256, applied_at_ms)` plus `PRAGMA user_version`.
- Version 0 is accepted only for an empty/new DB. A non-empty unversioned DB fails `SCHEMA_INVALID`.
- Future/newer `user_version` fails `SCHEMA_UNSUPPORTED`.
- Existing v1 verifies exact migration ID/hash and required table/index names. P2.1 does not auto-repair/drop unknown schema state.
- Bootstrap is one explicit migration transaction; `user_version=1` only after v1 DDL/history row succeeds.
- Migration timestamp comes from an injected/testable millisecond clock.

### Schema-v1 business tables
P2.1 creates only the physical schema defined by ADR-0017 for: `controller_runtime`, `settings`, `dialogues`, `turn_jobs`, `transient_payloads`, `delivery_segments`, `ingress_updates`, `callback_actions`, `approvals`, `deletion_tombstones`, `errors`, plus `schema_migrations` and deterministic supporting indexes.

Important frozen points:
- at most one retained/live dialogue row through a constant unique live slot;
- `NO_DIALOGUE` is absence of a dialogue row;
- long-lived tables do not add prompt/response/raw Telegram JSON/command-output/auth columns;
- transient content is isolated in `transient_payloads`;
- approvals represent exact wire request ID type/value but do not make the reusable wire ID globally unique;
- deletion tombstone stores hashed thread identity rather than dialogue content;
- foreign-key behavior supports later architect-authorized local purge, but P2.1 exposes no repository method that performs that purge.

### P2.1 forbidden scope
No controller/settings/dialogue repository APIs; no legal state-transition methods; no ingress/callback dedupe logic; no job claims; no retention cleaner; no approval repository orchestration; no delete finalization; no crash/restart harness; no P3 application service; no Telegram; no deployment; no production DB.

## Execution authority
Codex must not self-start work from this document.

Only **P2.1 — SQLite storage kernel + schema-v1 bootstrap/migration + process lock + transaction primitive** is eligible for the next explicit implementation prompt.
