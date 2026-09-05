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
- P1 is complete through T0/T1/T2; T3 real-Codex acceptance remains deferred.
- P2.1 accepted after two repair reviews: `61301fd25ff7253693f367664ce99e13dfc88446`.
- ADR-0017 defines the secure SQLite kernel/migration boundary.
- ADR-0018 freezes exact schema-v1 physical SQL and migration identity.
- ADR-0019 defines P2.2 core repository semantics.

## P2.1 accepted storage facts
- Standard-library `sqlite3`; one persistent connection on one dedicated `ThreadPoolExecutor(max_workers=1)` worker; default `check_same_thread=True`.
- Absolute/secure effective-UID-owned database + `.lock`, exact `0600`, symlink rejection, non-blocking lifetime `flock` and fail-closed second owner.
- Verified connection authority: foreign keys ON, WAL, busy timeout 5000ms, synchronous FULL, trusted schema OFF, explicit transactions and `sqlite3.Row` rows.
- Reads use DEFERRED + query-only authority; writes use IMMEDIATE. Once submitted, repeated public cancellation remains attached to the exact DB operation. No automatic retry. Close is owned/idempotent.
- Normal repository callbacks cannot take over transaction/savepoint control, mutate read transactions, set persistent PRAGMAs, ATTACH/DETACH another DB, mutate schema/migration authority, or return direct/nested SQLite/lazy resources. Connection row-factory/isolation invariants are checked/restored.
- Storage errors are finite and redact path/SQL/content/exception text.
- `SCHEMA_VERSION=1`, migration `0001_initial_state`, canonical DDL SHA-256 `b94122bec2188fa09066ae53dd08b4655462a0e69f7a975511601465300ecd9c`.
- Physical schema exactly matches ADR-0018: 12 user tables and 14 explicit indexes. Empty-v0 bootstrap only; v1 reopen verifies migration/hash/object/SQL authority and does not repair drift.
- Accepted proof counts: P2.1 unit 8, integration 31, full `248 + 8 + 31 = 287`; integration is included in full discovery. P1.10/P1 regressions, compile/import/diff/security passed.
- No production DB/state root or service was touched. The known P1.6 pending-task warning remains pre-existing debt.

## P2.2 exact architect authority
P2.2 implements only the first typed core durable repositories over accepted P2.1.

Binding source: `docs/adr/0019-core-state-repositories.md` plus ADR-0017/0018 and `docs/DATA_MODEL.md`.

### Common repository contract
- Immutable/materialized records only; no `sqlite3.Row`, cursor or connection escapes.
- Repository methods use only `SqliteStorage.read/write`; no direct filesystem/SQLite ownership outside the kernel.
- Finite semantic repository categories: `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `VERSION_CONFLICT`, `STATE_CONFLICT`, `CLOCK_INVALID`, `INVARIANT_VIOLATION`. Rendering contains category only. `StorageError` remains the underlying kernel error and may propagate unchanged.
- Required strings are NUL-free and schema-bound; nullable values follow ADR-0018. `last_error_class` is a sanitized ASCII identifier using letters/digits plus `_ . : -`, length 1..128.
- Injected repository clock returns non-bool integer epoch ms >=0; exception/invalid result => `CLOCK_INVALID`, redacted. Updates persist `max(clock_now, previous.updated_at_ms)`.
- Versioned records start at 0 and every successful mutation increments exactly by 1. Stale expected version => `VERSION_CONFLICT`; no merge/retry.

### controller_runtime repository
- P2.2 exposes only `get` + durable `begin_boot(fleet_version)` semantics. Control epoch/mode mutation is P2.3.
- First boot inserts singleton with epoch 0, historical requested mode SLEEP, boot generation 1 and supplied fleet version.
- Later boot preserves `last_control_epoch` and historical `requested_mode`, increments boot generation exactly once, replaces fleet version and advances timestamp.
- Returned boot result always has `effective_mode=SLEEP`, even when the persisted historical requested mode is ACTIVE. Restart never restores ACTIVE.

### settings repository
- Materialized record: nullable profile/model/effort + optimistic version/timestamps.
- `initialize_settings_if_absent(...)` inserts version 0 only when absent; an existing durable row wins over new config fallback values and is returned unchanged, with created/not-created outcome.
- `replace_settings(expected_version, profile_id, model_id, reasoning_effort)` replaces the full validated selection, increments version once and advances time. Missing => NOT_FOUND; stale => VERSION_CONFLICT.
- Product eligibility/state rules for profile/model/effort remain P3; repository does not query Codex/model catalog.

### dialogue create-intent repository
- `DialogueState` materializes all ADR-0018 states, but P2.2 writes only `CREATING`, `IDLE`, `CREATE_UNKNOWN`, `ERROR`.
- `get_live_dialogue()` returns the sole retained row or None.
- `create_dialogue_intent(dialogue_id, server_id, profile_id)` requires no retained dialogue and inserts CREATING/version0/thread NULL/error NULL. Any retained row => ALREADY_EXISTS. It is not silently idempotent.
- `confirm_dialogue_created(dialogue_id, expected_version, thread_id)`: exact CREATING row with NULL thread, set thread once, IDLE, clear error, version+1.
- `mark_dialogue_create_unknown(...)`: only CREATING+NULL thread, state CREATE_UNKNOWN, sanitized error, version+1.
- `mark_dialogue_create_error(...)`: only CREATING+NULL thread, state ERROR, sanitized error, version+1.
- Missing => NOT_FOUND; stale version => VERSION_CONFLICT; wrong state/thread precondition => STATE_CONFLICT. Server/profile identity is immutable. No generic state mutation and no dialogue deletion.

### P2.2 forbidden scope
No control-message epoch acceptance, ACTIVE/SLEEP routing update, Telegram ingress dedupe, callback claims, turn-job/transient/delivery/approval repositories, retention, error fingerprints, deletion tombstones/local purge, turn/interrupt/delete dialogue transitions, crash/restart orchestration, P3 service, Telegram or production deployment.

## Execution authority
Codex must not self-start work from this document.

Only **P2.2 — controller/settings/dialogue core repositories + optimistic versions + create-intent claims** is eligible for the next explicit implementation prompt.
